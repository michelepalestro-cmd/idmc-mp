# Claude IDMC How To

> **Currency.** This guide is a snapshot of the live evidence up to 2026-07-26. Several walls below have since fallen
> (design objects authored by package import, the DBMI task lifecycle, a `PUT` on runtime-environment selections, full
> SQL ELT pushdown). Check the currency list in [the Reference Library README](../../README.md) and the topic
> folders before quoting any limit from this file.

**What IDMC can and cannot do over its APIs and its MCP servers — stated outright, with the
evidence attached.**

## Read this first

### → [`what-idmc-can-and-cannot-do.md`](what-idmc-can-and-cannot-do.md)

The whole answer in one file. Every CAN, every CANNOT, and — the part that actually matters — **which
of four kinds of "cannot" you are looking at**:

1. **Hard wall** — no verb exists (`404` empty body, or `405` on everything). Stop and design a human
   click in.
2. **Read-only resource** — `405`. The route is real, this verb isn't. Use the update pattern.
3. **Not on this pod** — `404` *with* a body. Try another host. Says nothing about entitlement.
4. **Nobody checked** — absent from all evidence. **Unknown, not unsupported.** 569 of 830 verb
   combinations are in this bucket; never quote one as a limitation.

## The short version

**IDMC lets you read almost everything, run almost everything, and design almost nothing.**

- **100 of 166 endpoints** have a proven working verb. 37 `POST`s and 5 `DELETE`s are your entire
  write surface.
- **Zero `PUT` and zero `PATCH`** are proven live, anywhere. Updates are `DELETE` + re-`POST`, or on
  the v2 plane `POST` to `/{id}` *is* the update.
- **No `HEAD`, no `OPTIONS`.** To test a write verb, `POST` an empty body: `400`/`415`/`422` = the
  verb exists, `405` = it doesn't.
- **14 confirmed UI-only walls** + 12 more endpointless operations. Design and publish are the wall;
  read, run and operate are not.
- **MCP does exactly two things REST cannot:** asset **lineage**, and **fuzzy identity match**. The
  other 9 actions wrap REST, often less capably.
- **Nine former "walls" were wrong** — CAI publish, scheduling, Marketplace, Profiling, Mass
  Ingestion and MDM entitlement among them. Check that list before repeating a limitation.

## What else is in here

| File | Use it for |
|---|---|
| `idmc-endpoint-dictionary.md` | Full prose on any one endpoint — what it does, which verbs, which host and header, the evidence. Alphabetical. |
| `CSV - every endpoint\02_endpoint_verb_matrix.csv` | **"Does verb X work on path Y?"** 830 rows, one per combination. Filter `State`. |
| `CSV - every endpoint\01_endpoints.csv` | "What can I call today?" Filter `Any working verb? = YES`. |
| `CSV - every endpoint\` (8 more) | Postman summary, per-service rollup, MCP actions, UI-only walls, auth planes, status decoder, caps. See its own `README.md`. |
| `..\IDMC API & MCP Master Reference.docx` | The full narrative, organised by product. Lives one level up — it is the master deliverable and deliberately not duplicated here. |

## These files are generated — don't hand-edit them

`idmc-endpoint-dictionary.md` and everything in `CSV - every endpoint\` are written by one script
from one source of truth (`..\content\*.json`), so the prose, the CSVs and the master document cannot
disagree with each other. Edits made here are destroyed on the next build.

```bash
cd "<KB root>\knowledge/12-reference-library\IDMC API & MCP Reference"
python build/build_dictionary.py --csv     # this folder
python build/build_master.py               # the .docx one level up
```

`what-idmc-can-and-cannot-do.md` and this file are hand-written — edit them freely, but re-check the
counts against the CSVs after a rebuild.

## The one caveat that matters

Vendor-documented rows are durable. **Live rows are a dated snapshot** — 2026-07-25, two orgs, two
pods — and availability genuinely varies by pod, org and entitlement. Verdicts in this corpus flipped
on a **three-to-five-day cadence**. Re-probe anything you're about to promise a customer, using the
host and header from `CSV - every endpoint\07_auth_planes.csv`. The probe harness that dated these
rows (`probe_idmc_surface.py`) reads a local credential file, so it is not shipped with this KB;
reproduce its calls against your own org:

    python probe_idmc_surface.py                # full read-only sweep
    python probe_idmc_surface.py --grep cdgc    # one service

Four items remain genuinely unresolved and are listed in §7 of the CAN/CANNOT doc rather than being
quietly resolved in either direction.
