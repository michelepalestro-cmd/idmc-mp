# Mastering data (MDM SaaS / Business 360): cheat sheet

Turn duplicate or conflicting records into one trusted master record per real-world thing, natively in MDM SaaS
(Business 360, Customer 360) or as IDMC mappings over a warehouse table: use this whenever a user asks to master a
table, load or search MDM records, or tune match and merge.

**Start with:** the `idmc-mdm` skill; read with `toolkit/lib/idmc_session.py` (its command line only reads; MDM writes are hand-built, see the skill's Tools); open
[01 MDM SaaS: Runtime vs Design](01-mdm-saas-runtime-vs-design.md) first (for a warehouse table with no MDM SaaS model,
[05 Mastering a table](05-mastering-a-table-repeatable-playbook.md), and `/idmc-mp:clean-data` for a duplicate clean-up).
No MDM or DQ licence and a customer file? [Customer master from a CSV](../../toolkit/demos/customer_master_csv/README.md)
cleans, deduplicates and assigns customer ids with plain CDI mappings.

**The law:** the runtime plane on `<pod>-mdm.<domain>` (pod label + `-mdm`, no `/saas`) is headless; model design,
source systems, match models, survivorship, publish and job runs are Business 360 UI steps with no public route
(L-MDM-002, L-MDM-004, L-MDM-005). MDM runs in the pod, not on a Secure Agent (L-MDM-001).

## What works (headless)

| Task | How (exact route/tool/command) | Lesson |
|---|---|---|
| Authenticate | identity Login, `jwt/Token?client_id=cdlg_app`, then Bearer JWT + `IDS-SESSION-ID` + `X-INFA-ORG-ID`; re-mint at ~25 min | L-MDM-003 |
| Prove an entity is live | ingest POST gate with an invalid body: 404 "metadata ... cannot be found" until live, then 201/400; a fake entity name must stay 404 | L-MDM-008 |
| Ingest a source record | `POST .../business-entity/public/api/v1/entity/<runtimeId>?sourceSystem=<src>`, bare field map, `trustScore` as a string -> 201 | L-MDM-019 |
| Search and export | `POST .../search/public/api/v1/search` `{"search":"*","entityType":...,"recordOffset":..,"recordsToReturn":1000}`; union of queries past 10,000 | L-MDM-025 |
| Soft-delete records | `DELETE .../entity/<be>/<id>?sourceSystem=<src>`; bulk in waves of ~6 parallel calls (~500/min) | L-MDM-029, L-MDM-070 |
| Reference 360 search | `POST .../rdm-service/external/v1/search` (validator reached) | L-MDM-026 |
| Clone design objects | v3 export/import package (BUSINESS_ENTITY, MDM_SRC_SYSTEM, REFERENCE_ENTITY, RULE_SPECIFICATION), multipart upload | L-MDM-013, L-MDM-014 |
| Fuzzy master lookup | Customer Identification MCP: `search_master_record`, `get_master_record_details` (documented) | L-MDM-027 |
| Master a warehouse table with IDMC | parameterized CDI mappings: Cleanse/Verifier -> match on sorted input with variable ports -> sorted-Aggregator survivorship -> Router to a steward queue; one taskflow | L-MDM-075, L-MDM-081 |

## What doesn't work, and the workaround

| Wall | Workaround | Lesson |
|---|---|---|
| No REST deploy/publish/model authoring (`404 CMN00005`, matching bogus twins) | plan the Modeler session (Save, plus Publish if your release shows it); prove with the ingest gate | L-MDM-005, L-MDM-007 |
| Ingress, match/merge, reindex job runs: no public route | Business 360 Console: New > Jobs > Match and Merge > Save > Run (headed browser to automate) | L-MDM-016, L-MDM-036 |
| Job runs are invisible to headless signals | My Jobs (`/ui-config-app/main/jobs`) is the ground truth | L-MDM-018 |
| Design GUID in the record path: 404 "cannot be found during load" | use the runtime id (for example `c360.person`) | L-MDM-006 |
| `.../entity/<be>/search` 404/405/403 | `/search/public/api/v1/search` or the MCP fuzzy match | L-MDM-028 |
| Native MDM not licensed or not ready | warehouse stand-in per domain; cut over after a zero-drift reconcile | L-MDM-050, L-MDM-051 |
| Product 360 Cloud Edition (PIM) has no REST API | check privileges for `p360` first; it is a different product | L-MDM-055 |

## Fastest safe path

1. Prove the org and the MDM host; read entitlement from privileges, roles and `MDM_*` objects, not `products[]`.
   Read-back: the privilege list (L-MDM-011).
2. Classify the dataset (entity, registry, versioned asset, definition, event) and its grain. Read-back: duplicate groups
   per candidate key, by real scope (L-MDM-077).
3. Measure first: do sources diverge, do keys collide, are match keys filled. Read-back: divergence and collision counts
   (L-MDM-045, L-MDM-044, L-MDM-088).
4. Native MDM: model, rank every source, set survivorship and DQ, publish the match model, all before the first load.
   Read-back: the console receipt (L-MDM-039, L-MDM-097 (reported), L-MDM-098 (reported)).
5. Gate the model with the ingest POST + fake-entity control. Read-back: 201 or validation 400 vs fake 404 (L-MDM-008).
6. Ingest one real record and read it back to prove field names; then bulk with a tally and checkpoint (ingest is not
   idempotent). Read-back: submitted/ok/failed counts (L-MDM-046, L-MDM-022, L-MDM-033).
7. Run Match and Merge in the console (16-25 min whatever the size). Read-back: My Jobs Success (L-MDM-036, L-MDM-037).
8. Check search is indexed, then export and reconcile. Read-back: export union count = entity count (L-MDM-031,
   L-MDM-025).
9. Warehouse path: pilot one scope, size it (rows/s, jobs, memory), then fan out incrementally. Read-back: gates pass on
   the published table, one golden owner per scope (L-MDM-090, L-MDM-085, L-MDM-079).

## Top traps

- 404 "metadata with GUID ... cannot be found during load" on a live runtime -> design GUID used -> runtime id
  (L-MDM-006).
- 403 on `GET entity/<be>/<id>` -> access check runs before the lookup, proves nothing; `data360/mdm/.../businessEntities`
  200 is a fake (L-MDM-009).
- 400 "not allowed by the data model" -> body wrapped in `fields`/`attributes`/`record`; 400 "Enter a valid [null]" ->
  integer `trustScore` (L-MDM-020).
- A retried POST creates new master ids -> ingest is not idempotent -> tally and reconcile first (L-MDM-022).
- 404 `MigrationSvc_025` on import -> JSON content type -> multipart/form-data (L-MDM-014).
- 400 "Missing required parameter sourceSystem" on delete -> add `?sourceSystem=` (L-MDM-070).
- Search shows "No records found" after successful MatchMerge -> Search Reindex job stuck -> check My Jobs (L-MDM-031).
- Records loaded before the match model was published never match -> Publish and Regenerate Match Keys (L-MDM-097 (reported)).
- Surname + street-number key merges a household -> add the first initial; change every copy of the key, app included
  (L-MDM-072, L-MDM-073).
- Fuzzy address rules collapse distinct records on degenerate addresses -> deterministic business key first (L-MDM-044,
  L-MDM-075).
- Logic as a long Source query is not mastering, and IDMC decisions nobody reads change nothing -> transformations, and
  prove each output has a consumer (L-MDM-081, L-MDM-087).
- Calling a SQL dedup layer "golden record" or "MDM" -> say trusted curated layer (L-MDM-052).
- One 0.90 threshold looked 77 % precise but hid classes from 100 % down to 2.5 % -> hand-check each match class and
  auto-merge only the classes that clear the bar (L-MDM-121).
- Address matching inside one source mostly pairs distinct records -> two ids from one source are two entities; compare
  ids by raw bytes (L-MDM-122, L-MDM-123).
- Survivor keeps old values when the loser is newer -> rank per field, then recency; store the winning source per field
  (L-MDM-125). A pair-merge tool run on groups writes competing survivors -> merge clusters (L-MDM-126).
- Merged records come back or old ids stop resolving -> check the merge invariants daily (L-MDM-127); re-key retired
  ids one-to-one only (L-MDM-128).
- Blocking on one coarse key explodes into hundreds of millions of pairs -> union of tighter blocks, proven lossless
  (L-MDM-124).

## Go deeper

- [01 Runtime vs design](01-mdm-saas-runtime-vs-design.md): hosts, auth, runtime id, the deploy gate, entitlement.
- [02 Records](02-mdm-records-ingest-search-export-cleanup.md): ingest, search and export past 10,000, soft deletes, caps.
- [03 Business 360 modeling & match-merge](03-business-360-modeling-match-merge.md): design clicks, jobs, survivorship, stand-in.
- [04 P360 vs MDM SaaS & licensing](04-p360-vs-mdm-saas-licensing-notes.md): which product, record licensing, metering.
- [05 Mastering a table](05-mastering-a-table-repeatable-playbook.md): archetypes, the ten steps, acceptance gates.
- [lessons.md](lessons.md): every MDM lesson with evidence; grep it before any call.
