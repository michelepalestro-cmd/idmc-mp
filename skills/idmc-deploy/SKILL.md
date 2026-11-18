---
name: idmc-deploy
description: Use to deploy or promote Informatica IDMC assets between orgs or environments (dev to test to prod), export/import packages with the v3 migration API, edit packages safely, run an org-to-org migration with cutover and rollback, and clean up an org headless.
---

# IDMC co-pilot: Deploy, promote and migrate (CI/CD, org to org, cleanup)

Part of the **idmc-mp** plugin (the IDMC co-pilot). Paths are relative to the plugin root, `${CLAUDE_PLUGIN_ROOT}`
(two folders above this skill's folder). Use `python3` (on Windows `python` or `py`).

## Ground rules (from the core `idmc-mp` skill; they always apply)
- **Lessons first.** Before any call or design choice, search the lessons:
  `grep -i "<thing or error>" "${CLAUDE_PLUGIN_ROOT}/lessons/lessons.jsonl"` (this area: `"domain": "migration"`, `"domain": "org-cleanup"`),
  then `lessons/by-domain/10-migration-org-management.md` and the user's own `~/.idmc_toolkit/lessons-local.jsonl`.
- **Prove the org first.** `python3 "${CLAUDE_PLUGIN_ROOT}/toolkit/check_login.py"` (one login attempt per run: retries
  lock the account). Take every host from `products[].baseApiUrl`; never hand-build a pod URL.
- **The user's systems are the right systems.** Never steer to another technology; ask if none is named.
- **Never say "not possible"** before the workaround ladder in
  `knowledge/00-start-here/08-new-pipeline-milestones-any-source-any-target.md` is worked in this org.
- **Writes are dry runs** until the org guard passes (`--execute --expect-org <orgIdV3>`); say what will change first.
- **Evidence, not claims:** finish with ids, row counts, job states or the API answer that proves the result
  (`knowledge/14-claude-working-methods/02-evidence-discipline.md`).

## What users ask for
- Promote a project from dev to prod, repeatably.
- Migrate one org to another with a rollback plan.
- Clean up old assets safely.

## How to work
1. Inventory and dependency closure first (`toolkit/lib/idmc_objects.py`, runbook phase M1).
2. Export -> edit offline (connections, runtime, names) -> import with `idmc_export_import.py` and `idmc_package_edit.py`.
3. Order: foundation, connections and secrets, import, CAI, CDC, DQ, catalog, then validation (runbook M0-M10).
4. Cutover and rollback per doc 05; deletes leaf-first with `idmc_frs_delete.py` and KEEP guards (doc 06).
5. For a whole first deployment, follow the 13-stage end-to-end playbook and its post-mortem checks.

## Read (in this order when unsure)
| Need | File |
|---|---|
| Export and import (v3 migration API) | `knowledge/10-migration-org-management/01-export-import-v3-migration-api.md` |
| Editing packages safely | `knowledge/10-migration-org-management/02-editing-packages-safely.md` |
| Migration-clone authoring | `knowledge/10-migration-org-management/03-migration-clone-authoring.md` |
| Org-to-org migration runbook | `knowledge/10-migration-org-management/04-org-to-org-migration-runbook.md` |
| Cutover and rollback | `knowledge/10-migration-org-management/05-cutover-rollback.md` |
| Headless deletes and org cleanup | `knowledge/10-migration-org-management/06-headless-deletes-org-cleanup.md` |
| End-to-end playbook (13 stages) | `knowledge/00-start-here/07-end-to-end-playbook-deploy-and-operate-idmc-with-claude.md` |
| Production post-mortem: checks that catch each failure | `knowledge/00-start-here/09-what-went-wrong-production-deployment-post-mortem.md` |

## Tools (`--help` on each)
- `toolkit/lib/idmc_objects.py`: read-only inventory and references
- `toolkit/lib/idmc_export_import.py`: export, poll, download, import
- `toolkit/lib/idmc_package_edit.py`: edit a package offline and keep it importable
- `toolkit/lib/idmc_frs_delete.py`: dependency-checked, leaf-first deletes

## When you learn something
Append a generic lesson (no org ids, hosts, people or secrets; same shape as `lessons/lessons.jsonl`) to
`~/.idmc_toolkit/lessons-local.jsonl`, or run `/idmc-mp:save-lesson`. Never write inside the plugin folder.
