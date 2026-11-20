#!/usr/bin/env python3
"""bid_verify.py - smoke and end-to-end checks of the Bid Desk build.

    python bid_verify.py offline        # no login: templates parse, every ${...} resolves from config, SQL splits, sample PDFs
                                        # are the generator's output, the specs' rule specs exist in dq.json, mappings 1, 1b, 3a,
                                        # 3b, 4, 5 lint clean + compile with toolkit/mapgen (in memory), decisions consistent
    python bid_verify.py idmc           # live, read-only: project + 5 folders, 3 connections, 2 CLAIRE models, 7 rule specs,
                                        # 3 profiles, 8 tasks, 2 taskflows (and whether a schedule is attached)
    python bid_verify.py data           # live, read-only (Snowflake SQL API): row counts per layer, Gold decisions, scorecard,
                                        # lineage and glossary feeds (each Tableau tab has rows)
    python bid_verify.py all            # idmc + data
Exit 1 when a check fails. Nothing here writes anywhere.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "idmc" / "lib"))
import bid_common as C  # noqa: E402

FAIL = []


def check(ok, what):
    print("%-4s %s" % ("OK" if ok else "FAIL", what))
    if not ok:
        FAIL.append(what)


def offline(cfg):
    sys.path.insert(0, str(C.BP / "infra"))
    import snowflake_sql as SQ
    for p in sorted((C.TEMPLATES).rglob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except ValueError as e:
            check(False, "%s parses (%s)" % (p.name, e))
            continue
        left = sorted(set(m for m in re.findall(r"\$\{([^}]+)\}", json.dumps(C.render(d, cfg, {})))
                          if not m.startswith(("state:", "env:"))))
        check(not left, "%s: every config placeholder resolves %s" % (p.relative_to(C.BP), left or ""))
    for p in sorted((C.BP / "infra" / "snowflake").glob("*.sql")):
        text = C.render(p.read_text(encoding="utf-8"), cfg)
        n = len(SQ.split_sql(text))
        check(n > 0 and "${" not in text, "%s: %d statements, placeholders filled" % (p.name, n))
    rc = subprocess.call([sys.executable, str(C.BP / "infra" / "make_sample_pdfs.py"), "--check"], stdout=subprocess.DEVNULL)
    check(rc == 0, "sample PDFs are exactly the generator's output (infra/make_sample_pdfs.py --check)")
    for ag in cfg["salesforce"]["agencies"]:
        for k in ("original", "whatif"):
            check((C.BP / ag[k]).exists(), "sample file present: %s" % Path(ag[k]).name)
    rules = {r["name"] for r in C.template("dq.json")["rules"]}
    used = set()
    for p in (C.TEMPLATES / "mappings").glob("*.json"):
        used |= set(re.findall(r"\$\{state:rulespecs\.([^}]+)\}", p.read_text(encoding="utf-8")))
    check(used <= rules, "every rule spec a mapping uses is defined in dq.json %s" % sorted(used - rules))
    for prof in C.template("dq.json")["profiles"]:
        check(all(b[0] in rules for b in prof["bindings"]), "profile %r binds defined rules" % prof["name"])
    sys.path.insert(0, str(C.BP / "idmc"))
    import bid_mappings as BM
    res = BM.compile_specs(cfg, {}, offline=True, quiet=True)          # in memory: lint + compile + package, no files
    for stem, ntx, nlk, ne, nw, _ in res:
        check(ne == 0 and ntx > 0, "mapping %s lints clean and compiles with toolkit/mapgen (%d transformations, %d links%s)"
              % (BM.code(stem), ntx, nlk, ", %d warning(s)" % nw if nw else ""))
    check(sorted(BM.code(r[0]) for r in res) == sorted(BM.BUILDABLE), "the generator builds mappings %s" % ", ".join(BM.BUILDABLE))
    g = json.loads((C.TEMPLATES / "mappings" / "m_bid_4_bid_readiness.json").read_text(encoding="utf-8"))
    expr = json.dumps(g)
    for phase in cfg["expected"].values():
        for dec in phase.values():
            stem = re.sub(r"^FIX \d+ ITEMS?$", "FIX ", dec)          # 'FIX n ITEMS' is built from the count
            check(("'%s" % stem) in expr, "decision %r can be produced by mapping 4" % dec)


def idmc(ctx):
    cfg, proj = ctx.cfg, ctx.cfg["idmc"]["project"]
    projs = [o for o in C.v3_objects(ctx, "Project") if o.get("path") == proj]
    check(len(projs) == 1, "project %r exists" % proj)
    folders = {o["path"] for o in C.v3_objects(ctx, "Folder", proj + "/")}
    check(all("%s/%s" % (proj, f) in folders for f in cfg["idmc"]["folders"].values()), "the 5 stage folders exist")
    import urllib.parse
    for k, n in cfg["connections"].items():
        r = ctx.read("v2", "/api/v2/connection/name/" + urllib.parse.quote(n, safe=""))
        check(C.ok(r), "connection %r" % n)
    models = C.v3_objects(ctx, "SAAS_STRUCTURE_DISCOVERY", proj + "/")
    check(len(models) >= 2, "2 CLAIRE models (found %d)" % len(models))
    rs = C.v3_objects(ctx, "RULE_SPECIFICATION", proj + "/")
    check(len(rs) >= 7, "7 rule specifications (found %d)" % len(rs))
    r = ctx.read("profiling", "/profiling-service/api/v1/profile?limit=200")
    pn = [p for p in (r.json([]) if r is not None else []) if str(p.get("name", "")).startswith(proj.replace(".", "_"))]
    check(len(pn) >= 3, "3 Data Profiling profiles (found %d)" % len(pn))
    r = ctx.read("v2", "/api/v2/mttask")
    tn = [t for t in (r.json([]) if r is not None else []) if str(t.get("name", "")).startswith(proj + " - ")]
    check(len(tn) >= 8, "8 mapping tasks (found %d)" % len(tn))
    r = ctx.read("v2", "/api/v2/workflow")
    wf = {w.get("name"): w for w in (r.json([]) if r is not None else [])}
    for n in ("%s - Run" % proj, "%s - Reset" % proj):
        check(n in wf, "taskflow %r" % n)
    if "%s - Run" % proj in wf:
        d = ctx.read("v2", "/api/v2/workflow/" + wf["%s - Run" % proj]["id"]).json({})
        print("     schedule attached to Run:", d.get("scheduleId") or "none (as intended until the owner OKs it)")


def data(cfg):
    sys.path.insert(0, str(C.BP / "infra"))
    import snowflake_sql as SQ
    counts = {"BID_BRZ_SF_DOCUMENT": 2, "BID_BRZ_BID_PACKET": 1, "BID_BRZ_SIGNATURE_PAGE": 1, "BID_SLV_BID_LINES": 8,
              "BID_SLV_REQUIRED_FIELDS": 20, "BID_GLD_READINESS": 2, "BID_DQ_SCORECARD": 1, "BID_LINEAGE": 1, "BID_GLOSSARY": 1}
    for t, low in counts.items():
        n = int(SQ.rows(cfg, "SELECT COUNT(*) AS N FROM %s" % t)[0]["N"])  # nosec B608  # table names are code constants
        check(n >= low, "%s has rows (%d, expect >= %d)" % (t, n, low))
    for v in ("BID_V_BI_DECISIONS", "BID_V_BI_BID_LINES", "BID_V_BI_FIELDS", "BID_V_BI_DQ", "BID_V_BI_LINEAGE", "BID_V_BI_GLOSSARY",
              "BID_V_BI_PIPELINE", "BID_V_BI_PARSING"):
        n = int(SQ.rows(cfg, "SELECT COUNT(*) AS N FROM %s" % v)[0]["N"])  # nosec B608  # view names are code constants
        check(n > 0, "Tableau view %s is not blank (%d rows)" % (v, n))
    got = {r["SOLICITATION_NO"]: r["DECISION"] for r in SQ.rows(cfg, "SELECT SOLICITATION_NO, DECISION FROM BID_GLD_READINESS")}
    phase = next((k for k, want in cfg["expected"].items() if all(got.get(s) == d for s, d in want.items())), None)
    check(phase is not None, "Gold decisions match a known phase (%s): %s" % (phase, got))


def main():
    ap = C.parser(__doc__)
    ap.add_argument("what", choices=["offline", "idmc", "data", "all"])
    a = ap.parse_args()
    if a.what == "offline":
        C.H.safe_console()
        offline(C.load_config(a.config))
    else:
        ctx = C.Ctx(a)
        if a.what in ("idmc", "all"):
            if ctx.offline:
                C.H.die("idmc checks need IDMC credentials (or run: offline)")
            idmc(ctx)
        if a.what in ("data", "all"):
            data(ctx.cfg)
    print("%d check(s) failed" % len(FAIL) if FAIL else "ALL CHECKS PASSED")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
