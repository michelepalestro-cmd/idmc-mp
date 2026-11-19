# Bootstrap — zero to a running IDMC job

> **July 2026 snapshot.** Where this file says "UI-only", "no REST verb" or "walled", read it as a dated verdict:
> many were overturned later (KB `lessons/overturned-beliefs.md`, Laws 16-19). Before telling a user
> something is not possible, work the workaround ladder in KB `knowledge/00-start-here/08 New Pipeline Milestones`.
> "Org A" / "Org B" are two example orgs; derive your own values (Law 1).

Ordered, with a gate at step 3 that decides whether steps 7–10 are even possible. Each step is tagged:

- **HEADLESS** — Claude can do it over REST
- **NEEDS SHELL** — requires a shell on the target host
- **UI ONLY** — a human clicks; no HTTP verb exists

Do not skip step 3. Steps 7–10 fail confusingly without it.

## Read this first — the four gates people discover in the wrong order

A working connection needs **four** independent things. They fail with *different* errors that all look
like "the connection is broken", and each has its own fix in its own place. Establishing them in this
order is the difference between an hour and a day:

```
HOST      enough RAM / disk / swap, and only the engines you need   -> step 5
ENGINE    Data_Integration_Server RUNNING (not DEPLOYING)           -> step 6b #1   UI
ADAPTER   the connector's adapter jar deployed to the agent         -> step 6b #2   UI
DRIVER    third-party JDBC jar registered (JDBC_V2 targets only)    -> step 6b #3   UI
```

Then, and only then, do connection bodies and credentials matter (step 7).

**Three habits that save the most time:**

1. **Ask what the error names.** IDMC tells you which of the four is missing — the engine name, the
   `com.informatica.adapter.<x>` id, or `Unable to load driver`. Match the message to the gate instead
   of re-editing the connection.
2. **Read the connector's manifest before writing a body.** Field names are per-connector and not
   guessable; the manifest also says whether the type can carry credentials at all.
3. **Distrust convenient reads.** The runtime-environment *list* misreports agent health; the
   342-row connector catalog is a sales list; an error code can be a router artifact. Confirm against
   the per-agent endpoint, the on-host adapter registry, and a bogus twin.

---

## 1. Log in and pick a plane — HEADLESS

Three logins, three tokens. See `02-request-bodies.md`. Wrong plane is the largest source of false
negatives in this corpus.

Use `.serverUrl` from the v2 login as the base for later v2 calls — do not assume the pod host.

## 2. Confirm the org and pod — HEADLESS

```bash
GET /api/v2/org        # -> id (v2 shape), name, parent
```

Record **both** ID shapes and the pod. `dmp-us` ≠ `dm-us`. If this does not match the org you were
asked to work in, stop — sub-org membership is explicit per user, and org-switch paths 404.

## 3. Read the entitlement gate — HEADLESS — **THE GATE**

```bash
GET /api/v2/agent                        # any agents?  [] -> go to step 4
GET /api/v2/agent/details/{agentId}      # -> agentEngines[].appname, packages[]
GET /api/v2/agent/{agentId}              # -> readyToRun   (per-agent = authoritative)
```

Read `readyToRun` **per-agent**. `GET /api/v2/runtimeEnvironment` returns a stale false-negative for
the same agent — see the warning in `01-orgs-and-entitlement.md`.

**Branch on the result:**

| What you see | Meaning | Do |
|---|---|---|
| `Data_Integration_Server` present **and `RUNNING`** | DI can run | Continue to 6 |
| Engine present but `DEPLOYING`/`STOPPED` | Not ready yet — tests will fail with a *moving* error | Wait and re-read. Do not reconfigure |
| Only `OpsInsightsDataCollector` | Telemetry only — **no scan, no profile, no mapping execution** | Steps 7–10 will fail with `403 APP_105060`. Go to **6b #1** (UI service enablement) |
| `agents: []` | Nothing installed | Step 4 |
| `readyToRun: false`, `packages: 0` | **Suspect the reading first** — if this came from the *list* endpoint it is probably a stale false-negative. Re-read `GET /api/v2/agent/{agentId}` | If per-agent also says `false`: `01-orgs-and-entitlement.md` §three-layer gate; check for a duplicate agent JVM (`pgrep -c -f "agentcore.impls.MainApp"` → expect 1) |

**Before pricing a purchase, check the PARENT org.** A sub-org showing one engine does not mean the
tenancy lacks them — the parent may already run everything and allocation is then free. Log in at the
parent, list its agents, and read *their* `agentEngines[]`. (But you cannot shortcut by binding a
sub-org connection to a parent's *shared* runtime — the test error changes, which looks like progress,
yet an unroutable bogus host returns the identical error, so nothing was ever attempted.)

