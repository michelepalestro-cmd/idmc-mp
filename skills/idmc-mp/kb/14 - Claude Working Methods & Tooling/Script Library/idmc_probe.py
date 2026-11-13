#!/usr/bin/env python3
"""idmc_probe.py - route discovery that does not fool itself: bogus-twin comparison (filters fake 200s and router
artifacts), the empty-POST verb probe, Content-Type variation, a DNS sweep of per-service hosts, and a GET sweep.

  python idmc_probe.py twin  <plane> <path>                     (GET real vs bogus twin; read-only)
  python idmc_probe.py sweep --file probes.txt                  (lines '<plane> <path>'; GET + twin each; read-only)
  python idmc_probe.py hosts [--pod-host <pod>.<domain>.informaticacloud.com]   (DNS only, no HTTP)
  python idmc_probe.py verbs  <plane> <path>  --execute --expect-org <orgIdV3>   (one EMPTY-body POST + its twin)
  python idmc_probe.py ctypes <plane> <path>  --execute --expect-org <orgIdV3>   (empty POSTs, 5 Content-Types)
Planes: see idmc_session.py (v2, v3, frs, runtime, dbmi, cai, cdgc, d360, hdm, profiling, session).

Decoder (PROVEN on production orgs 2026-07..09):
  * Only a DIFFERENCE between the real path and a nonsense twin is evidence. A twin that answers the same (a
    zero-byte 200, 403/500 router answers, an nginx 503, the login HTML) proves nothing about the real route.
  * 200 + HTML = wrong plane or wrong auth (login page); 200 + 0 bytes = gateway prefix route, nothing serving.
  * 404 with a body = wrong path or host (keep hunting); 'No static resource' or an empty 404 = route absent; a
    typed product error inside a 404 (e.g. DBMI_TASK_WAS_NOT_FOUND) = a live handler. 404 never means 'not entitled'.
  * Empty POST: 400/415/422 = the verb exists and the body is wrong; a 500 naming a null field = the handler parsed
    and ran; 405 = no such verb. There is no HEAD/OPTIONS discovery.
  * Vary the Content-Type before calling an upload route absent: the v3 import upload answered 404 MigrationSvc_025
    to application/json, 415 to zip/octet-stream and 400 MigrationSvc_030 to multipart (the handler parsed it).
  * Hosts fan out per service (<pod>-ing, -cai, -dqprofile, -mdm, idmc-api., cdgc-api., hdm., mcp.): a path is
    only meaningful with its host. A bogus host suffix must fail DNS, which proves the resolving ones are real.
SAFETY (stricter than the source lesson): "an empty body cannot create anything" holds for collection endpoints,
  but id-bearing ACTION endpoints act on an empty body (a DBMI task/deploy/<id> POST with no body deployed the
  task). verbs/ctypes therefore refuse action words, login/token routes (a login attempt counts toward the
  lockout) and paths ending in an id, and they are writes: --execute + --expect-org.
"""
from __future__ import annotations

import argparse
import os
import re
import socket
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import idmc_http as H  # noqa: E402
from idmc_session import LoginError, Session  # noqa: E402

DENY = [r"/(deploy|undeploy|execute|executable|start|stop|resume|run|publish|unpublish|restart|activate|cancel|logout)(/|\b)",
        r"/job(/|$|\?)", r"/import/(?!package$)", r"(Delete|Move|Copy)Entities|BaseEntities|Documents\(",
        r"login|jwt/Token|oauth|authz-service"]
ID_TAIL = re.compile(r"^(\d{3,}|[A-Za-z0-9]{20,24}|[0-9a-f-]{36})$")
SUFFIXES = ["-ing", "-cai", "-dqprofile", "-mdm", "-dqcloud-api", "-apigw", "-apim"]
CTYPES = [("application/json", b"{}"), ("application/vnd.api+json", b"{}"), ("application/zip", b""),
          ("text/plain", b""), ("multipart/form-data; boundary=idmcprobe", b"--idmcprobe--\r\n")]


def twin_of(path):
    base, q, query = path.partition("?")
    parts = base.rstrip("/").split("/")
    parts[-1] = "bogusZZZ" + uuid.uuid4().hex[:4]
    return "/".join(parts) + (q + query if q else "")


def sig(r):
    code = re.search(r"\b[A-Z][A-Za-z]*_\d{2,6}\b", r.text[:2000])
    return (r.status, r.is_html, len(r.raw) == 0, r.json() is not None, code.group(0) if code else None)


