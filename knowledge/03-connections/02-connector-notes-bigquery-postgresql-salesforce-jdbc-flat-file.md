# Connector notes: BigQuery, PostgreSQL, Salesforce, JDBC and flat file

**Answers:** Which field names, key formats, object paths and driver locations does each connector need? Which
connector traps silently lose data (truncation, ignored truncates, a failed read that empties a target)? How do I keep
a small CRM target inside its storage? What does the SharePoint Online connector read and download?

**Read when:** before creating a connection of one of these types, when a run lands the wrong rows or none, and before
designing a reload or a reverse-ETL into a SaaS target.

**Key rules:**
- The BigQuery private-key form differs by consumer (CDI, Database Ingestion, the Data Gateway) and by pod: test each
  and keep one connection per consumer (L-CONN-035, L-CONN-036).
- The BigQuery V2 writer cuts STRING ports at 255 characters; a JSON-typed target column keeps the text (L-CONN-044).
- PostgreSQL objects are addressed `<schema>/TABLE/<table>` (L-CONN-028).
- `truncateTarget` is not a reload switch, and a `Pre SQL` truncate runs before the read, so a failed read leaves an
  empty target (L-CONN-032, L-CONN-056, L-CDI-208).
- A rolling reverse-ETL window can keep a small Salesforce org full: size the window to the org, purge, empty the
  Recycle Bin and probe headroom daily (L-CONN-088).
- The CDI SharePoint Online connector needs a refresh token minted for SharePoint, not Microsoft Graph: a Graph-scoped
  one passes Test Connection and reads 0 objects, so prove access with an object browse (L-CONN-100, L-CONN-101).

**Related:** [03 Connections](01-connections-create-test-update-delete.md) ·
[Source & Target Gotchas](../04-mappings/08-source-target-gotchas.md) (task-side write options) ·
[DBMI Targets & Drivers](../06-cdc-ingestion/03-dbmi-targets-drivers.md) ·
[CAI Connections & Connectors](../07-app-integration/03-cai-connections-connectors-salesforce-oauth.md) (real-time Salesforce writes) ·
[Lessons: Secure Agent & Connections](lessons.md)

**Last verified:** 2026-11-03 (evidence 2026-06-27 to 2026-11-03).

> Per-connector field names, formats and traps, each with the dates of its evidence. Catalog scans of these sources:
> [Catalog Sources](../09-catalog-lineage/02-catalog-sources-create-scan-update-purge.md).

Evidence dates are given per section as the range of the proofs behind it. A connector build or pod can behave
differently from the one that produced a proof; re-test on yours.

---

## 1. PostgreSQL (native CCI connector)

Evidence: 2026-06-27 to 2026-09-26.

**Body** (L-CONN-027, 2026-09-23):

```json
{"@type": "connection", "name": "<name>", "type": "TOOLKIT_CCI", "instanceName": "PostgreSQL",
 "runtimeEnvironmentId": "<reId>",
 "connParams": {"hostName": "<host>", "port": "5432", "database": "<db>",
                "userName": "<user>", "password": "<from file>",
                "authenticationType": "<see table>", "encryptionMethod": "noEncryption"}}
```

Connector GUID `com.informatica.adapter.postgres`. There is no schema parameter; do not send `schemaName`. Earlier
proven bodies also carried `tlsv1_2: false`, `sslv3: false`, `validateServerCertificate: false`, `agentId`,
`agentGroupId` and `orgId`.

**Key names drifted between connector builds and pods** (all tested 200 at the time):

| Date | `authenticationType` | User key | Other keys | Note |
|---|---|---|---|---|
| 2026-06-27 | `Database` (`Basic` rejected: 'not a valid choice') | `userName` | TLS flags false | Copied from a UI-created connection |
| 2026-07-07 | `UserIdPassword` | `userName` (`user` gave NPE 'error [null]') | | After a DataDirect driver rename |
| 2026-07-26 | `Standard` (mandatory) | `user` | both `databaseName` and `database` | Another pod; `database` was the last field the validator demanded |
| 2026-09-23 | (present) | `userName` | the set in the body above | Parameter list of a working connection |

Copy the key set from a working connection of the same type on your pod (L-CONN-003, 2026-09-16).

**Object paths** (L-CONN-028, 2026-09-23): as a task's source or target object use `<schema>/TABLE/<table>` or
`<schema>/VIEW/<view>`. `public/<table>` fails with SDK_APP_COM_20000 'Incorrect list of path is populated with size: 1';
`<table>`, `<schema>.<table>`, quoted names and `<db>.<schema>.<table>` give 'Object(s) [X] not found' (a cache-only
lookup: the database's statement log showed no query). With the path form, a connection created over REST and never
browsed in the UI resolves objects at run time.

**Text and JSON** (L-CONN-029, 2026-09-26): in template mapping tasks the connector typed every string as `string(255)`
and truncated silently, and it cannot land `jsonb`/`json`; `overriddenFields` precision overrides returned 400. Land such
tables from a view in a source schema that casts `jsonb::text`, via `<schema>/VIEW/<table>`, into a JSON-typed warehouse
column (section 2.4).

**Native versus JDBC V2** (L-CONN-030, 2026-07-08): per the Product Availability Matrix v39.1, JDBC V2 supports DI and DQ
but not Database Ingestion; use the native connector for CDC and for cataloging (JDBC catalog scans of PostgreSQL ended
COMPLETED WITH ERRORS and dropped sequences, constraints and foreign keys).

**Drivers for scans** (L-CONN-031, 2026-07-08): the Test path and the catalog scanners read JDBC drivers from different
folders. On a minimal agent put the PostgreSQL jar in `<agent_home>/ext/connectors/thirdparty/informatica.jdbc_v2/common/`
and in the scanner folders (`Metadata_Foundation_Agent/.../data/browse/drivers/` plus a `postgresql` subfolder,
`Metadata_Platform_Service/.../lib/drivers/`, `Database_Ingestion/.../dbmi_libs/libs/`).

**As a target**: `truncateTarget` was observed ignored (a rerun of the same file posted 0 new rows) and a posting task
built with it `true` was still flagged as able to wipe its table; make postings idempotent in the database, for example
a BEFORE INSERT trigger that skips existing business keys (L-CONN-032, 2026-09-28). In generated multi-target mappings,
a PostgreSQL target on operation `Upsert` ran green but applied 0 of 736 requested rows: split Update and Insert with a
Joiner on the target's keys and a Router (or use a generator that writes the writer attributes the UI sets), test
new-key inserts on every Upsert target before it goes live, and read uuid columns as `::text` in the source query
(L-CDI-207; details in [Source & Target Gotchas](../04-mappings/08-source-target-gotchas.md) §2).

**Before blaming the database**: run one read-only diagnostic as the connection's role (privileges, schema USAGE, RLS,
timeouts, `temp_file_limit`, blocked and idle-in-transaction sessions during a scan) (L-CONN-033, 2026-06-28). For CDC
prerequisites (logical WAL, publications, slots) see [knowledge/06-cdc-ingestion](../06-cdc-ingestion/02-cdc-from-postgresql.md).

