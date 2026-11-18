"""The live half: import a package, find the mapping, ensure its mapping task, run it, read the logs.

    from idmc_mapgen.deploy import deploy
    rec = deploy("examples/retail/m_rdf_customer_cleanse.json", profile="profile.local.json", run=True)

Steps of ``deploy`` (each is also a function you can call alone):
  lint (when idmc_mapgen.lint is present)  ->  guards  ->  build the IMF  ->  package (a trial on a copy: a build or
  package SpecError costs no IDMC session)  ->  assert the org  ->  find the existing mapping  ->  package
  ->  import_package (REUSE the first time; OVERWRITE under the SAME guid once the mapping exists in the folder)
  ->  find_mapping (by name INSIDE the folder, never by name alone)  ->  ensure_task (reuse or create + move)
  ->  run_task (optional; POST /api/v2/job, poll the activity log by runId).
Every live write runs under ``lock.live_lock`` (one live sequence at a time) and every job start is written
to the job ledger (``lock.record_job``), so a test campaign can respect a job budget.
The package and the IMF go to <workDir>/<name>.pkg.zip and .imf.json, a JSON record of each deploy to
<workDir>/runs/ (workDir: profile "workDir", default ./build; <name> = package.safe_file_name of the mapping name).
"""
import copy
import json
import os
import re
import time
import uuid

from . import lock, sc
from .client import Client

STATE_NAMES = {1: "SUCCESS", 2: "WARNING", 3: "FAILED"}
_IMPORT_RUNNING = ("IN_PROGRESS", "QUEUED", "NOT_STARTED", None)
_TASK_READONLY = ("orgId", "createTime", "updateTime", "createdBy", "updatedBy")


class DeployError(RuntimeError):
    pass


def _utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _text(x):
    if isinstance(x, bytes):
        return x.decode("utf-8", errors="replace")
    if isinstance(x, str):
        return x
    return json.dumps(x)


def _excerpt(text, n=40):
    lines = [l for l in text.splitlines() if l.strip()]
    hot = [l for l in lines if re.search(r"(?i)error|fail|exception|invalid|warn", l)]
    pick = hot[-n:] if hot else lines[-n:]
    return "\n".join(l[:400] for l in pick)


def multipart(field, filename, data, ctype="application/zip"):
    """(body bytes, Content-Type header) for a one-file multipart/form-data upload."""
    boundary = "mapgen" + uuid.uuid4().hex
    head = ('--%s\r\nContent-Disposition: form-data; name="%s"; filename="%s"\r\nContent-Type: %s\r\n\r\n'
            % (boundary, field, filename, ctype)).encode()
    return head + data + ("\r\n--%s--\r\n" % boundary).encode(), "multipart/form-data; boundary=" + boundary


