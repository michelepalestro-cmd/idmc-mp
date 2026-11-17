# Lessons: MDM
72 current lessons (2 of them disputed) and 11 superseded, IDs L-MDM-###; evidence dated 2026-07-04 to 2026-11-12. Every lesson is generic; its sources are mapped outside the generic zone.
Related: [MDM Runtime vs Design](<../08 - MDM/01 MDM SaaS - Runtime vs Design.md>) · [MDM Records](<../08 - MDM/02 MDM Records - Ingest, Search, Export, Cleanup.md>) · [Business 360 Modeling & Match-Merge](<../08 - MDM/03 Business 360 Modeling & Match-Merge.md>) · [P360 vs MDM SaaS & Licensing](<../08 - MDM/04 P360 vs MDM SaaS & Licensing Notes.md>)

## Current

### L-MDM-001  MDM SaaS runs in the cloud pod on <pod>-mdm, not on a Secure Agent
**Kind:** LAW · **Proven:** 2026-07-06 · **Evidence:** no MDM service in the engine lists of two agents (2026-07-06)
There is no MDM engine on a Secure Agent: MDM SaaS (Business 360, Customer 360 and the other 360 apps) is hosted in the pod on `<pod>-mdm.<domain>.informaticacloud.com`. Agent sizing and service selection do not affect it; an agent matters only for integration jobs that move data in or out.

### L-MDM-002  Build the MDM host by adding -mdm to the pod label and stripping /saas
**Kind:** ROUTE · **Proven:** 2026-07-26 · **Evidence:** live on two pods (2026-07-26)
The MDM runtime is `https://<pod>-mdm.<domain>.informaticacloud.com/business-entity/public/api/v1/...` (also `/search/public/api/v1/...` and `/rdm-service/...`): take the pod base URL from the login, add `-mdm` to the pod label and drop the trailing `/saas`. The unprefixed `mdm.<domain>` has no DNS, and `<pod>-mdm-model`, `<pod>-b360` and `<pod>-cs` do not resolve either.

### L-MDM-003  Authenticate MDM calls with the identity three-header set; the JWT lives 30 minutes from grant
**Kind:** ROUTE · **Proven:** 2026-09-28 · **Evidence:** record ingest with this set (2026-07-08); MDM search with a cdlg_app JWT (2026-09-28)
Log in with `POST https://<domain>.informaticacloud.com/identity-service/api/v1/Login` (`sessionId`, `orgId`), mint a JWT with `GET https://<domain>.informaticacloud.com/identity-service/api/v1/jwt/Token?client_id=cdlg_app&nonce=<n>` and header `IDS-SESSION-ID: <sessionId>`, then send `Authorization: Bearer <jwt>`, `IDS-SESSION-ID: <sessionId>` and `X-INFA-ORG-ID: <orgIdV3>` on every MDM call; Bearer alone returns 401 on writes. The JWT expires 30 minutes after it is minted, whatever the activity: re-mint it from the cached identity session (about 0.5 s, no password) at about 25 minutes or on a 401. The MDM session itself times out after 30 minutes idle.

### L-MDM-004  The MDM runtime plane is headless; the design plane is the Business 360 UI
**Kind:** LAW · **Proven:** 2026-07-27 · **Evidence:** 18 design-plane route shapes 404 with no 405 (2026-07-26/27); runtime calls 201/200 (2026-07-08, 2026-09-28)
Headless: record ingest, read by id, source-record (entity-xref) updates, record search and export, Reference 360 search, and the MCP fuzzy match. UI only: business-entity model authoring (fields, field groups, keys), publishing or deploying the model, registering source systems, match models, merge and survivorship rules (source ranking, trust), running match/merge and other jobs, and steward decisions. Plan the design clicks explicitly and script everything after them.

### L-MDM-005  No public REST route publishes, deploys or authors a business entity: stop hunting
**Kind:** OVERTURNED · **Proven:** 2026-07-27 · **Evidence:** sweep of 18 shapes with bogus twins (2026-07-26/27)
Six deploy shapes (`/business-entity/public/api/v1/{deploy,deployment,model/deploy,publish}`, `/mdm-config/api/v1/deploy`, `/data360/mdm/api/v1/deploy`) all return `404 CMN00005`, and twelve model-authoring host and path shapes (`.../model/businessEntity`, `/mdm-model/`, `/business-entity/{private,internal}/api/v1/businessEntities`, `/data360/businessentity/`, hosts `<pod>-mdm-model`, `<pod>-b360`, `<pod>-cs` and others) return 404 or NXDOMAIN, each matching its bogus twin, with no 405 anywhere. A uniform 404 without a 405 means the route does not exist. Holding the MDM Designer role and dozens of MDM privileges does not change that. Supersedes L-MDM-063.

### L-MDM-006  Address a business entity by its runtime id (for example c360.person), never by its design GUID
**Kind:** OVERTURNED · **Proven:** 2026-07-08 · **Evidence:** 404 with the design GUID, 200 with the runtime id on the same live runtime; hundreds of active records already present (2026-07-06); 201 ingests (2026-07-08)
The record API addresses entities by their runtime metadata id, such as `c360.person`: `GET https://<pod>-mdm.<domain>.informaticacloud.com/business-entity/public/api/v1/entity/c360.person/<recordId>`. Using the design or FRS GUID returns 404 "metadata ... cannot be found during load" even on a live runtime, which looks exactly like an undeployed model. An early-July "deploy wall" was this identifier mistake. Supersedes L-MDM-059.

### L-MDM-007  The one manual model step: runtime-effective on Save, or one Modeler Publish click
**Kind:** WALL · **Proven:** disputed (latest evidence 2026-07-27) · **Evidence:** UI inspection of a deployed entity (2026-07-06) versus sweep conclusions on an empty org (2026-07-26/27) [disputed]
Every source agrees there is no REST deploy. They disagree on the UI step. The only direct observation of a deployed entity (2026-07-06) found no Publish on the business entity's menu (Properties and Automapping only), a model that was runtime-effective on Save, and a Published state only on match models. Later write-ups (2026-07-09 to 2026-07-27) describe one Business 360 Modeler Publish click that gates all 360 apps, but they come from an org with nothing modeled, where the button could not be seen. Plan one Modeler step (Save, plus Publish if your release shows it) and prove the result headless with the ingest gate (L-MDM-008).

### L-MDM-008  Gate on the ingest POST, with a fake entity name as the control
**Kind:** RECIPE · **Proven:** 2026-07-27 · **Evidence:** identical 404 for three real-looking names and the fake one on an empty org (2026-07-26/27); 201 on a deployed entity (2026-07-08)
`POST https://<pod>-mdm.<domain>.informaticacloud.com/business-entity/public/api/v1/entity/<be>?sourceSystem=<src>` returns 404 "The requested metadata with GUID <be> cannot be found during load" while nothing is deployed under that name, and flips to 201 (or a validation 400) once it is. Send the same call with a fabricated name (`ZZFAKEENTITY`): it must stay 404, and if the fake name ever succeeds, discard the run. Keep the probe body invalid so no junk record is written. Corroborate an empty org with the unfiltered `GET /public/core/v3/objects?limit=5` (count 1, a single Default project). This makes the one UI step machine-checkable.

### L-MDM-009  A 403 on GET entity/<be>/<id> fires before the metadata lookup and proves nothing; data360 businessEntities is a fake 200
**Kind:** OVERTURNED · **Proven:** 2026-07-27 · **Evidence:** bogus twins on the entity name and on the path (2026-07-26/27)
`GET .../business-entity/public/api/v1/entity/<be>/<id>` returns 403 identically for a nonsense entity name, because the access check runs before the metadata lookup, so a 403 proves only that the plane is real. On the `idmc-api` host, `/data360/mdm/v1/businessEntities` returned a byte-identical 200 for its bogus twin: prefix routing, not a handler. Never cite either as evidence. Supersedes L-MDM-062.

