#!/usr/bin/env python3
"""bid_taskflows.py - the Bid Desk end to end as two linear IDMC taskflows (v2 workflows) in folder 5, and the nightly schedule.

    python bid_taskflows.py show                                  # both taskflows: steps, schedule (read-only)
    python bid_taskflows.py build [--no-sharepoint] [--execute --expect-org <orgIdV3>]   # create or update both, move to folder 5
    python bid_taskflows.py run [run|reset] [--execute ...]       # one run, then every step's state and rows (uses jobs + warehouse)
    python bid_taskflows.py schedule [--attach] [--execute ...]   # PREPARED, not attached by default: --attach binds it to Run
    python bid_taskflows.py detach [--execute ...]                # undo: unbind the schedule (scheduleId null) and read back

<project> - Run   (the nightly batch, on demand in the demo):
    1 CRM Bid Documents -> 1b Transfer to SharePoint -> 2a Read the Bid Packet -> 2b Read the Signature Page
    -> 3a Bid Lines Data Quality -> 3b Required Fields Data Quality -> 4 Bid Readiness
    1 and 1b continue on error (stopOnError false), so the CRM or SharePoint being down never blocks what is in Snowflake.
    --no-sharepoint leaves 1b out until SharePoint write consent is granted (infra/sharepoint_setup.py check).
<project> - Reset: 5 Reset (pre-processing: the originals again as new CRM versions) -> the same steps as Run.
Calls (PROVEN, toolkit/lib/idmc_taskflow_schedule.py has the same rules): POST /api/v2/workflow (create), POST
/api/v2/workflow/<id> (update: GET body minus audit fields, keep id and scheduleId; no PUT); a new workflow is born in
Default: find its FRS id (v3 objects location=='Default') and FRS MoveEntities into folder 5. Run: POST /api/v2/job
{"@type":"job","taskId":<wf id>,"taskType":"WORKFLOW"} and poll /api/v2/activity/activityLog?taskId=<id>&rowLimit=1 on runId.
Schedule: POST /api/v2/schedule; v2 startTime is POD-LOCAL time labelled 'Z'; startTimeUTC is true UTC. Every run is one job
of the org's monthly job budget and wakes the warehouse: ask before you attach a schedule.
Two taskflows that share tasks cannot overlap (REPO_17314): never start Reset while Run is running.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
import bid_common as C  # noqa: E402

PIPE = ["1 CRM Bid Documents", "1b Transfer to SharePoint", "2a Read the Bid Packet", "2b Read the Signature Page",
        "3a Bid Lines Data Quality", "3b Required Fields Data Quality", "4 Bid Readiness"]
NONSTOP = {"1 CRM Bid Documents", "1b Transfer to SharePoint"}
AUDIT = ("orgId", "createTime", "updateTime", "createdBy", "updatedBy")
STATE = {1: "SUCCESS", 2: "WARNING", 3: "FAILED"}


def flows(cfg, sharepoint=True):
    p = cfg["idmc"]["project"]
    pipe = [s for s in PIPE if sharepoint or not s.startswith("1b")]
    return {"%s - Run" % p: (pipe, "%s nightly pipeline (on demand in the demo): the agencies and their bid documents from the CRM -> "
                                   "SharePoint -> CLAIRE reads each PDF (Bronze) -> Data Quality rules (Silver) -> one decision per "
                                   "solicitation (Gold) -> Tableau." % p),
            "%s - Reset" % p: (["5 Reset"] + pipe, "%s back to the starting point: the agencies' originals attached again as new "
                                                   "CRM versions (nothing deleted) -> the whole pipeline." % p)}


def workflows(ctx):
    r = ctx.read("v2", "/api/v2/workflow")
    return {w.get("name"): w for w in (r.json([]) if r is not None else []) if isinstance(w, dict)}


def tasks(ctx):
    r = ctx.read("v2", "/api/v2/mttask")
    return {t.get("name"): t for t in (r.json([]) if r is not None else []) if isinstance(t, dict)}


def full(ctx, wid):
    r = ctx.read("v2", "/api/v2/workflow/" + wid)
    return r.json({}) if r is not None else {}


def run(ctx, wf_name):
    wf = workflows(ctx).get(wf_name)
    if not wf and not ctx.offline:
        C.H.die("no taskflow %r: build first" % wf_name)
    wid = (wf or {}).get("id", "<workflow id>")
    r = ctx.write("start " + wf_name, "v2", "POST", "/api/v2/job", body={"@type": "job", "taskId": wid, "taskType": "WORKFLOW"})
    if r is None:
        return True
    rid, t0 = (r.json({}) or {}).get("runId"), time.time()
    while time.time() - t0 < 2400:
        time.sleep(15)
        e = (ctx.read("v2", "/api/v2/activity/activityLog?taskId=%s&rowLimit=1" % wid).json([]) or [{}])[0]
        if e.get("runId") == rid and e.get("endTime"):
            print("taskflow %s: %s in %ds" % (wf_name, STATE.get(e.get("state"), e.get("state")), time.time() - t0))
            for x in e.get("entries") or []:
                print("  %-56s %-8s rows %s -> %s  %s" % (x.get("objectName"), STATE.get(x.get("state")), x.get("successSourceRows"),
                                                         x.get("successTargetRows"), (x.get("errorMsg") or "")[:200]))
            return e.get("state") in (1, 2)
    print("still running after 40 min")
    return False


def main():
    ap = C.parser(__doc__)
    ap.add_argument("cmd", choices=["show", "build", "run", "schedule", "detach"])
    ap.add_argument("which", nargs="?", default="run", choices=["run", "reset"])
    ap.add_argument("--no-sharepoint", action="store_true")
    ap.add_argument("--attach", action="store_true", help="schedule: also bind it to the Run taskflow")
    a = ap.parse_args()
    ctx = C.Ctx(a)
    cfg, st = ctx.cfg, C.state()
    proj = cfg["idmc"]["project"]
    F = flows(cfg, not a.no_sharepoint)
    run_name = "%s - Run" % proj
    if a.cmd == "run":
        sys.exit(0 if run(ctx, "%s - %s" % (proj, a.which.capitalize())) else 1)
    have = workflows(ctx)
    if a.cmd == "show":
        for n in F:
            w = have.get(n)
            d = full(ctx, w["id"]) if w else {}
            print("%-24s %s schedule=%s" % (n, (w or {}).get("id", "MISSING"), d.get("scheduleId")))
            for t in d.get("tasks") or []:
                print("   %s%s" % (t.get("name"), "" if t.get("stopOnError") else "  (continues on error)"))
        return
    if a.cmd == "build":
        T = tasks(ctx)
        for n, (steps, desc) in F.items():
            body_tasks = []
            for s in steps:
                tn = "%s - %s - task" % (proj, s)
                t = T.get(tn) or {"id": "<id of %s>" % tn, "name": tn}
                body_tasks.append({"@type": "workflowTask", "taskId": t["id"], "type": "MTT", "name": t["name"],
                                   "stopOnError": s not in NONSTOP, "stopOnWarning": False})
            old = have.get(n)
            body = {"@type": "workflow", "name": n, "description": desc, "tasks": body_tasks}
            if old:
                cur = full(ctx, old["id"])
                body = {k: v for k, v in cur.items() if k not in AUDIT}
                body.update(description=desc, tasks=body_tasks)
            r = ctx.write(("update " if old else "create ") + n, "v2", "POST", "/api/v2/workflow/" + old["id"] if old else "/api/v2/workflow",
                          body=body)
            if old or not C.ok(r):
                continue
            o = ctx.read("v3", "/public/core/v3/objects?q=%s&limit=200" % urllib.parse.quote("location=='Default'", safe="="))
            frs = next((x["id"] for x in (o.json({}) or {}).get("objects") or [] if x.get("type") == "WORKFLOW"
                        and x.get("path") == "Default/" + n), None)
            if frs:
                ctx.write("move %s into folder 5" % n, "frs", "POST", "/frs/api/v1/MoveEntities",
                          body={"xferSpec": {"targetLocationId": st["folders"]["f5"], "sourceSpecArr": [{"sourceEntityId": frs, "mergeTags": ""}]}})
        if ctx.offline:
            ctx.write("move each new taskflow into folder 5", "frs", "POST", "/frs/api/v1/MoveEntities",
                      body={"xferSpec": {"targetLocationId": "<folder f5 id>", "sourceSpecArr": [{"sourceEntityId": "<frs id>", "mergeTags": ""}]}})
        return
    wf = have.get(run_name)
    wid = (wf or {}).get("id", "<workflow id>")
    if a.cmd == "detach":
        cur = full(ctx, wid) if wf else {"id": wid}
        body = {k: v for k, v in cur.items() if k not in AUDIT}
        body["scheduleId"] = None
        ctx.write("detach the schedule from " + run_name, "v2", "POST", "/api/v2/workflow/" + wid, body=body)
        if ctx.execute:
            print("read back scheduleId:", full(ctx, wid).get("scheduleId"))
        return
    sc = cfg["schedule"]
    sched = {"@type": "schedule", "name": sc["name"], "status": "enabled", "interval": sc["interval"], "frequency": sc["frequency"],
             "startTimeUTC": sc["start_utc"] + ":00.000Z", "timeZone": sc["time_zone"],
             "description": "%s: the nightly pipeline. Attached only on the owner's OK (it runs and costs every day)." % proj}
    r = ctx.read("v2", "/api/v2/schedule")
    ex = next((x for x in (r.json([]) if r is not None else []) if isinstance(x, dict) and x.get("name") == sc["name"]), None)
    if not ex:
        r = ctx.write("create schedule (unbound)", "v2", "POST", "/api/v2/schedule", body=sched)
        ex = r.json({}) if C.ok(r) else {"id": "<schedule id>"}
    print("schedule %s: %s" % (sc["name"], ex.get("id")))
    if not a.attach:
        print("prepared, NOT attached (it runs every day). Attach with: schedule --attach --execute --expect-org <orgIdV3>")
        return
    cur = full(ctx, wid) if wf else {"id": wid}
    body = {k: v for k, v in cur.items() if k not in AUDIT}
    body["scheduleId"] = ex.get("id")
    ctx.write("attach the schedule to " + run_name, "v2", "POST", "/api/v2/workflow/" + wid, body=body)
    if ctx.execute:
        print("read back scheduleId:", full(ctx, wid).get("scheduleId"))
    C.put_state("schedule", ex.get("id")) if ctx.execute else None


if __name__ == "__main__":
    main()
