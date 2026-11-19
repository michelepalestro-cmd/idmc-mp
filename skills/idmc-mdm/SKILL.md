---
name: idmc-mdm
description: Use for Informatica IDMC MDM SaaS / Business 360: model business entities, match and merge rules, ingest, search, export and clean up records, golden records, and mastering a table end to end.
---

# IDMC co-pilot: Master data management (MDM SaaS, Business 360)

Part of the **idmc-mp** plugin (the IDMC co-pilot). Paths are relative to the plugin root, `${CLAUDE_PLUGIN_ROOT}`
(two folders above this skill's folder). Use `python3` (on Windows `python` or `py`).

## Ground rules (from the core `idmc-mp` skill; they always apply)
- **Lessons first.** Before any call or design choice, search the lessons:
  `grep -i "<thing or error>" "${CLAUDE_PLUGIN_ROOT}/lessons/lessons.jsonl"` (this area: `"domain": "mdm"`),
  then `lessons/by-domain/08-mdm.md` and the user's own `~/.idmc_toolkit/lessons-local.jsonl`.
- **Prove the org first.** `python3 "${CLAUDE_PLUGIN_ROOT}/toolkit/check_login.py"` (one login attempt per run: retries
  lock the account). Take every host from `products[].baseApiUrl`; never hand-build a pod URL.
- **The user's systems are the right systems.** Never steer to another technology; ask if none is named.
- **Never say "not possible"** before the workaround ladder in
  `knowledge/00-start-here/08-new-pipeline-milestones-any-source-any-target.md` is worked in this org.
- **Writes are dry runs** until the org guard passes (`--execute --expect-org <orgIdV3>`); say what will change first.
- **Evidence, not claims:** finish with ids, row counts, job states or the API answer that proves the result
  (`knowledge/14-claude-working-methods/02-evidence-discipline.md`).

## What users ask for
- Master a table into golden records.
- Load, search and export MDM records headless.
- Tune match and merge.

## How to work
1. Know which plane does what (doc 01: runtime vs design).
2. Model and match-merge (doc 03); follow the repeatable playbook for the dataset type (doc 05).
3. Ingest, search, export and clean up records (doc 02); prove counts before and after merge.

## Read (in this order when unsure)
| Need | File |
|---|---|
| Runtime vs design | `knowledge/08-mdm/01-mdm-saas-runtime-vs-design.md` |
| Records: ingest, search, export, cleanup | `knowledge/08-mdm/02-mdm-records-ingest-search-export-cleanup.md` |
| Business 360 modeling and match-merge | `knowledge/08-mdm/03-business-360-modeling-match-merge.md` |
| P360 vs MDM SaaS, licensing | `knowledge/08-mdm/04-p360-vs-mdm-saas-licensing-notes.md` |
| Mastering a table: repeatable playbook | `knowledge/08-mdm/05-mastering-a-table-repeatable-playbook.md` |

## Tools (`--help` on each)
- `toolkit/lib/idmc_session.py`: MDM calls go through the org-aware session

## When you learn something
Append a generic lesson (no org ids, hosts, people or secrets; same shape as `lessons/lessons.jsonl`) to
`~/.idmc_toolkit/lessons-local.jsonl`, or run `/idmc-mp:save-lesson`. Never write inside the plugin folder.
