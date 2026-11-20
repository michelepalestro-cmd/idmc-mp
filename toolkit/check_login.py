#!/usr/bin/env python3
"""check_login.py - connect to your IDMC org once and print which org it is.

    python3 toolkit/check_login.py            first run: creates your login file and tells you what to fill in.
                                              later runs: log in ONCE and print your org.
    python3 toolkit/check_login.py --setup    asks for the 3 values right here in the terminal (the password is
                                              hidden while you type), saves them, then logs in once.
    python3 toolkit/check_login.py --where    prints where your login file is.
    python3 toolkit/check_login.py --json     prints the full technical answer instead of the short summary.

Windows: use `python` or `py` instead of `python3`.

Your login file is ~/.idmc_toolkit/IDMC_LOGIN.txt, in your home folder, never inside the plugin. Before any login
attempt this script checks the three values on your computer, without the network, because every rejected login
counts towards locking the account. It makes at most one login attempt per run and never retries. Other arguments
(for example --expect-org <orgIdV3>) pass through to `toolkit/lib/idmc_session.py whoami`, which does the login.
"""
import argparse
import getpass
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

KB = Path(__file__).resolve().parent
LIB = KB / "lib"
sys.path.insert(0, str(LIB))
import idmc_login as L  # noqa: E402

TEMPLATE = KB / "setup" / "IDMC_LOGIN.template.txt"
PLACEHOLDERS = {"", "changeme", "change_me", "password", "yourpassword", "your-password", "your_password", "xxx",
                "jane.doe@example.com", "user", "username", "your-user", "your_user"}


def say(text=""):
    print(text, flush=True)


def open_hint(f):
    """The command that opens the login file in a plain text editor on this computer."""
    system = platform.system()
    if system == "Windows":
        return f'notepad "{f}"'
    if system == "Darwin":
        return f'open -e "{f}"'
    return f'nano "{f}"'


def write_login(f, user, password, host):
    """Write the template with the three values filled in, readable only by you (mode 600)."""
    lines = []
    for line in TEMPLATE.read_text(encoding="utf-8").splitlines():
        if line.startswith("IDMC_USER="):
            line = "IDMC_USER=" + user
        elif line.startswith("IDMC_PASS="):
            line = "IDMC_PASS=" + password
        elif line.startswith("IDMC_LOGIN_HOST="):
            line = "IDMC_LOGIN_HOST=" + host
        lines.append(line)
    f.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(f), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as out:
        out.write("\n".join(lines) + "\n")
    try:
        os.chmod(f, 0o600)
    except OSError:
        pass


def create_from_template(f):
    f.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(TEMPLATE, f)
    try:
        os.chmod(f, 0o600)
    except OSError:
        pass


def problems(values):
    """Offline checks that catch the mistakes that would waste a login attempt. Returns plain-English problems."""
    out = []
    user = values.get("IDMC_USER", "")
    pw = values.get("IDMC_PASS", "")
    raw_host = values.get("IDMC_LOGIN_HOST", "")
    host = L.normalize_host(raw_host)
    if not user:
        out.append("IDMC_USER is empty. Put the user name you sign in to IDMC with.")
    elif user.lower() in PLACEHOLDERS or "<" in user or " " in user:
        out.append("IDMC_USER still looks like the example or has a space in it. Put your real IDMC user name.")
    if not pw:
        out.append("IDMC_PASS is empty. Put the password of that user.")
    elif pw.lower() in PLACEHOLDERS or pw.startswith("<"):
        out.append("IDMC_PASS still looks like a placeholder. Put the real password.")
    elif pw != pw.strip():
        out.append("IDMC_PASS starts or ends with a space. Remove it (unless your password really has one).")
    if not raw_host:
        out.append("IDMC_LOGIN_HOST is empty. Sign in to IDMC in your browser and paste the address bar here.")
    elif not (host.endswith(".informaticacloud.com") and host.count(".") == 2):
        out.append(f"IDMC_LOGIN_HOST '{raw_host}' is not an IDMC address. It should look like "
                   "https://usw5.dm-us.informaticacloud.com/cloudUX/home (copy it from your browser after you sign in).")
    return out


def ask(prompt, secret=False):
    try:
        return (getpass.getpass(prompt) if secret else input(prompt)).strip()
    except (EOFError, KeyboardInterrupt):
        say("\nStopped. Nothing was saved.")
        sys.exit(130)


