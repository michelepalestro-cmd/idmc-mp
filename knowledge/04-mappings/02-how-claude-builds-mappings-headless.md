# How Claude Builds Mappings Headless

**Answers:** Which of the five headless routes to use for a mapping or mapping task; how to clone a task, package-clone a mapping or generate one as IMF JSON; which transformations and adapters the generator has proven; how to switch on full SQL ELT pushdown, prove it and decide whether to keep it; how to create an intelligent structure model and parse documents with a Structure Parser.

**Read when:** before creating or changing any mapping or mapping task without the designer; when a transformation type, an adapter or the pushdown setting is in question.

**Key rules:**
- Mappings arrive only by import package; `POST /api/v2/mapping` and v3 objects POST are not create surfaces (L-CDI-020, L-CDI-032).
- Route 5 (spec → IMF JSON → DTEMPLATE package → v3 import → task) builds real multi-transformation mappings, including Union, Rank, Sequence, Lookup, Data Masking, Rule Specification, Cleanse, Deduplicate, Normalizer and mapplets (L-CDI-033, L-CDI-204).
- Retarget a mapping by re-importing it OVERWRITE under the same GUID; target POSTs to its task are silent no-ops (L-CDI-050, L-CDI-145).
- Full SQL ELT is three keys on the v2 mapping task, and only `OPT_63367` plus one `INSERT INTO` per target in the session log proves it (L-CDI-202).
- Pushdown writes targets one after another (~5.4 s each): keep it only after parity 0/0 and a measured speed gain (L-CDI-203).
- Prove every generated mapping on parity targets, and keep the generator byte-identical on old specs before changing it (L-METHOD-125, L-CDI-141).
- An intelligent structure model is headless in six calls; the Structure Discovery service wants the session as cookie and header, and `X-CSRF-TOKEN` on every POST after `validateWidget` (L-CDI-223, L-CDI-224).
- A Structure Parser's ports take the model's types, and the mapping keeps `"@<v3 id>"` plus a copy of the model (Synchronize after a model edit); tick Passthrough on each output group to keep the source file on every parsed row (L-CDI-229, L-CDI-230, L-CDI-231).

**Related:** [03 Mapping Tasks - Create, Update, Run, Monitor](03-mapping-tasks-create-update-run-monitor.md) · [06 Mapping Design & Consolidation](05-mapping-design-consolidation.md) · [07 Performance, Concurrency & Job Caps](06-performance-concurrency-job-caps.md) · [09 Source & Target Gotchas](08-source-target-gotchas.md) · [Lessons: CDI](lessons.md)

**Last verified:** 2026-11-03

> **Summary.** There are five proven ways to get transformation logic into IDMC CDI with no designer clicks, and they differ in what the canvas shows, what lineage sees, and what can go wrong.
> (1) Mapping tasks over a Copy Data bundle template, with the logic in `customQuery` SQL. (2) Cloning a working mapping task. (3) Package-cloning a real mapping (`bin/@N.bin` IMF JSON, checksums, a connection GUID swap). (4) One UI-authored mapping, then clone-and-repoint. (5) A headless mapping generator that writes IMF JSON from a spec.
> Routes 1 and 5 have both carried production pipelines. Route 1 is the fastest to build. Route 5 produces real transformations that lineage and CLAIRE can see, and it is the target design.
> Full SQL ELT pushdown is settable over the v2 task API (§9), but it is not automatically faster. Still not headless: publishing API-made advanced taskflows, and retargeting an existing mapping to another connector type.

---

## 1. Decision guide

Pick the first row that fits. Every route ends the same way: a v2 mapping task (MTT) that you run with `POST /api/v2/job` (see [03](03-mapping-tasks-create-update-run-monitor.md)).

| You need | Route | Evidence state | What you give up |
|---|---|---|---|
| Move data or run SQL-shaped logic **today**, where the warehouse can compute it | **1** template MTT + `customQuery` | Proven 2026-09-23; 159 tasks ran for days (L-CDI-021, 2026-09-24) | An empty two-box canvas. The logic is invisible to lineage and CLAIRE. About 20 s of fixed cost and one job per task |
| Many near-identical tasks (one per table or file), or a task copied between folders | **2** clone a working MTT | Proven: every generator run (L-CDI-022, 2026-09-25); `iics` CLI variant 2026-07-09 (L-CDI-025) | Tasks over *ordinary* mappings cannot be retargeted this way (L-CDI-007, L-CDI-050) |
| A new mapping that is a variant of an existing real mapping (new SQL, new output columns, other connection of the **same** type) | **3** package-clone a mapping | Proven 2026-07-04 (14/14 parity) and 2026-08-19 (L-CDI-026, L-CDI-028) | Hand-editing IMF field arrays. It cannot change the connector type (L-CDI-031) |
| A transformation or adapter nobody has proven headless, or a setting only the UI knows | **4** one UI author, then clone | Proven 2026-08-19 (L-CDI-041) | 30–75 min of automated UI per mapping; behind a transparent proxy, the Chromium flag set of L-UI-031, or a browser host outside it |
| Real multi-transformation mappings (Expression, Joiner, Aggregator, Router…) at scale, or consolidating many tasks into few mappings | **5** headless generator | Proven: 11 mappings at parity 0-row diffs (L-CDI-033), then 21-, 28- and 11-transformation mappings and a 9-scenario suite at exact parity (L-CDI-204) | Only proven node types and adapters (§7). Pushdown is optional and must pass a speed gate (§9) |

Rules of thumb:
- A SQL-only transform with source and target in the same warehouse: route 1 now, and route 5 when the design has to be visible or consolidated.
- One-off fixes to an existing task's SQL: route 2 mechanics (GET, edit `customQuery`, POST), with the safety steps in [08 Changing Pipelines Safely](07-changing-pipelines-safely.md).
- Never try `POST /api/v2/mapping` or `POST /public/core/v3/objects`. They are not create surfaces (400 "Internal error" and 405; L-CDI-020, still true 2026-09-29).
- No managed MCP verb authors a mapping or a mapping task. The Job Management server only wraps run, status and stop (L-CDI-068).

## 2. What every route shares

1. **Assert the org first.** Read `GET /api/v2/org` (v2, header `icSessionId`) and compare `id` with the org you mean, before any write. Hosts come from the login answer (`serverUrl` / `products[].baseApiUrl`), never from a guess (see [knowledge/01-login-and-orgs](../01-login-and-orgs/)).
2. **Create or update by id, never by name.** The same task names can exist in unrelated folders (L-CDI-010, 2026-09-28).
3. **Read back every write.** A 200 whose value reverted is a silent rejection (L-CDI-050, 2026-09-29). Imports report per-item states inside a success envelope.
4. **New v2 objects are born in `Default`.** Move them with FRS `MoveEntities`, then tag them (L-CDI-016, L-CDI-054).
5. **Run and verify** with `POST /api/v2/job` and an activity-log poll matched on `runId` (L-CDI-056, L-CDI-059). Then compare outputs before anything consumes them ([08](07-changing-pipelines-safely.md)).

## 3. Route 1: mapping tasks over a Copy Data bundle template

**What it is.** Informatica ships parameterized "copy data" mappings as Add-On Bundle content under `Add-On Bundles/Data Transfer Templates`. Their `$Source$` (type `EXTENDED_SOURCE`) and `$Target$` (type `TARGET`) have `fixedConnection=false` and `connParam=true`. A mapping task over one of them brings its own source connection and object, or a custom query, plus its own target (L-CDI-003, 2026-09-23).

