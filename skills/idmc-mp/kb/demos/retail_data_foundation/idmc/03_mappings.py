#!/usr/bin/env python3
"""Step 3: the consolidated CDI mappings, generated headless (spec -> IMF JSON -> package -> v3 import -> mapping task).

  python idmc/03_mappings.py build --offline        # compile + lint + package all 6 specs, no network (placeholder ids)
  python idmc/03_mappings.py build                  # same with the real ids from state/ids.json (after 00_resolve)
  python idmc/03_mappings.py import --execute --expect-org <orgIdV3> [--mode REUSE|OVERWRITE] [--only m_rdf_x]
  python idmc/03_mappings.py tasks  --execute --expect-org <orgIdV3>     # create/repoint mt_rdf_*, move into the folder
  python idmc/03_mappings.py run m_rdf_customer_golden --execute --expect-org <orgIdV3>   # one job; costs IPUs

How (PROVEN 2026-09 with the same generator: 11 mappings parity-green, then 9 complex scenarios exact):
  1. the specs (idmc/mappings/rdf_specs.py) are compiled by the toolkit's shared generator core/mapgen (stdlib only);
     a profile built from config.json + state/ids.json supplies the org, folder, connection guids and ${VARS}
  2. lint blocks known runtime traps (OUTPUT ports referencing OUTPUT ports, >5 BigQuery readers, DATE/JSON types,
     comments or non-ASCII in SQL, BigQuery targets without the 1 s poll interval, dangling links)
  3. the DTEMPLATE package is imported with the core idmc_export_import (REUSE the first time, OVERWRITE to rebuild
     under the SAME guid: the guid of every mapping is kept in state/ids.json)
  4. POST /api/v2/mttask {"@type":"mtTask","name","mappingId":<v2 mapping id>,"runtimeEnvironmentId"} -> born in
     Default -> FRS MoveEntities into the project folder; an existing task is re-pointed (GET, edit, POST to its id)
Retargeting a finished mapping: rebuild its package with the new targets and import OVERWRITE. POSTing new target
parameters to its task returns 200 and changes nothing.
"""
import argparse
import copy
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "lib"))
sys.path.insert(0, str(HERE.parents[2] / "core" / "mapgen"))  # the toolkit's shared mapping generator
sys.path.insert(0, str(HERE / "mappings"))
import rdf_common as C  # noqa: E402
import rdf_specs  # noqa: E402

SQL_DIR = HERE / "sql"
PKG_DIR = C.STATE_DIR / "packages"
PH = {"project": "OFFLINEprojectGuid0001", "folder": "OFFLINEfolderGuid00001", "org": "OFFLINEorgGuid00000001",
      "PG": "OFFLINEconnGuidPG0001", "WH": "OFFLINEconnGuidWH0001", "SF": "OFFLINEconnGuidSF0001"}


def expand_sql(name, seen=()):
    if name in seen:
        C.die(f"include loop at {name}")
    text = (SQL_DIR / name).read_text(encoding="utf-8")
    text = re.sub(r"\{\{include ([\w.]+)\}\}", lambda m: expand_sql(m.group(1), seen + (name,)), text)
    return text


def query_text(name):
    return C.clean_sql(expand_sql(name))


def profile(cfg, st, offline):
    v = C.template_vars(cfg, offline=offline)
    conns = st.get("connections") or {}

    def conn(alias, key, kind):
        c = conns.get(key) or {}
        if not offline and not (c.get("guid") and c.get("id")):
            C.die(f"connection '{cfg['connections'][key]}' has no ids in state/ids.json: run 01_connections.py + 00_resolve.py "
                  "(or use --offline)")
        return {"guid": c.get("guid") or PH[alias], "name": cfg["connections"][key],
                "repoHandle": c.get("id") or f"OFFLINE_{alias}", "kind": kind}

    fold = st.get("folder") or {}
    if not offline and not fold.get("guid"):
        C.die("no project/folder ids in state/ids.json: run 00_resolve.py --create-home first (or use --offline)")
    org = st.get("org") or {}
    return {
        "org": {"v2Id": org.get("v2Id") or "OFFLINE", "guid": org.get("guid") or PH["org"], "name": org.get("name") or "offline"},
        "runtimeEnvironment": st.get("runtimeEnvironment") or {"id": "OFFLINE_RE", "name": cfg["idmc"]["runtimeEnvironment"]},
        "folder": {"project": cfg["idmc"]["project"], "projectGuid": fold.get("projectGuid") or PH["project"],
                   "name": cfg["idmc"]["folder"], "guid": fold.get("guid") or PH["folder"]},
        "connections": {"PG": conn("PG", "pg", "PG"), "WH": conn("WH", "bq", "BQ"), "SF": conn("SF", "sf", "SF")},
        "vars": {k: str(x) for k, x in v.items()},
    }


