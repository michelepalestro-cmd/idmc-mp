# CAI Troubleshooting & Stuck Assets

**Answers:** In what order to triage a CAI failure; what each publish, import, invoke, connection and monitoring signature means; how to handle assets stuck with duplicate or missing runtime entries; how to prove a platform fault; which data-level failures only look like CAI faults; what needs Informatica support or a UI step.

**Read when:** when any CAI call, publish, unpublish or delete fails, or a CAI-fed value looks wrong.

**Key rules:**
- Check host, asset path and header first: most CAI 'walls' were one of those (L-CAI-003, L-CAI-040).
- Read every publish item: failures arrive inside 200 envelopes (L-CAI-002).
- A 500 with a downstream error in the body is the target refusing the write, not CAI (L-CAI-080, L-CAI-082).
- Duplicate runtime rows and missing runtime entries cannot be fixed from outside: hand them to support (L-CAI-078).
- A REVIEW decision holds a record out of the CRM by design; label it, do not force it (L-CAI-112).

**Related:** [CAI Asset Lifecycle](01-cai-asset-lifecycle-author-publish-unpublish-delete.md) · [CAI Runtime](02-cai-runtime-invoke-urls-control.md) · [CAI Connections & Connectors](03-cai-connections-connectors-e.g.-salesforce-oauth.md) · [Process Server on a Secure Agent](04-process-server-on-a-secure-agent.md) · [Lessons: CAI](../../lessons/by-domain/05-application-integration-cai.md)

**Last verified:** 2026-11-03

> **Summary.** Most CAI "walls" were a wrong host, a wrong asset path or a wrong header: check those first. Read
> every publish item, because failures arrive inside 200 envelopes. Two states cannot be fixed from outside: an asset
> with duplicate runtime catalog rows ("singleton sequence... 2 items") and an asset with no runtime entry
> (`AvrEntryNotFoundFault`). Both stay flagged published, so FRS will not delete them and their projects cannot be
> emptied; they need Informatica support or a designer attempt. This page is the signature table plus what to hand
> to support.

---

## 1. Triage order

1. **Host.** Publish, invoke, restadmin and Operational Insights live on `<pod>-cai.<domain>`, not on the pod base
   host. Derive it from the login base URL (L-CAI-040).
2. **Path.** Publish and unpublish take `Explore/<project>/<folder>/<name>.<TYPE>.xml` (L-CAI-003); invoke takes
   `/public/rt/<orgIdV3>/<name>` for anonymous processes and `/rt/...` for authenticated ones.
3. **Headers.** `application/vnd.api+json` on both Accept and Content-Type for `asset/v1`; the v3 session for
   publish; no header for anonymous invoke.
4. **Items, not envelopes.** Poll the job and read every `itemState` (L-CAI-002).
5. **Engine.** For agent-bound assets, is the Process Server actually running (L-CAI-067, L-CAI-068)?
6. **Target.** For a 500 from a process, read the body: the downstream system may be the one refusing (L-CAI-080).

---

## 2. Signature table

### 2.1 Publish and unpublish

| Signature | Cause | Fix | Lesson |
|---|---|---|---|
| Item BAD_REQUEST "Invalid asset path." | Path without `Explore/` or without `.<TYPE>.xml` | Build it from the v3 object `path` | L-CAI-003 |
| HTTP 500 ClassCastException | `data` sent as an array | Send one object | L-CAI-004 |
| HTTP 500 NotAcceptable | `Accept: application/json` | `application/vnd.api+json` | L-CAI-005 |
| HTTP 403 on `/active-bpel/asset/publish` | Legacy path without `/v1/`, or the pod host | Correct path on `<pod>-cai` | L-CAI-001 (supersedes L-CAI-097) |
| HTTP 405 on `GET.../asset/v1/publish` | The starter is POST-only | POST; GET the `/publish/<id>/Status` resource | L-CAI-002 |
| jobState WARNING | An item NOT_FOUND | Check the path of that item | L-CAI-002 |
| Item "Publish Error" with no detail | An input declared as a field element | Declare inputs as parameters | L-CAI-022 |
| Item ERROR "... must be unpublished first. Dependent entry(ies):..." | Unpublishing something another asset depends on | Unpublish processes, then connections, then connectors | L-CAI-007 |
| Designer says "unexpected error when publishing"; assets stuck "Validation in progress.." | Designer first-publish regression (cpfPublish 500 on first publish, 200 on republish) | Publish over `asset/v1/publish`; send the asymmetry evidence to support | L-CAI-013 |
| Publish of agent-bound assets fails while the engine is down | Process Server not running | Repair the engine first | L-CAI-081 |
| "singleton sequence... 2 items" on publish and on unpublish | Duplicate runtime catalog rows | Section 3 | L-CAI-078 |
| `AvrEntryNotFoundFault` | No runtime entry for the asset | Section 3 | L-CAI-078 |

