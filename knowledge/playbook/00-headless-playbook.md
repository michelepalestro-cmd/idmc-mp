<!-- The playbook: Laws 0-7, error triage, preflight. Paths are relative to the skill folder. -->
# IDMC headless

## Master IDMC KB — read this FIRST (it is newer and far larger than this skill)

This skill is a July 2026 snapshot (~11 reference files). The maintained knowledge base is
`kb\` (the Master IDMC KB folder; inside this skill) (start at `README.md`):
~2,400 files, **1,800+ lessons** (`lessons\lessons.jsonl`, ids `L-<DOM>-###`, with status current/disputed/superseded).
Where it disagrees with this skill, **the KB wins** (check `lessons\overturned-beliefs.md`).

| Need | KB folder |
|---|---|
| **A new pipeline (any source, any target)** | `knowledge/00-start-here/08-new-pipeline-milestones-any-source-any-target.md`: runtime → connections → folder and assets → contract → mapping → task → run and proof |
| Laws, capability map, error triage | `knowledge/00-start-here` |
| Login, orgs, pods, sessions | `knowledge/01-access-auth-orgs` |
| Secure Agent, runtime, connections (incl. Salesforce) | `knowledge/02-secure-agent-connections` |
| Mappings / taskflows headless, mapping generator, consolidation | `knowledge/03-cdi-data-integration`: **start with `00-mapping-fast-path-read-this-first.md`** (ten commands, per-connector spec settings, costly errors), then one spec from `core\mapgen\examples\` and `core\mapgen\docs\SPEC_REFERENCE.md` |
| DBMI / CDC | `knowledge/04-cdc-mass-ingestion` |
| CAI publish/deploy/processes | `knowledge/05-cai-application-integration` |
| CDQ rules, profiling | `knowledge/06-data-quality-profiling` |
| CDGC catalog, lineage, glossary | `knowledge/07-catalog-governance-cdgc` |
| MDM SaaS | `knowledge/08-mdm` |
| CLAIRE GPT, MCP servers | `knowledge/09-claire-mcp` |
| Export/import, org cleanup, migration | `knowledge/10-migration-org-management` |
| IPU, metering, job caps | `knowledge/11-ipu-metering-licensing` |
| API & MCP reference corpus, verb matrix | `knowledge/12-reference-library` |
| Lessons by domain | `lessons` |
| How Claude works (scripts, patterns) | `knowledge/14-claude-working-methods` (`Script Library\`) |
| Your IDMC login (user, password, login address) | `kb\IDMC_LOGIN.txt` |
| Ready-to-rebuild demo blueprints (CDC, CDI, CAI, CDQ, CDGC) | `kb\demos\` (start at `BLUEPRINT_CONVENTIONS.md`) |
| The generic Python library every blueprint imports | `kb\knowledge/14-claude-working-methods\Script Library\` |
| The headless mapping generator (spec -> mapping -> import package) | `kb\core\mapgen\` |

**The KB and this skill are guidance, not a script.** Build with the user's own source, target and connectors. The
systems in the examples (PostgreSQL, BigQuery, Snowflake, Databricks, Salesforce, SharePoint, ClickHouse, Tableau, flat
files) are examples, not recommendations: never steer the user to one, or fall back to one, because it has more examples.
A connector the KB does not cover is normal: find its settings in the org, prove them with one small run, record a lesson.
The KB is not an allow-list: nothing is forbidden or impossible because the KB does not mention it. Native IDMC first;
Python only when no IDMC path works, and then as a bridge into IDMC.
A source, target or transformation IDMC supports but the generator has no template for: the exemplar route (KB Fast
Path §7.0): an existing or UI-made mapping that uses it, exported, read with `toolkit/mapgen/exemplar.py`, built from,
then added to the package as a template.
Copy the method (order of work, gates, safety rules, evidence); take the systems and settings from the user's org.

Before any IDMC call: `grep -ril "<thing>" "<KB>\lessons"` (Law 1). When you learn something, add it to the topic
doc and as a new lesson in `13` (generic only: no org ids, hosts, people or secrets). Keep your own org's ids in the
blueprint's `config.json`, never in the KB.

Drive IDMC with no browser: what works, how to work around what looks walled, and how to get running fast.

**The core insight (July 2026, since revised):** IDMC lets you **read almost everything and run almost
everything**. The July belief that you can "design almost nothing" is overturned: mappings, mapplets, taskflows, CAI
processes and DQ assets are authored headless through v3 import packages and clones (KB Law 16), and only a short,
dated list of residual clicks remains (KB Law 17). Every "UI-only" or "no REST verb" line below is a July verdict:
before you tell a user no, work the KB's workaround ladder (`knowledge/00-start-here/08 New Pipeline Milestones`, Rule 2).
**Never** answer a gap by steering the user to another technology (Rule 1). Every wrong conclusion this project has walked back came from misreading *which
kind* of failure was in front of it.

**Everything below is org-specific. Start at Law 0.**

## Which task is this? — route before you read

| If the ask is… | Go straight to | The one thing that decides it |
|---|---|---|
| **"set up IDMC" / "stand up an agent" / nothing works yet** | **`knowledge/playbook/03-bootstrap.md`** — read its *four gates* preamble first | **HOST → ENGINE → ADAPTER → DRIVER, in that order.** Four independent things fail with four different errors that all look like "the connection is broken". Establishing them out of order is the difference between an hour and a day |
| **"can IDMC do X headless?"** | Law 6, then `knowledge/playbook/05-endpoints-by-service.md` | Is X **read/run** (yes) or **design-time authoring / publish / deploy** (no create verb: use packages, clones or the UI's own call; KB Law 16, then the workaround ladder)? |
| **A call is failing** | The error-triage table below | Which *kind* of failure is it? A `403` alone distinguishes nothing |
| **"is this licensed?"** | Law 4, then `knowledge/playbook/01-orgs-and-entitlement.md` | `agentEngines[]`, never `products[]`. With no agent installed, entitlement is **unresolved, not disproven** |
| **Writing a request body** | `knowledge/playbook/02-request-bodies.md` | Field names are per-connector and not guessable — read the connector's manifest |

**First time in an org: run the Preflight block near the end of this file before anything else.**
It answers "which org, which pod, which engines" in five calls, and every one of those answers
changes what the rest of this skill means.

## Orientation — the verb surface, in one table

Measured across all 166 endpoints in this corpus. Learn this before designing any call; it prevents
the most common wasted hour.

| Verb | Proven | Doc only | Rejected | Untested | What it means in IDMC |
|---|---|---|---|---|---|
| `GET` | **82** | 6 | 39 | 39 | The real surface. Nearly everything readable is readable. |
| `POST` | **37** | 9 | 30 | 90 | Every write, every run — **and on the v2 plane every UPDATE**. `POST /{id}` *is* the update. |
| `PUT` | **0** | 14 | 12 | 140 | Effectively absent. Documented in places, never once proven live. **Do not design on it.** |
| `PATCH` | **0** | 5 | 9 | 152 | Does not exist in practice. Only MDM even discusses it. |
| `DELETE` | 5 | 7 | 6 | 148 | Rare and clustered. Half of the sanctioned update pattern: `DELETE` then re-`POST`. |
| `HEAD` / `OPTIONS` | **0** | 0 | 0 | 0 | **No preflight discovery exists.** To test a write verb, POST an empty body. |

**So the update idiom is `POST` to the resource id, or `DELETE` + re-`POST`. There is no PUT.**

### The four evidence states — never merge them

Collapsing these is what produced *every* conclusion this project had to walk back.

| State | Means | How to speak about it |
|---|---|---|
| **WORKS** | A live status code was observed, on a stated org and date | "Proven, as of <date>" — re-probe before promising it |
| **DOC** | A named Informatica guide states it; nobody exercised it here | "Documented, unproven." **Never** report as working |
| **REJECTED** | The verb was explicitly refused, with the code | A finding. `405` = read-only, a hard no at any permission level |
| **UNTESTED** | Absent from all evidence — **569 of 830 combinations** | **Unknown, not unsupported.** Never quote one as a limitation |

`--` or a blank cell means **untested**, not absent. `405` means absent. Those are opposites.

### Read / write / run, and what is simply not there

- **READ is broad and headless.** Assume you can read it until a probe says otherwise.
- **RUN is headless.** Start a job, poll it, read the log. The pattern is always **POST to start →
  GET to poll**; `GET` on the starter returns `405`.
- **WRITE splits in two.** Runtime/config objects (connections, catalog sources, schedules) write over
  REST. **Design-time authoring — mappings, glossary bindings, steward assignment, business-entity
  deploy, publish/activate — has no create verb**; most of it is now done headless through packages, clones and
  each service's own calls (KB Law 16), and the few remaining clicks are listed in KB Law 17 (`knowledge/playbook/08-…` is the
  July view).
- **Async everywhere.** A `202`/`201` + job id is success of *submission*, not of the work. Poll.
  Items can fail **inside a 200 envelope** — read per-item status, not just the HTTP code.

## Law 0 — establish the org before anything else

Two orgs are in play and they answer differently. **A proven row from one is not evidence for the
other.** This is the single largest source of wrong conclusions.

| | Org A | Org B |
|---|---|---|
| Name | `Org A` | `data` |
| Org ID | `<orgGuid>` (v3) / `<orgIdA>` (v2) | `<orgIdB>` (v2) / `<orgGuid>` (v3) |
| Pod / domain | `<podA>` / **`dmp-us`** | `<podB>` / **`dm-us`** |
| Base | `https://<podA>.dmp-us.informaticacloud.com/saas` | `https://<podB>.dm-us.informaticacloud.com/saas` |
| Engines | **23** since 2026-07-26 (was 1) incl. `Data_Integration_Server` 77.0.2 | **17** incl. `Data_Integration_Server` |
| Privileges | 876 | 897 |

