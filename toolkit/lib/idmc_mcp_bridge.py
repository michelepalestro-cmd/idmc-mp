#!/usr/bin/env python3
"""idmc_mcp_bridge.py - Informatica's managed MCP servers as Claude Code tools, through one local stdio MCP server.

The informatica-idmc-headless plugin starts this bridge on its own (plugin.json "mcpServers"). Until `/informatica-idmc-headless:connect-mcp` has written an
OAuth client file, it offers a single status tool that says how to connect, and makes no network call.

With the file in place it reads the server contexts listed in it, logs in with the OAuth client (client credentials),
and offers each server's tools as `<server>_<tool>` (for example `jobs_get_job_status`), forwarding calls unchanged.

  python3 idmc_mcp_bridge.py                     # stdio MCP server (what Claude Code runs)
  python3 idmc_mcp_bridge.py --check             # print the servers and tools it would offer, then exit
  python3 idmc_mcp_bridge.py --env PATH          # another client file (default: $IDMC_MCP_ENV_FILE or
                                                 # ~/.idmc_toolkit/mcp_client.env)

Safety:
  * Read-only by default: only tools whose names read (get_, list_, search_, browse_, preview_, test_, verify_, the
    agent questions and the documentation reader) are offered. Tools that change the org (create_, update_, delete_,
    run_, edit_, approve_ ...) appear only when the client file holds IDMC_MCP_ALLOW_WRITES=1, and their description
    then starts with "WRITES to IDMC". Claude Code still asks before each tool call.
  * The client file must live outside the plugin and be readable only by you (0600); the secret is never printed or
    logged. Only https hosts are called (plain http only to 127.0.0.1 / localhost, for tests).
  * The scope is the OAuth client's: it reaches only the servers it was created for, in the one org it belongs to.

Routes (the same as idmc_mcp.py): token POST <IDMC_TOKEN_URL> grant_type=client_credentials with Basic auth; each server
POST <MCP_BASE><context> JSON-RPC initialize -> Mcp-Session-Id -> notifications/initialized -> tools/list | tools/call,
answers as JSON or SSE 'data:' lines. Stdlib only.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import stat
import sys
import threading
import time
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import idmc_http as H  # noqa: E402

VERSION = "1.0.0"
PROTOCOL = "2025-06-18"
DEFAULT_ENV = os.path.join("~", ".idmc_toolkit", "mcp_client.env")
PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# short names keep Claude Code tool names (mcp__<server>__<tool>) under the 64-character limit
ALIAS = {"jobmanagement": "jobs", "connectionmanagement": "conn", "secureagentmanagement": "agent",
         "diassetpromotion": "promo", "cdgccatalogenrichment": "catedit", "cdgccatalogdiscovery": "catfind",
         "cdgcsearchmetadata": "catsearch", "cdgcdataqualityscore": "dqscore", "dataqualityagent": "dqagent",
         "dqverifyaddress": "addr", "searchcustomer": "cust", "dataprovisioning": "prov", "usermanagement": "users",
         "ipumanagement": "ipu", "troubleshooting": "trouble", "auditmanagement": "audit", "logmanagement": "logs",
         "datamanagementorchestrator": "claire", "dataexplorationagent": "explore", "ordermanagement": "orders",
         "cdgccatalogassethistory": "cathist", "policymanagement": "policy", "idmcassetdocumentation": "docs"}
READ_RE = re.compile(r"^(get|list|search|browse|preview|test|verify|describe|read|find|fetch|lookup|idmc)_|"
                     r"^(data_explore|master_data_explore|orchestrate|orchestrate_master_data_analysis|data_profiling|"
                     r"data_quality_analysis|data_quality_rule_recommendation|new_conversation|working)$")
STATUS_TOOL = "idmc_mcp_status"
MAX_NAME = 38   # Claude Code adds "mcp__plugin_informatica-idmc-headless_idmc__" (26 characters); tool names may total 64


def log(msg):
    """stderr only: stdout carries the protocol."""
    print("[idmc-mcp-bridge] " + msg, file=sys.stderr, flush=True)


def is_read(tool):
    ann = tool.get("annotations") or {}
    if ann.get("readOnlyHint") is True:
        return True
    if ann.get("destructiveHint") is True:
        return False
    return bool(READ_RE.search(tool.get("name") or ""))


def short_name(ctx, tool):
    n = f"{ALIAS.get(ctx, ctx[:12])}_{tool}"
    n = re.sub(r"[^A-Za-z0-9_-]", "_", n)
    return n if len(n) <= MAX_NAME else n[:MAX_NAME - 7] + "_" + hashlib.sha256(n.encode()).hexdigest()[:6]


def safe_url(u):
    p = urllib.parse.urlparse(u or "")
    return p.scheme == "https" or (p.scheme == "http" and p.hostname in ("127.0.0.1", "localhost"))


def load_env(path):
    """(env dict, problem). Problem is a plain sentence for the status tool, or None."""
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        return None, ("No MCP client file yet. Run /informatica-idmc-headless:connect-mcp in Claude Code to create one "
                      "(expected at %s)." % path)
    real = os.path.realpath(path)
    if real == PLUGIN_ROOT or real.startswith(PLUGIN_ROOT + os.sep):
        return None, "The MCP client file must live outside the plugin folder; move it to ~/.idmc_toolkit/."
    if os.name == "posix" and stat.S_IMODE(os.stat(path).st_mode) & 0o077:
        return None, "The MCP client file %s is readable by others: run chmod 600 on it, then restart Claude Code." % path
    env = {}
    with open(path, encoding="utf-8") as f:
        for ln in f:
            if "=" in ln and not ln.lstrip().startswith("#"):
                k, v = ln.strip().split("=", 1)
                env[k.strip()] = v.strip()
    need = [k for k in ("IDMC_CLIENT_ID", "IDMC_CLIENT_SECRET", "IDMC_TOKEN_URL", "MCP_BASE", "MCP_CONTEXTS") if not env.get(k)]
    if need:
        return None, "The MCP client file is missing %s; run /informatica-idmc-headless:connect-mcp again." % ", ".join(need)
    for k in ("IDMC_TOKEN_URL", "MCP_BASE"):
        if not safe_url(env[k]):
            return None, "%s in the MCP client file is not an https address." % k
    return env, None


def parse(r):
    t = r.text.strip()
    if t.startswith("{"):
        return r.json({}) or {}
    last = {}
    for line in t.splitlines():
        if line.startswith("data:"):
            try:
                last = json.loads(line[5:].strip())
            except ValueError:
                continue
            if isinstance(last, dict) and ("result" in last or "error" in last):
                return last
    return last or {"_http": r.status}


class Token:
    def __init__(self, env):
        self.env, self.value, self.exp, self.lock = env, None, 0.0, threading.Lock()

    def get(self, force=False):
        with self.lock:
            if force or not self.value or time.time() > self.exp - 300:
                basic = base64.b64encode(f"{self.env['IDMC_CLIENT_ID']}:{self.env['IDMC_CLIENT_SECRET']}".encode()).decode()
                r = H.request("POST", self.env["IDMC_TOKEN_URL"], {"Authorization": "Basic " + basic},
                              raw=b"grant_type=client_credentials", ctype="application/x-www-form-urlencoded", timeout=30)
                j = r.json({}) or {}
                if not j.get("access_token"):
                    raise RuntimeError("OAuth token refused (HTTP %s). The client may be disabled or deleted, or the "
                                       "password of the user who created it changed: run /informatica-idmc-headless:connect-mcp again." % r.status)
                self.value, self.exp = j["access_token"], time.time() + float(j.get("expires_in", 3600))
            return self.value


class Remote:
    """One managed server: streamable HTTP JSON-RPC with its own MCP session."""

    def __init__(self, ctx, url, token):
        self.ctx, self.url, self.token, self.sid, self.n = ctx, url, token, None, 0
        self.lock = threading.Lock()

    def _post(self, msg, again=True):
        h = {"Accept": "application/json, text/event-stream", "MCP-Protocol-Version": PROTOCOL,
             "Authorization": "Bearer " + self.token.get()}
        if self.sid:
            h["Mcp-Session-Id"] = self.sid
        r = H.request("POST", self.url, h, body=msg, timeout=180)
        if r.status == 401 and again:
            self.token.get(force=True)
            return self._post(msg, False)
        if r.status == 404 and self.sid and again and msg.get("method") != "initialize":
            self.sid = None                       # the server dropped our session: start a new one, once
            self._init()
            return self._post(msg, False)
        self.sid = next((v for k, v in r.headers.items() if k.lower() == "mcp-session-id"), self.sid)
        return r

    def _init(self):
        r = self._post({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                        "params": {"protocolVersion": PROTOCOL, "capabilities": {},
                                   "clientInfo": {"name": "informatica-idmc-headless-bridge", "version": VERSION}}})
        if not r.ok:
            raise RuntimeError("%s: initialize answered HTTP %s" % (self.ctx, r.status))
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def request(self, method, params):
        with self.lock:
            if not self.sid:
                self._init()
            self.n += 1
            r = self._post({"jsonrpc": "2.0", "id": 100 + self.n, "method": method, "params": params})
            j = parse(r)
            if "error" in j:
                raise RuntimeError("%s %s: %s" % (self.ctx, method, json.dumps(j["error"])[:400]))
            if not r.ok or "result" not in j:
                raise RuntimeError("%s %s: HTTP %s %s" % (self.ctx, method, r.status, r.head(200)))
            return j["result"]


class Bridge:
    def __init__(self, env_path):
        self.env_path = env_path
        self.tools, self.route, self.notes, self.loaded = [], {}, [], False
        self.allow_writes, self.org = False, ""

    def load(self):
        if self.loaded:
            return
        self.loaded = True
        env, problem = load_env(self.env_path)
        if problem:
            self.notes.append(problem)
            return
        self.allow_writes = env.get("IDMC_MCP_ALLOW_WRITES") == "1"
        self.org = env.get("IDMC_ORG_ID", "")
        token = Token(env)
        base = env["MCP_BASE"].rstrip("/") + "/"
        hidden = 0
        for ctx in [c.strip() for c in env["MCP_CONTEXTS"].split(",") if c.strip()]:
            if not re.fullmatch(r"[a-z0-9_-]+", ctx):
                self.notes.append("skipped server context %r (not a context name)" % ctx)
                continue
            rem = Remote(ctx, base + ctx, token)
            try:
                listed = rem.request("tools/list", {}).get("tools") or []
            except RuntimeError as e:
                self.notes.append("server %s unavailable: %s" % (ctx, e))
                continue
            for t in listed:
                read = is_read(t)
                if not read and not self.allow_writes:
                    hidden += 1
                    continue
                name = short_name(ctx, t.get("name", ""))
                desc = (t.get("description") or "").strip()
                prefix = "[Informatica %s] " % ctx if read else "WRITES to IDMC (%s). " % ctx
                self.tools.append({"name": name, "description": (prefix + desc)[:1000],
                                   "inputSchema": t.get("inputSchema") or {"type": "object", "properties": {}},
                                   "annotations": {"readOnlyHint": read, "title": "%s %s" % (ctx, t.get("name"))}})
                self.route[name] = (rem, t.get("name"))
            self.notes.append("server %s: %d tools" % (ctx, len(listed)))
        if hidden:
            self.notes.append("%d tools that change the org are hidden (read-only mode)" % hidden)

    def status(self):
        lines = ["IDMC MCP bridge %s" % VERSION]
        if self.org:
            lines.append("org: %s" % self.org)
        lines.append("mode: %s" % ("read and write" if self.allow_writes else "read-only"))
        lines += self.notes
        lines.append("tools offered: %d" % len(self.tools))
        return "\n".join(lines)

    def list_tools(self):
        self.load()
        st = {"name": STATUS_TOOL, "description": "Shows whether Informatica's MCP servers are connected, which servers "
              "and how many tools, and how to connect them (/informatica-idmc-headless:connect-mcp). Makes no change.",
              "inputSchema": {"type": "object", "properties": {}}, "annotations": {"readOnlyHint": True}}
        return [st] + self.tools

    def call(self, name, args):
        self.load()
        if name == STATUS_TOOL:
            return {"content": [{"type": "text", "text": self.status()}]}
        if name not in self.route:
            return {"isError": True, "content": [{"type": "text", "text": "Unknown or hidden tool %s. %s" % (name, self.status())}]}
        rem, tool = self.route[name]
        try:
            res = rem.request("tools/call", {"name": tool, "arguments": args or {}})
        except RuntimeError as e:
            return {"isError": True, "content": [{"type": "text", "text": str(e)}]}
        if not isinstance(res, dict) or not res.get("content") and "structuredContent" not in res:
            res = {"content": [{"type": "text", "text": json.dumps(res)[:20000]}]}
        return res


def serve(bridge):
    out = sys.stdout

    def send(obj):
        out.write(json.dumps(obj) + "\n")
        out.flush()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            send({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}})
            continue
        mid, method, params = msg.get("id"), msg.get("method"), msg.get("params") or {}
        if mid is None:                           # notifications need no answer
            continue
        try:
            if method == "initialize":
                res = {"protocolVersion": params.get("protocolVersion") or PROTOCOL,
                       "capabilities": {"tools": {"listChanged": False}},
                       "serverInfo": {"name": "informatica-idmc-headless", "version": VERSION},
                       "instructions": "Informatica IDMC managed MCP servers for the org in the OAuth client file. "
                                       "Call idmc_mcp_status first if a tool is missing."}
            elif method == "ping":
                res = {}
            elif method == "tools/list":
                res = {"tools": bridge.list_tools()}
            elif method == "tools/call":
                res = bridge.call(params.get("name"), params.get("arguments"))
            else:
                send({"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": "method not found: %s" % method}})
                continue
            send({"jsonrpc": "2.0", "id": mid, "result": res})
        except Exception as e:  # noqa: BLE001 - one bad call must not stop the bridge
            log("%s failed: %s: %s" % (method, type(e).__name__, e))
            send({"jsonrpc": "2.0", "id": mid, "error": {"code": -32603, "message": "%s: %s" % (type(e).__name__, e)}})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--env", default=os.environ.get("IDMC_MCP_ENV_FILE") or DEFAULT_ENV)
    ap.add_argument("--check", action="store_true", help="print what would be offered, then exit")
    a = ap.parse_args()
    b = Bridge(a.env)
    if a.check:
        H.safe_console()
        b.load()
        print(b.status())
        for t in b.tools:
            print("  %-38s %s" % (t["name"], "read" if t["annotations"]["readOnlyHint"] else "WRITE"))
        return 0 if b.tools else 1
    serve(b)
    return 0


if __name__ == "__main__":
    sys.exit(main())
