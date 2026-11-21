---
name: idmc-mdm
description: Use for Informatica IDMC MDM SaaS / Business 360: model business entities, match and merge rules, ingest, search, export and clean up records, golden records, and mastering a table end to end. Also for a single customer view, de-duplicating customers or other entities, and customer ids across systems.
---

# IDMC co-pilot: Master data management (MDM SaaS, Business 360)

Part of the **informatica-idmc-headless** plugin (the IDMC co-pilot). Paths are relative to the plugin root, `${CLAUDE_PLUGIN_ROOT}`
(two folders above this skill's folder). Use `python3` (on Windows `python` or `py`).

## Ground rules (from the core `informatica-idmc-headless` skill; they always apply)
- **Lessons first.** Before any call or design choice, search the lessons:
  `grep -i "<thing or error>" "${CLAUDE_PLUGIN_ROOT}/knowledge/lessons/lessons.jsonl"` (this area: `"domain": "mdm"`),
  then `knowledge/10-mdm/lessons.md` and the user's own `~/.idmc_toolkit/lessons-local.jsonl`.
- **Prove the org first.** `python3 "${CLAUDE_PLUGIN_ROOT}/toolkit/check_login.py"` (one login attempt per run: retries
  lock the account). Take every host from `products[].baseApiUrl`; never hand-build a pod URL.
- **The user's systems are the right systems.** Never steer to another technology; ask if none is named.
- **Never say "not possible"** before the workaround ladder in
  `knowledge/00-start-here/08-new-pipeline-milestones-any-source-any-target.md` is worked in this org.
- **Writes are dry runs** until the org guard passes (`--execute --expect-org <orgIdV3>`); say what will change first.
- **Evidence, not claims:** finish with ids, row counts, job states or the API answer that proves the result
  (`knowledge/14-working-with-claude/02-evidence-discipline.md`).

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
| **Start here:** the cheat sheet (what works, what doesn't, fastest path, traps) | `knowledge/10-mdm/README.md` |
| Runtime vs design | `knowledge/10-mdm/01-mdm-saas-runtime-vs-design.md` |
| Records: ingest, search, export, cleanup | `knowledge/10-mdm/02-mdm-records-ingest-search-export-cleanup.md` |
| Business 360 modeling and match-merge | `knowledge/10-mdm/03-business-360-modeling-match-merge.md` |
| P360 vs MDM SaaS, licensing | `knowledge/10-mdm/04-p360-vs-mdm-saas-licensing-notes.md` |
| Mastering a table: repeatable playbook | `knowledge/10-mdm/05-mastering-a-table-repeatable-playbook.md` |

## Tools (`--help` on each)
- `toolkit/lib/idmc_session.py`: the org-aware login and org proof. Its command line only runs GETs, and it has no
  `mdm` plane: `Session().hosts()["mdm"]` gives the `<pod>-mdm` host, but MDM search, ingest and delete calls (POST,
  DELETE) are hand-built in Python with the headers `knowledge/10-mdm/02-mdm-records-ingest-search-export-cleanup.md`
  lists (Bearer JWT from `Session().jwt()`, IDS-SESSION-ID, X-INFA-ORG-ID). Gate every write like the other tools: a
  dry run that prints the call first, then `--execute` only after `--expect-org` matches (`idmc_http.WriteGate`).
- MCP tools, when `/informatica-idmc-headless:connect-mcp` has connected the org's servers (`mcp__plugin_informatica-idmc-headless_idmc__*`): `cust_*` (fuzzy customer
  search, golden record, related records; needs MDM)
- No MDM licence: `toolkit/demos/customer_master_csv/` (clean, deduplicate, customer ids with plain CDI mappings)

## When you learn something
Append a generic lesson (no org ids, hosts, people or secrets; same shape as `knowledge/lessons/lessons.jsonl`) to
`~/.idmc_toolkit/lessons-local.jsonl`, or run `/informatica-idmc-headless:save-lesson`. Never write inside the plugin folder.
