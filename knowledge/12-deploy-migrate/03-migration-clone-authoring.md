# Migration-Clone Authoring

**Answers:** How do I author a design object that has no REST create verb? Which object types clone, what do I edit
in each, and what follow-up step makes the clone runnable? What does a clone inherit? What can I do in an empty org?

**Read when:** you need a new rule spec, MDM entity, marketplace product, CAI asset, mapping or DBMI task headless,
or you need to change one of them in place.

**Key rules:**
- Most design objects have no create verb: clone a same-type object through export, package edit and import, at no
  IPU cost (L-MIG-023).
- Give the clone a fresh 22-character GUID and a new name, or the import overwrites its template (L-MIG-023).
- A clone inherits the template's logic and its target-type properties (L-MIG-025).
- A commit creates the design object only: deploy DBMI, publish CAI, bind schedules and re-tag separately
  (L-MIG-024).
- An empty org has nothing to clone: prove it with an unfiltered objects read, then seed one object, build the
  package from scratch, or migrate one in (L-MIG-026, L-MIG-022).
- After every clone commit, run the survival gate (new object present; template and pre-existing objects unchanged)
  and search by id and exact type name before declaring anything gone (L-MIG-055, L-CLEAN-021).

**Related:** [Export & Import](01-export-import-v3-migration-api.md) · [Editing Packages Safely](02-editing-packages-safely.md) · [DBMI over REST](../06-cdc-ingestion/01-dbmi-over-rest-create-deploy-run-stop.md) · [Data Integration (CDI)](../04-mappings/) · [Lessons: Migration & Org Management](lessons.md)

**Last verified:** 2026-11-03

> The migration API authors objects that have no create verb: export a same-type object, change its name, GUID and
> references inside the package, re-hash, then import and start. This is migration-clone. It is proven for rule
> specs, MDM business entities, source systems and reference entities, marketplace products, CAI processes with their
> connections, mappings and DBMI tasks; packages built from scratch also import when their metadata is right.

---

## 1. When to use it

| You need | Best headless path |
|---|---|
| a mapping task over an existing mapping or a parameterized Add-On Bundle template | `POST /saas/api/v2/mttask` (no clone needed; see [Data Integration (CDI)](../04-mappings/)) |
| a new DBMI task | `POST.../dbmi/public/api/v2/task/create` from a JSON body (no clone needed; see [DBMI over REST](../06-cdc-ingestion/01-dbmi-over-rest-create-deploy-run-stop.md)) |
| a new rule spec, MDM entity, reference entity, marketplace product | **migration-clone** |
| a new CAI process, app connection or service connector | migration-clone, or a from-scratch package (then publish) |
| a real multi-transformation mapping | a from-scratch package with generated IMF JSON (see [Data Integration (CDI)](../04-mappings/)), or a clone of a similar mapping |
| a change to an existing object of these types | export → edit → import `OVERWRITE` (the same mechanism) |

## 2. The recipe (L-MIG-023)

1. **Pick a template**: an existing object of the same type in the org. Find it with `GET /public/core/v3/objects?q=type=='<TYPE>'`, using the exact type name (L-MIG-002). Make sure the user has the migration and object-admin roles (L-MIG-006).
2. **Export it**: `POST /public/core/v3/export {"name":"<n>","objects":[{"id":"<templateId>"}]}`, poll `GET /public/core/v3/export/<id>`, then `GET /public/core/v3/export/<id>/package`. Add `"includeDependencies":true` when the clone needs the template's connection or connector entries.
3. **Edit the package** (see [Editing Packages Safely](02-editing-packages-safely.md)):
   - in `exportMetadata.v2.json`: a new `objectName` and a fresh 22-character `objectGuid` (random alphanumerics) for the clone, so the template is not overwritten;
   - in the inner file: the same name and GUID where they appear, plus the retargeted references (connection ids or names, namespace, `frsID`, business logic);
   - in `exportPackage.chksum`: upper-case SHA-256 lines for the changed files only.
