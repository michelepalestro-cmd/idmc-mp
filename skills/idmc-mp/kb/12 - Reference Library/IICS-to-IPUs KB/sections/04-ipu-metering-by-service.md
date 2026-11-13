# 4. How Each Service Meters Against IPUs

[Section 3](./03-ipu-consumption-model.md) explained that IPUs are one universal pool spent
across the whole portfolio. This section answers the practical question that follows: **for
each IDMC service, what gets counted, and how fast does it draw the pool down?**

Every eligible service in the IDMC consumption matrix is defined by three things:

1. a **Scalar** — the thing being counted (compute hours, rows, gigabytes, API calls,
   assets, events, queries);
2. a **Metric** — the unit the scalar is bucketed into (e.g., *per hour*, *per million
   rows*, *per gigabyte*); and
3. an **IPU per metric unit** — how many IPUs one metric unit consumes, very often **tiered**
   so the marginal rate falls as volume rises.

> **About the rates below.** The specific "IPU per metric unit" numbers are **published**
> in Informatica's *Cloud and Product Description Schedule (CPDS)* — they are the public
> consumption matrix, not internal discounting. The figures quoted here are from **CPDS
> version 39.1, effective June 5, 2026**, and are **version-dated on purpose**: Informatica
> updates the matrix over time, and your subscription "includes updates to the IDMC matrix
> during the applicable Subscription Period." Always re-verify against the current CPDS
> before quoting to a customer. Informatica also publishes a **Measurement Guide** (on the
> Informatica Network) with the exact computation details per scalar. **`[verify]`** any
> rate that materially affects a scoping estimate.

---

## 4.1 The four metering bases (and what they mean)

Under the hood, every service meters on one of a handful of scalars. Understanding these
four families explains 90% of a consumption estimate:

| Scalar family | What it counts | Definition (CPDS) | Typical services |
|---|---|---|---|
| **Compute Units (per hour)** | Processing capacity used by an engine over time | "General utilization of processing capacity … inputs include processing power, transformation, physical/logical CPU-cores, nodes, outbound API calls, and job duration." **Minimum 4 CPU-cores** used in the calc. | CDI, CDQ, Advanced DI/DQ, DGC Scanner, B2B, Data Masking, INFACore |
| **Rows Processed (per million rows)** | Records moved/transformed/incorporated | "Number of rows … transferred, transformed or incorporated by each respective service." | CDC ingestion, DI-CDC, SQL ELT, DQ real-time, Data Access Management |
| **Data Volume (per gigabyte)** | Bytes ingested/replicated | "Volume of data transferred, transformed or incorporated." | Application / Database / File / Streaming ingestion (bulk) |
| **Other counts** | API calls, daily assets stored, events, queries, connections, orgs | Each defined individually | CAI, API Center, CDGC catalog/governance, Data Marketplace, Integration Hub, CLAIRE GPT |

A crucial consequence: **the same logical task can meter very differently depending on how
it runs.** Bulk database ingestion meters on **gigabytes**, but *change data capture* (CDC)
on the same database meters on **rows**. A data-quality rule run in batch meters on
**compute hours**, but the same logic exposed as a real-time API meters on **rows** at a
much higher rate. Scoping is about matching the *pattern* to the *scalar*.

---

## 4.2 Data Integration (CDI) and its compute-metered relatives

Standard data integration is the anchor workload and meters on **Compute Units per hour**,
tiered so heavy users get a lower marginal rate.

| Service | Scalar / Metric | IPU per metric unit (CPDS v39.1) |
|---|---|---|
| **Data Integration (CDI)** | Compute Units / hour | **0.16** for first 2,000 hrs; **0.025** thereafter |
| **Data Integration – Advanced Serverless** | Compute Units / hour | **0.28** for first 2,000 hrs; **0.10** thereafter |
| **Advanced Data Integration** (Spark/elastic "CDI-e") | Compute Units / hour | **0.19** |
| **Advanced Data Integration – Advanced Serverless** | Compute Units / hour | **0.32** |
| **Data Masking** | Compute Units / hour | 0.16 first 2,000 hrs; 0.025 thereafter |
| **Data Validation** | Compute Units / hour | 0.16 first 2,000 hrs; 0.025 thereafter |
| **INFACore** (embed DI/DQ in code/IDEs) | Compute Units / hour | **0.15** |
| **B2B & Industry Solutions** (EDI/HL7/SWIFT etc.) | Compute Units / hour | 0.28 first 1,000 hrs; 0.04 (1k–6k); 0.005 (>6k) |