# ---------------------------------------------------------------- import
def import_package(client, pkg_bytes, mode="REUSE", source_control=True, checkin_new=False, name=None,
                   poll_s=4, timeout_s=900, log=print):
    """Upload + start + poll a v3 package import. Returns {jobId, state, objects, log}. Raises unless SUCCESSFUL.

    source_control: check out the package's already source-controlled objects before an OVERWRITE and check them
    back in afterwards (no-op in orgs without source control). checkin_new: also check in objects the import
    created (they become source-controlled; off by default so scratch builds stay out of the repository).
    """
    if mode not in ("REUSE", "OVERWRITE"):
        raise ValueError("mode must be REUSE or OVERWRITE, not %r" % mode)
    pkg_objs = sc.package_objects(pkg_bytes) if source_control else []
    ctl = sc.controlled(client, pkg_objs) if pkg_objs else []
    checked_out = sc.checkout(client, ctl, log) if (mode == "OVERWRITE" and ctl) else []
    jid, state, msg, log_text, objs = None, None, "", "", []
    try:
        body, ct = multipart("package", "pkg.zip", pkg_bytes)
        st, up = client.call("/public/core/v3/import/package", raw=body, ctype=ct, v3=True, method="POST", timeout=600)
        if st != 200 or not isinstance(up, dict) or not up.get("jobId"):
            raise DeployError("package upload failed: %s %s" % (st, str(up)[:500]))
        jid = up["jobId"]
        if up.get("checksumValid") is False:
            log("warning: the service reports checksumValid=false (expect MigrationSvc_073)")
        st, r = client.call("/public/core/v3/import/%s" % jid,
                            {"name": name or "mapgen_import_%d" % time.time(),
                             "importSpecification": {"defaultConflictResolution": mode}}, v3=True, method="POST")
        if st not in (200, 201, 202):
            raise DeployError("import start failed: %s %s" % (st, str(r)[:500]))
        t0 = time.time()
        while True:
            time.sleep(poll_s)
            st, s = client.call("/public/core/v3/import/%s" % jid, v3=True)
            status = (s.get("status") or {}) if isinstance(s, dict) else {}
            state, msg = status.get("state"), status.get("message") or ""
            if state not in _IMPORT_RUNNING:
                break
            if time.time() - t0 > timeout_s:
                state = "TIMEOUT"
                break
        st, lg = client.call("/public/core/v3/import/%s/log" % jid, v3=True, accept="*/*")
        log_text = _text(lg)
        st, d = client.call("/public/core/v3/import/%s?expand=objects" % jid, v3=True)
        for o in (d.get("objects") or []) if isinstance(d, dict) else []:
            so, to = o.get("sourceObject") or {}, o.get("targetObject") or {}
            objs.append({"name": so.get("name"), "type": so.get("type"), "id": to.get("id"), "status": o.get("status")})
    except Exception:
        if checked_out:
            sc.undo_checkout(client, checked_out, log)
        raise
    if state != "SUCCESSFUL":
        if checked_out:
            sc.undo_checkout(client, checked_out, log)
        raise DeployError("import %s ended %s: %s\n--- import log (excerpt) ---\n%s" % (jid, state, msg, _excerpt(log_text)))
    if source_control:
        new = [g for g, _, _ in pkg_objs if g not in ctl] if checkin_new else []
        if checked_out or new:
            sc.checkin(client, checked_out + new, "mapgen import (%s)" % mode, log)
    log("import %s %s (%s)" % (jid, state, mode))
    return {"jobId": jid, "state": state, "message": msg, "objects": objs, "log": log_text[-4000:], "checkedOut": checked_out}


# ---------------------------------------------------------------- mapping / task lookup
def _last(path):
    return (path or "").rstrip("/").rsplit("/", 1)[-1]


def find_mapping(client, name, folder_path, retries=5, wait_s=3):
    """The mapping named ``name`` inside ``folder_path`` ('Project/Folder'): {id (v2), frsGuid, name, path} or None.

    The v3 folder listing gives the mapping's FRS guid; the v2 list is matched on assetFrsGuid, so a same-named
    mapping in another folder can never be picked up.
    """
    hits = [o for o in sc.objects_in(client, folder_path, "DTEMPLATE") if _last(o.get("path")) == name]
    if not hits:
        return None
    if len(hits) > 1:
        raise DeployError("%d mappings named %s in %s" % (len(hits), name, folder_path))
    guid = hits[0]["id"]
    for i in range(retries):
        st, ms = client.call("/api/v2/mapping")
        if st == 200 and isinstance(ms, list):
            same = [m for m in ms if m.get("name") == name]
            for m in same:
                if m.get("assetFrsGuid") == guid:
                    return {"id": m["id"], "frsGuid": guid, "name": name, "path": hits[0]["path"], "valid": m.get("valid")}
            for m in same:                       # the list may omit assetFrsGuid: read each same-named mapping
                if "assetFrsGuid" not in m:
                    st2, full = client.call("/api/v2/mapping/%s" % m["id"])
                    if st2 == 200 and isinstance(full, dict) and full.get("assetFrsGuid") == guid:
                        return {"id": m["id"], "frsGuid": guid, "name": name, "path": hits[0]["path"], "valid": full.get("valid")}
        time.sleep(wait_s)                       # just after an import the v2 list can lag the v3 catalog
    raise DeployError("mapping %s is in %s (frs %s) but has no v2 id yet" % (name, folder_path, guid))


def find_task(client, name, folder_path):
    """The mapping task named ``name`` inside ``folder_path``: the full v2 mttask object, or None."""
    hits = [o for o in sc.objects_in(client, folder_path, "MTT") if _last(o.get("path")) == name]
    if not hits:
        return None
    frs_ids = {o["id"] for o in hits}
    st, ts = client.call("/api/v2/mttask")
    if st != 200 or not isinstance(ts, list):
        raise DeployError("GET /api/v2/mttask -> %s %s" % (st, str(ts)[:300]))
    for t in ts:
        if t.get("name") == name:
            st, full = client.call("/api/v2/mttask/%s" % t["id"])
            if st == 200 and isinstance(full, dict) and full.get("frsGuid") in frs_ids:
                return full
    return None


