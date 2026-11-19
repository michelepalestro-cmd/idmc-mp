<!-- Frozen July 2026 snapshot, generated once from an earlier layout of the reference corpus; the generator is not shipped. Edit this file by hand. Its sources are the topic docs in knowledge/ and the lessons in lessons/; newer evidence there wins. -->

# MCP — the servers, the actions, and how to actually call one

> **July 2026 snapshot.** Where this file says "UI-only", "no REST verb" or "walled", read it as a dated verdict:
> many were overturned later (KB `lessons/overturned-beliefs.md`, Laws 16-19). Before telling a user
> something is not possible, work the workaround ladder in KB `knowledge/00-start-here/08 New Pipeline Milestones`.
> "Org A" / "Org B" are two example orgs; derive your own values (Law 1).

**Read this before comparing MCP to REST.** The verb question does not apply: every MCP call is
an HTTP POST to one server endpoint with a JSON-RPC body naming an action, so read/write intent
lives in the action name, not a verb. A verb matrix is a REST-only concept — say that first or
the comparison confuses.

Section 30 is the MCP *catalog* (which servers exist, which actions, how to authenticate). This section is the *operating manual*: the exact call sequence, the async poll loop, and the argument rules that decide whether a first call succeeds or silently loses context.

**Evidence class: live tool schemas, read directly from a connected CLAIRE MCP server on 2026-07-26.** Higher-grade than vendor doc for these specifics — it is the server describing itself. It corrected one row in section 30 (`working` takes NO arguments; the earlier note said `conversation_id`).

**The one-sentence model:** an IDMC MCP action is **asynchronous** — you submit a natural-language prompt, then poll a separate action until a sentinel line appears. Treat it as job submission, not a function call. This mirrors the REST platform exactly: POST to start, GET to poll.

## The call sequence — in this order, every session

| # | Call | Rule |
|---|---|---|
| 1 | new_conversation  (no arguments) | MUST be the very first action of every new chat session, BEFORE any skill call. It returns a fresh conversation id so the agent has clean context. Do NOT call it again mid-conversation unless deliberately resetting. Skipping it is the usual cause of a failed first call. |
| 2 | OrchestratorSkill \| MdmOrchestratorSkill  (prompt=...) | Submit ONE natural-language prompt. `prompt` is the only required argument. Returns immediately — this is a submission, not an answer. Pick the MDM twin for mastered entities, business entities, golden records, hierarchies, match/merge and cross-entity relationships; the general one for everything else (metadata discovery, exploration, DQ, rule generation, cleansing, profiling, enrichment, integration, product docs). |
| 3 | working  (no arguments) | Poll at roughly 1-second intervals until a sentinel arrives. Cursor-based server-side: each call returns only what queued since your last call, so there are no duplicates and you must not skip calls. Takes NO arguments — passing conversation_id is wrong. |
| 4 | stop on a sentinel | Do not poll past one. See the sentinel table. |

## Poll sentinels — what each returned line means

| Line starts with | Meaning | Do |
|---|---|---|
| ANSWER: | Final result. JSON with `responseType=FINAL_BUNDLE`, carrying `artifact`, `plan` and `human_probe` fields. | Render it and STOP polling. |
| PROBE: | CLAIRE needs clarification — it could not resolve the request. | Ask the human the question and STOP polling. Usually caused by a vague prompt. |
| done | Finished with no further output. | STOP polling. |
| Error: <msg> | The task failed. | Report the message and STOP. Do not retry blindly. |
| Still working... | Nothing ready yet. | Poll again SILENTLY — do not surface this to the human. |
| (any other plain text) | Live execution progress and reasoning. | Display each line VERBATIM to the human — do not rephrase or summarise — then keep polling. |

## Argument rules that silently cost you context

