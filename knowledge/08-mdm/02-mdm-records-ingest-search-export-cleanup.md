# MDM Records: Ingest, Search, Export, Cleanup

**Answers:** How do I ingest a source record into MDM SaaS, search and export master records past the 10,000 cap, and
delete records (one or in bulk)? What do deletes really do, and what must be exported before an MDM installation is
removed?

**Read when:** loading, exporting or cleaning MDM SaaS records headless; a POST returns 400; an export comes back short;
planning an MDM cleanup or decommission.

**Key rules:**
- Ingest is `POST .../entity/<runtimeId>?sourceSystem=<src>` with a bare field map and `trustScore` as a string; a
  re-post creates new master ids, so never retry blindly (L-MDM-019, L-MDM-020).
- One search query returns at most 10,000 records: export larger entities as a union of term and prefix queries and
  reconcile the count (L-MDM-025).
- Deletes need `?sourceSystem=` and are soft: records change state, drop out of search and can be restored
  (L-MDM-029, L-MDM-070).
- Bulk delete in search-page waves of about 6 parallel calls (about 500 records a minute), pausing for the index
  (L-MDM-070).
- Export every entity and the design objects before deleting an MDM installation (L-MDM-030).

**Related:** [MDM Runtime vs Design](01-mdm-saas-runtime-vs-design.md) ·
[Business 360 Modeling & Match-Merge](03-business-360-modeling-match-merge.md) ·
[Headless Deletes & Org Cleanup](../10-migration-org-management/06-headless-deletes-org-cleanup.md) ·
[Lessons: MDM](../../lessons/by-domain/08-mdm.md)

**Last verified:** 2026-10-03

> **Summary.** Ingest creates a source record (201 with an `MDM...` id); the master re-survives only when a match/merge
> job runs. Search and export use `POST .../search/public/api/v1/search`. Deletes are soft, per the Customer 360 guide
> and the live calls below.

---

## 1. Record vocabulary (vendor terms)

| Term | Meaning |
|---|---|
| Master record | The consolidated record (vendor term; not "golden record") |
| Source record | One source system's contribution to a master record; this is what ingest creates |
| Patch record | A source-like record holding only the fields edited on a master (UI, API or batch), one per source system |
| entity-xref | The API resource for source and patch records |
| Record State | active, pending, inactive, deleted |
| Match Outcome | Auto-merged, Auto-merged with Approval, User Merged, User Merged with Approval, Not Merged |

Tokens such as MATCH_INDEXED, SEARCH_INDEXED, CONSOLIDATED or UNMERGED seen in payloads are not documented; pin their
real values on a live read before gating on them (L-MDM-038; L-MDM-021, disputed).

---

## 2. Ingest a source record (L-MDM-019, L-MDM-020, L-MDM-022)

```
POST https://<pod>-mdm.<domain>.informaticacloud.com/business-entity/public/api/v1/entity/c360.person?sourceSystem=<sourceSystemId>
(three identity headers: Bearer JWT, IDS-SESSION-ID, X-INFA-ORG-ID)
Content-Type: application/json

{"firstName":"Ada","lastName":"Lovelace","email":"ada@example.com","trustScore":"85"}
```

Success: **201** `{"approvalRequired":false,"id":"MDM...","businessId":"MDM..."}`.

| Rule | Failure when broken |
|---|---|
| The body is a bare field map | Wrapped in `fields`, `attributes` or `record`: 400 "not allowed by the data model" |
| Required fields per entity (for `c360.person`: `firstName` and `lastName`; `fullName` is computed) | 400 |
| `trustScore` is a string | Integer: 400 "Enter a valid [null]" |
| Only fields that exist in the model | 400 |
| The source system id is a registered source (for example `c360.<system>.system`) | Rejected; acceptance of an unregistered name was never proven |
| Address the entity by runtime id | Design GUID: 404 "metadata ... cannot be found during load" |

What happens next: the record lands as a **source record**. The master record does not re-survive until a match/merge
job runs (a Business 360 Console action or a job schedule, L-MDM-016). Records show in the Customer 360 UI only once
they are search-indexed (L-MDM-031).

**Not idempotent.** A re-post of the same source record created new master ids. Keep a client-side
submitted/ok/failed tally and a checkpoint, reconcile before any retry, and do not rely on an untested
"POST per source key is an upsert" assumption.

---

## 3. Read a master record by id (L-MDM-021, disputed)

`GET https://<pod>-mdm.<domain>.informaticacloud.com/business-entity/public/api/v1/entity/<runtimeId>/<id>` returned
200 with the record plus `_meta` (consolidation and search-index states) in July. A later review concluded that some
early 200s were identity-service login HTML. Always check the Content-Type and body shape, not only the status. A 403
here proves only that the plane is real (L-MDM-009).

---

## 4. Update source records: entity-xref (L-MDM-023)

Send source-system updates to `/business-entity/public/api/v1/entity-xref/{...}` (GET, PUT and PATCH documented; not
exercised). Never write source data onto the master `entity` resource: that corrupts the master record. PATCH is
meaningful only in MDM, on `entity` and `entity-xref`. Request bodies carry `search` or `fields`, never both
(indicative, from a vendor deck, L-MDM-024).

---

## 5. Search and export (L-MDM-025)

```
POST https://<pod>-mdm.<domain>.informaticacloud.com/search/public/api/v1/search
(three identity headers; JWT minted with client_id=cdlg_app)
Content-Type: application/json

{"search":"*","entityType":"c360.person","recordOffset":0,"recordsToReturn":1000}
```

Page with `recordOffset` and `recordsToReturn`. One query returns at most **10,000** records in total, however you page.

**Export an entity larger than 10,000 records:**

