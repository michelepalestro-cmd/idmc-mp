# Source & Target Gotchas

**Answers:** How the BigQuery, PostgreSQL, Salesforce, flat-file, JDBC V2 and Snowflake connectors really behave as CDI sources and targets: long text, write dispositions, empty loads, types, temp views, upserts that apply nothing, key-sync deletes, write-back invariants, CRM storage, failure-safe reloads, unbounded column lengths; and a symptom table that maps error text to the real cause.

**Read when:** when a run succeeds with wrong data, fails with a connector error, or a target needs a write mode (truncate, upsert, delete, write-back) you have not proven on that connector.

**Key rules:**
- The BigQuery V2 writer cuts STRING ports to 255 characters: land long text into pre-created JSON columns (L-CDI-152, L-CDI-153).
- A Pre SQL `TRUNCATE` runs before the source is read, so a failed read leaves the target empty: reload mirrors by upsert plus key-sync delete, or stage and swap (L-CDI-208).
- Key-sync deletes belong to mirror targets only, never to append-history targets (L-CDI-199, L-CONN-057).
- Test new-key inserts on every Upsert target of a generated mapping; one applied 0 of 736 rows with no error (L-CDI-207).
- Size a reverse-ETL window to the CRM's storage and probe headroom daily (L-CONN-088).
- Concurrent BigQuery query sources can collide on `Temp_View<epoch-ms>` (409/404): retry once (L-CDI-205).
- Give every Snowflake column a length: plain `VARCHAR` (16,777,216 characters) ran the CDI writer out of Java memory, and source fields import at that precision (L-CDI-227, L-CDI-233).

**Related:** [02 How Claude Builds Mappings Headless](02-how-claude-builds-mappings-headless.md) · [03 Mapping Tasks - Create, Update, Run, Monitor](03-mapping-tasks-create-update-run-monitor.md) · [10 Serving Outputs to BI and Apps](10-serving-outputs-to-bi-and-apps-freshness-latency-reverse-etl.md) · [knowledge/02-secure-agent-connections](../02-secure-agent-connections/) · [Lessons: CDI](../../lessons/by-domain/03-data-integration-cdi.md)

**Last verified:** 2026-11-03

> **Summary.** Connector behaviour, not IDMC logic, caused most CDI surprises.
> **BigQuery:** the V2 writer cuts every STRING to 255 characters (pre-create JSON columns: full text up to 32,000); Bulk + "Write truncate" needs GCS staging; Streaming cannot truncate; a 0-row source leaves stale rows; the write disposition lives in `oprRuntimeAttrs`.
> **PostgreSQL:** object paths must be `<schema>/TABLE/<table>` or `<schema>/VIEW/<view>`; text is cut to 255 and jsonb cannot land (use `::text` views); NOT NULL flags travel with cloned mappings.
> **Salesforce:** upsert on external ids, API v64+, parents first, and preferably external-ID relationship fields instead of Id read-backs. **JDBC V2:** truncate through `"Pre SQL"`, and the connection's bound database wins over the object's schema.
> **Snowflake:** plain `VARCHAR` columns (16,777,216 characters) run the writer out of memory and import at full precision on sources, so give them lengths; the Advanced filter reaches Snowflake verbatim, and Preview Data ignores it.

---

## 1. BigQuery (V2 connector)

### 1.1 Long text: the 255-character cut and the JSON path

- **The cut.** The BigQuery V2 writer cuts every STRING port to 255 characters, **whatever the target schema** (L-CDI-152, 2026-09-24). Tested without success: a `varchar(4000)` source view, `allowMaxFieldLength=true`, `retainFieldMetadata=true`, a pre-created `STRING(4000)` column, and Streaming instead of Bulk. A diagnostic run into a CSV flat-file target kept the full 585-character values, which located the cut in the BigQuery writer. Field-precision overrides over v2 (`overriddenFields`) returned 400.
- **The fix** (L-CDI-153, proven 2026-09-24):
  - Pre-create the target column as **JSON**. IDMC then writes the full text as a JSON string scalar, up to **32,000** characters; longer values are cut to exactly 32,000.
  - BYTES targets fail with `CMN_1081`.
  - "Write truncate" keeps the JSON schema across reruns.
  - Read the text back with `JSON_VALUE(col)` in a view.
  - Byte-exact checks passed on 176,175/176,175 and 26,067/26,067 rows.
- **One-time table prep.** Rebuild the landing table so the long-text columns are `JSON`, dropping any legacy chunk columns. The next landing run refills it.
- **Guards** (L-CDI-087):
  - before landing, fail if any source value is longer than 32,000 characters;
  - after a run, flag any IDMC-written STRING column whose maximum length is exactly 255, or any JSON column exactly 32,000;
  - when a column grows past 255, move it to the JSON path, turn the next layer into a view, and remove the redundant copy task.