4. **Upload**: `POST /public/core/v3/import/package` (multipart, part `package`), and expect 200 `checksumValid:true`.
5. **Start**: `POST /public/core/v3/import/<jobId>` with `{"importSpecification":{"defaultConflictResolution":"OVERWRITE"}}` (or `REUSE` for the dependencies), then poll until `SUCCESSFUL`.
6. **Verify**: the new object appears in `GET /public/core/v3/objects` (the count rises by one, with a fresh `updateTime`); the template is unchanged; objects that were already in the org survived the commit.
7. **Make it runnable** (section 4).

## 3. Per-type notes

| Type | Proven | What to edit | Follow-up step | Notes |
|---|---|---|---|---|
| `RULE_SPECIFICATION` | yes (count 4 → 11 → 12) | name, GUID | none | the clone inherits the template's expression body; making each rule's logic match its intent still needs the rule builder (L-MIG-025). Bundle rule specs exported fine in one org |
| `BUSINESS_ENTITY`, `MDM_SRC_SYSTEM`, reference entities | yes (entities of 41 and 15 fields) | namespace, GUID, FRS id, fields | model deploy: disputed (UI Modeler publish vs "effective on save"); verify with a record-API read by runtime id | see [MDM](../10-mdm/) |
| Data Marketplace products | yes | name, GUID | none recorded | |
| CAI `PROCESS` (+ `AI_CONNECTION`, `AI_SERVICE_CONNECTOR`; carry every connection and connector a process references, L-CAI-156; fix a failing package under throwaway names, L-CAI-157) | yes | the process XML (swap the `<process>` element), the connection's base URL | `asset/v1/publish` in dependency order: connector, app connection, processes | inputs must be `<parameter>` elements; export by the IDMC object id, not the process GUID (`MigrationSvc_034`) |
| `MAPPING` / `DTEMPLATE` | yes (a connection swap ran 52/52; generated mappings run) | `bin/@<n>.bin` IMF JSON, the `mappingTemplate.json` references | wrap it in a mapping task (`POST /api/v2/mttask`) | schema-bound mappings need consistent field arrays; do not add a new connection to `objectRefs` (L-MIG-020) |
| `DBMI_TASK` | yes | `.dat` JSON: `sourceConnectionId`, `targetConnectionId`, slot and publication, name and GUID | `task/deploy` and `job/start` on `-ing` | a clone of a template built for another target type carries that type's target properties (L-MIG-025); `task/create` from `task/details` is simpler |
| `TASKFLOW` (advanced) | imports | generated XML | **publish failed** for API-created or FRS-copied taskflows (`AvrEntryNotFoundFault`, "File format was not recognized") | use linear taskflows (`/api/v2/workflow`), which need no publish |
| `PROFILE` | imports | — | re-bind the rule occurrences: imported profiles arrive with 0 rules | see [Data Quality & Profiling](../08-data-quality/) |
| Verifier (address) | yes (2026-11-02) | fresh GUID and name, `documentBlob.logicalModel.outputFields`, SHA-256 re-hash, import REUSE | prove one known address returns the enrichments you need | added output fields do not switch geocoding on: the option is in the asset's own process settings (L-DQ-130) |
| Two mappings merged into one | yes (2026-10-26) | transplant transformations between the exports: `$$class` re-pointed by class name, fresh `$$ID`s, the DTEMPLATE zip refreshed | import OVERWRITE under the id of the mapping you keep, so its task and taskflow stay | L-CDI-278 |
| `TOOL_CONNECTION` (MCP) | **fails** (`MigrationSvc_031` 'Internal error') | — | recreate it in the Application Integration designer | L-MIG-039 |
| CDGC governance objects | **fails** (`MigrationSvc_034`) | — | use the CDGC APIs | L-MIG-007 |

## 4. What persists and what does not (L-MIG-024, L-MIG-025)

| After a successful commit | State |
|---|---|
| the design object (name, GUID, definition) | created, `SUCCESSFUL`, `objects:null` in the envelope |
| the template | unchanged, when the clone had a fresh GUID and name |
| DBMI tasks | **not deployed** (`task/deploy`, then `job/start`) |
| CAI assets | **not published** (`asset/v1/publish`) |
| schedules | none bound |
| tags | none (re-tag with `TagObjects`) |
| connection secrets | masked (set them on the connection) |
| logic | the template's, unless you replaced it |
| target property maps | the template's target type, unless you replaced them |

The earlier belief that any imported object needs a UI click to deploy or publish was overturned for CAI and DBMI; MDM model deploy is still a UI step in these sources (L-MIG-067 → L-MIG-024).

