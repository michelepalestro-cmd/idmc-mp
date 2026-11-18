# Contributing to IDMC MP

This repo is one Claude Code plugin, `idmc-mp`. Keep it that way: `.claude-plugin/marketplace.json` lists exactly one
plugin, whose source is the repo root.

## Where things go

| You are adding... | Put it in | Rule |
|---|---|---|
| A lesson (something IDMC did, with evidence) | `lessons/lessons.jsonl` (one JSON line) and the matching `lessons/by-domain/NN-*.md` | generic: no org ids, hosts, people, customer names or secrets |
| An explanation, a procedure, a pattern | the topic folder in `knowledge/` (`00-start-here` ... `14-claude-working-methods`) | cite the lesson ids it rests on |
| A compact rule Claude must always apply | `knowledge/playbook/` or the core skill `skills/idmc-mp/SKILL.md` | short; link to the long doc |
| A workflow for one IDMC area | that area's `skills/idmc-*/SKILL.md` | "How to work", "Read", "Tools" sections |
| A slash command | `commands/<name>.md` | names the skill(s) to use; paths start with `${CLAUDE_PLUGIN_ROOT}/` |
| Python | `toolkit/lib/` (library), `toolkit/mapgen/` (generator), `toolkit/demos/<name>/` (a blueprint) | standard library only; `--help` must work without a login |
| A test or user story | `tests/run_tests.py`, `tests/USER_STORIES.md` | offline: no login, no network |

Names are lowercase with hyphens (no spaces or symbols), so every path works unquoted in any shell. Paths written in
docs as inline code (`knowledge/...`, `lessons/...`, `toolkit/...`) are relative to the plugin root.

## A lesson's shape

One line in `lessons/lessons.jsonl` with exactly these fields:

```json
{"id": "L-CDI-307", "domain": "cdi", "kind": "ERROR", "title": "...", "text": "...", "evidence": "...", "date": "2026-11-18", "status": "current", "supersedes_id": ""}
```

- `id`: `L-<DOMAIN>-<next number>`, never reused.
- `domain`: one of `auth`, `agent`, `connections`, `cdi`, `dbmi-cdc`, `cai`, `dq-profiling`, `cdgc`, `mdm`,
  `claire-mcp`, `migration`, `org-cleanup`, `ipu-licensing`, `environment-ops`, `claude-method`, `ui-automation`.
- `status`: `current`; when a new lesson overturns an old one, set the old one to `superseded`, put its id in the new
  lesson's `supersedes_id` (several: `L-A-001, L-A-002`) and add a line to `lessons/overturned-beliefs.md`.
- Then rebuild the error-signature index: `python3 toolkit/tools/build_skill_field_lessons.py`.

## Before you open a pull request

```
python3 tests/run_tests.py
```

It must print `ALL PASSED`. It checks the manifests (one plugin), every skill and command, every link and plugin path,
the lessons file, that every Python file compiles and every library script answers `--help`, the secret scan, and the
offline half of every user story. CI runs the same on every push and pull request.

Install the secret-scan hook once per clone: `git config core.hooksPath toolkit/tools/git-hooks`.

When a release changes what users get, bump `version` in both `.claude-plugin/plugin.json` and
`.claude-plugin/marketplace.json` (they must match) and add a `CHANGELOG.md` entry: installed copies only update when
the version changes.
