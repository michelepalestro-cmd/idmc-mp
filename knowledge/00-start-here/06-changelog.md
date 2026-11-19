# Changelog

**Answers:** What changed in this KB and when, which beliefs were overturned along the way, and what is still open?

**Read when:** you return to the KB after a while, a doc contradicts what you remember, or you need the history of a
belief.

**Key rules:**
- The latest dated evidence wins; older beliefs stay, marked superseded, in the lessons files (L-METHOD-035).
- A changelog entry is generic: what changed in the KB, never whose deployment it came from (L-METHOD-084).
- A wall overturned in this log is overturned everywhere: the Laws, the Capability Map and the topic doc change in the
  same edit (L-METHOD-034).

**Related:** [How to use this KB](01-how-to-use-this-kb.md) · [The Laws of Headless IDMC](02-the-laws-of-headless-idmc.md) ·
[Overturned Beliefs](../../lessons/overturned-beliefs.md) · [Lessons Learned](../../lessons/README.md) ·
[KB README](../README.md)

**Last verified:** 2026-11-19.

> In July the KB said "read almost everything, run almost everything, design almost nothing"; by late September most
> design, publish, deploy and delete steps had been proven headless, and the KB was rebuilt around dated lessons so that
> the next overturn can be recorded instead of rediscovered. October added pushdown, the last transformation types and
> the operating detail (agent tuning, job budgets, latency, serving to BI).

---

## 2026-11-19 (later): 188 lessons mined from public IDMC code

- **About 40 public repositories read** (no code run): CLIs, SDKs, community MCP servers, CAI and CI/CD repos, the
  vendor's own Claude skill, MDM and CDGC kits, and an open-source catalog's IDMC connector. Each candidate was checked
  against the existing lessons; duplicates were merged and unverified claims left out.
- **188 new lessons** (2,236 in total), every one labelled **Reported** (third-party code, not probed here) or
  **Documented** (the vendor skill), with a confidence note. Largest gains: CDGC (search behaviour, bulk import and
  export, audit events, DQ score upload, custom lineage and classifications), CAI (taskflow run, resume and terminate,
  package internals, fault-alert handlers, deployment settings), migration and source control, Secure Agent service and
  group configuration, MDM SaaS irreversible steps, and MCP tool design and monitoring patterns.
- **Two contradictions flagged, not overturned:** agent-group configuration has a reported REST route (L-AGENT-132 next
  to L-AGENT-088), and compare is reported as a POST (L-MIG-110 next to L-MIG-097). Probe both.
- **New:** [Community code index](../12-reference-library/community-code-index.md), from each lesson to the file it came
  from. The [ecosystem doc](../09-claire-mcp/07-ecosystem-plugins-registries-community-tools.md) gains the newly found
  repositories and three warnings (a phone-home script, an unattended write-capable bot, a cookie-copying extractor).

## 2026-11-19: 23 managed MCP servers, and the ecosystem around them

- **Managed servers brought to the October 2026 release** ([Managed MCP Servers](../09-claire-mcp/01-managed-mcp-servers-catalog-access.md)):
  the public registry (no login) lists 23 servers; four were missing here (`ordermanagement`, `cdgccatalogassethistory`,
  `policymanagement`, `idmcassetdocumentation`), plus the October tool additions to connection management, catalog
  discovery and catalog enrichment, a release-by-release count, and the October platform changes (protocol 2026-07-28,
  renamed OAuth servers, scopes, resources, tool states, monitoring). No new server authors mappings, deploys CDC or
  publishes CAI.
- **New doc** [Ecosystem: plugins, registries, community tools](../09-claire-mcp/07-ecosystem-plugins-registries-community-tools.md):
  the vendor's Claude plugin and how it sits next to this one, every place the servers are listed, the catalog-discovery
  and data-exploration tool contract, and a reviewed list of community CLIs, MCP servers, skills and CI/CD templates with
  verdicts.
- **6 new lessons (2,048 in total):** L-MCP-132 to L-MCP-137.

## 2026-11-17: a Quick Start, and the last two weeks of field work

- **Quick Start** ([10 Quick Start](10-quick-start-your-first-hour-with-idmc-and-claude.md)): the first hour for a
  new user: connect, prove the org, what to ask Claude for each common task, and the lessons that trip up almost every
  new user.
- **20 more from a live review of a mappings-built property MDM (2,036 in total):** mapping vs SQL write speed and
  why mapping-based mastering must be incremental; a 12-point checklist for why it failed at national scale; telling
  who wrote a table from the query log; address-verification job-cap burn and re-paying for verified addresses;
  blank match keys that block merges.
- **51 new lessons (2,016 in total)** from session work 2026-10-08 to 2026-11-13 that earlier harvests had not read:
  - IDMC native source control with a self-hosted Git: routing through the agent, checkout before an OVERWRITE
    import, no unlink endpoint, check-in limits.
  - Oracle: catalog scans need SELECT_CATALOG_ROLE; an Oracle target through the exemplar route; no engine restart.
  - CAI: idle timers still cost runs; anonymous processes on an agent port.
  - Tableau V3 targets: char_string publishes '0.0'; an invalid targetOperation is ignored.
  - OIE_007 on mapping-task imports; CLAIRE structure models tuned headless.
  - SharePoint connector traps; replication slots filling a CDC host; GCP, BigQuery and Azure CLI traps.
  - Claude working methods: subagents that die before writing, auto-mode production blocks, testing a packaged skill.

## 2026-11-10 (v5): ready for GitHub; what went wrong in a production deployment

Why: the KB is published as a git repository, and a production deployment onto a live warehouse (hundreds of tables,
a 100M+ row served table, many Claude sessions and another coding agent on one estate) produced most of its lessons
from things that went wrong around IDMC rather than in it.

