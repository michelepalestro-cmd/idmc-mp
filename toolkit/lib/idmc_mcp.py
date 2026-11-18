#!/usr/bin/env python3
"""idmc_mcp.py - Informatica managed MCP servers headless: list the org's registry, list / create / delete an
OAuth client (secret written straight to a 0600 file, never printed), and call MCP tools over streamable HTTP
(JSON-RPC) with the nested-envelope and async-poll patterns.

  python idmc_mcp.py servers [--tools]        python idmc_mcp.py clients
  python idmc_mcp.py client-create --name N --contexts jobmanagement,dqverifyaddress --env-out PATH [--access-timeout 1440]
  python idmc_mcp.py client-delete <clientId>                          (both writes: --execute --expect-org <orgIdV3>)
  python idmc_mcp.py tools --server <context> [--env PATH | --auth session]
  python idmc_mcp.py call  --server <context> --tool <name> (--args-json '{..}' | --args-file f) [--nested] [--poll]
                           [--env PATH | --auth session]    (a tool can act: --execute --expect-org <orgIdV3>)

Routes. PROVEN 2026-09 (production org, 19 managed servers, ~140 tools):
  GET  https://hdm.<domain>.informaticacloud.com/a2e-mcp-asset-mgmt-svc/api/v1/mcp-servers?type=MANAGED[&expandTools=true]
       header IDS-SESSION-ID: <v3 session> -> servers[]{id, mcpServerName, serverEndpointUrl, context, toolsDetails}
  POST .../a2e-mcp-asset-mgmt-svc/api/v1/oauth2clients {"providerType":"IDMC_MCP","clientName","description",
       "credentials":{"username","password"},"accessTimeout":1440,"enabled":true,"mcpServers":[{"id","name",
       "serverEndpointUrl","context","serverPolicy":null}]} -> 201 {clientId, clientSecret (shown ONCE)}
       (bodies with mcpServersDetails / mcpServerIds / servers / resources did not create a client; accessTimeout
       1440 gave 86,400 s tokens; the client stores the user's password, so recreate it after a password rotation)
  GET  .../oauth2clients?type=IDMC_MCP&page=1&size=50&sortBy=lastModifiedDate&sortOrder=desc&grantType=client_credentials
  Token: POST https://<domain>.informaticacloud.com/authz-service/oauth/token grant_type=client_credentials (Basic auth)
  MCP:   POST https://mcp.<domain>.informaticacloud.com/mcp-servers/public/<context>  Authorization: Bearer <token>,
         Accept: application/json, text/event-stream; initialize (protocolVersion 2025-06-18) -> keep the
         Mcp-Session-Id header -> notifications/initialized -> tools/list | tools/call. Answers may be SSE 'data:' lines.
  --auth session (PROVEN 2026-09 for the Data Quality agent server): Bearer = identity-service JWT client_id=idmc_api
         minted from the v3 session, plus IDS-SESSION-ID; its tools/call takes a NESTED JSON-RPC envelope (--nested) and
         runs async: poll get_skill_execution_updates {conversation_id, message_id, cursor} until has_more=false (--poll).
ADAPTED / UNTESTED: client-delete (the DELETE route answered in cleanup code; its status was not recorded).
Results are unwrapped from result.structuredContent, else content[0].text, up to three nested envelopes.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import idmc_http as H  # noqa: E402
from idmc_session import LoginError, Session, _inside_kb  # noqa: E402

MGMT = "/a2e-mcp-asset-mgmt-svc/api/v1"
LIST_CLIENTS = f"{MGMT}/oauth2clients?type=IDMC_MCP&page=1&size=50&sortBy=lastModifiedDate&sortOrder=desc&grantType=client_credentials"


def read_env(path):
    if not path or not os.path.exists(path):
        H.die("give --env PATH (the 0600 file written by client-create) or --auth session")
    if _inside_kb(path):
        H.die("the OAuth env file must live outside the KB")
    return dict(ln.strip().split("=", 1) for ln in open(path, encoding="utf-8") if "=" in ln and not ln.startswith("#"))


def parse(r):
    t = r.text.strip()
    if t.startswith("{"):
        return r.json({}) or {}
    for line in t.splitlines():
        if line.startswith("data:"):
            try:
                return json.loads(line[5:].strip())
            except ValueError:
                pass
    return {"_raw": r.head(300), "_http": r.status}


def unwrap(j):
    for _ in range(3):
        res = j.get("result") if isinstance(j, dict) else None
        if not isinstance(res, dict):
            return j
        if isinstance(res.get("structuredContent"), dict):
            return res["structuredContent"]
        c = res.get("content") or []
        txt = c[0].get("text") if c and isinstance(c[0], dict) else None
        try:
            j = json.loads(txt) if txt else res
        except ValueError:
            return {"text": txt}
    return j


class Mcp:
    def __init__(self, url, auth):
        self.url, self.auth, self.sid, self.n = url, auth, None, 0

    def post(self, msg, retry=True):
        h = {"Accept": "application/json, text/event-stream", "MCP-Protocol-Version": "2025-06-18", **self.auth(False)}
        if self.sid:
            h["Mcp-Session-Id"] = self.sid
        r = H.request("POST", self.url, h, body=msg, timeout=180)
        if r.status == 401 and retry:
            self.auth(True)
            return self.post(msg, False)
        self.sid = next((v for k, v in r.headers.items() if k.lower() == "mcp-session-id"), self.sid)
        return r, parse(r)

    def init(self):
        r, _ = self.post({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18",
                          "capabilities": {}, "clientInfo": {"name": "idmc-script-library", "version": "1"}}})
        if not r.ok:
            H.die(f"initialize HTTP {r.status} {r.head(200)}")
        self.post({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return self

    def call(self, tool, args, nested=False):
        self.n += 1
        if nested:
            args = {"jsonrpc": "2.0", "id": str(uuid.uuid4()), "method": "tools/call", "params": {"name": tool, "arguments": args}}
        r, j = self.post({"jsonrpc": "2.0", "id": 100 + self.n, "method": "tools/call", "params": {"name": tool, "arguments": args}})
        return r, unwrap(j)


def make_client(S, a):
    ctx = a.server
    if a.auth == "session":
        url = S.hosts()["mcp"] + "/mcp-servers/public/" + ctx

        def auth(force):
            if force:
                S._jwt.clear()
            return {"Authorization": "Bearer " + S.jwt("idmc_api", "v3"), "IDS-SESSION-ID": S.v3()["sid"]}
        return Mcp(url, auth), None
    env, tok = read_env(a.env), {}

    def auth(force):
        if force or not tok or time.time() > tok["exp"] - 300:
            basic = base64.b64encode(f"{env['IDMC_CLIENT_ID']}:{env['IDMC_CLIENT_SECRET']}".encode()).decode()
            r = H.request("POST", env["IDMC_TOKEN_URL"], {"Authorization": "Basic " + basic}, raw=b"grant_type=client_credentials",
                          ctype="application/x-www-form-urlencoded", timeout=30)
            j = r.json({}) or {}
            if not j.get("access_token"):
                H.die(f"OAuth token HTTP {r.status} {r.head(160)}")
            tok.update(v=j["access_token"], exp=time.time() + float(j.get("expires_in", 3600)))
        return {"Authorization": "Bearer " + tok["v"]}
    return Mcp(env["MCP_BASE"].rstrip("/") + "/" + ctx, auth), env


def main():
    H.safe_console()
    ap = argparse.ArgumentParser(description="managed MCP servers")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("servers").add_argument("--tools", action="store_true")
    sub.add_parser("clients")
    cc = H.add_gate_args(sub.add_parser("client-create"))
    for f in ("--name", "--contexts", "--env-out"):
        cc.add_argument(f, required=True)
    cc.add_argument("--access-timeout", type=int, default=1440)
    cc.add_argument("--desc", default="")
    H.add_gate_args(sub.add_parser("client-delete")).add_argument("client_id")
    for c in ("tools", "call"):
        p = H.add_gate_args(sub.add_parser(c)) if c == "call" else sub.add_parser(c)
        p.add_argument("--server", required=True, help="the server context, e.g. dqverifyaddress")
        p.add_argument("--env", default=os.environ.get("IDMC_MCP_ENV_FILE"))
        p.add_argument("--auth", choices=["oauth", "session"], default="oauth")
        if c == "call":
            p.add_argument("--tool", required=True)
            p.add_argument("--args-json")
            p.add_argument("--args-file")
            p.add_argument("--nested", action="store_true")
            p.add_argument("--poll", action="store_true")
    a = ap.parse_args()
    try:
        S = Session()
        if a.cmd == "servers":
            r = S.get("hdm", f"{MGMT}/mcp-servers?type=MANAGED" + ("&expandTools=true" if a.tools else ""))
            for s in (r.json({}) or {}).get("servers") or []:
                tools = [t.get("name") for t in (s.get("toolsDetails") or {}).get("tools") or []]
                print(f"  {s.get('context', ''):28} {s.get('mcpServerName', '')[:38]:38} tools={(s.get('toolsDetails') or {}).get('count')}"
                      + (f" {tools}" if a.tools else ""))
            print(f"HTTP {r.status}")
            return
        if a.cmd == "clients":
            r = S.get("hdm", LIST_CLIENTS)
            for c in (r.json({}) or {}).get("content") or []:
                print(f"  {c.get('clientName'):30} id={str(c.get('clientId'))[:4]}... enabled={c.get('enabled')} "
                      f"accessTimeout={c.get('accessTimeout')}")
            print(f"HTTP {r.status}")
            return
        if a.cmd == "tools":
            m, _ = make_client(S, a)
            _, j = m.init().post({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
            for t in (j.get("result") or {}).get("tools") or []:
                print(f"  {t.get('name'):40} {str(t.get('description'))[:90]}")
            return
        gate = H.WriteGate(a, S)
        if a.cmd == "call" and a.auth == "oauth" and gate.execute:
            env = read_env(a.env)
            if env.get("IDMC_ORG_ID") and env["IDMC_ORG_ID"] != a.expect_org:
                H.die(f"the OAuth client in {a.env} belongs to org {env['IDMC_ORG_ID']}, not --expect-org {a.expect_org}")
        gate.guard()
        if a.cmd == "client-create":
            if _inside_kb(a.env_out) or os.path.exists(a.env_out):
                H.die("--env-out must be a NEW file outside the KB (the secret is shown only once)")
            if any(c.get("clientName") == a.name for c in (S.get("hdm", LIST_CLIENTS).json({}) or {}).get("content") or []):
                H.die(f"client '{a.name}' exists; its secret cannot be read again: delete and recreate it deliberately")
            reg = {s.get("context"): s for s in (S.get("hdm", f"{MGMT}/mcp-servers?type=MANAGED").json({}) or {}).get("servers") or []}
            want = [c.strip() for c in a.contexts.split(",") if c.strip()]
            miss = [c for c in want if c not in reg]
            if miss:
                H.die(f"unknown server context(s) {miss}; see 'servers'")
            body = {"providerType": "IDMC_MCP", "clientName": a.name, "description": a.desc,
                    "credentials": {"username": S.cfg["IDMC_USER"], "password": S.cfg["IDMC_PASS"]},
                    "accessTimeout": a.access_timeout, "enabled": True,
                    "mcpServers": [{"id": reg[c]["id"], "name": reg[c].get("mcpServerName"), "context": c,
                                    "serverEndpointUrl": reg[c].get("serverEndpointUrl"), "serverPolicy": None} for c in want]}
            r = gate.send(f"create OAuth client {a.name}", "hdm", "POST", f"{MGMT}/oauth2clients", body=body)
            if r is not None:
                j = r.json({}) or {}
                if r.status not in (200, 201) or not j.get("clientSecret"):
                    H.die(f"create failed HTTP {r.status} (answer redacted above)")
                h = S.hosts()
                fd = os.open(a.env_out, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, "w") as f:
                    f.write(f"IDMC_CLIENT_ID={j['clientId']}\nIDMC_CLIENT_SECRET={j['clientSecret']}\n"
                            f"IDMC_TOKEN_URL={h['login']}/authz-service/oauth/token\nMCP_BASE={h['mcp']}/mcp-servers/public/\n"
                            f"IDMC_ORG_ID={S.v2().get('orgUuid')}\n")
                print(f"  client created; id {str(j['clientId'])[:4]}...; secret written to {a.env_out} (0600), never printed")
        elif a.cmd == "client-delete":
            r = gate.send(f"delete OAuth client {a.client_id[:4]}...", "hdm", "DELETE", f"{MGMT}/oauth2clients/{a.client_id}")
            if r is not None:
                left = [c for c in (S.get("hdm", LIST_CLIENTS).json({}) or {}).get("content") or [] if c.get("clientId") == a.client_id]
                print(f"  read-back: {'STILL PRESENT' if left else 'GONE'}")
        else:
            args = json.load(open(a.args_file, encoding="utf-8")) if a.args_file else json.loads(a.args_json or "{}")
            m, _ = make_client(S, a)
            print(f"[{'EXECUTE' if gate.execute else 'DRY-RUN'}] tools/call {a.tool} on {a.server}: {H.preview(args, 600)}")
            if not gate.execute:
                return
            r, pay = m.init().call(a.tool, args, a.nested)
            print(f"  HTTP {r.status}: {H.preview(pay, 3000)}")
            ctx = (pay or {}).get("context") or {} if isinstance(pay, dict) else {}
            cur = ((pay or {}).get("pagination") or {}).get("cursor", "0") if isinstance(pay, dict) else "0"
            for _ in range(180 if a.poll and ctx.get("conversation_id") else 0):
                time.sleep(1)
                _, pay = m.call("get_skill_execution_updates", {"conversation_id": ctx["conversation_id"],
                                "message_id": ctx.get("message_id"), "cursor": cur, "events": True, "reasoning": True}, a.nested)
                if not isinstance(pay, dict) or pay.get("error"):
                    print("  poll error:", H.preview(pay, 300))
                    break
                for it in pay.get("items") or []:
                    print(f"   [{it.get('responseType')}] {H.preview(it.get('payload'), 400)}")
                pg = pay.get("pagination") or {}
                cur = pg.get("cursor", cur)
                if not pg.get("has_more", False):
                    print(f"  done: status={pay.get('status')}")
                    break
    except (LoginError, RuntimeError, KeyError) as e:
        H.die(f"{type(e).__name__}: {e}", 3)


if __name__ == "__main__":
    main()
