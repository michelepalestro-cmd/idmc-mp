---
name: idmc-governance
description: Use for Informatica IDMC Cloud Data Governance and Catalog (CDGC): create and scan catalog sources, glossary domains and terms, links and classifications, search, lineage and the data marketplace, CDGC auth (JWT), and CDGC gaps. Also for a data catalog, data lineage, a business glossary, data classification or data governance in Informatica.
---

# IDMC co-pilot: Data governance and catalog (CDGC)

Part of the **idmc-mp** plugin (the IDMC co-pilot). Paths are relative to the plugin root, `${CLAUDE_PLUGIN_ROOT}`
(two folders above this skill's folder). Use `python3` (on Windows `python` or `py`).

## Ground rules (from the core `idmc-mp` skill; they always apply)
- **Lessons first.** Before any call or design choice, search the lessons:
  `grep -i "<thing or error>" "${CLAUDE_PLUGIN_ROOT}/knowledge/lessons/lessons.jsonl"` (this area: `"domain": "cdgc"`),
  then `knowledge/09-catalog-lineage/lessons.md` and the user's own `~/.idmc_toolkit/lessons-local.jsonl`.
- **Prove the org first.** `python3 "${CLAUDE_PLUGIN_ROOT}/toolkit/check_login.py"` (one login attempt per run: retries
  lock the account). Take every host from `products[].baseApiUrl`; never hand-build a pod URL.
- **The user's systems are the right systems.** Never steer to another technology; ask if none is named.
- **Never say "not possible"** before the workaround ladder in
  `knowledge/00-start-here/08-new-pipeline-milestones-any-source-any-target.md` is worked in this org.
- **Writes are dry runs** until the org guard passes (`--execute --expect-org <orgIdV3>`); say what will change first.
- **Evidence, not claims:** finish with ids, row counts, job states or the API answer that proves the result
  (`knowledge/14-working-with-claude/02-evidence-discipline.md`).

## What users ask for
- Scan the user's sources into the catalog and show lineage to the report.
- Load a business glossary and link terms to assets.
- Find assets and classifications by search.

## How to work
1. Auth: CDGC uses its own token (doc 01); check it with `toolkit/lib/idmc_cdgc.py`.
2. Catalog source: clone a working source definition, then scan and poll (doc 02).
3. Glossary, links, classification (doc 03); search and lineage (doc 04).
4. Before saying it cannot be done: read the gaps doc (05) and work the ladder.

## Read (in this order when unsure)
| Need | File |
|---|---|
| **Start here:** the cheat sheet (what works, what doesn't, fastest path, traps) | `knowledge/09-catalog-lineage/README.md` |
| APIs and auth | `knowledge/09-catalog-lineage/01-cdgc-apis-auth.md` |
| Catalog sources: create, scan, update, purge | `knowledge/09-catalog-lineage/02-catalog-sources-create-scan-update-purge.md` |
| Glossary, links, classification | `knowledge/09-catalog-lineage/03-glossary-links-classification.md` |
| Search, lineage, marketplace | `knowledge/09-catalog-lineage/04-search-lineage-marketplace.md` |
| Gaps and gotchas | `knowledge/09-catalog-lineage/05-cdgc-gaps-gotchas.md` |

## Tools (`--help` on each)
- `toolkit/lib/idmc_cdgc.py`: CDGC: token check, catalog sources, scans, glossary, links, search

## When you learn something
Append a generic lesson (no org ids, hosts, people or secrets; same shape as `knowledge/lessons/lessons.jsonl`) to
`~/.idmc_toolkit/lessons-local.jsonl`, or run `/idmc-mp:save-lesson`. Never write inside the plugin folder.
