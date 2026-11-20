# Build a CDI mapping headless: cheat sheet

Build, deploy, run and prove an IDMC Data Integration mapping and its mapping task without the designer, on the source
and target the user named; for any new mapping, a rebuild, or a change to a live mapping or task.

**Start with:** `/idmc-mp:new-pipeline <source> to <target>` ([command](../../commands/new-pipeline.md)) and the
generator `toolkit/mapgen/mapgen.py` ([README](../../toolkit/mapgen/README.md)). Open
[00 Mapping Fast Path](00-mapping-fast-path-read-this-first.md) first: it holds the ten commands, the per-connector
settings and the costly errors. A slow or costly pipeline: `/idmc-mp:optimize` ([command](../../commands/optimize.md)).

> The generator's writes (`import`, `task`, `run`, `deploy`) are dry runs until `--execute --expect-org <orgIdV3>`.
> `run` starts a job that counts against the job budget and IPUs: ask the user first.

## What works (headless)

| Task | How (exact route / tool / command) | Lesson |
|---|---|---|
| Prove the org | `python3 toolkit/check_login.py`: one attempt only, rejected logins lock the account (IDS_086) | Fast Path §1 |
| Fill ids from names | `mapgen.py --profile profile.json resolve --write` (every connection has a `kind`) | Fast Path §1 |
| Create a mapping | spec → lint → package → v3 import → mapping task (`mapgen.py ... deploy <spec>.json`): route 5 | L-CDI-033, L-CDI-204 |
| A connector or transformation with no template | exemplar route: export a mapping that uses it (`toolkit/lib/idmc_export_import.py export --id <frsGuid> --out exemplar.zip`), read it with `toolkit/mapgen/exemplar.py` | Fast Path §7.0 |
| Rebuild or retarget a mapping | OVERWRITE import under the same mapping id (the generator finds it by name in the folder) | L-CDI-050, L-CDI-145 |
| Create a mapping task | `deploy` creates or reuses `taskName`; raw: `POST /api/v2/mttask` with `{mappingId, runtimeEnvironmentId}` | L-CDI-037 |
| Update a mapping task | POST the full body to `/api/v2/mttask/<id>` and read it back; PUT is 405 | L-CDI-046 |
| Run and poll | `POST /api/v2/job` by v2 `taskId`; poll `activityLog?taskId=<id>&rowLimit=1` until YOUR `runId` has `endTime` | L-CDI-057, L-CDI-059 |
| Read what the engine did | `mapgen.py log <task>`; REST `GET /api/v2/activity/activityLog/<entryId>/sessionLog` | L-CDI-211 |
| Per-target rows of a multi-target mapping | `transformationEntries` of the activity-log row | L-CDI-198 |
| Full SQL ELT (pushdown) | three keys on the v2 mapping task; proved only by `OPT_63367` in the session log | L-CDI-202 |
| Change one template task's SQL | `toolkit/lib/idmc_mttask.py set-query` (anchored replace), with backup and read-back | L-CDI-135, L-CDI-196 |
| Run a Dynamic Mapping Task (Reported) | `POST /batch-mapping/api/v1/Job {"taskFrsId"}` on the pod host, monitor `.../Job/monitor/task/<taskFrsId>/run/<runId>`, stop `.../Job/stop`; never v2 `job` or `activityLog` | L-CDI-327, L-CDI-289 |
| Validate an expression before embedding it (Reported) | `POST /api/v2/expression/validate {"@type":"expressionValidation","expr",...}` | L-CDI-311 |

## What doesn't work, and the workaround

| Wall | Workaround | Lesson |
|---|---|---|
| `POST /api/v2/mapping` (400) or `POST /public/core/v3/objects` (405) to create a mapping | an import package from the generator | L-CDI-020 |
| POST new targets to a task over a real mapping: 200, nothing changes | re-import the mapping OVERWRITE under the same GUID, then re-read the task | L-CDI-050 |
| Edit `$Source$.customQuery` on a task over a fixed-source mapping: the run ignores it | make the source query an in-out parameter | L-CDI-284 |
| Browse a connection's objects or fields over REST (404s) | declare fields from the database's own catalog right before the build | L-CDI-017, L-CDI-197 |
| Truncate flag / transformation Pre SQL ignored by Snowflake, Databricks, JDBC V2 | Snowflake `writerAttrs` `presql`; Databricks `writeDisposition` Truncate; JDBC `rt` `"Pre SQL"` | L-CONN-106, L-CDI-248, L-CDI-171 |
| Retarget an existing mapping to another connector type by package edit | regenerate the mapping on the new connection | L-CDI-031 |
| A managed MCP verb that authors a mapping or task | none exists; use REST / the generator | L-CDI-068 |
| CDQ cleanse, deduplicate, decision on the Hosted Agent (EP_13236) | bind that task to a Secure Agent | L-CDI-279 |
| Generated Normalizer with occurring fields fails at DTM load | Expressions fanned into a Union | L-CDI-236 |
| Publish an API-made advanced taskflow | linear taskflows ([05](../05-taskflows-schedules/README.md)) | L-CDI-070 |

## Fastest safe path

1. **Prove the org:** `check_login.py`. Read-back: the 22-character `<orgIdV3>` you will pass to `--expect-org`.
2. **Profile:** copy `toolkit/mapgen/profile.example.json`, set `kind` on every connection (no `kind` = treated as
   BigQuery), then `resolve --write`. Read-back: every GUID, v2 id and runtime id filled.
3. **Pick a runtime by where the data lives:** Hosted Agent for SaaS-to-SaaS; Secure Agent for private data, files,
   CDQ, Structure Parser, Tableau V3 (Fast Path §6; L-AGENT-036, L-CDI-279).
