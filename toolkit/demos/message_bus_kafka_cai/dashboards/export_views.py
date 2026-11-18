#!/usr/bin/env python3
"""export_views.py - export the demo's dashboard views to CSV for any BI tool (optional; standard library only).

  python dashboards/export_views.py [--out build/dash]

Views (PostgREST, read only): dash_flow (messages per minute per stage / target / status), dash_error_queue (the
hospital by reason and status), targets (rows per simulated system), po_status (each PO in merchandising vs warehouse).
Point a BI tool at the CSVs, or directly at the Postgres views mbr_api.* with a read-only login. Suggested pages
(one workbook, one tab per topic): 1 the flow (old bus vs Kafka + CAI, labelled), 2 messages and outcomes per minute,
3 the hospital (open / replayed / resolved / dead by reason), 4 the CAI API calls per message (README section 6),
5 the nightly batch rows in Oracle. Read live numbers only; never type a number into a dashboard.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "verify"))
import mbr_msgs as M  # noqa: E402

VIEWS = ["dash_flow", "dash_error_queue", "targets", "po_status"]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__.split("\n\n", 1)[1])
    ap.add_argument("--out", default=str(M.CFG.BUILD / "dash"))
    ap.add_argument("--config")
    a = ap.parse_args()
    cfg = M.CFG.load(a.config)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for v in VIEWS:
        st, rows = M.api(cfg, f"/{v}")
        if st != 200 or not isinstance(rows, list):
            print(f"{v}: HTTP {st}")
            continue
        p = out / f"{v}.csv"
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["empty"])
            w.writeheader()
            w.writerows(rows)
        print(f"{v}: {len(rows)} rows -> {p}")


if __name__ == "__main__":
    main()
