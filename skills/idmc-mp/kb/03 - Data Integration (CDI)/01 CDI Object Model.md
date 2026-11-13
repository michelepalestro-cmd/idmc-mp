# CDI Object Model

**Answers:** What a mapping, mapping task, linear and advanced taskflow and schedule are; which object owns connections, fields, write options and schedules; how v2 ids and v3/FRS GUIDs map to each other; where objects live in FRS; how to inventory an org read-only.

**Read when:** before any CDI build, inventory or cleanup; when an id from one plane does not resolve on another; when a change to a task does not seem to take.

**Key rules:**
- Tasks over Copy Data bundle templates own their connections and objects; tasks over ordinary mappings do not, so retarget the mapping, not the task (L-CDI-003, L-CDI-007, L-CDI-050).
- The v2 task list hides `frsGuid` and `scheduleId`: read every task's detail before concluding anything (L-CDI-008, L-CDI-077).
- Address objects by id, never by name; resolve v2 ↔ v3 ids with `frsGuid`, `assetFrsGuid` or a v3 lookup by path (L-CDI-009, L-CDI-010).
- New v2 objects are born in `Default`; move them with FRS `MoveEntities` (at most 25 per call) and tag them in batches of 50 (L-CDI-016, L-CDI-054).
- The v3 type filter is not validated: an unknown type returns 0 objects, not an error (L-CDI-011).

**Related:** [02 How Claude Builds Mappings Headless](02%20How%20Claude%20Builds%20Mappings%20Headless.md) · [03 Mapping Tasks - Create, Update, Run, Monitor](03%20Mapping%20Tasks%20-%20Create,%20Update,%20Run,%20Monitor.md) · [04 Taskflows & Schedules](04%20Taskflows%20&%20Schedules.md) · [10 - Migration & Org Management](../10%20-%20Migration%20&%20Org%20Management/) · [Lessons: CDI](../13%20-%20Lessons%20Learned/03%20Data%20Integration%20(CDI).md)

**Last verified:** 2026-11-03

> **Summary.** CDI work is a chain of four kinds of objects: a **mapping** (the design; v3 type `DTEMPLATE`), a **mapping task** (MTT, the runnable instance with its parameters), a **taskflow** (linear v2 "workflow", or advanced Process-Designer `TASKFLOW`) and a **schedule**.
> Informatica's Add-On Bundle Copy Data templates (e.g. `dsst__copy_data_new_tgt`) are parameterized mappings: a task over one brings its own connections and objects, or a `customQuery`. Ordinary mappings are fixed to their connections and schema.
> The v2 plane (20-character ids) and the v3/FRS plane (22-character GUIDs) see these objects differently. The v2 list calls hide `frsGuid` and `scheduleId`, so read the details. Schedules can be bound at workflow level or task level.
> Every object has a place in the FRS repository (Explore). New v2 objects are born in `Default`, and moves are headless through FRS.

---

## 1. The chain

```
 connection(s) ──▶ MAPPING ──────────────▶ MAPPING TASK (MTT) ──▶ LINEAR TASKFLOW (v2 workflow) ──▶ SCHEDULE
 (org level)      v3 DTEMPLATE             v2 /api/v2/mttask       v2 /api/v2/workflow             v2 /api/v2/schedule
                  (documentType MAPPING)   v3 MTT, FRS doc MCT      v3 WORKFLOW                     (org level)
                  bundle template, or      mappingId -> mapping     ordered task list                bound on the workflow
                  real mapping             $Source$/$Target$ params                                   OR on the task itself
                                                                   └▶ ADVANCED TASKFLOW (v3 TASKFLOW, Process Designer XML)
```

