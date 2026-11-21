# How to use this KB

**Answers:** What is this KB and what is it not? In which order should a Claude session read it? Which doc answers my
task? How do I map its placeholders onto my own org? Which safety rules apply to every session? How is each doc built,
how sure is each claim, and how do I add what I learn?

**Read when:** at the start of every session that will touch IDMC, and whenever you are not sure which doc to open.

**Key rules:**
- The KB is guidance: build with the user's systems; its examples are not recommendations (§1).
- Find your task in the routing table (§3) and open its doc; read the Laws before the first write (L-METHOD-034).
- Map placeholders from live reads of your own org; never copy an id from one org into another (L-AUTH-011,
  L-AUTH-046).
- Every claim carries an evidence state and a date, and the latest dated evidence wins (L-METHOD-023, L-METHOD-035).
- Writes are dry runs until an org guard passes, and spend needs approval (L-METHOD-065, L-IPU-005).
- New generic knowledge goes into a topic doc and a dated lesson; deployment-specific facts stay outside the KB
  (L-METHOD-084).

**Related:** [KB README](../README.md) · [02 The Laws of Headless IDMC](02-the-laws-of-headless-idmc.md) ·
[03 Capability Map](03-capability-map.md) ·
[07 End-to-End Playbook](07-end-to-end-playbook-deploy-and-operate-idmc-with-claude.md) ·
[Lessons Learned](../lessons/README.md)

**Last verified:** 2026-11-10 (the evidence of the whole KB spans 2026-06-27 to 2026-11-10).

> This KB tells a Claude session how Informatica IDMC really behaves when it is driven without the UI: exact routes,
> hosts, headers, bodies, error codes, walls and the workarounds that beat them, plus more than 2,300 dated lessons.
> Every folder (`00`–`14`) is generic and works in any org; deployment-specific material is kept outside this KB.

---

## 1. What it is, and who it is for

- **A Claude session** (or a subagent) that must read, run, build, change, migrate or clean IDMC objects over REST or
  managed MCP, in an org it may never have seen. The docs assume Python or curl, a shell on the host that runs the
  Secure Agent when one is needed, and no browser unless a step is proven UI-only.
- **A human** who wants the same answers: what works headless, what it costs, what breaks, and what to hand to
  Informatica support.
- It is **not** vendor documentation. Where a vendor guide was the only source, the text says "documented" and names
  the guide. Everything else was observed live, with a date. It is not a description of any one deployment either:
  numbers stay ("a 62-task linear taskflow took 21 min"), names go.
- It is **guidance, not a script or a reference architecture.** The systems in its examples (PostgreSQL, BigQuery,
  Snowflake, Databricks, Salesforce, SharePoint, ClickHouse, Tableau, flat files) are the ones its builds happened to
  use, not recommendations. Readers come with any source, target and connector. Use the KB for the order of work, the
  gates, the safety rules and the evidence on how IDMC behaves; take the systems, names and settings from the user and
  their org. A connector the KB has not covered is the normal case: find its settings in the org, prove them with one
  small run, and record a lesson
  ([New Pipeline Milestones](08-new-pipeline-milestones-any-source-any-target.md), "Using this KB as guidance").

## 2. The read order

**First 15 minutes of a new session:**

1. New to IDMC with Claude? The [Quick Start](10-quick-start-your-first-hour-with-idmc-and-claude.md) first.
   Then this page, then [The Laws of Headless IDMC](02-the-laws-of-headless-idmc.md) once.
2. A new pipeline: [New Pipeline Milestones](08-new-pipeline-milestones-any-source-any-target.md) (runtime,
   connections, folder and assets first). Building or extending a deployment: the [End-to-End Playbook](07-end-to-end-playbook-deploy-and-operate-idmc-with-claude.md).
   Asking "can I do X?": the [Capability Map](03-capability-map.md). Going onto a live production system or
   inheriting a build: [What Went Wrong](09-what-went-wrong-production-deployment-post-mortem.md) first.
3. Open the topic doc for your task (§3). Read its opening block (Answers, Read when, Key rules) to confirm it is the
   right doc, then the section you need.
4. When anything fails, or succeeds suspiciously: [Error Triage](04-error-triage.md).
5. Before quoting any wall: [Overturned Beliefs](../lessons/overturned-beliefs.md) and the lesson's date.

**First ten minutes in a new org:**

