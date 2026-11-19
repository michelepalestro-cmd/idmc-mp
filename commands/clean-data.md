---
description: Clean a large table with IDMC mappings (standardize, match duplicates, decide survivors) into a stage table, proven against a SQL twin
argument-hint: "<connection> <table> [region or slice] [what to clean: duplicates, rules]"
---

Use the idmc-mp, idmc-data-quality and idmc-cdi skills. On Windows, use `python` (or `py`) where these steps say `python3`.
Clean: $ARGUMENTS

Follow `${CLAUDE_PLUGIN_ROOT}/knowledge/08-data-quality/05-cleaning-a-large-dataset-with-mappings.md`.

1. Prove the org (`python3 "${CLAUDE_PLUGIN_ROOT}/toolkit/check_login.py"`). Never retry a failed login.
2. Measure before building: rows in the slice, how many are candidates (rows sharing a key, or failing a rule), and the
   job budget this month. Pick one region or slice; full rebuilds stay in the warehouse's SQL.
3. List the org's DQ assets first (Cleanse, dictionaries, rule specifications: `toolkit/lib/idmc_objects.py`) and reuse
   them inside the mapping.
4. Build the mapping in the shape of the doc's section 2 (two readers + Sorters, Expression, Cleanse, key and guard flags,
   Aggregator, Filter, decision Expression, Joiner back, stage target). Write only to a stage table in a work schema.
5. Ask before the run (one job). Then compare with the SQL twin, read only: same decision and survivor per record; list
   what IDMC found extra and why.
6. Report: candidates, agreement, extra finds with examples, run time, job used. Apply nothing to the real tables
   without the user's yes on the merge list; keep old ids as aliases of the survivor.
7. Save what the run taught you with `/idmc-mp:save-lesson`.
