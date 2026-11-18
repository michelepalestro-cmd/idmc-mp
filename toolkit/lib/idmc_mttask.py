#!/usr/bin/env python3
"""idmc_mttask.py - mapping tasks (MTT) headless: show, clone a template task (upsert by name), change the
custom query safely, run via /api/v2/job and poll the activity log, read the logs.

  python idmc_mttask.py show <taskId> [--save f.json]
  python idmc_mttask.py clone --template <taskId> --name <name> [--desc ..] [--source-conn <connId>]
        [--query-file q.sql | --source-object <schema>/TABLE/<t>] [--target-conn <connId>] [--target <ds>/<table>]
        [--disposition truncate|append] [--fetch-runtime] [--re <reId>] [--update-id <taskId>]
        [--folder-guid <folder frsGuid>] [--tag <tag>]                        (dry-run; --execute --expect-org)
  python idmc_mttask.py set-query <taskId> (--query-file q.sql | --anchor OLD --with NEW)
  python idmc_mttask.py run <taskId> [--type MTT|WORKFLOW] [--no-wait] [--timeout 3600]  (a write: uses a job)
  python idmc_mttask.py log <taskId> [--session-log]

PROVEN 2026-09 (production, one MTT per table over the Copy Data bundle template dsst__copy_data_new_tgt):
  GET /api/v2/mttask/<id>; POST /api/v2/mttask (create, lands in Default); POST /api/v2/mttask/<id> (update:
  the full GET body minus audit fields and parameter ids; there is no PUT); GET /api/v2/task?type=MTT (name->id);
  POST /api/v2/job {"@type":"job","taskId","taskType"} -> runId; GET /api/v2/activity/activityLog?taskId=..;
  GET /api/v2/activity/activityMonitor; FRS POST /frs/api/v1/MoveEntities (xferSpec) -> FRS_200 per object;
  POST /public/core/v3/TagObjects (<=50 per call). ADAPTED: sessionLog read (proven 2026-08), --federated.
Rules encoded: fetchMode RUNTIME on $Source$/$Target$ when the target gains columns (otherwise IDMC keeps the
  creation-time field list and silently writes NULL into new columns); BigQuery disposition lives in
  oprRuntimeAttrs {"writeMode":"Bulk","writeDisposition":"Write truncate"|"Write append"}; a name that exists
  twice is refused (address tasks by id); state 1 SUCCESS, 2 WARNING (treated as FAILED when 0 target rows),
  3 FAILED; REPO_17314 = another instance running; 'exceeded your monthly limit of N jobs' = the org job cap
  (every task run and every taskflow run is one job; the license API shows -1, so the cap is invisible).
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import idmc_http as H  # noqa: E402
from idmc_session import LoginError, Session  # noqa: E402

AUDIT = ("orgId", "createTime", "updateTime", "createdBy", "updatedBy")


def clean(task, keep_ids=True):
    b = {k: v for k, v in copy.deepcopy(task).items() if k not in AUDIT and (keep_ids or k not in ("id", "frsGuid"))}
    for p in b.get("parameters") or []:
        p.pop("id", None)
    return b


def norm(task):
    b = clean(task)
    b["parameters"] = {p.get("name"): p for p in b.get("parameters") or []}
    return b


def build_clone(tpl, a):
    body = clean(tpl, keep_ids=False)
    body.update(name=a.name, description=a.desc or body.get("description", ""), shortDescription=a.desc or "",
                sessionProperties={})
    if a.re:
        body["runtimeEnvironmentId"] = a.re
        body.pop("agentId", None)
    for p in body.get("parameters") or []:
        if p.get("name") == "$Source$":
            if a.source_conn:
                p["sourceConnectionId"] = a.source_conn
            if a.query_file:
                p["customQuery"] = open(a.query_file, encoding="utf-8").read().strip().rstrip(";")
            if a.source_object:
                p.pop("customQuery", None)
            if a.query_file or a.source_object:          # proven builder: custom-query tasks read a dummy object
                obj = a.source_object or "DUMMY_Source"
                p["sourceObject"] = p["objectName"] = obj
                eo = p.get("extendedObject") or {}
                for o in [eo.get("object")] + list(eo.get("objects") or []):
                    if isinstance(o, dict):
                        o.update(name=obj, label=obj.split("/")[-1], dbSchema="")
        elif p.get("name") == "$Target$":
            if a.target_conn:
                p["targetConnectionId"] = a.target_conn
            if a.target:
                for k in ("targetObject", "targetObjectLabel", "newObjectName", "objectName", "objectLabel"):
                    p[k] = a.target
                p["tgtObjectAttributes"] = {"parent": a.target.split("/")[0]}
                p["runtimeAttrs"] = {}
                p["truncateTarget"] = False
            if a.disposition:
                p["oprRuntimeAttrs"] = {"writeMode": "Bulk", "writeDisposition":
                                        "Write truncate" if a.disposition == "truncate" else "Write append"}
        if a.fetch_runtime and p.get("name") in ("$Source$", "$Target$"):
            p["fetchMode"] = "RUNTIME"
    return body


def get_task(S, tid):
    r = S.get("v2", f"/api/v2/mttask/{tid}")
    if not r.ok:
        H.die(f"GET mttask {tid} -> HTTP {r.status} {r.head(200)} (403 REPO_19035 = not an MTT in this org)")
    return r.json()


def upsert(S, gate, body, update_id=None):
    names = [t for t in (S.get("v2", "/api/v2/task?type=MTT").json([]) or []) if t.get("name") == body["name"]]
    if update_id is None and len(names) > 1:
        H.die(f"{len(names)} tasks are named '{body['name']}': pass --update-id <taskId> (address tasks by id)")
    tid = update_id or (names[0]["id"] if names else None)
    if tid:
        cur = get_task(S, tid)
        body = dict(body, id=tid, frsGuid=cur.get("frsGuid"))
        H.print_diff(H.diff(norm(cur), norm(body)), f"UPDATE {tid} would change")
        r = gate.send(f"update MTT {body['name']}", "v2", "POST", f"/api/v2/mttask/{tid}", body=body)
    else:
        print(f"  CREATE new MTT '{body['name']}' (it lands in Default)")
        r = gate.send(f"create MTT {body['name']}", "v2", "POST", "/api/v2/mttask", body=body)
    if r is None:
        return None, None
    if not r.ok:
        H.die(f"write failed HTTP {r.status} {r.head(300)}")
    tid = tid or (r.json({}) or {}).get("id")
    after = get_task(S, tid)
    H.print_diff(H.diff(norm(body), norm(after), ignore=AUDIT + ("id", "frsGuid")), "read-back differs from what was sent")
    return tid, after


def place(S, gate, frs_guid, folder_guid, tag=None):
    body = {"xferSpec": {"targetLocationId": folder_guid, "sourceSpecArr": [{"sourceEntityId": frs_guid, "mergeTags": ""}]}}
    r = gate.send("move into folder", "frs", "POST", "/frs/api/v1/MoveEntities", body=body)
    if r is not None:
        codes = [s.get("resultValue") for v in (r.json({}) or {}).get("value", []) for s in v.get("statusArr", [])]
        print(f"    move result codes: {codes or r.head(200)} (FRS_200 = moved)")
    if tag:
        gate.send("tag", "v3", "POST", "/public/core/v3/TagObjects", body=[{"id": frs_guid, "tags": [tag]}])


def running(S, tid, name=None):
    mon = S.get("v2", "/api/v2/activity/activityMonitor?details=true").json([]) or []
    return [m for m in mon if tid in (m.get("taskId"), m.get("objectId")) or (name and m.get("taskName") == name)]


def run_job(S, gate, tid, task_type="MTT", wait=True, timeout=3600, federated=False):
    """Start one task or linear taskflow and wait for its activity-log row. Returns the row (or None)."""
    busy = running(S, tid)
    if busy:
        H.die(f"already running ({len(busy)} monitor row(s)); starting again gives REPO_17314")
    body = {"@type": "job", "taskFederatedId" if federated else "taskId": tid, "taskType": task_type}
    r = gate.send(f"start {task_type} {tid}", "v2", "POST", "/api/v2/job", body=body)
    if r is None:
        return None
    if not r.ok:
        if "monthly limit" in r.text:
            H.die("the org's monthly job cap is reached: every lane will fail until it resets or is lifted")
        H.die(f"job start HTTP {r.status} {r.head(300)}")
    run_id = str((r.json({}) or {}).get("runId"))
    if not wait:
        print(f"started runId {run_id}")
        return None

    def fetch():
        rows = S.get("v2", f"/api/v2/activity/activityLog?taskId={tid}&rowLimit=5").json([]) or []
        return next((x for x in rows if str(x.get("runId")) == run_id), None)
    row, done = H.poll(fetch, lambda x: x is not None and x.get("endTime"), interval=10, timeout=timeout,
                       describe=lambda x: "running" if not x else f"state={x.get('state')}")
    if not row:
        H.die(f"no activity-log row for runId {run_id} after {timeout}s")
    st = {1: "SUCCESS", 2: "WARNING", 3: "FAILED"}.get(row.get("state"), row.get("state"))
    if st == "WARNING" and not row.get("successTargetRows"):
        st = "FAILED (warning with 0 target rows)"
    print(f"RESULT {st}: target rows ok={row.get('successTargetRows')} failed={row.get('failedTargetRows')} "
          f"start={row.get('startTimeUtc') or row.get('startTime')} end={row.get('endTimeUtc') or row.get('endTime')}")
    if row.get("errorMsg"):
        print("  error:", row["errorMsg"][:600])
    for e in row.get("entries") or []:     # taskflow children log under the taskflow row
        print(f"   {e.get('objectName', ''):40} state={e.get('state')} ok={e.get('successTargetRows')} "
              f"fail={e.get('failedTargetRows')} {(e.get('errorMsg') or '')[:200]}")
    return row


def main():
    H.safe_console()
    ap = argparse.ArgumentParser(description="mapping tasks headless")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sh = sub.add_parser("show")
    sh.add_argument("task")
    sh.add_argument("--save")
    cl = H.add_gate_args(sub.add_parser("clone"))
    for f in ("--template", "--name"):
        cl.add_argument(f, required=True)
    for f in ("--desc", "--source-conn", "--query-file", "--source-object", "--target-conn", "--target", "--re",
              "--update-id", "--folder-guid", "--tag"):
        cl.add_argument(f)
    cl.add_argument("--disposition", choices=["truncate", "append"])
    cl.add_argument("--fetch-runtime", action="store_true")
    sq = H.add_gate_args(sub.add_parser("set-query"))
    sq.add_argument("task")
    for f in ("--query-file", "--anchor", "--with"):
        sq.add_argument(f)
    rn = H.add_gate_args(sub.add_parser("run"))
    rn.add_argument("task")
    rn.add_argument("--type", default="MTT", choices=["MTT", "WORKFLOW"])
    rn.add_argument("--no-wait", action="store_true")
    rn.add_argument("--timeout", type=int, default=3600)
    rn.add_argument("--federated", action="store_true", help="send taskFederatedId (a 2026-08 note saw 403 REPO_19035)")
    lg = sub.add_parser("log")
    lg.add_argument("task")
    lg.add_argument("--session-log", action="store_true")
    a = ap.parse_args()
    try:
        S = Session()
        if a.cmd == "show":
            t = get_task(S, a.task)
            print(H.preview({k: t.get(k) for k in ("id", "name", "frsGuid", "mappingId", "runtimeEnvironmentId", "scheduleId")}))
            for p in t.get("parameters") or []:
                q = p.get("customQuery") or ""
                print(f"  {p.get('name')}: " + H.preview({k: p.get(k) for k in ("sourceConnectionId", "sourceObject", "targetConnectionId",
                      "targetObject", "operationType", "oprRuntimeAttrs", "truncateTarget", "fetchMode") if k in p}, 400)
                      + (f" | customQuery {len(q)} chars: {q[:120]!r}" if q else ""))
            if a.save:
                print("saved", H.save_json(a.save, t))
            return
        if a.cmd == "log":
            rows = S.get("v2", f"/api/v2/activity/activityLog?taskId={a.task}&rowLimit=5").json([]) or []
            for x in rows:
                print(H.preview({k: x.get(k) for k in ("id", "runId", "objectName", "state", "startTimeUtc", "endTimeUtc",
                                                        "successTargetRows", "failedTargetRows", "errorMsg")}, 700))
            if a.session_log and rows:
                r = S.get("v2", f"/api/v2/activity/activityLog/{rows[0].get('id')}/sessionLog", headers={"Accept": "*/*"})
                print(f"session log HTTP {r.status}:\n", r.text[-3000:])
            return
        gate = H.WriteGate(a, S)
        gate.guard()
        if a.cmd == "clone":
            tid, _ = upsert(S, gate, build_clone(get_task(S, a.template), a), a.update_id)
            if tid and a.folder_guid and not a.update_id:
                place(S, gate, get_task(S, tid).get("frsGuid"), a.folder_guid, a.tag)
        elif a.cmd == "set-query":
            cur = get_task(S, a.task)
            body = clean(cur)
            src = next(p for p in body["parameters"] if p.get("name") == "$Source$")
            if a.query_file:
                src["customQuery"] = open(a.query_file, encoding="utf-8").read().strip().rstrip(";")
            else:
                n = (src.get("customQuery") or "").count(a.anchor or "\0")
                if n != 1:
                    H.die(f"anchor occurs {n} time(s) in customQuery; it must occur exactly once")
                src["customQuery"] = src["customQuery"].replace(a.anchor, a.__dict__["with"] or "")
            upsert(S, gate, body, update_id=a.task)
        else:
            run_job(S, gate, a.task, a.type, not a.no_wait, a.timeout, a.federated)
    except (LoginError, RuntimeError, StopIteration) as e:
        H.die(f"{type(e).__name__}: {e}", 3)


if __name__ == "__main__":
    main()
