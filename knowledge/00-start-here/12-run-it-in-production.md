# Run it in production: alerts, a daily check, and what to do when a job fails

**Answers:** How do I find out that a job failed? What should I check every day? A job failed at 2am: what now? How
do I handle agent upgrades, schedule owners, secret rotation and backups?

**Read when:** your pipelines work and now have to keep working without anyone watching them.

**Related:** [End-to-end playbook, Day-2 table](07-end-to-end-playbook-deploy-and-operate-idmc-with-claude.md#day-2-operations) ·
[Mapping tasks: monitor](../04-mappings/03-mapping-tasks-create-update-run-monitor.md#9-monitor) ·
[Deploy & migrate](../12-deploy-migrate/README.md) · [IPU & cost](../13-ipu-cost/README.md) ·
[Secrets hygiene](../14-working-with-claude/06-secrets-hygiene.md)

Everything on this page is read-only unless it says otherwise. Writes still need `--execute --expect-org <orgIdV3>`.

## 1. Know when a job fails (alerting)

Set up both layers: Informatica's own e-mails, and a watcher you control.

**Layer 1: Informatica's e-mail notifications (UI, no code).** Informatica's documentation describes e-mail
notification options for tasks and taskflows (send on failure, on warning, on success), and organization-wide default
notification addresses under Administrator. Set "on failure" (and "on warning") for every production task and
taskflow, to a shared mailbox, not one person. This is from the vendor documentation (docs.informatica.com, search
"email notification options"); it has not been proven headless here, so set it in the UI and check it with one test
failure.

**Layer 2: a watcher (L-CDI-067).** E-mails miss two things: a WARNING that wrote 0 rows (a failure, L-CDI-060), and a
job that never started at all. So also run a small watcher:

1. Every 15 minutes, read `GET /api/v2/activity/activityLog?rowLimit=1000&offset=<n>` (newest first; flatten
   `entries[]` for taskflow children, L-CDI-061; use `startTimeUtc` and `endTimeUtc`, L-CDI-063).
2. For each important taskflow, keep its last state in a small state file. Alert only when the state changes (fails,
   stops running on time, recovers), so the alert does not cry wolf (L-ENV-077).
3. Count `state` 3 (FAILED) and `state` 2 with `successTargetRows` 0 as failures.
4. Alert on freshness too: a daily load that has not finished in about 26 hours is late, even with no failed run
   (L-ENV-077).
5. One watcher per org, with separate state files (L-CDI-067). A healthy container or agent process is not a healthy
   pipeline: judge by runs that completed and rows that arrived.

Watch the hosts as well: an uptime alert per agent VM, host metrics that really arrive, and disk space on the agent
home (L-ENV-074, L-AGENT-107).

## 2. The daily health check

Run `/idmc-mp:health-check` every morning. Ask Claude Code to schedule it, or run the same reads from cron on a machine
that holds the login file. It reports:

| Check | How | Lesson |
|---|---|---|
| Failed runs in the last 24 h | activity log, `state` 3 | L-CDI-059 |
| WARNING runs that wrote 0 rows | `state` 2 and `successTargetRows` 0 | L-CDI-060 |
| What is running now (stuck jobs) | `GET /api/v2/activity/activityMonitor` | L-CDI-062 |
| Agents and services up | `GET /api/v2/agent`, then `agentEngines[]` per agent | 02 Secure Agent cheat sheet |
| Job-cap burn | jobs today (1 per task run plus 1 per taskflow run) against your monthly cap; profiling and catalog runs are counted elsewhere | L-IPU-041, L-IPU-055 |
| IPU trend | `/idmc-mp:ipu-report` weekly (`toolkit/lib/idmc_metering.py`) | L-IPU-021 |
| Who changed what (optional) | `GET /public/core/v3/securityLog` for logins and admin changes | L-AUTH-135 |

## 3. A job failed at 2am: the runbook

1. **Read the run.** Find its activity-log entry (match on `runId`, never just the newest row, L-CDI-059). Note the
   state, rows written, rows failed and `errorMsg`.
2. **Get the session log** if the message is short: `GET /api/v2/activity/activityLog/<entryId>/sessionLog`
   (`<entryId>` is the entry's `id`, not its `runId`). Search it for the first `[ERROR]` (L-CDI-211).
3. **Classify it** with the outcome table in
   [Mapping tasks section 9](../04-mappings/03-mapping-tasks-create-update-run-monitor.md#9-monitor) (L-CDI-205, L-CDI-287):

   | The error says | It is | Do |
   |---|---|---|
   | 50x, "service unavailable", "rate limit", "connection reset", "Retrying may solve the problem" | transient | run it once more after about 20 s; never twice |
   | "Aborted by agent disconnection", "DTM process terminated", "Premature EOF", "Too many simultaneous queries" | transport or capacity | retry up to 3 times with backoff; check the agent host |
   | cast error, null into a non-null column, constraint violation, permission on the asset | deterministic | fix the cause; a retry only repeats it |
   | fails in 2-3 s, 0 rows, "no active Secure Agent in group Informatica Cloud Hosted Agent" | Hosted Agent outage | open a support case and fail over (step 5) |
   | "monthly limit" | the job cap | no retry; stop non-essential schedules (L-IPU-041) |
   | WARNING with 0 rows | a failure | treat as FAILED (L-CDI-060) |

4. **Search the lessons** for the exact error code or text: `knowledge/lessons/error-index.md`, then
   `grep -i "<error text>" knowledge/lessons/lessons.jsonl`, or run `/idmc-mp:fix-error`.
5. **Hosted Agent outage:** follow L-ENV-100: confirm (APP_105060 on every hosted connection, L-AGENT-117), list the
   tasks on the hosted runtime, save each full task body to an undo file, rebind the tasks and the connections they
   use to a Secure Agent, re-run, and undo when the hosted runtime is back.
6. **Re-run only once the cause is fixed**, and check the rows: a run that "succeeded" with 0 rows has not delivered
   anything.
7. **Write it down:** what failed, why, what fixed it. If it was new, save it with `/idmc-mp:save-lesson`.

## 4. Agent upgrades

Informatica upgrades the Secure Agent and its services automatically. Plan for it:

- **Keep disk free** on the agent home, ideally on its own filesystem: one upgrade wrote a ~1.1 GB package that filled a
  shared disk and crashed the database next to it (L-AGENT-107). Unregister agents you no longer use: they keep
  upgrading.
- **Hand-placed JDBC jars disappear** on a Data Integration Server upgrade. Also stage them in
  `<agent_home>/ext/deploy_to_main/...` so they survive (L-CONN-050).
- **Port and script changes** can come back after a process-server upgrade (L-AGENT-073, L-CAI-072).
- **After every upgrade:** run the health check, test the connections that use custom drivers, and run one job per lane.

## 5. Schedule ownership

No lesson here yet proves what happens to a schedule when the user who created it is removed or loses its role. Until
one does, treat it as a risk to check:

- Create production schedules and tasks with a service user that people do not log in with, not a person's account.
- Before you remove or disable a user, list the schedules, tasks and connections they created
  (`createdBy` on the v2 objects) and move them first.
- After the change, check that the next scheduled run actually started (the watcher in section 1 catches this).
- When you move schedules between orgs, scan task-level schedules too (L-MIG-048).

## 6. Secrets rotation

- **Your IDMC login:** update every stored copy, clear the lockout block file and the session caches, then prove it
  with exactly one login (L-AUTH-043).
- **Connection passwords and keys:** rotate every consumer in one window; service-account keys never expire by default,
  so set an expiry and a reminder (L-ENV-052). CAI connection secrets: L-CAI-061.
- Full guidance: [Secrets hygiene](../14-working-with-claude/06-secrets-hygiene.md).

## 7. Backups

There is no scheduled backup inside IDMC. Make your own:

1. Weekly (and before every promotion or cleanup), list the production objects
   (`python3 toolkit/lib/idmc_objects.py list`, one v3 object id per line in a file) and export them with their
   dependencies (L-MIG-003):
   `python3 toolkit/lib/idmc_export_import.py export --ids-file <ids.txt> --out <backup folder>/<project>-<date>.zip`.
   The export changes nothing in the org.
2. Keep the zips outside the plugin and out of any repository, readable only by you: a package can hold plaintext
   secrets (L-MIG-018).
3. A package does not carry secrets, schedules, tags, catalog content or published CAI processes (L-MIG-017): keep a
   short written list of those, so a restore can rebuild them.
4. Test a restore into a sandbox org once, the same way as a promotion (`/idmc-mp:promote`).
