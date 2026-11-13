# DBMI over REST (create, deploy, run, stop)

**Answers:** Where Database Ingestion (DBMI) answers; which headers it needs; how to create, deploy, start, stop, resume, undeploy and delete a task over REST; the PostgreSQL → BigQuery CDC task body; job states and what each allows; where status, details and task logs live; how to change a task without an update verb; what each error means.

**Read when:** before any DBMI call; when a DBMI route answers 404, 405, 409, 415 or an HTML page; when a job sits in an unfamiliar state.

**Key rules:**
- DBMI lives on `<pod>-ing.<domain>.informaticacloud.com` under `/dbmi/public/api/v2`; a 404 elsewhere is the wrong host, not a missing licence (L-DBMI-001, L-DBMI-041).
- Create does not deploy and deploy does not start; every deploy makes a new job id (L-DBMI-003, L-DBMI-009).
- `general.location` is a project; connections and the runtime environment are names, not ids (L-DBMI-005).
- There is no update verb: re-import an edited export, or create a new task and delete the old one (L-DBMI-007).
- After an agent-host reboot CDC jobs pass through `awaiting_auto_restart` and return to `running` by themselves; do not redeploy them (L-DBMI-028, L-ENV-069). After a hard stop of the **source** host they stay `failed` with PWX-36749 until `job/resume` (L-DBMI-063).
- A table's CDC state is in the task log's transition events; a start is done when every table reports `NORMAL_CONTINUOUS_CDC_TABLE` (L-DBMI-030).

**Related:** [CDC from PostgreSQL](<02 CDC from PostgreSQL.md>) · [DBMI Targets & Drivers](<03 DBMI Targets & Drivers.md>) · [Headless Deletes & Org Cleanup](<../10 - Migration & Org Management/06 Headless Deletes & Org Cleanup.md>) · [Lessons: Mass Ingestion & CDC](<../13 - Lessons Learned/04 Mass Ingestion & CDC.md>)

**Last verified:** 2026-11-03

> Database Ingestion (DBMI, "Mass Ingestion - Databases") has a complete REST lifecycle on its own host, `https://<pod>-ing.<domain>.informaticacloud.com`. You create a task from JSON, deploy it (which creates a job), then start, stop, resume and undeploy the job, and read its status.
> There is no update verb. To change a task, re-import an edited export, or create a new task and delete the old one through FRS.
> Task and job ids are numeric on this plane; the 22-character `frsId` is the task's FRS / v3 id.
> Earlier "DBMI is UI-only" or "DBMI is not licensed" verdicts came from the wrong host, a missing path segment or the wrong header. The lifecycle is proven on two pods.

---

## 1. Where DBMI lives

| Plane | Base URL | Path prefix | Header | Used for |
|---|---|---|---|---|
| DBMI (design + runtime) | `https://<pod>-ing.<domain>.informaticacloud.com` | `/dbmi/public/api/v2/...` (create, deploy, job control, details); `/dbmi/api/v1/task/<taskId>/job` (status) | `IDS-SESSION-ID: <v2 icSessionId>` | everything in this doc |
| Second DBMI prefix | same host | `/mi/public/api/v2/*` | same | answers with typed DBMI errors; **unmapped** (2026-07-26) |
| FRS repository | `https://<pod>.<domain>.informaticacloud.com` | `/frs/api/v1/...` | `IDS-SESSION-ID` | move (`MoveEntities`) and delete (`BaseEntities('<frsId>')`) |
| v3 platform | `https://<pod>.<domain>.informaticacloud.com/saas` | `/public/core/v3/...` | `INFA-SESSION-ID` | export/import of tasks, object inventory, tags |
| v2 platform | the v2 login's `serverUrl` | `/api/v2/...` | `icSessionId` | connections, activity log; **not** for starting DBMI tasks |
| File Ingestion (Mass Ingestion Files) | `https://<pod>.<domain>.informaticacloud.com` (no `/saas`) | `/mftsaas/api/v1/...` | `IDS-SESSION-ID` and `INFA-SESSION-ID` | File Ingestion tasks and runs (§9; L-DBMI-060, L-DBMI-061) |

How to be sure you are on the right host (L-DBMI-001, 2026-07-26):

