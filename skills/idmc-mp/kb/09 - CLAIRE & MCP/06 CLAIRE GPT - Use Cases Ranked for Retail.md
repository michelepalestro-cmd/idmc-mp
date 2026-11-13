# CLAIRE GPT: every use case, ranked by impact for a retail customer

**Answers:** Which CLAIRE GPT and CLAIRE agent use cases matter most for a retailer, and how reliably did each work
live? Which prompt shape runs each one? What should never be demoed? What is the 15-minute storyline?

**Read when:** planning a CLAIRE GPT demo, proof of value or business case for a retail (or similar consumer-facing)
organization; choosing which prompts to rehearse.

**Key rules:**
- Lead with multi-step workstreams in one conversation (DQ triage, trust check, score to bad rows to impact); they ran
  3 of 3 with warehouse-exact numbers (L-MCP-091, L-MCP-104).
- Ask a count and its business impact in one prompt; a separate impact turn can drift into product documentation
  (L-MCP-122).
- Name the system, object type and bare table; never type `@`; re-ask a missed table search in a new conversation
  (L-MCP-056, L-MCP-103).
- Trust the chart and Show Code, not the narrative; list answers stop at 100 rows (L-MCP-101, L-MCP-114).
- Never demo the hallucination-prone asks (data dictionaries, governance counts) or anything in Tier D (L-MCP-106).
- CLAIRE GPT authors rules and plans; it does not change data or run pipelines (L-MCP-089).

**Related:** [03 CLAIRE GPT - Prompting Rules](<03 CLAIRE GPT - Prompting Rules & Patterns.md>) ·
[01 Managed MCP Servers](<01 Managed MCP Servers (catalog & access).md>) ·
[04 Agent-Style MCP](<04 Agent-Style MCP (async orchestration) & Custom Shims.md>) ·
[CLAIRE DQ Agent - File-Based](<../06 - Data Quality & Profiling/03 CLAIRE DQ Agent - File-Based Profiling & Cleansing.md>) ·
[Lessons: CLAIRE & MCP](<../13 - Lessons Learned/09 CLAIRE & MCP.md>)

**Last verified:** 2026-11-03

> **Summary.** A ranked list of what CLAIRE GPT and the CLAIRE agents can do, ordered by business impact for a
> **retail** organization, with how reliably each one worked in live tests. The base is about 200 live CLAIRE GPT runs
> plus 13 managed MCP agent calls in one standard org with:
> - a PostgreSQL operational source;
> - a BigQuery warehouse;
> - a Salesforce CRM;
> - a CDGC catalog with a glossary and DQ scores;
> - Customer 360 entities.
>
> Other inputs were the official documentation (57 documented capabilities) and retail market research (35 candidate
> use cases).
>
> **Headline:** the most powerful things CLAIRE GPT does for a retailer are **multi-step workstreams in one
> conversation**. Data-quality triage, a trust check before a board number, and "why is my score low → show me the bad
> rows → what does it cost me" each ran end to end with warehouse-exact numbers. Single-prompt tricks rank lower.

---

## 1. How the ranking works

Each use case gets two scores, and the rank is impact first, then proof:

- **Retail impact (1–5).**
  - 5 = board or P&L level: revenue, cost, regulatory fines, or the trust of an executive number.
  - 4 = a program-level win (loyalty, C360, merchandising, loss prevention).
  - 3 = a productivity gain for a team.
  - 2 = convenience.
  - 1 = trivia.
- **Live proof**, in the tested org:
  - **Proven** = passed at least 2 of 3 repeats, with numbers checked against the warehouse.
  - **Promising** = passed once, not yet repeated.
  - **Flaky** = passes sometimes, so it needs a fallback.
  - **Not working** = failed, or the capability is not in the org.
- **Type:**
  - **W** = a multi-step workstream: chained prompts in one conversation, or plan → approve → act → verify.
  - **S** = a single prompt.

The tiers follow from the two scores:

| Tier | Rule | Use it for |
|---|---|---|
| **A: lead with these** | Impact 5, Proven | The opening 10 minutes of any retail CLAIRE demo or POV |
| **B: strong supporting** | Impact 4–5 and Promising/Flaky, or impact 4 and Proven | Persona-specific follow-ups |
| **C: useful, lower impact** | Impact 2–3, Proven | Q&A, enablement, deep dives |
| **D: roadmap or do not demo** | Not working, or not in a standard org | Slides only, with the reason |

---

## 2. The ranking

### Tier A: lead with these (impact 5, proven live)

