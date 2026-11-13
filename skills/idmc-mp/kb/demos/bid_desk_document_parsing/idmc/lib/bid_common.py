"""bid_common.py - shared helpers for the Bid Desk blueprint scripts (stdlib only).

- Locates the KB's core library (the Script Library) relative to this file and imports idmc_http / idmc_session.
- Loads config.json (falls back to config.example.json with a warning) and state/ids.json (ids the build creates).
- Reads credentials from the environment, IDMC_LOGIN.txt (toolkit root) or the file named by IDMC_CREDS_FILE.
  Values are never printed.
- Renders ${a.b.c} placeholders from the config and ${state:key} from state/ids.json inside templates.
- Ctx: dry run by default. A dry run with --offline (or with no IDMC credentials) never logs in and never sends
  anything; it prints each request it would make. --execute needs --expect-org <orgIdV3> (the core WriteGate).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

BP = Path(__file__).resolve().parents[2]            # demos/bid_desk_document_parsing
TOOLKIT = BP.parents[1]                             # the toolkit root
CORE = TOOLKIT / "14 - Claude Working Methods & Tooling" / "Script Library"
sys.path.insert(0, str(CORE))
import idmc_http as H  # noqa: E402
import idmc_login as L  # noqa: E402

TEMPLATES = BP / "idmc" / "templates"
STATE_DIR = BP / "state"
STATE = STATE_DIR / "ids.json"
_PH = re.compile(r"\$\{([A-Za-z0-9_:.\-]+)\}")


class Offline(RuntimeError):
    """raised when a step needs a live read but the run is offline"""


# ------------------------------------------------------------------ config, state, env
def load_config(path=None):
    p = Path(path) if path else BP / "config.json"
    if not p.exists():
        p = BP / "config.example.json"
        print(f"[config] config.json not found: using {p.name} (placeholders only; copy it to config.json and fill it in)",
              flush=True)
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def state():
    if STATE.exists():
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(st):
    STATE_DIR.mkdir(exist_ok=True)
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(st, f, indent=1, sort_keys=True)
    print(f"[state] ids -> {STATE.relative_to(BP)}")


def put_state(key, value):
    st = state()
    cur = st
    parts = key.split(".")
    for k in parts[:-1]:
        cur = cur.setdefault(k, {})
    cur[parts[-1]] = value
    save_state(st)


def _creds_file():
    """IDMC_LOGIN.txt values, overlaid by the file IDMC_CREDS_FILE names (the explicit source wins)"""
    out, p = L.login_values(), os.environ.get("IDMC_CREDS_FILE")
    if p and os.path.exists(p) and Path(p).resolve() != L.login_file():
        if Path(p).resolve().is_relative_to(TOOLKIT.resolve()):
            H.die("IDMC_CREDS_FILE points inside the toolkit: move it outside (e.g. ~/.idmc_toolkit/.env)")
        out.update(L.read_kv(p))
    if out.get("IDMC_LOGIN_HOST"):
        out["IDMC_LOGIN_HOST"] = L.normalize_host(out["IDMC_LOGIN_HOST"])
    return out


def env(key, required=True):
    """a credential or environment value by KEY; never printed"""
    v = os.environ.get(key) or _creds_file().get(key)
    if not v and required:
        where = "IDMC_LOGIN.txt (toolkit root)" if key in L.KEYS else "your toolkit .env (see ENV_KEYS.md)"
        H.die(f"missing {key}: set it in {where}; the value is never printed")
    return v or None


def have_env(*keys):
    return all(os.environ.get(k) or _creds_file().get(k) for k in keys)


def lookup(cfg, dotted):
    cur = cfg
    for k in dotted.split("."):
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        elif isinstance(cur, list) and k.isdigit():
            cur = cur[int(k)]
        else:
            return None
    return cur


def render(obj, cfg, st=None, secrets=False):
    """replace ${dotted.config.key}, ${state:dotted.key} and ${env:KEY} in strings (recursively).
    ${env:KEY} is filled only when secrets=True (an --execute run); otherwise it stays '<KEY>'."""
    st = state() if st is None else st

    def one(s):
        def rep(m):
            k = m.group(1)
            if k.startswith("env:"):
                return (env(k[4:]) if secrets else f"<{k[4:]}>")
            if k.startswith("state:"):
                v = lookup(st, k[6:])
                return str(v) if v is not None else f"<state:{k[6:]} not built yet>"
            v = lookup(cfg, k)
            return str(v) if v is not None else m.group(0)
        if isinstance(s, str) and _PH.fullmatch(s) and not s.startswith("${env:") and not s.startswith("${state:"):
            v = lookup(cfg, _PH.fullmatch(s).group(1))
            if v is not None and not isinstance(v, str):
                return v                                       # keep lists / numbers / dicts as they are
        return _PH.sub(rep, s) if isinstance(s, str) else s

    if isinstance(obj, dict):
        return {one(k): render(v, cfg, st, secrets) for k, v in obj.items()}
    if isinstance(obj, list):
        return [render(v, cfg, st, secrets) for v in obj]
    return one(obj)


def template(rel):
    with open(TEMPLATES / rel, encoding="utf-8") as f:
        return json.load(f)


def name(cfg, suffix):
    """an IDMC object name: '<project> - <suffix>'"""
    return f"{cfg['idmc']['project']} - {suffix}"


# ------------------------------------------------------------------ CLI + context
def parser(doc):
    ap = argparse.ArgumentParser(description=(doc or "").split("\n\n")[0], epilog=doc,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", help="config file (default: config.json, else config.example.json)")
    ap.add_argument("--offline", action="store_true", help="never log in: print the requests only (implies dry run)")
    H.add_gate_args(ap)
    return ap


class Ctx:
    def __init__(self, args):
        H.safe_console()
        self.args = args
        self.cfg = load_config(getattr(args, "config", None))
        self.execute = bool(getattr(args, "execute", False)) and not getattr(args, "dry_run", False)
        self.offline = bool(getattr(args, "offline", False)) or (not self.execute and not have_env("IDMC_USER", "IDMC_PASS",
                                                                                                         "IDMC_LOGIN_HOST"))
        if self.execute and self.offline:
            H.die("--execute and --offline exclude each other")
        if self.execute and not getattr(args, "expect_org", None):
            H.die("--execute needs --expect-org <orgIdV3>: name the org you mean to change")
        self._s = self._gate = None
        mode = "EXECUTE" if self.execute else ("DRY-RUN offline" if self.offline else "DRY-RUN (live reads only)")
        print(f"[mode] {mode}", flush=True)

    @property
    def S(self):
        if self.offline:
            raise Offline("this step needs a live read")
        if self._s is None:
            from idmc_session import Session
            self._s = Session()
        return self._s

    def read(self, plane, path, method="GET", **kw):
        """a read (GET or a read-only POST such as a search); None when offline"""
        if self.offline:
            print(f"[OFFLINE] would read {method} {plane}:{path}")
            return None
        r = self.S.call(plane, method, path, **kw)
        return r

    def write(self, label, plane, method, path, **kw):
        if not self.execute:
            print(f"[DRY-RUN] {label}: {method} {plane}:{path}", flush=True)
            if kw.get("body") is not None:
                print("    body:", H.preview(H.redact(kw["body"]), 1400))
            elif kw.get("raw") is not None:
                print(f"    raw body: {len(kw['raw'])} bytes ({kw.get('ctype', '')})")
            return None
        if self._gate is None:
            self._gate = H.WriteGate(self.args, self.S)
        return self._gate.send(label, plane, method, path, **kw)

    def write_masked(self, label, plane, method, path, printable, **kw):
        """like write(), but prints `printable` (a masked copy) instead of the real body: for bodies whose secret keys the
        core redact() does not know (e.g. a catalog source's 'IICS Password' option)"""
        mode = "EXECUTE" if self.execute else "DRY-RUN"
        print(f"[{mode}] {label}: {method} {plane}:{path}", flush=True)
        print("    body:", H.preview(H.redact(printable), 1400))
        if not self.execute:
            return None
        if self._gate is None:
            self._gate = H.WriteGate(self.args, self.S)
        self._gate.guard()
        r = self.S.call(plane, method, path, **kw)
        print(f"    -> HTTP {r.status} {H.redact(r.head(240))}", flush=True)
        return r

    def json(self, r, default=None):
        return r.json(default) if r is not None else default


def ok(r):
    return r is not None and 200 <= r.status < 300


def v3_objects(ctx, otype, path_prefix=None):
    """v3 objects of a type (paged), optionally only under a path prefix; [] offline"""
    out, skip = [], 0
    while True:
        q = "type=='%s'" % otype
        r = ctx.read("v3", "/public/core/v3/objects?q=%s&limit=200&skip=%d" % (H_quote(q), skip))
        if r is None:
            return []
        page = (r.json({}) or {}).get("objects") or []
        out += page
        if len(page) < 200:
            break
        skip += 200
    if path_prefix:
        out = [o for o in out if (o.get("path") or "").startswith(path_prefix)]
    return out


def H_quote(s):
    import urllib.parse
    return urllib.parse.quote(s, safe="=")


def pod_host(ctx):
    """https://<pod>.<domain>.informaticacloud.com (offline: a placeholder)"""
    return "https://<pod>.<domain>.informaticacloud.com" if ctx.offline else ctx.S.hosts()["pod"]
