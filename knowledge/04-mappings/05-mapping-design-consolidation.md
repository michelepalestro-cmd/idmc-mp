# Mapping Design & Consolidation

**Answers:** Which expression idioms, cleanse formulas and transformation shapes work in CDI; how to case names without damaging them; SCD2, reject handling and DQ placement; how to audit task sprawl and consolidate many tasks into few mappings; what consolidation saves in time and jobs.

**Read when:** when designing a mapping, choosing where logic lives, or planning to fold copy tasks into generated mappings.

**Key rules:**
- As few mappings as possible: read each source once, write every consumer from one pipeline, keep deliberate parent → child chains (L-CDI-114, L-CDI-118).
- Every proven transformation can be generated headless, including Union, Rank, Sequence, Lookup, Masking, Rule Specification, Cleanse and Deduplicate (L-CDI-204).
- Plain `INITCAP` damages real names: use the per-word rule, and put the same rule in every writer of the field (L-CDI-104, L-CAI-086).
- Consolidation is the job-budget lever: one mapping per run replaces many task jobs; CAI calls and pushdown save none (L-IPU-042, L-CDI-170).
- Keep append-mode snapshot targets out of mappings that run per event (L-CDI-094).
- Keep at most about 5 warehouse readers per mapping on a small agent (L-CDI-129).

**Related:** [02 How Claude Builds Mappings Headless](02-how-claude-builds-mappings-headless.md) · [07 Performance, Concurrency & Job Caps](06-performance-concurrency-job-caps.md) · [08 Changing Pipelines Safely](07-changing-pipelines-safely.md) · [knowledge/08-data-quality](../08-data-quality/) · [Lessons: CDI](lessons.md)

**Last verified:** 2026-11-03

> **Summary.** Part A: the design patterns worth building: Informatica expression idioms (not SQL), proven cleanse formulas, Joiner/Router/Aggregator shapes that ran headless, SCD Type 2, reject handling and where data quality sits in a mapping.
> Part B: the consolidation doctrine, **as few mappings as possible**. One Copy Data task per table per layer (about 160 tasks and 10 taskflows) is an anti-pattern. It shows empty canvases, hides the logic from lineage and CLAIRE, pays about 20 s and one job per task, and makes lanes collide.
> Group by stage and dependency, read each source once and write every consumer from one pipeline, and keep deliberate chains intact. The plan shape was about 160 tasks → about 11 mappings and 10 taskflows → 3. A first build of 11 mappings replaced 40 tasks, parity-green.

---

## Part A: Design patterns

**Evidence classes on this page.** Rows marked *proven* ran in a live org (dated). Rows marked *reference* come from a third-party reference implementation (a CDC → SCD2 → star design over CDI + CDQ + CDGC). They are standard Informatica syntax and defensible designs, but they were **not live-probed** and are not vendor doctrine. Validate functions and load types in your org, because licence tiers and connectors differ.

### A1. The expression language is not SQL (reference; L-CDI-103)

| Need | Informatica expression | Note |
|---|---|---|
| Conditional / NVL | `IIF(ISNULL(x), 'INSERT', x)` | `IIF` is the ternary; `DECODE` is the switch. An empty string is not NULL: test both for required fields |
| Current time | `SYSTIMESTAMP` | Not `NOW` |
| Concatenate | `a \|\| ' ' \|\| b` | A NULL operand makes the result NULL: wrap volatile fields |
| Date arithmetic | `DATEADD(DAY, -1, $$LOAD_DATE)` | |
| Date surrogate key | `TO_NUMBER(TO_CHAR(d,'YYYYMMDD'))` | |
| Parameters | `$$LOAD_DATE`, `$$PIPELINE_RUN_ID` | `$$` = runtime parameter from a parameter set; `$` = system variable. No endpoint or upload format for parameter sets was captured |

**Proven cleanse formulas** (52 rows transformed, the changed values verified column by column, 2026-08-19; L-CDI-104):

