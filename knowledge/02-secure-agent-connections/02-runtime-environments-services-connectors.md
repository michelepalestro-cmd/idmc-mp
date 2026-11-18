# Runtime environments: services and connectors

**Answers:** Which kind of runtime environment should run a task? What is really deployed on an agent? How do I select
services and connectors headless, what does each selection pull in, and what does every change cost?

**Read when:** before you enable a service or connector, when an engine is missing or DEPLOYING, when a CLAIRE data
query or a new licence does not show up on the agent.

**Key rules:**
- Read what is deployed from `GET /api/v2/agent/details/<agentId>` (`agentEngines[]`), never from the runtime-environment
  list or the login `products[]` (L-AGENT-020, L-AGENT-021, L-AGENT-048).
- Change selections with `GET` then `PUT.../runtime/api/v2/runtimeEnvironment/<reId>/selections/ui` and header
  `IDS-SESSION-ID`; save the GET body as the undo and read back (L-AGENT-039).
- Every PUT downloads packages and rolls DIS, Mass Ingestion and Connector_Service: change selections between lanes,
  never before a timed run (L-AGENT-041, L-AGENT-042).
- What a selection downloads stays in `downloads/`, which services run from: never prune it (L-AGENT-094).
- The Data Gateway behind CLAIRE GPT "Query the data" is a licence package, not a selection; it needs its agent running
  (L-AGENT-097, L-AGENT-051).
- A Hosted Agent outage is failed over by rebinding the tasks **and** their connections, lookups included, to a Secure
  Agent, with full-body backups for the undo (L-AGENT-117, L-CONN-132, L-ENV-100).

**Related:** [01 Secure Agent](01-secure-agent-install-run-tune.md) ·
[05 Troubleshooting - the Four Gates](05-troubleshooting-the-four-gates.md) ·
[Entitlement, Licenses & Job Caps](../11-ipu-metering-licensing/03-entitlement-licenses-job-caps.md) ·
[Managed MCP Servers](../09-claire-mcp/01-managed-mcp-servers-catalog-access.md) (the `secureagentmanagement` server) ·
[Lessons: Secure Agent & Connections](../../lessons/by-domain/02-secure-agent-connections.md)

**Last verified:** 2026-11-03 (evidence 2026-06-27 to 2026-11-03; selections GET/PUT proven 2026-09-28 and used for
several on/off cycles; a Hosted Agent failover 2026-11-03).

> A runtime environment (RE) decides where work runs and which services and connectors its agents run. The selections
> GET/PUT pair was the first proven PUT in IDMC. Select only what the scope needs and never select everything on a small
> host.

---

## 1. Three kinds of runtime environment

A runtime environment is a network position, not a setting: whatever runs a task must be able to reach the data
(L-AGENT-036, 2026-07-26).

| Type | Runs where | Use it when | Cannot |
|---|---|---|---|
| Informatica Cloud Hosted Agent | Inside Informatica; nothing to install | Source and target are SaaS and the connector supports hosted execution | Reach a private network. A connection bound to it creates with 200 and then cannot see a private host. Its name is reserved: it cannot be created in an org that lacks it (REPO_38210, L-CONN-024). It cannot run CDQ cleanse, deduplicate or decision steps (EP_13236; rule specifications do run, L-CDI-279), its REST V3 adapter was not deployed (L-CONN-131), and its `SESSSTARTTIME` is US Eastern local time, not UTC (L-AGENT-115) |
| Secure Agent group | A host you own | Data is on a private network or on-premises. The only option that reaches a private database | Save you from patching, disk, RAM and uptime |
| Serverless | Informatica-managed compute inside your own AWS or Azure account (your VPC/VNet, subnets, IAM role) | Data already sits in that cloud account and you want no agent | Reach other clouds or data centres; it bills IPUs per runtime-hour; creation is UI-only (`/public/core/v3/serverlessRuntimeEnvironments` and `/api/v2/serverlessRuntimeEnvironment` both 404) |

