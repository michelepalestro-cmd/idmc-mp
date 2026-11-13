# CDC from PostgreSQL

**Answers:** What PostgreSQL needs for log-based CDC through DBMI; which task settings matter; what latency to expect and how to measure it per table; how slots behave and must be handled; how to hand a slot to another org's task or split a task hot/cold; which data traps bite (bulk fixes, deletes, erasure); how to watch a CDC job.

**Read when:** before enabling CDC on a PostgreSQL source, changing slots or publications, running a bulk fix on a captured table, or quoting a CDC latency.

**Key rules:**
- Four source rules each killed a job: CREATE on the schema, no `FOR ALL TABLES` publication, `REPLICA IDENTITY FULL`, the slot created after the publication (L-DBMI-011, L-DBMI-012).
- `FlushPeriod` (60 s default) is the latency floor; tables apply one after another per cycle, so split hot and cold tables (L-DBMI-018, L-DBMI-019).
- One job per slot; `active=f` between cycles is normal: judge a slot by LSN lag and job state, never drop a live one (L-DBMI-015, L-DBMI-016, L-DBMI-050).
- Measure per table: `APPENDS` for inserts, change counters against `__TABLES__` for updates; a view over a CDC table adds no hop (L-DBMI-029).
- Before a bulk UPDATE on a captured table, list its triggers and prove `session_replication_role = replica` inside one transaction (L-DBMI-027).
- A delete that reaches the warehouse is not erasure: change history, SaaS copies and logins keep the person (L-DBMI-051).
- A hard stop of the source host leaves the jobs FAILED (PWX-36749) until `job/resume`; auto-resume on the restart window, decided on the failure time, not on log text (L-DBMI-063).

**Related:** [DBMI over REST](<01 DBMI over REST (create, deploy, run, stop).md>) · [DBMI Targets & Drivers](<03 DBMI Targets & Drivers.md>) · [Serving Outputs to BI and Apps](<../03 - Data Integration (CDI)/10 Serving Outputs to BI and Apps (freshness, latency, reverse ETL).md>) · [Cutover & Rollback](<../10 - Migration & Org Management/05 Cutover & Rollback.md>) · [Lessons: Mass Ingestion & CDC](<../13 - Lessons Learned/04 Mass Ingestion & CDC.md>)

**Last verified:** 2026-11-03

> Log-based CDC from PostgreSQL uses a Database Ingestion task in `CDC_COMBINED` mode (an initial load, then continuous apply) through a `pgoutput` slot and a dedicated publication.
> Four source rules each killed a job until they were fixed: CREATE on the schema, no `FOR ALL TABLES` publication, `REPLICA IDENTITY FULL`, and the slot created after the publication.
> `FlushPeriod` (60 s by default) is the latency floor. With 5 s, changes reached BigQuery in 15–35 s, and a hot/cold task split brought that to 10–22 s.
> One job per slot. A polling job's slot shows `active=f` between cycles, so never drop a slot a job still uses. A slot can be handed from one org's task to another's with about 70 s of lost freshness.

---

## 1. Source prerequisites

Checklist (L-DBMI-011, L-DBMI-012, 2026-06-28 to 2026-09-26):

