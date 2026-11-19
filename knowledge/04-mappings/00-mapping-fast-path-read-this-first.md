# Mapping Fast Path (read this first)

**Answers:** How to build, deploy, run and check a CDI mapping headless in about ten commands, with the exact spec settings
per connector proven so far (Snowflake, Databricks, Salesforce, SharePoint Online, BigQuery, PostgreSQL, JDBC, flat file, Fabric:
examples, not recommendations), how to handle a connector that is not listed, where writer attributes go, which runtime environment to pick, and the errors that cost the most time.

**Read when:** before you build or change ANY mapping or mapping task. Read this page, open the one example spec it points
to, and only open the long docs when a row here says so.

**Key rules:**
- Build with the user's own source and target. The connectors below are the ones proven so far, in no order of
  preference; never switch a user to one of them because it has more examples (knowledge/00-start-here / 08 New Pipeline
  Milestones).
- Set `kind` on every connection in the profile: a connection with no `kind` is treated as BigQuery (lint warns
  `CONN_KIND_MISSING`).
- A source, target or transformation with no template here: the exemplar route (§7.0): an existing or UI-made
  mapping that uses it, exported and read with `toolkit/mapgen/exemplar.py`, then the template added to the package.
- One route by default: the generator in `toolkit/mapgen` (spec → lint → package → v3 import → mapping task → run). Never
  `POST /api/v2/mapping` or v3 `objects` (not create surfaces; L-CDI-020).
- Start from the closest example spec in `toolkit/mapgen/examples/`, never from a blank file. The full option list is
  `toolkit/mapgen/docs/SPEC_REFERENCE.md`.
- Declare every field in the spec, from the database's own catalog, right before the build. Do not rely on connection
  field browse (L-CONN-096, L-CDI-197).
- Writer settings on most connectors go in the target's `writerAttrs` (`opr` = internal names, `rt` = display names).
  The transformation's own Pre/Post SQL and the truncate flag are ignored by several writers (§3).
- A rebuild is an OVERWRITE import under the same mapping id. POSTing new target values to the task is a silent no-op
  (L-CDI-050, L-CDI-145).
- Read back every write. A run counts only when the activity-log row has YOUR `runId`, an `endTime` and state 1
  (L-CDI-059).

**Related:** [How Claude Builds Mappings Headless](02-how-claude-builds-mappings-headless.md) (all five routes, history)
· [Mapping Tasks](03-mapping-tasks-create-update-run-monitor.md) · [Taskflows & Schedules](../05-taskflows-schedules/01-taskflows-schedules.md)
· [Source & Target Gotchas](08-source-target-gotchas.md) · [Connections](../03-connections/01-connections-create-test-update-delete.md)
· [Lessons: CDI](lessons.md) · [Lessons: Connections](../03-connections/lessons.md)

**Last verified:** 2026-11-03.

---

## 1. The ten commands

Run them from the plugin root. Every command except `run` is free. `run` starts a job that counts against the org's job
budget and IPUs, so ask the user before you run.

