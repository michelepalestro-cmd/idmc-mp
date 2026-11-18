# Serving Outputs to BI and Apps (freshness, latency, reverse ETL)

**Answers:** How to serve IDMC-built warehouse tables to BI tools, CRM analytics and applications; views vs tables; how to keep BI extracts fresh without a personal warehouse OAuth login; how to detect new IDMC output cheaply; how to measure freshness and per-hop latency honestly; how event lanes keep moving beside a full refresh; how to size reverse-ETL windows and avoid CRM storage traps; which BI REST and embedding quirks bite.

**Read when:** a dashboard, embedded view, CRM segment or application screen must show IDMC output within minutes; a BI credential expires; before publishing any latency or freshness number; before writing golden data back into an application or a CRM.

**Key rules:**
- Serve consumers from views over the CDC landing tables and the batch-built tables; a view over a CDC table is as fresh as the table and adds no hop (L-DBMI-029, L-ENV-065).
- Never let every dashboard depend on one person's warehouse OAuth credential: refill extracts with a service account and republish them without credentials (L-ENV-081, L-ENV-064).
- Trigger downstream refreshes from `__TABLES__.last_modified_time`, excluding DBMI bookkeeping tables and housekeeping tables (L-ENV-082).
- Publish latencies only from a read-only, success-only collector, and time records with warehouse time travel per publish (L-METHOD-049, L-CDI-206).
- Before pausing a lane, map every BI object to the pipeline that refreshes it (L-ENV-079).
- Size reverse-ETL windows to the target's storage and probe headroom daily (L-CONN-088).

**Related:** [07 Performance, Concurrency & Job Caps](07-performance-concurrency-job-caps.md) · [09 Source & Target Gotchas](09-source-target-gotchas.md) · [CDC from PostgreSQL](../04-cdc-mass-ingestion/02-cdc-from-postgresql.md) · [CAI Runtime](../05-cai-application-integration/02-cai-runtime-invoke-urls-control.md) · [Lessons: Environment & Ops](../../lessons/by-domain/13-environment-ops.md)

**Last verified:** 2026-11-03

> **Summary.** IDMC lands and governs the data; consumers see it through a serving layer that has its own freshness, credentials and caches. Real-time views over CDC tables are about 20-30 s behind the source; tables written by event-driven CDI lanes 1-2.5 min; full refreshes minutes to hours. A BI tool adds its own hop: a live connection depends on a warehouse credential, an extract on a refresh, an open embedded view on the revision it loaded. The patterns here keep that last mile fast and honest: service-account extract pushes on change, cheap change detection from table metadata, a freshness map per object, a success-only latency collector, per-table locks so event lanes run beside full refreshes, and reverse-ETL windows sized to the target.
> Examples use Tableau Cloud, Salesforce and BigQuery because that is where the behaviour was measured; the patterns carry to other BI tools, CRMs and warehouses.

---

## 1. The serving layer: views, tables and which layer a tile reads

| Layer | Written by | Typical age | Notes |
|---|---|---|---|
| Real-time views | views over the CDC landing tables (DBMI) | ~20-30 s behind the source (10 s floor) | a view is evaluated at query time: report it as the CDC figure, not as an extra hop (L-DBMI-029) |
| Event-driven tables | CDI event lanes (golden records, marts touched per event) | 1-2.5 min | the lane runtime, not the trigger, dominates ([07](07-performance-concurrency-job-caps.md) §8.1) |
| Own-cadence tables | a scheduled taskflow or export | its schedule | show cadence plus last run, never a latency |
| Full-refresh-only tables | the full lane | up to the full-lane interval | the class that goes stale when a lane pauses (§4) |

Rules:
- **Find which layer each tile reads** before calling a data fix done: a correction made only in the batch layer does not reach a tile that reads the real-time view, and the reverse (L-ENV-065).
- **Build consumer views with the same names and SQL** as any batch marts they replace, and authorize a view dataset on the CDC dataset when the views live elsewhere ([DBMI Targets & Drivers](../04-cdc-mass-ingestion/03-dbmi-targets-drivers.md) §9).
- **Leave DBMI's own tables out.** A DBMI BigQuery target dataset also holds `INFORMATICA_CDC_RECOVERY` and `<table>_EXT` tables. Exclude `INFORMATICA%` and `%_EXT` from BI sources, catalog filters, table counts and change detection; derive any "tables replicated" list from the dataset instead of hard-coding it (a hard-coded list of 10 missed 3 of 13 tables) (L-ENV-082, L-DBMI-050).
- **Row order is the datasource's, not the view's.** Sorting a warehouse view changes nothing in a BI sheet: carry an explicit rank column (`ROW_NUMBER`) in the custom SQL and sort the sheet by it, and check that the SQL does not also filter new rows out (a "newest first" list missed new rows that a status filter excluded) (L-ENV-083).