| Template | Use |
|---|---|
| `dsst__copy_data_new_tgt` | Copy into a target it can create. The workhorse: landing, transforms, reverse-ETL and SaaS upserts were all tasks over it |
| `dsst__copy_data_existing_tgt` | Copy into an existing target |
| `dsst__copy_with_lookup_*` | Copy with a lookup |
| `dlt__copy_data` | Data Loader copy, with incremental-key filter parameters |
| `INFA_Generic_Cloud_Service_Mapping` | Generic cloud-service mapping |

A template shows `tasks=0` until a task uses it. It is system content: FRS reports `delete:false`, and a v3 export of it can return `403 MigrationSvc_038` for a non-admin user (org- and user-dependent). Cross-org imports reuse the target's own copy, which can be a different build (L-CDI-004, L-CDI-005).

**Steps (proven 2026-09-23 onward).**
1. Get one proven task over the template. The first one was created with a full `$Source$`/`$Target$` parameter body and validated. Since then every task is a clone of a proven landing task (route 2 mechanics). Bundle mappings have v2 ids of the form `<orgIdV2>17…`; find the template with `GET /api/v2/mapping` by name.
2. Put all business logic in SQL: one file per curated table or mart, in the dialect of the **source** connection (GoogleSQL for BigQuery; L-CDI-023). Strip comment lines, trailing `--` comments, non-ASCII characters and the trailing `;` (L-CDI-024).
3. Clone the proven task per SQL file. The body is below; the field-by-field list is L-CDI-022.
4. `POST /api/v2/mttask` → 200 with the new `id`. Move it into `<project>/<folder>` and tag it.
5. Run it and poll it. Diff the output against the reference before any consumer reads it.

```
GET  /api/v2/mttask/<templateTaskId>                          # header icSessionId, v2 serverUrl
body = response minus {id, orgId, createTime, updateTime, createdBy, updatedBy, frsGuid}
body.name = "mt_<app>_<layer>_<entity>"; body.description = body.shortDescription = "[<tag>]..."
body.sessionProperties = {}
for p in body.parameters: p.pop("id")
  $Source$ : sourceConnectionId = "<connId>"
             customQuery = "<SELECT...>"        # or remove the key for a plain table source
             sourceObject = objectName = "DUMMY_Source"            # query source
                                       | "<schema>/TABLE/<table>"  # PostgreSQL table (or /VIEW/)
             extendedObject.object and every extendedObject.objects[]:
                 name = <same object>, label = <last path segment>, dbSchema = ""
  $Target$ : targetObject = targetObjectLabel = newObjectName = objectName = objectLabel = "<dataset>/<table>"
             tgtObjectAttributes = {"parent": "<dataset>"}     # BigQuery
             runtimeAttrs = {}
             oprRuntimeAttrs = {"writeMode": "Bulk", "writeDisposition": "Write truncate"}
             truncateTarget = false
  optional : fetchMode = "RUNTIME" on $Source$ and $Target$ when the target may gain columns
POST /api/v2/mttask            -> 200 {"id": "<taskId>",...}   # anything else: raise with the first 300 chars
```

Template in-out parameters: `$p_filter_src$`, `$p_tgt_excluded_fields$` and `$p_exp_fields$`. Value-less STRING parameters need `uiProperties.required="false"` and placeholder values (`TRUE`, `NONE`), or validation fails with `APP_13506`/`APP_13507`. `errc=-1` under `schemaMode:"async"` means validation was deferred, not failed; `valid=true` is the authoritative answer (L-CDI-047, 2026-09-23).

**Evidence.** First genuine runs 2026-09-23. A 46-task hourly cycle moved about 1.5M rows per cycle with 0 failures (2026-09-24). The same template later carried 159 tasks: landing, raw, staging, gold, DQ marts, reverse-ETL into PostgreSQL, Salesforce upserts and read-backs, flat-file ingest, and append-only evidence snapshots (L-CDI-021).

**Limits, all measured.**
- The canvas shows two boxes. Lineage stops at table level, and CLAIRE answers "no information found" for task names (L-CDI-115).
- Every task costs about 20 s of fixed time and one job against the monthly cap (L-CDI-121, L-CDI-131).
- The BigQuery V2 writer cuts STRING ports to 255 characters. Long text needs JSON-typed target columns (L-CDI-152, L-CDI-153).
- One task per table per layer is the sprawl anti-pattern. Plan the consolidation from the start ([06](05-mapping-design-consolidation.md)).
- Label it honestly: SQL inside a copy task is CDI SQL, not Cloud Data Quality (L-CDI-112).

## 4. Route 2: clone a working mapping task

**v2 clone (the everyday form).** It is the same GET, strip, edit, POST as route 1, and it works for any task over a *parameterized* mapping. Keep one "proven template task" per shape: a query-to-warehouse task, a PostgreSQL table landing task, a flat-file landing task, an upsert task. Make generators create or update by name so that re-runs never duplicate (L-CDI-084, 2026-09-25):

```
existing = {t.name: t.id for t in GET /api/v2/task?type=MTT}         # cache once per run
if name in existing:
    cur = GET /api/v2/mttask/<id>; body.id = <id>; body.frsGuid = cur.frsGuid
    POST /api/v2/mttask/<id>                                          # update = POST to the id; PUT is 405
else:
    POST /api/v2/mttask  -> id; FRS MoveEntities into <project>/<folder>; TagObjects
```

**`iics` CLI variant (proven 2026-07-09).** Export one working task. In its `mtTask.json`, change `customQuery`, `targetObject`, the name and the `frsGuid`, recompute the package checksums, and import with the Informatica `iics` CLI. CLI notes: pass the region (`-r us`), filter with the double-equals form `type==MTT`, and use `--sync=true`. 18/18 cloned tasks ran SUCCESS (L-CDI-025).

**Where cloning a task does not work.**
- A task over an **ordinary** (user-authored) mapping has `connectionParameterized:false` and `objectParameterized:false`. Swapping only its connection gives an invalid task, and a task-level `sourceConnectionId` does not propagate into the mapping (L-CDI-007, 2026-09-22).
- On such tasks a POST that changes target parameters returns 200 and changes nothing. The task re-derives its targets from the mapping (L-CDI-050, 2026-09-29). Retarget the *mapping* instead (route 3 or 5 with OVERWRITE under the same GUID).
- A mapping task has no field array. Field precision and type changes belong to the mapping, and `overriddenFields` over v2 returns 400 (L-CDI-006).

## 5. Route 3: package-clone a real mapping

Use it when a real mapping exists that is close to what you need. It is also how a mapping is read back: export it and read its IMF.

**Export.** `POST https://<pod>.<domain>.informaticacloud.com/saas/public/core/v3/export`, header `INFA-SESSION-ID`, body `{"name":"<n>","objects":[{"id":"<frsGuid>","includeDependencies":false}]}`. Bare string ids give `400 V3API_007`. Then poll `GET /public/core/v3/export/<id>` until `SUCCESSFUL`, and download `GET /public/core/v3/export/<id>/package` with `Accept: application/zip`.

**Anatomy of a mapping export.**