1. Log in once at the org's own domain host, and derive the pod, both org ids and the base URL from the answer
   ([Identify the Org Before You Write](../01-login-and-orgs/03-identify-the-org-before-you-write.md)).
2. Read the agents and their `agentEngines[]`; ignore the login `products[]` list.
3. Look up what you are about to do in the [Capability Map](03-capability-map.md), then open its doc.
4. Before the first write: a backup, a dry run, an org assertion, and a plan for the read-back.

## 3. Which task is this? Go straight to

Open the first doc; read the second when the first sends you there. Scripts are in the
[Script Library](../../toolkit/lib/README.md) (dry run by default; writes need
`--execute --expect-org <orgIdV3>`).

| Your task | Go straight to | Then | Script |
|---|---|---|---|
| Build a new pipeline, any source to any target | [New Pipeline Milestones](08-new-pipeline-milestones-any-source-any-target.md) | [Mapping Fast Path](../04-mappings/00-mapping-fast-path-read-this-first.md) | `check_login.py`, `toolkit/mapgen/mapgen.py` |
| Avoid the failures of a production deployment (backups, gates, host, many sessions) | [What Went Wrong](09-what-went-wrong-production-deployment-post-mortem.md) | the lesson each row cites | (none) |
| Keep a deployment running after go-live (alerts, daily check, failed-job runbook, backups) | [Run It in Production](12-run-it-in-production.md) | [What Went Wrong](09-what-went-wrong-production-deployment-post-mortem.md) | `/informatica-idmc-headless:health-check`, `idmc_export_import.py` |
| Stand up or extend a deployment end to end | [End-to-End Playbook](07-end-to-end-playbook-deploy-and-operate-idmc-with-claude.md) | the doc each stage names | (per stage) |
| Log in, pick the right host and header, avoid a lockout | [Login, Sessions & Tokens](../01-login-and-orgs/02-login-sessions-tokens.md) | [Pods, Hosts & Service Planes](../01-login-and-orgs/01-pods-hosts-service-planes.md) | `idmc_session.py whoami` |
| Prove which org you are in before writing | [Identify the Org Before You Write](../01-login-and-orgs/03-identify-the-org-before-you-write.md) | [Users, Roles & Permissions](../01-login-and-orgs/04-users-roles-permissions.md) | `idmc_session.py whoami --expect-org` |
| Users, roles, entitlement ("is it licensed?"), trial orgs | [Users, Roles & Permissions](../01-login-and-orgs/04-users-roles-permissions.md) | [Entitlement, Licenses & Job Caps](../13-ipu-cost/03-entitlement-licenses-job-caps.md) | `idmc_session.py get` |
| Install, size, tune, resize or reboot a Secure Agent; two agents on one host | [Secure Agent - Install, Run & Tune](../02-secure-agent/01-secure-agent-install-run-tune.md) | [Runtime Environments - Services & Connectors](../02-secure-agent/02-runtime-environments-services-connectors.md) | `idmc_runtime_selections.py` |
| Jobs queue, or concurrency never passes 2 | [Secure Agent](../02-secure-agent/01-secure-agent-install-run-tune.md) §6.2 (the DTM pool) | [Performance, Concurrency & Job Caps](../04-mappings/06-performance-concurrency-job-caps.md) §6 | (none) |
| A connection fails (test or run) | [Troubleshooting - the Four Gates](../03-connections/03-troubleshooting-the-four-gates.md) | [Connections](../03-connections/01-connections-create-test-update-delete.md), [Connector Notes](../03-connections/02-connector-notes-bigquery-postgresql-salesforce-jdbc-flat-file.md) | `idmc_session.py get` |
| Can IDMC do X headless? | [Capability Map](03-capability-map.md) | the service folder, then [Overturned Beliefs](../lessons/overturned-beliefs.md) | `idmc_probe.py` |
| A call returns an error code or a suspicious 200 | [Error Triage](04-error-triage.md) | [Evidence Discipline](../14-working-with-claude/02-evidence-discipline.md) | `idmc_probe.py twin` |
| Build or change one mapping, fast | [Mapping Fast Path](../04-mappings/00-mapping-fast-path-read-this-first.md) | `toolkit/mapgen/docs/SPEC_REFERENCE.md`, `toolkit/mapgen/examples/` | `toolkit/mapgen/mapgen.py` |
| Build a pipeline (mappings, mapping tasks, lanes), turn on pushdown | [How Claude Builds Mappings Headless](../04-mappings/02-how-claude-builds-mappings-headless.md) | [The Pipeline-Generation Pattern](../04-mappings/04-the-pipeline-generation-pattern.md), [Mapping Design & Consolidation](../04-mappings/05-mapping-design-consolidation.md) | `idmc_mttask.py`, `idmc_package_edit.py` |
| Run, schedule and monitor jobs | [Mapping Tasks](../04-mappings/03-mapping-tasks-create-update-run-monitor.md), [Taskflows & Schedules](../05-taskflows-schedules/01-taskflows-schedules.md) | [Performance, Concurrency & Job Caps](../04-mappings/06-performance-concurrency-job-caps.md) | `idmc_mttask.py run`, `idmc_taskflow_schedule.py` |
| Promise or measure a latency (per hop, per record) | [Performance, Concurrency & Job Caps](../04-mappings/06-performance-concurrency-job-caps.md) §8 | [CDC from PostgreSQL](../06-cdc-ingestion/02-cdc-from-postgresql.md) §3, [Evidence Discipline](../14-working-with-claude/02-evidence-discipline.md) §9 | (none) |
| Change a live pipeline | [Changing Pipelines Safely](../04-mappings/07-changing-pipelines-safely.md) | [Editing Packages Safely](../12-deploy-migrate/02-editing-packages-safely.md) | `idmc_mttask.py set-query` |
| Serve outputs to BI tools, CRM analytics or apps; reverse ETL | [Serving Outputs to BI and Apps](../04-mappings/09-serving-outputs-to-bi-and-apps-freshness-latency-reverse-etl.md) | [Source & Target Gotchas](../04-mappings/08-source-target-gotchas.md), [Connector Notes](../03-connections/02-connector-notes-bigquery-postgresql-salesforce-jdbc-flat-file.md) §3 | (none) |
| CDC or database ingestion | [DBMI over REST](../06-cdc-ingestion/01-dbmi-over-rest-create-deploy-run-stop.md) | [CDC from PostgreSQL](../06-cdc-ingestion/02-cdc-from-postgresql.md), [DBMI Targets & Drivers](../06-cdc-ingestion/03-dbmi-targets-drivers.md) | `idmc_dbmi.py` |
| Author, publish or invoke a CAI process | [CAI Asset Lifecycle](../07-app-integration/01-cai-asset-lifecycle-author-publish-unpublish-delete.md) | [CAI Runtime](../07-app-integration/02-cai-runtime-invoke-urls-control.md), [CAI Troubleshooting](../07-app-integration/05-cai-troubleshooting-stuck-assets.md) | `idmc_cai_publish.py` |
| Listen to Kafka or a JMS broker (AMQP) with CAI; bridge JMS to Kafka; windowed or late subscribers | [CAI Event Listeners](../07-app-integration/06-cai-event-listeners-kafka-amqp-jms.md) | [CAI Asset Lifecycle](../07-app-integration/01-cai-asset-lifecycle-author-publish-unpublish-delete.md), [Process Server on a Secure Agent](../07-app-integration/04-process-server-on-a-secure-agent.md) | (none) |
| Decide whether a flow belongs to IDMC or an API gateway; front APIs with a gateway | [CAI Runtime](../07-app-integration/02-cai-runtime-invoke-urls-control.md) §10.7-10.8 | [Capability Map](03-capability-map.md) ("Which layer owns which edge") | (none) |
| DQ rules, profiling, scorecards | [Profiling - What Is Headless](../08-data-quality/02-profiling-what-is-headless.md) | [DQ Assets](../08-data-quality/01-dq-assets-rule-specs-cleanse-dictionaries-verifiers.md), [DQ Scorecards](../08-data-quality/04-dq-scorecards-warehouse-pattern-and-data-profiling-scorecards.md), [CLAIRE DQ Agent](../08-data-quality/03-claire-dq-agent-file-based-profiling-cleansing.md) | (none yet) |
| Register and scan a catalog source | [Catalog Sources](../09-catalog-lineage/02-catalog-sources-create-scan-update-purge.md) | [CDGC APIs & Auth](../09-catalog-lineage/01-cdgc-apis-auth.md), [CDGC Gaps & Gotchas](../09-catalog-lineage/05-cdgc-gaps-gotchas.md) | `idmc_cdgc.py` |
| Glossary, term links, classification, lineage | [Glossary, Links & Classification](../09-catalog-lineage/03-glossary-links-classification.md) | [Search, Lineage & Marketplace](../09-catalog-lineage/04-search-lineage-marketplace.md) | `idmc_cdgc.py` |
| MDM records, search, models | [MDM SaaS - Runtime vs Design](../10-mdm/01-mdm-saas-runtime-vs-design.md) | [MDM Records](../10-mdm/02-mdm-records-ingest-search-export-cleanup.md), [Business 360 Modeling](../10-mdm/03-business-360-modeling-match-merge.md) | (none yet) |
| Master a table (dedupe, match, survivorship, golden-record gates) for any kind of dataset | [Mastering a Table - Repeatable Playbook](../10-mdm/05-mastering-a-table-repeatable-playbook.md) | [Business 360 Modeling](../10-mdm/03-business-360-modeling-match-merge.md) (native MDM and the CDI-mapping pipeline), [DQ Assets](../08-data-quality/01-dq-assets-rule-specs-cleanse-dictionaries-verifiers.md) | (none) |
| MCP servers, OAuth clients, agent-style MCP | [Managed MCP Servers](../11-mcp-claire/01-managed-mcp-servers-catalog-access.md) | [MCP Auth & OAuth Clients](../11-mcp-claire/02-mcp-auth-oauth-clients.md), [MCP vs REST](../11-mcp-claire/05-mcp-vs-rest-when-to-use-which.md), [Ecosystem](../11-mcp-claire/07-ecosystem-plugins-registries-community-tools.md) | `/informatica-idmc-headless:connect-mcp`, `idmc_mcp.py`, `idmc_mcp_bridge.py --check` |
| A CLAIRE GPT demo or prompt set | [CLAIRE GPT - Prompting Rules & Patterns](../11-mcp-claire/03-claire-gpt-prompting-rules-patterns.md) | [Glossary, Links & Classification](../09-catalog-lineage/03-glossary-links-classification.md) section 10 | (UI harness) |
| IPUs, metering, licences, job caps and job budgets | [IPU Model](../13-ipu-cost/01-ipu-model-mechanics.md) | [Entitlement, Licenses & Job Caps](../13-ipu-cost/03-entitlement-licenses-job-caps.md), [Metering & Consumption Exports](../13-ipu-cost/02-metering-consumption-exports.md) | `idmc_metering.py` |
| Migrate an estate to another org | [Org-to-Org Migration Runbook](../12-deploy-migrate/04-org-to-org-migration-runbook.md) | [Export & Import](../12-deploy-migrate/01-export-import-v3-migration-api.md), [Cutover & Rollback](../12-deploy-migrate/05-cutover-rollback.md) | `idmc_export_import.py` |
| Clean an org, delete objects | [Headless Deletes & Org Cleanup](../12-deploy-migrate/06-headless-deletes-org-cleanup.md) | [Identify the Org Before You Write](../01-login-and-orgs/03-identify-the-org-before-you-write.md) | `idmc_frs_delete.py` |
| A step still looks UI-only | [UI Automation with Playwright](../14-working-with-claude/04-ui-automation-with-playwright.md) (section 8: capture the UI's own call) | [The Laws](02-the-laws-of-headless-idmc.md) (law 17: the residual clicks) | (Playwright skeleton in the doc) |
| Reach the agent host (SSH, IAP hop, run-command) | [How Claude Reaches and Drives IDMC](../14-working-with-claude/01-how-claude-reaches-and-drives-idmc.md) §7 | [Environment Traps](../14-working-with-claude/05-environment-traps-windows-git-bash-az-gcloud-docker.md) | (none) |
| Several sessions on one program; an action was denied; what needs the human | [Multi-Agent Coordination](../14-working-with-claude/03-multi-agent-coordination.md) | [How Claude Reaches and Drives IDMC](../14-working-with-claude/01-how-claude-reaches-and-drives-idmc.md) | (none) |
| A secret, a key or an exposure | [Secrets Hygiene](../14-working-with-claude/06-secrets-hygiene.md) | [Environment Traps](../14-working-with-claude/05-environment-traps-windows-git-bash-az-gcloud-docker.md) | (none) |

When nothing fits: search the KB for the exact error string or path first (a grep over `*.md` and
`lessons` is the fastest route to an answer), then the [Reference Library](../reference/README.md)
for endpoint-level rows and vendor text.

## 4. Map the placeholders to your org

Placeholders stand for values you read live in your own org, at run time. Keep the values in private run notes or
environment files outside the KB (0600), never in it, and never copy an id from one org into another (L-AUTH-011).

**Procedure (about five minutes, read-only):**

1. Credentials in the environment or a 0600 file outside the KB: `IDMC_USER`, `IDMC_PASS`, `IDMC_LOGIN_HOST` (your
   domain host, `<domain>.informaticacloud.com`), and one `IDMC_PROFILE` per org
   ([Script Library](../../toolkit/lib/README.md) §2).
2. `python idmc_session.py whoami`: one guarded login; it prints the org name, `<orgIdV2>`, `<orgIdV3>`, `<pod>`,
   `<domain>` and `<serverUrl>`. `python idmc_session.py hosts` prints every derived service host.
3. `python idmc_session.py get v2 /api/v2/agent`, `/api/v2/runtimeEnvironment` and `/api/v2/connection`: the agents,
   runtime environments and connections. `GET /api/v2/agent/details/<agentId>` lists what each agent really runs.
4. From your own estate: the agent host and its OS user, install root and systemd unit; the cloud project, VM names and
   resource groups; the warehouse project and datasets.
5. Before the first write: `python idmc_session.py whoami --expect-org <orgIdV3>` must pass.

| KB placeholder | Also written as | Means | Read it from |
|---|---|---|---|
| `<domain>` | `dm-us`, `dmp-us`, `dm-em`, `dm-ap`, `dm-na`, `dm-uk` | the domain label; one character separates `dm-us` from `dmp-us`, and a borrowed URL on the wrong label fails | the host you log in at; the login answer |
| `<pod>` | | the pod label, for example `usw1` | `products[].baseApiUrl` (v3) or `serverUrl` (v2) |
| `<pod>.<domain>.informaticacloud.com` | `<pod-host>`, `<pod>.dm-us.informaticacloud.com` | the pod host; service hosts are `<pod>-<service>.<domain>.informaticacloud.com` | derived from the login answer, never typed |
| `<serverUrl>` | `<baseApiUrl>` | the v2 base `https://<pod>.<domain>.informaticacloud.com/saas` | the v2 login |
| `<orgIdV2>`, `<orgIdV3>` | `<org-id>` (the 22-character v3 id unless a doc says v2) | the org's 6-character and 22-character ids | `GET /api/v2/org` (`id`, `orgUUID`) |
| `<agentId>`, `<reId>` | `<runtime-env>`, `<re>`, `<runtime>` (the runtime environment) | a Secure Agent and its runtime environment | `GET /api/v2/agent`, `GET /api/v2/runtimeEnvironment` |
| `<connId>` | `<connection>`, `<connection-name>`, `<conn>` | a connection (v2 id or name) | `GET /api/v2/connection` |
| `<taskId>`, `<wfId>`, `<scheduleId>`, `<jobId>`, `<runId>`, `<entryId>` | | v2 mapping task, workflow and schedule ids; DBMI job ids; run ids; an activity-log row's `id` | the v2 lists, `task/details` on `<pod>-ing`, the activity log |
| `<frsGuid>`, `<frsId>`, `<identity>`, `<externalId>`, `<csId>` | | 22-character repository GUIDs; CDGC asset identity and external id; catalog-source id | v2 details, `/public/core/v3/objects`, catalog search |
| `<tenant>`, `<Process>`, `<ProcessApiName>` | | the CAI tenant (`<orgIdV3>` in anonymous URLs) and process names | `GET /active-bpel/rt` |
| `<project>`, `<folder>` | `<project>/<folder>` | an Explore location | `GET /public/core/v3/objects` |
| `<agent_home>`, `<agentuser>`, `<unit>`, `<agent-slice>` | `<agent_user>`, `<agent_service>`; `<secure-agent-host>` is the host itself | the agent's install root, OS user, systemd unit and cgroup slice | the host |
| `<vm-name>`, `<resource-group>`, `<cloud-project>`, `<zone>` | | your cloud estate | your cloud CLI or console |
| `<warehouse-dataset>`, `<dataset>`, `<schema>`, `<table>` | `<cdc_dataset>`, `<golden_table>` | warehouse and database objects | your warehouse |
| `<be>`, `<runtimeId>` | | an MDM business entity and its runtime id (for example `c360.person`) | the MDM model |
| `<user>`, `<user>@example.com` | | an IDMC login, or any person | your identity provider |
| `<sessionId>`, `<sid>`, `<jwt>` | | session values and tokens | read at run time; never written down |

## 5. The safety rules every session follows

| # | Rule | Where it is argued |
|---|---|---|
| 1 | Prove the org from a live read before anything else; assert it in code before every write | Law 1, law 25; [Identify the Org](../01-login-and-orgs/03-identify-the-org-before-you-write.md) |
| 2 | Take every host and header from the login answer and the plane map | Laws 2 and 3; [Pods, Hosts & Service Planes](../01-login-and-orgs/01-pods-hosts-service-planes.md) |
| 3 | Read the body, bogus-twin anything surprising, read back every write | Laws 4, 5 and 12 |
| 4 | One designated session, one login attempt, a shared cache, a block file per org | Law 24; [Login, Sessions & Tokens](../01-login-and-orgs/02-login-sessions-tokens.md) §7 |
| 5 | Dry run by default; destructive calls take an explicit id list, a backup and a receipt line | Law 25; [Headless Deletes](../12-deploy-migrate/06-headless-deletes-org-cleanup.md) |
| 6 | Runs, previews, scans and profiles are spend; get approval; count jobs yourself | Laws 26 and 29 |
| 7 | A permission denial covers the outcome: never route around it; ask once, naming the action and its rollback | Law 25; [Multi-Agent Coordination](../14-working-with-claude/03-multi-agent-coordination.md) §4 |
| 8 | Never empty-POST an id-bearing action route, never prune an agent's `downloads/`, never drop a live replication slot | Laws 8 and 23; [Secure Agent](../02-secure-agent/01-secure-agent-install-run-tune.md) §6; [CDC from PostgreSQL](../06-cdc-ingestion/02-cdc-from-postgresql.md) §4 |
| 9 | Change live pipelines side by side, behind a swap gate | Law 28; [Changing Pipelines Safely](../04-mappings/07-changing-pipelines-safely.md) |
| 10 | Secrets are read at run time, printed by name only, and rotated once exposed | Law 30; [Secrets Hygiene](../14-working-with-claude/06-secrets-hygiene.md) |

## 6. How every doc is built, and how to read it

- **The opening block**, right under the title:
  - **Answers:** the questions the doc answers. If yours is not there, use §3 to find the right doc.
  - **Read when:** the situations that should send you to it.
  - **Key rules:** three to seven rules, each ending with the lesson ids that prove it.
  - **Related:** two to five neighbouring docs.
  - **Last verified:** the date the doc was last checked against the current lessons, with the date range of its
    evidence in brackets. Anything older than the newest overturn in its area may be stale; check
    [Overturned Beliefs](../lessons/overturned-beliefs.md).
- **A short summary** under the block, for readers who stop there.
- **Procedures** as numbered steps with the exact call (`METHOD /path`, the headers, a minimal body, the expected
  answer), then the failure modes ("if you get X: cause, fix"). **Decisions** as small tables.
- **Lesson citations** such as `(L-CDI-050, 2026-09-29)`: the stable id of the lesson that proves the sentence and,
  where given, the date it was proven. The full text is in the domain's lessons file in `lessons`.
- **An "Overturned beliefs" table** near the end of most docs: what used to be believed, until when, and what replaced
  it. Never quote a wall without checking it there first.

## 7. Evidence states

Four states, never merged (a blank cell means untested, not absent):

| State | Written as | Means | Never |
|---|---|---|---|
| WORKS | "proven <date>" | a live status and body were observed on a stated date (in some org, on some pod) | assume it holds on another org or pod without a re-probe |
| DOC | "documented" or "documented, unproven" | a named Informatica guide says so; nobody exercised it | report it as working |
| REJECTED | "rejected (<code>)" | the platform refused it with a code; `405` means the verb does not exist at any permission level | read a 404 as a rejection before a host sweep |
| UNTESTED | "untested" | nobody has checked | call it "unsupported" or a limitation |

Two more labels appear: **disputed** (two dated records disagree; the doc says which to trust) and **superseded**
(an older belief kept only so nobody re-learns it). For "can this run headless?" the docs also use six verdicts:
HEADLESS, HEADLESS-DOC, NEEDS SHELL (no browser, but a host shell), UI-ONLY (entitled and working; a human clicks),
UNTESTED, WRONG-HOST RISK (recorded absent, but the host family was never swept). UI-ONLY is never a GAP: it is one
click in something the org already owns. Details: [Evidence Discipline](../14-working-with-claude/02-evidence-discipline.md).

**Latest dated evidence wins.** When two lessons disagree, the newer proven one is current and the older one is kept
as superseded. A proof from one org or pod is evidence for that org or pod only.

## 8. Scope: generic only

| | Holds | Rule |
|---|---|---|
| **This KB** (folders `00`–`14`) | Generic IDMC knowledge: planes and hosts, routes, bodies, error codes, walls, processes, timings, limits, lessons, scripts | Names no customer, application, person, org, org id, agent or object id, VM, IP, internal host, cloud project or tracker key. Examples use the placeholders of §4. Numbers without names are fine |
| **Kept outside it** | Deployment-specific material: which org is which, ids, hosts, agents, application names and status, tracker history, org-specific scripts and evidence | Never linked from here; nothing in this KB depends on it |

The scope rule is enforced by `toolkit/tools/secret_scan.py`, which runs in a pre-commit hook and in CI and must print
CLEAN. Lesson provenance (which tracker issue, note or document proved a lesson) stays with your own deployment
material, never in the plugin.

## 9. How to update the KB

- **Using the plugin:** save what you learn with `/informatica-idmc-headless:save-lesson`. It goes to `~/.idmc_toolkit/lessons-local.jsonl`
  on your computer, which the skills search next time; the plugin folder is replaced on every update, so never edit it.
- **Contributing to the shared KB:** follow [CONTRIBUTING.md](../../.github/CONTRIBUTING.md): search first, write the lesson
  generically (placeholders, numbers without names, never a secret), keep overturned beliefs as superseded lessons, run
  the tools it lists (counts, error index, tests, secret scan), and open a pull request or an issue.

## 10. The lesson ID scheme

Every lesson has a stable id `L-<DOM>-<NNN>`. Ids are never renumbered or reused; a new lesson takes the next free
number of its prefix, whichever section it lands in.

| Prefix | Domain | Lessons file |
|---|---|---|
| `AUTH` | planes, hosts, logins, sessions, org identity, users and roles | [01 Access & Auth](../01-login-and-orgs/lessons.md) |
| `AGENT`, `CONN` | Secure Agent and runtime environments; connections and connectors | [02 Secure Agent](../02-secure-agent/lessons.md), [03 Connections](../03-connections/lessons.md) |
| `CDI` | mappings, mapping tasks, taskflows, schedules, pipelines | [04 Mappings](../04-mappings/lessons.md), [05 Taskflows & Schedules](../05-taskflows-schedules/lessons.md) |
| `DBMI` | Database Ingestion and CDC | [04 Mass Ingestion & CDC](../06-cdc-ingestion/lessons.md) |
| `CAI` | Application Integration | [05 Application Integration (CAI)](../07-app-integration/lessons.md) |
| `DQ` | Data Quality and profiling | [06 Data Quality & Profiling](../08-data-quality/lessons.md) |
| `CDGC` | catalog, governance, marketplace | [07 Catalog & Governance (CDGC)](../09-catalog-lineage/lessons.md) |
| `MDM` | MDM SaaS, Business 360, P360 | [08 MDM](../10-mdm/lessons.md) |
| `MCP` | CLAIRE, CLAIRE GPT, managed and custom MCP | [09 CLAIRE & MCP](../11-mcp-claire/lessons.md) |
| `MIG`, `CLEAN` | export/import, packages, org-to-org migration; deletes and org cleanup | [10 Migration & Org Management](../12-deploy-migrate/lessons.md) |
| `IPU` | IPUs, metering, licences, entitlement, job caps | [11 IPU, Metering & Licensing](../13-ipu-cost/lessons.md) |
| `METHOD` | how Claude works: evidence, coordination, gates | [12 Claude Working Methods](../14-working-with-claude/lessons.md) |
| `ENV` | workstation, shells, cloud CLIs, hosts, Docker, and the BI and gateway tools next to IDMC | [13 Environment & Ops](../14-working-with-claude/lessons-environment-ops.md) |
| `UI` | browser automation of the IDMC console | [14 UI Automation](../14-working-with-claude/lessons-ui-automation.md) |

Each lesson has a kind (LAW, GOTCHA, RECIPE, ROUTE, ERROR, WALL, WORKAROUND, OVERTURNED, PROCESS, DECISION, PERF,
PATTERN, SECURITY; a few older lessons carry WORKS, FACT, PROBE or FIX) and a status (current, superseded, disputed).
The file-by-file counts and the lesson template are in the
[Lessons Learned README](../lessons/README.md).
