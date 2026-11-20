# Process Server on a Secure Agent

**Answers:** Whether you need the CAI Process Server on an agent; how to enable it headless and prove it runs; how it fails (port 5432, a deleted Tomcat context, a missing keystore) and how to repair it; how to keep restarts and upgrades safe; how to run two agents on one host.

**Read when:** before running a process on a Secure Agent, after an agent upgrade or reboot, or when the process engine restart-loops.

**Key rules:**
- Processes that call only public APIs run on the Cloud Server and need no Process Server (L-CAI-056).
- 'Enabled' is not 'running': check `https://localhost:7443/process-engine/status` (200, body `2`) on the agent host (L-CAI-067, L-CAI-068).
- The embedded PostgreSQL is hard-wired to 5432: move it when another Postgres is there, and guard the port after every upgrade (L-CAI-069, L-CAI-072).
- On a shared host keep the engine off on the second agent, or give it its own port and owner-scoped guards (L-AGENT-013, L-CAI-074).

**Related:** [CAI Runtime](02-cai-runtime-invoke-urls-control.md) · [CAI Connections & Connectors](03-cai-connections-connectors-salesforce-oauth.md) · [CAI Troubleshooting](05-cai-troubleshooting-stuck-assets.md) · [Secure Agent - Install, Run & Tune](../02-secure-agent/01-secure-agent-install-run-tune.md) · [Lessons: CAI](lessons.md)

**Last verified:** 2026-11-20

> **Summary.** The CAI Process Server (engine `process-engine`) is only needed for agent-bound processes; processes
> that call public APIs run on the Cloud Server. It can be enabled headless through the runtime-environment
> selections PUT, but "enabled" is not "running": verify `https://localhost:7443/process-engine/status` (200, body
> `2`) and the agent details. Its embedded PostgreSQL is hard-wired to port 5432, which wrecks the install on any host
> that already runs a Postgres there, and its `deploy.sh` can delete the Tomcat context. Both are repairable in place;
> guard the port after every auto-upgrade and keep the engine off on a second agent that shares the host.

---

## 1. Do you need it?

| Need | Engine on the agent? |
|---|---|
| Processes that only call public cloud APIs | No: publish them to the Cloud Server (L-CAI-056) |
| Processes that reach private hosts, use event-based connectors, sign with local keys, or use RSA encrypt/decrypt | Yes |
| On-agent invoke and restadmin (`/process-engine/...`) | Yes |
| A second agent on a host that already runs one engine | Keep it off (section 8) |

Cloud-published processes never touch the agent's engine or its database (L-CAI-042). Entitlement for CAI shows up as
`process-engine` ("Process Server") in `GET /api/v2/agent/details/<agentId>`, not in the login `products[]` list
(L-CAI-077).

---

## 2. Enabling the engine

| Route | Result | Lesson |
|---|---|---|
| `GET https://<pod>.<domain>.informaticacloud.com/runtime/api/v2/runtimeEnvironment/<reId>/selections/ui`, edit the service flags, `PUT` the body back; both with `IDS-SESSION-ID: <v2 icSessionId>` (`INFA-SESSION-ID` returns the login HTML); read back | **works headless** | L-CAI-066 |
| `POST /api/v2/agent/service` (403 `APP_13401` or 500 `CMN_001`, both router artifacts), `/api/v2/agent/selectiveservices` (500), `POST /api/v2/agent` with `desiredStatus` (silent no-op), `/public/core/v3/runtimeEnvironments` (404) | do not use | L-CAI-109 (superseded by L-CAI-066) |
| Administrator > Runtime Environments > the agent > enable Application Integration > Save | the UI fallback | — |

After enablement the agent downloads `package-process-engine` (about 2-3 minutes) and starts the engine. Budget about
1.8-2 GB of RAM for it (it ran with `-Xmx1536M`) and watch the first start for a crash loop (L-CAI-075). Never select
every service at once on a small host: that pulled about 18 GB of packages and drove a 4-vCPU host to a load of 189
(see [Runtime Environments](../02-secure-agent/02-runtime-environments-services-connectors.md)).

**Enabled is not running (L-CAI-067).** The selection can read `enabled:true` while the engine restart-loops for days.
Always finish with the health checks below.

---

## 3. Health checks (L-CAI-068)

| Check | Healthy | Not healthy |
|---|---|---|
| `GET https://localhost:7443/process-engine/status` (or `http://<agentHost>:7080/process-engine/status`) on the agent host | 200, body `2` | 404 (webapp empty), connection refused (7443 not bound) |
| `GET.../process-engine/rt` | 401 (alive, auth-gated) | 404 |
| `GET <serverUrl>/api/v2/agent/details/<agentId>` | `process-engine` "Process Server" RUNNING/RUNNING | RESTARTING, DEPLOYING for a long time |
| `agentcore.log` | no repeated RESTARTING events | hundreds of RESTARTING events, many failed boots |
| Processes | the java process launched from `apps/process-engine/*/conf`; the embedded PostgreSQL up; deployed BPEL plans in state 2 | no engine PostgreSQL process |

