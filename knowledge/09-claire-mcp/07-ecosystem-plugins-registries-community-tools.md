# Ecosystem: Claude plugins, MCP registries and community tools

**Answers:** Besides the vendor's managed servers, what else exists for driving IDMC from an AI agent or a script? What
is in the vendor's own Claude plugin, and how does it relate to this plugin? Where are the managed servers listed? Which
community MCP servers, CLIs, skills and CI/CD templates are worth reading, and which should you avoid?

**Read when:** a user asks "is there an official plugin / MCP / CLI for IDMC?"; before you wire a third-party MCP server
or CLI into a session; you need the argument contract of the catalog-discovery or data-exploration tools; you want
another implementation to compare a route against.

**Key rules:**
- The vendor-hosted servers are the official MCP surface. There is no official open-source IDMC MCP server: community
  servers wrap the same REST APIs (L-MCP-005, L-MCP-137).
- The vendor's Claude plugin covers catalog discovery and data questions only, and its source ships with empty server
  URLs: in Claude Code, supply your pod's URLs and a credential yourself (L-MCP-135).
- Read the vendor plugin's skill for the catalog-discovery and data-exploration tool contract (§3, L-MCP-134).
- Review every third-party server or CLI before wiring it: TLS verification, where credentials live, which org it points
  at, and its license (L-MCP-124, L-MCP-137).
- A route seen in a community tool is **Reported**, not proven: probe it before you rely on it (§5).

**Related:** [01 Managed MCP Servers](01-managed-mcp-servers-catalog-access.md) ·
[02 MCP Auth & OAuth Clients](02-mcp-auth-oauth-clients.md) ·
[04 Agent-Style MCP & Custom Shims](04-agent-style-mcp-async-orchestration-custom-shims.md) ·
[Secrets Hygiene](../14-claude-working-methods/06-secrets-hygiene.md) ·
[Community code index](../12-reference-library/community-code-index.md) ·
[Lessons: CLAIRE & MCP](../../lessons/by-domain/09-claire-mcp.md)

**Last verified:** 2026-11-19 (every repository below cloned or listed that day; star counts and dates are as of then)

> **Summary.** The official pieces are the 23 vendor-hosted servers (public registry, L-MCP-132), the vendor's Claude
> plugin (one skill, two connectors; L-MCP-123, L-MCP-135) and partner listings such as Microsoft's MCP catalog
> (L-MCP-136). The community side is thin: most repositories have 0-5 stars. One CLI is maintained and safe to
> recommend; a few MCP servers and skills are useful to read but not to run as-is (L-MCP-137). Their code was mined for
> 292 more lessons in two passes (Reported, not probed here); the [community code index](../12-reference-library/community-code-index.md)
> maps each one to the file it came from.

---

## 1. The vendor's Claude plugin (L-MCP-123, L-MCP-135)

| Item | Value (2026-11-19) |
|---|---|
| Name | `informatica-for-claude-platform`, version 1.0.0, Apache-2.0 |
| Install (Claude Code) | `/plugin install informatica-for-claude-platform@claude-plugins-official` |
| Source | the vendor's public `informatica-claude-plugins` repository (under its parent company's GitHub organization), last commit 2026-09-15; a container repo with no marketplace manifest of its own |
| Skill | `catalog-and-data-discovery` (867 lines): catalog-first discovery, trust, sensitivity, policy and safe-use verdicts, then a hand-off to data exploration |
| MCP servers | `informatica-catalog-discovery` and `informatica-data-exploration`, both `type: "http"` with `url: ""` |
| What it does not cover | jobs, connections, Secure Agents, deploy and promote, DQ, MDM, IPU: everything else this plugin covers |

**How to use both.** They do not conflict: different plugin names, different skills. The vendor plugin answers "which
trusted table holds X, and what does it say"; this plugin builds, runs and fixes IDMC. In Claude Desktop and Cowork the
organization connectors (L-MCP-123) fill in the two URLs. In Claude Code, add them yourself, for example with
`claude mcp add --transport http`, pointing at `https://mcp.<domain>.informaticacloud.com/mcp-servers/public/cdgccatalogdiscovery`
and `.../dataexplorationagent`, and authenticate as in [02](02-mcp-auth-oauth-clients.md).

