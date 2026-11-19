---
description: Profile a table, propose data quality rules, and put them into the pipeline with scores
argument-hint: "<connection> <table> [columns or rules]"
---

Use the idmc-mp and idmc-data-quality skills. On Windows, use `python` (or `py`) where these steps say `python3`.
Table: $ARGUMENTS

1. Prove the org (`python3 "${CLAUDE_PLUGIN_ROOT}/toolkit/check_login.py"`).
2. Profile the table on the user's own connection (paths in
   `${CLAUDE_PLUGIN_ROOT}/knowledge/08-data-quality/02-profiling-what-is-headless.md`) and summarize nulls,
   distincts, patterns and outliers per column.
3. Propose rules (completeness, validity, consistency, uniqueness) with the column, the rule and why; grep the lessons
   (`"domain": "dq-profiling"`) for each rule type.
4. On the user's yes: author rule specs by cloning a template
   (`01-dq-assets-rule-specs-cleanse-dictionaries-verifiers.md` section 3.3), run them inside a CDI mapping, and report
   pass / fail counts per rule.
5. Offer a scorecard (`04-dq-scorecards-warehouse-pattern-and-data-profiling-scorecards.md`).
