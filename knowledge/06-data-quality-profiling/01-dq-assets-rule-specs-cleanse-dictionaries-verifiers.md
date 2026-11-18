# DQ Assets: rule specifications, cleanse, dictionaries, verifiers

**Answers:** Which Cloud Data Quality (CDQ) assets exist and where does each one execute? Which can Claude author
headless, and with which calls? How do I read a rule specification's logic out of an export package? How do I run
address verification from a pipeline without wasting calls or breaking its metrics?

**Read when:** authoring, cloning or moving rule specifications, cleanse/parse/deduplicate assets or dictionaries;
translating IDMC rules into another engine; building or debugging an address-verification job.

**Key rules:**
- DQ assets are definitions only: a CDI mapping on a Secure Agent executes them, and a Data Profiling profile scores
  them (L-DQ-001, L-DQ-002).
- There is no direct create for a rule specification (405): clone a same-type template through v3 export/import; new
  logic still needs the rulebuilder canvas, while the description can be patched over FRS (L-DQ-010, L-DQ-094).
- The only public CDQ write API is the Dictionary API on `<pod>-dqcloud-api`: no GET exists, and `finishUpload` is
  mandatory (L-DQ-006, L-DQ-007).
- A rule spec's logic sits in `nativeData.documentBlob` → `ruleModel`, and both are JSON strings: parse twice
  (L-DQ-104).
- Address verification: read the pre-merge layer, seed tests with real public addresses, cache and queue on an
  address hash, and keep a first-verified timestamp that is never overwritten (L-DQ-016, L-DQ-018).
- A cleanse rule must not damage correctly typed values, and every writer of the field must apply the same rule
  (L-CAI-086).
- A verifier returns only the enrichments its own process settings request: added output ports gave no geocodes, so
  prove one known address returns coordinates before a bulk run (L-DQ-130).

**Related:** [Profiling - What Is Headless](02-profiling-what-is-headless.md) ·
[DQ Scorecards](04-dq-scorecards-warehouse-pattern-and-data-profiling-scorecards.md) ·
[Export & Import (v3 Migration API)](../10-migration-org-management/01-export-import-v3-migration-api.md) ·
[Managed MCP Servers](../09-claire-mcp/01-managed-mcp-servers-catalog-access.md) ·
[Lessons: Data Quality & Profiling](../../lessons/by-domain/06-data-quality-profiling.md)

**Last verified:** 2026-11-03

> **Summary.** CDQ assets are reusable *definitions*: cleanse, deduplicate, labeler, parse, rule specification and
> verifier, plus dictionaries of reference data. None of them reads or writes data by itself. Rule specifications are
> readable over v3 and authored headless by cloning; dictionaries have their own write API; address verification exists
> as a batch REST API (1,000 addresses per call, documented) and as the managed MCP action `verify_address` (one per
> call, proven). Endpoints: [CDQ endpoint table](../12-reference-library/idmc-api-mcp-reference/content/16-cdq.json).

Evidence labels used below: **proven** (with a date) = a live call with a read-back; **documented** = a vendor guide says
so and it was not exercised; **rejected** (with the code) = the platform refused it; **untested** = unknown, not
"unsupported".

---

## 1. The assets at a glance

| Asset | What it is (vendor definition, CDQ April 2026) | Where it executes | Headless authoring | Evidence |
|---|---|---|---|---|
| **Rule specification** | A business rule in logical form. Rule sets hold rule statements; each statement reads an input column and tests a condition. Basic mode uses graphical shapes; advanced mode uses expressions with IF-THEN-ELSE. The primary rule set's output says whether a row meets the rule. | Rule Specification transformation in a CDI mapping; also bound to columns as a *rule occurrence* in a Data Profiling profile | Clone a same-type template through v3 export/import (L-DQ-010). Logic authoring stays in the rulebuilder canvas. | proven 2026-07-09 (clone); canvas = UI |
| **Cleanse** | One or more transformation steps that standardize the form and content of data | Cleanse transformation | UI; or copy an existing asset in from another org by v3 export/import (it then ran inside a generated mapping) | proven 2026-09-30 (L-CDI-204) |
| **Deduplicate** | Measures similarity between records and can consolidate similar records into one preferred record | Deduplicate transformation | UI; or copy an existing asset in by v3 export/import, and leave its `Id` match field out of the mapping (L-DQ-101) | proven 2026-09-30 (L-CDI-204, L-DQ-101) |
| **Labeler** | Derives information about content and structure by analysing tokens (delimited values) or characters | Labeler transformation | UI only | documented |
| **Parse** | Identifies discrete values in an input field and writes them to the right output fields | Parse transformation | UI only | documented |
| **Verifier** | Evaluates the accuracy and deliverability of postal addresses against address reference data. It can verify, format, suggest, measure and enrich. | Verifier transformation (the agent downloads reference data at run time) | UI only | documented |
| **Dictionary** | A reference-data table with one *valid* column (the preferred value) and alternative-value columns | Read by other assets when they are tested and when a mapping or profile runs | **REST Dictionary API** (§4) | proven 2026-07-25 (create 201) |

Facts that apply to every asset type (vendor, CDQ April 2026):

- Every asset belongs to at least one project. An asset created without a project lands in the Default project.
- You create assets in Data Quality (**New**), or in Data Integration (the **New Asset** dialog, or from inside a mapping).
  The configuration options are the same in all three places.
- A DQ asset "doesn't identify or connect directly to source data". It becomes active only inside the matching
  transformation of a mapping.
- Each asset editor has a **Test** facility on sample rows. The Secure Agent runs the test at design time. That is
  author-time validation, not production execution (L-DQ-002).
