# Overturned Beliefs

> **Summary.** The corrections log: every IDMC belief this KB once held and later overturned, 185 of them across 14
> domains, each with the dates it was held, the lesson that overturned it and what to do now. Most fell in two waves: June and July 2026 (65, mostly wrong hosts, missing headers, the clone route and CAI publish) and 21–29 September 2026 (90: the MCP registry, packages, DBMI, profiling, catalog writes, the selections PUT, deletes); 8 fell in August and early September, and 11 between 2026-09-30 and 2026-10-01 (CLAIRE GPT behaviour, catalog DQ scoring, a catalog-source scan, the agent downloads cache and BigQuery pushdown), and 3 on 2026-10-08 (Kafka and AMQP listeners authored headless; catalog lineage read and written over REST); later
> ones include a Databricks catalog type (2026-10-19) and, between 2026-10-26 and 2026-11-02, the REST cancel of a catalog
> job, ClickHouse profiling through JDBC V2 and the Operational Insights header. Read this page before quoting any wall. The 17 lessons that are still disputed, overturned neither way, are listed at the end.

Last verified: 2026-11-03, against lessons.jsonl (overturn dates 2026-06-27 to 2026-11-02).

Related: [Lessons Learned README](README.md) · [The Laws of Headless IDMC](../knowledge/00-start-here/02-the-laws-of-headless-idmc.md) ·
[Capability Map](../knowledge/00-start-here/03-capability-map.md) · [Changelog](../knowledge/00-start-here/06-changelog.md) ·
[Evidence Discipline](../knowledge/14-claude-working-methods/02-evidence-discipline.md)

---

## How to read it

- **Lesson** is the superseded lesson's id. Its full text sits in the "Superseded / overturned" section of the domain's
  lessons file, linked above each table.
- **Old belief** is what was believed, in the lesson's own words.
- **Held** is the date range the belief was held or restated, as recorded. A belief sometimes outlived its overturn in
  notes and runbooks, which is why a range can end after the overturn date.
- **Overturned by** names the lesson or lessons that replaced it, with the date the belief fell.
- **What to do now** is the practical consequence. The topic doc of the domain has the full route and its evidence.
- A few rows name a lesson that its lessons file keeps as **disputed** rather than superseded, because the newer proof
  came from a different setup and the difference was not isolated; the row says so. The newer, proven record is the
  one to follow.

Every row is a warning: the same wrong conclusion was often reached twice, months apart. Before you record a new wall,
search this page for the path, the product or the error code.

## The overturns that changed outcomes most

| # | Old belief | Fell | Lessons | Consequence |
|---|---|---|---|---|
| 1 | IDMC REST has no PUT; update only by POST to the id | 2026-09-28 | L-AUTH-077, L-AGENT-081, L-METHOD-096 → L-AUTH-016, L-AGENT-039, L-METHOD-032 | PUT is proven on runtime selections, catalog sources and profiles; the POST-to-id idiom still holds on v2 |
| 2 | The login `products[]` list, or a 404, decides entitlement | 2026-07-04 to 2026-09-24 (it recurred) | L-AUTH-085, L-AUTH-087, L-IPU-049, L-IPU-050, L-CDGC-129 → L-AUTH-070, L-AUTH-071, L-IPU-031, L-CDGC-007 | About 90 false licence escalations were retired; read privileges, engines, selections and effective licences |
| 3 | Design objects can only be authored in the UI (`POST /v3/objects` is 405) | 2026-07-05, again 2026-09-28 | L-MIG-061, L-CAI-101, L-DQ-089 → L-MIG-023, L-CAI-016, L-CAI-020, L-DQ-025 | Packages author mappings, CAI assets, DBMI tasks, rule specs, MDM entities and profiles |
| 4 | New mappings need the designer; mapping logic is a compiled binary | 2026-09-22 to 2026-09-29 | L-CDI-174, L-CDI-180, L-CDI-191 → L-CDI-003, L-CDI-021, L-CDI-027, L-CDI-033 | Template tasks and IMF-synthesized mappings are headless and parity-proven |
| 5 | Database Ingestion is a UI wizard with no deploy or run verb | 2026-07-26 (host), 2026-09-28 (lifecycle) | L-DBMI-045, L-DBMI-047, L-DBMI-048 → L-DBMI-001, L-DBMI-003 | The whole lifecycle runs on `<pod>-ing` |
| 6 | CAI publish is a UI click; imported assets need one UI save | 2026-07-09, 2026-09-28 | L-CAI-097, L-CAI-100 → L-CAI-001, L-CAI-003, L-CAI-020 | `asset/v1/publish` with the `Explore/...` asset path |
| 7 | Agent services and connectors can only be enabled in Administrator | 2026-09-23 (MCP), 2026-09-28 (REST) | L-AGENT-079, L-AGENT-080, L-UI-025 → L-AGENT-039, L-UI-001, L-UI-002 | The selections PUT, found by capturing the UI's own call |
| 8 | The managed MCP catalog is five servers with one write | 2026-09-23 | L-MCP-069, L-MCP-070, L-MCP-071 → L-MCP-001 | Enumerate the org's registry (19 servers, about 140 tools, on one org) |
| 9 | Glossary writes and term-to-column links have no REST route | 2026-09-24 | L-CDGC-125, L-CDGC-126 → L-CDGC-051, L-CDGC-056 | `data360/content/v1/assets` POST and PATCH |
| 10 | Data Profiling has no API, and profiles can only run from the UI | 2026-07-26 (reads), 2026-09-24 (create and run) | L-DQ-085, L-DQ-087, L-DQ-088 → L-DQ-019, L-DQ-023 | Create, bind rules, execute and poll on `<pod>-dqprofile` |
| 11 | The headless delete surface is five DELETE endpoints | 2026-09-26/28 | L-CLEAN-028, L-CLEAN-031 → L-CLEAN-006, L-CLEAN-003 | v2 DELETE on seven resources plus FRS `DeleteEntities` and `BaseEntities` |
| 12 | Hand-built import packages are always rejected | 2026-09-29 (held from 2026-06-28) | L-MIG-066, L-CDI-181 → L-MIG-022, L-CDI-032 | From-scratch packages import when metadata and checksums are right |
| 13 | The session is a 30-minute idle timeout | 2026-09-28 | L-AUTH-080, L-METHOD-099 → L-AUTH-027, L-METHOD-003 | Refresh by age, at most about 25 minutes after grant |
| 14 | BigQuery full pushdown cannot be enabled over REST | 2026-10-01 | L-CDI-042 → L-CDI-202 | Three fields on the v2 mapping task; prove OPT_63367 in the session log and keep pushdown only where it measures faster (L-CDI-203) |
| 15 | The agent downloads folder is a re-fetchable cache | 2026-09-30 | L-AGENT-055 → L-AGENT-094 | Never prune or move `downloads/`: services run from it; free disk elsewhere |
| 16 | Kafka and JMS event sources and listeners are designer-only; catalog lineage can be neither read nor written over REST | 2026-10-08 | L-CAI-117, L-CDGC-085, L-CDGC-180 → L-CAI-116, L-CDGC-181, L-CDGC-179 | Author Kafka and AMQP listeners in packages and control them with restadmin; read lineage hop by hop from the asset read and publish curated edges |
| 17 | A catalog job cannot be cancelled over REST; ClickHouse cannot be profiled through JDBC V2; the Operational Insights export takes a Bearer header | 2026-10-26 to 2026-11-02 | L-CDGC-040, L-DQ-119, L-CONN-089, L-CAI-049 → L-CDGC-221, L-CDGC-225, L-DQ-128, L-CAI-159 | Cancel stuck scans from a script and poll for CANCELLED; profile ClickHouse from a cloned JDBC V2 profile body; send `IDS-SESSION-ID` to the Operational Insights export |

## Counts by domain

