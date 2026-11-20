# Retail stress suite

Ten real CDI mappings, built from JSON specs by `idmc_mapgen`, that run on a Secure Agent against a synthetic
retail dataset in BigQuery. Every output table is compared row by row with an independent BigQuery query that
computes the expected answer.

| | |
|---|---|
| Seed | 15 tables, about 85,000 rows, deterministic (no `RAND()`), with planted edge cases |
| Mappings | 10 (`m_ex_<scenario>`), 1–4 BigQuery readers each, 110 transformations in total (sources, targets and lookups included) |
| Targets | 25 BigQuery tables (`out_*`) |
| Assertions | 29: keyed row-by-row comparisons, violation checks and row counts |
| IDMC jobs per full pass | 10 (one task run per scenario) |

> **Not included in this repository:** the `suite/` harness (`make_specs.py`, `seed.sql`, `seed_guards.sql`,
> `targets.sql`, `ref/*.sql`, `suite.json`, `check.py`, `profile.vars.example.json`). Only the 10 specs in
> `examples/retail/` ship here. The harness parts below are kept as a record of how the specs were proven; to repeat
> the proof, write your own seed and reference queries (or ask for the harness), and deploy the specs with mapgen.

The rest of this page covers the files, how to run the suite, what each scenario proves, the coverage, the planted
edge cases, how the comparison works, the rules every spec follows, and what a failure probably means.

## Files

Only `examples/retail/m_ex_*.json` is in this repository; every `suite/` path is **not included**.

| Path | What it is |
|---|---|
| `suite/make_specs.py` | One definition of every scenario. It writes the specs, `targets.sql` and `suite.json` (run it after any edit) |
| `examples/retail/m_ex_*.json` | The 10 specs: spec format v1, connection alias `BQ`, `${BQ_PROJECT}` / `${DATASET}` placeholders |
| `suite/seed.sql` | Creates the dataset (US, 14-day table expiration) and the seed tables |
| `suite/seed_guards.sql` | Seed self-test; every number must be 0 |
| `suite/targets.sql` | Empty target tables (generated) |
| `suite/ref/*.sql` | The expected answer per target, in plain BigQuery SQL (`_S0n_base.sql` holds shared CTEs) |
| `suite/suite.json` | Manifest: scenarios, targets with column types, assertions (generated) |
| `suite/check.py` | Runner: `seed`, `guards`, `selftest`, `prepare`, `check`, `refcheck`, `render`, `sql` |
| `suite/profile.vars.example.json` | The two values you supply: `BQ_PROJECT`, `DATASET` |

## Running it on your org

The `python suite/check.py ...` commands below need the harness, which is **not included in this repository**; only
the `mapgen.py deploy` line works with what ships here.

Prerequisites:
- A BigQuery V2 connection in IDMC (Simple mode) whose service account can create tables in the dataset you choose.
- A runtime environment with the Data Integration service.
- The `bq` CLI, already authenticated to the same project. To route SQL through another host instead, set
  `MAPGEN_BQ_RUNNER=vm` and `MAPGEN_VM_PATH=<dir with vm.py>`; `vm.bq(sql, fmt, maxrows)` must return the CLI's CSV.

Steps:

1. Copy `suite/profile.vars.example.json` to a vars file and set `BQ_PROJECT` and `DATASET`. Put the same values in
   your mapgen profile's `vars`.
2. Seed the data and prove the harness. `selftest` loads every expected answer into the targets, checks that all
   assertions pass, and truncates the targets again.
   ```
   python suite/check.py seed --vars vars.json
   python suite/check.py guards --vars vars.json
   python suite/check.py selftest all --vars vars.json
   ```
3. Run each scenario. `prepare` truncates its targets first, because a Bulk "Write truncate" skips a 0-row load and
   would leave old rows behind.
   ```
   python suite/check.py prepare S01 --vars vars.json
   python mapgen.py --profile <your profile> deploy examples/retail/m_ex_customer_cleanse.json --run --execute --expect-org <orgIdV3>
   python suite/check.py check S01 --vars vars.json
   ```

