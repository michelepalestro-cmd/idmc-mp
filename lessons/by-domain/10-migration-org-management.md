# Lessons: Migration & Org Management
138 current lessons (1 of them disputed) and 17 superseded, IDs L-CLEAN-### and L-MIG-###; evidence dated 2026-07-04 to 2026-10-13. Every lesson is generic; its sources are mapped outside the generic zone.
Related: [Export & Import](../../knowledge/10-migration-org-management/01-export-import-v3-migration-api.md) · [Editing Packages Safely](../../knowledge/10-migration-org-management/02-editing-packages-safely.md) · [Migration-Clone Authoring](../../knowledge/10-migration-org-management/03-migration-clone-authoring.md) · [Org-to-Org Migration Runbook](../../knowledge/10-migration-org-management/04-org-to-org-migration-runbook.md) · [Cutover & Rollback](../../knowledge/10-migration-org-management/05-cutover-rollback.md) · [Headless Deletes & Org Cleanup](../../knowledge/10-migration-org-management/06-headless-deletes-org-cleanup.md)

## Current

### L-MIG-001  The v3 objects API is a read-only inventory; the migration import is the write path
**Kind:** LAW · **Proven:** 2026-07-25 · **Evidence:** 405 on POST and 404 on PATCH across orgs (2026-07-04 to 2026-07-25)
`GET /public/core/v3/objects` (paged with `limit` and `skip`, optionally `q=type=='<TYPE>'`) lists design objects; `POST /public/core/v3/objects` returns 405 'Method not supported' and a per-object PATCH returns 404. Create and change design objects through the v3 import (or a service's own create API where one exists, such as DBMI task/create), and use the objects list for inventory and read-back.

### L-MIG-002  The v3 type filter is not validated: a wrong type name returns 0, not an error
**Kind:** OVERTURNED · **Proven:** 2026-09-25 · **Evidence:** fabricated types returned identical envelopes (2026-07-25); 23 objects found under the right type (2026-09-24/25)
`GET /public/core/v3/objects?q=type=='<X>'` returns the same clean `{"count":0,"objects":[]}` for a fabricated type as for an empty real one; an audit that asked for `DBMI` instead of `DBMI_TASK` missed 23 objects. Use exact type names (for example MTT, MAPPING, DTEMPLATE, DBMI_TASK, MI_TASK, PROCESS, TASKFLOW, WORKFLOW, RULE_SPECIFICATION, PROFILE, TOOL_CONNECTION, MCP_SERVER), or list unfiltered and group client-side. Never read count 0 as proof that a capability is absent. Supersedes L-MIG-064.

### L-MIG-003  v3 export: start, poll, download
**Kind:** ROUTE · **Proven:** 2026-09-28 · **Evidence:** export SUCCESSFUL with 0 missing references across 223 objects (2026-09-28)
`POST https://<pod>.<domain>.informaticacloud.com/saas/public/core/v3/export` with header `INFA-SESSION-ID` and body `{"name":"<name>","objects":[{"id":"<frsGuid>","includeDependencies":true}]}` returns 200 with the export job `id`. Poll `GET /public/core/v3/export/<id>` (add `?expand=objects` for per-object state) until `status.state` is SUCCESSFUL ('Export completed successfully'), then download `GET /public/core/v3/export/<id>/package` with `Accept: application/zip`. An export is read-only for the source; a 194-object scope with dependencies gave 223 objects (a 616 KB zip) in about 20 s. Supersedes L-MIG-070.

### L-MIG-004  Export body shape errors: V3API_007 and an empty `objects[]`
**Kind:** ERROR · **Proven:** 2026-07-26 · **Evidence:** live 2026-07-26; bare string ids confirmed 2026-09-28
`objects[]` takes objects like `{"id":"..."}`; bare id strings, or an added `type` key, give 400 `V3API_007 Bad Request`. An empty `objects[]` gives 400, and `GET /public/core/v3/export` is 405.

### L-MIG-005  MigrationSvc_041 'No asset selected' is a content verdict, not a shape error
**Kind:** ERROR · **Proven:** 2026-07-26 · **Evidence:** live on an empty org (2026-07-26)
400 `MigrationSvc_041 'No asset selected for export operation'` means the body parsed and the named object contributes nothing exportable, for example an org whose only object is an empty default project. Pick another object; do not sweep body shapes against an endpoint that already accepted the request.

### L-MIG-006  403 MigrationSvc_038 is a role gap; for Add-On Bundle templates it is org- and user-dependent
**Kind:** ERROR · **Proven:** 2026-07-06 · **Evidence:** 403 before and 200 after the grant (2026-07-05/06); bundle 403 seen and not reproduced in different orgs (2026-09-22 to 2026-09-29)
403 `MigrationSvc_038 'User does not have required permissions'` on export means the user lacks the migration (export/import) role, while an empty-body POST returning 400 proves the route is writable. Granting the migration and object-admin roles in Administrator takes about a minute and is free. Exporting Add-On Bundle templates (for example `dsst__copy_data_new_tgt`, `dlt__copy_data`) can return the same 403 for a non-admin while user-owned objects export fine, and the result differed by org and date; do not depend on exporting bundle content (import with REUSE instead).

### L-MIG-007  MigrationSvc_034 'Object resolution failed': the wrong kind of id, or a CDGC governance object
**Kind:** ERROR · **Proven:** 2026-09-28 · **Evidence:** MigrationSvc_034 on both (2026-07-04 and 2026-09-28)
Export takes the IDMC object id from `/public/core/v3/objects`; passing a CAI process GUID read from inside the process XML gives 400 `MigrationSvc_034`. CDGC governance objects (classifications, stakeholders, assignments) are not carried by v3 migration and give the same error.

### L-MIG-008  v3 import upload: multipart/form-data with one part named `package`
**Kind:** ROUTE · **Proven:** 2026-09-28 · **Evidence:** uploads accepted with checksumValid true (2026-07-06 to 2026-09-29)
`POST /public/core/v3/import/package` with `Content-Type: multipart/form-data; boundary=<b>` and one part `Content-Disposition: form-data; name="package"; filename="pkg.zip"` (part type `application/zip`) returns 200 `{"jobId":"<id>","checksumValid":true}` in state NOT_STARTED: staged, not committed. `checksumValid:false` means the checksum file does not match the zip.

### L-MIG-009  The upload route answers by Content-Type: json 404 MigrationSvc_025, zip 415, multipart 400 MigrationSvc_030
**Kind:** OVERTURNED · **Proven:** 2026-07-26 · **Evidence:** four encodings on one org (2026-07-26)
On `POST /public/core/v3/import/package`: `application/json` gives 404 `MigrationSvc_025 'Import request with identifier [package] doesnt exist'` (the service reads `package` as an import id: a live handler, not a dead route); `application/zip` and `application/octet-stream` give 415; `multipart/form-data` with an empty or invalid zip gives 400 `MigrationSvc_030 'Invalid import package'` (the validator was reached); multipart with a valid package gives 200. `POST /public/core/v3/import` is 404 'No static resource', and `/import/upload` is `MigrationSvc_025 [upload]`. Vary the Content-Type before calling any upload route absent. Supersedes L-MIG-063.

### L-MIG-010  Start the import on `/import/<jobId>` (not `/import/package/<jobId>`), then poll and read the log
**Kind:** ROUTE · **Proven:** 2026-09-28 · **Evidence:** import SUCCESSFUL with 180 created and 34 reused (2026-09-28)
`POST /public/core/v3/import/<jobId>` with `{"name":"<name>","importSpecification":{"defaultConflictResolution":"REUSE","includeObjects":[]}}` (or `OVERWRITE`) starts the staged import; `POST /import/package/<jobId>` is 404 'No static resource'. Poll `GET /public/core/v3/import/<jobId>` until `status.state` leaves IN_PROGRESS, QUEUED or NOT_STARTED (then SUCCESSFUL, FAILED or PARTIAL). The success envelope has `objects:null` unless you add `?expand=objects`, which returns per-object `sourceObject`, `targetObject` and `status` ('Create object' or 'Reuse existing object'); `targetObject.id` came back null, so read target ids from the target's objects list. `GET /public/core/v3/import/<jobId>/log` (Accept `*/*`) returns the log; a 214-object import ran about 3.5 minutes.

### L-MIG-011  Import into a non-empty org with REUSE, then check the reused pairs
**Kind:** DECISION · **Proven:** 2026-09-28 · **Evidence:** 34 reused pairs, 9 verified by runtime evidence (2026-09-28)
With `defaultConflictResolution: REUSE`, an object whose name and type already exist in the target is kept ('Reuse existing object'), nothing unrelated is overwritten, and bundle content comes from the target's own copy. The reused copy may be older than the source, so compare every reused pair whose source changed recently, or re-import that object with OVERWRITE. Test-import a small set first (a template plus one task).

### L-MIG-012  An import is all-or-nothing, and `includeObjects` does not exclude objects from validation
**Kind:** GOTCHA · **Proven:** 2026-09-28 · **Evidence:** 5 failures rolled back 180 objects; the edited package imported (2026-09-28)
If one object fails validation, the whole import fails (`MigrationSvc_031 'Import failed. Correct the errors in the Select Assets section and try again.'`) and every other object reports 'Object skipped because of previous failures'. Listing only some objects in `includeObjects` does not stop the others from being validated. Remove the failing objects from the package itself and import them separately.

### L-MIG-013  `importSpecification.objectSpecification` returned V3API_007 in every shape
**Kind:** ERROR · **Proven:** 2026-09-28 · **Evidence:** V3API_007 each time (2026-09-28)
Mapping a package object onto a chosen existing target object (`objectSpecification: [{sourceObjectId, existingTargetObjectId | existingObjectId}]`) was rejected with V3API_007 in every shape tried. Use name-based REUSE, or edit the package so it references the target object by name.

### L-MIG-014  MigrationSvc_056: objects are missing required dependent objects
**Kind:** ERROR · **Proven:** 2026-09-28 · **Evidence:** first import attempt of a migration (2026-09-28)
'One or more objects are missing required dependent objects' lists the objects it skipped. Export with `includeDependencies:true` and make sure every dependency (runtime environments, connections, bundle templates, bundle rule specs) is in the package or already in the target under the same name.

### L-MIG-015  The hosted runtime name is reserved: remap objects bound to it inside the package
**Kind:** GOTCHA · **Proven:** 2026-09-28 · **Evidence:** 15 objects remapped; import SUCCESSFUL (2026-09-28)
A runtime environment named 'Informatica Cloud Hosted Agent' cannot be created by import (`REPO_38210`). If the target is not entitled to the hosted runtime, remap every object bound to it to a self-hosted runtime environment inside the package (inner files, `exportMetadata.v2.json` entries and objectRefs, checksum lines) before importing.

### L-MIG-016  Imports drop tags: re-tag with TagObjects and read back
**Kind:** GOTCHA · **Proven:** 2026-09-28 · **Evidence:** 189 objects re-tagged and read back (2026-09-28)
Imported objects arrive without their tags. `POST /public/core/v3/TagObjects` with `[{"id":"<frsGuid>","tags":["<tag>"]}]`, at most 50 items per call, answers 204 or a per-item status; folders and projects cannot be tagged ('of type: [Folder]'). Re-tag after every import, or tag-based audits and later exports miss the imported objects.

### L-MIG-017  What a v3 package does not carry
**Kind:** LAW · **Proven:** 2026-09-28 · **Evidence:** nothing ran in the target after the import until those steps were done (2026-09-28)
Connection passwords (masked), schedules and their bindings, Secure Agents and runtime-environment service selections, CDGC content (catalog sources, glossary, links, classifications), object tags, DBMI deploy and start, CAI publish, profile rule occurrences, and every external caller's configuration (hard-coded ids and URLs). Plan each as its own step with a check: an import alone leaves nothing runnable.

### L-MIG-018  Export packages can hold plaintext secrets: treat the zip as a secret
**Kind:** SECURITY · **Proven:** 2026-09-28 · **Evidence:** found by package inspection (2026-09-28)
Connection passwords are masked, but a CAI app connection authored with `encrypted="false"` carries its OAuth client id and secret in clear, so every package containing it does too. Keep packages in a private 0600 location (not a desktop, share or repository), never print their contents in logs, and rotate the exposed secret after the migration.

### L-MIG-019  Edit a package: the inner file, its objectRefs, and upper-case SHA-256 lines for changed files only
**Kind:** RECIPE · **Proven:** 2026-09-28 · **Evidence:** checksumValid true and SUCCESSFUL imports after each edit (2026-09-22 to 2026-09-29)
(1) Change the inner file (rewrite the nested zip where there is one). (2) In `exportMetadata.v2.json` adjust or remove the object's entry and remap every `objectRefs` list that points at a changed or removed guid; each objectRef must point at an object present in the package. (3) In `exportPackage.chksum` replace only the lines of the files you changed with `<path>=<SHA-256 hex, upper case>`, including the line for `exportMetadata.v2.json` itself, and keep every other line byte-identical (the opaque object-hash lines stay valid). A missed hash gives `MigrationSvc_073 'package has been modified'`; a dangling objectRef gives `MigrationSvc_031` with empty details.

### L-MIG-020  Swapping a mapping's connection: edit the GUID in place and do not add the new connection to objectRefs
**Kind:** GOTCHA · **Proven:** 2026-08-19 · **Evidence:** the clone imported with checksumValid true and ran 52/52 rows into a different warehouse type (2026-08-19)
IDMC GUIDs are 22 characters, so a connection GUID can be swapped in place inside a mapping entry (for example `bin/@3.bin`) without shifting offsets; recompute the path-keyed checksum lines of the changed entries and leave the GUID-keyed lines alone. Adding the new connection's GUID to `objectRefs` when that connection is not in the package breaks the import with `MigrationSvc_031`; the swapped GUID resolves in the target at import time.

### L-MIG-021  Anatomy of a v3 export package
**Kind:** RECIPE · **Proven:** 2026-09-29 · **Evidence:** packages inspected and generated (2026-07-06 to 2026-09-29)
Object files sit under `Explore/<project>/<folder>/<name>.<TYPE>.<ext>`: `.DBMI_TASK.dat` and `.TOOL_CONNECTION.dat` are plain JSON; CAI assets are `.PROCESS.xml`, `.AI_CONNECTION.xml` and `.AI_SERVICE_CONNECTOR.xml`; a mapping is a nested `<name>.DTEMPLATE.zip` holding `mappingTemplate.json`, `fileRecord.json`, `bin/@<n>.bin` and `metadata.meta`. Dependencies sit under `SYS/` (`<conn>.Connection.zip`, `<re>.AgentGroup.zip`), next to `<folder>.Folder.json` and `<project>.Project.json`. `exportMetadata.v2.json` lists `exportedObjects[]` (`objectGuid`, `objectName`, `objectType`, `path`, `metadata.objectRefs`, `additionalInfo`, and `repoInfo.repoHandle` = the v2 id), `exportPackage.chksum` holds the hashes, and a CSV lists the objects.

### L-MIG-022  Packages built from scratch import when the metadata, folder entries and checksums are right
**Kind:** OVERTURNED · **Proven:** 2026-09-29 · **Evidence:** import states SUCCESSFUL, checksumValid true (2026-09-25 to 2026-09-29)
A self-built package imports SUCCESSFUL if it has the object files under `Explore/<project>/<folder>/`, the real `<folder>.Folder.json` and `<project>.Project.json` (copied from any genuine export in that folder), an `exportMetadata.v2.json` listing the folder, the project and each object with objectRefs to its dependencies (connections as `/SYS` entries with `repoInfo.repoHandle`), and correct upper-case SHA-256 lines. 400 `MigrationSvc_030` is what an empty or malformed multipart gets. Proven for CAI connectors, app connections and processes, advanced taskflows (import only) and multi-transformation mappings. Supersedes L-MIG-066.

### L-MIG-023  Migration-clone authors design objects headless for most object types
**Kind:** OVERTURNED · **Proven:** 2026-09-28 · **Evidence:** imports SUCCESSFUL with the new objects visible in the org (2026-07-05 to 2026-09-28)
Export a same-type object, change its name, GUID and references in the package, re-hash, import and start. Proven: RULE_SPECIFICATION (count 4 to 11 to 12), BUSINESS_ENTITY (41 and 15 fields), MDM_SRC_SYSTEM, reference entities and Data Marketplace products (2026-07); CAI PROCESS with its AI_CONNECTION and AI_SERVICE_CONNECTOR (2026-07 and 2026-09); MAPPING/DTEMPLATE (2026-08-19 and 2026-09); DBMI_TASK (2026-09-22). It costs no IPU, and needs the migration role plus an existing same-type object or a from-scratch package. Supersedes L-MIG-061, L-MIG-062, L-MIG-071.

### L-MIG-024  An import creates design objects only: deploy, publish and bind separately
**Kind:** GOTCHA · **Proven:** 2026-09-28 · **Evidence:** each follow-up step was needed before anything ran (2026-09-22 to 2026-09-28)
The commit creates design objects (state SUCCESSFUL, `objects:null`): DBMI tasks are not deployed, CAI assets are not published, no schedule is bound, connections have no passwords, and objects may point at runtime environments with no agent. Follow each import with the service's own step: DBMI `task/deploy`, CAI `asset/v1/publish`, a v2 schedule bind. MDM model deploy is still a UI step in these sources (disputed). Check that objects already in the org survive each commit. Supersedes L-MIG-067.

### L-MIG-025  A clone inherits the template's logic and target properties
**Kind:** GOTCHA · **Proven:** 2026-09-22 · **Evidence:** noted before the first run (2026-07-09 and 2026-09-22)
A cloned rule spec inherits the template's expression body, and a cloned task built from a template for another target type carries that type's target property map. Fix the logic or the properties before the first real run, or clone from a template of the same target type.

### L-MIG-026  Cloning needs a same-type object: an empty org has nothing to export
**Kind:** WALL · **Proven:** 2026-07-26 · **Evidence:** empty org (2026-07-26); from-scratch packages proven (2026-09-25 to 2026-09-29)
On an empty org the export fails with `MigrationSvc_041` because there is no template. Check with an unfiltered `GET /public/core/v3/objects?limit=5`: `count:1` with only a default project is decisive, while a type-filtered count 0 proves nothing. For a type with no object in the org, author one seed (UI), or build the package from scratch where its format is known (mappings, CAI assets, taskflows).

### L-MIG-027  Rebinding a cloned mapping to a new connection type needs that connection's package entry
**Kind:** WALL · **Proven:** 2026-07-06 · **Evidence:** export inspection: no mapping used the needed connection type (2026-07-06)
To rebind an exported mapping to a different connection type, the package needs that connection's `SYS/<conn>.Connection.zip`, which a pure clone only has if some mapping already uses it; if none does, author one seed mapping with that source or target and clone from it. Generated packages carry their own `/SYS` connection entries, which probably removes this limit for synthesized mappings (untested for a new connector type).

### L-MIG-028  MigrationSvc_031 on a mapping import: rule out package defects, then treat it as transient
**Kind:** ERROR · **Proven:** 2026-08-19 · **Evidence:** 85-124 July failures with 0 recoveries, then clean DTEMPLATE imports (2026-08-19, 2026-09-29)
A mapping package can upload (200 `checksumValid:true`) and still fail on start with 500 `MigrationSvc_031 ... type [DTEMPLATE] ... An error occurred while loading the mapping`. In July a known-good, already-live package failed identically, which pointed at a transient service fault (retry later or open a support case); later clones and synthesized mappings imported fine. The same code also comes from package defects (a dangling objectRef, another failing object, a TOOL_CONNECTION), so check those first.

### L-MIG-029  A mapping's `bin` entry is editable IMF JSON, not an opaque blob
**Kind:** OVERTURNED · **Proven:** 2026-09-22 · **Evidence:** package inspection (2026-09-22); connection swap ran (2026-08-19); mappings synthesized and imported (2026-09-29)
In the exports inspected in September, the DTEMPLATE entry `bin/@<n>.bin` held IMF JSON text, and the connection references sit in `mappingTemplate.json` `references[]`, so cloning and repointing a mapping is mechanically possible; schema-bound mappings still need consistent field arrays. An MI or DBMI task's `.dat` is plain JSON too. Supersedes L-MIG-065.

### L-MIG-030  Retarget a mapping task by re-importing its mapping, not by a v2 POST
**Kind:** GOTCHA · **Proven:** 2026-09-29 · **Evidence:** POST 200 with the old target on read-back; the OVERWRITE re-import changed it (2026-09-29)
POSTing a mapping task back to `/saas/api/v2/mttask/<taskId>` with changed target parameters returns 200 but changes nothing, because the task re-derives its targets from the mapping. Retarget by editing the mapping's package and re-importing it with OVERWRITE under the same GUID, then read the task back.

### L-MIG-031  Promote between environments in three gates: plan, validate without running, gated execute
**Kind:** PROCESS · **Proven:** 2026-07-04 · **Evidence:** plan mode exit 0 with the one expected delta (2026-07-04)
(1) Plan, read-only: enumerate the assets, show the intended deltas (usually only the warehouse connection), run a pre-flight parity check and write a plan file. (2) Validate without running: import into the target, test the connections, assert parity, run nothing. (3) Gated execute: run the promoted tasks, re-check parity, log the promotion, and exit non-zero on drift; keep rollback scoped to the target assets. Inside one org, org-scoped objects (catalog configuration, glossary, DQ rules, MDM model, roles) are shared by construction and only runtime-bound objects drift.

### L-MIG-032  One org with two runtime environments before production; split production into its own org at a trigger
**Kind:** DECISION · **Proven:** 2026-07-06 · **Evidence:** isolation audit 9/9 checks and a green parity script (2026-07-06)
Two runtime environments in one org share one control plane, login and catalog, which is fine before production. Move production to its own org when real customer or financial data arrives at volume, a compliance review needs it, or billing must be separated; the split follows the org-to-org runbook (new org, agent, connections, promotion by cross-org export and import, then remove the production runtime from the shared org). Keep an environment manifest and a parity script as the source of truth.

### L-MIG-033  A tag-scoped export misses untagged objects: cross-check folders and references
**Kind:** GOTCHA · **Proven:** 2026-09-28 · **Evidence:** a read-only cross-check found 2 untagged objects in scope (2026-09-28)
Objects created in a UI or by another tool may never have been tagged (for example an MCP_SERVER and a TOOL_CONNECTION with no dependency links). Cross-check the tag scope against the folder paths and the references graph, and export the stragglers as a second package imported with the main one.

### L-MIG-034  Dependency closure through the v3 references API
**Kind:** ROUTE · **Proven:** 2026-09-28 · **Evidence:** 223 objects referencing 0 missing objects; 25 legitimate outside dependencies (2026-09-28)
`GET /public/core/v3/objects/<frsGuid>/references?refType=uses&limit=50&skip=<n>` (and `refType=usedBy`) returns `references[]` with `id`, `path` and `documentType`. Walk it for every scoped object (a small thread pool is fine) and report what lies outside the scope: runtime environments, connections, bundle templates and bundle rule specs are dependencies, not scope creep.

### L-MIG-035  Inventory an org: page the objects list and snapshot the v2 details
**Kind:** RECIPE · **Proven:** 2026-09-28 · **Evidence:** full inventories of two orgs (2026-09-28)
Page `GET /public/core/v3/objects?limit=200&skip=<n>` until `skip` reaches `count`, filter client-side (tag, path prefix, a `[<tag>]` description marker), and snapshot the v2 lists (`/api/v2/connection`, `runtimeEnvironment`, `agent`, `schedule`, `mttask`, `workflow`, `mapping`) plus every mapping-task and workflow detail, because the lists hide `scheduleId` and `frsGuid`. Save the raw JSON for diffs and id maps.

### L-MIG-036  Build the source-to-target id map right after the import
**Kind:** PROCESS · **Proven:** 2026-09-28 · **Evidence:** a flip tool remapped 138 name/id pairs with 0 mismatches against the map (2026-09-28)
For every migrated object record type, path, source v3 id, target v3 id (read from the target's objects list in the destination folder), source v2 id (the package's `repoInfo.repoHandle`) and target v2 id (found by name only among the objects this import created, for example by create time and folder, because the same names can exist elsewhere). Add the dependencies matched by name (connections, runtime environments, folders). Every caller flip, checklist and cleanup reads this one file.

### L-MIG-037  After a migration, address objects by id: the target may hold same-named objects
**Kind:** GOTCHA · **Proven:** 2026-09-28 · **Evidence:** name collisions found after the import (2026-09-28)
A target org that already holds content can contain objects with the same names in other folders (15 task names collided in one migration). Import into a dedicated project, never overwrite unrelated objects, check which legacy agents are still alive before installing a new one, and make every tool and caller use ids from the id map, never names.

### L-MIG-038  Imported tasks bind to the target's own copy of a bundle template
**Kind:** GOTCHA · **Proven:** 2026-09-28 · **Evidence:** one transient failure, OK on rerun (2026-09-28)
Tasks built on an Add-On Bundle template reuse the target's installed copy, which can be a different build. One task failed once with 'Cannot propagate link rule of type TmplPatternRuleImpl between Expression and IUpdateStrategyNode5' and passed on a plain rerun. Validate each migrated task once and rerun before debugging.

### L-MIG-039  A TOOL_CONNECTION (MCP tool connection) does not import: recreate it in the designer
**Kind:** WALL · **Proven:** 2026-09-28 · **Evidence:** three failed import jobs (2026-09-28)
The migration service rejected an MCP tool connection with `MigrationSvc_031` 'Internal error' in three jobs, even after the package was fixed with the live URL and a bearer token (the export had carried `token:null`). Recreate it in the Application Integration designer (MCP connection form) and attach it to its MCP server; the MCP_SERVER object itself imported.

### L-MIG-040  CAI public URLs embed the pod and org id, so every caller changes at cutover
**Kind:** GOTCHA · **Proven:** 2026-09-28 · **Evidence:** a real call through the new base URL answered in 343 ms (2026-09-28)
Anonymous CAI endpoints look like `https://<pod>-cai.<domain>.informaticacloud.com/active-bpel/public/rt/<orgIdV3>/<process>`. Make the base URL an environment variable in every caller (a code default pointing at the old org is a trap), switch it in a separate step with one verified call, and keep the old value as the rollback. The target org needs its `CAI_Anonymous_<orgIdV3>` user.

### L-MIG-041  Scan every host for consumers of the source org before repointing
**Kind:** PROCESS · **Proven:** 2026-09-28 · **Evidence:** the scan's plan dry runs caught 3 unmapped schedule ids before GO (2026-09-28)
Walk the app and tooling trees, cron tables, systemd units and env files, and classify each hit: hosts (login domain, pod, `-cai`, `-ing`, `-dqprofile`, `idmc-api`, `cdgc-api`, MCP hosts), org ids of both shapes, v2 ids (they start with the source org's v2 id), v3 22-character ids, credential file references, helper imports, id files and CAI URLs. The result is the switch list, including consumers nobody remembered; flip runtime consumers and list design-time builders separately.

### L-MIG-042  Repoint callers with a flip tool: remap by id, block unmapped ids, back up, write in place
**Kind:** PROCESS · **Proven:** 2026-09-28 · **Evidence:** verify passed per group; smoke 7/7 (2026-09-28)
Offer `status | plan | apply --group <g> --execute | rollback --backup <ts> --execute`. Remap v2 ids by the source org prefix and v3 ids from the id map, never by name; swap host literals most specific first; refuse any file that would keep an unmapped source id; render a whole group first (all-or-nothing), back each file up with an UNDO log and a manifest, and write in place (same inode, because bind-mounted files keep the old inode otherwise). Comment out crons whose target side is not ready, rebuild and recreate services at an idle moment, verify (org id, agent, services), and read secrets from 0600 files at apply time without printing them.

### L-MIG-043  Make the source org read-only in the migration library
**Kind:** SECURITY · **Proven:** 2026-09-28 · **Evidence:** the source stayed unchanged through inventory and export (2026-09-28)
In the shared migration client, raise on any non-GET call to the source org unless an explicit override is set (export POSTs are allowed), log in once per org per session with no retry loop, take the base URL from `baseApiUrl`, and never print secrets. A migration then cannot write to the source by accident.

### L-MIG-044  Run an org-to-org migration with one lead, lanes, and one IDMC writer per org
**Kind:** PROCESS · **Proven:** 2026-09-28 · **Evidence:** cutover completed with rollback kept and no second lockout (2026-09-28)
One lead owns the plan and is the only session that logs in to either org and the only importer; lanes take host work (agent, drivers, slot preparation) without IDMC logins, caller repoint preparation (read-only until GO), read-only QA and checklists, and target cleanup. Lanes claim work with leases, post heartbeats and DONE with evidence, and the lead announces every import and risky step. Failed logins from several sessions once locked a target account; after the reset, one designated session made one attempt with confirmed credentials.

### L-MIG-045  The org-to-org milestones, M0 to M13
**Kind:** PROCESS · **Proven:** 2026-09-29 · **Evidence:** executed in about 10.5 hours (2026-09-28 15:15Z to 2026-09-29 01:50Z)
M0 access and identity; M1 read-only inventory, closure and export; M2 target agent, runtime environment and services; M3 connections and secrets; M4 import with REUSE, package fixes, re-tag and id map; M5 CAI publish; M6 DBMI CDC tasks deployed but not started; M7 DQ rebind; M8 CDGC and glossary; M9 caller repoint prepared; M10 validation run per lane plus parity; M11 gated cutover; M12 soak and rotations; M13 cleanup of the target's legacy content. Each milestone has a lease, evidence and an undo. Supersedes L-MIG-069.

### L-MIG-046  Validate every lane in the target before the cutover, with exact counts
**Kind:** PROCESS · **Proven:** 2026-09-29 · **Evidence:** landing 14/14 exact; marts 25/30 identical plus 5 explained; stories 8/9 (the miss was an app change); a 62-task taskflow ran 21.6 min vs 24.5 min in the source (2026-09-28)
Run each lane once in the target, announced, with the matching source schedule paused for that window. Compare per table the run's applied rows, the warehouse COUNT(*) and the source count as of the task's read time (so live inserts do not create false deltas); compare marts with the baseline and explain every delta; run the smoke checks and end-to-end stories and classify each failure as migration regression or unrelated change. Imported tasks keep their original targets, so a validation run may write production tables unless retargeted first.

### L-MIG-047  Cutover sequence: snapshot, unbind the source, flip callers, switch CDC, bind the target, verify
**Kind:** PROCESS · **Proven:** 2026-09-28 · **Evidence:** cutover done in 21 minutes with each step read back (2026-09-28)
On the owner's GO: (1) snapshot every source workflow binding and body, once (the rollback baseline); (2) unbind the source schedules (`POST /api/v2/workflow/<id>` with `scheduleId:null`) and read back; (3) flip the callers in groups; (4) stop the source CDC job and start the target job; (5) bind the target schedules, created unbound beforehand; (6) watch the first scheduled target runs; (7) scan every task detail in both orgs for task-level schedules.

### L-MIG-048  Task-level schedules survive a workflow-only unbind
**Kind:** GOTCHA · **Proven:** 2026-09-29 · **Evidence:** the missed binding ran once in the old org and was fixed about 40 minutes after the cutover finished (2026-09-28/29)
A mapping task can carry its own `scheduleId`, and `GET /api/v2/mttask` (the list) does not return it. At one cutover a task-level binding was missed and the task ran once more in the old org. Scan every task's detail GET for `scheduleId` before and after the cutover, and move those bindings too.

### L-MIG-049  Write the rollback before the cutover, one command per step
**Kind:** PROCESS · **Proven:** 2026-09-29 · **Evidence:** rollback commands staged in the cutover report (2026-09-28); CDC rollback deliberately closed after a split (2026-09-29)
Rebind the source schedules from the snapshot and unbind the target; stop the new CDC job and resume the old one on the same slot; restore the callers from the flip backup (and rebuild); turn off any new execution flag. Keep the source org's objects, stopped jobs and agent in place through the soak. Rolling back into the source only works while its account exists and is under its monthly job cap, and CDC rollback ends once the old job is undeployed or its slot dropped.

### L-MIG-050  After the cutover, rotate every exposed credential at every touchpoint
**Kind:** PROCESS · **Proven:** 2026-09-29 · **Evidence:** touchpoint list and rotation script prepared (2026-09-28/29)
List each exposed credential (a password pasted in chat, secrets carried by packages) and every place that stores or uses it: helper creds files, service env files, catalog-source scanner credentials, and MCP OAuth clients that store the user's password (recreate those). Change it at the source, update each touchpoint, clear the lockout-guard block, verify with exactly one login, then restart the consumers.

### L-MIG-051  After a cutover the source org stays as it is; delete only what the owner names
**Kind:** DECISION · **Proven:** 2026-09-29 · **Evidence:** owner instruction (2026-09-28/29)
Leave the source org's objects, unbound schedules and stopped jobs in place unless the owner names something for deletion; a 'ready to delete' checklist is reference only.

### L-MIG-052  Pre-migration gates worth running
**Kind:** PROCESS · **Proven:** 2026-09-28 · **Evidence:** draft runbook gates (2026-09-28); not all were run because the executed migration went headless
Check host capacity (free RAM after the existing agent, swap, about 25 GB free for a second agent's roughly 20 GB of engines, a listener baseline with `ss -ltnp`, free replication slots, `wal_level`); the target's job limit and entitlements; each plane against a fake-path twin; and the import route (an empty multipart should give 400 MigrationSvc_030). Drive the cutover with a stateful script that stops at each manual step, saves its state, and resumes only with an explicit confirm token after a machine check.

### L-MIG-053  Cut a legacy pipeline over to IDMC with a cheap rollback
**Kind:** PROCESS · **Proven:** 2026-09-23 · **Evidence:** first scheduled run 46/46 SUCCESS with consumers healthy (2026-09-23)
Snapshot the affected warehouse tables into a backup dataset with an expiry (for example 30 days) and export the view DDL; point the scheduler at the IDMC runner; stop the legacy service with a no-restart policy rather than removing it. Rollback = remove the scheduler entry and start the legacy service again. Keep tables that consumers MERGE into as real tables, and verify each downstream consumer after the switch.

### L-MIG-054  Move and copy assets with FRS MoveEntities and CopyEntities; ids are preserved
**Kind:** ROUTE · **Proven:** 2026-09-24 · **Evidence:** 95 assets moved with ids unchanged while a run finished 46/46 (2026-09-24)
The public v3 API has no move verb. `POST https://<pod>.<domain>.informaticacloud.com/frs/api/v1/MoveEntities` (header `IDS-SESSION-ID: <v2 icSessionId>`) with `{"xferSpec":{"targetLocationId":"<folderId>","sourceSpecArr":[{"sourceEntityId":"<frsGuid>","mergeTags":""}]}}` (batches of 25) returns `value[].statusArr[]` with `resultValue` FRS_200 per item. GUIDs and v2 task ids are preserved, so schedules, taskflows and callers keep working, even during a run. `CopyEntities` takes the same `xferSpec`; profiles cannot be moved (FRS_108).

### L-MIG-055  Before declaring objects gone, search by id, by exact type name and in other users' projects
**Kind:** OVERTURNED · **Proven:** 2026-09-24 · **Evidence:** the objects were found and moved with ids preserved (2026-09-24)
Objects that a scan reported missing were still there: the scan used type `DBMI` (0 results, no error) instead of `DBMI_TASK`, and some clones sat in the project of the user who owned the clone source. Confirm by id with the exact type name and include other projects before concluding that objects were deleted or never created. Supersedes L-MIG-068.

### L-MIG-056  A 62-task linear taskflow took about 21 minutes; the same tasks as a DAG at concurrency 4 about 5.5 minutes
**Kind:** PERF · **Proven:** 2026-09-29 · **Evidence:** timing comparison from a dependency-DAG stage plan (2026-09-29)
Per-task overhead is about 20 s regardless of data size, so the lever for a long linear chain is concurrency, and the floor is the longest dependent chain. Record the new baseline in the target during validation. Newer evidence: L-CDI-300.

### L-MIG-057  Crosswalk catalog assets from a retired source to the live one by column-set similarity
**Kind:** PROCESS · **Proven:** 2026-07-13 · **Evidence:** attached tables grew from 519 to 592 (2026-07-13)
Score each old table against the live tables by column-set Jaccard similarity, auto-map only above a threshold, list ambiguous candidates by name instead of guessing, and publish the residual that has no counterpart with the reason. This gives an honest floor instead of forced matches.

### L-MIG-058  Replace a governance or catalog consumer by coexistence, consumer inventory and sustained parity
**Kind:** PROCESS · **Proven:** 2026-07-13 · **Evidence:** checklist method (2026-07-13)
Keep the old system running, inventory every consumer and whether it reads or writes, add new consumers additively, and repoint each existing reader only after sustained parity (for example two consecutive weeks). Every edit has a backup and fallback stays trivial; decommission only after the full checklist is green.

### L-MIG-059  Check which IDMC jobs write a dataset before renaming or retiring it
**Kind:** GOTCHA · **Proven:** 2026-09-07 · **Evidence:** dataset inventory before a tier migration (2026-09-07)
Before moving, renaming or deleting a warehouse dataset during a migration, read its IDMC run or audit tables (last write time) and the task and taskflow configurations that target it; naming conventions only hint at the writer.

### L-MIG-060  Retargeting a cloned mapping to another warehouse dialect by translating its SQL is disputed
**Kind:** RECIPE · **Status:** disputed · **Last seen:** 2026-07-04 · **Evidence:** conflicting July records (2026-07-04 to 2026-07-09)
A July record reports 22 mapping clones retargeted to another warehouse by exporting, translating the customQuery SQL (backticks to [schema].[table], IFNULL to ISNULL, SAFE_DIVIDE to *1.0/NULLIF) and re-importing; other July records say the mapping-task retarget silently reverted and that dialect retarget by package edit was impossible. The proven levers are a connection-GUID swap inside the package (L-MIG-020) and an OVERWRITE re-import of the mapping (L-MIG-030).

### L-CLEAN-001  Prove which org you are in with a live read before any delete
**Kind:** LAW · **Proven:** 2026-09-28 · **Evidence:** the owner stopped a cleanup to ask which org it targeted (2026-09-28)
Before a delete batch, read the org live: `GET /api/v2/org` (id and orgUUID) and the session-service user endpoint `/session-service/api/v1/session/User` (name and orgId; its exact host was not recorded), and make destructive scripts assert the expected org id before their first call. When two orgs are in play, pin the org explicitly in every script instead of relying on a default.

### L-CLEAN-002  Clean an org in five steps: prove it, agree a keep list, back up, delete in order, read back
**Kind:** PROCESS · **Proven:** 2026-09-28 · **Evidence:** one pass removed 81 of 83 CAI objects, 18 mapping tasks, 18 mappings, 25 DQ assets, 9 connections, agents, runtime environments, schedules and 29 users with 0 KEEP objects touched (2026-09-28)
(1) Prove the org. (2) Agree explicit KEEP and DELETE lists by id, and move into KEEP anything a KEEP object uses. (3) Back up everything on the DELETE list. (4) Delete in dependency order, matching by id (frsGuid), never by name. (5) Log each write with its read-back, tell the migration lead before each batch, and never delete while an import runs. Undo = re-import the backup package with REUSE, then republish CAI; agents and runtime environments must be re-registered.

### L-CLEAN-003  FRS DeleteEntities: batch delete with a result code per item
**Kind:** ROUTE · **Proven:** 2026-09-28 · **Evidence:** per-item codes and FRS_070 read-backs; 80 of 83 legacy CAI objects in one pass (2026-09-28)
`POST https://<pod>.<domain>.informaticacloud.com/frs/v1/DeleteEntities` with header `IDS-SESSION-ID: <v2 icSessionId>` and body `{"artifactIds":["<frsGuid>", ...]}` returns a code per item: `FRS_200` deleted, `FRS_082` still published or out of date (unpublish first), `FRS_087` project not empty (delete its contents first); a later read gives `FRS_070` not found. With `INFA-SESSION-ID` instead, FRS answers with the login page. An older body, `{"deleteSpec":{"sourceSpecArr":[{"sourceEntityId":"<id>"}]}}` on `/frs/api/v1/DeleteEntities`, was tried once and its outcome was not recorded. Supersedes L-CLEAN-031.

### L-CLEAN-004  Check what uses an object before deleting it
**Kind:** ROUTE · **Proven:** 2026-09-28 · **Evidence:** used-by checks kept a dependency out of the delete list (2026-09-28)
FRS `POST .../frs/v1/GetInboundDocRefs` (who references this document) and `POST .../frs/v1/GetAllDependencies` (what it depends on) give exact used-by checks, and `GET /public/core/v3/objects/<id>/references?refType=usedBy` is a second source. Move any candidate that a KEEP object uses back into KEEP; an address-verification entity stayed because a kept mapping used it. FRS `$metadata` needs `Accept: */*`; the request bodies of the two FRS actions were not recorded.

### L-CLEAN-005  Delete a single repository object with FRS `BaseEntities`, not `Documents`
**Kind:** OVERTURNED · **Proven:** 2026-09-26 · **Evidence:** 204 on DBMI tasks, CAI processes and profiles (2026-09-26 to 2026-09-29)
`DELETE https://<pod>.<domain>.informaticacloud.com/frs/api/v1/BaseEntities('<frsGuid>')` with `IDS-SESSION-ID` (the call the Explore UI makes) deletes DBMI tasks (undeploy first), CAI processes (unpublish first), taskflows and profiles, answering 204. `DELETE .../frs/api/v1/Documents('<id>')` gives 403. Supersedes L-CLEAN-030, L-CLEAN-033.

### L-CLEAN-006  v2 DELETE routes and how to read them back
**Kind:** OVERTURNED · **Proven:** 2026-09-28 · **Evidence:** 200 per delete with counts falling (mappings 123 to 61, 2026-08-20); read-backs across a full org cleanup (2026-09-28)
With `icSessionId` on the v2 `serverUrl`, `DELETE /api/v2/{mttask|mapping|connection|agent|runtimeEnvironment|schedule|workflow}/<id>` returns 200. A read-back 403 means gone; a deleted schedule's GET returns an empty 200 shell, so check the `GET /api/v2/schedule` list instead. Resolve a task's v2 id from its v3 id through `frsGuid` and a mapping's through `assetFrsGuid`; a mapping deletes only when its `tasks[]` is empty. `/api/v2/dtemplate/<id>` is a wrong path (404 HTML), and `DELETE /public/core/v3/objects/<id>` returned 404. Supersedes L-CLEAN-028.

### L-CLEAN-007  A connection delete is blocked first by mappings (REPO_10242), then by catalog sources
**Kind:** ERROR · **Proven:** 2026-08-20 · **Evidence:** error progression observed on two connections (2026-08-20)
`DELETE /api/v2/connection/<id>` returns 403 `REPO_10242` while any mapping still references the connection; delete those mappings first. If the error then becomes a generic 'The asset is used by another asset', a CDGC catalog source holds the connection: remove the source (the definition delete is a UI step) and retry.

### L-CLEAN-008  REPO_52013: the mapping task still has its own schedule
**Kind:** ERROR · **Proven:** 2026-09-29 · **Evidence:** REPO_52013 on a delete attempt (2026-09-29)
A v2 DELETE of a mapping task that has a task-level schedule fails with `REPO_52013`. Treat it as a sign the task is live: find the binding in the task detail (`scheduleId`), check who reads its output, and unbind deliberately only if the task really must go.

### L-CLEAN-009  Delete users with `DELETE /public/core/v3/users/<id>` (204)
**Kind:** OVERTURNED · **Proven:** 2026-09-28 · **Evidence:** 29 users deleted and read back (2026-09-28)
`DELETE https://<pod>.<domain>.informaticacloud.com/saas/public/core/v3/users/<userId>` (header `INFA-SESSION-ID`) returns 204. Back up `GET /public/core/v3/users` to JSON first, and keep the `CAI_Anonymous_<orgIdV3>` system user (anonymous `/active-bpel/public/rt` calls need it) and any service user a live process or catalog scanner signs in as (grep the hosts and configs first). In-place edit (PUT or PATCH) remains unproven, so an edit is delete plus re-create. Supersedes L-CLEAN-029.

### L-CLEAN-010  Re-create a user with `name` and `groups`, and test one seat before a batch
**Kind:** ROUTE · **Proven:** 2026-07-09 · **Evidence:** 400 on the wrong key; one batch that lost 27 seats (2026-07-09)
`POST /public/core/v3/users` with `{"name":"<login>","firstName":"<first>","lastName":"<last>","email":"<email>","groups":["<groupId>"]}`: the identity key is `name` (`userName` gives 400), `groups` is a list of plain id strings, and at least one role or group is required. Snapshot before any batch delete-and-recreate and test the recreate on one seat first, because a wrong body once left 27 seats deleted.

### L-CLEAN-011  Unpublish CAI assets before deleting them, in dependency order
**Kind:** ROUTE · **Proven:** 2026-09-29 · **Evidence:** 59 legacy assets unpublished, then deleted (2026-09-28); the same order in a second org (2026-09-29)
`POST https://<pod>-cai.<domain>.informaticacloud.com/active-bpel/asset/v1/unpublish` with `Content-Type` and `Accept` both `application/vnd.api+json` and body `{"data":{"type":"unpublish","attributes":{"assetPaths":["Explore/<project>/<folder>/<name>.<TYPE>.xml"]}}}` returns `data.id`; poll `/active-bpel/asset/v1/unpublish/<id>/Status` and read each item. Unpublish processes first, then app connections, then connectors (up to 199 paths per call). A published asset refuses the FRS delete with FRS_082.

### L-CLEAN-012  CAI assets stuck with duplicate runtime rows or no runtime entry cannot be deleted
**Kind:** WALL · **Proven:** 2026-09-28 · **Evidence:** 2 of 83 legacy CAI objects left behind (2026-09-28)
If the CAI runtime holds two catalog rows for one asset, publish and unpublish both fault with 'singleton sequence ... 2 items'; an asset with no runtime entry faults with `AvrEntryNotFoundFault`. Both stay flagged published, so FRS refuses the delete (FRS_082) and their projects cannot be emptied (FRS_087). This needs Informatica support or a UI attempt.

### L-CLEAN-013  Delete in dependency order
**Kind:** PROCESS · **Proven:** 2026-09-28 · **Evidence:** the order held across a full org cleanup and a one-app removal in two orgs (2026-09-28/29)
CAI unpublish (processes, then app connections, then connectors), CAI assets, taskflows (after unbinding their schedules), mapping tasks, mappings, DBMI tasks (stop, undeploy, then FRS delete), DQ assets and profiles, connections (after a used-by check), agents, runtime environments, schedules, empty folders, empty projects, users. For CDGC, delete glossary items and purge the catalog sources over REST, then delete the source definitions in the UI.

### L-CLEAN-014  Back up everything a cleanup touches, and log each write
**Kind:** PROCESS · **Proven:** 2026-09-28 · **Evidence:** four backup packages, about 27,000 MDM records and the CDGC content saved before the deletes (2026-09-28)
Take v3 export packages of the connections, design content, CAI and MDM configuration you will delete (stored privately, because packages can hold secrets); MDM business records as JSON; CDGC glossary and catalog content as JSON; and the user list. The MDM search returns at most 10,000 records per query (`POST https://<pod>-mdm.<domain>.informaticacloud.com/search/public/api/v1/search` with `{"search":"*","entityType":"<be>","recordOffset":0,"recordsToReturn":1000}`, Bearer JWT plus `IDS-SESSION-ID` and `X-INFA-ORG-ID`), so export larger entities as a union of term and prefix-wildcard queries and check the union count against the entity count. Append every delete and its read-back to a log file.

### L-CLEAN-015  A REST delete of a CDGC catalog source only purges it; the definition stays
**Kind:** WALL · **Proven:** 2026-09-29 · **Evidence:** purges confirmed with the definitions still listed (2026-09-29); 400 on a stuck scan (2026-06-29)
`DELETE https://cdgc-api.<domain>.informaticacloud.com/ccgf-catalog-source-management/api/v1/datasources/<id>` purges the harvested metadata (a bulk purge job) and leaves the definition listed; delete the definition in Metadata Command Center, and back up the source JSON first. A delete while a scan is stuck returns 400 'Job is in progress ... cancel current job', with no cancel API, and de-registration can lag many minutes. Supersedes L-CLEAN-032.

### L-CLEAN-016  Never delete platform content
**Kind:** LAW · **Proven:** 2026-09-28 · **Evidence:** keep list of a full org cleanup (2026-09-28); utility dependency risk (2026-08-20)
Keep Add-On Bundles (FRS reports `delete:false` even for an admin, and tasks built on a bundle template break without it), the Default project and the system API policy, the CDGC home dashboard and widgets, the system classifications, policies and roles, the `CAI_Anonymous_<orgIdV3>` user, stock samples and utilities (`dsst__*`, `B2B_Gateway_*`, `infacore_*` DQ utilities that kept DQ mappings may reference), and the Reference360, Business360 and MultidomainMDM system content.

### L-CLEAN-017  A rejected or interrupted tool call may already have run: read back and report
**Kind:** LAW · **Proven:** 2026-09-28 · **Evidence:** 68 deletes found after the rejection (2026-09-28)
When a user rejects or interrupts a call mid-run, the server-side work may still have happened (68 FRS deletes had landed). Read back the real state and report exactly what happened before continuing.

### L-CLEAN-018  'Objects Listing Failed: null' (500) while another session writes: retry
**Kind:** ERROR · **Proven:** 2026-09-28 · **Evidence:** 500, then 200 on retry (2026-09-28)
`GET /public/core/v3/objects` returned a one-off 500 'Objects Listing Failed: null' while a peer session was importing into the same org, and a retry worked. Retry list calls once or twice before treating the error as real, and do not run large deletes during another session's import or cutover.

### L-CLEAN-019  An FRS PATCH of a document's `customAttributes` returns 204 and changes nothing
**Kind:** GOTCHA · **Proven:** 2026-09-28 · **Evidence:** read-back after the 204 (2026-09-28)
Read back every write; a 204 from FRS is not proof that anything changed.

### L-CLEAN-020  Select what to delete by owning agent or runtime, never by name
**Kind:** LAW · **Proven:** 2026-08-20 · **Evidence:** kept program verified intact after each delete wave while a peer added objects (2026-08-19/20)
Names mislead: a task named like one program can belong to another. Build the delete list from the runtime environment or agent each task runs on, keep an explicit denylist of what to keep, re-check each object's binding immediately before deleting it (other sessions may be creating assets meanwhile), and verify that the kept program still works after each wave.

### L-CLEAN-021  In an org you do not own, change only what you created, and prove the rest is untouched
**Kind:** LAW · **Proven:** 2026-09-24 · **Evidence:** non-owned location counts identical before and after a move of 95 assets (2026-09-24)
Relocate or modify only the assets your sessions created, and compare a location count of everything else before and after. Projects and folders cannot be tagged, so the ownership marker is a dedicated project or folder plus an asset tag; organization-level objects (connections, schedules, runtime environments) carry a name or description marker. Get the owner's OK before writes and log each write with its undo.

### L-CLEAN-022  Remove one application's whole footprint in dependency order
**Kind:** PROCESS · **Proven:** 2026-09-29 · **Evidence:** zero runs of the removed app on either agent at the next scheduled slots (2026-09-29)
Export with dependencies first; unbind its schedule; delete its taskflow; remove its tasks from any shared taskflow (GET the workflow, filter `tasks[]`, POST it back); delete its mapping tasks by v2 id; unpublish, then FRS-delete, its CAI processes; stop and undeploy, then FRS-delete, its DBMI tasks; delete its profiles, glossary domain and terms, and catalog source (purge now, definition later in the UI); delete its connections last, after a used-by check. Off-platform, comment out its IDMC cron jobs (with an undo file), switch its app-side calls off and label it honestly, then verify at the next scheduled slots that no run of it happened on any agent.

### L-CLEAN-023  Delete superseded tasks only after a chunked export backup and a name-to-id map
**Kind:** PROCESS · **Proven:** 2026-09-24 · **Evidence:** 50 tasks deleted with the live pipeline unaffected (2026-09-24)
Export the tasks with v3 export in chunks (for example 20 per package) and save a name to frsGuid map; the undo is a re-import of those packages. Keep live-plan tasks and templates, delete only superseded ones (shadow copies, spikes, failed probes), and leave cheap, harmless evidence in place.

### L-CLEAN-024  Never delete on an inventory verdict alone: refute orphanhood, then stage the removal
**Kind:** PROCESS · **Proven:** 2026-07-08 · **Evidence:** 37 false positives caught before any delete (2026-07-05)
Try to refute every 'orphan' label (code and pipeline SQL, dashboards, IDMC tasks, freshness metadata); in one audit 37 of 90 orphans were refuted. Then stage the removal: quarantine (rename and revoke writes), soak (for example 7 days, confirming no writer repopulates it), archive, and drop, each drop approved separately; exclude anything that serves an app. 100%-NULL columns on connected tables are unpopulated, not dead.

### L-CLEAN-025  'In no taskflow' is not 'unused'
**Kind:** GOTCHA · **Proven:** 2026-09-29 · **Evidence:** one 'orphan' had its own hourly schedule and fed an app API; another was obsolete (2026-09-29)
A task outside every taskflow can still run on its own schedule, feed an application endpoint, or be started by an external orchestrator by id. Check its detail GET for `scheduleId`, search the application code and views for its output, and grep orchestrator plans and id files before deleting it. Also check whether its target is still a table: one flagged task wrote a table that had become a live view, so it was obsolete rather than a data bug.

### L-CLEAN-026  For a project that mixes keepers and junk, move the keepers out first
**Kind:** GOTCHA · **Proven:** 2026-08-20 · **Evidence:** cleanup plan for two mixed projects (2026-08-20)
Move the assets to keep into a new project (FRS MoveEntities preserves ids), then delete the old project wholesale; this avoids item-by-item picking inside mixed projects.

### L-CLEAN-027  Post-cutover host cleanup must never drop the live replication slot
**Kind:** LAW · **Proven:** 2026-09-29 · **Evidence:** a staged host-cleanup script was rewritten to check-only (2026-09-29)
When a new CDC task took over an old slot, that slot is the live one: host cleanup scripts must be check-only by default and refuse to drop a slot unless its consumer is known to be undeployed for good.

### L-MIG-072  Inventory traps in v3 objects: linear taskflows are WORKFLOW, and references page at 50
**Kind:** GOTCHA · **Proven:** 2026-09-30 · **Evidence:** Two orgs of evidence; 1 vs 8 taskflows and the limit=200 400 reproduced (2026-09-30)
`GET /public/core/v3/objects?q=type=='TASKFLOW'` returns only advanced taskflows. Linear taskflows are type `WORKFLOW` and need their own query: one org showed 1 vs 8. `GET /public/core/v3/objects/<id>/references?refType=uses` rejects `limit=200` with 400 `V3API_ObjectReferenceError_02` 'Invalid limit parameter'. Use `limit=50` and page with `skip`. Leaving out `refType` is also a 400. A pre-delete used-by check that misses either returns a clean result that is wrong.

### L-CLEAN-034  Delete retired mapping tasks in gated waves: categorise, scan configuration files too, merge every keep list, export, DELETE, read back, rescan the catalog
**Kind:** PROCESS · **Proven:** 2026-10-01 · **Evidence:** Wave 1: a re-inventory cut 25 candidates to 13; 13 tasks and 1 empty schedule deleted, each DELETE 200 and read-back 403, after a 20-entry export package was checked; no lane impact and no overlap with the live plan
Inventory every mapping task fresh and put each in exactly one category: LIVE (in a lane, linear taskflow, taskflow or schedule), REFERENCED IN CODE OR CONFIGURATION, RAN SINCE <time>, BLOCKED BY A DORMANT TASKFLOW, SCRATCH, or SAFE. The reference scan must cover every file type the orchestrators and hosts read (.json, .yaml, .env, cron entries), not only code: a scan of .py and .sh files missed 11 tasks named in an orchestrator's rollback-plan JSON, so 25 'SAFE' candidates were really 13; treat bookkeeping fields such as 'replaces', 'replaced' or 'excluded' lists as non-uses. Objects that belong to another workload sharing the org look SAFE because nothing in your stack calls them: merge the keep lists of every application in the org (one such task was pulled at the last minute). Keep rollback-path objects until the agreed soak date (for example one green week) and delete them in a later wave. Right before each delete re-verify every object: the name still matches the id; no task-level schedule (the v2 list hides `scheduleId`, so GET each task, L-CDI-146); not in any lane or taskflow (taskflow references page at 50); no run since the cutoff, including taskflow sub-entries. Download and open a v3 export package of exactly these objects, then `DELETE /api/v2/mttask/<id>` (200) and read back (403 = gone); delete a now-empty schedule only after confirming that no task or taskflow references it. Afterwards rescan the IICS catalog source so lineage drops the deleted objects (Metadata Change Option = Delete, L-CDGC-028). Undo is a v3 import of the package (new ids, so nothing may call them by id). Delete your own scratch drafts with the same backup step (L-CLEAN-024, L-CLEAN-025).

### L-MIG-073  After an org move, give every source-org object a delete verdict from the id map and the import log before deleting anything
**Kind:** PROCESS · **Proven:** 2026-09-28 · **Evidence:** 228 source objects classified: 180 READY, 9 HOLD-VERIFY, 7 NO-TWIN (5 rejected initial-load tasks), 3 probes, 13 name-matched dependencies, 16 shared or vendor objects; built read-only from local files
Build the source-org decommission list from three inputs (the source inventory, the source-to-target id map and the target import's object log) and give each object one verdict: READY (the import created a twin and its target id is mapped); HOLD-VERIFY (the id map has a twin but the import log says 'Reuse existing object', so the target kept an older same-named object: compare content first); NO-TWIN (not in the target, for example an object the target rejected, such as initial-load tasks failing vendor validation with 403: never delete); test probes (delete any time); dependencies matched by name with no target id (connections, runtime environments, folders: delete last); and shared or vendor content (bundles, other teams' folders, hosted runtimes: never delete). Generate the list with a script so it can be rebuilt whenever the id map changes, and keep deletion a separate, owner-approved step after cutover and smoke tests (L-CLEAN-034).

### L-MIG-074  After moving to a new org, send one batched vendor case with only what the vendor alone can fix, each item with its evidence
**Kind:** PROCESS · **Proven:** 2026-10-02 · **Evidence:** One case covered the job limit, the DAM licence, 2 stuck CAI assets, the DBMI defect and the missing services; two earlier items (the data gateway, BigQuery profiling) were removed after they started working
Collect the post-cutover gaps that no headless or UI step can close and send them as one case, ordered by urgency: (1) the real monthly job limit when the Licenses page shows no jobs row and every limit reads -1 on a trial edition (an earlier org with the same reading stopped at exactly 10,000 jobs, L-IPU-041), plus a request to raise it or move to a non-trial licence; (2) services that restart-loop for lack of a licence or setup (for example the Data Access Management agent and proxy exiting with code 133 after 'Initializing TMS and CMS configuration services', L-AGENT-091), with the licence-read evidence; (3) CAI assets stuck with duplicate runtime rows ('singleton sequence ... 2 items') or no runtime entry (AvrEntryNotFoundFault) that block deletes (FRS_082, L-CAI-078); (4) reproducible product defects with a minimal repro (for example DBMI CDC shifting fractional-second digits, L-DBMI-024); (5) the engine and selection-list diff against the old org. Leave out tenant issues of other products (BI OAuth policy, SaaS storage), re-check each item the same day and drop those that resolve before sending, and post the case number where the team tracks work.

### L-CLEAN-035  Sort a shared org into one tag per workload plus a top-level Archive project, without deleting anything
**Kind:** RECIPE · **Proven:** 2026-10-06 · **Evidence:** 260 moves FRS_200 with every v2 task id read back unchanged; the orchestrator's id-based flows kept working; 725 objects tagged; nothing deleted
Give every Explore object exactly one owner tag (one per workload plus `archive`) and move what belongs to no workload into a new top-level `Archive` project, one folder per theme, with FRS `MoveEntities`. Ids, v2 task ids, schedules and run history survive the move. Make Archive a top-level project, never a folder inside a workload project, so the IICS catalog-source include filter on that project does not scan it. Refute each archive verdict before moving: FRS inbound refs, linear-taskflow membership, task-level schedules, recent runs (taskflow sub-entries included), and a grep of the orchestrator's code AND its JSON plan files for the v2 ids and names. Tag in place what cannot move: profiles (FRS_108), installed MDM app content, CAI assets stuck in the runtime. Bundle content cannot be tagged either. Keep the folders that generators write to, re-run a tag sweep after builds, and write a per-object undo log (id, from container, to container).

### L-CLEAN-036  Some cleaned-up objects regenerate: the sample mock connections and the DQ capability schedules
**Kind:** GOTCHA · **Proven:** 2026-10-06 · **Evidence:** connections recreated within 25 min of the delete; schedules recreated when DQ automation was enabled two days later
Three 'Sample ... Connection' MockConnector connections on the hosted runtime reappeared about 25 minutes after a delete, when a database-ingestion CDC task was created. The `DQ_Capability_Schedule_{Daily,Weekly,Monthly}_<epoch>` schedules ('Auto generated schedule for existing Rule Templates') are created by catalog data-quality automation, and they came back after a delete once DQ scoring was enabled on a catalog source. Classify both as platform-generated: keep them, or switch the feature off first. Don't put them on a delete list.

### L-MIG-075  Rename a repository object in place: PATCH the FRS Documents entity, not BaseEntities
**Kind:** ROUTE · **Proven:** 2026-10-08 · **Evidence:** Scratch mapping renamed and renamed back (204/204, v2 by-name read 200); 2 mappings, 2 tasks and 1 structure model renamed twice with read-back; task run after the rename 12 read / 9 loaded, the same as before; BaseEntities PATCH 400 FRS_068
`PATCH https://<pod>.<domain>.informaticacloud.com/frs/api/v1/Documents('<frsId>')` with header `IDS-SESSION-ID` and body `{"name": "<new name>"}` answers 204 and renames the object in place: the id is unchanged, and `GET /public/core/v3/objects` (path), `GET /api/v2/mapping/<id>` and `GET /api/v2/mttask/<id>` show the new name at once. Proven on mappings (DTEMPLATE), mapping tasks (MTT) and CLAIRE structure models (SAAS_STRUCTURE_DISCOVERY); names with spaces, a dot and a hyphen were accepted. A task keeps its mapping and a Structure Parser keeps its model, because both bind by id; a task run after the rename loaded the same rows as before. The same PATCH on `BaseEntities('<id>')` gives `400 FRS_068` 'Operation not allowed for the entity set BaseEntities': the opposite of a delete, where `BaseEntities` works and `Documents` gives 403 (L-CLEAN-005). FRS has no Rename action in its `$metadata`. Probe on a scratch object first and keep `{id, old name}` as the undo. Exporting, renaming and re-importing a package instead creates a second object, because the import matches by path.

### L-MIG-076  Import OIE_007 'Internal application provider error' on a pruned mapping: its template still references models the package no longer lists
**Kind:** GOTCHA · **Proven:** 2026-10-08 · **Evidence:** Same package FAILED with the stale references and SUCCESSFUL after removing them; the clone then validated and ran
A mapping cloned from a multi-lane export and pruned to one lane imported as `OIE_007 ... Failed to import object [...] of type [DTEMPLATE] ... Internal application provider error`, with nothing more in the job log and a 500 on the job's `?expand=objects`. The IMF itself was consistent (every `##ID` resolved). The cause was `mappingTemplate.json` inside the DTEMPLATE zip: its `references[]` still listed the structure models (`refType: structureDefinition`) of the removed lanes, while the package's `exportMetadata.v2.json` listed only the kept model and the connection in the mapping's `objectRefs`. Making the two agree (drop the removed references, or keep both lists complete) imported SUCCESSFUL on the next try. When pruning, rebuild `references[]` from the transformations you keep, and list each referenced model and connection in `exportedObjects` by id with its CURRENT path and name. Newer evidence: L-MIG-100.

### L-MIG-077  A package cloned from an export still carries the source objects' GUIDs: give the mapping and task fresh ones
**Kind:** GOTCHA · **Proven:** 2026-10-08 · **Evidence:** 3 parse mappings + 1 pickup cloned into a new project: the template GUIDs were live objects; after the swap 0 left, the source objects' update times unchanged; one upload refused with Duplicate key until the entries were deduplicated
A v3 export lists each object with its live GUID (exportMetadata objectGuid, mappingTemplate assetFrsGuid, the task's mapping reference). A clone built from it under a new name and path imported as a new object in the cases seen, but the GUIDs still point at the source objects, so a clone of a still-existing object risks landing on it. Replace the mapping and task GUIDs with fresh 22-character ids everywhere they occur (outer files and the files inside the DTEMPLATE/MTT zips), then check that none of the old ones is left. When the template package listed its Project or Folder twice and both entries now carry the same id, the upload fails before anything is imported: 500 MigrationSvc_002 'Duplicate key <id> (attempted merging values ObjectInfo...)'. Keep one exportedObjects entry per (objectType, objectGuid).

### L-MIG-078  The v3 project create refuses a dot in the name; create it without, then rename through FRS
**Kind:** GOTCHA · **Proven:** 2026-10-08 · **Evidence:** v3 create 400 with the dot, 201 without; FRS rename 204; 5 folders created and 9 packages imported under it
`POST /public/core/v3/projects` with a name like '<Demo> 4.0' answers 400 V3API_ContainerError_004 'Project name attribute contains illegal characters: #?`|{}"^&[]/\\..'. Create '<Demo> 4_0', then `PATCH .../frs/api/v1/Projects('<id>')` with `{"name": "<Demo> 4.0"}` (204): the project shows the dotted name in Explore, folders are created under it with `POST /public/core/v3/projects/<id>/folders`, and package imports address it by that path. Renaming existing projects and folders the same way also accepts dots (L-MIG-075).

### L-MIG-079  v3 folder create also refuses a dot (400); FRS MoveEntities to a missing target answers HTTP 200 with XFER_500 per entity
**Kind:** GOTCHA · **Proven:** 2026-10-09 · **Evidence:** folder create 400 with a dot, 201 without; 11 moves 200/XFER_500, then 11 moves OK after the fix
POST /public/core/v3/projects/<id>/folders with a name containing '.' returns 400 (like projects, L-MIG-075): create it with '_' and rename it through FRS PATCH Folders('<id>') {name}. And FRS /frs/v1/MoveEntities with a null or wrong targetLocationId still answers HTTP 200: the failure is in value[].resultValue = 'XFER_500 INTERNAL_SERVER_ERROR'. Check resultValue for every entity and stop before any follow-up (tagging) when one failed.

### L-MIG-080  FRS rename refuses parentheses in the NEW name (FRS_082), even when the old name has them; a rename also updates linear taskflows
**Kind:** GOTCHA · **Proven:** 2026-10-19 · **Evidence:** 71 objects renamed or re-described in one org (mappings, mapping tasks, linear taskflows, rule specifications, CLAIRE models, folders, project): all 204 + read-back; one 400 FRS_082 for a name with '(5 digits)'; two taskflow runs green after the rename
`PATCH .../frs/api/v1/Documents('<id>')` with a name containing '(' or ')' answers 400 FRS_082 "Name '<n>' is not valid because it contains the following characters: '()'" and changes nothing (the description in the same body is not applied either), although objects created by import can carry parentheses. Drop them from the new name and resend. A rename of a mapping task through FRS also shows at once in every v2 linear taskflow that runs it (`GET /api/v2/workflow/<id>` tasks[].name), because the taskflow binds by taskId; the taskflow, the tasks' mapping, runtime and pre/post commands were unchanged and a run after the rename succeeded with the same row counts. Activity-log entries keep the name the object had at run time, so scripts that match runs by name must accept both names.

### L-MIG-081  Rename a data profile through the profiling service, not FRS: GET the full profile, change name and description, PUT it back
**Kind:** RECIPE · **Proven:** 2026-10-19 · **Evidence:** 3 profiles renamed: service name, FRS name and description read back equal; field and rule counts unchanged (13/4 and the others)
A data profile keeps its own name and description in the profiling service (`GET https://<pod>-dqprofile.<domain>.informaticacloud.com/profiling-service/api/v1/profile/<id>`), which is what profile-list scripts read. `PUT .../profile/<id>` with the complete GET body and only `name` and `description` changed answers 200 and updates both the profiling service and the FRS document (Explore) at once; profileableFields and source.rules stay as they were because the full body is sent (an omitted field would be ignored, not removed). Scripts that look profiles up by exact name need the new name or an alias.

### L-MIG-082  Re-point an exported package to another org: connections, runtime environments (AgentGroup objects), org ids, pre-commands, checksums
**Kind:** RECIPE · **Proven:** 2026-10-16 · **Evidence:** One project imported on the first attempt (36 created, 4 reused); a second (28 tasks, 2 CDC tasks, CAI assets) imported after the bundle-template fix; every task then ran in the target org (2026-10-16)
Edit every file of the v3 export, nested DTEMPLATE zips included: replace each old connection's federatedId and v2 id with the target org's tested connection (and its name in SYS entries); map each old runtime's federatedId and v2 id to a target runtime per object (hosted or Secure Agent); replace the old org's v2 and v3 ids (profiles and CAI assets carry them); blank preProcessingCmd/postProcessingCmd values that call hosts the target cannot reach. Drop the old `SYS/<re>.AgentGroup.zip` and its exportedObjects entry and add, for EVERY target runtime that objects now reference, a `SYS/<re name>.AgentGroup.zip` (`runtimeEnvironment.json` = [{name, federatedId}] plus the original `metadata.meta`) and an exportedObjects entry (objectType AgentGroup, path /SYS, repoInfo.repoHandle = the runtime's v2 id). De-duplicate objectRefs (two old runtimes mapped onto one produce duplicates), rewrite `exportPackage.chksum` (spaces in paths escaped as '\ ', uppercase SHA-256) and string-scan the result for any old id. Import with REUSE. Refines L-CONN-024.

### L-MIG-083  Tasks built on Add-On Bundle templates do not migrate: the export lists the template and its project but carries no file, and the import fails MigrationSvc_031
**Kind:** GOTCHA · **Proven:** 2026-10-16 · **Evidence:** Import failed MigrationSvc_031 until the 10 template-based tasks were rebuilt as user mappings; then the import succeeded (2026-10-16)
An export of tasks over `dsst__copy_data_new_tgt` (or another Add-On Bundle template) lists the template object and the 'Add-On Bundles' system project in exportMetadata.v2.json, but the package has no file for them, so the import fails with MigrationSvc_031; a target org may not have the bundle at all. Remove the system project entry and the template references, and rebuild those tasks as ordinary user mappings (a spec-to-IMF generator did 10 of them) before importing, or recreate them on the target org's own copy of the template. Check an export for objects that have no file before the first import attempt. Refines L-CDI-004.

### L-MIG-084  License-installed MDM bundle content cannot be deleted headless, even by an admin: FRS answers 403 FRS_127
**Kind:** WALL · **Proven:** 2026-10-16 · **Evidence:** Unpublish OK, delete 403 FRS_127, republish restored all 7 objects (2026-10-16)
In an org provisioned with MDM bundles, the bundle projects' content (for example the unused C360/P360/S360 objects) unpublished fine, but `DELETE` of the entities through FRS BaseEntities answered 403 FRS_127 "permission [delete] not available" for an org admin. The content is system-locked like the Add-On Bundles (L-CLEAN-016). Republish what was unpublished (state restored and verified) and leave bundle content in place; hide it from demo users with roles instead. Refines L-CLEAN-016.

### L-MIG-085  Change a folder's description: PATCH /frs/v1/Folders('<folderId>')
**Kind:** ROUTE Â· **Proven:** 2026-11-02 Â· **Evidence:** 8 folder descriptions updated and read back; the v3 route 404 (2026-11-02)
PATCH https://<pod>.<domain>.informaticacloud.com/frs/v1/Folders('<folderId>') with header IDS-SESSION-ID and body {"description": "..."} answers 204, and GET /frs/v1/Folders('<folderId>') reads the new text back. The v3 form PATCH /saas/public/core/v3/projects/<projectId>/folders/<folderId> answers 404 'No static resource'. Keep folder descriptions as a short map of the live assets they hold and where retired ones went.

### L-MIG-086  Prove a table migration inside IDMC: per-dataset units and an order-free checksum on both sides, joined by one reconcile mapping that writes a status row per dataset
**Kind:** PATTERN · **Proven:** 2026-11-01 · **Evidence:** Two reconcile runs covering 116 legacy datasets: 108 reconciled, 5 mismatch_source_changed, 3 mismatch (2026-11-01)
For each legacy dataset measure, read-only and throttled (2 threads, a memory cap), its rows, distinct units and a checksum = sum(hash(unit key)) mod 2^64, which ignores row order, plus the table's last modification time. Stage these legacy stats as a flat file on the agent. The target-side SQL for the same measures comes from a run parameter file (`$$TGT_SQL`, see the parameter-file lesson) and counts a unit only when all its chunks are present. One mapping joins legacy stats (master outer, so datasets missing on the target still appear) to target stats; an Expression sets reconciled / mismatch / mismatch_source_changed (the legacy table changed after capture) / missing_target and writes one control row per dataset per run with run lineage ($CurrentTaskId / $CurrentRunId) and record_version = run id, so the latest run wins. Exact duplicate rows collapse into one record in a lossless capture keyed by row hash: record count() against the distinct row-hash count on the legacy side so the multiset stays provable. A linear taskflow runs the reconcile and the dictionary refresh together. The first two runs over 116 datasets gave 108 reconciled, 5 changed at the source and 3 real mismatches, which turned 'is everything there?' into a list of three datasets to inspect. Newer evidence: L-MIG-091.

### L-MIG-087  Make view-only walk-through copies of mappings with FRS CopyEntities: name and describe them in the call, omit conflictResolution ('NONE' gives XFER_500), and take the new id from tgtGuid
**Kind:** RECIPE · **Proven:** 2026-11-02 · **Evidence:** 16 mappings copied into a new 4-folder project, each named and described in one call; updateTime unchanged on all 16 originals; the conflictResolution 'NONE' probe failed with XFER_500 (2026-11-02)
`POST https://<pod>.<domain>.informaticacloud.com/frs/api/v1/CopyEntities` (header `IDS-SESSION-ID`) with {"xferSpec": {"targetLocationId": "<folderId>", "sourceSpecArr": [{"sourceEntityId": "<frsId>", "destName": "<new name>", "destDesc": "<text>", "resetExpiryTime": false, "mergeTags": ""}]}}. It answers XFER_200, with resultValue FRS_2xx and the copy's id in value[].statusArr[].tgtGuid. Adding "conflictResolution": "NONE" fails with XFER_500 'Unknown conflict resolution policy', so leave the key out. To set or fix a description later, `PATCH .../frs/api/v1/Documents('<id>')` {"description"} and read it back (as for rule specifications, L-DQ-094). A copy is only the mapping, with no mapping task, so it adds nothing to lineage: an IICS source harvests a mapping only through an in-scope task (L-CDGC-157). Put walk-through copies in a separate project outside the IICS catalog source's filter, and link the lineage of the live assets. Record each source's updateTime before the copy and compare it after, to prove the originals were not touched. Undo = `DELETE .../BaseEntities('<copyId>')` (L-CLEAN-005).

### L-MIG-088  Consolidate many warehouse databases into a few without copying data: Atomic RENAME TABLE, pause and repoint the writer, leave a read-only view at the old name
**Kind:** RECIPE · **Proven:** 2026-10-29 · **Evidence:** Plan for 1,648 kept tables; first phase 17 tables / 7.6 GB generated with undo, not yet run (2026-10-29)
To fold 29 databases into six by purpose (bronze, silver, gold, site, ML, ops), count code references first (about 800 files named the existing databases, so the six kept their old names and only tables moved). With Atomic databases a move is metadata only: pause the table's writer (cron, lane, publisher, IDMC task), `RENAME TABLE <old_db>.<t> TO <new_db>.<t>`, change dependent views, repoint the writer (for IDMC: the connection's schema or the task's target), resume, compare row counts, and keep a read-only view at the old name for 14 days, dropping it once `query_log` shows no reader. Generate the move, its undo and the per-table writer list from the live inventory, and rehearse on a scratch copy before the GO. A JDBC V2 profile or mapping only sees its connection's own database (L-DQ-134), so a consolidation also cuts the number of IDMC connections needed.

### L-MIG-089  A lightweight DELETE in the target hid 49.5M rows that IDMC had loaded: counts looked like missing data, and the rows were recoverable only until merges
**Kind:** GOTCHA · **Proven:** 2026-11-01 · **Evidence:** 50,056,845 physical vs 507,919 visible bronze rows (49,548,926 masked across 147 source tables); run manifests 873 physical vs 61 visible (2026-11-01)
During a lossless migration through IDMC, a cleanup DELETE (ClickHouse lightweight delete) masked rows that the capture lanes had already loaded, so per-table target counts fell far below what IDMC reported (for example 41.6M source rows loaded, 0 visible). The rows were still physically on disk and readable with `SETTINGS apply_deleted_mask = 0` until background merges purged them, which made recovery time-sensitive. Before reconciling an IDMC load against a target, read `system.mutations` and the DDL history for deletes on the target; compare IDMC's success rows with both visible and masked counts; and never run a delete on a migration target without a copy-out or an approved decision, because it also resets any progress cursor kept in the target.

### L-MIG-090  Constraints added to a target in the middle of a load reject rows that loaded fine an hour earlier, and the earlier rows were never checked
**Kind:** GOTCHA · **Proven:** 2026-11-01 · **Evidence:** 4 constraints at 23:35Z; one lane failed code 469 on a payload checksum constraint (2026-10-31/11-01)
A session added four CHECK constraints (state, year built, living area, geo shape) to a migration target while IDMC lanes were loading; later batches started failing with code 469 on rows of the same shape that had loaded before, and every row loaded earlier was never checked against the new rules. Freeze the target DDL for the duration of a load; if a rule must be added, add it before the first batch or run it as a DQ check (an IDMC rule specification or a scoring mapping) over the whole table afterwards, not as a constraint mid-load.

### L-MIG-091  'Everything is in the new tables' cannot be proven while the scope stops at one database engine and the source keeps changing
**Kind:** GOTCHA · **Proven:** 2026-11-01 · **Evidence:** 807 must-migrate objects / 4.96B rows; about 10.3 % in the target at the time; 5 datasets 'mismatch_source_changed' because the source was written after capture started (2026-11-01)
A completeness critic of a 'move everything into 3 tables' migration found the auditors had inventoried only the warehouse: a 27 GB PostgreSQL property database, 12 MongoDB ML collections, a graph database, model files and cloud archives were never listed, and 155 of 251 model files were missing from the target. The legacy warehouse was still being written by crons, an application and the publisher while counts were taken, so no count stayed true. Before claiming a migration complete: inventory every store the product reads (each engine on the host, file stores, buckets), have the owner include or exclude each explicitly, freeze writers or record a watermark, and reconcile per dataset with an order-free checksum on both sides (L-MIG-086), recorded outside IDMC's 1,000-row activity log. Refines L-MIG-086.

### L-MIG-092  A wide 'one table for everything' target used about 11x the bytes per row of the legacy estate: project the disk before loading billions of rows
**Kind:** PERF · **Proven:** 2026-11-01 · **Evidence:** 256.76 GiB / 440.67M rows = about 626 B/row vs 309.1 GiB / 6.15B rows legacy; 2.46 TiB free of 2.88 TiB (2026-11-01)
The migration target (one wide table with JSON payload columns per record) used about 626 bytes per row against about 54 for the legacy estate, so the rows still to load projected to 2.1-2.8 TiB against 2.46 TiB free. Measure bytes per row from the first loaded batches (`system.parts` bytes on disk / rows) per record kind, project the full load including rerun duplicates and masked rows, and resize or redesign before the lanes run for days. At the observed 12.4M rows/hour the remaining 3.27B rows would also have taken about 11 days of failure-free running.

### L-MIG-093  Reading a live production database for a migration: use a dedicated reader login so one KILL stops every lane, and stream instead of grouping
**Kind:** GOTCHA · **Proven:** 2026-11-01 · **Evidence:** Source memory 63.7 of 64 GB; 3 production queries hit the memory limit; after the kill memory fell to 2.2 GB (2026-11-01)
Eleven capture lanes that grouped wide rows on the live source pushed its server memory to the limit and production queries started failing. Because all lanes used one dedicated migration reader login, a single `KILL QUERY WHERE user = '<reader>'` freed the memory in seconds without touching production sessions. Use a separate login per migration so you can kill it as a unit, stream rows (no GROUP BY over wide rows) on a live source, cap memory per query and run at most about 3 heavy lanes. Refines L-CDI-292.

### L-MIG-094  Audit a previous automated build before extending it: count mappings, read full-run history, check lineage is real, and confirm each stage ran on the intended entity
**Kind:** PROCESS · **Proven:** 2026-11-01 · **Evidence:** 357 mappings / 354 tasks / 149 workflows with 16 MB of task SQL; 222 mappings with hand-typed run ids; 0 entity addresses verified; 431M rows and no golden record; all 62 full archive workflows 'Aborted by agent disconnection'; 6 real patterns -> ~8 mappings and 12.6 KB of SQL; 2 forgotten schedules still burning jobs
A pipeline built earlier by another coding agent looked busy but delivered little: hundreds of one-per-table mappings with all logic in source SQL, run ids typed into expressions by hand, address verification run against a national address-point table instead of the entity table, no golden records at all, and every full-scale workflow failed while only pilot slices landed. Before adding to an inherited build: inventory objects by pattern, read the full-run history (not the pilot runs), check lineage columns come from runtime variables, and sample the output of each stage against the entity it was meant to process. The audit collapsed the build to about 8 mappings. Refines L-CDI-115.

### L-MIG-095  IDMC native source control with a self-hosted GitLab: choose Platform = On-Premise, and Git traffic goes through a runtime environment's GitRepoConnectApp
**Kind:** ROUTE · **Proven:** 2026-10-02 · **Evidence:** Vendor Administrator source-control pages (updated Aug 2026) read 2026-10-02; live XHR capture: lookupConnectionType -> ONPREM_GIT for a self-hosted GitLab URL, an earlier 400 VCS_029 on the same field (2026-10-03)
IDMC source control supports GitHub and GitLab (cloud or self-hosted), Bitbucket (self-hosted, or cloud for Data Integration assets only) and Azure DevOps (cloud only). For a GitLab on your own domain set Administrator > Settings > Source Control > Platform = On-Premise and pick a runtime environment: the agent's GitRepoConnectApp service keeps a clone of only the configured branch under `<agent_home>/apps/GitRepoConnectApp/data/git_repository/`, so the Git host never has to be reachable from the vendor cloud, but every agent in that runtime environment must reach it over HTTPS. OAuth works only for cloud repos. As you type the repository URL the UI calls `GET /vcs/api/v1/remoteRepo/lookupConnectionType?uri=<repo_url>`; for a self-hosted host it returns `{"type":"ONPREM_GIT"}`, which tells you Cloud mode is the wrong choice. Before the org is configured, related calls answer 'The connection to the source control repository for this organization cannot be found', and an intermediate URL value can return 400 `VCS_029` 'The source control repository URL is not valid'.

### L-MIG-096  Once an asset is source-controlled, an OVERWRITE package import of it needs a checkout first: make headless importers check out, import, then check in
**Kind:** GOTCHA · **Proven:** 2026-10-02 · **Evidence:** Vendor asset-import and checkout pages (Jul 2026); a checkout-aware importer compiled and its lookup tested offline against a real package (2026-10-02). The org was not yet switched on, so the live error code for an import without checkout is unverified
After source control is enabled nothing is versioned until objects are checked in, and checking in one object makes its folder or project source-controlled. From then on, source-controlled objects must be checked out to change them, and the import docs say an asset must be checked out to be overwritten, so a generator that rebuilds mappings with `POST /public/core/v3/import` and OVERWRITE will start failing. Make the importer read the package's exported objects, `POST /public/core/v3/lookup` their ids to find the controlled ones, `POST /public/core/v3/checkout` those, import, then `POST /public/core/v3/checkin`; call `/undoCheckout` when the import fails, and keep a switch that skips all of it on orgs without source control. Mapping edits deploy to their mapping tasks even when the tasks are not checked out, and undo checkout reverts to the last pulled version with no history.

### L-MIG-097  IDMC source-control REST is v3 and asynchronous: POST checkin, checkout or pull, then poll sourceControlAction
**Kind:** ROUTE · **Proven:** 2026-10-02 · **Evidence:** Vendor platform v3 REST reference, source-control pages (Jul 2026), read 2026-10-02; the CLI binary's strings show only login/logout/lookup/objects/export/import
Endpoints under `/public/core/v3/`: POST `checkout`, `undoCheckout`, `checkin` (`objects[{id, includeContainerAssets}]` plus a required `summary` of at most 255 characters), `pull` (`commitHash`, `objects[{id|path,type}]`, and `objectSpecification` to remap connections and runtime environments) and `pullByCommitHash`; GET `commit`, `commitHistory?q=path=='<project>/<folder>/<asset>' and type=='DTEMPLATE'`, `compare` and `repositoryConnection?projectIds=`. Each POST returns `{"Id":...,"status":{"state":"NOT_STARTED"}}`; poll `GET /public/core/v3/sourceControlAction/<id>?expand=objects` until SUCCESSFUL, FAILED or WARNING. Check-in types include DTEMPLATE, MTT, DSS, DMAPPLET, MAPPLET, WORKFLOW, TASKFLOW, MI_TASK, UDF, PCS, FWCONFIG and the CAI types PROCESS, AI_CONNECTION, AI_SERVICE_CONNECTOR, GUIDE, PROCESS_OBJECT, HUMAN_TASK. Connections, runtime environments, schedules and Database Ingestion assets cannot be source-controlled, so they must already exist in a target org before a pull. The vendor's asset-management CLI has no Git commands. URL-encode the `q=` filter (quotes and spaces) when building these queries in code. Reported elsewhere (not probed here): compare as a POST with the object id in the path, L-MIG-110; and a second client confirms the flat routes, L-MIG-109.

### L-MIG-098  Decide the source-control scope before you switch it on: there is no unlink endpoint, and the way back is manual
**Kind:** LAW · **Proven:** 2026-10-02 · **Evidence:** Vendor disabling and unlinking pages (Aug 2026) read 2026-10-02; no unlink route in the v3 reference
Before source control can be disabled on a read/write org every asset must be unlinked, and projects and folders unlink only after every object in them is unlinked. The repository URL cannot be changed while any asset is source-controlled, and the org cannot move from read/write to read-only while anything is checked out. UNLINK exists only as an action type in status responses, not as an endpoint, so backing out of source control on a large org is click work in the UI. Pilot on a scratch org or a single project (Enable Project Level Source Control), use one development org per repository with read-only test and production orgs, and check in a planned scope rather than everything.

### L-MIG-099  IDMC source-control limits and pull traps: 800 objects per check-in, a branch that already exists, an empty repo, case-insensitive names
**Kind:** GOTCHA · **Proven:** 2026-10-02 · **Evidence:** Vendor best-practice and limits pages read 2026-10-02; scope counted live: 195 objects across three projects, none source-controlled yet
Use an empty repository with no `Explore` folder and a branch that already exists (a blank branch name means master or main); on save IDMC writes a small readme into the repository. Limits: 50 MB and at most 800 objects per check-in, at most 1,000 objects per container, and cloud-hosted GitLab check-ins of more than 100 objects fail after about 30 minutes, so batch them. A pull deletes objects that are not in the selected version, does not bring dependent objects, fails when a project holds names differing only by case (`sales` and `SALES`), and in a read-only org can silently overwrite local edits. The docs also warn that GitLab can show incorrect commit history in pull and compare. Count the scope first with v3 objects queries.

### L-MIG-100  Mapping-task package import OIE_007 'Internal application provider error': mtTask.json holds the runtime environment as an '@<FRS id>' reference; do not overwrite it with a v2 id
**Kind:** ERROR · **Proven:** 2026-10-13 · **Evidence:** Package FAILED with the v2 id in runtimeEnvironmentId, SUCCESSFUL after deleting that one line; both parse tasks then validated and ran (2026-10-13)
When cloning a mapping-task (MTT) from an export, the task's `mtTask.json` carries `runtimeEnvironmentId` as an FRS reference of the form `@<22-character id>`, not the v2 `01...25...` runtime id. Replacing it with the v2 id made the mapping import fine but the task fail with `OIE_007 ... Failed to import object [...] of type [MTT] ... Internal application provider error` (no further detail). Removing the override (keeping the exported `@` reference, which resolves by the runtime's FRS id in the target org) imported SUCCESSFUL. To change the runtime, set the FRS-id form, or update the task over v2 after import and read it back. Refines L-MIG-076.

### L-MIG-101  CDI-PC is PowerCenter in the customer's own domain, registered to IDMC; IDMC hosts domain management and PC2CDI, and DEI/IDQ modernization reached production only with the optional October 2026 update
**Kind:** FACT · **Proven:** 2026-11-17 · **Evidence:** CDI-PC Oct 2026 doc set, PowerCenter 10.5.11, PAM 2026.10, CPDS 37.0.1-39.2, Measurement Guide 39.1, Informatica KB 000246690
CDI-PC (Cloud Data Integration for PowerCenter) keeps the PowerCenter engine and desktop clients in the customer's on-prem domain; IDMC hosts the Domain Management service (status, alerts, automatic domain updates, licence sync, metering) plus the PC2CDI assess/convert tooling. A Secure Agent only links the domain to IDMC, and the domain goes offline after about 2 hours without IDMC. In the October 2026 release DEI and IDQ modernization (Developer and Analyst tools) moved from preview to production, but only for orgs that take the optional October update (otherwise April 2027); the April update is mandatory within 90 days. The CDI-PC PAM 2026.10 still lists DQ/DEI as unsupported, so check both documents. None of the Product Description Schedule versions 37.0.1 to 39.2 name CDI-PC in the IPU-eligible matrix: CDI-PC meter rates appear only on the org's Metering rate card. Operational Insights alerts cannot be set up for CDI-PC.

### L-MIG-102  v3 Lookup fails the whole batch with V3API_LookupError_012 when any item is missing; parse the message and retry the rest
**Kind:** GOTCHA · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence high: code plus its tests, change notes or live-check notes); not probed here
`POST /public/core/v3/lookup {"objects":[{"path","type"},...]}` does not return partial results: if one object is missing the whole call errors with `V3API_LookupError_012`, and `error.message` lists every missing object as `[type: <TYPE>, location: <path>]` entries (some types renamed, e.g. DTEMPLATE reported as MAPPING, so match on path only). Treating that error as 'all missing' inflates deployment plans. Chunk requests at 200, mark the listed paths missing, look the rest up again, bisect when the message cannot be matched, and treat a failing single-item call as missing. Do not rely on response order either: reconcile results by normalised path+type.

### L-MIG-103  Check a Connection in a target org by name over v2, not with v3 lookup; missing answers 404 or 403 APP_13436
**Kind:** GOTCHA · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence high: code plus its tests, change notes or live-check notes); not probed here
The v3 lookup does not reliably resolve CDI Connection objects (`SYS/<name>`, type Connection) by path+type and can report existing connections missing or unknown. Validate them with `GET /api/v2/connection/name/<url-encoded name>` (last path segment); a connection that does not exist answers 404 or HTTP 403 `APP_13436` with a 'no object named connection' message, which must be classified as missing rather than as a permissions error. Connection and AgentGroup objects live under the `SYS/` root in packages and locations; everything else under `Explore/`.

### L-MIG-104  v3 export start accepts includeTagInformation=true, and the synchronous start call can exceed 60 s
**Kind:** FACT · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence high: code plus its tests, change notes or live-check notes); not probed here
`POST /public/core/v3/export?includeTagInformation=true` (body `{"name","objects":[{"id","includeDependencies":true}]}`) exports object tags in the package. With a large artifact list plus tags the start call itself took over 60 s before returning the job id, so a client with a 60 s HTTP timeout fails with 'context deadline exceeded' before polling begins; use a per-request timeout of 120 s or more, separate from the job's polling deadline (10 s interval, 300 s default here).

### L-MIG-105  v3 PATCH works on /folders/<id>, /projects/<id> and the /name/ forms (204); only /projects/<id>/folders/<id> is 404
**Kind:** ROUTE · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence high: code plus its tests, change notes or live-check notes); not probed here
`PATCH /public/core/v3/folders/<folderId>` with `{"name","description"}` (either one) answers 204 for a folder in any project, as do `PATCH /public/core/v3/projects/<projectId>`, `/projects/name/<url-encoded project>` and `/projects/name/<project>/folders/name/<folder>` (verified live). Only the documented `/projects/<projectId>/folders/<folderId>` form returns 404 'No static resource'. The success body is empty, so read back. Folders can also be created at `POST /projects/name/<project>/folders`, and `POST /public/core/v3/folders` creates in the Default project; v3 object ids equal project and folder ids. Refines L-MIG-085.

