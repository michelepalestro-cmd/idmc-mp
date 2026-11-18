#!/usr/bin/env python3
"""bid_catalog.py - the Bid Desk in Data Governance & Catalog (CDGC): three catalog sources, their scans, the lineage
connection assignment, and the lineage feed for Tableau.

    python bid_catalog.py show                                   # the three sources, scope, last scan (read-only)
    python bid_catalog.py create [--execute --expect-org <orgIdV3>]   # clone a same-type source per config, new name + scope
    python bid_catalog.py scan [--no-profiling] [--execute ...]  # Salesforce, Snowflake (+ profiling), then lineage; one at a time
    python bid_catalog.py refs                                   # the lineage source's connection references (read-only)
    python bid_catalog.py merge [--execute ...]                  # assign those references onto the Snowflake / Salesforce sources
    python bid_catalog.py chain [OBJECT]                         # every upstream hop of a view (default BID_V_BI_DECISIONS)
    python bid_catalog.py feed [--execute]                       # that lineage for every Tableau view -> Snowflake BID_LINEAGE

Calls (PROVEN 2026-10-13; toolkit/lib/idmc_cdgc.py documents the hosts and headers):
  sources  GET/POST https://cdgc-api.<domain>/ccgf-catalog-source-management/api/v1/datasources[/<id>]: create = multipart POST
           with ONE part 'dataSource' (plain JSON gives 415) and 'custom' + 'endOfLife' set (else 500). We GET an existing source
           of the same type (config idmc.catalog_templates), drop read-only fields, set name, description and scope:
             Snowflake   typeOptions ConnectionId = our connection; 'Filter Value' = BID_* (metadata), BID_SLV_* + BID_GLD_* (profiling)
             Salesforce  ConnectionId + 'Runtime Environment' (the agent the CRM trusts); Metadata Extraction filter
                         Include Metadata / CRM / 'Object, using API name' / [Account, ContentVersion]
             IICS        Metadata Extraction filter = [the project]; Lineage Discovery filter = the two sources to stitch;
                         its three IDMC login options (user, pass, URL) come from the .env at --execute
  scan     POST https://idmc-api.<domain>/data360/executable/v1/catalogsource/<id> {"capabilityNames":[...]} (never an empty
           list: misleading 500) -> poll /data360/observable/v1/jobs/<jobId>?expandChildren=TASK-HIERARCHY. Scans bill IPUs and
           need the agent's metadata services; a scan with profiling runs queries on the warehouse (the cost guard counts it).
  merge    POST https://cdgc-api.<domain>/ccgf-contentv2/api/v1/assignment/connectionAssignment?operationType=MERGE
           {"sourceRootAsset":{externalId,origin,location}, "targetRootAsset":[{externalId,origin,isCaseSensitive,location}],
            "initialAssignment":true,"modifyAssignment":false}. Auto-accept never resolves IDMC references. Undo: operationType=SPLIT.
  read     search (Elasticsearch body) + GET /data360/search/v1/assets/<identity>?scheme=internal&segments=all (lineage segment).
Gotchas: the catalog reads each task's RUN metadata, so lineage shows after the next pipeline run; it cannot parse a
sub-query Salesforce filter (use a plain id list); CLAIRE steps show at table level only; SharePoint shows as a stub unless
you also catalog the site.
"""
from __future__ import annotations

import copy
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
import bid_common as C  # noqa: E402

DS = "/ccgf-catalog-source-management/api/v1/datasources"
RO = ("id", "createdBy", "lastModifiedBy", "createdTime", "lastModifiedTime", "seedVersion", "clonedCatalogSourceId", "modelVersion",
      "isDeleted")
CAPS = {"Snowflake": ["Metadata Extraction", "Data Profiling"], "Salesforce": ["Metadata Extraction"],
        "IICS": ["Metadata Extraction", "Lineage Discovery"]}


def gov(ctx):
    return C.render(C.template("governance.json"), ctx.cfg)


def sources(ctx):
    out, off = [], 0
    while True:
        r = ctx.read("cdgc", "%s?offset=%d&limit=100" % (DS, off))
        page = ((r.json({}) or {}).get("datasources") or []) if r is not None else []
        out += page
        if len(page) < 100:
            return {s["name"]: s for s in out}
        off += 100


