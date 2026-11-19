# Business 360 Modeling & Match-Merge

**Answers:** Which design clicks does a Business 360 model need, and in which order? How do I create and run a Match and
Merge job, and where do its runs show? Why do match-merge results go wrong? What does a warehouse stand-in need while
native MDM is not ready, including write-back and erasure?

**Read when:** designing an MDM model or match rules; a match/merge result merges different people or nothing at all;
running a golden-record stand-in; writing golden values back to source systems or erasing a person.

**Key rules:**
- Design, publish and job runs are Business 360 UI steps; My Jobs is the only place their runs show (L-MDM-005,
  L-MDM-016, L-MDM-018).
- A surname + street-number key merges different people at one address: add the first initial, and change every copy
  of the key together (batch, real-time view, the application itself) (L-MDM-072, L-MDM-073).
- Measure divergence and collisions before promising reconciliation or fuzzy matching (L-MDM-044, L-MDM-045).
- Attribute activity to the golden customer through the match key, never by the raw e-mail on the transaction
  (L-MDM-071).
- A golden-record write-back must also update the identity provider the apps display names from, and an erasure must
  fan out to every replicated layer (L-MDM-074).
- Name a SQL dedup layer a trusted curated layer; "golden record" means MDM (L-MDM-052).

**Related:** [Mastering a Table - Repeatable Playbook](05-mastering-a-table-repeatable-playbook.md) (classify the dataset, the ten steps, acceptance gates) ·
[MDM Runtime vs Design](01-mdm-saas-runtime-vs-design.md) ·
[MDM Records](02-mdm-records-ingest-search-export-cleanup.md) ·
[Mapping Design & Consolidation](../03-cdi-data-integration/06-mapping-design-consolidation.md) ·
[CDC from PostgreSQL](../04-cdc-mass-ingestion/02-cdc-from-postgresql.md) ·
[Lessons: MDM](../../lessons/by-domain/08-mdm.md)

**Last verified:** 2026-10-03

> **Summary.** The Business 360 Modeler authors business entities, source systems, match models and survivorship
> (source ranking, trust, best-version rules); the Business 360 Console runs and shows jobs; the Customer 360 app is for
> search, records and stewardship. A Match and Merge job runs Lock, Match, Merge, Index for Search, Group Potential
> Matches, Release, and took 16-25 minutes regardless of size. Most match-merge failures were data-premise failures:
> rules that merge households, degenerate addresses, and sources that never actually diverge.

---

## 1. The three MDM surfaces

All on `https://<pod>-mdm.<domain>.informaticacloud.com` (L-MDM-048).

| Surface | Path | What it does | Headless equivalent |
|---|---|---|---|
| Business 360 Modeler (inside the Console) | `/ui-config-app` | Business entities, field groups, keys, source systems, match models, merge and survivorship rules, publish | None (L-MDM-005); design objects can be cloned by migration (L-MDM-013) |
| Business 360 Console | `/ui-config-app`, My Jobs at `/ui-config-app/main/jobs` | Explore (projects, process assets, job definitions), job creation and runs, job schedules, job history | None for runs (L-MDM-016) |
| Customer 360 | `/ui-x360-app/app/c360/` | Search, master and source records, survivorship details, merge and unmerge, workflow inbox, file import, reports, My Jobs | Search, ingest and read are headless; steward decisions are not |
| Multidomain MDM, Supplier 360, Product 360, Reference 360 | `/ui-x360-app/app/mde`, `/s360`, `/p360`, `/rdm-ui/` | Domain apps | Reference 360 search is headless (L-MDM-026) |

---

## 2. The design clicks, in order

1. **Business entity.** Create it (or extend a stock one: the stock Person entity is SSN/DUNS-oriented and carries
   none of your fields, L-MDM-041), add field groups and fields, and designate the business key.
2. **Types and keys.** Map source types deliberately (floats to Double, integers to Integer, dates to Date,
   timestamps to Date Time with milliseconds, money to Decimal, coded values with leading zeros to Text), do not attach
   one key-format validator to an id whose shape differs by source, and null out sentinel defaults on extract
   (L-MDM-046).
3. **Source systems.** Register each contributing source, named exactly as your ingest code will send it.
4. **Match model.** Rules, strategy (exact or fuzzy), candidate selection and match keys.
5. **Merge and survivorship.** Source ranking, trust, best-version rules, and the auto-merge thresholds (section 5).
6. **Save and publish** (the disputed step, see [Runtime vs Design](01-mdm-saas-runtime-vs-design.md) section 4),
   capture the console's confirmation text as the receipt, and prove it with the ingest gate.
