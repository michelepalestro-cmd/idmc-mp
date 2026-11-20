# IDMC MP: the Informatica IDMC co-pilot for Claude Code

[![tests](https://github.com/michelepalestro-cmd/idmc-mp/actions/workflows/tests.yml/badge.svg)](https://github.com/michelepalestro-cmd/idmc-mp/actions/workflows/tests.yml)
[![version](https://img.shields.io/badge/version-1.14.1-blue)](.github/CHANGELOG.md)
[![license: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

IDMC MP is a Claude Code plugin for **Informatica IDMC** (Intelligent Data Management Cloud, formerly IICS). You ask in
plain words; Claude builds, runs, checks and fixes the work in your IDMC org through its APIs, without clicking through
the IDMC website.

Its purpose is to let anyone set up IDMC without the trial and error: it carries **2,358 field lessons** from real
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
| MCP servers and CLAIRE | `idmc-claire-mcp` | | "connect Claude to our managed MCP servers" |
| Deploy, promote, migrate | `idmc-deploy` | `promote` | "promote project `<X>` from dev to prod" |
| IPU cost and job caps | `idmc-ipu` | `ipu-report` | "what used our IPUs this month?" |

Behind the skills:

- **A knowledge base, one folder per job** (`knowledge/01-login-and-orgs` ... `14-working-with-claude`), each opening
  with a one-page cheat sheet and holding its guides and lessons. The router is
  [knowledge/00-start-here](knowledge/00-start-here/README.md).
- **A Python toolkit** (standard library only): login with a lockout guard, org proof, a headless mapping generator, and
  rebuildable demo blueprints such as [customer mastering from a CSV](toolkit/demos/customer_master_csv/README.md).
- **Safety by default:** your login stays on your computer, every write is a dry run until you name the org it may
  change, and the plugin talks only to Informatica and the systems you connect.

## Install

In Claude Code:

```
/plugin marketplace add michelepalestro-cmd/idmc-mp
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
- Questions or problems: open an [issue](https://github.com/michelepalestro-cmd/idmc-mp/issues/new/choose).

IDMC MP is an independent community project. It is not an official Informatica product, is not endorsed or supported
by Informatica, and comes with no warranty. Informatica, IDMC, IICS, CLAIRE and related marks are trademarks of
Informatica LLC; other product names are trademarks of their owners and appear only to describe interoperability. No
Informatica documentation is redistributed here; references cite https://docs.informatica.com. Licensed under
[MIT](LICENSE).
