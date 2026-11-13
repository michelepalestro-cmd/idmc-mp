# DBMI Targets & Drivers

**Answers:** Which DBMI targets are proven; how to install the Simba BigQuery JDBC driver set; which private-key form each engine accepts; how GCS staging must be granted; PostgreSQL target edge cases; where JDBC V2 driver jars go for CDI; what a BigQuery CDC target dataset contains and how consumers should treat it.

**Read when:** before deploying a DBMI task to a new agent or target, when a deploy fails on a driver or key, or when building consumers on a CDC target dataset.

**Key rules:**
- A BigQuery target needs the Simba JDBC set on the agent and an agent restart; the connection testing green proves nothing for DBMI (L-DBMI-033).
- Give DBMI its own BigQuery connection and probe the key form per pod and engine (L-DBMI-034; the exact PEM form is disputed, L-DBMI-035).
- The connection's service account needs write, list and delete on the GCS staging bucket (L-DBMI-036).
- A CDC target dataset also holds `<table>_EXT` and `INFORMATICA_CDC_RECOVERY`: leave them alone and filter them out of BI, catalog and counts (L-DBMI-050, L-ENV-082).
- Never let several native-CDC streams share one target dataset with the same source schema name (L-ENV-075).

**Related:** [DBMI over REST](<01 DBMI over REST (create, deploy, run, stop).md>) · [CDC from PostgreSQL](<02 CDC from PostgreSQL.md>) · [Serving Outputs to BI and Apps](<../03 - Data Integration (CDI)/10 Serving Outputs to BI and Apps (freshness, latency, reverse ETL).md>) · [Secure Agent & Connections](<../02 - Secure Agent & Connections/>) · [Lessons: Mass Ingestion & CDC](<../13 - Lessons Learned/04 Mass Ingestion & CDC.md>)

**Last verified:** 2026-10-08

> A BigQuery target for Database Ingestion needs three things: the Simba BigQuery JDBC driver set on the agent (about 73 jars plus `GoogleBigQueryJDBC42.jar`, then an agent restart), a GCS staging bucket the connection's service account can write, and a private key in the form the Simba driver accepts.
> On one pod the CDI BigQuery V2 connector and DBMI's Simba driver wanted different key forms, so give DBMI its own BigQuery connection. The exact PEM form Simba took is disputed.
> A PostgreSQL target needs no staging. JDBC V2 targets (for example Apache Doris over the MySQL protocol) are a CDI path with their own driver folder, not a DBMI connector. Microsoft Fabric was not a DBMI target in July 2026.

---

## 1. Target matrix (as observed)

| Target | Status | Staging | Driver on the agent | Notes |
|---|---|---|---|---|
| Google BigQuery | **proven** (CDC and initial load, 2026-09-26 to 2026-09-29) | GCS bucket (`target.bucket` / `directory`) | Simba BigQuery JDBC set (section 2) | typed tables merged on the primary key; audit columns prefixed `INFA_` |
| PostgreSQL (relational) | **proven** (initial load, 2026-09-22) | none: a local file plus JDBC COPY | ships with the agent | 24 tables / 682,385 rows in 43 s; see the edge cases in section 5 |
| Microsoft Fabric Data Warehouse | **rejected** (2026-07-06/07) | n/a | n/a | the DBMI CLI answered `No enum constant com.informatica.dbmicli.domain.Vendor.FABRIC`; use CDI mapping tasks or land files (L-DBMI-039). The target list changes by release: check the current vendor list before relying on this row |
| JDBC V2 targets | **not a DBMI connector** per the product availability matrix (v39.1) | n/a | the JDBC V2 jars (section 6) | JDBC V2 supports CDI and CDQ; DBMI and CDC need native connectors |

Source side: use the **native** PostgreSQL connector for DBMI and CDC; JDBC V2 does not support Database Ingestion (checked 2026-06-27).

## 2. The Simba BigQuery JDBC driver set (L-DBMI-033, 2026-09-28)

