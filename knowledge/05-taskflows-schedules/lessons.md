# Lessons: Taskflows & Schedules
40 lessons: 36 current, 1 disputed, 3 superseded; evidence dated 2026-07-04 to 2026-11-19. Topic docs: [knowledge/04-mappings](../04-mappings/).

## Current

### L-CDI-014  Task reads by type: /api/v2/task?type=, /api/v2/workflow, /api/v2/taskflow
**Kind:** ROUTE · **Proven:** 2026-07-25 · **Evidence:** 200 and 403 answers, live
`GET /api/v2/task?type=<X>` lists tasks by type (403 for `MI_TASK`, and 403 "DVT is not a valid task type" for `DVT`: use each service's own API). `GET /api/v2/workflow` and `GET /api/v2/taskflow` read workflows and taskflows (200).

### L-CDI-016  Move tasks into a folder with FRS MoveEntities; ids, schedules and history survive
**Kind:** OVERTURNED · **Proven:** 2026-09-29 · **Evidence:** `XFER_200` "Operation succeeded on 10 artifacts"; FRS_200 per item; runs unchanged afterwards
New v2 tasks and workflows are created in `Default`. Move them with `POST https://<pod>.<domain>.informaticacloud.com/frs/api/v1/MoveEntities` (or `/frs/v1/MoveEntities`), header `IDS-SESSION-ID: <v2 icSessionId>`, body `{"xferSpec":{"targetLocationId":"<folder frsGuid>","sourceSpecArr":[{"sourceEntityId":"<frsGuid>","mergeTags":""}]}}`, at most 25 ids per call. The v2 id, `mappingId`, schedule bindings and run history are unchanged. v3 `/objects/{id}/move` is 404. `CopyEntities` takes the same `xferSpec`. Data Quality profiles could not be moved.

### L-CDI-053  REPO_52013 on delete means the task is bound to a schedule, so it is live
**Kind:** ERROR · **Proven:** 2026-09-29 · **Evidence:** a prune attempt hit REPO_52013 on a task that looked unreferenced
A v2 DELETE of a mapping task that has its own task-level schedule fails with `REPO_52013`. Treat it as proof the task is live, not an orphan: find the binding in the task detail (`scheduleId`), check who reads its output, and unbind deliberately only if the task really should go.

### L-CDI-056  Run a task or linear taskflow with POST /api/v2/job; readyToRun=false does not block it
**Kind:** ROUTE · **Proven:** 2026-09-28 · **Evidence:** 200 + runId on thousands of runs; runs completed with the runtime-environment list reporting readyToRun=false
`POST <serverUrl>/api/v2/job`, header `icSessionId`, body `{"@type":"job","taskId":"<taskId|wfId>","taskType":"MTT"|"WORKFLOW"}` → 200 with a `runId`. It works even when the runtime-environment list reports `readyToRun=false`: that flag is stale on the list, and only mattered for catalog-source operations. No publish is needed to run an imported task.

### L-CDI-061  Tasks inside a linear taskflow log under the taskflow's entry (entries[])
**Kind:** GOTCHA · **Proven:** 2026-09-25 · **Evidence:** monitoring code changed to mirror children from the workflow entry; the console fix verified
When a linear taskflow runs, `GET /api/v2/activity/activityLog?taskId=<childTaskId>` does not show that run. The children are the `entries[]` of the taskflow's own row (`objectName`, `state`, `successTargetRows`, `errorMsg`, `startTimeUtc`, `runId`). Mirror child states from `entries[]` after the taskflow finishes; children missing after a stop did not run (`stopOnError`). Outer activity-log rows are batches, so flatten `entries[]` for per-run rows.

### L-CDI-066  Verify the production scheduler really calls IDMC; keep the legacy path behind a default-off flag
**Kind:** GOTCHA · **Proven:** 2026-07-04 · **Evidence:** a production cron still ran the retired SQL every 15 minutes while every on-demand IDMC run was green
A pipeline can pass every on-demand IDMC run while production output still comes from legacy code on a cron. Inspect the live scheduler and the driver it calls, and cross-check activity-log run counts, before claiming "runs on IDMC". When IDMC becomes the sole engine, fail loudly on IDMC errors, keep the old runner only behind a default-off emergency flag, and banner the old SQL as superseded.

### L-CDI-067  Watch run health per taskflow and alert on state change; a healthy container is not a healthy pipeline
**Kind:** PROCESS · **Proven:** 2026-09-26 · **Evidence:** a watcher added after a broken connection failed hourly runs silently; a pipeline container reported healthy for 38 h while every cycle failed
Run a small watcher (e.g. every 15 min) that reads the activity log for each important taskflow and alerts only when a flow changes state (fails, stops running, recovers). When one host drives two orgs, run one watcher per org with separate state files. Container health checks only prove a process and a port. Judge pipelines by run completions, row growth and freshness.

### L-CDI-069  Linear taskflows are created and updated headless with /api/v2/workflow and need no publish
**Kind:** OVERTURNED · **Proven:** 2026-09-25 · **Evidence:** 8/8, 50/50, then 62/62 tasks per scheduled cycle; 10 workflows migrated with no publish step
`POST /api/v2/workflow {"@type":"workflow","name":"wf_<app>_<lane>","description":"...","tasks":[{"@type":"workflowTask","taskId":"<taskId>","type":"MTT","name":"<task>","stopOnError":true,"stopOnWarning":false}, ...]}` creates a linear taskflow (tasks in execution order). It can reference a schedule and runs as soon as it exists. To update: `GET /api/v2/workflow/<wfId>`, keep its `scheduleId`, and `POST /api/v2/workflow/<wfId>` with `id`. Run it with `POST /api/v2/job {"taskType":"WORKFLOW"}`. It runs strictly in sequence.

### L-CDI-070  Advanced taskflows generated or copied by API import but cannot be published
**Kind:** WALL · **Proven:** 2026-09-25 · **Evidence:** publish faults `AvrEntryNotFoundFault` / "File format was not recognized"; July: imported taskflows stayed documentState INVALID
Advanced taskflow XML can be generated and imported with OVERWRITE:
- a `parallel` container per wave;
- Data Tasks as `ICSExecuteDataTask` services inside `eventContainer`s;
- a temp field per task with a `processObject` dependency;
- the step title equal to the field name, and no inner description.

But a taskflow created by the API, or copied with FRS CopyEntities, could not be **published** through `active-bpel/asset/v1/publish` with its `.TASKFLOW.xml` path. Its REST/SOAP run URL is minted only by a designer Publish (July). Use linear taskflows, or a controller that runs tasks concurrently.

### L-CDI-071  POST /api/v2/job rejects advanced taskflows (403 UI_13430)
**Kind:** ERROR · **Proven:** 2026-07-04 · **Evidence:** 403 UI_13430
The v2 job resource starts Data Integration tasks and linear workflows (`taskType` `MTT`/`WORKFLOW`). An advanced taskflow was rejected with `403 UI_13430`: it runs from its published endpoint. Run the member tasks in waves, or build the flow as a linear taskflow.

### L-CDI-072  Replace an unpublishable taskflow with RunAJob dependency waves and a native schedule
**Kind:** DECISION · **Proven:** 2026-07-04 · **Evidence:** 22 tasks in 5 waves, exit 0, gold matching the baseline exactly
Fire each task with `POST /api/v2/job` in dependency waves derived from the tasks' source reads. After each wave, barrier-poll the activity log until every run is terminal, matching runs by `runId`. Pre-truncate targets whose connector ignores truncate, fail loudly on any state 3, and offer dry-run and resume-from-wave. A published taskflow's run-URL trigger script should use distinct exit codes (success, failed, timeout, URL not configured) so callers can fall back.

### L-CDI-073  Create a v2 schedule with an explicit body: startTime pod-local plus startTimeUTC
**Kind:** RECIPE · **Proven:** 2026-09-28 · **Evidence:** the first target runs fired at the expected UTC minutes; startTimeUTC read back
`POST /api/v2/schedule {"@type":"schedule","name":"<tag>_<app>_<cadence>","description":"...","interval":"Hourly"|"Daily"|"Minutely","frequency":<n>,"timeZoneId":"GMT","startTime":"<pod-local time>Z","startTimeUTC":"<true UTC>Z","weekDay":false,"dayOfMonth":0,"mon":true,...,"sun":true}`. On a UTC-4 pod, local = UTC − 4 h (the API read `startTime` as pod-local and set `startTimeUTC = startTime + 4 h`). Read `startTimeUTC` back. Create migration schedules unbound, and make the create idempotent by name.

### L-CDI-074  UI_10612 without day flags on an hourly schedule; UI_10621 off a 5-minute boundary
**Kind:** ERROR · **Proven:** 2026-09-24 · **Evidence:** UI_10612 without the flags, created with them; UI_10621 on an off-boundary minute
`POST /api/v2/schedule` with `interval:"Hourly"` fails with `UI_10612` unless the day-of-week flags (`mon`…`sun`) are set. The start minute must be on a 5-minute boundary, otherwise `UI_10621`.

### L-CDI-075  Bind and unbind schedules by POSTing the workflow or task with scheduleId (null unbinds)
**Kind:** OVERTURNED · **Proven:** 2026-09-28 · **Evidence:** read-backs showed None after an unbind and the new id after a bind, in two orgs; 18 tasks bound at task level ran with a scheduler context (2026-07-09)
`GET /api/v2/workflow/<wfId>`, drop `createTime/updateTime/createdBy/updatedBy`, set `scheduleId` to `"<scheduleId>"` (bind) or `null` (unbind), `POST /api/v2/workflow/<wfId>`, then GET it again and compare. The same works at task level on `/api/v2/mttask/<id>`, with no taskflow needed. Prove the verb on a low-risk workflow first, and snapshot every binding as the rollback baseline.

### L-CDI-076  Ending a schedule: set endTime and endTimeUTC; a v3 disable PATCH returns V3API_007
**Kind:** GOTCHA · **Proven:** 2026-09-28 · **Evidence:** a schedule ran 4 hours longer than intended until both fields were set; the last run came just before the fixed end
`endTime` is read as pod-local even when written with `Z`: an `endTime` of "23:40Z" meant 03:40Z on a UTC-4 pod, and the lane kept running and failing. Set both `endTime` and `endTimeUTC` on a :05 boundary, and confirm no run fires after it. `PATCH /public/core/v3/schedule/<id> {"status":"disabled"}` returned `400 V3API_007`. Unbinding (`scheduleId:null`) is the simpler stop.

### L-CDI-077  At cutover, scan every task's detail for a task-level schedule
**Kind:** LAW · **Proven:** 2026-09-29 · **Evidence:** a task-level binding missed by a workflow-only unbind ran once more in the old org; a scan of 159 details found only that one
Mapping tasks can be bound to a schedule directly, and the v2 task list does not return `scheduleId`. Before a cutover, or before moving or deleting schedules, scan every task's detail as well as every workflow. Otherwise a task keeps running in the old org.

### L-CDI-078  REPO_17314: taskflows that share tasks cannot overlap
**Kind:** ERROR · **Proven:** 2026-09-25 · **Evidence:** the collision retired a cron runner; the quiet-window fix held
Starting a linear taskflow while another taskflow that runs the same tasks is running fails with `REPO_17314` "Another instance of the Linear Taskflow is currently running". Two orchestrators firing the same tasks get the same error. Keep on-demand subset lanes out of a quiet window around the scheduled full run (e.g. 7 minutes before to 1 minute after), make lanes mutually exclusive, or remove the subset taskflows.

### L-CDI-079  Never clone a new schedule from another application's schedule
**Kind:** GOTCHA · **Proven:** 2026-09-29 · **Evidence:** builders' schedule paths raised after the template schedule was deleted with its application
Builders that created a schedule by GETting an existing schedule, stripping `id/orgId/createTime/updateTime/createdBy/updatedBy/startTimeUTC` and renaming it broke when that template schedule was deleted. Create schedules from an explicit body.

### L-CDI-080  A schedule whose start date lies years ahead never fires
**Kind:** GOTCHA · **Proven:** 2026-07-09 · **Evidence:** a schedule starting in 2037; data moved only on manual runs
A task can look scheduled while its schedule's start date lies far in the future, so it never runs. Read each schedule's start time and next run before claiming scheduled operation.

### L-CDI-081  Delete a schedule; a deleted schedule's GET returns an empty 200 shell
**Kind:** ROUTE · **Proven:** 2026-09-28 · **Evidence:** read-backs during a cleanup
`DELETE /api/v2/schedule/<id>` → 200. A GET of the deleted schedule returns an empty 200 shell, so confirm with `GET /api/v2/schedule` (the list). Unbind or delete schedules before deleting the tasks bound to them (`REPO_52013`).

### L-CDI-082  Run an agent-side script from a taskflow with a Command Task (documented, not done headless)
**Kind:** RECIPE · **Documented:** 2026-07-09 · **Evidence:** Documented, not live-proven: a design; canvas automation fragile; not completed headless
To run a shell script natively on a schedule, create a Command Task (runtime environment = the agent's; Script File = an executable path on the agent), add it as a taskflow step, set Allowed Users, and publish and schedule the taskflow. Canvas automation of this was fragile (nested iframes, SVG edge drags, allowed users not persisting). Advanced taskflow publish is walled headless (L-CDI-070).

### L-CDI-083  The pipeline generator contract: plan + SQL -> tasks idempotent by name -> folder -> taskflows -> schedules
**Kind:** PROCESS · **Proven:** 2026-09-25 · **Evidence:** generators re-run many times in shadow and live modes without duplicates; 159 tasks built
**Inputs:** a directory of SQL files (one per curated table), a spec (`name, sql, target, reads, kind`, optional `materialization: view`), a landing table list and a mode (live|shadow).
**Order of work:**
1. Ensure the project and folder.
2. Upsert one landing task per source table, then the raw layer (a task, or a view for long-text tables).
3. Upsert the medallion tasks in topological order of `reads`, with views emitted as DDL.
4. Add the special shapes (reverse-ETL, SaaS, files, snapshots).
5. Write the plan file.
6. Build one linear taskflow per lane (keeping its schedule), and bind schedules created unbound.

### L-CDI-110  Taskflow shape, an explicit error policy, and one parameterized definition
**Kind:** DECISION · **Documented:** 2026-07-26 · **Evidence:** Documented, not live-proven: a third-party reference implementation; not live-probed; no parameter-set endpoint captured
- **Shape:** a master flow runs INGEST → QUALITY → CURATED, with CURATED sequential (dimensions before facts) and parallelism only inside a stage.
- **Error policy, stated up front:** ingest failure aborts all; a quality breach aborts; a curated failure aborts; per-row rejects within threshold route and continue.
- **Parameterization:** use one definition plus a parameter set (the scheduler passes `$$LOAD_DATE`), not clones per date or environment. No endpoint, file format or upload mechanism for CDI parameter sets was captured.

### L-CDI-117  Anti-pattern: two task families reading the same source tables on separate schedules
**Kind:** GOTCHA · **Proven:** 2026-09-29 · **Evidence:** a warehouse landing family and a second-warehouse landing family (12–17 tasks) read the same tables
When one pipeline lands a source table into the warehouse and a second one lands the same table into another store, each on its own schedule, the source is read twice and the copies drift in time. One mapping can read once and write both targets.

### L-CDI-122  Measured linear-taskflow durations on one agent
**Kind:** PERF · **Proven:** 2026-09-28 · **Evidence:** medians and maxima from the activity log and the run log
One Secure Agent, one task at a time: 50 tasks in 15 min; 62 tasks in about 19–24 min; a 16-task lane at a median of 4.6 min (max 5.5); a 19-task lane in about 6 min (max about 10). For sub-minute freshness use CDC (about 20 s median source to warehouse, p95 26 s).

### L-CDI-131  The monthly job cap: every task and taskflow run is one job
**Kind:** PERF · **Proven:** 2026-09-28 · **Evidence:** every lane failed within ~5 s with "You have exceeded your monthly limit of 10,000 jobs"; the license API showed all limits as -1
An org hit a cap of 10,000 jobs per month. The cap is invisible headless (license limits read `-1`, and neither the cap nor its lift appeared in the audit log), and CDC and CAI kept running. A linear taskflow of N tasks costs N + 1 jobs. An event lane of 16–20 tasks costs 17–21 jobs per event, and a 5-minute feed of 4 tasks costs 1,440 jobs per day. Levers: coalescing, fewer full runs, slower feeds, consolidation, and CDC/CAI for per-event freshness.

### L-CDI-143  Swap tasks inside existing taskflows in place, keeping ids and schedules
**Kind:** RECIPE · **Proven:** 2026-09-29 · **Evidence:** plan/apply/rollback tooling with a backup per workflow (staged)
For each workflow:
1. `GET /api/v2/workflow/<wfId>` and back up the whole body to a timestamped file.
2. Build the new task list. Every replaced task becomes its successor, once, at its first occurrence (`{"@type":"workflowTask","taskId":"<new>","type":"MTT","name":"<new>","stopOnError":..,"stopOnWarning":..}`); keep the others.
3. Re-sort by a stage function (landing, raw, staging, DQ, reverse-ETL, SaaS).
4. POST without the audit fields, then GET and check the task count and `scheduleId`.

Rollback = POST each backed-up body.

### L-CDI-146  Before calling a task an orphan, check task-level schedules, app readers and orchestrator id lists
**Kind:** LAW · **Proven:** 2026-09-29 · **Evidence:** an "orphan" had its own hourly schedule and fed an app API; REPO_52013 on its delete
"Not in any taskflow" is not enough to call a task unused. Check its detail GET for a task-level `scheduleId` (the list hides it). Check whether any app endpoint or view reads its output table. Check whether an orchestrator or host script starts it by id: grep the baked plan, workflow files and host id files.

### L-CDI-147  A task in no taskflow may be obsolete, not a bug: check whether its target became a view
**Kind:** OVERTURNED · **Proven:** 2026-09-29 · **Evidence:** the audit's stale-data bug retracted the same day; a coverage map marked the task for deletion
An audit flagged a raw task in no taskflow as leaving a mart on a stale snapshot. Its raw object had become a live view over the landing table when that table's long text moved to the JSON path, so the mart read live data and the task was simply obsolete. Delete it; do not add it back to a taskflow, because it would overwrite the view with a table.

### L-CDI-195  v2 schedule update: interval is the unit, frequency is the number
**Kind:** GOTCHA · **Proven:** 2026-09-30 · **Evidence:** 403 UI_10622 when swapped, then 200 with read-back for three schedules (2026-09-30)
On `POST /api/v2/schedule/<id>`, `interval` takes the unit ('Minutely', 'Hourly', 'Daily', 'Weekly', 'Monthly') and `frequency` the repeat count (for example `Hourly` + 6 = every 6 hours). Swapping them returns 403 `UI_10622` 'Interval is not valid', and a string frequency returns 400. Send the full object you read (drop create/update stamps), then read it back. Tasks keep their bindings.

### L-CDI-201  Tasks run inside a taskflow appear only as activity-log sub-entries
**Kind:** GOTCHA · **Proven:** 2026-09-30 · **Evidence:** Taskflow members reported never-run until the sub-entries were walked (2026-09-30)
In `/api/v2/activity/activityLog`, a mapping task started by a taskflow is not a top-level row. It appears only under the taskflow entry, in `entries[]` (and recursively `subTaskEntries`) with `type: MTT` and its `objectName`. A 'last run per task' built from top-level rows marks every taskflow member as never-run, and that is dangerous input for a delete list. Walk the sub-entries (and query `?taskId=` per task when in doubt). As with any count, check the unit, for example task vs task×target, against one known object.

### L-CDI-240  Nightly batch with a source that can be down: append its Bronze with a run id, read the latest run, and let its taskflow steps continue on error
**Kind:** PATTERN · **Proven:** 2026-10-09 · **Evidence:** taskflow 10 steps: the 2 source steps failed (login), 8 SUCCESS, decisions unchanged (6/6)
A truncate pre-SQL empties the Bronze table before the source is read, so a failed read leaves nothing and every decision downstream goes blank. Append instead (no presql), stamp each row with the run id, and read QUALIFY IDMC_RUN_ID = MAX(IDMC_RUN_ID) OVER () (per table, before any join); set stopOnError = false on those steps only. A failed read then writes nothing, the batch processes what is already archived, and Monitor shows the failed step honestly. Keep truncate-and-reload for Silver and Gold, which are rebuilt from Bronze every run.

### L-CDI-252  Poll a linear taskflow run with taskId AND runId: child entries carry their own runIds
**Kind:** GOTCHA · **Proven:** 2026-10-16 · **Evidence:** Premature 'finished' with the loose match; the runId-filtered poll ended exactly when the run did (2026-10-16)
The activity log lists finished runs only, and a linear taskflow's row holds its tasks in `entries[]` (L-CDI-061), each with its own `runId`. Matching 'runId == my run' anywhere in the response therefore matched a child task's entry and reported the taskflow finished early. Query `GET /api/v2/activity/activityLog?taskId=<workflowId>&runId=<runId>`: it returns an empty array until that taskflow run ends, then exactly one row, whose top-level state and endTimeUtc are the taskflow's. Refines L-CDI-059.

### L-CDI-253  Starting a linear taskflow that is already running answers REPO_17315
**Kind:** ERROR · **Proven:** 2026-10-16 · **Evidence:** REPO_17315 on a second start while the first run was active (2026-10-16)
`POST /api/v2/job` for a taskflow (taskType WORKFLOW) while an instance of it is still running is refused with REPO_17315 (another instance of the taskflow is running). Callers that can be pressed twice (a button, a scheduler retry) should treat REPO_17315 as 'already running' and attach to the running instance (latest activity-monitor entry) instead of retrying. Newer evidence: L-CDI-304.

### L-CDI-307  Stop anything running: job/stop with cleanStop for tasks, restadmin terminate for taskflows; the set of non-terminal states
**Kind:** RECIPE · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence medium: code only); not probed here
The CLI treats these states as running: AWAITING_AUTO_RESTART, CHILD_SUSPENDED, INITIALIZED, NOT_STARTED, QUEUED, RUNNING, SKIPPED, SUBMITTED, SUSPENDED, TRYING_TO_STOP. A task is stopped with `POST /saas/api/v2/job/stop?cleanStop=true` and `{"@type":"job","taskFederatedId":"<assetId>","taskType":"<assetType>"}`. A taskflow is stopped with `PUT https://<pod>.<domain>.informaticacloud.com/active-bpel/restadmin/processes/<pid>/terminate?isManual=true` using the cookie and XSRF auth, with `<pid>` from the JobLogEntries `extraData`. The KB knows only the bare documented terminate PUT and has nothing on `cleanStop`. Refines L-CAI-044.

### L-CDI-309  v3 schedule PATCH needs a schedules[] wrapper with id and scheduleFederatedId, which likely explains V3API_007 on a bare {status:disabled}
**Kind:** GOTCHA · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence medium: code only); not probed here
The CLI updates a schedule with `PATCH /public/core/v3/schedule/<id>` and the body `{"schedules":[{"id":"<id>","scheduleFederatedId":"<fedId from GET /schedule/<id>>","status":"disabled", ...changed fields}]}`. The KB records `400 V3API_007` for a bare `{"status":"disabled"}` body. Create is `POST /public/core/v3/schedule` with `name` and `startTime`, plus optional `interval`, `frequency`, `status`, `endTime`, `rangeStartTime`, `rangeEndTime`, `timeZoneId`, `weekDay`, `dayOfMonth`, `weekOfMonth`, `dayOfWeek` and `sun`..`sat`. List filters use `q=status=="enabled";interval=="<i>";updateTime>="<ts>"`. Retest the disable with the wrapper. Refines L-CDI-076.

