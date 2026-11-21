# Catalog, glossary, classification and lineage (CDGC): cheat sheet

Register and scan sources into Cloud Data Governance and Catalog, load a glossary, link terms and classifications to
assets, and produce or read lineage: use this whenever a user asks to catalog, govern, search or trace data in IDMC.

**Start with:** `/informatica-idmc-headless:catalog <source or connection>`; check auth with `toolkit/lib/idmc_cdgc.py jwt-check` (it also
has `sources`, `source-get`, `source-create`, `source-update`, `scan`, `job`, `search`, `glossary-create`, `link`); open
[01 CDGC APIs & Auth](01-cdgc-apis-auth.md) first.

**The law:** three headers on every call (`Authorization: Bearer <cdlg_app JWT>`, `IDS-SESSION-ID`, `X-INFA-ORG-ID`);
`data360/*` on `idmc-api.<domain>`, `ccgf-*` on `cdgc-api.<domain>`; a 404 on the pod host is a wrong host, not a wall
(L-CDGC-001, L-CDGC-002, L-CDGC-005). Every route here is probe-derived: re-probe when the build changes (L-CDGC-010).

## What works (headless)

| Task | How (exact route/tool/command) | Lesson |
|---|---|---|
| Mint the JWT | `POST /identity-service/api/v1/jwt/Token?client_id=cdlg_app&nonce=<n>` with `IDS-SESSION-ID`; lives 30 min, cache ~20, re-mint on 401 | L-CDGC-001 |
| List types and their options | `GET .../ccgf-catalog-source-management/api/v1/datasourceTypes`; `.../type/<Type>/capability/<Cap>/configuration` (404 = not offered) | L-CDGC-016, L-CDGC-234 |
| Create a catalog source | multipart `POST .../datasources` (no trailing slash), one part `dataSource`, body cloned from a same-type source, every id remapped | L-CDGC-014, L-CDGC-015 |
| Update or rename a source | GET, back up, edit, multipart `PUT .../datasources/<id>` with `id` kept in the JSON | L-CDGC-020, L-CDGC-163 |
| Run a scan | `POST idmc-api .../data360/executable/v1/catalogsource/<id>` `{"capabilityNames":[display names]}` | L-CDGC-034, L-CDGC-035 |
| Poll a scan | `GET .../data360/observable/v1/jobs/<jobId>?expandChildren=TASK-HIERARCHY` every 20-40 s | L-CDGC-037 |
| Cancel a stuck job | `POST cdgc-api .../ccgf-orchestration-management-api-server/api/v1/jobs/<jobId>/operations/cancel`; poll for CANCELLED | L-CDGC-225 |
| Search | `POST .../data360/search/api/v1/search` + `X-INFA-SEARCH-LANGUAGE: elasticsearch` (`term`, `bool`, `wildcard`, `exists`), sorted on `core.identity` | L-CDGC-073, L-CDGC-165, L-CDGC-169 |
| Glossary domain / term | `POST .../data360/content/v1/assets` with `core.classType` Domain or BusinessTerm (term names its `parent`) | L-CDGC-050, L-CDGC-051 |
| Rename / describe | `PATCH .../content/v1/assets/<id>` segment `summary` (technical assets: `core.description` only) | L-CDGC-053, L-CDGC-164 |
| Link terms to assets | PATCH segment `glossary`, or batch many in one `ccgf-contentv2/api/v1/publish` | L-CDGC-056, L-CDGC-174 |
| Apply a classification | PATCH segment `dataClassification` with an existing `core.DataElementClassification` | L-CDGC-060 |
| CDI lineage | IICS source with Metadata Extraction + Lineage Discovery, then `connectionAssignment?operationType=MERGE` per unresolved reference | L-CDGC-029, L-CDGC-159 |
| Read lineage | `GET .../search/v1/assets/<identity>?scheme=internal&segments=all` (`lineage` segment, hop by hop) | L-CDGC-181 |
| Curated lineage edges | contentv2 publish RELATIONSHIP `core.DataSetDataFlow` (tables) / `core.DirectionalDataFlow` (columns) | L-CDGC-179 |
| Catalog DQ score | runtime env in the Scope groups, RuleInstance publish + sync, `capabilityNames: ["Data Quality"]` | L-CDGC-143, L-CDGC-161, L-CDGC-166 |

## What doesn't work, and the workaround

