#!/usr/bin/env python3
"""idmc_cai_publish.py - publish / unpublish CAI assets (service connectors, app connections, processes,
taskflows, guides) in dependency waves, poll each job and check EVERY item, then read the state back.

  python idmc_cai_publish.py plan      (--path Explore/<p>/<f>/<n>.<TYPE>.xml | --resolve <name>:<TYPE> | --folder <p>/<f>) ...
  python idmc_cai_publish.py publish   (same selectors)   [--execute --expect-org <orgIdV3>]
  python idmc_cai_publish.py unpublish (same selectors) [--all]   [--execute --expect-org <orgIdV3>]
  python idmc_cai_publish.py status <jobId> --kind publish|unpublish

Routes (host https://<pod>-cai.<domain>.informaticacloud.com; INFA-SESSION-ID with the v2 id; Accept AND
Content-Type application/vnd.api+json). PROVEN 2026-09 (9/9 assets in a production migration, plus cleanup
unpublish waves):
  POST /active-bpel/asset/v1/publish   {"data":{"type":"publish","attributes":{"assetPaths":[...]}}}   -> 202, data.id
  POST /active-bpel/asset/v1/unpublish {"data":{"type":"unpublish","attributes":{"assetPaths":[...]}}} -> 202, data.id
  GET  /active-bpel/asset/v1/<publish|unpublish>/<id>/Status -> data.attributes.jobState + itemDetail[].itemState
Rules: asset paths are Explore/<project>/<folder>/<name>.<TYPE>.xml (a bare <project>/<folder>/<name> ends in
  itemState BAD_REQUEST 'Invalid asset path'); 'data' must be an object (an array gives 500 ClassCastException);
  Accept: application/json gives 500 NotAcceptable; at most 199 assets per call. Publish order: service connector
  -> app connection -> processes; unpublish in reverse; stop at the first failed wave. A 202 is only submission:
  read each item (SUCCESS / ERROR / NOT_FOUND / BAD_REQUEST). After a publish the runtime may serve the previous
  version for ~20 s: verify with side-effect-free calls and retry. FRS refuses to delete published assets
  (FRS_082): unpublish first. Duplicate runtime catalog rows ('singleton sequence ... 2 items') or a missing
  runtime entry (AvrEntryNotFoundFault) make both verbs fault: that needs support or a UI attempt.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import idmc_http as H  # noqa: E402
from idmc_objects import list_objects  # noqa: E402
from idmc_session import LoginError, Session  # noqa: E402

RANK = {"AI_SERVICE_CONNECTOR": 0, "AI_CONNECTION": 1, "PROCESS_OBJECT": 2, "PROCESS": 3, "TASKFLOW": 3, "GUIDE": 3}
RUNNING = ("NOT_STARTED", "RUNNING", "IN_PROGRESS", "QUEUED", None)
MAX_PER_CALL = 199


def asset_type(path):
    parts = path.rsplit(".", 2)
    return parts[-2] if len(parts) == 3 and parts[-1] == "xml" else None


def select(S, a):
    """-> [(assetPath, type, v3 object or None)] from --path / --resolve / --folder."""
    out, cache = [], {}

    def objs(t):
        if t not in cache:
            cache[t] = list_objects(S, f"type=='{t}'")
        return cache[t]
    for p in a.path or []:
        if not p.startswith("Explore/") or not asset_type(p):
            H.die(f"asset path must look like Explore/<project>/<folder>/<name>.<TYPE>.xml: {p}")
        out.append((p, asset_type(p), None))
    for spec in a.resolve or []:
        name, _, t = spec.rpartition(":")
        hits = [o for o in objs(t) if (o.get("path") or "").split("/")[-1] == name]
        if len(hits) != 1:
            H.die(f"{spec}: {len(hits)} matches (need exactly 1; use --path)")
        out.append((f"Explore/{hits[0]['path']}.{t}.xml", t, hits[0]))
    for folder in a.folder or []:
        for t in RANK:
            for o in objs(t):
                if (o.get("path") or "").startswith(folder.rstrip("/") + "/"):
                    out.append((f"Explore/{o['path']}.{t}.xml", t, o))
    return out


def waves(items, verb):
    order = sorted({RANK.get(t, 3) for _, t, _ in items}, reverse=(verb == "unpublish"))
    for rank in order:
        batch = [x for x in items if RANK.get(x[1], 3) == rank]
        for i in range(0, len(batch), MAX_PER_CALL):
            yield batch[i:i + MAX_PER_CALL]


def pub_state(o):
    return ((o or {}).get("customAttributes") or {}).get("publicationStatus")


def run_wave(S, gate, verb, batch):
    body = {"data": {"type": verb, "attributes": {"assetPaths": [p for p, _, _ in batch]}}}
    r = gate.send(f"{verb} {len(batch)} asset(s) {sorted({t for _, t, _ in batch})}", "cai", "POST",
                  f"/active-bpel/asset/v1/{verb}", body=body)
    if r is None:
        return True
    jid = ((r.json({}) or {}).get("data") or {}).get("id") if r.status in (200, 202) else None
    if not jid:
        print(f"  {verb} not accepted: HTTP {r.status} {r.head(300)}")
        return False
    return check_job(S, verb, jid)


def check_job(S, verb, jid, timeout=900):
    def fetch():
        r = S.get("cai", f"/active-bpel/asset/v1/{verb}/{jid}/Status")
        return ((r.json({}) or {}).get("data") or {}).get("attributes") or {} if r.ok else {"jobState": f"HTTP {r.status}"}
    at, done = H.poll(fetch, lambda x: x.get("jobState") not in RUNNING, interval=5, timeout=timeout,
                      describe=lambda x: f"job {jid} {x.get('jobState')}")
    items = at.get("itemDetail") or []
    bad = [d for d in items if str(d.get("itemState")).upper() not in ("SUCCESS", "SUCCESSFUL")]
    print(f"  job {jid}: {at.get('jobState')}, {len(items)} item(s), {len(bad)} not successful")
    for d in bad[:25]:
        print(f"    {d.get('assetPath') or d.get('itemPath')}: {d.get('itemState')} {str(d.get('itemStatusDetail'))[:220]}")
    return done and not bad and at.get("jobState") in ("SUCCESS", "WARNING", "COMPLETED")


def main():
    H.safe_console()
    ap = argparse.ArgumentParser(description="CAI publish / unpublish")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for c in ("plan", "publish", "unpublish"):
        p = H.add_gate_args(sub.add_parser(c)) if c != "plan" else sub.add_parser(c)
        p.add_argument("--path", action="append")
        p.add_argument("--resolve", action="append", help="<name>:<TYPE>, e.g. my_process:PROCESS")
        p.add_argument("--folder", action="append", help="<project>/<folder>: every CAI asset inside")
        if c == "unpublish":
            p.add_argument("--all", action="store_true", help="include assets not flagged published")
    stt = sub.add_parser("status")
    stt.add_argument("job")
    stt.add_argument("--kind", required=True, choices=["publish", "unpublish"])
    a = ap.parse_args()
    try:
        S = Session()
        if a.cmd == "status":
            ok = check_job(S, a.kind, a.job, timeout=0)
            sys.exit(0 if ok else 1)
        items = select(S, a)
        if a.cmd == "unpublish" and not a.all:
            skipped = [p for p, _, o in items if o is not None and pub_state(o) != "published"]
            items = [x for x in items if x[2] is None or pub_state(x[2]) == "published"]
            if skipped:
                print(f"  skipping {len(skipped)} asset(s) not flagged published (use --all to include)")
        if not items:
            H.die("nothing selected")
        verb = "unpublish" if a.cmd == "unpublish" else "publish"
        for n, batch in enumerate(waves(items, verb), 1):
            print(f"wave {n}:")
            for p, t, o in batch:
                print(f"   {t:22} {p}  (now: {pub_state(o) or '?'})")
        if a.cmd == "plan":
            return
        gate = H.WriteGate(a, S)
        gate.guard()
        for n, batch in enumerate(waves(items, verb), 1):
            if not run_wave(S, gate, verb, batch):
                H.die(f"wave {n} failed: later waves were NOT sent (dependency order)")
        if gate.execute:
            now = {f"Explore/{o['path']}.{t}.xml": pub_state(o) for t in {t for _, t, _ in items}
                   for o in list_objects(S, f"type=='{t}'")}
            for p, t, _ in items:
                print(f"  read-back {p}: publicationStatus={now.get(p)}")
    except (LoginError, RuntimeError) as e:
        H.die(f"{type(e).__name__}: {e}", 3)


if __name__ == "__main__":
    main()