| Entry | Content |
|---|---|
| `Explore/<project>/<folder>/<name>.DTEMPLATE.zip` | Inner zip: `mappingTemplate.json`, `fileRecord.json`, `bin/@N.bin`, `metadata.meta` |
| `mappingTemplate.json` | `@type mappingTemplate`, `assetFrsGuid`, `templateId:"@N"` (points at the IMF file record), `documentType:"MAPPING"`, `fixedConnection:true` for user mappings, `references:[{"refObjectId":"@<connection frsGuid>","refType":"connection"}]` |
| `bin/@N.bin` | **The IMF JSON** (`content` + `metadata.$$classInfo`): transformations, fields, connection bindings, `customQuery`. In the exports inspected the IMF was `@3.bin`, and `@2.bin` was a preview JPEG (L-CDI-027, 2026-09-22) |
| `SYS/<connection>.Connection.zip`, `SYS/<runtime>.AgentGroup.zip` | Dependencies, when exported with them (2026-07-06) |
| `exportMetadata.v2.json` | `exportedObjects[]`: each object's `objectGuid`, `objectName`, `objectType`, `path`, `metadata.objectRefs` |
| `exportPackage.chksum` | One `path=SHA256HEX` line per file |

The July 2026 reading that `bin/@3.bin` was a compiled binary blob, and that `mappingTemplate.json` was a useless stub, was overturned. The file is IMF JSON text (L-CDI-180 → L-CDI-027).

**Edits, in order.**
1. **Identity.** Give the clone a new name and a fresh random 22-character GUID in `exportMetadata.v2.json` (`objectGuid`, `objectName`) and in `mappingTemplate.json` (`assetFrsGuid`).
2. **Connection, same connector type.** Replace the old connection's 22-character GUID with the new one inside the IMF. GUIDs are 22 characters, so an in-place swap keeps every offset (L-CDI-028, 2026-08-19).
3. **New output shape.** Renaming fields is not enough. Rebuild the source and target field arrays **by position** from the live target schema, with fresh `$$ID`/`##ID` references and the right `platformType`/`javaType`/`nativeType`/`precision` per column (L-CDI-026, 2026-07-04).
4. **SQL.** Swap `customQuery` in the source `DataObject`. Keep the source connection's dialect (L-CDI-023).
5. **Target.** Repoint the target `DataObject` (`name`, `path`, `objectName`).

**Checksums (L-CDI-030, 2026-09-28).** In `exportPackage.chksum`, replace **only** the lines of files you changed: `SHA-256` in upper-case hex, with spaces in paths escaped as `\ `. That includes the line for `exportMetadata.v2.json` itself; otherwise the import fails with `MigrationSvc_073` "package has been modified". Keep every other line byte-identical; the opaque GUID-keyed lines may stay stale.

**The objectRefs trap (L-CDI-029).** Every GUID in an object's `metadata.objectRefs` must resolve. Adding a new connection GUID to `objectRefs` with no matching entry failed with `MigrationSvc_031` (2026-08-19). A dangling objectRef gives `MigrationSvc_031` with empty details (2026-09-28). Two ways work: leave `objectRefs` naming the original connection and let the swapped GUID resolve in the target (2026-08-19), or add an `exportedObjects` entry for the connection (`objectType:"Connection"`, `path:"/SYS"`, `repoInfo.repoHandle:<v2 connection id>`). The generator does the second (2026-09-29).

**Import.** Upload with `POST /public/core/v3/import/package` as multipart, field `package` → `{jobId, checksumValid}`. Start with `POST /public/core/v3/import/<jobId>` (not `/import/package/<jobId>`, which is 404), body `{"name":"<n>","importSpecification":{"defaultConflictResolution":"REUSE"|"OVERWRITE"}}`. Poll `GET /public/core/v3/import/<jobId>?expand=objects` and read `GET /public/core/v3/import/<jobId>/log` with `Accept: */*`. An import is all-or-nothing. A plain-JSON upload gives a misleading `404 MigrationSvc_025`; an empty multipart gives `400 MigrationSvc_030`. Details: [knowledge/12-deploy-migrate](../12-deploy-migrate/).

