#!/usr/bin/env python3
"""idmc_login.py - finds and reads IDMC_LOGIN.txt, the one file a user fills in to connect. stdlib only.

IDMC_LOGIN.txt sits at the toolkit root and holds three KEY=value lines: IDMC_USER, IDMC_PASS, IDMC_LOGIN_HOST.
Every loader in the toolkit (core/idmc, core/mapgen, the blueprints, setup/check_setup.py) reads it, so no
environment variable is needed. An explicit source wins over it: environment variables first, then the file
IDMC_CREDS_FILE names (a per-org file outside the KB), then IDMC_LOGIN.txt; empty values are ignored.

  login_file()        the IDMC_LOGIN.txt path (searched upward from this file, then ~/.idmc_toolkit/), or None
  read_kv(path)       KEY=value lines -> dict (comments, blanks and empty values dropped; quotes stripped)
  login_values()      the non-empty values of IDMC_LOGIN.txt ({} when the file is absent or blank)
  normalize_host(h)   a pasted browser address or pod host -> <domain>.informaticacloud.com
"""
from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

FILE_NAME = "IDMC_LOGIN.txt"
KEYS = ("IDMC_USER", "IDMC_PASS", "IDMC_LOGIN_HOST")
HOME_FILE = Path.home() / ".idmc_toolkit" / FILE_NAME   # plugin installs: keep the login outside the plugin


def login_file():
    """The toolkit root holds it; the KB's Script Library copy of this module sits one level deeper, so search up."""
    for d in list(Path(__file__).resolve().parents)[:4]:
        if (d / FILE_NAME).is_file():
            return d / FILE_NAME
    if HOME_FILE.is_file():
        return HOME_FILE
    return None


def read_kv(path):
    out = {}
    for line in Path(path).expanduser().read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line.startswith("export "):
            line = line[7:].lstrip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            v = v.strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
                v = v[1:-1]
            if v:
                out[k.strip()] = v
    return out


def login_values():
    f = login_file()
    return read_kv(f) if f else {}


def normalize_host(h):
    """'https://usw5.dm-us.informaticacloud.com/cloudUX/home' -> 'dm-us.informaticacloud.com'. A pod label
    (usw5, usw5-cai, ...) is dropped: logins go to the domain host, and a pod host answers 404."""
    h = (h or "").strip()
    host = (urlparse(h if "//" in h else "//" + h).hostname or "").lower()
    labels = host.split(".")
    if host.endswith(".informaticacloud.com") and len(labels) > 3:
        host = ".".join(labels[-3:])
    return host
