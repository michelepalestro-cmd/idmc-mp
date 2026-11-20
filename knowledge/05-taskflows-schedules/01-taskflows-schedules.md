# Taskflows & Schedules

**Answers:** How to create, update, run and monitor linear taskflows over v2; why API-made advanced taskflows cannot be published and what to do instead; how to create, bind, unbind, end and delete schedules with the pod-local time trap; how to cut schedules over between orgs.

**Read when:** before building or changing a lane's taskflow or schedule; when a schedule fires at the wrong time, a taskflow loses its schedule, or a start fails with `REPO_17314` or `UI_13430`.

**Key rules:**
- Linear taskflows are fully headless and need no publish; advanced taskflows made by API import but cannot be published (L-CDI-069, L-CDI-070).
- Keep `scheduleId` in every workflow update body, or the update unbinds the schedule (L-CDI-069, L-CDI-075).
- On US pods send `startTime` pod-local and `startTimeUTC` true UTC, on a 5-minute boundary, and read `startTimeUTC` back (L-CDI-073, L-CDI-074).
- Task-level schedules are invisible in the task list: scan every task's detail at cutover (L-CDI-077).
- Taskflows that share tasks cannot overlap (`REPO_17314`); an external controller with per-table conflict locks replaces quiet windows (L-CDI-128, L-CDI-078).

**Related:** [03 Mapping Tasks - Create, Update, Run, Monitor](../04-mappings/03-mapping-tasks-create-update-run-monitor.md) · [05 The Pipeline-Generation Pattern](../04-mappings/04-the-pipeline-generation-pattern.md) · [07 Performance, Concurrency & Job Caps](../04-mappings/06-performance-concurrency-job-caps.md) · [Lessons: CDI](../04-mappings/lessons.md)

**Last verified:** 2026-11-20

> **Summary.** Build pipelines as **linear taskflows** (v2 `workflow`): `POST /api/v2/workflow` with an ordered `tasks[]`, no publish step, run with `POST /api/v2/job {"taskType":"WORKFLOW"}`. Children log under the taskflow's activity-log entry.
> Advanced (parallel) taskflows can be generated and imported, but API-made ones could not be **published**, and `/api/v2/job` rejects them. Get parallelism from several linear lanes or a controller that starts tasks itself.
> Schedules are created with `POST /api/v2/schedule` and bound by setting `scheduleId` on a workflow **or a task** (null unbinds), always read back. The v2 task list hides task-level bindings.
> Times are pod-local (UTC-4 on US pods) but labelled `Z`: send both `startTime`/`startTimeUTC` (and `endTime`/`endTimeUTC`) on a 5-minute boundary. Taskflows that share tasks cannot overlap (`REPO_17314`).

---

## 1. Which orchestration object to use

| Need | Use | Why |
|---|---|---|
| Run N tasks in a fixed order, unattended, visible in IDMC Monitor | Linear taskflow + schedule | Fully headless, no publish (L-CDI-069, 2026-09-24) |
| Run one task on a cadence | Task-level schedule (`scheduleId` on the MTT) | No taskflow needed (L-CDI-075) |
| Run tasks in parallel by dependency | An external controller calling `POST /api/v2/job` per task (staged fan-out), or several linear taskflows | Advanced taskflow publish is walled headless (L-CDI-070, L-CDI-125) |
| An on-demand trigger from an app or event | The controller starts the lane's linear taskflow (`taskType:"WORKFLOW"`) | Coalesce events; see [07](../04-mappings/06-performance-concurrency-job-caps.md) |
| Run an agent-side shell script inside a flow | Command Task in an advanced taskflow | Documented; canvas automation was fragile, not done headless (L-CDI-082) |

## 2. Linear taskflows (v2 `workflow`)

**Create** (proven 2026-09-24, then 10 lanes; L-CDI-069):

```
POST /api/v2/workflow            # header icSessionId, v2 serverUrl
{"@type": "workflow", "name": "wf_<app>_<lane>", "description": "[<tag>]...",
 "tasks": [ {"@type": "workflowTask", "taskId": "<taskId>", "type": "MTT", "name": "<task name>",
             "stopOnError": true, "stopOnWarning": false},... ]}          # list in execution order
-> 200 {"id": "<wfId>",...}
```

**Update** without losing the schedule:

```
cur = GET /api/v2/workflow/<wfId>
body.id = <wfId>; if cur.scheduleId: body.scheduleId = cur.scheduleId       # an update without it unbinds the schedule
POST /api/v2/workflow/<wfId>  -> 200; GET again and compare the task count and scheduleId
```

- **Semantics.** Tasks run strictly one after another. `stopOnError:true` stops the flow at the first failed task; the tasks after it show as not run. `stopOnWarning:false` lets a WARNING (some rows rejected) continue. Per-task flags can differ: set `stopOnError:false` on a best-effort snapshot task so the tasks after it still run. The same applies to a step whose runtime is down: during a Hosted Agent outage one step still bound to the hosted runtime starved the unrelated data-quality steps behind it, so put independent steps before such a step, or make its failure reported but non-fatal until the runtime is back (L-ENV-100, 2026-11-03).
- **No publish step.** A linear taskflow runs as soon as it exists. Ten were migrated between orgs with no publish at all (L-CDI-069).
- **Placement.** v2 workflows carry no `frsGuid`. Resolve the v3 id by name among `type=='WORKFLOW'` objects (require exactly one match), then move it with FRS `MoveEntities` (L-CDI-009).
- **Run:** `POST /api/v2/job {"@type":"job","taskId":"<wfId>","taskType":"WORKFLOW"}` → `runId`. A taskflow run counts as one job, plus one per task inside it.
- **Monitor:** poll `GET /api/v2/activity/activityLog?taskId=<wfId>&rowLimit=1` until a row with `endTime` that started after your start. Read each child's state from its `entries[]`. Children do **not** appear under their own task ids (L-CDI-061). While it runs, `GET /api/v2/activity/activityMonitor?details=true` shows `subTaskName`/`currentTaskName` for the child running now (L-CDI-062).
- **Adopting a schedule-started run.** A controller that sees the taskflow in the activity monitor, without having started it, can adopt that instance and mirror its children instead of starting a second one. A second `POST /api/v2/job` for a running taskflow is refused with `REPO_17315`: attach, do not retry (L-CDI-253).
- **Name the parent taskflow in a failure alert.** Each activity-log entry carries `parentTaskFederatedId`; `POST /public/core/v3/lookup {"objects":[{"id":"<parentTaskFederatedId>"}]}` returns the parent taskflow's path and name. Never let a lookup failure block the alert (L-CDI-310, reported).
- **Stop a running taskflow** (reported from third-party code, not probed here): `PUT https://<pod>.<domain>.informaticacloud.com/active-bpel/restadmin/processes/<pid>/terminate?isManual=true`, with `<pid>` from the `extraData` of its JobLogEntries row; a task stops with `POST /api/v2/job/stop?cleanStop=true` (L-CDI-307).
- **Delete:** `DELETE /api/v2/workflow/<wfId>` → 200. Unbind its schedule first ([knowledge/12-deploy-migrate](../12-deploy-migrate)).
- **Removing one task from a shared taskflow:** GET, filter `tasks[]`, POST, read back.
- **Land files before a mapping.** A File Ingestion task ran as a taskflow step that copies cloud-storage files to an agent folder before a mapping that needs local files (L-DBMI-060); a CAI process can instead start it, poll its status and start the mapping's taskflow only on SUCCESS (L-DBMI-061) ([DBMI over REST](../06-cdc-ingestion/01-dbmi-over-rest-create-deploy-run-stop.md)).

**Measured** (one Secure Agent, one task at a time): 50 tasks in 15 min; a 62-task lane in 21.6–24.5 min; a 16-task lane at a median of 4.6 min; a 19-task lane in about 6 min (L-CDI-122). Each task costs about 20 s of fixed time, so a linear lane's duration is roughly the task count × 20 s ([07](../04-mappings/06-performance-concurrency-job-caps.md)).

## 3. Advanced taskflows (v3 `TASKFLOW`)

