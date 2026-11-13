# Capability Map: what IDMC can do headless

**Answers:** Can I do X without the UI? With which route, on which host, proven when, and which doc and lessons say so?
Which layer (IDMC or an API gateway) should own an integration edge?

**Read when:** before you promise, plan or estimate anything headless, before you call something a wall, and when you
choose between CDI, CDC, CAI and an API gateway for a flow.

**Key rules:**
- **No cell is a "no" to a user.** R, UI and U cells are where the workaround ladder starts, not where the answer ends:
  work it in your org before saying something is not possible, and never answer a gap by suggesting another technology
  ([New Pipeline Milestones](<08 New Pipeline Milestones - any source, any target.md>), the two rules).
- The services and connectors named here are the ones probed so far; a connector, format or operation that is not
  listed is untested, not unsupported or forbidden: anything IDMC can do is in scope. Look for the native IDMC route
  first; Python only as a bridge when no IDMC route works.
- A cell is a dated verdict for some org: check its date and re-probe in yours before promising it (L-METHOD-034,
  L-METHOD-035).
- UI-ONLY means one click in something the org owns, never a gap; UNTESTED is not unsupported (L-METHOD-023,
  L-METHOD-036).
- Full pushdown and the remaining transformation types are headless now; the session log is the proof of pushdown
  (L-CDI-202, L-CDI-204).
- Real-time application calls belong to the API layer; everything analytical runs on IDMC (CDC, CDI, CAI for
  API- or event-shaped analytics) (L-CAI-088).
- CAI invocations are not jobs; every task and taskflow run is (L-IPU-041, L-CAI-038).

**Related:** [The Laws of Headless IDMC](<02 The Laws of Headless IDMC.md>) · [Error Triage](<04 Error Triage.md>) ·
[Overturned Beliefs](<../13 - Lessons Learned/Overturned Beliefs.md>) ·
[MCP vs REST](<../09 - CLAIRE & MCP/05 MCP vs REST - When to Use Which.md>) ·
[UI Automation with Playwright](<../14 - Claude Working Methods & Tooling/04 UI Automation with Playwright.md>)

**Last verified:** 2026-11-03 (evidence 2026-06-27 to 2026-11-03; each row carries its own date).

> One page answering "can I do X without the UI?" for every IDMC service this KB covers. The matrix gives the state per
> operation; the tables under it give the dated status, the route in one line and the doc and lessons behind it. Most of
> the July "UI-only" cells turned headless in September and October 2026, so re-probe anything older than its last
> proof before promising it.

---

## How to read it

| Code | State | Meaning |
|---|---|---|
| **P** | PROVEN <date> | a live call and its read-back were observed on that date, in some org (re-verify in yours) |
| **D** | DOC | a vendor guide documents it; nobody exercised it here |
| **R** | REJECTED (<code>) | the platform refused it; a 405 means the verb does not exist |
| **U** | UNTESTED | nobody checked: unknown, not unsupported |
| **UI** | UI-ONLY | entitled and working, but a human (or browser automation) clicks; each one is dated and re-probeable |
| **SH** | NEEDS SHELL | no browser needed, but a shell on the host that runs the Secure Agent |
| **X** | DISPUTED | dated records disagree; the row says what to trust |
| **—** | not applicable | the operation does not exist for that object |

Hosts and headers are in [Pods, Hosts & Service Planes](<../01 - Access, Auth & Orgs/01 Pods, Hosts & Service Planes.md>):
`<serverUrl>` = `https://<pod>.<domain>.informaticacloud.com/saas`; v2 paths take `icSessionId`, v3 paths
`INFA-SESSION-ID`, FRS and selections `IDS-SESSION-ID`, and `idmc-api` / `cdgc-api` / `<pod>-mdm` the three identity
headers.

## The matrix at a glance

| Service | Read | Create | Update | Delete | Run | Publish / deploy | Author / design |
|---|---|---|---|---|---|---|---|
| 1 Platform: org, users, groups, roles | P | P | R (users: re-create) · U (groups) | P | — | — | UI (sub-org licences, auth mode) |
| 2 Secure Agent and runtime environments | P | P + SH (install) | P (selections PUT, engine configuration form) | P | SH | — | UI (serverless runtime) |
| 3 Connections | P | P · UI once per new add-on type | P | P | P (test) | — | — |
| 4 CDI mappings | P | P (package) · R (verb) | P (re-import) | P | — | — | P (route 5; full pushdown is a task setting, section 4) |
| 5 Mapping tasks | P | P | P · R (retarget on real mappings) | P | P | — | — |
| 6a Linear taskflows | P | P | P | P | P | — (none needed) | — |
| 6b Advanced taskflows | P | P (import) | P (import) | U | R (job API) | R · X | UI (designer) |
| 7 Schedules | P | P | P | P | P (bind) | — | — |
| 8 Database Ingestion and CDC | P | P | — (no verb: re-import) | P (FRS) | P | P | — |
| 9 CAI | P | P (package) · R (verb) | P (re-import, connection secrets with asset/v1/update) · D | P (FRS) · UI (stuck assets) | P (invoke, listener start and stop) | P · UI (API activate) | P (Kafka and AMQP listeners, by package) · UI (human tasks, file listeners) |
| 10 CDQ assets | P | P (rule-spec clone, dictionary) | D (dictionary rows) | P (FRS) · D | via a CDI mapping | — | UI (rule logic, other assets) |
| 11 Data Profiling | P | P | P | D | P | — | P (rule occurrences) |
| 12 CDGC catalog sources and scans | P | P | P | P (purge) · UI (definition) | P (cancel too) | — | P (lineage connection assignment, DQ rule occurrences) |
| 13 CDGC glossary, classification, stewardship | P | P | P | P · X (Published terms) | — | — | UI (bulk accept, stewards, DAM) |
| 14 CDGC search, lineage, Marketplace | P (lineage hop by hop) · MCP (lineage) | P (Marketplace, curated lineage edges) | D | P (curated lineage edges) · U | — | UI (delivery templates) | P (curated lineage edges) |
| 15 MDM SaaS | P (search) · X (by id) | P (ingest) | D (entity-xref) | D (soft delete) | UI (jobs) | UI · X (model publish) | UI (Modeler) · P (clone) |
| 16 Managed MCP, CLAIRE, CLAIRE GPT | P | P (OAuth clients) | U | U | P (tools/call) | — | UI (tool connections on private-preview orgs only, L-MCP-081; CLAIRE GPT chat) |
| 17 Migration: export/import and FRS | P | P (import) | P (OVERWRITE) | P (FRS) | — | — | P (packages) |
| 18 Metering and licences | P | — | — | — | — | — | UI (licence inventory) |

**Which layer owns which edge** (detail and the per-edge table in [CAI Runtime](<../05 - Application Integration (CAI)/02 CAI Runtime - Invoke, URLs & Control.md>) §10.7; fronting APIs with a gateway in §10.8):

