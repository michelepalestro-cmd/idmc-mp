# Lessons: Mappings & Mapping Tasks (CDI)
291 lessons: 271 current, 1 disputed, 19 superseded; evidence dated 2026-06-27 to 2026-11-19. Topic docs: [knowledge/04-mappings](.).

## Current

### L-CDI-001  The CDI object chain: mapping (DTEMPLATE) -> mapping task (MTT) -> linear or advanced taskflow -> schedule
**Kind:** ROUTE · **Proven:** 2026-09-29 · **Evidence:** v2 and v3 reads of every object type; 160 MTTs and 10 taskflows inventoried
A mapping is the design (v3 type `DTEMPLATE`, inner `documentType:"MAPPING"`; v2 `/api/v2/mapping` for read and delete). A mapping task is its runnable instance with parameters (v2 `/api/v2/mttask`, v3 `MTT`, FRS document type `MCT`). A linear taskflow is v2 `/api/v2/workflow` (v3 `WORKFLOW`), and an advanced taskflow is v3 `TASKFLOW`. A schedule (v2 `/api/v2/schedule`) is org-level and bound through `scheduleId`. Everything a pipeline runs is ultimately a mapping task started with `POST /api/v2/job`.

### L-CDI-002  A fresh org already holds about 160 stock template assets; count real tasks with /api/v2/mttask
**Kind:** GOTCHA · **Proven:** 2026-06-29 · **Evidence:** v3 object type counts (MAPPLET 48, DTEMPLATE 44, DMAPPLET 20, CLEANSE 18, DICTIONARY 15, PARSE 7) with 0 user mappings
`GET /public/core/v3/objects` on a new org lists many stock add-on assets. They are templates, not user work. Count real tasks with `GET /api/v2/mttask`. `/api/v2/diTask` returned 404.

### L-CDI-003  Add-On Bundle Data Transfer templates are parameterized mappings you can wrap in tasks directly
**Kind:** OVERTURNED · **Proven:** 2026-09-23 · **Evidence:** first genuine runs 2026-09-23; 46/46 SUCCESS per hourly cycle
The Copy Data templates under `Add-On Bundles/Data Transfer Templates` have `fixedConnection=false` and `connParam=true` on `$Source$` (`EXTENDED_SOURCE`) and `$Target$` (`TARGET`): `dsst__copy_data_new_tgt` (auto-creates the target), `dsst__copy_data_existing_tgt`, `dsst__copy_with_lookup_*`, `dlt__copy_data` (incremental-key filter parameters) and `INFA_Generic_Cloud_Service_Mapping`. A mapping task over one of them supplies its own connections, objects or `customQuery`, so no UI-authored mapping is needed. Each template shows `tasks=0` until used.

### L-CDI-004  Bundle templates are system content: FRS delete:false, export 403 MigrationSvc_038, import with REUSE
**Kind:** ERROR · **Proven:** 2026-09-29 · **Evidence:** 403 on bundle export for a non-admin user; FRS delete:false; import reported "Reuse existing object"
A v3 export of an Add-On Bundle template (e.g. `dsst__copy_data_new_tgt`, `dlt__copy_data`) can return `403 MigrationSvc_038` "User does not have required permissions". It reproduced in some orgs and dates and not in others. User-owned mappings and bundle rule specs exported fine. FRS reports `delete:false` on bundles even for an admin. When migrating tasks built on a bundle template, import with REUSE so the target's own copy is used.

### L-CDI-005  A target org reuses its own build of a bundle template; a TmplPatternRuleImpl failure passed on rerun
**Kind:** GOTCHA · **Proven:** 2026-09-28 · **Evidence:** one failure, then a successful plain rerun
After an org-to-org import, tasks bind to the target's copy of the bundle template, which can be a different build from the source's. One task failed once with "Cannot propagate link rule of type TmplPatternRuleImpl between Expression and IUpdateStrategyNode5" and succeeded on a plain rerun. Rerun before debugging, and validate each task once after an import.

### L-CDI-006  A mapping task carries no field array; field overrides over v2 return 400
**Kind:** GOTCHA · **Proven:** 2026-09-24 · **Evidence:** inspection of exported task packages; `overriddenFields` → HTTP 400
Exported mapping tasks contain no field array: fields live in the mapping referenced by `mappingId`. So precision or type changes cannot be made on a template-based task. Use a source view or SQL that casts, change the mapping itself, or use a JSON-typed target column for long text.

### L-CDI-007  Tasks over ordinary mappings are schema-bound; a task-level connection swap does not reach the mapping
**Kind:** GOTCHA · **Proven:** 2026-09-22 · **Evidence:** the task became invalid after a connection-only swap; an import log showed the original connection
A task built on an ordinary (user-authored) mapping has `connectionParameterized:false` and `objectParameterized:false`. Changing only its connection yields an invalid task, and a task-level `sourceConnectionId` does not propagate into the mapping. Check a mapping's real binding in its export, not its name. Clone a template-based task, or edit the mapping's objects and fields.

### L-CDI-008  The v2 mapping-task list omits frsGuid and scheduleId; read each task's detail
**Kind:** GOTCHA · **Proven:** 2026-09-29 · **Evidence:** a scan of 159 task details found a task-level binding the list did not show
`GET /api/v2/mttask` and `GET /api/v2/task?type=MTT` return names and ids but not `frsGuid` and not `scheduleId`. Anything that needs the v3 id, or needs to know whether a task has its own schedule, must `GET /api/v2/mttask/<id>` for every task.

### L-CDI-009  Resolve ids across planes: frsGuid, name match for workflows, assetFrsGuid, v3 lookup by path
**Kind:** RECIPE · **Proven:** 2026-09-25 · **Evidence:** workflow placement and a taskflow generator depended on it; deletes resolved this way on 2026-09-28
A v2 task's v3 id is its `frsGuid` (from the detail GET). v2 workflows carry no `frsGuid`: list v3 `type=='WORKFLOW'` objects and match the last path segment to the name, requiring exactly one hit. A v2 mapping's v3 id is its `assetFrsGuid`. `POST /public/core/v3/lookup {"objects":[{"path":"<project>/<folder>/<name>","type":"MTT"}]}` resolves by path. Cache name → GUID per org.

### L-CDI-010  Address tasks by id, never by name
**Kind:** LAW · **Proven:** 2026-09-28 · **Evidence:** 15 task names also existed in unrelated folders of the same org; 0 workflow task ids pointed at them after the check
An org with older content held tasks with the same names in other folders, so any lookup by name (to run, bind, delete or map ids) can hit the wrong object. Record ids at creation or import time, and resolve names only within the intended folder or among the objects created by one import.

### L-CDI-011  The v3 objects type filter is not validated: an unknown type returns 0
**Kind:** GOTCHA · **Proven:** 2026-09-25 · **Evidence:** an audit filtering `type=='DBMI'` missed 23 `DBMI_TASK` objects
`GET /public/core/v3/objects?q=type=='<X>'` returns an empty list, not an error, when `<X>` is not a real type name. Sweep candidate type names, or list everything unfiltered and group by type on the client.

### L-CDI-012  v2-created mapping tasks do appear in the v3 objects list
**Kind:** OVERTURNED · **Proven:** 2026-09-29 · **Evidence:** a live v3 read listed 160 MTTs and 10 taskflows
By 2026-09-25/29 the v3 objects list returned every v2-created mapping task (type `MTT`). An earlier sweep that saw none was probably a filter or paging artifact. When a v3 count looks like zero, cross-check with `GET /api/v2/task?type=MTT` before concluding anything, including that an org was wiped.

### L-CDI-013  Attribute tasks to runtime environments with GET /api/v2/mttask
**Kind:** RECIPE · **Proven:** 2026-07-04 · **Evidence:** per-runtime inventories of production and pre-production task sets
`GET /api/v2/mttask` returns `runtimeEnvironmentId` per task, so it is the source for "which tasks run on which runtime". v3 objects are org-scoped and carry no runtime field.

### L-CDI-015  v2 task resources mount per pod and per licensed engine
**Kind:** OVERTURNED · **Proven:** 2026-07-26 · **Evidence:** live A/B: 200 on one dm-us org, 404 on a dmp-us sub-org holding 876 privileges
`/api/v2/dss`, `dtemplate`, `dmask`, `dreplicate`, `plan` and `fileListener` mount per pod and per licensed engine, not per org. They were the biggest source of false "not entitled" calls. Never generalize a v2 inventory from one org.

### L-CDI-017  No headless browse of connection objects: know the connector's object path format
**Kind:** WALL · **Proven:** 2026-09-22 · **Evidence:** exhaustive 404s across v2 and v3 browse shapes
v2 `/api/v2/connection/{id}/objects|source|metadata|objectbrowse|objectcategories`, `/api/v2/mttask/objectDetails|browseObjects` and `/metadata/objects` all returned 404. So did v3 `/public/core/v3/connections[/{id}/objects|objectsList|metadata]` ("No static resource"). An older reference lists `GET /api/v2/connection/source/<connId>` as a source-metadata browse (200 or 403 per connection, July 2026). Write object paths from the connector's known format instead of browsing.

### L-CDI-018  v2 object-id type codes and FRS document types
**Kind:** RECIPE · **Proven:** 2026-09-29 · **Evidence:** ids observed across two orgs; FRS move receipts
A v2 id is 20 characters: the 6-character v2 org id, a 2-character type code, then a 12-character sequence. Observed codes: `0Z` mapping task, `0N` workflow, `D0` schedule, `17` mapping, `0B` connection, `08` agent, `25` runtime environment. v3/FRS ids are 22-character base-62 GUIDs. FRS reports a mapping task as document type `MCT`, the same code an advanced taskflow's Data Task uses for "Task Type".

### L-CDI-019  Job-history counts include runs of objects that no longer exist
**Kind:** GOTCHA · **Proven:** 2026-09-29 · **Evidence:** 930 of the last 1,000 job-history rows belonged to deleted test objects
Job totals in the monitoring views can be dominated by old runs of deleted objects. Filter by object and date before using job counts as evidence.

### L-CDI-020  POST /api/v2/mapping is not a create surface; v3 objects POST is 405
**Kind:** WALL · **Proven:** 2026-07-06 · **Evidence:** 400 HTML "Internal error, please contact technical support"; `/api/v2/Mapping` 404; `POST /public/core/v3/objects` 405; `/public/core/v3/mappings` 404; still true 2026-09-29
No REST call creates a mapping design directly. Do not debug the body. Author through import packages instead (a cloned or synthesized DTEMPLATE, then a v2 task over it). The vendor previewed a mapping-design API for about late 2026, GA about 2027 (documented in a July 2026 conversation, unproven).

### L-CDI-021  Route 1: tasks over the copy-data template with customQuery SQL move data fully headless
**Kind:** OVERTURNED · **Proven:** 2026-09-24 · **Evidence:** hourly cycles 46/46 SUCCESS, ~1.5M rows per cycle; later 159 tasks ran for days
Take one working task over `dsst__copy_data_new_tgt`. `GET /api/v2/mttask/<templateTaskId>`, change the name, `$Source$.customQuery` (or source object) and target object, then `POST /api/v2/mttask` to create, or `POST /api/v2/mttask/<id>` to update, and run with `POST /api/v2/job`. Landing, raw, staging, gold, DQ marts, reverse-ETL, SaaS upserts, flat-file ingest and evidence snapshots were all built this way. The cost: empty two-box canvases, logic invisible to lineage, and about 20 s plus one job per task.

### L-CDI-022  Clone a template mapping task over v2: which fields to strip and which parameters to set
**Kind:** RECIPE · **Proven:** 2026-09-25 · **Evidence:** 159 tasks built this way; probe tasks created and deleted with zero residue
Drop `id, orgId, createTime, updateTime, createdBy, updatedBy, frsGuid`. Set `name`, `description`, `shortDescription` and `sessionProperties={}`, and pop `id` in every `parameters[]` entry. `$Source$`: `sourceConnectionId`; `customQuery` (or pop it); `sourceObject = objectName =` `'DUMMY_Source'` or `'<schema>/TABLE/<t>'`; each `extendedObject.object`/`objects[]` entry gets `{name, label, dbSchema:""}`. `$Target$`: `targetObject = targetObjectLabel = newObjectName = objectName = objectLabel = '<dataset>/<table>'`, `tgtObjectAttributes={"parent":"<dataset>"}`, `runtimeAttrs={}`, `oprRuntimeAttrs={"writeMode":"Bulk","writeDisposition":"Write truncate"}`, `truncateTarget=false`. `POST /api/v2/mttask` and require 200.