1. Read `<pod>` and `<domain>` from the login answer (`serverUrl` or `products[].baseApiUrl`); never guess them.
2. DNS: `<pod>-ing.<domain>.informaticacloud.com` resolves; a nonsense sibling such as `<pod>-bogusZZZ` does not.
3. A/B the same path: on the pod host `/dbmi/public/api/v2/task/details` gives a bare 404, while on `-ing` it gives a typed DBMI error. Only the second means the handler exists.

### What each answer means on the `-ing` host (L-DBMI-002, 2026-07-26)

| Call | Answer | Meaning |
|---|---|---|
| `GET /dbmi/public/api/v2/task/details` with a bogus id | `{errorCode:404, errorMessage:'DBMI_TASK_WAS_NOT_FOUND'}` | Live handler; the id is wrong or stale |
| any path | `No static resource <path>` | The route does not exist on this host |
| `GET /dbmi/public/api/v2/task/create` | 405 `Request method GET is not supported` | The POST verb exists |
| `POST /dbmi/public/api/v2/task/create` with an empty body | 500 `Cannot invoke "Object.getClass" because "o" is null` | The handler parsed and ran; send a real body |
| `GET /dbmi/public/api/v2/job/status` | 415 `Content-Type is not supported` (with or without params; POST gives 405) | Live, content-negotiating route. Use the v1 status route below. One 2026-09-22 run reports reading status here with a GET that carried a JSON body `{"jobId":<n>}`; that was not re-verified |
| a DBMI route called with a 22-character GUID | routing 404 | Use the numeric id (section 6) |
| any call answered by an HTML login page with status 200 | wrong header or wrong plane | Fix the header; never count it as success |

## 2. Authentication and headers

- Send `IDS-SESSION-ID: <v2 icSessionId>` (from `POST https://<domain>.informaticacloud.com/ma/api/v2/user/login`), plus `Content-Type: application/json` and `Accept: application/json`.
- The helpers that worked also sent `INFA-SESSION-ID` and `icSessionId` with the same value, and one early run (2026-09-22) used `Authorization: Bearer <jwt>` plus `IDS-SESSION-ID`. Which header the plane strictly requires was **not isolated**, so sending all three with the same session value is the safe choice.
- The v2 session dies 30 minutes after it is granted, however active it is. Refresh it at about 24–25 minutes, and on a 401 log in exactly once more (see [Access, Auth & Orgs](<../01 - Access, Auth & Orgs/>)).

## 3. The lifecycle at a glance

All calls go to `https://<pod>-ing.<domain>.informaticacloud.com` unless noted (L-DBMI-003, proven 2026-09-22, 2026-09-26, 2026-09-28, 2026-09-29).

| Step | Verb + path | Body | Success | Read-back | Notes |
|---|---|---|---|---|---|
| Create | `POST /dbmi/public/api/v2/task/create` | task JSON (section 4) | 200/201 `{"taskId":<n>,"frsId":"<frsId>"}` | `GET /dbmi/public/api/v2/task/details?taskId=<n>` | `location` = project only (L-DBMI-005) |
| Deploy | `POST /dbmi/public/api/v2/task/deploy/<taskId>` | `{}` | 202, `data.jobId` | `GET /dbmi/api/v1/task/<taskId>/job`: `processing_deploy` → `deployed` (about 8 s) | every deploy makes a **new** job id |
| Start | `POST /dbmi/public/api/v2/job/start` | `{"jobId":<n>}` | 202 | status `running` | for a freshly deployed job |
| Stop | `POST /dbmi/public/api/v2/job/stop` | `{"jobId":<n>}` | 2xx | `processing_stop` → `stopped` | keeps the deployment; a CDC slot now retains WAL |
| Resume | `POST /dbmi/public/api/v2/job/resume` | `{"jobId":<n>}` | 2xx | `running` | stopped or failed jobs only; 409 `WRONG_ACTION_FOR_DEPLOYED_JOB` on a never-started job (L-DBMI-008) |
| Undeploy | `POST /dbmi/public/api/v2/job/undeploy` | `{"jobId":<n>}` | 2xx | `processing_undeploy` → `undeployed` | stop a running job first |
| Delete | `DELETE https://<pod>.<domain>.informaticacloud.com/frs/api/v1/BaseEntities('<frsId>')` | — | 204 | the task is gone from `task/details` | undeploy first; see [Headless Deletes](<../10 - Migration & Org Management/06 Headless Deletes & Org Cleanup.md>) |

Create does not deploy, and deploy does not start. An initial-load (UNLOAD) task ends in `completed`; a CDC task stays `running`.

