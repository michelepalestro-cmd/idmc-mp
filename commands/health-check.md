---
description: Read-only health check of your IDMC org: runtimes, agents, connections, projects, what it can run
---

Use the idmc-mp skill. Read-only: no writes and no job runs.

1. Prove the org: `python "${CLAUDE_PLUGIN_ROOT}/skills/idmc-mp/kb/check_login.py"`. If it fails, follow its message; never retry a login.
2. Read with `python "${CLAUDE_PLUGIN_ROOT}/skills/idmc-mp/kb/14 - Claude Working Methods & Tooling/Script Library/idmc_session.py" get <plane> <path>`:
   runtime environments and agents (`v2 /api/v2/runtimeEnvironment`, `v2 /api/v2/agent`, and per agent its
   `agentEngines[]` and health), connections (`v2 /api/v2/connection`), and projects and folders (v3 objects).
   Check each path against the lessons first: `grep -i "<path>" "${CLAUDE_PLUGIN_ROOT}/skills/idmc-mp/kb/13 - Lessons Learned/lessons.jsonl"`.
3. Decide what the org can run from deployed engines, privileges and selections, never from `products[]` or a 404.
4. Report one table (runtime, agent, status, engines), then connections by type, projects, the services the org can
   run, and anything unhealthy with the lesson id that explains it. Say that the monthly job limit cannot be read
   over the API and has to come from Informatica.
