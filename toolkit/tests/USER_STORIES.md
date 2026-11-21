# User stories

What the plugin promises, one story per row, each with how it is tested. Each story has two halves:

- **Offline**: `python3 toolkit/tests/run_tests.py` checks it on every push (no login, no network). The test name starts
  with the story id.
- **Live**: the checklist below, run by a person in Claude Code against a real IDMC org. Use a dev or sandbox org.
  Read-only stories are safe anywhere; stories that write or run jobs ask before every write and consume IPUs.

Record each live run in the table at the bottom (date, org type, result, notes).

| Id | As a... | I want to... | So that... | Entry point |
|---|---|---|---|---|
| US-01 | new user | install the plugin from the repo in two commands | I get exactly one plugin, nothing else | `/plugin marketplace add`, `/plugin install informatica-idmc-headless@informatica-idmc-headless` |
| US-02 | new user | connect Claude to my IDMC org once | every later session knows my org, and my login stays outside the plugin | `/informatica-idmc-headless:connect` |
| US-03 | admin | a read-only health check of my org | I know what runs, what is unhealthy and why | `/informatica-idmc-headless:health-check` |
| US-04 | developer | paste an IDMC error and get the cause and fix | I stop losing hours to known errors | `/informatica-idmc-headless:fix-error <error>` |
| US-05 | developer | save what I learned as a lesson | Claude uses it next time, and I can share it | `/informatica-idmc-headless:save-lesson <lesson>` |
| US-06 | data engineer | a pipeline from my source to my target, built, run and proven | I get value in hours, not weeks | `/informatica-idmc-headless:new-pipeline <source> to <target>` |
| US-07 | platform admin | my Secure Agent reviewed and tuned | jobs stop failing or queueing on the agent | `/informatica-idmc-headless:tune-agent`, skill `idmc-secure-agent` |
| US-08 | data engineer | a slow or costly pipeline made faster or cheaper | I meet the latency and stay within the job cap and IPUs | `/informatica-idmc-headless:optimize <pipeline>` |
| US-09 | data engineer | CDC from my database into my target | changes land continuously without hand-built jobs | skill `idmc-cdc` |
| US-10 | integration developer | a CAI process published and called | events and APIs trigger real work | skill `idmc-cai` |
| US-11 | data steward | a table profiled and DQ rules added to the pipeline with scores | bad data is caught and measured | `/informatica-idmc-headless:add-dq <table>` |
| US-12 | data governance lead | my sources scanned into the catalog with glossary and lineage | people can find and trust the data | `/informatica-idmc-headless:catalog <source>` |
| US-13 | MDM lead | a table mastered into golden records | one trusted record per entity | skill `idmc-mdm` |
| US-14 | release manager | assets promoted from dev to prod with a rollback plan | releases are repeatable and safe | `/informatica-idmc-headless:promote` |
| US-15 | budget owner | an IPU and job usage report with the biggest savings | I control spend | `/informatica-idmc-headless:ipu-report` |
| US-16 | architect | Claude connected to our managed MCP servers, and told when to use MCP vs REST | we use CLAIRE and MCP where they fit | `/informatica-idmc-headless:connect-mcp`, skill `idmc-claire-mcp` |
| US-17 | presales / learner | a demo blueprint rebuilt end to end | I can show the pattern on real systems | `toolkit/demos/*/BUILD.md` |
| US-18 | any user | updates that never touch my login or my lessons | updating is always safe | `/plugin update informatica-idmc-headless@informatica-idmc-headless` |
| US-19 | data steward | duplicates and bad values in a large table cleaned with IDMC mappings, proven before anything changes | the data gets cleaner without slowing every rebuild | `/informatica-idmc-headless:clean-data` |
| US-20 | new user | a messy customer CSV cleaned, de-duplicated and given customer ids by IDMC on my own Secure Agent, timed from zero | I see real value in under an hour without a DQ or MDM licence | `toolkit/demos/customer_master_csv/` (`check.py`, `BUILD.md`) |

## Live checklists

Run in a new Claude Code session after installing the plugin. "Pass" means every line holds.