## 4. Creating a task

### 4.1 Body for a PostgreSQL → BigQuery CDC task (L-DBMI-004, 2026-09-29)

```json
{
  "taskType": "dbmi",
  "general": {"name": "<task>", "description": "<text>", "location": "<project>",
              "runtimeEnvironment": "<RE name>", "type": "combined"},
  "source": {
    "connection": "<pg connection name>", "schema": "public", "includeViews": "false",
    "replicationSlotName": "<slot>", "replicationPlugin": "pgoutput", "publication": "<pub>",
    "restartPointForIncrementalLoad": "LATEST",
    "selectionRules": [{"include": "<table1>"}, {"include": "<table2>"}],
    "customProperties": {
      "loadType": "CDC_COMBINED", "selectionMode": "RULE_BASED", "lobsEnabled": "true",
      "unloadIncludeViews": "false",
      "pwx.cdcreader.postgresql.connection.repl.slotname": "<slot>",
      "pwx.cdcreader.postgresql.connection.repl.publication": "<pub>",
      "pwx.cdcreader.postgresql.connection.repl.plugin": "pgoutput"}},
  "target": {
    "connection": "<bigquery connection name>", "schema": "<dataset>",
    "bucket": "<gcs bucket>", "directory": "<dir>",
    "renamingRules": [], "dataTypeRules": [],
    "customProperties": {"auditColumnsPrefix": "INFA_", "targetBucket": "<gcs bucket>",
                         "targetDirectory": "<dir>"}},
  "runtimeOptions": {
    "applyCycleIntervalSecs": "10",
    "schemaDriftOptions": {"addColumn": "ignore", "renameColumn": "ignore",
                           "dropColumn": "ignore", "modifyColumn": "ignore"},
    "customProperties": {"FlushPeriod": "5", "rat.cdcfile.cycle.interval.secs": "10",
                         "writerRecoveryEnableCycleUpdates": "false"}}
}
```

Rules:

- **`general.location` must be a project name.** A folder path is rejected. Create the task in `<project>`, then move it with FRS `MoveEntities` (by `frsId`) and tag it with `POST /public/core/v3/TagObjects` (L-DBMI-005, 2026-09-26).
- **Names, not ids.** `general.runtimeEnvironment`, `source.connection` and `target.connection` are names. A runtime-environment name copied from another org's template resolves to nothing (2026-09-22).
- **Keep the slot and publication in both places:** the top-level `replicationSlotName`/`publication` and the `pwx.cdcreader.postgresql.connection.repl.*` custom properties.
- **Never add `dataTypeRules` for a BigQuery target.** They do not apply, and a half-applied rule killed a job (L-DBMI-023, 2026-09-26).
- **`type` and `loadType`:** `"combined"` with `CDC_COMBINED` gives an initial load, then continuous CDC. `"initial"` with `UNLOAD` gives a one-shot initial load.
- **Selection rules** accept include and exclude entries, for example `[{"include":"*"},{"exclude":"<table>"}]` (L-DBMI-037, 2026-09-22).
- Latency settings (`FlushPeriod`, the apply cycle) are covered in [CDC from PostgreSQL](<02 CDC from PostgreSQL.md>).

### 4.2 Get a complete body from a working task (the fast clone)

`GET /dbmi/public/api/v2/task/details?taskId=<n>` (or `?pageSize=200` for all tasks) returns `documents[]`, each with `name`, `taskId` and `dbmiTask`, the full definition in the shape `task/create` accepts. To clone:

1. Deep-copy `documents[i].dbmiTask`.
2. Set a new `general.name`, and reset `general.location` to the project (details reports the full `<project>/<folder>` path).
3. Change what differs (connection names, slot, publication, selection rules, target dataset or directory).
4. `POST task/create`, then deploy.

This is how a task that would not deploy was replaced during an org move (L-DBMI-007, 2026-09-28).

## 5. Job states and what you may do next