| Domain | Id prefixes | Overturned beliefs | Overturn dates |
|---|---|---|---|
| 01 Access, auth and orgs | `AUTH` | 11 | 2026-07-05 to 2026-09-28 |
| 02 Secure Agent and connections | `AGENT`, `CONN` | 24 | 2026-06-27 to 2026-11-02 |
| 03 Data Integration (CDI) | `CDI` | 21 | 2026-07-04 to 2026-10-07 |
| 04 Mass Ingestion and CDC | `DBMI` | 5 | 2026-07-25 to 2026-09-28 |
| 05 Application Integration (CAI) | `CAI` | 17 | 2026-07-07 to 2026-11-01 |
| 06 Data Quality and profiling | `DQ` | 15 | 2026-06-28 to 2026-11-02 |
| 07 Catalog and governance (CDGC) | `CDGC` | 26 | 2026-06-28 to 2026-10-26 |
| 08 MDM | `MDM` | 11 | 2026-07-06 to 2026-09-28 |
| 09 CLAIRE and MCP | `MCP` | 14 | 2026-07-09 to 2026-10-01 |
| 10 Migration and org management | `MIG`, `CLEAN` | 17 | 2026-07-26 to 2026-09-29 |
| 11 IPU, metering and licensing | `IPU` | 7 | 2026-07-04 to 2026-09-03 |
| 12 Claude working methods | `METHOD` | 8 | 2026-07-05 to 2026-09-29 |
| 13 Environment and ops | `ENV` | 3 | 2026-07-08 to 2026-09-24 |
| 14 UI automation | `UI` | 6 | 2026-07-07 to 2026-09-28 |
| **Total** | 16 prefixes | **185** | 2026-06-27 to 2026-11-02 |

---

## 01. Access, auth and orgs (11)

Lessons file: [01 Access & Auth](by-domain/01-access-auth.md)

| Lesson | Old belief | Held | Overturned by | What to do now |
|---|---|---|---|---|
| L-AUTH-077 | IDMC REST has no PUT or PATCH; update only by POST to the id | 2026-07-25 to 2026-09-27 | L-AUTH-016 (2026-09-28) | Update v2 objects by POSTing the full body to the id; use PUT where it is proven (runtime selections, catalog sources, profiles) and probe any other documented PUT or PATCH first |
| L-AUTH-078 | Never send a v3 session to a v2 endpoint; always keep two separate sessions | 2026-07-05 to 2026-09-20 | L-AUTH-020 (2026-09-21) | One session value can serve v2 and v3; keep the header name per plane, and keep a v3 session for the planes that reject the v2 id |
| L-AUTH-079 | The Data Profiling routes are SPA-session-only and not scriptable | 2026-07-09 to 2026-09-23 | L-AUTH-026 (2026-09-24) | Script profiling over REST with `IDS-SESSION-ID` (the v3 session on some pods) |
| L-AUTH-080 | The IDMC session is a 30-minute idle timeout, so a cached session stays valid while calls keep flowing | 2026-07-05 to 2026-09-27 | L-AUTH-027 (2026-09-28) | Refresh sessions by age: at most about 25 minutes after grant, whatever the activity |
| L-AUTH-081 | Parallel agents should each log in and mint their own token instead of sharing a cache | 2026-06-27 to 2026-08-19 | L-AUTH-031 (2026-08-20) | Share one cached session under a file lock; never give each agent its own login |
| L-AUTH-082 | Repeated IDS_085 at login means the account is locked or its password changed | 2026-09-22 (part of one session) | L-AUTH-035 (2026-09-22) | On `IDS_085`, check the login domain and the full user name before touching the password; `IDS_086` is the only lock code |
| L-AUTH-083 | Access to the org is a hard wall that only the account owner can clear | 2026-07-24 | L-AUTH-056 (2026-07-25) | Before calling an org walled, log in, read privileges and agents, and try a free create and delete |
| L-AUTH-084 | /public/core/v3/users/{id} rejects GET, PUT, PATCH and DELETE with 405 | 2026-07-25 to 2026-09-27 | L-AUTH-058 (2026-09-28) | Delete users with `DELETE /public/core/v3/users/<id>` (204); an edit is still a delete and re-create |
| L-AUTH-085 | The login products[] list decides entitlement | 2026-07-04 to 2026-09-21 | L-AUTH-070 (2026-09-23) | Read entitlement from privileges, engines, selections and `EffectiveLicenses()`, never from `products[]` |
| L-AUTH-086 | Read and run are headless; publish, deploy and serve are UI-only | 2026-07-09 to 2026-09-27 (overturned in part) | L-AUTH-016 (2026-09-28) | Treat "publish and deploy are UI-only" as a hypothesis and check the capability map; MDM model deploy and a few governance clicks remain |
| L-AUTH-087 | A 404 on a REST probe means the capability is not provisioned | until 2026-07-05 | L-AUTH-071 (2026-07-05) | A 404 is a path or host problem until a host sweep and the stopping rule say otherwise |

## 02. Secure Agent and connections (24)

Lessons file: [02 Secure Agent & Connections](by-domain/02-secure-agent-connections.md)

| Lesson | Old belief | Held | Overturned by | What to do now |
|---|---|---|---|---|
| L-AGENT-078 | Secure Agent registration needs the UI | until 2026-07-01 (restated in an August note) | L-AGENT-002 (2026-07-01) | Register agents headless: installer info over v2, then `configureToken` on the host |
| L-AGENT-079 | Secure Agent services and connectors can only be enabled in the Administrator UI | 2026-07-04 to 2026-09-22 | L-AGENT-039 (2026-09-28) | Enable services and connectors with the selections GET/PUT, or MCP `secureagentmanagement` |
| L-AGENT-080 | Enabling a connector adapter on an agent has no REST verb, and jar copies do not work | 2026-09-20 to 2026-09-23 | L-AGENT-039 (2026-09-23) | Select connectors on the runtime environment (REST PUT or MCP); copying adapter jars still enables nothing |
| L-AGENT-081 | No PUT is proven anywhere in IDMC | July 2026 | L-AGENT-039 (2026-09-28) | PUT is proven on the selections route; probe any other PUT before designing on it |
| L-AGENT-082 | readyToRun:false on the runtime-environment list means IDMC never marked the agent runnable | 2026-07-26 (same day) | L-AGENT-021 (2026-07-26) | Read `readyToRun` per agent (`GET /api/v2/agent/<id>`), not from the runtime-environment list |
| L-AGENT-083 | An engine reading RUNNING is usable, so the connection test should pass | until 2026-07-26 | L-AGENT-023 (2026-07-26) | Prove an engine usable with a connection test or a job that lands rows |
| L-AGENT-084 | Enabling agent services is free and safe | until 2026-07-26 | L-AGENT-052 (2026-07-26) | Budget RAM, disk and downloads before selecting services; never select everything on a small host |
| L-AGENT-085 | 403 APP_13401 / 500 CMN_001 on /api/v2/agent/service prove no enablement plane exists | until 2026-07-26 | L-AGENT-031 (2026-07-26) | Router-artifact codes prove nothing; bogus-twin before citing any answer under `/api/v2/agent/*` |
| L-AGENT-086 | CAI is not activatable: the agent has no Process Server runtime | 2026-09-21 (hours) | L-AGENT-048 (2026-09-21) | Read `agentEngines[]`: a Process Server listed there means CAI is provisioned |
| L-AGENT-087 | The BigQuery V2 403 APP_105060 and the PostgreSQL 'connector not registered' errors are permanent walls | 2026-09-21 to 2026-09-22 | L-AGENT-045 (2026-09-23) | Re-test connections after an agent is re-provisioned before escalating an adapter wall |
| L-CONN-076 | Creating a CCI connection (or any new source connection) requires the Administrator UI | 2026-06-27 to 2026-07-04 | L-CONN-001 (2026-06-27) | Create connections over v2 with `TOOLKIT_CCI`, `instanceName` and `connParams`; only a brand-new add-on type needed one UI save (July) |
| L-CONN-077 | 'Unable to load driver' on JDBC V2 needs the Administrator upload-JAR flow; a file copy is never enough | 2026-07-26 to 2026-08-18 | L-CONN-051 (2026-08-19) | Stage third-party JDBC jars in `common/` (and `deploy_to_main`), restart, then test; no UI upload is needed |
| L-CONN-078 | JDBC V2 takes credentials in connParams.user like other connectors | until 2026-07-26 | L-CONN-047 (2026-07-26) | Use the manifest's attribute names (`username`, `password`) for JDBC V2 |
| L-CONN-079 | If a connector appears in GET /api/v2/connector, the org can use it | until 2026-07-26 | L-CONN-021 (2026-07-26) | Treat `GET /api/v2/connector` as a type catalog; read the runtime environment's selections and the agent's adapters |
| L-CONN-080 | Fix a BigQuery JSON-column failure by flipping the connection from Simple to Hybrid | 2026-07-04 (plan) | L-CONN-042 (2026-07-04) | Keep BigQuery connections in Simple mode; land JSON through STRING casts or JSON-typed target columns |
| L-CONN-081 | Flat-file connections need the flat-file connector enabled in the UI | 2026-09-20 to 2026-09-23 | L-CONN-065 (2026-09-24) | Create flat-file connections headless with `type: CSVFile` |
| L-CONN-082 | The BigQuery privateKey can be sent as the stripped base64 body everywhere | 2026-09-22 to 2026-09-23 | L-CONN-035 (2026-09-25) | Test each consumer of a BigQuery key separately, and split connections when their key forms disagree |
| L-CONN-083 | The full PEM with literal \n escapes works for CDI and every other consumer | 2026-09-24 to 2026-09-28 | L-CONN-035 (2026-09-28) | Probe the key form per engine and per pod; keep one connection per consumer |
| L-CONN-084 | A never-browsed PostgreSQL connection cannot resolve source objects over REST | 2026-09-22 | L-CONN-028 (2026-09-23) | Use `<schema>/TABLE/<table>` object paths; no UI browse is needed |
| L-CONN-085 | IDMC native writes into Fabric land nothing | early July 2026 | L-CONN-071 (2026-07-09) | Verify Fabric targets by row count; a create-new-at-runtime target lands rows through the engine |
| L-CONN-086 | Chunking long text into 250-character columns is the only in-IDMC way past the 255 cut | 2026-09-23 to 2026-09-24 | L-CONN-044 (2026-09-24) | Land long text in JSON-typed target columns and retire chunk columns |
| L-CONN-087 | An older ClickHouse -all jar plus slf4j needed a UI connection test | 2026-07-13 | L-CONN-054 (2026-08-19) | Use the shaded ClickHouse jar with `http_connection_provider=HTTP_URL_CONNECTION`, tested headless |
| L-AGENT-055 | The agent downloads folder is a re-fetchable installer cache that can be cleared, or moved aside, when no engine is deploying | 2026-07-08 to 2026-09-28 | L-AGENT-094 (2026-09-30) | Never prune or move `downloads/`; size the agent volume up front and free disk in logs, the journal and other volumes |
| L-CONN-089 | JDBC V2 cannot import ClickHouse object metadata (JDBC_V2_ERROR_205), so do not plan direct profiling or cataloging of ClickHouse through JDBC V2; stage a sample in a natively supported database | 2026-10-03 to 2026-10-29 | L-DQ-128 (2026-11-02; L-CONN-089 is kept as disputed) | Profile ClickHouse over REST from a body cloned from a profile that has run on JDBC V2 (`TOOLKIT_CCI`, `<database>/TABLE`, NSTRING fields with `dataType` varchar); for catalog lineage, note that the generic JDBC type offers no Lineage Discovery (L-CDGC-234) |

