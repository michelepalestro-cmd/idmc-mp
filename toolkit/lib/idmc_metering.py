#!/usr/bin/env python3
"""idmc_metering.py - read billed IPU consumption with the asynchronous metering export (read-only, 0 IPU).

  python idmc_metering.py export --start 2026-06-01 --end 2026-07-01 [--job-type SUMMARY|ASSET|PROJECT_FOLDER] --out usage.zip
  python idmc_metering.py status <jobId>

Route (plane v3, header INFA-SESSION-ID; PROVEN, L-IPU-021):
  POST /public/core/v3/license/metering/ExportMeteringData {"jobType","startDate","endDate"} -> 201 {jobId}
  GET  /public/core/v3/license/metering/ExportMeteringData/<jobId>            (poll; also recorded as .../jobs/<jobId>)
  GET  /public/core/v3/license/metering/ExportMeteringData/<jobId>/download   -> a ZIP with one CSV per org
Rules: dates must be full ISO-8601 with a zone (a bare date gives 400 V3API_007; this tool adds T00:00:00Z);
  PROJECT_FOLDER (and ASSET) windows must be 30 days or less (400 LS_298); SUMMARY accepted 33 and 90 days.
  An org can have at most 5 active export jobs; PARTIAL_SUCCESS is downloadable (L-IPU-070). A trial or embedded
  sub-org returns a header-only CSV: then use the labelled activity-log proxy
  (knowledge/13-ipu-cost/02-metering-consumption-exports.md section 5) and say it is an estimate.
The export creates a report job only; it changes no design object or setting and needs no --execute.
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import idmc_http as H  # noqa: E402
from idmc_session import LoginError, Session  # noqa: E402

BASE = "/public/core/v3/license/metering"
DONE = ("SUCCESS", "PARTIAL_SUCCESS", "FAILED", "ERROR", "CANCELLED")


def iso(d):
    return d if "T" in d else d + "T00:00:00Z"


def job_status(S, jid):
    """Read the job; try the ExportMeteringData form first, then the jobs form (both recorded)."""
    for path in (f"{BASE}/ExportMeteringData/{jid}", f"{BASE}/jobs/{jid}"):
        r = S.get("v3", path)
        if r.status == 200:
            j = r.json({}) or {}
            st = j.get("status")
            st = st.get("state") if isinstance(st, dict) else st
            return r, j, str(st or j.get("state") or ""), path
    return r, {}, "", path


def cmd_export(S, a):
    body = {"jobType": a.job_type, "startDate": iso(a.start), "endDate": iso(a.end)}
    print(f"metering export {body} (read-only, 0 IPU)")
    r = S.call("v3", "POST", f"{BASE}/ExportMeteringData", body=body)
    jid = (r.json({}) or {}).get("jobId") if r.ok else None
    if not jid:
        H.die(f"export start HTTP {r.status} {r.head(400)} (V3API_007: date format; LS_147: dates missing; "
              f"LS_298: window over 30 days for this job type)")
    (r, j, state, path), done = H.poll(lambda: job_status(S, jid), lambda v: v[2].upper() in DONE,
                                       interval=20, timeout=a.timeout,
                                       describe=lambda v: f"job {jid}: HTTP {v[0].status} {v[2]}")
    if not done:
        print(f"NOT FINISHED after {a.timeout}s. Read it later (do not start another export):\n"
              f"  python3 idmc_metering.py status {jid}")
        return 1
    if state.upper() not in ("SUCCESS", "PARTIAL_SUCCESS"):
        H.die(f"export {jid} ended {state}: {H.preview(j, 800)}")
    d = S.get("v3", f"{path}/download", headers={"Accept": "*/*"}, timeout=600)
    if d.status != 200 or d.raw[:2] != b"PK":
        H.die(f"download HTTP {d.status}, not a zip: {d.head(200)}")
    H.write_private(a.out, d.raw)
    summarize(d.raw)
    print(f"saved {a.out} (job {jid}, {state})")
    return 0


def summarize(zbytes):
    """Print IPU totals by meter from each CSV; flag header-only files (trial and embedded sub-orgs)."""
    z = zipfile.ZipFile(io.BytesIO(zbytes))
    for name in z.namelist():
        rows = list(csv.DictReader(io.StringIO(z.read(name).decode("utf-8-sig", "replace"))))
        if not rows:
            print(f"  {name}: header only (trial or sub-org): use the labelled activity-log proxy instead")
            continue
        by = {}
        for r in rows:
            try:
                by[r.get("MeterName") or "?"] = by.get(r.get("MeterName") or "?", 0.0) + float(r.get("IPU") or 0)
            except ValueError:
                pass
        print(f"  {name}: {len(rows)} rows, {sum(by.values()):.2f} IPU")
        for m, v in sorted(by.items(), key=lambda kv: -kv[1])[:15]:
            print(f"    {v:12.2f}  {m}")


def main():
    H.safe_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    ex = sub.add_parser("export", help="start the export, poll, download the ZIP (0600) and print IPU by meter")
    ex.add_argument("--start", required=True, help="YYYY-MM-DD or full ISO-8601")
    ex.add_argument("--end", required=True, help="YYYY-MM-DD or full ISO-8601")
    ex.add_argument("--job-type", default="SUMMARY", choices=["SUMMARY", "ASSET", "PROJECT_FOLDER"])
    ex.add_argument("--out", required=True, help="where to save the ZIP (outside the plugin folder)")
    ex.add_argument("--timeout", type=int, default=900)
    st = sub.add_parser("status", help="read one export job")
    st.add_argument("job")
    a = ap.parse_args()
    try:
        S = Session()
        if a.cmd == "export":
            sys.exit(cmd_export(S, a))
        r, j, state, _ = job_status(S, a.job)
        print(f"HTTP {r.status} state={state}\n{H.preview(j, 2000)}")
    except (LoginError, RuntimeError, zipfile.BadZipFile) as e:
        H.die(f"{type(e).__name__}: {e}", 3)


if __name__ == "__main__":
    main()