## 2. Google BigQuery V2

Evidence: 2026-06-27 to 2026-09-28.

### 2.1 Identifiers and parameters (L-CONN-034, 2026-09-16)

| Item | Value |
|---|---|
| Connector GUID / shortName / sdkType | `com.infa.adapter.bigqueryv2` / `GoogleBigQueryV2` / CCI |
| Display names | 'Google BigQuery V2' (selections); connector name 'Google Big Query V2' |
| `connParams` | `connectorType: "Simple"`, `clientEmail`, `privateKey`, `projectId`, `storagePath` (`gs://<bucket>` staging), `datasetNameForCustomQuery`, plus a large `CCM_CONN_PRESENTATION` blob |
| Easiest create | GET a working BigQuery V2 connection, change only these fields, POST without the id |
| Service account roles | `roles/bigquery.dataEditor` + `roles/bigquery.jobUser` on the project, plus access to the staging bucket (Bulk writes with truncate needed `roles/storage.objectAdmin`) |
| Custom SQL sources | Set `useLegacySQLForCustomQuery=false` (standard SQL), re-supplying the key in the same update (L-CONN-041, 2026-09-23) |
| Connection mode | Keep Simple. `connectorType=Hybrid` returns 200 and breaks every full-pushdown / direct-read mapping with '4005 - Direct Read Mode with Hybrid connection mode is not supported' (L-CONN-042, 2026-07-04) |

### 2.2 The private key: format differs by engine and pod (L-CONN-035, 2026-09-28)

Never send real newlines (the v2 API strips them and the key fails as 'Invalid PKCS#8 data'). Beyond that:

| Pod seen | CDI BigQuery V2 connector | Database Ingestion (Simba JDBC) | Data Gateway (CLAIRE GPT 'Query the data') |
|---|---|---|---|
| Org A, on a `dmp-us` pod (2026-09-22 to 09-25) | Accepted the stripped base64 body; also worked with the full PEM with literal `\n` escapes | not tested there | Rejected stripped base64 ('Invalid PKCS#8 data'); needed the full PEM with literal `\n` escapes |
| Org B, on a `dm-us` pod (2026-09-28) | Accepted only the PEM body without the BEGIN/END header lines (or stripped base64); rejected the escaped-PEM form ('Invalid PKCS#8 data') | Rejected the header-less form ('[Simba] Invalid PKCS#8 data'); accepted the PEM form (reported as 'escaped PEM', but the script's replace was a no-op, so probably the unmodified PEM) | not tested there |

So: test each consumer separately and, when they disagree, keep **one BigQuery connection per consumer** (for example
one for CDI and a DBMI-only one). The probe loop (L-CONN-036, 2026-09-28): cycle stripped base64, full PEM, PEM without
header, one-line PEM and literal-`\n` PEM through GET / modify / POST `/api/v2/connection/<connId>`; after each run
`GET /api/v2/connection/test/<connId>` and, for DBMI, a `POST.../dbmi/public/api/v2/task/deploy/<taskId>` on the
`<pod>-ing` host; keep the first that passes, else restore the last known-good value. Every update must carry the key
because GET masks it (L-CONN-007, 2026-09-23).

UI paste trap (L-CONN-037, 2026-06-29): pasting `private_key` into the form fails with `BaseEncoding DecodingException:
Unrecognized character: 0x20` (wrapped lines) or a truncated start; upload the key file or copy the exact value from a
text file.

### 2.3 Key custody

- If `gcloud iam service-accounts keys create` yields a 0-byte file, the Google org probably enforces
  `constraints/iam.disableServiceAccountKeyCreation`; grant the roles to the agent VM's attached service account instead
  (an IDMC connection using that identity was not proven) (L-CONN-038, 2026-06-27).
- User-managed keys never expire by default. List them, rotate before a repo goes public or a stack moves, delete (not
  just un-commit) a leaked key, update the connection's `privateKey`, and confirm in Cloud Logging (grouped by
  `callerIp` and `private_key_id`) that the old key is silent (L-CONN-039, 2026-09-08).
- Compose bind mounts of key files from cloud-specific absolute paths create empty directories on a new host; jobs then
  fail with auth errors or '[Errno 21] Is a directory'. Use project-relative paths or secrets, and `--force-recreate`
  after fixing a file (L-CONN-040, 2026-09-08).