- Census before you assume an org is empty. A mature training org held 36 profiles, 507 rule specifications, 132 cleanse
  assets and 367 dictionaries, much of it Informatica library content. A new org also ships about 160 stock
  template assets.

---

## 2. Execution model: DQ authors and measures, CDI executes

**The law (L-DQ-001, page-cited vendor docs).** Data Quality is licensed
and metered separately, but it has no production run engine and no mapping designer of its own. To cleanse, parse,
match/deduplicate or verify addresses on real data, add the DQ assets to transformations in a **Data Integration mapping**
that runs on a Secure Agent. CDQ Introduction (April 2026) pp.6-7 describes the life cycle as *Discover* (profile) →
*Design* (create assets in DI or DQ) → *Apply* ("Design and run the mappings in Data Integration").

| You need to… | DQ alone | Needs a CDI mapping or mapping task |
|---|---|---|
| Author rule specs, cleanse, parse, labeler, deduplicate and verifier assets | Yes (UI; rule specs, cleanse and deduplicate assets also by clone) | No |
| Test an asset on sample rows | Yes (design time) | No |
| Profile a source and score rules on it | Yes: Data Profiling ([02](02-profiling-what-is-headless.md), [04](04-dq-scorecards-warehouse-pattern-and-data-profiling-scorecards.md)) | No |
| Schedule a single profiling or DQ task | Yes | No |
| Orchestrate several steps (taskflow) | No | Yes (CDI taskflow) |
| Cleanse, match, parse or verify **production** data | No | Yes: the transformation runs on the agent |
| Write cleansed data to a target | No; DQ alone only extracts exception/reject rows (Exception Management) | Yes |
| Push advanced DQ (match, address, parse) down into a warehouse | No | No: not pushdown-eligible; it runs on the agent |

Say it precisely (L-DQ-002; a 15-claim fact-check):

- "DQ alone cannot run on production data", not "DQ has no engine". The asset editors test on sample rows.
- DQ alone can schedule one profiling or DQ task. It lacks taskflow orchestration.
- Profiling is standalone. Viewing the **scorecard dashboard** needs CDGC and a governance role
  ([04](04-dq-scorecards-warehouse-pattern-and-data-profiling-scorecards.md)).
- DQ alone extracts exception/reject rows but writes no cleansed data to a target.
- MDM SaaS has its own built-in cleanse, match and merge. Do not route MDM matching through CDQ.

**Where the engine lives (L-DQ-003).** Enabling Data Quality on a Secure Agent adds no separate DQ service
directory. The DQ runtime sits inside the Data Integration Server: the DIS version bumps when DQ is enabled, and the DQ
libraries are under `<DIS>/.../ICS/main/DQ`. Troubleshoot DQ transformation runs through the DIS logs.

**SQL that imitates DQ is not IDMC DQ (L-DQ-004).** A CDI task that only pushes down SQL written to mimic
cleansing or match/merge shows that IDMC ran a job, but the DQ logic is still SQL. Genuine IDMC DQ means the logic lives in
DQ assets and transformations (Cleanse, Standardizer, Parser, Match/Merge or Deduplicate, Rule Specification, Profiling)
executed by the engine. Read the mapping (or the customQuery) before you claim "DQ runs in IDMC", and label every status
by evidence layer: IDMC-native, or SQL equivalent.

**A complete DQ demonstration covers six capabilities (L-DQ-005):**
1. profiling (completeness, conformity, consistency, accuracy, duplication);
2. standardization and cleansing (address, phone, formats);
3. deduplication (identify and merge);
4. parsing and enrichment (parse free text; enrich, e.g. ZIP to geography from reference data);
5. rule-based DQ applied continuously in transit;
6. AI-pipeline readiness (remediate before vectorization, embed only valid records).

With only entitled features, use a reference-data lookup for geo enrichment instead of a licensed address verification
service.

---

## 3. Rule specifications

### 3.1 What matters in a rule spec

- **Modes.** Basic mode uses graphical rule sets and rule statements. Advanced mode uses a text rule editor: simple
  expressions or nested IF-THEN-ELSE/ELSEIF, which can reference other rule specs, dictionaries, mapplets and
  complex expressions. *Convert to Advanced* is one-way: you cannot go back to basic mode.
- **For scorecards** ([04](04-dq-scorecards-warehouse-pattern-and-data-profiling-scorecards.md)):
  - the rule spec must carry a **dimension**: a built-in one, or a custom value from the Dimension attribute in Metadata
    Command Center (max 12 values);
  - passing rows must output one of `Valid`, `True`, `1`, `Yes`, `Ok`;
  - with several output fields, the scorecard uses the first available of `isValid`, `isTrue`, `out_valid`, `out_status`,
    `PrimaryRuleSet`.
- **Arithmetic in the advanced script works.** A UPC-A check digit (REG_MATCH for 12 digits, then the GS1 mod-10 sum
  with `TO_INTEGER(SUBSTR(<input>, <n>, 1))` and `MOD(..., 10) = 0`) validated as a mapplet at DTM load and matched an SQL
  check row for row (L-DQ-111).
- **Read a generated rule's allowed list.** A rule CLAIRE generated for 'valid two-letter US state abbreviation' failed
  every District of Columbia row (2,121 rows), while a SQL check with the 50 states plus DC passed them; extend such
  lists (DC, territories) before using them on national data (L-DQ-118, 2026-10-29).
