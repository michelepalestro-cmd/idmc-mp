# Cutover & Rollback

**Answers:** What are the cutover steps between two IDMC orgs, in order, and the rollback for each? How long is the
gap? What can still be rolled back, and when does that end? What happens after the cutover: soak, rotations, the
vendor case, the source org?

**Read when:** preparing the GO of an org-to-org cutover; a cutover step fails; deciding what to do with the source
org and what to ask the vendor afterwards.

**Key rules:**
- Write the rollback first, one command per step, and keep every step independently reversible (L-MIG-049).
- Never run both sides: schedules are bound in exactly one org, and exactly one CDC job consumes a slot (L-MIG-047,
  L-DBMI-015).
- Snapshot every binding once, task-level `scheduleId`s included, and scan both orgs for task-level schedules after
  the cutover (L-MIG-048).
- Rollback into the source needs its account under its monthly job cap; CDC rollback ends when the source job is
  undeployed or its slot dropped (L-MIG-049).
- The source org stays intact through the soak; delete there only what the owner names, after a per-object verdict
  (L-MIG-051, L-MIG-073).
- After the soak, send one batched vendor case with only what the vendor alone can fix, each item with its evidence
  (L-MIG-074).

**Related:** [Org-to-Org Migration Runbook](<04 Org-to-Org Migration Runbook.md>) · [CDC from PostgreSQL](<../04 - Mass Ingestion & CDC/02 CDC from PostgreSQL.md>) · [Headless Deletes & Org Cleanup](<06 Headless Deletes & Org Cleanup.md>) · [Entitlement, Licenses & Job Caps](<../11 - IPU, Metering & Licensing/03 Entitlement, Licenses & Job Caps.md>) · [Lessons: Migration & Org Management](<../13 - Lessons Learned/10 Migration & Org Management.md>)

**Last verified:** 2026-10-03

> A cutover between IDMC orgs is six small steps on an explicit GO (snapshot the source bindings, unbind the source
> schedules, flip the callers, switch CDC, bind the target schedules, verify), plus a seventh that scans for the
> task-level schedules a workflow-only unbind misses. Measured on a real run: 21 minutes from the first unbind to CDC
> streaming in the target, and about 70 s of CDC freshness lost at the switch. A schedule slot that falls between the
> source unbind and the target bind fires in neither org, so time the window between slots.

---

## 1. Principles

1. **Write the rollback first** (L-MIG-049): one command per step, in the cutover ticket, before the GO.
2. **Each step is independent**, so any one step can be rolled back without undoing the others.
3. **Never run both sides at once:** schedules are bound in exactly one org at a time, and exactly one CDC job consumes a slot (L-DBMI-015).
4. **The source stays intact** (objects, unbound schedules, stopped jobs, the agent) until the soak is over; delete only what the owner names (L-MIG-051).
5. **Read back after every write.** A v2 POST that returns 200 may not have changed anything; compare the field.
6. **One writer:** only the lead session logs in to either org during the cutover. Other lanes freeze their writes (no deletes and no imports in the target during the window).

## 2. Ready-for-GO checklist