## 2. BI extracts without a personal warehouse login

**Three ways to serve warehouse tables to a BI tool** (measured on a dashboard of about 35 datasources; L-ENV-081):

| Mode | How fresh | Survives a warehouse-credential cut | Cost |
|---|---|---|---|
| Live connection | every view open queries; an open view never re-queries by itself (Refresh: about 3 min on a 140-connection workbook, 45 s mid-size, 8-12 s small); one serial `SELECT 1` connection check per embedded datasource before the first data query (L-ENV-062) | no: every view fails when the shared OAuth credential expires (L-ENV-064) | warehouse cost per view open |
| Extract copy refreshed over REST on new data | opens in about 8 s | viewers yes; the refresh itself still needs a working credential | about 3 min of the site's metered backgrounder time per refresh (for example 8 backgrounder hours a day per Creator licence: a refresh every 5 min would need about 15 h, so cap data-triggered refreshes) |
| **Host-built extract push** | about 27-30 s change-to-visible on a small workbook, 67-84 s on 35-37 datasources | yes: the BI tool never connects to the warehouse | the warehouse queries per push (37 queries ≈ 3.6 GB billed) |

**The wall.** Tableau Cloud refuses any non-OAuth BigQuery credential headless. A publish with a service-account `connectionCredentials` (key in raw, compact, base64 or PEM form, or XML `authentication='auth-service-account'`) fails with `403132` in about 0.2 s, exactly like a bogus authentication type; `PUT.../connections/<id>` with `authenticationType=auth-service-account` returns `404020`, again identical to a bogus value. Service-account connections are authored in Tableau Desktop. Headless options: fix the identity provider's session-control policy (L-ENV-064), or stop depending on the live connection (L-ENV-080, L-ENV-081).

**The push, step by step** (L-ENV-081):
1. Back up the production workbook. Download it with `includeExtract=true`: each datasource is one custom-SQL relation plus an embedded `.hyper` extract.
2. On a host you control that holds a **read-only** warehouse service account, run each datasource's own SQL (37 queries in parallel took about 21 s).
3. With the Hyper API, delete and re-insert the rows of the existing `Extract.Extract` tables (Hyper column names equal the warehouse result column names, so they map 1:1; about 1 s) and bump the extract's update time.
4. Publish the packaged `.twbx` with `overwrite=true` and **no** connection credentials, signed in with a connected-app JWT (§3): `POST /api/<ver>/sites/<site-id>/workbooks?overwrite=true` as `multipart/mixed` (a form-data upload returns `406000`) → HTTP 201 in about 18-24 s. Keep the same workbook name and project, so the workbook id, its `contentUrl` and every embed survive.
5. Serialize publishes per site (concurrent publishes return 503; L-ENV-063), cap publishes per workbook per hour (for example 90), and keep the previous version when a push fails.

**Count BI refreshes against the warehouse's own limits** (L-CONN-133, 2026-11-03). Dashboard extract refreshes on the pipeline's warehouse project (about 40 queries each, at least 10 MB billed per table referenced) used up the project's custom daily query quota, and every IDMC task on that project then failed with 'Custom quota exceeded', including the data-quality checks and the dashboard rebuild. Refresh less often, or keep BI and pipeline work under separate projects or quotas.

**Push on change, not on a timer** (L-ENV-082, L-ENV-081):
- Poll the warehouse table metadata every few seconds (§4), plus a trigger file for on-demand pushes and a heartbeat push every 15 min. Push only when a business table the sheets read changes: housekeeping tables (run logs, CDC health, audit) change every minute and caused a push per minute.
- One loop per workbook, a per-query deadline (for example 20 s small, 45 s large) that reuses the last good result on timeout or error, and an hourly cap. While IDMC lanes run, warehouse queries slowed to 100-143 s, and a single shared loop made one change wait 280 s behind another workbook.
- Before swapping a datasource's SQL, run old and new on the warehouse and require identical output; a query that fails right after a template change stops that workbook's pushes once its last good copy is reset.
- Measured: 74 pushes, 0 failures in the first hour; change-to-visible 27 s average (11 s fastest) on a small workbook and 74 s (40 s fastest) on a 37-datasource one. Add about 20 s of CDC for source-to-visible, and the lane (about 2 min) for governed batch data.