- **A changed rule spec leaves its mappings Invalid in the designer only.** A Rule Specification transformation stores
  a copy of the rule's definition: after the asset changed, the Mapping Designer showed the mapping Invalid ('The
  definition of the referenced asset [<rule spec>] has been changed. Synchronize the asset') while FRS, the v2 API and
  the runs called it valid. In the designer: select the transformation, answer Yes to the resynchronize prompt on its
  Rule Specification tab, check Field Mapping, save and reopen. Headless: regenerate the mapping from the current
  definitions (a fresh export) whenever a rule changes, then sweep the designer for Invalid badges, because no API
  reports this state ([UI Automation](../14-claude-working-methods/04-ui-automation-with-playwright.md);
  L-DQ-126, L-UI-036, 2026-10-26).
- **Catalog scoring wants string inputs on BigQuery.** Catalog Data Quality skipped every BigQuery table that carried a
  decimal-input rule occurrence; text-input twins of the decimal rules on STRING snapshot columns scored (L-CDGC-185).

  (Vendor, Cloud Data Profiling October 2025 pp.87-88.)
- **Six built-in DQ dimensions** are enumerable read-only at `GET /profiling-service/api/v1/ruleOccurrence/ruleType` on
  `<pod>-dqprofile` ([02](02-profiling-what-is-headless.md)). Recipes list them as Accuracy, Validity, Completeness,
  Consistency, Uniqueness and Timeliness. An older runbook listed Conformity instead of Timeliness, so read the route on
  your pod.

**Anatomy of the export JSON (L-DQ-104).** In a v3 export package each `<name>.RULE_SPECIFICATION.json` has
the shape `{id, name, description, documentType, customAttributes.stringAttrs[], nativeData.documentBlob}`:

| Part | Holds | Notes |
|---|---|---|
| `customAttributes.stringAttrs[]` | the DIMENSION (for example VALIDITY, COMPLETENESS, CONSISTENCY) and EXCEPTION | the dimension is what a scorecard rolls up by |
| `nativeData.documentBlob` | a JSON **string**: `{inputFields, outputFields, ruleModel}` | parse once |
| `ruleModel` | another JSON **string** (class `com.informatica.dq.rulebuilder.RuleDefinition`) | parse twice |
| advanced mode (the form CLAIRE writes) | `alternateDefinition.script`: `IF <cond> THEN Output='VALID' ELSE Output='INVALID' ENDIF` with ISNULL, LENGTH, IS_SPACES, REG_MATCH, IN(x,[...]) | translates deterministically |
| basic mode | a `topRuleFamily.statements` tree of operations (SetField, Equals, NotEquals, DefaultValue, WithinList, NotWithinList, GreaterThanOrEqualTo, LessThanOrEqualTo, Valid, Expression, standardize, convertCase) plus `testData` arrays | needs an operation mapper |

```python
import json
spec  = json.load(open("<name>.RULE_SPECIFICATION.json", encoding="utf-8"))
blob  = json.loads(spec["nativeData"]["documentBlob"])
model = json.loads(blob["ruleModel"])                               # RuleDefinition
script = (model.get("alternateDefinition") or {}).get("script")     # advanced mode
tree   = (model.get("topRuleFamily") or {}).get("statements")       # basic mode
dims   = spec["customAttributes"]["stringAttrs"]
```

**Running IDMC-authored rules in a warehouse engine.** An advanced script maps to a SQL predicate:
`upper(CASE WHEN <cond> THEN 'VALID' ELSE 'INVALID' END) IN ('VALID','TRUE','1','YES','OK')` (a row passes when the
output is Valid, True, 1, Yes or Ok). Before trusting a translation, check three semantics against each rule's
`testData`: whether REG_MATCH is a full-string match, what IS_SPACES('') returns, and whether IN is case-sensitive.
RE2-based engines also reject lookarounds and backreferences. Mark anything the translator cannot map as needs-review,
and prove parity with per-rule checked and failed counts from one CDI task over the same rows, because profile rule
results have no REST read (L-DQ-100).

### 3.2 Read (census): proven

```
GET https://<pod>.<domain>.informaticacloud.com/saas/public/core/v3/objects?q=type=='RULE_SPECIFICATION'&limit=200
INFA-SESSION-ID: <v3 sessionId>
```

- Success: 200 with `count` and `objects[]` (`id` = the frsGuid, `path`, `updateTime`,...).
- Caveat: the v3 `type==` filter is not validated. A misspelt or nonexistent type also returns
  `200 {"count":0,"objects":[]}`. A count of 0 never proves absence. Cross-check with an unfiltered `?limit=5`.
- In one org, 191 RULE_SPECIFICATION objects turned out to be generic Informatica library content (CLAIRE, DQ, DataMesh
  bundles). Filter by project before you treat a count as "our rules".

**Read one rule spec's ports and description (L-DQ-109, proven 2026-10-06).**

```
POST https://<pod>.<domain>.informaticacloud.com/saas/api/v2/extensionPoint
icSessionId: <v2 sessionId>

{"alias": "RuleSpecificationTx", "method": "getDescription", "payload": "{\"ruleId\": \"<frsId>\"}"}
```

- Success: 200 with a JSON string whose `ruleModel` (itself a JSON string) holds `name`, `description`,
  `fields` (the inputs, with name and type), `outputFields` (usually one, `Output`) and `testData`.
- The catalog's rule-occurrence form calls it to map the input port and to fill the read-only TechnicalDescription
  (L-CDGC-145). Use it to build a catalog rule occurrence headless (L-CDGC-161;
  [04](04-dq-scorecards-warehouse-pattern-and-data-profiling-scorecards.md) §4).

### 3.3 Author a rule spec headless: clone a template (L-DQ-010)

Direct create does not exist. `POST /public/core/v3/objects` returns **405** "Method not supported". Every
`/data360/dq/*` rule path returns **404**. A same-type template can be cloned instead:

1. Confirm a template exists (the census above). Confirm the user holds the migration (export/import) and object-admin
   roles. Without them: **403 `MigrationSvc_038`**; granting the role takes about a minute.
2. Export it: `POST /saas/public/core/v3/export` with body `{"objects":[{"id":"<frsGuid>"}]}` (no `type` key, or
   **400 `V3API_007`**), then download the zip with `GET /saas/public/core/v3/export/<jobId>/package`. Export-job
   handling is covered in [Migration & Org Management](../10-migration-org-management/).
3. Edit the package:
   - give the object a new GUID and name in the metadata and in the object file;
   - recompute the SHA-256 of every edited file and update the package checksum/metadata files.

   The package anatomy and the re-hash rules are in [Migration & Org Management](../10-migration-org-management/).
4. Upload: `POST /saas/public/core/v3/import/package` as **multipart/form-data**. Success is 200 with `checksumValid=true`.
   Wrong content types look like dead routes:
   - `application/json` → **404 `MigrationSvc_025`**;
   - `octet-stream` → **415**;
   - an invalid or hand-built package → **400 `MigrationSvc_030`**.
5. Start the import with `POST /saas/public/core/v3/import/<importId>`, then poll `GET.../import/<importId>` to
   **SUCCESSFUL**. `MigrationSvc_031` was transient when known-good packages also failed; retry later.
6. Read back: the census count rises by one. The imported object gets its **own id**: in a clone of another asset type the
   client-supplied GUID was discarded. Address it by the id the target reports.

**Caveat:** the clone inherits the template's expression logic. In the first proof the rule-spec count went from 4 to
11 to 12, but 7 of the clones still needed their expressions completed in the rulebuilder canvas. Pick a template whose
logic you actually want, or plan the canvas step.

**Change only the description (L-DQ-094).**

```
PATCH https://<pod>.<domain>.informaticacloud.com/frs/v1/Documents('<frsId>')
IDS-SESSION-ID: <v2 session>
Content-Type: application/json

{"description": "<text>"}
```

Expect **204**; a GET of the same Document reads the new text back. Catalog rule instances copy their read-only
technical description from the rule spec when they are created, so fix the text here and then re-run the catalog
source's Data Quality capability ([04](04-dq-scorecards-warehouse-pattern-and-data-profiling-scorecards.md) §4).

### 3.4 What does not exist (rejected, with codes)

| Tried | Result | Date |
|---|---|---|
| `POST /public/core/v3/objects` (create any design object) | 405 Method not supported | 2026-07-04 |
| `/data360/dq/v1/ruleSpecifications` (all verbs) | 404 | 2026-07-25 |
| `/public/dq/v1/rules`, `/api/v2/dqRule` | 404 | 2026-07-05 |
| `/quality/public/v2/scorecards` (GET, POST) | 404: the CDQ public API is dictionaries-only | 2026-07-25 |
| `/data360/businessDataset/v1` (create a CDGC rule occurrence, the catalog scoring object) | 404 | 2026-07-25 |

A catalog rule occurrence is created on another plane: a `ccgf-contentv2/api/v1/publish` of a RuleInstance plus its
column relationship, then a sync (L-CDGC-161, 2026-10-06; [04](04-dq-scorecards-warehouse-pattern-and-data-profiling-scorecards.md) §4).

The April 2026 CDQ API Reference covers **only** the Dictionary API. It has no `/rules`, `/rulespecs`, `/scorecards` or
`/profiles` resource (L-DQ-009). Profiles and profile rule occurrences have their own service on
`<pod>-dqprofile` ([02](02-profiling-what-is-headless.md)).

### 3.5 Expose a rule spec as a request/response API (documented, untested)

The vendor documents a request/response route for a rule spec (DQ Assets guide, chapter 21) (L-DQ-012):

1. In Explore, open **Actions → Enable for APIs** on the rule spec and name it (up to 100 characters).
2. Import the API-enabled rule into **API Center**, design an endpoint and publish it.
3. External apps then call the endpoint for real-time or incremental checks.

This gives per-request verdicts. It produces no scorecard and no results table. A mapplet that contains a Rule
Specification transformation can be API-enabled the same way (Components help in Data Integration).

### 3.6 Move rule specs between orgs (L-DQ-011)

Rule specs travel as `RULE_SPECIFICATION` objects in a v3 export/import package, and the import uses REUSE on name
conflicts. Check these before and after:

- cross-pod version mismatch;
- whether the functions the rule references are licensed in the target;
- that every dictionary the rule reads already exists in the target;
- that the import reports the rule count you expect.

Passwords are not exported. Rule specs from Informatica bundles must exist in the target, or be imported with REUSE,
before profiles that bind them can be re-bound.
Bundle *rule specs* exported fine in an org where exporting an Add-On Bundle *mapping template* had been refused with
403 `MigrationSvc_038` in another org. Test bundle-object export per org rather than assuming the wall.

---

## 4. Dictionaries: the one public CDQ write API

### 4.1 Model (vendor, CDQ Dictionaries April 2026)

- A dictionary is a reference-data table with two or more columns. One column is the **valid** (preferred) value;
  the others hold alternative or incorrect spellings. A transformation searches every column except the valid one,
  so add a copy of the valid column if you want it searched too.
- You can create one in the Data Quality, Data Integration or Reference 360 UI, or through the Dictionary API.
  A dictionary sourced from Reference 360 is visible in DQ/DI but editable only in Reference 360.
