# End-to-End Playbook: deploy and operate IDMC with Claude

**Answers:** In what order does a team and its Claude sessions take IDMC from an empty org to running, governed
pipelines, and then operate them: the org and its users, a Secure Agent on a cloud VM, connections, CDC, generated CDI
mappings, data quality, catalog and CLAIRE, the split between IDMC and an API layer, serving outputs to BI and apps,
budgets and latency, a move to another org, and day-2 operations? Which doc holds the detail of each step, and what
proves that a stage is done?

**Read when:** before you plan or estimate a new IDMC deployment or a large extension; when you join a running
deployment and need the map; before you promise a go-live date or a latency.

**Key rules:**
- Prove the org and set up one guarded session before any other step (stage 0; L-AUTH-046, L-AUTH-041, L-METHOD-002).
- Size the agent host for the services you will select, and run the agent under systemd (stage 2; L-AGENT-052,
  L-AGENT-009).
- Pick the mechanism by freshness: CDC for seconds, event-driven CDI lanes for minutes, CAI for per-event calls; batch
  CDI cannot deliver seconds end to end (stages 5-9; L-CDI-126, L-CDI-206).
- Generate few, consolidated mappings, and change live pipelines only behind a swap gate (stage 6; L-CDI-119,
  L-CDI-142).
- Keep your own job ledger and a quota breaker from the first lane: the monthly job cap is invisible (stage 11;
  L-IPU-041, L-IPU-043).
- Every stage ends on a read-back gate, never on a 200 (L-METHOD-030).

**Related:** [How to use this KB](01-how-to-use-this-kb.md) · [The Laws of Headless IDMC](02-the-laws-of-headless-idmc.md) ·
[Capability Map](03-capability-map.md) · [Error Triage](04-error-triage.md) ·
[How Claude Reaches and Drives IDMC](../14-working-with-claude/01-how-claude-reaches-and-drives-idmc.md)

**Last verified:** 2026-11-03 (evidence 2026-06-27 to 2026-11-03).

