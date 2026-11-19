# Search, Lineage & Marketplace

**Answers:** How do I search the catalog with Elasticsearch DSL and page it reliably? How do I walk and count assets?
How does CDGC produce CDI lineage, why is it missing, and how do I resolve pending connection assignments? Which Data
Marketplace objects are REST and which are UI-only?

**Read when:** building coverage counts or extracts from the catalog; a lineage answer shows "0 upstream assets" or
grey referenced nodes; a BigQuery view has no lineage; scripting Marketplace products, targets and orders.

**Key rules:**
- Search with `POST /data360/search/api/v1/search` plus `X-INFA-SEARCH-LANGUAGE: elasticsearch` (`term`, `bool`,
  `wildcard` and `exists` queries; `match` and `match_phrase` answer 400); page with `"sort": [{"core.identity":
  {"order": "asc"}}]` (unsorted `from`/`size` pages overlap and drop assets silently), dedupe by `core.identity` and
  count per class, because totals cap at 10,000 (L-CDGC-073, L-CDGC-165, L-CDGC-169, L-CDGC-077, L-CDGC-078).
- Warehouse views are `...relational.View`, not `Table`: query both classes before concluding an asset is missing
  (L-CDGC-139).
- CDI lineage needs an IICS catalog source with Lineage Discovery plus resolved connection assignments: check
  `core.resolvedStatus`, stitch each unresolved reference to its physical source with
  `connectionAssignment?operationType=MERGE` (SPLIT undoes the assignment, not edges already written), one job at a
  time, then read a target table's lineage back (L-CDGC-159, L-CDGC-140, L-CDGC-146, L-CDGC-210, L-CDGC-211).
- Rescans and assignments are necessary, not sufficient: prove lineage with a CLAIRE upstream and downstream prompt
  before telling a lineage story (L-CDGC-148).
- BigQuery views whose SQL the analyzer cannot parse get no lineage; quote the project on its own
  (`` `<project>`.<dataset>.<table> ``) (L-CDGC-151).
- Read lineage over REST hop by hop from the asset read's `lineage` segment and publish curated edges for hops no
  scanner derives (L-CDGC-181, L-CDGC-179); the `/data360/lineage/*` graph routes are still not served.
- Marketplace: create the delivery target before any order; delivery templates are UI-only (L-CDGC-096, L-CDGC-097).
- Check a lineage link before you share it: walk upstream from the BI asset and require every root to be the system of
  record; curated edges stay on the node identities they were made for, so re-check them after every rescan
  (L-CDGC-232, L-CDGC-228).

**Related:** [01 CDGC APIs & Auth](01-cdgc-apis-auth.md) ·
[02 Catalog Sources](02-catalog-sources-create-scan-update-purge.md) ·
[05 CDGC Gaps & Gotchas](05-cdgc-gaps-gotchas.md) ·
[CLAIRE GPT - Prompting Rules](../11-mcp-claire/03-claire-gpt-prompting-rules-patterns.md) · [Lessons: CDGC](lessons.md)

**Last verified:** 2026-11-03

> **Summary.** The knowledge-query form `POST /data360/search/v1/assets?knowledgeQuery=...` also works once its query
> parameters are sent. Never treat a free-text hit as a stable handle. Lineage is produced by scans (view SQL, and CDI
> mappings through an IICS source) and read through the UI or MCP. Data Marketplace is REST on the producer side;
> ratings and consumer collaboration are UI-only. UI automation for the Marketplace app:
> [Claude Working Methods & Tooling](../14-working-with-claude/).

`API` = `https://idmc-api.<domain>.informaticacloud.com`; `CDGC` = `https://cdgc-api.<domain>.informaticacloud.com`. All calls
carry the three identity headers ([01](01-cdgc-apis-auth.md) section 2.4).

---

## 1. Search endpoints

| Endpoint | Host | Body | Returns | Use it for | Lesson |
|---|---|---|---|---|---|
| `POST /data360/search/api/v1/search` (optionally `?knowledgeQuery=*&segments=all`) | idmc-api | raw Elasticsearch DSL (`term`, `bool`, `wildcard`, `exists`; `match` and `match_phrase` answer 400); header `X-INFA-SEARCH-LANGUAGE: elasticsearch` | `hits.hits[].sourceAsMap`, `hits.total.value` | exact lookups, class census, coverage counts | L-CDGC-073, L-CDGC-165 |
| `POST /data360/search/v1/assets?knowledgeQuery=<q or *>&segments=<list>` | idmc-api | `{"from":0,"size":N}` | `hits[]` with `core.identity`, `summary`, `systemAttributes` | free-text queries, quick harvest totals | L-CDGC-074 |
| `GET /data360/search/v1/assets/<identity>?scheme=internal&segments=<list>` | idmc-api | - | one asset with the chosen segments | reads and tree walks | L-CDGC-075 |
| `POST /ccgf-searchv2/api/v1/search` | cdgc-api | ES subset: `multi_match`, `term`, `match_all`, `bool` (+ `aggs`) | ES-style hits | read-back checks only | L-CDGC-081 |
| MCP `search_metadata` | MCP | natural language | asset ids and core attributes | conversational discovery | L-CDGC-100 |

