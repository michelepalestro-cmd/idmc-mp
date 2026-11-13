# Entitlement, licences and job caps

**Answers:** Is capability X licensed, entitled, selected and running, and where do I read each? What does the
monthly job limit look like, and how do I see it coming? What burns jobs and what saves them? How do I keep a job
ledger, guard an unknown reset date, budget a test round and run a fast mode safely? How do I notice a licence change?

**Read when:** a capability seems missing; you plan a cadence, a test round, a fast mode or a cutover on an org with a
job cap; runs fail with 'exceeded your monthly limit' or stop with zero rows.

**Key rules:**
- Licensed, entitled, selected and running are four layers; read each from its own source, never from `products[]`
  or a bare 404 (L-IPU-033, L-IPU-031).
- A monthly job limit (10,000 seen) stops every Data Integration start and is readable nowhere; a trial edition shows
  no jobs row at all (L-IPU-056, L-IPU-041).
- Keep your own job ledger (activity log plus profile and catalog runs) and shed load at a soft ~85% and a hard ~95%
  threshold (L-IPU-043, L-IPU-055).
- When the reset date is unknown, guard on the worst of four windows and fail closed (L-IPU-059).
- At the cap only the first run of a lane carries the error: count the zero-row non-success runs as blocked too
  (L-IPU-060).
- Budget test rounds by write waves, and keep one timed fast/economy switch that the hard cap always overrides
  (L-IPU-058, L-IPU-054).
- Watch the licence record and every agent's engine list, and alert on content, not on `updateTime`
  (L-IPU-057).

**Related:** [01 IPU Model (mechanics)](<01 IPU Model (mechanics).md>) · [02 Metering & Consumption Exports](<02 Metering & Consumption Exports.md>) · [02 Runtime Environments - Services & Connectors](<../02 - Secure Agent & Connections/02 Runtime Environments - Services & Connectors.md>) · [Performance, Concurrency & Job Caps](<../03 - Data Integration (CDI)/07 Performance, Concurrency & Job Caps.md>) · [Lessons: IPU, Metering & Licensing](<../13 - Lessons Learned/11 IPU, Metering & Licensing.md>)

**Last verified:** 2026-11-03

> "Is it licensed?" has four layers that fail differently: the licence record, the org's entitlement, the selection on
> a runtime environment, and a running engine. There is no licence inventory API, every `EffectiveLicenses` limit
> reads -1, and a monthly job limit stays invisible until it stops every Data Integration job: count jobs yourself,
> guard them, and add a breaker. Org id shapes are in
> [Identify the Org Before You Write](<../01 - Access, Auth & Orgs/03 Identify the Org Before You Write.md>); roles in
> [Users, Roles & Permissions](<../01 - Access, Auth & Orgs/04 Users, Roles & Permissions.md>).

---

## 1. Four layers, four failure signatures

(L-IPU-033; L-AGENT-023.)

| Layer | Read it from | A failure looks like |
|---|---|---|
| Licensed (contract record) | Administrator > Organization > Licenses and its CSV export; `EffectiveLicenses` `active[]` | The capability is absent from the licence list. Never inferred from a REST 404 |
| Entitled in the org | Identity-service Login `effectivePrivileges`, roles, `feature.<cap>.*` flags; the services and connectors a runtime environment offers in its selections; design objects of that type in `GET /public/core/v3/objects` | Missing privilege or role (403/405 on writes), a service not offered |
| Selected on a runtime environment | `enabled: true` in `.../selections/ui` | Engine absent from `agentEngines[]`; a test names it: 'No running service found of type <Engine>' |
| Running and resolvable | `agentEngines[]` RUNNING, then a passing connection test or job | RUNNING in the API while the router still refuses |

Most "licensing" problems turned out to be the selection or engine layer: an org whose `products[]` said only
Integration Cloud held 321 licences, and the real gap was that no service was selected on its agent.

## 2. Ground truth, and what is not evidence

(L-IPU-031.)

| Use | Do not use |
|---|---|
| Identity-service Login: roles, `effectivePrivileges`, `feature.*` flags | The v3 login `products[]` (a launcher label; it listed only Integration Cloud on orgs entitled to CDGC, MCC, CDQ, DAM, Data Prep, DBMI, CAI, MDM, CLAIRE GPT and API Manager) |
| `EffectiveLicenses` `active[]` | A 404 on a guessed path (wrong path, host or pod) |
| `GET /api/v2/agent/details/<agentId>` `agentEngines[]` | `GET /public/core/v3/objects?q=type=='X'` returning 0 (the filter is not validated) |
| Runtime-environment selections (what can be enabled) | `GET /api/v2/connector` (a connector type catalog) |
| Real design objects of the type in `GET /public/core/v3/objects` | An agent-less org's silence: with no agent, entitlement is unresolved, not disproven |