| Argument | Rule | Failure if you get it wrong |
|---|---|---|
| conversation_id | OMIT it on the first call — do NOT generate your own. The server mints one and returns it at `response.context.conversation_id`. Pass that exact value on every subsequent call. | Omitting it on a FOLLOW-UP call is treated as a brand-new session and **all prior context is lost** — silently. No error is raised. |
| conversation_id vs history | Use ONE or the other, never both in the same request. `conversation_id` is preferred; `history` exists for stateless or embedded callers that manage their own state. | Sending both is out of contract. |
| history | An ordered list of `{role, content}` where role is user \| assistant \| system. | — |
| artifacts | Only names CLAIRE has ALREADY returned (e.g. an asset name from a discovery result). **Never invent or guess an artifact name.** | A guessed name is a fabricated reference — the exact failure mode this whole knowledge base exists to prevent. |
| prompt | Be specific about the data source, the entity name and the action. Good: 'Show customer datasets in the Snowflake_Prod connection' · 'Profile the ORDERS table and list columns with null values'. Bad: 'show data'. | A vague prompt returns a HUMAN_PROBE clarification instead of an answer — costing a full round trip. |
| reasoning | true exposes WHY: how intent was interpreted and which sub-skill was chosen (REASONING_TRACE items). | Debugging prompt interpretation and skill routing. |
| events | true exposes WHAT: a sequential log of which sub-skills ran, in what order, with outcomes (EXECUTION_INSIGHT items). | Auditing the execution pipeline. Distinct from `reasoning`. |

## What this changes about the MCP verdict

| Earlier framing | Refinement from the live server | So |
|---|---|---|
| 'MCP is 11 actions, all POST, one write' — a thin wrapper over REST. | Still true for the five vendor servers. But the CLAIRE agent server is a different shape: it exposes only 4 actions, and they are an *orchestration* interface, not endpoint wrappers. One free-text prompt is routed across metadata discovery, profiling, DQ, rule generation, cleansing, enrichment and integration. | Judge an MCP server by its action list, not by the word 'MCP'. Two IDMC MCP servers can differ more from each other than from REST. |
| 'Verb matrices do not apply to MCP.' | Confirmed and sharpened: there is no verb surface AND no endpoint surface. The unit of work is a natural-language prompt plus a poll loop. | Never promise MCP parity with a REST endpoint list. The comparison is category-mismatched — say so first, or the conversation confuses. |
| 'MCP is free in preview.' | Unchanged and worth repeating: the MCP layer is not monetised during the AI Agent Engineering preview, but every backing CDGC / CDI / Marketplace / MDM call still bills IPUs. | An agent that loops on an orchestration prompt can generate real consumption while the MCP line reads zero. |
| 'MCP could replace the Secure Agent.' | No — MCP is a calling convention, not a network position. It cannot reach a private database that a Secure Agent reaches, and no MCP action authors a design-time asset. | The UI-only authoring wall applies identically to MCP. MCP does not widen the write surface. |

## Rendering the ANSWER: bundle - one contract per viewType

| viewType | How to render it | Fields to read |
|---|---|---|
| GridView | Tabular discovery/search results. Build column headers from schema_definitions[].label IN ORDER, then map each items[] row by fieldName position. If key_insights is present, show it BELOW the table as a callout. | schema_definitions[].label, items[], key_insights |
| null or DataExploreResult | A data preview WITH the SQL. Same header/row build as GridView. Render a null cell as an em dash, not the word 'null'. Show the generated SQL below the table in a sql code fence, then a footer line: Rows: <row_count_total> \| Execution time: <execution_time_ms>ms. | schema_definitions[].label, items[][], execution_context.generated_sql, row_count_total, execution_time_ms |
| PropertiesView | Asset metadata. A two-column table: Property \| Value. If there are multiple property groups, separate them with subheadings. | property groups, name/value pairs |
| GraphView | Lineage and relationships. Use arrows for direction (SourceTable -> TransformLayer -> TargetTable), one node per line, indent branches for hierarchy. | nodes, edges/direction |
| AnalyticsView | Metrics and aggregates. Lead with the single most important metric in bold, then highlight trends and comparisons. Keep commentary minimal - do not narrate the numbers. | metrics, comparisons |
| TreeView | Hierarchies (catalog / schema / folder). Render as an indented tree with folder and table glyphs. | nested nodes |
| BlockText | Plain prose. Display as-is; do not reformat. | text |

## Local CLAIRE agent server - install and wiring