**Merge two mappings into one by transplanting transformations (L-CDI-278, 2026-10-26).** Every IMF document numbers its classes in its own `metadata.$$classInfo`, so a transformation copied from another export keeps `$$class` numbers that mean something else in the target. Deep-copy the node; map each `$$class` number to its class name in the source document, then to that name's number in the target (add an entry at max index + 1 when the target lacks the class); give every object a fresh `$$ID` and update the `##ID` references; rename field references to the new upstream's port names; drop the intermediate target and its TmplLink and link the last kept transformation to the first transplanted one. Then refresh the DTEMPLATE zip (the bin entry's size in `fileRecord.json`, `mappingTemplate.json` description and `references[]` for every model and connection still used, the SHA-256 lines) and import OVERWRITE under the id of the mapping you keep, so its task and taskflow step run the merged mapping unchanged. Proven by merging a parse-to-table mapping and a rules mapping (3 rule specifications and a status expression): 29 rows per run, task and taskflow ids unchanged.

**Wrap and run.** Find the new mapping's v2 id with `GET /api/v2/mapping` (by name, inside the intended folder), then create the task with the minimal body in L-CDI-037 and run it.

**Evidence.** 14/14 new-shape marts were ported with exact parity (set difference 0, 2026-07-04). A PostgreSQL-to-warehouse clone with a swapped connection GUID ran SUCCESS 52/52 (2026-08-19).

**Limits.**
- Editing the package did **not** move a mapping to a different connector type: the BigQuery-bound clones stayed bound to BigQuery (L-CDI-031, 2026-07-07; not retested since).
- Target-port `notNull` flags travel with the clone. Coalesce NULLs in a source view (L-CDI-165).
- The import carries no tags and no schedules, and it publishes nothing.
- A `MigrationSvc_031` on a known-good DTEMPLATE package was transient in July: retry before debugging.

## 6. Route 4: one UI author, then clone and repoint

Use the UI **once** when no headless route has proven what you need: a transformation type the generator has not run (the open list is in §8), a new source/target connector pair with no exemplar to harvest, or a setting whose REST name nobody has found. For a task setting, first try the JSON-diff method in §9 (diff a task the UI changed against an identical one it did not). Then turn that one mapping into the template for routes 3 and 5.

Steps (proven 2026-08-19 for 16 marts; L-CDI-041):
1. Drive the Data Integration designer with Playwright. Behind a transparent corporate proxy the IDMC design SPAs once rendered blank under every automation profile tried (L-UI-011); on 2026-10-06 headless Chromium with the Private and Local Network Access checks off drove the mapping designer from behind such a proxy (L-UI-031). Try that flag set first, and fall back to a host **outside** the proxy. Log in once, cache `storage_state`, and stop hard on the first rejected login.
2. For the query source, type the SQL into the CodeMirror editor with `setValue('<query>')` and commit it with `save`. Never press Escape before the commit (it discards the change). react-select options match `[class*='-option']`, not `role=option`.
3. Large custom queries (about 6 KB with inlined CTEs) can hang the field-derive spinner on a brand-new mapping. Recover by listing DTEMPLATE objects over v3, adopting the persisted `Mapping<N>` by GUID, and deleting orphans with `DELETE /api/v2/mapping/<id>`.
4. Export the saved mapping (route 3) and keep it as the exemplar for the generator (route 5).

Cost: 30–75 minutes per UI-authored mart, serially. It is worth doing once per shape, never once per table.

## 7. Route 5: the headless mapping generator (spec → IMF JSON → package → import)

**Proven 2026-09-29** (L-CDI-033): 11 real multi-transformation mappings, each wrapped in one task, parity-green against the live SQL (two-way `EXCEPT DISTINCT` = 0) and idempotent on a double run, replacing 40 copy-template tasks. This overturns "CDI mapping authoring has no REST verb" (L-CDI-174).

**Pipeline.**
1. **Exemplars.** If the org has no real mappings, harvest some read-only from an org that does (export only), covering Joiner, Aggregator, Router, Expression and Lookup patterns (L-CDI-036). They show the exact IMF shape of each transformation and adapter.
2. **Spec (JSON).**
   ```
   {"name": "m_<x>", "description": "[<tag>]...",
    "folder": {"project": "<project>", "projectGuid": "<frsGuid>", "name": "<folder>", "guid": "<frsGuid>"},
    "connections": {"WH": {"guid": "<connection frsGuid>", "name": "<conn name>", "repoHandle": "<v2 connId>"}},
    "nodes": [
      {"type": "source", "name": "SRC_A", "conn": "WH", "query": "SELECT...", "fields": [["col", "STRING", 256],...]},
      {"type": "source", "name": "SRC_B", "conn": "WH", "object": "<dataset>/<table>", "fields": [...]},
      {"type": "expression", "name": "EXP_A", "fields": [{"name": "x", "type": "STRING", "expr": "...", "kind": "OUTPUT|VARIABLE"}]},
      {"type": "filter", "name": "FIL_A", "cond": "..."},
      {"type": "router", "name": "RTR_A", "groups": [["VALID", "dq_status = 'VALID'"]]},        # DEFAULT1 is added
      {"type": "joiner", "name": "JNR_A", "master": "SRC_B", "detail": "SRC_A", "cond": [["m_col", "d_col"]],
       "join": "NORMAL|MASTER_OUTER|DETAIL_OUTER|FULL_OUTER", "sorted": false},
      {"type": "aggregator", "name": "AGG_A", "groupBy": ["col"], "fields": [{"name": "n", "type": "INTEGER", "expr": "COUNT(col)"}]},
      {"type": "sorter", "name": "SRT_A", "keys": ["col", "-ts"], "distinct": false},
      {"type": "target", "name": "TGT_A", "conn": "WH", "object": "<dataset>/<table>", "fields": [...],
       "truncate": true, "disposition": "Write truncate|Write append", "op": "Insert", "updateColumns": []}],
    "links": [["SRC_A", "EXP_A"], ["RTR_A.VALID", "TGT_A"], ["SRC_B", "JNR_A.Master", ["col1", "col2"]]]}
   ```
   Field types are the warehouse's (STRING, INTEGER, NUMERIC, FLOAT, TIMESTAMP, DATE, BOOLEAN). They map to platform types string 4000, bigint 19, decimal 28,9, double 15 and date/time 29,9. A third link element selects or renames fields.
3. **Build the IMF JSON** (L-CDI-035). `content` is a `Template` with `transformations[]` (`TmplSource`, `TmplTarget`, `TmplExpression`, `TmplRouter`, `TmplFilter`, `TmplJoiner`, `TmplAggregator`, `TmplSorter`, each with its `TmplGroup`s) and `links[]` of `TmplLink`. `metadata.$$classInfo` maps numeric class ids to Java classes (`com.informatica.metadata.template...`). Every object carries `$$ID` and `$$class`; references are `{"##ID","$$class"}`. Adapters are `BaseAdapter` objects with `connectionId:"saas:@<connection frsGuid>"`, `objectType` `QUERY` or `SINGLE`, a `DataObject`, `ReadOptions`/`WriteOptions` and `oprRuntimeAttributes`. Pass-through uses `TmplAllRule`; a link field selection uses `TmplNameRule` entries. Targets map fields `BY_NAME`.
4. **Package** (L-CDI-034). The outer zip holds `Explore/<project>/<folder>/<name>.DTEMPLATE.zip`, `exportMetadata.v2.json` and `exportPackage.chksum`. The inner zip holds:
   - `mappingTemplate.json`: `[{"@type":"mappingTemplate","id":"@1","name":..,"assetFrsGuid":"<22-char guid>","templateId":"@2","documentType":"MAPPING","fixedConnection":true,"valid":true,"references":[{"@type":"reference","refObjectId":"@<conn guid>","refType":"connection"}],...}]`;
   - `fileRecord.json`: `[{"@type":"fileRecord","id":"@2","type":"IMFOBJECT","size":<n>,"additionalInfo":"com.informatica.metadata.template.common.Template"}]`;
   - `bin/@2.bin` (the IMF JSON) and `metadata.meta` (`[{"@type":"objectRef","id":"@1","type":"mappingTemplate"}]`).

   `exportMetadata.v2.json` lists the DTEMPLATE (`objectRefs` = the connection guids, `documentState:"VALID"`), the Project and the Folder (with their real guids), and one `Connection` entry per connection (`path:"/SYS"`, `repoInfo.repoHandle:<v2 connId>`). Checksum lines are `path=SHA256HEX`, upper case, with spaces escaped as `\ `. From-scratch packages built this way import SUCCESSFUL. `MigrationSvc_030` is what an empty or invalid multipart gets (L-CDI-032).
5. **Import** with REUSE the first time, and with OVERWRITE for a rebuild under the **same** GUID. Assert the org first.
6. **Wrap:** `POST /api/v2/mttask {"@type":"mtTask","name":"mt_<x>","description":"[<tag>]...","mappingId":"<v2 mapping id>","runtimeEnvironmentId":"<reId>"}` → 200. It lands in `Default`, so move it with FRS MoveEntities (L-CDI-037).
7. **Run and prove.** Write only to a parity dataset first. Compare with the original SQL run at the same moment, then run twice and compare run 1 with run 2 ([08](07-changing-pipelines-safely.md)). Count a comparison only from runs that ended in state 1 and whose target `last_modified_time` is at or after the run start; otherwise the diff read an older table (L-CDI-141). Refresh the spec's column lists from `INFORMATION_SCHEMA` right before every build, or a column added later is silently left out and lands NULL on both sides of the parity check (L-CDI-197).

**Proven node types** (each ran in a real job from a generated mapping; L-CDI-033, L-CDI-204):

| Node | IMF class | Key properties | Adds / notes |
|---|---|---|---|
| Source: warehouse query or table; PostgreSQL table or view | `TmplSource` | adapter `objectType` `QUERY` or `SINGLE` | an ingest mapping reads each table once and writes several targets |
| Expression (OUTPUT and VARIABLE ports), Filter, Sorter, Router | `TmplExpression`, `TmplFilter`, `TmplSorter`, `TmplRouter` | Router groups plus the added `DEFAULT1` | — |
| Joiner: normal, master outer, full outer, chained, sorted same-source self-join | `TmplJoiner` | `master`, `detail`, `cond`, `join`, `sorted` | an unsorted Joiner runs Nested-Loop and caches its master side |
| Aggregator (also stacked) | `TmplAggregator` | `groupBy` + aggregate expressions | — |
| Union | `TmplUnion` | plain groups `Input1..n` plus `OutputGroup` and `fields` (TxField); `inputGroups` = `TmplUnionGroup {name, fieldMapping: FieldMapping {fields: [TxFieldMapping name=<incoming field>, txField=<ref to the output field>]}}` | `TmplUnionGroup` is not a group: putting it in `groups` fails with a cast error |
| Rank (top-N) | `TmplRank` | DefaultGroup with `isTop`, `rankField`, `numOfRows`, `groupByFieldsList` = `TmplRankGroupByFields {fields: [TmplRankGroupByField fieldName]}` | adds `RANKINDEX` |
| Sequence Generator | `TmplGenerator` | `midstream=true`, `state` = `GeneratorState {startValue,...}` | adds `NEXTVAL`; `startValue` was ignored (numbering began at 1) |
| Lookup, connected | `TmplLookup` | a warehouse adapter like a source's | — |
| Lookup, unconnected | `TmplLookup` | no groups; `inputPortNames`, `lookupConditions`, `returnPortName`, `unconnected=true`, an adapter (a query works) | call it as `:LKP.<NAME>(arg)` in an Expression |
| Data Masking | `TmplDmo` | `maskingType` takes the UI label ('Email address', 'Phone', 'SSN', 'Credit card', 'Key',...) with that technique's parameters | outputs `out_<field>`, format-preserving; pass-through fields did not flow through it, so link them around it |
| Rule Specification (a CDQ rule as a transformation) | DQ class | the package carries the asset: a `mappingTemplate.references` entry of `refType` `frsDocument`, an `exportedObjects` `RULE_SPECIFICATION` entry and the objectRefs | a failed import leaves a broken shell that a later REUSE import picks up (`REPO_36004`): re-import under a new name |
| Cleanse, Deduplicate (CDQ assets) | DQ class | copy the referenced DQ assets into the org first (package import) | in a stock customer dedupe asset the `Id` port is itself a match field: mapping the business key into it makes every record unique, so nothing matches |
| Normalizer, mapplets, in-out parameters for incremental loads | — | — | — |
| Targets: BigQuery truncate or append; Insert, Update, Upsert, Delete and Data Driven on BigQuery and PostgreSQL; Salesforce Upsert | `TmplTarget` | write disposition in `oprRuntimeAttributes`; the operation's writer attributes (adapter rules below) | — |

Still unproven headless: the multi-asset Data Quality transformation and a stand-alone Update Strategy (Data Driven target operations cover most of its use), plus the classes listed in §8 (L-CDI-204).

**Where a new class's shape comes from (no UI capture needed).** The Data Integration designer's JavaScript bundle (`https://prod.static.informaticacloud.com/<domain>/<pod>/diUI/app/cmd/resource/js/cmd-all-<build>.min.js` and `cmd-webpack-<build>.min.js`) holds the class model of every transformation: search it for `infaw.template.T<Name>Generator` (`initTx`, `createDefaultGroups`). `GET https://<pod>.<domain>.informaticacloud.com/da/w3.imf/iclass/?infaToken=<v2 icSessionId>` returns the class-header catalogue with HTTP status 400, but the body is real (no property lists). The masking-technique catalogue (27 techniques) is reachable only inside a logged-in designer page: evaluate `infaw.saas.SaaSService.instance.getMaskRulesAsJSON`. Then harvest a real IMF exemplar of the class (export only) from any org that has one (L-CDI-204).

**Adapters.** Proven: BigQuery source and target; PostgreSQL table and view sources; PostgreSQL targets with Insert, Update, Upsert, Delete and Data Driven once the generator writes the writer attributes the UI sets for each operation (an earlier generator's Upsert ran green and applied 0 of 736 rows; [09](08-source-target-gotchas.md) §2.2; L-CDI-207); a Salesforce Upsert target, with eleven parent-first flows in one mapping (L-CDI-170); a JDBC V2 target, which writes into the database bound on its connection (L-CDI-040). Untested: a flat-file source.

**Evidence.** Ingest mappings with PostgreSQL sources ran 13,202 / 8,567 / 9,435 rows in 208 / 135 / 73 s on a 4-vCPU host. A suite of 9 complex scenarios passed exact two-way keyed diffs on a real Secure Agent: three chained outer Joiners (22,895 rows in 42 s), stacked Aggregators with Lookup and Rank, Union with Lookup and Sequence, a full-outer two-key reconciliation (18,491 rows), a sorted same-source self-join (9,289 rows in 284 s), SCD2 with MD5, a multi-flow mapping and local-day lookups across a DST change. A fuzzy Deduplicate found the same 41 duplicates as the SQL survivorship (L-CDI-204).

**Runtime rules learned the hard way (shared 4-vCPU agent host):**

| Rule | Lesson |
|---|---|
| The BigQuery write disposition must be in the target adapter's `oprRuntimeAttributes` (`writeDisposition` "Write truncate"/"Write append", `writeMode` "Bulk"). `WriteOptions.truncate` alone is ignored: the session log says "Write append" | L-CDI-038 |
| At most about 5 BigQuery readers per mapping (7–8 exhausted the agent-wide DTM heap). Select only needed columns; STRING reader precision 256, not 4000. Split big specs into connected components of at most 4 readers | L-CDI-129 |
| Never let one source feed a Joiner's master and (directly or downstream) its detail: the session hangs with no error. Same-pipeline branches need "Sorted Input" plus Sorters, or the import fails ("Choose sorted input for <JNR> …") | L-CDI-106 |
| Many unsorted Joiners, Sorters (~150 MB per partition) and Aggregators in one mapping can pass alone and die beside other lanes: the DTM heap runs out (`PLUGIN_1762... OutOfMemoryError`), followed by `BIGQUERYV2_10000... 5001` token errors on the other reader partitions. Read the first `[ERROR]`; raise the DTM heap cloud-side; split the mapping or sort Joiner inputs | L-CDI-210 |
| A generated Upsert target can run green and apply nothing. Test new-key inserts on every Upsert target before go-live, or split into Update and Insert targets with a Joiner on the target keys and a Router | L-CDI-207 |
| Expression OUTPUT ports cannot reference other OUTPUT ports: use VARIABLE ports. An apostrophe in a literal is `\|\| CHR(39) \|\|` | L-CDI-105 |
| Fields declared JSON fail in Simple mode ("table contains [JSON] data type that is incompatible with the [Simple] connection mode"). Declare them STRING: the load still fills a pre-created JSON column | L-CDI-039 |
| A BigQuery DATE target needs a STRING `'YYYY-MM-DD 00:00:00'`. A BigQuery DATE declared as DATE in a source query that feeds a Salesforce date field fails with 'Unknown native type for field... Type: DATE': `CAST(col AS TIMESTAMP)` loads the same date | L-CDI-159 |
| Unicode, 255+ character strings, empty string vs NULL, embedded newlines, NUMERIC scale 9, integers above 2^53 and microsecond timestamps survive exactly. A 29-digit NUMERIC overflows the platform's decimal(28,9) with `TE_7007`: cap or cast wide numerics in the source query | L-CDI-159 |
| Every generated BigQuery target carries the writer poll interval (`jobPollInterval`/`pollInterval` = 1 and 'Job Poll Interval In Seconds' = 1); the 10 s default costs up to ~9 s per target | L-CDI-200 |
| A failed or stopped run leaves `Temp_View<epoch>` in the query source's dataset: drop it | L-CDI-160 |
| A JDBC V2 target writes into the database bound on its connection and ignores the schema part of the object. Parity runs need their own scratch connection | L-CDI-040 |
| Retarget a finished mapping by rebuilding its package with new targets under the same GUID and importing OVERWRITE. POSTing new target parameters to its task is a silent no-op | L-CDI-050, L-CDI-145 |

**Keeping the generator honest** (L-METHOD-125, L-CDI-159):
1. **One package.** When several copies of a generator have drifted, merge them into one stdlib-only package and prove it compiles every existing spec to byte-identical IMF (normalized diff = 0) before changing anything. Measured: 71/71 legacy specs byte-identical.
2. **A lint that blocks a build** on the runtime traps already paid for: Expression OUTPUT ports that reference other OUTPUT ports; one source feeding both sides of a Joiner without sorted input; more than about 5 warehouse readers per mapping; DATE and JSON declared types; dangling or duplicate links; non-ASCII characters and `--` comments in custom SQL; BigQuery targets without the 1 s poll interval. A 106-rule lint found 3 real issues in existing specs.
3. **A scratch-only live suite.** New shapes run only against a scratch folder and scratch datasets, one job at a time under a file lock, with a job ledger and a hard cap per round, and each scenario is checked with independent SQL assertions (two-way keyed diff: only_target = only_reference = mismatch = 0). Measured: 9/9 scenarios exact using 27 jobs of a 52-job cap.
4. **Skeptic checks.** Separate agents recompute the expected results from the seed data and from warehouse time travel; accept a PASS only if none of them can refute it (8 skeptics refuted 0 PASS results).

## 8. What is still UI-only or unproven

| Item | State | Workaround |
|---|---|---|
| Publishing an advanced (parallel) taskflow created by API or copied through FRS | WALL (`AvrEntryNotFoundFault`, "File format was not recognized"; L-CDI-070) | Linear taskflows plus controller-staged concurrency ([04](../05-taskflows-schedules/01-taskflows-schedules.md), [07](06-performance-concurrency-job-caps.md)) |
| Retargeting an existing mapping to another **connector type** | Unproven headless (L-CDI-031) | Synthesize a new mapping for that adapter (route 5), or one UI author (route 4) |
| Transformations not yet run headless: the multi-asset Data Quality transformation, a stand-alone Update Strategy, Hierarchy Parser/Builder, Python, Java, Labeler, Parse, Velocity, Transaction Control, Chunking, Vector Embedding, Structure Parser (its intelligent structure model is headless, a designer-built parsing mapping ran, and that mapping edited in its export and re-imported OVERWRITE ran too, §10; L-CDI-275, L-CDI-278) | Untested (their class models are in the designer bundle, §7) | Harvest an exemplar (export) or author once (route 4), then generate |
| A generated Normalizer with occurring fields (seen 2026-10-08) | Imported valid, failed at DTM load ('<Error> : [transformation< NRM_x > ]', 'The DTM process terminated unexpectedly'; L-CDI-236) | One Expression per output row fanned out into a Union |
| Dynamic Mapping Task (one job per table) creation and run | Read P 2026-11-01 (`GET https://<pod>.<domain>.informaticacloud.com/batch-mapping/api/v1/dynamictask/<v3 id>`, no `/saas`; v3 type `BATCH_MAPPING`); create P by v3 package import (audit `BATCH_MAPPING.CREATE`); the documented `POST /batch-mapping/api/v1/dynamictask` and the MCP `run_dynamic_mapping_task` are listed but not exercised (L-CDI-289) | Export a DMT and import it edited, as for any other object; consolidation plan in [06](05-mapping-design-consolidation.md) |
| CLAIRE parsing of a PDF in an advanced-mode (Spark) mapping | WALL in the designer 2026-10-26: Discover Structure lists the PDF model but never enables Select (L-CDI-276) | A standard mapping with a Structure Parser on a Secure Agent (§10). For generation: an advanced mapping exports as `AtScaleDTemplate` (`AT_SCALE_MAPPING`, `mapping_type = CDIE`), and the Document format outputs Text, FilePath, FileType and FileName. Check the documented limits first: a local advanced cluster needs 8 vCPU, 32 GB and a 100 GB root disk, a shortfall fails the jobs already running on the agent, the Document format applies no CLAIRE model, nested Claire output needs a Hierarchy Processor before a rule specification, and the catalog drops Structure Parser and Rule Specification steps from advanced-mode lineage (L-CDI-277) |
| CDI parameter sets (`$$LOAD_DATE` etc.) | No endpoint, file format or upload captured | Bake values into SQL or task parameters |
| A REST mapping-design API | On the vendor roadmap, no committed date (check the current release notes; unproven) | Routes 3 and 5 |
| First connection of a new add-on connector type in an org | See [knowledge/02-secure-agent](../02-secure-agent/) | — |

## 9. Full SQL ELT (pushdown): switch it on, prove it, decide whether to keep it

**Why it matters.**
- **Where the work runs.** In route 1 every task's logic is a BigQuery query run by the connector as a custom-query source: the work already runs *inside* BigQuery (ELT) with pushdown off, and the agent only streams the result rows to the writer. A visual mapping (route 5) without pushdown pulls source rows **through the DTM on the Secure Agent** and computes Expressions, Joiners and Aggregators there.
- **What that costs.** The DTM heap is one agent-wide setting, not settable per task, and several DTMs run at once. More than about 5 BigQuery readers in one mapping ran out of heap on a 4-vCPU host shared by two agents (L-CDI-129). Every row crosses the network twice.
- **When it can apply.** Full pushdown turns the whole mapping into SQL executed by the warehouse. It applies only when every source and target is in the same ecosystem (BigQuery to BigQuery). A mapping that also reads or writes PostgreSQL, Salesforce or another warehouse runs in agent mode (L-CDI-043). Group targets by ecosystem when you consolidate, so the warehouse-internal mappings stay eligible.

**Switch it on headless** (a scratch copy first; L-CDI-202):
1. Confirm every source and target of the mapping is BigQuery V2. Clone the mapping and task to a scratch copy that writes parity targets (`<warehouse-dataset>_parity`), and generate every BigQuery target with **no write disposition** (BigQuery rejects a write disposition on DML jobs).
2. `GET <serverUrl>/api/v2/mttask/<id>` (header `icSessionId`) and save the body as the undo.
3. Set the three keys, drop `orgId, createTime, updateTime, createdBy, updatedBy`, keep `id` and `frsGuid`:
   ```json
   {"sessionProperties": {"Pushdown Optimization": "Full", "Allow Temporary View for Pushdown": "Yes"},
    "enableCrossSchemaPushdown": true}
   ```
   `enableCrossSchemaPushdown` is a top-level task field; it is needed when sources and targets sit in different datasets of the same project.
4. `POST <serverUrl>/api/v2/mttask/<id>` with the full body → 200; `GET` it back and compare the three keys.
5. Run it (`POST /api/v2/job`), take the run's activity-log entry `id`, and download `GET <serverUrl>/api/v2/activity/activityLog/<entryId>/sessionLog` (`Accept: */*`; [03](03-mapping-tasks-create-update-run-monitor.md) §9).
6. Gate on parity (two-way `EXCEPT DISTINCT` = 0 on every target) and on speed (below) before switching the live task. Rollback: POST the saved body back (or `sessionProperties {}` and `enableCrossSchemaPushdown: false`).

**Proof is the session log only.** In order: `TM_6721 Started [SQL ELT optimization]`; `OPT_63375 SQL ELT fallback option is set to [Partial SQL ELT]`; `OPT_63321 [Full SQL ELT optimization is supported between the source and the target system.]` (plus one `OPT_63321` per target saying the staging-file attributes are ignored); `OPT_63367 Full SQL ELT optimization was successfully enabled.`; `TM_6722 Finished [SQL ELT optimization]. It took [~3] seconds.`; then for every target `BIGQUERYV2_10000... The Secure Agent ran the following final query to write the data into the target table in full SQL ELT mode: [INSERT INTO...]` between its pre-SQL and post-SQL lines, each INSERT taking 0-1 s. No `OPT_63367` and no `INSERT INTO` lines means agent mode, whatever the task JSON says (L-CDI-202).

| Symptom | Cause | Fix |
|---|---|---|
| The property reads back, but the log has no SQL ELT lines | Only `Pushdown Optimization` was set, or a target still carries a write disposition (which key was decisive was not isolated) | Set all three keys; remove the disposition |
| `OPT_63375... [Partial SQL ELT]` followed by agent-mode lines | Part of the flow cannot be expressed in warehouse SQL | Accept partial, or move that step out of the mapping |
| The pushdown run is slower than agent mode | Targets are written one after another | Keep agent mode for small multi-target mappings (below) |

**When it is slower** (L-CDI-203). Under full pushdown the targets of one mapping run **serially**, each costing about 5.4 s (two pre-SQL statements, the INSERT and a post-SQL), after an optimization step of about 3 s; agent mode writes all targets in parallel. A 5-target BigQuery-to-BigQuery mapping took a median 43 s with pushdown (n=6, 38-49 s) against 27-29 s in agent mode (n=32), on thousands to tens of thousands of rows per run.

| Mapping shape | Agent mode | Full SQL ELT | Verdict |
|---|---|---|---|
| 5 warehouse targets, small data | 27-29 s median | 43 s median | slower |
| 1 target, 12 s today | 12 s | ≥ ~8.4 s of fixed overhead alone | cannot reach the gate |
| 11 targets | — | ~3 s + 11 × 5.4 s | do not push down |
| few targets, large row volumes | — | not measured | where it should pay; measure it |

Estimate `3 s + 5.4 s × targets` (plus the ~20 s per-task overhead both modes pay, L-CDI-121) and compare with the measured agent-mode median. Keep pushdown on a mapping only if parity is 0/0 and the median of at least 3 timed runs is at least 20% or 10 s faster; otherwise revert. Pushdown does not change the job count (a run is still one job). When latency is the goal, the bigger lever is taking jobs off the critical path, for example reading the CDC replicas already in the warehouse instead of re-ingesting the source database in every lane ([07](06-performance-concurrency-job-caps.md) §8). For how runs are metered see [knowledge/13-ipu-cost](../13-ipu-cost/).

**Finding the REST name of any other task setting.** Diff the v2 JSON of a task that the UI switched to the setting against an identical task that was not switched; the functional differences are the keys to set. That is how the three pushdown keys were found, with no UI capture (L-CDI-202).

**Functions the optimizer refuses, and replacements that push down** (L-CDI-212, L-CDI-213, L-CDI-214). The connector guide lists the Informatica functions that push to BigQuery in full SQL ELT; FIRST()/LAST() and INITCAP are not among them. Pick-one-row-per-group logic becomes one Aggregator `MAX()` over a fixed-width order key plus `SUBSTR`; a missing native function such as INITCAP goes into a passive SQL transformation `SELECT INITCAP(~field~)` on the same connection. Write regex literals as the agent reads them (`'\s+'`): the optimizer escapes backslashes itself. Set `Pushdown Optimization Fallback Option` = `Fail Task` so a mapping that cannot push down fully fails instead of running partly on the agent, prefer table sources (no temporary views), and give pushdown its own connection whose custom-query and staging datasets are the work dataset. A 1-target, 26-transformation mapping on ~500 rows ran as one `INSERT ... SELECT` in 11-12 s: about 3 s slower than agent mode on the same data and about 2.3 times faster than partial pushdown.

## 10. Intelligent structure models and the Structure Parser

An intelligent structure model is the structure CLAIRE discovers in a sample file (a spreadsheet, a PDF); a Structure Parser transformation in a mapping parses files with it. The model can be created headless from a sample file in six calls (about 4 s); it reads back on v2 and v3 and opens in the designer like a UI-made one (L-CDI-223, proven 2026-10-06 on a spreadsheet and a PDF). A mapping that parses every document of a folder with such models ran on 2026-10-07 (L-CDI-231).

**Create it (L-CDI-223).** All on `https://<pod>.<domain>.informaticacloud.com`:

| # | Call | Auth and body | Returns |
|---|---|---|---|
| 1 | `GET /saas/api/v2/intelligentstructure/getAtlanticWidget` | header `icSessionId` | not recorded |
| 2 | `POST /structurediscovery-service/atlweb/api/v3.0/validateWidget` | empty body; cookie `USER_SESSION=<session>` **and** header `IDS-SESSION-ID: <session>` | `{"valid": true}` plus the service cookies (`JSESSIONID`, `XSRF-TOKEN`, ...) |
| 3 | `POST /structurediscovery-service/upload?<resumable params>` | multipart: the same params as form fields and the sample as part `file`; headers `X-CSRF-TOKEN: <XSRF-TOKEN cookie>`, `X-CSRF-PARAM: _csrf`, `X-Ajax-call: true` (on every later POST too) | `inputText` and the learner used |
| 4 | `POST .../RunDataPreview` | form `runData` (fileName, text = inputText, key, learnerUse, treeType horizontal) | `aModelString`, the CLAIRE-discovered model, in under a second |
| 5 | `POST .../getStructure` | form `formData` (name, description, learnerUse, fileName, aModelString) | the model JSON |
| 6 | `POST /saas/api/v2/intelligentstructure/create?containerId=<v3 folder id>` | header `icSessionId`; `{"orgId": "<orgIdV3>", "@type": "structureDefinition", "name", "modelName", "description", "amodel": <the step-5 JSON as a string>}` | the structureDefinition and its v2 id |

**The Structure Discovery service's auth rules (L-CDI-224).**
- It accepts the platform session only as both cookie `USER_SESSION` and header `IDS-SESSION-ID`. The cookie alone returns 200 `{"valid": false}`, a refusal dressed as success; no session returns a 302 to the login page.
- After `validateWidget`, every POST must carry `X-CSRF-TOKEN` equal to the `XSRF-TOKEN` cookie the service set. Without it, or with `X-XSRF-TOKEN` instead, Tomcat answers 404, not 403, which reads like a wrong path. GETs need no CSRF header.
- The unauthenticated 302 points at a plain `http://` URL; a client that follows it through a corporate proxy reports a 504 after about 45 s. Probe without following redirects.

**What the learners make of a file, and the types a parser emits (L-CDI-229).** The mapping copies the model's field names, so fix them before you build it.
- A PDF goes through the `PdfToModel` learner: the document becomes key/value records (header, details and footer groups) with dates typed as dates. A free-text block that spans two lines is left out.
- The Excel learner splits code-like values into a token and a number: `ABC-001` becomes `ABC` + `1`, so the separator and the leading zeros are lost and such a code cannot be rebuilt. A banner line above a table becomes a field name with an empty value.
- Field names are cleaned to letters, digits and underscores (`Customer account no.` becomes `Customer_account_no_`).
- Structure Parser output ports take the model's types (bigint, decimal(10,2), string(n)), not string(255) everywhere. They load into VARCHAR target columns without complaint, with numbers re-rendered (40 becomes 40.0).

**What a Structure Parser stores, and how the designer finds the model (L-CDI-230).**
- In an exported mapping the parser carries `isdModelId` = `"@<v3 id of the model>"`, `isdLastModify`, `modelString` (a copy of the model) and a `passthrough` flag per output group. Because the model is copied, a later edit of the model reaches the mapping only after Synchronize.
- The designer looks the model up by its v2 id: `GET /frs/api/v1/Documents?$filter=documentType eq 'SAAS_STRUCTURE_DISCOVERY' and repoInfo/repoHandle eq '<v2 id>'` and `GET /da/web.saas.service/saasinfo/structureDiscoveryDetail?id=<v2 id>` (which needs a designer session). It fills the Output Fields tab from `POST /structurediscovery-service/groupsWithXpath` (form body `aModelString=<model string>`).
- The input group `Input_Group` takes `FilePath` (string 4096) or `Data` (binary); there is one output group per model group, plus `Unidentified`.
- These fields come from the export of a parsing mapping and the designer's request log. That mapping was built in the designer through browser automation (L-UI-035), so the Structure Parser is not yet among the generator's proven node types of §7. That mapping, edited in its export (a new flat-file source, transplanted rule steps) and re-imported OVERWRITE under its own id, ran (L-CDI-275, L-CDI-278, 2026-10-26).

**Parse every document of a folder, and keep the source file on each row (L-CDI-231).** Proven 2026-10-07: one run parsed 8 documents of 3 types into 32 rows, each with its file name and path, and 0 rows unidentified.
1. **Source:** a warehouse view that lists the documents, one row per file with its path, filtered per flow on folder and extension in the source's Advanced filter (on Snowflake that filter is sent verbatim as the WHERE clause, and Preview Data ignores it: verify with a run, L-CDI-233).
2. **Expression:** turn the server path into the local path of the connector's download folder, `REPLACESTR(1, PATH, '<server prefix>', '<local folder>')`, and feed it to the parser's `FilePath`. For SharePoint Online that folder is the connection's `Attachment_File_Path` ([Connector Notes](../03-connections/02-connector-notes-bigquery-postgresql-salesforce-jdbc-flat-file.md) §6, L-CONN-102).
3. **Passthrough:** in the parser's Output Fields tab, tick Passthrough on each output group. Every incoming field except the one mapped to `FilePath`/`Data` then comes out on that group, so the file name and path land on every parsed row.
4. **Unidentified:** land the `Unidentified` group too, so content no model can place never drops out silently.
5. **One flow per document type,** ordered with Flow Run Order.

**Parse bytes that sit in a column, with no file on the agent (L-CDI-244).** Proven 2026-10-13 on two PDFs that a CRM read had
landed in warehouse rows as base64 text:
1. **Expression:** `DEC_BASE64(<base64 column>)` into an output port of platform type binary, with a precision at least the
   largest document (8,388,608 worked).
2. **Structure Parser:** `inputType` `BUFFER`; the Input_Group field `Data` (binary) and the data adapter's input field `Data`
   get the same precision, and the field mapping maps the binary port onto `Data`.
3. **Keep the base64 text out of the parser's input group** (an exclude rule on the link): every incoming field is passed
   through to each parsed row, so a 1.3 MB text column would repeat on every row.

A Snowflake BINARY column cannot be the source instead: it fails with 'Unknown native type' (L-CONN-113).

**Feed the parser from the document itself, with no listing file (L-CDI-275).** Proven 2026-10-26, so the document is the lineage source:
1. **Source:** a flat-file source object that is the PDF itself: code page ISO-8859-1 (every byte is a valid character), no header (`headerLineNo` 0, first data row 1) and `retainMetadata` true, so the run keeps the design-time column.
2. **Keep one row with a filter**, not the row limit: `readOptions.rowLimit` = 1 was ignored for the flat-file read, every one of 1,782 lines went through the parser again and the run hung for more than 15 minutes. Use advancedFilterCondition `SUBSTR(<column>, 1, 5) = '%PDF-'` (the PDF's first line).
3. **A constant `FilePath`** from an Expression. The mapping's catalog reference is then the PDF, which maps onto the cataloged storage file ([Search, Lineage & Marketplace](../09-catalog-lineage/04-search-lineage-marketplace.md)).
4. Re-import OVERWRITE to keep the mapping id, so the task and the taskflow stay unchanged.

**Designer traps (L-CDI-232).**
- Changing the model of an existing Structure Parser (for example on a flow copied in the designer, L-UI-034) removes its field mapping, its links and the Passthrough ticks: re-link, re-map `FilePath` and re-tick Passthrough afterwards.
- Linking from a parser with several output groups opens a 'Select Output Group' dialog; dropping a new transformation onto an existing link keeps the group.
- The model editor shows a spinner forever in headless Chromium: wait for the 200 of the service's `openStructureData` request instead (L-UI-033).

## 11. Overturned beliefs (latest evidence wins)

| Earlier belief (dates) | Overturned by (date) |
|---|---|
| CDI mapping authoring is UI-only; one mapping must be authored in the UI first (2026-07-06 → 2026-09-22; L-CDI-174) | Template tasks (2026-09-23, L-CDI-003/021) and synthesized IMF mappings (2026-09-29, L-CDI-033) |
| Headless CDI data movement is walled: a cold PostgreSQL source cannot resolve (2026-09-22/23; L-CDI-178) | The object path `<schema>/TABLE/<table>` (L-CDI-162) and cloned template tasks (L-CDI-021), 2026-09-23/24 |
| A mapping's connection and SQL are compiled into a binary `bin/@3.bin` (2026-07-07; L-CDI-180) | The file is IMF JSON text, edited and synthesized (2026-09-22 → 09-29, L-CDI-027) |
| Hand-built packages are rejected with `MigrationSvc_030` (2026-06-28 → 09-28; L-CDI-181) | From-scratch packages import when metadata and checksums are right (2026-09-29, L-CDI-032) |
| There is no REST read-back of a mapping's internals (2026-07-26; L-CDI-182) | Export the mapping and read its IMF (2026-09-22, L-CDI-027) |
| The first mapping for a new connector pair must be UI-authored (2026-07-07; L-CDI-191) | The generator built PostgreSQL-source and BigQuery-target mappings from exemplars (2026-09-29, L-CDI-033); other adapters are still untested |
| Swapping a mapping's target connection later is a quick change (2026-06-27; L-CDI-190) | Cross-connector retarget silently reverts (2026-07-04) and target-parameter POSTs are no-ops on real mappings (2026-09-29, L-CDI-050) |
| BigQuery full pushdown cannot be enabled over REST (2026-09-29; L-CDI-042) | Two session properties plus `enableCrossSchemaPushdown` on the v2 task, proven by `OPT_63367` in the session log (2026-10-01; L-CDI-202) |
| Lookup, Rank, Sequence, Data Masking and DQ transformations cannot be built headless (2026-09-29) | The generator built and ran them from class shapes read out of the designer bundle (2026-09-30 onward; L-CDI-204) |
| Every Structure Parser output field is a string(255); the real types stay in the model (2026-10-06; L-CDI-225) | The ports take the model's types: bigint, decimal(10,2), string(n) (2026-10-07; L-CDI-229) |
| A Structure Parser stores the model's v2 id as `isdModelId` (2026-10-06; L-CDI-226) | The mapping stores `"@<v3 id>"`, a copy of the model and a passthrough flag per output group; the designer resolves the model by its v2 id (2026-10-07; L-CDI-230) |
