# Changelog

Releases of the `idmc-mp` plugin. The knowledge base's own history is in
[knowledge/reference/kb-changelog.md](../knowledge/reference/kb-changelog.md).

## 1.15.1 (2026-11-20): full documentation audit

Every document (about 170) was checked against the newest lessons and the code; stale claims were fixed and newer
lessons added where they belong.

- **Data quality:** per-rule pass rates are readable over REST (the stale "console only" claim is gone from four
  places); new profiling, validation and verification lessons.
- **Catalog and lineage:** lineage is readable over REST hop by hop; the newer catalog lessons (bulk read, history,
  export, custom lineage, paging past 10,000) are in the guides, marked where they come from public code.
- **MDM:** search filters, incremental extract, survivorship before loading, and the new mastering lessons cited in
  the playbook.
- **MCP:** 23 servers everywhere the count is current; `/idmc-mp:connect-mcp` and the bridge in the auth, wiring and
  how-Claude-reaches-IDMC guides; the vendor plugin's search traps.
- **Secure Agent, connections, CDC, CAI:** the agent tuning form now goes in `configFormJson`; engine start and stop
  routes; replace-style connection updates and `Update-Mode: PARTIAL`; CDC job and metrics routes; CAI taskflow run
  control and publish rules.
- **Mappings, taskflows, deploy, IPU:** PostgreSQL truncate settled (L-CDI-331 supersedes L-CDI-194); four broken
  code snippets fixed; metering windows, limits and states; schedule PATCH; export limits and package hygiene.
- **Login and orgs:** the newer auth lessons, timestamps read as UTC-4 (not pod-local), and the org guard's two id forms.
- **Skills, commands and toolkit docs** match the code (flags, subcommands, defaults); each area skill names its MCP
  tool prefixes. The endpoint dictionary's builder carries the newer evidence, so rebuilds keep it.
- **Code:** `idmc_cai_publish.py` publishes Data Integration taskflows on the pod host in their own wave and leaves
  process objects out (L-CAI-164, L-CAI-165, reported); `idmc_mcp.py` finds the client file written by
  `/idmc-mp:connect-mcp` without `--env`.
- **Lessons:** five supersede links corrected, L-CDI-194 superseded, and text refinements to L-AUTH-125, L-CONN-145,
  L-IPU-035, L-DQ-100 and L-MCP-148.

## 1.15.0 (2026-11-20): Informatica's MCP servers as Claude's own tools

- **`/idmc-mp:connect-mcp`:** lists the org's managed MCP servers, creates a scoped OAuth client (secret straight to a
  0600 file in `~/.idmc_toolkit/`), and tests it. After a restart every server's tools are Claude Code tools.
- **The plugin's MCP bridge** (`toolkit/lib/idmc_mcp_bridge.py`, started by the plugin): read-only by default (tools
  that change the org appear only when the client allows writes, marked "WRITES to IDMC"), tokens renew by themselves,
  https only, the secret is never printed. With no client file it offers one status tool and makes no network call.
- **MCP and REST together:** the core skill now says which to use per task; the README and the MCP cheat sheet match.
- Tested offline against a stand-in Informatica server (four new tests), and in a real Claude Code install that
  called the bridge's tools.

## 1.14.2 (2026-11-20): MCP servers in the README

- The README now covers Informatica's 23 managed MCP servers: how to connect, when to use MCP or the REST API, and which
  servers were called live (6), connected with tools listed (13) or only documented (4).
- The MCP skill tells Claude to say which servers are untested and to prove one with a read-only call first.

## 1.14.1 (2026-11-20): golden-record and DQ lessons from a production mastering build

- **16 new lessons** (2,358 in total), mostly mastering: measure precision per match class before auto-merging
  (L-MDM-121), the source id is the identity inside one source (L-MDM-122), survivorship when the loser is newer
  (L-MDM-125), cluster merges (L-MDM-126), daily merge checks (L-MDM-127), safe re-keying (L-MDM-128), blocking size
  (L-MDM-124), change events (L-MDM-129); CLAIRE rules as governed warehouse rows and sample-bias fixes (L-DQ-173 to
  L-DQ-176); sort-key forks in a replacing golden table (L-ENV-145).
- L-MDM-075 and L-DQ-166 refined: exact id bytes and exact names are safe merge keys, fuzzy name similarity is not.
- The MDM and data-quality cheat sheets list the new traps.

## 1.14.0 (2026-11-20): fixes from six user-story walkthroughs

Six beginner journeys were walked end to end (install and log in, Secure Agent, connections, a nightly pipeline,
production, data quality and MDM). Each scored OK; these changes fix what they tripped on.