This retired about 90 false 'buy a licence' escalations on one org. Probes of DBMI returned 404 until they were sent to
the `<pod>-ing` host; CLAIRE GPT probes returned 404 on the wrong hosts while it was entitled (L-IPU-038).

## 3. Routes

### 3.1 Privileges and roles

(L-IPU-032.)

```
POST https://<domain>.informaticacloud.com/identity-service/api/v1/Login      -> sessionId, orgId, roles,
                                                                                effectivePrivileges, feature flags
GET  <serverUrl>/public/core/v3/privileges       (INFA-SESSION-ID)            -> e.g. 897 effective privileges
GET  <serverUrl>/public/core/v3/roles                                         -> e.g. 59 roles (system + custom)
```

Count privileges by product prefix (MDM/B360, CDGC/catalog, Marketplace, API Manager/apim, DBMI such as
`create.dbmi.task`, DQ/VERIFIER, DAM/cdam, CLAIRE GPT, metering such as `metering.admin` and
`feature.cdlg.ExportUsageMetrics`) and list roles such as Customer360, CLAIRE GPT User or Data Marketplace Admin; then
combine with the engine list.

### 3.2 The licence service: EffectiveLicenses

(L-IPU-030.) The call the console itself makes:

```
GET https://<pod>.<domain>.informaticacloud.com/license-service/api/v1/OrgLicenseAssignment('<orgIdV3>')/EffectiveLicenses
IDS-SESSION-ID: <session>
Accept: application/json
-> 200 {"active": [{"id": "...", "name": "CLAIRE GPT"},...],       # one org listed 469 active licences
        "limits": {"<licence id>": -1,...}}                       # every value -1 in two orgs (32 and 76 limits)
```

`active[]` is the best headless licence census available (names such as CLAIRE GPT, clairegpt.core,
ai.agent.engineering.designer appeared there while `products[]` said only Integration Cloud). `limits{}` read -1
everywhere, including in an org that had just hit its monthly job cap, so -1 does not mean "unlimited" in any useful
sense: it means the limit is not expressed here (section 5).

### 3.3 Per-org licence detail, and what does not exist

(L-IPU-029.)

| Route | Answer |
|---|---|
| `GET <serverUrl>/public/core/v3/license/org/<orgIdV3>` | 200 per-org licence detail with the 22-character v3 org id; the 6-character v2 id gives `V3API_016`; TRIAL licences came back without names and `customLimits: []` |
| `GET /public/core/v3/licenses` | 404 'No static resource' |
| `GET /api/v2/license` | 404 on a sub-org, 200 on another org |
| `GET /api/v2/org/<id>/license[s]` | 404 |
| `GET /api/v2/org/<id>` from a sub-org user | 403 REPO_10404 (use `GET /api/v2/org`) |
| `GET /api/v2/org` | 200, but only `maxLogRows`, `subOrgLimit`, `restApiSessionLimit` among limits |

For the licence list itself use Administrator > Organization > Licenses (for a sub-org, the parent's Sub-Organizations >
Licenses) or its CSV export ([doc 02](<02 Metering & Consumption Exports.md>) section 6).

### 3.4 Watch for a licence or entitlement change

Licence changes that matter (a new package such as the Data Gateway, a lifted job limit, a new edition) arrive without
notice, and part of each is invisible (limits read -1; the job cap never appears). Poll instead of re-checking by hand
(L-IPU-057). Everything here is read-only.

1. Every 10 minutes: `GET <serverUrl>/public/core/v3/license/org/<orgIdV3>` (v3 session; the 22-character id,
   L-AUTH-073). Normalise `customLicenses[]` to `licenseDef|licenseType|startDate|expirationDate` and
   `assignedEditions[]` to `edition|startDate|expirationDate`, sorted, and keep `updateTime` separately
   (L-IPU-057).
2. For each agent: `GET /api/v2/agent/details/<agentId>` and map `agentEngines[].agentEngineStatus.appname` (plus its
   version) to `status`.
3. Hash the normalised licence lists plus the sorted engine map into one fingerprint and diff it against the stored
   snapshot.
