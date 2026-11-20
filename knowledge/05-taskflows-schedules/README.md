# Orchestrate CDI with taskflows and schedules: cheat sheet

Chain mapping tasks into linear taskflows, run and monitor them, and put tasks or taskflows on a schedule (create,
bind, unbind, end, delete, cut over between orgs) without the UI.

**Start with:** `toolkit/lib/idmc_taskflow_schedule.py` (`upsert`, `run`, `schedule-create`, `bind`, `task-bind`,
`audit`, `snapshot`, `restore`) and open [01 Taskflows & Schedules](01-taskflows-schedules.md) first. It is the
orchestration milestone of `/idmc-mp:new-pipeline` ([command](../../commands/new-pipeline.md)); for parallel speed-ups
see `/idmc-mp:optimize` ([command](../../commands/optimize.md)).

> Every write of the tool is a dry run until `--execute --expect-org <orgIdV3>`. Every task run and every taskflow
> run is a job: ask before running or scheduling (L-CDI-131).

## What works (headless)

| Task | How (exact route / tool / command) | Lesson |
|---|---|---|
| Create a linear taskflow | `POST /api/v2/workflow` with an ordered `tasks[]` (`workflowTask`, `type` MTT, `stopOnError`, `stopOnWarning`); no publish step; tool `upsert` | L-CDI-069 |
| Update it | GET, keep `id` and `scheduleId`, drop audit fields, `POST /api/v2/workflow/<wfId>`, GET again | L-CDI-069 |
| Run it | `POST /api/v2/job {"@type":"job","taskId":"<wfId>","taskType":"WORKFLOW"}`; tool `run` | L-CDI-056 |
| Poll one run | `GET /api/v2/activity/activityLog?taskId=<wfId>&runId=<runId>`: empty until the run ends, then one row | L-CDI-252 |
| Read child results | the taskflow row's `entries[]` (and `subTaskEntries`), not the child task ids | L-CDI-061, L-CDI-201 |
| See what runs now | `GET /api/v2/activity/activityMonitor?details=true` (`currentTaskName`) | L-CDI-062 |
| Create a schedule | `POST /api/v2/schedule` explicit body: `interval`, `frequency`, pod-local `startTime` + true `startTimeUTC`, day flags; tool `schedule-create --pod-offset-hours` | L-CDI-073 |
| Update a schedule | `POST /api/v2/schedule/<id>` with the full object; `interval` = unit, `frequency` = number | L-CDI-195 |
| Bind / unbind | POST the workflow (or `/api/v2/mttask/<id>`) with `scheduleId` (`null` unbinds), then GET; tool `bind`, `unbind`, `task-bind` | L-CDI-075 |
| End a schedule by date | both `endTime` and `endTimeUTC` on a :05 boundary; tool `schedule-end` | L-CDI-076 |
| Delete a schedule | `DELETE /api/v2/schedule/<id>`, then confirm in the schedule list | L-CDI-081 |
| Move a taskflow into a folder | FRS `MoveEntities`, at most 25 ids per call; ids, schedules and history survive | L-CDI-016 |
| Swap tasks inside a live taskflow | back up the body, replace each task once, POST, check task count and `scheduleId` | L-CDI-143 |

## What doesn't work, and the workaround

| Wall | Workaround | Lesson |
|---|---|---|
| Publish an advanced taskflow made by the API or copied with FRS (`AvrEntryNotFoundFault`, "File format was not recognized") | linear taskflows, or a controller that starts tasks in dependency waves | L-CDI-070, L-CDI-072 |
| `POST /api/v2/job` on an advanced taskflow → `403 UI_13430` | run the member tasks yourself in waves, barrier-polling by `runId` | L-CDI-071, L-CDI-072 |
| Parallel steps inside one linear taskflow (it runs strictly in sequence) | several linear lanes, or staged fan-out: each task starts when its reads finish, at most N at once | L-CDI-069, L-CDI-125 |
| `PATCH /public/core/v3/schedule/<id> {"status":"disabled"}` → `400 V3API_007` | unbind (`scheduleId: null`) or set both end times; a `schedules[]` wrapper is reported, not probed | L-CDI-076, L-CDI-309 (reported) |
| Seeing the monthly job cap over the API (licence limits read `-1`) | budget jobs yourself: a taskflow of N tasks costs N + 1 jobs | L-CDI-131 |
| Command Task (agent-side script) headless | documented only; canvas automation was fragile | L-CDI-082 |
| CDI parameter sets | no endpoint or upload format was captured | L-CDI-110 |