GET on the search paths is 405 (they are POST). The data360 search endpoints live on `idmc-api`, not on the pod host.

---

## 2. The Elasticsearch search

### 2.1 Request and response (L-CDGC-073)

```
POST {API}/data360/search/api/v1/search?knowledgeQuery=*&segments=all
Authorization: Bearer <jwt>
IDS-SESSION-ID: <sessionId>
X-INFA-ORG-ID: <orgIdV3>
X-INFA-SEARCH-LANGUAGE: elasticsearch
Content-Type: application/json

{"from": 0, "size": 200, "query": {"term": {"core.classType": "com.infa.ccgf.models.governance.BusinessTerm"}}}

-> {"hits": {"total": {"value": <n>, "relation": "eq" | "gte"},
             "hits": [{"sourceAsMap": {"core.identity": "...", "core.externalId": "...", "core.name": "...",
                                       "core.location": "...", "core.description": "..."}},...]}}
```

### 2.2 Query cookbook

| Goal | Body (the `query` part) | Notes |
|---|---|---|
| All terms / domains / classifications | `{"term":{"core.classType":"com.infa.ccgf.models.governance.BusinessTerm"}}` (or `...Domain`, `core.DataElementClassification`) | page with `from`/`size` 200 |
| Resolve external ids | `{"terms":{"core.externalId":["<id1>","<id2>"]}}` | the way to get `core.identity` (L-CDGC-057) |
| One external id | `{"term":{"core.externalId":"<id>"}}` | same |
| Catalog-source roots | `{"term":{"core.classType":"core.Resource"}}` | one per scanned source |
| DQ rule occurrences | `{"term":{"core.classType":"com.infa.ccgf.models.governance.RuleInstance"}}` with `"size":200` | external ids `DQO-<n>`; term queries on the name do not match; scores only after the source's Data Quality capability ran (L-CDGC-144) |
| Views and tables of a dataset | `{"bool":{"should":[{"term":{"core.classType":"com.infa.odin.models.relational.Table"}},{"term":{"core.classType":"com.infa.odin.models.relational.View"}}]}}` | a dataset of views reads as "never scanned" if you count only Table (L-CDGC-139) |
| Pending connection assignments | `{"term":{"core.classType":"core.ConnectionAssignmentRecommendation"}}` | see section 9.1 (L-CDGC-159) |
| A glossary term by name | `{"term":{"core.classType":"com.infa.ccgf.models.governance.BusinessTerm"}}`, then compare `core.name` client-side | `match` and `match_phrase` answer 400; names repeat across domains, so also match the parent domain's identity in `core.location` (L-CDGC-165) |
| Every asset of one catalog source | filters on `core.origin` = `<csId>` and `elementType` = `OBJECT`, with `"sort": [{"core.identity": {"order": "asc"}}]` | complete and repeatable (1,311 fetched, 1,311 unique, twice); a `wildcard` on `core.externalId` also matches relationship documents, and a sort on `core.externalId` returned no hits (L-CDGC-169) |
| Everything | `{"match_all":{}}` | `hits.total` caps at 10000 with `relation: "gte"` |
| Profiling coverage | filter on the field `core.profiled` = True | exact field name matters: a wrong name is a 500 (L-CDGC-076); the precise query form is not recorded |
| CLAIRE coverage | presence of `core.generatedClassification` (and `core.acceptedClassification`) | e.g. an `exists` query; form not recorded |

### 2.3 Paging, caps and determinism

- **Stable paging** (L-CDGC-078): `from`/`size` with no stable sort returned overlapping pages (114 duplicates
  and 114 missing rows in a 7,464-column extract). Request one page larger than the per-source total, or add a stable sort
  key (`core.identity`, next bullet); dedupe by `core.identity`; reconcile the distinct count with the known total. Page
  until `from >= hits.total.value` or an empty page.
- **Sort on `core.identity`** (L-CDGC-169): two consecutive full reads of one catalog source, paged with `from`/`size`
  and no `sort`, returned 882 and 970 of its tables, views and columns, so lookups by name failed at random (a link
  script reported existing assets as missing). With `"sort": [{"core.identity": {"order": "asc"}}]` and a filter on
  `core.origin` + `elementType` OBJECT, instead of a wildcard on `core.externalId` (which also matches relationship
  documents), the read became complete and repeatable: 1,311 fetched, 1,311 unique, twice in a row. A sort on
  `core.externalId` returned no hits at all.
- **Cap**: totals stop at 10,000 (`gte`), so count per class or per source (L-CDGC-077).
- **Semantic ranking**: the same free-text query can return different hits and order across runs. Never cache "the top
  hit"; resolve by exact externalId or name at use time (L-CDGC-078).
- **Class filters** (L-CDGC-079): a third-party fleet's `classType` filter parameter was reported as accepted and ignored,
  but an ES `term` query on `core.classType` inside the body did filter. Use the term query and still check each hit's
  `core.classType`.
- **Unknown field = 500**, which looks like an outage; fix the field name (L-CDGC-076).
- **Query types** (L-CDGC-165): `term`, `bool`, `wildcard` and `exists` work; `match` and `match_phrase` answer 400.
  Find an asset by name with a class `term` query and a client-side compare of `core.name`.
