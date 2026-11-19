# IDMC MP: the Informatica IDMC co-pilot for Claude Code

A Claude Code plugin that makes Claude an IDMC co-pilot: it understands Informatica Intelligent Data Management Cloud
(IDMC / IICS), builds and runs it **without the UI**, and shortens the time to value of every IDMC service. Deploy and
promote, tune Secure Agents, build and speed up CDI pipelines, set up CDC, publish CAI processes, add data quality,
scan into the catalog, master data, and read IPU use, on the systems you already have.

Inside: 2,234 field lessons (error signature -> cause -> fix), one skill per IDMC area, twelve slash commands, a
13-stage deploy-and-operate playbook, a Python library with a login lockout guard, a mapping generator, three
rebuildable demo blueprints, and an endpoint-level API and MCP reference.

## Install

In Claude Code:

```
/plugin marketplace add michelepalestro-cmd/idmc-mp
/plugin install idmc-mp@idmc-mp
```

This repo offers exactly one plugin, `idmc-mp`. Restart Claude Code: the skills load on their own for IDMC work.

## Stay up to date

Turn on auto-update once: in Claude Code type `/plugin`, open **Marketplaces**, pick **idmc-mp** and enable
auto-update. Or update by hand: `claude plugin marketplace update idmc-mp`, then `claude plugin update idmc-mp@idmc-mp`.
Your login and your own lessons live in `~/.idmc_toolkit/`, outside the plugin, so updates never touch them.

## Quick start (first hour)

1. `/idmc-mp:connect`: creates your login file, then logs in once and prints your org.
2. `/idmc-mp:health-check`: read-only check of runtimes, agents, connections, projects and what the org can run.
3. `/idmc-mp:new-pipeline <source> to <target>`: builds, runs and proves a pipeline, milestone by milestone.

The full guide is the [Quick Start](knowledge/00-start-here/10-quick-start-your-first-hour-with-idmc-and-claude.md).

## What the co-pilot covers

| Area | Skill (loads on its own) | Commands | Ask, in your own words |
|---|---|---|---|
| Rules, login, routing, errors | `idmc-mp` | `connect`, `health-check`, `fix-error`, `save-lesson` | "why does this fail: `<error>`" |
| Secure Agent, runtime, connections | `idmc-secure-agent` | `tune-agent` | "install an agent on my VM and tune it for 20 parallel jobs" |
| Data Integration (CDI) | `idmc-cdi` | `new-pipeline`, `optimize` | "build a mapping from `<source>` to `<target>` and schedule it nightly" |
| Mass ingestion, CDC | `idmc-cdc` | | "set up CDC from my `<database>` to `<target>`" |
| Application Integration (CAI) | `idmc-cai` | | "publish a process that `<does X>` when `<event>`" |
| Data quality, profiling, cleaning | `idmc-data-quality` | `add-dq`, `clean-data` | "find the duplicate records in `<table>` and clean them with mappings" |
| Data governance, catalog (CDGC) | `idmc-governance` | `catalog` | "scan `<source>` into the catalog and show lineage to the report" |
| MDM | `idmc-mdm` | | "master the customer table into golden records" |
| CLAIRE, MCP | `idmc-claire-mcp` | | "connect to our managed MCP servers" |
| Deploy, promote, migrate | `idmc-deploy` | `promote` | "promote project `<X>` from dev to prod" |
| IPU, metering, job caps | `idmc-ipu` | `ipu-report` | "how many IPUs did we use this month, and on what" |

Informatica also publishes its own Claude plugin (`informatica-for-claude-platform`, catalog discovery and data
questions). It installs alongside this one; the [ecosystem guide](knowledge/09-claire-mcp/07-ecosystem-plugins-registries-community-tools.md)
covers it, all 23 managed MCP servers and the community tools worth knowing.

All commands are `/idmc-mp:<name>`. Two rules hold throughout: Claude builds with the systems you name (the examples
in the knowledge base are not recommendations), and it works the workaround ladder in your org before ever saying
something is not possible.

## Connect to your IDMC org (once)

Python 3.10+ (standard library only). Run `/idmc-mp:connect`, or from the plugin folder `python3 toolkit/check_login.py`
(Windows: `python` or `py`):

1. The first run creates `~/.idmc_toolkit/IDMC_LOGIN.txt` (in your home folder, outside the plugin).
2. Fill in `IDMC_USER` and `IDMC_PASS` of a **native** IDMC user (SSO-only users cannot call the API) and
   `IDMC_LOGIN_HOST` (the browser address after you sign in).
3. Run it again: it logs in once and prints your org and pod.

One file per org instead? Point `IDMC_CREDS_FILE` at it; its values win.

## How the repo is organized

```
.claude-plugin/   marketplace.json (one plugin) and plugin.json
skills/           idmc-mp (core: rules, login, routing) + one skill per IDMC area
commands/         the twelve /idmc-mp:<name> slash commands
knowledge/        the knowledge base: 00-start-here ... 14-claude-working-methods, playbook/, README (map), RULES
lessons/          lessons.jsonl (the source of truth), by-domain/ (readable), overturned-beliefs.md, case-studies/
toolkit/          lib/ (Python library), mapgen/ (mapping generator), demos/, setup/, tools/, check_login.py
tests/            run_tests.py (offline tests, run in CI) and USER_STORIES.md (each story with its live checklist)
```

Lessons are the evidence behind everything: each has an id (`L-<DOMAIN>-###`), a domain, the evidence that proved it,
and a status (current, superseded or disputed). The [lessons README](lessons/README.md) explains the format, and
[CONTRIBUTING.md](CONTRIBUTING.md) explains how to add one.

## Update / remove

`/plugin update idmc-mp@idmc-mp` - `/plugin uninstall idmc-mp@idmc-mp`.

## Share what you learn

`/idmc-mp:save-lesson` keeps new lessons on your machine. To add one for everyone, open an issue or a pull request with
the lesson in generic form: no org ids, hosts, people, customer names or secrets. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Notes

- Informatica's product documentation is **not** included; the skills point to https://docs.informatica.com for
  official wording.
- Demo blueprints in `toolkit/demos/` may need Docker and the accounts their README lists.
- Calls run against your org with your user's rights. Writes are dry runs until an org guard passes; jobs you run
  consume IPUs on your subscription.
- This is an independent community project, not an official Informatica product, and is not supported by
  Informatica. See [NOTICE](NOTICE).

## License

[MIT](LICENSE).
