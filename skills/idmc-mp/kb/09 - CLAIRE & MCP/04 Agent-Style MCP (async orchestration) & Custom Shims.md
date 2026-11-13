# Agent-style MCP (async orchestration) and custom shims

**Answers:** How do I drive Informatica's asynchronous agent tools (submit, poll, answer probes)? Why does a CLAIRE MCP
server list 0 tools? How do I build a safe stdio shim, a gateway over the managed servers, or my own MCP server over my
data? How do I wire MCP servers into Claude Code?

**Read when:** calling `OrchestratorSkill`, `orchestrate`, `data_explore` or the DQ agent from code; writing or reviewing
a shim; registering MCP servers in Claude Code; giving outside agents one MCP endpoint.

**Key rules:**
- Agent-style tools are asynchronous: submit, then poll (`working` with no arguments, or `get_skill_execution_updates`
  with a cursor) until a sentinel or `has_more=false` (L-MCP-034, L-MCP-037, L-MCP-044).
- Call `new_conversation` first; never invent a `conversation_id`, and pass the returned one on every follow-up
  (L-MCP-036).
- A server listing 0 tools is usually a local config pointed at another org: print the identity URL, user and org first
  (L-MCP-033).
- Shims take endpoints and credentials from the environment, check the login status, and stop after one rejected login
  (L-MCP-032).
- Review any third-party shim for disabled TLS verification (`CERT_NONE`, `check_hostname=False`, `verify=False`,
  `_create_unverified_context`) before wiring it (L-MCP-124).
- Outside agents reach IDMC through one aggregating gateway that holds an OAuth client, caches tool inventories and sets
  client timeouts (L-MCP-082, L-MCP-083, L-MCP-084).

**Related:** [01 Managed MCP Servers](<01 Managed MCP Servers (catalog & access).md>) ·
[02 MCP Auth & OAuth Clients](<02 MCP Auth & OAuth Clients.md>) ·
[03 CLAIRE GPT - Prompting Rules](<03 CLAIRE GPT - Prompting Rules & Patterns.md>) ·
[CLAIRE DQ Agent](<../06 - Data Quality & Profiling/03 CLAIRE DQ Agent - File-Based Profiling & Cleansing.md>) · [Lessons: CLAIRE & MCP](<../13 - Lessons Learned/09 CLAIRE & MCP.md>)

**Last verified:** 2026-10-03

> **Summary.** Two asynchronous contracts exist: (1) the **CLAIRE agent MCP**
> (`<claire_api_url>/claire-orchestrator-ai-agent/api/v1/mcp`): `new_conversation` → `OrchestratorSkill` /
> `MdmOrchestratorSkill` → `working` (**no arguments**) → sentinels (`ANSWER:`, `PROBE:`, `done`, `Error:`); (2) the
> **managed agent servers** (`dataqualityagent`, `datamanagementorchestrator`, `dataexplorationagent`): submit →
> `get_skill_execution_updates` with a cursor until `has_more=false`, with a `HUMAN_PROBE` you answer in the same
> conversation. Shims hide token refresh, envelopes and polling; register them with `claude mcp add` (L-MCP-041).
> References: [MCP operating reference](<../12 - Reference Library/IDMC API & MCP Reference/content/56-mcp-operating.json>),
> [custom fleet reference](<../12 - Reference Library/IDMC API & MCP Reference/content/57-custom-mcp-fleet.json>),
> [Claude Working Methods & Tooling](<../14 - Claude Working Methods & Tooling/>).

---

## 1. The two asynchronous contracts