4. **Copy the closest example** from `toolkit/mapgen/examples/` (Fast Path §4); rename `name` / `taskName` (letters,
   digits, spaces, hyphens only: L-CDI-280).
5. **Declare fields** from `INFORMATION_SCHEMA` / Salesforce describe as `[name, TYPE, precision, nativeType, scale]`,
   with native types from Fast Path §2. Read-back: the tuples match the catalog.
6. **Lint:** `mapgen.py --profile profile.json lint <spec>.json`. Read-back: zero ERROR; `WARN CONN_KIND` is expected
   for kinds other than BQ, PG, JDBC, FF, SF; `WARN CONN_KIND_MISSING` is not.
7. **Dry run, then deploy:** `deploy <spec>.json`, then `deploy <spec>.json --execute --expect-org <orgIdV3>`.
   Read-back: the mapping id and the task exist in the folder.
8. **Run (user's yes):** `deploy ... --run` or `run "<task>" --folder "<project>/<folder>"`. Read-back: activity-log
   row with your `runId`, `endTime`, state 1; a WARNING with 0 rows is a failure (L-CDI-059, L-CDI-060).
9. **Prove the output:** count rows on both sides; two-way diff = 0. On failure: `mapgen.py log <task>`, read the
   FIRST `[ERROR]` line (Fast Path §5).
10. **Then:** orchestrate ([05 Taskflows](../05-taskflows-schedules/README.md)); for a live change, back up, read back
    and prove parity first ([07](07-changing-pipelines-safely.md); L-CDI-149, L-CDI-197).

## Top traps

- **Upsert green, 0 rows changed** (PostgreSQL) → writer attributes missing for the operation → let the generator add
  them and test a new-key insert (L-CDI-207).
- **Target appends every run though truncate is on** → the writer ignores the flag → the per-connector setting in
  Fast Path §3; PostgreSQL truncates only with the writer attribute `TruncateTable` = `YES` (L-CONN-106, L-CDI-171,
  L-CDI-038, L-CDI-248, L-CDI-331).
- **A Pre SQL `TRUNCATE` runs before the source is read**: a failed read leaves the target empty (L-CDI-208).
- **Snowflake:** `Invalid Datatype: timestamp_ntz` → `timestampntz` (L-CONN-093); unbounded `VARCHAR` → writer
  `OutOfMemoryError` → give a length (L-CDI-227); NUMBER into a bigint lookup port → `BigDecimal cannot be cast` →
  decimal(19,0) (L-CONN-095).
- **`APP_13500` on task create after a good import** → parentheses in the task name (L-CDI-280).
- **Import `REPO_36004`** after a failed import → re-import under a new name (L-CDI-204); `MigrationSvc_030` → rebuild
  the package with the generator (L-CDI-032); `REPO_38210` → remap the reserved Hosted Agent name (L-CONN-024, L-MIG-015).
- **Session hangs with no error** → one source feeds both sides of a Joiner → sorted input or two reads (L-CDI-106);
  `PLUGIN_1762 ... OutOfMemoryError` → too many unsorted Joiners / readers: split the mapping (L-CDI-210, L-CDI-129).
- **Expression OUTPUT port reads another OUTPUT port → NULL** → use VARIABLE ports (L-CDI-105); `REG_EXTRACT` NULL →
  end the pattern with `.*` (L-CDI-246).
- **`403 REPO_19001` on task save** → about 4,000+ characters of SQL in an in-out parameter default → a per-task
  parameter file (L-CDI-285).
- **On-demand start while the scheduled run is active** → fails in about 1 s, state 3, and fails the lane → check the
  activity monitor first, or coalesce (L-CDI-304).
- **Retrying blindly** → retry a FAILED task once, on transient signatures only, never on 'monthly limit' (L-CDI-205).
- **One task per table per stage** → about 20 s fixed cost and one job per task → consolidate into few mappings
  (L-CDI-121, L-CDI-114).

## Go deeper

- [00 Mapping Fast Path](00-mapping-fast-path-read-this-first.md): the ten commands, connector settings, error table, runtime choice, exemplar route.
- [01 CDI Object Model](01-cdi-object-model.md): mapping, task, taskflow, schedule; v2 vs v3 ids; inventory.
- [02 How Claude Builds Mappings Headless](02-how-claude-builds-mappings-headless.md): the five routes, proven transformations, pushdown, structure parsing.
- [03 Mapping Tasks](03-mapping-tasks-create-update-run-monitor.md): create, update, run, monitor, session logs, retry rules.
- [04 The Pipeline-Generation Pattern](04-the-pipeline-generation-pattern.md): whole pipelines from SQL files and a spec, idempotent by name.
- [05 Mapping Design & Consolidation](05-mapping-design-consolidation.md): expression idioms, SCD2, rejects, fewer mappings.
- [06 Performance, Concurrency & Job Caps](06-performance-concurrency-job-caps.md): the 20 s floor, DAG fan-out, DTM pool, job cap.
- [07 Changing Pipelines Safely](07-changing-pipelines-safely.md): back up, read back, parity, the swap gate, rollback.
- [08 Source & Target Gotchas](08-source-target-gotchas.md): BigQuery, PostgreSQL, Salesforce, JDBC V2, Snowflake behaviour.
- [09 Serving Outputs to BI and Apps](09-serving-outputs-to-bi-and-apps-freshness-latency-reverse-etl.md): freshness, latency, reverse ETL.
- [Lessons: CDI](lessons.md) · [mapgen SPEC_REFERENCE](../../toolkit/mapgen/docs/SPEC_REFERENCE.md)