- **Run it in production:** new [runbook](../knowledge/00-start-here/12-run-it-in-production.md) (failed-job alerts, a
  daily check, "a job failed at 2am", agent upgrades, schedule owners, secrets rotation, backups), linked from the
  router and the playbook. `/idmc-mp:health-check` now reads the last 24 hours of runs.
- **Safer promotion:** the export/import tool checks each connection and runtime in the target by name during the dry
  run, and exits non-zero unless an import ends SUCCESSFUL (a timeout prints the status command, never a second import).
  `/idmc-mp:promote` guards the dry run with `--expect-org` and compares connection hosts after import.
- **IPU:** new read-only `toolkit/lib/idmc_metering.py` for the metering export.
- **Login:** clearer paused and locked messages, a path for trial users who are the only admin, and when to delete the
  pause file after an unlock.
- **Secure Agent:** `idmc_session.py get --save-to` stores the install token in a private file instead of printing it;
  fuller install steps (checksum, install folder, expired token, Ubuntu 24.04, Windows); heap tuning starts with the UI.
- **Connections:** Salesforce and flat-file bodies, the Snowflake role and `instanceName` rules made consistent, more
  error rows, and the working create/test script listed in the skill.
- **Pipelines:** PostgreSQL type names and truncate corrected (L-CDI-331), rows for 0-row successes and "value too
  long", schedule time-zone drift explained, and mapgen warns when IDMC reports an imported mapping as not valid.
- **Data quality and MDM:** a licence check with the no-licence customer CSV path, per-rule pass rates readable from
  the metric store (L-DQ-031 superseded), and the customer CSV check writes to a temp folder by default.
- New lessons: L-CDI-331, L-MIG-132 (2,342 in total).

## 1.13.0 (2026-11-20): one clear path for Claude

- **The core skill now sends Claude, in order:** the job's cheat sheet, the lessons (error codes via
  `knowledge/lessons/error-index.md`), the org check, and a long guide only when the cheat sheet points there. Its
  connect section follows the safe login flow (never handle a password in chat).
- **One source of truth:** the frozen July playbook snapshot is gone (its links point to the current cheat sheets and
  guides); its generated error index moved to `knowledge/lessons/error-index.md`; the KB's long history moved to
  `knowledge/reference/kb-changelog.md`.
- `knowledge/README.md` cut from 341 to 120 lines (map, asset table, conventions, scope); the blueprints get their own
  `toolkit/demos/README.md`; every guide opens with its "Answers / Read when" summary.
- Skill descriptions also match plain-language requests ("clean my data", "data lineage", "single customer view",
  "ETL pipeline", "what are we spending").

## 1.12.0 (2026-11-20): a tidy root and an overview README