## Superseded / overturned (kept so nobody re-learns them)

### L-CDI-184  Taskflow creation is UI-only, overturned 2026-09-24
**Was believed:** July 2026 (`/public/core/v3/taskflow` 404) · **Overturned by:** L-CDI-069
Linear taskflows are created and updated with `POST /api/v2/workflow` and need no publish. Advanced-taskflow publish is still walled (L-CDI-070).

### L-CDI-185  Binding a schedule over v2 is untested; plan a UI fallback, overturned 2026-09-28
**Was believed:** 2026-09-28 (a draft runbook) · **Overturned by:** L-CDI-075
Bind and unbind by POSTing `scheduleId` (or null) worked with read-back in two orgs.

### L-CDI-188  A raw task in no taskflow means the downstream mart reads stale data, overturned 2026-09-29
**Was believed:** 2026-09-29 (morning audit) · **Overturned by:** L-CDI-147
The raw object had become a live view over the landing table, so the task was obsolete, not a bug.

## Disputed (evidence conflicts; do not rely on either reading)

### L-CDI-193  Whether an advanced taskflow can be published over REST
**Kind:** WALL · **Status:** disputed · **Seen:** 2026-07-04 to 2026-09-25 · **Evidence:** July: every publish route 404; one July report of `publicationStatus=published` read back over REST, with no endpoint named; September: `asset/v1/publish` faulted `AvrEntryNotFoundFault` for API-made taskflows
No route is known that publishes an advanced taskflow created by API. Whether a body swapped into a designer-created shell publishes was not settled. Build on linear taskflows or controller staging (L-CDI-069, L-CDI-125).