| Field | Expression |
|---|---|
| Name (simple; damages real names, see below) | `INITCAP(LTRIM(RTRIM(REG_REPLACE(full_name,' +',' '))))` |
| Email | `LOWER(LTRIM(RTRIM(email)))` |
| Phone → E.164 | nested `IIF` over `REG_REPLACE(phone,'[^0-9]','')`: 10 digits → `'+1'\|\|d`; 11 digits starting with 1 → `'+'\|\|d`; else `''` |
| Canonical code | `DECODE(LOWER(TRIM(tier)),'gold','Gold','silver','Silver','bronze','Bronze','Unknown')` |
| Validity flag | `IIF(REG_MATCH(email_clean,'^[a-z0-9._%+-]+@[a-z0-9.-]+[.][a-z][a-z]+$'),'1','0')` |

**Casing person names without damaging them** (L-CDI-104, L-CAI-086). `INITCAP` lower-cases deliberate inner capitals (McDonald → Mcdonald, MacArthur → Macarthur) and capitalises particles (de la Cruz → De La Cruz), so a batch mapping using it fights any other writer that keeps them. The rule that worked, per word (delimiters: space, hyphen, straight and curly apostrophe):
- keep the typed word when it matches `^\p{Lu}\p{Ll}+(\p{Lu}\p{Ll}{2,}){1,2}$` (deliberate inner capitals; Unicode classes were accepted);
- keep a typed lower-case particle when it is neither the first nor the last word and the name has more than two words (`da das de del della der di do dos du la le van von den ter ten bin ibn al el`);
- otherwise `INITCAP` the word, so ALL CAPS and random case are still fixed.

Build it with VARIABLE ports evaluated in order before the output port: collapse whitespace, count words, extract word *i*, decide, join with `||`, and fall back to `INITCAP` for names longer than the number of word ports:

```text
v_nm = REG_REPLACE(REG_REPLACE(IIF(ISNULL(full_name),'',full_name),'\s+',' '),'^\s+|\s+$','')
v_n  = IIF(v_nm='',0,LENGTH(v_nm)-LENGTH(REPLACECHR(0,v_nm,' ',NULL))+1)
v_t2 = IIF(v_n<2,'',REG_EXTRACT(v_nm,'^(\S+ ){1}(\S+).*$',2))
v_o2 = IIF(v_t2='','',IIF(REG_MATCH(v_t2,'^\p{Lu}\p{Ll}+(\p{Lu}\p{Ll}{2,}){1,2}$'),v_t2,
       IIF(v_n>2 AND REG_MATCH(v_t2,'^(della|del|der|das|dos|den|da|de|di|do|du|la|le|van|von|ter|ten|bin|ibn|al|el)$'),v_t2,INITCAP(v_t2))))
full_name (OUTPUT) = IIF(v_n>8, INITCAP(v_nm), v_o1 || IIF(v_n>=2,' '||v_o2,'') ||...)
```

Traps: an unanchored alternation in `REG_MATCH` such as `(de|der|...)` takes the first branch for 'der' and then fails the whole-string match ('van der' came out 'van Der'): anchor every alternation and order it longest first. Test with names such as 'van der Berg', 'Ana María de la Cruz', "O'Neil-Smith". For addresses: collapse runs of spaces, title-case street and city only when the value was typed all lower-case (keeps 'NE', 'McKinney'), and `UPPER(TRIM)` the state. Bracketed tombstones such as `[erased]` get re-cased too, so match them case-insensitively downstream. Prove the rule with a scratch probe mapping that writes only a parity table, fed by a SQL source that UNIONs fixed test names with every live value, compare it with the other writers' rule in the warehouse, then swap it in (same GUID, OVERWRITE) and diff every column against a time-travel snapshot taken just before the swap (830/830 and 875/875 rows, 0 unintended changes).

Documented but not run headless: multi-format dates (`IIF(IS_DATE(s,'YYYY-MM-DD'), TO_DATE(s,'YYYY-MM-DD'), IIF(IS_DATE(s,'MM/DD/YYYY'), TO_DATE(s,'MM/DD/YYYY'), NULL))`); a USPS state `DECODE`; `IIF(REG_MATCH(zip,'^[0-9]{5}(-[0-9]{4})?$'), SUBSTR(zip,1,5), NULL)`.

