# IDMC MP: Informatica IDMC, headless, for Claude Code

A Claude Code plugin that teaches Claude to build and run Informatica Intelligent Data Management Cloud (IDMC / IICS)
**without the UI**: REST and MCP calls for CDI, CAI, CDQ, CDGC, MDM, Mass Ingestion / CDC, Secure Agents, runtime
environments, connections, mappings, taskflows, profiling, data quality, catalog and IPU metering.

Inside: 2,039 field lessons (error signature -> cause -> fix), a Quick Start, slash commands, a 13-stage
deploy-and-operate playbook, a Python script library with a login lockout guard, a mapping generator, three rebuildable
demo blueprints and an endpoint-level API and MCP reference.

## Install

In Claude Code:

```
/plugin marketplace add michelepalestro-cmd/idmc-mp
/plugin install idmc-mp@idmc-mp
```

Restart Claude Code. The skill loads on its own for IDMC work, or call it with `/idmc-mp:idmc-mp`.

## Quick start (first hour)

1. `/idmc-mp:connect`: creates your login file, then logs in once and prints your org.
2. `/idmc-mp:health-check`: read-only check of runtimes, agents, connections, projects and what the org can run.
3. `/idmc-mp:new-pipeline <source> to <target>`: builds, runs and proves a pipeline, milestone by milestone.

The full guide, with what to ask Claude for every common task and the lessons that trip up nearly every new user, is
the [Quick Start](<skills/idmc-mp/kb/00 - Start Here/10 Quick Start - your first hour with IDMC and Claude.md>).

## Commands

| Command | What it does |
|---|---|
| `/idmc-mp:connect` | set up the login file (outside the plugin) and prove the org |
| `/idmc-mp:health-check` | read-only org check: runtimes and agent health, connections, projects, what the org can run |
| `/idmc-mp:new-pipeline <source> to <target>` | plan, build, run and prove a pipeline on the systems you name |
| `/idmc-mp:fix-error <error text>` | look the error up in the lessons, then triage it in your org |
| `/idmc-mp:save-lesson <what you learned>` | save a new lesson, in generic form, to your local lessons file |

## Connect to your IDMC org (once)

Python 3.10+. Ask Claude to "connect to my IDMC org", or run `check_login.py` from the plugin's `skills/idmc-mp/kb/`
folder yourself:

1. The first run creates `~/.idmc_toolkit/IDMC_LOGIN.txt` (in your home folder, outside the plugin).
2. Fill in `IDMC_USER` and `IDMC_PASS` of a **native** IDMC user (SSO-only users cannot call the API) and
   `IDMC_LOGIN_HOST` (the browser address after you sign in).
3. Run it again: it logs in once and prints your org and pod.

One file per org instead? Point `IDMC_CREDS_FILE` at it; its values win.

## Use it

Or just ask, naming your own systems:

- "build a mapping from my `<source>` `<table>` to `<target>`, run it and show me the row counts"
- "set up CDC from my `<database>` to `<target>`"
- "put these mapping tasks in a taskflow and schedule it nightly"
- "profile `<table>`, suggest DQ rules and add them to the pipeline"
- "scan `<source>` into the catalog and show lineage to the report"
- "publish a CAI process that `<does X>` when `<event>`"
- "how many IPUs did we use this month, and on what"
- "why does this fail: `<error>`"

Two rules hold throughout: Claude builds with the systems you
name (the KB's examples are not recommendations), and it works the workaround ladder in your org before ever
saying something is not possible.

## Update / remove

`/plugin update idmc-mp@idmc-mp` (your login and your local lessons in `~/.idmc_toolkit/` are untouched) -
`/plugin uninstall idmc-mp@idmc-mp`.

## Share what you learn

`/idmc-mp:save-lesson` keeps new lessons on your machine. To add one for everyone, open an issue or a pull request
on this repo with the lesson in generic form: no org ids, hosts, people, customer names or secrets.

## Notes

- Informatica's product documentation is **not** included; the skill points to https://docs.informatica.com for official wording.
- Demo blueprints in `skills/idmc-mp/kb/demos/` may need Docker and the accounts their README lists.
- Calls run against your org with your user's rights. Writes are dry runs until an org guard passes; jobs you run
  consume IPUs on your subscription.
- This is an independent community project, not an official Informatica product, and is not supported by
  Informatica. See [NOTICE](NOTICE).

## License

[MIT](LICENSE).