**US-01 install**
- `/plugin` shows one marketplace `informatica-idmc-headless` with one plugin `informatica-idmc-headless`, and its version matches `plugin.json`.
- Typing `/informatica-idmc-headless:` lists the thirteen commands; asking "what IDMC skills do you have?" names the twelve skills.
- `/mcp` lists the plugin's `idmc` server (the MCP bridge); before `/informatica-idmc-headless:connect-mcp` it offers only `idmc_mcp_status`.

**US-02 connect**
- First `/informatica-idmc-headless:connect` creates `~/.idmc_toolkit/IDMC_LOGIN.txt` and stops without a login attempt.
- After you fill it in, the second run prints org name, org id, pod and base URL, with one login.
- A wrong password is NOT retried; Claude names the likely cause (login host first).

**US-03 health-check**
- One table of runtimes and agents with status and engines; connections by type; projects; what the org can run.
- No writes, no job runs (check the activity log). Every unhealthy item cites a lesson id.

**US-04 fix-error**
- Paste a known error (for example a `403 APP_10519` on connection create): Claude cites the lesson id before
  touching the org, and gives cause, fix and how to verify.
- Paste an unknown error: Claude runs the error-triage checks read-only and offers `/informatica-idmc-headless:save-lesson`.

**US-05 save-lesson**
- A new line appears in `~/.idmc_toolkit/lessons-local.jsonl` with all nine fields and no org id, host or name.
- Nothing changed inside the plugin folder.

**US-06 new pipeline**
- Claude uses the source and target you named (never suggests another), proves the org, dry-runs, and asks before the
  first run.
- Ends with ids of the mapping and task, the run status and row counts on both sides.

**US-07 tune-agent**
- Read-only report per agent; each recommendation has a lesson id and a way to measure it; nothing changes without a yes.

**US-08 optimize**
- Measurements first (wall time per step, queueing, jobs per day), then fixes ranked by measured gain.

**US-09 CDC**
- Prerequisites checked on the source, task created and deployed headless, a change shown arriving in the target.

**US-10 CAI**
- Process published headless and invoked; the run's result shown.

**US-11 add-dq**
- Profile summary per column; proposed rules with reasons; after a yes, pass/fail counts per rule from a real run.

**US-12 catalog**
- Existing catalog sources checked first; scan asked for, run and polled; asset counts, glossary links and the lineage
  path shown with ids.

**US-13 MDM**
- Records ingested and matched; counts before and after merge; a golden record shown.

**US-14 promote**
- Both orgs proven; dependency closure listed; package edited for the target; dry run shown; import only after a yes;
  validation run with row counts; rollback kit named.

**US-15 ipu-report**
- IPU by service and project for the period (or a labelled proxy), jobs against the cap, top three savings.

**US-16 MCP**
- The org's MCP servers listed and one tool called; MCP vs REST advice cites the doc.
- `/informatica-idmc-headless:connect-mcp`: dry run shown before the OAuth client is created; the secret goes to
  `~/.idmc_toolkit/mcp_client.env` (0600) and is never printed; `idmc_mcp_bridge.py --check` lists the chosen servers;
  after a restart the `mcp__plugin_informatica-idmc-headless_idmc__*` tools appear, read-only unless the user chose `--allow-writes`, and
  one read-only call answers.

**US-17 demo**
- `python3 verify/offline_check.py` (retail) and `python3 verify/bid_verify.py offline` pass; a live rebuild follows
  `BUILD.md` to its proof step.

**US-19 clean-data**
- Measures the slice first and reuses the org's Cleanse / dictionary / rule assets; writes only a stage table.
- After one job: agreement with the SQL twin per record (decision, survivor), the extra finds with examples, run time.
- Nothing applied to the real table without a yes on the merge list.

**US-20 customer CSV, timed from zero**
- Offline: `python3 toolkit/demos/customer_master_csv/check.py` passes (precision 1.00, recall at least 0.95).
- Live, following `BUILD.md` with its timing log filled in: agent installed and Data Integration RUNNING; flat-file
  connection tested; mapping and task deployed with `--execute --expect-org`; one run SUCCESS; `check.py --compare`
  says the live output matches the twin. Target: about 20-40 minutes the first time.

**US-18 update**
- After `/plugin update`, `~/.idmc_toolkit/` is unchanged and `/informatica-idmc-headless:connect` still logs straight in.

## Live runs

| Date | Story | Org type | Result | Notes |
|---|---|---|---|---|
| | | | | |
