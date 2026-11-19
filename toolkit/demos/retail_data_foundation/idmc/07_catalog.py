#!/usr/bin/env python3
"""Step 7: catalog (CDGC) sources, scans, business glossary and term links. Classification comes from the scans.

  python idmc/07_catalog.py render --offline                          # the three catalog-source bodies, no network
  python idmc/07_catalog.py sources --execute --expect-org <orgIdV3>  # create the sources (multipart dataSource part)
  python idmc/07_catalog.py scan rdf_cat_pg --execute --expect-org <orgIdV3>   # ONE source at a time; bills IPUs
  python idmc/07_catalog.py glossary --execute --expect-org <orgIdV3> # domain + terms (registry = idempotent, undo-able)
  python idmc/07_catalog.py links --execute --expect-org <orgIdV3>    # link terms to the scanned assets by exact name
  python idmc/07_catalog.py undo-glossary --execute --expect-org <orgIdV3>

Sources (PROVEN 2026-09: a catalog rebuild with 5 sources, 33 terms, 42 links, 6 classifications):
  rdf_cat_pg   PostgreSQL: schemas public + activation (a default public-only scope silently drops other schemas;
               the control schema is left out on purpose); profiling + auto classification
  rdf_cat_bq   Google BigQuery: the four datasets, each filter in both forms "<ds>.*" and "<project>.<ds>.*"
  rdf_cat_cdi  IICS (Data Integration lineage of the project): stitches PG -> BigQuery -> Salesforce through the
               mappings. Its user and secret are the IDMC login, injected at send time and never written to disk.
Create = POST /ccgf-catalog-source-management/api/v1/datasources as multipart with one part named dataSource
(plain JSON = 415) and the custom + endOfLife keys (without them: 500 'Custom flag cannot be null').
Scan = POST /data360/executable/v1/catalogsource/<id> {"capabilityNames": [...]} (an empty list = a misleading 500).
Set "Metadata Change Option" = Delete before a re-scan, or stale assets stay. REST cannot delete a source definition
(DELETE only purges its metadata): removing one is a UI step.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "lib"))
import rdf_common as C  # noqa: E402

TPL = HERE / "templates" / "catalog"
REG = C.STATE_DIR / "glossary_registry.json"
CONN_FOR = {"catalog_source_postgres.json": "pg", "catalog_source_bigquery.json": "bq"}


def render_sources(cfg, st, offline):
    v = C.template_vars(cfg, offline=offline)
    v["RE_ID"] = (st.get("runtimeEnvironment") or {}).get("id") or "<runtime environment id>"
    v["IDMC_LOGIN_HOST"] = C.env("IDMC_LOGIN_HOST") or "<IDMC_LOGIN_HOST>"
    v["IICS_USER"] = "<IDMC_USER, injected at send>"
    v["IICS_PASSWORD_INJECTED_AT_SEND"] = "<IDMC_PASS, injected at send>"  # nosec B105  # placeholder text, not a secret
    out = {}
    for name, sc in cfg["catalog"]["sources"].items():
        vv = dict(v, NAME=name)
        ck = CONN_FOR.get(sc["template"])
        vv["CONN_ID"] = ((st.get("connections") or {}).get(ck) or {}).get("id") or f"<v2 id of connection {ck}>"
        body = C.render_json(TPL / sc["template"], vv)
        out[name] = body
        C.write_rendered(f"catalog_{name}.json", body)
    return out


def inject(body):
    """The IICS source logs in as an IDMC user: put the real values in, in memory only."""
    for grp in (body.get("typeOptions") or {}).get("configurationProperties") or []:
        for o in grp.get("configOptions") or []:
            if o["key"] == "IICS User":
                o["values"] = [C.env("IDMC_USER", required=True)]
            elif o["key"] == "IICS Password":
                o["values"] = [C.env("IDMC_PASS", required=True)]
    return body


def main():
    ap = C.add_common_args(argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter))
    ap.add_argument("cmd", choices=["render", "sources", "scan", "glossary", "links", "undo-glossary"])
    ap.add_argument("names", nargs="*")
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args()
    cfg, st = C.load_config(a.config), C.load_state()
    if a.cmd == "render":
        bodies = render_sources(cfg, st, True)
        for n, b in bodies.items():
            print(f"{n}: type {b['type']}, capabilities {[c['capabilityName'] for c in b['capabilities']]} "
                  f"-> state/rendered/catalog_{n}.json")
        g = json.loads((C.BLUEPRINT / cfg["catalog"]["glossaryFile"]).read_text(encoding="utf-8"))
        print(f"glossary: domain '{g['domain']['name']}', {len(g['terms'])} terms, "
              f"{sum(len(t['links']) for t in g['terms'])} links")
        return 0
    if a.cmd in ("glossary", "undo-glossary"):
        g = json.loads((C.BLUEPRINT / cfg["catalog"]["glossaryFile"]).read_text(encoding="utf-8"))
        if a.cmd == "undo-glossary":
            return C.core_cli("idmc_cdgc.py", ["glossary-undo", "--registry", str(REG)] + C.gate_args(a))
        rc = C.core_cli("idmc_cdgc.py", ["glossary-create", "--registry", str(REG), "--domain", g["domain"]["name"],
                                         "--desc", g["domain"]["description"]] + C.gate_args(a))
        for t in g["terms"]:
            rc |= C.core_cli("idmc_cdgc.py", ["glossary-create", "--registry", str(REG), "--term", t["name"],
                                              "--domain-key", "DOM:" + g["domain"]["name"], "--desc", t["description"]]
                             + C.gate_args(a))
        return rc
    C.offline_session_guard(a)
    from idmc_session import Session
    import idmc_http as H
    import idmc_cdgc as G
    S = Session()
    gate = H.WriteGate(a, S)
    have = {d.get("name"): d for d in (S.get("cdgc", f"{G.DS}?offset=0&limit=100").json({}) or {}).get("datasources") or []}
    st.setdefault("catalog", {})
    if a.cmd == "sources":
        for name, body in render_sources(cfg, st, False).items():
            if a.names and name not in a.names:
                continue
            if name in have:
                print(f"{name}: exists ({have[name].get('id')}); change it with core idmc_cdgc.py source-update")
                st["catalog"][name] = {"id": have[name].get("id")}
                continue
            if "<" in json.dumps(body).replace("<IDMC_USER, injected at send>", "").replace("<IDMC_PASS, injected at send>", ""):
                C.die(f"{name}: unresolved ids in the body (run 00_resolve.py after step 1)")
            r = G.send_multipart(gate, f"create catalog source {name}", "POST", G.DS, inject(body))
            if r is not None:
                sid = (r.json({}) or {}).get("id") if r.ok else None
                print(f"   -> HTTP {r.status} id {sid or r.head(200)}")
                if sid:
                    st["catalog"][name] = {"id": sid}
    elif a.cmd == "scan":
        if len(a.names) != 1:
            C.die("scan exactly one source at a time (parallel scans fight for the metadata services)")
        sid = (st["catalog"].get(a.names[0]) or {}).get("id") or (have.get(a.names[0]) or {}).get("id")
        if not sid:
            C.die(f"{a.names[0]}: not created")
        return C.core_cli("idmc_cdgc.py", ["scan", sid, "--wait"] + C.gate_args(a))
    elif a.cmd == "links":
        g = json.loads((C.BLUEPRINT / cfg["catalog"]["glossaryFile"]).read_text(encoding="utf-8"))
        reg = json.loads(REG.read_text(encoding="utf-8")) if REG.exists() else {}
        dkey = "DOM:" + g["domain"]["name"]
        rc = 0
        for t in g["terms"]:
            tkey = f"{dkey}:{t['name']}"
            if tkey not in reg:
                print(f"{t['name']}: not in the registry (run glossary first)")
                continue
            for asset in t["links"]:
                found, _total = G.search(S, {"query": {"match": {"core.name": asset}}}, size=50)
                hits = [x for x in found if x.get("core.name") == asset
                        and any(k in (x.get("core.classType") or "") for k in ("Table", "View"))]
                if not hits:
                    print(f"   {t['name']} -> {asset}: no cataloged table/view with that exact name (scan first)")
                    continue
                for h in hits[:3]:                   # the same table name can exist in landing and gold
                    rc |= C.core_cli("idmc_cdgc.py", ["link", "--asset", h.get("core.identity"), "--term-key", tkey,
                                                      "--registry", str(REG)] + C.gate_args(a))
        return rc
    if gate.execute:
        C.save_state(st)
    return 0


if __name__ == "__main__":
    sys.exit(main())