| | CLAIRE agent MCP (orchestrator) | Managed agent servers (DQ agent, orchestrator, exploration) |
|---|---|---|
| Endpoint | `<claire_api_url>/claire-orchestrator-ai-agent/api/v1/mcp`: a path on the CLAIRE API host | the registry's `serverEndpointUrl`, e.g. `https://mcp.<domain>.informaticacloud.com/mcp-servers/public/dataqualityagent` |
| Auth | identity JWT (two calls; 30 min, self-refreshed) | Bearer JWT + `IDS-SESSION-ID`, or an OAuth token |
| Start | `new_conversation` (no arguments), then a skill with `prompt` | the skill tool (`data_quality_cleansing`, `orchestrate`,...) with `prompt` (+ `conversation_id`, `deferred`, `events`, `reasoning`) |
| Poll | `working` with **no arguments**, ~1 s interval, cursor-based server-side | `get_skill_execution_updates` with `conversation_id`, `message_id`, `cursor`, ~`poll_interval_ms` |
| Stop on | a sentinel line: `ANSWER:`, `PROBE:`, `done`, `Error:` | `pagination.has_more == false` and a terminal `status` (SUCCESS, PARTIAL_SUCCESS, FAILED), or a `HUMAN_PROBE` item |
| Answer | `ANSWER:` JSON with `responseType=FINAL_BUNDLE` (`artifact`, `plan`, `human_probe`) | items of type `ARTIFACT` (with `payload.summary` / `payload.data`), plus `EXECUTION_INSIGHT`, `REASONING_TRACE`, `END_OF_ANSWER` |
| Clarification | `PROBE:`: ask the human, stop polling | `HUMAN_PROBE`: answer "yes" (or the detail) with the same skill and `conversation_id`, then poll again |
| Envelope | normal `tools/call` | DQ agent: arguments = a full inner JSON-RPC `tools/call`; answers nest JSON-RPC inside text (§3.3) |

---

## 2. The CLAIRE agent MCP, step by step

### 2.1 Wiring (L-MCP-041)

- **Config keys:** `claire_api_url`, `identity_url`, `username`, `password`, `client_id`. Take them from config or
  environment, never inline and never in chat.
- **Auth chain (two calls):**
  1. `POST <identity_url>/api/v1/Login` → the session id (read `userInfo.sessionId`, `sessionId` or `session_id`);
  2. `GET <identity_url>/api/v1/jwt/Token?client_id=<id>&nonce=<fresh uuid>` with `IDS-SESSION-ID: <sessionId>` →
     `jwt_token`, valid 30 minutes. The shim refreshes it itself.
- **Endpoint:** `<claire_api_url>/claire-orchestrator-ai-agent/api/v1/mcp`. The agent is a **path** on the CLAIRE API
  host, not its own hostname.
- **Two registrations:** Informatica publishes a `claire-idmc-agent` skill (SKILL.md, a Python MCP shim and a setup
  script) (L-MCP-042). The *skill* tells Claude how to call; the *MCP server* (the shim, registered with `claude mcp add`)
  is the callable. Keep both. Without the server, the tools do not exist.

### 2.2 Tools (live enumeration)

| Tool | Arguments | Role |
|---|---|---|
| `new_conversation` | none | the first action of every chat session; returns a fresh conversation |
| `OrchestratorSkill` | `prompt` (required), `conversation_id`, `name`, `external_id`, `artifacts`, `history`, `reasoning`, `events` | general orchestration: metadata discovery, exploration, DQ, rule generation, cleansing, profiling, enrichment, integration, product docs |
| `MdmOrchestratorSkill` | same | mastered entities, business entities, golden records, hierarchies, match/merge, cross-entity relationships |
| `working` | **none** (`properties={}`) | poll for progress; cursor-based, returns only what queued since the last call |

### 2.3 The four-step sequence (L-MCP-034)

1. `new_conversation`: **first**, before any skill call, in every chat session. Do not call it again mid-conversation
   unless you are resetting on purpose.
2. `OrchestratorSkill` or `MdmOrchestratorSkill` with one specific prompt. It returns immediately: it is a submission.
3. `working` with **no arguments**, at about 1-second intervals. Never skip calls, because the cursor only moves forward.
4. **Stop on a sentinel** (L-MCP-035):

