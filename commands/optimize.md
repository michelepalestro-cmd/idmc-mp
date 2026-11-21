---
description: Find why an IDMC pipeline is slow or costly and propose measured fixes (concurrency, fan-out, job budget, IPU)
argument-hint: "<taskflow, task or project name>"
---

Use the informatica-idmc-headless, idmc-cdi and idmc-ipu skills. On Windows, use `python` (or `py`) where these steps say `python3`.
Pipeline: $ARGUMENTS

1. Prove the org (`python3 "${CLAUDE_PLUGIN_ROOT}/toolkit/check_login.py"`), then read the pipeline's objects and its
   recent runs read-only (`toolkit/lib/idmc_objects.py`, `toolkit/mapgen/mapgen.py jobs`/`log`).
2. Measure before proposing: wall time per step, the ~20 s floor per task, queueing vs running, rows per run, jobs per
   day against the monthly job cap, and IPU use if readable
   (`${CLAUDE_PLUGIN_ROOT}/knowledge/04-mappings/06-performance-concurrency-job-caps.md`,
   `${CLAUDE_PLUGIN_ROOT}/knowledge/13-ipu-cost/02-metering-consumption-exports.md`).
3. Grep the lessons (`"domain": "cdi"`, `"domain": "ipu-licensing"`) for each bottleneck you find.
4. Propose fixes ranked by measured gain: consolidate tasks, DAG / staged fan-out instead of linear, concurrency within
   the DTM pool, fewer and larger jobs, pushdown. Give the expected effect and how to prove it.
5. Apply only on the user's yes, using the safe-change rules in
   `${CLAUDE_PLUGIN_ROOT}/knowledge/04-mappings/07-changing-pipelines-safely.md`, then re-measure.