### L-CDI-023  customQuery runs in the dialect of the source connection
**Kind:** GOTCHA · **Proven:** 2026-07-06 · **Evidence:** BigQuery 400 "Syntax error: Unexpected "[" ... escape with backtick"; gone after the fix
The SQL in `$Source$.customQuery` runs on the source connection, so it must use that engine's dialect (GoogleSQL for BigQuery) even when the target is another warehouse. Half-translated queries that mix dialect-specific functions (`QUALIFY`, `REGEXP_CONTAINS` with raw strings) fail in both. Translate with an explicit map when the SQL must run elsewhere.

### L-CDI-024  Non-ASCII in a BigQuery customQuery fails the reader with "missing CR"
**Kind:** GOTCHA · **Proven:** 2026-09-23 · **Evidence:** the task failed with "IOException: missing CR" until an em dash in a comment was removed
Before storing SQL in a task, drop `--` comment lines and trailing comments, remove non-ASCII characters and strip the trailing `;`. In practice the only non-ASCII characters were in comments.

### L-CDI-025  Route 2 via the iics CLI: clone an exported mtTask.json and re-import it
**Kind:** OVERTURNED · **Proven:** 2026-07-09 · **Evidence:** 18/18 cloned tasks listed by the CLI and ran state=1
A mapping task's source SQL and target table are plain editable fields in its exported `mtTask.json` (`customQuery`, `targetObject`), and one pass-through template mapping can serve many tasks. Export one working task, clone it per output (new `customQuery`, target, name and `frsGuid`), recompute checksums, and import with the Informatica `iics` CLI (`-r us` region, `type==MTT` filters, `--sync=true`). Then run with `POST /api/v2/job`.

### L-CDI-026  Route 3: package-clone a working mapping and rebuild its field arrays by position
**Kind:** RECIPE · **Proven:** 2026-07-04 · **Evidence:** 14/14 new-shape marts ported with exact parity (set difference 0)
Clone a live mapping through a v3 export. For a new output shape, rebuild the source and target field arrays by position from the live target schema, with fresh `$$ID`/`##ID` references and correct `platformType`/`javaType`/`nativeType`/`precision` per column (renaming is not enough). Swap `customQuery`, repoint the target object, recompute SHA-256 lines and import. Then `POST /api/v2/mttask` and run.

### L-CDI-027  A mapping's IMF lives in bin/@N.bin as JSON text, not a compiled binary
**Kind:** OVERTURNED · **Proven:** 2026-09-22 · **Evidence:** export SUCCESSFUL, file contents inspected; the format was later used to synthesize 11 mappings
In a v3 export of a mapping (`.DTEMPLATE.zip`), the file named by `mappingTemplate.json`'s `templateId` holds the mapping definition as text JSON: IMF with `content` and `metadata.$$classInfo`. In the exports seen that was `bin/@3.bin`, and `bin/@2.bin` was a preview JPEG. `mappingTemplate.json` `references[]` holds the connection references. Exported user mappings are `fixedConnection:true` and schema-baked, so retargeting one means editing sources, targets and field graphs in the IMF, not only a connection id.

### L-CDI-028  Swap a connection GUID in place (22 characters) and re-hash only the path-keyed lines
**Kind:** RECIPE · **Proven:** 2026-08-19 · **Evidence:** import `checksumValid:true`; the cloned mapping ran SUCCESS 52/52
A connection swap inside a cloned mapping's IMF can be an in-place replacement: IDMC GUIDs are 22 characters, so offsets are preserved. After editing, recompute only the path-keyed SHA-256 lines of the changed entries in `exportPackage.chksum`. The opaque GUID-keyed lines could stay stale and the import still reported `checksumValid:true`.

### L-CDI-029  The objectRefs trap: an objectRef without a matching entry fails the import with MigrationSvc_031
**Kind:** ERROR · **Proven:** 2026-09-28 · **Evidence:** MigrationSvc_031 with the extra ref, a clean import without it (2026-08-19); SUCCESSFUL imports after remapping (2026-09-28/29)
Every GUID in an object's `metadata.objectRefs` (in `exportMetadata.v2.json`) must resolve. Adding a new connection GUID to `objectRefs` with no matching entry failed with `MigrationSvc_031`, and a dangling objectRef gives `MigrationSvc_031` with empty details. Two ways work: leave `objectRefs` naming the original connection and let the swapped GUID resolve in the target, or add an `exportedObjects` entry for the connection (`objectType:"Connection"`, `path:"/SYS"`, `repoInfo.repoHandle:<v2 connection id>`), as synthesized packages do.

### L-CDI-030  Checksum rules for an edited package (MigrationSvc_073)
**Kind:** RECIPE · **Proven:** 2026-09-28 · **Evidence:** `checksumValid:true` and SUCCESSFUL imports after each edit
`exportPackage.chksum` holds one `path=SHA256HEX` line per file: upper-case hex, with spaces in paths escaped as `\ `. Replace only the lines of files you changed, including the line for `exportMetadata.v2.json` itself; otherwise the import fails with `MigrationSvc_073` "package has been modified". Keep every other line byte-identical, and drop the matching rows of the contents CSV when you remove an object.

### L-CDI-031  Package edits did not retarget a mapping to a different connector type
**Kind:** WALL · **Proven:** 2026-07-07 · **Evidence:** the compiled definitions of 22 cloned "twin" mappings still referenced only the original warehouse connection
A mapping cloned through an export package kept its original source/target connection binding after the package was edited to point at a different connector type (one cloud warehouse to another). Retargeting an existing mapping across connector types was not achieved headless and was not retested after the IMF format became understood. Synthesize a new mapping for the other adapter (L-CDI-033), or author it once in the UI.

### L-CDI-032  From-scratch import packages are accepted when metadata and checksums are right
**Kind:** OVERTURNED · **Proven:** 2026-09-29 · **Evidence:** generated mapping, CAI and taskflow packages imported SUCCESSFUL, `checksumValid:true`
A package you build yourself imports fine if it has:
- the object files under `Explore/<project>/<folder>/`;
- the real `<folder>.Folder.json` and `<project>.Project.json`, copied from any genuine export in that folder, or `exportedObjects` entries with the real project and folder GUIDs;
- an `exportMetadata.v2.json` listing folder, project and each object (`objectGuid`, `objectName`, `objectType`, `path`, `metadata.objectRefs`, `additionalInfo`);
- a correct `exportPackage.chksum`.

`400 MigrationSvc_030` is what an empty or invalid multipart gets.

### L-CDI-033  Route 5: synthesize real multi-transformation mappings as IMF JSON and import them
**Kind:** OVERTURNED · **Proven:** 2026-09-29 · **Evidence:** 11 mappings imported SUCCESSFUL, two-way EXCEPT DISTINCT = 0 against the live SQL, and an idempotency double run
Write a JSON spec of nodes (`source` query or table, `expression`, `filter`, `router`, `joiner`, `aggregator`, `sorter`, `target`) and links. Generate the IMF template JSON, package it as a DTEMPLATE, and import it (REUSE first, OVERWRITE to rebuild under the same GUID). Wrap it in a v2 task with `{mappingId, runtimeEnvironmentId}`, move it into the folder, run it and check parity. The mappings show real transformations on the canvas. Proven: warehouse query/table sources, BigQuery targets, Expression, Router, Joiner and Aggregator, plus PostgreSQL-source ingest mappings in parity runs.

### L-CDI-034  The synthesized DTEMPLATE package layout
**Kind:** RECIPE · **Proven:** 2026-09-29 · **Evidence:** every generated package imported SUCCESSFUL
The outer zip holds `Explore/<project>/<folder>/<name>.DTEMPLATE.zip`, `exportMetadata.v2.json` and `exportPackage.chksum`. The inner zip holds:
- `mappingTemplate.json`: `[{"@type":"mappingTemplate","id":"@1","name","assetFrsGuid":"<22-char guid>","templateId":"@2","documentType":"MAPPING","fixedConnection":true,"valid":true,"references":[{"@type":"reference","refObjectId":"@<conn guid>","refType":"connection"}]}]`;
- `fileRecord.json`: `[{"@type":"fileRecord","id":"@2","type":"IMFOBJECT","size":<n>,"additionalInfo":"com.informatica.metadata.template.common.Template"}]`;
- `bin/@2.bin` (the IMF JSON) and `metadata.meta`.

`exportMetadata.v2.json` lists the DTEMPLATE (`objectRefs` = connection guids), the Project, the Folder, and each Connection (`path "/SYS"`, `repoInfo.repoHandle` = its v2 id).

### L-CDI-035  IMF content: transformation classes, $$classInfo, adapters, link rules, type map
**Kind:** RECIPE · **Proven:** 2026-09-29 · **Evidence:** proven node types ran; exemplars harvested from real mappings
- **Structure.** The IMF has `content` = a `Template` (`$$class`, `documentType:"MAPPING"`, `name`, `links:[TmplLink]`, `transformations:[...]`) and `metadata.$$classInfo` = `{<n>: "com.informatica.metadata.template...<Class>"}`. Every object carries `$$ID` and `$$class`; references are `{"##ID","$$class"}`.
- **Transformations.** `TmplSource`/`TmplTarget` each carry a `BaseAdapter` (`connectionId:"saas:@<conn frsGuid>"`, `objectType` `QUERY` or `SINGLE`, a `DataObject` with `BaseAdapterField`s, `ReadOptions`/`WriteOptions`, `oprRuntimeAttributes`). The others are `TmplExpression` (OUTPUT/VARIABLE fields), `TmplRouter` (`GroupFilterCondition`s), `TmplFilter`, `TmplJoiner` (`JoinCondition`s, `joinType`), `TmplAggregator` (group-by fields) and `TmplSorter` (`SortEntry`s).
- **Groups and links.** Groups hold ports. `TmplAllRule` passes every field through; `TmplNameRule` entries select or rename fields on a link.
- **Type map.** Platform types come from `smd:com.informatica.metadata.seed.platform.Platform.typesystem/<string|bigint|decimal|double|date/time>`.

### L-CDI-036  Harvest real mappings read-only from another org as exemplars
**Kind:** RECIPE · **Proven:** 2026-09-29 · **Evidence:** an export of 78 real mappings used as IMF exemplars
If the org you build in has no real mappings to copy, export (read-only) the mappings of an org that has them, covering Joiner, Aggregator, Router, Expression and Lookup patterns. They give the exact IMF shape of each transformation and adapter for a generator.

### L-CDI-037  Create a mapping task over a real mapping with a minimal v2 body
**Kind:** RECIPE · **Proven:** 2026-09-29 · **Evidence:** 11 tasks created, HTTP 200 each
After importing the mapping, find its v2 id with `GET /api/v2/mapping` (match by name inside the intended folder). Then `POST /api/v2/mttask {"@type":"mtTask","name":"mt_<x>","description":"...","mappingId":"<v2 mapping id>","runtimeEnvironmentId":"<reId>"}`. Reuse the task if the name already exists, and assert the org first. The task lands in `Default`: move it with FRS MoveEntities, then run it with `POST /api/v2/job`.

### L-CDI-038  In a synthesized mapping the BigQuery write disposition must sit in oprRuntimeAttributes
**Kind:** GOTCHA · **Proven:** 2026-09-29 · **Evidence:** session logs before and after; two mappings re-imported OVERWRITE with the fix
A BigQuery target's truncate or append behaviour comes from its adapter's `oprRuntimeAttributes` (`RuntimeAttribute` `writeDisposition` = "Write truncate" or "Write append", `writeMode` = "Bulk"). `WriteOptions.truncate` alone is ignored: the session log says "Write append" and every run appends.

### L-CDI-039  Fields declared JSON fail in BigQuery Simple mode; declare them STRING
**Kind:** GOTCHA · **Proven:** 2026-09-29 · **Evidence:** "The mapping failed because the table contains [JSON] data type that is incompatible with the [Simple] connection mode" (2026-09-29); "JSON incompatible with Simple connection mode" (2026-07-09); runs succeeded with STRING declarations
A mapping that declares JSON-typed fields on a BigQuery Simple-mode connection fails, on both source tables and target columns. Declare those fields STRING in the mapping. A pre-created JSON target column still receives the text through Bulk loads. Keep the connection in Simple mode (Hybrid breaks mappings; L-CDI-156).

### L-CDI-040  A JDBC V2 target writes into the database bound on its connection; the object's schema is ignored
**Kind:** GOTCHA · **Proven:** 2026-09-29 · **Evidence:** a parity probe wrote 1,723 rows into the live table; no data lost because the content matched; parity runs against a scratch database still landed in the live database until a separate scratch connection was used (2026-09-29)
A synthesized mapping whose JDBC V2 target object named a scratch schema wrote into the database the connection is bound to, ignoring that schema. Parity and scratch runs against such targets need their own connection, and a run-time assertion that no parity task points at a live database. To point parity or scratch runs at another database, clone the connection (`GET /api/v2/connection/<id>`, change the name and the JDBC URL's database, `POST /api/v2/connection` without the id, test it) and bind the scratch mapping to that clone; never change the live connection's URL for a test.

### L-CDI-041  Route 4: author one mapping in the designer (automated), then clone it
**Kind:** PROCESS · **Proven:** 2026-08-19 · **Evidence:** 16 marts authored this way, each with exact parity
When no headless route has proven a transformation or adapter, author one mapping in the Data Integration designer and clone the variants. Automation that worked:
- drive Playwright from a host outside any transparent proxy (behind one, the design SPAs rendered blank);
- enter SQL with CodeMirror `setValue(...)` plus `save()`, and never press Escape before the commit;
- react-select options match `[class*='-option']`;
- if a large query (about 6 KB) hangs the field-derive spinner, adopt the persisted `Mapping<N>` by GUID and delete orphans with `DELETE /api/v2/mapping/<id>`.

Cost: 30–75 minutes per mapping.

### L-CDI-043  Full pushdown runs only when source and target share an ecosystem; the session log is the proof
**Kind:** LAW · **Proven:** 2026-10-01 · **Evidence:** Documented in the CDI guides; live-proven on a 5-target BigQuery-to-BigQuery mapping whose session logs showed OPT_63367 and one INSERT INTO per target (2026-10-01)
One mapping runs with full pushdown (SQL ELT) when source and target are in the same ecosystem (proven BigQuery to BigQuery), and in agent mode when they cross ecosystems (to another warehouse, a database or a SaaS). The generated warehouse SQL in the session log is the proof that pushdown happened (L-CDI-202). Group targets by ecosystem when consolidating, and keep pushdown only where it measures faster: it writes a mapping's targets one after another (L-CDI-203). Newer evidence: L-CDI-305.

### L-CDI-044  Every connector a mapping uses must be on the one runtime environment that runs it
**Kind:** GOTCHA · **Proven:** 2026-07-06 · **Evidence:** state 3 in ~2 s, 0 rows, "DTM process terminated unexpectedly"; the agent package inventory plus a binding check
With the source connector on one agent and the target connector on another, a task failed within about 2 s. A session abort at "Importing Connection: <conn>" (`trepcnx.cpp:296`) means the task's runtime cannot use that connection: it is bound to another runtime environment, or that connector's package is missing on the agent. Colocate connectors on one runtime, or give the other side its own task.

### L-CDI-045  APP_13400 "Compute capacity exceeded" comes from a throttled target warehouse
**Kind:** ERROR · **Proven:** 2026-07-08 · **Evidence:** the capacity throttle on the warehouse side; tasks wrote 0 rows until capacity was restored
`APP_13400 Compute capacity exceeded` on a connection fetch came from the warehouse's capacity throttle, not from IDMC. Tasks against the throttled warehouse ran but wrote 0 rows with "DTM process terminated". Fix capacity: pause the jobs hitting it, then suspend and resume the capacity.

### L-CDI-046  Minimal task bodies fail APP_13507; APP_13533 means no mappingId; update is POST /{id}, PUT is 405
**Kind:** ERROR · **Proven:** 2026-08-19 · **Evidence:** APP_13507 on a minimal body; 403 APP_13533 without a mappingId; PUT 405 on both paths
`POST /api/v2/mttask` over a Copy Data template with a minimal body fails with `APP_13507`. The body needs the full `$Source$` (`EXTENDED_SOURCE`) and `$Target$` (`TARGET`) parameter objects, so clone a working task. `403 APP_13533 "specify a mapping id"` means a mapping was being authored through the task API. Updating is `POST /api/v2/mttask/<id>` (the v2 idiom), and `PUT` returns 405.

### L-CDI-047  Value-less template parameters need uiProperties.required=false and placeholder values
**Kind:** GOTCHA · **Proven:** 2026-09-23 · **Evidence:** task create + validate returned `valid=True` and ran on the agent
On a task over `dsst__copy_data_new_tgt`, value-less STRING parameters such as `$p_tgt_excluded_fields$` and `$p_filter_src$` without a `uiProperties.required` key are treated as required, and the task is rejected with `APP_13506`/`APP_13507`. Set `uiProperties.required="false"` and placeholders (`$p_filter_src$=TRUE`, `$p_tgt_excluded_fields$=NONE`). `errc=-1` under `schemaMode:"async"` means validation was deferred, not failed; `valid=true` is authoritative.

### L-CDI-048  Target write options go in $Target$.oprRuntimeAttrs; runtimeAttrs is ignored
**Kind:** GOTCHA · **Proven:** 2026-09-23 · **Evidence:** truncation was honoured only after the attributes moved
In a task over a Copy Data template, BigQuery write options are read from `$Target$.oprRuntimeAttrs`, e.g. `{"writeMode":"Bulk","writeDisposition":"Write truncate"}`. Values placed in `runtimeAttrs` are silently ignored for BigQuery; JDBC V2 targets use `runtimeAttrs` for "Pre SQL" (L-CDI-171).

### L-CDI-049  Set fetchMode RUNTIME or new target columns silently land NULL
**Kind:** GOTCHA · **Proven:** 2026-09-25 · **Evidence:** NULL columns observed after columns were added; populated after the change
A mapping task keeps the field list it had when it was created. If the target table or the source query gains columns later, the task silently writes NULL into them. Set `fetchMode:"RUNTIME"` on `$Source$` and `$Target$` so field metadata is read at run time, or rebuild the task after the schema changes.

### L-CDI-050  Silent no-op: a target-parameter POST returns 200 but the task keeps its mapping's targets
**Kind:** GOTCHA · **Proven:** 2026-09-29 · **Evidence:** 10 task POSTs → 200 with read-backs unchanged; after the mappings were re-imported OVERWRITE, the tasks showed the new targets (2026-09-29); a cross-connector `targetConnectionId` change reverted silently (2026-07-04)
Updating a task over a real (fixed-connection) mapping by POSTing changed target fields (`targetObject`, labels, `newObjectName`, connection) returns HTTP 200, but the task re-derives its targets from the mapping on every read and run. To retarget, change the mapping: rebuild or edit its package with the new targets and re-import it with OVERWRITE under the **same GUID**, then re-read the task. Tasks over Copy Data templates are different: their `$Target$` is task-owned and target changes stick. Always read back after any write.

### L-CDI-051  Switch an existing task between Write truncate and Write append
**Kind:** RECIPE · **Proven:** 2026-09-27 · **Evidence:** append-only snapshot tasks ran on every scheduled cycle after the switch
`GET /api/v2/mttask/<id>`. If `$Target$.oprRuntimeAttrs.writeDisposition` already equals the wanted value, stop. Otherwise set `{"writeMode":"Bulk","writeDisposition":"Write append"}` (or "Write truncate"), drop `orgId, createTime, updateTime, createdBy, updatedBy`, and POST the body back to `/api/v2/mttask/<id>`.

### L-CDI-052  Delete mapping tasks and mappings with v2 DELETE and read the delete back
**Kind:** ROUTE · **Proven:** 2026-09-29 · **Evidence:** 200 per delete; read-back 403; mapping counts dropped (123 → 61 on one cleanup)
`DELETE /api/v2/mttask/<id>` → 200, and a read-back 403 means gone. Resolve the v2 id from a v3 id through `frsGuid`, never by name. `DELETE /api/v2/mapping/<id>` → 200, only when the mapping's `tasks[]` is empty (resolve it through `assetFrsGuid`). `/api/v2/dtemplate/<id>` is the wrong path (404 HTML), and a v3 objects DELETE returned 404. Delete tasks before mappings, with an export backup first.

### L-CDI-054  Tag objects in batches of 50; projects and folders cannot be tagged; imports drop tags
**Kind:** RECIPE · **Proven:** 2026-09-28 · **Evidence:** 189 objects re-tagged after an import and read back
`POST /public/core/v3/TagObjects` with `[{"id":"<frsGuid>","tags":["<tag>"]}, ...]`, at most 50 per call. Read the status of every item (200/201/204/207). Items of type Folder or Project fail ("of type: [Folder]"), so let the project name mark the scope. Imports do not carry tags: re-tag after every import.

### L-CDI-055  Create the project and folder over v3 idempotently and cache their ids per org
**Kind:** RECIPE · **Proven:** 2026-09-29 · **Evidence:** folder create 201; repeated builds found and reused it
Find the project with `GET /public/core/v3/objects?q=type=='PROJECT'`, or create it with `POST /public/core/v3/projects {"name","description"}` (200/201 → id). List folders with `q=type=='FOLDER' and location=='<project>'`, and create one with `POST /public/core/v3/projects/<projectId>/folders {"name","description"}`. Cache the ids per org: ids from one org must never be used in another.

### L-CDI-057  Start jobs by v2 taskId; taskFederatedId works only with the task's own federated id in the same org
**Kind:** GOTCHA · **Proven:** 2026-09-22 · **Evidence:** `taskFederatedId` runs appeared as REST_API_V2 in the activity log in one org (2026-09-22); 403 REPO_19035 when another value was sent (2026-08-19)
The v2 `taskId` with `taskType:"MTT"` always worked. `{"taskFederatedId":"<federated id>","taskType":"MTT"}` also started runs in one org, with the federated id resolved from the task in that org. Sending another value (an id from a different plane or org) returned `403 REPO_19035` or `UI_13429`. The exact cause of the August failure was not isolated. Prefer `taskId`.

### L-CDI-058  UI_13404, UI_13429 and REPO_19035 on job start: wrong object type, stale id or another org
**Kind:** ERROR · **Proven:** 2026-09-22 · **Evidence:** the recorded 403 answers for 5 taskType variants and several object types
- `POST /api/v2/job` with a Database Ingestion or Mass Ingestion task, a profile, or an undeployed object gives `403 UI_13404` "Object identifier is not valid or missing" for every `taskType`. Run those through their own services.
- A federated id that no longer resolves gives `403 UI_13429`.
- `GET /api/v2/mttask/<id>` on an id that is not a mapping task, or that belongs to another org, gives `403 REPO_19035` "task does not exist".

### L-CDI-059  Poll the activity log by runId until the run is terminal
**Kind:** RECIPE · **Proven:** 2026-09-28 · **Evidence:** the standard run path of every lane since 2026-09-23; a false failure when rows[0] was used instead
After `POST /api/v2/job`, poll `GET /api/v2/activity/activityLog?taskId=<id>&rowLimit=1` every 5–10 s until `row[0].runId == runId` and `endTime` is set. State 1 = SUCCESS, 2 = WARNING (rows rejected), 3 = FAILED. Keep `successTargetRows`, `failedTargetRows`, `errorMsg` and the activity id. Time out at about 60 min per task and 2 h per taskflow. Never take the first row blindly: it can be the previous run.

### L-CDI-060  A WARNING run that wrote 0 rows is a failure
**Kind:** GOTCHA · **Proven:** 2026-09-28 · **Evidence:** orchestration code mapping state 2 + 0 rows to FAILED; a WARNING with 509/510 rows stayed non-blocking
State 2 (WARNING) means some rows were rejected. If `successTargetRows` is also 0, nothing was written: count it as FAILED in orchestration and alerts. A WARNING that wrote rows (e.g. one rejected SaaS row) can stay non-blocking.

### L-CDI-062  The activity monitor says what is running and which child step it is on
**Kind:** ROUTE · **Proven:** 2026-09-25 · **Evidence:** used before every lane start; a derived gauge read 17 while the monitor had 0 rows
`GET /api/v2/activity/activityMonitor` (add `?details=true` for taskflows) lists running jobs with `taskName`, `taskId`/`objectId` and `subTaskName` or `currentTaskName`. 0 rows means nothing is running. Use it before starting a task that may already be running, to adopt a schedule-started taskflow, and to show live progress. Do not trust derived "jobs running" gauges.

### L-CDI-063  US pods stamp local UTC-4 times with a Z; use the *Utc fields
**Kind:** GOTCHA · **Proven:** 2026-09-28 · **Evidence:** a 4-hour offset between `startTime` and `startTimeUtc` on two pods
On the US pods seen, v2 `createTime`/`startTime` and activity-log `startTime`/`endTime` are pod-local (UTC-4) but labelled `Z`. Use `startTimeUtc`/`endTimeUtc` for elapsed-time, freshness and completion logic. Schedules take both `startTime` (pod-local) and `startTimeUTC` (L-CDI-073).

### L-CDI-064  The agent's DIS session logs are exact run evidence
**Kind:** PROCESS · **Proven:** 2026-09-28 · **Evidence:** a 14/14 exact landing parity table and 12/12 and 5/5 lane parity built from these logs
Each mapping-task run writes `<agent_home>/apps/Data_Integration_Server/logs/s_mtt_<taskId>_<n>.log`:
- `TM_6014` marks the session start;
- `PETL_24012` marks a successful end and `PETL_24013` a failure;
- `WRT_8036 Target: <table>` names the target and `Applied Rows [N]` gives the count;
- `DATABASENAME=` gives the source database;
- "Session run completed successfully" is the verdict.

Parsing them gives exact timing, concurrency and row evidence without API calls.

### L-CDI-065  Before re-arming a job paused for an IDMC run, confirm nothing is running
**Kind:** PROCESS · **Proven:** 2026-07-04 · **Evidence:** an orphaned pause found; the activity monitor at 0 and no DTM process confirmed
Jobs paused to avoid colliding with an IDMC run are easily orphaned. Before un-pausing, confirm the activity monitor shows 0 running jobs and no `pmdtm`/DTM process is alive on the agent host. Run the re-armed job once by hand, keep backups of the crontab and manifests, and update baseline counts so drift checks do not false-alarm.

### L-CDI-068  The managed Job Management MCP server wraps run, status and stop
**Kind:** ROUTE · **Documented:** 2026-07-25 · **Evidence:** Documented, not live-proven: reference corpus action list; REST equivalents proven
The managed Job Management MCP server exposes `run_mapping_task` (wraps `POST /api/v2/job`), `get_job_status` (wraps the activity log, one job) and `stop_running_job`. It can also run taskflows and replications. REST is equivalent and returns full history. No managed MCP verb authors a mapping or a mapping task.

### L-CDI-084  Idempotent task upsert: look up by name, update in place with id and frsGuid
**Kind:** RECIPE · **Proven:** 2026-09-25 · **Evidence:** repeated generator runs rewrote the same tasks and never duplicated one
Cache `{name: id}` from `GET /api/v2/task?type=MTT` once per run. If the name exists: `GET /api/v2/mttask/<id>`, set `body.id=<id>` and `body.frsGuid=<current frsGuid>`, and `POST /api/v2/mttask/<id>`. Otherwise `POST /api/v2/mttask`, record the new id, and move and tag the new object. Require 200, and fail with the first 300 characters of any other answer.

### L-CDI-085  Rewrite logical dataset names to physical ones per mode (live or shadow)
**Kind:** RECIPE · **Proven:** 2026-09-23 · **Evidence:** a shadow build produced a full parallel chain for parity tests
Write mapping SQL against logical dataset names (`raw.`, `staging.`, `<gold>.`). At build time rewrite each one to `` `<cloud-project>`.<physical>. `` with a regex that skips names already qualified: `(?<![\w`.])<logical>\.`. A shadow mode maps every logical dataset to a shadow twin, so the whole chain can be built, run and compared without touching what apps read. Keep one mapping dict per mode.

### L-CDI-086  Generate the STRING raw layer from column metadata; long-text tables get a view instead
**Kind:** RECIPE · **Proven:** 2026-09-26 · **Evidence:** raw-layer text byte-identical to the previous engine's; long-text parity checks passed
For each landed table, generate a SELECT over the typed landing table:
- `JSON_VALUE(col)` for JSON columns;
- `FORMAT('%.<scale>f', col)` for scaled numerics;
- `FORMAT_TIMESTAMP('%Y-%m-%d %H:%M:%S+00:00', col, 'UTC')` for timestamps (the `%E6S` form when microseconds are non-zero);
- `CAST(col AS STRING)` otherwise.

Tables with long-text columns do not get a raw task, because an IDMC STRING write would re-cut the text. Their raw object is a view with the same SELECT, recreated by DDL each cycle, after deleting any TABLE standing in its place.

### L-CDI-087  Guards around a cycle: long-text capacity before, truncation suspects after
**Kind:** PROCESS · **Proven:** 2026-09-27 · **Evidence:** the guard found a 354-character column, which moved to the JSON path; a forced full run verified 49 rows longer than 255 intact
- **Before landing:** query the source for the longest value of each long-text column, and abort if any exceeds the landing capacity (32,000 characters for JSON-typed BigQuery columns).
- **After the full cycle:** compute `max(length(col))` for STRING columns and `max(length(JSON_VALUE(col)))` for JSON columns of every IDMC-written table. Exactly 255 or exactly 32,000 means probable truncation, so fail the cycle.
- **When the guard trips on a column that grew:** move it to the JSON landing path, make the next layer a view, and delete the redundant copy task.

### L-CDI-088  Truncate the targets of 0-row successes yourself, stage by stage
**Kind:** GOTCHA · **Proven:** 2026-09-24 · **Evidence:** a table whose source dropped to 0 rows kept its stale rows; the guard's log showed the zero-row truncates
With the BigQuery V2 target in Bulk mode and "Write truncate", a task whose source returns 0 rows does not touch the target, so a table that drops from N rows to 0 keeps its stale rows. After each stage, run `TRUNCATE TABLE` on the target of every task that SUCCEEDED writing 0 rows. Go stage by stage (landing, then raw) so an emptied upstream cascades.

### L-CDI-089  Reverse-ETL into PostgreSQL is a template task with an upsert target
**Kind:** OVERTURNED · **Proven:** 2026-09-25 · **Evidence:** first run SUCCESS (about 31,000 golden records); the reverse-ETL ran in every customer and full lane; the older in-app fan-out retired
Clone the template task. `$Source$` = the warehouse connection with `customQuery 'SELECT ... QUALIFY ROW_NUMBER() OVER (PARTITION BY <key> ORDER BY <built_at> DESC, <id>) = 1'`. `$Target$`: `targetConnectionId=<pgConnId>`, `targetObject = objectName = '<schema>/TABLE/<table>'`, labels `'<table>'`, pop `newObjectName`, `newObject=false`, empty `tgtObjectAttributes`/`runtimeAttrs`/`oprRuntimeAttrs`, `operationType='Upsert'`, `targetUpdateColumns=[<key>]`, `truncateTarget=false`. Write into a new schema beside the operational tables, and schedule it after the forward cycle.

### L-CDI-090  SaaS upsert task: columns aliased to API names, Upsert on an external id
**Kind:** RECIPE · **Proven:** 2026-09-25 · **Evidence:** the SaaS block ran last in every full lane; linked children verified by count
`$Source$`: the warehouse connection plus a `customQuery` whose column aliases are the SaaS API field names. `$Target$`: `targetConnectionId=<sfConnId>`, `targetObject = objectName =` labels `= '<SObject>'`, pop `newObjectName`, `newObject=false`, `operationType='Upsert'`, `targetUpdateColumns=['<ExtId__c>']`, `truncateTarget=false`. If the self-hosted agent's connector does not work, set the task-level `runtimeEnvironmentId` to a hosted runtime and drop `agentId`. Order the tasks parent before child.

### L-CDI-091  Guard every CRM upsert: count gate, test-identity exclusion, retention window
**Kind:** PROCESS · **Proven:** 2026-09-28 · **Evidence:** the batch sync stopped adding test rows; the target stayed within storage until real-time test traffic filled it
Append to every CRM/SaaS upsert query:
- **a count gate:** push nothing unless this cycle's count of valid golden records is at least 80% of what the target already holds, so a broken upstream load never overwrites good CRM data;
- **a test-identity exclusion** that matches the BI layer's test filter;
- **a retention window** for child objects when the target's storage is small.

Filter test identities at the source query: deleting them in the target is pointless while scheduled upserts re-create them.

### L-CDI-092  Incremental append: insert only new ids with an anti-join and a dedupe
**Kind:** RECIPE · **Proven:** 2026-09-27 · **Evidence:** idempotent loads verified on a 5-minute feed and on hourly snapshot tasks
For append-only feeds: `operationType='Insert'`, `oprRuntimeAttrs.writeDisposition='Write append'`, `newObject=false`, and a `customQuery` that LEFT JOINs the target over a lookback window and keeps only ids not already present, deduplicated with `QUALIFY ROW_NUMBER() OVER (PARTITION BY <id> ORDER BY <ts>) = 1`. Re-runs and overlapping schedules never duplicate rows.

### L-CDI-093  Make full reloads incremental with a watermark MERGE
**Kind:** RECIPE · **Proven:** 2026-07-08 · **Evidence:** proven on a development table (first run backfilled 266,643 rows, later runs processed the delta)
Replace truncate-and-reload SQL with a watermark store: read the watermark, MERGE rows whose change timestamp is later than watermark − lookback, then write back `MAX(change timestamp)`. The first run backfills and later runs process only the delta. It works for SQL run by a task's `customQuery` as well as for warehouse-native jobs.

### L-CDI-094  Evidence tasks: append-only snapshots, a once-per-day guard, and a run log written by load jobs
**Kind:** RECIPE · **Proven:** 2026-09-29 · **Evidence:** hourly snapshot runs wrote once per UTC day; run-log history queried by consoles and rehydrated after restarts; a readiness snapshot kept on its own task during a consolidation swap, with the double-run idempotency check part of the parity method (2026-09-29)
- **Daily snapshot:** a Write-append task whose SQL ends in `WHERE NOT EXISTS (SELECT 1 FROM <target> d WHERE d.snapshot_date = CURRENT_DATE())`. An hourly schedule then writes once per UTC day.
- **Run log:** after each lane, append one row per task run (`run_id, task, kind, target, rows_written, status, error, started_at, ended_at`) with a **load job**, not streaming, so rows are queryable and correctable at once. A failed log write must never mask the pipeline result.
- **Keep append snapshots out of event-driven consolidated mappings:** an append-mode snapshot target folded into a multi-target mapping inherits that mapping's cadence, so in a per-event lane every event appends another snapshot row. Leave append snapshots in their own task on their own schedule (with the once-per-day guard), consolidate only truncate-loaded targets into event-driven mappings, check every target's write disposition in the swap spec, and run the new mapping twice in a row: the second run must not change row counts.

### L-CDI-095  Flat-file ingest task: srcFFAttrs, file name in the object, header read at run time
**Kind:** RECIPE · **Proven:** 2026-09-27 · **Evidence:** the file lane landed every rehearsed file
Clone a proven flat-file landing task. Set `$Source$.srcFFAttrs = {"@type":"flatFileAttrs","delimiter":",","textQualifier":"\"","escapeChar":"","headerLineNo":1,"firstDataRow":2,"consecutiveDelimiterAsOne":false}`, put the file name in `extendedObject.object`/`objects[].name` and `label`, and set `fetchMode:"RUNTIME"` on `$Source$` and `$Target$` so the columns come from the file header at run time.

### L-CDI-096  The plan file is the contract with the orchestrator; keep one per org
**Kind:** PROCESS · **Proven:** 2026-09-29 · **Evidence:** three copies drifted; one held the previous org's ids after a migration
The generator writes `{"mode","landing":[{name,id,target,pg_table,chunked,chunk_capacity}],"raw":[...],"raw_views":[{target,sql}],"medallion":[{name,id,target,kind,reads}],"views":[{name,target,ddl}]}`. Ids are v2 task ids. A partial build (`--only`) must not overwrite it. Keep one plan per org, and treat copies baked into images or copied to other hosts as generated from it.

### L-CDI-097  Hard-coded ids and hosts in builders go stale after an org move
**Kind:** GOTCHA · **Proven:** 2026-09-29 · **Evidence:** builders still held the previous org's template, connection and runtime ids; one controller image had 72 ids baked in
Resolve per-org ids (template task, connections, runtime environment, project and folder) by name inside the target org at start-up. Derive hosts from the login answer: the pod base comes from `serverUrl`/`baseApiUrl`, and the CAI host is `https://<pod>-cai.<rest of the pod host>`. A string replace of one pod literal silently stops working when the org moves pods.

### L-CDI-098  Land a second schema into its own dataset; run large cross-cloud full reloads daily
**Kind:** DECISION · **Proven:** 2026-09-24 · **Evidence:** first run SUCCESS (127,694 / 75,071 / 36,836 rows); about 240k rows per full reload
When adding tables from a second schema whose names collide with tables already landed, land them into their own dataset (or with a prefix) using `<schema>/TABLE/<table>`. Full reloads of large tables across clouds cost egress on every run, so give them a daily schedule rather than an hourly lane unless a consumer needs fresher data.

### L-CDI-099  dbt-to-IDMC staged method and the one-technique mart migration
**Kind:** PROCESS · **Proven:** 2026-08-19 · **Evidence:** a DQ gate 21/21 byte-identical; 16/16 marts at parity 0/0 with identical `SHOW CREATE`
1. Rebuild every mart from the old tool's **compiled** SQL into a scratch schema with zero changes, and require a byte-identical match of the existing DQ gate. That proves the tool was only an orchestrator, and makes the per-mart SQL the spec.
2. Migrate each mart the same way: a Query source with the mart's SELECT verbatim, executed by the warehouse; the same table name in a scratch schema as target; Insert with a manual TRUNCATE per run; poll by `runId`; exact parity plus `SHOW CREATE`.
3. Keep the legacy pipeline live until IDMC produces the tables.

### L-CDI-100  Normalize drifting source schemas once, in a schema-adaptive landing view
**Kind:** WORKAROUND · **Proven:** 2026-08-18 · **Evidence:** 21 tasks successful after the change; an old-schema test row aliased correctly, then removed
When two producers write the same table under different column names (e.g. during concurrent redeploys of two app versions), make the landing view schema-adaptive. Introspect the physical columns, and re-create the view adding `<physical> AS <canonical>` for each missing canonical name. Downstream mappings keep referencing canonical names.

### L-CDI-101  Recover lost transform SQL from the warehouse job history
**Kind:** RECIPE · **Proven:** 2026-07-04 · **Evidence:** 14 build statements recovered read-only; 12/14 exact parity (2 were stale one-off snapshots)
If the SQL that built some marts is lost, search the warehouse's query/job history (e.g. BigQuery `INFORMATION_SCHEMA` jobs) for jobs whose destination table matches each mart. Recover the statement and validate it against the current table. That becomes the spec for new tasks or mappings.

### L-CDI-102  External runner: dependency waves, single-writer lock, guards and one lineage row per run
**Kind:** PROCESS · **Proven:** 2026-09-23 · **Evidence:** the first live cycle 46/46 SUCCESS in 13 min; about 1.48M rows per cycle
Before linear taskflows owned execution, a runner executed each cycle's tasks from outside IDMC:
- dependency waves (landing, then raw, then medallion), in parallel within a wave;
- a single-writer lock so overlapping cron runs never interleave;
- a long-text capacity guard and a 255-character truncation guard;
- one lineage row per run in a runs table.

Every task still ran in IDMC through `POST /api/v2/job`. Measured: 46 tasks and about 1.5M rows in 12–13 min per cycle. Newer evidence: L-CDI-294.

### L-CDI-103  Informatica expression idioms are not SQL
**Kind:** RECIPE · **Documented:** 2026-07-26 · **Evidence:** Documented, not live-proven: a third-party reference implementation; not live-probed; function availability across licence tiers unverified
- Conditionals: `IIF(ISNULL(x), 'INSERT', x)`. `IIF` is the ternary and `DECODE` the switch. An empty string is not NULL.
- Current time: `SYSTIMESTAMP()`.
- Concatenation: `||`. A NULL operand makes the result NULL.
- Date math: `DATEADD(DAY, -1, $$LOAD_DATE)`. Date key: `TO_NUMBER(TO_CHAR(d,'YYYYMMDD'))`.
- `$$NAME` is a runtime parameter from a parameter set; `$NAME` is a system variable.

Never hardcode dates, paths or connection names.

### L-CDI-104  Proven Expression cleanse formulas for name, email, phone, codes and a validity flag
**Kind:** RECIPE · **Proven:** 2026-10-03 · **Evidence:** 52 rows transformed; changed-value counts per column verified; the validity flag exactly on the 4 malformed emails; the particle defect reproduced on a first probe run and disappeared with anchored, longest-first alternatives (2026-10-03)
- Name: plain `INITCAP(LTRIM(RTRIM(REG_REPLACE(full_name,' +',' '))))` lower-cases deliberate internal capitals (McDonald -> Mcdonald, MacArthur -> Macarthur) and capitalises lower-case particles (de la Cruz -> De La Cruz), so it fights any other writer that keeps them. A per-word rule works with VARIABLE ports evaluated in order before the output port: collapse whitespace with `REG_REPLACE`, count words, extract word i with `REG_EXTRACT(v_nm, '^(\S+ ){i-1}(\S+).*$', 2)`, keep the typed word when it matches `^\p{Lu}\p{Ll}+(\p{Lu}\p{Ll}{2,}){1,2}$` (Unicode classes are accepted), keep a typed lower-case particle when it is neither the first nor the last word, otherwise `INITCAP` the word; join with `||` and fall back to `INITCAP` for names longer than the number of word ports (8). Anchor `REG_MATCH` alternations and put the longest alternatives first: an unanchored `(de|der|...)` took the first branch for 'der' and failed the whole-string match, so 'van der' came out 'van Der'; write `^(della|del|der|das|dos|den|da|de|di|do|du|la|le|van|von|ter|ten|bin|ibn|al|el)$`. Use the same rule in every writer of the name (L-CAI-086), and prove it with a scratch probe mapping that writes only a parity table, fed by a SQL source that UNIONs fixed test names with every live value, before swapping the live mapping (same GUID, OVERWRITE import).
- Email: `LOWER(LTRIM(RTRIM(email)))`.
- Phone to E.164: nested `IIF` over `REG_REPLACE(phone,'[^0-9]','')`. 10 digits → `'+1'||d`; 11 digits starting with 1 → `'+'||d`; else `''`. Emit this canonical form on the first run: a format dimension can read green over non-canonical stored values (L-DQ-105).
- Canonical code: `DECODE(LOWER(TRIM(tier)),'gold','Gold','silver','Silver','bronze','Bronze','Unknown')`.
- Flag: `IIF(REG_MATCH(email_clean,'^[a-z0-9._%+-]+@[a-z0-9.-]+[.][a-z][a-z]+$'),'1','0')`. Newer evidence: L-DQ-161.

### L-CDI-105  Expression OUTPUT ports cannot reference other OUTPUT ports
**Kind:** GOTCHA · **Proven:** 2026-09-29 · **Evidence:** consolidated-mapping build notes
In an Expression transformation, an OUTPUT port's expression cannot use another OUTPUT port: put intermediate values in VARIABLE ports. To put an apostrophe inside a string literal, concatenate `CHR(39)` (`'...' || CHR(39) || '...'`).

### L-CDI-106  One source feeding both sides of a Joiner hangs with no error
**Kind:** GOTCHA · **Proven:** 2026-09-29 · **Evidence:** a hung parity run had to be stopped; the rebuilt mapping passed
Never let one source feed a Joiner's master and also (directly or downstream) its detail: the session hangs forever with no error. When two branches of the same pipeline must meet in a Joiner, set "Sorted Input" on the Joiner and put Sorters on both branches. Without that, the import itself fails ("Choose sorted input for <JNR> to join data from the same source").

### L-CDI-107  SCD Type 2 in seven steps, with a fixed-order change hash
**Kind:** RECIPE · **Documented:** 2026-07-26 · **Evidence:** Documented, not live-proven: a third-party reference implementation; not live-probed
1. Read the increment by run id, not by date.
2. Look up the dimension `WHERE IS_CURRENT = TRUE` (surrogate key, stored hash, start date).
3. `NEW_HASH = MD5(<attributes in a fixed order>)`, never including a load timestamp, and never reordering the fields.
4. Filter `ISNULL(LKP_SK) OR NEW_HASH != LKP_RECORD_HASH`.
5. Route NEW vs CHANGED.
6. Update the old version (`EFF_END_DATE = DATEADD(DAY,-1,$$LOAD_DATE)`, `IS_CURRENT = FALSE`).
7. Insert the new version (`EFF_START_DATE = $$LOAD_DATE`, `IS_CURRENT = TRUE`, `RECORD_HASH`, the run id).

Make expire-then-insert atomic.

### L-CDI-108  Never drop a row silently: a structured reject sink and a reject-rate breaker
**Kind:** RECIPE · **Documented:** 2026-07-26 · **Evidence:** Documented, not live-proven: a third-party reference implementation; not live-probed
- **Reject sink:** every failed row goes to an ERROR table with the run id, source entity, business key, a reason of the form `<rule id> | <code> | <field>='<value>'`, and the full raw record, so it can be reprocessed.
- **Breaker:** fail the quality step and abort the flow when the reject rate exceeds a threshold (e.g. 10%).
- **Fail vs flag:** choose per rule.
- **Dedup:** deduplicate facts with a Lookup on the natural key, so re-runs never double rows.
- **Domains:** keep them in reference tables, not hard-coded lists.

### L-CDI-109  Layering: RAW append-only, CURATED, ERROR, stamped in the ingest mapping
**Kind:** DECISION · **Documented:** 2026-07-26 · **Evidence:** Documented, not live-proven: a third-party reference implementation; not live-probed
RAW is append-only (an immutable audit of every ingest, which lets you reprocess without re-fetching the source), CURATED is modelled and mutable, and ERROR holds rejects. Stamp every RAW row with the run id, source file name and load timestamp inside the ingest mapping itself, not afterwards.

### L-CDI-111  Transformation and object naming convention
**Kind:** RECIPE · **Documented:** 2026-07-26 · **Evidence:** Documented, not live-proven: reference convention; used consistently by a generator on 2026-09-29
- Transformations: `EXP_` expression, `LKP_` lookup (it also marks a round-trip hotspot), `FIL_` filter (pair each with a reject path), `RTR_` router (prefer it over two filters), `JNR_`, `AGG_`, `SRT_`, `SRC_`, `TGT_`.
- Objects: `m_` mapping, `mt_` mapping task, `wf_`/`tf_` taskflow, kept 1:1 and same-named.

With a generator, the spec file is the reviewable artifact, and an export's IMF is the read-back.

### L-CDI-112  Decide where logic lives; SQL in a copy-data task is CDI SQL, not CDQ
**Kind:** DECISION · **Proven:** 2026-09-28 · **Evidence:** an architecture review corrected labels; the copy-data design ran all cleanse and DQ as warehouse SQL
Putting all logic in IDMC makes rules reusable, visible in lineage and editable by non-SQL users, at a pushdown cost. Keeping logic as warehouse SQL fits a headless build. Neither is an Informatica requirement: choose deliberately and write it down. When cleanse, dedup or DQ logic is warehouse SQL inside mapping tasks, describe it as CDI SQL, not as Cloud Data Quality, and say which steps are genuine CDQ assets.

### L-CDI-113  Define each shared metric once and point every task at it
**Kind:** DECISION · **Proven:** 2026-09-27 · **Evidence:** two sample records went from three different values to one value everywhere
When the same metric (e.g. lifetime value) is computed separately by a CRM sync, a real-time process payload and an app API, the numbers drift apart. Define it once as a warehouse view with an explicit formula, and make every mapping task and consumer read it.

### L-CDI-114  As few mappings as possible: never one task per table per stage
**Kind:** LAW · **Proven:** 2026-09-29 · **Evidence:** 159 tasks on one template, each with ~20 s fixed cost; an 11-mapping build replaced 40 of them
Group same-shaped loads into one parameterized object: a Dynamic Mapping Task with one job per table, or one mapping with several pipelines. Read each source table once and write every consumer from the same pipeline. Use a dependency map (reads, writes, dependencies per task) to pick merge groups: stages with no internal dependency merge first, and ordered chains (e.g. a parent-child SaaS chain) stay intact.

### L-CDI-115  Copy-data template tasks are not real mappings; audit for the sprawl patterns
**Kind:** GOTCHA · **Proven:** 2026-09-29 · **Evidence:** a read-only audit parsed every task JSON in an export: 159/159 on the template, 0 real mappings
Tasks on `dsst__copy_data_new_tgt` keep all their logic in `customQuery` strings. An org can hold hundreds of tasks and zero designer mappings: empty two-box canvases, logic invisible to lineage and CLAIRE. Audit for:
- land and raw as two tasks per table;
- two pipelines reading the same source;
- subset lanes that duplicate the full lane;
- unscheduled shadow copies;
- read-back chains before child upserts. Newer evidence: L-MIG-094.

