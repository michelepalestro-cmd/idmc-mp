#!/usr/bin/env python3
"""bid_project.py - the IDMC project, its five stage folders and the runtime environments the Bid Desk uses.

    python bid_project.py show                                  # what exists now (read-only)
    python bid_project.py build [--execute --expect-org <orgIdV3>]   # create what is missing; ids -> state/ids.json
    python bid_project.py --offline build                       # print every request, never log in

Calls (PROVEN 2026-10-13 on the source demo):
  GET  v3 /public/core/v3/objects?q=type=='Project'          (and type=='Folder')
  POST v3 /public/core/v3/projects {"name","description"}
       If the name is refused (a dot in the name was refused once), create it as idmc.project_fallback_name and rename it
       through FRS: PATCH <pod>/frs/api/v1/Projects('<id>') {"name": <project>} (KB L-MIG-075).
  POST v3 /public/core/v3/projects/<projectId>/folders {"name","description"}
  GET  v2 /api/v2/runtimeEnvironment                          (names in config idmc.runtime_environment[_crm] -> ids)
Undo: teardown/bid_teardown.py (the project goes last, after everything in it).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
import bid_common as C  # noqa: E402

DESC = ("Bid Desk demo: public-sector solicitation PDFs attached in the CRM -> transferred to SharePoint -> read by CLAIRE -> "
        "Data Quality -> Snowflake Bronze / Silver / Gold (BID_*) -> Tableau. One nightly pipeline. Built headless.")
FOLDER_DESC = {
    "f1": "The agencies and the bid documents attached to them in the CRM, transferred to SharePoint.",
    "f2": "CLAIRE intelligent structure models + Structure Parser mappings: each solicitation PDF into Snowflake Bronze rows.",
    "f3": "Data Quality rule specifications, the Silver mappings that apply them, and the Data Profiling profiles.",
    "f4": "Gold: one bid-readiness decision per solicitation for the sales desk.",
    "f5": "The taskflows that run the pipeline end to end (the nightly batch) and reset it to its starting point.",
}


def objs(ctx, otype):
    return C.v3_objects(ctx, otype)


def main():
    ap = C.parser(__doc__)
    ap.add_argument("cmd", choices=["show", "build"])
    a = ap.parse_args()
    ctx = C.Ctx(a)
    cfg, st = ctx.cfg, C.state()
    proj_name = cfg["idmc"]["project"]
    proj = next((o for o in objs(ctx, "Project") if o.get("path") == proj_name), None)
    print("project %r: %s" % (proj_name, proj["id"] if proj else "MISSING"))
    if a.cmd == "build" and not proj:
        r = ctx.write("create project", "v3", "POST", "/public/core/v3/projects", body={"name": proj_name, "description": DESC})
        if r is not None and not C.ok(r):
            fb = cfg["idmc"]["project_fallback_name"]
            print("  refused; creating %r and renaming through FRS" % fb)
            r = ctx.write("create project (fallback name)", "v3", "POST", "/public/core/v3/projects", body={"name": fb, "description": DESC})
            pid = (r.json({}) or {}).get("id") if r is not None else None
            if pid:
                ctx.write("rename project", "frs", "PATCH", "/frs/api/v1/Projects('%s')" % pid, body={"name": proj_name})
        proj = next((o for o in objs(ctx, "Project") if o.get("path") == proj_name), None)
    pid = proj["id"] if proj else "<projectId>"
    have = {o.get("path"): o["id"] for o in objs(ctx, "Folder")}
    folders = st.get("folders", {})
    for key, fname in cfg["idmc"]["folders"].items():
        path = "%s/%s" % (proj_name, fname)
        if path in have:
            folders[key] = have[path]
            print("folder %-28s %s" % (fname, have[path]))
            continue
        print("folder %-28s MISSING" % fname)
        if a.cmd == "build":
            r = ctx.write("create folder", "v3", "POST", "/public/core/v3/projects/%s/folders" % pid,
                          body={"name": fname, "description": FOLDER_DESC[key]})
            if C.ok(r):
                folders[key] = (r.json({}) or {}).get("id")
    rt = st.get("runtime", {})
    r = ctx.read("v2", "/api/v2/runtimeEnvironment")
    envs = {e.get("name"): e.get("id") for e in (r.json([]) if r is not None else []) if isinstance(e, dict)}
    for key, cname in (("main", "runtime_environment"), ("crm", "runtime_environment_crm")):
        want = cfg["idmc"][cname]
        rt[key] = envs.get(want, rt.get(key))
        print("runtime %-4s %-40s %s" % (key, want, rt[key] or ("(offline)" if ctx.offline else "NOT FOUND: fix config")))
    if not ctx.offline and (a.cmd == "show" or ctx.execute):
        st.update(project=pid if proj else None, folders=folders, runtime=rt)
        C.save_state(st)


if __name__ == "__main__":
    main()