**Symptom:** `task/deploy` ends `failed`, and the task log says `Failed to load driver class com.simba.googlebigquery.jdbc.Driver`. The connection itself can test green, because CDI's BigQuery V2 connector does not use this driver.

**Where the jars go** (on the agent that runs the task):

| Folder | What | Evidence |
|---|---|---|
| `<agent_home>/apps/Database_Ingestion/ext/connectors/thirdparty/` | the Simba BigQuery JDBC set: about 73 jars (72 plus `GoogleBigQueryJDBC42.jar`) | a mirrored set made the deploy work (2026-09-28) |
| `<agent_home>/apps/Database_Ingestion/<version>/dbmi_libs/libs/` | `GoogleBigQueryJDBC42.jar` again (`<version>` is the DBMI package directory, for example `547.3.1`) | same run |

Procedure, copying from an agent that already runs DBMI to BigQuery (the original download source of that set was not recorded):

```bash
SRC=<agentA_home>/apps/Database_Ingestion
DST=<agentB_home>/apps/Database_Ingestion
VER=<version>                                   # ls $DST to see the package directory
sudo mkdir -p "$DST/ext/connectors/thirdparty"
sudo cp -p "$SRC"/ext/connectors/thirdparty/*.jar "$DST/ext/connectors/thirdparty/"
sudo cp -p "$SRC/$VER/dbmi_libs/libs/GoogleBigQueryJDBC42.jar" "$DST/$VER/dbmi_libs/libs/"
sudo chown -R <agent_user>:<agent_user> "$DST/ext/connectors/thirdparty" "$DST/$VER/dbmi_libs/libs/GoogleBigQueryJDBC42.jar"
sha256sum "$SRC/ext/connectors/thirdparty/GoogleBigQueryJDBC42.jar" "$DST/ext/connectors/thirdparty/GoogleBigQueryJDBC42.jar"
sudo systemctl restart <agent_service>          # the classloader caches the classpath at start
```

Then deploy the task again. Restarting only the task does not help; restart the **agent**, because the classloader caches at start. The copy and the restart took about 2 minutes together; check that the engines are RUNNING again before you deploy
(a start in the first minutes can fail with 'Mass Ingestion service could not find active agents': wait and retry once, L-DBMI-052).

**Keep the proven jar set** (L-DBMI-053). A freshly downloaded Simba set (1.8.1.x, 74 jars) loaded the driver, but an
initial load then ended `warning`: small tables landed and every larger table failed in the GCS staging writer
('Broken pipe', 'Failed while waiting to get the write lock', `NoSuchFileException` on a `W-TMP` file). Copy the set
from an agent where DBMI to BigQuery is proven rather than mixing in a newer download, and judge any driver change by an
initial load of your largest table.

Related agent facts (see [Secure Agent & Connections](<../02 - Secure Agent & Connections/>)):

- DBMI needs the Mass Ingestion (databases) service selected on the runtime environment, with `Database_Ingestion` and `MassIngestionRuntime` RUNNING in `GET /api/v2/agent/details/<agentId>` (L-DBMI-041).
- Every service-selection change can also roll DIS, Mass Ingestion and the connector service to their newest versions; a lane can queue for about 5 minutes behind that rollover. Re-check your jar folders after an upgrade.

## 3. The private key: give DBMI its own connection (L-DBMI-034, 2026-09-28)

**Symptom:** after the driver is fixed, the deploy fails with `[Simba] Invalid PKCS#8 data`.

What was observed:

| Org (pod domain) | CDI BigQuery V2 connector | DBMI Simba JDBC | CLAIRE data gateway |
|---|---|---|---|
| Org A, on a `dmp-us` pod (2026-09-22 to 2026-09-26) | accepted the stripped base64 body, and also the full PEM with literal `\n` escapes; real newlines failed | ran on the one shared connection holding the full PEM with literal `\n` escapes | rejected stripped base64 (`Invalid PKCS#8 data`); needed the full PEM with literal `\n` escapes |
| Org B, on a `dm-us` pod (2026-09-28) | accepted **only** the PEM body without its header and footer lines (or stripped base64); rejected the escaped form with `Invalid PKCS#8 data` | rejected the header-less form (`[Simba] Invalid PKCS#8 data`); accepted a PEM form (which one is disputed, below) | not tested |

