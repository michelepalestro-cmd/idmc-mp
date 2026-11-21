---
description: Diagnose an IDMC error: lessons first, then triage in your org
argument-hint: "<error message or symptom>"
---

Use the informatica-idmc-headless skill. On Windows, use `python` (or `py`) where these steps say `python3`. The user hit: $ARGUMENTS

1. Look up the exact signature: first `${CLAUDE_PLUGIN_ROOT}/knowledge/lessons/error-index.md` (error codes and messages),
   then `grep -i "<code or phrase>" "${CLAUDE_PLUGIN_ROOT}/knowledge/lessons/lessons.jsonl"`, then
   `~/.idmc_toolkit/lessons-local.jsonl` if it exists. Prefer
   `current` lessons, and check `${CLAUDE_PLUGIN_ROOT}/knowledge/lessons/overturned-beliefs.md` before quoting a wall.
2. If no lesson matches, run the five checks in `${CLAUDE_PLUGIN_ROOT}/knowledge/00-start-here/04-error-triage.md` against the org,
   read-only first.
3. Answer briefly: the cause, the fix, how to verify it, and the lesson id(s). If you fixed it, read back to prove
   it. If it was new, offer `/informatica-idmc-headless:save-lesson`.
