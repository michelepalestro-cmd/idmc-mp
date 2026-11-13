#!/usr/bin/env python3
"""deploy_cai.py - put the generated CAI package into an org, set the JMS secret, publish in dependency order.

  python idmc/deploy_cai.py ensure-project            find or create the project + folders; FRS records -> state/frs.json
  python idmc/deploy_cai.py import [--only listeners] import build/cai/mbr_cai.zip (OVERWRITE, includeObjects = its GUIDs)
  python idmc/deploy_cai.py set-secret                set the AMQP (JMS) user + password with asset/v1/update (L-CAI-132)
  python idmc/deploy_cai.py publish [--only listeners | --names a,b]   one asset path per call, in the manifest order
  python idmc/deploy_cai.py unpublish [--names a,b]   reverse order (all assets by default)
  python idmc/deploy_cai.py status                    publication status of every asset (v3 customAttributes)

Every write is a dry run until --execute --expect-org <orgIdV3> (core WriteGate). Uses the Script Library: idmc_session (one
guarded login), idmc_http (gate, multipart, poll), idmc_export_import (import + report), idmc_cai_publish (publish job
check). Credentials only from the environment / toolkit .env; values are never printed.

PROVEN in an earlier form: v3 import of hand-built packages (OVERWRITE + includeObjects), one-path-per-call publish with
itemDetail checks, the encrypted secret via asset/v1/update, the FRS reads. ADAPTED: the project/folder ensure step,
combined here into one script.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
import mbr_config as CFG  # noqa: E402

CFG.use_core()
import idmc_cai_publish as PUB  # noqa: E402
import idmc_export_import as IMP  # noqa: E402
import idmc_http as H  # noqa: E402
from idmc_session import Session  # noqa: E402

MAN = CFG.BUILD / "cai" / "mbr_cai.json"
ZIP = CFG.BUILD / "cai" / "mbr_cai.zip"


def manifest():
    if not MAN.exists():
        sys.exit(f"{MAN} missing: run python idmc/gen_cai.py first")
    return json.loads(MAN.read_text(encoding="utf-8"))


def flatten_frs(d):
    """FRS answers come as OData 'properties' lists or as plain objects; return a flat record."""
    if isinstance(d, dict) and isinstance(d.get("properties"), list):
        rec = {}
        for p in d["properties"]:
            v = p.get("value")
            if p.get("name") == "parentInfo" and isinstance(v, list):
                v = [{f["name"]: f.get("value") for f in (e.get("value") or [])} for e in v]
            rec[p.get("name")] = v
        return rec
    return dict(d or {})


def v3_objects(S, q):
    r = S.get("v3", "/public/core/v3/objects?limit=200&q=" + urllib.parse.quote(q, safe="=()'"))
    return (r.json({}) or {}).get("objects", []) if r.ok else []


def cmd_ensure_project(S, gate, cfg):
    p = cfg["project"]
    ids = CFG.state_get("ids.json", {})
    found = [o for o in v3_objects(S, "type=='PROJECT'") if o.get("path", "").strip("/") in (p["name"], "Explore/" + p["name"])
             or o.get("name") == p["name"]]
    if found:
        pid = found[0]["id"]
        print(f"project '{p['name']}' exists: {pid}")
    else:
        r = gate.send("create project", "v3", "POST", "/public/core/v3/projects", body={"name": p["name"], "description": p["description"]})
        if r is None:
            print("DRY-RUN: the folders would be created next; nothing written to state/")
            return
        pid = (r.json({}) or {}).get("id") or H.die(f"project create failed HTTP {r.status} {r.head(300)}")
    ids["project_id"] = pid
    have = {o.get("name"): o["id"] for o in v3_objects(S, f"type=='FOLDER' and location=='{p['name']}'")}
    folders = {}
    for name in p["folders"].values():
        if name in have:
            folders[name] = have[name]
            continue
        r = gate.send(f"create folder {name}", "v3", "POST", f"/public/core/v3/projects/{pid}/folders",
                      body={"name": name, "description": f"{p['name']}: {name}"})
        if r is None:
            continue
        folders[name] = (r.json({}) or {}).get("id") or H.die(f"folder create failed HTTP {r.status} {r.head(300)}")
    ids["folders"] = folders
    frs = {"project": None, "folders": {}}
    rp = S.get("frs", f"/frs/v1/Projects('{pid}')")
    frs["project"] = flatten_frs(rp.json({})) if rp.ok else H.die(f"FRS project read HTTP {rp.status} {rp.head(200)}")
    for name, fid in folders.items():
        rf = S.get("frs", f"/frs/v1/Folders('{fid}')")
        frs["folders"][name] = flatten_frs(rf.json({})) if rf.ok else H.die(f"FRS folder read HTTP {rf.status} {rf.head(200)}")
    CFG.state_put("ids.json", ids)
    CFG.state_put("frs.json", frs)
    print(f"state/ids.json + state/frs.json written: project + {len(folders)} folders")


def cmd_import(S, gate, a):
    man = manifest()
    guids = man["guids"]
    if a.only == "listeners":   # step 7: the re-import of the three listener connections with consumers enabled
        paths = set(man["listener_connections"])
        guids = [g for g, p in zip(man["guids"], man["paths"]) if p in paths]
    ns = argparse.Namespace(package=str(ZIP), mode="OVERWRITE", include=guids, name=f"mbr_cai_{int(time.time())}")
    IMP.cmd_import(S, ns, gate)


def cmd_set_secret(S, gate, cfg):
    man = manifest()
    jms_path = man["by_name"]["mbr-jms.AI_CONNECTION.xml"]
    gid = man["guids"][man["paths"].index(jms_path)]
    # the v3 object id of the connection is needed (its GUID in the package is the same object after import)
    objs = [o for o in v3_objects(S, "type=='AI_CONNECTION'") if o.get("path", "").endswith("/mbr-jms") or o.get("name") == "mbr-jms"]
    oid = objs[0]["id"] if objs else gid
    user, pw = CFG.env_value("MBR_ARTEMIS_USER"), CFG.env_value("MBR_ARTEMIS_PASSWORD")
    if not user or not pw:
        H.die("MBR_ARTEMIS_USER / MBR_ARTEMIS_PASSWORD not found in the environment or the toolkit .env")
    body = {"connections": [{"guid": {"$t": oid}, "attributes": [{"key": {"$t": "User Name"}, "value": {"$t": user}},
                                                                {"key": {"$t": "Password"}, "value": {"$t": pw}}]}]}
    print(f"set-secret: connection mbr-jms ({oid}); attributes 'User Name', 'Password' (values from the .env, not shown)")
    if not gate.execute:
        print("[DRY-RUN] PUT cai:/active-bpel/asset/v1/update?assetType=AppConnection  body: {connections:[{guid, attributes:[***]}]}")
        return
    gate.guard()
    r = S.call("cai", "PUT", "/active-bpel/asset/v1/update?assetType=AppConnection", body=body,
               headers={"Content-Type": "application/json", "Accept": "application/json"}, timeout=120)
    st = ((r.json({}) or {}).get("status") or {}).get("$t") if r.ok else None
    print(f"    -> HTTP {r.status} status {st}")      # the answer is not printed: it could echo attributes
    if st != "SUCCESS":
        H.die("asset/v1/update did not answer SUCCESS; nothing else changed")
    print("    republish mbr-jms and then its processes (deploy_cai.py publish --names mbr-jms,mbr_jms_bridge_items,mbr_jms_bridge_pos)")


def select_paths(man, a, verb):
    if getattr(a, "only", None) == "listeners":
        paths = man["listener_connections"]
    elif getattr(a, "names", None):
        want = [n.strip() for n in a.names.split(",") if n.strip()]
        paths = [p for n in want for s, p in man["by_name"].items() if s.split(".")[0] == n]
        if len(paths) != len(want):
            H.die(f"unknown asset name in --names: {want}")
    else:
        paths = man["publish"]
    return list(reversed(paths)) if verb == "unpublish" else paths


def cmd_publish(S, gate, a, verb):
    man = manifest()
    for p in select_paths(man, a, verb):
        typ = PUB.asset_type(p)
        ok = PUB.run_wave(S, gate, verb, [(p, typ, p.rsplit("/", 1)[-1])])
        if not ok and verb == "publish":
            H.die(f"stop: {verb} not successful for {p} (later assets depend on it)")
    if verb == "publish" and gate.execute:
        print("Read the agent's catalina log after a connection publish: a Kafka route can fail to start while the publish "
              "says SUCCESS (L-CAI-125).")


def cmd_status(S, cfg):
    p = cfg["project"]["name"]
    for typ in ("AI_SERVICE_CONNECTOR", "AI_CONNECTION", "PROCESS"):
        for o in v3_objects(S, f"type=='{typ}' and location=='{p}'"):
            ca = o.get("customAttributes") or {}
            print(f"  {typ:22} {o.get('path')}: {ca.get('publicationStatus')}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__.split("\n\n", 1)[1])
    ap.add_argument("--config")
    sub = ap.add_subparsers(dest="cmd", required=True)
    H.add_gate_args(sub.add_parser("ensure-project"))
    im = H.add_gate_args(sub.add_parser("import"))
    im.add_argument("--only", choices=["listeners"])
    H.add_gate_args(sub.add_parser("set-secret"))
    for v in ("publish", "unpublish"):
        p = H.add_gate_args(sub.add_parser(v))
        p.add_argument("--only", choices=["listeners"])
        p.add_argument("--names", help="comma-separated asset names, e.g. mbr-jms,mbr_jms_bridge_items")
    sub.add_parser("status")
    a = ap.parse_args()
    cfg = CFG.load(a.config)
    H.safe_console()
    S = Session()
    gate = H.WriteGate(a, S) if a.cmd != "status" else None
    if a.cmd == "ensure-project":
        cmd_ensure_project(S, gate, cfg)
    elif a.cmd == "import":
        cmd_import(S, gate, a)
    elif a.cmd == "set-secret":
        cmd_set_secret(S, gate, cfg)
    elif a.cmd in ("publish", "unpublish"):
        cmd_publish(S, gate, a, a.cmd)
    else:
        cmd_status(S, cfg)


if __name__ == "__main__":
    main()
