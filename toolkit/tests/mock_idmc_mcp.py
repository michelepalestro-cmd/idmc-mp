#!/usr/bin/env python3
"""mock_idmc_mcp.py - a local stand-in for Informatica's OAuth token endpoint and three managed MCP servers, so the MCP
bridge can be tested with no IDMC org and no network.

    python3 toolkit/tests/mock_idmc_mcp.py [--port 0]   # prints the base URL, serves until killed

What it imitates (from the routes in toolkit/lib/idmc_mcp.py): Basic-auth client credentials at /authz-service/oauth/token;
streamable HTTP JSON-RPC at /mcp-servers/public/<context> with an Mcp-Session-Id that must be sent back; answers as JSON
or as SSE 'data:' lines; the first token expires early, so the client has to fetch a new one after a 401.
Stdlib only.
"""
import argparse
import base64
import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CLIENT_ID, CLIENT_SECRET = "mock-client", "mock-secret-do-not-print"
TOOLS = {
    "jobmanagement": [
        {"name": "get_job_status", "description": "Status of a job run.",
         "inputSchema": {"type": "object", "properties": {"job_id": {"type": "string"}}, "required": ["job_id"]}},
        {"name": "run_mapping_task", "description": "Run a mapping task.",
         "inputSchema": {"type": "object", "properties": {"task_name": {"type": "string"}}}},
    ],
    "dqverifyaddress": [
        {"name": "verify_address", "description": "Verify one address.",
         "inputSchema": {"type": "object", "properties": {"address": {"type": "string"}}}},
    ],
    "connectionmanagement": [
        {"name": "list_connections", "description": "List connections.", "inputSchema": {"type": "object", "properties": {}}},
        {"name": "delete_connection", "description": "Delete a connection.",
         "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}}}},
        {"name": "get_object_metadata_with_flatfile_attrs", "description": "A long tool name.",
         "inputSchema": {"type": "object", "properties": {}}},
    ],
}
SSE = {"connectionmanagement"}                     # this server answers as an event stream


class State:
    def __init__(self):
        self.tokens, self.sessions, self.calls, self.lock = {}, set(), [], threading.Lock()
        self.issued = 0


def handler(state):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def reply(self, code, obj=None, headers=None, sse=False):
            body = b""
            if obj is not None:
                body = (("event: message\ndata: " + json.dumps(obj) + "\n\n") if sse else json.dumps(obj)).encode()
            self.send_response(code)
            self.send_header("Content-Type", "text/event-stream" if sse else "application/json")
            for k, v in (headers or {}).items():
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            raw = self.rfile.read(int(self.headers.get("Content-Length") or 0))
            if self.path == "/authz-service/oauth/token":
                want = "Basic " + base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
                if self.headers.get("Authorization") != want or b"grant_type=client_credentials" not in raw:
                    return self.reply(401, {"error": "invalid_client"})
                with state.lock:
                    state.issued += 1
                    tok = "tok-%d" % state.issued
                    state.tokens[tok] = state.issued > 1     # the first token is already "expired"
                return self.reply(200, {"access_token": tok, "token_type": "bearer", "expires_in": 86400})
            prefix = "/mcp-servers/public/"
            ctx = self.path[len(prefix):] if self.path.startswith(prefix) else ""
            if ctx not in TOOLS:
                return self.reply(404, {"error": "no such server"})
            tok = (self.headers.get("Authorization") or "").replace("Bearer ", "")
            if not state.tokens.get(tok):
                return self.reply(401, {"error": "invalid_token"})
            msg = json.loads(raw or b"{}")
            method, mid = msg.get("method"), msg.get("id")
            if method == "initialize":
                sid = uuid.uuid4().hex
                state.sessions.add(sid)
                return self.reply(200, {"jsonrpc": "2.0", "id": mid, "result": {
                    "protocolVersion": "2025-06-18", "capabilities": {"tools": {}},
                    "serverInfo": {"name": ctx, "version": "mock"}}}, {"Mcp-Session-Id": sid}, sse=ctx in SSE)
            if self.headers.get("Mcp-Session-Id") not in state.sessions:
                return self.reply(400, {"error": "missing or unknown Mcp-Session-Id"})
            if mid is None:
                return self.reply(202)
            if method == "tools/list":
                return self.reply(200, {"jsonrpc": "2.0", "id": mid, "result": {"tools": TOOLS[ctx]}}, sse=ctx in SSE)
            if method == "tools/call":
                name, args = msg["params"]["name"], msg["params"].get("arguments") or {}
                state.calls.append((ctx, name, args))
                if name not in [t["name"] for t in TOOLS[ctx]]:
                    return self.reply(200, {"jsonrpc": "2.0", "id": mid, "error": {"code": -32602, "message": "unknown tool"}})
                out = {"server": ctx, "tool": name, "arguments": args, "status": "VERIFIED" if name == "verify_address" else "OK"}
                return self.reply(200, {"jsonrpc": "2.0", "id": mid, "result": {
                    "content": [{"type": "text", "text": json.dumps(out)}], "structuredContent": out}}, sse=ctx in SSE)
            return self.reply(200, {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": "method not found"}})
    return H


def start(port=0):
    """(server, base_url, state); the server runs in a daemon thread. Call server.shutdown() when done."""
    state = State()
    srv = ThreadingHTTPServer(("127.0.0.1", port), handler(state))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, "http://127.0.0.1:%d" % srv.server_address[1], state


def write_env(path, base, contexts, allow_writes=False):
    """A client file in the format idmc_mcp.py client-create writes, pointing at the mock."""
    import os
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(f"IDMC_CLIENT_ID={CLIENT_ID}\nIDMC_CLIENT_SECRET={CLIENT_SECRET}\n"
                f"IDMC_TOKEN_URL={base}/authz-service/oauth/token\nMCP_BASE={base}/mcp-servers/public/\n"
                f"IDMC_ORG_ID=mockOrg0000000000000000\nMCP_CONTEXTS={','.join(contexts)}\n"
                f"IDMC_MCP_ALLOW_WRITES={'1' if allow_writes else '0'}\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--env-out", help="also write a client file pointing at this mock")
    ap.add_argument("--allow-writes", action="store_true")
    a = ap.parse_args()
    srv, base, _ = start(a.port)
    if a.env_out:
        write_env(a.env_out, base, list(TOOLS), a.allow_writes)
    print(base, flush=True)
    threading.Event().wait()
