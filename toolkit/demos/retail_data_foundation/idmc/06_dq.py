#!/usr/bin/env python3
"""Step 6: Data Quality - CDQ rule specifications bound in Data Profiling profiles, plus address verification.

  python idmc/06_dq.py plan                                   # offline: profiles, columns, rule bindings
  python idmc/06_dq.py build --execute --expect-org <orgIdV3> # create/update the profiles (clone a template profile)
  python idmc/06_dq.py run   --execute --expect-org <orgIdV3> # execute them (a run bills IPUs; ask first)
  python idmc/06_dq.py status                                 # last job state per profile
  python idmc/06_dq.py address --tools                      # read the verify_address input schema (read-only)
  python idmc/06_dq.py address --args-json '{...}' --execute --expect-org <orgIdV3>   # one address, one call

Data Profiling over REST (PROVEN 2026-09, rebuilt 8 profiles in a migration): host <pod>-dqprofile, base
/profiling-service/api/v1, header IDS-SESSION-ID with the v3 session id (one pod rejected the v2 id with 401):
  GET  /profile?limit=200                     list
  GET  /profile/<id>                          full body (the clone template)
  POST /profile        | PUT /profile/<id>    create | update  (body = template minus ids, new source + rules)
  POST /profile/<id>/execute  {}              -> profileJobId;   GET /job/<jobId> -> status
Body rules: source.properties {"dataSourceType": "TOOLKIT_CCI", "sourcePath": "<schema>/TABLE"}; profileableFields =
one DATASOURCEFIELD per column plus one MAPPLETFIELD per rule binding (columnKey 40000 + n); one rule entry per rule
spec per profile; char(n) columns are refused (PROFILE_MDL_00006); jsonb / vector columns abort the whole task.
Rule specifications themselves have no create verb (405): import them as a package or author them once in the UI,
then put their frsIds in config.json dq.ruleSpecs. The warehouse DQ (dq_results / dq_scorecard) is the mapping
m_rdf_dq_scorecard and needs none of this.
"""
import argparse
import copy
import json
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "lib"))
sys.path.insert(0, str(HERE.parent / "infra"))
import rdf_common as C  # noqa: E402

API = "/profiling-service/api/v1"


def pg_fields(cfg, table, psql=None):
    from pgexec import run_sql
    from pgexec import q
    sch = cfg["source"]["schema"]
    rows = run_sql("select column_name, data_type, coalesce(character_maximum_length,0), coalesce(numeric_precision,0), "
                   "coalesce(numeric_scale,0), ordinal_position from information_schema.columns "
                   f"where table_schema={q(sch)} and table_name={q(table)} order by ordinal_position;", psql)  # nosec B608  # values quoted by q()
    out = []
    for line in rows:
        n, t, clen, np_, ns, pos = line.split("\t")
        clen, np_, ns = int(clen), int(np_), int(ns)
        if t in ("text", "character varying", "uuid"):
            ft = ("varchar" if t == "character varying" else "text", "NSTRING", clen or 4000, 0)
        elif t == "numeric":
            ft = ("numeric", "DECIMAL", np_ or 28, ns if np_ else 8)
        elif t in ("bigint", "integer"):
            ft = (t, "DECIMAL", 19 if t == "bigint" else 10, 0)
        elif t.startswith("timestamp"):
            ft = ("timestamp_with_time_zone" if "with time zone" in t else "timestamp", "TOOLKIT_DATETIME", 32, 0)
        else:
            continue   # character(n), boolean, jsonb, arrays: not profiled
        out.append({"name": n, "dataType": ft[0], "precision": ft[2], "scale": ft[3], "pcType": ft[1],
                    "order": int(pos) - 1, "isDeleted": False, "isMetadataUpdated": False})
    return out


def rule_block(rs, col, field, n):
    rule = {"name": rs["name"], "description": f"{rs['name']} on {col}", "frsId": rs["frsId"],
            "inFields": [{"name": rs["in"], "label": None, "dataType": "string", "precision": 200, "scale": 0, "isDeleted": False}],
            "outFields": [{"name": rs["out"], "label": None, "dataType": "string", "precision": 100, "scale": 0, "isDeleted": False}],
            "isDeleted": False, "ruleType": "RULE_SPECIFICATION"}
    pf = {"isDeleted": False, "frsId": rs["frsId"], "scoreCardId": None, "assignmentIdentifier": uuid.uuid4().hex,
          "inputFieldMappings": [{"dataSourceFieldName": col, "inFieldName": rs["in"], "isDeleted": False,
                                  "dataSourceFieldPrecision": field["precision"], "dataSourceFieldScale": field["scale"]}],
          "outputFieldMappings": [{"columnKey": 40000 + n, "datatype": "string", "outFieldName": rs["out"], "label": None,
                                   "isDeleted": False}],
          "fieldType": "MAPPLETFIELD", "ruleType": "RULE_SPECIFICATION"}
    return rule, pf


