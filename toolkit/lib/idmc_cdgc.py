#!/usr/bin/env python3
"""idmc_cdgc.py - CDGC headless: JWT check, catalog sources (list/get/create/update, multipart), scans and job
polling, Elasticsearch search, glossary domain/term create with an idempotent registry and undo, term links.

  python idmc_cdgc.py jwt-check                    python idmc_cdgc.py sources
  python idmc_cdgc.py source-get <id> [--save f]
  python idmc_cdgc.py source-create --json f [--map OLD=NEW ...] [--forbid-prefix P ...]   (dry-run by default)
  python idmc_cdgc.py source-update <id> --json f                                          (dry-run by default)
  python idmc_cdgc.py scan <id> [--cap "Metadata Extraction" ...] [--wait]    python idmc_cdgc.py job <jobId> [--wait]
  python idmc_cdgc.py search (--class-type T | --external-id X ... | --es-json f) [--size 200] [--all]
  python idmc_cdgc.py glossary-create --registry reg.json (--domain NAME | --term NAME --domain-key KEY) [--desc D]
  python idmc_cdgc.py glossary-undo --registry reg.json    python idmc_cdgc.py link --asset A --term-key KEY --registry r
Writes need --execute --expect-org <orgIdV3>. Headers: Authorization Bearer <JWT client_id=cdlg_app> +
X-INFA-ORG-ID <orgIdV3> + IDS-SESSION-ID (minted from the v2 session; renewed on 401; cached 20 min in memory).

PROVEN 2026-09 (a production catalog rebuild: 5 sources, one-at-a-time scans, 33 terms, 42 links):
  https://cdgc-api.<domain>.informaticacloud.com/ccgf-catalog-source-management/api/v1/datasources[?offset&limit|/<id>]
    create = multipart POST with ONE part named 'dataSource' (plain JSON gives 415); needs 'custom' and 'endOfLife'
    (else 500 'Custom flag cannot be null'); update = multipart PUT (PATCH fallback) after stripping read-only fields
    but keeping 'id' (else 400 'id in request path and body do not match'); the read-back reorders capabilities, so
    diffs sort them by capabilityName
  https://idmc-api.<domain>.informaticacloud.com/data360/executable/v1/catalogsource/<id> {"capabilityNames":[..]} -> jobId
  .../data360/observable/v1/jobs/<jobId>?expandChildren=TASK-HIERARCHY -> status (COMPLETED, PARTIAL_COMPLETED, FAILED..)
  .../data360/search/api/v1/search?knowledgeQuery=*&segments=all + X-INFA-SEARCH-LANGUAGE: elasticsearch -> hits.hits[]
  .../data360/content/v1/assets (POST domain / term), DELETE .../assets/<identity>?scheme=internal,
  PATCH .../assets/<identity>?scheme=internal [{"operation":"add","segment":"glossary","items":[{"core.identity":..}]}]
Gotchas: an empty capabilityNames list gives a misleading 500; scans bill IPUs and need the agent's Metadata services
  (enable them only for the scan window, one source at a time); set 'Metadata Change Option' = Delete before a rescan
  or dropped objects stay; a GET by externalId in the path gives 400 (encoded slashes): resolve by search; the API
  rate-limits (429): walk sequentially with an adaptive pace; REST DELETE of a source only PURGES its metadata (the
  definition stays and is removed in the Metadata Command Center UI); an IICS lineage source stores a password in
  its options and breaks when it rotates (values of *Password* keys are masked in output).
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import idmc_http as H  # noqa: E402
from idmc_session import LoginError, Session  # noqa: E402

DS = "/ccgf-catalog-source-management/api/v1/datasources"
KEEP = ("name", "description", "type", "endOfLife", "custom", "overrides", "typeOptions", "capabilities",
        "typeCapabilities", "globalConfigOptions", "customAttributes")
READ_ONLY = ("id", "createdBy", "lastModifiedBy", "createdTime", "lastModifiedTime", "seedVersion",
             "clonedCatalogSourceId", "modelVersion")
DOMAIN, TERM = "com.infa.ccgf.models.governance.Domain", "com.infa.ccgf.models.governance.BusinessTerm"
ES = {"X-INFA-SEARCH-LANGUAGE": "elasticsearch"}


def mask(o):
    if isinstance(o, dict):
        if "password" in str(o.get("key", "")).lower() or "secret" in str(o.get("key", "")).lower():
            return dict(o, values=["<masked>"])
        return {k: mask(v) for k, v in o.items()}
    return [mask(x) for x in o] if isinstance(o, list) else o


def by_cap(o):
    """Sort capabilities/typeCapabilities by capabilityName: a GET after a PUT returns them reordered."""
    o = dict(o)
    for grp in ("capabilities", "typeCapabilities"):
        if isinstance(o.get(grp), list):
            o[grp] = sorted(o[grp], key=lambda c: str(c.get("capabilityName", "")) if isinstance(c, dict) else "")
    return o


def remap(o, m):
    if isinstance(o, dict):
        return {k: remap(v, m) for k, v in o.items()}
    if isinstance(o, list):
        return [remap(v, m) for v in o]
    return m.get(o, o) if isinstance(o, str) else o


def strings(o):
    if isinstance(o, dict):
        for v in o.values():
            yield from strings(v)
    elif isinstance(o, list):
        for v in o:
            yield from strings(v)
    elif isinstance(o, str):
        yield o


def search(S, query, size=200, all_pages=False):
    out, frm, pace = [], 0, 0.5
    while True:
        r = S.call("d360", "POST", "/data360/search/api/v1/search?knowledgeQuery=*&segments=all",
                   body=dict(query, **{"from": frm, "size": size}), headers=ES)
        if r.status == 429:
            pace = min(pace * 2, 30)
            time.sleep(pace)
            continue
        if not r.ok:
            raise RuntimeError(f"search HTTP {r.status} {r.head(200)}")
        hits = ((r.json({}) or {}).get("hits") or {})
        page = [h.get("sourceAsMap") or {} for h in hits.get("hits") or []]
        out += page
        frm += size
        total = (hits.get("total") or {}).get("value", 0) if isinstance(hits.get("total"), dict) else hits.get("total") or 0
        if not all_pages or not page or frm >= total:
            return out, total
        time.sleep(pace)


def get_source(S, sid):
    r = S.get("cdgc", f"{DS}/{sid}")
    if not r.ok:
        H.die(f"GET datasource {sid} -> HTTP {r.status} {r.head(200)}")
    return r.json({}) or {}


def send_multipart(gate, label, method, path, body):
    raw, ctype = H.multipart_json("dataSource", body)
    r = gate.send(label, "cdgc", method, path, raw=raw, ctype=ctype)
    if r is not None and r.status == 405 and method == "PUT":
        r = gate.send(label + " (PATCH fallback)", "cdgc", "PATCH", path, raw=raw, ctype=ctype)
    return r


def poll_job(S, jid, wait):
    def fetch():
        return S.get("d360", f"/data360/observable/v1/jobs/{jid}?expandChildren=TASK-HIERARCHY").json({}) or {}
    j, _ = H.poll(fetch, lambda x: not wait or x.get("status") not in ("RUNNING", "SUBMITTED", "STARTING", "QUEUED", "CREATED", None),
                  interval=15, timeout=7200, describe=lambda x: f"job {jid} status={x.get('status')}")
    return j


def load_reg(p):
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}


def main():
    H.safe_console()
    ap = argparse.ArgumentParser(description="CDGC headless")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("jwt-check")
    sub.add_parser("sources")
    g = sub.add_parser("source-get")
    g.add_argument("id")
    g.add_argument("--save")
    c = H.add_gate_args(sub.add_parser("source-create"))
    c.add_argument("--json", required=True)
    c.add_argument("--map", action="append", default=[])
    c.add_argument("--forbid-prefix", action="append", default=[])
    u = H.add_gate_args(sub.add_parser("source-update"))
    u.add_argument("id")
    u.add_argument("--json", required=True)
    s = H.add_gate_args(sub.add_parser("scan"))
    s.add_argument("id")
    s.add_argument("--cap", action="append")
    s.add_argument("--wait", action="store_true")
    j = sub.add_parser("job")
    j.add_argument("job")
    j.add_argument("--wait", action="store_true")
    q = sub.add_parser("search")
    q.add_argument("--class-type")
    q.add_argument("--external-id", action="append")
    q.add_argument("--es-json")
    q.add_argument("--size", type=int, default=200)
    q.add_argument("--all", action="store_true")
    gc = H.add_gate_args(sub.add_parser("glossary-create"))
    for f in ("--registry",):
        gc.add_argument(f, required=True)
    for f in ("--domain", "--term", "--domain-key", "--desc"):
        gc.add_argument(f)
    H.add_gate_args(sub.add_parser("glossary-undo")).add_argument("--registry", required=True)
    lk = H.add_gate_args(sub.add_parser("link"))
    for f in ("--asset", "--term-key", "--registry"):
        lk.add_argument(f, required=True)
    a = ap.parse_args()
    try:
        S = Session()
        if a.cmd == "jwt-check":
            print(f"JWT minted, {len(S.jwt())} chars (value never printed); X-INFA-ORG-ID={S.v2().get('orgUuid')}")
            return
        if a.cmd == "sources":
            r = S.get("cdgc", f"{DS}?offset=0&limit=100")
            for d in (r.json({}) or {}).get("datasources") or []:
                print(f"  {d.get('id')}  {d.get('type', ''):22} {d.get('name')}")
            print(f"HTTP {r.status}")
            return
        if a.cmd == "source-get":
            d = get_source(S, a.id)
            if a.save:
                print("saved (0600; may hold a password):", H.save_json(a.save, d))
            print(H.preview(mask(d), 6000))
            return
        if a.cmd == "job":
            print(H.preview(poll_job(S, a.job, a.wait), 3000))
            return
        if a.cmd == "search":
            query = (json.load(open(a.es_json, encoding="utf-8")) if a.es_json else
                     {"query": {"terms": {"core.externalId": a.external_id}}} if a.external_id else
                     {"query": {"term": {"core.classType": a.class_type}}})
            rows, total = search(S, query, a.size, a.all)
            for x in rows:
                print(f"  {x.get('core.identity')}  {x.get('core.classType', '')[-28:]:28} {x.get('core.name')}  {x.get('core.externalId')}")
            print(f"{len(rows)} of {total} hit(s)")
            return
        gate = H.WriteGate(a, S)
        gate.guard()
        if a.cmd == "source-create":
            body = remap({k: copy.deepcopy(v) for k, v in json.load(open(a.json, encoding="utf-8")).items() if k in KEEP},
                         dict(m.split("=", 1) for m in a.map))
            for k in ("custom", "endOfLife"):
                if body.get(k) is None:
                    H.die(f"body needs '{k}' (without it the create answers 500 'Custom flag cannot be null')")
            left = [x for x in strings(body) for p in a.forbid_prefix if x.startswith(p)]
            if left:
                H.die(f"unmapped ids left in the body: {sorted(set(left))[:10]}")
            have = {d.get("name") for d in (S.get("cdgc", f"{DS}?offset=0&limit=100").json({}) or {}).get("datasources") or []}
            if body.get("name") in have:
                H.die(f"a catalog source named '{body.get('name')}' already exists: use source-update")
            r = send_multipart(gate, f"create catalog source {body.get('name')}", "POST", DS, body)
            if r is not None:
                new = (r.json({}) or {}).get("id") if r.ok else None
                print(f"  created id={new}" if new else f"  create failed HTTP {r.status} {r.head(300)}")
                if new:
                    print(f"  read-back: {get_source(S, new).get('name')}")
        elif a.cmd == "source-update":
            cur = get_source(S, a.id)
            print("  backup:", H.save_json(f"datasource_{a.id}_before.json", cur))
            new = {k: v for k, v in json.load(open(a.json, encoding="utf-8")).items() if k not in READ_ONLY}
            new["id"] = a.id  # without it the PUT answers 400 'id in request path and body do not match'
            H.print_diff(H.diff(by_cap(mask(cur)), by_cap(mask(new)), ignore=READ_ONLY), "would change")
            r = send_multipart(gate, f"update catalog source {a.id}", "PUT", f"{DS}/{a.id}", new)
            if r is not None:
                H.print_diff(H.diff(by_cap(mask(new)), by_cap(mask(get_source(S, a.id))), ignore=READ_ONLY),
                             "read-back differs from sent")
        elif a.cmd == "scan":
            caps = a.cap or list(dict.fromkeys(c.get("capabilityName") for grp in ("capabilities", "typeCapabilities")
                                               for c in get_source(S, a.id).get(grp) or [] if c.get("capabilityName")))
            if not caps:
                H.die("no capabilityNames (an empty list gives a misleading 500)")
            print(f"  capabilities: {caps} (a scan bills IPUs)")
            r = gate.send(f"scan catalog source {a.id}", "d360", "POST", f"/data360/executable/v1/catalogsource/{a.id}",
                          body={"capabilityNames": caps})
            jid = (r.json({}) or {}).get("jobId") if r is not None and r.ok else None
            if jid:
                print(f"  jobId {jid}")
                print(H.preview(poll_job(S, jid, a.wait), 1500))
        elif a.cmd == "glossary-create":
            reg = load_reg(a.registry)
            key = ("DOM:" + a.domain) if a.domain else f"{a.domain_key}:{a.term}"
            if key in reg:
                print(f"  already in registry: {key} -> {reg[key]['identity']}")
                return
            if a.domain:
                body = {"core.classType": DOMAIN, "summary": {"core.name": a.domain, "core.description": a.desc or ""}}
            else:
                if a.domain_key not in reg:
                    H.die(f"--domain-key {a.domain_key} is not in the registry: create the domain first")
                body = {"core.classType": TERM, "summary": {"core.name": a.term, "core.description": a.desc or ""},
                        "parent": {"core.identity": reg[a.domain_key]["identity"]}}
            r = gate.send(f"create {key}", "d360", "POST", "/data360/content/v1/assets", body=body)
            if r is not None and r.ok:
                reg[key] = {"identity": (r.json({}) or {}).get("core.identity"), "ext": (r.json({}) or {}).get("core.externalId")}
                H.save_json(a.registry, reg, private=False)
                print(f"  registered {key} -> {reg[key]['identity']}")
        elif a.cmd == "glossary-undo":
            reg = load_reg(a.registry)
            for key, v in reversed(list(reg.items())):       # terms before their domain
                r = gate.send(f"delete {key}", "d360", "DELETE", f"/data360/content/v1/assets/{v['identity']}?scheme=internal")
                if r is not None and r.status in (200, 204):
                    reg.pop(key)
                    H.save_json(a.registry, reg, private=False)
        else:
            reg = load_reg(a.registry)
            if a.term_key not in reg:
                H.die(f"{a.term_key} is not in the registry")
            gate.send(f"link term {a.term_key}", "d360", "PATCH", f"/data360/content/v1/assets/{a.asset}?scheme=internal",
                      body=[{"operation": "add", "segment": "glossary", "items": [{"core.identity": reg[a.term_key]["identity"]}]}])
    except (LoginError, RuntimeError) as e:
        H.die(f"{type(e).__name__}: {e}", 3)


if __name__ == "__main__":
    main()