- **429**: pace long runs (section 4.3).

---

## 3. The knowledge-query search (L-CDGC-074)

```
POST {API}/data360/search/v1/assets?knowledgeQuery=<query or *>&segments=summary,systemAttributes
{"from": 0, "size": 50}
-> {"hits": [{"core.identity": "...", "summary": {"core.name": "..."},
              "systemAttributes": {"core.classType": "...", "core.origin": "<catalogSourceId>"}},...],...}
```

- Without `knowledgeQuery` this path answers 400 `MissingServletRequestParameter`: that was the old "dead end" verdict
  (L-CDGC-123 superseded).
- `segments=all`, or a list such as `summary,systemAttributes,dataClassification`, controls what comes back.
- A `*` query's total is a quick "is anything harvested?" check (5,089 assets on one org).
- A `filterSpec` body (`[{"attribute":"core.classType","values":[...]},{"attribute":"core.origin","values":["<csId>"]}]`)
  was probed; its effect is not recorded.

---

## 4. Reading assets and walking the tree

### 4.1 One asset (L-CDGC-075)

`GET {API}/data360/search/v1/assets/<identity>?scheme=internal&segments=<list>` with segments from `summary`,
`systemAttributes`, `selfAttributes`, `customAttributes`, `neighborhood`, `dataClassification`, or `all`. For slash-free
external ids use `?scheme=external` (e.g. `DOM-<n>` or a classification id).

### 4.2 Walking Resource > Database > Schema > Table/View > Column

- Start from the catalog source's `core.Resource` asset. Each asset's `neighborhood` segment lists entries with a `type` and
  `neighbors[]`; each neighbor carries `details` (an asset URL containing `/assets/<identity>`), `neighbor` (the name) and
  `paths[].serialized`. Outgoing parent-to-child edges show `-->` and `ParentChild` in the serialized path.
- Follow only outgoing parent-to-child edges; treat types ending in Column or Field as leaves and Database, Schema, Table,
  View, Object, Project, Dataset, Resource as containers.
- For each column read `segments=summary,dataClassification`. A classification asset's `selfAttributes.core.sensitivity`
  (e.g. Email = MEDIUM) lets you count PII columns as those with a MEDIUM, HIGH or CRITICAL classification.
- A Salesforce source holds the whole org schema: filter to the objects you use or the walk exceeds a practical budget
  (L-CDGC-013).

### 4.3 Pacing (L-CDGC-013)

```python
PACE = {"s": 0.8}
def paced_get(url):
    for i in range(10):
        time.sleep(PACE["s"])
        c, r = call("GET", url)                    # call drops the cached JWT on 401 (doc 01)
        if c == 200 and isinstance(r, dict):
            PACE["s"] = max(0.5, PACE["s"] * 0.97)
            return r
        if c == 429:
            PACE["s"] = min(4.0, PACE["s"] + 0.3); time.sleep(15)
        elif c != 401:
            time.sleep(min(30, 3 * (i + 1)))
    raise RuntimeError(f"unreadable after retries: {url}")
```

---

## 5. Coverage metrics (L-CDGC-077)

| Metric | How | Watch out |
|---|---|---|
| Sources harvested | count `core.Resource` hits; check `lastScanned` per source | a configured-only source has no fresh `lastScanned` |
| Tables, columns, keys | per-class counts by source (`core.origin`) | 10,000 cap on totals |
| Profiling coverage | `core.profiled=True` | asset grain vs column grain differ (1,755 profiled assets vs 671 profiled columns) |
| CLAIRE coverage | `core.generatedClassification` present | expect far more classified than profiled (L-CDGC-064) |
| Accepted classification | `core.acceptedClassification` present | applied manually or by the auto-accept threshold |
| PII columns | classification sensitivity MEDIUM, HIGH or CRITICAL | needs the per-column walk (4.2) |
| DQ scored | `RuleInstance` hits; per-dimension scores from the asset's `dataQuality` segment (DQResult objects); per occurrence, `value` (percent), `totalCount`, `exception` and `scannedTime` in the RuleInstance's `selfAttributes` | scores only after the source's Data Quality capability ran (L-CDGC-144, L-CDGC-143, L-CDGC-166) |

State the grain in every KPI. For dashboards built on these counts see L-CDGC-107; for catalog feeds into a warehouse see
L-CDGC-101 (no IDMC connector reads CDGC metadata, so feeds are external scripts). For DQ scores, either run the catalog
Data Quality capability on rule occurrences (accepted recommendations, L-DQ-097, or created over REST, L-CDGC-161) or
build scorecards on the Data Profiling service:
[DQ Scorecards](../08-data-quality/04-dq-scorecards-warehouse-pattern-and-data-profiling-scorecards.md).

## 6. Searching in the UI

- AI search (type=Query) can return 0 for everything in an org while Keyword search works
  (`cgsearch/<id>?query=<term>&type=Keyword`): use Keyword for demos and scripted UI checks (L-CDGC-080).
- Browse in DGC Explore (source > schema > tables); the Customize/admin pages show "nothing to display" even when the catalog
  is full (L-CDGC-012).

---