## Fastest safe path

1. **Prove the org** (`toolkit/check_login.py`) and check that each member task ran alone with state 1. Read-back:
   v2 `taskId` of every task (address by id, never by name).
2. **Create the taskflow:** `idmc_taskflow_schedule.py upsert --name wf_<app>_<lane> --task <taskId> ...`, dry run,
   then `--execute --expect-org <orgIdV3>`. Read-back: `show <wfId>` lists the tasks in order.
3. **Run once (user's yes):** `run <wfId>`. Read-back: the row for `taskId` + `runId` ends in state 1, and every child
   in `entries[]` succeeded with rows written (L-CDI-252, L-CDI-061).
4. **Create the schedule unbound,** on a :05 boundary, with pod-local `startTime` and true `startTimeUTC`. Read-back:
   `startTimeUTC` is the UTC minute you meant (L-CDI-073, L-CDI-074).
5. **Bind it:** `bind <wfId> <scheduleId>` (or `task-bind` for one task). Read-back: GET shows that `scheduleId`.
6. **Check the first scheduled run** fires at the expected UTC minute and that the start date is not years ahead
   (L-CDI-080).
7. **Snapshot every binding** (`snapshot --out <file>`, workflow AND task level) as the rollback baseline; `audit`
   before any cutover (L-CDI-077).
8. **On every later update** keep `scheduleId` in the body and re-read it (L-CDI-069).

## Top traps

- **Taskflow lost its schedule after an update** → the POST body had no `scheduleId` → keep the current one (L-CDI-069).
- **Schedule fires 4 hours off** → `startTime` is read pod-local (UTC-4 on US pods) though labelled `Z` → send
  `startTime` pod-local plus `startTimeUTC`, read back; read `*Utc` fields in logs (L-CDI-073, L-CDI-063).
- **"2am local" drifts by an hour twice a year** → schedules are created in GMT (`timeZoneId: "GMT"`, the only value
  proven; `schedule-create` always sends it), so a fixed UTC start moves against local time across daylight-saving
  changes. Give `--start-utc` as the UTC time of the local hour you want, and after each daylight-saving change end the
  schedule (`schedule-end`) and create a new one an hour earlier or later, or accept the shift. Re-read `startTime`
  against `startTimeUTC` after every change (L-AUTH-094, L-CDI-073). Another `timeZoneId` is untested here.
- **`UI_10612` on create** → Hourly without `mon`…`sun` flags; **`UI_10621`** → start minute off a 5-minute boundary
  (L-CDI-074).
- **`403 UI_10622` 'Interval is not valid'** → `interval` and `frequency` swapped; a string `frequency` gives 400 (L-CDI-195).
- **`REPO_17314`** → another taskflow sharing tasks is running → one controller owns every start, per-table locks or a
  quiet window (L-CDI-078). **`REPO_17315`** → this taskflow is already running → attach to it, do not retry (L-CDI-253).
- **Taskflow reported finished too early** → `runId` matched a child entry → poll with `taskId` AND `runId` (L-CDI-252).
- **Members look never-run** → children log only under the taskflow's `entries[]`; never build a delete list from
  top-level rows (L-CDI-201).
- **The old org still runs a task after cutover** → a task-level schedule, hidden from the v2 task list → scan every
  task's detail (L-CDI-077).
- **`REPO_52013` on task delete** → the task is bound to a schedule, so it is live, not an orphan (L-CDI-053, L-CDI-146).
- **Lane kept running after the schedule "ended"** → only `endTime` was set → set `endTimeUTC` too, or unbind (L-CDI-076).
- **A deleted schedule still answers GET** → it returns an empty 200 shell → check the list (L-CDI-081). A schedule
  cloned from another app's schedule breaks when that one is deleted → explicit body (L-CDI-079).
- **Lanes fail in seconds with 'monthly limit', later runs show 0 rows and empty errors** → the job cap (10,000/month
  seen) → quota breaker, consolidation, CDC/CAI for per-event freshness (L-CDI-131, L-IPU-060).

## Go deeper

- [01 Taskflows & Schedules](01-taskflows-schedules.md): linear vs advanced taskflows, schedule bodies, bind/unbind, overlaps, cutover checklist, symptom triage.
- [Lessons: Taskflows & Schedules](lessons.md)
- Related: [Mapping cheat sheet](../04-mappings/README.md) · [Performance, Concurrency & Job Caps](../04-mappings/06-performance-concurrency-job-caps.md) (DAG fan-out, the ~20 s per task floor; L-CDI-122).
