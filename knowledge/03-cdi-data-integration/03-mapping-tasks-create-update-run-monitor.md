# Mapping Tasks: Create, Update, Run, Monitor

**Answers:** How to create, update (POST, no PUT), run, monitor and delete a mapping task over v2; which `$Source$`/`$Target$` keys matter; how write modes and truncation behave per connector; how to read a run's outcome, its session log and its error codes; which failures deserve one automatic retry.

**Read when:** before writing any `/api/v2/mttask` or `/api/v2/job` call; when a run's state, row count or error text needs interpreting.

**Key rules:**
- Update = POST the full body to `/api/v2/mttask/<id>` and read it back; a 200 whose value reverted is a silent rejection (L-CDI-046, L-CDI-050).
- Poll the activity log by `runId`, never by the first row; a WARNING with 0 rows is a failure (L-CDI-059, L-CDI-060).
- The session log over REST (`/activity/activityLog/<entryId>/sessionLog`) is the evidence of what the engine did (L-CDI-211).
- Retry a FAILED task once, only on transient signatures, never on the monthly-limit error (L-CDI-205).
- At the job cap only the first run carries the error; later runs log as zero-row non-success, so count both (L-IPU-060, L-IPU-041).
- Insert-mode re-runs over a cloned mapping double the target unless its `TruncateTable` property is YES (L-CDI-166).

**Related:** [02 How Claude Builds Mappings Headless](02-how-claude-builds-mappings-headless.md) · [04 Taskflows & Schedules](04-taskflows-schedules.md) · [08 Changing Pipelines Safely](08-changing-pipelines-safely.md) · [09 Source & Target Gotchas](09-source-target-gotchas.md) · [Lessons: CDI](../../lessons/by-domain/03-data-integration-cdi.md)

**Last verified:** 2026-11-03

> **Summary.** A mapping task (MTT) is created with `POST /api/v2/mttask` and updated by POSTing the **full** body back to `/api/v2/mttask/<id>`; there is no PUT. Over a Copy Data template, the body needs complete `$Source$`/`$Target$` parameters. Over a real mapping, `{mappingId, runtimeEnvironmentId}` is enough.
> BigQuery write behaviour lives in `$Target$.oprRuntimeAttrs` (Bulk + "Write truncate" / "Write append"). On tasks over real mappings, target-parameter POSTs are **silent no-ops**: re-import the mapping instead.
> Run with `POST /api/v2/job` by v2 `taskId` (`taskType` `MTT` or `WORKFLOW`) and poll `GET /api/v2/activity/activityLog?taskId=<id>&rowLimit=1` until `runId` matches.
> Delete with `DELETE /api/v2/mttask/<id>`. A read-back 403 means the task is gone; `REPO_52013` means it is still bound to a schedule.

---

## 1. Plane, host, headers

- Base: the `serverUrl` returned by the v2 login, `https://<pod>.<domain>.informaticacloud.com/saas`, plus `/api/v2/...`. Header `icSessionId: <v2 session>`, with `Content-Type: application/json` and `Accept: application/json`.
- The v2 session dies about 30 minutes after it is granted. Cache it and refresh at about 25 minutes. On a 401, drop the cache and log in exactly once more (see [knowledge/01-access-auth-orgs](../01-access-auth-orgs/)).
- **Update idiom:** POST the full object to `/<resource>/<id>`. `PUT` returns 405 on both `/api/v2/mttask` and `/api/v2/mttask/<id>` (L-CDI-046).
- Wrapper calls must **not raise** on 4xx/5xx: return `(status, body)` and let the caller decide. Check the status on every call.

## 2. Create

**Over a Copy Data template (route 1).** A minimal body fails with `APP_13507`. The body must carry the full `$Source$` (type `EXTENDED_SOURCE`) and `$Target$` (type `TARGET`) parameter objects. The reliable method is to GET a working task over the same template, strip it, change the fields, and POST (L-CDI-046, L-CDI-022; body in [02](02-how-claude-builds-mappings-headless.md) §3):