Probe the agent host, not a cloud host root: a 404 from a cloud host says nothing about the engine. The agent itself
polls the status every 60 s. In agent details the engine is ready at `subState` "0", and the Process Server can take up
to 20 minutes to get there after a start, so give a start or restart a 20-minute deadline (L-AGENT-125, L-AGENT-139,
reported).

---

## 4. Failure anatomy (observed 2026-09-23/24)

| Fault | Mechanism | Symptom |
|---|---|---|
| Port 5432 collision (L-CAI-069) | Every engine script uses `localhost:5432/activevos`; `server_status.sh` is only `pg_isready -p 5432`. Another Postgres on 5432 answers, so each start logs a false "PostgreSQL database has started"; `prepareDB.sh` runs `db_init.sh` against the wrong database, fails, and deletes the engine's `data/PostGreSql` directory | Empty engine data directory; no engine PostgreSQL process; endless restarts |
| Context descriptor deleted (L-CAI-070) | `deploy.sh` runs `[ -d conf/Catalina/localhost ] \|\| mv host.name localhost`, then `rm -rf host.name`. If an empty `localhost/` already exists, `process-engine.xml` (allowLinking and the `jdbc/ProcessEngine` resource) is deleted instead of moved | Tomcat refuses the symlinked `WEB-INF/web.xml`; the webapp deploys empty in about 37 ms; every request, including `/process-engine/status`, is 404 |
| Keystore missing (L-CAI-070) | `conf/ae.keystore` and `ae.cacerts` absent under `apps/process-engine/conf` | Port 7443 never binds |

Check `ss -ltnp` for 5432 before enabling Application Integration on any host that runs application databases.

---

## 5. Repair procedure (L-CAI-071, proven 2026-09-24)

1. **Back up** `apps/process-engine/bin`, `conf` and `data` in one tar archive; that archive is the undo.
2. **Keystore.** If missing, copy `ae.keystore` and `ae.cacerts` from `<peVersion>/conf/certs` into
   `apps/process-engine/conf`.
3. **Move the database port.** Replace `localhost:5432/activevos` with a free port (for example 5433) in
   `<peVersion>/bin/*.sh` and in the context descriptor.
4. **Embedded PostgreSQL config.** In its `user.conf` set the same port and `listen_addresses = 'localhost'` (not
   `'*'`).
5. **Redeploy.** Stop the looping Tomcat, then re-run Informatica's own `deploy.sh` with the LCM environment
   variables captured from the live engine process. Expected: schema created, Liquibase updated, exit 0.
6. **Restore the context.** Put `conf/Catalina/localhost/process-engine.xml` back from the backup.
7. **Verify** with section 3: status 200, agent details RUNNING/RUNNING. Then publish or invoke one agent-bound
   process.

Result in the field: RUNNING for the first time since its install, and stable afterwards.

---

## 6. After agent upgrades: guard the port (L-CAI-072)

An auto-upgrade of the process engine ships a new version directory with the 5432 scripts again. Install a root cron
job (every 10 minutes) that re-applies the non-5432 port to the current version directory. The guard is tied to one
agent's install path: a second agent that runs its own engine needs its own copy, pointed at its own directory, and
its own engine ports configured.

---

## 7. Restart safety (L-CAI-073)

