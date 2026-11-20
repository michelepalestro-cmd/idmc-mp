# Export & Import (v3 Migration API)

**Answers:** How do I export, upload and start an import headless? What do `REUSE` and `OVERWRITE` do? What does a
package not carry, and what must follow an import? What does each `MigrationSvc_*` error mean? How does a Git
source-control promotion fit next to export and import?

**Read when:** moving, cloning or overwriting design objects between projects or orgs; an import fails; the target
project is connected to a Git repository.

**Key rules:**
- Export is a job (POST, poll, download); import is an upload as `multipart/form-data` part `package`, then
  `POST /public/core/v3/import/<jobId>` (L-MIG-003, L-MIG-008, L-MIG-010).
- An import is all-or-nothing, and `includeObjects` does not exclude objects from validation: drop failing objects
  from the package instead (L-MIG-012).
- `REUSE` keeps a same-name, same-type target object, which may be older than the source; `OVERWRITE` replaces it
  (L-MIG-011).
- A package carries no secrets, schedules, agents, selections, tags, CDGC content, CAI publish or DBMI deploy, so an
  import alone leaves nothing runnable (L-MIG-017, L-MIG-024).
- Packages can hold plaintext CAI secrets: store them 0600 and never print them (L-MIG-018).
- In a source-controlled project, check objects out before an `OVERWRITE` import and check them in afterwards
  (vendor-documented).

**Related:** [Editing Packages Safely](02-editing-packages-safely.md) · [Migration-Clone Authoring](03-migration-clone-authoring.md) · [Org-to-Org Migration Runbook](04-org-to-org-migration-runbook.md) · [Headless Deletes & Org Cleanup](06-headless-deletes-org-cleanup.md) · [Lessons: Migration & Org Management](lessons.md)

**Last verified:** 2026-11-03

> The v3 migration API is the write path for IDMC design objects: the v3 objects catalog is read-only, but export and
> import create, clone and overwrite objects at no IPU cost. Name conflicts resolve by `REUSE` or `OVERWRITE`;
> `objectSpecification` does not work on the import start. Orgs whose projects live in Git also have a
> vendor-documented pull/checkout/check-in path (section 11). The endpoint-level corpus is in the
> [IDMC API & MCP Reference](../reference/idmc-api-mcp-reference).

---

## 1. Plane, host, headers, roles

