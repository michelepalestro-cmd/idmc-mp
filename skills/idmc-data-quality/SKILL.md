---
name: idmc-data-quality
description: Use for Informatica IDMC Data Quality and profiling: profile a table, suggest and build DQ rule specifications, cleanse/parse/dictionary/deduplicate assets, run rules inside CDI pipelines, DQ scores and scorecards, and the CLAIRE DQ agent. Also for cleaning data, finding duplicates, validating or standardizing records (names, e-mails, phones, addresses).
---

# IDMC co-pilot: Data quality and profiling (CDQ)

Part of the **informatica-idmc-headless** plugin (the IDMC co-pilot). Paths are relative to the plugin root, `${CLAUDE_PLUGIN_ROOT}`
(two folders above this skill's folder). Use `python3` (on Windows `python` or `py`).

## Ground rules (from the core `informatica-idmc-headless` skill; they always apply)
- **Lessons first.** Before any call or design choice, search the lessons:
  `grep -i "<thing or error>" "${CLAUDE_PLUGIN_ROOT}/knowledge/lessons/lessons.jsonl"` (this area: `"domain": "dq-profiling"`),
  then `knowledge/08-data-quality/lessons.md` and the user's own `~/.idmc_toolkit/lessons-local.jsonl`.
- **Prove the org first.** `python3 "${CLAUDE_PLUGIN_ROOT}/toolkit/check_login.py"` (one login attempt per run: retries
  lock the account). Take every host from `products[].baseApiUrl`; never hand-build a pod URL.
- **The user's systems are the right systems.** Never steer to another technology; ask if none is named.
- **Never say "not possible"** before the workaround ladder in
  `knowledge/00-start-here/08-new-pipeline-milestones-any-source-any-target.md` is worked in this org.
- **Writes are dry runs** until the org guard passes (`--execute --expect-org <orgIdV3>`); say what will change first.
- **Evidence, not claims:** finish with ids, row counts, job states or the API answer that proves the result
  (`knowledge/14-working-with-claude/02-evidence-discipline.md`).

## What users ask for
- Profile a table and propose DQ rules for it.
- Put the rules into the pipeline and score the data.
- Publish a DQ scorecard people can read.
- Clean a big table: standardize, find duplicates, pick survivors (`/informatica-idmc-headless:clean-data`).

## How to work
1. Profile (doc 02 says what is headless) and read the results.
2. Author rule specs by cloning a template (doc 01 section 3.3); dictionaries via the CDQ API (section 4).
3. Execute the rules inside a CDI mapping (DQ authors, CDI executes); prove pass/fail counts.
4. Scorecards with the warehouse pattern (doc 04).

## Read (in this order when unsure)
| Need | File |
|---|---|
| **Start here:** the cheat sheet (what works, what doesn't, fastest path, traps) | `knowledge/08-data-quality/README.md` |
| DQ assets: rule specs, cleanse, dictionaries, verifiers | `knowledge/08-data-quality/01-dq-assets-rule-specs-cleanse-dictionaries-verifiers.md` |
| Profiling: what is headless | `knowledge/08-data-quality/02-profiling-what-is-headless.md` |
| CLAIRE DQ agent | `knowledge/08-data-quality/03-claire-dq-agent-file-based-profiling-cleansing.md` |
| Scorecards | `knowledge/08-data-quality/04-dq-scorecards-warehouse-pattern-and-data-profiling-scorecards.md` |
| Clean a large table with mappings (match, survivors, twin proof) | `knowledge/08-data-quality/05-cleaning-a-large-dataset-with-mappings.md` |

## Tools (`--help` on each)
- `toolkit/mapgen/mapgen.py`: rule specs run inside generated mappings
- `toolkit/lib/idmc_objects.py`: read-only census of DQ assets
- MCP tools, when `/informatica-idmc-headless:connect-mcp` has connected the org's servers (`mcp__plugin_informatica-idmc-headless_idmc__*`): `dqagent_*` (CLAIRE DQ
  agent), `addr_verify_address` (one address per call), `dqscore_*` (catalog DQ scores)

## When you learn something
Append a generic lesson (no org ids, hosts, people or secrets; same shape as `knowledge/lessons/lessons.jsonl`) to
`~/.idmc_toolkit/lessons-local.jsonl`, or run `/informatica-idmc-headless:save-lesson`. Never write inside the plugin folder.
