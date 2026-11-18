# IDMC Endpoint Dictionary — CSV set

The endpoint dictionary as spreadsheets. Same 166 verified endpoints, same 11 MCP actions,
same four verb states as `idmc-endpoint-dictionary.md` and `IDMC API & MCP Master Reference.docx`.

**Generated. Do not hand-edit.** All three views come out of one writer, so they cannot disagree:

```bash
python build/build_dictionary.py --csv
```

UTF-8 with BOM, so Excel opens every file directly — no import wizard.

## Start here

| File | What it is | Rows |
|---|---|---:|
| `01_endpoints.csv` | **One row per endpoint.** The sheet you read. | 166 |
| `02_endpoint_verb_matrix.csv` | **One row per endpoint × verb.** The sheet you pivot and filter. | 830 |
| `03_postman_verb_summary.csv` | The Postman question answered, per verb | 7 |
| `04_service_rollup.csv` | One row per service — endpoint and verb counts | 13 |
| `05_mcp_actions.csv` | Every MCP action, its server, and the REST it wraps | 11 |
| `06_no_endpoint_ui_only.csv` | Operations with **no endpoint at all** | 26 |
| `07_auth_planes.csv` | The 14 auth planes and how many endpoints sit on each | 14 |
| `08_status_code_decoder.csv` | What each status code actually means in IDMC | 15 |
| `09_limits_and_caps.csv` | Documented hard limits | 27 |
| `10_ui_only_walls.csv` | The UI-only walls, in full | 14 |

## Which file to open

- **"What can I call, and how?"** → `01`. Filter `Any working verb? = YES` for the 100 endpoints
  that are scriptable today. `Auth plane` + `Host` + `Header` are the three things that make a call
  succeed; getting them wrong is the single biggest source of false 404s in this platform.
- **"Does verb X work on path Y?"** → `02`. One row per combination, so
  `AutoFilter → State = WORKS` gives you the scriptable surface and nothing else.
- **"Summarise IDMC's verb support for me."** → `03`.
- **Building a Postman collection** → `02`, filtered to `Safe to script today? = YES`. Every row
  already carries the host and the header.

## The four states — never merged

`02`'s `State` column is the whole point of this corpus. All 830 combinations get exactly one:

| State | Rows | Means |
|---|---:|---|
| `WORKS` | 124 | A live status code was observed. Trust it. |
| `DOCUMENTED` | 41 | Informatica documents the verb; nobody exercised it here. Plausible, unproven. |
| `REJECTED` | 96 | Explicitly refused, with the code in `Rejection code`. A `405` is a **finding**: read-only at any permission level. |
| `UNTESTED` | 569 | Nobody probed it. **Unknown, not unsupported.** Never quote one of these as a limitation. |

**`UNTESTED` is the majority, and that is honest reporting, not a gap in the sheet.** Most of the
830 combinations have never been sent. Collapsing untested into "unsupported" is the mistake that
produced every wrong conclusion this project has had to walk back — so the file names it instead of
hiding it. If a verb appears nowhere in the source evidence, it lands here rather than vanishing.

## The Postman answer

| Verb | Works | Documented | Rejected | Untested |
|---|---:|---:|---:|---:|
| `GET` | 82 | 6 | 39 | 39 |
| `POST` | 37 | 9 | 30 | 90 |
| `PUT` | **0** | 14 | 12 | 140 |
| `PATCH` | **0** | 5 | 9 | 152 |
| `DELETE` | 5 | 7 | 6 | 148 |

**IDMC is a GET/POST platform.** Zero `PUT` and zero `PATCH` are proven live anywhere across
166 endpoints. The sanctioned update pattern is `DELETE` then re-`POST`, or on the v2 plane
**`POST` to `/{id}` — that *is* the update**. `HEAD` and `OPTIONS` appear in no guide and no probe:
there is no preflight discovery, so to test whether a write verb exists, `POST` an empty body —
**400 / 415 / 422 means the verb is there**, 405 means it is not.

100 of 166 endpoints have at least one working verb. Of the other 66: 18 are documented but never
exercised, 36 are declared none-proven, and **12 are demoted** — their source row names a verb but
the only evidence is a failure code, so `Demoted` is `YES` in `01` and the verb reads `REJECTED` in
`02` rather than `WORKS`. Plus the 26 operations in `06` that have no endpoint to call at all.

## On MCP

`05` carries all 11 actions. Every one is an HTTP `POST` — MCP has no verb surface of its own, so
intent lives in the action name. Only `checkout_data_order` writes anything. Eight actions are thin
wrappers over a REST endpoint you could call directly, and REST is often *more* capable (raw
Elasticsearch DSL vs one search string; 1,000 addresses per call vs one; full job history vs one
job). **Two are MCP-only:** `get_asset_details` for lineage and `search_master_record` for fuzzy
identity match. Neither has any REST equivalent. `get_master_record_details` is marked `DISPUTED`
because its REST counterpart returns 200 on one org and 404 on another.

## Before you rely on a row

Vendor-documented rows are durable. Live rows are a dated snapshot from specific orgs on specific
pods, and availability genuinely varies by pod, org and entitlement — verdicts in this corpus
flipped on a three-to-five-day cadence. Re-probe what you intend to depend on. The probe harness that
dated these rows reads a local credential file, so it is not shipped with this KB; reproduce its calls
against your own org:

    python probe_idmc_surface.py                # full read-only sweep
    python probe_idmc_surface.py --grep cdgc    # one service

## Not to be confused with the archived `_csv/`

The corpus's `_csv/` folder is the **mined universe**: 440 paths plus 6,898 unproven candidates
harvested from transcripts and docs, useful as a to-probe queue. It was mined from org-specific
sessions, so it is not part of this KB. This folder is the
**verified corpus** only — every row traces to `content/*.json` and carries its evidence.
