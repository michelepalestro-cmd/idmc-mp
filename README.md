# IDMC MP: the Informatica IDMC co-pilot for Claude Code

[![tests](https://github.com/michelepalestro-cmd/idmc-mp/actions/workflows/tests.yml/badge.svg)](https://github.com/michelepalestro-cmd/idmc-mp/actions/workflows/tests.yml)
[![version](https://img.shields.io/badge/version-1.8.0-blue)](CHANGELOG.md)
[![license: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

IDMC MP turns Claude Code into a helper for **Informatica IDMC** (Intelligent Data Management Cloud, formerly IICS).
You tell Claude what you want in plain words, and it builds, runs, checks and fixes it in your IDMC org **without
clicking through the IDMC website**: pipelines, Secure Agents, data quality, the catalog, MDM, deployments and IPU costs.

It comes with 2,340 field lessons (what went wrong in real orgs and how it was fixed), one skill per IDMC area,
twelve slash commands and a small Python toolkit that guards your login.

---

## Setup in 3 steps (about 10 minutes)

### Before you start

You need four things. Tick them off:

- [ ] **Claude Code** is installed and opens. ([How to install Claude Code](https://code.claude.com/docs))
- [ ] **Python 3.10 or newer.** To check, open a terminal window and type `python3 --version` (Windows: `py --version`).
      If it says 3.10 or higher, you are fine. If not, install it from [python.org](https://www.python.org/downloads/).
- [ ] **An IDMC user name and password that work on the IDMC sign-in page.**
      If you normally sign in with your company's single sign-on (SSO) button, that will **not** work here:
      ask your IDMC admin for a "native" IDMC user with its own password. A separate service user for Claude is best.
- [ ] **You can sign in to IDMC in your web browser** with that user. (You will copy the address from the browser.)

> **What is a terminal window?** It is the app where you type commands.
> Mac: open **Terminal** (press Cmd+Space, type "Terminal"). Windows: open **PowerShell** (Start menu, type
> "PowerShell"). Linux: open your **Terminal** app.

### Step 1: Install the plugin

Open Claude Code and type these two lines, one at a time, pressing Enter after each:

```
/plugin marketplace add michelepalestro-cmd/idmc-mp
```

```
/plugin install idmc-mp@idmc-mp
```

Then close Claude Code and open it again.

### Step 2: Give it your IDMC login

In Claude Code, type:

```
/idmc-mp:connect
```

Claude creates your private login file and shows you a command that ends in `--setup`. Now pick **one** way to fill
it in:

**Way A: let it ask you (easiest).** Copy the `--setup` command Claude showed you, paste it into a **terminal window**
(not into Claude Code) and press Enter. It asks three questions:

1. **The IDMC address.** Sign in to IDMC in your browser. Click the address bar at the top, copy everything, and paste
   it. It looks like `https://usw5.dm-us.informaticacloud.com/cloudUX/home`.
2. **Your IDMC user name.** Exactly what you type on the IDMC sign-in page.
3. **Your password.** You will **not** see anything while you type. That is normal. Press Enter when done.

**Way B: fill in the file yourself.** Claude also shows you a command that opens the file in a text editor. Fill in the
three lines at the bottom so they look like this example, then save:

```
IDMC_USER=svc_claude
IDMC_PASS=MyS3cretPassw0rd
IDMC_LOGIN_HOST=https://usw5.dm-us.informaticacloud.com/cloudUX/home
```

No quotes, and no spaces around the `=` sign.

> **Never paste your password into the Claude chat.** It only belongs in that file, which stays on your computer in
> your home folder (`~/.idmc_toolkit/IDMC_LOGIN.txt`) and only you can read.

### Step 3: Check that it works

In Claude Code, type `/idmc-mp:connect` again. When it works you see:

```
CONNECTED to IDMC
  Org name : <your org>
  Org id   : <22 letters and numbers>
  Pod      : <for example usw5>
  User     : <your user>
```

That's it. Try `/idmc-mp:health-check` next: it looks around your org and changes nothing.

---

## If the login doesn't work

**Stop after one failed try.** IDMC locks your account after a few wrong logins, and every new try can restart the
lock. The plugin tries only once per run and checks your file on your computer first, so it never wastes a try on an
empty or example value.

| What you see | What it means | What to do |
|---|---|---|
| `Your login is not ready yet` | A line in your file is empty or still has the example in it. Nothing was sent to IDMC. | Fill in the line it names, then run `/idmc-mp:connect` again. |
| `user name or password is wrong` (`IDS_085` or `UI_10000`) | Most often the **address is for the wrong region**, not a wrong password. | Sign in in your browser and paste that exact address into `IDMC_LOGIN_HOST`. Check the user name is exactly what you type on the sign-in page (it may not be your e-mail). |
| Same, and you sign in with an SSO button | SSO users have no IDMC password. | Ask your IDMC admin for a native IDMC user with a password. |
| `account is LOCKED` (`IDS_086`) | Too many wrong logins. | Don't try again. Ask an IDMC admin to unlock you (Administrator > Users > your user > Unlock), or use "Forgot your password?" on the sign-in page. |
| `Logins are paused` (`login BLOCKED`) | The plugin paused itself after a rejected login, to protect your account. | Sign in in the browser to prove the password works. Fix the file: changing the password or user lifts the pause by itself. |
| `could not reach IDMC` | Internet, VPN or proxy problem. Not your password. | Check your connection or VPN, then try again. |
| `CERTIFICATE_VERIFY_FAILED` | A company network is inspecting secure traffic. | Ask IT for the company certificate file and set `SSL_CERT_FILE` to it. |
| The password must be changed, or it expired | IDMC wants a new password first. | Sign in once in the browser, set the new password, then put it in your file. |

Still stuck? In Claude Code, type `/idmc-mp:fix-error` and paste the message (never your password).

---

## What you can ask

Just talk to Claude. Some examples:

- "Why does this fail: `<paste the error>`"
- "Build a mapping from `<source>` to `<target>` and schedule it nightly"
- "Install a Secure Agent on my VM and tune it for 20 parallel jobs"
- "Find the duplicate records in `<table>` and clean them"
- "Promote project `<X>` from dev to prod"
- "How many IPUs did we use this month, and on what?"

### Slash commands

All commands start with `/idmc-mp:`.

| Command | What it does |
|---|---|
| `connect` | Connects to your org and proves which org it is |
| `health-check` | Looks at agents, connections and projects. Read-only: changes nothing |
| `new-pipeline <source> to <target>` | Builds, runs and proves a pipeline, step by step |
| `fix-error` | Explains an error and fixes the cause |
| `tune-agent` | Tunes a Secure Agent for your workload |
| `optimize` | Speeds up a slow pipeline |
| `promote` | Moves a project from one org to another |
| `add-dq` | Adds data-quality rules |
| `clean-data` | Cleans a large dataset with mappings |
| `catalog` | Scans a source into the data catalog |
| `ipu-report` | Shows what used your IPUs |
| `save-lesson` | Saves something you learned, on your computer |

### What it covers

| Area | Skill (loads on its own) | Commands |
|---|---|---|
| Rules, login, routing, errors | `idmc-mp` | `connect`, `health-check`, `fix-error`, `save-lesson` |
| Secure Agent, runtime, connections | `idmc-secure-agent` | `tune-agent` |
| Data Integration (CDI) | `idmc-cdi` | `new-pipeline`, `optimize` |
| Mass ingestion, CDC | `idmc-cdc` | |
| Application Integration (CAI) | `idmc-cai` | |
| Data quality, profiling, cleaning | `idmc-data-quality` | `add-dq`, `clean-data` |
| Data governance, catalog (CDGC) | `idmc-governance` | `catalog` |
| MDM | `idmc-mdm` | |
| CLAIRE, MCP servers | `idmc-claire-mcp` | |
| Deploy, promote, migrate | `idmc-deploy` | `promote` |
| IPU, metering, job caps | `idmc-ipu` | `ipu-report` |

Two rules hold throughout: Claude builds with the systems **you** name (examples in the knowledge base are not
recommendations), and it works through the known workarounds in your org before it ever says something is not
possible.

Informatica also publishes its own Claude plugin (`informatica-for-claude-platform`, for catalog search and data
questions). It installs alongside this one. The [ecosystem guide](knowledge/09-claire-mcp/07-ecosystem-plugins-registries-community-tools.md)
covers it, all 23 managed MCP servers, and the community tools worth knowing.

---

## Safety

- **Your password stays on your computer**, in `~/.idmc_toolkit/IDMC_LOGIN.txt`, readable only by you. The plugin only
  talks to Informatica's own servers. It sends nothing anywhere else.
- **Writes are dry runs first.** Anything that changes your org shows what it will do, and only runs after it has
  checked it is connected to the org you named (`--expect-org <org id>`).
- **Jobs cost IPUs.** Jobs Claude runs in your org use your subscription, like any job you run yourself.
- Found a security problem? See [SECURITY.md](SECURITY.md).

## Update or remove

- **Get updates automatically (recommended):** in Claude Code type `/plugin`, open **Marketplaces**, pick **idmc-mp**
  and turn on auto-update.
- **Update by hand:** `/plugin marketplace update idmc-mp`, then `/plugin update idmc-mp@idmc-mp`.
- **Remove:** `/plugin uninstall idmc-mp@idmc-mp`.

Updates never touch your login or your own lessons: they live in `~/.idmc_toolkit/`, outside the plugin.

## For advanced users

- **Several orgs:** keep one login file per org anywhere outside the plugin, and set `IDMC_CREDS_FILE` to the one you
  want. Its values win over the default file.
- **Run the login check yourself:** `python3 toolkit/check_login.py` from the plugin folder (`--setup`, `--where`,
  `--json`). Windows: `py` instead of `python3`.
- **Working from a git clone, building the demos, or sharing a copy:** see [toolkit/setup/SETUP.md](toolkit/setup/SETUP.md).
- **Start here in the knowledge base:** the [Quick Start](knowledge/00-start-here/10-quick-start-your-first-hour-with-idmc-and-claude.md).

### How the repo is organized

```
.claude-plugin/   marketplace.json (one plugin) and plugin.json
skills/           idmc-mp (core: rules, login, routing) + one skill per IDMC area
commands/         the twelve /idmc-mp:<name> slash commands
knowledge/        the knowledge base: 00-start-here ... 14-claude-working-methods, playbook/, reference library
lessons/          lessons.jsonl (the source of truth), by-domain/ (readable), overturned-beliefs.md
toolkit/          lib/ (Python library), mapgen/ (mapping generator), demos/, setup/, tools/, check_login.py
tests/            run_tests.py (offline tests, run in CI) and USER_STORIES.md
.github/          CI workflows, issue forms and the pull-request checklist
```

Lessons are the evidence behind everything: each has an id (`L-<AREA>-###`), the evidence that proved it, and a status
(current, superseded or disputed). The [lessons README](lessons/README.md) explains the format.

## Getting help

- A login or setup problem: the [troubleshooting table](#if-the-login-doesnt-work) above.
- An IDMC error: `/idmc-mp:fix-error` in Claude Code.
- A bug in the plugin: open an [issue](https://github.com/michelepalestro-cmd/idmc-mp/issues/new/choose).
- A security problem: see [SECURITY.md](SECURITY.md) (please don't open a public issue).
- Anything else: e-mail the maintainer at michelepalestro@gmail.com.

## Contributing

`/idmc-mp:save-lesson` keeps new lessons on your computer. To share one with everyone, open an issue or a pull request
with the lesson in generic form: no org ids, hosts, people, customer names or secrets. The "Share a lesson" issue form
makes it easy. See [CONTRIBUTING.md](CONTRIBUTING.md) and the [Code of Conduct](CODE_OF_CONDUCT.md).

## Notes

- Informatica's product documentation is not included; the skills point to https://docs.informatica.com.
- Demo blueprints in `toolkit/demos/` may need Docker and the accounts their README lists.
- This is an independent community project, not an official Informatica product, and is not supported by
  Informatica. See [NOTICE](NOTICE).

## License

[MIT](LICENSE)
