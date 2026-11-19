# Profiling: what is headless

**Answers:** Which profiling path fits (Data Profiling profile, catalog-source profiling, CLAIRE DQ agent)? How do I
create, update, run, poll and read the run history of a profile over REST? Which sampling options does each connector
allow? How do I keep a wide profile from overloading a shared Secure Agent? Why does a catalog source profile nothing?

**Read when:** creating or running profiles headless; a profile fails, never shows a run, or takes the agent down;
counting profile runs for a job budget; catalog profiling coverage looks wrong.

**Key rules:**
- Data Profiling is fully headless on `<pod>-dqprofile` with `IDS-SESSION-ID` (a v3 session on some pods): clone a
  template body, `PUT` to change it, `POST /profile/<id>/execute`, poll `GET /job/<jobId>` (L-DQ-019, L-DQ-020).
- Read run history one run at a time, `GET /runDetail/<profileId>/<runKey>` for runKey 1..`lastRunKey`; the `/filter`
  form can answer 400 `PROFILE_SVC_00093` (L-DQ-019).
- Sampling options are fixed per connector (BigQuery V2 profiles All Rows only): materialise a deterministic sample
  table and profile it with All Rows (L-DQ-102, L-DQ-099).
- Size before you profile: a run is 3 + ceil((columns + rules) / 50) subtasks, and two DTMs per profile thrash a small
  agent; tune `runtimeOptions.profileAdvProps` on the profile rather than the agent-wide DTM pool (L-DQ-098,
  L-DQ-103).
- Profile runs are not in the v2 activity log: count them from the profiling service for job budgets (L-IPU-055).
- A catalog source profiles only with the Data Profiling capability, empty tables never profile, and exit 127 means a
  missing `libidn.so.11` (L-DQ-043, L-DQ-042, L-DQ-036).
- A JDBC V2 source (ClickHouse proven) profiles headless from a body cloned from a profile that has run on JDBC V2;
  the earlier "blocked" records are disputed (L-DQ-128).

**Related:** [DQ Assets](01-dq-assets-rule-specs-cleanse-dictionaries-verifiers.md) ·
[DQ Scorecards](04-dq-scorecards-warehouse-pattern-and-data-profiling-scorecards.md) ·
[Catalog Sources - Create, Scan, Update, Purge](../07-catalog-governance-cdgc/02-catalog-sources-create-scan-update-purge.md) ·
[Secure Agent - Install, Run & Tune](../02-secure-agent-connections/01-secure-agent-install-run-tune.md) ·
[Lessons: Data Quality & Profiling](../../lessons/by-domain/06-data-quality-profiling.md)

**Last verified:** 2026-11-05

> **Summary.** IDMC has three profiling paths: (1) **Data Profiling profiles** on the `<pod>-dqprofile` service, fully
> headless (create by cloning a template body, update, bind rule occurrences, execute, poll, read run history);
> (2) **catalog-source profiling** in CDGC, a capability on the catalog source run through the CDGC executable API on the
> agent's native `pmdtm` engine; (3) the **CLAIRE DQ agent's** file-based profiling of an uploaded sample
> ([03](03-claire-dq-agent-file-based-profiling-cleansing.md)). Profile objects travel in v3 packages and arrive
> without their rule occurrences (L-DQ-026). No REST read of per-rule pass rates has been found (L-DQ-031). Endpoints:
> [profiling endpoint table](../12-reference-library/idmc-api-mcp-reference/content/17-profiling.json).

---

## 1. Which path to use

| Path | Where it runs | Needs CDGC? | Headless? | Where results appear |
|---|---|---|---|---|
| **Data Profiling profile** (a "data profiling task") | `<pod>-dqprofile` service; the job runs on the connection's runtime environment (DIS; Elastic Server for Avro/Parquet/JSON) | **No** for profiling. The scorecard *dashboard* needs CDGC ([04](04-dq-scorecards-warehouse-pattern-and-data-profiling-scorecards.md)) | **Yes**: create, update, execute, poll, run history (proven) | Data Profiling console: Results tab (column stats, patterns, value frequencies, Rules view); metric-store OData reads |
| **Catalog-source profiling** | a CDGC catalog source with the Data Profiling capability, run through the executable API; `pmdtm` on the agent | **Yes** | **Yes** (run and poll); source configuration is headless too (multipart) | Catalog asset attributes (`core.profiled`, `core.nullPercentage`,...), MCC job view |
| **CLAIRE DQ agent `data_quality_cleansing`** | Informatica's cloud (the file is uploaded) | No | **Yes** (MCP) | The MCP answer bundle only; nothing is saved as a console asset |
| CLAIRE DQ agent `data_profiling` | Informatica's cloud, over a **cataloged** asset | Yes | Yes, but empty or erroring on uncataloged assets (L-DQ-071) | MCP answer |

Rule of thumb: for a reusable, schedulable profile or scorecard, use path 1. For catalog coverage and CLAIRE answers, use
path 2. For a quick look at a sample with generated cleansing code, use path 3.

The same rule specifications also run in a CDI mapping over the source and can be proven against SQL: on a JDBC V2
ClickHouse source an independent SQL computation of the same checks on a 1M-row sample matched 866 of 867 group x
check cells, and the one miss was a rule definition (L-DQ-117, L-DQ-118, 2026-10-29).

### 1.1 Sampling by connector (L-DQ-102)

Data Profiling offers All Rows, First N Rows or Random N Rows, but which ones depends on the connection type (vendor
Data Profiling guide):