## 3. Embedded views and BI REST traps

**An open embedded view never shows a republished revision** (L-ENV-083). An embedded view stays bound to the workbook revision it loaded: `viz.refreshDataAsync`, the toolbar Refresh and the page's own poll all re-read the old revision, so near-real-time data "does not show up" while every pipeline hop is green. Before debugging IDMC for a "missing" record, check whether the open view is on an old revision. Pattern:
1. After each push, write a small status file (finish time, revision) next to the page; poll it about every 10 s with a 5 s fetch timeout (a hung fetch otherwise leaves the checker busy for good). Take the "last seen push" baseline when the session opens, not at the first poll.
2. When a newer push lands, load it into a hidden twin viz stacked under the visible one (z-index and `pointer-events: none`, not `visibility: hidden`, which browsers throttle for cross-origin frames) and swap on `firstinteractive` (about 3-11 s), keeping the scroll position and exactly one viz afterwards.
3. Hold automatic swaps for about 60 s after the user clicks a mark, filter, parameter or tab; skip checks while the browser tab is hidden (drop a twin that never becomes interactive after about 90 s).
4. Cap any `getDataSourcesAsync` wait at 5 s; awaited on every sheet right after a reload it can stall the page on "Loading...".

**Connected-app sign-in** (L-ENV-084). An HS256 JWT with header `kid=<secret-id>`, `iss=<client-id>` and claims `iss=<client-id>`, `aud`, `sub=<user>@example.com`, `jti=<uuid>`, `exp` at most 10 minutes ahead and `scp` listing only what the job needs (`tableau:content:read`, `tableau:workbooks:download`/`create`/`update`/`delete`, `tableau:views:download`, `tableau:extracts:create`, `tableau:tasks:run`, `tableau:jobs:read`). Then:

```
POST /api/<ver>/auth/signin
{"credentials": {"jwt": "<jwt>", "site": {"contentUrl": "<site>"}}}
-> 200: site id + X-Tableau-Auth token
```

| Signature | Cause | Fix | Lesson |
|---|---|---|---|
| `400011` 'non-existent parameter' on publish (after up to ~3 min) | a `<` in custom SQL, read as a parameter reference | write comparisons the other way round (`500 > status`, `x >= a AND b >= x`); keep comments and `[...]` out of tile SQL; lint every tile query for `<` | L-ENV-085, L-ENV-061 |
| A drift keeper republishes in a loop | the BI tool stores SQL newlines as `&#10;`/`&#13;` | map them before comparing or replacing SQL | L-ENV-085 |
| After a browser save every relation appears twice and every hash changes | the web editor rewrote the workbook in a newer object model | diff normalised SQL, zones and text, never raw XML; make scripted editors accept both shapes | L-ENV-085 |
| `403132` on a live-connection publish | per-connection credential blocks | one workbook-level `<connectionCredentials name='<user>@example.com' password='' embed='true' oAuth='true'/>` inside `<workbook>`; send a `<views>` list with hidden entries or every sheet becomes a tab | L-ENV-084, L-ENV-085 |
| `400031` on `GET.../jobs/<id>` | `createExtract` jobs cannot be polled by id | poll `GET.../jobs?filter=createdAt:gte:<ts>&pageSize=100` and match the id in `backgroundJobs` | L-ENV-086, L-ENV-084 |
| `409093` on `POST.../workbooks/<id>/refresh` | a refresh is already queued or running | wait; poll `GET.../jobs/<id>` until `completedAt` (`finishCode` '0' = success) | L-ENV-084 |
| A just-republished extract copy queries the warehouse | until `createExtract` (API 3.27+, scope `tableau:extracts:create`) finishes, the copy runs live | never rebuild it while the warehouse credential is broken | L-ENV-084 |
| A workbook "not found" by name | the REST name filter splits on commas | list and match the exact name client-side | L-ENV-086 |
| An `extractUpdateTime` that will not parse | UTC text with a narrow no-break space (U+202F) before AM/PM | normalize it first | L-ENV-086 |
| `401` creating a new Direct Trust secret | secret creation has no JWT scope | move consumers to an External Authorization Server connected app with your own RSA key and a public JWKS; delete old Direct Trust secrets with scope `tableau:connected_app_direct_trust_secrets:delete` | L-ENV-086 |
| `10084` on EAS sign-in | `aud` is plain `tableau` | `aud` = `tableau:<site-luid>` | L-ENV-086 |
| `409` 'UUID string too large' on an embed token | the token carries a header `iss` | drop it | L-ENV-086 |
| An embed token opens other views | a `tableau:views:embed` token is not limited to one view: the JWT subject can open any view it can see | a dedicated viewer user or restricted project access; mint tokens server-side for a known referer only | L-ENV-086 |
| Long `bootstrapSession` calls fail with `ERR_NETWORK_CHANGED` in headless browser tests | headless Chromium with `--network host` on a busy container host | test from a bridge network or another machine | L-ENV-086, L-ENV-085 |
| Is the warehouse login still alive? | — | `GET.../views/<id>/data?maxAge=1` forces a fresh data pull: a cheap canary | L-ENV-084, L-ENV-067 |