So:

1. Keep **one BigQuery connection per consumer**: the CDI connection in the form CDI accepts, and a DBMI-only connection (same service account and project) in the form Simba accepts. Point the DBMI task's `target.connection` at the DBMI-only one.
2. Find each form with a **probe loop**. For each candidate (stripped base64, full PEM, PEM without header, one-line PEM, PEM with literal backslash-n):
   - `GET /api/v2/connection/<connId>`, set `connParams.privateKey`, drop the audit fields, and `POST /api/v2/connection/<connId>` the full body back;
   - `GET /api/v2/connection/test/<connId>` (the CDI side);
   - `POST.../dbmi/public/api/v2/task/deploy/<taskId>` and poll the job status (the DBMI side).
   Keep the first form that passes the consumer you are fixing. If none passes both, restore the last known-good value on the shared connection and split.
3. The v2 connection GET returns the key **masked**, so every update must re-supply it. Read the key from its file at run time and never print it.
4. Never paste a key with raw newlines into a hand-written JSON string. Build the body with a JSON library.

### The disputed part (L-DBMI-035, disputed 2026-09-28)

The reports say DBMI took the "escaped PEM" (literal backslash-n). But the script that created the DBMI-only connection applied a replace that is a byte-for-byte no-op (`"\n"` → `"\n"`), so the value it sent was most likely the unmodified PEM from the key file, JSON-encoded normally (newlines travel as `\n` escapes in JSON and arrive as real newlines). An earlier finding on the other pod said the v2 connection API needed escaped newlines. **Treat the exact form as unknown and probe it on each pod.**

## 4. GCS staging for BigQuery (L-DBMI-036)

- DBMI loads BigQuery through a GCS bucket: `target.bucket`, `target.directory`, and the matching `targetBucket` and `targetDirectory` custom properties. Give each task its own directory (for example one per split task).
- Grant the connection's service account write, list and delete on that bucket (for example a bucket-scoped storage admin or object admin role), and verify with a real write, list and delete before the first run (2026-06-29).
- A service account without `storage.buckets.create` cannot create the bucket itself (403). Create it with an owner identity, then grant the service account (2026-09-22).
- The dataset (`target.schema`) must exist; DBMI creates the tables in it.

## 5. PostgreSQL target and initial-load edge cases (L-DBMI-037, L-DBMI-038, 2026-09-22)

- A relational PostgreSQL target is written through a local file and JDBC COPY, so no cloud staging is needed. That makes a PostgreSQL-to-PostgreSQL initial load the quickest end-to-end proof of a new agent.
- `selectionRules` take include and exclude: `[{"include":"*"},{"exclude":"<control_table>"}]`.
- Tables with a **character primary key** failed the UNLOAD with `com.infa.rat.dbmi.payload.cdc.helper.VerifyValueException: Field Schema.column value error: no columns` (a read-side failure; the bigint-keyed tables in the same task loaded). Exclude them or add a numeric surrogate key at the source.
- On a PostgreSQL target, the COPY dropped some NOT-NULL text columns of two internal control tables, causing NOT-NULL violations. Exclude such tables.
- DBMI re-reads the live source on each initial load, so row counts rise slightly between reruns.

## 6. JDBC V2 targets: the MySQL driver for Apache Doris (CDI path)

A MySQL-protocol warehouse such as Apache Doris is reached through a **CDI** JDBC V2 connection, not a DBMI task. The driver jar goes on the agent (2026-09-28):

