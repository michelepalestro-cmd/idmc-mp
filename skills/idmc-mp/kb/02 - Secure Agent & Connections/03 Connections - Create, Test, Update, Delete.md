# Connections: create, test, update, delete

**Answers:** How do I create, test, update and delete a connection over REST? Which body shape does a connector want?
What does a passing test prove, and what does not? Where can a connection run?

**Read when:** before creating or changing any connection, after a migration import (connections arrive without
secrets), or when a test passes but runs fail.

**Key rules:**
- CCI connectors take `type: "TOOLKIT_CCI"` plus the connector's display name in `instanceName`; APP_10519 means the
  wrong `type`, not a missing licence (L-CONN-001).
- Update by POSTing the full body to `/api/v2/connection/<connId>` and re-send every secret: GET returns them masked,
  and posting the mask back blanks the secret (L-CONN-006, L-CONN-007).
- A test is a free handshake from one agent; only a run that lands rows proves a connection, and an empty source browse
  proves nothing (L-CONN-014, L-CONN-015, L-CONN-016). For a connector that renews a delegated OAuth token, a pass
  proves only that the token renews: prove access with an object browse (L-CONN-101).
- Every connector a mapping uses must sit on the one agent that runs it, bound to that task's runtime environment
  (L-CONN-022, L-CONN-023).
- Secrets come from 0600 files on the host that holds them, never from a command line or a transcript (L-CONN-008).

**Related:** [04 Connector Notes](<04 Connector Notes (BigQuery, PostgreSQL, Salesforce, JDBC, Flat File).md>) ·
[05 Troubleshooting - the Four Gates](<05 Troubleshooting - the Four Gates.md>) ·
[02 Runtime Environments](<02 Runtime Environments - Services & Connectors.md>) ·
[Org-to-Org Migration Runbook](<../10 - Migration & Org Management/04 Org-to-Org Migration Runbook.md>) (imported connections arrive without secrets) ·
[Lessons: Secure Agent & Connections](<../13 - Lessons Learned/02 Secure Agent & Connections.md>)

**Last verified:** 2026-11-03 (evidence 2026-06-27 to 2026-11-03; 8 migrated connections re-secured and tested
headless; connections rebound off a downed Hosted Agent).

> Connections are v2-only objects with a full headless lifecycle: create, test (a free metadata handshake), update by
> POST to the id (there is no PUT) and delete. A new add-on connector type needed one UI-created connection before REST
> could create more (July 2026 evidence). Secret hygiene in general:
> [Secrets Hygiene](<../14 - Claude Working Methods & Tooling/06 Secrets Hygiene.md>).

All calls below go to `<serverUrl>` (the v2 base, `https://<pod>.<domain>.informaticacloud.com/saas`) with header
`icSessionId: <v2 session>` and JSON bodies. `/public/core/v3/connections` is 404: connections live on v2 only.

---

## 1. The connection object

| Field | CCI connectors (`TOOLKIT_CCI`) | Native (non-CCI) v2 types |
|---|---|---|
| `@type` | `"connection"` | `"connection"` |
| `type` | `"TOOLKIT_CCI"`, never the connector name | The native type, for example `CSVFile`; the Salesforce connection seen also kept its credentials at the top level (probably a native type) |
| `instanceName` | The connector name as Administrator shows it: `PostgreSQL`, `JDBCV2`, `Amazon S3 v2`, `MongoDB` | not used |
| Connector GUID | Carried by several proven bodies, for example `com.informatica.adapter.postgres`, `com.infa.adapter.bigqueryv2`, `com.informatica.adapter.jdbc_v2` | |
| `runtimeEnvironmentId` | The RE whose agent runs it (some bodies also carry `agentId`, `agentGroupId`, `orgId`) | same |
| Parameters | Nested in `connParams` (camelCase keys that vary by connector and build) | Top-level fields (for example `database` = the directory of a CSVFile connection; `username`, `password`, `securityToken` on Salesforce) |

Per-connector bodies and quirks are in [04 Connector Notes](<04 Connector Notes (BigQuery, PostgreSQL, Salesforce, JDBC, Flat File).md>).

## 2. Create

```
POST <serverUrl>/api/v2/connection
{
  "@type": "connection",
  "name": "<name>",
  "type": "TOOLKIT_CCI",
  "instanceName": "<connector name as shown in Administrator>",
  "runtimeEnvironmentId": "<reId>",
  "connParams": { "<key>": "<value>", "password": "<from a 0600 file at run time>" }
}
-> 200 with the stored object (id, orgId,...). Read it back with GET /api/v2/connection/<connId>.
```