**Routes** (L-AGENT-035, 2026-07-26): `GET <serverUrl>/api/v2/runtimeEnvironment` lists REs with nested `agents[]`;
`POST <serverUrl>/api/v2/runtimeEnvironment` creates one (an empty body answers 400, so the verb exists). An agent
creates its own RE when it registers. Prefer the v2 forms: `GET /public/core/v3/runtimeEnvironments` returned 200 on one
pod and 404 on another, and the singular v3 path answered 415.

**Sub-orgs** (L-AGENT-038, 2026-07-26): a sub-org can inherit all of its REs from the parent; they show zero agents
until an agent is installed in the sub-org. Do not bind a sub-org connection to the parent's shared RE: the test error
changes from APP_105060 to `error [error [null]]`, which is identical for a bogus host, so nothing was attempted.

**When the Hosted Agent is down** (L-AGENT-117, L-CONN-132, L-ENV-100, 2026-11-03). The signature: every connection
bound to the hosted runtime fails its test with 403 APP_105060 naming the hosted agent group, hosted runs end FAILED
2-3 s after they start with 'no active Secure Agent in group Informatica Cloud Hosted Agent', and connections on your
Secure Agents still pass. Nothing restarts it from your side (one outage lasted more than 14 hours with no status
notice), so open a support case early and fail over:

1. Inventory: `GET /api/v2/mttask` and keep the tasks whose `runtimeEnvironmentId` is the hosted runtime; list the
   connections they use, lookups included, and the connections per runtime from `GET /api/v2/connection`.
2. Rebind each task: `GET /api/v2/mttask/<id>`, save the full body as the undo, drop createTime, updateTime,
   createdBy, updatedBy, lastRunTime and agentId, set `runtimeEnvironmentId` to the Secure Agent's runtime,
   `POST /api/v2/mttask/<id>` and read it back (17 tasks moved in seconds; ids, schedules and taskflows unchanged).
3. Rebind the connections too: a lookup resolves its connection through the connection's own runtime environment,
   so a task already on a healthy agent still failed at its lookup. Set `runtimeEnvironmentId` and
   `connParams.agentGroupId`, re-supply every masked secret, `POST /api/v2/connection/<id>`, then test it
   ([doc 03](03-connections-create-test-update-delete.md) §4).
4. Leave on the hosted runtime what the agent cannot serve (a CRM user that trusts only listed egress IPs, a connector
   not selected on the agent, work too big for it) and accept those tasks as down; unblock any chain that stops at
   their failure ([Taskflows & Schedules](../03-cdi-data-integration/04-taskflows-schedules.md)).
5. Re-run the failed tasks, check the outputs, and undo from the saved bodies when the hosted runtime is healthy.
   Expect CPU-bound mappings to run slower on a small agent (2-2.5x on 2 vCPU, L-AGENT-118), and read the error text
   of anything still failing: a warehouse quota can fail tasks too (L-CONN-133).

## 2. Reading what is deployed

**The truth is per agent.** `GET <serverUrl>/api/v2/agent/details/<agentId>` (header `icSessionId`) returns
`agentEngines[]`, each with `agentEngineStatus.appname`, `displayName`, `status`, `desiredStatus`, `subState` and the
engine version. `GET /api/v2/agent/<agentId>` gives `active`, `readyToRun`, the agent core `version`,
`upgradeStatus`, `lastUpgradeCheck` and `packages[]` (L-AGENT-020, 2026-07-26).

**Per-agent versus list `readyToRun`.** The list (`GET /api/v2/runtimeEnvironment`, `agents[].readyToRun`) reported
false for agents the per-agent read reported true, 3 times of 3, while the host said READY (L-AGENT-021, 2026-07-26).
The two flags sync separately. Mapping runs ignore both; only creating a new CDGC catalog source validated the RE view
and failed with 500 'Error while validating Runtime Environment detail [<reId>] under global config option [Execution]'
(L-AGENT-022, 2026-07-04).

