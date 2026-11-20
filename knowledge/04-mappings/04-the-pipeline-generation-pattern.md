# The Pipeline-Generation Pattern

**Answers:** How to generate a whole CDI pipeline from SQL files and a spec: inputs, layering and naming, the idempotent create-or-update algorithm, the special task shapes (reverse-ETL, SaaS upsert, flat file, JDBC V2, incremental, snapshots), the guards around each cycle, the plan file, lanes, taskflows and schedules.

**Read when:** when building or rebuilding a task-based pipeline headless, or when a generator, orchestrator plan or lane definition needs changing.

**Key rules:**
- Create or update every task by name in one folder and never duplicate; resolve per-org ids at start-up (L-CDI-083, L-CDI-084, L-CDI-097).
- Keep one plan file per org; it is the contract with the orchestrator, and its `reads` must be complete (L-CDI-096, L-CDI-127).
- Guard every outbound SaaS upsert with a count gate, a test-identity exclusion and a retention window sized to the target's storage (L-CDI-091, L-CONN-088).
- Truncate the targets of 0-row successes yourself, stage by stage (L-CDI-088).
- A reverse-ETL guard trigger that reverts NULL-over-value must still let the application clear a field explicitly (L-CDI-209).
- Patch the generator the same day as any manual fix, or the next rebuild reverts it (L-CDI-135).

**Related:** [02 How Claude Builds Mappings Headless](02-how-claude-builds-mappings-headless.md) · [04 Taskflows & Schedules](../05-taskflows-schedules/01-taskflows-schedules.md) · [06 Mapping Design & Consolidation](05-mapping-design-consolidation.md) · [07 Performance, Concurrency & Job Caps](06-performance-concurrency-job-caps.md) · [Lessons: CDI](lessons.md)

**Last verified:** 2026-11-03

> **Summary.** A whole CDI pipeline can be generated headless from files: a directory of SQL (one file per curated table), a small spec (targets, reads, kind) and a table list become one mapping task per SQL. The tasks are created or updated **idempotently by name**, placed in one folder and tagged, then chained into linear taskflows per lane and bound to schedules.
> The layering is landing (typed bronze) → raw (STRING) → staging → gold → serving views, plus reverse-ETL, SaaS upserts and evidence tasks, each a variant of the same task body.
> The generator also writes a plan file, the contract with whatever orchestrates the runs.
> This page is the generic version of a generator that built and rebuilt 159 production tasks. For its successor, which emits real mappings instead of tasks, see route 5 in [02](02-how-claude-builds-mappings-headless.md) and [06](05-mapping-design-consolidation.md).

---

## 1. The shape of it

```
 SQL files (one per table/mart) ─┐
 spec: name, sql, target,         │     ┌──────────────── generator (idempotent) ────────────────┐
       reads, kind, view?        ├──▶  │ 1 ensure project/folder   5 medallion tasks (topo order) │
 landing table list              │     │ 2 landing tasks per table 6 special shapes              │
 mode: live | shadow ────────────┘     │ 3 raw layer (task or view) 7 plan file                  │
                                        │ 4 guards metadata         8 taskflows per lane, schedule│
                                        └──────────────┬──────────────────────────────────────────┘
                                                       ▼
                       IDMC: N mapping tasks + lane taskflows + schedules   ◀── orchestrator reads the plan file
```

Everything the generator creates is a mapping task over one proven template task (route 1 in [02](02-how-claude-builds-mappings-headless.md)). A re-run rewrites the same tasks in place and never duplicates them (L-CDI-083, L-CDI-084).

## 2. Inputs