---

## 2. Where the managed servers are listed

| Listing | What it holds | Use it for |
|---|---|---|
| **Public registry** `https://hdm.<domain>.informaticacloud.com/mcp-registry/v0.1/servers` | all 23 shared servers, no login (L-MCP-132) | the current vendor catalog |
| **Org registry** `https://hdm.<domain>.informaticacloud.com/a2e-mcp-asset-mgmt-svc/api/v1/mcp-servers` | what *your org* exposes, with a v3 session (L-MCP-001) | before declaring a wall |
| **Vendor help**: the "Available MCP servers" and "Shared MCP servers" pages under `https://onlinehelp.informatica.com/IICS/prod/agentic-ui/en/` | one page per server with its tool list | tool names and arguments |
| **Microsoft's MCP catalog** (Informatica partner manifests in Microsoft's public Azure MCP repository) | only the April five: address verification, CDGC metadata search, customer identification, data provisioning, job management; OAuth client credentials (L-MCP-136) | Microsoft Foundry and agent platforms built on that catalog |
| **claude-plugins-official** | the vendor's Claude plugin (§1) | Claude Code, Desktop, Cowork |
| **Databricks Marketplace, MuleSoft Anypoint Exchange** | the shared servers; not every server on every marketplace (L-MCP-133) | those platforms |

Announced platform availability (vendor press releases, not tested here): Microsoft Foundry (GA, May 2026), Amazon Quick
(GA in US regions, May 2026), AWS Agent Registry (preview), Copilot Studio through MCP tools with Entra OAuth (blog,
November 2026). Gemini Enterprise calling CLAIRE agents depends on A2A, which no official page confirmed as shipped on
2026-11-19.

---

## 3. The catalog-discovery and data-exploration tool contract (L-MCP-134)

From the vendor plugin's skill (documented, not probed here). It complements the September schemas in L-MCP-119.

**`search_assets`** (Catalog Discovery)

| Argument | Notes |
|---|---|
| `query` | required; `*` searches the whole catalog |
| `mode` | `KEYWORD` (default) or `NL` (use as fallback) |
| `filterSpec` | typed filters, for example `classType: ["com.infa.odin.models.relational.Table"]`, `resourceType: ["Snowflake"]` |
| `aggregationSpec` | at most one aggregation, at most 20 buckets; read the buckets to route the next call |
| `sortSpec` | at most two |
| `from`, `size` | paging; `size` defaults to 20 |

**`get_asset_details`**

- `assetIdentity`: use the internal UUID (`identity` from search) with the default `identityType: INTERNAL`. An
  `EXTERNAL` id carries a `~classType` suffix that the API rejects with 400.
- `segments[]` (default `summary`): `summary`, `selfAttributes` (view SQL in `sourceStatementText`, `NumberOfRows`,
  `businessName`), `stakeholdership`, `glossary` (`curationStatus` ACCEPTED, INFERRED or REJECTED), `hierarchy` (columns,
  PK, FK), `neighborhood` (`core.PKFK` joins, glossary and DQ-rule links, `RelatedTo`; **no** `DataFlow` lineage,
  `ParentChild` or `ClassifiedAs`), `dataClassification`.
- Batch the segments you need into one call per asset. Useful sets: trust = `selfAttributes, stakeholdership, glossary`;
  relationships = `hierarchy, neighborhood`; sensitivity = `hierarchy, dataClassification`.
- For lineage, use `get_asset_lineage` (added October 2026, L-MCP-132) or the REST asset read (L-CDGC-181).

**`data_explore`** (CLAIRE Data Exploration Agent)

1. Authenticate: `authenticate`, then `complete_authentication`. The token lasts a flat 60 minutes, with no refresh.
2. Always send `external_id` (one asset) or `external_ids`, copied exactly from search or details. **Without it the tool
   returns empty frames and no error**: an empty result means "id missing", not "no data".
3. Send a rewritten, resolved instruction as `prompt`, never the raw question: exact measure column, member lists, date
   range, filters. ASCII only: em-dashes and angle brackets trip the input validator. A raw "Q2 revenue for EMEA" was
   filtered as `SALES_REGION = 'emea'` against country-valued data and returned zero rows.
