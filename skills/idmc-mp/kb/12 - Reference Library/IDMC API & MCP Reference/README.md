# IDMC API & MCP knowledge base

**The master document:** `IDMC API & MCP Master Reference.docx` — 30 sections, 73 tables and
641 data rows covering 167 distinct endpoints (counts from the 2026-10-03 rebuild).

Everything this knowledge base knows about what Informatica IDMC can do over its APIs and over MCP,
in one document, **organised by product**. Each IDMC service gets one section containing one big
table of every endpoint in that service, the exact HTTP verbs it accepts, and what it does — with
that same service's MCP coverage immediately underneath, so both interfaces for one product sit
side by side.

> **The .docx is generated. Do not edit it.** The truth lives in `content/*.json`.
> Edit those, then run the builder. Edits made in Word are destroyed on the next build.

---

## Working on it

```bash
cd "<KB root>\12 - Reference Library\IDMC API & MCP Reference"

python build/validate_content.py         # is the tree clean?
#    ... edit ONE file in content/ ...
python build/validate_content.py 12-cdi  # check just your section (must exit 0)
python build/build_master.py             # regenerate the master document
python build/build_dictionary.py --csv   # regenerate "Claude IDMC How To" (dictionary + CSVs)
```

`<KB root>` is the Master IDMC KB folder. All three scripts read and write only inside this folder.
Close the .docx in Word before running `build_master.py`, or the save fails with a permission error.

The Claude skill that was once generated from this corpus (`build_skill.py`, `skill_src/`, `skill/`,
`skill-public/`) is org-specific, so it is not part of this KB.
Do not recreate it in this folder.

**Agents: read `AGENTS.md` first.** It is the contract — section ownership, the status vocabulary,
and the rules that keep parallel work from destroying itself.

## Why it is structured this way

This folder previously held two .docx deliverables, and several agents working at once produced the
predictable failures: one session appended a whole addendum to a file another session was rebuilding,
content appeared twice under different headings, and a binary file cannot be merged or diffed. So the
content was lifted out of the document:

- **`content/*.json` — one file per section.** Two agents editing different sections touch different
  files and physically cannot collide. Diffable, greppable, reviewable.
- **`build/build_master.py` — the only thing that writes the .docx.** Deterministic: same content in,
  same document out. The document is disposable; the content is not.
- **`build/validate_content.py` — the gate.** Catches malformed rows, invented status values,
  unsourced claims and future-dated verification stamps before they reach the document. Verified to
  reject both a wrong cell count and an off-vocabulary status.

Two agents editing two sections simultaneously was tested: both edits landed, nothing was lost, and
the validator stayed clean.

## What is in the folder

| Path | What it is |
|---|---|
| `IDMC API & MCP Master Reference.docx` | **The deliverable.** Generated — never hand-edit. |
| `Claude IDMC How To/` | **Start here to answer "can IDMC do X?"** — the CAN/CANNOT write-up, the endpoint dictionary, and the verified corpus as 10 CSVs. The dictionary and CSVs are generated; see its `START HERE.md`. |
| `AGENTS.md` | The contributor contract. Read before editing. |
| `content/*.json` | **The source of truth.** One file per section. |
| `build/build_master.py` | Renders the master document. |
| `build/build_dictionary.py` | Renders the endpoint dictionary and, with `--csv`, the CSV set. Read-only over `content/`. |
| `build/validate_content.py` | Validates content before a build. |
| `build/seed_content.py` | One-time migration from the old .docx files. Do not re-run (its input is archived). |
| `build/restructure_services.py` | One-time reshape of the service sections (2026-07-25). Do not re-run (its inputs are archived). |
| (not bundled) | Informatica product guides — the vendor evidence — at https://docs.informatica.com. |
| `_spec/` | The 2026-07-25 catalog design note, kept for history. |

## Raw evidence and anonymisation

The live evidence behind this corpus was captured against specific orgs and names them, so it is not
part of this KB: the probe results, vendor extracts and migration audit trail (incl.
`_extracted_all_tables.json`), the mined universe (440 paths + 6,898 unproven candidates, a to-probe
queue), earlier build scripts and legacy data modules, the org-specific Claude skill sources and
builders, and the live probe harness `probe_idmc_surface.py` (it reads a local credential file).
Nothing in this folder needs any of it at build time.

In this folder the orgs are anonymised. **Org A** is an org on a dm-us pod, **Org B** is a sub-org on a
dmp-us pod, and "the parent org" is Org B's parent on the same pod. IDs, IPs, pod, host and database
names are placeholders (`<pod>`, `<orgIdV2>`, `<orgIdV3>`, `<agentId>`, `<reId>`, `<connId>`,
`<private-ip>`, `<db>`). Every status code, count, date and verdict is as observed.

## The document's own conventions

The service tables use **only the five Postman verbs** — no READ/WRITE/RUN vocabulary. The
`Verbs supported` column lists every verb an endpoint accepts:

| What you see | What it means |
|---|---|
| `GET, POST, DELETE` | All three verified working against a live org. |
| `PUT [doc]` | Informatica documents that verb; it was not exercised. Unproven. |
| `UI only` | The operation exists, but only in the interface. No verb reaches it. |
| `none proven` | No verb shown to work on this path. The notes say why. |

Rejections and gaps live in the notes column: `rejected: PUT 405` means that verb was explicitly
refused (405 = read-only, a hard no); `untested: PUT, PATCH` means nobody probed them.

> **`untested` and `rejected` are never merged.** Untested is an admission of ignorance; a 405 is a
> finding. Conflating them produced every wrong conclusion this project has had to walk back.

MCP has no verb surface of its own — every MCP call is an HTTP POST to one server endpoint carrying
a JSON-RPC body naming an action, so intent lives in the action name. Only five of the thirteen
services have any MCP coverage at all.

## What the document establishes

**On API versus MCP.** The verb question does not apply to MCP at all — every MCP call is an HTTP
POST to a single server endpoint carrying a JSON-RPC body naming an action, so read-versus-write
intent lives in the action name, not a verb. Seven of the eleven MCP actions are thin wrappers over
a REST endpoint, and REST is often *more* capable. MCP can do exactly two things REST cannot: read
asset **lineage**, and **fuzzy customer identity match**. Neither can author a design-time asset.

**Corrections to long-held beliefs**, all from official vendor documentation: CAI bulk publish is a
supported API, not a bypass; CDQ dictionaries have real CRUD (but no GET at all); Data Profiling has
documented profile CRUD; Operational Insights is GraphQL, not REST; `active-bpel/restadmin` is the
richest runtime-control plane in the platform; Mass Ingestion is entitled and running, not missing.

**Open questions are carried, not hidden.** The master collects every section's open questions into
one table near the front. Four items are genuinely disputed and flagged as such rather than resolved
in either direction.

## Superseded

`IDMC API & MCP Capability Reference.docx` and `IDMC Verb Matrix - API vs MCP.docx` were merged into
the master on 2026-07-25 and retired. All 633 of their data rows are in `content/`; the extraction
record is kept with the raw evidence, outside this KB. Do not resurrect them — add to the master instead.

## Before customer use

Vendor-documented rows are durable. Live rows are a dated snapshot from specific orgs on specific
pods, and endpoint availability genuinely varies by pod, org and entitlement — verdicts in this
corpus flipped on a three-to-five-day cadence. Re-probe the specific rows you intend to rely on.