| Connector | Sampling options |
|---|---|
| Google BigQuery V2, Flat File, Amazon S3 V2, ADLS Gen2, Google Cloud Storage V2, SAP BW Reader, mapplets | All Rows only |
| JDBC V2, PostgreSQL, Oracle, SQL Server, Salesforce, Amazon Athena, Microsoft Fabric Data Warehouse, ODBC | All Rows, First N Rows |
| Amazon Redshift V2, Azure Synapse SQL, Snowflake | All Rows, Random N Rows (First N too on Synapse and Snowflake) |
| Databricks Delta | All Rows; Sample N Rows only on Data Integration Server execution |

- First N reads whatever rows the source returns first, so it is rarely representative.
- **For a large source, profile a sample table.** Build a deterministic, stratified sample outside IDMC (for example at
  most 100k rows and at most 50 profiled columns), selected with a portable hash key so the same rows stay in at every
  refresh and in every engine (L-DQ-099). Then profile it with All Rows; the body carries
  `"samplingOptions": {"samplingType": "ALL_ROWS", "rows": -1}`. A 33,277-row, 39-column staged sample profiled to
  COMPLETED on a small agent where a 181-column full-width profile had overloaded it.
- A catalog source's Data Quality scope samples separately: All Rows, Limit N Rows (default 1000) or Custom Query
  ([Catalog Sources](../07-catalog-governance-cdgc/02-catalog-sources-create-scan-update-purge.md)).

---

## 2. Data Profiling service REST (path 1)

### 2.1 Host and session (L-DQ-020)

```
Base:   https://<pod>-dqprofile.<domain>.informaticacloud.com/profiling-service/api/v1
Header: IDS-SESSION-ID: <sessionId>
        Accept: application/json        (+ Content-Type: application/json on writes)
```

- On one pod the service answered **401 "Exception encountered while processing JWT"** to the v2 `icSessionId`.
  The **v3** login `sessionId` (from `POST https://<domain>.informaticacloud.com/saas/public/core/v3/login` →
  `userInfo.sessionId`) worked. Another org accepted the v2 id. Make the helper org-aware, or always use the v3 session.
- These routes are not "SPA-session only" (that belief is overturned, L-DQ-086 → L-DQ-020): a plain
  `INFA-SESSION-ID` GET returns the identity-service HTML shell, while `IDS-SESSION-ID` carrying a v3 session works.
- An HTML body with status 200 means you reached the identity SPA (wrong header or plane). Assert on the body shape,
  not the status.

### 2.2 Routes

| Purpose | Verb + path (under the base) | Body | Success / read-back | Errors seen | Evidence |
|---|---|---|---|---|---|
| List profiles | `GET /profile?limit=200` | none | 200 array of profiles (`id`, `name`,...) | | proven |
| Read one | `GET /profile/<id>` | none | 200 full definition (source, fields, rules, profileableFields, runtimeOptions, frsProjectId/frsFolderId) | HTML 200 = wrong session | proven |
| Create | `POST /profile` | a template profile's body, edited (§2.3) | 200/201; the response carries `id`. If it does not, list by name. | **500 "Row was updated or deleted"** if you send client-side ids (L-DQ-021); **PROFILE_MDL_00006** for unsupported column types (L-DQ-022); **PROFILE_SVC_00014** while the agent's DIS is down | proven |
| Update | `PUT /profile/<id>` | the full body from GET, edited | 200; GET shows the change | same as create | proven |
| Delete | `DELETE /profile/<id>` | none | confirm with `GET /profile` (it is no longer listed); status code not recorded | | documented (vendor troubleshooting examples) |
| Run | `POST /profile/<id>/execute` | `{}` | 200 `{"profileJobId": "<jobId>",...}` | 404 **PROFILE_SVC_00005** for a deleted profile id (L-DQ-096) | proven (8/8 in two orgs) |
| Poll a run | `GET /job/<profileJobId>` | none | `status` leaves RUNNING / QUEUED / SUBMITTED / STARTING; **COMPLETED** = done; `errorMessage` on failure; "No errors encountered" | | proven |
| Run history | `GET /runDetail/<profileId>/<runKey>` for runKey = 1..`lastRunKey` (from `GET /profile/<id>`) | none | one run: `startTime` (epoch ms), `status`, `rowsProcessed`, `numberOfColumns`, `numberOfRules` | `POST`/`GET /runDetail/<profileId>/filter` answered **400 PROFILE_SVC_00093** "Provided argument does not match the expected type" on one pod; `lastRunKey: null` after the agent died mid-run | proven (L-DQ-019) |
| Rule bindings | `GET /ruleOccurrence/...ForProfile_V2_Token/<uuid>` | none | the profile's rule occurrences (scorecard bindings) | | proven reads |
| DQ dimensions | `GET /ruleOccurrence/ruleType` | none | the six built-in dimensions | | proven reads |
| Column metrics | `GET https://<pod>-dqprofile.<domain>.informaticacloud.com/metric-store/api/v1/odata/Profiles('<uuid>')/Columns` (also `/Insights`, `/Patterns`, `/ValueFrequencies`) | none | per-column statistics, CLAIRE insights (rule-spec suggestions), patterns, top values | | proven reads |

- The profile's internal UUID differs from the `repoHandle` in the UI URL. Take ids from `GET /profile` (match on
  name), never from the address bar (L-DQ-049).