| Edge | Owner | Mechanism | See |
|---|---|---|---|
| Real-time application work: every button's API into the operational database, the app's own real-time sync into the CRM | API layer (an API gateway such as MuleSoft in front of the app's APIs) | the app API behind the gateway | L-CAI-088 |
| Analytics and BI integration: sources into the warehouse (raw to gold, DQ, golden records, catalog), the batch golden sync to the CRM, API- or event-shaped analytical integrations (usage events into the warehouse, activation from the warehouse into the app's API) | IDMC | CDC (Database Ingestion) and CDI with native connectors; CAI for the API- or event-shaped legs; a real-time DQ check as a CAI process the API layer calls, so the rules exist once | L-CAI-088 |
| BI or analytics data through the API layer | never | it bypasses lineage, governance and DQ; and moving work into CAI saves no jobs, because CAI invocations are not jobs | L-CAI-088, L-CAI-038 |

---

## 1. Platform: login, org, users, groups, roles

| Operation | Status | Route | See |
|---|---|---|---|
| Log in (v3, v2, identity) | P 2026-09-28 | `POST https://<domain>.informaticacloud.com/saas/public/core/v3/login`, `/ma/api/v2/user/login`, `/identity-service/api/v1/Login` | [Login, Sessions & Tokens](<../01 - Access, Auth & Orgs/02 Login, Sessions & Tokens.md>) · L-AUTH-018, L-AUTH-019, L-AUTH-021 |
| Mint a JWT | P 2026-09-29 | `POST` or `GET.../identity-service/api/v1/jwt/Token?client_id=<cdlg_app or idmc_api>&nonce=<n>` with `IDS-SESSION-ID` | L-AUTH-022, L-AUTH-023 |
| Read the org | P 2026-09-28 | `GET <serverUrl>/api/v2/org` (v2 id, `orgUUID`, parent, sub-orgs; no job limit) | [Identify the Org](<../01 - Access, Auth & Orgs/03 Identify the Org Before You Write.md>) · L-AUTH-049 |
| Read users, groups, roles, privileges | P 2026-07-25 | `GET /public/core/v3/users`, `/userGroups`, `/roles`, `/privileges` | [Users, Roles & Permissions](<../01 - Access, Auth & Orgs/04 Users, Roles & Permissions.md>) · L-AUTH-062 |
| Create a user | P 2026-07-25 | `POST /public/core/v3/users` (key `name`; `groups` as plain id strings) → 201 | L-AUTH-057 |
| Edit a user in place | R (405, July) | delete and re-create after a snapshot; `PUT /users/<id>/addRoles` is live but never seen to succeed | L-AUTH-059, L-AUTH-066 |
| Delete a user | P 2026-09-28 | `DELETE /public/core/v3/users/<userId>` → 204 | L-AUTH-058, L-CLEAN-009 |
| Create or delete a group with roles | P 2026-07-25 | `POST /public/core/v3/userGroups` (`roles` as id strings; read back); DELETE works; PUT and PATCH U | L-AUTH-060 |
| Read the audit log | P (securityLog) · X (v2 auditlog) | `GET /public/core/v3/securityLog?limit=N` | L-AUTH-075 |
| Switch org | R (404 on every path) | an admin action | L-AUTH-050 |
| Allocate licences to a sub-org | UI | the parent's Administrator > Sub-Organizations > Licenses | L-IPU-035 |
| Switch the org's REST authentication to JWT | UI (admin setting) · D (session-ID auth deprecated; JWT to become the default) | Administrator settings; put every client behind a `session|jwt` switch with timed refresh; JWT values are capped at 2,000 characters (documented) | [Login, Sessions & Tokens](<../01 - Access, Auth & Orgs/02 Login, Sessions & Tokens.md>) §6 · L-AUTH-032, L-AUTH-033 |

## 2. Secure Agent and runtime environments

| Operation | Status | Route | See |
|---|---|---|---|
| Read agents and deployed engines | P 2026-07-26 | `GET /api/v2/agent`, `/agent/<agentId>`, `/agent/details/<agentId>` (`agentEngines[]`) | [Secure Agent](<../02 - Secure Agent & Connections/01 Secure Agent - Install, Run & Tune.md>) · L-AGENT-020 |
| Read runtime environments | P 2026-07-26 | `GET /api/v2/runtimeEnvironment` (its `readyToRun` is stale: read per agent) | L-AGENT-021, L-AGENT-035 |
| Install and register an agent | P 2026-09-28 + SH | `GET /api/v2/agent/installerInfo/linux64` (token), install, `infaagent startup`, `consoleAgentManager.sh configureToken`; a reinstall on the same host with `configureTokenWithRuntime` into the same runtime reuses the agent id (2026-10-29) | L-AGENT-001, L-AGENT-002, L-AGENT-111 |
| Create a runtime environment | P (by registration) | the agent creates its own; `POST /api/v2/runtimeEnvironment` exists (empty body 400) | L-AGENT-035 |
| Create a serverless runtime environment | UI | both REST forms 404 | [Runtime Environments](<../02 - Secure Agent & Connections/02 Runtime Environments - Services & Connectors.md>) §1 |
| Select services and connectors | P 2026-09-28 | `GET` then `PUT https://<pod>.<domain>.informaticacloud.com/runtime/api/v2/runtimeEnvironment/<reId>/selections/ui` (`IDS-SESSION-ID`) | L-AGENT-039, L-AGENT-040 |
| Select them over MCP | P 2026-09-23 | `secureagentmanagement` → `update_runtime_environment_selections` | L-AGENT-080 (overturned), L-MCP-002 |
| Enable through the agent routes | R (router artifacts, no-ops) | `POST /api/v2/agent/service` (403 APP_13401, 500 CMN_001), `selectiveservices` (500), `POST /api/v2/agent/<id>` (no-op) | L-AGENT-044, L-AGENT-031 |
| Delete an agent or runtime environment | P 2026-09-28 | `DELETE /api/v2/agent/<id>`, `DELETE /api/v2/runtimeEnvironment/<id>`; a GET answering 403 = gone | L-CLEAN-006 |
| Start, stop, restart, supervise | SH | `infaagent startup` / `shutdown` under a systemd unit (never a run-command scope) | L-AGENT-009, L-AGENT-011 |
| Enable and check the Process Server | P 2026-09-28 (enable) · SH (repair) | the selections PUT; `https://localhost:7443/process-engine/status` on the host | [Process Server](<../05 - Application Integration (CAI)/04 Process Server on a Secure Agent.md>) · L-CAI-066, L-CAI-068 |
| Change engine configuration (System / Custom Configuration) | P 2026-09-29 (legacy form, UI session cookies) | `GET` then `POST https://<pod>.<domain>.informaticacloud.com/runtime/app/agent.do` (`displayUpdate`, then `actionMethod=update` with the whole `AgentForm` and its `csrfToken`); no REST verb; the cloud restarts DIS about 1.5 min later | [Secure Agent](<../02 - Secure Agent & Connections/01 Secure Agent - Install, Run & Tune.md>) §6.1 · L-AGENT-088 |
| Raise DTM concurrency and heap | P 2026-09-29 | a Custom Configuration row `Data_Integration_Server<major.minor>` / `TOMCAT_CFG` / `maxDTMProcesses` = N (default 2) plus the DTM `JVMOption1` row, through `agent.do`; verify `poolSize=N` in the new `tomcat_<ver>.log` and on the running JVM | [Secure Agent](<../02 - Secure Agent & Connections/01 Secure Agent - Install, Run & Tune.md>) §6.2 · L-AGENT-099 |
| Watch licence and engine changes | P 2026-09-30 (read-only poll) | `GET /public/core/v3/license/org/<orgIdV3>` and `GET /api/v2/agent/details/<agentId>` every 10 min; alert on content, not on `updateTime` | [Secure Agent](<../02 - Secure Agent & Connections/01 Secure Agent - Install, Run & Tune.md>) §12 · L-IPU-057 |
| Stage third-party JDBC drivers | P 2026-09-28 + SH | copy into `ext/connectors/thirdparty/informatica.jdbc_v2/common/`, restart | L-CONN-049, L-CONN-051 |
| Create a Local (on-agent) Spark advanced configuration | P 2026-10-26 | validate with `POST https://<pod>-ias.<domain>.informaticacloud.com/clustermanager/api/v1/clusterconfig/validation` (`cloud_type` LOCAL, `rteId`), save as an FRS `ATS_CLUSTER` document (`POST .../frs/api/v1/Spaces('SYS')/Documents`); the agent's Elastic Server service must be RUNNING; `/cis/api/v1/*` answers CMN_001 | [Runtime Environments](<../02 - Secure Agent & Connections/02 Runtime Environments - Services & Connectors.md>) · L-AGENT-114 |
| Fail tasks and connections over from a downed Hosted Agent | P 2026-11-03 | `POST /api/v2/mttask/<id>` with `runtimeEnvironmentId` changed (17 tasks in seconds), and `POST /api/v2/connection/<id>` with `runtimeEnvironmentId` and `connParams.agentGroupId` changed and the secrets re-supplied, because a lookup resolves its connection through the connection's own runtime; full-body backups for the undo | [Runtime Environments](<../02 - Secure Agent & Connections/02 Runtime Environments - Services & Connectors.md>) · L-ENV-100, L-CONN-132, L-AGENT-117 |

## 3. Connections

| Operation | Status | Route | See |
|---|---|---|---|
| Read connections and connector types | P 2026-07-25 | `GET /api/v2/connection[/<connId>]` (secrets masked); `GET /api/v2/connector` is a type catalog, not what runs | [Connections](<../02 - Secure Agent & Connections/03 Connections - Create, Test, Update, Delete.md>) · L-CONN-016, L-CONN-021 |
| Create | P 2026-09-12 | `POST /api/v2/connection` with `type:"TOOLKIT_CCI"`, `instanceName`, `connParams` (flat files: native type `CSVFile`) | L-CONN-001, L-CONN-065 |
| Create the first one of a new add-on type | UI (July; U since selections became headless) | one Administrator save registers the type, then REST manages it | L-CONN-005 |
| Update | P 2026-09-28 | `POST /api/v2/connection/<connId>` with the full body and the secret re-supplied | L-CONN-006, L-CONN-007 |
| Delete | P 2026-09-28 | `DELETE /api/v2/connection/<connId>` (403 REPO_10242 while mappings use it) | L-CONN-017 |
| Test | P 2026-09-23 | `GET /api/v2/connection/test/<connId>` (0 IPU); `POST /api/v2/connection/test` gives 500 APP_21000; for a connector that renews a delegated OAuth token a pass proves only that the token renews | L-CONN-014, L-CONN-101 |
| Create, update, test over MCP | P 2026-09-23 | `connectionmanagement` → `create_connection`, `update_connection`, `test_connection_by_id` | [MCP vs REST](<../09 - CLAIRE & MCP/05 MCP vs REST - When to Use Which.md>) · L-MCP-002 |
| Browse source objects | P (per connection) · not evidence of absence | `GET /api/v2/connection/source/<connId>?type=table`; it answered `200 []` for working PostgreSQL connections, so know the object path format and confirm through a consumer | L-CONN-016, L-CDI-017 |
| Browse objects as the designer does (proves a delegated token can read metadata) | P 2026-10-06 | `GET https://<pod>.<domain>.informaticacloud.com/da/w3.model/object/cloud/saas:<v2ConnId>@com.informatica.metadata.saas.Connection/search/?connKind=READ&searchRequest=<JSON: pageNumber, maxRecordsCount, context txType SOURCE_TYPE, engineType CLOUD_NATIVE>` with a designer session → `totalRecords`, `records[].attributes` | [Connections](<../02 - Secure Agent & Connections/03 Connections - Create, Test, Update, Delete.md>) §3 · L-CONN-101, L-CONN-100 |
| Read a connector's formats and engines | P 2026-10-26 | `GET <serverUrl>/api/v2/connector/metadata?connectorName=<name>`: each formatter in `cciMeta` lists its `supportedEngineTypes` (spark only = an advanced-mode mapping) | [Connector Notes](<../02 - Secure Agent & Connections/04 Connector Notes (BigQuery, PostgreSQL, Salesforce, JDBC, Flat File).md>) · L-CONN-130, L-CONN-129 |

## 4. CDI mappings (design objects)

| Operation | Status | Route | See |
|---|---|---|---|
| List mappings | P 2026-09-29 | `GET /api/v2/mapping` (v2 id, `assetFrsGuid`, `tasks[]`) | [CDI Object Model](<../03 - Data Integration (CDI)/01 CDI Object Model.md>) · L-CDI-001 |
| Read a mapping's internals | P 2026-09-22 | v3 export; the IMF JSON is in `bin/@N.bin` | L-CDI-027 |
| Create with a REST verb | R | `POST /api/v2/mapping` (400), `POST /public/core/v3/objects` (405) | L-CDI-020 |
| Create by package clone (routes 3, 4) | P 2026-07-04, 2026-08-19 | export, edit the IMF or swap a same-type connection GUID, re-checksum, import | [Mappings Headless](<../03 - Data Integration (CDI)/02 How Claude Builds Mappings Headless.md>) · L-CDI-026, L-CDI-028, L-CDI-041 |
| Create by synthesis (route 5) | P 2026-09-29 | spec → IMF JSON → `DTEMPLATE` package → import (REUSE, then OVERWRITE to rebuild) | L-CDI-033, L-CDI-034, L-CDI-035 |
| Update (including retarget) | P 2026-09-29 | rebuild the package and import OVERWRITE under the same GUID | L-CDI-145 |
| Move a mapping to another connector type | U headless (a package edit did not) | synthesize a mapping for the new adapter | L-CDI-031 |
| Delete | P 2026-09-28 | `DELETE /api/v2/mapping/<id>` once `tasks[]` is empty | L-CDI-052 |
| Transformations proven headless | P 2026-09-29 to 2026-10-03 | Source, Target, Filter, Expression (variable ports), Sorter, Joiner (normal, master and full outer, chained, sorted self-join), Router, Aggregator, Union, Rank, Sequence Generator, connected and unconnected Lookup, Data Masking, Rule Specification, Cleanse, Deduplicate, Normalizer, mapplets, in-out parameters, Update/Upsert/Delete/Data Driven targets; class shapes from the Mapping Designer's JavaScript bundle and `GET <pod>/da/w3.imf/iclass/?infaToken=<icSessionId>` | [Mappings Headless](<../03 - Data Integration (CDI)/02 How Claude Builds Mappings Headless.md>) §7 · L-CDI-033, L-CDI-204 |
| Transformations not yet headless | U | the Data Quality transformation and Update Strategy: one UI author, then clone | L-CDI-041, L-CDI-204 |
| Create an intelligent structure model from a sample file | P 2026-10-06 | six calls on `https://<pod>.<domain>.informaticacloud.com`, about 4 s: `GET /saas/api/v2/intelligentstructure/getAtlanticWidget`; Structure Discovery `validateWidget`, `upload`, `RunDataPreview` and `getStructure` (the session as cookie `USER_SESSION` and header `IDS-SESSION-ID`, and `X-CSRF-TOKEN` on every POST after `validateWidget`); then `POST /saas/api/v2/intelligentstructure/create?containerId=<v3 folder id>`; the model reads back on v2 and v3 | [Mappings Headless](<../03 - Data Integration (CDI)/02 How Claude Builds Mappings Headless.md>) §10 · L-CDI-223, L-CDI-224 |
| Parse documents with a Structure Parser in a mapping | P 2026-10-07 (a designer-built mapping) · P 2026-10-26 (the PDF itself as a header-less flat-file source, one row kept by a filter because `rowLimit` is ignored on flat-file reads, re-imported OVERWRITE; L-CDI-275) | a warehouse view that lists the documents (one row per file, filtered per flow in the source's Advanced filter), an Expression that turns each server path into the local download path for the parser's `FilePath`, Passthrough ticked on every output group (file name and path on each parsed row), `Unidentified` landed, one flow per document type in Flow Run Order; the ports take the model's types, and the mapping stores `"@<v3 id>"` plus a copy of the model (Synchronize after a model edit) | [Mappings Headless](<../03 - Data Integration (CDI)/02 How Claude Builds Mappings Headless.md>) §10 · L-CDI-231, L-CDI-229, L-CDI-230 |
| Read a SharePoint library and download its documents with CDI | P 2026-10-06 (a designer-built mapping) | the SharePoint Online connector with a refresh token minted for `https://<tenant>.sharepoint.com/.default offline_access` (a Graph-scoped one reads 0 objects); one object per list or library; a read returns the library's root rows (12 properties) and downloads every file, recursively, to the connection's `Attachment_File_Path`; one row per file through an Indirect File Path file of absolute, URL-encoded wildcard patterns | [Connector Notes](<../02 - Secure Agent & Connections/04 Connector Notes (BigQuery, PostgreSQL, Salesforce, JDBC, Flat File).md>) §6 · L-CONN-102, L-CONN-103, L-CONN-100 |
| BigQuery full pushdown (full SQL ELT) | P 2026-10-01 | `GET /api/v2/mttask/<id>`, set `sessionProperties` `{"Pushdown Optimization":"Full","Allow Temporary View for Pushdown":"Yes"}` and `enableCrossSchemaPushdown: true`, POST the full body back; proof = `OPT_63367` and one `INSERT INTO` per target in the session log; targets run serially, so small multi-target mappings get slower | [Mappings Headless](<../03 - Data Integration (CDI)/02 How Claude Builds Mappings Headless.md>) §9 · L-CDI-202, L-CDI-203 |
| Merge two mappings into one | P 2026-10-26 | transplant transformations between exports: re-point every `$$class` by class name, fresh `$$ID`s, refresh the DTEMPLATE zip, import OVERWRITE under the kept mapping's id (its task and taskflow stay) | [Mappings Headless](<../03 - Data Integration (CDI)/02 How Claude Builds Mappings Headless.md>) · L-CDI-278 |
| Advanced-mode (Spark) mappings | U (generated headless; an export is an `AtScaleDTemplate`, `AT_SCALE_MAPPING`) · UI wall 2026-10-26 for CLAIRE PDF parsing in the designer (Discover Structure never enables Select) | parse documents in a standard mapping on a Secure Agent instead; check the documented advanced-cluster limits first (8 vCPU, 32 GB) | [Mappings Headless](<../03 - Data Integration (CDI)/02 How Claude Builds Mappings Headless.md>) · L-CDI-276, L-CDI-277 |
| Find designer-only Invalid badges | UI (browser automation, 2026-10-26) | open `.../diUI/products/integrationDesign/main/<mapping, mct or linearTaskflow>/<frsId>/read`, read the badge and the Validation panel; no API reports a stale rule-spec copy | [UI Automation](<../14 - Claude Working Methods & Tooling/04 UI Automation with Playwright.md>) · L-UI-036, L-DQ-126 |

## 5. Mapping tasks

| Operation | Status | Route | See |
|---|---|---|---|
| Read | P 2026-09-29 | `GET /api/v2/mttask/<id>` (the detail has `frsGuid` and `scheduleId`; the lists hide both) | [Mapping Tasks](<../03 - Data Integration (CDI)/03 Mapping Tasks - Create, Update, Run, Monitor.md>) · L-CDI-008 |
| Create over a Copy Data template | P 2026-09-23 | `POST /api/v2/mttask` with full `$Source$` / `$Target$` (clone a proven task) | L-CDI-022, L-CDI-047 |
| Create over a real mapping | P 2026-09-29 | `POST /api/v2/mttask {"@type":"mtTask","name","mappingId","runtimeEnvironmentId"}` | L-CDI-037 |
| Update | P 2026-09-28 | `POST /api/v2/mttask/<id>` with the full body (PUT is 405) | L-CDI-046, L-CDI-135 |
| Retarget a task over a real mapping | R (200, silent no-op) | change the mapping instead (section 4) | L-CDI-050 |
| Delete | P 2026-09-29 | `DELETE /api/v2/mttask/<id>`; a GET answering 403 = gone; REPO_52013 = still bound to a schedule | L-CDI-052, L-CDI-053 |
| Run and monitor | P 2026-09-28 | `POST /api/v2/job {"taskId","taskType":"MTT"}`, then `GET /api/v2/activity/activityLog?taskId=<id>&rowLimit=1` until the `runId` matches | L-CDI-056, L-CDI-059 |
| Run over MCP | D (tools listed live 2026-09-23) | `jobmanagement` → `run_mapping_task`, `get_job_status`, `stop_running_job` | L-CDI-068 |
| Read a run's session log | P 2026-10-01 | `GET /api/v2/activity/activityLog/<entryId>/sessionLog` (`Accept: */*`; `<entryId>` = the activity-log row's `id`, not the `runId`) → plain text | [Mapping Tasks](<../03 - Data Integration (CDI)/03 Mapping Tasks - Create, Update, Run, Monitor.md>) §9 · L-CDI-211 |
| Retry transient failures | P (orchestrator rule, 2026-09-29 to 2026-11-01) | one re-run on a transient signature (BigQuery 503, a staging upload error, `Temp_View` 409/404, a spurious "does not exist", Premature EOF, agent disconnection, too many simultaneous queries); never on "monthly limit", cast, null-into-non-nullable, permission or repository-save errors (L-CDI-287) | [Performance & Job Caps](<../03 - Data Integration (CDI)/07 Performance, Concurrency & Job Caps.md>) §4 · L-CDI-205 |
| Run more than 2 tasks at once on one agent | P 2026-09-29 (after raising the DTM pool) | section 2, "Raise DTM concurrency" | L-AGENT-099 |
| Vary a task's source SQL per run | P 2026-11-01 + SH (parameter file) | `$Source$.customQuery` works only when the mapping's source query is a parameter; for one mapping over many sources use an in-out parameter (`$$SRC_SQL`); SQL over about 4,000 characters goes in a per-task parameter file (`parameterFileName`, staged on the agent), not the parameter default (REPO_19001) | [Mapping Tasks](<../03 - Data Integration (CDI)/03 Mapping Tasks - Create, Update, Run, Monitor.md>) · L-CDI-284, L-CDI-285 |
| Read a Dynamic Mapping Task | P 2026-11-01 | v3 type `BATCH_MAPPING`; `GET https://<pod>.<domain>.informaticacloud.com/batch-mapping/api/v1/dynamictask/<v3 id>` (no `/saas`) returns groups, parameters and jobs | [CDI Object Model](<../03 - Data Integration (CDI)/01 CDI Object Model.md>) · L-CDI-289 |
| Create or run a Dynamic Mapping Task | P 2026-11-01 (create by v3 package import, audit `BATCH_MAPPING.CREATE`) · D (`POST /batch-mapping/api/v1/dynamictask`; MCP `run_dynamic_mapping_task`) | import a package; the documented POST and the MCP run tools are listed but not exercised | [CDI Object Model](<../03 - Data Integration (CDI)/01 CDI Object Model.md>) · L-CDI-289 |
| Move and tag | P 2026-09-29 | FRS `MoveEntities` (ids, schedules and history survive); `POST /public/core/v3/TagObjects` | L-CDI-016, L-CDI-054 |
| Publish or deploy | — | a mapping task runs as soon as it exists; a designer save of its mapping redeploys every task on it (`POST /saas/app/da/dTemplatesXHR.do?actionMethod=autodeploy`), so the next runs execute the saved mapping | L-CDI-228 |
## 6. Taskflows

**6a. Linear taskflows (v2 `workflow`)**

| Operation | Status | Route | See |
|---|---|---|---|
| Read | P 2026-09-28 | `GET /api/v2/workflow[/<wfId>]` (no `frsGuid`: resolve the v3 id by exact name) | [Taskflows & Schedules](<../03 - Data Integration (CDI)/04 Taskflows & Schedules.md>) · L-CDI-009 |
| Create | P 2026-09-24 | `POST /api/v2/workflow` with an ordered `tasks[]` of `workflowTask` entries | L-CDI-069 |
| Update | P 2026-09-24 | `POST /api/v2/workflow/<wfId>`, keeping the current `scheduleId` (omitting it unbinds) | L-CDI-069 |
| Delete | P 2026-09-28 | `DELETE /api/v2/workflow/<wfId>` (unbind its schedule first) | L-CLEAN-006 |
| Run and monitor | P 2026-09-28 | `POST /api/v2/job {"taskId":"<wfId>","taskType":"WORKFLOW"}`; the children are `entries[]` of its activity-log row | L-CDI-056, L-CDI-061 |
| Publish | — (none needed) | a linear taskflow runs as soon as it exists | L-CDI-069 |

**6b. Advanced taskflows (v3 `TASKFLOW`, Process Designer XML)**

| Operation | Status | Route | See |
|---|---|---|---|
| Read | P | `GET /api/v2/taskflow`; `TASKFLOW` objects in the v3 catalog | L-CDI-014 |
| Create or update | P 2026-09-25 (import) | generated Process Designer XML in a package, imported OVERWRITE | L-CDI-070 |
| Publish | R (API-made or FRS-copied: `AvrEntryNotFoundFault`) · X (a designer-created shell) | `POST https://<pod>-cai.<domain>.informaticacloud.com/active-bpel/asset/v1/publish` with the `.TASKFLOW.xml` path | L-CDI-070, L-CDI-193 |
| Run through the job API | R (403 UI_13430) | run the member tasks from a controller, or use linear taskflows | L-CDI-071, L-CDI-125 |
| Run a published one | D | its REST or SOAP endpoint; MCP `run_published_taskflow` | L-CDI-071 |
| Author parallel paths, decisions, Command Tasks | UI | the designer | L-CDI-082 |

## 7. Schedules

| Operation | Status | Route | See |
|---|---|---|---|
| Read | P 2026-09-28 | `GET /api/v2/schedule[/<id>]` (a deleted schedule's GET is an empty 200 shell) | [Taskflows & Schedules](<../03 - Data Integration (CDI)/04 Taskflows & Schedules.md>) · L-CDI-081 |
| Create | P 2026-09-28 | `POST /api/v2/schedule` with `startTime` (pod-local) and `startTimeUTC`, the day flags, a :05 boundary | L-CDI-073, L-CDI-074 |
| Update or end | P 2026-09-28 | `POST /api/v2/schedule/<id>`; to end, set both `endTime` and `endTimeUTC`; a v3 PATCH gives 400 V3API_007 | L-CDI-073, L-CDI-076 |
| Bind and unbind | P 2026-09-28 | POST the workflow or the mapping task with `scheduleId` (`null` unbinds), then read it back | L-CDI-075 |
| Delete | P 2026-09-28 | `DELETE /api/v2/schedule/<id>`; confirm with the list | L-CDI-081 |
| Audit every binding | P 2026-09-29 | the workflow details and **every** task's detail (the task list hides task-level bindings) | L-CDI-077 |

## 8. Database Ingestion (DBMI) and CDC

All DBMI routes are on `https://<pod>-ing.<domain>.informaticacloud.com` with `IDS-SESSION-ID`; ids are numeric.

| Operation | Status | Route | See |
|---|---|---|---|
| Read task definitions | P 2026-09-28 | `GET /dbmi/public/api/v2/task/details?taskId=<n>` (or `?pageSize=200`) | [DBMI over REST](<../04 - Mass Ingestion & CDC/01 DBMI over REST (create, deploy, run, stop).md>) · L-DBMI-006 |
| Read job status | P 2026-09-28 | `GET /dbmi/api/v1/task/<taskId>/job` (`job/status` answers 415) | L-DBMI-002 |
| Create | P 2026-09-22 to 2026-09-29 | `POST /dbmi/public/api/v2/task/create` (`general.location` = a project only) | L-DBMI-003, L-DBMI-004, L-DBMI-005 |
| Create by clone | P 2026-09-22 | a v3 package with the `.DBMI_TASK.dat` JSON | L-MIG-023 |
| Update | — (no update verb) | undeploy, re-import an edited export OVERWRITE; or create a new task and delete the old | L-DBMI-007 |
| Deploy | P 2026-09-22, 2026-09-28 | `POST /dbmi/public/api/v2/task/deploy/<taskId>` with `{}` (a new job id each time) | L-DBMI-003 |
| Start, stop, resume, undeploy | P 2026-09-28 | `POST /dbmi/public/api/v2/job/{start,stop,resume,undeploy}` with `{"jobId":<n>}` | L-DBMI-003, L-DBMI-008 |
| Run through the platform job API | R (403 UI_13404) | DBMI tasks are not v2 tasks | L-DBMI-010 |
| Delete | P 2026-09-26 | undeploy, then `DELETE https://<pod>.<domain>.informaticacloud.com/frs/api/v1/BaseEntities('<frsId>')` → 204 | L-CLEAN-005 |
| Deploy over MCP | R (no MCP verb) | use REST | L-MCP-003 |
| BigQuery target drivers | P 2026-09-28 + SH | the Simba JDBC set in the agent's `apps/Database_Ingestion/...` folders, then restart the agent | [DBMI Targets & Drivers](<../04 - Mass Ingestion & CDC/03 DBMI Targets & Drivers.md>) · L-DBMI-033, L-CONN-045 |
| PostgreSQL source prerequisites | P 2026-06-28 to 2026-09-26 | `wal_level=logical`, a dedicated publication, `REPLICA IDENTITY FULL`, the slot created after the publication | [CDC from PostgreSQL](<../04 - Mass Ingestion & CDC/02 CDC from PostgreSQL.md>) · L-DBMI-011, L-DBMI-012 |
| Hand a slot to another org's task | P 2026-09-28 | stop the source job (keep it deployed as the rollback), start the target job on the same slot | L-DBMI-020, L-DBMI-021 |
| Resume CDC jobs after a hard stop of the source host | P 2026-11-02 | `POST /dbmi/public/api/v2/job/resume` `{"jobId":<n>}`: the jobs stay FAILED with PWX-36749 until resumed (unlike after an agent reboot); a restart-window auto-resume is safe to automate | [CDC from PostgreSQL](<../04 - Mass Ingestion & CDC/02 CDC from PostgreSQL.md>) · L-DBMI-063 |
| Create and run a File Ingestion (Mass Ingestion Files) task | P 2026-10-26 | on the pod host without `/saas`: `POST .../mftsaas/api/v1/mitasks` (location set at create; Blob Storage V3 `blobSourceLocation` = the container name), `POST .../mftsaas/api/v1/job {"taskId"}` (`IDS-SESSION-ID` and `INFA-SESSION-ID`), `GET .../job/<runId>/status`; a CAI process can start and poll it before a mapping | [DBMI over REST](<../04 - Mass Ingestion & CDC/01 DBMI over REST (create, deploy, run, stop).md>) · L-DBMI-060, L-DBMI-061, L-DBMI-062 |

## 9. Application Integration (CAI)

Publish, invoke, restadmin and Operational Insights live on `https://<pod>-cai.<domain>.informaticacloud.com`.

| Operation | Status | Route | See |
|---|---|---|---|
| List assets and publication status | P 2026-07-25 | `GET /public/core/v3/objects?q=type=='PROCESS'`; `GET /active-bpel/asset/v1/status?MimeType=<type>` | [CAI Asset Lifecycle](<../05 - Application Integration (CAI)/01 CAI Asset Lifecycle (author, publish, unpublish, delete).md>) · L-CAI-009 |
| Read deployed services and contracts | P 2026-07-06 | `GET /active-bpel/rt`; `GET /active-bpel/rt/<orgIdV3>/<Process>/schema/input` | L-CAI-032 |
| Author with a REST verb | R | `POST /public/core/v3/objects` (405); `asset/v1/processes`, `/import`, `/deploy`, `/save` (500, not authoring) | L-CAI-025 |
| Author by package | P 2026-07-04, 2026-09-22 (clone); 2026-09-25 (from scratch) | v3 import of `.PROCESS.xml`, `.AI_CONNECTION.xml`, `.AI_SERVICE_CONNECTOR.xml`; carry every connection and connector a process references and limit the import with `includeObjects` (2026-10-26) | L-CAI-016, L-CAI-020, L-CAI-156 |
| Update a live process | P 2026-09-28 | export, edit, import OVERWRITE, publish, verify, roll back automatically on failure | L-CAI-018 |
| Change a connection secret | P 2026-09-26 | re-import the connection OVERWRITE under the same GUID, republish | L-CAI-061 |
| Change a connection secret in place, stored encrypted | P 2026-10-08 | author the attribute `encrypted="true"` with an empty value, import, then `PUT https://<pod>-cai.<domain>.informaticacloud.com/active-bpel/asset/v1/update?assetType=AppConnection` and republish | L-CAI-132 |
| Change access or Run On in place | D | `PUT .../active-bpel/asset/v1/update?assetType=Process` | L-CAI-015 |
| Publish | P 2026-07-09, 2026-09-28 | `POST /active-bpel/asset/v1/publish` (`application/vnd.api+json`, asset path `Explore/<project>/<folder>/<name>.PROCESS.xml`) | L-CAI-001, L-CAI-003 |
| Unpublish | P 2026-09-28/29 | `POST /active-bpel/asset/v1/unpublish`, dependents first | L-CAI-007 |
| Delete | P 2026-09-28/29 | unpublish, then FRS `DeleteEntities` or `BaseEntities('<frsGuid>')` | L-CAI-008 |
| Clear a stuck asset | UI or support | duplicate runtime rows or no runtime entry: FRS answers `FRS_082` forever | [CAI Troubleshooting](<../05 - Application Integration (CAI)/05 CAI Troubleshooting & Stuck Assets.md>) · L-CAI-078 |
| Invoke | P 2026-07-06 to 2026-09-28 | anonymous `/active-bpel/public/rt/<orgIdV3>/<ProcessApiName>`; authenticated `/active-bpel/rt/...` | [CAI Runtime](<../05 - Application Integration (CAI)/02 CAI Runtime - Invoke, URLs & Control.md>) · L-CAI-030, L-CAI-031 |
| Count invocations as jobs | — (they are not) | CAI calls do not appear in the v2 activity log and did not move a job budget; anonymous URLs answer an unauthenticated GET with 500 and are guessable, so require authentication or front them with a gateway | L-CAI-038 |
| Schedule a process | P (GET 2026-07-09; create and delete 2026-10-09) · D (update) · WALL 2026-10-09 for a process published to a Secure Agent: stored, never run | `/active-bpel/restadmin/scheduler/schedules`; agent-run processes: a timer on the agent host posting to `/process-engine/public/rt/<process>` | L-CAI-045, L-CAI-142 |
| Publish a Data Access Service Connector (JDBC from CAI) | WALL 2026-10-08 in one org (empty 'Publish Error', cpfPublish HTTP 500) | the format is in L-CAI-140; route around it through the database's REST layer | L-CAI-139, L-CAI-140, L-CAI-146 |
| Suspend, resume, terminate an instance | D | `PUT /active-bpel/restadmin/processes/<processId>/{suspend,resume,terminate}` | L-CAI-044 |
| Read job history | P 2026-11-01 | GraphQL `GET /active-bpel/opsanalytics-das/metrics?query={processJobReport(...)}` with `IDS-SESSION-ID` (the documented `Authorization: Bearer` answered 401) → one row per day, process, environment and status | [CAI Runtime](<../05 - Application Integration (CAI)/02 CAI Runtime - Invoke, URLs & Control.md>) §8 · L-CAI-159 (L-CAI-049 disputed) |
| Activate or deactivate an API | UI (documented) | Application Integration Console > APIs; a republish does not reactivate | L-CAI-010 |
| Kafka and AMQP (JMS) listener connections, event-bound processes, fault handling | P 2026-10-08 | AI_CONNECTION with the Camel javaConnector (`type` KAFKA or AMQP) and event-bound processes in an import package, published over `asset/v1/publish` on a Secure Agent | [CAI Event Listeners](<../05 - Application Integration (CAI)/06 CAI Event Listeners - Kafka & AMQP (JMS).md>) · L-CAI-116, L-CAI-118, L-CAI-119 |
| Start or stop a listener event source | P 2026-10-08 | `POST <pod>-cai .../active-bpel/local/restadmin/eventconnection/stop` or `/start?agentName=<agent>` with `IDS-SESSION-ID` (`INFA-SESSION-ID` answers 500) | L-CAI-122 |
| Produce to Kafka from a process | P 2026-10-08 | a Service step on `<conn>:<eventTarget>` with a KafkaMessage (key, value, headers) | L-CAI-124 |
| Move a file's bytes through a process (no disk, no agent) | P 2026-10-26 | read Salesforce `ContentVersion.VersionData` as base64 with a SOAP `retrieve`; `sff:createAttachmentFromBase64`, then a REST action with an attachment input and an empty body (Azure Put Blob 201, MD5-identical) | [CAI Connections & Connectors](<../05 - Application Integration (CAI)/03 CAI Connections & Connectors (e.g. Salesforce OAuth).md>) · L-CAI-154, L-CAI-155 |
| Human tasks, file listeners | UI | the Process Designer | L-CAI-025 |
| MCP tool connections | UI on private-preview orgs only (import fails `MigrationSvc_031`); newer orgs have no such type (AI Agent Engineering builder sunset) | on a preview org, recreate in the Application Integration designer; elsewhere let your own agent call the vendor-hosted MCP servers and your MCP server through one gateway | L-CAI-027, L-MIG-039, L-MCP-081, L-MCP-082 |

## 10. CDQ assets (rule specifications, dictionaries, cleanse, verifiers)

| Operation | Status | Route | See |
|---|---|---|---|
| Census | P 2026-07-09 | `GET /public/core/v3/objects?q=type=='RULE_SPECIFICATION'` (the type filter is unvalidated) | [DQ Assets](<../06 - Data Quality & Profiling/01 DQ Assets (rule specs, cleanse, dictionaries, verifiers).md>) · L-DQ-010 |
| Read a rule specification's ports and description | P 2026-10-06 | `POST <serverUrl>/api/v2/extensionPoint` (`icSessionId`) with `{"alias": "RuleSpecificationTx", "method": "getDescription", "payload": "{\"ruleId\": \"<frsId>\"}"}` → a JSON string whose `ruleModel` holds `name`, `description`, `fields`, `outputFields` and `testData` | L-DQ-109 |
| Create a rule specification | P 2026-07-09 (clone: inherits the template's logic) | v3 export, new name and GUID, import | L-DQ-010 |
| Author rule logic | UI | the rule-builder canvas | L-DQ-010 |
| Create any DQ asset with a REST verb | R | `POST /public/core/v3/objects` (405); `/data360/dq/*` (404); the public CDQ API is dictionaries-only | L-DQ-009 |
| Author cleanse, parse, labeler, deduplicate, verifier | UI · P 2026-11-02 (a verifier cloned through a v3 package; its enrichments come from the asset's own process settings, not from added output fields, L-DQ-130) | Data Quality > New | [DQ Assets](<../06 - Data Quality & Profiling/01 DQ Assets (rule specs, cleanse, dictionaries, verifiers).md>) §5 |
| Create a dictionary | P 2026-07-25 | `POST https://<pod>-dqcloud-api.<domain>.informaticacloud.com/quality/public/v2/dictionaries/` → 201 | L-DQ-006 |
| Add, replace or delete rows; finish; delete | D | `.../dictionaries/<id>/rows` (POST, PUT, DELETE; 10,000 rows per call), `.../finishUpload` (mandatory), `DELETE.../dictionaries/<id>` | L-DQ-006 |
| Read or list dictionaries | R (no GET exists) | keep the id from the create answer | L-DQ-006 |
| Let REST write a UI-made dictionary | UI | Convert to API | L-DQ-007 |
| Run DQ on production data | P (through CDI) | a transformation inside a mapping task run with `POST /api/v2/job`; cleanse, deduplicate and decision steps need a Secure Agent with the Data Quality service (EP_13236 on the Hosted Agent), rule specifications run on both (2026-10-28) | L-DQ-001, L-CDI-279 |
| Verify one address | P 2026-09-27 | MCP `dqverifyaddress` → `verify_address` (not an IDMC job) | L-DQ-016, L-DQ-017 |
| Verify addresses in batch | P 2026-11-03 | `POST https://idmc-api.<domain>.informaticacloud.com/dataquality/addressverification/api/v1/process` (Certified mode, 1,000 per call) from a CDI Java transformation; `GET .../api/v1/info` checks the Bearer JWT first (a catalog-minted one is accepted) | [DQ Assets](<../06 - Data Quality & Profiling/01 DQ Assets (rule specs, cleanse, dictionaries, verifiers).md>) · L-DQ-015, L-DQ-131, L-DQ-132 |
| Delete DQ assets | P 2026-09-28 | FRS `BaseEntities` or `DeleteEntities` | L-CLEAN-003 |
| Expose a rule spec as a request/response API | D | Explore > Enable for APIs, then API Center | L-DQ-012 |

## 11. Data Profiling

Routes are on `https://<pod>-dqprofile.<domain>.informaticacloud.com/profiling-service/api/v1` with `IDS-SESSION-ID`
(on at least one pod only the v3 session works).

| Operation | Status | Route | See |
|---|---|---|---|
| Read profiles, runs, bindings, metrics | P 2026-07 to 2026-09-28 | `GET /profile[/<id>]`, `/job/<jobId>`, `/ruleOccurrence/...`; column metrics on `/metric-store/api/v1/odata/...` | [Profiling](<../06 - Data Quality & Profiling/02 Profiling - What Is Headless.md>) · L-DQ-019, L-DQ-020 |
| Create | P 2026-09-24 | `POST /profile` from a template profile's body, with no client-side ids | L-DQ-019, L-DQ-021 |
| Update and bind rule occurrences | P 2026-09-24 | `PUT /profile/<id>` with one rule block per rule spec and `MAPPLETFIELD` entries | L-DQ-023 |
| Run and poll | P 2026-09-24, 2026-09-28 | `POST /profile/<id>/execute`, then `GET /job/<profileJobId>` to COMPLETED | L-DQ-019 |
| Read run history | P 2026-10-03 | `GET /runDetail/<profileId>/<runKey>` for runKey 1..`lastRunKey` (from `GET /profile/<id>`); the `/runDetail/<id>/filter` form answered 400 `PROFILE_SVC_00093` on one pod | [Profiling](<../06 - Data Quality & Profiling/02 Profiling - What Is Headless.md>) · L-DQ-019 |
| Run through the platform job API | R (403 UI_13404) | use `/execute` | L-DQ-024 |
| Delete | D | `DELETE /profile/<id>` (FRS deletes were used in a cleanup) | [Profiling](<../06 - Data Quality & Profiling/02 Profiling - What Is Headless.md>) §2.2 |
| Move between folders | P 2026-11-02 | FRS `MoveEntities` (FRS_200; folder, fields and run history kept). FRS_108 only on orphan profile documents the profiling service does not list | L-DQ-124 (disputes L-DQ-029) |
| Migrate | P 2026-09-28 | v3 package; profiles arrive with 0 rule occurrences, so re-bind them | L-DQ-025, L-DQ-026 |
| Read per-rule pass rates | U (no route found) | the console only; mirror scores into warehouse tables | [DQ Scorecards](<../06 - Data Quality & Profiling/04 DQ Scorecards (warehouse pattern and Data Profiling scorecards).md>) · L-DQ-031 |
| Profile and cleanse an uploaded file | P 2026-09-21 | MCP `dataqualityagent` → `request_upload_url`, then `data_quality_cleansing` | [CLAIRE DQ Agent](<../06 - Data Quality & Profiling/03 CLAIRE DQ Agent - File-Based Profiling & Cleansing.md>) · L-DQ-072 |
| Profile through a catalog scan | P 2026-09-24 | a catalog source with the Data Profiling capability, then a scan (section 12); on BigQuery catalog sources it FAILED with no message (2026-10-08) | L-DQ-043, L-CDGC-184 |
| Profile a BigQuery V2 table | P 2026-10-08 | `POST /profile` + `/execute` on a connection whose five hidden retry attributes hold the connector defaults (empty ones fail every run with 'Cannot parse null string') | L-DQ-110, L-DQ-107 |
| Profile ClickHouse through a JDBC V2 connection | P 2026-11-02 | clone a profile body that has run on JDBC V2 (`TOOLKIT_CCI`, `sourcePath` `<database>/TABLE`, NSTRING fields with `dataType` varchar, DOUBLE fields), `POST /profile`, `/execute`; profile typed sample tables | [Profiling](<../06 - Data Quality & Profiling/02 Profiling - What Is Headless.md>) · L-DQ-128 (overturns L-DQ-119, L-CONN-089) |
## 12. CDGC catalog sources and scans

Writes on `https://cdgc-api.<domain>.informaticacloud.com`, runs and reads on `https://idmc-api.<domain>.informaticacloud.com`,
always with the three identity headers (the JWT minted with `client_id=cdlg_app`).

| Operation | Status | Route | See |
|---|---|---|---|
| List source types | P 2026-09-24 | `GET /ccgf-catalog-source-management/api/v1/datasourceTypes` | [Catalog Sources](<../07 - Catalog & Governance (CDGC)/02 Catalog Sources - Create, Scan, Update, Purge.md>) · L-CDGC-016 |
| Read a source type's option schema per capability | P 2026-10-03, 2026-11-01 | `GET.../ccgf-catalog-source-management/api/v1/type/<Type>/capability/<Capability, URL-encoded>/configuration` → `optionGroups[].options[]`; a 404 "capability configuration does not exist" means the type does not offer it (the JDBC type has no Lineage Discovery) | L-CDGC-016, L-CDGC-234 |
| Read sources | P 2026-09-28 | `GET /ccgf-catalog-source-management/api/v1/datasources?offset=0&limit=100`, `.../datasources/<csId>` | L-CDGC-017 |
| Create | P 2026-09-24 to 2026-09-29 | multipart `POST.../datasources` with one part `dataSource` (`custom` and `endOfLife` set, every id remapped) | L-CDGC-014, L-CDGC-015 |
| Create a SharePoint Online source | P 2026-10-06 | connection URL = the tenant root `https://<tenant>.sharepoint.com`, `Subsite_URL` = the full site URL, and every Scanner Configuration option sent (a create without one answers 500); the scan catalogs the site, its libraries, folders and documents | [Catalog Sources](<../07 - Catalog & Governance (CDGC)/02 Catalog Sources - Create, Scan, Update, Purge.md>) §4 · L-CDGC-162 |
| Update filters and options | P 2026-09-25 to 2026-10-06 | multipart `PUT.../datasources/<csId>` with `id` repeated in the JSON part (400 without it); PATCH as fallback | L-CDGC-020, L-CDGC-163 |
| Purge the metadata | P 2026-09-29 | `DELETE.../datasources/<csId>` starts a purge job | L-CDGC-047 |
| Delete the definition | UI | Metadata Command Center > Catalog Sources | L-CDGC-047, L-CLEAN-015 |
| Run a scan | P 2026-06-28, 2026-09-29 | `POST /data360/executable/v1/catalogsource/<csId>` with `{"capabilityNames":["Metadata Extraction",...]}` (display names) | L-CDGC-034, L-CDGC-035 |
| Poll a scan | P 2026-09-29 | `GET /data360/observable/v1/jobs/<jobId>?expandChildren=TASK-HIERARCHY`; list at `/data360/observable/api/v1/jobs`; a PARTIAL_COMPLETED can carry no message in the job tree, so read the agent's scanner Sync log | L-CDGC-037, L-CDGC-168 |
| Cancel a scan | P 2026-10-26 (console capture and script replay, both 200) | `POST https://cdgc-api.<domain>.informaticacloud.com/ccgf-orchestration-management-api-server/api/v1/jobs/<jobId>/operations/cancel` (the console's Cancel Job); CANCELLED in 1-2 min while Test Connection runs, still CANCEL_REQUESTED after 50 min when sent during Catalog Source Extraction; a stuck job holds the source lock (runs 406, delete 400) until cancelled; job ids also at `.../ccgf-orchestration-management-api-server/api/v1/jobs?metadataOnly=false&offset=<total-60>&limit=60` (oldest first) | [Catalog Sources](<../07 - Catalog & Governance (CDGC)/02 Catalog Sources - Create, Scan, Update, Purge.md>) · L-CDGC-221, L-CDGC-225 |
| Produce CDI lineage | P 2026-09-24/25 (config) · P 2026-09-30 (assignments auto-accepted in the scan) · P 2026-10-06 (references stitched by MERGE) · X for CLAIRE answers | an IICS source with Lineage Discovery; auto-accept in the scan, then a MERGE for every reference it left unresolved (next row; seen in a new org); CLAIRE still showed no job-level lineage for custom-query tasks; for tasks that read connection objects it walked 4 hops through the task and a curated edge (2026-10-27) | L-CDGC-159, L-CDGC-140, L-CDGC-148, L-MCP-128 |
| Accept a pending connection-assignment recommendation (stitch a reference to its catalog source) | P 2026-10-06 | `POST https://cdgc-api.<domain>.informaticacloud.com/ccgf-contentv2/api/v1/assignment/connectionAssignment?operationType=MERGE` with `sourceRootAsset` (the IICS reference), `targetRootAsset` (the physical database, or a File System root for flat files), `initialAssignment: true`, `modifyAssignment: false` → a job id; `SPLIT` undoes; `ASSIGN`, `UNASSIGN`, `ACCEPT` and `CREATE` fail the enum conversion; the job completes even for a bogus reference, so prove it by reading a target table's lineage (no rescan needed); a SharePoint reference, which can be named after the connection's v2 id, MERGEs onto the SharePoint Online source's Site | [Search, Lineage & Marketplace](<../07 - Catalog & Governance (CDGC)/04 Search, Lineage & Marketplace.md>) §9 · L-CDGC-159, L-CDGC-160, L-CDGC-167 |
| Configure a source's Data Quality capability | P 2026-09-30 | multipart `PUT.../datasources/<csId>` with typeCapabilities Data Profiling Scope and Data Quality Scope carrying the runtime environment | L-CDGC-143 |
| Run Data Quality and read catalog scores | P 2026-09-30, 2026-10-06 | `POST /data360/executable/v1/catalogsource/<csId>` with `capabilityNames: ['Data Quality']`; scores in the `dataQuality` segment, in CLAIRE, and per occurrence in the RuleInstance's `selfAttributes` (`value`, `totalCount`, `exception`, `scannedTime`) | L-CDGC-143, L-CDGC-144, L-CDGC-166, L-DQ-097 |
| Create catalog rule instances | P 2026-10-06 (REST) · UI 2026-09-30 (CLAIRE GPT) | `POST https://cdgc-api.<domain>.informaticacloud.com/ccgf-contentv2/api/v1/publish` with `X-INFA-PRODUCT-ID: CDGC`: an OBJECT INSERT of a RuleInstance plus a RELATIONSHIP INSERT (`asscParentDataElementRuleInstance`) from the column → 207 with a 201 per item; then `.../ccgf-ruleautomation/api/v1/dataQuality/sync` → PASSED; port names and description from `RuleSpecificationTx.getDescription` (section 10); bind a column of the rule's input type (a decimal-input rule on a text column is never scored, a typed view column is). Or, in CLAIRE GPT, recommend with the columns named, then "Accept all the recommended rules" | [DQ Scorecards](<../06 - Data Quality & Profiling/04 DQ Scorecards (warehouse pattern and Data Profiling scorecards).md>) §4 · L-CDGC-161, L-DQ-109, L-MCP-086, L-CDGC-170 |
| Delete catalog rule instances | P 2026-09-30 | `DELETE /data360/content/v1/assets/<identity>?scheme=internal` | L-CDGC-144 |
| Carry catalog content in a v3 package | R (`MigrationSvc_034`) | rebuild through the APIs in the target | L-CDGC-071 |

## 13. CDGC glossary, links, classification and stewardship

Content writes are on `https://idmc-api.<domain>.informaticacloud.com/data360/content/v1/assets`; address assets by
internal identity (`?scheme=internal`), resolved through an Elasticsearch `terms` query on `core.externalId`.

| Operation | Status | Route | See |
|---|---|---|---|
| Read domains and terms | P 2026-09-29 | ES `term` query on `core.classType` through `POST /data360/search/api/v1/search` | [Glossary, Links & Classification](<../07 - Catalog & Governance (CDGC)/03 Glossary, Links & Classification.md>) · L-CDGC-073 |
| Create a domain or term | P 2026-09-24 to 2026-09-29 | `POST /data360/content/v1/assets` (`core.classType` Domain or BusinessTerm; a term names its `parent`) | L-CDGC-050, L-CDGC-051 |
| Rename or redefine | P 2026-09-28 | `PATCH /data360/content/v1/assets/<identity>?scheme=internal`, segment `summary` | L-CDGC-053 |
| Delete | P (2xx) · X for Published terms | `DELETE /data360/content/v1/assets/<identity>?scheme=internal`, then confirm by search | L-CDGC-059 |
| Link a term to an asset | P 2026-09-24 to 2026-09-29 | `PATCH`, segment `glossary`, operation `add` | L-CDGC-056 |
| Write asset descriptions | P 2026-09-24/28, 2026-10-06 | `PATCH`, segment `summary` (a later scan can blank them); a technical asset (table, view, column) takes `core.description` alone (`core.name` → 400), and bursts hit 429 | L-CDGC-054, L-CDGC-055, L-CDGC-164 |
| Apply a classification | P 2026-09-24/28 | `PATCH`, segment `dataClassification` | L-CDGC-060 |
| Bulk-accept CLAIRE classifications | UI (July; not re-probed) · X (a browser-captured job) | the auto-accept threshold on the source, then a rescan | L-CDGC-061, L-CDGC-063 |
| Assign stewards and owners | UI (July; not re-probed) | MCC > Associations > Stakeholders | L-CDGC-066 |
| Author DAM policies | UI (on the orgs probed) | the first policy in the UI; demonstrate the controls as pushdown | L-CDGC-067 |
| Glossary and classification writes over MCP | U (tools listed) | `cdgccatalogenrichment` | L-MCP-002 |

## 14. CDGC search, lineage and Data Marketplace

| Operation | Status | Route | See |
|---|---|---|---|
| Search with Elasticsearch DSL | P 2026-06-28, 2026-09-29, 2026-10-06, 2026-10-07 | `POST /data360/search/api/v1/search` with `X-INFA-SEARCH-LANGUAGE: elasticsearch`; `term`, `bool`, `wildcard` and `exists` queries work, `match` and `match_phrase` answer 400; page with `"sort": [{"core.identity": {"order": "asc"}}]` and filter on `core.origin` + `elementType` OBJECT, because unsorted `from`/`size` pages overlap and drop assets | [Search, Lineage & Marketplace](<../07 - Catalog & Governance (CDGC)/04 Search, Lineage & Marketplace.md>) · L-CDGC-073, L-CDGC-165, L-CDGC-169 |
| Search with a knowledge query | P 2026-09-24/28 | `POST /data360/search/v1/assets?knowledgeQuery=<q>&segments=<list>` | L-CDGC-074 |
| Read one asset | P 2026-09-28 | `GET /data360/search/v1/assets/<identity>?scheme=internal&segments=<list>` | L-CDGC-075 |
| Read lineage | P 2026-10-04 and 2026-10-08 (hop by hop) · R (`/data360/lineage/*` graph) · D over MCP | `GET /data360/search/v1/assets/<identity>?scheme=internal&segments=all`: the `lineage` segment (inbound and outbound data-flow hops) and the neighborhood segment; MCP `cdgcsearchmetadata` → `get_asset_details` | [Search, Lineage & Marketplace](<../07 - Catalog & Governance (CDGC)/04 Search, Lineage & Marketplace.md>) · L-CDGC-181, L-CDGC-156 |
| Write lineage edges | P 2026-10-08, 2026-10-26 to 2026-10-29 | `POST https://cdgc-api.<domain>.informaticacloud.com/ccgf-contentv2/api/v1/publish` with RELATIONSHIP items: `core.DataSetDataFlow` for tables, `core.DirectionalDataFlow` for columns (`core.DataFlow` is refused); DELETE items undo; PDF files, SharePoint DocumentLibrary and Blob Container endpoints answer INVALID_RELATIONSHIP_CLASS_TYPE; edges stay on the node identities they were made for, so re-check them after rescans | L-CDGC-179, L-CDGC-224, L-CDGC-228 |
| Check a lineage link before sharing it | P 2026-10-26, 2026-10-29 | walk inbound from the BI asset with the `lineage` segment, fail on any root that is not the system of record, foreign nodes, a missing middle system or an end asset with outbound edges; share the link seeded on the BI asset | [Search, Lineage & Marketplace](<../07 - Catalog & Governance (CDGC)/04 Search, Lineage & Marketplace.md>) · L-CDGC-232, L-CDGC-229 |
| Create Marketplace producer objects | P 2026-07-04 to 2026-08-20 | `/data360/marketplace/api/v1/{dataAssets,dataCollections,categories,termsOfUse,orders}`, `/api/v2/{data-collections,delivery-targets,orders}` | L-CDGC-092, L-CDGC-093, L-CDGC-094 |
| Read provisioning ids | P 2026-07-10 | `GET https://cdgc-api.<domain>.informaticacloud.com/cdmp-marketplace/api/v1/provisioning/{deliveryTemplates,deliveryFormats,deliveryMethods}` | L-CDGC-095 |
| Delivery templates, ratings, approvals, consumer chat | UI | the Marketplace app, in a headed browser | L-CDGC-096, L-CDGC-098 |
| Raise an access request over MCP | D | `dataprovisioning` → `checkout_data_order` | L-CDGC-099 |

## 15. MDM SaaS

The runtime plane is `https://<pod>-mdm.<domain>.informaticacloud.com` (no `/saas`) with the three identity headers;
address entities by runtime id (for example `c360.person`), never by design GUID.

| Operation | Status | Route | See |
|---|---|---|---|
| Ingest a source record | P 2026-07-08 | `POST /business-entity/public/api/v1/entity/<runtimeId>?sourceSystem=<src>` (bare field map; string `trustScore`) → 201 | [MDM Records](<../08 - MDM/02 MDM Records - Ingest, Search, Export, Cleanup.md>) · L-MDM-019 |
| Read a master record by id | X (200 in July; some 200s were login HTML) | `GET /business-entity/public/api/v1/entity/<runtimeId>/<id>`; check the Content-Type | L-MDM-021 |
| Search and export | P 2026-09-28 | `POST /search/public/api/v1/search` (at most 10,000 per query: export larger entities as a union of prefix queries) | L-MDM-025 |
| Update a source record | D | `/business-entity/public/api/v1/entity-xref/...` (never the master `entity`) | L-MDM-023 |
| Delete a record | P (route, 2026-07-08) · D (soft-delete semantics) | `DELETE /business-entity/public/api/v1/entity/<runtimeId>/<id>?sourceSystem=<src>` | L-MDM-029 |
| Reference 360 lookup | P 2026-07-26 (the validator answered) | `POST /rdm-service/external/v1/search` | L-MDM-026 |
| Fuzzy identity match | D | MCP `searchcustomer` → `search_master_record`, then `get_master_record_details` | L-MDM-027 |
| Author or change a business entity | UI (Modeler) · P (clone, July) | v3 package of `BUSINESS_ENTITY`, `MDM_SRC_SYSTEM`, reference entities | [MDM SaaS - Runtime vs Design](<../08 - MDM/01 MDM SaaS - Runtime vs Design.md>) · L-MDM-005, L-MDM-013 |
| Publish or deploy the model | UI · X (Save or Publish) | prove it with the ingest POST gate and a fake-entity control | L-MDM-005, L-MDM-007, L-MDM-008 |
| Run match/merge, ingress, reindex jobs | UI | the Business 360 Console, or job schedules | [Business 360 Modeling](<../08 - MDM/03 Business 360 Modeling & Match-Merge.md>) · L-MDM-016 |

## 16. Managed MCP, CLAIRE and CLAIRE GPT

| Operation | Status | Route | See |
|---|---|---|---|
| Read the org's MCP registry | P 2026-09-23/28 | `GET https://hdm.<domain>.informaticacloud.com/a2e-mcp-asset-mgmt-svc/api/v1/mcp-servers?type=MANAGED` (v3 session in `IDS-SESSION-ID`) | [Managed MCP Servers](<../09 - CLAIRE & MCP/01 Managed MCP Servers (catalog & access).md>) · L-MCP-001 |
| Create an OAuth client | P 2026-09-28 | `POST.../a2e-mcp-asset-mgmt-svc/api/v1/oauth2clients` → 201; the secret is shown once | [MCP Auth & OAuth Clients](<../09 - CLAIRE & MCP/02 MCP Auth & OAuth Clients.md>) · L-MCP-018 |
| List or delete OAuth clients | P (recorded) · U (the library's delete helper) | `GET.../oauth2clients?type=IDMC_MCP&...`, `DELETE.../oauth2clients/<clientId>` | L-MCP-018 |
| Call a server's tools | P 2026-09-28 | JSON-RPC over streamable HTTP: `initialize`, `notifications/initialized`, `tools/list`, `tools/call` (protocol `2025-06-18`) | [Agent-Style MCP](<../09 - CLAIRE & MCP/04 Agent-Style MCP (async orchestration) & Custom Shims.md>) · L-MCP-028 |
| Use the DQ agent | P 2026-09-21 | `dataqualityagent`: nested `tools/call`, then `get_skill_execution_updates` | L-DQ-070, L-DQ-072 |
| Use the CLAIRE agent MCP | P (read-only answers) | `<claire_api_url>/claire-orchestrator-ai-agent/api/v1/mcp`; it can list 0 tools for an org | L-MCP-010, L-MCP-033 |
| Author a CDI mapping, deploy DBMI, publish CAI over MCP | R (no verb on any server) | use REST | L-MCP-003 |
| Composite servers and tool connections | UI (tool-connection import fails; tool connections exist only on private-preview orgs) | AI Agent Engineering (composite servers expose CAI processes as tools); the Application Integration designer on a preview org | L-MCP-012, L-MCP-081 |
| Chat with CLAIRE GPT, NL-to-SQL | UI (no public chat API) | `https://claire-gpt.<domain>.informaticacloud.com`; one warehouse asset per question (joins fail), PostgreSQL unsupported; every generated query ends in `LIMIT 100`, so list answers stop at 100 rows | [CLAIRE GPT](<../09 - CLAIRE & MCP/03 CLAIRE GPT - Prompting Rules & Patterns.md>) · L-MCP-050, L-MCP-051, L-MCP-091, L-MCP-100, L-MCP-114 |
| Ask CLAIRE's questions headless (DQ scores, diagnosis, MDM match rules, NL data checks) | P 2026-10-01 | managed `datamanagementorchestrator.orchestrate` / `orchestrate_master_data_analysis`, `dataexplorationagent.data_explore` (nested envelope, cursor polling from "0"); same answers as the UI in 28-80 s | L-MCP-111, L-MCP-112 |
| Generate a mapping in the CLAIRE GPT chat | X 2026-10-01 (in-chat proposal only; nothing saved) | "Create a mapping to load these" after an exploration gives an artifact in the conversation; use packages | L-MCP-108, L-MCP-052 |
| Generate, test and publish DQ rules with CLAIRE GPT | UI 2026-09-30 · 2026-10-01 | attach a policy file ("This file is a data quality policy with one rule per line. Generate data quality rules from this file.") or write one sentence; proceed + Send, Publish Rules + Send. Never type at the Publish prompt (it can publish); "Generate Dictionaries" saves dictionaries before Publish | L-MCP-079, L-MCP-089, L-MCP-096, L-MCP-097, L-MCP-099 |
| Pin, unpin and rename CLAIRE GPT conversations | UI 2026-09-30 (browser automation) | row buttons `chat-pin-button`, `chat-unpin-button`, `chat-edit-button` | L-UI-029 |

## 17. Migration: v3 export/import and FRS

| Operation | Status | Route | See |
|---|---|---|---|
| List objects | P (read-only: POST 405) | `GET /public/core/v3/objects?limit=200&skip=<n>` (filter on the client) | [Export & Import](<../10 - Migration & Org Management/01 Export & Import (v3 Migration API).md>) · L-MIG-001, L-MIG-002 |
| Dependency closure | P 2026-09-28 | `GET /public/core/v3/objects/<id>/references?refType=uses` (and `usedBy`) | L-MIG-034 |
| Export | P 2026-09-28 | `POST /public/core/v3/export` → `GET /export/<id>` → `GET /export/<id>/package` | L-MIG-003 |
| Import | P 2026-09-28 | multipart `POST /public/core/v3/import/package` (part `package`) → `POST /import/<jobId>` → poll | L-MIG-008, L-MIG-010 |
| Import a from-scratch package | P 2026-09-25 to 2026-09-29 | real Folder and Project JSON, `exportMetadata.v2.json`, upper-case SHA-256 lines | [Editing Packages Safely](<../10 - Migration & Org Management/02 Editing Packages Safely.md>) · L-MIG-022 |
| Map a source object onto a named target | R (`V3API_007` in every shape) | use `REUSE`, or edit the package | L-MIG-013 |
| Move or copy | P 2026-09-24 to 2026-11-02 | FRS `POST https://<pod>.<domain>.informaticacloud.com/frs/api/v1/MoveEntities` (or `CopyEntities`: name each copy with `destName` and `destDesc`, omit `conflictResolution` ('NONE' gives XFER_500), the new id is in `tgtGuid`) | L-MIG-054, L-MIG-087 |
| Delete repository objects | P 2026-09-26/28 | FRS `POST /frs/v1/DeleteEntities` (per-item codes), `DELETE /frs/api/v1/BaseEntities('<id>')`; `Documents('<id>')` gives 403 | [Headless Deletes](<../10 - Migration & Org Management/06 Headless Deletes & Org Cleanup.md>) · L-CLEAN-003, L-CLEAN-005 |
| Tag | P 2026-09-28 | `POST /public/core/v3/TagObjects` (at most 50 per call; imports drop tags) | L-MIG-016 |
| Promote dev to prod within one org | P (process) | plan, validate, re-point only the intended delta | L-MIG-031 |
| Migrate a whole estate to another org | P 2026-09-28 | the M0–M13 runbook | [Org-to-Org Migration Runbook](<../10 - Migration & Org Management/04 Org-to-Org Migration Runbook.md>) · L-MIG-045 |

## 18. Metering and licences

| Operation | Status | Route | See |
|---|---|---|---|
| Export consumption | P 2026-07-04 to 2026-10-03 | `POST <serverUrl>/public/core/v3/license/metering/ExportMeteringData` → poll → download a ZIP of CSVs; `PROJECT_FOLDER` (and plan `ASSET` the same way) windows of at most 30 days (`400 LS_298`), `SUMMARY` accepts longer | [Metering & Consumption Exports](<../11 - IPU, Metering & Licensing/02 Metering & Consumption Exports.md>) · L-IPU-021 |
| Read meter allocations and usage | P 2026-09-29 (browser-session capture) | `GET <pod host>/license-service/api/v1/metering/org/('<orgIdV3>')/instances?aggregatedMeterOnly=true`, `POST <pod host>/metering-service/api/v1/metering/org/('<orgIdV3>')/queryAggregatedMeterData`; on a trial org these are serverless compute-unit meters, not the job cap | L-IPU-056 |
| Summary reads | R (404 `No static resource`) | `.../metering/MeteringUsageSummary` and the other summary GETs | L-IPU-022 |
| Read effective licences | P 2026-09-28 | `GET https://<pod>.<domain>.informaticacloud.com/license-service/api/v1/OrgLicenseAssignment('<orgIdV3>')/EffectiveLicenses` (limits read -1) | [Entitlement, Licenses & Job Caps](<../11 - IPU, Metering & Licensing/03 Entitlement, Licenses & Job Caps.md>) · L-IPU-030 |
| Read one org's licence detail | P 2026-09-28 | `GET /public/core/v3/license/org/<orgIdV3>` (the 6-character id gives `V3API_016`) | L-IPU-029 |
| Read the licence inventory | UI (and its CSV export) | Administrator > Licenses | L-IPU-029, L-IPU-028 |
| Read the monthly job limit | not readable anywhere | count jobs from the activity log (rows plus each taskflow's children) into your own ledger, with soft (~85%) and hard (~95%) thresholds and a quota breaker; the log keeps about 1,000 entries for a busy project, so record each run at completion (L-CDI-288) | L-IPU-041, L-IPU-043, L-CDI-288 |
| Metering exports over MCP | U (tools listed) | `ipumanagement` | L-MCP-002 |

---

## What moved in September to early November 2026

Cells that were UI-only or "no API" in the July 2026 corpus and are headless now (details in each section):

| Capability | Proven headless | Lesson |
|---|---|---|
| Service and connector selection on a runtime environment | 2026-09-23 (MCP), 2026-09-28 (REST PUT) | L-AGENT-039 |
| Agent engine configuration (System / Custom Configuration) | 2026-09-29 (the legacy form the console iframes) | L-AGENT-088 |
| New CDI mappings with real transformations | 2026-09-29 | L-CDI-033 |
| Linear taskflows and schedule binding | 2026-09-24, 2026-09-28 | L-CDI-069, L-CDI-075 |
| DBMI create, deploy, start, stop, resume, undeploy | 2026-09-22 to 2026-09-29 | L-DBMI-003 |
| CAI publish with imported or hand-built assets | 2026-09-24/25 | L-CAI-003, L-CAI-020 |
| Data Profiling create, rule binding and run | 2026-09-24 | L-DQ-019, L-DQ-023 |
| Catalog-source create and update; glossary, links, classification writes | 2026-09-24 to 2026-09-29 | L-CDGC-014, L-CDGC-020, L-CDGC-051, L-CDGC-056, L-CDGC-060 |
| MDM record search and export | 2026-09-28 | L-MDM-025 |
| MCP registry (19 servers) and OAuth clients | 2026-09-23, 2026-09-28 | L-MCP-001, L-MCP-018 |
| Design-object deletes (FRS) and user deletes | 2026-09-26/28 | L-CLEAN-003, L-CLEAN-005, L-CLEAN-009 |
| Union, Rank, Sequence, Lookup, Masking, Rule Specification, Cleanse, Deduplicate and Normalizer in generated mappings | 2026-09-30 | L-CDI-204 |
| DTM pool size and heap, cloud-side | 2026-09-29 | L-AGENT-099 |
| Full SQL ELT (BigQuery pushdown) | 2026-10-01 | L-CDI-202 |
| A run's session log over REST | 2026-10-01 | L-CDI-211 |
| Catalog connection assignment for CDI lineage (`operationType=MERGE`) | 2026-10-06 | L-CDGC-159 |
| Catalog Data Quality rule occurrences: create, and read each one's score | 2026-10-06 | L-CDGC-161, L-CDGC-166 |
| File Ingestion (Mass Ingestion Files) task create, run and poll | 2026-10-26 | L-DBMI-060, L-DBMI-061 |
| Local (on-agent) Spark advanced configuration | 2026-10-26 | L-AGENT-114 |
| Catalog job cancel from a script | 2026-10-26 | L-CDGC-221, L-CDGC-225 |
| A file's bytes through a CAI process (Salesforce file in, binary PUT out) | 2026-10-26 | L-CAI-154, L-CAI-155 |
| Operational Insights export (with `IDS-SESSION-ID`) | 2026-11-01 | L-CAI-159 |
| Dynamic Mapping Task read (and create by package) | 2026-11-01 | L-CDI-289 |
| ClickHouse profiling through JDBC V2 | 2026-11-02 | L-DQ-128 |
| Cloud address verification in Certified mode from a mapping | 2026-11-03 | L-DQ-132 |

What did **not** move is listed in [law 17](<02 The Laws of Headless IDMC.md>) and marked UI in the tables above.
Before quoting any UI or R cell, check its date and re-probe it in the org you are working in.
