---
description: Diagnose an IDMC error: lessons first, then triage in your org
argument-hint: "<error message or symptom>"
---

Use the idmc-mp skill. On Windows, use `python` (or `py`) where these steps say `python3`. The user hit: $ARGUMENTS

1. Search the lessons for the exact signature first: `grep -i "<code or phrase>" "${CLAUDE_PLUGIN_ROOT}/lessons/lessons.jsonl"`,
   then `${CLAUDE_PLUGIN_ROOT}/knowledge/reference/playbook/06-lessons-field.md`, then `~/.idmc_toolkit/lessons-local.jsonl` if it exists. Prefer
   `current` lessons, and check `${CLAUDE_PLUGIN_ROOT}/lessons/overturned-beliefs.md` before quoting a wall.
2. If no lesson matches, run the five checks in `${CLAUDE_PLUGIN_ROOT}/knowledge/00-start-here/04-error-triage.md` against the org,
   read-only first.
3. Answer briefly: the cause, the fix, how to verify it, and the lesson id(s). If you fixed it, read back to prove
   it. If it was new, offer `/idmc-mp:save-lesson`.
