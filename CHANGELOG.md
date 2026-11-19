# Changelog

Releases of the `idmc-mp` plugin. The knowledge base's own history is in
[knowledge/00-start-here/06-changelog.md](knowledge/00-start-here/06-changelog.md).

## 1.5.0 (2026-11-19): 186 lessons from public IDMC code

- **186 new lessons** (2,234 in total) mined from about 40 public IDMC repositories and the vendor's own Claude skill,
  each labelled Reported or Documented with a confidence note; nothing was run against an org.
- **New:** [Community code index](knowledge/12-reference-library/community-code-index.md): which public file each
  lesson came from. The ecosystem doc lists the newly found repositories, what to avoid, and the patterns worth copying.
- Two lessons that public code contradicts now point to the reported alternative (L-AGENT-088, L-MIG-097).

## 1.4.0 (2026-11-19): all 23 managed MCP servers, and the ecosystem

- **Managed MCP servers updated to the October 2026 release:** 23 servers (four were missing: Data Marketplace Order
  Management, Catalog Asset History, Data Access Management, IDMC Asset Documentation), the vendor's public registry
  (readable with no login), the October tool additions and platform changes.
- **New doc:** [Ecosystem: plugins, registries, community tools](knowledge/09-claire-mcp/07-ecosystem-plugins-registries-community-tools.md):
  the vendor's own Claude plugin and how to use it alongside this one, where the servers are listed, the
  catalog-discovery and data-exploration tool contract, and a reviewed list of community tools with verdicts.
- **Six lessons:** L-MCP-132 to L-MCP-137. The `idmc-claire-mcp` skill points to the new doc.

## 1.3.0 (2026-11-18): clean data with mappings

- **New playbook:** [cleaning a large dataset with IDMC mappings](knowledge/06-data-quality-profiling/05-cleaning-a-large-dataset-with-mappings.md):
  when mappings and when SQL, the duplicate-record match as ten native steps, the SQL-twin proof, safe runs, and field
  results from two regions (every shared record agreed, every survivor the same).
- **New command** `/idmc-mp:clean-data` (twelve in all); the `idmc-data-quality` skill points to both.
- **Three lessons:** L-DQ-165 (the match-mapping pattern), L-DQ-166 (the Cleanse dictionary is where IDMC beats a plain
  key), L-DQ-167 (re-count every region after a merge rule improves).

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