def move_into(client, frs_guid, name, folder_guid, description=""):
    """FRS MoveEntities (objects are born in Default). Returns the FRS answer."""
    body = {"xferSpec": {"targetLocationId": folder_guid, "sourceSpecArr": [
        {"sourceEntityId": frs_guid, "destName": name, "destDesc": description or "", "conflictResolution": "NONE",
         "resetExpiryTime": False, "mergeTags": ""}]}}
    st, r = client.frs("POST", "MoveEntities", body)
    if st != 200:
        raise DeployError("FRS MoveEntities -> %s %s" % (st, str(r)[:400]))
    return r


def ensure_task(client, name, mapping_id, runtime_env_id, folder, description="", log=print):
    """Reuse the task ``name`` in ``folder`` ({path, guid}) or create it (born in Default) and move it there.

    A reused task is re-pointed when its mappingId or runtime environment differ (GET -> edit -> POST to the id,
    then read back). Returns {id, frsGuid, name, created, updated, moved}.
    """
    if not runtime_env_id:
        raise DeployError("no runtime environment id (profile runtimeEnvironment.id)")
    t = find_task(client, name, folder["path"])
    created = moved = updated = False
    if t is None:
        t = find_task(client, name, "Default")       # a previous attempt created it but never moved it
        if t is None:
            st, r = client.call("/api/v2/mttask", {"@type": "mtTask", "name": name, "description": description,
                                                   "mappingId": mapping_id, "runtimeEnvironmentId": runtime_env_id}, method="POST")
            if st != 200 or not isinstance(r, dict) or not r.get("id"):
                raise DeployError("create mttask %s -> %s %s" % (name, st, str(r)[:400]))
            created = True
            st, t = client.call("/api/v2/mttask/%s" % r["id"])
            log("created task %s %s" % (name, r["id"]))
        move_into(client, t["frsGuid"], name, folder["guid"], description)
        moved = True
    if t.get("mappingId") != mapping_id or t.get("runtimeEnvironmentId") != runtime_env_id:
        body = {k: v for k, v in t.items() if k not in _TASK_READONLY}
        body["mappingId"], body["runtimeEnvironmentId"] = mapping_id, runtime_env_id
        st, r = client.call("/api/v2/mttask/%s" % t["id"], body, method="POST")
        if st != 200:
            raise DeployError("update mttask %s -> %s %s" % (name, st, str(r)[:400]))
        updated = True
    back = find_task(client, name, folder["path"])
    if back is None or back["id"] != t["id"]:
        raise DeployError("task %s (%s) is not in %s after the move" % (name, t["id"], folder["path"]))
    if back.get("mappingId") != mapping_id:
        raise DeployError("task %s still points at mapping %s, not %s" % (name, back.get("mappingId"), mapping_id))
    return {"id": back["id"], "frsGuid": back["frsGuid"], "name": name, "created": created, "updated": updated, "moved": moved}


# ---------------------------------------------------------------- run
def wait_quiet(client, prefixes, max_wait_s=900, poll_s=20, log=print):
    """Wait while any running task's name starts with one of ``prefixes`` (the shared agent's live lanes).

    Returns the seconds waited. After max_wait_s it stops waiting and lets the run start (with a warning):
    a small test run beside a long live lane is acceptable, a test that never runs is not.
    """
    if not prefixes:
        return 0
    t0 = time.time()
    while True:
        st, mon = client.call("/api/v2/activity/activityMonitor")
        names = [m.get("taskName", "") for m in mon] if isinstance(mon, list) else []
        busy = [n for n in names if n.startswith(tuple(prefixes))]
        if not busy:
            return int(time.time() - t0)
        if time.time() - t0 > max_wait_s:
            log("warning: still busy after %d s (%s); starting anyway" % (max_wait_s, ", ".join(busy[:5])))
            return int(time.time() - t0)
        log("waiting: live tasks running (%s)" % ", ".join(busy[:3]))
        time.sleep(poll_s)