**Four states, never merged** (L-AGENT-023, 2026-07-26):

| State | How you read it | Failure looks like |
|---|---|---|
| Licensed | Administrator > Licenses, its CSV export, `EffectiveLicenses` `active[]` | Absent licence. Not a REST 404: licence paths 404 even when licensed |
| Selected (assigned) | `enabled: true` in the RE selections | Engine missing from `agentEngines[]`; a connection test names it: 'No running service found of type <Engine> <ver>.*' |
| Deploying | `agentEngineStatus.status = DEPLOYING` | Calls fail meanwhile, and the engine named in the error changes as each one lands |
| Running and resolvable | Only a passing connection test or job | The API can say RUNNING while the agent log says UNKNOWN and the router still refuses |

**How long DEPLOYING lasts** (L-AGENT-024, 2026-09-28): 45+ minutes for a large set on a small host; about 18 minutes for
a trimmed set (PUT at 22:10Z, engines RUNNING at 22:28Z). The agent pulls packages itself; no restart or reinstall is
needed (L-AGENT-025, 2026-07-26). A single `500 CMN_001` on one package URL retries itself (L-AGENT-027, 2026-07-26).

### 2.1 What each engine is for

| `appname` in `agentEngines[]` | Serves | Selected through | Notes |
|---|---|---|---|
| `Data_Integration_Server` | CDI mapping tasks, taskflows, DQ assets (DQ runs inside DIS), on-agent address verification, profiling DTMs | Data Integration (Data Quality adds DQ libraries) | Version 77.x rolls on selection changes (L-AGENT-042, L-AGENT-049); address verification has no engine of its own (L-AGENT-116) |
| `Connector_Service` | Connection tests, metadata, connector adapters | Data Integration | 21.x; caches its driver classpath (L-CONN-049) |
| `Common_Integration_Components`, `OpsInsightsDataCollector` | Platform plumbing, telemetry | Platform (mandatory) | An agent showing only the telemetry engine has nothing selected (L-AGENT-032) |
| `Database_Ingestion`, `MassIngestionRuntime` | Database Ingestion and Replication, CDC | Mass Ingestion-Databases | BigQuery targets need the Simba jars (L-CONN-045) |
| `process-engine` ('Process Server') | CAI processes on the agent (private hosts) | Application Integration | +1.8-2 GB RAM, fragile on shared hosts; one per host, because its web ports are static (L-AGENT-053, L-AGENT-070, L-AGENT-090) |
| `Metadata_Foundation_Agent`, `Metadata_Platform_Service` | On-agent catalog scans (CDGC) | Data Governance and Catalog; Metadata Platform Service | Heavy; switch on for scan windows only (L-AGENT-043) |
| `Data_Access_Management_Agent`, `_Proxy` | Data Access Management policies | Data Access Management Agent / Proxy | Restart-loop (exit 133 about 3.5 min after each start) when the org has no Data Access Management setup; exclude them from monitors (L-AGENT-046, L-AGENT-091) |
| `Streaming_Ingestion_Agent` | Streaming ingestion | Mass Ingestion-Streaming | |
| `FileIntegrationService` | File ingestion | Mass Ingestion-Files (probably) | Seen in engine lists; the mapping to the selection is inferred. File Ingestion tasks ran once Mass Ingestion-Files and the source connector were selected (L-DBMI-060) |
| `B2BProcessor`, `CIHProcessor` | B2B Gateway, Cloud Integration Hub | B2B Gateway, Integration Hub | CIH binds a static API port 19443: move it on a second agent of the same host (L-AGENT-090) |
| `DataServiceApiMgmt` | API management | (not recorded) | |
| `At_Scale_Server` | Elastic / at-scale processing (probably) | Data Integration - Elastic (probably) | Untick when not needed (L-AGENT-047). Its Elastic Server must be RUNNING before a Local (on-agent) advanced configuration validates (L-AGENT-114) |
| `AIAgentRuntime` | AI Agent Runtime | (not recorded) | Needs `unzip`, `libffi6`, `libreadline7`, `libtinfo5` on Ubuntu 22.04 (L-AGENT-062) |

