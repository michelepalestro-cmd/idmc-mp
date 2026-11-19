# BUILD: Message Bus Replacement (Kafka + CAI), from an empty org to a verified run

Run every command from this blueprint folder (`toolkit/demos/message_bus_kafka_cai/`). Each step: **why**, the command, what
you should see, how to verify, how to undo. Tags: **PROVEN** = the same calls / XML worked end to end in a real org in
an earlier (non-generic) form; **ADAPTED** = rewritten or combined here and not yet re-run in this form. Writes are dry
runs until `--execute --expect-org <orgIdV3>` (the core library's guard). KB links are relative to this file.

Read first: [CAI Event Listeners - Kafka & AMQP (JMS)](../../../knowledge/05-cai-application-integration/06-cai-event-listeners-kafka-amqp-jms.md),
[CAI Asset Lifecycle](../../../knowledge/05-cai-application-integration/01-cai-asset-lifecycle-author-publish-unpublish-delete.md),
[Lessons: CAI](../../../lessons/by-domain/05-application-integration-cai.md).

| # | Step | Tag |
|---|---|---|
| 0 | Prerequisites | - |
| 1 | Credentials + config | - |
| 2 | Prove the org | PROVEN |
| 3 | Secure Agent with the Process Server on the Docker host | PROVEN (KB route) |
| 4 | Stand-in systems (docker compose) | ADAPTED |
| 5 | Project, folders, FRS records | ADAPTED |
| 6 | Generate the CAI package, consumers off | PROVEN grammar, ADAPTED assets |
| 7 | Import the package | PROVEN |
| 8 | Set the JMS secret encrypted | PROVEN |
| 9 | Publish in dependency order | PROVEN |
| 10 | Turn the consumers on | PROVEN |
| 11 | Check the routes and the consumer groups | PROVEN |
| 12 | Hospital sweep timer | ADAPTED |
| 13 | Smoke: an item and a PO over Kafka and over JMS | ADAPTED |
| 14 | The 19,500-line PO and the drills | ADAPTED |
| 15 | Load test | ADAPTED |
| 16 | Nightly CDI batch into Oracle | PROVEN parts, ADAPTED as a whole |
| 17 | Teardown | ADAPTED |

Count: 7 steps PROVEN (2, 3, 7, 8, 9, 10, 11), 9 ADAPTED (4, 5, 6, 12, 13, 14, 15, 16, 17), step 6 resting on a proven
grammar and step 16 on proven calls.

---

## 0. Prerequisites

- An IDMC org with Application Integration and Data Integration, and a user with Designer + Operator + Admin rights.
- One **Linux** host (8 vCPU / 16 GB recommended: Kafka, Artemis, Postgres, Oracle Free and the Secure Agent share it)
  with Docker + docker compose v2 and Python 3.10+. The agent reaches every stand-in on `127.0.0.1`; nothing listens
  on a public interface. The scripts in `verify/` also run there (they `docker exec` into the Kafka container and call
  the agent's local process endpoint).
- Images pulled on first start (no jars or drivers are shipped here): `apache/kafka:4.3.1`,
  `apache/activemq-artemis:2.42.0-alpine`, `postgres:16-alpine`, `postgrest/postgrest:v12.2.3`,
  `gvenzl/oracle-free:23-slim`, `curlimages/curl:8.10.1`. The IDMC Oracle and PostgreSQL connectors ship with the agent.

## 1. Credentials + config

**Why:** every value lives outside the code. **Do:**
1. Add the keys of [ENV_KEYS.md](ENV_KEYS.md) to your toolkit `.env` (default `~/.idmc_toolkit/.env`, or the file
   `IDMC_CREDS_FILE` points to), chmod 600. Generate `MBR_KAFKA_CLUSTER_ID` once:
   `docker run --rm apache/kafka:4.3.1 /opt/kafka/bin/kafka-storage.sh random-uuid`.
2. `cp config.example.json config.json` and fill in `org.org_id_v3`, `org.org_name`, `agent.name`,
   `agent.runtime_environment`, `agent.runtime_environment_id` (after step 3), `cdi_batch.template_task_id` (step 16).
3. `python ../../setup/check_setup.py --demo message_bus_kafka_cai` (offline) -> every key `ok`.
**Undo:** delete `config.json`; remove the keys.

## 2. Prove the org (PROVEN)

`python "../../lib/idmc_session.py" whoami --expect-org <orgIdV3>` -> your org name, v2 + v3 ids, the pod host.
One login; on `IDS_085` / `IDS_086` stop and fix the password (never loop logins, never delete the block file
without the user). [Access, Auth & Orgs](../../../knowledge/01-access-auth-orgs/).

## 3. Secure Agent with the Process Server (PROVEN route, KB)

**Why:** Kafka and AMQP listeners run only on an agent's Process Server; the agent must sit next to the stand-ins.
1. Install the agent on the Docker host headless: `GET /api/v2/agent/installerInfo/linux64` gives the download URL and
   an install token for this org; install as a non-root user
   ([Secure Agent - Install, Run & Tune](../../../knowledge/02-secure-agent-connections/01-secure-agent-install-run-tune.md)).
2. Enable the Process Server (Application Integration) on its runtime environment, and the Oracle + PostgreSQL
   connectors, at most a few at a time:
   `python "../../lib/idmc_runtime_selections.py" show <reId>` then
   `... set <reId> --enable "services:<Process Server item>" --execute --expect-org <orgIdV3>` (never select all: one
   host pulled about 18 GB and stalled).
3. Wait until `GET /api/v2/agent/details/<agentId>` shows `process-engine` RUNNING
   ([Process Server on a Secure Agent](../../../knowledge/05-cai-application-integration/04-process-server-on-a-secure-agent.md)).
4. Put the agent name and the runtime environment id in `config.json`.
**Verify:** `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:7080/process-engine/public/rt/x` answers (404 for
an unknown process is fine: the engine is up). **Undo:** `idmc_runtime_selections.py restore <backup>`.

## 4. Stand-in systems (ADAPTED)

**Why:** Kafka (the new bus), Artemis (the legacy JMS bus), the ledger + hospital + simulated targets, Oracle.
```
docker compose --env-file ~/.idmc_toolkit/.env -f infra/docker-compose.yml up -d
docker compose -f infra/docker-compose.yml logs mbr-kafka-init      # lists mbr.dlq mbr.item mbr.perf mbr.po
curl -s http://127.0.0.1:18080/rpc/config                            # {"result":"ok","retry_max":"5",...}
curl -s http://127.0.0.1:18080/targets                               # 7 rows, n = 0
docker logs mbr-oracle 2>&1 | grep -m1 "DATABASE IS READY"           # 1-3 minutes on first start
```
The Postgres init scripts (`infra/postgres/00..30`) run on the FIRST start only (empty volume). PostgREST serves only
schema `mbr_api` on 127.0.0.1:18080. Kafka, Artemis, Postgres and Oracle images and settings are PROVEN from the source
build (Kafka 4.3.1 KRaft, 5 MB message limit, 7-day retention); the PostgREST stand-in contract is new here.
**Undo:** `docker compose -f infra/docker-compose.yml down` (`--volumes` drops the data).

## 5. Project, folders, FRS records (ADAPTED)

**Why:** the import package must carry the project and folder records of the TARGET org (`Explore/<project>.Project.json`
and `<folder>.Folder.json`, built by `idmc/lib/mbr_cai.py frs_json()` from the org's own FRS answers).
```
python idmc/deploy_cai.py ensure-project                                  # dry run: shows the creates
python idmc/deploy_cai.py ensure-project --execute --expect-org <orgIdV3>
```
Calls: `GET /public/core/v3/objects?q=type=='PROJECT'`, `POST /public/core/v3/projects {"name","description"}`,
`POST /public/core/v3/projects/<id>/folders {"name","description"}`, `GET /frs/v1/Projects('<id>')`,
`GET /frs/v1/Folders('<id>')` (IDS-SESSION-ID). Writes `state/ids.json` + `state/frs.json`.
Names may not hold `.` or `#?|{}"^&[]/\` (V3API_ContainerError_004; KB L-MIG-075).
**Undo:** step 17 (delete the project).

## 6. Generate the CAI package, consumers off (PROVEN grammar, ADAPTED assets)

```
python idmc/gen_cai.py                 # -> build/cai/mbr_cai.zip + mbr_cai.json, 23 assets
python idmc/gen_cai.py --dump          # also build/cai/xml/<asset>.xml to read
```
**Why consumers off:** a connection published with `enabled="false"` consumers starts only its producer routes, so no
listener runs before its process exists (L-CAI-119). Offline dry run on any PC: `--offline-frs` (not importable).
What the XML contains, in short (read `idmc/lib/mbr_cai.py`, `mbr_flow.py`, `gen_cai.py`):
- Kafka connection: attributes `kafkaHost`, `kafkaPort`, `additionalBrokers`, `otherAttributesCommon`, `Use SSL`,
  `Use SASL`; consumers `typeName="KafkaConsumer"` with `topic`, `groupId`, `contentFormat=TEXT`,
  `otherAttributesProducerConsumer`; producers `typeName="KafkaProducer"`; `javaConnector plugin="Camel" type="KAFKA"
  uuid="c5d3f9bc-95ba-48e6-99df-5bca133b44b3"` (L-CAI-116).
- Consumer options `autoOffsetReset=earliest&consumersCount=3&maxPollRecords=5&maxPollIntervalMs=600000&autoCommitIntervalMs=1000`
  (6 consumers on the 6-partition load-test topic); producer options
  `requestRequiredAcks=all&enableIdempotence=true&retries=10&maxInFlightRequest=5&maxRequestSize=5242880`.
- AMQP connection: `type="AMQP" uuid="59b13626-0180-4d48-a749-38f8f33f7b18"`, `Query Parameters` =
  `jms.validatePropertyNames=false`, consumers `typeName="AMQP Source"` (queue, dead-letter queue, Payload Format Text),
  Password `encrypted="true"` with an EMPTY value.
- Listener process: `<deployment><targetLocation>agent</targetLocation><event eventSource="<conn>:<eventSource>"/>`
  and input `event` of type reference `<conn>:KafkaMessage` (or `:AMQPMessage`) with the connection GUID (L-CAI-118).
- Handlers, `mbr_deliver`: `<rest></rest>` with no access = private subprocess, no URL (L-CAI-130).
  `mbr_error_queue_replay`, `mbr_hospital_retry`: anonymous on the agent's endpoint.
- REST actions: `requestTimeout="10"` (seconds), `failOnError="false"` + an output `responseStatusCode="true"`.
**Undo:** delete `build/` (and `state/guids.json` only if you want new object identities: keep it to overwrite).

## 7. Import the package (PROVEN)

```
python idmc/deploy_cai.py import                                       # dry run: NEW / EXISTS preview, nothing sent
python idmc/deploy_cai.py import --execute --expect-org <orgIdV3>
```
Calls (core `idmc_export_import.cmd_import`): multipart `POST /public/core/v3/import/package` (field `package`) ->
`jobId`, `checksumValid` (false = never start), `POST /public/core/v3/import/<jobId>`
`{"name", "importSpecification": {"defaultConflictResolution": "OVERWRITE", "includeObjects": [<the package GUIDs>]}}`,
poll `GET /public/core/v3/import/<jobId>?expand=objects`. Expect SUCCESSFUL with 23 objects.
**Verify:** `python idmc/deploy_cai.py status` lists 23 assets (unpublished). **Undo:** step 17.

## 8. Set the JMS secret encrypted (PROVEN)

```
python idmc/deploy_cai.py set-secret --execute --expect-org <orgIdV3>
```
`PUT https://<pod>-cai.<domain>/active-bpel/asset/v1/update?assetType=AppConnection` (INFA-SESSION-ID, JSON)
`{"connections":[{"guid":{"$t":"<objectId>"},"attributes":[{"key":{"$t":"User Name"},"value":{"$t":"..."}},
{"key":{"$t":"Password"},"value":{"$t":"..."}}]}]}` -> `{"status":{"$t":"SUCCESS"}}` (L-CAI-132). The value is
stored as a sensitive value and never exported. **Verify:** after step 9, the bridge consumes (step 13 over JMS).

## 9. Publish in dependency order (PROVEN)

```
python idmc/deploy_cai.py publish --execute --expect-org <orgIdV3>
```
One asset path per call, in the manifest order: service connectors -> REST connections -> Kafka / AMQP connections ->
`mbr_deliver` -> handlers -> replay -> sweep -> listeners -> bridges. `POST /active-bpel/asset/v1/publish`
`{"data":{"type":"publish","attributes":{"assetPaths":["Explore/Message Bus Replacement/<folder>/<name>.<TYPE>.xml"]}}}`
-> 202 + job id; poll `.../publish/<id>/Status` and check every `itemDetail[].itemState` (a 202 is only submission).
The script stops at the first failure: later assets depend on it.
**Verify:** `deploy_cai.py status` -> every asset `published`. **Undo:** `deploy_cai.py unpublish --execute ...`.

## 10. Turn the consumers on (PROVEN)

```
python idmc/gen_cai.py --consumers on
python idmc/deploy_cai.py import  --only listeners --execute --expect-org <orgIdV3>
python idmc/deploy_cai.py publish --only listeners --execute --expect-org <orgIdV3>
```
Only the three listener connections are re-imported and republished. A new group with `autoOffsetReset=earliest`
reads everything still retained in its topic. **Undo:** rebuild with `--consumers off` and republish the three.

## 11. Check the routes and the consumer groups (PROVEN)

- Agent catalina log (under the agent's `apps/process-engine` logs): 'Starting route ... mbr-kafka:item-sub',
  'Subscribed to topic(s)'; no 'Failed to start route' (a route can fail while the publish says SUCCESS, L-CAI-125).
- `python verify/ops.py status` -> groups `mbr-cai-item`, `mbr-cai-po`, `mbr-cai-store-price`, `mbr-cai-perf` with
  members > 0 and lag 0.

## 12. Hospital sweep timer (ADAPTED)

```
docker compose --env-file ~/.idmc_toolkit/.env -f infra/docker-compose.yml --profile timer up -d mbr-timer
docker logs -f mbr-timer          # "sweep HTTP 200" every 60 s
```
**Why a container:** the CAI scheduler stores but never runs schedules for agent-run processes (L-CAI-142); a 1-minute
timer posting to the agent's anonymous endpoint plays the hospital retry adapter (the source build used a systemd
timer). Each sweep is one CAI run (1,440 a day). **Undo / pause:** `docker stop mbr-timer`.

## 13. Smoke: an item and a PO over Kafka and over JMS (ADAPTED)

```
python verify/ops.py reset --yes
python verify/send.py smoke        # SMOKE: item via kafka PASS, PO via kafka PASS, item via jms PASS, PO via jms PASS
python verify/send.py item --via kafka
python verify/send.py po --via jms --lines 25
```
Expected timeline of an item: `consumed` (item subscriber) -> `validated` -> `delivered` target all; `consumed`
(store-price subscriber) -> `delivered` target store; over JMS a `bridged` event first. **Verify** on the CAI Monitor:
7 runs for the Kafka item, 8 for the JMS one (README section 6).

## 14. The 19,500-line PO and the drills (ADAPTED)

```
python verify/send.py po --lines 19500           # ~4 MB; merchandising and warehouse both report 19,500 lines
python verify/drills.py all                      # poison, validation, outage, missing-items, compensation, large-po
python verify/drills.py restart --expect-org <orgIdV3>   # stops / starts mbr-kafka:item-sub (an IDMC write)
```
- **poison**: malformed XML -> listener catch -> hospital `MALFORMED_XML` (not retryable) + a copy on `mbr.dlq` -> the
  operator discards it.
- **outage**: merchandising answers 503 for 90 s -> `mbr_deliver` retries 2 / 4 / 8 / 16 s -> hospital
  `MERCH_UNAVAILABLE` (retryable) -> back -> replay -> delivered (the warehouse part answers `duplicate`) -> resolved.
- **missing-items**: a PO before its items -> hospital `ITEMS_MISSING` -> the items arrive -> replay -> delivered.
- **compensation**: the warehouse refuses a PO -> the merchandising PO is cancelled -> hospital `REJECTED`.
- **restart**: stop the item listener, send 50 items (lag grows, the store-price group keeps reading), start it ->
  all 50 delivered; a few re-read after the restart are answered `duplicate`.
`listener_ctl.py`: `POST https://<pod>-cai.<domain>/active-bpel/local/restadmin/eventconnection/stop?agentName=<agent>`
`{"eventRoute":["project:/rt.connection/mbr-kafka/$public/mbr-kafka:item-sub"]}` and `/start`
`{"routeInfo":[{"eventRoute":"..."}]}` with **IDS-SESSION-ID** (L-CAI-122).

## 15. Load test (ADAPTED)

`python verify/load_test.py --rate 40 --seconds 30` (1,200 CAI runs) or `--burst 3000`. Prints delivered, p50 / p95 and
the drain rate. Ask the org owner first: every ping is a CAI run.

## 16. Nightly CDI batch into Oracle (PROVEN parts, ADAPTED as a whole)

**Why:** the overnight batch the legacy estate runs into its database, done by CDI on the same agent.
1. Connections (dry run first): `python idmc/cdi_batch.py connections --test --execute --expect-org <orgIdV3>`.
   Oracle body (PROVEN): `{"@type":"connection","name":"mbr_oracle","type":"Oracle","runtimeEnvironmentId","host",
   "port":1521,"database":"FREEPDB1","schema":"MBR_BATCH","codepage":"UTF-8","username","password"}`. PostgreSQL:
   `type TOOLKIT_CCI`, `instanceName PostgreSQL`, `connParams` with `userName`; the accepted `authenticationType` drifts
   by pod: copy a working connection's key set. Encryption: `noEncryption` only while the ledger host is loopback (the
   stand-in on 127.0.0.1:15432, no server certificate); any other host gets `encryptionMethod SSL`, `tlsv1_2` and
   `validateServerCertificate` `true` (`cdi_batch.pg_tls`). Kafka: `kafka.use_ssl` false is accepted only for loopback
   brokers ([Connector Notes](../../../knowledge/02-secure-agent-connections/04-connector-notes-bigquery-postgresql-salesforce-jdbc-flat-file.md)).
2. Template task (**UI-only wall if your org has none**): Data Integration > New > Mapping Task > mapping
   `dsst__copy_data_new_tgt` (Add-On Bundles) > any source / target > Save. Put its v2 id in
   `cdi_batch.template_task_id`.
3. Tasks: `python idmc/cdi_batch.py tasks --execute --expect-org <orgIdV3>` -> 3 tasks (`mt_mbr_items_to_oracle`,
   `mt_mbr_po_header_to_oracle`, `mt_mbr_po_line_to_oracle`), each a `customQuery` from `idmc/templates/` with
   truncate (core `idmc_mttask.py clone`, PROVEN pattern; the Oracle target attributes are ADAPTED: read the first
   task back with `idmc_mttask.py show <id>` and compare with a UI-made Oracle target).
4. Taskflow + schedule: `cdi_batch.py taskflow --execute ...`, then
   `cdi_batch.py schedule --start-utc <first run, UTC> --execute ...` (pod-local times: see core
   `idmc_taskflow_schedule.py`).
5. One run (1 + 3 jobs against the monthly job budget): `cdi_batch.py run --execute ...`; then in Oracle
   `SELECT COUNT(*) FROM MBR_BATCH.MBR_PO_LINE` equals `merch_lines` summed in `curl -s 127.0.0.1:18080/po_status`.
**Undo:** unbind the schedule (`idmc_taskflow_schedule.py unbind <wfId>`), then `idmc_frs_delete.py v2-delete`
workflow, mttask, connection (in that order).

## 17. Teardown (ADAPTED)

`python teardown/teardown.py plan`, then in order: `export` (backup) -> `schedule` -> `cai` (stop listeners, unpublish
in reverse) -> `delete` (core FRS delete, leaf first; it refuses published assets, `FRS_082`) -> `infra --volumes`.
`teardown/pg_undo.sql` drops the Postgres schemas and roles if you keep the container.

---

## Gotchas (every hard-won fix)

1. **Consumers first off, then on** (L-CAI-119). Republishing a connection restarts all its event sources: a
   subscriber you stop and start alone gets its own connection (`mbr-kafka-store`).
2. **One process at a time per consumer** (L-CAI-120): a Wait or a retry backoff inside a Kafka-started process holds
   its partition. Keep in-process retries short (here max 30 s); long outages belong in the hospital.
3. **A stop resumes from the last auto-commit** (L-CAI-121): set `autoCommitIntervalMs=1000` and make every target
   idempotent on (message id, revision); here they answer `duplicate`.
4. **restadmin eventconnection needs IDS-SESSION-ID**; INFA-SESSION-ID answers 500 NullPointerException (L-CAI-122).
5. **JMS property names with hyphens vanish over AMQP** unless `jms.validatePropertyNames=false` in the connection's
   Query Parameters (L-CAI-123). The bridge also reads `mbr_msg_id`-style names and the envelope as fallbacks.
6. **`messageKey` is empty on consume**: send the business key and the message id as headers (L-CAI-118). Produce with
   the native producer: Service `<conn>:<eventTarget>`, input `event` = a temp field typed `<conn>:KafkaMessage` with
   `messageKey`, `body`, `headers` (L-CAI-124).
7. **Idempotent producer needs `retries` set** (Camel default 0): otherwise the route fails to start while the publish
   says SUCCESS; callers then get 'No consumers available on endpoint' (L-CAI-125). Read the catalina log.
8. **4 MB messages**: broker `message.max.bytes`, topic `max.message.bytes` and the producer `maxRequestSize` all
   5,242,880 (the producer default 1 MB stopped the bridge, L-CAI-127).
9. **`requestTimeout` is in seconds** (`10000` = no timeout in practice, L-CAI-128). A timeout returns HTTP 500 to a
   `failOnError="false"` action, which `mbr_deliver` retries (L-CAI-129).
10. **Private subprocess**: `<rest></rest>` with no access gives no URL but is callable as a subprocess (L-CAI-130).
11. **`util:getProcessId()`** in every ledger event joins it to the run in the Monitor (L-CAI-131).
12. **Secrets**: author `encrypted="true"` + empty value, set with `asset/v1/update` (L-CAI-132). `encrypted="false"`
    stores AND exports the value in plaintext.
13. **Out-of-date after a republish** (L-CAI-133): import only what changed (`includeObjects`), publish processes
    last. The runtime can serve the old version for about 20 s.
14. **A Decision whose branches all end has no outgoing link** (L-CAI-135; `mbr_flow.decision` handles it). The long
    'ActiveVOS specific extension function used' text in `itemStatusDetail` is noise: the real error is at its end.
15. **The package must carry its dependency closure** (L-CAI-136): every connection / connector a process names; an
    `objectRefs` entry to an object outside the package gives `MigrationSvc_031`.
16. **Subprocess outputs need an explicit mapping**, and a callee fault is caught around the Subprocess step
    (L-CAI-137). Malformed XML faults in `util:parseXML` ('xmlStringToElement', 'SAXParseException') -> MALFORMED_XML.
17. **Replays lose hand-off headers: ask the system of record** (L-CAI-138): the PO handler asks merchandising for the
    applied version on every run instead of trusting a header.
18. **An unset field is EMPTY, not ''**: `$temp.x = ''` is false; `mbr_flow.sx()` wraps field references in `string()`.
19. **`&` between query parameters in a REST action URL must be `&amp;amp;` in the file** (L-CAI-145; `url_amp()`).
20. **Package checksums**: one `path=SHA256` line per file, spaces escaped `\ `, upper-case hex; `checksumValid=false`
    means fix the file, never start the import. No 0x08 bytes (a shell heredoc once turned `\b` into one).
21. **Kafka console producer**: Kafka 4.x deprecates `--property` in favour of `--reader-property`; if your broker
    version refuses `--property`, change `verify/mbr_msgs.kafka_cmd()`.
22. **Artemis STOMP**: a SEND frame with `content-length` becomes a BytesMessage; without it a TextMessage (what the
    CAI AMQP consumer with Payload Format Text expects). STOMP header values escape `:` as `\c`.
23. **PostgREST**: a function with ONE unnamed `json` argument receives the request body as is; GET works only on
    STABLE functions; a function sets its HTTP status with `set_config('response.status', '503', true)`.
24. **The agent's engine port 7080 is plain HTTP**: anonymous processes there answer anyone who reaches the port. Keep
    it on loopback / firewalled.
25. **Every task and taskflow run is one job** against the org's monthly cap, invisible headless (the license API
    shows -1). The batch costs 4 jobs a night.
26. **Sessions die about 30 min after grant**: the core library re-logs in once at 24 min; never retry a rejected
    login (IDS_086 lockout).

## UI-only walls (no API did it in the source work)

| Wall | Click path / workaround |
|---|---|
| The first Copy Data template task (if the org has none to clone) | Data Integration > New > Mapping Task > Mapping: Add-On Bundles > `dsst__copy_data_new_tgt` > Save |
| Counting CAI runs per message | Monitor > Application Integration (process run list), filter by time and `mbr_` names (README section 6) |
| Scheduling an agent-run CAI process | not possible headless (L-CAI-142): the `mbr-timer` container instead |
| A Data Access Service (JDBC) connector would not publish in one org | stand-ins and ledger behind REST (PostgREST) instead (L-CAI-139) |
| Orphan CAI catalog rows after deleting probe assets | none: no API deleted them; avoid probes in the project folder |
| Reading the agent's catalina log | on the agent host (shell), not via IDMC REST |