| Object | v2 route | v3 / FRS | What it is | Headless create |
|---|---|---|---|---|
| Mapping | `/api/v2/mapping` (read, delete) | `DTEMPLATE`; inner `documentType:"MAPPING"`. Some listings also show a `MAPPING` type | The transformation design: sources, transformations, targets, field arrays, connection bindings | **Not** via REST create (`POST /api/v2/mapping` 400; L-CDI-020). By import package (L-CDI-032, L-CDI-033) |
| Bundle transfer template | same | `DTEMPLATE` under `Add-On Bundles/Data Transfer Templates` | Informatica's parameterized Copy Data mappings | Ships with the org (system content) |
| Mapping task (MTT) | `/api/v2/mttask`, `/api/v2/mttask/<id>` | `MTT`; FRS document type `MCT` | A runnable instance of one mapping (`mappingId`) with its parameters, runtime environment and optional schedule | `POST /api/v2/mttask` (L-CDI-022, L-CDI-037) |
| Synchronization task | `/api/v2/dss` (mounts per pod and engine) | `DSS` | Classic source-to-target task with its own field mapping and no separate mapping object | Documented; not used or tested in this program (L-CDI-015) |
| Linear taskflow | `/api/v2/workflow` | `WORKFLOW` | An ordered list of tasks, each with `stopOnError`/`stopOnWarning`; can carry `scheduleId`; **no publish step** | `POST /api/v2/workflow` (L-CDI-069) |
| Advanced taskflow | `/api/v2/taskflow` (read) | `TASKFLOW` (Process Designer XML) | Parallel paths, decisions, Data Task steps; run through a published REST/SOAP endpoint | Import works; **publish** of API-made ones fails (L-CDI-070) |
| Schedule | `/api/v2/schedule` | org-level, no folder | A cadence object bound through `scheduleId` | `POST /api/v2/schedule` (L-CDI-073) |
| Connection, runtime environment, agent | `/api/v2/connection`, `/runtimeEnvironment`, `/agent` | org-level (`/SYS` in export metadata; runtime environment = `AgentGroup`) | What a task runs on and reads/writes through | See [02 - Secure Agent & Connections](../02%20-%20Secure%20Agent%20&%20Connections/) |

A fresh org already holds about 160 stock design assets (e.g. MAPPLET 48, DTEMPLATE 44, DMAPPLET 20, CLEANSE 18, DICTIONARY 15, PARSE 7). They are templates, not user work: count real tasks with `GET /api/v2/mttask` (L-CDI-002, 2026-06-29).

## 2. Mapping, mapping task, template: who owns what

| Concern | Lives in the **mapping** | Lives in the **task** |
|---|---|---|
| Transformations and links | yes | — |
| Field arrays (names, types, precision, `notNull`) | yes. A task has **no** field array; `overriddenFields` over v2 returns 400 (L-CDI-006) | — |
| Connection binding | yes for ordinary mappings (`fixedConnection:true`, `connectionParameterized:false`) | yes for **parameterized** templates (`$Source$.sourceConnectionId`, `$Target$.targetConnectionId`) |
| Source and target objects | ordinary mappings: fixed (`objectParameterized:false`) | templates: `sourceObject`, `extendedObject`, `targetObject`… |
| `customQuery` | query sources in the mapping IMF | templates: `$Source$.customQuery` |
| Write disposition (BigQuery) | adapter `oprRuntimeAttributes` (L-CDI-038) | templates: `$Target$.oprRuntimeAttrs` (L-CDI-048) |
| Runtime environment, session properties, schedule | — | `runtimeEnvironmentId`, `agentId`, `sessionProperties`, `optimizationPlan`, `scheduleId` |

Consequences:
- On a task over an **ordinary** mapping, changing the connection gives an invalid task (2026-09-22). A task-level `sourceConnectionId` does not propagate into the mapping, and a target-parameter POST returns 200 but the task keeps the mapping's targets (L-CDI-007, L-CDI-050). Change the mapping instead: re-import it OVERWRITE under the same GUID.
- Check a mapping's real binding in its export, not its name. "Twin" mappings named for one warehouse were bound to another (L-CDI-007).

**The Copy Data bundle templates** (L-CDI-003, 2026-09-23): `dsst__copy_data_new_tgt` (creates the target if missing), `dsst__copy_data_existing_tgt`, `dsst__copy_with_lookup_*`, `dlt__copy_data` (Data Loader, with incremental-key filter parameters) and `INFA_Generic_Cloud_Service_Mapping`. Their `$Source$` is `EXTENDED_SOURCE` and their `$Target$` is `TARGET`, both with `fixedConnection=false` and `connParam=true`. In-out parameters include `$p_filter_src$`, `$p_tgt_excluded_fields$` and `$p_exp_fields$`. They are **system content**: FRS reports `delete:false`, a v3 export can return `403 MigrationSvc_038` for a non-admin user (it varied by org and date), and an org-to-org import with REUSE binds tasks to the **target's own** copy, which can be a different build (L-CDI-004, L-CDI-005).

