---
name: idmc-connections
description: Use for Informatica IDMC connections to any database, warehouse, cloud store, file system or application (Snowflake, BigQuery, Databricks, PostgreSQL, Oracle, SQL Server, JDBC, Salesforce, SharePoint, S3, Azure, flat files and more): create, test, update and delete connections headless, find a connector's settings, and fix a connection that fails its test or a job (the four gates).
---

# IDMC co-pilot: connections

Part of the **idmc-mp** plugin (the IDMC co-pilot). Paths are relative to the plugin root, `${CLAUDE_PLUGIN_ROOT}`
(two folders above this skill's folder). Use `python3` (on Windows `python` or `py`).

## Ground rules (from the core `idmc-mp` skill; they always apply)
- **Lessons first.** Before any call or design choice, search the lessons:
  `grep -i "<connector or error>" "${CLAUDE_PLUGIN_ROOT}/knowledge/lessons/lessons.jsonl"` (this area: `"domain": "connections"`),
  then `knowledge/03-connections/lessons.md` and the user's own `~/.idmc_toolkit/lessons-local.jsonl`.
- **Prove the org first.** `python3 "${CLAUDE_PLUGIN_ROOT}/toolkit/check_login.py"` (one login attempt per run: retries
  lock the account). Take every host from `products[].baseApiUrl`; never hand-build a pod URL.
- **The user's systems are the right systems.** Build the connection the user names; a connector the KB has not covered
  is normal: read its metadata in the org, prove one test and one small run, record a lesson.
- **Never put a secret in the chat, a command line or the plugin.** Ask the user to enter connection passwords and keys
  themselves, or read them from a file outside the plugin; print key names, never values.
- **Writes are dry runs** until the org guard passes (`--execute --expect-org <orgIdV3>`); say what will change first.
- **A passing connection test is not proof:** prove a connection with a real data read.

## What users ask for
- Create a connection to their own source or target and test it.
- Fix a connection that fails its test, or a job that fails on a connection.
- Change a connection's settings (host, user, schema, key) without breaking the tasks that use it.

## How to work
1. Prove the org; list runtime environments and existing connections read-only (`/idmc-mp:health-check`).
2. Check the runtime environment has the connector's service enabled (`toolkit/lib/idmc_runtime_selections.py`).
3. Read the connector's metadata (`GET /api/v2/connector/metadata`: its `type` is the `instanceName`) and the notes for
   that connector (doc 02), then create the connection (doc 01). Secrets come from a 0600 file, never the chat.
4. Test it, then prove it with a small real read (a preview or a one-row task).
5. On failure, walk the four gates in order (doc 03): host, engine, adapter, driver.

## Read (in this order when unsure)
| Need | File |
|---|---|
| **Start here:** the cheat sheet (what works, what doesn't, fastest path, traps) | `knowledge/03-connections/README.md` |
| Create, test, update, delete connections | `knowledge/03-connections/01-connections-create-test-update-delete.md` |
| Per-connector settings that work | `knowledge/03-connections/02-connector-notes-bigquery-postgresql-salesforce-jdbc-flat-file.md` |
| A failing connection or job: the four gates | `knowledge/03-connections/03-troubleshooting-the-four-gates.md` |
| Services and connectors on the runtime environment | `knowledge/02-secure-agent/02-runtime-environments-services-connectors.md` |
| CAI (application integration) connections | `knowledge/07-app-integration/03-cai-connections-connectors-salesforce-oauth.md` |

## Tools (`--help` on each)
- `toolkit/lib/idmc_session.py`: org-aware session, read-only from the command line: `whoami`, `hosts`,
  `get v2 /api/v2/connection` (list), `get v2 /api/v2/connection/test/<connId>` (test, free)
- `toolkit/demos/retail_data_foundation/idmc/01_connections.py`: a working create-and-test script to copy for a new
  connection: JSON templates under `idmc/templates/connections/`, `plan --offline` renders the bodies with secrets
  hidden, `apply` creates or updates (dry run until `--execute --expect-org <orgIdV3>`), `test` tests them. Secrets are
  read from a 0600 `.env` outside the plugin at send time, never printed. It covers PostgreSQL, BigQuery and Salesforce;
  for another connector, add a template from doc 02.
- `toolkit/lib/idmc_runtime_selections.py`: services and connectors of a runtime environment
- `toolkit/lib/idmc_objects.py`: find existing connections and the assets that use them
- MCP tools, when `/idmc-mp:connect-mcp` has connected the org's servers (`mcp__plugin_idmc-mp_idmc__*`): `conn_*` (list, get, test,
  browse and preview; create and update only when the client allows writes); read a write back over REST

## When you learn something
Append a generic lesson (no org ids, hosts, people or secrets; same shape as `knowledge/lessons/lessons.jsonl`) to
`~/.idmc_toolkit/lessons-local.jsonl`, or run `/idmc-mp:save-lesson`. Never write inside the plugin folder.
