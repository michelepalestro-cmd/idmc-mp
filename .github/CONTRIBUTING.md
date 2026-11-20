# Contributing to IDMC MP

Thank you for helping. The quickest way to contribute is to **share a lesson**: something IDMC did, with the evidence.
Open an issue with the "Share a lesson" form, or a pull request if you are comfortable with git. Please read
[SECURITY.md](SECURITY.md) and the [Code of Conduct](CODE_OF_CONDUCT.md) first.

## The one rule: keep it generic

Nothing that identifies a real org, system or person goes into this repository: no org ids, hosts, pod-specific
addresses, IP addresses, cloud project or bucket names, customer, company or application names, people's names,
e-mails, tracker keys, and never a password, token, key or session id. Use placeholders such as `<pod>`, `<domain>`,
`<orgIdV3>`, `<connId>`, `<agent_home>`. Keep numbers, drop names ("a 62-task taskflow took 21 minutes" is fine).

## Where things go

This repo is one Claude Code plugin, `idmc-mp`. Keep it that way: `.claude-plugin/marketplace.json` lists exactly one
plugin, whose source is the repo root.

| You are adding... | Put it in | Rule |
|---|---|---|
| A lesson (something IDMC did, with evidence) | `knowledge/lessons/lessons.jsonl` (one JSON line, the source of truth) and the job folder's `knowledge/<job>/lessons*.md` | generic; see "A lesson" below |
| An explanation, a procedure, a pattern | the job folder in `knowledge/` (`01-login-and-orgs` ... `14-working-with-claude`), or `knowledge/reference/` for lookup material | cite the lesson ids it rests on |
| A compact rule Claude must always apply | `knowledge/00-start-here/` or the core skill `skills/idmc-mp/SKILL.md` | short; link to the long doc |
| A workflow for one IDMC area | that area's `skills/idmc-*/SKILL.md` | "How to work", "Read", "Tools" sections |
| A slash command | `commands/<name>.md` | names the skill(s) to use; paths start with `${CLAUDE_PLUGIN_ROOT}/` |
| Python | `toolkit/lib/` (library), `toolkit/mapgen/` (generator), `toolkit/demos/<name>/` (a blueprint), `toolkit/tools/` (repo tools) | standard library only; `--help` must work without a login; writes are dry runs until `--execute --expect-org <orgIdV3>` |
| A test or user story | `toolkit/tests/run_tests.py`, `toolkit/tests/USER_STORIES.md` | offline: no login, no network |

The reference library (`knowledge/reference/`) also holds the build scripts that regenerate its reference
files; some need extra packages, which their READMEs list. They are not part of the plugin's runtime.

**Names.** New folders and Markdown docs: lowercase with hyphens (for example 06-cleaning-a-large-dataset.md). Python files:
snake_case. Uppercase is kept for conventional files (`README.md`, `BUILD.md`, `SETUP.md`, `CHANGELOG.md`). No spaces or
special characters in any new file name, so every path works unquoted in any shell. Paths in docs written as inline
code (`knowledge/...`, `knowledge/lessons/...`, `toolkit/...`) are relative to the plugin root.

## A lesson

One line in `knowledge/lessons/lessons.jsonl` with exactly these fields, and the same lesson as a block in its job folder's `knowledge/<job>/lessons*.md`:

```json
{"id": "L-CDI-331", "domain": "cdi", "kind": "ERROR", "title": "...", "text": "...", "evidence": "...", "date": "2026-11-19", "status": "current", "supersedes_id": ""}
```

- `id`: `L-<PREFIX>-<next free number>` (the prefixes are listed in [knowledge/lessons/README.md](../knowledge/lessons/README.md) §5), never
  reused.
- `domain`: one of `auth`, `agent`, `connections`, `cdi`, `dbmi-cdc`, `cai`, `dq-profiling`, `cdgc`, `mdm`,
  `claire-mcp`, `migration`, `org-cleanup`, `ipu-licensing`, `environment-ops`, `claude-method`, `ui-automation`.
- `evidence`: what proved it and when (an HTTP code, a read-back, a count, a measured time). Keep the evidence state
  honest: **proven** (a live call), **documented** (vendor docs), **reported** (someone else's code or notes),
  **rejected** (refused, with the code) or **untested**. Never upgrade a state you did not test.
- `status`: `current`. When a new lesson overturns an old one, give it the kind `OVERTURNED`, set the old one to
  `superseded`, put its id in the new lesson's `supersedes_id` (several: `L-A-001, L-A-002`), move the old block to the
  file's `## Superseded / overturned` section and add a row to `knowledge/lessons/overturned-beliefs.md`.

Then regenerate what depends on the lessons:

```
python3 toolkit/tools/sync_lesson_counts.py
python3 toolkit/tools/build_skill_field_lessons.py
```

## Before you open a pull request

```
python3 toolkit/tests/run_tests.py
python3 toolkit/tools/secret_scan.py
```

The tests must print `ALL PASSED` and the scan `CLEAN`. CI also runs CodeQL, bandit and detect-secrets (see
[SECURITY.md](SECURITY.md)); if detect-secrets flags a value you have checked is not a secret, update the baseline
with `detect-secrets scan --baseline .github/secrets.baseline` and say so in the pull request. The tests check the manifests (one plugin), every skill and
command, every link and plugin path, the lessons file and its counts, that every Python file compiles and every library
script answers `--help`, and the offline half of every user story. CI runs the same on every push and pull request.

Install the secret-scan hook once per clone: `git config core.hooksPath toolkit/tools/git-hooks`. Commit with an e-mail
you are happy to publish, for example your GitHub no-reply address:
`git config user.email "<id>+<username>@users.noreply.github.com"`.

When a release changes what users get, bump `version` in both `.claude-plugin/plugin.json` and
`.claude-plugin/marketplace.json` (they must match) and the badge in `README.md`, and add an entry to `.github/CHANGELOG.md`:
installed copies only update when the version changes.
