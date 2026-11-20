---
description: Report IPU consumption and job usage for a period, by service and project, with the biggest savings
argument-hint: "[period, e.g. this month]"
---

Use the idmc-mp and idmc-ipu skills. On Windows, use `python` (or `py`) where these steps say `python3`. Read-only.
Period: $ARGUMENTS (default: the current month).

1. Prove the org (`python3 "${CLAUDE_PLUGIN_ROOT}/toolkit/check_login.py"`).
2. Run the metering export (read-only, 0 IPU):
   `python3 "${CLAUDE_PLUGIN_ROOT}/toolkit/lib/idmc_metering.py" export --start <YYYY-MM-DD> --end <YYYY-MM-DD> --out ~/.idmc_toolkit/usage.zip`
   (`--job-type PROJECT_FOLDER` or `ASSET` for per-project or per-asset use, windows of 30 days or less). It starts
   `POST /public/core/v3/license/metering/ExportMeteringData`, polls, downloads the ZIP and prints IPU by meter
   (`${CLAUDE_PLUGIN_ROOT}/knowledge/13-ipu-cost/02-metering-consumption-exports.md`, L-IPU-021). `idmc_session.py` cannot
   do this: it only sends GETs. If billed IPU reads 0 (a header-only CSV), use the labelled activity-log proxy
   (section 5 of that doc) and say it is a proxy.
3. Count jobs for the period separately: the monthly job cap is its own ledger and cannot be read over the API. The
   activity log keeps only days, so a month needs the ledger described in
   `${CLAUDE_PLUGIN_ROOT}/knowledge/13-ipu-cost/03-entitlement-licenses-job-caps.md`.
   For a spike, compare day by day and by project (`PROJECT_FOLDER` export), then find the tasks whose run count or
   duration jumped in the activity log (L-IPU-061, L-IPU-064).
4. Report: IPU by service and by project or task, the trend, jobs against the cap, and the three largest savings with
   how to get them (see `/idmc-mp:optimize`). Never present entitlement from `products[]`.