`dmp-us` vs `dm-us` is one character and silently 404s every borrowed URL. Both org-ID shapes are
real for the same org — v2 IDs differ from v3 IDs. Do not "fix" that.

**One org per session unless told otherwise.** Org A work is Org A-only.

### Working in an org this table does not name

Do not borrow a row above — **derive your own in three calls, before anything else.** Every value
you need comes back from login; guessing the pod is the single most common way to waste an hour.

```bash
POST /saas/public/core/v3/login   {"username": "...", "password": "..."}
# -> userInfo.orgId (v3 shape) | userInfo.orgName | sessionId
# -> products[].baseApiUrl  <-- USE THIS AS YOUR BASE. Never hand-assemble the pod host.
GET  /api/v2/org                  # -> the v2 org ID (a DIFFERENT shape for the same org) + parent
GET  /api/v2/agent                # -> [] means entitlement is UNRESOLVED, not absent (Law 4)
```

Then record, and re-derive per session rather than caching: **org name · both ID shapes · pod ·
domain label (`dm-us` vs `dmp-us`) · base URL from `baseApiUrl`**. Two traps that bite immediately:

- **The domain label is not guessable from the pod name** — read it off `baseApiUrl`.
- **Sub-org membership is explicit per user.** If login lands somewhere other than the org you were
  asked to work in, stop: every documented org-switch path `404`s, so this is an admin action, not
  something to route around. A parent-org admin often **cannot** read a child's agents (`403`).

