# Performance, Concurrency & Job Caps

**Answers:** Why small CDI tasks are latency-bound; how linear, staged and consolidated lanes compare; how to stage a lane on its dependency DAG; which locks let event lanes run beside a full refresh; how the DTM pool limits concurrency and how to raise it; how the monthly job cap behaves and is budgeted; how to measure end-to-end latency per record before promising one.

**Read when:** before promising a latency, sizing concurrency, adding a lane or trigger, or when lanes slow down, queue or stop at the job cap.

**Key rules:**
- Every mapping task pays about 20 s of fixed cost; fewer tasks (consolidation) and concurrency are the levers, not bigger machines (L-CDI-121, L-CDI-119).
- The Data Integration Server runs only `maxDTMProcesses` DTMs at once (default 2): measure the queue before raising concurrency (L-AGENT-099).
- Block lanes on per-table conflicts, not one global run lock, so the critical event lane can run beside a full refresh (L-CDI-128).
- Every task run and every taskflow run is a job; CAI calls and running CDC jobs are not; at the cap later runs log as zero-row non-success (L-CDI-131, L-IPU-060, L-CAI-038).
- Retry a failed task once on transient signatures only, never on the job-cap error (L-CDI-132, L-CDI-205).
- Time each record with CDC change history plus warehouse time travel per publish, never with a truncate-load stamp (L-CDI-206).

**Related:** [02 How Claude Builds Mappings Headless](02-how-claude-builds-mappings-headless.md) · [06 Mapping Design & Consolidation](05-mapping-design-consolidation.md) · [10 Serving Outputs to BI and Apps](09-serving-outputs-to-bi-and-apps-freshness-latency-reverse-etl.md) · [knowledge/02-secure-agent](../02-secure-agent) · [knowledge/13-ipu-cost](../13-ipu-cost)

**Last verified:** 2026-11-03

> **Summary.** Small CDI tasks are latency-bound. Every mapping task pays about **20 s of fixed cost** (DTM start ~14 s + cloud dispatch ~5 s) before it moves a row, so a 62-task linear taskflow takes 21–24 min for about 53k rows.
> The levers are **fewer tasks** (consolidation) and **concurrency**, not bigger machines. Staging a lane on its read/write dependency DAG at concurrency 4 cut 21 min to about 5.5 min (estimated) and a 16-task lane from 462 s to 215 s (measured). The floor is the longest sequential chain.
> Cap concurrency near the host's vCPU count when agents share a small host, keep lanes that write the same tables mutually exclusive, and remember that **every task run and every taskflow run is a job**. One org hit a 10,000 jobs/month cap that no API shows.

---

## 1. The ~20 s floor per task

| Component | Time | Evidence |
|---|---|---|
| DTM session start on the agent | ~14 s | Agent session logs (`TM_6014` to the first reader activity), 2026-09-28 |
| Cloud dispatch (job start → agent pickup) | ~5 s | Activity log vs session log |
| Actual data movement for small tables | a few s | 8–60 s total per task observed |
| Wait for a free DTM slot (only when more sessions are submitted than the pool allows) | p50 13.9 s, p90 39.7 s, max 76 s with 4 parallel submits on the default pool of 2 | 'Submit job to thread pool queue' → 'DTM process started' in the DIS Tomcat log (§6.1; L-AGENT-099) |

