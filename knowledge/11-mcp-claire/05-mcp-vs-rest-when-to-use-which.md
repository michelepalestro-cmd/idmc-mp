# MCP vs REST: when to use which

**Answers:** For a given IDMC capability, should I call REST or an MCP server? What is only on one side? What does the
same task look like both ways? What do they cost and how fast are they?

**Read when:** designing an agent, gateway or script that touches IDMC; before declaring "MCP can't" or "REST can't".

**Key rules:**
- MCP and REST share one capability boundary: MCP never reaches what the service API cannot, and adds no network
  position (L-MCP-006).
- Use REST when you need exact bodies, paging, bulk, read-back and idempotence; use MCP for natural language, lineage
  reads and fuzzy match (L-MCP-049).
- Only on MCP: fuzzy customer match, the file-based DQ agent, the CLAIRE agent questions. Only on REST: Data Profiling,
  dictionaries, DBMI deploy, CAI publish, authoring mappings (L-MCP-003, L-MCP-049). Lineage is on both: MCP in one
  call, REST hop by hop from the asset read (L-CDGC-181).
- In this plugin both are available at once: the REST API through the toolkit, and the org's managed servers as
  Claude Code tools after `/idmc-mp:connect-mcp` (§0).
- Never a user session in a daemon: use REST with a service login or an MCP gateway that holds an OAuth client
  (L-MCP-031).
- Budget the backing service, not the MCP line (L-MCP-026).
- NL-to-SQL runs in the CLAIRE GPT UI or the managed agent routes with the same answers; neither changes data
  (L-MCP-111, L-MCP-089).

**Related:** [01 Managed MCP Servers](01-managed-mcp-servers-catalog-access.md) ·
[04 Agent-Style MCP & Custom Shims](04-agent-style-mcp-async-orchestration-custom-shims.md) ·
[Capability Map](../00-start-here/03-capability-map.md) ·
[The Laws of Headless IDMC](../00-start-here/02-the-laws-of-headless-idmc.md) · [Lessons: CLAIRE & MCP](lessons.md)

**Last verified:** 2026-11-20 (23 managed servers, October 2026 release; L-MCP-132)

> **Summary.** Many writes now exist on **both** sides (connections, runtime-environment selections, glossary and
> classification, users and roles, export and import) (L-MCP-049). Auth for MCP callers:
> [02 MCP Auth & OAuth Clients](02-mcp-auth-oauth-clients.md). The older comparison table in the reference library
> ([API vs MCP reference](../reference/idmc-api-mcp-reference/content/31-api-vs-mcp.json)) predates the
> full registry; section 6 lists what it got wrong.

---

## 0. How this plugin gives Claude both

| Side | How Claude reaches it | Scope |
|---|---|---|
| **REST API** | the toolkit (`toolkit/lib/*.py`, `toolkit/mapgen/`), logged in with the user's own login file (`/idmc-mp:connect`); `idmc_session.py get` reads any REST path, the write scripts send through the dry-run gate (`--execute --expect-org`) | every REST route the user's login is allowed to call, in the one org it logs in to; routes per service in the [endpoint dictionary](../reference/idmc-api-mcp-reference/claude-idmc-how-to/idmc-endpoint-dictionary.md) |
| **Managed MCP servers as tools** | `/idmc-mp:connect-mcp` creates a scoped OAuth client (`~/.idmc_toolkit/mcp_client.env`); the plugin's bridge (`toolkit/lib/idmc_mcp_bridge.py`) offers each server's tools as `mcp__plugin_idmc-mp_idmc__<server>_<tool>`; `idmc_mcp_status` shows what is connected | the servers the org has switched on and the client was created for; **read-only** unless the client allows writes |
| **Managed MCP servers by script** | `toolkit/lib/idmc_mcp.py tools / call` (session or OAuth) | the same servers, without the setup step |