| Rank | Use case | Type | Retail persona and value | Tested prompt shape (fill the UPPERCASE) | Live proof |
|---|---|---|---|---|---|
| **1** | **Data-quality triage workstream.** Failing checks, then a failure-rate chart, then root sources (upstream lineage), then a status note for the CDO | W (4 turns) | CDO, data governance. It turns "our data is bad" into a ranked, sourced, costed list in about 4 minutes. Poor DQ costs an average organization at least $12.9M a year (Gartner) | 1) `Which data quality checks fail in the WAREHOUSE view DQVIEW? Query the data.` 2) `Show the failure rate of each failing check as a bar chart.` 3) `Where does the data in DQVIEW come from? Show its upstream lineage.` 4) `Write a short data quality status update for the Chief Data Officer covering the numbers, the root sources and the top 3 fixes.` | **3/3** full chain, failure rates exact; the lineage card showed 25 upstream assets over 4 hops; the CDO fixes are somewhat generic |
| **2** | **"Why is my score low → show me the bad rows → what does it cost me"** | W (2 turns) | Loyalty/CRM, data steward. Example: a phone-format score of 0% explained as "almost no customer phone number is in international format, so SMS campaigns cannot reach them; fix the format first" | 1) `What is the data quality score of the WAREHOUSE table TABLE, and which rules are applied to it?` 2) `How many CUSTOMERS in the WAREHOUSE table TABLE have a phone number that does not start with a plus sign, and how many have no phone at all? Query the data and explain the business impact on SMS marketing campaigns.` | The combined count + impact turn passed **3/3** with exact counts; asking the impact as a separate third turn passed only 2 of 4 in re-tests (it drifted into product documentation), so keep it in the count prompt (L-MCP-122). The diagnosis-only prompt `What could be the reason for the low data quality score of the WAREHOUSE table TABLE?` passed 5/5 in the UI and 3/3 over MCP |
| **3** | **"Can I trust this number before it goes to the CEO/board?"** One verdict built from metadata completeness, DQ scores and lineage | W (plan + one verdict); extend with query → chart → summary | CDO, CFO. Answers the executive question in 90 s | `I want to use the WAREHOUSE table TABLE for reporting to the CEO. Assess its metadata completeness, data quality and lineage, and tell me whether I can trust it.` Follow-ups: query, `Show that as a bar chart.`, `Write a 5 bullet executive summary.` | Proven (3 runs; 4/5 turns in a later chain, where only the opening "find the table" discovery failed) |
| **4** | **Self-serve "ask the data" with conversational refinement** | W (3 turns) | Merchandising, loyalty, store ops. No BI ticket; answers in about 90 s with charts and Show Code SQL | 1) `Who are the top 10 CUSTOMERS by MEASURE in the WAREHOUSE view VIEW, excluding test accounts? Query the data.` 2) `Now show only SEGMENT customers.` 3) `Show that as a bar chart.` | **3/3**, the same list as the BI dashboard |
| **5** | **Payment / revenue leakage analysis** (for example lost revenue per card network) | W (3 turns) | CFO, finance ops, payments. Exact leakage shares in under 3 minutes | 1) `What is the recovered revenue versus the lost revenue per card network in the WAREHOUSE view VIEW? Query the data.` 2) `Which card network has the highest share of lost revenue? Calculate lost revenue as a percentage of recovered plus lost revenue.` 3) `What is the business impact and what should the finance team do next?` | **3/3**, percentages exact; the finance advice is generic. If the bare impact turn drifts into product documentation, fold it into turn 2 ("... and explain the business impact for the finance team") (L-MCP-122) |
| **6** | **Policy document → tested, publishable DQ rules** | W (attach → plan → generate → test → publish) | Merchandising, pricing and finance stewards. A written policy (SKU format, price above 0, discount 0–100%, allowed tiers, no future order dates) becomes tested rules in about 5 minutes, and duplicates of existing rules are skipped | attach a plain-text policy file, one rule per line, then `This file is a data quality policy with one rule per line. Generate data quality rules from this file.` Proceed + Send; stop or publish at the end | Proven (5 tested rules from a 6-line policy; the opening sentence fixed the 1-in-3 misroute; duplicate detection worked on every run) |
| **7** | **Messy product-catalog file → cleansing plan, code and reusable mapplet** | W (attach → plan → proceed → artifact) | E-commerce, merchandising content, supplier onboarding. Every planted issue was found with its row: duplicate SKU, "$3.49" stored as text, a negative price, discounts of 250 and 120, 16 category spellings, 11 unit spellings | attach the file, then `Clean this file: standardize the SKU, category and unit columns, fix prices stored with a dollar sign or as negatives, cap discounts at 100 percent, and flag the records you could not fix.` Proceed; then "Proceed without testing" | **2/2**; the mapplet could be explained later in the same conversation |
| **8** | **Privacy sweep across the estate (CCPA/GDPR/PCI)** | S, or W with lineage | Privacy officer, CISO. Every email or phone column in every system in one answer. California fined a retailer $1.2M under CCPA (2022) | `Which columns in the catalog are classified as Email?` (also `... as Phone Number USA?`). Per table: `List the columns of the SYSTEM table TABLE and say which of them contain personal data.` | Catalog-wide 3/4 (found 25+ columns across PostgreSQL and BigQuery); per-table on a warehouse table proven. **Wording matters**: "Which tables contain email addresses?" fails |
| **9** | **Customer value segmentation** | S (+ follow-ups) | Loyalty/CRM, CMO. High/medium/low value bands with counts and spend, exact on every run | `Segment the CUSTOMERS in the WAREHOUSE view VIEW into high, medium and low value: high is lifetime spend over 500, medium is 150 to 500, low is under 150. Exclude test accounts. Count the customers and total spend per segment. Query the data.` | **3/3** exact |
| **10** | **CLAIRE inside your own agents (managed MCP routes)** | W (plan, poll, artifacts) | Head of AI, platform team. The same answers as the UI in 28–80 s from any MCP client, for example a retailer's own agents. CLAIRE has an Informatica plugin for Claude and an Agent Fabric listing | `orchestrate` ("Which SYSTEM tables have no data quality scores?", a score and its rules), `data_explore` (customers per tier), `orchestrate_master_data_analysis` (match rules), DQ agent cleansing with a file upload | **11/13** pass, 2 stopped at a plan by design; answers matched the UI |