### L-MDM-010  The -mdm host is live even when one prefix 404s: a 403 with an errorId beside a bogus 404 is a role gap
**Kind:** OVERTURNED · **Proven:** 2026-07-26 · **Evidence:** 403 errorId versus bogus 404 CMN00005 (2026-07-26)
On one pod, `/business-360/*` returned 404 and the host was declared unmounted. DNS resolved and `/business-entity/public/api/v1/entity/<be>/search` returned 403 "Authorization Client Error" with an errorId while a bogus sibling returned `404 CMN00005`: the route exists and the caller lacks a role. A host verdict needs more than one prefix. Supersedes L-MDM-064.

### L-MDM-011  Read MDM entitlement from privileges, roles and design objects; entitlement is not reachability
**Kind:** OVERTURNED · **Proven:** 2026-07-27 · **Evidence:** privileges, roles and 97 MDM design objects read (2026-07-04 to 2026-07-27)
MDM entitlement shows as privileges (CRUD on `mdm.asset.be`, `.srcsystem`, `.hierarchy`, `.relationship`, `.jobdef`, `.appmodel`; `execute.mdm.flows`; `manage.mdm.jobs` and `manage.mdm.schedules`) in the identity Login's `effectivePrivileges`, roles such as MDM Designer and Customer 360 Data Steward, Manager and Analyst, and `MDM_*` or BUSINESS_ENTITY design objects in `GET /public/core/v3/objects`. The login `products[]` list is only a label. An org can hold 83 MDM privileges and still have no reachable deploy route: probe routes separately. Supersedes L-MDM-066.

### L-MDM-012  Enable MDM SaaS for an org in order: license, MDM administrator role, then set up the application
**Kind:** RECIPE · **Proven:** documented, unproven (read 2026-08-15) · **Evidence:** vendor setup article cited in a demo install guide (2026-08-15) [doc]
Per the Business 360 setup documentation: confirm the license, give the user the MDM administrator role, then in Customer 360 choose "Yes, Set up Application" to provision the application before modeling or loading anything.

### L-MDM-013  Clone MDM design objects through the migration package (design layer only)
**Kind:** RECIPE · **Proven:** 2026-07-26 · **Evidence:** imports SUCCESSFUL for a 41-field and a 15-field entity, a source system, reference entities and a rule spec (2026-07-04/05)
BUSINESS_ENTITY, MDM_SRC_SYSTEM, REFERENCE_ENTITY and RULE_SPECIFICATION objects travel in v3 migration packages: export a same-type template, retarget namespace, GUID, name and FRS id, recompute the checksums, upload with `POST /public/core/v3/import/package` (multipart), start it, and poll to SUCCESSFUL. It is free. The import lands design objects; whether they are runtime-effective without a Modeler step is part of the dispute in L-MDM-007, so verify with the ingest gate. An org with no same-type object has no template (export answers `400 MigrationSvc_041`), and importing an entity exported from another org into an empty MDM org is untested.

### L-MDM-014  The import route is open with multipart/form-data; MigrationSvc_025 was a JSON content-type trap
**Kind:** OVERTURNED · **Proven:** 2026-07-26 · **Evidence:** four-encoding matrix (2026-07-26)
`POST /public/core/v3/import/package` with `Content-Type: application/json` returns `404 MigrationSvc_025 "Import request with identifier [package] doesnt exist"`, which reads like a closed route. With `multipart/form-data` (file field `package`) the same route accepts uploads. What an empty org lacks is a template, not the route; stale copies of the "closed backdoor" claim survive in older reference sections. Supersedes L-MDM-068.

### L-MDM-015  Calling MDM services from the console page context is blocked: use REST from outside or drive the UI
**Kind:** GOTCHA · **Proven:** 2026-07-06 · **Evidence:** 302 plus a CSP block (2026-07-06)
Direct calls to MDM job, process-template or license services from a page context redirect (302) to an internal host and are blocked by the page's CSP (`connect-src 'self'`) and missing X-INFA and CSRF headers. UI clicks were the reliable path for MDM job operations.

### L-MDM-016  Ingress, match/merge and other MDM job runs have no public route
**Kind:** WALL · **Proven:** 2026-07-26 · **Evidence:** 404 on every job and flow shape (2026-07-09 and 2026-07-26)
`/data360/ingress/api/v1/jobs` returns 404 on GET and POST, and 11 job and flow shapes plus 5 x360 and config shapes (`/mdm/.../job`, `/business-entity/.../match`, `/cmx/.../match` and others) returned 404 although `execute.mdm.flows`, `manage.mdm.jobs` and `view.mdm.x360` were granted. Running match and merge, ingress and reindex jobs is a Business 360 Console action. An ingested record lands as a source record; the master record does not re-survive until a job runs.

### L-MDM-017  MDM process assets have no Run button: runs come from landing data, job schedules or the API/CLI
**Kind:** LAW · **Proven:** 2026-07-06 · **Evidence:** menus of 74 items inspected in a Customer 360 project (2026-07-06)
In Business 360 Explore, process assets (Ingress, MDMFlow) offer Properties, View, Edit, Publish, Unpublish, Export and Delete but no Run; system Ingress cannot be edited, moved or deleted; source systems have no ingest-now action. Job definitions (for example Job Recovery) expose Job Schedules and Add Job Schedule. Ingress, match/merge and reindex therefore run when data lands at the ingress location, on a job schedule, or through an API or CLI.

### L-MDM-018  The Business 360 Console My Jobs page is the ground truth that native MDM ran
**Kind:** OVERTURNED · **Proven:** 2026-07-06 · **Evidence:** 26 job rows, 23 successful, including six MatchMerge runs (2026-07-06)
Successful `<BE> MatchMerge` and reference-data ingress jobs on My Jobs (`https://<pod>-mdm.<domain>.informaticacloud.com/ui-config-app/main/jobs`) prove the entity is deployed and survivorship ran. REST 404s on record, steward and deploy routes reflected missing public routes, not an undeployed model, and headless signals (v3 objects, CDGC activity) do not show MDM runtime jobs at all. Supersedes L-MDM-060.

### L-MDM-019  Ingest a source record with a bare field map and a string trustScore
**Kind:** OVERTURNED · **Proven:** 2026-07-08 · **Evidence:** 201 per record for 10 real records, state ACTIVE, validation passed, SEARCH_INDEXED (2026-07-08)
`POST https://<pod>-mdm.<domain>.informaticacloud.com/business-entity/public/api/v1/entity/<runtimeId>?sourceSystem=<sourceSystemId>` with the three identity headers and a bare JSON field map (not wrapped in `fields`, `attributes` or `record`) returns 201 `{"approvalRequired":false,"id":"MDM...","businessId":"MDM..."}`. For `c360.person`, `firstName` and `lastName` are required (`fullName` is computed), and `trustScore` must be a string such as `"85"`. The source system id must be a registered source (for example `c360.<system>.system`). Supersedes L-MDM-061.

### L-MDM-020  Ingest 400 signatures: a wrapped body, an integer trustScore, a field that is not in the model
**Kind:** ERROR · **Proven:** 2026-07-08 · **Evidence:** 400s during the contract discovery, then 201 (2026-07-08)
A body wrapped in `fields`/`attributes`/`record` returns 400 "not allowed by the data model"; an integer `trustScore` returns 400 "Enter a valid [null]"; a field that is not in the model (for example a computed or invented field) returns 400. Fix the body; a 400 here also proves the entity is deployed.

### L-MDM-021  Read a master record by id: 200 in July, disputed later
**Kind:** ROUTE · **Proven:** disputed (latest evidence 2026-07-26) · **Evidence:** 200 with a live master record (2026-07-06/08); disputed in a 2026-07-26 review [disputed]
`GET https://<pod>-mdm.<domain>.informaticacloud.com/business-entity/public/api/v1/entity/<runtimeId>/<id>` returned 200 with the record plus `_meta`, including `consolidation=MATCH_INDEXED` and `searchIndex=SEARCH_INDEXED`. A later review concluded that some early 200s were identity-service login HTML. Check the Content-Type and the body shape, not just the status. The consolidation and search-index tokens are not in the vendor docs, so pin their real values on a live read before gating on them.

