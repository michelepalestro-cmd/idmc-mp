# DQ Scorecards: the warehouse pattern and Data Profiling scorecards

**Answers:** Where can a DQ score live (warehouse tables, Data Profiling scorecard, catalog DQ score), and which one
should I build on? How do I bind, run and read each one headless? How do I keep the numbers honest?

**Read when:** an app, dashboard, steward queue or CLAIRE answer needs DQ numbers; building a Data Profiling scorecard;
running catalog Data Quality scoring; a DQ score looks too good or too bad.

**Key rules:**
- Anything an app or dashboard must read lives in warehouse scorecard tables written by a CDI task (L-DQ-054,
  L-DQ-055). Data Profiling pass rates do have a read since 2026-11-02: each rule binding's output column in the metric
  store, `Profiles('<id>')/Columns('<columnId>')/ValueFrequencies` (VALID / INVALID counts; L-DQ-123). Use it for trend
  jobs and parity checks; L-DQ-031 was about the profiling-service routes.
- A Data Profiling scorecard needs rule specs with a dimension, passing outputs Valid/True/1/Yes/Ok, at most 200
  occurrences, and a re-run after binding (L-DQ-049, L-DQ-032).
- Catalog DQ scores work end to end: create the rule occurrences over REST or accept named-column recommendations, give
  the source's Scope groups a runtime environment, run the Data Quality capability, then read each occurrence's score
  (L-CDGC-161, L-DQ-097, L-CDGC-143, L-MCP-086, L-CDGC-166).
- Bind each catalog rule occurrence to a column of the rule's input type: a decimal-input rule on a text column passes
  publish and sync and is never scored (L-CDGC-170).
- A format rule must test the stored string literally (E.164 is `^\+[1-9]\d{7,14}$`); count failing patterns before
  trusting a score (L-DQ-105).
- Right denominators, each business rule counted once, test identities excluded, and a detector proven falsifiable
  (L-DQ-058, L-DQ-060).
- Report value as fixes applied, not rules passed (L-DQ-095).

**Related:** [Profiling - What Is Headless](02-profiling-what-is-headless.md) ·
[DQ Assets](01-dq-assets-rule-specs-cleanse-dictionaries-verifiers.md) ·
[Catalog Sources - Create, Scan, Update, Purge](../07-catalog-governance-cdgc/02-catalog-sources-create-scan-update-purge.md) ·
[CLAIRE GPT - Prompting Rules & Patterns](../09-claire-mcp/03-claire-gpt-prompting-rules-patterns.md) ·
[Lessons: Data Quality & Profiling](../../lessons/by-domain/06-data-quality-profiling.md)

**Last verified:** 2026-11-03

> **Summary.** A DQ score can live in three places. (A) **Warehouse scorecard tables** written by CDI mapping tasks:
> one row per rule with `checked`, `failed` and `dimension`, rolled up to `pass_rate` per dimension; fully headless and
> readable by apps. (B) **Data Profiling scorecards**: rule occurrences on a profile, a run, then **View Scorecard** in
> the CDGC dashboard; binding and running are headless, reading the pass rates is console-only. (C) **CDGC catalog DQ
> scores**: rule instances on catalog assets, scored by the catalog source's Data Quality capability and readable by
> CLAIRE. Build on (A) for anything an application must read, (B) for console stewardship, (C) for catalog-wide
> governance and CLAIRE answers. Never loosen a gate to accept a partial score.

---

## 1. The three scorecards compared

