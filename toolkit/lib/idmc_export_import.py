#!/usr/bin/env python3
"""idmc_export_import.py - v3 migration lifecycle: export -> poll -> download, and upload -> start -> poll ->
per-object result -> log, with a REUSE / OVERWRITE choice and a read-back of what landed.

  python idmc_export_import.py export --id <frsGuid> [--id ...] [--ids-file f] [--no-deps] --out pkg.zip
  python idmc_export_import.py import pkg.zip --mode REUSE|OVERWRITE [--include <guid> ...]   (dry-run)
  python idmc_export_import.py import pkg.zip --mode REUSE --execute --expect-org <orgIdV3>
  python idmc_export_import.py status <jobId> --kind export|import      python idmc_export_import.py log <importJobId>

Routes (plane v3, header INFA-SESSION-ID; all PROVEN 2026-09 against production orgs):
  POST /public/core/v3/export {"name","objects":[{"id":"<frsGuid>","includeDependencies":true}]} -> {id}
  GET  /public/core/v3/export/<id>[?expand=objects] -> status.state   GET /export/<id>/package (Accept application/zip)
  POST /public/core/v3/import/package  multipart, field 'package' -> {jobId, checksumValid}   (staged, not committed)
  POST /public/core/v3/import/<jobId> {"name","importSpecification":{"defaultConflictResolution":..,"includeObjects":[..]}}
       (the start route drops '/package'; /import/package/<jobId> is 404)
  GET  /public/core/v3/import/<jobId>[?expand=objects]   GET /public/core/v3/import/<jobId>/log (Accept */*)
Safety: export changes nothing in the org (allowed without --execute). import is a write: dry-run by default; it
  previews each packaged object as NEW or EXISTS (by path lookup; connections and runtime
  environments by name over v2) and needs --execute + --expect-org. Pass --expect-org on the dry run too, so the
  preview is proven to read the target org. The import and log commands exit 1 unless the job ended SUCCESSFUL;
  on a poll timeout, read the job back with `status` and never start a second import. An upload
  with checksumValid=false is never started.
Traps: bare string ids -> 400 V3API_007; exporting by a CAI process GUID (not the object id) -> MigrationSvc_034;
  Add-On Bundle templates can answer 403 MigrationSvc_038; application/json on the upload -> 404 MigrationSvc_025;
  an empty or hand-built multipart -> MigrationSvc_030; a changed file with a stale checksum -> MigrationSvc_073;
  a dangling objectRef -> MigrationSvc_031 with empty details. The import is ALL-OR-NOTHING and includeObjects
  does not exclude objects from validation: drop failing objects from the package (idmc_package_edit.py drop).
  objectSpecification returned V3API_007 in every shape tried: use name-based REUSE. The import drops tags
  (re-tag with TagObjects), creates no schedules, publishes no CAI asset and deploys no DBMI task.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
import urllib.parse
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import idmc_http as H  # noqa: E402
from idmc_objects import lookup_path  # noqa: E402
from idmc_session import LoginError, Session  # noqa: E402

RUNNING = ("IN_PROGRESS", "QUEUED", "NOT_STARTED", None, "")


def job_state(S, kind, jid, expand=False):
    r = S.get("v3", f"/public/core/v3/{kind}/{jid}" + ("?expand=objects" if expand else ""))
    j = r.json({}) if r.ok else {}
    j = j if isinstance(j, dict) else {}
    st = j.get("status")                      # usually status.state; some answers carry a top-level state
    return r, j, (st.get("state") if isinstance(st, dict) else st) or j.get("state")


def wait_job(S, kind, jid, timeout=1800):
    (r, j, state), done = H.poll(lambda: job_state(S, kind, jid), lambda v: v[0].status != 200 or v[2] not in RUNNING,
                                 interval=5, timeout=timeout, describe=lambda v: f"{kind} {jid}: HTTP {v[0].status} {v[2]}")
    return j, state, done


def package_objects(zbytes):
    z = zipfile.ZipFile(io.BytesIO(zbytes))
    meta = json.loads(z.read("exportMetadata.v2.json"))
    return meta.get("exportedObjects") or [], z.namelist()


def cmd_export(S, a):
    ids = list(a.id or [])
    if a.ids_file:
        ids += [ln.strip() for ln in open(a.ids_file, encoding="utf-8") if ln.strip() and not ln.startswith("#")]
    if not ids:
        H.die("give --id and/or --ids-file")
    body = {"name": a.name or f"export_{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}",
            "objects": [{"id": i, "includeDependencies": not a.no_deps} for i in ids]}
    print(f"export {len(ids)} object(s), includeDependencies={not a.no_deps} (read-only for the org)")
    r = S.call("v3", "POST", "/public/core/v3/export", body=body)
    jid = (r.json({}) or {}).get("id") if r.ok else None
    if not jid:
        H.die(f"export start HTTP {r.status} {r.head(300)}")
    j, state, done = wait_job(S, "export", jid)
    if state != "SUCCESSFUL":
        H.die(f"export {jid} ended {state}: {H.preview(j, 800)}")
    r = S.get("v3", f"/public/core/v3/export/{jid}/package", headers={"Accept": "application/zip"}, timeout=600)
    if r.status != 200 or r.raw[:2] != b"PK":
        H.die(f"package download HTTP {r.status}, not a zip: {r.head(200)}")
    H.write_private(a.out, r.raw)            # 0600: packages can hold plaintext secrets
    objs, names = package_objects(r.raw)
    by = {}
    for o in objs:
        by[o.get("objectType")] = by.get(o.get("objectType"), 0) + 1
    print(f"saved {a.out}: {len(r.raw)} bytes, {len(names)} files, {len(objs)} objects {by} (export id {jid})")
    print("NOTE: packages can hold plaintext secrets (e.g. CAI connections saved with encrypted=false): keep them "
          "outside the plugin and out of any repo.")


def preview_import(S, objs, mode, include):
    new = exists = sysdeps = 0
    for o in objs:
        path, name, typ = (o.get("path") or ""), o.get("objectName"), o.get("objectType")
        mark = "" if not include or o.get("objectGuid") in include else "  (not in --include)"
        if not path.startswith("/Explore"):
            sysdeps += 1
            print(f"  SYS {sys_state(S, typ, name):7} {typ:22} {name}{mark}")
            continue
        full = (path[len("/Explore"):].strip("/") + "/" + name).strip("/")
        if typ in ("Project", "Folder"):
            print(f"  {'CONT':6} {typ:22} {full}")
            continue
        _, hits = lookup_path(S, full, typ)
        if hits:
            exists += 1
            verb = "OVERWRITE" if mode == "OVERWRITE" else "REUSE"
            print(f"  {verb:9} {typ:22} {full}  (target id {hits[0].get('id')}){mark}")
        else:
            new += 1
            print(f"  NEW       {typ:22} {full}{mark}")
    print(f"  => {new} new, {exists} existing ({mode}), {sysdeps} SYS dependencies (connections, runtime environments)")
    if sysdeps:
        print("  WARNING: SYS objects are matched by NAME in the target and are not changed by the import. Each one must"
              " already exist there and point at THIS org's systems (prod hosts and databases, not dev): test every"
              " connection and compare its host and database after the import (L-MIG-082, L-MIG-103).")


def sys_state(S, typ, name):
    """Read-only check that a packaged connection or runtime environment exists in the target, by name over v2.
    Routes reported in public code (L-MIG-103, L-AGENT-130); a missing connection can answer 404 or 403 APP_13436."""
    route = {"Connection": "connection", "AgentGroup": "runtimeEnvironment"}.get(typ)
    if not route or not name:
        return "?"
    r = S.get("v2", f"/api/v2/{route}/name/{urllib.parse.quote(str(name), safe='')}")
    if r.status == 200:
        return "EXISTS"
    if r.status == 404 or (r.status == 403 and "APP_13436" in r.head(400)):
        return "MISSING"
    return f"HTTP{r.status}"


def cmd_import(S, a, gate):
    zbytes = open(a.package, "rb").read()
    if zbytes[:2] != b"PK":
        H.die("not a zip file")
    objs, _ = package_objects(zbytes)
    print(f"package {a.package}: {len(objs)} objects, mode {a.mode}" + (f", includeObjects {a.include}" if a.include else ""))
    preview_import(S, objs, a.mode, set(a.include or []))
    if a.mode == "OVERWRITE":
        print("  OVERWRITE replaces the target copy of every matching object; the import is all-or-nothing.")
    raw, ctype = H.multipart("package", os.path.basename(a.package), zbytes)
    up = gate.send("upload package", "v3", "POST", "/public/core/v3/import/package", raw=raw, ctype=ctype, timeout=600)
    if up is None:
        print("DRY-RUN: nothing uploaded. Re-run with --execute --expect-org <orgIdV3>.")
        return
    u = up.json({}) or {}
    if not up.ok or not u.get("jobId"):
        H.die(f"upload failed HTTP {up.status} {up.head(300)}")
    if u.get("checksumValid") is False:
        H.die(f"checksumValid=false for staged job {u['jobId']}: fix exportPackage.chksum; the import was NOT started")
    spec = {"defaultConflictResolution": a.mode}
    if a.include:
        spec["includeObjects"] = a.include
    body = {"name": a.name or f"import_{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}", "importSpecification": spec}
    st = gate.send("start import", "v3", "POST", f"/public/core/v3/import/{u['jobId']}", body=body)
    if not st or not st.ok:
        H.die("import start failed; the staged upload was not committed")
    return report(S, u["jobId"])


def report(S, jid):
    """Print the job's result, per-object outcome and log. Returns the exit code: 0 only for SUCCESSFUL."""
    j, state, done = wait_job(S, "import", jid)
    print(f"import {jid}: {state}" + ("" if done else " (poll timeout)"), H.preview((j or {}).get("status"), 400))
    det = ((j or {}).get("error") or {}).get("details") or []
    roots = [x.get("message", "") for x in det if "skipped because of previous failures" not in x.get("message", "")]
    for m in roots[:30]:
        print("  ROOT FAILURE:", m[:500])
    _, jx, _ = job_state(S, "import", jid, expand=True)
    for o in (jx or {}).get("objects") or []:
        so, to = o.get("sourceObject") or {}, o.get("targetObject") or {}
        print(f"  {str(o.get('status'))[:60]:60} {so.get('name')} -> target id {to.get('id')}")
    lg = S.get("v3", f"/public/core/v3/import/{jid}/log", headers={"Accept": "*/*"})
    print(f"  log HTTP {lg.status}:", lg.text[-2500:] if lg.ok else lg.head(200))
    if done and state == "SUCCESSFUL":
        return 0
    if not done:
        print(f"NOT FINISHED: the job may still be running. Do NOT import again; read it back first:\n"
              f"  python3 idmc_export_import.py status {jid} --kind import")
    else:
        print(f"IMPORT {state}: read the ROOT FAILURE lines above; nothing is promoted until the state is SUCCESSFUL.\n"
              f"  Re-read later with: python3 idmc_export_import.py status {jid} --kind import")
    return 1


