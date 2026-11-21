---
description: Clean a large table with IDMC mappings (standardize, match duplicates, decide survivors) into a stage table, proven against a SQL twin
argument-hint: "<connection> <table> [region or slice] [what to clean: duplicates, rules]"
---

Use the informatica-idmc-headless, idmc-data-quality and idmc-cdi skills. On Windows, use `python` (or `py`) where these steps say `python3`.
Clean: $ARGUMENTS

Follow `${CLAUDE_PLUGIN_ROOT}/knowledge/08-data-quality/05-cleaning-a-large-dataset-with-mappings.md`.

1. Prove the org (`python3 "${CLAUDE_PLUGIN_ROOT}/toolkit/check_login.py"`). Never retry a failed login.
1b. Check the licence before building (one read, no write): the identity login's `effectivePrivileges`, roles and
   design objects show what the org holds (L-MDM-011 shows the method for MDM; read CDQ the same way: data quality and
   profiling privileges, and `RULE_SPECIFICATION` / Cleanse objects in `toolkit/lib/idmc_objects.py`). The login's
   `products[]` list is only a label. The Cleanse step needs CDQ and a Secure Agent with the Data Quality service: it does not run on the
   Hosted Agent (L-CDI-279). Without CDQ, say so plainly and offer the no-licence path:
   `${CLAUDE_PLUGIN_ROOT}/toolkit/demos/customer_master_csv/` (plain CDI mappings: clean, deduplicate, assign ids).
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
7. Save what the run taught you with `/informatica-idmc-headless:save-lesson`.

Want one golden record per customer with a lasting customer id (mastering), not only a clean-up? Use the idmc-mdm skill
and `${CLAUDE_PLUGIN_ROOT}/knowledge/10-mdm/README.md` (native MDM SaaS, or a warehouse stand-in when MDM is not
licensed); for a customer file with no DQ or MDM licence, the `customer_master_csv` demo does it with plain mappings.
