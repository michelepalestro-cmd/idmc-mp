# Master IDMC KB: rules for any Claude session working here

> **Plugin install:** your login lives in `~/.idmc_toolkit/IDMC_LOGIN.txt` (run `python check_login.py` once
> to create it), not in this folder. Where the docs below say "IDMC_LOGIN.txt at the toolkit root", that home
> file is what is read (a root copy still works when you run from a git clone).

You are in the **Master IDMC KB**: one folder with the knowledge base (topic folders `00`-`14`), its Python library
(`14 - .../Script Library`), a mapping generator and three demo blueprints for building and running Informatica IDMC demos **headless** (REST, no UI), in the user's own IDMC org.

## The goal and the two rules (they override everything below)
**Goal:** help the user create any IDMC asset and deploy IDMC end to end, with every capability they ask for, on the
systems they have. The milestones in `00 - Start Here/08 New Pipeline Milestones - any source, any target.md` are the
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
  (`03 - Data Integration (CDI)/00 Mapping Fast Path - read this first.md` §7.0). Ask the user for an existing mapping
  that already uses it, or ask them to create one once in the Mapping Designer (one source, one target, saved); export
  it, read it with `python core/mapgen/exemplar.py <zip>`, build from that shape, prove it, then enrich the package
  (connector row, example spec, lesson). Never stall, guess, or switch the user to a connector the generator knows.
- **Copy the method, not the choices:** the order of work, the gates, the safety rules and the evidence on how IDMC
  behaves carry over; object names, field lists, load modes and settings from an example do not.
- **Lessons are dated evidence.** Your org's live answer wins; re-probe when a lesson and the org disagree.

## Read in this order
1. `README.md` (what is here, how to connect, the rebuild path, the KB map)
2. `00 - Start Here/02 The Laws of Headless IDMC.md` (30 laws; they override your instincts about REST APIs)
3. **A new pipeline:** `00 - Start Here/08 New Pipeline Milestones - any source, any target.md` (runtime → connections →
   folder and assets → contract → mapping → task → first run and proof → DQ → orchestration → governance).
4. **Any mapping or mapping-task work:** `03 - Data Integration (CDI)/00 Mapping Fast Path - read this first.md`
   (the ten commands, per-connector settings, the costly errors), then ONE example from `core/mapgen/examples/` and
   `core/mapgen/docs/SPEC_REFERENCE.md` for options. Open the long `03` docs only when the fast path points there.
5. **Live production system, or a build someone else made:** `00 - Start Here/09 What Went Wrong - Production Deployment Post-Mortem.md` (each failure with the
   check that catches it)
6. `00 - Start Here/04 Error Triage.md` when anything fails
7. The blueprint's `README.md` then `BUILD.md` (`demos/<name>/`)
8. Before any IDMC call, search the lessons first: `grep -ril "<thing>" "13 - Lessons Learned"`

This KB ships inside the `idmc-mp` Claude skill (`../SKILL.md`, playbook in `../references/`): nothing to install.

## Non-negotiables
- **The IDMC login lives in `IDMC_LOGIN.txt`** (the KB root: `IDMC_USER`, `IDMC_PASS`, `IDMC_LOGIN_HOST`); every
  script reads it. If the user cannot connect, have them fill in that file, nothing else. It is the ONE credential file
  allowed in the folder; the blueprints' other secrets live outside it, in `~/.idmc_toolkit/.env` (`IDMC_CREDS_FILE`).
  Never print the file's values, and never write a credential, token, session id or key anywhere else in the toolkit,
  a transcript or a command line. Print key names, never values.
- **One login, one attempt.** A few rejected logins lock the account (`IDS_086`). The core library serializes logins,
  caches the session and writes a block file after a rejected login: never delete that file without the user confirming
  the password was fixed.
- **One writer per org.** Only one session writes to an org at a time. Prove the org (`python check_login.py`, which runs the
  Script Library's `idmc_session.py whoami`) before any change, and pass `--execute --expect-org <orgIdV3>` for writes. Everything is a dry run otherwise.
  The mapping generator is the one exception: `core/mapgen/mapgen.py deploy` writes unless you pass `--dry-run`. So
  prove the org first, run `--dry-run` before every deploy, and keep the profile's `guards` covering every connection
  alias you write to.
- **Read back every write.** A 200 can be empty or silently reverted (Law 4, Law 12).
- **Runs cost money / jobs.** Every task and taskflow run counts against the org's job budget and IPUs. Building is
  free; ask the user before running loads, schedules or anything that loops.
- **Integration logic belongs in IDMC.** If CAI / CDI / CDQ can do it, the runtime path uses IDMC. Python is for
  building, deploying, verifying and stand-in traffic, and, where IDMC has no native path, for a small bridge (an agent
  pre/post step, or a script that fetches, converts or stages data for an IDMC connector). A bridge is a valid
  workaround to offer; a refusal is not.
- **Keep the toolkit generic.** Your org's ids go in each blueprint's `config.json` / `state/`; don't share
  those files. Before re-sharing the toolkit empty `IDMC_LOGIN.txt` and run `python tools/secret_scan.py`; it must print CLEAN.
- **Never delete what you can't restore.** Export (v3 export package) before deleting IDMC objects; keep undo files.

## When you learn something
Add the reusable fact to the matching topic doc (`01`-`12`, `14`) and as a lesson in `13 - Lessons Learned` (generic: no org
ids, hosts, people or secrets), and fix the blueprint's BUILD.md "Gotchas" if it changes a step.