| Input | Content | Notes |
|---|---|---|
| SQL directory | `<name>.sql` per curated table or mart, written in the source warehouse's dialect | Reference datasets by **logical** names (`raw.`, `staging.`, `<gold>.`); the generator rewrites them per mode (L-CDI-085) |
| Spec (YAML/JSON) | One entry per task: `name`, `sql`, `target` (`<logical_ds>.<table>`), `reads` (upstream tables), `kind` (cleanse / curate / cdq / reverse_etl / post …), optional `materialization: view` | `reads` drives the topological order, the lanes and later the DAG ([07](06-performance-concurrency-job-caps.md)). Keep it complete: undeclared reads broke staging later (L-CDI-127) |
| Landing table list | Source tables to land | Column metadata is read live from `information_schema.columns` |
| Mode | `live` or `shadow` | Shadow maps every logical dataset to a twin and the source views to a shadow schema, so the whole chain can be built and compared without touching what apps read (L-CDI-136) |
| Per-org constants | Template task id, connection ids, runtime-environment id, project/folder ids | Resolve them **by name inside the target org** at start-up and cache them per org. Hard-coded ids went stale after an org move (L-CDI-097) |

## 3. Layering and naming

| Layer | Dataset (placeholder) | Written by | Content |
|---|---|---|---|
| Landing (typed bronze) | `<land_ds>` | one landing task per source table | Source columns, typed. Long text goes to **JSON-typed** columns (L-CDI-153) |
| Raw (STRING) | `<raw_ds>` | one raw task per table, **or** a view | A STRING projection of landing, byte-identical to what downstream SQL expects (L-CDI-086) |
| Staging | `<staging_ds>` | cleanse / standardize / score tasks | Cleansed, standardized, DQ-flagged rows |
| Gold | `<gold_ds>` | curate / facts / marts / DQ-results / scorecard tasks | Golden records, facts, marts, DQ results |
| Serving | views in `<gold_ds>` | DDL run by the orchestrator (`materialization: view`) | Not tasks |
| Outbound | app database, SaaS | reverse-ETL and SaaS upsert tasks, last in the lane | Upserts keyed on business or external ids |
| Evidence | `<gold_ds>` | append-only snapshot tasks and the run log | History for BI and audit (L-CDI-094) |

Naming conventions that kept the folder readable and every object findable by prefix:
- Tasks: `mt_<app>_land_<table>`, `mt_<app>_raw_<table>`, `mt_<app>_stg_<entity>`, `mt_<app>_<mart>`, `mt_<app>_revetl_<system>`, `mt_<app>_sfdc_<object>`.
- Linear taskflows: `wf_<app>_<lane>`. Schedules: `<tag>_<app>_<cadence>`. Mappings (route 5): `m_<domain>_<purpose>` with its task `mt_<domain>_<purpose>`, kept 1:1 and same-named (L-CDI-111).
- Suffixes: `_shadow` for shadow-mode copies, `_v2` for a consolidated generation. Descriptions start with `[<tag>]`.
- One project and one folder hold every object of the team. The service is carried by the name prefix, not by subfolders. Every object carries the tag `<tag>`; projects and folders cannot be tagged, so the project name is the marker (L-CDI-054).
- Organization-level objects (connections, runtime environments, agents, schedules) cannot live in folders. Identify them by name prefix or description.

## 4. The algorithm (pseudocode)