def profile_body(tpl, name, table, fields, bindings, cfg, st):
    body = copy.deepcopy(tpl)
    for k in ("id", "profileKey", "version", "frsId", "createdBy", "createdByName", "createTime", "updatedBy",
              "updatedByName", "updateTime", "lastRunKey"):
        body.pop(k, None)
    fold = st.get("folder") or {}
    body.update(name=name, description=f"[{cfg['idmc']['tag']}] data quality profile of {table}",
                frsProjectId=fold.get("projectGuid"), frsFolderId=fold.get("guid"),
                connectionId=((st.get("connections") or {}).get("pg") or {}).get("guid"))
    (body.get("runtimeOptions") or {}).pop("id", None)
    src = body["source"]
    src.pop("id", None)
    src.update(name=table, fields=fields, rules=[])
    src["properties"] = {"dataSourceType": "TOOLKIT_CCI", "sourcePath": f"{cfg['source']['schema']}/TABLE"}
    body["profileableFields"] = [{"isDeleted": False, "appliedBy": "USER", "columnKey": 10001 + i, "sourceName": table,
                                  "fieldName": f["name"], "precision": f["precision"], "scale": f["scale"],
                                  "fieldType": "DATASOURCEFIELD"} for i, f in enumerate(fields)]
    byname = {f["name"]: f for f in fields}
    seen = set()
    for n, (col, rk) in enumerate(bindings, start=1):
        rs = cfg["dq"]["ruleSpecs"].get(rk) or {}
        if not rs.get("frsId") or col not in byname:
            print(f"   skip binding {col}:{rk} (no frsId in config, or column missing)")
            continue
        rule, pf = rule_block(rs, col, byname[col], n)
        if rs["frsId"] not in seen:            # one rule entry per rule spec per profile
            src["rules"].append(rule)
            seen.add(rs["frsId"])
        body["profileableFields"].append(pf)
    return body


def main():
    ap = C.add_common_args(argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter))
    ap.add_argument("cmd", choices=["plan", "build", "run", "status", "address"])
    ap.add_argument("names", nargs="*")
    ap.add_argument("--psql", help="psql command for column metadata (default: docker compose exec)")
    ap.add_argument("--address", help="address: one free-text address to verify")
    ap.add_argument("--args-json", help="address: the tool arguments as JSON, shaped as the tool's input schema "
                                        "(read it first: core idmc_mcp.py tools --server dqverifyaddress --auth session)")
    ap.add_argument("--tools", action="store_true", help="address: only list the tool's input schema (read-only)")
    a = ap.parse_args()
    cfg, st = C.load_config(a.config), C.load_state()
    profs = {k: v for k, v in cfg["dq"]["profiles"].items() if not a.names or k in a.names}
    if a.cmd == "plan":
        for n, p in profs.items():
            print(f"{n}: {cfg['source']['schema']}.{p['table']}  rules: " +
                  ", ".join(f"{c}->{r}{'' if cfg['dq']['ruleSpecs'].get(r, {}).get('frsId') else ' (no frsId yet)'}"
                            for c, r in p["bindings"]))
        print(f"template profile: '{cfg['dq'].get('templateProfileName') or '<set dq.templateProfileName>'}'")
        print(f"address verification: MCP {cfg['dq']['addressVerification']['mcpContext']} / "
              f"{cfg['dq']['addressVerification']['tool']}, max {cfg['dq']['addressVerification']['maxCallsPerRun']} calls per run")
        return 0
    if a.cmd == "address":
        av = cfg["dq"]["addressVerification"]
        if a.tools:
            return C.core_cli("idmc_mcp.py", ["tools", "--server", av["mcpContext"], "--auth", "session"])
        args = a.args_json or json.dumps({"address": a.address or "1 Main St, Springfield, IL 62701, US"})
        return C.core_cli("idmc_mcp.py", ["call", "--server", av["mcpContext"], "--tool", av["tool"], "--args-json",
                                          args, "--auth", "session"] + C.gate_args(a))
    C.offline_session_guard(a)
    from idmc_session import Session
    import idmc_http as H
    S = Session()
    gate = H.WriteGate(a, S)
    have = {p["name"]: p for p in (S.get("profiling", API + "/profile?limit=200").json([]) or [])}
    st.setdefault("dq", {})
    if a.cmd == "build":
        tname = cfg["dq"].get("templateProfileName")
        if not tname or tname not in have:
            C.die("set dq.templateProfileName to an existing Data Profiling profile on a PostgreSQL connection "
                  "(create one in the UI once: UI-only wall for the first profile of an org)")
        tpl = S.get("profiling", f"{API}/profile/{have[tname]['id']}").json({}) or {}
        for n, p in profs.items():
            body = profile_body(tpl, n, p["table"], pg_fields(cfg, p["table"], a.psql), p["bindings"], cfg, st)
            if n in have:
                r = gate.send(f"update profile {n}", "profiling", "PUT", f"{API}/profile/{have[n]['id']}", body=body)
            else:
                r = gate.send(f"create profile {n}", "profiling", "POST", f"{API}/profile", body=body)
            if r is not None:
                pid = (r.json({}) or {}).get("id") if r.ok else None
                st["dq"][n] = {"id": pid or (have.get(n) or {}).get("id")}
                print(f"   -> HTTP {r.status} id {st['dq'][n]['id']}")
    elif a.cmd == "run":
        for n in profs:
            pid = (st["dq"].get(n) or {}).get("id") or (have.get(n) or {}).get("id")
            if not pid:
                print(f"{n}: not built")
                continue
            r = gate.send(f"execute {n}", "profiling", "POST", f"{API}/profile/{pid}/execute", body={})
            if r is not None:
                st["dq"].setdefault(n, {})["job"] = (r.json({}) or {}).get("profileJobId")
                print(f"   job {st['dq'][n]['job']}")
    else:
        for n in profs:
            job = (st["dq"].get(n) or {}).get("job")
            j = S.get("profiling", f"{API}/job/{job}").json({}) if job else {}
            print(f"{n}: job {job} status {(j or {}).get('status')} {(j or {}).get('errorMessage') or ''}")
    if gate.execute:
        C.save_state(st)
    return 0


if __name__ == "__main__":
    sys.exit(main())