def guided_setup(f):
    if not sys.stdin.isatty():
        say("--setup needs a terminal you can type in. Open a terminal window and run:")
        say(f"  {Path(sys.executable).name} \"{Path(__file__).resolve()}\" --setup")
        say(f"Or open your login file in a text editor and fill it in:\n  {open_hint(f)}")
        sys.exit(2)
    say("Let's connect to IDMC. You will type 3 things. Nothing is sent anywhere until the end.\n")
    say("1) Sign in to IDMC in your web browser. Copy the whole address from the top of the browser.")
    say("   It looks like https://usw5.dm-us.informaticacloud.com/cloudUX/home")
    host = ask("   Paste it here and press Enter: ")
    say("\n2) Your IDMC user name (the one you type on the IDMC sign-in page).")
    user = ask("   User name: ")
    say("\n3) The password for that user. You will NOT see it while you type. That is normal.")
    pw = ask("   Password: ", secret=True)
    values = {"IDMC_USER": user, "IDMC_PASS": pw, "IDMC_LOGIN_HOST": host}
    bad = problems(values)
    if bad:
        say("\nSomething does not look right, so nothing was saved and no login was tried:")
        for b in bad:
            say("  - " + b)
        say("Run --setup again when you are ready.")
        sys.exit(2)
    write_login(f, user, pw, host)
    say(f"\nSaved to {f} (only you can read it).")


LOCKED = ("Your IDMC account is LOCKED (too many wrong logins).\n"
          "  1. Do not try again yet: every try can restart the lock.\n"
          "  2. Ask an IDMC admin to unlock you (Administrator > Users > your user > Unlock), or use\n"
          "     'Forgot your password?' on the IDMC sign-in page. On a trial you are usually the only admin:\n"
          "     use 'Forgot your password?', or open a case with Informatica support.\n"
          "  3. Sign in once in your browser to prove the password works, put that password in your login file,\n"
          "     then run this again. If the password did not change, also delete the .block.json pause file\n"
          "     (run this once more and it names the file).")
WRONG = ("IDMC said the user name or password is wrong. The usual reasons, in order:\n"
         "  1. IDMC_LOGIN_HOST points at the wrong region. Sign in in your browser and paste that exact address.\n"
         "  2. The user name is not exactly what you type on the IDMC sign-in page (it may not be your e-mail).\n"
         "  3. You sign in with your company's single sign-on (SSO) button. Those users have no IDMC password.\n"
         "     Ask your IDMC admin for a 'native' IDMC user with a password, for example a service user.\n"
         "     If you are the admin (a trial): Administrator > Users > Add User, choose a native IDMC user,\n"
         "     set its password, and put that user in your login file.\n"
         "  4. The password changed, expired, or must be changed at first sign-in. Sign in once in the browser.\n"
         "  Fix the file and run this again. Do not try several times in a row: wrong logins lock the account.")
PAUSED = ("Logins are paused on purpose after a rejected login, so the account does not get locked.\n"
          "  No login was sent this time.\n"
          "  1. Sign in in your browser with the same user and password to make sure they work.\n"
          "  2. Fix your login file. Changing the user, the password or the address lifts the pause by itself.\n"
          "  3. If the values were already right (for example an admin unlocked you and the password is the\n"
          "     same), delete the .block.json file named above, then run this once.")
WRONG_HOST = ("That address is not an IDMC sign-in address. Sign in to IDMC in your browser and paste the address\n"
              "  bar into IDMC_LOGIN_HOST exactly as it is.")
CERT = ("Your network is inspecting secure (HTTPS) traffic, usually a company proxy or VPN. Ask IT for the company\n"
        "  certificate bundle and set SSL_CERT_FILE to it, or try from a network without the proxy.")
OFFLINE = ("Your computer could not reach IDMC. Check your internet connection, VPN and proxy, then run this again.\n"
           "  This was not a wrong password, so nothing was blocked.")
BUSY = "IDMC was busy or had a temporary error. Wait a few minutes and run this again. Nothing was blocked."
LEGEND = "(IDS_085 = bad credentials or wrong domain; IDS_086 = account locked)"


