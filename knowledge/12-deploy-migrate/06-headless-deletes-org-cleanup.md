# Headless Deletes & Org Cleanup

**Answers:** What can be deleted headless in an IDMC org, with which call, and how do I read the delete back? How do
I build a keep list that does not lie, back everything up, and delete in the right order and in safe waves? What must
never be deleted? How do I decommission a source org after a move?

**Read when:** cleaning an org, removing one application's footprint, retiring superseded tasks, or deleting in a
source org after a migration.

**Key rules:**
- Prove the org with a live read before the first delete; destructive scripts assert the expected org id
  (L-CLEAN-001).
- Select by id from an agreed keep list, never by name, date window or "in no taskflow" (L-CLEAN-002, L-CLEAN-020,
  L-CLEAN-025).
- A SAFE verdict must survive a reference scan of every file type the orchestrators and hosts read (JSON, YAML, env,
  cron, plan files) and every other application's keep list (L-CLEAN-034).
- Right before each wave, re-verify every object, export exactly those objects, then DELETE and read back 403
  (L-CLEAN-034).
- Delete in dependency order and in waves; rollback-path objects go only after their soak date (L-CLEAN-034,
  L-CLEAN-013).
- Never delete platform content, and treat a rejected or interrupted tool call as possibly executed (L-CLEAN-016,
  L-CLEAN-017).
- Decommissioning a source org: give every object one verdict from the id map and the import log first
  (L-MIG-073).

**Related:** [Export & Import](01-export-import-v3-migration-api.md) · [Org-to-Org Migration Runbook](04-org-to-org-migration-runbook.md) · [Cutover & Rollback](05-cutover-rollback.md) · [Catalog Sources](../09-catalog-lineage/02-catalog-sources-create-scan-update-purge.md) · [Lessons: Migration & Org Management](lessons.md)

**Last verified:** 2026-11-03

> Almost everything in an IDMC org can be deleted headless: v2 `DELETE` covers mapping tasks, mappings, taskflows,
> connections, agents, runtime environments and schedules; FRS `DeleteEntities` (per-item result codes) and
> `BaseEntities('<id>')` cover repository objects (CAI assets after unpublish, DBMI tasks after undeploy, profiles, DQ
> assets, folders and projects); `DELETE /public/core/v3/users/<id>` removes users. What stays manual: CDGC
> catalog-source definitions (a REST delete only purges them) and CAI assets stuck in the runtime.

---

## 1. Prove the org first (L-CLEAN-001)

- Read the org live before the first delete: `GET /api/v2/org` (`id`, `orgUUID`) and the session-service user endpoint `/session-service/api/v1/session/User` (`name`, `orgId`; its exact host was not recorded). Compare them with the org you intend to clean.
- Destructive scripts assert the expected org id at start and refuse otherwise. When a host holds helpers for two orgs, pin the org in every destructive script; never rely on a default that a switch file can change.
- Show the proof in the first line of every cleanup report: an owner who cannot see which org is being cleaned will stop the run to ask.

## 2. Agree the keep list (L-CLEAN-002, L-CLEAN-004, L-CLEAN-016, L-CLEAN-025)

1. Inventory every object: v3 objects by project, plus the v2 lists of tasks, mappings, connections, runtime environments, agents, schedules and users.
2. Write explicit **KEEP** and **DELETE** lists **by id**; never select by a date window or by a name pattern alone (L-CLEAN-020).
3. For each DELETE candidate, check what uses it and move anything a KEEP object uses into KEEP:
   - FRS `POST https://<pod>.<domain>.informaticacloud.com/frs/v1/GetInboundDocRefs` (who references this document);
   - FRS `POST.../frs/v1/GetAllDependencies` (what it depends on);
   - `GET /public/core/v3/objects/<id>/references?refType=usedBy` (a second source).
   The request bodies of the two FRS actions were not recorded; an address-verification entity stayed in KEEP because a kept mapping used it.
4. Always KEEP platform content (section 9) and anything a peer session created after the cleanup started.
5. **Put every candidate in exactly one category**, from a fresh inventory (L-CLEAN-034):