def per_target_rows(entry):
    """[{tx, table, type, success, failed}] from an activity-log entry's transformationEntries (all levels)."""
    out = []

    def walk(e):
        for t in e.get("transformationEntries") or []:
            out.append({"tx": t.get("txInstanceName"), "table": t.get("txName"), "type": t.get("txType"),
                        "success": t.get("successRows"), "failed": t.get("failedRows")})
        for sub in e.get("entries") or []:
            walk(sub)
    walk(entry)
    return out


def run_task(client, task_id, timeout_s=3600, poll_s=8, owner="mapgen", task_name=None, quiet=None, log=print):
    """POST /api/v2/job, then poll the activity log until THIS runId has an endTime.

    Returns {runId, state (1/2/3), stateName, successTargetRows, failedTargetRows, errorMsg, activityId,
    targets: [...], sources: [...], startTime, endTime, wall_s}. stateName TIMEOUT when timeout_s passes.
    """
    if quiet:
        wait_quiet(client, quiet, log=log)
    t_req = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
    st, r = client.call("/api/v2/job", {"@type": "job", "taskId": task_id, "taskType": "MTT"}, method="POST")
    if st != 200 or not isinstance(r, dict):
        raise DeployError("job start for %s -> %s %s" % (task_id, st, str(r)[:400]))
    rid = r.get("runId")
    lock.record_job(owner, task_id, task_name or r.get("taskName"), rid, "STARTED")
    log("job started: task %s runId %s" % (task_id, rid))
    t0 = time.time()
    while True:
        time.sleep(poll_s)
        st, al = client.call("/api/v2/activity/activityLog?taskId=%s&rowLimit=1" % task_id)
        if isinstance(al, list) and al:
            a = al[0]
            mine = (a.get("runId") == rid) if rid is not None else ((a.get("startTimeUtc") or "") >= t_req)
            if mine and a.get("endTime"):
                break
        if time.time() - t0 > timeout_s:
            return {"runId": rid, "state": None, "stateName": "TIMEOUT", "wall_s": int(time.time() - t0)}
    rows = per_target_rows(a)
    return {"runId": rid, "state": a.get("state"), "stateName": STATE_NAMES.get(a.get("state"), str(a.get("state"))),
            "successTargetRows": a.get("successTargetRows"), "failedTargetRows": a.get("failedTargetRows"),
            "successSourceRows": a.get("successSourceRows"), "errorMsg": a.get("errorMsg") or "", "activityId": a.get("id"),
            "targets": [x for x in rows if x["type"] == "TARGET"], "sources": [x for x in rows if x["type"] == "SOURCE"],
            "startTime": a.get("startTimeUtc") or a.get("startTime"), "endTime": a.get("endTimeUtc") or a.get("endTime"),
            "wall_s": int(time.time() - t0)}


def session_log(client, activity_id):
    """The session log text of one activity-log entry (top-level id)."""
    st, lg = client.call("/api/v2/activity/activityLog/%s/sessionLog" % activity_id, accept="*/*")
    if st != 200:
        raise DeployError("session log %s -> %s %s" % (activity_id, st, str(lg)[:300]))
    return _text(lg)


# ---------------------------------------------------------------- deploy
def task_name_for(mapping_name):
    return "mt_" + mapping_name[2:] if mapping_name.startswith("m_") else "mt_" + mapping_name


def folder_path_of(spec):
    f = spec.get("folder") or {}
    return "%s/%s" % (f.get("project"), f.get("name"))


def work_dir(profile):
    return os.path.expanduser((profile or {}).get("workDir") or "build")


def _write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, default=str)


def find_mapplet(client, name, folder_path):
    """The mapplet named ``name`` inside ``folder_path``: {frsGuid, name, path} or None (mapplets have no v2 id)."""
    hits = [o for o in sc.objects_in(client, folder_path, "DMAPPLET") if _last(o.get("path")) == name]
    if len(hits) > 1:
        raise DeployError("%d mapplets named %s in %s" % (len(hits), name, folder_path))
    return {"frsGuid": hits[0]["id"], "name": name, "path": hits[0]["path"]} if hits else None