- **Ready for GitHub:** `.gitignore` (caches, `.env` files, keys, run output, the private scan list), `.gitattributes`,
  a pre-commit hook (`git config core.hooksPath toolkit/tools/git-hooks`) and a CI job (`.github/workflows/secret-scan.yml`)
  that both run `toolkit/tools/secret_scan.py`; setup now starts from `git clone` and recommends keeping the login outside the
  working tree (`IDMC_CREDS_FILE`). Compiled Python caches, which carried a local home path, are gone; a real sub-org
  name and pod in the skill references became placeholders.
- **93 new lessons** (1,965 in all), 74 of them failures with their fix: a data disk that silently did not mount,
  forced password expiry and OOM lockouts, a Secure Agent watchdog, agent config saves that kill every job, backups
  that covered 2 databases and were never restored, repair copies piling up inside the database, a delete that hid
  49.5M loaded rows, DQ gates on the wrong table or unable to fail, live-database profiling (memory caps, stale
  "latest run", metric-store leftovers, one connection per database), an inherited 357-mapping build with fake
  lineage, golden-table rebuilds that doubled, peer sessions rewriting reviewed SQL, orphaned schedules and leases,
  identities that could not do the approved change, cost with no billing export, and Azure Native IDMC sign-up.
  41 of them add evidence to an existing lesson ("Newer evidence:" on the older one).
- **New doc:** [What Went Wrong: a Production Deployment Post-Mortem](09-what-went-wrong-production-deployment-post-mortem.md),
  every failure with the check that catches it and its lesson id, linked from README, How to use this KB and CLAUDE.md.

## 2026-11-03 (v4): any source, any target; never push, never say no too early

Why: readers' sessions treated the KB's example systems as the recommended stack (one kept falling back to BigQuery
for a flat-file to flat-file pipeline), and some walls were quoted as final answers. The goal of the KB is to help a
team deploy IDMC end to end, with every capability they ask for, on the systems they already have.