| Category | Delete in this wave? |
|---|---|
| LIVE: in a lane or a schedule (task-level `scheduleId` included) | no |
| REFERENCED in code **or configuration** | no |
| RAN SINCE `<cutoff>` (taskflow sub-entries included) | no |
| BLOCKED BY A DORMANT TASKFLOW, or on a rollback path | a later wave, after the agreed soak date (for example one green week) |
| SCRATCH, or SAFE and on no other workload's keep list | yes, after the export and the re-verify (section 3.1) |

6. **Scan every file type the orchestrators and hosts read** for task ids and names: `.json`, `.yaml`, `.env`, cron
   entries and plan files, not only `.py` and `.sh`. In one inventory, 25 tasks marked SAFE held only 13 truly safe
   ones: 11 were named in an orchestrator's JSON rollback plan, and 1 belonged to another application sharing the org
   (L-CLEAN-034). Treat bookkeeping fields such as `replaces`, `replaced` or `excluded` lists as non-uses.
7. **Merge the keep lists of every application in the org.** An object another workload owns reads SAFE because
   nothing in your own stack calls it.

## 3. Back up everything first (L-CLEAN-014)

| What | How | Undo |
|---|---|---|
| connections, design content, CAI assets, MDM configuration | v3 export packages by id (`includeDependencies` where needed); chunk large sets (for example 20 objects per package, L-CLEAN-023) | re-import with `REUSE`, then republish CAI; agents and runtime environments must be re-registered |
| MDM business records | `POST https://<pod>-mdm.<domain>.informaticacloud.com/search/public/api/v1/search` with `{"search":"*","entityType":"<be>","recordOffset":0,"recordsToReturn":1000}`, Bearer JWT (identity-service `jwt/Token?client_id=cdlg_app`) plus `IDS-SESSION-ID` and `X-INFA-ORG-ID`. **At most 10,000 records per query**: export larger entities as a union of term and prefix-wildcard queries, and check the union count against the entity count | reload the records |
| CDGC glossary, marketplace, catalog-source definitions | JSON reads of each item | recreate them through the CDGC APIs |
| users | `GET /public/core/v3/users` to JSON | recreate them (section 7) |

Store the backups privately (packages can hold plaintext secrets; L-MIG-018), and append every delete, with its answer and read-back, to a log file.

### 3.1 The per-object gate before each delete wave

Run these steps right before every wave, not once at planning time (L-CLEAN-034):

1. Re-run the inventory and diff it against the approved list; anything that changed goes back to review
   (L-CLEAN-034).
2. Per object, re-verify: the name still matches the id; no task-level schedule (the v2 list hides `scheduleId`, so
   `GET /api/v2/mttask/<id>` each one); not in any lane, linear taskflow (v3 type `WORKFLOW`) or taskflow
   (`GET /public/core/v3/objects/<id>/references?refType=usedBy&limit=50&skip=<n>`, L-MIG-072); no run in the
   activity window, taskflow sub-entries included; no reference in code or configuration; not another workload's
   asset.
3. Export exactly these objects (`POST /public/core/v3/export` with their ids), download the package and open it:
   check that its entry count matches the wave before the first delete.
4. `DELETE /api/v2/mttask/<v2Id>` → 200, then `GET /api/v2/mttask/<v2Id>` → 403 (gone). Delete a schedule the wave
   leaves empty only after confirming that no task or taskflow references it, and confirm that delete through the
   schedule list (section 6).
5. Rescan the Data Integration (IICS) catalog source with Metadata Change Option = Delete, so lineage drops the
   deleted objects (L-CDGC-028).