> Fourteen stages in order, then day-2 operations and the Claude working rules that apply throughout. Each stage gives
> its goal, the steps in one line each with the doc that holds the calls and bodies, a **Done when** gate and the traps
> that cost the most. Payloads live in the linked docs; this page holds the order, the decisions and the gates.
>
> **Your stack, not ours.** The worked example below happens to use a PostgreSQL operational database, a BigQuery
> warehouse, a Salesforce CRM and a BI tool, with the Secure Agent on a cloud VM, because that is where the evidence
> came from. It is an example, not a recommendation. The stages, their order and their gates are the same for any
> source, warehouse, lake, file store, SaaS app or BI tool. Where a step names a system, read it as "for example", and
> do the matching step for yours (the connector's own settings, proven with one small run). For a single new pipeline,
> the short version of this page is [New Pipeline Milestones](08-new-pipeline-milestones-any-source-any-target.md).

---

## Stage map

| Stage | Outcome | Main doc |
|---|---|---|
| 0 | A guarded, org-aware session; the org proven | [Identify the Org Before You Write](../01-login-and-orgs/03-identify-the-org-before-you-write.md) |
| 1 | An automation user, personas and role bindings; entitlement known | [Users, Roles & Permissions](../01-login-and-orgs/04-users-roles-permissions.md) |
| 2 | A Secure Agent on a sized cloud VM, supervised, reachable | [Secure Agent - Install, Run & Tune](../02-secure-agent/01-secure-agent-install-run-tune.md) |
| 3 | Only the services and connectors the scope needs, RUNNING | [Runtime Environments](../02-secure-agent/02-runtime-environments-services-connectors.md) |
| 4 | Connections to the warehouse, the databases and the SaaS apps, proven by rows | [Connections](../03-connections/01-connections-create-test-update-delete.md) |
| 5 | Sources landed in the warehouse by CDC | [CDC from PostgreSQL](../06-cdc-ingestion/02-cdc-from-postgresql.md) |
| 6 | Curated and golden layers built by generated, consolidated mappings | [How Claude Builds Mappings Headless](../04-mappings/02-how-claude-builds-mappings-headless.md) |
| 7 | Lanes that run on events and schedules, staged and budgeted | [Performance, Concurrency & Job Caps](../04-mappings/06-performance-concurrency-job-caps.md) |
| 8 | Data quality rules running inside the pipeline, scored | [DQ Assets](../08-data-quality/01-dq-assets-rule-specs-cleanse-dictionaries-verifiers.md) |
| 9 | A catalog with lineage and glossary, and CLAIRE answering | [Catalog Sources](../09-catalog-lineage/02-catalog-sources-create-scan-update-purge.md) |
| 10 | Every integration edge owned by the right layer; the real-time CAI leg | [CAI Runtime](../07-app-integration/02-cai-runtime-invoke-urls-control.md) §10 |
| 11 | Outputs served to BI tools, CRM analytics and apps | [Serving Outputs to BI and Apps](../04-mappings/09-serving-outputs-to-bi-and-apps-freshness-latency-reverse-etl.md) |
| 12 | Job budget, IPU and latency measured and guarded | [Entitlement, Licenses & Job Caps](../13-ipu-cost/03-entitlement-licenses-job-caps.md) |
| 13 | The estate moved to another org, the old one decommissioned (when needed) | [Org-to-Org Migration Runbook](../12-deploy-migrate/04-org-to-org-migration-runbook.md) |
| Day 2 | Monitored, resized, upgraded, cleaned and re-verified safely | this page, "Day-2 operations" |

---

## Stage 0. Prepare the session and prove the org

Goal: one session module through which every call passes, and a proven org.

1. Credentials in the environment or a 0600 file outside any repository; one native IDMC user for automation (SSO-only
   users have no password for REST) (L-METHOD-001, L-AUTH-045).
2. One org-aware session module for every call: the [Script Library](../../toolkit/lib/README.md)'s
   `idmc_session.py`, or your own built the same way (file lock, cache with grant time, refresh at ~25 minutes, one
   re-login on a 401, a block file per org on any rejected login) (L-METHOD-002, L-AUTH-030, L-AUTH-041).
3. The three-call preflight: v3 login at the domain host, `GET /api/v2/org`, `GET /api/v2/agent`; record org name, both
   id shapes, pod, domain label and base URL in your run notes (L-AUTH-046;
   [Identify the Org](../01-login-and-orgs/03-identify-the-org-before-you-write.md) §1).
4. Map the KB's placeholders to your values ([How to use this KB](01-how-to-use-this-kb.md) §4).
5. Agree the Claude working rules for the program: one writer per org, the approval list, how sessions coordinate
   (Working with Claude, at the end of this page).

**Done when:** `idmc_session.py whoami --expect-org <orgIdV3>` prints the receipt line, and a mocked rejected login
writes the block file and stops further attempts (L-AUTH-041).

**Traps:** the domain label cannot be guessed (`dm-us` versus `dmp-us`; the wrong one answers `IDS_085`, which looks
like a bad password) (L-AUTH-004); per-agent logins add lockout risk (L-AUTH-031).

## Stage 1. Org, users, roles and entitlement

1. Create the automation user and persona users with `POST /public/core/v3/users` (key `name`, `groups` as plain id
   strings) after a snapshot of the current users (L-AUTH-057, L-AUTH-059).
2. Bind roles through groups (`roles` as plain role-id strings) and read them back (L-AUTH-060). The automation login
   needs Admin, Designer, Governance Administrator, CLAIRE GPT User, the migration role and the MCP privileges
   (L-AUTH-063; [Users, Roles & Permissions](../01-login-and-orgs/04-users-roles-permissions.md) §3).
3. Establish what the org may run from six reads, never from the login `products[]` list; check whether it is a trial
   edition (L-AUTH-074, L-IPU-056; [Users, Roles & Permissions](../01-login-and-orgs/04-users-roles-permissions.md) §6).
4. Ask Informatica for the monthly job limit and its reset day now, because no API shows it (L-IPU-041).

**Done when:** the automation user logs in once, its roles read back, and each product you plan to use shows its
privilege prefix and (after stage 3) its engine.

## Stage 2. A Secure Agent on a cloud VM

**Choose the runtime environment kind** ([Runtime Environments](../02-secure-agent/02-runtime-environments-services-connectors.md) §1):

| Data lives | Use | Why |
|---|---|---|
| SaaS only, and the connector supports hosted execution | Informatica Cloud Hosted Agent | nothing to install; it cannot reach a private network |
| A private network, a VM-hosted database, on premises | a Secure Agent on a VM you own | the only option that reaches private hosts (L-AGENT-036) |
| Already in your own AWS or Azure account, no agent wanted | Serverless (created in the UI) | billed per runtime hour; reaches only that account |

**Size the VM** ([Secure Agent](../02-secure-agent/01-secure-agent-install-run-tune.md) §2, §6):

| Scope | vCPU | RAM | Disk | Evidence |
|---|---|---|---|---|
| Data Integration plus a few connectors | 4 | 16 GB or more | about 20 GB free beyond the install, plus swap | L-AGENT-052 |
| CDI, CDC, DQ and catalog scan windows (10-17 services) | 8 | 32 GB, with a unit memory limit | agent home 25-30 GB; `downloads/` alone about 20 GB and never pruned | L-AGENT-093, L-AGENT-094, L-ENV-069 |
| Two agents on one host (for example during an org move) | 8 | 32 GB, a MemoryHigh per unit | both installs; a stopped one still holds about 46 GB | L-AGENT-015, L-AGENT-018, L-ENV-069 |

Steps:

1. Prove outbound HTTPS from the VM before installing (L-AGENT-003).
2. Mint the install token in the target org (`GET /api/v2/agent/installerInfo/linux64`), install as a non-root user,
   `infaagent startup`, then `consoleAgentManager.sh configureToken` from the agentcore directory (L-AGENT-001,
   L-AGENT-002).
3. Run it under a systemd unit (`Type=forking`, `RemainAfterExit=yes`, `KillMode=control-group`, no `Restart=`), never
   from a cloud run-command; add the orphan reaper and owner-scoped port guards (L-AGENT-009, L-AGENT-011, L-AGENT-013,
   L-AGENT-096).
4. Cap it with `systemctl set-property` and check that the cap is real (every agent process inside the slice, the
   heaps fit) (L-AGENT-017).
5. Install native libraries the engines need on your distribution (`libidn.so.11`, `libxcrypt-compat`) (L-AGENT-059,
   L-AGENT-060).
6. Disks: put Docker's data-root and containerd's store on a data disk if containers share the VM, and make Docker wait
   for that disk (L-ENV-032, L-ENV-071).
7. Reach paths for Claude: SSH where egress is stable; an IAP jump host on GCP, run as a service account with
   `--account` pinned; Azure run-command only for short scripts (it is a per-VM singleton with a 4 KB output tail, and
   anything it starts dies on reboot) (L-ENV-001, L-ENV-003, L-ENV-005, L-ENV-009, L-ENV-008;
   [How Claude Reaches and Drives IDMC](../14-working-with-claude/01-how-claude-reaches-and-drives-idmc.md) §7).

**Done when:** `pgrep -c -f 'agentcore.impls.MainApp'` prints 1 inside the unit's cgroup, `getstatus` is READY,
`GET /api/v2/agent/<agentId>` reads `active: true`, and after one `systemctl restart <unit>` it is READY again.

## Stage 3. Select only the services and connectors you need

1. GET the runtime-environment selections and save the body as the undo; PUT it back with only the `enabled` flags you
   mean to change, header `IDS-SESSION-ID` (L-AGENT-039).
2. Choose by scope ([Runtime Environments](../02-secure-agent/02-runtime-environments-services-connectors.md) §6):
   Data Integration first; Mass Ingestion-Databases for CDC; Data Quality (it brings three storage connectors); the
   catalog Metadata services only for scan windows; Application Integration only when processes must reach private
   hosts, and only one Process Server per host (L-AGENT-040, L-CDGC-045, L-AGENT-090).
3. Every PUT downloads packages and rolls DIS, Mass Ingestion and Connector_Service: change selections between lanes,
   never before a timed run (L-AGENT-041, L-AGENT-042).
4. Set engine properties cloud-side through the `agent.do` form: the DTM heap, and the DTM pool (`maxDTMProcesses`,
   default 2) once you plan to run more than two tasks at once (L-AGENT-088, L-AGENT-099;
   [Secure Agent](../02-secure-agent/01-secure-agent-install-run-tune.md) §6.1-6.2).
5. CLAIRE GPT "Query the data" needs the Data Gateway licence package on the org; it deploys by itself once licensed,
   and needs its agent running (L-AGENT-097, L-AGENT-051).

**Done when:** every needed engine reads RUNNING in `GET /api/v2/agent/details/<agentId>` and one connection test per
engine passes (L-AGENT-023).

## Stage 4. Connections: warehouse, databases, SaaS

1. CCI connections: `POST /api/v2/connection` with `type: "TOOLKIT_CCI"`, the connector's display name in
   `instanceName` and parameters in `connParams`; update by POSTing the full body with the secret re-supplied
   (L-CONN-001, L-CONN-006, L-CONN-007; [Connections](../03-connections/01-connections-create-test-update-delete.md)).
2. Warehouse (for example BigQuery; for yours, take the connector's own auth and settings): one service account or
   credential per consumer with the documented roles; test the private-key form per
   consumer (CDI, Database Ingestion, the Data Gateway) and keep one connection per consumer when they disagree
   (L-CONN-034, L-CONN-035, L-DBMI-034; [Connector Notes](../03-connections/02-connector-notes-bigquery-postgresql-salesforce-jdbc-flat-file.md) §2).
3. Databases (for example PostgreSQL): a dedicated least-privilege user; objects addressed `<schema>/TABLE/<table>`; a same-host
   database through `localhost`, never the VM's public name (L-CONN-012, L-CONN-028, L-ENV-014).
4. SaaS (for example Salesforce): user, password and token at the top level of the v2 connection, API 64 or newer; for real-time
   writes from CAI, an OAuth client-credentials app (L-CONN-058, L-CONN-063).
5. Prove each connection with a run that lands rows, not only with a test; an empty source browse proves nothing
   (L-CONN-015, L-CONN-016).

**Done when:** every connection tests green from the runtime environment of the tasks that will use it, and one small
task per connection lands the expected row count.

## Stage 5. Land the sources with CDC

1. Source prerequisites (PostgreSQL shown; each source database has its own CDC prerequisites in its connector guide): logical WAL, a replication role, a dedicated publication (`FOR TABLE...`), the slot created
   after the publication (L-DBMI-011, L-DBMI-012; [CDC from PostgreSQL](../06-cdc-ingestion/02-cdc-from-postgresql.md) §1).
2. The target needs its own connection and, for some targets, a driver on the agent (a BigQuery target needs the
   Simba driver set) (L-DBMI-033, L-DBMI-034;
   [DBMI Targets & Drivers](../06-cdc-ingestion/03-dbmi-targets-drivers.md)).
3. Create, deploy and start the task over REST on `<pod>-ing` (L-DBMI-003, L-DBMI-004;
   [DBMI over REST](../06-cdc-ingestion/01-dbmi-over-rest-create-deploy-run-stop.md)).
4. Split hot and cold tables into two tasks when one cycle applies tables in turn (L-DBMI-019, L-DBMI-022).
5. Add the watchdog (job state, slot lag, freshness, bounded auto-resume) and never drop a live slot (L-DBMI-016,
   L-DBMI-028).
6. Leave Database Ingestion's own tables (`INFORMATICA_CDC_RECOVERY`, `<table>_EXT`) out of counts, BI and catalog
   scopes (L-ENV-082).

**Done when:** every table's latest transition event is `NORMAL_CONTINUOUS_CDC_TABLE` with no ERROR lines
(L-DBMI-030), and the landing latency is measured per table with `APPENDS` (about 20-30 s was typical)
(L-DBMI-029).

## Stage 6. Build the curated and golden layers: generated mappings

1. Pick the route with the decision guide ([How Claude Builds Mappings Headless](../04-mappings/02-how-claude-builds-mappings-headless.md) §1):
   template mapping tasks for straight copies; the IMF generator (route 5) for real transformations, which lineage and
   CLAIRE can see (L-CDI-033).
2. Generate few mappings: one ingest per source group, one golden-record mapping with many targets, key-sync or
   insert/update writers; the consolidation that cut a 62-task lane to 23 jobs (L-CDI-119;
   [Mapping Design & Consolidation](../04-mappings/05-mapping-design-consolidation.md)).
3. Apply your target connector's writer settings (for example the job poll interval on a BigQuery target, L-CDI-200;
   the per-connector table is in the [Mapping Fast Path](../04-mappings/00-mapping-fast-path-read-this-first.md) §2).
4. Read the CDC replicas already in the warehouse instead of re-reading the source database in every lane: it removes
   jobs from the critical path (L-CDI-203).
5. Full SQL ELT (pushdown) is a task setting; keep it only if parity holds and a measured speed gate passes, because it
   writes targets one after another (L-CDI-202, L-CDI-203).
6. Watch the target-side traps: the 255-character STRING cut, ignored `truncateTarget`, a `Pre SQL` truncate before a
   failed read, generated PostgreSQL upserts that insert nothing (L-CONN-044, L-CONN-032, L-CDI-208,
   L-CDI-207; [Source & Target Gotchas](../04-mappings/08-source-target-gotchas.md)).
7. Change anything live side by side, behind the swap gate, and count parity only from successful runs that rewrote
   the target (L-CDI-141, L-CDI-142;
   [Changing Pipelines Safely](../04-mappings/07-changing-pipelines-safely.md)).

**Done when:** each mapping has a session log as run evidence, a two-way `EXCEPT DISTINCT` parity of 0 against the
reference, and an idempotent second run.

## Stage 7. Orchestrate: lanes, concurrency, retries, speed modes

1. Group tasks into lanes (full, per-record, events, files) and run them with a staged executor on their dependency
   DAG; every task pays about 20 s of fixed cost, so fewer tasks beat bigger machines (L-CDI-121, L-CDI-125;
   [Performance, Concurrency & Job Caps](../04-mappings/06-performance-concurrency-job-caps.md)).
2. Match concurrency to the host and to the DTM pool you set in stage 3 (L-AGENT-019, L-AGENT-099).
3. Let the critical event lane run as a guest beside a long full lane, with per-table conflict checks instead of one
   global lock (L-CDI-128).
4. Retry a failed task once, only on a transient signature (a warehouse 503, a staging upload error, a `Temp_View`
   collision, a spurious "does not exist"), never on the job-cap error (L-CDI-205).
5. Put one speed switch on the controller (economy by default, a timed fast mode that reverts by itself); the hard job
   cap wins in every mode, and CDC and CAI are the same in both (L-IPU-054).

**Done when:** each lane has run green several times in a row, the DTM queue wait p90 is under about 10 s, and the
retry log shows the first error and the second outcome of every retried task.

## Stage 8. Data quality inside the pipeline

1. Data Quality authors and measures; a CDI mapping on a Secure Agent executes the rules (L-DQ-001;
   [DQ Assets](../08-data-quality/01-dq-assets-rule-specs-cleanse-dictionaries-verifiers.md)).
2. Put the same cleanse rule in every writer of a field (the golden mapping, the real-time CAI path, the CRM sync), or
   passes flip values back and forth (L-CAI-086).
3. Profile headless, and stage a sample table when the connector profiles All Rows only (L-DQ-019,
   L-DQ-102; [Profiling - What Is Headless](../08-data-quality/02-profiling-what-is-headless.md)).
4. Score: a warehouse scorecard written by CDI, a Data Profiling scorecard or the catalog DQ score
   ([DQ Scorecards](../08-data-quality/04-dq-scorecards-warehouse-pattern-and-data-profiling-scorecards.md)); make
   format rules test the stored string (L-DQ-105).
5. Address verification through the managed MCP tool, fed from the pre-merge layer and seeded with real public
   addresses in tests (L-DQ-016).

**Done when:** the rules run inside the lanes, their results land in a scored table, and the score matches a direct
query of the stored values.

## Stage 9. Catalog, lineage, glossary and CLAIRE

1. Create catalog sources over REST (multipart `dataSource`), scan one source at a time with the Metadata services
   switched on only for the window (L-CDGC-014, L-CDGC-045;
   [Catalog Sources](../09-catalog-lineage/02-catalog-sources-create-scan-update-purge.md)).
2. On a host with two agents, make `/tmp/poifiles` shared before the first scan (L-CDGC-150).
3. CDI lineage needs an IICS catalog source, the physical sources and connection assignments; where the scan's
   auto-accept left a reference unresolved (seen in a new org), stitch it headless with
   `connectionAssignment?operationType=MERGE` and prove it by reading a target table's lineage (L-CDGC-159, L-CDGC-140;
   [Search, Lineage & Marketplace](../09-catalog-lineage/04-search-lineage-marketplace.md) §9.1).
