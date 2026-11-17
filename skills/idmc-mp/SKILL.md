---
name: idmc-mp
description: Use when working with Informatica IDMC / IICS without its UI or building IDMC assets and demos - REST or MCP calls to CDI, CAI, CDQ, CDGC, MDM, DBMI/CDC, Secure Agents, runtime environments, connections, mappings, taskflows, profiling, data quality rules, catalog, IPU metering - or when an IDMC call returns 401, 403, 404, 405, 500, APP_10519, APP_105060, a zero-byte 200, or readyToRun false.
---

# IDMC MP: build and run Informatica IDMC headless

Everything here is relative to this skill's folder (the base directory shown when the skill loads).
`kb/` is the full Master IDMC KB: topic folders `00`-`14`, ~1,970 field lessons, a Python library, a mapping
generator and three demo blueprints. Informatica's own product guides are not bundled: use https://docs.informatica.com.

## The two rules (they override everything else)
1. **Never push the user to another technology.** Build with the source, target and connectors the user names. The
   KB's systems (PostgreSQL, BigQuery, Snowflake, Databricks, Salesforce, SharePoint, ClickHouse, Tableau, files) are
   examples, not recommendations. If the user has not named a system, ask.
2. **Never say "not possible" before the workaround ladder is worked in this org:** lessons -> re-probe -> another
   plane -> clone a UI-made object -> capture the UI's own call -> another IDMC component -> a Python bridge -> one
   residual click (`kb/00 - Start Here/08 New Pipeline Milestones - any source, any target.md`). Then report what each
   rung showed and the nearest working path. The KB is not an allow-list. **Native IDMC first; Python only as a bridge.**

## Before any IDMC call
- **Search the lessons first (Law 1):** `grep -ril "<thing or error>" "kb/13 - Lessons Learned"` and
  `grep -i "<thing>" "kb/13 - Lessons Learned/lessons.jsonl"` (ids `L-<DOMAIN>-###`; status current / disputed /
  superseded; `Overturned Beliefs.md` lists what flipped). Also `references/06-lessons-field.md` (error-signature index) and the user's own
  `~/.idmc_toolkit/lessons-local.jsonl` if it exists.
- **Establish the org (Law 0):** log in, take `products[].baseApiUrl` as the base, never hand-build the pod host.
- **Read the playbook** `references/00-headless-playbook.md` for Laws 0-7, error triage, per-service gotchas and the
  preflight. Its key facts: a 200 can be fake (probe a bogus twin); 404 = wrong path, not unlicensed; entitlement comes
  from `agentEngines[]`, never `products[]`; no HEAD/OPTIONS (probe with an empty POST); read and run are headless,
  authoring/publish/deploy usually go through packages, clones or the UI's own call; MCP never replaces the Secure Agent.

## Connect (once per person)
Run `python "kb/check_login.py"`. The first run creates `~/.idmc_toolkit/IDMC_LOGIN.txt` (outside this plugin,
which is replaced on every update) and stops; the user fills in `IDMC_USER`, `IDMC_PASS` of a **native** IDMC
user and `IDMC_LOGIN_HOST` (the browser address after sign-in), then runs it again: it logs in once and prints
the org. One login attempt per run: rapid re-logins lock the account. A per-org file elsewhere works too: set
`IDMC_CREDS_FILE` to its path (its values win). Never write credentials inside this plugin's folder, and never
print, share or commit a filled-in login.
If the user gives you their credentials: write them only to `~/.idmc_toolkit/IDMC_LOGIN.txt` (or the file they
choose), and confirm with key names and a masked password, never the value. If `IDMC_CREDS_FILE` is already
set or the home file is filled in, it is already connected: run `check_login.py`, don't ask again.

## Where to go
| Task | Start at |
|---|---|
| New to IDMC with Claude: first hour, what to ask, top lessons | `kb/00 - Start Here/10 Quick Start - your first hour with IDMC and Claude.md` |
| New pipeline, any source to any target | `kb/00 - Start Here/08 New Pipeline Milestones - any source, any target.md` |
| Any single asset type | `kb/README.md` ("Create any IDMC asset" table) |
| Login, orgs, pods, sessions | `kb/01 - Access, Auth & Orgs/` |
| Secure Agent, runtime, connections | `kb/02 - Secure Agent & Connections/`, `references/03-bootstrap.md` (HOST -> ENGINE -> ADAPTER -> DRIVER) |
| Mappings, taskflows, mapping generator | `kb/03 - Data Integration (CDI)/00 Mapping Fast Path - read this first.md`, then `kb/core/mapgen/` |
| Mass ingestion / CDC | `kb/04 - Mass Ingestion & CDC/` |
| CAI processes, publish | `kb/05 - Application Integration (CAI)/` |
| Profiling, DQ rules | `kb/06 - Data Quality & Profiling/` |
| Catalog, lineage, glossary | `kb/07 - Catalog & Governance (CDGC)/` |
| MDM SaaS, golden records | `kb/08 - MDM/` |
| CLAIRE, MCP servers | `kb/09 - CLAIRE & MCP/`, `references/10-mcp.md` |
| Export/import, migration | `kb/10 - Migration & Org Management/` |
| IPU, metering, job caps | `kb/11 - IPU, Metering & Licensing/`, `kb/12 - Reference Library/IICS-to-IPUs KB/` |
| Endpoints and verbs per service | `references/05-endpoints-by-service.md`, `kb/12 - Reference Library/` |
| A documented cap or limit | `kb/12 - Reference Library/IDMC API & MCP Reference/Claude IDMC How To/CSV - every endpoint/09_limits_and_caps.csv`; Informatica's exact wording at https://docs.informatica.com |
| A worked end-to-end case (property data: profiling, DQ, mastering, ClickHouse) | `kb/13 - Lessons Learned/Field Lessons - Property Data Platform.md` |
| Python helpers (session, lockout guard, CDGC, jobs) | `kb/14 - Claude Working Methods & Tooling/Script Library/` |
| Rebuildable demos (CDC, CDI, CAI, CDQ, CDGC) | `kb/demos/` (start at `BLUEPRINT_CONVENTIONS.md`) |

**Informatica guides:** not bundled (they are Informatica's copyrighted documentation). When the user needs
Informatica's official wording or a documented limit, answer from the KB lessons and the org itself (connector
metadata, one connection test), say which parts are field evidence, and point to https://docs.informatica.com for the
official text. Never present one product's guide as another's.

## When you learn something
This plugin's folder is replaced on every update, so never write into `kb/`. Append the new lesson (same shape
as `kb/13 - Lessons Learned/lessons.jsonl`, generic: no org ids, hosts, people or secrets) to
`~/.idmc_toolkit/lessons-local.jsonl`, and grep that file too in Law 1. Keep the user's own ids in their
blueprint `config.json` (outside the plugin), never in a lesson. To share a lesson with everyone, the user can
open an issue or pull request on the plugin's GitHub repo.

## Red flags - stop and re-check
- About to say "IDMC can't" or "not licensed" without the lessons grep and the ladder.
- About to suggest a different source, target or cloud than the user named.
- A second login attempt after a failure (lockout), or a password in a command line or output.
- Hand-building a pod URL instead of using `baseApiUrl`.
