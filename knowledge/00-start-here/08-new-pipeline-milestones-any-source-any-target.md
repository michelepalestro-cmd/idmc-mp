# New Pipeline Milestones: any source, any target

**Answers:** I need a new data pipeline in IDMC. In what order do I work, what must be true before I move on, and how do
I use this KB when my source, target or connector is one the KB has never seen?

**Read when:** at the start of a new pipeline, before the first build command; again when a pipeline stalls and you
are not sure which milestone is really done. The milestones are a recommended order, not a requirement: skip, reorder
or go straight to one asset whenever the user wants to.

**Key rules:**
- **Never push the user to another technology.** Build on their systems; a system the KB has never covered is built
  brand new with the same milestones (Rule 1).
- **Never say "not possible" before the workaround ladder has been worked in this org** (Rule 2, eight rungs, from the
  lessons to a Python bridge to one residual click).
- The milestones are guidance: the user decides the order and the scope. When you follow them, each one ends on a
  **Done when** check that you read back from the org, never on a 200
  (L-METHOD-030).
- Your systems come from the user, not from this KB. Never swap in a source, target or connector the user did not ask
  for because the KB has more examples of it (see "Using this KB as guidance" below).
- Milestones 1-3 (runtime, connections, folder) cost nothing and decide whether everything after them works. Do them
  fully before you write a mapping.
- Runs cost jobs and IPUs. Milestones 0-6 are free; ask the user before milestone 7's first run (L-IPU-005).

**Related:** [End-to-End Playbook](07-end-to-end-playbook-deploy-and-operate-idmc-with-claude.md) (the same order for a
whole deployment) · [The Laws of Headless IDMC](02-the-laws-of-headless-idmc.md) ·
[Mapping Fast Path](../04-mappings/00-mapping-fast-path-read-this-first.md) ·
[Runtime Environments](../02-secure-agent/02-runtime-environments-services-connectors.md) ·
[Connections](../03-connections/01-connections-create-test-update-delete.md) ·
[Error Triage](04-error-triage.md)

**Last verified:** 2026-11-03.

---

## The goal and the two rules

**The goal:** help the user deploy IDMC end to end, with every IDMC capability they ask for, on the systems they
already have, by working through the milestones below.

**Rule 1. Never push the user to another technology.** Build on the user's source, target, cloud and tools. Most users
have neither the warehouse nor the SaaS apps in this KB's examples, and they do not need them. A connector, database or
file system the KB has never covered (SAP, Oracle, a mainframe file, an FTP drop, a REST API, anything) is built brand
new with everything the KB has learned: the same milestones, the same gates, the same evidence habits. Never suggest
"use BigQuery / Snowflake / X instead", and never fall back to a system the user did not name.

**Rule 2. Never say "not possible" until every path has been tried.** A "no" is allowed only after the workaround
ladder below has been worked and every rung failed with evidence in **this** org. Even then, say what was tried, give
the nearest path that does work on the user's own systems, and name the one manual step (if any) that remains. "The KB
does not cover it" and "a lesson says it failed once" are never a no: they are the start of the work.

**The KB is not an allow-list.** Nothing is forbidden, unsupported or impossible because this KB does not mention it.
A connector, transformation, file format or pattern that is missing here is simply not recorded yet: anything IDMC
can do is in scope. Take the closest pattern the KB does have, adapt it, and prove it in the user's org.

**Native IDMC first; Python only when IDMC cannot.** Look for the IDMC way first (a connector, a transformation, a
task type, CAI, CDQ, Mass Ingestion, a clone of a UI-made object). Use Python only when no IDMC path works, and then
as a small bridge into IDMC, never as a replacement for it.

### Before you tell anyone no: the workaround ladder

Work it top to bottom; stop at the first rung that works, and record it as a lesson. Rungs 1-6 stay inside IDMC;
rung 7 (Python) is only for when none of them works.