4. Write glossary domains, terms and links through the content API
   ([Glossary, Links & Classification](../09-catalog-lineage/03-glossary-links-classification.md)).
5. Catalog Data Quality scores need rule occurrences (created over REST, or by CLAIRE recommend-and-accept: L-CDGC-161,
   L-MCP-086) and a runtime environment in the source's capabilities; clone sources with DQ automation off unless you
   want IDMC-side schedules (L-CDGC-143, L-CDGC-152).
6. Test the CLAIRE GPT prompts you will rely on, after the index has caught up with the last scan (L-MCP-062, L-MCP-091;
   [CLAIRE GPT - Prompting Rules & Patterns](../11-mcp-claire/03-claire-gpt-prompting-rules-patterns.md));
   enumerate the org's managed MCP registry before planning MCP work (L-MCP-001), and use `/informatica-idmc-headless:connect-mcp` to
   offer its tools to Claude Code (read-only by default).

**Done when:** scans complete (a PARTIAL_COMPLETED counts only after the agent-side scanner log shows a benign cause, such as unreadable warehouse tags, L-CDGC-168), lineage resolves from source to golden table, and the agreed
CLAIRE prompt set passes in fresh conversations.

## Stage 10. The integration-layer split and the real-time CAI leg

1. Decide each edge's owner and record it: the API layer runs the application's real-time calls; IDMC owns everything
   that feeds or serves analytics; BI never goes through the API layer (L-CAI-088;
   [CAI Runtime](../07-app-integration/02-cai-runtime-invoke-urls-control.md) §10.7, and the
   [Capability Map](03-capability-map.md) row).