```python
# ---------- 0. session, org, home ----------
assert GET("/api/v2/org").id == EXPECTED_ORG            # every write script asserts the org first
home = ensure_home(project="<project>", folder="<folder>")   # v3: find by q=type=='PROJECT'/'FOLDER', else create; cache per org
TPL = lookup_template_task(org)                          # a proven task over dsst__copy_data_new_tgt, resolved by name in this org
existing = {t.name: t.id for t in GET("/api/v2/task?type=MTT")}   # cached for the whole run

def upsert(name, desc, src_conn, custom_query, target, src_object=None, runtime_meta=False):
    body = clone(GET(f"/api/v2/mttask/{TPL}"), strip=["id","orgId","createTime","updateTime","createdBy","updatedBy","frsGuid"])
    body.update(name=name, description=desc, shortDescription=desc, sessionProperties={})
    set_source(body, src_conn, custom_query, src_object or "DUMMY_Source")    # see 02 §3 for the exact keys
    set_target(body, target, writeMode="Bulk", writeDisposition="Write truncate")
    if runtime_meta: set_fetch_mode(body, "RUNTIME")     # the target gained columns since creation (L-CDI-049)
    if name in existing:                                  # update in place: same id, same frsGuid
        tid = existing[name]; cur = GET(f"/api/v2/mttask/{tid}")
        body.update(id=tid, frsGuid=cur.frsGuid); r = POST(f"/api/v2/mttask/{tid}", body)
    else:
        r = POST("/api/v2/mttask", body); tid = r.id; existing[name] = tid
        frs_move([tid], home.folder); tag([frsGuid_of(tid)], "<tag>")   # born in Default (L-CDI-016)
    require(r.status == 200, r.text[:300])
    return tid

# ---------- 1. landing: source -> typed bronze ----------
for t in LANDING_TABLES:
    meta = pg_columns(t)                                  # name, data_type, numeric_scale from information_schema
    long = [c for c in meta if c.type in ("json","jsonb") or c.name in LONGTEXT_COLS.get(t, [])]
    if any(c.type in ("json","jsonb") for c in meta):
        create_or_replace_view(f"{SRC_SCHEMA}.{t}", cast_jsonb_to_text=True)   # PG connector cannot land jsonb
        src = f"{SRC_SCHEMA}/VIEW/{t}"
    else:
        src = f"public/TABLE/{t}"                         # the only object-path shapes that resolve (L-CDI-162)
    if long: ensure_json_columns(f"{LAND}.{t}", long)     # one-time: rebuild the landing table with JSON-typed columns
    tid = upsert(f"mt_<app>_land_{t}", "...", PG_CONN, None, f"{LAND}/{t}", src_object=src)
    plan.landing.append({name, id: tid, target: f"{LAND}.{t}", pg_table: t, chunked: long, chunk_capacity: 32000})

    # ---------- 2. raw STRING layer ----------
    raw_sql = raw_select(meta, f"{LAND}.{t}", long)       # JSON_VALUE / FORMAT / FORMAT_TIMESTAMP / CAST (L-CDI-086)
    if long:                                              # an IDMC STRING write would re-cut the long text to 255
        plan.raw_views.append({target: f"{RAW}.{t}", sql: raw_sql})     # a view, recreated by DDL each cycle
    else:
        rid = upsert(f"mt_<app>_raw_{t}", "...", WH_CONN, raw_sql, f"{RAW}/{t}")
        plan.raw.append({name, id: rid, target: f"{RAW}.{t}", kind: "raw"})

# ---------- 3. medallion ----------
for e in topo_sort(spec.tasks, by="reads"):               # upstream first
    sql = rewrite_datasets(clean_sql(read(e.sql)), DS[mode])   # strip comments, non-ASCII, trailing ';' (L-CDI-024)
    if e.materialization == "view":
        plan.views.append({name: e.name, target: e.target, ddl: f"CREATE OR REPLACE VIEW `{WH}.{e.target}` AS {sql}"})
        continue
    tid = upsert(f"mt_<app>_{e.name}", f"[<tag>] {e.kind}: {e.sql} -> {e.target}", WH_CONN, sql,
                 e.target.replace(".", "/"), runtime_meta=e.name in RUNTIME_META)
    plan.medallion.append({name, id: tid, target: e.target, kind: e.kind, reads: e.reads})

# ---------- 4. special shapes (section 5), 5. plan file, 6. lanes, 7. schedules ----------
if not partial_build: write_json(f"plan_{mode}.json", plan)      # a --only build never overwrites the plan
for lane, tasks in orchestrator_lane_order.items():            # landing -> raw -> medallion waves; SaaS last
    upsert_linear_taskflow(f"wf_<app>_{lane}", tasks, keep_schedule=True)   # 04 §2
bind_schedules(created_unbound=True)                             # 04 §4-5
```