def scope(d, spec, st, secrets):
    t = spec["type"]
    for g in (d.get("typeOptions") or {}).get("configurationProperties") or []:
        for o in g.get("configOptions") or []:
            if o["key"] == "ConnectionId" and spec.get("connection"):
                o["values"] = [spec["connection"]]
            role = next((i for i, w in enumerate(("User", "Pass", "URL")) if w in o["key"]), None) if t == "IICS" else None
            if role is not None and o["key"].startswith("IICS"):
                k = spec["login_env"][role]
                v = C.env(k) if secrets else "<%s>" % k
                o["values"] = ["https://" + v.split("://")[-1].rstrip("/") if role == 2 and secrets else v]
    if t == "Salesforce":
        for g in d.get("globalConfigOptions") or []:
            for p in g.get("configurationProperties") or []:
                for o in p.get("configOptions") or []:
                    if o["key"] == "Runtime Environment":
                        o["values"] = [spec["runtime"]]
        flt = {"optionGroupName": "Metadata Filter Config", "configOptions": [
            {"key": k, "values": v, "additionalMetadata": None} for k, v in (
                ("Filter Pivot", ["Include Metadata"]), ("Filter Type", ["CRM"]), ("Filter Conditions", ["Object, using API name"]),
                ("Filter Value", spec["objects"]))]}
        d["typeCapabilities"] = [{"capabilityName": "Metadata Extraction", "configurationProperties": [flt]}]
        return d
    for c in d.get("typeCapabilities") or []:
        for g in c.get("configurationProperties") or []:
            fv = {o["key"]: o for o in g.get("configOptions") or []}.get("Filter Value")
            if not fv:
                continue
            if t == "Snowflake":
                fv["values"] = spec["profiling_filter"] if c["capabilityName"] == "Data Profiling" else spec["metadata_filter"]
            elif c["capabilityName"] == "Metadata Extraction":
                fv["values"] = spec["project_filter"]
            elif c["capabilityName"] == "Lineage Discovery":
                fv["values"] = spec["stitch"]
    return d


def masked(d):
    m = copy.deepcopy(d)
    for g in (m.get("typeOptions") or {}).get("configurationProperties") or []:
        for o in g.get("configOptions") or []:
            if "password" in o.get("key", "").lower():
                o["values"] = ["<masked>"]
    return m


def search_all(ctx, query):
    import idmc_cdgc as G
    return G.search(ctx.S, query, size=200, all_pages=True)[0]


def refs(ctx, src_id):
    rows = search_all(ctx, {"query": {"bool": {"must": [{"term": {"core.origin": src_id}}]}}})
    return [r for r in rows if r.get("core.classType") == "core.DataSource"]


def upstream(ctx, st, obj, kind="View"):
    """walk the lineage segment upstream from one Snowflake object; [(from, type, system, to, type, system)]"""
    sf, snow = ctx.cfg["snowflake"], st["catalog"][ctx.cfg["idmc"]["project"] + " - Snowflake"]
    ext = "%s://%s/%s/%s~com.infa.odin.models.relational.%s" % (snow, sf["database"], sf["schema"], obj, kind)
    rows = search_all(ctx, {"query": {"terms": {"core.externalId": [ext]}}})
    if not rows:
        return []
    # only distance-1 hops come back per asset (L-CDGC-181): walk inbound hop by hop
    edges, todo, seen = [], [rows[0]["core.identity"]], set()
    while todo and len(seen) < 300:
        ident = todo.pop(0)
        if ident in seen:
            continue
        seen.add(ident)
        d = ctx.read("d360", "/data360/search/v1/assets/%s?scheme=internal&segments=all" % ident).json({})
        for x in d.get("lineage") or []:
            if x.get("direction") != "inbound":
                continue
            for h in x.get("hops") or []:
                for it in h.get("items") or []:
                    ft, tt = (it.get("fromType") or "").split("."), (it.get("toType") or "").split(".")
                    edges.append((it.get("from"), ft[-1], ft[-2] if len(ft) > 1 else "", it.get("to"), tt[-1], tt[-2] if len(tt) > 1 else ""))
                    if it.get("fromIdentity"):
                        todo.append(it["fromIdentity"])
        time.sleep(0.6)
    return edges