7. **Supplier entities.** Turn off out-of-the-box DUNS, SSN, tax and bank enrichment you have no data for: it bills
   per external lookup; verify by re-exporting the model (L-MDM-040).

Budget real time for this: it is a working session in the Modeler, not one click.

---

## 3. Jobs, and why only the console shows them

| Job | What it does | Where it shows |
|---|---|---|
| `<BE> MatchMerge` | Match and merge a business entity's source records into master records | My Jobs |
| Search Reindex (`c360.search.index`) | Builds the search index; records appear in the UI only once indexed | My Jobs |
| Ingress / egress | Load into, and export out of, MDM | My Jobs |
| Job Recovery and other job definitions | Maintenance; they expose Job Schedules and Add Job Schedule | Explore, My Jobs |
| Resolve Long-Running Operations | System job that completes timed-out create, update and delete operations | My Jobs |
| Bulk edit, process hierarchies | Mass edits; hierarchy processing (one job per hierarchy at a time) | My Jobs |

- **Ground truth.** My Jobs is the evidence that native MDM ran: successful MatchMerge and ingress rows prove the
  entity is deployed and survivorship executed. REST collectors, v3 objects and CDGC activity do not see these jobs
  (L-MDM-018).
- **No Run button.** Process assets (Ingress, MDMFlow) offer Properties, View, Edit, Publish, Unpublish, Export and
  Delete but not Run; runs start when data lands, on a schedule, or through a job (L-MDM-017).
- **Stopped jobs cannot be restarted** and may leave data partly processed; download rejected records within 7 days
  (L-MDM-035).
- **Schedule service failures.** "Cannot load the data... contact Informatica Global Customer Support" on Add Job
  Schedule, with Save failing "Enter a value", is a degraded backend: open a support case (L-MDM-047).
- **A wedged reindex.** A Search Reindex job stuck in Running leaves search empty, can have Stop and Restart both
  disabled, and has no reindex-now button; a fresh reindex comes from a publish-time trigger, a schedule or the API
  (L-MDM-031).

---

## 4. Create and run a Match and Merge job (L-MDM-036, L-MDM-037)

1. Business 360 Console: New... > Jobs > Match and Merge > Create.
2. Display name; Process Type Match and Merge; the business entity; the match model (for example a published
   baseline deduplication model); Version Latest.
3. Save ("saved successfully"), then Run ("job started successfully").
4. Watch the stage graph: Lock, Match, Merge, Index for Search, Group Potential Matches, Release.
5. Before trusting an automatic merge on new rules, inspect the candidate pairs in the Match Analysis and
   Explainability views.

| Fact | Value |
|---|---|
| Duration | about 16-25 minutes regardless of row count (one 10-record run took 25 min 16 s) |
| Queueing | generate match keys above 5,000 records, index for search above 10,000: queued is expected |
| Automation | headed browser (xvfb); headless runs stalled |
| Match-and-export results | import them within 4 days of the Release The Job step, or they expire |

---

## 5. Survivorship, trust and ranking (L-MDM-038, L-MDM-039)

- Survivorship is configured in the model by an administrator: trust, source ranking and criteria. An ingest-time
  `trustScore` does not define it, and it is unproven that survivorship honours it at all.
- **Source ranking.** If the ranking lists only one source, precedence between sources is undefined: rank every
  contributing source system.
- **Best-version rules per attribute.** Typical choices: most trusted source for email, most recent for name,
  non-null for external ids, earliest for first-seen dates, recompute for derived scores.
- **Change control.** Editing a published match model creates a new model version and a re-index.
- **In Customer 360.** Survivorship details (rules, rankings, trust scores) can be shown per record; a steward can
  override survivorship (the chosen value gets the highest trust), merge masters manually, and unmerge source records
  (patch records follow their source records).
- **Deleting sources** recalculates the master's trust scores from the remaining active sources
  ([MDM Records](02-mdm-records-ingest-search-export-cleanup.md) section 6).

---

## 6. Match-merge lessons