- The Secure Agent **downloads** every dictionary an asset specifies when a profile or mapping runs, and the dictionaries
  a test needs when you test an asset. Watch the agent's download directory for disk use.

### 4.2 Host, auth and routes

The host is derived from the DQ app URL: app `https://<pod>-dqcloud.<domain>.informaticacloud.com/...` → API base
`https://<pod>-dqcloud-api.<domain>.informaticacloud.com`. Headers: `Content-Type: application/json` and either
`Authorization: Bearer <jwt>` (identity-service JWT) or `IDS-SESSION-ID: <sessionId>`.

| Verb + path (under the base) | Body | Success | Errors / notes | Evidence |
|---|---|---|---|---|
| `POST /quality/public/v2/dictionaries/` | `{"name":"<name ≤125>","description":"<text>","columns":["<c1>","<c2>"],"path":"<project folder>"}` | **201**; returns `id`, `name`, `path`, `type:"DICTIONARY"`, `columns`, `customAttributes` | ≤42 columns; column names unique and ≤64 chars; no `path` → Default project | **proven** 2026-07-25 |
| `DELETE /quality/public/v2/dictionaries/<dictionaryId>` | none | 204 | | documented |
| `POST /quality/public/v2/dictionaries/<dictionaryId>/rows` | `{"cols":["<c1>","<c2>"],"rows":[["<v1>","<v2>"],...]}` | 201 | ≤10,000 rows per call → **413** above; row width must equal the column count | documented |
| `PUT /quality/public/v2/dictionaries/<dictionaryId>/rows` | same shape | 200 | replaces all rows; ≤10,000 per call | documented |
| `DELETE /quality/public/v2/dictionaries/<dictionaryId>/rows` | none | 204 | must be finalized | documented |
| `POST /quality/public/v2/dictionaries/<dictionaryId>/finishUpload` | none | 200 | **mandatory**; skipping it → **424** Failed Dependency; one call finalizes several pending POST/DELETE operations | documented |

Other documented codes: 400, 401, 403, 404, **409** Conflict (a state conflict), 500.

Gotchas:

- **No GET anywhere** (L-DQ-006). You cannot list dictionaries or look one up over REST. Keep the `id` from the create
  response, or take it from the dictionary's UI URL.
- Until `finishUpload` runs, added or deleted rows sit encrypted in an internal store. They are **not** visible to
  mappings, and deleted rows stay live.
- **One editing environment at a time (L-DQ-007, vendor).** A dictionary cannot take UI and API updates
  simultaneously:
  - on a UI-created dictionary, click **Convert to API** (Definition or Configuration tab) before REST can write it;
  - **Convert to UI** switches it back;
  - the create response's `customAttributes` carries a `MODE` attribute naming the environment that may update or
    delete it.

  A dictionary created through the API presumably starts in API mode, since the documented flow creates it and adds
  rows through the API. No receipt of the Convert click has been captured.
- **Host not mounted everywhere (L-DQ-008, disputed).** `<pod>-dqcloud-api` answered 200 on one org's pod
  and failed on another org's pod in a different regional domain. One record says 404 (not mounted), another says 401 (a role gap). The vendor examples
  all use dm-us pods. Resolve the host by DNS and make one authenticated call before you design on it.

### 4.3 Minimal flow

1. `POST.../dictionaries/` → keep `id`.
2. `POST.../dictionaries/<id>/rows`, in batches of ≤10,000 rows.
3. `POST.../dictionaries/<id>/finishUpload`.
4. Verify by running a mapping or profile that reads the dictionary (REST gives you no read-back), or download
   the data from the dictionary's Configuration tab in the UI.

---

## 5. Cleanse, parse, labeler and deduplicate assets

- **Authoring is UI** (Data Quality → New, or DI → New Asset). The migration clone path is proven for
  `RULE_SPECIFICATION`, profiles, MDM business entities, CAI processes, DBMI tasks and mappings, and existing cleanse and
  fuzzy deduplicate assets copied in from another org ran inside generated mappings (L-CDI-204, L-DQ-101). A verifier
  cloned through a v3 package (fresh GUID and name, output fields extended, SHA-256 re-hashed, import REUSE) imported
  and its mapping ran (L-DQ-130, 2026-11-02, §6.1). It is **untested** for parse and labeler assets. Try an export and
  import on one object before you plan on it.
- **Where they run** (L-CDI-279, 2026-10-28): cleanse, deduplicate and decision transformations fail on the Informatica
  Cloud Hosted Agent with EP_13236 (`libIDQTokenStandardiserZTransform.so`, `libIDQDecisionZTransform.so`); rule
  specifications run there. Bind mappings with those steps to a Secure Agent that has the Data Quality service.
- **What a Deduplicate outputs** (L-DQ-127, 2026-10-28): every incoming field passes through; `Out_RowId` and
  `Out_DriverId` come as the text `'1 - <SequenceId>'` (strip the prefix before joining on your key); the pair score is
  `Out_LinkScore` (`Out_DriverScore` reads 1.0 on every row); with consolidation on, the output adds one survivor row
  per cluster with `Out_IsSurvivor = 'Y'` next to the members (`'N'`): filter on it, or counts double. Keep unique ids
  out of the match fields (L-DQ-101).
- **Test** each asset on sample rows in its editor (design time, on the agent).
- **Execution** only happens inside the matching transformation of a CDI mapping ([Data Integration (CDI)](../03-cdi-data-integration/)).
- **A headless alternative for cleansing logic:** the hosted CLAIRE DQ agent profiles an uploaded file and generates a
  complete cleansing transformation in the IDMC **Python-transformation** dialect ([03](03-claire-dq-agent-file-based-profiling-cleansing.md)).
  In these sources that code was executed locally by a harness. Running it inside an IDMC mapping as a Python
  transformation is untested.
