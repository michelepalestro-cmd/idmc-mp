---
name: idmc-ipu
description: Use for Informatica IDMC IPU and cost questions: how IPUs are metered, consumption exports and reports, entitlement and licences, monthly job caps, and estimating or reducing IPU use of a pipeline.
---

# IDMC co-pilot: IPU consumption, metering, licences and job caps

Part of the **idmc-mp** plugin (the IDMC co-pilot). Paths are relative to the plugin root, `${CLAUDE_PLUGIN_ROOT}`
(two folders above this skill's folder). Use `python3` (on Windows `python` or `py`).

## Ground rules (from the core `idmc-mp` skill; they always apply)
- **Lessons first.** Before any call or design choice, search the lessons:
  `grep -i "<thing or error>" "${CLAUDE_PLUGIN_ROOT}/lessons/lessons.jsonl"` (this area: `"domain": "ipu-licensing"`),
  then `lessons/by-domain/11-ipu-metering-licensing.md` and the user's own `~/.idmc_toolkit/lessons-local.jsonl`.
- **Prove the org first.** `python3 "${CLAUDE_PLUGIN_ROOT}/toolkit/check_login.py"` (one login attempt per run: retries
  lock the account). Take every host from `products[].baseApiUrl`; never hand-build a pod URL.
- **The user's systems are the right systems.** Never steer to another technology; ask if none is named.
- **Never say "not possible"** before the workaround ladder in
  `knowledge/00-start-here/08-new-pipeline-milestones-any-source-any-target.md` is worked in this org.
- **Writes are dry runs** until the org guard passes (`--execute --expect-org <orgIdV3>`); say what will change first.
- **Evidence, not claims:** finish with ids, row counts, job states or the API answer that proves the result
  (`knowledge/14-claude-working-methods/02-evidence-discipline.md`).

## What users ask for
- How many IPUs did we use this month, and on what?
- What will this pipeline cost, and how do we lower it?
- Are we near a job cap?

## How to work
1. Read consumption with the metering export (doc 02); if billed IPU reads 0, use the labelled proxy (section 5).
2. Entitlement from `agentEngines[]`, never `products[]` (doc 03); job caps are a separate ledger.
3. Estimate with the IPU model (doc 01) and the IICS-to-IPUs reference; reduce via fewer, larger jobs (CDI doc 07).

## Read (in this order when unsure)
| Need | File |
|---|---|
| IPU model | `knowledge/11-ipu-metering-licensing/01-ipu-model-mechanics.md` |
| Metering and consumption exports | `knowledge/11-ipu-metering-licensing/02-metering-consumption-exports.md` |
| Entitlement, licences, job caps | `knowledge/11-ipu-metering-licensing/03-entitlement-licenses-job-caps.md` |
| IICS to IPUs reference | `knowledge/12-reference-library/iics-to-ipus-kb/README.md` |

## Tools (`--help` on each)
- `toolkit/lib/idmc_session.py`: metering and activity-log reads

## When you learn something
Append a generic lesson (no org ids, hosts, people or secrets; same shape as `lessons/lessons.jsonl`) to
`~/.idmc_toolkit/lessons-local.jsonl`, or run `/idmc-mp:save-lesson`. Never write inside the plugin folder.
