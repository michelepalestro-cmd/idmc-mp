# Database ingestion and CDC (DBMI): cheat sheet

Land a database in the user's target with an initial load plus continuous change data capture through a Database
Ingestion (DBMI) task, and create, deploy, start, stop, change and monitor it headless.

**Start with:** `toolkit/lib/idmc_dbmi.py` (`list`, `details`, `status`, `create --spec`, `deploy`, `start`, `stop`,
`resume`, `undeploy`, `delete`) and open [01 DBMI over REST](01-dbmi-over-rest-create-deploy-run-stop.md) first; for
a PostgreSQL source, [02 CDC from PostgreSQL](02-cdc-from-postgresql.md) §1 before anything else.

> The tool's writes are dry runs until `--execute --expect-org <orgIdV3>`. DBMI ids are numeric; the 22-character
> `frsId` is only for FRS move, delete, tags and export (L-DBMI-006).

## What works (headless)

| Task | How (exact route / tool / command) | Lesson |
|---|---|---|
| Reach DBMI | `https://<pod>-ing.<domain>.informaticacloud.com/dbmi/public/api/v2/...`, header `IDS-SESSION-ID: <v2 session>` (send `INFA-SESSION-ID` and `icSessionId` with the same value) | L-DBMI-001 |
| Create a task | `POST /dbmi/public/api/v2/task/create` with the task JSON → `{taskId, frsId}`; tool `create --spec task.json` | L-DBMI-003, L-DBMI-004 |
| Get a complete body to clone | `GET /dbmi/public/api/v2/task/details?taskId=<n>` → `documents[].dbmiTask`; tool `details --save` | L-DBMI-007 |
| Deploy | `POST /dbmi/public/api/v2/task/deploy/<taskId>` with `{}` → `data.jobId`; every deploy = a new job id | L-DBMI-003, L-DBMI-009 |
| Start / stop / resume / undeploy | `POST /dbmi/public/api/v2/job/start` (`stop`, `resume`, `undeploy`) with `{"jobId": <n>}` | L-DBMI-003 |
| Read status | `GET /dbmi/api/v1/task/<taskId>/job` → `status`, `runId` (= job id) | L-DBMI-003 |
| Per-table state | task log on the agent: every table's latest transition event is `NORMAL_CONTINUOUS_CDC_TABLE` | L-DBMI-030 |
| Pause without a re-baseline | `job/stop`, then `job/resume`: continues from the stored restart point | L-DBMI-056 |
| Place it in a folder | create in the project (`general.location`), then FRS `MoveEntities` by `frsId` | L-DBMI-005 |
| Delete | stop, undeploy, then `DELETE https://<pod>.<domain>.informaticacloud.com/frs/api/v1/BaseEntities('<frsId>')` → 204 | L-DBMI-007 |
| Hand a slot to another org's task | stop (not undeploy) the old job, start the new one on the same slot; rollback = stop new, resume old | L-DBMI-020 |
| File Ingestion (files to an agent folder) | `POST .../mftsaas/api/v1/mitasks`, then `POST .../mftsaas/api/v1/job`, poll `job/<runId>/status` | L-DBMI-060, L-DBMI-061 |

## What doesn't work, and the workaround

| Wall | Workaround | Lesson |
|---|---|---|
| DBMI paths on the pod `/saas` host give 404 (read as "not licensed") | use the `-ing` host; entitlement = `Database_Ingestion` and `MassIngestionRuntime` RUNNING plus privileges | L-DBMI-001, L-DBMI-041 |
| `POST /api/v2/job` with a DBMI id → `403 UI_13404`; `/api/v2/mttask/<id>` → `REPO_19035` | DBMI tasks are not v2 tasks: `-ing` job routes | L-DBMI-010 |
| No update verb | A: stop + undeploy, export, edit `.DBMI_TASK.dat`, re-hash, import OVERWRITE; B: create a new task, delete the old one | L-DBMI-007 |
| `general.location` as a folder path is rejected | a project name, then FRS move | L-DBMI-005 |
| Datatype rules on a BigQuery target: no effect, and a half-applied one killed a job | `dataTypeRules: []`; repair types in views | L-DBMI-023 |
| Microsoft Fabric DW as a DBMI target (July 2026: `No enum constant ... FABRIC`) | CDI mapping tasks or land files; re-check the vendor list | L-DBMI-039 |
| Importing an UNLOAD task to an agent with no DBMI engine → `403 FORBIDDEN` vendor validation | enable the engine first, or create the task later with `task/create` | L-DBMI-032 |
| JDBC V2 as a DBMI source or target | the native connector (JDBC V2 is a CDI path) | doc 03 §1 |

## Fastest safe path

1. **Prove the org and the engine:** `check_login.py`, then `GET /api/v2/agent/details/<agentId>` shows
   `Database_Ingestion` and `MassIngestionRuntime` RUNNING (L-DBMI-041).
