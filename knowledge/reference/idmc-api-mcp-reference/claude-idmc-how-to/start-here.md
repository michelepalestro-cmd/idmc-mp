# Claude IDMC How To

> **Currency.** The live evidence behind this folder ends 2026-07-26. Several walls have since fallen
> (design objects authored by package import, the DBMI task lifecycle, a `PUT` on runtime-environment selections, full
> SQL ELT pushdown). Check the currency list in [the Reference Library README](../../README.md) and the topic
> folders before quoting any limit from this folder.

**What IDMC can and cannot do over its APIs and its MCP servers, with the evidence attached.**

## Read this first

### → [`what-idmc-can-and-cannot-do.md`](what-idmc-can-and-cannot-do.md)

Every CAN, every CANNOT and, the part that matters, **which of four kinds of "cannot" you are looking at**:

1. **Hard wall**: no verb exists (`404` empty body, or `405` on everything). Design a human click in.
2. **Read-only resource**: `405`. The route is real, this verb isn't. Use the update pattern.
3. **Not on this pod**: `404` *with* a body. Try another host. Says nothing about entitlement.
4. **Nobody checked**: absent from all evidence. **Unknown, not unsupported.** 574 of the 835 verb
   combinations are in this bucket; never quote one as a limitation.

## The short version

Counts are from the generated set (`csv-every-endpoint/`); re-check them after a rebuild.

**IDMC lets you read almost everything, run almost everything, and design almost nothing.**

- **102 of 167 endpoints** have a proven working verb. 38 `POST`s and 5 `DELETE`s are the corpus's
  entire proven write surface.
- **Zero `PUT` and zero `PATCH`** are proven live in the corpus. Updates are `DELETE` + re-`POST`, or
  on the v2 plane `POST` to `/{id}` *is* the update. (A later `PUT` on runtime-environment selections
  is recorded in the topic folders, not here.)
- **No `HEAD`, no `OPTIONS`.** To test a write verb, `POST` an empty body: `400`/`415`/`422` = the
  verb exists, `405` = it doesn't.
- **28 operations have no endpoint at all** (`06_no_endpoint_ui_only.csv`); the UI-only walls are
  listed in full in `10_ui_only_walls.csv`. Design and publish are the wall; read, run and operate are not.
- **MCP does exactly two things REST cannot:** asset **lineage**, and **fuzzy identity match**. Eight
  of the other nine actions wrap REST, often less capably; one is disputed.

## What else is in here

| File | Use it for |
|---|---|
| [`idmc-endpoint-dictionary.md`](idmc-endpoint-dictionary.md) | Full prose on any one endpoint: what it does, which verbs, which host and header, the evidence. |
| `csv-every-endpoint/02_endpoint_verb_matrix.csv` | **"Does verb X work on path Y?"** One row per combination. Filter `State`. |
| `csv-every-endpoint/01_endpoints.csv` | "What can I call today?" Filter `Any working verb? = YES`. |
| [`csv-every-endpoint/`](csv-every-endpoint/README.md) (8 more) | Postman summary, per-service rollup, MCP actions, UI-only walls, auth planes, status decoder, caps. |

## Generated files: don't hand-edit them

`idmc-endpoint-dictionary.md` and every CSV in `csv-every-endpoint/` are written by one script from
`../content/*.json`. Edits made here are destroyed on the next build. From the repo root (Python 3.10+,
standard library only):

```bash
cd knowledge/reference/idmc-api-mcp-reference
python3 build/validate_content.py           # must exit 0 (warnings are fine)
python3 build/build_dictionary.py --csv     # rewrites this folder
```

The product-by-product master `.docx` is not shipped; `python3 build/build_master.py` renders it
(needs `pip install python-docx`).

`what-idmc-can-and-cannot-do.md` and this file are hand-written. Edit them freely, but re-check the
counts against the CSVs after a rebuild.

## The caveat that matters

Vendor-documented rows are durable. **Live rows are a dated snapshot** (2026-07-25, two orgs, two
pods), and availability varies by pod, org and entitlement. Verdicts in this corpus flipped on a
three-to-five-day cadence. Re-probe anything you are about to promise, using the host and header
from `csv-every-endpoint/07_auth_planes.csv`. The probe harness that dated these rows read a local
credential file, so it is not shipped; reproduce its calls against your own org (method in
`../content/90-provenance.json`).

Four items remain unresolved and are listed in §7 of the CAN/CANNOT doc rather than being quietly
resolved in either direction.