| Wall | Workaround | Lesson |
|---|---|---|
| REST `DELETE` purges metadata but leaves the definition | delete the definition in MCC > Catalog Sources; keep an id list | L-CDGC-047 |
| Bulk-accept of CLAIRE classifications | auto-accept threshold on the source + rescan; manual PATCH for a reviewed list | L-CDGC-061, L-CDGC-060 |
| Steward / owner assignment | MCC > Associations > Stakeholders; keep ownership as code | L-CDGC-066 |
| DAM policy authoring | build the first policy in the UI; demo controls as warehouse views | L-CDGC-067 |
| Marketplace delivery template | headed-browser automation of the Marketplace app | L-CDGC-096 |
| CDGC content in a v3 package (`MigrationSvc_034`) | rebuild in the target through the APIs from a read-only export | L-CDGC-071, L-CDGC-104 |
| `/data360/lineage/*` graph routes not served | walk the `lineage` segment asset by asset | L-CDGC-181 |
| Generic JDBC type has no Lineage Discovery | IICS source + MERGE, curated edges for in-database logic | L-CDGC-234 |
| Catalog profiling of BigQuery fails with no message | profile BigQuery with Data Profiling profiles | L-CDGC-184 |

## Fastest safe path

1. Prove the org, mint the JWT, `jwt-check`. Read-back: a search returns hits (or a real empty JSON, not a 0-byte 200:
   a new tenant needs one interactive open of DGC first) (L-CDGC-006, L-CDGC-213).
2. List existing sources; reuse one that covers the system. Read-back: `GET .../datasources` plus your own name-to-id
   map, since the list can come back empty (L-CDGC-017, L-CDGC-018).
3. Clone a same-type source, remap connection, runtime (also in every Scope group) and ids, DQ automation switches off.
   Read-back: GET shows no old ids (L-CDGC-015, L-CDGC-217, L-CDGC-152).
4. Select the agent's Metadata services, run Metadata Extraction alone first, one source at a time (ask first: scans
   are IPU-metered). Read-back: every task COMPLETED (L-CDGC-045, L-CDGC-103).
5. Confirm the harvest in search: tables AND views, fresh `lastScanned`. Read-back: counts per class (L-CDGC-039,
   L-CDGC-139).
6. Add profiling, classification or DQ only once the asset list holds the intended tables. Read-back: `core.profiled`
   counts (L-CDGC-152, L-CDGC-077).
7. Glossary: search before create, keep a registry and undo file. Read-back: terms Published by search (L-CDGC-052,
   L-CDGC-175).
8. Link terms in one batched publish. Read-back: the asset's `glossary` segment (L-CDGC-174).
9. Lineage: scan the database source, then the IICS source; MERGE references one job at a time. Read-back: walk
   upstream from the end asset to the system of record (L-CDGC-187, L-CDGC-210, L-CDGC-232).

## Top traps

- 500 "Login sessionID is missing" or 401 on data360 -> headers missing -> send all three (L-CDGC-002, L-CDGC-003).
- 415 on create -> JSON body -> multipart part `dataSource`; 500 "Custom flag cannot be null" -> set `custom`,
  `endOfLife` (L-CDGC-014).
- 400 "dataSource id in request path and body do not match" -> `id` stripped -> keep it; diff capabilities by name
  (L-CDGC-163, L-CDGC-212).
- 500 "no capability is being chosen" -> empty `capabilityNames` -> list them; 406 "Job is in progress" -> a job holds
  the lock -> cancel it, never loop (L-CDGC-034, L-CDGC-225).
- Rule Profiling FAILED in 0-1 s, no text -> no runtime env in the Scope groups -> add both groups (L-CDGC-143,
  L-CDGC-216).
- "None of the Assets met filter criteria" on PostgreSQL -> filter `db.schema.*` -> use `schema.*`; Filter Type Tables
  skips views -> add a Views group (L-CDGC-026, L-CDGC-177).
- Stale or duplicate assets after a rescan -> Metadata Change Option Retain -> set Delete (but Retain when narrowing a
  filter, or Delete purges the dropped scope) (L-CDGC-028, L-CDGC-223).
- Search 500 -> unknown field name, not an outage; `match` -> 400; unsorted paging drops assets (L-CDGC-076, L-CDGC-165,
  L-CDGC-169).
- A Published term DELETE reports success and stays -> verify every delete by search (L-CDGC-059).
- A scan blanks curated descriptions -> also set them in the source system, re-run curation (L-CDGC-055).
- MERGE job "completes" for a nonexistent reference; overlapping MERGE/SPLIT both FAIL -> one at a time, prove by a
  lineage read (L-CDGC-159, L-CDGC-210).
- Lineage shows old mapping logic -> the task has not run since the change -> run the task once (L-CDGC-197).

## Go deeper

- [01 CDGC APIs & Auth](01-cdgc-apis-auth.md): hosts, the three headers, status triage, entitlement checks.
- [02 Catalog sources](02-catalog-sources-create-scan-update-purge.md): create, clone, scan, poll, cancel, rename, purge.
- [03 Glossary, links & classification](03-glossary-links-classification.md): domains, terms, links, dictionary, classifications.
- [04 Search, lineage & marketplace](04-search-lineage-marketplace.md): ES search, coverage, lineage stitching, Marketplace.
- [05 CDGC gaps & gotchas](05-cdgc-gaps-gotchas.md): the headless matrix and the walls still standing.
- [lessons.md](lessons.md): every CDGC lesson with evidence; grep it before any call.
