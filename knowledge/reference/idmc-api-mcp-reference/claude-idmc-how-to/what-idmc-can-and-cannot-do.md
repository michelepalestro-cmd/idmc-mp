# What IDMC CAN and CANNOT do over its APIs and MCP

> **Currency.** This guide is a snapshot of the live evidence up to 2026-07-26. Several walls below have since fallen
> (design objects authored by package import, the DBMI task lifecycle, a `PUT` on runtime-environment selections, full
> SQL ELT pushdown, `PATCH` on v3 folders and catalog assets, lineage over REST (L-CDGC-181), per-rule DQ pass rates
> (L-DQ-123), 23 managed MCP servers (L-MCP-132)). Check the currency list in [the Reference Library README](../../README.md) and the topic
> folders before quoting any limit from this file.

**The whole answer, in one file.** Nothing here is inferred. Every claim below traces to either a
live HTTP status code observed against a real IDMC org, or a named Informatica guide — and the two
are never blended into a single confident-sounding sentence.

Corpus as of 2026-07-26: **166 endpoints**, **830 endpoint×verb combinations**, **11 MCP actions**,
**26 operations with no endpoint at all**, across **13 services** and **14 auth planes**. Verified
2026-07-25 against two orgs (Org A on a `dm-us` pod, and Org B, a sub-org on a `dmp-us` pod).

> **Counts in this file are as of 2026-07-26.** The generated set has since grown (167 endpoints,
> 102 with a working verb, 835 combinations, 28 endpointless operations, 15 auth planes); take
> current numbers from `csv-every-endpoint/` or `idmc-endpoint-dictionary.md`, not from this file.

---

# 1. The one-paragraph answer

**IDMC lets you read almost everything, run almost everything, and design almost nothing.**

You can list, inspect, execute, schedule and monitor over REST. You can create the *operational*
objects — connections, users, groups, runtime environments, mapping tasks, schedules, catalog
sources, marketplace collections and orders, DQ dictionaries. You **cannot** author the *design*
objects: a mapping's transformation logic, a taskflow's publish step, a DQ rule's logic, an MDM
business entity, a Mass Ingestion task, a masking policy. Those are UI clicks with no HTTP verb
behind them, and no amount of correct authentication changes that. Plan on automating the pipeline
around a human who clicks Publish once per design change.

---

# 2. CAN — what works today

**100 of 166 endpoints have at least one verb proven live.** Proven means a status code was actually
observed, not that a guide mentions it.

## 2.1 By service

| Service | Endpoints | Proven working | `GET` | `POST` | `PUT` | `PATCH` | `DELETE` |
|---|---:|---:|---:|---:|---:|---:|---:|
| CDI — Cloud Data Integration | 23 | **21** | 21 | 7 | 0 | 0 | 1 |
| Administration & Core platform | 27 | **19** | 13 | 8 | 0 | 0 | 2 |
| CAI — asset lifecycle | 18 | **13** | 10 | 5 | 0 | 0 | 0 |
| Data Marketplace | 14 | **11** | 10 | 7 | 0 | 0 | 0 |
| CDGC — Governance & Catalog | 17 | **9** | 5 | 6 | 0 | 0 | 2 |
| Data Profiling | 11 | **9** | 9 | 0 | 0 | 0 | 0 |
| CAI — invocation & runtime admin | 16 | **9** | 5 | 0 | 0 | 0 | 0 |
| Migration — export & import | 7 | **5** | 3 | 2 | 0 | 0 | 0 |
| MDM / C360 / B360 / R360 | 11 | **5** | 4 | 1 | 0 | 0 | 0 |
| CDQ — Cloud Data Quality | 9 | **2** | 1 | 1 | 0 | 0 | 0 |
| Mass Ingestion | 7 | **1** | 1 | 0 | 0 | 0 | 0 |
| Operational Insights | 2 | **0** | 0 | 0 | 0 | 0 | 0 |
| Data Access Mgmt / API Mgr / CLAIRE | 8 | **0** | 0 | 0 | 0 | 0 | 0 |

