# Troubleshooting: the four gates

**Answers:** Why does a connection test or a job fail on a Secure Agent, and in which order do I check? What does each
agent, engine, adapter, driver and host signature really mean?

**Read when:** a connection test fails, a run dies early, engines flap or stay in ERROR, the agent will not start, or
an error names an engine, an adapter id or a driver.

**Key rules:**
- Fix the gates in order: host, engine, adapter, driver; only then bodies and credentials (L-AGENT-034).
- `APP_105060` is a family: read the message to see whether it names an engine, an adapter or a binding (L-CONN-018).
- RUNNING is a deployment signal; only a passing test or a run that lands rows proves an engine usable (L-AGENT-023,
  L-CONN-015).
- Read the first `[ERROR]` of a session log: a heap OOM shows up later as token errors on other reader partitions
  (L-CDI-210).
- Engines left in ERROR after a memory thrash need the load removed and one agent restart (L-AGENT-076).
- To prove a process is not in a data path, measure bytes on its existing sockets or stop it; a new-connection sampler
  proves nothing (L-METHOD-123).

**Related:** [01 Secure Agent](01-secure-agent-install-run-tune.md) ·
[02 Runtime Environments](02-runtime-environments-services-connectors.md) ·
[04 Connector Notes](04-connector-notes-bigquery-postgresql-salesforce-jdbc-flat-file.md) ·
[Error Triage](../00-start-here/04-error-triage.md) (the org-wide table) ·
[Lessons: Secure Agent & Connections](../../lessons/by-domain/02-secure-agent-connections.md)

**Last verified:** 2026-11-03 (evidence 2026-06-27 to 2026-11-03).

> A working connection or job needs four independent things, established in order: **HOST** (RAM, disk, swap, OS
> libraries, egress, one healthy agent JVM), **ENGINE** (the service selected and RUNNING on that runtime environment),
> **ADAPTER** (the connector selected and deployed on that agent), **DRIVER** (third-party jars staged and loaded). Each
> gate fails with its own signature that looks like "the connection is broken". The tables in section 3 map every
> signature seen to its cause and fix.

---

## 1. The gates

(L-AGENT-034, 2026-09-28.) Out-of-order work is the difference between an hour and a day.

| Gate | Must be true | Check with | Typical failure | Fix |
|---|---|---|---|---|
| 1 HOST | Enough RAM/disk/swap; native libraries resolvable; outbound HTTPS; exactly one agentcore JVM; under a real supervisor | `free`, `df`, PSI, `ldd pmdtm`, `pgrep -c -f 'agentcore.impls.MainApp'`, `getstatus`, `systemctl status <unit>` | Rotating test errors (OOM churn), exit 127, `SingularApplicationLock`, agent gone after reboot | [doc 01](01-secure-agent-install-run-tune.md) |
| 2 ENGINE | The service is selected on the RE and its engine is RUNNING (not DEPLOYING) | `GET /api/v2/agent/details/<agentId>`, the RE selections | 'No running service found of type <Engine> <ver>.* service for AgentGroup: <reId>' | Select the service; wait; [doc 02](02-runtime-environments-services-connectors.md) |
| 3 ADAPTER | The connector is selected on the RE and deployed on that agent; the org knows the type | RE `connectors.selections[]`; `<agent_home>/apps/Connector_Service/<ver>/connectors/cci/plugins/` | 'Unable to fetch Connector attributes... [com.informatica.adapter.<x>]'; 'no connector with type=' | Select the connector; one UI connection for a new type |
| 4 DRIVER | Third-party jars are in the directory the consumer reads, and the consumer was restarted | `ls ext/connectors/thirdparty/informatica.jdbc_v2/common/`; tomcat log | 'Unable to load driver'; 'Failed to load driver class com.simba...' | Stage, restart, test ([doc 04](04-connector-notes-bigquery-postgresql-salesforce-jdbc-flat-file.md) section 4) |
| then | Body and credentials | Connection test, then a run that lands rows | APP_10519, APP_105054, auth errors | [doc 03](03-connections-create-test-update-delete.md) |

