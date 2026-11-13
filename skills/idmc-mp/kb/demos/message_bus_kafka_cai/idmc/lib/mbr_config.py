"""mbr_config.py - config + state helpers shared by the blueprint's scripts (standard library only).

config.json (copy of config.example.json, filled in) holds names and ids; state/ holds what the build created
(ids.json, frs.json, guids.json). Neither holds a secret. Secrets come from the environment, IDMC_LOGIN.txt (toolkit
root, the IDMC login) or the toolkit .env (IDMC_CREDS_FILE), and only by key name (env_value())."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

BP = Path(__file__).resolve().parents[2]          # demos/message_bus_kafka_cai
TOOLKIT = BP.parents[1]                            # the toolkit root
CORE = TOOLKIT / "14 - Claude Working Methods & Tooling" / "Script Library"
STATE = BP / "state"
BUILD = BP / "build"


def use_core():
    """Put the Script Library (the core library) on sys.path (conventions rule 3) and return its folder."""
    if str(CORE) not in sys.path:
        sys.path.insert(0, str(CORE))
    return CORE


def load(path=None, example_ok=False):
    p = Path(path) if path else BP / "config.json"
    if not p.exists():
        if example_ok:
            p = BP / "config.example.json"
            print(f"[config] {BP.name}/config.json not found: using config.example.json (placeholders, offline use only)")
        else:
            sys.exit(f"config not found: {p} (copy config.example.json to config.json and fill it in)")
    return json.loads(p.read_text(encoding="utf-8"))


def placeholders(cfg, keys):
    """Return the dotted keys whose value is still a <placeholder>."""
    out = []
    for k in keys:
        v = cfg
        for part in k.split("."):
            v = v.get(part) if isinstance(v, dict) else None
        if v is None or (isinstance(v, str) and v.startswith("<")):
            out.append(k)
    return out


def state_get(name, default=None):
    p = STATE / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def state_put(name, obj):
    STATE.mkdir(parents=True, exist_ok=True)
    p = STATE / name
    p.write_text(json.dumps(obj, indent=1, sort_keys=True), encoding="utf-8")
    return p


def env_value(key):
    """A value from the environment, IDMC_LOGIN.txt or the toolkit .env file (IDMC_CREDS_FILE, default
    ~/.idmc_toolkit/.env). Never print the result."""
    if os.environ.get(key):
        return os.environ[key]
    use_core()
    import idmc_login as L
    f = Path(os.environ.get("IDMC_CREDS_FILE") or (Path.home() / ".idmc_toolkit" / ".env")).expanduser()
    v = (L.read_kv(f) if f.is_file() else {}).get(key) or L.login_values().get(key)
    return L.normalize_host(v) if v and key == "IDMC_LOGIN_HOST" else v
