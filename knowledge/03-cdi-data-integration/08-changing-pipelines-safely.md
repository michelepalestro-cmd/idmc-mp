# Changing Pipelines Safely

**Answers:** How to change one task safely (back up, anchored edit, read back, diff, run once, patch the generator); how to prove a big change side by side with parity SQL; the swap gate for replacing tasks with consolidated mappings; which writes are silently rejected; what to check before deleting, pausing or fixing anything; the rollback kit.

**Read when:** before any write to a live pipeline: an SQL or write-mode change, a mapping swap, a lane pause, a delete or an orchestrator plan switch.

**Key rules:**
- One writer per org, and read back every write: 200s can be silent no-ops (L-CDI-149, L-CDI-050).
- Count a parity result only from a run in state 1 whose target was rewritten at or after the run start (L-CDI-141, L-CDI-197).
- A spec patch is not a fix: re-import, export again and compare, and change the rule in every target and every lane that writes the table (L-CDI-197).
- Refresh column lists from `INFORMATION_SCHEMA` right before a swap; a swap import creates a same-name twin, so wrap the live mapping's id in a new task (L-CDI-197).
- Before pausing a lane, map every BI-read object to the pipeline that refreshes it (L-ENV-079).

**Related:** [03 Mapping Tasks - Create, Update, Run, Monitor](03-mapping-tasks-create-update-run-monitor.md) · [05 The Pipeline-Generation Pattern](05-the-pipeline-generation-pattern.md) · [06 Mapping Design & Consolidation](06-mapping-design-consolidation.md) · [10 Serving Outputs to BI and Apps](10-serving-outputs-to-bi-and-apps-freshness-latency-reverse-etl.md) · [Lessons: CDI](../../lessons/by-domain/03-data-integration-cdi.md)

**Last verified:** 2026-11-03

