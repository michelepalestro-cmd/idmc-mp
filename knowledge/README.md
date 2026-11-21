# Informatica IDMC Headless knowledge base

> Setup (install, connect, troubleshooting) is in the root [README](../README.md). Paths in inline code
> (`knowledge/...`, `knowledge/lessons/...`, `toolkit/...`) are relative to the plugin root.

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

**Last verified:** 2026-11-20

## What this is

A knowledge base about Informatica IDMC, written for Claude sessions and the people working with them: how IDMC really
behaves when it is driven without its UI (routes, hosts, headers, bodies, error codes), what each wall turned into
when it was tested, and more than 2,300 dated lessons, each with its evidence. It is **guidance**: your systems, your
naming and your order of work are always the right ones, and your org's live answer beats any lesson.

**Start at the router, [00-start-here](00-start-here/README.md)** ("I want to..." -> command, cheat sheet, tool), then
the job folder's one-page cheat sheet. Setup and login: [Setup and login](00-start-here/11-setup-and-login.md). The
rules every session follows: [RULES.md](RULES.md). How the placeholders map onto your org:
[How to use this KB](00-start-here/01-how-to-use-this-kb.md).

## The map

One folder per job, in the order you usually build. Each folder starts with a one-page `README.md` cheat sheet and
holds that job's guides and its `lessons*.md`. The "I want to..." router is [00-start-here](00-start-here/README.md).

| Folder | Read it when you need to… |
|---|---|
| [`00-start-here`](00-start-here/README.md) | orient yourself: the router, **the laws of headless IDMC**, the capability map, error triage, glossary, quick start, end-to-end playbook, new-pipeline milestones, what went wrong in production, running it in production (Day 2) |
| [`01-login-and-orgs`](01-login-and-orgs/README.md) | log in, pick the right host and header, handle sessions, lockouts and the JWT change, prove the org before writing, users and roles |
| [`02-secure-agent`](02-secure-agent/README.md) | install, size, tune, resize or reboot a Secure Agent; enable services and connectors on a runtime environment |
| [`03-connections`](03-connections/README.md) | create, test, update and delete connections to any system; per-connector settings; fix "the connection is broken" (the four gates) |
| [`04-mappings`](04-mappings/README.md) | **build mappings and whole pipelines headless** (start with the Fast Path), mapping tasks, consolidation, pushdown, performance and job caps, changing pipelines safely, serving outputs to BI and apps |
| [`05-taskflows-schedules`](05-taskflows-schedules/README.md) | linear and advanced taskflows, schedules, run and monitor them |
| [`06-cdc-ingestion`](06-cdc-ingestion/README.md) | database ingestion and CDC over REST, PostgreSQL CDC, targets and drivers, file ingestion |
| [`07-app-integration`](07-app-integration/README.md) | author, publish and invoke CAI processes, connections and connectors, Process Server on an agent, event listeners |
| [`08-data-quality`](08-data-quality/README.md) | DQ assets, profiling, the CLAIRE DQ agent, scorecards, cleaning a large dataset with mappings |
| [`09-catalog-lineage`](09-catalog-lineage/README.md) | catalog sources and scans, glossary, links, classification, search, lineage, marketplace |
| [`10-mdm`](10-mdm/README.md) | MDM SaaS runtime vs design, records, Business 360 modeling, match and merge, mastering any table |
| [`11-mcp-claire`](11-mcp-claire/README.md) | Informatica's managed MCP servers, MCP OAuth clients, CLAIRE GPT, agent-style MCP, plugins and community tools |
| [`12-deploy-migrate`](12-deploy-migrate/README.md) | v3 export and import, editing packages, clone-authoring, org-to-org migration and cutover, headless deletes and cleanup |
| [`13-ipu-cost`](13-ipu-cost/README.md) | the IPU model, metering exports, entitlement vs licence, job caps and budgets |
| [`14-working-with-claude`](14-working-with-claude/README.md) | how Claude reaches and drives IDMC, evidence discipline, multi-agent work, UI automation, environment traps, secrets hygiene |
| [`reference`](reference/README.md) | the endpoint-level API and MCP reference, the IICS-to-IPU KB, the compact playbook, the [community code index](reference/community-code-index.md) |
| [`lessons`](lessons/README.md) | every lesson in one searchable file (`lessons.jsonl`), the counts, and every overturned belief |