- **Deduplicate / match rules need a business decision (L-DQ-068).** A fuzzy rule keyed on surname plus
  street number merged people with different first names and e-mails at 100% confidence. Either tighten it (add e-mail
  domain or phone) or present it deliberately as a *household* match. Decide before showing match results.
- **A name and address cleanse that keeps correct typing (L-CAI-086).** Plain INITCAP makes correct names
  worse (`MacArthur` → `Macarthur`, `de la Cruz` → `De La Cruz`). A rule that held, per word `w`, with space, hyphen,
  straight and curly apostrophe as delimiters:

  ```
  keep typed w   if w ~ ^\p{Lu}\p{Ll}+(\p{Lu}\p{Ll}{2,}){1,2}$          (deliberate inner capitals)
  keep lower w   if w in {da,das,de,del,della,der,di,do,dos,du,la,le,van,von,den,ter,ten,bin,ibn,al,el}
                 and the name has more than two words and w is not the first word
  else           INITCAP(w)                                          (ALL CAPS and random case are still fixed)
  ```

  For addresses: collapse runs of spaces, title-case street and city only when the value was typed all lower-case
  (keeps `NE` and `McKinney`), and `upper(trim)` the state. Put the **same** rule in every writer of the field (the
  golden mapping and each of its targets, the real-time CAI path, the CRM sync): with two different rules the passes
  flip values back and forth. Bracketed tombstones such as `[erased]` get re-cased too, so match tombstones
  case-insensitively downstream. The mapping-side pattern is in
  [Mapping Design & Consolidation](../03-cdi-data-integration/06-mapping-design-consolidation.md).
- **Make cleansing visible in a demo (L-DQ-069).** Generate realistically messy inputs (case, spacing, formats) that
  still pass the application's API contract, so the cleanse has something to fix.

---

## 6. Verifiers and address verification

### 6.1 The verifier asset (vendor)

A verifier builds a template of input and output address fields. At mapping run time the Verifier transformation compares
the input with address reference data that the Secure Agent downloads, and then:

- **verifies**: fixes errors and completes partial records on a positive match;
- **formats**: to postal-authority rules or your own structure;
- **suggests**: a list of candidate addresses;
- **measures**: status and quality fields;
- **enriches**: global and country-specific enrichments; country certification standards.

It covers postal addresses only. E-mail and phone verification and geocoding are separate services and licences.

**Enrichments are switched on in the asset, not by output ports** (L-DQ-130, 2026-11-02). Three on-agent verifiers whose
outputs were address lines, ZIP, locality, state, ProcessStatus and ResultQuality verified addresses but wrote no
geocodes and no DPV values, although the agent held the geocoding reference files. A clone with geocode output
fields added (`/Variants/0/Enrichments/Geocodes/Standard/Value`, `/Latitude`, `/Longitude`) ran to completion
and returned every geocode empty with no error: the compiled mapping carried no geocoding option. Configure
geocoding and enrichment in the verifier asset's own process settings, prove one known address returns coordinates,
and read `ResultInfo.DataFilesUsed` (L-DQ-125). How to set the option headless is still open.

**On the agent** (L-AGENT-116, 2026-11-01): verification runs inside the Data Integration Server (no engine of its
own); the reference files end in `.MD6` (USA about 4.1 GB, no CASS files), a licence file is fetched at every start
(IPU-metered), and the job log prints NumFunctionServers, MaxMemoryMegabytes and preload use (1, 8,192 MB, 0 MB by
default). `Address verification library error (-12000)` 'insufficient memory' means the preload and memory settings
exceed what the DTM can give. Measured 160 and 550-580 addresses/s per DTM in two pipeline shapes: measure yours and
scale out over disjoint key ranges ([Secure Agent](../02-secure-agent-connections/01-secure-agent-install-run-tune.md) §1).

### 6.2 Cloud Address Verification REST (L-DQ-015, L-DQ-131, L-DQ-132; proven 2026-11-02/03)

```
POST <baseApiUrl>/dataquality/addressverification/api/v1/process
Authorization: Bearer <identity-service JWT>      (two-step login: identity Login → jwt/Token)
Content-Type: application/json
```

- Verifies, standardizes and geocodes addresses in 240+ countries.
- Up to **1,000 addresses per call**; 100 suggestions in interactive mode.
- The job token expires in **5 minutes**. Free resubmits are 2x (interactive) and 9x (QuickCapture).
- **POST only.** GET, PUT, PATCH and DELETE return 405. Swagger is at
  `https://<service URL>/dataquality/addressverification/docs/swagger-ui/index.html`.
- The regional base is the `idmc-api.<domain>` family (`dm-us`, `dm-em`, `dm-ap`, `dm-na`, `dm-uk`).
- **Other routes and the token** (L-DQ-131, 2026-11-02): the service's OpenAPI lists only `GET /api/v1/info` (status),
  `GET /api/v1/welcome` and the process call, with one Bearer-JWT scheme. A JWT minted for the catalog
  (`client_id=cdlg_app`, L-AUTH-022) was accepted for `/info` and a 2-address Certified call: check the token and host
  with `/info` before a bulk run. Unauthenticated requests answer 401 'Authentication token not provided'.

**Certified mode from a CDI Java transformation** (L-DQ-132, 2026-11-03):

1. **Shape:** Source (one partition and one hash slice per run, already-verified records skipped) → Rule Specification
   'required id' → Java transformation → Expression → append-only target.
