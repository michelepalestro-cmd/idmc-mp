---
name: idmc-cdc
description: Use for Informatica IDMC Database Ingestion / Mass Ingestion and change data capture (CDC): create, deploy, run, stop and monitor DBMI tasks headless, CDC from PostgreSQL or other databases, targets and drivers, and CDC errors. Also for replicating a database or streaming its changes into a warehouse in near real time, and file ingestion.
---

# IDMC co-pilot: Mass Ingestion and CDC (DBMI)

Part of the **informatica-idmc-headless** plugin (the IDMC co-pilot). Paths are relative to the plugin root, `${CLAUDE_PLUGIN_ROOT}`
(two folders above this skill's folder). Use `python3` (on Windows `python` or `py`).

## Ground rules (from the core `informatica-idmc-headless` skill; they always apply)
- **Lessons first.** Before any call or design choice, search the lessons:
  `grep -i "<thing or error>" "${CLAUDE_PLUGIN_ROOT}/knowledge/lessons/lessons.jsonl"` (this area: `"domain": "dbmi-cdc"`),
  then `knowledge/06-cdc-ingestion/lessons.md` and the user's own `~/.idmc_toolkit/lessons-local.jsonl`.
- **Prove the org first.** `python3 "${CLAUDE_PLUGIN_ROOT}/toolkit/check_login.py"` (one login attempt per run: retries
  lock the account). Take every host from `products[].baseApiUrl`; never hand-build a pod URL.
- **The user's systems are the right systems.** Never steer to another technology; ask if none is named.
- **Never say "not possible"** before the workaround ladder in
  `knowledge/00-start-here/08-new-pipeline-milestones-any-source-any-target.md` is worked in this org.
- **Writes are dry runs** until the org guard passes (`--execute --expect-org <orgIdV3>`); say what will change first.
- **Evidence, not claims:** finish with ids, row counts, job states or the API answer that proves the result
  (`knowledge/14-working-with-claude/02-evidence-discipline.md`).

## What users ask for
- Land a database in the user's target with initial load plus CDC.
- Deploy, start, stop and monitor ingestion tasks without the UI.
- Fix a CDC task that will not deploy or run.

## How to work
1. Check the source's CDC prerequisites (e.g. PostgreSQL logical replication, doc 02) and the target driver (doc 03).
2. Create and deploy over REST on the ingestion plane with `toolkit/lib/idmc_dbmi.py` (doc 01).
3. Run, then prove: rows in the target and a change flowing end to end.
4. Errors: grep the lessons for the exact code before changing anything.

## Read (in this order when unsure)
| Need | File |
|---|---|
| **Start here:** the cheat sheet (what works, what doesn't, fastest path, traps) | `knowledge/06-cdc-ingestion/README.md` |
| DBMI over REST: create, deploy, run, stop | `knowledge/06-cdc-ingestion/01-dbmi-over-rest-create-deploy-run-stop.md` |
| CDC from PostgreSQL | `knowledge/06-cdc-ingestion/02-cdc-from-postgresql.md` |
| Targets and drivers | `knowledge/06-cdc-ingestion/03-dbmi-targets-drivers.md` |

## Tools (`--help` on each)
- `toolkit/lib/idmc_dbmi.py`: DBMI / CDC tasks on the ingestion plane

## When you learn something
Append a generic lesson (no org ids, hosts, people or secrets; same shape as `knowledge/lessons/lessons.jsonl`) to
`~/.idmc_toolkit/lessons-local.jsonl`, or run `/informatica-idmc-headless:save-lesson`. Never write inside the plugin folder.