- A linear taskflow's duration ≈ tasks × 20 s + data time. The 62-task lane measured 21.6 min in one org and 24.5 min in another (L-CDI-121, 2026-09-29).
- The uniform 20 s/task model matched the measured session timings closely enough to plan with ([§3](#3-the-dependency-dag)).
- Dispatch is normally about 5 s. One agent was seen starting REST-started jobs on a ~3-minute job-poll cadence (15 serial tasks ≈ 45 min; L-CDI-189, superseded by L-CDI-121): if dispatch looks like minutes, check the agent before tuning anything else.
- The activity log can lag the agent's own statistics. For a tight loop, also watch the target, or read the session log.

**Measured linear lanes** (one agent, one task at a time; L-CDI-122): 50 tasks in 15 min; 62 tasks in 19–24 min; a 16-task lane at a median of 4.6 min (max 5.5); a 19-task lane in about 6 min (max about 10). For sub-minute freshness use CDC instead: about 20 s median, p95 26 s, source to warehouse ([knowledge/06-cdc-ingestion](../06-cdc-ingestion)).

## 2. Linear vs DAG: the numbers

A DAG model of every lane (L-CDI-124, 2026-09-29). "Estimate" uses 20 s per task. "Measured-duration estimate" replays each task's measured session time + 5 s dispatch, greedy critical-path list scheduling.

| Lane (shape) | Tasks | Stages | Sequential est. | Conc. 4 est. | Conc. 8 est. | Measured-duration est. seq / c4 / c8 | Longest SaaS chain |
|---|---|---|---|---|---|---|---|
| Full batch (landing → raw → staging → gold → DQ → reverse-ETL → SaaS) | 62 | 15 | 20m40s | 5m20s | 5m00s | 22m25s / 5m41s / 5m41s | 11 |
| Per-record (sign-up → golden record → DQ → outbound) | 16 | 6 | 5m20s | 2m20s | 2m00s | 5m29s / 2m16s / 2m04s | 1 |
| Activity events (facts, marts, SaaS children) | 19 | 5 | 6m20s | 1m40s | 1m40s | 7m22s / 2m20s / 2m20s | 5 |
| Landing-only to a second warehouse | 17 | 1 | 5m40s | 1m40s | 1m00s | 3m29s / 0m58s / 0m30s | 0 |
| Small landing + gold | 8 | 2 | 2m40s | 0m40s | 0m40s | 3m34s / 1m09s / 1m09s | 0 |
| Feed with read-backs | 5 | 4 | 1m40s | 1m20s | 1m20s | 2m06s / 1m46s / 1m46s | 3 |
| File lane | 5 | 4 | 1m40s | 1m20s | 1m20s | 1m40s / 1m20s / 1m20s | 0 |
| Evidence snapshots | 3 | 2 | 1m00s | 0m40s | 0m40s | 0m56s / 0m42s / 0m42s | 0 |

What the table says:
- **Concurrency 8 barely beats 4.** The full lane's floor is an 11-task sequential SaaS chain (parent upsert → id read-back → child upsert …). Shorten the chain first, with external-ID relationship upserts instead of read-backs (L-CDI-118), then add concurrency.
- **Wide shallow lanes gain the most.** A 17-task landing-only lane has 1 stage: 3m29s → 0m58s at c4.
- **Actual staged runs** matched the estimates in direction (§4): 16 tasks 462 s → 215–279 s; 19 tasks 357 s → 240–267 s; a new record reached the golden table in 93 s instead of about 5 min (L-CDI-126).
- **After consolidation** the same lanes became 7, 11 and 23 jobs: per-record lane average 96 s (82-113 s), activity lane 145-159 s, full refresh 258-358 s; a 12-task linear taskflow ran 84 s ([06](05-mapping-design-consolidation.md) B5; L-CDI-119, L-CDI-206). Say which number you quote: the orchestrator's wall-clock and the IDMC task span of the same run differed by about 74 s on a full lane (the orchestrator's post-run steps).

## 3. The dependency DAG

Model (L-CDI-123, 2026-09-29):
1. **Reads** of a task: its source object (a PostgreSQL, SaaS or file object), or every `dataset.table` in its SQL, with warehouse views expanded to base tables through `INFORMATION_SCHEMA.VIEWS`. Reading a raw **view** means reading its landing table.
2. **Writes** of a task: its target.
3. For tasks *i < j* in the lane's current order, *j* depends on *i* on read-after-write, write-after-read or write-after-write of the same object.
4. **Deliberate chains stay ordered:** the SaaS parent → child sequence.
5. **External writers wait for everything before them.** A task that writes outside the warehouse (SaaS, reverse-ETL, postings) depends on **every** internal task before it, because its declared reads are incomplete.
6. **Unresolvable tasks are barriers:** everything before comes first, everything after waits.
7. Stage = longest-path level. Every dependency points earlier in lane order, so the order is a valid topological order and no deadlock is possible.

Validation: 0 unresolved tasks, and 0 dependency violations against the executor's own dependency function.

## 4. The staged fan-out executor

Instead of one linear taskflow, the controller starts every mapping task itself: still `POST /api/v2/job`, still executed **in IDMC**, as soon as its dependencies are done, at most N at once (L-CDI-125):

```python
order, deps = lane_deps(lane)            # section 3; lane order breaks ties
pending, running, finished, stop = list(order), {}, set, None
while pending or running:
    if stop is None:
        ready = [t for t in pending if deps[t] <= finished]
        for t in ready[:max(0, N - len(running))]:
            pending.remove(t); running[pool.submit(run_task, t)] = t   # run_task = POST /api/v2/job + activity-log poll
    if not running: break
    done, _ = wait(running, return_when=FIRST_COMPLETED)
    for f in done:
        t = running.pop(f); finished.add(t)
        if state[t] not in ("SUCCESS", "WARNING") and stop is None:
            stop = t                     # an error stops further starts; running tasks finish
for t in pending: state[t] = "NOT_RUN"   # never started because an earlier task failed
verdict = "SUCCESS" if all(state[t] == "SUCCESS" for t in order) else "FAILED"   # same verdict as the taskflow
```

- **Semantics match the linear taskflow.** A WARNING does not stop the lane, an error stops new starts, and never-started tasks are NOT_RUN.
- **Behind a flag with instant rollback.** Concurrency 0 restores the linear taskflow with no rebuild. Switch only when the controller reports it is idle, and **never mid-lane**.
- **Before staging the full lane**, add every missing declared read (4 landing reads through raw views were missing), keep it exclusive with its subset lanes, and unbind its IDMC schedule so the controller starts it inside the slot window (L-CDI-127).
- **Jobs:** a staged lane of N tasks costs N jobs; the linear taskflow cost N + 1 (§7).
- **One retry per task** for transient failures only (a BigQuery 503, a staging-file upload error, a `Temp_View` 409/404 collision, a 'does not exist' on an existing table), after about 20 s or at once for a core task; never for the monthly-limit error. Record the first error and a RETRYING state; the classifier is in [03](03-mapping-tasks-create-update-run-monitor.md) §9 (L-CDI-205).

## 5. Mutexes and triggers between lanes

| Rule | Why | Lesson |
|---|---|---|
| Per-table conflict locks instead of one global run lock: block only the same mapping task, two writes of one table, or a read of a table another run is writing | One global run lock made a new record wait behind a 20-minute full refresh (1,027 s to its golden record); with per-table locks record → golden stayed 76-88 s solo and beside a full refresh | L-CDI-128 |
| The critical (per-record) event lane may start as a guest beside any running lane, one guest per lane; other event lanes only beside the full refresh and only if allow-listed, otherwise they wait (the full lane refreshes their targets anyway) | New records must not queue behind a long lane | L-CDI-128 |
| Priority per-record > files > activity > full: a lower-priority run starts no task that a waiting higher-priority task conflicts with (bounded wait, e.g. 600 s), keeps at most concurrency − 2 tasks while a higher-priority run is active (1 while a per-record run is), under a global cap across all runs | The critical path owns the small agent | L-CDI-128 |
| Critical path first: inside the per-record lane nothing off the path to the golden table starts until it lands | Nothing competes with the governed record | L-CDI-128 |
| Soft-fail side tasks: a failed DQ side task alerts (the run ends FAILED) but does not stop activation, reverse-ETL or SaaS tasks | A DQ task's heap OOM had stopped the whole downstream tail | L-CDI-128 |
| SaaS reverse-ETL may read beside writers (every warehouse target load is one truncate-load job); the SaaS chain stays one at a time | Reads of a truncate-loaded table see a whole version | L-CDI-128 |
| A drain file: while it exists no run starts; recreate the controller only when idle, then a catch-up run replays queued events | No run is cut by a redeploy | L-CDI-128 |
| A blackout window (plus 30 min before it) blocks full refreshes; an optional extra run refreshes the marts just before | No heavy refresh during a critical window | L-CDI-128 |
| The controller, not IDMC schedules, owns every start | IDMC refuses a second taskflow that runs the same tasks (`REPO_17314`) | L-CDI-078, L-CDI-128 |
| Only while IDMC schedules start the full lane: keep subset lanes mutually exclusive with it and out of a quiet window (e.g. 7 min before to 1 min after its start) | The schedule starts the taskflow no matter what | L-CDI-078, L-CDI-127 |
| Coalesce events: a pending counter per lane, and the next run takes all of them | A burst of sign-ups becomes one run, not twenty | L-CDI-128 |
| Minimum gap per event lane (`MIN_GAP_S`; 0 = start as soon as pending) | A job-budget lever | L-CDI-131 |
| Round-robin between event lanes | A new record arriving during every 5-minute per-record run starved the activity lane | L-CDI-128 |
| A 5 s scheduler tick | Low pickup latency without hammering the API | L-CDI-128 |
| Never switch the engine (linear ↔ staged, plan v1 ↔ v2) mid-lane | Half a lane on each engine gives an unverifiable result | L-CDI-125 |

## 6. Concurrency on a shared small host

- **Cap concurrency near the host's vCPU count** when agents share it. Four concurrent jobs on a 4-vCPU host running two agents was the working point; 8 bought almost nothing (L-CDI-126, L-CDI-134).
- **Readers per mapping.** Each BigQuery reader takes DTM Java heap, and the heap is agent-wide, not settable per task. 7–8 readers in one mapping died with heap / GC-overhead errors, 6 worked once, and at most 5 (the splitter targets 4) was reliable. Select only the columns you need, and give STRING reader fields a precision of 256 (4000 made the reader allocate huge row buffers; L-CDI-129).
- **Parallel BigQuery runs** can throw transient GCS-staging `5001` errors (with 409/404). They cleared on a serial retry, and sometimes the data had landed anyway, so check the target before treating it as a failure (L-CDI-130).
- **Host tuning that mattered:**
  - a separate OS user and systemd unit per agent, with memory limits and CPU/IO weights so the second agent cannot starve the first or the apps;
  - swap for idle JVM pages;
  - **select only the agent services and connectors you need**: selecting all services pulled 18 GB of packages in 8 minutes, drove load to 189 on 4 vCPU and used all swap;
  - enable catalog metadata services only for a scan and deselect them afterwards (3.7 GB freed).
  See [knowledge/02-secure-agent](../02-secure-agent).
- **Where DTM time goes.** Two agents on 4 vCPU contended for CPU, not memory. When lanes slow down, look at CPU wait on the host before adding concurrency.
- **Temp_View collisions.** A BigQuery V2 custom-query source creates `Temp_View<epoch-ms>` in the connection's dataset. Two DTMs that reach that step in the same millisecond collide: one fails with 409 'Already Exists', the other's cleanup DELETE gets 404 (and may leave the view behind). Measured at 1 in about 1,717 task runs at concurrency 4. Retry the task once after ~20 s (it gets a new timestamp), optionally add 1-2 s of start jitter between tasks of one stage, and drop leftover `Temp_View*` views afterwards, or they get catalogued (L-CDI-160; L-CDI-205).
- **Heap OOM beside other lanes.** A mapping with many Joiners, Sorters and Aggregators can pass alone and fail beside other lanes, because each DTM takes the agent-wide heap setting and several run at once. The first error is `PLUGIN_1762... OutOfMemoryError`; the token errors that follow are a cascade ([09](08-source-target-gotchas.md) §7; L-CDI-210).

- **Parallel JDBC V2 lanes into one database** (L-CDI-292, 2026-11-01 to 2026-11-03). Eleven uncapped lanes reading one ClickHouse server drove it to its memory limit: one lane failed MEMORY_LIMIT_EXCEEDED and another's long read died with 'Premature EOF' after 9.7M rows; address-verification shard runs failed Code 241 until `SETTINGS max_threads = 4, max_memory_usage = 6000000000` went into their source SQL. Stream from a live source (no GROUP BY over wide rows), cap memory and threads in every source query, allow external sort and group-by spill (L-CDI-272) and run about 3 heavy lanes at once; the database's concurrent-query limit (32 here) is shared by loads, DQ and verification. On other warehouses use statement memory limits, resource groups or workload management.
- **Read the real buffers before you tune** (L-CDI-290): `TM_6660` in the session log gives the buffer pool and block size actually used, `DBG_21699` from the reader means back-pressure, and `JDBC_V2_10000` shows the exact SELECT and INSERT ([03](03-mapping-tasks-create-update-run-monitor.md) §9).
- **A small fallback agent after a failover** (L-AGENT-118, 2026-11-03): a CPU-bound data-quality mapping took 62 s on a 2-vCPU Secure Agent at 4 tasks at once against a 26 s p50 on the Hosted Agent, and started late behind other jobs; a full-reprocess golden-record mapping took 118 s on both. Size the fallback for the CPU-bound share and start the latency-critical task first; for full-reprocess mappings the lever is an incremental design.

### 6.1 The DTM pool: measure it before you raise concurrency (L-AGENT-099)

Every mapping-task session waits for a slot in the Data Integration Server's DTM pool. The pool size is the Tomcat property `maxDTMProcesses`; with no such line in `tomcat.cfg` the default is **2**. With the default, a controller that submits 4 tasks in parallel never gets more than 2 concurrent DTMs, whatever it submits. CPU was not the limit: a landing or SQL-ELT DTM spends most of its 14-20 s waiting on the warehouse load or query job (about 12 s) and only ~2 s on JVM start.

1. **Read the pool size:** `grep -h 'maxDTMProcesses(poolSize)' <agent_home>/apps/Data_Integration_Server/logs/tomcat/tomcat_*.log | tail -1` (logged at DIS start-up, for example `maxDTMProcesses(poolSize)=2`).
2. **Measure the queue:** per session, the time from 'Submit job to thread pool queue' to 'DTM process started' ('Creating DTM process' sits between them) in the same log; report p50 / p90 / max. Sample the number of DTM child processes of the DIS JVM every 5 s during a busy period.
3. **Decide:** the pool binds when the observed maximum equals the pool size and the p90 wait is above ~10 s (measured on the default pool: p50 13.9 s, p90 39.7 s, p99 70.1 s; 61% of 472 sessions waited over 10 s).
4. **Raise it cloud-side,** in a drained window: a Custom Configuration row `Data_Integration_Server<major.minor>` / `TOMCAT_CFG` / `maxDTMProcesses` / `<N>` (the Tomcat type does not list this property, so it must be a custom row), together with the DTM heap (`JVMOption1`, type DTM, for example `-Xmx2048m`), through the agent.do form ([knowledge/02-secure-agent](../02-secure-agent); L-AGENT-088), so both survive version rolls. The save restarts DIS by itself about 1.5-2 minutes later and may roll it to a pending build; the old JVM kept dispatching until the new one's tunnel opened, and no dispatch gap was seen.
5. **Verify:** `poolSize=<N>` in the new `tomcat_<disVersion>.log`, the same queue histogram under a real burst (aim for p90 under 10 s), and the agent unit's memory events (`high`, `oom_kill`).

| Pool | When |
|---|---|
| 2 (default) | parallel lanes serialize; a staged executor caps at 2 |
| 4 | a 4-vCPU host with about 8-12 GB available to the agent (about 0.5-1 GB per DTM plus heap headroom) |
| 1 | small or shared database hosts; heavy profiling (L-DQ-098) |

Measured after N=4 plus a 2 GB DTM heap: 4 concurrent DTMs in a 15-minute burst, minimum MemAvailable 10.1 GB, agent unit peak 7.55 GB under a 12 GB limit, 0 memory.high events; a 40-task full refresh 40/40 in 321 s; event-lane golden time 62-85 s → 47 s.

## 7. The monthly job cap

**Facts** (L-CDI-131, 2026-09-28):
- An org hit a cap of **10,000 jobs per month**. From then on every Data Integration start failed within about 5 s with "You have exceeded your monthly limit of 10,000 jobs." In the one case seen, the vendor lifted it within hours (reset or raise unknown; L-IPU-041). Assume a new or trial org is capped even when its licence data shows every limit as -1.
- The cap is **invisible headless**: the license API showed every limit as `-1`, and neither the cap nor its lift appeared in the org audit log. Count jobs yourself.
- CDC (Database Ingestion), CAI processes and a database-trigger → CAI relay kept running during the cap: they are not CDI jobs. CAI calls did not move a job budget around a test burst either, so moving work between CAI and another layer saves no jobs (L-IPU-044, L-CAI-038).
- **What the cap looks like in your run data:** only the run that starts first carries the message. The other tasks of each lane are recorded with an empty error, 0 rows and a state outside 1/2/3 (in one window: 8 FAILED runs with the message against 121 zero-row runs across 33 tasks, and event lanes kept adding about 54 attempts an hour). A breaker or alert that matches the message only on FAILED rows sees a fraction of the blocked runs; 'success rate' tiles over a longer window keep reading high; a 'last successful run' freshness header and '24 h rows' tiles freeze and then decay; batch read-backs stop silently. Derive freshness from the newest CDC landing instead, and label batch-fed tiles 'paused since <last success> (job limit)' (L-IPU-060).

**What burns it** (arithmetic from the measured lanes):

| Source of jobs | Jobs |
|---|---|
| One task run | 1 |
| One linear taskflow run of N tasks | N + 1 (a 62-task full run = 63) |
| One staged lane run of N tasks | N |
| An event lane of 16–20 tasks, per sign-up or event | 17–21 |
| A 5-minute feed of 4 tasks + 1 taskflow | 5 × 288 = **1,440 per day** |
| One estimate with event lanes, frequent feeds and full runs | ~3,200–3,600 per day ≈ 100k per month |
| One Dynamic Mapping Task run | untested: its sub-jobs log as type MAPPING; whether each counts against the cap is not measured (L-CDI-289) |

**Levers:** coalescing with a minimum gap; fewer full runs (every N hours instead of hourly); slower feeds, or moving a feed to streaming or CDC; and **consolidation**. The first consolidation build replaced 40 tasks with 11 mappings, 29 fewer jobs per cycle (L-CDI-119); in steady state jobs per full-lane run fell from 63 to 24 and folding 11 CRM upsert tasks into one mapping removed about 175 jobs a day ([06](05-mapping-design-consolidation.md) B5). Pushdown and moving CAI work save nothing. Use CDC or CAI, not CDI lanes, for per-event freshness.

**Measured burn.** An economy cadence on a capped trial org still burned 520-557 jobs a day (about 16-17k a month); a two-hour fast window cost about 280 jobs; a QA round run story by story would cost ~1,750 jobs where 7 write waves cost ~250 (L-IPU-042, L-IPU-058). Projections matter more than the month-to-date count.

**Budget proactively** (details in [knowledge/13-ipu-cost](../13-ipu-cost)): keep your own job ledger from the activity log (`GET /api/v2/activity/activityLog?rowLimit=1000&offset=<n>`, keyed by entry `id`; one job per top-level entry plus one per child of a `WORKFLOW` entry), because the cap is unreadable and the log keeps only a few days (a busy project's full read held about 1,000 entries and each task keeps `maxLogs: 10`, so treat counts from it as lower bounds and record each run at completion; L-CDI-288); publish month-to-date, last 24 h, projected month-end and days of runway; shed load at about 85% (coalesce event lanes, slow feeds) and stop automatic batch lanes at about 95%; when the reset date is unknown, guard on the worst of several windows (UTC month, org-timezone month, since the licence day, rolling 30 days) and fail closed (L-IPU-043, L-IPU-059). Before trimming cadence, attribute each run to what started it (`runContextType`, `startedBy`): a schedule can already read Daily while an external starter runs the same work hourly (L-IPU-061).

**Speed modes under a cap** (L-IPU-054). One mode switch on the controller that starts IDMC jobs, persisted, with the hard job-cap breaker winning in every mode; every other knob (BI refresh, feeds) mirrors it every ~30 s. Economy is the default (event-lane gap 60 s, full rebuild daily, periodic feed every 6 h); fast is timed (1-8 h) and reverts by itself (gap 0, full rebuild hourly, feed every 15 min); an unknown or unreadable mode is economy; CDC and CAI are the same in every mode. Keep any synthetic-load generator off the switch (following fast mode it filled a small SaaS org), make waits interruptible (re-read the mode every 30 s), and state the truth beside the switch: even at gap 0 a record reaches the golden table in about 1-1.5 min and a dashboard only after its own refresh.

**The quota breaker** (L-CDI-132, 2026-09-28; the controller's side):
1. After each run, look for "monthly limit" in the run or task errors.
2. If found, pause the automatic lanes for a backoff (60 min), record SKIPPED lane entries instead of failures, and expose the blocked-until time on the health endpoint and UI.
3. After the backoff, let exactly **one** lane through as a probe: the same error pauses again, a success clears the pause.
4. Send **one** alert per 24 h instead of one per failed lane.
5. Do not gate manual starts or relays that are not IDMC jobs (e.g. a database trigger → CAI → SaaS relay).
6. After a restart, re-derive the pause from the run log.

It un-paused by itself when the cap was lifted. Keep this reactive breaker as the last line behind the proactive ledger above.

**Metering note.** CDI consumption is metered on compute hours per run, not on data volume (2026-07-05; hedged; L-CDI-133). Fewer, longer mappings and fewer jobs lower both the job count and the per-task overhead. Pricing and rates: [knowledge/13-ipu-cost](../13-ipu-cost).

## 8. Checklist before promising a latency

1. Count the tasks on the critical path: × 20 s is the floor for linear execution.
2. Build the DAG; the longest chain × 20 s is the floor for any concurrency.
3. Cap concurrency at about the host's vCPU count, check the DTM pool (§6.1), and keep at most about 5 warehouse readers per mapping.
4. Count jobs per day for every trigger, against the org's monthly cap (ask the admin; the API will not tell you).
5. Before switching a mapping to full SQL ELT, estimate `3 s + 5.4 s × targets` and require parity 0/0 plus a measured gain of at least 20% or 10 s over at least 3 runs ([02](02-how-claude-builds-mappings-headless.md) §9; L-CDI-203).
6. Measure the current path per record (below), find the step that dominates, and work on that step, not on steps that are already fast.
7. Extra on-demand starts cannot shorten a chain whose floor is a task's own runtime: a mapping task runs one instance at a time, and a start while its scheduled run is active fails in about 1 s (L-CDI-304).
8. If the answer is still too slow, the task is CDC or CAI, not a CDI lane. 'Seconds end to end' through batch CDI is not reachable when each lane is 85-150 s; real-time paths must carry the per-event story (L-CDI-206).

### 8.1 Measure source event → governed table per record (L-CDI-206)

A golden mapping that truncate-loads its target re-stamps every row on every run, so its load stamp cannot time a single record. Measure without instrumenting IDMC:
1. **Source events:** the first `_CHANGE_TIMESTAMP` per key from the CDC replica's change history (`APPENDS(TABLE <cdc_dataset>.<table>, <t0>, NULL)`; it also returns rows later purged at the source, L-DBMI-029), or the source `created_at`.
2. **Publishes:** every successful run of the golden mapping (start and end, `startTimeUtc`/`endTimeUtc`) from your run ledger or the activity log (page it at `rowLimit=1000` and flatten taskflow sub-entries; a stand-alone task's sub-entry can have an empty `objectName`: skip it).
3. **First sighting:** for each publish end T, query the golden table `FOR SYSTEM_TIME AS OF T + 2 s` for the new keys. BigQuery accepts only one `FOR SYSTEM_TIME AS OF` value per table per query, so snapshots of one table cannot be UNIONed: run one small query per publish (in parallel). `AT` is reserved and cannot be an alias. Time travel reaches back about 7 days (L-CDI-161).
4. **Decompose:** latency = first sighting − event; wait = run start − event (it can be negative: a row committed up to ~35 s after the mapping started still made that run, because the source is read after the fixed start-up cost); runtime = the activity-log duration. Count the keys that missed a run.
5. **Report** n, average, median, p90, fastest, last and the window, success-only, split by pipeline mode; show 'not measured' when there are no samples, never a typed-in number. Collectors are read-only by construction (PostgreSQL `READ ONLY` transactions with `statement_timeout`; BigQuery SELECT-only with `maximum_bytes_billed` and job labels). Confirm the controller is idle before timing anything.

```sql
-- one query per golden publish (one AS OF per table per query)
SELECT '<run_id>' AS run_id, key
FROM `<cloud-project>.<warehouse-dataset>.<golden_table>`
  FOR SYSTEM_TIME AS OF TIMESTAMP_ADD(TIMESTAMP '<run_end>', INTERVAL 2 SECOND)
WHERE key IN UNNEST(@new_keys);
-- source events, including rows later purged at the source
SELECT key, _CHANGE_TIMESTAMP FROM APPENDS(TABLE `<cloud-project>.<cdc_dataset>.<table>`, TIMESTAMP '<since>', NULL);
```

**Baseline on one 8-vCPU agent host** (58 new records over ~24 h, 42 golden publishes, ~1 GB billed for all snapshot queries; L-CDI-206):

| Hop | Median | Average / range |
|---|---|---|
| source → CDC replica in the warehouse | ~21 s | 20-29 s per table, ~10 s fastest ([knowledge/06-cdc-ingestion](../06-cdc-ingestion)) |
| record → its golden row | 67 s | average 76 s, p90 116 s, fastest 33 s |
| golden mapping runtime (11 targets, ~8,900 rows) | 65 s | 58-77 s: the bottleneck |
| wait for the golden mapping to start | 1.5 s | — |
| records that missed a run (lane gap or a running lane's lock) | — | 7 of 58, forming the whole 104-156 s tail |
| real-time CAI decision | ~0.1 s | — |
| event → CRM contact through CAI | ~1 s | — |
| event → BI extract republished | — | 40-130 s ([10](09-serving-outputs-to-bi-and-apps-freshness-latency-reverse-etl.md)) |

After a 4 → 8 vCPU resize the PostgreSQL ingest mappings ran about 3x faster (123 → 41 s, 112 → 38 s, 67 → 24 s) and the golden mapping 75 → 65 s (L-CDI-206). Conclusion from this baseline: optimize the mapping on the path (here an 11-target golden mapping), not the trigger.