### L-MIG-106  List projects and folders with created time and creator through FRS OData: /frs/api/v1/Projects, /Folders, /Projects('<id>')/Folders
**Kind:** ROUTE · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence medium: code only); not probed here
`GET https://<pod>.<domain>.informaticacloud.com/frs/api/v1/Projects?$top=1000&$skip=<n>` (also `/frs/api/v1/Folders` and `/frs/api/v1/Projects('<projectId>')/Folders`) with header `IDS-SESSION-ID: <sessionId>` returns `{"value":[{id,name,description,createdBy,lastUpdatedBy,createdTime,lastUpdatedTime,documentType,parentInfo:[{parentId,parentName,parentType}]}]}`; page until fewer than `$top` rows. `createdBy`/`lastUpdatedBy` are user ids (map them through `GET /public/core/v3/users`); a folder's project is the `parentInfo` entry with `parentType` Project. The v3 objects API has no created time or creator, so fall back to it only when FRS fails.

### L-MIG-107  v3 objects rows carry sourceControl and customAttributes (CAI publication) blocks
**Kind:** FACT · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence medium: code only); not probed here
`GET /public/core/v3/objects` entries can include `sourceControl` {`sourceControlled`, `checkedOutBy`, `checkedOutTime`, `hash`, `lastCheckinBy`, `lastCheckinTime`, `lastPullTime`} and, for Application Integration assets, `customAttributes` {`publishedBy`, `publicationDate`}, besides `id`, `path`, `type`, `description`, `updatedBy`, `updateTime`, `tags`. Use them to find checked-out assets before an OVERWRITE import and to see when a CAI asset was last published without calling the -cai host. The references API names its fields differently: `documentType` and `lastUpdatedTime`, and `appContextId` is usually null (dedupe on `id`).

