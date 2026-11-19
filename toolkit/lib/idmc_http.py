#!/usr/bin/env python3
"""idmc_http.py - shared plumbing for the IDMC script library, toolkit/lib (stdlib only).

HTTP that never raises, a dry-run write gate, redaction, multipart bodies, polling, JSON diffs and an
append-only log. Nothing here logs in or knows an org; idmc_session.py builds on it.

Rules every script inherits from this module:
  * Writes go through WriteGate.send(). The default is DRY-RUN: the request is printed and nothing is
    sent. --execute sends it, and --execute always needs --expect-org <orgIdV3>; the gate checks that id
    against the live org (Session.require_org) before the first write.
  * Secrets never reach the console or a log: redact() masks session ids, tokens, passwords, private
    keys and client secrets by key name (case-insensitive substring), and printed headers are always redacted.
  * Redirects are followed only to https on the same host (SafeRedirect): session headers never leave it.
  * HTTP errors are data, not exceptions: request() returns Resp for every HTTP status and status -1
    for DNS/TLS/timeouts. Callers must check r.status (older helpers that returned only the body hid
    failures; a 200 whose body is the login HTML page is a wrong-plane answer, see Resp.verdict()).

Evidence: the request/response handling is generalised from wrappers proven 2026-07..09 against
production orgs. WriteGate, redact(), diff() and poll() are new in this library (untested live).
"""
from __future__ import annotations

import gzip
import json
import os
import re
import sys
import time
import uuid
import urllib.error
import urllib.parse
import urllib.request

TIMEOUT = 120
SECRET_KEYS = {"icsessionid", "infa-session-id", "ids-session-id", "authorization", "cookie", "password",
               "sessionid", "sid", "jwt", "jwt_token", "access_token", "refresh_token", "clientsecret",
               "client_secret", "privatekey", "private_key", "securitytoken", "token", "mcp-session-id"}
# any key whose name, lower-cased with spaces, '_' and '-' removed, contains one of these is a secret
_SECRET_RE = re.compile(r"password|passwd|passphrase|^pass$|pwd|secret|token|apikey|privatekey|sessionid|"
                        r"authorization|cookie|^sas|sas$|signature|credential")
_JWT_RE = re.compile(r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}(?:\.[A-Za-z0-9_-]+)?")


def safe_console():
    """Windows consoles choke on non-ASCII IDMC messages; never crash on print."""
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(errors="backslashreplace")
        except (AttributeError, ValueError):
            pass


def die(msg, code=2):
    print("STOP: " + msg, file=sys.stderr, flush=True)
    sys.exit(code)


def is_secret_key(k):
    """True for a secret-ish key name, case-insensitively by substring ('Client Secret', 'secretKey', 'IICS Password',
    'api-key', 'Private Key Password', 'X-Session-Id' ...)."""
    if isinstance(k, dict):                 # CDGC style {"$t": "IICS Password"}
        k = k.get("$t", "")
    n = re.sub(r"[\s_\-]", "", str(k).lower())
    return n in SECRET_KEYS or bool(_SECRET_RE.search(n))


def _mask(v):
    return f"<redacted:{len(str(v))}>" if v not in (None, "") else v


def redact(obj):
    """Deep copy with secret-named values replaced by <redacted:N>. Use on anything you print or log.
    Also masks "value" / "values" of a {"key": <secret-ish name>, ...} pair object (CDGC options, CAI properties)."""
    if isinstance(obj, dict):
        pair = ("key" in obj and is_secret_key(obj["key"])) or ("name" in obj and "value" in obj
                                                                and is_secret_key(obj["name"]))
        out = {}
        for k, v in obj.items():
            if is_secret_key(k) or (pair and k in ("value", "values")):
                out[k] = [_mask(x) for x in v] if isinstance(v, list) else _mask(v)
            else:
                out[k] = redact(v)
        return out
    if isinstance(obj, list):
        return [redact(v) for v in obj]
    if isinstance(obj, str):
        return _JWT_RE.sub("<jwt>", obj)
    return obj


def preview(obj, n=900):
    s = obj if isinstance(obj, str) else json.dumps(redact(obj), default=str)
    return s if len(s) <= n else s[:n] + f"... (+{len(s) - n} chars)"


