# IPU cost, entitlement and job caps: cheat sheet

Reading, estimating and lowering IPU consumption, answering "is X licensed?", and staying under the monthly job cap;
applies to any cost report, sizing, licence question, cadence plan or "exceeded your monthly limit" failure.

**Start with:** `/idmc-mp:ipu-report [period]` (skill `idmc-ipu`, read-only) and
[02 Metering & Consumption Exports](02-metering-consumption-exports.md); for licences and caps,
[03 Entitlement, Licences & Job Caps](03-entitlement-licenses-job-caps.md). Prove the org first (`toolkit/check_login.py`).

## What works (headless)

| Task | How (exact route / tool / command) | Lesson |
|---|---|---|
| Billed consumption | `POST <serverUrl>/public/core/v3/license/metering/ExportMeteringData` `{"jobType":"SUMMARY","startDate":"<ISO Z>","endDate":"<ISO Z>"}` -> 201 `jobId` -> poll `.../ExportMeteringData/<jobId>` until SUCCESS -> `.../<jobId>/download` (ZIP, one CSV per org); costs 0 IPU; tool: `toolkit/lib/idmc_metering.py export --start --end --out` | L-IPU-021 |
| Per-project / per-asset split | Same export with `jobType` `PROJECT_FOLDER` (or `ASSET`), windows of 30 days or less | L-IPU-021 |
| Job-level metering (Reported) | `POST .../license/metering/ExportServiceJobLevelMeteringData` `{startDate,endDate,allMeters:true}`; unverified window | L-IPU-065 (reported) |
| IPU alert thresholds (Reported) | `GET /public/core/v3/metering/ipuAlert/org('<orgId>')[/viewTagsPreference]`, read-only | L-IPU-069 (reported) |
| Usage proxy when billed reads 0 | `GET /api/v2/activity/activityLog?rowLimit=1000&offset=<n>`; hours x editable rate, labelled `estimate=true, billed=false` | L-IPU-024 |
| Licence census | `GET <pod>/license-service/api/v1/OrgLicenseAssignment('<orgIdV3>')/EffectiveLicenses` -> `active[]` (`limits{}` read -1) | L-IPU-030 |
| Per-org licence record | `GET /public/core/v3/license/org/<orgIdV3>` (22-char v3 id; v2 id gives `V3API_016`) | L-IPU-029 |
| Entitled / running engines | `GET /api/v2/agent/details/<agentId>` `agentEngines[]`; selections `.../runtimeEnvironment/<reId>/selections/ui` | L-IPU-031, L-IPU-033 |
| Privileges and roles | identity-service `Login` (`effectivePrivileges`, feature flags); `GET /public/core/v3/privileges`, `/roles` | L-IPU-032 |
| Licence-change watch | Every 10 min: diff normalised licence record + engine map; alert on content, not `updateTime` | L-IPU-057 |
| Job ledger | Activity-log rows into an idempotent ledger keyed by entry id; + profile runs + catalog jobs | L-IPU-043, L-IPU-055 |
| Estimate a design | CPDS rate card x Measurement Guide units ([01](01-ipu-model-mechanics.md) §3-4); counts and sizes, never runtimes | L-IPU-003, L-IPU-004, L-IPU-008 |
| Know what is free | 0 IPU: development, reads, export/import and clones, connection tests, taskflow orchestration, metering reads. Metered: runs, UI previews, scans, profiles, serverless hours | L-IPU-005 |
| Count jobs | 1 per task run + 1 per taskflow run (top-level rows + each WORKFLOW row's `entries[]` children); 2,329 rows were 2,775 jobs | L-IPU-042, L-IPU-043 |
| Size small pipelines | Below ~1 GB a month, run counts and API-write batching drive IPU, not volume (one flow ~20 -> 0.1 IPU a month by batching) | L-IPU-009 |

## What doesn't work, and the workaround

| Wall | Workaround | Lesson |
|---|---|---|
| Summary GETs (`MeteringUsageSummary`, `/metering/summary`...) 404 | Use the export; the 404 says nothing about entitlement | L-IPU-022 |
| Trial / embedded sub-org exports a header-only CSV | Labelled activity-log proxy; the zero is trial-conditional | L-IPU-023, L-IPU-024 |
| Monthly job cap readable nowhere (`limits` -1, `customLimits: []`, no jobs row on trial) | Own job ledger; assume ~10,000 until Informatica confirms; ask for limit and reset date | L-IPU-041, L-IPU-056 |
| No licence inventory API | Administrator > Licenses CSV export; `EffectiveLicenses` `active[]` | L-IPU-029, L-IPU-028 |
| Sub-org licence allocation | Proven in the UI (parent's Sub-Organizations > Licenses); a reported `PUT /public/core/v3/license/org/<subOrgId>` is a full overwrite: GET, edit, PUT back; check the parent first | L-IPU-035, L-IPU-072, L-IPU-034 |
| Activity log keeps only days and misses profiles and catalog jobs | Collect on a schedule; add profiling and catalog job sources | L-IPU-024, L-IPU-055 |
| Price of an IPU | Never from this KB: it is in the customer's Order | L-IPU-019 |

## Fastest safe path

1. Prove the org. Read-back: org id; `OrgLicenseAssignment(...)/Views` shows whether it is a trial (L-IPU-056).
2. Run the metering export for the period (full ISO dates with a zone). Read-back: status SUCCESS and a CSV with rows.
3. Header-only CSV? Build the proxy and say it is a proxy. Read-back: proxy rows labelled `billed=false` (L-IPU-024).
4. Aggregate by `BillingPeriodStartDate/EndDate`, not calendar month; by service (`MetricCategory`) and project
   (L-IPU-027). Read-back: totals with the unit (per month) in every label (L-IPU-016).
5. Count jobs separately: task rows + taskflow rows + their children + profiles + catalog jobs (L-IPU-042, L-IPU-055).
   Read-back: month-to-date jobs, 24 h burn, projected month-end, runway to the hard threshold.
6. Attribute burn to its trigger (`runContextType`, `startedBy`) before trimming (L-IPU-061).
7. Propose the largest savings: fewer, larger jobs; coalesced event lanes; slower feeds (L-IPU-043, L-IPU-064).
8. Before any run, preview, scan or profile in someone else's org: explicit, recorded approval (L-IPU-020).

## Top traps

- "Not licensed" from `products[]` or a 404 -> launcher label / wrong host -> read engines, privileges, `EffectiveLicenses` (L-IPU-031, L-IPU-038).
- Capability "missing" -> usually the selection or engine layer, not the contract (L-IPU-033).
- 400 `V3API_007` on export -> bare date -> `2026-06-01T00:00:00Z` form; 400 `LS_147` -> `jobType` alone (L-IPU-021).
- 400 `LS_298`, no job -> `PROJECT_FOLDER` window over 30 days -> split windows (L-IPU-021).
- Export will not start or comes back `PARTIAL_SUCCESS` -> 5 active jobs per org; partial ZIPs may be incomplete, ZIPs kept 3 days -> queue, flag partials (L-IPU-070).
- Tuning agents to cut Mass Ingestion IPUs -> it is metered per GB or million rows, not runtime -> move less data (L-IPU-063).
- Estimator says 0.0 -> the collector got 403 or nothing -> treat zero or unsampled as unknown, fail on errors (L-IPU-025).
- Estimator prices a line at 0 -> service name not exactly the rate-card name (L-IPU-010).
- Monthly read as annual -> twelvefold error -> keep the unit in every variable (L-IPU-016).
- "Exceeded your monthly limit of 10,000 jobs" -> every DI start fails in ~5 s; CDC and CAI keep running -> breaker with backoff + one probe lane (L-IPU-041, L-IPU-043).
- Breaker sees only a few FAILED rows -> rest of each lane logs zero-row non-success -> count those as blocked (L-IPU-060).
- Metering page "10,000" -> serverless compute-unit hours, not the job cap (L-IPU-056).
- Guard counts the wrong window -> reset date unknown -> max of four windows, fail closed (L-IPU-059).
- "MCP is free" -> backing services bill; taskflow runs are jobs that bill no compute hours (L-IPU-005, L-IPU-044).
- External runner every few minutes -> ~728 jobs a day, invisible in schedules -> count jobs per task per day (L-IPU-064).
- Test rounds per story blow the cap -> budget by write waves (~250 vs ~1,750 jobs) (L-IPU-058).

## Go deeper

- [01 IPU Model](01-ipu-model-mechanics.md): the pool, subscription shapes, rate card, compute hours, free vs metered, sizing method.
- [02 Metering & Consumption Exports](02-metering-consumption-exports.md): the export job, CSV columns, errors, the activity-log proxy.
- [03 Entitlement, Licences & Job Caps](03-entitlement-licenses-job-caps.md): four layers, licence routes, the job cap, ledger, breaker, fast mode.
- [Lessons: IPU, Metering & Licensing](lessons.md) (L-IPU-*; skip the superseded section).