### L-MDM-022  Record ingest is not idempotent: a re-post created new master ids
**Kind:** GOTCHA · **Proven:** 2026-07-08 · **Evidence:** new master ids on re-post (2026-07-08); upsert assumption in a 2026-08-03 plan, untested
Posting the same source record again created new master ids, so a retry loop can duplicate records. Track what was ingested (a client-side tally or checkpoint) and reconcile before re-posting. A later plan assumed a POST per (source, key) is an upsert; that assumption was never tested.

### L-MDM-023  Send source-system updates to entity-xref, never to the master entity
**Kind:** LAW · **Proven:** documented, unproven (read 2026-07-26) · **Evidence:** vendor material and the skill's per-service rule (2026-07-25/26) [doc]
Source-system updates belong on `/business-entity/public/api/v1/entity-xref/{...}` (GET, PUT and PATCH documented, not exercised); writing source data onto the master `entity` resource corrupts the master record. PATCH matters only in MDM, on entity and entity-xref.

### L-MDM-024  MDM request bodies carry search or fields, never both (indicative)
**Kind:** LAW · **Proven:** documented, unproven (read 2026-07-25) · **Evidence:** vendor deck (2026-07-25); not verified end to end [doc]
From an Informatica solution-architect deck, not product documentation: the MDM SaaS resources are `search`, `entity`, `entity-xref` and `searchmatch`, and a body carries `search` or `fields`, never both.

### L-MDM-025  Search and export records with /search/public/api/v1/search; one query stops at 10,000
**Kind:** OVERTURNED · **Proven:** 2026-09-28 · **Evidence:** 19,253 of 19,255 and 7,689 of 7,689 records exported for two entities (2026-09-28)
`POST https://<pod>-mdm.<domain>.informaticacloud.com/search/public/api/v1/search` with the three identity headers (JWT from `client_id=cdlg_app`) and `{"search":"*","entityType":"c360.person","recordOffset":0,"recordsToReturn":1000}` pages through master records. One query returns at most 10,000 records in total, so export a larger entity as a union of term and prefix-wildcard queries, dedupe by id, and check the union count against the entity count. Supersedes L-MDM-069.

### L-MDM-026  Reference 360 search is live on /rdm-service/external/v1/search
**Kind:** OVERTURNED · **Proven:** 2026-07-26 · **Evidence:** 400/405/404 controls (2026-07-26)
`POST https://<pod>-mdm.<domain>.informaticacloud.com/rdm-service/external/v1/search` with an empty body returns `400 RDM.0040044 "No input given to required..."` (the validator was reached, so the verb exists), GET returns 405 and a bogus twin 404. Reference 360 lookup is headless. `/rdm-service/api/v1/referenceDataSets` returns 404, which on its own is not evidence that Reference 360 is unavailable. Supersedes L-MDM-065.

### L-MDM-027  Fuzzy master-record lookup: the Customer Identification MCP server
**Kind:** ROUTE · **Proven:** documented, unproven (read 2026-07-26) · **Evidence:** vendor MCP guide (April 2026); listed in the managed registry [doc]
The managed Customer Identification MCP server offers `search_master_record` (fuzzy identity match that returns the business id of the best master record) and `get_master_record_details` (the consolidated master record). Use it when you need fuzzy matching, which the record API does not offer.

### L-MDM-028  The business-entity search route .../entity/<be>/search is 404/405, or a 403 role gap
**Kind:** GOTCHA · **Proven:** 2026-07-26 · **Evidence:** live on two pods (2026-07-26)
`/business-entity/public/api/v1/entity/<be>/search` returned GET 404 and POST 405 on one pod and 403 "Authorization Client Error" on another. Do not build on it; use `/search/public/api/v1/search` (L-MDM-025) or the MCP fuzzy match.

### L-MDM-029  Delete a record with ?sourceSystem=; deletes are soft
**Kind:** ROUTE · **Proven:** 2026-07-08 · **Evidence:** delete qualifier observed (2026-07-08); semantics per the Customer 360 guide p.79
`DELETE .../business-entity/public/api/v1/entity/<runtimeId>/<id>?sourceSystem=<src>` needs the source-system qualifier. Per the Customer 360 guide, deleted master and source records are not removed from the data store: their state changes from active to deleted, they cannot be updated, search leaves them out unless you filter for deleted records, and deleted source records can be restored. Deleting a master record leaves its source records active; deleting a source record keeps the master while any contributing source stays active, and deleting all contributing sources deletes the master. A UI soft delete also removes a record from API search.

### L-MDM-030  Export every entity's records to JSON before deleting an MDM installation
**Kind:** PROCESS · **Proven:** 2026-09-28 · **Evidence:** four entities exported to JSON before a cleanup (2026-09-28); the outcome of the MDM deletion itself is not recorded
Deleting MDM content (the 360 projects, business entities, reference entities) removes business records, not just design assets. First export the records of each entity with the search API as a union of queries (L-MDM-025), then v3-export the MDM design objects, then delete item by item and list anything the MDM service refuses instead of forcing it. Keep entities that live assets still use (for example an address-verifier entity).

### L-MDM-031  Records show in the UI only once search-indexed; a stuck Search Reindex job leaves search empty
**Kind:** GOTCHA · **Proven:** 2026-07-06 · **Evidence:** search 0 results with six successful MatchMerge runs; the reindex job Running for days with Stop/Restart disabled (2026-07-06)
Records appear in Customer 360 browse and search only once they are SEARCH_INDEXED. If search shows "No records found" although MatchMerge jobs succeeded, check the Search Reindex job (`c360.search.index`) on My Jobs: stuck in Running (a zombie), it never populates the index, its Stop and Restart can both be disabled, and there is no reindex-now button. A fresh reindex comes from a publish-time trigger, a job schedule or the API.

### L-MDM-032  Reconcile what the MDM runtime already holds before a bulk ingest
**Kind:** GOTCHA · **Proven:** 2026-07-05 · **Evidence:** hundreds of active runtime masters versus a 19-row source population (2026-07-05)
A runtime can already contain active master records from earlier match/merge runs or seeds. Before ingesting a new population, reconcile the runtime against your source of truth and check that the search-reindex job is not wedged; otherwise you create duplicate or conflicting masters, or records that never show in search.

### L-MDM-033  A bulk ingest outlasts the 30-minute JWT: refresh by grant time, back off, checkpoint
**Kind:** PERF · **Proven:** design guidance, not executed (2026-08-03) · **Evidence:** estimate plus the documented JWT lifetime (2026-08-03); plan, not executed at scale [plan]
Record ingest is one POST per record: about 98,000 records were estimated at about 2.7 hours, while the JWT dies 30 minutes after it is minted. Before any bulk run: re-mint the JWT from the cached identity session at about 25 minutes or on a 401, send bounded batches with exponential backoff on 429 (an MDM ingest 429 threshold is not documented, so this is defence), keep a client-side submitted/ok/failed tally, and checkpoint so a failure resumes instead of restarting.

### L-MDM-034  Documented MDM SaaS caps and job queueing thresholds
**Kind:** LAW · **Proven:** documented, unproven (read 2026-08-03) · **Evidence:** Customer 360 guide pp.65, 168, 247 and the match-and-export chapter; verified against the docs (2026-08-03) [doc]
CSV import: 100 MB and 100,000 rows. Search results and export: 10,000. Reports: 500 rows. Ingress and egress jobs queue once 25 run concurrently on a pod or 5 in an org. Step queueing: ingress load above 1,000 records, transform above 100,000, index for search above 10,000, generate match keys above 5,000; egress stage above 1,000. Match results of a match-and-export run expire 4 days after the Release The Job step. Rejected records are kept 7 days. There is no documented "1,000 addresses per call" limit for MDM (that figure belongs to address verification).

### L-MDM-035  Queued is normal for large MDM jobs, and a stopped job cannot be restarted
**Kind:** GOTCHA · **Proven:** documented, unproven (read 2026-08-03) · **Evidence:** Customer 360 guide pp.246-247 [doc]
When a step lacks resources MDM moves the job from Running to Queued; with the thresholds in L-MDM-034 this is expected behaviour, not a failure. A stopped job cannot be restarted or resumed, and its data may be partially processed. Download rejected records within 7 days. A system Resolve Long-Running Operations job completes create, update and delete operations that timed out.

