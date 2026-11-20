---
description: Read-only daily health check of your IDMC org: failed and 0-row runs, agents, connections, job-cap burn, projects
---

Use the idmc-mp skill. On Windows, use `python` (or `py`) where these steps say `python3`. Read-only: no writes and no job runs.

1. Prove the org: `python3 "${CLAUDE_PLUGIN_ROOT}/toolkit/check_login.py"`. If it fails, follow its message; never retry a login.
2. Read with `python3 "${CLAUDE_PLUGIN_ROOT}/toolkit/lib/idmc_session.py" get <plane> <path>`:
   runtime environments and agents (`v2 /api/v2/runtimeEnvironment`, `v2 /api/v2/agent`, and per agent its
   `agentEngines[]` and health), connections (`v2 /api/v2/connection`), and projects and folders (v3 objects).
   Check each path against the lessons first: `grep -i "<path>" "${CLAUDE_PLUGIN_ROOT}/knowledge/lessons/lessons.jsonl"`.
3. Run history for the last 24 hours: page `v2 "/api/v2/activity/activityLog?rowLimit=1000&offset=<n>"` (newest first;
   flatten each taskflow row's `entries[]` for its child tasks; use the `startTimeUtc`/`endTimeUtc` fields, L-CDI-063).
   List every run with `state` 3 (FAILED), every `state` 2 (WARNING) with `successTargetRows` 0 (a failure, L-CDI-060),
   and the error text of each. Classify each failure with the outcome table in
   `${CLAUDE_PLUGIN_ROOT}/knowledge/04-mappings/03-mapping-tasks-create-update-run-monitor.md` section 9 (transient,
   capacity, deterministic, Hosted Agent outage, job cap). Also count the day's jobs (1 per task run plus 1 per
   taskflow run) to show the job-cap burn; profiling and catalog runs are not in this log (L-IPU-055); `v2 /api/v2/activity/activityMonitor` shows what runs now.
4. Connection tests stay out of this read-only check (a test is a call to the agent); list the connections the failed
   runs used and offer to test them.
5. Decide what the org can run from deployed engines, privileges and selections, never from `products[]` or a 404.
6. Report: failed and 0-row runs first (task, time, error, class, lesson id, next step), then one table (runtime, agent,
   status, engines), connections by type, jobs today, projects, the services the org can run, and anything unhealthy
   with the lesson id that explains it. Say that the monthly job limit itself cannot be read over the API and has to
   come from Informatica.

**Run it every day:** ask Claude Code to schedule `/idmc-mp:health-check` (a scheduled task), or run the same reads from
cron on a machine that holds the login file. Alert only when the set of failing tasks changes (L-CDI-067). The full
Day-2 runbook is `${CLAUDE_PLUGIN_ROOT}/knowledge/00-start-here/12-run-it-in-production.md`.
