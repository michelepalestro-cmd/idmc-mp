---
description: Save something you learned about IDMC as a reusable lesson on your machine
argument-hint: "<what you learned>"
---

Use the idmc-mp skill. Save this as a lesson: $ARGUMENTS

1. Check it is new: grep `${CLAUDE_PLUGIN_ROOT}/skills/idmc-mp/kb/13 - Lessons Learned/lessons.jsonl` and `~/.idmc_toolkit/lessons-local.jsonl`.
   If it repeats a lesson, say which one and stop. If it adds to one, note `Refines <id>`.
2. Write it in generic form: no org ids, hosts, pod names, people, customer names, emails or secrets (use `<org>`,
   `<pod>`, `<host>`, `<connection>`). Include the exact verb, path, setting or error code, the cause, the fix and how
   to verify it.
3. Append one JSON line to `~/.idmc_toolkit/lessons-local.jsonl` (create the folder if needed) with the fields `id`
   (`L-LOCAL-<n>`), `domain`, `kind`, `title`, `text`, `evidence`, `date`, `status` ("current") and `supersedes_id` ("").
   Never write into the plugin folder: it is replaced on every update.
4. Show the saved lesson, and tell the user they can share it with everyone through an issue or pull request on the
   plugin's GitHub repo.
