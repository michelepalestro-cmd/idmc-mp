# IDMC MP knowledge base

> Setup (install, connect, troubleshooting) is in the root [README](../README.md). Paths in inline code
> (`knowledge/...`, `lessons/...`, `toolkit/...`) are relative to the plugin root.

**Answers:** What is this knowledge base, how should a Claude session read it, how do its placeholders map onto your own
IDMC org, which safety rules apply to every session, and where is each kind of question answered?

**Read when:** first, in every new session, project or org that uses this KB; again whenever you are unsure where an
answer lives.

**Key rules:**
- Build on the user's own systems and never push another technology; never say "not possible" before the
  workaround ladder has been worked in the org ([New Pipeline Milestones](00-start-here/08-new-pipeline-milestones-any-source-any-target.md)).
- Prove which org you are in before anything else, and work in one org per session (L-AUTH-046, L-AUTH-047).
- Take the host and header from the plane map, read the body rather than the status, and read back every write
  (L-AUTH-001, L-METHOD-025, L-METHOD-030).
- One login attempt, one shared session cache, a block file on rejection: rejected logins from every session add up to
  one lockout (L-AUTH-036, L-AUTH-041).
- Writes are dry runs until an org guard passes; runs, scans and previews are spend and need approval (L-METHOD-065,
  L-IPU-005).
- A wall is a dated verdict: check the Capability Map and Overturned Beliefs, then re-probe in your own org
  (L-METHOD-034, L-METHOD-035).
- Never write a secret, or an id or host of your own org, into this KB (L-METHOD-001).

**Related:** [Quick Start](00-start-here/10-quick-start-your-first-hour-with-idmc-and-claude.md) · [How to use this KB](00-start-here/01-how-to-use-this-kb.md) ·
[The Laws of Headless IDMC](00-start-here/02-the-laws-of-headless-idmc.md) ·
[End-to-End Playbook](00-start-here/07-end-to-end-playbook-deploy-and-operate-idmc-with-claude.md) ·
[Capability Map](00-start-here/03-capability-map.md) · [Error Triage](00-start-here/04-error-triage.md)

**Last verified:** 2026-11-17

## What this KB is for

**A working kit for building on Informatica IDMC with Claude.** Install it, point Claude at it, sign in to your IDMC
org once, and create IDMC assets without the UI: connections to any database, cloud, file store or application that
IDMC supports, runtime environments, projects and folders, mappings and mapping tasks, taskflows and schedules, CDC and
file ingestion, CAI processes, data quality rules and profiles, catalog sources, glossary, classification and lineage,
MDM, MCP. Everything in it comes from real IDMC builds: the calls that work, the errors and their fixes, and the order
of work that gets an asset running fast.

It is **guidance**. Use as much or as little as you like: follow the milestones, jump straight to one asset, or work
your own way. Your systems, your naming and your order of work are always the right ones.

### Quick start (about 15 minutes)

