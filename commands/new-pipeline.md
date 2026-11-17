---
description: Plan, build, run and prove an IDMC pipeline on the systems you name
argument-hint: "<source> to <target> [details]"
---

Use the idmc-mp skill. The user wants a pipeline: $ARGUMENTS

1. Build with the systems the user named. Never switch them to another source, target or cloud. If a system is
   missing, ask once.
2. Follow `${CLAUDE_PLUGIN_ROOT}/skills/idmc-mp/kb/00 - Start Here/08 New Pipeline Milestones - any source, any target.md`: runtime, connections,
   project and folder, data contract, mapping, mapping task, first run and proof, DQ if in scope, orchestration,
   hand-over. For mappings, use `${CLAUDE_PLUGIN_ROOT}/skills/idmc-mp/kb/03 - Data Integration (CDI)/00 Mapping Fast Path - read this first.md` and
   `${CLAUDE_PLUGIN_ROOT}/skills/idmc-mp/kb/core/mapgen/`.
3. Prove the org before the first write, dry-run before every deploy, and read back after every write.
4. Ask before running loads or schedules: they count against the job limit and IPUs.
5. Report each milestone as it completes, with real evidence (ids, row counts, run status). Never say something is
   not possible before working the workaround ladder in this org.
