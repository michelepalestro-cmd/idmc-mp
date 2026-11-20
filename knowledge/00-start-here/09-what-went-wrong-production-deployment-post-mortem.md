# What Went Wrong: a Production Deployment Post-Mortem

**Answers:** What went wrong when IDMC was deployed onto a large, live production data platform, and which check
would have caught each problem before it cost a night, a run or a customer-visible number?

**Read when:** before you take IDMC (profiling, DQ rules, migration, mastering) onto a live production database or
warehouse; before you inherit a build someone else (or another coding agent) made; before you call any
deployment "done".

**Key rules:**
- "Done" is a measured state on the table consumers read, never a job status (L-DQ-136, L-MDM-083, L-METHOD-147).
- Prove the backup by restoring it; a backup alert that is always red is the same as no backup (L-ENV-113, L-ENV-123).
- A gate that passes 100 % of rows on every run is not testing anything (L-DQ-143, L-DQ-152).
- Before you extend or "fix" anything, inventory what is live and who owns it (L-MIG-094, L-METHOD-137, L-METHOD-138).
- Hash the reviewed artifact right before you run it; another session may have rewritten it (L-METHOD-132).

**Related:** [End-to-End Playbook](07-end-to-end-playbook-deploy-and-operate-idmc-with-claude.md) ·
[New Pipeline Milestones](08-new-pipeline-milestones-any-source-any-target.md) ·
[Error Triage](04-error-triage.md) · [Lessons Learned](../lessons/README.md) ·
[Multi-Agent Coordination](../14-working-with-claude/03-multi-agent-coordination.md)

**Last verified:** 2026-11-10

---

## The deployment in one paragraph

A production data platform (a very large served table, a larger raw layer, hundreds of tables in a warehouse and
an application database) was brought onto IDMC: a Secure Agent next to the data,
JDBC V2 connections, column profiles and DQ rule specifications on raw and gold tables, address verification, a
table-by-table migration into a consolidated model and a golden-record (mastering) layer. Several Claude sessions and
another coding agent worked on it at the same time. The IDMC product behaviour mostly worked as the KB describes. What
went wrong was almost always **around** IDMC: the host, the backups, the gates, the ownership of work, and the
definition of "done". Every item below links to the lesson with the exact evidence and fix.

## 1. The host and the database

| What went wrong | Check that catches it | Lesson |
|---|---|---|
| After a reboot the data disk did not mount (`nofail`); the database started on an empty directory and the data looked gone | after any reboot, compare mounts with `/etc/fstab` and the database's data path before anyone "recovers" | L-ENV-101 |
| A forced OS password expiry blocked every automated key login | never force-expire service accounts; check `chage -l` on any account automation uses | L-ENV-102 |
| Memory pressure from the co-located Secure Agent stopped sshd accepting connections | make sshd OOM-immune; cap the agent's cgroup | L-ENV-103, L-AGENT-119 |
| The agent pushed host load past 100 and a normal stop hung | a watchdog that kills the agent's cgroup on load or IO thresholds | L-AGENT-119, L-AGENT-120 |
| Saving agent configuration restarted the Data Integration Server and killed every job on the agent, including other sessions' jobs | treat an agent config save as a restart: announce it, wait for idle | L-AGENT-121 |
| A whole project failed in one minute: another session's resize had rebooted the VM | check host boot time before debugging jobs | L-ENV-122 |
| Memory walls were the database's baseline RSS, not the query | settle merges and purge allocator caches before heavy mutations | L-ENV-109 |
| Migration lanes drove the live source to its memory limit and production queries failed | a dedicated reader login, so one KILL stops every lane; stream, do not group | L-MIG-093 |
| A temporary bulk-load tweak (fsync off) stayed in force after the load | every temporary setting gets a revert step and a dated owner | L-ENV-121 |
| A live-only code edit in a running container existed in no image | rebuild from the running container's source before redeploying | L-ENV-108 |
| A non-root container could read but not rename files in a root-owned drop folder, so every batch errored | match the drop folder's owner to the container uid | L-ENV-104 |

## 2. Backups and destructive changes

