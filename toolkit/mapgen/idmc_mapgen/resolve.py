"""Fill a profile's ids BY NAME from the org (read-only): org, runtime environment, connections, project/folder.

    new_profile, changes, problems = resolve(client, profile)

- org: v2 id from GET /api/v2/org, the 22-character org guid from the login answer (orgUuid).
- runtimeEnvironment: GET /api/v2/runtimeEnvironment, matched on name (or id when only the id is given).
- connections: GET /api/v2/connection, matched on name. A spec connection needs three values and they all come
  from that one record: repoHandle = the v2 "id", guid = "federatedId" (the FRS guid the IMF binds to with
  "saas:@<guid>"), and kind (BQ / PG / JDBC / FF / SF) from the connector type.
- folder (+ every entry of the optional "folders" map): v3 objects of type Project / Folder, matched on path.
Names are the source of truth; ids copied from another org go stale after a migration.
"""
import copy
import urllib.parse

KIND_BY_CONNECTOR = {
    "google big query v2": "BQ", "googlebigqueryv2": "BQ", "google bigquery v2": "BQ", "bigquery": "BQ",
    "postgresql": "PG", "jdbcv2": "JDBC", "jdbc_v2": "JDBC", "csvfile": "FF", "flatfile": "FF",
    "salesforce": "SF",
}


def connector_kind(c):
    """BQ / PG / JDBC / FF / SF (None = unknown) from a v2 connection record."""
    for k in (c.get("instanceName"), c.get("instanceDisplayName"), c.get("type")):
        if k and k.lower() in KIND_BY_CONNECTOR:
            return KIND_BY_CONNECTOR[k.lower()]
    guid = (c.get("connectorGuid") or "").lower()
    if "bigquery" in guid:
        return "BQ"
    if "postgres" in guid:
        return "PG"
    if "jdbc" in guid:
        return "JDBC"
    return None


def v3_objects(client, type_):
    """All v3 objects of one type (paged)."""
    out, skip = [], 0
    q = urllib.parse.quote("type=='%s'" % type_, safe="=")
    while True:
        st, r = client.call("/public/core/v3/objects?limit=200&skip=%d&q=%s" % (skip, q), v3=True)
        if st != 200 or not isinstance(r, dict):
            raise RuntimeError("v3 objects type=%s -> %s %s" % (type_, st, str(r)[:300]))
        objs = r.get("objects", [])
        out += objs
        if len(objs) < 200:
            return out
        skip += 200


def folder_ids(client, path):
    """'Project/Folder' -> (projectGuid, folderGuid); (guid, None) for a bare 'Project'."""
    proj, _, fold = path.partition("/")
    pg = next((o["id"] for o in v3_objects(client, "Project") if o.get("path") == proj), None)
    fg = next((o["id"] for o in v3_objects(client, "Folder") if o.get("path") == path), None) if fold else None
    return pg, fg


def _set(d, key, val, changes, where):
    old = d.get(key)
    if val is not None and old != val:
        changes.append((where + "." + key, old, val))
        d[key] = val


def resolve(client, profile):
    """-> (new profile, [(key, old, new)], [problems]). Nothing is written to the org."""
    p = copy.deepcopy(profile or {})
    changes, problems = [], []
    who = client.whoami()
    org = p.setdefault("org", {})
    if org.get("v2Id") and org["v2Id"] != who["id"]:
        problems.append("profile org.v2Id %s but the login is in org %s (%s) - wrong credentials or profile?"
                        % (org["v2Id"], who["id"], who["name"]))
        return p, changes, problems
    _set(org, "v2Id", who["id"], changes, "org")
    _set(org, "guid", who["uuid"], changes, "org")
    _set(org, "name", who["name"], changes, "org")

    rt = p.get("runtimeEnvironment")
    if rt:
        st, envs = client.call("/api/v2/runtimeEnvironment")
        envs = envs if isinstance(envs, list) else []
        hit = next((e for e in envs if rt.get("name") and e.get("name") == rt["name"]), None) or \
            next((e for e in envs if rt.get("id") and e.get("id") == rt["id"]), None)
        if hit:
            _set(rt, "id", hit.get("id"), changes, "runtimeEnvironment")
            _set(rt, "name", hit.get("name"), changes, "runtimeEnvironment")
        else:
            problems.append("runtime environment %r not found (have: %s)" % (rt.get("name") or rt.get("id"),
                                                                          ", ".join(e.get("name", "?") for e in envs)))
    if p.get("connections"):
        st, conns = client.call("/api/v2/connection")
        conns = conns if isinstance(conns, list) else []
        by_name = {c.get("name"): c for c in conns}
        for alias, c in p["connections"].items():
            hit = by_name.get(c.get("name"))
            if not hit:
                problems.append("connection %s: no connection named %r in the org" % (alias, c.get("name")))
                continue
            _set(c, "repoHandle", hit.get("id"), changes, "connections." + alias)
            _set(c, "guid", hit.get("federatedId"), changes, "connections." + alias)
            if not c.get("kind"):
                _set(c, "kind", connector_kind(hit), changes, "connections." + alias)
            elif connector_kind(hit) and connector_kind(hit) != c["kind"]:
                problems.append("connection %s: profile kind %s but the org says %s (%s)"
                                % (alias, c["kind"], connector_kind(hit), hit.get("instanceName") or hit.get("type")))
    folders = []
    if p.get("folder"):
        folders.append(("folder", p["folder"]))
    for k, f in (p.get("folders") or {}).items():
        folders.append(("folders." + k, f))
    if folders:
        projects = {o.get("path"): o["id"] for o in v3_objects(client, "Project")}
        flist = {o.get("path"): o["id"] for o in v3_objects(client, "Folder")}
        for where, f in folders:
            pg = projects.get(f.get("project"))
            fg = flist.get("%s/%s" % (f.get("project"), f.get("name")))
            if pg is None:
                problems.append("%s: project %r not found" % (where, f.get("project")))
            if fg is None:
                problems.append("%s: folder %s/%s not found" % (where, f.get("project"), f.get("name")))
            _set(f, "projectGuid", pg, changes, where)
            _set(f, "guid", fg, changes, where)
    return p, changes, problems
