# Cleaning a large dataset with IDMC mappings: the hybrid pattern

**Answers:** How do I use IDMC mappings (Cleanse, rule specifications, match, survivorship) to clean a large table that
lives in a fast warehouse, without making every rebuild 10-100 times slower? What does a duplicate-record match look like
as a mapping, and how do I prove it before it changes anything?

**Read when:** a dataset has duplicates, inconsistent values or rule failures to fix; someone asks "can IDMC clean
this?"; or a mapping-based clean-up is much slower than the SQL it replaces.

**Key rules:**
- Measure first, then size the work: full rebuilds stay in the warehouse's own SQL; IDMC mappings clean the **slice that
  needs it** (candidates, changed rows, one region at a time) (L-MDM-085, L-CDI-305).
- A mapping that cleans writes to a **stage table** in a work schema; a separate, reviewed step applies its decisions to
  the real tables. Nothing is merged or overwritten by the first run (L-DQ-165).
- Prove the mapping against a **twin**: the same rule in SQL, read only, compared row by row (decision and survivor) before
  the mapping's output is trusted (L-DQ-165).
- Reuse the org's DQ assets (Cleanse with its dictionary, rule specifications) inside the mapping: that is where IDMC adds
  something the SQL did not have (standardized words, shared rules), not in re-doing joins (L-DQ-166).
- Buildings, condos and multi-unit records are never merged by address alone: they go to `review` (L-DQ-165).

**Related:** [DQ Assets](01-dq-assets-rule-specs-cleanse-dictionaries-verifiers.md) ·
[Profiling](02-profiling-what-is-headless.md) · [DQ Scorecards](04-dq-scorecards-warehouse-pattern-and-data-profiling-scorecards.md) ·
[Mastering a Table](../10-mdm/05-mastering-a-table-repeatable-playbook.md) ·
[Performance, Concurrency & Job Caps](../04-mappings/06-performance-concurrency-job-caps.md)

**Last verified:** 2026-11-18

---

## 1. When mappings, when SQL

| Work | Where it runs | Why |
|---|---|---|
| Full rebuild of a large master (hundreds of millions of rows) | the warehouse's SQL | without pushdown every row leaves the database, crosses the agent and comes back: measured 1,100-18,000 rows/s through mappings against 124,000-660,000 rows/s in set-based SQL on the same server (L-MDM-085) |
| Standardizing words, applying shared DQ rules, scoring | **IDMC mapping** with Cleanse / rule specification mapplets | the org's assets are the single definition; results land in a scorecard table (doc 04) |
| Matching and survivorship on the **candidates** (rows that share a key, rows changed since the last run) | **IDMC mapping** | the slice is small: about 1 % of rows change per build in a large master, and that slice ran in 1-13 minutes in IDMC (L-MDM-085) |
| Applying the merges to the real tables | reviewed SQL (or a mapping's Post SQL) after the twin agrees | one controlled write, with an undo |

A smaller dataset (one region, a few million rows) can run the whole flow as mappings: a one-town flow written fully as
mappings reproduced the SQL flow row for row (L-MDM-085 evidence; L-CDI-305 for pushdown limits).

## 2. The duplicate-record match as a mapping

The shape that worked (stage target in a work schema; every step native):

1. **Source, twice.** Read the candidate rows twice (`ROWS` and `GROUPS`) with the same query. A Joiner of one pipeline
   with itself needs sorted input and fails otherwise ("Choose sorted input ... to join data from the same source").
2. **Sorter right after each reader.** It caches the rows at reader speed, so a warehouse stream never idles past its send
   timeout while the Joiner waits ("Premature EOF" otherwise; L-DQ-166).
3. **Expression: prepare the key parts.** Trim, upper-case, collapse spaces; strip junk tokens your profile found (for
   example a ZIP code pasted into the street field); blank a unit that only repeats the state or ZIP.
4. **Cleanse with the org's dictionary.** Standardize street words (HIGHWAY -> HWY, STREET -> ST ...). This is the step
   that finds the duplicates a plain SQL key misses (L-DQ-166).
5. **Expression: the match key and the guard flags.** Key = house | standardized street | unit | ZIP5. Flags per row: has a
   unit, is a building / condo / multi-unit, residential type, has a parcel record, survivor rank (parcel record first,
   then the oldest).
6. **Aggregator per key** on the `GROUPS` branch: group size, max flags, min / max type, min / max parcel, best survivor rank.
7. **Filter** groups of size > 1.
8. **Expression: the decision.** `review` when any member has a unit, is a building or condo, types are incompatible, or
   two different parcel numbers are present; `merge` otherwise, with the survivor taken from the best rank.
9. **Joiner** of the decided groups back to every member row (`ROWS` branch), so each record gets its decision and survivor.
10. **Target**: the stage table (`region`, `record_id`, `match_key`, `group_size`, `decision`, `reason`, `survivor`, run id
    from `$CurrentTaskId` / `$CurrentRunId`).

## 3. Prove it, then apply it

1. **Twin.** Run the same decision in SQL, read only, and compare per record: in an IDMC group, same decision, same
   survivor. Write the comparison to a file with the run time.
2. **Read the differences.** Records IDMC groups but SQL does not are usually spelling variants the Cleanse standardized
   (they are the value IDMC adds); records SQL groups but IDMC does not point at a key-preparation difference to fix.
3. **Apply** only `merge` decisions the twin agrees on (plus the extra ones a person reviewed), in one reviewed write,
   keeping every old record id as an alias of its survivor so links and pages still resolve.
4. **Re-measure** the duplicate count after the write, and add the run to the scorecard.
5. **After the rule improves, re-count every region already built.** The improvement is not in the live data until each
   region is rebuilt: one region built under the old rule had applied about a thousand merges where the current rule merges tens of
   thousands (L-DQ-167).

## 4. Running it safely

- One region (state, country, business unit) per run; one IDMC job per run. Count jobs against your monthly cap before
  each run (doc 07 of CDI; L-IPU-041).
- Cleanse and deduplicate transformations need a Secure Agent: they do not run on the Hosted Agent (L-CDI-279).
- The stage table is a work table with a named owner and a removal date; it is never read by an application.

## 5. Field results

| Run | Candidates | Agreement with the SQL twin | Extra found by IDMC | Time |
|---|---|---|---|---|
| Region A (over a million verified records) | tens of thousands of records in duplicate groups | every shared record: same decision, same survivor | a few hundred (mostly merges, some review): a highway number written 'HIGHWAY' in one record and 'HWY' in the other | one job |
| Region B (several hundred thousand verified records) | tens of thousands of records in duplicate groups | every shared record: same decision, same survivor | none; 8 review records only the SQL key grouped ('ROAD # REAR' vs 'RD REAR') | 2 min 10 s, one job |