(L-CONN-001, 2026-09-12.) A body with `type: "PostgreSQL"`, `"ClickHouse"` or a shortName, or a flat body without
`connParams`, returns 403 APP_10519 'The connection type is not valid'; that looks like licensing and is not.

**Discovering the fields**

1. **Read the manifest on the agent** (L-CONN-003, 2026-09-16):
   `grep -o '"attributeName":"[a-zA-Z_]*"' <agent_home>/downloads/package-<CONNECTOR>.<ver>/CCIManifest.txt`, or the
   plugin XML at `<agent_home>/downloads/package-<CONNECTOR>*/package/rdtm/plugins/*.xml`, which also says whether the
   type can carry credentials (`HASUSERNAME`, `HASUSERPASSWORD`).
2. **Copy a working one**: GET a UI-created or working connection of the same type and reuse its key set.
3. **Walk the validator** (L-CONN-002, 2026-07-26): each 403 APP_105054 (or 400/422) names one missing or misnamed
   attribute; add it and repeat until 200. 405 = no such verb, stop. A different error for one type string (for example
   `UI_13427 Code page is not valid`) means that shape reaches real validation.

**Clone rather than author** (L-CONN-004, 2026-09-03): GET a working connection, change `name` and the database (and
host), drop `id`, POST it to `/api/v2/connection`, test. For environment mirrors, take dev credentials from the running
containers (`docker inspect` env), use a predictable naming suffix, bind to the mirror's RE, and make the script
idempotent. Creating, testing and deleting connections costs 0 IPU. A clone is also how you get a scratch connection
for parity runs: a JDBC V2 target writes into the database named in the connection's URL, whatever the target object's
schema says, so never edit the live connection's URL for a test (L-CDI-040).

**New add-on connector types** (L-CONN-005, 2026-07-08): when the cloud side has never seen a connection of a type,
`POST /api/v2/connection` fails for every body shape with 403 'no connector with type=<shortName>' (for example
`GoogleBigQueryV2`) or APP_10519. Creating one connection of that type in Administrator > Connections registered the
type; afterwards REST managed it. Proven for BigQuery V2 and native PostgreSQL in July 2026; not re-tested since
connector selection became headless ([doc 02](<02 Runtime Environments - Services & Connectors.md>)), so try REST first
and fall back to one UI save.

## 3. Test

```
GET <serverUrl>/api/v2/connection/test/<connId>            # some native CCI tests append ?type=TOOLKIT_CCI
-> 200 "test successful"   |   403 APP_105060... (see section 8)
```

(L-CONN-014, 2026-09-23.) It is a read-only metadata handshake: no data moves and it costs 0 IPU, so use it freely for
reachability matrices across runtime environments. Wrong forms: `POST /api/v2/connection/test` answered 500 (APP_21000)
and `/api/v2/connection/<connId>/test` 404; one July record got 400 until `?type=TOOLKIT_CCI` was appended. The managed
MCP tool `connectionmanagement.test_connection_by_id` is a reliable alternative. `GET /api/v2/connection/<connId>`
carries a cached `status` of the last test (`success`, `failed`, or absent when never tested).

Other reads (L-CONN-016, 2026-07-25): `GET /api/v2/connection` lists connections with the cached test `status`;
`GET /api/v2/connection/source/<connId>?type=table` browses source objects (200 or 403 per connection, and it can
surface target-side errors such as a throttled warehouse); `GET /api/v2/connector` lists connector types;
`GET /api/v2/connector/metadata?connectorName=<name>` returns a connector's schema, and `200 []` means the connector is
not activated.

What a pass does and does not prove (L-CONN-015, 2026-08-19): it proves the handshake from that agent. It can pass with
a wrong stored password (a JDBC V2 test did, L-CONN-013, 2026-06-27) and it proves nothing about write paths, staging buckets or types.
The proof of a connection is a small run that lands rows, checked by count.

**Delegated OAuth: a pass proves only that the token renews** (L-CONN-101, 2026-10-06). For OAuth connectors that
renew a delegated token, a successful test says the refresh worked, not that the token can read metadata: a SharePoint
Online connection passed while every metadata call answered 401 (L-CONN-100, [doc 04](<04 Connector Notes (BigQuery, PostgreSQL, Salesforce, JDBC, Flat File).md>) §6).
Prove access by browsing objects, in the designer's object picker or with a designer session:

```
GET https://<pod>.<domain>.informaticacloud.com/da/w3.model/object/cloud/saas:<v2ConnId>@com.informatica.metadata.saas.Connection/search/?connKind=READ&searchRequest={"pageNumber":1,"maxRecordsCount":200,"context":{"txType":"SOURCE_TYPE","engineType":"CLOUD_NATIVE"}}
-> totalRecords, records[].attributes
```

**An empty browse proves nothing** (L-CONN-016): `GET /api/v2/connection/source/<connId>?type=table` (and
the same call without `?type`) returned `200 []` for two working PostgreSQL connections whose databases held tables and
whose tests passed. Confirm objects through a consumer instead (profile source fields, a mapping preview, a catalog
scan's Metadata Extraction). To prove that a test really reached the database and was not a cached status, diff the
database's own counters around it; on PostgreSQL one test opened one session and committed about 8 transactions in
1.4 s:

```sql
-- before and after GET /api/v2/connection/test/<connId>
SELECT sessions, xact_commit FROM pg_stat_database WHERE datname = '<db>';
```

## 4. Update

**The idiom** (L-CONN-006, 2026-09-28):

```
GET  <serverUrl>/api/v2/connection/<connId>
     change the fields; delete createTime, updateTime, createdBy, updatedBy
POST <serverUrl>/api/v2/connection/<connId>      <- the whole body, id in the path (there is no PUT)
GET  <serverUrl>/api/v2/connection/<connId>      <- compare the changed field; a reverted value = silent rejection
GET  <serverUrl>/api/v2/connection/test/<connId>
```

`POST /api/v2/connection` without the id is create-only: for an existing name it fails with REPO_10200 (name exists).

**Secrets come back masked** (L-CONN-007, 2026-09-23). The password or private key in the GET body is masked; POSTing
it back unchanged blanks the secret and breaks the connection. Re-supply the secret in every update, even one that only
flips an unrelated attribute, and re-test.

**Set secrets on the host that holds them** (L-CONN-008, 2026-09-28):

```python
# generic sketch: run it on the host that stores the secret; never print or log the value
import json, urllib.request
def call(path, body=None, method=None):
    h = {"icSessionId": sid, "Accept": "application/json"}
    data = json.dumps(body).encode if body is not None else None
    if data: h["Content-Type"] = "application/json"
    with urllib.request.urlopen(urllib.request.Request(server_url + path, data=data, headers=h, method=method), timeout=120) as r:
        return r.status, json.loads(r.read or b"{}")
def secret(path):                       # a 0600 file on this host, read at run time
    return open(path).read.strip
st, c = call(f"/api/v2/connection/{conn_id}")
for k in ("createTime", "updateTime", "createdBy", "updatedBy"):
    c.pop(k, None)
c.setdefault("connParams", {})["password"] = secret("<secret file>")   # privateKey for BigQuery V2;
                                                                      # top-level username/password/securityToken for Salesforce
st, _ = call(f"/api/v2/connection/{conn_id}", c, "POST")
st, t = call(f"/api/v2/connection/test/{conn_id}")
```

Connections that arrive through a migration import carry no passwords: bind each to the target runtime environment, set
its secret this way and test it on the target agent before any run.

**Rebind to another runtime environment** (L-CONN-132, 2026-11-03): the same idiom. Keep a backup of the GET body
without the secret, drop createTime, updateTime, createdBy, updatedBy and majorUpdateTime, set the body's
`runtimeEnvironmentId` **and** `connParams.agentGroupId` to the target runtime's v2 id (set `agentId` in the body and in
`connParams` only to pin one agent, and remove it when going back to the Hosted Agent), re-supply every masked secret
(for a BigQuery key, cycle the key formats until the test passes, L-CONN-036), POST, then test. This is the failover
step tasks alone do not cover (§6).

**Repoint after a database move** (L-CONN-009, 2026-07-12): update host and port in place with
`POST /api/v2/connection/<connId>` so mapping tasks and catalog sources that reference the id stay bound; scans that
failed after the move recover on their next run.

**Renames**

- Renaming a shared connection re-sends the whole object, can blank a key, and breaks tools that reference it by name;
  do it only in a coordinated window with the secret re-supplied (L-CONN-010, 2026-09-24).
