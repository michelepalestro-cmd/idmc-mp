# Org-to-Org Migration Runbook

**Answers:** How do I move a working IDMC estate from one org to another without the UI? Who may write to which org?
What are the phases, their evidence and their undo? How do I validate before the cutover, and what comes after it?

**Read when:** planning or running an org-to-org migration, a production split or a promotion between orgs; sizing
the lanes and the job budget for one.

**Key rules:**
- One lead session is the only IDMC writer per org; lanes prepare host work, repoints, QA and cleanup without logging
  in (L-MIG-044).
- Follow M0 to M13, each phase with posted evidence and its own undo (L-MIG-045).
- The target's monthly job limit is not readable, and a trial edition shows no jobs row at all: run your own job
  ledger before validation starts (L-IPU-056, L-IPU-043).
- Build the source-to-target id map right after the import, only from objects that import created (L-MIG-036).
- Imported tasks keep their original targets: retarget validation runs to shadow datasets (L-MIG-046).
- Scan every host for consumers, then flip callers by id with a tool that blocks unmapped ids (L-MIG-041,
  L-MIG-042).
- After the soak, send one batched vendor case, and classify every source object before any decommission delete
  (L-MIG-074, L-MIG-073).

**Related:** [Export & Import](01-export-import-v3-migration-api.md) · [Cutover & Rollback](05-cutover-rollback.md) · [Headless Deletes & Org Cleanup](06-headless-deletes-org-cleanup.md) · [CDC from PostgreSQL](../06-cdc-ingestion/02-cdc-from-postgresql.md) · [Lessons: Migration & Org Management](lessons.md)

**Last verified:** 2026-11-03

> This runbook moves a working IDMC estate (mapping tasks, taskflows, CAI processes, DBMI CDC, DQ profiles, catalog
> content and every external caller) from one org to another without the UI, with a cutover of about 20 minutes and a
> rollback for every step. It is the generic form of a migration executed end to end in about 10.5 hours: inventory →
> dependency closure → export → edit → import (REUSE by name) → connections and secrets → agent and runtime
> environment → schedules → CDC → CAI → CDGC → caller repoint → validation → cutover → cleanup.

---

## 1. Roles: one lead, lanes, one writer per org (L-MIG-044)

| Role | Owns | Logs in to IDMC? | Delivers |
|---|---|---|---|
| **Lead** | the plan, every import and publish, the cutover GO steps | **yes: the only session that logs in to either org** | milestone receipts, the cutover report |
| Host lane | agent install and systemd unit, drivers, disk and RAM, replication slots, host guards | no | host receipts; staged scripts (dry run by default, each step printing its undo) |
| Repoint lane | caller scan, flip tool, id files, smoke tests | no until GO (read-only planning) | flip plan, backups, smoke results |
| Catalog lane | CDGC sources, scans, glossary, links, CLAIRE retest | via the lead's session policy | catalog receipts |
| QA / docs lane | package cross-check, checklists, id-map audits | no (reads local files) | cross-check report, delete checklist |
| Cleanup lane | target-org cleanup (M13) | only after the lead's OK, never during an import | backups and delete log |

Coordination rules:

- Each lane claims its child task with a **lease** (owner, since, expires), posts heartbeats on long work and a DONE with evidence, and releases explicitly.
- The lead announces every import, publish and cutover step on the epic before doing it.
- Several sessions often receive the same request, so check first and split by component.
- **Logins:** failed logins from several sessions add up. About 6 rejected logins from 3 sessions locked a target account, and each retry restarted the lock. A password reset unlocks it. After that, one designated session made exactly one attempt with credentials confirmed in a browser, cached the session, and every script reused it. Build a lockout guard into every helper (see [Access, Auth & Orgs](../01-login-and-orgs)).
- The shared migration library makes the **source read-only**: any non-GET call to the source raises unless an explicit override is set, and export POSTs are allowed (L-MIG-043).

## 2. The phases at a glance (L-MIG-045)

