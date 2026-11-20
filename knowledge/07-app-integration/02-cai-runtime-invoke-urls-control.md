# CAI Runtime: Invoke, URLs & Control

**Answers:** Which URL invokes a published process (anonymous or authenticated); the request and response contract; what each status code means; how to control runs over `restadmin`; the limits; where run evidence lives; how applications should call CAI; which integration edges belong on an API layer and which on IDMC; how to front CAI with an API gateway.

**Read when:** before calling a process from an application, a relay or a gateway; when an invoke answers 4xx/5xx; when deciding whether an integration edge belongs in CAI, CDI/CDC or an API platform.

**Key rules:**
- Anonymous endpoints answer anyone with the URL (an unauthenticated GET gets 500, not 401): require authentication or front them with a gateway for anything that writes (L-CAI-038).
- Call CAI inline fail-open with a ~6 s timeout and no retry; retry only the background parent push on 5xx/transport errors (L-CAI-082).
- Empty outputs are left out of the response: read optional outputs with a default (L-CAI-036, L-CAI-114).
- CAI runs are not in the activity log and are not jobs: record your own evidence (L-CAI-041, L-CAI-038).
- The API layer runs the application's real-time calls; IDMC (CDC, CDI, CAI) owns everything that feeds or serves analytics (L-CAI-088).
- Report latency averages over successful calls only (§10.1; L-CAI-038).

**Related:** [CAI Asset Lifecycle](01-cai-asset-lifecycle-author-publish-unpublish-delete.md) · [CAI Connections & Connectors](03-cai-connections-connectors-salesforce-oauth.md) · [CAI Troubleshooting](05-cai-troubleshooting-stuck-assets.md) · [Serving Outputs to BI and Apps](../04-mappings/09-serving-outputs-to-bi-and-apps-freshness-latency-reverse-etl.md) · [Lessons: CAI](lessons.md)

**Last verified:** 2026-11-03