def main():
    H.safe_console()
    ap = argparse.ArgumentParser(description="v3 export/import lifecycle")
    sub = ap.add_subparsers(dest="cmd", required=True)
    ex = sub.add_parser("export")
    ex.add_argument("--id", action="append")
    ex.add_argument("--ids-file")
    ex.add_argument("--no-deps", action="store_true")
    ex.add_argument("--name")
    ex.add_argument("--out", required=True)
    im = H.add_gate_args(sub.add_parser("import"))
    im.add_argument("package")
    im.add_argument("--mode", required=True, choices=["REUSE", "OVERWRITE"])
    im.add_argument("--include", action="append", help="includeObjects guid (repeat)")
    im.add_argument("--name")
    stt = sub.add_parser("status")
    stt.add_argument("job")
    stt.add_argument("--kind", required=True, choices=["export", "import"])
    lg = sub.add_parser("log")
    lg.add_argument("job")
    a = ap.parse_args()
    try:
        S = Session()
        if a.cmd == "export":
            cmd_export(S, a)
        elif a.cmd == "import":
            gate = H.WriteGate(a, S)
            gate.guard()
            sys.exit(cmd_import(S, a, gate) or 0)
        elif a.cmd == "status":
            r, j, state = job_state(S, a.kind, a.job, expand=True)
            print(f"HTTP {r.status} state={state}\n{H.preview(j, 4000)}")
        else:
            sys.exit(report(S, a.job))
    except (LoginError, RuntimeError, KeyError, zipfile.BadZipFile) as e:
        H.die(f"{type(e).__name__}: {e}", 3)


if __name__ == "__main__":
    main()