### L-CDI-116  Anti-pattern: a second task per table that only casts to STRING
**Kind:** GOTCHA · **Proven:** 2026-09-29 · **Evidence:** 10 tables × 2 tasks in an audited design
A raw-layer task that only CASTs every column to STRING doubles the task count, and with it the fixed cost and the jobs. Do the STRING projection in an Expression inside the ingest pipeline (one read, two writes), or as a view.

### L-CDI-118  Anti-pattern: reading SaaS record Ids back before child upserts builds a long serial chain
**Kind:** GOTCHA · **Proven:** 2026-09-29 · **Evidence:** a DAG model put a 62-task lane in 15 stages with an 11-task SaaS chain as the floor
Upserting parents, reading their record Ids back into the warehouse (SObject → `sf_ids_<object>`, Write truncate) and joining them into child upserts makes a chain that must run strictly in order. It set the floor of the whole lane. Upsert children with external-ID relationship fields (`<Parent>__r.<Parent_Ext_Id__c>`) instead, which removes the read-back tasks.

### L-CDI-119  Consolidation: 11 mappings replaced 40 tasks; lanes of 16, 19 and 62 tasks became 7, 11 and 23 jobs
**Kind:** PERF · **Proven:** 2026-10-01 · **Evidence:** measured runs per mapping and per replaced task; lane wall-clock before the swap, after it and after the poll-interval re-import (2026-09-30); 711 job runs over 24 h with 2 failures and per-mapping medians from the activity log (2026-10-01)
Each consolidated mapping ran in 28–87 s, while each task it replaced ran in 8–60 s, about 20 s of it fixed. For example, one ingest mapping (85 s) replaced 6 raw tasks of 34–38 s each. Fewer tasks also meant fewer jobs against the monthly cap and a shorter critical path. In production, after the live lanes moved to consolidated mappings (one ingest per source group, one golden-record mapping with many targets, key-sync or insert/update writers) and the 1 s BigQuery writer poll interval was added to every generated target (L-CDI-200): the per-record lane went from 16 tasks (98-108 s) to 7 jobs (84-96 s average, 82 s fastest), the activity lane from 19 tasks to 11 (about 145-159 s), and the full refresh from 62 tasks (about 20 min) to 23 jobs (258-358 s; 6.7 min before the poll-interval fix). Jobs per full-lane run fell from 63 to 24 against the monthly cap. A 59-transformation golden-record mapping with 11 targets ran a median 65 s (55-79 s, 27 of 27 successful); ingest mappings that read a source once and write several targets ran a median 24-41 s; single-target marts 8-27 s. Without the poll-interval setting the consolidated mappings were slower than expected, because each BigQuery target paid up to about 9 s of polling. Each step was accepted only with parity 0/0 against the old outputs (L-CDI-141) plus an independent check, and the replaced tasks were deleted only after 24 h green (L-CDI-142). The same mappings also ran 1.6-3x faster after the agent host went from 4 to 8 vCPU, but the poll-interval fix landed the same day, so the two effects are not separable.

### L-CDI-120  The consolidation plan shape: about 160 tasks to about 11 mappings, 10 taskflows to 3
**Kind:** PROCESS · **Proven:** 2026-09-29 · **Evidence:** an audit plan; the first 11 mappings built and parity-green; the remaining folds were planned
The target design:
- a parameterized ingest (a Dynamic Mapping Task, or a few multi-pipeline mappings) that reads each source once and writes typed landing, a STRING layer via an Expression, and a second store;
- a golden-record mapping (cleanse → lookup/dedupe → golden → reverse-ETL targets);
- a DQ mapping (rule checks → Router → Aggregator scorecard);
- facts and marts mappings with Joiners and Aggregators;
- a SaaS sync mapping with targets in load order and external-ID relationships;
- a file-ingest mapping (validation Expression → Router: valid → ready and post, invalid → quarantine).

Three taskflows: batch, a second application, files. Keep the work in the warehouse with full pushdown where possible.

### L-CDI-121  Every mapping task pays about 20 s of fixed time
**Kind:** PERF · **Proven:** 2026-09-29 · **Evidence:** a 62-task linear lane took 21.6–24.5 min for about 53k rows; the uniform 20 s/task model matched the session timings
Each task pays roughly 14 s of DTM startup plus about 5 s of cloud dispatch before it moves any data. A linear taskflow's duration is therefore about tasks × 20 s. The fixes are fewer tasks (consolidation) or concurrency, not larger machines.

### L-CDI-123  Model a lane as a read/write dependency DAG
**Kind:** PROCESS · **Proven:** 2026-09-29 · **Evidence:** 0 unresolved tasks; 0 dependency violations against the executor
- **Reads:** its source object, or every `dataset.table` in its SQL with warehouse views expanded to base tables through `INFORMATION_SCHEMA.VIEWS`.
- **Writes:** its target.
- **Dependencies:** for tasks *i < j* in lane order, *j* depends on *i* on read-after-write, write-after-read or write-after-write of one object.
- **Special cases:** SaaS parent-child chains stay ordered; a task writing outside the warehouse waits for every earlier internal task; an unresolvable task is a barrier.

Stage = longest-path level, and lane order is a valid topological order.

### L-CDI-124  DAG staging at concurrency 4 cut a 62-task lane from about 21 to about 5.5 min
**Kind:** PERF · **Proven:** 2026-09-29 · **Evidence:** a model at 20 s/task and a replay with measured durations (22m25s sequential vs 5m41s at concurrency 4)
A 62-task lane had 15 stages: 20.7 min sequential, 5.3 min at concurrency 4, and 5.0 min at concurrency 8. The floor was an 11-task sequential SaaS chain, so shorten that chain before adding concurrency. A 16-task lane went from about 5.5 to 2.2 min, and a 19-task lane from about 7.4 to 2.3 min (estimates). Lanes that write the same targets must stay mutually exclusive.

### L-CDI-125  Staged fan-out: start each task when its dependencies finish, at most N at once
**Kind:** PROCESS · **Proven:** 2026-09-29 · **Evidence:** a 7-check lane smoke passed with the flag on; 0 dependency violations
The orchestrator starts every task itself (still `POST /api/v2/job`, so everything runs in IDMC) as soon as its dependencies are done, at most N at once, waiting on the first completion. A WARNING does not stop the lane, an error stops new starts, and tasks never started are NOT_RUN: the same verdict as the linear taskflow. Put it behind a flag whose off position restores the linear taskflow without a rebuild, and never switch mid-lane.

### L-CDI-126  Measured staged lanes at concurrency 4 on a shared 4-vCPU host
**Kind:** PERF · **Proven:** 2026-09-29 · **Evidence:** staged runs 16/16 and 19/19 SUCCESS
With at most 4 concurrent task jobs on a 4-vCPU host shared by two agents: a 16-task lane went from 462 s to 215–279 s, a 19-task lane from 357 s to 240–267 s, and a new record reached the golden table in 93 s instead of about 5 min. Cap concurrency near the host's vCPU count when agents share a host.

### L-CDI-127  Before staging a full lane, add missing reads and keep it exclusive with subset lanes
**Kind:** GOTCHA · **Proven:** 2026-09-29 · **Evidence:** 4 undeclared landing reads through raw views found before the switch
A full lane that shares targets with smaller event lanes must never run at the same time as them. Its declared reads were incomplete (reads through raw views were missing), which would let a task start before its input landed. Fix the declared reads, or add barriers, before staging. If an IDMC schedule starts the full lane, unbind it and let the orchestrator start it inside the slot window.

### L-CDI-128  Event-driven lanes: coalesce, round-robin, guests beside a long lane with per-table conflict locks, priority, quiet window
**Kind:** PROCESS · **Proven:** 2026-09-30 · **Evidence:** Before round-robin one event lane starved the other (2026-09-26); record to golden 76-88 s both solo and beside a full refresh (was up to 1,027 s); later lanes 38/38 and 23/23 tasks ok with guests and retries; a 93-check sandbox suite (side-by-side runs, per-table overlap, caps, soft-fail, drain, blackout) passed before every deploy (2026-09-29/30)
- **Coalesce:** events increment a pending counter per lane instead of starting a run each, and the next run takes all pending events.
- **Gap:** a minimum gap per lane limits starts (0 = start as soon as something is pending).
- **Fairness:** alternate between event lanes.
- **Guests, not one global lock:** a single run lock made a new record wait behind a 20-minute full refresh (1,027 s to its golden record in one case). Admit the critical event lane (new records) as a guest beside a running lane, one guest per lane, and block only real conflicts per table: the same mapping task, two writes of one table, or a read of a table another run is writing. Lower-value event lanes wait for a running full lane, which refreshes the same targets anyway.
- **Priority:** new-record lane > file lane > activity lane > full lane. A lower-priority run starts no task that a waiting higher-priority task conflicts with (bounded wait, for example 600 s), keeps at most concurrency minus 2 tasks while a higher-priority run is active (1 while a new-record run is), and a global cap limits tasks across all runs.
- **Critical path first:** in the new-record lane, tasks that are not on the path to the golden table start only after it lands.
- **Soft-fail side tasks:** a failed DQ side task is reported (the run ends FAILED and alerts) but does not stop activation, reverse-ETL or SaaS tasks; one DQ task's heap OOM had stopped the whole downstream tail.
- **One retry** per task for transient failures only, never for the job-cap error (L-CDI-205).
- **Quiet window:** hold event lanes before a scheduled full run, and block full refreshes in a blackout window (plus 30 min before it).
- **Drain:** while a drain file exists no run starts, so the orchestrator can be recreated between runs; every switch (plan, lanes, guests, blackout) drains, waits for idle, recreates the orchestrator and then runs one catch-up for the events queued meanwhile. Because IDMC refuses a second taskflow that runs the same tasks (REPO_17314), the orchestrator, not IDMC schedules, owns every start.
- **Latency:** a 5 s scheduler tick keeps pickup latency low.

### L-CDI-129  At most about 5 BigQuery readers per mapping on a small shared agent
**Kind:** PERF · **Proven:** 2026-09-29 · **Evidence:** OOMs with 7–8 readers; the splits then ran clean
Each BigQuery source (reader) takes Java heap in the DTM, and the heap is agent-wide, not settable per task. With 7–8 readers in one mapping the DTM died with heap / GC-overhead errors; 6 worked once, and at most 5 (the splitter targets 4) was reliable. Select only the columns a pipeline needs, give STRING reader fields a small precision (256; 4000 made the reader allocate huge row buffers), and split big specs into connected components.

### L-CDI-130  Transient GCS-staging 5001 errors on parallel BigQuery runs
**Kind:** GOTCHA · **Proven:** 2026-07-04 · **Evidence:** rows present despite the error; serial retries cleared it
Launching many BigQuery-staged tasks in parallel produced transient GCS-staging errors (`5001` with 409/404) that cleared on a serial retry. Sometimes the data still landed. Check the target row count before treating a 5001 as a real failure.

### L-CDI-132  Quota breaker: pause lanes on the job-cap error, one probe, one alert per day
**Kind:** RECIPE · **Proven:** 2026-09-28 · **Evidence:** the breaker un-paused by itself when the cap was lifted; 0 new alert mails across later events
After each run, look for "monthly limit" in the run or task errors. If found:
- pause the automatic lanes for a backoff (60 min), recording SKIPPED entries instead of failures;
- after the backoff, let exactly one lane through as a probe: the same error pauses again, a success clears the pause;
- send one alert per 24 h;
- expose the blocked-until time on the health endpoint;
- leave manual starts and relays that are not IDMC jobs ungated;
- re-derive the pause from the run log after a restart.

### L-CDI-133  CDI consumption is metered on compute hours per run, not data volume
**Kind:** DECISION · **Proven:** 2026-07-05 · **Evidence:** a metering analysis (hedged: rates and tiers not re-verified here)
Data Integration consumption is driven by runs × compute time, not by the volume of data moved. Fewer, better-packed mappings reduce metered time as well as job counts. For rates and licensing see the IPU domain.

### L-CDI-134  Cap concurrency near the host's vCPU count and select only the agent services you need
**Kind:** PERF · **Proven:** 2026-09-29 · **Evidence:** selecting all services pulled 18 GB of packages in 8 minutes, load 189 on 4 vCPU, swap exhausted; concurrency 8 gained little over 4
On a small host shared by two agents, 4 concurrent task jobs was the working point, and more mostly added contention. The agents contended for CPU, not memory. Give each agent its own OS user and systemd unit with memory limits and CPU/IO weights, add swap for idle JVM pages, and enable only the services and connectors the lanes need. Turn heavy catalog metadata services on only for scans (3.7 GB freed after deselecting them).

### L-CDI-135  Change a task's SQL safely: back up, anchored replace, diff, then switch
**Kind:** RECIPE · **Proven:** 2026-09-28 · **Evidence:** display-text and name-rule changes applied this way, each with a backup; a standalone run with 663 rows succeeded and 0 failed
1. Save the `GET /api/v2/mttask/<id>` JSON, the current `customQuery` as a `.sql` file, and a v3 export of the task (lookup by path → export → zip).
2. GET the task, pop `orgId/createTime/updateTime/createdBy/updatedBy/agentId` and each parameter `id`, and replace the snippet in `$Source$.customQuery` only after asserting it occurs exactly once. Save the new SQL, then POST it back.
3. Diff the old and new SQL results in the warehouse before the live run.
4. Run the task once standalone, then patch the generator.

Undo = POST the saved JSON.

### L-CDI-136  Shadow mode: build the whole chain against shadow datasets first
**Kind:** PROCESS · **Proven:** 2026-09-24 · **Evidence:** a shadow cycle ran 46/46 without touching live views; the cutover followed shadow parity
A generator's shadow mode writes every layer to shadow datasets (typed landing, raw, staging, gold) from shadow source views, as unscheduled `_shadow` tasks. Keep the shadow source views in their **own** schema, or a shadow build can silently redefine the views the live tasks read. Run it, compare it with the live outputs or a reference build, cut over only when clean, and delete the shadow objects afterwards.

### L-CDI-137  Parity SQL: counts plus two-way EXCEPT DISTINCT on JSON-serialized rows
**Kind:** RECIPE · **Proven:** 2026-09-23 · **Evidence:** "all identical" or per-table diff counts drove every cutover decision
For each table pair:
- compare `count(*)` on both sides;
- compare `count(*) FROM (SELECT to_json_string(struct(<common cols>)) FROM a EXCEPT DISTINCT SELECT ... FROM b)` in both directions;
- for duplicates, compare multisets: `GROUP BY` the JSON string with `count(*)`;
- exclude run-time columns (`run_at, ingested_at, run_id, loaded_at, computed_at, refreshed_at, ...`);
- for a mismatch, diff per column on the join key, with two sample rows for the first differing column.

### L-CDI-138  Logic parity and frozen parity give both engines the same input
**Kind:** RECIPE · **Proven:** 2026-09-23 · **Evidence:** 23/23 outputs row-for-row identical before a cutover
- **Logic parity:** point the shadow raw views at the live raw tables, so the new engine reads exactly what the old one read.
- **Frozen parity:** snapshot the raw tables into a dataset, build a reference with the same SQL (`CREATE OR REPLACE TABLE AS`, in topological order), run the new engine on the snapshot, and compare as multisets.

Frozen parity separates logic differences from data arriving mid-run. Keep text formats byte-identical where consumers parse them (e.g. `%.2f` numerics, ISO timestamps).

### L-CDI-139  Parity for marts that stamp now(): exclude the stamp, check freshness
**Kind:** RECIPE · **Proven:** 2026-08-19 · **Evidence:** parity 0/0 excluding the stamp; the stamp fresh on every row
Marts that set `run_at`/`ingested_at` with `now()` can never reach full-row parity with a live copy. Assert parity on all other columns (0 rows only in A, 0 only in B) and check separately that the timestamp is fresh. For heavy queries over federated or remote views, compute parity in one execution, e.g. `SELECT countIf(cnt != 2) FROM (SELECT ..., count() cnt FROM (<A> UNION ALL <B>) GROUP BY ...)`.

### L-CDI-140  Cross-engine parity fingerprints: normalize, then counts and a keyset hash
**Kind:** RECIPE · **Proven:** 2026-07-04 · **Evidence:** dual-dialect fingerprint SQL used between two warehouses
Compute on both engines `COUNT(*)`, `COUNT(DISTINCT key)` and an order-independent keyset hash: `BIT_XOR(FARM_FINGERPRINT(ARRAY_TO_STRING([...], '|')))` on BigQuery, `CHECKSUM_AGG(CONVERT(bigint, HASHBYTES('SHA2_256', CONCAT_WS('|', ...))))` on T-SQL. The engines hash and render NULL, decimals and dates differently, so normalize first: NULL → '', money to NUMERIC(18,2), dates as ISO UTC, the same TRIM, column order and delimiter.

### L-CDI-141  Consolidation parity: parity-only dataset, original SQL at the same moment, idempotency double run
**Kind:** PROCESS · **Proven:** 2026-09-29 · **Evidence:** 11 mappings: two-way EXCEPT DISTINCT = 0, and run 1 = run 2; a false 0-diff read from stale tables caught (2026-09-29)
Build the new mappings in a separate folder, writing only to a parity dataset, and check at run time that no task target points at a live dataset. Compare each new target with the **original** task SQL run at the same moment (upstream references repointed), using two-way `EXCEPT DISTINCT`. Then run everything twice in stage order and compare run 1 with run 2, run-time columns excluded. Exclude parity datasets and `_v2` names from freshness and health checks meanwhile. Count a parity verdict only from runs that ended in state 1 AND rewrote the compared table: check that each table's `last_modified_time` is at or after the start of the run that should have produced it, record run id, state, start time and the table's last-modified time next to each diff, and treat a missing or older last-modified as 'not tested', never as 'no difference'. A mapping that failed with Java heap OOM on both test runs was reported idempotent and 0-diff because the compare read the tables of an earlier good run; it then failed 3 of 3 live runs.

### L-CDI-142  The swap gate: story suite green, swap in place, plan v2, re-gate, then delete
**Kind:** PROCESS · **Proven:** 2026-09-29 · **Evidence:** a staged swap process with rollback for every step (applied up to the swap packages)
1. The application's end-to-end story suite at 100% on the current stack.
2. Retarget the new mappings to live targets (swap packages, same GUID).
3. Update the taskflows in place.
4. Switch the orchestrator to the new plan.
5. Run the story suite again.
6. Only then delete the old tasks, with an export backup.

Each step has its own rollback: the saved workflow bodies, the old plan file, and the saved mapping packages.

### L-CDI-144  Generate the orchestrator's new plan with a generator that proves coverage and order
**Kind:** RECIPE · **Proven:** 2026-09-29 · **Evidence:** the generator ran sandboxed and emitted a plan, workflows and a report (staged)
Before switching an orchestrator to consolidated mappings, generate its plan from the old plan plus the swap spec. Make the generator exit non-zero unless:
- every replaced task's target is written by a new task;
- every lane's new order is a valid topological order (reads after writers; raw views count as reads of their landing tables);
- every replaced task in a lane has its successor in that lane.

Run it with no network, inside the orchestrator's own image, and ship the plan as a separate file selected by an environment variable.

### L-CDI-145  Build the swap-ready package from the parity spec under the same mapping GUID
**Kind:** RECIPE · **Proven:** 2026-09-29 · **Evidence:** 11 swap packages imported SUCCESSFUL; tasks then showed the live targets
To point a parity-proven generated mapping at live tables, rebuild its package from the same spec:
- set each target object to its live table;
- rewrite parity-dataset references inside query sources to the live datasets;
- keep the mapping GUID;
- assert that no parity reference is left.

Import it with OVERWRITE and re-read the task. POSTing new targets to the task instead is a silent no-op (L-CDI-050).

### L-CDI-148  Delete shadow and parity copies right after the proof
**Kind:** GOTCHA · **Proven:** 2026-09-29 · **Evidence:** 46 unscheduled shadow tasks, duplicate landing tasks and a stray sample pruned (160 → 94 tasks, export backup first)
Unscheduled shadow tasks, duplicate tasks writing an unused dataset, and stray samples stay in the org long after the parity test. They inflate the design, confuse audits and the catalog, and make cleanup risky later. Delete them right after the comparison, with an export backup first.

### L-CDI-149  One writer per org; read back after every write, including rejected tool calls
**Kind:** LAW · **Proven:** 2026-09-28 · **Evidence:** a migration and cutover run by one lead session; 68 repository deletes had landed from a tool call the user rejected mid-run
One lead session is the only one that logs in to each IDMC org and the only importer or publisher. Other sessions work read-only or host-side, coordinating with lease comments, heartbeats and DONE posts with evidence. Announce before any import. Read back after every write: a tool call rejected mid-run can already have executed server-side.

### L-CDI-150  When CAI real time and a CDI batch write the same fields, both apply the same rule
**Kind:** LAW · **Proven:** 2026-09-28 · **Evidence:** a full diff 701/701 rows with 0 changed columns, 12/12 synthetic cases, and 126/127 runs OK after the change
If a real-time CAI process and a scheduled CDI task both write the same fields in a target system, the batch SQL must implement the same transformation rule. Otherwise the batch run minutes later silently undoes the real-time cleansing. When changing the rule, update both, prove the batch change with a full diff against the old SQL plus synthetic cases, and keep an undo of the previous task definition.

### L-CDI-151  Retire or retarget load tasks before turning their target tables into views
**Kind:** GOTCHA · **Proven:** 2026-09-28 · **Evidence:** a 5-minute lane failed on every run until its schedule was really stopped
If you replace a warehouse table with a same-name view (e.g. to switch consumers to a streaming source), every IDMC task still loading that table fails on each run. Stop or retarget the lane first (schedule end, taskflow removal), and keep the old table as a renamed history table for the view to union.

### L-CDI-152  The BigQuery V2 writer cuts every STRING port to 255 characters
**Kind:** GOTCHA · **Proven:** 2026-09-24 · **Evidence:** 585-character values intact in a CSV target and cut in BigQuery; `overriddenFields` 400; every variant tested stayed at 255
Tasks built over parameterized templates typed strings as `string(255)`, and the BigQuery V2 writer silently cut longer values, whatever the target schema. Tested without success: a `varchar(4000)` source view, `allowMaxFieldLength=true`, `retainFieldMetadata=true`, a pre-created `STRING(4000)` column, and Streaming instead of Bulk. Land long text into JSON-typed columns (L-CDI-153).

### L-CDI-153  A pre-created JSON target column carries the full text up to 32,000 characters
**Kind:** OVERTURNED · **Proven:** 2026-09-24 · **Evidence:** byte-exact live checks 176,175/176,175 and 26,067/26,067 rows; shadow and live cycles 46/46
When the pre-created BigQuery target column is typed JSON, IDMC writes the full text as a JSON string scalar up to 32,000 characters; longer values are cut to exactly 32,000. BYTES targets fail with `CMN_1081`, and "Write truncate" keeps the JSON schema across reruns. Read the text with `JSON_VALUE()` in views, fail a cycle on values of exactly 32,000, and serve the next layer as a view, since a STRING write would cut it again.

### L-CDI-154  Bulk + Write truncate needs GCS staging; Streaming mode cannot truncate
**Kind:** GOTCHA · **Proven:** 2026-09-23 · **Evidence:** a second Streaming run doubled a table (33,106 → 66,230); Bulk + truncate cycles were stable afterwards
With the BigQuery V2 target in Streaming mode, truncate is not honoured and a second run appends. For full reloads use `writeMode` Bulk with `writeDisposition` "Write truncate". That needs a GCS staging path on the BigQuery connection, and the connection's service account needs `roles/storage.objectAdmin` on the bucket. A short bucket lifecycle rule (about 2 days) keeps staging files from accumulating.

### L-CDI-155  truncateTarget=true was ignored on some BigQuery targets; use the write disposition
**Kind:** GOTCHA · **Proven:** 2026-07-09 · **Evidence:** gold tables doubled on every run (19 → 38 → 57) while other tasks with the same flag truncated
With BigQuery V2 as the target, `truncateTarget=true` on the task was ignored for some mappings and rows doubled on every run. Set `writeDisposition` "Write truncate" in `oprRuntimeAttrs`, or truncate each target yourself right before its run. If rows double on an Insert-mode mapping, also check the mapping model's `TruncateTable` property: with NO it appends.

### L-CDI-156  Never flip the BigQuery connection to Hybrid mode (4005)
**Kind:** GOTCHA · **Proven:** 2026-07-09 · **Evidence:** the flip returned 200 and then every mapping failed with 4005 "Direct Read + Hybrid unsupported"
Switching a BigQuery V2 connection from Simple to Hybrid mode broke all mappings on it. Keep Simple mode. For JSON columns, declare the fields as STRING instead (L-CDI-039).

### L-CDI-157  Booleans land as 'true'/'false' strings through the copy template
**Kind:** GOTCHA · **Proven:** 2026-09-23 · **Evidence:** observed in landed tables; a JDBC read in a synthesized mapping rendered 't'/'f' (2026-09-29)
Through `dsst__copy_data_new_tgt`, PostgreSQL booleans land in BigQuery as STRING values `'true'`/`'false'`. Cast them in the next layer. A synthesized mapping reading PostgreSQL through JDBC rendered booleans as `'t'`/`'f'` and needed an Expression to match.

### L-CDI-158  Streamed rows sit in the buffer and cannot be changed at once; write ledgers with load jobs
**Kind:** GOTCHA · **Proven:** 2026-09-24 · **Evidence:** first-run row counts needed a delayed backfill; load-job rows were editable immediately
Rows written by BigQuery streaming inserts (e.g. per-run lineage rows) sit in the streaming buffer and cannot be updated or deleted by DML right away. Write such ledgers with load jobs (`load_table_from_json`, `WRITE_APPEND`), or schedule corrections later.

### L-CDI-159  Type fidelity through generated BigQuery mappings: DATE in and out, the decimal(28,9) ceiling, and the lint rules worth enforcing
**Kind:** GOTCHA · **Proven:** 2026-10-03 · **Evidence:** Consolidated-mapping build notes (2026-09-29); a type diagnostic 8/8 rows exact with one TE_7007 overflow; a DATE failure on a draft build fixed with CAST AS TIMESTAMP; the lint (106 rules) found 3 real issues in existing specs (2026-10-03)
Writing a BigQuery DATE column from a synthesized mapping: the native DATE type showed as "unknown", and a `'YYYY-MM-DD'` string failed the Timestamp cast; send a STRING in the form `'YYYY-MM-DD 00:00:00'`. Reading one: a DATE column declared as DATE in a source query that feeds a Salesforce date field failed with 'Unknown native type for field ... Type: DATE'; `CAST(col AS TIMESTAMP)` (midnight) loads the same date. These survived exactly: unicode text, 255+ character strings, empty string versus NULL, embedded newlines, NUMERIC with scale 9, integers above 2^53 and microsecond timestamps. A 29-digit NUMERIC overflows the platform's decimal(28,9) and fails with TE_7007: cap or cast wide numerics in the source query. Encode the known runtime traps as a lint that blocks a build: Expression OUTPUT ports that reference other OUTPUT ports; one source feeding both sides of a Joiner without sorted input; more than about 5 warehouse readers per mapping; DATE and JSON declared types; dangling or duplicate links; non-ASCII characters and '--' comments in custom SQL.

### L-CDI-160  BigQuery query-source temp views: concurrent runs collide on the Temp_View<epoch-ms> name, and failed or stopped runs leave them behind
**Kind:** GOTCHA · **Proven:** 2026-09-30 · **Evidence:** An orphan view dropped after a hung run (2026-09-29); one collision in about 1,717 staged runs at concurrency 4 with 409 and 404 in the two session logs; a catch-up ran 16 of 16 tasks in 113 s and the lanes stayed green after the one-shot retry (2026-09-29/30)
When a mapping with a BigQuery V2 query (custom SQL) source fails or is stopped, the connector's temporary view (`Temp_View<epoch-ms>`, created in the connection's dataset) stays behind. The name comes from a millisecond timestamp, so two DTMs that reach that step in the same millisecond collide: one fails with 409 'Already Exists', and the other's cleanup DELETE gets 404 although it has already written its rows, which stops a staged lane on a run that mostly succeeded. It is rare (1 in about 1,717 task runs at concurrency 4) but appears exactly when you raise concurrency: treat `temp_view[0-9]+` with 409 or 404 as transient and re-run the task once after about 20 s (L-CDI-205; it gets a new timestamp, and a truncate-load is idempotent), optionally with a 1-2 s start jitter between the tasks of one stage; never retry a quota error. List and drop leftover `Temp_View*` views after aborted runs and before catalog rescans: they otherwise pile up, get cataloged and appear in CLAIRE lineage answers (L-CDGC-149).

### L-CDI-161  BigQuery time travel reaches back about 7 days: start snapshot tasks early
**Kind:** GOTCHA · **Proven:** 2026-09-27 · **Evidence:** a partial backfill; days older than the window could not be rebuilt
To backfill a daily snapshot table from history, `FOR SYSTEM_TIME AS OF` reaches back only about 168 hours, and tables recreated in between cannot be read at older times. Start daily snapshot tasks early, in append mode.

### L-CDI-162  PostgreSQL source objects need the <schema>/TABLE/<table> path; a cold catalog is not a blocker
**Kind:** OVERTURNED · **Proven:** 2026-09-23 · **Evidence:** 33,106 rows landed with 0 errors once the path was right; PG statement logging had shown no query reaching the database before
For the native PostgreSQL connector as `$Source$`, the object path is `<schema>/TABLE/<table>` or `<schema>/VIEW/<view>`. `public/<table>` fails with `SDK_APP_COM_20000` "Incorrect list of path is populated with size: 1". Bare names, `public.<table>`, quoted identifiers and `db.schema.table` give "Object(s) [X] not found": a cache-only lookup. With the right path, the adapter resolves the object at run time with no prior UI browse. The connection has no schema parameter.

### L-CDI-163  The PostgreSQL connector truncates text and cannot land jsonb: land from ::text views
**Kind:** GOTCHA · **Proven:** 2026-09-26 · **Evidence:** long-text parity checks passed after the switch
The native PostgreSQL connector types text as `string(255)` and cannot land `jsonb` or `json`. Create a view in a dedicated source schema that selects every column, with `jsonb::text` for the JSON ones, and land from `<schema>/VIEW/<table>` into JSON-typed warehouse columns. Tables without such columns land from `public/TABLE/<table>`. The views are additive and reversible.

