# CDGC Gaps & Gotchas

**Answers:** What in CDGC is still not headless, and what is the workaround? Which "UI-only" or "not entitled" verdicts
were wrong, and why? Which gotchas make a scan, a search or a lineage answer look broken? What is still unresolved?

**Read when:** before calling anything in the catalog a wall; when a catalog result looks wrong and the topic doc has no
answer; when planning a migration or a demo that depends on lineage or CLAIRE.

**Key rules:**
- The walls left are narrow: deleting a source definition, bulk-accepting CLAIRE classifications, stakeholder
  assignment, DAM policy authoring, and Marketplace delivery templates and consumer features (L-CDGC-047, L-CDGC-061,
  L-CDGC-066, L-CDGC-067, L-CDGC-096). Connection assignment is headless since 2026-10-06
  (`connectionAssignment?operationType=MERGE`, L-CDGC-159), lineage is read hop by hop since 2026-10-08 (L-CDGC-181,
  which supersedes L-CDGC-085), and a scan is cancelled over REST since 2026-10-26 (L-CDGC-221, L-CDGC-225; the old wall
  L-CDGC-040 is superseded).
- Most "UI-only" and "not entitled" verdicts were wrong hosts, missing headers or an empty catalog: check hosts, headers
  and a bogus twin before deciding (L-CDGC-005, L-CDGC-006, L-CDGC-007).
- An empty catalog is unpopulated: scan one small source and search again before raising anything (L-CDGC-007).
- Re-probe a wall whenever the build, host, header set or tooling changes, and record host, headers, verb and status
  (L-CDGC-010).
- Shared-host and parser traps make healthy scans look broken: `/tmp/poifiles` permissions, BigQuery view SQL, include
  filters naming missing datasets, a Snowflake role that cannot read tags (L-CDGC-150, L-CDGC-151, L-CDGC-168).

**Related:** [01 CDGC APIs & Auth](01-cdgc-apis-auth.md) ·
[02 Catalog Sources](02-catalog-sources-create-scan-update-purge.md) ·
[04 Search, Lineage & Marketplace](04-search-lineage-marketplace.md) ·
[CLAIRE & MCP](../11-mcp-claire/) · [Lessons: CDGC](lessons.md)

**Last verified:** 2026-11-03

> **Summary.** CDGC is the most headless IDMC family: catalog-source create, update, rename and purge, scans, search,
> glossary, links, dictionary, manual classification, lineage connection assignment, catalog DQ rule occurrences and
> their scoring all work over REST. This page is the register
> of what is still true, what was overturned, and what is still unresolved. Cost of scans and metadata operations:
> [IPU, Metering & Licensing](../13-ipu-cost/).

---

## 1. Headless capability matrix

