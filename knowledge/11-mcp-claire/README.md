# MCP servers and CLAIRE: cheat sheet

Driving IDMC through Informatica's managed MCP servers, your own MCP shims or gateways, and CLAIRE GPT; applies whenever a
user wants an agent, Claude or a chat to read, run or change IDMC through MCP, or asks "MCP or REST?".

**Start with:** `python3 toolkit/lib/idmc_mcp.py servers --tools` (skill `idmc-claire-mcp`), then open
[01 Managed MCP Servers](01-managed-mcp-servers-catalog-access.md). Prove the org first (`toolkit/check_login.py`).

## What works (headless)

| Task | How (exact route / tool / command) | Lesson |
|---|---|---|
| Vendor catalog, no login | `GET https://hdm.<domain>.informaticacloud.com/mcp-registry/v0.1/servers?limit=100` (23 servers, Oct 2026 release) | L-MCP-132 |
| The org's own servers | `GET https://hdm.<domain>.../a2e-mcp-asset-mgmt-svc/api/v1/mcp-servers?type=MANAGED` + `IDS-SESSION-ID`; then `tools/list` per `serverEndpointUrl` (`idmc_mcp.py servers --tools`) | L-MCP-001, L-MCP-029 |
| Call any server | POST JSON-RPC `initialize` (protocol 2025-06-18) -> keep `Mcp-Session-Id` -> `notifications/initialized` -> `tools/list` / `tools/call`; parse SSE `data:` lines | L-MCP-028 |
| OAuth client for a daemon | `POST .../a2e-mcp-asset-mgmt-svc/api/v1/oauth2clients` `{providerType:"IDMC_MCP", credentials, accessTimeout, enabled, mcpServers[...]}` -> 201 `clientId`, `clientSecret` (`idmc_mcp.py client-create --env-out PATH`) | L-MCP-018 |
| Token | `POST https://<domain>.informaticacloud.com/authz-service/oauth/token` `grant_type=client_credentials` (Basic auth); call servers with `Authorization: Bearer` | L-MCP-018, L-MCP-020 |
| JWT for shims | `GET .../identity-service/api/v1/jwt/Token?client_id=idmc_api&nonce=<uuid>` + `IDS-SESSION-ID`; JWT 30 min, session ~8 h: cache both | L-MCP-024 |
| Connections create / update / test | `connectionmanagement` (its test passed where a v2 POST test gave APP_21000) | L-MCP-002, L-MCP-049 |
| Services and connectors on a runtime | `secureagentmanagement.update_runtime_environment_selections` (rolls engines: minutes) | L-MCP-002 |
| Run / monitor / stop deployed tasks | `jobmanagement` `run_*`, `get_*_status`, stop (CDI jobs only, not CAI instances) | L-MCP-002, L-MCP-004 |
| Export / import definitions | `diassetpromotion` (REST is better for package editing) | L-MCP-049 |
| Glossary, classification writes | `cdgccatalogenrichment`; REST for scripted, idempotent curation | L-MCP-002, L-MCP-049 |
| Lineage read, fuzzy customer match | `get_asset_details` (`id`, `scheme`); `searchcustomer.search_master_record` | L-MCP-004, L-MCP-007 |
| CLAIRE GPT questions headless | `datamanagementorchestrator.orchestrate`, `dataexplorationagent.data_explore` (needs `name`, `external_id`): same answers as the UI in 28-80 s | L-MCP-111, L-MCP-119 |
| File profiling and cleansing | `dataqualityagent` (`request_upload_url` + skill; retry a 409 PUT with a fresh URL) | L-MCP-049, L-MCP-112 |
| Wire into Claude Code | `claude mcp add <name> -s user -- <python> -u <shim.py>`, credentials from env, then one read-only call | L-MCP-041 |

## What doesn't work, and the workaround

| Wall | Workaround | Lesson |
|---|---|---|
| No MCP verb authors a CDI mapping, deploys DBMI or publishes CAI | REST: package synthesis + v3 import; `task/deploy` + `job/start` on `<pod>-ing`; `POST <pod>-cai/active-bpel/asset/v1/publish` | L-MCP-003, L-MCP-130 |
| MCP cannot reach a private DB only an agent reaches | Keep the Secure Agent; MCP is a calling convention, not a network position | L-MCP-006 |
| `GET /public/core/v3/mcpServers` 404 / v3 census count 0 | Not the registry and not proof of absence: use the `hdm` registry route | L-MCP-001, L-MCP-011 |
| External MCP tool connections on a newer org | Retired outside private preview: your own agent + one aggregating gateway over vendor and own servers | L-MCP-081, L-MCP-082 |
| CLAIRE GPT has no public chat API; it never calls MCP tools or changes data | Agent MCP routes for questions; your automation executes the rules CLAIRE authors | L-MCP-051, L-MCP-089 |
| "Query the data" on PostgreSQL: "not supported" | Documented sources only (BigQuery, Snowflake, Redshift, Databricks, SQL Server, Oracle, Synapse); needs the Data Gateway on an agent | L-MCP-114, L-MCP-060 |
| Every generated SQL ends in `LIMIT 100`, no warning | Ask counts, aggregates or top-N <= 100; full extracts: take SQL from Show Code, run it elsewhere | L-MCP-114 |
| Data profiling, DQ dictionaries have no MCP tool | REST only | L-MCP-049 |
| CLAIRE orchestrator MCP lists 0 tools | Local config points at another org: print identity URL, user, org; use the managed `orchestrate` | L-MCP-033 |