| Phase | Goal | Key actions | Evidence to post | Undo |
|---|---|---|---|---|
| **M0** access and identity | know both orgs exactly | one v3 login per org; record org name, both id shapes, `baseApiUrl`, licenses, agents, job limit | org summary (ids, pod, domain) | none (read-only) |
| **M1** inventory, closure, export | a complete, self-consistent package | page objects; v2 detail snapshots; references closure; tag-scope cross-check; export with dependencies; manifest | object counts by type; 0 missing references | none (read-only) |
| **M2** target foundation | a target agent that can run everything | install and register an agent; select only the needed services and connectors; stage drivers | agent RUNNING; engines listed | stop and remove the unit |
| **M3** connections and secrets | every connection green | set secrets from files; test each on the target agent | N/N connection tests 200 | restore the connection bodies |
| **M4** import | all design objects in the target | test import; REUSE; package fixes; re-tag; id map | import SUCCESSFUL; created and reused counts; tag read-back | delete the imported objects (M13 routes) |
| **M5** CAI | processes live in the target | publish in dependency order; side-effect-free checks; one real upsert | N/N published; check calls ok | unpublish |
| **M6** DBMI CDC | a target CDC task ready | drivers and key; create or import; deploy; **not started** | task `deployed` | undeploy and delete |
| **M7** DQ | profiles and rules working | re-bind rule specs (target frsIds); run the profiles | N/N profile jobs COMPLETED | restore the profile bodies |
| **M8** CDGC | catalog and glossary rebuilt | recreate sources (same names); scan one at a time; glossary, links, classifications | scan states; term and link counts | delete the created sources and terms |
| **M9** caller repoint (prepared) | every caller ready to flip | host scan; id map; flip tool `plan` dry runs | plan with 0 unmapped ids | nothing applied yet |
| **M10** validation | proof the target produces the same data | one announced run per lane; parity; smoke; end-to-end stories | parity tables; timings | none (validation only) |
| **M11** cutover | the target is live | snapshot, unbind source, flip callers, switch CDC, bind target, verify | receipts with times | the per-step rollback ([Cutover & Rollback](05-cutover-rollback.md)) |
| **M12** soak and rotations | stable, and no exposed secret still valid | watch runs; rotate credentials at every touchpoint | runs green; rotation receipts | n/a |
| **M13** target cleanup | only the new platform left in the target | keep list, backups, deletes in dependency order | delete log with read-backs | re-import the backups |

## 3. Phase details

### M0: Access and identity

- Log in once per org at the org's **own domain** host (a login at the wrong domain answers `IDS_085`, which looks like a bad password). Take the pod base from `products[].baseApiUrl`; derive the CAI host as `https://<pod>-cai.<rest of the host>`.
- Record: org name, `<orgIdV2>` (6 characters) and `<orgIdV3>` (22 characters), `baseApiUrl`, the license list, agents and runtime environments. v3 license lookups need the 22-character id (the 6-character one gives `V3API_016`).
- **The monthly job limit is not readable over the API.** The licence limits all read `-1`, and the cap was hit in one org without any API trace. A trial-edition target shows no jobs row on its Licenses page and only serverless compute-unit-hour meters on its Metering page; its edition name is readable from `OrgLicenseAssignment('<orgIdV3>')/Views` (L-IPU-056). Assume the cap of a comparable org (10,000 jobs a month seen) until Informatica confirms, start a job ledger with soft and hard thresholds before M10, and keep a quota breaker in anything that starts jobs (see [Entitlement, Licenses & Job Caps](../13-ipu-cost/03-entitlement-licenses-job-caps.md) § 7).
- A target that already holds content (legacy objects, bundles, agents) needs a **dedicated project**; never overwrite unrelated objects, and resolve everything by id afterwards (L-MIG-037).

### M1: Inventory, dependency closure, export

1. **Inventory** (L-MIG-035): page `GET /public/core/v3/objects?limit=200&skip=<n>` to `count`; filter client-side (the `q` filter is not validated). Linear taskflows are type `WORKFLOW`, not `TASKFLOW`, so query both (L-MIG-072). Snapshot the v2 lists (`connection`, `runtimeEnvironment`, `agent`, `schedule`, `mttask`, `workflow`, `mapping`) **and every task and workflow detail**, because the lists hide `scheduleId` and `frsGuid`.
2. **Scope**: by tag, path or description marker. Then **cross-check** against the folder contents and the references graph: untagged objects (for example an MCP server and its tool connection) are easy to miss (L-MIG-033).
3. **Closure** (L-MIG-034): `GET /public/core/v3/objects/<id>/references?refType=uses&limit=50&skip=<n>` (and `usedBy`) for every scoped object; `limit=200` or a missing `refType` answers 400 (L-MIG-072). Whatever lies outside the scope (runtime environments, connections, bundle templates, bundle rule specs) is a dependency, not scope creep.
4. **Export** with `includeDependencies:true` (L-MIG-003). Measured: 194 scoped objects gave 223 objects in about 20 s.
5. **Archive** the package privately (it can hold plaintext secrets; L-MIG-018), with a manifest: counts per type, the connection list with type and host, and the excluded probes.
6. Write down what the package does **not** carry (L-MIG-017); each item becomes a later phase.