```
POST /api/v2/mttask
{ "@type": "mtTask", "name": "mt_<app>_<layer>_<entity>", "description": "[<tag>]...", "shortDescription": "...",
  "mappingId": "<v2 id of dsst__copy_data_new_tgt>", "runtimeEnvironmentId": "<reId>", "sessionProperties": {},
  "parameters": [ {"name": "$Source$", "type": "EXTENDED_SOURCE",... },
                  {"name": "$Target$", "type": "TARGET",... },
                  {"name": "$p_filter_src$", "text": "TRUE", "uiProperties": {"required": "false"},...},
                  {"name": "$p_tgt_excluded_fields$", "text": "NONE", "uiProperties": {"required": "false"},...} ] }
-> 200 {"id": "<taskId>", "frsGuid": "<frsGuid>",...}
```

- Value-less STRING parameters without `uiProperties.required` are treated as required, and the task is rejected with `APP_13506`/`APP_13507`. Set `"required":"false"` and give placeholders (L-CDI-047, 2026-09-23).
- `errc=-1` under `schemaMode:"async"` means validation was **deferred**, not failed. `valid=true` is authoritative.

**Over a real mapping (routes 3 and 5).** A minimal body works (L-CDI-037, 2026-09-29):

```
POST /api/v2/mttask {"@type":"mtTask","name":"mt_<x>","description":"[<tag>]...","mappingId":"<v2 mapping id>","runtimeEnvironmentId":"<reId>"}
-> 200 {"id": "<taskId>"}          # find the mapping id with GET /api/v2/mapping, by name inside the intended folder
```

- `403 APP_13533 "specify a mapping id"` means you tried to author a mapping through the task API. A task only wraps an existing `mappingId` (L-CDI-046).
- The new task lands in **`Default`**. Move it with FRS `MoveEntities` (§7).
- Reuse the task if the name already exists in the intended folder. Assert the org before creating.
- **Names refuse parentheses** (L-CDI-280, 2026-10-28): a generated mapping named with `(...)` imported without complaint, then its task create failed with `APP_13500`, so the deploy stopped halfway. Normalise generated names to letters, digits, spaces and hyphens before the first import, and check that every task exists after a deploy (connections refuse parentheses with APP_10500, L-CONN-124).

**Vary the source SQL per run (L-CDI-284, L-CDI-285, 2026-11-01).** Editing `$Source$.customQuery` works on the Copy Data templates because their source is a parameter; on a mapping whose source query is fixed, the run executes the mapping's own query whatever the task holds. Make the mapping's Source query an in-out parameter (`$$SRC_SQL`). Short values can go in the task's `currentValue`; a default of about 4,000 characters and up makes `POST /api/v2/mttask` fail `403 REPO_19001`. For long SQL:
1. Set the task's `parameterFileName` to `<lane>.param`; the agent resolves it in `<agent_home>/apps/Data_Integration_Server/data/userparameters/`, and the file holds one line `$$SRC_SQL=<the SQL on one line>`.
2. Before each run, install that run's staged file on the agent host (this needs a shell there) and fail the item if the install fails, so a lane never reruns the previous SQL.
3. For N lanes, clone the task N times: GET it, drop `id`, `frsGuid`, the create and update stamps, `lastRunTime`, `orgId`, `scheduleId` and `federatedId`, pop `parameters[].id`, set a new name and `parameterFileName`, POST.
4. When a mapping that already has tasks gains a new in-out parameter, an OVERWRITE import fails while it redeploys the dependent tasks: delete the task, import, then recreate it. The session-log warning `VAR_27062` 'Cannot find section for worklet' about the agent's own `data/parameters/s_mtt_<taskId>.param` is harmless.

## 3. `$Source$` / `$Target$` parameter reference (Copy Data template)