CDI is the most automatable service in the platform. DAM, API Manager, CLAIRE and Operational
Insights have **zero** proven endpoints — see §3.4 before concluding they are broken.

## 2.2 The complete write surface — all 37 proven `POST` endpoints

This is every write and every run you can perform today. If an operation is not on this list and not
a `DELETE` in §2.3, you cannot do it over REST.

**Authentication (5)** — `/ma/api/v2/user/login`, `/saas/public/core/v3/login`,
`/identity-service/api/v1/Login`, `/identity-service/api/v1/jwt/Token`, and the session flows behind
them. Start here; see §5.

**Administration (6)** — create a **connection** (`/api/v2/connection`), **update** one
(`POST /api/v2/connection/{id}` — this *is* the update, there is no PUT), create a **runtime
environment**, create a **user** (`/public/core/v3/users`), create a **group and bind roles**
(`/public/core/v3/userGroups`), post platform **alerts**.

**CDI execution (4)** — **run a task** (`POST /api/v2/job` — RunAJob, the workhorse), create a
**mapping task** from an existing mapping (`/api/v2/mttask`), **update** that task
(`POST /api/v2/mttask/{id}`), create a **schedule** (`/api/v2/schedule`).

**CAI (5)** — **bulk publish** up to 199 assets (`/active-bpel/asset/v1/publish` → 202 + job id),
**bulk unpublish**, **invoke a process** authenticated (`/active-bpel/rt/{Process}`), invoke
**anonymously** with no header at all (`/active-bpel/public/rt/...`), send an anonymous **message
event**.

**CDGC (6)** — **register a catalog source**, **trigger a scan**
(`/data360/executable/v1/catalogsource/{id}`, body `capabilityNames[]`), **enterprise search** with
raw Elasticsearch DSL (`/data360/search/api/v1/search`), list executables, and the CDGC **write
plane** `/ccgf-contentv2/api/v1/publish` — certify, relate, assign.

**Data Marketplace (7)** — create a **data collection**, a **data asset**, a **category**,
**terms of use**, a **delivery target**, and **place an order** on either the v1 or v2 plane. The
full provisioning chain has been run end to end.

**Migration (3)** — start an **export** job, **import** a genuine export zip
(hand-built zips are rejected with `MigrationSvc_030`), and **export IPU metering** data async.

**CDQ (1)** — create a **DQ dictionary** (`/quality/public/v2/dictionaries/`).

**MDM (1)** — **ingest a source record**
(`/business-entity/public/api/v1/entity/{be}?sourceSystem=X` → 201).

## 2.3 The complete delete surface — all 5 proven `DELETE` endpoints

`/api/v2/connection/{id}` · `/public/core/v3/users` · `/public/core/v3/userGroups` ·
`/data360/catalog-source-management/v1/catalogsources` and its `/{id}` form.

That is all. `DELETE` matters more than its count suggests because it is **half of the sanctioned
update pattern** — see §4.

## 2.4 What MCP can do

All 11 actions, every one an HTTP `POST`. **Only `checkout_data_order` writes anything.**

| Server | Actions | Can |
|---|---|---|
| Job Management | `run_mapping_task`, `get_job_status`, `stop_running_job` | Trigger, watch and kill a CDI task |
| CDGC Metadata Search | `search_metadata`, `get_asset_details` | Natural-language catalog search; **asset lineage** |
| Customer Identification | `search_master_record`, `get_master_record_details` | **Fuzzy identity match**; golden record |
| Data Provisioning | `list_data_collections`, `list_delivery_targets`, `checkout_data_order` | Browse marketplace; **raise a governed access request** |
| Address Verification | `verify_address` | Validate / standardize / geocode, 240+ countries |

