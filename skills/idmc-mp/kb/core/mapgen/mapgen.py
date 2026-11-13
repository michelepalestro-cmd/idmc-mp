#!/usr/bin/env python3
"""mapgen: JSON mapping spec -> real IDMC CDI mapping (+ mapping task, + run). Python 3.10+, standard library only.

  python mapgen.py build   spec.json [--profile p] [--out dir]      compile + package, nothing sent
  python mapgen.py lint    spec.json [--profile p] [--allow-live]   static checks (known runtime traps)
  python mapgen.py whoami  [--profile p]                            login (cached) + org assertion
  python mapgen.py resolve [--profile p] [--write]                  fill profile ids BY NAME (read-only)
  python mapgen.py import  pkg.zip [--mode REUSE|OVERWRITE] [--no-sc] [--dry-run]
  python mapgen.py task    <mapping name> [--folder Project/Folder] [--name mt_x] [--dry-run]
  python mapgen.py run     <task id | task name> [--folder Project/Folder] [--no-wait] [--dry-run]
  python mapgen.py deploy  spec.json [--run] [--mode ...] [--allow-live] [--force] [--dry-run]
  python mapgen.py log     <activity id> [--out file]                session log of one run
  python mapgen.py jobs                                              job-ledger count (budget guard)

Profile: --profile (a relative path is relative to the current directory), else -- for build, lint and deploy --
the spec's own "profile" key (relative to the spec file), else $MAPGEN_PROFILE when it is non-empty (an empty value
counts as unset; a non-empty one is the profile path, '~' = the home folder, relative to the current directory, and
the file must exist: a missing one is an error, never skipped), else ./profile.json, else local/profile.local.json
next to this file (these two only when the file exists). jobs reads no profile.
(Python 3.10+: idmc_mapgen/nodes/__init__.py uses sys.stdlib_module_names.)
Credentials come from the environment (see profile.example.json "auth"), never from the profile itself.
Exit codes: 0 ok, 1 failure (import/run/lint errors), 2 usage, spec or profile problem.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

SPEC_CMDS = ("build", "lint", "deploy")     # these resolve the profile per spec (the spec's own key first)
NO_PROFILE_CMDS = ("jobs",)                 # these use no profile: a missing $MAPGEN_PROFILE must not stop them


def _fallback_profile():
    """The profile when neither --profile nor (build / lint / deploy) the spec's own "profile" key names one:
    $MAPGEN_PROFILE (set = meant: a missing file is an error, never skipped), else ./profile.json, else
    local/profile.local.json next to this file. An absolute path, or None."""
    env = os.environ.get("MAPGEN_PROFILE")
    if env:
        return os.path.abspath(os.path.expanduser(env))
    for p in ("profile.json", os.path.join(HERE, "local", "profile.local.json")):
        if os.path.exists(p):
            return os.path.abspath(p)
    return None


def _profile_path(arg):
    """The profile path of a command that takes no spec: --profile, else the fallbacks."""
    return os.path.abspath(os.path.expanduser(arg)) if arg else _fallback_profile()


def _load_profile(arg):
    """(profile, path) of a command that takes no spec. SpecError (exit 2) when it cannot be loaded."""
    p = _profile_path(arg)
    if not p:
        return {}, None
    from idmc_mapgen.spec import load_profile
    return load_profile(p), p


def _need(modname):
    try:
        return __import__("idmc_mapgen." + modname, fromlist=[modname])
    except ImportError as e:
        raise SystemExit("idmc_mapgen.%s is not available in this build (%s)" % (modname, e))


def _client(prof):
    from idmc_mapgen.client import Client
    return Client(prof)


def _folder(prof, path, client=None):
    """{path, guid} for --folder (default: the profile folder)."""
    f = prof.get("folder") or {}
    default = "%s/%s" % (f.get("project"), f.get("name")) if f else None
    path = path or default
    if not path:
        raise SystemExit("no folder: pass --folder Project/Folder or set profile.folder")
    if path == default and f.get("guid"):
        return {"path": path, "guid": f["guid"]}
    for k, ff in (prof.get("folders") or {}).items():
        if "%s/%s" % (ff.get("project"), ff.get("name")) == path and ff.get("guid"):
            return {"path": path, "guid": ff["guid"]}
    if client is None:
        return {"path": path, "guid": None}
    from idmc_mapgen.resolve import folder_ids
    return {"path": path, "guid": folder_ids(client, path)[1]}


def _print(obj):
    print(json.dumps(obj, indent=1, default=str))


def _mapplet_warning(spec):
    """The warning for a DMAPPLET spec whose assets / projectJson / folderJson / packageOverrides its package ignores
    (nodes.mapplet.package_ignored_message, lint's MPLT_PKG_IGNORED), or None."""
    if spec.get("documentType") != "DMAPPLET":
        return None
    try:
        from idmc_mapgen.nodes.mapplet import package_ignored_message
    except ImportError:
        return None
    return package_ignored_message(spec)


def cmd_build(a, profile, default):
    specmod, compiler, packager = _need("spec"), _need("compile"), _need("package")
    s, prof = specmod.load_spec_and_profile(a.spec, profile=profile, default_profile=default)
    imf = compiler.build(s)
    out = a.out or os.path.expanduser(prof.get("workDir") or "build")
    os.makedirs(out, exist_ok=True)
    stem = packager.safe_file_name(s["name"])    # 'm_a:b.pkg.zip' would land in an NTFS alternate data stream
    pkg = os.path.join(out, stem + ".pkg.zip")
    packager.package(s, imf, pkg)                # a DMAPPLET spec gets its DMAPPLET package, as deploy imports it
    with open(os.path.join(out, stem + ".imf.json"), "w", encoding="utf-8") as f:
        json.dump(imf, f, indent=1)
    warn = _mapplet_warning(s)
    if warn:
        print("WARN: %s" % warn, file=sys.stderr)
    print("package %s guid %s transformations %d links %d" % (pkg, s["guid"], len(imf["content"]["transformations"]),
                                                            len(imf["content"]["links"])))
    return 0


def cmd_lint(a, profile, default):
    lintmod = _need("lint")
    argv = ([a.spec] + (["--profile", profile] if profile else []) + (["--allow-live"] if a.allow_live else [])
            + (["--json"] if a.json else []))
    return lintmod.main(argv, default_profile=default)      # exit 1 on any ERROR, 2 when the spec cannot be read


def cmd_whoami(a, prof):
    c = _client(prof)
    who = c.whoami()
    exp = (prof.get("org") or {}).get("v2Id")
    who["expected"] = exp
    who["match"] = (exp == who["id"]) if exp else None
    _print(who)
    return 0 if who["match"] in (True, None) else 1


def cmd_resolve(a, prof, ppath):
    from idmc_mapgen.resolve import resolve
    new, changes, problems = resolve(_client(prof), prof)
    for k, old, nv in changes:
        print("%-40s %s -> %s" % (k, old, nv))
    for p in problems:
        print("PROBLEM", p)
    if not changes and not problems:
        print("profile matches the org (no changes)")
    if a.write and ppath and not problems:
        with open(ppath, "w", encoding="utf-8") as f:
            json.dump(new, f, indent=1)
        print("wrote", ppath)
    return 1 if problems else 0


def cmd_import(a, prof):
    from idmc_mapgen import deploy as dp, lock
    data = open(a.pkg, "rb").read()
    if a.dry_run:
        from idmc_mapgen import sc
        print("dry run: would import %s (%d bytes, mode %s); objects: %s" % (a.pkg, len(data), a.mode, sc.package_objects(data)))
        return 0
    c = _client(prof)
    c.assert_org()
    with lock.live_lock("cli-import"):
        r = dp.import_package(c, data, a.mode, source_control=not a.no_sc,
                              checkin_new=(prof.get("sourceControl") or {}).get("checkinNew", False))
    _print({k: v for k, v in r.items() if k != "log"})
    return 0


def cmd_task(a, prof):
    from idmc_mapgen import deploy as dp, lock
    c = _client(prof)
    c.assert_org()
    f = _folder(prof, a.folder, c)
    m = dp.find_mapping(c, a.mapping, f["path"])
    if not m:
        print("no mapping %s in %s" % (a.mapping, f["path"]))
        return 1
    name = a.name or dp.task_name_for(a.mapping)
    re_id = (prof.get("runtimeEnvironment") or {}).get("id")
    if a.dry_run:
        print("dry run: would ensure task %s -> mapping %s (%s) in %s (runtime %s)" % (name, m["id"], m["frsGuid"], f["path"], re_id))
        return 0
    with lock.live_lock("cli-task"):
        _print(dp.ensure_task(c, name, m["id"], re_id, f, a.description or ""))
    return 0


def cmd_run(a, prof):
    from idmc_mapgen import deploy as dp, lock
    c = _client(prof)
    c.assert_org()
    tid = a.task
    if not (len(tid) == 20 and tid.isalnum() and tid.upper() == tid):
        t = dp.find_task(c, tid, _folder(prof, a.folder, c)["path"])
        if not t:
            print("no task %s in the folder" % tid)
            return 1
        tid = t["id"]
    if a.dry_run:
        print("dry run: would start task %s (jobs used so far: %d)" % (tid, lock.jobs_used()))
        return 0
    with lock.live_lock("cli-run"):
        r = dp.run_task(c, tid, owner="cli", task_name=a.task, quiet=(prof.get("guards") or {}).get("busyTaskPrefixes"),
                        timeout_s=10 if a.no_wait else 3600)
    _print(r)
    return 0 if r.get("state") == 1 else 1


def cmd_deploy(a, profile, default):
    from idmc_mapgen import deploy as dp
    r = dp.deploy(a.spec, profile, run=a.run, dry_run=a.dry_run, mode=a.mode, allow_live=a.allow_live,
                  force_lint=a.force_lint, owner="cli-deploy", default_profile=default)
    _print(r)
    run = r.get("run")
    return 0 if (run is None or run.get("state") == 1) else 1


def cmd_log(a, prof):
    from idmc_mapgen import deploy as dp
    txt = dp.session_log(_client(prof), a.activity)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(txt)
        print("wrote", a.out, len(txt), "chars")
    else:
        print(txt)
    return 0


def cmd_jobs(a, prof):
    from idmc_mapgen import lock
    print("jobs recorded:", lock.jobs_used(), "| ledger:", lock.LEDGER)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="mapgen", description=__doc__.split("\n")[0])
    ap.add_argument("--profile")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("build"); p.add_argument("spec"); p.add_argument("--out")
    p = sub.add_parser("lint"); p.add_argument("spec"); p.add_argument("--allow-live", action="store_true"); p.add_argument("--json", action="store_true")
    sub.add_parser("whoami")
    p = sub.add_parser("resolve"); p.add_argument("--write", action="store_true")
    p = sub.add_parser("import"); p.add_argument("pkg"); p.add_argument("--mode", default="REUSE", choices=["REUSE", "OVERWRITE"])
    p.add_argument("--no-sc", action="store_true"); p.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("task"); p.add_argument("mapping"); p.add_argument("--folder"); p.add_argument("--name")
    p.add_argument("--description"); p.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("run"); p.add_argument("task"); p.add_argument("--folder"); p.add_argument("--no-wait", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("deploy"); p.add_argument("spec"); p.add_argument("--run", action="store_true")
    p.add_argument("--mode", choices=["REUSE", "OVERWRITE"]); p.add_argument("--allow-live", action="store_true")
    p.add_argument("--force-lint", "--force", dest="force_lint", action="store_true"); p.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("log"); p.add_argument("activity"); p.add_argument("--out")
    sub.add_parser("jobs")
    for sp in sub.choices.values():
        sp.add_argument("--profile", default=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    if not a.cmd:
        print(__doc__)
        return 2
    explicit = getattr(a, "profile", None) or None
    try:
        if a.cmd in SPEC_CMDS:          # explicit --profile > the spec's own "profile" key > the fallbacks
            return globals()["cmd_" + a.cmd](a, explicit, None if explicit else _fallback_profile())
        if a.cmd in NO_PROFILE_CMDS:
            return globals()["cmd_" + a.cmd](a, {})
        prof, ppath = _load_profile(explicit)
        if a.cmd == "resolve":
            return cmd_resolve(a, prof, ppath)
        return globals()["cmd_" + a.cmd](a, prof)
    except SystemExit:
        raise
    except Exception as e:
        name = type(e).__name__
        if name in ("SpecError",):
            print("SPEC ERROR: %s" % e, file=sys.stderr)
            return 2
        if name in ("LoginError", "OrgMismatch", "DeployError", "TimeoutError"):
            print("%s: %s" % (name, e), file=sys.stderr)
            return 1
        raise


if __name__ == "__main__":
    sys.exit(main())