| Line starts with | Meaning | Do |
|---|---|---|
| `ANSWER:` | final JSON, `responseType=FINAL_BUNDLE` with `artifact`, `plan`, `human_probe` | render it and stop |
| `PROBE:` | CLAIRE needs clarification (usually a vague prompt) | ask the human and stop |
| `done` | finished with no further output | stop |
| `Error: <msg>` | the task failed | report it and stop; do not retry blindly |
| `Still working...` | nothing yet | poll again **silently** |
| any other text | live progress or reasoning | show it verbatim, keep polling |

### 2.4 Argument rules that silently lose context (L-MCP-036)

- **Omit `conversation_id` on the first skill call** and never invent one. The server mints it and returns it at
  `response.context.conversation_id`. Pass that exact value on every follow-up. Omitting it on a follow-up silently
  starts a new session and drops all prior context; no error is raised.
- Send `conversation_id` **or** `history` (a list of `{role, content}`, with role user | assistant | system), never both.
- `artifacts` may contain only names CLAIRE already returned. A guessed name is a fabricated reference.
- Vague prompts come back as a probe and cost a round trip. Name the source, the entity and the action.
- `reasoning=true` exposes *why* (REASONING_TRACE items); `events=true` exposes *what ran* (EXECUTION_INSIGHT items).
- **`working` takes no arguments (L-MCP-037).** An earlier skill signature and catalog row passed `conversation_id`
  to it. The live schema (`properties={}`) corrected that (was L-MCP-074, superseded by L-MCP-037).

### 2.5 Host-app behaviour and loop bugs

- **Claude Desktop keeps MCP servers alive across chats (L-MCP-039).** "New Chat" does not reset CLAIRE's server-side
  context, which is why `new_conversation` must come first. Skipping it leaks context between chats.
- **`working` is a temporary polling shim (L-MCP-038).** The server documents it as local, to be removed once native
  progress streaming ships. Put polling behind one function, so the swap is a single edit.
- **Most integration bugs are loop bugs, not auth bugs:** a self-generated conversation id; dropping it on the second
  call; passing arguments to `working`; surfacing "Still working..." to the user; stopping before a sentinel.

### 2.6 Rendering the `ANSWER:` bundle by `viewType` (L-MCP-040)

| `viewType` | Render as |
|---|---|
| `GridView` | a table: headers from `schema_definitions[].label` in order; each `items[]` row mapped by `fieldName` position; `key_insights` as a callout below |
| `DataExploreResult` (or null) | the same grid with null cells as an em dash; `execution_context.generated_sql` in a sql fence; a footer `Rows: <row_count_total> \| Execution time: <execution_time_ms>ms` |
| `PropertiesView` | a two-column Property \| Value table, with subheadings per group |
| `GraphView` | lineage arrows (`Source -> Transform -> Target`), one node per line, indented branches |
| `AnalyticsView` | the key metric in bold, then trends; minimal commentary |
| `TreeView` | an indented tree (catalog / schema / folder) |
| `BlockText` | as-is |

### 2.7 What it can do

The CLAIRE agent MCP is **read-only** in practice: it could not register agents, create connections or author assets
(L-MCP-010). It answers from the CDGC catalog and the MDM repository only, so sources that were never scanned
return nothing (L-MCP-043). Whether it writes anything at all through cleansing or "integration" routes is unverified.

---

## 3. The managed agent servers

### 3.1 Submit, then poll `get_skill_execution_updates` (L-MCP-044)

```
tools/call <skill>            {"prompt":"...","conversation_id":"<cid, omit to start>","name":"<asset>",
                               "external_id":"<catalog asset id>","deferred":true,"events":true,"reasoning":true}
→ {"context":{"conversation_id":"<cid>","message_id":"<mid>"}, "status":"...", "items":[...], "pagination":{...}}

tools/call get_skill_execution_updates
                              {"conversation_id":"<cid>","message_id":"<mid>","cursor":"<cursor>","events":true,"reasoning":true}
→ {"status":"IN_PROGRESS|SUCCESS|PARTIAL_SUCCESS|FAILED","items":[...],
   "pagination":{"cursor":"<next>","has_more":<bool>,"poll_interval_ms":1500}}
```