def _deploy_mapplet(s, prof, rec, fpath, dry_run, mode, client, owner, use_sc, sc_cfg, log):
    """A spec with documentType DMAPPLET: build -> DMAPPLET package -> import. No task: a mapplet only runs inside a mapping
    (reference it from a mapping's "mapplet" node with the frsGuid printed here, plus an "assets" entry)."""
    from . import compile as compiler
    from .nodes.mapplet import mapplet_package_bytes, package_ignored_message
    from .package import safe_file_name
    imf = compiler.build(s)
    ignored = package_ignored_message(s)     # assets / projectJson / folderJson / packageOverrides (lint: MPLT_PKG_IGNORED)
    if ignored:
        log("warning: %s" % ignored)
    existing = None
    if not dry_run:
        mapplet_package_bytes(copy.deepcopy(s), imf, guid=s.get("guid"))   # first: a package SpecError costs no session
        client = client or Client(prof)
        rec["org"] = client.assert_org()["id"]
        existing = find_mapplet(client, s["name"], fpath)
        if existing:
            s["guid"] = existing["frsGuid"]
    mode = mode or ("OVERWRITE" if existing else "REUSE")
    pkg = mapplet_package_bytes(s, imf, guid=s.get("guid"))
    wd = work_dir(prof)
    os.makedirs(wd, exist_ok=True)
    stem = safe_file_name(s["name"])         # 'm_a:b.pkg.zip' would land in an NTFS alternate data stream
    pkg_path = os.path.join(wd, stem + ".pkg.zip")
    with open(pkg_path, "wb") as f:
        f.write(pkg)
    _write_json(os.path.join(wd, stem + ".imf.json"), imf)
    rec.update(kind="DMAPPLET", package=pkg_path, mode=mode, transformations=len(imf["content"]["transformations"]),
               existed=bool(existing))
    rec_path = os.path.join(wd, "runs", "%s_%s.json" % (time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()), stem))
    if dry_run:
        _write_json(rec_path, rec)
        return rec
    with lock.live_lock(owner):
        rec["import"] = {k: v for k, v in import_package(client, pkg, mode, source_control=use_sc,
                                                         checkin_new=sc_cfg.get("checkinNew", False), log=log).items() if k != "log"}
        m = None
        for _ in range(10):
            m = find_mapplet(client, s["name"], fpath)
            if m:
                break
            time.sleep(3)
    if not m:
        raise DeployError("import succeeded but mapplet %s is not in %s" % (s["name"], fpath))
    rec["mapplet"] = m
    log("mapplet %s: frs guid %s (reference it as mappletGuid, with an assets entry type DMAPPLET path /Explore/%s)"
        % (s["name"], m["frsGuid"], fpath))
    _write_json(rec_path, rec)
    rec["record"] = rec_path
    return rec