| # | Do | Command / detail |
|---|---|---|
| 1 | Prove the org | `python3 toolkit/check_login.py`. One login, one attempt: a few rejected logins lock the account (IDS_086) |
| 2 | Make a profile | Copy `toolkit/mapgen/profile.example.json` to your own `profile.json` (keep it out of shares). Fill `org`, `runtimeEnvironment.name`, `folder.project` / `folder.name`, and one entry per connection: `{"name": "<connection name>", "kind": "<kind>"}` (§2 gives the kind). Salesforce also needs `"typeSystem": "Salesforce"`. The example profile has BQ, PG, SF, SNOW, DBX and FF entries as examples: delete the ones you don't use, add your own connector under any label, and set `kind` on every entry. Until `resolve` runs, give each connection its own placeholder guid and id, because two equal placeholders fail lint (`SPEC_SHAPE`) |
| 3 | Fill the ids | `python toolkit/mapgen/mapgen.py --profile profile.json resolve --write` looks up every GUID, v2 id and runtime id from the names |
| 4 | Pick an example | §4 lists which example shows which pattern. Copy it, rename `name` / `taskName`, keep the shape |
| 5 | Declare the fields | Query the source and target catalogs (`INFORMATION_SCHEMA`, Salesforce describe) and write each field as `[name, TYPE, precision, nativeType, scale]` (§2 gives the native types) |
| 6 | Lint | `python toolkit/mapgen/mapgen.py --profile profile.json lint <spec>.json`. Fix every ERROR. `WARN CONN_KIND ... Known kinds: BQ, PG, JDBC, FF, SF` is expected for every other connector (Snowflake, Databricks, SharePoint, Oracle, SQL Server...: they use the generic TOOLKIT adapter). `WARN CONN_KIND_MISSING` is not: set the connection's `kind` |
| 7 | Dry run | `... deploy <spec>.json` (a dry run by default) prints what it would import and create |
| 8 | Deploy | `... deploy <spec>.json --execute --expect-org <orgIdV3>`: build → package → v3 import (REUSE for a new mapping; it finds an existing mapping by name in the folder and rebuilds it under that id, OVERWRITE) → create or reuse the mapping task `taskName`, born in `Default`, moved into the folder. Protected folders and targets in the profile's `guards` are refused unless `--allow-live` |
| 9 | Run | `... deploy <spec>.json --run --execute --expect-org <orgIdV3>`, or `... run "<task name>" --folder "<project>/<folder>" --execute --expect-org <orgIdV3>`. It polls the activity log for this run's `runId` and prints per-target rows |
| 10 | Prove the output | Count rows in the target and compare with the source or the old pipeline (two-way diff = 0). On a failure: `... log <task>` and read the FIRST `[ERROR]` line (§5) |

A taskflow over several tasks: [04 Taskflows & Schedules](../05-taskflows-schedules/01-taskflows-schedules.md). Linear taskflows are headless;
publishing an API-made advanced taskflow is not (L-CDI-070). Poll a taskflow run with taskId AND runId, because child entries
carry their own runIds (L-CDI-252); starting one that is still running answers REPO_17315 (L-CDI-253). Read the `*Utc`
times, never the local ones (L-AUTH-094).

## 2. Connector settings that work in a generated mapping

The connectors proven so far, in no order of preference. **Your connector is not in the table?** Do not substitute
one that is: use the exemplar route (§7.0), which learns the settings from one mapping that already uses it. Or, for
a simple connector, try the generic path first. It still works through
the generic path: give it any `kind` label, take its object path, native types and writer attributes from the
connector's metadata in your org (or export one mapping made in the UI with it, §7), prove it with one small passthrough
run, and record the settings as a lesson.