**Port rules** (proven 2026-09-29). An Expression OUTPUT port cannot reference another OUTPUT port: put intermediate values in VARIABLE ports. An apostrophe inside a literal is `'...' || CHR(39) || '...'` (L-CDI-105).

### A2. Transformation shapes that ran headless

| Shape | How it was built | Rule |
|---|---|---|
| **Router** pass/fail | Groups `[["VALID","dq_status = 'VALID'"],...]`; the generator adds `DEFAULT1` | One pass, mutually exclusive groups; prefer it over two Filters |
| **Joiner** | `master`, `detail`, `cond` pairs, `join` NORMAL / MASTER_OUTER / DETAIL_OUTER / FULL_OUTER; a link field selection (`TmplNameRule`) picks the columns | **Never** let one source feed the master and (directly or downstream) the detail: the session hangs with no error. Same-pipeline branches need "Sorted Input" plus Sorters, or the import fails ("Choose sorted input for <JNR> to join data from the same source") (L-CDI-106) |
| **Aggregator** | `groupBy` plus aggregate expressions (`COUNT`, `SUM`…) | Fold several small marts that share a grain into one mapping |
| **Expression** | OUTPUT plus VARIABLE ports | See A1 |
| **Query source** | A warehouse SELECT as a source | Keeps heavy set logic inside the warehouse; counts as one reader |
| Filter, Sorter | Generated and run | — |
| Union, Rank (`RANKINDEX`), Sequence (`NEXTVAL`), Lookup (connected, and unconnected `:LKP.<name>`), Data Masking, Rule Specification, Cleanse, Deduplicate, Normalizer, mapplets, Update / Upsert / Delete / Data Driven targets | The generator (route 5); class shapes from the designer bundle and `GET /da/w3.imf/iclass/?infaToken=` ([02](02-how-claude-builds-mappings-headless.md) §7) | Copy referenced DQ assets into the org first; in a stock dedupe asset never map the business key into `Id` (L-CDI-204) |
| The multi-asset Data Quality transformation, a stand-alone Update Strategy | **Not yet built headless** | Rule Specification, Cleanse and Deduplicate transformations, or Data Driven targets, cover most uses |

Keep at most about 5 warehouse readers per mapping on a small shared agent (L-CDI-129), and split a big design into connected components.

### A3. SCD Type 2 in seven steps (reference; L-CDI-107)

1. Read the increment by run id (`PIPELINE_RUN_ID = $$PIPELINE_RUN_ID`), not by date, so a re-run is idempotent.
2. Look up the dimension `WHERE IS_CURRENT = TRUE` for the surrogate key, the stored hash and the start date. Without the predicate every version returns and rows multiply.
3. Expression: `NEW_HASH = MD5(<attributes in a fixed order>)`. Hash only attributes whose change should make a new version, never a load timestamp. Never reorder the fields: that invalidates every stored hash.
4. Filter: `ISNULL(LKP_SK) OR NEW_HASH != LKP_RECORD_HASH`.
5. Router into NEW and CHANGED.
6. Target A (UPDATE, key `SK = LKP_SK`): `EFF_END_DATE = DATEADD(DAY,-1,$$LOAD_DATE)`, `IS_CURRENT = FALSE`.
7. Target B (INSERT): `EFF_START_DATE = $$LOAD_DATE`, `EFF_END_DATE = NULL`, `IS_CURRENT = TRUE`, `RECORD_HASH = NEW_HASH`, the surrogate key from a sequence and the run id on the row.

Make expire-then-insert atomic: a failure between steps 6 and 7 leaves two current rows.

### A4. Never drop a row silently (reference; L-CDI-108)

- **Reject sink.** Each failed row goes to an ERROR table with the run id, source entity, business key, a reason of the form `CQ-002 | INVALID_EMAIL_FORMAT | EMAIL='<value>'`, and the **full raw record** (JSON), so it can be reprocessed.
- **Reject-rate breaker.** If rejects exceed a threshold (e.g. 10%), fail the quality step and abort the flow: the source contract changed.
- **Fail vs flag**, chosen per rule: a NULL business key rejects; an odd code may only flag.
- **Deduplicate** facts with a Lookup on the natural key plus `FIL ISNULL(LKP_SK)`, so a re-run never doubles rows.
- **Put domains in reference tables**, not hard-coded IN-lists.