Credentials come from the toolkit's `IDMC_LOGIN.txt` (three lines: `IDMC_USER`, `IDMC_PASS`,
`IDMC_LOGIN_HOST`; the core library reads it by itself) or the environment, never a literal in a script or a committed
file. If a user cannot connect, the fix is to fill in that one file:

```bash
export IDMC_USER=... IDMC_PASS=...     # environment variables override IDMC_LOGIN.txt
```

⚠️ **A JW token expires 30 minutes from grant.** Any script that runs longer must
re-authenticate, or it dies mid-run for reasons that look like a permissions change.

## Law 1 — search the KB before you call anything a wall

The answer is usually already on disk. Before concluding "not possible" or "not entitled":

```bash
grep -ril "<the-thing>" knowledge/ lessons/by-domain/
grep -i "<endpoint-or-error>" lessons/lessons.jsonl knowledge/playbook/06-lessons-field.md
```

**What this prevents.** A session tried to create a Postgres connection with `type: "PostgreSQL"`,
got `403 APP_10519`, swept 13 spellings, and reported an **entitlement wall** — telling the operator to
raise a licensing ticket. `_evidence/connection_create_body_verified.json` already said: use
`TOOLKIT_CCI`, put the connector name in `instanceName`. The org turned out to hold N of them.
One grep would have saved the session.