| Item | Value / rule | Note |
|---|---|---|
| MCP endpoint shape | <claire_api_url>/claire-orchestrator-ai-agent/api/v1/mcp | Built by the shim from claire_api_url. The agent is a PATH on the CLAIRE API host, not its own hostname. |
| Config keys required | claire_api_url, identity_url, username, password, client_id | Credentials come from config/env - never inline, never in chat. |
| Auth chain (2 calls) | POST <identity_url>/api/v1/Login -> sessionId (read from userInfo.sessionId, or sessionId, or session_id) ; then GET <identity_url>/api/v1/jwt/Token?client_id=<id>&nonce=<uuid> with header IDS-SESSION-ID -> jwt_token | Same identity plane the data360/CDGC calls use. The nonce is a fresh uuid per request. |
| Token lifetime | 30 minutes, self-refreshed by the shim | Matches the documented platform JWT lifetime. A long session MUST re-auth. |
| Install layout | skill folder at ~/.claude/skills/claire-idmc-agent/ ; python .venv created by the installer ; register with `claude mcp add` | The skill and the MCP server are two separate registrations - the skill tells Claude HOW to call, the server IS the callable. |
| Session isolation gotcha | Claude Desktop keeps the MCP server running ACROSS chats - clicking New Chat does NOT reset CLAIRE's context | This is exactly why new_conversation must be the first action every chat. Skipping it leaks context between conversations. |

## Catalog — The five servers, and which IDMC product each one covers

| MCP server | Backing IDMC service | Actions | What it is for |
|---|---|---|---|
| Address Verification | Cloud Address Verification (CDQ) | 1 | Validate, standardize and geocode addresses in real time, 240+ countries |
| CDGC Metadata Search | CDGC catalog | 2 | Natural-language asset discovery; returns metadata including lineage and profile |
| Customer Identification | MDM SaaS / Customer 360 | 2 | Fuzzy identity resolution plus master (golden) record retrieval |
| Data Provisioning | Cloud Data Marketplace | 3 | List collections and targets, and raise a governed access request |
| Job Management | CDI execution engine | 3 | Trigger, monitor and stop mapping tasks in real time |

## Catalog — All eleven actions across the five servers

| MCP action | Verb | Server | Key inputs | What it does |
|---|---|---|---|---|
| verify_address | POST | Address Verification | address payload | Validates, standardizes and geocodes an address; returns a validation status. Persists nothing. |
| search_metadata | POST | CDGC Metadata Search | knowledgeQuery (NL string) | Natural-language catalog query returning matching asset IDs and core attributes. |
| get_asset_details | POST | CDGC Metadata Search | id, scheme | Full metadata for one asset — includes lineage, profile and full descriptions. |
| search_master_record | POST | Customer Identification | customer details | Fuzzy match returning the business ID of the best-matching master record. |
| get_master_record_details | POST | Customer Identification | business ID | The consolidated golden record, merged across source systems. |
| list_data_collections | POST | Data Provisioning | limit, search | Lists marketplace data collections. |
| list_delivery_targets | POST | Data Provisioning | id (uuid), segments | Returns collection detail. Note: despite the name it does not return a target list. |
| checkout_data_order | POST | Data Provisioning | dataCollectionId, justification, targetRef | The only write in the catalog. Raises a formal access request; requires a business justification. |
| run_mapping_task | POST | Job Management | task plus runtime parameters | Triggers execution of a CDI mapping task. |
| get_job_status | POST | Job Management | job id | Live execution state, row counts and error logs. |
| stop_running_job | POST | Job Management | job id | Sends an immediate termination request to the Secure Agent. |

## Catalog — Protocol and transport

| Property | Value | Note |
|---|---|---|
| MCP protocol version | 2025-06-18 | MCP guide p.7. Pin this when writing a client. |
| Transport | streamable HTTP | Not stdio. Remote servers, not local subprocesses. |
| Host / client model | your AI app = MCP host; each agent = MCP client; one client to one server | MCP guide p.6. Informatica calls MCP tools 'actions'; the details page says actions, third-party clients say tools. Same thing. |
| Where to see them | AI Agent Engineering > MCP Servers page | Each server's Configuration tab holds the endpoint URL and a paste-ready code block. |
| Supported clients | Claude Desktop, Cursor, VS Code, Python, and the AI Agent Engineering MCP Tool | MCP guide pp.13-14. |
| Metering | Not monetized during the AI Agent Engineering preview — BUT the underlying service APIs still bill IPUs at the service rate card | MCP guide p.7. The trap: MCP looks free, then CDGC, CDI, Marketplace and MDM calls appear on the bill. Budget the backing service, not the MCP layer. |