## 03. Data Integration (CDI) (21)

Lessons file: [03 Data Integration (CDI)](by-domain/03-data-integration-cdi.md)

| Lesson | Old belief | Held | Overturned by | What to do now |
|---|---|---|---|---|
| L-CDI-174 | CDI mapping authoring is UI-only; one mapping must be authored in the UI first | 2026-06-27 to 2026-09-22 | L-CDI-003, L-CDI-021, L-CDI-033 (2026-09-23) | Build mappings headless: template tasks (route 1) or synthesized IMF packages (route 5); `POST /api/v2/mapping` is still not a create route |
| L-CDI-175 | v2-created mapping tasks do not surface in a v3 type=='MTT' scan | 2026-09-23 | L-CDI-012 (2026-09-25) | Cross-check v3 `MTT` counts with `/api/v2/task?type=MTT` before concluding anything |
| L-CDI-176 | The v2 task resources exist on every pod | July 2026 | L-CDI-015 (2026-07-26) | Never generalize a v2 inventory from one org: task resources mount per pod and per engine |
| L-CDI-177 | Moving an asset to another project is a UI Explore action | 2026-08-19 | L-CDI-016 (2026-09-24) | Move objects with FRS `MoveEntities`; ids, schedules and run history survive |
| L-CDI-178 | Headless CDI data movement is walled (a cold PostgreSQL source cannot resolve) | 2026-09-22 to 2026-09-23 | L-CDI-021, L-CDI-162 (2026-09-23) | Land data headless with template tasks and the `<schema>/TABLE/<table>` path |
| L-CDI-179 | Mapping tasks, taskflows and schedules for a redesign are UI-only | early July 2026 | L-CDI-025, L-CDI-075 (2026-07-09) | Clone tasks, and create and bind schedules, over v2 |
| L-CDI-180 | A mapping's connection and SQL are compiled into a binary bin/@3.bin that cannot be edited | 2026-07-05 to 2026-09-22 | L-CDI-027 (2026-09-22) | Read, diff and regenerate a mapping's IMF JSON; a package edit still does not change its connector type |
| L-CDI-181 | Hand-built import packages are always rejected with MigrationSvc_030 | 2026-06-28 to 2026-09-28 | L-CDI-032 (2026-09-29) | Build packages from scratch with correct metadata, folder entries and checksums; `MigrationSvc_030` means an empty or malformed upload |
| L-CDI-182 | There is no REST read-back or diff of a mapping's internals | 2026-07-26 | L-CDI-027 (2026-09-22) | Export a mapping and read its IMF to review or diff it |
| L-CDI-183 | Scheduling and monitoring mapping tasks requires the Administrator UI | early July 2026 | L-CDI-073, L-CDI-075 (2026-07-04) | Schedule and monitor over v2: `/api/v2/schedule`, `scheduleId`, the activity log |
| L-CDI-184 | Taskflow creation is UI-only | July 2026 (`/public/core/v3/taskflow` 404) | L-CDI-069 (2026-09-24) | Build linear taskflows over `/api/v2/workflow`; advanced-taskflow publish is still walled |
| L-CDI-185 | Binding a schedule over v2 is untested; plan a UI fallback | 2026-09-28 (a draft runbook) | L-CDI-075 (2026-09-28) | Bind and unbind schedules by POSTing `scheduleId` (null unbinds), then read back |
| L-CDI-186 | Long text can only be kept by chunking into 250-character columns or by a Fields-tab edit | 2026-09-23 to 2026-09-24 | L-CDI-153 (2026-09-24) | Pre-create JSON target columns for long text |
| L-CDI-187 | Reverse-ETL into an application database needs a UI-authored mapping | 2026-09-24 | L-CDI-089 (2026-09-24) | Deliver reverse-ETL as a template task with a PostgreSQL upsert target |
| L-CDI-188 | A raw task in no taskflow means the downstream mart reads stale data | 2026-09-29 (morning audit) | L-CDI-147 (2026-09-29) | Before fixing a task that sits in no taskflow, check whether its target has become a view |
| L-CDI-189 | REST-started agent jobs start on a ~3-minute job-poll cadence | 2026-08-20 (one agent; 15 serial tasks ≈ 45 min) | L-CDI-121 (2026-09-28) | Expect about 20 s of fixed cost per task; minutes of dispatch point at the agent |
| L-CDI-190 | Swapping a mapping's target connection to another warehouse later is a quick change | 2026-06-27 (a plan) | L-CDI-050, L-CDI-031 (2026-07-04) | Retarget by changing the mapping (re-import OVERWRITE); target POSTs to the task are silent no-ops |
| L-CDI-191 | The first mapping for a new connector pair must be authored in the UI | 2026-07-07 | L-CDI-033 (2026-09-29) | Synthesize mappings from harvested exemplars; adapters never tried (Salesforce and PostgreSQL targets, flat-file sources) stay unproven |
| L-CDI-042 | BigQuery full pushdown cannot be enabled over REST: the session property persists but nothing pushes down | 2026-09-29 to 2026-09-30 | L-CDI-202 (2026-10-01) | Set `Pushdown Optimization: Full`, `Allow Temporary View for Pushdown: Yes` and `enableCrossSchemaPushdown: true` on the v2 mapping task, prove OPT_63367 in the session log, and keep pushdown only where it measures faster |
| L-CDI-225 | Every Structure Parser output field is a string(255); the real types stay in the model | 2026-10-06 | L-CDI-229 (2026-10-07) | Expect the model's types on the parser ports (bigint, decimal, string(n)); codes like ABC-001 lose separator and leading zeros |
| L-CDI-226 | A Structure Parser stores the model's v2 id as isdModelId | 2026-10-06 | L-CDI-230 (2026-10-07) | The mapping stores '@<v3 id>' + a model copy + passthrough per group; the designer resolves the model by its v2 id |