> **Summary.** Published processes answer on the `<pod>-cai` host: anonymously at
> `/active-bpel/public/rt/<orgIdV3>/<process>` (no auth header; runs as the system user `CAI_Anonymous_<orgIdV3>`),
> or authenticated at `/active-bpel/rt/...` (gated by the process's own access list). Runtime control is
> `active-bpel/restadmin` (instances, suspend/resume/terminate, a scheduler, URN mappings, listeners) and job history
> is the Operational Insights GraphQL export. The traps: a 10,000-activity limit that blocks a process for 15
> minutes, outputs that vanish when empty, URLs that embed the pod and org id, and a double-call race that makes one
> of two simultaneous upserts fail with 500.

---

## 1. URL map

All paths are on `https://<pod>-cai.<domain>.informaticacloud.com` unless noted. `<orgIdV3>` is the 22-character
org id, which the vendor calls `{TenantName}` in anonymous URLs.

| Purpose | Path | State |
|---|---|---|
| Invoke, anonymous | `/active-bpel/public/rt/<orgIdV3>/<ProcessApiName>` (GET or POST) | proven 2026-07-08 to 2026-09-28 |
| Invoke, authenticated | `/active-bpel/rt/<ProcessApiName>` (vendor form); `/active-bpel/rt/<orgIdV3>/<ProcessApiName>` answered in the field | proven 2026-07-06/07 |
| List deployed services | `GET /active-bpel/rt` | proven (54-68 services listed) |
| Input contract | `GET /active-bpel/rt/<orgIdV3>/<Process>/schema/input` | proven 2026-07-06 |
| Swagger / WSDL | append `?swagger` to an rt URL, `?wsdl` to a SOAP URL | documented |
| SOAP | `/active-bpel/soap/<Process>`; anonymous `/active-bpel/public/soap/<Tenant>/<Process>` | documented |
| Message event | `/active-bpel/public/rt/<Tenant>/<Process>/event/<MessageName>`; authenticated `/active-bpel/rt/<Process>/event/<MessageName>` | documented |
| Runtime control | `/active-bpel/restadmin/...` (section 6) | partly proven |
| Operational Insights | `GET /active-bpel/opsanalytics-das/metrics?query={...}` with `IDS-SESSION-ID` (section 8) | proven 2026-11-01 (200 with `IDS-SESSION-ID`; the documented Bearer header gets 401) |
| On a Secure Agent | `http(s)://<agentHost>:<port>/process-engine/rt/<service>`, `/process-engine/public/rt/<service>` (add `?swagger` for its Swagger 2.0), `/process-engine/restadmin/...` | anonymous invoke and `?swagger` proven 2026-10-09 (L-CAI-143); see [Process Server](04-process-server-on-a-secure-agent.md) |

A process gets no service URL at all unless it has listed users or groups, or anonymous access (L-CAI-034).

---

## 2. Anonymous invoke (L-CAI-030, L-CAI-038)

```
POST https://<pod>-cai.<domain>.informaticacloud.com/active-bpel/public/rt/<orgIdV3>/<ProcessApiName>
Content-Type: application/json
Accept: application/json

{"order_id":"123","amount":"42.50","status":"paid"}
```

- The process must be deployed with anonymous access (the designer's Allow anonymous access option).
- It runs as the org's system user `CAI_Anonymous_<orgIdV3>`. Deleting that user during a user cleanup breaks every
  public endpoint of the org, so keep it on every KEEP list.
- Anyone who has the URL can call it, and the URLs are predictable (`<orgIdV3>` plus the process name). An
  unauthenticated GET from the internet answered HTTP 500, not 401, which still proves the endpoint is live
  (L-CAI-038). Anonymous access suits demos and side-effect-free decisions; for production writes use listed
  users or groups, API Gateway OAuth, or an API gateway in front (§10.8).
- Smoke-test each process with one valid and one invalid payload. Measured: about 270-730 ms per inline decision on
  the Cloud Server.

## 3. Authenticated invoke (L-CAI-031, L-CAI-033)

- **How to authenticate.** The Design guide documents two ways: HTTP Basic authentication with an IDMC user, or the
  v3 login session id sent in the `IDS-SESSION-ID` header. A field client that worked sent the v3 session in
  `INFA-SESSION-ID`, cached it, and retried once on 401/403 after a fresh login.
- **Who may call.** Only users in the process's Allowed Users or Allowed Groups who also hold the Run privilege.
  A 403 "User not authorized" means the caller is not on that list; broad org roles (admin, migration) do not help.
  Change the list in the designer (or with the untested `asset/v1/update`) and republish.
- **Wrong path for the access mode.** A process deployed for anonymous access answers 401/403 on `/rt/`; call it on
  `/public/rt/`. Client code should support both modes (for example a flag that skips the session header).
- **API Gateway mode.** A process set to accept only API Gateway authorization needs an OAuth2 token from an API
  Manager client; this mode is available only for processes that run on the Cloud Server.

## 4. Request and response contract

| Rule | Detail | Lesson |
|---|---|---|
| Send inputs as strings | Field callers stringified every value; numbers are parsed inside the process | L-CAI-035 |
| Unknown fields are rejected | 400 "extra" | L-CAI-035 |
| No inputs | Send `{}` | L-CAI-035 |
| Provider webhooks | A flat input schema rejects a nested, signed webhook payload with 400: author for the provider's shape (and verify its signature) or run a bridge that pulls, flattens and invokes | L-CAI-035 |
| Empty outputs vanish | An output whose value is `''` is left out of the JSON: read every optional output with a default (`resp.get('field', '')`), and add new outputs without assuming old callers will see them | L-CAI-036, L-CAI-114 |
| Old version after a publish | For about 20 s after a publish the runtime can answer with the previous version | L-CAI-011 |
| Base URL is configuration | The URL embeds pod and org id: read it from the environment in every caller | L-CAI-039 |
| Host is derived | Insert `-cai` after the pod label of the login base URL | L-CAI-040 |

## 5. Reading status codes (L-CAI-037)

| Code | Meaning | Next step |
|---|---|---|
| 200 | The process ran | Check the outputs (missing keys = empty strings) |
| 400 | Input contract mismatch ("extra", wrong shape) | Read `/schema/input` |
| 401 / 403 | Wrong path for the access mode, or the caller is not on the access list | Anonymous processes on `/public/rt/`; fix the list |
| 404 | No published process of that name for that tenant: unpublished, renamed, wrong org id, wrong pod | Check `GET /active-bpel/rt`, the org id and the publish state |
| 429 | Rate window exceeded, or the process is blocked by the 10,000-activity limit | Section 7 |
| 500 with a downstream error in the body | The process ran and the external system refused (a test key, a storage limit, a race) | Read the body; see [CAI Troubleshooting](05-cai-troubleshooting-stuck-assets.md) |

A smoke test should assert **reachability**, not business success: a 500 from the downstream API and a 403 from the
access list both prove the process is deployed and reachable, and an orchestration process that returns 200 with a
job id proves the outbound call works.

---

## 6. Runtime control: `active-bpel/restadmin`

The vendor Monitor guide documents 18 restadmin endpoints; each has a Secure Agent twin under
`http(s)://<agentHost>:<port>/process-engine/restadmin/...` (tenant `$public` on the agent). Headers: the scheduler
GET was proven with `INFA-SESSION-ID`; the guide documents `IDS-SESSION-ID` for the process APIs and a Bearer session
id for URN mappings. If one header is refused, try the documented one before concluding anything.

### 6.1 Process instances (L-CAI-043)

`GET https://<pod>-cai.<domain>.informaticacloud.com/active-bpel/restadmin/processes` returned 200
`{"process":[...]}`; the `/active-bpel/services/restadmin` variant returned 403. These are process **instances**
(runs), not definitions, so an empty list does not mean nothing is deployed (use `GET /active-bpel/rt` for that).
Documented filters:

| Parameter | Values |
|---|---|
| `processState` | SUSPENDED, COMPLETED, RUNNING, COMPENSATABLE, FAULTED |
| `processName`, `processNameNamespace`, `processGroup` | API name, namespace, group (for example `RT.User`) |
| `hideSystem`, `hidePublicTenant` | true or false |
| `processId` | one run (`?processId=<runId>`) |
| `listStart`, `maxReturn` | paging; the default page size is 20 |
| `advancedQuery` | for example `getProcessProperty('Version')=3.0` |

Completed instances stay 24 h and faulted ones 72 h by default, so the list is a short window, not a history.

### 6.2 Suspend, resume, terminate (L-CAI-044, documented)

`PUT.../active-bpel/restadmin/processes/<processId>/suspend` (also `/resume`, `/terminate`) returns 204 per the
Monitor guide. Not exercised live. An older note said "retry as POST on 405 because no PUT is proven in IDMC"; that
premise is outdated, so try the documented PUT first. The Job Management MCP server stops CDI jobs, not CAI instances.

### 6.3 Scheduler (L-CAI-045)

| Verb | Path | Body | Result |
|---|---|---|---|
| GET | `.../restadmin/scheduler/schedules/?tenantContextId=<orgIdV3>` (add `&name=<n>` for one) | none | 200 `{"schedulerInitialized":true,"scheduledItems":...}` (proven 2026-07-09) |
| POST | `.../restadmin/scheduler/schedules` | see below | 204 (documented) |
| PUT | same | the item with its `scheduleId` | 204 (documented) |
| DELETE | same | `{"scheduleId":[<id>,...]}` | 204; one invalid id and nothing is deleted (documented) |

```json
{"tenantContextId":"<orgIdV3>","name":"<schedule name>","ipdService":true,"once":null,
 "intraday":{"executeEvery":{"value":30,"interval":"MINUTES"},"onlyBetween":null},
 "daily":null,"weekly":null,"monthly":null,"runOptions":"SKIP",
 "serviceName":"<process API name>","inputDocument":null}
```

`ipdService: true` is for Process Designer processes; BPEL services use `false` plus a SOAP `inputDocument`. A process
Start binding offers only REST/SOAP and Event, but scheduling is a separate layer that works on a REST-bound process.
The scheduler only fires the process: record run evidence inside the process or from the caller. On one pod
the scheduler returned 401 while processes and URN mappings returned JSON, which is a role gap, not a missing plane
(L-CAI-048).

**Processes that run on a Secure Agent (L-CAI-142).** A schedule created for a process published to an agent answered
204 but stayed `enabled: false` with `planId: -1` and never ran; the agent's own `/process-engine/restadmin/scheduler`
answered 401 or 403. Start such timer processes from the agent host instead: a system timer that posts to
`http://localhost:7080/process-engine/public/rt/<process>` every minute, with a lock per process as 'skip if running'.

**Contract answers (L-CAI-144).** A REST-started process answers 400 or 503 with all its output fields through a
Milestone step with `<httpStatus>`, so a caller gets the reasons of a rejection in the body and retries only a 503.

### 6.4 URN mappings and listeners (L-CAI-046, L-CAI-122)

- `GET.../active-bpel/restadmin/urn/<orgIdV3>` reads all URN mappings (proven); `PUT.../restadmin/urn/` adds or
  updates one and `DELETE` removes one or more (documented).
- Listener-based event sources: `POST.../active-bpel/local/restadmin/eventconnection/stop` and `/start` with
  `?agentName=<agent>` and the `IDS-SESSION-ID` header (proven 2026-10-08; `INFA-SESSION-ID` answers 500
  NullPointerException). Route paths, bodies and the windowed-subscriber pattern: [CAI Event Listeners](06-cai-event-listeners-kafka-amqp-jms.md) §4 (L-CAI-122).

---

## 7. Limits

| Limit | Behaviour | State |
|---|---|---|
| Activity execution limit (default 10,000 BPEL activities per execution) | Invocations return 429 ("The last execution of this process has exceeded the activity execution limit...") and no new instance is created for 15 minutes, or until the process is republished | documented; tech preview (L-CAI-050) |
| Rate window | REST/SOAP calls return 429 when the window's limit is exceeded | documented (L-CAI-051) |
| Payload and attachments on the Cloud Server | 5,242,880 bytes (5 MB) | documented |
| Non-persistent process runtime | terminated after 3,600 s | documented |
| Retention (automated maintenance) | completed 24 h, faulted 72 h, logs 30 days | documented |
| Kafka producer request size (Camel `maxRequestSize`) | 1 MB by default; raise it to the broker's limit for large messages (a 4.1 MB message ran after the change) | proven 2026-10-08 (L-CAI-127) |

About the activity limit: it counts BPEL activities, not designer steps (count the "Executing [" lines in the process
log); the cache is node-local, so on a multi-node agent group one node can reject while another runs; a process at
the limit is suspended when its persistence is Full or Persist (resuming resets the count) and terminated when it is
None, Brief or Final. Keep loops bounded, pace high-volume traffic below the limit, and give heavy CAI work its own
agent node if other processes must not be blocked.

---

## 8. Operational Insights export: GraphQL, not REST (L-CAI-049, L-CAI-159)

```
GET https://<pod>-cai.<domain>.informaticacloud.com/active-bpel/opsanalytics-das/metrics?query={processJobReport(start:"2026-09-01T00:00:00Z",end:"2026-09-28T00:00:00Z"){time processName endpoint env originContext status executionCount executionTime averageExecutionTime}}
IDS-SESSION-ID: <session id>
Content-Type: application/json
Accept: text/csv            (omit for JSON)
```

| Resource | Parameters | Range |
|---|---|---|
| `processJobReport` | `start`, `end` (`YYYY-MM-DDTHH:mm:ssZ`, required), `env` (default `allEnvironments`), `status` (Completed or Faulted) | up to 13 months |
| `processRunsByNameEnv` | `start`, `end` (`YYYY-MM-DD`), `env`, `status` (SUCCESS, FAILED, RUNNING, STOPPED) | up to one month |

**Send the session as `IDS-SESSION-ID`** (L-CAI-159, 2026-11-01). The guide sends the session id as a Bearer token in
`Authorization`; that header answered 401 'Unauthorized' on the same query that returned 200 with `IDS-SESSION-ID`
(237 daily rows for one month in `data.processJobReport[]`, one row per day, process, environment and status; `env` is
`<agentId>_<agentName>` for an agent or `_Cloud_` for the cloud runtime). The earlier record (L-CAI-049, now disputed
on the header) had only a 400 on a malformed query. One active request per org, no pagination, UTC timestamps; the
full schema is in Informatica KB article 000259754. `/public/core/v3/operationalInsights` is 404: wrong plane.

---

## 9. Where run evidence lives

| Source | Covers | Lesson |
|---|---|---|
| The invocation response | Every call you make; the only complete record for most setups | L-CAI-053 |
| Your own decisions table | One row per call written by the caller (section 10) | L-CAI-082 |
| restadmin process instances | A short window (24 h completed, 72 h faulted) | L-CAI-043 |
| Operational Insights export | Aggregates and job rows, up to 13 months (send `IDS-SESSION-ID`) | L-CAI-049, L-CAI-159 |
| The engine's embedded PostgreSQL on an agent | Agent-deployed processes only (database `activevos`, tables such as `aeprocess`, `aeplan`) | L-CAI-052 |
| Data Integration activity log | Never: CAI runs do not appear there, and they do not count against the monthly job cap (a job budget did not move around a test burst) | L-CAI-041, L-CAI-038 |

For agent-bound processes a "Run a Shell Command" step can write evidence on the agent after a one-time UI
enablement of the Shell Service on that agent (L-CAI-053). **Careful:** the Shell Service lets any process published to
that agent run operating-system commands as the agent user; enable it only on a dedicated agent and prefer a service step
that posts to your own endpoint.

---

## 10. Caller patterns

### 10.1 Inline calls from an application (L-CAI-082)

- Short timeout (about 6 s), every input as a string, and **fail open**: a CAI outage must never block a sign-up or a
  payment; record it as `ok=false`.
- One row per call: process, subject, decision, ok, latency_ms, error, request, response. Let the batch pipeline land
  that table so decisions show up in analytics.
- A health endpoint that makes one side-effect-free call.
- **Retry only the background parent push** (L-CAI-082). Run the push that creates the parent SaaS record (for
  example the CRM contact that later child upserts reference by external id) in a background thread and retry only
  transient failures there (HTTP 5xx, timeouts, connection resets) after 2 s, 5 s and 10 s, persisting the final
  outcome with the attempt count. A missing parent makes every later child upsert fail with 'Foreign key external ID
  not found' (L-CAI-063), so the parent is the one call worth retrying; child upserts get no retry.

  | Call | Timeout | Retry | Persist |
  |---|---|---|---|
  | Inline decision in a user flow | ~6 s | none (fail open) | one row; `ok=false` on failure |
  | Background parent push | ~6 s per attempt | 5xx and transport errors only: 2 s, 5 s, 10 s | final outcome + attempts |
  | Child upserts | ~6 s | none; fix the parent first | one row |

- **Measure honestly.** With retries, the stored latency is the last attempt's round trip, not the user's wait: measure
  end to end separately. Report averages over successful calls only: 27 failures ('500 after 4 attempts' while the CRM
  was full) pulled one average from about 1,130 ms to about 810 ms. Before reading a daily 500 rate as runtime
  flakiness, group failures by the downstream error in the response body: a full target (`STORAGE_LIMIT_EXCEEDED`,
  L-CAI-080) or a same-second double call (L-CAI-079) is not fixed by retries (L-CAI-038, L-CAI-082).
- **Measured on the Cloud Server** (L-CAI-082, L-CAI-038):

  | Process | Average | p50 / fastest |
  |---|---|---|
  | inline decision (cleanse + validate + ACTIVATE/REVIEW) | 77-114 ms | p50 266 ms on a busier day; fastest 41 ms |
  | CRM contact upsert (round trip) | 1.37-1.43 s | p50 975 ms, p95 1.9 s; fastest 0.59 s |
  | application insert → CRM record | 1.9 s | fastest 1.46 s |

### 10.2 Near-real-time SaaS upserts (L-CAI-083)

A database trigger builds the payload in the process's input shape and fires `pg_notify`; a thin relay LISTENs and
posts each event to the matching CAI upsert process. Retry after 3, 6 and 12 s on retryable answers (parent not
landed yet, DUPLICATE_VALUE, UNABLE_TO_LOCK_ROW, REQUEST_LIMIT, 5xx), skip events beyond a burst limit (for example
200 per 300 s) and let the scheduled batch reconcile them. Keep the business rule in the trigger and the SaaS logic
in CAI. Measured: database write to CRM record in 1.35 s. A relay for child records produced 1,085 events in one
period: 514 ok, 243 'Foreign key external ID not found' (child before its parent) and 328 dropped by the burst guard;
the batch sync repaired the gaps, so keep it scheduled (L-CAI-038). A bulk fix on a table with such a trigger
fans out into one CAI call per row: silence triggers for hygiene fixes ([CDC from PostgreSQL](../06-cdc-ingestion/02-cdc-from-postgresql.md) §7).

For BI, a live view of the SaaS data is the batch read-back UNION the successful CAI upserts newer than the read-back's
watermark, deduplicated on the record id; the read-back alone shows every new record as missing (L-CAI-113;
[Serving Outputs to BI and Apps](../04-mappings/09-serving-outputs-to-bi-and-apps-freshness-latency-reverse-etl.md) §5).

### 10.3 The double-call race (L-CAI-079)

When two callers (an application and a trigger relay) invoke the same upsert for the same record within the same
second, one wins and the other gets HTTP 500, although the record is written. Make exactly one caller responsible per
record per event, or serialize and dedupe, and let status views keep the latest SUCCESS per record rather than the
latest attempt.

### 10.4 One rule, every writer (L-CAI-085)

A SaaS field can be written by a CAI cleanse, a CAI upsert and a batch mapping task a few minutes later. Change the
rule in all writers together and verify after the next batch run, or the batch silently undoes the real-time fix.

### 10.5 Moving callers to another org (L-CAI-039, L-CAI-087)

Publish and verify in the target first, then switch each caller's base-URL environment variable and recreate only
the consuming services (a 10-30 s blip), make one real call, and keep the old value as the rollback.

### 10.6 Other process patterns

- Long-running work: accept, dispatch, suspend, resume on a callback message event, with a timer for the timeout
  (L-CAI-054).
- Orchestration: a process can call `POST /api/v2/job` to start a mapping task and return its run id; keep the task
  ids current (L-CAI-092).
- Copy, then parse: a process can start a File Ingestion task (`POST https://<pod>.<domain>.informaticacloud.com/mftsaas/api/v1/job`),
  poll `GET .../mftsaas/api/v1/job/<runId>/status` in a Wait + Jump loop (8 s, at most 30 polls) and start the
  mapping's taskflow only on SUCCESS; a task started this way has no used-by link, so never archive it as unused
  ([DBMI over REST](../06-cdc-ingestion/01-dbmi-over-rest-create-deploy-run-stop.md) §9; L-DBMI-061).
- Real-time latency to a SaaS record: about 0.2-2 s, versus minutes for batch lanes (L-CAI-084).

### 10.7 Which layer owns which edge: the integration-layer split (L-CAI-088)

When an API-led platform (for example MuleSoft) and IDMC run side by side, split the estate by purpose:

- **The API layer runs the application.** The APIs behind every app action (web, mobile, point-of-sale and staff
  tools) into the operational database, application logic such as payment ledger legs, operational writes to
  downstream systems, and the application's own real-time record sync into the CRM.
- **IDMC owns everything that feeds or serves analytics.** Native connectors with CDC (DBMI) and CDI bring source data
  into the warehouse (raw to gold, DQ, golden records, catalog lineage) and never pass through an app API where a
  native connector exists; CDI keeps the batch golden sync to the CRM; CAI carries the analytical integrations that are
  API- or event-shaped (usage or app events into the warehouse, golden-record activation back into the apps by calling
  the app's own API, replacing custom warehouse loaders).
- **A real-time DQ check stays an Informatica service.** Cleanse + validate + decision built on IDMC DQ rules runs as a
  CAI process that the API layer calls, so the rules exist once and are not re-coded in the app.

| Edge | Owner | Mechanism |
|---|---|---|
| App action → operational database | API layer | gateway + app API |
| App → CRM record in real time | API layer | an API-layer integration (CAI until it moves) |
| Real-time DQ check on a sign-up | IDMC | CAI process using IDMC DQ rules, called by the API layer (fail open, §10.1) |
| Source systems → warehouse | IDMC | native connector + CDC (DBMI) / CDI |
| Warehouse → CRM batch golden sync | IDMC | CDI native connector |
| API-usage or app events → warehouse | IDMC | CAI process |
| Golden data → application database | one writer (the API layer's activation API) | never also by JDBC from a mapping |
| BI or analytics data through the API layer | never | it bypasses lineage, governance and DQ |

Rules: no Informatica hop goes through the API gateway; never make an application's critical path wait on a batch job;
golden data flows back into the app database through one writer only. Audit an existing build for crossings: CAI
processes in the app's request path, clients that bypass the gateway, gateway logs written straight to the warehouse
instead of through IDMC, two writers of golden data into the app, and custom loaders that belong to neither. Record the
decision per edge, move edges one at a time with the old path as rollback, and confirm the API platform has runtime
capacity before moving a flow (an expired trial with 0 production capacity blocked one move). What the split does
**not** buy: jobs. CAI calls are not jobs, so moving work between CAI and the API layer saves none; consolidating CDI
tasks does ([Mapping Design & Consolidation](../04-mappings/05-mapping-design-consolidation.md) B5;
L-CAI-038).

### 10.8 Fronting CAI and other APIs with an API gateway (Anypoint API Manager, headless) (L-ENV-089, L-ENV-090)

Use this to put a governed front door on APIs that sit next to IDMC: CAI processes, activation services, system APIs.
Auth: a connected app using client credentials with the scopes View Organization/Environment, API Manager Manage API
Configuration and Manage Policies, and Exchange Contributor; pass its secret inline only, never write it to a file.

| Step | Call | Trap |
|---|---|---|
| Spec | `POST /exchange/api/v2/assets` as `multipart/form-data` with a real OAS file part (classifier `oas`) | metadata-only gives 400 'Could not determine asset type'; convert OpenAPI 3.1 specs down to 3.0 |
| Instance | `POST /apimanager/api/v1/organizations/<anypoint-org>/environments/<env>/apis` with `{technology:'flexGateway', endpoint:{deploymentType:'HY', isCloudHub:null, type:'rest', uri:'<backend-url>', proxyUri:'http://0.0.0.0:8081/<path>'}, spec:{groupId, assetId, version}, instanceLabel}` | `isCloudHub` must be present and `null`; `isCloudHub:false` and `muleVersion4OrAbove` are rejected |
| Upstream and route | `POST.../apis/<id>/upstreams`, then PATCH the routing | a unique proxy path per instance (`/<resource>s` collided with `/<resource>`) |
| Deploy | `PATCH /apimanager/xapi/v1/organizations/<anypoint-org>/environments/<env>/apis/<id>` with `{"deployment":{"targetId":"<flex-target-id>","type":"HY","gatewayVersion":"<ver>",...}}` | there is no `POST.../deployments` (404); the same PATCH on the `/apimanager/api/v1` base answers 200 and does nothing |
| Verify | GET the instance after every write | healthy = `status:'active'` plus a populated `deployment`; `endpointUri:null` is cosmetic |

Only HTTP surfaces can be enrolled: database wire protocols, workers without an HTTP port and the gateway itself
cannot. Gateways in Local Mode (configuration from files) still need a Local Mode `registration.yaml` in `conf.d`
(without one they bind no listener); copying a Connected Mode registration makes the gateway pull another environment's
APIs. A Local Mode route `/<prefix>(/.*)` to a Service upstream with `destinationPath: ""` strips the prefix. The
`rate-limiting-flex` policy works in Local Mode (429 with `x-ratelimit-limit`/`x-ratelimit-remaining`); a useful pair is
an external, rate-limited, firewall-scoped gateway and an internal loopback gateway without a throttle for
service-to-service calls. The vendor console shows Local Mode APIs as inactive (L-ENV-068). Before promising client-id
governance on a gateway, call each route without credentials and expect 401.

---

## 11. Overturned beliefs (this area)

| Belief | Believed | Overturned by |
|---|---|---|
| CAI has never run; `/active-bpel/rt` 404 means publish and run are UI-only | to 2026-07-07 | L-CAI-042 (L-CAI-110) |
| A CAI process cannot be scheduled natively | 2026-07-09 | L-CAI-045 (L-CAI-104) |
| Operational Insights has no API plane | to 2026-07-25 | L-CAI-049 (L-CAI-105) |
| The Operational Insights export takes the documented `Authorization: Bearer <session>` | 2026-07-25 to 2026-11-01 | L-CAI-159 (L-CAI-049, disputed): `IDS-SESSION-ID` |
| restadmin exists only on dm-us pods | to 2026-07-25 | L-CAI-048 (L-CAI-106) |
| No PUT is proven in IDMC, so restadmin PUTs should be retried as POST | 2026-07-25 to 09-28 | L-CAI-044 (L-CAI-111) |