| What went wrong | Check that catches it | Lesson |
|---|---|---|
| The nightly backup covered 2 of the databases and failed every night, so its alert was ignored; no restore had ever been tested | list what the backup actually covers; restore one database to a scratch host | L-ENV-113 |
| A new host held the only copy of migrated data with no backup timer and one local backup on the same disk | no data lands on a host before its offsite backup has run once | L-ENV-123 |
| Repair "backups" kept as tables inside the database piled up to hundreds of tables on a 91 % full disk | rollback copies go off the server; a janitor drops untracked copies after 7 days | L-ENV-114 |
| Waiting for spend approval for offsite backup left nothing at all | a filesystem-level freeze (ClickHouse `FREEZE`) is an immediate, near-free guard | L-ENV-105 |
| A truncate-then-insert rebuild ran out of memory and left a table empty every night | rebuild into a staging table and swap atomically | L-ENV-106 |
| A cleanup delete hid tens of millions of rows IDMC had loaded and reset the progress cursors | no deletes on a migration target while lanes run; know the engine's recovery window | L-MIG-089 |
| A re-ingest doubled a partition; every reader without dedup served rows twice | on merge-deduplicated engines, read with `FINAL` or dedupe, and count after every load | L-ENV-107 |
| Constraints added mid-load rejected rows that had loaded fine an hour earlier | add constraints before the load, or re-check every earlier row | L-MIG-090 |

## 3. Data quality gates that proved nothing

| What went wrong | Check that catches it | Lesson |
|---|---|---|
| Every DQ gate measured the legacy table, not the gold table customers read | point gates at the served table; run old and new side by side | L-DQ-136 |
| Status columns were 100 % "passed": constants, or forced by a CHECK constraint | a gate with no failures over many runs is suspect; bind independent rules to it | L-DQ-143, L-DQ-152 |
| A fingerprint column held the SHA-256 of an empty string | reject `e3b0c442…b855` in the hash rule | L-DQ-146 |
| Most lineage ids were typed into SQL or written outside IDMC | validate lineage stamps as data: real IDMC object ids only | L-CDI-295, L-CDI-293 |
| A case-sensitive key comparison passed a partition holding about a million duplicates | normalise case and whitespace inside key checks | L-DQ-139 |
| Approximate distinct counts were used to "prove" a key unique | exact counts in key and duplicate checks | L-DQ-141 |
| A correct repair broke the duplicate gate overnight; the dependent flagging job had not run in weeks | after a repair, re-run the dependent flags; do not revert the repair | L-DQ-138 |
| A hand-written fix query selected millions of rows where the gate flagged 2 groups | build the fix set from the gate's own view | L-DQ-135 |
| An empty standardized column made "address present" fail on a third of the rows | check presence on the raw column, standardization separately | L-DQ-145, L-DQ-140 |
| A 5-digit postal rule failed ZIP+4 output | define each column's format before writing its rule | L-DQ-156 |
| Closed lists taken from observed values disagreed with the data dictionary | take closed lists from the dictionary's enums | L-DQ-153 |
| A classification column was empty on every row of the target | profile fill rates before writing rules | L-DQ-142 |
| Address verification ran on reference address points: no served entity verified | confirm the population (which table, which rows) before any verification run | L-DQ-144 |
| A quoted DQ score was older than the table's last write | the profile's last completed run must be newer than the last write | L-METHOD-147, L-DQ-150 |
| The session's own DQ evaluator read empty as missing and accepted a script name as lineage | validate your evaluator on known-bad rows first | L-METHOD-139 |

## 4. Profiling a live database

| What went wrong | Check that catches it | Lesson |
|---|---|---|
| "Premature EOF" was the SQL override's own 4 GB memory cap, not the network | read the database's query log for the real code (241); size the cap to the query | L-DQ-148 |
| A profile failed in STAGING_TO_STORE after the read had finished and never resumed | resubmit unchanged | L-DQ-149 |
| A failed run left the previous COMPLETED run showing as "latest" | track the job id you started, not `lastRunKey` | L-DQ-150 |
| Metric-store value lists mixed in earlier runs' values | keep entries whose totalRows equals the current totalRows | L-DQ-151 |
| A find-by-name after create missed profiles past 200 (offset is ignored) | page with a large limit and check the count | L-DQ-155 |
| 940 tables waited because each database needed its own connection and REST never returns the stored password | plan one connection per database at provisioning | L-CONN-136 |
| Profiles store real values in the cloud metric store | leave PII and raw JSON blobs out of every profile | L-DQ-157 |
| A full ALL_ROWS read of a billion-row blob registry would have pulled a few hundred GB | inventory and price the run first; sample | L-CDI-296, L-DQ-158, L-DQ-159 |
| A long profiling orchestrator ran in a laptop shell and was killed under memory pressure | run multi-hour orchestrators on a server with a done-ledger | L-METHOD-148 |