**Never conclude "not entitled" from a 404 or from `products[]`.** With no agent installed,
entitlement is unresolved, not disproven.

## 4. Get the agent install token — HEADLESS

```bash
GET /api/v2/agent/installerInfo/linux64
# -> downloadUrl + 122-char org-scoped installToken
```

The token scopes the agent to **this** org — that is how you guarantee placement. Mint fresh; they
expire.

## 5. Install the Secure Agent on the host — NEEDS SHELL

🚨 **Size the host FIRST — before the installer, and before you enable anything.** This is the step
that is skipped and then costs the most. Enabling a full engine set on an undersized box does not fail
politely: it invites the OS OOM killer to kill whatever else lives there, **including the production
databases you came to govern**.

| Check | Floor |
|---|---|
| RAM | **≥16 GB** once Data Integration is on. 8 GB is not enough — engine `-Xmx` reservations alone can total ~9 GB |
| Free disk | **~20 GB.** The engine payload is ~20 GB (`downloads/` + `apps/`) and arrives in minutes |
| Swap | **Must exist.** With none, every spike goes straight to the OOM killer |
| Co-tenancy | Do not co-locate a full engine set with production databases on a small host |

Measured consequence of ignoring this on an 8 GB / 4 vCPU box with 23 engines enabled: **27 OOM-kill
events**, the database server killed **twice**, load average **54 on 4 cores**, engines flapping
`RUNNING`↔`STOPPED`, disk 79% → 95%. Data survived only because it was on container volumes with
restart policies. **Enable only the engines the use case needs** (governance ≈
`Data_Integration_Server` + `Connector_Service` + `Metadata_Foundation_Agent` +
`Metadata_Platform_Service`).

The installer must execute on the machine that can reach the databases. There is no remote-exec API on
DigitalOcean (`/console`, `/exec`, `/run` all 404; `user_data` is immutable at 405), so this needs SSH
or the provider's web console. See `04-environment-traps.md` for the access traps.

```bash
adduser --disabled-password --gecos "" infa      # the installer REFUSES to run as root
su - infa -c 'bash -s' <<'EOF'
set -e
cd ~ && mkdir -p infaagent && cd infaagent
curl -fL --retry 3 -O "<downloadUrl from step 4>"
sha256sum -c <<< "<published sha256>  agent64_install_ng_ext.<build>.bin"   # verify BEFORE executing
chmod +x agent64_install_ng_ext.<build>.bin && ./agent64_install_ng_ext.<build>.bin -i silent
cd ~/infaagent/apps/agentcore
./infaagent startup                              # must be running BEFORE token registration
./consoleAgentManager.sh configureToken <user> '<installToken>'
./consoleAgentManager.sh getstatus               # -> READY
EOF
```

Order matters: `configureToken` before startup gives *"Cannot connect to the Agent."*

Install a `systemd` unit now — a reboot silently stops an unmanaged agent. The naive unit fails; see
`04-environment-traps.md` for the working one.

**Verify from both sides:** on-host `getstatus` → `READY`, and `GET /api/v2/agent` → `active: true`
with the expected org. Then re-run step 3 — the engine list is the answer to the entitlement question.

## 6. Runtime environment — HEADLESS

```bash
GET  /api/v2/runtimeEnvironment       # prefer this on dmp-us; the v3 form 404s there
POST /api/v2/runtimeEnvironment       # create if needed
```

The agent creates its own RE on registration. The Hosted Agent is the only RE usable with no Secure
Agent.

## 6b. Enable the ENGINES, then the CONNECTORS — UI ONLY, and they are two different things

**This is the step most likely to be missed, because "the agent is installed" feels like done.** Three
separate things must each be true, and enabling one does *not* enable the next:

| # | Thing | How you know it is missing | Where |
|---|---|---|---|
| 1 | **Engine** (e.g. `Data_Integration_Server`) | `GET /api/v2/connection/test/{id}` → `403` *"No running service found of type `Data_Integration_Server` `<ver>.*` service for AgentGroup: `{reId}`"* | Administrator → Runtime Environments → agent → enable service. **No reinstall** — the agent polls and pulls packages |
| 2 | **Connector adapter** (e.g. PostgreSQL, MongoDB) | `403` *"Unable to fetch Connector attributes, Ensure adapter ID is valid and the service is enabled `[com.informatica.adapter.postgres]`"* | Administrator → Runtime Environments → agent → **add the connector**. Enabling engines does NOT do this |
| 3 | **Third-party JDBC driver** (JDBC_V2 targets) | `Unable to load driver` | Administrator's upload-JAR flow. A file copy into the driver dir is **not** sufficient — see below |

**Verify adapters on the host, not from the API.** The agent's real registry is:

```bash
ls <agent>/apps/Connector_Service/<ver>/connectors/cci/plugins/   # the ADAPTER_HOME its log prints
```