## Law 2 — a 200 can be fake; probe a bogus twin

On Org A, `data360` and `cdmp-marketplace` return **200 with a zero-byte body** — and so does a
nonsense path. That is prefix routing, not a handler.

```bash
# real path AND fake path both 200/0-bytes  ->  gateway artifact, NOT a capability
GET  /data360/search/api/v99/bogusZZZ
GET  /api/v2/bogusZZZnope        # control: 404 "Resource not found" => this plane IS real
```

Never report a zero-byte 200 as working. Also treat `200` + login HTML as a wrong plane, and a `200`
whose value reverts as a silent write rejection — read back after every write.

**The twin applies to any input you control, not just the path** — and to error codes, not just 200s:

| Twin the… | Because otherwise you conclude |
|---|---|
| **path** (`/…/bogusZZZ`) | a gateway 200 is a capability |
| **object name** (`entity/ZZFAKEENTITY`) | a `403` means "exists but forbidden" — when the ACL check runs *before* metadata lookup, so it fires for anything |
| **host** (an unroutable IP) | an opaque connection error was a network result, when nothing was ever attempted |
| **error code** (`/api/v2/agent/bogusZZZ`) | a `403`/`500` proves a handler exists, when it is router boilerplate |

If the fake input answers like the real one, you have learned nothing about the real one.

## Law 3 — `404` means wrong path, not unlicensed

`404` with a body → wrong path or host, keep hunting. `404` with an **empty** body → real wall.
`403`/`405` → role or read-only, not entitlement.

## Law 4 — entitlement comes from `agentEngines[]`, never `products[]`

`products[]` on login is a marketing label. Org A shows only `Integration Cloud` while holding CDGC,
Marketplace and MDM privileges.

```bash
GET /api/v2/agent/details/{agentId}   # -> agentEngines[].appname = ground truth
```

No agent yet? Entitlement is **UNRESOLVED, not disproven**. Say so.

## Law 5 — no HEAD, no OPTIONS: probe verbs with an empty POST

`400` / `415` / `422` → **the verb exists**, your body is wrong — keep going.
`405` → the verb does not exist. An empty body cannot create anything, so this is safe.

⚠️ **A write route has two axes, and `Content-Type` is the one everybody forgets.** The same
path answered four ways on one org: `application/json` → **404**, `application/zip` and
`application/octet-stream` → **415**, `multipart/form-data` → **400** (validator reached, route
alive). The `json` 404 is the dangerous cell — it reads as Law 3 "wrong path", so you file it as
absent and walk away. That cost this project a wrong "the backdoor is closed" conclusion about
`/v3/import/package`. **Before declaring an upload route absent, vary the encoding too:** `json`,
`multipart/form-data`, `application/zip`, `octet-stream`. Only `405` on *every* encoding is a
verdict.