| Item | Check |
|---|---|
| validation passed | parity, smoke and stories recorded (see the runbook's validation table) |
| target schedules exist, **unbound** | created with `POST /api/v2/schedule`; no workflow or task carries them yet |
| target CDC task deployed, **not started** | `GET.../dbmi/api/v1/task/<taskId>/job` → `deployed`; drivers and key proven by that deploy |
| id map complete | every caller id resolves; the flip tool's `plan` shows 0 unmapped ids |
| flip tool backups | the backup directory is writable; the `rollback --backup <ts>` path tested by design |
| CAI callers | already switched in their own step, or planned in the flip |
| rollback commands | written in the ticket, one per step |
| the source's job budget | under its monthly cap (a rollback needs it); the target's job ledger running ([Entitlement, Licenses & Job Caps](<../11 - IPU, Metering & Licensing/03 Entitlement, Licenses & Job Caps.md>) § 7.1) |
| peers | every lane acknowledged the freeze |

## 3. The sequence (L-MIG-047)

### Step 1: snapshot the source bindings (the rollback baseline, written once)

For every workflow in scope, `GET /api/v2/workflow/<wfId>` and save `{name: {id, scheduleId, schedule name, endTimeUTC, full body}}` to a timestamped JSON file. Also save every mapping task's detail with a non-null `scheduleId` (the list call hides it; L-MIG-048). Write the file once and never overwrite it.

### Step 2: unbind the source schedules

```python
def set_schedule(call, wf_id, schedule_id):         # schedule_id=None unbinds
    st, w = call("GET", f"/api/v2/workflow/{wf_id}")
    body = {k: v for k, v in w.items if k not in ("createTime", "updateTime", "createdBy", "updatedBy")}
    body["scheduleId"] = schedule_id
    st2, r = call("POST", f"/api/v2/workflow/{wf_id}", body)
    st3, after = call("GET", f"/api/v2/workflow/{wf_id}")
    assert st2 == 200 and after.get("scheduleId") == schedule_id, (st2, after.get("scheduleId"))
```

- This is the v2 update idiom: POST the full GET body back to the id. It worked on both pods tested.
- Unbinding leaves the schedule object itself untouched, which is the simplest way to stop a lane. Disabling a schedule through v3 (`PATCH /public/core/v3/schedule/<id>` with `{"status":"disabled"}`) returned 400 `V3API_007`.
- To stop a schedule by date instead, set **both** `endTime` (read in pod-local time) and `endTimeUTC`.
- Task-level bindings use the same idiom on `/api/v2/mttask/<taskId>`.

### Step 3: flip the callers

Apply the flip tool group by group (`apply --group <g> --execute`), each with its verify step: the controller's status shows the target org id, the agent is active, and its services are RUNNING. Rebuild container images first, then recreate each service at an idle moment, so a lane cannot start between the idle check and the swap. CAI base URLs are part of the flip, or a separate earlier step (L-MIG-040, L-MIG-042).

### Step 4: switch CDC (stop order matters)

1. `POST.../dbmi/public/api/v2/job/stop {"jobId":<source job>}` on the **source** `-ing` host. Wait for `stopped`. **Do not undeploy it: it is the rollback.**
2. `POST.../dbmi/public/api/v2/job/start {"jobId":<target job>}` on the **target** `-ing` host, on the same slot and publication (or on the new slot created a moment before step 1).
3. Watch: the slot has one consumer; the target task log has 0 errors; within a few minutes every table reaches continuous CDC; the source audit maximum equals the warehouse's.

The details and the measured gap are in [CDC from PostgreSQL](<../04 - Mass Ingestion & CDC/02 CDC from PostgreSQL.md>). If the target deploy or start fails, **resume the source job at once** and fix the target offline. That rollback cost about 5 minutes of freshness in the real run, because the target was missing a driver set.

### Step 5: bind the target schedules

The same `set_schedule` on the target workflows (and any task-level bindings), using the schedules created unbound beforehand. When you create a schedule, set **both** `startTime` (pod-local; one pod stamped local UTC-4 times with a `Z` suffix) and `startTimeUTC`; an hourly schedule needs the `mon`…`sun` flags set (see [Data Integration (CDI)](<../03 - Data Integration (CDI)/>)).

### Step 6: verify the first runs

Watch the first scheduled run of each bound schedule and the first event-driven runs in the target's activity log (use the `*Utc` time fields). Re-run the smoke suite and the stories.

### Step 7: scan for task-level schedules in both orgs

Read **every** task's detail GET for `scheduleId` in both orgs. At one cutover a task-level binding was missed by the workflow-only unbind and its task ran once more in the old org; it was found and moved about 40 minutes after the cutover finished (L-MIG-048). Deleting a task that still has its own schedule fails with `REPO_52013` (L-CLEAN-008).

## 4. Timeline of the executed cutover (minutes from the first unbind)

| T+ (min) | Step |
|---|---|
| 0 | snapshot and unbind of the source schedules (read back) |
| 1–2 | source CDC job stopped; the target deploy fails (the Simba driver set is missing) |
| 2 | callers flipped (controller and host tools); verify passed |
| 6 | source CDC job resumed while the host lane installs the driver set and restarts the agent (T+8 to T+10) |
| 10 | target schedules bound (read back) |
| 14 | the next target deploy fails on the key format; a DBMI-only warehouse connection and a new target task are created |
| 20–21 | source CDC job stopped again; the new target job started on the same slot |
| 22 | the first target CDC write (about 70 s after the stop) |
| 24 | all CDC tables in continuous CDC; one consumer, 0 errors |
| 31 | the first scheduled target run of the full lane |
| 38 | the MCP clients flipped |
| 60 | the missed task-level schedule moved to the target |

## 5. Measured downtime

| Surface | Gap | Why |
|---|---|---|
| batch lanes | none for the main lanes; a slot that falls between the unbind and the bind fires in neither org (inferred from the schedule times; an hourly lane's slot fell inside the 10-minute window) | the unbind and bind happened 10 minutes apart |
| CDC (first attempt) | about 5 minutes | the target deploy failed; the source job was resumed |
| CDC (switch) | about 70 s until the first target write; 3 min 13 s until all tables were continuous | the CDC_COMBINED re-baseline of 13 tables |
| CAI callers | 10–30 s per recreated service | a container recreate |
| staged controller lanes | none measured | recreated at an idle moment |

## 6. Rollback per step

| Step | Rollback | Limits |
|---|---|---|
| 2 source unbind | re-POST each workflow with the `scheduleId` from the step-1 snapshot (and the task-level ones) | the source account must exist and be under its monthly job cap |
| 3 caller flip | `rollback --backup <ts> --execute` for each backup set, **newest first**, then rebuild and recreate | a flip applied later on top of the same files needs its own rollback first |
| 4 CDC | stop the target job, then `job/resume` the source job on the same slot | only while the source job is stopped but still deployed, and its slot still exists |
| 5 target bind | re-POST the target workflows with `scheduleId: null` | none |
| new execution flags (for example staged lanes) | turn the flag off (an env switch plus a container recreate) | none |
| CAI callers | restore the env backup and recreate the services | the source processes must still be published |

Rollback into the source ends when you choose to end it: when the source CDC job is undeployed or its slot dropped (for example after the target splits its CDC onto new slots), CDC has **no way back**. Do that only after the soak, and say so in the report (L-MIG-049).

## 7. After the cutover

- **Soak:** watch the scheduled runs, the CDC watchdog and the job budget for a day.
- **Rotations** (L-MIG-050): rotate every exposed credential and update each touchpoint (helper creds files, service env files, catalog-scanner credentials, MCP OAuth clients that store the user's password); clear the lockout-guard block; verify with one login.
- **One batched vendor case** (L-MIG-074). Collect the post-cutover gaps that no headless or UI step can close
  and send them as one case, ordered by urgency:
  1. the real monthly job limit when the Licenses page shows no jobs row and every limit reads -1 (a trial edition; a
     comparable org stopped at exactly 10,000 jobs), with a request to raise it or move to a non-trial licence (see
     [Entitlement, Licenses & Job Caps](<../11 - IPU, Metering & Licensing/03 Entitlement, Licenses & Job Caps.md>) § 5);
  2. services that restart-loop for lack of a licence or setup (for example the Data Access Management agent and proxy
     exiting with code 133 after 'Initializing TMS and CMS configuration services'), with the licence-read evidence;
  3. CAI assets stuck with duplicate runtime rows ('singleton sequence... 2 items') or no runtime entry
     (`AvrEntryNotFoundFault`) that block deletes with `FRS_082` (L-CLEAN-012);
  4. reproducible product defects, each with a minimal repro;
  5. the engine and selection-list diff against the old org (L-IPU-053).
  Leave out other products' tenant issues (a BI tool's OAuth policy, SaaS-target storage), re-check every item the
  day you send it and drop those that resolved, and record the case number where the team tracks the work.
- **The source org:** keep it as it is unless the owner names deletions. A "ready to delete" checklist built from the id map is reference only (L-MIG-051). When the owner does approve deletions, give every source object one verdict from the id map and the import log first (READY, HOLD-VERIFY for objects the import reused, NO-TWIN, PROBE, DEP-LAST, SHARED; [Headless Deletes & Org Cleanup](<06 Headless Deletes & Org Cleanup.md>) § 12, L-MIG-073), diff every HOLD-VERIFY pair (the target copy may be older), and delete dependencies last.
- **The old agent:** stop it only after nothing depends on it. Check what really uses it before assuming; for example, check whether a demo feature still runs through it.
- **Clean the target** of legacy content only with explicit id lists (see [Headless Deletes & Org Cleanup](<06 Headless Deletes & Org Cleanup.md>)).

## 8. Creating the target schedules unbound (before the GO)

Create every schedule in the target ahead of time, idempotently by name, and bind nothing yet:

```json
POST /api/v2/schedule
{"@type":"schedule","name":"<name>","description":"<text>",
 "interval":"Hourly","frequency":4,"timeZoneId":"GMT",
 "startTime":"<first run in pod-local time, ISO, with the Z the pod expects>",
 "startTimeUTC":"<first run in UTC, ISO>",
 "weekDay":false,"dayOfMonth":0,
 "mon":true,"tue":true,"wed":true,"thu":true,"fri":true,"sat":true,"sun":true}
```

- On one pod the v2 plane reads `startTime` as local time (UTC-4) even though it carries a `Z`, so compute both fields from the same UTC instant.
- An hourly schedule without the weekday flags is rejected (`UI_10612`). A daily schedule takes its own flags.
- Copy interval, frequency and description from the source snapshot, and give the first run a time **after** the planned GO.
- Read the created schedule back and keep its id in the id map. Schedules do not travel in the package.
- Do not clone a schedule from another application's schedule in a builder script: when that schedule is deleted, the builder breaks.

## 9. Roles during the window

| Who | During the cutover |
|---|---|
| lead | the only session calling either org: snapshot, unbind, CDC stop and start, bind, verify |
| repoint lane | runs the flip tool group by group on the lead's word, then its verify; holds the rollback command |
| host lane | watches the slot, the task logs and the agent processes every 10 s; fixes drivers or restarts the agent if asked |
| cleanup lane | frozen: no deletes in the target during the window |
| QA lane | runs the smoke suite and the stories after the lead's "done" |

Announce the window on the epic, post a receipt with UTC times after each step, and post a final status with what runs where.

## 10. What the cutover report records

1. **Where everything runs now:** a table per surface (batch lanes, event lanes, CDC, CAI, controller and host tools, MCP clients, DQ, catalog), with before and after and the switch time.
2. **What was checked:** parity, the first scheduled runs, CDC consumer and audit parity, smoke, stories (with the failures classified).
3. **What still runs on the source and why** (for example a feature that has not moved yet), and what may be deleted there later.
4. **Rollback commands**, one per step, with their limits (section 6).
5. **Open items**, each with its owner, and the vendor case number (section 7).
6. **Credential rotation touchpoints:** every file, service, scanner and OAuth client that stores an exposed credential (L-MIG-050).
7. **New methods proven during the run**, dated, so they become lessons.
8. **Updates after the soak** (for example the CDC split or a retired rollback path), dated in the same report.

## 11. Lessons in this doc

L-MIG-040, L-MIG-042, L-MIG-047 to L-MIG-051, L-DBMI-015, L-DBMI-020, L-CLEAN-008, L-CLEAN-012, L-IPU-053, L-MIG-074, L-MIG-073. Full text: [Lessons: Migration & Org Management](<../13 - Lessons Learned/10 Migration & Org Management.md>) and [Lessons: Mass Ingestion & CDC](<../13 - Lessons Learned/04 Mass Ingestion & CDC.md>).
