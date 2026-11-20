# Data quality and profiling: cheat sheet

Profile a table, author DQ rule specifications, run and score them, and clean or deduplicate data with IDMC Cloud Data
Quality (CDQ): use this whenever a user asks for profiling, DQ rules, scores, scorecards or a clean-up.

**Start with:** `/idmc-mp:add-dq <connection> <table>` (profile, rules, scores) or `/idmc-mp:clean-data` (standardize,
match, survivors); census the org's DQ assets with `toolkit/lib/idmc_objects.py`; open
[02 Profiling: what is headless](02-profiling-what-is-headless.md) first.

**No CDQ licence?** Check first (privileges and DQ objects, the method of L-MDM-011). Without it, clean and deduplicate
a customer file with plain CDI mappings: [customer master from a CSV](../../toolkit/demos/customer_master_csv/README.md).

**The law:** DQ authors and measures; a CDI mapping on a Secure Agent executes. DQ alone never writes cleansed data to a
target (L-DQ-001, L-DQ-002). SQL that imitates cleansing is not IDMC DQ: label each result IDMC-native or SQL (L-DQ-004).

## What works (headless)

| Task | How (exact route/tool/command) | Lesson |
|---|---|---|
| List, read, create, update a profile | `<pod>-dqprofile` `/profiling-service/api/v1/profile` (GET, POST a body cloned from a profile on the same connection type, PUT the full body), header `IDS-SESSION-ID` | L-DQ-019, L-DQ-128 |
| Run and poll a profile | `POST /profile/<id>/execute` -> `profileJobId`; poll `GET /job/<profileJobId>` (status + `jobSteps`) | L-DQ-019, L-DQ-149 |
| Bind rule specs to columns | inside the profile body: one `source.rules[]` block per rule spec, one `MAPPLETFIELD` per column; PUT, re-run | L-DQ-023 |
| Read per-rule pass rates | metric store `Profiles('<id>')/Columns('<columnId>')/ValueFrequencies` on the rule's `Output` column (VALID/INVALID); keep entries whose `totalRows` = the column's current `totalRows` | L-DQ-123, L-DQ-151 |
| Count profile runs (job budget) | job log service `JobLogEntries?$filter=assetType eq 'PROFILE'` (not in the v2 activity log) | L-DQ-106 |
| Read rule specs | `GET /public/core/v3/objects?q=type=='RULE_SPECIFICATION'`; ports via `POST /saas/api/v2/extensionPoint` `RuleSpecificationTx.getDescription` | L-DQ-009, L-DQ-109 |
| Author a rule spec | clone a same-type template: v3 export -> new GUID + name -> re-hash SHA-256 -> import/package (multipart) -> import to SUCCESSFUL | L-DQ-010 |
| Change a rule spec description | `PATCH /frs/v1/Documents('<frsId>')` `{"description": ...}` -> 204 | L-DQ-094 |
| Read a rule spec's logic | v3 export: `nativeData.documentBlob` -> `ruleModel` (both JSON strings: parse twice) | L-DQ-104 |
| Dictionaries | `<pod>-dqcloud-api` `/quality/public/v2/dictionaries/` create (201) + rows + mandatory `finishUpload`; no GET: keep the id | L-DQ-006 |
| Execute rules / cleanse / dedupe on real data | Rule Specification, Cleanse, Deduplicate transformations in a CDI mapping on a Secure Agent | L-DQ-001, L-DQ-165 |
| Scores an app can read | CDI mapping task writing `dq_results` per rule and `dq_scorecard` per dimension | L-DQ-054, L-DQ-055 |
| Catalog DQ score (CLAIRE reads it) | runtime env in the source's Scope groups, rule instances, `capabilityNames: ["Data Quality"]` | L-DQ-097 |
| File-based profile + generated cleansing | `dataqualityagent` MCP: `request_upload_url` -> PUT -> `data_quality_cleansing` (two calls) | L-DQ-072, L-DQ-073 |
| Address verification | cloud REST `.../addressverification/api/v1/process` (1,000 per call) or MCP `verify_address` (one per call) | L-DQ-015, L-DQ-016 |

## What doesn't work, and the workaround

| Wall | Workaround | Lesson |
|---|---|---|
| `POST /public/core/v3/objects` for a rule spec or profile: 405; `/data360/dq/*`: 404 | clone through v3 export/import; profiles via `POST /profile` | L-DQ-010, L-DQ-025 |
| CDQ public REST has no rule, scorecard or profile endpoints | profiling service on `<pod>-dqprofile`; warehouse scorecard | L-DQ-009, L-DQ-050 |
| Running a profile through `/api/v2/job`: 403 UI_13404 | `POST /profile/<id>/execute` | L-DQ-024 |
| Profiling on the Cloud Hosted Agent: EP_13236 `libpmdpaggregate.so` | enable the Data Quality service on a Secure Agent; set `runtimeOptions.runtimeEnvironmentId` to its federatedId | L-DQ-114, L-DQ-115 |
| DQ agent skills other than cleansing on an uncataloged table: empty answers | catalog the source first, or use file-based `data_quality_cleansing` | L-DQ-071 |
| DQ agent rule generation saves nothing | put the logic in a rule spec (UI or clone) bound to a profile or mapping | L-DQ-079 |
| BigQuery V2 samples All Rows only | build a deterministic hash-sample table, profile it with All Rows | L-DQ-102, L-DQ-099 |
| Catalog-source profiling of BigQuery fails | profile BigQuery with Data Profiling profiles | L-DQ-110 |
| Deduplicate is not MDM (no trust, xref, unmerge, stewardship) | call it "dedupe + consolidate"; position MDM for those | L-DQ-164 |