4. Read `issues[].code`: `term_not_found`, `term_not_wired`, `ambiguous_term`, `permission_denied`, `query_too_heavy`,
   `no_data`, `partial_result`, `timeout`, `metric_version_break`.

The gateway, connection and wording lessons in [03](03-claire-gpt-prompting-rules-patterns.md) and L-MCP-122 to
L-MCP-127 still apply.

---

## 4. Community tools (as of 2026-11-19; L-MCP-137)

Verdicts: **Recommend** = maintained, licensed, credential-safe; **Read** = useful as a reference, do not run as-is;
**Skip** = dead, empty or unsafe.

### 4.1 CLIs and SDKs

| Tool | Language, license | Last commit | What it does | Verdict |
|---|---|---|---|---|
| `jbrazda/iics-cli` | Go, Apache-2.0 | 2026-11-02 (v0.6.2) | wide v2/v3 coverage: objects, export/import, projects, roles, users, metering, schedules, agents, connections, source control, CAI publish; v3 login; retries on 429; passwords in the OS keyring | **Recommend**: the only maintained general IDMC CLI |
| `jonbowring/idmc-cli` | Python, GPL-3.0 | 2025-10-20 | broad v2/v3 CLI including source control and metering export | Read (semi-stale; GPL) |
| `BrentGruber/pydmc` | Python, no license | 2025-03-10 | small admin client; SAML group/role mappings and TrustedIP v3 routes | Read (no license) |
| `InformaticaCloudApplicationIntegration/Tools` ("IICS Asset Management CLI") | MIT, binaries only | 2021-12-27 | the vendor's old export/import/publish CLI | Skip (stale; use v3 REST or iics-cli) |
| `Tzrlk/terraform-provider-idmc` | Go, no license | 2024-10-15 | roles and runtime environments only; not on the Terraform registry | Skip |
| PyPI `infapy`; `chriszacny/informatica_cloud_python_api` | | 2016-2021 | old wrappers | Skip |
| `joseangelramos/idmc-java` | Java, Apache-2.0 | 2024-09-18 | not IDMC code: a renamed Unity Catalog client | Skip |
| `BrentGruber/informatica-inventory` | Go, no license | push 2026-04-28 | a scaffold whose route list includes v3 paths that do not exist | Skip |

### 4.2 MCP servers and AI-assistant skills

| Tool | License | Last commit | What it does | Verdict |
|---|---|---|---|---|
| `jbrazda/ai-agent-skills` | Apache-2.0 | 2026-10-13 | `iics-doc-gen` skill: Markdown documentation from exported CAI process and taskflow XML; manifests for Claude Code, Cursor and Copilot; offline, no credentials | **Recommend** for CAI documentation (compare the managed `idmcassetdocumentation` server, L-MCP-132) |
| `jklim-insfa/idmc-cdgc-mcp-server` | none | 2026-09-24 | 18 CDGC tools over `identity-service` login and `/data360/*` routes | Read (no license) |
| `jpeckjr/informatica-mcp` | none | 2026-10-13 | 42 tools over v2 jobs, mappings, connections, agents and CAI taskflow run/status/terminate, plus a Slack monitor | Read only: its README says the credential points at a **production** org |
| `woppedisano323/Informatica-MDM-kit` | none | 2026-11-11 | Claude Code commands that coach an MDM SaaS build: setup, profile, deploy, operate; the irreversible steps | Read (no license) |
| `woppedisano323/Informatica-CDGC-kit` | none | 2026-10-10 | Claude Code commands plus scripts that generate CDGC bulk-import workbooks and import them over REST | Read (no license; a few internal contradictions, flagged in the lessons) |
| `wil-schneider/CDQ-DQRO-Score-Upload` | none | 2026-06-16 | creates catalog DQ rule occurrences and uploads external scores | Read (no license) |
| `bmantha/data-classification-policy`, `bmantha/dq-gate-policy` | none | 2026-11-17 | API-gateway policies that block agent (MCP, A2A) calls by CDGC classification or DQ score | Read: a pattern for governing agents with the catalog |
| `datahub-project/datahub` (Informatica source) | Apache-2.0 | 2026-11-18 | an open-source catalog's IDMC ingestion: v2 lists, v3 export lineage, session checks | **Recommend** as a reference implementation |
| `rashmiprabhu8192/cdgc_metadata_propagation`, `monte-carlo-data/apollo-agent`, `IBM/data-intelligence-sdk` | none / source-available / unknown | 2026 | metadata propagation over the audit API; IdP-JWT login; data contracts from CDGC metadata | Read |