## Catalog — Three ways to authenticate

| Method | Header to send | When to use it | Notes |
|---|---|---|---|
| Session ID | headers={"IDS-SESSION-ID": "<session ID>"} | Quickest path; you already have this from a v1 login. | MCP guide pp.12-14. Same session ID the REST planes use. |
| JWT | headers={"Authorization": "Bearer <token>"} | When the org standardises on JWT. | Minted the same way as the data360 token. Remember the documented 30-minute lifetime. |
| OAuth — direct client | headers={"Authorization": "Bearer <token>"} | Production. The agent never holds the operator's IDMC credentials. | Client Credentials grant, POST to the token endpoint, OAuth 2.0. Recommended for anything long-lived. |
| OAuth — federated | headers={"Authorization": "Bearer <token>"} | Org uses SAML SSO; identity is delegated to Okta or Azure AD. | Requires the org configured for SAML with users set up as SAML users, plus a configured IdP. |

## Catalog — OAuth client lifecycle — Configuration > MCP Server Authorization

| Operation | Where | What you get / must know |
|---|---|---|
| Add OAuth client | Add OAuth Client wizard: Authentication > Details > Resources > Generate Credentials | Returns client ID, client secret, and an auth header value (base64 of id:secret). On the Resources page you pick WHICH MCP servers this client may reach — scope it narrowly. |
| Access-token timeout | Details page of the wizard | Default 5 minutes. Range 5 to 1440 minutes (24 h). Five minutes will bite any long-running agent — raise it deliberately. |
| Secret retrieval | Generate Credentials page, once | The secret and header value are NOT available after the wizard closes. Copy them then, or regenerate. |
| Regenerate secret | Actions menu > Regenerate Secret | Re-authenticates with username and password first. The recovery path when a secret is lost. |
| Disable / enable | Actions menu > Disable or Enable | Enabled on creation. Disable stops token issuance without deleting — the correct response to a compromised client. |
| Edit | Edit icon | Change name, description, timeout, or which MCP servers are in scope. |
| Delete | Delete icon | For clients no longer needed. |
| Download report | Download CSV icon | Name, description, status, MCP servers and last-update date for every client. Ignores on-screen filters — always the full list. Useful as an audit artifact. |

## Catalog — The CLAIRE MCP server on this machine — live enumeration

| Tool | Accepted arguments | What it is |
|---|---|---|
| OrchestratorSkill | prompt, conversation_id, name, external_id, artifacts, history, reasoning, events | General CLAIRE orchestration. One free-text prompt in, an artifact-bearing response out. |
| MdmOrchestratorSkill | prompt, conversation_id, name, external_id, artifacts, history, reasoning, events | The MDM-specialised twin. |
| new_conversation | (no domain args) | Must be called FIRST to obtain a conversation_id. Skipping it is the usual cause of a failed first call. |
| working | (NONE - takes no arguments at all) | Poll until the response is ready. CLAIRE is asynchronous - treat this as a poll-until-done loop. CORRECTED 2026-07-26 from the live tool schema: this action accepts NO arguments (properties={}), so do NOT pass conversation_id. It is cursor-based server-side and returns only items queued since your previous call. It is also a LOCAL POLLING SHIM that Informatica will remove once the MCP server provides native progress streaming. |

## Catalog — How many MCP servers are there, really