### 2.2 Authoring and import

| Signature | Cause | Fix | Lesson |
|---|---|---|---|
| 405 on `POST /public/core/v3/objects` | The catalog is read-only | Author through an import package | L-CAI-025 |
| 500 on `POST /active-bpel/asset/v1/processes` (and `/import`, `/deploy`, `/save`) | Not an authoring route | Import package | L-CAI-025 |
| `MigrationSvc_034` on export | Exported by the GUID inside the process XML | Use the IDMC object id from v3 objects | L-CAI-019 |
| `MigrationSvc_031` "Internal error" on a TOOL_CONNECTION | MCP tool connections do not import | Recreate in the designer on a private-preview org; newer orgs have no such type, so use your own agent through an MCP gateway | L-CAI-027, L-MCP-081 |
| Import-based rename of a published process hangs | Renames by import are unreliable | Recreate under the new name, switch callers, retire the old | L-CAI-012 |
| An authored process "disappeared" | It sits in the project of the user who owned the clone source, or the audit used a wrong type name | Query by exact type and id without a folder filter | L-CAI-028 |
| Deployed logic contains odd bytes; regexes misbehave | A shell heredoc mangled backslashes | Write with a file tool; `grep -P '\x08'` | L-CAI-024 |
| `MigrationSvc_031` 'Correct the errors in the Select Assets section', empty details, on a hand-built CAI package | A process references connections or connectors that are not in the package | Add the dependency closure; limit the import with `includeObjects` | L-CAI-136 |
| 'Internal application provider error' on a PROCESS import, nothing more in the log | The process calls a shared connection or connector that is not in the package | Put that connector's XML in the package and leave it out of `includeObjects` (its live secrets stay) | L-CAI-156 |
| Publish SUCCESS, yet every invoke answers 'No plan found for service' | The name's first imports had failed; it stayed unroutable | Import the same XML under a new name; use throwaway names while fixing a package | L-CAI-157 |
| Publish ERROR 'Link definition error: /process/flow/links/link[...]' | A Decision whose branches all end still has an outgoing link | Remove the link (the 'ActiveVOS specific extension function used' list is noise) | L-CAI-135 |
| 'String "PT...S" is not a valid xsd:duration' at run time | A Wait period built with `<arg source="field">` or `source="formula"` is taken literally | `<duration source="formula">` with `concat('PT', ..., 'S')` | L-CAI-134 |
| Assets read 'out-of-date' after a connection or connector republish | Dependent processes are flagged; the runtime already uses the new connection | Republish the processes last | L-CAI-133 |

### 2.3 Invoke