### Tier B: strong supporting (persona follow-ups)

| Rank | Use case | Type | Impact | Tested prompt shape | Live proof |
|---|---|---|---|---|---|
| 11 | **Anonymous-to-loyalty conversion opportunity** (guest shoppers who could become loyalty members). CLAIRE builds its own opportunity score per location | S | 5 | `Using the WAREHOUSE view VIEW, query the data and tell the marketing team which LOCATION has the best opportunity to convert guest shoppers into loyalty members, and why.` | Promising (1/1, $ uplift verified) |
| 12 | **Churn / lapsed-VIP watch → win-back plan** | W (3 turns) | 5 | 1) `How many CUSTOMERS per tier have had no activity in the last 30 days in the WAREHOUSE view VIEW? Count CUSTOMERS with no activity at all as inactive. Query the data.` 2) `Of the CUSTOMERS in VIEW2 with lifetime spend above 500, which ones have their last purchase more than 14 days ago? Query the data.` 3) `Based on these results, recommend a win back campaign.` | Flaky (1/3 full, 2/3 usable; the losses were table-search misses) |
| 13 | **Anomaly / outlier transactions** (loss prevention, returns abuse) | S | 4 | `Are there any unusually large transactions in the WAREHOUSE table TABLE? Query the data, flag amounts more than 3 standard deviations above the mean, and list the outliers.` | Proven 2/3, threshold and rows exact |
| 14 | **One-sentence business rule → tested control** | W (plan → test → publish) | 4 | `Create a data quality rule that checks that the COLUMN column in the SYSTEM table TABLE is ALLOWED VALUES / a positive number / not in the future.` | Proven 5/6 (price, discount, tier, date, state); name the table, otherwise it asks for a data source |
| 15 | **One-prompt governance brief** (numbered multi-intent) | S → 4 cards | 4 | `1. Find the WAREHOUSE table TABLE. 2. List its personal data columns. 3. Show its downstream lineage. 4. List the business terms linked to it.` | Proven 3/3 for **catalog** tasks; a numbered **analytics** prompt failed 0/1 |
| 16 | **Customer 360: entities, match and survivorship rules explained** | S | 4 | `Show the match rules and survivorship rules of the Person business entity.` | Proven 4/4 UI + MCP |
| 17 | **Blind spots: which systems are not measured** | S | 4 | `Which SYSTEM tables have no data quality scores?` | Proven (5/5 PostgreSQL; BigQuery passed; same over MCP) |
| 18 | **Recommend → accept DQ rules on the customer master** | W | 4 | `Recommend data quality rules for the C1, C2 and C3 columns of the SYSTEM table TABLE.` then check the card, then type `Accept all the recommended rules` | Proven with the columns named (9/9 pairings). **Only matches rules already in the repository**; for new controls use #6/#14 |
| 19 | **Duplicate-customer diagnosis on a file** (same person, different spellings) | W | 4 | attach a customer file, then `Find the duplicate customers in this file, show the evidence, and propose golden records.` | Flaky: the diagnosis is strong, but the golden-record table never appeared, and the repeat errored |
| 20 | **PII anonymization code for a file** (mask email/phone, last-4 card, birth year) | W | 4 | attach the file, then `Mask the email and phone, keep only the last 4 digits of the card number and only the birth year.` | Flaky: correct PII and code, but **invented issues**, so it needs review |
| 21 | **Exploration → "Create a mapping to load these"** (pipeline from a question) | W | 4 | query first, then `Create a mapping to load these customers.` | Promising: an in-chat mapping proposal; nothing is saved to the org; save it from the designer |
| 22 | **Operations KPIs** (cancellation rate per store, surcharge or add-on revenue, average spend per tier) | S | 3–4 | `What is the order cancellation rate per LOCATION in the WAREHOUSE view VIEW? Rank them. Query the data.` | Proven (4 KPIs, all exact) |