## Create any IDMC asset: where to start

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
| A file ingestion task | [Mass Ingestion & CDC](06-cdc-ingestion) (lessons L-DBMI-060 to L-DBMI-062) | `POST /mftsaas/api/v1/mitasks`, then `job` |
| A CAI process, app connection or service connector | [CAI Asset Lifecycle](07-app-integration/01-cai-asset-lifecycle-author-publish-unpublish-delete.md), [CAI Connections](07-app-integration/03-cai-connections-connectors-salesforce-oauth.md) | import package + publish (`idmc_cai_publish.py`) |
| A Kafka or JMS event listener | [CAI Event Listeners](07-app-integration/06-cai-event-listeners-kafka-amqp-jms.md) | listener + process, published |
| A data quality rule, cleanse, dictionary or verifier | [DQ Assets](08-data-quality/01-dq-assets-rule-specs-cleanse-dictionaries-verifiers.md) | clone-authored assets, run inside a mapping |
| Address verification and enrichment (verify, standardize, geocode, CASS) | [DQ Assets](08-data-quality/01-dq-assets-rule-specs-cleanse-dictionaries-verifiers.md) §6 | an on-agent Verifier asset in a mapping (the generator's `verifier` node), or the cloud Address Verification REST service (Certified mode for CASS) |
| A data profile | [Profiling](08-data-quality/02-profiling-what-is-headless.md) | the profiling service REST API |
| A catalog source and its scan | [Catalog Sources](09-catalog-lineage/02-catalog-sources-create-scan-update-purge.md) | `idmc_cdgc.py` |
| Glossary terms, links, classifications | [Glossary, Links & Classification](09-catalog-lineage/03-glossary-links-classification.md) | CDGC content API |
| Lineage (scanned and curated) | [Search, Lineage & Marketplace](09-catalog-lineage/04-search-lineage-marketplace.md) | catalog scans + curated edges |
| MDM business entities, records, a mastered table | [Business 360 Modeling](10-mdm/03-business-360-modeling-match-merge.md), [MDM Records](10-mdm/02-mdm-records-ingest-search-export-cleanup.md), [Mastering a Table](10-mdm/05-mastering-a-table-repeatable-playbook.md) | MDM APIs, or CDI mappings that master a table |
| MCP access, CLAIRE GPT prompts | [Managed MCP Servers](11-mcp-claire/01-managed-mcp-servers-catalog-access.md), [CLAIRE GPT](11-mcp-claire/03-claire-gpt-prompting-rules-patterns.md) | `/informatica-idmc-headless:connect-mcp` (a scoped OAuth client, and the servers' tools as Claude Code tools through the plugin's bridge), or managed MCP + OAuth clients from the toolkit |
| A copy, a move, an export / import, a clone of any asset | [Export & Import](12-deploy-migrate/01-export-import-v3-migration-api.md), [Migration-Clone Authoring](12-deploy-migrate/03-migration-clone-authoring.md) | v3 export / import packages; FRS `CopyEntities` / `MoveEntities` |
| **Anything not in this table** | [Milestones](00-start-here/08-new-pipeline-milestones-any-source-any-target.md): "A system or connector the KB has never seen" and the workaround ladder | the closest pattern here, adapted and proven in your org, then recorded as a lesson |

## Conventions

- **Evidence states are never merged.** *Proven <date>* means a live response was observed. *Documented* means a
  vendor guide says so and nobody has exercised it. *Rejected (<code>)* means the verb was explicitly refused.
  *Untested* means unknown, not unsupported.
- **Latest dated evidence wins.** Older beliefs are kept, marked superseded, in `lessons`, so nobody
  re-learns them.
- **Lesson IDs** (`L-CDI-012`) are stable. Each lesson's text stands on its own.
- **No secrets anywhere.** Credentials come from `~/.idmc_toolkit/IDMC_LOGIN.txt`, environment variables or files
  outside the plugin.

## Scope: generic by design

| What | Rule |
|---|---|
| **In this plugin (`knowledge/`, `knowledge/lessons/`, `skills/`, `commands/`, `toolkit/`)** | Generic IDMC knowledge that works in *any* org: planes, hosts, routes, bodies, error codes, walls, timings, limits, workarounds, lessons and the scripts that apply them. No customer, application, person, org or object id, host, IP, cloud project or tracker key appears here. Numbers without names stay ("a 62-task linear taskflow took 21 min"): the timings and limits are the point |
| **Kept outside this KB** | Deployment-specific material: which org is which, their ids, hosts and VMs, application names and status, migrations, tracker history, evidence, org-specific scripts, and the raw provenance of each lesson. Nothing in this KB links to it or depends on it |

Your own login never lives in the plugin: it is in `~/.idmc_toolkit/IDMC_LOGIN.txt`. The rule is enforced by
`toolkit/tools/secret_scan.py`, which runs in a pre-commit hook and in CI and must print CLEAN.

History: [KB changelog](reference/kb-changelog.md) and the plugin's [CHANGELOG](../.github/CHANGELOG.md). Contributing:
[CONTRIBUTING](../.github/CONTRIBUTING.md).