**MCP can do exactly two things REST cannot:** read asset **lineage** (`get_asset_details`) and
**fuzzy customer identity match** (`search_master_record`). Every REST lineage path returns 404, and
REST has no public MDM search resource. Those two are the entire case for using MCP.

> **Later evidence.** Lineage is now readable over REST, hop by hop, through the asset read's `lineage` segment
> (`GET /data360/search/v1/assets/<identity>?scheme=internal&segments=all`); only the `/data360/lineage/*` graph routes
> stay 404 (L-CDGC-181). The five servers above are the April 2026 catalog: the public MCP registry listed 23 managed
> servers as of the October 2026 release (L-MCP-132).

The other 8 actions wrap a REST endpoint you could call directly, and **REST is often more
capable**: raw Elasticsearch DSL vs one search string, 1,000 addresses per call vs one, full job
history vs a single job.

---

# 3. CANNOT — and exactly which kind of "cannot"

**This is the section that matters, because "cannot" has four completely different meanings.** Get
these confused and you will either tell a customer something false or waste weeks probing a wall.

| # | Kind of cannot | How you know | What to do |
|---|---|---|---|
| 1 | **Hard wall** — no verb exists | `404` with an **empty body**, or `405` on every verb | Stop. Design a human click into the process. |
| 2 | **Read-only resource** | `405 Method Not Allowed` | The route is real, this verb is not. Use §4's update pattern. |
| 3 | **Not on this pod** | `404` **with** a body | Try the other pod/host. Says nothing about entitlement. |
| 4 | **Nobody checked** | absent from all evidence | **Unknown, not unsupported.** Never quote it as a limit. |

## 3.1 Genuinely cannot — the UI-only walls (14 confirmed)

Each of these has a real failure signature. The "what DOES work" column is what you can still
automate around the wall.

| You cannot | But you CAN | The failure you'll see | Human clicks |
|---|---|---|---|
| Design a **CDI mapping** | list / run / schedule / monitor it | `POST /api/v2/mapping` → 400 HTML; v3 objects → 405 | Mapping Designer canvas |
| **Publish a taskflow** | `GET` the taskflow (200) | `POST /api/v2/taskflow/publish` → 404 | DI designer Publish |
| Author **Mass Ingestion tasks** | see engines RUNNING; read activityLog | every `mi`/`dbmi` path 404; `MI_TASK` count 0 | Mass Ingestion wizard |
| Author **CDQ rule logic / scorecards** | read and clone rule specs; read per-rule pass rates from the metric store (later evidence, L-DQ-123) | `data360/dq/*` 404; no create on RuleOccurrence | rulebuilder + DQO wizard |
| **Accept CLAIRE classifications** | read classifications | 37+ accept paths 404; UI offers only Dismiss | auto-accept threshold + re-scan |
| **Deploy an MDM business entity** | read 97 `MDM_*` design objects | ~20 deploy paths 404; `BUSINESS_ENTITY` count 0 | B360 Modeler Publish |
| Run **MDM ingress / match-merge** | ingest a record (201) | all ingress and job paths 404 | B360 Console |
| Bind a **glossary term to a column** | read the glossary; link terms with a `glossary` segment PATCH on `data360/content/v1/assets` (later evidence, L-CDGC-056) | ~20 paths 404, empty bodies | CDGC UI (partial `ccgf-contentv2` workaround) |
| Assign a **steward / data owner** | read stewards | stewardship writes 404 / 405 | CDGC UI |
| Create a **Marketplace delivery template** | read templates | **405 on every verb** | Marketplace UI, headed browser |
| Create a **DAM masking policy** | — | ~40 policy paths 404; policy count 0 | engine deployed, no REST plane at all |
| **Register a connector type** | see the connector in the global catalog | `403 no connector with type=X` | **one** UI Save in Administrator |
| Toggle the **CAI process engine** on the prod agent | `/process-engine/status` → 200 | `POST /api/v2/agent/service` → 403 `APP_13401` | Administrator UI toggle |
| Design **rich transforms** (joiner, aggregator, expression) | run what exists; switch full SQL ELT pushdown on through the v2 mapping task (later evidence, L-CDI-202) | no authoring verb in this snapshot | Mapping Designer |