def main():
    ap = C.parser(__doc__)
    ap.add_argument("cmd", choices=["show", "create", "scan", "refs", "merge", "chain", "feed"])
    ap.add_argument("obj", nargs="?")
    ap.add_argument("--no-profiling", action="store_true")
    a = ap.parse_args()
    ctx = C.Ctx(a)
    cfg, st = ctx.cfg, C.state()
    g = gov(ctx)
    G_ = C.render(g["sources"], cfg, st)
    have = sources(ctx)
    cat = st.setdefault("catalog", {})
    for n in G_:
        if n in have:
            cat[n] = have[n]["id"]
    if a.cmd == "show":
        for n, spec in G_.items():
            print("%-34s %-10s %s" % (n, spec["type"], cat.get(n, "(offline)" if ctx.offline else "MISSING")))
    elif a.cmd == "create":
        for n, spec in G_.items():
            if n in have:
                print("EXISTS", n, have[n]["id"])
                continue
            tid = cfg["idmc"]["catalog_templates"][spec["type"]]
            r = ctx.read("cdgc", "%s/%s" % (DS, tid))
            t = r.json({}) if C.ok(r) else {"type": spec["type"], "typeOptions": {}, "typeCapabilities": []}
            d = {k: v for k, v in t.items() if k not in RO}
            d.update(name=n, description=spec["description"], custom=False, endOfLife=False)
            d = scope(d, spec, st, secrets=ctx.execute)
            raw, ctype = C.H.multipart_json("dataSource", d)
            r = ctx.write_masked("create catalog source " + n, "cdgc", "POST", DS, masked(d), raw=raw, ctype=ctype)
            if C.ok(r):
                cat[n] = (r.json({}) or {}).get("id")
    elif a.cmd == "scan":
        for n in g["scan_order"]:
            spec = G_[n]
            caps = [c for c in CAPS[spec["type"]] if not (a.no_profiling and c == "Data Profiling")]
            r = ctx.write("scan " + n, "d360", "POST", "/data360/executable/v1/catalogsource/%s" % cat.get(n, "<source id>"),
                          body={"capabilityNames": caps})
            if not C.ok(r):
                continue
            jid = (r.json({}) or {}).get("jobId")
            while True:
                time.sleep(20)
                j = ctx.read("d360", "/data360/observable/v1/jobs/%s?expandChildren=TASK-HIERARCHY" % jid).json({})
                if j.get("status") not in ("RUNNING", "SUBMITTED", "STARTING", "QUEUED", "CREATED", None):
                    print("  %s: %s" % (n, j.get("status")))
                    break
    elif a.cmd in ("refs", "merge"):
        lin, snow, crm = (cat.get("%s - %s" % (cfg["idmc"]["project"], k)) for k in ("Data Lineage", "Snowflake", "Salesforce"))
        if ctx.offline:
            print("[OFFLINE] would search core.origin=<lineage source> for core.DataSource references, then MERGE each onto")
            print("  Snowflake: {externalId: '<snowflake source>://%s~com.infa.odin.models.relational.Database'}" % cfg["snowflake"]["database"])
            print("  Salesforce: {externalId: '<salesforce source>://<org name>~com.infa.odin.models.Salesforce.Organization'}")
            return
        targets = {cfg["connections"]["warehouse"].upper(): {
            "externalId": "%s://%s~com.infa.odin.models.relational.Database" % (snow, cfg["snowflake"]["database"]), "origin": snow,
            "isCaseSensitive": False, "location": "%s://%s/%s" % (snow, snow, cfg["snowflake"]["database"])}}
        orgs = [x for x in search_all(ctx, {"query": {"bool": {"must": [{"term": {"core.origin": crm}}]}}})
                if (x.get("core.classType") or "").endswith("Salesforce.Organization")]
        if orgs:
            targets[cfg["connections"]["crm"].upper()] = {"externalId": orgs[0]["core.externalId"], "origin": crm,
                                                          "isCaseSensitive": False, "location": orgs[0].get("core.location")}
        for r in refs(ctx, lin):
            name, tgt = str(r.get("core.name")).upper(), None
            tgt = next((v for k, v in targets.items() if k == name or k in name), None)
            print("REF %-34s resolved=%-10s -> %s" % (r.get("core.name"), r.get("core.resolvedStatus"), (tgt or {}).get("externalId")))
            if a.cmd == "merge" and tgt and not r.get("core.resolvedStatus"):
                body = {"sourceRootAsset": {"externalId": r["core.externalId"], "origin": lin, "location": r["core.location"]},
                        "targetRootAsset": [tgt], "initialAssignment": True, "modifyAssignment": False}
                ctx.write("MERGE " + r.get("core.name"), "cdgc", "POST",
                          "/ccgf-contentv2/api/v1/assignment/connectionAssignment?operationType=MERGE", body=body)
                st.setdefault("merges", []).append({"body": body, "undo": "operationType=SPLIT"})
    elif a.cmd in ("chain", "feed"):
        views = [a.obj] if a.obj else (g["lineage"]["tableau_views"] if a.cmd == "feed" else [g["lineage"]["start_object"]])
        if ctx.offline:
            print("[OFFLINE] would walk the upstream lineage of", views)
            return
        rows = []
        for v in views:
            for i, e in enumerate(upstream(ctx, st, v), 1):
                print("  %-40s [%s] -> %s [%s]" % (e[0], e[1], e[3], e[4]))
                rows.append((v, i) + e)
        if a.cmd == "feed":
            sys.path.insert(0, str(C.BP / "infra"))
            import snowflake_sql as SQ
            esc = lambda s: str(s or "").replace("'", "''")  # noqa: E731
            now = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
            vals = ",\n".join("('%s','%s',%d,'%s','%s','%s','%s','%s','%s')" % ((now, esc(r[0]), r[1]) + tuple(esc(x) for x in r[2:]))
                              for r in rows)
            sql = "INSERT INTO BID_LINEAGE VALUES\n" + vals
            print("[DRY-RUN] " + sql[:400]) if not (ctx.execute and rows) else print("Snowflake", SQ.run(cfg, sql)[0])
    if not ctx.offline and (ctx.execute or a.cmd == "show"):
        C.save_state(st)


if __name__ == "__main__":
    main()
