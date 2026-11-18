#!/usr/bin/env python3
"""Step 2: Database Ingestion CDC, PostgreSQL -> BigQuery, split into a HOT and a COLD task (each its own slot).

  python idmc/02_cdc.py render --offline                        # write state/rendered/dbmi_rdf_cdc_*.json, no network
  python idmc/02_cdc.py create  --lane hot  --execute --expect-org <orgIdV3>
  python idmc/02_cdc.py deploy  --lane hot  --execute --expect-org <orgIdV3>
  python idmc/02_cdc.py start   --lane hot  --execute --expect-org <orgIdV3>
  python idmc/02_cdc.py status  --lane hot
  (stop | resume | undeploy | delete  are in teardown/teardown.py and the core idmc_dbmi.py)

Call order (PROVEN 2026-09 in a production cutover, host <pod>-ing, base /dbmi/public/api/v2):
  POST /task/create (body = the dbmiTask doc)          -> 201 + numeric taskId
  POST /task/deploy/<taskId>  body {}                   -> 202 + data.jobId (a NEW deploy job id, not the taskId)
  POST /job/start {"jobId": <deployJobId>}              -> 202   (job/resume on a freshly deployed job = 409)
  GET  /task/<taskId>/job                              -> status deployed -> running; runId = the job id
Prerequisites: infra/sql/02_cdc_prereqs.sql (publications, slots, REPLICA IDENTITY FULL, the CDC role), the
Simba BigQuery JDBC jars on the agent (Database_Ingestion ext folder) and a GCS staging bucket the key can write.
Measured: PostgreSQL -> BigQuery 10-22 s per change with the hot/cold split (one combined task: 15-35 s, because the
tables of one task apply one after another in a cycle).
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
import rdf_common as C  # noqa: E402

TPL = C.BLUEPRINT / "idmc" / "templates" / "cdc" / "dbmi_cdc_task.json"


def render_lane(cfg, lane, offline):
    t = cfg["cdc"]["tasks"][lane]
    v = C.template_vars(cfg, offline=offline)
    v.update(TASK_NAME=t["name"], LANE=lane, SLOT=t["slot"], PUBLICATION=t["publication"],
             APPLY_SECS=t["applyCycleSecs"], FLUSH=t["flushPeriod"],
             SELECTION_RULES=json.dumps([{"include": x} for x in t["tables"]]))
    body = json.loads(C.render(TPL.read_text(encoding="utf-8"), v, "dbmi_cdc_task.json"))
    p = C.write_rendered(f"{t['name']}.json", body)
    return t, body, p


def main():
    ap = C.add_common_args(argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter))
    ap.add_argument("cmd", choices=["render", "create", "deploy", "start", "status"])
    ap.add_argument("--lane", choices=["hot", "cold", "both"], default="both")
    ap.add_argument("--offline", action="store_true", help="render with placeholders for unset .env values")
    a = ap.parse_args()
    cfg, st = C.load_config(a.config), C.load_state()
    lanes = ["hot", "cold"] if a.lane == "both" else [a.lane]
    st.setdefault("cdc", {})
    rc = 0
    for lane in lanes:
        t, body, p = render_lane(cfg, lane, a.offline or a.cmd == "render")
        print(f"[{lane}] {t['name']}: {len(t['tables'])} tables, slot {t['slot']}, publication {t['publication']}, "
              f"apply {t['applyCycleSecs']} s, flush {t['flushPeriod']} s -> {p.relative_to(C.BLUEPRINT)}")
        if a.cmd == "render":
            continue
        tid = (st["cdc"].get(lane) or {}).get("taskId")
        if a.cmd == "create":
            if tid:
                print(f"   already created (taskId {tid}); there is no update verb: delete + create, or patch in the UI")
                continue
            rc |= C.core_cli("idmc_dbmi.py", ["create", "--spec", str(p)] + C.gate_args(a))
            print("   then record the printed taskId:  state/ids.json  cdc.%s.taskId  (or re-run 'status' after listing)" % lane)
        elif not tid:
            print(f"   no taskId for lane {lane} in state/ids.json (add it from the create output: cdc.{lane}.taskId)")
            rc = 1
        elif a.cmd == "status":
            rc |= C.core_cli("idmc_dbmi.py", ["status", str(tid)])
        else:
            args = [a.cmd, str(tid)]
            job = (st["cdc"].get(lane) or {}).get("jobId")
            if a.cmd == "start" and job:
                args += ["--job-id", str(job)]
            rc |= C.core_cli("idmc_dbmi.py", args + C.gate_args(a))
    return rc


if __name__ == "__main__":
    sys.exit(main())
