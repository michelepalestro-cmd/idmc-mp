# Mastering a Table: a Repeatable Playbook (by dataset type)

**Answers:** How do I turn one warehouse table into mastered records (one trusted record per real-world thing), step by
step, the same way every time? Which match, survivorship and acceptance rules fit which kind of dataset (an entity
with fuzzy identity, a small registry, a versioned asset registry, a data dictionary, events)? How do I prove a table
is mastered with queries instead of opinions?

**Read when:** someone asks to "do MDM on" or "master" a table; a table has duplicate or conflicting rows for the same
thing; two pipelines both claim to publish the golden version; you are planning match-merge for a dataset that is not
a person or an organization.

**Key rules:**
- Classify the dataset first (section 1). The archetype decides the match key, the survivorship rules and the gates.
  Most bad merges come from using the person or address recipe on something else (L-MDM-044, L-MDM-075).
- One physical table can hold several archetypes (an entity plus its events plus its relationships, told apart by a
  record-kind column). Master each record kind on its own terms.
- Deterministic tiers first, fuzzy rules last. Measure key collisions before turning anything fuzzy on (L-MDM-042,
  L-MDM-044).
- One cross-reference row per source record, and survivorship reads only the cross-reference (L-MDM-075).
- Exactly one golden owner per entity scope. Two builds publishing golden rows for the same entities is a defect, not a
  backup (L-MDM-079).
- "Mastered" means the gates in section 4 pass, measured on the published table.
- The rules run as IDMC transformations (Cleanse, Verifier, Rule Specification, sorted Aggregator, Router), not as
  a long query in the Source; one parameterized mapping per table, never one per scope (section 6, L-MDM-081).
- Wording: in an Informatica conversation a warehouse result is a trusted curated layer, or the master record of a
  stand-in, not "MDM" (L-MDM-052). When a party domain is licensed in MDM SaaS, the same spec becomes the Business 360
  model, and the cutover follows L-MDM-051.

**Related:** [Business 360 Modeling & Match-Merge](03-business-360-modeling-match-merge.md) (native MDM, and the
CDI-mapping MDM pipeline) · [DQ Assets](../06-data-quality-profiling/01-dq-assets-rule-specs-cleanse-dictionaries-verifiers.md) ·
[DQ Scorecards](../06-data-quality-profiling/04-dq-scorecards-warehouse-pattern-and-data-profiling-scorecards.md) ·
[Mapping Design & Consolidation](../03-cdi-data-integration/06-mapping-design-consolidation.md) ·
[Glossary, Links & Classification](../07-catalog-governance-cdgc/03-glossary-links-classification.md) ·
[Lessons: MDM](../../lessons/by-domain/08-mdm.md)

**Last verified:** 2026-11-03

> **Summary.** Every mastering job runs the same ten steps: profile, define, standardize, rule, match, cross-reference,
> survive, relate, steward, publish. What changes between datasets is *how* steps 5-8 are done and *which* gates prove
> it. Section 1 picks the archetype, section 2 is the ten steps, section 3 is the per-archetype recipe, section 4 is the
> acceptance gates (copyable SQL), section 5 is the one-page spec to fill in for every new table, and section 6 is the
> mapping set that does the work inside IDMC.

---

## 1. Step 0: classify the dataset (five archetypes)

Answer these in order, for each record kind in the table:

1. **Does a row describe something that happened** (a sale, transfer, assessment, listing, payment, evaluation run)?
   Then it is an **E - Event**. Events are not mastered on their own: they are de-duplicated to a canonical event and
   attached to a master.
2. **Is it a definition of data** (column definitions, code lists, crosswalks, quality rules, vocabularies)?
   Then it is a **D - Definition**.
3. **Does the thing have versions that must all be kept** (model versions, document revisions, product releases), with
   one of them "current" per scope? Then it is a **V - Versioned asset**.
4. **Is it a small, curated list** (roughly under 100,000 rows: data sources, vendors, branches, a catalog), where a
   person can review every merge? Then it is an **R - Registry**.