- **Two rules, at the top of README, CLAUDE.md, the Laws, the Capability Map and the skill:** (1) never push the user
  to another technology: a system the KB has never covered (SAP, Oracle, files, an API...) is built brand new with
  everything the KB has learned; (2) never say "not possible" before the eight-rung workaround ladder has been worked in
  the user's org (lessons, re-probe, another plane, clone a UI-made object, capture the UI call, another IDMC component,
  a Python bridge, one residual click). The KB is not an allow-list: nothing is forbidden or impossible because it is
  not written here. Native IDMC first; Python only when no IDMC path works. The flat-file target is the worked example
  (not documented, built on the user's own connection, written natively by IDMC, recorded as L-CDI-274).
- **Purpose and quick start:** the README now opens with what the KB is for (install, point Claude at it, sign in,
  create any IDMC asset), a four-step quick start and a "Create any IDMC asset: where to start" table (connections,
  runtimes, projects, mappings, tasks, taskflows, CDC, file ingestion, CAI, DQ, profiles, catalog, glossary, lineage,
  MDM, MCP, copies and moves). `IDMC_LOGIN.txt` ships empty; a private file outside the folder through
  `IDMC_CREDS_FILE` works the same.
- **The exemplar route** ([Mapping Fast Path](../03-cdi-data-integration/00-mapping-fast-path-read-this-first.md)
  §7.0, L-METHOD-129): a source, target or transformation that IDMC supports but the generator has no template for
  is learned from one mapping that already uses it (an existing one, or one made once in the Mapping Designer),
  exported and read offline with the new `toolkit/mapgen/exemplar.py`, then added to the package as a template. CLAUDE.md,
  the milestones, the generator README and the skill point there instead of stalling or substituting a connector.
- **New:** [New Pipeline Milestones](08-new-pipeline-milestones-any-source-any-target.md) (a recommended order,
  never a requirement): write the pipeline
  down, then (1) identify the runtime (Secure Agent or Hosted Agent), (2) identify the connections, (3) identify or
  create the project and folder and list the assets that belong in it (and what lives in the org instead), then the data
  contract, the mapping, the task, the first run and its proof, DQ, orchestration and governance; each with a Done-when
  gate, plus a walk-through for a connector the KB has never seen.
- **Neutral wording:** the README, How to use this KB, the End-to-End Playbook (its stack is now labelled a worked
  example), the Mapping Fast Path (the connector table is "proven so far, in no order of preference", with a route for
  an unlisted connector), the blueprints and the skill now say plainly that their systems are examples.
- **Generator:** a connection with no `kind` now lints `WARN CONN_KIND_MISSING` instead of silently being treated as
  BigQuery, and `CONN_KIND` says every other connector takes the generic path. Flat-file **targets** are documented:
  the first run creates the file, every run overwrites it, `createTarget` is optional (L-CDI-274;
  `toolkit/mapgen/examples/probes/m_probe_ff_target.json`, SPEC_REFERENCE, PROBES, Fast Path §2 and §4).
- **Skill:** its error-signature file is now generated from this KB's current lessons
  (`python toolkit/tools/build_skill_field_lessons.py`); the July file carried deployment-specific rows and is retired. The
  July reference files carry a "dated verdict" banner, and the July "design almost nothing" line is corrected.
- **Sharing:** `toolkit/tools/secret_scan.py` also flags payment-provider keys and account ids.
- **65 new lessons** (2026-10-26 to 2026-11-03), 6 lessons that were only in `lessons.jsonl` rendered into their
  files, and 3 marked disputed by newer evidence:
  - **Hosted Agent outage:** how it shows (APP_105060, L-AGENT-117), the runbook (L-ENV-100), why connections must be
    rebound as well as tasks (a lookup resolves its connection through the connection's own runtime, L-CONN-132), and
    the speed cost of the fallback agent (L-AGENT-118).
  - **Files and documents:** File Ingestion tasks created, run and polled headless (L-DBMI-060, L-DBMI-061,
    L-DBMI-062), Local Spark advanced configurations (L-AGENT-114), reading object-storage formats from connector
    metadata (L-CONN-129, L-CONN-130), a Structure Parser fed from the document itself (L-CDI-275), advanced-mode
    limits (L-CDI-276, L-CDI-277), and CAI moving file bytes (L-CAI-154, L-CAI-155).
  - **CAI packages:** what a hand-built package must carry (L-CAI-156), an unroutable process name (L-CAI-157), and the
    Operational Insights export header (L-CAI-159, disputes L-CAI-049).
  - **Lineage:** design for a clean path (L-CDGC-229), check a link before sharing it (L-CDGC-232), files loaded outside
    IDMC (L-CDGC-233), stitching storage copies (L-CDGC-227), curated-edge rules (L-CDGC-224, L-CDGC-228), scan hangs
    and cancels (L-CDGC-223, L-CDGC-225), scan times (L-CDGC-230), and scanner limits (L-CDGC-231, L-CDGC-234).
  - **Overturned by trying again:** data profiling of a database over JDBC V2, recorded as blocked, ran headless by
    cloning a working profile body (L-DQ-128; disputes L-DQ-119 and L-CONN-089).
  - **Operating mappings:** per-run SQL beyond about 4,000 characters (L-CDI-285), `$Source$` query overrides
    (L-CDI-284), Dynamic Mapping Tasks (L-CDI-289), retry classification and the incomplete activity log (L-CDI-287,
    L-CDI-288), lane sharding and memory caps (L-CDI-286, L-CDI-292), buffers from the session log (L-CDI-290), merging
    mappings between exports (L-CDI-278), and a set of smaller gotchas (L-CDI-279 to L-CDI-283, L-CDI-291).
  - **Address verification and DQ:** the cloud service from a Java transformation (L-DQ-132), what a Verifier returns
    (L-DQ-130), classifying failed rows before fixing them (L-DQ-129), the on-agent reference data (L-AGENT-116), the service's info route
    (L-DQ-131), designer resync after a rule change (L-DQ-126), Deduplicate outputs (L-DQ-127).
  - **Also:** CDC after a hard stop of the source host (L-DBMI-063), a warehouse quota failing every task
    (L-CONN-133), a REST connection for a SaaS API with a static key (L-CONN-131), proving a table migration inside IDMC
    (L-MIG-086), view-only copies with FRS CopyEntities (L-MIG-087), SESSSTARTTIME time zones (L-AGENT-115), CLAIRE
    lineage and classification answers (L-MCP-128, L-MCP-129), a designer sweep for Invalid badges (L-UI-036) and a
    tunnel-safe scan poller (L-ENV-099), and the exemplar route itself (L-METHOD-129).
- **Topic docs:** every new lesson is cited where a reader looks for it: about 25 Capability Map rows, about 45 Error
  Triage rows, the Hosted Agent outage runbook in Runtime Environments and the Playbook's day-2 operations, and the
  overturned and disputed lessons in Overturned Beliefs.

---

## 2026-11-02: a repeatable playbook for mastering a table

Why: "do MDM on this table" kept being re-planned from scratch, and the person/address recipe was being applied to
registries, model registries and dictionaries where it does not fit.

- New [Mastering a Table - Repeatable Playbook](../08-mdm/05-mastering-a-table-repeatable-playbook.md): five
  dataset archetypes (entity master, registry, versioned asset, definition, event), the same ten steps for all of
  them, a recipe per archetype, acceptance gates G1-G9 as copyable SQL, and a one-page spec to fill in per table.
- Lessons L-MDM-077 to L-MDM-081: classify before matching (per-scope rows are the grain), the alias crosswalk for
  versioned registries, one golden owner per scope (and the replace key), two-way dictionary reconciliation, and the
  mapping test (a Source query that does all the work masters nothing; section 6 of the playbook is the target shape).

---

## 2026-10-26: a mapping fast path, the generator's reference shipped, Hosted Agent limits

Why: sessions spent most of their time finding the right mapping facts among 1,700 lessons and five route descriptions.

- **New entry point:** [Mapping Fast Path](../03-cdi-data-integration/00-mapping-fast-path-read-this-first.md):
  the ten commands from login to a proven run, the spec settings per connector (Snowflake, Databricks, Salesforce,
  SharePoint Online, Tableau V3, BigQuery, PostgreSQL, JDBC, flat file, Fabric), where writer attributes go, which
  runtime to pick, and the errors that cost the most time, each with its lesson id. `CLAUDE.md`, the README, How to use
  this KB and the skill now send mapping work there first.
- **The generator ships its own documentation and templates:** `toolkit/mapgen/docs/SPEC_REFERENCE.md` (every spec
  option), `HOW_IT_WORKS.md`, `PROBES.md`, `RETAIL_SUITE.md`, `profile.example.json` and 28 example specs that were
  built and run in a real org (`toolkit/mapgen/examples/`). Code synced with the maintained copy: a Salesforce source's
  SOQL `filter` and `sfObject`, and rule-specification input scale (its test suite: 434 passed).
- **Recorded, not new behaviour:** Snowflake, Databricks and SharePoint connections lint with `WARN CONN_KIND` and go
  through the generic adapter path; that is expected.
- **54 new lessons** (dated 2026-10-04 to 2026-10-26; 18 refine an older lesson and say which):
  - **Hosted Agent:** what it runs and what still needs a Secure Agent: Structure Parser, Data Profiling, CDQ match /
    decision transformations, Tableau V3, SharePoint file transfers (L-AGENT-103, L-AGENT-104, L-DQ-114, L-CDI-247,
    L-CONN-116, L-CONN-125); Snowflake there through a Programmatic Access Token (L-CONN-118).
  - **Databricks:** the connection (L-CONN-119, L-CONN-120, L-CONN-127), full reload through `writeDisposition`
    Truncate (L-CDI-248), custom queries sent verbatim (L-CDI-249), its catalog source (L-CDGC-218).
  - **Moving an org:** re-pointing a package (L-MIG-082), bundle-template tasks that cannot migrate (L-MIG-083),
    connection clone and naming rules (L-CONN-122 to L-CONN-124).
  - **SharePoint Online:** the connection type is TOOLKIT, not TOOLKIT_CCI (L-CONN-128, an exception now noted on
    L-CONN-001); a file upload over Microsoft Graph from CAI with no agent (L-CAI-149).
  - **Runs and times:** poll a taskflow run with taskId and runId (L-CDI-252), REPO_17315 (L-CDI-253); the local
    times are UTC-4 on a US west pod too, so the offset is not the pod's zone (L-AUTH-094, refines L-AUTH-014).
  - Also Tableau V3 targets, catalog DQ scopes and rule occurrences, CAI process design, agent sizing and OOM behaviour.
- **Eight lessons** that were in `lessons.jsonl` but missing from their domain files are now in both.

---

## 2026-10-13: one user limited to one project, documents parsed from a column, warehouse quota stops

Ten new lesson ids, all dated 2026-10-13, from one build that read documents from a CRM into a warehouse, parsed them with
CLAIRE, scored them with data quality rules, cataloged the result and limited one user to that one project. In generic terms:

- **Access (new section in [Users, Roles & Permissions](../01-access-auth-orgs/04-users-roles-permissions.md) §3a).**
  Object permissions are read, added and removed over v3 on projects, assets, connections and runtime environments
  (L-AUTH-089). Role, group and membership writes take `privileges`, `roles` and `users`, not the names the validator prints,
  and a user must keep one direct role (L-AUTH-090). The pattern that limits one user to one project without changing
  anyone else's access (L-AUTH-091); the catalog has no per-source permission route, so such a user gets no catalog role
  (L-CDGC-195).
- **Documents without files.** A Structure Parser in BUFFER mode parses bytes decoded with `DEC_BASE64` from a column
  (L-CDI-244); a Snowflake BINARY source fails with 'Unknown native type', so keep base64 text (L-CONN-113).
- **Small facts.** A Salesforce datetime source field validates at precision 24, scale 0, which settles the datetime failure
  in L-CDI-217 (L-CDI-245); REG_EXTRACT needs a whole-value match (L-CDI-246); a profile whose table was recreated is
  recreated on a view (L-DQ-112); a warehouse resource monitor at its quota stops IDMC, catalog and BI jobs at once
  (L-ENV-096).

---

## 2026-10-09: CAI against on-premises PL/SQL APIs, agent-run timers, contract APIs

Nine new lesson ids, all from one build that put CAI where a message bus's PL/SQL publisher, subscriber, retry and
routing adapters used to be, on one Secure Agent next to the database. In generic terms:

- **Walls (2).** A Data Access Service Connector would not publish in one org: an empty 'Publish Error' from both the
  designer and `asset/v1/publish` (L-CAI-139); its XML format is recorded for the orgs where it publishes (L-CAI-140). The
  restadmin scheduler stored a schedule for an agent-run process but never ran it (L-CAI-142); start such processes from
  the agent host. The Capability Map and the topic docs changed in the same edit.
- **Routes.** PL/SQL APIs through the database's REST layer (L-CAI-146); agent-published processes answer on the agent
  host and give their Swagger there (L-CAI-143); a driver unzipped into the engine's `ext` directory needs no restart
  (L-CAI-141, not yet exercised by a JDBC call).
- **Process design.** A contract-checking API that answers 400 or 503 through a Milestone step (L-CAI-144); double-escape
  `&` between query parameters in a REST action URL, or the call fails silently at run time (L-CAI-145); `eventconnection`
  stops one event source while the other consumers of the same connection keep running (L-CAI-147).
- **Corrected.** CAI API calls per message (L-CAI-148) gain d, the delivery-subprocess runs (one per target call), and are
  counted on the CAI Monitor's run list: an event-ledger count misses every run that writes no event (2 to 5 calls a message
  there against 7 to 10 on the Monitor).

---

## 2026-10-08: event-driven CAI on Kafka and JMS, BigQuery profiling fixed, lineage over REST

Thirty-eight new lesson ids, all dated 2026-10-08, from one build that put CAI between a Kafka hub, a JMS broker and REST
targets on a Secure Agent, with CDC into a warehouse and a governed medallion behind it. In generic terms:

- **Overturned (3).** Kafka and AMQP (JMS) listener connections, event-bound processes and fault handling author headless in an
  import package: the Camel `javaConnector` values and the consumer and producer elements are in L-CAI-116 (the designer-only
  belief, since superseded, is L-CAI-117). Lineage is readable over REST hop by hop through the asset read's `lineage` segment (L-CDGC-181;
  L-CDGC-085 moved to Superseded), and curated lineage edges are writable through the ccgf-contentv2 publish with
  `core.DataSetDataFlow` and `core.DirectionalDataFlow` (L-CDGC-179; the superseded 'silent no-op' belief is L-CDGC-180). The Laws (law
  17), the Capability Map and the topic docs changed in the same edit.