A deployed engine proves the capability is provisioned; the login `products[]` list does not (L-AGENT-048,
2026-09-21). There is no MDM engine on any agent: MDM runs in the pod (L-AGENT-050, 2026-07-06). CLAIRE GPT 'Query the
data' executes through a Secure Agent's data gateway in the org, so keep that agent up for demos (L-AGENT-051,
2026-09-29). The Data Gateway is not in this service list at all: it is a separate Platform licence package
(`IDMCDataGatewayService`) that deploys to the agent only when the org holds it, so ticking services, or copying another
org's service list, cannot bring it (L-AGENT-097, 2026-09-30). Also read 'received new AppSpec' log lines as inventory, not
enablement: a service deploys only when it is selected (`LCM_10001 Deploying app`, a new `apps/` folder; L-AGENT-098).

When the agent that hosts the Data Gateway is down, a "Query the data" prompt answers "I couldn't execute the data query
because the underlying data service connection is currently unavailable... ensure the data gateway service is
running"; glossary, lineage and search prompts still work. After a start, `IDMC_Data_Gateway_Service` was RUNNING about
7 minutes later and the same prompt answered in 96 s. If the unit reads `failed` because a graceful stop outran its
timeout, run `systemctl reset-failed <unit>` before `systemctl start <unit>` (L-AGENT-051). A licence that
reaches the org shows up as a new engine in every agent's `agentEngines[]` within about 10 minutes, so watch the engine
list rather than the licence record's `updateTime`, which changes on its own (L-IPU-057).

## 3. Change what runs: the selections route

**Proven 2026-09-28** (L-AGENT-039, 2026-09-28): the call behind the Administrator 'Enable or Disable Services' dialog, and the
same job the managed MCP tool `secureagentmanagement.update_runtime_environment_selections` does.

```
GET  https://<pod>.<domain>.informaticacloud.com/runtime/api/v2/runtimeEnvironment/<reId>/selections/ui
PUT  https://<pod>.<domain>.informaticacloud.com/runtime/api/v2/runtimeEnvironment/<reId>/selections/ui
Headers: IDS-SESSION-ID: <v2 icSessionId>    Accept: application/json    (plus Content-Type: application/json on the PUT)
PUT body: the GET body, unchanged except the "enabled" flags you mean to change
Success: 200; read the selections back; engines move to DEPLOYING, then RUNNING
Wrong header: INFA-SESSION-ID -> the identity-service login HTML page (wrong auth plane, not a result)
```

**Body shape** (the host is the pod API host; the ids inside are catalog ids, keep them as returned):

```json
{
  "services":           {"id": "...", "name": "Services",            "selections": [ SELECTION,... ]},
  "connectors":         {"id": "...", "name": "Connectors",          "selections": [ SELECTION,... ]},
  "additionalServices": {"id": "...", "name": "Additional Services", "selections": [ SELECTION,... ]}
}
SELECTION = {"id": "...", "name": "Data Quality", "internalName": "Data Quality",
             "mandatory": false, "enabled": true, "visible": true,
             "productDependencies": [...], "connectorDependencies": [...]}
```

One org's body held 17 services, 218 connectors and 3 additional services (L-AGENT-040, 2026-09-28).

**Procedure**