- **Do not copy JSON-landed text into a STRING layer** with another IDMC task: the STRING writer cuts it again. Serve that layer as a view (L-CDI-086).
- The interim workaround, chunking long text into 16 × 250-character columns and re-joining them in a view, is superseded (L-CDI-186).

### 1.2 JSON columns and Simple connection mode

- **Keep the connection in Simple mode.** Flipping a BigQuery V2 connection to Hybrid returned 200 but broke **every** mapping with `4005` "Direct Read + Hybrid unsupported" (L-CDI-156, 2026-07-09).
- **Declared JSON fields fail in Simple mode:**
  - a July mapping writing a JSON target column failed with "JSON incompatible with Simple connection mode";
  - a synthesized mapping reading a table with JSON columns failed with "The mapping failed because the table contains [JSON] data type that is incompatible with the [Simple] connection mode" (2026-09-29).

  In both cases, declaring those fields **STRING** in the mapping made them run. Pre-created JSON target columns still receive the text: the copy-template tasks wrote into JSON columns (§1.1), and Bulk loads parse the string (L-CDI-039). This reconciles three observations; re-check on a new connector version.

### 1.3 Write disposition, truncate and empty loads

| Situation | Behaviour | What to do | Lesson |
|---|---|---|---|
| Full reload | `oprRuntimeAttrs {"writeMode":"Bulk","writeDisposition":"Write truncate"}` on `$Target$`; in a synthesized mapping, the adapter's `oprRuntimeAttributes` | `runtimeAttrs` and `WriteOptions.truncate` alone are ignored ("Write append" in the log) | L-CDI-048, L-CDI-038 |
| Bulk mode | Needs a GCS staging path on the connection; the connection's service account needs `roles/storage.objectAdmin` on the bucket | A short bucket lifecycle rule (about 2 days) keeps staging files from piling up | L-CDI-154 |
| Streaming mode | Cannot truncate: a second run doubled the rows (33,106 → 66,230) | Use Bulk for anything that reloads | L-CDI-154 |
| Streamed rows | Sit in the streaming buffer and cannot be updated or deleted by DML at once | Write ledgers and run logs with **load jobs** | L-CDI-158 |
| `truncateTarget=true` | Ignored on some BigQuery targets (gold tables doubled each run, July), while others truncated | Use the write disposition; pre-truncate if in doubt; check the template's `TruncateTable` | L-CDI-155 |
| Source returns 0 rows | Bulk + Write truncate **skips** the load, so the target keeps stale rows | For every SUCCESS with 0 rows, `TRUNCATE TABLE` the target, stage by stage | L-CDI-088 |
| Target gains columns | The task keeps its creation-time field list and writes NULL into new columns | `fetchMode:"RUNTIME"` on `$Source$` and `$Target$` | L-CDI-049 |
| Parallel runs | Transient GCS-staging `5001` with 409/404; data sometimes landed anyway | Serial retry; check the target before calling it failed | L-CDI-130 |
| Parallel query-source runs | Two DTMs create `Temp_View<epoch-ms>` in the same millisecond: 409 'Already Exists' on create, 404 on the other's cleanup (1 in ~1,717 runs at concurrency 4) | Retry the task once after ~20 s; optional 1-2 s start jitter; drop leftover views | L-CDI-205, L-CDI-160 |
| Table replaced by a same-name view | Every task still loading it fails on each run | Stop or retarget those tasks first | L-CDI-151 |
| Write a few derived fields back into a wide table | An Update keyed on the primary key, through a target object that declares only 3 of the table's columns, left the other columns untouched (2026-10-28) | Declare the key as the update key; the task keeps its own copy of the target object, so re-check it after changing the target (L-CDI-271); upsert semantics differ by connector (L-CDI-207) | L-CDI-282 |
| Every task on the project fails 'Custom quota exceeded' | The project's own daily query quota was used up (here by BI extract refreshes), not an IDMC fault (2026-11-03) | Raise the cap, or separate pipeline and BI projects or quotas; read the cap headless first (L-ENV-041) | L-CONN-133 |

### 1.4 Types, SQL and leftovers

