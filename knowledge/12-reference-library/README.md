# knowledge/12-reference-library

**Answers:** Where is the endpoint-level row for an IDMC REST route or MCP action, the vendor's own wording on a
product, rate or meter, or the IICS-to-IPU licensing background, and how far can each be trusted?

**Read when:** a topic doc sends you here for an endpoint row, a verb state or a vendor sentence; you need a licensing
or metering definition; you are about to regenerate one of the reference sub-libraries.

**Key rules:**
- For "how do I do X", start in the topic folders and search the existing evidence first; use this library for
  lookups (L-METHOD-034).
- Its live API evidence ends 2026-07-26: where a row disagrees with a topic doc or a newer lesson, the newer dated
  evidence wins (L-METHOD-035).
- A "no endpoint" or "UI-only" row is a dated verdict: check the Capability Map and re-probe before calling it a wall
  (L-METHOD-034, L-METHOD-035).
- Take the host and header for a route from the plane map, not from a reference row (L-AUTH-001).

**Related:** [How to use this KB](../00-start-here/01-how-to-use-this-kb.md) ·
[Capability Map](../00-start-here/03-capability-map.md) ·
[Pods, Hosts & Service Planes](../01-access-auth-orgs/01-pods-hosts-service-planes.md) ·
[IPU Model](../11-ipu-metering-licensing/01-ipu-model-mechanics.md) ·
[Lessons Learned](../../lessons/README.md)

**Last verified:** 2026-10-04 (structure and links). Live API evidence in the corpus 2026-06-28 to 2026-07-26; vendor
guides April 2026 (CPDS and Measurement Guide v39.1); IICS-to-IPUs KB 2026-09-03; de-identified and rebuilt
2026-09-29 and 2026-10-03.

The reference material the topic folders lean on: an endpoint-level IDMC API and MCP corpus with its
generated master document, a customer-facing IICS-to-IPU licensing KB and a superseded verb-matrix generator. Informatica's own
schedules and guides are not bundled: read them at https://docs.informatica.com. Use it for lookups (a path, a verb, a
host, a vendor sentence, a licensing rule). For "how do I do X", start with the topic folders.

## What is in here