### A5. Data quality inside a mapping

- **DQ measures, CDI acts.** Cleanse, match, parse and address rules run inside a CDI mapping on the Secure Agent. The target design for a DQ mapping is the org's rule specifications as transformations, then a Router pass/fail, then an Aggregator scorecard. Rule Specification, Cleanse and Deduplicate transformations are generated headless; the multi-asset Data Quality transformation is not yet (L-CDI-204). See [knowledge/08-data-quality](../08-data-quality/).
- **Label honestly.** Cleanse, dedup and DQ logic written as warehouse SQL inside mapping tasks is CDI SQL, not Cloud Data Quality. Say which steps are genuine CDQ assets (L-CDI-112).
- **Where CDQ steps run** (L-CDI-279, 2026-10-28): cleanse, deduplicate and decision transformations fail on the Hosted Agent with EP_13236 (the hosted server lacks the DQ engine libraries); rule specifications run there. Keep those steps in their own small mappings bound to a Secure Agent with the Data Quality service, and leave memory-heavy flows such as big aggregations on the hosted runtime (L-CDI-260).
- **What a Deduplicate outputs** (L-DQ-127, 2026-10-28): every incoming field passes through (no join back needed); `Out_RowId` and `Out_DriverId` arrive as the text `'1 - <SequenceId>'` (strip the prefix before joining); read the pair score from `Out_LinkScore` (`Out_DriverScore` is 1.0 on every row); with consolidation on, one extra row per cluster carries `Out_IsSurvivor = 'Y'` beside the members (`'N'`), so filter on it or counts double.
- **Golden-record pipeline shape:** a cleanse Expression → Lookup or rank-based dedupe (survivorship order, e.g. completeness desc, DQ score desc, created asc) → golden target → the reverse-ETL targets **in the same pipeline**, so one read feeds every consumer.
- **One rule in every writer.** Put the same cleanse rule in every target of the golden mapping, in the real-time CAI path and in the CRM sync; with two different rules the passes flip values back and forth (L-CAI-086, L-CDI-150). Check a format rule's output distribution, not only its DQ dimension: a 'phone E.164' dimension read 99% while the golden column held 10- and 11-digit strings with no '+'.
- **A corrected value must reach what the screens read.** A DQ-corrected name written back to the application database still showed wrong in web and mobile apps, which render the identity provider's token `name` claim taken at sign-in. List every copy the screens read (database rows, identity-provider profile and token claims, CRM, caches) before calling a write-back done; the write-back invariants are in [09](08-source-target-gotchas.md) §2.2 (L-MDM-074).
- **Match keys:** a surname + street-number key merged different people when the street number was blank. Fall back to a stricter key (e.g. surname + email) in that case. See the DQ domain for match rules.
- **Gate outbound writes** on DQ: push nothing to a CRM when this cycle's valid golden count falls below 80% of what the CRM already holds (L-CDI-091).

### A6. Layering, flow shape and placement of logic