2. Call CAI from the application inline, fail-open with a short timeout; retry only the background push that creates a
   parent record (L-CAI-082).
3. Do not leave anonymous process URLs in the application's path: they answer unauthenticated calls and are guessable;
   require authentication or front them with a gateway (L-CAI-038;
   [CAI Runtime](../07-app-integration/02-cai-runtime-invoke-urls-control.md) §10.8).
4. CAI invocations are not jobs, so moving work into or out of CAI saves no jobs (L-CAI-038).

**Done when:** every edge in the architecture inventory has one owner, the real-time leg is measured (about 0.2-2 s to a
SaaS record) (L-CAI-084), and an outage of CAI does not block a user action.

## Stage 11. Serve outputs to BI tools, CRM analytics and apps

1. Serve from views over the CDC landing tables and the batch-built tables, and find which layer each tile reads
   (L-ENV-065; [Serving Outputs to BI and Apps](../04-mappings/09-serving-outputs-to-bi-and-apps-freshness-latency-reverse-etl.md) §1).
2. Never let every dashboard depend on one person's warehouse OAuth credential: refill extracts with a service account
   and republish them without credentials (L-ENV-064, L-ENV-081).
3. Trigger refreshes from table metadata, not row scans, and build a freshness map before any pause
   (L-ENV-082, L-ENV-079).