| Class | Count | Evidence |
|---|---|---|
| Informatica-MANAGED MCP servers | 5 - Address Verification, CDGC Metadata Search, Customer Identification, Data Provisioning, Job Management | AIAE April 2026 'Available MCP servers' p.7-8 enumerates exactly these five and no others. This is the authoritative catalog for that release. |
| ...of those, exposed on a probed org | 2 of 5 | GET /public/core/v3/mcpServers returned a populated registry on one org listing 2; the same path 404s on another org entirely. Exposure is per-org, not per-product. |
| CLAIRE / AI-agent MCP servers | separate class, NOT in the five | Reached at <claire_api_url>/claire-orchestrator-ai-agent/api/v1/mcp. Appears as tools in the HOST app, not in the org's mcpServers registry - so counting it against the five is a category error. |
| Your own / third-party servers | unbounded | Any MCP server you register in the host (claude mcp add) sits beside these. IDMC does not know about them. |
| Commonly-heard '5 to 10' | Treat as unverified | Only the 5 managed servers are vendor-enumerated for April 2026. If someone cites more, ask which RELEASE and whether they are counting AI-agent servers or their own registrations. Re-read the Available MCP servers page before quoting a number to a customer - the roadmap is active. |

## REST-versus-MCP coverage delta

| Capability | Over REST | Over MCP | Which to use |
|---|---|---|---|
| Catalog search / asset detail | READ (data360 search + catalog) | READ — search_metadata, get_asset_details | MCP. Natural-language query is a real gain over building a query envelope. |
| Address validation / geocoding | READ (Cloud Address Verification) | READ — verify_address | Either. MCP is simpler for one address; REST batches 1,000. |
| Master-record lookup | MDM SaaS APIs (host-mounted, 404 on Org A) | READ — search_master_record, get_master_record_details | MCP. Fuzzy match is the whole value, and it is not trivial to replicate. |
| Marketplace order / provisioning | WRITE — full chain proven | WRITE — checkout_data_order (the only MCP write) | REST for the full chain; MCP for a conversational just-in-time request. |
| Run / monitor / stop a CDI task | RUN — v2 job, activityLog | EXECUTE — run_mapping_task, get_job_status, stop_running_job | Either. MCP is the cleaner surface for an operator agent. |
| Create a connection | WRITE — proven, §17 | no action | REST only. Nothing in MCP touches connections. |
| Publish CAI assets in bulk | RUN — asset/v1/publish, 199 max | no action | REST only. |
| CAI suspend / resume / terminate | RUN — restadmin, §16 | no action | REST only. Note Job Management MCP stops CDI jobs, not CAI instances. |
| Schedule anything | WRITE — v2 schedule + CAI restadmin scheduler | no action | REST only. |
| Users, groups, roles, agents | WRITE — v2 and v3 admin | no action | REST only. No MCP server fronts administration. |
| Glossary, classification accept, stewardship | UI-ONLY | no action | Neither. Still the most stubbornly UI-bound part of the platform. |

## Custom fleets — Reference fleet — 9 custom servers, ~110 tools, split by IDMC product

| Server | Tools | Covers |
|---|---|---|
| idmc-core | 15 | Platform: connections, mappings, mapping tasks, taskflows, start/stop job, activity log, schedules, object lookup, org licence, roles |
| idmc-mdm | 17 | MDM: search, search_match, entity read by id / xref / members, create, update, patch, delete, merge, unmerge, relationships, xref, metadata, jobs |
| idmc-cdgc | 20 | CDGC: asset search, find-by-name, business-term search, asset get/create/update/delete, catalog-source list + run, DQ scores, audit history, export |
| idmc-cdmp | 8 | Data Marketplace: data-product search/get, collection get, access request create/approve/reject, asset usage |
| idmc-cdam | 10 | Data Access Management: policy list/get/create/update/delete, evaluate access, classifications, entitlements |
| idmc-profiling | 8 | Profiling: create, run, list profiles, get definition, per-column stats, patterns, value frequencies, job |
| idmc-dbmi | 10 | Database ingestion: task create/deploy/get, job start/stop/resume/undeploy, status, metrics, job id |
| idmc-file-ingestion | 9 | File pipelines: task create/update/delete, run job, job status + logs, list/get task, activity log |
| idmc-streaming | 9 | Streaming: task deploy/undeploy, start/stop, job get/list/status/statistics/history |

## Custom fleets — Architecture patterns worth copying

