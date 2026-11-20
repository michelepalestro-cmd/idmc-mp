# Deploy, promote, migrate and clean up: cheat sheet

Moving IDMC design objects between projects, environments or orgs (export, edit, import, clone), cutting over and
rolling back, and deleting headless; applies to any promotion, org-to-org move, clone of an object with no create verb,
or cleanup.

**Start with:** `/idmc-mp:promote` (skill `idmc-deploy`) and
[01 Export & Import](01-export-import-v3-migration-api.md); for a whole org move, the
[04 Org-to-Org Runbook](04-org-to-org-migration-runbook.md). Prove the org first (`toolkit/check_login.py`).

## What works (headless)

| Task | How (exact route / tool / command) | Lesson |
|---|---|---|
| Inventory | `GET /public/core/v3/objects?limit=200&skip=<n>` until `skip` reaches `count` (`idmc_objects.py list`, `census`) | L-MIG-035 |
| Dependency closure | `GET /public/core/v3/objects/<frsGuid>/references?refType=uses` / `usedBy` (`idmc_objects.py refs`) | L-MIG-034 |
| Export | `POST /public/core/v3/export` `{"name","objects":[{"id":"<frsGuid>","includeDependencies":true}]}` -> poll `GET /export/<id>` -> `GET /export/<id>/package` (`idmc_export_import.py export`) | L-MIG-003 |
| Upload (staged, not committed) | `POST /public/core/v3/import/package`, `multipart/form-data`, part `package` -> `jobId`, `checksumValid` | L-MIG-008 |
| Start import | `POST /public/core/v3/import/<jobId>` `{"importSpecification":{"defaultConflictResolution":"REUSE"}}`; poll; `?expand=objects`; `/log` | L-MIG-010, L-MIG-011 |
| Edit a package offline | `idmc_package_edit.py inspect / verify / sub / drop / remap` (dry run, then `--execute`) | L-MIG-019 |
| Re-point a package to another org (connections, runtime environments, org ids) | Edit every file, nested zips too, then re-hash (`idmc_package_edit.py remap` / `sub`) | L-MIG-082 |
| Check the target's connections and runtimes before import | `GET /api/v2/connection/name/<url-encoded name>`, `GET /api/v2/runtimeEnvironment/name/<name>` (the import dry run prints EXISTS / MISSING) | L-MIG-103 (reported) |
| Author an object with no create verb | Migration-clone: export a same-type object, new name + fresh 22-char GUID, re-hash, import (free, no IPU) | L-MIG-023, L-MIG-077 |
| Retarget a mapping task | Re-import its mapping with `OVERWRITE` under the same GUID | L-MIG-030 |
| Re-tag after import | `POST /public/core/v3/TagObjects` (<= 50 items per call), read back | L-MIG-016 |
| Move / copy objects, ids kept | FRS `POST .../frs/api/v1/MoveEntities` / `CopyEntities` (omit `conflictResolution`) | L-MIG-054, L-MIG-087 |
| Rename in place | `PATCH .../frs/api/v1/Documents('<frsId>')` `{"name"}` (not `BaseEntities`) | L-MIG-075 |
| Unbind / bind schedules | v2 idiom: `GET /api/v2/workflow/<id>`, POST the full body back with `scheduleId`, read back | L-MIG-047 |
| Delete | v2 `DELETE /api/v2/<resource>/<id>` (read-back 403); FRS `DeleteEntities {"artifactIds"}` / `BaseEntities('<id>')` (`idmc_frs_delete.py`) | L-CLEAN-006, L-CLEAN-003, L-CLEAN-005 |
| Delete a user | `DELETE /public/core/v3/users/<id>` -> 204 | L-CLEAN-009 |
| CAI unpublish before delete | `POST <pod>-cai/active-bpel/asset/v1/unpublish`, processes -> app connections -> connectors | L-CLEAN-011 |

## What doesn't work, and the workaround

| Wall | Workaround | Lesson |
|---|---|---|
| v3 objects is read-only (POST 405, PATCH 404) | Create and change through import | L-MIG-001 |
| One object failing validation fails the whole import (every object rolled back); `includeObjects` does not skip validation | Drop the failing object from the package (`idmc_package_edit.py drop`). Treat any end state but `SUCCESSFUL` (including a documented `PARTIAL`) as not promoted | L-MIG-012 |
| `objectSpecification` -> `V3API_007` in every shape tried | Name-based `REUSE`, or edit the package | L-MIG-013 |
| Package carries no secrets, agents, selections, schedules, tags, CDGC content, CAI publish, DBMI deploy | Set secrets + test, selections, schedules unbound then bind, TagObjects, publish, deploy (runbook M2-M8) | L-MIG-017, L-MIG-024 |
| Hosted runtime name reserved (`REPO_38210`) | Remap to a self-hosted runtime inside the package | L-MIG-015 |
| Add-On Bundle template tasks do not migrate (`MigrationSvc_031`) | Rebuild as user mappings or use the target's copy; check for objects with no file first | L-MIG-083 |
| `TOOL_CONNECTION` import fails `MigrationSvc_031` | Recreate in the CAI designer (preview orgs only) | L-MIG-039 |
| CDGC catalog-source REST delete only purges | Delete the definition in Metadata Command Center | L-CLEAN-015 |
| CAI assets stuck (duplicate runtime rows, `FRS_082`) | Vendor support or a UI attempt; list them in the report | L-CLEAN-012 |
| No source-control unlink endpoint | Decide the scope first; pilot on one project | L-MIG-098 |