Plus 12 more endpointless operations in `06_no_endpoint_ui_only.csv`: CAI event sources and file
listeners, human tasks, service connectors, API activate/deactivate, MDM match/merge/survivorship
config, Operational Insights alert rules.

**The pattern.** Read, run and operate are automatable. **Design and publish are not.** That single
sentence is the shape of this entire platform.

## 3.2 Cannot in place — `PUT` and `PATCH`

**Zero `PUT` and zero `PATCH` are proven live anywhere across 166 endpoints** (July 2026 census).

> **Later evidence.** `PUT` was proven on runtime-environment selections (L-AUTH-016) and `PATCH` on v3 folders and
> projects (L-MIG-105) and data360 content assets (L-CDGC-053); `DELETE /public/core/v3/users/{id}` returns 204
> (L-AUTH-058). The 405 on the other verbs of that path still holds.

| Verb | Works | Documented only | Rejected | Untested |
|---|---:|---:|---:|---:|
| `GET` | 82 | 6 | 39 | 39 |
| `POST` | 37 | 9 | 30 | 90 |
| `PUT` | **0** | 14 | 12 | 140 |
| `PATCH` | **0** | 5 | 9 | 152 |
| `DELETE` | 5 | 7 | 6 | 148 |

14 `PUT`s and 5 `PATCH`es are *documented* by Informatica but were never exercised here — that is
"plausible, unproven," not "works." The canonical proof is `/public/core/v3/users/{id}`, where
`GET`, `PUT`, `PATCH` **and** `DELETE` all return **405**. See §4 for what to do instead.

> **Do not tell anyone "IDMC supports PUT" on the strength of a documented row.** This distinction
> is the most valuable thing in this knowledge base.

## 3.3 Cannot preflight — no `HEAD`, no `OPTIONS`

Neither verb appears in any guide or any probe. There is no capability-discovery mechanism.

**To test whether a write verb exists, `POST` an empty body:**
- `400` / `415` / `422` → **the verb exists**, you have the body shape wrong. Keep going.
- `405` → the verb does not exist. Stop.

This one trick converts an unknown into a finding in a single call.

## 3.4 "Cannot" that is probably wrong — 569 untested combinations

**569 of 830 endpoint×verb combinations have never been sent.** That is 69% of the matrix.

DAM, API Manager, CLAIRE and Operational Insights show 0 proven endpoints — but that is mostly
*unprobed*, not *refused*. Operational Insights in particular is **GraphQL, not REST** (one endpoint
at `/active-bpel/opsanalytics-das/metrics` taking `?query={...}`), which is why REST-shaped probes
found nothing. A `400` from it is **positive evidence** that the endpoint parses input.

**Never quote an untested cell as a product limitation.** Conflating "we didn't check" with "it
doesn't work" produced every wrong conclusion this project has had to walk back.

## 3.5 Corrections — nine things we were wrong about

All nine were believed to be walls and are not. Check this list before repeating a limitation:

| Was believed | Actually |
|---|---|
| CAI publish needs a human click | `POST /active-bpel/asset/v1/publish` → **202**. 4 processes published headlessly. The old probe used the wrong path *and* wrong host. |
| CDQ has no write path | Dictionaries have full documented CRUD on the `-dqcloud-api` host. (Rules genuinely are UI-only.) |
| Data Profiling has no API | **LIVE** at `<short>-dqprofile.<pod>/profiling-service/api/v1/profile` → 200. The host was the missing piece, not the path. |
| Operational Insights is a gap | It's **GraphQL**. Probed as REST on the wrong host family. |
| Scheduling is UI-only | `POST /api/v2/schedule` → 200, creates a real schedule. Never probed before being written off. |
| Marketplace publish is UI-only | Collections, categories, orders, terms of use, delivery targets **all create over REST**. Only the *template* is UI-only. |
| Mass Ingestion isn't provisioned | Engines **RUNNING** on both agents. 404s were misread as missing entitlement. |
| MDM / C360 isn't licensed | **Fully entitled** — 97 design objects, 83 privileges. Inferred wrongly from the login `products[]` list, which is only a label. |
| CDGC scan trigger is blocked | **201** with a real job id, once you send all three identity headers *and* a non-empty `capabilityNames[]`. |