### L-CDI-164  Native PostgreSQL connector type limits (enum, json, arrays) need cast views
**Kind:** GOTCHA · **Proven:** 2026-07-26 · **Evidence:** recorded connector errors
The native PostgreSQL connector raised "native type system does not support the data type [<ENUM>]" and "could not identify an equality operator for type json", and skipped array columns. Cast such columns to text in a source view before landing or profiling them.

### L-CDI-165  Target-port NOT NULL flags are baked into a cloned mapping
**Kind:** GOTCHA · **Proven:** 2026-08-19 · **Evidence:** a run failed "Cannot set null to non-nullable column #N"; after a view repoint it ran SUCCESS 52/52
A mapping cloned from one target type carries `notNull` on its target ports regardless of the live target's nullability, and making the target column nullable does not help. Fix it at the source: a view that coalesces nullable text columns (keep keys and timestamps native), with the mapping source repointed to `<schema>/VIEW/<view>`.

### L-CDI-166  Create-new-at-runtime targets in Insert mode append duplicates on re-runs
**Kind:** GOTCHA · **Proven:** 2026-08-19 · **Evidence:** source 52 = target 52 after one run; duplicates on re-runs; write failures cleared after dropping the old tables; re-runs doubled a target 10 -> 20 before the TruncateTable patch, and it stayed at 10 across repeated re-fires and 18 scheduler-fired runs after it (2026-07-09)
A mapping whose target is created at run time, in Insert mode, creates the table on the first run and appends the full row set on every later run. Truncate first, or use an upsert. If a table with an older schema already exists, the run does not rebuild it and hits column mismatches: drop it first. In cloned template packages the mapping's target session property `TruncateTable` (some entries spell it `Truncate Table`) can be NO, which makes every run append its full row set (a re-fired task doubled its target from 10 to 20 rows): patch both spellings to YES in the mapping model and recompute the package checksums before importing; the engine then truncates before load with no external pre-step (L-CDI-155).

### L-CDI-167  An upsert writes every mapped column; protect non-empty values at the target
**Kind:** WORKAROUND · **Proven:** 2026-09-25 · **Evidence:** reverse-ETL moved to IDMC with the "non-empty only" contract kept
An IDMC upsert writes all mapped columns, so an empty source value can blank a populated target field. Where the contract is "only overwrite with non-empty values", enforce it at the target with a `BEFORE UPDATE` trigger that keeps the old value when the new one is empty, or leave those columns out of the source SQL.

### L-CDI-168  Truncate-then-reload flaps to 0 rows for readers mid-run
**Kind:** GOTCHA · **Proven:** 2026-07-09 · **Evidence:** live resampling caught a dimension at 0 rows mid-reload
A mapping that truncates its target and then reloads it non-transactionally leaves a window where readers see 0 rows. For tables read continuously, load a staging table and swap or rename, or reload inside a transaction, and resample during runs to catch it.

### L-CDI-169  A post-only-valid task with truncateTarget=true on a system-of-record table is a wipe risk
**Kind:** GOTCHA · **Proven:** 2026-09-28 · **Evidence:** a flagged configuration on an accounting table (an open risk, not an observed wipe)
A task that posts validated rows into a system-of-record table (e.g. accounts receivable) with `truncateTarget=true` may empty that table on the next run, including a run over an almost-empty file. Use Insert or Upsert without truncate, and make postings idempotent in the database: a `BEFORE INSERT` trigger that skips a row whose business key already exists.

### L-CDI-170  Salesforce targets: API v64+, hosted runtime if needed, parents first, external-ID relationships
**Kind:** RECIPE · **Proven:** 2026-10-03 · **Evidence:** an 11-task SaaS block ran in every full cycle; 642 contacts plus related objects written; 7 lane runs after the one-mapping swap all SUCCESS, Salesforce = SQL for 8 objects (15 to 748 rows each) with 0 missing and 0 mismatches, 0 records created by the test run (2026-10-03)
- Use a Salesforce connection on API version 64 or newer. If the Secure Agent's Salesforce connector misbehaves, run those tasks on a hosted runtime.
- Upsert on external ids, with the source columns aliased to API field names. Checkbox fields need 1/0, and the connector dropped SOAP long fields.
- Order parents before children, and map merged duplicates to the golden survivor's key.
- Prefer child upserts through external-ID relationship fields over Id read-back tasks (L-CDI-118).
- Gate every upsert on DQ volume (L-CDI-091).
- For live counts when both a batch read-back and a real-time path write the CRM, count the read-back plus the real-time upserts newer than the last read-back (the read-back alone missed 19 recent records; L-CAI-113).
- **One mapping can replace the whole chain:** eleven serial Salesforce copy tasks (accounts, account-id read-back, contacts, contact-id read-back, child objects, activities, invoices, a DQ scorecard object) were folded headless into one mapping with eleven flows in the old parent-before-child order, each an Upsert on an external id with nulls not sent, non-bulk, fields mapped by name and the source SQL copied verbatim; edit it by exporting, changing the source customQuery and re-importing OVERWRITE. The Salesforce step took 85-92 s for about 3,100 rows to 11 targets and made about 30-40 counted Salesforce API calls per run (one login per flow, upserts in batches of 200); jobs per lane run fell from 11 (full) or 5 (event lane) to 1, about 175 fewer a day. Parity before the swap: the SQL columns equal the mapping's source ports, target ports and Salesforce fields for every flow; an updates-only test run (created-since = 0 on every object); after the live run Salesforce equals the SQL output for every source key. Keep the old tasks as the rollback path for a week.

### L-CDI-171  JDBC V2 targets ignore truncateTarget: use runtimeAttrs "Pre SQL" (with the space)
**Kind:** GOTCHA · **Proven:** 2026-09-26 · **Evidence:** a landing lane into a MySQL-protocol warehouse ran full reloads this way; a failed source login left a lane's targets empty after the truncate (2026-09-26)
A task writing through JDBC V2 does not honour `truncateTarget`. For a full reload, set the target's `runtimeAttrs` to `{"Pre SQL": "TRUNCATE TABLE <t>"}`; the key needs the space, and `preSQL`/`PreSQL` are silently ignored. The MySQL JDBC jar goes in the agent's `ext/connectors/thirdparty/informatica.jdbc_v2/common`. The Pre SQL runs before the source is read, so a failed read leaves the target empty: see L-CDI-208 before relying on it for objects that downstream readers refresh from.

### L-CDI-172  ClickHouse through JDBC V2: truncate, string precision and UInt64 quirks
**Kind:** GOTCHA · **Proven:** 2026-08-19 · **Evidence:** SUCCESS with 0 rows when truncateTarget was true; clean loads after the casts
- `truncateTarget:true` can report SUCCESS and leave 0 rows. Set it false and run an explicit `TRUNCATE TABLE` before each Insert-mode run.
- ClickHouse `String` reports JDBC precision 0 ("Length/Precision must be > 0"). Cast outputs with `toFixedString(col,N)` in the source query; JDBC V2 strips the padding on write.
- `UInt64` reads as NULL, so cast it with `toInt64`.
- Use the `-shaded` driver jar, with `http_connection_provider=HTTP_URL_CONNECTION` in the URL.

### L-CDI-173  Flat-file connections: CSVFile type, placeholders for empty fields, agent-readable directory
**Kind:** GOTCHA · **Proven:** 2026-09-24 · **Evidence:** the file lane landed every rehearsed file; the cleanse step showed the restored NULLs
- Create flat-file connections with type `CSVFile`; the native `FLATFILE` type gave `APP_10519`.
- The directory must be readable by the agent's OS user.
- That reader rejected empty fields (`FR_3085` null character). Write a placeholder such as `(blank)` for empty cells and turn it back into NULL in the cleanse step.
- Write files to a temp name and rename them into place atomically.

### L-CDI-196  Change a copy-data task's SQL logic headless: edit parameters[0].customQuery
**Kind:** ROUTE · **Proven:** 2026-09-30 · **Evidence:** Two live rule changes, each read back and proven by the next lane run (2026-09-30)
Mapping tasks built on a copy-data template keep their logic as a custom SQL query in the task itself. `GET /api/v2/mttask/<taskId>`, change only `parameters[0].customQuery`, drop `createTime`/`updateTime`/`createdBy`/`updatedBy`, then `POST /api/v2/mttask/<taskId>` with the full object. It returns 200, and the next run uses the new SQL. Read the query back, keep the GET body as the backup (undo = POST it back), and dry-run the new expression against the warehouse first to count exactly which rows change.

### L-CDI-197  Change every live writer of a table, re-import and read back, and refresh the generator's schema before a swap
**Kind:** GOTCHA · **Proven:** 2026-10-03 · **Evidence:** The old key reappeared after a full-lane run; fixed by patching the second writer (2026-09-30); a NULL key column caught 18 min after a swap and rolled back, a same-name second mapping after a swap import, and a view fix that survived only after the plan DDL changed (2026-09-30 to 2026-10-03)
After consolidation, the same table can be written by an old per-table task in one lane and a new multi-target mapping in another. A rule changed in only one of them silently comes back the next time the other runs: a fixed dedupe key was overwritten by the older logic 3 hours later, when the full lane ran. Before changing a transformation rule, list every task or mapping whose targets include the table (the plan's target lists, the lanes and task-level schedules), change them all, then run each lane once and check the output. A spec patch is not a fix: re-import the mapping (OVERWRITE, same GUID), export it again and compare (for example the md5 of the exported IMF) with what you meant to ship. Change the rule in every target of a multi-target mapping too: a cleanse rule changed in only one of two targets made two downstream passes flip a value back and forth. A swap import of a proven mapping into the live project can create a second mapping of the same name beside the scratch copy (another folder and id): create the live mapping task on the live mapping's id, never repoint or reuse the scratch task. Refresh the generator's column list from INFORMATION_SCHEMA immediately before every build and swap, and diff source against target columns, not only rows: a cached schema that predated one column produced a mapping that wrote NULL into it, and parity had passed because the column was absent on both sides (L-CDI-141). If a controller re-creates warehouse views from its own plan after every run, a direct CREATE OR REPLACE is reverted at the next run: change the plan's DDL.

### L-CDI-198  Per-target row counts of a multi-target mapping are in transformationEntries
**Kind:** GOTCHA · **Proven:** 2026-09-30 · **Evidence:** Five- and eleven-target mappings logged per table after the change (2026-09-30)
The activity-log entry of a mapping task with several targets reports one `successTargetRows` total, the sum over all targets. Per-table counts are in its sub-entry's `transformationEntries`: entries with `txType` TARGET carry `txName` (the table), `txInstanceName` (the transformation) and `successRows`. An insert target and an update target of the same table appear as `<table>` and `<table>_1`, so merge them by table. Two targets with the same table name in different datasets differ only by instance name, so map those by a naming hint such as Land/Raw/Stg. Log one lineage row per table, not one per task.

### L-CDI-199  Key-sync deletes in a consolidated mapping can erase history the old tasks kept
**Kind:** GOTCHA · **Proven:** 2026-09-30 · **Evidence:** Caught before go-live: 180 earlier invoices would have been deleted; insert+update kept all 360 (2026-09-30)
A generated 'full key sync' pattern (source keys outer-joined to target keys, missing keys deleted) is right for mirrors, but wrong for append-history targets such as posted invoices. A mapping that posts one file at a time would have deleted every row from earlier files. For history targets use insert + update only. Prove it on a scratch copy seeded with the live rows: the count must stay the same and the diff must be 0.

### L-CDI-200  Generated mappings must carry the BigQuery writer poll interval (default 10 s)
**Kind:** GOTCHA · **Proven:** 2026-09-30 · **Evidence:** Same scratch mapping 127 s vs 56 s; an earlier task-level change 114 s → 40-69 s (2026-09-29/30)
The BigQuery V2 writer polls its load job every 10 s by default, adding up to ~9 s per BigQuery target. A mapping that writes 10 BigQuery tables pays it 10 times. Set `jobPollInterval`/`pollInterval` = 1 and the advanced attribute 'Job Poll Interval In Seconds' = 1 on every BigQuery target, and put them in the generator's template so new mappings inherit them. Measured on the same mapping and rows: 127 s → 56 s. A consolidation that forgot them made its lane slower than the tasks it replaced.

### L-CDI-202  Full SQL ELT (pushdown) is switched on headless on the v2 mapping task: three fields, proved only by OPT_63367 in the session log
**Kind:** OVERTURNED · **Proven:** 2026-10-01 · **Evidence:** A scratch copy configured over v2 ran 11 times (10 SUCCESS); every session log showed OPT_63367 and one BigQuery INSERT INTO per target (5 targets, each INSERT 0-1 s); a field-by-field diff against the agent-mode task showed only these three keys as functional differences; an earlier attempt with only 'Pushdown Optimization: Full' read back but logged no SQL ELT lines · **Supersedes:** L-CDI-042
`GET <serverUrl>/api/v2/mttask/<taskId>` (header `icSessionId`), drop the read-only fields, set `"sessionProperties": {"Pushdown Optimization": "Full", "Allow Temporary View for Pushdown": "Yes"}` and the top-level `"enableCrossSchemaPushdown": true` (needed when sources and targets sit in different datasets of one warehouse), then `POST /api/v2/mttask/<taskId>` with the full body (L-CDI-084) and read it back. The mapping's BigQuery targets must carry no write disposition, because BigQuery rejects one on DML jobs. `Pushdown Optimization: Full` on its own persists on read-back but the run stays in agent mode, which is why pushdown once looked walled; which added key is decisive was not isolated, so set all three. The only proof is the run's session log (`GET /api/v2/activity/activityLog/<entryId>/sessionLog`, L-CDI-211): `TM_6721 Started [SQL ELT optimization]`, `OPT_63321 [Full SQL ELT optimization is supported between the source and the target system.]`, `OPT_63367 Full SQL ELT optimization was successfully enabled.`, `TM_6722 Finished [SQL ELT optimization]` (about 3 s), then for every target a `BIGQUERYV2_10000 ... final query ... in full SQL ELT mode: [INSERT INTO ...]` line between its pre-SQL and post-SQL lines; `OPT_63375` names the fallback mode, and 'Partial SQL ELT' means part of the mapping ran on the agent. No OPT_63367 and no INSERT lines means no pushdown, whatever the task JSON says. Mappings that also read or write another system cannot push down fully (L-CDI-043). To find the REST name of any task setting without a UI capture, diff the v2 JSON of a task the UI switched against an identical task that was not switched. Prove it on an unscheduled scratch copy that writes parity targets, then gate on speed (L-CDI-203); the rollback is `sessionProperties {}` and `enableCrossSchemaPushdown: false`.

### L-CDI-203  Full pushdown writes a mapping's targets one after another: on small data a multi-target mapping gets slower, not faster
**Kind:** PERF · **Proven:** 2026-10-01 · **Evidence:** Session-log timestamps of the pushdown run: the 5 targets finished about 6.4, 11.1, 16.2, 21.9 and 27.2 s after the optimization step; medians from 24 h of activity-log rows for both tasks; the pilot was closed as 'measured slower'
In full SQL ELT the agent writes a mapping's targets serially, each as two pre-SQL statements, the INSERT and a post-SQL statement, at about 5.4 s per target even when the warehouse INSERT itself takes 0-1 s, after an optimization step of about 3 s; agent mode writes all targets of the mapping in parallel. A 5-target BigQuery-to-BigQuery mapping took a median 43 s with pushdown (n=6, 38-49 s) against 27-29 s in agent mode (n=30-32). Rule of thumb: pushdown costs about 3 s + 5.4 s x targets on top of the ~20 s fixed task cost (L-CDI-121), so a 1-target mapping at 12 s cannot gain much and an 11-target golden-record mapping gets slower. Pushdown does not change the job count (each run is still one job), but it is metered per million rows processed instead of per compute hour (L-IPU-003), so it can still pay for cost at high volume. Keep pushdown on a mapping only if a parity run matches exactly (two-way EXCEPT DISTINCT = 0 on every target) and the median of at least 3 timed runs is at least 20% or 10 s faster; otherwise revert. At thousands to tens of thousands of rows per run the bigger lever was removing jobs from the critical path, for example reading the CDC copies already in the warehouse instead of re-reading the source database in every lane. Where pushdown should pay (large volumes, few targets) was not measured here.

### L-CDI-204  Transformations proven headless with a spec-to-IMF generator, and where their IMF shapes come from
**Kind:** RECIPE · **Proven:** 2026-10-03 · **Evidence:** Every node type above ran in real jobs from scratch mappings (2026-09-30); three showcase mappings (21, 28 and 11 transformations, 16 types) tied to the reporting layer exactly; a suite of 9 complex scenarios passed exact two-way keyed diffs on a real Secure Agent (3 chained outer joiners 22,895 rows in 42 s; full-outer 2-key reconciliation 18,491 rows; sorted self-join 9,289 rows in 284 s; SCD2 with MD5; local-day lookups across a DST change) (2026-10-03)
A generator (spec JSON -> IMF JSON -> DTEMPLATE package -> v3 import -> mapping task -> run) built and ran real multi-transformation mappings with Source, Target, Filter, Expression (variable ports), Sorter, Joiner (normal, master outer, full outer, chained, sorted same-source self-join), Router, Aggregator (stacked), Union, Rank (top-N), Sequence Generator, connected and unconnected Lookup, Data Masking, Rule Specification, Cleanse, Deduplicate, Normalizer, mapplets, in-out parameters for incremental loads, and Update, Upsert, Delete and Data Driven writes on BigQuery and PostgreSQL targets. The class model lives in the Mapping Designer's JavaScript bundle (`cmd-all-<build>.min.js` and `cmd-webpack-<build>.min.js` under the designer's static path): search it for `infaw.template.T<Name>Generator` (`initTx`, `createDefaultGroups`). `GET https://<pod>.<domain>.informaticacloud.com/da/w3.imf/iclass/?infaToken=<icSessionId>` returns the class-header catalogue (HTTP 400 status but a real body, no property lists), and the masking techniques come from `infaw.saas.SaaSService.instance().getMaskRulesAsJSON()` evaluated inside a logged-in designer page (27 techniques). Shapes that ran: Union = plain groups Input1..n plus OutputGroup, with `inputGroups` = TmplUnionGroup {name, fieldMapping: {fields: [TxFieldMapping name=<incoming field>, txField=<ref to the output field>]}} (TmplUnionGroup is not a group: putting it in `groups` fails with a cast error); Rank = a DefaultGroup with `isTop`, `rankField`, `numOfRows` and `groupByFieldsList` (it adds RANKINDEX); Sequence = TmplGenerator with `midstream=true` and a GeneratorState `state` (it adds NEXTVAL; the start value was ignored and numbering began at 1); unconnected Lookup = no groups, `inputPortNames`, `lookupConditions`, `returnPortName`, `unconnected=true` and a warehouse adapter like a source's, called as `:LKP.<NAME>(arg)` in an Expression; Data Masking (TmplDmo) = `maskingType` with the human label ('Email address', 'Phone', 'SSN', 'Credit card', 'Key') and that rule's parameters, outputs `out_<field>`, format-preserving, and pass-through fields do not flow through it (link them around it); Rule Specification = the package must carry the asset (a mappingTemplate `references` entry of refType `frsDocument`, an `exportedObjects` RULE_SPECIFICATION entry and the objectRefs). A failed import leaves a broken shell that a later REUSE import picks up (REPO_36004): re-import under a new name. Copy the DQ assets a mapping references (cleanse, dedupe) in from another org by package import first, and harvest real IMF exemplars of each class by export (L-CDI-035). For the Deduplicate match-field trap see L-DQ-101. Still unproven headless: the Data Quality transformation and Update Strategy.

### L-CDI-205  Retry a FAILED IDMC task once on transient error signatures only, never on the job-cap error, and classify SaaS-target WARNINGs separately
**Kind:** RECIPE · **Proven:** 2026-10-01 · **Evidence:** 24 h census of one org (711 top-level entries: 612 SUCCESS, 97 WARNING, 2 FAILED): both failures were transient cloud errors (a BigQuery 503 and a staging-file upload error) and the next run of each succeeded; all 97 WARNINGs were SaaS upserts rejected with STORAGE_LIMIT_EXCEEDED; a golden-record mapping failed 1 in 52 runs with 'Table [...] does not exist' on an existing table (2026-10-01); a scheduled taskflow's single re-run after a BigQuery 503 succeeded (2026-09-29); the overall recovery rate of the retry was not recorded
When an external orchestrator or watcher starts mapping tasks or taskflows (`POST /api/v2/job`, watched through the activity log), classify a FAILED task's error text and start it once more (after about 20 s, or at once for a lane's critical-path task) only if it matches a transient pattern: 'Retrying may solve the problem' (a BigQuery 503 backend error), HTTP 500/502/503/504 in the message, 'backend error', 'service unavailable', 'rate limit', 'connection reset', a staging-file upload error, "Table [<table>] does not exist" for a table that does exist, and `Temp_View<digits>` with 409 or 404 (concurrent BigQuery query-source collisions, L-CDI-160). Never retry 'monthly limit' (the job-cap error, L-IPU-041): hand it to the quota breaker (L-CDI-132). Report every other failure (heap OOM, validation, authentication, data errors) without retrying, and do not auto-retry SaaS writes that failed on target-side limits such as a full CRM (they only repeat, L-CAI-080). Retry only once: record the first error and a RETRYING state so the retry shows in run history, keep a state file of runs already re-run so a second failure is never retried, and count each retry as one more job against the monthly cap. A persistent 'Internal error ... DTM process terminated unexpectedly' is a host problem (L-AGENT-063); after a staging 5001 check the target row count first (L-CDI-130). Keep the watcher's own network errors (DNS, timeouts) from triggering any IDMC call, and stop it at once on a rejected login instead of looping (L-AUTH-042). Without a retry an event-driven lane leaves the triggering record waiting for the next event: one transient 'does not exist' failure on the golden-record mapping cost a record 28 minutes. Treat WARNING per task, not per lane: a WARNING with rejected rows on a SaaS target (storage full, duplicates, locks) is a target problem to alert on, not a pipeline failure, while a WARNING that wrote 0 rows is a failure (L-CDI-060); an orchestrator that failed whole lanes on any WARNING marked lanes FAILED although the golden records and marts had landed.