1. Get the entity's total from the first page (or from the console) and write it down.
2. Split the population into queries that each return fewer than 10,000: terms or prefix wildcards on a
   high-cardinality text field (for example `a*`, `b*`, ... on a name field), narrowing a prefix further whenever it
   still hits the cap.
3. Page each query to exhaustion and write every record to JSON.
4. Deduplicate by record id across queries (prefixes overlap on multi-token values).
5. Compare the union count with the total; investigate any gap before calling the export complete.

Measured: 19,253 of 19,255 and 7,689 of 7,689 records for two entities, plus two small entities, before a cleanup.

**Other lookups.**

| Need | Route | Lesson |
|---|---|---|
| Reference 360 lookup | `POST .../rdm-service/external/v1/search` (empty body gives 400 `RDM.0040044`: the verb exists) | L-MDM-026 |
| Fuzzy identity match | Customer Identification MCP server: `search_master_record`, then `get_master_record_details` | L-MDM-027 |
| Do not use | `.../business-entity/public/api/v1/entity/<be>/search` (404/405, or a 403 role gap) | L-MDM-028 |

---

## 6. Delete and soft-delete (L-MDM-029)

API: `DELETE .../business-entity/public/api/v1/entity/<runtimeId>/<id>?sourceSystem=<src>`; the source-system
qualifier is required.

Semantics per the Customer 360 guide (p.79):

| Action | Effect |
|---|---|
| Delete a master record | State changes to deleted; it is not removed from the data store; its source records stay active |
| Delete a source record | The master stays active while at least one contributing source is active; trust scores are recalculated |
| Delete all contributing sources | The master record is deleted automatically |
| After deletion | Deleted records cannot be updated; search excludes them unless you filter for deleted records |
| Restore | Deleted source records can be restored; trust scores are recalculated |
| Relationships | Deleting a related master removes the relationship; a record field pointing at it keeps showing it as deleted |

A UI soft delete also removes a record from API search, so an export taken afterwards will not contain it.

**Proven call and bulk recipe (L-MDM-070).**

```
DELETE https://<pod>-mdm.<domain>.informaticacloud.com/business-entity/public/api/v1/entity/<runtimeId>/<id>?sourceSystem=c360.default.system
IDS-SESSION-ID: <sessionId>
X-INFA-ORG-ID: <orgIdV3>
```

Expect **200** `{"approvalRequired":false}`; a GET of the record then returns 404. Without the parameter the answer is
**400** "Missing required parameter sourceSystem".

1. Search the first page (`POST /search/public/api/v1/search`, 500 records) and filter it client-side, for example by
   `_meta.creationDate` for a test window.
2. Delete that page with about 6 parallel calls.
3. Pause for the search index, then search again and repeat until the filter returns nothing.

Throughput was about 500 records a minute (about 27,000 records in about 50 minutes). Export first (section 5): the
deleted records leave search, so a later export misses them.

---

## 7. Before deleting an MDM installation (L-MDM-030)

Deleting MDM content (360 projects, business entities, reference entities) removes business records, not just
design assets.

1. Export every entity's records to JSON with the search union method (section 5) and reconcile counts.
2. v3-export the MDM design objects as the design backup (store it as a secret; packages can carry credentials).
3. Keep entities that live assets still use (for example an address-verifier entity used by a DQ asset).
4. Delete item by item, read back, and list anything the MDM service refuses instead of forcing it.

Record deletes are proven headless (section 6); deleting the installation's design content (360 projects, business
and reference entities) is not, so plan the Business 360 UI as the fallback for that step. Org-level order is in
[Headless Deletes & Org Cleanup](../10-migration-org-management/06-headless-deletes-org-cleanup.md).

---

## 8. Running a bulk ingest

| Concern | Practice | Lesson |
|---|---|---|
| Token lifetime | One POST per record; ~98,000 records was estimated at ~2.7 h against a 30-minute JWT. Re-mint at ~25 min or on 401 | L-MDM-033 |
| Throttling | Bounded batches, exponential backoff on 429 (no MDM ingest threshold is documented, so this is defence) | L-MDM-033 |
| Resume | Client-side tally plus a checkpoint of the last committed key | L-MDM-033 |
| First row | Ingest one real record and read it back: the only check that UI field names match your field map | L-MDM-046 |
| Existing population | Reconcile what the runtime already holds, and check the reindex job is not wedged, before a bulk load | L-MDM-032 |
| Visibility | Records appear in the UI only once search-indexed; a stuck Search Reindex job leaves search empty | L-MDM-031 |
| Queueing | Load steps above 1,000 records and index steps above 10,000 queue: expected, not a failure | L-MDM-035 |

---

## 9. Caps (L-MDM-034, documented)

| Item | Cap |
|---|---|
| Search results and export | 10,000 |
| CSV file import | 100 MB and 100,000 rows |
| Reports | 500 rows |
| Concurrent ingress and egress jobs | queue beyond 25 per pod or 5 per org |
| Ingress step queueing | load > 1,000; transform > 100,000; index for search > 10,000; generate match keys > 5,000 |
| Egress step queueing | stage > 1,000 |
| Match-and-export results | expire 4 days after the Release The Job step |
| Rejected records | kept 7 days |
| MDM session | 30 minutes idle |

---

## 10. Overturned beliefs (this area)

| Belief | Believed | Overturned by |
|---|---|---|
| Ingest with `fullName`, `sourceRecordCount` and a numeric trustScore | 2026-07-05 to 07-08 | L-MDM-019 (L-MDM-061) |
| There is no public search, list or count of MDM records | 2026-07-08 to 09-27 | L-MDM-025 (L-MDM-069) |
| Reference 360 is unavailable because `referenceDataSets` 404s | 2026-07-26 | L-MDM-026 (L-MDM-065) |