4. Reverse ETL into a CRM: size the window to the target's storage, purge, empty the recycle bin and probe headroom
   daily; write golden values back to every copy the apps display, the identity provider included (L-CONN-088,
   L-CONN-088, L-MDM-074).
5. Erasure is a fan-out: CDC replicates the delete, but change history, SaaS copies and logins keep the person
   (L-DBMI-051).

**Done when:** change-to-visible is measured per dashboard, the dashboards keep working with the personal credential
revoked, and the CRM headroom probe passes.

## Stage 12. Job budget, IPU and latency

1. Keep your own job ledger from the activity log (task rows plus taskflow children), with soft (~85%) and hard (~95%)
   thresholds, and a quota breaker in anything that starts jobs (L-IPU-043, L-CDI-132,
   L-IPU-024).
2. When the reset day is unknown, guard on the worst of four windows and fail closed; add profile runs and catalog jobs,
   which the activity log misses (L-IPU-055, L-IPU-059).
3. Budget test rounds in write waves, not stories (L-IPU-058).
4. Size IPUs from business drivers, with steady state plus a peak band (L-IPU-008;
   [IPU Model](../13-ipu-cost/01-ipu-model-mechanics.md)); read consumption with the metering
   export in windows of at most 30 days (L-IPU-021).
5. Measure latency per hop with warehouse time travel at each publish, and publish numbers only from a read-only,
   success-only collector (L-CDI-206, L-METHOD-049;
   [Performance, Concurrency & Job Caps](../04-mappings/06-performance-concurrency-job-caps.md) §8).