## 3. `customQuery`

- `$Source$.customQuery` holds a whole SELECT that the **source connection** executes. The source object is then a dummy name (`DUMMY_Source`), and the canvas shows two boxes.
- Its dialect is the source connection's, whatever the target is: GoogleSQL on BigQuery. T-SQL against a BigQuery source fails with BigQuery `400 Unexpected "[" … escape with backtick` (L-CDI-023).
- Non-ASCII characters, in practice from SQL comments, fail the BigQuery reader with `IOException: missing CR`. Store cleaned SQL (L-CDI-024).
- On the BigQuery connection set `useLegacySQLForCustomQuery=false`.
- All logic in `customQuery` runs **inside the warehouse** (ELT) even with pushdown off. It is also invisible to lineage below table level and to CLAIRE (L-CDI-115).
- A task's `$Source$.customQuery` takes effect only when the mapping's source query is a parameter, as on the Copy Data templates. On a mapping whose source query is fixed, the task's copy can be edited without an error, but the run executes the mapping's own query. For one mapping over many sources, make the query an in-out parameter (`$$SRC_SQL`) used as the Source query, and vary it per run; SQL longer than about 4,000 characters goes in a parameter file ([03](03%20Mapping%20Tasks%20-%20Create,%20Update,%20Run,%20Monitor.md) §2; L-CDI-284, L-CDI-285, 2026-11-01).

## 4. Linear vs advanced taskflows

| | Linear taskflow (v2 `workflow`) | Advanced taskflow (v3 `TASKFLOW`) |
|---|---|---|
| Structure | Ordered `tasks[]` of `{"@type":"workflowTask","taskId","type":"MTT","name","stopOnError","stopOnWarning"}` | Process Designer XML: `parallel` containers, Data Task steps (`ICSExecuteDataTask`), decisions |
| Create / update | `POST /api/v2/workflow`, `POST /api/v2/workflow/<wfId>` | Generated XML imports (OVERWRITE) |
| Publish | Not needed | Needed for its REST/SOAP run URL. **Fails** for API-created or FRS-copied taskflows (`AvrEntryNotFoundFault`, "File format was not recognized"; L-CDI-070, 2026-09-25) |
| Run | `POST /api/v2/job {"taskId":"<wfId>","taskType":"WORKFLOW"}` | Its published endpoint. `POST /api/v2/job` rejected taskflows with `403 UI_13430` (July; L-CDI-071) |
| Monitoring | Children appear as `entries[]` of the workflow's activity-log row (L-CDI-061) | Process monitoring |
| Concurrency | One task at a time. Parallelism means several taskflows or an external controller | Parallel paths |
| Overlap | Two linear taskflows that share tasks cannot overlap (`REPO_17314`; L-CDI-078) | — |

## 5. Schedules: workflow level vs task level

- A schedule is bound by setting `scheduleId` on a **workflow** (`POST /api/v2/workflow/<wfId>`) or directly on a **mapping task** (`POST /api/v2/mttask/<id>`). `scheduleId: null` unbinds (L-CDI-075).
- The v2 MTT **list** does not return `scheduleId`, so task-level bindings are invisible there. Only each task's detail GET shows them. A cutover that scanned only workflows missed one task-level schedule, which kept running in the old org (L-CDI-008, L-CDI-077).
- Deleting a task that still has a schedule bound fails with `REPO_52013`, which also proves the task is live (L-CDI-053).
- Schedules are organization-level objects: they live in no folder. Find them by name prefix.

## 6. v2 vs v3 visibility