**What can be generated** (2026-09-25; L-CDI-070). The Process Designer XML is an `aetgt:getResponse` repository item with MIME type `application/xml+taskflow`, wrapping `<taskflow>`:
- one `parallel` container per dependency wave, with one `flow` per task;
- each Data Task is an `eventContainer` holding a `service` with `serviceName` `ICSExecuteDataTask` and inputs `Wait for Task to Complete=true`, `Max Wait=604800`, `Task Name`, `GUID` (the task's `frsGuid`), `Task Type=MCT` and `Has Inout Parameters=false`;
- a temp field per task referencing a `processObject` named `<task-name-with-dashes>-<frsGuid>`, with `failOnNotRun`/`failOnFault` options and error/warning catches;
- the step title equal to the temp field name, and no inner description text (the designer rejected text there).

Packaged like any import (real Project/Folder json entries, `exportMetadata.v2.json` with `objectType:"TASKFLOW"` and `objectRefs` = the task GUIDs, checksums), it **imports** with OVERWRITE.

**What fails.**
- Publishing through `POST https://<pod>-cai.<domain>.informaticacloud.com/active-bpel/asset/v1/publish` with the `Explore/<project>/<folder>/<name>.TASKFLOW.xml` path failed for taskflows created by the API **or copied with FRS CopyEntities**: `AvrEntryNotFoundFault` / "File format was not recognized" (2026-09-25).
- In July, an imported taskflow stayed `documentState INVALID`, and every validate/compile/publish route probed returned 404.
- The REST/SOAP run URL of an advanced taskflow is minted only by a designer Publish with Binding=API (July 2026).
- Whether a body swapped into a designer-created shell can be published was not settled. One July report of a DI taskflow showing `publicationStatus=published` over REST named no endpoint (L-CDI-193, disputed).

**Why `/api/v2/job` rejects taskflows.** The v2 job resource starts Data Integration tasks and linear workflows (`taskType` `MTT` or `WORKFLOW`). An advanced taskflow is a Process Designer process: its XML, MIME type and publish route are the Application Integration ones (an inference from the format). It starts from its published REST/SOAP endpoint, and `POST /api/v2/job` answered it with `403 UI_13430` (2026-07-04; L-CDI-071).

**What to do instead** (L-CDI-072):
- Run the member tasks yourself in dependency waves: `POST /api/v2/job` per task, a barrier poll on the activity log, pre-truncation where the connector ignores truncate, and a loud failure on state 3. That is functionally equivalent for a batch (22 tasks in 5 waves, exact baseline match, 2026-07-04).
- Or use a controller with staged fan-out: each task starts when its dependencies finish, at most N at once (L-CDI-125).
- A trigger script for a published taskflow's URL should return distinct exit codes (success, failed, timeout, URL not configured) so the caller can fall back.

## 4. Schedules

**Create** with an explicit body (proven 2026-09-28; L-CDI-073):

```
POST /api/v2/schedule
{"@type": "schedule", "name": "<tag>_<app>_<cadence>", "description": "[<tag>]...",
 "interval": "Hourly" | "Daily" | "Minutely", "frequency": <n>, "timeZoneId": "GMT",
 "startTime": "<pod-local time>Z", "startTimeUTC": "<true UTC>Z",
 "weekDay": false, "dayOfMonth": 0,
 "mon": true, "tue": true, "wed": true, "thu": true, "fri": true, "sat": true, "sun": true}
-> 200 {"id": "<scheduleId>", "startTime":..., "startTimeUTC":..., "interval":...}     # read startTimeUTC back
```

| Rule | Detail | Lesson |
|---|---|---|
| Pod-local times | On a UTC-4 pod, `startTime` is read as pod-local even with a `Z` (the stored `startTimeUTC` = `startTime` + 4 h). Send `startTime` = UTC − 4 h and `startTimeUTC` = the true UTC, then read `startTimeUTC` back. The July variant: send the shifted `startTime` and omit `startTimeUTC` to force a recompute | L-CDI-073, L-CDI-063 |
| 5-minute boundary | The start minute must be on a :05 boundary, else `UI_10621` | L-CDI-074 |
| Day flags | An `Hourly` schedule without the `mon`…`sun` flags fails with `UI_10612` | L-CDI-074 |
| Idempotent by name | Look the name up first; update with `POST /api/v2/schedule/<id>` | L-CDI-073 |
| Update = the full object | `POST /api/v2/schedule/<id>` with the object you read (drop the create/update stamps; vendor docs also list the header `Update-Mode: PARTIAL` for v2 schedule and workflow, L-CDI-321). `interval` is the unit ('Minutely', 'Hourly', 'Daily', 'Weekly', 'Monthly') and `frequency` the count (`Hourly` + 6 = every 6 hours); swapped they give 403 `UI_10622` 'Interval is not valid', and a string `frequency` gives 400. Bound tasks keep their bindings; read back | L-CDI-195 |
| Create **unbound** | For a migration or a new lane, create schedules unbound and bind them in one explicit step | L-CDI-073 |
| No cloning | Never build a schedule by GETting another application's schedule and changing the name. Builders did, and broke when that schedule was deleted with its app | L-CDI-079 |
| Check the start date | A schedule starting years ahead (e.g. 2037) never fires; data then moves only on manual runs | L-CDI-080 |

## 5. Bind, unbind, stop, delete

**Bind or unbind** (proven in two orgs 2026-09-28; L-CDI-075):

```
wf = GET /api/v2/workflow/<wfId>
wf = wf minus {createTime, updateTime, createdBy, updatedBy}
wf.scheduleId = "<scheduleId>"        # bind      |  null  -> unbind
POST /api/v2/workflow/<wfId>  -> 200
GET  /api/v2/workflow/<wfId>  -> scheduleId must equal what you sent (None after an unbind)
```

- The same works at **task level** on `/api/v2/mttask/<id>`. Runs then show a scheduler context in the activity log (L-CDI-075).
- Prove the verb on a low-risk workflow first, and snapshot every binding to JSON (workflow and task level) as the rollback baseline.
- **Task-level bindings are invisible in the v2 task list.** Before a cutover, scan **every task's detail**. One task-level schedule was missed by a workflow-only unbind and ran once more in the old org (L-CDI-077, 2026-09-29).

**Stop a schedule by date** (L-CDI-076). Set **both** `endTime` (pod-local) and `endTimeUTC`, on a :05 boundary. Setting `endTime` alone to "23:40Z" meant 03:40Z on a UTC-4 pod, and the lane kept running and failing. `PATCH /public/core/v3/schedule/<id> {"status":"disabled"}` returned `400 V3API_007`; third-party code wraps the change as `{"schedules":[{"id":"<id>","scheduleFederatedId":"<from GET /public/core/v3/schedule/<id>>","status":"disabled"}]}`, which likely explains the 400 but is not yet retested here (L-CDI-309). **Unbinding** (`scheduleId:null`) is the simpler stop.

**Delete:** `DELETE /api/v2/schedule/<id>` → 200. A deleted schedule's GET returns an **empty 200 shell**, so confirm with the schedule list (L-CDI-081).

## 6. Overlaps and quiet windows

- Two linear taskflows that share tasks cannot run at the same time. The second start fails with `REPO_17314` "Another instance of the Linear Taskflow is currently running". A second orchestrator firing the same tasks gets the same error (L-CDI-078).
- Subset lanes (event-driven lanes whose tasks are a subset of the full lane) must stay out of a **quiet window** around the full lane's scheduled start, e.g. 7 minutes before to 1 minute after, while IDMC schedules start the full lane. Better: let one external controller own every start, consolidate the subset lanes away, and block only real conflicts with per-table locks, so the critical event lane can run beside a long full refresh ([07](../04-mappings/06-performance-concurrency-job-caps.md) §5; L-CDI-128).
- A retired cron runner that started the same tasks collided with the scheduled taskflow. Retire old starters when a taskflow takes over, and make them exit with a clear message unless an override is set.

## 7. Cutover checklist for schedules (org to org)

1. Snapshot every binding in the source: workflow `scheduleId`s **and** task-level `scheduleId`s from each task's detail.
2. Create the target schedules **unbound** (explicit bodies, idempotent by name).
3. At the switch: unbind the source (read back), flip the callers, bind the target (read back).
4. Verify the first scheduled run in the target at the expected UTC minute.
5. Scan every source task's detail again for a leftover task-level binding.
6. Rollback: rebind from the snapshot, unbind the target. Rolling back into the source only works while its account exists and is under its monthly job cap.

## 8. Symptom triage

| Symptom | Likely cause | Fix | Lesson |
|---|---|---|---|
| `REPO_17314` "Another instance of the Linear Taskflow is currently running" | A taskflow sharing tasks is running, or a second starter fired | Wait; quiet window; or let one controller own every start with per-table conflict locks | L-CDI-078 |
| `403 UI_13430` from `POST /api/v2/job` | An advanced taskflow was passed | Linear taskflow, or run the member tasks | L-CDI-071 |
| A child task's run is missing under its own task id | Children log under the taskflow's `entries[]` | Read the taskflow's activity-log row | L-CDI-061 |
| Later children show as not run | `stopOnError` after an earlier failure | Fix the failing task, rerun the lane | L-CDI-061 |
| Unrelated children never run while one step's runtime is down | `stopOnError:true` on a step bound to the dead runtime | Independent steps first, or that step non-fatal until the runtime is back | L-ENV-100 |
| A retired pipeline's sweep keeps running and repeats paid work | Its schedules are still bound, some in another project | Unbind every schedule of a retired pipeline; drive sweeps from stored results, not a deletable cursor | L-CDI-283, L-CDI-075 |
| A schedule fires 4 hours off | `startTime` was read as pod-local (UTC-4) | Send `startTime` pod-local plus `startTimeUTC`, read back | L-CDI-073 |
| `UI_10612` on create | Hourly without the day flags | Set `mon`…`sun` | L-CDI-074 |
| `UI_10621` on create | Start minute off a 5-minute boundary | Use :00, :05, :10 … | L-CDI-074 |
| `403 UI_10622` 'Interval is not valid' on update | `interval` and `frequency` swapped | `interval` = unit, `frequency` = number | L-CDI-195 |
| A lane keeps running after the schedule was "ended" | Only `endTime` was set | Set `endTime` and `endTimeUTC`, or unbind | L-CDI-076 |
| A taskflow lost its schedule after an update | The POST body had no `scheduleId` | Keep the current `scheduleId` on update | L-CDI-069 |
| The old org still runs a task after a cutover | A task-level schedule (hidden from the list) | Scan every task detail; unbind | L-CDI-077 |
| `REPO_52013` on task delete | The task is bound to a schedule | Unbind deliberately, or keep the task | L-CDI-053 |
| A deleted schedule still answers GET | A deleted schedule returns an empty 200 shell | Check the schedule list | L-CDI-081 |
| `400 V3API_007` on `PATCH /public/core/v3/schedule/<id>` | A bare body; the v3 PATCH reportedly needs a `schedules[]` wrapper with `id` and `scheduleFederatedId` | Unbind, or set the end times; retest with the wrapper | L-CDI-076, L-CDI-309 |
| An on-demand task start ends in ~1 s, state 3, 0 rows: 'Another instance of the task is currently running' | The task's scheduled or lane run is active; a mapping task runs one instance at a time | Check the activity monitor for that task id and skip or coalesce; do not fail the lane | L-CDI-304 |
| `AvrEntryNotFoundFault` / "File format was not recognized" on publish | An API-created or FRS-copied advanced taskflow | Linear taskflow or controller staging | L-CDI-070 |
| A task "is scheduled" but never runs | The schedule's start date is years ahead | Fix the start; read the next run | L-CDI-080 |
| A builder's schedule step raises "not found" | It cloned a template schedule that was deleted | Explicit schedule body | L-CDI-079 |
| A scheduled taskflow FAILED on a BigQuery 503 or a staging-file upload error | A transient cloud error | One watcher re-run of the taskflow; the re-run succeeded | L-CDI-205 |
| Lanes fail within seconds with 'monthly limit', then later runs show empty errors and 0 rows | The org's monthly job cap | Quota breaker; count both kinds of run ([07](../04-mappings/06-performance-concurrency-job-caps.md) §7) | L-IPU-060, L-CDI-132 |

## 9. Overturned beliefs (latest evidence wins)

| Earlier belief | Overturned by |
|---|---|
| Scheduling and monitoring mapping tasks requires the Administrator UI (early July 2026; L-CDI-183) | `POST /api/v2/schedule` → 200 and a real schedule, 2026-07-04; binding by `scheduleId` (L-CDI-075) |
| Taskflow creation is UI-only (`/public/core/v3/taskflow` 404, July; L-CDI-184) | Linear taskflows over `POST /api/v2/workflow`, 2026-09-24 (L-CDI-069). Advanced-taskflow **publish** is still walled (L-CDI-070) |
| Binding a schedule over v2 is untested, so plan a UI fallback (draft runbook, 2026-09-28; L-CDI-185) | Bind and unbind with read-back in two orgs, 2026-09-28 (L-CDI-075) |