- **Layers** (reference; L-CDI-109). RAW is append-only (an immutable audit that lets you reprocess), CURATED is modelled and mutable, and ERROR holds rejects. Stamp every RAW row with the run id, source file and load time **inside the ingest mapping**.
- **Flow shape** (reference; L-CDI-110). A master flow runs INGEST → QUALITY → CURATED, with CURATED sequential (dimensions before facts) and parallelism only inside a stage. State the error policy per scenario: ingest failure aborts all, a quality breach aborts, a curated failure aborts, and per-row rejects within threshold route and continue. Use one parameterized definition, not clones per date or environment.
- **Where logic lives** (L-CDI-112). All logic in IDMC makes rules visible in lineage and editable by non-SQL users, at a pushdown cost. Logic as warehouse SQL fits a headless build. Choose deliberately and write the choice down. With BigQuery sources and targets, full pushdown is settable, but on small multi-target mappings it was slower than agent mode because targets run serially: measure before switching ([02](02-how-claude-builds-mappings-headless.md) §9; L-CDI-203).
- **Design for a clean lineage path** (L-CDGC-229, 2026-10-26). An automated source-first, BI-last lineage check failed a two-mapping design three ways: a rules mapping that joined the source system's record again drew an edge that skipped the storage stage, a middle table read by a second mapping drew an edge backwards, and a parse mapping without rules showed no data-quality step. Rebuilt as one mapping per pipeline (storage read, parse, rule specifications, status, one target), both lineages passed. Carry metadata from the storage side (file name, modified time, checksum) instead of re-reading the system of record, and retire the old mappings from the catalog's scope ([Search, Lineage & Marketplace](../09-catalog-lineage/04-search-lineage-marketplace.md)).
- **One definition per metric** (L-CDI-113). When a CRM sync, an activation payload and an app API each computed "lifetime value", they gave three numbers. Define it once as a view with an explicit formula, and make every task read it.
- **Naming** (L-CDI-111): `EXP_` expression, `LKP_` lookup (also flags a round-trip hotspot), `FIL_` filter (pair each with a reject path), `RTR_` router, `JNR_` joiner, `AGG_` aggregator, `SRT_` sorter, `SRC_`/`TGT_` for sources and targets. Mapping `m_<x>`, task `mt_<x>`, taskflow `wf_<x>`, kept 1:1 and same-named. With a generator, the spec file is the reviewable artifact; the export IMF is the read-back.

---

## Part B: Consolidation, "as few mappings as possible"

### B1. The doctrine (L-CDI-114, 2026-09-29)

Never design one mapping task per table per layer. Group same-shaped loads into **one parameterized object**: a Dynamic Mapping Task with one job per table (v3 type `BATCH_MAPPING`, read and created by package headless; L-CDI-289), or one mapping with several pipelines. Read each source table **once** and write every consumer from the same pipeline. Show real transformations (Expression, Lookup, Joiner, Aggregator, Router, Rank, Rule Specification) instead of SQL strings, and keep heavy set logic in the warehouse: query sources, or full pushdown where it measures faster ([02](02-how-claude-builds-mappings-headless.md) §9).

### B2. Why per-table copy-data tasks are an anti-pattern

A generated pipeline reached **160 mapping tasks and 10 taskflows**, with 159 of the tasks on one Copy Data template and the logic in `customQuery` strings (L-CDI-115, 2026-09-29). What that cost:

| Cost | Evidence |
|---|---|
| Empty canvases | Every task opened as a two-box canvas; a demo showed nothing of the design |
| Invisible logic | Lineage stopped at table level. Mapping tasks are not catalog assets, and CLAIRE said "no information found" for task names |
| Fixed latency | About 20 s per task (DTM ~14 s + ~5 s dispatch): a 62-task lane took 21–24 min for about 53k rows (L-CDI-121) |
| Job budget | One job per task plus one per taskflow. Event lanes burned 17–21 jobs per event, and one org hit its 10,000 jobs/month cap (L-CDI-131) |
| Collisions | Subset taskflows shared tasks with the full taskflow: `REPO_17314`, quiet windows, mutual-exclusion code (L-CDI-078) |
| Sprawl | 46 unscheduled shadow copies, duplicate landing tasks and stray samples in `Default` inflated the design (L-CDI-148) |

### B3. The audit: find the sprawl before you design

1. **Inventory** every task: its template (`mappingId`), schedule (the **detail** GET; the list hides it), taskflow membership, reads (source object, or every `dataset.table` in its SQL with views expanded) and write (target). A read-only export package makes it easy to parse every task's JSON offline.
2. **Flag the patterns** (L-CDI-115):
   - land + raw as two tasks per table, where raw only casts to STRING (L-CDI-116);
   - two task families reading the same source tables on separate schedules (L-CDI-117);
   - subset lanes that are subsets of the full lane;
   - unscheduled shadow or parity copies;
   - SaaS record-id read-backs chained before child upserts (L-CDI-118);
   - tasks whose only purpose is a cast.