⚠️ **`GET /api/v2/connector` is not evidence.** It returns ~342 types including `PostgreSQL` and
`MongoDB v2` — that is Informatica's **global product catalog** (what they sell), not what this org
registered or this agent installed. A connection will `POST` **200** against a type whose adapter was
never deployed, and only fail at test time. Downloaded ≠ extracted ≠ registered: the package can sit in
`~/infaagent/downloads/` while no adapter jar exists.

**Engine status ≠ engine ready.** Read `agentEngines[].agentEngineStatus.status` — `DEPLOYING` is not
`RUNNING`, and while engines settle a connection test fails with a *moving* error (the engine it names
rotates, or it times out). **A rotating error is deployment progress, not a new fault** — do not start
re-configuring in response to it.

**Third-party driver reality check (unresolved, so budget for the UI):** a known-good jar copied into
**four** plausible directories — including next to Informatica's own working `ojdbc8.jar` in
`ext/connectors/thirdparty/informatica.<connector>/common/` — still gave `Unable to load driver` after
agent restarts, even though the jar had Java-8 bytecode (same class-file major version as `ojdbc8`), a
correct `META-INF/services/java.sql.Driver`, and connected fine from the host's own JVM. Treat driver
registration as a **UI step**. (Packaging trap: for ClickHouse 0.6.5 the `-all` classifier is *not*
shaded — it omits `com.clickhouse.client.*` and throws `NoClassDefFoundError`. Use `-shaded`.)

## 7. Create and test connections — HEADLESS

Bodies and the `TOOLKIT_CCI` rule: `02-request-bodies.md`.

```bash
POST /api/v2/connection               # -> id
GET  /api/v2/connection/test/{id}     # metadata handshake, 0 IPU
```

**Read the field names out of the connector's own manifest instead of guessing.** They differ per
connector and are not the obvious ones — JDBC_V2 wants **`username`** (not `user`) and
`additionalsecurityproperties` all-lowercase:

```bash
grep -o '"attributeName":"[a-zA-Z_]*"' <agent>/downloads/package-<CONNECTOR>.<ver>/CCIManifest.txt
```

That manifest also declares whether the connection type carries credentials at all:
`HASUSERNAME="NO" HASUSERPASSWORD="NO"` means the connector **cannot send them** — it will
authenticate as the driver's default account no matter what you set, and the fix is server-side. Prove
which it is by hitting the database directly with the same credentials (e.g. ClickHouse HTTP `8123`
with `X-ClickHouse-User`/`-Key`); if direct works and IDMC does not, IDMC is not sending them.

**Always read back after a write** — `POST /api/v2/connection/{id}` is the update verb (no `PUT`), and
a `200` whose value reverts is a silent rejection.

Triage: `403 APP_10519` → wrong `type` string, your problem. `403 APP_105060` → connection is fine,
**engine** missing (step 6b #1). `Unable to fetch Connector attributes` → **adapter** missing (6b #2).
`Unable to load driver` → **driver** missing (6b #3).

**Point at a table that has rows.** A scan or DQ pass over a 0-row database returns clean and means
nothing. Verify row counts in the database before claiming any governance result.

## 8. Create a task — HEADLESS (wrapping only)

```bash
POST /api/v2/mttask       # requires an existing mappingId
POST /api/v2/schedule
```

`mttask` **wraps** a mapping; it cannot author one. `APP_13533` means you tried.

## 9. Run it — HEADLESS

```bash
POST /api/v2/job          # {taskId, taskType:"MTT"} -> runId
```

Works even when `readyToRun` is `False`.

## 10. Monitor — HEADLESS

```bash
GET /api/v2/activity/activityLog?rowLimit=N     # history
GET /api/v2/activity/activityMonitor            # currently running
```

## 11. Author a design object — HEADLESS **by cloning only**

`POST /public/core/v3/objects` is 405. Use the migration-package clone in `02-request-bodies.md`.

## 12. Publish / deploy it — UI ONLY

No REST verb exists. A human clicks:

| Object | Where |
|---|---|
| CAI process | App Integration → Publish |
| MDM business entity | Business 360 Console → Modeler → Publish (this one deploy gates all five 360 apps) |
| Taskflow run URL | DI designer → Publish (or orchestrate with RunAJob waves instead) |
| Mapping logic | Mapping Designer canvas |
| Connector type, first registration | Administrator → Save, once |

Migration import creates the object but **does not deploy** it.

---

## The realistic shape of a headless feature

```
connections  ->  RunAJob  ->  activityLog  ->  export/promote
```

Neither REST nor MCP authors transformation logic (vendor roadmap: mapping-design API preview
~late 2026, GA ~2027). So keep transformation logic in SQL/DDL on the data platform side and use IDMC
for **connection, execution and monitoring**. That is the shape the evidence supports.