- **CAI listeners (new doc [CAI Event Listeners](../05-cai-application-integration/06-cai-event-listeners-kafka-amqp-jms.md)).**
  Event-bound process XML and the Kafka event shape (L-CAI-118); a safe first start (L-CAI-119); one process at a time per
  consumer (L-CAI-120); a stop resumes from the last offset auto-commit (L-CAI-121); restadmin `eventconnection` start and stop
  need `IDS-SESSION-ID` (L-CAI-122); the AMQP connector drops JMS property names that are not Java identifiers unless
  `jms.validatePropertyNames=false` (L-CAI-123); the native Kafka producer (L-CAI-124) and its idempotence trap (L-CAI-125);
  measured drain rates and a 4 MB message (L-CAI-126, L-CAI-127).
- **CAI assets.** `requestTimeout` is in seconds (L-CAI-128); `failOnError` false versus true (L-CAI-129); a process without an
  access configuration is a private subprocess (L-CAI-130); `util:getProcessId()` for tracing (L-CAI-131); a connection secret
  stored encrypted through `asset/v1/update`, which proves L-CAI-015 for app connections (L-CAI-132); dependent processes go
  out-of-date after a connection republish (L-CAI-133); a Wait period from a field (L-CAI-134); Decision links (L-CAI-135);
  the dependency closure of a hand-built package (L-CAI-136); subprocess output mapping and fault catching (L-CAI-137); ask the
  system of record on retries (L-CAI-138).