`check` prints one line per assertion: `rows`, `ref` (reference rows), `only_tgt` / `only_ref` (keys present on one
side only), `mismatch` (rows whose values differ) and `dupkeys`, followed by the mismatching columns with their
counts, for example `tier=3 order_ts=12`. It exits 1 if anything fails.

`render S01 --out DIR` writes a spec with the placeholders filled in, for any other compiler.

## Scenarios

| Id | Mapping | Readers | What it proves | Targets |
|---|---|---|---|---|
| S01 | `m_ex_customer_cleanse` | 1 | String cleansing (regex, INITCAP, "Last, First" swap), e-mail/phone validation, previous-row duplicate flag (variable ports over a Sorter), 3-way Router with reason-coded rejects, Data Masking of the valid rows | clean, review, rejects, masked share |
| S02 | `m_ex_order_enrichment` | 4 | Three chained master-outer Joiners (orders, products, customers), NUMERIC money maths, `DECODE(TRUE, ...)` reject codes, a 3-group Router whose HIGH_VALUE group overlaps SALE, DEFAULT1 reject sink | sales, refunds, rejects, high value |
| S03 | `m_ex_customer_value` | 3 | Two stacked Aggregators (distinct-store count without COUNT DISTINCT), conditional aggregates `SUM(x, cond)` / `COUNT(x, cond)`, inner Joiner, unconnected Lookup, `DATE_DIFF`/`TO_INTEGER`, Rank top 5 per region | customer value, top 5 |
| S04 | `m_ex_returns_unified` | 3 | Two differently shaped inputs (online SKU resolved by an unconnected Lookup, free-text reasons classified, US text dates parsed with `IS_DATE`/`TO_DATE`) unioned with a field map, then Filter, Sorter and Sequence surrogate keys, plus an Aggregator | unified returns, reason summary |
| S05 | `m_ex_order_return_recon` | 2 | Two Aggregators feeding a full-outer Joiner on a 2-column key; NULL group keys (receipt-less returns); the Router's DEFAULT1 group must stay empty | reconciled, exceptions, unexpected (empty) |
| S06 | `m_ex_order_share_selfjoin` | 1 | Same-source self-join: Sorter, a sorted-input Aggregator and a sorted-input Joiner (the `set`/`advanced` escape hatches), link field selection with rename | order share, above-average orders |
| S07 | `m_ex_price_scd2` | 2 | SCD type 2: MD5 change detection over a full-outer Joiner; overlapping Router groups send a CHANGED row to both the insert and the expire target; `ADD_TO_DATE` | inserts, expires, unchanged |
| S08 | `m_ex_store_ops_multiflow` | 3 | Two independent flows in one mapping: (A) signed movements, conditional SUMs, detail-outer Joiner on 2 keys; (B) distinct Sorter de-duplication, Filter and Aggregator | inventory position, loyalty balance |
| S09 | `m_ex_sales_local_day` | 4 | Two unconnected Lookups with 2-column keys (UTC offset per zone + UTC hour; FX per currency + day), DST-correct local time, `TRUNC`/`TO_CHAR`, Aggregator per store-day | order local time, store-day |
| S10 | `m_ex_type_fidelity` | 1 | Diagnostic type round trip: unicode, 255-char text, empty vs NULL, quotes and embedded newlines, NUMERIC at scale 9, 64-bit integers above 2^53, doubles, booleans, microsecond timestamps, DATE in and out | type fidelity |

### Transformation coverage

| Node type | S01 | S02 | S03 | S04 | S05 | S06 | S07 | S08 | S09 | S10 |
|---|---|---|---|---|---|---|---|---|---|---|
| source | x | x | x | x | x | x | x | x | x | x |
| target | x | x | x | x | x | x | x | x | x | x |
| expression (OUTPUT + VARIABLE) | x | x | x | x | x | x | x | x | x | x |
| filter |  |  | x | x | x | x | x | x | x |  |
| router (DEFAULT1 used) | x | x |  |  | x |  | x |  |  |  |
| sorter | x |  |  | x |  | x |  | x (distinct) |  |  |
| joiner | | master-outer ×3 | normal | | full-outer, 2-key | sorted, same source | full-outer | detail-outer, 2-key | normal | |
| aggregator |  |  | x ×2 | x | x ×2 | x (sorted) |  | x ×2 | x |  |
| union (field map) |  |  |  | x |  |  |  |  |  |  |
| lookup (unconnected) |  |  | x |  |  |  |  |  | x ×2 (2-key) |  |
| rank |  |  | x |  |  |  |  |  |  |  |
| sequence |  |  |  | x |  |  |  |  |  |  |
| masking | x |  |  |  |  |  |  |  |  |  |