### L-CDI-206  Measure record-to-golden latency per hop with CDC APPENDS() plus warehouse time travel at each publish, never the truncate-load stamp
**Kind:** RECIPE · **Proven:** 2026-10-01 · **Evidence:** 61 inserts over 24.6 h (58 new records, 3 merged into existing survivors) read against 42 golden-table publishes by time travel (about 1 GB billed for all snapshot queries); per-hop numbers from the activity log and the CDC change history; 0 records seen before their source event
A golden-record mapping that truncate-loads its target restamps one load time on every row, so that stamp cannot time a single record. Measure instead: (1) list new source rows and their first `_CHANGE_TIMESTAMP` from the CDC replica's `APPENDS(TABLE <cdc_dataset>.<table>, <t0>, NULL)` history (L-DBMI-029; it also keeps rows later purged at the source), or take the source `created_at`; (2) list every successful publish of the golden table (task end) from your run ledger or the activity log (page at `rowLimit=1000` and flatten taskflow entries; a stand-alone task's sub-entry has an empty objectName); (3) for each publish query the golden table `FOR SYSTEM_TIME AS OF TIMESTAMP_ADD(<task end>, INTERVAL 2 SECOND)` for the new keys: the first snapshot that holds a key gives its latency. BigQuery traps: only one `FOR SYSTEM_TIME AS OF` value per table per query, so snapshots cannot be UNIONed (one small query per publish, run in parallel); `AT` is reserved and cannot be an alias; time travel reaches back about 7 days (L-CDI-161). Decompose each sample into wait-to-start (run start minus event: it can be negative, because the mapping reads the source after its fixed start-up cost, so a row committed up to about 35 s after the start still made that run) and the mapping's runtime, and confirm the orchestrator is idle before timing. Report n, average, fastest, last and median over a rolling 24 h, success-only (L-METHOD-049), and say whether a number is the orchestrator's wall time or the IDMC task span (they differed by about 74 s on a full lane). Measured on one 8-vCPU agent host (source row -> CDC copy -> one consolidated golden mapping with 11 targets; 60 s minimum gap between lane starts): created to golden average 76 s, median 67 s, p90 116 s, fastest 33 s (n=58); the golden mapping ran a median 65 s (about 8,900 rows) and was the bottleneck, and the median wait to start was 1.5 s; the 7 of 58 records that missed a run (the lane gap or another lane's lock) formed the whole 104-156 s tail. In the same window CDC to the warehouse averaged about 21 s and the real-time CAI decision about 0.1 s; lane wall times were about 96 s (7 tasks), 145-159 s (11 tasks) and 258-358 s (a 23-task full rebuild). Conclusions: seconds end to end through batch CDI lanes are not reachable (each lane takes 85-150 s), so CDC and CAI must carry the per-event story; optimize the dominant step on the path, not the trigger. Newer evidence: L-METHOD-158.

### L-CDI-207  PostgreSQL targets in generated mappings: an Upsert that applied nothing, keep-when-null, uuid reads, and mirror versus history deletes
**Kind:** GOTCHA · **Proven:** 2026-09-30 · **Evidence:** 736 requested / 0 applied on the first build; the Joiner + Router build wrote 753 updates + 5 inserts, 780 + 5 and 780 + 5 on three targets with 0 mismatched keys; a mirror with a delete group did Insert 7 / Update 764 / Delete 2; keep-when-null verified on 51 rows; a mirror equal to the source on 12 of 12 tables (2026-09-29/30)
In an IMF-generated mapping that fans out to several PostgreSQL reverse-ETL targets, the targets set to operation Upsert behaved as update-only: on a scratch copy where every key was new the session requested 736 rows and applied 0, with no error, because the generator had not written the writer attributes the UI sets for that operation (the exact attribute was not isolated). Two fixes worked: (a) a Joiner against the target's keys (outer, so unmatched source rows survive), then a Router into an Update target instance (key found) and an Insert target instance (key not found); (b) a later generator that writes those attributes, with which Upsert, Update, Delete and Data Driven all ran on PostgreSQL and BigQuery targets. The template-task Upsert with `targetUpdateColumns` (L-CDI-089) was not affected; test new-key inserts on every Upsert target of a generated mapping before it goes live. Other rules from the same swaps: an old per-column update never overwrote a stored value with NULL, so the consolidated mapping needs a keep-when-null Expression (take the stored value when the incoming one is NULL) or stored values get blanked; read PostgreSQL uuid columns as `::text` in the source query; for mirror targets (a database or a JDBC warehouse) do upsert plus a key-sync delete (a master-outer Joiner of target keys to source keys, a Filter where the source key is null, then Delete), never a TRUNCATE (L-CDI-208); for append-history targets use insert + update only (L-CDI-199).

### L-CDI-208  A 'Pre SQL' TRUNCATE runs before the source is read: a failed read leaves the target empty
**Kind:** GOTCHA · **Proven:** 2026-09-30 · **Evidence:** A source-login failure made every landing task of one mirror lane fail after its Pre SQL truncate had already run; the next hourly downstream refresh published empty marts and 5 dashboard charts showed no results for about 4.5 h (2026-09-26). After the redesign as key-sync mappings (parity 0/0), a scratch task aimed at a missing table ended state 3 'Object [...] not found' and the target kept its 822 rows (2026-09-30)
The full-reload switch for JDBC V2 targets, the runtime attribute `Pre SQL` = `TRUNCATE TABLE <t>` (L-CDI-171, L-CONN-056), executes when the session starts, before the reader has fetched a row. If the source login or object then fails (a renamed or retired database role, a dropped table, a network drop), the task ends in error with the target already empty, and whatever refreshes from it next (materialized views, BI extracts, dashboards) publishes empty results until a good run. A failed read should leave the last good data in place: (1) load a stage table and swap or rename it in only after a successful run (post-SQL did not run when the read failed; verify this on your connector); or (2) use a key-sync mirror (upsert every source row, then delete target keys missing from the source) whose deletes run only after a successful read, guarded by a count gate that skips the deletes when the source returns 0 rows or far fewer than the target holds (L-CDI-091). Never use key-sync deletes on append-history targets (L-CDI-199). Prove the design by pointing a scratch copy at a source object that does not exist: the task must fail and the target must keep its rows. Before retiring or renaming a database role, list every connection that logs in as it (L-CONN-011).

### L-CDI-209  A reverse-ETL guard trigger that never blanks a governed field must still allow an explicit clear
**Kind:** PATTERN · **Proven:** 2026-10-03 · **Evidence:** Stale-value drift 68 -> 0 after a backfill; CRM versus source mismatches 3 -> 0 of 721 linked records; guard behaviour tested in a rolled-back transaction
A database trigger on reverse-ETL targets that reverts any NULL written over a non-NULL value protects governed fields from a broken upstream load, but it also reverts legitimate business clears (for example a cancellation that empties a plan or status field), so the CRM and downstream syncs keep the old value. Let the application opt in per transaction: it runs `SET LOCAL <namespace>.allow_clear = 'on'` only for an explicit clear, and the trigger returns NEW unchanged when `current_setting('<namespace>.allow_clear', true) = 'on'`. IDMC writes never set it, so they stay guarded. Test it in a rolled-back transaction: without the flag a NULL is reverted, with it the NULL lands, and the flag is gone after commit.

### L-CDI-210  A DTM heap OOM shows up as 'Unexpected error refreshing access token' on the other BigQuery reader partitions
**Kind:** ERROR · **Proven:** 2026-09-29 · **Evidence:** A 17-transformation data-quality mapping failed 3 of 3 live runs with this sequence (PLUGIN_1762 OOM first, then BIGQUERYV2_10000 5001 token errors on four reader partitions, WRT_8044) after passing a solo run; with a 2 GB DTM heap it ran solo OK (859 rows, parity 0/0)
When a DTM runs out of heap, the first error is `PLUGIN_1762 [ERROR] java.lang.OutOfMemoryError: Java heap space` in one reader thread (stack in `CCIRuntimeDataClientImpl.readData`). Seconds later the other BigQuery V2 reader partitions fail with `BIGQUERYV2_10000 ... [5001 - Unexpected error refreshing access token]` and the targets log `WRT_8044 No data loaded for this target`. The token errors are a cascade of the dying JVM, not a credential problem: read the first `[ERROR]` in the session log. Generated multi-transformation mappings with many Joiners, Sorters and Aggregators are the usual victims: an unsorted Joiner runs as `TT_11098 The Joiner transformation [...] is configured with the join algorithm: Nested-Loop` and caches its master side, a Sorter reserved about 150 MB per partition, and Aggregators grow their caches at start (`TE_7212 Increasing [Data Cache] size`). Such a mapping can pass alone and fail beside other lanes, because the heap is per DTM and several DTMs run at once (L-AGENT-099). Fix in this order: take the mapping out of the live taskflows (restore the tasks it replaced), raise the DTM heap cloud-side (L-AGENT-056), then split the mapping or give its Joiners sorted input before putting it back.

### L-CDI-211  Download a task run's session log over REST: GET /api/v2/activity/activityLog/<entryId>/sessionLog
**Kind:** ROUTE · **Proven:** 2026-10-01 · **Evidence:** HTTP 200 for two runs (76,677 and 76,524 characters, one pushdown and one agent-mode run of the same mapping); used to prove pushdown
`GET <serverUrl>/api/v2/activity/activityLog/<entryId>/sessionLog` with header `icSessionId: <v2 session>` and `Accept: */*` returns the run's session log as plain text (about 75 KB for a 5-target mapping), so run evidence can be read without a shell on the agent host (the on-disk logs of L-CDI-064). `<entryId>` is the `id` of the run's activity-log entry, not its `runId`. Grep the text for what you must prove: `TM_6721`/`TM_6722` (optimization start and finish with its duration), `OPT_63367` (full SQL ELT enabled, L-CDI-202), `OPT_63375` (the fallback mode), the connector's `INSERT INTO` lines and per-step execution times, or the first `[ERROR]` of a failed run (L-CDI-210). Save the text with the run id as evidence: it is the only proof of what the engine actually did.

### L-CDI-212  Full SQL ELT to BigQuery without FIRST() or INITCAP: MAX over a fixed-width order key, and a SQL transformation for the native function
**Kind:** RECIPE · **Proven:** 2026-10-04 · **Evidence:** A 26-transformation BigQuery-to-BigQuery mapping (5 table sources, 4 Aggregators, 4 master-outer Joiners, the SQL transformation, 1 target) ran 6 of 6 times with OPT_63367 and one INSERT INTO ... SELECT; rows and checksum equal to an independent SQL answer key (496 rows) on every run; the FIRST/INITCAP version had been refused with OPT_63321 / OPT_00014 (2026-10-04)
The Google BigQuery V2 connector's full-SQL-ELT function list has no FIRST()/LAST() and no INITCAP, so a mapping that uses either is refused (`OPT_63321 ... The Following <tx> is not Supported in Full SQL ELT Mode : FIRST`, `OPT_00014 SQL ELT optimization stopped due to expression [...]`) and falls back to partial pushdown or agent mode. Replace a 'Sorter + Aggregator FIRST(x)' pick (one row per group in a multi-column order) with one Aggregator `MAX(order_key)`: build `order_key` in an Expression as fixed-width, order-preserving text of the sort columns followed by the payload, for example `IIF(status = 'active', '1', '0') || TO_CHAR(IIF(ISNULL(ts), TO_DATE('1900-01-01 00:00:00', 'YYYY-MM-DD HH24:MI:SS'), ts), 'YYYY-MM-DD HH24:MI:SS.US') || <fixed-length id> || <payload>`, and cut the payload out after the Aggregator with `SUBSTR(best, <pos>, <len>)`. The optimizer writes that TO_CHAR as `FORMAT_TIMESTAMP('%Y-%m-%d %H:%M:%E6S', ...)`, always 26 characters, and Informatica `||` as a CONCAT that returns NULL only when every operand is NULL. An all-descending order needs no inversion; give NULL sort values an explicit sentinel. Link into the Aggregator only the ports it groups by or aggregates. For a warehouse function missing from the list (INITCAP), put a passive SQL transformation on the same BigQuery connection with the entered query `SELECT INITCAP(~<field>~) AS <out>` (the connector guide documents SQL transformations for pushing scalar functions and UDFs): the optimizer inlines it into the generated `INSERT ... SELECT`, so the result has the warehouse's own semantics. Build the SQL transformation in the designer's shape (one IN port per incoming field, pass-through fields as OUT `<name>_output`). The guide also refuses full SQL ELT when one transformation feeds several (documented, not tested here), so keep one Aggregator instead of a Rank branch plus a COUNT branch.

### L-CDI-213  The SQL ELT optimizer escapes backslashes itself: write a regex as the agent reads it ('\s+'); a doubled backslash silently changes it
**Kind:** GOTCHA · **Proven:** 2026-10-04 · **Evidence:** Two full-SQL-ELT runs of one mapping (2026-10-04): spec '\\s+' gave a generated literal with 4 backslashes, spec '\s+' one with 2; a BigQuery SELECT on 'ann  <TAB> lee' returned the input unchanged for the first literal and 'ann lee' for the second, the same as r'\s+'
When the optimizer writes an Informatica string literal as BigQuery SQL it escapes every backslash, so the regex reaches the warehouse with the meaning it has in agent mode: `REG_REPLACE(x, '\s+', ' ')` is generated as `REGEXP_REPLACE(..., '\\s+', ' ')`, which collapses whitespace runs. Doubling the backslash, as the connector guide's backslash note suggests, is wrong on this path: `'\\s+'` was generated as `'\\\\s+'`, a literal backslash followed by `s`, so the step silently did nothing; the run still succeeded and even matched its answer key on data without repeated whitespace. Read the literal in the session log's generated SQL and test it with one SELECT in the warehouse (`SELECT REGEXP_REPLACE('a  b', '<literal>', ' ')`) before trusting a pushed-down regex.

### L-CDI-214  Full SQL ELT hygiene: fallback 'Fail Task', table sources (no temp views), a dedicated connection for the custom-query and staging datasets
**Kind:** RECIPE · **Proven:** 2026-10-04 · **Evidence:** Session logs and activity-log rows of 4 timed runs and 2 validation runs; a dataset census after every run found no temporary object created by the runs; BigQuery job statistics of the TRUNCATE and INSERT jobs (2026-10-04)
The task's fallback option is the v2 session property `Pushdown Optimization Fallback Option` (designer values include `Partial PDO`, the default, and `Fail Task`); set it with the pushdown fields of L-CDI-202 and the session log reports `OPT_63375 SQL ELT fallback option is set to [Fail Task]`: a run that cannot push down fully then fails instead of silently running partly on the agent, which also keeps a SQL transformation from running once per row. Use table or view objects as sources: the generated SELECT reads them directly and no temporary view is created. A custom-query source (or an SQL override) needs `Allow Temporary View for Pushdown` and creates one view per source in the connection's `Dataset Name for Custom Query` (connParams `datasetNameForCustomQuery`), with a create and a drop statement each (about 0.5-0.6 s apiece, one after another). Give pushdown work its own BigQuery V2 connection (a GET-and-re-POST clone of the working one, with the key re-supplied from where it is stored) whose `datasetNameForCustomQuery` and staging dataset (`datasetNameValue`) are the work dataset, so no temporary object lands in a shared landing dataset. Measured on small data (1 target, ~500 output rows from 5 tables of 80-780 rows, 26 transformations): job time 11-12 s (n=4) of which optimization ~3 s, the pre-SQL TRUNCATE ~1.9 s and the single INSERT ~1.9 s (warehouse execution 1.3-1.6 s, 20-29 slot-seconds); the same logic in agent mode took ~9-11 s, and a partial-pushdown version (5 query-source temp views, joins on the agent) ~29-30 s. On data this small full pushdown is about 3 s slower than agent mode (L-CDI-203) and about 2.3 times faster than partial pushdown.

### L-CDI-218  Mapping-task pre- and post-processing commands are set headless with v2 preProcessingCmd / postProcessingCmd; flat-file sources are validated before the pre-command runs
**Kind:** RECIPE · **Proven:** 2026-10-06 · **Evidence:** One headless build of a multi-flow mapping (flat-file sources, Snowflake lookups and targets) on a Linux Secure Agent, adapter version 10.4 (build 872), five runs (2026-10-06)
GET /api/v2/mttask/<id> omits the fields when they are empty. POST the task object back (drop createTime, updateTime, lastRunTime, createdBy, updatedBy) with preProcessingCmd and postProcessingCmd set to shell commands, then read back to confirm. The commands run on the Secure Agent host as the agent's OS user: pre before the mapping, post after a successful run (a failed run skips post). Two traps: (1) the task validates every flat-file source object BEFORE the pre-processing command runs; a missing file fails the run at once with 'Object <file> is not valid: ... File [<dir>/<file>] does not exist', so a pre-command that generates the source files needs them (headers are enough) to exist already; (2) re-importing the mapping in OVERWRITE mode keeps the task and its commands. This gives a headless script step around a mapping without an advanced taskflow Command Task (whose publish is UI-only).

### L-CDI-219  Document-intake pattern in one mapping: per-flow check expressions, router OK / EXC / ALL, one exception union, per-document aggregates joined to a registry
**Kind:** PATTERN · **Proven:** 2026-10-06 · **Evidence:** One headless build of a multi-flow mapping (flat-file sources, Snowflake lookups and targets) on a Linux Secure Agent, adapter version 10.4 (build 872), five runs (2026-10-06)
For many small document feeds, one mapping keeps the cost to one job and one warehouse session per run. Per flow: source -> expression (typing with IS_NUMBER / IS_DATE guards plus unconnected cached lookups on master data) -> expression of checks (rule = first failing check, nested IIF; detail = every failing check's text concatenated) -> router with OK (no rule), EXC (rule) and ALLROWS groups, all gated by a 'document already processed' lookup -> OK to the typed target, EXC to a Union feeding one exceptions table, ALLROWS to an Aggregator by document id (rows, loaded, review, rejected, one example reason). The per-flow aggregates go through a second Union into a Joiner (master outer) with the registry source, and an expression derives each document's status (PROCESSED / PARTIAL / NEEDS_REVIEW / REJECTED / DUPLICATE). In-batch duplicates: Sorter on the business key plus VARIABLE ports comparing with the previous row; history duplicates: a lookup on the loaded table. Grouped 'packet' rules (all required documents present): Aggregator by folder, then join the packet status back to a second read of the same file (no self-join). One unconnected lookup can be called from several pipelines of the same mapping.

### L-CDI-222  TagObjects: bundle content refuses tags, MDM app and CAI content accept them; hyphenated tags work; delete an empty tag through FRS
**Kind:** GOTCHA · **Proven:** 2026-10-06 · **Evidence:** 207 per-item results on a 20-object type probe; tag-query read-back; DELETE 204 then 404 FRS_037
`POST /public/core/v3/TagObjects` answers 207. Each Add-On Bundle item (bundle mappings, mapplets, cleanses) comes back `FAILED ... skipped has no READ permission`, even for an org administrator. Objects inside installed MDM app projects, CAI assets (stuck published ones included), the system API policy and DQ preview mappings return SUCCESS. Tag names with a hyphen work, and `GET /public/core/v3/objects?q=tag=='<tag>'` reads them back. `UntagObjects` takes the same body. A tag with no documents left still exists in FRS `Tags`: `DELETE https://<pod>.<domain>.informaticacloud.com/frs/api/v1/Tags('<tagId>')` with `IDS-SESSION-ID` returns 204, and the read-back is 404 `FRS_037` (no artifact).

### L-CDI-220  Event-driven pickup from SharePoint Online for a mapping task: a Graph change-feed poll triggers the job, the task's own pre-processing step downloads only new files
**Kind:** RECIPE · **Proven:** 2026-10-06 · **Evidence:** One live build on a Linux Secure Agent: upload seen in 4 s, job started 18 s later, run 101 s; six demo uploads verified end to end (30 of 30 checks); offline tests of the watcher logic (17 cases).
For 'drop a document in SharePoint and IDMC processes it' without a schedule: a small service on the Secure Agent host polls Microsoft Graph delta on the document library (GET /drives/<id>/root/delta, one call every few seconds; start with token=latest). When a file changes it waits until uploads go quiet for a few seconds (so a multi-file drop becomes one run) and starts the mapping task with POST /api/v2/job. The download itself happens inside the task: its preProcessingCmd pulls every file whose item id + cTag is not yet in a local ledger into the folder the flat-file connection reads, so the Run button behaves the same as an upload. No upload means no job and no warehouse wake-up. Guard it: one run at a time (check activityMonitor), runs per hour/day, the same file version at most twice, back-off after a failed run, a pause file.

### L-CDI-221  A mapping-task post-processing command that starts background work must detach it from the command's stdout/stderr, or the post-session step waits for it
**Kind:** GOTCHA · **Proven:** 2026-10-06 · **Evidence:** Live mapping task on a Linux Secure Agent: post step returned in ~1 s while the detached hooks ran 2-40 s afterwards and logged to their own file.
The agent runs postProcessingCmd through a shell and reads its output until EOF. A child process that inherits stdout keeps the step (and the task) open until the child ends. Start follow-up work (a BI refresh, a quality snapshot) in a new session with stdin from /dev/null and stdout/stderr to a log file (e.g. Python subprocess.Popen(..., start_new_session=True, stdin=DEVNULL, stdout=logfile, stderr=STDOUT)); the step then returns at once. Remember the post command runs only after a successful session.

### L-CDI-223  Create an intelligent structure model headless from a sample file: six calls, about 4 s
**Kind:** RECIPE · **Proven:** 2026-10-06 · **Evidence:** two models created from a spreadsheet and a PDF; read back on v2 and v3; per-call responses kept
All on `https://<pod>.<domain>.informaticacloud.com`. (1) `GET /saas/api/v2/intelligentstructure/getAtlanticWidget` (header `icSessionId`). (2) `POST /structurediscovery-service/atlweb/api/v3.0/validateWidget`, empty body, with cookie `USER_SESSION=<session>` and header `IDS-SESSION-ID: <session>`: `{"valid": true}` plus the service cookies (`JSESSIONID`, `XSRF-TOKEN`, ...). (3) `POST /structurediscovery-service/upload?<resumable params>`: multipart, the same params as form fields and the sample as part `file`, headers `X-CSRF-TOKEN: <XSRF-TOKEN cookie>`, `X-CSRF-PARAM: _csrf`, `X-Ajax-call: true` (all later POSTs too); it returns `inputText` and the learner used. (4) `POST .../RunDataPreview` with form `runData` (fileName, text = inputText, key, learnerUse, treeType horizontal) returns `aModelString`, the CLAIRE-discovered model, in under a second. (5) `POST .../getStructure` with form `formData` (name, description, learnerUse, fileName, aModelString) returns the model JSON. (6) `POST /saas/api/v2/intelligentstructure/create?containerId=<v3 folder id>` (header `icSessionId`) with `{"orgId": "<v3 org id>", "@type": "structureDefinition", "name", "modelName", "description", "amodel": <the step-5 JSON as a string>}` returns the structureDefinition and its v2 id. The model reads back on v2 and v3 and opens in the designer like a UI-made one. Newer evidence: L-CDI-297.

### L-CDI-224  Structure Discovery service: the session as cookie AND header, then X-CSRF-TOKEN on every POST, or a 404
**Kind:** GOTCHA · **Proven:** 2026-10-06 · **Evidence:** controlled test: no CSRF header 404, X-XSRF-TOKEN 404, X-CSRF-TOKEN 200; cookie-only validateWidget 200 valid:false
The ISD service accepts the platform session only as both cookie `USER_SESSION` and header `IDS-SESSION-ID`: the cookie alone returns 200 `{"valid": false}` (a refusal dressed as success) and no session returns a 302 to the login page. After validateWidget, every POST must carry `X-CSRF-TOKEN` equal to the `XSRF-TOKEN` cookie the service set; without it, or with `X-XSRF-TOKEN` instead, Tomcat answers 404, not 403, which reads like a wrong path. GETs need no CSRF header. The unauthenticated 302 points at a plain http:// URL; a client that follows it through a corporate proxy reports a 504 after about 45 s, so probe without following redirects.

### L-CDI-215  Hard deletes in a Salesforce-to-warehouse pipeline: a key-sync reconcile mapping with a count gate
**Kind:** RECIPE · **Proven:** 2026-10-04 · **Evidence:** Scratch copies: 2 planted non-live Ids deleted from a 17-row table (3 runs); a 23-row copy with 8 non-live Ids (35%) held back by the gate (0 deleted); an 8-object run against an in-sync warehouse: 8/8 SUCCESS in 29 s, 0 rows deleted, READ-ONLY pre/post checks 0 false deletes (2026-10-04)
When the source hard-deletes rows and empties the Recycle Bin, an incremental SystemModstamp watermark never sees the deletes. A per-object reconcile mapping built only from standard transformations removes them: a Salesforce source with only the Id field (the reader issues SELECT Id FROM <object>, one query call per 2,000 rows), a warehouse source with the target's Ids (read the table as an object rather than a custom query, so the BigQuery reader does not create a temporary view in the connection's default dataset), a Joiner with master outer join (master = the Salesforce Ids, so every target row is kept), an Expression not_live = IIF(ISNULL(sf_id), 1, 0), a count gate (Sorters on a constant key on both branches, an Aggregator with sorted input computing n_rows and n_not_live, a Joiner with sorted input back onto the rows: same-pipeline branches need sorted input, L-CDI-106), a Filter not_live = 1 AND n_not_live <= 0.3 * n_rows (L-CDI-208), and a BigQuery V2 target with operation Delete on Id (the writer runs DELETE <table> AS A WHERE EXISTS (SELECT * FROM <staging> AS B WHERE A.Id = B.Id)). Add append targets for one audit row per run and for the deleted Ids. Run one task per object in parallel; the run is idempotent, so a failed task can simply be rerun.

### L-CDI-216  Parallel tasks appending to one BigQuery table hit the per-table update rate limit: use Streaming for shared ledgers
**Kind:** GOTCHA · **Proven:** 2026-10-04 · **Evidence:** One of 8 parallel tasks FAILED on the rate limit with Bulk; after the switch 8/8 SUCCESS, and a Delete probe wrote its 2 log rows by streaming (2026-10-04)
Eight mapping tasks started at once that each appended one audit row to the same BigQuery table through the V2 writer's default Bulk mode (one load job each) failed one task with '[ERROR] The [LOAD] job failed with the following error: [Exceeded rate limits: too many table update operations for this table]' (BigQuery allows about 5 table metadata updates per 10 seconds). Set the shared append targets (audit rows, deleted-Id logs, run ledgers) to Streaming: oprRuntimeAttributes writeMode and runtimeAttributes 'Write Mode' = Streaming; the writer logs 'Sending streaming request [#1] with [n] rows' and the rows are queryable at once. Keep Bulk for targets that are truncated or later changed by DML (L-CDI-154, L-CDI-158).

### L-CDI-217  Generated mappings can read Salesforce objects; a datetime source field failed source-definition validation
**Kind:** GOTCHA · **Proven:** 2026-10-04 · **Evidence:** 12 generated Salesforce-source mappings ran on a Secure Agent (8 reconcile mappings, 3 probes, 1 eight-flow queryAll probe); 3 datetime variants failed validation (2026-10-04)
A spec-generated mapping with a Salesforce source ran: BaseAdapter typeSystem Salesforce, DataObject name = the object API name with objectType SINGLE and the data-object attributes owner / resource (as on a generated Salesforce target), adapter fields with Salesforce native types (Id = id, precision 18). The reader built SOQL from the declared fields ('SOQL is [SELECT Id FROM <object>]', 'Total Expected Records from Salesforce is N') and the stream joined a warehouse source. readOptions.queryAll is the 'Include archived and deleted rows' switch ('The use QueryAll attribute is set.') and readOptions.filterCondition the SOQL filter. A datetime field (SystemModstamp) on the same source made the session stop at start: 'Validating Source Definition <object>... Field SystemModstamp's precision is invalid', then 'The DTM process terminated unexpectedly', with precision/scale 29/0, 19/0 and 29/9 alike; an Id-only field list ran. Take the datetime field shape from one UI-authored Salesforce source, or read datetimes through a template task.

### L-CDI-227  Unbounded Snowflake VARCHAR targets make the CDI writer run out of Java memory: give every target column a length
**Kind:** GOTCHA · **Proven:** 2026-10-06 · **Evidence:** the first run failed with that error; the same mapping with explicit lengths of 20 to 1,200 ran in 93 s
A Snowflake target table whose columns are plain `VARCHAR` (16,777,216 characters) made the CDI Snowflake writer fail with `java.lang.OutOfMemoryError: GC overhead limit exceeded`: it sized its buffer from the declared lengths (a block of about 436 MB for 21 such columns). Create target tables with `VARCHAR(n)`, or set the native precision in Target Fields > Edit Metadata; there, type the value and press Enter, because a pasted value does not commit.

### L-CDI-228  Connector lookups have no operation context of their own; saving a mapping redeploys its tasks
**Kind:** GOTCHA · **Proven:** 2026-10-06 · **Evidence:** designer request log of a lookup's metadata calls and of a mapping save followed by the autodeploy call
Designer calls that take a connection operation context accept READ and WRITE only: a lookup uses the READ settings, so there is no separate lookup configuration to look for. Saving a mapping in the designer ends with `POST /saas/app/da/dTemplatesXHR.do?actionMethod=autodeploy` (`daId` = the v2 mapping id), which redeploys every task on it, so a mapping save changes what the next task run executes without touching the task.

### L-CDI-229  What CLAIRE structure discovery makes of a PDF and a spreadsheet, and the types a Structure Parser emits
**Kind:** OVERTURNED · **Proven:** 2026-10-07 · **Evidence:** three models (a spreadsheet price list, a pricing addendum, a tax-form PDF) parsed in one mapping run; ports and values compared with the source files
A PDF goes through the `PdfToModel` learner: the document becomes key/value records (header, details and footer groups) with dates typed as dates, and a free-text block that spans two lines is left out. The Excel learner splits code-like values into a token and a number (`ABC-001` becomes `ABC` + `1`: the separator and leading zeros are lost, so such a code cannot be rebuilt), and a banner line above a table becomes a field NAME with an empty value. Structure Parser output ports take the model's types (bigint, decimal(10,2), string(n)), not string(255) everywhere; they load into VARCHAR target columns without complaint, with numbers re-rendered (40 becomes 40.0). Field names are cleaned to letters, digits and underscores (`Customer account no.` becomes `Customer_account_no_`). Fix names before building the mapping: the mapping copies them.

### L-CDI-230  A Structure Parser stores '@<v3 id>' of its model plus a copy of the model; the designer resolves the model by its v2 id
**Kind:** OVERTURNED · **Proven:** 2026-10-07 · **Evidence:** the export of a three-flow parsing mapping (isdModelId = '@' + the models' v3 ids) and the designer request log
In an exported mapping the Structure Parser carries `isdModelId: "@<v3 id of the model>"`, `isdLastModify`, `modelString` (a copy of the model, so a later model edit reaches the mapping only after Synchronize) and a `passthrough` flag per output group. The designer looks the model up by its v2 id: `GET /frs/api/v1/Documents?$filter=documentType eq 'SAAS_STRUCTURE_DISCOVERY' and repoInfo/repoHandle eq '<v2 id>'`, `GET /da/web.saas.service/saasinfo/structureDiscoveryDetail?id=<v2 id>` (needs a designer session), and fills the Output Fields tab from `POST /structurediscovery-service/groupsWithXpath` (form body `aModelString=<model string>`). Input group `Input_Group` takes `FilePath` (string 4096) or `Data` (binary); there is one output group per model group plus `Unidentified`. Newer evidence: L-CDI-298.

### L-CDI-231  Parse every document of a folder with a Structure Parser and keep the source file on each parsed row
**Kind:** RECIPE · **Proven:** 2026-10-07 · **Evidence:** one run parsed 8 documents of 3 types into 32 rows, each with its file name and path; 0 rows unidentified
Source = a warehouse view that lists the documents (one row per file with its path), filtered per flow on folder and extension in the source's Advanced filter; an Expression turns the server path into the local path of the connector's download folder (`REPLACESTR(1, PATH, '<server prefix>', '<local folder>')`) and feeds the parser's `FilePath`. In the parser's Output Fields tab, tick Passthrough on each output group: every incoming field except the one mapped to FilePath/Data then comes out on that group, so file name and path land on every parsed row. Land the `Unidentified` group too, so content no model can place never drops out silently. Give each document type its own flow and use Flow Run Order.

### L-CDI-232  Changing the model on a Structure Parser clears its field mapping and every link
**Kind:** GOTCHA · **Proven:** 2026-10-07 · **Evidence:** a copied flow lost its mapping and links when its model changed; re-linked and re-ticked, it ran
Swapping the intelligent structure model of an existing Structure Parser (for example on a copied flow) removes its field mapping, its links and the Passthrough ticks; re-link, re-map FilePath and re-tick Passthrough afterwards. Linking from a parser with several output groups opens a 'Select Output Group' dialog; dropping a new transformation onto an existing link keeps the group.

### L-CDI-233  Snowflake source fields import at 16,777,216 characters: trim them, and know that the Advanced filter is passed verbatim
**Kind:** GOTCHA · **Proven:** 2026-10-07 · **Evidence:** session log of the reader's SELECT (fields used + the filter as WHERE); preview showing unfiltered rows
A Snowflake table or view with unbounded VARCHAR columns imports into a mapping source with precision 16,777,216 per field, the same memory risk as on targets (L-CDI-227): delete the fields the flow does not use and lower the precision of the rest in Edit Metadata. The source's Advanced filter is sent to Snowflake verbatim as the WHERE clause, and the reader selects only the fields used downstream. Preview Data ignores both the filter and the field edits, so verify with a run.

### L-CDI-234  A mapping with many pipelines opens a reader and a writer connection per pipeline even in a strict load order, and they linger
**Kind:** GOTCHA · **Proven:** 2026-10-07 · **Evidence:** failure at pipeline 24 with a limit of 10; with a limit of 40, runs of 49, 61 and 70 pipelines succeeded (8,208 / 11,732 / 8,993 rows) with peaks of 14 reader / 11 writer connections
A landing mapping with 49 source-to-target pipelines, each in its own target load order group (the session log shows group N, concurrent set 1, one after another), still opened a new reader and a new writer JDBC connection for every pipeline, and the connections closed lazily. With pipelines of about 0.3 s, a database role with CONNECTION LIMIT 10 failed at the 24th pipeline with `[SDK_APP_COM_20000] too many connections for role`, after 3,643 rows had landed (the task ends failed; the earlier tables stay loaded). Sampling `pg_stat_activity` every second during later runs showed peaks of 14 reader and 11 writer connections for 49 to 70 pipelines. Give the roles such a mapping uses a limit of about 40 (after checking the server's max_connections headroom), or split the mapping.

### L-CDI-235  Generate a sampled landing layer from the database catalog and validate it with zero IDMC jobs
**Kind:** RECIPE · **Proven:** 2026-10-07 · **Evidence:** 180 queries EXPLAINed clean and the DDL rollback test was clean; then 3 of 3 mapping runs succeeded on the first full attempt with row counts equal to the planned samples
Build each table's field list from `information_schema.columns` filtered by `has_column_privilege(<read role>, <table>, <column>, 'SELECT')`, so column-level grants are respected. Give every table a source with an SQL query: simple types keep their type (integer, bigint, numeric(p,s), timestamptz, date; timestamp converted with `AT TIME ZONE 'UTC'`), everything else becomes `::text` with a precision from the measured maximum length, and bytea and free-text bodies are left out. Write the aliases bare (`"col"::text AS col`): PostgreSQL accepts any keyword as a column label after AS, and quoted aliases defeat simple SQL-to-field checks. Sample inside the query with `ORDER BY <time column> DESC NULLS LAST LIMIT $$<cap>`, using one in-out parameter (retention NEVER) per class of table, so scaling up later means changing one value. Before any run, EXPLAIN every query as the read role and run the target DDL inside BEGIN ... ROLLBACK: neither costs a job.

### L-CDI-236  Generated Normalizer transformations failed at the agent's DTM load; fan out with Expressions into a Union instead
**Kind:** GOTCHA · **Proven:** 2026-10-08 · **Evidence:** runs 1 and 2 FAILED at DTM load; runs 3 and 4 SUCCESS after the Union rewrite (2026-10-08)
A generated mapping with Normalizer transformations (5 occurring fields, and also with a single occurring 512-character field) imported as valid but failed when the agent loaded it: the session log showed only '<Error> : [transformation< NRM_x > ]' and the run ended 'The DTM process terminated unexpectedly'. Replacing each Normalizer with one Expression per output row, fanned out from the same pipeline into a Union, ran successfully. This narrows the Normalizer entry of L-CDI-204: give every new transformation shape one small test run before relying on it.

### L-CDI-237  Finding your tasks: the v2 mttask list has no frsGuid and its 'valid' is always false; a v3 type query stops at 200
**Kind:** GOTCHA · **Proven:** 2026-10-08 · **Evidence:** list valid=false for 260 tasks incl. running ones; per-task GET valid=true; v3 type query 200 of 260; taskflow found in Default by name and moved (FRS_200)
`GET /api/v2/mttask` lists every task but without `frsGuid`, and its `valid` field read false for every task, also ones that run (the per-task `GET /api/v2/mttask/<id>` says valid true). `GET /public/core/v3/objects?q=type=='MTT'&limit=200` returned only the first 200 of an org's 260 tasks, so new tasks were missing from it. Match tasks by a name convention (for example a project prefix) or query by location (`q=location=='<Project>/<Folder>'`), and read validity per task. A new v2 linear taskflow (`POST /api/v2/workflow`) is created in Default and its v2 read has no frsGuid either: find it with `q=location=='Default'` by name and move it with FRS MoveEntities.

### L-CDI-238  Drive Gold from the master entity, not from the documents, so a missing document shows as 'waiting' instead of nothing
**Kind:** PATTERN · **Proven:** 2026-10-08 · **Evidence:** 6 entities: reset -> 6 waiting; first document -> 1 'write the reply'; second -> 1 'fix'; all -> 6/6 expected decisions
A Gold mapping whose source is the checked document lines produces no row for an entity whose documents have not arrived, so the page loses it. Make the source the master list (for example every CRM opportunity) LEFT JOINed to the Silver lines in the source query; in the Aggregator a COUNT of a line key is then 0 for an entity without documents, and the decision Expression can say WAITING FOR <document> (or WRITE <reply> when only the first document came). Together with a starting point (a config row the reset sets to now, and a file-list view that only keeps files modified since then, joined into every Silver read), the same mappings give a clean demo start, a staged arrival one document at a time, and the full picture, with no special code paths.

### L-CDI-239  A reset step inside IDMC: a 3-transformation mapping whose Snowflake target runs CALL <procedure>() as its presql
**Kind:** ROUTE · **Proven:** 2026-10-08 · **Evidence:** reset taskflow 6/6 SUCCESS: starting point set, 0 documents in play, Gold rebuilt as all-waiting, BI refreshed
Source `SELECT 1` -> Expression (run id, SESSSTARTTIME) -> target: a small log table, with the writer runtime attribute `presql` (and display 'Pre SQL') = `CALL <db>.<schema>.<RESET_PROC>()` (KB L-CONN-106: the Snowflake writer only runs SQL from that attribute). The procedure (Snowflake Scripting) sets the starting point and truncates Silver and Gold; the mapping then logs one row per reset. Put it first in a 'reset' taskflow followed by the Silver and Gold steps, so the page is rebuilt in its starting state and the BI refresh (post step of the last task) runs too. SQL runners that split files on ';' cut a procedure body: run the CREATE PROCEDURE as one statement.

### L-CDI-241  Archive every version, read only the newest: '<title> (vN).<ext>' in the archive, ROW_NUMBER per document in the file-list view
**Kind:** PATTERN · **Proven:** 2026-10-09 · **Evidence:** what-if: v2 in play -> the decision flips to the corrected copy; v2 out of play -> back (real runs)
When a document is attached again upstream as a new version, archive it next to the first one as '<title> (v2).<ext>' (the library connector never overwrites, L-CONN-107) and make the file list the readers use keep one row per document: QUALIFY ROW_NUMBER() OVER (PARTITION BY <folder>, REGEXP_REPLACE(<name>, ' [(]v[0-9]+[)]', '') ORDER BY <version number> DESC NULLS LAST, <modified> DESC) = 1. Every reader that filters its Bronze on that list then sees exactly the newest version, and taking the version out of play restores the previous one.

### L-CDI-242  A cloned file-pickup mapping keeps the clone source's pattern file: it lists the other project's folders and never its own
**Kind:** GOTCHA · **Proven:** 2026-10-09 · **Evidence:** cloned pickup listed 6 files of the original project; patched to its own file (2 patterns)
A SharePoint (or any file) pickup copied from another project keeps the source's runtime attribute 'Indirect File Path' (a pattern file on the agent) in both runtimeAttributes and oprRuntimeAttributes. It runs green but lists only the folders of the project it was cloned from. Give each pickup its own pattern file (one line per folder depth, URL-encoded) and patch both attributes in place (export -> edit the IMF -> import OVERWRITE; the task keeps the same mapping GUID). Never edit the shared file: the original project still reads it.

### L-CDI-244  Parse a document whose bytes sit in a column, with no file on the agent: DEC_BASE64 to a binary port, then a Structure Parser in BUFFER mode
**Kind:** RECIPE · **Proven:** 2026-10-13 · **Evidence:** two PDFs (15 pages and 1 page) parsed from warehouse rows in one run each: 29 line rows and 1 form row (2026-10-13)
When the document arrives as base64 text in a column (for example a CRM file body landed in a warehouse VARCHAR), parse it without writing a file. Add an Expression output port `DEC_BASE64(<base64 column>)` with platform type binary and a precision at least the largest document (8,388,608 worked). Set the Structure Parser's `inputType` to `BUFFER`, give its Input_Group field `Data` (binary) and the data adapter's input field `Data` the same precision, and map the binary port onto `Data` in the parser's field mapping. Keep the base64 text out of the parser's input group (an exclude rule on the link): every incoming field is passed through to each parsed row, so a 1.3 MB text column would be repeated on every output row.

### L-CDI-245  A Salesforce datetime source field validates at precision 24, scale 0; a semi-join SOQL filter runs but hides the source from lineage
**Kind:** FACT · **Proven:** 2026-10-13 · **Evidence:** the first run stopped with the precision error (agent session log); precision 24 ran and loaded every row; the semi-join filter returned only the matching parents' rows (2026-10-13)
In a generated mapping, a Salesforce source field with nativeType `datetime` (platform date/time, precision 24, scale 0) passed source-definition validation and loaded into a warehouse timestamp column. Precisions 29/0, 19/0 and 29/9 had stopped the session with "Field <name>'s precision is invalid" (L-CDI-217). The source's SOQL filter (`readOptions.filterCondition`) may use a semi-join on another object at run time, for example `<lookupField> IN (SELECT Id FROM Account WHERE Name IN ('<a>','<b>'))` (Salesforce refuses a semi-join on the same object as the outer query), but the catalog cannot parse it and drops the source from lineage (L-CDGC-196): prefer a literal list.

### L-CDI-246  REG_EXTRACT returns NULL unless the pattern matches the whole value
**Kind:** GOTCHA · **Proven:** 2026-10-13 · **Evidence:** rows landed with NULL; with `.*` appended the next run extracted the code (2026-10-13)
In the CDI expression language REG_EXTRACT matches its pattern against the whole input, like a full match: a pattern for a leading code, `'^([0-9A-Z]+(-[0-9A-Z]+)+)'`, returned NULL on values that continue after the code, and the same pattern ending in `.*` returned the code as group 1. Test an expression on real values before a run, and backfill rows already loaded with NULL.

### L-CDI-243  Re-importing a mapping under the same GUID renames the task's parameters but keeps the task's description
**Kind:** GOTCHA · **Proven:** 2026-10-12 · **Evidence:** read-back of the task before and after an OVERWRITE redeploy and a v2 POST (2026-10-12)
When a mapping is re-imported with OVERWRITE under its existing GUID and its transformations have new names, the mapping task re-derives its `parameters[]` from the new names (`$<NEW_NAME>$`) and keeps their connections, objects and operations. Its pre- and post-processing commands are kept too. The task's `description` and `shortDescription` are not updated: Explore keeps showing the old text. To change them, GET `/api/v2/mttask/<id>`, drop orgId/createTime/updateTime/createdBy/updatedBy, set `description`, POST the body back to the same id, then read it back.

### L-CDI-247  CDQ deduplicate/decision transformations do not run on the Informatica Cloud Hosted Agent: libIDQDecisionZTransform.so
**Kind:** WALL · **Proven:** 2026-10-16 · **Evidence:** Cutover runs failed with the quoted error; the same tasks succeeded on a Secure Agent from the next run on (2026-10-16)
Mapping tasks that embed CDQ Deduplicate or decision-type DQ assets failed on the hosted runtime with "EP_13236 Could not open the following dll: [libIDQDecisionZTransform.so]. ... cannot open shared object file: No such file or directory" (the DTM terminated, 0 rows). Plain Rule Specification transformations did run there. Bind the dedupe/decision tasks to a Secure Agent that has the Data Quality service; they then ran with the same row counts as before the move. Newer evidence: L-CDI-279.

### L-CDI-248  Databricks target full reload: set writeDisposition Truncate in the writer attributes; the truncate flag, Pre SQL and create-at-runtime all append
**Kind:** GOTCHA · **Proven:** 2026-10-16 · **Evidence:** Reruns of two tasks kept 5 and 3 rows with writeDisposition Truncate; earlier runs had appended (2026-10-10, 2026-10-16)
A Databricks target with the mapping's truncate flag, a TRUNCATE in Pre SQL or other operation attributes still appended on every run, and a target created at run time also appends on reruns (L-CDI-166). Put `writeDisposition` = `Truncate` in the target adapter's operation and runtime attributes (generated IMF: `oprRuntimeAttributes` and `runtimeAttributes`, the same pair as the Snowflake presql fix, L-CONN-106); reruns then replaced the table. Count rows after the second run, because an appending target looks right after the first. Refines L-CDI-166.

### L-CDI-249  The Databricks connector sends a source custom query verbatim: a Unity Catalog metric view can be read with MEASURE() directly
**Kind:** FACT · **Proven:** 2026-10-21 · **Evidence:** Test task read 3 rows (total + 2 channels) from the metric view and published them; values matched the warehouse's own answer (2026-10-21)
A mapping source on the Databricks connector with a custom query such as `SELECT <dim>, CAST(MEASURE(`<measure>`) AS DOUBLE) AS <col> FROM <catalog>.<schema>.<metric_view> GROUP BY ALL` (also a UNION ALL of a total and a per-dimension query) ran unchanged: the session log line `DATABRICKSDELTA_10000 [INFO] SQL QUERY:` shows exactly the text sent, and no wrapper view, table or staging object was created in Databricks. Declare the measure as a DOUBLE/FLOAT port (cast DECIMAL measures, see the Hyper limit when the target is Tableau). Reading the metric view as a plain object (SELECT *) does not evaluate measures, so use the custom query.

### L-CDI-250  A Data Transfer (copy-data template) task caches the source column metadata: recreate it after a source type change
**Kind:** GOTCHA · **Proven:** 2026-10-10 · **Evidence:** Type change in the source only took effect after the task was recreated (2026-10-10)
Mapping tasks built on the Add-On Bundle copy-data template (`dsst__copy_data_new_tgt`) kept the source columns and types they were created with. After a source column changed type, the task kept writing the old type until the task was deleted and created again. Recreate (or re-fetch the fields of) such a task whenever a source changes shape, and drop a create-at-runtime target table that carries the old schema (L-CDI-166).

### L-CDI-251  Tableau V3 target in a generated mapping: Overwrite, a .hyper file name, project and data source in both attribute sets, Tableau native types
**Kind:** RECIPE · **Proven:** 2026-10-19 · **Evidence:** Each quoted failure was a real run; the corrected task published the data source and a Hyper read-back matched (2026-10-19, 2026-10-21)
Writer attributes, in both the operation and the runtime attribute sets: `targetOperation` = `Overwrite`, `project` = <Tableau project>, `dataSource` = <published data source name>, `extractFileName` = `<name>.hyper`, with `createTarget` true. Field nativeTypes are Tableau's (`text`, `double`, ...). The failures on the way: nativeType `string` -> "The native type system does not support the data type [string] in the native metadata field"; a file name without the extension -> "[FATAL] The name specified for the Extract file must have a .hyper extension."; `Replace` -> "Exception occurred while converting [targetOperation$] value [Replace] to [Parameter]". With an empty workbook name the writer publishes a data source; the session log (`TABLEAUV3_10000`) echoes Target Operation, File name, Project and Data source, then 'Publishing the Extract ... is successful.' Newer evidence: L-CDI-302, L-CDI-303.

### L-CDI-254  Salesforce field precisions in a generated mapping: date is 10, datetime is 24; take them from the IDMC field metadata
**Kind:** GOTCHA · **Proven:** 2026-10-16 · **Evidence:** Rebuilt Salesforce-sourced tasks validated and ran after switching date fields to precision 10 (2026-10-16)
When a mapping is generated without the designer, a Salesforce `date` field must be declared with precision 10 (scale 0) and a `datetime` field with precision 24 (L-CDI-245); the generic date/time default of 29 that other connectors use was not accepted for Salesforce date fields. Read each field's precision and scale from the connection's own field metadata (the values the designer would import) instead of a type-wide default, and keep the Salesforce nativeType (date, datetime, currency, picklist). Refines L-CDI-245.

### L-CDI-255  PostgreSQL fields in a generated mapping take the connector's type names: bigint, not the int8 alias
**Kind:** GOTCHA · **Proven:** 2026-10-16 · **Evidence:** Rebuilt PostgreSQL-reading tasks ran after int8 -> bigint (2026-10-16)
Generated PostgreSQL source, lookup and target fields need the native type names the IDMC PostgreSQL connector reports: `bigint` for a 64-bit integer column, not PostgreSQL's catalog alias `int8` (likewise the connector's own spellings such as `character_varying` and `timestamp_with_time_zone`). `int8` was not accepted for those fields; `bigint` ran. Copy native types from a designer-built mapping or the connector's field metadata, never from information_schema/pg_catalog short names.

### L-CDI-256  A mapplet package's documentType is exactly 'DMAPPLET': 'MAPPLET' is rejected, and the import assigns a new id
**Kind:** FACT · **Proven:** 2026-10-04 · **Evidence:** Generator deploys proven live (mapplet imported, resolved by name, called by a mapping that ran) (2026-10-04)
A synthesized mapplet is a `<name>.DMAPPLET.zip` holding `mappletTemplate.json`, with `documentType` "DMAPPLET" (case-sensitive); "MAPPLET" is rejected by IDMC. A REUSE import assigns the mapplet a new id, so look it up by name in its folder after the import and use that id in the calling mapping's mapplet transformation and in its package `assets` entry (type DMAPPLET, path /Explore/<project>/<folder>); an OVERWRITE re-import keeps the FRS GUID.

### L-CDI-257  An unconnected lookup called with a NULL argument can return the value of a NULL-key row
**Kind:** GOTCHA · **Proven:** 2026-10-28 · **Evidence:** 44 records with no source key all received one previous value from a cached query lookup (Use First Value) whose key column held NULLs; the next run gave 44 golden records the same identifier (2026-10-28)
`:LKP.<lookup>(<key>)` with `<key>` NULL returned the value stored on a row whose key column is NULL, so every record without a key got that one value. Guard the call (`IIF(ISNULL(<key>), NULL, :LKP.<lookup>(<key>))`), add `WHERE <key> IS NOT NULL` to the lookup query, and give records that have no natural key a stable stand-in key (for example `'NOID-' || MD5(<email>)`) so they can still be looked up on the next run.

### L-CDI-258  A previous-row comparison after a Sorter did not mark repeats on the runtime: decide ties set-wise with a ranking lookup
**Kind:** GOTCHA · **Proven:** 2026-10-29 · **Evidence:** Sorter on the claimed value, then an Expression with v_taken = (value = v_last) followed by v_last = value: 43 groups claiming one value all kept it, while a running counter (v_seq = v_seq + v_new) in the same Expression incremented correctly; a query lookup ranking with ROW_NUMBER fixed it (2026-10-29)
Do not rely on comparing a row with the previous row to break ties between groups. Compute the winner per contested value in the warehouse instead: a query lookup `SELECT K, W FROM (SELECT K, GROUP_KEY AS W, ROW_NUMBER() OVER (PARTITION BY K ORDER BY <size> DESC, GROUP_KEY) AS RN, COUNT(*) OVER (PARTITION BY K) AS C FROM (...)) WHERE RN = 1 AND C > 1`, then `IIF(NOT ISNULL(:LKP.<winner>(K)) AND :LKP.<winner>(K) <> GROUP_KEY, <new value>, K)`. Only contested keys are cached, so the lookup stays small. A running counter variable is still fine for numbering.

### L-CDI-259  In a multi-flow mapping (flowOrder), an earlier flow saw a table empty that a later flow of the same mapping rewrites
**Kind:** GOTCHA · **Proven:** 2026-10-29 · **Evidence:** A consolidated match + merge mapping whose match flow looked up the previous identifiers in the cross-reference table that the merge flow writes with truncate gave all 167,440 records new identifiers; with the previous identifiers read from the append-only merge log instead, 167,430 of 167,440 kept theirs and the rest were logged rule changes (2026-10-29)
Targets of a mapping are emptied when the mapping starts, not when their flow runs, so a source or lookup in an EARLIER flow that reads a table a LATER flow truncates finds it empty. Flows may read what earlier flows wrote (that worked: a hierarchy flow read the golden table the flow before it wrote). When consolidating dependent steps, read 'last run' state from a table the mapping only appends to (a merge log: latest event per source key), or keep the steps in separate mappings. Check by fingerprinting every output table before and after the consolidated run; BigQuery time travel (copy `<table>@<epoch-ms>` over the table) restores a bad run.

### L-CDI-260  A large aggregation that runs on the Hosted Agent can fail on a small Secure Agent: keep the step that needs the Secure Agent in its own mapping
**Kind:** PERF · **Proven:** 2026-10-29 · **Evidence:** Merging an aggregation over about 720,000 groups with a deduplicate step forced the mapping onto a small Secure Agent; it failed with TE_7041 'Aggregate Error: Failed to allocate'; split back, the aggregation ran on the Hosted Agent (2026-10-29)
A mapping runs on one runtime. When one flow needs the Secure Agent (cleanse or deduplicate need its Data Quality engine) and another does heavy aggregation, putting them in one mapping moves the aggregation onto the Secure Agent's memory. Keep the Data Quality-engine step in its own small mapping and leave memory-heavy flows on the Hosted Agent.

### L-CDI-261  BigQuery SQL in a lookup query: a CTE named like the returned column returns the whole row
**Kind:** GOTCHA · **Proven:** 2026-10-29 · **Evidence:** A lookup query ending in `SELECT KEY, R FROM r` (CTE r, column R) returned a STRUCT per row instead of the text (2026-10-29)
BigQuery names are case-insensitive, so a CTE `r` and a column `R` collide and `R` resolves to the whole row of `r`. Give CTEs names that are never column names (`res`, `cand`), and run every lookup query once in BigQuery before deploying the mapping.

### L-CDI-262  JDBC V2 writer: rows per INSERT = min(writer batch size, rows per DTM block); wide ports and the 200-row default make a ClickHouse write storm
**Kind:** PERF · **Proven:** 2026-11-01 · **Evidence:** query_log written_rows per INSERT measured before/after on the same target: 60-82, 200, 2,108, ~9,957 (2026-11-01)
A JDBC V2 target sends one INSERT per writer batch, and a batch never spans DTM buffer blocks. With the writer batch size left at 0 the writer uses 200 rows; with a large batch size the block caps it: rows per block = `Default buffer block size` / declared row width (string precision x 2 bytes). A mapping that carried a 128K-character JSON port wrote 60-82 rows per INSERT (about 52 inserts per second, about 150 rows per second per task, a new ClickHouse part per insert). Fix: keep ports narrow (no raw payload through the DTM unless needed), set the task session properties `DTM buffer size` (1-2 GB) and `Default buffer block size` (32-64 MB) on the v2 task (`sessionProperties`), and set the target's `writeOptions.batchSize` (10,000-20,000). Rows per INSERT went 200 -> 2,108 (wide golden rows) and about 10,000 (narrow cross-reference rows). Raise the DTM Java heap at the same time (next lesson).

### L-CDI-263  Attribute-level survivorship in one sorted Aggregator: FIRST(value, condition) per attribute group
**Kind:** PATTERN · **Proven:** 2026-11-01 · **Evidence:** Golden-record mapping run green on a few million observations -> slightly fewer masters; lineage ids checked against source rows
Read the observations ordered by master id, newest first (warehouse ORDER BY), set the Aggregator to Sorted Input (`inputSorted=true` + advanced `Sorted Input=true`) grouped by the master id, and give each golden attribute `FIRST(value, NOT ISNULL(value))` (text: `LENGTH(LTRIM(RTRIM(v))) > 0`) = most recent non-null value. Use the same anchor condition for companion fields so they come from one observation (`FIRST(tax_year, NOT ISNULL(assessed_value))`), and `FIRST(record_id, <anchor>)` for per-group field lineage. The Aggregator streams (no group cache): a few million masters from as many observations in 13 min including rule specifications and two targets. Non-grouped input ports leave the Aggregator with the last row's value, so name every output port distinctly.

### L-CDI-264  ClickHouse through JDBC V2: read DateTime as text, write UInt16 from an integer port and UInt64 from decimal(20,0)
**Kind:** GOTCHA · **Proven:** 2026-11-01 · **Evidence:** Each error reproduced on one task, then cleared by the change (2026-11-01)
A custom-query source column of type DateTime64 failed at the first row: 'Error Occured for Transformation - <source> while writing the data to DTM Buffer - Timestamp format must be yyyy-mm-dd hh:mm:ss[.fffffffff]'. Select `toString(toDateTime(x, 'UTC'))` as a 19-character string and convert with `TO_DATE(s, 'YYYY-MM-DD HH24:MI:SS')` in an Expression. On the target side a ClickHouse UInt16 column needs an integer (INT32) port: a bigint port fails 'java.lang.Long cannot be cast to java.lang.Integer'; a UInt64 column takes decimal(20,0) (a bigint port fails 'java.lang.Long cannot be cast to java.math.BigDecimal'), and a non-nullable column rejects NULL ('Cannot set null to non-nullable column'). Float32 takes a double port. Newer evidence: L-CDI-291.

### L-CDI-265  $CurrentTaskId and $CurrentRunId are substituted inside expression literals; an in-out parameter is not
**Kind:** WORKS · **Proven:** 2026-11-01 · **Evidence:** Run lineage read back from target rows; the quoted parameter wrote '$$p_scope_list' into a manifest (2026-11-01)
`'run/' || '$CurrentTaskId' || '/' || '$CurrentRunId'` in an Expression and the same tokens in a custom query arrive as the v2 task id and the numeric run id, so every row can carry real run lineage without hard-coded ids. An in-out parameter behaves differently: inside a custom query `$$p_scope_list` is replaced anywhere (also inside quotes), but in an Expression a quoted `'$$p_scope_list'` stays literal text; reference it unquoted (`'...' || $$p_scope_list || '...'`). The task exposes each in-out parameter's `currentValue` (v2 GET mttask -> edit `inOutParameters[].currentValue` -> POST), so one mapping serves any scope (one region, a list, ALL) without copies.

### L-CDI-266  Generate a Verifier (address verification) transformation headless
**Kind:** ROUTE · **Proven:** 2026-11-01 · **Evidence:** Generated mapping imported valid=true and ran to completion (2026-11-01)
TmplVerifier (advanced `version`=R37) with groups `Input group:` (input, all-fields rule) and `MappletOutputTx_Output` (output); `verifierAssetId` = '@<asset frs id>'; `inputFields` and `outputFields` are VerifierFields lists of TxField named after the asset's ports (Address_Lines_1 128, Postal_Code_1 15, ...); `inputGroups` = one TmplVerifierGroup `Input group:` with fieldMappingMode MANUAL and a FieldMapping of TxFieldMapping {name = incoming field, txField = reference to the input TxField}. Incoming fields pass through to the output group. List the asset in the package as type VERIFIER. Shape harvested from a designer-built mapping; imported valid and ran.

### L-CDI-267  JDBC V2 reading ClickHouse fails 'Premature EOF' when back-pressure stalls the reader longer than ClickHouse's 30 s HTTP send timeout
**Kind:** ERROR · **Proven:** 2026-11-01 · **Evidence:** Two runs died after 1.9M and 9.9M rows with the server-side timeout in system.query_log; the same read passed after the proxy temp limit was raised from 512 MB (2026-11-01)
A long sorted read (millions of rows) into a mapping whose writer is slower than the reader stalls the JDBC V2 reader once the DTM buffers are full. If a stall lasts longer than ClickHouse's `http_send_timeout` (30 s; it applies only in the server's default profile and needs a server restart to change, so a query SETTINGS clause does not help), ClickHouse aborts the query ('Timeout exceeded while writing to socket (..., 30000 ms)' or 'Broken pipe') and the session fails minutes later with `java.io.IOException: Premature EOF` after processing what was already buffered. Fix: read through a buffering reverse proxy (nginx `proxy_buffering on` with a `proxy_max_temp_file_size` larger than the result, on a big disk) so the database can always send at full speed, or keep the downstream as fast as the read. nginx sizes take only k/m suffixes here: `200g` is rejected and the proxy crash-loops; write `204800m`. Newer evidence: L-DQ-148.

### L-CDI-268  ClickHouse MATERIALIZED columns are evaluated without short-circuit on INSERT: if(cond, cheap, heavy) pays for heavy on every row
**Kind:** PERF · **Proven:** 2026-11-01 · **Evidence:** Null-engine benchmark of 40,000 captured rows: 9.3-11 s with the columns, 0.05 s without; per-expression SELECT timings 5.6 / 2.8 / 2.9 / 0.1 s (2026-11-01)
A MATERIALIZED expression `if(record_kind = '<kind>', <empty>, <heavy array/lambda expression>)` still evaluates the heavy branch for every inserted row: the INSERT default-evaluation path does not use lazy (short-circuit) execution, and `short_circuit_function_evaluation = 'force_enable'` at query or session level does not change it (an arrayMap in the skipped branch still raised 'Arrays passed to arrayMap must have equal size'). The same expression in a SELECT is lazy (0.16 s instead of 2.8 s for 40,000 rows). Measured on a JDBC V2 target: four completeness columns built from arrays over ~660 fields took 11.4 s of a 15 s single-threaded insert of 40,000 rows, which made the target's insert CPU the bottleneck of every writer lane. Keep heavy derivations out of MATERIALIZED columns of high-volume tables, or compute them in a SELECT path (for example a materialized view over a Null-engine landing table, inserting with insert_allow_materialized_columns = 1; not yet proven).

### L-CDI-269  A ClickHouse Join-engine table cannot be a source query; read its persisted data file instead
**Kind:** GOTCHA · **Proven:** 2026-11-01 · **Evidence:** file() read returned 109,151 and 29,544 rows = total_rows of both Join tables; joinGetOrNull over the base table returned 109,096 (2026-11-01)
`SELECT ... FROM <join table>` on a multi-key ClickHouse Join engine (`Join(ANY, LEFT, k1, k2)`) fails in the mapping's source with 'Code: 121 ... Unsupported JOIN keys of type hashed in StorageJoin (UNSUPPORTED_JOIN_KEYS)', also with an explicit column list. Its rows persist in `<data_path>/<n>.bin` (from system.tables.data_paths) as compressed Native: decompress with `clickhouse compressor --decompress < 1.bin > <name>.native`, place it under user_files and read `file('<dir>/<name>.native', 'Native', '<column structure>')`; the row count equals system.tables.total_rows. Reading through joinGetOrNull over a key source misses keys whose base rows changed after the Join was built.

### L-CDI-270  formatRowNoNewline('JSONEachRow', *) silently picks up a same-named alias of the same SELECT
**Kind:** GOTCHA · **Proven:** 2026-11-01 · **Evidence:** Reconciliation of a 587-row table: equal counts, identical hash sets after the fix, checksum 10006624177009380784 vs 5883335861068302957 before it (2026-11-01)
In ClickHouse a `*` inside an expression expands to the table's columns, but a column whose name equals an alias defined in the same SELECT resolves to that alias. `SELECT lower(hex(SHA256(formatRowNoNewline('JSONEachRow', *)))) AS h, count() AS n FROM t GROUP BY h` on a table with a column `n` hashed count() instead of the column: same row count, different checksum, no error. Build the row JSON in an innermost subquery over the bare table with an alias no table uses (`SELECT ... AS __x_h FROM t`) and aggregate one level up. A same-named alias that the row expression itself depends on fails loudly ('cyclic aliases'), so only the silent case needs this guard.

### L-CDI-271  A v2 mapping task keeps its own copy of the mapping's fixed target object
**Kind:** FACT · **Proven:** 2026-11-01 · **Evidence:** Lane task GET showed targetObject on the TARGET parameter (2026-11-01)
GET /api/v2/mttask/<id> lists each non-parameterized target in `parameters[]` (type TARGET) with `targetObject` = '<schema>/TABLE/<table>' and its connection id, copied when the task was created. Changing the target object of a mapping that already has run-lane tasks therefore means updating or recreating every dependent task (and an OVERWRITE import may fail while it deploys changes to them). Decide target objects before cloning lanes, or parameterize the target.

### L-CDI-272  A big sorted ClickHouse read for a sorted-input Aggregator: external sort alone still hits the memory cap; shrink merge blocks and shard by hash
**Kind:** PERF · **Proven:** 2026-11-01 · **Evidence:** 8 group runs x 3 tries failed in MergeSortingTransform; the same 7.4M-row read passed at 8.5 GB with the smaller blocks; sharded runs followed (2026-11-01)
A golden-record source that ORDER BYs 6-9M wide rows failed every time with 'Query memory limit exceeded ... While executing MergeSortingTransform' at a 10 GB per-query cap, although max_bytes_before_external_sort (2 GB) was set: the merge of the spilled runs keeps one block per run in memory. `max_block_size = 8192` plus `prefer_external_sort_block_bytes = 4194304` brought a 7.4M-row read to 8.5 GB peak (passes a 12 GB cap); the robust bound is a hash shard parameter on the mapping (`cityHash64(id) % N = k` in every CTE, k/N an in-out parameter) so each run sorts at most about 2-4M rows. Shard on the master id so a master and all its observations land in the same run.

### L-CDI-273  Fix a replacing-engine table with Array/Map columns through CDI: conform in transformations, write a scalar staging batch, merge with the target's Post SQL
**Kind:** PATTERN Â· **Proven:** 2026-11-02 Â· **Evidence:** 1,790-row registry: one run, 1,790 rows in/out, 17 s; 221 scopes and 258 statuses conformed, 12 shared names disambiguated, all rows re-stamped with the real mapping/task/run ids; Array/Map columns identical before and after (1,790 / 570 / 570) (2026-11-02)
A replacing table (ClickHouse ReplacingMergeTree by version) needs whole rows on every fix, but six of its columns were Array/Map types that a JDBC V2 writer cannot round-trip, and a partial insert would have reset them to defaults. Pattern that worked: the Source only selects and orders; Expression / Aggregator + sorted Joiner / Rule Specifications / Expression conform the values and add steward reason codes and IDMC lineage; the target writes one scalar row per key to a staging table (version = run start in epoch seconds); the target's Post SQL (writerAttrs rt 'Post SQL' plus the transformation's Post SQL property) runs one INSERT INTO <table> SELECT s.* REPLACE (f.col AS col, ..., f.version AS version) FROM <table> AS s FINAL INNER JOIN (latest staging batch) AS f USING the key WHERE f.version > s.version, so the complex columns never leave the warehouse. The staging table keeps every batch (the IDMC user had SELECT/INSERT but no TRUNCATE), and the merge picks max(version). Take an undo copy first. A same-source self-join needs Sorters on both sides and a sorted Joiner, or the session hangs (L-CDI-106).

### L-CDI-274  Flat-file target in a generated mapping: name the new file and declare the upstream fields; the run creates it and every run overwrites it
**Kind:** RECIPE · **Proven:** 2026-11-03 · **Evidence:** FF -> FF passthrough 189/189 rows in 8 s, session log 'Writing output to: <dir>/<file>.csv'; re-run: the file still held header + 189 rows; the same mapping without createTarget created its new file, 189/189 (2026-11-03)
A target on a CSVFile flat-file connection needs only `object` = the file name (written in the connection's directory on the Secure Agent) and its fields declared in the spec, the same as the upstream fields. A file that does not exist yet has nothing to browse or describe before the first run, so do not look it up: the first run creates it, with or without `createTarget`. The writer puts a header line first and double-quotes every value; a re-run overwrites the file (one header, no appended rows), unlike a create-new-at-runtime table target in Insert mode (L-CDI-166). The generator writes its generic target adapter (it has a flat-file branch for sources only) and the engine picks the file writer from the connection. A connector the docs describe only as a source is not proof that it cannot be a target: build one small passthrough and run it.

### L-CDI-275  Feed a Structure Parser from the document itself instead of a listing file: read the PDF as a header-less flat file, keep one row with a filter (the row limit does not apply to flat-file reads), and pass a fixed path
**Kind:** RECIPE · **Proven:** 2026-10-26 · **Evidence:** with rowLimit 1 a 1,782-line PDF read every line and the parser ran for more than 15 minutes; with the header-line filter it parsed once, and lineage showed the storage file upstream of the mapping (2026-10-26)
To make the document the lineage source and drop the helper CSV, make the flat-file source object the PDF itself. Give it code page ISO-8859-1 (every byte is a valid character), no header (headerLineNo 0, first data row 1) and `retainMetadata` true, so the run keeps the design-time column instead of re-reading field names from a header-less file. The source's `readOptions.rowLimit` = 1 was IGNORED for the flat-file read. All 1,782 lines of the PDF were read, and each one sent the file through the CLAIRE Structure Parser again, a hang of more than 15 minutes. Keep the one row with a filter instead: advancedFilterCondition `SUBSTR(<column>, 1, 5) = '%PDF-'` (the PDF's first line). Give the Structure Parser a constant file path from an Expression. The mapping's IICS reference is then the PDF, which maps onto the cataloged storage file. Re-import with OVERWRITE to keep the mapping id, so the task and the taskflow stay unchanged.

### L-CDI-276  In an advanced-mode (Spark) mapping, CLAIRE could not read a PDF set up in the designer: the Discover Structure model picker never enables Select
**Kind:** WALL · **Proven:** 2026-10-26 · **Evidence:** an empty advanced-mode mapping created and exported to read its markers; its source set up with the Document format, where Discover Structure never enabled Select for the PDF model (2026-10-26)
Take an advanced-mode mapping whose source is a data-lake connection with the Document or CLAIRE format. The 'Discover Structure' step lists the PDF model, but its Select button never becomes enabled, so the source cannot be finished in the designer. Treat CLAIRE parsing of PDFs in advanced mode as blocked in the UI. The working path is a standard mapping on a Secure Agent, with a Structure Parser over a file on the agent (L-AGENT-104, and the flat-file PDF read). For headless generation: an advanced mapping exports as an AtScaleDTemplate document (documentType AT_SCALE_MAPPING) with the annotation mapping_type = CDIE, and the Document format outputs the ports Text, FilePath, FileType and FileName.

### L-CDI-277  Advanced (Spark) mode for document parsing: the limits the October 2026 documentation sets
**Kind:** FACT · **Proven:** 2026-10-26 · **Evidence:** documented: Data Integration Advanced Clusters guide and the connector and lineage guides, October 2026, read while planning an in-place PDF read on a 2 vCPU / 16 GB agent (2026-10-26)
Check these documented limits before you plan CLAIRE document parsing on an advanced cluster. A local advanced cluster needs at least 8 vCPU, 32 GB memory and a 100 GB root disk (20 GB for /var, 30 GB for /tmp). A resource shortfall fails the advanced job and also the jobs already running on that agent. The 'Document' format returns only the file's text (it is meant for chunking and embeddings) and applies no CLAIRE model. The 'Claire' (Discover Structure) format outputs nested fields, which a Rule Specification does not accept, so a Hierarchy Processor must flatten them first. In advanced mode a Structure Parser cannot give relational output. The catalog extracts advanced mappings only with these transformations: Mapplet, Aggregator, Sorter, Expression, Filter, Joiner, Lookup, Normalizer, Rank, Router, Sequence, Union and AccessPolicy. A Structure Parser or Rule Specification step can therefore drop out of lineage. When lineage must show the parse and the rules, or the agent is small, parse in a standard mapping on a Secure Agent (L-AGENT-104).

### L-CDI-278  Merge two mappings into one by transplanting transformations between exports: re-point every $$class by class name and give fresh $$IDs
**Kind:** RECIPE · **Proven:** 2026-10-26 · **Evidence:** Two merged mappings imported, validated and ran SUCCESS: 29 rows each run, 95-167 s, with the task and taskflow ids unchanged (2026-10-26)
Every IMF document numbers its classes in its own `metadata.$$classInfo`. So a transformation copied from another mapping's export keeps `$$class` numbers that mean something else in the target document. To transplant: deep-copy the node, map each `$$class` number to its class name in the source document, then to that name's number in the target document, adding a new entry (max index + 1) when the target lacks the class. Then give every object a fresh `$$ID` and update the `##ID` references to match. Rename field references to the new upstream's port names (for example the parser's ports instead of the middle table's columns). Drop the intermediate target and its TmplLink, and link the last kept transformation to the first transplanted one. Then refresh the DTEMPLATE zip: the bin entry's size in `fileRecord.json`, `mappingTemplate.json` (description, and references[] for every model and connection still used, L-MIG-076) and the SHA-256 lines in `exportPackage.chksum`. Import with OVERWRITE under the id of the mapping you keep, so its task and the taskflow step run the merged mapping unchanged. Proven by merging a parse-to-table mapping and a rules mapping (3 rule specifications and a status expression) into one parse, rules and target mapping.

### L-CDI-279  CDQ cleanse, deduplicate and decision transformations do not run on the Informatica Cloud Hosted Agent (EP_13236 libIDQTokenStandardiserZTransform.so / libIDQDecisionZTransform.so); rule specifications do
**Kind:** GOTCHA · **Proven:** 2026-10-28 · **Evidence:** cleanse mappings failed on the hosted runtime with the quoted library and ran on a Linux Secure Agent; 9 rule specifications ran on the hosted runtime (2026-10-28)
Extends L-CDI-247, which covered deduplicate and decision steps (libIDQDecisionZTransform.so), to cleanse. A mapping task with a CDQ cleanse asset (remove spaces, convert case) failed on the hosted runtime with EP_13236 'Could not open the following dll: [libIDQTokenStandardiserZTransform.so]': the hosted Data Integration Server lacks the Data Quality engine libraries. Rule Specification transformations in the same project ran on the hosted runtime. Keep cleanse, deduplicate and decision steps in their own small mappings, bound to a Secure Agent with the Data Quality service (L-AGENT-103). Leave memory-heavy flows such as big aggregations on the hosted runtime, because a small agent can run out of memory on them (L-CDI-260). Refines L-CDI-247.

### L-CDI-280  Mapping-task names refuse parentheses (APP_13500): the mapping imports, then the task create fails
**Kind:** GOTCHA · **Proven:** 2026-10-28 · **Evidence:** a mapping named with '()' imported, then its task create failed with APP_13500; renamed without parentheses, the task was created and ran (2026-10-28)
A generated mapping whose name contained '(...)' imported without complaint, but creating its mapping task failed with APP_13500, so the deploy script stopped halfway: the mapping existed and the task did not. Each object type has its own name rules: connections refuse parentheses with APP_10500 (L-CONN-124), FRS renames refuse them with FRS_082 (L-MIG-080), and folders refuse a dot (L-MIG-079). Normalise every generated name to letters, digits, spaces and hyphens before the first import, and check that each task exists after a deploy.

### L-CDI-281  Large cached lookups on a small Secure Agent fail with 'No space left on device': cut port precisions and filter the lookup query
**Kind:** GOTCHA · **Proven:** 2026-10-28 · **Evidence:** lookup-heavy mappings failed with 'No space left on device' on an agent with about 6.5 GB free; with smaller precisions and filtered lookup queries they ran (2026-10-28)
A Secure Agent with only about 6.5 GB of free disk failed mappings with 'No space left on device' while it built lookup caches. A cache is sized from the declared precision of the cached ports times the rows, not the actual data width, so wide string ports multiply the disk a lookup needs. Fix: declare small precisions on the lookup ports, and select only the columns and rows you need in the lookup query (`WHERE <key> IS NOT NULL` also guards against the NULL-key trap, L-CDI-257). Keep the agent's cache directory on a filesystem with headroom (L-AGENT-107).

### L-CDI-282  An Update through a target object that declares only some of the table's columns leaves the other columns untouched
**Kind:** FACT · **Proven:** 2026-10-28 · **Evidence:** a 3-column Update target written into a wide table: the other columns kept their values after the run (2026-10-28)
Proven on BigQuery V2. A mapping wrote an Update, keyed on the primary-key column, through a target object that declared only 3 of the table's columns, and the other columns kept their values. Use this to write a few derived fields (an id, a flag) back into a wide table without carrying every column through the mapping. Declare the key as the update key. The task keeps its own copy of the target object (L-CDI-271), so check the task again after you change the target definition. Upsert semantics differ by connector (L-CDI-207), so test on the target you use.

### L-CDI-283  Drive a resumable verification or enrichment sweep from 'already has a result for this input', never from a cursor kept in deletable control rows
**Kind:** PATTERN · **Proven:** 2026-11-01 · **Evidence:** Per-run key ranges before and after the control-row delete; duplicate assessment counts; unique-fingerprint count (2026-11-01)
Two scheduled address-verification workflows read their keyset cursor back from the latest committed control (run-manifest) row. When those control rows were deleted, both restarted from the first key and re-verified addresses they had already done (duplicate assessments), repeating metered calls, and their schedules kept firing because nothing else stopped them. Select the next batch by an anti-join to the stored results on an input fingerprint (normalized address hash) plus the reference-data version, and re-verify only when the inputs that matter change (for example the 3-digit ZIP prefix or the house number). Dedupe inputs by fingerprint before calling: repeated inputs are common in address data. Unbind the schedules of a pipeline you retire (L-CDI-075), including ones that live in another project. Newer evidence: L-IPU-064.

### L-CDI-284  A mapping task's $Source$.customQuery only takes effect when the mapping's source query is a parameter; on a fixed-source mapping the run executes the mapping's own query
**Kind:** GOTCHA · **Proven:** 2026-11-01 · **Evidence:** Test runs of one capture task before and after its mapping gained an in-out query parameter; audit of a 357-mapping generated build (2026-11-01)
Editing `$Source$.customQuery` on a v2 mapping task (GET, change, POST /api/v2/mttask/<id>) works for the copy-data template because its source is a parameter (L-CDI-021). On a mapping whose source query is fixed in the mapping, the task's copy can be edited without an error but the run reads the mapping's query, much like the fixed target object a task copies (L-CDI-271). This is how a generated build ended with one mapping per source table (357 mappings for 354 tasks). For one mapping over many sources, make the query an in-out parameter used as the Source query (for example `$$SRC_SQL`) or a parameterized source object, then vary it per run (the task's currentValue, L-CDI-265, or a parameter file for long SQL, next lesson).

### L-CDI-285  Per-run SQL longer than about 4,000 characters: put it in a per-task parameter file on the agent, not in the in-out parameter default (REPO_19001)
**Kind:** RECIPE · **Proven:** 2026-11-01 · **Evidence:** Two REPO_19001 task saves; 12 cloned lanes then ran hundreds of capture items, each with its own staged parameter file; task delete-import-recreate after the parameter was added (2026-11-01)
An in-out parameter whose default value is a long SQL statement (about 4K characters and up) makes `POST /api/v2/mttask` fail 403 `REPO_19001` 'An error occurred while saving the Mapping task to the repository.' Working pattern: the mapping's Source query is the in-out parameter `$$SRC_SQL`; the task sets `parameterFileName` = '<lane>.param', which the agent resolves in `<agent_home>/apps/Data_Integration_Server/data/userparameters/`; the file holds one line `$$SRC_SQL=<the SQL on one line>`. Before each run, install that run's staged file on the agent host (this needs a shell on the host) and fail the item if the install fails, so a lane never reruns the previous SQL. For N lanes, clone the task N times: GET /api/v2/mttask/<base>, drop id, frsGuid, create/update stamps, lastRunTime, orgId, scheduleId and federatedId, pop `parameters[].id`, set a new name and parameterFileName, POST. Start with POST /api/v2/job {taskId, taskType MTT} and poll the activity log by runId. The agent also writes its own `data/parameters/s_mtt_<taskId>.param`; the session-log warning VAR_27062 'Cannot find section for worklet' about it is harmless. When a mapping that already has tasks gains a new in-out parameter, an OVERWRITE import fails while deploying the change to the dependent tasks: delete the task, import, then recreate it (L-CDI-271).

### L-CDI-286  Sharding lanes by a hash of the whole row can drop rows silently: ClickHouse's cityHash64(*) is NULL when any column is NULL
**Kind:** GOTCHA · **Proven:** 2026-11-01 · **Evidence:** Rows missing from hash-sharded capture lanes, found during reconciliation; shards re-keyed on the sort key (2026-11-01)
A lane filter `WHERE cityHash64(*) % N = k` leaves every row that has a NULL in any Nullable column out of all N shards, because the hash of a tuple with a NULL is NULL and `NULL % N = k` is never true. No error is raised and each lane's counts look clean. Shard on a key that is never NULL (the table's sort or primary key, or coalesce each argument), and reconcile the shard totals against the source count before trusting a sharded load. Other engines: check whether the row-hash expression you shard or sample on can return NULL before using it (see L-DQ-099 for a portable sample key).

### L-CDI-287  Classify mapping-task failures by errorMsg before retrying: transport and capacity errors retry, data and permission errors do not
**Kind:** PATTERN · **Proven:** 2026-11-01 · **Evidence:** Census of 1,076 activity-log entries of one project; a resumable lane runner's retry outcomes over hundreds of items (2026-11-01)
In about 1,100 retained activity-log entries of one project the most frequent messages were: 'Aborted by agent disconnection.' 134 (all 62 full runs of one workflow design ended this way, and every running workflow failed in the same second when the agent host rebooted); 'The job failed.' 86 (the linear-taskflow wrapper: read its child entries, L-CDI-061); 'java.io.IOException: Premature EOF' 30 (L-CDI-267); 'stopped by user ... using the API' 20; custom-query errors 15; target write errors 13; the database's 'Too many simultaneous queries (max 32)' 10; null into a non-nullable column 9. Single runs also failed with 'JDBC V2 adapter not available', 'job not found on agent' and 'User does not have permission to execute the asset ...'. A lane runner retried up to 3 times only on: Premature EOF, agent disconnection, too many simultaneous queries, timeouts, connection reset or broken pipe, HTTP 502/503/504, 'not available', 'job not found on agent', 'DTM process terminated' and database memory-limit errors. Cast errors, null-into-non-nullable, constraint violations, permission errors and repository save errors are deterministic: fix them, do not retry. Failed-target-row counts that repeat (60, 72, 12) reveal the writer's batch size (L-CDI-262).

### L-CDI-288  The activity log is not a complete run history: a busy project's log held about 1,000 entries, so counts read from it are lower bounds
**Kind:** FACT · **Proven:** 2026-11-01 · **Evidence:** Activity-log census (1,076 entries, oldest three weeks back) against 563 jobs in the last 24 hours; mttask GET showing maxLogs 10 (2026-11-01)
A full read of `GET /api/v2/activity/activityLog?rowLimit=1000&offset=<n>` returned 1,076 entries reaching back three weeks for a project with 354 tasks that started more than 500 jobs a day, and each v2 task carries `maxLogs: 10` (GET /api/v2/mttask/<id>). Run and row totals taken from the activity log are therefore lower bounds. If you need run history (billing proxies, reconciliation, 'who wrote this row'), write your own ledger at completion: task id, run id, start and end in UTC (the *Utc fields, L-AUTH-014), success and failed rows and error text, and stamp the same run id into the rows written ($CurrentTaskId / $CurrentRunId, L-CDI-265).

### L-CDI-289  Dynamic Mapping Tasks are v3 type BATCH_MAPPING and are read at /batch-mapping/api/v1/dynamictask/<id> on the pod host, without /saas
**Kind:** ROUTE · **Proven:** 2026-11-01 · **Evidence:** GET 200 on two DMT objects, 404 under /saas, 500 CMN_001 for a bogus id; v3 type census; org audit log entry for the create (2026-11-01)
A v3 objects query for type DMAPPINGTASK or DMT returns count 0, exactly like an invented type; the Dynamic Mapping Task type is `BATCH_MAPPING`. `GET https://<pod>.<domain>.informaticacloud.com/batch-mapping/api/v1/dynamictask/<v3 id>` with the session headers returns 200 with name, description, mappingId, mappingDocType MAPPING, runtimeEnvironmentId, scheduleId, state VALID, `groups[]` {groupName, enabled} and `parameters[]` {uniqueName 'Source:p_src_conn', name, txName, type SOURCE_CONNECTION, scope, ...} plus the jobs. The same path under `/saas` answers 404 (HTML), and an unknown id answers 500 CMN_001. Two DMTs in the org had been created headless by importing a v3 package (audit event BATCH_MAPPING.CREATE), each with one group and four jobs, so creation by package works. The documented `POST /batch-mapping/api/v1/dynamictask` and running through the managed MCP server jobmanagement (`run_dynamic_mapping_task`, `get_dynamic_mapping_task_status`) were listed but not exercised. Sub-jobs log as type MAPPING. Whether each DMT job counts separately against a monthly job cap (L-IPU-041) is untested.

### L-CDI-290  Read the real DTM buffers and the generated JDBC V2 SQL from the session log: TM_6660 for pool and block size, DBG_21699 for back-pressure, JDBC_V2_10000 for the exact SELECT and INSERT
**Kind:** FACT · **Proven:** 2026-11-01 · **Evidence:** Three session logs of JDBC V2 tasks (defaults and two tuned configurations) read side by side (2026-11-01)
The session log of a JDBC V2 mapping task states what actually ran: `TM_6660 Total Buffer Pool size is <n> bytes and Block size is <m> bytes` (left at defaults, one task with wide ports got a 22 MB pool and 1.2 MB blocks; with session properties set, 512 MB / 32 MB and 1 GB / 32 MB), `TM_6966 Reducing estimate of the amount of buffer pool memory required` when the request is trimmed, `TM_6187 Session target-based commit interval is [10000]`, and `JDBC_V2_10000 [INFO]` lines with the connection string and the exact SELECT and INSERT the reader and writer issued. `DBG_21699 Waiting for consumer to free buffer block. Please increase the dtm buffer pool size.` from the READER thread means the downstream is slower than the read; on a long read that back-pressure is what precedes the 'Premature EOF' of L-CDI-267. Use block size / declared row width to predict rows per INSERT (L-CDI-262) before changing batch sizes. The start-of-session warnings 'Invalid value false for attribute Truncate Target / Apply Custom Schema' are harmless defaults.

### L-CDI-291  ClickHouse through JDBC V2, unsigned integer targets: UInt16 from an integer port, UInt32 from a bigint port, UInt64 from decimal(20,0)
**Kind:** GOTCHA · **Proven:** 2026-11-02 · **Evidence:** UInt32 dictionary columns (ordinal and order numbers) written from bigint ports in a generated mapping after the integer port failed (2026-11-02)
Adds UInt32 to L-CDI-264. Writing a ClickHouse UInt32 column from an integer (INT32) port failed with an Integer-to-Long cast error; a bigint port works. Together with L-CDI-264 the rule is: UInt16 <- integer, UInt32 <- bigint, UInt64 <- decimal(20,0), Float32 <- double, DateTime read as text. The driver expects the next wider Java type for each unsigned type (Integer, Long, BigDecimal), and the cast error names the type it wanted. Other JDBC drivers map unsigned types differently: read the cast message and give the port that Java type. Keep the full table in the mapping generator's type map so new mappings do not rediscover it. Refines L-CDI-264.

### L-CDI-292  Cap memory and threads inside every lane's source query: uncapped parallel JDBC V2 lanes exhausted the database and killed each other's long reads
**Kind:** PERF · **Proven:** 2026-11-03 · **Evidence:** Server memory limit hit with 11 lanes; 2 of about 70 shard runs failed Code 241; 10 runs failed on the 32-query concurrency limit (2026-11-01 to 2026-11-03)
Eleven capture lanes reading one ClickHouse server without per-query limits drove it to its 64 GiB server memory limit: one lane failed MEMORY_LIMIT_EXCEEDED and another session's long read died with 'Premature EOF' after 9.7M rows. Address-verification shard runs failed 'memory limit exceeded ... 72 GiB' (Code 241) until `SETTINGS max_threads = 4, max_memory_usage = 6000000000` was added to their source SQL. Rules that held: stream on a live production source (no GROUP BY over wide rows), cap memory and threads in the source query, allow external sort and group-by spill (L-CDI-272), and run at most about 3 heavy lanes at once. The database's own concurrency limit is shared by loads, DQ and AV together: 32 concurrent queries on the target produced 'Too many simultaneous queries (max 32)' failures. The query-level caps here are ClickHouse SETTINGS; on other warehouses use the equivalent statement memory limits, resource groups or workload management. Newer evidence: L-MIG-093.

### L-CDI-293  An AI-generated IDMC build of 357 one-off mappings put all logic in SQL strings and typed fake lineage ids into the data
**Kind:** GOTCHA · **Proven:** 2026-11-01 · **Evidence:** 357 mappings / 354 tasks / 149 taskflows; 0 gold rows; replaced by 4 MDM mappings plus 1 ingest mapping with 12 lane tasks (2026-11-01)
A project generated by another coding agent contained 357 mappings, 354 tasks and 149 taskflows (104 loose at the project root): one per source table, chunk and pilot, none parameterized, 16 MB of SQL inside source queries (median 15.6 KB, max 679 KB), and 222 mappings with `_mapping_id`, `_task_id` and even `_run_id` literals typed into their SQL, so the 'lineage' columns in the data named runs that never produced those rows. It also wrote 60-82 rows per INSERT. Review a generated IDMC build before running it: count mappings per purpose, check for parameters, measure source-SQL length, and grep for literal ids; replace with a few parameterized mappings whose transformations carry the logic (L-MDM-081) and stamp lineage with `$CurrentTaskId` / `$CurrentRunId` (L-CDI-265). Archive the generated build with its ids kept, because loaded rows reference them. Refines L-MDM-081.

### L-CDI-294  An external REST runner that rewrites each mapping's SQL before every run makes the IDMC export alone unreproducible: keep the runner and its query templates with the assets
**Kind:** GOTCHA · **Proven:** 2026-11-03 · **Evidence:** 4 mapping tasks, every run submitted over REST by an external driver; driver location unknown at handoff time (2026-11-03)
Run history showed that every address-verification run had been started over REST under a user login by a program outside IDMC. That program also rewrote each mapping task's source query (shard and slice predicates) before submitting it. The program was not on the workstation, and reading the VM's scheduler was blocked. So a v3 export plus the activity log showed what ran, but not how to run it again. If a runner owns parameters or SQL, version it with the IDMC assets, name it in the mapping description, and record its path and schedule in the runbook. Better still, move the per-run values into parameter files or in-out parameters that IDMC itself holds (L-CDI-285). Refines L-CDI-102.

### L-CDI-295  Lineage stamps can be checked as data: a rule that rejects anything but a real 20-character IDMC object id found most rows written outside IDMC
**Kind:** WORKAROUND · **Proven:** 2026-11-04 · **Evidence:** Lineage rule mean pass 59.4 % across 8 columns; gold task-id check 23.14 % (2026-11-04)
Rows written by scripts or native SQL steps carried lineage stamps such as `native:<step>` or a `<org>17PENDING00000` placeholder in their mapping-id / task-id columns. A rule specification that answers VALID only for a real 20-character IDMC object id (and blank) and INVALID for `native:...` and PENDING placeholders, bound to those columns in every profile, turned 'is this table really built by IDMC' into a pass rate: 76.9 % of gold rows and 48.5 % of staging rows were not backed by an IDMC object, and 72.1 % of dictionary rows carried the placeholder. Fix by moving those steps into IDMC mappings or recording the real ids; re-run the profile to show movement. Refines L-METHOD-043.

### L-CDI-296  Never run a whole-table ALL_ROWS profile or read on a billion-row registry of blob chunks over JDBC: it is a few hundred GB
**Kind:** GOTCHA · **Proven:** 2026-11-04 · **Evidence:** Over a billion rows; a sample of about 1.5M rows profiled; about 11 GB of base64 over a few hundred chunks (2026-11-02/11-04)
A model registry table held over a billion rows, most of them dataset snapshots and base64 artifact chunks averaging about 25 MB each. An ALL_ROWS profile of it would have pulled a few hundred GB through the JDBC V2 reader. Profile model, version and evaluation rows in full and only a fixed fraction of snapshot and chunk rows (here 1/4096), and before moving such a table through IDMC test whether one JDBC V2 string field carries a chunk that size or whether chunks must shrink. Refines L-DQ-128.

### L-CDI-297  Tune a CLAIRE intelligent structure model headless: flip the model editor's switches inside the model JSON, then create it
**Kind:** RECIPE · **Proven:** 2026-10-07 · **Evidence:** 6 models tuned and created; one parsing mapping then structured 27 of 27 documents (PDF, XLSX, CSV) into 124 rows with 0 Unidentified and 0 failed rows, run twice (2026-10-07)
The model string the structure-discovery service returns (`aModelString`) is `<header>|<base64 of zlib-compressed JSON>`. Decode it, walk `rmodel.script.statementChildren`, and apply the editor's own switches before saving: (1) for each top-level details group with `projectToSeparateGroup` = "1", set it to "0" so its fields join the document's row (one row per document; repeating tables of type ARRAY keep their own group, one row per line); (2) for each free-text node (`blob*`, statementType STRING), set `isExport` = "1" and `projectToSeparateGroup` = "0" so the text CLAIRE left out reaches an output port and an Expression can parse it. Re-encode (zlib, base64, same header) and continue the normal create flow (L-CDI-223). This recovered fields the default discovery dropped (vendor id, tax id, remit e-mail, account number, auto-renew) without custom code. Refines L-CDI-223.

### L-CDI-298  A Structure Parser built on a tuned model has record_PK and record_FK ports that are not model nodes: their stored id is the record root's node id
**Kind:** GOTCHA · **Proven:** 2026-10-07 · **Evidence:** KeyError 'record_PK' in the generator; adding both keys with the root's uniqueId produced a package that imported and ran 27 of 27 documents (2026-10-07)
When a mapping generator builds a Structure Parser's output groups from the model's nodes, a tuned model's record group also carries `record_PK` (and `record_FK` on child groups), keys CLAIRE adds per record. They have no node of their own in `rmodel.script`, so a generator that looks every port up by node failed with KeyError 'record_PK'. In a designer-built parser these ports map to the record root's `uniqueId` (the first statementChild of the script), string 255. Add them explicitly with that id when you generate the parser, or the package will not match what the designer produces. Refines L-CDI-230.

### L-CDI-299  SUM(NULL) in an Aggregator fails the run: TE_7002 'constant operand evaluated to NULL not allowed'
**Kind:** ERROR · **Proven:** 2026-10-07 · **Evidence:** Run FAILED with TE_7002; summing the real price port instead ran SUCCESS (2026-10-07)
An Aggregator output written as `SUM(NULL)` (meant as 'no value for this row type') validated but the run failed: `TE_7002 Transformation stopped due to a fatal error in the mapping. The expression [SUM(NULL)] contains the following errors [<<PM Parse Error>> [NULL]: constant operand evaluated to NULL not allowed]`. Aggregate a real port, or emit the null outside the aggregate (for example an Expression after the Aggregator, or `IIF(<cond>, <port>, NULL)` inside SUM over a port).

### L-CDI-300  Splitting a pipeline into many small mapping tasks costs about 30 s of start-up per task in a linear taskflow
**Kind:** PERF · **Proven:** 2026-10-07 · **Evidence:** Two full runs of the 8-step taskflow: 286 s and 260 s, against about 210 s before the split, same outputs (2026-10-07)
Rebuilding a document pipeline as 8 small mappings (one per stage folder, 3 to 10 transformations each, easy to show in the designer) instead of fewer large ones moved the end-to-end time from about 3.5 to about 4.5-4.75 minutes with the same data: each extra task added roughly 30 s of session start-up regardless of rows. Choose the split deliberately: small mappings for readability, few mappings (or a DAG with concurrency, L-MIG-056) for speed. Refines L-MIG-056.

### L-CDI-301  Build a headless mapping with an Oracle target when your generator has no Oracle target type: copy the target shape from one UI-authored native Oracle target
**Kind:** RECIPE · **Proven:** 2026-10-08 · **Evidence:** import valid=true; first run 43,361 rows, 0 failed, 47 s; appended as a taskflow step (the taskflow then costs 4 jobs a run); Oracle matched the warehouse exactly: 111/111 orders, 101/101 items, 25/25 mart rows, 43,359 lines, same money total (2026-10-08)
A mapping generator that only knew warehouse and file targets had no Oracle target shape. Author one throwaway mapping with a native Oracle connector target in the designer, export it, and reshape the generated targets to match its target element and attributes; the import then came back valid and ran. A truncate-and-reload pattern worked: the session log shows `TRUNCATE TABLE <schema>.<table>`, the DataDirect Oracle wire-protocol writer and the Post SQL completing. Stamp every row with a run id, write one run-audit row per run, and verify the load row for row against the source (per key, per item, totals), not by counts alone.

### L-CDI-302  Tableau V3 target: nativeType char_string is accepted but every string column publishes as '0.0'; use text
**Kind:** GOTCHA · **Proven:** 2026-10-19 · **Evidence:** Runs 8 and 9 SUCCESS with grain/channel = '0.0' on all 3 rows, numbers 52/40/100 correct; redeployed with nativeType text, next run published the real labels and the card check passed (2026-10-19)
In a generated mapping whose target is the Tableau V3 connector, string ports declared with nativeType `char_string` (Java type String) validated, ran SUCCESS and published the data source, but every value of those columns in the published Hyper extract read '0.0'; numeric (`double`) columns were correct. Declaring the same ports with nativeType `text` published the real strings. A green run is not proof here: read the published extract back (Hyper API or a Tableau query) and compare it with the source before pointing a dashboard at it, because a filter on the broken text column silently matches nothing and an unfiltered sum shows the wrong total. Refines L-CDI-251.

### L-CDI-303  Tableau V3 target: an invalid targetOperation in the plain attribute is silently ignored, the writer uses Create, and the second run fails 403007
**Kind:** GOTCHA · **Proven:** 2026-10-19 · **Evidence:** Mapping JSON read back with Replace; session log TABLEAUV3_10000 '[FATAL] Utils : Tableau Rest Runner: Error Code: 403007'; adapter class strings list create/append/overwrite; Overwrite runs repeated and overwrote the same data source id (2026-10-19)
Setting `targetOperation` = `Replace` in the writer's operation and runtime attribute sets (without the `targetOperation$` parameter form) raised no error at import or validation; the deployed mapping still showed Replace, but the session ran with Create. The first run published; every later run failed in the 'Tableau Rest Runner' step with Tableau error 403007 because the data source already existed. Putting the same bad value in `targetOperation$` fails fast instead ('Exception occurred while converting [targetOperation$] value [Replace] to [Parameter]'). The adapter only knows create/append/overwrite: use `Overwrite` in both forms, and check the session log line 'Target Operation - ...' (TABLEAUV3_10000) to see what the writer actually used. Refines L-CDI-251.

### L-CDI-304  Starting a mapping task on demand while its scheduled pipeline run is active fails at once with 'The Mapping task failed to run. Another instance of the task is currently running.' and fails the whole lane
**Kind:** ERROR · **Proven:** 2026-11-10 · **Evidence:** activityLog: runs of 1-2 s with state 3 and 0 rows between successful ~2-min runs (11,171 rows); controller alert and 'run ... FAILED (7 tasks)' two minutes later
To beat a latency target, extra runs of a golden-record mapping task were started with `POST /api/v2/job` (taskType MTT) whenever a new record landed. When the pipeline's own run was already in progress, the extra run ended in about 1 s with state 3, 0 rows and that message in the activity log, and the controller marked that lane's cycle (7 tasks) FAILED. A mapping task runs one instance at a time, and re-starting it cannot shorten a chain whose floor is the task's own runtime (about 2 min 10 s here). Before an on-demand start, read the latest activity-log entries or the activity monitor for that taskId and skip if one is running, or coalesce triggers into the next scheduled run (L-CDI-128). Refines L-CDI-253.

### L-CDI-305  Pushdown would not rescue a mapping-based master on ClickHouse: SQL ELT is proven only within one warehouse family, and Cleanse, Verifier, Deduplicate and cloud address verification never push down
**Kind:** FACT · **Proven:** 2026-11-12 · **Evidence:** Not probed live (would need a task change); KB evidence only; measured agent-mode gap 10-100x on full rebuilds
Asked whether enabling pushdown would have closed the gap with native SQL: full SQL ELT is documented and proven only when source and target share an ecosystem (BigQuery to BigQuery, L-CDI-043/L-CDI-202), and nothing shows pushdown generating ClickHouse SQL through the JDBC V2 connector. Even where it works, only set work (joins, survivorship aggregations, match keys, routing) pushes down; the DQ engine steps run in the agent's engine and address verification is a cloud service call either way. Plan ClickHouse mastering as agent mode: incremental volume, tuned JDBC writes (L-CDI-262) and a Post SQL fold. For certainty, test pushdown once on a copy of one task and look for generated SQL in the session log. Refines L-CDI-043.

### L-CDI-306  Monitor jobs of every type from jls-di JobLogEntries with the session as a USER_SESSION cookie plus a double-submit XSRF_TOKEN
**Kind:** RECIPE · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence medium: code only); not probed here
`GET https://<pod>.<domain>.informaticacloud.com/jls-di/api/v1/Orgs('<orgUuid>')/JobLogEntries?$top=<n>&$skip=<m>&$orderby=<f>&$filter=(status eq 'RUNNING' or status eq 'QUEUED') and (assetType eq 'MTT') and (contains(assetName,'<x>')) and (startTime ge <ts>) and (contains(runtimeEnvName,'<re>'))` returns `{value:[...]}` for all job types, taskflows included. Auth in the CLI: `Cookie: USER_SESSION=<v3 sessionId>; XSRF_TOKEN=<random>` plus the header `XSRF_TOKEN: <same random>`, an alternative to the KB's `IDS-SESSION-ID`. Pre-encode `$filter` in the URL. Each row's `extraData` is a JSON string: `pid` is the process id for a TASKFLOW, and `saasTaskId` is the v2 task id otherwise. Other filterable fields: `errorMessage`, `location`. The CLI marks this as experimental and unsupported. Refines L-DQ-106.