| Item | Value |
|---|---|
| Base | `https://<pod>.<domain>.informaticacloud.com/saas` (take it from the v3 login's `products[].baseApiUrl` or the v2 `serverUrl`) |
| Prefix | `/public/core/v3/` |
| Header | `INFA-SESSION-ID: <session>` (a v2 `icSessionId` was accepted too) |
| Role | the migration (export/import) role plus object admin. Without it, export answers 403 `MigrationSvc_038` (L-MIG-006). The grant is a free Administrator toggle of about a minute |
| Cost | free: no IPU is consumed by export or import |
| MCP | no managed MCP server covers this API; it is REST only |

The objects catalog is **read-only** (L-MIG-001): `GET /public/core/v3/objects` lists design objects, but `POST` is 405 and a per-object `PATCH` is 404. Create and change objects through import.

## 2. Export

| Step | Call | Success | Notes |
|---|---|---|---|
| Start | `POST /public/core/v3/export` body `{"name":"<name>","objects":[{"id":"<frsGuid>","includeDependencies":true},...]}` | 200 with the job `id` | bare string ids, or a `type` key, give 400 `V3API_007`; an empty `objects[]` gives 400; `GET /export` is 405 (L-MIG-004) |
| Poll | `GET /public/core/v3/export/<id>` (add `?expand=objects` for per-object state) | `status.state` = `SUCCESSFUL`, `status.message` = `Export completed successfully` | also IN_PROGRESS, QUEUED, NOT_STARTED, FAILED |
| Download | `GET /public/core/v3/export/<id>/package` with `Accept: application/zip` | the zip bytes | write it with mode 0600 (section 7) |

(L-MIG-003.) The ids are v3 object ids (`frsGuid`) from `/public/core/v3/objects`. Exporting by a CAI process GUID read from inside the process XML gives 400 `MigrationSvc_034 Object resolution failed` (L-MIG-007).

Measured: a 194-object scope with `includeDependencies` exported 223 objects (a 616 KB zip) in about 20 s. The dependencies it pulled in were runtime environments (including the hosted one), connections, CAI connectors and app connections, an Add-On Bundle mapping template and bundle rule specs.

An export is read-only for the source org. When one migration library enforces "source read-only", let export POSTs through and block every other non-GET call (L-MIG-043).

## 3. Import

### 3.1 Upload (L-MIG-008)

```
POST /public/core/v3/import/package
Content-Type: multipart/form-data; boundary=<b>

--<b>
Content-Disposition: form-data; name="package"; filename="pkg.zip"
Content-Type: application/zip

<zip bytes>
--<b>--
```

It answers 200 `{"jobId":"<id>","checksumValid":true,...}` in state `NOT_STARTED`: the package is **staged, not committed**. `checksumValid:false` means `exportPackage.chksum` does not match the zip (see [Editing Packages Safely](02-editing-packages-safely.md)). Only the field name `package` has been used.

The route answers differently by Content-Type (L-MIG-009):

| Sent | Answer | Meaning |
|---|---|---|
| `application/json` | 404 `MigrationSvc_025 'Import request with identifier [package] doesnt exist'` | the service read `package` as an import id: a **live** handler, not a dead route |
| `application/zip`, `application/octet-stream` | 415 | wrong media type |
| `multipart/form-data`, empty or invalid zip | 400 `MigrationSvc_030 'Invalid import package'` | the validator was reached (the route-discovery success signal) |
| `multipart/form-data`, valid package | 200 | staged |
| `POST /public/core/v3/import` (bare) | 404 `No static resource core/v3/import` | not a route |
| `POST /public/core/v3/import/upload` | 415 on JSON; 404 `MigrationSvc_025 [upload]` | not a route (the segment is read as an import id) |

### 3.2 Start (L-MIG-010)

```
POST /public/core/v3/import/<jobId>
{"name":"<name>","importSpecification":{"defaultConflictResolution":"REUSE","includeObjects":[]}}
```

- Use `REUSE` or `OVERWRITE` (section 4).
- **The start route drops the `/package` segment.** `POST /import/package/<jobId>` is 404 `No static resource`.
- `includeObjects` can list object ids, but it does **not** exclude the others from validation (L-MIG-012).
- `objectSpecification` (map a source object onto a named existing target object) returned `V3API_007` in every shape tried: `[{sourceObjectId, existingTargetObjectId}]`, `[{sourceObjectId, existingObjectId}]` (L-MIG-013). Use `REUSE`, or edit the package.

### 3.3 Poll and read the log

- `GET /public/core/v3/import/<jobId>` until `status.state` leaves `IN_PROGRESS`, `QUEUED` or `NOT_STARTED`. It ended `SUCCESSFUL` or `FAILED` in every run recorded here: one object failing validation rolls back all of them (L-MIG-012). Informatica also documents a `PARTIAL` state, never seen here; treat every state but `SUCCESSFUL` as not promoted, and on a poll timeout read the job back instead of importing again (L-MIG-132).
- `GET /public/core/v3/import/<jobId>?expand=objects` returns the per-object results. `GET /public/core/v3/import/<jobId>/log` with `Accept: */*` returns the log.
- A 214-object import ran about 3.5 minutes.

Success envelope (no `expand`):

```json
{"id":"<jobId>","name":"<name>","startTime":"...","endTime":"...",
 "status":{"state":"SUCCESSFUL","message":"Import completed successfully"},
 "objects":null,"sourceOrgId":"<source orgIdV3>","checksumValid":true}
```

A per-object result (with `?expand=objects`):

```json
{"sourceObject":{"id":"<source frsGuid>","name":"<name>","path":"/<project>/<folder>","type":"MTT"},
 "targetObject":{"id":null,"name":"<name>","path":"/<project>/<folder>","type":"MTT"},
 "status":{"state":"SUCCESSFUL","message":"Create object"}}
```

`message` is `Create object` or `Reuse existing object`. **`targetObject.id` came back null**, so read the target ids from the target's objects list in the destination folder when you build the id map (see [Org-to-Org Migration Runbook](04-org-to-org-migration-runbook.md)).

Failure envelope: the whole import fails and every other object is skipped.

```json
{"error":{"code":"MigrationSvc_031",
  "message":"Import failed. Correct the errors in the Select Assets section and try again.",
  "details":[{"message":"Object name [<name>] type [<TYPE>] path [/<project>/<folder>] message [<reason>]"},
             {"message":"Object name [<other>] type [MTT] path [/<project>/<folder>] message [Object skipped because of previous failures]"}]}}
```

## 4. Conflict resolution and non-empty targets

| Mode | Effect | Use |
|---|---|---|
| `REUSE` | an object with the same **name and type** already in the target is kept (`Reuse existing object`); only missing objects are created | the default for a migration into an org that already holds content (L-MIG-011) |
| `OVERWRITE` | the target object is replaced | rebuilding your own object under the same GUID (a clone rebuild, a mapping retarget, a DBMI or CAI change) |

With `REUSE`:

- Bundle content (Add-On Bundle templates, bundle rule specs) comes from the target's own copy, which may be a different build (L-MIG-038).
- Nothing unrelated is overwritten.
- A reused copy may be **older** than the source. Compare every reused pair whose source changed recently, or re-import that one object with `OVERWRITE`.
- Test-import a small set first (for example the bundle template plus one task).

A target that already holds content can contain objects with the same names in other folders. Import into a dedicated project, and address everything by id afterwards (L-MIG-037).

In a project under source control, an `OVERWRITE` import of a source-controlled asset needs a checkout first (section 11).

## 5. What a package does NOT carry (L-MIG-017)

| Not carried | Do this instead |
|---|---|
| connection passwords and keys (masked; exports never carry them) | set them from host files after import, then `GET /api/v2/connection/test/<connId>` (see [Secure Agent & Connections](../02-secure-agent)) |
| Secure Agents; runtime-environment service and connector selections | install and register the agent; `GET/PUT.../runtime/api/v2/runtimeEnvironment/<reId>/selections/ui` |
| schedules and their bindings | create the schedules unbound, then bind at cutover (see [Cutover & Rollback](05-cutover-rollback.md)) |
| object tags | `POST /public/core/v3/TagObjects` (section 6) |
| DBMI deploy and start | `task/deploy` and `job/start` on `-ing` (see [DBMI over REST](../06-cdc-ingestion/01-dbmi-over-rest-create-deploy-run-stop.md)) |
| CAI publish | `POST https://<pod>-cai.<domain>.informaticacloud.com/active-bpel/asset/v1/publish` in dependency order (see [Application Integration (CAI)](../07-app-integration)) |
| CDGC catalog sources, glossary, links, classifications | recreate them through the CDGC APIs (see [Catalog & Governance (CDGC)](../09-catalog-lineage)); a v3 export of a governance object fails with `MigrationSvc_034` |
| profile rule occurrences | re-bind the rule specs (target frsIds) to the columns (see [Data Quality & Profiling](../08-data-quality)) |
| external callers (hard-coded ids, org ids, CAI URLs) | a caller scan and a flip tool (see [Org-to-Org Migration Runbook](04-org-to-org-migration-runbook.md)) |

An import alone leaves nothing runnable (L-MIG-024).

## 6. Tags after an import (L-MIG-016)

Imports drop tags. Re-apply them:

```
POST /public/core/v3/TagObjects
[{"id":"<frsGuid>","tags":["<tag>"]},...]        (at most 50 items per call)
```

It answers 204, or a per-item status (200/201/204/207). Folders and projects cannot be tagged (they fail "of type: [Folder]"); use the project name as the scope marker. Read the tags back, or tag-based audits and later exports will miss the imported objects.

## 7. Secrets in packages (L-MIG-018)

- Connection passwords are masked in exports. But a CAI app connection authored with `encrypted="false"` carries its OAuth client id and secret in **plaintext**, so every package containing it does too.
- Store packages in a private location with mode 0600 (not a desktop, a shared drive or a repository), leave a move note where they used to be, never print package contents into logs, and rotate the exposed secret after the migration.

## 8. Reserved and special objects

| Object | Behaviour | Do |
|---|---|---|
| runtime environment `Informatica Cloud Hosted Agent` | reserved: import cannot create it (`REPO_38210`) | if the target is not entitled to the hosted runtime, remap the bound objects to a self-hosted runtime environment inside the package (L-MIG-015) |
| Add-On Bundle templates and bundle rule specs | system content; their export can be 403 `MigrationSvc_038` for a non-admin, depending on org and user | do not export them; import with `REUSE` so the target's copy is used (L-MIG-006) |
| `TOOL_CONNECTION` (MCP tool connection) | import fails `MigrationSvc_031` 'Internal error', even with the URL and token fixed | recreate it in the Application Integration designer (L-MIG-039), only possible on an org from the AI Agent Engineering private preview; newer orgs have no such type (L-MCP-081) |
| `MCP_SERVER` | imports | attach the recreated tool connection to it (preview orgs), or expose CAI processes as its tools |
| DBMI initial-load (UNLOAD) tasks | vendor validation 403 when the target agent has no Database Ingestion engine | enable the engine first, or create them later with `task/create` (L-DBMI-032) |
| CDGC governance objects | `MigrationSvc_034` | not migratable this way |

## 9. Error codes

| Code | Where | Meaning | Fix |
|---|---|---|---|
| 400 on an empty export body | export | the route is writable | send a real body |
| 400 `V3API_007` | export or import start | body shape: bare ids, a `type` key, `objectSpecification` | `[{"id":...}]`; drop `objectSpecification` |
| 400 `MigrationSvc_041 'No asset selected for export operation'` | export | the body parsed, but nothing exportable was selected (for example an empty default project) | pick another object; do not sweep body shapes (L-MIG-005) |
| 403 `MigrationSvc_038 'User does not have required permissions'` | export | the migration role is missing, or an Add-On Bundle template for a non-admin | grant the role; skip bundle content |
| 400 `MigrationSvc_034 'Object resolution failed'` | export | not an IDMC object id (for example a process GUID), or a CDGC governance object | use the id from `/public/core/v3/objects` |
| 404 `MigrationSvc_025 'Import request with identifier [X] doesnt exist'` | upload | JSON sent to `/import/package`, or a wrong path segment | `multipart/form-data` |
| 400 `MigrationSvc_030 'Invalid import package'` | upload | empty or malformed zip | a real export, or a correctly built package (L-MIG-022) |
| 500 `MigrationSvc_031` (`type [DTEMPLATE]... An error occurred while loading the mapping`) | start | a transient service fault, or a mapping defect | retry; rule out package defects first (L-MIG-028) |
| `MigrationSvc_031 'Import failed. Correct the errors in the Select Assets section'` with details | start | one object failed validation; everything else skipped | remove that object from the package (L-MIG-012) |
| `MigrationSvc_031` with **empty** details | start | a dangling `objectRefs` entry in `exportMetadata.v2.json`; on a CAI package, a connection or connector a process references is missing | remap or remove the ref (see [Editing Packages Safely](02-editing-packages-safely.md)); for CAI, add every referenced connection and connector and limit the import with `includeObjects` (L-CAI-156) |
| 'Internal application provider error' on a PROCESS | start | the process calls a shared connection or connector that is not in the package | add its XML to the package outside `includeObjects` (L-CAI-156) |
| `XFER_500 'Unknown conflict resolution policy'` | FRS `CopyEntities` | `conflictResolution: "NONE"` | omit the key (L-MIG-087) |
| `MigrationSvc_056 'One or more objects are missing required dependent objects'` | start | a dependency is neither in the package nor in the target by name | export with `includeDependencies:true` (L-MIG-014) |
| `MigrationSvc_073 'package has been modified'` | start | a changed file's hash (often `exportMetadata.v2.json`) was not updated | re-hash every changed file |
| `REPO_38210` | start | the reserved hosted runtime name | remap to a self-hosted runtime environment |
| 500 `Objects Listing Failed: null` | `GET /public/core/v3/objects` | transient, seen while another session was importing | retry once or twice (L-CLEAN-018) |

## 10. Inventory and dependency routes used with migrations

- Page `GET /public/core/v3/objects?limit=200&skip=<n>` until `skip` reaches `count`. The `q` filter is not validated (a fabricated type returns `{"count":0,"objects":[]}`), so filter client-side or use exact type names (L-MIG-002, L-MIG-035).
- Dependency closure: `GET /public/core/v3/objects/<frsGuid>/references?refType=uses&limit=50&skip=<n>`, and `refType=usedBy` (L-MIG-034).
- Move objects between folders, ids preserved: FRS `POST https://<pod>.<domain>.informaticacloud.com/frs/api/v1/MoveEntities` with `IDS-SESSION-ID` (L-MIG-054).
- Copy objects (for example view-only walk-through copies of mappings) with FRS `POST .../frs/api/v1/CopyEntities`:
  `{"xferSpec": {"targetLocationId": "<folderId>", "sourceSpecArr": [{"sourceEntityId": "<frsId>", "destName": "<new name>",
  "destDesc": "<text>", "resetExpiryTime": false, "mergeTags": ""}]}}` answers XFER_200, with the copy's id in
  `value[].statusArr[].tgtGuid`. Leave `conflictResolution` out (`"NONE"` fails with XFER_500 'Unknown conflict resolution
  policy'); fix a description later with `PATCH .../frs/api/v1/Documents('<id>')` and read it back. A mapping copy has no
  task, so it adds nothing to lineage: keep copies in a project outside the IICS catalog source's filter. Record each
  source's `updateTime` before and after to prove the originals were not touched; undo is `DELETE .../BaseEntities('<copyId>')`
  (L-MIG-087, 2026-11-02; 16 mappings copied into a 4-folder project).

## 11. Source control (Git) as a promotion path (documented by the vendor, not exercised here)

Projects connected to a Git repository have a second promotion path in the Platform REST API v3: pull a commit into
the target org instead of importing a package. Same base and header as export and import
(`<serverUrl>/public/core/v3/`, `INFA-SESSION-ID`). Everything in this section comes from the vendor's Platform REST
API v3 'Source control' resources and the Asset Management guide; no call here has been exercised against an org, so
probe each route (an empty body should reach a validator) before you build on it.

| Call | Purpose | Answer |
|---|---|---|
| `GET /public/core/v3/repositoryConnection?projectIds=<id>` | which repository each project uses | the per-project repository connections |
| `POST /public/core/v3/pull` | load objects from one commit; overwrites existing assets | operation id, `status.state: NOT_STARTED` |
| `POST /public/core/v3/pullByCommitHash` | load only what one commit changed (`searchCustomRepositories`; `repoConnectionId` for project-level repositories) | operation id |
| `POST /public/core/v3/checkout` · `/undoCheckout` | lock objects for change; all-or-nothing (the rest become `CANCELLED`) | operation id |
| `POST /public/core/v3/checkin` | commit the checked-out objects; needs `summary` (at most 255 characters); accepts `includeContainerAssets` | operation id |
| `GET /public/core/v3/sourceControlAction/<id>?expand=objects` | poll any of the above | `NOT_STARTED`, `IN_PROGRESS`, `SUCCESSFUL`, `FAILED`, `WARNING`; per object also `SKIPPED`, `CANCELLED` |
| `GET /public/core/v3/commitHistory?q=id=='<id>'` | the history of one asset (`type` required for an asset; `perPage` at most 100) | commits |

**Promote a commit into the target org**

1. Find the repository: `GET /public/core/v3/repositoryConnection?projectIds=<projectId>`.
2. Pull, remapping connections and runtime environments onto the target's own:

```json
POST /public/core/v3/pull
{"commitHash": "<hash>",
 "objects": [{"path": ["<project>"], "type": "PROJECT"}],
 "objectSpecification": [
   {"source": {"path": ["<connection-name>"], "type": "Connection"}, "target": {"id": "<target-connection-id>"}},
   {"source": {"path": ["<runtime-env>"], "type": "AgentGroup"}, "target": {"id": "<target-runtime-env-id>"}}]}
```

   Expect an operation id in state `NOT_STARTED`. GitHub accepts the first 7 characters of the commit hash; other
   hosts need all 40. Objects are given by `id`, or by `path` plus `type` (`DTEMPLATE`, `MTT`, `DSS`, `DMASK`, `DRS`,
   `DMAPPLET`, `MAPPLET`, `BSERVICE`, `HSCHEMA`, `PCS`, `FWCONFIG`, `CUSTOMSOURCE`, `MI_TASK`, `WORKFLOW`, `TASKFLOW`,
   `UDF`; check-in also takes `PROCESS`, `AI_CONNECTION`, `AI_SERVICE_CONNECTOR`, `GUIDE`, `PROCESS_OBJECT`,
   `HUMAN_TASK`). `relaxObjectSpecificationValidation` ignores mapped sources that are not in the pull. Unmapped
   connections, runtime environments and schedules are matched by name in the target.
3. Poll `GET /public/core/v3/sourceControlAction/<id>?expand=objects` until `SUCCESSFUL`, `WARNING` or `FAILED`, and
   read every object's state. Dependencies that live in other projects are not pulled; the response lists them.
4. Make the result runnable exactly as after an import (section 5): secrets, selections, schedules, CAI publish, DBMI
   deploy.

**Interplay with export and import**

- Overwriting a source-controlled asset by import requires a checkout first:
  `POST /public/core/v3/checkout {"objects":[{"id":"<id>"}]}` → poll → import with `OVERWRITE` →
  `POST /public/core/v3/checkin {"objects":[{"id":"<id>"}],"summary":"<at most 255 characters>"}`, or
  `POST /public/core/v3/undoCheckout` if the import fails (checkout operation ids are kept only 7 days).
- The target org needs the licences of every asset it receives, by either path.

| Limit | Value |
|---|---|
| Objects per pull, and per project or folder | about 1,000 |
| Source-control logs and checkout operation ids | kept 7 days |
| Not source-controllable | runtime environments, connections, Data Integration bundles |
| Repository hosts | GitHub, GitLab (its commit history can display incorrectly), Bitbucket (cloud: Data Integration assets only), Azure DevOps (cloud) |

## 12. Overturned beliefs

| Earlier belief (dates) | What overturned it | Lessons |
|---|---|---|
| "Design authoring is UI-only because `POST /v3/objects` is 405" (2026-07-04 to 2026-07-08; again 2026-09-20/21) | clone and from-scratch packages through import | L-MIG-061 → L-MIG-023 |
| "There is no v3 export/import API on this org" (2026-07-04 to 2026-07-08) | the same routes worked; the 404 was a path, host or role problem | L-MIG-062 → L-MIG-023 |
| "The clone backdoor is closed: `import/package` is 404 MigrationSvc_025" (2026-07-26) | the Content-Type must be multipart | L-MIG-063 → L-MIG-009 |
| "Export returns the zip synchronously; the `/export/jobs` endpoints are the async form" (2026-07-04) | export is a job: POST, poll `/export/<id>`, download `/export/<id>/package` | L-MIG-070 → L-MIG-003 |
| "Anything an import creates needs a UI click to deploy or publish" (2026-07-26) | CAI `asset/v1/publish` and DBMI `task/deploy` are headless | L-MIG-067 → L-MIG-024 |
| "Hand-built packages are rejected with MigrationSvc_030" (2026-06-28; a draft runbook 2026-09-28) | self-built packages import when the metadata and checksums are right | L-MIG-066 → L-MIG-022 |
| "A type-filtered count of 0 from the objects list proves a type is unsupported" (July 2026 to 2026-07-25) | the `q` type filter is not validated: fabricated types return the same empty envelope | L-MIG-064 → L-MIG-002 |

## 13. Lessons in this doc

L-MIG-001 to L-MIG-018, L-MIG-022, L-MIG-024, L-MIG-028, L-MIG-034, L-MIG-035, L-MIG-037 to L-MIG-039, L-MIG-043, L-MIG-054, and the superseded L-MIG-061 to L-MIG-064, L-MIG-066, L-MIG-067, L-MIG-070. Full text: [Lessons: Migration & Org Management](lessons.md).