1. `GET` the selections and save the body to a timestamped file: it is your undo.
2. Edit only the `enabled` flags (services by `name`, connectors by `name`). Never flip `mandatory` entries.
3. Check free disk and RAM first (section 5).
4. `PUT` the whole body back; expect 200.
5. `GET` again and compare the flags you changed (a 200 whose value reverts is a silent rejection).
6. Poll `GET /api/v2/agent/details/<agentId>` until the new engines are RUNNING (tens of minutes).
7. Prove it with a connection test on that RE (`GET /api/v2/connection/test/<connId>`) or a small job.
8. Undo = PUT the saved body.

```python
# generic sketch; session and host come from your org-aware helper
import json, time, urllib.request
URL = f"https://{pod_host}/runtime/api/v2/runtimeEnvironment/{re_id}/selections/ui"
H = {"IDS-SESSION-ID": v2_session, "Accept": "application/json", "Content-Type": "application/json"}
def call(method, body=None):
    req = urllib.request.Request(URL, data=json.dumps(body).encode if body else None, headers=H, method=method)
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.status, json.loads(r.read or b"{}")
st, sel = call("GET")
json.dump(sel, open(f"selections.BEFORE_{int(time.time)}.json", "w"))
want = {"Data Integration": True, "Mass Ingestion-Databases": True, "Data Quality": True}
for s in sel["services"]["selections"]:
    if s["name"] in want and not s["mandatory"]:
        s["enabled"] = want[s["name"]]
for c in sel["connectors"]["selections"]:
    if c["name"] in ("PostgreSQL", "Google BigQuery V2"):
        c["enabled"] = True
st, _ = call("PUT", sel)
st2, back = call("GET")          # verify the flags, then poll agentEngines[]
```

**What does not work** (still true as negative facts, L-AGENT-044, 2026-07-26): `POST /api/v2/agent/service` (router
artifacts 403 APP_13401 / 500 CMN_001), `/api/v2/agent/selectiveservices` (500), `POST /api/v2/agent/<agentId>` with
`agentEngines[].desiredStatus` (500 or a redirect, reads back `agentEngines: []`), and anything under
`/public/core/v3/runtimeEnvironments`. Those error codes prove nothing either way (L-AGENT-031, 2026-07-26).

**UI equivalent**: Administrator > Runtime Environments > (RE) > Actions > Enable or Disable Services. The receipt recorded
for the components dialog in July read 'Changes successful. The selected components are enabled for the runtime
environment, and all unselected components are disabled for the runtime environment.'

## 4. Dependencies: what else a selection switches on

Each selection lists `productDependencies` and `connectorDependencies`; enabling it enables them (L-AGENT-040,
2026-09-28). Services seen on one pod:

| Service (selection `name`) | Pulls in | Engines it brings (seen together; the per-service mapping is inferred) |
|---|---|---|
| Platform | (mandatory, invisible) | Common_Integration_Components, OpsInsightsDataCollector, Administrator |
| Data Integration | none | Data_Integration_Server, Connector_Service |
| Data Integration - Elastic | Data Integration; ADLS Gen2, Google Cloud Storage V2, Amazon S3 v2, Hadoop Files V2 connectors | (elastic engines) |
| Application Integration | none | process-engine |
| Mass Ingestion-Databases | Data Integration | Database_Ingestion, MassIngestionRuntime |
| Mass Ingestion-Files | Data Integration | (needed with the source connector for File Ingestion tasks, L-DBMI-060) |
| Mass Ingestion-Streaming | Data Integration | Streaming_Ingestion_Agent |
| Integration Hub | Data Integration | |
| B2B Gateway (internal name B2B) | Data Integration; AS2, Advanced FTP/SFTP/FTPS V2, B2B EDI Gateway connectors | |
| Data Quality | Data Integration; Amazon S3 v2, Google Cloud Storage V2, ADLS Gen2 connectors | DQ libraries inside DIS |
| Data Masking | Data Integration; JDBC_IC connector | |
| Data Governance and Catalog | Data Integration, Data Quality; Amazon Redshift v2, JDBCV2, Snowflake Data Cloud connectors | Metadata_Foundation_Agent |
| Metadata Platform Service | none | Metadata_Platform_Service |
| Industry Solutions, Python Integration | Data Integration | |
| Data Access Management Agent / Proxy | none | Data_Access_Management_Agent / _Proxy |
| Additional services: Self-hosted Git Repo, EDC Integration, Secret Manager | | |