### L-CDI-308  Start a task by path: v3 lookup id works as taskFederatedId in POST /api/v2/job; the job body also takes callbackURL and runtime parameter-file fields
**Kind:** RECIPE · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence medium: code only); not probed here
The CLI resolves `<project>/<folder>/<task>` with `POST /public/core/v3/lookup` and sends the returned v3 id as `taskFederatedId` in `POST /saas/api/v2/job` with `{"@type":"job","taskFederatedId":"<v3 id>","taskType":"MTT"}`, plus optional `callbackURL` and `runtime:{parameterFileName:"<file>",parameterFileDir:"<dir>"}` to override the parameter file per run. This matches the KB's finding that taskFederatedId works only with the task's own federated id in the same org: the v3 object id is that id. Refines L-CDI-057.

### L-CDI-310  Bridge a mapping-task run to its parent taskflow: parentTaskFederatedId plus POST /public/core/v3/lookup
**Kind:** RECIPE · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence high: code plus its tests, change notes or live-check notes); not probed here
Each v2 activityLog entry carries `parentTaskFederatedId`, a v3 federated id. `POST <baseApiUrl>/public/core/v3/lookup` with `{"objects":[{"id":"<parentTaskFederatedId>"}]}` returns the parent TASKFLOW's path, name and type (`objects[0].path`). With this, a failure alert can name the taskflow, and the name feeds the /active-bpel/rt re-run. Lookup failures should never block the alert.