## 04. Mass Ingestion and CDC (5)

Lessons file: [04 Mass Ingestion & CDC](by-domain/04-mass-ingestion-cdc.md)

| Lesson | Old belief | Held | Overturned by | What to do now |
|---|---|---|---|---|
| L-DBMI-045 | DBMI authoring is a UI wizard because every mi/dbmi REST path 404s | 2026-07-04 to 2026-07-25 | L-DBMI-001 (2026-07-26) | Send DBMI calls to `<pod>-ing`; sweep the host family before calling any product UI-only |
| L-DBMI-046 | A DBMI 404 means the entitlement is missing and needs a purchase | 2026-07-04 to 2026-07-05 | L-DBMI-041 (2026-07-25) | Read DBMI entitlement from engines and privileges, not from 404s |
| L-DBMI-047 | DBMI deploy and run have no public REST verb | 2026-09-22 to 2026-09-23 | L-DBMI-003 (2026-09-28) | Deploy and run with `task/deploy/<taskId>` and `job/start` under `/dbmi/public/api/v2` on `<pod>-ing` |
| L-DBMI-048 | Author the first DBMI task in the UI wizard, then clone it | 2026-07-04 to 2026-09-21 | L-DBMI-003 (2026-09-28) | Create tasks from JSON with `task/create`, cloning a body from `task/details` |
| L-DBMI-049 | A datatype rule (timestamptz to STRING) fixes the fractional-seconds defect | 2026-09-26 (hours) | L-DBMI-023 (2026-09-26) | Never set datatype rules on a BigQuery-target CDC task; repair the timestamps in the views |

## 05. Application Integration (CAI) (17)

Lessons file: [05 Application Integration (CAI)](by-domain/05-application-integration-cai.md)

| Lesson | Old belief | Held | Overturned by | What to do now |
|---|---|---|---|---|
| L-CAI-097 | CAI publish has no REST verb; a human must click Publish in Application Integration | 2026-07-04 to 2026-07-26 | L-CAI-001 (2026-09-28) | Publish with `asset/v1/publish` on `<pod>-cai`, using `Explore/...` asset paths |
| L-CAI-098 | Publishing CAI over REST is an undocumented bypass, and a 403 on asset/publish means there is no API | 2026-07-06 to 2026-07-25 | L-CAI-001 (2026-09-28) | The bulk publish resource is documented and supported: use it |
| L-CAI-099 | CAI first publish is blocked until Informatica fixes the designer build | 2026-07-08 to 2026-07-09 | L-CAI-013 (2026-07-09) | Publish over REST when the designer regresses, and send the asymmetry evidence to support |
| L-CAI-100 | Migration-imported CAI assets need one UI Save in Process Designer before they can be published | 2026-09-09 to 2026-09-24 | L-CAI-003, L-CAI-020 (2026-09-28) | Publish imported and hand-built assets directly with the `Explore/<project>/<folder>/<name>.<TYPE>.xml` path |
| L-CAI-101 | CAI process authoring is UI-only because POST /public/core/v3/objects returns 405 | 2026-07-04; again 2026-09-20 to 2026-09-22 | L-CAI-016, L-CAI-020 (2026-09-25) | Author CAI assets through a v3 import: a clone or a package built from scratch |
| L-CAI-102 | Unpublish CAI assets in the same order as publish: service connector, app connection, process | 2026-07-25 to 2026-09-28 | L-CAI-007 (2026-09-29) | Unpublish dependents first: processes, then app connections, then service connectors |
| L-CAI-103 | Secrets inside a CAI app connection can only be set in the UI | 2026-07-08 to 2026-09-25 | L-CAI-061 (2026-09-26) | Rotate connection secrets by re-importing the connection OVERWRITE and republishing; treat packages as secrets |
| L-CAI-104 | A CAI process cannot be scheduled natively, so scheduling needs a DI taskflow or browser automation | 2026-07-09 | L-CAI-045 (2026-07-09) | Schedule REST-bound processes with the restadmin scheduler |
| L-CAI-105 | Operational Insights has no API plane | to 2026-07-25 | L-CAI-049 (2026-07-25) | Export job history through the Operational Insights GraphQL route on `<pod>-cai` |
| L-CAI-106 | The CAI restadmin plane exists only on the dm-us host family | to 2026-07-25 | L-CAI-048 (2026-07-25) | restadmin answers on dmp-us pods too; a scheduler 401 is a role gap |
| L-CAI-107 | A Process Server 'validation failed' (404 on the status probe) means the engine is broken | 2026-07-04 | L-CAI-068 (2026-09-24) | Health-check the Process Server on the agent host (`https://localhost:7443/process-engine/status`) |
| L-CAI-108 | CAI is not provisioned or not licensed on the org | 2026-07-04 to 2026-07-05; again 2026-09-21 | L-CAI-077 (2026-09-21) | Read CAI entitlement from engines and PROCESS objects, not from `products[]` |
| L-CAI-109 | Enabling the Process Server on a Secure Agent is a UI-only Administrator toggle | 2026-07-09 to 2026-09-27 | L-CAI-066 (2026-09-28) | Enable the Process Server through the selections PUT, then verify that it really runs |
| L-CAI-110 | CAI has never run in the org, and publish and run are UI-only (/active-bpel/rt 404, /process-engine/rt 401) | to 2026-07-07 | L-CAI-042 (2026-07-07) | Call cloud-published processes on `<pod>-cai`; an agent's empty run history says nothing about them |
| L-CAI-111 | No PUT is proven anywhere in IDMC, so documented restadmin PUTs should be retried as POST on 405 | 2026-07-25 to 2026-09-28 | L-CAI-044 (the documented PUTs, 2026-07-25); the premise fell with L-AUTH-016 (2026-09-28) | Try the documented restadmin PUTs as PUTs; they are still unexercised |
| L-CAI-117 | Kafka and JMS event sources, listener processes and fault handling can only be authored in the Process Designer | 2026-09-22 to 2026-10-07 | L-CAI-116 (2026-10-08) | Author Kafka and AMQP connections and event-bound processes in an import package, publish them over REST, and start or stop listeners with restadmin (L-CAI-119, L-CAI-122) |
| L-CAI-049 | The Operational Insights GraphQL export takes the documented `Authorization: Bearer <session id>` header | 2026-07-25 to 2026-11-01 | L-CAI-159 (2026-11-01; L-CAI-049 is kept as disputed for its header) | Send `IDS-SESSION-ID: <session id>`: 200 with `data.processJobReport[]`, while the Bearer form answered 401 on the same query |

## 06. Data Quality and profiling (15)

Lessons file: [06 Data Quality & Profiling](by-domain/06-data-quality-profiling.md)

