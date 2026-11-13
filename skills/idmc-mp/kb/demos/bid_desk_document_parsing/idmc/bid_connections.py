#!/usr/bin/env python3
"""bid_connections.py - the three IDMC connections of the Bid Desk: create if missing, else update in place, then test.

    python bid_connections.py show                               # each connection: id, runtime, last test (read-only)
    python bid_connections.py build [crm|warehouse|sharepoint|all] [--execute --expect-org <orgIdV3>]
    python bid_connections.py test                               # GET /api/v2/connection/test/<id> for all three
    python bid_connections.py --offline build all                # print the bodies (secrets shown as <KEY>)

Bodies: idmc/templates/connections.json (PROVEN shapes, 2026-10-13). Secrets come from the .env only at --execute and are
masked in every print. Calls: GET /api/v2/connection/name/<url-quoted name>; POST /api/v2/connection (create);
POST /api/v2/connection/<id> with "id" (update; there is no PUT); GET /api/v2/connection/test/<id>.
Gotchas:
  * Salesforce: a password login depends on the agent's egress IP. From an agent inside the org's trusted IP ranges the
    security token may be empty; from any other agent the same login fails LOGIN_MUST_USE_SECURITY_TOKEN (L-CONN-110).
    An empty session log + 'The DTM process terminated unexpectedly' = this login failure; the reason is in the agent's
    tomcat log (L-CONN-109).
  * Snowflake key pair: privateKeyFile is a path ON THE AGENT; put the key at the same path on every agent of the group,
    so a task may run on any of them.
  * SharePoint Online: Test Connection only proves the token renews. Prove access with an object browse, and prove WRITE
    with infra/sharepoint_setup.py check (the token carries the consented scopes only, L-CONN-101/111).
  * Renaming a connection in place needs its secrets re-supplied (L-CONN-105).
"""
from __future__ import annotations

import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
import bid_common as C  # noqa: E402

KEYS = ("crm", "warehouse", "sharepoint")


def find(ctx, name):
    r = ctx.read("v2", "/api/v2/connection/name/" + urllib.parse.quote(name, safe=""))
    d = r.json({}) if r is not None else {}
    return d.get("id") if C.ok(r) and isinstance(d, dict) else None


def test(ctx, cid, name):
    r = ctx.read("v2", "/api/v2/connection/test/" + cid)
    if r is not None:
        d = r.json({})
        print("test %-28s HTTP %s %s" % (name, r.status, (d.get("description") if isinstance(d, dict) else r.head(200))))


def main():
    ap = C.parser(__doc__)
    ap.add_argument("cmd", choices=["show", "build", "test"])
    ap.add_argument("which", nargs="?", default="all", choices=KEYS + ("all",))
    a = ap.parse_args()
    ctx = C.Ctx(a)
    cfg, st = ctx.cfg, C.state()
    tpl = C.template("connections.json")
    conns = st.setdefault("conn", {})
    for key in (KEYS if a.which == "all" else (a.which,)):
        name = cfg["connections"][key]
        cid = find(ctx, name)
        if cid:
            conns[key] = cid
        print("connection %-28s %s" % (name, cid or ("(offline)" if ctx.offline else "MISSING")))
        if a.cmd == "test" and cid:
            test(ctx, cid, name)
        if a.cmd != "build":
            continue
        body = C.render(tpl[key], cfg, st, secrets=ctx.execute)
        if cid:
            body["id"] = cid
        r = ctx.write("%s connection %s" % ("update" if cid else "create", name), "v2", "POST",
                      "/api/v2/connection/" + cid if cid else "/api/v2/connection", body=body)
        if C.ok(r):
            conns[key] = (r.json({}) or {}).get("id") or cid
            test(ctx, conns[key], name)
        elif r is not None:
            print("  FAILED:", r.head(300))
    if not ctx.offline and (a.cmd != "build" or ctx.execute):
        C.save_state(st)


if __name__ == "__main__":
    main()