| | **A. Warehouse scorecard (CDI)** | **B. Data Profiling scorecard** | **C. CDGC catalog DQ score** |
|---|---|---|---|
| Object | tables you own (`dq_results`, `dq_scorecard`,...) | rule occurrences on a **profile** (`<pod>-dqprofile`) | rule occurrences on **catalog assets** (BusinessDataset / RuleOccurrence / DATA_QUALITY_SCORE) |
| Rule logic | SQL in customQuery, or a Rule Specification transformation in the mapping | CDQ rule specifications | CDQ rule specifications |
| Engine | a CDI mapping task on the Secure Agent (or warehouse pushdown) | the Data Profiling job | CDGC / DQ engine during a catalog scan |
| Author headless? | yes (mapping task over a template, [CDI](../03-cdi-data-integration/)) | yes: `PUT /profile/<id>` with MAPPLETFIELD entries | yes: a `ccgf-contentv2` publish of the RuleInstance plus its column relationship, then a sync (§4, L-CDGC-161); or CLAIRE GPT recommend-and-accept (browser-automatable) |
| Run headless? | yes (`POST /api/v2/job`, schedules, taskflows) | yes: `POST /profile/<id>/execute` | yes: the source's `Data Quality` capability run (needs a runtime environment in the Scope groups) |
| Read the numbers headless? | **yes** (SQL) | **no REST read found** (console only) | **yes**: each RuleInstance's `selfAttributes` (`value`, `totalCount`, `exception`, `scannedTime`; L-CDGC-166), the `dataQuality` segment and CLAIRE answers; the MCP `cdgcdataqualityscore` server lists `get_asset_score` (untested) |
| Who can see it | anyone with warehouse or BI access | Results → Rules view: Data Profiling users; View Scorecard: needs the **Governance User** role, and DQ + CDGC on the pod | CDGC users |
| Visible to CLAIRE GPT | yes, if the view is cataloged and "queried" | via CDGC once published | yes, once published |
| Best for | apps, dashboards, alerts, trends | console demos, stewardship in IDMC | catalog-wide governance |

---

## 2. Pattern A: the warehouse scorecard written by CDI

### 2.1 Why this pattern exists

- CDQ has no production engine of its own: DQ needs CDI to execute (L-DQ-001).
- A CDI mapping task that evaluates the rules and writes a scorecard table is a genuine IDMC-native path to scores. It
  runs on the DIS engine and shows SUCCESS in the v2 activity log, independent of catalog rule-occurrence limits
  (L-DQ-054).
- The profiling-service routes do not return pass rates (L-DQ-031), but the metric store does: read the rule output
  column's ValueFrequencies (L-DQ-123). App-facing numbers still belong in your own tables, so they have a schema you own.

### 2.2 Table design (L-DQ-055)

A pattern that ran hourly in production (15 dimensions, 23 rules, ~560k checks per run):

**`dq_results`**: one row per rule (the `rule` value is unique):

```sql
select '<rule_id>' as rule, count(*) as checked,
       countif(<fail condition>) as failed,
       '<dimension>' as dimension, current_timestamp as run_at
from <staging model>
union all
select...                              -- one SELECT per rule
```

**`dq_scorecard`**: rolled up by dimension, plus one `overall` totals row:

```sql
with r as (select * from <dq_results>),
by_dimension as (select dimension, count(*) as rules, sum(checked) as checked, sum(failed) as failed
                 from r group by dimension),
overall as (select 'overall' as dimension, count(*) as rules, sum(checked) as checked, sum(failed) as failed from r),
scored as (select *, round(1 - failed / greatest(checked, 1), 4) as pass_rate
           from (select * from by_dimension union all select * from overall))
select dimension, rules, checked, failed, pass_rate,
       case when pass_rate >= 0.99 then 'green' when pass_rate >= 0.90 then 'amber' else 'red' end as status,
       current_timestamp as run_at
from scored
```

Companion marts that proved useful:

| Mart | Grain | Purpose |
|---|---|---|
| `dq_daily` | rule x day (x capture channel) | history and trends. Write APPEND with a `NOT EXISTS` guard, so it writes once per UTC day. Keep its rule logic identical to `dq_results`. |
| completeness worklist | one row per entity | `completeness_score`, per-rule flags, `failing_rules`, `on_worklist` (score < 1 or key validity failed): the steward / human-in-the-loop queue |
| reconciliation | bucket | cross-system matches vs orphans (for example "has a CRM id" vs "never synced") |
| match pairs | candidate pair | the duplicate pairs a dedup rule found, for review |
| clean-only gate | view | only records that pass the blocking rules. Downstream activation (reverse-ETL, CRM loads) reads this, never the raw layer. |

Mechanics:

- Each mart is a mapping task over the Copy Data template with the SQL in `customQuery`, placed in an hourly
  taskflow ([Data Integration (CDI)](../03-cdi-data-integration/)).