## 7. Lineage: how CDGC produces it

| Source of lineage | What you must do | Result | Lesson |
|---|---|---|---|
| Database views | Put the view in the Metadata Extraction include scope, enable Lineage Discovery, rescan | Data-flow edges parsed from the view SQL | L-CDGC-087 |
| Base tables written by CDI | Nothing from the database scan: its logic is in the mapping | Containment only; add an IICS source | L-CDGC-087 |
| CDI mappings and mapping tasks | IICS catalog source with Include `Data Integration` / `<project>` / All Types and Lineage Discovery (L-CDGC-029), plus catalog sources for the physical systems | Column-level lineage source table > mapping task > landing table > next task | L-CDGC-159 |
| Endpoints of that lineage | Lineage Discovery generates and auto-accepts connection-assignment recommendations in the scan (task steps Candidate Selection, Recommendations Generation, Auto Accept Recommendations). In a new org the auto-accept left references unresolved: stitch each one headless with a `connectionAssignment` MERGE (section 9.1); MCC > Configure > Lineage does the same by hand | Referenced stubs resolve into real assets | L-CDGC-140, L-CDGC-159, L-CDGC-088 |
| Flat files a mapping reads or writes | A File System catalog source over that directory on the same Secure Agent, then a MERGE of the IICS reference (named after the directory, slashes replaced by underscores) to its `FileServer` root (section 9.1) | Each file appears upstream of the mapping task | L-CDGC-160 |
| SharePoint document libraries a mapping reads | A SharePoint Online catalog source over the site, then a MERGE of the IICS reference (which can be named after the connection's v2 id) onto that source's Site (section 9.1) | SharePoint document library > mapping task > warehouse table, the library resolved to the catalog's own asset | L-CDGC-167 |
| Salesforce objects | Salesforce source on the native Salesforce connection (ViewSetup + ViewRoles), then assign the IDMC Salesforce connection | Tasks stitched to Salesforce objects | L-CDGC-142, L-CDGC-032 |
| New or consolidated mappings | Rescan the IICS source (Metadata Extraction + Lineage Discovery) after the change | Until then the catalog and CLAIRE describe the old tasks | L-CDGC-146 |
| Objects in cloud storage that a mapping reads from an agent-folder copy | An Azure Blob Storage catalog source, the copy step writing to a directory named `/<storage-account>/<container>/`, then a MERGE of the reference onto the StorageAccount root (section 9.1) | Source system > storage > mapping > table, with the mapping's input on the scanned blob | L-CDGC-227 |
| Files loaded into the warehouse outside IDMC | Header-only copies (column names, no rows) in a folder on the scanning agent, a File System catalog source over it, one curated file-to-table edge per file (section 8) | The files become the far-left roots: file > raw > tasks > silver > gold | L-CDGC-233 |
| A database reached only through the generic JDBC type | The IICS source plus a MERGE onto the JDBC source, and curated edges for logic inside the database: the JDBC type has no Lineage Discovery | Task-level lineage; view SQL is not parsed | L-CDGC-234 |

Notes:
- A "Lineage Discovery Filter Config" group (`Filter Pivot` Include, `Filter Type` "Catalog Source Name", `Filter Value` =
  source names) limits the sources an IICS source stitches to; it was set by PUT and its effect is not recorded.
- Grey "referenced" nodes in the Lineage tab mean an unassigned connection (L-CDGC-088); MERGE-assign it (section 9.1).
- Relationship Discovery (similar columns and join keys) is not lineage (L-CDGC-087).
- Business logic kept inside a task's custom-query SQL is invisible to lineage below table level, and mapping tasks are not
  catalog assets (CLAIRE finds nothing for a task name). Visual transformations give column-level lineage (L-CDGC-091).

## 8. Lineage: how to read it, and the gaps

- **UI**: DGC > asset > Lineage tab; switch to the Data Element level and use Expand Upstream.
- **MCP**: the CDGC Metadata Search action `get_asset_details` (`id`, `scheme`) returns lineage with profile and
  descriptions (L-CDGC-100).
- **REST, hop by hop (proven 2026-10-08, L-CDGC-181)**: `GET https://idmc-api.<domain>.informaticacloud.com/data360/search/v1/assets/<identity>?scheme=internal&segments=all`
  returns a `lineage` list of `{direction inbound|outbound, hops[{distance, items[{from, to, fromType, toType, fromLocation,
  toLocation, attributes.core.associationKind}]}]}` beside the `neighborhood` segment, whose data-flow edges reach column
  level (L-CDGC-156). Only distance-1 hops were seen: walk asset by asset for a chain. The `/data360/lineage/*` graph routes
  still answer 404 (L-CDGC-085, superseded).
- **Writes (proven 2026-10-08, L-CDGC-179)**: publish curated edges as RELATIONSHIP items on
  `POST https://cdgc-api.<domain>.informaticacloud.com/ccgf-contentv2/api/v1/publish` (header `X-INFA-PRODUCT-ID: CDGC`):
  `{operation INSERT, type core.DataSetDataFlow (table to table) | core.DirectionalDataFlow (column to column), fromIdentity,
  toIdentity (external ids), sourceIdentityType and targetIdentityType EXTERNAL, attributes {core.curationStatus ACCEPTED,
  core.channels [MANUAL], core.inferred false}}`; `core.DataFlow` is refused. Use it
  for hops no scanner derives, such as Database Ingestion CDC tasks (L-CDGC-183). Undo: the same items with DELETE. An
  earlier publish of a data-flow edge came back as 207 with `items: []` and changed nothing (L-CDGC-065; that belief,
  L-CDGC-180, is superseded by L-CDGC-179).
  - **Endpoint classes** (L-CDGC-224, 2026-10-26): accepted were Salesforce Object, relational Table and View, flat file and
    a lineage-reference `core.DataSet`; refused with INVALID_RELATIONSHIP_CLASS_TYPE were PDF file assets, a SharePoint
    DocumentLibrary and an Azure Blob Container (SharePoint folder and file assets: L-CDGC-214). To show a storage hop,
    have the mapping read the object itself through a path that resolves to the storage location, or draw the edge to
    or from a reference dataset. In that round a `core.DataSetDataProcess` edge into a mapping task instance was also
    refused, which disagrees with the next bullet: re-probe before relying on either.
  - **Tasks as endpoints (L-CDGC-208)**: dataset -> task works with `type core.DataSetDataProcess` (the association the
    scanner writes). Task -> dataset is refused (INVALID_RELATIONSHIP_CLASS_TYPE) for task instances, mapping tasks and
    mappings under every association tried, so draw a dropped write as dataset -> dataset with `core.DataSetDataFlow`.
  - **One item per call** when you record results: a multi-item 207 does not return items in request order, and the items
    carry no from/to. `RELATIONSHIP_ALREADY_EXISTS` (403) means the pair exists, not that lineage shows it: one such
    pair was missing from both nodes' lineage segments 30 minutes later, so verify with the lineage segment (L-CDGC-228).
  - **Edges are pinned to node identities** (L-CDGC-228): when a mapping's input changed (a new directory gives a new
    reference and new dataset nodes), its curated upstream edge stayed on the old node and the hop vanished; after every
    IICS rescan, re-check the hop and re-publish it to the node the task now reads (an idempotent 'fix hop' script and a
    registry with undo). An older curated edge from another pipeline into a shared reference pulled that pipeline's whole
    graph in: list the inbound edges of shared reference nodes and DELETE the foreign ones.
  - **Fill the gaps a warehouse scanner leaves** (L-CDGC-231, 2026-10-28; proven on BigQuery): views whose SQL `UNNEST`s
    inline STRUCT arrays or reads `__TABLES__` metadata were cataloged with no upstream edges. Read each view's SQL from
    `<dataset>.INFORMATION_SCHEMA.VIEWS`, extract the referenced tables (skip metadata tables), compare with the view's
    inbound lineage, and publish only the missing pairs in one call (28 edges); confirm each by reading the view's
    lineage back, because a 207 carries no from/to. Count inbound edges per view after every scan.
  - **Files loaded outside IDMC** (L-CDGC-233, 2026-10-29): stage header-only copies (column names, no rows, so no
    personal data lands on the agent) on the scanning agent, catalog them with a File System source, and publish one
    curated `core.DataSetDataFlow` per file to its raw table. If IDMC itself reads the files, prefer the MERGE onto the
    File System root (section 9.1).
  - **Tableau published extracts (L-CDGC-209)**: a published data source holding a Hyper extract is cataloged as a reference
    dataset `<name>.hyper/Extract` (path carries the extract GUID), not as a Tableau DataSource; target edges there.
