#!/usr/bin/env python3
"""idmc_session.py - org-aware IDMC session: guarded v2 + v3 login, pod hosts, plane headers, JWT,
live org proof (whoami) and the --expect-org guard. stdlib only.

CONFIGURATION (fill in IDMC_LOGIN.txt at the KB root; environment > IDMC_CREDS_FILE > IDMC_LOGIN.txt)
  IDMC_USER        full login name (a truncated name gives a false IDS_085)
  IDMC_PASS        password
  IDMC_LOGIN_HOST  the DOMAIN host <domain>.informaticacloud.com (e.g. dm-us / dmp-us); a pasted browser address
                   or pod host is reduced to it (a pod host 404s on login)
  IDMC_CREDS_FILE  optional KEY=value file outside the KB (e.g. one per org); its values win over IDMC_LOGIN.txt
  IDMC_CACHE_DIR   session caches, login lock and block file (default ~/.idmc_session, outside the KB)
  IDMC_PROFILE     cache name; use one per org (default: a hash of user + login host)

PLANES (every host is computed from the login answer; header values are session ids)
  v2 / v3    <serverUrl>/api/v2/... and <serverUrl>/public/core/v3/...    icSessionId / INFA-SESSION-ID (v2 id)
  frs        https://<pod>.<domain>.informaticacloud.com/frs/...          IDS-SESSION-ID (v2 id)
  runtime    https://<pod>.<domain>.informaticacloud.com/runtime/...      IDS-SESSION-ID (v2 id)
  dbmi       https://<pod>-ing.<domain>.informaticacloud.com/dbmi/...     IDS-SESSION-ID + INFA-SESSION-ID + icSessionId
  cai        https://<pod>-cai.<domain>.informaticacloud.com/active-bpel/...  INFA-SESSION-ID + vnd.api+json
  cdgc/d360  https://cdgc-api.<domain>... / https://idmc-api.<domain>...  Bearer JWT + X-INFA-ORG-ID + IDS-SESSION-ID
  hdm        https://hdm.<domain>.informaticacloud.com/a2e-mcp-asset-mgmt-svc/...  IDS-SESSION-ID (v3 id)
  profiling  https://<pod>-dqprofile.<domain>.informaticacloud.com/...    IDS-SESSION-ID (v3 id; the v2 id got 401 on one pod)
  session    https://<pod>.<domain>.informaticacloud.com/session-service/...  IDS-SESSION-ID + USER_SESSION cookie
  public     a full URL and no auth header (anonymous CAI runtime)

EVIDENCE  PROVEN 2026-09 against production orgs: the v2 login (icSessionId, serverUrl, orgId, orgUuid); the v3
  login (userInfo.sessionId, userInfo.orgId, products[].baseApiUrl); the v2 id accepted on v2, v3, frs, runtime,
  dbmi and cai; POST identity-service/api/v1/jwt/Token?client_id=cdlg_app with IDS-SESSION-ID + USER_SESSION
  cookie (the GET form, client_id=idmc_api, also 2026-09); GET /api/v2/org. ADAPTED / UNTESTED: the
  session-service User read (a UI call; its headless header set is not proven), the Windows file lock.

LOCKOUT GUARD  A few rejected logins lock the account (IDS_086) and each retry restarts the lock. So: one attempt
  per run; logins serialised by a file lock with the cache re-checked under the lock; a rejected login (4xx) writes
  a block file keyed by a fingerprint of the credentials, and while it matches no process logs in again. Fix the
  credentials (the fingerprint changes) or have a human confirm them before deleting the block file. 5xx, 429 and
  network errors stop the run without a block. Sessions die ~30 min after grant, so re-login happens at 24 min.

CLI  python idmc_session.py whoami [--expect-org <orgIdV3>] [--no-v3] | hosts | get <plane> <path> [--full]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import idmc_http as H  # noqa: E402
import idmc_login as L  # noqa: E402

MAX_AGE, JWT_AGE = 24 * 60, 20 * 60
KB_ROOT = Path(__file__).resolve().parents[2]          # Script Library -> its topic folder -> KB root
PLANE_HOST = {"v2": "base", "v3": "base", "frs": "pod", "runtime": "pod", "session": "pod", "dbmi": "ing",
              "cai": "cai", "cdgc": "cdgc", "d360": "d360", "hdm": "hdm", "profiling": "dqprofile", "login": "login"}


class LoginError(RuntimeError):
    pass


def _inside_kb(p):
    p = Path(p).expanduser().resolve()
    return p == KB_ROOT or KB_ROOT in p.parents


def load_config():
    cfg, f = L.login_values(), os.environ.get("IDMC_CREDS_FILE")
    if f and Path(f).expanduser().resolve() != L.login_file():
        if _inside_kb(f):
            H.die("IDMC_CREDS_FILE points inside the KB; keep credentials outside it")
        cfg.update(L.read_kv(f))
    for k in L.KEYS:
        if os.environ.get(k):
            cfg[k] = os.environ[k]
    miss = [k for k in L.KEYS if not cfg.get(k)]
    if miss:
        where = L.login_file() or f"{L.FILE_NAME} at the toolkit root"
        H.die("missing " + ", ".join(miss) + f": fill in {where}, save, and run again")
    host = L.normalize_host(cfg["IDMC_LOGIN_HOST"])
    if not host.endswith(".informaticacloud.com") or host.count(".") != 2:
        H.die(f"IDMC_LOGIN_HOST must be <domain>.informaticacloud.com, got '{host}' (a pod host 404s on login; "
              "the wrong domain answers IDS_085, which looks like a bad password)")
    cfg["IDMC_LOGIN_HOST"] = host
    return cfg


class _Lock:
    """Exclusive inter-process lock: fcntl on POSIX, msvcrt on Windows."""

    def __init__(self, path):
        self.path = path

    def __enter__(self):
        self.f = open(self.path, "a+")
        try:
            import fcntl
            fcntl.flock(self.f, fcntl.LOCK_EX)
        except ImportError:
            import msvcrt
            for _ in range(240):
                try:
                    self.f.seek(0)
                    msvcrt.locking(self.f.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    time.sleep(0.5)
            else:
                raise LoginError("could not take the login lock")
        return self

    def __exit__(self, *exc):
        try:
            import fcntl
            fcntl.flock(self.f, fcntl.LOCK_UN)
        except ImportError:
            import msvcrt
            try:
                self.f.seek(0)
                msvcrt.locking(self.f.fileno(), msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
        self.f.close()


class Session:
    def __init__(self, cfg=None):
        self.cfg = cfg or load_config()
        self.host = self.cfg["IDMC_LOGIN_HOST"]
        d = Path(os.environ.get("IDMC_CACHE_DIR") or (Path.home() / ".idmc_session")).expanduser()
        if _inside_kb(d):
            H.die("IDMC_CACHE_DIR points inside the KB; session caches hold live session ids")
        d.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.prof = os.environ.get("IDMC_PROFILE") or hashlib.sha256(
            f"{self.cfg['IDMC_USER']}|{self.host}".encode()).hexdigest()[:10]
        self.dir, self.lock, self.block = d, d / f"{self.prof}.lock", d / f"{self.prof}.block.json"
        self._s, self._jwt = {}, {}

    def _fp(self):
        c = self.cfg
        return hashlib.sha256("\0".join((c["IDMC_USER"], c["IDMC_PASS"], self.host)).encode()).hexdigest()[:16]

    def _file(self, kind):
        return self.dir / f"{self.prof}.{kind}.json"

    def _cached(self, kind):
        s = self._s.get(kind)
        if not s:
            try:
                s = json.loads(self._file(kind).read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return None
        if time.time() - s.get("t", 0) < MAX_AGE:
            self._s[kind] = s
            return s
        return None

    def drop(self, kind):
        self._s.pop(kind, None)
        try:
            self._file(kind).unlink()
        except OSError:
            pass

    def _check_block(self):
        try:
            b = json.loads(self.block.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if b.get("fp") == self._fp():
            raise LoginError(f"login BLOCKED since {b.get('at')} ({b.get('why')}). Fix the credentials, or have a human "
                             f"confirm them in a browser, then delete {self.block}. Not retrying.")

    def _login(self, kind):
        s = self._cached(kind)
        if s:
            return s
        with _Lock(self.lock):
            s = self._cached(kind)            # another process may have logged in while this one waited
            if s:
                return s
            self._check_block()
            u, p = self.cfg["IDMC_USER"], self.cfg["IDMC_PASS"]
            if kind == "v2":
                url, body = f"https://{self.host}/ma/api/v2/user/login", {"@type": "login", "username": u, "password": p}
            else:
                url, body = f"https://{self.host}/saas/public/core/v3/login", {"username": u, "password": p}
            r = H.request("POST", url, body=body, timeout=60)
            if not r.ok:
                why = f"{kind} login HTTP {r.status} " + r.head(200).replace(p, "***")
                if r.status in (-1, 429) or r.status >= 500:
                    raise LoginError(why + " (transient: not blocked, not retried)")
                if r.status == 404:
                    raise LoginError(why + " (wrong login host?)")
                H.save_json(str(self.block), {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                              "fp": self._fp(), "why": why})
                raise LoginError(why + " -> REJECTED, block file written, not retrying "
                                 "(IDS_085 = bad credentials or wrong domain; IDS_086 = account locked)")
            j = r.json({}) or {}
            if kind == "v2":
                s = {"sid": j.get("icSessionId"), "serverUrl": j.get("serverUrl"), "orgId": j.get("orgId"),
                     "orgUuid": j.get("orgUuid"), "orgName": j.get("orgName"), "user": j.get("name")}
            else:
                ui, prods = j.get("userInfo") or {}, j.get("products") or []
                bases = [x.get("baseApiUrl") for x in prods if x.get("baseApiUrl")]
                s = {"sid": ui.get("sessionId"), "orgId": ui.get("orgId"), "orgName": ui.get("orgName"),
                     "user": ui.get("name"), "baseApiUrl": bases[0] if bases else None,
                     "products": [x.get("name") for x in prods]}
            if not s["sid"]:
                raise LoginError(f"{kind} login answered 200 without a session id: {r.head(160)}")
            s["t"] = time.time()
            H.save_json(str(self._file(kind)), s)
            self._s[kind] = s
            return s

    def v2(self):
        return self._login("v2")

    def v3(self):
        return self._login("v3")

    def hosts(self):
        base = self.v2()["serverUrl"].rstrip("/")         # https://<pod>.<domain>.informaticacloud.com/saas
        pod_url = base[:-5] if base.endswith("/saas") else base
        pod, rest = pod_url.split("://", 1)[1].split(".", 1)
        return {"base": base, "pod": pod_url, "ing": f"https://{pod}-ing.{rest}", "cai": f"https://{pod}-cai.{rest}",
                "dqprofile": f"https://{pod}-dqprofile.{rest}", "mdm": f"https://{pod}-mdm.{rest}",
                "cdgc": f"https://cdgc-api.{rest}", "d360": f"https://idmc-api.{rest}", "hdm": f"https://hdm.{rest}",
                "mcp": f"https://mcp.{rest}", "login": f"https://{self.host}", "pod_label": pod, "domain_host": rest}

    def jwt(self, client_id="cdlg_app", sid_kind="v2"):
        c = self._jwt.get((client_id, sid_kind))
        if c and time.time() - c[1] < JWT_AGE:
            return c[0]
        sid = (self.v2() if sid_kind == "v2" else self.v3())["sid"]
        url = (f"https://{self.host}/identity-service/api/v1/jwt/Token?client_id={client_id}"
               f"&nonce={uuid.uuid4().hex}&access_code=")
        h = {"IDS-SESSION-ID": sid, "Cookie": "USER_SESSION=" + sid}
        r = H.request("POST", url, h, raw=b"", ctype="application/json")
        if r.status in (404, 405):
            r = H.request("GET", url, h)
        tok = (r.json({}) or {}).get("jwt_token") if r.ok else None
        if not tok:
            raise LoginError(f"JWT mint failed HTTP {r.status} {r.head(160)}")
        self._jwt[(client_id, sid_kind)] = (tok, time.time())    # memory only, never written to disk
        return tok

    def headers(self, plane):
        if plane == "public":
            return {}
        if plane in ("hdm", "profiling"):
            return {"IDS-SESSION-ID": self.v3()["sid"]}
        sid = self.v2()["sid"]
        table = {"v2": {"icSessionId": sid}, "v3": {"INFA-SESSION-ID": sid}, "frs": {"IDS-SESSION-ID": sid},
                 "runtime": {"IDS-SESSION-ID": sid}, "session": {"IDS-SESSION-ID": sid, "Cookie": "USER_SESSION=" + sid},
                 "dbmi": {"IDS-SESSION-ID": sid, "INFA-SESSION-ID": sid, "icSessionId": sid},
                 "cai": {"INFA-SESSION-ID": sid, "Accept": "application/vnd.api+json",
                         "Content-Type": "application/vnd.api+json"}}
        if plane in table:
            return dict(table[plane])
        if plane in ("cdgc", "d360"):
            return {"Authorization": "Bearer " + self.jwt(), "X-INFA-ORG-ID": self.v2().get("orgUuid") or "",
                    "IDS-SESSION-ID": sid}
        raise ValueError(f"unknown plane '{plane}' (managed MCP servers: use idmc_mcp.py)")

    def call(self, plane, method, path, body=None, raw=None, ctype=None, headers=None, timeout=H.TIMEOUT):
        if not path.startswith("http") and plane == "public":
            raise ValueError("the public plane needs a full URL")
        url = path if path.startswith("http") else self.hosts()[PLANE_HOST[plane]] + path
        r = None
        for attempt in (1, 2):
            h = self.headers(plane)
            h.update(headers or {})
            r = H.request(method, url, h, body=body, raw=raw, ctype=ctype, timeout=timeout)
            if r.status != 401 or attempt == 2 or plane == "public":
                return r
            self._jwt.clear()                                  # cdgc/d360: usually an expired JWT
            if plane not in ("cdgc", "d360"):
                self.drop("v3" if plane in ("hdm", "profiling") else "v2")   # revoked early: log in once more
        return r

    def get(self, plane, path, **kw):
        return self.call(plane, "GET", path, **kw)

    def whoami(self, with_v3=True):
        s2 = self.v2()
        w = {"login_host": self.host, "user": s2.get("user"), "orgName": s2.get("orgName"), "orgIdV2": s2.get("orgId"),
             "orgIdV3": s2.get("orgUuid"), "serverUrl": s2.get("serverUrl"), "session_age_s": int(time.time() - s2["t"])}
        r = self.get("v2", "/api/v2/org")
        o = r.json({})
        o = (o[0] if o else {}) if isinstance(o, list) else (o or {})
        w["api_v2_org"] = {"status": r.status, "id": o.get("id"), "name": o.get("name"),
                           "uuid": o.get("orgUuid") or o.get("uuid")}
        if not w["orgName"] and o.get("name"):             # the v2 login body often omits orgName; /api/v2/org has it
            w["orgName"] = o["name"]
        r = self.get("session", "/session-service/api/v1/session/User")
        u = r.json({}) if r.ok and not r.is_html else {}
        u = u if isinstance(u, dict) else {}
        w["session_user"] = {"status": r.status, "name": u.get("name"), "orgId": u.get("orgId")}
        seen = [w["api_v2_org"]["uuid"], w["orgIdV3"]]
        so = u.get("orgId") or ""
        if len(so) == 22:
            seen.append(so)
        elif so and so != w["orgIdV2"]:
            w["mismatch"] = f"session-service orgId {so} != session org {w['orgIdV2']}"
        if with_v3:
            s3 = self.v3()
            w["v3_login"] = {"orgId": s3.get("orgId"), "orgName": s3.get("orgName"), "baseApiUrl": s3.get("baseApiUrl")}
            seen.append(s3.get("orgId"))
            if (s3.get("baseApiUrl") or "").rstrip("/") != (s2.get("serverUrl") or "").rstrip("/"):
                w["warning"] = "v3 baseApiUrl differs from v2 serverUrl: check the pod before writing"
        w["v3_ids_seen"] = sorted({i for i in seen if i})
        return w

    def require_org(self, expected):
        if not re.fullmatch(r"[A-Za-z0-9]{22}", expected or ""):
            H.die("--expect-org must be the 22-character v3 org id (userInfo.orgId / orgUuid)")
        w, bad = self.whoami(with_v3=False), []
        org = w["api_v2_org"]
        if org["status"] != 200:
            bad.append(f"GET /api/v2/org -> {org['status']}")
        elif org["id"] and org["id"] != w["orgIdV2"]:
            bad.append(f"/api/v2/org id {org['id']} != session org {w['orgIdV2']}")
        if w["v3_ids_seen"] != [expected]:
            bad.append(f"live v3 org id(s) {w['v3_ids_seen']} != --expect-org {expected}")
        if w.get("mismatch"):
            bad.append(w["mismatch"])
        if bad:
            H.die("ORG GUARD FAILED, nothing sent: " + "; ".join(bad))
        print(f"ORG GUARD OK: '{w['orgName']}' v3={expected} v2={w['orgIdV2']} user={w['user']}", flush=True)
        return w


def main():
    H.safe_console()
    ap = argparse.ArgumentParser(description="IDMC session helper (read-only)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("whoami", help="prove the org: logins + GET /api/v2/org + session user")
    w.add_argument("--expect-org")
    w.add_argument("--no-v3", action="store_true", help="skip the v3 login (one login instead of two)")
    sub.add_parser("hosts", help="hosts derived from the login answer")
    g = sub.add_parser("get", help="one read-only GET on a plane")
    g.add_argument("plane", choices=sorted(PLANE_HOST) + ["public"])
    g.add_argument("path")
    g.add_argument("--full", action="store_true")
    a = ap.parse_args()
    try:
        S = Session()
        if a.cmd == "whoami":
            print(json.dumps(S.whoami(with_v3=not a.no_v3), indent=1))
            if a.expect_org:
                S.require_org(a.expect_org)
        elif a.cmd == "hosts":
            print(json.dumps(S.hosts(), indent=1))
        else:
            r = S.get(a.plane, a.path)
            print(f"HTTP {r.status} | {r.verdict()} | {r.ctype}")
            body = r.json()
            print(H.preview(body if body is not None else r.text, 10 ** 6 if a.full else 3000))
    except LoginError as e:
        H.die(str(e), 3)


if __name__ == "__main__":
    main()