3. **Before calling a task an orphan**, check its task-level schedule, whether an app endpoint or view reads its output, and whether an orchestrator or host script starts it by id. Grep the orchestrator's baked plan and workflow files. One "orphan" had its own hourly schedule and fed an app API (L-CDI-146).
4. **Before calling a stale-looking task a bug**, check whether its target has become a **view**. A raw task in no taskflow looked like a stale-data bug, but its table had become a live view over the landing table, so the task was simply obsolete (L-CDI-147, 2026-09-29).

### B4. How to group

1. **Build the dependency map** (reads, writes and dependencies per task; the same DAG as in [07](06-performance-concurrency-job-caps.md)). A tool that groups tasks by (SQL vs copy, source kind, target kind) shows the candidates.
2. **Merge stages with no internal dependency first.** N parallel landing loads of the same shape become one Dynamic Mapping Task, or one multi-pipeline mapping that reads each table once and writes all its targets: typed landing, the STRING layer through an Expression, and a second warehouse.
3. **Merge by business entity next:** all staging and gold steps of one entity (cleanse → dedupe → golden → outbound) become one mapping with several targets.
4. **Keep deliberate chains intact.** A parent → child SaaS upsert order stays ordered: targets in load order inside one mapping, with external-ID relationship fields instead of read-back tasks (L-CDI-118).
5. **Split where the platform forces it:** at most about 5 warehouse readers per mapping on a small agent (L-CDI-129), and a separate mapping per target ecosystem so warehouse-internal mappings stay pushdown-eligible.
6. **Retire the cast-only layer.** Do the STRING projection in an Expression inside the ingest mapping, or as a view (L-CDI-116).
7. **Keep append-mode snapshot targets out of event mappings.** A daily evidence snapshot written with 'Write append' inherits the cadence of the mapping it is folded into: in a per-event lane every event appends another snapshot row. Keep such targets on their own scheduled task with the once-per-day guard (L-CDI-094), check every target's write disposition in the swap spec, and run the new mapping twice in a row: the second run must not change row counts (L-CDI-094).
8. **Read replicas, not sources, where CDC already lands them.** Ingest mappings that re-read the operational database in every lane cost 25-42 s and 3 jobs per lane run; reading the CDC tables in the warehouse removes them (L-CDI-203, L-IPU-042).
9. **Merge two existing mappings by transplant** when they run as a pair: copy the second mapping's transformations into the first's export, re-point `$$class` numbers by class name, give fresh ids, drop the middle target, and import OVERWRITE under the kept id ([02](02-how-claude-builds-mappings-headless.md) §5; L-CDI-278).
10. **One mapping over many sources needs a parameterized source query.** A task's `customQuery` edit is ignored on a fixed-source mapping, which left one generated build with 357 mappings for 354 tasks (L-CDI-284).

### B5. The plan shape (≈160 tasks → ≈11 mappings, 10 taskflows → 3)

| Target mapping (generic) | Transformations | Replaces |
|---|---|---|
| Ingest (Dynamic Mapping Task, one job per table; or 3 multi-pipeline ingest mappings split by reader count) | source read once → typed landing target + Expression → STRING raw target + second-warehouse target | the land, raw and second-warehouse landing tasks (14 + 10 + 12 in the audited design) |
| Golden record | cleanse Expression → Lookup/dedupe → golden target → reverse-ETL targets | the staging, curate and outbound tasks of the entity (5 in the first build) |
| Data quality | DQ transformation (or rule expressions) → Router pass/fail → Aggregator scorecard | the DQ result, match-pair, reconciliation, completeness and scorecard tasks (built as 2 mappings replacing 3 + 4) |
| Facts and marts | Joiners and Aggregators by grain | built as 4 mappings replacing 5 + 1 + 4 + 3 |
| Feeds | query source → feed targets | 2 |
| SaaS sync | one mapping with one flow per object, in parent → child order, each an Upsert on an external id (nulls not sent, non-bulk, fields mapped by name), source SQL copied verbatim from the old tasks | the 11-task upsert and read-back chain; built headless with no UI seed (L-CDI-170) |
| File ingest | validation Expression → Router: valid → ready + post; invalid → quarantine | the file-lane tasks (3 of 4 in the first build; the posting task waited for a proven PostgreSQL target) |