## Law 6 — read and run are headless; author, publish and deploy usually are not

`POST /public/core/v3/objects` is **405** — the v3 catalog is read-only. But authoring is not
impossible: **clone through the migration package** (export a same-type template → retarget
GUID/name → recompute SHA256 → `POST /public/core/v3/import/package`). Free, and proven for
`BUSINESS_ENTITY` (Person 41 fields, Supplier 15), `MDM_SRC_SYSTEM`, 2 reference entities and
`RULE_SPECIFICATION` (count 4→11→12). **Import does not deploy** — that stays a UI click.

**Cloning needs a same-type template, so it fails on an empty org — and that is not a route
problem.** On a pod holding a single design object (one empty `Project`), the import route is open
but there is nothing to clone: `POST /v3/export` returns `400 MigrationSvc_041` "No asset selected"
because the target holds no exportable asset. Check `GET /public/core/v3/objects?limit=5`
**unfiltered** before planning a clone — a type-filtered `count: 0` is not evidence either way
(the filter is not validated), but an unfiltered near-empty org is decisive.

Zero `PUT` and zero `PATCH` are proven anywhere. Update = `POST /{id}` on the v2 plane, or
`DELETE` + re-`POST`.

## Law 7 — MCP is not the lever, and never replaces the Secure Agent

11 actions across the five vendor servers, all HTTP POST, and **exactly one writes**
(`checkout_data_order`). MCP does two things
REST cannot: asset **lineage** (`get_asset_details`) and **fuzzy identity match**
(`search_master_record`). The other 9 wrap REST, usually less capably.

On Org A `GET /public/core/v3/mcpServers` **404s** — no vendor MCP server is reachable there. MCP is
a calling convention, not a network path: only a Secure Agent can reach a private database. Editing
an MCP proxy's code cannot bypass a server-side check. Metering trap: MCP is free in preview but the
backing CDGC/CDI/Marketplace/MDM calls still bill IPUs.

**Judge a server by its action list, not by the word "MCP."** A connected *agent* server (e.g.
CLAIRE) is a different shape entirely: ~4 actions that are an **orchestration** interface, not
endpoint wrappers — one free-text prompt, routed internally. It is **asynchronous**: submit, then
poll a separate action until a `ANSWER:` / `PROBE:` / `done` / `Error:` sentinel. Most integration
bugs are loop bugs, not auth bugs → `knowledge/playbook/10-mcp.md`.

---

## Error triage — failures that look identical but are not

