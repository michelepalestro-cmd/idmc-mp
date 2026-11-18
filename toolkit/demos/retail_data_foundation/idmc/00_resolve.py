#!/usr/bin/env python3
"""Step 0: prove the org and resolve every per-org id BY NAME into state/ids.json (read-only, except --create-home).

  python idmc/00_resolve.py --offline                 # no network: show what will be resolved and from where
  python idmc/00_resolve.py                           # login (one attempt), resolve, write state/ids.json
  python idmc/00_resolve.py --create-home --execute --expect-org <orgIdV3>   # also create the project + folder

Resolves:
  org                 GET /api/v2/org (v2 id) + orgUuid (the 22-char v3 org id), cross-checked by the core guard
  runtimeEnvironment  GET /api/v2/runtimeEnvironment, matched on config idmc.runtimeEnvironment
  connections         GET /api/v2/connection, matched on config connections.* names:
                      v2 "id" (repoHandle), "federatedId" (the FRS guid a mapping binds with saas:@<guid>), kind
  project / folder    v3 objects of type Project / Folder (their ids are the FRS guids MoveEntities needs)
Names are the source of truth: ids copied from another org go stale after a migration (re-run this step instead).
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
import rdf_common as C  # noqa: E402

KIND = {"googlebigqueryv2": "BQ", "google big query v2": "BQ", "google bigquery v2": "BQ", "postgresql": "PG",
        "salesforce": "SF", "jdbcv2": "JDBC"}


def kind_of(c):
    for k in (c.get("instanceName"), c.get("instanceDisplayName"), c.get("type")):
        if k and k.lower() in KIND:
            return KIND[k.lower()]
    g = (c.get("connectorGuid") or "").lower()
    return "BQ" if "bigquery" in g else "PG" if "postgres" in g else "SF" if "salesforce" in g else None


def main():
    ap = C.add_common_args(argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter))
    ap.add_argument("--offline", action="store_true", help="no network; print the plan")
    ap.add_argument("--create-home", action="store_true", help="create the project/folder when missing (a write)")
    a = ap.parse_args()
    cfg = C.load_config(a.config)
    names = cfg["connections"]
    if a.offline:
        print("would resolve (read-only):")
        print(f"  org                 GET v2 /api/v2/org  (+ v3 orgUuid)")
        print(f"  runtimeEnvironment  '{cfg['idmc']['runtimeEnvironment']}'")
        for k, n in names.items():
            print(f"  connection {k:7}  '{n}'")
        print(f"  project / folder    '{cfg['idmc']['project']}' / '{cfg['idmc']['folder']}'")
        print("credentials needed:", ", ".join(f"{k}={s}" for k, s in C.env_status(["IDMC_USER", "IDMC_PASS", "IDMC_LOGIN_HOST"])))
        return 0
    C.offline_session_guard(a)
    from idmc_session import Session
    import idmc_http as H
    import idmc_objects as O
    S = Session()
    gate = H.WriteGate(a, S)
    st = C.load_state()
    org = S.get("v2", "/api/v2/org").json({}) or {}
    st["org"] = {"v2Id": org.get("id"), "guid": org.get("orgUuid") or S.v2().get("orgUuid"), "name": org.get("name")}
    print(f"org: v2 {st['org']['v2Id']}  v3 {st['org']['guid']}  '{st['org']['name']}'")
    res = [r for r in S.get("v2", "/api/v2/runtimeEnvironment").json([]) or []
           if r.get("name") == cfg["idmc"]["runtimeEnvironment"]]
    if len(res) != 1:
        C.die(f"runtime environment '{cfg['idmc']['runtimeEnvironment']}': {len(res)} match(es); fix config idmc.runtimeEnvironment")
    st["runtimeEnvironment"] = {"id": res[0]["id"], "name": res[0]["name"]}
    print(f"runtimeEnvironment: {res[0]['id']} '{res[0]['name']}'")
    conns = S.get("v2", "/api/v2/connection").json([]) or []
    st.setdefault("connections", {})
    for key, name in names.items():
        hit = [c for c in conns if c.get("name") == name]
        if len(hit) == 1:
            c = hit[0]
            st["connections"][key] = {"id": c.get("id"), "guid": c.get("federatedId"), "name": name, "kind": kind_of(c)}
            print(f"connection {key}: {c.get('id')} guid={c.get('federatedId')} kind={kind_of(c)}")
        else:
            print(f"connection {key}: '{name}' {len(hit)} match(es) (create it in step 1, then re-run this step)")
    proj, fold = cfg["idmc"]["project"], cfg["idmc"]["folder"]
    projects = [o for o in O.list_objects(S, q="type=='Project'") if (o.get("path") or "").strip("/") == proj]
    if not projects and a.create_home:
        r = gate.send("create project", "v3", "POST", "/public/core/v3/projects",
                      body={"name": proj, "description": f"[{cfg['idmc']['tag']}] Retail Data Foundation demo"})
        if r is not None and r.ok:
            projects = [{"id": (r.json({}) or {}).get("id"), "path": proj}]
    if projects:
        pid = projects[0]["id"]
        folders = [o for o in O.list_objects(S, q="type=='Folder'") if (o.get("path") or "").strip("/") == f"{proj}/{fold}"]
        if not folders and a.create_home:
            r = gate.send("create folder", "v3", "POST", f"/public/core/v3/projects/{pid}/folders",
                          body={"name": fold, "description": f"[{cfg['idmc']['tag']}]"})
            if r is not None and r.ok:
                folders = [{"id": (r.json({}) or {}).get("id")}]
        st["folder"] = {"project": proj, "projectGuid": pid, "name": fold,
                        "guid": folders[0]["id"] if folders else None, "path": f"{proj}/{fold}"}
        print(f"project {pid}  folder {st['folder']['guid']}")
    else:
        print(f"project '{proj}' not found (re-run with --create-home --execute --expect-org <orgIdV3>)")
    print("wrote", C.save_state(st).relative_to(C.BLUEPRINT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