### L-MDM-036  Create and run a Match and Merge job in the Business 360 Console
**Kind:** RECIPE · **Proven:** 2026-07-09 · **Evidence:** a job ran to Success with the full stage graph (2026-07-09)
In the Business 360 Console (`https://<pod>-mdm.<domain>.informaticacloud.com/ui-config-app`): New... > Jobs > Match and Merge > Create; set the display name, Process Type Match and Merge, the business entity, the match model (for example a published baseline deduplication model) and Version Latest; Save ("saved successfully"), then Run ("job started successfully"). The stage graph reads Lock, Match, Merge, Index for Search, Group Potential Matches, Release. Automation needed a headed browser (xvfb); headless runs stalled.

### L-MDM-037  A match-and-merge run took 16-25 minutes regardless of size
**Kind:** PERF · **Proven:** 2026-07-09 · **Evidence:** job detail in the Business 360 Console (2026-07-09)
One run over 10 records took 25 min 16 s; runs took about 16-25 minutes whatever the row count (match-engine warm-up). Budget that time in demos and schedules, and do not read a slow small run as a failure.

### L-MDM-038  Survivorship lives in the model; the record vocabulary is Record State plus Match Outcome
**Kind:** LAW · **Proven:** documented, unproven (read 2026-08-03) · **Evidence:** Customer 360 guide terminology and dashboards, checked against a design deck (2026-08-03) [doc]
Survivorship (trust, source ranking, criteria) is configured in the business-entity model by an administrator; an ingest-time `trustScore` does not define it, and it is unproven that survivorship honours it at all. Documented record axes: Record State (active, pending, inactive, deleted) and Match Outcome (Auto-merged, Auto-merged with Approval, User Merged, User Merged with Approval, Not Merged); CONSOLIDATED, UNMERGED and MATCH_INDEXED are not documented terms. Vendor terminology: "master record" (not golden), "Text" (not String), entity-xref = source and patch records. Outbound is batch (egress jobs, match and export, business events). The C360 docs give no per-record IPU rate.

### L-MDM-039  Rank every source system; define attribute-level best-version rules; treat match-model edits as change-controlled
**Kind:** RECIPE · **Proven:** 2026-07-04 · **Evidence:** ranking authored and saved in the Modeler (2026-07-04)
If the Source Ranking survivorship rule lists only one source, precedence between sources is undefined. In the Modeler rank every contributing source system, then set attribute-level best-version-of-truth rules (most trusted source for email, most recent for name, non-null for external ids, earliest for first-seen dates, recompute for derived scores). Editing a published match model creates a new model version and a re-index, so schedule it like a change.

### L-MDM-040  Turn off out-of-the-box DaaS enrichment on a Supplier entity: it bills per external lookup
**Kind:** GOTCHA · **Proven:** 2026-07-08 · **Evidence:** suppression verified by re-export (2026-07-04/08)
The stock Supplier business entity ships DUNS, SSN, tax and bank enrichment providers that bill per lookup. Deactivate the enrichment you have no source data for, verify by re-exporting the model and checking that fields such as `dunsNumber`, `identifier`, `tax` and `bankDetails` are gone, and keep DaaS providers off on optional match/merge runs.

### L-MDM-041  The stock Person entity carries none of your domain fields until you extend it
**Kind:** GOTCHA · **Proven:** 2026-07-08 · **Evidence:** stock Person entity with no domain fields and 0 domain records until extended (2026-07-08)
The out-of-the-box Person business entity is SSN/DUNS-oriented. Extend the model with your own fields (in the Modeler, or by cloning an extended entity) before expecting domain attributes to land or survive.

### L-MDM-042  Check fuzzy thresholds and numeric survivorship claims with real numbers
**Kind:** GOTCHA · **Proven:** 2026-08-15 · **Evidence:** computed JW 0.69; SUM gave 6,400 instead of 2,100 in a 10-row ledger (2026-08-15)
Name similarity is weaker than it looks: Jaro-Winkler for nickname pairs such as Bob/Robert is about 0.69, far below a 0.92 threshold, so a rule needs another signal (exact normalized phone, exact surname token, a nickname map). For numeric survivorship over duplicates, SUM double-counts the duplicate's value; use MAX or a consolidated value.

### L-MDM-043  A surname plus street-number match rule is a household match: tighten it or label it
**Kind:** DECISION · **Proven:** 2026-09-26 · **Evidence:** 45 merged pairs listed for review (2026-09-26)
A fuzzy rule keyed on surname and street number merged people with different first names and different emails at full confidence. Either tighten it (add email domain or phone) or present it deliberately as a household match, and decide before showing match-and-merge results to anyone.

### L-MDM-044  Degenerate addresses collapse distinct records under fuzzy rules; match deterministically on the business key
**Kind:** GOTCHA · **Proven:** design guidance, not executed (2026-08-03) · **Evidence:** collision measurement over a 2.5M-record sample (2026-08-03); design decision, not run in MDM [plan]
A fuzzy address rule (normalized address plus zip and city) would have collided on tens of thousands of distinct record groups: the unit was almost always empty and one degenerate address was shared by 306 distinct records. SSA-NAME3 populations are person and organization identity models, with no population for things such as parcels. For non-party entities, match deterministically on a real business key and measure collisions before enabling any fuzzy rule.

### L-MDM-045  Verify the data premise before designing a survivorship demo
**Kind:** PROCESS · **Proven:** 2026-08-03 · **Evidence:** 0 divergence across 800 records x 22 fields in a two-store mirror (2026-08-03)
Before promising that MDM reconciles source A against source B, measure whether the sources actually diverge (sample fields across many records, count keys with more than one source version). Byte-identical mirrors give match/merge nothing to resolve. Treat heterogeneous opaque ids as exact-match keys only (never parse them), and keep a separate field map per source.

### L-MDM-046  Model hygiene for a new business entity: types, keys, sentinels, a one-row canary
**Kind:** RECIPE · **Proven:** design guidance, not executed (2026-08-03) · **Evidence:** design guidance from an adversarially reviewed plan (2026-08-03); not executed end to end [plan]
Map warehouse types deliberately (Float64 to Double, integers to Integer, Date32 to Date, DateTime64 to Date Time with milliseconds, money to Decimal, codes with leading zeros to Text). Do not attach a key-format validator to an id whose shape differs by source. Null out sentinel defaults (for example 'unknown', 'other') on extract. There is no field-schema list verb, so ingest one real record and read it back to prove that the UI-authored field names match the code's field map before any bulk load.

### L-MDM-047  'Cannot load the data' on Add Job Schedule means the MDM schedule service is degraded
**Kind:** ERROR · **Proven:** 2026-07-06 · **Evidence:** same failure manually and under automation (2026-07-06)
When the Business 360 Add Job Schedule form shows "Cannot load the data. Try again later ... contact Informatica Global Customer Support" and Save fails with "Enter a value", the schedule service backend is failing. It is not a selector or automation problem; open a support case.

### L-MDM-048  Business 360 and Customer 360 app URLs, and how to automate them
**Kind:** RECIPE · **Proven:** 2026-07-07 · **Evidence:** all apps loaded and selectors drove a search (2026-07-06/07)
On the `<pod>-mdm` host: Business 360 Console `/ui-config-app` (Modeler, Explore, My Jobs at `/ui-config-app/main/jobs`), Customer 360 `/ui-x360-app/app/c360/`, Multidomain MDM `/ui-x360-app/app/mde`, Product 360 `/p360`, Supplier 360 `/s360`, Reference 360 `/rdm-ui/`. Log in on the identity host and let SSO carry over. Deep links such as `/explore/<id>` render empty when cold: navigate Explore > All Projects > the project instead. Grid rows are `role=row`, the kebab menu appears only on hover, and the console JWT lasts about 30 minutes, so log in fresh per script. Customer 360 search: `div[data-testid='mdm-bui-search-dropdown']`, `span#selected-entity`, `input[aria-label='Search input']`.