5. **Otherwise it is an M - Entity master**: many sources, no trustworthy global key, identity decided by matching
   (people, organizations, locations, properties, devices).

| Archetype | Typical examples | Identity comes from | Who approves merges |
|---|---|---|---|
| **M - Entity master** | property, parcel, customer, location | match rules over standardized attributes | rules auto-merge confirmed tiers; a steward reviews ambiguous groups |
| **R - Registry** | data-source catalog, vendor list, branch list | a canonical name + scope + domain, plus an alias list | a steward approves every merge (the list is small) |
| **V - Versioned asset** | ML model registry, documents, product versions | an asset id + a version id, after an alias crosswalk | rules (exact keys); a steward only for crosswalk gaps |
| **D - Definition** | data dictionary, code lists, rule catalog | (table, column) or (vocabulary, code), with effective dates | the data owner; the live schema is the referee |
| **E - Event** | sales, assessments, listings, evaluations | master id + event type + date + amount or instrument | rules, plus a conflict group for a steward |

Do not mistake fan-out for duplication. A registry that holds one row per dataset *per state* repeats every national
dataset once per state: the repeated name is the grain, not a duplicate. Model it as a parent (the dataset) with child
rows (the per-scope feeds) instead of merging (L-MDM-077).

---

## 2. The ten steps (every archetype)

Each step names its output and the IDMC asset that does the work. Python and SQL are for building and checking. The
runtime path is IDMC (CDI mappings, CDQ assets, a taskflow).

| # | Step | Output | IDMC asset |
|---|---|---|---|
| 1 | **Inventory and profile.** Rows, distinct candidate keys, blank and null rates, duplicate groups per candidate key, vocabulary variants (`Statewide` vs `statewide`), orphan foreign keys. | a profile sheet with numbers | Data Profiling, or warehouse SQL when profiling cannot reach the connector; CLAIRE rule recommendations |
| 2 | **Define the entity.** The grain (one row = one *what*), an immutable master id (never reused, never recomputed from attributes that can change), the business key, the hierarchy levels, and which columns are identity, attributes or derived. | a dictionary entry for every golden column | the data dictionary table, the CDGC glossary term |
| 3 | **Standardize.** Cleanse text, conform vocabularies, verify addresses, conform types, and stamp an input fingerprint so unchanged records are skipped on the next run. | one standardized row per source record | Cleanse, Verifier, reference dictionaries (L-CDI-266, L-DQ-120) |
| 4 | **Quality rules.** One severity scale for the whole domain: *hard* = cannot be golden, *soft* = golden with a flag, *info* = measured only. | rule results per record, reason codes | Rule Specifications in the mapping (L-CDI-263) |
| 5 | **Match.** Block on a candidate key, then match tier by tier: same source id, full business key, then anything fuzzy. Measure collisions per tier before enabling the next one. | candidate pairs and groups with a tier and score | Expression with variable ports over sorted input (L-MDM-075); MDM SaaS match model for party data |
| 6 | **Cross-reference.** One row per source record: source system, source key, master id, match tier, score, status (confirmed, merged, provisional, ambiguous). | the cross-reference (XREF) | the match mapping's second target |
| 7 | **Survivorship.** One rule per attribute group: source rank, most recent non-null, most complete, a qualified event beats a stale snapshot, derived values recomputed. Keep the winning record id per group as field lineage. | one golden row per master id | sorted Aggregator `FIRST(value, condition)` (L-CDI-263); MDM SaaS survivorship (L-MDM-039) |
| 8 | **Relationships and hierarchy.** Parent and child links (unit in building, feed in dataset, version of model), confirmed by evidence, never by inference alone. | relationship rows with a status | Router group in the golden mapping (L-MDM-076) |
| 9 | **Steward queue and overrides.** Ambiguous groups, hard-rule failures, same-key-different-master pairs. Decisions go to an override table (force merge, force split, retire) that step 5 reads first on the next run. | a queue with reason codes, an override table | Router to an issue target; Customer 360 tasks for native MDM |
| 10 | **Publish and certify.** Exactly one current golden publication per scope, a manifest row (expected, written, held, failed), the serving flag, and the gates in section 4. Consumers read only committed publications. | the golden table, a manifest row, gate results | publish mapping + taskflow; CDGC lineage scan |

