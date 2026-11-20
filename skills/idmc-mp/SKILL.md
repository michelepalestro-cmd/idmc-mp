---
name: idmc-mp
description: Use when working with Informatica IDMC / IICS without its UI, or planning, deploying, optimizing or troubleshooting IDMC - REST or MCP calls to CDI, CAI, CDQ, CDGC, MDM, DBMI/CDC, Secure Agents, runtime environments, connections, mappings, taskflows, profiling, data quality rules, catalog, IPU metering - or when an IDMC call returns 401, 403, 404, 405, 500, APP_10519, APP_105060, a zero-byte 200, or readyToRun false. Also the starting point for anything Informatica, Informatica Cloud or IICS: setting it up, logging in, or any error.
---

# IDMC MP: the IDMC co-pilot for Claude

This is the core skill of the **idmc-mp** plugin: the rules, the login, and where to go. Paths are relative to the
plugin root, `${CLAUDE_PLUGIN_ROOT}` (two folders above this skill's folder).
**Python command:** use `python3` on macOS and Linux (macOS has no `python`), and `python` or `py` on Windows.
The library needs only the standard library (Python 3.10+).

## The two rules (they override everything else)
1. **Never push the user to another technology.** Build with the source, target and connectors the user names. The
   KB's systems (PostgreSQL, BigQuery, Snowflake, Databricks, Salesforce, SharePoint, ClickHouse, Tableau, files) are
   examples, not recommendations. If the user has not named a system, ask.
2. **Never say "not possible" before the workaround ladder is worked in this org:** lessons -> re-probe -> another
   plane -> clone a UI-made object -> capture the UI's own call -> another IDMC component -> a Python bridge -> one
   residual click (`knowledge/00-start-here/08-new-pipeline-milestones-any-source-any-target.md`). Then report what
   each rung showed and the nearest working path. The KB is not an allow-list. **Native IDMC first; Python only as a
   bridge.**

## Where everything is
One folder per job under `knowledge/` (`01-login-and-orgs` ... `14-working-with-claude`). Each starts with a one-page
`README.md` cheat sheet (what works, what doesn't, the fastest safe path, the top traps with lesson ids) and holds that
job's guides and its `lessons.md`. The router is `knowledge/00-start-here/README.md` ("I want to..." -> command, cheat
sheet, tool). Open the cheat sheet first; open a long guide only when the cheat sheet points there.

## Before any IDMC call (in this order)
1. **Open the job's cheat sheet** (`knowledge/<job>/README.md`, via the router `knowledge/00-start-here/README.md`):
   what works, what doesn't, the fastest safe path and the top traps, each with its lesson id.
2. **Search the lessons (Law 1)** for the exact thing or error:
   `grep -i "<thing or error>" "${CLAUDE_PLUGIN_ROOT}/knowledge/lessons/lessons.jsonl"` (one JSON lesson per line: `id`,
   `domain`, `kind`, `title`, `text`, `evidence`, `status` current / disputed / superseded). For an error code or
   message, look in `knowledge/lessons/error-index.md` first, then grep `lessons.jsonl`. Also grep the user's own
   `~/.idmc_toolkit/lessons-local.jsonl` if it exists.
   A lesson marked Reported or Documented is not proven live: say so.
3. **Establish the org (Law 0):** `python3 "${CLAUDE_PLUGIN_ROOT}/toolkit/check_login.py"`; take `products[].baseApiUrl`
   as the base, never hand-build a pod host.
4. **Open a long guide only when the cheat sheet points there**, and only the section you need (`grep -n "^#"` first).

Facts that hold everywhere ([the laws](../../knowledge/00-start-here/02-the-laws-of-headless-idmc.md)): a 200 can be
fake (probe a bogus twin); 404 = wrong path, not unlicensed; entitlement comes from `agentEngines[]`, never
`products[]`; read and run are headless, authoring and publish usually go through packages, clones or the UI's own
call; MCP never replaces the Secure Agent.

## Connect (once per person)
Run `/idmc-mp:connect` (it runs `toolkit/check_login.py`). The first time, it creates `~/.idmc_toolkit/IDMC_LOGIN.txt`
outside the plugin and prints a `--setup` command: the user runs that in a terminal and answers three questions (the
IDMC address from the browser, the user name, the password, hidden). It checks the values offline and makes **one**
login attempt: never retry a failed login, wrong logins lock the account. If `IDMC_CREDS_FILE` is set or the file is
filled in, the user is already connected: run `check_login.py`, don't ask again. **Never ask for, write or repeat a
password in the chat**; if one is pasted, tell the user to change it and enter the new one with `--setup`. Setup and
login help: `knowledge/00-start-here/11-setup-and-login.md`.

## Where to go: one skill per area
| The user wants to... | Skill | Start at |
|---|---|---|
| Get going: first hour, what to ask, top lessons | this one | `knowledge/00-start-here/10-quick-start-your-first-hour-with-idmc-and-claude.md` |
| Deploy IDMC end to end (13 stages) | `idmc-deploy` | `knowledge/00-start-here/07-end-to-end-playbook-deploy-and-operate-idmc-with-claude.md` |
| A new pipeline, any source to any target | `idmc-cdi` | `knowledge/00-start-here/08-new-pipeline-milestones-any-source-any-target.md` |
| Install, run, tune a Secure Agent; runtime environments | `idmc-secure-agent` | `knowledge/02-secure-agent/` |
| Connections to any system: create, test, fix | `idmc-connections` | `knowledge/03-connections/` |
| Mappings, tasks, taskflows, schedules, CDI speed and cost | `idmc-cdi` | `knowledge/04-mappings/00-mapping-fast-path-read-this-first.md` |
| Mass ingestion / CDC | `idmc-cdc` | `knowledge/06-cdc-ingestion/` |
| CAI processes, publish, events | `idmc-cai` | `knowledge/07-app-integration/` |
| Profiling, DQ rules, scorecards | `idmc-data-quality` | `knowledge/08-data-quality/` |
| Catalog, glossary, lineage (data governance) | `idmc-governance` | `knowledge/09-catalog-lineage/` |
| MDM, golden records | `idmc-mdm` | `knowledge/10-mdm/` |
| CLAIRE, MCP servers | `idmc-claire-mcp` | `knowledge/11-mcp-claire/` |
| Promote dev to prod, org-to-org migration, cleanup | `idmc-deploy` | `knowledge/12-deploy-migrate/` |
| IPU, metering, job caps, cost | `idmc-ipu` | `knowledge/13-ipu-cost/` |
| Login, orgs, pods, sessions, users and roles | this one | `knowledge/01-login-and-orgs/` |
| Something failed | this one | `/idmc-mp:fix-error`, `knowledge/00-start-here/04-error-triage.md` |
| Any single asset type | this one | `knowledge/00-start-here/README.md` (the router), then that job's cheat sheet |
| Endpoints and verbs per service; documented caps | this one | `knowledge/reference/idmc-api-mcp-reference/claude-idmc-how-to/idmc-endpoint-dictionary.md`, `knowledge/reference/` |
| Python helpers (session, lockout guard, CDGC, jobs) | this one | `toolkit/lib/README.md` |
| Rebuildable demos (CDC, CDI, CAI, CDQ, CDGC) | this one | `toolkit/demos/BLUEPRINT_CONVENTIONS.md` |

The router is `knowledge/00-start-here/README.md`; the rules for every session are `knowledge/RULES.md`.

**Informatica guides:** not bundled (they are Informatica's copyrighted documentation). When the user needs
Informatica's official wording or a documented limit, answer from the lessons and the org itself (connector metadata,
one connection test), say which parts are field evidence, and point to https://docs.informatica.com.

## When you learn something
This plugin's folder is replaced on every update, so never write into it. Append the new lesson (same shape as
`knowledge/lessons/lessons.jsonl`, generic: no org ids, hosts, people or secrets) to `~/.idmc_toolkit/lessons-local.jsonl`
(`/idmc-mp:save-lesson`), and grep that file too in Law 1. Keep the user's own ids in their blueprint `config.json`
(outside the plugin), never in a lesson. To share a lesson with everyone, open an issue or pull request on the
plugin's GitHub repo (`.github/CONTRIBUTING.md`).

## Red flags - stop and re-check
- About to say "IDMC can't" or "not licensed" without the lessons grep and the ladder.
- About to suggest a different source, target or cloud than the user named.
- A second login attempt after a failure (lockout), or a password in a command line or output.
- Hand-building a pod URL instead of using `baseApiUrl`.
- A write without the org guard, or a "done" without evidence (ids, counts, job states).
