#!/usr/bin/env python3
"""bid_access.py - OPTIONAL: one IDMC user sees and runs ONLY the Bid Desk project (the access-limit pattern), with verify and undo.

    python bid_access.py plan                          # read the live state, save the backup, print every change (changes nothing)
    python bid_access.py apply [--execute --expect-org <orgIdV3>]   # make the changes in order, each recorded as it is made
    python bid_access.py verify                        # read it all back and check it
    python bid_access.py undo [--execute ...]          # put everything back the way the backup has it

Off unless config access.enabled is true. The idea (PROVEN 2026-10-13 on 972 permission entries):
  role privileges cap WHAT a user can do; object permissions cap WHICH objects a user can see.
  1. role '<access.role>': view + run only, copied privilege by privilege from the system roles 'Data Integration Task
     Executor' (Admin service: view project / folder / connection / agent / agent group only; DI: all) and 'Monitor'
     (DQ + Profile: all). POST /public/core/v3/roles {"name","description","privileges":[ids]} (the JSON property is
     'privileges'; 'privilegeIds' answers 400 V3API_007).
  2. group '<access.group>' with that role; the viewer joins it: PUT /public/core/v3/userGroups/<id>/addUsers {"users":[name]}.
  3. object permissions (all five: read, update, delete, execute, changePermission) for EVERY principal that must keep its
     access (access.keep_users, access.keep_groups and the CAI anonymous user, or CAI processes cannot run restricted DI
     tasks) on everything else the viewer role could list: the other projects, the other connections, the runtime
     environments this demo does not use. POST /public/core/v3/objects/<id>/permissions {"principal":{"type","name"},
     "permissions":{...}}. Once an object has ANY entry, only listed principals see it, so everyone else keeps exactly
     today's access and the viewer loses it. Left without entries on purpose: this project, its connections, its runtimes.
  4. the viewer leaves every other group (PUT /users/<id>/removeGroups {"groups":[...]}), gets the viewer role
     (PUT /users/<id>/addRoles {"roles":[NAMES]}) and loses the others (removeRoles; IDMC refuses to remove a user's last role,
     so add first).
Limits: the system role 'Admin' sees every asset whatever its object permissions; no catalog role is given (the catalog would
show every source). New objects created later are NOT hidden until you run apply again.
Files: state/access_backup.json (the state before; written once), state/access_registry.json (every change, for undo).
"""
from __future__ import annotations

import json
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
import bid_common as C  # noqa: E402

U = "/public/core/v3"
FULL = {"read": True, "update": True, "delete": True, "execute": True, "changePermission": True}
PRIVS = {"Data Integration Task Executor": {"Admin": {"view.project", "view.folder", "view.connection", "view.agent", "view.agent.group"},
                                            "DI": "*", "Monitor": "*"},
         "Monitor": {"DQ": "*", "Profile": "*"}}
BACKUP, REG = C.STATE_DIR / "access_backup.json", C.STATE_DIR / "access_registry.json"


def get(ctx, path, api="v3"):
    r = ctx.read(api, path)
    return r.json({}) if r is not None else {}


def q(s):
    return urllib.parse.quote(s, safe="")


def one(ctx, kind, field, name, expand=""):
    d = get(ctx, '%s/%s?q=%s==%%22%s%%22%s' % (U, kind, field, q(name), expand))
    return (d[0] if isinstance(d, list) and d else None) if not isinstance(d, dict) else None


def principals(ctx, acc):
    keep = [("USER", u) for u in acc["keep_users"]] + [("GROUP", g) for g in acc["keep_groups"]]
    if acc.get("cai_anonymous_user_prefix") and not acc["cai_anonymous_user_prefix"].startswith("<"):
        users = get(ctx, "%s/users?limit=200" % U)
        keep += [("USER", u["userName"]) for u in (users if isinstance(users, list) else [])
                 if u.get("userName", "").startswith(acc["cai_anonymous_user_prefix"])]
    return keep


def targets(ctx):
    cfg, st = ctx.cfg, C.state()
    proj = cfg["idmc"]["project"]
    out, skip = [], 0
    while not ctx.offline:
        d = get(ctx, "%s/objects?limit=200&skip=%d" % (U, skip))
        page = d.get("objects") or []
        for o in page:
            top = (o.get("path") or "").split("/")[0]
            if o.get("type") == "Project" and top not in (proj, "Add-On Bundles", "Default"):
                out.append(("Project", o["id"], o["path"]))
        if len(page) < 200:
            break
        skip += 200
    mine_c = set((st.get("conn") or {}).values())
    for c in (get(ctx, "/api/v2/connection", "v2") or []) if not ctx.offline else []:
        if c.get("id") not in mine_c and c.get("federatedId"):
            out.append(("Connection", c["federatedId"], c.get("name")))
    mine_r = set((st.get("runtime") or {}).values())
    for e in (get(ctx, "/api/v2/runtimeEnvironment", "v2") or []) if not ctx.offline else []:
        if e.get("id") not in mine_r and e.get("federatedId"):
            out.append(("RuntimeEnvironment", e["federatedId"], e.get("name")))
    return out