Expression functions used: `IIF`, `DECODE` (value and `DECODE(TRUE, ...)` forms), `ISNULL`, `IS_DATE`, `REG_MATCH`,
`REG_REPLACE`, `INSTR` (incl. negative start), `SUBSTR`, `LPAD`, `LTRIM`/`RTRIM`, `UPPER`/`LOWER`/`INITCAP`,
`LENGTH`, `CHR(39)`, `TO_CHAR` (number, date, `HH24`, `.US`), `TO_DATE`, `TO_DECIMAL`, `TO_INTEGER(x, TRUE)`,
`ADD_TO_DATE`, `DATE_DIFF`, `TRUNC(date, 'DD')`, `ROUND` on NUMERIC, `MD5`, `:LKP.<name>(a[, b])`, `NEXTVAL`,
`RANKINDEX`, and the aggregates `SUM`/`COUNT`/`MIN`/`MAX`, also with filter conditions.

Not covered here (the probe work covers them separately): connected Lookup, Normalizer, Expression window
functions, data-driven upsert/delete targets, mapping parameters, non-BigQuery connectors.

## Planted edge cases (seed.sql)

- **Customers** (2,000):
  - leading, trailing and double spaces; UPPER/lower/mixed case;
  - "Last, First" and "Last,First " formats; NULL and empty names; single-token names;
  - unicode names (María, Zoë, Søren, Siobhán, Østergaard, Müller); apostrophes and hyphens (O'Neil, d'Angelo, Smith-Jones);
  - e-mails that are padded, UPPER-case, invalid or NULL;
  - seven phone formats, including 7-digit numbers, `+1` and `1-` prefixes, NULL and empty;
  - 20 near-duplicate customers whose e-mail differs only in case or spaces;
  - five tier spellings, `Platinum` (unknown) and NULL.
- **Orders** (8,000) and **lines** (20,028):
  - guest orders (no customer); unknown customers; an unknown store;
  - refunds as negative quantities; zero-quantity lines; unknown products; 150 lines with no order;
  - order times clustered around UTC midnight and inside the US (Mar 8) and EU/UK (Mar 29) DST switches;
  - late arrivals (loaded more than 48 h later);
  - four currencies.
- **Returns** (POS 723, online 1,401), in two shapes:
  - POS returns: messy reason codes, over-returns, receipt-less returns, returns of orders that do not exist, zero refunds;
  - online returns: lower-case order references, padded, lower-case or unknown SKUs, refunds in cents, free-text
    reasons, `MM/DD/YYYY HH24:MI` text dates (some invalid: `N/A`, `13/45/2026 25:61`).
- **Inventory**: snapshots (4,000) plus movements (12,000) for stores and products with no snapshot; negative adjustments.
- **Loyalty** (6,120): 120 exact duplicate rows, events with no customer, zero-point events.
- **Price dimension** (764 rows, 1–3 versions per product) and feed (400 rows), which give:
  - 87 changed prices or categories (NULL → value included);
  - 10 discontinued and 20 new products.
- **Lookup tables**: FX rates (4 currencies × 150 days) and UTC offsets (8 zones × 3,600 UTC hours).
- **Type edges** (9 rows): see S10.

## How the comparison works

- **keyed**: the target and the reference are full-outer-joined on `TO_JSON_STRING(STRUCT(<key>))`. That is NULL-safe,
  so rows whose key is NULL compare too. Each reference column is `CAST` to the target's type.
  - Values compare with `IS DISTINCT FROM`.
  - Columns with a tolerance compare as `ABS(a - b) <= tol`: 1e-6 for 6-decimal ratios, 1e-4 for 4-decimal rates.
  - It PASSes when nothing is only on one side, no value differs, no key is duplicated, and the row count is within bounds.