Helper details:
- **`clean_sql`**: drop comment lines and trailing `[ \t]--…` comments, strip non-ASCII (`encode("ascii","ignore")`), strip the trailing `;`. The only non-ASCII characters were in comments, and they failed the BigQuery reader with "missing CR" (L-CDI-024, 2026-09-24).
- **`rewrite_datasets`**: a regex per logical dataset that skips names already qualified, `(?<![\w`.])<logical>\.` → `` `<cloud-project>`.<physical>. ``, with one mapping dict per mode (L-CDI-085, 2026-09-23).
- **`raw_select`**: `JSON_VALUE(col)` for JSON columns; `FORMAT('%.<scale>f', col)` for scaled numerics; `FORMAT_TIMESTAMP('%Y-%m-%d %H:%M:%S+00:00', col, 'UTC')`, or the `%E6S` form when microseconds are non-zero, for timestamps; `CAST(col AS STRING)` otherwise. Booleans already land as `'true'`/`'false'` (L-CDI-157).
- **`topo_sort`**: depth-first over `reads`, restricted to targets the spec itself writes. A cycle is a spec error.
- **`frs_move`**: FRS `MoveEntities` in chunks of at most 25 ids; log every non-`FRS_200` item ([03](03-mapping-tasks-create-update-run-monitor.md) §7).

## 5. Special task shapes (same template, different `$Target$`)

| Shape | `$Source$` | `$Target$` (changes from the default) | Lesson |
|---|---|---|---|
| **Reverse-ETL into PostgreSQL** | Warehouse `customQuery` with `QUALIFY ROW_NUMBER OVER (PARTITION BY <key> ORDER BY <built_at> DESC, <id>) = 1` | `targetConnectionId=<pgConnId>`; `targetObject = objectName = "<schema>/TABLE/<table>"`; `targetObjectLabel = objectLabel = "<table>"`; pop `newObjectName`; `newObject=false`; `tgtObjectAttributes = runtimeAttrs = oprRuntimeAttrs = {}`; `operationType="Upsert"`; `targetUpdateColumns=[<key>]`; `truncateTarget=false` | L-CDI-089 |
| **SaaS upsert** (e.g. Salesforce) | Warehouse `customQuery` whose column aliases are the API field names (lookups filled with record Ids, or relationship fields) | `targetConnectionId=<sfConnId>`; `targetObject = objectName =` labels `= "<SObject>"`; pop `newObjectName`; `newObject=false`; `operationType="Upsert"`; `targetUpdateColumns=["<ExtId__c>"]`. If the agent's connector misbehaves, set the task-level `runtimeEnvironmentId=<hostedReId>` and drop `agentId` | L-CDI-090, L-CDI-170 |
| **SaaS read-back** | The SObject (no `customQuery`) | Warehouse `<ds>/sf_ids_<object>`, Write truncate | L-CDI-118 (prefer external-ID relationships instead) |
| **Flat-file ingest** | A cloned flat-file landing task; `extendedObject` name = `<file>.csv`; `srcFFAttrs = {"@type":"flatFileAttrs","delimiter":",","textQualifier":"\"","escapeChar":"","headerLineNo":1,"firstDataRow":2,"consecutiveDelimiterAsOne":false}`; `fetchMode:"RUNTIME"` | Warehouse table, Write truncate | L-CDI-095 |
| **JDBC V2 full reload** (MySQL-protocol warehouse) | Warehouse query or source table | `runtimeAttrs = {"Pre SQL": "TRUNCATE TABLE <t>"}` (key with the space). JDBC V2 ignores `truncateTarget` | L-CDI-171 |
| **Incremental append** | `customQuery` that keeps only ids absent from the target within a lookback window, deduplicated with `QUALIFY ROW_NUMBER OVER (PARTITION BY <id> ORDER BY <ts>) = 1` | `operationType="Insert"`; `oprRuntimeAttrs.writeDisposition="Write append"`; `newObject=false` | L-CDI-092 |
| **Append-only evidence snapshot** | `customQuery` ending in `WHERE NOT EXISTS (SELECT 1 FROM <target> WHERE snapshot_date = CURRENT_DATE)` for a once-per-day snapshot | Write append (set after creation, §6) | L-CDI-094 |
| **Post only valid rows** into a system-of-record table | Query over the validated staging table | `operationType="Insert"`, `truncateTarget=false`, plus an idempotency trigger in the database (skip an insert whose business key exists) | L-CDI-169 |

**Guards inside outbound SQL** (L-CDI-091, 2026-09-28), appended by the generator to every SaaS upsert query:
- **Count gate.** Push nothing unless this cycle's count of valid golden records is at least 80% of what the SaaS already holds, so a broken upstream load never overwrites good CRM data.
- **Test-identity exclusion.** One shared regex keeps synthetic identities out; it matches the BI layer's test filter. Deleting test records in the target is pointless while the next run re-creates them.
- **Retention window.** Child objects older than N days are skipped when the target org's storage is small. Size N to the org: a 60-day window of activity, booking and visit children kept a 5 MB CRM org full, while 7 days plus a daily retention job left about 600 records of headroom (L-CONN-088; [09](08-source-target-gotchas.md) §3).

**Changing the write mode of an existing task** (L-CDI-051): `GET /api/v2/mttask/<id>`; if `$Target$.oprRuntimeAttrs.writeDisposition` already equals the wanted value, stop. Otherwise set `{"writeMode":"Bulk","writeDisposition":"Write append"}`, drop the audit fields and POST back to `/api/v2/mttask/<id>`.

## 6. Guards and housekeeping around each cycle

These run in the orchestrator, outside IDMC, because the connector behaviours below cannot be fixed inside a task:

| Guard | When | What | Lesson |
|---|---|---|---|
| Long-text capacity | Before landing | Longest value of each long-text column in the source; abort if any exceeds 32,000 characters (the JSON landing cap) | L-CDI-087 |
| Enforce empty targets | After each stage (landing, then raw) | Bulk + Write truncate **skips** a 0-row load, so the table keeps stale rows. For every task that SUCCEEDED writing 0 rows, run `TRUNCATE TABLE` on its target. Stage by stage, so an emptied landing table cascades | L-CDI-088 |
| Raw and serving views | Start of the raw stage; end of the lane | `CREATE OR REPLACE VIEW`. Delete a legacy TABLE standing where the view goes | L-CDI-086 |
| Truncation suspects | After a full cycle | For every IDMC-written table: `max(length(col))` of STRING columns and `max(length(JSON_VALUE(col)))` of JSON columns. Exactly 255 or exactly 32,000 means probable truncation, so fail the cycle. Full lane only, to spare the warehouse | L-CDI-087 |
| Newly long column | When the truncation guard trips | Add the column to the long-text list: JSON landing column, raw view, delete the redundant raw task, then force a full run to verify full-length values | L-CDI-087 |
| Run log (lineage) | After each lane | One row per task run (`run_id, task, kind, target, rows_written, status, error, started_at, ended_at`; the activity log keeps only about 1,000 entries for a busy project, so this is the run history, L-CDI-288) appended with a **load job**, not streaming, so it can be queried and corrected at once. A failed log write never masks the pipeline result. After a restart, rebuild the "last run" view from it. For multi-target mappings log one row per table from `transformationEntries` | L-CDI-094, L-CDI-158, L-CDI-198 |
| Reverse-ETL NULL guard | On every write into the operational database | A trigger reverts a NULL written over a non-NULL governed value, so a broken upstream load cannot blank fields. It must still allow a legitimate clear (a cancellation that empties a tier): the application runs `SET LOCAL <namespace>.allow_clear = 'on'` only for an explicit clear, and the trigger returns `NEW` unchanged when `current_setting('<namespace>.allow_clear', true) = 'on'`. IDMC writes never set it, so they stay guarded. Test in a rolled-back transaction: without the flag a NULL is reverted, with it the NULL lands, and the flag is gone after commit | L-CDI-209 |

Two more guards from a capture and verification build (2026-11-01):

| Guard | When | What | Lesson |
|---|---|---|---|
| Retry classifier | Each failed run | Retry up to 3 times only on transport and capacity errors (agent disconnection, Premature EOF, too many simultaneous queries, timeouts, 502/503/504, 'not available', 'job not found on agent'); cast, null, constraint, permission and repository-save errors are fixed, never retried | L-CDI-287 |
| Resumable sweep | Each batch of a verification or enrichment sweep | Select the next batch by an anti-join to the stored results on an input fingerprint plus the reference-data version, never from a cursor kept in deletable control rows (deleting them restarted two sweeps from the first key and repeated metered calls); dedupe inputs by fingerprint first | L-CDI-283 |

## 7. The plan file: the contract with the orchestrator

```json
{"mode": "live",
 "landing":   [{"name": "...", "id": "<taskId>", "target": "<land_ds>.<t>", "pg_table": "<t>", "chunked": ["<long col>"], "chunk_capacity": 32000}],
 "raw":       [{"name": "...", "id": "<taskId>", "target": "<raw_ds>.<t>", "kind": "raw"}],
 "raw_views": [{"target": "<raw_ds>.<t>", "sql": "SELECT..."}],
 "medallion": [{"name": "...", "id": "<taskId>", "target": "<ds>.<t>", "kind": "cleanse", "reads": ["<raw_ds>.<t>"]}],
 "views":     [{"name": "...", "target": "<gold_ds>.<v>", "ddl": "CREATE OR REPLACE VIEW..."}]}
