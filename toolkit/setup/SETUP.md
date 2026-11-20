# Setup for advanced users: git clones, demos and sharing

Most people only need the 3 steps in the [README](../../knowledge/00-start-here/11-setup-and-login.md#setup-in-3-steps-about-10-minutes): install the
plugin, run `/idmc-mp:connect`, done. This page is for when you work from a **git clone**, build a **demo blueprint**,
or want to **share** your copy.

Paths below are relative to the plugin folder (the repository root). Windows: use `py` where it says `python3`.

## 1. What you need

| Need | Why |
|---|---|
| Python 3.10+ | the toolkit uses only the standard library (a demo's `requirements.txt` may add more) |
| Claude Code | the skills and slash commands |
| A native IDMC user (with its own password, not SSO-only) | every login and every build runs as this user, in your org |
| Docker + Docker Compose | only for the stand-in systems under `toolkit/demos/*/infra/` |
| The accounts a demo names under "Credentials needed" in its README | for example a warehouse, Salesforce, SharePoint, Tableau |

## 2. Clone and protect the repository

```
git clone https://github.com/michelepalestro-cmd/idmc-mp.git
cd idmc-mp
git config core.hooksPath toolkit/tools/git-hooks
```

The last line turns on a pre-commit check (`toolkit/tools/secret_scan.py`) that blocks a commit holding a password, a
key, an IP address, an e-mail or a local path.

## 3. Your IDMC login (one file, outside the repository)

```
python3 toolkit/check_login.py --setup
```

It asks for the IDMC address from your browser, your user name and your password (hidden while you type), saves them
to `~/.idmc_toolkit/IDMC_LOGIN.txt` (readable only by you) and logs in once. Prefer a text editor? Run
`python3 toolkit/check_login.py` once to create the file, then fill in its three lines.

- **Several orgs:** keep one file per org outside the repository (same three lines) and point `IDMC_CREDS_FILE` at the
  one you want. Its values win over the default file. Environment variables `IDMC_USER`, `IDMC_PASS` and
  `IDMC_LOGIN_HOST` win over both.
- **Where is my login file?** `python3 toolkit/check_login.py --where`
- An older layout kept `IDMC_LOGIN.txt` at the repository root. That still works, but keep the home file instead: then
  nothing secret ever sits in the working tree.

The login check prints your **org id** (22 characters). Write it down: every command that changes your org takes
`--execute --expect-org <org id>` and refuses to run in any other org.

## 4. If a login is rejected

Stop. A few rejected logins lock the account (`IDS_086`), and every new try can restart the lock. The toolkit writes a
block file under `~/.idmc_session/` after a rejection, so no script logs in again with the same values.

1. Sign in in the browser with the same user and password to prove they work.
2. Fix the login file. A changed user or password lifts the block by itself.
3. Only if the values were already right, delete the block file the message names, and try once.

The README's [troubleshooting table](../../knowledge/00-start-here/11-setup-and-login.md#if-the-login-doesnt-work) explains each message.

## 5. Demo blueprints (optional)

Demos may need accounts besides IDMC. Keep those in a separate file outside the repository:

```
mkdir -p ~/.idmc_toolkit
cp toolkit/setup/.env.example ~/.idmc_toolkit/.env
chmod 600 ~/.idmc_toolkit/.env
export IDMC_CREDS_FILE=~/.idmc_toolkit/.env
```

Windows (PowerShell): `copy toolkit\setup\.env.example $HOME\.idmc_toolkit\.env`, then
`setx IDMC_CREDS_FILE "$HOME\.idmc_toolkit\.env"`.

Fill in only the section of the demo you build, then check the computer (offline, prints no secret values):

```
python3 toolkit/setup/check_setup.py --demo <demo folder name>
```

It must end with `READY`. Then open Claude Code in the repository and say, for example, "rebuild the
`<demo>` blueprint in my org", or follow `toolkit/demos/<demo>/BUILD.md` step by step. Every step is a dry run until
you add `--execute`.

## 6. Before you share or commit

```
python3 toolkit/tools/secret_scan.py
python3 toolkit/tests/run_tests.py
```

The scan must print `CLEAN` and the tests `ALL PASSED`. A demo's filled-in `config.json` and `state/` files hold your
org's ids: don't share them. Add your own org ids, hosts and names (one regex per line) to
`toolkit/tools/secret_scan_extra.txt` so the scan catches them too.