### L-MIG-108  Selective package build: keep closure and SYS refs in exportMetadata, match .dat files, regenerate checksum and contents CSV
**Kind:** RECIPE · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence medium: code only); not probed here
To cut a subset out of a v3 export package: rebuild `exportMetadata.v2.json` from the selected objects plus their in-package `objectRefs` closure and container (Project/Folder) entries - keeping only the selected rows broke imports - and keep the `SYS/` Connection and AgentGroup refs of selected CDI assets; prune refs that point outside the kept set. Match each object to its file as `<path>/<name>.<TYPE>` + `.xml`, `.zip`, `.json` or `.dat` (Mass Ingestion types such as MI_TASK and MI_FILE_LISTENER serialize as `.dat`; missing that extension leaks unrelated MI files into the subset). Drop the old `exportPackage.chksum`, `exportMetadata.v2.json` and `ContentsofExportPackage_<name>.csv` and regenerate all three. Refines L-MIG-019.

### L-MIG-109  Source-control routes are flat under /public/core/v3 (no /sourceControl/ segment): checkout, checkin, undoCheckout, pull, pullByCommitHash, sourceControlAction, repositoryConnection, commitHistory, commit/{hash}, compare/{id}
**Kind:** ROUTE · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence medium: code only); not probed here
The GPL CLI builds every Git call on the pod host as `/saas/public/core/v3/<verb>` with `INFA-SESSION-ID`: POST `checkout`, `checkin`, `undoCheckout`, `pull`, `pullByCommitHash`; GET `sourceControlAction/<id>`, `repositoryConnection?projectIds=|projectNames=`, `commitHistory`, `commit/<hash>`; POST `compare/<objectId>`. It never uses a `/public/core/v3/sourceControl/...` prefix, which corroborates the flat paths recorded in the KB over the other CLI's `sourceControl/{checkout,checkin,pull,commit}` variant. checkin/checkout/undoCheckout bodies are `{"objects":[{"id":"<frsId>","includeContainerAssets":true}]}` (checkin adds `summary`, optional `description`). Another client calls `/public/core/v3/sourceControl/{checkout,checkin,pull,commit}`, but with no test, change note or live check behind it, while its verified routes all carry one: treat that form as unverified. Refines L-MCP-137.

