# CLAIRE GPT: prompting rules and patterns

**Answers:** How do I word a CLAIRE GPT prompt so it finds the right asset and returns warehouse-exact numbers? Which
question shapes pass and which fail? What can CLAIRE GPT change or persist? Why does "Query the data" fail, stop at 100
rows or answer from the wrong asset? How do I turn CLAIRE GPT on and rehearse a demo?

**Read when:** writing, rehearsing or automating CLAIRE GPT prompts; a CLAIRE answer is wrong, empty, truncated or says
the data service connection is unavailable; deciding whether CLAIRE can act on data.

**Key rules:**
- One new conversation per independent question; name the platform, the object type and the bare name ("the BigQuery
  table T"); never type `@`, never write `dataset.table` (L-MCP-054, L-MCP-055, L-MCP-056).
- For "Query the data" do **not** add "in the <dataset> dataset": CLAIRE can search for the dataset as an asset and
  answer from a same-named view. Pin a dataset only for catalog and DQ-score questions, and check the asset that ran in
  Show Code (L-MCP-122).
- Ask a count and its business impact in **one** prompt; a separate impact follow-up drifts into product documentation
  (L-MCP-122).
- Every generated SQL ends in `LIMIT 100`: ask for counts, aggregates or a top-N of at most 100 (L-MCP-114).
- CLAIRE GPT authors, it does not act: it persists DQ rule specifications (plus dictionaries) and accepted rule
  occurrences, never data, pipelines or tool calls (section 10) (L-MCP-089).
- Never type while "Publish Rules / Don't Publish Rules" is showing, and press Send after every plan-button click
  (L-MCP-096, L-MCP-079).
- "Query the data" runs through the Data Gateway on a Secure Agent: keep that agent up. Pinned conversations drop query
  results, so analytic answers must run live (L-AGENT-051, L-MCP-122).

**Related:** [06 Use Cases Ranked](06-claire-gpt-use-cases-ranked-for-retail.md) ·
[01 Managed MCP Servers](01-managed-mcp-servers-catalog-access.md) ·
[04 Agent-Style MCP & Custom Shims](04-agent-style-mcp-async-orchestration-custom-shims.md) ·
[DQ Scorecards](../08-data-quality/04-dq-scorecards-warehouse-pattern-and-data-profiling-scorecards.md) ·
[Lessons: CLAIRE & MCP](lessons.md)

**Last verified:** 2026-11-03

> **Summary.** CLAIRE GPT is the conversational UI over an org's CDGC catalog: glossary, classifications (PII), lineage
> and impact. It also runs NL-to-SQL ("Query the data") on cataloged **warehouse** tables through a Secure Agent's Data
> Gateway. It lives on its own hosts (`claire-gpt.<domain>`); entitlement shows in EffectiveLicenses, and the proof is a
> live chat answer (L-MCP-050). There is no public REST chat API, but the managed `orchestrate` and `data_explore` MCP
> tools answer the same questions headless (L-MCP-111). It is **nondeterministic**: rehearse every prompt, allow
> 30-200 s per answer, re-ask after about 6 minutes of "Mapping identified concepts...", and never rescan a source within
> about 40 minutes of use. Catalog preparation and lineage set-up:
> [Catalog & Governance (CDGC)](../09-catalog-lineage/); gateway and agent:
> [Secure Agent & Connections](../02-secure-agent/).

---

## 1. What CLAIRE GPT is (and is not)

- **CLAIRE vs CLAIRE GPT.** CLAIRE is Informatica's ML auto-classification, part of the catalog. CLAIRE GPT is the
  generative add-on, entitled separately.
- **Where it lives (L-MCP-050, L-MCP-051).**
  - The chat UI ("Agentic Data Management") is at `https://claire-gpt.<domain>.informaticacloud.com`.
  - A conversation API was observed behind it on `claire-gpt-api.<domain>`, under
    `.../claire-conversation-session/api/v2/conversations`. It is internal and undocumented; a live query returned HTTP
    201.
  - Probes of `/data360/claire-gpt/*`, `/copilot/*` and `/ai/*` on `idmc-api.<domain>` all return 404: wrong host, not
    "not entitled". A 32-path sweep of `/data360/clairegpt/*` also 404ed, and `<pod>-clairegpt` / `<pod>-ai` had no DNS
    on one pod.
- **Entitlement check.**
  - The v3 login `products[]` list can show only "Integration Cloud" while CLAIRE GPT works.
  - Look instead at the identity-service login's **EffectiveLicenses** (`CLAIRE GPT`, `clairegpt.core`,
    `ai.agent.engineering.designer`), its `effectiveRoles` ("CLAIRE GPT User") and its `feature.clairegpt.*` flags.
  - The proof is one live question answered in the UI.
  - Engine-level evidence (no agentic engine on the agents) conflicted with licence evidence in July. Reconcile per org
    before saying "not entitled".
- **Roles.** The user needs the **CLAIRE GPT User** role. A login doing CDI, CAI, CDQ, CDGC and CLAIRE needed Admin,
  Designer, Governance Administrator and CLAIRE GPT User (L-MCP-068).
- **Turn it on (documented by the vendor, not exercised: the test orgs already had it on).**
  1. The org holds the IDMC licence (Administrator > Licenses).
  2. A runtime environment runs the services CLAIRE tasks need; for "Query the data" that is the Data Gateway on a
     Secure Agent group (section 6).
  3. Users hold **CLAIRE GPT User** (plus Designer to open and run generated mappings).
  4. An org administrator enables Administrator > Settings > **Enable CLAIRE Generative AI Services**, or clicks
     "Yes, I agree" in the "Welcome to CLAIRE GPT!" consent dialog, which ticks the same setting. Background
     provisioning for every user takes several minutes; other services stay usable meanwhile.

  The same setting gates the catalog: **Create a Rule**, when configuring a technical rule reference for a DQ rule
  template or occurrence in Data Governance and Catalog, appears only while it is on. When CLAIRE GPT or "Create a Rule"
  is missing in a new org, check this setting before suspecting entitlement.