| Capability | State | How | Lesson |
|---|---|---|---|
| Three-header auth with a `cdlg_app` JWT | HEADLESS | identity `jwt/Token` | L-CDGC-001, 002 |
| List source types | HEADLESS | `GET.../datasourceTypes` | L-CDGC-016 |
| Read a type's option schema per capability | HEADLESS | `GET.../type/<Type>/capability/<Capability>/configuration` | L-CDGC-016 |
| Create a catalog source | HEADLESS | multipart `POST.../datasources` (part `dataSource`) | L-CDGC-014 |
| Create a SharePoint Online source | HEADLESS | connection URL = the tenant root, `Subsite_URL` = the full site URL; every Scanner Configuration option sent on create | L-CDGC-162 |
| Change filters, change option, profiling and lineage options | HEADLESS | multipart `PUT.../datasources/<id>`, with `id` repeated in the JSON part | L-CDGC-020, 163 |
| Rename a source | HEADLESS | multipart `PUT.../datasources/<id>` with the new `name`; update name-keyed Lineage Discovery filters and rescan | L-CDGC-141, 147 |
| Run a scan | HEADLESS (IPU-metered) | `POST /data360/executable/v1/catalogsource/<id>` | L-CDGC-034 |
| Poll and list jobs | HEADLESS | `data360/observable` | L-CDGC-037 |
| Create a DQ rule occurrence | HEADLESS | `ccgf-contentv2/api/v1/publish` of a RuleInstance plus its column relationship (header `X-INFA-PRODUCT-ID: CDGC`), then `ccgf-ruleautomation/api/v1/dataQuality/sync`; bind a column of the rule's input type | L-CDGC-161, 170 |
| Catalog DQ scoring | HEADLESS | `capabilityNames: ['Data Quality']` with a runtime environment in the Scope groups; per-dimension scores from the `dataQuality` segment, per-occurrence `value`, `totalCount` and `exception` in the RuleInstance's `selfAttributes` | L-CDGC-143, 144, 166 |
| Delete a DQ rule occurrence | HEADLESS | `DELETE.../content/v1/assets/<identity>?scheme=internal` on the RuleInstance | L-CDGC-144 |
| Edit a rule occurrence's text | NO (read-only; copied once from the rule specification) | fix the specification, recreate the occurrence | L-CDGC-145 |
| Cancel a scan | HEADLESS (2026-10-26) | `POST https://cdgc-api.<domain>.informaticacloud.com/ccgf-orchestration-management-api-server/api/v1/jobs/<jobId>/operations/cancel`; poll for CANCELLED (1-2 min in Test Connection, 50+ min once extraction runs) | L-CDGC-221, 225 (L-CDGC-040 superseded) |
| Read which capabilities a source type offers | HEADLESS | `GET .../type/<Type>/capability/<Capability>/configuration`: 404 = not offered (the generic JDBC type has no Lineage Discovery) | L-CDGC-234 |
| Purge a source's metadata | HEADLESS | `DELETE.../datasources/<id>` | L-CDGC-047 |
| Delete a source definition | UI-ONLY | MCC > Catalog Sources | L-CDGC-047 |
| Search and read assets | HEADLESS | `search/api/v1/search` (`term`, `bool`, `wildcard`, `exists`; not `match`; page sorted on `core.identity`), `search/v1/assets` | L-CDGC-073 to 075, 165, 169 |
| Glossary domains and terms: create, rename, redefine | HEADLESS | `data360/content/v1/assets` POST / PATCH | L-CDGC-050 to 053 |
| Delete a Published term | UNRELIABLE (reported deleted, stayed) | DELETE + search read-back | L-CDGC-059 |
| Data dictionary descriptions | HEADLESS | PATCH `summary` (technical assets: `core.description` alone) | L-CDGC-054, 164 |
| Term-to-asset links | HEADLESS | PATCH `glossary` | L-CDGC-056 |
| Apply a classification manually | HEADLESS | PATCH `dataClassification` | L-CDGC-060 |
| Bulk-accept CLAIRE classifications | UI lever (auto-accept threshold + rescan); a browser-captured job is disputed | MCC capability config | L-CDGC-061, 063 |
| Steward / owner assignment | UI-ONLY (not re-probed since) | MCC > Associations > Stakeholders | L-CDGC-066 |
| DAM policy authoring | UI-ONLY on probed orgs | UI; pushdown stand-in | L-CDGC-067 |
| Relationship publish (term to column) | HEADLESS | `ccgf-contentv2/api/v1/publish` (207) | L-CDGC-065 |
| Lineage edge write (curated) | HEADLESS (2026-10-08) | `ccgf-contentv2/api/v1/publish` RELATIONSHIP items with `core.DataSetDataFlow` (tables) or `core.DirectionalDataFlow` (columns) | L-CDGC-179 |
| Lineage production (IICS source + Lineage Discovery) | HEADLESS; recommendations auto-accept in the scan | `POST.../catalogsource/<id>` with Lineage Discovery | L-CDGC-029, 140 |
| Connection assignment (stitch an IICS reference to its physical source) | HEADLESS (2026-10-06) | `POST.../ccgf-contentv2/api/v1/assignment/connectionAssignment?operationType=MERGE`; SPLIT undoes; verify by a lineage read-back; a SharePoint reference (which can be named after the connection's v2 id) MERGEs onto the SharePoint source's Site | L-CDGC-159, 160, 167 |
| Lineage read | HEADLESS hop by hop (2026-10-08); the graph routes are not served | `GET .../assets/<identity>?scheme=internal&segments=all` (`lineage` and neighborhood segments); MCP `get_asset_details` | L-CDGC-181, L-CDGC-156 |
| Marketplace producer objects | HEADLESS | `data360/marketplace/api/v1` and `/api/v2` | L-CDGC-092 to 095 |
| Marketplace delivery template | UI-ONLY (headed browser) | Marketplace app | L-CDGC-096 |
| Marketplace ratings, stakeholders, chat, approvals | UI-ONLY | - | L-CDGC-097, 098 |
| QuickLook | CLIENT INSTALL | browser extension | L-CDGC-070 |
| Carry CDGC content in a v3 package | NO (`MigrationSvc_034`) | rebuild through the APIs | L-CDGC-071, 104 |

---

## 2. Walls still standing, with their evidence

1. **Cancelling a scan is no longer a wall** (2026-10-26): `POST .../ccgf-orchestration-management-api-server/api/v1/jobs/<jobId>/operations/cancel`
   answered 200 from the console and from a script; a stuck job holds the source lock (runs 406, delete 400) until it reaches
   CANCELLED (L-CDGC-221, L-CDGC-225; L-CDGC-040, whose variants all answered 404/405, is superseded).
2. **Source definitions are deleted only in MCC**; REST DELETE purges metadata (L-CDGC-047).
3. **Bulk acceptance of CLAIRE-generated classifications**: 37+ data360 variants 404/405; the lever is the auto-accept
   threshold on a rescan (L-CDGC-061; not re-probed against the content-API segments).
4. **Stakeholder assignment**: 100+ variants 404/405; echo-only 200 on a Marketplace collection PUT (L-CDGC-066; not
   re-probed since).
5. **DAM policies**: no policy REST on the probed orgs while the engine runs (L-CDGC-067; org-scoped verdict).
6. **Lineage graph routes**: `/data360/lineage/*` 404 on 25+ variants. No longer a wall for reading lineage: the asset
   read's `lineage` segment gives every hop (L-CDGC-181, 2026-10-08; L-CDGC-085 is superseded).
7. **Lineage edge writes**: no longer a wall: curated RELATIONSHIP items with `core.DataSetDataFlow` or
   `core.DirectionalDataFlow` are written (L-CDGC-179, 2026-10-08; the belief, L-CDGC-180, is superseded). Some endpoint
   classes are refused (PDF files, SharePoint DocumentLibrary, Blob Container: INVALID_RELATIONSHIP_CLASS_TYPE; L-CDGC-224):
   draw those hops to a reference dataset.
8. **Marketplace delivery templates, ratings, stakeholders, consumer chat, order approvals** (L-CDGC-096, L-CDGC-098;
   405s).
9. **QuickLook** is a per-user client install (L-CDGC-070).
10. **CDGC content does not travel in a v3 package** (L-CDGC-071).
11. **A rule occurrence's TechnicalDescription is read-only**: fix the rule specification and recreate the occurrence
    (L-CDGC-145).

Re-probe any of these when the build, host, header set or your tooling changes. Record the host, headers, verb, status and
date of each new verdict. A Salesforce-connection-type "wall" fell on such a re-check (L-CDGC-142), and so did accepting
a connection assignment: `connectionAssignment?operationType=MERGE` stitches each reference headless (2026-10-06,
L-CDGC-159).

---

## 3. When "not entitled" was really an empty catalog

The same mistake cost days more than once. What it looked like, and what was actually true:

| Symptom seen | Read at the time as | Actually | Settled by |
|---|---|---|---|
| Login `products[]` listed only "Integration Cloud"; five guessed data360/ccgf paths (such as `/data360/search/v1/health`, `/data360/search/v2/query`, `/data360/models/v1/models`, `/ccgf-cataloging/api/v1/catalogSources`) 404'd on the pod host | CDGC not entitled; ask the parent-org owner for a grant | Wrong hosts and paths; the catalog was simply unpopulated | RE selections showed `Data Governance and Catalog` enabled and the metadata engines RUNNING; a `cdlg_app` JWT search returned 5,089 assets and 15 existing sources; sources, scans, glossary and dictionary were then created headless (L-CDGC-007) |
| Every data360 path answered 200 with zero bytes | Not licensed | A partially mounted gateway; CDGC privileges were present | Privilege read; bogus-twin tests (L-CDGC-006) |
| Glossary, Marketplace and Reference 360 probes 404'd on a trial org's platform host | No REST for those products | Wrong host, and `/marketplace/v1/` instead of `/marketplace/api/v1/` | Marketplace created over REST; glossary over content (L-CDGC-005) |
| A Salesforce source refused with "no permissions to access connections which are selected" | The connection type cannot be scanned | Not a type wall; the same source on the same native connection scanned | Retry with the Metadata services selected (L-CDGC-142) |
| Catalog-keyed MCP DQ tools returned SUCCESS with an empty `END_OF_ANSWER` | DQ agent broken, or not entitled | The asset was not cataloged | Scan first (L-CDGC-100) |

**Rules that came out of it:**
- An empty catalog means unpopulated. Scan one small source and search again before raising anything.
- Decide entitlement from runtime-environment services, agent engines, privileges and a real create; never from `products[]`
  or a guessed 404 (L-CDGC-007).
- **Governance is org-scoped, not runtime-environment-scoped** (L-CDGC-009): every runtime environment in an org sees the
  same catalog, glossary, classifications and DQ rules. A "second environment" in the same org has nothing to mirror;
  parity can drift only on RE-bound things (agent versions, per-environment connections, the task set) and on which
  warehouse each catalog source points at. True isolation needs a second org. When a check says "governance differs between
  environments", suspect the probe.

---

## 4. Overturned beliefs, in date order

| Believed | Belief | Overturned | By | Lessons |
|---|---|---|---|---|
| 2026-06-27 to 2026-07-25 | Scans can only be triggered in the UI; the ccgf-auth-pep 500 is a platform bug | 2026-06-28 | three headers + non-empty `capabilityNames` | L-CDGC-120 -> 034 |
| 2026-06-27 | `readyToRun=false` blocks source creation until support fixes it | 2026-06-28 / 2026-09-24 | scans unaffected; creates validated with `IDS-SESSION-ID` | L-CDGC-136 -> 022 |
| 2026-06-28 | 406 + zero profiled columns = stuck scan (root cause) | 2026-06-28 | native profiling engine crash | L-CDGC-121 -> 044 |
| until 2026-06-28 | Search needs an undiscovered parameter; verify in the UI | 2026-06-28 | ES endpoint + `X-INFA-SEARCH-LANGUAGE` | L-CDGC-122 -> 073 |
| 2026-06-29 | Glossary, Marketplace, Reference 360 have no REST (platform-host 404s) | 2026-07-04 | wrong host / missing `/api/` | L-CDGC-137 -> 005 |
| until 2026-07-04 | An INFACore 404 means not entitled | 2026-07-04 | INFACore is a client SDK | L-CDGC-131 -> 011 |
| early July 2026 (restated 2026-09-12) | Marketplace publishing and checkout are UI-only | 2026-07-04 | REST creates with PUBLISHED status | L-CDGC-132 -> 092 |
| until 2026-07-06 | DAM controls cannot be demonstrated without entitlement | 2026-07-06 | pushdown views | L-CDGC-133 -> 067 |
| 2026-07-08 | The observable path form is disputed | 2026-07-10 | list needs `/api/`, single poll does not | L-CDGC-135 -> 037 |
| 2026-07-25 | Zero-byte 200s mean not licensed | 2026-07-25 | privileges present; gateway artifact | L-CDGC-130 -> 006 |
| 2026-07-25 | An API Manager 503 means routed but empty | 2026-07-26 | bogus paths 503 too | L-CDGC-138 -> 105 |
| 2026-07-25 to 2026-09-13 | The scan capability is `CATALOG_EXTRACT` | 2026-08-20 / 2026-09-28 | display names | L-CDGC-134 -> 035 |
| 2026-06-28 to 2026-07-25 | `data360/search/v1/assets` is a dead end | 2026-09-24 | `knowledgeQuery` + `segments` | L-CDGC-123 -> 074 |
| 2026-07-04 to 2026-08-20 | Source types can only be picked in MCC | 2026-09-24 | `datasourceTypes` | L-CDGC-124 -> 016 |
| 2026-06-28 to 2026-07-25 | Glossary, domains, classification have no REST create; content is misrouted | 2026-09-24 | `data360/content/v1/assets` | L-CDGC-125 -> 051 |
| 2026-07-04 to 2026-07-25 | Term-to-column binding is UI-only | 2026-09-24 | PATCH `glossary` segment | L-CDGC-126 -> 056 |
| 2026-08-18 to 2026-09-28 | Source registration and deletion are MCC-only where the data360 prefix is not routed | 2026-09-24 / 2026-09-29 | ccgf multipart create; REST purge | L-CDGC-128 -> 014 |
| 2026-09-21 to 2026-09-24 | The org has no CDGC entitlement | 2026-09-24 | RE selections, engines, real creates | L-CDGC-129 -> 007 |
| 2026-06-29 to 2026-08-20 | Object selection, capability config and rebinding are MCC-only | 2026-09-25 | multipart PUT | L-CDGC-127 -> 020 |
| 2026-07-09 | Rule occurrences have no API; reading scores means scraping the Score tab | 2026-09-30 | RuleInstance assets found by class and deleted by the content API; scores from the `dataQuality` segment (and created over REST since 2026-10-06, L-CDGC-161) | L-CDGC-082 -> 144 |
| 2026-07-09 | Running only the Data Quality capability returns 406 | 2026-09-30 | DQ alone runs with a runtime environment in the Scope groups | L-DQ-044 -> L-CDGC-143 |
| 2026-09-29 | A Salesforce source on a legacy v2 connection type cannot scan | 2026-09-30 | the same source scanned on the native connection | L-CDGC-031 -> 142 |
| 2026-07-25 to 2026-10-07 | No lineage-graph REST: read lineage through MCP | 2026-10-08 | the asset read's `lineage` and neighborhood segments | L-CDGC-085 -> 156, 181 |
| 2026-08-20 to 2026-10-07 | Lineage edges cannot be written: the publish is a silent no-op | 2026-10-08 | RELATIONSHIP items with `core.DataSetDataFlow` / `core.DirectionalDataFlow` | L-CDGC-180 -> 179 |
| to 2026-10-25 | There is no REST cancel for a running scan; cancel in MCC | 2026-10-26 | `POST .../jobs/<jobId>/operations/cancel`, from the console and from a script | L-CDGC-040 -> 221, 225 |
| 2026-09-30 | Connection assignments cannot be accepted headless: the accept call (`operationType=ASSIGN`) has an unproven body, so accept in MCC | 2026-10-06 | `connectionAssignment?operationType=MERGE`, SPLIT undoes; a lineage read-back proves it | L-CDGC-086 -> 159 |

---

## 5. Gotchas by theme

**Auth and hosts**
- Only-`INFA-SESSION-ID` helpers get 401 on data360 (L-CDGC-003).
- data360 on the pod host 404s; `<pod>-cdgc` has no DNS (L-CDGC-005).
- data360 can fake-200 (zero bytes, identical for bogus twins) (L-CDGC-006).
- The data360 catalog-source prefix flipped between 200 and empty-404 on one org (L-CDGC-019).
- The asset and search APIs return 429 under load (L-CDGC-013), and so do bursts of description PATCHes: back off and
  retry (L-CDGC-164).
- No vendor guide: treat every route as a dated probe (L-CDGC-010).

**Catalog sources and scans**
- Create needs multipart, `custom` + `endOfLife`, no trailing slash, `IDS-SESSION-ID` (L-CDGC-014).
- No per-catalog-source permission route was found: guessed `datasources/<id>/permissions`-style paths 404 like a bogus id,
  and the platform object-permissions API refuses catalog-source UUIDs. A user who must not see other sources gets no
  catalog role (L-CDGC-195).
- An update (multipart PUT) must repeat `id` in the JSON part, or it answers 400 'dataSource id in request path and body
  do not match' (L-CDGC-163).
- SharePoint Online: the connection URL is the tenant root and `Subsite_URL` the full site URL. The site URL as the
  connection URL fails the scan with AADSTS500011 (resource principal not found), a relative subsite with 'no protocol:
  sites/<site>/_api/web'; a create that omits any Scanner Configuration option answers 500 (L-CDGC-162).
- The list can come back empty (L-CDGC-018).
- PostgreSQL filters are `schema.*` (L-CDGC-026); use the native connector (L-CDGC-023).
- `Retain` keeps dead objects; set `Delete` before rescans (L-CDGC-028).
- Profiling PARTIAL_COMPLETED: pgvector, a column named `rows`, transient 503s; the job API shows no error (L-CDGC-043).
- Metadata Extraction PARTIAL_COMPLETED on every run ("Total objects processed count N is the same as objects count with
  errors") on a host shared by two agent OS users: `/tmp/poifiles` was created 755 by the first; `chmod 1777`
  (L-CDGC-150).
- `GET /api/v2/connection/source/<connId>` answers 200 `[]` even for a known-good connection: it proves nothing about
  table visibility; a Metadata Extraction run does (L-CDGC-150).
- A Snowflake Metadata Extraction ends PARTIAL_COMPLETED, with no message in the job tree, when the role cannot read
  tags ('Unable to resolve TAGS objects from SNOWFLAKE' in the scanner's Sync log), although every table and view was
  extracted: read the scanner log before treating a partial as a failure (L-CDGC-168).
- Data Quality runs alone only with a runtime environment in the Scope groups; otherwise Rule Profiling fails in 0 s with
  no error text (L-CDGC-143).
- Cloning a DQ-enabled source brings auto-generated `DQ_Capability_Schedule_*` schedules; switch its automation off
  (L-CDGC-152).
- An include filter naming a dataset that does not exist logs "Could not find matching schemas" (L-CDGC-151).
- Scanner services are heavy; one source at a time (L-CDGC-045).
- An IICS source stores a password and breaks on rotation (L-CDGC-030); one IICS rescan kept failing at
  extraction after flat-file tasks were added (open, L-CDGC-046).
- A Tableau scan hangs in Test Connection, with no timeout, when an in-scope workbook reads a warehouse that is gone: the
  lineage-stitching check opens that connection; the hung job blocks the next scan with 406 until cancelled (L-CDGC-223).
- A cancel sent during Catalog Source Extraction can sit CANCEL_REQUESTED for 50+ minutes (L-CDGC-225).
- A SPLIT does not hold: the catalog assigns references by location, so the next scan assigns it again (L-CDGC-226).
- An Azure Blob Storage V3 catalog source refuses the Hosted Agent (DISPATCH_REJECTED) although its connection tests there
  (L-CONN-129).
- Plan about an hour for rescanning a full lineage chain on one small agent, one job at a time (L-CDGC-230); run tunnel
  helpers as their own process (L-ENV-099).
- The generic JDBC type offers no Lineage Discovery (L-CDGC-234).
- A catalog source holding a connection blocks the connection's delete (L-CDGC-048).
- Monitor can show orphan RUNNING rows after a source delete (L-CDGC-042).

**Glossary, links, classification**
- Slash external ids break GET-by-path (400): resolve by search (L-CDGC-057).
- External ids embed the source id; DOM numbers differ per org (L-CDGC-058).
- Deleting a Published term can be a silent no-op (L-CDGC-059).
- A scan can blank curated descriptions (L-CDGC-055).
- A technical asset (table, view, column) takes a description PATCH of `core.description` alone; with `core.name` it
  answers 400 'Asset name update not supported for technical assets' (L-CDGC-164).
- Term names repeat across domains: an idempotent create matches the name AND the parent domain, or it reuses another
  domain's term (L-CDGC-165).
- CLAIRE-generated classes are not built-in classes; promote exact matches only (L-CDGC-062).
- Auto Classification can infer nothing: classify manually (L-CDGC-060, L-CDGC-064).
- A rule occurrence's text is copied from its rule specification once; a DQ re-run does not refresh it (L-CDGC-145).
- A rule-occurrence publish without `X-INFA-PRODUCT-ID: CDGC` answers 500; after the publish, call `dataQuality/sync`
  (L-CDGC-161). Scoring curated tables whose loads already reject bad rows gives 100 everywhere: score the raw layer too
  (L-CDGC-166).
- An occurrence that binds a decimal-input rule to a text (VARCHAR) column passes publish and sync but is never scored:
  the Data Quality run ends PARTIAL_COMPLETED with no message. Bind a numeric column of a view over the table
  (`TRY_TO_NUMBER`), a `ViewColumn`, instead (L-CDGC-170).

**Search**
- Unknown field = 500 (L-CDGC-076); totals cap at 10,000 (L-CDGC-077).
- Views are cataloged as `View`, not `Table`: a Table-only count says "never scanned" (L-CDGC-139).
- Unstable paging duplicates and drops rows (L-CDGC-078): sort on `core.identity` and filter on `core.origin` +
  `elementType` OBJECT; a sort on `core.externalId` returns no hits (L-CDGC-169).
- UI AI search can return 0; Keyword works (L-CDGC-080).
- ccgf-searchv2 supports only some query types (L-CDGC-081); on data360 search `match` and `match_phrase` answer 400,
  so use `term`, `bool`, `wildcard` or `exists` and compare names client-side (L-CDGC-165).

**Lineage and CLAIRE**
- A semi-join in a Salesforce source's SOQL filter makes the IICS scanner drop that source from lineage (ParseException in the
  scanner log, job still COMPLETED); filter on literal values (L-CDGC-196).
- The IICS scanner reads each mapping task's run metadata: a mapping change shows in lineage only after the task runs again, a
  never-run task is skipped, and a project change starts an automatic 'Catalog Source Sync' job; the scanner logs are on the
  agent under `apps/Metadata_Foundation_Agent/data/workspaces/<source>-*/logs/` (L-CDGC-197).
- A Structure Parser shows as 'Unknown custom transformation type: StructureDiscovery': lineage through it is object level
  (L-CDGC-198).
- Database scans derive lineage only from view SQL; a new view outside the include scope is not even cataloged
  (L-CDGC-087).
- Grey "referenced" nodes = unassigned connection (L-CDGC-088); MERGE-assign it (L-CDGC-159).
- A `connectionAssignment` MERGE job completes even for a reference that does not exist: prove the stitch by reading a
  target table's lineage (L-CDGC-159). A flat-file reference stitches to a File System source's `FileServer` root
  (L-CDGC-160). A SharePoint connection reference can be named after the connection's v2 id: find it by
  `core.reference` and class `core.DataSource`, not by connection name, and MERGE it onto the SharePoint source's Site
  (L-CDGC-167).
- Mapping tasks are not catalog assets; SQL-in-a-task hides lineage (L-CDGC-091).
- CLAIRE lags fresh scans, is blind while a source scans, and trips on duplicate legacy sources (L-CDGC-090).
- BigQuery views whose SQL the analyzer cannot parse (`UnsupportedOperationException`, `Parse error NoViableAlt` on a
  single-backtick fully qualified name) get no lineage (L-CDGC-151); so do views that `UNNEST` inline STRUCT arrays or
  read `__TABLES__`: publish the missing pairs as curated edges built from the view definitions (L-CDGC-231).
- Curated edges are pinned to node identities: a rescan that gives a mapping's input new nodes orphans the hop, a foreign
  edge into a shared reference pulls another pipeline's graph in, and `RELATIONSHIP_ALREADY_EXISTS` proves nothing about
  the path (L-CDGC-228). Check each link with an automated upstream walk before sharing it (L-CDGC-232).
- A MERGE matches by path: an agent-folder reference does not merge onto a storage container root; mirror the
  `/<storage-account>/<container>/` path and MERGE onto the StorageAccount root (L-CDGC-224, L-CDGC-227).
- New or consolidated mappings reach lineage only after a rescan of the IICS source, and cross-system stitching needs
  resolved connection assignments (L-CDGC-146); auto-accepted assignments still did not show job-level lineage in CLAIRE
  (L-CDGC-148).
- A renamed source keeps its old name in CLAIRE until rescanned (L-CDGC-147); leftover connector temp views appear as
  downstream dependents until dropped and rescanned with Delete (L-CDGC-149).

**Marketplace**
- Orders placed before a delivery target exists stay PENDING forever (L-CDGC-097).
- Echo-only 200 on stakeholder PUTs (L-CDGC-098).
- Always include `/api/` in Marketplace paths (L-CDGC-005).

**Migration, cleanup and cost**
- CDGC content must be rebuilt in a target org; plan UI steps for definition deletes (L-CDGC-104). What the
  v3 package does carry: [Export & Import (v3 Migration API)](../12-deploy-migrate/01-export-import-v3-migration-api.md).
- Harvest GUID-keyed links before purging a source (L-CDGC-084).
- Scans cost IPUs; configuration, search and content writes do not (L-CDGC-103).
- No IDMC connector reads CDGC metadata: catalog feeds are external scripts with one writer (L-CDGC-101).

---

## 6. Unresolved contradictions and open questions

1. **Classification promotion.** A browser session saw `POST ccgf-api.<domain>/ccgf-orchestration-management-api-server/api/v1/management/job`
   (type 'Classification Promotion') return 200 + jobId once, while probes and a UI check found no accept route and only
   Dismiss. Unresolved: capture the request body from the browser and test it
   headless before relying on either claim (L-CDGC-061, L-CDGC-063).
2. **Deleting Published terms.** "Reported deleted, still searchable" versus domain and term deletes reported done during
   a later clean-up. Possibly lifecycle-dependent; verify each delete by search (L-CDGC-059).
3. **The data360 catalog-source prefix** answered 200, then an empty 404 identical to a bogus twin, then 200 again on the
   same org. Cause unknown (L-CDGC-019).
4. **Class filters.** A third-party fleet reports its `classType` filter is ignored; ES `term` queries on `core.classType`
   did filter here. Probably different mechanisms; the `filterSpec` probe's outcome is unrecorded (L-CDGC-079).
5. **`CATALOG_EXTRACT`.** Display names are proven; whether the enum form is also accepted is untested (L-CDGC-035).
6. **Not re-probed** with the content-API patterns: stakeholder assignment (L-CDGC-066) and bulk classification accept
   (L-CDGC-061). The lineage REST family was: hops read from the asset read, the graph routes still 404 (L-CDGC-181, which
   supersedes L-CDGC-085).
7. **Option strings not captured:** the exclude pivot of "Profiling Filter Config", the `Filter Type` values for database
   sources, and the effect of "Lineage Discovery Filter Config" (L-CDGC-043, L-CDGC-027, L-CDGC-141, L-CDGC-159).
8. **Host overlap.** Whether `ccgf-catalog-source-management` answers on `idmc-api` as well as `cdgc-api` (helper code on one
   org suggests yes) (L-CDGC-005).
9. **Rebinding** a source's `ConnectionId` to a different valid connection by PUT: a PUT with `id` repeated read back
   with the new connection binding (L-CDGC-163); a scan on the rebound source is not recorded (section 9 of
   [02](02-catalog-sources-create-scan-update-purge.md)).
10. **IICS extraction failure** after flat-file tasks (open) (L-CDGC-046).
11. **Rule-occurrence scoring**: six identical occurrences once scored 1 of 6, cause unknown (was L-CDGC-082, superseded
    by L-CDGC-144); re-check with the RuleInstance census and a fresh Data Quality run.
12. **The connection-assignment body: settled 2026-10-06.** `ccgf-contentv2/api/v1/assignment/connectionAssignment` takes
    `operationType=MERGE` (SPLIT undoes) with the body in [04](04-search-lineage-marketplace.md) section 9.1;
    `ASSIGN`, `UNASSIGN`, `ACCEPT` and `CREATE` fail the enum conversion (L-CDGC-159). SPLIT removes the assignment but
    not the edges already written (L-CDGC-211), and overlapping MERGE and SPLIT jobs on one reference both report
    FAILED: run them one at a time (L-CDGC-210).
13. **Settled contradictions** (recorded so they are not reopened): "data product publish stays a UI action" in an older
    wall list is a restatement from research, contradicted by REST creates with status PUBLISHED (L-CDGC-092); "no IPU for
    metadata operations" referred to reads and configuration, while scans are metered (L-CDGC-103); the jwt/Token route
    is recorded as both POST and GET, and the POST form is the one proven in helper code (L-CDGC-001); "Data Quality
    cannot run alone" (L-CDGC-036) held only until the Scope groups carried a runtime environment (L-CDGC-143).
14. **Curated edges into a mapping task (open, 2026-10-26).** L-CDGC-208 (2026-10-19) recorded `core.DataSetDataProcess`
    dataset -> MappingTaskInstance accepted with 201; in a later round the same kind of edge was refused (L-CDGC-224), and the
    logged results did not record which class pair each answer was for. Re-probe one dataset -> task edge before relying on
    either.
15. **The stuck-scan cancel time (settled 2026-10-26).** L-CDGC-221 recorded CANCELLED about two minutes after the request;
    that held only while Test Connection was the running task. During Catalog Source Extraction a cancel stayed
    CANCEL_REQUESTED for more than 50 minutes (L-CDGC-225).

---

## 7. Adjacent governance-family services

- **Data Access Management**: policy authoring walled on the probed orgs; prove the controls as pushdown; the verdict is
  org-scoped (L-CDGC-067).
- **API Manager**: `<pod>-apigw` and `<pod>-apim` return nginx 503 for every path including bogus ones, an artifact with
  no per-path meaning; `/public/apim/v1/apis` 404'd while the DataServiceApiMgmt engine ran; the developer portal
  `/public/api/v1/apiPortal` is the one likely true entitlement gap (weak evidence) (L-CDGC-105).
- **QuickLook**: client-side extension (L-CDGC-070).
- **CLAIRE GPT**: answers from this catalog. There is no public REST chat API, but the managed `orchestrate` and
  `data_explore` MCP tools answer the same questions headless (L-MCP-111); deterministic fallbacks built on catalog search
  and pre-validated queries remain for orgs without them (L-CDGC-108). CLAIRE GPT authors rule specifications and rule
  occurrences; it does not change data (L-MCP-089). Prompt rules:
  [CLAIRE GPT - Prompting Rules](../11-mcp-claire/03-claire-gpt-prompting-rules-patterns.md).
- **Governance dashboards**: build them on search counts plus warehouse governance views; user-adoption analytics need an
  audit-log feed exported to the warehouse (L-CDGC-107).

## Lessons cited in this doc

Every current CDGC lesson appears in the matrix or the gotcha list; the superseded ones are L-CDGC-031, L-CDGC-082,
L-CDGC-086 (superseded by L-CDGC-159) and L-CDGC-120 to L-CDGC-138 (L-CDGC-120 superseded by L-CDGC-034, L-CDGC-138 by
L-CDGC-105) plus L-DQ-044 (superseded by L-CDGC-143).
Full text: [Lessons: CDGC](lessons.md).
