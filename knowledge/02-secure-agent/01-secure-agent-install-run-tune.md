# Secure Agent: install, run and tune

**Answers:** How do I install, register and supervise a Secure Agent without the UI? How big must its host be? How do I
change engine settings (DTM heap, DTM pool) so that they survive upgrades? How do two agents share one host? What do I
check after a resize or a reboot, and where may I free disk?

**Read when:** before you install, resize or reboot an agent host; before you select many services; when jobs queue,
engines flap or the agent will not start; before you delete anything on an agent host.

**Key rules:**
- Install and register headless, then run the agent under a systemd unit (`Type=forking`, no `Restart=`), never from a
  cloud run-command (L-AGENT-002, L-AGENT-009, L-AGENT-011).
- Size the host before you select services: sum every `-Xmx`, budget 16 GB RAM or more and about 20 GB free disk; a
  17-service agent needs about 11-12 GB (L-AGENT-052, L-AGENT-093).
- Set engine properties (DTM heap, `maxDTMProcesses`) cloud-side (the UI first, `agent.do` last, §6.1) and verify them on the
  running JVM; a host edit lands in one version directory and is lost (L-AGENT-088, L-AGENT-056).
- The DTM pool defaults to 2: a controller that starts more tasks at once gets no speed-up until you raise it
  (L-AGENT-099).
- Never prune or move `<agent_home>/downloads/`: installed services run from it (L-AGENT-094).
- On a shared host, scope every guard and reaper to its own agent user, and run only one Process Server per host
  (L-AGENT-096, L-AGENT-090).

**Related:** [02 Runtime Environments](02-runtime-environments-services-connectors.md) ·
[Troubleshooting: the four gates](../03-connections/03-troubleshooting-the-four-gates.md) ·
[Process Server on a Secure Agent](../07-app-integration/04-process-server-on-a-secure-agent.md) ·
[Performance, Concurrency & Job Caps](../04-mappings/06-performance-concurrency-job-caps.md) ·
[Lessons: Secure Agent & Connections](../03-connections/lessons.md)

**Last verified:** 2026-11-03 (evidence 2026-06-27 to 2026-11-03; live installs on four orgs, two agents on one host).

> A Secure Agent is an `agentcore` supervisor plus one JVM-based engine per selected service, on a host you own.
> Installing and registering it is headless; only the shell on the host is manual. Most "IDMC is broken" incidents on an
> agent host are host problems: RAM, disk, native libraries, orphaned processes, a duplicate JVM or a stale pid file.
> Host reach (IAP hops, cloud run-command) is in
> [How Claude Reaches and Drives IDMC](../14-working-with-claude/01-how-claude-reaches-and-drives-idmc.md) §7.

Placeholders: `<serverUrl>` = the v2 base from the v2 login (`https://<pod>.<domain>.informaticacloud.com/saas`);
`<agent_home>` = the agent install root, by default `~/infaagent` of the install user; `<agentuser>` = that OS user;
`<unit>` = the systemd unit name; `<agentId>`, `<reId>` = ids read live, never copied across orgs.

---

## 1. What you are running

| Piece | What it is | Where |
|---|---|---|
| `agentcore` | The supervisor JVM (`agentcore.impls.MainApp`), started by `infaagent startup`, respawned by the `agent_start.sh` loop | `<agent_home>/apps/agentcore/` |
| Engines | One app per selected service: `Data_Integration_Server`, `Connector_Service`, `Database_Ingestion`, `process-engine` and so on | `<agent_home>/apps/<Service>/<version>/` |
| Runtime environment | The org-side group the agent belongs to; the agent creates its own on registration | Administrator, `GET /api/v2/runtimeEnvironment` |
| Selections | Which services and connectors the runtime environment runs | `.../runtime/api/v2/runtimeEnvironment/<reId>/selections/ui` ([doc 02](02-runtime-environments-services-connectors.md)) |

A runtime environment is a network position, not a setting: the agent reaches only what its host's network reaches
(L-AGENT-036, 2026-07-26; L-AGENT-037, 2026-07-08). MDM SaaS never runs on an agent (L-AGENT-050, 2026-07-06), and
Data Quality runs inside the Data Integration Server (L-AGENT-049, 2026-06-27), and so does on-agent address
verification: there is no separate engine; the USA reference files (`.MD6`, about 4.1 GB, so a search for `*.MD` misses
them) sit in `apps/Data_Integration_Server/data/avdata/FileSetA/`, the licence file `data/avLicenseFile/AV_IDMC_IPU.LIC`
is fetched again at every start (on-agent verification is IPU-metered), and the job log prints NumFunctionServers,
MaxMemoryMegabytes and preload use (1 function server, 8,192 MB, 0 MB preload by default). Measure throughput per
pipeline (160 and 550-580 addresses/s per DTM in two shapes) and scale out over disjoint key ranges (L-AGENT-116,
2026-11-01).

## 2. Before you touch a host

**Preflight in five calls** (L-AGENT-032, 2026-07-26):

| Call | What it tells you |
|---|---|
| `POST https://<domain>.informaticacloud.com/saas/public/core/v3/login` | Org, pod (`products[].baseApiUrl`) |
| `GET <serverUrl>/api/v2/org` | Both org id shapes |
| `GET <serverUrl>/api/v2/agent` | Any agents at all? `[]` = entitlement unresolved, install one |
| `GET <serverUrl>/api/v2/agent/<agentId>` | Per-agent `active`, `readyToRun`, `version` |
| `GET <serverUrl>/api/v2/agent/details/<agentId>` | `agentEngines[]` and each `agentEngineStatus.status` |

The whole sequence from an empty org to a running job, in order: log in and pick the plane; confirm org and pod; read
the gate (agents, `agentEngines[]`, per-agent `readyToRun`); get the install token; size the host, install and register
(the only step that needs a shell); read the runtime environment the agent created; select services, then connectors,
then stage drivers; create and test connections; create tasks and schedules; run with `POST /api/v2/job`; monitor
(L-AGENT-033, 2026-09-28).

**Egress check from the future host** (L-AGENT-003, 2026-08-18): a GET on the login endpoint answering 405 (POST-only),
a package path answering 404 and the `https://<domain>.informaticacloud.com` root answering 301 prove outbound HTTPS.
A timeout or TLS error is a firewall or proxy problem; fix it first.

**Host requirements.** Vendor minimums (documented, not re-measured): Linux at least 11 GB free, a `libidn.so.11`, a
non-root install user; Windows 4 CPU, 16 GB RAM, 5 GB free on a 250 GB disk, MSVC++ 2015 runtime, outbound 443
(L-AGENT-005, 2026-08-15). Field rules that held up (L-AGENT-052, 2026-09-12):

- Sum the `-Xmx` of every service you will select before selecting it; 23 engines on a 7.8 GiB host reserved ~9.2 GB.
- Budget at least 16 GB RAM once Data Integration is on (inferred from observed heaps, not vendor guidance).
- Keep about 20 GB free disk: the agent home reached 25 GB, 19 GB of it the `downloads/` package store, which services
  run from and which is never pruned (L-AGENT-094).
