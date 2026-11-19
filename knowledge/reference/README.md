# knowledge/reference

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
[Pods, Hosts & Service Planes](../01-login-and-orgs/01-pods-hosts-service-planes.md) ·
[IPU Model](../13-ipu-cost/01-ipu-model-mechanics.md) ·
[Lessons Learned](../../lessons/README.md)

**Last verified:** 2026-11-19 (structure and links). Live API evidence in the corpus 2026-06-28 to 2026-07-26; vendor
guides April 2026 (CPDS and Measurement Guide v39.1); IICS-to-IPUs KB 2026-09-03; de-identified and rebuilt
2026-09-29 and 2026-10-03.

The reference material the topic folders lean on: an endpoint-level IDMC API and MCP corpus and a
customer-facing IICS-to-IPU licensing KB. Informatica's own schedules and guides are not bundled: read
them at https://docs.informatica.com. Use it for lookups (a path, a verb, a host, a vendor sentence, a
licensing rule). For "how do I do X", start with the topic folders.

## What is in here

| Sub-library | What it is | Open first |
|---|---|---|
| `idmc-api-mcp-reference/` | Every IDMC REST endpoint and MCP action the corpus has seen: 167 endpoints, 11 MCP actions, 28 operations with no endpoint (generated set, 2026-10-03 rebuild). For each one it gives the verbs in one of four states (**Works** = a live status code was seen, **Documented** = vendor-documented but unexercised, **Rejected** = refused with a code, **Untested**), the auth plane, the host pattern, the header and the evidence. The source of truth is `content/*.json` (30 sections); the dictionary and CSVs are generated from it. | [claude-idmc-how-to/start-here.md](idmc-api-mcp-reference/claude-idmc-how-to/start-here.md) |
| `iics-to-ipus-kb/` | A customer-facing KB on the move from legacy IICS licensing (per-service subscriptions, connector tiers) to the IDMC IPU consumption model, anchored on CPDS v39.1. 13 section files plus a citation registry. | [start-here.md](iics-to-ipus-kb/start-here.md) |
| `community-code-index.md` | For each of the 292 lessons mined from public IDMC code on 2026-11-19 (two passes), the repository and file it came from, grouped by area. | [community-code-index.md](community-code-index.md) |

Inside `idmc-api-mcp-reference/`:

- `claude-idmc-how-to/` holds `idmc-endpoint-dictionary.md` (organised by path) and
  `csv-every-endpoint/` (10 CSVs), both generated, plus two hand-written guides: `start-here.md` and
  `what-idmc-can-and-cannot-do.md`.
- The product-by-product master `.docx` is not shipped; `build/build_master.py` renders it on demand
  (needs `python-docx`).
- `README.md` and `AGENTS.md` are the corpus's own contract: one section file per agent, the four verb
  states never merged, and a validator before every build.

## When to use this library and when to use the topic folders

All CSV paths below are under `idmc-api-mcp-reference/claude-idmc-how-to/csv-every-endpoint/`.

| You want | Go to |
|---|---|
| How to do a task end to end: route, body, read-back, walls, workarounds | the topic folder for the domain (`01`–`11`), then `lessons` |
| Whether verb X works on path Y, and which host and header to use | `02_endpoint_verb_matrix.csv` (filter `State`), or `idmc-endpoint-dictionary.md` |
| Everything callable today for one product | `01_endpoints.csv` (filter `Any working verb? = YES` and `Service`) |
| What a status code or error really means | `08_status_code_decoder.csv`, then the triage in `knowledge/00-start-here` |
| Informatica's exact wording or a documented cap | `09_limits_and_caps.csv`, then https://docs.informatica.com |
| IPU rates, metering rules, SKUs, licensing terms | `knowledge/13-ipu-cost` for the method; the CPDS and Measurement Guide at https://docs.informatica.com for the source wording |
| A customer-shareable explanation of IICS to IPUs | `iics-to-ipus-kb/sections/` (a single `.md` or PDF can be built with its `build/` scripts) |

