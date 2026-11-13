# Orgs, entitlement and the three-layer gate

> **July 2026 snapshot.** Where this file says "UI-only", "no REST verb" or "walled", read it as a dated verdict:
> many were overturned later (KB `13 - Lessons Learned/Overturned Beliefs.md`, Laws 16-19). Before telling a user
> something is not possible, work the workaround ladder in KB `00 - Start Here/08 New Pipeline Milestones`.
> "Org A" / "Org B" are two example orgs; derive your own values (Law 1).

Which org you are in decides which answers apply. This file also settles the question that has burned
the most sessions: *is this blocked by licensing, or by something else that looks like licensing?*

## The two orgs

| | Org A | Org B |
|---|---|---|
| Name | `Org A` | `data` |
| Org ID v3 / v1 | `<orgGuid>` | `<orgGuid>` |
| Org ID v2 | `<orgIdA>` | `<orgIdB>` |
| Pod / domain | `<podA>` / `dmp-us` | `<podB>` / `dm-us` |
| v2 + v3 base | `https://<podA>.dmp-us.informaticacloud.com/saas` | `https://<podB>.dm-us.informaticacloud.com/saas` |
| Parent | `<orgGuid>` (the parent org) | — |
| Secure agents | 1 — `<agentName>`, `<agentId>`, v76.17 (DI 77.0.2.x) | 2 — `<agentName>`, `<agentName>` |
| Engines | **23** since the 2026-07-26 UI enablement (was **1** — `OpsInsightsDataCollector`). 9 `RUNNING` incl. `Data_Integration_Server` 77.0.2, `Connector_Service` 21.0.2; 14 still `DEPLOYING` | **17** incl. `Data_Integration_Server`, `Database_Ingestion`, `process-engine`, `DAM`, `At_Scale_Server` |
| Privileges | 876, 38 roles | 897 |
| Connectors visible | 342 | 153 |
| Design objects | 0 of every type | populated |

**`dmp-us` is not `dm-us`.** One character; every borrowed URL 404s silently.

**Both org-ID shapes are correct.** The v2 plane reports `<orgIdA>` for the same org the v3 plane calls
`<orgGuid>`, and v2 object IDs are prefixed with it (`<connId>`). Not a bug.

**Org A is a sub-org.** All four runtime environments are inherited from the parent, which is why
they showed zero agents before one was installed.

## Where Org A and Org B disagree

Every row here is a live-verified difference. Do not carry a verdict across.

| Endpoint | Org B (<podB>/dm-us) | Org A (<podA>/dmp-us) | Conclusion |
|---|---|---|---|
| `GET /api/v2/license` | 200 | 404 | Sub-orgs do not expose it. Read privileges instead |
| `GET /api/v2/loginAudit` | 200 | 404 | Parent-org only. Use `/api/v2/auditlog` (live on both) |
| `GET /api/v2/dss`, `dtemplate`, `dmask`, `dreplicate`, `plan`, `fileListener` | 200 | 404 | These mount **per pod and per licensed engine**, not per org. Biggest source of false "not entitled" |
| `GET /public/core/v3/runtimeEnvironments` | 200 | 404 | On `dmp-us` use the v2 form `/api/v2/runtimeEnvironment` → 200 |
| `GET /public/core/v3/agent`, `agentGroups`, `tags`, `licenses`, `orgs`, `permissions` | 200 | 404 | The v3 admin surface is thinner on `dmp-us` |
| `data360/**` (CDGC + Marketplace) | 200 with real payloads | **200, zero bytes** | Gateway artifact — see the bogus-twin test |
| `GET /public/core/v3/mcpServers` | 200 (registry lists servers) | **404** | No vendor MCP server is reachable on Org A |
| MDM `searchmatch` | 200 | 404 | |
| CDQ dictionaries | 200 | 401 | Role gap, not a wall |
| Profiling `profiles` | 200 | 500 | |
| CAI process list / publish | 200 | 403 / 500 | |
| Migration **export** | 200 | **200** — real handler `MigrationSvcV3Api_002` | Works on both |
| Migration **import** | 200 | 404 on all 6 candidate paths | |
| Generic object create | 405 | 405 | v3 catalog is read-only everywhere |

## The three-layer gate — why "licensed" is not enough

A capability needs **all three**. Each fails with a different signature, and they are routinely
confused for each other.

```
Layer 1  LICENSED        Administrator > Licenses shows the entitlement
             |           fails as: absent from the Licenses page
             v
Layer 2  READY TO RUN    the runtime env has readyToRun: true
             |           fails as: readyToRun false, and IDMC sends NO engine packages
             v
Layer 3  ENGINE PRESENT  agentEngines[] contains the engine that does the work
                         fails as: 403 APP_105060 "no running service found"
```