| # | Rung | How | KB |
|---|---|---|---|
| 1 | Search the evidence | `grep -ril "<thing>" "lessons"`, the [Capability Map](03-capability-map.md), [Overturned Beliefs](../../lessons/overturned-beliefs.md). A wall is a dated verdict; many walls were later overturned | Law 9 |
| 2 | Re-probe in this org | the right host and header for the plane, a bogus twin, the item status inside a 200; another release or org may differ | Laws 2-8 |
| 3 | Another plane or API version | v2, v3, FRS, the service's own host (`-ing`, CAI, catalog, MDM), managed MCP | Laws 2, 22 |
| 4 | Clone instead of create | have the object made once in the UI (or find one), export it as a v3 package, edit and re-import it; that is how mappings, mapplets, taskflows, CAI processes and DQ assets are built headless. Example: profiling a database over JDBC V2 was recorded as blocked, then worked by cloning a working profile body (L-DQ-128) | Law 16, [Editing Packages Safely](../12-deploy-migrate/02-editing-packages-safely.md) |
| 5 | Capture the UI's own call | record the browser's request (HAR / Playwright) and replay it with the session header | Law 19, [UI Automation](../14-working-with-claude/04-ui-automation-with-playwright.md) §8 |
| 6 | Another IDMC component | no native connector: REST V2 / a generic JDBC or ODBC connector, a CAI process calling the system's API, a flat file staged where a file connection reads it; a missing transformation: an expression pattern, a mapplet, a SQL query in the source, a second mapping | [Capability Map](03-capability-map.md), [Mapping Fast Path](../04-mappings/00-mapping-fast-path-read-this-first.md) §7 |
| 7 | A Python bridge (only when rungs 1-6 found no IDMC path) | a small script on the agent host as a pre/post step, or a stand-in that fetches, converts or stages data for an IDMC connector, while the integration logic itself stays in IDMC | [Script Library](../../toolkit/lib/README.md) |
| 8 | One residual click | the single step that truly has no API, done once by the user from a written instruction, with everything before and after it headless | Law 17 |

Only when all eight rungs fail is the answer "not possible today", stated with the evidence of each rung, the date,
and the nearest working path on the user's own systems.

### Worked example: a flat-file target the KB had not documented

A user asked for a passthrough from a flat file to a new flat file. The KB then described flat files only as a
**source**, so a session found no evidence for a file target and fell back to a warehouse the user never asked for.
That broke both rules. The right process took a few minutes and stayed inside IDMC:
1. Rung 1: the lessons and the generator docs covered flat-file sources only. That is a gap, not a no.
2. Rung 2: build the simplest spec on the user's own connection (flat-file source → flat-file target, the target
   fields = the source fields, nothing to browse because the file does not exist yet), lint it, dry run, deploy, run.
3. Result: IDMC wrote the file natively, 189 of 189 rows; the first run creates it and every later run overwrites it.
   No Python and no other system was needed.
4. Record it: a lesson (L-CDI-274), the connector row in the Mapping Fast Path, an example spec
   (`toolkit/mapgen/examples/probes/m_probe_ff_target.json`), so the next reader finds it on rung 1.

### A system or connector the KB has never seen (SAP, Oracle, an FTP drop, a REST API: anything IDMC connects to)

Run the same milestones; only the connector-specific facts are new, and you collect them as you go. Three things to
know up front:
- **Find what the KB already holds on it:** `grep -ril "<connector>" .` across the whole KB, including the vendor
  connector guides in `knowledge/reference` and the runtime-selection tables in `knowledge/02-secure-agent`.
  A connector named only there is still covered by the same method.
- **Expect up to one UI step the first time** a connector type is used in an org: creating its first connection, or
  one exemplar mapping to export (L-CONN-005, rung 4). Tell the user at the start; everything after it is headless.