4. On a fingerprint change or a new engine, append the diff to a change log and send **one** notification. An
   `updateTime`-only change (seen with the same 6 licences and 8 editions) is information, not an alert.
5. Write a heartbeat line on every run, so a dead watcher is visible.

```
every 10 min:
  lic = GET /public/core/v3/license/org/<orgIdV3>
  eng = {a: GET /api/v2/agent/details/<a> -> agentEngines[].appname + version + status}
  fp  = hash(normalized(lic.customLicenses, lic.assignedEditions) + sorted(eng))
  if fp != last_fp: log(diff); notify_once(diff); last_fp = fp      # ignore updateTime-only changes
  heartbeat
```

The decisive signal that an entitlement reached a Secure Agent is a new engine in the agent details (or a looping
service leaving RESTARTING): a licence line alone deploys nothing (L-AGENT-097, L-AGENT-098). A newly granted package
showed up as a new RUNNING engine on every agent within about 10 minutes. To prove a gap between two orgs, diff their
engine and selection lists (L-IPU-053).

## 4. Parents, sub-orgs and assignments

- **Sub-orgs inherit** the parent's entitlements; a narrow `products[]` in the sub-org's own login means nothing
  (L-IPU-036). Trial or embedded sub-orgs accrue zero billed IPU even when capabilities run.
- **Check the parent first**: a sub-org showing one engine looked unlicensed, but the parent's shared agent ran 22
  engines and selecting services on the sub-org's own agent delivered all 22 with no reinstall (L-IPU-034).
- **Allocating licences to a sub-org** is UI-only: the parent's Administrator > Sub-Organizations > Licenses
  (L-IPU-035).
- **Shared orgs can licence-lock UI roles**: a demo user could not see Monitor > All Jobs, My Jobs or the Application
  Integration Console, and adding Monitor or Operator roles failed with 'license status is not enabled'; use Monitor >
  Running Jobs, Operational Insights or the job APIs instead (L-IPU-039).

**Capability notes**

| Capability | Finding | Lesson |
|---|---|---|
| CLAIRE GPT | Entitled per `EffectiveLicenses` and a live query (201) although no agent engine serves it; it is a cloud service | L-IPU-038 |
| API developer portal | No Developer Portal privilege among ~660 and `/public/api/v1/apiPortal` 404: a weak, disputed signal of a missing SKU; confirm in Administrator | L-IPU-037 |
| Database Ingestion pricing | A 'fixed floor plus 24x7 runtime' structure was never verified; the CPDS meters CDC per million rows | L-IPU-040 |
| CAI | A Process Server in `agentEngines[]` means the runtime is provisioned; Application Integration comes with Integration Cloud | L-AGENT-048 |

## 5. The monthly job limit

(L-IPU-041.) An org can carry a monthly job limit; one org stopped at 10,000.

**What happens at the cap**

- Every Data Integration start (mapping tasks, taskflows, DQ, reverse-ETL, read-backs) fails within about 5 seconds with
  'You have exceeded your monthly limit of 10,000 jobs.'
- Still working: an already running Database Ingestion CDC job, CAI processes, and address verification through its
  managed MCP tool.
- The lift came about 8.5 hours later from Informatica, with no trace over the API; whether it was a reset or a raise
  could not be seen.

**What the cap looks like in your run data** (L-IPU-060)

- The run that starts first fails with the cap message. The remaining tasks of each lane are recorded with an empty
  error, 0 rows and a state outside 1/2/3 (state 4 in a run ledger mirrored from the activity log). In two hours that
  was 8 FAILED runs carrying the message against 121 zero-row runs across 33 tasks, while event-triggered lanes kept
  adding about 54 attempts an hour.
- A breaker or alert that matches the message only on FAILED rows sees a fraction of the blocked runs: treat any
  state other than SUCCESS or WARNING with zero rows after a cap error as blocked by the cap.
- Downstream: 'success rate' tiles over a long window keep reading high; a 'last IDMC run' freshness header and any
  '24 h rows processed' tile freeze, then decay to 0; batch read-backs and batch-only enrichment stop silently. Derive
  BI freshness from the newest CDC landing (CDC keeps running at the cap, L-DBMI-044), label batch-fed tiles 'paused
  since <last success> (job limit)', and point reconciliation views at real-time sources where they exist.