| Signature | Cause | Fix | Lesson |
|---|---|---|---|
| 404 from the runtime | Not published, renamed, wrong tenant (org id) or pod in the URL | `GET /active-bpel/rt`; check the base URL | L-CAI-037, L-CAI-039 |
| 401/403 on `/rt/` for an anonymous process | Wrong path for the access mode | Use `/public/rt/<orgIdV3>/...` | L-CAI-031 |
| 403 "User not authorized" | Caller not in Allowed Users/Groups | Fix the list and republish; org roles do not help | L-CAI-033 |
| 400 "extra" | Unknown input field | Match `/schema/input` | L-CAI-035 |
| 400 on a provider webhook | Nested, signed payload versus a flat schema | Bridge or provider-shaped process | L-CAI-035 |
| Missing output keys | Empty-string outputs are omitted | Treat missing as `''` | L-CAI-036 |
| Old behaviour right after a publish | The runtime serves the previous version for ~20 s | Retry verification | L-CAI-011 |
| 429 "exceeded the activity execution limit" | 10,000-activity limit; blocked for 15 min | Wait or republish; fix the loop; pace traffic | L-CAI-050 |
| 429 without that message | Rate window | Back off | L-CAI-051 |
| 500 with a downstream error in the body | The target refused (invalid key, storage limit, duplicate rule) | Fix the target side | L-CAI-080, L-CAI-064 |
| 500 on one of two simultaneous calls for one record | Double-call race | One caller per record per event | L-CAI-079 |
| 500 on an unauthenticated GET of an anonymous process | The endpoint is live and open; the 500 is not an auth answer | Require authentication or front it with a gateway | L-CAI-038 |
| '500 after 4 attempts' in bursts on an upsert process | The CRM is rejecting inserts (storage full); retries only repeat | Free storage; group failures by downstream error before blaming the runtime | L-CAI-082, L-CAI-080 |
| Optional output keys missing for some records | Empty outputs are omitted | Read optional outputs with a default | L-CAI-036, L-CAI-114 |
| 500 from an orchestration process | It points at deleted task ids | Update the ids it uses | L-CAI-092 |
| Cloud Server process cannot reach a service | The service is on a private network | Run on an agent with a network path | L-CAI-057 |
| A fixed value is overwritten minutes later | A batch task writes the same field | Change every writer | L-CAI-085 |

### 2.4 Connections, runtime control and monitoring

| Signature | Cause | Fix | Lesson |
|---|---|---|---|
| `invalid_client_id` on a token call | Wrong consumer key in the connection | Fix, re-import, republish | L-CAI-062 |
| 'Invalid User' setting a client-credentials Run As user; `app_blocked` on a token call | A new Connected App cannot take a Run As user; a blocked old app after rotation | External Client App; repoint the connection | L-CONN-063 |
| "Foreign key external ID not found" | Parent record missing | Retry; or resend without the link, then re-link | L-CAI-063 |
| 403 on `/active-bpel/services/restadmin/...` | Wrong prefix | `/active-bpel/restadmin/...` | L-CAI-043 |
| 401 on the scheduler while other restadmin calls work | Role gap | Grant the role | L-CAI-048 |
| `{"process":[]}` from `restadmin/processes` | No retained instances (it lists runs, not definitions) | `GET /active-bpel/rt` for deployed services | L-CAI-043 |
| 404 on `/public/core/v3/operationalInsights` | Wrong plane | GraphQL on `/active-bpel/opsanalytics-das/metrics` with `IDS-SESSION-ID` | L-CAI-049, L-CAI-159 |
| 400 from the OI endpoint | Malformed GraphQL (the endpoint parsed it) | Fix the query | L-CAI-049 |
| 401 'Unauthorized' from the OI endpoint with `Authorization: Bearer <session>` | The export takes the session as `IDS-SESSION-ID` (the documented Bearer form was refused, 2026-11-01) | Send `IDS-SESSION-ID` | L-CAI-159 |
| `INSUFFICIENT_ACCESS_ON_CROSS_REFERENCE_ENTITY` creating a Salesforce `ContentDistribution` | Refused for an API-only integration user | Move the bytes through the process (SOAP retrieve, attachment, PUT) | L-CAI-158 |
| CAI runs missing from the activity log | They never appear there | Record your own evidence | L-CAI-041 |
| `/process-engine/status` 404 on the agent | Empty webapp (context deleted) or engine never deployed | [Process Server repair](04-process-server-on-a-secure-agent.md) | L-CAI-070 |
| 7443 not listening | Keystore missing | Copy `ae.keystore` and `ae.cacerts` | L-CAI-070 |
| Engine logs "PostgreSQL database has started" but restarts forever | Another Postgres answers on 5432 | Move the engine's database port | L-CAI-069 |
| Kafka connection publish SUCCESS, callers get 'No consumers available on endpoint: direct://<conn>_<eventTarget>' | A producer route failed to start (catalina 'Failed to start route'; for an idempotent producer 'Must set retries to non-zero') | Set `retries` with `enableIdempotence`; read catalina after every connection publish | L-CAI-125 |
| HTTP 500 'NullPointerException: Cannot read the array length ...' on `restadmin/eventconnection/start` or `/stop` | Sent with `INFA-SESSION-ID` | Send `IDS-SESSION-ID` | L-CAI-122 |
| JMS properties with hyphens or dots missing from AMQP event headers | Qpid JMS drops names that are not Java identifiers | Query Parameters `jms.validatePropertyNames=false` | L-CAI-123 |
| Kafka records processed twice after a listener stop or a connection republish | The listener resumed from the last offset auto-commit | Idempotent targets; `autoCommitIntervalMs=1000` | L-CAI-121 |
| A slow REST target is waited for far beyond the intended timeout | `requestTimeout` is in seconds | Set it in seconds | L-CAI-128 |