- Loop until `has_more` is false and the status is terminal. Sleep `poll_interval_ms` between polls, and give up after
  a deadline (~15 min for code generation).
- **`HUMAN_PROBE`:** stop polling, call the **same skill** with `{"prompt":"yes","conversation_id":"<cid>","deferred":true,...}`,
  take the new `context`, and poll again. Allow up to ~3 probe rounds.
- **Never start a second skill run** to "resume". Keep the `conversation_id` and `message_id`, and poll them.

### 3.2 Envelopes and unwrapping (L-MCP-030)

- The DQ agent wants the tool `arguments` to be a complete inner JSON-RPC `tools/call` message
  ([CLAIRE DQ Agent](<../06 - Data Quality & Profiling/03 CLAIRE DQ Agent - File-Based Profiling & Cleansing.md>) §3.1).
  If a gateway already wraps calls and the tool rejects the nested shape with a validation error, **retry once with the
  plain argument object**.
- Answers nest a JSON-RPC message inside `result.content[].text`, sometimes twice. Unwrap up to three levels (or read
  `result.structuredContent`) before you parse the payload.

### 3.3 The orchestrator and exploration servers

- `datamanagementorchestrator`: `orchestrate` and `orchestrate_master_data_analysis`. One NL prompt is routed across
  catalog, DQ, profiling, exploration and integration, with an MDM twin. It was listed live while a local CLAIRE agent
  shim showed zero tools (§4).
- `dataexplorationagent`: `data_explore` and `master_data_explore` (row, value and quality previews with generated SQL);
  `data_explore` requires `prompt`, `name` and `external_id` (L-MCP-119).
- Both follow the agent-style contract and returned the same answers as the CLAIRE GPT UI for the same prompts, in
  28-80 s, leaving no conversation in the shared UI list (L-MCP-111). Mechanics (L-MCP-112): arguments go inside a nested
  inner JSON-RPC envelope; poll `get_skill_execution_updates` with `cursor` starting at `"0"` and feed back
  `pagination.cursor`; concatenate TOKEN `content` fragments; answer a HUMAN_PROBE (`probe_message`) in the same
  conversation. Plans come back for approval rather than executing, and nothing here writes data
  ([03](<03 CLAIRE GPT - Prompting Rules & Patterns.md>) §10).

---

## 4. The "zero-skills orchestrator" trap (L-MCP-033)

**Symptom:** the CLAIRE agent MCP lists only `new_conversation` and `working` (no `OrchestratorSkill`), or `tools/list`
returns **0 tools** for the org. `working` answers "No active CLAIRE request".

**What it was:** the local MCP configuration pointed at a *different org* than the one under test, a config left over
from another engagement. It was not the platform. The org's own managed registry exposed `datamanagementorchestrator`
with a live `orchestrate` tool. A verdict that "the orchestrator has zero skills until the org owner loads them" was
wrong (overturned L-MCP-073; see L-MCP-033).

**Checklist:**

1. Print which **identity URL, username and org** the local MCP server logs into (from its config file or environment)
   and compare them with the org under test.
2. Enumerate the org's managed registry ([01](<01 Managed MCP Servers (catalog & access).md>) §2) and `tools/list` the
   orchestrator server there.
3. If the CLAIRE agent endpoint still lists 0 tools for that org, test **CLAIRE GPT in the web UI** with a scripted
   browser ([03](<03 CLAIRE GPT - Prompting Rules & Patterns.md>) §8).
4. Record which of the three was the cause, with a date.

---

## 5. Calling any MCP server over streamable HTTP (L-MCP-028)