### L-MIG-110  Compare asset versions is POST /public/core/v3/compare/<objectId> with source/destination = commit hash or CURRENT-VERSION
**Kind:** ROUTE · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence medium: code only); not probed here
`POST /public/core/v3/compare/<objectId>` with body `{"source":"<old commit hash | CURRENT-VERSION>","destination":"<new commit hash | CURRENT-VERSION>","outputFormat":"JSON"|"TEXT"}`. Use the literal `CURRENT-VERSION` for an uncommitted working copy. The KB lists `compare` among the GET routes without an id or body; this client sends a POST with the object id in the path. Conflicts with L-MIG-097: probe before relying on either.

### L-MIG-111  commitHistory paginates with page/perPage (not limit/skip) and filters by id and branch; results are under commits[]
**Kind:** GOTCHA · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence medium: code only); not probed here
`GET /public/core/v3/commitHistory?page=<n>&perPage=<size>&q=id=="<frsId>" and branch=="<branch>"` pages by a 1-based `page` and `perPage`, unlike the limit/skip paging of other v3 lists. Each page returns `{"commits":[...]}`; stop when `commits` is empty. `branch` is needed only when it differs from the org's configured branch. A `q=id==` filter works as well as the path==/type== form the KB records. Refines L-MIG-097.

