# Changelog

Releases of the `idmc-mp` plugin. The knowledge base's own history is in
[knowledge/00-start-here/06-changelog.md](knowledge/00-start-here/06-changelog.md).

## 1.2.0 (2026-11-18): the IDMC co-pilot layout

- **One skill per IDMC area**, next to the core `idmc-mp` skill: `idmc-secure-agent`, `idmc-cdi`, `idmc-cdc`,
  `idmc-cai`, `idmc-data-quality`, `idmc-governance`, `idmc-mdm`, `idmc-claire-mcp`, `idmc-deploy`, `idmc-ipu`. Each
  has the ground rules, a work order, the docs to read and the tools to use.
- **Six new commands:** `tune-agent`, `optimize`, `promote`, `add-dq`, `catalog`, `ipu-report` (eleven in all).
- **New layout:** `knowledge/` (topic folders and the playbook), `lessons/` (lessons.jsonl, by-domain, overturned
  beliefs, case studies) and `toolkit/` (library, mapping generator, demos, setup, tools) at the plugin root, with
  lowercase hyphenated names. Every link (2,091) and every code path was moved with them.
- **Lessons cleaned:** 29 lessons with a stray domain spelling (`conn`, `ui`, `dq`, `env`, `data-quality`) moved to the
  standard domain; `supersedes_id` lists use one separator.
- **Tests:** `tests/run_tests.py` (structure, links, lessons, code, secret scan, and the offline half of every user
  story) runs in CI; `tests/USER_STORIES.md` holds each story with its live checklist.
- `python3` on macOS and Linux everywhere; `check_setup.py` now reports the real login file.

## 1.1.3 (2026-11-17)

- Quick start, slash commands, latest lessons.