```python
import json, urllib.request
URL = "<serverEndpointUrl or local gateway>/mcp"
H = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}   # + auth headers
sid = None
def post(body):
    global sid
    h = dict(H, **({"Mcp-Session-Id": sid} if sid else {}))
    r = urllib.request.urlopen(urllib.request.Request(URL, json.dumps(body).encode, h, method="POST"), timeout=300)
    sid = r.headers.get("Mcp-Session-Id") or sid          # keep the session header from initialize
    txt = r.read.decode(errors="replace").strip
    if txt.startswith("{"):
        return json.loads(txt)
    last = None                                           # SSE: take the last "data:" line
    for line in txt.splitlines:
        if line.startswith("data:"):
            try: last = json.loads(line[5:].strip)
            except ValueError: pass
    return last

post({"jsonrpc":"2.0","id":1,"method":"initialize",
      "params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"<client>","version":"1"}}})
post({"jsonrpc":"2.0","method":"notifications/initialized"})
tools = post({"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}})["result"]["tools"]
res = post({"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"<tool>","arguments":{...}}})
```

- `Accept` must list both `application/json` and `text/event-stream`. Answers may arrive as SSE `data:` lines.
- Keep the `Mcp-Session-Id` response header from `initialize`, and send it on every later call.
- A tool result is `result.content[]` (join the `text` parts), `result.structuredContent`, and `result.isError`.

---

## 6. Shim patterns

### 6.1 A stdio shim over a remote managed server

A small stdio MCP server that Claude launches locally, which then calls the remote server. It hides three things
(proven with the DQ agent):

1. **Token refresh.** It logs in and mints the JWT, caches both with an expiry, and refreshes ~5 minutes before the
   30-minute mark.
2. **The nested envelope.** It builds the inner JSON-RPC message for the remote tools.
3. **Polling.** It submits, polls `get_skill_execution_updates` to completion, and returns the collected text
   synchronously: progress lines, the summary, and the data.

Keep the exposed surface small. Show only the skill tools, with a simple schema (`prompt` required, optional `name`).
Hide the plumbing tools, and fall back to a static tool list if the remote `tools/list` fails.

### 6.2 Configure by environment, never by hard-coding (L-MCP-032)

- Override **every endpoint and credential** from the environment: the login URL (or the pod/domain it is derived from),
  the JWT URL, the MCP URL, and a credentials file path, or user/password variables. A shim hard-coded to one domain and
  org, with a stale password in a client config, silently served the wrong org until it was re-pointed by environment
  override.
- Log the resolved endpoint (never the credential) at startup, so the org under test is visible.

### 6.3 Handle login failures explicitly (L-MCP-032)

A shim that reads `response["userInfo"]` without checking the status throws **`KeyError 'userInfo'`** whenever the login
fails (wrong host, wrong org, stale password), and the error surfaces as a baffling tool failure.

- Check the HTTP status.
- Surface the login error code: `IDS_085` = wrong domain or pod for a valid credential; `IDS_086` = account locked.
- Stop after **one** rejected login. Repeated automated retries lock the account, and each further attempt restarts the
  lock ([Access, Auth & Orgs](<../01 - Access, Auth & Orgs/>)).

### 6.4 A local gateway that holds the OAuth client (L-MCP-031)

Run one small gateway container that:

- holds the org's OAuth client credentials (a 0600 env file);
- refreshes the token;
- exposes the managed servers' tools through **one** local streamable-HTTP endpoint, with server-prefixed names
  (`address_verify_address`, `dq_get_skill_execution_updates`,...).

Scripts and cron jobs then need no IDMC credentials. To move to another org: create a new OAuth client there
([02](<02 MCP Auth & OAuth Clients.md>)), swap the env file and the MCP base URL, rebuild with a **new image tag**, and keep
the previous tag for rollback. One gateway listed 89 tools (83 Informatica) after such a switch.

The same gateway, published behind TLS and authentication, is also **the way outside agents reach IDMC** now that
external MCP tool connections are retired on newer orgs (L-MCP-081): mount your MCP Toolbox unprefixed next to the
vendor servers and hand any MCP client the one URL (recipe L-MCP-082). Three things make it usable:

- **Cache each proxy's tool inventory (L-MCP-083).** FastMCP 2.14 resolves every `tools/call` by listing all mounted
  servers through each proxy's tool manager, which bypasses middleware: 13 upstreams cost about 26 s per call. A 300 s
  TTL cache on `_tool_manager.get_tools` brought a local tool call to 0.3 s and a vendor tool call to about 3 s.
- **Set a client timeout on every proxy (L-MCP-084).** An upstream HTTP 500 (MCP Toolbox answers a failing SQL tool
  that way) otherwise hangs the call forever.
- **Guard destructive tools by name** in a per-server middleware (connection create/update/delete, agent service
  changes, job stop/terminate): hidden from `tools/list` and refused on call.

### 6.5 Your own MCP servers over your own data

- **Read-only by construction (L-MCP-015):**
  - serve published or golden rows only, preferably from snapshots, not live primaries;
  - enforce a **hard field denylist** server-side (encrypted fields, API keys, e-mail, phone);
  - expose no write tools;
  - read live first, with a snapshot fallback;
  - stamp every answer with its `_source`.

  Tools that shell out to a CLI break on hosts where the CLI is not installed.
- **MCP Toolbox for Databases (L-MCP-016).** Run it as your own MCP server, with tools such as
  `<x>_pg_list_tables`, `<x>_pg_execute_sql`, `<x>_bq_list_dataset_ids`, `<x>_bq_list_table_ids`,
  `<x>_bq_get_table_info` and `<x>_bq_execute_sql`. Give it **read-only identities**:
  - a Postgres role with `default_transaction_read_only` and a 30 s statement timeout;
  - a GCP service account with `bigquery.dataViewer` + `bigquery.jobUser`.

  Verify that DELETE and CREATE are rejected. Toolbox runs as uid 65532 (chown its config and key files to it). Its
  `/api` endpoints are disabled, so clients use JSON-RPC on `/mcp`. Put it behind TLS with a bearer or Basic auth gate.
  The agent writes its SQL from the tool descriptions, so they must name the source's real warehouse project: after
  an app rename, a description naming a new-looking project made every query fail with 403 while the dataset listing
  still worked (L-MCP-085). Test one real SQL call per source after any change.
- **A deterministic agent when the agent engine is not licensed (L-MCP-014).** A rule-based planner
  (understand → retrieve via MCP tools → rank/explain → consent-gated handoff) with no LLM calls, over live read-only
  skills. It keeps the tool contract, so moving to the licensed engine later is the only delta.
- **Wrap a REST flow as a tiny stdio server (L-MCP-017).** For example, Data Marketplace ordering
  (`list_data_collections`, `list_delivery_targets`, `checkout_data_order` over the public Marketplace API, with
  self-refreshing session auth) registered in Claude Code at user scope.

### 6.6 Custom fleets: patterns worth copying (L-MCP-045 to L-MCP-048)

- **A fleet changes ergonomics, not capability.** Every tool wraps the same REST surface; it cannot author what the API
  cannot. It buys discoverability, session handling, role selection and parallelism.
- **One server per product**, so each tool list stays small (a specialist sees 15-46 tools, not ~110) and a broken plane
  is isolated. The cost: each server logs in independently.
- **Stateless servers with an on-disk session cache**, holding the JWT, org id, base URL and identity session. Cold start
  (login) took 6-8 s; warm start ~0 s.
- **Two token tiers:** the identity session (~8 h) and the JWT (30 min), refreshed silently from the session. Cache both.
- **Credentials from a secret manager**, one item per **role** (parent org, governance sub-org admin, MDM analyst,...),
  so a 403 becomes a login choice. Example: `op read "op://<vault>/<item>/<field>"`, ~2-3 s with a biometric prompt.
- **Route by query shape (L-MCP-047).** A direct tool call answers a single-domain question in ~3-5 s versus ~8 s via a
  sub-agent. Parallel sub-agents pay off only for multi-domain fan-out (~28 s vs ~60 s sequential, as reported, not
  measured here) or phased workflows. Parallel agents also multiply IPU billing on the backing calls.