### L-MIG-112  pullByCommitHash and commit/{hash} can search project-level repositories: searchCustomRepositories and repoConnectionId
**Kind:** ROUTE · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence medium: code only); not probed here
`POST /public/core/v3/pullByCommitHash {"commitHash":"<hash>","searchCustomRepositories":true,"repoConnectionId":"<repoConnId>","relaxObjectSpecificationValidation":true}` pulls every object in one commit. `GET /public/core/v3/commit/<hash>?searchCustomRepositories=true&repoConnectionId=<id>` reads a commit's details. Without these flags only the org's global repository is searched, so a hash that was committed to a project-level repository looks missing. Get the repo connection ids from `GET /public/core/v3/repositoryConnection?projectNames=<a>,<b>`. `relaxObjectSpecificationValidation:true` (also accepted on `pull`) ignores objectSpecification entries whose sources are not in the pulled assets. Refines L-MIG-097.

### L-MIG-113  Query objects by source-control and publication state through v3 objects q= fields
**Kind:** RECIPE · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence medium: code only); not probed here
`GET /public/core/v3/objects?limit=<n>&skip=<m>&q=<clauses joined by ' and '>` accepts `sourceControl.checkedOutBy=="<user>"`, `sourceControl.checkedOutTime>=<ts>`, `sourceControl.lastCheckinBy=="<user>"`, `sourceControl.lastCheckinTime>=<ts>`, `sourceControl.sourceControlled==true`, `sourceControl.hash==<hash>` (a trailing `*` matches a partial hash), `customAttributes.publishedBy=="<user>"`, `customAttributes.publicationDate>=<ts>`, `updatedBy=="<user>"` and `updateTime>=<ts>`, besides `type`, `location` and `tag`. Use them to list everything a user still has checked out before a release, or what changed since the last check-in. Note: the client sends `sourceControl.hash <=`, which looks like a bug, so use `==`.