### L-MDM-049  Capture the browser network trace during one Modeler publish to settle the hidden plane (open)
**Kind:** PROCESS · **Proven:** design guidance, not executed (2026-07-26) · **Evidence:** recorded as the top open question (2026-07-26); not yet done [plan]
Every public route shape for model authoring and deploy 404s, so the Modeler must call something non-public or session-cookie-only. Capturing the network trace during one real Save/Publish is the cheapest way to settle the biggest untested gap in MDM; never paste captured cookies or Authorization headers anywhere.

### L-MDM-050  A warehouse SQL master-record stand-in per domain while native MDM is gated
**Kind:** WORKAROUND · **Proven:** 2026-07-08 · **Evidence:** stand-ins rebuilt and scheduled for three domains (2026-07-04 to 2026-07-08)
Until native MDM is usable, a SQL realisation per domain keeps 360 use cases moving: stage, normalize, cross-reference (source system, source key, match tier, score, trust), attribute-level survivorship, a steward queue, a reversible merge-override table, a serving view and validation. Keep one canonical table (other names are views, so they cannot drift), keep consumers on the stand-in's id so the producer can switch to native MDM, and keep it as the conformance oracle afterwards.

### L-MDM-051  Cut over to native MDM only after a zero-drift reconcile, gated behind the runtime probe
**Kind:** PROCESS · **Proven:** 2026-07-08 · **Evidence:** harness gated and exiting cleanly before deploy (2026-07-05); cutover plan (2026-07-07/08)
Order: the one Modeler step, ingest, first match/merge, then a native-versus-stand-in reconcile (party count, cross-references, survivorship winners) that must show zero drift, then QA sign-off and approval, and only then re-point consumers (a configuration flip). Gate the reconcile harness behind the ingest-POST probe (L-MDM-008) so it reports DEFERRED and exits 0 until the entity is live.

### L-MDM-052  Do not call a SQL dedup layer a golden record or MDM in an Informatica conversation
**Kind:** DECISION · **Proven:** 2026-09-27 · **Evidence:** 0 visible golden/MDM strings after a relabel of demo pages and dashboards (2026-09-27)
In Informatica terms "golden record" and "single source of truth" mean MDM. A warehouse pipeline that cleanses, standardises, DQ-scores and rule-deduplicates without MDM is better described as a trusted curated layer, and a CRM's unified profile is its own concept. Change the visible wording; identifiers can stay.

### L-MDM-053  Prepare an activation-readiness package per MDM domain before the first native run
**Kind:** PROCESS · **Proven:** 2026-07-05 · **Evidence:** a 44-file readiness package built for four domains (2026-07-05)
Before activating each 360 domain, prepare an activation plan, runbook, entity spec, ingest script, reconcile/drift harness and done-checklist, plus a master pack (runbook, RACI, go/no-go, risk register). Define a machine-checkable activation proof (the ingest route flipping from 404 to 201) and treat the first native ingest and match/merge as a metered first run that needs approval.

### L-MDM-054  Interim collectors should emit an explicit 'unavailable' signal, not a green zero
**Kind:** GOTCHA · **Proven:** 2026-07-04 · **Evidence:** collector emitting an honest unavailable signal (2026-07-04)
While a native MDM runtime is not live, a collector should self-detect the 404 and emit an explicit unavailable metric (for example `mdm.run.available=0` with a reason) rather than a zero that renders green, and switch to native telemetry automatically once real jobs appear.

### L-MDM-055  Product 360 Cloud Edition is a different product from MDM SaaS and has no REST API
**Kind:** OVERTURNED · **Proven:** 2026-07-27 · **Evidence:** P360 Cloud Edition Configuration and Customization Guide v10.0; zero P360-family privileges on the probed org (2026-07-26/27)
Informatica MDM - Product 360 Cloud Edition is an AWS-hosted PIM, not MDM SaaS or Business 360. Its automation is empty marker files (`do_deploy.txt`, `do_deploy_web.txt`, `stop_server.txt`, `restart_server.txt`) dropped into an S3 customization folder that a cron scans; workflows deploy through the ActiveVOS console; DEV to QA to PROD promotion is a support ticket with a window of at least 4 hours. Before answering a P360 question from MDM SaaS evidence, grep the org's privileges for `p360`, `s360`, `catalog.item` or `supplier360`. Supersedes L-MDM-067.

### L-MDM-056  MDM SaaS is licensed by records; its bundled services apply only where MDM is the source or target
**Kind:** LAW · **Proven:** documented, unproven (read 2026-07-29) · **Evidence:** product description schedule citation (2026-07-29) [doc]
Per the Cloud Product Description Schedule v39.1 (effective 2026-06-05), MDM SaaS is a separate license metered by unconsolidated records, not IPUs. It bundles Data Integration (the Business 360 connector and transformations), Data Synchronization, ingestion of Business 360 events, DQ assets (cleanse, verify, parse, deduplicate, profile, exception management), Application Integration (Process Designer and Server, OData), API Gateway, named users, sandboxes and hierarchy management, but only where MDM is the sole source or target of the data. Address verification consumption needs a Premium Address Cleansing pack or IPUs; integration or quality between non-MDM systems, standalone Mass Ingestion, standalone CAI or API Center, and all of CDGC draw on the IPU pool.

### L-MDM-057  MDM meters outside the IPU pool; record-processing cost is unknown until measured
**Kind:** LAW · **Proven:** documented, unproven (read 2026-09-03) · **Evidence:** CPDS v39.1 pp.7, 28 (2026-09-03); metering export review (2026-08-03) [doc]
MDM (and Operational Insights) are metered outside the IPU pool. The Customer 360 docs give no per-record IPU rate, and a near-empty org's metering export showed only an API Center baseline line, which is not an MDM rate. Take a metering snapshot before and after an ingest and a match/merge run to get a real unit cost, and do not extrapolate before then.

### L-MDM-058  Entitled on a trial org says nothing about a production license
**Kind:** GOTCHA · **Proven:** 2026-07-04 · **Evidence:** trial org with 59 roles, 897 privileges and 88 feature flags (2026-07-04)
A trial or embedded org can show nearly the whole suite entitled (MDM, the 360 apps and more) in roles, privileges and feature flags. That is not evidence of what a production commercial license includes; check the order or the license team for that.

### L-MDM-070  Bulk soft-delete of MDM SaaS records: sourceSystem=c360.default.system
**Kind:** ROUTE · **Proven:** 2026-09-30 · **Evidence:** 26,943 records deleted; search hits 0 afterwards (2026-09-30)
`DELETE https://<pod>-mdm.<domain>.informaticacloud.com/business-entity/public/api/v1/entity/<businessEntity>/<id>?sourceSystem=c360.default.system` with headers `IDS-SESSION-ID` and `X-INFA-ORG-ID: <orgIdV3>` returns 200 `{approvalRequired:false}`, and a GET of the record then returns 404. Without the parameter the answer is 400 'Missing required parameter sourceSystem'. For bulk: search the first page (`POST /search/public/api/v1/search`, 500 records), filter by `_meta.creationDate`, delete with about 6 parallel calls, pause for the index, and repeat. About 500 records/min; about 27k records took about 50 min. Deletes are soft (L-MDM-029).

### L-MDM-071  Attribute spend to the golden customer through the match key, never by the raw email on the transaction
**Kind:** PATTERN · **Proven:** 2026-09-30 · **Evidence:** top 10 identical to the golden-keyed LTV view after the fix; rows without email 221 to 61
Lifetime-value or top-customer lists built by joining payments to customers on the transaction's email undercount everyone whose payments sit under a merged duplicate's email, and drop payments whose source row carries no email at all (reservation payments often reference only the booking). Credit each payment to the customer on its booking, order or subscription first, then map every sign-up email to its golden customer via the same person key the golden table uses, and aggregate by golden id. Two lists computed both ways looked like a 'unique customers vs accounts' definitional difference; it was an attribution bug (one customer: 1,111 vs 1,369).

