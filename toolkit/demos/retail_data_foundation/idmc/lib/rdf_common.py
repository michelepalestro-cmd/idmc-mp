"""Shared helpers for the retail_data_foundation blueprint (stdlib only, Python 3.10+).

- paths: BLUEPRINT (this demo's folder), CORE (the core library, the KB's Script Library), STATE (state/ids.json lives here)
- config: load_config() reads config.json, else config.example.json (with a warning)
- env:    env(name) / env_status(names) read IDMC_LOGIN.txt (toolkit root), the toolkit .env (IDMC_CREDS_FILE) or
          the environment; values are never printed, only key names
- render: render(text, vars) replaces ${NAME} strictly (an unknown name is an error); template_vars(cfg) builds the
          non-secret variable set every template uses
- state:  load_state() / save_state() for the ids the build creates (state/ids.json, private, never shared)
- core:   core_cli(script, args) runs a Script Library script as a subprocess, so the core stays unmodified and owns the
          login, the org guard and the dry-run default
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

BLUEPRINT = Path(__file__).resolve().parents[2]
TOOLKIT = Path(__file__).resolve().parents[4]
CORE = TOOLKIT / "lib"
STATE_DIR = BLUEPRINT / "state"
STATE_FILE = STATE_DIR / "ids.json"
RENDERED = STATE_DIR / "rendered"

if str(CORE) not in sys.path:
    sys.path.insert(0, str(CORE))
import idmc_login as L  # noqa: E402


def die(msg, code=2):
    print("ERROR: " + msg, file=sys.stderr)
    sys.exit(code)


# ---------------------------------------------------------------- config
def load_config(path=None):
    p = Path(path) if path else BLUEPRINT / "config.json"
    if not p.exists():
        ex = BLUEPRINT / "config.example.json"
        print(f"note: {p.name} not found, using config.example.json (copy it to config.json and edit)", file=sys.stderr)
        p = ex
    with open(p, encoding="utf-8-sig") as f:
        return json.load(f)


# ---------------------------------------------------------------- env (.env file or environment)
_ENV_CACHE = None


def _env_file_values():
    global _ENV_CACHE
    if _ENV_CACHE is not None:
        return _ENV_CACHE
    vals = L.login_values()
    f = os.environ.get("IDMC_CREDS_FILE")
    if f and Path(f).expanduser().exists() and Path(f).expanduser().resolve() != L.login_file():
        fp = Path(f).expanduser().resolve()
        if TOOLKIT in fp.parents:
            die("IDMC_CREDS_FILE points inside the toolkit; keep the .env outside it")
        vals.update(L.read_kv(fp))
    if vals.get("IDMC_LOGIN_HOST"):
        vals["IDMC_LOGIN_HOST"] = L.normalize_host(vals["IDMC_LOGIN_HOST"])
    _ENV_CACHE = vals
    return vals


def env(name, default=None, required=False):
    """Environment wins over the .env file. Never print the value."""
    v = os.environ.get(name) or _env_file_values().get(name) or default
    if required and not v:
        die(f"missing {name} (set it in " + ("IDMC_LOGIN.txt at the toolkit root)" if name in L.KEYS
                                         else "the toolkit .env, see ENV_KEYS.md)"))
    return v


def env_status(names):
    """[(name, 'set'|'MISSING')] - for --help style checks; values never shown."""
    return [(n, "set" if env(n) else "MISSING") for n in names]


# ---------------------------------------------------------------- render
_VAR = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def render(text, vars_, where="template"):
    missing = sorted({m for m in _VAR.findall(text) if m not in vars_})
    if missing:
        die(f"{where}: unknown placeholder(s) {', '.join(missing)}")
    return _VAR.sub(lambda m: str(vars_[m.group(1)]), text)


def render_json(path, vars_):
    return json.loads(render(Path(path).read_text(encoding="utf-8"), vars_, where=str(Path(path).name)))


def template_vars(cfg, offline=False):
    """Non-secret values used by every template. offline=True fills env-backed values with visible placeholders."""
    def e(name, dflt):
        v = env(name)
        return v if v else (dflt if offline else die(f"missing {name} (needed to render templates; or use --offline)"))
    ds = cfg["warehouse"]["datasets"]
    c = cfg["connections"]
    v = {
        "PREFIX": cfg["prefix"], "TAG": cfg["idmc"]["tag"],
        "PROJECT": cfg["idmc"]["project"], "FOLDER": cfg["idmc"]["folder"],
        "RUNTIME_ENV": cfg["idmc"]["runtimeEnvironment"],
        "PG_SCHEMA": cfg["source"]["schema"], "PG_ACT_SCHEMA": cfg["source"]["activationSchema"],
        "PG_HOST": e("PG_HOST", "pg-host-placeholder"), "PG_PORT": e("PG_PORT", "5432"),
        "PG_DB": e("PG_DB", "rdf_retail"), "PG_USER": e("PG_USER", "rdf_app"), "PG_CDC_USER": e("PG_CDC_USER", "rdf_cdc"),
        "WH_PROJECT": e("BQ_PROJECT", "bq-project-placeholder"), "GCS_BUCKET": e("GCS_STAGING_BUCKET", "gcs-bucket-placeholder"),
        "BQ_LOCATION": cfg["warehouse"].get("location", "US"),
        "DS_LAND": ds["land"], "DS_STAGING": ds["staging"], "DS_GOLD": ds["gold"], "DS_CDC": ds["cdc"],
        "CONN_PG": c["pg"], "CONN_PG_CDC": c["pgCdc"], "CONN_BQ": c["bq"], "CONN_BQ_DBMI": c["bqDbmi"], "CONN_SF": c["sf"],
        "SF_API_VERSION": cfg["crm"]["apiVersion"], "SF_CONTACT_EXT": cfg["crm"]["contactExternalId"],
        "SF_MEMBERSHIP_OBJ": cfg["crm"]["membershipObject"], "SF_MEMBERSHIP_EXT": cfg["crm"]["membershipExternalId"],
        "CRM_COUNT_GATE": cfg["crm"]["countGate"], "TEST_ID_REGEX": cfg["crm"]["testIdentityRegex"],
        "CDC_GCS_DIR": cfg["cdc"]["gcsDirectory"],
    }
    v.update(pg_tls_vars(cfg, v["PG_HOST"]))
    return v


LOOPBACK = {"localhost", "127.0.0.1", "::1", "[::1]"}


def pg_tls_vars(cfg, host):
    """TLS settings of the IDMC PostgreSQL connections. TLS with certificate validation everywhere, except the loopback
    stand-in of infra/docker-compose.yml (plain postgres image without a server certificate, published on 127.0.0.1
    only, so the Secure Agent on the same host never sends the login over a network). source.tls = "on" forces TLS."""
    mode = str(cfg["source"].get("tls", "auto")).lower()
    if mode not in ("auto", "on"):
        die('config.json source.tls must be "auto" or "on"')
    if mode == "auto" and str(host).strip().lower() in LOOPBACK:
        return {"PG_ENCRYPTION": "noEncryption", "PG_TLS12": "false", "PG_VALIDATE_CERT": "false"}
    return {"PG_ENCRYPTION": "SSL", "PG_TLS12": "true", "PG_VALIDATE_CERT": "true"}


# ---------------------------------------------------------------- state
def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {}


def save_state(st):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(st, indent=1, sort_keys=True), encoding="utf-8")
    os.replace(tmp, STATE_FILE)
    return STATE_FILE


def write_rendered(name, obj):
    RENDERED.mkdir(parents=True, exist_ok=True)
    p = RENDERED / name
    p.write_text(json.dumps(obj, indent=1) if not isinstance(obj, (bytes, str)) else obj, encoding="utf-8")
    return p


# ---------------------------------------------------------------- SQL hygiene (the BigQuery reader rejects comments and non-ASCII)
def clean_sql(text):
    out = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("--"):
            continue
        line = re.sub(r"[ \t]--.*$", "", line)
        out.append(line.rstrip())
    sql = "\n".join(out).encode("ascii", "ignore").decode().strip()
    return sql[:-1].rstrip() if sql.endswith(";") else sql


# ---------------------------------------------------------------- core CLI passthrough
def gate_args(a):
    """The write-gate flags of an argparse namespace, forwarded to a core script."""
    out = []
    if getattr(a, "execute", False) and not getattr(a, "dry_run", False):
        out.append("--execute")
    if getattr(a, "expect_org", None):
        out += ["--expect-org", a.expect_org]
    if getattr(a, "log", None):
        out += ["--log", a.log]
    return out


def core_cli(script, args, dry_print=False):
    """Run <Script Library>/<script> with args. dry_print=True only prints the command (offline planning)."""
    cmd = [sys.executable, str(CORE / script)] + [str(x) for x in args]
    shown = " ".join(f'"{x}"' if " " in str(x) else str(x) for x in cmd[1:])
    print(f"$ python {shown}", flush=True)
    if dry_print:
        return 0
    return subprocess.call(cmd)


def add_common_args(ap, gate=True):
    ap.add_argument("--config", help="config file (default: config.json, else config.example.json)")
    if gate:
        g = ap.add_argument_group("write safety (same meaning as the core library)")
        g.add_argument("--execute", action="store_true", help="really send writes (default: dry-run)")
        g.add_argument("--dry-run", action="store_true", help="the default; wins over --execute")
        g.add_argument("--expect-org", metavar="ORGIDV3", help="v3 org id you mean to change; required with --execute")
        g.add_argument("--log", metavar="FILE", help="append writes and read-backs to this JSONL file")
    return ap


def offline_session_guard(a):
    if getattr(a, "execute", False) and not getattr(a, "expect_org", None):
        die("--execute needs --expect-org <orgIdV3>")


def frs_move(S, gate, frs_guid, folder_guid, name):
    """FRS MoveEntities (a new task or mapping lands in Default). Tries the KB path, then the older recipe path on 404."""
    body = {"xferSpec": {"targetLocationId": folder_guid, "sourceSpecArr": [{
        "sourceEntityId": frs_guid, "destName": name, "destDesc": "", "conflictResolution": "NONE",
        "resetExpiryTime": False, "mergeTags": ""}]}}
    for path in ("/frs/api/v1/MoveEntities", "/frs/v1/MoveEntities"):
        r = gate.send(f"move {name} into folder", "frs", "POST", path, body=body)
        if r is None or r.status != 404:
            return r
    return r


# ---------------------------------------------------------------- HTTP: redirects never carry credentials elsewhere
import urllib.error as _ue  # noqa: E402
import urllib.parse as _up  # noqa: E402
import urllib.request as _ur  # noqa: E402

_SENSITIVE = {"authorization", "cookie", "x-tableau-auth", "icsessionid", "infa-session-id", "ids-session-id",
              "x-snowflake-authorization-token-type"}


class SafeRedirect(_ur.HTTPRedirectHandler):
    """urllib's default handler re-sends every header (Authorization, Cookie, session ids) to whatever Location a
    3xx names. This one refuses an https -> http downgrade and drops credential headers when the redirect leaves the
    original scheme + host + port (a pre-signed download URL on another host still works)."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is None:
            return None
        o, n = _up.urlsplit(req.full_url), _up.urlsplit(new.full_url)
        if o.scheme == "https" and n.scheme != "https":
            raise _ue.HTTPError(req.full_url, code, "refused redirect from https to " + n.scheme, headers, fp)
        if (o.scheme, o.hostname, o.port) != (n.scheme, n.hostname, n.port):
            for d in (new.headers, new.unredirected_hdrs):
                for k in [k for k in d if k.lower() in _SENSITIVE]:
                    del d[k]
        return new


_OPENER = _ur.build_opener(SafeRedirect)


def urlopen(req, timeout=60):
    """urllib.request.urlopen with SafeRedirect (use it for every request that carries a credential)."""
    return _OPENER.open(req, timeout=timeout)