**Two id shapes.**
- **v2 id** (20 characters) = `<orgIdV2>` (6) + a 2-character type code + a 12-character sequence. Observed type codes (L-CDI-018, 2026-09-29): `0Z` mapping task, `0N` workflow, `D0` schedule, `17` mapping, `0B` connection, `08` agent, `25` runtime environment.
- **v3/FRS GUID** (22 characters, base-62): the `id` in `GET /public/core/v3/objects`, the `frsGuid` on an MTT detail, and the `assetFrsGuid` on a v2 mapping.

**What each call shows.**

| Call | Shows | Hides |
|---|---|---|
| `GET /api/v2/mttask`, `GET /api/v2/task?type=MTT` | names, v2 ids, `runtimeEnvironmentId` (use it for per-runtime inventory; L-CDI-013) | `frsGuid`, `scheduleId` (L-CDI-008) |
| `GET /api/v2/mttask/<id>` | full body: `parameters[]`, `mappingId`, `frsGuid`, `scheduleId`, `runtimeEnvironmentId`, `agentId`, `sessionProperties` | — |
| `GET /api/v2/workflow/<wfId>` | `tasks[]`, `scheduleId` | **no** `frsGuid` |
| `GET /api/v2/mapping` | v2 mapping ids, names, `assetFrsGuid`, `tasks[]` using it | — |
| `GET /public/core/v3/objects?limit=200&skip=N` | `id`, `path` (`<project>/<folder>/<name>`), `type`, per page until `count` | v2 ids, runtime environment |
| `GET /api/v2/task?type=<X>` | tasks of one type | `MI_TASK` and `DVT` give 403 ("not a valid task type"; L-CDI-014) |
| `GET https://<pod>.<domain>.informaticacloud.com/batch-mapping/api/v1/dynamictask/<v3 id>` (no `/saas`) | a Dynamic Mapping Task: name, `mappingId`, `runtimeEnvironmentId`, `scheduleId`, state, `groups[]` {groupName, enabled}, `parameters[]` (for example `Source:p_src_conn`, type SOURCE_CONNECTION) and the jobs (L-CDI-289, 2026-11-01) | under `/saas` the path answers 404 HTML; an unknown id 500 CMN_001 |

**Resolving ids (L-CDI-009, 2026-09-25).**
- MTT v2 → v3: `frsGuid` from the detail GET.
- Workflow v2 → v3: list v3 `type=='WORKFLOW'` objects and match the last path segment to the name. Require exactly one match.
- Mapping v2 → v3: `assetFrsGuid`.
- By path: `POST /public/core/v3/lookup {"objects":[{"path":"<project>/<folder>/<name>","type":"MTT"}]}`.
- Starting a job by `taskFederatedId` needs the task's own federated id in the same org. The v2 `taskId` always works (L-CDI-057).
- **Address objects by id, never by name.** Unrelated folders can hold the same names (L-CDI-010).

**Traps.**
- The v3 `q` type filter is **not validated**. An unknown type (`type=='DBMI'` instead of `'DBMI_TASK'`) returns 0 objects, not an error. Sweep candidate type names, or list unfiltered and group client-side (L-CDI-011, 2026-09-25).
- The v3 list does return v2-created MTTs under `type=='MTT'` (160 in one audit). A sweep that finds none is a filter or paging artifact: cross-check with `/api/v2/task?type=MTT` before concluding anything (L-CDI-012).
- The v2 task resources (`/api/v2/dss`, `dtemplate`, `dmask`, `dreplicate`, `plan`, `fileListener`) mount **per pod and per licensed engine**: 200 on one org, 404 on another. Never generalize a v2 inventory from one org (L-CDI-015).
- Job-history totals can be dominated by old runs of deleted objects (930 of 1,000 rows once). Filter by object and date (L-CDI-019).
- The activity log is not complete history: a full read of a busy project's log returned 1,076 entries reaching back three weeks, against more than 500 jobs a day, and each task carries `maxLogs: 10`. Counts read from it are lower bounds; keep your own run ledger (L-CDI-288, 2026-11-01).
- A v3 query for type `DMAPPINGTASK` or `DMT` returns count 0, like an invented type: Dynamic Mapping Tasks are v3 type `BATCH_MAPPING`, and their sub-jobs log as type MAPPING (L-CDI-289).