---

## 3. Stuck assets: duplicate runtime rows and missing runtime entries (L-CAI-078)

**What you see.** Publish and unpublish of one asset both fault with "singleton sequence... 2 items" (the runtime
holds two catalog rows for it), or with `AvrEntryNotFoundFault` (the runtime has no entry for it). The asset stays
flagged published or out of date, so `DeleteEntities` returns `FRS_082` for it and `FRS_087` for its project.

**What to try before escalating (in order).**
1. Re-read the asset path from the v3 catalog and retry the unpublish once with the exact path.
2. Check whether a dependent asset is still published (unpublish that first).
3. Try Unpublish from the designer's Explore page (a UI attempt is cheap and sometimes clears the state).
4. Leave the asset, and its project, on a documented "stuck" list; do not force deletes around it.

**What to send Informatica support.**
- Org id (v3), pod, the asset's v3 object id and Explore path, asset type.
- The exact fault text from the unpublish job's `itemStatusDetail`, with job ids and UTC times.
- The FRS delete result (`FRS_082`) and the fact that the asset is not referenced by live assets.
- For the designer regression (L-CAI-013): the client build stamp, and the same-session asymmetry evidence
  (re-publish 200 versus first publish 500 on identical calls).

**Observed scale.** A cleanup removed 81 of 83 legacy CAI objects after unpublishing 59; the 2 that remained were one
asset with duplicate runtime rows (plus its connection) and one with no runtime entry (2026-09-28).

---

## 4. Proving a platform fault (L-CAI-014)

Make the identical call with the same session and endpoint on a case that should work and on the failing case. A
deterministic split, plus the vendor UI failing the same way, shows the fault is server-side. Nothing on the client
side (headed browser, flags, reloads) fixed the designer regression; the REST route bypassed it.

---

## 5. Data-level failures that look like CAI faults

| Symptom | Real cause | Lesson |
|---|---|---|
| Sync-status view shows errors for records that exist | Two callers raced; the loser returned 500 | L-CAI-079 |
| A name rule "stops working" | A batch mapping re-writes the field minutes later | L-CAI-085 |
| Names come out wrong-cased or split badly | Naive title-casing and first/last split | L-CAI-086 |
| CAI returns 500 for hours | The target org is out of storage | L-CAI-080 |
| New CRM records silently missing | A CRM duplicate rule | L-CAI-064 |
| A person is in the golden table but not in the CRM | The onboarding decision returned REVIEW, and the batch sync sends DQ-valid rows only | L-CAI-112 |
| Child upserts fail with 'Foreign key external ID not found' in bursts | Children relayed before their parent landed | L-CAI-063, L-CAI-038 |
| A published average latency looks too low or too high | Failures and timeouts inside the average, or final-attempt-only timing | L-CAI-038, L-CAI-082 |

---

## 6. What needs Informatica support or a UI step

| Item | Why | Lesson |
|---|---|---|
| Duplicate runtime catalog rows; missing runtime entry | No external verb clears them | L-CAI-078 |
| Designer first-publish regression | Server-side build issue (publish over REST meanwhile) | L-CAI-013 |
| API activation after a deactivation | Console APIs page only | L-CAI-010 |
| MCP tool connections in a new org | Import fails; recreate in the designer only if the org was in the AI Agent Engineering private preview, otherwise the type does not exist | L-CAI-027, L-MCP-081 |
| File listeners, human tasks | Designer-only constructs (Kafka and AMQP event sources, listener processes and fault handling author by package: [CAI Event Listeners](06-cai-event-listeners-kafka-amqp-jms.md)) | L-CAI-025, L-CAI-116 |
| Shell Service enablement on an agent | One-time UI step; it lets processes run OS commands on that agent, so use a dedicated agent | L-CAI-053 |
| Managed APIs and policies in API Manager | No REST in July 2026; re-probe | L-CAI-094 |