class Resp:
    def __init__(self, status, ctype, raw, headers, method, url):
        self.status, self.ctype, self.raw = status, ctype or "", raw or b""
        self.headers, self.method, self.url = headers or {}, method, url

    @property
    def ok(self):
        return isinstance(self.status, int) and 200 <= self.status < 300

    @property
    def text(self):
        return self.raw.decode("utf-8", "replace")

    @property
    def is_html(self):
        t = self.text.lstrip()[:400].lower()
        return t.startswith("<!") or "<html" in t

    def json(self, default=None):
        try:
            return json.loads(self.raw) if self.raw else default
        except ValueError:
            return default

    def head(self, n=300):
        """Short printable answer. JSON answers are redacted by key name (e.g. a clientSecret shown once)."""
        j = self.json()
        if j is not None:
            return preview(j, n)
        return _JWT_RE.sub("<jwt>", self.text[:n].replace("\n", " "))

    def verdict(self):
        """Response classifier (from the proven surface prober): IDMC status codes need decoding."""
        s = self.status
        if s == -1:
            return "UNREACHABLE (DNS/TLS/timeout)"
        if s == 200:
            if self.is_html:
                return "HTML-200 = wrong path or wrong auth plane (login page), not success"
            if not self.raw:
                return "EMPTY-200 = gateway prefix route, not a real result"
            return "JSON (live)" if self.json() is not None else f"200 {self.ctype[:30]}"
        return {400: "400 route+verb exist, body rejected", 401: "401 wrong token for this plane",
                403: "403 permission, wrong org, or unregistered type", 404: "404 not on this host/pod (never 'not entitled')",
                405: "405 verb unsupported", 406: "406 busy (the API works)", 415: "415 route exists, wrong Content-Type",
                422: "422 route+verb exist, body invalid"}.get(s, str(s))


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    """Follows a redirect only to https on the SAME host; any other Location (another host, an http downgrade) is
    refused, so the session headers (icSessionId, INFA-SESSION-ID, IDS-SESSION-ID, Authorization, Cookie) never
    leave the host they were meant for. A refused redirect comes back as the 3xx answer itself."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        old, new = urllib.parse.urlsplit(req.full_url), urllib.parse.urlsplit(newurl)
        if new.scheme.lower() != "https" or (new.hostname or "").lower() != (old.hostname or "").lower() \
                or new.port != old.port:
            return None
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER = urllib.request.build_opener(SafeRedirect)


def urlopen(req, timeout=TIMEOUT):
    """urllib.request.urlopen with the SafeRedirect policy (TLS verification as urllib's default)."""
    return _OPENER.open(req, timeout=timeout)


def request(method, url, headers=None, body=None, raw=None, ctype=None, timeout=TIMEOUT):
    """One HTTP call. body=JSON-able object, or raw=bytes with ctype. Returns Resp; never raises."""
    h = {"Accept": "application/json"}
    h.update(headers or {})
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    if data is not None and not any(k.lower() == "content-type" for k in h):
        h["Content-Type"] = ctype or "application/json"
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urlopen(req, timeout=timeout) as r:
            b, hd, st = r.read(), dict(r.headers), r.status
    except urllib.error.HTTPError as e:
        b, hd, st = e.read(), dict(e.headers or {}), e.code
    except Exception as e:  # noqa: BLE001 - DNS, TLS, timeout: an observation, not a crash
        return Resp(-1, "", f"{type(e).__name__}: {e}".encode(), {}, method, url)
    if hd.get("Content-Encoding") == "gzip":
        try:
            b = gzip.decompress(b)
        except OSError:
            pass
    return Resp(st, hd.get("Content-Type", ""), b, hd, method, url)


def multipart(field, filename, data, ctype="application/zip"):
    """(body, content_type) for one file part, e.g. field 'package' for the v3 import upload."""
    b = "idmc" + uuid.uuid4().hex
    head = (f"--{b}\r\nContent-Disposition: form-data; name=\"{field}\"; filename=\"{filename}\"\r\n"
            f"Content-Type: {ctype}\r\n\r\n").encode()
    return head + data + f"\r\n--{b}--\r\n".encode(), f"multipart/form-data; boundary={b}"


def multipart_json(field, obj):
    """(body, content_type) for one JSON part without filename, e.g. field 'dataSource' for CDGC."""
    b = "idmc" + uuid.uuid4().hex
    body = (f"--{b}\r\nContent-Disposition: form-data; name=\"{field}\"\r\nContent-Type: application/json\r\n\r\n"
            + json.dumps(obj) + f"\r\n--{b}--\r\n").encode()
    return body, f"multipart/form-data; boundary={b}"


def poll(fetch, done, interval=5, timeout=900, describe=None):
    """Call fetch() until done(value) or timeout. Returns (value, finished)."""
    t0, last = time.time(), None
    while True:
        last = fetch()
        if describe:
            print(f"    [{int(time.time() - t0):>4}s] {describe(last)}", flush=True)
        if done(last):
            return last, True
        if time.time() - t0 > timeout:
            return last, False
        time.sleep(interval)


def flatten(obj, prefix=""):
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    else:
        out[prefix] = json.dumps(obj, sort_keys=True, default=str) if isinstance(obj, list) else obj
    return out


def diff(before, after, ignore=("updateTime", "updatedBy", "createTime", "createdBy")):
    """Leaf-level changes between two JSON objects: [(path, old, new)]."""
    a, b = flatten(before or {}), flatten(after or {})
    return [(k, a.get(k), b.get(k)) for k in sorted(set(a) | set(b))
            if a.get(k) != b.get(k) and k.split(".")[-1] not in ignore]


def print_diff(changes, title="changed", limit=40):
    print(f"  {title}: {len(changes)} field(s)")
    for k, old, new in changes[:limit]:
        print(f"    {k}: {preview(redact(old), 120)} -> {preview(redact(new), 120)}")
    if len(changes) > limit:
        print(f"    ... {len(changes) - limit} more")


def save_json(path, obj, private=True):
    """Write JSON; private files are created 0600 (session caches, backups that can hold secrets)."""
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600 if private else 0o644)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, default=str)
    return path