**Trial editions** (L-IPU-056): the Licenses page shows no jobs row, every `EffectiveLicenses` limit reads -1,
and the Metering page shows only serverless compute-unit-hour meters (10,000 hours each; [doc 02](<02 Metering & Consumption Exports.md>)
section 1.1). No API exposes a monthly jobs cap, so assume the cap seen on a comparable org (10,000 jobs a month) until
Informatica confirms otherwise. Budget QA and rehearsal rounds in jobs and recount from the activity log after each
round: three story rounds burned about 294 jobs in 1.7 hours and pulled the projected cap date to about 12 days out.

**Why you cannot see it coming**

| Where you would look | What it showed |
|---|---|
| `GET /api/v2/org` | `maxLogRows`, `subOrgLimit`, `restApiSessionLimit` only |
| `GET /public/core/v3/license/org/<orgIdV3>` | `customLimits: []`; TRIAL licences without names |
| `EffectiveLicenses` `limits{}` | Every limit -1, before and after the cap |
| v2 audit log | Nothing when the cap was lifted |
| Activity log | Only about 3-4 days of history, so month-to-date counts must be collected continuously |
| Administrator > Metering | Serverless compute-unit meters (10,000 hours on a trial), not jobs (L-IPU-056) |

So: keep your own job ledger (section 7.1), ask Informatica for the limit and its reset date (after a migration, in one
batched case: [Cutover & Rollback](<../10 - Migration & Org Management/05 Cutover & Rollback.md>) section 7), and check
a target org's limit before a migration cutover.

## 6. What burns jobs, and what does not

(L-IPU-042; L-IPU-044.)

**Arithmetic**: 1 job per task run plus 1 per taskflow run. In the activity log that is each top-level row plus, for a
taskflow row (`type` WORKFLOW), each child in its `entries[]`; a stand-alone mapping task's own sub-entry is its
session, not a second job (L-IPU-043).

| Pattern | Jobs |
|---|---|
| A 16-20-task event lane per user event | 17-21 per event |
| A 62-task full lane | 63 per run |
| A 5-task taskflow every 5 minutes | 5 x 288 = 1,440 a day, about 10,000 a week |
| All hourly schedules of one pipeline | about 650 a day |
| An event-driven demo stack (event lanes + full lane every 4 h + a 5-minute feed) | about 3,200-3,600 a day, roughly 100,000 a month |
| Back-to-back event lanes under test traffic | about 4,000 in one day |