## 5. The empty-org limitation (L-MIG-026)

- The clone path needs an object of the same type. On an empty org the export answers 400 `MigrationSvc_041 'No asset selected'`.
- Check emptiness with an **unfiltered** `GET /public/core/v3/objects?limit=5`: `count:1` with only a default project is decisive. A type-filtered count of 0 proves nothing, because the filter is not validated (L-MIG-002).
- For a type with no object in the org:
  1. author one seed in the UI, then clone the rest; or
  2. build the package from scratch, where the format is known (mappings, CAI assets, advanced taskflows; L-MIG-022); or
  3. migrate one object of that type from another org (import creates it).
- To rebind a mapping to a **new connection type** by pure clone, the package needs that connection's `SYS/<conn>.Connection.zip`, which only exists if some mapping already uses such a connection (L-MIG-027). Generated packages carry their own `/SYS` connection entries, which probably removes this limit (untested for a new connector type).

## 6. From-scratch packages (L-MIG-022)

A package you build yourself imports `SUCCESSFUL` if it has:

1. the object files under `Explore/<project>/<folder>/` in the same formats an export uses;
2. the real `<folder>.Folder.json` and `<project>.Project.json`, copied from any genuine export of an object in that folder;
3. an `exportMetadata.v2.json` whose `exportedObjects[]` list the folder, the project and each object (`objectGuid`, `objectName`, `objectType`, `path` like `/Explore/<project>/<folder>`, `metadata.objectRefs` = its dependency guids, `additionalInfo`), plus connection entries with `path:"/SYS"` and `repoInfo.repoHandle` = the v2 connection id;
4. an `exportPackage.chksum` with a correct upper-case SHA-256 line per file.

400 `MigrationSvc_030` is what an empty or malformed multipart gets; it does not mean "hand-built packages are rejected" (that belief was L-MIG-066, overturned by L-MIG-022). Persist the GUIDs you generate (a small registry file), so a rebuild overwrites the same objects instead of creating duplicates.

## 7. Clones in a shared org

- Verify by id and by the exact type name before concluding that a clone is gone. A scan with the wrong type name (`DBMI` instead of `DBMI_TASK`) returns 0 without an error, and clones can land in the project of the user who owns the template (L-MIG-055).
- Change only what you created, and prove that other content is untouched by comparing location counts before and after (L-CLEAN-021).
- Place new objects in your own project or folder right after creation (FRS `MoveEntities`, ids preserved; L-MIG-054) and tag them.

## 8. Overturned beliefs

| Earlier belief (dates) | What overturned it | Lessons |
|---|---|---|
| "Design authoring is UI-only because `POST /v3/objects` is 405" (2026-07-04 to 2026-07-08; again 2026-09-20/21) | migration-clone (2026-07-05; DBMI and CAI 2026-09-22) | L-MIG-061 → L-MIG-023 |
| "The clone list stops at MDM objects and rule specs; with MI_TASK at 0 there is nothing to clone" (2026-07-26) | DBMI_TASK and PROCESS clones (2026-09-22) | L-MIG-071 → L-MIG-023 |
| "A mapping's logic is a compiled binary, so a clone cannot retarget it; clone fails for DTEMPLATE" (2026-07-05 to 2026-07-09) | IMF JSON in `bin/@<n>.bin`; an in-place GUID swap ran (2026-08-19) | L-MIG-065 → L-MIG-029 |
| "Author-only clones disappear from a shared org within a day" (2026-09-23/24) | a wrong type name and another user's project | L-MIG-068 → L-MIG-055 |
| "Hand-built packages are rejected" (2026-06-28 to 2026-09-28) | from-scratch packages import (2026-09-25 onward) | L-MIG-066 → L-MIG-022 |

Still disputed: retargeting a cloned mapping to a **different SQL dialect** by translating its custom query SQL (July records disagree; L-MIG-060). Still failing: taskflow publish of generated taskflows, tool-connection import, and CDGC governance export.

## 9. Worked example: clone a rule specification

Goal: a new rule spec from an existing one, headless and free.