Taskflows go from 10 to 3: batch, a second application and files (2 once the second application left the platform).

**First build** (2026-09-29; L-CDI-119, L-CDI-120). 11 mappings, parity-green and idempotent, replaced **40** tasks and wrote only to a parity dataset until the swap gate. Each mapping ran in 28–87 s, while each task it replaced ran in 8–60 s, about 20 s of it fixed. One ingest mapping (85 s) replaced 6 raw tasks of 34–38 s each. Fewer tasks also meant fewer jobs (40 → 11 per cycle for that part) and a shorter critical path.

**Steady state after the swap** (L-CDI-119):

| Lane | Before | After |
|---|---|---|
| per-record event lane | 16 tasks, 98-108 s | 7 jobs, average 96 s (fastest 82 s) |
| activity event lane | 19 tasks, ~240-267 s staged | 11 jobs, average 159 s |
| full refresh | 62 tasks, ~20 min | 23 jobs, 258-358 s |
| CRM sync step | 11 serial upsert tasks | 1 mapping, 85-92 s for ~3,100 rows to 11 objects, ~30-40 counted CRM API calls |

A 59-transformation golden-record mapping with 11 targets ran a median 65 s (27 of 27 successful); ingest mappings that read each source once and write several targets ran 24-41 s; single-target marts 8-27 s. Each step was accepted only with parity 0/0 against the old outputs plus an independent check, and the replaced tasks were deleted only after 24 h green (L-CDI-141, L-CDI-142). Without the 1 s BigQuery writer poll interval the consolidated mappings were slower than the tasks they replaced (L-CDI-200). A host resize from 4 to 8 vCPU the same day made the same mappings 1.6-3x faster, so the two effects are not separable.

**What consolidation saves in jobs** (L-IPU-042, L-CDI-170, L-CAI-038). Each mapping run is one job however many targets it writes, so jobs per run fall with the task count: 63 → 24 per full-lane run, 16 → 7 per event. Folding 11 CRM upsert tasks into one mapping removed about 175 jobs a day (of about 920). Reading CDC replicas instead of re-ingesting saved 3 jobs per lane run. What did **not** save jobs: moving work between CAI and another integration layer (CAI calls are not jobs) and pushdown (still one job per run). Budgeting the cap itself: [07](06-performance-concurrency-job-caps.md) §7.

**How it was swapped in:** side by side, gated. See [08 Changing Pipelines Safely](07-changing-pipelines-safely.md).

### B6. The anti-pattern list (from the audit and a migration)

1. One task per table per layer on the Copy Data template, with the logic in `customQuery` strings.
2. Land and raw as two tasks per table, where raw only casts to STRING.
3. The same source table read twice by two task families on separate schedules.
4. Shadow and parity copies never removed, plus duplicate landing tasks writing an unused dataset, plus a stray sample in `Default`.
5. Subset taskflows that share tasks with the full taskflow (`REPO_17314`, quiet windows, mutual-exclusion logic).
6. Round-trip read-backs of SaaS record ids before child upserts (an 11-task sequential chain became the DAG floor).
7. Task-level schedules that list calls do not show; one was missed at cutover.
8. Hard-coded ids in app code and builders (72 ids baked into one controller image); builders cloning schedules from another app's schedule; the same builder in two or three directories.
9. Event lanes that burn 16–20 jobs per user event, until the org's monthly cap is hit.
10. Secrets in design objects: an app connection with `encrypted="false"` carried an OAuth secret into every export package (see [knowledge/07-app-integration](../07-app-integration/)).
11. A risky target option: a posting task with `truncateTarget=true` on an accounting table (L-CDI-169).
12. Anonymous public processes writing to a SaaS org (accepted for a demo; flagged).
13. The "obsolete, not a bug" trap: check whether the object a task writes is still a table (L-CDI-147).