- Remember the evidence layer: this is IDMC running **SQL**. If you must claim "IDMC DQ", put a Rule Specification
  transformation or Data Profiling rule occurrences in the chain too (L-DQ-004).

### 2.3 Rule catalog as data, two engines, parity (L-DQ-056)

- Keep one rule catalog as data. Each rule carries its violation query for every engine that scores it (for example the
  operational database and the warehouse).
- Score with both engines and reconcile with a parity harness. A difference is either real drift or a rule bug; in one
  proof, 17 of 19 rules matched and the 2 misses were real drifts.
- Publish the scorecard to dashboards, alert on it, and validate it against the golden-record layer.
- **Scheduled scoring exits 0 even when the verdict is red.** Red is a data verdict, not a job failure.
- **Run the org's rule specifications in a CDI mapping and prove them against SQL** (L-DQ-117, 2026-10-29): a
  custom-query source on a JDBC V2 ClickHouse connection, rule specification transformations chained with an Expression
  that renames each `Output`, an Aggregator per group and a JDBC V2 target on a second connection whose URL names the
  results database (L-CDI-040). An independent SQL computation of the same checks on the same 1M-row sample matched
  866 of 867 group x check cells; use a deterministic hash filter so both sides read the same rows. The one miss was a
  CLAIRE-generated state-code rule that rejected DC (L-DQ-118): read generated allowed lists before national runs.

### 2.4 Make the numbers honest (L-DQ-058)

- **Right denominators.** Rule checks over raw sign-up rows (with test accounts and duplicates) inflate duplicate counts
  and distort completeness, and a headline weighted by raw rows will not match per-customer numbers elsewhere. Define:
  - customer checks over **unique customers**;
  - the duplicate check over the records **actually merged**;
  - test identities **excluded**.
- **Count each business rule once.** If street, city, state and ZIP completeness are four rules over the same rows,
  make them one "address complete" rule. Do not test the same property twice (phone valid vs phone E.164 valid).
- **Publish one view** that BI and CLAIRE both read, so every surface shows the same number.
- **Report value as fixes applied (L-DQ-095).** For a business audience the number that explains DQ is how many problems
  were fixed automatically (names, phones and e-mails standardized, duplicates merged, addresses corrected), with a
  stated minutes-per-fix assumption, derived from the same before/after audit the cleansing view shows.

### 2.5 Rules that do not lie

| Practice | Why | Lesson |
|---|---|---|
| **Gate on activity:** below an activity threshold (for example "reviews" only when completed orders > 20), report `NO_ACTIVITY`, not `BROKEN` | small-n tables false-alarm when nothing happened yet | L-DQ-059 |
| **Prove the detector is falsifiable:** seed a known violation, watch the rule go RED (exit non-zero), remove it, watch GREEN | a GREEN verdict means little until the detector has been seen to fail | L-DQ-060 |
| **Keep synthetic rows out of gold:** filter test identities at staging and assert a zero count of synthetic markers in every gold/golden table (fail loud) | leakage makes every downstream score wrong | L-DQ-061 |
| **Shadow tables with views that exclude synthetic rows** and run unchanged rules with `SET search_path = <dq_schema>, public` | test suites keep refilling the live DB with invalid fixtures, so repair never converges | L-DQ-062 |
| **Expect reseeding to move failures:** a new synthetic e-mail domain trips a different identity rule; verify it has no real users, then exclude it symmetrically in every compared system | the same pattern recurs after each reseed | L-DQ-063 |
| **Validate allow-lists against `SELECT DISTINCT`** on the live column | vendor vocabularies (payment statuses) differ from the app's own enum | L-DQ-064 |
| **Flag dormant tables from live row counts** (e.g. warehouse `__TABLES__`), not a hard-coded list | zero-row tables reveal unused or broken features | L-DQ-065 |
| **If the rule SQL is replicated into a mapping customQuery**, keep the two bodies byte-identical | the replica silently drifts otherwise | L-DQ-059 |
| **Test the stored representation literally:** a phone "E.164" rule matches `^\+[1-9]\d{7,14}$` (or `^\+1\d{10}$` for one country) on the stored column, and you count non-matching rows by pattern before trusting the score | a golden phone column held 10- and 11-digit strings with no `+` while its "phone E.164" dimension read 99%; the app and CRM looked right only because a later write-back normalised them | L-DQ-105 |
| **Emit the canonical form on the first run** of the golden mapping (one phone formula in every writer) | first-cycle records otherwise differ from later ones | L-DQ-105 |

