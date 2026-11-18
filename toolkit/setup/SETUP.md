# Setting up the Master IDMC KB on a new PC

> **Plugin install:** your login lives in `~/.idmc_toolkit/IDMC_LOGIN.txt` (run `python3 toolkit/check_login.py` once
> to create it), not in this folder. Where the docs below say "IDMC_LOGIN.txt at the toolkit root", that home
> file is what is read (a root copy still works when you run from a git clone).

About 15 minutes, all offline except step 5. Nothing before step 5 logs in to IDMC.

## 1. What you need

| Need | Why |
|---|---|
| Python 3.10+ (Windows or Linux) | the core library and every blueprint script (standard library only, unless a blueprint's `requirements.txt` says otherwise) |
| Claude Code | the skill and `CLAUDE.md` make a Claude session productive in this folder from the first prompt |
| Docker + Docker Compose | only for the stand-in systems under `demos/*/infra/` (source databases, Kafka, mock targets) |
| An IDMC org you may write to, and its user / password | every blueprint builds into *your* org. A trial org works, but has a monthly job budget |
| The accounts a blueprint names in its README "Credentials needed" | e.g. a warehouse, Salesforce, SharePoint, Tableau |

## 2. Get the folder and fill in your IDMC login (one file)

```
git clone <repo-url> "Master IDMC KB"
cd "Master IDMC KB"
git config core.hooksPath toolkit/tools/git-hooks     # pre-commit runs toolkit/tools/secret_scan.py: a filled-in login, a key,
                                              # an IP, an email or a local path blocks the commit
git update-index --skip-worktree IDMC_LOGIN.txt   # git stops tracking your edits to the login file
```

A zip works too: unzip anywhere. Then open `IDMC_LOGIN.txt` at the top of the toolkit folder, fill in the three lines and save:

| Line | What to put |
|---|---|
| `IDMC_USER=` | the user name you sign in to IDMC with, in full. A native IDMC user (an SSO-only user cannot use the API) |
| `IDMC_PASS=` | its password |
| `IDMC_LOGIN_HOST=` | sign in to IDMC in a browser and paste the address bar, as is. The toolkit keeps the region part (`dm-us.informaticacloud.com`, `dm-em...`, `dm-ap...`) |

That is all IDMC needs: no org id (step 5 prints it), no environment variable. Every script finds the file by itself.
Linux: `chmod 600 IDMC_LOGIN.txt`. Never share, zip or commit the toolkit while this file is filled in. In a git clone the
safer habit is to leave `IDMC_LOGIN.txt` empty and keep the same three lines in a file outside the repository
(`IDMC_CREDS_FILE`, below): its values win, and nothing secret ever sits in the working tree.

**Only if you build a blueprint**, its other accounts (warehouse, Salesforce, SharePoint...) go in a separate file
outside the toolkit:

```
mkdir ~/.idmc_toolkit
cp "toolkit/setup/.env.example" ~/.idmc_toolkit/.env        # Windows: copy setup\.env.example %USERPROFILE%\.idmc_toolkit\.env
export IDMC_CREDS_FILE=~/.idmc_toolkit/.env           # PowerShell: setx IDMC_CREDS_FILE "$HOME\.idmc_toolkit\.env"
```

Fill in only that blueprint's section. Linux: `chmod 600 ~/.idmc_toolkit/.env`.

## 3. Install the Claude skill

Nothing to do: this KB already sits inside the `idmc-mp` skill. The skill folder belongs at
`~/.claude/skills/idmc-mp/` (Windows `%USERPROFILE%\.claude\skills\idmc-mp\`); see `../INSTALL.md`.

## 4. Check the PC (offline)

```
python toolkit/setup/check_setup.py                                   # IDMC_LOGIN.txt, library compiles, skill, docker
python toolkit/setup/check_setup.py --demo retail_data_foundation     # plus one blueprint's keys
```

It must end with `READY`. It never prints a credential value.

## 5. Prove the org (the first and only login)

```
python3 toolkit/check_login.py
```

This logs in once, caches the session and prints the org name and `orgIdV3`. Write that id down: every write in every
blueprint takes `--execute --expect-org <orgIdV3>`, and refuses to run in any other org.

If the login is rejected, **stop**. The library writes a block file so that no further attempt is made (a few rejected
logins lock the account, `IDS_086`). Confirm you can sign in in the browser with the same user and password, fix the
line in `IDMC_LOGIN.txt` (a changed user or password lifts the block by itself), and only if the values were already
right delete the block file it names.

## 6. Build a demo

Open Claude Code in the toolkit folder and say, for example, *"rebuild the retail data foundation blueprint in my org"*,
or follow `demos/<name>/BUILD.md` yourself step by step. Every step is a dry run until you add `--execute`.

## Before you share your copy again

```
python toolkit/tools/secret_scan.py      # must print CLEAN (empty IDMC_LOGIN.txt first)
```

Your filled-in `config.json` and `state/` files under each blueprint hold your org's ids: don't share them. Add your own
org ids, hosts and names (one regex per line) to `tools/secret_scan_extra.txt` so the scan catches them too.