- Add swap; with none, every spike goes straight to the OOM killer.
- Never co-locate a full engine set with production databases on a small host.
- A 17-service agent plus a second agent on 4 vCPU ran at load 12-31 with swap full; on 8 vCPU the same work ran at
  load 11 (L-ENV-069).

### 2.1 Resize or reboot an agent host, then run the post-boot checklist (L-ENV-069)

1. Announce the window to every session and job that uses the host (BI publish chains, lane controllers, catalog
   scans) and drain the lane controller. A resize is spend: get the approval first.
2. Azure: `az vm resize -g <resource-group> -n <vm-name> --size <new-size>` (from git-bash
   `python -m azure.cli vm resize...`). When `az vm list-vm-resize-options` lists the target size, it is one reboot of
   about 10 minutes with no deallocation; a static public IP and the OS and data disks are kept, and a `CanNotDelete`
   lock does not block it. Rollback is the same command with the old size (L-ENV-069).
3. After the boot, run the fixed **post-boot checklist** below, in order, before anyone calls the host healthy. Keep it
   as one script that prints a line per check.

| # | Check | Command or call | What it catches |
|---|---|---|---|
| 1 | Host | `nproc; free -m; swapon --show; cat /proc/loadavg` | the new size took; swap state |
| 2 | Agent process, not the unit | `pgrep -u <agentuser> -c -f agentcore.impls.MainApp` | a `Type=forking` + `RemainAfterExit=yes` unit reads `active (exited)` while agentcore is dead; a second unit ordered `After=` the first stays inactive for about 2 minutes |
| 3 | Stale pid files | with no agent process alive, move every `apps/**/*.pid` aside before the start (pre-start hook, §4.5) | a stale AI Agent Runtime `gunicorn.pid` killed agentcore about 40 s after every start (L-AGENT-095) |
| 4 | Agent online, engines up | `GET /api/v2/agent/<agentId>` (`active`, `readyToRun`) and `GET /api/v2/agent/details/<agentId>`; DIS `subState` 0 | any engine not RUNNING (L-AGENT-075) |
| 4a | Connections | `GET /api/v2/connection/test/<connId>` for one connection per engine | an engine that reads RUNNING but does not serve (L-AGENT-023) |
| 5 | Process Server | `curl -sk -o /dev/null -w '%{http_code}' https://localhost:7443/process-engine/status` = 200; `ss -ltn` shows its ports and its embedded Postgres port | a Process Server bound to the wrong Postgres (L-AGENT-089) |
| 6 | CDC | `GET /dbmi/api/v1/task/<taskId>/job` per CDC task; slot lag `pg_wal_lsn_diff(pg_current_wal_lsn, confirmed_flush_lsn)` | jobs pass through `awaiting_auto_restart` and return to running by themselves about 20 minutes after boot: do not redeploy them |
| 7 | Containers on the same host | `docker ps -a --filter status=exited --filter status=restarting` | a compose service with a dynamic address took another's static `ipv4_address` ('Address already in use', exit 255): give every service a fixed address, or an `ip_range` that excludes the static ones |
| 8 | Lane controller and speed mode | the controller's health endpoint; its persisted speed mode (economy unless a timed fast window is still meant to run); then lift the drain | a controller that came back drained, or in the wrong mode (L-IPU-054) |
| 9 | One lane smoke | the smallest lane, once | `/tmp` is cleared at boot: recreate anything that lived there |

A 4 -> 8 vCPU resize (same 32 GiB) made per-task runtimes fall up to 3x (a database-ingest mapping from a 123 s to a
41 s median), but a mapping consolidation went live the same day, so the gain is not the resize's alone
(L-ENV-069).

## 3. Install and register headless

**The route** (L-AGENT-001, 2026-09-28):

```
GET <serverUrl>/api/v2/agent/installerInfo/linux64          # or /api/v2/agent/installerInfo/<platform>
icSessionId: <v2 session>
-> 200 {"downloadUrl": "...", "installToken": "<122 chars>", "checksumDownloadUrl": "..."}  # the token pins the agent to THIS org
```

Mint the token in the org the agent must join, and use it fresh: the vendor guide says install tokens expire after
24 hours, and a token saved in July was expired in August. The v3 agent paths return 404.

- **Get the token without printing it.** `idmc_session.py get` hides secrets in what it prints, so the token shows as
  `<redacted:122>`. Save the whole answer to a private file instead, then read the token from that file on the agent
  host: `python3 toolkit/lib/idmc_session.py get v2 /api/v2/agent/installerInfo/linux64 --save-to
  ~/.idmc_toolkit/agent_installer.json` (mode 0600, refuses a path inside the plugin). Without the toolkit: in IDMC,
  Administrator > Runtime Environments > **Generate Install Token**, copy it once and paste it straight into
  `configureToken`.
- **Checksum.** The same answer carries `checksumDownloadUrl`, a `.sha256` file next to the installer; both are public
  downloads that need no session (L-AGENT-131, reported).
- **Expired or wrong-org token.** `configureToken` does not answer `Login succeeded`, and the agent never shows up in
  `GET /api/v2/agent`: mint a fresh token in the right org and run `configureToken` again (L-AGENT-001).
- **Before the install,** prove the host reaches IDMC over HTTPS; a timeout or TLS failure is a firewall or proxy
  problem to fix first (L-AGENT-003).

**The sequence** (L-AGENT-002, 2026-09-28): the order matters; registering before the daemon runs fails.

```bash
sudo useradd -m <agentuser>                      # the installer refuses root
sudo -iu <agentuser>
curl -fsSLo agent64_install.bin '<downloadUrl>'  # then verify the published SHA-256
sha256sum agent64_install.bin
chmod +x agent64_install.bin
./agent64_install.bin -i silent                  # the file is named agent64_install_ng_ext.<build>.bin
                                                 # installs into ~/infaagent; another folder: add
                                                 # -DUSER_INSTALL_DIR=/opt/infaagent (L-AGENT-140, reported)
cd ~/infaagent/apps/agentcore                    # consoleAgentManager must run from here (see below)
nohup ./infaagent startup >/dev/null 2>&1 &     # START FIRST (or start the systemd unit, section 4)
./consoleAgentManager.sh configureToken <idmc-user> '<installToken>'   # -> Login succeeded
./consoleAgentManager.sh getstatus               # -> READY
./consoleAgentManager.sh isConfigured            # -> true
```

Then check the cloud side: `GET /api/v2/agent` shows the agent `active: true` in the expected org, and a runtime
environment for it now exists. Read `GET /api/v2/agent/details/<agentId>`: a fresh agent can show a single telemetry
engine until services are selected (one showed exactly one) ([doc 02](02-runtime-environments-services-connectors.md)).
An idle, registered agent uses about 1 GB RAM (L-AGENT-053, 2026-07-04).

**Reinstall on the same host** (L-AGENT-111, 2026-10-29): `consoleAgentManager.sh configureTokenWithRuntime <user>
<token> <runtimeEnvironment>` from a fresh install directory registered as the existing (stopped) agent id in that
runtime environment, matched by host name; its connections needed no edit and tested green. Move the old install
directory aside so nothing starts two installs with one id. `DELETE /api/v2/agent/<id>` is refused with 403
REPO_38225 while the agent is the only member of a runtime environment that connections or tasks use, and a rename
(`POST /api/v2/agent/<id>`) returns 405.