| `status` | Meaning | Allowed next action |
|---|---|---|
| `processing_deploy`, `queued` | deploying | wait (poll every 5–8 s) |
| `deployed` | deployed, never started | `job/start` (not resume) |
| `running` | CDC streaming or load in progress | `job/stop` |
| `stopped` | stopped by request | `job/resume` (continues from the stored restart point, no re-baseline; the first apply comes at the next cycle, L-DBMI-056), or `job/undeploy` |
| `failed` | died on an error | read the task log; `job/resume` only for transient warehouse errors (L-DBMI-028), or after a source-host stop: PWX-36749 'Call to read from a replication slot failed' (Not retriable) does not clear when the database returns, and `job/resume` restarts from the restart point with no re-baseline (2.68 GB of slot lag drained in about 3 minutes; L-DBMI-063) |
| `failed_deploy` | the deploy failed (driver, key, connection) | fix the cause, then deploy again |
| `processing_stop`, `processing_undeploy` | transition | wait |
| `undeployed` | no job | FRS delete, or deploy again (new job id) |
| `completed` (UNLOAD) / `warning` | initial load finished | read the row counts |
| `awaiting_auto_restart` | the agent restarted (for example a host reboot) and the job is waiting to come back | wait: CDC jobs returned to `running` by themselves about 20 minutes after boot, with slot lag back to 0; treat it as transient for at least 30 minutes, and do not redeploy, resume or drop the slot meanwhile (L-DBMI-028, L-ENV-069, L-DBMI-016) |

A minimal client:

```python
import json, time, urllib.request, urllib.error

ING = "https://<pod>-ing.<domain>.informaticacloud.com"

def dcall(method, path, sid, body=None):
    h = {"IDS-SESSION-ID": sid, "INFA-SESSION-ID": sid, "icSessionId": sid,
         "Accept": "application/json", "Content-Type": "application/json"}
    data = json.dumps(body).encode if body is not None else None
    try:
        with urllib.request.urlopen(urllib.request.Request(ING + path, data=data, headers=h,
                                                           method=method), timeout=120) as r:
            raw = r.read
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        return e.code, e.read.decode(errors="replace")[:800]

def wait(task_id, sid, leave=("processing_deploy", "queued", "processing_stop", "processing_undeploy")):
    for _ in range(40):
        st, j = dcall("GET", f"/dbmi/api/v1/task/{task_id}/job", sid)
        s = j.get("status") if isinstance(j, dict) else None
        if s not in leave:
            return s, j
        time.sleep(8)
    return s, j

# create -> deploy -> start
st, r = dcall("POST", "/dbmi/public/api/v2/task/create", sid, task_json)
task_id, frs_id = int(r["taskId"]), r["frsId"]
st, r = dcall("POST", f"/dbmi/public/api/v2/task/deploy/{task_id}", sid, {})
job_id = (r.get("data") or {}).get("jobId")
status, j = wait(task_id, sid)                      # expect "deployed"
dcall("POST", "/dbmi/public/api/v2/job/start", sid, {"jobId": job_id or j.get("runId")})
```

## 6. Reading status, details and history