2. **Source prerequisites (PostgreSQL):** `wal_level=logical`, a `LOGIN REPLICATION` role, USAGE and CREATE on the
   schema, a dedicated `FOR TABLE` publication (no `FOR ALL TABLES` anywhere), `REPLICA IDENTITY FULL`,
   `max_slot_wal_keep_size`, and the slot created last. Read-back: the check queries in doc 02 §1 (L-DBMI-011, L-DBMI-012).
3. **Target prerequisites (BigQuery):** the proven Simba jar set on the agent plus an agent restart; a DBMI-only
   connection with a probed key form; write/list/delete on the GCS bucket; project-level metadata read
   (L-DBMI-033, L-DBMI-053, L-DBMI-034, L-DBMI-036, L-DBMI-054).
4. **Build the task JSON** from a working task's `details` or doc 01 §4.1 (`combined` + `CDC_COMBINED`, slot and
   publication in both places, `FlushPeriod` 5). Create: dry run, then `--execute --expect-org <orgIdV3>`.
   Read-back: `task/details?taskId=<n>`.
5. **Deploy.** Read-back: status `processing_deploy` → `deployed` (about 8 s).
6. **Start (not resume).** Read-back: status `running`; the task log shows every table `NORMAL_CONTINUOUS_CDC_TABLE`
   and no ` ERROR `, ` SEVERE ` or ` FATAL ` lines (L-DBMI-030).
7. **Prove:** target row counts, then a real change (not a no-op UPDATE) lands; about 25 s with `FlushPeriod` 5
   (L-DBMI-025, L-DBMI-018).
8. **Watch it:** job state, slot LSN lag, end-to-end freshness, bounded auto-resume, alerts on state change only
   (L-DBMI-028, L-DBMI-063).

## Top traps

- **Changes take about 85 s** → default `FlushPeriod` 60 s is the floor → 5 s; the last tables of a big task land
  15-20 s after the first → split hot and cold tasks (L-DBMI-018, L-DBMI-019).
- **Deploy `failed`, `Failed to load driver class com.simba.googlebigquery.jdbc.Driver`**, connection tests green →
  copy the Simba set and restart the agent; a newer download broke the GCS writer on large tables (L-DBMI-033, L-DBMI-053).
- **`[Simba] Invalid PKCS#8 data`** → key form differs per engine and pod → DBMI-only connection, probe the form (L-DBMI-034; the exact PEM form is disputed, L-DBMI-035).
- **`409 WRONG_ACTION_FOR_DEPLOYED_JOB` on resume** → the job never started → `job/start` (L-DBMI-008).
- **'Mass Ingestion service could not find active agents'** right after an agent restart → wait for the engines,
  retry once; do not recreate the task (L-DBMI-052).
- **Slot shows `active=f`** → normal between polling cycles → judge by LSN lag and job state; never drop a live slot;
  unused slots pin WAL and fill the disk (L-DBMI-016, L-DBMI-014, L-DBMI-064).
- **Two jobs on one slot or into one target** → double writes → one job per slot (L-DBMI-015).
- **Job down after an outage:** an agent reboot passes `awaiting_auto_restart` and recovers by itself (do not
  redeploy); a source-host hard stop leaves `PWX-36749` Not retriable until `job/resume` (L-DBMI-028, L-DBMI-063).
- **Imported task re-loads everything** → it keeps the source's slot and publication names, and a first start with
  `LATEST` re-runs the initial load (L-DBMI-021); any redeploy = new job id and a short gap (L-DBMI-009).
- **UNLOAD `VerifyValueException ... no columns`** → a character primary key → exclude it or add a numeric key (L-DBMI-038).
- **Resume fails `DBMIP_20004` 'more than one entry of type CYCLE_ENTRY'** → identical duplicate rows in
  `INFORMATICA_CDC_RECOVERY` → back up, dedupe that task's rows, resume (L-DBMI-058).
- **Counts and BI include odd tables** → `<table>_EXT` and `INFORMATICA_CDC_RECOVERY` live in the target dataset →
  exclude, never drop; each changed table bills at least 30 MiB per apply cycle (L-DBMI-050, L-DBMI-055).

## Go deeper

- [01 DBMI over REST](01-dbmi-over-rest-create-deploy-run-stop.md): hosts, headers, the lifecycle, task JSON, job states, changing and deleting tasks, error signatures, File Ingestion.
- [02 CDC from PostgreSQL](02-cdc-from-postgresql.md): source checklist, task settings, measured latency, slots, org handover, hot/cold split, data traps, the watchdog.
- [03 DBMI Targets & Drivers](03-dbmi-targets-drivers.md): target matrix, Simba jars, key forms, GCS staging, PostgreSQL target edge cases, BigQuery target conventions.
- [Lessons: Mass Ingestion & CDC](lessons.md)