## 5. Inherited builds, migration and mastering

| What went wrong | Check that catches it | Lesson |
|---|---|---|
| An AI-generated build had 357 one-off mappings, logic in SQL strings and fake lineage | audit before extending: count mappings, read full run history, check lineage | L-CDI-293, L-MIG-094 |
| An external runner rewrote each mapping's SQL before every run, so the IDMC export alone could not reproduce the pipeline | export the runner and its query templates with the assets | L-CDI-294 |
| "Everything is migrated" could not be proven while the source kept changing | freeze or checkpoint the source; reconcile per dataset | L-MIG-091 |
| A one-table-for-everything target used about 11x the bytes per row | project disk before loading billions of rows | L-MIG-092 |
| A golden-table rebuild doubled the table with provisional records and every mastering rule dropped | compare row count and status mix with the previous build before "done" | L-MDM-083 |
| A survivorship demo was designed over two sources that were byte-identical mirrors | prove the sources conflict first | L-MDM-082 |
| Repairs under the shared admin login made every change unattributable | one named writer on the served layer; alert on any other | L-ENV-118 |

## 6. Many sessions, one estate

| What went wrong | Check that catches it | Lesson |
|---|---|---|
| A peer session overwrote the reviewed SQL file between review and run | hash the artifact right before running it | L-METHOD-132 |
| "Fixing" an agentless runtime binding re-armed lanes the owner had retired | ask why before fixing what looks broken | L-METHOD-138 |
| Stopping another session's jobs left their schedules enabled | stop the schedule, then the job | L-METHOD-135 |
| An expired lease left a critical-path step with no owner | when a lease expires, reassign its open steps | L-METHOD-142 |
| A runner rewrote its manifest from memory and erased a hand edit | never edit a runner's state while it runs | L-METHOD-136 |
| Six audit subagents declared DQ governance absent: none looked at cron | inventory schedulers before concluding something is missing | L-METHOD-131 |
| The live build was on a VM no board or doc mentioned | inventory the live estate before asking the user | L-METHOD-137 |
| "How does our pipeline do X" was answered from memory and named the wrong component | answer from the exported live assets and run history | L-METHOD-145 |
| A bulk fill was 2M rows short (a TSV NULL-encoding bug) | reconcile predicted against realized counts after every fill | L-METHOD-130 |
| Work was deferred behind another session's load until the user forced it | a bounded wait and a capped fallback | L-METHOD-140 |

## 7. Access, cost and sharing

| What went wrong | Check that catches it | Lesson |
|---|---|---|
| An approved disk resize was impossible: no available identity had the permission, and human tokens kept expiring | test the identity's permission before promising the change | L-ENV-119 |
| There was no billing export, so cost had to be estimated by hand; a "temporary" scale-up ran for days | turn on the billing export on day one; date every temporary scale-up | L-ENV-124 |
| A planned teardown never ran (auto-delete disabled) and a budget alert never fired | check the delete schedule is enabled; budgets alert on recorded spend only | L-ENV-111 |
| Full-scale address verification was unknown spend with no visible meter | price throughput and IPUs on a sample first | L-IPU-062 |
| A filled-in credential template sat in the shareable KB for days | the session that sees it fixes it; scan before every share | L-METHOD-141, L-METHOD-144 |
| Assets were "missing" because someone looked in another pod | hand-offs give the org name and the full pod URL | L-METHOD-134 |
| Secrets folded into warehouse SQL appeared in error messages | keep secrets out of warehouse SQL entirely | L-ENV-110 |

## What to do differently, in order

1. **Day 0:** offsite backup run and restored once; billing export on; one named writer per served layer; agent
   cgroup caps and sshd protection on any shared host (§1, §2, §7).
2. **Before any IDMC write:** inventory the live estate, its schedules and owners; audit any inherited build (§5, §6).
3. **Before any gate:** point it at the served table, test it on known-bad rows, and make sure it can fail (§3).
4. **Before any profile or verification at scale:** inventory, price, sample, and size the per-query caps (§4).
5. **Before "done":** compare against the previous build, reconcile counts, and check that every score is newer than
   the table's last write (§3, §5).