| Folder | Why |
|---|---|
| `<agent_home>/ext/connectors/thirdparty/informatica.jdbc_v2/common/` | the canonical JDBC V2 driver folder used by connection tests and task runs |
| `<agent_home>/ext/deploy_to_main/bin/rdtm-extra/jdbc_v2/` and `<agent_home>/ext/deploy_to_main/bin/rdtm/javalib/` | staged copies that survive DIS auto-upgrades (earlier finding) |
| the catalog scanner's own driver folders | catalog scans read separate folders |

Restart the connector service (or the agent) after staging, because the connector caches its classpath. The JDBC V2 connector ignores `truncateTarget`; use a pre-SQL `TRUNCATE TABLE <t>` in the task runtime attributes instead (see [Data Integration (CDI)](<../03 - Data Integration (CDI)/>)).

## 7. Moving targets and drivers to another agent or org (checklist)

1. Mirror the Simba set and `GoogleBigQueryJDBC42.jar` into the new agent's DBMI folders, restart the agent, and check the engines.
2. Create a **DBMI-only BigQuery connection** in the new org and probe the key form with a deploy.
3. Create or verify the GCS bucket grant for that connection's service account.
4. Stage any JDBC V2 driver jars for CDI tasks in the canonical folder.
5. Only then deploy the CDC task. A deploy failure during a cutover costs freshness; one such failure cost about 5 minutes (see [CDC from PostgreSQL](<02 CDC from PostgreSQL.md>)).
6. Importing initial-load tasks before the target agent has a Database Ingestion engine failed vendor validation with 403 and rolled back the whole import. Enable the engine first, or leave these tasks out of the package and create them later (L-DBMI-032).

## 8. Diagnosing a failed deploy or a dead job

Read the newest task log first: `<agent_home>/apps/Database_Ingestion/logs/tasks/*_<jobId>-*.log`, root-readable; grep ` ERROR ` (L-DBMI-030).

| Symptom | Check | Fix |
|---|---|---|
| `failed` right after deploy; `Failed to load driver class com.simba.googlebigquery.jdbc.Driver` | the jar count in `<agent_home>/apps/Database_Ingestion/ext/connectors/thirdparty/` (about 73) and `GoogleBigQueryJDBC42.jar` present in `<version>/dbmi_libs/libs/` | copy the set, fix the owner, restart the agent (section 2) |
| `[Simba] Invalid PKCS#8 data` | the key form on the connection the task uses | a DBMI-only connection; probe loop (section 3) |
| staging or GCS permission errors | the service account's rights on the bucket and directory | grant, then verify with write, list and delete (section 4) |
| status stuck in `processing_deploy` | engine state in `GET /api/v2/agent/details/<agentId>`; a service rollover after a selection change | wait for the engines, then deploy again |
| import of an UNLOAD task: `Cannot validate vendor... 403 FORBIDDEN` | is `Database_Ingestion` RUNNING on the target agent? | enable it first, or create the task later (L-DBMI-032) |
| UNLOAD fails with `VerifyValueException... no columns` | the table's primary-key type | exclude it, or add a numeric surrogate key (section 5) |
| a CDC job dies with `Value of type... cannot be assigned to` | a datatype rule on the task | redeploy with `datatypeChangeRules=[]` (L-DBMI-023) |
| a CDC job stops with `100032` / `backendError` / `rateLimitExceeded` | a transient warehouse error | `job/resume` (bounded; L-DBMI-028) |
| the deploy works but the target stays empty | the slot and publication on the source; the table selection rules | see [CDC from PostgreSQL](<02 CDC from PostgreSQL.md>) |

## 9. Target-side conventions (BigQuery)

