#!/usr/bin/env python3
"""cdi_batch.py - the nightly CDI batch: ops-ledger Postgres -> Oracle, one mapping task per table, one taskflow, one schedule.

  python idmc/cdi_batch.py connections [--test]        create (or find) mbr_ledger_pg (PostgreSQL) + mbr_oracle (Oracle)
  python idmc/cdi_batch.py tasks                       clone one mapping task per table over the Copy Data template
  python idmc/cdi_batch.py taskflow                    linear taskflow tf_mbr_nightly_batch over the tasks
  python idmc/cdi_batch.py schedule --start-utc 2026-01-02T07:30:00Z [--interval Daily]   create unbound + bind
  python idmc/cdi_batch.py run                         ONE on-demand taskflow run (uses 1 + 3 jobs: ask first)
Every write: --execute --expect-org <orgIdV3>; otherwise a dry run. Passwords come from the toolkit .env by key name.

How (and why):
- Connections are v2 `POST /api/v2/connection`. PostgreSQL = the native connector, `type TOOLKIT_CCI`,
  `instanceName PostgreSQL`, `connParams` with `userName` (not `user`) and an `authenticationType` whose accepted value
  drifts by pod: copy the key set from a working connection on your pod (KB 02/04). Oracle = `type Oracle` with host,
  port, database (= the service name FREEPDB1), schema, codepage, username, password (PROVEN in the source build).
- Tasks reuse the core script idmc_mttask.py `clone` over a task of the Add-On Bundle template
  dsst__copy_data_new_tgt (PROVEN pattern: one task per table, customQuery source, truncate target). ADAPTED here for
  an Oracle target: re-check `tgtObjectAttributes` / the target object on the first task in your org.
- Taskflow + schedule reuse idmc_taskflow_schedule.py (`upsert`, `schedule-create` unbound, `bind`).
- The source build loaded Oracle from a generated multi-table mapping; this blueprint uses the simpler Copy Data
  tasks so it needs no mapping generator (ADAPTED).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
import mbr_config as CFG  # noqa: E402

CORE = CFG.use_core()
import idmc_http as H  # noqa: E402
from idmc_session import Session  # noqa: E402

HERE = Path(__file__).resolve().parent


def find_conn(S, name):
    r = S.get("v2", "/api/v2/connection/name/" + name)
    d = r.json({}) if r.ok else None
    return d if isinstance(d, dict) and d.get("id") else None


LOOPBACK = {"localhost", "127.0.0.1", "::1", "[::1]"}


def pg_tls(host):
    """TLS with server-certificate validation for any ledger host except loopback. The loopback stand-in
    (infra/docker-compose.yml, postgres:16-alpine without a server certificate, published on 127.0.0.1 only, the agent on
    the same host) is the one case that keeps encryption off."""
    if str(host).strip().lower() in LOOPBACK:
        return {"encryptionMethod": "noEncryption"}
    return {"encryptionMethod": "SSL", "tlsv1_2": "true", "validateServerCertificate": "true"}


def conn_bodies(cfg):
    b, re_id = cfg["cdi_batch"], cfg["agent"]["runtime_environment_id"]
    pg, ora = b["postgres"], b["oracle"]
    pg_body = {"@type": "connection", "name": b["postgres_connection"], "type": "TOOLKIT_CCI", "instanceName": "PostgreSQL",
               "runtimeEnvironmentId": re_id, "description": "Message Bus Replacement: ops ledger (read only, nightly batch)",
               "connParams": {"hostName": pg["host"], "port": str(pg["port"]), "database": pg["database"],
                              "userName": "mbr_batch_reader", "password": "<MBR_CDI_PG_PASSWORD>",  # nosec B105  # placeholder text, not a secret
                              "authenticationType": "UserIdPassword", **pg_tls(pg["host"])}}
    ora_body = {"@type": "connection", "name": b["oracle_connection"], "type": "Oracle", "runtimeEnvironmentId": re_id,
                "description": "Message Bus Replacement: nightly batch target", "host": ora["host"], "port": int(ora["port"]),
                "database": ora["service"], "schema": ora["schema"], "codepage": "UTF-8", "username": ora["schema"],
                "password": "<MBR_ORACLE_BATCH_PASSWORD>"}  # nosec B105  # placeholder text, not a secret
    return [(pg_body, "MBR_CDI_PG_PASSWORD"), (ora_body, "MBR_ORACLE_BATCH_PASSWORD")]


def fill_secret(body, key):
    v = CFG.env_value(key)
    if not v:
        H.die(f"{key} not found in the environment or the toolkit .env")
    s = json.dumps(body).replace(f"<{key}>", v.replace("\\", "\\\\").replace('"', '\\"'))
    return json.loads(s)


def cmd_connections(S, gate, cfg, test):
    ids = CFG.state_get("ids.json", {})
    for body, key in conn_bodies(cfg):
        name = body["name"]
        have = find_conn(S, name)
        if have:
            print(f"connection {name} exists: {have['id']}")
            ids.setdefault("connections", {})[name] = have["id"]
        else:
            masked = json.loads(json.dumps(body))           # the gate prints this body: secret still a placeholder
            print(f"create {name} (password from {key}, not shown)")
            if not gate.execute:
                gate.send(f"create connection {name}", "v2", "POST", "/api/v2/connection", body=masked)
                continue
            r = gate.send(f"create connection {name}", "v2", "POST", "/api/v2/connection", body=fill_secret(body, key))
            d = r.json({}) if r is not None else {}
            if not r.ok or not d.get("id"):
                H.die(f"create {name} failed HTTP {r.status} {H.preview(H.redact(d), 400)}")
            ids.setdefault("connections", {})[name] = d["id"]
        if test and ids.get("connections", {}).get(name):
            r = S.get("v2", "/api/v2/connection/test/" + ids["connections"][name], timeout=300)
            print(f"  test {name}: HTTP {r.status} {H.preview(H.redact(r.json({}) or {}), 300)}")
    if gate.execute:
        CFG.state_put("ids.json", ids)


def core(script, *args, gate_args=()):
    cmd = [sys.executable, str(CORE / script), *args, *gate_args]
    print("  $", " ".join(a if " " not in a else f'"{a}"' for a in cmd[1:]))
    return subprocess.run(cmd, check=False).returncode


def gate_args(a):
    out = []
    if a.execute and not a.dry_run:
        out += ["--execute", "--expect-org", a.expect_org or ""]
    if a.log:
        out += ["--log", a.log]
    return out


def task_ids(S, names):
    r = S.get("v2", "/api/v2/task?type=MTT")
    rows = r.json([]) if r.ok else []
    by = {}
    for t in rows if isinstance(rows, list) else []:
        by.setdefault(t.get("name"), []).append(t.get("id"))
    return {n: (by.get(n) or [None])[0] if len(by.get(n) or []) <= 1 else "AMBIGUOUS" for n in names}


def cmd_tasks(S, a, cfg):
    b = cfg["cdi_batch"]
    ids = CFG.state_get("ids.json", {})
    conns = ids.get("connections", {})
    src, tgt = conns.get(b["postgres_connection"]), conns.get(b["oracle_connection"])
    if not (src and tgt):
        print("connection ids missing in state/ids.json: run `cdi_batch.py connections --execute ...` first; showing the plan")
    if CFG.placeholders(cfg, ["cdi_batch.template_task_id"]):
        H.die("set cdi_batch.template_task_id in config.json (BUILD.md step 9)")
    for t in b["tasks"]:
        core("idmc_mttask.py", "clone", "--template", b["template_task_id"], "--name", t["name"],
             "--desc", f"Message Bus Replacement nightly batch -> {t['target']}", "--source-conn", src or "<pg conn id>",
             "--query-file", str(HERE / t["query"]), "--target-conn", tgt or "<oracle conn id>",
             "--target", f"{b['oracle']['schema']}/{t['target']}", "--disposition", "truncate",
             "--re", cfg["agent"]["runtime_environment_id"], "--tag", cfg["project"]["tag"], gate_args=gate_args(a))
    if a.execute and not a.dry_run:
        found = task_ids(S, [t["name"] for t in b["tasks"]])
        ids["tasks"] = found
        CFG.state_put("ids.json", ids)
        print("task ids:", found)


def cmd_taskflow(a, cfg):
    tids = CFG.state_get("ids.json", {}).get("tasks") or {}
    names = [t["name"] for t in cfg["cdi_batch"]["tasks"]]
    args = ["upsert", "--name", cfg["cdi_batch"]["taskflow"], "--desc", "Message Bus Replacement: nightly batch into Oracle"]
    for n in names:
        args += ["--task", tids.get(n) or f"<id of {n}>"]
    core("idmc_taskflow_schedule.py", *args, gate_args=gate_args(a))
    if a.execute and not a.dry_run:
        remember(Session(), "workflow", cfg["cdi_batch"]["taskflow"], "taskflow_id")


def by_name(S, resource, name):
    """v2 id of a workflow / schedule by exact name (exactly one match)."""
    r = S.get("v2", f"/api/v2/{resource}")
    rows = r.json([]) if r.ok else []
    hits = [x.get("id") for x in rows if isinstance(rows, list) and x.get("name") == name]
    return hits[0] if len(hits) == 1 else None


def remember(S, resource, name, key):
    ids = CFG.state_get("ids.json", {})
    ids[key] = by_name(S, resource, name)
    CFG.state_put("ids.json", ids)
    print(f"{key} = {ids[key]}")
    return ids[key]


def cmd_schedule(a, cfg):
    s = cfg["cdi_batch"]["schedule"]
    core("idmc_taskflow_schedule.py", "schedule-create", "--name", s["name"], "--interval", a.interval, "--start-utc", a.start_utc,
         "--desc", "Message Bus Replacement nightly batch", gate_args=gate_args(a))
    ids = CFG.state_get("ids.json", {})
    wf, sch = ids.get("taskflow_id") or "<taskflow id>", "<schedule id>"
    if a.execute and not a.dry_run:
        sch = remember(Session(), "schedule", s["name"], "schedule_id") or sch
    core("idmc_taskflow_schedule.py", "bind", wf, sch, gate_args=gate_args(a))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__.split("\n\n", 1)[1])
    ap.add_argument("--config")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = H.add_gate_args(sub.add_parser("connections"))
    c.add_argument("--test", action="store_true")
    H.add_gate_args(sub.add_parser("tasks"))
    H.add_gate_args(sub.add_parser("taskflow"))
    sc = H.add_gate_args(sub.add_parser("schedule"))
    sc.add_argument("--start-utc", required=True)
    sc.add_argument("--interval", default="Daily")
    H.add_gate_args(sub.add_parser("run"))
    a = ap.parse_args()
    cfg = CFG.load(a.config)
    H.safe_console()
    if a.cmd == "connections":
        S = Session()
        cmd_connections(S, H.WriteGate(a, S), cfg, a.test)
    elif a.cmd == "tasks":
        cmd_tasks(Session() if a.execute else None, a, cfg)
    elif a.cmd == "taskflow":
        cmd_taskflow(a, cfg)
    elif a.cmd == "schedule":
        cmd_schedule(a, cfg)
    else:
        print("A taskflow run uses 1 job + 1 per task against the org's monthly job budget.")
        core("idmc_taskflow_schedule.py", "run", CFG.state_get("ids.json", {}).get("taskflow_id") or "<taskflow id>",
             gate_args=gate_args(a))


if __name__ == "__main__":
    main()