## 4. Detecting new output and mapping freshness

**Change detection from table metadata** (L-ENV-082). Read the newest `last_modified_time` instead of scanning rows:

```sql
SELECT MAX(last_modified_time) AS newest_ms
FROM `<cloud-project>.<cdc-dataset>.__TABLES__`
WHERE table_id NOT LIKE 'INFORMATICA%' AND table_id NOT LIKE '%_EXT'
UNION ALL
SELECT MAX(last_modified_time) FROM `<cloud-project>.<curated-dataset>.__TABLES__`
WHERE table_id IN ('<cdi_output_1>', '<cdi_output_2>')     -- the tables the consumer actually reads
```

Exclude tables your own monitors rewrite every few minutes (run ledgers, health and count feeds), or every tick looks like new data. Gate the trigger with a minimum gap (for example 5 min, or 60 s in a fast mode), a maximum age that forces a refresh anyway (60 min, or 15 min fast) and a daily budget for the consumer's metered work.

**A freshness map before any pause or maintenance window** (L-ENV-079). For every warehouse object a BI workbook or app reads, record its refresher and cadence, its age at probe time and its worst case during the planned pause. Build it read-only from `INFORMATION_SCHEMA.VIEWS` (walk each view down to its base tables), `__TABLES__`, the orchestrator's lane plan and the IDMC v2 workflows and schedules.

| Class | Refreshed by | Typical age | Affected by a full-lane pause? |
|---|---|---|---|
| streaming | views over the CDC landing or a log stream | seconds | no |
| event-driven | event lanes | minutes | no |
| own cadence | its own taskflow, schedule or export job | its cadence | no |
| full-lane only | the full refresh | until the next full run | **yes**: repoint the tile at a live view over the same source, or accept a snapshot |

In one audit: 66 objects, 43 streaming, 9 event-driven, 13 own cadence and exactly 1 full-lane-only (it would have been ~13.7 h stale). Traps: a VIEW's `last_modified_time` is when its definition changed, not its data age (streamed views ~1 min behind read 1,813 min "old"): query the view's newest row. A "newest data N minutes ago" header measures event age, not pipeline lag, when sources are quiet.

**At the job cap**, batch-fed freshness freezes while CDC keeps running: derive freshness from the newest CDC landing and label batch tiles "paused since <last success> (job limit)" ([07](07-performance-concurrency-job-caps.md) §7; L-IPU-060).

## 5. Real-time and batch copies of the same SaaS data

**A live SaaS mirror = the batch read-back UNION the newer real-time upserts** (L-CAI-113). When CAI writes records to a SaaS application in real time and a CDI task reads the SaaS objects back in batch, a reconciliation built only on the read-back flags every record created since the last read-back as missing, and all new records once batch stops (for example at the job cap). Build the view as the read-back rows UNION the successful upserts from your own CAI decision log (CAI runs are not in the activity log, L-CAI-041) that are newer than the read-back's watermark, deduplicated on the SaaS record id or the natural key. New records then appear within the CAI round trip plus the view's own latency (one check went from 12 false "missing" rows to +1 per synced record within about 25 s).