### Tier C: useful, lower impact (Q&A, enablement, deep dives)

| Rank | Use case | Prompt shape | Proof |
|---|---|---|---|
| 23 | Explain an ETL mapping in business terms | `Explain in business terms what the mapping MAPPING in the FOLDER folder does, step by step.` | 7/9 overall; 2/2 with the folder named |
| 24 | Executive brief of a data product | `Summarize the WAREHOUSE table TABLE for a business executive: what it contains, where it comes from, who uses it and how sensitive it is.` | Proven 3/3 |
| 25 | Glossary: KPI definitions and terms linked to a table | `What does the business term TERM mean and where does its data come from?` / `Which business terms are linked to the SYSTEM table TABLE?` | Proven 7/7 (avoid parentheses in term names) |
| 26 | Help in context of the asset just found | `Find the SYSTEM table TABLE.` then `How do I add data quality rules to this table?` / `How do I mask the sensitive columns of this table?` | Proven 2/2 |
| 27 | Product documentation Q&A (scorecards, classification, mapping vs task) | `How do I set up a data quality scorecard in Cloud Data Quality?` | Proven 3/3 |
| 28 | Distributions, mix and trend charts | `What is the distribution of MEASURE in VIEW? Group into ranges A, B, C. Query the data and show a bar chart.` / `... show a pie chart.` / `... show a line chart.` | Proven; **read the chart, not the narrative** (the text covers only the first ~5 rows) |
| 29 | Querying raw, messy data (numbers stored as text) | `... The amount and discount columns are stored as text. Query the data.` | Promising 1/1 (it CASTs and TRIMs) |
| 30 | Compare a source table with its curated copy | `Compare the SYSTEM table T1 with the WAREHOUSE table T2.` | Proven 2/2 (exact column diff) |
| 31 | Suggest glossary terms for a table's columns (no create) | `Suggest business glossary terms for the columns of the SYSTEM table TABLE. Do not create them.` | Proven 2/2 |
| 32 | Data Marketplace: collections never requested, collection overview | `What data collections have never been requested in Data Marketplace?` | Proven 3/3 (one unverified "available in the marketplace" claim on another prompt) |
| 33 | File profiling with row and column filters | attach, then `Profile only the rows where COLUMN is VALUE, and only columns A, B, C and D.` | Proven 2/2 |
| 34 | Data Integration inventory (projects, folders, mappings) | `List all projects and folders in Data Integration.` | Proven 4/4 |
| 35 | Ownership and certification gaps | `Who owns the WAREHOUSE table TABLE and who is its data steward?` | Proven: it answers "not provided" honestly |
| 36 | Clear conversation memory mid-thread | `Clear conversation memory...` | Proven 1/1 |

### Tier D: roadmap or do not demo (and why)