### M2: Target foundation (agent, runtime environment, services, drivers)

See [Secure Agent & Connections](../02-secure-agent) for the full agent procedure. Migration-specific points:

- A second agent on an existing host needs its own OS user and home, and its own systemd unit (`Type=forking`, `RemainAfterExit`, `KillMode=control-group`, no `Restart=`, an `ExecStartPre` guard that refuses to start while a manual instance runs, and `MemoryHigh`/`MemoryMax` plus CPU and IO weights so it cannot starve the first agent). An agent started through a cloud run-command lives in a transient cgroup and dies on reboot.
- Get the install token from `GET /api/v2/agent/installerInfo/linux64`, start the agent **before** `consoleAgentManager.sh configureToken <user> <token>`, and let it create its runtime environment.
- Select only the services and connectors the scope needs, through `GET/PUT https://<pod>.<domain>.informaticacloud.com/runtime/api/v2/runtimeEnvironment/<reId>/selections/ui` with `IDS-SESSION-ID`. Selecting all services once pulled 18 GB of packages in 8 minutes and drove a 4-vCPU host to a load of 189. Every PUT can also roll engines to newer versions (a lane may queue for about 5 minutes).
- Keep the on-agent process engine off on a second agent that shares a host (port clashes).
- Stage the DBMI Simba set and any JDBC V2 driver jars, then restart the agent (see [DBMI Targets & Drivers](../06-cdc-ingestion/03-dbmi-targets-drivers.md)).

### M3: Connections and secrets

- Imported connections carry **no passwords**. For each one: `GET /api/v2/connection/<connId>`, set the secret fields from host files at run time (never printed), `POST` the full body back, and `GET /api/v2/connection/test/<connId>` (a test costs no IPU).
- Flat-file connections need a directory the new agent's OS user can read (a shared, group-writable directory with the files copied in).
- Key formats can differ by pod **and** engine: give DBMI its own BigQuery connection (L-DBMI-034).

### M4: Import

1. Test-import a small set first (for example the bundle template plus one task).
2. Import the whole package with `REUSE` (L-MIG-011). Fix the package as needed (see [Editing Packages Safely](02-editing-packages-safely.md)):
   - remap objects bound to the reserved hosted runtime (`REPO_38210`; L-MIG-015);
   - drop objects that fail validation, because the import is all-or-nothing (L-MIG-012);
   - `MigrationSvc_056` means a dependency is missing (L-MIG-014);
   - re-point connections, runtime environments and org ids in every file, nested zips included, then compare each
     target connection's host and database with the intended values (L-MIG-082).
   On a poll timeout, read the job back (`idmc_export_import.py status <jobId> --kind import`); never start a second
   import (L-MIG-132).
3. Re-tag with `TagObjects` and read back (L-MIG-016).
4. **Build the id map at once** (L-MIG-036): source and target v3 ids, source v2 id (`repoInfo.repoHandle`), target v2 id found by name **only among the objects this import created**.
5. Compare every reused pair whose source changed recently; the reused copy may be older.
6. Recreate tool connections in the designer (L-MIG-039).

Measured: the import went SUCCESSFUL after several failed attempts, with 214 objects (180 created, 34 reused) in about 3.5 minutes. The earlier attempts failed with `MigrationSvc_056` and `MigrationSvc_031` (unmet dependencies, the reserved runtime, 5 UNLOAD tasks failing vendor validation).

### M5: CAI

- Publish in dependency order: service connector, then app connection, then processes (see [Application Integration (CAI)](../07-app-integration)). Verify with side-effect-free calls against the **target** runtime base, then one real call whose result you read back from the downstream system (this proves the migrated connection and its secret).
- Callers switch in a **separate** step (L-MIG-040): CAI URLs embed the pod and the org id, so set each caller's base-URL environment variable to the target and recreate only those services (a 10–30 s blip). The target needs its `CAI_Anonymous_<orgIdV3>` user.

### M6: DBMI CDC

