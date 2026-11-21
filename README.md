# IDMC MP: the Informatica IDMC co-pilot for Claude Code

[![tests](https://github.com/michelepalestro-cmd/idmc-mp-informatica-claude-plugin/actions/workflows/tests.yml/badge.svg)](https://github.com/michelepalestro-cmd/idmc-mp-informatica-claude-plugin/actions/workflows/tests.yml)
[![version](https://img.shields.io/badge/version-1.15.2-blue)](.github/CHANGELOG.md)
[![license: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

IDMC MP is a Claude Code plugin for **Informatica IDMC** (Intelligent Data Management Cloud, formerly IICS). You ask in
plain words; Claude builds, runs, checks and fixes the work in your IDMC org without clicking through the IDMC
website. It works both ways IDMC can be reached: the **REST APIs** and **Informatica's managed MCP servers**, and it
picks the right one per task ([MCP or API?](#informaticas-mcp-servers)).

Its purpose is to let anyone set up IDMC without the trial and error: it carries **2,369 field lessons** from real
builds (what works, what does not, the error that fooled everyone and its fix), so Claude starts from what is already
known instead of rediscovering it.

## What it includes

**Skills** load on their own when your request matches; **commands** are typed as `/idmc-mp:<name>`.

| Area | Skill | Commands | For example |
|---|---|---|---|
| Rules, login, routing, errors | `idmc-mp` | `connect`, `health-check`, `fix-error`, `save-lesson` | "why does this fail: `<error>`" |
| Secure Agent and runtime environments | `idmc-secure-agent` | `tune-agent` | "install an agent on my VM and tune it" |
| Connections to any system | `idmc-connections` | | "connect to our Snowflake account" |
| Mappings, tasks, taskflows (CDI) | `idmc-cdi` | `new-pipeline`, `optimize` | "build a nightly pipeline from `<source>` to `<target>`" |
| Mass ingestion and CDC | `idmc-cdc` | | "set up CDC from my database" |
| Application integration (CAI) | `idmc-cai` | | "publish a process that runs when `<event>`" |
| Data quality, profiling, cleaning | `idmc-data-quality` | `add-dq`, `clean-data` | "find the duplicates in `<table>` and clean them" |
| Catalog, glossary, lineage (CDGC) | `idmc-governance` | `catalog` | "scan `<source>` and show lineage to the report" |
| Master data (MDM) | `idmc-mdm` | | "master the customer table into golden records" |
| MCP servers and CLAIRE | `idmc-claire-mcp` | `connect-mcp` | "connect Claude to our managed MCP servers" |
| Deploy, promote, migrate | `idmc-deploy` | `promote` | "promote project `<X>` from dev to prod" |
| IPU cost and job caps | `idmc-ipu` | `ipu-report` | "what used our IPUs this month?" |

Behind the skills:

- **A knowledge base, one folder per job** (`knowledge/01-login-and-orgs` ... `14-working-with-claude`), each opening
  with a one-page cheat sheet and holding its guides and lessons. The router is
  [knowledge/00-start-here](knowledge/00-start-here/README.md).
- **A Python toolkit** (standard library only): login with a lockout guard, org proof, a headless mapping generator, and
  rebuildable demo blueprints such as [customer mastering from a CSV](toolkit/demos/customer_master_csv/README.md).
- **An MCP bridge** that turns your org's managed MCP servers into Claude's own tools after `/idmc-mp:connect-mcp`,
  read-only unless you choose otherwise.
- **Safety by default:** your login stays on your computer, every write is a dry run until you name the org it may
  change, and the plugin talks only to Informatica and the systems you connect.

## Informatica's MCP servers

The knowledge base covers **Informatica's managed MCP servers** (25 servers and 271 tools in the November 2026
registry, including four CAI servers) plus the CLAIRE agent server: what each one can and cannot do, its tools, how to
log in to it, and the traps found using it.

**How to connect:** after `/idmc-mp:connect`, run **`/idmc-mp:connect-mcp`**. It lists the servers your org has
(Informatica switches them on per org), creates a scoped OAuth client whose secret goes straight to a private file on
your computer, and tests it. After a restart, every server's tools are Claude's own tools, through a small bridge the
plugin starts by itself. It is **read-only** unless you choose otherwise, Claude Code still asks before each call, and
tokens renew by themselves. Without this step Claude can still call the servers through the toolkit. Details:
[MCP servers and CLAIRE](knowledge/11-mcp-claire/README.md).

**MCP or API?** Both reach the same IDMC services, so neither can do what the service itself can't. Claude picks per
task ([full table](knowledge/11-mcp-claire/05-mcp-vs-rest-when-to-use-which.md)):

| Use MCP for | Use the REST API for |
|---|---|
| Questions in plain language (CLAIRE orchestrator and data exploration) | Building mappings, deploying CDC, publishing CAI processes (an MCP CAI publish is listed but unproven) |
| Fuzzy customer match (MCP only) | Lineage (the MCP lineage tool's backend answers "Unknown tool") and data profiling (REST only) |
| Profiling and cleansing an uploaded file (DQ agent, MCP only) | Bulk work, exact bodies, paging and read-back, such as batch address checks (1,000 per call vs 1) |
| One-off address checks, running and watching tasks, CAI process monitoring | Anything a scheduled job repeats: same input, same result |
| "Why is it failing?": agent health, connection tests, browsing and previewing a table | Loops: MCP adds 0.25-0.65 s per call and its list tools do not page |

Using MCP is not free: the services behind each call use IPUs as usual. An MCP failure comes back HTTP 200 with the
error in the text, so Claude reads the text, not the status.

**What has been tested:**

| Status | Servers |
|---|---|
| **Every read-only tool called live** (24, 2026-11-20) | Job Management, Audit Management, Asset Promotion, CDGC Metadata Search, Catalog Discovery, CDGC Data Quality Score, Customer Identification, Data Provisioning, IPU Management, Troubleshooting, Connection Management, Address Verification, CLAIRE Data Quality Agent, CLAIRE Orchestrator, CLAIRE Data Exploration Agent, Data Marketplace Order Management, Data Access Management, IDMC Asset Documentation, CAI Administration, CAI Asset Management, CAI Connection Management, CAI Job Management, Data Quality Assets, Catalog Asset History |
| **Listed but broken** | Catalog Asset History `get_asset_history` and Catalog Discovery `get_asset_lineage`: their backends answer "Unknown tool" |
| **Write tools listed, not called** | Catalog Enrichment (all write), CAI publish and run, policy and DQ-asset writes, order approvals |
| **Called live earlier, not in the November registries** | Secure Agent Management; User Management and Log Management were listed in September only |

The CLAIRE agent server also ran as a local MCP server inside Claude Code. For an untested server, Claude says it is
untested and confirms with one read-only call before relying on it.

## Install

In Claude Code:

```
/plugin marketplace add michelepalestro-cmd/idmc-mp-informatica-claude-plugin
```

```
/plugin install idmc-mp@idmc-mp
```

Close Claude Code and open it again, then run `/idmc-mp:connect`. The full guide, including what to do when a login fails, is
[Setup and login](knowledge/00-start-here/11-setup-and-login.md).

## Repository layout

```
commands/    the slash commands
skills/      one skill per IDMC area (Claude loads them on its own)
knowledge/   one folder per job (cheat sheet, guides, lessons), the lessons file, and reference material
toolkit/     Python: library, mapping generator, demo blueprints, setup, repository tools and tests
```

## More

- [Changelog](.github/CHANGELOG.md) · [Contributing](.github/CONTRIBUTING.md) · [Security](.github/SECURITY.md) ·
  [Code of conduct](.github/CODE_OF_CONDUCT.md)
- Questions or problems: open an [issue](https://github.com/michelepalestro-cmd/idmc-mp-informatica-claude-plugin/issues/new/choose).

IDMC MP is an independent community project. It is not an official Informatica product, is not endorsed or supported
by Informatica, and comes with no warranty. Informatica, IDMC, IICS, CLAIRE and related marks are trademarks of
Informatica LLC; other product names are trademarks of their owners and appear only to describe interoperability. No
Informatica documentation is redistributed here; references cite https://docs.informatica.com. Licensed under
[MIT](LICENSE).