| Lesson | What happened | Do this | ID |
|---|---|---|---|
| Measure fuzzy thresholds | Jaro-Winkler for nickname pairs such as Bob/Robert is about 0.69, far below a 0.92 threshold | Add another signal (exact normalized phone, surname token, a nickname map) | L-MDM-042 |
| Numeric survivorship | SUM over duplicates double-counted (6,400 instead of 2,100) | MAX or a consolidated value | L-MDM-042 |
| Household matches | A surname plus street-number rule merged different people at full confidence | Tighten it (email, phone) or present it as a household match | L-MDM-043 |
| Degenerate addresses | A fuzzy address rule would have collapsed tens of thousands of distinct record groups; one address was shared by 306 records | Match deterministically on a real business key; measure collisions first | L-MDM-044 |
| Party models | SSA-NAME3 populations are person and organization identity models | Do not use them for non-party entities | L-MDM-044 |
| Data premise | Two stores that looked like two sources were a byte-identical mirror (0 divergence) | Measure divergence before promising reconciliation | L-MDM-045 |
| Single-source runs | One source gives one master per source record and zero consolidations | Expect 1:1; that is a pass, not a failure | L-MDM-045 |
| Existing masters | The runtime already held hundreds of active masters from earlier runs | Reconcile before a bulk ingest | L-MDM-032 |
| Household key | A deterministic key `lower(surname)\|house-number` folded two people of one household into one golden record, so a new sign-up "disappeared" | Use `surname\|first-initial\|house-number`, and `surname\|first-initial\|email` when the address has no number; tie out counts before and after | L-MDM-072 |
| Every copy of the key | The key lived in the batch mapping, a real-time dedupe view and the application's own customer rows (driving a one-subscription-per-person guard and a staff duplicate list) | Search code and stored key columns; change every copy together, with the same token rules and fallback | L-MDM-073 |
| Attribution | Spend joined to customers on the transaction's e-mail undercounted everyone whose payments sat under a merged duplicate's e-mail | Credit each payment to its booking or order owner, map every e-mail to its golden id through the same person key, aggregate by golden id | L-MDM-071 |

---

## 7. Stewardship

- Search and read are headless; steward decisions (approve, reject, merge, unmerge in the workflow inbox) are UI-only.
- The consolidated task inbox was a preview in April 2026 that support enables per org; the stewardship review
  workflow itself is generally available (L-MDM-038).
- Stewards need the Customer 360 Data Steward (or MDM administrator) role.

---

## 8. While native MDM is not ready: a stand-in and a gated cutover

- **Stand-in (L-MDM-050).** A warehouse SQL realisation per domain: stage, normalize, cross-reference (source system,
  source key, match tier, score, trust), attribute-level survivorship, a steward queue, a reversible merge-override
  table, a serving view and validation. Keep one canonical table (other names as views) and keep consumers on its id,
  so the producer can switch to MDM without downstream rework.
- **Naming (L-MDM-052).** In Informatica conversations "golden record" and "single source of truth" mean MDM; call a
  SQL dedup layer a trusted curated layer.
- **Readiness (L-MDM-053).** Per domain: activation plan, runbook, entity spec, ingest script, reconcile harness and
  a machine-checkable activation proof (the ingest route flipping from 404 to 201). The first native ingest and
  match/merge is a metered run that needs approval.
- **Cutover (L-MDM-051).** Modeler step, ingest, first match/merge, then a native-versus-stand-in reconcile (counts,
  cross-references, survivorship winners) that must show zero drift, QA sign-off and approval, then re-point
  consumers. Gate the reconcile harness behind the ingest gate so it exits cleanly until the entity is live.