```

- Ids in the plan are **v2 task ids**. The orchestrator runs tasks and lanes by these ids and mirrors their states.
- Keep **one plan per org**, and treat every copy (baked into an image, or copied to another host) as generated from it. Three copies drifted, and one still held the previous org's ids after a migration (L-CDI-096, 2026-09-29).
- `reads` must be complete. A task that reads a raw **view** reads that view's landing table. The staging and DAG logic in [07](06-performance-concurrency-job-caps.md) is only as good as these declarations.

## 8. Lanes, taskflows and schedules

1. **Lanes** are subsets of the task universe, each with a trigger. *full*: everything, on a schedule. *per-record*: the tasks one golden record and its DQ need, plus the outbound syncs; started per sign-up. *activity*: the facts and marts fed by transactional events. *files*: land → cleanse → ready/quarantine → post; started by a watched folder.
2. **Order** each lane landing → raw → medallion dependency waves, with outbound SaaS tasks last in parent → read-back → child order. Generate the taskflows from the orchestrator's lane order so the two never disagree.
3. **Taskflows**: one linear taskflow per lane, created or updated by name with `POST /api/v2/workflow[/<wfId>]`, **keeping its `scheduleId`** on update ([04](../05-taskflows-schedules/01-taskflows-schedules.md) §2). Move it into the folder by its v3 id (resolved by name among `WORKFLOW` objects) and write `lane → {id, name, tasks}` to a workflows file the orchestrator reads.
4. **Parallel lanes over one mapping** (L-CDI-285, L-CDI-286, L-CDI-292, 2026-11-01 to 2026-11-03): one mapping whose Source query is the in-out parameter `$$SRC_SQL`, cloned into N tasks, each with its own `parameterFileName` staged on the agent before each run ([03](03-mapping-tasks-create-update-run-monitor.md) §2). Shard on a key that is never NULL (a whole-row hash such as ClickHouse `cityHash64(*)` is NULL when any column is, so those rows land in no shard), reconcile the shard totals against the source count, cap memory and threads inside every lane's source query, and run about 3 heavy lanes at once: uncapped lanes exhausted the database and killed each other's long reads.
5. **Schedules**: create them from an explicit body, never by cloning another application's schedule (that template schedule was later deleted with its app; L-CDI-079). Create them unbound, bind them in one step, and read back `scheduleId` ([04](../05-taskflows-schedules/01-taskflows-schedules.md) §4–5).

## 9. Orchestration options, in the order they were used

| Stage | Mechanism | Measured | Lesson |
|---|---|---|---|
| RunAJob waves (July) | A script fires tasks with `POST /api/v2/job` in dependency waves, barrier-polls the activity log, pre-truncates targets, and fails loudly on state 3 | 22 tasks in 5 waves, exact baseline match | L-CDI-072 |
| External runner (September) | Waves in parallel inside a wave, a single-writer lock, capacity and truncation guards, one lineage row per run | 46 tasks, ~1.5M rows, 12–13 min per cycle | L-CDI-102 |
| Linear taskflows on IDMC schedules | IDMC runs the lane; the controller starts or adopts it and mirrors children from `entries[]` | 50 tasks in 15 min; 62 tasks in 21.6–24.5 min | L-CDI-069, L-CDI-122 |
| Controller-staged lanes | The controller starts each task (still `POST /api/v2/job`, still in IDMC) when its dependencies finish, at most N at once | 16-task lane 462 s → 215 s at N=4 | L-CDI-125, L-CDI-126 |
| Consolidated mappings under the same controller | Generated multi-target mappings (route 5) replace most tasks; per-table conflict locks let event lanes run beside a full refresh | event lane 16 tasks → 7 jobs (96 s average); full lane 62 tasks → 23 jobs (258-358 s) | L-CDI-119, L-CDI-128 |

Each stage kept every task running **in IDMC**. Only the starter changed.

## 10. Pitfalls this pattern hit

- **Stale ids and hosts.** The builders kept the previous org's template, connection and runtime-environment ids after an org move, and a controller image had 72 task, taskflow and agent ids baked in. Resolve per-org ids at start-up, and derive hosts from the login answer: the CAI host is `https://<pod>-cai.<rest of the pod host>`, not a string replace of one pod literal (L-CDI-097).
- **Copies of the builder.** The same builder lived in two or three directories and fixes landed in one copy only. Keep one canonical generator and make the others generated or deleted.
- **Rebuild must equal live.** After any manual fix to a task (an SQL change, a write mode), patch the generator the same day. The next rebuild otherwise silently reverts the fix ([08](07-changing-pipelines-safely.md)).
- **Shadow objects linger.** 46 unscheduled `_shadow` tasks stayed for days and inflated the design to 160 tasks. Delete them right after the proof (L-CDI-148).
- **Same names elsewhere.** Other folders of the same org held tasks with the same names. Build the name → id cache from the list, but create, run and delete by id (L-CDI-010).
- **Folder audits with the wrong type name.** A placement guard filtering on `type=='DBMI'` instead of `'DBMI_TASK'` silently matched nothing (L-CDI-011).
- **Production still on the old engine.** On-demand runs were green while the production cron still ran the retired SQL. Check what the scheduler really calls (L-CDI-066).
- **One mapping per table by accident.** A generated build ended with 357 mappings for 354 tasks because a task's `customQuery` edit is ignored on a fixed-source mapping; parameterize the source query instead (L-CDI-284).
- **Names the next step refuses.** A mapping named with parentheses imported, then its task create failed `APP_13500` and the deploy stopped halfway (L-CDI-280).

