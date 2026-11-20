# Application Integration (CAI) processes: cheat sheet

Author, publish, invoke, change and remove CAI processes, app connections and service connectors headless, including
Salesforce OAuth, the Process Server on a Secure Agent and Kafka / AMQP listeners.

**Start with:** `toolkit/lib/idmc_cai_publish.py` (`plan`, `publish`, `unpublish`, `status`) and
`toolkit/lib/idmc_export_import.py` (authoring is by package); open
[01 CAI Asset Lifecycle](01-cai-asset-lifecycle-author-publish-unpublish-delete.md) first.

> Writes are dry runs until `--execute --expect-org <orgIdV3>`. Export packages can carry connection secrets in
> plaintext: store them as secrets (L-CAI-060).

## What works (headless)

| Task | How (exact route / tool / command) | Lesson |
|---|---|---|
| Author a process, connection or connector | a v3 import package: clone with dependencies, change in place (OVERWRITE), or build from scratch | L-CAI-016, L-CAI-018, L-CAI-020 |
| Resolve an asset path | `GET /public/core/v3/objects?q=type=='<TYPE>'`, match the name → `Explore/<project>/<folder>/<name>.<TYPE>.xml` | L-CAI-003 |
| Publish | `POST https://<pod>-cai.<domain>.informaticacloud.com/active-bpel/asset/v1/publish`, `INFA-SESSION-ID`, Accept and Content-Type `application/vnd.api+json`, `data` an object → 202 `data.id`; tool `publish` | L-CAI-001 |
| Check the result | `GET .../asset/v1/publish/<id>/Status`, read every `itemDetail[].itemState` | L-CAI-002 |
| Unpublish | `POST .../asset/v1/unpublish`, processes → connections → connectors; tool `unpublish` | L-CAI-007 |
| Delete | after the unpublish: FRS `POST /frs/v1/DeleteEntities` (`IDS-SESSION-ID`); `FRS_070` on read-back = gone | L-CAI-008 |
| Set a secret encrypted | author `encrypted="true"` with an empty value, import, `PUT .../asset/v1/update?assetType=AppConnection`, republish | L-CAI-132 |
| Invoke anonymously | `POST /active-bpel/public/rt/<orgIdV3>/<ProcessApiName>` on the `-cai` host, inputs as strings | L-CAI-030, L-CAI-035 |
| Invoke authenticated | `/active-bpel/rt/<ProcessApiName>`; the caller must be on the process's access list | L-CAI-031, L-CAI-033 |
| Discover contracts | `GET /active-bpel/rt` (deployed services); `.../rt/<orgIdV3>/<Process>/schema/input` | L-CAI-032 |
| Run history | GraphQL `GET /active-bpel/opsanalytics-das/metrics?query={...}` with `IDS-SESSION-ID` | L-CAI-159 |
| Salesforce writes | own REST service connector: client-credentials token action + external-id `PATCH` upsert | L-CAI-058 |
| Process Server on an agent | runtime-environment selections PUT, then `https://localhost:7443/process-engine/status` = 200, body `2` | L-CAI-066, L-CAI-068 |
| Kafka / AMQP listeners | author in the package, publish; start/stop with `restadmin/eventconnection` and `IDS-SESSION-ID` | L-CAI-116, L-CAI-122 |
| Orchestrate CDI from a process | the process calls `POST /api/v2/job` and polls the activity log | L-CAI-092, L-CAI-153 |

## What doesn't work, and the workaround

| Wall | Workaround | Lesson |
|---|---|---|
| `POST /public/core/v3/objects` (405); `asset/v1/processes`, `/import`, `/deploy`, `/save` author nothing | v3 import package | L-CAI-025 |
| Re-activating an API that was deactivated in the console | console APIs page only; a republish does not reactivate it | L-CAI-010 |
| Asset with duplicate runtime rows ("singleton sequence ... 2 items") or no runtime entry (`AvrEntryNotFoundFault`) | Informatica support or a designer attempt; keep it on a stuck list, do not force deletes | L-CAI-078 |
| File listeners, human tasks | designer only | L-CAI-025 |
| MCP tool connections (`MigrationSvc_031` on import) | recreate in the designer (private-preview orgs only) | L-CAI-027 |
| Managed APIs and policies in API Manager (July 2026) | no REST; re-probe | L-CAI-094 |
| Built-in Salesforce connector (needs ModifyMetadata) | REST service connector + client credentials | L-CAI-058 |
| restadmin scheduler for an agent-run process (stays `enabled: false`) | a system timer on the agent host posting to the local `/process-engine/public/rt/<process>` | L-CAI-142 |
| CAI runs in the Data Integration activity log | never there: record your own evidence | L-CAI-041, L-CAI-053 |
| Rename a published process by import | recreate under the new name, switch callers, retire the old | L-CAI-012 |