### L-MIG-114  v3 references carry appContextId, the v2 id: the bridge across the v3-ids-don't-work-on-v2 rule
**Kind:** GOTCHA · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence high: code plus its tests, change notes or live-check notes); not probed here
v3 `objects`/`lookup` ids are federated ids and fail on v2 endpoints. `GET <baseApiUrl>/public/core/v3/objects/<federatedId>/references?refType=Uses|usedBy&limit=50&skip=<n>` (at most 50 per page) returns references that each carry `appContextId`, the service-specific id that v2 task, job and connection calls accept. Use `usedBy` on a connection to list every asset that a connection update affects, before you change it. Refines L-MIG-034.

### L-MIG-115  v3 import spec for promotion: REUSE by default, OVERWRITE only the exported assets, mapping-task conflict flags
**Kind:** RECIPE · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence low: a comment or README claim); not probed here
`POST /public/core/v3/import/<jobId>` body `{"name":..,"importSpecification":{"defaultConflictResolution":"REUSE","objectSpecification":[{"sourceObjectId":"<id>","conflictResolution":"OVERWRITE","additionalProviderFlags":[{"key":"mapping_conflict_policy_existing","value":"RETAIN|REPLACE"},{"key":"mapping_conflict_policy_new","value":"RESET"}]}]}}` (the provider flags go on MTT objects only, and RETAIN keeps persisted in-out values). Never OVERWRITE projects, folders, connections or runtime environments. Terminal states include PARTIAL_SUCCESS and CANCELLED, and upload returns NOT_STARTED. Export takes `?includeTagInformation=true`. The author marks this not yet run live. Refines L-MIG-013.