- **Monitoring (L-MDM-054).** Until jobs exist, emit an explicit "unavailable" metric rather than a green zero.
- **Write-back must reach every copy the screens read (L-MDM-074).** Applications usually display a person's
  name from the identity provider's login token (captured at sign-in), not from the customer table. A golden-record
  write-back that updates only the operational table leaves every app showing the typed value. Before calling a
  write-back done, list each copy the screens read (database rows, identity-provider profile and token claims, CRM,
  caches), then:
  1. in the write-back handler also update the identity provider's first and last name, but only when the words are
     equal ignoring case (a re-casing, never another person's name), keeping its own first/last split; audit the change
     and never fail the write-back on an identity-provider error;
  2. let the web session re-read the login profile about once a minute, and let mobile prefer the API profile value
     when the e-mail matches;
  3. back-fill existing logins that differ, and re-check drift afterwards (0 of 30 after one back-fill).

  Measured: typed record to fixed in the database and the login in 1.5-2.7 minutes (golden mapping plus a 120 s
  activation loop); an open web session followed about 20 s later. Write back only whitelisted identity, contact and
  address fields of DQ-valid records, normalised to the source's own convention so an unchanged record writes nothing
  ([Source & Target Gotchas](../03-cdi-data-integration/09-source-target-gotchas.md)).
- **Erasure is a fan-out, not a delete (L-MDM-074).** A privacy erase in the source system does not propagate by
  itself to CDC replicas and IDMC-built layers: minutes after an erase the old e-mail, phone or name still sat in CDC
  tables, real-time views and curated or activation tables (36 warehouse tables checked), plus log and outbox tables in
  the source database, while the CRM was correctly anonymised. CDC carries the delete into the warehouse tables, but the
  warehouse change history (time travel, about 7 days) still returns the rows, a CRM contact keeps its fields, and the
  identity provider keeps the login (L-DBMI-051;
  [CDC from PostgreSQL](../04-cdc-mass-ingestion/02-cdc-from-postgresql.md)). Design the erase per layer:

  | Layer | Erase action | Check |
  |---|---|---|
  | operational database (incl. logs, outbox) | delete or anonymise | key search returns nothing |
  | CDC landing, real-time views, curated and golden tables | tombstone and purge per layer | key search across every dataset |
  | warehouse change history | document the residual time-travel window, or shorten it if policy requires | policy sign-off |
  | CRM and other SaaS copies | anonymise or delete the record | read back |
  | identity provider | delete the login | login fails |
  | activation and reverse-ETL | skip tombstoned and erased keys | next run writes nothing for the key |

---

## 9. Automating the UI (L-MDM-048)

Log in on the identity host and let SSO carry over; log in fresh per script (the console session lasts about 30
minutes). Deep links such as `/explore/<id>` render empty when cold: navigate Explore > All Projects > the project.
Grid rows are `role=row`, the kebab menu appears only on hover, and the Customer 360 search uses
`div[data-testid='mdm-bui-search-dropdown']`, `span#selected-entity` and `input[aria-label='Search input']`. Calls to
MDM services from inside the page context are blocked by its content-security policy (L-MDM-015).

**Open question (L-MDM-049).** The Modeler must call something non-public when it saves or publishes. Capturing the
browser network trace during one real publish would settle the biggest untested gap; never paste captured cookies or
authorization headers anywhere.

---

## 10. Overturned beliefs (this area)

| Belief | Believed | Overturned by |
|---|---|---|
| MDM is undeployed because its REST endpoints 404 | to 2026-07-06 | L-MDM-018 (L-MDM-060): My Jobs showed successful MatchMerge runs |
| The Product 360 docs describe the MDM you have | to 2026-07-26 | L-MDM-055 (L-MDM-067) |

## An MDM-style pipeline in CDI mappings (no MDM service), proven 2026-11-01

The step-by-step method around this pipeline (dataset archetypes, the ten steps, acceptance gates G1-G9, the
one-page spec) is [Mastering a Table - Repeatable Playbook](05-mastering-a-table-repeatable-playbook.md).

When the master must live in a warehouse table (no Business 360 model), build the MDM stages as a few parameterized
CDI mappings plus one linear taskflow, not one mapping per table or per region (a stand-in in the sense of L-MDM-050;
call its output the master record of the stand-in, L-MDM-052):

| Stage | Mapping shape | Lessons |
|---|---|---|
| Standardize & verify | query source (records not yet verified, by input fingerprint) -> Cleanse -> Verifier -> Expression interprets ProcessStatus / ResultQuality -> one verified-address row per entity and input | L-CDI-266, L-DQ-120 |
| Match & merge | query source ordered by the standardized key -> Expression recomputes the key -> variable ports assign the master id -> one cross-reference row per source record (confirmed / merged) | L-MDM-075 |
| Survivorship | cross-reference-joined source ordered by master id, newest first -> sorted Aggregator `FIRST(value, condition)` per attribute group, `FIRST(record_id, condition)` for field lineage -> Rule Specifications -> certification Expression -> Router: master record + steward queue for hard-rule failures | L-CDI-263 |
| Publish | counts per scope (expected masters vs written, certified, held, failed, issues) -> one manifest row; consumers read only committed publications | - |

Rules that mattered: scope is an in-out parameter (one region, a list or ALL; L-CDI-265), lineage comes from
`$CurrentTaskId` / `$CurrentRunId` (never hard-coded), the run start is the record version so re-runs replace, transaction
events can beat a stale attribute (the latest qualified sale event replaced nominal last-sale values), hierarchy gates hold
units whose parent relationship is unconfirmed, and the write path needs big batches and a bigger DTM heap
(L-CDI-262, L-AGENT-112). Bound warehouse memory per query and run full-scale backfills by scope group: one long full-scale
read died when other workloads exhausted the warehouse's memory.