## Fastest safe path

1. **Prove the org** and derive the `-cai` host by inserting `-cai` after the pod label of the login base URL (L-CAI-040).
2. **Decide where it runs:** Cloud Server for public APIs; a Secure Agent for private networks, listeners or local
   keys (L-CAI-056, L-CAI-057). Agent: read-back `process-engine/status` 200, body `2` ("enabled" is not "running";
   L-CAI-067).
3. **Export a working asset** by its IDMC object id (not the GUID inside the XML) with dependencies; keep the zip as
   the undo (L-CAI-019, L-CAI-016).
4. **Edit and import:** change only what you mean (one hit per anchor), re-hash changed files, import OVERWRITE; the
   package carries every connection and connector its processes call. Read-back: import SUCCESSFUL (L-CAI-018, L-CAI-136).
5. **Publish in order** connectors → connections → processes: `idmc_cai_publish.py plan`, then `publish`. Read-back:
   every `itemState` SUCCESS (L-CAI-006, L-CAI-002).
6. **Verify** with side-effect-free calls, one valid and one invalid payload, retrying for about 2 minutes: the
   runtime can serve the old version for about 20 s. On failure, re-import the saved zip and republish (L-CAI-011, L-CAI-018).
7. **Set access deliberately:** no access configuration = no service URL; anonymous URLs answer anyone (L-CAI-034, L-CAI-038).
8. **Call it fail-open** from apps (about 6 s timeout, no retry inline) and record one row per call (L-CAI-082).

## Top traps

- **Item BAD_REQUEST "Invalid asset path."** → path lacks `Explore/` or `.<TYPE>.xml` → build it from the v3 `path` (L-CAI-003).
- **HTTP 500 ClassCastException** → `data` sent as an array (L-CAI-004); **500 NotAcceptable** → `Accept: application/json` (L-CAI-005).
- **A 202/200 is not success** → items fail inside the envelope → poll and read every item (L-CAI-002).
- **Item "Publish Error" with no detail** → a process input declared as a field → declare it as a parameter (L-CAI-022).
- **`MigrationSvc_034` on export** → exported by the GUID inside the XML → use the v3 object id (L-CAI-019).
- **`MigrationSvc_031` 'Correct the errors in the Select Assets section'** → missing dependencies in a hand-built
  package → add the closure, limit with `includeObjects` (L-CAI-136, L-CAI-156).
- **'No plan found for service' after a SUCCESS publish** → the name's first imports failed → fix packages under
  throwaway names, import the final name once (L-CAI-157).
- **Unpublish item ERROR "... must be unpublished first"** → wrong order (L-CAI-007); **`FRS_082` on delete** → still
  published (L-CAI-008).
- **403 "User not authorized"** → the process's access list, not an org role (L-CAI-033); 401/403 on `/rt/` for an
  anonymous process → use `/public/rt/` (L-CAI-031).
- **Missing output keys / blanked CRM fields** → empty outputs are omitted; a PATCH with an empty field sets it empty →
  read with defaults, omit absent fields (L-CAI-036, L-CAI-114).
- **429 "exceeded the activity execution limit"** → 10,000 activities; no new instance for 15 minutes (L-CAI-050).
  **500 with a downstream error in the body** → the target refused (e.g. `STORAGE_LIMIT_EXCEEDED`), not CAI (L-CAI-080).
- **Process Server restart-loops** → its embedded PostgreSQL is hard-wired to 5432 → move the port, guard it after
  every upgrade (L-CAI-069, L-CAI-072). **Kafka:** an idempotent producer needs `retries` or its route fails while the
  publish says SUCCESS (L-CAI-125); a listener stop resumes from the last auto-commit → idempotent targets (L-CAI-121).

## Go deeper

- [01 CAI Asset Lifecycle](01-cai-asset-lifecycle-author-publish-unpublish-delete.md): author (clone, in place, from scratch), publish, unpublish, delete, checklists.
- [02 CAI Runtime: Invoke, URLs & Control](02-cai-runtime-invoke-urls-control.md): URL map, contracts, status codes, restadmin, limits, evidence, caller patterns.
- [03 CAI Connections & Connectors](03-cai-connections-connectors-salesforce-oauth.md): where calls run, REST connectors, secrets, Salesforce OAuth, upserts.
- [04 Process Server on a Secure Agent](04-process-server-on-a-secure-agent.md): enable, health checks, failure anatomy, repair, upgrades.
- [05 CAI Troubleshooting & Stuck Assets](05-cai-troubleshooting-stuck-assets.md): triage order, full signature table, what needs support.
- [06 CAI Event Listeners: Kafka & AMQP](06-cai-event-listeners-kafka-amqp-jms.md): listener connections and processes, start/stop, delivery semantics, throughput.
- [Lessons: CAI](lessons.md)
