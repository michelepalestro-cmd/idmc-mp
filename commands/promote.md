---
description: Promote IDMC assets between orgs or environments (dev -> test -> prod) with export, edit, import and validation
argument-hint: "<project or assets> from <source org> to <target org>"
---

Use the idmc-mp and idmc-deploy skills. On Windows, use `python` (or `py`) where these steps say `python3`.
Promote: $ARGUMENTS

1. Prove BOTH orgs (one login file per org, `IDMC_CREDS_FILE`); write down each org id. Never retry a failed login.
2. Inventory and dependency closure in the source org, read-only (`toolkit/lib/idmc_objects.py`).
3. Export (`toolkit/lib/idmc_export_import.py`), then edit the package offline for the target: connections, runtime
   environment, names (`toolkit/lib/idmc_package_edit.py`, rules in
   `${CLAUDE_PLUGIN_ROOT}/knowledge/10-migration-org-management/02-editing-packages-safely.md`).
4. Check the target has the foundation first (agent, runtime, services, connections and secrets), per
   `${CLAUDE_PLUGIN_ROOT}/knowledge/10-migration-org-management/04-org-to-org-migration-runbook.md`.
5. Dry-run, show the user what will change, and import only on their yes with `--expect-org <target orgIdV3>`.
6. Validate in the target: objects present, connections test, one run with row counts. Keep the rollback kit
   (`05-cutover-rollback.md`) ready and report it.