| # | Requirement | Why | Check |
|---|---|---|---|
| 1 | `wal_level=logical` (needs a restart) | logical decoding | `SHOW wal_level;` |
| 2 | free `max_replication_slots` and `max_wal_senders` | one slot and one sender per task | `SHOW max_replication_slots; SELECT count(*) FROM pg_replication_slots;` |
| 3 | a `LOGIN REPLICATION` role with CONNECT and SELECT on the captured tables | reading changes and the initial load | `\du <cdc_user>` |
| 4 | USAGE **and CREATE** on the schema where DBMI writes `public.infa_persistent_<task>_<job>` | DBMI creates its own persistence table | the task fails without it |
| 5 | `pg_hba.conf`: `host replication <cdc_user> <agent-cidr> scram-sha-256` | replication connections from the agent host | a connection test and a deploy |
| 6 | a **dedicated** publication `FOR TABLE...` | the persistence table must not be published | `SELECT * FROM pg_publication_tables WHERE pubname='<pub>';` |
| 7 | **no** `FOR ALL TABLES` publication anywhere in the database | it would publish the persistence table, which DBMI refuses | `SELECT pubname FROM pg_publication WHERE puballtables;` returns no rows |
| 8 | `REPLICA IDENTITY FULL` on every captured table | the rule that failed the job; deletes on tables without a primary key need it too | `SELECT relname, relreplident FROM pg_class WHERE relreplident <> 'f' AND relname IN (...);` |
| 9 | the slot created **after** the publication | pgoutput decodes with the historic catalog | slot creation time later than the publication |
| 10 | `max_slot_wal_keep_size` set (for example 8GB) | a stalled slot cannot fill the disk | `SHOW max_slot_wal_keep_size;` |

The SQL, with placeholders (run it as the table owner, with a psql variable for the password):

```sql
-- 1. WAL. ALTER SYSTEM needs a restart before wal_level takes effect.
ALTER SYSTEM SET wal_level = 'logical';
ALTER SYSTEM SET max_slot_wal_keep_size = '8GB';
-- restart the instance, then: SHOW wal_level;  -- logical

-- 2. Least-privilege CDC role (L-DBMI-013)
CREATE ROLE <cdc_user> LOGIN REPLICATION PASSWORD :'pw';
GRANT CONNECT ON DATABASE <db> TO <cdc_user>;
GRANT USAGE, CREATE ON SCHEMA public TO <cdc_user>;          -- DBMI creates its persistence table here
GRANT SELECT ON public.<t1>, public.<t2> TO <cdc_user>;
ALTER DEFAULT PRIVILEGES FOR ROLE <owner> IN SCHEMA public GRANT SELECT ON TABLES TO <cdc_user>;

-- 3. A dedicated publication; drop any FOR ALL TABLES publication first
DROP PUBLICATION IF EXISTS <old_all_tables_pub>;
CREATE PUBLICATION <pub> FOR TABLE public.<t1>, public.<t2>;

-- 4. Replica identity on every captured table
ALTER TABLE public.<t1> REPLICA IDENTITY FULL;
ALTER TABLE public.<t2> REPLICA IDENTITY FULL;

-- 5. The slot, last, and only when the task is about to consume it (L-DBMI-014)
SELECT pg_create_logical_replication_slot('<slot>', 'pgoutput');
```

Rollback (stop and undeploy the DBMI job first, or the slot stays in use):

```sql
SELECT pg_drop_replication_slot('<slot>');
DROP PUBLICATION <pub>;
ALTER TABLE public.<t1> REPLICA IDENTITY DEFAULT;
DROP TABLE IF EXISTS public.infa_persistent_<task>_<job>;
REASSIGN OWNED BY <cdc_user> TO <owner>; DROP OWNED BY <cdc_user>; DROP ROLE <cdc_user>;
```

### Flipping `wal_level` safely

- Logical is a superset of replica, so an existing **physical streaming replica keeps streaming** after the flip. Check `pg_stat_replication` for `state=streaming`. Prove logical decoding by creating a test slot and dropping it again (proven 2026-07-09).
- On a containerized Postgres, first check that the compose `command:` does not pin `wal_level` (if it does not, `ALTER SYSTEM` is authoritative). Snapshot the disk, restart only that container, verify `SHOW wal_level`, and confirm the application reconnected (a restart took 12 s, 2026-06-28).
- The flip needs a restart, so schedule it in a maintenance window for production. When you enable `archive_mode` later (also a restart), keep `wal_level=logical`.

## 2. The task

Create it with the JSON in [DBMI over REST](<01 DBMI over REST (create, deploy, run, stop).md>) (section 4.1). The settings that matter for CDC (L-DBMI-017, 2026-09-26):

