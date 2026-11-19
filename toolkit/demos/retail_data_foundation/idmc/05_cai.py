#!/usr/bin/env python3
"""Step 5: CAI real-time sync to the CRM (service connector + app connection + processes), headless.

  python idmc/05_cai.py build --offline                       # build the package with stand-in folder files, inspect only
  python idmc/05_cai.py harvest --execute --expect-org <id>   # export one task of the folder -> folder/project JSON
  python idmc/05_cai.py build                                 # the real package (holds NO secret; file is 0600)
  python idmc/05_cai.py import  --execute --expect-org <orgIdV3>
  python idmc/05_cai.py set-secret --execute --expect-org <orgIdV3>  # Connected App id/secret, stored encrypted
  python idmc/05_cai.py publish --execute --expect-org <orgIdV3>   # waves: connector -> connection -> processes
  python idmc/05_cai.py url                                   # print CAI_RT_BASE for the .env and the process URLs
  python idmc/05_cai.py purge                                 # delete the built package

Access (config.json "cai"): the processes are REST endpoints restricted to cai.allowedUsers / cai.allowedGroups
(IDMC users / groups), called with Basic Authentication on https://<pod>-cai.<domain>/active-bpel/rt/<process>.
cai.anonymous = true publishes them with NO authentication (anyone with the URL can write to the CRM): test orgs only.
The Connected App client id / secret are packaged encrypted with empty values and set by 'set-secret' (L-CAI-132).

Package layout (PROVEN 2026-09: 9/9 assets imported + published in a migration, Contact upsert 0.2-2 s end to end):
  Explore/<project>/<folder>/<name>.<TYPE>.xml   one per asset, each wrapped in the repository getResponse/Item
  Explore/<project>/<folder>.Folder.json + Explore/<project>.Project.json   copied from a real export of that folder
  exportMetadata.v2.json   exportedObjects[] with objectGuid / objectType / path / objectRefs (connection -> connector,
                           processes -> connection); sourceOrgId copied from the harvested export
  exportPackage.chksum     path=SHA256 (upper-case hex) per file
Publish: POST /active-bpel/asset/v1/publish {"data":{"type":"publish","attributes":{"assetPaths":[...]}}} on the
<pod>-cai host with vnd.api+json headers; a 202 is only submission: read every itemDetail[].itemState. The runtime can
serve the previous version for about 20 s after a publish.
"""
import argparse
import datetime
import hashlib
import io
import json
import os
import random
import string
import sys
import uuid
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "lib"))
sys.path.insert(0, str(HERE / "cai"))
import rdf_common as C  # noqa: E402
import cai_assets as A  # noqa: E402

PKG = C.STATE_DIR / "packages" / "rdf_cai.pkg.zip"
HARVEST = C.STATE_DIR / "harvest"


def g22():
    return "".join(random.SystemRandom().choice(string.ascii_letters + string.digits) for _ in range(22))


def guids(st, names):
    cai = st.setdefault("cai", {})
    gd = cai.setdefault("guids", {})
    for n in names:
        gd.setdefault(n, g22())
    cai.setdefault("sc_uuid", str(uuid.uuid4()))
    return gd, cai["sc_uuid"]


def folder_files(cfg, offline):
    proj, fold = cfg["idmc"]["project"], cfg["idmc"]["folder"]
    pj, fj, meta = HARVEST / "Project.json", HARVEST / "Folder.json", HARVEST / "exportMetadata.v2.json"
    if pj.exists() and fj.exists() and meta.exists():
        m = json.loads(meta.read_text(encoding="utf-8"))
        objs = [o for o in m.get("exportedObjects", []) if o.get("objectType") in ("Project", "Folder")]
        return pj.read_bytes(), fj.read_bytes(), objs, m.get("sourceOrgId"), m.get("sourceOrgName")
    if not offline:
        C.die("no harvested folder files: run '05_cai.py harvest' first (or build --offline to inspect)")
    stub = json.dumps({"_stand_in": "offline build: replace by harvest"}).encode()
    objs = [{"objectGuid": "OFFLINEfolderGuid00001", "objectName": fold, "objectType": "Folder", "path": f"/Explore/{proj}"},
            {"objectGuid": "OFFLINEprojectGuid0001", "objectName": proj, "objectType": "Project", "path": "/Explore"}]
    return stub, stub, objs, "OFFLINE", "offline"


