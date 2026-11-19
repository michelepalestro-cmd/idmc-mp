# Secure Agent and runtime environments: cheat sheet

Installing, registering, supervising, sizing and tuning a Secure Agent, and choosing the services and connectors its
runtime environment runs; it applies whenever work must reach a private network or an agent is slow, down or missing.

**Start with:** `/idmc-mp:health-check` (read-only inventory of runtimes, agents and engines), `/idmc-mp:tune-agent`
for sizing, and `toolkit/lib/idmc_runtime_selections.py` (`show` / `set` / `restore`) for services and connectors.
Open first: [Secure Agent: install, run and tune](01-secure-agent-install-run-tune.md).

## What works (headless)

| Task | How (exact route/tool/command) | Lesson |
|---|---|---|
| Preflight | v3 login, `GET <serverUrl>/api/v2/org`, `/api/v2/agent`, `/api/v2/agent/<agentId>`, `/api/v2/agent/details/<agentId>` | L-AGENT-032 |
| Installer and token | `GET <serverUrl>/api/v2/agent/installerInfo/linux64` (`icSessionId`) -> `downloadUrl`, `installToken` (pins the org; mint fresh) | L-AGENT-001 |
| Install and register | Non-root user, `./agent64_install.bin -i silent`, `infaagent startup` **first**, then from `apps/agentcore`: `consoleAgentManager.sh configureToken <idmc-user> '<installToken>'` | L-AGENT-002, L-AGENT-006 |
| Run as a service | systemd `Type=forking`, `RemainAfterExit=yes`, `KillMode=control-group`, `WorkingDirectory=<agent_home>/apps/agentcore`, no `Restart=` | L-AGENT-009 |
| Health | Per agent: `/api/v2/agent/<agentId>` (`active`, `readyToRun`) and `/agent/details/<agentId>` (`agentEngines[]`, `subState` 0) | L-AGENT-020, L-AGENT-125 (reported) |
| Select services and connectors | `GET` then `PUT https://<pod>.<domain>.informaticacloud.com/runtime/api/v2/runtimeEnvironment/<reId>/selections/ui` with `IDS-SESSION-ID: <v2 sid>`; GET body = undo | L-AGENT-039 |
| List / create a runtime | `GET`/`POST <serverUrl>/api/v2/runtimeEnvironment`; create needs `"@type":"runtimeEnvironment"`; DELETE works | L-AGENT-035, L-AGENT-130 (reported) |
| DTM heap and DTM pool | Cloud-side legacy form `/runtime/app/agent.do` (read `displayUpdate`, save `actionMethod=update`); rows packed in `configFormJson` | L-AGENT-088, L-AGENT-099, L-AGENT-127 (reported) |
| Reinstall on the same host | `consoleAgentManager.sh configureTokenWithRuntime <user> <token> <runtimeEnvironment>` reuses the agent id | L-AGENT-111 |
| Move to a bigger host | rsync the install dir; same OS user, UID/GID, path, hostname; same agent id | L-AGENT-102 |
| Memory / CPU caps | `systemctl set-property <unit> MemoryHigh=... MemoryMax=... CPUWeight=...` | L-AGENT-017 |
| Two agents on one host | Own OS user, home, unit, guard; one Process Server per host | L-AGENT-015, L-AGENT-090 |

## What doesn't work, and the workaround

| Wall | Workaround | Lesson |
|---|---|---|
| `POST /api/v2/agent/service`, `/api/v2/agent/selectiveservices`, `POST /api/v2/agent/<id>` with `desiredStatus`, v3 `runtimeEnvironments` | The selections PUT; `APP_13401` / `CMN_001` there are router artifacts | L-AGENT-044, L-AGENT-031 |
| Selections with `INFA-SESSION-ID` -> login HTML 200 | `IDS-SESSION-ID: <v2 icSessionId>` | L-AGENT-039 |
| `configureToken` -> 'Cannot connect to the Agent.' | Start the daemon first | L-AGENT-002 |
| `consoleAgentManager.sh` by absolute path -> 'cannot open ./version.sh' | `cd <agent_home>/apps/agentcore` first | L-AGENT-006 |
| RE list `agents[].readyToRun: false` | Stale; read per agent and `getstatus` | L-AGENT-021 |
| Host edit of `pmrdtm.cfg` / `tomcat.cfg` | Lost on the next DIS version roll; set it via `agent.do` | L-AGENT-056 |
| Agent started by a cloud run-command | Dies with the extension scope / on reboot; use the unit | L-AGENT-011 |
| `DELETE /api/v2/agent/<id>` -> 403 `REPO_38225`; rename `POST` -> 405 | Reinstall into the same runtime; rename via the `agent.do` name field | L-AGENT-111, L-AGENT-129 (reported) |
| `PUT /api/v2/runtimeEnvironment/<id>` -> 500 `CMN_001` | No v2 rename of a runtime | L-AGENT-130 (reported) |
| CLAIRE "Query the data" gateway by ticking services | It is a licence package; keep its agent running | L-AGENT-097, L-AGENT-051 |
| Hosted Agent reaching a private host | A Secure Agent on that network | L-AGENT-036, L-AGENT-037 |