### L-CDI-311  Validate an expression headless: POST /api/v2/expression/validate; list custom functions with GET /api/v2/customFunc
**Kind:** ROUTE · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence medium: code only); not probed here
`POST <serverUrl>/api/v2/expression/validate` with `{"@type":"expressionValidation","expr":"<expr>","connectionId":"<v2 connId>","objectName":"<object>","isSourceType":true}` validates an expression against a source or target object's fields before you embed it in a mapping. `GET <serverUrl>/api/v2/customFunc` lists the org's reusable custom functions. Both are read-only and were in the author's live smoke-test set.

### L-CDI-312  Read activityMonitor and activityLog with the right fields, and page the log to the window start
**Kind:** GOTCHA · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence high: code plus its tests, change notes or live-check notes); not probed here
activityMonitor (`GET /api/v2/activity/activityMonitor?details=true`, running only) names the job in `taskName` (objectName is empty) and the state in `executionState`. activityLog (completed only) names it in `objectName`, and `state == 3` means failed. Use `startTimeUtc`/`endTimeUtc`. Entries carry every transformation's stats (multi-MB pages), so always send `rowLimit`, page with `offset`, filter with `taskId`, and give a 120 s timeout (30 s failed in production). A fixed newest-N pull silently missed failures on a busy org. Refines L-CDI-288.