- **Profiling and DQ.** Data Profiling of BigQuery V2 failed with 'Cannot parse null string' because the connection's five
  hidden retry attributes were empty; with the connector defaults it completes (L-DQ-110, which resolves the failure in
  L-DQ-107). A UPC-A check digit in a rule specification's advanced script (L-DQ-111). Catalog-source profiling of BigQuery still
  fails (L-CDGC-184); catalog DQ on BigQuery skips tables with a decimal-input occurrence, so score decimal rules through
  text-input twins (L-CDGC-185).
- **Catalog.** The BigQuery scanner needs project-level dataset metadata (L-CDGC-182); an IICS source's Database Ingestion
  filter needs Filter Conditions 'Database' (L-CDGC-183).
- **CDC and CDI.** A DBMI deploy to BigQuery needs project-level metadata too (L-DBMI-054); CDC into BigQuery bills at least
  30 MiB per changed table per cycle (L-DBMI-055); stop and resume continue from the restart point (L-DBMI-056); generated
  Normalizers failed at DTM load, a Union fan-out works (L-CDI-236).
- **Next to IDMC.** Pin the Grafana BigQuery plugin on Grafana older than 11.6 (L-ENV-094); an anonymous Grafana Viewer can run
  any SQL through `/api/ds/query` unless a guard allows only the dashboards' queries (L-ENV-095).
- **Not added, with the reason:** a candidate about empty XQuery sequences in CAI conditions (no primary evidence kept), one
  about the XML GUID differing from the object id (already L-CAI-019), and the BigQuery private-key format for DBMI (already
  L-CONN-035, L-DBMI-034, L-MCP-127).

## 2026-10-07: SharePoint documents into the warehouse, and the Structure Parser corrected

Seventeen new lessons in two batches, nine dated 2026-10-06 and eight dated 2026-10-07, with the topic docs brought in
line. In generic terms:

- **Overturned.** Two Structure Parser beliefs of 2026-10-06. The parser's output ports take the model's types
  (bigint, decimal(10,2), string(n)), not string(255) everywhere, and code-like values lose their separator and leading
  zeros (L-CDI-229; L-CDI-225 moved to Superseded). An exported mapping stores `isdModelId` = `"@<v3 id>"` with a copy
  of the model and a passthrough flag per output group, while the designer resolves the model by its v2 id (FRS
  Documents by `repoHandle`, `structureDiscoveryDetail`) and fills the output groups from `groupsWithXpath` (L-CDI-230;
  L-CDI-226 moved to Superseded).
- **Batch 2 (2026-10-06, nine lessons).** The CDI SharePoint Online connector: a Graph-scoped refresh token reads 0
  objects while Test Connection passes, so mint a SharePoint-scoped one (L-CONN-100); a test proves only that a
  delegated token renews, and an object browse proves access (L-CONN-101); what a read returns and downloads, and the
  connector's source, target and lookup capabilities (L-CONN-102); one row per file through an Indirect File Path of
  absolute, URL-encoded wildcard patterns (L-CONN-103). Unbounded Snowflake VARCHAR targets run the CDI writer out of
  Java memory (L-CDI-227); lookups have no operation context of their own, and a designer save redeploys every task on
  the mapping (L-CDI-228). A mapping's SharePoint connection reference, which can be named after the connection's v2
  id, MERGEs onto the SharePoint catalog source's Site (L-CDGC-167); a Snowflake extraction ends PARTIAL_COMPLETED when
  the role cannot read tags (L-CDGC-168); copying a selection of transformations clones a whole flow (L-UI-034).
- **Batch 3 (2026-10-07, eight lessons).** Search pages on data360 drop assets without a sort: sort on `core.identity`
  and filter on `core.origin` + `elementType` OBJECT (L-CDGC-169); a decimal-input rule bound to a text column is
  skipped without an error, so bind a typed view column (L-CDGC-170); the two corrections above (L-CDI-229, L-CDI-230);
  a recipe that parses every document of a folder and keeps the source file on each parsed row (L-CDI-231); changing a
  parser's model clears its field mapping and links (L-CDI-232); Snowflake source fields import at 16,777,216
  characters, the Advanced filter is passed verbatim as the WHERE clause, and Preview Data ignores both (L-CDI-233);
  small mapping-designer traps (L-UI-035).
- **Counts:** 1,581 lessons (1,385 current, 177 superseded, 19 disputed).
- **Docs updated:** the Capability Map (sections 3, 4, 5, 12 and 14), Error Triage, Connections, Connector Notes, How
  Claude Builds Mappings Headless (section 10 corrected and extended, sections 8 and 11), Mapping Tasks, Source & Target
  Gotchas, the five CDGC docs, DQ Scorecards (Pattern C), and UI Automation with Playwright.

## 2026-10-06: lineage stitching, catalog rule occurrences and structure models go headless

Seventeen new lessons, all dated 2026-10-06, with the topic docs brought in line. In generic terms:

- **Overturned.** Connection assignment for CDI lineage is headless: a `connectionAssignment` call with
  `operationType=MERGE` stitches each IICS connection reference to its physical catalog source, `SPLIT` undoes it, and
  `ASSIGN`, `UNASSIGN`, `ACCEPT` and `CREATE` are not values of the enum; a lineage read-back is the proof, because the
  job also completes for a bogus reference (L-CDGC-159; L-CDGC-086 moved to Superseded). A mapping's flat-file reference
  stitches the same way to a File System catalog source (L-CDGC-160).
- **Disputed.** L-UI-011 (IDMC consoles render blank under automation behind a transparent proxy): headless Chromium
  with the Private and Local Network Access checks off drove Metadata Command Center, the catalog and the mapping
  designer from behind such a proxy (L-UI-031). Data Profiling and Administrator were not retested; the cloud-host
  fallback stays.