| Pattern | How it works | Why it pays |
|---|---|---|
| One server per IDMC product | 9 servers split along product lines rather than one monolith, each with its own auth session. | Keeps tool lists small enough for a model to choose well, and isolates a broken product plane from the rest. The trade-off is stated below: each server logs in independently. |
| Stateless servers + session cache on disk | Session written to `.idmc_sessions/<server>_session_<item>.json` holding JWT, org id, base URL and the IDS session; loaded on server startup. | Cold start ~6-8 s (login), warm start ~0 s. Survives a server restart, so a fleet of 9 does not mean 9 logins per query. |
| Two-tier token lifetime | IDS session ~8 h (full re-login needed after), JWT ~30 min (auto-refreshed FROM the IDS session, no credential prompt). Refresh ~0.5 s every ~25 min. | Matches the platform's documented 30-min JWT. The insight is that the long-lived IDS session is what lets you refresh silently — cache both, not just the JWT. |
| Credentials from a secret manager, never a file | 1Password CLI (`op read "op://<vault>/<item>/<field>"`) with biometric prompt on first access, ~2-3 s. | The right shape: the MCP server holds no plaintext credential and each org/role is a separate vault item. Directly matches this corpus's secrets rule. |
| One vault item per ROLE, not per person | Separate items for the parent org, the governance sub-org (holds CDGC Admin), an MDM analyst and an MDM developer — pick the item that has the privilege the task needs. | Turns 'why does this 403' into a login choice instead of a debugging session. Ties directly to the three-layer gate: a role gap is not an entitlement gap. |
| Sub-agents per domain, spawned in parallel | 4 orchestrating sub-agents (platform / mdm / cdgc / ingestion) each scoped to its own tool namespace; multi-domain questions fan out concurrently. | Reported ~28 s parallel vs ~60 s sequential for a 3-domain query. The real win is prompt scoping — a specialist agent sees 15-46 tools, not 110. |
| Route by query shape | Simple single-domain question -> call the tool directly (~3-5 s). Multi-domain -> parallel agents. Multi-phase workflow -> sequential agents with a barrier between phases. | Explicitly notes the monolith WINS for simple queries (3-5 s vs 8 s for an agent). Do not spawn an agent to list connections. |

## Custom fleets — Base URLs — per-product, and they differ in shape

| Product | Base URL pattern | Note |
|---|---|---|
| Platform (v2/v3) | https://<pod>.<domain>.informaticacloud.com/saas | The only one with /saas. |
| CDGC / CDMP / CDAM | https://idmc-api.<domain>.informaticacloud.com | The identity plane host, not the pod host. Three headers. |
| MDM | https://<pod>-mdm.<domain>.informaticacloud.com | Add -mdm to the pod label and DROP /saas. ⚠️ Recorded as 404-not-mounted on a different org — per-org. |
| Database ingestion (DBMI) | https://<pod>-ing.<domain>.informaticacloud.com | NEW to this corpus: an `-ing` suffix host. Not previously recorded. |
| File + streaming ingestion | https://<pod>.<domain>.informaticacloud.com | Pod host but WITHOUT /saas — a third shape. |
| Login (identity) | https://<domain>.informaticacloud.com/identity-service/api/v1/Login then /jwt/Token?client_id=idmc_api | Unprefixed domain host. Same chain the CLAIRE shim uses. |

## Custom fleets — Reconciliation — where this fleet's tools meet our recorded 404s