| Parameter key | Meaning | Values used |
|---|---|---|
| `$Source$.sourceConnectionId` | Source connection | `<connId>` |
| `$Source$.customQuery` | Whole source SELECT, in the source's dialect | SQL, or remove the key for an object source |
| `$Source$.sourceObject`, `objectName` | Source object | `DUMMY_Source` (query); `<schema>/TABLE/<table>` or `<schema>/VIEW/<view>` (PostgreSQL); `<SObject>` (Salesforce); `<file>.csv` (flat file) |
| `$Source$.extendedObject.object`, `.objects[]` | Object descriptors | `name` = the object, `label` = last path segment, `dbSchema = ""` |
| `$Source$.srcFFAttrs` | Flat-file reader settings | `{"@type":"flatFileAttrs","delimiter":",","textQualifier":"\"","escapeChar":"","headerLineNo":1,"firstDataRow":2,"consecutiveDelimiterAsOne":false}` |
| `$Target$.targetConnectionId` | Target connection | `<connId>` |
| `$Target$.targetObject`, `targetObjectLabel`, `newObjectName`, `objectName`, `objectLabel` | Target object | `<dataset>/<table>` (BigQuery). For PostgreSQL and Salesforce: `objectName = targetObject = <path>`, labels = table/object, and pop `newObjectName` |
| `$Target$.newObject` | Create the target at run time | `false` for existing tables |
| `$Target$.tgtObjectAttributes` | Target container | `{"parent":"<dataset>"}` (BigQuery); `{}` otherwise |
| `$Target$.oprRuntimeAttrs` | **Write behaviour (BigQuery)** | `{"writeMode":"Bulk","writeDisposition":"Write truncate"|"Write append"}` (L-CDI-048) |
| `$Target$.runtimeAttrs` | Connector runtime attributes | `{}` for BigQuery (values here are ignored). JDBC V2: `{"Pre SQL":"TRUNCATE TABLE <t>"}` (L-CDI-171) |
| `$Target$.operationType`, `targetUpdateColumns` | Insert vs upsert | `"Insert"`, or `"Upsert"` with `[<key>]` / `[<ExtId__c>]` |
| `$Target$.truncateTarget` | Truncate before load | `false`. Connector behaviour is unreliable; see §4 |
| `fetchMode` (on `$Source$` and `$Target$`) | When field metadata is read | `"RUNTIME"` whenever the target or query gains columns. Without it IDMC keeps the field list from creation time and **silently writes NULL** into new columns (L-CDI-049) |
| task level: `runtimeEnvironmentId`, `agentId` | Where it runs | Drop `agentId` when moving the task to another runtime environment, e.g. a hosted one |

## 4. Write modes and truncate rules

| Connector | Full reload | Append | Traps |
|---|---|---|---|
| BigQuery V2 target | `writeMode Bulk` + `writeDisposition "Write truncate"` in `oprRuntimeAttrs`. Needs a GCS staging path on the connection, and the service account needs `roles/storage.objectAdmin` on the bucket (L-CDI-154) | `"Write append"` | **Streaming** mode cannot truncate: a second run doubled the rows (33,106 → 66,230). A **0-row** source leaves the old rows in place, so truncate those targets yourself (L-CDI-088). `truncateTarget=true` alone was ignored on some tasks and targets doubled (July; L-CDI-155) |
| JDBC V2 target | `runtimeAttrs {"Pre SQL": "TRUNCATE TABLE <t>"}`. The key needs the space: `preSQL` and `PreSQL` are silently ignored | Insert | `truncateTarget` is ignored (L-CDI-171). The connection's bound database wins over the object's schema (L-CDI-040) |
| PostgreSQL target | Upsert on a key, or Insert with a database-side idempotency trigger | Insert | Whether `truncateTarget=true` truncates or is ignored is **disputed**. Never use it on a system-of-record table (L-CDI-169, L-CDI-194) |
| Salesforce target | Upsert on an external id | — | See [09](09-source-target-gotchas.md) |
| Any target of a cloned template mapping | The mapping's target session property `TruncateTable` (some packages spell it `Truncate Table`) = YES | Insert | With NO, the mapping appends its full row set on every run, so a re-fired or scheduled task doubles its target (10 → 20). Patch both spellings to YES in the mapping model, recompute the package checksums and re-import; the engine then truncates before load. Proven on create-new-at-runtime targets (L-CDI-166) |

Switching an existing task between truncate and append: GET, check `$Target$.oprRuntimeAttrs.writeDisposition`, set it, and POST the body back without the audit fields (L-CDI-051).

## 5. Update

```
cur  = GET /api/v2/mttask/<id>
body = cur minus {orgId, createTime, updateTime, createdBy, updatedBy}   # keep id and frsGuid
       (popping agentId and each parameters[].id also worked; do it when moving runtime environments)
edit only the field you mean (e.g. $Source$.customQuery, after asserting the anchor you replace occurs exactly once)
POST /api/v2/mttask/<id>  -> 200
GET  /api/v2/mttask/<id>  -> compare the changed field   # a 200 whose value reverted is a silent rejection
```