- **Run history, step by step (L-DQ-019).** `GET /profile/<id>` returns `lastRunKey` (a run counter 1..N)
  and `profileKey` (a small numeric key). Iterate `GET /runDetail/<profileId>/<runKey>` from 1 to `lastRunKey` and cache
  the runs already seen. A run that dies with the agent (engines killed mid-run) can leave `lastRunKey: null`, so a
  profile that reads "never run" does not prove that no profiling DTM ran.
- **Map a host process to its profile.** The agent names profiling DTM sessions `s_profiling_<profileKey>_<run>_<n>`
  (with matching `.param` and `.xml` files under the agent's Data Integration Server directory), so a running or
  crashed `pmdtm` process maps back to `profileKey`.
- **Counting runs for a job budget.** Profile runs do not appear in the v2 activity log; count them per owned profile
  from this run history, and weight each run as 1 + 3 + ceil((columns + rules) / 50) jobs until the cap behaviour is
  measured (L-IPU-055, [Entitlement, Licenses & Job Caps](../11-ipu-metering-licensing/03-entitlement-licenses-job-caps.md)).
- `/data360/profiling/v1/results` returns 404: that is the wrong host family.
- `/profiling-service/internal/api/v1/ruleOccurrence/publishResults` appears only inside an error message on an
  Informatica ops domain. The `internal/` segment means unsupported, so do not call it (L-DQ-032).
- Query CRUD (create, update, delete profiling *queries*) is vendor-documented, with paths in the separate "Getting
  Started with Cloud Data Profiling REST API" guide, which is not held. Say "documented, paths not held", never "no API".

### 2.3 Create body: clone a known-good profile on the same connection type

Take `GET /profile/<templateId>` of a working profile on the **same connection type** and edit it:

1. **Remove server-owned keys:** `id`, `profileKey`, `version`, `frsId`, `createdBy`, `createdByName`, `createTime`,
   `updatedBy`, `updatedByName`, `updateTime`, `lastRunKey`; also `runtimeOptions.id` and `source.id`. Send **no**
   client-side ids anywhere, including in rule blocks and field entries, or you get 500 "Row was updated or deleted".
2. **Set identity and placement:** `name`, `description`, `frsProjectId`, `frsFolderId`, `connectionId`.
3. **Set the source:** `source.name = "<table>"`, `source.fields = [...]` (§2.4),
   `source.rules = []`, and `source.properties = {"dataSourceType":"TOOLKIT_CCI","sourcePath":"<schema>/TABLE"}`
   for a native relational (CCI) source.
4. **Declare the columns to profile:** one `DATASOURCEFIELD` entry per column, with `columnKey` counting from 10001:

```json
"profileableFields": [
  {"isDeleted":false,"appliedBy":"USER","columnKey":10001,"sourceName":"<table>","fieldName":"<col>",
   "precision":<p>,"scale":<s>,"fieldType":"DATASOURCEFIELD"}
]
```

5. `POST /profile`, then `GET /profile?limit=200` to confirm the new `id` if the response does not carry it.

**A JDBC V2 source (ClickHouse, proven 2026-11-02; L-DQ-128).** Five profiles on a JDBC V2 connection COMPLETED, up to
an ALL_ROWS run over a wide table of about 100M rows, two of them created by this cloned-body POST, and rule bindings and
metric-store reads worked on them. The body: `connectionId` = the JDBC V2 connection; `source.sourceType` DATASOURCE;
`source.dataSourceType` and `source.properties.dataSourceType` = `TOOLKIT_CCI`; `source.properties.sourcePath` =
`<database>/TABLE`; `source.name` = the table; `runtimeOptions.runtimeEnvironmentId` null (the connection's runtime
is used); `samplingOptions {samplingType ALL_ROWS, rows -1}`; fields as in §2.4; `profileableFields[]` entries
`{fieldType DATASOURCEFIELD, appliedBy USER, fieldName, sourceName = table, precision, scale}`. Then
`POST /profile/<id>/execute` and poll `/job/<profileJobId>`. Earlier attempts failed (JDBC_V2_ERROR_205 on object
fetches, L-CONN-089; NSTRING refused and a 'string' create that hung, L-DQ-119; both now disputed). What differed
(a body cloned from a profile that had already run, NSTRING paired with `dataType` varchar, another agent and
connection) was not isolated, so start from a profile that has run on the same connection type. Profile typed sample
tables, not raw production tables: cast enum and low-cardinality columns to Nullable String, numbers to Float64 and
dates to text, and use a stable hash sample (about 2,000 rows per partition, L-DQ-099); a full profile of a
billion-row table would have pulled a few hundred GB through the agent.

### 2.4 Field typing (PostgreSQL example) (L-DQ-022)

Build `source.fields[]` from `information_schema.columns`. Each entry is
`{"name","dataType","precision","scale","pcType","order","isDeleted":false,"isMetadataUpdated":false}`:

| Postgres type | `dataType` | `pcType` | precision / scale | Notes |
|---|---|---|---|---|
| text, uuid | `text` | `NSTRING` | char length or 4000 / 0 | |
| character varying | `varchar` | `NSTRING` | char length or 4000 / 0 | |
| numeric | `numeric` | `DECIMAL` | numeric precision (28 default) / scale | |
| timestamp / timestamptz | `timestamp` / `timestamp_with_time_zone` | `TOOLKIT_DATETIME` | 32 / 0 | |
| `character(n)`, `int4` | skip | | | rejected with **PROFILE_MDL_00006** as profileable fields; profile a view that casts them |
| jsonb, arrays | skip | | | not profiled by this builder (whether the service accepts them is untested) |

On a JDBC V2 source the fields that worked were `{dataType varchar, pcType NSTRING, precision 4000, scale 0}` for text and
`{dataType double, pcType DOUBLE, precision 15}` for numbers (L-DQ-128).

### 2.5 Rule occurrences inside the body (L-DQ-023)

A rule occurrence binds an existing **rule specification** (by its `frsId`) to a column:

- Each rule spec appears **once** per profile in `source.rules[]`:

```json
{"name":"<rule spec name>","description":"<rule> on <col>","frsId":"<ruleSpecFrsId>",
 "inFields":[{"name":"<rule input>","label":null,"dataType":"string","precision":255,"scale":0,"isDeleted":false}],
 "outFields":[{"name":"<rule output>","label":null,"dataType":"string","precision":255,"scale":0,"isDeleted":false}],
 "isDeleted":false,"ruleType":"RULE_SPECIFICATION"}
```

- Each bound column adds one `MAPPLETFIELD` entry to `profileableFields[]`. Several columns can reuse one rule spec:

```json
{"isDeleted":false,"frsId":"<ruleSpecFrsId>","scoreCardId":null,"assignmentIdentifier":"<fresh uuid hex>",
 "inputFieldMappings":[{"dataSourceFieldName":"<col>","inFieldName":"<rule input>","isDeleted":false,
                        "dataSourceFieldPrecision":<p>,"dataSourceFieldScale":<s>}],
 "outputFieldMappings":[{"columnKey":40001,"datatype":"string","outFieldName":"<rule output>","label":null,"isDeleted":false}],
 "fieldType":"MAPPLETFIELD","ruleType":"RULE_SPECIFICATION"}
```

- `columnKey` for rule outputs counts from 40000 + n; data columns use 10001 + i.
- **To update an existing profile's rules:** GET it, set `source.rules = []`, keep only the `DATASOURCEFIELD` entries of
  `profileableFields`, append the new rule blocks and `MAPPLETFIELD` entries, then `PUT /profile/<id>`.
- Rule-occurrence *scoring* settings (dimension, thresholds) come from the rule spec and the Metrics tab. See
  [04](04-dq-scorecards-warehouse-pattern-and-data-profiling-scorecards.md). The vendor caps a profile at **≤200 rule
  occurrences**: above that, the scorecard publish times out (L-DQ-032).
- After you create or update occurrences, **run the profile again**. Scores only exist for runs after the change.

### 2.6 Execute and poll

```
POST {base}/profile/<id>/execute        body {}     → 200 {"profileJobId":"<jobId>"}
GET  {base}/job/<jobId>                              → {"status":"RUNNING"|...|"COMPLETED", "errorMessage":...}
```

Poll every ~10 s, and stop when `status` is not RUNNING, QUEUED, SUBMITTED or STARTING. Schedule it yourself (cron),
or set a schedule on the profile's Schedules tab in the UI. A profile on a schedule runs after the org's schedule offset.

**Do not use the platform job API.** `POST /saas/api/v2/job` with a profile id returns **403 `UI_13404`** "Object
identifier is not valid or missing" for every `taskType` tried (`Profile`, `PROFILE`, `DSS`). Also,
`/public/core/v3/jobs` and `/v3/profile/<id>/run` return 404 (L-DQ-024). That probe is what created the
belief, now overturned, that "profiles have no REST run verb" (L-DQ-087 → L-DQ-019).

### 2.7 No REST read of per-rule pass rates (L-DQ-031)

Every guessed result path returned "not implemented". CDQ rule runtime scores were also unreadable over REST in July.
The per-rule scores show in the console (View Scorecard / Results → Rules). If an application must display DQ numbers,
compute them in your own warehouse tables ([04](04-dq-scorecards-warehouse-pattern-and-data-profiling-scorecards.md)).

### 2.8 Gotchas table

| Symptom | Cause | Fix | Lesson |
|---|---|---|---|
| 500 "Row was updated or deleted" on POST /profile | client-side ids in the body | strip every id | L-DQ-021 |
| PROFILE_MDL_00006 | an `int4` or `char(n)` column in profileable fields | skip it, or profile a casting view | L-DQ-022 |
| PROFILE_MDL_00006 'PowerCenter data type NSTRING ... is not supported' on a JDBC V2 create; or a 'string' create that never answers | hand-built fields on a body cloned from another connector's profile (2026-10-29, disputed) | clone a profile that has run on JDBC V2; NSTRING with `dataType` varchar then worked (2026-11-02) | L-DQ-128, L-DQ-119 |
| `JDBC_V2_ERROR_205 'entry [<database>] already exists in the collection [null]'` on every object or field fetch (ClickHouse) | seen 2026-10-03; did not recur with the cloned JDBC V2 body (disputed) | the cloned-body create of §2.3 | L-DQ-128, L-CONN-089 |
| 401 "Exception encountered while processing JWT" | v2 session on a pod that wants the v3 session | use the v3 login `sessionId` | L-DQ-020 |
| 403 UI_13404 | trying to run a profile through `/api/v2/job` | use `POST /profile/<id>/execute` | L-DQ-024 |
| 'Profile job failed with error Cannot parse null string.' in 'Generating data profiling mappings', no DTM (BigQuery V2) | the connection's five hidden retry attributes (`maxRetryAttempts`, `initialRetryDelay`, `retryDelayMultiplier`, `maxRetryDelay`, `totalTimeout`) are empty strings, as on connections created over REST | fill the connector defaults 6, 1, 2.0, 32 and 50 (Enable Retry stays false), POST the full connection back with the key, re-run; tables of up to 43,210 rows then profiled in about 50 s | L-DQ-110 (resolves L-DQ-107) |
| FRS_108 / "cannot move profile" | moving an orphan profile document (not listed by `GET /profile?limit=200`) with FRS MoveEntities; real profiles move with FRS_200 and keep their run history | check the list first; back up `GET /profile/<id>` bodies (v3 export of PROFILE fails MigrationSvc_086) | L-DQ-124 (disputes L-DQ-029) |
| UI shows "updated source metadata / unsaved changes" | the profile was updated through the API | open and save once in the UI (check before a demo) | L-DQ-030 |
| 403 APP_105060 "Unable to fetch Connector attributes [com.infa.adapter.amazons3]" | the profiling results store uses the Amazon S3 V2 connector, which is not enabled on the runtime environment | Administrator → Add-On Connectors → Amazon S3 V2 → enable/assign to the RE | L-DQ-033 |
| Scorecard job "Read timed out" on publishResults, while the results page is fine | more than 200 rule occurrences on the profile | ≤200 occurrences; re-import or trim, re-run | L-DQ-032 |
| 400 PROFILE_SVC_00093 "Invalid request - Provided argument does not match the expected type" | the `/runDetail/<id>/filter` form on some pods | iterate `GET /runDetail/<profileId>/<runKey>` | L-DQ-019 |
| "never run" profile, yet `pmdtm` `s_profiling_<profileKey>_*` processes on the agent | the run died with the agent and left no run record | match `profileKey` from `GET /profile/<id>` to the DTM session name | L-DQ-019 |
| PROFILE_SVC_00014 "No running service found of type Data_Integration_Server" on create or run | the agent's DIS is down; after a memory thrash its engines can stay in ERROR for hours | remove the cause (stop or shrink the run, free memory), restart the agent's service unit once, poll `GET /api/v2/agent/details/<agentId>` until every engine is RUNNING | L-AGENT-076 |
| 404 PROFILE_SVC_00005 "Cannot find PROFILE with ID … for orgId …" on every scheduled execute | a runner still holds ids of deleted profiles | remove the ids from the runner's list; check the next run | L-DQ-096 |
| agent services in ERROR and host load spiking during one wide profile | two DTMs per profile on a small capped agent | profile a sample table; fewer columns per mapping (§5.5) | L-DQ-098 |
| JDBC V2 profile fails 'Data too long for column error_msg'; the agent log shows '[<db>] was not found', 'Object(s) [<t>] not found', 'Invalid operation field name' or 'cannot be cast to java.sql.Timestamp' | the source must be a real table of the connection's own schema with its real column names, and recognised types must come back natively | one connection per database; real table + column names; DateTime / numbers bare, Date as toDateTime(col), only complex types as text | L-DQ-134 |
| 500 PROFILE_SVC_00004 'Data too long for column property_value' (ds_adv_properties) on POST /profile | the SQL Override is longer than 4,000 characters | split the columns across profiles, each override under 4,000 characters, same sample clause | L-DQ-133 |
| 'Invalid operation field name' after the profiled table was recreated with other columns; a new profile on the same table then returns no rule metrics | not isolated | `DELETE /profile/<id>`, recreate the profile on a view over the table | L-DQ-112 |

---

## 3. Profile objects in migration packages

- **Export shape (L-DQ-027).** A v3 export of a profile yields a `.PROFILE.json` with `connectionId`, a
  **hard-coded** `source.fields[]` list and `runtimeOptions`. Retargeting it to another table means rewriting the field
  list. For new tables, cloning through the REST body (§2.3) is easier.
- **Profiles travel in v3 packages (L-DQ-025).** `POST /public/core/v3/objects` for a profile
  returns 405, but profiles moved inside an export/import package like other assets.
- **They arrive with 0 rule occurrences (L-DQ-026).** Re-bind the rules with the **target's** rule-spec
  `frsId`s (§2.5), then re-run. Rule specs that came from Informatica bundles must already exist in the target, or be
  imported with REUSE. Keep id caches (project, folder, rule specs) **per org**, so no target object ever receives a
  source-org id.
- **Bulk import troubleshooting (vendor, CDP October 2025 pp.159-160; L-DQ-028):**
  - if a bulk profile import fails, delete the profiles already in the target folder (`GET` + `DELETE` on
    `/profiling-service/api/v1/profile/<id>`), confirm the list is empty, and import again;
  - uncheck any profile whose zip entry has an empty object reference;
  - if a column path is missing on the target connection, put the folder path in the source connection first, then
    export and import.
- **Seed an org that has no profiles (L-DQ-053).** Import a package that holds a profile with rule occurrences plus its
  rule specs, retarget the source connection, re-bind the occurrences and run (proven end to end: import, re-bind, 8/8
  COMPLETED). After that, one working profile is enough to clone the rest by REST (§2.3).

---

## 4. Authoring in the UI (when you must)

- **Wizard traps (L-DQ-035).**
  - The Data Profiling wizard chokes when it enumerates system or backup schemas (`pg_catalog`, `information_schema`,
    `_archive.*` copies). Scope the **connection's Schema field**, not just the profile, to business schemas.
  - Tick at least one column on the Columns tab, or Save errors.
- **"Enable CLAIRE capabilities"** is a checkbox in the profiling-task wizard. Unchecking it sidestepped a Java
  transformation (pmjtx) plugin defect on one agent (L-DQ-039).
- **Playwright** (from a host outside any enterprise proxy; Data Profiling was not retested with the Chromium flag set
  that drove other consoles from behind one on 2026-10-06, L-UI-031):
  - reuse a saved login state, because every login counts toward the account lockout;
  - create one profile per browser session;
  - select all columns with the header checkbox and verify through the page text;
  - expect the Location picker to be flaky (profiles can land in Default).

  See [Claude Working Methods & Tooling](../14-claude-working-methods/).
- The DQ privacy switch **Disable Data Value Storage** (vendor) stops minimum, maximum and most-frequent values being
  stored in the profiling warehouse. The **Sensitive Data - view** privilege hides them per role.

---

## 5. The profiling engine on the agent (pmdtm)

### 5.1 Only profiling needs `pmdtm` (L-DQ-038)

In a CDGC catalog scan:

- Metadata Extraction, Lineage, Data Quality and Classification run in the Java scanner, the DQ engine and cloud
  services;
- **Data Profiling launches the native `pmdtm` engine** on the Secure Agent;
- Data Observability depends on profiling and is skipped when profiling fails.

So a scan where *only* profiling fails points at the agent's DTM, not at the source database.

### 5.2 Zero columns profiled: read the pmdtm exit code first (L-DQ-037)

When scans complete and metadata is present but nothing is profiled, check how `pmdtm` died on the agent host before
you chase job locks, `readyToRun` flags or auth errors. Every source failing identically is the tell.

| Exit | Meaning | Look at |
|---|---|---|
| 127 | ELF loader failure: a native library is missing (usually `libidn.so.11`) | the tomcat log of Data_Integration_Server; `ldd pmdtm` |
| 134 | SIGABRT | the DTM logs; the same compat-library fix once cleared it |
| 137 | OOM kill | host memory; DTM heap (`JVMOption1=-Xmx2048m` in `pmrdtm.cfg`, re-check after upgrades) |

### 5.3 The `libidn.so.11` fix on Debian 12 (and RHEL/Rocky 8/9) (L-DQ-036)

`pmdtm` (under `ICS/main/bin/rdtm/`) links `libpmcurl.so`, which needs `libidn.so.11`. Debian 12 ships only
`libidn.so.12`, and `libidn11` is not in its repos. Every profile then dies at launch with
`pmdtm: error while loading shared libraries: libidn.so.11` and exit **127**. libidn 1.x is ABI-compatible; the SONAME bump
was a packaging change. Make the fix durable in three ways:

```bash
# 1) system symlink (survives reboots and agent re-syncs, which only rewrite the agent directory)
sudo ln -s /usr/lib/x86_64-linux-gnu/libidn.so.12 /usr/lib/x86_64-linux-gnu/libidn.so.11
# 2) a compat directory registered with the loader
sudo mkdir -p /opt/infa-compat-libs && sudo cp -L /usr/lib/x86_64-linux-gnu/libidn.so.12 /opt/infa-compat-libs/libidn.so.11
echo /opt/infa-compat-libs | sudo tee /etc/ld.so.conf.d/infa-compat.conf && sudo ldconfig
# 3) agent-scoped: append the compat dir to LD_LIBRARY_PATH in agent_start.sh, then restart the agent
# verify:
env -u LD_LIBRARY_PATH ldd <agent_home>/.../ICS/main/bin/rdtm/pmdtm | grep libidn     # must resolve
```

- `ldconfig -p` will not list the library under the `.11` name; that is fine.
- Count failures before and after in `<agent_home>/apps/Data_Integration_Server/logs/tomcat/tomcat_<ver>.log`. In the
  proof, 1,965 libidn misses matched 1,965 exit-127s before the fix and 0 after; profiled columns went from 0 to 671
  within an hour.
- Alternative: install an EL7 `libidn-1.28` RPM with `rpm -i --nodeps`.
- A Java OOM would be exit 137 with a stack trace, so do not tune heap for an exit 127.

### 5.4 "DTM process terminated unexpectedly" on every profile run (L-DQ-039)

Profiling uses a Java transformation (pmjtx). The DTM import log (`Data_Integration_Server/logs/s_profiling_*_import.log`)
stopped at "Post validation on imported plug-ins... Error encountered while Parsing file". The cause was **dangling
`*.xml` symlinks** in the `rdtm` plugin folders, because DIS parses every XML file there. Renaming the dead files and
restarting the agent fixed it. Non-profiling mappings kept running the whole time.

### 5.5 Size the run and control its fan-out (L-DQ-098, L-DQ-103)

**Subtask math (vendor).** A profile run is 3 fixed subtasks (row count, generate mappings, load to the metric store)
plus one subtask per `maxColumnsPerMapping` columns and rules (default 50) at or below `minNoOfRowsForSplitMapping`
rows (default 100,000,000), or one subtask per column above it. A 181-column table above 100M rows means about 184
subtasks per run; a 100k-row sample needs about 7. The vendor example: 10M rows x 100 columns gives 2 subtasks by
default, or 4 smaller ones with 25 columns per mapping, each using less memory.

**Concurrency.** The Data Integration Server runs up to `maxDTMProcesses` DTMs at once (documented default 2; vendor
sizing rule n = int(0.8 x cores)). One profile of a 181-column table on an agent confined to a 4 GB, 1-vCPU slice
started two profiling DTMs of 33-36 threads each: the slice sat at its memory limit and thrashed, the host reached load
63, and several agent services stayed in ERROR until a restart.

**Per-profile knobs.** The profile body's `runtimeOptions.profileAdvProps` holds the vendor's advanced options as
fields; `null` means the default:

```json
"runtimeOptions": {"runtimeEnvironmentId": null, "profileAdvProps": {
  "maxColumnsPerMapping": 25, "minNoOfRowsForSplitMapping": null,
  "maxMemory": null, "maxPercentMemory": null, "dtmBufferSize": null, "defaultBufferBlockSize": null,
  "lineSequentialBufferLength": null, "maxTopN": null, "maxPatterns": null, "maxPatternThresholdPercent": null,
  "maxRanks": null, "detectOutliers": true, "inferDateTime": true, "enableClaireAnomalyDetection": true,
  "stopOnErrors": null, "tracingLevel": "NORMAL"}}
```

`maxMemory`/`maxPercentMemory` is Maximum Memory per Mapping (default 512 MB). `runtimeEnvironmentId: null` means the
profile runs on its connection's runtime environment. The field names were read live from `GET /profile/<id>`; a `PUT`
that changes them has not been exercised yet, so read the body back after the first change.

**Before profiling on a small or shared host:**

1. Profile a sample table (§1.1), not the full-width source.
2. Sum the configured heaps of everything inside the agent's memory cap, and make sure every agent process runs inside
   it (L-AGENT-017; [Secure Agent - Install, Run & Tune](../02-secure-agent-connections/01-secure-agent-install-run-tune.md)).
3. Lower `maxColumnsPerMapping` on the profile (PUT the full body) instead of lowering the agent-wide `maxDTMProcesses`
   that other pipelines rely on.
4. Run one profile at a time and watch the host while the first one runs.

Agent-level setup (services, drivers, restarts) is in [Secure Agent & Connections](../02-secure-agent-connections/).

---

## 6. Results storage: which store does profiling need?

- **Proven (L-DQ-033):** in one org the profiling results warehouse was an Informatica-managed, immutable
  Amazon S3 V2 connection. Profiles could not run until the **Amazon S3 V2** add-on connector was enabled on the runtime
  environment (403 APP_105060 before). Scorecards funnel through the same gate.
- **Disputed / untested (L-DQ-034):** a later peer note says a Data Profiling setup can use ADLS Gen2 or
  GCS as the results store and read PostgreSQL directly, so S3 is not required. It was not re-tested. If a profile fails
  with APP_105060 naming `amazons3`, enable the S3 V2 connector first. Then check which store your org uses.

---

## 7. Profiling on catalog sources (CDGC)

Catalog-source APIs (create/update multipart, scans, polling) are documented in the CDGC folder:
[CDGC APIs & Auth](../07-catalog-governance-cdgc/01-cdgc-apis-auth.md). The profiling-specific rules:

1. **Configure the capability (L-DQ-043).** A catalog source with only Metadata Extraction and Lineage
   Discovery never profiles, however often it is scanned. Add **Data Profiling** (and **Data Classification** for CLAIRE
   classification) to the catalog source. One source can run all five capabilities (Metadata Extraction, Lineage
   Discovery, Data Profiling, Data Quality, Data Observability) in one scan. When you trigger it over REST, list the
   capabilities explicitly:
   `POST https://idmc-api.<domain>.informaticacloud.com/data360/executable/v1/catalogsource/<id>` with
   `{"capabilityNames":["Metadata Extraction","Data Profiling",...]}`. An empty list gives a misleading 500.
2. **A Data Quality run needs a runtime environment in the source's Scope groups (L-CDGC-143).**
   `{"capabilityNames":["Data Quality"]}` runs and scores once `typeCapabilities` carry the runtime environment in the
   `Data Profiling Scope` and `Data Quality Scope` groups; without it, Rule Profiling fails within a second with no error
   text anywhere in the job API (the old belief that it simply returns 406 is overturned, §8). Failed capability tasks
   still expose little detail over the observable job API: read the Metadata Command Center job view or the agent's
   session logs (item 3).
3. **PARTIAL_COMPLETED profiling (L-DQ-045).**
   - Poll with `GET.../data360/observable/v1/jobs/<jobId>?expandChildren=TASK-HIERARCHY` to see each capability's
     child tasks.
   - Find the failing table in `<agent_home>/apps/Data_Integration_Server/logs/s_cp_*_session.log`. Causes seen: a pgvector
     column; a BigQuery column named `rows` (the profiler's generated SQL chokes on it); transient BigQuery 503s.
   - On a BigQuery catalog source the Data Profiling capability FAILED outright (no message, no agent session) with All
     Rows and with Limit N Rows, even on a connection that path-1 profiles complete on (2026-10-08, L-CDGC-184): profile
     BigQuery with path-1 profiles (section 2, after the connection fix L-DQ-110) and keep catalog profiling for databases.
   - Fix: add a **Profiling Filter Config** row (Exclude, Tables, `schema.table`) to the source's Data Profiling
     capability, PUT the source back (multipart), and re-run **Data Profiling only**. The table stays in the catalog.
4. **Measure coverage with exact facets (L-DQ-046).** `POST.../data360/search/api/v1/search` with
   `X-INFA-SEARCH-LANGUAGE: elasticsearch` and a facet on `core.profiled=True` gives real counts. A wrong field name
   returns **500**, which was once misread as "profiling is broken". Column grain and asset grain differ (671 profiled
   columns versus 1,755 profiled assets in one catalog), so state the grain of every KPI.
5. **Empty tables never profile (L-DQ-042).** Profiling samples rows, so a table with `NumberOfRows = 0`
   keeps `core.profiled=false`, correctly. Compute coverage against tables that hold rows. In one catalog, 97.9% of the
   unprofiled columns sat in empty tables, and the "21% coverage" headline simply tracked each source's share of
   non-empty tables.
6. **Native PostgreSQL connector type limits (L-DQ-040).**
   - It refuses custom enum types (`native type system does not support the data type [<ENUM>]`), plain `json`
     (`could not identify an equality operator for type json`), arrays and `tsvector`;
   - `jsonb` profiled fine on the catalog path.
7. **Casting views (L-DQ-041).**
   - Build a read-only schema of views that cast those columns to text (`enum::text`, `json::text`) and add the
     schema to the catalog source's object selection. Roll back with `DROP SCHEMA <schema> CASCADE`.
   - Catalog-source filters are edited headless through the datasources multipart PUT (see the CDGC folder); for this
     purpose that is probable, untested.
   - Price it first: on a real corpus the views recovered only about **0.25%** of columns. The expected "~100%" never
     materialized, because empty tables, not types, were the gap (L-DQ-042; the old belief is L-DQ-092, overturned).
8. **Classification is not profiling (L-DQ-047).**
   - CLAIRE classification (`core.generatedClassification`) infers a column's category from names and metadata, so it
     covers empty tables too.
   - Profiling computes statistics from rows: `core.average`, `minValue`, `maxValue`, `distinctCount`,
     `nullPercentage`, `standardDeviation`, `patternStatistics`, `topNValueFrequenciesSample`, `inferredDataType`.

   Expect classified counts to exceed profiled counts: in one catalog, 2,582 of 3,136 columns were classified and 671
   profiled.
9. **Governed is not the same as scanned.** Confirm each capability task completed, and that columns show
   `core.profiled=True` and a `lastProfiledState` other than "Not Profiled".

---

## 8. Overturned beliefs (kept so nobody re-learns them)

| Belief | Held | Overturned by | Lesson |
|---|---|---|---|
| "Data Profiling has no API; it only rides a catalog scan" | until 2026-07-25 | Live reads on `<pod>-dqprofile` (2026-07-25/26), then full create/execute (2026-09-24) | L-DQ-085 → L-DQ-019 |
| "Data Profiling routes are SPA-session only" (IDS-SESSION-ID injected by the web app) | 2026-07-09 to 2026-07-25 | `IDS-SESSION-ID` carrying a (v3) login session works for create, update and execute | L-DQ-086 → L-DQ-020 |
| "Profile execution has no public REST verb" (from `/api/v2/job` → UI_13404; dqprofile run guesses → 404) | 2026-09-13 to 2026-09-21 | `POST /profile/<id>/execute`: 8/8 COMPLETED (2026-09-24, again 2026-09-28) | L-DQ-087 → L-DQ-019 |
| "Binding rules to a profile (rule occurrences) is UI-only" | 2026-09-13 | `MAPPLETFIELD` entries in `PUT /profile/<id>` (2026-09-24) | L-DQ-088 → L-DQ-023 |
| "Profile authoring is UI-only" (`POST /v3/objects` = 405) | 2026-09-20 | Package import (2026-09-28) and REST create from a template body (2026-09-24) | L-DQ-089 → L-DQ-025 |
| "Empty profiling is a stuck-job 406 lock, readyToRun=false or ccgf-auth-pep 500s" | June 2026 | The missing `libidn.so.11` explained why every source failed identically | L-DQ-091 → L-DQ-037 |
| "Low coverage (~17%) is caused by the connector skipping json/enum/array; casting views take it to ~100%" | 2026-06-28 to 2026-07-09 | Empty tables were 97.9% of the gap; the views recovered ~0.25% | L-DQ-092 → L-DQ-042 |
| "Catalog scans and profiling are UI-initiated; there is no REST trigger" | 2026-07-05 | `POST /data360/executable/v1/catalogsource/<id>` with `capabilityNames` (used in June, proven again 2026-09-24) | L-DQ-093 → L-DQ-043 |
| "Running only the Data Quality capability returns 406; failed profiling jobs expose no error over REST" | 2026-07-09 | The Data Quality run completes and scores once the Scope groups carry a runtime environment | L-DQ-044 → L-CDGC-143 |
| "ClickHouse cannot be profiled through JDBC V2: object fetches fail JDBC_V2_ERROR_205, NSTRING is refused and 'string' hangs; profile a PostgreSQL copy" | 2026-10-03 to 2026-10-29 | Five JDBC V2 ClickHouse profiles COMPLETED from a cloned JDBC V2 body, up to ALL_ROWS over about 100M rows (2026-11-02) | L-CONN-089, L-DQ-119 (disputed) → L-DQ-128 |

---

## 9. Open questions

- The vendor paths for profiling **query** CRUD (a separate guide, not held).
- Any REST read of per-rule pass rates and scorecard values, beyond the metric-store column metrics.
- Which results stores (S3 V2, ADLS Gen2, GCS) an org can choose, and where that is configured.
- Whether a profile schedule set in the UI survives a v3 export/import.
- Whether `jsonb` and array columns are accepted as profileable fields by the Data Profiling service (path 1), as they
  are on the catalog path.