- **CLAIRE and fresh scans**: lineage answers lag new scans (hours in one org; lineage and NL-to-SQL still failing about 30
  minutes after a migration while glossary and PII passed), CLAIRE is blind on a source while it scans, and duplicate
  legacy sources make it pick the wrong table (L-CDGC-090). Downstream lineage is missing when an IICS source's extraction
  failed (L-CDGC-046).
- **Auto-accepted assignments are not proof.** After a COMPLETED Lineage Discovery with every recommendation
  auto-accepted (L-CDGC-140), CLAIRE still answered "0 upstream assets" for warehouse tables loaded by custom-query tasks and
  showed only view-on-table edges downstream (L-CDGC-148, unresolved). Check with an upstream and a downstream prompt before a
  lineage story. With tasks that read connection objects (not custom SQL), MERGEd references and a curated edge, CLAIRE GPT
  walked 4 upstream hops through the mapping task to the Salesforce object (L-MCP-128, 2026-10-27).
- **Check every link before you share it** (L-CDGC-232). People judge a lineage page by its two ends. Seed a script on the
  end asset (the BI dashboard, or the gold table if BI is not cataloged), walk inbound through the `lineage` segment asset
  by asset up to a node cap, map each node to a system by `core.classType` (for generic `core.DataSet` references by
  `core.location`), and FAIL the link if any root is not the source system, nodes from other projects appear, an
  expected middle system is missing, or the end asset is not the BI asset or has outbound edges. Re-run it on a loop
  while scans and merges land, then share `https://cdgc.<domain>.informaticacloud.com/asset/<id>?tabId=lineage` seeded on
  the BI asset. A typical failure: after a fresh BI scan the dashboard's upstream stops at the warehouse view until the
  BI source's warehouse reference is MERGEd (L-CDGC-201).