## 7. Where each object lives in FRS

| Object | Location | How it gets there |
|---|---|---|
| Your mappings, tasks, taskflows | Explore `<project>/<folder>/<name>` | New v2 MTTs and workflows are created in **`Default`**. Move them with FRS `MoveEntities`; v2 id, `mappingId`, schedule bindings and run history survive the move (L-CDI-016) |
| Bundle templates | `Add-On Bundles/Data Transfer Templates` | System content (`delete:false`) |
| Connections, runtime environments, agents, schedules | Organization level (export metadata path `/SYS`) | Identify them by name prefix or description |
| Projects and folders | v3 `PROJECT` / `FOLDER` objects | `POST /public/core/v3/projects {"name","description"}`, `POST /public/core/v3/projects/<projectId>/folders {"name","description"}`. Cache ids per org (L-CDI-055). They cannot be tagged; the project name is the marker (L-CDI-054) |

**FRS repository calls** (the ones the Explore UI makes):
- Base: `https://<pod>.<domain>.informaticacloud.com/frs/api/v1/...` or `/frs/v1/...` (both worked). Header `IDS-SESSION-ID: <v2 icSessionId>`; `INFA-SESSION-ID` returns the login HTML page. `$metadata` needs `Accept: */*`.
- `POST .../MoveEntities` and `.../CopyEntities`: body `{"xferSpec":{"targetLocationId":"<folder frsGuid>","sourceSpecArr":[{"sourceEntityId":"<frsGuid>","mergeTags":""}]}}`. The answer is `value[].statusArr[].resultValue == "FRS_200"` per object, or `XFER_200` "Operation succeeded on N artifacts". For a copy, name and describe it in the same item (`destName`, `destDesc`, `resetExpiryTime: false`), leave `conflictResolution` out (`"NONE"` fails with `XFER_500` 'Unknown conflict resolution policy') and take the copy's id from `value[].statusArr[].tgtGuid`; a mapping copy has no task, so it adds nothing to lineage (L-MIG-087, 2026-11-02). Send at most 25 ids per call. v3 `/objects/{id}/move` is 404.
- Deletes and dependency checks (`DeleteEntities`, `DELETE .../BaseEntities('<id>')`, `GetInboundDocRefs`, `GetAllDependencies`): see [10 - Migration & Org Management](../10%20-%20Migration%20&%20Org%20Management/).

**Export package names** (see [02](02%20How%20Claude%20Builds%20Mappings%20Headless.md) §5): mapping `Explore/<project>/<folder>/<name>.DTEMPLATE.zip`; an exported mapping task carries an `mtTask.json`; advanced taskflow `…/<name>.TASKFLOW.xml`; plus `exportMetadata.v2.json` and `exportPackage.chksum`.

## 8. Inventory recipe (read-only)

1. Page `GET /public/core/v3/objects?limit=200&skip=N` until `count`, then group by `type` and path prefix on the client.
2. `GET /api/v2/task?type=MTT` and `GET /api/v2/workflow`, then **every detail** (`/api/v2/mttask/<id>`, `/api/v2/workflow/<wfId>`) for `mappingId`, `scheduleId`, `frsGuid` and the parameters.
3. Classify each MTT by its `mappingId`: bundle template (a copy-data task, logic in `customQuery`) or a real mapping. Note its source and target objects.
4. Dependencies: `GET /public/core/v3/objects/<id>/references?refType=uses|usedBy&limit=50&skip=N`.
5. Before calling anything unused, check task-level schedules, app readers of its output and orchestrator id lists (L-CDI-146).

## 9. Glossary of terms used in this folder