**Freshness by mechanism** (measured on one stack; re-measure on yours):

| Mechanism | Typical source-to-visible | Use it for |
|---|---|---|
| CDC landing, and views over it | about 20-30 s | per-record visibility, operational dashboards (L-DBMI-029) |
| CAI real-time call | about 0.1-2 s | per-event decisions and SaaS writes (L-CAI-084) |
| An event-driven CDI lane | about 1-2.5 min (median 67 s to a golden record) | governed records, golden tables (L-CDI-206) |
| Full CDI lane | minutes to hours | marts, rebuilds |

**Done when:** the ledger matches the activity log, the breaker has been tested once, and the latency collector
publishes at least three hops.

## Stage 13. Move to another org (when needed)

1. Plan with the milestones M0 to M13, one lead and one writer per org (L-MIG-044, L-MIG-045;
   [Org-to-Org Migration Runbook](../12-deploy-migrate/04-org-to-org-migration-runbook.md)).
2. Export and import over the v3 migration API; a package carries no secrets, agents, selections, schedule bindings,
   tags, catalog content, CAI publication or DBMI deployment, so finish each of those in the target (L-MIG-017;
   [Export & Import](../12-deploy-migrate/01-export-import-v3-migration-api.md)).
3. Cut over in sequence: snapshot, unbind the source, flip callers, switch CDC on the same slot, bind the target,
   verify (L-MIG-047; [Cutover & Rollback](../12-deploy-migrate/05-cutover-rollback.md)).
