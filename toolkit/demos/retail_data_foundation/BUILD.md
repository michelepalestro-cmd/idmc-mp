# Retail Data Foundation: rebuild, step by step

Every step: **why**, **one command**, **expected output**, **verify**, **undo**. Run commands from this folder
(`toolkit/demos/retail_data_foundation`). Every script is a **dry run** until you add `--execute --expect-org <orgIdV3>`
(the core library's org guard). Read first: the [Laws of Headless IDMC](../../../knowledge/00-start-here/02-the-laws-of-headless-idmc.md)
and the [End-to-End Playbook](../../../knowledge/00-start-here/07-end-to-end-playbook-deploy-and-operate-idmc-with-claude.md).
The generic method behind each step is linked from it; this file keeps only what is specific to this demo.

Before anything else, prove the folder works offline (no credentials, no network):

```
python verify/offline_check.py          # expected: 13/13 offline steps passed
```

---

## Step 0. Prerequisites (one time, partly UI)

**Why.** IDMC runs the mappings, CDC and profiling on your Secure Agent; the agent needs the right services and
connectors, and the CRM needs the fields the sync writes.

1. **Secure Agent** running and registered in the org, in a runtime environment whose name you put in
   `config.json` `idmc.runtimeEnvironment`. It must reach the stand-in Postgres (`PG_HOST:PG_PORT`) and the internet.
   Agent services: Data Integration Server, Database Ingestion (Mass Ingestion), Connector Service, plus the
   metadata / profiling services for steps 9-10. Change selections **between** runs: every change rolls services to
   the newest build and queues jobs for about 5 minutes. Never select every connector on a small host (one did,
   pulled about 18 GB and stalled the host). Tool: `python "../../lib/idmc_runtime_selections.py"`.
   KB: [Runtime Environments - Services & Connectors](../../../knowledge/02-secure-agent-connections/02-runtime-environments-services-connectors.md).
2. **Database Ingestion to BigQuery** needs the Simba BigQuery JDBC jars on the agent (copy the set into
   `<agent_home>/apps/Database_Ingestion/ext/connectors/thirdparty`), or the deploy fails with "Failed to load driver
   class com.simba.googlebigquery.jdbc.Driver". KB: [DBMI Targets & Drivers](../../../knowledge/04-cdc-mass-ingestion/03-dbmi-targets-drivers.md).
3. **Google Cloud**: a project (`BQ_PROJECT`), a service account with `roles/bigquery.dataEditor` +
   `roles/bigquery.jobUser`, `roles/storage.objectAdmin` on a staging bucket (`GCS_STAGING_BUCKET`), and its JSON key
   saved **outside** the toolkit (`BQ_KEY_FILE`).
4. **Salesforce** (a Developer Edition org is enough):
   - Contact custom fields: `Rdf_Customer_Id__c` (Text 64, **External ID, Unique**), `Rdf_Tier__c` (Text 16),
     `Rdf_Home_Store__c` (Text 16), `Rdf_Signup_Channel__c` (Text 16), `Rdf_DQ_Score__c` (Number 4,4).
   - Custom object `Rdf_Membership__c` with `Rdf_Membership_Id__c` (Text, External ID, Unique), `Contact__c`
     (Lookup Contact), `Tier__c`, `Status__c` (Text), `Monthly_Price__c` (Currency), `Started_At__c`, `Cancelled_At__c`
     (Date/Time).
   - An API-only integration user (permission set with Read/Create/Edit on these objects and fields) for the CDI
     connection, and a **Connected App** with the client-credentials flow run as that user, for CAI.
   This is Salesforce setup (UI or the Salesforce metadata API), not IDMC.
5. `cp config.example.json config.json`, edit names if you like, and fill the toolkit `.env` ([ENV_KEYS.md](ENV_KEYS.md)).

**Verify.** `python ../../setup/check_setup.py --demo retail_data_foundation` and
`python "../../lib/idmc_session.py" whoami` (one login; note the v3 org id for `--expect-org`).

---

## Step 1. Stand-in source database  (ADAPTED)

**Why.** A PostgreSQL with logical decoding is the operational system IDMC reads, captures and writes back to.

```
docker compose -p rdf -f infra/docker-compose.yml up -d
docker compose -p rdf -f infra/docker-compose.yml exec -T postgres psql -U rdf_app -d rdf_retail < infra/sql/01_schema.sql
python infra/seed.py --customers 500 --apply
```

**Expected.** `generated: {'customers': ~520, 'memberships': ~200, 'orders': ~1300}` then `applied`.
**Verify.** `... psql -U rdf_app -d rdf_retail -c "select count(*) from public.customers"`.
**Undo.** `docker compose -p rdf -f infra/docker-compose.yml down -v`.
Seed a **fresh** database only (the generator numbers foreign keys from 1). Allow the agent's network in `pg_hba.conf`
if the agent is not on the docker host.

## Step 2. Warehouse datasets and tables  (ADAPTED)

**Why.** The mappings write Bulk + Write truncate into pre-created tables; columns added later must be added here.

```
python infra/bq_setup.py            # dry run: renders state/rendered/bigquery_ddl.sql
python infra/bq_setup.py --execute  # runs it with the bq CLI (gcloud auth activate-service-account --key-file ...)
```

**Expected.** `OK CREATE SCHEMA ...` x4, `OK CREATE TABLE ...` x18, one view. **Verify.** `bq ls <BQ_PROJECT>:rdf_gold`.
**Undo.** `bq rm -r -f <BQ_PROJECT>:rdf_land` (and the other three datasets).

## Step 3. Prove the org, resolve ids, create the project folder  (PROVEN resolve / ADAPTED create)

**Why.** Every later step addresses objects by id; ids are resolved **by name in your org** and cached in
`state/ids.json`, never copied from elsewhere (ids copied from another org went stale after a migration).

```
python idmc/00_resolve.py --create-home --execute --expect-org <orgIdV3>
```

**Expected.** `org: v2 ... v3 ...`, `runtimeEnvironment: ...`, `project ... folder ...`, connections "0 match(es)" on
the first run. **Verify.** `state/ids.json` has `org`, `runtimeEnvironment`, `folder.guid`.
**Undo.** Delete the project in Explore (empty it first; teardown does the contents).
Project/folder create uses `POST /public/core/v3/projects` and `/projects/<id>/folders` (ADAPTED); if your org
refuses it, create them in Explore and re-run without `--create-home`.

## Step 4. Connections  (PROVEN except Salesforce: ADAPTED)

**Why.** Five connections, one per consumer: CDI and Database Ingestion each get their own PostgreSQL role and their
own BigQuery connection, because the BigQuery private-key form each accepts differs on some pods.

```
python idmc/01_connections.py plan --offline                                  # bodies, secrets as key names
python idmc/01_connections.py apply --execute --expect-org <orgIdV3>
python idmc/01_connections.py test
python idmc/00_resolve.py                                                     # caches ids + FRS guids
```

**Expected.** `create connection rdf_pg_retail: POST v2:/api/v2/connection` ... `read-back id=... guid=...`; then
`test HTTP 200 OK` for each. **Verify.** `00_resolve.py` prints all five with a `guid` (the FRS `federatedId`).
**Undo.** `python "../../lib/idmc_frs_delete.py" v2-delete connection <id>` (after everything that uses it).
If BigQuery fails with "Invalid PKCS#8 data", cycle `--key-format noheader|stripped|pem|escaped` on that one
connection and re-test (see Gotchas). KB: [Connections](../../../knowledge/02-secure-agent-connections/03-connections-create-test-update-delete.md),
[Connector Notes](../../../knowledge/02-secure-agent-connections/04-connector-notes-bigquery-postgresql-salesforce-jdbc-flat-file.md).

## Step 5. CDC: PostgreSQL -> BigQuery in seconds  (PROVEN)

**Why.** Real-time replicas in `rdf_cdc` (MERGE) for BI; the hot/cold split keeps the busy tables at a 5 s apply
cycle (measured 10-22 s end to end; one combined task gave 15-35 s).

```
docker compose -p rdf -f infra/docker-compose.yml exec -T postgres psql -U rdf_app -d rdf_retail \
    -v cdc_user=rdf_cdc -v cdc_pw="$PG_CDC_PASS" -v owner=rdf_app < infra/sql/02_cdc_prereqs.sql
python idmc/02_cdc.py render                     # state/rendered/dbmi_rdf_cdc_hot.json + _cold.json
python idmc/02_cdc.py create --lane hot --execute --expect-org <orgIdV3>
```

Put the printed numeric `taskId` into `state/ids.json` as `cdc.hot.taskId` (and later the deploy `jobId` as
`cdc.hot.jobId`, the task's FRS id as `cdc.hot.frsId` for teardown), then:

```
python idmc/02_cdc.py deploy --lane hot --execute --expect-org <orgIdV3>
python idmc/02_cdc.py start  --lane hot --execute --expect-org <orgIdV3>
python idmc/02_cdc.py status --lane hot          # deployed -> running
```

Repeat with `--lane cold`. **Verify.** Insert a row (`python infra/traffic.py --count 1 --kind signup`) and see it
in `rdf_cdc.customers` within about 20 s. **Undo.** `teardown/teardown.py run --only cdc ...` then
`teardown/pg_teardown.sql`. KB: [DBMI over REST](../../../knowledge/04-cdc-mass-ingestion/01-dbmi-over-rest-create-deploy-run-stop.md),
[CDC from PostgreSQL](../../../knowledge/04-cdc-mass-ingestion/02-cdc-from-postgresql.md).

## Step 6. The consolidated CDI mappings  (generator, import, tasks: PROVEN; these six specs: ADAPTED)

**Why.** As few mappings as possible: 6 real multi-transformation mappings (one per business flow) replace what was
once about 40 one-table copy tasks; fewer tasks means fewer jobs per lane run and a shorter critical path. The SQL of
the cleanse, survivorship and DQ rules runs inside BigQuery as each mapping's source query (ELT); the agent streams the
result rows to the targets and does the routing, aggregation and the cross-system writes (PostgreSQL, Salesforce).

```
python idmc/03_mappings.py list
python idmc/03_mappings.py build                                   # compile + lint + package with your ids
python idmc/03_mappings.py import --execute --expect-org <orgIdV3> # REUSE first time; --mode OVERWRITE to rebuild
python idmc/03_mappings.py tasks  --execute --expect-org <orgIdV3> # mt_rdf_* created, moved into the folder, tagged
python idmc/03_mappings.py run m_rdf_ingest_customers --execute --expect-org <orgIdV3>   # one job, check it first
```

**Expected.** `OK m_rdf_customer_golden: 8 transformations, 6 links, guid ...` for all six (two lint warnings are
expected: the 1000-char person_key and the PostgreSQL Upsert target); import `SUCCESSFUL`; each task
`id ... mapping ... RE ...`; a run ends state 1 with rows > 0. **Verify.** Run the six in taskflow order once and check
row counts in `rdf_land`, `rdf_staging`, `rdf_gold`, `activation.customer_golden` and Salesforce. Test a **new key** on
every Upsert target (`verify/e2e_check.py` does): a generated Upsert can run green and apply nothing.
**Undo.** `teardown/teardown.py run --only tasks ...`. Change a mapping: edit `idmc/mappings/rdf_specs.py` or
`idmc/sql/*.sql`, `build`, `import --mode OVERWRITE` (same guid, kept in `state/ids.json`).
KB: [How Claude Builds Mappings Headless, route 5](../../../knowledge/03-cdi-data-integration/02-how-claude-builds-mappings-headless.md),
[Mapping Design & Consolidation](../../../knowledge/03-cdi-data-integration/06-mapping-design-consolidation.md),
[The Pipeline-Generation Pattern](../../../knowledge/03-cdi-data-integration/05-the-pipeline-generation-pattern.md).

| Mapping | Flow | Readers |
|---|---|---|
| `m_rdf_ingest_customers` | PG customers, memberships, stores, products -> `rdf_land` | 4 PG |
| `m_rdf_ingest_activity` | PG orders, order_lines, payments, visits -> `rdf_land` | 4 PG |
| `m_rdf_customer_golden` | cleanse -> `stg_customers`; survivorship -> Expression -> `customer_golden` + Router: VALID -> PG `activation.customer_golden` (Upsert), DEFAULT -> `customer_review` | 2 BQ |
| `m_rdf_dq_scorecard` | rule rows -> `dq_results`; Aggregator by dimension + Aggregator overall -> Union -> Expression -> `dq_scorecard` | 1 BQ |
| `m_rdf_sales_facts` | order lines -> `order_line_facts` + Aggregator -> `store_daily_sales`; visits -> `visit_facts` | 2 BQ |
| `m_rdf_crm_sync` | clean-only, count-gated, test-excluded golden records -> Salesforce Contact Upsert on `Rdf_Customer_Id__c` | 1 BQ |

**Pushdown.** These mappings mix ecosystems (PostgreSQL and Salesforce targets) or are small, so they run in agent mode
on purpose. Full SQL ELT applies only to BigQuery-to-BigQuery mappings and was measured slower for small multi-target
ones; if you want to try it on `m_rdf_sales_facts`, follow
[§9 of How Claude Builds Mappings Headless](../../../knowledge/03-cdi-data-integration/02-how-claude-builds-mappings-headless.md)
(three task keys, proof only in the session log).

## Step 7. Lanes: taskflows and the schedule  (PROVEN)

**Why.** The lane orchestration lives in IDMC: a linear taskflow per lane and one schedule. The sign-up lane can be
started on demand.

```
python idmc/04_taskflows.py plan
python idmc/04_taskflows.py apply    --execute --expect-org <orgIdV3>
python idmc/04_taskflows.py schedule --execute --expect-org <orgIdV3>
python idmc/04_taskflows.py run tf_rdf_customer --execute --expect-org <orgIdV3>
python idmc/04_taskflows.py audit
```

**Expected.** `CREATE workflow 'tf_rdf_full' with 6 task(s)`, a schedule created unbound, then bound
(`read-back scheduleId=... -> OK`). **Verify.** `audit` lists the binding; the first scheduled run appears in Monitor.
**Undo.** `teardown/teardown.py run --only schedule,taskflows ...`.
KB: [Taskflows & Schedules](../../../knowledge/03-cdi-data-integration/04-taskflows-schedules.md),
[Performance, Concurrency & Job Caps](../../../knowledge/03-cdi-data-integration/07-performance-concurrency-job-caps.md).

**Optional: an external lane orchestrator.** The source demo also ran a small controller service that started lanes
on events (a sign-up started the customer lane within seconds), coalesced bursts, ran independent tasks of a lane
concurrently (dependency stages, concurrency 4), held per-table conflict locks so an event lane could run beside the
full lane, paused on the monthly job-cap error with one probe after a back-off, and logged every task run to a
warehouse run table. It cut the full lane from about 20 min to 5-6 min and sign-up -> golden from about 16 min (when it
waited behind a full run) to under 1 min, at the price of running Python outside IDMC. Prefer the taskflows above;
if you need event-driven starts, a CAI process can start `tf_rdf_customer` instead. Concurrency limits that apply
either way: the agent's DTM pool (`maxDTMProcesses`, default 2) and the org's monthly job budget (every task run and
every taskflow run is a job; a trial org had a hidden cap of about 10k per month).

## Step 8. CAI real-time sync to the CRM  (package, import, publish: PROVEN; cleanse formulas: ADAPTED)

**Why.** A sign-up should reach the CRM in about a second, not at the next batch lane. CAI calls are not jobs.

```
python idmc/05_cai.py harvest --execute --expect-org <orgIdV3>   # exports one task of the folder for its folder files
python idmc/05_cai.py build                                        # state/packages/rdf_cai.pkg.zip (0600)
python idmc/05_cai.py import  --execute --expect-org <orgIdV3>
python idmc/05_cai.py publish --execute --expect-org <orgIdV3>
python idmc/05_cai.py purge                                        # the package holds the Connected App secret
python idmc/05_cai.py url                                          # copy CAI_RT_BASE into the .env
python infra/traffic.py --count 1 --kind signup --cai              # expect "HTTP 200 in ~1 s ... upserted"
```

**Expected.** import `SUCCESSFUL` with 4 objects; publish waves connector -> connection -> processes, every item
`SUCCESS`. **Verify.** The Contact exists in Salesforce with the external id = the new `customer_id`.
**Undo.** `python idmc/05_cai.py unpublish --execute --expect-org <orgIdV3>`, then `teardown/teardown.py run --only cai`.
The processes are **anonymous** REST (`config.json` `cai.anonymous`); set it to false for a shared org and call them
with a session or basic auth instead. Every writer of a Contact field must apply the same rule (the CAI process,
the batch sync): otherwise the batch silently undoes the real-time result 2-3 minutes later.
KB: [CAI Asset Lifecycle](../../../knowledge/05-cai-application-integration/01-cai-asset-lifecycle-author-publish-unpublish-delete.md),
[CAI Connections & Connectors](../../../knowledge/05-cai-application-integration/03-cai-connections-connectors-e.g.-salesforce-oauth.md).

## Step 9. Data Quality: profiles with rule specifications, address verification  (PROVEN; arg shape ADAPTED)

**Why.** The warehouse scorecard (step 6) measures every lane run; CDQ rule specifications scored by Data Profiling
give the governed, catalog-visible view of the same rules on the source.

1. Rule specifications (UI wall, see below): import or author `rdf_rs_email_validity`, `rdf_rs_phone_completeness`,
   `rdf_rs_not_null` in the project, and put their frsIds into `config.json` `dq.ruleSpecs`.
2. Create ONE Data Profiling profile on `rdf_pg_retail` in the UI (any table) and name it in
   `dq.templateProfileName`: the scripts clone it.

```
python idmc/06_dq.py plan
python idmc/06_dq.py build --execute --expect-org <orgIdV3>
python idmc/06_dq.py run   --execute --expect-org <orgIdV3>    # bills IPUs: 3 + ceil((columns + rules) / 50) subtasks
python idmc/06_dq.py status
python idmc/06_dq.py address --tools                           # read the verify_address input schema
python idmc/06_dq.py address --args-json '<one address, shaped as the schema>' --execute --expect-org <orgIdV3>
```

**Expected.** `create profile rdf_prof_customers ... -> HTTP 201 id ...`; `status` COMPLETED.
**Verify.** The profile's Results tab shows rule pass rates. **Undo.** delete the profiles (teardown prints the calls).
Address verification is one address per MCP call: for a pipeline, read the pre-merge layer (`stg_customers`), queue on
an address hash, cap calls per run (`dq.addressVerification.maxCallsPerRun`) and MERGE results into
`rdf_gold.address_verification` with a first-checked timestamp that is set once.
KB: [DQ Assets](../../../knowledge/06-data-quality-profiling/01-dq-assets-rule-specs-cleanse-dictionaries-verifiers.md),
[Profiling - What Is Headless](../../../knowledge/06-data-quality-profiling/02-profiling-what-is-headless.md),
[DQ Scorecards](../../../knowledge/06-data-quality-profiling/04-dq-scorecards-warehouse-pattern-and-data-profiling-scorecards.md).

## Step 10. Catalog, classification, glossary, lineage  (PROVEN; link lookup ADAPTED)

**Why.** CLAIRE and the catalog answer "what is a golden customer, where does it come from, who may see the e-mail"
only when the sources are scanned and the glossary is linked.

```
python idmc/07_catalog.py render
python idmc/07_catalog.py sources --execute --expect-org <orgIdV3>
python idmc/07_catalog.py scan rdf_cat_pg  --execute --expect-org <orgIdV3>    # one source at a time
python idmc/07_catalog.py scan rdf_cat_bq  --execute --expect-org <orgIdV3>
python idmc/07_catalog.py scan rdf_cat_cdi --execute --expect-org <orgIdV3>    # lineage PG -> BQ -> Salesforce
python idmc/07_catalog.py glossary --execute --expect-org <orgIdV3>
python idmc/07_catalog.py links    --execute --expect-org <orgIdV3>
```

**Expected.** three sources created; each scan job COMPLETED (PostgreSQL may report PARTIAL_COMPLETED); 15 glossary
items registered; up to 21 links. **Verify.** In Data Governance, search `customer_golden`: it shows the term "Golden
Customer Record", PII classifications on e-mail and phone, and upstream lineage to `public.customers`.
**Undo.** `python idmc/07_catalog.py undo-glossary --execute ...`; catalog sources are deleted in the UI.
Classification comes from the scan's Data Classification capability (Auto Classification); promoting CLAIRE
suggestions in bulk is UI. KB: [Catalog Sources](../../../knowledge/07-catalog-governance-cdgc/02-catalog-sources-create-scan-update-purge.md),
[Glossary, Links & Classification](../../../knowledge/07-catalog-governance-cdgc/03-glossary-links-classification.md).

## Step 11. Verify end to end  (ADAPTED)

```
python verify/e2e_check.py                                          # the plan (dry run)
python verify/e2e_check.py --execute --expect-org <orgIdV3> --cai   # sign-up -> CAI -> lane -> golden -> PG -> CRM
python teardown/teardown.py verify-records --execute                # remove the verify.invalid test rows
```

**Expected.** `PASS in ~120-300 s: source=ok, cai=ok, golden=ok, reverse_etl=ok, crm=ok`. The golden row shows the
cleansed values (`Verify Rdf<ts>`, lower-case e-mail, `+1...` phone, tier `Gold`) although the sign-up was typed messy.

## Step 12. Teardown  (core deletes PROVEN; the sequence ADAPTED)

```
python teardown/teardown.py plan
python teardown/teardown.py run --execute --expect-org <orgIdV3>
python teardown/teardown.py clean-local --all-state
```

Order: backup export -> schedule -> taskflows -> CAI -> tasks + mappings -> CDC (then `pg_teardown.sql`) -> profiles ->
glossary -> catalog sources (UI) -> connections -> BigQuery datasets -> the docker volume. A rejected or interrupted
delete may already have removed objects: read back before reporting.

---

## Gotchas (every one cost a failed run before it was learned)

**Connections**
- Native PostgreSQL: `type: TOOLKIT_CCI` + `instanceName: PostgreSQL`; the user key is **`userName`** (with `user` the
  bean reads null and you get an opaque `403 APP_105060 error [null]` in ~7 ms); `authenticationType` must match the
  driver build: `UserIdPassword` on the build seen in 2026-09 (`Standard`, `md5`, `scram` were rejected; an earlier
  build wanted `Database`). `encryptionMethod: noEncryption`. No `schemaName` key.
- A type that the org has never had answers `403 APP_10519 'The connection type is not valid'` (looks like licensing,
  is not): create the first connection of that type in the UI once.
- Update = `POST /api/v2/connection/<id>` with the full body and the secret again (GET masks it). There is no PUT.
- BigQuery private key: never send real newlines; the accepted form differs by consumer and pod (CDI took the PEM
  body without header lines, Database Ingestion needed the PEM). One connection per consumer. Keep `connectorType`
  `Simple` (Hybrid breaks direct-read and pushdown); `useLegacySQLForCustomQuery=false` for standard-SQL sources.
- Salesforce v2 connection: `username`, `password`, `securityToken` are **top-level** fields; API v64 or newer.

**CDC (Database Ingestion)**
- The task creates `public.infa_persistent_<job>` itself (CREATE on public), that table must not be in any publication
  (no FOR ALL TABLES), every captured table needs REPLICA IDENTITY FULL, and the slot must be created after its
  publication. Two tasks never share a slot; an idle slot retains WAL (cap it).
- `runtimeEnvironment` in the task body is the runtime environment **name**, `location` must be a project; ids on the
  ingestion host are numeric (a guid gives a routing 404); deploy returns a **new** job id; `job/start`, not `resume`,
  on a freshly deployed job (409).
- An id-bearing action endpoint acts on an empty body: an empty POST to `task/deploy/<id>` deploys. Never "probe" one.
- A TEXT primary key breaks the initial load ("Field Schema.column value error: no columns"): BIGINT keys everywhere.
- Internal control tables with NOT NULL text columns failed the initial load: they live in schema `control`, which
  no publication includes.
- There is no update verb: change = delete + create (or edit in the UI). Never set datatype rules on a BigQuery-target
  task (a half-applied rule change killed a running job). Fractional seconds ending in zero arrived shifted
  ('.495670' as '.049567') on about 10 % of CDC timestamps in one org: compare with the batch tables before trusting
  sub-second CDC times.
- Hand-over: when a slot moves to another task or org, STOP (do not undeploy) the old job; rollback = stop new, resume old.

**Mappings**
- BigQuery write disposition must be in the target adapter's runtime attributes (`writeDisposition` +
  `writeMode Bulk`); `WriteOptions.truncate` alone silently appends. Write truncate skips an empty load, so a target
  whose source fell to 0 rows keeps stale rows: truncate it yourself when a success reports 0 rows.
- At most about 5 BigQuery readers per mapping on a small agent (7-8 exhausted the DTM heap); select only needed
  columns; STRING reader precision 256.
- Never feed one source to a Joiner's master and detail (the session hangs with no error). Expression OUTPUT ports
  cannot reference other OUTPUT ports (use a VARIABLE port, as `EXP_SC.v_rate` does).
- Strip comments and non-ASCII from custom SQL (the BigQuery reader fails with "missing CR"); `03_mappings.py` does it.
- A BigQuery DATE target column needs the STRING `'YYYY-MM-DD 00:00:00'` (this blueprint uses TIMESTAMP columns).
- A generated PostgreSQL Upsert target can run green and apply 0 rows unless the writer's `UpdateMode = Update Else
  Insert` is set (the generator adds it); always test a new key.
- Retarget a finished mapping by rebuilding its package and importing OVERWRITE under the same guid; POSTing new
  target parameters to its task returns 200 and changes nothing.
- A failed or stopped run leaves `Temp_View<epoch>` objects in the query source's dataset: drop them.
- Every generated BigQuery target polls its load job every 1 s (the writer default of 10 s cost up to ~9 s per target).
- A new task lands in `Default`: move it with FRS `MoveEntities` (the v3 move route answers 404). Two forms of the FRS
  path were recorded (`/frs/api/v1/MoveEntities` and `/frs/v1/MoveEntities`); the helper tries both.
- Refresh the spec field lists from `INFORMATION_SCHEMA` after any column change, or the column lands NULL silently.

**Taskflows and schedules**
- Linear taskflows only: an API-created advanced taskflow imports but cannot be published (`AvrEntryNotFoundFault`).
- Two linear taskflows that share tasks cannot overlap (`REPO_17314`): do not start `tf_rdf_customer` during
  `tf_rdf_full`.
- v2 schedule times are pod-local but labelled `Z`; set both `startTime` and `startTimeUTC`
  (`config.json idmc.podOffsetHours`, or let the core derive it from an existing schedule).
- A task-level schedule is hidden in the task list: `audit` both levels before any cutover.
- Activity-log `startTime` is pod-local too: use `startTimeUtc` / `endTimeUtc` when you measure latency.

**CAI**
- Asset paths are `Explore/<project>/<folder>/<name>.<TYPE>.xml`; publish waves connector -> connection -> processes;
  a 202 is only submission (read every `itemDetail[].itemState`); the runtime serves the old version for ~20 s.
- The app connection is imported with `encrypted="false"` attributes: the client secret then travels in clear text in
  every later export of that connection. Keep exports out of shared folders, `purge` the built package, or build with
  `--no-secrets` and type the values into the connection in Application Integration.
- OAuth token parameters go in a form-encoded **body**, not the URL. The built-in Salesforce connector needs
  ModifyMetadata (breaks least privilege): this blueprint uses its own REST service connector.
- CAI omits empty outputs: read optional outputs with a default. Callers should fail open with a short timeout.
- Two calls for the same record within a second race (one returns 500): idempotent upserts on the external id make the
  retry safe.
- A full Salesforce dev org (about 5 MB) answers `STORAGE_LIMIT_EXCEEDED`: size the seed and purge test records
  (`teardown.py verify-records`); emptying the recycle bin is SOAP-only.

**Data Quality and catalog**
- The profiling host rejected the v2 session id on one pod (401 "...processing JWT"): the scripts use the v3 session.
- char(n), jsonb and vector columns: the first is refused, the others abort the whole profiling task.
- A catalog source scoped to one schema silently drops the others: list every schema in the filter. BigQuery filters
  were needed in both `<ds>.*` and `<project>.<ds>.*` forms. Scan one source at a time, with the metadata services
  selected only for the scan window. Set "Metadata Change Option" = Delete before a re-scan. A scan can blank curated
  descriptions: re-run the glossary links after each scan. A Published term can report "deleted" and stay: read back.

**Operations**
- One login per session; a few rejected logins lock the account (`IDS_086`, admin unlock only). Never run two
  sessions or watchers with different passwords against one account.
- Every task run and taskflow run is a job against the monthly budget, invisible headless on some licences: the
  6-task full lane every 4 h is 42 jobs a day; the sign-up lane is 4 jobs per run.

## UI-only walls (no API does these; click path given)

| Wall | Click path |
|---|---|
| First connection of a connector type in a new org | Administrator > Connections > New Connection > pick the type > Save (then REST manages it) |
| Secure Agent install and registration | Administrator > Runtime Environments > Download Secure Agent, install on the host, register with the install token |
| CDQ rule specification logic (no create verb, 405) | Data Quality > New > Rule Specification > build the rule > Save (or import a package that holds one) |
| The first Data Profiling profile (the clone template) | Data Profiling > New > Data Profiling Task > connection `rdf_pg_retail` > a table > all columns > Save |
| Deleting a catalog-source definition | Metadata Command Center > Catalog Sources > select > Delete |
| Bulk-accepting CLAIRE classification suggestions, stakeholders, access policies | Data Governance > the asset > Classifications / Stakeholders |
| Publishing an advanced (parallel) taskflow | Data Integration > New > Taskflow (designer) > Publish (this blueprint uses linear taskflows instead) |
| Salesforce custom fields, Connected App, integration user | Salesforce Setup (or the Salesforce metadata API) |

## Other warehouses

BigQuery is the proven path. Another warehouse means: new connections in step 4 (and a JDBC V2 or native connector
for the CDC target), the SQL in `idmc/sql/` rewritten in its dialect, the target kinds in `rdf_specs.py` (a JDBC V2
target writes into the database bound on its connection and ignores the schema part of the object, and needs
`Pre SQL: TRUNCATE TABLE <t>` instead of a write disposition), and new catalog-source templates. Budget a day.

## PROVEN / ADAPTED ledger

| # | Item | State |
|---|---|---|
| 1 | Stand-in Postgres, schema, seed, traffic (this schema) | ADAPTED |
| 2 | BigQuery DDL + bq CLI runner | ADAPTED |
| 3 | Org proof + id resolution by name | PROVEN |
| 4 | Project/folder create via v3 | ADAPTED |
| 5 | PostgreSQL native connection (userName, UserIdPassword) | PROVEN |
| 6 | PostgreSQL CDC-role connection | PROVEN |
| 7 | BigQuery V2 connections (CDI + Database Ingestion, key forms) | PROVEN |
| 8 | Salesforce v2 connection body | ADAPTED |
| 9 | CDC prerequisites SQL (publications, slots, replica identity, role) | PROVEN |
| 10 | Database Ingestion create / deploy / start / status | PROVEN |
| 11 | Hot/cold CDC split | PROVEN |
| 12 | Mapping generator (spec -> IMF -> package), lint | PROVEN |
| 13 | v3 import REUSE / OVERWRITE same guid | PROVEN |
| 14 | Mapping task create + FRS move + tag | PROVEN |
| 15 | The six rdf mapping specs | ADAPTED |
| 16 | Linear taskflows, schedule create/bind, audit | PROVEN |
| 17 | CAI package layout, import, publish waves | PROVEN |
| 18 | CAI service connector (token + upsert) and event process | PROVEN |
| 19 | CAI contact-process cleanse formulas | ADAPTED |
| 20 | Data Profiling profiles with rule bindings (clone, PUT, execute) | PROVEN |
| 21 | verify_address MCP call (arguments shaped by its schema) | ADAPTED |
| 22 | Catalog sources PG / BQ / IICS + one-at-a-time scans | PROVEN |
| 23 | Glossary create / undo with registry | PROVEN |
| 24 | Term links | PROVEN |
| 25 | Asset lookup for links by exact name (search) | ADAPTED |
| 26 | Warehouse DQ rules + scorecard (rule SQL, thresholds) | PROVEN |
| 27 | Golden record survivorship + clean-only + count gate + test exclusion | PROVEN |
| 28 | Reverse ETL into PostgreSQL from a mapping (Upsert writer attributes) | PROVEN |
| 29 | Salesforce Upsert target from a generated mapping | PROVEN |
| 30 | End-to-end check script | ADAPTED |
| 31 | Teardown sequence script | ADAPTED |
| 32 | Core deletes used by teardown (v2-delete, FRS delete, DBMI stop/undeploy/delete, unpublish) | PROVEN |
| 33 | Address-verification pipeline shape (hash queue, cap, MERGE) | ADAPTED |

22 PROVEN, 11 ADAPTED. PROVEN means proven in an earlier, non-generic form; re-verify each call in your org.