| Connector (profile `kind`) | Object path in the spec | Native types | Full reload | Must know |
|---|---|---|---|---|
| **Snowflake Data Cloud** (any label, e.g. `SNOW`) | `<DATABASE>/<SCHEMA>/<TABLE>`; a view: add `"objkind": "VIEW"` | lower case: `varchar` (STRING, always with a length), `number` (NUMERIC p, s, or INTEGER 19, scale 0), `date`, `boolean`, `timestampntz` (TIMESTAMP with precision `null` = the default; `timestamp_ntz` is refused at session start) | `writerAttrs: {"opr": {"presql": "TRUNCATE TABLE <db>.<schema>.<t>"}, "rt": {"Pre SQL": "<same>"}}`; the truncate flag and the transformation's Pre SQL are ignored (L-CONN-106) | Post SQL only from `postsql` (L-CONN-094). Give every target VARCHAR a length or the writer runs out of memory (L-CDI-227). A NUMBER read into a lookup port must be decimal(19,0), not bigint ('BigDecimal cannot be cast to java.lang.Long'; L-CONN-095). Key-pair auth needs the key file on the agent host (L-CONN-092); on the Hosted Agent use a Programmatic Access Token connection (L-CONN-118) |
| **Databricks** (any label, e.g. `DBX`) | `<schema>/<table>` | `string`, `decimal` (with scale), `bigint`, `timestamp` | `writerAttrs: {"opr": {"writeDisposition": "Truncate"}, "rt": {"writeDisposition": "Truncate"}}`; the truncate flag, Pre SQL and create-at-runtime all append (L-CDI-248) | Connection: TOOLKIT_CCI 'Databricks Delta' with a SQL-warehouse JDBC URL (L-CONN-119); put the personal access token in BOTH `dbToken` and `PersonalAccessToken`, or Test Connection fails 'access token has expired' (L-CONN-120). A source `query` is sent verbatim, so Unity Catalog `MEASURE()` works (L-CDI-249) |
| **Salesforce** (`SF`, profile `"typeSystem": "Salesforce"`) | the object API name (`Account`, `ContentVersion`, `<Object>__c`); source: `"sfObject": true` | Salesforce's own, each with a base type: `id` → STRING 18; `string`, `picklist`, `reference` → STRING (the field's length; 255 is typical); `currency` → NUMERIC 18, scale 2; `int` → INTEGER 10; `datetime` → TIMESTAMP 24, scale 0; `date` precision 10 (L-CDI-254); `base64` → STRING up to 7340032. Take real lengths from the IDMC field metadata | n/a (source) / Upsert on an external id (target, L-CDI-090) | SOQL WHERE in the source's `filter` (`IsLatest = true`); keep it a literal list, because the catalog cannot parse a sub-query and drops the source from lineage (L-CDI-245). Two Salesforce sources in one Joiner collide; use separate flows (L-CONN-108). The integration user needs field-level security on every field |
| **SharePoint Online** (any label, e.g. `SP`) | the list or library name (`Documents`) | `string` | n/a | Write a file = INSERT a row with `ServerRelativeUrl` (folder) + `Name` (file). The bytes are read from the connection's `Attachment_File_Path` on the agent host, so stage them there first, on a Secure Agent: the field is mandatory even to test, and the Hosted Agent cannot move files with it (L-CONN-125). No agent at all: upload over Microsoft Graph from a CAI process (L-CAI-149). A name that exists fails, so version names upstream (L-CONN-107). 'Operation failed: Documents is not found' = a Graph-scoped refresh token (L-CONN-126). Create the connection with type TOOLKIT, not TOOLKIT_CCI (L-CONN-128); the refresh token must carry SharePoint scopes, not Graph (L-CONN-100, L-CONN-111) |
| **BigQuery** (`BQ`) | `<dataset>/<table>` or a `query` | STRING, INTEGER, NUMERIC, FLOAT, TIMESTAMP, DATE, BOOLEAN | `truncate: true` (the generator writes `writeDisposition` into `oprRuntimeAttributes`; L-CDI-038) | At most about 5 BigQuery readers per mapping (L-CDI-129). A DATE target wants a STRING `'YYYY-MM-DD 00:00:00'` (L-CDI-159). The generator adds the 1 s job poll (L-CDI-200) |
| **PostgreSQL** (`PG`) / **JDBC V2** (`JDBC`) | `<schema>/<table>` (rewritten to `<schema>/TABLE/<table>`; views `"objkind": "VIEW"`) | PG native `bigint` (not `int8`, L-CDI-255), `varchar`, `numeric`, `timestamp` | PG `truncate: true` (the generator writes `TruncateTable = YES`); JDBC: `rt` `Pre SQL` (L-CDI-171) | PG Upsert gets `UpdateMode = Update Else Insert` from the generator; still test new-key inserts (L-CDI-207). JDBC writes into the database bound on its connection (L-CDI-040) |
| **Tableau V3** (target, any label) | a `.hyper` file name, with the project and data source in both attribute sets | Tableau's own | Overwrite | Secure Agent only, not the Hosted Agent (L-CONN-116); full recipe and the three failure errors in L-CDI-251; NUMERIC above precision 18 → DOUBLE (L-CONN-121); the writer prints its REST token in the session log (L-AUTH-093) |
| **Flat file** (`FF`) | the file name (in the connection's directory on the agent) | `string` | target: every run overwrites the file (one header, no append) | Source and **target** both work. A target file that does not exist yet is created by the first run, with or without `createTarget`: declare its fields in the spec (= the upstream fields); there is nothing to browse before the first run, so do not look it up. Values are written double-quoted, with a header. The generator's flat-file format is comma, `"` and a header on line 1; for another delimiter, no header or another qualifier, set the format with the node's `set` / `advanced` escape hatch (SPEC_REFERENCE §6) or copy it from one exported UI-made mapping. Proven FF → FF 189/189 rows (2026-11-03, `probes/m_probe_ff_target.json`, L-CDI-274). Flat-file lookups are not supported by the generator |
| **Microsoft Fabric DW / Lakehouse / OneLake** | not yet generated by mapgen | — | — | The connection needs `StagingLakehouseName` before any run (L-CONN-071). Harvest one exported Fabric mapping as the exemplar, then add its shape to the generic path (§6) |

## 3. Where target settings go

| Setting | Spec key | Lands in | Lesson |
|---|---|---|---|
| Operation | `op`: `Insert`, `Update`, `Upsert`, `Delete`, `Data Driven` + `updateColumns` (keys) | target transformation | SPEC_REFERENCE §5.1 |
| Snowflake / Databricks / JDBC writer options | `writerAttrs.opr` (internal name) and `writerAttrs.rt` (display name), always both | `oprRuntimeAttributes` / `runtimeAttributes` | L-CONN-094, L-CONN-106 |
| BigQuery write mode | `truncate`, `disposition` | `oprRuntimeAttributes.writeDisposition` (`WriteOptions.truncate` alone is ignored) | L-CDI-038 |
| Pre/Post SQL on BigQuery and PostgreSQL | `pre_sql` / `post_sql` | the writer attributes those writers run | SPEC_REFERENCE §5.1 |
| Load order of several targets | top-level `flowOrder` | the mapping | SPEC_REFERENCE §1 |

A Pre SQL TRUNCATE runs before the source is read: a failed read leaves the target empty (L-CDI-208).

## 4. Which example to copy (`toolkit/mapgen/examples/`)

| You need | Example |
|---|---|
| Salesforce → Snowflake, full reload, load timestamp (the simplest real shape) | `connectors/m_ex_sf_accounts_to_snowflake.json` |
| Salesforce → aggregate → Databricks, full reload | `connectors/m_ex_sf_orders_to_databricks.json` |
| Flat file → flat file, target file created at run time | `probes/m_probe_ff_target.json` |
| Clean, standardize, route valid/invalid, mask | `retail/m_ex_customer_cleanse.json` |
| Join + aggregate + lookup | `retail/m_ex_order_enrichment.json`, `retail/m_ex_customer_value.json` |
| Union of several sources | `retail/m_ex_returns_unified.json` |
| Full-outer reconciliation | `retail/m_ex_order_return_recon.json` |
| Self-join on one source (sorted input) | `retail/m_ex_order_share_selfjoin.json` |
| Slowly changing dimension type 2 | `retail/m_ex_price_scd2.json`, `combos/m_ex_combo_scd2.json` |
| Incremental load with a high-water mark (in-out parameter) | `combos/m_ex_combo_watermark.json`, `probes/m_probe_params.json` |
| Several independent flows in one mapping | `retail/m_ex_store_ops_multiflow.json` |
| Update / Upsert / Delete / Data Driven targets | `probes/m_probe_ops_pg.json`, `probes/m_probe_ops_bq.json` |
| Mapplet | `probes/mplt_ex_clean_names.json`, `probes/m_probe_mapplet.json` |
| Normalizer | `probes/m_probe_normalizer.json` (generated Normalizers with occurring fields can fail at DTM load, L-CDI-236) |
| Remove duplicates by a key (keep one row per key) | a `rank` node with `n: 1`, `groupBy: [<key>]` and `by: <survivor column>` (shape in `retail/m_ex_customer_value.json`), or a `sorter` with `distinct: true`: plain CDI, any runtime. Fuzzy matching (the same entity under different keys) is the `dedup` node over a CDQ Deduplicate asset, on a Secure Agent (L-CDI-279, L-DQ-127) |
| Data quality rule as a transformation | `rulespec` node: list the rule in `assets`, copy the rule's input precision AND scale (`[["Amount", "NUMERIC", 18, 4]]`), or the designer marks the mapping Invalid (L-DQ-113) |

Any source or target (listed in §2 or not): take the **shape** from the closest example, whatever systems it uses, then
change `conn`, `object`, the field tuples and `writerAttrs` for your connectors. Nothing else differs.

Two conventions every proven spec follows:
- **Map target fields explicitly** with a rename on the last link (`{"Id": "ACCOUNT_ID", ...}`), so case and names never
  depend on by-name matching (SPEC_REFERENCE §3).
- **Load timestamp = `SESSSTARTTIME`**: one value for the whole run, so a run's rows group together
  (`SYSTIMESTAMP()` changes per row). A run stamp as text: `TO_CHAR(SESSSTARTTIME, 'YYYYMMDDHH24MISS')`.

## 5. Errors that cost the most time

| You see | Cause | Fix | Lesson |
|---|---|---|---|
| Run green, 0 rows changed on an Upsert | writer attributes missing for the operation | let the generator add them; test a new-key insert | L-CDI-207 |
| Target appends on every run although truncate is on | the writer ignores the flag | Snowflake `presql`, JDBC `Pre SQL`, BigQuery `writeDisposition` (§3) | L-CONN-106, L-CDI-171, L-CDI-038 |
| `Invalid Datatype: timestamp_ntz` then 'DTM process terminated unexpectedly' | Snowflake native type spelled wrong | `timestampntz` | L-CONN-093 |
| `java.math.BigDecimal cannot be cast to java.lang.Long` | Snowflake NUMBER into a bigint port | decimal(19,0) + `TO_BIGINT` | L-CONN-095 |
| `java.lang.OutOfMemoryError: GC overhead limit exceeded` (Snowflake writer) | unbounded VARCHAR target columns | `VARCHAR(n)` | L-CDI-227 |
| `PLUGIN_1762 ... OutOfMemoryError`, then reader token errors | too many unsorted Joiners / Sorters / readers in one mapping | split the mapping; sort Joiner inputs | L-CDI-210, L-CDI-129 |
| Session hangs with no error | one source feeds a Joiner's master and its detail | sorted input + Sorters, or two reads | L-CDI-106 |
| `Field <name>'s precision is invalid` (Salesforce datetime) | wrong precision | 24, scale 0 | L-CDI-245 |
| `table contains [JSON] data type that is incompatible with the [Simple] connection mode` | JSON field declared | declare STRING | L-CDI-039 |
| An Expression OUTPUT port reads another OUTPUT port and gets NULL / invalid | not allowed | use VARIABLE ports | L-CDI-105 |
| `REG_EXTRACT` returns NULL | it matches the whole value | end the pattern with `.*` | L-CDI-246 |
| Import `REPO_36004` after a failed import | a broken shell from the first try | re-import under a new name | L-CDI-204 |
| Import `MigrationSvc_030` | empty or invalid multipart | rebuild the package with the generator | L-CDI-032 |
| Import `REPO_38210` | the package binds the reserved Hosted Agent name in an org without it | remap to your runtime inside the package | L-CONN-024, L-MIG-015 |
| Mapping valid, rule-spec transformation Invalid in the designer | rule input scale not copied; or the rule specification changed after the mapping was built ('Synchronize the asset') | give `[name, TYPE, prec, scale]`; regenerate from the current rule-spec definitions, then sweep the designer for Invalid badges | L-DQ-113, L-DQ-126, L-UI-036 |
| Mapping imports, then the task create fails `APP_13500` | parentheses in the task name | letters, digits, spaces and hyphens only; check every task exists after a deploy | L-CDI-280 |
| `403 REPO_19001` on a task save | an in-out parameter default holding long SQL (about 4,000+ characters) | a per-task parameter file (`parameterFileName`) | L-CDI-285 |
| 'No space left on device' while lookup caches build | cache size = declared port precision x rows | small lookup-port precisions; filter the lookup query | L-CDI-281 |
| `Timestamp format must be yyyy-mm-dd hh:mm:ss[.fffffffff]` on a ClickHouse (JDBC V2) source | DateTime64 column in the query | select `toString(toDateTime(x, 'UTC'))` as STRING(19), `TO_DATE` in an Expression | L-CDI-264 |
| `java.lang.Long cannot be cast to java.lang.Integer` (or `...BigDecimal`, or an Integer-to-Long cast) on a ClickHouse target | port type vs UInt16 / UInt32 / UInt64 column | UInt16 -> INT32 port; UInt32 -> bigint; UInt64 -> decimal(20,0) | L-CDI-264, L-CDI-291 |
| A JDBC V2 target writes only 60-200 rows per INSERT (slow, part storm in ClickHouse) | writer batch default (200) and DTM block / wide ports | target `batchSize` 10-20K + task `Default buffer block size` 32-64 MB + narrow ports | L-CDI-262 |
| `GC overhead limit exceeded` in the JDBC V2 reader, then the session hangs at 0 rows | DTM Java heap too small for the block size | `JVMOption1=-Xmx4096m` (pmrdtm.cfg / cloud-side DTM config); stop the hung run | L-AGENT-112 |
| `java.io.IOException: Premature EOF` minutes into a long ClickHouse read | the reader stalled (slow writer) longer than ClickHouse's 30 s HTTP send timeout; the server aborted the query | read through a buffering proxy with a temp-file limit above the result size, or speed up the writer | L-CDI-267 |
| 'Unsupported JOIN keys of type hashed in StorageJoin' from a ClickHouse source query | the source is a Join-engine table, which cannot be scanned | read its persisted `.bin` data (decompressed to Native) with `file()` | L-CDI-269 |
| A ClickHouse target's insert CPU dominates every writer lane | MATERIALIZED columns are evaluated for every row on INSERT; `if()` is not short-circuited there | keep heavy derivations out of MATERIALIZED columns of high-volume tables | L-CDI-268 |
| Same row count, different checksum when hashing `formatRowNoNewline('JSONEachRow', *)` | a table column has the same name as an alias of the same SELECT | build the row JSON in an innermost subquery with unique aliases | L-CDI-270 |

## 6. Runtime environment: Hosted Agent or Secure Agent

Choose by where the data lives (L-AGENT-036).

| Needs | Runtime |
|---|---|
| SaaS to SaaS (Salesforce, Snowflake, Databricks) and nothing on a private network | Informatica Cloud Hosted Agent (nothing to install). Snowflake through a Programmatic Access Token, because it cannot read a key file |
| A private database, files on a host, SharePoint file uploads (`Attachment_File_Path`, L-CONN-125), pre/post-processing commands | Secure Agent |
| Structure Parser (CLAIRE document parsing), Data Profiling, Tableau V3 targets | Secure Agent: they fail on the Hosted Agent (L-AGENT-104, L-DQ-114, L-CONN-116) |
| Cleanse, Deduplicate / match and decision transformations (CDQ libraries) | Secure Agent: on the Hosted Agent they fail with EP_13236 (`libIDQTokenStandardiserZTransform.so`, `libIDQDecisionZTransform.so`); rule specifications run on both (L-CDI-247, L-CDI-279) |
| Advanced-mode (Spark) mappings, Spark-only connector formats | Secure Agent with a Local advanced configuration (L-AGENT-114) |

Bind only the tasks that need it to the Secure Agent (the task's `runtimeEnvironmentId`) and keep the rest on the Hosted Agent, so the agent stays small (L-AGENT-103). A Secure Agent running DI, DQ, CDC, CAI and catalog scans needs 16 GB, not 8 GB (L-AGENT-109). If the Hosted Agent goes down, rebind the tasks and their connections to a Secure Agent (lookups resolve through the connection's runtime), and expect `SESSSTARTTIME` stamps to change time zone (L-ENV-100, L-CONN-132, L-AGENT-115).

Moving mappings to another org: export and import packages ([10 - Migration](../12-deploy-migrate/01-export-import-v3-migration-api.md)).
Re-point connections, runtime environments (AgentGroup objects, one per target runtime), org ids, pre-commands and
checksums inside the package (L-MIG-082). Bundle-template tasks listed in an export have no file and fail
MigrationSvc_031, so rebuild them with the generator (L-MIG-083). Clone a connection with v2 minus agentId,
agentGroupId and orgId (L-CONN-122); connection names refuse parentheses (L-CONN-124).

## 7. When the generator cannot do it (yet)

The generator not knowing something is never a reason to tell the user no, or to move them to a connector it knows.
**The generator only has templates for the connectors and transformations in this page; IDMC supports far more.** When
a source, target or transformation the user needs has no template here, use the exemplar route below. It is the
standard way forward, not a workaround of last resort.

### 7.0 The exemplar route: learn the shape from a mapping that already uses it

Say this to the user first: *"IDMC supports <connector> as a <source / target>, but this package has no template for
it yet. I will learn its exact settings from one mapping that already uses it, build yours from that, and add the
template to the package so it is there next time."*

1. **Ask for an exemplar.** "Is there a mapping in your org that already reads from / writes to <connector>?" If yes,
   find it: `GET /public/core/v3/objects?q=type=='DTEMPLATE'&limit=200` (match by name), or let the user give the
   name or path. Any mapping that uses the connector the same way (as a source, as a target) is enough; its other
   transformations do not matter.
2. **No exemplar yet?** Ask the user to create one once in the Mapping Designer: one source, one target, the connector
   in the role you need (e.g. a flat-file source to a `<connector>` target with two fields), then Save. It does not
   need to run, and it takes a couple of minutes. This is the one UI step of the route (rung 8 of the workaround ladder).
3. **Export it** (read-only, changes nothing in the org):
   `python "toolkit/lib/idmc_export_import.py" export --id <frsGuid> --out exemplar.zip`.
   Keep the zip outside any shared folder: it holds your org's ids.
4. **Read it:** `python toolkit/mapgen/exemplar.py exemplar.zip`. For each source, target and lookup it prints the
   connection reference, `typeSystem`, `objectType`, the object path, the read / write options and runtime attributes
   that differ from the defaults, connector-specific attribute objects, the fields as spec tuples, a starter spec node
   and a starter profile entry; it also names any transformation class the generator does not build yet.
5. **Build your spec from it:** your connection under any `kind` label (with the exemplar's `typeSystem` in the profile
   when it is not `TOOLKIT`), the object path in the exemplar's form, the field tuples, `writerAttrs` from its runtime
   attributes, and anything else through the node's `set` / `advanced` escape hatches (SPEC_REFERENCE §6) or a
   `generic` node with the exemplar's class (SPEC_REFERENCE §5.6). If the shape is hard to reproduce, package-clone the
   exemplar mapping itself and edit it (route 3 in [02](02-how-claude-builds-mappings-headless.md) §5).
6. **Prove it:** lint, `deploy` (dry run), `deploy --execute --expect-org <orgIdV3>`, then (with the user's approval) one run, and check the rows.
7. **Enrich the package, so the learning persists:** add the connector's row to §2 of this page (object path, native
   types, full-reload setting, must-know), save a placeholder-only example spec in `toolkit/mapgen/examples/connectors/`
   (`m_ex_<source>_to_<target>.json`; never the exemplar zip or your org's ids), add a dated lesson in
   `lessons`, and note any generator change it would need (for example a connector-kind entry) for the next
   maintainer to probe before shipping.

### 7.1 Other gaps

0. A connector it has no row for (SAP, Oracle, SQL Server, an FTP or cloud file store, a REST API...): the exemplar
   route (§7.0). For a simple relational or file connector, the generic path may work straight away: give the
   connection any `kind` label, take the object path and native types from the connector metadata in your org, and
   build the simplest passthrough first; if lint, the import or the run disagrees, go to §7.0.
1. A transformation it has no node for: the exemplar route (§7.0) with a mapping that has it; `exemplar.py` names its
   class, and the `generic` node takes its raw properties (SPEC_REFERENCE §5.6). The designer's JavaScript bundle holds every class model
   ([02](02-how-claude-builds-mappings-headless.md) §7).
2. A one-off SQL change to an existing task: route 2 in [02](02-how-claude-builds-mappings-headless.md), with
   [08 Changing Pipelines Safely](07-changing-pipelines-safely.md).
Then, for anything else, the workaround ladder in [New Pipeline Milestones](../00-start-here/08-new-pipeline-milestones-any-source-any-target.md).

3. Not headless on the last probe (each has a workaround in its doc; re-probe in your org): publishing an API-made
   advanced taskflow (chain linear taskflows, or publish once in the UI), changing an existing mapping's connector type
   (regenerate the mapping on the new connection), CDI parameter sets ([02](02-how-claude-builds-mappings-headless.md) §8).

When you learn something new, add it to the lessons file and to the matching row of this page in the same edit.