- The proven rename (L-CONN-105, 2026-10-08): `POST /api/v2/connection/<connId>` with the full body and the new `name`;
  re-supply OAuth secrets after redeeming the stored refresh token once (a dead token would need an interactive sign-in);
  URL-quote names with spaces in `GET /api/v2/connection/name/<name>`; switch every builder and generator profile that
  looks the connection up by name in the same change, or its next run creates a duplicate; test every connection after.
- Renaming or retiring a database user breaks every IDMC connection still logging in as it ('password authentication
  failed for user <old>'). Before the change, list every connection whose `userName` is that role (not only the one named
  after the app), plus CDC tasks, BI tools and backups, and update them in the same window (L-CONN-011, 2026-09-26).

## 5. Delete

```
DELETE <serverUrl>/api/v2/connection/<connId>   -> 200
GET    <serverUrl>/api/v2/connection/<connId>   -> 403 or 404 = gone
```

(L-CONN-017, 2026-09-28.) An Amazon S3 v2 create-then-delete round trip left no orphan. Check users first: REPO_10242
means mappings still reference the connection, and 'used by another asset' means a catalog source holds it. In a
cleanup, connections go late: after CAI assets, tasks, mappings and catalog sources that use them (see
[Headless Deletes & Org Cleanup](<../10 - Migration & Org Management/06 Headless Deletes & Org Cleanup.md>)).

## 6. Where a connection can run