2. **Call:** the Java step buffers 1,000 inputs and POSTs `https://idmc-api.<domain>.informaticacloud.com/dataquality/
   addressverification/api/v1/process` with `Parameters.Mode` Certified, one `CountrySets[]` entry (OutputDetail
   SubItems, ElementStatus, OutputStatusForEmptyElements; Process.Enrichments CountrySpecific, Global and Geocoding
   Rooftop and ArrivalPoint) and `IO.Inputs[]` of `{SourceID, AddressElements {Country, SubBuilding, Locality,
   AdministrativeDivision, PostalCode}, PreformattedData.PostalDeliveryAddressLines}`.
3. **Guard it:** up to 5 attempts with linear backoff (3 s x attempt), renew the token on 401, and fail the run if the
   output count differs from the input count.
4. **Keep everything:** parse ResultInfo, Variants[0].StatusValues, the address elements, the CASS certification
   block, the geocodes and the census, FIPS, CBSA and time-zone enrichments, and store the whole response JSON and its
   SHA-256 on every row: 17 returned fields existed only in the JSON and were back-filled later with no new calls.
5. **Secrets and governance:** keep the short-lived Bearer token in a tmpfs file on the agent host, renewed by a helper
   that keeps at least 300 s of validity, never in the mapping, a parameter or a log. No IDMC connection holds this
   credential, so the call is invisible to connection governance and lineage: document it.
6. **Scale:** clone the mapping into a few shard tasks over disjoint hash slices (4 ran in parallel), cap the source
   query's memory (L-CDI-292), and select each batch by an anti-join to stored results on an input fingerprint plus the
   reference-data version, never from a deletable cursor (L-CDI-283).

**Classify the 'failed' rows before fixing them** (L-DQ-129, 2026-11-02). Bucket the failed Certified responses by
ResultQuality, the HouseNumber element and the Street value, read from the stored JSON. Five classes recur: premise
found but unit not confirmed (these rows still carry rooftop coordinates, census and DPV, so they are verified
premises mislabelled as failed), street with no house number, house number given but street not found, street found
but house number invalid, and placeholder or no street. Treat ResultQuality >= 4 with DPV confirmation D or S as
'verified, unit unconfirmed' (no new calls needed); route no-house-number and placeholder rows to a
geocode-by-location path or a steward queue instead of paying for another Certified call; cleanse and re-derive ZIP
and city before one re-verify. Verified shares vary widely by region and source quality: measure your own, by class.

### 6.2a Which path enriches most (L-DQ-125)

| Data file (ResultInfo.DataFilesUsed) | What it adds | Cloud service, Certified | On-agent verifier (typical USA install) |
|---|---|---|---|
| VRF/BIA | verification, standardized elements | yes | yes |
| VRF/C02-C07 | CASS: DPV and footnotes, RDI, LACSLink, SuiteLink, eLOT, barcode, carrier route, congressional district | yes | only if the CASS files are installed |
| ENR/EN1 | FIPS, census tract / block / block group, MCD, MSA, CBSA, place, time zone | yes | yes |
| ENR/GRT, ENR/GAP | rooftop and arrival-point geocodes | yes | yes |
| ENR/GST | Standard (street-level) geocode | not returned | yes |

Use the cloud service in Certified mode for the most fields, keep the whole output JSON per address, and fill the
Standard geocode from a local verifier only where rooftop and arrival point come back NothingFound. A requested
enrichment with no data file returns nothing and no error, so always read DataFilesUsed.

### 6.3 Managed MCP `verify_address` in a pipeline (L-DQ-016)

The Cloud Address Verification service is also the managed MCP server with context **`dqverifyaddress`** and tool
**`verify_address`** (Interactive mode). It handles one address per call and persists nothing. See
[Managed MCP Servers](../09-claire-mcp/01-managed-mcp-servers-catalog-access.md) for access and
[MCP Auth & OAuth Clients](../09-claire-mcp/02-mcp-auth-oauth-clients.md) for the token. A small polling job
(every ~20 s) that calls it for new records is a proven production shape; its first run made 583 calls with 0 errors.

1. **Read the pre-merge layer.** Extract from the per-record staging layer (every source record, minus erased ones),
   not from the de-duplicated golden view: a job that read the golden view never verified the source records that
   match-and-merge had folded into a survivor (L-DQ-016).
2. **Queue and cache on a normalized-address hash.** Key the work queue on a hash of the address fields (or on the
   last-modified time), so an address that is added or changed later is re-verified; a queue keyed only on "missing from
   the results table", or a "new records only" mode, never re-checks it (L-DQ-018). Cache results by the same hash:
   re-checks of unchanged addresses then make no call (51 re-checks cost 0 calls in one run).
3. **Cap calls** per run and per day.
4. **MERGE the results** (upsert, no duplicates) into a warehouse table with the result code per record. Codes seen:
   `VERIFIED`, `VERIFIED_CORRECTED`, `LOW_CONFIDENCE_MATCH`, `STREET_NOT_FOUND`, `HOUSE_NUMBER_NOT_FOUND`,
   `NO_ADDRESS`.
5. **Keep a first-verified timestamp that is set once**, separate from `checked_at`:

   ```sql
   MERGE <results> t USING <batch> b ON t.addr_hash = b.addr_hash AND t.record_id = b.record_id
   WHEN MATCHED THEN UPDATE SET status = b.status, checked_at = b.checked_at,
        first_checked_at = COALESCE(t.first_checked_at, t.checked_at)
   WHEN NOT MATCHED THEN INSERT (record_id, addr_hash, status, checked_at, first_checked_at)
        VALUES (b.record_id, b.addr_hash, b.status, b.checked_at, b.checked_at)
   ```

   Count a latency sample only when the first check lands within a few minutes of the record's creation. Lost first-check
   times can be recovered with warehouse time travel (`FOR SYSTEM_TIME AS OF` a moment before the change, within about
   7 days, L-CDI-161).