> **Summary.** Small changes (one task's SQL or write mode) follow **back up → change one field → read back → diff old vs new in the warehouse → run once standalone → patch the generator**; undo = POST the saved JSON.
> Big changes (new mappings replacing many tasks) go **side by side**: shadow or parity objects write only to a parity dataset and are proven by parity SQL (two-way `EXCEPT DISTINCT`, frozen inputs, an idempotency double run). Then a **swap gate**: the end-to-end story suite green → taskflows swapped in place → orchestrator plan switched → re-gate → only then delete the old tasks.
> Throughout: **one writer per org**, read back every write (200s can be silent no-ops), address objects by id, and delete shadow copies after the proof.

---

## 1. The laws

1. **One writer per org** (L-CDI-149). One lead session is the only one that logs in to each IDMC org and the only importer or publisher. Other sessions work read-only or host-side. Coordinate with lease comments (owner, since, expires), heartbeats and DONE posts with evidence. Announce before any import, and never delete while an import runs.
2. **Read back after every write** (L-CDI-149). A 200 whose value reverted is a silent rejection (L-CDI-050). A tool call that the user rejected mid-run can already have executed server-side: 68 repository deletes had landed once. Always read back and report what actually happened.
3. **Back up first:** the v2 JSON of every object you change, the old SQL as a file, and a v3 export package of the objects.
4. **Change only the field you mean,** and assert the anchor you replace occurs exactly once.
5. **Prove it before switching:** run old and new side by side on current data and diff them in full.
6. **Rebuild must equal live.** Patch the generator the same day as any manual change, or the next rebuild reverts it.
7. **Engine changes sit behind flags** with an instant rollback that needs no rebuild, and are never switched mid-lane: wait until the controller reports it is idle (L-CDI-125).

## 2. Small change: one task's SQL or write mode

**Recipe** (proven 2026-09-26 and 2026-09-28; L-CDI-135):

```
1  backup:  GET /api/v2/mttask/<id>                 -> save <task>.v2.json
            save $Source$.customQuery               -> <task>.old.sql
            POST /public/core/v3/lookup {"objects":[{"path":"<project>/<folder>/<task>","type":"MTT"}]} -> v3 id
            POST /public/core/v3/export {...} -> poll -> GET /export/<id>/package        -> <backup>.zip
2  edit:    body = GET again; drop orgId, createTime, updateTime, createdBy, updatedBy (and agentId, parameters[].id)
            q = $Source$.customQuery; assert q.count(anchor) == 1; q = q.replace(anchor, new); save <task>.new.sql
3  prove:   run old and new SQL in the warehouse against current data; full diff (expect only the intended change)
4  apply:   POST /api/v2/mttask/<id>; GET and compare customQuery
5  verify:  run the task once standalone while no taskflow containing it is running; check rows and errors
6  persist: patch the generator so a rebuild produces the same SQL
undo:       POST the saved <task>.v2.json back to /api/v2/mttask/<id>
```

- Example scale: a name-split rule change was proven on 701/701 rows with 0 changed columns on existing data plus 12/12 synthetic cases, then applied with an undo kept (L-CDI-150, 2026-09-28).
- To switch a task between Write truncate and Write append, change only `$Target$.oprRuntimeAttrs.writeDisposition`, and skip the POST if it is already set (L-CDI-051).
- **Two writers of the same fields, one rule.** When a real-time CAI process and a scheduled CDI task both write the same target fields, the batch SQL must implement the same transformation rule. Otherwise the batch run minutes later silently undoes the real-time result. Change both together (L-CDI-150).

## 3. Big change: side by side, then parity

**Shadow mode** (L-CDI-136). Build the whole chain against shadow datasets (shadow landing, raw, staging, gold) from a **separate** shadow schema of source views, so a shadow build can never redefine the views the live tasks read (L-CDI-136, 2026-09-24). Leave shadow tasks unscheduled. Run them, compare, cut over, and then delete them.

**Parity-only targets.** A new mapping writes only to a parity dataset. Check at run time that no candidate task's target points at a live dataset, and give JDBC targets their own scratch connection: a JDBC V2 target writes into the database bound on its connection, and a "parity" probe wrote 1,723 rows into a live table that way (L-CDI-040, 2026-09-29; no data lost because the content matched).

**Parity methods:**

| Method | What it proves | How | Lesson |
|---|---|---|---|
| Row counts + two-way set diff | Same rows, no extras | `SELECT count(*)` both sides; `SELECT count(*) FROM (SELECT to_json_string(struct(<common cols>)) FROM a EXCEPT DISTINCT SELECT … FROM b)` in **both** directions | L-CDI-137 |
| Multiset diff | Same duplicates too | `GROUP BY <json>, count(*)` on both sides; sum the positive differences | L-CDI-137 |
| Run-time columns excluded | Parity despite `now` stamps | Exclude `run_at, ingested_at, run_id, loaded_at, computed_at, refreshed_at, …`, and check separately that they are fresh | L-CDI-137, L-CDI-139 |
| Per-column diff | Where it differs | Join on the key; the first differing column with two sample rows | L-CDI-137 |
| Logic parity | Same logic, same input | Point the shadow raw views at the live raw tables | L-CDI-138 |
| Frozen parity | Same logic, no mid-run arrivals | Snapshot the raw tables, build a reference with the same SQL (`CREATE OR REPLACE TABLE AS`, in topological order), run the new engine on the snapshot, compare | L-CDI-138 |
| Consolidation parity | A new mapping equals the old tasks | Compare the parity target with the **original task SQL run at the same moment**, upstream references repointed; two-way `EXCEPT DISTINCT` = 0 | L-CDI-141 |
| Idempotency | Re-running is safe | Run the new tasks twice in stage order, snapshot after run 1, compare run 1 with run 2 (counts + two-way `EXCEPT`, run-time columns excluded) | L-CDI-141 |
| Cross-engine fingerprint | Two different warehouses hold the same mart | Normalize first (NULL → '', money to NUMERIC(18,2), ISO UTC dates, the same TRIM, column order and delimiter), then `COUNT(*)`, `COUNT(DISTINCT key)` and an order-independent keyset hash: `BIT_XOR(FARM_FINGERPRINT(ARRAY_TO_STRING([...],'\|')))` vs `CHECKSUM_AGG(CONVERT(bigint, HASHBYTES('SHA2_256', CONCAT_WS('\|',...))))` | L-CDI-140 |
| Heavy federated views | One read, not two | Compute parity in a single execution, e.g. `SELECT countIf(cnt != 2) FROM (SELECT …, count cnt FROM (<A> UNION ALL <B>) GROUP BY …)` | L-CDI-139 |
| Migration parity | A moved pipeline equals the old one | Landing `Applied Rows` (session log) = warehouse `COUNT(*)` = source count at the task's read time (14/14 exact); marts against a pre-cutover baseline, every delta explained | L-CDI-064 |

Run parity where the warehouse client and its key already live, and never print the key.

**Count a parity result only from fresh tables** (L-CDI-141, L-CDI-197). For every compared table, check that the run that should have produced it ended in state 1 and that the table's `last_modified_time` is at or after that run's start. Otherwise the compare read a table left by an earlier run: a consolidated mapping was reported idempotent and 0-diff while both of its test runs had failed with a Java heap OOM, and it then failed 3 of 3 live runs. Record the run id, state, start time and the table's last-modified time next to each diff, and treat a missing or older last-modified time as 'not tested', never as 'no difference'.

## 4. The swap gate (consolidated mappings replacing tasks)

The sequence, proven up to the swap on 2026-09-29 (L-CDI-142):
1. **Build** the new mappings in a separate folder, writing only to a parity dataset. Parity plus idempotency as in §3.
2. **Gate:** the application's end-to-end story suite at 100% on the **current** stack. Meanwhile, exclude parity datasets and `*_v2` names from freshness and run-health checks so they do not raise false alerts.
3. **Retarget the new mappings to live targets.** Build a swap-ready package from the parity spec: targets set to the live tables, upstream and guard references inside queries rewritten from the parity dataset to live datasets, the **same mapping GUID**, and an assertion that no parity reference is left. Import it OVERWRITE (L-CDI-145). Do **not** POST new targets to the tasks: that returns 200 and changes nothing (L-CDI-050).
4. **Swap the taskflows in place** (L-CDI-143). For each workflow, GET it and back up the whole body. Build the new task list: each replaced task becomes its successor, once, at its first occurrence (`{"@type":"workflowTask","taskId":"<new>","type":"MTT","name":"<new>","stopOnError":…,"stopOnWarning":…}`); keep the others; re-sort by a stage function (landing, raw, staging, DQ, reverse-ETL, SaaS). POST it and read back the task count and `scheduleId`. Rollback = POST each backed-up body.
5. **Switch the orchestrator's plan** (L-CDI-144). Generate the new plan from the old plan plus the swap spec. The generator exits non-zero unless every replaced task's target is written by a successor, every lane's order is a valid topological order (each in-lane read after its writer; raw views count as reads of their landing tables), and every replaced task in a lane has its successor in that lane. Run it sandboxed (no network) inside the orchestrator's own image, and ship the plan as a separate file selected by an environment variable, so a rollback is a restart.
6. **Re-gate** with the same story suite.
7. **Only then delete the old tasks**, with an export backup first ([03](03-mapping-tasks-create-update-run-monitor.md) §11). Keep them as the rollback path for about a week, or at least 24 h green (L-CDI-142, L-CDI-170).

**Swap traps** (L-CDI-197):
- **A same-name twin appears.** A swap import of a proven mapping into the live project creates a second mapping of the same name beside the scratch copy (another folder and id). Create a new mapping task on the live mapping's id; do not repoint or reuse the scratch task.
- **A cached schema drops columns silently.** A generator that types ports from a cached schema file goes stale: a column added to the warehouse later was left out of the spec and landed NULL, and parity passed because both sides came from the same stale definition. Refresh the column list from `INFORMATION_SCHEMA` immediately before every swap and diff source vs target **columns**, not only rows. A NULL key column caught this way 18 minutes after a swap was rolled back.
- **Re-import and read back.** Re-import the mapping (OVERWRITE, same GUID), export it again and compare (for example the md5 of the exported IMF) with what you meant to ship.
- **Change every target and every lane.** A rule must change in every target of a multi-target mapping and in every mapping or task that writes the same table (plan target lists, lanes, task-level schedules). A cleanse rule changed in one of two targets made two downstream passes flip a value back and forth; an older mapping in another lane reverted a fixed key 3 h after the fix (L-CDI-197).
- **Views re-created by a controller.** If a controller or job re-creates warehouse views from its own plan after every run, a direct `CREATE OR REPLACE VIEW` is reverted at the next run: change the plan's DDL.
- **Snapshot before, diff after.** Take a time-travel snapshot of every target just before the swap and diff every column after the first live run (L-CDI-104).

## 5. Before you delete or "fix" anything

| Check | Why | Lesson |
|---|---|---|
| The task's **detail** for a task-level `scheduleId` | The list hides it. One "orphan" ran hourly on its own schedule and fed an app API | L-CDI-146, L-CDI-077 |
| App endpoints and views that read the task's output table | A task in no taskflow can still feed a live screen | L-CDI-146 |
| The orchestrator's plan, workflow files and host id files | Tasks started directly by id are in no taskflow | L-CDI-146 |
| Whether the task's target is still a **table** | If it became a view, the task is obsolete, not a stale-data bug; delete it rather than re-adding it to a taskflow, which would overwrite the view | L-CDI-147 |
| Tasks that load a table you are about to replace with a view | They fail on every run after the swap. Stop or retarget them first, and keep the old table as renamed history | L-CDI-151 |
| `REPO_52013` on delete | The task is bound to a schedule, so it is live | L-CDI-053 |

After a proof, delete shadow and parity objects at once, with an export backup. 46 unscheduled shadow tasks lingered for days, confused an audit and inflated the design (L-CDI-148).

## 6. Silent rejections to read back for

| Write | Looks like | Actually |
|---|---|---|
| POST new target parameters to a task over a real mapping | 200 | Unchanged; the task re-derives targets from the mapping (L-CDI-050) |
| POST a cross-connector `targetConnectionId` to any task | 200 | The original connection kept (L-CDI-050) |
| `sessionProperties {"Pushdown Optimization":"Full"}` alone | 200, persists on read-back | No pushdown in the session log; full SQL ELT needs all three keys and no target write disposition ([02](02-how-claude-builds-mappings-headless.md) §9; L-CDI-202) |
| A generated Upsert target on PostgreSQL | SUCCESS | 0 of the requested rows applied when the generator had not written the operation's writer attributes (L-CDI-207) |
| A rule changed in one target or one lane | Green runs | Another target or an older mapping in another lane writes the old value back (L-CDI-197) |
| A direct `CREATE OR REPLACE VIEW` on a controller-managed view | Works | Reverted at the next run from the controller's plan DDL (L-CDI-197) |
| Update a workflow without its `scheduleId` | 200 | The schedule is unbound |
| FRS PATCH of a Document's `customAttributes` | 204 | No-op |
| Import SUCCESS envelope | 200 | Per-item states can still fail; read `?expand=objects` |
| Schedule `endTime` with a "Z" on a UTC-4 pod | 200 | Ends 4 hours later than meant (L-CDI-076) |
| A task SUCCESS with 0 rows on BigQuery Write truncate | SUCCESS | The target kept stale rows (L-CDI-088) |
| POST a new `$Source$.customQuery` to a task over a fixed-source mapping | 200, the task shows the new SQL | The run executes the mapping's own query (L-CDI-284) |
| Change a rule specification that mappings embed | API and FRS still call the mappings valid; runs succeed | The Mapping Designer shows them Invalid ('Synchronize the asset'): regenerate from the current definitions, or resynchronize in the designer, then sweep the designer for Invalid badges (L-DQ-126, L-UI-036) |
| Move a task off a downed runtime | 200, the task reads back on the new runtime | Its lookups still resolve through their connections' old runtime; rebind those connections too (L-CONN-132) |

## 7. Production reality checks

- **Does production really run on IDMC?** On-demand runs were green while the production cron still ran the retired SQL every 15 minutes. Inspect the live scheduler and what it calls, and cross-check activity-log run counts (L-CDI-066).
- **Retire the old engine behind a default-off emergency flag.** Fail loudly when IDMC fails, and put SUPERSEDED banners on the old SQL so logic changes happen in one place (L-CDI-066).
- **Re-arming paused jobs:** confirm the activity monitor shows 0 running jobs and no DTM process is alive on the agent, re-run the job once by hand, and update baselines so drift checks do not false-alarm (L-CDI-065).
- **Health is rows, not containers.** A controller container can report healthy while every cycle fails. Alert on run state changes, row growth and freshness (L-CDI-067).
- **Before pausing a lane, map what it feeds.** List every warehouse object a BI workbook or app reads, walk each view down to its base tables, and classify it: streaming (views over the CDC landing: seconds), event-driven (minutes), own cadence (its own taskflow or export), or full-lane-only. Only the last class goes stale during a full-lane pause: in one audit 1 of 66 objects, which would have been ~13.7 h stale, and the fix was to point its tile at a live view over the same source. A VIEW's `__TABLES__.last_modified_time` is when its definition changed, not its data age: query the newest row instead. Recipe in [10](10-serving-outputs-to-bi-and-apps-freshness-latency-reverse-etl.md) §4 (L-ENV-079).

## 8. Pre-change checklist and rollback kit

**Before the first write:**
1. The org is asserted: `GET /api/v2/org` returns the expected `id`.
2. You are the writer for this org: a lease is posted, no other session is importing or publishing, and no import is running.
3. Backups exist:
   - the v2 JSON of every object you will touch;
   - the SQL as files;
   - a v3 export zip of the objects;
   - the body of every workflow you will change;
   - a snapshot of every schedule binding, at workflow **and** task level.
4. The change is one field, or one package, with an anchored edit.
5. The proof is ready: which SQL runs on which datasets, the columns excluded as run-time stamps, and the expected diff.
6. Nothing that contains the task is running: the activity monitor shows none of its lanes. Plan the change outside the quiet window of scheduled lanes.
7. The generator patch is prepared, so a rebuild produces the new state, and its column lists were refreshed from `INFORMATION_SCHEMA` today.
8. The consumers are known: app readers of each output, BI objects by refresher class, and the orchestrator's id lists.
9. For a mapping swap: a time-travel snapshot time of every target is noted, so the first live run can be diffed column by column.

**The rollback kit** (written before the switch; each step independent):

| Undo | How |
|---|---|
| A task change | POST the saved task JSON back to `/api/v2/mttask/<id>` |
| A taskflow change | POST each saved workflow body back to `/api/v2/workflow/<wfId>`, then read back the task count and `scheduleId` |
| A mapping change | Re-import the saved mapping package with OVERWRITE under the same GUID |
| An orchestrator plan switch | Restore the previous plan file or environment flag and restart the orchestrator; wait until it is idle first |
| Schedule moves | Rebind from the snapshot and unbind the new bindings |
| An org-to-org switch | Only possible while the old org's account exists and is under its monthly job cap |

**After the switch:** read back every write, verify the first scheduled run end to end, delete shadow and parity objects (with a backup), and record what changed and why.

## 9. Overturned beliefs (latest evidence wins)

| Earlier belief | Overturned by |
|---|---|
| A raw task in no taskflow means the downstream mart reads stale data (2026-09-29, 00:55Z; L-CDI-188) | The raw object was a live view; the task was obsolete (2026-09-29, ~03:40Z; L-CDI-147) |
| Swapping a mapping's target connection later is a quick change (2026-06-27; L-CDI-190) | Target POSTs silently revert; retarget by re-importing the mapping (2026-07-04 and 2026-09-29; L-CDI-050, L-CDI-145) |