| Setting | Value | Note |
|---|---|---|
| `general.type` / `source.customProperties.loadType` | `combined` / `CDC_COMBINED` | an initial load, then continuous CDC |
| `source.replicationPlugin` | `pgoutput` | |
| `source.publication` and `replicationSlotName` | `<pub>`, `<slot>` | also set in the `pwx.cdcreader.postgresql.connection.repl.*` custom properties |
| `source.restartPointForIncrementalLoad` | `LATEST` | a first start with LATEST re-runs the initial load (L-DBMI-021) |
| `runtimeOptions.applyCycleIntervalSecs` | `10` (hot tables `5`) | how often a cycle applies |
| `runtimeOptions.customProperties.FlushPeriod` | `5` (hot tables `2`) | the writer flush; **60 s by default, which is the latency floor** |
| `runtimeOptions.customProperties."rat.cdcfile.cycle.interval.secs"` | the same as the apply cycle | |
| `target.dataTypeRules` | `[]` | never set rules for a BigQuery target (L-DBMI-023) |
| `target.customProperties.auditColumnsPrefix` | `INFA_` | the audit columns in the target |

The BigQuery target holds **current state** (merged on the primary key), not a change log, so put views over it for consumers. When CDC takes over a table, retire any truncate-and-reload batch job that writes the same target, because a full reload fights the stream.

## 3. Latency: what was measured

| Setup | Measured | Date | Lesson |
|---|---|---|---|
| default `FlushPeriod` (60 s) | about 85 s from source write to BigQuery | 2026-09-26 | L-DBMI-018 |
| `FlushPeriod=5`, cycle 10 s, 13 tables | 24.9 s to the CDC table, 21.9 s to a view over it | 2026-09-26 | L-DBMI-018 |
| the same, per table in one cycle | first table 15.4 s … last tables 32.9 / 34.8 s | 2026-09-28 | L-DBMI-019 |
| application event → warehouse row, end to end | 21–34 s; to a golden-record view 22–29 s | 2026-09-26 | L-DBMI-018 |
| p50 from BigQuery `APPENDS` | about 20 s | 2026-09-27 | L-DBMI-029 |
| hot task (7 tables, cycle 5 s, flush 2 s) plus cold task (7 tables, cycle 10 s, flush 5 s) | 10–22 s | 2026-09-29 | L-DBMI-019 |
| the same split over 24 h, inserts on five tables | average 25.9 s, fastest 10.0 s (n=305): 20.5 s on the hot table, 26.6-28.9 s on four transaction tables, a 10-11 s floor on every table; new-entity rows median 21.2 s, p90 29.7 s, worst 56 s (n=61) | 2026-10-01 | L-DBMI-029 |

Why the spread: within one cycle DBMI applies tables **one after another**, so the last tables in a large task land 15–20 s after the first. The fix is to split the tables users watch into a small hot task with its own publication and slot.

How to measure without instrumenting DBMI (L-DBMI-029):

- Read each row's landing time from BigQuery's `APPENDS` change-history function on the CDC tables and compare it with the source commit time.
- DBMI did not persist its commit timestamp, and `track_commit_timestamp` was off, so use the source row's `created_at` as the commit proxy.
- A cheaper check: compare the newest source `created_at` with the table's `last_modified_time` in `<dataset>.__TABLES__`.
- An end-to-end timer (write a test row, poll the warehouse and the views) catches the whole path.
- **Update-heavy traffic**, where insert probes see nothing: sample `pg_stat_user_tables` every 2 s (`n_tup_ins + n_tup_upd + n_tup_del` per table) and note when each counter moves; poll `<dataset>.__TABLES__.last_modified_time` (epoch ms) every 3 s; the first last-modified after the change is that table's apply time. Report every table, not one, and prove catch-up separately (an audit table's max id equal at the source and in the warehouse) (L-DBMI-029).
- Exclude rows copied by the initial load (they have no meaningful landing time). **A view over a CDC table** is evaluated at query time, so a record is visible in it the moment it lands: report it as the CDC figure, not as an extra hop (L-DBMI-029).
- The per-record path from the CDC table into governed tables is measured with time travel at each publish: [Performance, Concurrency & Job Caps](<../03 - Data Integration (CDI)/07 Performance, Concurrency & Job Caps.md>) §8.1.

