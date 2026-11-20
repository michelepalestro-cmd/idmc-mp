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
   `${CLAUDE_PLUGIN_ROOT}/knowledge/12-deploy-migrate/02-editing-packages-safely.md`; the full re-point recipe is lesson
   L-MIG-082).
4. Check the target has the foundation first (agent, runtime, services, connections and secrets), per
   `${CLAUDE_PLUGIN_ROOT}/knowledge/12-deploy-migrate/04-org-to-org-migration-runbook.md`.
5. Dry-run against the target WITH `--expect-org <target orgIdV3>`, so the preview is proven to read the target and not
   dev: `python3 "${CLAUDE_PLUGIN_ROOT}/toolkit/lib/idmc_export_import.py" import <pkg.zip> --mode REUSE --expect-org <target orgIdV3>`.
   Every connection and runtime environment must show `EXISTS`; a `MISSING` one is created first (step 4). Show the
   user what will change, and import only on their yes with `--execute --expect-org <target orgIdV3>`.
6. The import must end `SUCCESSFUL` (the tool exits 1 otherwise). On a poll timeout, read it back with
   `idmc_export_import.py status <jobId> --kind import`; never start a second import (L-MIG-132).
7. Prove nothing points at dev: for each connection the imported objects use, read it in the target
   (`GET /api/v2/connection/name/<url-encoded name>`) and compare its host, database and user with the prod values the
   user gave you, field by field. A connection test can pass against a dev host the prod agent can reach.
8. Validate in the target: objects present, connections test, one run with row counts. Keep the rollback kit
   (`05-cutover-rollback.md`) ready and report it.
