# Design — IDMC API & MCP Capability Catalog

**Date:** 2026-07-25 · **Owner:** the KB owner · **Location:** built outside this KB; now kept in
`knowledge/12-reference-library\IDMC API & MCP Reference\_spec\`

> **Superseded, kept for history.** The Capability Catalog this note designs was merged into
> `IDMC API & MCP Master Reference.docx` on 2026-07-25. Org names and IDs below were replaced with
> neutral labels on 2026-09-29: ORG-A = an org on a dm-us pod, ORG-B = a sub-org on a dmp-us pod.

## Purpose

One authoritative document answering, for every IDMC service: **which API operations exist, which
HTTP verbs they take, what class of work they can actually do, and whether that is proven, merely
documented, or blocked.** Plus the equivalent for the MCP surface (CLAIRE's native MCP, the local
stdio proxy, and the self-hosted fallback).

Written for two readers at once: an engineer who needs the exact path and header set, and a seller
who needs "can this be automated headlessly — yes/no/partly."

## Deliverables

| Path | Role |
|---|---|
| `IDMC API & MCP Capability Catalog.docx` | The deliverable. Landscape, styled tables. |
| `_source\catalog.md` | Markdown mirror of the same content, diffable. |
| `_build\build_docx.py` | Generator. Holds the catalog data and emits both files. |
| `_spec\2026-07-25-...-design.md` | This design. |

**Deviation from the original plan:** the data lives as Python structures inside `build_docx.py`
rather than being parsed back out of `catalog.md`. Parsing markdown tables is fragile; this way
there is exactly one source of truth and `catalog.md` is a rendered output. To revise the catalog,
edit `build_docx.py` and re-run it.

## The two columns that carry the document

HTTP verbs alone do not describe IDMC, because IDMC's verbs do not map onto CRUD:

- **v2 uses POST for both create and update.** `POST /api/v2/connection` creates;
  `POST /api/v2/connection/{id}` updates. There is no PUT on the v2 plane.
- **POST does not imply "can author."** `POST /api/v2/job` *runs* an existing task; it cannot
  create one. `POST /api/v2/mapping` returns 400 — mapping design is not a REST operation.

So every row carries both the raw verbs and a **capability class**:

| Class | Meaning |
|---|---|
| READ | List or inspect metadata |
| RUN | Execute or schedule something that already exists |
| CONFIG | Create/update infrastructure — connections, users, agents, schedules |
| AUTHOR | Define a transform or design object |
| PROMOTE | Export/import for CI/CD promotion |

## Evidence labelling

No new API calls were made for this document. Every row is labelled instead:

| Label | Meaning |
|---|---|
| PROVEN LIVE | An HTTP status was actually observed. Carries code + date + org. |
| DOCUMENTED | Exists per Informatica documentation; not exercised in our testing. |
| BLOCKED | Tried and failed. Carries the real error. |
| UI-ONLY | No REST authoring path exists; the final action is a UI click. |
| NOT ENTITLED | Licensing/provisioning gap, not a capability gap. |

### Org scoping

Capability differs by org, so evidence rows name theirs.

- **ORG-A** — a trial org, legacy v2 ID `<orgIdV2>`, v3 orgUUID `<orgIdV3>`, a `dm-us` pod.
  MDM, Mass Ingestion, API Manager and DAM are **not** provisioned here.
- **ORG-B** — a sub-org, org id `<orgIdV3>`, pod `dmp-us`.
  What the CLAIRE MCP proxy authenticates against. MDM **is** live here.

### Two contradictions in the source corpus, resolved rather than propagated

1. **Catalog scan trigger.** The 2026-06-28 truth matrix records
   `POST /data360/executable/v1/catalogsource/{id}` as **HTTP 500, "blocked by a platform auth
   bug."** The later evidence doc from the same day **disproves it**: the 500 was a client bug —
   missing `IDS-SESSION-ID` and `X-INFA-ORG-ID` headers plus an empty `capabilityNames` body. With
   all three headers and explicit capability names it returns **201 + jobId**. The catalog carries
   the corrected 201 and footnotes the stale claim, so "scan trigger is blocked" stops circulating.

2. **v3 export/import.** One blocker note says `/public/core/v3/export|import` "all 404 — no
   promotion API on this org." Other notes record `POST /public/core/v3/export` → **200** and
   `POST /public/core/v3/import/package` → **200 checksumValid=true**, proven for Person BE,
   Supplier BE, MDM_SRC_SYSTEM, two reference entities and one reference set. Resolution: the
   **migration** export/import-package route works; the *executable* export/import variant 404s.
   Both are recorded, distinguished by path.

3. **Mass Ingestion.** Recorded both as "engines running, authoring is UI-only" and as "not
   entitled, 404, purchase gate." The later live re-verification (2026-07-05) is decisive: login
   `products[]` = `['Integration Cloud']` only, and every MI service path returns 404 "No static
   resource" — the service is not served on this pod. The engines being RUNNING is a red herring;
   **engine-deployed ≠ entitled**. Recorded as NOT ENTITLED on ORG-A with the engine nuance noted.

## Structure

**Part I — Executive layer.** The automatable-vs-UI-only matrix across all 14 services; the
governing principle; the auth model (four distinct planes with different headers — the single
largest source of misleading 401/404/500s).

**Part II — Per-service endpoint tables**, endpoint-level granularity (one row per path, verbs
collapsed into a Verbs column): Platform/Admin & Security · CDI · Mass Ingestion · Database
Ingestion & Replication · CDQ · Data Profiling · CDGC Catalog & Scan · CDGC Governance ·
Reference 360 · CAI · API Manager · MDM/C360 · Operational Insights · CLAIRE & AI.

**Part III — MCP.** Three distinct layers: CLAIRE's native MCP server; the local stdio proxy with
its two injected shims; the self-hosted FastMCP fallback. Plus an MCP-vs-REST division-of-labour
table.

**Part IV — Appendices.** Auth recipes, the known-blockers register, gotchas, and how to re-verify.

## The governing principle

> Everything that **reads** or **runs** is scriptable. Everything that **defines a transform** is
> UI-only — *except* where an existing same-type object can be cloned through the v3 migration
> import/package route, which is the one genuine headless authoring path.

That exception is the most commercially useful finding in the corpus and gets its own callout.

## Out of scope

- No new live probes. Statuses are as-of their recorded dates.
- The `idmc.py` / `cdgc.py` probe clients are **not included** — this folder holds only the
  knowledge base. Reproduction notes therefore cite the KB commands, not runnable scripts.
