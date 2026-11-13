#!/usr/bin/env python3
"""check_login.py - log in once and print your org (name, orgIdV3, pod).

    python check_login.py

First run: if you have no login file yet, this creates ~/.idmc_toolkit/IDMC_LOGIN.txt from the template, tells
you to fill in its 3 lines, and stops (no login attempt). The same as the Script Library's
`idmc_session.py whoami`, which does the work (one attempt, lockout guard, cached session). Extra arguments pass
through, e.g. --expect-org <orgIdV3>.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

KB = Path(__file__).resolve().parent
LIB = KB / "14 - Claude Working Methods & Tooling" / "Script Library"
sys.path.insert(0, str(LIB))
import idmc_login as L  # noqa: E402

if not os.environ.get("IDMC_CREDS_FILE") and not all(os.environ.get(k) for k in L.KEYS):
    f = L.login_file()
    if f is None:
        f = L.HOME_FILE
        f.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(KB / "setup" / "IDMC_LOGIN.template.txt", f)
        try:
            os.chmod(f, 0o600)
        except OSError:
            pass
        print(f"Created {f}\nFill in IDMC_USER, IDMC_PASS and IDMC_LOGIN_HOST there, save, then run this again.")
        sys.exit(2)
    if not all(L.login_values().get(k) for k in L.KEYS):
        print(f"{f} is not filled in yet: set IDMC_USER, IDMC_PASS and IDMC_LOGIN_HOST, then run this again.")
        sys.exit(2)
sys.exit(subprocess.call([sys.executable, str(LIB / "idmc_session.py"), "whoami", *sys.argv[1:]]))