def _names(v):
    """Configured user / group names, without the '<...>' placeholders of config.example.json."""
    return [str(x).strip() for x in (v or []) if str(x).strip() and not str(x).strip().startswith("<")]


def access(cfg, offline=False):
    """(anonymous, users, groups) for the processes' REST deployment. Secure by default: anonymous only when
    cai.anonymous is literally true; otherwise at least one allowed user or group is required (offline builds only warn)."""
    c = cfg["cai"]
    anon = c.get("anonymous", False) is True
    users, groups = _names(c.get("allowedUsers")), _names(c.get("allowedGroups"))
    if anon:
        print("WARNING: cai.anonymous = true: the CRM-sync processes accept calls with NO authentication from anyone "
              "who has the URL. Use it only in a throwaway test org.", file=sys.stderr)
        return True, [], []
    if not users and not groups:
        msg = ("cai.allowedUsers / cai.allowedGroups name no IDMC user or group: the processes would answer 403 to "
               "every caller. Put the IDMC user that calls them (RDF_CAI_USER) in cai.allowedUsers")
        if not offline:
            C.die(msg)
        print("note (offline): " + msg, file=sys.stderr)
    return False, users, groups


def v3_objects(S, q):
    import urllib.parse
    r = S.get("v3", "/public/core/v3/objects?limit=200&q=" + urllib.parse.quote(q, safe="=()'"))
    return (r.json({}) or {}).get("objects", []) if r.ok else []


def set_secret(a, cfg, st):
    """Store SF_CLIENT_ID / SF_CLIENT_SECRET encrypted in the imported app connection (L-CAI-132). Values never printed."""
    C.offline_session_guard(a)
    from idmc_session import Session
    import idmc_http as H
    conn = cfg["cai"]["appConnection"]
    cid, csec = C.env("SF_CLIENT_ID", required=True), C.env("SF_CLIENT_SECRET", required=True)
    S = Session()
    gate = H.WriteGate(a, S)
    objs = [o for o in v3_objects(S, "type=='AI_CONNECTION'")
            if o.get("name") == conn or str(o.get("path", "")).endswith("/" + conn)]
    oid = objs[0]["id"] if objs else ((st.get("cai") or {}).get("guids") or {}).get(conn)
    if not oid:
        C.die(f"app connection {conn} not found: import the package first")
    print(f"set-secret: app connection {conn} ({oid}); attributes SF_CLIENT_ID, SF_CLIENT_SECRET (values from the .env, "
          "not shown)")
    if not gate.execute:
        print("[DRY-RUN] PUT cai:/active-bpel/asset/v1/update?assetType=AppConnection  body: {connections:[{guid, attributes:[***]}]}")
        return 0
    gate.guard()
    body = {"connections": [{"guid": {"$t": oid}, "attributes": [{"key": {"$t": "SF_CLIENT_ID"}, "value": {"$t": cid}},
                                                                {"key": {"$t": "SF_CLIENT_SECRET"}, "value": {"$t": csec}}]}]}
    r = S.call("cai", "PUT", "/active-bpel/asset/v1/update?assetType=AppConnection", body=body,
               headers={"Content-Type": "application/json", "Accept": "application/json"}, timeout=120)
    status = ((r.json({}) or {}).get("status") or {}).get("$t") if r.ok else None
    print(f"    -> HTTP {r.status} status {status}")     # the answer is not printed: it could echo attributes
    if status != "SUCCESS":
        C.die("asset/v1/update did not answer SUCCESS; nothing else changed")
    print("    (re)publish the connection, then the processes: 05_cai.py publish --execute --expect-org <orgIdV3>")
    return 0