- **Root reduced to what must be there:** `commands/`, `skills/` (Claude Code's plugin format), `knowledge/`,
  `toolkit/`, `README.md`, `CHANGELOG.md`, `LICENSE`. The lessons file moved to `knowledge/lessons/`, the tests to
  `toolkit/tests/`, CONTRIBUTING, SECURITY and CODE_OF_CONDUCT to `.github/`, CLAUDE.md to `.claude/`; NOTICE folded
  into the README. Every link and path was rewritten and tested.
- **README is now an overview** (purpose, skills, commands, layout); setup and login troubleshooting moved to
  [Setup and login](../knowledge/00-start-here/11-setup-and-login.md).
- CI actions updated to checkout v7.0.1 and setup-python v7.1.0 (pinned SHAs, verified against the release tags).

## 1.11.0 (2026-11-19): passes enterprise security scanners

- **Clean under bandit, Semgrep (python, security-audit, secrets, github-actions), detect-secrets, ShellCheck and
  actionlint**, and the full git history scanned for secrets (863 file versions: none).
- **Fixes:** XML parsing refuses DTDs and entities; URL opens allow https only (http only to localhost); explicit
  verified TLS context; uuid4; MD5 only where Salesforce requires it, marked not for security; GUIDs from `secrets`;
  three demo SQL builders that lacked escaping now escape or validate; a CDC template renamed `.json.tmpl`; the customer
  CSV check calls the generator in-process.
- **New CI:** CodeQL (security-extended, weekly too) and a security-scan workflow (bandit, detect-secrets against an
  audited `.secrets.baseline`, the repository secret scan), read-only and SHA-pinned.

## 1.10.0 (2026-11-19): user story: a messy customer CSV, mastered by IDMC

- **New blueprint `toolkit/demos/customer_master_csv/`:** a messy customer CSV is standardized, de-duplicated and given
  stable `CUST-######` ids by one IDMC mapping on a Secure Agent, built from native transformations only (no DQ or MDM
  licence): name + ZIP blocks, a new customer only when a known e-mail or phone conflicts, the most complete and most
  recent record as survivor, and a source-to-customer cross-reference.
- **Proven offline in under a second** (`check.py`): sample with an answer key, lint and build of the real IDMC
  package, a Python twin of the same rules, checks and a match score (precision 1.00; recall 1.00 on the default
  sample; 0.996 precision and 0.983 recall on 2,000 people). `check.py --compare` diffs a live run against the twin.
- **Timed live run** in `BUILD.md` (agent, flat-file connection, deploy, run, compare) with targets from the lessons and
  a timing log; new test US-20 and a router entry.

## 1.9.0 (2026-11-19): one folder per job, with a cheat sheet for each

- **New layout:** `knowledge/01-login-and-orgs` ... `14-working-with-claude`, in the order you build. Each job folder
  holds a one-page `README.md` cheat sheet, its guides and its `lessons.md`. Secure Agent and connections, and mappings
  and taskflows, now have their own folders. Reference material and the compact playbook are in `knowledge/reference/`.
  `knowledge/lessons/lessons.jsonl` still holds every lesson in one searchable file.
- **14 cheat sheets:** what works (exact routes, tools, commands), what doesn't and the workaround, the fastest safe
  path with the read-back for each step, and the top traps, every row citing its lesson. Lessons that came from other
  people's code and are not yet proven live are marked **(reported)**.
- **Router:** `knowledge/00-start-here/README.md` maps "I want to..." to the command, cheat sheet and tool.
- **New skill `idmc-connections`** for connections to any system; `idmc-secure-agent` now covers the agent and its
  runtime environment. Every skill opens its cheat sheet first.
- **Project-neutral lessons:** methods kept, dataset sizes, geography and source details replaced by orders of
  magnitude.
- The mapping Fast Path shows `--execute --expect-org` on every write; the secret scan checks what git would commit
  (`--all` for a whole folder).

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
- **New** [SECURITY.md](../.github/SECURITY.md); `toolkit/setup/SETUP.md` rewritten for git clones, demos and sharing; a test
  (US-02b) proves example or empty values never reach IDMC.

## 1.5.0 (2026-11-19): 186 lessons from public IDMC code

- **186 new lessons** (2,234 in total) mined from about 40 public IDMC repositories and the vendor's own Claude skill,
  each labelled Reported or Documented with a confidence note; nothing was run against an org.
- **New:** [Community code index](../knowledge/reference/community-code-index.md): which public file each
  lesson came from. The ecosystem doc lists the newly found repositories, what to avoid, and the patterns worth copying.
- Two lessons that public code contradicts now point to the reported alternative (L-AGENT-088, L-MIG-097).

## 1.4.0 (2026-11-19): all 23 managed MCP servers, and the ecosystem

- **Managed MCP servers updated to the October 2026 release:** 23 servers (four were missing: Data Marketplace Order
  Management, Catalog Asset History, Data Access Management, IDMC Asset Documentation), the vendor's public registry
  (readable with no login), the October tool additions and platform changes.
- **New doc:** [Ecosystem: plugins, registries, community tools](../knowledge/11-mcp-claire/07-ecosystem-plugins-registries-community-tools.md):
  the vendor's own Claude plugin and how to use it alongside this one, where the servers are listed, the
  catalog-discovery and data-exploration tool contract, and a reviewed list of community tools with verdicts.
- **Six lessons:** L-MCP-132 to L-MCP-137. The `idmc-claire-mcp` skill points to the new doc.

## 1.3.0 (2026-11-18): clean data with mappings

- **New playbook:** [cleaning a large dataset with IDMC mappings](../knowledge/08-data-quality/05-cleaning-a-large-dataset-with-mappings.md):
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
- **New layout:** `knowledge/` (topic folders and the playbook), `knowledge/lessons/` (lessons.jsonl, by-domain, overturned
  beliefs, case studies) and `toolkit/` (library, mapping generator, demos, setup, tools) at the plugin root, with
  lowercase hyphenated names. Every link (2,091) and every code path was moved with them.
- **Lessons cleaned:** 29 lessons with a stray domain spelling (`conn`, `ui`, `dq`, `env`, `data-quality`) moved to the
  standard domain; `supersedes_id` lists use one separator.
- **Tests:** `toolkit/tests/run_tests.py` (structure, links, lessons, code, secret scan, and the offline half of every user
  story) runs in CI; `toolkit/tests/USER_STORIES.md` holds each story with its live checklist.
- `python3` on macOS and Linux everywhere; `check_setup.py` now reports the real login file.

## 1.1.3 (2026-11-17)

- Quick start, slash commands, latest lessons.