### L-MDM-072  A surname + street-number match key merges different people at one address; add the first initial and keep every copy of the rule identical
**Kind:** GOTCHA · **Proven:** 2026-09-30 · **Evidence:** before: household of 2 merged, customers 715; after: 2 separate keys, customers 716; batch and real-time layers equal again
A deterministic person key of lower(surname)|house-number collapses two people of one household (same surname, same street number) into one golden record, so a new sign-up 'disappears' from every dashboard. Use surname|first-initial|house-number, and surname|first-initial|email when the address has no number. The key usually exists in more than one place (the batch mapping that builds the golden table AND any real-time view that dedupes the change stream); change all of them together and tie out counts before and after (raw sign-ups, curated, customers without tests), or the batch and real-time layers disagree by exactly the wrongly merged people.

### L-MDM-073  The operational app often keeps its own copy of the match key: change it with the pipeline, or it keeps denying and flagging the people you split
**Kind:** GOTCHA · **Proven:** 2026-09-30 · **Evidence:** after the batch and real-time fix the app still stored the old key for both people of the split pair; the new customer's registration wrote a one-per-person 'deny' event; 1 such pair and 6 denies in 7 days
Besides the batch mapping and the real-time view, the application that captures sign-ups often computes the same person key itself and stores it on the customer and subscription rows, where it drives business rules (a one-active-subscription-per-person guard, a staff duplicate worklist) rather than the golden table. A pipeline-only fix leaves those rules on the old key: the split people still collide at registration time (a false 'deny' event per registration) and still appear as a duplicate pair to staff, while every dashboard looks right. Search the application code and the stored key column for the key's definition, mirror the new rule exactly (same token rules, same fallback), update every parser of the key format (a two-part length check silently disables the guard once the key has three parts), then backfill the stored keys from a backup copy.