**Serving IDMC tables to a CRM's data platform by Zero Copy** (L-ENV-087). Salesforce Data 360 can read IDMC-built BigQuery tables in place through a Zero Copy BigQuery connection (`GET /ssot/connections?connectorType=BIGQUERY` lists it; the data lake object's data source is that connection). Data lake object counts matched BigQuery on every change checked (18 of 18 over 21 minutes, deletes included), and a new record was queryable about 1-2 minutes after it landed, with no copy pipeline.

| Action | Headless for an integration user? |
|---|---|
| Zero Copy read of BigQuery tables | yes, live |
| `/ssot/*` answers `FUNCTIONALITY_NOT_ENABLED` | the user lacks the Data Cloud permission set; not a tenant problem |
| identity resolution run | yes: `POST /ssot/identity-resolutions/<rulesetId>/actions/run-now` (about 30 min) |
| segment create or publish | no: 403 `FUNCTIONALITY_NOT_ENABLED` (needs a data-platform admin or the UI) |
| calculated-insight manual run | no (400) |
| activation | UI |

Segments republish only on their own schedule (for example every 12 h), and a segment without a schedule keeps its old count; a segment that needs history the CRM no longer keeps (because of a retention window, §8) publishes 0, so segment on a warehouse-computed field. Read segment and activation counts back into the warehouse with a small job if dashboards need them.

## 6. Measuring freshness and per-hop latency honestly

**Methods:** per record into a governed table, CDC change history plus time travel at each publish ([07](07-performance-concurrency-job-caps.md) §8.1); per table for CDC, `APPENDS` for inserts and change counters against `__TABLES__` for updates ([CDC from PostgreSQL](../04-cdc-mass-ingestion/02-cdc-from-postgresql.md) §3).

**The collector contract** (L-METHOD-049). Every latency on a page, runbook or status report comes from a collector, never typed in:
1. Compute each hop from timestamps the platform already records (source commit proxy → CDC landing; event → first successful CAI upsert in your decision log; event → end of the first fully successful CDI lane run that started after it; event → first verification row; gateway log time → warehouse arrival) over a rolling window (24 h), as n, average, fastest, last and last_at.
2. **Success only:** an integration call with ok=true (HTTP below 500; note that 4xx fast-fails drag "fastest" down); IDMC runs SUCCESS or WARNING; a lane only when every task succeeded. A sample belongs to the window in which it completed; drop samples overlapping a deploy and negative values (clock skew).
3. Match an outcome to its event only within N minutes (for example 10) and count the event's own first check, so a later back-fill or re-check is not reported as event latency. Keep a first-seen column that is never overwritten: a downstream job that re-checks records and overwrites its timestamp destroys the first-time latency.
4. Every hop independent: one failing query marks only its hop unavailable. Write the output atomically (temp file + rename) and refuse to publish when fewer than 3 hops were measured, keeping the previous file. Hide hops with no samples instead of printing a placeholder.
5. Split lane statistics by pipeline mode; show batch schedules (full rebuilds, daily loads, catalog refreshes) as cadence plus last run, never as a latency.
6. Read-only by construction: PostgreSQL in a `READ ONLY` transaction with `statement_timeout`; BigQuery SELECT-only with `maximum_bytes_billed` and job labels. Mark every name or meaning the collector assumes (`# ASSUMPTION:` plus evidence), and check that each hop keys on names the callers actually log (hops keyed on process names nobody writes stay at 0 samples forever).
7. Quote a p50 only with at least 5 timed calls and a p95 with at least 20, or one slow histogram bucket becomes a headline number (L-ENV-088).

**Traps that made published figures lie** (one audit of 37 figures, 15 inconsistencies): averages over all calls including failures (809 ms at 51.8% success, failures sitting at the timeout; 27 failures pulled another average from ~1,130 ms to ~810 ms, L-CAI-038); a client that stores latency only for the final attempt, hiding retries and backoff (L-CAI-082); orchestrator wall-clock versus IDMC task span; a "real-time view" hop that is only a view over the CDC table; lane times quoted without the pipeline mode; cadences copied from an old schedule; a re-applied DDL file that redefined a view without a newer column. Time browser dashboards cold and warm: one cold-cache slowdown (17-26 s against about 10 s) came from the BI vendor's CDN assets inside the browser, and viewers see the warm number.