def compare(S, plane, path, method="GET", raw=None, ctype=None):
    real = S.call(plane, method, path, raw=raw, ctype=ctype)
    twin = S.call(plane, method, twin_of(path), raw=raw, ctype=ctype)
    same = sig(real) == sig(twin)
    print(f"  {method} {plane}:{path}")
    print(f"     real : HTTP {real.status:>4}  {real.verdict()}  | {real.head(140)}")
    print(f"     twin : HTTP {twin.status:>4}  {twin.verdict()}  | {twin.head(140)}")
    print(f"     =>   {'NO EVIDENCE: the twin answers the same way' if same else 'EVIDENCE: the real path differs from its twin'}")
    return real, twin, same


def refuse_actions(path):
    for pat in DENY:
        if re.search(pat, path, re.I):
            H.die(f"refused: '{path}' matches an action/login pattern ({pat}); an empty POST there can act or lock the account")
    tail = path.split("?")[0].rstrip("/").split("/")[-1]
    if ID_TAIL.match(tail) or re.search(r"\('[^']+'\)$", tail):
        H.die(f"refused: '{path}' ends in an object id; an empty POST may act on that object")


def cmd_hosts(S, pod_host):
    if not pod_host:
        pod_host = S.hosts()["pod"].split("://", 1)[1]
    pod, rest = pod_host.split(".", 1)
    names = [f"{pod}{s}.{rest}" for s in SUFFIXES] + [f"{p}.{rest}" for p in ("idmc-api", "cdgc-api", "hdm", "mcp")]
    control = f"{pod}-bogus{uuid.uuid4().hex[:4]}.{rest}"

    def resolve(h):
        try:
            socket.getaddrinfo(h, 443)
            return "resolves"
        except socket.gaierror:
            return "no DNS"
        except OSError as e:
            return f"error {e}"
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=12) as ex:     # failed lookups can take ~10 s each behind corporate resolvers
        results = list(ex.map(resolve, names + [control]))
    for h, ok in zip(names + [control], results):
        print(f"  {h:55} {ok}{'   (control: must be no DNS)' if h == control else ''}")


def main():
    H.safe_console()
    ap = argparse.ArgumentParser(description="IDMC route probes")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for c in ("twin", "verbs", "ctypes"):
        p = H.add_gate_args(sub.add_parser(c)) if c != "twin" else sub.add_parser(c)
        p.add_argument("plane")
        p.add_argument("path")
    sw = sub.add_parser("sweep")
    sw.add_argument("--file", required=True)
    sw.add_argument("--pace", type=float, default=0.5)
    sub.add_parser("hosts").add_argument("--pod-host")
    a = ap.parse_args()
    try:
        S = Session() if not (a.cmd == "hosts" and a.pod_host) else None
        if a.cmd == "hosts":
            return cmd_hosts(S, a.pod_host)
        if a.cmd == "twin":
            compare(S, a.plane, a.path)
            return
        if a.cmd == "sweep":
            evid = 0
            for line in open(a.file, encoding="utf-8"):
                if not line.strip() or line.startswith("#"):
                    continue
                plane, path = line.split(None, 1)
                evid += not compare(S, plane, path.strip())[2]
                time.sleep(a.pace)                       # sequential and paced: several services rate-limit (429)
            print(f"{evid} path(s) with evidence")
            return
        refuse_actions(a.path)
        gate = H.WriteGate(a, S)
        if not gate.execute:
            print(f"DRY-RUN: would send empty POST(s) to {a.plane}:{a.path} and its twin. Add --execute --expect-org.")
            return
        gate.guard()
        if a.cmd == "verbs":
            real, _, same = compare(S, a.plane, a.path, "POST", raw=b"", ctype="application/json")
            meaning = {400: "verb exists (body rejected)", 415: "verb exists (content type)", 422: "verb exists (body invalid)",
                       405: "NO such verb", 500: "handler parsed and ran (if it names a null field)"}.get(real.status, "see decoder")
            print(f"  verb verdict: HTTP {real.status} -> {meaning}{' (but the twin matches: not evidence)' if same else ''}")
        else:
            for ctype, body in CTYPES:
                r = S.call(a.plane, "POST", a.path, raw=body, ctype=ctype)
                print(f"  {ctype[:40]:40} HTTP {r.status:>4}  {r.verdict()}  | {r.head(120)}")
            print("  415 on some types + 400 on another = the route exists; the 400 type is the one it parses")
    except (LoginError, RuntimeError, ValueError) as e:
        H.die(f"{type(e).__name__}: {e}", 3)


if __name__ == "__main__":
    main()