### L-CDI-313  Rule-based errorMsg triage table mined from production failures
**Kind:** ERROR · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence medium: code only); not probed here
Substring rules on the activityLog `errorMsg`: 'was stopped by user' (not an error: a manual stop), 'another instance of the task is currently running' (the previous run overran its slot), 'is not recognized' (Snowflake type mismatch, for example a date string into NUMBER), 'duplicate row detect' (Snowflake MERGE with duplicate keys), 'deadlock' (SQL Server victim, rerun), 'dtm process terminated unexpectedly' (agent memory or disk, or an agent restart), 'no more data available to read' (PostgreSQL connection dropped mid-read), 'unknownhostexception' (DNS on the agent), 'repoexception' (IICS-side HTTP 500, usually transient), 'sql compilation error' (bad warehouse or database value on the Snowflake connection). The string 'no errors encountered' means no real error.

### L-CDI-314  Lineage from mapping exports: resolve the IMF by templateId, never by file size or name prefixes
**Kind:** GOTCHA · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence medium: code only); not probed here
One third-party lineage extractor picks the largest `bin/*.bin` in a DTEMPLATE zip and classifies sources and targets by transformation name prefixes (`src_`, `tgt_`), which silently mislabels mappings that follow other naming; it also calls a `/saas/api/v2/export` route that the v2 API does not have (export is v3). Resolve the mapping body through `mappingTemplate.json` `templateId` and `fileRecord.json` (type `IMFOBJECT`; `mappingPreviewFileRecordId` names the preview image), then read sources and targets from the IMF transformation classes and their connection bindings. The same code tolerates `mappingTemplate.json` as a bare array or as `{"value":[...],"Count":n}`. Refines L-CDI-027.

### L-CDI-315  v2 mapping and connection lists are unpaginated: limit, skip and maxRecordsCount are ignored
**Kind:** GOTCHA · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence high: code plus its tests, change notes or live-check notes); not probed here
GET <serverUrl>/api/v2/mapping and /api/v2/connection return every record in one response and ignore limit, skip and maxRecordsCount (verified live by the maintainers of an open-source catalog connector). Very large orgs (over 10k mappings or 1k connections) can hit request timeouts; raise the timeout or scope by tag through the v3 objects API, which does page with limit/skip. /api/v2/mttask is often restricted to some roles (403).

### L-CDI-316  Table lineage from a v3 mapping export: bin/@3.bin JSON transformations and saas:@ connection refs
**Kind:** RECIPE · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence medium: code only); not probed here
Export mappings with POST /public/core/v3/export (batches of up to ~1000 ids), poll, download, and in each inner dTemplate zip read bin/@3.bin (bin/@2.bin is a preview image) as UTF-8 JSON. content.transformations[] entries with a dataAdapter give object name/objectName/label, dbSchema and connectionId 'saas:@<federatedId>', and $$class marks source or target. Resolve the federated id against /api/v2/connection connParams['Connection Type'] for the platform. Taskflow step order comes from the exported .TASKFLOW.xml taskflowModel (start/service/end nodes linked by link targetId). Filter bundle objects by path 'Add-On Bundles/' or updatedBy 'bundle-license-notifier'. Refines L-CDI-027.

### L-CDI-317  Asset name length limits by type (field guide): CDI 100, mappings 200, CAI connectors and connections 128, processes 80
**Kind:** FACT · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence low: a comment or README claim); not probed here
A field naming guide gives these maximum name lengths: CDI connections, tasks, taskflows and schedules 100 characters, mappings 200, CAI service connectors and app connections 128, CAI processes 80; agent names are at most 100 (the agent form's `name` field has maxlength 100). Check a generated name against the limit before a create or import, and prefer short prefixes (`M_`, `TF_`, `SCH_`, `MP-`/`SP-` for master and sub-processes). Renaming CAI assets later is hard because designs reference each other by name. The guide dates from 2019: confirm a limit on your pod with one throwaway create.

### L-CDI-318  v3 MTT object rows lack the mapping reference: enrich with GET /api/v2/mttask/name/<name>; taskflow by-name reads fail on modern pods
**Kind:** ROUTE · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence medium: code or a guide); not probed here
`/public/core/v3/objects?q=type=='MTT'` does not return which mapping a task runs; `GET <serverUrl>/api/v2/mttask/name/<urlencoded name>` (icSessionId) adds `mappingId`, `mappingName` and `connectionId`, the bridge from task to mapping lineage. For a taskflow's step graph the client probes `/public/core/v3/objects/<guid>`, `/api/v2/taskflow/name/<name>` and `/api/v2/workflow/name/<name>` (legacy, 403 on most modern tenants) and notes these fail on modern pods, so it falls back to a v3 export of the TASKFLOW, submitting all taskflow GUIDs in one export job and parsing `<eventContainer>/<service>/<link>`.

### L-CDI-319  Code task API: submit a Scala Spark JAR to an advanced cluster via /disnext/api/v1/CodeTask
**Kind:** ROUTE · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence medium: code or a guide); not probed here
Vendor docs: `POST <serverUrl>/disnext/api/v1/CodeTask` with header `IDS-SESSION-ID` and body {codeTaskName, runtimeEnvironmentName, codeExecutionParameters:{agentGroupId, logLevel (none|terse|normal|verboseInitialization|verboseData), sparkMainClass, sparkMainClassArgs[], sparkPrimaryResource (JAR), sparkJars[], sparkFiles[], advancedCustomProperties (escaped JSON string of spark.* props), overrideTaskTimeout (-1 = none)}} returns codeTaskId. Start with `POST .../CodeTask/Start` {codeTaskId} -> jobId; read config with `GET .../CodeTask/<codeTaskId>`; cancel with `PUT .../CodeTask/Cancel` {jobId}. agentGroupId wins when both it and runtimeEnvironmentName are given. Documented for AWS serverless or non-serverless advanced clusters only.

### L-CDI-320  Poll a code task job: CodeTask/JobStatus, then logservice logs and callback
**Kind:** ROUTE · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence medium: code or a guide); not probed here
`GET <serverUrl>/disnext/api/v1/CodeTask/JobStatus/<jobId>` (IDS-SESSION-ID) returns executionState (QUEUED, RUNNING, SUCCEEDED, FAILED, CANCELLED), sessionLogUrl, firstErrorMessage and, on serverless, assignedServerlessComputeUnits / consumedServerlessComputeUnits. Session logs: `GET <serverUrl>/logservice/api/v1/jobs/<jobId>/logs`; Spark task result: `GET <serverUrl>/logservice/api/v1/jobs/<jobId>/callback`, whose callbackBody is an escaped JSON string carrying taskId, executionId, sessionLogUrl and executionState. Parse callbackBody twice.

### L-CDI-321  Update-Mode: PARTIAL works on six v2 resources; collection entries need their key fields
**Kind:** FACT · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence high: code plus its tests, change notes or live-check notes, or vendor documentation bundled in the repository); not probed here
Vendor docs list partial mode (header `Update-Mode: PARTIAL`, JSON only, include `@type`) for v2 connection, fwConfig, masterTemplate, mttask, schedule and workflow; everything else is full replace. To change one entry inside a collection, send that entry's key: fwConfig.fwColumn by name; masterTemplate.mtParameter by name+type; mttask mtTaskInOutParameter, mtTaskOverriddenField by name, mtTaskParameter by name+type, sequenceDefinition by txName, extendedObject.objects by name; workflow.workflowTask by taskId. Example: swap a mapping task's source connection with {"@type":"mtTask","parameters":[{"@type":"mtTaskParameter","name":"$Src$","type":"EXTENDED_SOURCE","sourceConnectionId":"<id>"}]}. Refines L-CONN-142.

### L-CDI-322  Documented job-history read: cdiinsights-service JobLogEntries (33 days, 500 rows per filter)
**Kind:** ROUTE · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence high: code plus its tests, change notes or live-check notes, or vendor documentation bundled in the repository); not probed here
The vendor-documented Operational Insights route is `GET <serverUrl>/cdiinsights-service/api/v1/analytical/Orgs(<orgId>)/JobLogEntries` with `IDS-SESSION-ID` (examples also show icSessionId). OData params: `$filter=(endTime ge <ISO>) and (endTime le <ISO>)` (startswith on runtime/agent/asset), a separate non-OData `listFilter=status in (COMPLETED,WARNING,FAILED,END,SUCCESS,STOPPED) and assetType in (MTT,TASKFLOW,MI_TASK,DSS,WORKFLOW,DRS,PCS,DTT,DLT,...)`, `$count=true`, `$top` (max 500), `$skip`, `$orderby`. Only completed jobs, only the last 33 days, at most 500 records for any filter, so slice long windows by endTime. Rows carry logEntryId, assetId, runId, assetName, status, assetType, start/endTime, duration, errorMessage, location, rowsProcessed, successRows, errorRows, runtimeEnvName, startedBy, subtasks, extraData, parent* fields, agentId/agentName, projectName. This is the supported counterpart to the undocumented jls-di JobLogEntries.

### L-CDI-323  Job callbackURL: at-least-once delivery, 30 s timeout, retries for 30 minutes; make the receiver idempotent
**Kind:** GOTCHA · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence high: code plus its tests, change notes or live-check notes, or vendor documentation bundled in the repository); not probed here
With `callbackURL` in `POST <serverUrl>/api/v2/job`, IDMC POSTs JSON {"@type":"callbackUrlResponse", objectId, objectName, runId, endTime, status COMPLETED|FAILED} when the job ends. The receiver must answer HTTP 200 within 30 seconds; any other status, a timeout, downtime or a network blip counts as a failure: three immediate retries, then exponential backoff from about 30 s up to 3-minute gaps until 30 minutes have passed. So the same completion can arrive several times: dedupe on (objectId, runId). The URL must be publicly reachable from the IDMC pod, so put it behind your own authenticated gateway rather than exposing an internal service. Refines L-CDI-308.

### L-CDI-324  Hierarchical mapper (h2h) API: create, run synchronously with a buffer or file, read metadata
**Kind:** ROUTE · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence medium: code or a guide); not probed here
Hierarchical mappers (XSD-to-XSD transforms, e.g. EDI) are on `<serverUrl>/h2h/api/v1/` with `IDS-SESSION-ID`. Create: `POST .../create/<mapperId>` {name, description, projectName, projectFolderPath, sourceXsd, sourceXsdDependencies[], targetXsd}. Run: `POST .../service/run/<mapperId>` {agentGroupId (omit = runs on the Cloud Server), input:{type: buffer|file, value: <XML/JSON or agent path>}, output:{type: buffer|file, value: "" or path}} returns {output, message} synchronously. Metadata: `GET .../idsm/metadata/<mapperId>`. The mapper id is the last path segment of the designer URL `.../integrationDesign/main/idsm/<id>/read`.

### L-CDI-325  Render a mapping diagram: GET /api/v2/mapping/<id>/image?deployed=true|false
**Kind:** ROUTE · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence medium: code or a guide); not probed here
`GET <serverUrl>/api/v2/mapping/<v2 mappingId>/image?deployed=<true|false>` (icSessionId) returns an image of the mapping canvas; deployed=true renders the deployed version. Useful for documentation or review packs without opening the designer. Uses the v2 mapping id, not the v3 federated id.

### L-CDI-326  Run industry data services (HL7, EDI parsers etc.) via /DSRepo/rest/api/v1/services/run/<serviceName>
**Kind:** ROUTE · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence medium: code or a guide); not probed here
`POST <serverUrl>/DSRepo/rest/api/v1/services/run/<serviceName>` (IDS-SESSION-ID) runs a pre-built industry data service (e.g. HL7_2_6_ADT_A01_Parser) on a Secure Agent group. Body: {agentGroupId (required), input:{type FILE|BUFFER, value}, output:{type FILE|BUFFER, value (path when FILE)}, additionalInputs:[{name,type,value}], additionalOutputs:[{name,type,value}], serviceParameters:[{name,value}]}. FILE paths are on the agent host; BUFFER returns the result inline in the response.

### L-CDI-327  Run, monitor and stop a dynamic mapping task on /batch-mapping/api/v1/Job, never v2 job/activityLog
**Kind:** ROUTE · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence high: code plus its tests, change notes or live-check notes, or vendor documentation bundled in the repository); not probed here
On the pod host (no /saas) with IDS-SESSION-ID: start with `POST /batch-mapping/api/v1/Job` {"taskFrsId":"<v3 federated id from lookup>"} -> {runId, taskFrsId}; monitor with `GET /batch-mapping/api/v1/Job/monitor/task/<taskFrsId>/run/<runId>` which returns overall successRows/errorRows/runContext plus jobs[] {jobName, groupName, saasJobRunId, saasLogId, failed/successSourceRows, failed/successTargetRows, errorMessage, enabled, sessionLogUrl}; stop with `POST /batch-mapping/api/v1/Job/stop` {"taskFrsId", "runId"}. The vendor docs say not to use the v2 job resource for DMT status. The per-job saasLogId links each sub-job back to the v2 activity log entry. Refines L-CDI-289.

### L-CDI-328  v2 detail by federated id works only for mapping tasks: mttask/frs/<id>; dsstask/<frsId> and workflow/<frsId> give 500
**Kind:** GOTCHA · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence high: code plus its tests, change notes or live-check notes, or vendor documentation bundled in the repository); not probed here
`GET <serverUrl>/api/v2/mttask/frs/<v3 object id>` returns the mapping task (documented; the bare `mttask/<frsId>` also answered but is not guaranteed). The same trick fails for other types: `GET /api/v2/dsstask/<frsId>` and `/api/v2/workflow/<frsId>` answer 500. Synchronization tasks and linear taskflows must be read by name (`dsstask/name/<name>`, `workflow/name/<name>`), and those lookups are org-wide, not folder-scoped, so two same-named tasks in different folders cannot be told apart through them; warn on duplicates found in v3 objects. A DSS detail carries sourceConnectionId, targetConnectionId and sourceObjects[] but no runtime environment (srcRuntimeAttrs/tgtRuntimeAttrs come back empty).

### L-CDI-329  mttask lastRunTime is epoch milliseconds while createTime/updateTime are ISO strings
**Kind:** GOTCHA · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence high: code plus its tests, change notes or live-check notes, or vendor documentation bundled in the repository); not probed here
In `GET /api/v2/mttask/frs/<id>` the same response has createTime and updateTime as ISO-8601 UTC strings but lastRunTime as a JSON number of epoch milliseconds (e.g. 1794466734000 = 2026-11-12T06:58:54Z), contrary to the 'all dates are ISO' convention. Parse numbers as milliseconds; treat 0, null or missing as unknown rather than 'never ran'. Whether a run triggered only from a taskflow updates it is unverified, and it is not 'last successful run'.

### L-CDI-330  Read transformation order and connection parameterization from mttask parameters[], not the mapping
**Kind:** FACT · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence medium: code or a guide); not probed here
mttask `parameters[]` and the mapping's `parameters[]` can list Source and Target in different orders, and `GET /api/v2/mapping/<id>` has no reliable path, location or folder, so build task documentation from the task. The transformation name is `parameters[].name` stripped of the surrounding `$` (label is often just the connection's display label). Connection parameterization appears as `uiProperties.connectionParameterized` (the STRING "true"/"false", not a boolean), `uiProperties.connDefault` (default connection name), `uiProperties.paramName`, `uiProperties['paramType-mapping']=="Connection"`, and `runtimeParameterData.connectionParameterName` / `isConnectionRuntimeParameter` (boolean). These keys are not in the public field table; parse defensively. Refines L-CDI-007.

### L-CDI-331  PostgreSQL truncate before load works only through the writer attribute TruncateTable = YES
**Kind:** GOTCHA · **Proven:** 2026-10-03 · **Evidence:** Generated mapping run on a scratch PostgreSQL schema: session log TRUNCATE line, table emptied before load (2026-10-03, toolkit/mapgen/docs/PROBES.md)
On a PostgreSQL target the writer ignores the mapping's `WriteOptions.truncate`; the writer attribute `TruncateTable` (display name "Truncate target") set to `YES` truncates, and the session log shows `TRUNCATE "<schema>"."<table>"`. The value must be `YES`: `true` is rejected and falls back to NO. The mapping generator writes it for `truncate: true` (lint warns TGT_PG_TRUNCATE). This explains the earlier conflicting reports about PostgreSQL truncate (L-CDI-194, L-CONN-032), which concerned the flag, not the writer attribute. A truncating posting table is still a wipe risk (L-CDI-169).

## Superseded / overturned (kept so nobody re-learns them)

### L-CDI-174  CDI mapping authoring is UI-only; one mapping must be authored in the UI first, overturned 2026-09-23
**Was believed:** 2026-06-27 to 2026-09-22 · **Overturned by:** L-CDI-003, L-CDI-021, L-CDI-033
The belief was that new mappings need the designer canvas ("build once in the designer, run over REST"), and that headless work needs one UI-authored seed. Tasks over the parameterized bundle templates (2026-09-23) and synthesized IMF mappings (2026-09-29) removed both claims. `POST /api/v2/mapping` is still not a create route (L-CDI-020).

### L-CDI-175  v2-created mapping tasks do not surface in a v3 type=='MTT' scan, overturned 2026-09-25
**Was believed:** 2026-09-23 · **Overturned by:** L-CDI-012
A scan saw 0 MTTs while the tasks ran hourly. Later reads listed all of them; the earlier result was probably a filter or paging artifact.

### L-CDI-176  The v2 task resources exist on every pod, overturned 2026-07-26
**Was believed:** July 2026 · **Overturned by:** L-CDI-015
`/api/v2/dss`, `dtemplate`, `dmask`, `dreplicate`, `plan` and `fileListener` were assumed universal. They mount per pod and per licensed engine.

### L-CDI-177  Moving an asset to another project is a UI Explore action, overturned 2026-09-24
**Was believed:** 2026-08-19 · **Overturned by:** L-CDI-016
FRS `MoveEntities` moves objects headless, and runs key off immutable ids, so moves are harmless to running pipelines.

### L-CDI-178  Headless CDI data movement is walled (a cold PostgreSQL source cannot resolve), overturned 2026-09-23
**Was believed:** 2026-09-22 to 2026-09-23 · **Overturned by:** L-CDI-021, L-CDI-162
The verdict: template sources browse at run time, a task carries no field array, and a never-browsed PostgreSQL source cannot resolve, so a UI browse or catalog seeding would be needed. The object path `<schema>/TABLE/<table>` and cloned template tasks moved data headless the same day.

### L-CDI-179  Mapping tasks, taskflows and schedules for a redesign are UI-only, overturned 2026-07-09
**Was believed:** early July 2026 · **Overturned by:** L-CDI-025, L-CDI-075
Tasks were cloned headless (`mtTask.json` + the `iics` CLI) and schedules were created and bound over v2.

### L-CDI-180  A mapping's connection and SQL are compiled into a binary bin/@3.bin that cannot be edited, overturned 2026-09-22
**Was believed:** 2026-07-05 to 2026-09-22 · **Overturned by:** L-CDI-027
The IMF file is JSON text. It was edited and later synthesized from scratch. The part that still stands: package edits did not change a mapping's connector **type** (L-CDI-031).

### L-CDI-181  Hand-built import packages are always rejected with MigrationSvc_030, overturned 2026-09-29
**Was believed:** 2026-06-28 to 2026-09-28 · **Overturned by:** L-CDI-032
Packages built from scratch import SUCCESSFUL when `exportMetadata.v2.json`, the project and folder entries and the checksums are right. `MigrationSvc_030` is an empty or invalid multipart.

### L-CDI-182  There is no REST read-back or diff of a mapping's internals, overturned 2026-09-22
**Was believed:** 2026-07-26 · **Overturned by:** L-CDI-027
Exporting a mapping returns its IMF JSON, which can be read, diffed and regenerated. A written spec is still the best review artifact.

### L-CDI-183  Scheduling and monitoring mapping tasks requires the Administrator UI, overturned 2026-07-04
**Was believed:** early July 2026 · **Overturned by:** L-CDI-073, L-CDI-075
`POST /api/v2/schedule` returns 200 and creates a real schedule, `scheduleId` binds it, and the activity log monitors every run.

### L-CDI-186  Long text can only be kept by chunking into 250-character columns or by a Fields-tab edit, overturned 2026-09-24
**Was believed:** 2026-09-23 to 2026-09-24 · **Overturned by:** L-CDI-153
The interim design landed long text as 16 × 250-character chunk columns re-joined in a view. JSON-typed target columns replaced it the same afternoon.

### L-CDI-187  Reverse-ETL into the app database needs a UI-authored mapping, overturned 2026-09-24
**Was believed:** 2026-09-24 · **Overturned by:** L-CDI-089
A template task with a warehouse query source and a PostgreSQL upsert target delivered reverse-ETL headless.

### L-CDI-189  REST-started agent jobs start on a ~3-minute job-poll cadence, overturned 2026-09-28
**Was believed:** 2026-08-20 (one agent; 15 serial tasks ≈ 45 min) · **Overturned by:** L-CDI-121
On the agents used from 2026-09-23, dispatch took about 5 s and a task's fixed cost was about 20 s. Treat minutes-long dispatch as an agent problem to investigate.

### L-CDI-190  Swapping a mapping's target connection to another warehouse later is a quick change, overturned 2026-07-04
**Was believed:** 2026-06-27 (a plan) · **Overturned by:** L-CDI-050, L-CDI-031
Cross-connector retargets of tasks silently reverted, and target changes on tasks over real mappings are no-ops. Retargeting means changing the mapping.

### L-CDI-191  The first mapping for a new connector pair must be authored in the UI, overturned 2026-09-29
**Was believed:** 2026-07-07 · **Overturned by:** L-CDI-033
A generator built mappings with PostgreSQL sources and BigQuery targets from harvested exemplars, with no UI seed for that pair. Adapters never tried (Salesforce and PostgreSQL targets, flat-file sources) remain unproven.

### L-CDI-042  BigQuery full pushdown could not be enabled over REST, overturned 2026-10-01
**Was believed:** 2026-09-29 to 2026-09-30 · **Overturned by:** L-CDI-202
`POST /api/v2/mttask/<id>` with `sessionProperties {"Pushdown Optimization":"Full"}` persists, but pushdown does not happen, and `optimizationPlan` accepts any string, unvalidated. Capture the UI's save request once (an XHR log) to learn the real property name and value. Until then, heavy warehouse logic runs as query sources. Setting the temporary-view property and `enableCrossSchemaPushdown` as well, with no write disposition on the targets, made the same kind of mapping push down (OPT_63367 in the session log).

### L-CDI-225  What CLAIRE structure discovery makes of a PDF and a spreadsheet: review the names before building the mapping, overturned 2026-10-07
**Was believed:** 2026-10-06 · **Overturned by:** L-CDI-229
A PDF goes through the `PdfToModel` learner: the document becomes key/value records (header, details and footer groups) with dates typed as dates, and a free-text block that spans two lines is left out (it reaches the Unidentified port). The Excel learner splits code-like values such as `ABC-123` into `_token` and `_number` fields and can name a table-row group with a semantic guess unrelated to the content. Field names keep their spaces in the model; Structure Parser ports are cleaned to letters, digits and underscores, and every output field is a string(255) (the real types stay in the model). Fix names before the mapping is built, because the mapping copies them (the service exposes `singleNodeModification`, `mergeNodes` and `splitNode`; not exercised).

### L-CDI-226  A Structure Parser stores the model's v2 id and a copy of the model: model edits arrive only after Synchronize, overturned 2026-10-07
**Was believed:** 2026-10-06 · **Overturned by:** L-CDI-230
In a mapping, a Structure Parser transformation keeps `isdModelId` = the intelligent structure model's v2 id (the export's `repoInfo.repoHandle`, not the v3 id) and `modelString` = a copy of the model, with `parserMode` isdMode, `inputType` FILE, `outputType` Relational and an empty `connectionId` for the CLAIRE engine. Its input group takes `FilePath` (string 4096) and `Data` (binary); it has one output group per model group plus `Unidentified`. Because the model is copied, a later edit of the model reaches the mapping only after Synchronize. The designer reads the detail from `GET /da/web.saas.service/saasinfo/structureDiscoveryDetail?id=<v2 id>`, which needs a designer session.

### L-CDI-194  Whether truncateTarget=true on a PostgreSQL target truncates or is ignored, overturned 2026-10-03
**Was believed:** 2026-09-28 (disputed) · **Overturned by:** L-CDI-331
Do not rely on either reading. Never set `truncateTarget=true` on a system-of-record table, and make postings idempotent in the database (L-CDI-169).

## Disputed (evidence conflicts; do not rely on either reading)

### L-CDI-192  A mapping task can be run through POST /public/core/v3/jobs with taskFederatedId
**Kind:** ROUTE · **Status:** disputed · **Seen:** 2026-07-04 · **Evidence:** a single report of 22 runs; the same tasks are recorded elsewhere as run through `POST /api/v2/job`
One July record says `POST /public/core/v3/jobs {"taskFederatedId":"<id>","taskType":"MTT"}` returned a runId, polled at `GET /public/core/v3/jobs/<runId>`. No other source reproduces it. Use `POST /api/v2/job` with the v2 `taskId` (L-CDI-056).