**The lesson in all nine: a 404 usually meant wrong host, and `products[]` never meant entitlement.**

---

# 4. How to update something when there is no `PUT`

Two patterns, both proven:

1. **On the v2 plane, `POST` to `/{id}` IS the update.** `POST /api/v2/connection/{id}` and
   `POST /api/v2/mttask/{id}` both update in place. No PUT needed, none offered.
2. **Everywhere else: `DELETE`, then re-`POST`.** This is why the 5 deletes in §2.3 matter. The v3
   user resource is explicit about it — all four verbs on `/users/{id}` return 405, so you delete the
   user and create them again.

---

# 5. Before you blame the API, check the plane

**Mixing auth planes is the single largest source of false negatives in this corpus.** Fourteen
planes, and the wrong host returns a *convincing* failure — often `200` with login HTML.

| Plane | Endpoints | Host | Send |
|---|---:|---|---|
| v3 platform | 36 | `<pod>.dm-us.informaticacloud.com/saas` | `INFA-SESSION-ID` |
| Identity / CDGC | 35 | `idmc-api.dm-us.informaticacloud.com` | `Bearer` + `IDS-SESSION-ID` + `X-INFA-ORG-ID` |
| v2 platform | 31 | `<pod>.dm-us.informaticacloud.com/saas` | `icSessionId` |
| CAI runtime | 24 | `<pod>-cai.dm-us.informaticacloud.com` | `INFA-SESSION-ID` (+ `vnd.api+json` to publish) |
| Data Profiling | 10 | `<pod>-dqprofile.dm-us.informaticacloud.com` | `IDS-SESSION-ID` (SPA-injected) |
| MDM runtime | 8 | `<pod>-mdm.dm-us.informaticacloud.com` | `Bearer` + `IDS-SESSION-ID` + `X-INFA-ORG-ID` |
| CDQ dictionaries | 6 | `<pod>-dqcloud-api.dm-us.informaticacloud.com` | `Bearer` JWT or `IDS-SESSION-ID` |
| CDGC write plane | 4 | `cdgc-api.dm-us.informaticacloud.com` | all three identity headers |
| Anonymous CAI | 2 | `<pod>-cai.dm-us.informaticacloud.com` | **no header at all** |
| MCP | — | `a2e-prod-<pod>-mcp.dm-us.informaticacloud.com` | `IDS-SESSION-ID` \| `Bearer` \| OAuth2 |

Three logins, not one: v2 `POST /ma/api/v2/user/login` → `icSessionId`; v3
`POST /saas/public/core/v3/login` → `INFA-SESSION-ID`; identity `POST /identity-service/api/v1/Login`
then `/jwt/Token` → the three-header combination. **JWTs live 30 minutes.**

## Decode the failure before you retry

| You see | It means | Do |
|---|---|---|
| `404` **empty body** | real UI-only wall | stop, §3.1 |
| `404` **with** a body | wrong path or host | keep hunting — this is the #1 false negative |
| `405` | read-only resource, at **any** permission level | §4's update pattern |
| `403` | missing role, or unregistered connector type | check the role; not a verb problem |
| `406` | busy — a job is already running | **positive evidence.** Retry later |
| `409` | conflicts with current resource state | resolve state, retry |
| `413` | you exceeded a documented cap | see `09_limits_and_caps.csv` |
| `424` | you skipped a prerequisite call | order the chain correctly |
| `200` + **login HTML** | wrong host or plane | fix the plane, §5 |
| `200` but the value reverts | **silent write rejection** | verify every write with a read-back |
| `200`, 0 bytes, no `Content-Type` | route mounted, nothing serving | not a success |
| `APP_13533` | "specify a mapping id" | `mttask` only **wraps** an existing mapping |
| `MigrationSvc_030` | invalid import package | hand-built zips are rejected; use a real export |

