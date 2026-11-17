---
description: Diagnose an IDMC error: lessons first, then triage in your org
argument-hint: "<error message or symptom>"
---

Use the idmc-mp skill. The user hit: $ARGUMENTS

1. Search the lessons for the exact signature first: `grep -i "<code or phrase>" "${CLAUDE_PLUGIN_ROOT}/skills/idmc-mp/kb/13 - Lessons Learned/lessons.jsonl"`,
   then `${CLAUDE_PLUGIN_ROOT}/skills/idmc-mp/references/06-lessons-field.md`, then `~/.idmc_toolkit/lessons-local.jsonl` if it exists. Prefer
   `current` lessons, and check `Overturned Beliefs.md` before quoting a wall.
2. If no lesson matches, run the five checks in `${CLAUDE_PLUGIN_ROOT}/skills/idmc-mp/kb/00 - Start Here/04 Error Triage.md` against the org,
   read-only first.
3. Answer briefly: the cause, the fix, how to verify it, and the lesson id(s). If you fixed it, read back to prove
   it. If it was new, offer `/idmc-mp:save-lesson`.