## Fastest safe path

1. Prove the org (`/idmc-mp:connect`, see [Login, orgs and access](../01-login-and-orgs/README.md)). **Proof:** org id
   printed; mint the install token in that org (L-AGENT-001).
2. Preflight (`/idmc-mp:health-check`). **Proof:** agents and engines listed; `[]` = install one (L-AGENT-032).
3. Egress from the future host. **Proof:** login GET 405, domain root 301; timeout/TLS = fix firewall first (L-AGENT-003).
4. Size before selecting: sum every `-Xmx`, >= 16 GB RAM with DI on, ~20 GB free disk, swap (L-AGENT-052, L-AGENT-109).
5. Token, install, `infaagent startup`, `configureToken`. **Proof:** `getstatus` READY, `isConfigured` true,
   `GET /api/v2/agent` `active: true` in this org (L-AGENT-001, L-AGENT-002).
6. Hand over to the systemd unit. **Proof:** `pgrep -c -f 'agentcore[.]impls[.]MainApp'` = 1, `systemctl restart` once
   still READY (L-AGENT-009, L-AGENT-007).
7. Select only what the scope needs, save the GET body, PUT, GET again. **Proof:** flags read back; engines RUNNING with
   `subState` 0 tens of minutes later (L-AGENT-039, L-AGENT-024, L-AGENT-125 (reported)).
8. One connection test per engine. **Proof:** `GET /api/v2/connection/test/<connId>` passes; RUNNING alone proves nothing (L-AGENT-023).
9. Tune by measurement: queue wait in `tomcat_<ver>.log`, then raise `maxDTMProcesses` in a drained window. **Proof:**
   `poolSize=<N>` on the running DIS (L-AGENT-099, L-AGENT-121).

## Top traps

- Pruning or moving `<agent_home>/downloads/` -> 14 of 20 services ERROR ('./status.sh: not found') -> services run from
  it; restart and wait ~10 min, never prune (L-AGENT-094).
- Selecting every service on a small host -> ~18 GB downloads, load ~189, swap full (L-AGENT-041).
- Every selections PUT rolls DIS, Mass Ingestion and Connector_Service -> jobs queue ~5 min; change between lanes (L-AGENT-042).
- Parallel lanes stuck at 2 DTMs -> default `maxDTMProcesses` = 2 -> raise cloud-side (L-AGENT-099).
- `agent.do` save -> DIS restarts ~1.5 min later and kills every job on the agent -> drain first (L-AGENT-121); flat
  form POST -> 500 `CMN_001` -> pack rows into `configFormJson` (L-AGENT-127 (reported)).
- One JVM OOM-killed -> whole unit `failed` (`Restart=no`, `OOMPolicy=stop`) -> `systemctl reset-failed` + start; drop-in
  `OOMPolicy=continue` (L-AGENT-101, L-AGENT-108).
- `SingularApplicationLock`, real `readyToRun: false` -> two agent JVMs -> one supervisor only (L-AGENT-008).
- Connection-test errors rotating between engines -> OOM churn, not configuration -> cap the agent, fewer services (L-AGENT-052).
- `pmdtm` exit 127 -> missing native library (`libidn.so.11`), not heap; 137 = OOM kill (L-AGENT-061, L-AGENT-059).
- Process Server -> embedded Postgres on hardcoded 5432; ports 7005/7080/7443 static -> one per host (L-AGENT-071, L-AGENT-090).
- agentcore dies ~40 s after each start post-reboot -> stale `gunicorn.pid` -> move `.pid` files aside pre-start (L-AGENT-095).
- Every hosted connection fails `APP_105060` naming the hosted group -> Hosted Agent outage -> fail over tasks **and**
  connections to a Secure Agent (L-AGENT-117).

## Go deeper

- [Secure Agent: install, run and tune](01-secure-agent-install-run-tune.md): install, systemd, two agents, memory, DTM pool, Process Server, post-boot checklist.
- [Runtime environments: services and connectors](02-runtime-environments-services-connectors.md): runtime types, engine list, selections PUT, dependencies, Hosted Agent failover.
- [Lessons: Secure Agent](lessons.md): every current and superseded `L-AGENT` lesson.
- [Troubleshooting: the four gates](../03-connections/03-troubleshooting-the-four-gates.md): host, engine, adapter, driver signatures.
- [Bootstrap](../reference/playbook/03-bootstrap.md): zero to a running job.