## Fastest safe path

1. Prove the org (`toolkit/check_login.py`); census DQ assets and existing profiles (`GET /profile?limit=1000`, assert
   count < limit). Read-back: counts per asset type (L-DQ-155).
2. Measure fill rates and size the run (sample table at most 100k rows, about 50 columns; one profile at a time; PII
   columns left out). Read-back: the column list and excluded count (L-DQ-142, L-DQ-102, L-DQ-098, L-DQ-157).
3. Create the profile by cloning a body that has already run on the same connection type, no client ids. Read-back:
   `GET /profile/<id>` (L-DQ-021, L-DQ-128).
4. Execute and poll the job id. Read-back: `GET /job/<jobId>` COMPLETED with all `jobSteps` done (L-DQ-150).
5. Propose rules from the profile (and CLAIRE insights); take closed lists from the dictionary, not observed values.
   Read-back: the user's yes per rule (L-DQ-122, L-DQ-153).
6. Clone rule specs from templates; validity rules pass blanks, one separate "value present" rule. Read-back: the
   RULE_SPECIFICATION census rises (L-DQ-010, L-DQ-154).
7. Bind them in the profile, re-run, read pass rates from the metric store. Read-back: VALID/INVALID per binding
   (L-DQ-023, L-DQ-123).
8. Prove the detector: spot-check a frozen sample in SQL; seed one violation and watch it go red. Read-back: equal rates
   (L-DQ-147, L-DQ-060).
9. For dashboards, land results in `dq_results` / `dq_scorecard` with a CDI task. Read-back: SQL row counts (L-DQ-055).

## Top traps

- 500 "Row was updated or deleted" on `POST /profile` -> client-side ids in the body -> strip every id (L-DQ-021).
- 401 "Exception encountered while processing JWT" on `-dqprofile` -> v2 session on a pod that wants v3 -> send the v3
  login `sessionId` (L-DQ-020).
- A profile PUT that omits rules changes nothing -> send them with `isDeleted: true`, read back (L-DQ-116).
- Failed run but `runDetail` shows the old COMPLETED -> `lastRunKey` does not advance -> track the execute job id
  (L-DQ-150).
- `GET /profile` ignores `offset` -> paging loops on page one -> one large `limit`, assert the count (L-DQ-155).
- "Cannot parse null string" on BigQuery profiles -> empty hidden retry attributes on a REST-made connection -> fill the
  connector defaults (L-DQ-110).
- 500 PROFILE_SVC_00004 -> SQL Override over 4,000 characters -> split columns across profiles (L-DQ-133).
- Zero columns profiled, `pmdtm` exit 127 -> missing `libidn.so.11` -> symlink it to `libidn.so.12` (L-DQ-036, L-DQ-037).
- Deduplicate matches nothing -> unique id mapped into its `Id` match field -> leave it out (L-DQ-101).
- `dq_status = passed` on every row with no score -> a constant stamp -> compute status from rule results and make the
  gate able to fail (L-DQ-121, L-DQ-143).
- Rule spec changed, mapping shows Invalid in the designer while the API says valid -> resynchronize or regenerate from
  the current export; copy field precision and scale (L-DQ-126, L-DQ-113).
- DQ agent upload PUT 409 -> HTTP/2 or `Expect: 100-continue` used the single-use URL -> `curl --http1.1 -H "Expect:"`,
  unique filename, re-mint (L-DQ-072).
- CLAIRE rules built from a small profile slice break in production -> take bounds from percentiles, check the slice's
  bias, write year windows relative to today (L-DQ-174); keep recommendations as governed rule rows (L-DQ-173).
- The same rule gives different numbers in different engines -> one counting convention: NULL fails, uniqueness counts
  surplus copies, a finding is not a failed run (L-DQ-175). On BigQuery pack rules into one query per table (L-DQ-176).

## Go deeper

- [01 DQ assets](01-dq-assets-rule-specs-cleanse-dictionaries-verifiers.md): rule specs, cleanse, dictionaries, verifiers, address verification.
- [02 Profiling: what is headless](02-profiling-what-is-headless.md): the three profiling paths, REST routes, sizing, agent fixes.
- [03 CLAIRE DQ agent](03-claire-dq-agent-file-based-profiling-cleansing.md): file upload, two-call cleansing, applying the generated code.
- [04 DQ scorecards](04-dq-scorecards-warehouse-pattern-and-data-profiling-scorecards.md): warehouse, Data Profiling and catalog scores compared.
- [05 Cleaning a large dataset](05-cleaning-a-large-dataset-with-mappings.md): match mapping into a stage table, proven against a SQL twin.
- [lessons.md](lessons.md): every DQ lesson with evidence; grep it before any call.