- Install the drivers, create a DBMI-only BigQuery connection, then create the task (clone the source task's body through `task/details`, or import it and fix the slot and publication names) and **deploy it without starting it** (L-DBMI-015, L-DBMI-021).
- Decide the slot strategy: reuse the source's slot at cutover, or create a new slot right before the switch (see [CDC from PostgreSQL](../06-cdc-ingestion/02-cdc-from-postgresql.md)). Do not create a new slot days early.

### M7: Data quality

Re-bind the rule specifications (by the **target** frsIds) to the profile columns; imported profiles arrive with 0 rule occurrences. Run each profile once (8 of 8 completed). See [Data Quality & Profiling](../08-data-quality).

### M8: Catalog and glossary

CDGC content does not travel in the package. Recreate the catalog sources under the same names (multipart part `dataSource`, remapped ids), enable the agent's metadata services only for the scan window, and scan **one source at a time**. Rebuild the glossary, the term links, the classifications and the curated descriptions from a read-only export of the source. Purge legacy duplicates, then retest CLAIRE after the index settles (lineage and NL-to-SQL questions still failed about 30 minutes after the scans, probably index lag). See [Catalog & Governance (CDGC)](../09-catalog-lineage).

### M9: Caller repoint, prepared

1. **Scan the hosts** for every consumer of the source org (L-MIG-041): hosts, both org-id shapes, v2 ids (they start with the source `<orgIdV2>`), v3 22-character ids, credential files, helper imports, id files, CAI URLs, cron tables, systemd units and env files.
2. **Build the flip tool** (L-MIG-042) with `status | plan | apply --group <g> --execute | rollback --backup <ts> --execute`. It remaps by id from the id map (never by name), blocks unmapped ids, swaps host literals most specific first, backs up every file, writes in place, and pauses crons whose target side is not ready.
3. Run `plan` until it shows **0 unmapped ids**. Dry runs caught 3 unmapped schedule ids before the GO.
4. Make the shared helper **org-aware**: a switch file or env variable selects the org, each org has its own creds file, session cache and login host, and a single job can be pinned to the old org.

### M10: Validation (L-MIG-046)

Run each lane once in the target, announced, with the matching source schedule paused for that window, then compare (section 4). **Imported tasks keep their original targets**: a validation run can write production tables unless you retarget it to shadow datasets first.

Budget validation and story rounds in jobs: group writes into waves (one lane run per burst), read the job ledger before and after each wave, and set a cap and a hard stop per round (L-IPU-058; [Entitlement, Licenses & Job Caps](../13-ipu-cost/03-entitlement-licenses-job-caps.md) § 7.3).

### M11 to M13

- **M11 cutover:** [Cutover & Rollback](05-cutover-rollback.md).
- **M12 soak and rotations:** watch the first scheduled runs; rotate every credential that was exposed (a password shared in chat, secrets carried in packages) at every touchpoint, including catalog scanners and MCP OAuth clients that store a user's password (L-MIG-050). Then send one batched vendor case with only what the vendor alone can fix (the real job limit, unlicensed looping services, stuck CAI runtime rows, product defects with a repro, the engine diff), each item re-verified the day you send (L-MIG-074; [Cutover & Rollback](05-cutover-rollback.md) § 7).
- **M13 target cleanup:** [Headless Deletes & Org Cleanup](06-headless-deletes-org-cleanup.md).
- **Source decommission (only when the owner approves):** the source org stays as it is unless the owner names deletions (L-MIG-051). Before any delete there, give every source object one verdict (READY, HOLD-VERIFY, NO-TWIN, PROBE, DEP-LAST, SHARED) from the id map and the import log (L-MIG-073; [Headless Deletes & Org Cleanup](06-headless-deletes-org-cleanup.md) § 12).

## 4. Validation metrics

| Metric | How | Pass bar | Observed |
|---|---|---|---|
| landing row parity | per table: the run's applied rows vs the warehouse `COUNT(*)` vs the source count as of the task's read time | exact | 14/14 exact |
| mart parity | each mart vs the pre-cutover baseline; explain every delta (rows that arrived mid-run, append-only tables, time series) | identical or explained | 25/30 identical + 5 explained |
| other lanes | the same per lane | exact | exact on each |
| full taskflow run | tasks OK and duration | all OK; duration recorded as the new baseline | 62/62 in 21.6 min (source 24.5 min) |
| CAI | side-effect-free checks plus one real call | all ok | all ok; 343 ms |
| CDC | one consumer; source audit max = warehouse max | within seconds | 0 errors; equal |
| DQ | profile jobs | all COMPLETED | 8/8 |
| smoke suite | host smoke checks | all pass | 7/7 |
| end-to-end stories | the application's own story suite | all pass, or each failure classified | 8/9 (the one failure was an unrelated app change) |
| first scheduled runs after cutover | every bound schedule fires once | all run | all ran |
| per-dataset reconcile (a table migration proven inside IDMC) | legacy stats per dataset (rows, distinct units, an order-free checksum = sum(hash(unit key)) mod 2^64, last modification time) staged as a flat file; the target-side SQL from a run parameter file; one mapping joins them (master outer) and writes one status row per dataset per run: reconciled / mismatch / mismatch_source_changed / missing_target (L-MIG-086) | every dataset reconciled, or each mismatch explained | 116 datasets: 108 reconciled, 5 changed at the source, 3 real mismatches to inspect |

## 5. Measured numbers from the executed run

| Step | Number |
|---|---|
| export | 194 scoped → 223 objects, 616 KB, about 20 s |
| import | 214 objects (180 created, 34 reused), about 3.5 min, after several failed attempts |
| re-tag | 189 objects |
| CAI publish | 9/9 |
| connections | 8/8 green |
| full lane | 62 tasks, 21.6 min |
| cutover | 21 minutes (unbind to the CDC switch complete) |
| CDC gap | about 70 s to the first target write; about 5 min lost in an earlier failed attempt |
| whole migration | about 10.5 hours, request to final status |
| after cutover (a dependency DAG instead of the linear taskflow) | the same 62 tasks planned at about 5.5 minutes at concurrency 4 (L-MIG-056) |

## 6. Pre-migration gates (L-MIG-052)

- Host capacity: free RAM after the existing agent, swap, about 25 GB free for a second agent's roughly 20 GB of engines, a listener baseline (`ss -ltnp`), free replication slots, `wal_level=logical`.
- The target's job limit and entitlements.
- The target org is on the same or a newer IDMC release than the source, and each export or import job stays within
  1,000 objects (vendor docs; L-MIG-129).
- Tasks built on Add-On Bundle templates do not migrate as exported: remove the template entries and rebuild those
  tasks as user mappings before the first import (L-MIG-083).
- Probe each plane against a fake-path twin (a 404 on the fake path versus a typed answer on the real one tells you the plane is routed).
- Probe the import route: an empty multipart should give 400 `MigrationSvc_030`.
- A stateful cutover script that stops at each manual step, saves its state, and resumes only with an explicit confirm token.

## 7. Related migrations

- **Promotion inside one org (dev → prod)** (L-MIG-031): plan (read-only), validate without running, gated execute; re-point only the intended delta (usually the warehouse connection); org-scoped objects are shared by construction.
- **Splitting production into its own org** (L-MIG-032): the trigger is real customer data at volume, a compliance need or separate billing; the method is this runbook.
- **Legacy pipeline → IDMC** (L-MIG-053): snapshot the tables with an expiry, point the scheduler at IDMC, stop the legacy service with a no-restart policy, and roll back by starting it again.
- **Catalog or governance consumer cutover** (L-MIG-057, L-MIG-058): crosswalk assets by column-set similarity; repoint readers only after sustained parity.
- Before renaming or retiring a dataset, check which IDMC jobs write it (L-MIG-059).
- **Table and warehouse migrations through IDMC** (L-MIG-086 to L-MIG-094): audit any earlier automated build before
  extending it; read a live source through a dedicated reader login; prove completeness with per-dataset counts and an
  order-free checksum on both sides, over an inventory of every source store, not only the warehouse; do not add target constraints mid-load; check for
  rows hidden by a lightweight DELETE before calling them missing; project only the columns needed instead of one wide
  table; and consolidate warehouse databases with atomic renames rather than copies.

## 8. Overturned beliefs

| Earlier belief (dates) | What overturned it | Lessons |
|---|---|---|
| "No cross-org export/import; promotion only re-points within one org" (2026-07-04) | this runbook, executed (2026-09-28) | L-MIG-069 → L-MIG-045 |
| "Design objects must be authored in the UI" (2026-07; again 2026-09-20/21) | migration-clone and import | L-MIG-061 → L-MIG-023 |
| a draft runbook (2026-09-28) marked service enablement, DBMI deploy, the MCP OAuth client and schedule binding as UI-only or untested | all were done headless in the executed run the same day | see the domain folders; L-DBMI-047 → L-DBMI-003 |

## 9. Lessons in this doc

L-MIG-003, L-MIG-011 to L-MIG-018, L-MIG-031 to L-MIG-046, L-MIG-050 to L-MIG-053, L-MIG-056 to L-MIG-059, L-MIG-072, L-MIG-082, L-MIG-083, L-MIG-129, L-MIG-132, L-DBMI-015, L-DBMI-021, L-DBMI-034, and the superseded L-MIG-061 and L-MIG-069. Full text: [Lessons: Migration & Org Management](lessons.md).