- **Same agent for everything a mapping touches** (L-CONN-022, 2026-07-08). Connectors are per agent: with the source
  connector on one agent and the target connector on another, a task died in about 2 s ('DTM process terminated
  unexpectedly', 0 rows). An abort at 'Importing Connection: <conn>' (`trepcnx.cpp:296`) means the task's runtime cannot
  use that connection. Bind connections to the runtime environment of the task that uses them.
- **'No running service found of type Connector_Service'** usually means the connection is bound to another runtime
  environment, such as a hosted or regional agent (L-CONN-023, 2026-09-16).
- **A lookup follows its connection's runtime, not the task's** (L-CONN-132, 2026-11-03). During a Hosted Agent outage a
  task already bound to a healthy Secure Agent still failed, because its lookup used a connection bound to the hosted
  runtime; lookup-free tasks on the same agent succeeded. A failover moves the connections as well as the tasks (§4),
  so inventory tasks per runtime (`GET /api/v2/mttask`) and connections per runtime (`GET /api/v2/connection`) before
  you need them.
- **The Hosted Agent** reaches only SaaS; a private host behind it creates fine and never connects (L-AGENT-036, 2026-07-26). Its name
  is reserved, so objects bound to it must be remapped when imported into an org without it (L-CONN-024, 2026-09-28).
- **Network reach**: an agent cannot reach another cloud's private addresses without a VPN or peering, and a database
  open only to tagged hosts needs the agent on one of them (L-AGENT-037, 2026-07-08).
- **Containers**: from a containerized agent, `127.0.0.1` is the agent container; use the Docker service names and prove
  reachability with a `/dev/tcp/<host>/<port>` probe inside the container (L-CONN-025, 2026-08-18). Containerized
  databases often bind a private interface; find it with `ss -ltnp` and `docker inspect` (L-CONN-026, 2026-07-26).
- **Same-host databases**: a native agent's connection to a database on its own VM uses `localhost` or the Docker
  network alias, never the VM's public name or IP. Clouds do not route a VM's traffic to its own public address back
  to it, and Docker's userland proxy rewrites the source address of host-local calls, so allowlist tests from the host
  answer 403 while real clients pass (L-ENV-014).

## 7. Credentials and hygiene

- Give IDMC its own database user instead of changing a shared default account, and replace POC credentials with
  least-privilege read-only users before the integration is real (L-CONN-012, 2026-08-20).
- Take credentials from the running application's own configuration (for example `printenv` inside the app container)
  rather than guessing; a green JDBC V2 test does not prove the password (L-CONN-013, 2026-06-27).
- Never pass secrets on a command line or print them; read them from 0600 files inside the script that needs them. Treat
  anything that reached a transcript as exposed and rotate it.
- v3 export packages mask connection passwords, but CAI app connections authored with `encrypted="false"` carry values
  such as an OAuth client secret in plaintext: treat package zips as secrets and rotate afterwards (L-CONN-064,
  2026-09-28).
- Service-account keys used in connections never expire by default; rotate them and prove the old key is dead in the
  cloud audit log (L-CONN-039, 2026-09-08).

## 8. Errors at a glance

| Signature | Meaning | Fix |
|---|---|---|
| 403 APP_10519 'The connection type is not valid' | Wrong `type` string | `TOOLKIT_CCI` + `instanceName` (L-CONN-001) |
| `200 []` from the source browse on a working connection | The browse is not evidence | Confirm through a profile, preview or scan (L-CONN-016) |
| Test passes, but the designer's object picker shows 0 objects (SharePoint Online) | The refresh token was minted for Microsoft Graph; every SharePoint metadata call answers 401 | A SharePoint-scoped refresh token ([doc 04](<04 Connector Notes (BigQuery, PostgreSQL, Salesforce, JDBC, Flat File).md>) §6, L-CONN-100), proven by an object browse (§3, L-CONN-101) |
| `403 CONSUMER_INVALID` from a BigQuery connection that used to work | Its service-account key belongs to a deleted cloud project | A key from a live project ([doc 04](<04 Connector Notes (BigQuery, PostgreSQL, Salesforce, JDBC, Flat File).md>) §2.3, L-ENV-052) |
| 403 'no connector with type=<shortName>' | Add-on type never registered in the org | One UI-created connection of that type (L-CONN-005) |
| 403 'There is no connector with type=' | Wrong `instanceName` spelling (for example `JDBC_V2`) | Use the Administrator display name (`JDBCV2`) (L-CONN-046) |
| 403 APP_105054 naming an attribute | Validator: one missing field | Add it, repeat (L-CONN-002) |
| REPO_10200 | Create against an existing name | Update with the id in the path (L-CONN-006) |
| 403 APP_105060 'No running service found of type <Engine>' | Engine not selected, deploying or down on that RE | [doc 02](<02 Runtime Environments - Services & Connectors.md>); L-AGENT-076 |
| 403 APP_105060 'Unable to fetch Connector attributes [com.informatica.adapter.<x>]' | Adapter not on the agent | Select the connector on the RE (L-CONN-019) |
| 'No running service found of type Connector_Service' | Bound to another RE | Rebind (L-CONN-023) |
| 403 APP_105060 naming the hosted agent group, on every hosted connection at once | A Hosted Agent outage, not a connection fault | Fail over tasks and connections ([doc 02](<02 Runtime Environments - Services & Connectors.md>) §1; L-AGENT-117, L-ENV-100) |
| Every task on one warehouse fails 'Custom quota exceeded' | The warehouse's own query quota is used up | Raise or separate the quota ([doc 04](<04 Connector Notes (BigQuery, PostgreSQL, Salesforce, JDBC, Flat File).md>) §2.4; L-CONN-133) |
| 'Unable to load driver' | JDBC driver not staged or not reloaded | [doc 04](<04 Connector Notes (BigQuery, PostgreSQL, Salesforce, JDBC, Flat File).md>) section 4 |
| `error [error [null]]` | Proves nothing: a bogus host gives the same | Check the binding (L-AGENT-038) |
| REPO_10242 on delete | Mappings still reference it | Delete or retarget them first (L-CONN-017) |

APP_105060 is a family: the same code carries the engine gate ('No running service found of type <Engine>'), the
adapter gate ('Unable to fetch Connector attributes') and a binding problem ('... of type Connector_Service'), so always
read the message (L-CONN-018, 2026-09-28). The full signature table, including host-level causes, is in
[05 Troubleshooting - the Four Gates](<05 Troubleshooting - the Four Gates.md>).

## 9. Overturned beliefs (connections)

| Believed | Until | Now | Lesson |
|---|---|---|---|
| Creating a CCI connection needs the Administrator UI | 2026-07-04 | The full v2 body creates it; only a brand-new add-on type needed one UI save | L-CONN-076 -> L-CONN-001 |
| A connector listed by `GET /api/v2/connector` is usable | 2026-07-26 | The list is a type catalog; the RE selections and the agent's adapter registry decide | L-CONN-079 -> L-CONN-021 |
| Flat-file connections need the flat-file connector enabled in the UI | 2026-09-23 | `type: CSVFile` works headless | L-CONN-081 -> L-CONN-065 |
| A never-browsed PostgreSQL connection cannot resolve objects over REST | 2026-09-22 | The object path format was the problem | L-CONN-084 -> L-CONN-028 |