## Fastest safe path

1. Prove both orgs, one login file each (`IDMC_CREDS_FILE`). Read-back: each org id written down.
2. Inventory + closure in the source, read-only. Read-back: counts by type, 0 missing references (L-MIG-045).
3. Export with dependencies; store the zip 0600 outside the repo (L-MIG-018). Read-back: `SUCCESSFUL`, file count.
4. Edit offline (connections, runtime, names), then `verify`. Read-back: upload answers `checksumValid:true` (L-MIG-019).
5. Target foundation first: agent, selections, connections + secrets. Read-back: N/N connection tests 200 (L-MIG-045).
6. Dry-run the import with `--expect-org <target orgIdV3>` (so the preview reads the right org): NEW vs EXISTS, and every
   connection and runtime EXISTS in the target. Get the user's yes, then `--execute --expect-org <target orgIdV3>`.
   Read-back: import `SUCCESSFUL`, created/reused counts; compare reused pairs that may be older (L-MIG-011). On a poll
   timeout, read the job back with `status`; never import again (L-MIG-132).
   Then compare each connection's host and database in the target with the prod values: a connection test can pass
   against a dev host the prod agent can reach (L-MIG-082).
7. Build the id map from objects this import created (`targetObject.id` comes back null) (L-MIG-036). Re-tag.
8. Publish CAI, deploy DBMI (not started), re-bind DQ. Read-back: N/N published, task `deployed`.
9. Validate: retarget runs to shadow datasets, one run per lane, exact counts (L-MIG-046).
10. Cutover on an explicit GO with the rollback written first; then scan both orgs for task-level schedules (L-MIG-049,
    L-MIG-048).

## Top traps

- 403 `MigrationSvc_038` -> migration role missing (or bundle content) -> grant the role, skip bundle content (L-MIG-006).
- 400 `V3API_007` on export -> bare string ids, a `type` key, or root-level `includeDependencies` -> `[{"id","includeDependencies":true}]` (L-MIG-004, L-MIG-124 (reported)).
- 400 `MigrationSvc_034` -> a process GUID or CDGC object, not a v3 `frsGuid` -> use the id from `/objects` (L-MIG-007).
- 404 `MigrationSvc_025` on upload -> JSON sent -> `multipart/form-data`; start route has no `/package` segment (L-MIG-009, L-MIG-010).
- `MigrationSvc_073` -> a changed file (often `exportMetadata.v2.json`) not re-hashed -> upper-case SHA-256 per changed file (L-MIG-019).
- `MigrationSvc_031` with empty details -> dangling `objectRefs`; never add a ref to a connection the package lacks (L-MIG-020).
- `OIE_007` on an MTT clone -> v2 id written into `runtimeEnvironmentId` -> keep the `@<FRS id>` form (L-MIG-100).
- Clone overwrote its template -> source GUIDs still in the package -> fresh GUIDs everywhere, nested zips too (L-MIG-077).
- Validation wrote production tables -> imported tasks keep original targets -> retarget first (L-MIG-046).
- Old org ran a task after cutover -> task-level `scheduleId` survived a workflow-only unbind -> scan every task detail (L-MIG-048).
- `REPO_52013` / `REPO_10242` on delete -> task has its own schedule / connection used by mappings (L-CLEAN-008, L-CLEAN-007).
- Rejected or interrupted delete call -> may have run (68 FRS deletes landed) -> read back, report real state (L-CLEAN-017).
- "Unused" verdict -> select by id from a keep list, never by name or "in no taskflow"; scan config files (L-CLEAN-020, L-CLEAN-025, L-CLEAN-034).
- Source-controlled project -> `OVERWRITE` needs checkout, import, check-in (L-MIG-096).
- Import poll timed out -> the job may still commit -> `status <jobId>`, never a second import (L-MIG-132).

## Go deeper

- [01 Export & Import](01-export-import-v3-migration-api.md): routes, REUSE/OVERWRITE, what a package omits, every `MigrationSvc_*` code, Git path.
- [02 Editing Packages Safely](02-editing-packages-safely.md): package anatomy, the three consistency rules, worked edits.
- [03 Migration-Clone Authoring](03-migration-clone-authoring.md): clone recipe per type, empty orgs, the survival gate.
- [04 Org-to-Org Runbook](04-org-to-org-migration-runbook.md): roles, phases M0-M13 with evidence and undo, validation.
- [05 Cutover & Rollback](05-cutover-rollback.md): the seven-step cutover, per-step rollback, soak and vendor case.
- [06 Headless Deletes & Cleanup](06-headless-deletes-org-cleanup.md): delete surface, order, never-delete list, safety laws.
- [Lessons: Migration & Org Management](lessons.md) (L-MIG-*, L-CLEAN-*; skip the superseded section).