| Sub-library | What it is | Open first |
|---|---|---|
| `IDMC API & MCP Reference\` | Every IDMC REST endpoint and MCP action the corpus has seen: 167 endpoints, 11 MCP actions, 28 operations with no endpoint. For each one it gives the verbs in one of four states (**Works** = a live status code was seen, **Documented** = vendor-documented but unexercised, **Rejected** = refused with a code, **Untested**), the auth plane, the host pattern, the header and the evidence. The source of truth is `content\*.json` (30 sections); everything else is generated from it. | `Claude IDMC How To\start-here.md` |
| `IICS-to-IPUs KB\` | A customer-facing KB on the move from legacy IICS licensing (per-service subscriptions, connector tiers) to the IDMC IPU consumption model, anchored on CPDS v39.1. It has 13 section files and a generated `.md` + `.pdf`. | `start-here.md` |
| `community-code-index.md` | For each of the 292 lessons mined from public IDMC code on 2026-11-19 (two passes), the repository and file it came from, grouped by area. | [community-code-index.md](community-code-index.md) |
| `REST Verb Matrix\` | The 2026-07-25 generator and data module behind the retired "IDMC Verb Matrix - API vs MCP" document. Its rows were merged into `IDMC API & MCP Reference\content\` the same day, so this is history. Running `build_verbmatrix.py` writes that old `.docx` next to the script. | nothing, unless you are auditing the merge |

Inside `IDMC API & MCP Reference\`:

- `IDMC API & MCP Master Reference.docx` is the full narrative, organised by product. It is generated, so never edit it.
- `Claude IDMC How To\` holds `idmc-endpoint-dictionary.md` (organised by path) and `CSV - every endpoint\` (10 CSVs), both generated. It also holds two hand-written guides: `start-here.md` and `what-idmc-can-and-cannot-do.md`.
- `_spec\` holds the 2026-07-25 design note, kept for history.
- `README.md` and `AGENTS.md` are the corpus's own contract: one section file per agent, the four verb states never merged, and a validator before every build.

## When to use this library and when to use the topic folders

| You want | Go to |
|---|---|
| How to do a task end to end: route, body, read-back, walls, workarounds | the topic folder for the domain (`01`–`11`), then `lessons` |
| Whether verb X works on path Y, and which host and header to use | `Claude IDMC How To\CSV - every endpoint\02_endpoint_verb_matrix.csv` (filter `State`), or `idmc-endpoint-dictionary.md` |
| Everything callable today for one product | `01_endpoints.csv` (filter `Any working verb? = YES`), or that product's section in the master `.docx` |
| What a status code or error really means | `08_status_code_decoder.csv`, then the triage in `knowledge/00-start-here` |
| Informatica's exact wording or a documented cap | `09_limits_and_caps.csv`, then https://docs.informatica.com |
| IPU rates, metering rules, SKUs, licensing terms | `knowledge/11-ipu-metering-licensing` for the method; the CPDS and Measurement Guide at https://docs.informatica.com for the source wording |
| A customer-shareable explanation of IICS to IPUs | `IICS-to-IPUs KB\IICS to IPUs — Knowledge Base.pdf` |

**Currency: read this before quoting the corpus.** The corpus's live rows are a snapshot from
2026-06-28 to 2026-07-26, taken on two orgs: **Org A**, an org on a dm-us pod, and **Org B**, a sub-org on a
dmp-us pod. Later evidence in the topic folders overturns some of its walls:

- The corpus says no `PUT` is proven anywhere. A `PUT` on runtime-environment service selections was later proven (2026-09-28).
- The corpus calls design-time authoring a UI wall and treats cloning through v3 export, package edit and import as a narrow exception. Later work made that clone path the standard headless authoring route: a CDI mapping-template clone on 2026-08-19, and org-to-org migration clones from 2026-09-22.
- The corpus left the DBMI create body unknown. The full DBMI task lifecycle (create, deploy, start, stop, undeploy) was proven headless on 2026-09-28.
- The corpus lists "rich transforms (joiner, aggregator, expression, pushdown)" as Mapping Designer only. Full SQL ELT
  pushdown is now switched on headless through the v2 mapping task (`sessionProperties` plus `enableCrossSchemaPushdown`,
  proven by `OPT_63367` in the session log) (L-CDI-202); for transformation authoring see
  `knowledge/03-cdi-data-integration\02-how-claude-builds-mappings-headless.md`.
- The corpus gives `GET /profiling-service/api/v1/runDetail/{uuid}/filter` for run history. On at least one pod that
  form (GET and POST) answers 400 `PROFILE_SVC_00093`; read one run at a time with `GET.../runDetail/<profileId>/<runKey>`
  for runKey 1 to `lastRunKey` (L-DQ-019).
- The corpus describes `GET /api/v2/activity/activityLog` as mapping-task rows only. Its rows are of type `MTT`,
  `WORKFLOW` and `MAPPING`, carry no `runtimeEnvironmentId` or `agentId` at the top level (the agent id sits in
  `entries[]`), and never include profile runs or catalog jobs (L-IPU-024, L-IPU-055).
- The corpus lists `ExportMeteringData` job types without window limits. A `PROJECT_FOLDER` window longer than 30 days
  is refused with 400 `LS_298` and creates no job, while `SUMMARY` accepts longer windows (L-IPU-021).
- The corpus treats the agent's `downloads/` folder as installer packages that only must not be bulk-deleted
  mid-deployment. Installed services run from it: never clean or move it (L-AGENT-094).

When this library and a topic folder disagree, the topic folder's later-dated evidence wins. The corpus is
a dated record and is not rewritten after the fact; correct it only with a new live response, following
its `AGENTS.md`.

## How to rebuild the API reference

```bash
cd "<KB root>\knowledge/12-reference-library\IDMC API & MCP Reference"
python build\validate_content.py         # must exit 0 (warnings are fine)
python build\build_master.py             # -> IDMC API & MCP Master Reference.docx (close it in Word first)
python build\build_dictionary.py --csv   # -> Claude IDMC How To\idmc-endpoint-dictionary.md + CSV - every endpoint\*.csv
```

- Edit only `content\*.json`. All three scripts read and write only inside `IDMC API & MCP Reference\`.
  `build_dictionary.py --check` renders and prints the counts without writing anything.
- `build\seed_content.py` and `build\restructure_services.py` were one-time migrations. Never re-run them;
  their inputs are archived (see below).
- The hand-written guides are not regenerated. `start-here.md`, `what-idmc-can-and-cannot-do.md` and the
  CSV folder's `README.md` still quote the 2026-07-26 counts (166 endpoints, 100 with a working verb). The
  generated set now says 167 and 102. Re-check those numbers whenever you rebuild.
- IICS-to-IPUs KB: `python build\build_kb.py`, then `python build\build_pdf.py`. The PDF step needs
  `markdown`, `pymdown-extensions` and `playwright` with msedge. See its `AGENTS.md`.

## Raw evidence

The corpus was built from live runs against specific orgs, so its raw evidence names them and is not part of
this library: the probe results and vendor extracts, the migration audit trail, the mined universe of 440
paths + 6,898 unproven candidates, earlier build scripts and legacy data modules, an org-specific Claude
skill, and the live probe harness `probe_idmc_surface.py` (it reads a local credential file). Nothing in this
library needs any of it at build time. To re-date a live row, reproduce the probe against your own org (the
method is in `IDMC API & MCP Reference\content\90-provenance.json`).

## Rules for this folder

- **Generic zone.** No org, app, customer or person names; no org, agent, RE, connection or object IDs;
  no IP addresses, pod, VM or host names, tracker keys or user names. Use the neutral labels (Org A,
  Org B, the parent org, Customer A/B/C) and placeholders: `<pod>`, `<domain>`, `<org>`, `<orgIdV2>`,
  `<orgIdV3>`, `<agentId>`, `<reId>`, `<connId>`, `<private-ip>`, `<db>`. Domain labels (`dm-us`,
  `dmp-us`) and Informatica's own names are fine.
- **Gate before you finish.** Run the KB's share gate (an identity, pricing and secret scanner that is
  kept outside the shared KB) over the KB root. It reads text, Office and PDF files, and must report
  nothing under `knowledge/12-reference-library`.
- **No internal commercial material.** Price-list extracts, discount schedules, deal notes and seller-only
  enablement do not belong in this library. IPU *mechanics* (meters, IPU rates, how consumption is
  computed) are fine.
- **No secrets.** Refer to credentials by name and location only. Never paste a value.