- **SAP, as an example:** IDMC has several SAP connectors with different jobs. For batch reads into a mapping, use the
  table- or extractor-type SAP connectors your org lists (names vary by release; check `GET /api/v2/connector` and
  their guides); the BAPI and IDoc connectors are for application integration (CAI). Most need SAP's client
  libraries on the Secure Agent host and SAP-side authorizations for the integration user.

1. **Runtime (M1):** find the connector in the org (`GET /api/v2/connector`, filter on its name) and read its guide for
   what the Secure Agent needs (many enterprise connectors, SAP's among them, need the vendor's client libraries on
   the agent host, so plan a Secure Agent rather than the Hosted Agent). Enable it on the runtime and read it back RUNNING.
2. **Connection (M2):** read the connector's definition for its `connParams`, or export one connection made in the UI,
   then create, test and prove it with a small read of rows.
3. **Folder and assets (M3):** the same as for any pipeline.
4. **Contract and mapping (M4-M5):** read the object list and fields from the connector's own metadata calls; build the
   simplest passthrough first. If the generator has no template for the connector, use the exemplar route (Fast Path
   §7.0): an existing or UI-made mapping with it, exported and read with `toolkit/mapgen/exemplar.py` (rung 4).
5. **Run and prove (M7)**, then add the transformations, DQ and orchestration the user asked for.
6. Record every setting that worked as a lesson, so the next user of that connector starts further ahead.

## Using this KB as guidance, not as a script

This KB was written from real IDMC builds. Those builds happened to use certain systems: PostgreSQL, BigQuery,
Snowflake, Databricks, Salesforce, SharePoint, ClickHouse over JDBC V2, Tableau, flat files. **Those are examples, not
recommendations.** IDMC has hundreds of connectors, and your pipeline can start and end anywhere IDMC can connect.

| Take from the KB | Do not take from the KB |
|---|---|
| The order of work and the gates (this page, the Playbook) | The choice of source, target, cloud or warehouse |
| How IDMC behaves: endpoints, bodies, error codes, timings, walls and workarounds | A connector because it has the most examples |
| The method for an unknown connector (milestone 2 and 5 below) | An example's object names, field lists or load mode as-is |
| The safety rules: one login, prove the org, dry run first, read back every write | An id, host or setting from an example, unchanged |

When your system is not in the KB:
1. Say so plainly to the user: "the KB has no notes on `<connector>`; I will find its settings in the org and prove
   them". Do not route to a system the KB knows better.
2. Read the connector's own definition from the org (`GET /api/v2/connector`, then the connector's metadata) and its
   Informatica guide; build one small object and prove it with rows.
3. If the generator or a recipe does not know the connector, have one example made once in the UI, export it, and copy
   its shape (L-CDI-036, L-CDI-204; [Mapping Fast Path](../04-mappings/00-mapping-fast-path-read-this-first.md) §7).
4. Record what you proved as a new lesson (generic, dated) so the next pipeline starts further ahead.

Lessons are dated evidence from particular orgs and releases. Your own org's live answer wins over any lesson; when they
disagree, re-probe and write down the newer result (L-METHOD-034, L-METHOD-035).

---

## Milestone map

| # | Milestone | Done when | Cost |
|---|---|---|---|
| 0 | Write the pipeline down | one line: source(s) → IDMC work → target(s), freshness, volume, load mode; the user agrees | free |
| 1 | Identify the runtime: Secure Agent or Hosted Agent | the runtime environment is up, and the services and connectors both ends need are RUNNING on it | free |
| 2 | Identify the connections | one connection per system, tested from that runtime environment, and a small read returns rows | free (a test is a metadata handshake) |
| 3 | Identify or create the project and folder, and list its assets | the folder id is read back, names follow one prefix, and the asset list is written down | free |
| 4 | Declare the data contract | every field, type, precision and key written from the systems' own catalogs | free |
| 5 | Build the mapping(s) | lint clean, dry run read, imported, the mapping reads back valid in the folder | free |
| 6 | Create the mapping task | the task is in the folder, bound to the runtime from milestone 1 | free |
| 7 | First run and proof | a run with your runId ended in success, target counts and a two-way diff match the source | **jobs + IPUs: ask first** |
| 8 | Data quality (if in scope) | rules run inside the pipeline and their results are read back per row | runs: ask first |
| 9 | Orchestrate and schedule | a taskflow or schedule runs the tasks in order, inside the job budget | every run counts |
| 10 | Govern and hand over | catalog scope covers the folder, lineage shows source → target, a runbook and the new lessons are written | scans: ask first |