| Term | Meaning |
|---|---|
| `DTEMPLATE` | The v3 object type and package suffix of a CDI mapping (`<name>.DTEMPLATE.zip`). Its inner `documentType` is `MAPPING` |
| IMF | The JSON mapping model inside an export's `bin/@N.bin`: a `Template` with `transformations[]`, `links[]` and `metadata.$$classInfo` |
| MTT / `MCT` | A mapping task. The v3 type is `MTT`; FRS and advanced-taskflow steps call it `MCT` |
| `$Source$` / `$Target$` | The source (`EXTENDED_SOURCE`) and target (`TARGET`) parameters of a task over a parameterized template |
| `customQuery` | A whole SELECT that the source connection executes; the task's source object is then a dummy name |
| RunAJob | `POST /api/v2/job`, the one headless way to start a task or a linear taskflow |
| DTM / `pmdtm` | The Data Transformation Manager process the agent starts per task session. It accounts for about 14 s of each task's fixed cost. Its Java heap is one agent-wide setting (`JVMOption1`, type DTM), and the DIS runs at most `maxDTMProcesses` DTMs at once (2 by default; [07](07%20Performance,%20Concurrency%20&%20Job%20Caps.md) §6) |
| DIS | The Data Integration Server service on the Secure Agent, which runs DTM sessions and writes `s_mtt_<taskId>_<n>.log` |
| Linear taskflow | The v2 `workflow`: an ordered task list with no publish step |
| Dynamic Mapping Task (DMT) | One parameterized object over one mapping that runs one job per group (for example per table); v3 type `BATCH_MAPPING`, read at `/batch-mapping/api/v1/dynamictask/<id>` on the pod host and created headless by v3 package import (L-CDI-289) |
| Advanced mode | A mapping that runs on Spark (an advanced configuration; a Local one runs on the agent). It exports as an `AtScaleDTemplate` document (`AT_SCALE_MAPPING`, annotation `mapping_type = CDIE`) (L-CDI-276, L-AGENT-114) |
| Advanced taskflow | The v3 `TASKFLOW`: Process Designer XML with parallel paths, run from its published endpoint |
| Bulk / Streaming | BigQuery V2 write modes. Only Bulk can truncate, and it needs GCS staging |
| Write truncate / Write append | BigQuery write dispositions, set in `oprRuntimeAttrs` (task) or `oprRuntimeAttributes` (mapping adapter) |
| `fetchMode: "RUNTIME"` | Read source and target field metadata at run time instead of keeping the creation-time field list |
| `frsGuid` / `assetFrsGuid` | The v3/FRS ids of a mapping task and of a mapping, as exposed on their v2 detail objects |
| Lane | A subset of a pipeline's tasks that runs together with its own trigger (full, per-record, events, files) |
| Shadow mode / parity dataset | Building and running the chain against twin datasets so that results can be compared before anything live changes |
| Swap gate | The gated sequence that replaces tasks with new mappings: tests green, swap in place, plan switch, re-test, delete ([08](08%20Changing%20Pipelines%20Safely.md)) |
| Job | One task run or one taskflow run, counted against the org's monthly job cap ([07](07%20Performance,%20Concurrency%20&%20Job%20Caps.md)). CAI process calls and running CDC jobs are not jobs |
| Full SQL ELT (pushdown) | A mapping-task mode in which the whole mapping runs as warehouse SQL; set on the v2 task and proven only by `OPT_63367` in the session log ([02](02%20How%20Claude%20Builds%20Mappings%20Headless.md) §9) |
| Session log | The engine's run log of one task run; on the agent as `s_mtt_<taskId>_<n>.log`, and over REST at `GET /api/v2/activity/activityLog/<entryId>/sessionLog` ([03](03%20Mapping%20Tasks%20-%20Create,%20Update,%20Run,%20Monitor.md) §9) |

## 10. Overturned beliefs (latest evidence wins)

| Earlier belief | Overturned by |
|---|---|
| One mapping must be authored in the UI before anything can run headless (to 2026-09-22; L-CDI-174) | Tasks over the parameterized bundle templates, 2026-09-23 (L-CDI-003) |
| v2-created MTTs do not surface in a v3 `type=='MTT'` scan (2026-09-23; L-CDI-175) | The v3 list returned all of them, 2026-09-25/29 (L-CDI-012) |
| The v2 task resources exist on every pod (July; L-CDI-176) | They mount per pod and per licensed engine, 2026-07-26 (L-CDI-015) |
| Moving an asset between projects is a UI Explore action (2026-08-19; L-CDI-177) | FRS `MoveEntities` headless, 2026-09-24/29 (L-CDI-016) |
