---
name: idmc-cdi
description: Use for Informatica IDMC Cloud Data Integration: build mappings headless (the mapping generator), mapping tasks, taskflows and schedules, run and monitor jobs, change live pipelines safely, and speed up or right-size CDI pipelines (concurrency, job caps, DAG fan-out, latency).
---

# IDMC co-pilot: Data Integration (CDI): mappings, tasks, taskflows, performance

Part of the **idmc-mp** plugin (the IDMC co-pilot). Paths are relative to the plugin root, `${CLAUDE_PLUGIN_ROOT}`
(two folders above this skill's folder). Use `python3` (on Windows `python` or `py`).

## Ground rules (from the core `idmc-mp` skill; they always apply)
- **Lessons first.** Before any call or design choice, search the lessons:
  `grep -i "<thing or error>" "${CLAUDE_PLUGIN_ROOT}/lessons/lessons.jsonl"` (this area: `"domain": "cdi"`),
  then `knowledge/04-mappings/lessons.md` and the user's own `~/.idmc_toolkit/lessons-local.jsonl`.
- **Prove the org first.** `python3 "${CLAUDE_PLUGIN_ROOT}/toolkit/check_login.py"` (one login attempt per run: retries
  lock the account). Take every host from `products[].baseApiUrl`; never hand-build a pod URL.
- **The user's systems are the right systems.** Never steer to another technology; ask if none is named.
- **Never say "not possible"** before the workaround ladder in
  `knowledge/00-start-here/08-new-pipeline-milestones-any-source-any-target.md` is worked in this org.
- **Writes are dry runs** until the org guard passes (`--execute --expect-org <orgIdV3>`); say what will change first.
- **Evidence, not claims:** finish with ids, row counts, job states or the API answer that proves the result
  (`knowledge/14-working-with-claude/02-evidence-discipline.md`).

## What users ask for
- Build a mapping from the user's source to their target, run it and prove the row counts.
- Wrap mappings in tasks and taskflows, and schedule them.
- Make a slow or costly pipeline faster or cheaper (concurrency, fan-out, job budget).
- Change a live pipeline without breaking it.

## How to work
1. Read the Mapping Fast Path first (doc 00): the ten commands, connector settings, costly errors.
2. Copy ONE example from `toolkit/mapgen/examples/` that matches the shape; options in `toolkit/mapgen/docs/SPEC_REFERENCE.md`.
3. Build -> lint -> import -> task -> run with `toolkit/mapgen/mapgen.py`; prove with row counts on both sides.
4. No template for the user's connector or transformation: use the exemplar route (doc 00 section 7.0).
5. Orchestrate with `toolkit/lib/idmc_taskflow_schedule.py` (doc 04); for speed use the DAG / staged fan-out (doc 07).
6. Changing something live: follow doc 08 (small change in place; big change side by side, parity, then the swap gate; rollback kit first).

## Read (in this order when unsure)
| Need | File |
|---|---|
| Mapping Fast Path (start here) | `knowledge/04-mappings/00-mapping-fast-path-read-this-first.md` |
| Object model | `knowledge/04-mappings/01-cdi-object-model.md` |
| How mappings are built headless | `knowledge/04-mappings/02-how-claude-builds-mappings-headless.md` |
| Mapping tasks: create, update, run, monitor | `knowledge/04-mappings/03-mapping-tasks-create-update-run-monitor.md` |
| Taskflows and schedules | `knowledge/05-taskflows-schedules/01-taskflows-schedules.md` |
| Performance, concurrency, job caps | `knowledge/04-mappings/06-performance-concurrency-job-caps.md` |
| Changing pipelines safely | `knowledge/04-mappings/07-changing-pipelines-safely.md` |
| Source and target gotchas | `knowledge/04-mappings/08-source-target-gotchas.md` |
| Serving outputs to BI and apps | `knowledge/04-mappings/09-serving-outputs-to-bi-and-apps-freshness-latency-reverse-etl.md` |

## Tools (`--help` on each)
- `toolkit/mapgen/mapgen.py`: mapping generator: build, lint, import, task, run, deploy, log, jobs
- `toolkit/mapgen/exemplar.py`: read the shape of an exported mapping that already uses a connector
- `toolkit/lib/idmc_mttask.py`: mapping tasks: show, clone, update, run
- `toolkit/lib/idmc_taskflow_schedule.py`: linear taskflows and schedules

## When you learn something
Append a generic lesson (no org ids, hosts, people or secrets; same shape as `lessons/lessons.jsonl`) to
`~/.idmc_toolkit/lessons-local.jsonl`, or run `/idmc-mp:save-lesson`. Never write inside the plugin folder.