```python
import json, secrets, string

def new_guid:                                   # IDMC GUIDs are 22 alphanumerics
    return "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(22))

# 1. find a template of the exact type
#    GET /public/core/v3/objects?q=type=='RULE_SPECIFICATION'&limit=200   -> pick <templateId>
# 2. export it and download the package (see Export & Import)
files = read_pkg("rulespec_template.zip")         # toolkit from Editing Packages Safely
meta = json.loads(files["exportMetadata.v2.json"])
obj = next(o for o in meta["exportedObjects"] if o["objectType"] == "RULE_SPECIFICATION")
old_guid, old_name = obj["objectGuid"], obj["objectName"]
guid, name = new_guid, "<new rule name>"
obj["objectGuid"], obj["objectName"] = guid, name
files["exportMetadata.v2.json"] = json.dumps(meta).encode("utf-8")
# 3. rename the object file and replace the old name/GUID inside it where they appear
#    (inspect the file first: the internal layout of each type is not documented; for a rule spec the
#    logic sits in nativeData.documentBlob -> ruleModel, two nested JSON strings, see DQ Assets)
# 4. recompute the checksum lines for every file you changed, including exportMetadata.v2.json
#    (a renamed file needs its line renamed too)
#    pruning a mapping? rebuild mappingTemplate.json references[] to match exportMetadata objectRefs, or the import
#    fails with OIE_007 'Internal application provider error' (L-MIG-076)
# 5. upload (multipart, part "package"), start with OVERWRITE, poll to SUCCESSFUL
# 6. GET /public/core/v3/objects?q=type=='RULE_SPECIFICATION' -> the count rose by one; the template is unchanged
```

The clone carries the template's logic (L-MIG-025). Changing what the rule checks still needs the rule builder, or a template that already has the right logic. To read a rule spec's logic from its `<name>.RULE_SPECIFICATION.json` (the `documentBlob` → `ruleModel` anatomy, advanced-mode scripts and basic-mode statement trees), see [DQ Assets](../08-data-quality/01-dq-assets-rule-specs-cleanse-dictionaries-verifiers.md) (L-DQ-104).

## 10. Worked example: change a CAI process safely (export, swap, import, publish, verify, roll back)

This is the same mechanism used to change an existing object. Used live, the runtime served the new version within about 20 s:

1. Find the process's IDMC object id with `GET /public/core/v3/objects?q=type=='PROCESS'`. Exporting by the GUID inside the process XML gives `MigrationSvc_034` (L-MIG-007).
2. Export it, and keep the zip untouched: **it is the undo**.
3. Replace the `<process...>...</process>` element of `<name>.PROCESS.xml` with the new definition. Match with a whitespace-tolerant pattern, because the export is pretty-printed, and assert exactly one replacement.
4. Recompute the SHA-256 lines of the changed files (keys escape spaces as `\ `).
5. Import with `OVERWRITE`, then publish: `POST https://<pod>-cai.<domain>.informaticacloud.com/active-bpel/asset/v1/publish` with the asset path `Explore/<project>/<folder>/<name>.PROCESS.xml` and `application/vnd.api+json` headers.
6. Run side-effect-free verification calls against the runtime. If any check fails, re-import the saved export and publish it again **in the same run**, automatically.

Rules for generated CAI definitions: process inputs must be `<parameter>` elements (a `<field>` inside `input` makes publish fail with a bare "Publish Error"), and CAI omits empty outputs, so callers should treat a missing field as empty. See [Application Integration (CAI)](../07-app-integration/).

## 11. The survival gate

Every clone commit is a write into a live org. After each import:

- the new object exists (by id, with the exact type name);
- the **template** is unchanged (the same `updateTime`);
- every pre-existing object of that type is still there (compare the counts, or better the id lists, before and after);
- nothing was deployed or published as a side effect (`objects:null` in the envelope; DBMI and CAI states unchanged).

Only then build on the clone. If a check fails, stop and restore from the export you took first.

## 12. Lessons in this doc

L-MIG-002, L-MIG-006, L-MIG-007, L-MIG-020, L-MIG-022 to L-MIG-027, L-MIG-029, L-MIG-039, L-MIG-054, L-MIG-055, L-MIG-060, L-CLEAN-021, and the superseded L-MIG-061, L-MIG-065 to L-MIG-068, L-MIG-071. Full text: [Lessons: Migration & Org Management](lessons.md).
