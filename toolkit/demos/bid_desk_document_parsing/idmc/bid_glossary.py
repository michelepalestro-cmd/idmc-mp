#!/usr/bin/env python3
"""bid_glossary.py - the Bid Desk business glossary in CDGC: one domain, its terms in the documents' own words, and the
term-to-column links, headless.

    python bid_glossary.py create [--execute --expect-org <orgIdV3>]    # domain + terms (idempotent; registry in state/ids.json)
    python bid_glossary.py publish [--execute ...]   # every term-to-column link in ONE Content Publish (ccgf-contentv2)
    python bid_glossary.py verify                    # read back the domain, the terms (lifecycle Published) and every link
    python bid_glossary.py feed [--execute]          # the terms + links -> Snowflake BID_GLOSSARY (the dashboard's glossary tab)
    python bid_glossary.py undo [--execute ...]      # delete the terms (newest first), then the domain

Content: idmc/templates/governance.json "glossary". A link target is '<SCHEMA>.<TABLE>[.<COLUMN>]' in the catalog source
'<project> - Snowflake'; a target not cataloged yet is skipped and reported (scan first: bid_catalog.py scan).
Calls (PROVEN 2026-10-13; KB CDGC 03, lessons L-CDGC-050/051/052/165/174):
  create  POST https://idmc-api.<domain>/data360/content/v1/assets
          domain {"core.classType":"com.infa.ccgf.models.governance.Domain","summary":{"core.name","core.description"}}
          term   {"core.classType":"com.infa.ccgf.models.governance.BusinessTerm","summary":{...},"parent":{"core.identity":<domain>}}
  publish POST https://cdgc-api.<domain>/ccgf-contentv2/api/v1/publish   header X-INFA-PRODUCT-ID: CDGC
          {"items":[{"operation":"INSERT","elementType":"RELATIONSHIP","fromIdentity":<asset externalId>,"toIdentity":<term
          externalId>,"type":"com.infa.ccgf.models.governance.IClassTechnicalGlossaryBase","sourceIdentityType":"EXTERNAL",
          "targetIdentityType":"EXTERNAL","attributes":{"core.curationStatus":"ACCEPTED","core.channels":["MANUAL"],
          "core.inferred":false}}]}  -> one Content Publish Task for all links; read each item's statusCode
  verify  GET /data360/search/v1/assets/<identity>?scheme=internal&segments=glossary
  undo    DELETE /data360/content/v1/assets/<identity>?scheme=internal (terms first, then the domain)
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
import bid_common as C  # noqa: E402

DOMAIN, TERM = "com.infa.ccgf.models.governance.Domain", "com.infa.ccgf.models.governance.BusinessTerm"
REL = "com.infa.ccgf.models.governance.IClassTechnicalGlossaryBase"
CONTENT = "/data360/content/v1/assets"


def search_all(ctx, query):
    import idmc_cdgc as G
    return G.search(ctx.S, query, size=200, all_pages=True)[0]


def by_class(ctx, cls):
    return [] if ctx.offline else search_all(ctx, {"query": {"term": {"core.classType": cls}}})


def asset_map(ctx, snow_src):
    out = {}
    if ctx.offline:
        return out
    for x in search_all(ctx, {"query": {"bool": {"must": [{"term": {"core.origin": snow_src}}, {"term": {"elementType": "OBJECT"}}]}}}):
        leaf = x.get("core.classType", "").split(".")[-1]
        parts = [p for p in x.get("core.externalId", "").split("://", 1)[-1].split("~")[0].split("/") if p]
        if leaf in ("Table", "View") and len(parts) >= 3:
            out["%s.%s" % (parts[-2], parts[-1])] = (x["core.identity"], x.get("core.externalId"))
        elif leaf in ("Column", "ViewColumn") and len(parts) >= 4:
            out["%s.%s.%s" % (parts[-3], parts[-2], parts[-1])] = (x["core.identity"], x.get("core.externalId"))
    return out


def main():
    ap = C.parser(__doc__)
    ap.add_argument("cmd", choices=["create", "publish", "verify", "feed", "undo"])
    a = ap.parse_args()
    ctx = C.Ctx(a)
    cfg, st = ctx.cfg, C.state()
    g = C.render(C.template("governance.json"), cfg)["glossary"]
    reg = st.setdefault("glossary", {})
    dname = g["domain"]["name"]
    if a.cmd == "create":
        if "domain" not in reg:
            have = [x for x in by_class(ctx, DOMAIN) if x.get("core.name") == dname]
            if have:
                reg["domain"] = {"identity": have[0]["core.identity"], "ext": have[0].get("core.externalId"), "reused": True}
            else:
                r = ctx.write("create domain " + dname, "d360", "POST", CONTENT,
                              body={"core.classType": DOMAIN, "summary": {"core.name": dname, "core.description": g["domain"]["description"]}})
                if C.ok(r):
                    d = r.json({})
                    reg["domain"] = {"identity": d.get("core.identity"), "ext": d.get("core.externalId")}
        dom = (reg.get("domain") or {}).get("identity", "<domain identity>")
        terms = reg.setdefault("terms", {})
        existing = by_class(ctx, TERM)
        for t in g["terms"]:
            if t["name"] in terms:
                continue
            have = [x for x in existing if x.get("core.name") == t["name"] and dom in str(x.get("core.location", ""))]
            if have:
                terms[t["name"]] = {"identity": have[0]["core.identity"], "ext": have[0].get("core.externalId"), "reused": True}
                continue
            r = ctx.write("create term " + t["name"], "d360", "POST", CONTENT,
                          body={"core.classType": TERM, "summary": {"core.name": t["name"], "core.description": t["definition"]},
                                "parent": {"core.identity": dom}})
            if C.ok(r):
                d = r.json({})
                terms[t["name"]] = {"identity": d.get("core.identity"), "ext": d.get("core.externalId")}
                time.sleep(0.5)
        print("terms in registry: %d of %d" % (len(terms), len(g["terms"])))
    elif a.cmd == "publish":
        snow = (st.get("catalog") or {}).get(cfg["idmc"]["project"] + " - Snowflake", "<snowflake source id>")
        amap = asset_map(ctx, snow)
        links, todo, miss = reg.setdefault("links", {}), [], []
        for t in g["terms"]:
            tv = (reg.get("terms") or {}).get(t["name"]) or {}
            for target in t.get("links", []):
                key = "%s|%s" % (t["name"], target)
                if key in links:
                    continue
                ai, ext = amap.get(target) or (None, "<externalId of %s>" % target if ctx.offline else None)
                if not ext or (not tv.get("ext") and not ctx.offline):
                    miss.append((key, "term not created" if not tv.get("ext") else "asset not in catalog"))
                    continue
                todo.append((key, ai, ext, tv.get("ext", "<term externalId>")))
        print("links to publish: %d (not linkable now: %d)" % (len(todo), len(miss)))
        for m in miss:
            print("  skip:", m)
        if todo:
            body = {"items": [{"operation": "INSERT", "elementType": "RELATIONSHIP", "fromIdentity": ext, "toIdentity": bt, "type": REL,
                               "sourceIdentityType": "EXTERNAL", "targetIdentityType": "EXTERNAL",
                               "attributes": {"core.curationStatus": "ACCEPTED", "core.channels": ["MANUAL"], "core.inferred": False}}
                              for (_k, _a, ext, bt) in todo]}
            r = ctx.write("publish %d links" % len(todo), "cdgc", "POST", "/ccgf-contentv2/api/v1/publish", body=body,
                          headers={"X-INFA-PRODUCT-ID": "CDGC"})
            items = ((r.json({}) or {}).get("items") or []) if r is not None else []
            for (key, ai, ext, _bt), it in zip(todo, items):
                if it.get("statusCode") in (200, 201):
                    links[key] = {"asset": ai, "ext": ext}
                else:
                    print("  item failed %s: %s" % (key, str(it)[:200]))
    elif a.cmd == "verify":
        dom = (reg.get("domain") or {}).get("identity")
        mine = {x["core.identity"]: x for x in by_class(ctx, TERM) if dom and dom in str(x.get("core.location", ""))}
        ok = sum(1 for n, v in (reg.get("terms") or {}).items()
                 if mine.get(v["identity"], {}).get("core.name") == n and mine[v["identity"]].get("core.assetLifecycle") == "Published")
        print("domain %s: %s | terms Published %d of %d | links in registry %d" % (dname, "found" if dom else "MISSING", ok,
                                                                                  len(g["terms"]), len(reg.get("links") or {})))
    elif a.cmd == "feed":
        defs = {t["name"]: t["definition"] for t in g["terms"]}
        rows = [(n, defs.get(n, ""), k.split("|", 1)[1]) for k in (reg.get("links") or {}) for n in [k.split("|", 1)[0]]]
        rows += [(n, defs[n], "") for n in defs if not any(r[0] == n for r in rows)]
        esc = lambda s: str(s).replace("'", "''")  # noqa: E731
        now = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        sql = "INSERT INTO BID_GLOSSARY VALUES\n" + ",\n".join(
            "('%s','%s','%s','%s','Published','%s')" % (now, esc(dname), esc(n), esc(d), esc(l)) for n, d, l in rows)
        if not ctx.execute:
            print("[DRY-RUN] Snowflake: %s ... (%d rows)" % (sql[:300], len(rows)))
        else:
            sys.path.insert(0, str(C.BP / "infra"))
            import snowflake_sql as SQ
            print("Snowflake", SQ.run(cfg, sql)[0])
    else:
        order = list(reversed(list((reg.get("terms") or {}).items())))
        for n, v in order:
            if v.get("reused"):
                print("keep %s (it existed before this build)" % n)
                continue
            ctx.write("delete term " + n, "d360", "DELETE", "%s/%s?scheme=internal" % (CONTENT, v["identity"]))
        if reg.get("domain"):
            ctx.write("delete domain " + dname, "d360", "DELETE", "%s/%s?scheme=internal" % (CONTENT, reg["domain"]["identity"]))
        if ctx.execute:
            st.pop("glossary", None)
    if ctx.execute:
        C.save_state(st)


if __name__ == "__main__":
    main()