### 2.6 Rejects and circuit breakers (third-party reference design, not live-probed) (L-DQ-066, L-DQ-067)

- **Never drop a row silently.** Send every failed row to an error table with:
  - run id, source entity and business key;
  - a reason `<rule id> | <code> | <offending value>` (for example `CQ-002 | INVALID_EMAIL_FORMAT | EMAIL='x@example.com'`);
  - the raw record as JSON.

  Choose per rule between reject and flag/warn. Keep domain value lists in a reference table, not a hard-coded IN-list.
- **Reject-rate circuit breaker.** Above a threshold (for example 10% rejects), fail the quality task and abort the
  taskflow: a mass reject means the source contract changed.
- **Safe re-runs.** A lookup against the fact on the natural key, followed by a filter `ISNULL(LKP_SK)`, so that
  re-processing a file does not double the facts.

### 2.7 Turn red scores into work (L-DQ-057)

A red-score loop:

1. Read the scorecard and flag any rule with `failed > 0`.
2. Route it to a data steward by domain, through a steward-queue view.
3. File a ticket.

Native CLAIRE auto-rule generation comes out of a CDGC profiling scan and is reviewed in the UI. The warehouse loop is
the headless equivalent.

---

## 3. Pattern B: the Data Profiling scorecard

### 3.1 Prerequisites (vendor, Cloud Data Profiling October 2025 pp.86-90)

- **The rule spec must have a dimension.** Use a built-in one, or a custom value from the Dimension attribute in
  Metadata Command Center (Asset Customization; max 12 values). The dimension is what rolls a rule up into the scorecard.
- **Passing rows must output** `Valid`, `True`, `1`, `Yes` or `Ok`. Failing rows may output anything.
- **Only rule specifications** can back a rule occurrence: no other DQ assets, no mapplets. With several output fields,
  the scorecard uses the first available of `isValid`, `isTrue`, `out_valid`, `out_status`, `PrimaryRuleSet`. With
  several *input* fields, the dashboard scores only one of them, chosen at random.
- **Re-run after changes.** Scorecard results appear only for runs after occurrences are created or updated. Deleting a
  rule deletes its occurrences.
- **Viewing the dashboard** needs the **Governance User** role, and Data Quality plus Data Governance and Catalog
  available on the org's pod.
- **Roles for occurrences.** Creating occurrences needs asset permissions on the Data Profiling Task and the Data Quality
  Rule Occurrence asset types. Stakeholder assignment needs the Data Governance Administrator privilege.
- **Limit: ≤200 rule occurrences per profile.** Above that, the scorecard job times out on an internal publishResults
  call even though the results page renders (L-DQ-032).

### 3.2 UI recipe (L-DQ-049)

1. Create a profile on the source connection ([02](02-profiling-what-is-headless.md)) and run it once.
2. Optional: open the profile's **Insights** tab, where CLAIRE lists recommended rule specifications scored High, Medium
   or Low, and take them as the starting rule list (L-DQ-049).
3. **Rules** tab: add rule specifications, each with its input column.
4. **Metrics** tab (Menu → Scorecard Metrics): promote them to **rule occurrences**. Each carries:
   - a type/dimension (Accuracy, Validity, Completeness, Consistency, Uniqueness, Timeliness);
   - thresholds (Good / Acceptable / Not Acceptable), a target, `measuringMethod` "InformaticaCloudDataQuality" and
     a criticality;
   - `ruleFRSId` (the rule spec) and `mappletColumnId` (the column).
5. **Run**, or set a schedule (runtime environment plus e-mail).
6. **View Scorecard** opens the scorecard dashboard in Data Governance and Catalog.

For REST reads of the same profile (insights, run detail, rule bindings) use the profile's internal uuid from
`GET /profile?limit=200` (match on name); the handle in the browser URL is a different id (L-DQ-049).

### 3.3 Headless recipe (L-DQ-019, L-DQ-023)