Two patterns to read off this table:

- **Advanced (elastic Spark) compute costs a bit more per hour** than standard CDI (0.19 vs
  0.16) — you pay for the ability to run big-data-scale, parameterized, orchestrated jobs on
  managed elastic engines.
- **Serverless variants cost more per hour again** (e.g., 0.16 → 0.28 for CDI; see also DQ
  and DGC below). That premium buys away the infrastructure: serverless jobs "run on an
  Informatica-managed serverless Org," so you have **no Secure Agent compute to size,
  patch, or scale**. The trade is *more IPUs, less ops*.

### SQL ELT / advanced pushdown optimization — the biggest lever on consumption

**SQL ELT** pushes processing **down into the target ecosystem** (e.g., your cloud data
warehouse) instead of running it on Informatica's engines, and it meters on **rows**, not
compute hours:

| Service | Scalar / Metric | IPU per metric unit (CPDS v39.1) |
|---|---|---|
| **SQL ELT** (pushdown) | Rows Processed / million rows | **0.048** (first 100M); **0.010** (100M–10B); **0.002** (10B–5T); **0.0003** (>5T) |

Why this matters: with **advanced pushdown optimization (APDO / SQL ELT)**, the heavy
transformation compute happens in the customer's warehouse (Snowflake, Databricks,
BigQuery, Redshift, etc.), which the customer already pays for. Informatica then meters only
a very low **per-row** rate that **falls off a cliff at scale** (0.048 → 0.0003 IPU per
million rows). For large, set-based ELT workloads this can consume **dramatically fewer
IPUs** than running the same transformations as compute-hour jobs — a primary FinOps tactic
for keeping a pool efficient. (Conversely, chatty row-by-row real-time patterns are the
*expensive* end — see Data Quality – Real Time below.)

---

## 4.3 Cloud Application Integration (CAI) and APIs

Application integration and API traffic meter on **API calls**.

| Service | Scalar / Metric | IPU per metric unit (CPDS v39.1) |
|---|---|---|
| **Application Integration (CAI)** | API Calls / thousand | **1.453** (first 20K); 1.163 (20K–100K); 0.038 (100K–1M); 0.032 (1M–12.5M); 0.015 (>12.5M) |
| **Application Integration – Advanced Serverless** | API Calls / thousand | 2.5 (first 20K); 2.0 (20K–100K); 0.065 (100K–1M); 0.055 (1M–12.5M); 0.025 (>12.5M) |
| **API Center** (API management/gateway) | API Calls / **million** | **13.33** |
| **API Management** (folded into API Center as of Feb 7, 2025) | API Calls / million | 13.33 |

Notes:

- CAI historically also offered a **Compute Units / hour** scalar (1.38 first 60 hrs, etc.),
  but that basis is **grandfathered** — retained only "for IPUs subscribed before February
  7, 2025." New subscriptions meter CAI on **API calls**.
- **API Center meters per *million* calls** at a flat 13.33 IPUs — cheap at high volume,
  and the runtime "API Gateway" routes calls to the target service. An **API call is the
  individual call routed by the gateway.**
- The serverless CAI premium (roughly ~1.7× the standard per-thousand rate) again buys away
  infrastructure and supports long-running/stateful processes (screenflows, human tasks).

---

## 4.4 Data Ingestion & Replication (mass ingestion) — sub-type by sub-type