def explain_failure(text):
    t = text.replace(LEGEND, "")                     # the library's legend names both codes: ignore it
    helps = []
    if "login BLOCKED" in t:
        helps.append(PAUSED)                         # paused: the earlier reason is history, not a new failure
    elif re.search(r"IDS_086|account is locked", t, re.I):
        helps.append(LOCKED)
    elif re.search(r"IDS_085|UI_10000|not valid", t, re.I):
        helps.append(WRONG)
    if "wrong login host?" in t:
        helps.append(WRONG_HOST)
    if re.search(r"CERTIFICATE_VERIFY_FAILED|SSL", t):
        helps.append(CERT)
    elif re.search(r"login HTTP -1|timed out|Name or service not known|getaddrinfo|Connection refused|"
                   r"Network is unreachable", t, re.I):
        helps.append(OFFLINE)
    elif re.search(r"login HTTP (5\d\d|429)", t):
        helps.append(BUSY)
    if not helps:
        helps.append("The login did not work. Read the message above, check your login file, and run this once more.\n"
                     "  Stuck? In Claude Code run /idmc-mp:fix-error and paste the message (never your password).")
    for h in helps:
        say("\nWHAT THIS MEANS\n  " + h)


def summarize(w):
    server = w.get("serverUrl") or ""
    pod = (re.match(r"https?://([^.]+)\.", server) or [None, "?"])[1]
    say("CONNECTED to IDMC")
    say(f"  Org name : {w.get('orgName') or '?'}")
    say(f"  Org id   : {w.get('orgIdV3') or '?'}   (writes ask for this: --expect-org <org id>)")
    say(f"  Pod      : {pod}")
    say(f"  User     : {w.get('user') or '?'}")
    say(f"  Base URL : {server or '?'}")
    for k in ("warning", "mismatch"):
        if w.get(k):
            say(f"  NOTE     : {w[k]}")
    say("\nNext, in Claude Code: /idmc-mp:health-check")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--setup", action="store_true", help="type the 3 values here (password hidden) and save them")
    ap.add_argument("--where", action="store_true", help="print where your login file is and stop")
    ap.add_argument("--json", action="store_true", help="print the full technical answer")
    a, rest = ap.parse_known_args()

    explicit = os.environ.get("IDMC_CREDS_FILE") or all(os.environ.get(k) for k in L.KEYS)
    f = L.login_file() or L.HOME_FILE

    if a.where:
        say(str(Path(os.environ["IDMC_CREDS_FILE"]).expanduser()) if os.environ.get("IDMC_CREDS_FILE") else str(f))
        return 0
    if a.setup:
        if explicit:
            say("Your login comes from IDMC_CREDS_FILE or environment variables, not from the login file. "
                "Unset them first if you want to use --setup.")
            return 2
        guided_setup(f)
    elif not explicit:
        if not f.is_file():
            create_from_template(f)
            say(f"Created your login file:\n  {f}\n")
            say("Fill in the 3 lines at the bottom of that file, save it, then run this again.")
            say("  IDMC_USER        your IDMC user name")
            say("  IDMC_PASS        its password")
            say("  IDMC_LOGIN_HOST  sign in to IDMC in your browser and paste the address bar")
            say(f"\nOpen it with:\n  {open_hint(f)}")
            say("\nEasier: let this script ask you instead (run it in a terminal, the password stays hidden):")
            say(f"  {Path(sys.executable).name} \"{Path(__file__).resolve()}\" --setup")
            return 2

    values = {**(L.login_values() if not explicit else {}),
              **(L.read_kv(os.environ["IDMC_CREDS_FILE"]) if os.environ.get("IDMC_CREDS_FILE") and
                 Path(os.environ["IDMC_CREDS_FILE"]).expanduser().is_file() else {}),
              **{k: os.environ[k] for k in L.KEYS if os.environ.get(k)}}
    bad = problems(values)
    if bad:
        say(f"Your login is not ready yet ({os.environ.get('IDMC_CREDS_FILE') or f}). No login was tried:")
        for b in bad:
            say("  - " + b)
        if not explicit:
            say(f"\nOpen the file with:\n  {open_hint(f)}\nor run this script with --setup.")
        return 2

    say("Logging in to IDMC (one attempt)...")
    r = subprocess.run([sys.executable, str(LIB / "idmc_session.py"), "whoami", *rest],
                       capture_output=True, text=True)
    text = (r.stdout or "") + (r.stderr or "")
    if r.returncode != 0:
        say(text.strip())
        explain_failure(text)
        return r.returncode or 1
    if a.json or rest:
        say(r.stdout.strip())
        if r.stderr.strip():
            say(r.stderr.strip())
        return 0
    try:
        start = r.stdout.index("{")
        w = json.loads(r.stdout[start:])
    except ValueError:
        say(text.strip())
        return 0
    summarize(w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