1. Make sure the rule specs exist in the org, with dimensions ([01](01-dq-assets-rule-specs-cleanse-dictionaries-verifiers.md) §3).
2. `GET /profile/<id>`. Add one `source.rules[]` block per rule spec and one `MAPPLETFIELD` entry per bound column, with
   no client-side ids. `PUT /profile/<id>` (or `POST /profile` for a new one). The exact body is in
   [02](02-profiling-what-is-headless.md) §2.5.
3. `POST /profile/<id>/execute` and poll `GET /job/<jobId>` to COMPLETED.
4. Read the scores in the console. **No REST read of per-rule pass rates exists** (L-DQ-031). Mirror anything an app
   needs into Pattern A tables.

Eight profiles built this way ran daily, all COMPLETED with "No errors encountered", in two orgs. Profiles imported
from another org arrive with **no** rule occurrences: re-bind them (L-DQ-026).

### 3.4 Where the numbers show

| Surface | What you see | Needs |
|---|---|---|
| Data Profiling → profile → **Results** tab | column statistics, patterns, value frequencies; the **Rules** view with per-rule pass/fail | Data Profiling results view privilege; no CDGC |
| **View Scorecard** → CDGC scorecard dashboard | per-dimension and per-occurrence scores, trends (widgets such as Average Latest Scores), thresholds; notifications on status changes (good → not acceptable,...) to stakeholders; download of up to 100 rows (valid/invalid preview) | Governance User role; DQ + CDGC on the pod; drill-down needs the Data Profiling Query Create/Submit, Results View and Sensitive Data view privileges |
| **Export Profile Results** | an Excel file of the results | results export privilege |
| REST | the profile definition, run history, rule bindings, column metrics (metric-store OData) | no pass-rate read found |

When the scorecard dashboard is not available (no CDGC entitlement or no Governance User role), use the **Results →
Rules view** and export to Excel. Land your own rule results in a table for dashboards (L-DQ-050).

---

## 4. Pattern C: the CDGC catalog DQ score

**Two scorecard features exist (L-DQ-048).** The CDGC Data Quality score (rule instances on catalog assets) scores
catalog assets; the Data Profiling scorecard (Pattern B) scores a profile's source, is simpler, and its design objects
are exportable. Pattern C is the one CLAIRE GPT reads.

**The loop that works (L-DQ-097):**

1. **Configure the catalog source.** Give it the Data Quality capability, and put the runtime environment into both
   Scope groups of `typeCapabilities` (`Data Profiling Scope`, `Data Quality Scope`). Without it, a Data Quality run
   shows Rule Generation COMPLETED and Rule Profiling FAILED within a second, with no error text in the job API
   (L-CDGC-143). The body shapes are in
   [Catalog Sources - Create, Scan, Update, Purge](../07-catalog-governance-cdgc/02-catalog-sources-create-scan-update-purge.md).