## Fastest safe path

1. Prove the org (`toolkit/check_login.py`). Read-back: the printed org id matches the user's.
2. Read the public registry, then the org registry with tools. Read-back: server list with `context` and tool counts; mark
   each server called-live vs registry-only and quote tools as a range (L-MCP-131).
3. Pick MCP or REST per capability ([05](05-mcp-vs-rest-when-to-use-which.md) §3). Read-back: the chosen tool exists in
   `tools/list`.
4. For unattended callers, create a scoped OAuth client (dry run, then `--execute --expect-org <orgIdV3>`), secret to a
   0600 file, `accessTimeout` 1440 if it is a daemon (L-MCP-019, L-MCP-020). Read-back: the client in `clients`.
5. Make one read-only `tools/call`. Read-back: a real payload (unwrap up to three nested envelopes, L-MCP-030).
6. Agent-style tools: submit, poll `get_skill_execution_updates` from cursor `"0"` until `has_more=false`; answer a
   `HUMAN_PROBE` in the same conversation (L-MCP-044, L-MCP-112). Read-back: status SUCCESS / PARTIAL_SUCCESS / FAILED.
7. Any write tool: `--execute --expect-org`, then read the object back over REST (connection test, v3 objects).
8. Budget the backing services, not the MCP line (L-MCP-026).

## Top traps

- 400 `IDS_085` -> valid credential on the wrong domain or pod -> fix the host, do not reset the password (L-MCP-025).
- 401 on one server -> each server holds its own session -> it says nothing about the others (L-MCP-025).
- Shim `KeyError 'userInfo'` -> the login failed -> surface the code, stop after one rejected login (L-MCP-032).
- OAuth secret shown once -> write it straight to a 0600 file, recreate the client on any leak (L-MCP-019).
- Gateway dies after 5 min -> `accessTimeout` is minutes (5-1440) -> raise it; recreate the client when its creator's
  password rotates (L-MCP-020, L-MCP-021).
- CLAIRE agent loses context -> never invent `conversation_id`, pass the returned one; `working` takes no arguments
  (L-MCP-036, L-MCP-037).
- Proxied call hangs forever on an upstream 500 -> set a client timeout; ~26 s per call -> cache each proxy's tool
  inventory (L-MCP-084, L-MCP-083).
- "MCP is free" -> the backing CDGC/CDI/MDM calls bill IPUs; CLAIRE GPT is 50 IPU per 1,000 queries (L-MCP-026, L-MCP-116).
- Typing while "Publish Rules / Don't Publish Rules" shows -> CLAIRE publishes the rule -> click Don't Publish + Send
  first; audit `RULE_SPECIFICATION` objects (L-MCP-096).
- CLAIRE prompt never sent / table not found -> no `@`, no `dataset.table`: name platform, object type, bare name; one new
  conversation per question; re-ask after ~6 min hang (L-MCP-055, L-MCP-056, L-MCP-110).
- Gateway-only BigQuery connection fails the v2 test (APP_105060) yet serves queries -> prove with a data query and the
  gateway log, label it so nobody re-keys it (L-MCP-127, L-MCP-125).
- `search_assets` zero hits -> `filterSpec.types` is stripped, KEYWORD is token by token, NL drops filters: retry
  filter-free first (L-MCP-140, L-MCP-141, L-MCP-142).
- Third-party shim -> check for disabled TLS verification and which org it points at before wiring (L-MCP-124, L-MCP-137).

## Go deeper

- [01 Managed MCP Servers](01-managed-mcp-servers-catalog-access.md): registries, every server's can/cannot, composite servers, privileges.
- [02 MCP Auth & OAuth Clients](02-mcp-auth-oauth-clients.md): session, JWT, OAuth client credentials, OAuth 2.1 public clients, rotation.
- [03 CLAIRE GPT Prompting](03-claire-gpt-prompting-rules-patterns.md): prompt rules, shapes that pass, "Query the data", what CLAIRE persists.
- [04 Agent-Style MCP & Shims](04-agent-style-mcp-async-orchestration-custom-shims.md): async contracts, sentinels, shims, gateways, Claude Code wiring.
- [05 MCP vs REST](05-mcp-vs-rest-when-to-use-which.md): capability-by-capability table and decision rules.
- [06 CLAIRE Use Cases Ranked](06-claire-gpt-use-cases-ranked-for-retail.md): what to demo, reliability tiers, a 15-minute storyline.
- [07 Ecosystem](07-ecosystem-plugins-registries-community-tools.md): the vendor Claude plugin, registries, community tools and their risks.
- [Lessons: CLAIRE & MCP](lessons.md) (L-MCP-*; skip the superseded section).
