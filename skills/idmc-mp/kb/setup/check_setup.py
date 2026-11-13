#!/usr/bin/env python3
"""check_setup.py - offline readiness check for the Master IDMC KB on a new PC (makes no network call).

    python setup/check_setup.py                 # core checks + the IDMC login (IDMC_LOGIN.txt)
    python setup/check_setup.py --demo <name>   # also the keys one blueprint needs (from setup/.env.example)

Checks: Python version, IDMC_LOGIN.txt filled in (the IDMC login) and, for --demo, the blueprint's keys in the
credentials file outside the toolkit (values are never printed), the core library compiles, the Claude skill is
installed, docker / docker compose present (the stand-in stacks need them).
"""
import argparse
import os
import py_compile
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOGIN = ROOT / "IDMC_LOGIN.txt"
sys.path.insert(0, str(ROOT / "14 - Claude Working Methods & Tooling" / "Script Library"))
import idmc_login  # noqa: E402
DEFAULT_ENV = Path.home() / ".idmc_toolkit" / ".env"
OK, BAD, WARN = "  ok  ", "  FAIL", "  warn"


def env_file():
    return Path(os.environ.get("IDMC_CREDS_FILE") or DEFAULT_ENV).expanduser()


def read_env(p):
    out = {}
    if p.is_file():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
    return out


def keys_for(demo):
    """Key names listed under '# [<demo>]' (or '# [core]') in setup/.env.example."""
    keys, cur = [], None
    for line in (ROOT / "setup" / ".env.example").read_text(encoding="utf-8").splitlines():
        m = re.match(r"#\s*\[(.+?)\]", line)
        if m:
            cur = m.group(1).strip()
            continue
        m = re.match(r"(?:#\s*)?([A-Z][A-Z0-9_]+)=", line)   # "# KEY=" = a key shared with an earlier section
        if m and cur == demo:
            keys.append(m.group(1))
    return keys


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--demo", help="blueprint folder name under demos/ (e.g. retail_data_foundation)")
    a = ap.parse_args()
    fails = 0

    v = sys.version_info
    ok = v >= (3, 10)
    print(f"{OK if ok else BAD} python {v.major}.{v.minor} (need 3.10+)")
    fails += not ok

    login = idmc_login.login_values()
    p = env_file()
    if p.resolve() == LOGIN.resolve():
        p = DEFAULT_ENV
    if a.demo:
        if not p.is_file():
            print(f"{BAD} credentials file not found: {p}  (copy setup/.env.example there and fill in the "
                  f"[{a.demo}] keys)")
            fails += 1
        elif ROOT in p.resolve().parents:
            print(f"{BAD} credentials file is inside the toolkit ({p}); move it out so a re-zip can never leak it")
            fails += 1
        else:
            print(f"{OK} credentials file {p}")
    creds = idmc_login.read_kv(p) if p.is_file() else {}
    env = {**login, **creds, **{k: v for k, v in os.environ.items() if k.isupper() and v}}
    for k in idmc_login.KEYS:
        have = bool(env.get(k))
        src = ("set in the environment" if os.environ.get(k) else f"set in {p}" if k in creds
               else "set in IDMC_LOGIN.txt")
        print(f"{OK if have else BAD} [login] {k} {src if have else 'MISSING: fill it in ' + str(LOGIN)}")
        fails += not have
    if env.get("IDMC_LOGIN_HOST"):
        host = idmc_login.normalize_host(env["IDMC_LOGIN_HOST"])
        good = host.endswith(".informaticacloud.com") and host.count(".") == 2
        print(f"{OK if good else BAD} [login] login host {host or '(empty)'}" +
              ("" if good else ": paste the IDMC address from your browser, e.g. https://usw5.dm-us.informaticacloud.com/..."))
        fails += not good
    for section in [a.demo] if a.demo else []:
        for k in keys_for(section):
            have = bool(env.get(k))
            print(f"{OK if have else BAD} [{section}] {k} {'set' if have else 'MISSING'}")
            fails += not have

    bad = []
    for f in sorted((ROOT / "14 - Claude Working Methods & Tooling" / "Script Library").glob("*.py")):
        try:
            py_compile.compile(str(f), doraise=True, cfile=os.path.join(tempfile.gettempdir(), "idmc_toolkit_check.pyc"))
        except py_compile.PyCompileError as e:
            bad.append(f"{f.name}: {e.msg}")
    print(f"{OK if not bad else BAD} core library compiles" + ("" if not bad else ": " + "; ".join(bad)))
    fails += bool(bad)

    sk = Path(__file__).resolve().parents[2] / "SKILL.md"           # kb/setup/ -> the idmc-mp skill folder
    print(f"{OK if sk.is_file() else WARN} Claude skill idmc-mp " +
          ("present (this folder)" if sk.is_file() else "SKILL.md not found next to kb/: unzip the whole idmc-mp folder"))

    if shutil.which("docker"):
        r = subprocess.run(["docker", "compose", "version"], capture_output=True, text=True)
        print(f"{OK if r.returncode == 0 else WARN} docker compose " + (r.stdout.strip() or "missing"))
    else:
        print(f"{WARN} docker not found (needed only for the stand-in stacks under demos/*/infra)")

    print("\nREADY" if not fails else f"\n{fails} problem(s) to fix")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