## 11. Starting from dbt or hand SQL: the staged method (proven 2026-08-18/19)

1. **Prove the old tool is a thin orchestrator.** Rebuild every mart from the tool's **compiled** SQL into a scratch schema with zero changes, and run the existing DQ gate against the scratch copy. Require a byte-identical match (21/21 checks here). The per-mart SQL files then become the spec (L-CDI-099).
2. **One technique for every mart:** a Query source with the mart's SELECT verbatim, executed by the warehouse; the target the same table name in a scratch schema; Insert with a manual `TRUNCATE` per run; poll by `runId`; exact parity against live plus a `SHOW CREATE` comparison. Easy and hard marts differ only in SQL size.
3. **Stage the prerequisites without switching anything.** The legacy pipeline stays live, and "runs on IDMC" is claimed only when IDMC produces the tables.
4. **Cut over consumers only after full parity**, then stop the old engine and keep it behind a default-off emergency flag (L-CDI-066).

Related techniques:
- **Recover lost SQL.** Search the warehouse's job history for jobs whose destination is each mart, validate the recovered statement against the current table (12/14 exact here; the other 2 were stale one-off snapshots), and make that the spec (L-CDI-101).
- **Drifting source schemas.** When two producers write the same table under different column names, make the landing view schema-adaptive: add `<physical> AS <canonical>` for each missing canonical name, found by introspecting the physical columns. Downstream SQL keeps canonical names (L-CDI-100).
- **A second schema with the same table names.** Land it into its own dataset (or with a prefix) using `<schema>/TABLE/<table>`. Give large cross-cloud full reloads a daily schedule rather than an hourly lane, to limit egress (L-CDI-098).
- **Full reloads that should be incremental.** Use a watermark store: MERGE rows changed after (watermark − lookback), then write back the new MAX (L-CDI-093).