### L-MDM-074  Golden-record write-back must reach every copy the screens read, including the identity provider's login name, under strict invariants
**Kind:** PATTERN · **Proven:** 2026-10-03 · **Evidence:** End-to-end browser tests on web and mobile for ALL CAPS sign-ups, 5 of 5: the name corrected in the database, the identity provider and an open session; both page cards agreed about 85 s after sign-up without a reload; 18 of 31 drifted logins back-filled, drift 0 of 30 afterwards (2026-10-02/03)
A governed write-back of golden-record fields onto the system of origin should accept only a whitelist of identity, contact and address columns (never status, financial, lifecycle, keys or derived values), normalise each golden value to the source's own convention before comparing (for example phone to +E.164) so an unchanged record writes nothing, push only records the DQ rules mark valid, audit every change by record id with before and after values and no raw PII in the audit key, and arrive through the application's own API with service credentials (one writer of golden data into the app, L-CAI-088). Before calling a write-back done, list every copy the screens actually read (database rows, the identity provider's profile and token claims, the CRM, caches): web and mobile apps usually render the person's name from the login token (a name claim taken at sign-in), so a DQ-corrected name (for example an ALL CAPS sign-up) reached the database but stayed wrong in every app. Update the identity-provider user too, only when the words are equal ignoring case (a re-casing, never another person's name), keeping its own first/last split, never failing the write-back on an identity-provider error, and audited; make the web session re-read userinfo about once a minute, let mobile prefer the API profile value when the email matches, and back-fill logins that already differ. Measured: source insert to database and identity provider corrected in 1.5-2.7 min (the golden mapping plus a 120 s activation loop), and an open web session followed about 20 s later. During that gap the golden record is clean while the write-back has not landed, so a page that shows both disagrees: poll until they match (every 5-10 s, up to 3 min). For erasure, the opposite direction, see L-DBMI-051.

### L-MDM-075  Deterministic property match: never merge on parcel or address alone; sort in the warehouse, assign masters with variable ports
**Kind:** PATTERN · **Proven:** 2026-11-01 · **Evidence:** One state (2.5M properties): 36,153 shared-address groups were all distinct parcels, 44,907 shared-parcel groups were condos; the key merged none of them (2026-11-01)
Same parcel is not same property (condo units share one parcel; some state feeds reuse parcel numbers across counties) and same address is not same property (house plus vacant lot, units with no unit number). A safe automatic merge key for property records is state + ZIP5 + normalized parcel + normalized address + unit + class; everything else stays its own master. Read the observations ordered by that key in the warehouse (no DTM sorter cache), recompute the key visibly in an Expression, and carry the first id of each key run in variable ports (`v_master = IIF(key changed, id, v_master)`). If the warehouse and the Expression ever normalize differently a group is only split (a missed merge), never merged wrongly. Write one cross-reference row per source observation (confirmed / merged) so survivorship reads only the cross-reference.

### L-MDM-076  Confirm condo unit -> building hierarchy from postal verification, not from inferred memberships
**Kind:** PATTERN · **Proven:** 2026-11-01 · **Evidence:** Applied to one state's inferred memberships and land parcels: the premise rule confirmed the unit memberships it could, and land parcels moved from failed to non-postal certified (2026-11-01)
Inferred unit-in-building memberships (same address, review status) do not satisfy a serving gate that needs a confirmed parent. A rule that holds up: when address verification confirms the unit (delivery point quality plus the same sub-building token), the unit belongs to the building at its verified premise; build the building id from the verified premise without the unit plus ZIP5 (for example a hash of it), write one confirmed unit_in_building relationship row per unit from the golden-record mapping (a third Router group), keep the inferred membership as evidence in the row, and hold units without a verified unit (code it, e.g. CONDO_PARENT_UNCONFIRMED). Land parcels need the opposite rule: no deliverable address is expected, so certify them as non-postal with the assessor parcel record and coordinates as existence evidence instead of failing them. Newer evidence: L-MDM-089.

### L-MDM-077  Classify a dataset before matching it: rows repeated per scope in a registry are the grain, not duplicates
**Kind:** PATTERN Â· **Proven:** 2026-11-02 Â· **Evidence:** 1,790-row registry: 70 same-domain groups (1,459 rows) and 27 same-name groups (841 rows), but only 6 same-name-and-scope groups (12 rows) were real duplicates; 220,827 referencing rows carried the placeholder id (2026-11-02)
A source registry that keeps one row per dataset per state repeats every national dataset once per state, so a same-name or same-domain duplicate check reports most of the table as duplicates. Decide the archetype first (entity master, registry, versioned asset, definition, event) and the grain (one row = dataset x scope). Model registries as provider -> dataset -> per-scope feed, and count only same name + same scope as a duplicate. Placeholder foreign keys such as 'unresolved' on the referencing table are orphans and belong in the registry's acceptance gate.

### L-MDM-078  One asset, many ids: build the alias crosswalk before mastering a versioned registry
**Kind:** PATTERN Â· **Proven:** 2026-11-02 Â· **Evidence:** 65 version ids vs 284 artifact ids (258 matching no version) and 40 evaluation ids (none matching); artifacts themselves complete (487/487 chunk sets) (2026-11-02)
In a captured model registry the same model showed up under three identities: the registry name (family:scope), the artifact file name (scope.asof-date.ext) and the legacy table that logged its evaluations, and some captured rows used a source table name as the model id with the capture run as the version. Every join between versions, artifacts, evaluations and deployments came back empty. Build the asset alias crosswalk first (pattern rules plus a steward list for the rest), then master family -> asset -> version with one champion per scope, and gate on artifacts and evaluations that map to no version.

### L-MDM-079  One golden owner per entity scope: competing golden builds and run ids in the replace key give one entity several golden rows
**Kind:** PATTERN Â· **Proven:** 2026-11-02 Â· **Evidence:** Shared table: two golden publications in one state, 4.70M rows / 2.18M ids in one of them; the separately built one-row-per-entity table passed (rows = ids) (2026-11-02)
Two pipelines both published golden rows for the same entities in one shared table, so part of one state had two golden records per entity. Inside one publication, re-runs also accumulated (4.70M rows for 2.18M entity ids) because the replacing table's sort key carried the record id and publication id, so a replacing merge never collapsed them. Gate on two things: exactly one publication holding golden rows per scope, and count() = uniqExact(master_id) in the current publication. Make the master id the replace key of the golden table. Retire a superseded build with versioned tombstones, not deletes. Newer evidence: L-MDM-083. Newer evidence: L-ENV-139.

### L-MDM-080  Reconcile a data dictionary against the live schema in both directions, and check the change plan before retiring a definition
**Kind:** PATTERN Â· **Proven:** 2026-11-02 Â· **Evidence:** Dictionary of 1.50M current entries: 457 + 10 definitions without a live column, of which 462 were planned; 26,858 unresolved source mappings (2026-11-02)
A dictionary audit found 457 definitions for a table that did not exist and 10 for columns missing from the live table. The 457, plus 5 of the 10, belonged to a planned rename and a finished table waiting to be swapped in. Retiring them would have broken the cutover. Only 5 definitions had no live or planned column. Reconcile both ways (live columns without a definition, definitions without a live column), tie every definition for a not-yet-live object to a named change, and close the vocabularies. The same audit found one severity concept spelled five ways (hard, error, soft, info, transform) and 5 rule ids defined more than once.

### L-MDM-081  A mapping whose Source query does all the work is not mastering: move survivorship, vocabularies and rules into transformations
**Kind:** GOTCHA Â· **Proven:** 2026-11-02 Â· **Evidence:** Read-only export of 5 mappings: 4 had no Aggregator, Router, Sorter or Verifier and carried 2-36K chars of SQL; the golden-record stage mapping built the other way (sorted Aggregator + Rule Specifications + Router), like the Cleanse + Verifier stage before it, applied its rules in IDMC (2026-11-02)
A project with 54 mappings looked complete, but most were one-offs (one copy per state, shard or table, none parameterized), and the mastering logic sat in the Source: a 35,738-character warehouse query doing survivorship, then one Rule Specification, an Expression and the Target. An 'address verification' shard had no Verifier at all. IDMC only moved rows, so the DQ assets did not run, lineage showed query -> table, and each change meant editing every copy. Test: if removing every transformation between Source and Target changes nothing the query does not already do, the mapping masters nothing. Keep the Source to select + scope filter + ORDER BY, and put the work in Cleanse/Verifier, Lookup or Dictionary, Rule Specification, Expression variable ports (match), sorted Aggregator (survivorship) and Router (steward queue). Use one parameterized mapping per table and archetype, plus one gates mapping and one taskflow. Newer evidence: L-CDI-293. Newer evidence: L-MDM-086.

### L-MDM-082  Verify that sources actually conflict before designing an MDM survivorship demo: two stores were a byte-identical mirror, so survivorship had nothing to decide
**Kind:** PROCESS · **Proven:** 2026-08-03 · **Evidence:** 0 divergence across 800 x 22 fields; plan rebuilt as a 98,115-row single-source track plus a 9,105-row two-source track (2026-08-03)
A property MDM plan was built on 'MDM reconciles the warehouse against the document store'. An adversarial check of 800 records x 22 fields found the two stores were a byte-identical mirror of one public source (0 divergence, no parcel with more than one source), so a conflict-survivorship demo would have fired on nothing. Measure overlap and per-field divergence between candidate sources first; if none, design a single-source mechanics track (1:1, fuzzy off) and a separate real two-source track on a small area. The same review removed claims that were not in evidence: a 'percent headless' figure, undocumented record-state tokens, and a per-call address limit that does not exist; pin such terms against a live record read and the product documentation.

### L-MDM-083  After every golden-table rebuild, compare its row count and identity-status mix with the previous build before you declare it done: one rebuild silently doubled the table with held provisional records
**Kind:** GOTCHA · **Proven:** 2026-11-04 · **Evidence:** Golden table 203.9M rows written over about 20 h; 50.5 % provisional (21.9 % address, 21.2 % parcel, 7.3 % source id); confirmed rows 66.9 % serving; gold rule score 90.3 % (2026-11-04)
An overnight rebuild of a one-row-per-entity golden table wrote 203.9M rows, about twice the 101M of the previous build. 50.5 % of them were provisional identities (provisional address, provisional parcel or source-id-only). The serving gate held: none of the provisional rows were serving or ML eligible. But every mastering rule fell to about 49-52 % (class mastered, identity confirmed, address verified), so the table-level score dropped and looked like a data regression. Add a post-build check: total rows, distinct entity ids and rows by resolution status against the last build, with a tolerance. Score eligible rows and all rows separately. Then decide whether held records belong in the golden table at all. Refines L-MDM-079.

### L-MDM-084  A repeat sign-up with the same name and address is correctly merged into the existing golden customer, but downstream CRM writes then land on the survivor while the new CRM contact stays orphaned
**Kind:** GOTCHA · **Proven:** 2026-11-10 · **Evidence:** 2 paid customers listed as open trials; 2 contacts lost their tag and were re-tagged; the duplicate-merge story itself passed as designed
Match-and-merge folded re-registered people into their existing golden record, and their purchase then attached to the survivor's CRM record; the new sign-up's own CRM contact had no plan, so an agent querying CRM listed paying customers as open trials. A later write also overwrote the sign-up source tag with a sales channel, dropping contacts out of the agent's filter. Downstream systems must resolve identity through the golden id / cross-reference, not through their own per-sign-up record: merge or link the duplicate CRM contact when the master merges, and never reuse a tag or lineage field for a second meaning.

### L-MDM-085  Mapping-based mastering on ClickHouse ran 10-100x slower than in-warehouse SQL on full rebuilds; it is viable only when each cycle processes the changed ~1%
**Kind:** PERF · **Proven:** 2026-11-12 · **Evidence:** IDMC: standardization 383M rows in 5.8 h (1,372 rows/INSERT), merge routing 29.7M in 7.4 h (200 rows/INSERT); SQL: 2.0B rows in 50.5 min and 1.09B in 147 min of query time; 850,912 of 91,749,560 rows changed per build; ~1.8B rows rewritten/day
Measured from ClickHouse system.query_log on the same server: IDMC mappings writing over JDBC V2 reached about 1,100-18,000 rows/s (all tasks together), while set-based SQL inside ClickHouse wrote 124,000-660,000 rows/s, because without pushdown every row leaves the database, crosses the agent's engine and comes back. A full national rebuild through mappings would take about 8-25 h per pass against about 4 h/day for the SQL. Only 0.93% of golden rows changed per build, and that slice (about 850k rows) takes roughly 1-13 minutes in IDMC. Design a mapping-based master as incremental from day one (input fingerprint; re-run match and survivorship only for touched entities); do not compare IDMC with SQL on full rebuilds. Refines L-AGENT-118.

### L-MDM-086  Post-mortem of a home-grown MDM built with IDMC mappings: it worked on one state and was abandoned at national scale for design reasons, not because mappings cannot master
**Kind:** PATTERN · **Proven:** 2026-11-12 · **Evidence:** Single-state results: 2.52M source records -> 2.52M masters with 0 diffs on single-source masters (golden step 13-38 min); identity matching 235,734 rows -> 169,916 entities, 0 wrong merges in 939 checked pairs; national IDMC standardization 383M rows in 5.8 h; the national master then built by 6,649 plain-SQL statements
A property master built with IDMC transformations (Cleanse/Verifier, Rule Specifications, match on sorted input, sorted-Aggregator survivorship, Router to a review queue) was proven on single states, then replaced by plain SQL when scaled to about 92M entities. The costly mistakes, in order: (1) full rebuilds instead of incremental; (2) jumping from a 235k-row pilot to national without a sizing step; (3) four competing golden builds in 12 days instead of one owner evolving one pipeline; (4) logic as SQL text, first in mapping source queries, then outside IDMC; (5) one copy per state (123 mappings/tasks) instead of one parameterized mapping, with one state re-run about 11 times; (6) tuned JDBC write settings not carried into new mappings; (7) matching on blank standardized keys; (8) gates measured but never allowed to stop a publish; (9) IDMC merge decisions computed and never consumed; (10) rules prototyped in Python/SQL and never ported back; (11) orchestration by AI coding sessions (reaped after 120 min idle) instead of a scheduled IDMC taskflow; (12) no budget for jobs and paid calls. Use the list as a pre-scale checklist. Refines L-MDM-081.

### L-MDM-087  IDMC merge decisions and DQ results that no downstream step reads: 29.7M routing decisions, a 3.56M-pair review queue and 140M+ rule-result rows changed nothing in the golden table
**Kind:** GOTCHA · **Proven:** 2026-11-12 · **Evidence:** Routing 29.7M rows, review queue 3.56M rows, DQ rule rows 140M+; IDMC standardized facts WERE consumed (via one SQL facts table), routing and queue were not
The IDMC pipeline wrote merge-or-review routing decisions with keep-apart rules, a steward review queue and per-rule DQ results, but the golden build re-derived duplicates with its own SQL rules, so two rule sets existed and the IDMC outputs were dead ends (only ad-hoc SELECTs read them). Before claiming IDMC masters a table, prove each IDMC output has a consumer: in query_log, look for INSERT ... SELECT statements whose `tables` include the decision table and whose target is a golden-stage table. Either make the IDMC decisions the input of the merge (then a short Post SQL fold, L-CDI-273) or retire the IDMC step; compare IDMC and SQL decisions on one scope first. Refines L-METHOD-043.

### L-MDM-088  Standardized match-key columns left blank on held (provisional) rows made half a golden table unmatchable: millions were exact duplicates of confirmed entities by raw address
**Kind:** GOTCHA · **Proven:** 2026-11-12 · **Evidence:** Golden table 204.6M rows / 302 GB; provisional 100.6M (49.2%): address 44.75M, parcel 43.39M, source-id-only 12.45M; standardized address blank on 100% of provisional rows
The matcher keyed on standardized address columns, but those columns were empty on every provisional row, so 49% of the golden table stayed provisional and could never merge. Matching the same rows on the raw normalized address found 12.85M provisional-address rows equal to a confirmed entity's state + address and 2.5M provisional-parcel rows equal to a confirmed parcel id (about 17-19M likely unmerged duplicates). Add a gate that fails the run when any row entering matching has a blank match key, and profile match-key completeness per scope (state, source) before every match run. Refines L-DQ-145.

### L-MDM-089  Condo units without a unit number collapse onto one served address: gate on no duplicate (address, ZIP, unit) among served rows and recover units before matching
**Kind:** GOTCHA · **Proven:** 2026-11-12 · **Evidence:** Blank unit + different parcels 408,251 groups / 916,284 rows; blank unit + same parcel 41,828 / 85,521; unit set + different parcel 10,173 / 21,717; old table 442,526 groups / 1.61M served rows; one address repeated 53 times
In a property master, about 916k served rows shared a standardized address with a blank unit number across different parcels, and 85k more shared both the address and the parcel (condo units that lost their unit). Address-only match keys either merge distinct units or leave visible duplicates; a rule that unit-less units must not be served had been written but was not enforced. Gate: group served rows by state, ZIP, house number, street, suffix and unit and fail on any group > 1. Recover units by cleansing the source unit field, verifying it, and placing units under their building by parcel (L-MDM-076). Check first whether the sources carry units at all. Refines L-MDM-076.

### L-MDM-090  Insert a sizing step between pilot and fan-out: measure rows/s, jobs per run and sort memory on one scope, then extrapolate before scaling a mastering pipeline
**Kind:** PROCESS · **Proven:** 2026-11-12 · **Evidence:** Pilot 235,734 rows; national ~92M entities; full IDMC pass estimated 8-25 h; job cap ~10,000/month; one state re-run ~11 times (197M rows written for 17.9M entities)
A master went from a 235k-row single-state pilot straight to about 92M entities; throughput, the monthly job count and the warehouse sort-memory cap (L-CDI-272) were all discovered at go-live under deadline, and the team switched to plain SQL. Before fanning out: run one mid-size scope, record rows/s per stage from the warehouse log, jobs per scope (N tasks in a taskflow = N+1 jobs), and peak memory of the sorted reads; compute national time, monthly jobs and memory headroom; fan out in scope groups only if all three fit, otherwise redesign first (incremental, sharding, fewer bigger runs).

## Superseded / overturned (kept so nobody re-learns them)

### L-MDM-059  A record-API 404 'metadata ... cannot be found during load' means the business entity is not deployed, overturned 2026-07-08
**Was believed:** 2026-07-04 to 2026-07-06 · **Overturned by:** L-MDM-006
With `MDM_MATCH_MODEL` count 0 and the record API answering 404, the runtime was thought never to have activated, and a UI deploy was treated as the single gate. The entity had been addressed by its design GUID; by its runtime id it answered 200, and hundreds of active records already existed.

### L-MDM-060  MDM is undeployed because about 30 config, deploy, record and steward REST endpoints return 404, overturned 2026-07-06
**Was believed:** to 2026-07-06 · **Overturned by:** L-MDM-018
The 404s reflected missing public routes. The Business 360 Console My Jobs page showed successful MatchMerge and ingress jobs, which prove deployment.

### L-MDM-061  Ingest Person records with fullName, sourceRecordCount and an integer trustScore, overturned 2026-07-08
**Was believed:** 2026-07-05 to 2026-07-08 · **Overturned by:** L-MDM-019
The early field map sent `fullName` and `sourceRecordCount` and treated `trustScore` as a number. `fullName` is computed (send `firstName` and `lastName`), `sourceRecordCount` is not in the model (400), and `trustScore` must be a string.

### L-MDM-062  A 403 on GET entity/<be>/<id> means the entity exists and you only lack rights, overturned 2026-07-27
**Was believed:** to 2026-07-26 · **Overturned by:** L-MDM-009
The identical 403 fires for a fabricated entity name, because the access check runs before the metadata lookup.

### L-MDM-063  MDM model deploy must have a REST verb somewhere: keep hunting, overturned 2026-07-27
**Was believed:** to 2026-07-26 · **Overturned by:** L-MDM-005
Absence was treated as "not yet found". Eighteen shapes returning a uniform 404 with no 405 meet the stopping rule: the route does not exist; plan the Modeler step.

### L-MDM-064  The <pod>-mdm host is not mounted on this org, overturned 2026-07-26
**Was believed:** 2026-07-26 · **Overturned by:** L-MDM-010
Declared after `/business-360/*` returned 404. Another prefix on the same host answered with a role-gap 403 while its bogus sibling returned 404.

### L-MDM-065  Reference 360 is unavailable because referenceDataSets returns 404, overturned 2026-07-26
**Was believed:** 2026-07-26 · **Overturned by:** L-MDM-026
One 404 on one path was generalised to the service. The search sibling returns a validator 400, so Reference 360 lookup is headless.

### L-MDM-066  MDM / Customer 360 is not licensed on the org, overturned 2026-07-27
**Was believed:** 2026-07-04 to 2026-07-06 · **Overturned by:** L-MDM-011
Inferred from the login `products[]` list, which showed only Integration Cloud. Privileges, roles, the console apps and dozens of MDM design objects showed full entitlement.

### L-MDM-067  The Product 360 documentation describes the MDM you have, overturned 2026-07-27
**Was believed:** to 2026-07-26 · **Overturned by:** L-MDM-055
A P360 doc URL was assumed to cover the licensed MDM, so its automation notes were applied. P360 Cloud Edition is a different, AWS-hosted product with no REST API.

### L-MDM-068  The migration clone route is closed on this pod (import/package 404 MigrationSvc_025), overturned 2026-07-26
**Was believed:** 2026-07-26 · **Overturned by:** L-MDM-014
The probe had sent `application/json`. With `multipart/form-data` the import route accepts uploads; what the org lacked was a template to clone.

### L-MDM-069  There is no public REST search, list or count of MDM records, so master-record counts cannot be read headless, overturned 2026-09-28
**Was believed:** 2026-07-08 to 2026-09-27 · **Overturned by:** L-MDM-025
Held while the probed routes were `.../entity/<be>/search` (404/405) and job routes. `POST /search/public/api/v1/search` pages and exports master records, up to 10,000 per query.
