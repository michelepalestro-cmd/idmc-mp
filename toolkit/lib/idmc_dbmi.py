#!/usr/bin/env python3
"""idmc_dbmi.py - Database Ingestion (DBMI / CDC) tasks headless on the <pod>-ing plane: list, details, status,
create, deploy, start / stop / resume / undeploy, and delete (FRS) once undeployed.

  python idmc_dbmi.py list [--grep x]              python idmc_dbmi.py details <taskId> [--save f.json]
  python idmc_dbmi.py status <taskId>
  python idmc_dbmi.py create --spec task.json      (dry-run; --execute --expect-org <orgIdV3>)
  python idmc_dbmi.py deploy|start|stop|resume|undeploy <taskId> [--job-id N] [--no-wait]   (dry-run by default)
  python idmc_dbmi.py delete <taskId> --frs-id <frsId>   (only when the job is undeployed; dry-run by default)

Routes: host https://<pod>-ing.<domain>.informaticacloud.com, headers IDS-SESSION-ID + INFA-SESSION-ID + icSessionId
  (the v2 id). PROVEN 2026-09 (production CDC cutover, both orgs):
  POST /dbmi/public/api/v2/task/create  <plain task JSON>  -> {taskId (numeric), frsId}
  POST /dbmi/public/api/v2/task/deploy/<taskId>            -> data.jobId (or jobId); an empty body is enough
  POST /dbmi/public/api/v2/job/start | stop | resume | undeploy  {"jobId": <int>}
  GET  /dbmi/api/v1/task/<taskId>/job -> status (processing_deploy, deployed, running, stopped, failed, undeployed),
       runId (= the job id)        GET /dbmi/public/api/v2/task/details?pageSize=200 | ?taskId=<n> -> documents[]
  DELETE https://<pod>.<domain>.informaticacloud.com/frs/api/v1/BaseEntities('<frsId>') (IDS-SESSION-ID) -> 204
Task JSON essentials: taskType "dbmi"; general{name, description, location: "<project>" (a project only; move it
  into a folder afterwards with FRS MoveEntities), runtimeEnvironment: "<RE name>", type "combined"|"initial"};
  source{connection name, schema, replicationSlotName, replicationPlugin "pgoutput", publication, selectionRules,
  restartPointForIncrementalLoad "LATEST", customProperties{loadType "CDC_COMBINED"|"UNLOAD", ...}};
  target{connection, schema, customProperties{...}}; runtimeOptions{applyCycleIntervalSecs, customProperties
  {FlushPeriod, ...}}. Clone the JSON from 'details' of a working task and change names and connections.
Gotchas: there is NO update verb (stop + undeploy, re-import an edited .DBMI_TASK.dat with OVERWRITE, or create a
  new task and delete the old one); DBMI refuses an import while the task is deployed; ids on this plane are
  numeric (a design GUID gives a routing 404); an imported task keeps the source's slot and publication names;
  CDC_COMBINED with LATEST re-runs the initial unload on first start; to move CDC between orgs STOP (do not
  undeploy) the old job and start the new task on the same slot, so rollback = stop new + resume old. A slot
  that shows active=f between polling cycles while confirmed_flush advances is NOT dead: never drop it.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import idmc_http as H  # noqa: E402
from idmc_session import LoginError, Session  # noqa: E402

WAIT_UNTIL = {"deploy": ("deployed", "failed", "running"), "start": ("running", "failed", "stopped"),
              "resume": ("running", "failed", "stopped"), "stop": ("stopped", "failed", "completed"),
              "undeploy": ("undeployed", "failed", None)}
REQUIRED = (("taskType",), ("general", "name"), ("general", "location"), ("general", "runtimeEnvironment"),
            ("source", "connection"), ("target", "connection"))


def numeric(tid):
    if not str(tid).isdigit():
        H.die(f"DBMI task ids on the -ing plane are numeric runtime ids, got '{tid}' (a design GUID gives a routing 404)")
    return str(tid)


def status(S, tid):
    r = S.get("dbmi", f"/dbmi/api/v1/task/{numeric(tid)}/job")
    j = r.json({}) if r.ok else {}
    j = j if isinstance(j, dict) else {}
    return r, j.get("status"), j.get("runId"), j


def wait(S, tid, op, timeout=900):
    want = WAIT_UNTIL[op]
    (r, st, run, _), done = H.poll(lambda: status(S, tid), lambda v: v[1] in want or (op == "undeploy" and v[0].status == 404),
                                   interval=10, timeout=timeout, describe=lambda v: f"HTTP {v[0].status} status={v[1]} job={v[2]}")
    print(f"  final: status={st} job={run}" + ("" if done else " (timeout: check again with 'status')"))
    return st


def main():
    H.safe_console()
    ap = argparse.ArgumentParser(description="Database Ingestion tasks headless")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list").add_argument("--grep")
    dt = sub.add_parser("details")
    dt.add_argument("task")
    dt.add_argument("--save")
    sub.add_parser("status").add_argument("task")
    cr = H.add_gate_args(sub.add_parser("create"))
    cr.add_argument("--spec", required=True)
    for op in ("deploy", "start", "stop", "resume", "undeploy"):
        p = H.add_gate_args(sub.add_parser(op))
        p.add_argument("task")
        p.add_argument("--job-id", type=int)
        p.add_argument("--no-wait", action="store_true")
    de = H.add_gate_args(sub.add_parser("delete"))
    de.add_argument("task")
    de.add_argument("--frs-id", required=True)
    a = ap.parse_args()
    try:
        S = Session()
        if a.cmd == "list":
            r = S.get("dbmi", "/dbmi/public/api/v2/task/details?pageSize=200")
            docs = (r.json({}) or {}).get("documents") or [] if r.ok else []
            print(f"HTTP {r.status}: {len(docs)} task(s)")
            for d in docs:
                t = d.get("dbmiTask") or {}
                if a.grep and a.grep.lower() not in json.dumps(d).lower():
                    continue
                print(f"  {d.get('taskId')!s:>8}  {d.get('name', ''):40} type={(t.get('general') or {}).get('type')} "
                      f"src={(t.get('source') or {}).get('connection')} tgt={(t.get('target') or {}).get('connection')}")
            return
        if a.cmd == "details":
            r = S.get("dbmi", f"/dbmi/public/api/v2/task/details?taskId={numeric(a.task)}")
            print(f"HTTP {r.status} | {r.verdict()}")
            if a.save and r.ok:
                print("saved", H.save_json(a.save, r.json()))
            print(H.preview(r.json() if r.ok else r.text, 5000))
            return
        if a.cmd == "status":
            r, st, run, j = status(S, a.task)
            print(f"HTTP {r.status} status={st} jobId(runId)={run}\n{H.preview(j, 1500)}")
            return
        gate = H.WriteGate(a, S)
        gate.guard()
        if a.cmd == "create":
            spec = json.load(open(a.spec, encoding="utf-8"))
            for keys in REQUIRED:
                node = spec
                for k in keys:
                    node = node.get(k) if isinstance(node, dict) else None
                if not node:
                    H.die(f"spec is missing {'.'.join(keys)}")
            if "/" in str(spec["general"]["location"]):
                H.die("general.location must be a project name only (a folder path is rejected); move it afterwards")
            r = gate.send("create DBMI task", "dbmi", "POST", "/dbmi/public/api/v2/task/create", body=spec)
            if r is not None:
                j = r.json({}) or {}
                if not r.ok or not j.get("taskId"):
                    H.die(f"create failed HTTP {r.status} {r.head(400)}")
                print(f"  created taskId={j.get('taskId')} frsId={j.get('frsId')} (not deployed; next: deploy)")
                rb = S.get("dbmi", f"/dbmi/public/api/v2/task/details?taskId={j.get('taskId')}")
                print(f"  read-back details HTTP {rb.status}")
            return
        r0, st0, run0, _ = status(S, a.task)
        print(f"  task {a.task}: status={st0} job={run0}")
        if a.cmd == "delete":
            if st0 not in ("undeployed", None) and r0.status != 404:
                H.die(f"job status is '{st0}': stop and undeploy it first (FRS delete of a deployed task is refused)")
            r = gate.send("FRS delete DBMI task", "frs", "DELETE", f"/frs/api/v1/BaseEntities('{a.frs_id}')")
            if r is not None:
                rb = S.get("frs", f"/frs/v1/BaseEntities('{a.frs_id}')")
                print(f"  read-back: HTTP {rb.status} -> {'GONE' if rb.status == 404 or not rb.ok else 'STILL PRESENT'}")
            return
        if a.cmd == "deploy":
            r = gate.send(f"deploy task {a.task}", "dbmi", "POST", f"/dbmi/public/api/v2/task/deploy/{numeric(a.task)}", body={})
        else:
            job = a.job_id or run0
            if not job:
                H.die("no job id: deploy the task first, or pass --job-id")
            if a.cmd == "undeploy":
                print("  NOTE: undeploy ends the job; to hand a CDC slot to another task or org, STOP instead.")
            r = gate.send(f"{a.cmd} job {job}", "dbmi", "POST", f"/dbmi/public/api/v2/job/{a.cmd}", body={"jobId": int(job)})
        if r is not None:
            if not r.ok:
                H.die(f"{a.cmd} failed HTTP {r.status} {r.head(400)}")
            j = r.json({}) or {}
            print(f"  accepted: jobId={(j.get('data') or {}).get('jobId') or j.get('jobId') or ''}")
            if not a.no_wait:
                wait(S, a.task, a.cmd)
    except (LoginError, RuntimeError, ValueError) as e:
        H.die(f"{type(e).__name__}: {e}", 3)


if __name__ == "__main__":
    main()
