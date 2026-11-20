#!/usr/bin/env python3
"""idmc_taskflow_schedule.py - linear taskflows (v2 workflows) and schedules: create/update, bind/unbind with
read-back, a binding audit that includes TASK-LEVEL schedules, snapshot/restore for cutovers, and run.

  python idmc_taskflow_schedule.py show <wfId>
  python idmc_taskflow_schedule.py upsert --name <wf name> --task <taskId> [--task ..] [--desc ..] [--continue-on-error]
  python idmc_taskflow_schedule.py schedule-create --name <n> --interval Hourly|Daily|Minutely --frequency 1
         --start-utc 2026-01-01T00:05 [--days mon,..,sun] [--pod-offset-hours -4] [--desc ..]
  python idmc_taskflow_schedule.py schedule-end <scheduleId> --end-utc 2026-01-01T00:05 [--pod-offset-hours -4]
  python idmc_taskflow_schedule.py bind <wfId> <scheduleId> | unbind <wfId>
  python idmc_taskflow_schedule.py task-bind <mttId> <scheduleId> | task-unbind <mttId>
  python idmc_taskflow_schedule.py audit [--json f]      snapshot --out f.json      restore f.json [--only wf1,wf2]
  python idmc_taskflow_schedule.py run <wfId> [--timeout 7200]
Every write is dry-run unless --execute --expect-org <orgIdV3>.

PROVEN 2026-09 (production cutover and lane builds): POST /api/v2/workflow (create) and POST /api/v2/workflow/<id>
  (update = GET body minus createTime/updateTime/createdBy/updatedBy, keep id and scheduleId; no PUT);
  bind/unbind = the same POST with scheduleId set or null, then GET and compare (a 200 whose value reverted is a
  silent rejection); POST /api/v2/schedule with interval/frequency/startTime/startTimeUTC/day flags; task-level
  binding = scheduleId on /api/v2/mttask/<id>. ADAPTED: schedule-end (the fix that worked was setting BOTH
  endTime and endTimeUTC; endTime alone was read as pod-local and the lane kept running), pod-offset derivation.
Gotchas: v2 startTime/endTime are POD-LOCAL time labelled 'Z' (UTC-4 on the pods seen); startTimeUTC is true UTC.
  schedule-create always sends timeZoneId "GMT" (the only value proven), so a daily local time such as 2am moves by
  an hour against local time across daylight-saving changes: end and re-create the schedule, or accept the shift.
  The v2 MTT LIST omits scheduleId: only detail GETs show task-level bindings (one was missed at a real cutover
  and ran once more in the old org). Two taskflows sharing tasks cannot overlap (REPO_17314). Deleting a task
  bound to a schedule fails with REPO_52013. v3 PATCH /public/core/v3/schedule/<id> {"status":"disabled"} gave
  400 V3API_007. Linear taskflows need no publish; tasks inside log under the taskflow's activity row.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import idmc_http as H  # noqa: E402
from idmc_mttask import clean, run_job  # noqa: E402
from idmc_session import LoginError, Session  # noqa: E402

AUDIT = ("createTime", "updateTime", "createdBy", "updatedBy")
DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def _ts(s):
    """'2026-01-01T00:05', '...T00:05Z' or '...T00:05:00.000Z' -> naive datetime (the 'Z' is NOT trusted)."""
    s = s.strip().rstrip("Z").split(".")[0]
    return dt.datetime.strptime(s if len(s) == 19 else s + ":00", "%Y-%m-%dT%H:%M:%S")


def fmt(t):
    return t.strftime("%Y-%m-%dT%H:%M:00.000Z")


def get(S, kind, oid):
    r = S.get("v2", f"/api/v2/{kind}/{oid}")
    if not r.ok:
        H.die(f"GET {kind}/{oid} -> HTTP {r.status} {r.head(200)}")
    return r.json({}) or {}


def pod_offset(S, given):
    if given is not None:
        return given
    for s in S.get("v2", "/api/v2/schedule").json([]) or []:
        d = get(S, "schedule", s["id"])
        if d.get("startTime") and d.get("startTimeUTC"):
            off = round((_ts(d["startTime"]) - _ts(d["startTimeUTC"])).total_seconds() / 3600)
            print(f"  pod offset {off:+d} h derived from schedule '{d.get('name')}' (startTime vs startTimeUTC)")
            return off
    H.die("no schedule to derive the pod-local offset from: pass --pod-offset-hours (e.g. -4)")


def set_binding(S, gate, kind, oid, sid):
    cur = get(S, kind, oid)
    body = clean(cur) if kind == "mttask" else {k: v for k, v in cur.items() if k not in AUDIT}
    body["scheduleId"] = sid
    print(f"  {kind} {oid} '{cur.get('name')}': scheduleId {cur.get('scheduleId')} -> {sid}")
    r = gate.send(f"{'bind' if sid else 'unbind'} {kind}", "v2", "POST", f"/api/v2/{kind}/{oid}", body=body)
    if r is None:
        return
    after = get(S, kind, oid).get("scheduleId")
    ok = r.ok and after == sid
    print(f"  read-back scheduleId={after} -> {'OK' if ok else 'NOT APPLIED (silent rejection or error)'}")
    H.jlog(gate.logfile, op="binding", kind=kind, id=oid, want=sid, got=after, status=r.status)


def upsert_wf(S, gate, a):
    tasks = []
    for tid in a.task:
        t = get(S, "mttask", tid)
        tasks.append({"@type": "workflowTask", "taskId": tid, "type": "MTT", "name": t.get("name"),
                      "stopOnError": not a.continue_on_error, "stopOnWarning": False})
    body = {"@type": "workflow", "name": a.name, "description": a.desc or "", "tasks": tasks}
    same = [w for w in S.get("v2", "/api/v2/workflow").json([]) or [] if w.get("name") == a.name]
    if len(same) > 1:
        H.die(f"{len(same)} workflows named '{a.name}': refusing (address by id)")
    if same:
        cur = get(S, "workflow", same[0]["id"])
        body.update(id=cur["id"], scheduleId=cur.get("scheduleId"))
        print(f"  UPDATE {cur['id']}: tasks {[t.get('name') for t in cur.get('tasks') or []]} -> {[t['name'] for t in tasks]}")
        r = gate.send("update workflow", "v2", "POST", f"/api/v2/workflow/{cur['id']}", body=body)
    else:
        print(f"  CREATE workflow '{a.name}' with {len(tasks)} task(s)")
        r = gate.send("create workflow", "v2", "POST", "/api/v2/workflow", body=body)
    if r is not None:
        wid = (r.json({}) or {}).get("id") if r.ok else None
        if not wid:
            H.die(f"write failed HTTP {r.status} {r.head(300)}")
        w = get(S, "workflow", wid)
        print(f"  read-back {wid}: {len(w.get('tasks') or [])} task(s), scheduleId={w.get('scheduleId')}")


def audit(S):
    rows = []
    for w in S.get("v2", "/api/v2/workflow").json([]) or []:
        d = get(S, "workflow", w["id"])
        rows.append({"kind": "workflow", "id": d["id"], "name": d.get("name"), "scheduleId": d.get("scheduleId"),
                     "tasks": len(d.get("tasks") or [])})
    for t in S.get("v2", "/api/v2/mttask").json([]) or []:          # the list hides scheduleId: detail per task
        d = get(S, "mttask", t["id"])
        if d.get("scheduleId"):
            rows.append({"kind": "mttask", "id": d["id"], "name": d.get("name"), "scheduleId": d["scheduleId"]})
    names = {s["id"]: s.get("name") for s in S.get("v2", "/api/v2/schedule").json([]) or []}
    for x in rows:
        x["schedule"] = names.get(x.get("scheduleId"))
        if x.get("scheduleId") or x["kind"] == "workflow":
            flag = "  <-- TASK-LEVEL binding" if x["kind"] == "mttask" else ""
            print(f"  {x['kind']:8} {x['id']}  {x.get('name', ''):40} schedule={x.get('schedule')}{flag}")
    return rows


def main():
    H.safe_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("show").add_argument("wf")
    up = H.add_gate_args(sub.add_parser("upsert"))
    up.add_argument("--name", required=True)
    up.add_argument("--task", action="append", required=True)
    up.add_argument("--desc")
    up.add_argument("--continue-on-error", action="store_true")
    sc = H.add_gate_args(sub.add_parser("schedule-create"))
    for f in ("--name", "--interval", "--start-utc"):
        sc.add_argument(f, required=True)
    sc.add_argument("--frequency", type=int, default=1)
    sc.add_argument("--days")
    sc.add_argument("--desc", default="")
    sc.add_argument("--pod-offset-hours", type=int)
    se = H.add_gate_args(sub.add_parser("schedule-end"))
    se.add_argument("schedule")
    se.add_argument("--end-utc", required=True)
    se.add_argument("--pod-offset-hours", type=int)
    for c, n in (("bind", 2), ("unbind", 1), ("task-bind", 2), ("task-unbind", 1)):
        p = H.add_gate_args(sub.add_parser(c))
        p.add_argument("obj")
        if n == 2:
            p.add_argument("schedule")
    sub.add_parser("audit").add_argument("--json")
    sub.add_parser("snapshot").add_argument("--out", required=True)
    rs = H.add_gate_args(sub.add_parser("restore"))
    rs.add_argument("snapshot")
    rs.add_argument("--only")
    rn = H.add_gate_args(sub.add_parser("run"))
    rn.add_argument("wf")
    rn.add_argument("--timeout", type=int, default=7200)
    a = ap.parse_args()
    try:
        S = Session()
        if a.cmd == "show":
            w = get(S, "workflow", a.wf)
            print(f"{w.get('id')} '{w.get('name')}' scheduleId={w.get('scheduleId')}")
            for t in w.get("tasks") or []:
                print(f"   {t.get('taskId')}  {t.get('type')}  {t.get('name')}  stopOnError={t.get('stopOnError')}")
            return
        if a.cmd in ("audit", "snapshot"):
            rows = audit(S)
            path = a.json if a.cmd == "audit" else a.out
            if path:
                print("saved", H.save_json(path, {"org": S.whoami(with_v3=False).get("orgIdV3"), "bindings": rows}))
            return
        gate = H.WriteGate(a, S)
        gate.guard()
        if a.cmd == "upsert":
            upsert_wf(S, gate, a)
        elif a.cmd == "schedule-create":
            if any(s.get("name") == a.name for s in S.get("v2", "/api/v2/schedule").json([]) or []):
                print(f"  EXISTS: schedule '{a.name}' (no write; schedules are idempotent by name here)")
                return
            u = _ts(a.start_utc)
            loc = u + dt.timedelta(hours=pod_offset(S, a.pod_offset_hours))
            days = set((a.days or ("" if a.interval == "Daily" else ",".join(DAYS))).split(","))
            body = {"@type": "schedule", "name": a.name, "description": a.desc, "interval": a.interval,
                    "frequency": a.frequency, "timeZoneId": "GMT", "startTime": fmt(loc), "startTimeUTC": fmt(u),
                    "weekDay": False, "dayOfMonth": 0, **{d: d in days for d in DAYS}}
            r = gate.send("create schedule (unbound)", "v2", "POST", "/api/v2/schedule", body=body)
            if r is not None and r.ok:
                d = get(S, "schedule", (r.json({}) or {}).get("id"))
                print(f"  read-back: id={d.get('id')} startTime={d.get('startTime')} startTimeUTC={d.get('startTimeUTC')}")
        elif a.cmd == "schedule-end":
            cur = get(S, "schedule", a.schedule)
            u = _ts(a.end_utc)
            body = {k: v for k, v in cur.items() if k not in AUDIT}
            body.update(endTime=fmt(u + dt.timedelta(hours=pod_offset(S, a.pod_offset_hours))), endTimeUTC=fmt(u))
            r = gate.send("end schedule", "v2", "POST", f"/api/v2/schedule/{a.schedule}", body=body)
            if r is not None:
                d = get(S, "schedule", a.schedule)
                print(f"  read-back endTime={d.get('endTime')} endTimeUTC={d.get('endTimeUTC')}")
        elif a.cmd in ("bind", "unbind", "task-bind", "task-unbind"):
            set_binding(S, gate, "mttask" if a.cmd.startswith("task") else "workflow", a.obj,
                        getattr(a, "schedule", None) if "unbind" not in a.cmd else None)
        elif a.cmd == "restore":
            snap = json.load(open(a.snapshot, encoding="utf-8"))
            only = set(a.only.split(",")) if a.only else None
            for x in snap["bindings"]:
                if x.get("scheduleId") and (not only or x.get("name") in only):
                    set_binding(S, gate, x["kind"], x["id"], x["scheduleId"])
        else:
            run_job(S, gate, a.wf, "WORKFLOW", True, a.timeout)
    except (LoginError, RuntimeError, ValueError) as e:
        H.die(f"{type(e).__name__}: {e}", 3)


if __name__ == "__main__":
    main()
