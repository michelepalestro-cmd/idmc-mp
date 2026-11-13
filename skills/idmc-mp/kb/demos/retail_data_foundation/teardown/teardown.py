#!/usr/bin/env python3
"""Teardown in reverse build order. Every IDMC delete goes through the core library (dry run unless --execute
--expect-org); a v3 export backup of everything is taken first and kept in state/backup/.

  python teardown/teardown.py plan                                   # offline: the ordered steps and commands
  python teardown/teardown.py run --execute --expect-org <orgIdV3>   # all steps
  python teardown/teardown.py run --only cdc,cai --execute --expect-org <orgIdV3>
  python teardown/teardown.py verify-records [--execute]             # remove the verify.invalid test rows (DB + CRM)
  python teardown/teardown.py clean-local                            # delete state/packages, rendered, harvest

Steps (ids come from state/ids.json):
  backup     v3 export (with dependencies) of every task, mapping, taskflow and CAI asset -> state/backup/
  schedule   unbind tf_rdf_full, then delete sch_rdf_every_4h       (a deleted schedule's GET is an empty 200 shell)
  taskflows  delete tf_rdf_full, tf_rdf_customer
  cai        unpublish (processes -> connection -> connector), then FRS-delete the assets (published = FRS_082)
  tasks      delete mt_rdf_* mapping tasks, then the m_rdf_* mappings (a mapping only once its tasks[] is empty)
  cdc        stop, undeploy, delete both Database Ingestion tasks; then run teardown/pg_teardown.sql (slots!)
  dq         delete the Data Profiling profiles
  glossary   glossary-undo (terms before the domain, read back by search)
  catalog    UI ONLY: REST cannot delete a catalog-source definition (DELETE purges its metadata only)
  connections delete the five connections (last: everything above references them)
  warehouse  bq rm -r -f the four datasets (printed, run it yourself)
  source     docker compose -p rdf down -v (printed, run it yourself)
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "idmc" / "lib"))
SL = "14 - Claude Working Methods & Tooling/Script Library"   # the core library
sys.path.insert(0, str(ROOT / "infra"))
import rdf_common as C  # noqa: E402

VERIFY_DOMAIN = "verify.invalid"      # the e-mail domain verify/e2e_check.py uses for its test sign-ups
LIKE_VERIFY = f"'%@{VERIFY_DOMAIN}'"
ORDER = ["backup", "schedule", "taskflows", "cai", "tasks", "cdc", "dq", "glossary", "catalog", "connections",
         "warehouse", "source"]


def ids(st, key):
    return {k: (v or {}).get("id") for k, v in (st.get(key) or {}).items()}


def steps(cfg, st):
    """[(step, description, [core command args] | None)] in teardown order."""
    out = []
    tasks, maps = ids(st, "tasks"), st.get("mappings") or {}
    tfs, schs = ids(st, "taskflows"), ids(st, "schedules")
    gd = (st.get("cai") or {}).get("guids") or {}
    backup_ids = [t.get("frsGuid") for t in (st.get("tasks") or {}).values() if t.get("frsGuid")] + list(gd.values())
    out.append(("backup", f"export {len(backup_ids)} object(s) with dependencies",
                ["idmc_export_import.py", "export"] + sum((["--id", i] for i in backup_ids), [])
                + ["--out", str(C.STATE_DIR / "backup" / "rdf_backup.zip")] if backup_ids else None))
    for sname, s in cfg["schedules"].items():
        if tfs.get(s["taskflow"]):
            out.append(("schedule", f"unbind {s['taskflow']}", ["idmc_taskflow_schedule.py", "unbind", tfs[s["taskflow"]]]))
        if schs.get(sname):
            out.append(("schedule", f"delete {sname}", ["idmc_frs_delete.py", "v2-delete", "schedule", schs[sname]]))
    for tf in cfg["taskflows"]:
        if tfs.get(tf):
            out.append(("taskflows", f"delete {tf}", ["idmc_frs_delete.py", "v2-delete", "workflow", tfs[tf]]))
    proj, fold = cfg["idmc"]["project"], cfg["idmc"]["folder"]
    c = cfg["cai"]
    paths = [f"Explore/{proj}/{fold}/{p}.PROCESS.xml" for p in c["processes"]] + \
            [f"Explore/{proj}/{fold}/{c['appConnection']}.AI_CONNECTION.xml",
             f"Explore/{proj}/{fold}/{c['serviceConnector']}.AI_SERVICE_CONNECTOR.xml"]
    out.append(("cai", "unpublish the CAI assets", ["idmc_cai_publish.py", "unpublish"] + sum((["--path", p] for p in paths), [])))
    if gd:
        out.append(("cai", "delete the CAI assets (FRS, leaf-first)", ["idmc_frs_delete.py", "delete"] + list(gd.values())))
    for t, tid in tasks.items():
        if tid:
            out.append(("tasks", f"delete task {t}", ["idmc_frs_delete.py", "v2-delete", "mttask", tid]))
    for m, v in maps.items():
        if (v or {}).get("v2Id"):
            out.append(("tasks", f"delete mapping {m}", ["idmc_frs_delete.py", "v2-delete", "mapping", v["v2Id"]]))
        elif (v or {}).get("guid"):
            out.append(("tasks", f"delete mapping {m} (by FRS guid)", ["idmc_frs_delete.py", "delete", v["guid"]]))
    for lane, v in (st.get("cdc") or {}).items():
        tid = (v or {}).get("taskId")
        if tid:
            out += [("cdc", f"stop {lane}", ["idmc_dbmi.py", "stop", str(tid)]),
                    ("cdc", f"undeploy {lane}", ["idmc_dbmi.py", "undeploy", str(tid)])]
            if v.get("frsId"):
                out.append(("cdc", f"delete {lane}", ["idmc_dbmi.py", "delete", str(tid), "--frs-id", v["frsId"]]))
    out.append(("cdc", "then: psql ... -f teardown/pg_teardown.sql (drops slots + publications + the CDC role)", None))
    for n, v in (st.get("dq") or {}).items():
        out.append(("dq", f"delete profile {n} ({(v or {}).get('id')}) - DELETE /profiling-service/api/v1/profile/<id>", None))
    out.append(("glossary", "glossary-undo", ["idmc_cdgc.py", "glossary-undo", "--registry",
                                              str(C.STATE_DIR / "glossary_registry.json")]))
    out.append(("catalog", "UI: Metadata Command Center > Catalog Sources > " + ", ".join(cfg["catalog"]["sources"]) +
                " > Delete (REST cannot delete a source definition)", None))
    for k, v in (st.get("connections") or {}).items():
        if (v or {}).get("id"):
            out.append(("connections", f"delete connection {v.get('name')}", ["idmc_frs_delete.py", "v2-delete", "connection", v["id"]]))
    ds = cfg["warehouse"]["datasets"]
    out.append(("warehouse", "bq rm -r -f " + " ".join(f"<BQ_PROJECT>:{d}" for d in ds.values()), None))
    out.append(("source", "docker compose -p rdf -f infra/docker-compose.yml down -v", None))
    return out


def main():
    ap = C.add_common_args(argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter))
    ap.add_argument("cmd", choices=["plan", "run", "verify-records", "clean-local"])
    ap.add_argument("--only", help="comma list of steps: " + ",".join(ORDER))
    ap.add_argument("--psql")
    ap.add_argument("--all-state", action="store_true", help="clean-local: also delete state/ids.json")
    a = ap.parse_args()
    cfg, st = C.load_config(a.config), C.load_state()
    if a.cmd == "clean-local":
        for d in ("packages", "rendered", "harvest"):
            p = C.STATE_DIR / d
            if p.exists():
                shutil.rmtree(p)
                print("deleted", p.relative_to(ROOT))
        for f in (["ids.json", "glossary_registry.json"] if a.all_state else []):
            if (C.STATE_DIR / f).exists():
                (C.STATE_DIR / f).unlink()
                print("deleted state/" + f)
        return 0
    if a.cmd == "verify-records":
        sql = f"DELETE FROM activation.customer_golden WHERE email LIKE {LIKE_VERIFY}; " \
              f"DELETE FROM public.customers WHERE lower(trim(email)) LIKE {LIKE_VERIFY} RETURNING customer_id;"
        if not a.execute:
            print("[DRY-RUN] psql:", sql)
            print(f"[DRY-RUN] Salesforce: DELETE each Contact WHERE Email LIKE {LIKE_VERIFY} (REST sobjects/Contact/<Id>)")
            return 0
        from pgexec import run_sql
        print("deleted source rows:", run_sql(sql, a.psql))
        sys.path.insert(0, str(ROOT / "verify"))
        import urllib.request
        from e2e_check import sf_query
        recs = sf_query(f"SELECT Id FROM Contact WHERE Email LIKE {LIKE_VERIFY}", cfg["crm"]["apiVersion"])
        print(f"{len(recs)} CRM Contact(s) to delete: delete them in the CRM UI or with the REST DELETE "
              "(the integration user needs Delete on Contact; a small dev org fills up fast)")
        return 0
    only = set(a.only.split(",")) if a.only else set(ORDER)
    rc = 0
    for step, desc, cmd in steps(cfg, st):
        if step not in only:
            continue
        if cmd is None or a.cmd == "plan":
            print(f"[{step}] {desc}" + ("" if cmd is None else f'\n    $ python "{SL}/{cmd[0]}" ' + " ".join(cmd[1:])))
            continue
        print(f"[{step}] {desc}")
        extra = C.gate_args(a) if cmd[1] not in ("export",) else []
        if step == "backup":
            (C.STATE_DIR / "backup").mkdir(parents=True, exist_ok=True)
        rc |= C.core_cli(cmd[0], cmd[1:] + extra)
        if step == "backup" and rc:
            C.die("backup export failed: stopping before any delete")
    return rc


if __name__ == "__main__":
    sys.exit(main())