## 4. Slots: one consumer, `active=f`, and never dropping a live slot

- **One job per slot** (L-DBMI-015). Two jobs cannot consume one logical slot. An old-org job and a new-org job writing the same warehouse tables would double-write, so never run both.
- **`active=f` is normal** (L-DBMI-016). DBMI polls (the pgoutput consumer reconnects each cycle), so `pg_replication_slots.active` is false between cycles while `confirmed_flush_lsn` keeps advancing. Alert on `pg_wal_lsn_diff(pg_current_wal_lsn, confirmed_flush_lsn)`, the DBMI job state and end-to-end freshness, never on the flag (L-DBMI-050):

```sql
SELECT slot_name, active, wal_status,
       pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn, confirmed_flush_lsn)) AS lag,
       pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn, restart_lsn))        AS retained
FROM pg_replication_slots ORDER BY 1;
```

- **An idle slot pins WAL** (L-DBMI-014). A slot nobody consumes grows until `max_slot_wal_keep_size`, then it is invalidated. Create a new slot only right before the switch that will use it; a slot created days early can fill a nearly full disk. A stopped job's slot starts retaining WAL immediately.
- **Never drop a live slot.** Cleanup scripts must refuse by default and drop a slot only when its consumer is known to be undeployed for good (L-DBMI-016, L-CLEAN-027). After a cutover that reused a slot, that slot is the live one.

## 5. Handing a slot to another org's task (cutover)

Proven 2026-09-28 (L-DBMI-020, L-DBMI-021):

