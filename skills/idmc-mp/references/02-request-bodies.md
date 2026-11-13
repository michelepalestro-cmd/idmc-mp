# Request bodies that actually work

> **July 2026 snapshot.** Where this file says "UI-only", "no REST verb" or "walled", read it as a dated verdict:
> many were overturned later (KB `13 - Lessons Learned/Overturned Beliefs.md`, Laws 16-19). Before telling a user
> something is not possible, work the workaround ladder in KB `00 - Start Here/08 New Pipeline Milestones`.
> "Org A" / "Org B" are two example orgs; derive your own values (Law 1).

The bodies below were validated against a live org. Several required fields appear in **no vendor PDF**
— they were found by the validator loop at the end of this file.

**Credentials come from the environment, never from a file and never from chat.**

```bash
export IDMC_USER=... IDMC_PASS=...      # you supply; never written to disk
POD=<podA>  DOMAIN=dmp-us                 # Org A   — proven 2026-07-26
# POD=<podB> DOMAIN=dm-us                 # Org B — DIFFERENT domain, not a typo
BASE="https://$POD.$DOMAIN.informaticacloud.com/saas"
```

## Login — three planes, three different tokens

```bash
# v3 platform  -> INFA-SESSION-ID   (serves /public/core/v3/*)
curl -sS -X POST "$BASE/public/core/v3/login" \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"$IDMC_USER\",\"password\":\"$IDMC_PASS\"}"
# -> .userInfo.sessionId  ->  send as header  INFA-SESSION-ID

# v2 platform  -> icSessionId       (serves /api/v2/*)
curl -sS -X POST "$BASE/../ma/api/v2/user/login" \
  -H 'Content-Type: application/json' \
  -d "{\"@type\":\"login\",\"username\":\"$IDMC_USER\",\"password\":\"$IDMC_PASS\"}"
# -> .icSessionId + .serverUrl   ->  header  icSessionId
#    USE .serverUrl as the base for every later v2 call

# identity  -> the three-header combination (serves data360/*, marketplace, MDM)
curl -sS -X POST "https://$DOMAIN.informaticacloud.com/identity-service/api/v1/Login" \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"$IDMC_USER\",\"password\":\"$IDMC_PASS\"}"
curl -sS -X POST "https://$DOMAIN.informaticacloud.com/identity-service/api/v1/jwt/Token" \
  -H 'Content-Type: application/json' -d '{"client_id":"idmc_api"}'   # or cdlg_app
# -> send ALL THREE:  Authorization: Bearer <jwt>
#                     IDS-SESSION-ID: <sessionId>
#                     X-INFA-ORG-ID:  <orgId>
# Bearer alone = 401 on writes. JWT lives 30 minutes.
```

## Create a connection — `TOOLKIT_CCI` is the whole trick

**This is the one that cost a session.** `type` is not the connector name.

| Field | The trap | What actually works |
|---|---|---|
| `type` | `"PostgreSQL"` or the shortName `"PostgreSQLadapter"` → **403 APP_10519** "The connection type is not valid." | **`TOOLKIT_CCI`** — the generic CCI toolkit type for every modern connector |
| `instanceName` | A GUID or shortName | The **display string exactly as Administrator shows it** — `PostgreSQL`, `MongoDB`, `JDBCV2` |
| `connParams.hostName` | `host` | `hostName` — camel case, long form |
| `connParams.database` | Assuming `databaseName` is enough | **both** `databaseName` *and* `database` were present in the successful body |
| `connParams.authenticationType` | Omitting it (most examples do) | Mandatory. `"Standard"` is accepted |
| `runtimeEnvironmentId` | Guessing | Read from `GET /api/v2/runtimeEnvironment` |

```bash
curl -sS -X POST "$V2BASE/api/v2/connection" \
  -H "icSessionId: $ICS" -H 'Content-Type: application/json' -d '{
  "@type": "connection",
  "name": "POSTGRES-Org A",
  "type": "TOOLKIT_CCI",
  "instanceName": "PostgreSQL",
  "runtimeEnvironmentId": "<from GET /api/v2/runtimeEnvironment>",
  "connParams": {
    "hostName": "<host-ip>",
    "port": "5432",
    "databaseName": "orga_db",
    "database": "orga_db",
    "authenticationType": "Standard",
    "user": "<db user>",
    "password": "<from env, never inline>"
  }
}'
```

### The undocumented per-connector fields

Found only by the validator loop. In no local vendor guide.

| Connector | `instanceName` | Extra required `connParams` |
|---|---|---|
| PostgreSQL | `PostgreSQL` | `hostName`, `port`, `databaseName` **and** `database`, `authenticationType` |
| MongoDB | `MongoDB` | **`dbName`** — *not* `databaseName`; plus `hostname`, `port` |
| ClickHouse | **`JDBCV2`** — not `JDBC_V2` | **`jdbcdriverclassname`** and **`connectionstring`**. There is no native ClickHouse connector; JDBCV2 stores the target in `connectionstring`/`jdbcUrl` so `host`/`port`/`db` read back empty — that is correct, not a failed write. Needs the ClickHouse JDBC driver JAR staged on the agent |

