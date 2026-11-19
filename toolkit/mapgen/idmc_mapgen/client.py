"""IDMC REST client: one v2 login, a cached session, v2 / v3 / FRS calls and an org assertion.

    from idmc_mapgen.client import Client
    c = Client(profile)                      # profile dict (see profile.example.json); nothing is sent yet
    c.assert_org()                           # logs in on first use; raises OrgMismatch unless org.v2Id matches
    st, body = c.call("/api/v2/mttask")      # v2: header icSessionId
    st, body = c.call("/public/core/v3/objects?limit=5", v3=True)     # v3: header INFA-SESSION-ID
    st, body = c.frs("POST", "MoveEntities", {...})                    # FRS: <pod host>/frs/v1/<action>

Credentials never live in a profile. ``profile["auth"]`` names environment variables (defaults IDMC_USER,
IDMC_PASS, IDMC_LOGIN_URL) and may name a KEY=VALUE file (``envFile``, or the MAPGEN_ENV_FILE variable) that
supplies them. ``auth.loginUrl`` may hold the login host itself (e.g. https://dm-us.informaticacloud.com).
With no env file named, the toolkit's login file is used (~/.idmc_toolkit/IDMC_LOGIN.txt; a repo-root
IDMC_LOGIN.txt only as a git-clone legacy fallback); its IDMC_LOGIN_HOST gives the login URL.
Credentials go ONLY to https://<domain>.informaticacloud.com (anything else raises LoginError before a byte is sent),
and an "auth" block is never taken from a spec's inline "profile" object (spec.resolve_profile refuses it).

Login safety: the login itself is toolkit/lib/idmc_session.py's (Session.v2()), so mapgen shares the library's ONE
lockout guard: one attempt, a file lock, and after a rejected login (4xx) a block file keyed by an HMAC fingerprint of
the credentials; while it matches, no process (library or mapgen) logs in again. Fix the credentials (the fingerprint
changes) or have a human confirm them before deleting the block file (its path is in the error). Sessions are cached
0600 in IDMC_CACHE_DIR (default ~/.idmc_session) and reused for 24 minutes (IDMC sessions die 30 minutes after grant).
Every host comes from the login answer's serverUrl; nothing is guessed. Redirects are followed only to https on the
same host, and an absolute URL passed to call() must be https under the login domain.
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from . import lock

_LIB = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib"))
SESSION_MAX_AGE_S = 24 * 60
RELOGIN_GAP_S = 5 * 60          # after a 401: at most one forced re-login per client in this window
DEFAULT_AUTH = {"userEnv": "IDMC_USER", "passwordEnv": "IDMC_PASS", "loginUrlEnv": "IDMC_LOGIN_URL"}


def _lib(name):
    """A toolkit/lib module (idmc_session, idmc_http, idmc_login)."""
    if _LIB not in sys.path:
        sys.path.insert(0, _LIB)
    return __import__(name)


class LoginError(RuntimeError):
    """The login failed or cannot be attempted (missing credentials, recent failure)."""


class OrgMismatch(RuntimeError):
    """The session belongs to a different org than the profile expects."""


def read_env_file(path):
    """KEY=VALUE lines -> dict (blank lines, '#' comments and 'export ' prefixes allowed; quotes stripped)."""
    out = {}
    with open(os.path.expanduser(path), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            if line.startswith("export "):
                line = line[7:].lstrip()
            k, v = line.split("=", 1)
            v = v.strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
                v = v[1:-1]
            out[k.strip()] = v
    return out


def _parse(raw):
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except ValueError:
        return raw


class Session:
    def __init__(self, d):
        self.d = d
        self.session_id = d["icSessionId"]
        self.server_url = d["serverUrl"].rstrip("/")
        self.org_id = d.get("orgId")
        self.org_uuid = d.get("orgUuid")
        self.t = d.get("t", 0)

    @property
    def host(self):
        """https://<pod>.<domain>.informaticacloud.com (serverUrl without its /saas suffix)."""
        u = self.server_url
        return u[: -len("/saas")] if u.endswith("/saas") else u