6. **Swap the job's code safely:** under the same `flock` the job takes, after checking the live files' checksums,
   with a backup and an undo script.
7. Without e-mail or phone verification licences, fall back to CDQ format flags for those fields.

**Test data that can verify (L-DQ-016).**

| Test input | What the service answers |
|---|---|
| invented streets (random house number + generic street name) | always `STREET_NOT_FOUND` or `HOUSE_NUMBER_NOT_FOUND`, however often you re-check or raise caps |
| a small pool of real **public** addresses (civic buildings, libraries, arenas; never private homes) | 25 of 25 `VERIFIED` |
| messy variants of those (lower case, missing suffix or direction, spelled-out suffix, wrong ZIP) | 9 of 10 `VERIFIED_CORRECTED` (the tenth was already clean) |

Keep a small invented share behind a knob (a mix of about 72% clean, 24% messy and 5% invented kept both the correction
and the exception story). Check that pool addresses do not collide on your match key (surname + initial + street
number) before assigning them. Enrichment that deliberately skips test identities must still be proven on one real
record.

**Measured:** record creation to first check about 33-34 s average (24-44 s; n = 11-13 per 24 h) with a 20 s polling
job; a few minutes more until visible in BI, depending on the BI refresh path.

| If you see | Cause | Fix |
|---|---|---|
| verified rate stuck near 0 | invented test addresses | seed from real public addresses plus messy variants |
| merged duplicates never verified | the job reads the golden view | read the pre-merge staging layer |
| "record to verified" latency reads hours | re-checks overwrote the only timestamp | `first_checked_at` set once (COALESCE in the MERGE); restore by time travel |
| calls grow with every run | no cache, or a queue keyed on "missing from results" | queue and cache on the address hash |

MCP calls to `verify_address` do **not** appear as IDMC jobs and do not count against the org's monthly job limit
(L-DQ-017). Describe the enrichment accordingly, and budget IPUs for the backing service
([IPU, Metering & Licensing](../11-ipu-metering-licensing/)).

---

## 7. Adjacent products that are *not* DQ scoring paths

- **Data Quality for Fabric (DQF)** (L-DQ-013). A preview run from the Microsoft Fabric UI that profiles
  Fabric data. It has no rules, no scorecards and no REST, API or RunAJob surface, so it is not a scoring path. A CDI
  mapping task that evaluates rules is stronger.
- **Data Preparation** (L-DQ-014).
  - `/dataprep/projects` and `/prep/v1/projects` returned 404 on GET and POST;
  - `<pod>-prep` and `<pod>-dataprep` had no DNS on at least one pod.

  Treat it as UI-only or absent there. Meet parsing needs with a parse asset in a mapping, or with deterministic code.

---

## 8. What needs a CDI mapping to execute

| Goal | Asset | Transformation / runner | Headless run |
|---|---|---|---|
| Standardize values on production data | Cleanse | Cleanse transformation in a mapping | `POST /api/v2/job` on the mapping task |
| Split free text into fields | Parse | Parse transformation | same |
| Label tokens or characters | Labeler | Labeler transformation | same |
| Find and merge duplicates | Deduplicate | Deduplicate transformation | same |
| Verify postal addresses in bulk | Verifier, or the cloud service | Verifier transformation (agent downloads reference data), or a Java transformation calling the cloud service in Certified mode (§6.2; L-DQ-132) | same |
| Evaluate a business rule per row | Rule specification | Rule Specification transformation | same |
| Score rules on a table | Rule specification + profile | Data Profiling rule occurrences | `POST /profile/<id>/execute` on `<pod>-dqprofile` ([02](02-profiling-what-is-headless.md)); no mapping needed |
| One-off address check | none | managed MCP `verify_address` or AV REST | MCP call / REST POST |
| Profile and cleanse an uploaded file | none | hosted CLAIRE DQ agent `data_quality_cleansing` | MCP ([03](03-claire-dq-agent-file-based-profiling-cleansing.md)) |

How to run a mapping task headless is covered in [Data Integration (CDI)](../03-cdi-data-integration/).

---

## 9. Overturned beliefs (kept so nobody re-learns them)

| Belief | Held | Overturned by | Lesson |
|---|---|---|---|
| "Native CDQ rule authoring is UI-only" (from 405 on `/v3/objects` and 404 on `/data360/dq/*`) | 2026-07-04 to 2026-07-07 | The migration clone of a template rule spec (2026-07-09). Only new *logic* still needs the canvas. | L-DQ-083 → L-DQ-010 |
| "CDQ has no REST write path at all" | until 2026-07-25 | The documented Dictionary API, with create proven live | L-DQ-084 → L-DQ-006 |

---

## 10. Open questions

- Does the migration clone work for parse and labeler assets? (It works for cleanse and deduplicate assets, L-CDI-204,
  and a verifier clone imported and ran, L-DQ-130.)
- How is a verifier's geocoding or enrichment option set headless? Added output fields alone did not switch it on (L-DQ-130).
- What exact receipt does **Convert to API** leave? Does an API-created dictionary start in API mode?
- Which pods mount `<pod>-dqcloud-api`? The 404 vs 401 records on the second pod have not been reconciled.
- Can a CLAIRE-generated Python transformation run unchanged inside an IDMC mapping's Python transformation?
- The three rule-translation semantics (REG_MATCH full match, IS_SPACES(''), IN case sensitivity) against IDMC's own
  output.