| Claimed tool | What this corpus recorded | How to resolve |
|---|---|---|
| dbmi_create_task / deploy / job status (10 tools) | `/dbmi/public/api/v2/task/create` = documented but **404 on our org**; `task/details`, `job/status` 404; `/api/v2/miTask` 404 across 7 variants; MI authoring listed as a UI-only wall. | The `-ing` host is the likely explanation — we may have probed DBMI on the wrong base URL entirely. **Highest-value single thing to re-probe** from this document: `https://<pod>-ing.<domain>/dbmi/public/api/v2/...`. If it answers, our Mass Ingestion wall is a host error, not a platform limit. |
| cdam_create_policy / update / delete | ~40 `/data360/dam/v1/policies` variants **404 on our org** while the DAM engine was RUNNING; recorded as a UI-only wall. | Different org may have the plane mounted, or the fleet uses a path we never tried. Re-probe before repeating 'DAM has no REST plane' as a platform fact — our evidence is org-scoped. |
| mdm_create / update / patch / delete / merge / unmerge | Ingest via `POST .../entity/{be}?sourceSystem=X` is proven 201; `PUT`/`PATCH` on `{be}/{id}` are documented-only, 0 proven; public search 404/405; **model deploy is a hard UI wall**. | Consistent, not contradictory: entity-level CRUD is plausible; MODEL authoring/deploy is the wall. Note this fleet claims no model-deploy tool either — agreement, once you separate the two. |
| cdgc_create_asset / update_asset / delete_asset | The proven CDGC write plane is `POST /ccgf-contentv2/api/v1/publish` (207 + jobId). Glossary-term binding and steward assignment are UI-only walls. | Likely the same publish plane wrapped in friendlier tool names. Verify which underlying path the tool calls before assuming a new capability exists. |
| profiling_create / profiling_run | Profiling reads are LIVE on `<pod>-dqprofile`; profile+query CRUD is 'documented, paths not held'. | This third-party server may hold the paths we lacked. Probe them yourself (bogus-twin test, Law 2) to confirm the exact endpoints — it closes a known gap. |

## Custom fleets — Operational traps this fleet reports

| Symptom | Cause | Fix |
|---|---|---|
| `401 Unauthorized` on one product but not others | Each MCP server holds an INDEPENDENT session. Logging into core does not authenticate cdgc. | Log in per server. This is the cost of the one-server-per-product split. |
| `IDS_085 User name or password is not valid`, HTTP 400 | Wrong pod — credentials issued for one pod used against another. | Check the pod/domain in the stored credential item. A valid credential on the wrong pod looks exactly like a bad password. |
| CDGC `classType` filter silently ignored | Known API bug: the filter is accepted and has no effect. | Use find-by-name with exact match, or filter client-side on `core.classType` after fetching. **A filter that is ignored rather than rejected is the worst kind — it returns plausible wrong results.** |
| First query takes 6-8 s | Cold-start login (1Password prompt + dual login). | Expected. Subsequent queries are ~0 s from the disk cache. |
| `Agent type '<name>' not found` | Agent definition files missing, or the host was not restarted after adding them. | Confirm `.claude/agents/*.md` exist, then restart the host. |
| Cached CDGC asset ids stop resolving | CDGC search returns SEMANTIC results — ids are not stable handles to re-use later. | Re-resolve by name at use time rather than caching an id. |

## Availability is per-org and per-machine — check, do not assume

`GET /public/core/v3/mcpServers` returned a populated registry on one org and 404 on another, and only 2 of the 5 vendor servers were exposed on the lab org. A locally-connected agent server (like CLAIRE here) is a separate thing again: it appears as tools in the host application, not in that registry. Before designing on MCP, enumerate what your host actually has AND probe the org registry — they answer different questions.

## The poll loop is the whole integration

Most MCP integration bugs here are loop bugs, not auth bugs: self-generating a conversation id, dropping it on the second call, passing arguments to `working`, surfacing 'Still working...' to the user, or stopping before a sentinel. Get the four-step sequence right and the rest is prompt quality.

## `working` is explicitly temporary

The server documents it as a local polling shim that will be REMOVED when the MCP server provides native progress streaming. Any client built on it should isolate the poll behind one function, so the swap is a single edit rather than a rewrite.

## Relationship to the shipped claire-idmc-agent skill

Informatica Tech Sales publishes a dedicated `claire-idmc-agent` skill (SKILL.md + a python MCP shim + setup script) whose whole job is to OPERATE the CLAIRE agent server well: skill selection, the poll loop, and the seven viewType rendering contracts above. This section absorbs its operational contract so a single skill can both decide WHETHER to use MCP and then call it correctly. It does NOT replace the shim - you still need that MCP server registered for the tools to exist. Keep both: their skill is the transport, this is the judgement.

## MCP is a small curated subset of REST, with two exceptions.