- **Booleans** from PostgreSQL land as STRING `'true'`/`'false'` through the copy template. Cast them in the next layer. A synthesized mapping reading PostgreSQL through JDBC rendered booleans as `'t'`/`'f'` and needed a mapping step to match (L-CDI-157).
- **DATE targets** written from a synthesized mapping need a STRING `'YYYY-MM-DD 00:00:00'`. The native DATE type showed as "unknown", and `'YYYY-MM-DD'` failed the Timestamp cast (L-CDI-159). A BigQuery DATE declared as DATE in a source query that feeds a Salesforce date field fails with 'Unknown native type for field... Type: DATE'; `CAST(col AS TIMESTAMP)` (midnight) loads the same date (L-CDI-159).
- **Type fidelity through a generated mapping:** unicode text, 255+ character strings, empty string vs NULL, embedded newlines, NUMERIC with scale 9, integers above 2^53 and microsecond timestamps survived exactly. A 29-digit NUMERIC overflows the platform's decimal(28,9) and fails with `TE_7007`: cap or cast wide numerics in the source query (L-CDI-159).
- **customQuery dialect** is GoogleSQL, the source's dialect. When SQL must run on a T-SQL warehouse instead, translate backtick names to `[schema].[table]`, `IFNULL` to `ISNULL`, `SAFE_DIVIDE(x,y)` to `x*1.0/NULLIF(y,0)`, and `JSON_VALUE(PARSE_JSON(...))` to `JSON_VALUE(...)`. Remove `QUALIFY`, `REGEXP_CONTAINS` with raw strings, and r-strings (L-CDI-023).
- **Non-ASCII** in a customQuery fails the reader ("IOException: missing CR"). Store cleaned SQL (L-CDI-024). Set `useLegacySQLForCustomQuery=false` on the connection.
- **Temp views.** A failed or stopped query-source run leaves `Temp_View<epoch>` in the query source's dataset. List and drop them, so they do not pile up or get catalogued and show up in lineage answers (L-CDI-160). The same naming makes concurrent query sources collide (409 on create, 404 on cleanup): classify `Temp_View[0-9]+` with 409/404 as transient and re-run once; a catch-up ran 16 of 16 tasks in 113 s (L-CDI-160, L-CDI-205).
- **Readers.** At most about 5 BigQuery readers per mapping on a small shared agent; STRING reader precision 256 (L-CDI-129).
- **Backfills.** BigQuery time travel (`FOR SYSTEM_TIME AS OF`) reaches back only about 168 hours, and recreated tables cannot be read at older times. Start daily snapshot tasks early, in append mode (L-CDI-161).
- **Key formats** differ by engine and pod (CDI BigQuery V2 vs Database Ingestion's JDBC driver vs a data gateway). Probe each with a connection test: see [knowledge/02-secure-agent-connections](../02-secure-agent-connections/).

## 2. PostgreSQL (native connector)

### 2.1 As a source

- **Object paths** (L-CDI-162, 2026-09-23). Use `<schema>/TABLE/<table>` or `<schema>/VIEW/<view>`.
  - `public/<table>` fails with `SDK_APP_COM_20000` "Incorrect list of path is populated with size: 1".
  - Bare names, `public.<table>`, quoted identifiers and `db.schema.table` all give "Object(s) [X] not found". That is a cache-only lookup: statement logging showed no query reaching the database.
  - With the right path, the adapter resolves the object at run time with **no prior UI browse**. The "cold catalog" wall was a path-format mistake.
  - The connection has no schema parameter.
- **Text and jsonb** (L-CDI-163). The connector types text as `string(255)` and cannot land `jsonb`/`json`. Create a view in a dedicated source schema that selects every column with `jsonb::text`, and land from `<src_schema>/VIEW/<table>` into a JSON-typed warehouse column (§1.1). Views are additive and reversible (`DROP SCHEMA <src_schema> CASCADE`). Shadow builds need their **own** view schema, or a shadow build can rewrite live views (L-CDI-136).
- **Other native type limits** (L-CDI-164): "native type system does not support the data type [<ENUM>]"; "could not identify an equality operator for type json". Arrays are skipped. Cast them in the source view.
- **Browsing** objects over REST is not possible. Know the path format (L-CDI-017).

### 2.2 As a target

- **Object and labels** (L-CDI-089): `targetObject = objectName = "<schema>/TABLE/<table>"`, `targetObjectLabel = objectLabel = "<table>"`, pop `newObjectName`, `newObject=false`, empty `tgtObjectAttributes`/`runtimeAttrs`/`oprRuntimeAttrs`.
- **Upsert:** `operationType="Upsert"`, `targetUpdateColumns=[<key>]`. Deduplicate the source on that key (`QUALIFY ROW_NUMBER … = 1`) first.
- **An upsert writes every mapped column** (L-CDI-167), so an empty source value blanks a populated target field. Where the contract is "overwrite only with non-empty values", add a `BEFORE UPDATE` trigger that keeps the old value when the new one is empty, or leave those columns out of the source SQL.
- **Write reverse-ETL into a new schema** beside the operational tables. Expose it to the app read-only; nothing the app owns gets overwritten (L-CDI-089).
- **System-of-record postings.** A "post only valid rows" task with `truncateTarget=true` is a wipe risk. One source says the PostgreSQL target ignores `truncateTarget` (L-CDI-194, disputed); do not rely on either reading. Use Insert without truncate plus a `BEFORE INSERT` trigger that skips a row whose business key already exists, so a re-sent file never double-posts (L-CDI-169).
- **Create-new-at-runtime targets** in Insert mode create the table on the first run and append the full set on every later run. If an older-schema table already exists, the run does not rebuild it: drop it first (L-CDI-166).
- **NOT NULL flags** on target ports are baked into a mapping cloned from another target type. Source NULLs then fail with "Cannot set null to non-nullable column #N", and making the target column nullable does not help. Coalesce nullable text in a source view (keep keys and timestamps native) and repoint the source (L-CDI-165).
- **Truncate-then-reload is not atomic.** Readers saw a dimension flap between 0 and its real count mid-run. For tables read continuously, load a staging table and swap, or reload inside a transaction (L-CDI-168).
- **Upsert in a generated mapping can apply nothing.** A generated mapping with PostgreSQL targets on operation Upsert ran green but applied 0 of 736 requested rows (every key was new) with no error: the generator had not written the writer attributes the UI sets for that operation. Two fixes worked: (a) a Joiner against the target's keys (outer, so unmatched source rows survive) plus a Router with two groups, key found → a target instance with operation Update, key not found → one with operation Insert (753 updates + 5 inserts, 0 parity diffs); (b) a generator that writes those attributes, with which Upsert, Update, Delete and Data Driven all ran on PostgreSQL and BigQuery targets. Template-task upserts with `targetUpdateColumns` (L-CDI-089) were not affected. Test new-key inserts on every Upsert target of a generated mapping before it goes live (L-CDI-207).
- **Keep-when-null.** An old per-column update never overwrote a stored value with NULL; a consolidated mapping needs a keep-when-null Expression (take the stored value when the incoming one is NULL), or it blanks stored values (51 stored tiers would have been lost) (L-CDI-207, L-CDI-167).
- **uuid columns:** read them as `::text` in the source query (L-CDI-207).
- **Mirror vs history targets.** For mirror targets (a database or JDBC warehouse table that must equal the source), upsert plus a key-sync delete: a master-outer Joiner of target keys to source keys, a Filter where the source key is NULL, then a target instance with operation Delete; never a TRUNCATE (see §5). For append-history targets (invoices, ledgers, state-change logs) use insert + update only, never deletes (L-CDI-199; L-CDI-207).

**Write-back to the system of origin (reverse-ETL invariants)** (L-MDM-074):
1. Accept only a whitelist of identity, contact and address columns; never status, financial, lifecycle, key or derived values (such as a tier).
2. Normalize each golden value to the source's own convention before comparing (for example phone to +E.164), so an unchanged record writes nothing; make the push idempotent with a watermark plus a diff-upsert, so a re-run reports N unchanged.
3. Push only records the DQ rules mark valid, and log read, clean, skipped-unclean and errors per run; the skipped count is an intended gap, not a failure.
4. Audit every change by record id with before and after values and no raw PII in the audit key; arrive through one writer (an API gateway with service credentials, or one mapping), never two writers of the same field.
5. Verify each target against the right denominator: a mirror equals the gated golden count, not the raw source count; append-only logs legitimately exceed the source.
6. Update every copy the screens read. Web and mobile apps often render the person's name from the identity provider's token (a name claim taken at sign-in), not from the database: a DQ-corrected name stayed wrong in every app although the database was fixed. Also update the identity-provider profile (only re-case it when the words match ignoring case, keep its own first/last split, never fail the write-back on an identity-provider error), and let the web session re-read userinfo about once a minute. Measured: source insert to database and identity provider corrected in 1.5-2.7 min; an open web session followed ~20 s later.
7. Tolerate the gap: for 1-2 minutes the golden record is clean while the write-back has not landed, so a page that shows both disagrees; poll until they match (every 5-10 s, up to 3 min).
8. Audit existing propagation before trusting 'in sync': fire-after-commit calls whose failures are logged and swallowed (no retry, no working outbox) lose the side effect for good; schedule the idempotent sweep after every forward cycle.

## 3. Salesforce as a target (via CDI)

Proven 2026-09-25 (L-CDI-170, L-CDI-090):
- **Connection:** API version 64 or newer. When the self-hosted agent's Salesforce connector misbehaves, run those tasks on a hosted runtime: task-level `runtimeEnvironmentId=<hostedReId>`, drop `agentId`.
- **Upsert on an external id:** `operationType="Upsert"`, `targetUpdateColumns=["<ExtId__c>"]`, the SObject as `targetObject`/`objectName`/labels, pop `newObjectName`, `newObject=false`. Alias the source columns to API field names. Checkbox fields need integer 1/0, and the connector dropped SOAP long fields.
- **Parent-child order.** Upsert parents first. The first design then read the parents' record Ids back into the warehouse (SObject source → `<ds>/sf_ids_<object>`, Write truncate) and joined them into the child upserts. That chain became an 11-task sequential floor. Upserting children with **external-ID relationship fields** (`<Parent>__r.<Parent_Ext_Id__c>`) removes the read-back tasks; the real-time path already worked that way (L-CDI-118).
- **One mapping instead of a chain of upsert tasks** (L-CDI-170). Eleven serial Salesforce copy tasks (parents, id read-backs, children, activities, a scorecard object) folded into one generated mapping with eleven flows in the old parent-before-child order; each flow is an Upsert on an external id, nulls not sent, non-bulk, fields mapped by name, with the source SQL copied verbatim. Edit it by exporting, changing the source `customQuery` and re-importing OVERWRITE. It took 85-92 s for about 3,100 rows and made about 30-40 counted CRM API calls per run (one login per flow, upserts in batches of 200). Parity before the swap: (1) static, the SQL columns equal the mapping's source ports, target ports and CRM fields for every flow; (2) an updates-only test run (created-since = 0 on every object); (3) after the live run, the CRM equals the SQL output for every source key (0 missing, 0 mismatched).
- **Guards in the source SQL:** a count gate (push nothing if valid golden records < 80% of what the SaaS already holds), a test-identity exclusion, and a retention window for child objects when storage is small (L-CDI-091). Map merged duplicates to the golden survivor's key.
- **Size the window to the org's storage** (L-CONN-088). Child syncs that re-upsert every child record of the last 60 days on every run kept a 5 MB developer org (about 2,560 records) full, and re-created deleted records within minutes, so deleting and emptying the bin bought only hours. Fix: shorten the window in each task's `customQuery` (60 → 7 days, through the v2 GET-edit-POST, L-CDI-196), delete the older child records once with a backup and SOAP `emptyRecycleBin` exactly those ids, then run a daily retention job (delete and empty records older than the window + 1 day, then a headroom probe: insert 201, delete 204, empty; alert when any step fails). Facts: `emptyRecycleBin` answers `INVALID_ID_FIELD` for rows the bin no longer holds although `queryAll` still lists them, so IsDeleted counts are not reclaimable space; storage accounting lags about a minute after a purge, so trust the probe, not counts; while the org is full, batch updates of existing rows keep working but inserts and real-time contact creation return 500 (L-CONN-088); after a purge select bin rows with `IsDeleted = true AND SystemModstamp > <purge time>`. Metrics that need more history than the CRM keeps (for example 'no visit in 21+ days') read 0 there: compute them in the warehouse.
- **Classify CRM warnings per task.** A controller that failed whole lanes on any WARNING marked lanes FAILED although the warehouse targets had landed; a WARNING with rejected rows on a SaaS target (storage full, duplicates, locks) is a target alert, a WARNING with 0 rows written is a failure (L-CDI-060; L-CDI-205).
- **A WARNING is not always a failure.** A run that wrote 509/510 rows with 1 rejected (a child whose parent did not exist) stayed non-blocking. A WARNING with 0 rows written counts as FAILED (L-CDI-060).
- **Reporting.** When a batch read-back and a real-time upsert path write the same CRM, a live count = the read-back plus the real-time upserts newer than the last read-back, minus records deleted since. The read-back alone flagged every record created since the last read-back as missing, and all new records once batch stopped at the job cap ([10](10-serving-outputs-to-bi-and-apps-freshness-latency-reverse-etl.md) §5; L-CAI-113).

## 4. Flat files

- **Connection type** `CSVFile`; the native `FLATFILE` type gave `APP_10519`. The directory must be readable by the agent's OS user: use a shared group-writable directory (L-CDI-173).
- **Task:** clone a proven flat-file landing task, set `$Source$.srcFFAttrs = {"@type":"flatFileAttrs","delimiter":",","textQualifier":"\"","escapeChar":"","headerLineNo":1,"firstDataRow":2,"consecutiveDelimiterAsOne":false}`, put the file name in `extendedObject.object`/`objects[].name` and `label`, and set `fetchMode:"RUNTIME"` so the columns come from the header at run time (L-CDI-095).
- **Empty fields.** That reader rejected empty fields (`FR_3085` null character). When converting a spreadsheet for the agent, write a placeholder such as `(blank)` and turn it back into NULL in the cleanse step. Write to a temp name and rename into place atomically, so a task never reads a half-written file (L-CDI-173).
- **As a target.** A flat file works as a target in a generated mapping: `object` = the new file name, fields declared in the spec (= the upstream fields). The file does not exist until the first run creates it (with or without `createTarget`), so there is nothing to browse first. The writer adds a header line and double-quotes every value, and every run overwrites the file instead of appending (L-CDI-274; example `toolkit/mapgen/examples/probes/m_probe_ff_target.json`).

## 5. JDBC V2 targets (MySQL-protocol warehouses and similar)

- **Truncate (Snowflake):** the Snowflake writer also ignores the truncate flag and the transformation's 'Pre SQL'; put the TRUNCATE in the data
  adapter's runtime attributes `presql` (opr) / `Pre SQL` (display), adding the RuntimeAttribute class to `$$classInfo` if a cloned mapping lacks it (L-CONN-106).
- **Truncate:** JDBC V2 ignores `truncateTarget`. A full reload can set `runtimeAttrs {"Pre SQL": "TRUNCATE TABLE <t>"}`. The key needs the space: `preSQL` and `PreSQL` are silently ignored (L-CDI-171).
- **`Pre SQL` truncate is not failure-safe** (L-CDI-208). It runs when the target initializes, before the reader has fetched a row. If the source then fails (a renamed or retired database login, a missing object, a network drop), the task fails with the target already empty, and whatever refreshes from it next (materialized views, BI extracts) publishes empty results until a good run (one incident: 5 dashboard charts empty for about 4 h). For tables people or dashboards read:

  | Pattern | When | Guard |
  |---|---|---|
  | Stage table, then swap or rename on success | full reloads of mirrors | the swap runs only if the load succeeded (post-SQL is not run when the read fails; verify on your connector) |
  | Key-sync mirror: upsert every source row, then delete target keys missing from the source | mirrors with a stable key | deletes act only on rows the source actually returned; skip them on 0 or implausibly few source rows (L-CDI-091) |
  | Insert + update only | append-history targets (invoices, ledgers) | never delete (L-CDI-199) |

  Prove it by pointing a scratch copy at a source object that does not exist: it ended state 3 'Object [...] not found' and the target kept its 822 rows. Before retiring or renaming a database role, list every connection that logs in as it.
- **UNIQUE KEY tables of a MySQL-protocol warehouse** (for example Apache Doris) are upserted by key and never truncated by the writer, so rows deleted at the source stay. For mirror tables in a consolidated mapping add a key-sync delete branch: a Joiner with the source keys as master (outer) against the target keys, a Filter `ISNULL(<source_key>)`, then a target instance with operation Delete; prove it through a scratch connection bound to a scratch database, seeded with a few fake keys that must disappear (L-CONN-057).
- **Driver:** the MySQL JDBC jar goes into `<agent_home>/ext/connectors/thirdparty/informatica.jdbc_v2/common`; restart after adding it.
- **Database binding:** the target writes into the database bound on the **connection**. The schema part of the target object is ignored, so a "parity" write landed in the live table. Use a separate connection for scratch or parity work (L-CDI-040, 2026-09-29).
- **ClickHouse through JDBC V2** (L-CDI-172, 2026-08-19):
  - `truncateTarget:true` can report SUCCESS and leave 0 rows, so run an explicit `TRUNCATE TABLE` before each Insert run instead;
  - `String` reports precision 0 ("Length/Precision must be > 0"), so cast outputs with `toFixedString(col,N)` in the source query; the padding is stripped on write;
  - `UInt64` reads as NULL, so cast with `toInt64`;
  - use the `-shaded` jar and add `http_connection_provider=HTTP_URL_CONNECTION` to the URL;
  - unsigned targets want the next wider Java type: UInt16 from an integer port, UInt32 from bigint, UInt64 from decimal(20,0) (L-CDI-264, L-CDI-291, 2026-11-01/02);
  - cap `max_threads` and `max_memory_usage` in each parallel lane's source query, and never shard on `cityHash64(*)`, which is NULL when any column is NULL (L-CDI-292, L-CDI-286).

## 6. Cross-connector and runtime traps

- **One runtime for every connector.** Every connector a mapping uses must be on the one runtime environment that runs it. With the source connector on one agent and the target connector on another, a task failed in about 2 s (state 3, 0 rows, "DTM process terminated unexpectedly"). A session abort at "Importing Connection: <conn>" (e.g. `trepcnx.cpp:296`) means the task's runtime cannot use that connection: it is bound to another runtime, or the connector package is missing there (L-CDI-044).
- **A throttled target warehouse** shows up as `APP_13400` "Compute capacity exceeded" on the connection, and as tasks writing 0 rows with "DTM process terminated". Fix the capacity, not IDMC (L-CDI-045).
- **A mapping's connection binding** decides the connector type. Package edits did not move a mapping to a different connector type (L-CDI-031); synthesize a mapping for the new adapter instead ([02](02-how-claude-builds-mappings-headless.md) §7).
- **Lookups take disk by declared precision** (L-CDI-281, 2026-10-28). A Secure Agent with about 6.5 GB free failed mappings with 'No space left on device' while it built lookup caches: a cache is sized from the cached ports' declared precision times the rows, not the real width. Declare small lookup-port precisions, select only the columns and rows you need (`WHERE <key> IS NOT NULL` also guards the NULL-key trap, L-CDI-257), and keep the cache directory on a filesystem with headroom (L-AGENT-107).
- **A lookup reaches its connection through the connection's runtime** (L-CONN-132, 2026-11-03): moving a task to another runtime does not move its lookup connections; rebind them too.
- **Load timestamps follow the runtime's clock** (L-AGENT-115, 2026-10-26): `SESSSTARTTIME` came out in US Eastern time from the Hosted Agent and in the host zone (UTC) from a Secure Agent, in one taskflow. Write UTC explicitly and say in the column description which clock it holds.
- **Lookups use the read settings** (L-CDI-228). Designer calls that take a connection operation context accept READ and WRITE only: a lookup uses the READ settings, so there is no separate lookup configuration to look for.
- **Snowflake targets: give every column a length** (L-CDI-227, 2026-10-06). A Snowflake target table whose columns are plain `VARCHAR` (16,777,216 characters) made the CDI Snowflake writer fail with `java.lang.OutOfMemoryError: GC overhead limit exceeded`: it sized its buffer from the declared lengths (a block of about 436 MB for 21 such columns). Create target tables with `VARCHAR(n)`, or set the native precision in Target Fields > Edit Metadata; there, type the value and press Enter, because a pasted value does not commit. With explicit lengths of 20 to 1,200 the same mapping ran in 93 s.
- **Snowflake sources: trim the fields, and know what the filter does** (L-CDI-233, 2026-10-07). A Snowflake table or view with unbounded VARCHAR columns imports into a mapping source with precision 16,777,216 per field, the same memory risk as on targets: delete the fields the flow does not use and lower the precision of the rest in Edit Metadata. The source's Advanced filter is sent to Snowflake verbatim as the WHERE clause, and the reader selects only the fields used downstream. Preview Data ignores both the filter and the field edits, so verify with a run.

- **REG_EXTRACT matches the whole value** (L-CDI-246, 2026-10-13). A pattern for a leading code, `'^([0-9A-Z]+(-[0-9A-Z]+)+)'`,
  returned NULL on values that continue after the code; ending it with `.*` returned the code as group 1. Test an
  expression on real values before a run.
- **Snowflake BINARY sources fail** with 'Unknown native type' (L-CONN-113): read base64 text and decode it with
  `DEC_BASE64` (L-CDI-244).

## 7. Symptom triage

| Symptom | Likely cause | Fix | Lesson |
|---|---|---|---|
| Text values end at exactly 255 characters | BigQuery V2 STRING cut (or the PostgreSQL `string(255)` typing) | JSON-typed target column; `::text` source views | L-CDI-152, L-CDI-163 |
| JSON-landed values end at exactly 32,000 | The JSON landing cap | Fail the cycle; shorten or split at the source | L-CDI-153 |
| Rows double on every run | Streaming mode, an ignored `truncateTarget`, or `TruncateTable` NO in the template | Bulk + `writeDisposition` "Write truncate"; pre-truncate | L-CDI-154, L-CDI-155 |
| A target keeps old rows after its source went empty | Bulk + Write truncate skips 0-row loads | Truncate the targets of 0-row successes, stage by stage | L-CDI-088 |
| New target columns are NULL | The task froze its creation-time field list | `fetchMode:"RUNTIME"` | L-CDI-049 |
| "IOException: missing CR" | Non-ASCII in the customQuery | Strip comments and non-ASCII | L-CDI-024 |
| BigQuery `400 Unexpected "["` | T-SQL on a BigQuery source | Write the source's dialect | L-CDI-023 |
| "JSON incompatible with Simple connection mode" / "table contains [JSON] data type …" | JSON-typed fields declared in the mapping | Declare them STRING; keep Simple mode | L-CDI-039 |
| `4005` "Direct Read + Hybrid unsupported" on every mapping | The connection was flipped to Hybrid | Back to Simple | L-CDI-156 |
| `SDK_APP_COM_20000` or "Object(s) [X] not found" on a PostgreSQL source | The object path format | `<schema>/TABLE/<table>` or `<schema>/VIEW/<view>` | L-CDI-162 |
| "Cannot set null to non-nullable column #N" | `notNull` baked into a cloned mapping | Coalesce in a source view | L-CDI-165 |
| Populated target fields blanked by an upsert | Every mapped column is written | A `BEFORE UPDATE` keep-non-empty trigger, or drop the columns | L-CDI-167 |
| A JDBC V2 target keeps its old rows | `truncateTarget` is ignored there | `runtimeAttrs {"Pre SQL": "TRUNCATE TABLE <t>"}` | L-CDI-171 |
| A "scratch" JDBC write landed in a live table | The connection's database wins over the object schema | A separate scratch connection | L-CDI-040 |
| "DTM process terminated unexpectedly" in ~2 s, 0 rows | A connector missing on the runtime, or a throttled warehouse | Colocate connectors; fix capacity (`APP_13400`) | L-CDI-044, L-CDI-045 |
| `5001` GCS staging errors on parallel runs | Transient staging contention | Serial retry; check the target first | L-CDI-130 |
| A DATE target fails the Timestamp cast | A native DATE or `'YYYY-MM-DD'` sent | Send `'YYYY-MM-DD 00:00:00'` | L-CDI-159 |
| `Temp_View<epoch>` objects pile up in a dataset | Aborted runs of query-source mappings | Drop them | L-CDI-160 |
| A session hangs forever with no error | One source feeds both sides of a Joiner | Sorted Input plus Sorters, or separate sources | L-CDI-106 |
| Java heap / GC-overhead errors in the reader | Too many BigQuery readers in one mapping | At most about 5 readers; precision 256; split the mapping | L-CDI-129 |
| `BIGQUERYV2_10000... [5001 - Unexpected error refreshing access token]` on several reader partitions, preceded in the same log by `PLUGIN_1762 [ERROR] java.lang.OutOfMemoryError: Java heap space` (stack in `CCIRuntimeDataClientImpl.readData`), then `WRT_8044 No data loaded for this target` | The DTM heap ran out; the token errors are a cascade of the dying JVM, not a credential problem. Typical with many unsorted Joiners (`TT_11098... Nested-Loop`), Sorters (~150 MB per partition) and growing Aggregator caches (`TE_7212`), passing alone and failing beside other lanes | Take the mapping out of the live lanes (restore the tasks it replaced), raise the DTM heap cloud-side, then split it or give its Joiners sorted input | L-CDI-210 |
| `Temp_View<epoch-ms>` 409 'Already Exists' on one task and 404 on another's cleanup | Concurrent query-source runs collided | Retry once after ~20 s | L-CDI-205 |
| `TE_7007` on a NUMERIC column | A value wider than decimal(28,9) | Cap or cast in the source query | L-CDI-159 |
| 'Unknown native type for field... Type: DATE' on a Salesforce target | A BigQuery DATE declared as DATE in the source query | `CAST(col AS TIMESTAMP)` | L-CDI-159 |
| A generated Upsert target ran green and applied 0 rows | The generator did not write the operation's writer attributes | Joiner + Router into Update and Insert targets, or regenerate | L-CDI-207 |
| A target is empty after a failed run | A `Pre SQL` truncate ran before the read failed | Stage-and-swap or key-sync mirror (§5) | L-CDI-208 |
| Rows deleted at the source stay in a JDBC V2 target | UNIQUE KEY tables are upserted by key | Key-sync delete branch (§5) | L-CONN-057 |
| CRM inserts fail with 500 / `STORAGE_LIMIT_EXCEEDED` while updates succeed | The CRM org is full | Shrink the window, purge, empty the bin, probe daily (§3) | L-CONN-088 |
| A transient 'Table [<table>] does not exist' for a table that exists, or a BigQuery 503 | A transient cloud error (1 in 52 runs on one core mapping) | Retry once at once | L-CDI-205 |
| `java.lang.OutOfMemoryError: GC overhead limit exceeded` in the Snowflake writer | Target columns declared plain `VARCHAR` (16,777,216 characters) | `VARCHAR(n)`, or the native precision in Target Fields > Edit Metadata (typed, then Enter) | L-CDI-227 |
| Preview Data shows rows a Snowflake source's Advanced filter should exclude | Preview ignores the filter and the field edits | Verify with a run | L-CDI-233 |
| 'No space left on device' while lookup caches build | Cache = declared precision x rows | Smaller precisions, a filtered lookup query | L-CDI-281 |
| Integer-to-Long cast error on a ClickHouse UInt32 target | The driver wants a bigint port | bigint (UInt16 integer, UInt64 decimal(20,0)) | L-CDI-291 |
| A load-time column shifts by hours after a task moved runtimes | `SESSSTARTTIME` follows the runtime's local clock | Write UTC explicitly | L-AGENT-115 |
| 'Custom quota exceeded' on every task of one BigQuery project | The project's daily query quota is used up | Raise or separate the quota (§1.3) | L-CONN-133 |

## 8. Overturned beliefs (latest evidence wins)

| Earlier belief | Overturned by |
|---|---|
| The 255-character cut can only be fixed on a mapping's Fields tab, or by chunking into 250-character columns (2026-09-23/24; L-CDI-186) | Pre-created JSON target columns, 2026-09-24 (L-CDI-153) |
| A cold (never-browsed) PostgreSQL catalog blocks headless landing (2026-09-22; L-CDI-178) | The path `<schema>/TABLE/<table>` resolves at run time, 2026-09-23 (L-CDI-162) |
| Reverse-ETL into the app database needs a UI-authored mapping (2026-09-24; L-CDI-187) | A template task with a warehouse query source and a PostgreSQL upsert target, 2026-09-24/25 (L-CDI-089) |