- Save a backup first: the v2 JSON, the old SQL as a file and a v3 export. Undo = POST the saved JSON back ([08](08-changing-pipelines-safely.md), L-CDI-135).
- Run the changed task once on its own while no taskflow that contains it is running, then patch the generator so that a rebuild produces the same body.
- **A runtime-only change** (a failover off a downed runtime): drop createTime, updateTime, createdBy, updatedBy, lastRunTime and agentId, set `runtimeEnvironmentId`, POST and read back; 17 tasks moved in seconds with ids, schedules and taskflows unchanged. Move the connections their lookups use too ([knowledge/02-secure-agent-connections](../02-secure-agent-connections/); L-ENV-100, L-CONN-132, 2026-11-03).

## 6. The silent-no-op trap (read this before any retarget)

- **On tasks over real (fixed-connection) mappings.** POSTing the task with changed target parameters (`targetObject`, `targetObjectLabel`, `newObjectName`, connection) returns **200**, and the read-back still shows the mapping's targets. The task re-derives its targets from the mapping. Proven 2026-09-29: 10 tasks POSTed, 10 read-backs unchanged. The one task whose mapping had already been re-imported with live targets showed the new targets (L-CDI-050).
- **Cross-connector retarget of any task** (e.g. BigQuery to another warehouse's connector) also returned 200 and silently kept the original `targetConnectionId` (2026-07-04; L-CDI-050, L-CDI-031).
- **What works:** change the **mapping**. Build its package again with the new targets (for a generated mapping, re-run the generator on a "swap" spec with the same mapping GUID), import it with `OVERWRITE` under the same GUID, and re-read the task (L-CDI-145). Tasks over **Copy Data templates** are different: their `$Target$` is task-owned, and target changes do stick (they are how route 1 works).
- **The other direction: a designer save redeploys the tasks** (L-CDI-228). Saving a mapping in the designer ends with `POST /saas/app/da/dTemplatesXHR.do?actionMethod=autodeploy` (`daId` = the v2 mapping id), which redeploys every task on it. A mapping save therefore changes what the next run of each task executes without touching the task: treat it as a change to every task on the mapping ([08](08-changing-pipelines-safely.md)).

## 7. Move and tag

- **Move:** `POST https://<pod>.<domain>.informaticacloud.com/frs/api/v1/MoveEntities` (or `/frs/v1/MoveEntities`), header `IDS-SESSION-ID: <v2 icSessionId>`, body `{"xferSpec":{"targetLocationId":"<folder frsGuid>","sourceSpecArr":[{"sourceEntityId":"<task frsGuid>","mergeTags":""}]}}`. One variant also sends `destName`, `destDesc`, `conflictResolution:"NONE"` and `resetExpiryTime:false`. Success is `XFER_200` "Operation succeeded on N artifacts", or `FRS_200` per item. At most 25 ids per call. Get the `frsGuid` from the detail GET, because the list omits it. Runs keep working: ids, `mappingId`, schedules and history are unchanged (L-CDI-016).
- **Tag:** `POST /public/core/v3/TagObjects` with `[{"id":"<frsGuid>","tags":["<tag>"]},...]`, at most 50 per call. Read each item's status (200/201/204/207). Folders and projects fail ("of type: [Folder]"). Imports drop tags, so re-tag after every import (L-CDI-054).

## 8. Run

```
POST /api/v2/job  {"@type":"job","taskId":"<v2 taskId | wfId>","taskType":"MTT" | "WORKFLOW"}
-> 200 {"runId": <n>, "taskName": "...",...}
```

- Identify the task by its **v2 `taskId`**. `taskFederatedId` worked in one org when given the task's own federated id (2026-09-22). A wrong, stale or foreign id gives `403 REPO_19035` or `UI_13429` (2026-08-19, 2026-09-21; L-CDI-057).
- It runs even when the runtime-environment list says `readyToRun:false`. That flag is stale on the list and only mattered for catalog operations (L-CDI-056).
- `taskType "WORKFLOW"` starts a **linear** taskflow. Advanced taskflows were rejected with `403 UI_13430` (L-CDI-071).
- Before starting, check the activity monitor: starting something already running, or a taskflow that shares tasks with a running one, fails with `REPO_17314` (L-CDI-078).
- REST-started runs show a REST context (e.g. `REST_API_V2`) in the activity log; schedule-started runs show the scheduler.
- The managed **Job Management** MCP server wraps the same plane: `run_mapping_task`, `get_job_status`, `stop_running_job`. REST is equivalent (L-CDI-068).
- Each run is one job against the org's monthly job cap. So is each taskflow run ([07](07-performance-concurrency-job-caps.md)).

## 9. Monitor

**Activity-log poll (L-CDI-059, 2026-09-28):**

```python
rid = POST("/api/v2/job", {...})["runId"]
deadline = now + 60*60                     # 60 min per task; use 2 h for a taskflow
while now < deadline:
    sleep(5..10)
    rows = GET(f"/api/v2/activity/activityLog?taskId={task_id}&rowLimit=1")
    if rows and rows[0]["runId"] == rid and rows[0].get("endTime"):      # never trust rows[0] alone (L-CDI-059)
        x = rows[0]
        state = {1: "SUCCESS", 2: "WARNING", 3: "FAILED"}[x["state"]]
        if x["state"] == 2 and not x.get("successTargetRows"):
            state = "FAILED"                  # a warning that wrote nothing is a failure (L-CDI-060)
        return state, x["successTargetRows"], x["failedTargetRows"], x["errorMsg"], x["id"]
return "TIMEOUT"
```

- **Match on `runId`.** The first row can be the previous run's finished entry while the new run is still in flight, which produces false failures or false successes.
- **Taskflow children** do not appear under their own task id. They are the `entries[]` of the taskflow's activity-log row (`objectName`, `state`, `successTargetRows`, `errorMsg`, `startTimeUtc`, `runId`). Children missing after a stop did not run (`stopOnError`; L-CDI-061). The log's outer rows are batches, so flatten `entries[]` for per-run rows.
- **Times:** on US pods `startTime`/`endTime`/`createTime` are pod-local (UTC-4) but carry a `Z`. Use `startTimeUtc`/`endTimeUtc` (L-CDI-063).
- **What is running now:** `GET /api/v2/activity/activityMonitor[?details=true]` lists `taskName`, `taskId`/`objectId` and `subTaskName` or `currentTaskName`. 0 rows means nothing is running. Do not trust a derived "jobs running" gauge; one read 17 while the monitor had 0 rows (L-CDI-062).
- **On the agent host:** each run writes `<agent_home>/apps/Data_Integration_Server/logs/s_mtt_<taskId>_<n>.log`. `TM_6014` marks the session start, `PETL_24012`/`PETL_24013` the end (13 = failure), `WRT_8036 Target: <table>` the target, `Applied Rows [N]` the count, and "Session run completed successfully" the verdict. Parsing these gives exact timing and row evidence with no API calls (L-CDI-064).
- **Health:** a watcher that reads each important taskflow's last runs every 15 minutes and alerts only on state change caught silent hourly failures. Run one watcher per org (L-CDI-067).
- **The activity log is not complete history** (L-CDI-288, 2026-11-01): `GET /api/v2/activity/activityLog?rowLimit=1000&offset=<n>` returned 1,076 entries reaching back three weeks for a project that started more than 500 jobs a day, and each task carries `maxLogs: 10`. For billing proxies, reconciliation or 'who wrote this row', write your own ledger at completion (task id, run id, start and end from the `*Utc` fields, success and failed rows, error text) and stamp the same run id into the rows written (`$CurrentTaskId` / `$CurrentRunId`).
- **Before re-arming a job paused for a run:** activity monitor at 0 and no `pmdtm`/DTM process on the agent (L-CDI-065).

**The session log over REST** (L-CDI-211). No shell on the agent host is needed:

```
GET <serverUrl>/api/v2/activity/activityLog/<entryId>/sessionLog
icSessionId: <v2 session>
Accept: */*
-> 200, text/plain (about 75 KB for a 5-target mapping)
```

`<entryId>` is the `id` of the run's activity-log entry, not its `runId`. Grep the text for what you must prove: `TM_6721`/`TM_6722` (optimization start and finish, with its duration), `OPT_63367` (full SQL ELT enabled), `OPT_63375` (the fallback mode), the connector's `INSERT INTO` lines and per-step execution times, the first `[ERROR]`. Save it with the run id as evidence.

**What the session log tells you about buffers and SQL** (L-CDI-290, 2026-11-01): `TM_6660 Total Buffer Pool size is <n> bytes and Block size is <m> bytes` (defaults gave one wide-port task a 22 MB pool and 1.2 MB blocks), `TM_6966` when the request was trimmed, `TM_6187` the commit interval, and `JDBC_V2_10000 [INFO]` lines with the connection string and the exact SELECT and INSERT. `DBG_21699 Waiting for consumer to free buffer block` from the READER thread is back-pressure (the downstream is slower than the read); on a long read it precedes a 'Premature EOF' (L-CDI-267). Predict rows per INSERT from block size / declared row width before changing batch sizes (L-CDI-262). The start-of-session warnings 'Invalid value false for attribute Truncate Target / Apply Custom Schema' are harmless.

**Outcome rules for a controller or watcher** (L-CDI-205, L-IPU-060, L-CDI-287):

| Run outcome | Meaning | Action |
|---|---|---|
| FAILED with a BigQuery 503 ('Retrying may solve the problem', 'backend error'), HTTP 500/502/503/504 in the message, 'service unavailable', 'rate limit', 'connection reset', a staging-file upload error, `Temp_View<digits>` with 409/404, or "Table [<table>] does not exist" for a table that exists | transient | start it once more after about 20 s (at once for a lane's core task); record the first error and a RETRYING state; never retry the same run twice |
| FAILED with 'Aborted by agent disconnection.' (every running workflow fails in the same second when the agent host reboots), 'java.io.IOException: Premature EOF', 'Too many simultaneous queries', 'JDBC V2 adapter not available', 'job not found on agent', 'DTM process terminated', connection reset or broken pipe, a database memory limit | transport or capacity (L-CDI-287, 2026-11-01) | retry up to 3 times with backoff |
| FAILED with a cast error, null into a non-nullable column, a constraint violation, 'User does not have permission to execute the asset ...' or a repository save error | deterministic (L-CDI-287) | fix it; never retry. Failed-target-row counts that repeat (60, 72, 12) reveal the writer's batch size (L-CDI-262) |
| FAILED 2-3 s after start, 0 rows, 'no active Secure Agent in group Informatica Cloud Hosted Agent' | a Hosted Agent outage (L-AGENT-117) | fail over the tasks and their connections; do not retry in place (L-ENV-100) |
| FAILED with 'monthly limit' | the job cap (L-IPU-041) | no retry; hand it to the quota breaker ([07](07-performance-concurrency-job-caps.md) §7) |
| empty error, 0 rows, a state outside 1/2/3, after a cap error in the same window | blocked by the cap | count it with the cap failures; a breaker that matches the message only on FAILED rows sees a fraction of the blocked runs |
| FAILED with a heap OOM, validation, authentication or data error | real failure | report it; do not retry |
| persistent 'Internal error... DTM process terminated unexpectedly' | a host problem | see [knowledge/02-secure-agent-connections](../02-secure-agent-connections/) |
| WARNING with rejected rows on a SaaS target (storage full, duplicates, locks) | the target refused writes | alert on the target; do not fail the lane |
| WARNING with 0 rows written | failure (L-CDI-060) | treat as FAILED |

Use one case-insensitive pattern for the transient class, for example `retrying may solve the problem|[^0-9]50[0234][^0-9]|backend ?error|service unavailable|rate ?limit|connection reset|temp_view[0-9]+|does not exist`, and skip any message containing `monthly limit`. Each retry is one more job against the cap. Without a retry, an event-driven lane leaves its record waiting for the next event: one transient 'does not exist' failure cost a record 28 minutes. Do not auto-retry SaaS writes that failed on target-side limits; they only repeat.

**Alert rules that do not cry wolf** (L-ENV-077). Derive each freshness SLA from the schedule of the job that loads the table, plus slack (a daily load needs about 26 h, not 90 min); page "no new rows" stalls only on one or two heartbeat tables that always move while the source application is alive, and keep per-table recency as dashboard data; exclude drained-by-design tables (processed queues) from volume-drop alerts and require a minimum previous count (for example ≥ 50); report empty-at-source tables as NO_ACTIVITY; give history and snapshot tables their own scheduled writer; inventory every alert channel (BI alerting and any direct emailers in collector scripts), fix each at its source, and state-dedupe emailers (mail when the red set changes, then one RECOVERED).

## 10. Error codes

| Code / symptom | Where | Meaning | Action |
|---|---|---|---|
| `APP_13507`, `APP_13506` | create/update MTT | Parameters incomplete, or value-less parameters treated as required | Full `$Source$`/`$Target$`; `uiProperties.required="false"` |
| `403 APP_13533` "specify a mapping id" | create MTT | No `mappingId` | Tasks only wrap existing mappings |
| `405` | `PUT /api/v2/mttask[/<id>]` | No PUT on v2 | POST to `/<id>` |
| 200 but the value reverted | update MTT | Silent rejection | §6 |
| `403 UI_13404` "Object identifier is not valid or missing" | `/api/v2/job` | The id is not a runnable DI task (a DBMI or MI task, a profile, an undeployed object) | Use that service's own API (L-CDI-058) |
| `403 UI_13429` | `/api/v2/job` | Stale or foreign federated id | Re-resolve in this org |
| `403 REPO_19035` "task does not exist" | job start, `GET /api/v2/mttask/<id>` | Wrong id type, or the id belongs to another org | Look the task up in this org's objects |
| `REPO_17314` "Another instance … is currently running" | job start | The task or a taskflow sharing tasks is running | Wait; hold a quiet window (L-CDI-078) |
| "You have exceeded your monthly limit of 10,000 jobs" | every run, ~5 s | Org job cap | Quota breaker ([07](07-performance-concurrency-job-caps.md)) |
| Empty error, 0 rows, a state outside 1/2/3 | runs after a cap error | Blocked by the job cap; only the first run of a lane carries the message | Count them as cap blocks (L-IPU-060) |
| `PLUGIN_1762... OutOfMemoryError: Java heap space`, then `BIGQUERYV2_10000... 5001 - Unexpected error refreshing access token` and `WRT_8044 No data loaded` | run | DTM heap exhausted; the token errors are a cascade | Read the first `[ERROR]`; see [09](09-source-target-gotchas.md) §7 (L-CDI-210) |
| `Temp_View<epoch-ms>` with 409 'Already Exists' or 404 on cleanup | parallel BigQuery query-source runs | Two DTMs created the temporary view in the same millisecond | Retry once after ~20 s (L-CDI-205) |
| `5001` GCS staging, with 409/404 | parallel BigQuery runs | Transient | Serial retry; check the target first, because data may have landed (L-CDI-130) |
| "Cannot propagate link rule of type TmplPatternRuleImpl between Expression and IUpdateStrategyNode5" | first run after an org move | Different bundle-template build | Rerun once (L-CDI-005) |
| "DTM process terminated unexpectedly" in ~2 s, 0 rows | run | A connector is missing on the runtime environment, or the warehouse is throttled (`APP_13400`) | Colocate connectors; fix capacity (L-CDI-044, L-CDI-045) |
| `REPO_52013` | delete MTT | Bound to a schedule | Unbind deliberately, or keep the task (L-CDI-053) |
| `APP_13500` | create MTT | Parentheses in the task name | Letters, digits, spaces, hyphens (L-CDI-280) |
| `403 REPO_19001` "An error occurred while saving the Mapping task to the repository." | create/update MTT | A long SQL default (about 4,000+ characters) on an in-out parameter | A per-task parameter file (§2; L-CDI-285) |
| 200, but the run still executes the old query | update `$Source$.customQuery` | The mapping's source query is fixed | Make it an in-out parameter (§2; L-CDI-284) |

## 11. Delete

- `DELETE /api/v2/mttask/<id>` → 200. Read it back: a **403 means gone**. Resolve the v2 id from a v3 id through `frsGuid`, never by name (L-CDI-052).
- Mappings: `DELETE /api/v2/mapping/<id>` → 200, only when the mapping's `tasks[]` is empty. Resolve it through `assetFrsGuid`. `/api/v2/dtemplate/<id>` is the wrong path (404 HTML), and a v3 objects DELETE returned 404.
- Delete tasks before their mappings, and schedules before or with the tasks bound to them. Take an export backup first and never delete while an import is running ([knowledge/10-migration-org-management](../10-migration-org-management/)).
- Before deleting a task that looks orphaned, check its task-level schedule, app readers of its output and orchestrator id lists (L-CDI-146).