Short server names in the tool names: `jobs` (jobmanagement), `conn` (connectionmanagement), `agent`
(secureagentmanagement), `promo` (diassetpromotion), `catsearch` / `catfind` / `catedit` / `cathist` (catalog search,
discovery, enrichment, asset history), `dqscore`, `dqagent`, `addr` (dqverifyaddress), `cust` (searchcustomer), `prov`
(dataprovisioning), `orders`, `users`, `ipu`, `trouble`, `audit`, `logs`, `claire` (datamanagementorchestrator),
`explore` (dataexplorationagent), `policy` (policymanagement), `docs` (idmcassetdocumentation).

What decides access: the org's licences and switched-on servers, the user's privileges (a 403 means the role lacks
it, L-MCP-025), and the services' IPU bill. Neither side can do what the service itself cannot (L-MCP-006).

---

## 1. The model: what an MCP call is

- **Verbs do not apply (L-MCP-007).** Every MCP call is an HTTP POST of a JSON-RPC body (`tools/call`) naming an
  action, sent to one server endpoint. Read or write intent lives in the **action name**. A REST verb matrix is a
  category error for MCP: say that first, or the comparison confuses.
- **The same boundary (L-MCP-006).** MCP sits on top of the same service APIs. MCP cannot author what the API cannot,
  and editing an MCP proxy cannot bypass a server-side check.
- **The same network position problem.** A managed MCP server runs in Informatica's cloud. It cannot reach a private
  database that only a Secure Agent reaches, so MCP never replaces the agent.
- **The same bill (L-MCP-026).** The MCP layer is free in the AI Agent Engineering preview. Its backing CDGC, CDI,
  Marketplace and MDM calls bill IPUs. Agent loops and parallel sub-agents multiply those calls.
- **Different ergonomics.** MCP gives tool discovery (`tools/list`), natural-language parameters and agent-style
  orchestration. REST gives exact bodies, paging and deterministic read-backs.

---

## 2. Capability by capability