def write_private(path, data):
    """Write bytes to a file created 0600 (export packages and edited packages can hold plaintext secrets)."""
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    try:
        os.chmod(path, 0o600)              # an existing file keeps its old mode through O_TRUNC
    except OSError:
        pass
    return path


def jlog(logfile, **rec):
    """Append one redacted JSON line (ts added) to logfile. Use for every write and its read-back."""
    if not logfile:
        return
    rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **redact(rec)}
    with open(logfile, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, default=str) + "\n")


def add_gate_args(ap):
    g = ap.add_argument_group("write safety")
    g.add_argument("--execute", action="store_true", help="really send writes (default: dry-run, print only)")
    g.add_argument("--dry-run", action="store_true", help="the default; wins over --execute if both are given")
    g.add_argument("--expect-org", metavar="ORGIDV3", help="22-char v3 org id you intend to change; required with --execute")
    g.add_argument("--log", metavar="FILE", help="append every write and read-back to this JSONL file")
    return ap


class WriteGate:
    """Dry-run by default. --execute sends; it needs --expect-org, checked once against the live org."""

    def __init__(self, args, session):
        self.execute = bool(getattr(args, "execute", False)) and not getattr(args, "dry_run", False)
        self.expect, self.session, self.checked = getattr(args, "expect_org", None), session, False
        self.logfile = getattr(args, "log", None)
        if self.execute and not self.expect:
            die("--execute needs --expect-org <orgIdV3>: name the org you mean to change")

    def guard(self):
        """Org proof: always before the first real write; also in dry-run when --expect-org is given."""
        if self.checked or not self.expect:
            return
        self.session.require_org(self.expect)
        self.checked = True

    def send(self, label, plane, method, path, **kw):
        mode = "EXECUTE" if self.execute else "DRY-RUN"
        print(f"[{mode}] {label}: {method} {plane}:{path}", flush=True)
        if kw.get("body") is not None:
            print("    body:", preview(kw["body"]))
        elif kw.get("raw") is not None:
            print(f"    raw body: {len(kw['raw'])} bytes ({kw.get('ctype', '')})")
        if not self.execute:
            return None
        self.guard()
        r = self.session.call(plane, method, path, **kw)
        print(f"    -> HTTP {r.status} {r.head(240)}", flush=True)
        jlog(self.logfile, label=label, method=method, plane=plane, path=path, status=r.status, answer=r.head(600))
        return r