def prepared_specs(cfg, st, only=None):
    out = []
    for sp in rdf_specs.all_specs():
        if only and sp["name"] not in only:
            continue
        sp = copy.deepcopy(sp)
        for nd in sp["nodes"]:
            if "queryFile" in nd:
                nd["query"] = query_text(nd.pop("queryFile"))
        g = ((st.get("mappings") or {}).get(sp["name"]) or {}).get("guid")
        if g:
            sp["guid"] = g                      # rebuild under the SAME guid (import OVERWRITE)
        out.append(sp)
    return out


def cmd_build(a, cfg, st):
    from idmc_mapgen import lint as L
    from idmc_mapgen.spec import load_spec
    from idmc_mapgen.compile import build
    from idmc_mapgen.package import package_bytes
    prof = profile(cfg, st, a.offline)
    PKG_DIR.mkdir(parents=True, exist_ok=True)
    errors = 0
    st.setdefault("mappings", {})
    for sp in prepared_specs(cfg, st, a.only):
        issues = L.lint(copy.deepcopy(sp), profile=prof, allow_live=True)
        errs = [i for i in issues if getattr(i, "severity", None) == "ERROR" or (isinstance(i, tuple) and i[1] == "ERROR")]
        warns = [i for i in issues if i not in errs]
        for i in errs + warns:
            print(f"  [{'ERROR' if i in errs else 'warn '}] {sp['name']}: {getattr(i, 'code', i[0])} "
                  f"{getattr(i, 'message', '') or (i[3] if isinstance(i, tuple) else '')}"[:300])
        if errs:
            errors += 1
            continue
        spec = load_spec(sp, profile=prof)
        imf = build(spec)
        pkg = package_bytes(spec, imf)
        p = PKG_DIR / f"{spec['name']}.pkg.zip"
        p.write_bytes(pkg)
        (PKG_DIR / f"{spec['name']}.imf.json").write_text(json.dumps(imf, indent=1), encoding="utf-8")
        ntx = len(imf["content"]["transformations"])
        print(f"OK {spec['name']}: {ntx} transformations, {len(imf['content']['links'])} links, guid {spec['guid']} "
              f"-> {p.relative_to(C.BLUEPRINT)}")
        if not a.offline:
            st["mappings"].setdefault(spec["name"], {})["guid"] = spec["guid"]
    if not a.offline:
        C.save_state(st)
    if a.offline:
        print("offline build: packages carry PLACEHOLDER ids - rebuild without --offline before importing")
    return 1 if errors else 0


def offline_package(zbytes):
    """True when a package (or the DTEMPLATE zip inside it) carries a placeholder id of an --offline build"""
    import io
    import zipfile
    with zipfile.ZipFile(io.BytesIO(zbytes)) as z:
        for n in z.namelist():
            data = z.read(n)
            if b"OFFLINE" in data or (n.endswith(".zip") and offline_package(data)):
                return True
    return False


def cmd_import(a, cfg, st):
    rc = 0
    for sp in prepared_specs(cfg, st, a.only):
        p = PKG_DIR / f"{sp['name']}.pkg.zip"
        if not p.exists():
            C.die(f"{p.name} missing: run build first")
        if offline_package(p.read_bytes()):
            C.die(f"{p.name} was built --offline (placeholder ids): rebuild without --offline")
        rc |= C.core_cli("idmc_export_import.py", ["import", str(p), "--mode", a.mode, "--name", f"rdf_{sp['name']}"]
                         + C.gate_args(a))
    return rc