**Two more traps.** A load timestamp built from `SESSSTARTTIME` follows the runtime's local clock (US Eastern on the Hosted Agent, the host zone on a Secure Agent), so a failover shifts it by hours: write UTC explicitly (L-AGENT-115). Drop latency samples that span an outage: a CDC catch-up after a three-day stop showed an 'average latency' of tens of thousands of seconds (L-DBMI-063).

**Reference numbers from one stack** (8-vCPU agent host; L-METHOD-049, L-CDI-206, L-ENV-083):

| Hop | Average | Fastest |
|---|---|---|
| application call → SaaS record through CAI | ~2 s | ~1.5 s |
| source row → CDC table in the warehouse | ~26 s (n=295) | 10 s |
| record → golden table (event lane) | ~76 s (median 67 s) | 33 s |
| event-driven CDI lane, event → trusted record | ~106 s (n=21) | 62 s |
| longer activity lane | ~213 s (n=32) | 124 s |
| warehouse change → BI extract visible (push) | 27-84 s by workbook size | 11 s |
| new record → BI copies republished | 98-131 s | — |

## 7. Event lanes beside a full refresh

The serving layer is only as fresh as the lane that feeds it. A single global run lock made a new record wait behind a 20-minute full refresh (1,027 s to its golden record). An external controller that starts the IDMC jobs itself can admit the critical event lane as a guest beside a running lane and block only real conflicts, per table: the same mapping task, two writes of one table, or a read of a table another run is writing. Record → golden then stayed at 76-88 s both solo and beside a full refresh. Rules (priority, critical path first, soft-fail DQ side tasks, drain file, blackout window): [07](07-performance-concurrency-job-caps.md) §5 (L-CDI-128). Speed modes and the job cost of fresher data: [07](07-performance-concurrency-job-caps.md) §7.

## 8. Reverse ETL into applications and CRMs: windows and storage

**Size the window to the target** (L-CONN-088). A reverse-ETL child sync that re-upserts every record of a rolling window on every run holds `window × children per day` records in the target permanently, and re-creates whatever you delete within one run. Rule of thumb: choose the window so the records it holds plus the parents fit the target's storage with headroom. Measured: a 60-day window kept a 5 MB CRM org (about 2,560 records) full; 7 days plus a daily retention job (delete and empty records older than 8 days) left about 600 records free (about 1,930 used).

1. Change only the source window in each task's `customQuery` (for example `INTERVAL 7 DAY`) with the v2 GET-edit-POST, and read it back (L-CDI-196).
2. Delete the older child records once, with a backup, and empty exactly those ids from the recycle bin (SOAP `emptyRecycleBin`; REST cannot; L-CONN-088).
3. Schedule the retention job, then a headroom probe: insert one record (201), delete it (204), empty it; alert when any step fails. The sync user may not be able to read the org's storage figure, so estimate headroom from record counts.

**Storage facts** (L-CONN-088): while the org is full, batch updates of existing rows keep working, but inserts and real-time contact creation through CAI return 500 (`STORAGE_LIMIT_EXCEEDED` behind it); `emptyRecycleBin` answers `INVALID_ID_FIELD` for rows the bin no longer holds although `queryAll` still lists them, so IsDeleted counts are not reclaimable space; storage accounting lags about a minute after a purge, so trust the probe, not counts. A lane controller that treats a CRM task WARNING as a lane failure marks whole lanes FAILED although the warehouse targets landed: classify CRM-only warnings separately ([09](09-source-target-gotchas.md) §3). Never let a synthetic-load generator follow a fast pipeline mode: it created CRM records faster than a small org's storage allowed (L-IPU-054).

**What else belongs to a reverse-ETL design:**
- Guards in the outbound SQL: a count gate, a test-identity exclusion and the retention window (L-CDI-091; [05](05-the-pipeline-generation-pattern.md) §5).
- Write-back invariants (column whitelist, normalize then compare, DQ-valid only, audit, one writer, update the identity provider too): [09](09-source-target-gotchas.md) §2.2 (L-MDM-074).
- A database NULL-guard trigger that still allows explicit clears: [05](05-the-pipeline-generation-pattern.md) §6 (L-CDI-209).
- Metrics that need more history than the target keeps (for example "no activity in 21+ days") read 0 there: compute them in the warehouse and send the result.
- Erasure: a delete that flows through CDC is not erasure; fan it out to every copy ([CDC from PostgreSQL](../04-cdc-mass-ingestion/02-cdc-from-postgresql.md) §7.1; L-DBMI-051).