- **Design the mappings for that path** (L-CDGC-229): each system once, data quality inside the mapping, no second read of
  the system of record downstream (one mapping per pipeline passed where a two-mapping design failed three ways), the old
  mappings retired from the IICS source's scope, and a curated edge for the copy into storage, which no scanner draws
  ([Mapping Design & Consolidation](../04-mappings/05-mapping-design-consolidation.md) A6).
- **Walk-through copies add nothing to lineage**: an FRS copy of a mapping has no task, and an IICS source harvests a
  mapping only through an in-scope task; keep copies in a project outside the IICS source's filter (L-MIG-087,
  L-CDGC-157).
- **Renamed sources and leftover views.** A renamed source keeps its old resource name in CLAIRE's answers until it is
  rescanned (L-CDGC-147). A leftover connector `Temp_View<epoch-ms>` shows up as a downstream dependent until it is dropped and the
  source is rescanned with Metadata Change Option = Delete (L-CDGC-149).
- **View SQL the BigQuery analyzer cannot parse** (L-CDGC-151). Metadata Extraction parses each view's SQL to
  build lineage; such a view gets no lineage and looks skipped while the other views of the source parse fine.

| Scan-log message | Seen on | Fix |
|---|---|---|
| `UnsupportedOperationException` (repeated for one view) | a raw-string regex inside a CTE used as a scalar-subquery argument, IN-subquery flags in the select list, about 20 `COUNTIF` calls | simplify the view, or accept no lineage for it; prove any rewrite with a parity check first |
| `Parse error NoViableAlt` | a single backticked fully qualified name `` `<project>.<dataset>.<table>` `` | quote the project on its own: `` `<project>`.<dataset>.<table> `` |
| `Could not find matching schemas` | an include filter naming a dataset that does not exist | remove the filter entry |
| `Could not process workbook <name> ... XmlWindow.getViewpoints() is null` (Tableau, job still COMPLETED) | a dashboard window with no `<viewpoints>` in a generated TWB; with Metadata Change Option = Delete the workbook and its reference MERGEs are purged | write `<viewpoints />` in every dashboard window, republish, rescan, re-MERGE (L-CDGC-207) |

## 9. Lineage workarounds

### 9.1 Resolve pending connection assignments (L-CDGC-159)

Symptom: after an IICS (Data Integration) catalog source is scanned (typically in a new org), its task references to the
source and target connections stay unresolved, and CLAIRE answers "0 upstream assets". A Lineage Discovery run can
auto-accept recommendations (L-CDGC-140), but in a new org that auto-accept had left these references unresolved.

1. Read the IICS source's endpoint reference assets and check `core.resolvedStatus`: empty means unresolved.
2. Find the pending fix: search `{"term":{"core.classType":"core.ConnectionAssignmentRecommendation"}}`. Each hit names
   the target catalog source, a score (100 seen), the number of objects it covers and action NONE.