| Lesson | Old belief | Held | Overturned by | What to do now |
|---|---|---|---|---|
| L-DQ-083 | Native CDQ rule authoring is UI-only | 2026-07-04 to 2026-07-07 | L-DQ-010 (2026-07-09) | Clone a template rule specification through v3 export and import; new logic still needs the rule-builder canvas |
| L-DQ-084 | CDQ has no REST write path at all | until 2026-07-25 | L-DQ-006 (2026-07-25) | Use the Dictionary API on `<pod>-dqcloud-api` for reference data; rule logic and scorecards stay outside the public API |
| L-DQ-085 | Data Profiling has no API; it only rides a catalog scan | until 2026-07-25 | L-DQ-019 (2026-07-26) | Use the Data Profiling REST service on `<pod>-dqprofile` |
| L-DQ-086 | Data Profiling routes are SPA-session only | 2026-07-09 to 2026-07-25 | L-DQ-020 (2026-09-24) | Send `IDS-SESSION-ID` carrying a login session (the v3 session on some pods) |
| L-DQ-087 | Profile execution has no public REST verb | 2026-09-13 to 2026-09-21 | L-DQ-019 (2026-09-24) | Run profiles with `POST /profile/<id>/execute`; `/api/v2/job` cannot run them |
| L-DQ-088 | Binding rules to a profile (rule occurrences) is UI-only | 2026-09-13 | L-DQ-023 (2026-09-24) | Bind rule occurrences in `PUT /profile/<id>` with `MAPPLETFIELD` entries; dimensions still come from the rule spec |
| L-DQ-089 | Profile authoring is UI-only (POST /v3/objects = 405) | 2026-09-20 | L-DQ-025 (2026-09-28) | Create profiles from a template body with `POST /profile`, or move them in packages |
| L-DQ-090 | The DQ agent upload PUT fails with a permanent 409 (a per-user preview cap) | 2026-09-04 | L-DQ-072 (2026-09-21) | Upload with `curl --http1.1 -H "Expect:"`, a unique file name and a fresh URL on each 409 |
| L-DQ-091 | Empty profiling was a stuck-job 406 lock, readyToRun=false or ccgf-auth-pep 500 errors | June 2026 (to 2026-06-28) | L-DQ-037 (2026-06-28) | On zero profiled columns, read the `pmdtm` exit code first (127 means a missing native library) |
| L-DQ-092 | Low profiling coverage (~17%) is caused by the connector skipping json/enum/array; casting views take it to ~100% | 2026-06-28 to 2026-07-09 | L-DQ-042 (2026-07-26) | Measure coverage against non-empty tables; casting views recover very little |
| L-DQ-093 | CDGC catalog scans and profiling are UI-initiated; there is no REST trigger | 2026-07-05 | L-DQ-043 (2026-09-24) | Trigger scans and profiling over REST: `data360/executable/v1/catalogsource/<id>` with `capabilityNames` |
| L-DQ-044 | Running only the Data Quality capability returns 406 | 2026-07-09 | L-CDGC-143 (2026-09-30) | Run `capabilityNames: ['Data Quality']` once the source's typeCapabilities carry the Data Profiling and Data Quality Scope groups with a runtime environment; a failed job still shows no error text over REST |
| L-DQ-051 | Catalog rule occurrences score 1 of 6, and reading the scores is UI-only | 2026-07-09 | L-DQ-097, L-CDGC-144 (2026-09-30) | All 9 accepted instances scored in one run; read the scores through the `dataQuality` segment or ask CLAIRE, and recompute the rules in the warehouse to check them |
| L-DQ-052 | Catalog rule occurrences have no create path, and a warehouse source can't be scored | 2026-07-09 | L-CDGC-143, L-MCP-086, L-DQ-097 (2026-09-30) | Create occurrences through CLAIRE GPT's recommend-and-accept with the columns named (no REST create verb seen); a warehouse source scores once its typeCapabilities carry a runtime environment |
| L-DQ-119 | A REST profile on a JDBC V2 ClickHouse source cannot be created (NSTRING refused with PROFILE_MDL_00006, 'string' hangs), so direct profiling of ClickHouse stays blocked | 2026-10-29 | L-DQ-128 (2026-11-02; L-DQ-119 is kept as disputed: what differed was not isolated) | Clone a profile that has already run on a JDBC V2 connection, with NSTRING fields typed `dataType` varchar; five ClickHouse profiles completed, up to ALL_ROWS over 101M rows |

## 07. Catalog and governance (CDGC) (26)

Lessons file: [07 Catalog & Governance (CDGC)](by-domain/07-catalog-governance-cdgc.md)