6. Keep the rollback path (the old tasks plus the orchestrator's previous plan) for one green week, then remove it in
   a later wave with the same steps. Delete your own scratch drafts with the same backup step.

Undo is a v3 import of the wave's package with `REUSE`. The re-created objects get **new ids**, so nothing may call
them by id afterwards (L-CLEAN-034). In one first wave, 13 tasks and 1 empty schedule were deleted this way
(each DELETE 200, each read-back 403) after a 20-entry package was checked, with no lane impact.

## 4. The delete surface

| Object | Delete call | Success | Read-back | Notes |
|---|---|---|---|---|
| mapping task | `DELETE /api/v2/mttask/<v2Id>` (`icSessionId`) | 200 | `GET` → 403 | resolve the v2 id from the v3 id through `frsGuid`; `REPO_52013` if it has its own schedule (L-CLEAN-008) |
| mapping | `DELETE /api/v2/mapping/<v2Id>` | 200 | `GET` → 403 | only when its `tasks[]` is empty; resolve through `assetFrsGuid`; `/api/v2/dtemplate/<id>` is a wrong path (404 HTML) |
| linear taskflow | `DELETE /api/v2/workflow/<v2Id>` | 200 | `GET` → 403 | unbind its schedule first, or delete the schedule |
| schedule | `DELETE /api/v2/schedule/<id>` | 200 | **check the list**: a deleted schedule's `GET` returns an empty 200 shell | |
| connection | `DELETE /api/v2/connection/<id>` | 200 | `GET` → 403 | 403 `REPO_10242` while mappings use it; then 'used by another asset' while a catalog source holds it (L-CLEAN-007) |
| agent | `DELETE /api/v2/agent/<id>` | 200 | `GET` → 403 | also uninstall the binaries on the host |
| runtime environment | `DELETE /api/v2/runtimeEnvironment/<id>` | 200 | `GET` → 403 | after its agents |
| repository objects, batch | `POST https://<pod>.<domain>.informaticacloud.com/frs/v1/DeleteEntities` `{"artifactIds":[...]}` (`IDS-SESSION-ID`) | a per-item `FRS_200` | FRS `FRS_070` not found | `FRS_082` still published or out of date; `FRS_087` project not empty (L-CLEAN-003) |
| one repository object | `DELETE https://<pod>.<domain>.informaticacloud.com/frs/api/v1/BaseEntities('<frsGuid>')` (`IDS-SESSION-ID`) | 204 | gone from the v3 objects list | what the Explore UI calls; `Documents('<id>')` gives 403 (L-CLEAN-005) |
| CAI process, app connection, connector | unpublish (section 8), then FRS | per item | `FRS_070` | a published asset gives `FRS_082` |
| DBMI task | `job/stop`, `job/undeploy` on `<pod>-ing`, then FRS `BaseEntities` | 204 | gone from `task/details` | [DBMI over REST](../06-cdc-ingestion/01-dbmi-over-rest-create-deploy-run-stop.md) |
| profiles and DQ assets | FRS `BaseEntities` or `DeleteEntities` | 204 / `FRS_200` | objects list | profiles move with FRS `MoveEntities` (FRS_200); FRS_108 only on orphan profile documents (L-DQ-124) |
| folders and projects | FRS `DeleteEntities` once empty | `FRS_200` | objects list | `FRS_087` while anything is inside |
| user | `DELETE https://<pod>.<domain>.informaticacloud.com/saas/public/core/v3/users/<userId>` (`INFA-SESSION-ID`) | 204 | `GET /public/core/v3/users` | keep the system users (section 7) |
| user group | `DELETE` on `/public/core/v3/userGroups` | recorded as proven in July 2026; the exact path form was not re-verified | list | |
| glossary domain or term | `DELETE https://idmc-api.<domain>.informaticacloud.com/data360/content/v1/assets/<identity>?scheme=internal` | 2xx | **search for it again**: API-deleted terms can stay searchable, and one record calls a published-term delete a silent no-op | see [Catalog & Governance (CDGC)](../09-catalog-lineage) |
| catalog source | `DELETE https://cdgc-api.<domain>.informaticacloud.com/ccgf-catalog-source-management/api/v1/datasources/<id>` (Bearer JWT, `IDS-SESSION-ID`, `X-INFA-ORG-ID`) | a purge job | the definition **stays listed** | delete the definition in Metadata Command Center (L-CLEAN-015) |
| v3 object | `DELETE /public/core/v3/objects/<id>` | **404** | — | not a delete route |

FRS details:

- FRS wants `IDS-SESSION-ID: <v2 icSessionId>`. With `INFA-SESSION-ID` it returns the login HTML page, which a script can mistake for success.
- Both `/frs/v1/...` and `/frs/api/v1/...` prefixes were used successfully. FRS `$metadata` needs `Accept: */*`.
- A `PATCH` of a Document's `customAttributes` returns 204 and changes nothing (L-CLEAN-019): read back every write.
- A `PATCH` of a Document's `name` does work: `PATCH .../frs/api/v1/Documents('<frsId>')` with `{"name": "<new name>"}` → 204 renames a mapping, mapping task or CLAIRE structure model in place (id unchanged; v3 path and v2 names change at once). The same PATCH on `BaseEntities` gives `400 FRS_068`. Keep `{id, old name}` as the undo (L-MIG-075). A new name with parentheses answers 400 `FRS_082` and nothing changes, the description in the same body included (L-MIG-080); a folder's description is changed with `PATCH /frs/v1/Folders('<folderId>')` (L-MIG-085).
- An older `DeleteEntities` body, `{"deleteSpec":{"sourceSpecArr":[{"sourceEntityId":"<id>"}]}}` on `/frs/api/v1/DeleteEntities`, was tried once; its outcome was not recorded. Use `{"artifactIds":[...]}`.

## 5. Delete order (L-CLEAN-013)

1. CAI **unpublish**: processes, then app connections, then connectors.
2. CAI assets (FRS).
3. Taskflows (after unbinding or deleting their schedules). Remove shared tasks from **shared** taskflows instead of deleting those taskflows (section 10).
4. Mapping tasks (by v2 id).
5. Mappings (once their `tasks[]` is empty).
6. DBMI tasks (stop, undeploy, then FRS).
7. DQ assets and profiles (FRS).
8. Connections (after a used-by check; catalog sources can hold them).
9. Agents, then runtime environments.
10. Schedules.
11. Empty folders, then empty projects (FRS; `FRS_087` means something is still inside).
12. Users.
13. CDGC: glossary items and catalog-source purges over REST, then the source definitions in the UI.

Tell the migration lead before each batch, never delete while an import runs, and keep logins to one per session (a login loop can lock the account). A v3 objects list gave a one-off 500 `Objects Listing Failed: null` while a peer was importing; a retry worked (L-CLEAN-018).

## 6. v2 DELETE semantics (L-CLEAN-006)

- Header `icSessionId` on the v2 `serverUrl`. A successful delete answers 200.
- **Read-back:** a `GET` of the deleted id answering 403 means gone. The exception is schedules: a deleted schedule's `GET` returns an empty 200 shell, so confirm with the `GET /api/v2/schedule` list.
- **Resolve ids by the right key, never by name:** a mapping task's v2 id from its v3 id through the task detail's `frsGuid`, and a mapping's v2 id through `assetFrsGuid`. Same-named objects can exist in other folders.
- The v2 task list omits `scheduleId` and `frsGuid`, so read each task's detail first.

## 7. Users (L-CLEAN-009, L-CLEAN-010)

- `DELETE /public/core/v3/users/<userId>` returns 204 (an older reference row said 405; that is wrong). Back up the user list first.
- **Reassign the user's file listener associations first** (reported): the owner is whoever last picked the listener in a file ingestion task or last published the taskflow it triggers, and that account cannot be deleted until `POST <serverUrl>/mftsaas/api/v1/ChangeCallbackOwnership {"currentOwner":"<userId>","newOwner":"<userId>"}` (`IDS-SESSION-ID`) moves them (L-CLEAN-037).
- **Keep** the `CAI_Anonymous_<orgIdV3>` system user (anonymous `/active-bpel/public/rt` calls need it), the automation user you are logged in as, and any service user a live process, connection or catalog scanner signs in as (grep the hosts and configs first).
- There is no proven in-place edit (PUT or PATCH were 405 in July), so an edit is delete plus re-create: `POST /public/core/v3/users` with `{"name":"<login>","firstName":"<first>","lastName":"<last>","email":"<email>","groups":["<groupId>"]}`. The key is `name` (not `userName`), and `groups` holds plain id strings. Test the re-create on one seat before a batch: a wrong body once left 27 seats deleted.

## 8. CAI: unpublish before delete (L-CLEAN-011, L-CLEAN-012)

```
POST https://<pod>-cai.<domain>.informaticacloud.com/active-bpel/asset/v1/unpublish
Content-Type: application/vnd.api+json        Accept: application/vnd.api+json        INFA-SESSION-ID: <session>
{"data":{"type":"unpublish","attributes":{"assetPaths":["Explore/<project>/<folder>/<name>.PROCESS.xml"]}}}
```

It returns `data.id`. Poll `GET /active-bpel/asset/v1/unpublish/<id>/Status` and read each item. Use `.AI_CONNECTION.xml` and `.AI_SERVICE_CONNECTOR.xml` paths for connections and connectors. Order: processes, then app connections, then connectors, with up to 199 paths per call. Then delete through FRS.

**Stuck assets:** if the CAI runtime holds two catalog rows for one asset, publish and unpublish both fault with 'singleton sequence... 2 items'. An asset with no runtime entry faults with `AvrEntryNotFoundFault`. Both stay flagged as published, so FRS refuses the delete (`FRS_082`) and their project cannot be emptied (`FRS_087`). This needs Informatica support or a UI attempt; list them in the report (2 of 83 in one cleanup).

## 9. Never delete (L-CLEAN-016)

| Content | Why |
|---|---|
| Add-On Bundles (for example the Data Transfer Templates) | system content: FRS reports `delete:false` even for an admin, and tasks built on a bundle template break without it |
| the Default project and the system API policy | platform content |
| the CDGC home dashboard and widgets; system classifications, policies and roles | catalog scans rely on the system classifications |
| `CAI_Anonymous_<orgIdV3>` | anonymous CAI endpoints need it |
| stock samples and utilities (`dsst__*`, `B2B_Gateway_*`, `infacore_*` DQ utilities) | kept DQ mappings may reference the utilities |
| Reference360, Business360 and MultidomainMDM system content | deleting stock MDM scaffolding can destabilize the MDM engine; delete only the entities and records you authored. Licence-installed MDM bundle content cannot be deleted headless anyway: FRS answers 403 `FRS_127` even for an org admin, so republish anything you unpublished and hide it with roles (L-MIG-084) |
| platform-generated objects (the 'Sample ... Connection' mock connections, `DQ_Capability_Schedule_*` schedules) | they regenerate after a delete when CDC tasks or catalog DQ scoring are in use: keep them, or switch the feature off (L-CLEAN-036) |
| MDM entities that live assets still use | for example an address-verification entity |
| the live replication slot (when cleaning the database host) | a polling CDC job shows `active=f` between cycles (L-CLEAN-027) |

MDM content: deleting an MDM installation deletes business **records**, not only design assets. Export the records first (section 3), delete the assets item by item, and list whatever the MDM service refuses instead of forcing it. The outcome of a fully headless MDM delete pass is not recorded in these sources.

## 10. Remove one application's footprint (L-CLEAN-022)

1. Back up: export everything in scope with dependencies, plus a JSON of its CDGC items.
2. Unbind its schedule.
3. Delete its taskflow (`DELETE /api/v2/workflow/<id>`).
4. Remove its tasks from any **shared** taskflow: `GET /api/v2/workflow/<id>`, filter `tasks[]`, then `POST` the body back and read it back.
5. Delete its mapping tasks by v2 id.
6. Unpublish, then FRS-delete, its CAI processes (asset path `Explore/<path>.PROCESS.xml`).
7. Stop and undeploy, then FRS-delete, its DBMI tasks.
8. Delete its profiles and any rule specs it alone uses; keep shared ones.
9. Delete its glossary domain and terms; purge its catalog source (the definition goes later, in the UI).
10. Delete its connections last, after a used-by check.
11. Off-platform: comment out its IDMC cron jobs (keep an undo file), switch its app-side IDMC calls off, and label its status honestly.
12. Verify at the next scheduled slots that no run of it happened on any agent.

This order was proven in two orgs.

## 11. Safety laws

- **A rejected or interrupted tool call may already have run** (L-CLEAN-017). 68 FRS deletes had landed although the call was rejected. Read back and report the real state.
- **Select by owning agent or runtime, never by name** (L-CLEAN-020), and re-check each object's binding right before deleting it while other sessions are active.
- **In an org you do not own, change only what you created** (L-CLEAN-021), and prove the rest untouched with before-and-after location counts.
- **"In no taskflow" is not "unused"** (L-CLEAN-025): check the task-level `scheduleId`, application readers of its output, orchestrator id lists, and whether its target is still a table. A File Ingestion task that a CAI process starts by id has no used-by link: a cleanup that archived it as unused broke the live flow, so grep CAI process XML for task ids first (L-DBMI-061). Unbind the schedules of a pipeline you retire, including ones in other projects (L-CDI-283).
- **Walk-through copies** made with FRS `CopyEntities` are undone with `DELETE .../frs/api/v1/BaseEntities('<copyId>')` (L-MIG-087, L-CLEAN-005).
- **Refute before you delete, then stage the removal** (L-CLEAN-024): quarantine, soak, archive, then drop, each drop approved; in one audit 37 of 90 "orphans" were refuted.
- **Mixed projects:** move the keepers into a new project first (ids are preserved), then delete the old project wholesale (L-CLEAN-026).
- **Superseded tasks:** delete only after a chunked export backup and a name-to-frsGuid map (L-CLEAN-023).

## 12. Decommissioning the source org after a move

Deleting in the **source** org is a separate, owner-approved step after the cutover, the soak and the smoke tests
(L-MIG-051). Build the decommission list with a script, read-only, from three local inputs: the source inventory, the
source-to-target id map, and the target import's per-object log (`GET /public/core/v3/import/<jobId>?expand=objects`).
Rebuild it whenever the id map changes, and give every object exactly one verdict (L-MIG-073):

| Verdict | Rule | Action |
|---|---|---|
| READY | the import created a twin (`Create object`) and its target id is mapped | delete after cutover and smoke tests |
| HOLD-VERIFY | the id map has a twin, but the import log says `Reuse existing object`: the target kept an older same-named object | diff the content first |
| NO-TWIN | not in the target (for example tasks the target rejected with a vendor-validation 403) | never delete |
| PROBE | a test object | any time |
| DEP-LAST | a dependency matched by name with no target id (connections, runtime environments, folders) | delete last |
| SHARED | bundles, other teams' folders, hosted runtimes, vendor content | never delete (section 9) |

In one 228-object source the split was 180 READY, 9 HOLD-VERIFY, 7 NO-TWIN, 3 probes, 13 name-matched dependencies and
16 shared or vendor objects. Then delete with the same keep-list, backup and per-object gates as any other cleanup
(sections 2 and 3).

## 13. Overturned beliefs

| Earlier belief (dates) | What overturned it | Lessons |
|---|---|---|
| "The headless delete surface is five DELETE endpoints; design objects have no headless delete" (2026-07-25) | v2 DELETE on seven resources (2026-08-20, 2026-09-28) and FRS deletes (2026-09-26/28) | L-CLEAN-028 → L-CLEAN-006 |
| "`DELETE /public/core/v3/users/{id}` returns 405" (2026-07-25) | 204 (2026-09-28) | L-CLEAN-029 → L-CLEAN-009 |
| "FRS delete is `DELETE /frs/api/v1/Documents('<id>')`" (2026-09-25) | `Documents` gives 403; `BaseEntities` deletes (2026-09-26) | L-CLEAN-030 → L-CLEAN-005 |
| "Agents, runtime environments, projects, MDM content and catalog sources have no headless delete" (2026-08-20) | v2 DELETE for agents and runtime environments, FRS for folders and projects (2026-09-28); catalog-source definitions still need the UI | L-CLEAN-031 → L-CLEAN-003 |
| "The catalog-source prefix is not routed on some orgs, so deletes are UI-only" (2026-08-20) | the prefix answered 200 there later; a REST delete purges (2026-09-28/29) | L-CLEAN-032 → L-CLEAN-015 |
| "DBMI tasks have no delete API; use the Explore UI" (2026-09-25/26) | FRS `BaseEntities` (what the UI calls) | L-CLEAN-033 → L-CLEAN-005 |

## 14. Lessons in this doc

L-CLEAN-001 to L-CLEAN-027, L-MIG-018, L-MIG-051, L-MIG-072, L-CDGC-028, L-CLEAN-034, L-CLEAN-036, L-CLEAN-037, L-MIG-073, L-MIG-075, L-MIG-084, L-MIG-087, and the superseded L-CLEAN-028 to L-CLEAN-033. Full text: [Lessons: Migration & Org Management](lessons.md).
