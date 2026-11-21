---
description: Review a Secure Agent's health and sizing, then recommend (and on your yes apply) tuning
argument-hint: "[agent or runtime environment name]"
---

Use the informatica-idmc-headless and idmc-secure-agent skills. On Windows, use `python` (or `py`) where these steps say `python3`.
Target: $ARGUMENTS (if empty, every runtime environment in the org).

1. Prove the org: `python3 "${CLAUDE_PLUGIN_ROOT}/toolkit/check_login.py"`. Never retry a failed login.
2. Read-only first: runtime environments, agents, `agentEngines[]` and their status, and the selected services and
   connectors (`python3 "${CLAUDE_PLUGIN_ROOT}/toolkit/lib/idmc_runtime_selections.py" --help`). Grep the lessons
   (`"domain": "agent"`) for every warning you see.
3. If the user can give host access, gather memory, heap, disk, DTM pool and concurrency per
   `${CLAUDE_PLUGIN_ROOT}/knowledge/02-secure-agent/01-secure-agent-install-run-tune.md` (sections 5-6) and
   `${CLAUDE_PLUGIN_ROOT}/knowledge/04-mappings/06-performance-concurrency-job-caps.md` (section 6.1).
4. Report: one table per agent (status, engines, services selected but unused, risks), then the recommendations in
   order of impact, each with its lesson id and how to measure the gain.
5. Change nothing until the user says yes; then change one thing at a time and re-measure.
