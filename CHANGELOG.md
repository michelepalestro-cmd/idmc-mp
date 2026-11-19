# Changelog

Releases of the `idmc-mp` plugin. The knowledge base's own history is in
[knowledge/00-start-here/06-changelog.md](knowledge/00-start-here/06-changelog.md).

## 1.8.0 (2026-11-19): security and tidiness pass

- **Security fixes from a full code review:** the mapping generator only sends credentials to an https
  `*.informaticacloud.com` login and ignores `auth` in specs; its writes are dry runs until `--execute --expect-org`;
  one lockout guard for every tool (HMAC-keyed block file); redirects never carry session headers to another host or to
  http; wider secret redaction; export packages written 0600; session calls refuse non-IDMC URLs; at most one re-login
  per call; tests can never reach the network.
- **Demos:** CAI processes require Basic Authentication; no Salesforce secret inside packages; Postgres bound to
  localhost; TLS on non-local connections; bound Snowflake parameters; no password on any command line.
- **Content:** the identifiable case study removed; safe wording for the legacy agent form, VM backups (managed
  identity, no secret over run-command), the Shell Service and curl logins; a vendor ticket key and a private roadmap
  note removed; `/idmc-mp:connect` never handles a pasted password.
- **CI:** least-privilege permissions, actions pinned to commit SHAs, no persisted token, Python 3.10 and 3.12,
  Dependabot. `.gitignore` covers demo `config.json` / `state/` and the mapping generator's `profile.json`.
- **Tidiness:** lesson counts are generated (`toolkit/tools/sync_lesson_counts.py`) and tested; stale docs rewritten;
  reference library trimmed (generated and history-only files removed, POSIX paths); new CODE_OF_CONDUCT, issue forms,
  pull-request checklist, `.editorconfig`, `toolkit/README.md`, `CLAUDE.md`; a maintainer contact; the secret scan
  covers `lessons.jsonl` and masks what it prints.

## 1.7.0 (2026-11-19): a second pass over public IDMC code

- **106 more lessons** (2,340 in total) from a second, file-by-file pass: every bug and change note of the best-maintained
  CLI, the vendor admin REST documentation bundled in one repository, Informatica's service-connector packages, the CAI
  quickstart bundle, MDM record and search API docs, and repositories the first pass had not read.
- Highlights: v3 logout and the org-wide `logoutall`, SCIM tokens, SAML mapping bodies, trusted IP and sub-org licence
  overwrites, fetchState/loadState, metering export caps and meter ids, job callbacks, taskflow status polling rules,
  code tasks, elastic runtimes, file listeners and MFT, service-connector authoring, and MDM record reads and writes.
- Unsafe material stays out: the shell-command service is not documented, and four more repositories with security
  problems are not linked (their plain API facts are kept). L-AUTH-108 points to a reported alternative (L-AUTH-129).

## 1.6.0 (2026-11-19): setup anyone can follow

- **README rewritten around a 3-step setup** in plain words: a checklist of what you need, install, connect, check,
  and a table that explains every login message and what to do about it.
- **Guided login:** `python3 toolkit/check_login.py --setup` asks for the IDMC address from your browser, your user
  name and your password (hidden while typing) and saves them to your private login file. `--where` shows the file.
- **No wasted login attempts:** the login check now looks at your file on your computer first (empty values, example
  values, an address that is not IDMC) and only then makes its single attempt. A failed login is explained in plain
  words: wrong region, single sign-on user, locked account, paused login, network or certificate problem.
- A short "CONNECTED" summary instead of raw JSON (`--json` for the full answer); `/idmc-mp:connect` asks users not to
  paste passwords into the chat.
- **New** [SECURITY.md](SECURITY.md); `toolkit/setup/SETUP.md` rewritten for git clones, demos and sharing; a test
  (US-02b) proves example or empty values never reach IDMC.

## 1.5.0 (2026-11-19): 186 lessons from public IDMC code

- **186 new lessons** (2,234 in total) mined from about 40 public IDMC repositories and the vendor's own Claude skill,
  each labelled Reported or Documented with a confidence note; nothing was run against an org.
- **New:** [Community code index](knowledge/reference/community-code-index.md): which public file each
  lesson came from. The ecosystem doc lists the newly found repositories, what to avoid, and the patterns worth copying.
- Two lessons that public code contradicts now point to the reported alternative (L-AGENT-088, L-MIG-097).

## 1.4.0 (2026-11-19): all 23 managed MCP servers, and the ecosystem

- **Managed MCP servers updated to the October 2026 release:** 23 servers (four were missing: Data Marketplace Order
  Management, Catalog Asset History, Data Access Management, IDMC Asset Documentation), the vendor's public registry
  (readable with no login), the October tool additions and platform changes.
- **New doc:** [Ecosystem: plugins, registries, community tools](knowledge/11-mcp-claire/07-ecosystem-plugins-registries-community-tools.md):
  the vendor's own Claude plugin and how to use it alongside this one, where the servers are listed, the
  catalog-discovery and data-exploration tool contract, and a reviewed list of community tools with verdicts.
- **Six lessons:** L-MCP-132 to L-MCP-137. The `idmc-claire-mcp` skill points to the new doc.

## 1.3.0 (2026-11-18): clean data with mappings

- **New playbook:** [cleaning a large dataset with IDMC mappings](knowledge/08-data-quality/05-cleaning-a-large-dataset-with-mappings.md):
  when mappings and when SQL, the duplicate-record match as ten native steps, the SQL-twin proof, safe runs, and field
  results from two test datasets (every shared record agreed, every survivor the same).
- **New command** `/idmc-mp:clean-data` (twelve in all); the `idmc-data-quality` skill points to both.
- **Three lessons:** L-DQ-165 (the match-mapping pattern), L-DQ-166 (the Cleanse dictionary is where IDMC beats a plain
  key), L-DQ-167 (re-count every scope after a merge rule improves).

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