**Counts as a job but bills no compute hours**: taskflow runs (orchestration is free in the Measurement Guide, the tasks
it runs are metered).
**Does not count as a job**: address-verification MCP calls (they do not appear as IDMC jobs; they still consume their
service's metered units). On-agent address verification is IPU-metered too: the agent fetches the licence file
`AV_IDMC_IPU.LIC` again at every start (L-AGENT-116), and a sweep that restarts from its first key repeats those metered
calls (L-CDI-283).
**Not measured**: whether each job of a Dynamic Mapping Task counts separately against the monthly cap (its sub-jobs log as
type MAPPING; L-CDI-289).
**Not stopped by the cap**: CAI process executions and an already running CDC job (whether they count toward the limit
was not established).

**Measured burn and what saves jobs** (L-IPU-042). An economy cadence on an event-driven stack still burned
520-557 jobs a day (about 16-17k a month) against a guard of soft 8,500 / hard 9,500; a two-hour fast window cost about
280 jobs; three story-test rounds added 150-300.

| Saved jobs | Did not save jobs |
|---|---|
| folding 11 SaaS-target tasks into one mapping (about 175 a day) | moving CAI work elsewhere (CAI calls are not jobs) |
| reading CDC replicas instead of re-ingesting the source (3 jobs per lane run) | full SQL ELT pushdown (a pushed-down task is still a job) |
| coalescing events into one lane run per burst (section 7.3) | |

**Count from every source** (L-IPU-055): the v2 activity log for tasks and taskflows (top-level rows plus each
taskflow's children), the profiling service's run history for profiles, and the catalog jobs API (filtered by your
catalog-source ids) for scans and catalog Data Quality runs. A guard that reads only the activity log under-counts a
profiling or catalog workload. Rule-specification previews (for example from CLAIRE rule tests) do appear in the
activity log, as short `PreviewMapping_RULE_SPECIFICATION` runs (about 3 s); whether they count against the cap is not
verified (L-IPU-058). Glossary loads add one catalog 'Content Publish Task' job per created asset (L-CDGC-153).

**Attribute every run to its trigger before you trim** (L-IPU-061). Group the activity-log rows by `runContextType`
(`SCHEDULER` or `REST_API_V2`) and `startedBy`. Two schedules already read `Daily` while their work still ran hourly,
started over REST by an external lane controller: the cut belonged in the controller, and editing the schedules would
have saved nothing. Read each schedule's `interval` and `frequency`, never its name (one named hourly ran every 4 hours).

## 7. Budgeting and a quota breaker

(L-IPU-043.)

**Levers**: coalesce events into one lane run (a minimum gap between event lanes); run the full lane less often; slow
high-frequency feeds (5-minute to hourly saved 1,440 jobs a day); consolidate many copy tasks into few mappings; freeze
test traffic before a demo; prefer CDC or CAI where per-event freshness matters.

**Breaker** (in the controller that starts jobs):

```
on start error containing "exceeded your monthly limit":
    blocked_until = now + QUOTA_BACKOFF (60 min)          # pause the event and full lanes
    alert at most once per 24 h                           # not once per failed lane
at blocked_until: let exactly one probe lane through
    success -> clear the block;  failure -> extend it
expose blocked_until on /health; leave manual starts and non-IDMC real-time paths (CAI relay, CDC) ungated
```

Before cutting over into a trial or new org, confirm its job limit or cut over with a budgeted cadence (a minimum gap
between event lanes, fewer full runs) (L-IPU-043).

### 7.1 A proactive job ledger with soft and hard thresholds

The cap cannot be read and the activity log keeps only a few days, so persist every job yourself and act before the
cap does (L-IPU-043).

1. Every ~10 minutes, page `GET /api/v2/activity/activityLog?rowLimit=1000&offset=<n>` (newest first) and insert each
   entry into a ledger keyed by the entry `id` (idempotent). Stop paging when a page inserts nothing, its oldest row is
   from the previous month, or it returns fewer than 1,000 rows.
2. Count each top-level entry as one job and, for taskflow entries (`type` WORKFLOW), each child in `entries[]` as one
   more (section 6). Add profile runs and catalog jobs from their own services (L-IPU-055).
3. Derive month-to-date jobs, jobs in the last 24 h, the top job sources of the last 24 h, the projected month-end
   count and the runway to the hard threshold, and publish them on a health endpoint.
4. Shed load in two steps against the cap you expect (10,000 observed). **SOFT** at about 85% (8,500): coalesce event
   lanes to a long gap (for example one run per 600 s) and slow periodic feeds (for example every 2 h). **HARD** at
   about 95% (9,500): start no automatic batch lane until the month resets. Alert once per level per month. CDC and a
   database-trigger to CAI real-time relay are not jobs and keep running.
5. Keep the reactive breaker above as the last line.

```sql
CREATE TABLE IF NOT EXISTS idmc_job_ledger (activity_id text PRIMARY KEY, month text NOT NULL,
  started_at timestamptz, job_type text, name text, parent text, counted_at timestamptz NOT NULL DEFAULT now);
-- INSERT... ON CONFLICT (activity_id) DO NOTHING
```

```
level = HARD if jobs >= 0.95*cap else SOFT if jobs >= 0.85*cap else OK     # every lane reads the level before it starts
projected_month_end = jobs + jobs_24h * days_left
runway_days         = (hard - jobs) / jobs_24h
```

Assume a new or trial org is capped even when every limit reads -1: an org showing -1 stopped at 10,000. Projections
matter more than the month-to-date count: one day at a heavy test pace (557 jobs) projected about 17,500 for the month,
which would have tripped the hard threshold after about 16 days.

### 7.2 Unknown reset date: guard on the worst of four windows, and fail closed

A hidden cap may reset on any of four windows, and a count over the wrong one can be off by thousands: in one org the
four windows read 2,899, 2,811, 6,774 and 6,774 jobs at the same moment (L-IPU-059).

| Window | Key |
|---|---|
| calendar month, UTC | `cal_month_utc` |
| calendar month in the org's timezone (`timezone` in `GET /api/v2/org`) | `cal_month_<tz>` |
| since the licence anniversary day | `since_<day>` |
| rolling 30 days | `rolling_30d` |

1. Take org usage as the maximum over the four windows.
2. The activity log keeps only about 4 days, so on every run append an hourly-maxima snapshot to your own ledger and
   merge it; flag hours nobody observed as estimates.
3. Add the sources the activity log misses: profile run history, and catalog jobs filtered by your catalog-source ids
   (L-IPU-055).
4. Make the pre-run check fail closed. It exits non-zero when a read fails; when usage plus the planned jobs would
   cross a lane's month, day or hour budget or an org-wide pause threshold set below the cap; when a cap-error text
   ('exceeded your monthly limit') appeared within the block window; or when a login was rejected.
5. At the recent daily pace, project for each window the date it reaches each threshold. In a shared org, freeze the
   lower-priority tenants well before the cap (L-IPU-042).

| Exit code | Meaning |
|---|---|
| 0 | allowed |
| 3 | blocked (the reason is printed) |
| 4 | an IDMC read failed (fail closed) |
| 5 | login blocked |

### 7.3 Test and QA rounds: budget by write waves, not by stories

With coalescing event lanes (a minimum gap between runs of a lane), events inside one burst share one lane run, so a
round costs per write wave, not per story (L-IPU-058). One event-lane run cost about 18 jobs; 129 stories run
one by one would have cost about 1,750 jobs, while 42 priority stories grouped into 7 waves cost about 250.

| Step | Rule |
|---|---|
| before the round | read the job budget; probe SaaS-target storage headroom |
| each write wave | one burst, then at least 3 minutes of quiet so the lanes drain; read the budget again |
| read-only checks | waves of their own (0 jobs) |
| double-submit stories | reuse a retry of an existing story instead of creating new identities |
| round cap | for example 300 jobs, hard stop at 350 |
| never | the fast mode that removes the lane gap (every event then costs a full lane run) |
| after the round | purge the test records; recount from the ledger |

### 7.4 A speed switch under the cap: economy by default, a timed fast mode

- **One source of truth** (L-IPU-054): the controller that starts IDMC jobs owns the mode
  (`GET/POST /mode?mode=<id>&hours=<n>`), persists it in a state file and enforces the hard job cap in every mode.
  Every other knob (BI refresh loops, feeds) mirrors it about every 30 s, so every switch path moves every knob.
- **Fast is timed** (1-8 h; 3 h worked) and reverts to economy by itself; offer fixed durations only; an unknown or
  unreadable mode is economy. Make waits interruptible (re-read the mode every 30 s), so a switch acts within 30-40 s
  instead of after an economy-length sleep.
- **The UI ignores read-backs for about 12 s after a switch**; otherwise a stale cached read swallows a second click.
- **Keep any synthetic-load generator off the switch**: following fast mode, it created SaaS-target records faster
  than a small target's storage allowed, and its records pass the BI test filters (L-IPU-054).
- **Label it plainly** (for example 'Normal' and 'Demo'), state the trade-off and quote real numbers: even at gap 0
  each change waits for the lane that carries it (85-148 s per lane), so governed data lands in about 2 minutes, not
  'under a minute'; sub-minute freshness everywhere needs CDC or CAI, not CDI lanes. One two-hour fast window cost about
  280 jobs.
- In fast mode also start lanes for sources that have no change trigger, and retry a core task once on a transient
  failure (a transient 'Table [...] does not exist' left a new record ungoverned for 28 minutes).
- A 'request' endpoint that only queues still honours the minimum gap; a force endpoint starts the run directly, keeps
  only the budget, drain and run-lock guards, and does not reset the gap timer. Never lengthen the economy gap
  silently to save jobs when a live moment depends on it, and never make fast mode a preparation step.

Example knob values (L-IPU-054):

| Knob | economy (default) | fast (timed, auto-revert) |
|---|---|---|
| event-lane minimum gap | 60 s | 0 s |
| full rebuild | daily | hourly |
| periodic feed | every 6 h | every 15 min |
| CDC and CAI paths | unchanged | unchanged |
| synthetic load | does not follow the mode | does not follow the mode |
| hard job cap | wins | wins |

## 8. Overturned beliefs (entitlement)

| Believed | Until | Now | Lesson |
|---|---|---|---|
| About ten capabilities are licence-blocked and must be purchased | 2026-07-06 | Engines, privileges and objects showed them entitled; the walls were UI steps and wrong hosts | L-IPU-049 -> L-IPU-031 |
| The org has only Integration Cloud because `products[]` says so | 2026-07-04 (recurred 2026-09-21/22) | `products[]` is a launcher label | L-IPU-050 -> L-IPU-031 |
| A sub-org showing one engine may need a purchase | 2026-07-26 | Check the parent: it was an assignment | L-IPU-051 -> L-IPU-034 |
| CLAIRE GPT is genuinely absent (no agentic engine) | 2026-07-09 | Active in `EffectiveLicenses`, live query 201 | L-IPU-052 -> L-IPU-038 |