---

## Milestone 0. Write the pipeline down

Before any call, write the brief in one line and confirm it with the user:

`<source system(s)>` → `<what IDMC does: copy, cleanse, join, master, verify, mask>` → `<target system(s)>`, freshness
(seconds, minutes, nightly), rough volume, load mode (full reload, upsert on a key, incremental by watermark), and who
reads the output.

- The systems in the brief are the user's. If the user has not named one, ask; do not fill the gap from an example.
- Freshness picks the mechanism: CDC for seconds, event-driven CDI lanes for minutes, CAI for per-event calls, batch CDI
  for the rest (L-CDI-126, L-CDI-206).
- Prove the org you will build in (`python3 toolkit/check_login.py`) and keep to one org per session (L-AUTH-046, L-AUTH-047).

**Done when:** the brief is written, the user has agreed it, and the org is proven.

## Milestone 1. Identify the runtime: Secure Agent or Hosted Agent

Every task runs on a runtime environment. Pick it first, because it decides which connectors and transformations are
available.

| Your data lives | Runtime | Watch for |
|---|---|---|
| SaaS or cloud endpoints the connector reaches from Informatica's cloud | Informatica Cloud Hosted Agent (nothing to install) | some transformations and connectors need a Secure Agent: document parsing, profiling, CDQ cleanse / deduplicate / decision, some file and BI writers (L-AGENT-103, L-CDI-279). It is a shared platform runtime: if it goes down, every hosted connection fails with APP_105060; keep a Secure Agent to fail over to (L-AGENT-117, L-ENV-100) |
| A private network, a VM-hosted database, on premises, local files | a Secure Agent on a host you own | size it for the services you will enable (L-AGENT-052, L-AGENT-093) |
| Your own cloud account, no agent wanted | Serverless (set up in the UI) | it reaches only that account |

Steps:
1. List what exists: `GET /api/v2/runtimeEnvironment` and `GET /api/v2/agent` (L-AGENT-020). An empty agent list means
   entitlement is unresolved, not absent (L-AGENT-032).
2. For a Secure Agent: `GET /api/v2/agent/details/<agentId>` and check that every engine you need reads RUNNING
   (L-AGENT-024).
3. Check that the connector package for **both** ends is on that runtime. The org's connector catalog
   (`GET /api/v2/connector`) is a type list, not proof that the agent can run it (L-CONN-021). Enable missing services
   and connectors through the runtime-environment selections (L-AGENT-039), between runs, never just before a timed one
   (L-AGENT-041).
4. Note the runtime's name and id in your private run notes; the mapping task and any lookup connections must use one
   that is up.

**Done when:** the runtime environment is up, the services and connectors both ends need read RUNNING on it, and you
know which tasks (if any) must run on a different runtime.

## Milestone 2. Identify the connections

1. Look for existing ones first: `GET /api/v2/connection` and match by name and type (L-CONN-016). Reuse a connection
   only when it points at the right system and account.
2. To create one: most connectors are `POST /api/v2/connection` with `type: "TOOLKIT_CCI"`, the connector's display name
   in `instanceName` and its settings in `connParams` (L-CONN-001). Some connectors differ (for example a `TOOLKIT`
   type, L-CONN-128): read the connector's definition, or export one connection made in the UI, before you guess.