**Traps**

| Symptom | Cause | Fix |
|---|---|---|
| `Cannot connect to the Agent.` on `configureToken` | Daemon not started | `infaagent startup` first (L-AGENT-002) |
| `cannot open./version.sh` | `consoleAgentManager.sh` called by absolute path; it sources files relative to `$PWD` | `cd <agent_home>/apps/agentcore` first (L-AGENT-006, 2026-07-26) |
| Installer "hangs", blank logs | Disk full: the installer is ~382 MB and needs ~2 GB to unpack; nohup buffering hides output | Free disk, re-run (L-AGENT-004, 2026-07-26) |
| `readyToRun` really false, no packages delivered | Two agent JVMs fighting the lock (`SingularApplicationLock`) | One supervisor only; `ls <agent_home>/apps/` shows what arrived (L-AGENT-008, 2026-07-26) |
| Phantom "second JVM" | `pgrep -af... \| wc -l` counts your own SSH command | `pgrep -c -f 'agentcore.impls.MainApp'` must print 1 per install dir (L-AGENT-007, 2026-09-28); the bracketed form `'agentcore[.]impls[.]MainApp'` cannot match any shell that carries the pattern |

## 4. Run it as a service

### 4.1 The systemd unit

A naive unit fails silently: `infaagent` forks and resolves its scripts relative to its own directory, so
`systemctl is-active` reports inactive while the agent runs, and a reboot leaves it down (L-AGENT-009, 2026-09-28).

```ini
# /etc/systemd/system/<unit>.service
[Unit]
Description=Informatica Secure Agent (<agentuser>)
After=network-online.target
Wants=network-online.target

[Service]
Type=forking
RemainAfterExit=yes
User=<agentuser>
WorkingDirectory=<agent_home>/apps/agentcore
ExecStart=<agent_home>/apps/agentcore/infaagent startup
ExecStop=<agent_home>/apps/agentcore/infaagent shutdown
KillMode=control-group
TimeoutStopSec=300
# No Restart= : agent_start.sh already respawns agentcore, and a second supervisor
# fights the singleton lock (L-AGENT-008).

[Install]
WantedBy=multi-user.target
```

Switch over safely: stop any manually started instance, confirm `pgrep -c -f 'agentcore.impls.MainApp'` prints 0,
`systemctl daemon-reload && systemctl enable --now <unit>`, confirm exactly one JVM and `getstatus` READY, then
`systemctl restart <unit>` once to prove the unit really controls it.

### 4.2 Never leave an agent in a cloud run-command scope

An agent started through `az vm run-command` lives in the run-command extension's transient cgroup (an
`...RunCommandLinux.slice` / `enable_<n>.scope`). Nothing supervises it, it is exposed to the extension's lifecycle, and
it does not come back after a reboot (L-AGENT-011, 2026-09-28). Check where it lives:

```bash
cat /proc/$(pgrep -f 'agentcore.impls.MainApp' | head -1)/cgroup   # want: /system.slice/<unit>.service
systemctl status <unit>
```

### 4.3 No systemd? An @reboot entry

`@reboot sleep 30 && <agent_home>/apps/agentcore/infaagent startup` in the agent user's crontab (older installs use
`infaagent.sh startup`) is a zero-cost, reversible self-heal; without it a reboot silently stops every schedule
(L-AGENT-010, 2026-07-08). Prefer the unit.

### 4.4 Restarting without losing the agent

- Restart detached: `infaagent shutdown`, then `nohup infaagent startup &` (or `setsid ./agent_start.sh`, or tmux, or the
  unit). A dropped SSH or IAP session in the middle of a startup can leave the agent down (L-AGENT-012, 2026-07-06).
- After any restart: all engines RUNNING, DIS `subState` 0, one connection test green (L-AGENT-075, 2026-06-27).
- Break-glass ladder: restart the agent, reboot the host, re-register (new token), reinstall; check each rung from both
  sides, the per-agent API and on-host `getstatus` (L-AGENT-010, 2026-07-08).
- A locked-out IDMC user does not stop the agent: it has its own agent token, schedules keep running, only REST triggers,
  exports and UI work stop (L-AGENT-014, 2026-08-19).

### 4.5 Make restarts safe: reap orphans, guard ports

`agent_start.sh` respawns agentcore in place, which can strand engine JVMs and the Process Server's embedded Postgres.
They keep ports and lock files, and the next start stalls for hours. The fix that was proven by a forced crash
(L-AGENT-013, 2026-09-26):

```ini
# sketch of the proven setup (the reaper's own argument names were not recorded)
# /etc/systemd/system/<unit>.service.d/10-reap-orphans.conf
[Service]
ExecStartPre=+/usr/local/sbin/<reaper>.sh prestart   # kill leftovers of <agentuser> (TERM, 30 s, KILL);
                                                    # refuse to start while ports 7005/14479 or *.mv.db are held
ExecStopPost=+/usr/local/sbin/<reaper>.sh reap       # same reap after any stop
```