3. Stitch each connection reference of the IICS source to its physical catalog source, headless:

   ```
   POST {CDGC}/ccgf-contentv2/api/v1/assignment/connectionAssignment?operationType=MERGE     (the three identity headers)
   {"sourceRootAsset": {"externalId": "<iicsSourceId>_<CONN>://<CONN>~core.DataSource",
                        "origin": "<iicsSourceId>",
                        "location": "<iicsSourceId>://<iicsSourceId>/<iicsSourceId>_<CONN>/<CONN>"},
    "targetRootAsset": [{"externalId": "<sourceId>://<DATABASE>~com.infa.odin.models.relational.Database",
                         "origin": "<sourceId>", "isCaseSensitive": false,
                         "location": "<sourceId>://<sourceId>/<DATABASE>"}],
    "initialAssignment": true, "modifyAssignment": false}

   -> a job id
   ```

   - The same body with `operationType=SPLIT` undoes the stitch. It removes the assignment, not the edges the source
     already holds: after a completed SPLIT the old source's tables still showed the task and Tableau hops (`origin` =
     that source), so a replaced source keeps a duplicate copy of the lineage until its metadata is purged (L-CDGC-211).
   - **One job at a time** (L-CDGC-210). Each MERGE or SPLIT job takes about 5 minutes. A SPLIT started on a reference
     while its MERGE was still running made both jobs FAILED ('Merge/Split Operation FAILED', no error text in
     `outputProperties`), although the MERGE's Bulk Ingestion step completed and its edges appeared. Poll
     `GET https://idmc-api.<domain>.informaticacloud.com/data360/observable/v1/jobs/<jobId>?expandChildren=TASK-HIERARCHY` to COMPLETED before starting the next
     job, and read the lineage back whatever the status says.
   - `ASSIGN`, `UNASSIGN`, `ACCEPT` and `CREATE` fail the enum conversion: the accepted values are the catalog UI's
     Merge and Split.
   - The job also completes for a reference that does not exist, so a completed job proves nothing.
   - **Flat files** (L-CDGC-160): a mapping that reads or writes files through a flat-file connection shows a reference
     named after the file directory, slashes replaced by underscores
     (`<iicsSourceId>_<dir_with_underscores>://<dir_with_underscores>~core.DataSource`). Catalog that directory with a
     File System catalog source on the same Secure Agent, then MERGE the reference to the File System root:
     `{"externalId": "<fsSourceId>://FileServer~com.infa.odin.models.file.FileSystem", "origin": "<fsSourceId>",
     "isCaseSensitive": true, "location": "<fsSourceId>://<fsSourceId>/File Server"}`. Each file then appears upstream of
     the mapping task.
   - **SharePoint libraries** (L-CDGC-167): an IICS catalog source can name a connection reference after the
     connection's v2 id instead of its name (`<iicsSourceId>_<connId>://<connId>~core.DataSource`), so list references
     by `core.reference` and class `core.DataSource`, not by connection name. MERGE it onto the SharePoint Online catalog
     source's Site: `{"externalId": "<spSourceId>://<site title>~com.infa.odin.models.file.sharepoint.Site", "origin":
     "<spSourceId>", "isCaseSensitive": false, "location": "<spSourceId>://<spSourceId>/<site title>"}`. Lineage then
     reads SharePoint document library > mapping task > warehouse table, with the library resolved to the catalog's own
     asset (the job COMPLETED, and the table's lineage walk showed it).
   - **Salesforce** (L-CDGC-190): MERGE the reference `<iicsSourceId>_<CONNECTION NAME>://<CONNECTION NAME>~core.DataSource` onto the Salesforce source's Organization root: `{"externalId": "<sfSourceId>://<OrgName>~com.infa.odin.models.Salesforce.Organization", "origin": "<sfSourceId>", "isCaseSensitive": false, "location": "<sfSourceId>://<sfSourceId>/<OrgName>"}`. Field-level hops showed without a rescan (2026-10-12).
   - **Object storage through an agent-folder copy** (L-CDGC-227, 2026-10-26): when a copy step (a File Ingestion task or
     a pre-processing command) puts files in an agent folder, the reference is named after that directory, and a MERGE
     onto the storage source's Container root placed the nodes at `<storage-account>/<container>/home/<user>/inbox/<file>`,
     where no scanned blob sits, so the input kept no upstream. Make the paths equal: have the copy step write to
     `/<storage-account>/<container>/`, point the flat-file connection there, and MERGE the reference
     `_<storage-account>_<container>` onto the StorageAccount root: `{"externalId":
     "<storageSourceId>://<storage-account>~com.infa.odin.models.file.azureblob.StorageAccount", "origin":
     "<storageSourceId>", "isCaseSensitive": false, "location": "<storageSourceId>://<storageSourceId>/<storage-account>"}`.
     Proven on Azure Blob; other object stores whose scanner roots at an account or bucket should match paths the same
     way (untested).
   - **SPLIT does not stop re-assignment** (L-CDGC-226): the catalog resolves references by location, so a SPLIT reference
     was ASSIGNED again at the next scan; change the scanning source's scope instead.
   - **No target lineage** for a task writing through the Tableau V3 connector: the scanner logs 'Unknown writer type: TableauV3_extracts Writer' and drops the task's graph (L-CDGC-189).
4. Prove the stitch by reading a target table's lineage: it hops through the mapping task to its sources and lookups. It
   showed without another scan.
5. Check `core.resolvedStatus` again, then ask CLAIRE for upstream and downstream lineage of one target table
   (L-CDGC-148).

If the graph is still empty: tasks that read through custom SQL may not resolve into table-level lineage (L-CDGC-148);
keep a static lineage feed for dashboards meanwhile.

### 9.2 Other workarounds

- **Probe fields** (L-CDGC-089): prove source > bronze > silver > gold by checking each key column exists at every layer in
  the warehouse INFORMATION_SCHEMA and cross-checking the documented mapping edges.
- **Overlays** (L-CDGC-089): roll governing DQ rules up to each node (worst failing severity, rule count) and flag nodes
  that back a Marketplace product, from catalog exports plus governance views.
- **Classification propagation** down lineage as a reviewed worklist (L-CDGC-069).

---

## 10. Data Marketplace: object model and chain

| Object | Route | Notes |
|---|---|---|
| Category | `GET/POST /data360/marketplace/api/v1/categories` | 200/201 |
| Data collection | `GET/POST /data360/marketplace/api/v1/dataCollections`; `GET /api/v2/data-collections` | 201, PUBLISHED, with a category |
| Data asset (product) | `GET/POST /data360/marketplace/api/v1/dataAssets` | 201, PUBLISHED; `technicalAssetName` points at the governed physical asset; `PUT` documented |
| Data elements | `/api/v1/dataAssets/<id>/dataElements` | GET/POST/PUT documented only |
| Terms of use | `GET/POST /data360/marketplace/api/v1/termsOfUse` | `type` CONSTRAINED / NEUTRAL / PERMISSIVE, `acknowledgement`, `status` ENABLED |
| Delivery format, method, template | `GET {CDGC}/cdmp-marketplace/api/v1/provisioning/{deliveryFormats,deliveryMethods,deliveryTemplates}` | reads only; `objects[]` with the UUIDs targets and orders need; template create is UI-only |
| Delivery target | `GET/POST /data360/marketplace/api/v2/delivery-targets` | 201; one per collection |
| Order | `POST /data360/marketplace/api/v1/orders` or `/api/v2/orders` | 201; PENDING until fulfilled; COMPLETE with access AVAILABLE |