3. A create that answers 200 proves only that the type exists in the catalog. Test it:
   `GET /api/v2/connection/test/<connId>` is a free metadata handshake (L-CONN-014). Test from the runtime environment
   the tasks will use: a connection carries its own runtime environment, and a lookup reaches its connection through
   it, not through the task's (L-CONN-132).
4. Prove it with data: a small read that returns rows. An empty browse proves nothing (L-CONN-015, L-CONN-016).
5. Updates re-supply the secret (L-CONN-007). Secrets are read at run time and printed by name only (law 30).

**Done when:** every system in the brief has one connection, each tests green from the right runtime environment, and a
small read returns the rows you expect.

## Milestone 3. Identify or create the project and folder, and list its assets

Projects and folders hold the design and run objects of the pipeline. Some objects live in the org, not in a folder.

| Lives in your project / folder | Lives in the org (not in a folder) |
|---|---|
| mappings (`DTEMPLATE`), mapplets (`MAPPLET` / `DMAPPLET`) | connections |
| mapping tasks (`MTT`), linear taskflows (`WORKFLOW`), taskflows (`TASKFLOW`) | runtime environments and Secure Agents |
| DQ assets: rule specifications (`RULE_SPECIFICATION`), dictionaries, cleanse and verifier assets | schedules |
| data profiles (`PROFILE`) | users, groups, roles |
| CAI processes, app connections and service connectors (`PROCESS`, `AI_CONNECTION`, `AI_SERVICE_CONNECTOR`) | catalog sources (in the catalog service) |
| Database Ingestion tasks (`DBMI_TASK`, created in a project, then moved) | |

Steps:
1. Find or create the project and folder over v3 and cache their ids: `GET /public/core/v3/objects?q=type=='PROJECT'`,
   `POST /public/core/v3/projects`, then the folder under it (L-CDI-055). A dot in the name is refused with 400: create
   it with `_` and rename through FRS (L-MIG-078, L-MIG-079). Mapping-task names refuse parentheses (APP_13500,
   L-CDI-280). For view-only walk-through copies of assets, use FRS `CopyEntities` (L-MIG-087).
2. Write the asset list for the pipeline before building: which mappings, tasks, taskflow, DQ assets and processes, one
   name prefix for all of them, and which existing assets you will reuse.
3. New v2 tasks are created in `Default`. Move them into your folder with FRS `MoveEntities`; ids, schedules and run
   history survive (L-CDI-016, L-MIG-054). A task left in `Default` falls outside a catalog source that filters on your
   project, and its mapping drops out of lineage (L-CDGC-157).
4. Tag the assets in batches of 50 if your org uses tags; projects and folders cannot be tagged, and imports drop tags
   (L-CDI-054, L-METHOD-086).
5. If only some users may see this pipeline, plan the role and object permissions now (L-AUTH-091).

**Done when:** the project and folder ids are read back, the asset list and name prefix are written down, and nothing
of this pipeline will stay in `Default`.

## Milestone 4. Declare the data contract

1. Read the fields from each system's own catalog (`INFORMATION_SCHEMA`, a describe call, the file header) right before
   the build, not from connection field browse (L-CONN-096, L-CDI-197).
2. Write each field with its type, precision and scale as the target connector wants them. Each connector has its own
   native types and quirks: look for its row in the [Mapping Fast Path](../04-mappings/00-mapping-fast-path-read-this-first.md) §2,
   and when it has none, take them from the connector's metadata in your org.
3. Decide the keys and the load mode: full reload, upsert on a key, or incremental by a watermark.

**Done when:** the contract is written for every source and target field, with keys and the load mode.

## Milestone 5. Build the mapping(s)

1. Pick the route: a template task for a straight copy, the generator in `toolkit/mapgen` for real transformations
   (L-CDI-033; [How Claude Builds Mappings Headless](../04-mappings/02-how-claude-builds-mappings-headless.md) §1).
