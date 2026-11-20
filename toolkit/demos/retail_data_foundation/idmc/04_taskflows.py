#!/usr/bin/env python3
"""Step 4: lanes as linear taskflows + one schedule (the IDMC-native replacement of an external lane orchestrator).

  python idmc/04_taskflows.py plan                                   # offline: print the core commands
  python idmc/04_taskflows.py apply    --execute --expect-org <orgIdV3>   # upsert tf_rdf_full + tf_rdf_customer
  python idmc/04_taskflows.py schedule --execute --expect-org <orgIdV3>   # create sch_rdf_every_4h unbound, then bind
  python idmc/04_taskflows.py run tf_rdf_customer --execute --expect-org <orgIdV3>   # one lane run (jobs + IPUs)
  python idmc/04_taskflows.py audit                                  # every workflow AND task-level schedule binding

Lanes (config.json "taskflows"):
  tf_rdf_full      all six mapping tasks in dependency order, scheduled every 4 h
  tf_rdf_customer  the sign-up lane: ingest customers -> golden -> CRM sync (run on demand, e.g. by verify/)
Rules (PROVEN 2026-09): linear taskflows only (an advanced / parallel taskflow created by API imports but cannot be
published); two linear taskflows that share tasks cannot overlap (REPO_17314), so the on-demand lane must not start
while the scheduled full lane runs; create schedules unbound, then bind (times are pod-local labelled Z: the core
derives the offset); a task-level schedule hides from the task list, so audit both levels before any cutover.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
import rdf_common as C  # noqa: E402


def resolve_ids(st):
    """v2 ids of the workflows and schedules BY NAME (read-only), cached in state/ids.json."""
    from idmc_session import Session
    S = Session()
    st["taskflows"] = {w["name"]: {"id": w["id"]} for w in S.get("v2", "/api/v2/workflow").json([]) or []
                       if w.get("name", "").startswith("tf_")}
    st["schedules"] = {x["name"]: {"id": x["id"]} for x in S.get("v2", "/api/v2/schedule").json([]) or []
                       if x.get("name", "").startswith("sch_")}
    C.save_state(st)
    return st


def main():
    ap = C.add_common_args(argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter))
    ap.add_argument("cmd", choices=["plan", "apply", "schedule", "run", "audit"])
    ap.add_argument("names", nargs="*")
    a = ap.parse_args()
    cfg, st = C.load_config(a.config), C.load_state()
    tasks = st.get("tasks") or {}
    plan_only = a.cmd == "plan"
    rc = 0
    if a.cmd in ("plan", "apply"):
        for tf, members in cfg["taskflows"].items():
            ids = [(tasks.get(m) or {}).get("id") or f"<id of {m}>" for m in members]
            if not plan_only and any(i.startswith("<") for i in ids):
                C.die(f"{tf}: missing task ids in state/ids.json (run 03_mappings.py tasks first)")
            args = ["upsert", "--name", tf, "--desc", f"[{cfg['idmc']['tag']}] lane {tf}: " + " -> ".join(members)]
            for i in ids:
                args += ["--task", i]
            rc |= C.core_cli("idmc_taskflow_schedule.py", args + C.gate_args(a), dry_print=plan_only)
    if a.cmd in ("schedule", "run"):
        C.offline_session_guard(a)
        st = resolve_ids(st)
    if a.cmd in ("plan", "schedule"):
        for sname, s in cfg["schedules"].items():
            args = ["schedule-create", "--name", sname, "--interval", s["interval"], "--frequency", str(s["frequency"]),
                    "--start-utc", s["startTimeUTC"], "--desc", f"[{cfg['idmc']['tag']}] {s['taskflow']}"]
            if cfg["idmc"].get("podOffsetHours") is not None:
                args += ["--pod-offset-hours", str(cfg["idmc"]["podOffsetHours"])]
            rc |= C.core_cli("idmc_taskflow_schedule.py", args + C.gate_args(a), dry_print=plan_only)
            if not plan_only:
                st = resolve_ids(st)
            wid = (st.get("taskflows", {}).get(s["taskflow"]) or {}).get("id") or f"<v2 id of {s['taskflow']}>"
            sid = (st.get("schedules", {}).get(sname) or {}).get("id") or f"<v2 id of {sname}>"
            if not plan_only and (wid.startswith("<") or sid.startswith("<")):
                print(f"   cannot bind yet: {wid} / {sid} (dry run, or the create did not happen)")
                continue
            rc |= C.core_cli("idmc_taskflow_schedule.py", ["bind", wid, sid] + C.gate_args(a), dry_print=plan_only)
    if a.cmd == "run":
        for n in a.names or ["tf_rdf_customer"]:
            wid = (st.get("taskflows", {}).get(n) or {}).get("id") or C.die(f"taskflow {n} not found (run apply first)")
            rc |= C.core_cli("idmc_taskflow_schedule.py", ["run", wid] + C.gate_args(a))
    if a.cmd == "audit":
        rc |= C.core_cli("idmc_taskflow_schedule.py", ["audit"])
    return rc


if __name__ == "__main__":
    sys.exit(main())