- **New headless routes.** Catalog Data Quality rule occurrences created over REST (a contentv2 publish of a
  RuleInstance plus its column relationship, then a sync) and scored per occurrence by the Data Quality capability
  (L-CDGC-161, L-CDGC-166); a rule specification's ports and description read through `extensionPoint` (L-DQ-109);
  intelligent structure models created from a sample file in six calls, with the Structure Discovery service's session
  and CSRF rules, what its PDF and spreadsheet learners produce, and how a Structure Parser keeps the model
  (L-CDI-223 to L-CDI-226; L-CDI-226 since superseded by L-CDI-230).
- **Gotchas.** SharePoint Online catalog sources (tenant-root URL, full-site subsite URL, every scanner option on
  create), the `id` a catalog-source PUT must repeat, technical-asset descriptions patched with `core.description`
  alone, and the query types data360 search accepts (L-CDGC-162 to L-CDGC-165); catalog picker automation and the
  structure-model editor's endless spinner (L-UI-032, L-UI-033); a message to a running background agent starts a
  second copy of it (L-METHOD-128).
- **Lessons hygiene.** Seven lessons that existed only in `lessons.jsonl` were rendered into their domain files, five
  lesson blocks filed in the wrong section were moved back to Current, and the counts were recomputed (1,564 lessons:
  1,370 current, 175 superseded, 19 disputed).
- **Docs updated:** the Laws (16, 17, 19), the Capability Map (sections 4, 10, 12 to 14 and "What moved"), Error
  Triage, the End-to-End Playbook (stage 9), the five CDGC docs, DQ Assets, Profiling and DQ Scorecards (the
  rule-occurrence recipe), How Claude Builds Mappings Headless (new section 10), CLAIRE GPT Prompting Rules, UI
  Automation with Playwright, How Claude Reaches and Drives IDMC, and Multi-Agent Coordination.

## 2026-10-04: verification pass of the currency update

An independent check of about 130 facts from the period against the KB. In generic terms:

- **New lessons.** A DBMI start right after an agent restart (L-DBMI-052); a newer driver download that broke the DBMI
  staging writer (L-DBMI-053); one catalog system job per glossary asset created (L-CDGC-153); attributing job burn to
  the trigger of each run before trimming (L-IPU-061); subagents that lose a very large single-response file write
  (L-METHOD-127). Refined: L-ENV-085 (a browser save rewrites a workbook's format), L-CONN-088 (the CRM limits read is
  hidden from a minimum-access profile).
- **Corrected.** Cleanse and fuzzy Deduplicate assets do copy between orgs by package import (the DQ Assets doc still
  said untested); Error Triage now recommends one starter with per-table conflict locks, not one global run lock;
  the schedule `interval`/`frequency` rule (`UI_10622`) and the CSS-case trap reached their topic docs.
- **Hygiene.** Repeated lesson ids inside one citation were collapsed; the agent install root is written
  `<agent_home>` everywhere; the Reference Library and Script Library READMEs got the standard opening block.

## 2026-10-03: currency update and share-readiness pass

**Currency update.** About 190 harvested candidate lessons (field notes, the project tracker, project documents and
session scratch, dated 2026-09-28 to 2026-10-03) were checked against the KB. New ones became lessons in
`lessons`, refinements updated existing lessons in place, superseded beliefs moved to Overturned Beliefs,
and the topic docs were brought in line. In generic terms:

- **Overturned.** Full SQL ELT (BigQuery pushdown) is headless: three settings on the v2 mapping task, with the session
  log as the only proof. The remaining "not headless" transformations (Union, Rank, Sequence, Lookup, Data Masking, Rule
  Specification, Cleanse, Deduplicate, Normalizer) were built and run by a mapping generator. The Secure Agent's
  `downloads/` folder is live code, not a cache.
- **Limits and behaviours.** The DIS DTM pool defaults to 2 and caps real concurrency; DTM heap and pool belong in the
  agent's cloud-side configuration; full pushdown writes targets serially and can be slower on small multi-target
  mappings; CAI invocations are not jobs; what a hit job cap looks like in run data, four candidate reset windows and a
  proactive job ledger; metering export windows; profile run history; catalog scans on hosts that run two agents;
  same-millisecond temp-view collisions and the transient failures worth one retry.
- **Patterns.** The integration-layer split (an API gateway runs the application's real-time calls; IDMC owns
  analytics integration); serving outputs to BI without a personal OAuth login; per-hop latency measured with warehouse
  time travel; reverse-ETL windows sized to a small CRM org; write-back that also reaches the identity provider;
  erasure through CDC; resizing and rebooting an agent host with a fixed post-boot checklist.
- **Claude working methods.** A permission denial covers the outcome; coordinate parallel sessions through tracker
  comments; estimates calibrated against measured actuals; three paths for every task; evidence traps (new-socket
  samplers, repository copies of schedules, cron lines that run and do nothing).
- **Orientation.** Every topic doc now opens with a Claude-friendly block (Answers, Read when, Key rules with their
  lesson ids, Related, Last verified). New: the [End-to-End Playbook](07-end-to-end-playbook-deploy-and-operate-idmc-with-claude.md)
  and a CDI doc on [serving outputs to BI and apps](../03-cdi-data-integration/10-serving-outputs-to-bi-and-apps-freshness-latency-reverse-etl.md).
  The Laws, Capability Map, Error Triage and Glossary were updated, and the README and
  [How to use this KB](01-how-to-use-this-kb.md) were rewritten as the entry point.

**Share-readiness pass.**

- **Generic throughout.** Every doc was re-read end to end. Org, agent, connection, runtime and object ids, hosts, pods
  tied to one deployment, and application, dataset and object names were replaced with placeholders (`<orgIdV3>`,
  `<pod>`, `<project>/<folder>`, `<dataset>`, `<cloud-project>`), and dated incidents were restated as timeless
  lessons. The 400-level detail (routes, bodies, error codes, timings, limits, scripts) was kept.
- **Moved out.** Deployment-specific narratives and internal commercial material left the KB; every link now stays
  inside the KB folder.
- **Vendor roadmap.** Preview and GA dates heard in vendor conversations were removed; the docs say "on the vendor
  roadmap, no committed date" and point to the current release notes.