So a "DQ only" change also enables three storage connectors, and a catalog scan window also enables Redshift, JDBCV2
and Snowflake connectors. Account for their downloads.

## 5. What happens on every PUT

1. **Packages download.** Each newly selected service or connector downloads its package into
   `<agent_home>/downloads`; one all-services selection pulled about 18 GB in about 8 minutes (L-AGENT-041, 2026-09-28).
   Those packages stay: installed services run from them, so a later deselection frees no disk there (L-AGENT-094).
2. **Engines roll to the newest build.** Any PUT, even one that only deselects, upgrades Data_Integration_Server,
   MassIngestionRuntime and Connector_Service (seen: DIS 77.0.4 -> 77.0.5 -> 77.0.6 over three changes). Jobs submitted
   meanwhile queue for about 5 minutes; a running CDC job was unaffected (L-AGENT-042, 2026-09-29).
3. **Side effects of a rollover**: hand-placed JDBC jars in old version directories are left behind (stage them in
   `ext/deploy_to_main` too, L-CONN-050, 2026-08-20); host edits of `pmrdtm.cfg` / `tomcat.cfg` live in version
   directories and stay behind, so set engine properties cloud-side
   ([doc 01](01-secure-agent-install-run-tune.md) §6.1) (L-AGENT-056, L-AGENT-088).
4. **Timing**: engines reach RUNNING tens of minutes later (L-AGENT-024, 2026-09-28).

Rules: batch selection changes; make them between lanes, never right before a timed run or a demo; check free disk
first; re-test one connection per engine afterwards.

## 6. Choosing a selection

| Scope | Select | Leave off |
|---|---|---|
| CDI batch pipelines | Platform, Data Integration (+ the connectors you use) | Everything else |
| CDI + CDC | + Mass Ingestion-Databases | |
| CDI + DQ assets | + Data Quality (brings three storage connectors) | |
| Governance scans | + Data Governance and Catalog, Metadata Platform Service, only for the scan window | Afterwards: deselect them (L-AGENT-043) |
| CAI to private hosts | + Application Integration, on a host without a local Postgres on 5432 or with the embedded port moved (L-AGENT-089) | On a second agent sharing a host while the first agent's Process Server runs: only one Process Server per host (L-AGENT-016, L-AGENT-090) |
| File Ingestion (land cloud-storage files on the agent) | + Mass Ingestion-Files and the source connector (L-DBMI-060) | Runs on that agent while the PUT rolls its engines |
| Advanced-mode (Spark) mappings and Spark-only connector formats on the agent | + Data Integration - Elastic, then a Local advanced configuration: validate with `POST https://<pod>-ias.<domain>.informaticacloud.com/clustermanager/api/v1/clusterconfig/validation` (`clusterConfig` with `cloud_type` LOCAL and `file:///` staging and log locations, plus `rteId`), save with `POST https://<pod>.<domain>.informaticacloud.com/frs/api/v1/Spaces('SYS')/Documents` (documentType `ATS_CLUSTER`, the configuration in `nativeData.documentBlob`); capture the Administrator form's Validate and Save once for your release's keys (L-AGENT-114). The documented minimum for a local advanced cluster is 8 vCPU, 32 GB and a 100 GB root disk (L-CDI-277) | The older `/cis/api/v1/*` paths (CMN_001) |

- Small sets that ran cleanly: CDI plus catalog on 8 services; governance-only on DIS, Connector_Service
  and the two Metadata engines (load 65 -> 14 after trimming) (L-AGENT-047, 2026-07-26).