- **Current state, not a change log:** the tables are typed and merged on the primary key; each row carries audit columns with the `INFA_` prefix (`auditColumnsPrefix`). Build consumer views over them, with the same names and SQL as any batch marts they replace.
- **Re-baselines rewrite the tables:** a CDC_COMBINED task started with LATEST (a first start, a redeploy, or a handover to another org) re-runs the initial unload into the existing tables before it streams. Readers see a short gap (about 3 minutes in the runs measured), not wrong data.
- **One staging directory per task** (`target.directory` and `targetDirectory`), so split tasks do not collide.
- **The deploy needs project-level metadata:** it runs `SELECT ... FROM region-<location>.INFORMATION_SCHEMA.SCHEMATA`, so an identity with dataset-level roles only gets 403; grant project-level metadata read or use an identity that has it (L-DBMI-054).
- **Cost per cycle:** every apply of a changed table is one SCRIPT job (CREATE TEMPORARY TABLE from the `_EXT` table, then MERGE) billed 30 MiB at the 10 MiB per-table minimum, plus a 20 MiB MERGE into `INFORMATICA_CDC_RECOVERY` per cycle; two tasks under test traffic billed about 21 GiB (21,560 MiB) in 2 h 40 min. Put high-churn tables on a long-cycle task and count bytes billed with jobs.list (L-DBMI-055).
- **Views in another dataset need authorization:** when consumers read the CDC tables through views in a separate dataset, authorize that view dataset on the CDC dataset (and on any dataset the views join), and grant the reader identity on the view dataset only (2026-09-26).
- **Timestamps:** repair the fractional-seconds defect in those views (L-DBMI-024), not with datatype rules.
- **DBMI's own tables live in the target dataset** (L-DBMI-050, L-ENV-082). Each replicated table gets a managed table plus a `<table>_EXT` external table (the staging twin over the GCS files the job writes), and the dataset holds an `INFORMATICA_CDC_RECOVERY` table (the job's restart bookkeeping). These change without new business rows. Exclude `INFORMATICA%` and `%_EXT` from BI sources, catalog filters, table counts, freshness fingerprints and consumer grants; never drop or rewrite them while the job is deployed; derive any "replicated tables" list from the dataset instead of hard-coding it.
- **Change detection for consumers:** `SELECT MAX(last_modified_time) FROM <cloud-project>.<cdc-dataset>.__TABLES__ WHERE table_id NOT LIKE 'INFORMATICA%' AND table_id NOT LIKE '%_EXT'`, gated by a minimum gap, a maximum age and a daily budget ([Serving Outputs to BI and Apps](<../03 - Data Integration (CDI)/10 Serving Outputs to BI and Apps (freshness, latency, reverse ETL).md>) §4).
- **Native warehouse CDC beside IDMC** (L-ENV-075). If a cloud-native CDC service (for example GCP Datastream) lands into the same project: several streams that share one target dataset and the same source schema name (for example `public`) write into the same table names, so rows from different source databases merge with the last writer winning, and the per-stream heartbeat table is overwritten. Give each source its own dataset (`<domain>_<source>_raw`) and union them in a view; fixing it later means recreating the streams and backfilling. A stream replicates only the tables in its include list (tables created later do not flow until the configuration changes), so check row counts per expected table, not only stream state. A stream whose source was merged away can end FAILED_PERMANENTLY with only a stale heartbeat row; retire it after confirming nothing reads it. This is the rule IDMC follows for colliding schema names too (L-CDI-098).

## 10. Overturned and disputed

| Belief (dates) | Status now | Lessons |
|---|---|---|
| "The BigQuery key must be the full PEM with literal `\n` escapes for every engine" (2026-09-24/25, one pod) | **Disputed.** On another pod CDI rejected that form while DBMI needed a PEM form; probe per pod and engine, and split connections | L-DBMI-034, L-DBMI-035 |
| "DBMI to BigQuery is blocked" (2026-09-22) | it was a missing GCS bucket and grant, not a capability limit | L-DBMI-036 |

## 11. Lessons in this doc

L-DBMI-023, L-DBMI-024, L-DBMI-028, L-DBMI-030, L-DBMI-032 to L-DBMI-039, L-DBMI-041, L-DBMI-052 and L-DBMI-053. Full text: [Lessons: Mass Ingestion & CDC](<../13 - Lessons Learned/04 Mass Ingestion & CDC.md>).