def build_package(cfg, st, offline):
    c, tag = cfg["cai"], cfg["idmc"]["tag"]
    sc, conn = c["serviceConnector"], c["appConnection"]
    p_contact, p_member = c["processes"]
    gd, sc_uuid = guids(st, [sc, conn, p_contact, p_member])
    login = C.env("SF_LOGIN_URL") or "https://<my-domain>.my.salesforce.com"
    token_url = login.rstrip("/") + "/services/oauth2/token"
    anon, users, groups = access(cfg, offline)
    api = cfg["crm"]["apiVersion"]
    fields = ["FirstName", "LastName", "Email", "Phone", "Rdf_Tier__c", "Rdf_Signup_Channel__c"]
    assets = [
        (sc, "AI_SERVICE_CONNECTOR", "application/xml+businesssconnector",
         A.service_connector(sc, sc_uuid, token_url, api, cfg["crm"]["contactExternalId"], tag, fields), []),
        (conn, "AI_CONNECTION", "application/xml+connection",
         A.app_connection(conn, sc, gd[sc], sc_uuid, tag, token_url, api), [gd[sc]]),
        (p_contact, "PROCESS", "application/xml+process",
         A.contact_process(p_contact, gd[p_contact], conn, gd[conn], tag, anon, users, groups), [gd[conn]]),
        (p_member, "PROCESS", "application/xml+process",
         A.event_process(p_member, A.membership_event(cfg), gd[p_member], conn, gd[conn], tag, anon, users, groups),
         [gd[conn]]),
    ]
    proj, fold = cfg["idmc"]["project"], cfg["idmc"]["folder"]
    pj, fj, fobjs, src_org, src_name = folder_files(cfg, offline)
    import xml.dom.minidom
    files, objs = {}, list(fobjs)
    for name, typ, mime, entry, refs in assets:
        x = A.item(name, mime, f"[{tag}] real-time CRM sync", gd[name], entry).encode()
        xml.dom.minidom.parseString(x)               # every asset must be well-formed XML before it is packaged
        files[f"Explore/{proj}/{fold}/{name}.{typ}.xml"] = x
        objs.append({"objectGuid": gd[name], "objectName": name, "objectType": typ, "path": f"/Explore/{proj}/{fold}",
                     "providerName": None, "metadata": {"modelVersion": {"major": 1, "minor": 0}, "repoInfo": None,
                                                        "objectRefs": refs, "contextAttributes": None,
                                                        "additionalInfo": {"description": f"[{tag}] real-time CRM sync",
                                                                           "contentType": "application/json; charset=utf-8",
                                                                           "documentState": "VALID"}}})
    files[f"Explore/{proj}/{fold}.Folder.json"] = fj
    files[f"Explore/{proj}.Project.json"] = pj
    files["exportMetadata.v2.json"] = json.dumps({"name": "rdf_cai", "sourceOrgId": src_org, "sourceOrgName": src_name,
                                                  "exportedObjects": objs}, indent=2).encode()
    chk = "#\n#" + datetime.datetime.now(datetime.timezone.utc).strftime("%a %b %d %H:%M:%S UTC %Y") + "\n" + "".join(
        f"{p.replace(' ', chr(92) + ' ')}={hashlib.sha256(b).hexdigest().upper()}\n" for p, b in files.items())
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p, b in files.items():
            z.writestr(p, b)
        z.writestr("exportPackage.chksum", chk)
        z.writestr("ContentsofExportPackage_rdf_cai.csv", "objectPath,objectName,objectType,id\n" + "\n".join(
            f"/Explore/{proj}/{fold},{n},{t},{gd[n]}" for n, t, *_ in assets))
    PKG.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(PKG, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(buf.getvalue())
    return assets, gd


def asset_paths(cfg):
    c, proj, fold = cfg["cai"], cfg["idmc"]["project"], cfg["idmc"]["folder"]
    out = [f"Explore/{proj}/{fold}/{c['serviceConnector']}.AI_SERVICE_CONNECTOR.xml",
           f"Explore/{proj}/{fold}/{c['appConnection']}.AI_CONNECTION.xml"]
    return out + [f"Explore/{proj}/{fold}/{p}.PROCESS.xml" for p in c["processes"]]


def main():
    ap = C.add_common_args(argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter))
    ap.add_argument("cmd", choices=["build", "harvest", "import", "set-secret", "publish", "unpublish", "url", "purge"])
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--no-secrets", action="store_true", help=argparse.SUPPRESS)   # kept for old scripts: now always so
    ap.add_argument("--from-task", help="harvest: v3 id of any object already in the project folder")
    a = ap.parse_args()
    cfg, st = C.load_config(a.config), C.load_state()
    if a.cmd == "build":
        assets, gd = build_package(cfg, st, a.offline)
        for n, t, *_ in assets:
            print(f"  {t:22} {n:30} guid {gd[n]}")
        print(f"package -> {PKG.relative_to(C.BLUEPRINT)} (0600; no secret inside: after the import run 'set-secret')")
        if not a.offline:
            C.save_state(st)
        return 0
    if a.cmd == "harvest":
        src = a.from_task or next(iter((st.get("tasks") or {}).values()), {}).get("frsGuid")
        if not src:
            C.die("harvest needs --from-task <v3 id of an object in the folder> (or run 03_mappings.py tasks first)")
        out = C.STATE_DIR / "harvest" / "export.zip"
        out.parent.mkdir(parents=True, exist_ok=True)
        rc = C.core_cli("idmc_export_import.py", ["export", "--id", src, "--no-deps", "--out", str(out)])
        if rc == 0 and out.exists():
            proj, fold = cfg["idmc"]["project"], cfg["idmc"]["folder"]
            with zipfile.ZipFile(out) as z:
                names = z.namelist()
                pj = next(n for n in names if n.endswith(f"{proj}.Project.json"))
                fj = next(n for n in names if n.endswith(f"{fold}.Folder.json"))
                (HARVEST / "Project.json").write_bytes(z.read(pj))
                (HARVEST / "Folder.json").write_bytes(z.read(fj))
                (HARVEST / "exportMetadata.v2.json").write_bytes(z.read("exportMetadata.v2.json"))
            print("harvested Project.json, Folder.json, exportMetadata.v2.json ->", HARVEST.relative_to(C.BLUEPRINT))
        return rc
    if a.cmd == "import":
        if not PKG.exists():
            C.die("build the package first")
        if b"OFFLINE" in PKG.read_bytes():
            C.die("this package was built --offline: rebuild it after 'harvest'")
        gd = (st.get("cai") or {}).get("guids") or {}
        args = ["import", str(PKG), "--mode", "OVERWRITE", "--name", "rdf_cai"]
        for g in gd.values():
            args += ["--include", g]
        return C.core_cli("idmc_export_import.py", args + C.gate_args(a))
    if a.cmd == "set-secret":
        return set_secret(a, cfg, st)
    if a.cmd in ("publish", "unpublish"):
        args = [a.cmd]
        for p in asset_paths(cfg):
            args += ["--path", p]
        return C.core_cli("idmc_cai_publish.py", args + C.gate_args(a))
    if a.cmd == "url":
        from idmc_session import Session
        S = Session()
        h = S.hosts()
        base = (h.get("cai") or "").rstrip("/")
        org = S.v2().get("orgUuid")
        anon, users, groups = access(cfg, offline=True)
        rt = f"{base}/active-bpel/public/rt/{org}" if anon else f"{base}/active-bpel/rt"
        print("CAI_RT_BASE (put it in the toolkit .env; it is not a secret, but it is org-specific):")
        print("  " + rt)
        how = ("NO authentication (test opt-in)" if anon else
               "Basic Authentication as RDF_CAI_USER / RDF_CAI_PASS; allowed: " + ", ".join(users + [f"group {g}" for g in groups]))
        for p in cfg["cai"]["processes"]:
            print(f"  POST {rt}/{p}   (JSON body; {how})")
        return 0
    if a.cmd == "purge":
        if PKG.exists():
            PKG.unlink()
            print("deleted", PKG.relative_to(C.BLUEPRINT))
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