- A key dies with its project. After the cloud project that minted a service-account key is deleted, the key file still
  parses but every call fails `403 CONSUMER_INVALID`. In a key inventory, check that the project named in the key's
  `client_email` (also the connection's `clientEmail`, `<sa>@<cloud-project>.iam.gserviceaccount.com`) still exists,
  remove dead keys from hosts and connections, and point the CLI's default project at a live one (L-ENV-052).

### 2.4 Types, JSON and the 255-character cut

- **The 255 cut** (L-CONN-044, 2026-09-27): mapping tasks writing through BigQuery V2 truncated every STRING port to 255
  characters whatever the target schema (a varchar(4000) source view, `allowMaxFieldLength=true`,
  `retainFieldMetadata=true`, a pre-created STRING(4000) column and Streaming mode all still cut at 255). A pre-created
  **JSON** target column receives the full text as a JSON string scalar up to 32,000 characters (longer values are cut at
  exactly 32,000); BYTES targets fail with CMN_1081; Write truncate keeps the JSON schema. Read it with `JSON_VALUE`.
  Guard: fail before landing if a source value exceeds 32,000; after a run, flag any IDMC-written STRING column whose
  maximum length is exactly 255, or JSON column exactly 32,000.
- **JSON in Simple mode is disputed** (L-CONN-043, 2026-07-06): in July, reading a JSON column, or writing a JSON target
  column from a STRING source, failed with 'table contains [JSON] data type incompatible with [Simple] connection mode'
  and STRING casts fixed it; in September, template mapping tasks in Bulk mode wrote into JSON target columns fine (the
  bullet above). Test on your pod.
- **Heap**: keep BigQuery source readers per mapping at about five on a small agent, select only needed columns and give
  STRING fields a small reader precision (L-AGENT-057, 2026-09-29).
- **Numbers and dates** (L-CDI-159): through a generated mapping, unicode text, 255+ character strings, empty
  string versus NULL, embedded newlines, NUMERIC with scale 9, integers above 2^53 and microsecond timestamps survived
  exactly. A 29-digit NUMERIC overflows the platform's decimal(28,9) with `TE_7007`: cap or cast wide numerics in the
  source query. A BigQuery `DATE` declared in a source query that feeds a Salesforce date field failed with 'Unknown
  native type for field... Type: DATE'; `CAST(col AS TIMESTAMP)` loads the same date.
- **Task side** (see the CDI folder): write disposition belongs in `$Target$.oprRuntimeAttrs`
  (`{"writeMode": "Bulk", "writeDisposition": "Write truncate" | "Write append"}`); `truncateTarget` was ignored on some
  BigQuery V2 targets (L-CONN-032, 2026-09-28); Write truncate skips empty loads, so a table whose source fell to 0 rows keeps stale
  rows unless you truncate it yourself; a failed or stopped run can leave a `Temp_View<epoch>` in the query dataset, and
  two query-source runs that reach that step in the same millisecond collide on the name (409 on create, 404 on
  cleanup): retry the task once (L-CDI-205).
- **Partial-column Update** (L-CDI-282, 2026-10-28): an Update keyed on the primary key, through a target object that
  declares only 3 of the table's columns, left the other columns untouched. Use it to write a few derived fields back
  into a wide table; the task keeps its own copy of the target object, so re-check the task after changing it
  (L-CDI-271).
- **The project's own query quota** (L-CONN-133, 2026-11-03): a custom daily query-usage quota on the project, used up
  by dashboard extract refreshes (BigQuery bills at least 10 MB per table referenced, and each refresh ran about 40
  queries), made every IDMC task on that project fail with 'Custom quota exceeded'. Nothing was wrong with the IDMC
  connection. Read the cap headless first (L-ENV-041), raise it, or keep pipeline and BI work under separate projects
  or quotas; usage resets daily (midnight Pacific time), and a raised cap stays until someone lowers it.

### 2.5 Database Ingestion to BigQuery (L-CONN-045, 2026-09-28)

A DBMI deploy with a BigQuery target failed with 'Failed to load driver class com.simba.googlebigquery.jdbc.Driver' on a
fresh agent. Copy the Simba BigQuery JDBC set (about 73 jars) into
`<agent_home>/apps/Database_Ingestion/ext/connectors/thirdparty` and `GoogleBigQueryJDBC42.jar` into
`<agent_home>/apps/Database_Ingestion/<ver>/dbmi_libs/libs`, then restart the agent (the classloader caches at start).
Then give DBMI its own BigQuery connection with the key format it accepts (2.2). More in
[DBMI Targets & Drivers](../06-cdc-ingestion/03-dbmi-targets-drivers.md).

## 3. Salesforce

Evidence: 2026-08-15 to 2026-09-28.

**CDI connection** (L-CONN-058, 2026-09-28): the v2 Salesforce connection keeps `username`, `password` and
`securityToken` as top-level fields (not in `connParams`); from an IP range the Salesforce org trusts, an empty
`securityToken` worked. Use Salesforce API version 64 or newer. When one Secure Agent's Salesforce connector misbehaved
(cause not recorded), the Salesforce tasks ran on the Informatica Cloud Hosted Agent; after a migration the same tasks
ran on a self-hosted agent. A minimal, low-risk demo target: a Developer Edition org, a standard object, plain Insert
(no external id), an API user plus security token, Salesforce as a target only.

**OAuth** (L-CONN-063, 2026-09-25): for real-time writes from CAI, the built-in CAI Salesforce connector needs the
ModifyMetadata permission, which breaks least privilege. The pattern that worked: your own CAI REST service connector that
gets a token with OAuth client credentials from a Connected App (token parameters in a form-encoded body, not the URL)
and upserts with `PATCH /services/data/v<nn>/sobjects/<Object>/<ExternalIdField>/<value>`, linking parents by external-id
relationship fields. OAuth on a CDI Salesforce connection was not tested in these sources. CAI app connections authored
with `encrypted="false"` export their client secret in plaintext (L-CONN-064, 2026-09-28).

**Salesforce as a source in a generated mapping** (L-CONN-108, L-CDI-245, 2026-10-13): a `datetime` field (for example
`CreatedDate`) validates at precision 24, scale 0 (29/0, 19/0 and 29/9 stop the session with "Field <name>'s precision is
invalid"). Base64 fields such as `ContentVersion.VersionData` arrive as a string. The SOQL filter in
`readOptions.filterCondition` may semi-join another object (`<field> IN (SELECT Id FROM Account WHERE Name IN (...))`);
Salesforce refuses a semi-join on the outer query's own object. The catalog's lineage scanner cannot parse a semi-join and
drops that source from lineage, so for lineage filter on literal values (L-CDGC-196).

**Data behaviour**

| Trap | Fix | Lesson |
|---|---|---|
| Checkbox (boolean) fields not set by string or boolean-looking values | Send integer 1 or 0 | L-CONN-059, 2026-09-26 |
| SOAP `long` fields come back empty on read | Fetch them with the Salesforce REST API and join in the warehouse | L-CONN-060, 2026-09-26 |
| An active Contact duplicate rule silently blocks CAI and CDI upserts | Decide where dedup lives; deactivate or adjust the rule; re-test both paths | L-CONN-061, 2026-09-26 |
| Fields written by IDMC look empty | Check field-level security on the viewer's permission set; the integration user needs FLS on the fields it writes | L-CONN-062, 2026-09-26 |
| A small org fills up | Count API calls per lane (about 10-18 per lane run, ~2,000 a day seen) and cap child-object retention; see "Storage in a small org" below | L-CONN-075, L-CONN-088 |

Upserts need the target field names as SObject API names and an external-id field in `targetUpdateColumns` (see the
CDI folder). Catalog scans of Salesforce need a user with ViewSetup and ViewRoles. A scan refused with 'no permissions to
access connections which are selected' was not a connection-type wall: the same source on the native Salesforce
connection scanned every standard and custom object, so select the Metadata services on the runtime environment and
retry before building a new connection (L-CDGC-142; see
[Catalog Sources](../09-catalog-lineage/02-catalog-sources-create-scan-update-purge.md)).
Eleven serial Salesforce upsert tasks folded into one generated mapping with eleven parent-first flows (Upsert on an
external id, nulls not sent, non-bulk) made about 30-40 counted Salesforce API calls per run and saved about 175 jobs a
day (L-CDI-170; recipe in [Source & Target Gotchas](../04-mappings/08-source-target-gotchas.md) §3).

**Rotating Salesforce credentials** (L-CONN-063): a newly created Connected App could no longer be given a
client-credentials Run As user (Setup answered 'Invalid User' for every user, and the Metadata API silently dropped
`oauthClientCredentialUser`); an External Client App with the client-credentials flow running as the integration user
works instead (CAI side in [CAI Connections & Connectors](../07-app-integration/03-cai-connections-connectors-salesforce-oauth.md) §6).
When you rotate the integration user's password (SOAP `setPassword` worked; the REST `/password` resource answered
NOT_FOUND), update the CDI Salesforce connection in the same minute (the security token can stay empty from a trusted
IP), and rerun any task that logged in during the swap.

**Storage in a small org** (L-CONN-088). Reverse-ETL tasks that re-upsert every
child record of a rolling window (60 days) on every lane run kept a 5 MB org of about 2,560 records full; deleting test
leftovers and emptying the Recycle Bin bought only hours.

1. Shrink the window at the source: 60 -> 7 days in each task's source query (v2 mttask GET, edit, POST; read back).
2. Back up, delete the older child records and SOAP `emptyRecycleBin` exactly those ids. REST cannot empty the bin, and
   the API user can purge only what it deleted itself (L-CONN-088).
3. Schedule a daily retention job (delete and empty records older than the window plus one day), then a headroom probe:
   insert one record (201), delete it (204), empty it; alert if any step fails.

Facts that mislead: `emptyRecycleBin` answers `INVALID_ID_FIELD` for rows that `queryAll` still lists as IsDeleted
(they are already purged and free nothing); storage accounting lags about a minute after a purge, so trust the probe,
not counts; while the org is full, updates of existing rows keep working but inserts and real-time contact creation
return 500; a lane controller that fails a lane on any Salesforce WARNING marks lanes FAILED although the warehouse
targets landed, so classify CRM-only warnings separately (L-CONN-088). Metrics that need more history than the
CRM keeps (for example "no visit in 21+ days") read 0 there: compute them in the warehouse (L-CONN-088).

## 4. JDBC V2 (generic JDBC) and third-party drivers

Evidence: 2026-06-27 to 2026-09-28.

### 4.1 Body and credentials

```json
{"@type": "connection", "name": "<name>", "type": "TOOLKIT_CCI", "instanceName": "JDBCV2",
 "runtimeEnvironmentId": "<reId>",
 "connParams": {"jdbcdriverclassname": "<driver class>", "connectionstring": "jdbc:<vendor>://<host>:<port>/<db>",
                "username": "<user>", "password": "<from file>"}}
```

- `instanceName` is `JDBCV2`; `JDBC_V2` and `JDBC V2` return 403 'There is no connector with type=' (L-CONN-046,
  2026-07-26). The keys are all lowercase; the object stores `connectionstring` and `jdbcUrl`, and host, port and
  database read back empty, which is normal.
- Credential attributes are `username`, `password`, `additionalsecurityproperties` (from the manifest); `user` does
  nothing (L-CONN-047, 2026-07-26).
- **Disputed: does JDBC V2 pass the password at all?** The plugin XML declares `HASUSERNAME="NO" HASUSERPASSWORD="NO"`,
  and a July proof from both ends showed no password reaching the database in any form, the driver authenticating as the
  default account; an August setup needed a password on the database side and passed only after one was set
  (L-CONN-048, 2026-08-18). Read the database's own auth log before trusting either result, and do not treat a green test
  as proof of the password (L-CONN-013, 2026-06-27).

### 4.2 Where drivers go, and when they load

| Consumer | Directory | Then |
|---|---|---|
| JDBC V2 connections (CDI, DQ) | `<agent_home>/ext/connectors/thirdparty/informatica.jdbc_v2/common/` (Informatica drops its own DB2, MSSQL, Oracle drivers there) | Owner = agent user, mode 644; restart Connector_Service or the agent (classpath cached) (L-CONN-049, 2026-09-28) |
| Survive DIS upgrades | also `<agent_home>/ext/deploy_to_main/bin/rdtm-extra/jdbc_v2/` and `<agent_home>/ext/deploy_to_main/bin/rdtm/javalib/` | Redeployed into the active version on restart (L-CONN-050, 2026-08-20) |
| Catalog scanners | the Metadata engines' `drivers` folders | L-CONN-031 |
| Database Ingestion (Simba BigQuery) | `apps/Database_Ingestion/ext/connectors/thirdparty` + `<ver>/dbmi_libs/libs` | Restart the agent (L-CONN-045) |
| CAI process-engine JDBC | `<agent_home>/apps/process-engine/ext` when 'JDBC Jar Directory' is blank | |

The `common/` directory exists only after the engine deploys; stage the jar afterwards. Guessed folders
(`ext/jdbc/`, `apps/Data_Integration_Server/ext/drivers/`) were ignored. A DIS auto-upgrade leaves jars in the old
version directory behind and the test then says 'JDBC driver is available at the correct location'; the active DIS
version is in the tomcat log file name.

**File copy is enough** (L-CONN-051, 2026-09-28): in July and August 'Unable to load driver' survived several copies and
restarts, and one case was fixed only by the Administrator upload-JAR flow, so a UI step was budgeted. Later the driver
loaded with no UI upload once the DTM native-library gaps were fixed and the jar sat in `common/` (2026-08-19), and a
MySQL driver copied into `common/` plus a restart worked on 2026-09-28. The earlier failures were most likely other gates
(native libraries, staging before the engine deployed, no restart). Order: connector enabled, jar staged (and in
`deploy_to_main`), restart, test, then a run that lands rows.

**Check the jar** (L-CONN-053, 2026-07-26): an `-all` classifier is not necessarily shaded (clickhouse-jdbc 0.6.5 `-all`
lacks `com.clickhouse.client.*` and throws `NoClassDefFoundError ClickHouseClient`); `unzip -l <jar> | grep -c client/`;
check the size (one "jar" was a 554-byte HTML 404 page).

**Diagnose** (L-CONN-052, 2026-08-20): compile a tiny JDBC probe with the agent's bundled JDK (`<agent_home>/jdk8/bin/javac`)
or run `java -cp <driver.jar>...` against the same URL on the agent host; then read
`<agent_home>/apps/Data_Integration_Server/logs/tomcat/tomcat_<ver>.log` for `op:testConnection` and
`adpId:com.informatica.adapter.jdbc_v2`.

### 4.3 Targets through JDBC V2

- `truncateTarget` is ignored: set the target `runtimeAttrs` to `{"Pre SQL": "TRUNCATE TABLE <t>"}`; the key must be
  exactly `Pre SQL` with the space (`preSQL` and `PreSQL` are silently ignored) (L-CONN-056, 2026-09-26).
- **A `Pre SQL` truncate is not failure-safe** (L-CDI-208): it runs when the target initializes, before the
  reader has fetched a row. When the source login then failed, every landing task of a lane failed with its target
  already empty, and the next downstream refresh published empty dashboards for hours. For tables people read, load a
  stage table and swap it on success, or run a key-sync mirror whose deletes act only on rows the source returned and
  are skipped when the source returns 0 or implausibly few rows; never key-sync delete an append-history target
  (L-CDI-199). Prove the design with a scratch copy pointed at a source object that does not exist.
- MySQL-protocol warehouses (for example Apache Doris): `mysql-connector-j` in `common/`, checksum-identical when copied
  between agents; without it runs fail with an 'invalid format' error (L-CONN-057, 2026-09-28). Into UNIQUE KEY tables
  the writer upserts by key and never truncates, so rows deleted at the source stay; mirror tables need a key-sync
  delete branch (master-outer Joiner of source keys to target keys, Filter `ISNULL(<source_key>)`, target operation
  Delete) (L-CONN-057).
- **The URL's database wins** (L-CDI-040): the database in the connection's JDBC URL decides where a
  target writes; a schema or database on the target object is ignored. For parity or scratch runs, clone the connection
  (GET, new name and URL, POST without the id, test) and bind the scratch mapping to it.

### 4.4 ClickHouse through JDBC V2

Evidence: 2026-07-13 to 2026-11-03. There is no native connector.

- Driver `com.clickhouse.jdbc.ClickHouseDriver` from the `-shaded` jar; URL
  `jdbc:clickhouse://<host>:8123/<db>?http_connection_provider=HTTP_URL_CONNECTION` (a bare URL picks the Apache HTTP
  client, which needs slf4j and fails on the agent); the agent's bundled JRE runs it; ClickHouse 24.x rejects the
  `default` user with an empty password over HTTP, so use a dedicated user (L-CONN-054, 2026-08-20).
- Types (L-CONN-055, 2026-08-20): `String` reports precision 0 and blocks the mapping save ('Length/Precision must be
  greater than 0'); cast `toFixedString(col, N)` in the source query (the writer strips the NUL padding), or select the
  target while its columns are FixedString and revert, or use a create-new-at-runtime target. `UInt64` reads as NULL
  (`toInt64`). `DateTime` and `DateTime64(6)` pass through. `ALTER... MODIFY COLUMN` on an ORDER BY key fails with 524;
  drop and recreate, then confirm `SHOW CREATE TABLE` matches.
- `truncateTarget: true` once reported SUCCESS with 0 rows; truncate explicitly (L-CONN-032, 2026-09-28).
- **Profiling through JDBC V2 works headless** (L-DQ-128, 2026-11-02). On 2026-10-03 every object or field fetch for a
  profile failed with `JDBC_V2_ERROR_205 'entry [<database>] already exists in the collection [null]'` (three URL
  variants; L-CONN-089, now disputed), and on 2026-10-29 a REST create with NSTRING fields was refused (L-DQ-119,
  disputed). On 2026-11-02 five ClickHouse profiles on a JDBC V2 connection COMPLETED, up to an ALL_ROWS run over
  about 100M rows: clone a profile body that has run on JDBC V2 (`TOOLKIT_CCI`, `sourcePath` `<database>/TABLE`, NSTRING
  fields with `dataType` varchar) and profile typed sample tables (body and steps in
  [Profiling](../08-data-quality/02-profiling-what-is-headless.md)). What differed from the failed
  attempts was not isolated, so start from a profile that has run on the same connection type.
- **Cataloging** (L-CDGC-234, 2026-11-01): the generic JDBC catalog-source type offers Metadata Extraction, Data
  Profiling, Data Quality, Data Classification, Relationship Discovery and Glossary Association, but no Lineage
  Discovery; lineage for a database reached only through JDBC comes from the IICS source plus a connection-assignment
  MERGE, and curated edges. A ClickHouse scan through that type is untested here.
- **Unsigned integer and DateTime ports** (L-CDI-291, L-CDI-264, 2026-11-01/02): UInt16 from an integer port, UInt32
  from bigint, UInt64 from decimal(20,0), Float32 from double; a DateTime64 custom-query column failed at the first row
  ('Timestamp format must be yyyy-mm-dd hh:mm:ss[.fffffffff]'), so select it as text (`toString(toDateTime(x, 'UTC'))`)
  and convert with `TO_DATE` in an Expression. The cast error names the Java type the driver wanted.
- **Parallel lanes** (L-CDI-292, L-CDI-286, 2026-11-01 to 2026-11-03): put `SETTINGS max_threads = 4, max_memory_usage =
  <bytes>` in every lane's source query (uncapped lanes hit the server memory limit and killed each other's long
  reads), keep to about 3 heavy lanes, and remember the server's concurrent-query limit (32 here) is shared by loads,
  DQ and verification. Never shard on `cityHash64(*)`: it is NULL when any column is NULL, so those rows land in no
  shard.

## 5. Flat file (CSVFile)

Evidence: 2026-09-20 to 2026-09-28.

- **Type** (L-CONN-065, 2026-09-24): a native `FLATFILE` connection returns APP_10519 and a CCI 'Flat File' type returns
  'no connector with type'. A connection with `type: "CSVFile"`, created by `POST /api/v2/connection`, bound to the agent's
  runtime environment, with the directory on the agent host in the top-level `database` field, tests green and works as a
  source and a target. FileIO, Sequential File and CSVFile appear among licensed connector types.
- **Permissions** (L-CONN-067, 2026-09-28): the directory must be readable (and, for targets, writable) by the OS user of
  the agent that runs the task. For a second agent under its own user, use a shared directory owned
  `<agentuser>:<appgroup>` with mode 2775.
- **Empty fields** (L-CONN-066, 2026-09-24): FR_3085 'null character' on empty cells; have the writer emit a placeholder
  such as `(blank)` and turn it back into NULL with NULLIF downstream.
- **Task attributes** (L-CONN-068, 2026-09-27): `$Source$.srcFFAttrs = {"@type":"flatFileAttrs","delimiter":",",
  "textQualifier":"\"","escapeChar":"","headerLineNo":1,"firstDataRow":2,"consecutiveDelimiterAsOne":false}`, the file
  name in `extendedObject.object` / `objects[].name`, and `fetchMode: "RUNTIME"` on `$Source$` and `$Target$` to read the
  header at run time.

## 6. Other connectors seen

**Amazon S3 v2** (L-CONN-069, 2026-07-09): `instanceName` = the display string `Amazon S3 v2` (not a GUID),
`connParams.FolderPath` = the bucket name, top-level `folderPath` = `/`. Created with 200 and deleted cleanly. Data Quality
selections pull this connector in automatically.

**Snowflake, key pair** (L-CONN-092, 2026-10-06): `instanceName: "Snowflake Cloud Data Warehouse V2"` (the UI label `Snowflake Data Cloud` returns 403 'There is no connector with type='). `connParams`: `authentication: "KeyPair"`, `user`, `account` (`ORGNAME-ACCOUNTNAME`), `warehouse` (mandatory), `role`, `privateKeyFile` = absolute path of the .p8 **on the agent host** (agent OS user, mode 400), `additionalparam: "db=<DB>&schema=<SCHEMA>"`. Test answers 200 success.

**Snowflake in generated mappings** (L-CONN-093 to 096, 2026-10-06): object `DB/SCHEMA/TABLE`, type system `TOOLKIT`, native types `varchar` / `number` / `date` / `timestampntz`; Post SQL only through the writer attribute `postsql`; lookups on `NUMBER` need decimal ports; the v2 field browse fails (declare the fields in the spec).

**Snowflake column lengths** (L-CDI-227, L-CDI-233, 2026-10-06 and 2026-10-07): plain `VARCHAR` target columns
(16,777,216 characters) made the CDI writer fail with `java.lang.OutOfMemoryError: GC overhead limit exceeded`, and
unbounded source columns import at that precision per field. Give every column a length; details in
[Source & Target Gotchas](../04-mappings/08-source-target-gotchas.md) §6.

**Snowflake BINARY and large values** (L-CONN-113, 2026-10-13): a BINARY column fails as a CDI source field with
'Unknown native type'. Keep bytes as base64 text in `VARCHAR(16777216)` and decode them with `DEC_BASE64` in an
Expression (L-CDI-244). Check big values inside the warehouse (`SHA2(BASE64_DECODE_BINARY(<col>))`): the SQL API pages
a large result into partitions (`?partition=<n>`), and a client that reads only the first response sees part of it.

**SharePoint Online (CDI connector)** (evidence 2026-10-06):

- **Mint the token for SharePoint, not Graph** (L-CONN-100). The connector calls SharePoint's own REST API
  (`https://<tenant>.sharepoint.com/sites/<site>/_api/...`), not Microsoft Graph, and renews its delegated token without
  asking for a scope, so it receives a token for whatever resource the stored refresh token was minted for. With a
  refresh token minted for Graph every metadata call answers 401: the object picker shows 0 objects and a refresh gives
  `infa.cloud.OBJECT_SEARCH_FAILED`, yet Test Connection passes. Mint the refresh token for
  `https://<tenant>.sharepoint.com/.default offline_access` (redeeming an existing refresh token of the same app
  registration with that scope works headless, with no sign-in) and store it in the connection. Prove access with an
  object browse, not a test ([03 Connections](01-connections-create-test-update-delete.md) §3, L-CONN-101).
- **Objects** (L-CONN-102): one per SharePoint list or document library, hidden system lists included; there is no
  site, version, permission or list-catalog object.
- **What a read returns** (L-CONN-102): one row per folder or file at the library root, with 12 properties
  (TimeCreated, TimeLastModified, UniqueId, ServerRelativeUrl, Name, ProgID, WelcomePage, IsWOPIEnabled, Exists,
  ExistsWithException, ExistsAllowThrowForPolicyFailures, and ItemCount, which is empty for files). Size, ETag, version
  label, author, editor and content type are not exposed. Preview Data shows only the root rows and ignores the
  advanced properties.
- **What a read downloads** (L-CONN-102): every file of the library, recursively, into the connection's
  `Attachment_File_Path`, which must already exist and be writable by the agent user; Preserve Directory Structure =
  YES keeps the library tree.
- **Capabilities** (L-CONN-102): as a source, a single object or a parameter, filter yes, sort no; as a target, Insert,
  Update, Upsert, Delete and Data Driven; lookups (cached and uncached) use the read settings (L-CDI-228).
- **One row per file** (L-CONN-103): set the source's advanced property Indirect File Path to an agent-side text file
  with one pattern per line, each a full server-relative path with spaces written `%20`
  (`/sites/<site>/Shared%20Documents/<folder>/*/*.*`; `*` and `?` work). Each matching file becomes one row and is
  downloaded. Relative or unencoded patterns produce broken URLs (404 or 403 in the session log; runs with such
  patterns returned 0 rows). A `*` directly under the library also walks SharePoint's internal Forms folder and aborts
  the read with 'String index out of range: -1', so list the business folders by name. When two flows of one mapping
  both download, order them with Flow Run Order so the downloads do not overlap.
- **Next steps.** The downloaded files can be parsed with a Structure Parser
  ([Mappings Headless](../04-mappings/02-how-claude-builds-mappings-headless.md) §10, L-CDI-231). A
  SharePoint site is cataloged by its own catalog-source type
  ([Catalog Sources](../09-catalog-lineage/02-catalog-sources-create-scan-update-purge.md) §4,
  L-CDGC-162), and a mapping's SharePoint connection reference stitches to that source's Site for lineage
  ([Search, Lineage & Marketplace](../09-catalog-lineage/04-search-lineage-marketplace.md) §9.1,
  L-CDGC-167).

**MongoDB** (L-CONN-070, 2026-07-26): `instanceName: "MongoDB"`, `connParams` `hostName`, `port` and `dbName` (not
`databaseName` or `database`).

**Azure Blob Storage V3 and ADLS Gen2** (evidence 2026-10-26):

- **Formats** (L-CONN-130, L-CONN-129): read them from `GET <serverUrl>/api/v2/connector/metadata?connectorName=<name>`.
  Blob Storage V3 lists Flat, Avro, Parquet and JSON (cloud_native and spark) and a `binary` formatter with no engine
  restriction; ADLS Gen2 adds ORC, Delta and a `Binary` formatter, and its 'Claire' (AtlanticParserRead) and
  'Document' (DocumentParserRead) formats list spark only, so they need an advanced-mode mapping and an advanced
  configuration ([Runtime Environments](../02-secure-agent/02-runtime-environments-services-connectors.md) §6). A binary read into a
  Structure Parser in BUFFER mode (L-CDI-244) is a candidate route with no copy step; it has not been run.
- **ADLS Gen2 needs a hierarchical-namespace account**: on a plain Blob account its test returned 403 (L-CONN-129).
- **Runtimes** (L-CONN-129): a Blob Storage V3 connection tests green on the Hosted Agent, but a catalog source on it
  refuses the hosted runtime (DISPATCH_REJECTED): scan it on a Secure Agent.
- **Documents without Spark**: land the files on a Secure Agent with a File Ingestion task (`blobSourceLocation` = the
  container name, L-DBMI-060, L-DBMI-062), then parse them in a standard mapping
  ([Mappings Headless](../04-mappings/02-how-claude-builds-mappings-headless.md) §10, L-CDI-275).

**HubSpot and REST V3** (L-CONN-131, 2026-10-28/29): the partner-built CDI HubSpot connector authenticates by OAuth only
(clientId, clientSecret, a refreshToken from an app install). A REST V3 connection has no static-header auth, but it
tested green on a Secure Agent with `authType` AuthorizationCode, `accessToken` = a service key and `tokenType` Bearer.
REST V3 runs only in advanced (elastic) mappings: a standard mapping task using it failed with APP_13400. On the Hosted
Agent its adapter was not deployed (an APP_105060 adapter message) although the selection read enabled; on a Secure
Agent, HubSpot, REST V2 and REST V3 went live about 4 minutes after the selections PUT. For standard mappings, the
native connector with an OAuth app on that Secure Agent is the route.

**Microsoft Fabric** (evidence 2026-07-04 to 2026-07-12):

- Data Warehouse (L-CONN-071, 2026-07-09): connector `com.informatica.adapter.fabricdw`, JDBC to
  `<workspace>.datawarehouse.fabric.microsoft.com:1433` with a service principal (`clientId`, `clientSecret`,
  `tenantId`), `WorkspaceName`, `Database`. Runs fail 'Staging Lakehouse Name is not set' until `StagingLakehouseName`
  names an existing lakehouse. Native writes work (a PostgreSQL source into a create-new-at-runtime Fabric target landed
  rows); pushdown into Fabric needs the source and Fabric connectors on one agent and an ADLS Gen2 staging container; one
  source says plain DW inserts needed no ADLS staging. Always check target counts: a drop test once reported SUCCESS
  with 0 rows. Lakehouse (documented): workspace and lakehouse, an Entra app with Contributor, and the
  `<server>.lakehouse.pbidedicated.windows.net` SQL endpoint.
- A preview (SNAPSHOT) FabricDW connector build crashed pmdtm with SIGABRT 134 at `trepcnx.cpp:296` before any write;
  check the connector package version on the agent (L-CONN-072, 2026-07-07).
- Capacity (L-CONN-073, 2026-07-12): 24801 = throttled (often a backlog of failing jobs; pause them, kill orphan 1433
  loaders, suspend and resume the capacity before resizing), 24800 = paused, `APP_13400 compute capacity exceeded` on
  `GET /api/v2/connection/source/<connId>?type=table`. An F2 locked for minutes after one mapping job; F4 held.
- Warehouse SQL (L-CONN-074, 2026-07-09): DDL is eventually consistent (2714 after DROP/CREATE, so TRUNCATE and reuse);
  2,100 bind parameters per statement; `COUNT(*)` rather than `sys.partitions`; `FABRICDW_10000 Invalid operation field
  name <column>` names the failing column.
- SQL that runs on the Fabric warehouse (pre/post SQL, target DDL, verification and contract queries) must stay inside
  its T-SQL subset: timestamps as `DATETIME2(6)` (legacy `DATETIME` and precision above 6 were refused); no `QUALIFY`
  (filter a `ROW_NUMBER` CTE outside); no `REGEXP_*` (use `LIKE`/`PATINDEX`, or move the regex into the source query,
  which runs in the source dialect). Materialize each statement once on Fabric before wiring it into a task
  (L-CONN-074).

## 7. Cross-connector: truncateTarget is not a reload switch

| Connector (target) | What happened with `truncateTarget: true` | Do instead | Date |
|---|---|---|---|
| BigQuery V2 | Some tasks appended (gold tables doubled) | `oprRuntimeAttrs.writeDisposition = "Write truncate"`, or pre-truncate | 2026-07-04 |
| ClickHouse via JDBC V2 | SUCCESS with 0 rows | Explicit TRUNCATE, `truncateTarget: false` | 2026-08-19 |
| JDBC V2 (Doris) | Ignored | `runtimeAttrs {"Pre SQL": "TRUNCATE TABLE <t>"}` | 2026-09-26 |
| PostgreSQL | Observed ignored; separately flagged as a wipe risk on a posting table | Idempotent inserts in the database; never on a system-of-record table | 2026-09-24 / 2026-09-28 |
| Fabric DW (create-new-at-runtime, cloned template mappings) | The mapping model carried `TruncateTable` (or `Truncate Table`) = NO, so every re-run appended and doubled the target | Set both spellings to YES in the package's mapping model, recompute the checksums, re-import (L-CDI-166) | 2026-07-09 |

(L-CONN-032, 2026-09-28.) Verify row counts after every reload. Whatever truncates, a truncate that runs before the read
leaves an empty target when the read fails (§4.3).

## 8. Overturned beliefs (connectors)

| Believed | Until | Now | Lesson |
|---|---|---|---|
| The stripped base64 key works everywhere | 2026-09-23 | The Data Gateway needed escaped PEM on that pod | L-CONN-082 -> L-CONN-035 |
| The escaped PEM works for every consumer | 2026-09-28 | Another pod's CDI rejected it while DBMI needed PEM | L-CONN-083 -> L-CONN-035 |
| Only 250-character chunking gets long text past the 255 cut | 2026-09-24 | JSON-typed target columns | L-CONN-086 -> L-CONN-044 |
| Flip BigQuery to Hybrid to land JSON | 2026-07-04 | Hybrid breaks full pushdown (4005); cast to STRING | L-CONN-080 -> L-CONN-042 |
| JDBC V2 drivers need the upload-JAR UI | 2026-08-18 | File copy into `common/` plus a restart | L-CONN-077 -> L-CONN-051 |
| JDBC V2 takes `connParams.user` | 2026-07-26 | `username` / `password` from the manifest | L-CONN-078 -> L-CONN-047 |
| An old ClickHouse `-all` jar needs a UI test | 2026-07-13 | Shaded jar plus `http_connection_provider` works headless | L-CONN-087 -> L-CONN-054 |
| A never-browsed PostgreSQL connection cannot resolve objects | 2026-09-22 | `<schema>/TABLE/<table>` | L-CONN-084 -> L-CONN-028 |
| ClickHouse cannot be profiled through JDBC V2 (JDBC_V2_ERROR_205; NSTRING refused) | 2026-10-03 to 2026-10-29 | Five profiles completed from a cloned JDBC V2 profile body | L-CONN-089, L-DQ-119 (disputed) -> L-DQ-128 |
| Fabric native writes land nothing | early July 2026 | A create-new-at-runtime target landed rows | L-CONN-085 -> L-CONN-071 |
| Flat files need the UI-enabled flat-file connector | 2026-09-23 | `type: CSVFile` | L-CONN-081 -> L-CONN-065 |