## 9. API traffic analytics beside IDMC

API usage analytics (calls, blocked calls, latency per API) do not need a CDI lane: a 4-task lane every 5 minutes would cost about 1,440 jobs a day. Two routes (L-ENV-088):

| Route | How | Measured | When |
|---|---|---|---|
| CAI process carrying the events | the gateway or the backends post usage events to a CAI process that writes the warehouse | CAI calls are not jobs (L-CAI-038) | the default under the integration-layer split: analytics ingestion stays in IDMC ([CAI Runtime](../05-cai-application-integration/02-cai-runtime-invoke-urls-control.md) §10.7) |
| The gateway's own log shipper | for example a self-managed Flex Gateway's embedded Fluent Bit: a `Configuration` resource with `spec.logging.outputs` (a BigQuery output) plus `accessLogs` on every gateway; a writer service account limited to one dataset, key mounted read-only; the raw table partitioned by ingest day with an expiry (14 days); `retry_limit no_limits` and `storage.total_limit_size` on the output; `ingested_at DEFAULT CURRENT_TIMESTAMP` | calls landed in about 3-5 s; a policy rejection was visible in the warehouse within ~1 s and on a tile within ~25 s | when the architecture allows a non-IDMC path for this telemetry; record it as an exception |

Either way: gateway policy expressions have no clock (`now` is a parse error, `uuid` is evaluated once), so per-call latency comes from a `server-timing: app;dur=<ms>` header the backends add; give policies an explicit order (credential policies otherwise mask tier rate limits); build the reporting tables as views over the log table.

## 10. Symptom triage

| Symptom | Likely cause | Fix | Lesson |
|---|---|---|---|
| Every dashboard fails at the same moment | the shared warehouse OAuth credential expired (a session-control policy) | trust/exempt the BI app, or serve pushed extracts (§2) | L-ENV-064, L-ENV-081 |
| A pushed record never appears in an open embedded view | the view is bound to the revision it loaded | twin-viz swap on a push signal (§3) | L-ENV-083 |
| A tile is unchanged after a data fix | the tile reads the other layer (real-time vs batch) | fix both layers; verify the tile's own query | L-ENV-065 |
| BI pushes run every minute with no business change | housekeeping tables in the change check | exclude them (§4) | L-ENV-082 |
| A "replicated tables" count is short | a hard-coded table list | derive it from `__TABLES__`, excluding `INFORMATICA%` and `%_EXT` | L-ENV-082 |
| A view looks hours stale in metadata | a view's `last_modified_time` is its definition time | query its newest row | L-ENV-079 |
| Reconciliation shows new records as missing in the CRM | the check reads only the batch read-back | UNION the newer real-time upserts (§5) | L-CAI-113 |
| "Last successful run" freshness frozen, success-rate tile still high | the job cap: later runs are zero-row non-success | freshness from CDC; label batch tiles paused | L-IPU-060 |
| CRM inserts fail with 500, updates succeed | the CRM org is full; a rolling reverse-ETL window refills it | shrink the window, purge, empty the bin, probe daily (§8) | L-CONN-088 |
| A segment count never changes | it republishes only on its schedule, or needs history the CRM no longer keeps | schedule it; segment on a warehouse-computed field | L-ENV-087 |
| Grafana BigQuery panels error in the browser ('react/jsx-runtime' 404) while `/api/ds/query` answers | grafana-bigquery-datasource 3.x needs Grafana 11.6 or later | pin `grafana-bigquery-datasource 2.2.1` in GF_INSTALL_PLUGINS; recreate only Grafana | L-ENV-094 |
| Anyone can query the warehouse or the ledger through a public dashboard | an anonymous Viewer can POST any SQL to `/api/ds/query` | a guard that allows only the dashboards' panel queries; views without PII; a bytes-billed cap | L-ENV-095 |
| Published average latency looks too good or too bad | failures in the average, final-attempt-only timing, wrong span | success-only collector (§6) | L-METHOD-049 |
| Every IDMC task on the warehouse fails 'Custom quota exceeded' after a day of BI refreshes | the refreshes used up the project's daily query quota | raise or separate the quota; refresh less often (§2) | L-CONN-133 |
| A load-time column jumps by hours after a failover | `SESSSTARTTIME` follows the runtime's clock | write UTC explicitly (§6) | L-AGENT-115 |
