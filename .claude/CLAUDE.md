# Working on this repository

This is the source of the `idmc-mp` Claude Code plugin. When you change it:

- Follow [CONTRIBUTING.md](../.github/CONTRIBUTING.md) (where things go, the lesson format, keeping everything generic) and
  [knowledge/RULES.md](../knowledge/RULES.md) (the rules for any session that touches IDMC).
- Never write a credential, org id, host, IP address, e-mail or person's or company's name into the repository.
- After editing lessons, run `python3 toolkit/tools/sync_lesson_counts.py` and
  `python3 toolkit/tools/build_skill_field_lessons.py`.
- Before finishing, run `python3 toolkit/tests/run_tests.py` (must print ALL PASSED) and `python3 toolkit/tools/secret_scan.py`
  (must print CLEAN).