- **The share gate** (kept outside the KB) now also scans Office documents, PDFs and file names.

## 2026-10-01: CLAIRE GPT deep dive (about 190 runs, three lanes, plus the vendor docs)

- **New lessons L-MCP-091 to L-MCP-120 and L-UI-030.** What CLAIRE answers now; the publish-consent trap (never type
  at "Publish Rules / Don't Publish Rules") and a harness publish guard; dictionaries saved before Publish;
  recommendation matches existing rules only; the policy-file opener; one asset per data question; narratives read only
  the first rows; SQL in chat refused (use Show Code); discovery and search flakiness; chains, memory clear and numbered
  prompts; hallucination-prone asks; view-level vs job-level lineage; in-chat mapping proposals; answer times and hangs;
  the managed agent MCP routes answering like the UI; MDM and marketplace in chat. Documented facts: supported
  data-exploration sources and the 100 x 100 preview cap, gateway tuning properties, 50 IPU per 1,000 queries and the
  design-time promotion to 2027-01-31, models and retention, the agent status board, 20 managed MCP servers and their
  argument schemas, role privileges and file limits.
- **Overturned (moved to Superseded):** L-MCP-058 (catalog-wide classification search, mappings by name, product
  how-to and view lineage now pass), L-MCP-088 (fix-first is grounded with "Use only the scores in the catalog"; since superseded by L-MCP-095),
  L-MCP-053 (NL-to-SQL now has a headless route through the managed agent MCP tools; since superseded by L-MCP-111).
- **Docs updated:** CLAIRE GPT Prompting Rules (sections 1-4, 6-9, 11, 12), the Capability Map (section 16), Error
  Triage, the lessons README and Overturned Beliefs.

## 2026-09-30: an all-services agent, consolidation at scale, CLAIRE rule publishing

- **Secure Agent (L-AGENT-089 to 096).** Running every service on an agent that shares its host:
  - the Process Server's hardcoded embedded-database port and missing keystore/descriptor, with a self-healing guard;
  - static ports (only one Process Server, and one Cloud Integration Hub API port, per host);
  - the Data Access Management restart loop without an org entitlement;
  - parsing `getStatus`;
  - memory for about 17 services;
  - `downloads/` is live and must never be pruned;
  - stale `.pid` files after a reboot;
  - scoping a pre-start guard to its own agent user.
- **CDI (L-CDI-195 to 200).**
  - Schedule update field semantics.
  - Editing a copy-data task's SQL headless.
  - Change every live writer of a table.
  - Per-target row counts of multi-target mappings.
  - Key-sync deletes vs append-history targets.
  - The BigQuery writer poll interval that generated mappings must carry.
- **CLAIRE and DQ (L-MCP-079, L-DQ-094).**
  - CLAIRE GPT creates, tests and publishes DQ rules end to end. Its plan buttons only fill the input, so press Send. This overturns the earlier "nothing after proceed" failure.
  - Rule-specification descriptions update headless with an FRS PATCH of `description`.
- **MDM (L-MDM-070).** The bulk soft-delete route and source-system value.
- **Inventory traps (L-MIG-072, L-AUTH-088, L-CDI-201).** Linear taskflows are `WORKFLOW` not `TASKFLOW`; references page at 50; a v2 session on v3 routes gives 401 (not 'no objects'); taskflow-run tasks appear only as activity-log sub-entries.
- **CLAIRE GPT and catalog data quality, end to end (L-MCP-086 to L-MCP-089, L-CDGC-147 to L-CDGC-149, L-DQ-097).**
  - Name the columns when asking CLAIRE to recommend rules; otherwise it pairs rules with the wrong columns.
  - A more reliable blind-spots wording; "What should we fix first?" still invents issues; what CLAIRE does and doesn't do without the data gateway service.
  - Recommend and accept, run the source's Data Quality capability, then ask for the score: the full loop works, and four July walls fell
    (L-DQ-044, L-DQ-051, L-DQ-052, L-CDGC-082 moved to Superseded).
  - Catalog pitfalls: old resource names after a rename, auto-accepted assignments that still gave no job-level lineage in CLAIRE, leftover temp views in impact answers.
- **Methods and automation (L-METHOD-119, L-METHOD-120, L-UI-028, L-UI-029).** Diff a governance feed across orgs before switching it; re-test demo
  prompts after every catalog change; a CLAIRE harness settle rule; pinning conversations headless.
- **General (L-ENV-067, L-ENV-068).** A canary-and-reminder guard for an expiring BI credential; API gateways in Local Mode look inactive in the vendor console.
- **MDM (L-MDM-073).** The operational app often keeps its own copy of the match key (for one-per-person guards and
  duplicate worklists); a pipeline-only key change leaves it denying and flagging the people you split.
- **MCP for outside agents, and one overturn (L-MCP-081 to L-MCP-085).**
  - The AI Agent Engineering builder is being sunset (vendor notice, May 2026). External MCP tool connections now exist
    only on private-preview orgs, so L-MCP-013 ("recreate them in the designer") moved to Superseded. The Capability Map,
    Error Triage, Glossary, Laws and the CAI, migration and MCP topic docs were qualified.
  - The replacement pattern is one aggregating MCP gateway that your own agent calls. It needs a per-proxy tool-inventory
    cache (FastMCP resolves every call by listing all upstreams: about 26 s per call without it) and client timeouts
    (an upstream HTTP 500 hangs the call). Toolbox descriptions must name the real warehouse project.
- **Agent licensing signals (L-AGENT-097, L-AGENT-098).** The Data Gateway behind CLAIRE's "Query the data" is a
  Platform licence package, not a service you can select. "Received new AppSpec" log lines are inventory, not enablement.
- **Smaller ones (L-DQ-096, L-METHOD-117, L-METHOD-118, L-ENV-066).** A stale profile id gives `PROFILE_SVC_00005`. A
  secret found in git may already be dead (compare by length and hash, then make a path-limited commit). Browser checks
  read CSS-transformed text. Mailpit deletes need its HTTP API.