1. **Before the cutover:** create or import the target task, set its slot and publication (reuse the source's, or deliberately new ones), install the driver set, and deploy it. **Do not start it.**
2. **At the switch:** `job/stop` the source job (do **not** undeploy it: it is the rollback), and wait for `stopped`.
3. `job/start` the target job on the **same slot and publication**. With CDC_COMBINED and LATEST it re-runs the initial unload into the existing target tables, then streams; the merge apply keeps parity.
4. **Verify:** one consumer on the slot, 0 errors in the new task log, every table's latest transition event `NORMAL_CONTINUOUS_CDC_TABLE` ([DBMI over REST](<01 DBMI over REST (create, deploy, run, stop).md>) §6; L-DBMI-030), and the source audit maximum equal to the warehouse's within seconds.
5. **Rollback:** stop the target job and resume the source job on the same slot.

Measured: about 70 s until the first target write, and 3 min 13 s until all 13 tables reached continuous CDC. A first attempt failed on the target (the driver set was missing), the source job was resumed while it was fixed, and that cost about 5 minutes of freshness. Stage the drivers and keys before the switch (see [DBMI Targets & Drivers](<03 DBMI Targets & Drivers.md>)).

The two slot strategies:

| Strategy | Gap | Risk | Use when |
|---|---|---|---|
| **reuse the same slot** (what ran) | about 70 s, plus a short re-baseline | none if only one job runs; rollback is stop new, resume old | the source job can be stopped cleanly |
| a **new slot**, created right before the source job stops | none | possible duplicate rows around the switch; two slots retaining WAL until the old one is dropped | the old and new tasks must overlap |

An imported task carries the **source's** slot and publication names (L-DBMI-021). Decide deliberately whether to reuse them or change them before deploying.

## 6. Splitting a task into hot and cold (L-DBMI-022, 2026-09-29)

1. Create a publication per split (`CREATE PUBLICATION <pub_hot> FOR TABLE...`, then `<pub_cold>`). For any table that is **new** to CDC, add `REPLICA IDENTITY FULL` and `GRANT SELECT` for the CDC role.
2. Create the slots (`pg_create_logical_replication_slot('<slot_hot>','pgoutput')`, then the cold one), after the publications. Make the script idempotent (`WHERE NOT EXISTS`).
3. Clone the running task's body twice (from `task/details`): new names, the split's `selectionRules`, the new slot and publication (both places), its own target directory, and the cycle and flush values. Create and deploy both tasks; **do not start them yet**.
4. Stop the old job, start the two new jobs, and watch the slot lag, the PowerExchange processes and the task-log error counts every 10 s.
5. When both are verified, undeploy the old job and drop the old slot. **That ends the rollback onto the old slot.** From then on, the new slots are the ones that must never be dropped.

## 7. Data traps

| Trap | What happens | Do this | Lesson |
|---|---|---|---|
| datatype change rules on a BigQuery target | no effect (5 spellings, 3 redeploys); a half-applied rule (staging STRING, target TIMESTAMP) made the MERGE fail and the job died silently for about 2 h | `datatypeChangeRules=[]`; recover with a redeploy (new job id) | L-DBMI-023 |
| fractional seconds ending in zero | `.46035` is stored as `.046035`: about 10% of timestamps off by < 1 s, on the initial-load and CDC paths | fix it in the views: prefer an exact batch copy's value when within 1 s; open a support case | L-DBMI-024 |
| a test UPDATE that changes nothing | not replicated | make a real change and revert it (for example ±1 µs), and time both | L-DBMI-025 |
| deleting test rows | deletes replicate to the target | purge at the source (after archiving) and the CDC copy follows | L-DBMI-026 |
| a bulk fix with `SET session_replication_role = replica` | triggers are silenced, but CDC still captures the change | use it for hygiene fixes that must not fire relays; follow the bulk-fix recipe below | L-DBMI-027 |
| a `FOR ALL TABLES` publication | DBMI refuses its published persistence table; deletes need `REPLICA IDENTITY FULL` | a dedicated publication | L-DBMI-012 |

**Bulk fixes on a captured table** (L-DBMI-027). A one-off backfill can fan out through row triggers: an `AFTER INSERT OR UPDATE... FOR EACH ROW` trigger that calls `pg_notify` for a real-time relay would turn a ~590-row key backfill into ~590 CAI-to-SaaS upserts.
1. List the triggers: `SELECT tgname, pg_get_triggerdef(t.oid) FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid WHERE c.relname IN ('<table>') AND NOT tgisinternal;`
2. In **one explicit transaction** (not autocommit: `SET LOCAL` has no effect outside a transaction block): `BEGIN; SET LOCAL session_replication_role = replica; SHOW session_replication_role;` and abort unless it returns `replica`. Setting it needs a superuser (or a role granted SET on it); if the SET fails, roll back before changing anything.
3. `CREATE TABLE <table>_bak_<tag> AS SELECT <key>, <col> FROM <table>;` then the UPDATE; `COMMIT;`
4. Verify the change reached the warehouse through CDC (WAL still captures it) and that the relay and the SaaS saw no burst.
5. Keep the undo: `UPDATE <table> t SET <col> = b.<col> FROM <table>_bak_<tag> b WHERE b.<key> = t.<key>;`

### 7.1 Deletes, erasure and history (L-DBMI-051)

A delete in the operational database flows through CDC to the warehouse tables (L-DBMI-026), but that is not erasure: the warehouse change history (`APPENDS` and time travel, about 7 days) still returns the deleted rows, a CRM contact created by a real-time process or a batch upsert keeps name, email and phone, and the identity provider keeps the login. An erasure path needs explicit fan-out and a check per system: delete or anonymize the CRM record (a minute-level job anonymized one in about 36 s), delete the login, keep only a tombstone without personal data, exclude erased keys from every reverse-ETL and SaaS upsert, and document the residual window of warehouse time travel (or shorten the dataset's time-travel window if policy requires).

## 8. The watchdog (L-DBMI-028)

Run it every 5 minutes (cron) and pause it explicitly during planned redeploys:

1. **Job:** `GET /dbmi/api/v1/task/<taskId>/job` must say `running`. Treat `awaiting_auto_restart` as transient for at least 30 minutes after an agent restart: after a host reboot the jobs came back to `running` by themselves about 20 minutes after boot, with slot lag back to 0 (L-DBMI-028, L-ENV-069). A hard stop of the **source** host is different: two jobs failed with PWX-36749 'Call to read from a replication slot failed' (Not retriable) and stayed failed for 3 days after the database returned (L-DBMI-063, 2026-11-02).
2. **Slot:** it exists, and `pg_wal_lsn_diff(pg_current_wal_lsn, confirmed_flush_lsn)` is below a threshold (for example 256 MB).
3. **Freshness:** the newest source audit row older than 5 minutes is present in the warehouse.
4. **Auto-resume**, only when the newest task log shows a transient warehouse error (`Retrying the job may solve the problem`, `100032`, `backendError`, `rateLimitExceeded`) and no schema or type error (`Value of type`, `cannot be assigned to`, `does not exist`, `Permission denied`). At most 3 resumes per rolling hour; anything else is left for a human. Also auto-resume a job whose failure `endTime` falls in a window around a source restart (30 minutes before to 15 minutes after the database's start time, or the start of the tunnel the agent reads through), at most 3 times per hour: it passed 5 of 5 simulated cuts. Decide on the failure time, not on log text: a log-based watchdog never fired because it read task logs from the old agent host after a runtime move (L-DBMI-063).
5. **Alert only on state changes** (PROBLEM and RECOVERED), and append one health row per run for dashboards. Send them to a channel someone works: the 3-day outage above sat in an unread inbox (L-DBMI-063).
6. **Per table:** read each table's latest transition event from the newest task log ([DBMI over REST](<01 DBMI over REST (create, deploy, run, stop).md>) §6); a table not in `NORMAL_CONTINUOUS_CDC_TABLE` is not streaming (L-DBMI-030).

Without it, one job died silently for 2 hours and another stopped on a transient error and froze the views for more than 2 hours.

After a resume, the first apply cycle took 73 s and steady state returned to about 21 s; drop latency samples that span
an outage, or the catch-up shows an 'average latency' of tens of thousands of seconds (L-DBMI-063).

## 9. When not to use log-based CDC, and where it fits

- A watermark-based incremental MERGE (read the watermark, MERGE rows newer than the watermark minus a lookback, write back MAX(ts)) is cheap and idempotent (a 97.4% scan cut), but it cannot see UPDATEs or DELETEs on tables without `updated_at`. Use CDC for those, or add an application-maintained `updated_at` (L-DBMI-043, 2026-07-04).
- CDC runs on the ingestion runtime, not the Data Quality service. AWS DMS, GCP Datastream, Databricks Lakeflow Connect, Snowflake Openflow and Fabric Mirroring also do log-based CDC, but they only replicate rows; Informatica's distinct edge is mainframe and legacy CDC through PowerExchange (L-DBMI-042, 2026-08-14).
- A running CDC job kept working when the org's monthly job limit stopped all CDI runs (L-DBMI-044, 2026-09-28), so CDC is the per-event freshness path that survives a job cap.

## 10. Overturned beliefs

| Earlier belief (dates) | What overturned it | Lessons |
|---|---|---|
| "Author the first CDC task in the UI wizard, then clone it" (2026-07-04 to 2026-09-21) | `task/create` from JSON | L-DBMI-048 → L-DBMI-003 |
| "A datatype rule timestamptz → STRING fixes the fractional-seconds defect" (2026-09-26) | rules are no-ops for BigQuery, and a half-applied rule killed the job; the fix moved to views | L-DBMI-049 → L-DBMI-023 |
| "Create a new target slot for the org move" (the staged plan, 2026-09-28) | not overturned but not used: reusing the same slot worked, with a single consumer and a trivial rollback | L-DBMI-020 |

## 11. Lessons in this doc

L-DBMI-011 to L-DBMI-029, L-DBMI-042 to L-DBMI-044, L-DBMI-063, L-CLEAN-027, and the superseded L-DBMI-048 and L-DBMI-049. Full text: [Lessons: Mass Ingestion & CDC](<../13 - Lessons Learned/04 Mass Ingestion & CDC.md>).