plus a root cron every 5 minutes that runs the reaper in check mode (kill an engine JVM whose pid file names a different
live JVM; warn if agentcore is missing or JVMs sit outside the unit's cgroup). Result of `kill -9` on agentcore and its
respawn loop followed by `systemctl restart`: 0 orphans and 20/20 engines RUNNING in about 6 minutes, with a running CDC
job and CAI unaffected. If the Process Server is enabled, add its port guard (section 9).

**Scope every guard to its own agent** (L-AGENT-096, L-AGENT-013). A guard that counted any holder of 7005 or
14479 and any open `*.mv.db` refused every start of the first agent once a second agent's Process Server and metadata
service held their own; it surfaced only at the next reboot. Count a port holder only when its process belongs to this
agent's OS user, and lock files only under this agent's home. With no agent process alive, every app `.pid` file is
stale: move them aside in the same pre-start hook (L-AGENT-095).

```bash
# reaper/guard: only holders owned by THIS agent's OS user count
port_holders { ss -Hltnp | awk -v ports="$PORTS" 'BEGIN{n=split(ports,a," ")} {for(i=1;i<=n;i++) if($4 ~ ":"a[i]"$") print}' |
  while read -r l; do p=$(echo "$l" | grep -oE 'pid=[0-9]+' | head -1 | cut -d= -f2)
    [ -n "$p" ] && [ "$(stat -c %U /proc/$p 2>/dev/null)" = "$AGENT_USER" ] && echo "$l"; done; }
# lock files: only under THIS agent's home
mvdb_holders { for p in /proc/[0-9]*; do ls -l "$p/fd" 2>/dev/null | grep -q "$AGENT_HOME/.*\.mv\.db" && echo "${p#/proc/}"; done; }
```

## 5. Two agents on one host

Proven 2026-09-28/29 with a second agent for another org next to a production agent on a 4-vCPU host
(L-AGENT-015, 2026-09-28).

| Concern | Rule |
|---|---|
| Identity | Own OS user, own home and install directory (own singleton lock and environment) |
| Supervisor | Own unit with a new name; `Type=forking`, `RemainAfterExit=yes`, `KillMode=control-group`, no `Restart=` |
| Double start | `ExecStartPre` guard that refuses while a manual instance runs; match with a `[.]` so pgrep does not match the guard itself |
| Resources | `MemoryHigh`/`MemoryMax` and `CPUWeight`/`IOWeight` on both units |
| Ports | Only one Process Server per host: 7005, 7080 and 7443 are static, so run it on the agent whose org runs the CAI processes and leave the other's off or deselected; that one's embedded Postgres can move to its own port (for example 5434) (L-AGENT-090, L-AGENT-089, L-AGENT-013). Cloud Integration Hub's processor binds a static API port too (table below) |
| Temp directories | The catalog scanner writes its scan report into `/tmp/poifiles`. The first agent user to scan creates it with mode 755, and the second agent's scans then end PARTIAL_COMPLETED with `AccessDeniedException`: `chmod 1777 /tmp/poifiles` (or give each agent its own `java.io.tmpdir`) and write-test it as both users (L-CDGC-150) |
| Secrets | Deny the new user read access to the applications' secret files |
| File lanes | Share flat-file directories through a group-writable directory (mode 2775), not the first agent's home (L-CONN-067, 2026-09-28) |
| Proof | `pgrep -c -f 'agentcore.impls.MainApp'` = 1 per install dir; the first agent's pid unchanged |

The guard line, with the self-match trap avoided:

```ini
ExecStartPre=/bin/sh -c '! pgrep -u <agentuser2> -f "agentcore[.]impls[.]MainApp"'
```

The regex `agentcore[.]impls[.]MainApp` matches the real JVM but not the guard's own command line, which contains the
brackets literally; `-u` keeps the first agent's JVM out of the count. The first attempt of the real unit, with an
unbracketed pattern, was refused by its own guard.

**Ports seen on an agent host**

| Port(s) | Holder | Note |
|---|---|---|
| 7080 / 7443 | Process Server (CAI) HTTP/HTTPS | `/process-engine/status` |
| 7005, 14479 | Process Server internals | A reaper guard on the first agent refused to start while these were held |
| 5432 | Process Server embedded Postgres (hardcoded) | Collides with any local Postgres; move it and guard the move after upgrades (L-AGENT-071, L-AGENT-089) |
| 19443 | Cloud Integration Hub processor `server.api.port` (static) | A second agent with CIH selected restart-loops ('The Tomcat connector configured to listen on port 19443 failed to start'): set a free port in `<agent_home>/apps/CIHProcessor/<ver>/conf/application.properties` as the agent user, restart, and re-apply it from the root cron guard, because an upgrade re-extracts the default (L-AGENT-090) |
| 14xxx range | Engine JVMs such as Metadata_Platform_Service | Engines picked free ports; the second agent skipped one the first held |

Diff `ss -ltnp` before and after each service lands.

### 5.1 Limits with systemctl set-property

```bash
systemctl set-property <unit> MemoryHigh=12G MemoryMax=14G CPUWeight=100 IOWeight=100   # live, no restart
systemctl set-property --runtime <other-unit> CPUWeight=20 IOWeight=20                  # lost at reboot
cat /sys/fs/cgroup/system.slice/<unit>.service/memory.events      # high 0 = never throttled
cat /proc/pressure/cpu /proc/pressure/memory                      # PSI: are we CPU-starved?
```

Persistent set-property drop-ins land in `/etc/systemd/system.control/<unit>.d/` and override
`/etc/systemd/system/<unit>.d/` (L-AGENT-017, 2026-09-29). If RAM is tight, add a second swapfile with `nofail` in
fstab so idle JVM pages can leave RAM. A 17-service agent held about 11.2 GB and kept hitting a 12 GB `MemoryHigh`;
raise MemoryHigh/MemoryMax (for example to 14/16 GB) only when the host still has at least 9 GB available
(L-AGENT-093).

**Check that the cap is real** (L-AGENT-017):

1. Every agent process must be inside the slice. An agent first started from an interactive SSH session lived in that
   session's scope, uncapped (8.8 GB RSS); under its own unit the same agent used 3.6 GB. Helper scripts that start or
   redeploy agent components must run through `systemd-run --scope --slice=<agent-slice>`.
2. The configured heaps must fit: add up the `-Xmx` of every agent JVM (agentcore, DIS Tomcat, Mass Ingestion runtimes,
   other engines) plus the DTMs. With about 9.5 GB of configured heap inside a 4 GB cap the slice throttled even when
   idle (`memory.events high` about 12 million).
3. No duplicate JVMs: after a lifecycle restart, three orphaned copies of one engine JVM pushed the slice over MemoryHigh
   (memory pressure full avg10 62%); killing them dropped it to 4%.
4. The slice is the one you meant: systemd reads a hyphen in a slice name as hierarchy, so `<name>-<suffix>.slice` is a
   child of `<name>.slice` and inherits its caps, while the child's own caps applied to a cgroup that was never created.
   An agent nested that way under a 4 GB parent had its page cache evicted again and again, and its JVM re-reads ran a
   shared database host out of disk IOPS (load above 100, IO pressure 98 %). Name agent slices without a hyphen, read
   `memory.max`, `io.max` and `cpu.max` on the real cgroup, and give an idle agent with services selected 3-4 GB plus
   headroom (L-AGENT-110, 2026-10-29).

```bash
ps -eo pid,cgroup,rss,args | grep -i infa | grep -v <agent-slice>   # must be empty
cat /sys/fs/cgroup/<agent-slice>/memory.events /sys/fs/cgroup/<agent-slice>/memory.pressure
grep nr_throttled /sys/fs/cgroup/<agent-slice>/cpu.stat
```

### 5.2 What limits performance

- Two agents on 4 vCPU contend for CPU, not memory (`memory.events high=0` while lanes slowed). Lower the idle agent's
  weights, give the working agent memory headroom, and deselect the catalog Metadata services after scans: a 16-task lane
  went from 7.7 to 3.5 minutes (L-AGENT-018, 2026-09-29).
- Cap parallel task fan-out at about the vCPU count: concurrency 4 on 4 vCPU cut a 16-task lane from 462 s to 215 s
  (L-AGENT-019, 2026-09-29), once the DTM pool allowed it (next bullet).
- **The DTM pool decides real concurrency.** The Data Integration Server runs at most `maxDTMProcesses` DTMs at once,
  and the default is 2. A controller that submitted 4 tasks at once never got more than 2 DTMs: over 472 sessions the
  queue wait before 'DTM process started' was p50 13.9 s, p90 39.7 s, p99 70 s, while CPU was not the limit (a
  warehouse-bound DTM spends most of its 14-20 s waiting on the warehouse). Raise the pool cloud-side (§6.2)
  (L-AGENT-099).
- Agent JVMs alone drove a shared VM's load to about 35; do not measure test suites on an agent host
  (L-AGENT-054, 2026-07-13).
- A 2-vCPU fallback agent is CPU-bound where the Hosted Agent was not: after a failover a data-quality mapping took 62 s
  at 4 tasks at once against a 26 s p50 on the Hosted Agent, while a full-reprocess golden-record mapping kept its
  118 s on both. Size a fallback agent for the CPU-bound share at your concurrency and start the latency-critical task
  first; for full-reprocess mappings the lever is an incremental design (L-AGENT-118, 2026-11-03).
- Jobs started over REST can wait for the agent's job-poll cadence: on one agent 15 serial tasks took about 45 minutes
  (about 3 minutes each), while another agent showed only about 20 s of fixed cost per task; watch the target as well as
  the activity log when detecting completion (L-AGENT-058, 2026-08-20).

## 6. Memory, disk and heap

**What each thing costs**

| Item | Observed cost | Lesson |
|---|---|---|
| Idle registered agent | ~1 GB RAM | L-AGENT-053 |
| CAI Process Server | +1.8-2 GB RAM (`-Xmx1536M`); watch for a first-start crash loop | L-AGENT-053 |
| Catalog scanner services | several GB RAM plus heavy CPU; switch on only for scan windows | L-AGENT-043 |
| Every service selected | ~18 GB of downloads in ~8 min, load ~189 on 4 vCPU, swap full | L-AGENT-041 |
| 17 services selected | ~11-12 GB in the agent's unit | L-AGENT-093 |
| Package store `downloads/` (live: never clean it) | 19-20 GB after many enablements | L-AGENT-094 |
| Long-lived agent home | ~25-27 GB | L-AGENT-066 |
| A stopped agent installation left on the host | ~46 GB | L-ENV-069 |
| USA address-verification reference data in `data/avdata` | ~4.1 GB | L-AGENT-116 |
| Cached lookups | declared port precision x rows, not the data width: 'No space left on device' with ~6.5 GB free; cut precisions and filter the lookup query | L-CDI-281 |

**OOM.** An over-subscribed agent OOM-kills its neighbours first (co-located databases died twice), engines flap
RUNNING/STOPPED, and connection tests fail with an error that rotates between engines. That rotation is OOM churn, not
configuration (L-AGENT-052, 2026-09-12). Cap the agent with a slice or unit limits and select fewer services.

**DTM heap.** For DTM OutOfMemory failures raise the DTM heap (`JVMOption1=-Xmx2048m`), and set it **cloud-side**
(type DTM, §6.1) rather than in `<agent_home>/apps/Data_Integration_Server/<disVersion>/ICS/main/bin/rdtm/pmrdtm.cfg`
(L-AGENT-056, L-AGENT-088). After a few version rolls several `<disVersion>` directories coexist, and an edit made in
one that was no longer running changed nothing while the mapping kept failing; any selections PUT or configuration save
can roll DIS again (L-AGENT-056). Find the running version from the youngest DIS JVM's command line:

```bash
for p in $(pgrep -u <agentuser> java); do tr '\0' '\n' < /proc/$p/cmdline | grep -oE 'apps/Data_Integration_Server/[0-9.]+'; done | sort -u
```

The heap setting is agent-wide and every DTM gets it, and several DTMs run at once, so a mapping that passes alone can
run out of heap beside other lanes. The first error is `PLUGIN_1762... OutOfMemoryError: Java heap space` in one
reader; the `BIGQUERYV2_10000... 5001` token errors that follow on the other reader partitions are a cascade, not a
credential problem (L-CDI-210). Keep BigQuery readers per mapping at about five on a small agent, select only
needed columns and give STRING fields a small reader precision (L-AGENT-057, 2026-09-29).

**Exit codes** (L-AGENT-061, 2026-06-28): `pmdtm` exit 127 = a shared library failed to load (run `ldd`, do not touch
the heap); 134 = SIGABRT (a missing library or a broken connector build); 137 = OOM kill.

**Disk: `downloads/` is live code, not a cache** (L-AGENT-094; supersedes L-AGENT-055). Installed
services run jars and scripts from `<agent_home>/downloads/package-<name>.<n>/package/` (agent logs show 'Actual JAR
location:.../downloads/package-<x>.<n>/package/lib/...'), and an older version number can be the one a current appspec
pins. Keeping only the newest version per package put 14 of 20 services into ERROR ('./status.sh: not found'). Never
delete, prune or move anything there.

- If it already happened: restart the agent service and wait about 10 minutes; agentcore re-downloads the pinned
  packages and redeploys them, and disk usage returns to where it was (nothing was gained).
- Plan the disk instead: leave room for about 20 GB of packages after many enablements (L-AGENT-052).
- Free space elsewhere, in this order: agent and session logs, the systemd journal, package caches, Docker build cache
  (`docker builder prune -f` touches build cache only). Never prune Docker volumes, a live agent's directory or images
  that are rollback targets (L-ENV-069).
- On a Docker host, moving Docker's data-root does not move containerd's own store: `/var/lib/containerd` filled an OS
  disk shared with an agent. Check both paths (L-ENV-071).

### 6.1 Change engine configuration cloud-side (DTM heap, DTM pool)

Pick the first route that works for you:

1. **The UI (simplest):** Administrator > Runtime Environments > the agent > **Edit** > System Configuration Details,
   pick the service (Data Integration Server) and type (DTM for the job heap, Tomcat for `maxDTMProcesses`), change the
   value, save. Saving restarts the Data Integration Server, so drain running jobs first (L-AGENT-121).
2. **Group level over REST:** `GET/PUT /api/v2/runtimeEnvironment/<reId>/configs` sets a property for every agent in
   the runtime environment (L-AGENT-132, reported: try it on a scratch group, read back, and check the engines restart).
3. **Per agent, without a browser:** the legacy `agent.do` form below. It is the last resort.

#### The legacy `agent.do` form (per agent, no REST verb)

Host edits of `pmrdtm.cfg` / `tomcat.cfg` are lost on every DIS version roll. The durable place for a DTM heap, a DTM pool
size or any other engine property is the agent's **System / Custom Configuration** in the cloud. There is **no REST verb**
for it. The Administrator shell iframes a legacy Struts form, and that form can be driven directly (L-AGENT-088, proven
2026-09-29).

> **Before you use it.** This form is undocumented and can change without notice; prefer the UI or a REST route for
> anything else. Never copy session cookies out of a browser: authenticate with your own REST login (step 1). Saving
> rewrites the agent's whole engine configuration and **restarts the Data Integration Server, killing every running job
> on that agent** (L-AGENT-121), so drain the agent first, save a copy of the form you read, and change one value at a
> time.

1. **Read:** `GET https://<pod>.<domain>.informaticacloud.com/runtime/app/agent.do?actionMethod=displayUpdate&iframeWorkspaceId=SecureAgentDetailsWS&id=<agentId>`.
   Authenticate with the session from your own REST login, sent as the `USER_SESSION` cookie together with a random
   `XSRF_TOKEN` cookie that matches the form's `csrfToken` (L-AGENT-126). The page holds ONE form, `AgentForm`
   (~1,550 fields), plus a `csrfToken`. **Keep a copy of what you read**: it is your undo.
2. **Engine properties are parallel arrays**, one entry per row: `engineConfigKey`
   (`<Engine><major.minor><TYPE><name>`, e.g. `Data_Integration_Server<ver>PMRDTM_CFGJVMOption1`), `engineConfigValue`,
   `engineConfigDefault` and `engineConfigOverriden`. To change one, set its value and `engineConfigOverriden=true`. To
   reset it, set `overridden=false` and value = default.
3. **Properties an engine does not list** (e.g. the DIS Tomcat `maxDTMProcesses`) go in as **Custom Configuration** rows:
   `customConfigEngine=Data_Integration_Server<major.minor>`, `customConfigTypeEngine=TOMCAT_CFG` (the DTM type is
   `PMRDTM_CFG`), `customConfigSubType=-1`, `customConfigName`, `customConfigValue`. Leave `customConfigType=-1`; that
   select is for agent-core types.
4. **Save:** `POST /runtime/app/agent.do` as `application/x-www-form-urlencoded` with the WHOLE form, `actionMethod=update`
   and the page's `csrfToken`. This is exactly what the UI's `doSave` → `doUpdate` → `AgentForm.submit` sends. It
   returns 200 and renders the read view. **Read back** by re-GETting `displayUpdate`.
5. **Effect:** the cloud pushes the change into `<ver>/ICS/main/tomcat/tomcat.cfg` and
   `<ver>/ICS/main/bin/rdtm/pmrdtm.cfg`, then **restarts DIS by itself ~1.5 min later**. That restart may also **roll
   DIS to a pending newer version**. The old DIS JVM keeps serving until the new one's tunnel opens (~1 min), and it is
   retired 5–8 min later. Expect a short window of two JVMs.
6. **Gotchas:**
   - the DIS default DTM pool is `maxDTMProcesses` (poolSize) = 2, as logged in `tomcat_<ver>.log`;
   - the Administrator shell iframe can stop rendering for a headless browser, but driving `agent.do` at top level works;
   - the undo is the same POST with the custom row removed and/or the key reset;
   - verify on the **running** DIS and DTM processes' command lines (`ps -o args`), not on the newest version directory:
     the save can roll DIS to a newer build in the same step, and the old JVM lingers 5-8 minutes (L-AGENT-099).

### 6.2 The DTM pool: measure it, then raise it (L-AGENT-099)

1. **Read the pool size:** `grep -h 'maxDTMProcesses(poolSize)' <agent_home>/apps/Data_Integration_Server/logs/tomcat/tomcat_*.log | tail -1`.
   No `maxDTMProcesses` line in the running version's `tomcat.cfg` means the default, 2.
2. **Measure the queue:** for each session, the time from 'Submit job to thread pool queue' to 'DTM process started'
   in the same log; report p50, p90 and max. Sample the number of DTM child processes of the DIS JVM every 5 s during a
   busy period.
3. **Decide:** the pool is binding when the observed maximum equals the pool size and p90 wait is above about 10 s.
4. **Raise it in a drained window** through the `agent.do` form (§6.1): a Custom Configuration row
   `Data_Integration_Server<major.minor>` / `TOMCAT_CFG` / `maxDTMProcesses` / `<N>`, together with the DTM heap row
   (`PMRDTM_CFG`, `JVMOption1`), so both survive version rolls. Size N to memory first (about 0.5-1 GB per DTM plus heap
   headroom under the unit's limit) and to the vCPUs.
5. **Verify:** after the automatic DIS restart, `poolSize=<N>` in the new `tomcat_<disVersion>.log`, the queue
   histogram under a real burst (aim for p90 under 10 s), and the unit's `memory.events` (`high`, `oom_kill`). The old
   JVM kept dispatching until the new one's tunnel opened; no dispatch gap was seen.

| Pool | When |
|---|---|
| 2 (default) | Parallel lanes serialize; a staged executor caps at 2 |
| 4 | A 4-vCPU host with about 8-12 GB available to the agent (measured: 4 concurrent DTMs, minimum MemAvailable 10.1 GB, unit peak 7.55 GB under a 12 GB MemoryHigh) |
| 1 | Small or shared database hosts; heavy profiling (L-DQ-098) |

After the change, a 40-task full refresh ran 40/40 in 321 s and the event lane's golden mapping went from 62-85 s to
47 s (L-AGENT-099). Add a soak check that alerts when the running pool or heap drifts from the intended value
(§12).

## 7. Native libraries on modern distributions

| Distro | What fails | Fix | Lesson |
|---|---|---|---|
| Debian 12 | `pmdtm`: `libidn.so.11: cannot open shared object file`, exit 127 (profiles), exit 134 (DTM) | `ln -s libidn.so.12 /usr/lib/x86_64-linux-gnu/libidn.so.11`; also a compat dir in `/etc/ld.so.conf.d/` + `ldconfig`, and that dir on `LD_LIBRARY_PATH` in `agent_start.sh`; verify `env -u LD_LIBRARY_PATH ldd pmdtm` | L-AGENT-059 |
| Rocky / RHEL 8-9 | `pmdtm` cannot load `libcrypt.so.1` and `libidn.so.11`; jobs die before reading a row | `dnf install libxcrypt-compat`; EL7 `libidn-1.28-4.el7.x86_64.rpm` from vault.centos.org with `rpm -i --nodeps`; no restart needed (pmdtm spawns per job) | L-AGENT-060 |
| Ubuntu 24.04 and other new distros | `libidn.so.11: cannot open shared object file` | Same fix as Debian 12 (the `.12` symlink); reported, not proven on 24.04 | L-AGENT-005, L-AGENT-059 |
| Ubuntu 22.04 | AI Agent Runtime stuck DEPLOYING | Install `unzip`, `libffi6`, `libreadline7`, `libtinfo5` side by side | L-AGENT-062 |
| Any | Every profile run dies 'DTM process terminated unexpectedly'; import log stops at 'Error encountered while Parsing file' | Rename dangling `*.xml` symlinks in the rdtm plugin folders, restart | L-AGENT-063 |

The system-level symlink survives agent re-syncs, which rewrite only the agent directory. `ldconfig -p` not listing the
`.11` name is fine. In a container, all of this must be baked into the image (section 8).

## 8. Containers and Windows

**Windows** (documented, not proven here): get the installer and token with `/api/v2/agent/installerInfo/win64`; the
host needs 4 CPU, 16 GB RAM, the MSVC++ 2015 runtime and outbound 443 (L-AGENT-005, L-AGENT-131). The agent runs as a
Windows service; register it the same way with the install token. Everything else in this guide is proven on Linux.

**Containers:**

- The agent registers under the container's hostname: set `hostname: <agent-name>` in docker-compose, or the container
  id becomes the agent name (L-AGENT-064, 2026-09-08).
- OS packages installed into a running container vanish on recreate (`docker compose down -v`); the volume usually keeps
  only the agent home. Restart such a container, never recreate it, and bake the libraries into the Dockerfile
  (L-AGENT-065, 2026-09-03).
- The agent's named volume exists only on the host's OS disk and snapshots, not in application backups; deleting the VM
  deletes the agent state (L-AGENT-066, 2026-09-08).
- Inside a container, `127.0.0.1` in a connection is the agent container itself; use Docker network aliases
  (L-CONN-025, 2026-08-18).

## 9. The Process Server (CAI) on the agent

Enable it only if processes must reach private hosts; processes that call only cloud endpoints can run on the hosted
Cloud Server. Treat it as fragile on shared hosts.

1. **Verify it really serves** (L-AGENT-070, 2026-09-24): on the host, `https://localhost:7443/process-engine/status`
   (or `:7080`) returns 200 with body `2`, `/process-engine/rt` returns 401, and agent details show process-engine
   RUNNING/RUNNING. `enabled: true` in the selections proves nothing; a restart loop shows as repeated RESTARTING events
   in `agentcore.log`. A flapping Process Server shows `/process-engine/status` returning 404, then
   `[LCM_10012]... Status script return code: EXITED_NONZERO` and a restart; Cloud Integration Hub writes the same
   LCM_10012 lines, so count restarts per engine name, not per message (L-AGENT-100).
2. **Port 5432 is hardcoded** for its embedded Postgres (every PE script, `server_status.sh` = `pg_isready -p 5432`).
   With another local Postgres on 5432 the start logs a false 'PostgreSQL database has started', `prepareDB.sh` runs
   against the wrong database and deletes the embedded data directory (L-AGENT-071, 2026-09-24).
3. **`deploy.sh` can delete its own Tomcat context descriptor** when `conf/Catalina/localhost` already exists; the webapp
   then deploys empty in ~37 ms and every URL is 404. `conf/ae.keystore` and `ae.cacerts` must exist or 7443 never binds
   (L-AGENT-072, 2026-09-24).
4. **Repair** (L-AGENT-073, 2026-09-26): back up bin/conf/data; move `localhost:5432/activevos` to a free port in
   `<peVersion>/bin/*.sh` and the context descriptor; set that port and `listen_addresses='localhost'` in the embedded
   `user.conf`; stop the looping Tomcat; re-run Informatica's `deploy.sh` with the LCM environment captured from the live
   process; restore `conf/Catalina/localhost/process-engine.xml`; verify. Auto-upgrades ship new version directories with
   the 5432 scripts again, so a root cron port guard re-applies the port.
5. A stopped Process Server whose binaries are present can be started on the host itself (L-AGENT-074, 2026-07-05).
6. **The keystore symptom has a database cause** (L-AGENT-089, 2026-09-30). With another Postgres on 5432, the deploy
   script's Liquibase update reaches the wrong server, prints 'Process Server update failed' and exits before it copies
   `ae.keystore`, `crypto.properties` and `tomcat-users.xml` into `apps/process-engine/conf`; Tomcat then fails its
   HTTPS connector ('Error creating SSLContext... conf/ae.keystore'), 7443 never opens and the service restarts every
   ~2 minutes. Fix as the agent user: change 5432 to a free port in `bin/*.sh`, `conf/Catalina/*/process-engine.xml`
   and every `data/*/user.conf` (`port = <p>`, `listen_addresses = 'localhost'`), then run `.lcm/stop-wrapper.sh`
   followed immediately by `.lcm/deploy-wrapper.sh` from the version directory. A 10-minute root cron re-patches the
   files and re-runs stop plus deploy when the newest deploy result in `logs/scripts.log` is a failure.
7. **One Process Server per host** (L-AGENT-090): 7005, 7080 and 7443 are static, so a second agent's Process Server
   stays in ERROR while the first holds them.

## 10. Restarts, classloader caching and version rollovers

| Change | Needs a restart? | Survives an engine upgrade? | Lesson |
|---|---|---|---|
| Third-party JDBC jar staged for JDBC V2 | Yes: restart Connector_Service or the agent (classpath cached) | Only if also staged in `ext/deploy_to_main/...` | L-CONN-049, L-CONN-050 |
| Simba BigQuery jars for Database Ingestion | Yes: restart the agent (classloader caches at start) | Re-check after DBMI upgrades | L-CONN-045 |
| Native OS libraries for `pmdtm` | No (pmdtm spawns per job) | Yes (system dirs) | L-AGENT-060 |
| Host edit of `pmrdtm.cfg` / `tomcat.cfg` | Next DTM / DIS restart | No: it lives in one `<disVersion>` directory; set it cloud-side instead | L-AGENT-056 |
| Cloud-side engine configuration (`agent.do`) | DIS restarts itself ~1.5 min after the save | Yes: the cloud writes it into each new version | L-AGENT-088 |
| VM resize or reboot | Agent and engines restart | n/a: run the post-boot checklist (§2) | L-ENV-069 |
| Process Server port patch | Re-deploy | No: new PE version dirs restore 5432 | L-AGENT-073 |
| Service or connector selection change | Automatic | It triggers the rollover itself | L-AGENT-042 |

**Version rollovers.** Engine versions move independently of the agent core version (DIS 77.x vs core 76.x,
L-AGENT-023, 2026-07-26). DIS auto-upgrades drop hand-placed jars left in the old version's directories
(L-CONN-050, 2026-08-20), and every selections PUT rolls Data_Integration_Server, MassIngestionRuntime and
Connector_Service to their newest builds, queueing jobs for about 5 minutes (L-AGENT-042, 2026-09-29). After any
rollover, re-check the `ext/deploy_to_main` drivers, the running DIS JVM's heap and DTM pool (§6.2), the Process
Server port and the Cloud Integration Hub port.

## 11. Where the agent keeps things

| Path under `<agent_home>` | Contents |
|---|---|
| `apps/agentcore/` | `infaagent`, `agent_start.sh`, `consoleAgentManager.sh`, `agentcore.log` ('Service Status Distribution... Deploying: N Running: N Stop: N Restart: N'). Its timestamps are `YYYY-MM-DD HH:MM:SS` with a space, so a time filter built with the ISO `T` matches nothing (L-AGENT-100) |
| `apps/agentcore/conf/infaagent.ini` | `MasterUrl=https://<domain>.informaticacloud.com`, `InfaAgent.Id=<agentId>`, the org id |
| `apps/<Service>/<version>/` | One directory per engine and version |
| `apps/Data_Integration_Server/logs/tomcat/tomcat_<ver>.log` | Connection-test errors (`op:testConnection`); the file name shows the active DIS version; `maxDTMProcesses(poolSize)=<n>` at startup; per session 'Submit job to thread pool queue'... 'DTM process started' (the queue wait) (L-AGENT-099) |
| `apps/Data_Integration_Server/logs/s_mtt_<taskId>_<n>.log` | One session log per mapping-task run (`TM_6014` start, `PETL_24012`/`24013` end, `Applied Rows [N]`); also readable over REST (`GET /api/v2/activity/activityLog/<entryId>/sessionLog`, L-CDI-211). Profiling DTMs run as `s_profiling_<profileKey>_<run>_<n>` sessions (L-DQ-019) |
| `apps/Data_Integration_Server/data/userparameters/` | Per-task parameter files named by a task's `parameterFileName` (the agent writes its own `data/parameters/s_mtt_<taskId>.param`) (L-CDI-285) |
| `apps/Data_Integration_Server/data/avdata/FileSetA/`, `data/avLicenseFile/` | Address-verification reference files (`.MD6`) and the licence fetched at each start (L-AGENT-116) |
| `apps/Metadata_Foundation_Agent/data/workspaces/<source>-*/jobs/<ts>-*/debug/thread_dumps/` | Catalog scanner thread dumps, every 10 minutes: where a hung scan shows its stuck thread (L-CDGC-223) |
| `apps/Database_Ingestion/logs/tasks/*_<jobId>-CDC_COMBINED-*.log` | DBMI task logs; per-table progress as `transition event [<EVENT>]. Details: [table=<schema>.<table>` lines (L-DBMI-030) |
| `apps/IDMC_Data_Gateway_Service/<ver>/log/system/log/` | The Data Gateway behind CLAIRE GPT 'Query the data' (present only when the org holds that package, L-AGENT-097) (L-AGENT-051) |
| `apps/CIHProcessor/<ver>/conf/application.properties` | Cloud Integration Hub `server.api.port` (static 19443) (L-AGENT-090) |
| `apps/process-engine/` | Process Server (CAI), its embedded Postgres and conf |
| `downloads/` | The live package store: installed services run jars and scripts from `package-<name>.<n>/package/`, and `package-<CONNECTOR>*/` holds connector manifests and plugin XML. Never clean it (L-AGENT-094) |
| `ext/connectors/thirdparty/`, `ext/deploy_to_main/` | Hand-staged drivers |

(L-AGENT-069, 2026-09-29.) Before deleting one of several VMs, match `InfaAgent.Id` with the agent id in IDMC, confirm
the Java processes and compare the org's connection hosts with the VM's network (L-AGENT-068, 2026-07-06). Native agents
do not appear in `docker ps`; look for `/home/*/infaagent/` and 14xxx listeners (L-AGENT-067, 2026-09-07).

## 12. Health monitoring

- **Routes** (L-AGENT-020, 2026-07-26): `GET /api/v2/agent/<agentId>` (`active`, `readyToRun`, `version`,
  `upgradeStatus`, `lastUpgradeCheck`, `packages[]`) and `GET /api/v2/agent/details/<agentId>` (`agentEngines[]` with
  `agentEngineStatus.status`, `desiredStatus`, `subState`). No v3 object returns live status.
- **Do not trust the list**: `GET /api/v2/runtimeEnvironment` reports a stale `agents[].readyToRun: false`
  (3 reads of 3); read per agent and confirm with `getstatus` (L-AGENT-021, 2026-07-26). `readyToRun` exists twice and
  only catalog-source creation checks it; mapping runs ignore it (L-AGENT-022, 2026-07-04).
- **Alert rules**: `engine_ok = (status == desiredStatus)`, but treat RESTARTING and DEPLOYING as transients and alert on
  STOPPED/FAILED while desired RUNNING, or on a persistent RESTARTING loop (L-AGENT-028, 2026-07-05). A scheduled exporter
  must actually run, and node_exporter textfiles need LF endings (L-AGENT-029, 2026-07-04).
- **Tell a Hosted Agent outage from a connection fault**: every hosted connection fails its test at once with APP_105060
  naming the hosted agent group, and hosted runs fail in 2-3 s with 'no active Secure Agent in group Informatica Cloud
  Hosted Agent', while Secure Agent connections pass. Fail over with the runbook in
  [doc 02](02-runtime-environments-services-connectors.md) §1 (L-AGENT-117, L-ENV-100, 2026-11-03).
- **Iterate everything**: one login sees every runtime environment; loop them all, stamp an environment label on each
  row, and count them before asserting "all N healthy" (L-AGENT-030, 2026-07-08).
- **Lifecycle restart loops**: an agent can crash-restart hundreds of times a day and be fully down for ~5 minutes in each
  trough; check 'Service Status Distribution' history, not one read (L-AGENT-077, 2026-07-05).
- Crash-looping, unconfigured services (typically Data Access Management) can be deselected per runtime environment
  (L-AGENT-046, 2026-09-24). In an org with no Data Access Management setup, its agent and proxy log 'Initializing TMS
  and CMS configuration services', then exit with code 133 about 3.5 minutes later, forever; exclude them from alerts
  rather than patching the host (L-AGENT-091, L-AGENT-100).
- **Parse `getStatus` by keyword**: the status keyword (`READY` or `NOT_ALL_SERVICES_ARE_RUNNING_OR_STOPPED`) is on the
  first line, followed by a 'Detail:' block and a trailing blank line; a monitor that reads the last line raises false
  alerts (L-AGENT-092).
- **Watch the engine settings**: a soak check that reads the youngest DIS JVM's heap and DTM pool and alerts when they
  differ from the intended values, not when the version changes (L-AGENT-056).
- **Watch entitlement arrive**: poll the per-org licence record and every agent's `agentEngines[]` every 10 minutes and
  alert on content changes; a new engine on the agents is the decisive signal, because a licence line alone deploys
  nothing (L-IPU-057; [Entitlement, Licenses & Job Caps](../13-ipu-cost/03-entitlement-licenses-job-caps.md)).
- **Cloud-side baseline for the agent VMs**, before production pipelines run (L-ENV-074): an uptime alert per VM;
  host metrics that really arrive (on three VMs an installed monitoring agent sent only its self-telemetry, so no
  disk-full alert was possible, and a full disk is the recurring agent-host outage); a project budget with alerts; a
  freshness alert on any replication feed into the warehouse.
- **After any agent, selection or pipeline change**, run one read-only verification sweep scoped to "since the change"
  (engines, runs, schedules, CDC jobs, output freshness) (L-METHOD-057;
  [Evidence Discipline](../14-working-with-claude/02-evidence-discipline.md) §8).

## 13. Overturned beliefs (Secure Agent)

| Believed | Until | Now | Lesson |
|---|---|---|---|
| Agent registration needs the UI | 2026-07-01 (restated 2026-08-18) | Installer info over v2 plus `configureToken` | L-AGENT-078 -> L-AGENT-002 |
| Services and connectors can only be enabled in Administrator | 2026-09-22 | `PUT.../selections/ui` with `IDS-SESSION-ID` | L-AGENT-079 -> L-AGENT-039 |
| Enabling agent services is free and safe | 2026-07-26 | Every service costs RAM, disk and downloads | L-AGENT-084 -> L-AGENT-052 |
| An engine reading RUNNING is usable | 2026-07-26 | Only a passing test or job proves it | L-AGENT-083 -> L-AGENT-023 |
| The RE list's `readyToRun:false` means never runnable | 2026-07-26 | Stale list value; read per agent | L-AGENT-082 -> L-AGENT-021 |
| APP_13401 / CMN_001 prove there is no enablement plane | 2026-07-26 | Router artifacts; prove nothing | L-AGENT-085 -> L-AGENT-031 |
| `downloads/` is a re-fetchable installer cache that can be cleared or moved aside | 2026-07-08 to 2026-09-28 | It is the live package store; pruning it broke most services | L-AGENT-055 -> L-AGENT-094 |