| You see | Cause | Do |
|---|---|---|
| `403 APP_10519` "connection type is not valid" | Wrong `type` string | Use `type: TOOLKIT_CCI`; connector goes in `instanceName` → `knowledge/playbook/02-request-bodies.md` |
| `403 APP_105060` "no running service found" | Connection is fine; **no engine** to open a session | Check `agentEngines[]` (Law 4) |
| `readyToRun: false` from `GET /api/v2/runtimeEnvironment` | **Suspect the reading first.** The LIST endpoint reports a stale false-negative — reproducible 3/3 against an agent that `GET /api/v2/agent/{id}` reports `true` | Re-read per-agent. Only then `knowledge/playbook/01-orgs-and-entitlement.md` |
| `403 APP_13401` or `500 CMN_001` under `/api/v2/agent/*` | **Router artifact — proves nothing.** Bogus twins return them identically (`/api/v2/agent/bogusZZZnope` → 403; `/api/v2/agent/bogusZZZ/{id}` → 500) | Never cite these either way (Law 2 covers error codes too). Enablement *is* UI-only, on other evidence → `knowledge/playbook/01-orgs-and-entitlement.md` |
| `No running service found of type X <ver>.* service for AgentGroup: {reId}` (on `GET /api/v2/connection/test/{id}`) | Cleanest **Layer-3** proof: engine X was never assigned to that agent | UI: Runtime Environments → agent → enable the service. No reinstall. If the named engine *changes* between tries, that is deployment progress, not a new wall |
| `403` "no connector with type=X" | Connector type never registered in the org | One UI Save in Administrator |
| `403` on MDM `GET …/entity/{be}/{id}` | The **plane** is real — **not** proof the entity exists. The same 403 fires for a nonsense entity name, because the ACL check runs **before** the metadata lookup | Bogus-twin the **entity name**, not just the path. Test existence with `POST …/entity/{be}?sourceSystem=X` and read the 404 body |
| `403` "Unable to fetch Connector attributes, Ensure adapter ID is valid and the service is enabled [com.informatica.adapter.X]" | The **adapter for X was never deployed to the agent** — enabling engines does not enable connectors | Check the agent's real registry: `<agent>/apps/Connector_Service/<ver>/connectors/cci/plugins/`. Then Administrator → Runtime Environments → agent → add connector X. **Never** infer from the 342-row `GET /api/v2/connector` — that is Informatica's global product catalog |
| `Unable to load driver` on a JDBC_V2 connection | Third-party driver not registered (a file copy into the driver dir is **not** sufficient — 4 locations tried, all failed with a proven-good jar) | Use Administrator's upload-JAR flow. Field names come from `CCIManifest.txt` in the downloaded package: **`username`**/`password`, not `user` |
| `400` on a create | **Good news** — verb exists, body incomplete | Read the named field, add it, retry (validator loop) |
| `406` | A job is already running | Positive evidence. Retry later |
| `MigrationSvc_030` "Invalid import package" | Hand-built import zip — and note this is the **route-discovery success signal**: the handler parsed your upload | Use a genuine export |
| `404 MigrationSvc_025` "Import request with identifier **[package]** doesnt exist" | **Not a dead route.** The service read your path segment as an `importId` and looked it up. This is a live handler answering a lookup | **Vary the `Content-Type`, not the path.** On `/v3/import/package`: `application/json` → this 404; `application/zip` / `octet-stream` → `415`; **`multipart/form-data` → `400 MigrationSvc_030`** = alive |
| `400 MigrationSvc_041` "No asset selected for export operation" | Your body **parsed fine** — the named object holds nothing exportable (e.g. an empty Project). A **content** verdict | Pick a different object. Do **not** sweep body shapes; contrast with `V3API_007`, which *is* a shape error (`objects[]` takes `{"id": "…"}`, never bare strings) |
| `APP_13533` | "specify a mapping id" | `mttask` only wraps an existing mapping |
| `200`, 0 bytes | Gateway artifact | Law 2 |
| `count: 0` from `objects?q=type=='X'` | Filter is **not validated** — a fake type returns the same | Never proof of capability |

## Per-service gotchas — check your service here before you design the call

Each of these is the one fact that makes the difference between a working call and a day of probing.
Full numbers and sources: `knowledge/playbook/08-answers-planes-caps-corrections.md`.