## 2. Triage order

1. **Name the org and the agent.** Which runtime environment is the connection or task bound to, and which agent serves
   it? Read `GET /api/v2/agent/<agentId>` per agent; never trust the runtime-environment list's `readyToRun`
   (L-AGENT-021, 2026-07-26).
2. **Read the engine list.** `GET /api/v2/agent/details/<agentId>`: is the engine the error names present, and RUNNING?
   DEPLOYING means wait; a changing engine name in successive errors is progress (L-AGENT-026, 2026-07-26).
3. **Read the host.** RAM, swap, disk, load, PSI; one agentcore JVM; recent OOM kills (`dmesg`, `journalctl -k`); the
   agentcore.log 'Service Status Distribution' line.
4. **Read the exact error text.** APP_105060 alone is not a diagnosis: the same code carries the engine gate, the
   adapter gate and a binding problem, and the message names which (L-CONN-018, 2026-09-28).
5. **Fix one gate, re-test once.** `GET /api/v2/connection/test/<connId>` is free; then a small run that lands rows.
6. **Distrust convenient reads**: the RE list, the connector catalog, a single RUNNING, a green JDBC V2 test, router
   error codes (section 5).

## 3. Signatures: cause and fix

### 3.1 Connection-test and create errors

| Signature | Cause | Fix | Lesson |
|---|---|---|---|
| 403 APP_10519 'The connection type is not valid' | `type` set to a connector name or shortName, or a flat body | `type: "TOOLKIT_CCI"` + `instanceName` + nested `connParams` | L-CONN-001 |
| 403 APP_10519 on a native `FLATFILE` connection; 'no connector with type' for CCI 'Flat File' | Wrong flat-file type | `type: "CSVFile"` | L-CONN-065 |
| 403 'no connector with type=<shortName>' (for example `GoogleBigQueryV2`) | Add-on connector type never registered in the org | Create one connection of that type in the UI once (July 2026 evidence) | L-CONN-005 |
| 403 'There is no connector with type=' | `instanceName` spelled wrong (`JDBC_V2`, `JDBC V2`) | Use the display name (`JDBCV2`) | L-CONN-046 |
| 403 APP_105054 naming an attribute | Validator: one missing or misnamed field | Add it, repeat until 200 | L-CONN-002 |
| `UI_13427 Code page is not valid` for one type while others give APP_10519 | That shape reaches real validation | Keep that type, fix the body | L-CONN-002 |
| REPO_10200 (name exists) | Update sent to the create path | `POST /api/v2/connection/<connId>` | L-CONN-006 |
| 403 APP_105060 'Unable to resolve channel service. No running service found of type Data_Integration_Server <ver>.* service for AgentGroup: <reId>' | DIS not selected, still deploying, or down on that RE | Select Data Integration; wait for RUNNING; restart a dead DIS | L-AGENT-076 |
|... 'of type Connector_Service 21.*' right after a DIS error | Deployment progressing to the next engine | Wait and re-test | L-AGENT-026 |
| 'No running service found of type Connector_Service' on a working agent | Connection bound to another RE (hosted or regional agent) | Use a connection bound to your RE | L-CONN-023 |
| 403 APP_105060 'Unable to fetch Connector attributes, Ensure adapter ID is valid and the service is enabled [com.informatica.adapter.<x>]' | Connector not selected or not deployed on that agent | Select the connector on the RE; wait for the package | L-CONN-019 |
| The same, after enabling engines | Enabling engines does not enable connectors | Select the connector too | L-CONN-019 |
| Test error moves from APP_105060 to `error [error [null]]` | Proves nothing: a bogus host gives the identical answer (seen when bound to a parent org's shared RE) | Fix the binding, not the host | L-AGENT-038 |
| 'Unable to load driver' (JDBC V2) | Jar not in `common/`, staged before the engine deployed, or not reloaded | Stage in `common/` (+ `deploy_to_main`), restart Connector_Service or the agent | L-CONN-049, L-CONN-051 |
| 'JDBC driver is available at the correct location' after an engine upgrade | Jar left in the old DIS version directory | Stage in `ext/deploy_to_main/...` and restart | L-CONN-050 |
| `NoClassDefFoundError ClickHouseClient` | Non-shaded `-all` jar | Use the `-shaded` jar; check size | L-CONN-053 |
| slf4j errors from the ClickHouse driver | Bare URL picks the Apache HTTP client | `?http_connection_provider=HTTP_URL_CONNECTION` | L-CONN-054 |
| Test green, database log shows the default user with no password | JDBC V2 sent no password (disputed whether it ever does) | Server-side auth config; read the DB auth log | L-CONN-048 |
| 403 'password authentication failed for user <old>' | Stale password or a renamed database role | Update every connection using that role, re-supplying the password | L-CONN-011 |
| Connection broken right after an unrelated update | Masked secret posted back and blanked | Re-supply the secret on every update | L-CONN-007 |
| 500 APP_21000 on `POST /api/v2/connection/test` | Wrong verb or path | `GET /api/v2/connection/test/<connId>` or MCP `test_connection_by_id` | L-CONN-014 |
| `200 []` from `GET /api/v2/connection/source/<connId>` on a connection that tests green | The browse is not evidence of an empty or unreadable database | Confirm through a profile, preview or scan; prove the test from the database's own counters | L-CONN-016 |
| `403 CONSUMER_INVALID` from a BigQuery connection | The key's cloud project was deleted | A key from a live project | L-ENV-052 |
| Test times out whatever the credentials | No network route (another cloud's private range; DB firewall allows only tagged hosts) | VPN, peering, or an agent on an allowed host | L-AGENT-037 |
| Failing from a containerized agent with host `127.0.0.1` | Loopback of the agent container | Docker service names; `/dev/tcp` probe | L-CONN-025 |
| 403 APP_105060 '... AgentGroup <hosted runtime id>' on **every** hosted connection at once, Secure Agent connections green | A Hosted Agent outage: not a gate you can fix | Support case, then fail over tasks and connections ([doc 02](02-runtime-environments-services-connectors.md) §1) | L-AGENT-117, L-ENV-100 |
| A task moved to a healthy agent still fails at a lookup | The lookup's connection is still bound to the old runtime | Rebind the connection ([doc 03](03-connections-create-test-update-delete.md) §4) | L-CONN-132 |
| ADLS Gen2 test 403 | The storage account has no hierarchical namespace | An HNS account, or Blob Storage V3 on the plain account | L-CONN-129 |

### 3.2 BigQuery, PostgreSQL, Salesforce, Fabric and flat-file run errors

| Signature | Cause | Fix | Lesson |
|---|---|---|---|
| 'Invalid PKCS#8 data' (CDI, DBMI Simba or the Data Gateway) | Private-key format not accepted by that engine on that pod | Probe formats per consumer; one connection per consumer | L-CONN-035, L-CONN-036 |
| `BaseEncoding DecodingException: Unrecognized character: 0x20` | Wrapped key pasted into the UI | Upload the key file or paste a clean copy | L-CONN-037 |
| '4005 - Direct Read Mode with Hybrid connection mode is not supported' | Connection switched to Hybrid | Back to Simple | L-CONN-042 |
| 'table contains [JSON] data type incompatible with [Simple] connection mode' | JSON column in Simple mode (July builds) | STRING cast or STRING column; test JSON targets on your pod | L-CONN-043 (disputed) |
| Values exactly 255 characters long in the warehouse | BigQuery V2 writer cut STRING ports | Land long text into JSON-typed columns | L-CONN-044 |
| CMN_1081 on a BYTES target | Unsupported target type for long text | JSON column | L-CONN-044 |
| 'Failed to load driver class com.simba.googlebigquery.jdbc.Driver' (DBMI deploy) | Simba jars missing on the agent | Copy the set, restart the agent | L-CONN-045 |
| SDK_APP_COM_20000 'Incorrect list of path is populated with size: 1' | PostgreSQL object given as `schema/table` | `<schema>/TABLE/<table>` | L-CONN-028 |
| 'Object(s) [X] not found' on PostgreSQL | Bare, dotted or quoted object name | `<schema>/TABLE/<table>` or `<schema>/VIEW/<view>` | L-CONN-028 |
| NPE 'error [null]' on a PostgreSQL create | Wrong user key for that connector build | Copy keys from a working connection | L-CONN-027 |
| 'not a valid choice' for `authenticationType` | Value not accepted by that build | Try the values seen (Database, UserIdPassword, Standard) or copy from UI | L-CONN-027 |
| Salesforce checkbox not set | Non-integer value | 1 / 0 | L-CONN-059 |
| Salesforce 'long' fields empty on read | Connector drops SOAP long | Salesforce REST API | L-CONN-060 |
| New Contacts silently not created | Salesforce duplicate rule | Adjust the rule; decide where dedup lives | L-CONN-061 |
| 'Staging Lakehouse Name is not set' | FabricDW connection without `StagingLakehouseName` | Set it with an update | L-CONN-071 |
| 24801 / 'compute capacity has exceeded its limits' / 24800 / APP_13400 | Fabric capacity throttled / paused / exceeded on browse | Pause failing jobs, suspend/resume, or resize | L-CONN-073 |
| `FABRICDW_10000 Invalid operation field name <column>` | A specific Fabric column | Fix or exclude that column | L-CONN-074 |
| FR_3085 'null character' | Empty CSV fields | Placeholder plus NULLIF | L-CONN-066 |
| Flat-file task cannot read its directory | Agent OS user lacks permission | Shared group directory, mode 2775 | L-CONN-067 |
| 'Length/Precision must be greater than 0' (ClickHouse) | String reports precision 0 | `toFixedString(col, N)` | L-CONN-055 |
| REPO_38210 on import | Reserved 'Informatica Cloud Hosted Agent' name | Remap objects to your RE | L-CONN-024 |
| Targets double on every run / SUCCESS with 0 rows | `truncateTarget` not honoured | Explicit truncate (Pre SQL, write disposition, a step) | L-CONN-032, L-CONN-056 |
| 'Custom quota exceeded' on every task that queries one BigQuery project | The project's daily query quota is used up (for example by BI refreshes) | Raise the cap or separate the quotas | L-CONN-133 |
| Integer-to-Long cast error on a ClickHouse UInt32 target | The driver wants the next wider Java type | bigint port (UInt16 integer, UInt64 decimal(20,0)) | L-CDI-291 |
| 'Too many simultaneous queries (max 32)' or Code 241 'memory limit exceeded' (ClickHouse through JDBC V2) | Uncapped parallel lanes | Per-query `max_threads` and `max_memory_usage`; about 3 heavy lanes | L-CDI-292 |

### 3.3 Engine, DTM and host errors

| Signature | Cause | Fix | Lesson |
|---|---|---|---|
| 'DTM process terminated unexpectedly', state 3 in ~2 s, 0 rows | Source and target connectors on different agents, or the connection bound to another RE | Co-locate connectors; bind to the task's RE | L-CONN-022 |
| Abort at 'Importing Connection: <conn>' (`trepcnx.cpp:296`) | Task runtime cannot use that connection (binding or missing connector); or a preview connector build | Rebind / select the connector; check the connector package version | L-CONN-022, L-CONN-072 |
| pmdtm exit 127, 'error while loading shared libraries: libidn.so.11' | Debian 12 / EL8-9 lack libidn v1 | Symlink or EL7 RPM | L-AGENT-059, L-AGENT-060 |
| pmdtm cannot load `libcrypt.so.1` | EL8/EL9 | `dnf install libxcrypt-compat` | L-AGENT-060 |
| pmdtm exit 134 (SIGABRT) | Missing library, or a broken connector build | `ldd`; connector version | L-AGENT-061 |
| Exit 137, OutOfMemory, GC overhead | Heap too small or host over-subscribed | DTM `JVMOption1` set cloud-side; fewer readers; fewer services | L-AGENT-056, L-AGENT-088, L-AGENT-057, L-AGENT-052 |
| `PLUGIN_1762... OutOfMemoryError: Java heap space` in one reader, then `BIGQUERYV2_10000... [5001 - Unexpected error refreshing access token]` on the other partitions and `WRT_8044 No data loaded for this target` | DTM heap exhausted; the token errors are a cascade of the dying JVM (unsorted Joiners, Sorters and Aggregators are the usual victims) | Read the first `[ERROR]`; take the mapping out of the live lanes; raise the DTM heap cloud-side; split it or sort the Joiner inputs | L-CDI-210 |
| A heap edit in `pmrdtm.cfg` changed nothing | It was made in a version directory that is not running | Find the running DIS version from the JVM command line; set the heap cloud-side | L-AGENT-056 |
| Tasks wait 10-70 s before 'DTM process started'; never more than 2 DTMs at once | The default DTM pool (`maxDTMProcesses` = 2) | Raise it cloud-side ([doc 01](01-secure-agent-install-run-tune.md) §6.2) | L-AGENT-099 |
| `PROFILE_SVC_00014` 'No running service found of type Data_Integration_Server' on a profile create or run | DIS (and its siblings) in ERROR, often after a memory thrash whose self-restarts failed; they stayed in ERROR for about 2 hours | Remove the load; `systemctl restart <unit>` once; poll agent details until every engine is RUNNING (~8 min) | L-AGENT-076 |
| Slice throttles even when idle (`memory.events high` in the millions); agent RSS above the cap | Configured heaps exceed the cap, agent processes outside the slice, or orphan JVMs | Sum every `-Xmx`; start helpers with `systemd-run --scope --slice=<agent-slice>`; kill orphans | L-AGENT-017 |
| Every profile run dies; import log stops at 'Error encountered while Parsing file' | Dangling `*.xml` symlinks in rdtm plugin folders | Rename them, restart | L-AGENT-063 |
| Scans complete, 0 columns profiled | The profiling DTM dies at launch (exit 127) | Native libraries | L-AGENT-059 |
| Rotating connection-test errors on a busy host | Engines OOM-killed mid-handshake | Size the host; cap the agent | L-AGENT-052 |
| DIS ERROR with `subState` 303; every test fails | DIS Tomcat up but seen down by the control plane | Restart the agent detached | L-AGENT-075 |
| Engines RESTARTING forever; 'missing privitar.jdbcproxy.userWithConnectionPrivileges' | Data Access Management without a policy proxy | Deselect DAM on that RE | L-AGENT-046 |
| DAM Agent/Proxy log 'Initializing TMS and CMS configuration services', then `ProcessSupervisor... exit code: 133` about 3.5 min after 'Application status set to running', forever | The org has no Data Access Management setup or entitlement (vendor-hosted agents loop too) | Set DAM up in the org, or deselect it; exclude both from monitors | L-AGENT-091, L-AGENT-100 |
| AI Agent Runtime stuck DEPLOYING on Ubuntu 22.04 | Missing `unzip`, `libffi.so.6`, `libreadline.so.7` | Install `unzip`, `libffi6`, `libreadline7`, `libtinfo5` | L-AGENT-062 |
| `/process-engine/status` 404, every PE URL 404 | Context descriptor deleted by `deploy.sh`, or an empty webapp | Restore `process-engine.xml`, re-run deploy | L-AGENT-072 |
| 7443 never binds | `conf/ae.keystore` / `ae.cacerts` missing | Copy from `<peVersion>/conf/certs` | L-AGENT-072 |
| 'PostgreSQL database has started' but no embedded Postgres; empty data dir | Another Postgres on 5432 | Move the PE Postgres port; port guard | L-AGENT-071, L-AGENT-073 |
| Process Server restarts every ~2 min; 'Error creating SSLContext... conf/ae.keystore (No such file or directory)'; 'Process Server update failed' | The deploy's Liquibase update reached another Postgres on 5432 and exited before copying the keystore | Move the port in `bin/*.sh`, `process-engine.xml` and `user.conf`; `.lcm/stop-wrapper.sh` then `.lcm/deploy-wrapper.sh` | L-AGENT-089 |
| `/process-engine/status` 404, then `[LCM_10012]... Status script return code: EXITED_NONZERO` and a restart | A flapping Process Server (Cloud Integration Hub writes the same LCM_10012 lines) | Count restarts per engine name; repair per [Process Server on a Secure Agent](../05-cai-application-integration/04-process-server-on-a-secure-agent.md) | L-AGENT-100 |
| The second agent's Process Server stays in ERROR | 7005, 7080 and 7443 are static; the first Process Server holds them | One Process Server per host | L-AGENT-090 |
| CIH restart-loops on a second agent: 'The Tomcat connector configured to listen on port 19443 failed to start' | Static `server.api.port` | A free port in `CIHProcessor/<ver>/conf/application.properties`, guarded after upgrades | L-AGENT-090 |
| Agent starts, then stalls; ports 7005/14479 held | Orphans from a respawn | Reaper in ExecStartPre/ExecStopPost | L-AGENT-013 |
| Agent down after every reboot | No unit, or it lives in a run-command scope | systemd unit | L-AGENT-009, L-AGENT-011 |
| `systemctl` reads `active (exited)` but the agent is dead | `Type=forking` + `RemainAfterExit=yes` report the unit, not agentcore | Check `pgrep -u <agentuser> -c -f agentcore.impls.MainApp` and `getstatus` | L-ENV-069 |
| agentcore dies about 40 s after every start, right after a reboot | A stale AI Agent Runtime `gunicorn.pid`: its stop script killed a reused PID's process group | Move stale `.pid` files aside before the start | L-AGENT-095 |
| The pre-start guard refuses every start on a host with two agents | It counts the other agent's ports and `*.mv.db` files | Scope it to this agent's OS user and home | L-AGENT-096, L-AGENT-013 |
| Most services in ERROR with './status.sh: not found' or 'No such file or directory' after a disk clean-up | `downloads/` was pruned; services run from it | Restart the agent service: it re-downloads the pinned packages (~10 min); never prune it again | L-AGENT-094 |
| Catalog scan PARTIAL_COMPLETED 'Total objects processed count N is the same as objects count with errors'; `AccessDeniedException` on `/tmp/poifiles` | A second agent user on the host; the first created the directory with mode 755 | `chmod 1777 /tmp/poifiles` and write-test as both users | L-CDGC-150 |
| CLAIRE GPT 'Query the data': 'the underlying data service connection is currently unavailable... ensure the data gateway service is running' | The agent hosting the Data Gateway is down | Start it (`systemctl reset-failed` first if the unit is `failed`); the gateway is RUNNING about 7 min later | L-AGENT-051, L-AGENT-097 |
| A monitor raises false alerts on agent status | It read the last (blank) line of `getStatus` | Take the first line that matches `^[A-Z_]+$` | L-AGENT-092 |
| A container on the agent host exits 255 'Address already in use' after a reboot | A dynamic address took another service's static IP | Fixed addresses for every service, or an `ip_range` that excludes them | L-ENV-069 |
| `$'\r': command not found` from a script deployed to the agent host | It was written on Windows with CRLF line endings | Write with `newline='\n'`; check with `bash -n` before deploying | L-ENV-023 |
| Agent fully down for ~5 min several times a day | Lifecycle crash/restart loop | Investigate agentcore.log; do not trust one read | L-AGENT-077 |
| Jobs queue ~5 min right after a selection change | Engine rollover | Change selections between lanes | L-AGENT-042 |
| Isolated `500 CMN_001` on one package URL while deploying | Transient download error | Wait; it retries | L-AGENT-027 |
| 'No space left on device' while lookup caches build | Cache size = declared port precision x rows | Smaller precisions, a filtered lookup query, a cache directory with headroom | L-CDI-281 |
| `Address verification library error (-12000)` 'insufficient memory... Review the preload properties' | Preload and memory settings exceed the DTM or its container | Lower the preload or raise the DTM memory | L-AGENT-116 |
| Disk thrash (load above 100, IO pressure ~98 %) under a cap you did not set | A hyphenated slice name nests the agent under a parent slice's MemoryMax | Slice names without hyphens; read the real cgroup's caps | L-AGENT-110 |
| 500 'Error while validating Runtime Environment detail [<reId>]' on catalog-source create | RE-nested `readyToRun` false | Re-check per-agent state; create with the full header set | L-AGENT-022 |

### 3.4 Agent command and API errors

| Signature | Cause | Fix | Lesson |
|---|---|---|---|
| 'Cannot connect to the Agent.' on `configureToken` | Daemon not started | `infaagent startup` first | L-AGENT-002 |
| 'cannot open./version.sh' / 'cannot open./agent_start.sh' | Script run by absolute path; relative sourcing | `cd` into agentcore; `WorkingDirectory=` | L-AGENT-006, L-AGENT-009 |
| `SingularApplicationLock: Cannot acquire lock` | Two agent JVMs | One supervisor; no `Restart=` next to a manual start | L-AGENT-008 |
| `readyToRun: false` in `GET /api/v2/runtimeEnvironment` | Stale list value | `GET /api/v2/agent/<agentId>` | L-AGENT-021 |
| 403 APP_13401 / 500 CMN_001 under `/api/v2/agent/*` | Router artifacts (bogus twins identical) | Cite neither way; use the selections route | L-AGENT-031 |
| 403 REPO_38225 on `DELETE /api/v2/agent/<id>`; 405 on `POST /api/v2/agent/<id>` (rename) | The agent is the only member of a runtime that connections or tasks use | Reinstall on the same host into that runtime: the id is reused | L-AGENT-111 |
| The login HTML page from `.../selections/ui` | `INFA-SESSION-ID` sent | `IDS-SESSION-ID: <v2 icSessionId>` | L-AGENT-039 |
| 'You have exceeded your monthly limit of 10,000 jobs.' | Org job cap reached | [11 / 03](../11-ipu-metering-licensing/03-entitlement-licenses-job-caps.md) | L-IPU-041 |

## 4. Host-side diagnostics

```bash
# who and where
pgrep -c -f 'agentcore[.]impls[.]MainApp'                      # 1 per install dir
systemctl status <unit>; cat /proc/<agentcore pid>/cgroup        # /system.slice/<unit>.service
su - <agentuser> -c 'cd <agent_home>/apps/agentcore &&./consoleAgentManager.sh getstatus'
ls <agent_home>/apps/                                            # what was actually delivered
# pressure
free -g; swapon --show; df -h <agent_home>; cat /proc/pressure/cpu /proc/pressure/memory
journalctl -k --since '-2h' | grep -i 'out of memory'
cat /sys/fs/cgroup/system.slice/<unit>.service/memory.events
# ports and libraries
ss -ltnp | grep -E ':(7080|7443|7005|14479|5432|14[0-9]{3})\b'
ldd <agent_home>/apps/Data_Integration_Server/<ver>/ICS/main/bin/rdtm/pmdtm | grep 'not found'
# logs (agentcore.log timestamps are 'YYYY-MM-DD HH:MM:SS' with a space, not an ISO 'T')
grep 'Service Status Distribution' <agent_home>/apps/agentcore/agentcore.log | tail -3
grep -E 'op:testConnection|adpId:' <agent_home>/apps/Data_Integration_Server/logs/tomcat/tomcat_<ver>.log | tail
ls -t <agent_home>/apps/Data_Integration_Server/logs/s_mtt_<taskId>_*.log | head -1
ls -t <agent_home>/apps/Database_Ingestion/logs/tasks/ | head -3
# status keyword: the first line, not the last
su - <agentuser> -c 'cd <agent_home>/apps/agentcore &&./consoleAgentManager.sh getstatus' | grep -m1 -E '^[A-Z_]+$'
# which DIS version is running, and its DTM pool
for p in $(pgrep -u <agentuser> java); do tr '\0' '\n' < /proc/$p/cmdline | grep -oE 'apps/Data_Integration_Server/[0-9.]+'; done | sort -u
grep -h 'maxDTMProcesses(poolSize)' <agent_home>/apps/Data_Integration_Server/logs/tomcat/tomcat_*.log | tail -1
# is the memory cap real?
ps -eo pid,cgroup,rss,args | grep -i infa | grep -v <agent-slice>      # must print nothing
cat /sys/fs/cgroup/<agent-slice>/memory.events /sys/fs/cgroup/<agent-slice>/memory.pressure
```

For a JDBC question, reproduce outside IDMC with the agent's own JDK and the same URL, then compare with the database's
auth log (L-CONN-052, 2026-08-20).

## 5. Evidence rules that saved days

- **Router artifacts prove nothing.** An error code that a bogus twin path also returns (APP_13401, CMN_001 under
  `/api/v2/agent/*`) is not evidence either way (L-AGENT-031, 2026-07-26).
- **A moving error is progress.** DIS, then Connector_Service, then a driver error means each gate is falling in turn
  (L-AGENT-026, 2026-07-26).
- **RUNNING is a deployment signal.** Only a passing test or a job proves an engine is usable (L-AGENT-023, 2026-07-26).
- **A test is a handshake; a run that lands rows is the proof** (L-CONN-015, 2026-08-19).
- **Walls go stale.** After a re-provisioning, four APP_105060 walls vanished; re-test before escalating
  (L-AGENT-045, 2026-09-23).
- **Diagnose from both ends** (IDMC error plus the database's own log) when an error is ambiguous (L-CONN-048, 2026-08-18).
  A connection test that really reached PostgreSQL moves `pg_stat_database.sessions` by one (L-CONN-016).
- **Prove absence with bytes, not with new connections** (L-METHOD-123). A sampler that flagged only new
  outbound connections saw nothing while CLAIRE's Data Gateway sent queries over tunnels it keeps open, so the agent
  was judged idle; stopping it broke "Query the data" within 4 minutes. Compare per-socket byte counters
  (`ss -tinp`, bytes_sent and bytes_received) or `/proc/<pid>/io` deltas before and during one triggered request, then
  do a reversible stop test with the restart command ready.
- **Count before you assert.** Enumerate runtime environments and agents from the API before claiming "all N healthy"
  (L-AGENT-030, 2026-07-08).

## 6. Overturned beliefs that cost the most time

| Belief | Real cause | Lesson |
|---|---|---|
| Service and connector enablement is UI-only | The selections PUT does it | L-AGENT-079 -> L-AGENT-039 |
| JDBC V2 drivers need the upload-JAR UI | Other gates (native libraries, staging order, no restart) | L-CONN-077 -> L-CONN-051 |
| Adapter errors are permanent walls | Agent state; cleared after re-provisioning | L-AGENT-087 -> L-AGENT-045 |
| A cold PostgreSQL catalog cannot resolve objects | Object path format | L-CONN-084 -> L-CONN-028 |
| One BigQuery key format fits every engine | Formats differ by engine and pod | L-CONN-083 -> L-CONN-035 |
| Zero profiled columns is a stuck job or `readyToRun` | pmdtm dying on a missing library (exit 127) | L-AGENT-059 |
| `downloads/` is a cache that can be cleared to free disk | Services run from it; pruning broke 14 of 20 | L-AGENT-055 -> L-AGENT-094 |