Proven created on Org A: `POSTGRES-Org A` `<connId>`, `MONGODB-Org A`
`…0004`, `CLICKHOUSE-Org A` `…0005`, all bound to agent `<agentId>`.

**Update a connection:** `POST /api/v2/connection/{id}` — that *is* the update. No `PUT` exists.
**Test it:** `GET /api/v2/connection/test/{id}` — a metadata handshake, 0 IPU. `403 APP_105060`
"no running service found" here means the connection is fine and the **engine** is missing.

## Run a job and poll it

```bash
# RunAJob — works even when readyToRun is False
curl -sS -X POST "$V2BASE/api/v2/job" -H "icSessionId: $ICS" \
  -H 'Content-Type: application/json' \
  -d '{"@type":"job","taskId":"<mtTaskId>","taskType":"MTT"}'      # -> runId

curl -sS "$V2BASE/api/v2/activity/activityLog?rowLimit=5" -H "icSessionId: $ICS"
```

`POST /api/v2/mttask` needs an existing `mappingId` — `APP_13533` "specify a mapping id" means you
tried to author a mapping, which REST cannot do.

## Author a design object by cloning (the only headless authoring path)

`POST /public/core/v3/objects` is **405**. The migration package writes:

```
POST /public/core/v3/export            {objects:[<template id>]}    -> jobId
GET  /public/core/v3/export/{id}/package                           -> .zip
     retarget GUID / name / frsID inside the package
     recompute the SHA256 checksums
POST /public/core/v3/import/package                                 -> 200 checksumValid: true
     run the import                                                 -> SUCCESSFUL
```

Proven for `BUSINESS_ENTITY` (Person 41 fields, Supplier 15), `MDM_SRC_SYSTEM`, 2 reference entities,
`RULE_SPECIFICATION` (count 4 → 11 → 12). Free.

Two caveats: **import does not deploy** to the runtime (UI only), and a cloned logic body inherits the
template's expressions — making it *do* the right thing still needs the rulebuilder canvas. Hand-built
zips are rejected with `MigrationSvc_030`; only a genuine export works. Fails for `DTEMPLATE` mappings.

## CDGC scan

```bash
# all three identity headers, and capabilityNames MUST be non-empty
curl -sS -X POST "https://idmc-api.$DOMAIN.informaticacloud.com/data360/executable/v1/catalogsource/{id}" \
  -H "Authorization: Bearer $JWT" -H "IDS-SESSION-ID: $IDS" -H "X-INFA-ORG-ID: $ORG" \
  -H 'Content-Type: application/json' -d '{"capabilityNames":["CATALOG_EXTRACT"]}'   # -> 201 + job id

# job polling: the /api/ infix is REQUIRED
curl -sS ".../data360/observable/api/v1/jobs?limit=20" -H ...
```

Enterprise search takes **raw Elasticsearch DSL** at `/data360/search/api/v1/search` with header
`X-INFA-SEARCH-LANGUAGE: elasticsearch`.

## MDM record ingest

```bash
POST https://$POD-mdm.$DOMAIN.informaticacloud.com/business-entity/public/api/v1/entity/c360.person?sourceSystem=<sys>
# bare body; firstName + lastName required; trustScore is a STRING  -> 201
```

## Secure Agent install token — fully headless

```bash
curl -sS "$V2BASE/api/v2/agent/installerInfo/linux64" -H "icSessionId: $ICS"
# -> downloadUrl + a 122-char org-scoped installToken
```

No UI click needed to *get* the token. Installing still needs a shell on the target host.

## One MCP call

```bash
curl -sS -X POST "https://a2e-prod-$POD-mcp.$DOMAIN.informaticacloud.com/mcp-servers/public/..." \
  -H "IDS-SESSION-ID: $IDS" -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call",
       "params":{"name":"search_metadata","arguments":{"knowledgeQuery":"customer tables"}}}'
```

Protocol version `2025-06-18`, streamable HTTP (not stdio). On Org A the registry 404s, so confirm
`GET /public/core/v3/mcpServers` before assuming a server exists.

---

## The validator loop — how the undocumented fields were found

IDMC's create validators reveal **one missing field per request**. Exploit that instead of guessing:

1. `POST` the body you have.
2. `405`? The verb does not exist — stop.
3. `400`/`422`? **The verb exists.** Read the field name out of the error message.
4. Add that field. Repeat.
5. `403 APP_10519`? Not a missing field — a wrong `type`. Go back to `TOOLKIT_CCI`.

This is how `dbName`, `jdbcdriverclassname` and `connectionstring` surfaced. An empty-body POST is
safe: it cannot create an object.

**Distinguish a type error from an entitlement error.** If *one* type string produces a different
error than the others (ODBC returned `UI_13427` "Code page is not valid" while every other type
returned `APP_10519`), your request shape is correct and reaching real field validation — so the
others are being refused at the **type gate**, not by licensing.