### L-MIG-116  Promotion manifest guards for export and import
**Kind:** PATTERN · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence medium: code only); not probed here
Write a manifest beside each exported zip (source env and org, job, object list, sha256 of the package). The import tool previews by default. It refuses a package from the same org as the target (promotion) and a package outside the export directory, and refuses when the checksum no longer matches the manifest. It exports the target's own pre-change copy first, so rollback re-imports that copy, and rollback refuses packages from other orgs.

### L-MIG-117  For CAI objects repoInfo.repoHandle is the repository EntryId, not a v2 id
**Kind:** GOTCHA · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence high: code plus its tests, change notes or live-check notes); not probed here
In `exportMetadata.v2.json` (and the CLI's per-object sidecar JSON) Data Integration and SYS objects carry a 20-character v2 id in `metadata.repoInfo.repoHandle` (for example `<orgId>0B00000000001D` for a connection, `<orgId>25...` for an AgentGroup), but PROCESS, AI_CONNECTION, AI_SERVICE_CONNECTOR, GUIDE and PROCESS_OBJECT entries carry the CAI EntryId (`<id>-gt-<n>-<timestamp>::pd.xml`, `::conn.xml`, `::po.xml`). Projects have `repoInfo: null`. An id map that treats repoHandle as a v2 id must branch on objectType; for CAI assets map by v3 objectGuid or by path and name. Refines L-MIG-036.

### L-MIG-118  Per-environment substitution of CAI assets by XSLT before packaging
**Kind:** RECIPE · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence high: code plus its tests, change notes or live-check notes); not probed here
Promote one source tree and rewrite environment-specific settings per target with identity-copy XSLT 2.0 (Saxon, the engine CAI itself uses): move to agent = replace `sfd:deployment/sfd:targetLocation` text or insert one when missing; move to cloud = drop `sfd:deployment/sfd:targetLocation`; connection to agent = replace `con:agent` text; set `sfd:deployment/@tracingLevel` and `@suspendOnFault` (add the attribute when absent); replace `sfd:rest/sfd:allowedGroups|allowedUsers` from a mapping file. Drive includes and excludes per environment from a properties file (for example: all `*.PROCESS.xml` to agent group X, except `SCH-*` schedulers). With the REST migration API, recompute the changed files' checksum lines afterwards.