**Layer 1 was misdiagnosed on Org A.** Every license path is absent from REST — `/v3/licenses` 404,
`/api/v2/license` 404, `/api/v2/org/{id}` 403 `REPO_10404` — so a session inferred "not licensed."
The Administrator → Licenses page then showed **321 custom licenses** including `Advanced Taskflow`
under Data Integration, plus scanner packages. Licensing was never the problem.

**Read Layer 1 from the UI, not from REST.** There is no licensing *inventory* API. Administrator →
Organization → Licenses (or, for a sub-org, the parent's Sub-Organizations → Licenses).

**But consumption IS readable headlessly** — the one licensing-adjacent path that works. Proven live:

```bash
POST /public/core/v3/license/metering/ExportMeteringData
     {"jobType":"SUMMARY","startDate":"2026-06-01T00:00:00Z","endDate":"2026-07-26T00:00:00Z"}
# -> 201 + jobId.  Poll GET .../{jobId} until SUCCESS (~3 min), then
GET  .../{jobId}/download        # -> a ZIP of one CSV per org. Read BYTES, not text.
```

Dates must be **full ISO-8601 with a zone** — a bare `2026-06-01` gives `400 V3API_007`; `jobType`
alone gives `400 LS_147`. Reads accrue 0 IPU. Useful inference: **near-zero metered usage is itself
evidence that nothing has ever run in the org** — on Org A the only line was API Center at
0.0000133 IPU, independently confirming no integration job had executed.

**Layer 2 is the one nobody checks:**

```bash
GET /api/v2/agent/{agentId}       # -> readyToRun, active, packages[]   <- READ THIS ONE
GET /api/v2/runtimeEnvironment    # -> agents[].readyToRun   <- STALE. Do not trust it.
```

⚠️ **The list endpoint lies.** `/api/v2/runtimeEnvironment` reported `readyToRun: false` for the
Org A agent while `/api/v2/agent/{id}` reported `true` for the same agent, reproducible 3 reads out
of 3. Believing the list value produced the diagnosis "Layer 2 failure, engine packages never sent" —
which was wrong; Layer 2 passes. **Always read agent health per-agent**, and treat a Layer 2 verdict
built on the list endpoint as unproven.

`readyToRun: false` means the agent registered and reports `READY` on the host, but IDMC has not
marked it runnable — so the package manifest it receives contains no DI packages. No error is raised;
the packages are simply never offered. On the host, `ls ~/infaagent/apps/` shows only what was
actually delivered.

Known cause: **two agent JVMs fighting the singleton lock** —
`SingularApplicationLock: Cannot acquire lock, there is probably another instance running`. A
`systemd` unit with `Restart=on-failure` respawning against an already-running manual start produces
exactly this. Check `pgrep -c -f "agentcore.impls.MainApp"` — expect 1. Use `-c -f` with the full
class name: `pgrep -af "agentcore.*MainApp" | wc -l` **counts your own SSH command string too**, so it
returns 2 on a healthy host and manufactures a phantom lock conflict.

**Confirm health on-host — and `cd` first.** `consoleAgentManager.sh` sources `./version.sh` relative
to `$PWD`, so an absolute-path call dies with `cannot open ./version.sh` and reads as a dead agent:

```bash
su - infa -c 'cd ~/infaagent/apps/agentcore && ./consoleAgentManager.sh getstatus'   # -> READY
```

**Layer 3 is ground truth for entitlement:**

```bash
GET /api/v2/agent/details/{agentId}    # -> agentEngines[].appname, packages[]
```

Trust the **per-agent** endpoint, not the list endpoint, for health. `packages: 0` with a licensed org
points at Layer 2.

## Never infer entitlement from these

| Signal | Why it lies |
|---|---|
| `products[]` on login | A licensing label. Org A shows only `Integration Cloud` while holding CDGC, Marketplace, MDM and API Manager privileges |
| A `404` | Wrong path or not mounted on this pod |
| `objects?q=type=='X'` → `count: 0` | The filter is **not validated** — `TOTALLY_FAKE_TYPE_ZZZ` returns the same clean empty envelope |
| The connector catalog (342 items) | The global product catalog — what Informatica sells, not what this org licenses |
| No agent installed | Then entitlement is **UNRESOLVED, not disproven**. Say so |

## What has no REST plane at all

Stop probing these; they are UI-only by design:

- **Sub-org license allocation** — parent's Administrator → Sub-Organizations → Licenses
- **Engine enablement on an agent** — Administrator → Runtime Environments → agent → enable service
- **Connector type registration** — one UI Save in Administrator, then REST works

⚠️ **Do not cite `403 APP_13401` / `500 CMN_001` as the evidence.** Under `/api/v2/agent/*` those are
**router artifacts**: bogus twins return them byte-identically (`/api/v2/agent/bogusZZZnope` → 403
`APP_13401`; `/api/v2/agent/bogusZZZ/{id}` → 500 `CMN_001`). Law 2 applies to error codes, not just
200s. The UI-only verdict stands on other grounds: `POST /api/v2/agent/{id}` with `agentEngines[]`
returns 500 and **read-back shows `agentEngines: []`** (a silent no-op), and every probe repeated **as
the parent-org admin** returns identical results — a parent cannot even read a sub-org's agent
(`403 APP_13407`).

**A missing engine names itself.** The useful error is on the connection test, not the agent API:

```bash
GET /api/v2/connection/test/{id}
# 403 "No running service found of type Data_Integration_Server 77.* service
#      for AgentGroup: {runtimeEnvId}"     <- cleanest Layer-3 proof
```

After a license change **no reinstall is needed**: the agent polls IDMC and pulls new engine packages
itself, exactly as it fetched OpsInsights. **Verified end-to-end 2026-07-26:** enabling services took
the agent from 1 engine to **22**, all reporting `DEPLOYING` within minutes, packages downloading with
no agent restart.

🚨 **Size the HOST before you enable services — this is the trap that bit hardest.** Entitlement is
not the only gate; the box has to be able to run what you turn on. Enabling *all* services put **23
engines** on a **7.8 GiB / 4 vCPU** agent host whose engine `-Xmx` reservations alone sum to **~9.2 GB —
more RAM than the machine has**. Consequences, all observed:

- **27 OOM-kill events**; the Linux OOM killer killed **`clickhouse-server` twice**, plus `mongod`
  and `systemd`. Only Docker volumes + container restart policies saved the data (row counts verified
  identical to baseline afterward).
- Load average **54 on 4 cores**; engines **flapping** between `RUNNING` and `STOPPED`.
- `~/infaagent` grew to **25 GB** (19 GB of `downloads/`), root disk **79% → 95%**.
- Connection tests then fail in a *moving* way — the engine named in the error rotates
  (`Data_Integration_Server 77.*` → `Connector_Service 21.*` → timeout) because whichever engine the
  handshake needs is being killed mid-flight. **That looks like a config bug and is not one.**

**Rules of thumb:** enable only the engines the use case needs (governance ≈ `Data_Integration_Server`
+ `Connector_Service` + `Metadata_Foundation_Agent` + `Metadata_Platform_Service`); budget **≥16 GB
RAM** once DI is on; ensure **~20 GB free disk**; **add swap** — with none, every spike goes straight
to the OOM killer. Never co-locate a full engine set with production databases on a small host.

**`DEPLOYING` is not `RUNNING`.** Read the per-engine status, not just the engine list:

```bash
GET /api/v2/agent/details/{agentId}   # -> agentEngines[].agentEngineStatus.status
```

While engines deploy, a connection test keeps returning `APP_105060` — but **watch which engine it
names**. It moving on (e.g. `Data_Integration_Server 77.*` → `Connector_Service 21.*`) is *progress*,
not a new wall. Isolated `500 CMN_001` on a single `appspec/dependency/package/.../urls/...` fetch is
retried automatically (backoff to 80 s) and does not stall the others.

## Open questions

1. ~~Does parent **the parent org** carry DI + CDGC engines to allocate down to Org A?~~
   **RESOLVED 2026-07-26 — yes, and it was an assignment, not a purchase.** The parent
   (`<parentOrgId>` / `<orgGuid>`) logs in with the *same* password as the sub-org-native user
   and enumerates **22 sub-orgs**; its agent `shared-sa-…` (`<parentReId>`) is
   `active=true, readyToRun=true` with **22 engines** incl. `Data_Integration_Server`,
   `Metadata_Foundation_Agent`, `Metadata_Platform_Service`, `Database_Ingestion`, `process-engine`.
   Enabling those services on the sub-org's own agent then delivered all 22.
   **Lesson: always check the parent before pricing a purchase.**
   **But do not borrow the parent's shared RE as a shortcut** — a sub-org connection bound to shared RE
   `<parentReId>` creates fine (200) and its test error changes from `APP_105060` to
   `error [error [null]]`, which reads as progress but is not: an **unroutable bogus host returns the
   identical error**, so it is host-independent and proves no reachability.
2. Org A `data360` returns zero-byte 200s **while CDGC is licensed** there. Deployment question, not
   a licensing one — do not raise it as an entitlement ticket.
3. `<podA>-apigw` returns 503 — route exists, nothing behind it. Unexplained.