def cmd_tasks(a, cfg, st):
    C.offline_session_guard(a)
    from idmc_session import Session
    import idmc_http as H
    import idmc_objects as O
    S = Session()
    gate = H.WriteGate(a, S)
    re_id = (st.get("runtimeEnvironment") or {}).get("id") or C.die("no runtime environment id: run 00_resolve.py")
    fold = st.get("folder") or {}
    folder_path = fold.get("path") or C.die("no folder in state: run 00_resolve.py --create-home")
    maps = S.get("v2", "/api/v2/mapping").json([]) or []
    tasks = S.get("v2", "/api/v2/mttask").json([]) or []
    st.setdefault("tasks", {})
    for sp in prepared_specs(cfg, st, a.only):
        guid = ((st.get("mappings") or {}).get(sp["name"]) or {}).get("guid")
        cand = [m for m in maps if m.get("name") == sp["name"]]
        mp = next((m for m in cand if not guid or m.get("assetFrsGuid") in (None, guid)), None)
        if not mp:
            print(f"{sp['name']}: no imported mapping found (import first)")
            continue
        st.setdefault("mappings", {}).setdefault(sp["name"], {})["v2Id"] = mp["id"]
        tname, desc = sp["taskName"], C.render(sp["description"], {"TAG": cfg["idmc"]["tag"]})
        same = [t for t in tasks if t.get("name") == tname]
        if len(same) > 1:
            print(f"{tname}: {len(same)} tasks with this name, refusing (address by id)")
            continue
        if same:
            cur = S.get("v2", f"/api/v2/mttask/{same[0]['id']}").json({}) or {}
            if cur.get("mappingId") == mp["id"] and cur.get("runtimeEnvironmentId") == re_id:
                print(f"{tname}: up to date ({cur['id']})")
                st["tasks"][tname] = {"id": cur["id"], "frsGuid": cur.get("frsGuid")}
                continue
            body = {k: v for k, v in cur.items() if k not in ("orgId", "createTime", "updateTime", "createdBy", "updatedBy")}
            body.update(mappingId=mp["id"], runtimeEnvironmentId=re_id)
            r = gate.send(f"repoint {tname}", "v2", "POST", f"/api/v2/mttask/{cur['id']}", body=body)
            tid = cur["id"]
        else:
            r = gate.send(f"create {tname}", "v2", "POST", "/api/v2/mttask",
                          body={"@type": "mtTask", "name": tname, "description": desc, "mappingId": mp["id"],
                                "runtimeEnvironmentId": re_id})
            tid = ((r.json({}) or {}).get("id") if r is not None and r.ok else None)
        if r is None:
            continue
        if not r.ok or not tid:
            print(f"    FAILED HTTP {r.status} {r.head(300)}")
            continue
        back = S.get("v2", f"/api/v2/mttask/{tid}").json({}) or {}
        st["tasks"][tname] = {"id": tid, "frsGuid": back.get("frsGuid")}
        in_folder = [o for o in O.list_objects(S, q="type=='MTT'") if (o.get("path") or "").startswith(folder_path + "/")
                     and o.get("id") == back.get("frsGuid")]
        if not in_folder and back.get("frsGuid"):
            mv = C.frs_move(S, gate, back["frsGuid"], fold["guid"], tname)
            print(f"    move: HTTP {getattr(mv, 'status', '-')} {mv.head(160) if mv is not None else ''}")
            gate.send("tag", "v3", "POST", "/public/core/v3/TagObjects", body=[{"id": back["frsGuid"], "tags": [cfg["idmc"]["tag"]]}])
        print(f"    {tname}: id {tid} mapping {back.get('mappingId')} RE {back.get('runtimeEnvironmentId')}")
    if gate.execute:
        C.save_state(st)
    return 0


def cmd_run(a, cfg, st):
    names = [n if n.startswith("mt_") else "mt" + n[1:] for n in a.names]
    rc = 0
    for n in names:
        tid = ((st.get("tasks") or {}).get(n) or {}).get("id")
        if not tid:
            C.die(f"{n}: no task id in state (run tasks first)")
        rc |= C.core_cli("idmc_mttask.py", ["run", tid] + C.gate_args(a))
    return rc


def main():
    ap = C.add_common_args(argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter))
    ap.add_argument("cmd", choices=["build", "import", "tasks", "run", "list"])
    ap.add_argument("names", nargs="*", help="run: mapping or task names")
    ap.add_argument("--only", action="append", help="limit to this mapping name (repeatable)")
    ap.add_argument("--offline", action="store_true", help="build with placeholder ids (no state, no .env needed)")
    ap.add_argument("--mode", choices=["REUSE", "OVERWRITE"], default="REUSE")
    a = ap.parse_args()
    cfg, st = C.load_config(a.config), C.load_state()
    if a.cmd == "list":
        for sp in rdf_specs.all_specs():
            kinds = {}
            for nd in sp["nodes"]:
                kinds[nd["type"]] = kinds.get(nd["type"], 0) + 1
            print(f"{sp['name']:26} task {sp['taskName']:28} " + " ".join(f"{k}={v}" for k, v in sorted(kinds.items())))
        return 0
    return {"build": cmd_build, "import": cmd_import, "tasks": cmd_tasks, "run": cmd_run}[a.cmd](a, cfg, st)


if __name__ == "__main__":
    sys.exit(main())