class Client:
    def __init__(self, profile=None, state_dir=None, env=None, urlopen=None, clock=None):
        profile = profile or {}
        self.profile = profile
        self.auth = dict(DEFAULT_AUTH, **(profile.get("auth") or {}))
        self.expected_org = (profile.get("org") or {}).get("v2Id")
        self.state_dir = os.path.expanduser(state_dir or lock.STATE_DIR)   # live lock / job ledger (sessions: idmc_session)
        self._env = os.environ if env is None else env
        self._urlopen = urlopen or _lib("idmc_http").urlopen     # SafeRedirect: same-host https redirects only
        self._clock = clock or time.time
        self._sess = None
        self._lib_sess = None
        self._relogin_at = None
        self.logins = 0                       # sessions obtained by this client (tests and audit)

    # ---------- credentials and session ----------
    def _creds(self):
        L = _lib("idmc_login")
        env_file = (self.auth.get("envFile") or self._env.get("MAPGEN_ENV_FILE")
                    or self._env.get("IDMC_CREDS_FILE"))
        if not env_file:
            lf = L.login_file()               # ~/.idmc_toolkit/IDMC_LOGIN.txt, else the git-clone legacy copy
            env_file = str(lf) if lf else None
        file_vals = read_env_file(env_file) if env_file else {}

        def get(var):
            return self._env.get(var) or file_vals.get(var)
        user = get(self.auth["userEnv"])
        pw = get(self.auth["passwordEnv"])
        url = self.auth.get("loginUrl") or get(self.auth["loginUrlEnv"])
        if not url and get("IDMC_LOGIN_HOST"):       # IDMC_LOGIN.txt: a domain host or a pasted browser address
            raw = get("IDMC_LOGIN_HOST").strip()
            url = raw if "//" in raw else "https://" + raw
        missing = [n for n, v in ((self.auth["userEnv"], user), (self.auth["passwordEnv"], pw),
                                  ("auth.loginUrl or " + self.auth["loginUrlEnv"], url)) if not v]
        if missing:
            raise LoginError("missing credentials: set %s (environment%s)" % (
                ", ".join(missing), " or " + env_file if env_file else ", or auth.envFile / MAPGEN_ENV_FILE"))
        return user, pw, self.login_url(url)

    @staticmethod
    def login_url(url):
        """https://<domain>.informaticacloud.com or LoginError: credentials are never sent to any other place."""
        L = _lib("idmc_login")
        u = urllib.parse.urlsplit(url.strip())
        if u.scheme.lower() != "https" or u.username or u.password or u.port not in (None, 443):
            raise LoginError("login URL %r refused: it must be https://<domain>.informaticacloud.com "
                             "(credentials are never sent elsewhere)" % url)
        host = L.normalize_host(u.hostname or "")
        if not L.is_login_host(host):
            raise LoginError("login host %r refused: it must be <domain>.informaticacloud.com "
                             "(credentials are never sent elsewhere)" % (u.hostname or url))
        return "https://" + host

    def _library_session(self):
        """The idmc_session.Session that does the login (one lockout guard for the whole toolkit)."""
        if self._lib_sess is None:
            user, pw, url = self._creds()
            S = _lib("idmc_session")
            try:
                self._lib_sess = S.Session({"IDMC_USER": user, "IDMC_PASS": pw,
                                            "IDMC_LOGIN_HOST": urllib.parse.urlsplit(url).hostname})
            except S.LoginError as e:
                raise LoginError(str(e)) from None
        return self._lib_sess

    def session(self, fresh=False):
        """A live session: the in-memory one, the cached one (< 24 min old), or ONE guarded login (idmc_session)."""
        now = self._clock()
        if not fresh and self._sess and now - self._sess.t < SESSION_MAX_AGE_S:
            return self._sess
        self._sess = self.login(fresh=fresh)
        return self._sess

    def login(self, fresh=False):
        """ONE v2 login attempt through idmc_session (file lock + credential-fingerprint block file). Never retried."""
        ls = self._library_session()
        S = _lib("idmc_session")
        if fresh:
            ls.drop("v2")
        try:
            d = ls.v2()
        except S.LoginError as e:
            raise LoginError(str(e)) from None
        if not d.get("sid") or not d.get("serverUrl"):
            raise LoginError("login answer has no icSessionId/serverUrl - not retrying")
        self.logins += 1
        return Session({"icSessionId": d["sid"], "serverUrl": d["serverUrl"], "orgId": d.get("orgId"),
                        "orgUuid": d.get("orgUuid"), "t": self._clock() - (time.time() - d.get("t", time.time()))})

    def _check_url(self, url, s):
        """An absolute URL gets the session only when it is https under the login domain."""
        u = urllib.parse.urlsplit(url)
        host = (u.hostname or "").lower()
        dom = ".".join(urllib.parse.urlsplit(s.server_url).hostname.lower().split(".")[-3:])
        if u.scheme.lower() != "https" or not (host == dom or host.endswith("." + dom)):
            raise ValueError("refusing to send the IDMC session to %s://%s (only https hosts under %s)"
                             % (u.scheme, host, dom))

    # ---------- calls ----------
    def call(self, path, body=None, method=None, v3=False, raw=None, ctype="application/json", accept="application/json",
             base=None, timeout=180, headers=None, frs=False, _retry=True):
        """-> (status, parsed body). status -1 = transport error (body = repr). Never raises on HTTP errors."""
        s = self.session()
        if path.startswith("http"):
            self._check_url(path, s)
            url = path
        elif frs:
            url = s.host + "/frs/v1/" + path.lstrip("/")
        else:
            url = (base or s.server_url) + path
        h = {"Accept": accept}
        h["IDS-SESSION-ID" if frs else ("INFA-SESSION-ID" if v3 else "icSessionId")] = s.session_id
        if headers:
            h.update(headers)
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        if data is not None:
            h["Content-Type"] = ctype
        req = urllib.request.Request(url, data=data, headers=h, method=method)
        try:
            with self._urlopen(req, timeout=timeout) as x:
                b = x.read()
                status = getattr(x, "status", None) or x.getcode()
                if accept in ("application/json",) or b[:1] in (b"{", b"["):
                    return status, _parse(b)
                return status, b
        except urllib.error.HTTPError as e:
            txt = e.read().decode(errors="replace")[:4000]
            if e.code == 401 and _retry and (self._relogin_at is None or self._clock() - self._relogin_at >= RELOGIN_GAP_S):
                # the cached session died early: drop it and make ONE fresh login (a new attempt, not a retry of a
                # failed one); at most one such re-login per call and per RELOGIN_GAP_S, so a 401 loop never logs in
                self._relogin_at = self._clock()
                self._sess = None
                self.session(fresh=True)
                return self.call(path, body, method, v3, raw, ctype, accept, base, timeout, headers, frs, _retry=False)
            return e.code, _parse(txt.encode()) if txt[:1] in "{[" else txt
        except Exception as e:
            return -1, repr(e)[:500]

    def frs(self, method, action, body=None, timeout=180):
        return self.call(action, body=body, method=method, frs=True, timeout=timeout)

    def get_ok(self, path, v3=False, what=None):
        st, r = self.call(path, v3=v3)
        if st != 200:
            raise RuntimeError("GET %s -> %s %s" % (what or path, st, str(r)[:300]))
        return r

    # ---------- org ----------
    def whoami(self):
        """The org of this session: {"id": v2 org id, "name": ..., "uuid": ..., "serverUrl": ...}."""
        r = self.get_ok("/api/v2/org", what="v2 org")
        o = r[0] if isinstance(r, list) else r
        s = self.session()
        return {"id": o.get("id"), "name": o.get("name"), "uuid": s.org_uuid, "serverUrl": s.server_url,
                "parentOrgId": o.get("parentOrgId")}

    def assert_org(self, expected=None):
        """Raise OrgMismatch unless the session's v2 org id equals ``expected`` (default: profile org.v2Id)."""
        expected = expected or self.expected_org
        if not expected:
            raise OrgMismatch("no expected org: set org.v2Id in the profile (every write asserts the org first)")
        who = self.whoami()
        if who["id"] != expected:
            raise OrgMismatch("session org is %s (%s), the profile expects %s - refusing to continue"
                              % (who["id"], who["name"], expected))
        return who

    def require_org(self, expected_v3):
        """The write guard: the live org must be ``expected_v3`` (22-char v3 org id), proven exactly as
        idmc_session.Session.require_org proves it (GET /api/v2/org + the session user). Raises OrgMismatch."""
        if not re.fullmatch(r"[A-Za-z0-9]{22}", expected_v3 or ""):
            raise OrgMismatch("--expect-org must be the 22-character v3 org id (orgUuid), got %r" % (expected_v3,))
        self.session()
        try:
            return self._library_session().require_org(expected_v3)
        except SystemExit:
            raise OrgMismatch("ORG GUARD FAILED for --expect-org %s (see the message above); nothing was sent"
                              % expected_v3) from None