| Step | Do | Detail |
|---|---|---|
| 1. Install | Install the `idmc-mp` plugin in Claude Code (the repo README), or clone the repository and run `git config core.hooksPath toolkit/tools/git-hooks` once so no commit can carry a secret. You need Python 3.10+ (standard library only) and Claude Code | `python3 toolkit/setup/check_setup.py` checks the PC offline ([toolkit/setup/SETUP.md](../toolkit/setup/SETUP.md)) |
| 2. Point Claude at it | With the plugin installed, the `idmc-mp` skills load on their own for IDMC work (`skills/`); the rules for any session are in [RULES.md](RULES.md) | [Claude Working Methods](14-working-with-claude/01-how-claude-reaches-and-drives-idmc.md) |
| 3. Sign in | `/idmc-mp:connect`, then `python3 toolkit/check_login.py --setup` in a terminal (three questions; the password stays hidden). One login, it prints your org | the root [README](../README.md#setup-in-3-steps-about-10-minutes) |
| 4. Build | Ask Claude for what you need, in your own words: "create a connection to <system>", "build a nightly pipeline from <source> to <target>", "add a data quality rule", "scan this source into the catalog and show lineage" | the table below; [New Pipeline Milestones](00-start-here/08-new-pipeline-milestones-any-source-any-target.md) for a whole pipeline |

### Create any IDMC asset: where to start

| You want to create | Start here | How it is done without the UI |
|---|---|---|
| A login session, and proof of which org you are in | [Login, Sessions & Tokens](01-login-and-orgs/02-login-sessions-tokens.md), [Identify the Org](01-login-and-orgs/03-identify-the-org-before-you-write.md) | `python3 toolkit/check_login.py` (one attempt, cached session, lockout guard) |
| Users, roles, permissions | [Users, Roles & Permissions](01-login-and-orgs/04-users-roles-permissions.md) | v3 users / roles, object permissions |
| A Secure Agent, a runtime environment, its services and connectors | [Secure Agent](02-secure-agent/01-secure-agent-install-run-tune.md), [Runtime Environments](02-secure-agent/02-runtime-environments-services-connectors.md) | install token + `configureToken`; runtime selections (`idmc_runtime_selections.py`) |
| A connection to any database, cloud, file store or application | [Connections](03-connections/01-connections-create-test-update-delete.md), [Connector Notes](03-connections/02-connector-notes-bigquery-postgresql-salesforce-jdbc-flat-file.md); a connector with no notes: [Milestones](00-start-here/08-new-pipeline-milestones-any-source-any-target.md) M2 | `POST /api/v2/connection` (`TOOLKIT_CCI` + the connector's `instanceName`), then a free `connection/test` |
| A project or folder | [Milestones](00-start-here/08-new-pipeline-milestones-any-source-any-target.md) M3 | `POST /public/core/v3/projects`, then its folders; move assets with FRS `MoveEntities` |
| A mapping, with any transformations | [Mapping Fast Path](04-mappings/00-mapping-fast-path-read-this-first.md) | a JSON spec → `toolkit/mapgen` lint → v3 import package |
| A mapping task | [Mapping Tasks](04-mappings/03-mapping-tasks-create-update-run-monitor.md) | the generator's `deploy`, or `POST /api/v2/mttask` |
| A taskflow or a schedule | [Taskflows & Schedules](05-taskflows-schedules/01-taskflows-schedules.md) | `idmc_taskflow_schedule.py` |
| A whole pipeline (many mappings, lanes, pushdown) | [How Claude Builds Mappings Headless](04-mappings/02-how-claude-builds-mappings-headless.md), [The Pipeline-Generation Pattern](04-mappings/04-the-pipeline-generation-pattern.md) | generated, consolidated mappings behind a swap gate |
| A CDC / database ingestion task | [DBMI over REST](06-cdc-ingestion/01-dbmi-over-rest-create-deploy-run-stop.md) | `idmc_dbmi.py` on the `-ing` service host |
| A file ingestion task | [Mass Ingestion & CDC](06-cdc-ingestion/) (lessons L-DBMI-060 to L-DBMI-062) | `POST /mftsaas/api/v1/mitasks`, then `job` |
| A CAI process, app connection or service connector | [CAI Asset Lifecycle](07-app-integration/01-cai-asset-lifecycle-author-publish-unpublish-delete.md), [CAI Connections](07-app-integration/03-cai-connections-connectors-salesforce-oauth.md) | import package + publish (`idmc_cai_publish.py`) |
| A Kafka or JMS event listener | [CAI Event Listeners](07-app-integration/06-cai-event-listeners-kafka-amqp-jms.md) | listener + process, published |
| A data quality rule, cleanse, dictionary or verifier | [DQ Assets](08-data-quality/01-dq-assets-rule-specs-cleanse-dictionaries-verifiers.md) | clone-authored assets, run inside a mapping |
| Address verification and enrichment (verify, standardize, geocode, CASS) | [DQ Assets](08-data-quality/01-dq-assets-rule-specs-cleanse-dictionaries-verifiers.md) §6 | an on-agent Verifier asset in a mapping (the generator's `verifier` node), or the cloud Address Verification REST service (Certified mode for CASS) |
| A data profile | [Profiling](08-data-quality/02-profiling-what-is-headless.md) | the profiling service REST API |
| A catalog source and its scan | [Catalog Sources](09-catalog-lineage/02-catalog-sources-create-scan-update-purge.md) | `idmc_cdgc.py` |
| Glossary terms, links, classifications | [Glossary, Links & Classification](09-catalog-lineage/03-glossary-links-classification.md) | CDGC content API |
| Lineage (scanned and curated) | [Search, Lineage & Marketplace](09-catalog-lineage/04-search-lineage-marketplace.md) | catalog scans + curated edges |
| MDM business entities, records, a mastered table | [Business 360 Modeling](10-mdm/03-business-360-modeling-match-merge.md), [MDM Records](10-mdm/02-mdm-records-ingest-search-export-cleanup.md), [Mastering a Table](10-mdm/05-mastering-a-table-repeatable-playbook.md) | MDM APIs, or CDI mappings that master a table |
| MCP access, CLAIRE GPT prompts | [Managed MCP Servers](11-mcp-claire/01-managed-mcp-servers-catalog-access.md), [CLAIRE GPT](11-mcp-claire/03-claire-gpt-prompting-rules-patterns.md) | managed MCP + OAuth clients |
| A copy, a move, an export / import, a clone of any asset | [Export & Import](12-deploy-migrate/01-export-import-v3-migration-api.md), [Migration-Clone Authoring](12-deploy-migrate/03-migration-clone-authoring.md) | v3 export / import packages; FRS `CopyEntities` / `MoveEntities` |
| **Anything not in this table** | [Milestones](00-start-here/08-new-pipeline-milestones-any-source-any-target.md): "A system or connector the KB has never seen" and the workaround ladder | the closest pattern here, adapted and proven in your org, then recorded as a lesson |

## About this knowledge base

A knowledge base about Informatica IDMC (Intelligent Data Management Cloud), written for Claude sessions and the people
who work with them. It explains how IDMC really behaves when it is driven without its UI: the routes, hosts, headers,
bodies and error codes; what each wall turned into when it was tested; how mappings, pipelines, CDC, CAI, data quality,
catalog, MDM and MCP work are built and operated; and more than 2,300 dated lessons, each with its evidence. It is
**generic**: nothing in it belongs to one org, so it works in yours once you map its placeholders to your own values.

Use it as a Claude project's knowledge base or as a folder the session can read. If you build IDMC skills or agents of
your own, make each one start by reading this KB: a skill built from an older snapshot does not carry later lessons
(L-METHOD-084).

It is also a working kit: the plugin holds the Python library the KB describes, a headless mapping generator, the
Claude Code skills and three ready-to-rebuild demo blueprints.

> **The goal:** help you deploy IDMC end to end, with every capability you ask for, on the systems you already have.
> Two rules every Claude session using this KB follows:
> 1. **It never pushes you to another technology.** No "use BigQuery / Snowflake instead". A system the KB has never
>    covered (SAP, Oracle, files, an API...) is built brand new with everything the KB has learned.
> 2. **It never says "not possible", and never treats something as forbidden because the KB does not mention it.**
>    The KB is not an allow-list: anything IDMC can do is in scope. Before any "no" it works the workaround ladder in
>    your org, native IDMC first and Python only when no IDMC path works: the lessons, a re-probe,
>    another API plane, cloning a UI-made object, capturing the UI's own call, another IDMC component, a Python bridge,
>    and only then one residual manual step
>    ([New Pipeline Milestones](00-start-here/08-new-pipeline-milestones-any-source-any-target.md), "The goal and the two rules").
>
> **Guidance, not a script. Bring any source and any target.**
> This KB is a field guide, not a reference architecture. Its examples use the systems its builds happened to use
> (PostgreSQL, BigQuery, Snowflake, Databricks, Salesforce, SharePoint, ClickHouse, Tableau, flat files). Those are
> examples, **not recommendations**: IDMC connects to hundreds of systems, and yours are the right ones for your
> pipeline. Take the KB's order of work, its gates, its safety rules and its evidence on how IDMC behaves. Do not take
> its choice of systems, object names or settings as-is. When your connector or source is not covered, the KB tells
> you how to find out (read the connector's metadata, prove one small run, record a lesson), and that is the expected
> path, not a failure. Lessons are dated evidence from particular orgs and releases: your own org's live answer wins.
>
> **Starting a new pipeline?** Work the milestones in order:
> [New Pipeline Milestones](00-start-here/08-new-pipeline-milestones-any-source-any-target.md): (1) identify the
> Secure Agent / runtime, (2) identify the connections, (3) identify or create the folder and list the assets that go
> in it, then the data contract, the mapping, the task, the first run and its proof, DQ, orchestration and governance.

## 0. Connect to your IDMC org

Follow the 3 steps in the root [README](../README.md#setup-in-3-steps-about-10-minutes): install the plugin, run
`/idmc-mp:connect`, answer three questions with `python3 toolkit/check_login.py --setup`. Your login lives in
`~/.idmc_toolkit/IDMC_LOGIN.txt`, outside the plugin, readable only by you. Every login message is explained in the
README's [troubleshooting table](../README.md#if-the-login-doesnt-work).

### What else is in the folder

| Path | What it is |
|---|---|
| `knowledge/00-start-here` ... `knowledge/14-working-with-claude` | The knowledge base (the map is in §5) |
| [`lessons/`](../lessons/README.md) | Every field lesson: `lessons.jsonl` (every lesson, for searching; the readable copies sit in each job folder as `lessons.md`), `overturned-beliefs.md` |
| `~/.idmc_toolkit/IDMC_LOGIN.txt`, `toolkit/check_login.py` | **Your IDMC login** (the only file you fill in to connect) and the one-command login check |
| [`toolkit/lib/`](../toolkit/lib/README.md) | The Python library (stdlib only): login with lockout guard, org proof, objects, export/import, package edits, mapping tasks, taskflows and schedules, CDC (Database Ingestion), CAI publish, catalog, MCP |
| [`toolkit/mapgen/`](../toolkit/mapgen/README.md) | The headless mapping generator: a mapping spec (JSON / Python) -> IDMC mapping -> importable package (stdlib only) |
| [`toolkit/demos/`](../toolkit/demos/BLUEPRINT_CONVENTIONS.md) | Three blueprints; each has `README.md` (what and why) and `BUILD.md` (numbered rebuild, gotchas, UI-only walls) |
| `skills/`, [`playbook/`](reference/playbook/00-headless-playbook.md) | The Claude Code skills (`idmc-mp` core plus one per area) and the compact headless playbook |
| [`toolkit/setup/`](../toolkit/setup/SETUP.md) | `SETUP.md` (new-PC guide), `.env.example` (the blueprints' other credential keys, no values), `check_setup.py` |
| `toolkit/tools/secret_scan.py` | Run before you share your copy: must print CLEAN |
| [`RULES.md`](RULES.md) | The rules any Claude session follows with this KB |

### The three blueprints

| Blueprint | What it shows | IDMC services | Rebuild |
|---|---|---|---|
| [`retail_data_foundation`](../toolkit/demos/retail_data_foundation/README.md) (`rdf_`) | A multi-store retailer's whole data layer: Postgres -> CDC -> BigQuery, consolidated mappings to a golden customer record, DQ scorecard, reverse ETL to Postgres and Salesforce (batch and real time), catalog with glossary, classification and lineage | CDC (Database Ingestion), CDI, CAI, CDQ / Profiling, CDGC, address verification | 2-3 h first time |
| [`bid_desk_document_parsing`](../toolkit/demos/bid_desk_document_parsing/README.md) (`bid_`) | Bid documents attached in the CRM -> SharePoint -> CLAIRE document parsing -> DQ rules -> a bid-readiness decision -> Snowflake -> one Tableau workbook (6 tabs); Run / What-if / Reset loop | CDI, CLAIRE parsing (Structure Parser), CDQ, CDGC, taskflows | about half a day |
| [`message_bus_kafka_cai`](../toolkit/demos/message_bus_kafka_cai/README.md) (`mbr_`) | A legacy JMS retail integration bus replaced by Kafka + CAI: subscribers, validate / transform / route, retry with backoff, error queue, dead-letter and replay, JMS-to-Kafka bridge, nightly CDI batch to Oracle | CAI (Kafka / AMQP listeners, processes), CDI | 2-3 h |

The blueprints name concrete systems only so that they can be rebuilt end to end as written. They are not a
recommended stack: to build the same pattern on your own systems, keep each blueprint's stages and gates and swap the
connections (the [New Pipeline Milestones](00-start-here/08-new-pipeline-milestones-any-source-any-target.md)
show how for a connector the KB has not covered).

Each step in each `BUILD.md` is marked **PROVEN** (worked end to end in a real org, in an earlier non-generic form) or
**ADAPTED** (rewritten generically, checked offline only). Expect to fix a few ADAPTED steps on the first run.

### The rebuild path

1. **Set up the PC**: connect (§0), then follow [`toolkit/setup/SETUP.md`](../toolkit/setup/SETUP.md) §5 for the demos
   (`python3 toolkit/setup/check_setup.py --demo <name>` until READY).
2. **Read the laws**: [The Laws of Headless IDMC](00-start-here/02-the-laws-of-headless-idmc.md): thirty rules that
   override REST instincts (a 200 can be fake, logins are scarce, read back every write).
3. **Prove the org**: `python3 toolkit/check_login.py` (one login; note the `orgIdV3`).
4. **Pick a blueprint**: `python toolkit/setup/check_setup.py --demo <name>`, copy its `config.example.json` to `config.json`,
   fill it in, then work through its `BUILD.md`. Every write is a dry run until `--execute --expect-org <orgIdV3>`.
5. **When something fails**: [Error Triage](00-start-here/04-error-triage.md), then
   `grep -i "<error code or object>" lessons/lessons.jsonl`.

With Claude Code and the plugin installed, ask, for example, *"set up this PC, then rebuild the message bus blueprint
in my org, dry run first"*. The skills and [RULES.md](RULES.md) make it follow the same rules. **Cost:** building is free; every
task or taskflow run, catalog scan and profile run is a job and uses IPUs. The blueprints never start a run, a schedule
or a loop unless you ask.

## 1. Start here: the read order

| Step | Read | What you get | Time |
|---|---|---|---|
| 0 | [Quick Start](00-start-here/10-quick-start-your-first-hour-with-idmc-and-claude.md) if you are new: connect, prove the org, what to ask Claude for each task, the lessons that bite first | a working org in the first hour | 10 min |
| 1 | [How to use this KB](00-start-here/01-how-to-use-this-kb.md) | the routing table, the placeholders, the evidence states, how each doc is built | 10 min |
| 2 | [The Laws of Headless IDMC](00-start-here/02-the-laws-of-headless-idmc.md) | the 30 rules that most change outcomes, each with its test | 15 min |
| 3 | [New Pipeline Milestones](00-start-here/08-new-pipeline-milestones-any-source-any-target.md) for one new pipeline; the [End-to-End Playbook](00-start-here/07-end-to-end-playbook-deploy-and-operate-idmc-with-claude.md) when you build or extend a deployment; the [Capability Map](00-start-here/03-capability-map.md) when the question is "can I do X headless?" | the order of work and its gates; the dated verdict per operation | 10 min |
| 3b | [What Went Wrong](00-start-here/09-what-went-wrong-production-deployment-post-mortem.md) before you take IDMC onto a live production database or inherit someone else's build | the failures of a real production deployment, each with the check that catches it | 10 min |
| 4 | The topic doc for your task (the routing table in step 1) | the 400-level detail: calls, bodies, failure modes, measured numbers | as needed |
| 5 | [Error Triage](00-start-here/04-error-triage.md) whenever a call fails or succeeds suspiciously | the real cause and the fix per code or message | as needed |
| 6 | [Lessons Learned](../lessons/README.md) and [Overturned Beliefs](../lessons/overturned-beliefs.md) | the evidence behind any claim, and what used to be believed | as needed |

Every topic doc opens with the same block: **Answers** (the questions it answers), **Read when**, **Key rules** (each
with its lesson ids), **Related** and **Last verified**. Read that block first; it tells you whether the doc is the
right one.

## 2. Map the KB onto your org

Every org-specific value is written as a placeholder: `<pod>`, `<domain>` (so a pod host is
`<pod>.<domain>.informaticacloud.com`, for example on the `dm-us` label), `<orgIdV3>` (the org id), `<reId>` (a runtime
environment), `<connId>` (a connection), `<agent_home>`, `<cloud-project>`, `<warehouse-dataset>` and so on. Read the
values live from your org at run time, keep them in private run notes outside the KB, and never copy an id from one org
into another.

1. Connect (§0). The [toolkit library](../toolkit/lib/README.md) reads `~/.idmc_toolkit/IDMC_LOGIN.txt` by itself
   (`IDMC_USER`, `IDMC_PASS`, `IDMC_LOGIN_HOST` = your browser address). To work in several orgs, keep one 0600 file
   per org outside the plugin and point `IDMC_CREDS_FILE` at it: it wins over the default file.
2. Run `python3 toolkit/check_login.py` (= `idmc_session.py whoami`): it logs in once and prints the org name, both org id
   shapes, the pod, the domain label and the base URL.
3. Read the agents, runtime environments and connections: `python3 toolkit/lib/idmc_session.py get v2 /api/v2/agent`, then
   `/api/v2/runtimeEnvironment` and `/api/v2/connection`.
4. Fill the rest from your own estate: the agent host, its OS user and install root, the cloud project, the warehouse
   datasets.

The full placeholder table, with the other spellings you may meet, is in
[How to use this KB](00-start-here/01-how-to-use-this-kb.md) §4.

## 3. The safety rules in one screen

1. **Org first.** Derive the org from the login every session; assert it in code before every write (laws 1 and 25).
2. **Plane map.** Every host and header comes from the login answer and the plane table, never from a guess (laws 2 and 3).
3. **Distrust 200s.** Read the body and read back every write; bogus-twin anything surprising (laws 4, 5 and 12).
4. **Logins are scarce.** One designated session, one attempt, a shared cache, a block file per org (law 24).
5. **Dry run by default.** A script writes only with `--execute --expect-org <orgIdV3>`; a destructive call takes an
   explicit id list, a backup and a receipt line (law 25).
6. **Spend needs approval.** Runs, previews, scans and profiles are metered; the monthly job cap is invisible, so count
   jobs yourself (laws 26 and 29).
7. **A denial covers the outcome.** Never re-attempt a denied action in pieces, through another tool or another session
   (law 25).
8. **Walls are dated.** Search the KB first, re-probe in your org, and record what you find as a lesson (laws 9 and 17).
9. **Secrets** are read at run time, printed by name only, and rotated once exposed (law 30).

## 4. Where each kind of question is answered

| Question | Go to |
|---|---|
| Can IDMC do X without the UI? | [Capability Map](00-start-here/03-capability-map.md), then the service folder, then [Overturned Beliefs](../lessons/overturned-beliefs.md) |
| I need a new pipeline: where do I start, and what must be done before I build? | [New Pipeline Milestones](00-start-here/08-new-pipeline-milestones-any-source-any-target.md): runtime, connections, folder and assets, then build, run, prove |
| My source, target or connector is not in the KB | [New Pipeline Milestones](00-start-here/08-new-pipeline-milestones-any-source-any-target.md), "Using this KB as guidance"; [Mapping Fast Path](04-mappings/00-mapping-fast-path-read-this-first.md) §2 and §7 |
| What goes wrong on a live production deployment, and how do I avoid it? | [What Went Wrong: a Production Deployment Post-Mortem](00-start-here/09-what-went-wrong-production-deployment-post-mortem.md) |
| In which order do I stand up or extend a deployment? | [End-to-End Playbook](00-start-here/07-end-to-end-playbook-deploy-and-operate-idmc-with-claude.md) |
| This call or run failed: why? | [Error Triage](00-start-here/04-error-triage.md); for agent and connection failures [the Four Gates](03-connections/03-troubleshooting-the-four-gates.md) |
| Which host, header or login? | [Pods, Hosts & Service Planes](01-login-and-orgs/01-pods-hosts-service-planes.md), [Login, Sessions & Tokens](01-login-and-orgs/02-login-sessions-tokens.md) |
| Install, size, tune, resize or reboot a Secure Agent | [Secure Agent - Install, Run & Tune](02-secure-agent/01-secure-agent-install-run-tune.md) |
| Build or change a mapping (start here) | [Mapping Fast Path](04-mappings/00-mapping-fast-path-read-this-first.md): ten commands, per-connector settings, costly errors |
| Build or change a pipeline | [How Claude Builds Mappings Headless](04-mappings/02-how-claude-builds-mappings-headless.md), then [Changing Pipelines Safely](04-mappings/07-changing-pipelines-safely.md) |
| Speed, concurrency, latency, job caps | [Performance, Concurrency & Job Caps](04-mappings/06-performance-concurrency-job-caps.md), [Entitlement, Licenses & Job Caps](13-ipu-cost/03-entitlement-licenses-job-caps.md) |
| Serve outputs to BI tools, CRM analytics or apps | [Serving Outputs to BI and Apps](04-mappings/09-serving-outputs-to-bi-and-apps-freshness-latency-reverse-etl.md) |
| Event-driven CAI: listen to Kafka or a JMS broker, bridge JMS to Kafka, windowed subscribers | [CAI Event Listeners](07-app-integration/06-cai-event-listeners-kafka-amqp-jms.md) |
| Which layer owns a flow: IDMC or an API gateway? | [CAI Runtime](07-app-integration/02-cai-runtime-invoke-urls-control.md) §10.7 and the [Capability Map](00-start-here/03-capability-map.md) |
| What does this term mean? | [Glossary](00-start-here/05-glossary.md) |
| What proved this claim, and when? | the lesson id in the text, in [Lessons Learned](../lessons/README.md) |
| How should Claude sessions work on IDMC (evidence, coordination, approvals, secrets)? | [Claude Working Methods & Tooling](14-working-with-claude/01-how-claude-reaches-and-drives-idmc.md) |

## 5. The map

| Folder | Read it when you need to… |
|---|---|
| [`knowledge/00-start-here`](00-start-here/) | orient yourself: how to use this KB, **the laws of headless IDMC**, the capability map ("can I do X headless?"), error triage, the glossary, the changelog, the **end-to-end playbook** and **what went wrong** in a production deployment |
| [`knowledge/01-login-and-orgs`](01-login-and-orgs/) | log in, pick the right host and header for a service, handle session expiry, lockouts and the JWT change, prove which org you are in before writing, manage users, roles and entitlement reads |
| [`knowledge/02-secure-agent`](02-secure-agent/) | install, size, tune, resize or reboot a Secure Agent, enable services and connectors headless, create/test/update connections, fix "the connection is broken" |
| [`knowledge/04-mappings`](04-mappings/) | understand mappings vs mapping tasks vs templates, **build mappings and whole pipelines headless** (including pushdown), run and monitor jobs, taskflows, schedules, consolidation, performance and job caps, and **serve outputs to BI and apps** ([10 Serving Outputs to BI and Apps](04-mappings/09-serving-outputs-to-bi-and-apps-freshness-latency-reverse-etl.md)) |
| [`knowledge/06-cdc-ingestion`](06-cdc-ingestion/) | create/deploy/run DBMI tasks over REST, set up PostgreSQL CDC, measure CDC latency |
| [`knowledge/07-app-integration`](07-app-integration/) | author, publish, unpublish and invoke CAI processes, run a Process Server on an agent, split work between CAI and an API gateway |
| [`knowledge/08-data-quality`](08-data-quality/) | DQ assets, profiling, the CLAIRE DQ agent's file-based route, DQ scorecards |
| [`knowledge/09-catalog-lineage`](09-catalog-lineage/) | catalog sources and scans, glossary, links, classification, search, lineage, marketplace |
| [`knowledge/10-mdm`](10-mdm/) | MDM SaaS runtime vs design, records, Business 360; the repeatable playbook for mastering any table |
| [`knowledge/11-mcp-claire`](11-mcp-claire/) | the managed MCP servers, MCP OAuth clients, CLAIRE GPT prompting, agent-style MCP, the plugin and community-tool ecosystem |
| [`knowledge/12-deploy-migrate`](12-deploy-migrate/) | v3 export/import, editing packages, clone-authoring, **org-to-org migration and cutover**, headless deletes and org cleanup |
| [`knowledge/13-ipu-cost`](13-ipu-cost/) | the IPU model and how consumption is metered, metering exports, entitlement vs licence, job caps and budgets |
| [`knowledge/reference`](reference/) | the generated API & MCP endpoint reference, the IICS→IPU KB, and the [community code index](reference/community-code-index.md) |
| [`lessons`](../lessons/) | every lesson by domain (current and **overturned**), with stable IDs `L-<DOM>-###` |
| [`knowledge/14-working-with-claude`](14-working-with-claude/) | how Claude reaches and drives IDMC, evidence discipline, multi-agent coordination, UI automation, environment traps, secrets hygiene, and the **Script Library** |

## 6. Scope: generic by design

| What | Rule |
|---|---|
| **In this plugin (`knowledge/`, `lessons/`, `skills/`, `commands/`, `toolkit/`)** | Generic IDMC knowledge that works in *any* org: planes, hosts, routes, bodies, error codes, walls, timings, limits, workarounds, lessons and the scripts that apply them. No customer, application, person, org or object id, host, IP, cloud project or tracker key appears here. Numbers without names stay ("a 62-task linear taskflow took 21 min"): the timings and limits are the point |
| **Kept outside this KB** | Deployment-specific material: which org is which, their ids, hosts and VMs, application names and status, migrations, tracker history, evidence, org-specific scripts, and the raw provenance of each lesson. Nothing in this KB links to it or depends on it |

Your own login never lives in the plugin: it is in `~/.idmc_toolkit/IDMC_LOGIN.txt`. The rule is enforced by
`toolkit/tools/secret_scan.py`, which runs in a pre-commit hook and in CI and must print CLEAN.

## 7. Conventions

- **Evidence states are never merged.** *Proven <date>* means a live response was observed. *Documented* means a
  vendor guide says so and nobody has exercised it. *Rejected (<code>)* means the verb was explicitly refused.
  *Untested* means unknown, not unsupported.
- **Latest dated evidence wins.** Older beliefs are kept, marked superseded, in `lessons`, so nobody
  re-learns them.
- **Lesson IDs** (`L-CDI-012`) are stable. Each lesson's text stands on its own.
- **No secrets anywhere.** Credentials come from `~/.idmc_toolkit/IDMC_LOGIN.txt`, environment variables or files
  outside the plugin.

## 8. Keeping it current

- New **generic** knowledge goes to the matching topic doc *and* as a new lesson in `lessons`, with a date
  and evidence. When a belief is overturned, move it to the "Superseded / overturned" section; never delete it.
- New **deployment- or org-specific** facts (which org, ids, hosts, application status) stay outside the KB.
- Before finishing, run `python3 toolkit/tools/secret_scan.py` (must print CLEAN) and `python3 tests/run_tests.py`
  (checks every link and path; must print ALL PASSED). How to contribute: [CONTRIBUTING.md](../CONTRIBUTING.md).

## 9. History

- **2026-09-22:** first consolidation of scattered IDMC notes, scripts and references into 13 topic buckets.
- **2026-09-29:** full rebuild: generic topic folders written from about 2,200 pooled lessons (deduplicated to 1,335),
  vendor references moved to `knowledge/reference/`, deployment-specific material and secret-bearing files moved
  out, every move reversible from its undo log.
- **2026-10-03:** share-readiness pass (every doc genericized to placeholders, every link kept inside the KB) and a
  currency update (about 190 new field candidates checked against the KB; full pushdown and the remaining transformation
  types headless; agent tuning, job budgets, latency and serving to BI; every doc in `00`–`02` given the Claude-friendly
  block; the [End-to-End Playbook](00-start-here/07-end-to-end-playbook-deploy-and-operate-idmc-with-claude.md)
  added). See the [Changelog](00-start-here/06-changelog.md).
- **2026-10-23:** one combined Master IDMC KB: the IDMC Toolkit (mapping generator, three demo blueprints, Claude skill,
  setup) folded in, the Script Library as its one library, and `IDMC_LOGIN.txt` as the one file a reader fills in to
  connect.
- **2026-10-26:** a [Mapping Fast Path](04-mappings/00-mapping-fast-path-read-this-first.md) as the
  first stop for any mapping work; the generator's spec reference and 28 proven example specs shipped in `toolkit/mapgen/`;
  54 new lessons (Hosted Agent limits, Databricks, Snowflake, SharePoint, moving an org). See the
  [Changelog](00-start-here/06-changelog.md).
- **2026-11-03 (v4):** two rules up front (never push another technology; never say "not possible" before the
  workaround ladder), [New Pipeline Milestones](00-start-here/08-new-pipeline-milestones-any-source-any-target.md)
  for any source and target, neutral wording in the entry docs and the generator (a connection with no `kind` now
  warns instead of silently becoming BigQuery; flat-file targets documented), the skill's error index rebuilt from
  the KB's own lessons, a quick start and a "create any IDMC asset" index, the exemplar route for any connector the
  generator has no template for (`toolkit/mapgen/exemplar.py`), and 65 new lessons (Hosted Agent outage, File Ingestion
  and Local Spark headless, CAI file bytes, lineage design, address verification, database profiling over JDBC V2).
  See the
  [Changelog](00-start-here/06-changelog.md).
- **2026-11-10 (v5):** ready for GitHub (`.gitignore`, a pre-commit hook and a CI job that run `toolkit/tools/secret_scan.py`,
  `git clone` setup, no compiled caches or device paths), 93 new lessons from a production deployment onto a live
  warehouse (backups, host failures, DQ gates that proved nothing, live-database profiling, inherited builds, many
  sessions on one estate, cost), and [What Went Wrong](00-start-here/09-what-went-wrong-production-deployment-post-mortem.md), the post-mortem that turns
  them into checks. See the [Changelog](00-start-here/06-changelog.md).
- **2026-11-19:** the `idmc-mp` plugin layout throughout, all 23 managed MCP servers, an ecosystem guide, about 300
  lessons mined from public IDMC code (Reported, with a [community code index](reference/community-code-index.md)),
  a plain-language setup, and a security and tidiness pass. See the [Changelog](00-start-here/06-changelog.md).
