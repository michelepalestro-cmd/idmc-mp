# Rules for any Claude session working with the IDMC MP plugin

Paths in inline code are relative to the plugin root. The plugin holds the knowledge base (topic folders `00`-`14` under
`knowledge/`), the lessons (`knowledge/lessons/`), the skills and commands, and a Python toolkit (`toolkit/lib/`, a
mapping generator in `toolkit/mapgen/` and four demo blueprints in `toolkit/demos/`) for building and running
Informatica IDMC **headless** (REST, no UI), in the user's own IDMC org.

## The goal and the two rules (they override everything below)
**Goal:** help the user create any IDMC asset and deploy IDMC end to end, with every capability they ask for, on the
systems they have. The milestones in `knowledge/00-start-here/08-new-pipeline-milestones-any-source-any-target.md` are the
recommended order for a pipeline, not a requirement: if the user wants one asset, another order or their own way, do
that. The README's "Create any IDMC asset" table says where each asset type starts.
1. **Never push the user to another technology.** No "use BigQuery / Snowflake / X instead", no silent fallback to a
   system the user did not name. A system the KB has never covered (SAP, Oracle, files, an API...) is built brand new
   with everything the KB has learned.
2. **Never say "not possible" until the workaround ladder (same doc: lessons → re-probe → another plane → clone a
   UI-made object → capture the UI call → another IDMC component → a Python bridge → one residual click) has been
   worked in this org.** Then report what each rung showed, the nearest working path on the user's systems, and any
   single manual step left. "The KB doesn't cover it" or "a lesson says it failed once" is never a no.
   **The KB is not an allow-list:** nothing is forbidden or unsupported because the KB does not mention it; anything
   IDMC can do is in scope. **Native IDMC first; Python only when no IDMC path works**, and then as a bridge into IDMC.
   Worked example (flat-file target, in the milestones doc): not documented, built on the user's own connection,
   IDMC wrote the file natively, recorded as a lesson.

## The KB is guidance, not a script
- **The user's systems are the right systems.** Build with the source, target and connectors the user names. The KB's
  examples (PostgreSQL, BigQuery, Snowflake, Databricks, Salesforce, SharePoint, ClickHouse, Tableau, flat files) are
  examples, not recommendations. Never steer the user to a system, or fall back to one (e.g. BigQuery), because the KB
  or the generator has more examples of it. If the user has not named a system, ask.
- **A connector the KB has not covered is normal.** Say so, then find its settings in the org (connector metadata, one
  connection test, one small run), and record the result as a lesson.
- **A source, target or transformation IDMC supports but the generator has no template for: use the exemplar route**
  (`knowledge/04-mappings/00-mapping-fast-path-read-this-first.md` §7.0). Ask the user for an existing mapping
  that already uses it, or ask them to create one once in the Mapping Designer (one source, one target, saved); export
  it, read it with `python toolkit/mapgen/exemplar.py <zip>`, build from that shape, prove it, then enrich the package
  (connector row, example spec, lesson). Never stall, guess, or switch the user to a connector the generator knows.
- **Copy the method, not the choices:** the order of work, the gates, the safety rules and the evidence on how IDMC
  behaves carry over; object names, field lists, load modes and settings from an example do not.
- **Lessons are dated evidence.** Your org's live answer wins; re-probe when a lesson and the org disagree.

## Read in this order
1. `knowledge/README.md` (what is here and the KB map); the root `README.md` for setup
2. `knowledge/00-start-here/02-the-laws-of-headless-idmc.md` (30 laws; they override your instincts about REST APIs)
3. **A new pipeline:** `knowledge/00-start-here/08-new-pipeline-milestones-any-source-any-target.md` (runtime → connections →
   folder and assets → contract → mapping → task → first run and proof → DQ → orchestration → governance).
4. **Any mapping or mapping-task work:** `knowledge/04-mappings/00-mapping-fast-path-read-this-first.md`
   (the ten commands, per-connector settings, the costly errors), then ONE example from `toolkit/mapgen/examples/` and
   `toolkit/mapgen/docs/SPEC_REFERENCE.md` for options. Open the long `03` docs only when the fast path points there.
5. **Live production system, or a build someone else made:** `knowledge/00-start-here/09-what-went-wrong-production-deployment-post-mortem.md` (each failure with the
   check that catches it), and `knowledge/00-start-here/12-run-it-in-production.md` (the Day-2 runbook)
6. `knowledge/00-start-here/04-error-triage.md` when anything fails
7. The blueprint's `README.md` then `BUILD.md` (`toolkit/demos/<name>/`)
8. Before any IDMC call, search the lessons first: `grep -i "<thing>" knowledge/lessons/lessons.jsonl` and the user's own
   `~/.idmc_toolkit/lessons-local.jsonl`

This KB ships inside the `idmc-mp` Claude Code plugin (skills in `skills/`, playbook in `knowledge/00-start-here/`): nothing else to install.

## Non-negotiables
- **The IDMC login lives in `~/.idmc_toolkit/IDMC_LOGIN.txt`** (`IDMC_USER`, `IDMC_PASS`, `IDMC_LOGIN_HOST`), outside
  the plugin; `IDMC_CREDS_FILE` or environment variables can point elsewhere. If the user cannot connect, run
  `/idmc-mp:connect` and have them fill it in with `python3 toolkit/check_login.py --setup` in a terminal. Never ask
  for a password in the chat, never print the file's values, and never write a credential, token, session id or key
  into the plugin, a transcript, a log or a command line. Print key names, never values.
- **One login, one attempt.** A few rejected logins lock the account (`IDS_086`). The library serializes logins,
  caches the session and writes a block file after a rejected login: never delete that file without the user confirming
  the password was fixed.
- **One writer per org.** Only one session writes to an org at a time. Prove the org (`python3 toolkit/check_login.py`)
  before any change. Every write, including the mapping generator's, is a dry run until you pass
  `--execute --expect-org <orgIdV3>`, and it refuses to run in any other org.
- **Read back every write.** A 200 can be empty or silently reverted (Law 4, Law 12).
- **Runs cost money / jobs.** Every task and taskflow run counts against the org's job budget and IPUs. Building is
  free; ask the user before running loads, schedules or anything that loops.
- **Integration logic belongs in IDMC.** If CAI / CDI / CDQ can do it, the runtime path uses IDMC. Python is for
  building, deploying, verifying and stand-in traffic, and, where IDMC has no native path, for a small bridge (an agent
  pre/post step, or a script that fetches, converts or stages data for an IDMC connector). A bridge is a valid
  workaround to offer; a refusal is not.
- **Talk only to the user's systems.** Never send org data, credentials or logs to any other host, and never run
  third-party IDMC tools before reviewing them (`knowledge/11-mcp-claire/07-ecosystem-plugins-registries-community-tools.md` §5).
- **Keep the plugin generic.** The user's org ids go in each blueprint's `config.json` / `state/` (git-ignored); never
  write them into the plugin folder. Before sharing a clone, run `python3 toolkit/tools/secret_scan.py`; it must print CLEAN.
- **Never delete what you can't restore.** Export (v3 export package) before deleting IDMC objects; keep undo files.

## When you learn something
Save it as a generic lesson (no org ids, hosts, people or secrets) in the user's `~/.idmc_toolkit/lessons-local.jsonl`
with `/idmc-mp:save-lesson`: the plugin folder is replaced on every update, so never write into it. To share a lesson
with everyone, follow `.github/CONTRIBUTING.md` (an issue or a pull request).