Seven of the eleven actions are thin wrappers over a REST endpoint you could call directly, and in several cases REST is strictly more capable - raw Elasticsearch DSL instead of one search string, 1,000 addresses per call instead of one, full job history instead of a single job. The two genuine exceptions are asset lineage via get_asset_details and fuzzy identity match via search_master_record; neither has any REST equivalent on this platform.

## No MCP action authors a design-time asset.

There is no mapping designer, no rule authoring and no business-entity modelling in the MCP catalog. The read/write boundary is identical to REST's, which is the clearest evidence that MCP sits on top of the same service APIs rather than beside them.

## Billing.

MCP server usage is not separately metered during the AI Agent Engineering preview, but the shared servers call IDMC service APIs underneath and that consumption incurs IPUs at your normal service rate card. Budget MCP as the underlying service.

## Server availability is per-org.

Of the five published servers, a live enumeration of one lab tenant found only two exposed on its MCP host. The documented catalog is the ceiling, not a guarantee.

## The count question, settled

Three different things get called 'IDMC MCP servers'. (1) FIVE Informatica-MANAGED servers, vendor-enumerated for April 2026, 11 actions, one write. (2) CLAIRE / AI-agent servers — a separate class reached on the CLAIRE API host, appearing as host tools rather than in the org registry. (3) CUSTOM fleets like this one — 9 servers and ~110 tools of somebody's own code over the same REST APIs, unbounded in principle. When someone quotes a number, ask which class they mean and which release. Only (1) is a vendor fact.

## What a custom fleet does and does not change

It changes ERGONOMICS, not capability. Every tool is a wrapper over the same REST surface, so the platform boundary is unmoved: design-time authoring (mapping design, taskflow publish, MDM model deploy, DQ rule authoring) still has no REST verb, and no amount of MCP wrapping creates one. A 110-tool fleet cannot do anything the API cannot. What it genuinely buys is discoverability, session handling, role selection and parallelism.

## Do not spawn an agent for a simple query

This architecture's own measurements say the direct tool call wins on single-domain questions (3-5 s vs ~8 s for a sub-agent) and only pays off on multi-domain fan-out (~28 s vs ~60 s) or phased workflows. Worth stating because the temptation with a 4-agent fleet is to route everything through an agent.

## Treat the tool inventory as third-party code, not a spec

The tool names in this section exist in a third-party MCP server's code, not in Informatica's product. Someone reading this skill should not expect `mcp__idmc-cdgc__cdgc_create_asset` to exist in their own environment. The transferable content is the architecture, the base-URL shapes, and the traps.

## Open questions

- Does the CLAIRE agent MCP server carry any write capability at all, or is every route through OrchestratorSkill read-only? The action descriptions name cleansing, rule generation and integration, which imply writes, but none was exercised.
- How does the CLAIRE agent server authenticate in practice on this machine (IDS-SESSION-ID, JWT or OAuth), and does it inherit the host's IDMC session or hold its own?
- Whether `artifacts` accepts only asset names or any prior artifact reference, and what happens on an unrecognised name (silent drop vs error) — untested.
- The shipped claire-idmc-agent skill lists trigger phrases like 'prepare me for the meeting' / 'prepare me for the day' that imply agenda-style composite queries. Whether those route to any distinct capability, or are just prompt sugar over OrchestratorSkill, is unverified.
- ~~Does DBMI answer on <pod>-ing?~~ **RESOLVED YES, 2026-07-26.** The -ing host is real (DNS resolves; bogus sibling does not) and serves live DBMI handlers. Our entire Mass Ingestion 'wall' was a wrong-host error. Body shapes still unmapped, and job/status needs an unknown Content-Type. A second prefix /mi/public/api/v2/* is also live on that host and unmapped.
- Are the DAM policy and CDGC asset-CRUD tools calling paths we never probed, or a different org where those planes are mounted? Probe the exact endpoint each tool would hit (Law 2) before relying on it.
- What are the Data Profiling profile+query CRUD paths this fleet uses? Our corpus records them as 'documented, paths not held' — this would close that gap.
- Is the reported ~2x parallel speedup measured or estimated? No methodology is given, and 4 concurrent agents also multiply IPU-billing on the backing calls.