- Further lessons from the same day by other sessions (catalog, MCP, methods, environment) are listed in their domain
  files with 2026-09-30 dates.

## 2026-09-29: the rebuild

- **Sources pooled.** About 2,200 raw lessons from 13 extraction passes over the full project-tracker history
  (14 projects, about 2,400 issues and 11,000 comments), an earlier distilled lessons base, Claude's memory, the
  installed IDMC skills, the API and MCP reference corpus, and live pipeline code.
- **Lessons.** Deduplicated into **1,335 lessons** with stable ids in 14 domain files: 1,154 current, 164 superseded and
  17 disputed (a 1,336th lesson, on agent engine configuration, was added the same day). Where lessons conflicted, the latest dated evidence won, and every older belief was kept with the lesson
  that overturned it. A machine-readable copy, one JSON object per lesson, is
  `lessons\lessons.jsonl`.
- **Topic folders.** Folders `01`–`11` and `14` were written from the pooled lessons: 59 docs, each with a summary, a
  "Last verified" range, related links, lesson citations and an overturned-beliefs table, plus a Script Library of 14
  standard-library Python scripts (dry run by default, org-guarded writes).
- **Orientation layer.** This folder (`00`): how to use the KB, the 30 laws, the capability map, the error triage, the
  glossary and this changelog; plus the lessons README and the corrections log in `lessons`.
- **Generic by design.** Everything specific to one deployment (its applications, orgs, ids, hosts and tracker
  history) moved out of the KB. A share gate keeps folders `00`–`14` free of those names; the Reference Library was
  sanitized to the same rule (vendor text excepted).
- **Secrets.** Secret-bearing files were sequestered outside the KB and redacted copies kept; the rotation list is kept
  outside the KB too.
- **Housekeeping.** Duplicates, misfiled items and the old bucket folders moved to a dated archive outside the KB, each
  move reversible from an undo log.

## How the KB evolved

| Date | Change |
|---|---|
| 2026-06-27 to 2026-07-09 | First field lessons from a project board. Many early verdicts ("not licensed", "UI-only", "the API is a no-op") came from wrong hosts, missing headers or the login `products[]` list, and were overturned later |
| 2026-07-25/26 | The API and MCP reference corpus (about 167 endpoints, four verb states) and the installed IDMC skills: eight laws, an error triage, the host map, and the framing "design almost nothing". A DNS sweep found Database Ingestion on `<pod>-ing`; CAI publish over REST was confirmed |
| 2026-08-18 to 2026-08-20 | A mapping clone with a swapped connection GUID and automated designer authoring (routes 3 and 4; the first package-edit clones date from 2026-07-04); v2 DELETE on mappings |
| 2026-09-22 | First consolidation of scattered IDMC notes, scripts and references into 13 buckets |
| 2026-09-21 to 2026-09-29 | The September walls fell: the MCP registry (19 servers), template mapping tasks and linear taskflows, DBMI create and deploy, profiling create and run, catalog-source create and update, glossary and link writes, the runtime-environment selections PUT, MCP OAuth clients, FRS and user deletes, a full org-to-org migration, and synthesized IMF mappings |
| 2026-09-29 | The rebuild above |
| 2026-09-30 to 2026-10-03 | Full pushdown and the remaining transformation types proven headless; agent tuning (DTM pool, cloud-side heap, two agents on one host), job budgets and per-hop latency measured in production-shaped runs |
| 2026-10-03 | The currency update and share-readiness pass above |

## The beliefs that changed outcomes most

Each is a row in [Overturned Beliefs](../../lessons/overturned-beliefs.md) with its dates and lesson ids.

1. **PUT is not absent.** The runtime-environment selections PUT (2026-09-28), catalog-source and profile PUTs.
2. **`products[]` is not the entitlement map**, and a 404 is not a licence verdict (July, recurring into September).
3. **Design is headless through packages**: clones (from 2026-07-05), CAI and DBMI objects (2026-09-22), from-scratch
   packages (2026-09-25) and IMF-synthesized mappings (2026-09-29).
4. **CAI publish, DBMI deploy and profile runs have REST verbs** on their own hosts (2026-07-09 to 2026-09-28).
5. **The managed MCP catalog is an org registry** (19 servers on one org, 2026-09-23), not the five servers of the
   April 2026 guide.
6. **Deletes are headless**: v2 DELETE on seven resources, FRS `DeleteEntities` and `BaseEntities`, users (2026-09-28).
7. **Sessions die 30 minutes after grant**, not after 30 idle minutes (2026-09-28).
8. **Full pushdown is a task setting, not a UI-only property** (2026-10-01), and it is not automatically faster.
9. **The agent's `downloads/` folder is not a cache** (2026-09-30): pruning it broke most services.

## Known gaps after the currency update (2026-10-03)

- **Still unproven headless:** the Data Quality transformation and Update Strategy in generated mappings; the body of
  the catalog's connection-assignment accept call; the monthly job cap's reset day (guard on the worst window).
- **Documented by the vendor, not exercised here:** the session-ID to JWT authentication change and its 2,000-character
  token cap; Git source-control promotion over the v3 API; Application Ingestion and Replication tasks; the
  OAuth 2.1 public client for interactive MCP clients. Treat them as DOC until a run proves them.

## Known gaps after the rebuild

- **Not re-probed since July:** steward assignment, bulk acceptance of CLAIRE classifications, the lineage REST family,
  CDGC catalog rule occurrences, managed-API authoring.
- **Open questions:** publishing an advanced taskflow through a designer-made shell; whether JDBC V2 ever sends a
  password; the Content-Type that DBMI `job/status` wants; MDM Save versus Publish; the Data Profiling query CRUD
  paths; the managed MCP tool count (about 140 reported, about 120 summed per server).
- **Script Library:** compile-checked and exercised offline with mocked HTTP on 2026-09-29; not yet run against a live
  org in its current form.
- **Reference Library:** its live rows date from 2026-06-28 to 2026-07-26; where it disagrees with a topic folder, the
  topic folder's later evidence wins.