def main():
    ap = C.parser(__doc__)
    ap.add_argument("cmd", choices=["plan", "apply", "verify", "undo"])
    a = ap.parse_args()
    ctx = C.Ctx(a)
    acc = ctx.cfg["access"]
    if not acc.get("enabled"):
        print("access.enabled is false in config: this optional step is off (nothing read, nothing changed)")
        return
    user = one(ctx, "users", "userName", acc["viewer_user"]) or {"id": "<user id>", "userName": acc["viewer_user"], "groups": [], "roles": []}
    keep, t = principals(ctx, acc), targets(ctx)
    print("viewer %s | %d principals keep their access | %d objects get object permissions" % (acc["viewer_user"], len(keep), len(t)))
    if a.cmd == "plan":
        if not ctx.offline and not BACKUP.exists():
            C.STATE_DIR.mkdir(exist_ok=True)
            BACKUP.write_text(json.dumps({"user": user, "objects": {o[1]: get(ctx, "%s/objects/%s/permissions" % (U, o[1])) for o in t}},
                                         indent=1), encoding="utf-8")
            print("backup ->", BACKUP.relative_to(C.BP))
        for kind, oid, name in t[:50]:
            print("  %-18s %s" % (kind, name))
        return
    reg = json.loads(REG.read_text(encoding="utf-8")) if REG.exists() else {"made": []}
    if a.cmd == "apply":
        if not BACKUP.exists() and ctx.execute:
            C.H.die("run plan first (it writes the backup undo needs)")
        privs = {}
        for rn, want in PRIVS.items():
            r = one(ctx, "roles", "roleName", rn, "&expand=privileges") or {}
            for p in r.get("privileges") or []:
                pick = want.get(p.get("service"))
                if pick == "*" or (isinstance(pick, set) and p.get("name") in pick):
                    privs[p["id"]] = p.get("name")
        if not one(ctx, "roles", "roleName", acc["role"]):
            ctx.write("create role " + acc["role"], "v3", "POST", U + "/roles",
                      body={"name": acc["role"], "description": "Bid Desk demo: view and run only.", "privileges": sorted(privs) or ["<ids>"]})
            reg["made"].append({"role": acc["role"]})
        g = one(ctx, "userGroups", "userGroupName", acc["group"])
        if not g:
            r = ctx.write("create group " + acc["group"], "v3", "POST", U + "/userGroups",
                          body={"name": acc["group"], "description": "Bid Desk demo viewers.", "roles": [acc["role"]]})
            g = r.json({}) if C.ok(r) else {"id": "<group id>"}
            reg["made"].append({"group": acc["group"]})
        ctx.write("add the viewer to the group", "v3", "PUT", "%s/userGroups/%s/addUsers" % (U, g["id"]), body={"users": [acc["viewer_user"]]})
        for kind, oid, name in t:
            have = get(ctx, "%s/objects/%s/permissions" % (U, oid)) if not ctx.offline else []
            got = {(x["principal"]["type"], x["principal"]["name"]) for x in (have if isinstance(have, list) else [])}
            for ptype, pname in keep:
                if (ptype, pname) not in got:
                    r = ctx.write("permission %s on %s" % (pname, name), "v3", "POST", "%s/objects/%s/permissions" % (U, oid),
                                  body={"principal": {"type": ptype, "name": pname}, "permissions": FULL})
                    if C.ok(r):
                        d = r.json([])
                        ace = next((x for x in (d if isinstance(d, list) else []) if x.get("principal", {}).get("name") == pname), {})
                        reg["made"].append({"ace": [oid, ace.get("id"), pname]})
        if ctx.offline:
            ctx.write("permission <keep principal> on <every other object>", "v3", "POST", U + "/objects/<id>/permissions",
                      body={"principal": {"type": "GROUP", "name": "<group>"}, "permissions": FULL})
        others = [x.get("userGroupName") or x.get("name") for x in user.get("groups") or [] if (x.get("userGroupName") or x.get("name")) != acc["group"]]
        ctx.write("viewer gets the viewer role", "v3", "PUT", "%s/users/%s/addRoles" % (U, user["id"]), body={"roles": [acc["role"]]})
        if others:
            ctx.write("viewer leaves the other groups", "v3", "PUT", "%s/users/%s/removeGroups" % (U, user["id"]), body={"groups": others})
            reg["removed_groups"] = others
        roles = [x.get("roleName") or x.get("name") for x in user.get("roles") or [] if (x.get("roleName") or x.get("name")) != acc["role"]]
        if roles:
            ctx.write("viewer loses the other roles", "v3", "PUT", "%s/users/%s/removeRoles" % (U, user["id"]), body={"roles": roles})
            reg["removed_roles"] = roles
        if ctx.execute:
            REG.write_text(json.dumps(reg, indent=1), encoding="utf-8")
    elif a.cmd == "verify":
        if ctx.offline:
            print("[OFFLINE] would read the viewer's groups and roles and every target's permissions")
            return
        bad = [n for k, oid, n in t if any(x["principal"]["name"] == acc["viewer_user"] for x in get(ctx, "%s/objects/%s/permissions" % (U, oid)) or [])]
        gs = [x.get("userGroupName") for x in user.get("groups") or []]
        print("groups %s | roles %s | objects still open to the viewer: %d" % (gs, [x.get("roleName") for x in user.get("roles") or []], len(bad)))
    else:
        for m in reversed(reg.get("made") or []):
            if "ace" in m:
                oid, ace_id, pname = m["ace"]
                ctx.write("remove permission %s" % pname, "v3", "DELETE", "%s/objects/%s/permissions/%s" % (U, oid, ace_id))
        if reg.get("removed_groups"):
            ctx.write("viewer rejoins its groups", "v3", "PUT", "%s/users/%s/addGroups" % (U, user["id"]), body={"groups": reg["removed_groups"]})
        ctx.write("viewer leaves the viewer group", "v3", "PUT", "%s/users/%s/removeGroups" % (U, user["id"]), body={"groups": [acc["group"]]})
        if reg.get("removed_roles"):
            ctx.write("viewer gets its roles back", "v3", "PUT", "%s/users/%s/addRoles" % (U, user["id"]), body={"roles": reg["removed_roles"]})
        print("then delete the group and role in Administrator > User Groups / User Roles, or keep them for the next demo")


if __name__ == "__main__":
    main()
