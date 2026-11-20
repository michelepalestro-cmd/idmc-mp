# Managed MCP Servers: catalog and access

**Answers:** Which Informatica-managed MCP servers does an org have, and what can each one do? What can no MCP verb do?
How do I reach a server and which privileges does it need? What are composite servers and tool connections, and what do
they require?

**Read when:** before declaring "MCP cannot do X"; wiring an agent or gateway to IDMC's hosted servers; planning tools
for your own agents; a composite server or tool connection will not save or answers 401.

**Key rules:**
- For the vendor's current catalog, read the public registry first: no login needed.
  `GET https://hdm.<domain>.informaticacloud.com/mcp-registry/v0.1/servers?limit=100` listed **23 servers** on
  2026-11-19 (L-MCP-132). Calling any server still needs an org credential (401 without one).
- Enumerate the org registry before declaring a wall:
  `GET https://hdm.<domain>.informaticacloud.com/a2e-mcp-asset-mgmt-svc/api/v1/mcp-servers?type=MANAGED` with
  `IDS-SESSION-ID`, then `tools/list` per server (L-MCP-001).
- The managed servers write (connections, runtime-environment selections, glossary, roles, export and import), but no
  MCP verb authors a CDI field mapping, deploys a DBMI task or publishes a CAI process (L-MCP-002, L-MCP-003).
- MCP is a calling convention, not a network position, and its backing calls bill IPUs (L-MCP-006, L-MCP-026).
- External MCP tool connections exist only on private-preview orgs; elsewhere put the vendor servers and your own behind
  one aggregating gateway (L-MCP-081, L-MCP-082).
- Composite servers expose only active, Basic-Auth, REST/SOAP, Cloud-Server CAI processes; each deployment is an
  instance you refresh after a process change (documented, L-MCP-119).
- CLAIRE GPT is not a client of any MCP server, yours or composite (L-MCP-089).

**Related:** [02 MCP Auth & OAuth Clients](02-mcp-auth-oauth-clients.md) ·
[04 Agent-Style MCP & Custom Shims](04-agent-style-mcp-async-orchestration-custom-shims.md) ·
[05 MCP vs REST](05-mcp-vs-rest-when-to-use-which.md) ·
[07 Ecosystem: plugins, registries, community tools](07-ecosystem-plugins-registries-community-tools.md) ·
[MCP catalog reference](../reference/idmc-api-mcp-reference/content/30-mcp-servers.json) · [Lessons: CLAIRE & MCP](lessons.md)

**Last verified:** 2026-11-19 (public registry read live; October 2026 server pages read)

> **Summary.** The MCP asset-management service lists each server's `id`, `name`, `serverEndpointUrl` and `context`. One
> full org's registry exposed **19 servers with about 140 tools**, the September 2026 guide documented 20 shared servers,
> and the October 2026 release brought the public registry to **23** (L-MCP-001, L-MCP-119, L-MCP-132). Two verdicts built only on the servers wired into one Claude session were wrong the same day,
> which is why enumeration comes first. File-based DQ agent: [CLAIRE DQ Agent](../08-data-quality/03-claire-dq-agent-file-based-profiling-cleansing.md);
> operating reference: [56-mcp-operating.json](../reference/idmc-api-mcp-reference/content/56-mcp-operating.json).

---

## 1. "How many IDMC MCP servers are there?" Ask which class and which release

Three different things get called "IDMC MCP servers" (L-MCP-005):

