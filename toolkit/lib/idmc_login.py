#!/usr/bin/env python3
"""idmc_login.py - finds and reads IDMC_LOGIN.txt, the one file a user fills in to connect. stdlib only.

IDMC_LOGIN.txt lives in ~/.idmc_toolkit/ and holds three KEY=value lines: IDMC_USER, IDMC_PASS, IDMC_LOGIN_HOST.
Every loader in the toolkit (toolkit/lib, toolkit/mapgen, the demos, toolkit/setup/check_setup.py) reads it, so no
environment variable is needed. Precedence: environment variables first, then the file IDMC_CREDS_FILE names (a
per-org file outside the plugin), then ~/.idmc_toolkit/IDMC_LOGIN.txt, then (git-clone legacy only) an IDMC_LOGIN.txt at
the repository root or in toolkit/; empty values are ignored. The home file always wins over a plugin-local one.

  login_file()        the IDMC_LOGIN.txt path (~/.idmc_toolkit/ first, then the legacy repo-root / toolkit/ copy), or None
  read_kv(path)       KEY=value lines -> dict (comments, blanks and empty values dropped; quotes stripped)
  login_values()      the non-empty values of IDMC_LOGIN.txt ({} when the file is absent or blank)
  normalize_host(h)   a pasted browser address or pod host -> <domain>.informaticacloud.com
  is_login_host(h)    True when h is exactly <domain>.informaticacloud.com (the only host credentials may go to)
"""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

FILE_NAME = "IDMC_LOGIN.txt"
KEYS = ("IDMC_USER", "IDMC_PASS", "IDMC_LOGIN_HOST")
HOME_FILE = Path.home() / ".idmc_toolkit" / FILE_NAME   # plugin installs: keep the login outside the plugin
_HERE = Path(__file__).resolve()
LEGACY_FILES = (_HERE.parents[2] / FILE_NAME, _HERE.parents[1] / FILE_NAME)   # git-clone legacy: repo root, toolkit/
_LOGIN_HOST_RE = re.compile(r"[a-z0-9-]+\.informaticacloud\.com")


def login_file():
    """~/.idmc_toolkit/IDMC_LOGIN.txt first; a repo-root (or toolkit/) copy is only a git-clone legacy fallback."""
    for f in (HOME_FILE,) + LEGACY_FILES:
        if f.is_file():
            return f
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


def is_login_host(h):
    """True only for a bare <domain>.informaticacloud.com host: credentials are never sent anywhere else."""
    return bool(_LOGIN_HOST_RE.fullmatch(h or ""))
