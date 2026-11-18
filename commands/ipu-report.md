---
description: Report IPU consumption and job usage for a period, by service and project, with the biggest savings
argument-hint: "[period, e.g. this month]"
---

Use the idmc-mp and idmc-ipu skills. On Windows, use `python` (or `py`) where these steps say `python3`. Read-only.
Period: $ARGUMENTS (default: the current month).

1. Prove the org (`python3 "${CLAUDE_PLUGIN_ROOT}/toolkit/check_login.py"`).
2. Run the metering export and read its CSV
   (`${CLAUDE_PLUGIN_ROOT}/knowledge/11-ipu-metering-licensing/02-metering-consumption-exports.md`). If billed IPU reads
   0, use the labelled activity-log proxy (section 5) and say it is a proxy.
3. Count jobs for the period separately: the monthly job cap is its own ledger and cannot be read over the API.
4. Report: IPU by service and by project or task, the trend, jobs against the cap, and the three largest savings with
   how to get them (see `/idmc-mp:optimize`). Never present entitlement from `products[]`.