- **What it can change:** rule specifications, dictionaries and accepted rule occurrences only; see section 10.
- **Cost (documented, L-MCP-116).** 50 IPU per 1,000 natural-language queries, shown in the Metering console. A vendor
  promotion makes design-time CLAIRE use (chat, copilots, agents, headless features) free for eligible subscriptions
  until 2027-01-31; runtime work CLAIRE triggers (profiling, DQ runs, generated mappings when run) bills its own meters.
- **Models and retention (documented, L-MCP-117).** Azure OpenAI and Anthropic Claude through Amazon Bedrock, privately
  deployed per region. Conversations go inactive after 180 days and are deleted after 13 months.
- **Which agents ship (documented, L-MCP-118).** Discovery, Data Quality, Data Integration (ELT) and Product Help agents
  and headless CLAIRE over MCP are GA; the Product Experience agent is preview; the Data Lineage, Data Ingestion,
  Modernization, Metadata Enrichment and data-steward agents are announced or roadmap.
- **Skills it exposes:**
  - discovery: multi-step reasoning with grounded "Technical Assets" cards;
  - glossary answers;
  - PII and classification lookups;
  - lineage and impact, with a clickable LINEAGE card;
  - NL-to-SQL with **Show Code** and charts;
  - Data Integration inventory and mapping explanations (L-MCP-093);
  - MDM business entities with match and survivorship rules, and Data Marketplace collections (L-MCP-113);
  - DQ rule generation, recommendation, diagnosis and file cleansing;
  - executive summaries of a table;
  - Informatica product-documentation answers;
  - "generate a mapping", which lives in the Data Integration designer canvas, not headless (L-MCP-052).

---

## 2. What it answers reliably, and what it does not (L-MCP-091, about 260 runs)

Single-shot pass rates were 54-64% per test lane, and the same wording can swing between pass and fail, so these are
tendencies: rehearse every prompt (§7). Every data answer that actually ran matched the warehouse to the cent.

| Works (passed repeatedly) | Fails or is unreliable |
|---|---|
| Glossary domains and terms: "What business terms are in the... glossary domain?"; "What does the business term X mean?"; terms linked to a table | **DQ scores or profiles of catalog assets** when no DQ rule occurrences are defined, run and published in CDGC → "No Data Quality information is currently available" |
| **PII / personal-data columns** of a named table ("List the columns of the SYSTEM table TABLE and say which of them contain personal data.") | Rule recommendation that names only the table pairs repository rules with the wrong columns (L-MCP-086); recommendation **only matches rules already in the repository**, so a new control gets "No matching data quality rules" (L-MCP-098) |
| **Catalog-wide classification search**: "Which columns in the catalog are classified as CLASSIFICATION?" (L-MCP-092) | "Which tables contain e-mail addresses?" and "datasets with sensitive data elements in the SYSTEM system" |
| **View-level lineage and impact**: downstream views of a table or view, upstream lineage through views (several hops, LINEAGE card) (L-MCP-107). **Job-level and SaaS hops** once the integration lineage is set up (an IICS source scanned with Lineage Discovery, its references MERGEd, curated edges for the hops no scanner draws): 4 upstream hops through a mapping task and a curated Salesforce edge in 75 s (L-MCP-128, 2026-10-27) | **Job-level lineage for custom-query tasks** ("0 upstream assets" even after auto-accepted assignments, L-CDGC-148); impact questions on a table no current mapping writes ('Lineage is not created', L-MCP-128) |
| **NL-to-SQL on one warehouse asset** ending in "... Query the data." (group-bys, buckets, window functions, outliers, text-to-number casts; a chart, plus Show Code) | **Cross-table joins** (0 of 4): only one asset stays in scope (L-MCP-100). **PostgreSQL data queries** are unsupported by design (L-MCP-061, L-MCP-114) |
| An **executive brief** or **trust verdict** of a named table; **comparing** two tables or a table and its view (exact column diff) | **Discovery by business question** without a table name (1 of 7, L-MCP-103); named-table search flakes about 1 in 6 ("not found in the limited set of 25 results") |
| **Explain a mapping** in business terms by name, with "in the FOLDER folder" when variants exist; list projects, folders and the mappings in a folder (L-MCP-093) | **Mapping tasks** by name or "which mapping tasks write to X"; mapping or job lineage |
| **MDM**: business entities, match and survivorship rules; **Data Marketplace**: never-requested collections, collection overview (7 of 7, L-MCP-113) | **Data dictionary generation** (invents columns), "terms with no linked assets" and governance counts (wrong and inconsistent) (L-MCP-106) |
| **Product how-to**, also about the asset found earlier in the same conversation (5 of 5, L-MCP-094) | "Show me the SQL" / "Generate SQL": refused; use Show Code (L-MCP-102) |
| **DQ score, low-score reason and fix-first** with "Use only the scores in the catalog" (5 of 5 UI, 3 of 3 MCP, L-MCP-095) | "Show the tables that have no data quality scores" passed 3 of 5; "Which SYSTEM tables have no data quality scores?" does not miss (L-MCP-087) |
| **Rules from a policy file** or one sentence (generated and tested, duplicates skipped); cleaning an attached file; filtered file profiling (L-MCP-099) | "Create a mapping..." gives an **in-chat proposal only**, or "Unable to identify all assets" for a new target (L-MCP-108); generated-code self-tests need agent Python (L-MCP-109) |
| A **numbered multi-intent catalog prompt** (find, PII, lineage, terms: 3 of 3, L-MCP-105); chained analytics when every turn names its asset (L-MCP-104) | A numbered multi-intent **analytics** prompt (0 of 1); **dotted names** (`dataset.table`); naming a **catalog source** in the prompt |
| Stakeholders or certification answered honestly ("not provided"); suggesting glossary terms for columns without creating them | A written narrative over multi-row results: it describes only the first ~5 rows (L-MCP-101) |

---

## 3. Prompting rules