| Use case | Status | Why / what unblocks it |
|---|---|---|
| **Job-level, SaaS-object and source-system lineage** (PostgreSQL → ETL → warehouse → CRM) and impact analysis from a source table | Not working in the test org (2026-10-01); in another org it walked 4 upstream hops through a mapping task to a Salesforce object once the integration lineage was set up, for tasks that read connection objects (2026-10-27, L-MCP-128) | Lineage worked at view level and on the DQ view (25 upstream assets, 4 hops), but returned 0 upstream for the gold table and its CRM targets. It needs a Data Integration catalog source with lineage discovery and accepted connection assignments |
| Cross-table joins in "Query the data" | 0/4 | Only one table enters scope. Query a pre-joined view instead |
| Discovery from a business question with no table name ("Where is our loyalty data?") | About 1 in 7 | Name the system and the table; enrich glossary links and descriptions |
| Generate a mapping from words ("create a mapping that reads X and writes Y") | Fails ("unable to identify all assets") | Use #21, or the Data Integration Copilot in the designer |
| "Generate SQL" / "show me the SQL" in chat | Refused | Use "Query the data", then **Show Code** |
| Full row lists ("list every customer who...") | Capped silently at 100 rows: every generated query ends in `LIMIT 100` | Ask for counts or a top-N; for the full list run the Show Code SQL without the LIMIT in the warehouse (L-MCP-114) |
| "Fix / update / delete these records", SQL that writes, or calling your own tools from the chat | Not possible by design: CLAIRE GPT authors rules and plans only | Use the routes in [03](<03 CLAIRE GPT - Prompting Rules & Patterns.md>) §10 (L-MCP-089) |
| Data dictionary generation | **Hallucinated** columns that do not exist | Never demo. Use the executive brief (#24) |
| Governance counts ("terms with no linked assets", coverage %, "retire this system") | Wrong or inconsistent | Never demo |
| Query the data on PostgreSQL | Not supported by design | Supported: Redshift, Databricks, BigQuery, Synapse, Azure SQL, SQL Server, Oracle, Snowflake |
| Product data enrichment from supplier PDFs (Product Experience Agent) | Preview, inside Product 360 | High retail value (PIM); needs Product 360. Slide only |
| Metadata Enrichment agent, Data Steward agent, CLAIRE in Slack, A2A | Announced for Q4/Fall 2026 | Roadmap slide |

---

## 3. The best retail storyline (about 15 minutes, all Tier A)

Present these as **one agentic workstream**, which is how Informatica positions CLAIRE GPT: a supervisor agent, plan
approval, visible reasoning. Do not present them as separate tricks.

1. **Blind spots** (#17, 1 min): what nobody measures.
2. **Can I trust the board number?** (#3, 2 min).
3. **Why is the score low → the bad rows → the SMS revenue at risk** (#2, 3 min).
4. **The policy becomes controls** (#6, 5 min; start it, and narrate while it runs).
5. **Ask the data: top customers → one segment → chart** (#4, 2 min), then **leakage by card network** (#5) for a CFO
   audience, or **segmentation** (#9) for a CMO.
6. **Close with the platform** (#10): the same agents are callable from the customer's own AI.

Persona swaps:
- privacy officer: #8 + #15;
- e-commerce or merchandising: #7 + #14;
- loyalty: #12 + #11;
- loss prevention: #13 + #5;
- IT/architecture: #23 + #21 + Tier D lineage set-up.

---

## 4. Value notes for a business case

Public figures. Mark vendor numbers as "Informatica reports".

- Gartner: poor data quality costs an average organization at least **$12.9M a year**, and 59% of organizations do not measure DQ.
- NRF / Happy Returns: **$890B** in US retail returns in 2024 (16.9% of sales); 93% of retailers call return fraud significant.
- IHL: **$1.7T** global inventory distortion in 2024, of which $1.2T was out-of-stocks.
- California AG: a **$1.2M** CCPA penalty against a beauty retailer (2022).
- Informatica customer stories:
  - a manufacturer's DQ score went from 80% to 95% (over $200K saved, CLAIRE GPT in use);
  - a sportswear retailer had 25% fewer quality errors;
  - an RV retailer deduplicated 29M customer records.
- Cost: CLAIRE GPT meters **50 IPU per 1,000 queries**. Informatica advertises that design-time CLAIRE use (chat,
  copilots, agents) costs nothing extra through 2027-01-31 for eligible customers. Jobs it triggers bill normally.

---

## 5. Rules that make the ranking hold

The full detail is in [03](<03 CLAIRE GPT - Prompting Rules & Patterns.md>).

- Use a new conversation per scenario; follow-ups inside a workstream are fine.
- Name the system, the object type and the bare table; never type `@`. Do not add "in the DATASET dataset" to a "Query
  the data" prompt (L-MCP-122).
- Ask a count and its business impact in the same prompt (L-MCP-122).
- Expect about 1 in 6 table searches to miss. Re-ask in a new conversation.
- **Never send free text while "Publish Rules / Don't Publish Rules" is showing.** CLAIRE treats it as consent and
  publishes. "Generate Dictionaries" saves dictionaries before Publish.
- Trust the **chart and Show Code**, not the written narrative, for results longer than about 5 rows.
- Rehearse once; CLAIRE is nondeterministic. Pinned conversations drop query results, so analytics prompts must run live.