| Capability | REST | MCP (managed server → tool) | Use | Evidence |
|---|---|---|---|---|
| Catalog search | `POST https://idmc-api.<domain>.../data360/search/api/v1/search` with an Elasticsearch body (`X-INFA-SEARCH-LANGUAGE: elasticsearch`) | `cdgcsearchmetadata` / `cdgccatalogdiscovery` → `search_metadata` / `search_assets` (one NL string) | **MCP** for natural-language questions; **REST** for exact filters, bulk counts, facets (`core.profiled`) and paging | REST proven; MCP documented and listed |
| Asset detail and **lineage** | `GET .../data360/search/v1/assets/<identity>?scheme=internal&segments=all`: the `lineage` segment lists inbound and outbound data-flow hops, one asset at a time (L-CDGC-181); `/data360/lineage/*` graph paths are 404 | `get_asset_details` (`id`, `scheme`): lineage, profile, descriptions; **(Oct)** `cdgccatalogdiscovery` → `get_asset_lineage` | **MCP** for a lineage question; **REST** to walk and store lineage in a pipeline | REST hops proven; MCP documented |
| Fuzzy customer match | no public MDM search/list (404/405; 403 role gap on one pod) | `searchcustomer` → master-record search and details | **MCP** | REST walls |
| Address verification | `POST.../dataquality/addressverification/api/v1/process` (≤1,000 per call) | `dqverifyaddress` → `verify_address` (1 per call) | **REST** for batches; **MCP** for trickle or one-off | REST documented; MCP proven |
| Profile and cleanse an **uploaded file** | none | `dataqualityagent` → `request_upload_url` + `data_quality_cleansing` | **MCP only** | proven |
| Data Profiling profiles (create, run, poll) | `<pod>-dqprofile/profiling-service/api/v1` | none | **REST only** | proven |
| Per-rule pass rates of a profile | metric store `Profiles('<id>')/Columns('<columnId>')/ValueFrequencies` on the rule's `Output` column (L-DQ-123) | none proven (`get_asset_score` reads catalog scores, untested) | **REST** | REST proven |
| DQ dictionaries | `<pod>-dqcloud-api/quality/public/v2/dictionaries` | none | **REST only** | create proven |
| Run / monitor / stop CDI tasks | `POST /saas/api/v2/job`; `/api/v2/activity/activityLog`, `/activityMonitor` | `jobmanagement` → `run_*`, `get_*_status`, stop/terminate, `search_completed_jobs` | **Either**. MCP suits an operator agent; REST gives full history and exact filters. | both proven |
| Taskflows | `POST /api/v2/workflow` (linear, headless); advanced taskflow publish was a wall | `run_linear_taskflow`, `run_published_taskflow` (run only) | REST to author linear taskflows; either to run | REST proven |
| **Connections** create, update, test | v2 GET → edit → POST the full body; `GET /api/v2/connection/test/<id>` | `connectionmanagement` → `create_connection`, `update_connection`, `test_connection(_by_id)` | **Either**. The MCP test passed where a v2 POST test returned APP_21000. | both proven |
| Services and connectors on a runtime environment | `GET/PUT.../runtime/api/v2/runtimeEnvironment/<reId>/selections/ui` (`IDS-SESSION-ID`) | `secureagentmanagement` → `update_runtime_environment_selections` | **Either** | both proven |
| Export / import (clone authoring, migration) | `POST /public/core/v3/export`, `/import/package`, `/import/<id>` | `diassetpromotion` → `rest_export_start`, `rest_import_start`, status/log | **REST** for package editing (checksums, retargeting); MCP to trigger or inspect | REST proven |
| New CDI mapping definition (field mapping) | package synthesis and import; template mapping tasks | **none** | **REST** | MCP wall |
| Deploy a DBMI task | `task/deploy/<id>`, `job/start` on `<pod>-ing` | **none** | **REST** | proven |
| Publish a CAI process | `POST <pod>-cai/active-bpel/asset/v1/publish` | **none** | **REST** | proven |
| CAI suspend / resume / terminate, schedules | `/active-bpel/restadmin/...` | none. `jobmanagement` stops CDI jobs, not CAI instances. | **REST** | documented |
| Glossary and classification writes | `POST/PATCH.../data360/content/v1/assets` | `cdgccatalogenrichment` (glossary, classification, business-metadata writes) | **REST** for scripted, idempotent curation with undo; MCP for conversational edits | REST proven; MCP listed |
| Classification *accept*, steward assignment | UI-only (not re-probed since) | not recorded | **Neither** (re-probe) | walls |
| Users, groups, roles | `/public/core/v3/users`, `/userGroups`, `/roles` (user DELETE 204) | `usermanagement` → `create_user`, add/remove roles and groups | **Either** (both privileged) | REST proven; MCP listed |
| Marketplace order | full REST chain | `dataprovisioning` → `checkout_data_order` | **REST** for the full chain; **MCP** for a just-in-time conversational request | both documented; REST chain proven |
| Catalog DQ scores | the asset's `dataQuality` segment returns per-dimension DQResult objects once the source's Data Quality capability ran (L-CDGC-144, L-DQ-097) | `cdgcdataqualityscore` → `get_asset_score` (untested); `orchestrate` answers score questions (L-MCP-095, L-MCP-111) | **REST** for automation; **MCP** or CLAIRE for questions | REST proven; `get_asset_score` untested |
| IPU metering export | `POST /public/core/v3/license/metering/ExportMeteringData` | `ipumanagement` (metering exports) | **REST** for exact windows | REST proven |
| Diagnostics (session logs, dependencies, agent health) | scattered v2/v3 reads | `troubleshooting`, `logmanagement`, `auditmanagement` | **MCP** for exploration, **REST** for automation | MCP listed |
| Browse a connection's objects, read metadata, preview rows | object reads through the v2 connection and metadata routes (see [03 Connections](../03-connections/README.md)) | **(Oct)** `connectionmanagement` → `browse_objects`, `get_object_metadata`, `preview_object_data` | **MCP** for a quick look; **REST** in pipelines | MCP documented |
| Data access policies, row filters, de-identification | not recorded here | **(Oct)** `policymanagement` (32 tools: create and publish policies, filters, de-identification) | **MCP**; a privileged write surface | documented |
| Who changed a catalog asset, and when | not recorded here | **(Oct)** `cdgccatalogassethistory` → `get_asset_history` | **MCP** | documented |
| Document a project's assets | v3 object reads and exports, assembled yourself | **(Oct)** `idmcassetdocumentation` (35 read-only tools) | **MCP** for documentation; it does not change mappings | documented |
| Data Marketplace order lifecycle (approve, fulfill, cancel) | full REST chain | `ordermanagement` (Sept), the approver's side `dataprovisioning` lacks | **Either** | documented |
| NL-to-SQL over cataloged warehouse data | none public | CLAIRE GPT (UI); `dataexplorationagent.data_explore`, `datamanagementorchestrator.orchestrate` (agent MCP) | **Either**: the UI for demos, agent MCP for automation; same answers (L-MCP-111); SELECT-only, rows capped by `LIMIT 100` (L-MCP-114) | both proven |