4. Send the vendor one batched case with only what the vendor alone can fix (L-MIG-074).
5. Decommission the source from verdicts built from the inventory, the id map and the import log, as a separate
   approved step (L-MIG-073; [Headless Deletes & Org Cleanup](../12-deploy-migrate/06-headless-deletes-org-cleanup.md)).

**Done when:** the target runs every lane green, the source has no bound schedules, and the decommission list is
approved.

---

## Day-2 operations

The full Day-2 runbook (alerting, the daily check, a failed job at 2am, upgrades, schedule owners, backups) is
[Run it in production](12-run-it-in-production.md).

| Situation | Do | Doc |
|---|---|---|
| A job failed (or a WARNING wrote 0 rows) | read the run by `runId`, get the session log, classify it (transient, capacity, deterministic, Hosted Agent outage, job cap), fix or retry once, check rows | [Run it in production](12-run-it-in-production.md) §3 · L-CDI-205, L-CDI-060 |
| Failed jobs go unnoticed | the tasks' failure e-mails plus a watcher that alerts on state change | [Run it in production](12-run-it-in-production.md) §1 · L-CDI-067 |
| Any agent, selection or pipeline change | one read-only verification sweep scoped to "since the change", then one end-to-end story traced hop by hop | [Evidence Discipline](../14-working-with-claude/02-evidence-discipline.md) §8 · L-METHOD-057 |
| Monitoring the agent hosts | an uptime alert per VM, host metrics that really arrive, a budget, freshness on replication feeds; engine and setting drift checks | [Secure Agent](../02-secure-agent/01-secure-agent-install-run-tune.md) §12 · L-ENV-074 |
| A promised licence or service | poll the licence record and every agent's engines; a new engine is the signal | [Secure Agent](../02-secure-agent/01-secure-agent-install-run-tune.md) §12 · L-IPU-057 |
| Resizing or rebooting an agent host | announce, drain, resize, then the fixed post-boot checklist | [Secure Agent](../02-secure-agent/01-secure-agent-install-run-tune.md) §2.1 · L-ENV-069 |
| Disk pressure on an agent host | free logs, journal and build cache; never prune `downloads/` or Docker volumes | [Secure Agent](../02-secure-agent/01-secure-agent-install-run-tune.md) §6 · L-AGENT-094 |
| Alerts that cry wolf | SLAs from the load schedule, stalls gated on a heartbeat table, volume-drop alerts with a floor | [Mapping Tasks](../04-mappings/03-mapping-tasks-create-update-run-monitor.md) §9 · L-ENV-077 |
| Pausing a lane for maintenance | a freshness map of every BI object first | [Serving Outputs to BI and Apps](../04-mappings/09-serving-outputs-to-bi-and-apps-freshness-latency-reverse-etl.md) §4 · L-ENV-079 |
| Retiring tasks | gated waves: categorise, scan configuration files too, export, delete, read back, rescan the catalog | [Headless Deletes & Org Cleanup](../12-deploy-migrate/06-headless-deletes-org-cleanup.md) · L-CLEAN-034 |
| The Hosted Agent is down (APP_105060 on every hosted connection, hosted runs failing in seconds) | support case, then fail over: rebind the tasks **and** the connections they use to a Secure Agent with full-body backups (a lookup resolves through its connection's own runtime), leave what the agent cannot serve, unblock stop-on-first-failure chains, re-run, undo when the runtime is back | [Runtime Environments](../02-secure-agent/02-runtime-environments-services-connectors.md) §1 · L-ENV-100, L-CONN-132, L-AGENT-117 |
| The CDC source host was hard-stopped | the jobs stay FAILED (PWX-36749) after the database returns: `job/resume`, and automate a restart-window auto-resume | [CDC from PostgreSQL](../06-cdc-ingestion/02-cdc-from-postgresql.md) §8 · L-DBMI-063 |
| A secret exposed or a key rotated | rotate every consumer in one window; dead keys from deleted projects removed | [Secrets Hygiene](../14-working-with-claude/06-secrets-hygiene.md) · L-ENV-052 |
| The org's REST authentication moving to JWT | every client behind a `session|jwt` switch with timed refresh | [Login, Sessions & Tokens](../01-login-and-orgs/02-login-sessions-tokens.md) §6 · L-AUTH-033 |

## Working with Claude on IDMC

- **One lead, one writer per org**, lanes for the rest; coordinate parallel sessions through tracker comments, not
  through messages that each cost the user an approval click (L-AUTH-054, L-METHOD-061;
  [Multi-Agent Coordination](../14-working-with-claude/03-multi-agent-coordination.md)).
- **Approvals:** spend, shared deletes and production changes wait for a human; batch them into one list, and treat a
  denial as covering the outcome (L-METHOD-065, L-METHOD-121).
- **Three paths for every task:** Claude, Claude through a named workaround, or the human as a last resort with the
  exact clicks written down (L-METHOD-066).
- **Estimates:** build them bottom-up from the steps; large Claude tasks were over-estimated about 2x, so never pad
  (L-METHOD-122).
- **Evidence:** dated, read back, success-only numbers; a green sweep proves only the window it covered
  ([Evidence Discipline](../14-working-with-claude/02-evidence-discipline.md); L-METHOD-124).
- **Keep the KB current:** every new generic lesson goes into a topic doc and a dated lesson
  ([How to use this KB](01-how-to-use-this-kb.md) §9).