2. **Create the rule instances**, headless (L-CDGC-161) or through CLAIRE GPT. Either way they carry no score yet.
   - **Headless.** First read the rule specification's ports and description (L-DQ-109):

     ```
     POST https://<pod>.<domain>.informaticacloud.com/saas/api/v2/extensionPoint        (header icSessionId)
     {"alias": "RuleSpecificationTx", "method": "getDescription", "payload": "{\"ruleId\": \"<frsId>\"}"}

     -> a JSON string whose ruleModel (itself a JSON string) holds name, description, fields (the inputs, with name
        and type), outputFields (usually one, Output) and testData
     ```

     Then publish the occurrence and its column binding in one call, with the identity headers plus
     `X-INFA-PRODUCT-ID: CDGC` (without it: 500 'Required request header X-INFA-PRODUCT-ID'), and sync it:

     ```
     POST https://cdgc-api.<domain>.informaticacloud.com/ccgf-contentv2/api/v1/publish
       item 1  OBJECT INSERT of type com.infa.ccgf.models.governance.RuleInstance with a provisional identity
               (identityType PROVISIONAL); attributes, each prefixed com.infa.ccgf.models.governance.:
               RuleType (the dimension, e.g. Validity), TechnicalDescription, MeasuringMethod
               InformaticaCloudDataQuality, Criticality, Target, Threshold, Frequency null, ruleInputPortName,
               ruleOutputPortName, TechnicalRuleReference (the rule specification's frsId); plus core.name,
               core.description and core.origin (the catalog source id)
       item 2  RELATIONSHIP INSERT of type com.infa.ccgf.models.governance.asscParentDataElementRuleInstance from the
               column's external id (sourceIdentityType EXTERNAL) to the provisional id (targetIdentityType PROVISIONAL)

     -> 207 with a 201 per item, the new DQO-<n> id and its internal id

     POST .../ccgf-ruleautomation/api/v1/dataQuality/sync        ["<internal id>"]        -> PASSED
     ```

     This is the request the asset form (New > Business Rules > Data Quality Rule Occurrence > Create) sends. Capture
     it from the form once, then replay it per column (L-UI-032); take the port names and the description from the
     `getDescription` answer.
   - **Through CLAIRE GPT.** Ask for recommendations and **name the columns**, or repository rules land on the wrong
     columns (L-MCP-086); accepting them creates the instances at once. Recommendation only matches rules already in
     the repository: for a new control use rule generation, then bind it (L-MCP-098).
   - **Bind a column of the rule's input type** (L-CDGC-170). An occurrence whose rule specification takes a decimal
     input, bound to a text (VARCHAR) column of a raw landing table, was accepted by publish and sync but never
     scored: the Data Quality run ended PARTIAL_COMPLETED with no message in the job tree, no profiling job for that
     table on the agent and no value on the RuleInstance. A view over the same table with `TRY_TO_NUMBER(<col>, 18, 4)`
     as a numeric column (non-numbers become NULL and fail a 'filled in' rule), cataloged by a Metadata Extraction and
     bound instead (view columns are `...~com.infa.odin.models.relational.ViewColumn`), scored on the next run
     (98.63 %, 73 rows, 1 failed) although the view was never profiled.
3. **Run the capability:**

   ```
   POST https://idmc-api.<domain>.informaticacloud.com/data360/executable/v1/catalogsource/<catalogSourceId>
   {"capabilityNames": ["Data Quality"]}
   ```

   Rule Profiling, Batch Profiling and Score Propagation give per-instance, per-dimension and overall scores. On the
   Secure Agent this runs a Rule Profiling Task and a Batch Profiling Task: about 15 min for ten occurrences on five
   small tables (L-CDGC-166).
4. **Read and ask.** Each RuleInstance then carries its own score in `selfAttributes`:
   `com.infa.ccgf.models.governance.value` (the score in percent), `totalCount` (rows checked), `exception` (rows that
   failed) and `scannedTime` (epoch ms), read with
   `GET https://idmc-api.<domain>.informaticacloud.com/data360/search/v1/assets/<internal id>?scheme=internal&segments=selfAttributes`.
   Occurrences created over REST score like ones made in the UI (L-CDGC-166). CLAIRE GPT then answers score, trust and
   low-score questions from them.
5. **Recompute each rule in the warehouse before a demo.** A format rule at 0% can be a real finding (curated phone
   numbers stored as digits without the leading `+` fail an E.164 check on every row, §2.5). The reverse also misleads:
   scoring curated tables whose loads already reject bad rows gives 100 everywhere, so score the raw layer too to show
   what the rules caught (L-CDGC-166).
6. **Change or remove instances.** An instance copies its read-only technical description from the rule spec when it
   is created: fix the rule spec's description (FRS PATCH, L-DQ-094) and recreate the instance (L-CDGC-145). Instances
   are RuleInstance assets: find them by class and delete them with the content API (L-CDGC-144).
7. **Check for auto-generated schedules.** With `Run Rule Occurrence Frequency` and `Data Quality Automation` on, the
   org gains `DQ_Capability_Schedule_Daily_<epochMs>`, `..._Weekly_..` and `..._Monthly_..` schedules that run accepted
   occurrences on IDMC-side schedules. Those runs are not in the v2 activity log (count them through the catalog jobs
   API, L-IPU-055). When you clone a DQ-enabled source, set both switches to `false` unless you want IDMC-side
   scheduling, and re-read `GET /api/v2/schedule` after each accept (L-CDGC-152).