| Lesson | Old belief | Held | Overturned by | What to do now |
|---|---|---|---|---|
| L-CDGC-120 | Scans can only be triggered from the UI: the ccgf-auth-pep 500 is a platform auth bug | 2026-06-27 to 2026-07-25 | L-CDGC-034 (2026-06-28) | Scan over REST with the three identity headers and a non-empty `capabilityNames` |
| L-CDGC-121 | Every run returning 406 with zero profiled columns means a stuck scan holds the source lock (root cause) | 2026-06-28 | L-CDGC-044 (2026-06-28) | When every source fails profiling the same way, check the agent's native profiling engine |
| L-CDGC-122 | The CDGC search API needs an undiscovered query parameter; verify assets in the Explore UI instead | until 2026-06-28 | L-CDGC-073 (2026-06-28) | Search with the Elasticsearch endpoint and `X-INFA-SEARCH-LANGUAGE: elasticsearch` |
| L-CDGC-123 | data360/search/v1/assets is a dead end (400 MissingServletRequestParameter forever) | 2026-06-28 to 2026-07-25 | L-CDGC-074 (2026-09-24) | Send `knowledgeQuery` and `segments` to `data360/search/v1/assets` |
| L-CDGC-124 | Catalog-source types cannot be listed over REST; pick them in the MCC wizard | 2026-07-04 to 2026-08-20 | L-CDGC-016 (2026-09-24) | List catalog-source types with `GET .../datasourceTypes` |
| L-CDGC-125 | Glossary terms, domains, classifications and policies have no REST create; the content service is misrouted | 2026-06-28 to 2026-07-25 | L-CDGC-051 (2026-09-24) | Create domains and terms with `POST data360/content/v1/assets`; policies and DAM remain walled |
| L-CDGC-126 | Term-to-column binding and glossary relationships are UI-only | 2026-07-04 to 2026-07-25 | L-CDGC-056 (2026-09-24) | Link terms to assets with a PATCH on the `glossary` segment |
| L-CDGC-127 | A catalog source's object selection, capability configuration and connection binding can only be changed in MCC | 2026-06-29 to 2026-08-20 | L-CDGC-020 (2026-09-25) | Change filters and options with a multipart PUT of the edited definition |
| L-CDGC-128 | Catalog-source registration and deletion are MCC-UI-only on orgs where catalog-source-management is not routed | 2026-08-18 to 2026-09-28 | L-CDGC-014 (2026-09-24) | Register sources with the multipart create on the ccgf plane; only the definition delete stays in the UI |
| L-CDGC-129 | The org has no CDGC entitlement: the login lists only Integration Cloud and the data360 paths 404 | 2026-09-21 to 2026-09-24 | L-CDGC-007 (2026-09-24) | Decide CDGC entitlement from selections, engines, privileges and a real create |
| L-CDGC-130 | CDGC is not licensed on an org whose data360 plane returns zero-byte 200s | 2026-07-25 | L-CDGC-006 (2026-07-25) | Treat zero-byte 200s as gateway artifacts and bogus-twin them |
| L-CDGC-131 | An INFACore REST 404 means INFACore is not available or not entitled | until 2026-07-04 | L-CDGC-011 (2026-07-04) | INFACore is a client SDK: ignore its 404 |
| L-CDGC-132 | Data Marketplace publishing and checkout are UI-only | early July 2026 (restated 2026-09-12) | L-CDGC-092 (2026-07-04) | Create Marketplace objects over REST; only delivery templates are UI |
| L-CDGC-133 | DAM control types cannot be demonstrated without the DAM entitlement | until 2026-07-06 | L-CDGC-067 (2026-07-06) | Demonstrate DAM controls as warehouse pushdown; only policy authoring is UI |
| L-CDGC-134 | The scan capability is triggered with the enum CATALOG_EXTRACT | 2026-07-25 to 2026-09-13 | L-CDGC-035 (2026-08-20) | Use display names ("Metadata Extraction") in `capabilityNames` |
| L-CDGC-135 | The observable jobs path form is disputed (/api/ infix required vs not) | 2026-07-08 | L-CDGC-037 (2026-07-10) | Poll one job at `observable/v1/jobs/<jobId>`; list jobs at `observable/api/v1/jobs` |
| L-CDGC-136 | readyToRun=false blocks catalog-source creation until a support ticket clears it | 2026-06-27 | L-CDGC-022 (2026-06-28) | Send `IDS-SESSION-ID` on catalog-source create; `readyToRun=false` never blocked scans |
| L-CDGC-137 | Glossary, Marketplace and Reference 360 have no REST on a trial org (platform-host 404s) | 2026-06-29 | L-CDGC-005 (2026-07-04) | Call glossary and Marketplace routes on `idmc-api`, with the `/api/` infix |
| L-CDGC-138 | An API Manager 503 means the plane is routed but empty | 2026-07-25 | L-CDGC-105 (2026-07-26) | A 503 from the API Manager hosts means nothing: bogus paths get it too |
| L-CDGC-082 | Rule occurrences have no create API, and reading scores means scraping the Score tab | 2026-07-09 | L-CDGC-144 (2026-09-30) | Census RuleInstances by class, delete them with the content API, and create them with CLAIRE's recommend-and-accept (L-MCP-086) |
| L-CDGC-031 | A Salesforce catalog source on a legacy v2 Salesforce connection cannot scan | 2026-09-29 | L-CDGC-142 (2026-09-30) | Retry the scan with the metadata services selected on the runtime environment before building a new connection |
| L-CDGC-086 | Connection assignments cannot be accepted headless: the accept call is operationType=ASSIGN, still unproven, so accept in MCC | 2026-09-30 | L-CDGC-159 (2026-10-06) | MERGE-assign each IICS connection reference to its physical source (SPLIT undoes), then prove it with a lineage read-back |
| L-CDGC-180 | Lineage edges cannot be written over REST: a ccgf-contentv2 lineage publish answers 207 with items: [] and changes nothing | 2026-08-20 to 2026-10-07 | L-CDGC-179 (2026-10-08) | Publish curated RELATIONSHIP items with core.DataSetDataFlow (tables) or core.DirectionalDataFlow (columns) |
| L-CDGC-085 | No lineage-graph REST: read lineage through MCP get_asset_details | 2026-07-25 to 2026-10-07 | L-CDGC-156 (2026-10-04), L-CDGC-181 (2026-10-08) | Read lineage hop by hop from the asset read with segments=all (the lineage and neighborhood segments); the /data360/lineage/* graph routes are still not found |
| L-CDGC-188 | The only current Databricks catalog type, `Databricks Notebooks`, catalogs notebooks, not Unity Catalog tables or views | 2026-10-12 to 2026-10-18 | L-CDGC-206 (2026-10-19) | Catalog Databricks with a `Databricks Notebooks` source on a native Databricks Delta connection, not JDBC V2; grant the scan user system.access lineage for Unity lineage |
| L-CDGC-040 | There is no REST cancel for a running scan (every variant answered 404 or 405); cancel in MCC | 2026-07-25 to 2026-10-25 | L-CDGC-221 (2026-10-26), refined by L-CDGC-225 (2026-10-26) | Cancel with `POST .../ccgf-orchestration-management-api-server/api/v1/jobs/<jobId>/operations/cancel` from a script or the console, then poll for CANCELLED: 1-2 min while Test Connection runs, 50+ min once extraction runs |

## 08. MDM (11)

Lessons file: [08 MDM](by-domain/08-mdm.md)

| Lesson | Old belief | Held | Overturned by | What to do now |
|---|---|---|---|---|
| L-MDM-059 | A record-API 404 'metadata ... cannot be found during load' means the business entity is not deployed | 2026-07-04 to 2026-07-06 | L-MDM-006 (2026-07-08) | Address business entities by runtime id (for example `c360.person`), never by design GUID |
| L-MDM-060 | MDM is undeployed because about 30 config, deploy, record and steward REST endpoints return 404 | to 2026-07-06 | L-MDM-018 (2026-07-06) | Check the Business 360 Console My Jobs page before calling MDM undeployed |
| L-MDM-061 | Ingest Person records with fullName, sourceRecordCount and an integer trustScore | 2026-07-05 to 2026-07-08 | L-MDM-019 (2026-07-08) | Send a bare field map with `firstName`, `lastName` and a string `trustScore` |
| L-MDM-062 | A 403 on GET entity/<be>/<id> means the entity exists and you only lack rights | to 2026-07-26 | L-MDM-009 (2026-07-27) | A 403 on GET entity proves only the plane; use the ingest gate with a fake-entity control |
| L-MDM-063 | MDM model deploy must have a REST verb somewhere: keep hunting | to 2026-07-26 | L-MDM-005 (2026-07-27) | Stop hunting for a model-deploy verb and plan the Modeler step |
| L-MDM-064 | The <pod>-mdm host is not mounted on this org | 2026-07-26 | L-MDM-010 (2026-07-26) | Probe several prefixes on `<pod>-mdm` against a bogus sibling before calling the host absent |
| L-MDM-065 | Reference 360 is unavailable because referenceDataSets returns 404 | 2026-07-26 | L-MDM-026 (2026-07-26) | Use `/rdm-service/external/v1/search` for Reference 360 |
| L-MDM-066 | MDM / Customer 360 is not licensed on the org | 2026-07-04 to 2026-07-06 | L-MDM-011 (2026-07-27) | Read MDM entitlement from privileges, roles and design objects |
| L-MDM-067 | The Product 360 documentation describes the MDM you have | to 2026-07-26 | L-MDM-055 (2026-07-27) | Check which product the org holds before applying any P360 document |
| L-MDM-068 | The migration clone route is closed on this pod (import/package 404 MigrationSvc_025) | 2026-07-26 | L-MDM-014 (2026-07-26) | Upload packages as `multipart/form-data`; what an empty org lacks is a template |
| L-MDM-069 | There is no public REST search, list or count of MDM records, so master-record counts cannot be read headless | 2026-07-08 to 2026-09-27 | L-MDM-025 (2026-09-28) | Search and export records with `POST /search/public/api/v1/search` (10,000 per query) |

## 09. CLAIRE and MCP (14)

Lessons file: [09 CLAIRE & MCP](by-domain/09-claire-mcp.md)

| Lesson | Old belief | Held | Overturned by | What to do now |
|---|---|---|---|---|
| L-MCP-069 | The managed MCP catalog is exactly five servers with eleven actions and one write | 2026-07-25 to 2026-07-26 | L-MCP-001 (2026-09-23) | Enumerate the org's own registry on `hdm` before quoting any number of servers or tools |
| L-MCP-070 | GET /public/core/v3/mcpServers is the org's MCP registry | 2026-07-25 | L-MCP-001 (2026-09-22) | Read the registry at `hdm.<domain>/a2e-mcp-asset-mgmt-svc/api/v1/mcp-servers` |
| L-MCP-071 | The MCP surface is DQ-only and cannot cross the integration walls | 2026-09-23 (afternoon) | L-MCP-001 (2026-09-23) | Test the full registry, not only the servers wired into the current session |
| L-MCP-072 | MCP OAuth clients can only be created in the UI wizard | 2026-07-26 to 2026-09-28 | L-MCP-018 (2026-09-28) | Create OAuth clients over REST; write the one-time secret straight to a 0600 file |
| L-MCP-073 | The CLAIRE orchestrator has zero skills until the org owner loads them server-side | 2026-09-22 to 2026-09-23 | L-MCP-033 (2026-09-23) | Check which org a local CLAIRE shim logs into; the managed orchestrator is live |
| L-MCP-074 | The CLAIRE working action takes conversation_id | until 2026-07-26 | L-MCP-037 (2026-07-26) | Call `working` with no arguments |
| L-MCP-075 | AI Agent Engineering is not entitled, so no native agentic process or MCP server can be built | 2026-07-04 to 2026-07-08 | L-MCP-011 (2026-09-22) | A zero count from the unvalidated v3 filter proves nothing; read the registry |
| L-MCP-076 | CLAIRE GPT is not entitled, or has no plane | 2026-07-04 to 2026-07-25 | L-MCP-050 (2026-07-09) | Check `EffectiveLicenses()` and ask one live question on `claire-gpt.<domain>` |
| L-MCP-077 | IDMC MCP servers are roadmap, not shipping | before 2026-07-25 | L-MCP-009 (2026-07-25) | Managed MCP servers ship: enumerate them per org |
| L-MCP-078 | Nothing in MCP touches connections or administration, and glossary is UI-only on both REST and MCP | 2026-07-25 | L-MCP-049 (2026-09-23) | Choose REST or MCP per capability; connections, users, agents and glossary have MCP tools too |
| L-MCP-013 | MCP tool connections do not migrate: recreate them in the Application Integration designer | 2026-09-28 to 2026-09-29 | L-MCP-081 (2026-09-30) | Outside the AI Agent Engineering private preview the connection type does not exist (builder sunset): let your own agent call the vendor-hosted MCP servers and your MCP server through one gateway (L-MCP-082) |
| L-MCP-058 | What CLAIRE GPT answers reliably, and what fails: catalog-wide classification search, mappings by name, view lineage and product how-to all fail | 2026-09-28 to 2026-09-30 | L-MCP-091, L-MCP-092, L-MCP-093, L-MCP-094, L-MCP-107 (2026-10-01) | Ask "Which columns in the catalog are classified as CLASSIFICATION?"; explain mappings by name with the folder named; ask product how-to; view-level lineage answers, job-level lineage still needs the integration lineage setup |
| L-MCP-088 | "What should we fix first?" mixes real scores with invented issues | 2026-09-30 | L-MCP-095 (2026-10-01) | Add "Use only the scores in the catalog." to the fix-first prompt |
| L-MCP-053 | CLAIRE GPT NL-to-SQL has no headless invocation route | 2026-07-09 to 2026-09-30 | L-MCP-111 (2026-10-01) | Call the managed `orchestrate` or `data_explore` MCP tools: same answers as the UI, in 28-80 s |

## 10. Migration and org management (17)

Lessons file: [10 Migration & Org Management](by-domain/10-migration-org-management.md)

| Lesson | Old belief | Held | Overturned by | What to do now |
|---|---|---|---|---|
| L-MIG-061 | Design-object authoring is UI-only because POST /public/core/v3/objects returns 405 | 2026-07-04 to 2026-07-08, and again 2026-09-20 to 2026-09-21 | L-MIG-023 (2026-09-28) | Author design objects by migration clone or with a built package |
| L-MIG-062 | There is no v3 export/import API on this org; promotion is author-time UI | 2026-07-04 to 2026-07-08 | L-MIG-023 (2026-09-28) | Export and import work: debug a 404 as a path, host or role problem |
| L-MIG-063 | The migration clone backdoor is closed: import/package returns 404 MigrationSvc_025 | 2026-07-26 (one pass) | L-MIG-009 (2026-07-26) | Upload as multipart: the clone route is open |
| L-MIG-064 | An empty type-filtered census proves the type is unsupported | July 2026 to 2026-07-25 | L-MIG-002 (2026-09-25) | Filter on the client, or use exact type names; a zero count proves nothing |
| L-MIG-065 | A mapping's connection and SQL are compiled into a binary blob, so a package edit cannot retarget a mapping | 2026-07-05 to 2026-07-09 | L-MIG-029 (2026-09-22) | Edit the IMF JSON in `bin/@N.bin`, swapping GUIDs in place |
| L-MIG-066 | The import rejects hand-built packages with MigrationSvc_030; upload only genuine exports | 2026-06-28 to 2026-09-28 | L-MIG-022 (2026-09-29) | Build packages from scratch with the right metadata and checksums |
| L-MIG-067 | Anything a migration import creates needs a UI click to deploy or publish | 2026-07-26 to 2026-09-22 | L-MIG-024 (2026-09-28) | After an import, publish CAI and deploy DBMI over REST; MDM model deploy is still a click |
| L-MIG-068 | Objects authored headless in a shared org disappear within a day | 2026-09-23 to 2026-09-24 03:00Z | L-MIG-055 (2026-09-24) | Search by id, by exact type name and in other users' projects before declaring objects gone |
| L-MIG-069 | No cross-org export/import is available; promotion only re-points within one org | 2026-07-04 | L-MIG-045 (2026-09-29) | Use the v3 export and import across orgs, following the M0 to M13 runbook |
| L-MIG-070 | Export returns the zip synchronously; the /export/jobs and /import/jobs endpoints are the async form | 2026-07-04 | L-MIG-003 (2026-09-28) | Treat an export as a job: POST, poll `/export/<id>`, download `/export/<id>/package` |
| L-MIG-071 | The clone list stops at MDM objects and rule specs; with MI_TASK at 0 there is nothing to clone for ingestion | 2026-07-26 to 2026-09-22 | L-MIG-023 (2026-09-28) | Clone DBMI tasks and CAI processes too |
| L-CLEAN-028 | The headless delete surface is five DELETE endpoints; design objects have no headless delete | July 2026 to 2026-08-20 | L-CLEAN-006 (2026-09-28) | Delete with v2 DELETE (seven resources) and FRS (design objects), and read each delete back |
| L-CLEAN-029 | DELETE /public/core/v3/users/{id} returns 405; delete through the collection and recreate | 2026-07-25 to 2026-09-28 | L-CLEAN-009 (2026-09-28) | `DELETE /public/core/v3/users/<id>` works (204) |
| L-CLEAN-030 | An FRS delete is DELETE /frs/api/v1/Documents('<id>') | 2026-09-25 to 2026-09-26 | L-CLEAN-005 (2026-09-26) | Use `BaseEntities('<id>')`; `Documents('<id>')` gives 403 |
| L-CLEAN-031 | Agents, runtime environments, projects, MDM content and catalog sources have no headless delete | 2026-08-20 to 2026-09-28 | L-CLEAN-003 (2026-09-28) | Delete agents and runtime environments with v2 DELETE, folders and projects with FRS; catalog-source definitions still need the UI |
| L-CLEAN-032 | The catalog-source management prefix is not routed on some orgs, so catalog-source delete is UI-only | 2026-08-20 to 2026-09-28 | L-CLEAN-015 (2026-09-29) | Purge catalog sources over REST, then delete the definition in the UI |
| L-CLEAN-033 | DBMI tasks have no delete API; delete them in the Explore UI | 2026-09-25 to 2026-09-26 | L-CLEAN-005 (2026-09-26) | Stop and undeploy, then delete DBMI tasks with FRS `BaseEntities` |

## 11. IPU, metering and licensing (7)

Lessons file: [11 IPU, Metering & Licensing](by-domain/11-ipu-metering-licensing.md)

| Lesson | Old belief | Held | Overturned by | What to do now |
|---|---|---|---|---|
| L-IPU-045 | IPU metering needs an org-admin Consumption API entitlement; actuals are UI-only | 2026-07-04 (same day) | L-IPU-021 (2026-07-04) | Read consumption with the asynchronous `ExportMeteringData` job; no extra entitlement is needed |
| L-IPU-046 | Licensing and consumption have no API at all | until 2026-07-26 | L-IPU-021 (2026-07-26) | Read consumption through the export; only the licence inventory is UI-only |
| L-IPU-048 | Connectors draw from the IPU pool | until 2026-09-03 | L-IPU-006 (2026-09-03) | Size connectors by their tier licence, not in IPUs |
| L-IPU-049 | About ten IDMC capabilities are licence-blocked and must be purchased | 2026-07-04 to 2026-07-06 | L-IPU-031 (2026-07-06) | Read the ground truth before escalating a purchase: most "licence walls" were UI steps or wrong hosts |
| L-IPU-050 | The org has only Integration Cloud (CDI) because the login products list says so | until 2026-07-04 (and again 2026-09-21/22) | L-IPU-031 (2026-07-04) | Never read `products[]` as the entitlement set |
| L-IPU-051 | A sub-org showing one engine may need an entitlement purchase | 2026-07-26 (before the parent check) | L-IPU-034 (2026-07-26) | Check the parent org's allocation before raising a purchase |
| L-IPU-052 | CLAIRE GPT is genuinely absent: no agentic engine among the agent's engines | 2026-07-04 to 2026-07-09 | L-IPU-038 (2026-07-09) | Check `EffectiveLicenses()` and a live query: CLAIRE GPT needs no agent engine |

## 12. Claude working methods (8)

Lessons file: [12 Claude Working Methods](by-domain/12-claude-working-methods.md)

| Lesson | Old belief | Held | Overturned by | What to do now |
|---|---|---|---|---|
| L-METHOD-096 | Zero PUT is proven anywhere in IDMC; never design on PUT | 2026-07-25 to 2026-09-27 | L-METHOD-032 (2026-09-28) | PUT is proven on the selections route; keep the POST-to-id idiom for most v2 resources and probe other PUTs |
| L-METHOD-097 | A documented path that returns 404 means the capability is absent or unlicensed | to 2026-07-25 | L-METHOD-029 (2026-07-26) | Sweep the host family and apply the stopping rule before calling anything absent |
| L-METHOD-098 | IDMC lets you read almost everything, run almost everything and design almost nothing | 2026-07-13 to 2026-09-22 | L-METHOD-093 (2026-09-29) | Start from the capability map: most design is headless now; MDM model deploy, CDQ rule logic, classification accept and API activation remain |
| L-METHOD-099 | The session cache can assume a 30-minute idle timeout | 2026-06 to 2026-07 | L-METHOD-003 (2026-09-28) | Refresh the session cache by age (at most 25 minutes) |
| L-METHOD-100 | Claim protocol v1: a wip label plus a self-expiring claim comment | 2026-07-04 | L-METHOD-064 (2026-07-05) | Use one canonical lease format and a reaper that reads exactly that format |
| L-METHOD-101 | Clone-authored design objects do not persist in a shared org | 2026-09-23 to 2026-09-25 | L-METHOD-038 (2026-09-24) | Check the exact type name and other users' projects before calling clones gone |
| L-METHOD-102 | An org whose login lists only Integration Cloud has no catalog or CAI entitlement | 2026-09-21 to 2026-09-22 | L-METHOD-033 (2026-09-24) | Read selections and engines before calling an org unentitled |
| L-METHOD-103 | July open questions that must not be asserted to a customer | 2026-07-25 | L-METHOD-011, L-METHOD-035 (2026-09-28) | Re-probe the July open questions before asserting them; MDM read-by-id, CLAIRE GPT and the MCP registry have moved |

## 13. Environment and ops (3)

Lessons file: [13 Environment & Ops](by-domain/13-environment-ops.md)

| Lesson | Old belief | Held | Overturned by | What to do now |
|---|---|---|---|---|
| L-ENV-053 | Set MSYS_NO_PATHCONV=1, or run from cmd, for the bq and gcloud wrappers | 2026-07-04 | L-ENV-017 (2026-07-08) | Export `MSYS_NO_PATHCONV=1` only for the IDMC REST helpers, never globally |
| L-ENV-054 | Allowlisting the corporate proxy's /24 is a durable way to reach a VM | 2026-09-14 to 2026-09-21 | L-ENV-011 (2026-09-24) | Reach agent hosts through IAP hops or control-plane channels, not IP allowlists |
| L-ENV-055 | docker exec with a redirected script does nothing through run-command | to 2026-09-22 | L-ENV-004 (2026-09-23) | `docker exec -i ... < file` works through a managed run-command; debug the specific call |

## 14. UI automation (6)

Lessons file: [14 UI Automation](by-domain/14-ui-automation.md)

| Lesson | Old belief | Held | Overturned by | What to do now |
|---|---|---|---|---|
| L-UI-022 | Playwright is a screenshot tool for IDMC, not an automation path | 2026-07-10 | L-UI-021 (2026-08-19) | Playwright can author IDMC objects, but use it last: it is slow and fragile |
| L-UI-023 | The first mapping of a new source/target pair can only be authored by hand | to 2026-07-06 | L-UI-021 (2026-07-07) | Author a new connector pair's first mapping by IMF synthesis, or once by automation |
| L-UI-024 | Log in fresh in each script | 2026-07-06 to 2026-07-08 | L-UI-005 (2026-09-03) | Reuse a saved storage state inside its window, and refresh it with one login per batch |
| L-UI-025 | Enabling agent services and connectors needs the Administrator UI (a UI bot) | 2026-07 to 2026-09-22 | L-UI-001, L-UI-002 (2026-09-28) | Enable services with the selections PUT or MCP; retire the UI bot |
| L-UI-026 | CAI publish has to be driven through the designer UI | 2026-07-08 to 2026-07-24 | L-UI-001 (2026-07-25) | Publish CAI over REST on `<pod>-cai` |
| L-UI-027 | Chromium flags that disable Private Network Access are enough to automate the console behind the proxy | 2026-08-18 to 2026-09-13 | L-UI-011 (2026-09-20) | Run UI automation from a host outside the proxy |
---

## Still disputed: overturned neither way (18)

These lessons have dated records that disagree. None of them is a belief to quote, and none is settled enough to
overturn. Each row says what to do until someone settles it with a new dated probe.

| Lesson | Open question | The readings that disagree | What to do meanwhile |
|---|---|---|---|
| L-AUTH-075 | Is `GET /api/v2/auditlog` live? | 404 in one record; live on both orgs in another | use `GET /public/core/v3/securityLog` |
| L-CDGC-063 | Does the Classification Promotion job work headless? | 200 and a job id once, from a browser session; only Dismiss in another tenant | capture the request body from the browser and test it; meanwhile the auto-accept threshold is the lever |
| L-CDI-192 | Can a mapping task run through `POST /public/core/v3/jobs` with `taskFederatedId`? | one July report of 22 runs; no other source reproduces it | start jobs with `POST /api/v2/job` and the v2 `taskId` |
| L-CDI-193 | Can an advanced taskflow be published over REST? | API-made and copied ones fail; a designer-made shell is unsettled; one July report named no endpoint | build on linear taskflows or controller-staged runs |
| L-CDI-194 | Does `truncateTarget=true` truncate a PostgreSQL target? | "ignored" in one source; a wipe risk in another; no wipe observed | never set it on a system-of-record table; make postings idempotent in the database |
| L-CONN-043 | Does BigQuery V2 Simple mode reject JSON columns? | failures in July; JSON target columns filled by template tasks in September | test on your pod; STRING casts in the mapping are safe |
| L-CONN-048 | Does JDBC V2 pass a password to the database? | July: no password reached the database; August: tests passed only after one was set | read the database's own auth log; never trust a green test for the password |
| L-DBMI-035 | Which private-key form does the Simba driver accept? | the reports say escaped PEM; the script probably sent the plain PEM | probe the form on each pod; give DBMI its own connection |
| L-DQ-008 | Is `<pod>-dqcloud-api` mounted on every pod? | 404 (not mounted) in one record, 401 (a role gap) in another, on the same pod family | resolve the host by DNS and make one authenticated call first |
| L-DQ-034 | Must the profiling results store be Amazon S3 V2? | S3 V2 had to be enabled on one org; a later note says ADLS Gen2 or GCS also work | if a profile fails naming `amazons3`, enable S3 V2 first, then check the org's store |
| L-IPU-037 | Is the API developer portal a missing SKU? | an absent privilege and a 404 only | confirm in Administrator before escalating |
| L-IPU-040 | Is Database Ingestion priced as a floor plus 24x7 runtime? | a task title says so; the CPDS meters CDC per million rows and bulk per GB | size from the CPDS rates |
| L-MCP-011 | Is AI Agent Engineering entitled where the v3 census shows zero? | zero counts from an unvalidated filter; a 19-server registry on another org | read the org's registry on `hdm` |
| L-MCP-027 | Does MCP require the org's REST authentication switched to JWT? | a staff statement; the guide and working calls with session, JWT and OAuth | check the setting first; never flip it under a live workload |
| L-MDM-007 | Is the one manual model step a Save or a Publish? | a deployed entity showed no Publish; later write-ups describe a Modeler Publish | plan both, and prove the result with the ingest gate and a fake entity |
| L-MDM-021 | Does `GET .../entity/<runtimeId>/<id>` return the master record? | 200s in July; some of them were login HTML | check the Content-Type and body shape; use the search route for reads |
| L-MIG-060 | Can a cloned mapping be moved to another warehouse dialect by translating its SQL? | one report of 22 clones retargeted; other records say retargets reverted | swap a same-type connection GUID or re-import OVERWRITE; synthesize a mapping for a new adapter |
| L-UI-011 | Do IDMC consoles render under automation behind a transparent proxy? | blank under five configurations (2026-09-20); rendered and worked with the PNA and LNA flags off (2026-10-06) | try the L-UI-031 flag set first; fall back to a host outside the proxy |