---

## 3. Decision rules

1. **If a REST route exists and you need exactness** (bodies, paging, bulk, read-back, idempotence), use REST.
2. **If the value is natural language or fuzziness** (catalog questions, lineage, identity match), use MCP.
3. **If only one side has it**, use that side: the DQ agent file path is MCP-only; profiles, dictionaries, DBMI deploy
   and CAI publish are REST-only.
4. **For long-running or unattended callers**, prefer REST or an MCP gateway with an OAuth client
   ([04](04-agent-style-mcp-async-orchestration-custom-shims.md) §6.4; the plugin's bridge is one). Never a user session
   in a daemon.
5. **Before declaring anything impossible**, enumerate the managed registry *and* check the REST folders. Many "MCP
   can't" and "REST can't" verdicts fell once the full registry was enumerated (§6).
6. **Budget the backing service**, not the MCP line.
7. **Read back every MCP write over REST** (the connection test, the v3 object, the activity log): an MCP answer is
   not proof (L-MCP-049).
8. **Untested server, one read-only call first.** Say which servers were called live and which are only listed
   (L-MCP-131), and prove an untested one with a read-only call before building on it.

---

## 4. The same task both ways

Headers, sessions and hosts for REST are in [Access, Auth & Orgs](../01-login-and-orgs). MCP calls use the
server's `serverEndpointUrl` with a Bearer token ([02](02-mcp-auth-oauth-clients.md)), and the `tools/call` envelope
of [04](04-agent-style-mcp-async-orchestration-custom-shims.md) §5.

**Run a mapping task and wait for it**

- REST: `POST https://<pod>.<domain>.informaticacloud.com/saas/api/v2/job` with header `icSessionId` and body
  `{"@type":"job","taskId":"<taskId>","taskType":"MTT"}`. It returns 200 and a run id. Then poll
  `GET.../saas/api/v2/activity/activityLog`: state 1 = success, 3 = failed. Prefer the `*Utc` time fields.
- MCP: `jobmanagement` → `run_mapping_task` (task plus runtime parameters), then `get_job_status` (job id) and, if needed,
  `stop_running_job`. In Claude Code through the plugin: `jobs_run_mapping_task` (offered only when the client allows
  writes) and `jobs_get_job_status`.
- Choose REST for fleets of tasks and job history. Choose MCP for an operator agent answering "run it and tell me".

**Test a connection**

- REST: `GET.../saas/api/v2/connection/test/<connId>`. A POST form once returned `APP_21000` 500 while the GET and the
  MCP test worked.
- MCP: `connectionmanagement` → `test_connection_by_id`.

**Enable a connector or service on a runtime environment**

- REST: `GET https://<pod>.<domain>.informaticacloud.com/runtime/api/v2/runtimeEnvironment/<reId>/selections/ui` with
  `IDS-SESSION-ID`, edit the flags, then `PUT` the body back.
- MCP: `secureagentmanagement` → `update_runtime_environment_selections`.
- Either way, each change rolls the agent's engines (expect minutes of queueing). Select only what you need.

**Find catalog assets**

- REST: `POST https://idmc-api.<domain>.informaticacloud.com/data360/search/api/v1/search?knowledgeQuery=*&segments=all`
  with `Authorization: Bearer <jwt>`, `IDS-SESSION-ID`, `X-INFA-ORG-ID` and `X-INFA-SEARCH-LANGUAGE: elasticsearch`, plus
  an Elasticsearch body (`from`, `size`, `query`).
  - Page completely and dedupe.
  - Filter client-side on `core.classType`: a class-type filter was reported to be silently ignored.
  - Results are semantic, so asset ids are not stable handles.
- MCP: `cdgcsearchmetadata` → `search_metadata` with `{"knowledgeQuery":"customer tables"}`, then `get_asset_details`
  with `id` and `scheme` for lineage and profile.

**Verify addresses**

- REST: `POST <baseApiUrl>/dataquality/addressverification/api/v1/process`, with up to 1,000 addresses per call and a
  5-minute job token.
- MCP: `dqverifyaddress` → `verify_address`, one address per call. It is not an IDMC job and not counted against the job
  limit.

---

## 5. Cost and speed notes

| Situation | Observed |
|---|---|
| Direct tool call, single domain (custom fleet) | ~3-5 s |
| The same through a sub-agent | ~8 s |
| Multi-domain fan-out, parallel vs sequential sub-agents | ~28 s vs ~60 s (reported) |
| Cold MCP server start with login | 6-8 s; warm ~0 s from a session cache |
| CLAIRE GPT answer | 47-112 s |
| Managed agent routes (`orchestrate`, `data_explore`) | 28-80 s (L-MCP-111) |
| CLAIRE DQ agent code-generation run | minutes (poll up to ~15 min) |
| Address verification | REST batches 1,000 per call; MCP 1 per call, and not counted as an IDMC job |

---

## 6. What the older comparison got wrong (superseded)

The older REST-vs-MCP table (still in the reference library) predates the 19-server registry. It stated:

- "Create a connection: REST only. Nothing in MCP touches connections." Superseded by `connectionmanagement`.
- "Users, groups, roles, agents: REST only. No MCP server fronts administration." Superseded by `usermanagement` and
  `secureagentmanagement`.
- "Glossary, classification accept, stewardship: UI-only on both." Glossary writes are headless on REST
  (`data360/content`) and on MCP (`cdgccatalogenrichment`). Classification *accept* and steward assignment were not
  re-probed.
- "MCP adds exactly two things REST lacks (lineage, fuzzy match)." Probably outdated: the file-based DQ agent is a third,
  and the agent servers are a different shape again.

Recorded as L-MCP-078 → L-MCP-049. The capabilities that *remain* MCP-only or REST-only are in §2.

---

## 7. Open questions

- ~~Do the agent-style servers (`datamanagementorchestrator`, `dataexplorationagent`) return the same answers as CLAIRE
  GPT in the UI?~~ Answered: yes, faster (L-MCP-111).
- ~~Can per-rule pass rates be read headless?~~ Answered on REST: the metric store's ValueFrequencies (L-DQ-123).
  Still open: does `get_asset_score` read Data Profiling scorecard values?
- Do the October 2026 servers (`cdgccatalogassethistory`, `policymanagement`, `idmcassetdocumentation`), the October
  connection tools and `ordermanagement` behave as documented? None has been called live yet.
- Are classification accept and steward assignment now reachable through `cdgccatalogenrichment`?