- **violations**: a query returns one number n, and it must be `<= max_violations`. This covers masked values,
  surrogate keys 1..N, and the masked share against the clean rows.
- **count**: the row count must be within bounds. S05's DEFAULT1 target must have exactly 0 rows.

The seed self-test (`guards`) keeps the exact comparisons fair:
- no money value sits exactly on a half cent before `ROUND(..., 2)`, so decimal and double arithmetic agree. Order-line
  discounts and FX rates are nudged by one step where needed.
- no 6- or 4-decimal ratio sits on a half step;
- there is no tie at the Rank top-5 cut;
- the lookup keys are unique;
- every order falls inside the lookup tables' date range.

## Rules every spec follows (and why)

| Rule | Why |
|---|---|
| ≤ 4 BigQuery readers (sources + lookups) per mapping; reader STRING precision 256 | The agent-wide DTM heap ran out with 7–8 readers, and STRING 4000 allocates huge row buffers |
| BigQuery targets: truncate (Write truncate, Bulk), 1 s job poll attributes | `WriteOptions.truncate` alone is ignored; the writer's default 10 s poll adds ~9 s per target (the generator now writes the 1 s poll by default; the suite's specs also set it themselves) |
| A DATE column is written from a STRING `'YYYY-MM-DD 00:00:00'` (target field declared STRING); a DATE source column is read as `CAST(... AS TIMESTAMP)` | A workaround from before DATE worked: the generator used to give DATE adapter fields the Java type `java.sql.Date`, and every run failed with "Unknown native type". It now writes `java.sql.Timestamp`, so BigQuery DATE columns read and write natively (`examples/fixes/m_ex_fix_bq_date.json`). The suite keeps the STRING / CAST form, so its specs and reference answers stay as they are, and S10 still exercises that path |
| Expression OUTPUT ports never read other OUTPUT ports; VARIABLE ports carry the intermediates | CDI rejects OUTPUT → OUTPUT references |
| Every source column is aliased with a per-source prefix (`ln_`, `o_`, `p_`, `c_`, …) | Joiner master/detail names never collide, and Expression outputs get fresh names |
| The one same-source Joiner (S06) uses a Sorter, a sorted-input Aggregator and a sorted-input Joiner | One source feeding both sides unsorted hangs the session with no error |
| Masked fields come out as `out_<field>` for every input field; an Expression renames them | That is how the Data Masking transformation emits its group (proven in a scheduled mapping) |

## Triage: what a failure probably means

| Symptom | Likely cause | Where to look |
|---|---|---|
| Import fails on S01 `EXP_PREV_ROW` | Forward reference to a variable port (`v_prev_key`) or a self-reference (`v_seq`) not accepted | Swap to two Expressions, or a Rank/Aggregator design |
| S01 `std_name` mismatches only on non-ASCII names | Informatica `INITCAP` treats accented letters as word breaks (the reference assumes they are letters) | Compare the failing rows; adjust the reference delimiters |
| S06 run never finishes | Same-source Joiner deadlock despite sorted input | Stop the job (the timeout is the test); the session log shows the Joiner waiting |
| S09 `offset_min` all NULL | The 2-column condition of an unconnected Lookup is not honoured (single-key lookups are proven) | The `LKP_TZ_OFFSET` cache build in the session log |
| Timestamps or dates off by whole hours in S02/S03/S09 | The DTM converts BigQuery TIMESTAMP to agent-local time (the reference assumes UTC) | The agent host's time zone |
| S04 `return_sk` not matching while everything else matches | Sequence values were not assigned in Sorter order | Sorter → Sequence ordering |
| S10 `f_val`, `b_str`, `s_empty`, `ts_micro`, `s_quote` mismatches | Platform type behaviour: double precision, boolean rendering, empty string vs NULL through Bulk loads, microseconds, embedded newlines/quotes | Diagnostic: record it as a type finding, not a generator bug |
| S10 row 99 missing | NUMERIC wider than 28 digits (20 integer digits) overflows the default decimal(28,9) field | Raise the field precision in the spec (decimal up to 38) |
| Any keyed check: `only_ref` = all rows, `rows=0` | The run wrote nothing, or wrote to another table | The task's activity log; `prepare` was run before |
