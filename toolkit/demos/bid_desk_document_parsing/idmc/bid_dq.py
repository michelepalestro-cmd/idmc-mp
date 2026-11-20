#!/usr/bin/env python3
"""bid_dq.py - Cloud Data Quality for the Bid Desk: the 7 rule specifications (folder 3) and the 3 Data Profiling profiles
that score them on what CLAIRE read (Bronze) and on Silver; the scorecard lands in Snowflake BID_DQ_SCORECARD.

    python bid_dq.py rulespecs                       # the rule specs in folder 3: id, dimension (read-only)
    python bid_dq.py profiles                        # the profiles: id, table, rule -> column, last run (read-only)
    python bid_dq.py build [--execute --expect-org <orgIdV3>]   # create what is missing: rule specs, profiles, bindings
    python bid_dq.py run [all|<profile name>] [--execute ...]   # run profiles one at a time (~2-4 min each; uses the warehouse)
    python bid_dq.py results [all]                   # per rule occurrence, latest COMPLETED run: checked / passed / score
    python bid_dq.py land [--execute]                # results -> BID_DQ_SCORECARD (Snowflake SQL API)

Rule specs (PROVEN 2026-10-13): there is no create verb. `build` exports ONE existing single-string-input rule spec of your org
(config idmc.template_rule_spec) as a v3 package (POST /public/core/v3/export, poll, GET .../export/<id>/package), clones its
RULE_SPECIFICATION document per rule (fresh 22-char GUID, name, description, DIMENSION attribute, input field, the IF/THEN/ELSE
script, test data, fresh 'U:' internal ids), points the Project/Folder documents at this project's folder 3, recomputes
exportPackage.chksum (path=SHA256 upper case; spaces escaped '\\ ') and imports ONE package per rule (an import is
all-or-nothing): POST /public/core/v3/import/package (multipart part 'package'; checksumValid must be true), then
POST /public/core/v3/import/<jobId> {"importSpecification":{"defaultConflictResolution":"REUSE"}}, poll, read the objects.
Then the imported script is read back (FRS Documents('<id>')?$expand=nativeData) and compared.
Profiles (PROVEN 2026-10-13): on the <pod>-dqprofile host, header IDS-SESSION-ID (the v3 session; the v2 id got 401 on
one pod): POST /profiling-service/api/v1/profile (no client-side ids anywhere, else 500) built from the Snowflake
connection's own field metadata (GET v2 /api/v2/connection/source/<connId>/fields?objectName=<db>/<schema>/<table> + PUT
/profiling-service/api/v1/Configuration/columns/profilingFacts), then PUT /profile/<id> with one rule block per rule spec and
one MAPPLETFIELD per (rule, column). Run: GET /job/runningJobs/<id> (refuse if busy) -> POST /profile/<id>/execute -> poll
/job/<jobId>. Results: metric store /metric-store/api/v1/odata/Profiles('<id>')/Columns?$filter=runKey eq <n> and, when a
rule output has two values, the run-keyed Patterns of that column, accepted only when every row carries this column's key,
run and profile (an unknown column id still answers 200 with every column's patterns). ValueFrequencies is NOT run-keyed.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import io
import json
import re
import secrets
import string
import sys
import time
import urllib.parse
import uuid
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
import bid_common as C  # noqa: E402

PB, MS = "/profiling-service/api/v1", "/metric-store/api/v1/odata"
PASS = ("VALID", "TRUE", "1", "YES", "OK")
TERMINAL = ("COMPLETED", "FAILED", "STOPPED", "CANCELLED", "CANCELED", "ABORTED", "ERROR", "COMPLETED_WITH_ERRORS", "PARTIAL_COMPLETED")
q = lambda s: urllib.parse.quote(s, safe="=$&'(),")  # noqa: E731


def tpl():
    return C.template("dq.json")


def rname(cfg, r):
    return "%s - %s" % (cfg["idmc"]["project"], r)


def pname(cfg, p):
    return "%s - %s" % (cfg["idmc"]["project"].replace(".", "_"), p)


def prof(ctx, method, path, body=None):
    if method == "GET":
        return ctx.read("profiling", PB + path)
    return ctx.write("profiling %s" % path.split("?")[0], "profiling", method, PB + path, body=body)


# ------------------------------------------------------------------ rule specs (clone a template through a package)
def new_guid():
    return "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(22))


def new_internal_id():
    return "U:" + base64.urlsafe_b64encode(uuid.uuid4().bytes).decode().rstrip("=")


def chk_key(n):
    return n.replace("\\", "\\\\").replace(" ", "\\ ").replace(":", "\\:").replace("=", "\\=")


def export_template(ctx, frs_id):
    r = ctx.write("export the template rule spec", "v3", "POST", "/public/core/v3/export",
                  body={"name": "bid_dq_tpl_%d" % time.time(), "objects": [{"id": frs_id, "includeDependencies": False}]})
    jid = (r.json({}) or {}).get("id") if C.ok(r) else None
    if not jid:
        return None
    for _ in range(100):
        time.sleep(3)
        j = ctx.read("v3", "/public/core/v3/export/%s" % jid).json({})
        if (j.get("status") or {}).get("state") not in ("IN_PROGRESS", "QUEUED", "NOT_STARTED", None):
            break
    if (j.get("status") or {}).get("state") != "SUCCESSFUL":
        C.H.die("template export ended %s" % (j.get("status") or {}).get("state"))
    z = ctx.S.call("v3", "GET", "/public/core/v3/export/%s/package" % jid, headers={"Accept": "application/zip"}).raw
    with zipfile.ZipFile(io.BytesIO(z)) as zf:
        return {n: zf.read(n) for n in zf.namelist()}


def set_odata(od, values, parents):
    for p in od.get("properties") or []:
        if p.get("name") in values:
            p["value"] = values[p["name"]]
        if p.get("name") == "parentInfo":
            for item, (pid, pnm, ptype) in zip(p.get("value") or [], parents):
                for v in item.get("value") or []:
                    v["value"] = {"parentId": pid, "parentName": pnm, "parentType": ptype}.get(v.get("name"), v.get("value"))
    return od


def clone_doc(t, spec, full_name):
    d = copy.deepcopy(t)
    guid = new_guid()
    d["id"], d["name"], d["description"] = guid, full_name, spec["description"]
    d.setdefault("repoInfo", {})["repoHandle"] = guid
    attrs = d.setdefault("customAttributes", {}).setdefault("stringAttrs", [])
    dim = [x for x in attrs if x.get("name") == "DIMENSION"]
    if dim:
        dim[0]["value"] = spec["dimension"]
    else:
        attrs.append({"name": "DIMENSION", "value": spec["dimension"]})
    d["nativeData"]["id"] = guid
    blob = json.loads(d["nativeData"]["documentBlob"])
    model = json.loads(blob["ruleModel"])
    iname, itype, iprec, iscale = spec["input"]
    blob["inputFields"] = [{"name": iname, "type": itype, "precision": iprec, "scale": iscale}]
    model["name"], model["description"] = full_name, spec["description"]
    model["alternateDefinition"]["script"] = spec["script"]
    if len(model["fields"]) != 1 or len(model.get("testData") or []) != 1:
        C.H.die("the template rule spec must have exactly ONE input (pick another in config idmc.template_rule_spec)")
    f = model["fields"][0]
    f["name"], f["precision"], f["scale"] = iname, str(iprec), str(iscale)
    f["$type"]["##SID"] = "smd:com.informatica.metadata.seed.platform.Platform.typesystem/" + itype
    model["testData"][0]["testData"] = list(spec["test"])
    txt = json.dumps(model, separators=(",", ":"), ensure_ascii=False)
    for old in sorted(set(re.findall(r"U:[A-Za-z0-9_-]{22}", txt))):
        txt = txt.replace(old, new_internal_id())
    blob["ruleModel"] = txt
    d["nativeData"]["documentBlob"] = json.dumps(blob, separators=(",", ":"), ensure_ascii=False)
    return d, guid


def build_package(files, spec, full_name, proj, folder_id, folder_name, space):
    rs = [n for n in files if n.endswith(".RULE_SPECIFICATION.json")]
    pj = [n for n in files if n.endswith(".Project.json")]
    fj = [n for n in files if n.endswith(".Folder.json")]
    if not (len(rs) == len(pj) == len(fj) == 1):
        C.H.die("unexpected template package layout")
    tdoc, pdoc, fdoc = (json.loads(files[x[0]]) for x in (rs, pj, fj))
    meta0 = json.loads(files["exportMetadata.v2.json"])
    pid, pnm = proj
    pdoc["id"] = "Projects(%s)" % pid
    set_odata(pdoc, {"id": pid, "name": pnm}, [(space[0], space[1], "Space")])
    fdoc["id"] = "Folders(%s)" % folder_id
    set_odata(fdoc, {"id": folder_id, "name": folder_name}, [(space[0], space[1], "Space"), (pid, pnm, "Project")])
    entry = lambda t: copy.deepcopy(next(o for o in meta0["exportedObjects"] if o["objectType"] == t))  # noqa: E731
    out, objs = {}, []
    out["Explore/%s.Project.json" % pnm] = json.dumps(pdoc, separators=(",", ":")).encode()
    out["Explore/%s/%s.Folder.json" % (pnm, folder_name)] = json.dumps(fdoc, separators=(",", ":")).encode()
    e = entry("Project")
    e.update(objectGuid=pid, objectName=pnm, path="/Explore")
    objs.append(e)
    d, guid = clone_doc(tdoc, spec, full_name)
    out["Explore/%s/%s/%s.RULE_SPECIFICATION.json" % (pnm, folder_name, full_name)] = json.dumps(d, indent=1).encode()
    e = entry("RULE_SPECIFICATION")
    e.update(objectGuid=guid, objectName=full_name, path="/Explore/%s/%s" % (pnm, folder_name))
    e["metadata"]["repoInfo"] = {"repoHandle": guid}
    e["metadata"]["additionalInfo"]["description"] = spec["description"]
    objs.append(e)
    e = entry("Folder")
    e.update(objectGuid=folder_id, objectName=folder_name, path="/Explore/" + pnm)
    objs.append(e)
    name = "bid_dq_%s" % time.strftime("%Y%m%dT%H%M%S", time.gmtime())
    meta = {k: v for k, v in meta0.items() if k != "exportedObjects"}
    meta.update(name=name, exportedObjects=objs)
    out["exportMetadata.v2.json"] = json.dumps(meta, indent=2).encode()
    lines = ["#", "#" + time.strftime("%a %b %d %H:%M:%S UTC %Y", time.gmtime())]
    lines += ["%s=%s" % (chk_key(n), hashlib.sha256(b).hexdigest().upper()) for n, b in out.items()]
    out["exportPackage.chksum"] = ("\n".join(lines) + "\n").encode()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for n, b in out.items():
            z.writestr(n, b)
    return name, buf.getvalue()


def import_package(ctx, name, zb):
    b = uuid.uuid4().hex
    raw = ("--%s\r\nContent-Disposition: form-data; name=\"package\"; filename=\"%s.zip\"\r\nContent-Type: application/zip\r\n\r\n"
           % (b, name)).encode() + zb + ("\r\n--%s--\r\n" % b).encode()
    r = ctx.write("upload package " + name, "v3", "POST", "/public/core/v3/import/package", raw=raw,
                  ctype="multipart/form-data; boundary=" + b)
    if r is None:
        return None
    up = r.json({}) or {}
    if not up.get("jobId") or up.get("checksumValid") is not True:
        C.H.die("upload: HTTP %s checksumValid=%s: the import was NOT started" % (r.status, up.get("checksumValid")))
    jid = up["jobId"]
    ctx.write("start import", "v3", "POST", "/public/core/v3/import/%s" % jid,
              body={"name": name, "importSpecification": {"defaultConflictResolution": "REUSE"}})
    for _ in range(200):
        time.sleep(3)
        j = ctx.read("v3", "/public/core/v3/import/%s" % jid).json({})
        if (j.get("status") or {}).get("state") not in ("IN_PROGRESS", "QUEUED", "NOT_STARTED", None):
            break
    jx = ctx.read("v3", "/public/core/v3/import/%s?expand=objects" % jid).json({})
    for o in jx.get("objects") or []:
        print("    %s %s: %s" % ((o.get("sourceObject") or {}).get("type"), (o.get("sourceObject") or {}).get("name"),
                                 (o.get("status") or {}).get("message")))
    return (j.get("status") or {}).get("state")


def build_rulespecs(ctx, st):
    cfg = ctx.cfg
    proj, fname = cfg["idmc"]["project"], cfg["idmc"]["folders"]["f3"]
    have = {o["path"].rsplit("/", 1)[-1]: o["id"] for o in C.v3_objects(ctx, "RULE_SPECIFICATION", "%s/%s/" % (proj, fname))}
    reg = st.setdefault("rulespecs", {})
    rules = tpl()["rules"]
    for r in rules:
        full = rname(cfg, r["name"])
        if full in have:
            reg[r["name"]] = have[full]
    missing = [r for r in rules if rname(cfg, r["name"]) not in have]
    print("rule specs: %d present, %d missing" % (len(rules) - len(missing), len(missing)))
    if not missing:
        return
    tpath = cfg["idmc"]["template_rule_spec"]
    t = next((o for o in C.v3_objects(ctx, "RULE_SPECIFICATION") if o.get("path") == tpath), None)
    if not t and not ctx.offline:
        C.H.die("template rule spec %r not found: name any rule spec with ONE string input (create one in the UI once if your "
                "org has none: Data Quality > New > Rule Specification)" % tpath)
    files = export_template(ctx, (t or {}).get("id", "<template frs id>")) if ctx.execute else None
    fid = (st.get("folders") or {}).get("f3", "<folder f3 id>")
    pid = st.get("project", "<project id>")
    space = ("<space id>", "<space name>")
    if ctx.execute:
        pr = ctx.S.get("frs", "/frs/v1/Projects('%s')" % pid).json({})
        sp = next(p for p in pr.get("parentInfo") or [] if p.get("parentType") == "Space")
        space = (sp["parentId"], sp["parentName"])
    for r in missing:
        full = rname(cfg, r["name"])
        if not files:
            print("[DRY-RUN] clone %r (%s, input %s) from %r and import it as one package" % (full, r["dimension"], r["input"][0], tpath))
            continue
        name, zb = build_package(files, r, full, (pid, proj), fid, fname, space)
        state = import_package(ctx, name, zb)
        print("  %s: import %s" % (full, state))
    if ctx.execute:
        have = {o["path"].rsplit("/", 1)[-1]: o["id"] for o in C.v3_objects(ctx, "RULE_SPECIFICATION", "%s/%s/" % (proj, fname))}
        for r in missing:
            i = have.get(rname(cfg, r["name"]))
            if not i:
                print("  MISSING after import:", r["name"])
                continue
            d = ctx.S.get("frs", "/frs/v1/Documents('%s')?%s" % (i, q("$expand=nativeData"))).json({})
            blob = json.loads(((d.get("nativeData") or {}).get("documentBlob")) or "{}")
            script = json.loads(blob.get("ruleModel") or "{}").get("alternateDefinition", {}).get("script")
            print("  %s %s script %s" % (r["name"], i, "matches" if script == r["script"] else "DIFFERS: check it"))
            if d.get("description") != r["description"]:
                ctx.write("set description", "frs", "PATCH", "/frs/v1/Documents('%s')" % i, body={"description": r["description"]})
            reg[r["name"]] = i


# ------------------------------------------------------------------ profiles
def list_profiles(ctx):
    r = prof(ctx, "GET", "/profile?limit=200")
    return {p["name"]: p for p in (r.json([]) if r is not None else []) if isinstance(p, dict)}


def table_fields(ctx, conn_v2, conn_frs, table):
    sf = ctx.cfg["snowflake"]
    r = ctx.read("v2", "/api/v2/connection/source/%s/fields?objectName=%s&validateFields=false"
                 % (conn_v2, urllib.parse.quote("%s/%s/%s" % (sf["database"], sf["schema"], table), safe="")))
    f = r.json([]) if r is not None else []
    if not f:
        C.H.die("no fields for %s (create the Snowflake objects first: infra/snowflake/*.sql)" % table)
    cols = [dict(x, dataType=x["type"], order=x.get("naturalOrder", i), isLeafNode=True, id=x["name"]) for i, x in enumerate(f)]
    rr = ctx.S.call("profiling", "PUT", PB + "/Configuration/columns/profilingFacts",
                    body={"columns": cols, "connectionId": conn_frs, "formatId": None, "dbType": "TOOLKIT_CCI",
                          "instanceType": "Snowflake Cloud Data Warehouse V2", "schemaType": None, "parserId": None})
    fx = {x["name"]: x for x in (rr.json([]) if rr.ok else [])}
    for x in f:
        x["precision"] = (fx.get(x["name"]) or {}).get("precision") or x["precision"]
        x["_ok"] = (fx.get(x["name"]) or {}).get("isSupported", True)
        x["_auto"] = (fx.get(x["name"]) or {}).get("isAutoSelected", True)
        x["_date"] = (fx.get(x["name"]) or {}).get("baseDataType") == "DATE" or x["type"] in ("date", "timestamp", "timestampntz")
    return f


def profile_body(ctx, spec, fields, conn_frs, folder_id, project_id):
    sf, must = ctx.cfg["snowflake"], {c for _, c in spec["bindings"]}
    keep = [x for x in fields if x["_ok"] and not x["_date"] and (x["_auto"] or x["name"] in must)]
    return {"name": pname(ctx.cfg, spec["name"]), "description": spec["description"], "frsProjectId": project_id,
            "frsFolderId": folder_id, "connectionId": conn_frs, "isFilterEnabled": False,
            "runtimeOptions": {"scheduleId": None, "runtimeEnvironmentId": None, "defaultEmailNotification": True,
                               "profileAdvProps": {"inferDateTime": True, "detectOutliers": True, "enableClaireAnomalyDetection": False,
                                                   "tracingLevel": "NORMAL"}},
            "source": {"name": spec["table"], "rules": [], "dataSourceType": "TOOLKIT_CCI",
                       "fields": [{"name": x["name"], "dataType": x["type"], "precision": x["precision"], "scale": x["scale"],
                                   "pcType": x["pcType"], "order": x.get("naturalOrder", i), "isDeleted": False,
                                   "isMetadataUpdated": False} for i, x in enumerate(fields)],
                       "properties": {"dataSourceType": "TOOLKIT_CCI", "sourcePath": "%s/%s" % (sf["database"], sf["schema"])},
                       "advancedOptions": {"Database": sf["database"], "Schema": sf["schema"], "Warehouse": sf["warehouse"], "Role": "",
                                           "Table Name": ""}, "sourceType": "DATASOURCE"},
            "profileableFields": [{"isDeleted": False, "appliedBy": "USER", "columnKey": 10001 + i, "sourceName": spec["table"],
                                   "fieldName": x["name"], "precision": x["precision"], "scale": x["scale"],
                                   "fieldType": "DATASOURCEFIELD"} for i, x in enumerate(keep)],
            "samplingOptions": {"rows": -1, "samplingType": "ALL_ROWS"}, "profileType": "COLUMN_PROFILE", "drillDownType": "ON"}


def bind(ctx, pid, bindings, st):
    rules = {r["name"]: r for r in tpl()["rules"]}
    cur = prof(ctx, "GET", "/profile/" + pid).json({})
    fields = {x["name"]: x for x in cur["source"]["fields"]}
    cur["source"]["rules"] = []
    cur["profileableFields"] = [x for x in cur["profileableFields"] if x.get("fieldType") == "DATASOURCEFIELD"]
    for n, (rule, col) in enumerate(bindings):
        frs = st["rulespecs"][rule]
        iname, itype, iprec, iscale = rules[rule]["input"]
        if not any(r["frsId"] == frs for r in cur["source"]["rules"]):
            cur["source"]["rules"].append({
                "name": rname(ctx.cfg, rule), "description": "%s on %s" % (rule, ", ".join(c for r2, c in bindings if r2 == rule)),
                "frsId": frs, "inFields": [{"name": iname, "label": None, "dataType": itype, "precision": iprec, "scale": iscale,
                                            "isDeleted": False}],
                "outFields": [{"name": "Output", "label": None, "dataType": "string", "precision": 50, "scale": 0, "isDeleted": False}],
                "isDeleted": False, "ruleType": "RULE_SPECIFICATION"})
        cur["profileableFields"].append({
            "isDeleted": False, "frsId": frs, "scoreCardId": None, "assignmentIdentifier": uuid.uuid4().hex,
            "inputFieldMappings": [{"dataSourceFieldName": col, "inFieldName": iname, "isDeleted": False,
                                    "dataSourceFieldPrecision": fields[col]["precision"], "dataSourceFieldScale": fields[col]["scale"]}],
            "outputFieldMappings": [{"columnKey": 40001 + n, "datatype": "string", "outFieldName": "Output", "label": None, "isDeleted": False}],
            "fieldType": "MAPPLETFIELD", "ruleType": "RULE_SPECIFICATION"})
    prof(ctx, "PUT", "/profile/" + pid, cur)


def build_profiles(ctx, st):
    have, reg = list_profiles(ctx), st.setdefault("profiles", {})
    for spec in tpl()["profiles"]:
        n = pname(ctx.cfg, spec["name"])
        if n in have:
            reg[spec["name"]] = have[n]["id"]
            print("profile %-46s present %s" % (n, have[n]["id"]))
            continue
        print("profile %-46s missing -> %s" % (n, "creating" if ctx.execute else "would create + bind %d rule occurrences"
                                                % len(spec["bindings"])))
        if not ctx.execute:
            prof(ctx, "POST", "/profile", {"name": n, "source": {"name": spec["table"]}, "...": "built from the table's fields"})
            continue
        conn_v2 = st["conn"]["warehouse"]
        conn_frs = ctx.S.get("v2", "/api/v2/connection/" + conn_v2).json({}).get("federatedId") or conn_v2
        f = table_fields(ctx, conn_v2, conn_frs, spec["table"])
        prof(ctx, "POST", "/profile", profile_body(ctx, spec, f, conn_frs, st["folders"]["f3"], st["project"]))
        time.sleep(2)
        pid = list_profiles(ctx)[n]["id"]
        bind(ctx, pid, spec["bindings"], st)
        reg[spec["name"]] = pid


# ------------------------------------------------------------------ run + results
def latest_run(ctx, pid, last_key, completed=True):
    k = last_key or 0
    while k >= 1:
        r = prof(ctx, "GET", "/runDetail/%s/%d" % (pid, k))
        rd = r.json({}) if r is not None else {}
        if r is not None and r.status == 200 and (not completed or rd.get("status") == "COMPLETED"):
            return rd
        k -= 1
    return None


def run_profile(ctx, name, pid, timeout=1800):
    rj = prof(ctx, "GET", "/job/runningJobs/" + pid)
    if rj is not None and rj.json([]):
        return {"profile": name, "status": "NOT_STARTED", "error": "already running"}
    r = prof(ctx, "POST", "/profile/%s/execute" % pid, {})
    if r is None:
        return {"profile": name, "status": "DRY-RUN"}
    jid, t0, job = (r.json({}) or {}).get("profileJobId") or (r.json({}) or {}).get("jobId"), time.time(), {}
    while time.time() - t0 < timeout:
        time.sleep(5)
        job = prof(ctx, "GET", "/job/%s" % jid).json({}) or {}
        if str(job.get("status", "")).upper() in TERMINAL:
            break
    return {"profile": name, "jobId": jid, "status": job.get("status"), "seconds": round(time.time() - t0)}


def pattern_label(v):
    sym, out, i = ["X" if ch.isalpha() else "9" if ch.isdigit() else ch for ch in v], [], 0
    while i < len(sym):
        j = i
        while j < len(sym) and sym[j] == sym[i]:
            j += 1
        out.append("%s(%d)" % (sym[i], j - i) if j - i >= 4 else sym[i] * (j - i))
        i = j
    return "".join(out)


def count_rule(ctx, pid, pk, c, rk):
    total, nul = int(c.get("totalRows") or 0), int(c.get("nulCount") or 0)
    vals = sorted({str(v) for v in (c.get("minimumValue"), c.get("maximumValue")) if v not in (None, "")})
    if total == 0:
        return 0, 0
    if c.get("distinctCount") == 1 and len(vals) == 1:
        return total, (total - nul) if vals[0].upper() in PASS else 0
    good = [v for v in vals if v.upper() in PASS]
    if c.get("distinctCount") != 2 or len(vals) != 2 or len(good) != 1:
        return total, None
    lg, lb = pattern_label(good[0]), pattern_label(next(v for v in vals if v != good[0]))
    r = ctx.read("profiling", MS + "/Profiles('%s')/Columns('%s')/Patterns?%s" % (pid, c["columnId"], q("$filter=runKey eq %d" % rk)))
    rows = (r.json({}) or {}).get("value") if r is not None and r.status == 200 else None
    if not rows or any(x.get("columnKey") != c.get("columnKey") or x.get("runKey") != rk or x.get("profileKey") != pk for x in rows):
        return total, None
    pats = {}
    for x in rows:
        pats[x.get("patternLabel")] = pats.get(x.get("patternLabel"), 0) + int(x.get("satisfiedCount") or 0)
    if lg == lb or not ({lg, lb} & set(pats)) or sum(pats.values()) != total - nul:
        return total, None
    return total, (pats[lg] if lg in pats else total - nul - pats[lb])


def results(ctx, st):
    rows, rules = [], {r["name"]: r for r in tpl()["rules"]}
    by_frs = {v: k for k, v in (st.get("rulespecs") or {}).items()}
    for spec in tpl()["profiles"]:
        pid = (st.get("profiles") or {}).get(spec["name"])
        if not pid:
            print("%s: not built" % spec["name"])
            continue
        d = prof(ctx, "GET", "/profile/" + pid).json({})
        rd = latest_run(ctx, pid, d.get("lastRunKey"))
        if not rd:
            print("%s: no COMPLETED run yet" % spec["name"])
            continue
        rk = rd["runKey"]
        cols = ctx.read("profiling", MS + "/Profiles('%s')/Columns?%s" % (pid, q("$filter=runKey eq %d" % rk))).json({})
        by_id = {c.get("columnId"): c for c in cols.get("value") or []}
        for f in d.get("profileableFields") or []:
            if f.get("fieldType") != "MAPPLETFIELD":
                continue
            for om in f.get("outputFieldMappings") or []:
                c = by_id.get(om.get("id"))
                checked, passed = count_rule(ctx, pid, d.get("profileKey"), c, rk) if c and c.get("columnKey") == om.get("columnKey") \
                    else (None, None)
                rule = by_frs.get(f["frsId"], f["frsId"])
                rows.append({"layer": spec["layer"], "profile": pname(ctx.cfg, spec["name"]), "run_ref": rd.get("jobId") or rk,
                             "table": spec["table"], "column": f["inputFieldMappings"][0]["dataSourceFieldName"], "rule": rule,
                             "frs": f["frsId"], "dimension": (rules.get(rule) or {}).get("dimension"), "checked": checked,
                             "passed": passed, "failed": (checked - passed) if None not in (checked, passed) else None,
                             "score": round(100.0 * passed / checked, 1) if checked and passed is not None else None})
    return rows


def main():
    ap = C.parser(__doc__)
    ap.add_argument("cmd", choices=["rulespecs", "profiles", "build", "run", "results", "land"])
    ap.add_argument("which", nargs="?", default="all")
    a = ap.parse_args()
    ctx = C.Ctx(a)
    st = C.state()
    if a.cmd == "rulespecs":
        p = "%s/%s/" % (ctx.cfg["idmc"]["project"], ctx.cfg["idmc"]["folders"]["f3"])
        for o in C.v3_objects(ctx, "RULE_SPECIFICATION", p):
            print(o["path"], o["id"])
        for r in tpl()["rules"]:
            print("  spec: %-34s %-12s input %s" % (r["name"], r["dimension"], r["input"][0]))
    elif a.cmd == "profiles":
        for n, p in sorted(list_profiles(ctx).items()):
            print(n, p.get("id"))
        for s in tpl()["profiles"]:
            print("  spec: %-40s %-26s %s" % (pname(ctx.cfg, s["name"]), s["table"], ", ".join("%s->%s" % b for b in s["bindings"])))
    elif a.cmd == "build":
        build_rulespecs(ctx, st)
        build_profiles(ctx, st)
        if ctx.execute:
            C.save_state(st)
    elif a.cmd == "run":
        for s in tpl()["profiles"]:
            if a.which not in ("all", s["name"]):
                continue
            pid = (st.get("profiles") or {}).get(s["name"], "<profile id>")
            print(json.dumps(run_profile(ctx, s["name"], pid)))
    else:
        rows = [] if ctx.offline else results(ctx, st)
        for r in rows:
            print("%-7s %-24s %-18s %-34s %s/%s %s%%" % (r["layer"], r["table"], r["column"], r["rule"], r["passed"], r["checked"], r["score"]))
        if a.cmd == "land":
            sys.path.insert(0, str(C.BP / "infra"))
            import snowflake_sql as SQ  # noqa: E402
            now = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
            # values read back from IDMC profiling travel as SQL API bind variables, never inside the SQL text
            SQ.insert_rows(ctx.cfg, "BID_DQ_SCORECARD", [(
                now, r["layer"], r["profile"], r["run_ref"], r["table"], r["column"], rname(ctx.cfg, r["rule"]), r["frs"],
                r["dimension"], *(r[k] for k in ("checked", "passed", "failed", "score"))) for r in rows],
                bool(a.execute and rows))


if __name__ == "__main__":
    main()