- **Status:** `GET /dbmi/api/v1/task/<taskId>/job` returns `status`, `runId` (the job id), `duration`, and `extraData.taskId` (which holds the `frsId`). This is the route every working tool used.
- **Details:** `GET /dbmi/public/api/v2/task/details?taskId=<n>` or `?pageSize=200` returns `documents[].{name, taskId, dbmiTask}`.
- **History:** DBMI runs show up in the v2 activity log (`GET /api/v2/activity/activityLog`) and in Monitor. Failed probe instances stay listed in Monitor > Running Jobs until they are undeployed (L-DBMI-031, 2026-09-24).
- **Task logs on the agent:** `<agent_home>/apps/Database_Ingestion/logs/tasks/*_<jobId>-CDC_COMBINED-*.log` (readable by root or the agent user only). A running job's processes show as `PwxAgent_dbmi_<task>_<job>` under the agent's OS user (L-DBMI-030).
- **Per-table state from the log** (L-DBMI-030). Each table's progress is logged as `transition event [<EVENT>]. Details: [table=<schema>.<table>`. `M4_UNLOAD_COMPLETE` ends a table's initial unload; `NORMAL_CONTINUOUS_CDC_TABLE` means it is streaming. A start, restart or switch is complete when every table's latest event is `NORMAL_CONTINUOUS_CDC_TABLE` and the file has no ` ERROR `, ` SEVERE ` or ` FATAL ` lines: `grep -oE 'transition event \[[A-Z0-9_]+\]. Details: \[table=[a-z_.]+' <log>` lists them (13 tables reached continuous CDC 3 min 13 s after a new job started, initial unload included). Prove an old job is gone by its log's last write time and zero `PwxAgent_dbmi_<task>_<job>` processes.

### Ids on this plane (L-DBMI-006, 2026-09-28)

| Id | Looks like | Comes from | Use it for |
|---|---|---|---|
| `taskId` | integer | `task/create` answer; `task/details` | every `/dbmi/...task...` route |
| job id (`runId`, `data.jobId`) | integer | the deploy answer; the status `runId` | `job/start/stop/resume/undeploy` |
| `frsId` | 22 characters | the create answer; `extraData.taskId`; the v3 objects list (type `DBMI_TASK`) | FRS move and delete, `TagObjects`, v3 export |

The `frsId` is the task's v3 object id. A GUID passed to a DBMI route gives a routing 404.

## 7. Changing a task: there is no update verb (L-DBMI-007, 2026-09-28)

| You want to change | Use | Why |
|---|---|---|
| runtime properties (flush, apply cycle) on the same task | **A: re-import** | keeps the task id and frsId; needs an undeploy |
| connection, slot, publication, table list | **B: create new, delete old** | clean and fast; the new task has a new id |
| copy a working task | **B** | details → edit → create |

**A. Re-import an edited export.** Stop and undeploy the job (DBMI refuses an import while the task is deployed). Then v3-export the task (by `frsId`) and edit `Explore/<project>/<folder>/<task>.DBMI_TASK.dat` (plain JSON; runtime properties sit in `common.runtimeSettings.runtimePropsMap`). Replace **only** that file's line in `exportPackage.chksum` with the upper-case SHA-256 of the new bytes, import with `OVERWRITE`, then deploy and start (a new job id). See [Editing Packages Safely](<../10 - Migration & Org Management/02 Editing Packages Safely.md>) for a worked example.

**B. Create a new task, then delete the old one.** Build the new body from `task/details` (section 4.2), create it, deploy it, then start it when you are ready. Stop and undeploy the old job, and delete the old task with FRS `BaseEntities('<frsId>')`.

A redeploy always creates a new job id, and a CDC_COMBINED task re-baselines (views over the target gapped about 3 minutes). For a clean initial load, also drop the target tables and the source-side `public.infa_persistent_<task>_<jobId>` table before you deploy (L-DBMI-009, 2026-09-26).

## 8. Deleting a task

1. If it is running, `job/stop`, then wait for `stopped`.
2. `job/undeploy`, then wait for `undeployed`.
3. `DELETE https://<pod>.<domain>.informaticacloud.com/frs/api/v1/BaseEntities('<frsId>')` with `IDS-SESSION-ID` returns 204. For batches, FRS `POST /frs/v1/DeleteEntities` returns a code per item.
4. Read back: the task is gone from `task/details`, and the v3 objects list no longer shows it.
5. For a CDC task, decide separately about its **slot and publication** in the source database. Never drop a slot another job still uses (L-DBMI-016).

`DELETE.../frs/api/v1/Documents('<id>')` gives 403; `BaseEntities` is the call the Explore UI makes.

## 9. What does not work, and what it tells you

| Call | Answer | Meaning / use instead |
|---|---|---|
| `POST /saas/api/v2/job` with a DBMI task id (any `taskType`: MI_TASK, DMI, DBMI, DRS, MTT) | 403 `UI_13404 'Object identifier is not valid or missing'` | DBMI tasks are not v2 tasks; use `-ing` (L-DBMI-010) |
| the agent's runAJob utility on a DBMI task | 403 `UI_13404` | same |
| `GET /saas/api/v2/mttask/<dbmi id>` | 403 `REPO_19035` | not an MTT |
| `POST /api/v2/miTask` (plus 6 name variants) | 404, or a login HTML page on POST | absent on the platform host |
| `/public/mi/v1/tasks` (plus 8 variants) | 404 `No static resource` | absent |
| `POST /public/core/v3/objects` with type `MI_TASK` | 405 | the v3 objects API is read-only |
| `mftsaas` on the pod root | 503 HTML; `/mftsaas/api/v1/jobs` gives 500 "needs ?type=running" | not a DBMI surface: `mftsaas` is File Ingestion (next paragraph) |
| `/dbmi/api/v1/tasks/<id>/deploy` (no `public` segment) | 404 | the deploy verb is `/dbmi/public/api/v2/task/deploy/<taskId>` |
| v3 `objects/<id>/deploy`, `activate`, `publish` | 404 | not a DBMI surface |
| any managed MCP tool | no DBMI deploy verb exists (2026-09-23) | use REST |
| agent-local `dbmi_deploy.sh` or a file drop into `apps/Database_Ingestion/data/tasks` | manages the service, not tasks | not a deploy path |

**File Ingestion (Mass Ingestion Files) is headless on `mftsaas`** (L-DBMI-060, L-DBMI-061, L-DBMI-062, 2026-10-26). All
calls go to `https://<pod>.<domain>.informaticacloud.com/mftsaas/api/v1/` (the `/saas/mftsaas/...` form returns the login
page) with `IDS-SESSION-ID` and `INFA-SESSION-ID`:

1. **Create:** `POST mitasks` with `sourceType` CONNECTION and `sourceConnection {id, type: "Azure Blob"}`, `targetType`
   LOCAL_FOLDER and `targetConnection {type: "local"}` (case matters), `sourceParameters` as a map of **strings**
   (`filePatternFilter: "true"`, `filePattern` such as `*.pdf`, `filePatternType: WILDCARD`, `blobSourceLocation`),
   `targetParameters {targetDirectory, fileExistsAction: OVERWRITE}`, `agentGroupId` = the runtime, and `location
   {projectId, projectName, folderId, folderName}` set at create time (a later PUT refuses to change it). The errors name
   the missing field, so iterate from a partial body.
2. **`blobSourceLocation` = the container name** for Azure Blob Storage V3, even when the connection names the container:
   with `/` the first run failed at listing ('Listing files failed: Unable to connect') although the connection tested
   fine; with the container name every later run was SUCCESS.
3. **Run and poll:** `POST job` `{"taskId": "<id>"}` returns `runId`; `GET job/<runId>/status` returns `jobStatus` and
   `successFiles`. Keep polling while jobStatus is empty, SUBMITTED, QUEUED, STARTING or RUNNING; a 2-file copy reached
   SUCCESS in under 20 s.
4. **Runtime:** the agent needs the Mass Ingestion-Files service and the source connector selected; the selections PUT
   rolls the engines for a few minutes, so start no runs on that agent meanwhile (L-AGENT-042).
5. **Use:** a taskflow step that lands cloud-storage files in an agent folder before a mapping that reads local files,
   or a CAI process that starts the task, polls it (Wait + Jump, 8 s, at most 30 polls) and starts the mapping's
   taskflow only on SUCCESS. A task started from a process has no used-by link: a cleanup that archived it as
   'unused' broke the live flow, so grep process XML for task ids before archiving (L-CLEAN-025). FRS `MoveEntities`
   moves the task between folders (200).

## 10. Error signatures

| Signature | Where | Cause | Fix |
|---|---|---|---|
| `DBMI_TASK_WAS_NOT_FOUND` | `-ing` | wrong, stale or GUID id | numeric `taskId` from `task/details` |
| `No static resource <path>` | `-ing` or pod host | route absent on that host | check host and prefix |
| 405 `Request method GET is not supported` | create | GET on a POST route | POST |
| 500 `... "Object.getClass" because "o" is null` | create | empty body | send the task JSON |
| 415 `Content-Type is not supported` | `job/status` | content negotiation | use `/dbmi/api/v1/task/<taskId>/job` |
| 409 `WRONG_ACTION_FOR_DEPLOYED_JOB` | `job/resume` | the job was never started | `job/start` |
| deploy → `failed`, log `Failed to load driver class com.simba.googlebigquery.jdbc.Driver` | agent | Simba BigQuery JDBC set missing | [DBMI Targets & Drivers](<03 DBMI Targets & Drivers.md>) (L-DBMI-033) |
| `Mass Ingestion service could not find active agents` | `job/start` or `task/deploy` right after an agent restart | the Mass Ingestion engine is still starting | wait until `Database_Ingestion` and `MassIngestionRuntime` read RUNNING in `GET /api/v2/agent/details/<agentId>`, then retry once (L-DBMI-052) |
| deploy → `failed`, `[Simba] Invalid PKCS#8 data` | agent | BigQuery key in the wrong form for DBMI | a DBMI-only connection (L-DBMI-034) |
| import: `Cannot validate vendor for task with type UNLOAD... 403 FORBIDDEN. Access denied.` | v3 import | probably no Database Ingestion engine on the target agent yet | enable the engine; or create the task later with `task/create` (L-DBMI-032) |
| `VerifyValueException: Field Schema.column value error: no columns` | UNLOAD run | a table with a character primary key | exclude it, or add a numeric surrogate key (L-DBMI-038) |
| `Retrying the job may solve the problem`, `100032`, `backendError`, `rateLimitExceeded` | CDC job log | transient warehouse error | `job/resume` (bounded; L-DBMI-028) |
| `Value of type...`, `cannot be assigned to`, `does not exist`, `Permission denied` | CDC job log | schema, type or rights error | fix the cause; never auto-resume |
| a 200 whose body is an HTML login page | any | wrong header or plane | `IDS-SESSION-ID`; the correct host |
| `PWX-36749 'Call to read from a replication slot failed'` (Not retriable), job `failed` | CDC job, after a hard stop of the source host | the jobs do not recover by themselves when the database returns | `job/resume`; auto-resume on a restart window ([CDC from PostgreSQL](<02 CDC from PostgreSQL.md>) §8; L-DBMI-063) |
| 'Listing files failed: Unable to connect' on a File Ingestion run | `mftsaas` job | `blobSourceLocation` was `/` | the container name (§9; L-DBMI-062) |

## 11. The DBMI command-line client (alternative)

The agent ships `<agent_home>/apps/dbmicli/dbmicli.jar`. Run it with the agent's JDK (`JAVA_HOME=<agent_home>/jdk`) and log in at the **domain** host (`<domain>.informaticacloud.com`), not the pod host. Task definitions are YAML: source connection and schema, table list, target connection and schema (L-DBMI-040, 2026-07-06). The REST lifecycle made it unnecessary in later work; it is still useful for reading the vendor enum of supported targets (a Fabric target failed there, see [DBMI Targets & Drivers](<03 DBMI Targets & Drivers.md>)).

## 12. Entitlement: engines and privileges, not 404s

DBMI is entitled when `GET /api/v2/agent/details/<agentId>` lists the `Database_Ingestion` and `MassIngestionRuntime` engines as RUNNING and the user holds the `create.dbmi.task` and `execute.dbmi.task` privileges. The runtime environment must also have the Mass Ingestion (databases) service selected (see [Secure Agent & Connections](<../02 - Secure Agent & Connections/>)). A 404 on a DBMI path means the wrong host or path, not a missing license (L-DBMI-041, 2026-07-25).

When an org hits its monthly job limit, CDI starts fail within seconds, but a running DBMI CDC job keeps working (L-DBMI-044, 2026-09-28; see [IPU, Metering & Licensing](<../11 - IPU, Metering & Licensing/>)).

## 13. Overturned beliefs (latest evidence wins)

| Earlier belief (dates) | What overturned it | Lessons |
|---|---|---|
| "Mass Ingestion authoring is a UI wizard; every mi/dbmi REST path 404s" (2026-07-04 to 2026-07-25) | the probes had all used the platform host; DBMI answers on `<pod>-ing` (2026-07-26) | L-DBMI-045 → L-DBMI-001 |
| "A DBMI 404 means a missing entitlement that needs a purchase" (early July) | engines RUNNING and privileges present (2026-07-05 to 2026-07-25) | L-DBMI-046 → L-DBMI-041 |
| "DBMI deploy and run have no public REST verb" (26-probe matrix, 2026-09-22; 'No static resource' on one agent build, 2026-09-23) | `task/deploy` and `job/start` under `/dbmi/public/api/v2` (the probes missed `public`), proven 2026-09-22 and again 2026-09-26 to 2026-09-29 | L-DBMI-047 → L-DBMI-003 |
| "Author the first DBMI task in the UI wizard, then clone it" (2026-07-04 to 2026-09-21) | `task/create` from a JSON body | L-DBMI-048 → L-DBMI-003 |
| "Import creates a DBMI task, but deploy is a UI click" (2026-07-26) | `task/deploy` after import (see [Migration-Clone Authoring](<../10 - Migration & Org Management/03 Migration-Clone Authoring.md>)) | L-MIG-067 → L-MIG-024 |

## 14. Lessons in this doc

L-DBMI-001 to L-DBMI-010, L-DBMI-023, L-DBMI-028, L-DBMI-030 to L-DBMI-033, L-DBMI-037, L-DBMI-038, L-DBMI-040, L-DBMI-041, L-DBMI-044, L-DBMI-052, L-DBMI-060 to L-DBMI-063, and the superseded L-DBMI-045 to L-DBMI-048. Full text: [Lessons: Mass Ingestion & CDC](<../13 - Lessons Learned/04 Mass Ingestion & CDC.md>).
