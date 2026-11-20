"""IDMC source-control helpers (v3 REST: checkout / checkin / undoCheckout / sourceControlAction).

Used by deploy.import_package: before an OVERWRITE import, check out the objects in the package that are already
source-controlled; after a SUCCESSFUL import check them back in; after a failed one undo the checkout.
In an org without source control (or for objects that are not source-controlled) every step is a quiet no-op,
so an import behaves exactly as it would without this module.
"""
import io
import json
import time
import urllib.parse
import zipfile

# object types IDMC can source-control (v3 checkin reference)
SC_TYPES = {"DTEMPLATE", "MTT", "DSS", "DMASK", "DRS", "DMAPPLET", "MAPPLET", "BSERVICE", "HSCHEMA", "PCS", "FWCONFIG",
            "CUSTOMSOURCE", "MI_TASK", "WORKFLOW", "TASKFLOW", "UDF", "PROCESS", "AI_CONNECTION",
            "AI_SERVICE_CONNECTOR", "GUIDE", "PROCESS_OBJECT", "HUMAN_TASK"}
OK_STATES = ("SUCCESSFUL", "WARNING")


def package_objects(pkg_bytes):
    """[(guid, type, folder path)] of the source-controllable objects named in a package's exportMetadata.v2.json."""
    z = zipfile.ZipFile(io.BytesIO(pkg_bytes))
    meta = json.loads(z.read("exportMetadata.v2.json"))
    out = []
    for o in meta.get("exportedObjects", []):
        t = (o.get("objectType") or "").upper()
        if t in SC_TYPES:
            folder = (o.get("path") or "").replace("/Explore/", "", 1).strip("/")   # '/Explore/P/F' -> 'P/F'
            out.append((o.get("objectGuid"), t, folder))
    return out


def objects_in(client, folder, type_):
    """v3 objects of one type in one folder ('Project/Folder'), all pages."""
    out, skip = [], 0
    q = urllib.parse.quote("location=='%s' and type=='%s'" % (folder, type_), safe="=")
    while True:
        st, o = client.call("/public/core/v3/objects?limit=200&skip=%d&q=%s" % (skip, q), v3=True)
        objs = (o or {}).get("objects", []) if isinstance(o, dict) else []
        out += objs
        if st != 200 or len(objs) < 200:
            return out
        skip += 200


def controlled(client, pkg_objs):
    """Guids among pkg_objs [(guid, type, folder)] that already exist in the org AND are source-controlled."""
    seen, out = {}, []
    for g, t, folder in pkg_objs:
        if not folder:
            continue
        key = (folder, t)
        if key not in seen:
            seen[key] = objects_in(client, folder, t)
        if any(x.get("id") == g and x.get("sourceControl") for x in seen[key]):
            out.append(g)
    return out


def _wait(client, action, label, log=print, poll_s=4, tries=90):
    aid = (action or {}).get("id") or (action or {}).get("Id") if isinstance(action, dict) else None
    if not aid:
        return None, action
    for _ in range(tries):
        time.sleep(poll_s)
        st, s = client.call("/public/core/v3/sourceControlAction/%s?expand=objects" % aid, v3=True)
        state = ((s or {}).get("status") or {}).get("state") if isinstance(s, dict) else None
        if state not in ("NOT_STARTED", "IN_PROGRESS", None):
            log("%s %s %s" % (label, state, (((s.get("status") or {}).get("message")) or "")[:300]))
            return state, s
    log("%s TIMEOUT waiting for %s" % (label, aid))
    return "TIMEOUT", None


def checkout(client, guids, log=print):
    """Check out the given (source-controlled) objects. Raises if the checkout does not succeed."""
    if not guids:
        return []
    st, r = client.call("/public/core/v3/checkout", {"objects": [{"id": i} for i in guids]}, method="POST", v3=True)
    log("checkout %s %s" % (st, str(r)[:200]))
    if st not in (200, 201, 202):
        raise RuntimeError("checkout failed - not importing over source-controlled objects: %s %s" % (st, str(r)[:300]))
    state, _ = _wait(client, r, "checkout", log)
    if state not in OK_STATES:
        raise RuntimeError("checkout did not succeed (%s) - not importing" % state)
    return list(guids)


def checkin(client, guids, summary, log=print):
    """Check in the objects (new ones become source-controlled). Quietly skipped when the org has no source control."""
    if not guids:
        return None
    body = {"objects": [{"id": g, "includeContainerAssets": False} for g in guids], "summary": summary[:255]}
    st, r = client.call("/public/core/v3/checkin", body, method="POST", v3=True)
    log("checkin %s %s" % (st, str(r)[:200]))
    if st not in (200, 201, 202):
        log("checkin skipped (org source control off, or objects not eligible)")
        return None
    state, _ = _wait(client, r, "checkin", log)
    return state


def undo_checkout(client, guids, log=print):
    if guids:
        st, r = client.call("/public/core/v3/undoCheckout", {"objects": [{"id": i} for i in guids]}, method="POST", v3=True)
        log("undoCheckout %s %s" % (st, str(r)[:200]))
        _wait(client, r, "undoCheckout", log)