- Never select everything on a small or shared host: all ~17 services and 26 connectors drove load to ~189 on 4 vCPU,
  filled swap and knocked an application container over (L-AGENT-041, 2026-09-28). Selecting another org's whole
  service list on a small shared host deployed about nine extra services within minutes (L-AGENT-098). After trimming,
  leave `downloads/` alone: pruning it put 14 of 20 services into ERROR (L-AGENT-094).
- Deselect unconfigured services that crash-loop, typically Data Access Management Agent and Proxy logging 'missing
  privitar.jdbcproxy.userWithConnectionPrivileges' or hanging at 'Initializing TMS and CMS configuration services'; the
  loop does not block DI but the agent reports 'Not All Services Running', and vendor-hosted agents of such an org loop
  the same way (L-AGENT-046, L-AGENT-091).

## 7. Connectors on a runtime environment

- The per-RE truth is `connectors.selections[]` with `enabled` flags plus the adapter registry on the agent
  (`<agent_home>/apps/Connector_Service/<ver>/connectors/cci/plugins/`), not `GET /api/v2/connector`, which is a type
  catalog (153, 342 or 352 types on different orgs) (L-CONN-021, 2026-07-26).
- A connector must be selected on the RE of the agent that runs the task; every connector a mapping uses must be on that
  one agent (L-CONN-022, 2026-07-08).
- Copying adapter jars into plugin folders does not enable a connector; selection triggers a control-plane push and the
  agent downloads and deploys the package itself (L-CONN-020, 2026-09-22).
- A brand-new add-on connector type may still need one UI-created connection before REST can create connections of that
  type (proven July 2026, not re-tested since selections became headless) (L-CONN-005, 2026-07-08).
- Connector state goes stale: after an agent was re-provisioned, four connections that had failed with APP_105060 all
  tested green; an agent restart alone did not bring back a connector disabled at the control plane (L-AGENT-045,
  2026-09-23).
- An enabled selection is not proof the adapter is deployed: on the Hosted Agent the REST V3 adapter answered an
  APP_105060 adapter message although its selection read enabled; on a Secure Agent, HubSpot, REST V2 and REST V3
  adapters went live about 4 minutes after the selections PUT (L-CONN-131, 2026-10-28).
- Read a connector's formats and the engines each supports before you design a read:
  `GET <serverUrl>/api/v2/connector/metadata?connectorName=<name>`, `cciMeta` formatters with `supportedEngineTypes`
  (spark only means an advanced-mode mapping and an advanced configuration) (L-CONN-130, 2026-10-26).

## 8. Overturned beliefs (runtime environments)

| Believed | Until | Now | Lesson |
|---|---|---|---|
| Service enablement on an agent is UI-only; the API is a silent no-op | 2026-09-22 | `PUT.../selections/ui` with `IDS-SESSION-ID`, proven with read-back | L-AGENT-079 -> L-AGENT-039 |
| Connector adapter enablement is UI-only | 2026-09-23 | MCP `secureagentmanagement` (2026-09-23), selections PUT (2026-09-28) | L-AGENT-080 -> L-AGENT-039 |
| No PUT is proven anywhere in IDMC | 2026-09-28 | The selections PUT is; other documented PUT/PATCH remain unproven until probed | L-AGENT-081 -> L-AGENT-039 |
| CAI is not activatable: no Process Server | 2026-09-21 | Process Server was in `agentEngines[]` | L-AGENT-086 -> L-AGENT-048 |
| APP_105060 adapter errors are permanent walls | 2026-09-22 | They cleared after re-provisioning | L-AGENT-087 -> L-AGENT-045 |
| The RE list's `readyToRun:false` means never runnable | 2026-07-26 | Stale list value | L-AGENT-082 -> L-AGENT-021 |
| After trimming, unreferenced packages in `downloads/` can be moved aside and deleted | 2026-09-28 | Services run from those package folders; never prune them | L-AGENT-055 -> L-AGENT-094 |
