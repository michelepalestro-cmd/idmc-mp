# Connections: cheat sheet

Creating, testing, updating, rebinding and deleting IDMC connections over the v2 REST plane, and diagnosing why a test
or run fails; it applies to every source or target the user names, and after migrations (imported connections arrive
without secrets).

**Start with:** `/idmc-mp:health-check` (lists connections and their runtimes), `/idmc-mp:fix-error` when a test or
run fails, and `python3 toolkit/lib/idmc_session.py get v2 /api/v2/connection` for reads.
Open first: [Connections: create, test, update, delete](01-connections-create-test-update-delete.md).

## What works (headless)

All on `<serverUrl>` (`https://<pod>.<domain>.informaticacloud.com/saas`) with `icSessionId`; connections are v2-only (L-AUTH-013).

| Task | How (exact route/tool/command) | Lesson |
|---|---|---|
| Create (CCI) | `POST /api/v2/connection` with `"@type":"connection"`, `"type":"TOOLKIT_CCI"`, `instanceName` = Administrator display name, `runtimeEnvironmentId`, nested `connParams` | L-CONN-001 |
| Find the fields | Agent manifest `downloads/package-<CONNECTOR>.<ver>/CCIManifest.txt`; or copy a working connection; or walk `APP_105054` one field at a time | L-CONN-003, L-CONN-002 |
| Clone | GET a working one, change `name` (+ host/db), drop `id`, POST, test | L-CONN-004 |
| Clone into another org | Drop `agentId`, `agentGroupId`, `orgId` from `connParams`, set the target runtime, re-supply secrets | L-CONN-122 |
| Test (free, 0 IPU) | `GET /api/v2/connection/test/<connId>`, or MCP `connectionmanagement.test_connection_by_id` | L-CONN-014 |
| Update | GET, drop `createTime`/`updateTime`/`createdBy`/`updatedBy`, re-supply every secret, `POST /api/v2/connection/<connId>` (full body), GET, test | L-CONN-006, L-CONN-007 |
| Partial update | Same POST with header `Update-Mode: PARTIAL` (reported, code-read) | L-CONN-142 (reported) |
| Rebind to another runtime | Set `runtimeEnvironmentId` **and** `connParams.agentGroupId`, re-supply secrets, POST, test | L-CONN-132 |
| Repoint after a DB move | Update host/port in place: ids and bindings stay | L-CONN-009 |
| Delete | `DELETE /api/v2/connection/<connId>` -> 200; GET -> 403/404 = gone | L-CONN-017 |
| Flat file | `"type":"CSVFile"`, directory on the agent host in top-level `database` | L-CONN-065 |
| Look up by name | `GET /api/v2/connection/name/<url-encoded name>` | L-CONN-149 (reported) |
| Connector formats | `GET /api/v2/connector/metadata?connectorName=<name>` (`cciMeta` `supportedEngineTypes`) | L-CONN-130 |

## What doesn't work, and the workaround

| Wall | Workaround | Lesson |
|---|---|---|
| `type` = connector name or shortName, or a flat body -> 403 `APP_10519` (looks like licensing; it is not) | `TOOLKIT_CCI` + `instanceName` + `connParams` | L-CONN-001 |
| `instanceName` `JDBC_V2` / `JDBC V2` -> 'There is no connector with type=' | `JDBCV2` (display name) | L-CONN-046 |
| `POST /api/v2/connection/test` -> 500 `APP_21000`; `/connection/<id>/test` -> 404 | `GET /api/v2/connection/test/<connId>` | L-CONN-014 |
| Posting the masked secret back | Blanks the secret; re-supply it in every update | L-CONN-007 |
| Name-only or partial rename body -> 403 `APP_10501` | Full GET body with the new name and secrets | L-CONN-123, L-CONN-105 |
| Create on an existing name -> `REPO_10200` | POST to `/api/v2/connection/<connId>` | L-CONN-006 |
| Name with parentheses -> `APP_10500` | Letters, digits, spaces and `_ . + - ,` | L-CONN-124 |
| Brand-new add-on type -> 'no connector with type=<shortName>' | Try REST first; else one UI-created connection registers the type | L-CONN-005 |
| Copy adapter jars to enable a connector | Select the connector on the runtime | L-CONN-020 |
| `GET /api/v2/connector` as "what can run" | Type catalog only; read the runtime's selections | L-CONN-021 |
| `?type=` / `?name=` filters on `GET /api/v2/connection` | Ignored; filter client-side or use `/name/` | L-CONN-149 (reported) |
| Reading a stored password back (GET returns `***`) | Plan one connection per database at provisioning | L-CONN-136 |