---

# 6. Caps that will bite you

`199` assets per CAI bulk publish · `10,000` rows per CDQ dictionary call (`413` past that) ·
`1,000` addresses per Address Verification REST call, but **1** per MCP call · OAuth access-token
default **5 minutes** (range 5–1440 — five minutes will break any long-running agent) · JWT
**30 minutes** · full list in `09_limits_and_caps.csv`.

**MCP billing trap.** MCP is not separately metered during the AI Agent Engineering preview, but the
underlying CDGC / CDI / Marketplace / MDM service APIs **still bill IPUs**. Budget the backing
service, not the MCP layer.

---

# 7. Four things still genuinely unresolved

Carried openly rather than resolved in either direction:

1. **Org B's `data360` returns zero-byte 200s** even though CDGC is licensed there (create/execute
   privileges and both Governance roles present). Licensing question vs deployment question — do not
   raise it as an entitlement ticket.
2. **CAI scheduler 401s** on `dmp-us` while processes and URN mappings return real JSON — isolated to
   a role gap, not a plane problem.
3. **MDM read-by-id disputed** — `get_master_record_details`' REST counterpart returns 200 on one org
   and 404 on another.
4. **`<pod>-apigw` 503.** Unexplained.

Also unresolved and worth knowing: `content/01-executive-summary.json` lists `PUT`/`PATCH` under
"Verbs proven" for five services, while every detail row for those carries them as `[doc]`. **The
detail rows are authoritative** — that is what §3.2 counts. Flagged to that section's owner.

---

# 8. Two traps that invalidate evidence

1. **`objects?q=type=='X'` returning count 0 proves nothing.** The filter is **not validated** — a
   fabricated type returns the same clean empty envelope (verified with `TOTALLY_FAKE_TYPE_ZZZ`).
   Valid for counting content, **never** for proving capability.
2. **Endpoint availability is per-pod.** Six `/api/v2/` task resources exist on Org A's `dm-us` pod and
   404 on Org B's `dmp-us` pod — in an org holding 876 privileges. Never generalise an inventory from one org.

---

# 9. Where to look next

| Question | File |
|---|---|
| Does verb X work on path Y? | `02_endpoint_verb_matrix.csv` — filter `State` |
| What can I call today, and how? | `01_endpoints.csv` — filter `Any working verb? = YES` |
| Full prose on one endpoint | `idmc-endpoint-dictionary.md` |
| The whole story, by product | the master `.docx` (not shipped; build it with `../build/build_master.py`, needs `python-docx`) |
| Every MCP action | `05_mcp_actions.csv` |
| What has no endpoint at all | `06_no_endpoint_ui_only.csv`, `10_ui_only_walls.csv` |

**Re-verify before you commit to anything.** Vendor-documented rows are durable; live rows are a
dated snapshot, and verdicts in this corpus flipped on a **three-to-five-day cadence**. The probe
harness that dated them reads a local credential file, so it is not shipped with this KB; reproduce its
calls against your own org:

    python probe_idmc_surface.py                # full read-only sweep
    python probe_idmc_surface.py --grep cdgc    # one service

---

*Derived from `content/*.json` as of 2026-07-26 — 166 endpoints, 830 verb combinations, 11 MCP actions, 26
endpointless operations. Live evidence 2026-07-25 from two orgs on two pods. The four verb states
(**Works** / **Documented** / **Rejected** / **Untested**) are never merged anywhere in this corpus.*