- Treat any fleet's tool inventory as its author's code, not a product spec.

### 6.7 Security basics for every shim

- Keep **TLS certificate verification on**. Disabling it invites interception of tokens and passwords.
- **Review every third-party shim before reuse (L-MCP-124).** A field-distributed stdio shim for the CLAIRE agent
  and DQ servers created its HTTPS context with `ssl.CERT_NONE` and `check_hostname=False`, so it would accept any
  certificate for the identity and API hosts it sends the user's IDMC credentials to.
  1. `grep -nE "CERT_NONE|check_hostname|verify=False|_create_unverified_context" <shim files>`.
  2. Restore default verification (`ssl.create_default_context`), or pin your proxy's CA bundle
     (`ssl.create_default_context(cafile="<ca-bundle.pem>")`) behind a corporate proxy.
  3. Check that it reads credentials from a 0600 file or the environment, never from its arguments.
  4. Run one read-only tool call against the intended org before wiring it into a client.
- No credentials in code, chat or transcripts: use environment variables, 0600 files or a secret manager.
- Mask secrets in any echoed error. Rotate anything that reached a log.
- Scope OAuth clients to the servers the consumer needs.

---

## 7. Wiring MCP servers into Claude Code

- **A local stdio shim** (proven):

```bash
claude mcp add <name> -s user -- <path to python> -u <path to shim.py>
```

  `-s user` makes it available in every project for this user; project scope writes a `.mcp.json` in the repo. Start a
  new Claude session after adding it. Tools appear as `mcp__<name>__<tool>`.
- **Credentials:** pass them through environment variables or a config-file path read by the shim. Do not put them on
  the command line, where they land in shell history and process lists.
- **Remote HTTP servers.** Claude Code can also register a remote streamable-HTTP server with a static header
  (`claude mcp add --transport http <name> <url> --header "Authorization: Bearer..."`). IDMC tokens expire in 5 to
  30 minutes (OAuth default and JWT), however, which is why the shim and gateway patterns exist. This route was not
  exercised in these sources.
- **Other hosts** (vendor-documented): Claude Desktop `claude_desktop_config.json` (`mcpServers` object), Cursor
  `mcp.json`, VS Code `.vscode/mcp.json`, Python, and the AI Agent Engineering MCP Tool. Paste the code block from the
  server's Configuration tab, then edit its `headers`.
- **Interactive clients without a shim.** The vendor's Informatica plugin for Claude Enterprise connects Claude
  Desktop, Cowork and Claude Code to the hosted Catalog Discovery and CLAIRE Data Exploration Agent servers through an
  OAuth 2.1 public client with per-user consent: set-up in [02](<02 MCP Auth & OAuth Clients.md>) §6.1 (documented, not
  exercised; L-MCP-123).
- **After wiring,** confirm the target org (§4) and run one read-only tool call before relying on the server.

---

## 8. Overturned beliefs (kept so nobody re-learns them)

| Belief | Held | Overturned by | Lesson |
|---|---|---|---|
| "`working` takes `conversation_id`" | until 2026-07-26 | The live tool schema: no arguments | L-MCP-074 → L-MCP-037 |
| "The CLAIRE orchestrator has zero skills until loaded server-side" | 2026-09-22 to 2026-09-23 | A mis-pointed local config; the managed orchestrator is live | L-MCP-073 → L-MCP-033 |

---

## 9. Open questions

- Does the CLAIRE agent MCP carry any write capability through `OrchestratorSkill` (cleansing, "integration" routes)?
- What does `artifacts` do with an unrecognized name: silently drop it, or raise an error?
- Do trigger phrases such as "prepare me for the meeting" route to distinct capabilities, or are they prompt sugar?
- When will native progress streaming replace `working`, and will `get_skill_execution_updates` change with it?
