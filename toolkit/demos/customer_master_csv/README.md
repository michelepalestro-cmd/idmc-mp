# Customer mastering from a CSV (blueprint `customer_master_csv`)

**The user story:** "I have a messy customer CSV. Clean it, find the duplicates, give every real customer one id, and
give me a clean CSV back." Built with IDMC on a Secure Agent, from native transformations only: no Data Quality or MDM
licence and no other system to set up.

| You start with `customers_raw.csv` | You get `customers_golden.csv` + `customer_xref.csv` |
|---|---|
| `"  Hernandez,   Patricia "`, `" RICHARD.MILLER146@example.com  "`, `563.555.0126`, `Wisconsin`, `52732-7648`, the same person on up to four rows | `Patricia Hernandez`, `richard.miller146@example.com`, `(563) 555-0126`, `WI`, `52732`, one row per real customer with a stable `CUST-000123` id, and a cross-reference from every source row to its customer id |

## How it works (one mapping, 9 transformations)

```
SRC customers_raw.csv
 -> EXP_STANDARDIZE   trim and collapse spaces; "Last, First" -> "First Last"; name case; e-mail lower case and
                      validated; phone -> 10 digits (drops a leading 1); address upper case, ST/AVE/RD; state name ->
                      code; ZIP -> 5 digits (restores a dropped leading zero); a completeness score
 -> SRT_BY_BLOCK      block = name + ZIP; records with an e-mail and a phone first
 -> EXP_CLUSTER       a new customer starts when the block changes, or when a known e-mail or phone conflicts;
                      assigns CUST-###### and how the record joined (FIRST, EMAIL, PHONE, NAME+ZIP)
 -> SRT_BY_CUSTOMER   most complete, then most recent record first
 -> EXP_SURVIVOR      one survivor per customer
 -> FIL_SURVIVORS -> customers_golden.csv      (one row per customer)
 -> customer_xref.csv                          (every source row -> its customer id)
```

The spec is [mapping/m_customer_master_csv.json](mapping/m_customer_master_csv.json); the plugin's mapping generator
turns it into a real IDMC mapping and import package. The method is the "match in native steps" pattern of
[Cleaning a large dataset with mappings](../../../knowledge/08-data-quality/05-cleaning-a-large-dataset-with-mappings.md).

## Try it now, offline (no login, under a second)

```
python3 check.py
```

It makes a messy sample (fictional names, `@example.com` e-mails, `555-01xx` phones) with an answer key, lints and
builds the IDMC package, runs the Python twin that applies the same rules to produce the expected output, checks the
results, and scores the match. It writes into a new temp folder (it prints the path) and never into the plugin
folder; `--out <folder>` picks the folder. On the default sample: 281 messy records -> 150 customers, precision 1.00,
recall 1.00. On 2,000 people (`--customers 2000`, 3,764 records): precision 0.996, recall 0.983, in about 0.2 s; the
few errors are records whose name or ZIP is damaged badly enough to sit in the wrong block (see Limits).

| File | What it is |
|---|---|
| `make_sample.py` | the messy sample and its answer key (`data/` under the output folder) |
| `mapping/m_customer_master_csv.json` | the mapping spec |
| `reference.py` | the Python twin: same rules, same order, same IDMC function behaviour (`expected/`) |
| `check.py` | the timed offline proof; `--compare <folder>` diffs a live run's output against the twin |
| [BUILD.md](BUILD.md) | the live run: Secure Agent, flat-file connection, deploy, run, compare, with a timing log |

## Run it in your org

Follow [BUILD.md](BUILD.md). You need an IDMC org, a Linux (or Windows) machine for the Secure Agent, and the plugin
connected (`/informatica-idmc-headless:connect`). Expect about 20-40 minutes the first time, most of it the agent install.

## Limits, on purpose

- Matching is deterministic: a person whose name or ZIP is badly damaged in one record stays split (that is the recall
  you give up for never merging two different people). Fuzzy matching needs Data Quality assets (`dedup` node) or MDM.
- The survivor is a whole record (the most complete, most recent); it does not mix fields from several records.
- Use your own data: put your file (same header) in place of the generated `customers_raw.csv` on the agent, or change the source fields in the
  spec. Put `(blank)` in empty cells: an empty field can fail an IDMC CSV source (L-CONN-066), and the mapping reads
  `(blank)` as empty.
