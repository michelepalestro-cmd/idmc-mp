#!/usr/bin/env python3
"""bid_demo.py - the demo loop in one command: run, what-if, reset, verify, status, publish.

    python bid_demo.py run     [--execute --expect-org <orgIdV3>]   # taskflow '<project> - Run' = tonight's batch, now (~4 min)
    python bid_demo.py whatif  [bid|sig|both] [--execute ...]       # CRM: the completed copies as NEW versions, then run
    python bid_demo.py reset   [--execute ...]                      # taskflow '<project> - Reset': the originals back as new versions
                                                                    # (nothing deleted), then the whole pipeline = the starting point
    python bid_demo.py verify  [start|whatif]                       # Gold against config "expected" (Snowflake SQL API, read-only)
    python bid_demo.py status                                       # CRM file versions + the decisions now (read-only)
    python bid_demo.py publish [--execute]                          # lineage + glossary feeds -> Snowflake, then the Tableau workbook

Expected with the synthetic samples (config "expected"):
  start   ECPC-2031-07 PRICE THE BID     EUSD-31-RFQ-04 SIGN THE FORM
  whatif  ECPC-2031-07 FIX 2 ITEMS       EUSD-31-RFQ-04 SUBMIT THE FORM
          (the priced copy has one price with 3 decimals and one line without a brand: the DQ rules catch both)
Every run is one job of the org's job budget and wakes the warehouse. Nothing here runs on its own.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
import bid_common as C  # noqa: E402

HERE = Path(__file__).resolve().parent


def sub(script, *args, gate=None):
    cmd = [sys.executable, str(script)] + [str(x) for x in args] + (gate or [])
    print(">>", " ".join(Path(c).name if i == 1 else c for i, c in enumerate(cmd[1:], 1)), flush=True)
    return subprocess.call(cmd)


def decisions(cfg):
    sys.path.insert(0, str(C.BP / "infra"))
    import snowflake_sql as SQ
    return {r["SOLICITATION_NO"]: r for r in SQ.rows(cfg, "SELECT SOLICITATION_NO, AGENCY, DECISION, DQ_SCORE, DETAIL, VERSION_NUMBER "
                                                          "FROM BID_GLD_READINESS ORDER BY SORT_ORDER")}


def main():
    ap = C.parser(__doc__)
    ap.add_argument("cmd", choices=["run", "whatif", "reset", "verify", "status", "publish"])
    ap.add_argument("arg", nargs="?")
    a = ap.parse_args()
    C.H.safe_console()
    cfg = C.load_config(a.config)
    gate = (["--execute", "--expect-org", a.expect_org] if a.execute and a.expect_org else (["--execute"] if a.execute else []))
    gate += (["--config", a.config] if a.config else []) + (["--offline"] if a.offline else [])
    sfgate = (["--execute"] if a.execute else []) + (["--config", a.config] if a.config else []) + (["--offline"] if a.offline else [])
    if a.cmd == "run":
        sys.exit(sub(HERE / "bid_taskflows.py", "run", "run", gate=gate))
    if a.cmd == "reset":
        sys.exit(sub(HERE / "bid_taskflows.py", "run", "reset", gate=gate))
    if a.cmd == "whatif":
        rc = sub(C.BP / "infra" / "sf_files.py", "whatif", a.arg or "both", gate=sfgate)
        sys.exit(rc or sub(HERE / "bid_taskflows.py", "run", "run", gate=gate))
    if a.cmd == "publish":
        rc = sub(HERE / "bid_catalog.py", "feed", gate=gate) or sub(HERE / "bid_glossary.py", "feed", gate=gate)
        sys.exit(rc or sub(C.BP / "dashboards" / "bid_tableau.py", "publish", gate=sfgate))
    if a.offline:
        print("[OFFLINE] %s reads BID_GLD_READINESS through the Snowflake SQL API and compares with config expected.%s"
              % (a.cmd, a.arg or "start"))
        return
    if a.cmd == "status":
        sub(C.BP / "infra" / "sf_files.py", "status", gate=(["--config", a.config] if a.config else []))
        for k, r in decisions(cfg).items():
            print("%-16s %-40s %-16s DQ %s%%  v%s  %s" % (k, r["AGENCY"], r["DECISION"], r["DQ_SCORE"], r["VERSION_NUMBER"], r["DETAIL"]))
        return
    want, got, bad = cfg["expected"][a.arg or "start"], decisions(cfg), 0
    for sol, dec in want.items():
        g = (got.get(sol) or {}).get("DECISION")
        bad += g != dec
        print("%-4s %-16s expected %-16s got %s" % ("OK" if g == dec else "FAIL", sol, dec, g))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