| If you see | Cause | Fix |
|---|---|---|
| CLAIRE: "No Data Quality information is currently available" | no rule instances, or the Data Quality capability has not run | steps 2-3 |
| Rule Profiling FAILED in 0-1 s, no error text | no runtime environment in the Scope groups | step 1 |
| recommended rules on the wrong columns | columns not named in the prompt | name the columns (L-MCP-086) |
| "No matching data quality rules were found" for a column | no repository rule fits it | rule generation, then bind (L-MCP-098) |
| new `DQ_Capability_Schedule_*` schedules after an accept | DQ automation switches on the source | set them to false, or budget the runs |
| 500 'Required request header X-INFA-PRODUCT-ID' on the occurrence publish | the header is missing | `X-INFA-PRODUCT-ID: CDGC` (L-CDGC-161) |
| every occurrence scores 100 | the scored tables are curated: their loads already rejected the bad rows | score the raw layer too (L-CDGC-166) |
| the Data Quality run ends PARTIAL_COMPLETED with no message, and one occurrence never gets a value | a decimal-input rule bound to a text (VARCHAR) column | bind a numeric column of a typed view (step 2; L-CDGC-170) |

- **Reading catalog scores over MCP.** The managed registry lists a `cdgcdataqualityscore` server with a
  `get_asset_score` tool. It is untested here ([Managed MCP Servers](../09-claire-mcp/01-managed-mcp-servers-catalog-access.md)).
- **CLAIRE GPT and DQ without catalog scores.** To tell a DQ story before Pattern C has run, point CLAIRE at a cataloged
  Pattern A **view** and ask it to *query the data*
  ([CLAIRE GPT - Prompting Rules & Patterns](../09-claire-mcp/03-claire-gpt-prompting-rules-patterns.md)).

---

## 5. Choosing

1. **An app, a BI dashboard or an alert needs the number:** Pattern A. Mirror Pattern B results into it if you also
   have profiles.
2. **An IDMC console demo, or stewardship inside IDMC:** Pattern B, with rule specs that carry dimensions, ≤200
   occurrences, a re-run after binding, and the Governance User role for View Scorecard.
3. **Catalog-wide governance and CLAIRE answers:** Pattern C. Put the runtime environment in the Scope groups, create
   the occurrences over REST or accept named-column recommendations, run the Data Quality capability, recompute in the
   warehouse before a demo, and watch for auto-generated schedules.
4. **Whatever you choose:** right denominators, one business rule counted once, test identities excluded, a detector
   proven falsifiable, and history kept in a daily snapshot.

---

## 6. Overturned beliefs (kept so nobody re-learns them)

| Belief | Held | Overturned by | Lesson |
|---|---|---|---|
| "A DQ scorecard is UI-only: author the profile, bind the rules, assign dimensions and run, all in the UI; no run or author REST verb" | 2026-09-12 to 2026-09-22 | Rule occurrences bound by `PUT /profile/<id>` and runs by `POST /profile/<id>/execute` (2026-09-24). Dimensions still come from the rule spec. | L-DQ-087, L-DQ-088 → L-DQ-019, L-DQ-023 |
| "Native CDQ rule authoring is UI-only" | 2026-07-04 to 2026-07-07 | Clone a template rule spec through v3 export/import (2026-07-09) | L-DQ-083 → L-DQ-010 |
| "Running only the Data Quality capability returns 406" | 2026-07-09 | The run completes once typeCapabilities carry a runtime environment (2026-09-30) | L-DQ-044 → L-CDGC-143 |
| "Catalog rule occurrences score 1 of 6, reading scores is UI-only, and they have no create path" | 2026-07-09 | 9 of 9 accepted instances scored; scores read through the content API and CLAIRE; instances created by CLAIRE's recommend-and-accept (2026-09-30), then over REST with per-occurrence scores (2026-10-06) | L-DQ-051, L-DQ-052 → L-DQ-097, L-CDGC-144, L-MCP-086, L-CDGC-161, L-CDGC-166 |

---

## 7. Open questions

- A REST (or MCP `get_asset_score`) read of Data Profiling scorecard values per rule occurrence.
- Whether the auto-generated `DQ_Capability_Schedule_*` runs count against the monthly job cap, and how many jobs they add.
- Whether rule-occurrence thresholds and criticality can be set in the `PUT /profile` body. The builders relied on
  defaults.