This family (Informatica's mass ingestion) splits by **source type** *and* by **bulk vs.
change data capture (CDC)** — and the scalar changes accordingly. **Bulk** loads meter on
**data volume (GB)**; **CDC** meters on **rows**.

| Sub-type | Scalar / Metric | IPU per metric unit (CPDS v39.1) |
|---|---|---|
| **Application Ingestion & Replication** (bulk) | Data Volume / GB | **0.1** (first 2TB); 0.08 (2–10TB); 0.05 (10–25TB); 0.018 (>25TB) |
| **Application Ingestion – Change Data Capture** | Rows / million | **6.00** (first 10M); **0.2** (>10M) |
| **Database Ingestion & Replication** (bulk) | Data Volume / GB | 0.1 (first 2TB); 0.08 (2–10TB); 0.05 (10–25TB); 0.018 (>25TB) |
| **Database Ingestion – Change Data Capture** | Rows / million | **6.5** (first 15M); 0.55 (15M–750M); 0.05 (>750M) |
| **Database Ingestion – Change Data Capture (via CDI)** *(DI – CDC, RDBMS incl. z/Series, iSeries)* | Rows / million | 4.88 (first 15M); 0.41 (15M–750M); 0.04 (>750M) |
| **File Ingestion & Replication** | Data Volume / GB | **0.03** (first 5TB); 0.015 (>5TB) |
| **Streaming Ingestion & Replication** (IoT/streaming) | Data Volume / GB | **0.27** (first 1TB); 0.135 (>1TB) |

How to read this for scoping:

- **Initial/bulk loads are cheap per gigabyte** (0.1 IPU/GB, dropping to 0.018 at scale),
  and **file replication is the cheapest of all** (0.03 IPU/GB) — moving files is low-touch.
- **CDC is priced on rows and front-loaded**: the first tranche (e.g., first 15M rows for
  database CDC) is relatively expensive per million, then the marginal rate collapses
  (6.5 → 0.55 → 0.05). CDC is designed for *steady, high-volume* change streams; a trickle
  of low-volume CDC jobs pays the high entry rate without reaching the cheap tiers.
- **Streaming is the priciest ingestion per GB** (0.27), reflecting always-on, low-latency
  processing.
- Each of these can run on a customer **Secure Agent** or, where available, on an
  Informatica-managed **serverless** environment (which shifts infra management to
  Informatica; verify serverless availability and any rate difference per sub-type).

---

## 4.5 Cloud Data Quality (CDQ) and Address Verification

Batch data quality meters on **compute hours**; real-time DQ and address verification meter
on **rows**.

| Service | Scalar / Metric | IPU per metric unit (CPDS v39.1) |
|---|---|---|
| **Data Quality (CDQ)** | Compute Units / hour | **0.38** (first 2,000 hrs); 0.152 thereafter |
| **Data Quality – Advanced Serverless** | Compute Units / hour | **0.65** |
| **Advanced Data Quality** (Spark) | Compute Units / hour | **0.45** |
| **Advanced Data Quality – Advanced Serverless** | Compute Units / hour | **0.77** |
| **Data Quality – Real Time** (rule specs/mapplets via API) | Rows / million | **35.0** (first 12M); **26.3** (>12M) |
| **Address Verification – Batch** (global, ex-IRL/GBR) | Rows / thousand | 1.10 (first 30K); 0.43 (30K–300K); 0.09 (300K–3M); 0.03 (>3M) |
| **Address Verification – Real Time** (REST API) | Rows / thousand | 1.40 (first 30K); 0.83 (30K–300K); 0.21 (300K–3M); 0.04 (>3M) |
| **Address Verification – Geo Coding** (add-on) | Rows / thousand | 0.75 (first 30K); 0.19 (30K–300K); 0.05 (300K–3M); 0.023 (>3M) |

Notes:

- **Real-time DQ is expensive by design** (35 IPUs *per million rows*, vs. batch DQ's
  compute-hour basis). Real-time DQ is "optimized for low-latency, **low-volume** use
  cases," and it requires an API/End Point defined in **API Center**. High-volume cleansing
  belongs in batch/compute-hour patterns; real-time is for the last-mile validation call.
- **Address Verification counts one verified (or invalid) address as "one row."** Using the
  verifier asset inside a mapping **also** consumes the mapping's execution-time IPUs, and
  **Geo Coding** enrichment consumes *both* the base verification rate *and* the geo add-on.
  Address content is also subject to third-party **Content Supplier** pass-through terms.

---

## 4.6 Cloud Data Governance & Catalog (CDGC) and Data Access Management

Cataloging/governance is metered mostly on **daily assets stored** (an inventory-style
scalar) plus **compute hours** for the scanners.

| Service | Scalar / Metric | IPU per metric unit (CPDS v39.1) |
|---|---|---|
| **DGC – Catalog** (technical metadata) | Daily Assets Stored / hundred-thousand | **0.83** (first 500K); 0.067 (>500K) |
| **DGC – Governance** (glossary, policies, terms) | Daily Assets Stored / thousand | **0.95** (first 40K); 0.475 (>40K) |
| **DGC – Metadata Record Consumption** (API access to catalog) | API Calls / thousand | **0** (first 100K); 0.32 (>100K) |
| **DGC – Scanner** | Compute Units / hour | **0.32** |
| **DGC – Scanner – Advanced Serverless** | Compute Units / hour | **0.56** |
| **Data Access Management – Policy Pushdown** | Daily Assets Stored / hundred | 0.6 → 0.5 → 0.3 → 0.2 (by tier) |
| **Data Access Management – Queries** | API Calls / thousand | 0.70 (first 400K); 0.50 (>400K) |
| **Data Access Management – Rows Processed** | Rows / million | 0.72 (first 150M) down to 0.13 (>25B) |

Notes:

- **"Daily Assets Stored" is an inventory scalar** — it counts the assets a service holds
  *on a given day*, measured monthly. Catalog cost therefore scales with the **size of your
  metadata estate**, not with how often you query it; the first tranche of API access to the
  catalog (first 100K calls) is even **free (0 IPUs)**.
- **Scanners meter on compute hours** (like CDI), with the usual serverless premium
  (0.32 → 0.56).

---

## 4.7 Marketplace, Integration Hub, and platform/security services

| Service | Scalar / Metric | IPU per metric unit (CPDS v39.1) |
|---|---|---|
| **Data Marketplace** | Daily Assets Stored / hundred daily assets | **0.416** |
| **Integration Hub** (pub/sub across apps) | Events Processed / thousand events | **6.00** (first 10K); 0.50 (10K–100K); 0.02 (>100K) |
| **Secrets Manager Configuration Service** | Daily Connection Definitions | 0.016 → 0.0011 → 0.0006 (by tier) |
| **Customer Managed Key (CMK)** | Org / per 10 IPUs | **2** |
| **Additional Org** (Pre-Release, Sandbox, Sub-Org, Additional Production) | Org / per Org | **6.00** |

Notes:

- **Integration Hub meters on *events*** through its intermediate publish/subscribe storage
  layer — an event is "inbound and outbound data accessing an intermediate storage layer" —
  front-loaded (6 IPUs/1K events) then very cheap at scale (0.02).
- **Data Marketplace meters on the size of the storefront** (data collections + consumer
  orders over a rolling 30-day window), counted as daily assets stored.

---

## 4.8 CLAIRE / CLAIRE GPT

Informatica's AI copilot meters on **queries**, and — importantly — **cascades** into other
services when a query does real work.

| Service | Scalar / Metric | IPU per metric unit (CPDS v39.1) |
|---|---|---|
| **CLAIRE GPT** (natural-language query) | Queries / thousand | **50** |

Notes:

- A natural-language query costs a flat **50 IPUs per 1,000 queries**, *plus* — per the
  cross-service rule — **"if a natural language query triggers use of another eligible Cloud
  Service, IPUs will also be consumed for the other service."** Asking CLAIRE GPT to build
  and run an ELT pipeline therefore consumes CLAIRE query IPUs **and** the CDI/SQL-ELT IPUs
  the pipeline itself burns.
- Informatica recommends using **CDGC** to enrich the metadata CLAIRE GPT reasons over, so
  the catalog investment and the AI investment reinforce each other.
- **CLAIRE** (the underlying always-on AI/ML engine that powers recommendations,
  auto-tuning, classification, and matching across IDMC) is largely embedded in the services
  it accelerates rather than billed as a separate line; its *effects* show up as more
  efficient consumption of the services it optimizes. **`[verify]`** any standalone CLAIRE
  (non-GPT) metering line against the current CPDS.

---

## 4.9 Services that do NOT meter against IPUs

Two important capabilities sit **outside** the IPU pool and are scoped separately — a
frequent source of confusion:

- **Master Data Management (MDM SaaS / Customer 360, Product 360, Supplier 360, Reference
  360)** is subscribed on a **per-record basis** — by **Unconsolidated Records** within a
  **Data Domain** (with storage sized at ~14 KB/record and defined sandbox allowances),
  **not** metered against IPUs. It is a distinct subscription line in the CPDS. (MDM's own
  bundled integration/quality capabilities are usable only in conjunction with the MDM data
  it serves.)
- **Operational Insights** is subscribed **per instance**, requires a compatible product
  (e.g., Data Quality), "is not subscribed separately," and includes a fixed allotment
  (e.g., 10 environments, 30-day retention). It is **not** an IPU scalar.

See [Section 3.2](./03-ipu-consumption-model.md) for how these fit alongside the pool, and
[Section 7 – Side-by-Side Matrix](./07-side-by-side-matrix.md) for the consolidated view.

---

## 4.10 Practical implications for scoping a pool

- **Match pattern to scalar.** Bulk = cheap GB; CDC = row-priced and front-loaded; batch DQ
  = compute hours; real-time DQ/verification = expensive rows. The *architecture choice*
  drives the IPU bill more than raw data size does.
- **Pushdown (SQL ELT) is the strongest efficiency lever.** Moving set-based transformation
  into the target warehouse trades compute-hour IPUs for very low per-row IPUs that fall to
  0.0003/million at scale.
- **Serverless trades IPUs for ops.** Every "Advanced Serverless" variant costs more IPUs
  per unit than its Secure-Agent equivalent, in exchange for zero infrastructure to manage.
- **Tiering rewards concentration.** Almost every rate is tiered downward, so consolidating
  volume into fewer, larger workloads reaches cheaper marginal tiers faster than many small
  ones.
- **Watch the cascades.** CLAIRE GPT queries and any job that borrows another service's
  components bill at the **other** (or the **highest**) applicable rate — model these
  explicitly in an estimate.
- **Re-verify rates.** All numbers here are **CPDS v39.1 (eff. June 5, 2026)**. Confirm
  against the current CPDS and the Informatica **Measurement Guide** before committing
  figures to a customer.

---

## Sources

- Informatica — *Cloud and Product Description Schedule (CPDS)*, **Version 39.1, effective
  June 5, 2026** (PDF). Full IDMC IPU consumption matrix: per-service scalars, metrics, and
  IPU-per-metric-unit rates quoted throughout this section (CDI, Advanced DI, CAI, API
  Center, Application/Database/File/Streaming Ingestion and CDC, DI-CDC, SQL ELT, CDQ and
  Advanced DQ, Data Quality – Real Time, Address Verification & Geo Coding, DGC
  Catalog/Governance/Scanner/Metadata Record Consumption, Data Access Management, Data
  Marketplace, Integration Hub, INFACore, B2B, CLAIRE GPT, Secrets Manager, CMK, Additional
  Org); definitions of Compute Units (min 4 CPU-cores), Rows Processed, Data Volume, API
  Calls, Daily Assets Stored, Events; cross-service "highest applicable rate" and
  natural-language-query rules; MDM SaaS per-Unconsolidated-Record and Operational Insights
  per-instance treatment. Accessed 2026-09-03.
  <https://www.informatica.com/content/dam/informatica-com/en/docs/informatica-cloud-and-product-description-schedule.pdf>
- Informatica — *Cloud Data Integration Pricing* page. "Calculated per scaler … Secure
  Agent, CDI-e, Data Mass Ingestion volume and more"; automatic in-product usage tracking;
  reference to the Informatica **Measurement Guide** for how each scaler is measured.
  Accessed 2026-09-03.
  <https://www.informatica.com/products/cloud-integration/pricing.html>
- Informatica — *Measurement Guide* (referenced; hosted on the Informatica Network for
  members). Cited by the CPDS/pricing page as the authoritative per-scalar computation
  detail. Landing article did not render for anonymous retrieval on 2026-09-03 — **`[verify]`**
  contents via an authenticated Informatica Network session.
  <https://knowledge.informatica.com/s/article/DOC-19140?language=en_US>