No Informatica-specific Cursor rules or Copilot instruction files were found.

Repositories with security problems are deliberately not named or linked in this KB: scripts that report the user's
hostname and login details to a personal server, a chat bot that runs Claude with permission checks skipped and catalog
write tools, an extractor that has users copy their browser session cookie into a file, and servers that take the IDMC
password as a tool argument or store it in a config file, a server that logs request bodies holding passwords,
and repositories that commit real org ids or profiling results. §5 says how to spot each of these in any tool you are given.

### 4.3 CI/CD, packaging and reference assets

| Tool | License | Last commit | Verdict |
|---|---|---|---|
| `jbrazda/iics-project-template` | MIT | 2023-01-11 | Read: how to lay out export packages in Git (Ant + Bitbucket Pipelines) |
| `jbrazda/iics-reporting-tools` | MIT | 2024-10-18 | Read: XQuery dependency and design reports over export ZIPs |
| `jbrazda/iics-quickstart-bundle`, `icai-fault-alert-service`, `iics-bootcamp` | MIT / Apache-2.0 | 2019-2024 | Read: reusable CAI assets, fault alerting, training labs |
| `InformaticaCloudApplicationIntegration/Service-Connectors` | MIT | 2022-01-05 | Read: about 45 CAI service-connector packages with Swagger/WSDL (36 stars, the most of any IDMC repo; unmaintained) |
| `api-evangelist/informatica` | none | 2026-10-30 | Read: a README pointing at third-party API profiles on apis.io; unofficial, specs not checked |

No GitHub Action, Azure DevOps task or Pulumi provider for IDMC was found. There is no open-source PowerCenter-to-IDMC
converter (the vendor's PowerCenter modernization tooling is proprietary); `mantovani/Parser-PowerCenter-XML` is a 2012
Perl stub, and `digital-rain-tech/crawl` was not reachable on 2026-11-19.

---

## 5. Using a community tool safely

1. **Check the license.** No license means no right to copy its code into your work; read it, do not vendor it.
2. **Grep for disabled TLS** (`CERT_NONE`, `check_hostname`, `verify=False`, `_create_unverified_context`,
   `rejectUnauthorized`) before the first run (L-MCP-124).
3. **Check where credentials live.** Prefer the OS keyring, a 0600 file or the environment; never the MCP config's args
   or a committed `.env` (L-METHOD-001). Use an OAuth client-credentials client scoped to the servers you need rather than
   a user password ([02](02-mcp-auth-oauth-clients.md)).
4. **Point it at a non-production org first**, and check which org a session lands in (L-MCP-033).
5. **Treat its routes as Reported.** Example: one CLI calls `/public/core/v3/sourceControl/{checkout,checkin,pull,commit}`
   with no test or live note behind it, while this KB and a second CLI use the flat `/public/core/v3/{checkout,checkin,pull}`
   routes: keep the flat form (L-MIG-097, L-MIG-109).
6. **Grep for outbound calls to anything but `*.informaticacloud.com`** (`workers.dev`, webhooks, `X-Auth-Key`,
   telemetry): two public CDGC scripts post the hostname and login details to a personal endpoint on every run
   (L-METHOD-170).
7. **Never put a write-capable IDMC MCP server behind an unattended agent** that runs with permission checks skipped: any
   chat member, or text injected through catalog content, could then trigger writes (L-METHOD-164).
8. **Copy the good patterns instead**: preview-then-confirm write tools, an org guard after every login, a failure-only
   monitor that proves its own silence, secrets kept out of the chat (L-METHOD-162, L-ENV-140, L-METHOD-163). They are lessons now; find them under "Working
   methods" and "Environment & ops" in the [community code index](../12-reference-library/community-code-index.md).