**The chain** (L-CDGC-097): Delivery Format + Delivery Method > Delivery Template (an Automatic template grants
access with no manual task) > a Delivery Target per collection > an Order, which fulfils and grants access. Orders placed
before a target exists stay PENDING and do not recover.

## 11. Marketplace routes, walls and hints

- Producer routes are REST (L-CDGC-092 to L-CDGC-095): re-GET after every write (anti-false-green).
- The bare `{CDGC}/cdmp-marketplace/api/v1/provisioning` answers 500 (wrong shape, not an absent service); use the
  sub-resources (L-CDGC-095).
- `/data360/marketplace/api/v2/delivery-targets/templates` is the wrong plane (GET 400, POST 405) (L-CDGC-094).
- **UI-only** (L-CDGC-096, L-CDGC-098): delivery template creation (405 on every verb), ratings (`PUT.../ratings` 405),
  stakeholders and comments (405), consumer chat, and approval or access-key verbs on orders (405). `PUT /dataCollections/<id>`
  with stakeholder ids echoes 200 without persisting.
- **Automating the template UI** (L-CDGC-096): the Marketplace app (`https://cdmp-app.<domain>.informaticacloud.com/`) stalls
  headless because of cross-origin bootstrap calls, so drive it in a headed browser (xvfb on servers). Setup > Delivery uses
  react-select dropdowns (options match `[class*='-option']`; `role=option` belongs to a background grid and Escape closes
  the modal); fields carry `data-testid` values such as `field_deliveryType`, `field_deliveryFormatIds`,
  `field_deliveryMethodIds`.
- A probe of `/data360/marketplace/v1/dataAssets` (no `/api/`) 404'd: always include the `/api/` infix
  (L-CDGC-137 superseded).

## 12. MCP coverage

| Server | Actions | Notes | Lesson |
|---|---|---|---|
| CDGC Metadata Search | `search_metadata`, `get_asset_details` | the only lineage read | L-CDGC-100 |
| Data Provisioning | `list_data_collections`, `list_delivery_targets` (returns collection detail, not a target list), `checkout_data_order` (dataCollectionId, justification, targetRef) | the checkout raises a governed access request | L-CDGC-099 |

A small local stdio MCP shim over the public Marketplace API can offer the same three actions to Claude. Catalog-keyed DQ
agent tools return an empty `END_OF_ANSWER` for assets that are not cataloged (L-CDGC-100). Details:
[CLAIRE & MCP](../11-mcp-claire/).

---

## 13. Overturned beliefs (kept so nobody re-learns them)

| Earlier belief (dates) | Overturned by (date) |
|---|---|
| The search API needs an undiscovered parameter; verify in the Explore UI (until 2026-06-28) (L-CDGC-122) | The Elasticsearch endpoint with `X-INFA-SEARCH-LANGUAGE` (2026-06-28) (L-CDGC-073) |
| `data360/search/v1/assets` is a dead end (2026-06-28 to 2026-07-25) (L-CDGC-123) | It works with `knowledgeQuery` and `segments` (2026-09-24) (L-CDGC-074) |
| Marketplace publishing and checkout are UI-only (early July 2026; restated 2026-09-12) (L-CDGC-132) | Data assets, collections, categories, terms, targets and orders create over REST (2026-07-04/05) (L-CDGC-092, L-CDGC-093) |
| Glossary, Marketplace and Reference 360 have no REST on a trial org (2026-06-29) (L-CDGC-137) | Wrong host or missing `/api/` infix (2026-07-04) (L-CDGC-005) |
| No lineage-graph REST: read lineage through MCP (2026-07-25 to 2026-10-07) (L-CDGC-085) | The asset read's `lineage` and neighborhood segments give every hop (2026-10-04, 2026-10-08) (L-CDGC-156, L-CDGC-181) |
| Lineage edges cannot be written: the publish is a silent no-op (2026-08-20 to 2026-10-07) (L-CDGC-180, superseded) | RELATIONSHIP items with `core.DataSetDataFlow` or `core.DirectionalDataFlow` (2026-10-08) (L-CDGC-179) |
| Pending connection assignments are accepted in MCC: the accept route is live but its body is unknown (`operationType=ASSIGN`, UNASSIGN to reverse) (2026-09-30) (L-CDGC-086) | `connectionAssignment?operationType=MERGE` stitches each reference, SPLIT undoes it, and a lineage read-back proves it (2026-10-06) (L-CDGC-159) |

## Lessons cited in this doc

L-CDGC-012, 013, 032, 046, 057, 064, 065, 069, 073 to 085, 087 to 101, 107, 139, 140, 142 to 149, 159, 160, 161, 165,
166, 167, 169, 207 to 211, L-DQ-097, and the superseded L-CDGC-086 (superseded by L-CDGC-159), L-CDGC-122 (superseded by L-CDGC-073), 123, 132,
137.
Full text: [Lessons: CDGC](lessons.md).