Run it the same way each time:
- **Pilot one scope first** (one state, one family, one source), pass every gate there, then fan out by scope groups
  with the scope as an in-out parameter (L-CDI-265), never one mapping per scope.
- **Re-runs replace, they do not accumulate.** Version every golden row by run, and make sure the warehouse's
  replace key is the master id. If the sort key also carries a run or record id, re-runs pile up (L-MDM-079).
- **Incremental after the first load.** Only records whose input fingerprint changed go through steps 3-7. Their
  masters are re-survived as a whole, so a group never mixes old and new winners.

---

## 3. The recipe per archetype

### M - Entity master (fuzzy identity)

| Step | Rule |
|---|---|
| Match key | Deterministic tiers. R1 = same source system + source id. R2 = the full business key (for a property: state + ZIP5 + normalized parcel + normalized address + unit + class). Never merge on parcel alone or address alone (L-MDM-075). |
| Fuzzy | Only for party data (name populations), or to *propose* pairs into the steward queue. Measure degenerate keys first: one shared address can collapse hundreds of distinct records (L-MDM-044). |
| Survivorship | Attribute groups with one anchor each (assessed value and its tax year come from one observation). Transaction events beat snapshot fields when the event is qualified (arm's length, above a floor price). |
| Hierarchy | Unit -> building -> parcel or site. A building id comes from the verified premise without the unit. Units with no verified unit are held with a code (L-MDM-076). |
| Steward queue | Same business key under two masters, ambiguous groups, provisional matches (parcel-only, address-only). |
| Extra gates | Exact-key duplicates across masters = 0 or queued. Every provisional master has a reason code. Address verification status is on every row that has an address. |

### R - Registry (small curated list)

| Step | Rule |
|---|---|
| Match key | Normalized name + scope (state, county, town) + domain. The same name in a different scope is a different child, not a duplicate. |
| Fuzzy | Name similarity only to propose merges. A person approves each one. |
| Survivorship | The curated row wins over captured metadata. Keep every former name and URL in an alias list (the alias list is what lets old references resolve). |
| Hierarchy | Provider (publisher or domain) -> dataset (canonical product) -> feed (per scope). |
| Steward queue | Proposed merges, unresolved URLs, blank status. |
| Extra gates | Every foreign key elsewhere that points into the registry resolves to a surviving id or an alias. Placeholder ids like `unresolved` count as orphans. Status and scope vocabularies are closed lists. |

### V - Versioned asset (model registry and similar)

| Step | Rule |
|---|---|
| Identity crosswalk first | The same asset usually appears under several ids: a registry name (`<family>:<scope>`), an artifact file name (`<scope>.<asof-date>.<ext>`), and the legacy table that logged its evaluations. Build the alias crosswalk before anything else, or every later join is empty (L-MDM-078). |
| Match key | asset id + version id, exact, after the crosswalk. |
| Survivorship | Per version: the latest record version wins, and metrics come from the most complete evaluation. Per asset: exactly one current (champion) version per scope, decided by the promotion records. |
| Hierarchy | Family -> asset (per scope) -> version -> artifacts, evaluations, deployments. |
| Steward queue | Artifacts or evaluations whose id maps to no version, and captured rows that only look like versions (a table name used as the model id). |
| Extra gates | Every artifact is complete (all chunks present, checksum matches). Every evaluation and deployment links to a version. One champion per asset and scope. Every training dataset links to a published data version. Decision fields hold codes, with the sentence in a separate reason field. |

### D - Definition (data dictionary, code lists)

| Step | Rule |
|---|---|
| Match key | (target table, column) for column definitions; (vocabulary, code) for values; rule id for quality rules. |
| Survivorship | One current definition per key: the highest version with `effective_to` empty. Older versions stay as history, never deleted. |
| Reconcile both ways | Against the live schema: every live column has a definition, and every definition has a live column. A definition for a missing column is either retired or tied to a named planned change (a pending table rename). Check the change plan before retiring (L-MDM-080). |
| Vocabularies | One severity scale (hard / soft / info), one status scale per entry kind, closed lists for enumerations. |
| Steward queue | Unresolved source mappings, duplicate rule ids, definitions without a live column, the same description shared by unrelated columns. |
| Extra gates | Unresolved mappings = 0, or explicitly `not_applicable` with a reason. No rule id defined twice. Every golden-table column documented. |

### E - Event (sales, assessments, listings)

| Step | Rule |
|---|---|
| Match key | master id (from the cross-reference, never from a raw address) + event type + date + amount or instrument number, with a small tolerance on dates. |
| Survivorship | A conflict group per candidate duplicate set, plus one canonical row flagged inside it. Qualification codes (arm's length, transfer type) are attributes, not filters. |
| Keep, do not drop | Events with unknown or year-only dates, and zero-value events, are kept with a precision code. Dropping them is information loss. |
| Extra gates | Every event resolves to a master. Exactly one canonical row per conflict group. Portfolio (multi-property) transactions carry an allocation rule. |

---

## 4. Acceptance gates: "mastered" means these pass

Run them on the published table, for every scope, and store the results as a gate row (gate id, scope, value, pass,
run id). The examples are ClickHouse-flavoured and use the names from section 5. Rename them to your columns.

```sql
-- G1 Uniqueness: one golden row per master id in the current publication
SELECT count() AS rows, uniqExact(master_id) AS masters, rows = masters AS pass
FROM golden WHERE publication_id = {current_pub};

-- G2 Single owner: exactly one publication holds golden rows for each scope
SELECT scope, uniqExact(publication_id) AS owners, owners = 1 AS pass
FROM golden_history WHERE record_stage = 'gold' AND is_deleted = 0 GROUP BY scope;

-- G3 Coverage: every source record has exactly one XREF row; every master has at least one
SELECT count() AS unmapped_source_records FROM source_records s
LEFT ANTI JOIN xref x ON x.source_system = s.source_system AND x.source_key = s.source_key;
SELECT count() AS masters_without_xref FROM golden g LEFT ANTI JOIN xref x ON x.master_id = g.master_id;

-- G4 No exact business-key duplicates across masters (or every group is in the steward queue)
SELECT count() AS dup_groups, sum(n) AS dup_rows FROM (
  SELECT business_key, uniqExact(master_id) AS n FROM golden GROUP BY business_key HAVING n > 1);

-- G5 Hard rules: nothing served with a hard failure; every held row carries a reason code
SELECT countIf(serving_eligible = 1 AND has(dq_issue_codes_hard, 1)) AS served_hard_fail,
       countIf(serving_eligible = 0 AND empty(eligibility_reasons)) AS held_without_reason FROM golden;

-- G6 Lineage: every row names its mapping, task and run; every attribute group names its winning record
SELECT countIf(idmc_run_id = '' OR idmc_mapping_id = '') AS rows_without_run,
       countIf(field_lineage_json IN ('', '{}')) AS rows_without_field_lineage FROM golden;

-- G7 Referential integrity: every foreign key resolves (registries, parents); placeholders count as orphans
SELECT countIf(fk_id IN ('', 'unresolved') OR fk_id NOT IN (SELECT id FROM registry)) AS orphan_fk FROM golden;

-- G8 Reconciliation: legacy count = masters + merged-away + retired + held, per scope (every difference explained)
-- G9 Dictionary: every golden column defined, no definition without a column (unless tied to a planned change)
```

Gate thresholds: G1, G2, G6 and G7 must be exact. G4 is "0, or every group queued with a reason". G8 is "every
difference has a reason code". Report a gate that could not run as `UNAVAILABLE`, never as a green zero (L-MDM-054).

---

## 5. The one-page mastering spec (fill in per table, before building)

```
Table / record kind:            <db>.<table>  record_kind = <kind>
Archetype:                      M | R | V | D | E          (section 1)
Grain (one row = one ...):      <entity>
Master id:                      <column>, immutable, format <...>, generated by <step/mapping>
Business key:                   <columns, normalized how>
Scope parameter:                <state | family | source>   pilot scope: <one value>
Sources and rank:               1. <source> (trust high)  2. <source>  ...
Match tiers:                    R1 <rule>  R2 <rule>  (fuzzy: none | proposals only | <population>)
Collision check (before go):    <query>  result <n groups / n rows>
Survivorship per group:         <group>: <rule>, anchor <field>   ...
Hierarchy:                      <parent> -> <child>, confirmed by <evidence>, hold code <CODE>
Quality rules (hard/soft/info): <rule ids>
Steward queue reasons:          <codes>
Overrides table:                <table>, read by match step first
Publication + manifest:         <publication id pattern>, manifest <table>
Gates and thresholds:           G1..G9 (section 4) + archetype extras (section 3)
Owner of the golden scope:      <one pipeline, one writer>
Undo:                           <how a bad publication is withdrawn>
```

Order across related tables: master the registries and definitions first (they are the foreign-key and vocabulary
targets), then the versioned assets, then the large entity master, then its events. That way G7 and G9 can pass on
the large table the first time it publishes.

---

## 6. The mapping set: the logic goes in transformations, not in source SQL

A common failure mode looks like progress: dozens of mappings, each one a long warehouse query in the Source (all the
survivorship and vocabulary CASE ladders) followed by an Expression and a Target, copied once per state, shard or
table. IDMC then only moves rows. The rules cannot be reused or seen in lineage (the catalog shows "query -> table"),
DQ assets never run, and every change means editing N copies (L-MDM-081).

The test: open the mapping. If removing every transformation between Source and Target would change nothing that the
query does not already do, the mapping is not mastering anything.

The target shape, per table (one mapping per archetype and table, parameterized by scope and shard, never one per
scope):

| Step | Transformation | Archetype notes |
|---|---|---|
| Select and order | Source with a short query: columns, scope filter, ORDER BY the match key (sorting in the warehouse saves a Sorter cache) | V: read only the identity rows (versions, artifacts, evaluations), never the bulk snapshot rows |
| Drop what is not in scope | Filter | erased, test and placeholder records |
| Standardize | Cleanse asset (text, case, punctuation) + Expression for types | M: Verifier for addresses (L-CDI-266), with geocoding switched on in the asset's own settings (L-DQ-130), or the cloud service in Certified mode from a Java step (L-DQ-132); count 'premise found, unit unconfirmed' as verified-unit-unconfirmed (L-DQ-129). Cleanse, deduplicate and decision steps need a Secure Agent (L-CDI-279) |
| Conform vocabularies | Lookup on a reference table or a DQ Dictionary | one closed list per coded column |
| Quality rules | Rule Specification (hard / soft / info outputs) | R: URL present, status in list; D: definition complete |
| Match | Sorter (when the source cannot sort) + Expression with variable ports carrying the master id per key run (L-MDM-075) | R: name + scope; V: parsed asset id + version; for fuzzy party matching a CDQ Deduplicate: read the pair score from `Out_LinkScore` and filter on `Out_IsSurvivor` (L-DQ-127) |
| Survive | sorted Aggregator, `FIRST(value, condition)` per attribute group (L-CDI-263) | D: one current definition per key |
| Key | Sequence or a deterministic hash for new master ids | ids are never recomputed from changing attributes |
| Enrich | Joiner or Lookup to the registries (foreign keys) | G7 is decided here |
| Split | Router: golden / steward queue / retire candidate | every non-golden row carries a reason code |
| Publish | Target with a big write batch (L-CDI-262) + a manifest row | consumers read committed publications only |

When the warehouse table is a replacing engine (whole rows per version) and has columns the writer cannot round-trip
(arrays, maps), keep the fixing in the transformations, write a scalar staging batch, and let the target's Post SQL
merge it with `SELECT s.* REPLACE (...)` so the complex columns stay in the warehouse (L-CDI-273).

Plus one gates mapping for all tables (the section 4 queries from a parameter file, an Expression for pass/fail,
one gate row per table x gate x scope) and one taskflow that runs registries -> definitions -> versioned assets ->
entity master -> gates, with a Decision step that stops on a failed exact gate. A party-data pipeline built this way
reads like a story: filter test identities, standardize, look up the home location, rule-check, keep the best record
per person, key it, enrich it, route the weak ones to a steward, mask for sharing.

A golden-record mapping that re-reads and rewrites every record took the same 118 s on the Hosted Agent and on a 2-vCPU
Secure Agent: its time goes into reading and writing the full set, so the lever is an incremental design, not a bigger
runtime (L-AGENT-118).

---

## 7. Measuring progress toward a 100 % DQ score (DQ + DG evaluation)

Run the same evaluation after every fix, store each run, and compare with the previous one. A score that is not
re-measured the same way each time cannot show progress.

**DQ checks (per table, per row they apply to).** Write each check as `(id, dimension, severity, applies, fails)` and
compute both counts in one aggregate scan per table, grouped by scope (state, family). Cover every dimension:

| Dimension | Typical checks |
|---|---|
| Completeness | identity and address fields present; attributes present where they apply (beds only for residential, year built only for buildings) |
| Validity | formats (ZIP5, FIPS, GEOID), ranges (year, area, price), closed vocabularies |
| Uniqueness | G1 and G4 from section 4 |
| Consistency | cross-field: county code inside the row's state, tract inside the county, assessed = building + land, a unit has a parent, a held row has a reason, a status flag agrees with its detail flag |
| Accuracy | postal verification status; geocode precision |
| Integrity | foreign keys resolve (placeholders count as failures) |
| Lineage and timeliness | run ids stamped, per-field lineage present, processed and observed recently |

**Score.** Per check, pass rate = 1 - fails / applies (skip checks that apply to 0 rows). Table score = weighted mean
(hard x2, soft x1, info not scored). Also report the share of rows with no hard failure: it is the number that reaches
100 only when every row is clean. Sort the check list by "points to 100" (weight x missing pass rate / total weight),
so the next fix is always the one that moves the score most.

**DG checks (per table, pass or fail).** Every live column defined, and every defined type equal to the live type.
Sensitivity classified (more than one access tier in use). Columns covered by a *testable* rule. Source mappings
resolved. An IDMC profile on the table itself (not a copy) that completed, with rules bound. Catalog rule occurrences on
the table. A glossary term. Lineage. Where the DQ score is published for apps, consoles and CLAIRE:
[DQ Scorecards](../06-data-quality-profiling/04-dq-scorecards-warehouse-pattern-and-data-profiling-scorecards.md).

**Traps that make a score look better than it is (L-DQ-121, L-DQ-122):**
- A status column that says `passed` on every row while the score column is empty: the status is a stamp, not a result.
  Gate on "passed carries a measured score".
- Allowed-value lists generated from the values observed in the data, including the blank value. That documents dirty
  data as valid. A controlled vocabulary is written first and the data is tested against it.
- Rule catalogs whose entries are process notes ("validation remains incomplete until ...") instead of expressions.
  Count only testable rules as coverage.
- Constraints enforced on insert: they pass by construction (bad rows were rejected or never written). Count the
  rejects, not the pass rate.
- A profile that reads a copy of the table, or that has never run, and profiles with no rules bound: profiling alone
  produces statistics, not a DQ score.