**Currency: read this before quoting the corpus.** The corpus's live rows are a snapshot from
2026-06-28 to 2026-07-26, taken on two orgs: **Org A**, an org on a dm-us pod, and **Org B**, a sub-org on a
dmp-us pod. Later evidence in the topic folders overturns some of its walls:

- The corpus says no `PUT` is proven anywhere. A `PUT` on runtime-environment service selections was later proven (2026-09-28).
- The corpus calls design-time authoring a UI wall and treats cloning through v3 export, package edit and import as a narrow exception. Later work made that clone path the standard headless authoring route: a CDI mapping-template clone on 2026-08-19, and org-to-org migration clones from 2026-09-22.
- The corpus left the DBMI create body unknown. The full DBMI task lifecycle (create, deploy, start, stop, undeploy) was proven headless on 2026-09-28.
- The corpus lists "rich transforms (joiner, aggregator, expression, pushdown)" as Mapping Designer only. Full SQL ELT
  pushdown is now switched on headless through the v2 mapping task (`sessionProperties` plus `enableCrossSchemaPushdown`,
  proven by `OPT_63367` in the session log) (L-CDI-202); for transformation authoring see
  [`knowledge/04-mappings/02-how-claude-builds-mappings-headless.md`](../04-mappings/02-how-claude-builds-mappings-headless.md).
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

## How to rebuild

From the repo root, with Python 3.10+:

```bash
cd knowledge/reference/idmc-api-mcp-reference
python3 build/validate_content.py          # must exit 0 (warnings are fine)
python3 build/build_dictionary.py --csv    # -> claude-idmc-how-to/idmc-endpoint-dictionary.md + csv-every-endpoint/*.csv
python3 build/build_master.py              # optional -> idmc-api-mcp-master-reference.docx (needs python-docx; not committed)
```

- Edit only `content/*.json`. All three scripts read and write only inside `idmc-api-mcp-reference/`.
  `build_dictionary.py --check` renders and prints the counts without writing anything. The first two
  scripts are standard library only.
- The `content/` files were seeded on 2026-07-25 from probe evidence kept outside this repo.
- The hand-written guides are not regenerated. Re-check their counts whenever you rebuild;
  `what-idmc-can-and-cannot-do.md` keeps its counts as of 2026-07-26 and says so.
- IICS-to-IPUs KB: `cd knowledge/reference/iics-to-ipus-kb && python3 build/build_kb.py`
  writes `iics-to-ipus-knowledge-base.md` (standard library); `python3 build/build_pdf.py` then renders a
  PDF (needs `markdown`, `pymdown-extensions` and `playwright`). Neither output is committed. See its
  `AGENTS.md`.

## Raw evidence

The corpus was built from live runs against specific orgs, so its raw evidence names them and is not part of
this library: the probe results and vendor extracts, the migration audit trail, the mined universe of 440
paths + 6,898 unproven candidates, earlier build scripts and legacy data modules, an org-specific Claude
skill, and the live probe harness `probe_idmc_surface.py` (it reads a local credential file). Nothing in this
library needs any of it at build time. To re-date a live row, reproduce the probe against your own org (the
method is in `idmc-api-mcp-reference/content/90-provenance.json`).

## Rules for this folder

- **Generic zone.** No org, app, customer or person names; no org, agent, RE, connection or object IDs;
  no IP addresses, pod, VM or host names, tracker keys or user names. Use the neutral labels (Org A,
  Org B, the parent org, Customer A/B/C) and placeholders: `<pod>`, `<domain>`, `<org>`, `<orgIdV2>`,
  `<orgIdV3>`, `<agentId>`, `<reId>`, `<connId>`, `<private-ip>`, `<db>`. Domain labels (`dm-us`,
  `dmp-us`) and Informatica's own names are fine.
- **Gate before you finish.** Run `python3 toolkit/tools/secret_scan.py .` from the repo root; it must
  print CLEAN.
- **No internal commercial material.** Price-list extracts, discount schedules, deal notes and seller-only
  enablement do not belong in this library. IPU *mechanics* (meters, IPU rates, how consumption is
  computed) are fine.
- **No secrets.** Refer to credentials by name and location only. Never paste a value.