2. Follow the [Mapping Fast Path](../04-mappings/00-mapping-fast-path-read-this-first.md): start from the example
   closest in **shape** (passthrough, join, aggregate, upsert, incremental), then change the connections, objects and
   fields to yours. The example's systems do not matter; its shape does.
3. A source or target with no template in the generator (no row in the Fast Path §2): the **exemplar route** (Fast
   Path §7.0): an existing or UI-made mapping that uses it, exported and read with `toolkit/mapgen/exemplar.py`.
4. Set every connection's `kind` explicitly in the generator profile. A connection with no `kind` is treated as
   BigQuery; lint warns about it.
5. Few mappings: group by stage rather than one mapping per table (L-CDI-119).
6. Lint, dry run, deploy. Read back that the mapping is in your folder and valid.

**Done when:** lint has no errors, the import succeeded, and the mapping reads back in your folder.

## Milestone 6. Create the mapping task

1. Create the task over the mapping with the runtime environment from milestone 1 (L-CDI-037); the generator's
   `deploy` does this and moves it into the folder.
2. Lookups and other connections inside the mapping also need a runtime that is up: check every connection the task
   touches, not only the source and target (L-CONN-132).

**Done when:** the task reads back in your folder, bound to the right runtime environment.

## Milestone 7. First run and proof

Ask the user before the first run: it is a job and uses IPUs.

1. Run, then poll the activity log for **your** `runId` until it has an end time and success (L-CDI-059). Read the
   `*Utc` times (L-AUTH-094).
2. On a failure, read the first `[ERROR]` line of the session log, then [Error Triage](04-error-triage.md) and
   `grep -ril "<error>" "lessons"`.
3. Prove the output: target row count against the source, a two-way diff of 0, and a second run that changes nothing
   when the source did not change. For a large table, compare an order-free checksum per unit inside IDMC (L-MIG-086).
4. Retry only what can succeed on retry: transport and capacity errors yes, data and permission errors no (L-CDI-287).
   The activity log is not a complete run history, so keep your own run ledger (L-CDI-288).

**Done when:** the run succeeded, the counts and diff match, and the second run is idempotent.

## Milestone 8. Data quality (if in scope)

Rules run inside the pipeline as rule-specification transformations or DQ assets; profiling measures them. Copy each
rule's input precision and scale, or the mapping turns invalid (L-DQ-113). Read the results back per row, not only a
pass flag ([DQ Assets](../08-data-quality/01-dq-assets-rule-specs-cleanse-dictionaries-verifiers.md)).

**Done when:** each rule's result is visible per row in the target and the scores are read back.

## Milestone 9. Orchestrate and schedule

1. Chain the tasks: linear taskflows are fully headless; an advanced taskflow made by API imports but cannot be
   published headless (L-CDI-070; [Taskflows & Schedules](../05-taskflows-schedules/01-taskflows-schedules.md)).
2. Poll a taskflow with its taskId and runId (L-CDI-252).
3. Count the jobs a schedule will start per month against the org's job budget, and keep a ledger from the first lane
   (L-IPU-041, L-IPU-043).

**Done when:** one scheduled or triggered run completes all tasks in order, and the monthly job count is known.

## Milestone 10. Govern and hand over

1. Make sure the catalog source's scope includes your project and folder (and that no task stayed in `Default`), then
   check lineage from source to target: every root should be the system of record and nothing unexpected should join
   in (L-CDGC-157, L-CDGC-229, L-CDGC-232;
   [Catalog Sources](../09-catalog-lineage/02-catalog-sources-create-scan-update-purge.md)).
2. Write a short runbook: what runs, when, on which runtime, how to re-run, how to roll back.
3. Add every new fact you proved as a generic lesson in `lessons`, especially for a connector the KB did
   not cover.

**Done when:** lineage shows the pipeline, the runbook exists, and the lessons are written.