1. **Start a new conversation for every independent prompt** (L-MCP-054). Context from an earlier question skews the
   next one. A deliberate chain is fine when **every turn names its asset** (L-MCP-104); "Clear conversation memory"
   resets the context and keeps the history.
2. **Never type `@`** (L-MCP-055). It opens the mention picker and the prompt is never sent, so e-mail addresses
   cannot appear in prompts.
3. **Name the system, the object type and the bare name** (L-MCP-056): "the BigQuery table T" or "the BigQuery view V".
   `dataset.table` is not resolved. Pin a dataset ("in the D dataset") only for catalog and DQ-score questions: in a
   "Query the data" prompt CLAIRE can search for the dataset name as an asset ("the asset D is not found in the limited
   set of 25 results") and then answer from another asset that shares the bare name (a view instead of the table), with
   plausible but different numbers. Answer "table or view?" with "The Table" or "The View", and confirm in **Show Code**
   which fully qualified name ran (L-MCP-122).
4. **Business names must be linked to technical names** (L-MCP-056). A business phrase that differs from the object's
   technical name (for example a SaaS custom object with a legacy prefix) is not found unless a **glossary term links
   them**.
5. **Anchor on the glossary** (L-MCP-057). "The business term X" or "in the BUSINESS NAME..." keeps CLAIRE in your
   catalog: 18 of 18 such questions were answered from the org glossary. Generic phrasing ("How is net revenue
   calculated?") is routed to Informatica product documentation.
6. **Say "Query the data."** in an NL-to-SQL question, on a **warehouse** table or view. The query runs through the
   org's runtime environment (§6). If the answer must carry business meaning, put the impact in the **same** prompt:
   "How many ENTITIES in the WAREHOUSE table TABLE have CONDITION1, and how many have CONDITION2? Query the data and
   explain the business impact on PROCESS." passed 3 of 3 with warehouse-exact counts and a grounded impact paragraph. A
   separate follow-up ("What is the business impact of this for PROCESS, and what should we fix first?") passed only
   2 of 4 to 2 of 5: without a data query in the turn it is routed to the Product Help agent and answers "No relevant
   information was found in the product documentation", or answers from vendor product docs instead of the numbers just
   computed. "Based on these numbers, explain the business impact..." fares better but is still a second hop, and a
   statement-style prompt ("Phone numbers in TABLE are not stored in...") went to the docs (L-MCP-122,
   L-MCP-122).
7. **Write plain ASCII prose.** Keep punctuation simple. Angle brackets (`<`, `>`, `->`) are rejected by the CLAIRE DQ
   agent's validator (`-32602`), so avoid them in any CLAIRE prompt.
8. **Allow 50-110 s per answer.** Narrate the "Reasoning" steps meanwhile. A harness must wait until the busy text
   (with its trailing "...") disappears, not for a fixed 60 s (L-MCP-063).
9. **Be specific about the asset, the entity and the action.** A vague prompt comes back as a clarifying question
   ("Table or View?", "which asset?"). Answer it (for example "1"), or rephrase with an explicit anchor.
10. **Do not ask for what is not cataloged.** CLAIRE sees only cataloged sources (L-MCP-043). Assets appear only after
    the catalog index catches up (§5).
11. **Name the columns when you ask for rule recommendations** (L-MCP-086). "…for the C1, C2 and C3 columns of the
    SYSTEM table TABLE" makes them the critical data elements; naming only the table let CLAIRE pair a ZIP rule with an id
    column. Read the "Recommended Data Quality Rules" card before you type "Accept all the recommended rules".
12. **Press Send after every click** on a plan button, "Publish Rules" or a suggestion chip: the click only fills the
    message box (L-MCP-079).
13. **Never send free text while "Publish Rules / Don't Publish Rules" is showing** (L-MCP-096). CLAIRE took
    a typed follow-up as consent and published the rule. Click "Don't Publish Rules" (plus Send) first, or end the
    conversation. A browser harness needs a publish guard (L-UI-030).
14. **Rule generation is not side-effect-free.** The "Generate Dictionaries" step saves missing dictionaries to CDQ
    before any Publish (L-MCP-097). List DICTIONARY objects afterwards.
15. **Recommend for existing rules, generate for new controls** (L-MCP-098). Recommendation only matches rules already in
    the repository. For a new check (a positive amount, a range, a value list, no future dates), generate it from a
    sentence that names the system, table and column, or from a policy file.
16. **Start a policy-file prompt with "This file is a data quality policy with one rule per line."** (L-MCP-099). Without
    it, one run in three profiled the file as data and found no rules.
17. **One asset per data question** (L-MCP-100). Joins fail: only one asset stays in scope. Pre-join in a cataloged view.
18. **Trust the chart or table, not the narrative** (L-MCP-101). The "Analysis & Insights" text reads only the first ~5
    rows of a long result. Put the chart type in the question, and name the filter and definition columns (test flag,
    activity date, kind) so CLAIRE does not guess; exclude placeholder values explicitly.
19. **Never ask for the SQL in chat** (L-MCP-102). "Show me the SQL" and "generate SQL" are refused; ask with
    "Query the data." and open **Show Code**.
20. **Always name the asset** (L-MCP-103). Discovery by business question without a table name passed about 1 in 7.
    Named-table search still flakes about 1 in 6 ("not found in the limited set of 25 results"): re-ask the same prompt
    in a **new conversation**, and in a chain re-name the asset in the follow-up.
21. **Use a numbered multi-intent prompt for catalog tasks only** (L-MCP-105). Find, PII, lineage and terms in one
    numbered prompt passed 3 of 3; a numbered analytics prompt failed at discovery.
22. **Do not demo the hallucination-prone asks** (L-MCP-106): data dictionary generation, "terms with no linked
    assets", governance counts and percentages, marketplace-availability claims. Review generated cleansing logic
    against the data.
23. **Re-ask after a long hang** (L-MCP-110). Runs stuck on "Mapping identified concepts..." or "Generating queries..."
    ended at about 405 s or with a CLAIRE timeout. Stop at about 6 minutes and re-ask in a new conversation.
24. **Expect generated-code self-tests to fail** unless Python is enabled for the agent's data gateway: answer "Proceed
    without testing" plus Send (L-MCP-109).
25. **Ask for aggregates, not lists** (L-MCP-114). Every generated query ends in `LIMIT 100` (§6), with no
    truncation warning in the narrative. Ask for counts, sums or an explicit top-N of at most 100; for a full list, copy
    the SQL from Show Code, drop the `LIMIT` and run it in the warehouse or a mapping.
26. **Re-ask a transient connection error** (L-MCP-122). "Connection issue with the WAREHOUSE source system"
    in the middle of a chain was transient: re-ask the same turn. "The underlying data service connection is currently
    unavailable" is not transient: the Data Gateway's agent is down (§6).

---

## 4. Prompt shapes that passed (templates; fill the placeholders)

Order a set by the question a stakeholder asks next: *what does it mean → is it safe → can I trust it → what breaks if it
changes → is it good → what is it worth → brief me*. Each shape below passed repeatedly (answers in 30-200 s, a new
conversation each time unless it is a chain marked →) (L-MCP-059, L-MCP-091). A ranked list of these shapes as retail
use cases is in [06](06-claire-gpt-use-cases-ranked-for-retail.md).

| Stage | Shape |
|---|---|
| Shared language | `What business terms are in the DOMAIN glossary domain?` |
| A KPI explained | `What does the business term TERM mean and where does its data come from?` |
| Privacy | `Which columns in the SYSTEM table TABLE contain personal data?` (with no classifications in the catalog it falls back to column names, so classify first; a mid-answer 'Looks like CLAIRE GPT encountered an error' line is noise when the answer completes, L-MCP-129) |
| Trust (lineage) | `Show the upstream lineage of the table TABLE`, then click the LINEAGE card. Answers through views; job-loaded tables answer once the integration lineage is set up (L-MCP-107, L-MCP-128) |
| Change impact | `What is the downstream impact if the table TABLE changes? List the affected jobs and SAAS objects.` (view level only until job lineage exists) |
| SaaS reach | `Which SAAS objects are loaded from the WAREHOUSE table TABLE?` (passed only where job and SaaS lineage were cataloged; 0 of 1 without, L-MCP-107) |
| Data quality | `Which data quality checks fail in the WAREHOUSE view DQVIEW? Query the data and explain the business risk of each failure.` |
| DQ summary (with a chart) | `How is the data quality of our ENTITY data? Query the WAREHOUSE view DQVIEW and show the pass rate of every check that has failures.` |
| Ask the data | `Who are the top 10 ENTITIES by MEASURE in the WAREHOUSE table TABLE? Query the data.` |
| Count + business impact (one prompt) | `How many ENTITIES in the WAREHOUSE table TABLE have CONDITION1, and how many have CONDITION2? Query the data and explain the business impact on PROCESS.` (3 of 3; never ask the impact as a separate turn, L-MCP-122) |
| Distribution | `How many ENTITIES are there per ATTRIBUTE in the WAREHOUSE table TABLE, excluding test accounts? Query the data.` |
| Trend | `What is the monthly MEASURE trend in the WAREHOUSE table TABLE? Query the data and show a line chart.` |
| Term to table | `Which business terms are linked to the SYSTEM table TABLE?` |
| Executive brief | `Summarize the WAREHOUSE table TABLE for a business executive: what it contains, where it comes from, who uses it and how sensitive it is.` |
| Profile-style | `Show data distributions for TABLE` / `Analyze data completeness of TABLE`. CLAIRE first asks "Table or View?". |
| Blind spots | `Which SYSTEM tables have no data quality scores?` (5 of 5; the generic "Show the tables that have no data quality scores" passed 3 of 5) (L-MCP-087) |
| Trust verdict | `I want to use the WAREHOUSE table TABLE for reporting to the CEO. Assess its metadata completeness, data quality and lineage, and tell me whether I can trust it.` |
| DQ score | `What is the data quality score of the WAREHOUSE table TABLE, and which rules are applied to it?` (needs scored rule instances, L-DQ-097) |
| Rules from a policy file | attach a plain-text policy (one rule per line), then `This file is a data quality policy with one rule per line. Generate data quality rules from this file.`; proceed + Send; at the Publish prompt click Publish Rules + Send only if you mean it, and type nothing else (L-MCP-099, L-MCP-096) |
| One rule from a sentence | `Create a data quality rule that checks that the COLUMN column in the WAREHOUSE table TABLE is a valid FORMAT.` (L-MCP-079) |
| Recommend and accept | `Recommend data quality rules for the C1, C2 and C3 columns of the SYSTEM table TABLE.`, proceed + Send, check the card, then type `Accept all the recommended rules` (L-MCP-086; existing repository rules only, L-MCP-098) |
| Clean a file | attach the file, then `Clean this file: standardize the names, emails and phone numbers, and flag the records you could not fix.`; proceed + Send, later "Proceed without testing" + Send (L-MCP-089, L-MCP-109) |
| Explain a mapping | `Explain in business terms what the mapping MAPPING in the FOLDER folder does, step by step.` (L-MCP-093) |
| Integration inventory | `List all projects and folders in Data Integration.` / `Which mappings are in the FOLDER folder?` (4 of 4) |
| Catalog-wide PII sweep | `Which columns in the catalog are classified as CLASSIFICATION?` (use the classification name the catalog shows, L-MCP-092) |
| Per-table PII (stabler wording) | `List the columns of the SYSTEM table TABLE and say which of them contain personal data.` |
| Governance dossier in one prompt | `1. Find the WAREHOUSE table TABLE. 2. List its personal data columns. 3. Show its downstream lineage. 4. List the business terms linked to it.` (3 of 3, about 75 s, L-MCP-105) |
| Fix first (grounded) | `Which rule has the lowest score on the WAREHOUSE table TABLE, and what should we fix first? Use only the scores in the catalog.` (L-MCP-095) |
| Low-score diagnosis | `What could be the reason for the low data quality score of the WAREHOUSE table TABLE?` |
| Help about an asset | `Find the WAREHOUSE table TABLE.`, then in the same conversation `How do I add data quality rules to this table?` (L-MCP-094) |
| Compare | `Compare the SYSTEM table TABLE with the WAREHOUSE table TABLE2.` / `What is the difference between the WAREHOUSE table TABLE and the view TABLE?` |
| MDM | `Show all business entities in Customer 360.` / `What are the match and survivorship rules of the Person business entity?` (L-MCP-113) |
| Marketplace | `What data collections have never been requested in Data Marketplace?` / `Show an overview of the data collection COLLECTION.` |
| Segmentation | `Segment the ENTITIES in the WAREHOUSE view VIEW into high, medium and low value: high is MEASURE over X, medium is Y to X, low is under Y. Exclude test accounts. Count the ENTITIES and total MEASURE per segment. Query the data.` (3 of 3) |
| Outliers | `Are there any unusually large transactions in the WAREHOUSE table TABLE? Query the data, flag amounts more than 3 standard deviations above the mean, and list the outliers.` |
| Ratio per group | `What is the recovered revenue versus the lost revenue per GROUP in the WAREHOUSE view VIEW? Query the data.` → `Which GROUP has the highest share of lost revenue? Calculate lost revenue as a percentage of recovered plus lost revenue.` (3 of 3) |
| DQ triage chain | `Which data quality checks fail in the WAREHOUSE view DQVIEW? Query the data.` → `Show the failure rate of each failing check as a bar chart.` → `Where does the data in DQVIEW come from? Show its upstream lineage.` → `Write a short data quality status update for the Chief Data Officer covering the numbers, the root sources and the top 3 fixes.` (3 of 3, L-MCP-104) |
| Refine in a chain | after a top-N answer: `Now show only SEGMENT customers.` → `Show that as a bar chart.` |

Replace the UPPERCASE words with real names: `SYSTEM` and `WAREHOUSE` are the platform names (for example
"Postgres", "BigQuery"), `SAAS` is the SaaS system, and `TABLE`, `DQVIEW` and `DATASET` are bare object names.

Several names exist as both a table and a view: CLAIRE then asks "table or view?". Answer "The Table" or "The View"
(about 35 s extra). When many warehouse assets share one name (for example six tables in different datasets plus a
view), "Query the data" can stop with "unable to process the query... missing scope... confirm which dataset": answer
"The Table" to its question (naming the dataset worked after that question too), and remove or rename stale same-name
copies in other datasets (L-CDGC-090, L-MCP-122).

**Stability tip (catalog and DQ-score questions only).** Pinning the dataset name ("in the DATASET dataset") stabilised a
catalog DQ question whose unpinned wording once drifted into a DQ-rule-generation plan. Do not carry the pin into "Query
the data" prompts (rule 3): there it sent one of two runs to a same-named view (L-MCP-122).

---

## 5. Prepare the catalog so CLAIRE answers well

1. **Give the glossary business context (L-MCP-066).**
   - Write a glossary **domain** whose description states the company, what it does and its goal.
   - Add a term for every business concept, including one term that explains legacy technical names.
   - Link each term to its physical assets: tables, columns, SaaS objects.
   - Write curated descriptions on catalog sources, databases and schemas, **and** in the source system itself (for
     example warehouse dataset and view descriptions), so rescans carry them.
   - Script it idempotently: a term-id registry, and an undo JSON before every change. Then test with a fixed question
     set (18/18 passed after this work).
   - The glossary and link REST routes are in [Catalog & Governance (CDGC)](../09-catalog-lineage/).
2. **Purge duplicate legacy sources (L-MCP-064).** When the catalog still holds old sources with the same
   table names (a second copy of a table, stale mart copies), CLAIRE picks the wrong asset for PII, lineage and impact
   questions. Purge the legacy sources, **include-filter** the live ones (with Metadata Change Option = Delete before a
   rescan), then retest. In one test, run 1 was confused and run 2, after the purge, passed.
3. **Mind the index lag (L-MCP-062).** New or rescanned sources become answerable only after hours: assets created at
   06:23 became answerable around 09:00, and assets created at 19:00 were still missing at 20:30. About 30 minutes after
   fresh scans (Lineage Discovery and auto-accept COMPLETED), glossary and PII questions already passed while lineage and
   NL-to-SQL still failed, probably index lag. **Gate any switch that depends on CLAIRE on a passing retest.**
4. **Never rescan shortly before use (L-MCP-063).** While a catalog scan on a source is RUNNING, CLAIRE answers "no
   relevant information" for that source's assets. Do not trigger rescans within ~40 minutes of a demo.
5. **Publish DQ if you want DQ answers.** Catalog DQ answers need rule occurrences defined, run and published in CDGC
   (they can be created over REST, L-CDGC-161, as well as by recommend-and-accept).
   Otherwise, catalog a **DQ results view** in the warehouse and ask CLAIRE to query it
   ([DQ Scorecards](../08-data-quality/04-dq-scorecards-warehouse-pattern-and-data-profiling-scorecards.md)).
6. **Catalog the job layer for lineage.** Mapping-task lineage appears only when a Data Integration (IICS) catalog source
   is scanned with Lineage Discovery and its connection assignments are resolved (auto-accepted in the scan, or stitched
   headless with a `connectionAssignment` MERGE: L-CDGC-140, L-CDGC-159). Classic tasks still cannot be named in
   prompts.

---

## 6. "Query the data" depends on a Secure Agent (L-MCP-060)

- NL-to-SQL executes through a **runtime environment of the org** (a Secure Agent's data gateway). Stopping that agent
  breaks the "Query the data" prompts, even when no data jobs remain on it. Lineage and glossary prompts keep working.
  Keep the agent up for a demo, and do not retire it until CLAIRE runs elsewhere. On an org without the Data Gateway
  licence package the service never appears (not even as a service to select), so "Query the data" cannot run there
  until the vendor adds the package (L-AGENT-097).
- The data gateway parses the warehouse connection's private key **more strictly than CDI**. On one pod, a stripped
  base64 key that CDI accepted gave "Invalid PKCS#8 data" in the gateway, and the full PEM with literal `\n` escapes
  worked. Key formats are pod- and engine-dependent: test CDI, the ingestion driver and the gateway
  separately ([Secure Agent & Connections](../02-secure-agent/)).
- Data exploration ran on **BigQuery** (row counts, group-bys, joins) and not on **PostgreSQL** (L-MCP-061). Point
  data questions at warehouse copies.
- **No gateway, no data answers; add the licence and it works (L-MCP-090).** Without the service, CLAIRE answers
  "source unsupported" or "the Data Gateway Service is not running on your Secure Agent". Once the licence arrived, the
  service deployed to every agent within ~10 minutes with no selection (L-AGENT-097), and the data prompts passed with
  warehouse-identical numbers. When a name exists as both a table and a view, answer CLAIRE's "which one?" with "The Table".
- **Documented sources and limits (L-MCP-114).** Amazon Redshift (v2), Databricks, Google BigQuery V2, Azure Synapse
  SQL, Azure SQL Server, Microsoft SQL Server, Oracle and Snowflake; **not PostgreSQL** (choose a sample's store
  accordingly, L-MCP-121). A preview shows at most **100 rows x 100 columns**, and the row cap is in the SQL itself:
  every query "Query the data" generates ends in `LIMIT 100`, even a single-row aggregate (8 of 8 Show Code captures),
  and the downloadable card holds the same capped result, with no truncation warning (L-MCP-114). Inferred joins need PK/FK constraints (for BigQuery and Synapse through a custom catalog
  source), but in practice a question keeps only one asset in scope (L-MCP-100). An uncataloged dataset is "not in
  your catalog".
- **When the gateway's agent is down (L-AGENT-051).** "Query the data" answers: "I couldn't execute the data
  query because the underlying data service connection is currently unavailable... ensure the data gateway service is
  running." Glossary, lineage and search prompts are not affected. Recovery:
  1. Start the agent. If its systemd unit shows `failed` because the graceful stop outran its timeout, run
     `systemctl reset-failed <unit>`, then `systemctl start <unit>`.
  2. Wait for the agent to read READY (a few minutes) and for `IDMC_Data_Gateway_Service` to read RUNNING in
     `GET /api/v2/agent/details/<agentId>` (about 7 minutes after the start).
  3. Re-ask the prompt in a new conversation (the re-test answered in 96 s with chart and SQL).

  The gateway logs to `<agent_home>/apps/IDMC_Data_Gateway_Service/<ver>/log/system/log/idmc-data-gateway-service_host-*`
  and holds long-lived :443 tunnels to the vendor cloud, so it opens no new connection per query: a sampler that watches
  only new sockets cannot prove it is out of the data path
  ([Evidence Discipline](../14-working-with-claude/02-evidence-discipline.md)). Keep that agent running
  until another runtime environment of the org runs the gateway (L-AGENT-097).
- **Gateway tuning (documented, L-MCP-115).** APP_CFG properties on the Data Gateway Service:
  `idmc_dgs_connectionPoolMaxSize` (100, range 10-1000), `idmc_dgs_connectionPoolCacheExpiryDuration` (30 min, 10-120),
  `idmc_dgs_queryExecutionTimeout` (60 s default). Raise the timeout before blaming the prompt for a slow view. Python
  for generated cleansing code needs `python_enabled=true` with Pandas and PyArrow (L-MCP-109).

---

## 7. Running a demo or a regression set

1. About **30 minutes before**, run every prompt once, each in a new conversation (L-MCP-054). The same prompt passed,
   asked "which asset?", or drifted into a rule plan on different runs. In one final 8-prompt set, 7 of 8 passed the
   first time. **Pin** good **catalog** answers (glossary, PII, lineage, scores) as fallbacks. Saved and pinned
   conversations drop query results ("no longer available due to privacy guidelines"), so "Query the data" answers
   cannot be kept as pinned fallbacks: rehearse them, then run them live (L-MCP-122).
2. Keep tested fallbacks for every slot (§4 shapes).
3. **Freeze the catalog:** no rescans within ~40 minutes; the gateway agent running; no legacy duplicates.
4. Record every run: prompt, pass/partial/fail, seconds, and a screenshot. A pass/fail log per prompt is what made the
   final set defensible.
5. After the demo, unpin the rehearsal conversations if they would confuse later users.
6. **Re-test after every catalog change**, whoever makes it: rescans, renames, source deletions, a data quality run and
   rule-instance deletions all changed answers in one morning (L-METHOD-120). Have the catalog owner announce each change,
   then stop catalog jobs once the answers are verified.
7. **Rename and rescan before the demo.** A renamed source keeps its old name in CLAIRE's answers until it is rescanned (L-CDGC-147).
8. **Audit the org after a test batch.** List rule specifications, dictionaries, mappings, tasks and mapplets updated
   since the batch began (`GET /public/core/v3/objects`); a single typed reply at a Publish prompt published a rule
   (L-MCP-096, L-UI-030).

---

## 8. Driving CLAIRE GPT without a person

- **There is no public API.** The CLAIRE agent MCP endpoint (`claire-orchestrator-ai-agent`) can list **0 tools** for an
  org, and a local CLAIRE MCP config may point at a different org than the one under test (L-MCP-033). Check what
  your MCP config logs into before drawing conclusions
  ([04](04-agent-style-mcp-async-orchestration-custom-shims.md)).
- **Scripted browser harness (L-MCP-065).** From a host **outside any enterprise proxy** (proxies blanked
  the IDMC single-page apps under automation, L-UI-011; on 2026-10-06 a Chromium flag set drove other consoles from
  behind one, L-UI-031, but CLAIRE GPT was not retested that way):
  - log in fresh, or refresh the saved state before a batch;
  - read prompts from a JSON file; open a new conversation per prompt;
  - auto-click "proceed" when CLAIRE offers a plan, from an explicit **allow-list** only, and never click Publish,
    Accept, save or delete;
  - **stop the scenario** (or click "Don't Publish Rules") when a Publish/Accept prompt is showing, before any scripted
    follow-up (L-UI-030);
  - auto-answer only harmless clarifications ("The Table");
  - wait until the busy text (including its "...", for example "Analyzing concepts...") is gone;
  - save the answer text plus a screenshot per prompt.

  One harness exited early because it matched the busy text without the dots.
- **A settle rule that works (L-UI-028).** Read only the newest reply (record the page text length before sending);
  treat it as busy while its last ~60 non-space characters hold the letter-spaced spinner text ("L o a d i n g"), and as
  done on reply markers ("let me know", "shall I proceed", "Cards (<n>)") or 150 s of unchanged text. Never use a bare
  "..." as a busy marker: the input placeholder "Ask CLAIRE..." always contains it. Add the single Unicode ellipsis
  U+2026 to the busy patterns: status lines such as "Checking available connections…" end in it, and a rule that knows
  only "..." and "Loading" cut a data prompt at 76 s with no table (the same prompt passed in 116 s once U+2026 was a busy
  marker); re-check old "no table" failures for this cause (L-UI-028).
- **Pins and renames (L-UI-029).** Hover the row that holds `span[data-testid=chat-nav-link]` and use `chat-pin-button`,
  `chat-edit-button` and `chat-delete-button` (on the Pinned tab, `chat-unpin-button`). Read the Pinned tab's titles back:
  a rename can silently not stick.
- **The managed agent routes answer like the UI (L-MCP-111).** `datamanagementorchestrator.orchestrate`,
  `orchestrate_master_data_analysis` and `dataexplorationagent.data_explore` returned the same answers as the CLAIRE GPT
  UI for the same prompts (DQ scores, unscored tables, low-score diagnosis, MDM match rules, NL data checks with a chart
  and an SQL citation), in **28-80 s** instead of 50-130 s, and they leave no conversation in the shared UI list. Plans
  come back for approval rather than executing, and on an unprofiled table `orchestrate` runs its own read-only
  profiling SQL through the gateway. Mechanics (L-MCP-112, with L-MCP-030 and L-MCP-044):
  - every tool argument goes inside a **nested inner JSON-RPC envelope**, and results are nested the same way;
  - poll `get_skill_execution_updates` with `cursor` starting at `"0"` and feed back `pagination.cursor`;
  - the answer streams as TOKEN items whose `content` fragments you concatenate, plus ARTIFACT items with GridView data;
  - a HUMAN_PROBE carries its question in `probe_message`; answer it in the same conversation;
  - `data_explore` requires `prompt`, `name` and `external_id` (documented schema, L-MCP-119);
  - a `request_upload_url` PUT can still answer 409 (the preflight race, L-DQ-072): request a fresh URL and retry
    (two retries were enough).

  See [04](04-agent-style-mcp-async-orchestration-custom-shims.md) and
  [01](01-managed-mcp-servers-catalog-access.md) (20 managed servers in the vendor guide, L-MCP-119).

---

## 9. The UI-only parts

- New Conversation, **pinning** and unpinning conversations (no API; a browser harness does them, L-UI-029).
- The `@` mention picker.
- Clicking the **LINEAGE** card to open the graph.
- **Show Code** for the generated SQL, and the chart rendering (over MCP, `data_explore` returns an SQL citation and
  GridView data instead, L-MCP-111).
- The "Yes, proceed" button on plans (a click only fills the box; press Send, L-MCP-079).
- "Generate a mapping" in the Data Integration designer: the generated mapping must be saved from the canvas
  (L-MCP-052). In the CLAIRE GPT chat, "Create a mapping to load these" after an exploration produces only an in-chat
  mapping artifact; nothing is saved in the org (L-MCP-108). `/saas/public/core/v3/copilot` returns 404. Headless mapping authoring goes through packages instead
  ([Data Integration (CDI)](../04-mappings/)).

---

## 10. What CLAIRE GPT can and cannot change (L-MCP-089)

On an org that is not in a private preview, the CLAIRE GPT chat **authors; it does not act**. The Data Integration agent
"can't perform create, move, store, or delete operations on existing data", and drafts are saved only from the designer
canvas.

| CLAIRE GPT persists | CLAIRE GPT does not |
|---|---|
| DQ rule specifications from rule generation, in the CLAIRE project and folder, after Publish + Send (about 4 min end to end) (L-MCP-079) | write source or target data, or run non-SELECT SQL ("Query the data" is SELECT-only, §6) |
| dictionaries a generated rule needs, saved at the "Generate Dictionaries" step even if you then click "Don't Publish Rules" (L-MCP-097) | save or run a pipeline: "Create a mapping" is an in-chat proposal (L-MCP-108); "generate a mapping" is saved from the designer canvas (L-MCP-052) |
| catalog rule occurrences (RuleInstance assets) when you accept recommended rules (L-MCP-086, L-CDGC-144) | call a CAI process or any MCP tool, yours or Informatica's |
| | run what it publishes: publishing a rule does not execute it |

Audit after a session: `GET /public/core/v3/objects?q=type=='RULE_SPECIFICATION'` (and `DICTIONARY`) by update time, and
the RuleInstance census in the catalog ([07/04](../09-catalog-lineage/04-search-lineage-marketplace.md) §2.2).

**Routes that do change data, ranked:**

1. **CLAIRE authors, your automation executes.** Detect new or changed rule specifications (diff `RULE_SPECIFICATION`
   objects by `id` and `updateTime`) and execute each in a mapping or in the warehouse. This is a design: the execute
   half has not been built here.
2. **Your own agent on the vendor-hosted MCP servers.** `jobmanagement` runs tasks and taskflows,
   `cdgccatalogenrichment` edits glossary and classifications, `dataqualityagent` generates and persists rules, and
   `datamanagementorchestrator` routes across skills ([01](01-managed-mcp-servers-catalog-access.md) §3).
3. **A composite MCP server** that exposes CAI processes as tools to your own agents (documented requirements: Basic
   Auth, REST/SOAP binding, Cloud Server; limits 1,000 requests per minute and a 1 MB payload). CLAIRE GPT is not a
   client of it ([01](01-managed-mcp-servers-catalog-access.md) §8).
4. **CAI agent recipes** with your own LLM key.

**Dead ends:** non-SELECT SQL through "Query the data"; CLAIRE GPT calling your MCP tools; requesting MCP tool
connections for a newer org (a product decision, not an entitlement, L-MCP-081).

---

## 11. When CLAIRE GPT is not available: deterministic fallbacks (L-MCP-067)

Build no-credit, deterministic stand-ins over the live catalog and warehouse, and validate the real CLAIRE GPT against
them once it is enabled:

- **discovery:** the catalog search API (`POST.../data360/search/api/v1/search`) for ranked hits;
- **NL-to-SQL:** a curated intent matcher plus pre-validated queries against the gold layer;
- **documentation research:** curated pointers to proven API mechanics.

Prove each with a harness, and label them clearly as fallbacks.

---

## 12. Overturned beliefs (kept so nobody re-learns them)

| Belief | Held | Overturned by | Lesson |
|---|---|---|---|
| "CLAIRE GPT is not entitled / has no plane": 404s on `/data360/claire-gpt/*`, `/copilot/*`, `/ai/*`, no agentic engine on the agents | 2026-07-04 to 2026-07-25 | The service lives on `claire-gpt.<domain>`; EffectiveLicenses listed it; a live query answered (201) on 2026-07-09; 70 runs in September | L-MCP-076 → L-MCP-050 |
| "The CLAIRE orchestrator has zero skills until the org owner loads them server-side" | 2026-09-22 to 2026-09-23 | A mis-pointed local shim; the managed `datamanagementorchestrator` exposes `orchestrate`; test CLAIRE GPT in the UI | L-MCP-073 → L-MCP-033 |
| "Rule recommend and generate do nothing after 'Yes, proceed'" | 2026-09-28 to 2026-09-30 | The click only fills the message box; press Send (2026-09-30) | L-MCP-058 → L-MCP-079 |
| "CLAIRE cannot answer catalog DQ-score questions" | 2026-07-09 to 2026-09-30 | Accept recommendations, run the source's Data Quality capability with a runtime environment in typeCapabilities; CLAIRE then reports the scores (2026-09-30) | L-DQ-051, L-DQ-052 → L-DQ-097, L-CDGC-143 |
| "Catalog-wide PII or classification searches fail" | 2026-09-28 to 2026-09-30 | "Which columns in the catalog are classified as CLASSIFICATION?" found 25+ columns across sources (3 of 4); "Which tables contain..." still fails (2026-10-01) | L-MCP-058 → L-MCP-092 |
| "Mappings are not catalog assets; they cannot be named in prompts" | 2026-09-28 to 2026-09-30 | With Data Integration metadata scanned, mappings are explained by name (name the folder when variants exist) and listed per folder; mapping tasks are still not found (2026-10-01) | L-MCP-058 → L-MCP-093 |
| "Product how-to questions are unreliable" | 2026-09-28 to 2026-09-30 | 5 of 5 passed, including help about the asset found earlier in the conversation (2026-10-01) | L-MCP-058 → L-MCP-094 |
| "Lineage of views fails" | 2026-09-28 to 2026-09-30 | View-to-view lineage and multi-hop upstream lineage through views answered; job-level and SaaS lineage still need the integration lineage setup (2026-10-01) | L-MCP-058 → L-MCP-107 |
| "Job-level and SaaS lineage answer 'no lineage' or '0 upstream assets'" | 2026-10-01 | With an IICS source scanned, references MERGEd and a curated edge, CLAIRE walked table > mapping task > library reference > Salesforce object (2026-10-27); custom-query tasks still answer 0 | L-MCP-107 → L-MCP-128 |
| "'What should we fix first?' invents issues" | 2026-09-30 | Adding "Use only the scores in the catalog." grounds it: no invented tail (2026-10-01) | L-MCP-088 → L-MCP-095 |
| "NL-to-SQL has no headless route" | 2026-07-09 to 2026-09-30 | The managed `orchestrate` and `data_explore` MCP tools answer the same prompts with the same answers (2026-10-01) | L-MCP-053 → L-MCP-111 |
| "Pin the dataset ('in the DATASET dataset') to anchor every question" | until 2026-10-01 | For "Query the data" the pin can make CLAIRE search for the dataset as an asset and answer from a same-named view; pin only catalog and DQ-score questions (2026-10-01) | L-MCP-054 narrowed by L-MCP-122 |
| "Pin every good rehearsal conversation as the demo fallback" | until 2026-10-01 | Pinned conversations drop query results; only catalog answers survive as pinned fallbacks (2026-10-01) | L-MCP-054 narrowed by L-MCP-122 |
| "Ask the business impact as a follow-up to the numbers" | until 2026-10-01 | The follow-up drifts into product documentation; one combined count + impact prompt passed 3 of 3 (2026-10-01) | L-MCP-122 |

---

## 13. Open questions

- Is the conversation API behind the UI usable by external clients, and how does it authenticate?
- ~~Can pinned conversations be managed without the UI?~~ Answered: not by an API, but a browser harness pins, unpins and renames them (L-UI-029).
- How long does index lag take to settle after a full rescan of a large source?
- ~~Do `datamanagementorchestrator.orchestrate` answers match CLAIRE GPT UI answers for the same prompt?~~ Answered: yes, same numbers and diagnosis, faster (L-MCP-111).
- ~~Does the 100-row preview cap truncate "list every..." answers silently?~~ Answered: yes; every generated query ends in `LIMIT 100` and the narrative gives no warning (L-MCP-114).
- Does "Show the lineage between the table TABLE1 and the table TABLE2" (documented) work where single-asset job lineage is empty?