### L-MIG-119  Git-based CAI CI/CD: snapshot, build once, back up the target, import, publish
**Kind:** PATTERN · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence high: code plus its tests, change notes or live-check notes); not probed here
Snapshot: export the project (list query `location==<project>`), unzip and expand nested zips into `src/`, delete the generated `*.zip`, `exportMetadata.v2.json`, `exportPackage.chksum` and contents CSV, clean `src/` first so deletions and renames show in git, regenerate the publish list, commit. Build: copy `src/` to a work dir, apply per-environment transforms, re-zip nested objects and rebuild the package (metadata and checksums regenerated). Deploy per environment: export the target's current state as a backup artifact first, import, then publish from an ordered list. Build the package once and promote the same file from test to prod.

### L-MIG-120  Vendor-CLI workspace layout: per-object sidecar JSON and .nzip folders for nested zips
**Kind:** FACT · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence high: code plus its tests, change notes or live-check notes); not probed here
The old IICS Asset Management CLI (`iics extract`) writes each object file plus a hidden sidecar `.<name>.<TYPE>.json` holding that object's `exportedObjects` entries and its dependencies' entries; `iics package -w <workspace> -f <list>` rebuilds `exportMetadata.v2.json` and the checksums from these sidecars. Nested zips (DTEMPLATE, MTT, SYS Connection and AgentGroup) are kept expanded as `<name>.<TYPE>.zip.nzip/` folders by a helper. `<folder>.Folder.json` and `<project>.Project.json` are OData FRS entity dumps (`"type":"OData.frs.Folder"`, `"id":"Folders(<guid>)"`). Package lists name `Explore/<project>.Project` or `Explore/<project>/<folder>.Folder`; publish lists name `Explore/<project>/<folder>/<name>.<TYPE>` without `.xml`.

### L-MIG-121  Redeploy with a package that leaves out the Connections folder so target connection settings survive
**Kind:** PATTERN · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence high: code plus its tests, change notes or live-check notes); not probed here
Keep two package lists per project: `all_designs` (project-level, used once for the first install) and `all_exclude_connections` (every folder except Connections and SYS, used for every later deployment). Excluding the connection objects means an OVERWRITE import cannot reset the agent binding, endpoint or secrets that were set by hand in the target after the first install. Distributions follow the same split (`<Bundle>_InitialInstall_All_Designs.zip`, `<Bundle>_Update_Excluding_Connections.zip`). Dependencies outside the package (shared connections, other projects) must be imported first. Refines L-MIG-011.

### L-MIG-122  exportPackage.chksum is a Java properties file: skip '#' header lines
**Kind:** FACT · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence high: code plus its tests, change notes or live-check notes); not probed here
A vendor-built package's `exportPackage.chksum` starts with `#` comment lines (a blank `#` and a `#<date>` timestamp) before the `<path>=<SHA-256 upper-case hex>` lines, with spaces in keys escaped as `\ `, which is the `java.util.Properties` store format. A checksum rewriter must keep or skip `#` lines rather than parse them as entries. That 2018 package also had no opaque object-hash lines, so do not assume every package has them. Refines L-MIG-019.

### L-MIG-123  Commit export trees with line-ending conversion off
**Kind:** GOTCHA · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence medium: code only); not probed here
Use a `.gitattributes` with `* -text`, `*.xml text eol=lf`, `*.json text eol=lf`, and `binary` for `*.bin`, `*.zip`, `*.png` and `*.jpg`. Automatic CRLF conversion rewrites the CAI XML, the IMF JSON in `bin/@<n>.bin` and the sidecar JSON, so any reuse of the original checksum lines would fail with MigrationSvc_073 and diffs would be noisy. Sorting connector actions, process objects and fields by `@name` with an XSLT before committing also keeps connector diffs readable, because the designer does not sort them.

## Superseded / overturned (kept so nobody re-learns them)

### L-MIG-061  Design-object authoring is UI-only because POST /public/core/v3/objects returns 405, overturned 2026-09-28
**Was believed:** 2026-07-04 to 2026-07-08, and again 2026-09-20 to 2026-09-21 · **Overturned by:** L-MIG-023
With the v3 objects POST at 405 and guessed create paths at 404, mappings, rule specs, processes, business entities and ingestion tasks were believed to need a UI author. The migration import writes objects by clone or from a built package.

### L-MIG-062  There is no v3 export/import API on this org; promotion is author-time UI, overturned 2026-09-28
**Was believed:** 2026-07-04 to 2026-07-08 · **Overturned by:** L-MIG-023
A promotion script reported the v3 export and import routes as 404 and planned per-asset UI export plus warehouse re-pointing. The same routes worked for other sessions on the same org; the 404 was a path, host or role problem.

### L-MIG-063  The migration clone backdoor is closed: import/package returns 404 MigrationSvc_025, overturned 2026-07-26
**Was believed:** 2026-07-26 (one pass) · **Overturned by:** L-MIG-009
A probe that sent `application/json` to `/public/core/v3/import/package` concluded the clone route was closed. The route needs `multipart/form-data`; what an empty org lacks is a same-type template, not the route.

### L-MIG-064  An empty type-filtered census proves the type is unsupported, overturned 2026-09-25
**Was believed:** July 2026 to 2026-07-25 · **Overturned by:** L-MIG-002
A type-filtered count of 0 from the v3 objects list was used as capability evidence. The filter is not validated: fabricated types return the same empty envelope.

### L-MIG-065  A mapping's connection and SQL are compiled into a binary blob, so a package edit cannot retarget a mapping, overturned 2026-09-22
**Was believed:** 2026-07-05 to 2026-07-09 · **Overturned by:** L-MIG-029
In July the DTEMPLATE `bin/@3.bin` entry was read as a compiled binary, direct edits failed with MigrationSvc_031, and clone-retarget of mappings was recorded as impossible ('fails for DTEMPLATE'). Later exports held IMF JSON, a 22-character GUID swap worked, and mappings were synthesized from scratch.

### L-MIG-066  The import rejects hand-built packages with MigrationSvc_030; upload only genuine exports, overturned 2026-09-29
**Was believed:** 2026-06-28 to 2026-09-28 · **Overturned by:** L-MIG-022
A hand-built package was rejected with MigrationSvc_030 in June, and a September draft runbook repeated the rule. Self-built packages import when the metadata, the real folder and project entries and the checksums are right; 030 is what an empty or malformed multipart gets.

### L-MIG-067  Anything a migration import creates needs a UI click to deploy or publish, overturned 2026-09-28
**Was believed:** 2026-07-26 to 2026-09-22 · **Overturned by:** L-MIG-024
The July verdict table said import creates an object but deploying or publishing it is always a UI click. CAI publish (`asset/v1/publish`) and DBMI deploy (`task/deploy` on `<pod>-ing`) are headless follow-ups; MDM model deploy is still UI in these sources.

### L-MIG-068  Objects authored headless in a shared org disappear within a day, overturned 2026-09-24
**Was believed:** 2026-09-23 to 2026-09-24 03:00Z · **Overturned by:** L-MIG-055
A read-only scan found none of 13 clone-authored objects (9 DBMI tasks, 4 CAI processes) and concluded that authoring in a shared org is not durable. The scan used the wrong type name, and some objects sat in another user's project.

### L-MIG-069  No cross-org export/import is available; promotion only re-points within one org, overturned 2026-09-29
**Was believed:** 2026-07-04 · **Overturned by:** L-MIG-045
An early promotion design treated the v3 export and import as a same-org tool (re-point assets between runtime environments) and stated that no cross-org path existed. A full org-to-org migration later ran on the same API.

### L-MIG-070  Export returns the zip synchronously; the /export/jobs and /import/jobs endpoints are the async form, overturned 2026-09-28
**Was believed:** 2026-07-04 · **Overturned by:** L-MIG-003
One early note said `POST /saas/public/core/v3/export` returned the zip directly and that the job endpoints `/export/jobs` and `/import/jobs` 404 or 400 on some orgs. Export is a job: the POST returns an id, `GET /export/<id>` gives the state and `GET /export/<id>/package` the zip; the `/jobs` paths are not routes.

### L-MIG-071  The clone list stops at MDM objects and rule specs; with MI_TASK at 0 there is nothing to clone for ingestion, overturned 2026-09-28
**Was believed:** 2026-07-26 to 2026-09-22 · **Overturned by:** L-MIG-023
The July skill listed clone proofs only for BUSINESS_ENTITY, MDM_SRC_SYSTEM, reference entities and RULE_SPECIFICATION, and recorded Mass Ingestion as having nothing to clone. DBMI_TASK and CAI PROCESS clones followed in September.

### L-CLEAN-028  The headless delete surface is five DELETE endpoints; design objects have no headless delete, overturned 2026-09-28
**Was believed:** July 2026 to 2026-08-20 · **Overturned by:** L-CLEAN-006
The July corpus listed only connection, users, userGroups and catalog-source DELETEs as proven ('that is all') and left DELETE on mttask, mapping, runtimeEnvironment and schedule untested. v2 DELETE works on seven resources and FRS deletes design objects.

### L-CLEAN-029  DELETE /public/core/v3/users/{id} returns 405; delete through the collection and recreate, overturned 2026-09-28
**Was believed:** 2026-07-25 to 2026-09-28 · **Overturned by:** L-CLEAN-009
An endpoint table recorded GET, PUT, PATCH and DELETE on `/public/core/v3/users/{id}` as 405, although another section of the same corpus listed DELETE as supported. DELETE answers 204.

### L-CLEAN-030  An FRS delete is DELETE /frs/api/v1/Documents('<id>'), overturned 2026-09-26
**Was believed:** 2026-09-25 to 2026-09-26 · **Overturned by:** L-CLEAN-005
A runbook note recorded `Documents('<id>')` as the repository delete. That call gives 403; `BaseEntities('<id>')`, the call the Explore UI makes, deletes.

### L-CLEAN-031  Agents, runtime environments, projects, MDM content and catalog sources have no headless delete, overturned 2026-09-28
**Was believed:** 2026-08-20 to 2026-09-28 · **Overturned by:** L-CLEAN-003
An August cleanup did these in the UI and kept an exact-id checklist. Agents and runtime environments delete with v2 DELETE, and empty folders and projects with FRS DeleteEntities; catalog-source definitions still need the UI (L-CLEAN-015).

### L-CLEAN-032  The catalog-source management prefix is not routed on some orgs, so catalog-source delete is UI-only, overturned 2026-09-29
**Was believed:** 2026-08-20 to 2026-09-28 · **Overturned by:** L-CLEAN-015
In August the catalog-source DELETE returned an empty-body 404 on every host of one org while search worked with the same token. On the same org the prefix answered 200 later, and a REST DELETE purges a source (only the definition delete stays in the UI).

### L-CLEAN-033  DBMI tasks have no delete API; delete them in the Explore UI, overturned 2026-09-26
**Was believed:** 2026-09-25 to 2026-09-26 · **Overturned by:** L-CLEAN-005
A dead DBMI task was first removed through the Explore UI by browser automation because no delete API was known. The Explore UI itself calls FRS `BaseEntities('<id>')` DELETE, which works headless.
