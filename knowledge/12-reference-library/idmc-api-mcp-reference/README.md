# IDMC API & MCP reference

Everything this corpus knows about what Informatica IDMC can do over its APIs and over MCP,
**organised by product**. Each IDMC service has one section with one table of every endpoint in that
service, the exact HTTP verbs it accepts and what it does, with that service's MCP coverage
immediately underneath. As of the 2026-10-03 rebuild: 30 sections, 167 distinct endpoints, 11 MCP
actions, 28 operations with no endpoint.

**The source of truth is `content/*.json`.** Everything else is generated from it.

**Agents: read [`AGENTS.md`](AGENTS.md) first.** It is the contract: section ownership, the status
vocabulary, and the rules that keep parallel work from destroying itself.

## What is in the folder

| Path | What it is |
|---|---|
| [`claude-idmc-how-to/`](claude-idmc-how-to/start-here.md) | **Start here for "can IDMC do X?"**: the CAN/CANNOT write-up (hand-written), the endpoint dictionary and 10 CSVs (generated). |
| `content/*.json` | **The source of truth.** One file per section. |
| `build/validate_content.py` | Validates content before a build. Standard library only. |
| `build/build_dictionary.py` | Renders `claude-idmc-how-to/idmc-endpoint-dictionary.md` and, with `--csv`, `claude-idmc-how-to/csv-every-endpoint/*.csv`. Read-only over `content/`. Standard library only. |
| `build/build_master.py` | Renders the product-by-product master document, `idmc-api-mcp-master-reference.docx`. The `.docx` is not shipped; build it when you need it (needs `pip install python-docx`). |
| `AGENTS.md` | The contributor contract. |

## Working on it

From the repo root, with Python 3.10+:

```bash
cd knowledge/12-reference-library/idmc-api-mcp-reference
python3 build/validate_content.py           # is the tree clean? (must exit 0; warnings are fine)
#    ... edit ONE file in content/ ...
python3 build/validate_content.py 12-cdi    # check just your section
python3 build/build_dictionary.py --csv     # regenerate the dictionary and the CSVs
python3 build/build_dictionary.py --check   # or: render and print counts, write nothing
python3 build/build_master.py               # optional: the .docx (python-docx)
```

All three scripts read and write only inside this folder. Then run
`python3 toolkit/tools/secret_scan.py .` from the repo root.

## Why it is structured this way

Several agents once edited two binary `.docx` deliverables at the same time: one session appended an
addendum to a file another was rebuilding, content appeared twice under different headings, and a
binary cannot be merged or diffed. So the content was lifted out of the document:

- **One JSON file per section.** Two agents editing different sections touch different files.
- **Deterministic builders.** Same content in, same output out. The outputs are disposable.
- **A validator as the gate.** It catches malformed rows, invented status values, unsourced claims
  and future-dated verification stamps.

The `content/` files were seeded on 2026-07-25 from two superseded documents ("IDMC API & MCP
Capability Reference" and "IDMC Verb Matrix - API vs MCP", 633 data rows in all) and from probe
evidence kept outside this repo. Do not resurrect those documents; add to `content/` instead.

## Conventions

The service tables use **only the five Postman verbs**. The `Verbs supported` column lists every verb
an endpoint accepts:

| What you see | What it means |
|---|---|
| `GET, POST, DELETE` | All three verified working against a live org. |
| `PUT [doc]` | Informatica documents that verb; it was not exercised. Unproven. |
| `UI only` | The operation exists, but only in the interface. No verb reaches it. |
| `none proven` | No verb shown to work on this path. The notes say why. |

Rejections and gaps live in the notes column: `rejected: PUT 405` means that verb was explicitly
refused; `untested: PUT, PATCH` means nobody probed them. **`untested` and `rejected` are never
merged**: untested is an admission of ignorance, a 405 is a finding.

MCP has no verb surface of its own: every MCP call is an HTTP POST to one server endpoint carrying a
JSON-RPC body naming an action. MCP does exactly two things REST cannot: read asset **lineage**, and
**fuzzy customer identity match**.

## Raw evidence and anonymisation

The live evidence was captured against specific orgs and names them, so it is not in this repo: the
probe results, vendor extracts and migration audit trail, the mined universe (440 paths + 6,898
unproven candidates), and the probe harness `probe_idmc_surface.py` (it reads a local credential
file). Nothing here needs any of it at build time. To re-date a live row, reproduce the probe
against your own org (method in `content/90-provenance.json`).

The orgs are anonymised: **Org A** is an org on a dm-us pod, **Org B** is a sub-org on a dmp-us pod,
and "the parent org" is Org B's parent. IDs, IPs, pod, host and database names are placeholders
(`<pod>`, `<orgIdV2>`, `<orgIdV3>`, `<agentId>`, `<reId>`, `<connId>`, `<private-ip>`, `<db>`).

## Before customer use

Vendor-documented rows are durable. Live rows are a dated snapshot (2026-06-28 to 2026-07-26), and
endpoint availability varies by pod, org and entitlement; verdicts flipped on a three-to-five-day
cadence. Later evidence in the topic folders overturns some walls (see the currency list in
[the Reference Library README](../README.md)). Re-probe the rows you intend to rely on.