def deploy(spec, profile=None, run=False, dry_run=False, mode=None, allow_live=False, force_lint=False,
           owner="mapgen", client=None, log=print, source_control=None, vars=None, default_profile=None):
    """lint -> build -> package -> (import -> task -> run). ``spec``: path or dict. Returns the run record.

    The profile is chosen as spec.load_spec chooses it: ``profile`` (path or non-empty dict), else the spec's own
    "profile" key, else ``default_profile``. That one profile (and ``vars``) feeds the package, lint, the guards,
    the workDir and the client, so they always agree."""
    from . import compile as compiler, package as packager, spec as specmod
    s, prof = specmod.load_spec_and_profile(spec, profile=profile, vars=vars, default_profile=default_profile)
    fpath = folder_path_of(s)
    rec = {"t": _utc(), "spec": os.fspath(spec) if isinstance(spec, (str, os.PathLike)) else "<dict>", "name": s["name"],
           "folder": fpath, "dry_run": dry_run, "owner": owner}
    try:
        from . import lint as lintmod
    except ImportError:
        lintmod = None
    if lintmod is not None:
        # the RAW spec with the same profile arguments and vars: lint picks the profile and loads the spec exactly as
        # load_spec did. Never a loaded spec (its $${X} escapes are already consumed), and never `prof` itself: an
        # explicit profile file holding {} reads as "not given" there, and lint would fall back to the spec's own key.
        issues = lintmod.lint(spec, profile, allow_live, vars=vars, default_profile=default_profile)
        rec["lint"] = lintmod.summary(issues)
        if lintmod.has_errors(issues) and not force_lint:
            raise DeployError("lint found errors (fix them, or force_lint=True / --force-lint):\n"
                              + lintmod.format_issues(issues, "error"))
    else:
        rec["lint"] = "lint module not installed"
    guards = prof.get("guards") or {}
    if not allow_live:                  # enforced here too, so --force-lint can never bypass a guard
        for pat in guards.get("protectedFolders") or []:
            if re.search(pat, fpath):
                raise DeployError("folder %s matches protected pattern %r (pass allow_live for a reviewed swap)" % (fpath, pat))
        pats = guards.get("protectedTargets") or []
        for nd in s["nodes"]:
            if nd.get("type") != "target":
                continue
            obj, alias = nd.get("object", ""), nd.get("conn", "")
            if pats and not isinstance(obj, str):   # unjudgeable (--force-lint got it here): fail closed, never a TypeError
                raise DeployError("target %s: 'object' must be a string (the table it writes), got %r, so the "
                                  "protectedTargets guard cannot check it" % (nd.get("name"), obj))
            cname = (s["connections"].get(alias) or {}).get("name", "")
            for pat in pats:
                if any(re.search(pat, c) for c in (obj, "%s:%s" % (alias, obj), "%s:%s" % (cname, obj))):
                    raise DeployError("target %s (%s) matches protected pattern %r (pass allow_live for a reviewed swap)"
                                      % (nd.get("name"), obj, pat))
    sc_cfg = prof.get("sourceControl") or {}
    use_sc = sc_cfg.get("enabled", True) if source_control is None else source_control
    if s.get("documentType") == "DMAPPLET":
        return _deploy_mapplet(s, prof, rec, fpath, dry_run, mode, client, owner, use_sc, sc_cfg, log)
    imf = compiler.build(s)
    existing = None
    if not dry_run:
        packager.package_bytes(copy.deepcopy(s), imf)   # first: a package SpecError (an unreadable folderJson ...) costs no session
        client = client or Client(prof)
        rec["org"] = client.assert_org()["id"]
        existing = find_mapping(client, s["name"], fpath)
        if existing:
            if s.get("guid") and s["guid"] != existing["frsGuid"]:
                log("warning: spec guid %s differs from the existing mapping's %s; keeping the existing one"
                    % (s["guid"], existing["frsGuid"]))
            s["guid"] = existing["frsGuid"]
    mode = mode or ("OVERWRITE" if existing else "REUSE")
    pkg = packager.package_bytes(s, imf)
    wd = work_dir(prof)
    os.makedirs(wd, exist_ok=True)
    stem = packager.safe_file_name(s["name"])    # 'm_a:b.pkg.zip' would land in an NTFS alternate data stream
    pkg_path = os.path.join(wd, stem + ".pkg.zip")
    with open(pkg_path, "wb") as f:
        f.write(pkg)
    _write_json(os.path.join(wd, stem + ".imf.json"), imf)
    rec.update(guid=s["guid"], package=pkg_path, mode=mode, transformations=len(imf["content"]["transformations"]),
               links=len(imf["content"]["links"]), existed=bool(existing))
    rec_path = os.path.join(wd, "runs", "%s_%s.json" % (time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()), stem))
    if dry_run:
        _write_json(rec_path, rec)
        return rec
    with lock.live_lock(owner):
        rec["import"] = {k: v for k, v in import_package(client, pkg, mode, source_control=use_sc,
                                                         checkin_new=sc_cfg.get("checkinNew", False), log=log).items() if k != "log"}
        m = None
        for _ in range(10):
            m = find_mapping(client, s["name"], fpath)
            if m:
                break
            time.sleep(3)
        if not m:
            raise DeployError("import succeeded but mapping %s is not in %s" % (s["name"], fpath))
        if m["frsGuid"] != s["guid"]:
            log("warning: the imported mapping has frs guid %s, the package said %s" % (m["frsGuid"], s["guid"]))
        rec["mapping"] = m
        tname = s.get("taskName") or task_name_for(s["name"])
        re_id = (s.get("runtimeEnvironment") or {}).get("id")
        rec["task"] = ensure_task(client, tname, m["id"], re_id, {"path": fpath, "guid": s["folder"]["guid"]},
                                  s.get("description", ""), log)
        if run:
            rec["run"] = run_task(client, rec["task"]["id"], owner=owner, task_name=tname,
                                  quiet=guards.get("busyTaskPrefixes"), log=log)
    _write_json(rec_path, rec)
    rec["record"] = rec_path
    return rec