| Working on | The thing that will catch you |
|---|---|
| **CAI publish** | `POST /active-bpel/asset/v1/publish` on the **`-cai`** host, `Content-Type: application/vnd.api+json`, **199 assets max** per call. Dependency order: service-connector → app-connection → process. Items fail **inside a 200 envelope** — poll `/publish/{id}/Status` and read each `itemState`. Publish does **not** activate. |
| **CAI runtime control** | `active-bpel/restadmin` is the strongest control plane in IDMC: suspend / resume / terminate a running process, schedule CRUD, listener start/stop. Process list **defaults to 20** — page with `listStart` + `maxReturn`. |
| **CAI at volume** | **10,000 activities → 429 and no new instances for 15 min.** Counter is node-local. Batch in sub-10k windows. |
| **CDQ dictionaries** | Dedicated **`<pod>-dqcloud-api`** host. **Write-only — there is no GET at all**; get the `dictionaryId` from the UI URL. 42 columns, 10k rows per call. `finishUpload` is mandatory (**424** if skipped). A human must click **Convert to API** first, and that locks the dictionary out of UI editing. |
| **Operational Insights** | **GraphQL, not REST** — that is why REST probes find nothing. One endpoint: `GET /active-bpel/opsanalytics-das/metrics?query={...}` on the `-cai` host. 13-month history, **one active request per org**, no pagination, metrics refresh weekly. A `400` on a malformed query is **positive evidence**. |
| **MDM SaaS** | Base URL mutates twice: add **`-mdm`** to the pod label **and strip the trailing `/saas`**. Body takes `search` **XOR** `fields`, never both. 🚨 **Source-system updates go to `entity-xref`, never the golden-record `entity`** — writing source data to `entity` corrupts the golden record. A UI soft-delete removes a record from API search. |
| **MDM: mastering, headless or not** | **Split runtime from design and the question answers itself.** RUNTIME is headless — ingest (`POST …/entity/{be}?sourceSystem=X`, flat body, `trustScore` is a **STRING**), read-by-id, `entity-xref`, R360 search. DESIGN is **UI-only**: business entity, match/merge/survivorship, and **deploy** — `deploy` was swept across 6 route shapes and the model-authoring plane across 12 host+path shapes, **all 404, never once 405** ⇒ no route, not a verb limit (B360 Modeler *Publish*). So mastering is headless **only after one manual publish**. 83 MDM privileges and an `MDM Designer` role do **not** imply a deploy verb. |
| **MDM: is anything actually modeled?** | Ask before you design any call. `POST …/entity/{be}?sourceSystem=X` → `404` "The requested metadata with GUID *{be}* cannot be found during load" means **not deployed** — and it fires identically for a fabricated name, so run it against `ZZFAKEENTITY` as your control. Corroborate with unfiltered `GET /public/core/v3/objects?limit=5`. When a model *is* deployed the same POST flips **404 → 201**, which makes a clean automated gate check. |
| **P360 ≠ MDM SaaS** | **Product 360** (`onlinehelp.informatica.com/p360/…`) is a separate AWS-hosted PIM with **no REST API at all**. "Automation" there = uploading an empty **`do_deploy.txt`** marker file into an **S3** customization folder (plus `stop_server.txt` / `restart_server.txt`), workflows deploy via the **ActiveVOS console UI**, and DEV→QA→PROD promotion is a **support ticket** with a ≥4-hour window. Check for `p360`/`s360` privileges before answering a P360 question from MDM SaaS evidence. |
| **Data Profiling** | Profile + query CRUD **is documented**; we do not hold the paths. The honest answer is "documented, paths not held" — **not** "no API". |
| **Any long script** | The JW token **expires 30 minutes from grant**. From **2026-11-03** an org admin can switch REST auth to JWT, so scripts must self-re-authenticate or they break. |

## Preflight — run before any IDMC work

```bash
POST /saas/public/core/v3/login          # -> INFA-SESSION-ID; confirms org + pod
GET  /api/v2/org                         # -> which org am I really in (both ID shapes)
GET  /api/v2/agent                       # -> any agents? []  means Law 4 is unresolved
GET  /api/v2/agent/{agentId}             # -> readyToRun (per-agent = authoritative; list lies)
GET  /api/v2/agent/details/{agentId}     # -> agentEngines[] + .agentEngineStatus.status
```

Read the **per-engine `status`**, not just the engine list: `DEPLOYING` ≠ `RUNNING`, and a connection
test keeps failing until the engine it names is actually up.

**Read the verdict off it like this** — the branch matters more than the output:

| Preflight says | Verdict | Next |
|---|---|---|
| `agents: []` | Entitlement **unresolved** — not "unlicensed" | `knowledge/playbook/03-bootstrap.md` step 4: install an agent |
| Only `OpsInsightsDataCollector` | Telemetry only. **No scan, profile or mapping execution** — everything will fail `403 APP_105060` | Bootstrap **6b #1**: enable the engine (UI) |
| `Data_Integration_Server` present but `DEPLOYING` | Not ready. Tests fail with a **moving** error | Wait and re-read. A rotating error is progress — do **not** reconfigure |
| `Data_Integration_Server` `RUNNING`, connection test still fails | Engine is fine; the **adapter** or **driver** is missing | Match the error text to bootstrap 6b #2 / #3 |
| `readyToRun: false` from the **list** endpoint | Probably a stale false-negative | Re-read `GET /api/v2/agent/{id}` — the per-agent value is authoritative |

**Wrap these calls in a script you keep, not a one-off.** The pieces worth encoding once, because
each one has already caused a wrong diagnosis: the bogus-twin fake-200 filter (Law 2), the
empty-POST verb probe (Law 5), the per-agent health read rather than the list, and `TOOLKIT_CCI`
in `type` with the connector name in `instanceName`. Make writes idempotent and give it a
`--dry-run` that prints the body without sending it.

**Licensing/consumption is readable headlessly** even though every `/license` path 404s — see the
metering export in `knowledge/playbook/01-orgs-and-entitlement.md`. Dates need full ISO-8601 or you get
`400 V3API_007`.

## Where to look next

| Question | Read |
|---|---|
| **Which host / header / cap? Was a belief overturned?** | **`knowledge/playbook/08-answers-planes-caps-corrections.md` — start here** |
| **Using an MCP server** (which actions, the async poll loop, argument rules) | `knowledge/playbook/10-mcp.md` |
| **What do I actually BUILD?** mapping shapes, SCD2, expressions, taskflow, DQ rules | `knowledge/playbook/09-design-patterns.md` |
| **Deploying IDMC**: which runtime, engines, drivers, host sizing | `knowledge/playbook/08-answers-planes-caps-corrections.md` §Deploying it |
| Nothing runs / `403 APP_105060` after a UI enable | Same file, §Licence-assignment — check `agentEngineStatus.status`, not the engine list |
| Can IDMC do X at all? Which kind of cannot? | `knowledge/playbook/05-endpoints-by-service.md` (per-service state) + `knowledge/playbook/08-answers-planes-caps-corrections.md` (UI-only walls) |
| Does verb V work on path P? | `knowledge/playbook/05-endpoints-by-service.md` — every endpoint, per-verb |
| Full prose on one endpoint | `knowledge/playbook/05-endpoints-by-service.md`, then `06-lessons-field.md` for symptoms |
| Which org, which engines, why blocked | `knowledge/playbook/01-orgs-and-entitlement.md` |
| Exact request body for a connection etc. | `knowledge/playbook/02-request-bodies.md` |
| **Standing up an agent / first working connection** | **`knowledge/playbook/03-bootstrap.md` — read its "four gates" preamble BEFORE touching anything. Host → engine → adapter → driver, in that order** |
| SSH, firewall, egress, systemd, Docker traps | `knowledge/playbook/04-environment-traps.md` |
| Every endpoint by service, with state | `knowledge/playbook/05-endpoints-by-service.md` |
| Has this bitten us before? (by symptom) | `knowledge/playbook/06-lessons-field.md` |
| How old is this evidence? | `knowledge/playbook/99-provenance.md` |

## Red flags — stop and re-check

- About to say **"not entitled"** → did you read `agentEngines[]`, or just a 404? (Laws 1, 3, 4)
- About to say **"not possible"** → did you grep `_evidence/` and the verb matrix? (Law 1)
- About to quote a limitation → is that cell **UNTESTED**? 569 of 830 combinations are. Untested is
  unknown, not unsupported.
- Reusing a proven endpoint across orgs → Law 0.
- Reporting a 200 as success → Law 2.
- Reaching for MCP to do a write → Law 7.
- Concluding from `products[]` or a `count: 0` → Law 4, triage table.