| Class | What it is | Where it appears | Count |
|---|---|---|---|
| **1. Informatica-managed servers** | Servers Informatica hosts over its own service APIs: jobs, connections, agents, catalog, DQ, MDM, marketplace, policies, ops | the public registry and the org registry on the `hdm` host; the AI Agent Engineering → MCP Servers page | **5** servers / 11 actions in the April 2026 guide; **19** servers / ~140 tools in one org's registry; **20** shared servers in the September 2026 guide (L-MCP-119); **23** in the October 2026 release and the public registry (L-MCP-132) |
| **2. CLAIRE / AI-agent servers** | The conversational CLAIRE orchestrator, reached on the CLAIRE API host at `<claire_api_url>/claire-orchestrator-ai-agent/api/v1/mcp` | as tools in your **host app**, not in the org registry | 4 tools (`new_conversation`, `OrchestratorSkill`, `MdmOrchestratorSkill`, `working`); can list 0 for an org ([04](04-agent-style-mcp-async-orchestration-custom-shims.md)) |
| **3. Custom fleets** | Your own (or a colleague's) MCP servers wrapping the same REST APIs | wherever you register them (`claude mcp add`, IDE config) | unbounded; one reference fleet had 9 servers / ~110 tools |

The managed catalog grows release by release. Quote a number only with its class, its release and when you enumerated
it:

| Release | Servers added | Running total |
|---|---|---|
| April 2026 | Address Verification, CDGC Metadata Search, Customer Identification, Data Provisioning, Job Management | 5 |
| July 2026 | Catalog Discovery, Catalog Enrichment | 7 |
| August 2026 | nine, including Connection, Secure Agent, User, IPU, Log and Audit Management, Asset Promotion, CDGC Data Quality Score and the Troubleshooting preview | 16 |
| September 2026 | CLAIRE Data Exploration Agent, CLAIRE Data Quality Agent, CLAIRE Orchestrator, Data Marketplace Order Management | 20 |
| October 2026 (published 2026-11-10) | Catalog Asset History, Data Access Management, IDMC Asset Documentation | **23** |

(Release-by-release split from the vendor What's New pages, read 2026-11-19; L-MCP-132.)

---

## 1a. The public registry: the vendor's catalog without a login (L-MCP-132)

```
GET https://hdm.<domain>.informaticacloud.com/mcp-registry/v0.1/servers?limit=100
```

- **No IDMC login.** It follows the official MCP registry standard (`GET /v0.1/servers`). On `dm-us` it answered 200
  with `metadata.count: 23` on 2026-11-19. Each entry is named `com.informatica.idmc/<context>`, has a `title`, a
  `version` (most `1.0.0`; Connection Management `2.2.2`, Catalog Enrichment `1.0.3`, Catalog Discovery `1.0.2`), and one
  `streamable-http` remote at `https://mcp.<domain>.informaticacloud.com/mcp-servers/public/<context>` that accepts
  either an `IDS-SESSION-ID` header or `Authorization: Bearer <token>`.
- **What it does not tell you:** which servers *your org* exposes, or the tool list. An unauthenticated `initialize`
  answers 401. For those, use the org registry (§2) and `tools/list` with a credential.
- **`status: active` is the registry's lifecycle field, not GA.** Troubleshooting is listed `active` but is still a
  preview in the docs.

---

## 2. Enumerate the registry first (L-MCP-001)

```
GET https://hdm.<domain>.informaticacloud.com/a2e-mcp-asset-mgmt-svc/api/v1/mcp-servers?type=MANAGED
IDS-SESSION-ID: <v3 login sessionId>
Accept: application/json
```

- **Response:** a list of servers, each with `id`, `name`, `serverEndpointUrl` and `context`. `context` is the short
  server key: `jobmanagement`, `dqverifyaddress`, and so on. `serverEndpointUrl` has the form
  `https://mcp.<domain>.informaticacloud.com/mcp-servers/public/<context>`.
- **Without `?type=MANAGED`** the route also lists non-managed (composite) servers.
- **Next step:** for each server, call `initialize` and then `tools/list` on its `serverEndpointUrl` to read the real
  tool names and input schemas ([04](04-agent-style-mcp-async-orchestration-custom-shims.md) §5).
- **Session:** use the v3 login (`POST https://<domain>.informaticacloud.com/saas/public/core/v3/login` →
  `userInfo.sessionId`). One read-only login served the whole enumeration.

**Why "enumerate first" is a law here.** A session that tested only the two MCP servers wired into it concluded "MCP is
DQ-only and cannot cross the integration walls"; the same afternoon the registry listed all 19 servers, and a connection
test, a runtime-environment selection and the other writes then ran through them (L-MCP-071, superseded by L-MCP-001). The belief
that `GET /public/core/v3/mcpServers` is the registry was also wrong: its 404 on one org was probably a wrong-path or
wrong-host result (was L-MCP-070, superseded by L-MCP-001).

**The v3 objects census does not prove absence.** `GET /public/core/v3/objects?q=type=='MCP_SERVER'` (or `AI_AGENT`,
`GENAI_AGENT`) returning 0 was once read as "AI Agent Engineering is not entitled". The type filter is not validated,
so a zero count never proves absence. Check the registry and the AI Agent Engineering pages (L-MCP-011, disputed;
the overturned L-MCP-075).

---

## 3. The managed servers: what each can and cannot do

The first 19 rows come from one org's registry (September 2026). The last four rows, and the tools marked **(Oct)**, come
from the October 2026 vendor server pages (documented, read 2026-11-19, not yet called live; L-MCP-132). Tool counts in the
first 19 rows come from one first-hand `tools/list` per server. The per-server counts recorded sum to about 120; the
enumeration summary said "~140 tools". Re-list on your org, because exposure is per org.

| Server (`context`) | Tools | Key tools | Can | Cannot / notes |
|---|---|---|---|---|
| `jobmanagement` | 19 | `run_mapping_task`, `run_synchronization_task`, `run_linear_taskflow`, `run_published_taskflow`, `run_replication_task`, `run_powercenter_task`, `run_dynamic_mapping_task` (listed, not exercised; a DMT is read at `/batch-mapping/api/v1/dynamictask/<id>`, L-CDI-289), `run_masking_task`, resume/stop/terminate, `get_*_status`, `search_completed_jobs`, `search_task_asset` | run, monitor and stop **already deployed or published** tasks and taskflows | no authoring, deploying or publishing. It stops CDI jobs, not CAI process instances. |
| `connectionmanagement` | 12 (18 documented Oct) | `create_connection`, `update_connection`, `delete_connection`, `get_connection(_by_name)`, `list_connections`, `test_connection`, `test_connection_by_id`; **(Oct)** `browse_objects`, `get_objects(_by_name)`, `get_related_objects`, `get_object_metadata` (+ `_with_dataformat`, `_with_flatfile_attrs`), `preview_object_data` (+ the same two variants) | **create, update and test connections** (a headless write); a connection test through it passed where a v2 POST test returned APP_21000; **(Oct)** browse a connection's objects, read their metadata and preview rows | same connector rules as REST (types, key formats) |
| `secureagentmanagement` | 15 | list/get agents and runtime environments, **`update_runtime_environment_selections`**, start/stop service | enable or disable **services and connectors** on a runtime environment | each selection change rolls engines (minutes of queueing); the REST twin is `GET/PUT.../runtime/api/v2/runtimeEnvironment/<reId>/selections/ui` |
| `diassetpromotion` | 7 | `rest_export_start`, `rest_import_start`, export/import status and log, `search_assets` (FIQL) | v3 **export/import** of asset definitions: the clone-authoring path | an import lands *definitions* only; it does not deploy DBMI or publish CAI |
| `cdgccatalogenrichment` | 3 (7 documented Oct) | `update_asset_business_metadata`, `edit_data_asset_business_glossaries`, `edit_data_asset_data_classifications`; **(Oct)** `edit_asset_certification`, `edit_asset_rating`, `manage_asset_groups`, `manage_asset_stakeholders` | **glossary, classification, certification, rating, group and stakeholder writes** | needs a populated catalog |
| `cdgccatalogdiscovery` | 2 (3 documented Oct) | `search_assets`, `get_asset_details`, **(Oct)** `get_asset_lineage` | natural-language and keyword asset discovery; argument contract in [07](07-ecosystem-plugins-registries-community-tools.md) §3 (L-MCP-134) | read-only; the server the vendor's Claude plugin uses |
| `cdgcsearchmetadata` | 2 | `search_metadata` (`knowledgeQuery`), `get_asset_details` (`id`, `scheme`) | NL catalog search; asset detail **including lineage and profile**. The `/data360/lineage/*` graph paths 404, but REST reads the same hops from the asset read's `lineage` segment (L-CDGC-181) | read-only; semantic results, so asset ids are not stable handles |
| `cdgcdataqualityscore` | 1 | `get_asset_score` | read catalog DQ scores | untested in these sources |
| `dataqualityagent` | 7 | `data_profiling`, `data_quality_analysis`, `data_quality_cleansing`, `data_quality_rule_generation`, `data_quality_rule_recommendation`, `request_upload_url`, `get_skill_execution_updates` | CLAIRE DQ agent: **file-based profiling and cleansing** with no catalog; catalog-keyed skills on cataloged assets | asynchronous; nested envelope; saves no console asset. See [CLAIRE DQ Agent](../08-data-quality/03-claire-dq-agent-file-based-profiling-cleansing.md) |
| `dqverifyaddress` | 1 | `verify_address` (Interactive mode) | verify, standardize and geocode one address per call; persists nothing | not an IDMC job; batch REST does 1,000 per call |
| `searchcustomer` | 3 | `search_master_record` (fuzzy match), `get_master_record_details` (golden record), `get_related_records` | MDM customer identification (fuzzy match; no public REST search exists) | needs MDM |
| `dataprovisioning` | 3 | `list_data_collections`, `list_delivery_targets` (returns collection detail, not targets), `checkout_data_order` | raise a governed Data Marketplace access request | the order is a request, not delivery |
| `usermanagement` | 9 | `create_user`, add/remove roles and groups (includes deletes) | **user and role administration** | treat as a privileged write surface |
| `ipumanagement` | 5 | IPU metering exports | cost visibility | see [IPU, Metering & Licensing](../13-ipu-cost) |
| `troubleshooting` | 19 | mapping and connection metadata, dependencies, agent health, activity and session logs | rich read-only diagnostics | read-only; **preview** since the July 2026 release: evaluation only, not for production (documented, L-MCP-119) |
| `auditmanagement` | 2 | audit and security logs | read-only telemetry: the audit trail plus security and identity events (logins, MFA changes, password resets, user, role and group changes) | read-only (documented, L-MCP-119) |
| `logmanagement` | 3 | activity, error and session logs | read | read-only |
| `datamanagementorchestrator` | 4 | **`orchestrate`**, **`orchestrate_master_data_analysis`** | one NL prompt routed across catalog, DQ, profiling, exploration and integration (plus an MDM twin): the CLAIRE orchestrator as a managed server; the same answers as the CLAIRE GPT UI in 28-80 s (L-MCP-111) | agent-style asynchronous contract with a nested envelope ([04](04-agent-style-mcp-async-orchestration-custom-shims.md), L-MCP-112); plans come back for approval rather than executing |
| `dataexplorationagent` | 4 | `data_explore`, `master_data_explore` | preview rows, values and quality with generated SQL; `data_explore` requires `prompt`, `name` and `external_id` (L-MCP-119) | agent-style; same answers as the UI (L-MCP-111); SELECT-only |
| `ordermanagement` (Data Marketplace Order Management; Sept) | 8 | `create_order`, `get_order`, `list_orders`, `approve_order`, `reject_order`, `fulfill_order`, `cancel_order`, `delete_order` | the full Data Marketplace order lifecycle, including the approver's side that `dataprovisioning` lacks | needs Data Marketplace; `fulfill_order` marks an order fulfilled, it does not move data |
| `cdgccatalogassethistory` (Catalog Asset History; Oct) | 1 | `get_asset_history` | read who changed what on a catalog asset, and when | read-only |
| `policymanagement` (Data Access Management; Oct) | 32 | e.g. `create_data_access_control`, `create_data_filter`, `create_data_deidentification`, `publish_data_access_asset`, `search_policy_reference_assets`, `list_user_groups` | author and publish data-access policies, row filters, de-identification and protection rules, precedence tiers and usage types | the context name does not match the title; a privileged write surface, like `usermanagement`; needs Data Access Management |
| `idmcassetdocumentation` (IDMC Asset Documentation; Oct) | 35 | read-only `idmc_*` tools over agents, connections, ingestion, mappings, mapplets, mapping task templates, objects, runtimes, source control and taskflows; its server page also names a skill, `idmc-document-project` | generate documentation of a project's assets: the first managed server that reads mapping internals for documentation | read-only: it does **not** author or change mappings (§5 still holds) |

Mapping to the April 2026 vendor names:

| April 2026 name | September context |
|---|---|
| Address Verification | `dqverifyaddress` |
| CDGC Metadata Search | `cdgcsearchmetadata` (also `cdgccatalogdiscovery`) |
| Customer Identification | `searchcustomer` |
| Data Provisioning | `dataprovisioning` |
| Job Management | `jobmanagement` |

**A client scoped to 12 of these servers** (an OAuth client for a daemon, [02](02-mcp-auth-oauth-clients.md)) exposed
83 Informatica tools through one gateway endpoint.

---

## 4. The April 2026 vendor catalog (still the reference for action arguments)

From *Getting Started with Informatica MCP Servers - Headless Data Management* (April 2026, pp.7-8) (L-MCP-004):

| Server | Action | Key inputs | What it does |
|---|---|---|---|
| Address Verification | `verify_address` | address payload | validate, standardize and geocode; returns a status; persists nothing |
| CDGC Metadata Search | `search_metadata` | `knowledgeQuery` (a natural-language string) | matching asset ids and core attributes |
| | `get_asset_details` | `id`, `scheme` | full metadata for one asset, including lineage, profile and descriptions |
| Customer Identification | `search_master_record` | customer details | fuzzy match → business id of the best master record ("finds Jon Smyth for John Smith") |
| | `get_master_record_details` | business id | the golden record, merged across sources |
| Data Provisioning | `list_data_collections` | `limit`, `search` | marketplace collections |
| | `list_delivery_targets` | `id` (uuid), `segments` | collection detail (despite the name) |
| | `checkout_data_order` | `dataCollectionId`, `justification`, `targetRef` | raises a formal access request; the only write in that release |
| Job Management | `run_mapping_task` | task plus runtime parameters | trigger a CDI mapping task |
| | `get_job_status` | job id | state, row counts, error logs |
| | `stop_running_job` | job id | termination request to the Secure Agent |

Documented platform facts from the same guide:

- **Protocol and transport:** MCP protocol **2025-06-18** over **streamable HTTP** (not stdio). Your AI app is the MCP
  host and each agent an MCP client, with one client per server. Informatica calls tools "actions".
- **Documented clients:** Claude Desktop (`claude_desktop_config.json`), Cursor (`mcp.json`), VS Code
  (`.vscode/mcp.json`), Python, and the AI Agent Engineering **MCP Tool** (New → Tool → MCP Tool, token
  authentication). Each server's **Configuration** tab holds the endpoint URL and a paste-ready code block.
- **Metering:** see §7.

"Only one write" and "MCP does only two things REST cannot" (lineage via `get_asset_details`, fuzzy match via
`search_master_record`) were true of that five-server release. With the later registries they are **outdated**
(L-MCP-007).

---

## 5. The narrow wall: what no MCP verb does (L-MCP-003)

Across all 19 servers of the September registry, including `datamanagementorchestrator.orchestrate`, **no verb**
(still true of the 23 documented in October 2026: `idmcassetdocumentation` reads mappings, it does not write them; L-MCP-132):

| Missing verb | REST route that does it | Where it is documented |
|---|---|---|
| authors a brand-new CDI mapping definition (field mapping) | synthesize mappings as packages and import them; clone a template mapping task | [Data Integration (CDI)](../04-mappings), [Migration & Org Management](../12-deploy-migrate) |
| deploys a Database Ingestion (DBMI) task | `task/deploy/<id>` and `job/start` on `https://<pod>-ing.<domain>.informaticacloud.com/dbmi/public/api/v2/...` | [Mass Ingestion & CDC](../06-cdc-ingestion) |
| publishes a CAI process | `POST https://<pod>-cai.<domain>.informaticacloud.com/active-bpel/asset/v1/publish` | [Application Integration (CAI)](../07-app-integration) |

`diassetpromotion` import lands asset definitions only. `jobmanagement` runs only already deployed or published tasks.

**Everything else in the old "MCP can't write" list fell:** connection create, update and test; connector enablement on
the agent; run, monitor and stop; asset export and import; glossary and classification writes; role assignment
(L-MCP-002). The universal limit remains: MCP sits on the same service APIs, so it does not widen what those APIs allow.

---

## 6. Access: endpoints, privileges, auth

- **Endpoint.** Take `serverEndpointUrl` from the registry, or from the server's Configuration tab. Do not build it by
  hand. Two host patterns have been recorded: `https://a2e-prod-<pod>-mcp.<domain>.informaticacloud.com/mcp-servers/public/...`
  in older examples, and `https://mcp.<domain>.informaticacloud.com/mcp-servers/public/<context>` in current registries
  (L-MCP-029).
- **Auth**, in detail in [02](02-mcp-auth-oauth-clients.md):

| Method | Header |
|---|---|
| session ID | `IDS-SESSION-ID: <sessionId>` |
| JWT | `Authorization: Bearer <jwt>`. For the DQ agent, both headers were sent together. |
| OAuth client credentials (recommended for daemons) | `Authorization: Bearer <access token>` |

- **Each server holds its own session.** A 401 on one server says nothing about the others (L-MCP-025).
- **Privileges** (vendor, chapter 3):
  - feature privileges **Execute Managed MCP Servers** and **View Managed MCP Servers**;
  - asset privileges **MCP Server** and **Deployed MCP Server**, for *composite* servers you build.

  Admin and Designer hold them by default. Operator can run but cannot create or set permissions on composite servers.

---

## 6a. October 2026 platform changes (documented, L-MCP-133)

From the vendor's October 2026 What's New (published 2026-11-10), read 2026-11-19; none of this was exercised yet.

| Change | What it means for you |
|---|---|
| **Protocol 2026-07-28** (stateless MCP) over streamable HTTP, in dual-era mode | clients on 2025-06-18 keep working; MCP Python SDK v2 is supported |
| **OAuth renames**: the OAuth 2.1 server is now "Informatica OAuth Server (Authorization Code Grant)", the OAuth 2.0 one "Informatica OAuth Server (Client Credentials Grant)"; clients are "Authorization Code" and "Client Credentials" clients | the same two flows as [02](02-mcp-auth-oauth-clients.md), new labels in the UI |
| **OAuth scopes** for Authorization Code clients: `mcp:tools:read`, `mcp:tools:write`, `mcp:tools:execute`, and `mcp:resources:read` for resources | give a human-in-the-loop client only the scopes it needs; clients created before the release inherit all three tool scopes |
| **MCP resources**: read-only API, File or Zip resources (for example skill files) on a new Resources tab | check a server's Resources tab for vendor skill files before you write your own |
| **Tool lifecycle states** (Preview, Active, Deprecated) per server and per tool; the Actions tab is now **Tools**; a Configuration tab holds connection snippets | check a tool's state before you build on it |
| **MCP Monitoring**: invocations, error rate, average/P95/P99 duration, connected clients, CSV export, 90 days kept; needs the "View MCP Monitoring" privilege | the first vendor-side view of what your agents call |
| **More marketplaces**: the shared servers are also offered through Databricks Marketplace and MuleSoft Anypoint Exchange ("not all servers on all marketplaces") | see [07](07-ecosystem-plugins-registries-community-tools.md) §2 for every place they are listed |

Not confirmed in any official page read on 2026-11-19: A2A support (announced in May 2026 for the "Fall 2026 release"),
GA of external MCP tool connections, and an MCP-specific meter (the metering page answered 404).

---

## 7. Laws that bound every MCP design

1. **MCP is a calling convention, not a network position (L-MCP-006).** A managed server runs in
   Informatica's cloud and cannot reach a private database that only a Secure Agent reaches, so MCP never replaces the
   agent. Editing an MCP proxy's code cannot bypass a server-side check. Judge a server by its action list, not by the
   word "MCP".
2. **Verbs do not apply (L-MCP-007).** Every MCP call is an HTTP POST of a JSON-RPC body naming an action. Read or write
   intent lives in the action name, so a REST verb matrix is meaningless for MCP.
3. **MCP looks free, the backing calls are not (L-MCP-026).** During the AI Agent Engineering preview, MCP usage itself
   is not monetized, but every backing CDGC, CDI, Marketplace or MDM call bills IPUs at the service rate card. An agent
   looping on an orchestration prompt can burn real consumption while the MCP line reads zero.
4. **Availability is per org, and per machine.** The documented catalog is a ceiling, not a guarantee. A locally
   connected agent server is a separate thing again.

---

## 8. Composite servers, tool connections and AI Agent Engineering

- **The builder is being retired (L-MCP-081).** A vendor support notice (May 2026) sunsets the standalone AI
  Agent Engineering builder: the vendor-hosted MCP servers of this page stay generally available, and CLAIRE's agents
  become skills callable over MCP, A2A or an SDK (preview announced). **External MCP servers as agent tools**
  (`TOOL_CONNECTION`) exist only on orgs that were in the private preview. A newer org offers only "Composite MCP Server"
  (CAI processes exposed as tools), its CAI connection types have no MCP entry, and the tool-connection routes answer like
  a bogus twin. That is not an entitlement to ask for. Invert the design: your own agent (any MCP client) calls these
  servers plus your own MCP server through one aggregating gateway (L-MCP-082), with a per-upstream tool-inventory cache
  (L-MCP-083: about 26 s per call without it) and client timeouts (L-MCP-084: an upstream HTTP 500 hangs the call).
- **Composite MCP servers** (`MCP_SERVER` objects) are servers you assemble in AI Agent Engineering. **Tool connections**
  (`TOOL_CONNECTION`) are Application Integration connections to an external MCP server (URL plus bearer token), on
  private-preview orgs only (see above).
- **Composite server prerequisites and lifecycle (documented by the vendor, not exercised; L-MCP-119).**
  1. The CAI process behind it is **active** and published as an API, deployed with **Basic Authentication** (a process
     deployed with anonymous access cannot be used), uses the **REST/SOAP binding**, runs on the **Cloud Server** (not a
     Secure Agent), and is **not** restricted to accept requests only from the API Gateway.
  2. Create the server: pick the process and the operations to expose as tools.
  3. Deploy it: each deployment creates an instance agents can call; one server can be deployed several times as
     separate instances.
  4. After the process changes, update the server and refresh every deployed instance.

  Documented limits: 1,000 requests per minute and a 1 MB payload (L-MCP-089). Plan composite tools as
  cloud-hosted CAI processes with Basic Auth, or bypass composites and expose your own tools through your own MCP server
  or gateway (L-MCP-082). CLAIRE GPT cannot call a composite server or any other MCP tool:
  [03](03-claire-gpt-prompting-rules-patterns.md) §10 lists the routes that do change data.
- **Test a trivial MCP tool connection first in a new org (L-MCP-012).** In one org, New Tool → MCP Tool →
  Token Authentication (prefix `Authorization:Bearer `) → **Fetch Actions** made
  `POST.../a2e-flow-mgmt-svc/api/v1/mcp/fetch-actions` return **401 from IDMC itself**. The request never reached the
  MCP server (its access log stayed empty), and Save was a no-op, although the user held Admin plus Designer. That is most
  likely an entitlement or licence limit of that org.
  - Template worth reusing: the Agent Hub "Business Insights AI Agent using CDGC Metadata Discovery" (text-to-SQL
    grounded in CDGC). Swap its Snowflake/Databricks execute tools for your MCP tools. The model can be any configured
    provider deployment.
- **Migration (L-CAI-027; L-MCP-013 overturned by L-MCP-081).** A v3 export scoped by **tag** misses untagged
  `MCP_SERVER` and `TOOL_CONNECTION` objects: export them as an extra package. Importing a `TOOL_CONNECTION` failed with
  `MigrationSvc_031` "Internal error" in several jobs, even with the live URL and token supplied. On a private-preview
  org, recreate it in the **Application Integration designer** (MCP connection form; it is not offered under Data
  Integration New Asset), re-enter the token, and attach it to the MCP server object; a newer target org cannot hold it
  at all (first bullet). See [Migration & Org Management](../12-deploy-migrate).
- **Your own MCP servers** (MCP Toolbox for Databases, read-only identities, denylists) are covered in
  [04](04-agent-style-mcp-async-orchestration-custom-shims.md) §6.

---

## 9. The CLAIRE agent MCP server (class 2) in one paragraph

The CLAIRE orchestrator is reached at `<claire_api_url>/claire-orchestrator-ai-agent/api/v1/mcp` with a two-call identity
JWT. It is a read-only orchestration interface: it cannot provision agents, connections or assets (L-MCP-010). Its loop is
`new_conversation` → `OrchestratorSkill` (or `MdmOrchestratorSkill`) → `working` (no arguments) until a sentinel. It
answers only from cataloged content (L-MCP-043). It can list **0 tools** for an org, and a local MCP config can silently
point at another org (L-MCP-033). Full operating manual: [04](04-agent-style-mcp-async-orchestration-custom-shims.md).
CLAIRE GPT in the browser is covered in [03](03-claire-gpt-prompting-rules-patterns.md).

---

## 10. Overturned beliefs (kept so nobody re-learns them)

| Belief | Held | Overturned by | Lesson |
|---|---|---|---|
| "MCP servers are roadmap, not shipping" | before 2026-07-25 | The April 2026 guide documents shipping servers | L-MCP-077 → L-MCP-009 |
| "Exactly five managed servers / 11 actions / one write; '5 to 10' is unverified; only 2 of 5 exposed" | 2026-07-25 to 2026-07-26 | The September registry lists 19 servers, ~140 tools | L-MCP-069 → L-MCP-001 |
| "`GET /public/core/v3/mcpServers` is the org registry; a 404 means no vendor server is reachable" | 2026-07-25 | The registry lives on `hdm.<domain>/a2e-mcp-asset-mgmt-svc/api/v1/mcp-servers` | L-MCP-070 → L-MCP-001 |
| "MCP is DQ-only and cannot cross the integration walls" (2 servers tested) | 2026-09-23 (pm) | Full registry enumeration the same day | L-MCP-071 → L-MCP-001 |
| "AI Agent Engineering is not entitled" (`AI_AGENT`/`GENAI_AGENT`/`MCP_SERVER` counts 0) | 2026-07-04 to 2026-07-08 | 19 managed servers registered; the count-0 census never proved absence (disputed) | L-MCP-075 → L-MCP-011 |
| "Nothing in MCP touches connections; no MCP server fronts administration; glossary is UI-only on both" | 2026-07-25 | `connectionmanagement`, `usermanagement`, `cdgccatalogenrichment` (2026-09-23), and CDGC REST writes | L-MCP-078 → L-MCP-049 |

---

## 11. Open questions

- Is the ~140 tool figure right? The recorded per-server counts sum to ~120. The October 2026 server pages add four
  servers and about 85 tools (32 in `policymanagement`, 35 in `idmcassetdocumentation`), so a 23-server org could expose
  well over 200: re-list before you quote a number.
- The Job Management page mentions `resume_taskflow_fault_retry` and the Connection Management page mentions
  `list_connector_types`, `get_connector_schema`, `list_connection_runtime_environments` and `resolve_dynamic_attributes`,
  none of which is in their documented tool lists. Check `tools/list`.
- Does `cdgcdataqualityscore.get_asset_score` return Data Profiling scorecard values, or only catalog scores?
- What do the write tools in `cdgccatalogenrichment` and `usermanagement` require (bodies, roles)? They were listed, not
  exercised, in these sources.
- Is the `hdm` host always `hdm.<domain>`, or pod-qualified in some regions? AI Agent Engineering was also seen at
  `hdm.<pod>.informaticacloud.com` in one note.