- Run the agent under systemd rather than from a remote-shell session (such a session's process tree dies on reboot).
- Add an orphan reaper as `ExecStartPre` and `ExecStopPost` in a drop-in for the agent unit, plus a 5-minute check.
  It kills orphaned engine processes (including a surviving engine PostgreSQL) and refuses to start, loudly, while
  engine ports such as 7005 and 14479 or `*.mv.db` files are still held.
- Proof: killing the agent core and its respawn loop, then restarting the unit, left 0 orphans and brought all 20
  engines back RUNNING in about 6 minutes, with CDC and CAI unaffected (2026-09-26).

---

## 8. Two agents on one host (L-CAI-074)

The engine binds 7080 and 7443, internal ports (7005, 14479) and its embedded PostgreSQL. A second agent's engine
clashes with the first one's, and the first agent's start guard refuses while those ports are taken. If CAI runs on
the Cloud Server, deselect the process engine on the second agent; diff `ss -ltnp` before and after each service is
added, and keep the second agent's own systemd limits (memory, CPU and IO weights) as described in
[Secure Agent - Install, Run & Tune](../02-secure-agent/01-secure-agent-install-run-tune.md).

**When the second agent must also run a Process Server** (L-AGENT-013): move its embedded Postgres to a free port
(for example 5434 beside an application Postgres on 5432) with its own port guard (L-CAI-072), and scope every
pre-start reaper and guard to its own install: count a port holder only if the PID belongs to that agent's OS user
(`stat -c %U /proc/<pid>`), and count `*.mv.db` lock files only under that agent's home. An unscoped guard ("any holder
of 7005/14479, any `*.mv.db`") refused every start of the first agent once the second agent's Process Server held 7005;
it surfaced only at the next reboot. After a reboot check the agent process (`pgrep -u <agentuser> -c -f
agentcore.impls.MainApp`), not the systemd unit: a `Type=forking` + `RemainAfterExit=yes` unit reads `active (exited)`
even when agentcore is dead.

---

## 9. Run history on the agent (L-CAI-052)

For processes deployed to the agent, run history sits in the engine's embedded PostgreSQL: database `activevos`,
tables such as `aeprocess` and `aeplan`, default local port 5432 (or the port you moved it to), default user
`bpeluser`. Read it over SSH with psql if you need it in a warehouse. It is empty for Cloud Server processes; use
Operational Insights for those ([CAI Runtime](02-cai-runtime-invoke-urls-control.md)).

---

## 10. On-agent endpoints (L-CAI-047, documented)

| Purpose | Path on `http(s)://<agentHost>:<port>` |
|---|---|
| Invoke (authenticated / anonymous) | `/process-engine/rt/<service>`, `/process-engine/public/rt/<service>` |
| SOAP 1.2 | `/process-engine/soap/<service>` (`?wsdl`); Swagger with `?swagger` on rt URLs |
| Runtime control | `/process-engine/restadmin/processes`, `/process-engine/restadmin/scheduler/schedules` (tenant `$public`) |
| Status | `/process-engine/status` |

Local defaults: `http://localhost:7080/process-engine/` and `https://localhost:7443/process-engine/`.

An anonymous process published to an agent answers on `http://<agentHost>:7080/process-engine/public/rt/<process>`
with no IDMC login, so keep that port local (bind or firewall it) and put an authenticating reverse proxy with an
allow-list of process names in front of any page that must call it (L-CAI-163).

---

## 11. Other agent-side notes

- **Start a stopped engine.** When the binaries are installed, a stopped Process Server can be started on the host
  (or toggled in the console); verify ports 7080/7443 and agent details (L-CAI-076). From REST, `POST
  /public/core/v3/agent/service` with the agent's `federatedId`, `serviceName` and `serviceAction` start or stop starts
  or stops one engine ([Secure Agent](../02-secure-agent/01-secure-agent-install-run-tune.md) §4.4; L-AGENT-124,
  reported).
- **Limits you can raise per agent** (L-CAI-189, reported): the message size limits (5 MB by default; the Cloud Server
  keeps 5 MB), the contribution and deployment-plan caches, and the JVM heap (`512M`/`1536M` by default) under
  Administrator > Runtime Environments > the agent > Process Server > JVM. The Shell and Email services start
  disabled. Restart the Process Server after a change.
- **Agent groups do not fail over state** (L-AGENT-137, reported): each node keeps instances in its own embedded
  PostgreSQL, so only stateless processes balance across a group. For a site failover, sync `apps/process-engine/ext`
  to the standby agents beforehand, move them into the group, then republish the processes.
- **Monitoring thresholds** for the Application Integration Console engine monitors, from one field setup, are in
  L-CAI-188 (reported); a CAI process can also count RUNNING engines per agent from `GET /api/v2/agent/details`
  (L-AGENT-136).
- **Crash-looping engines.** A Process Server whose embedded PostgreSQL data directory never initialised
  crash-loops; a minimal catalog-plus-DI agent ran fine with it disabled (L-CAI-075).
- **Shell steps.** A "Run a Shell Command" process step on an agent needs a one-time UI enablement of the Shell
  Service for that agent (L-CAI-053).
- **JDBC drivers.** `<agent_home>/apps/process-engine/ext` when a CAI JDBC connection leaves "JDBC Jar Directory" blank
  (L-CAI-065).
- **Monitoring.** The vendor Process Server Health dashboard needs the Monitor role.

---

## 12. Overturned beliefs (this area)

| Belief | Believed | Overturned by |
|---|---|---|
| Enabling the Process Server is a UI-only Administrator toggle | 2026-07-09 to 09-27 | L-CAI-066 (L-CAI-109) |
| A "validation failed" 404 on the status probe means the engine is broken | 2026-07-04 | L-CAI-068 (L-CAI-107) |
| CAI is not provisioned (no Process Server runtime, products[] shows Integration Cloud only) | 2026-07-04/05; 2026-09-21 | L-CAI-077 (L-CAI-108) |