## Fastest safe path

1. Prove the org (`/idmc-mp:connect`) and name the runtime of the task that will use the connection. **Proof:**
   `runtimeEnvironmentId` read live; every connector of a mapping must sit on that one agent (L-CONN-022).
2. Check the gates in order: host, engine, adapter, driver. **Proof:** engine RUNNING in `agentEngines[]`, connector
   `enabled` in the runtime's selections (L-AGENT-034, L-CONN-019).
3. Get the body by cloning a working connection or reading the manifest. **Proof:** key set matches a working one (L-CONN-004, L-CONN-003).
4. Read secrets from a 0600 file on the host that holds them, inside the script; never a command line (L-CONN-008).
5. `POST /api/v2/connection`. **Proof:** 200 with an id; `GET /api/v2/connection/<connId>` reads it back.
6. `GET /api/v2/connection/test/<connId>`. **Proof:** 'test successful' (L-CONN-014).
7. Run a small job that lands rows. **Proof:** row count on the target; a test is only a handshake (L-CONN-015).
8. For updates: GET -> modify -> POST full body with secrets -> GET -> test. **Proof:** changed field reads back (a
   reverted value is a silent rejection) and the test passes (L-CONN-006).

## Top traps

- `APP_105060` is a family -> read the message: 'No running service ... <Engine>' = engine, 'Unable to fetch Connector
  attributes' = adapter, '... Connector_Service' = bound elsewhere (L-CONN-018, L-CONN-023).
- Green JDBC V2 test with a wrong password -> a test does not prove credentials (L-CONN-013, L-CONN-048).
- Delegated OAuth test passes but 0 objects -> it proves only token renewal; prove access by an object browse
  (SharePoint: SharePoint-scoped refresh token) (L-CONN-101, L-CONN-100).
- 'DTM process terminated unexpectedly' in ~2 s, 0 rows -> source and target connectors on different agents (L-CONN-022);
  with an empty session log -> the connection login failed; read the agent's `tomcat_<ver>.log` (L-CONN-109).
- Task moved to a healthy agent still fails at a lookup -> the lookup follows its connection's runtime -> rebind the connection too (L-CONN-132).
- Private host bound to the Hosted Agent -> creates with 200, never connects (L-AGENT-036).
- `127.0.0.1` from a containerized agent is the agent container -> Docker service names (L-CONN-025).
- `200 []` from `/api/v2/connection/source/<connId>` -> proves nothing -> confirm via profile, preview or scan (L-CONN-016).
- `error [error [null]]` -> a bogus host gives the same -> check the binding (L-AGENT-038).
- BigQuery 'Invalid PKCS#8 data' -> key format differs by consumer and pod -> one connection per consumer (L-CONN-035, L-CONN-036).
- PostgreSQL 'Object(s) [X] not found' / `SDK_APP_COM_20000` -> path `<schema>/TABLE/<table>` (L-CONN-028).
- 'Unable to load driver' -> jar in `ext/connectors/thirdparty/informatica.jdbc_v2/common/` (+ `ext/deploy_to_main`), then
  restart (L-CONN-049, L-CONN-050); `REPO_10242` on delete -> mappings still use it (L-CONN-017).

## Go deeper

- [Connections: create, test, update, delete](01-connections-create-test-update-delete.md): object shape, lifecycle, where a connection can run, error table.
- [Connector notes](02-connector-notes-bigquery-postgresql-salesforce-jdbc-flat-file.md): PostgreSQL, BigQuery, Salesforce, JDBC V2, flat file, SharePoint and others; `truncateTarget` traps.
- [Troubleshooting: the four gates](03-troubleshooting-the-four-gates.md): host, engine, adapter, driver; every signature with cause and fix.
- [Lessons: Connections](lessons.md): every current and superseded `L-CONN` lesson.
- [Runtime environments: services and connectors](../02-secure-agent/02-runtime-environments-services-connectors.md): selecting connectors on a runtime.
- [Error Triage](../00-start-here/04-error-triage.md): the org-wide error table.
