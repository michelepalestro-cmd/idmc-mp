# 6. What the IPU Model Unlocks

The **Informatica Processing Unit (IPU)** consumption model replaces siloed, per-service subscriptions with a **single pool of consumption** that can be spent across the Informatica Intelligent Data Management Cloud (IDMC) portfolio. Instead of buying fixed capacity for one service at a time, you commit to a pool of IPUs and draw against it as you use eligible services — metered **per scaler, based on the scaler's usage** (for example Secure Agent, CDI-e / elastic compute, Data Mass Ingestion volume, and more).

This one structural change — **one flexible unit, one pool, one platform** — is what unlocks everything below.

> Framing note: This section describes the **benefits and how they resolve** each legacy constraint. The underlying constraints themselves are detailed in Section 5.

---

## 6.1 Access to the full portfolio from one pool

A single IPU pool provides **access to all eligible cloud services** across IDMC — Data Integration, Data Quality & Observability, Application/API Integration, Data Catalog, Data Marketplace, Governance/Access/Privacy, and MDM & 360 Applications. The breadth of the platform is available to you by default; you draw on whichever services a given initiative requires.

**What this unlocks**
- Cross-functional initiatives (for example, a trusted-customer-view program that needs integration **and** quality **and** MDM) can proceed as one project rather than waiting on multiple separate purchases.
- Teams design around the **best capability for the job**, not around the narrow subset that happened to be licensed.
- MDM remains available, accessed on a **per-domain records basis** alongside the IPU pool.

---

## 6.2 Try and adopt any service with no new SKU

Because eligible services all draw from the same pool, adopting a new capability is a **turn-it-on** decision rather than a **buy-a-new-SKU** decision. Customers can **swap for new services as needed** and **test new applications and address different use cases with ease**, and **all eligible new services are automatically activated once released**.

**What this unlocks**
- The cost of experimentation drops to near zero: a team can pilot data quality, cataloging, or governance to validate value before scaling it up.
- New platform capabilities become available **automatically** as Informatica ships them — no amendment required to gain access to what has been released.
- Innovation is bounded by imagination and delivery speed, not by the shape of a contract signed months earlier.

---

## 6.3 Elasticity and scale on demand

Consumption flexes with real usage. You **pay for what you need now and scale for the future**, drawing more from the pool during peaks and less during quiet periods rather than sizing and paying for a fixed peak tier that sits idle the rest of the time.

**What this unlocks**
- Bursty and seasonal workloads (month-end close, a one-time migration, a campaign) are absorbed without a procurement cycle.
- Growth is no longer punished: a successful project scales by consuming more of an existing pool, not by triggering a new purchase.
- Because the pool is shared, capacity effectively **follows the work** — surplus that a subscription model would strand can instead fund the next priority.

---

## 6.4 Serverless runtime and advanced pushdown optimization

The IPU model meters modern, on-demand runtime options as scalers, so customers can use them as needed. Cloud Data Integration offers **ETL, ELT, Spark, or a fully managed serverless option**, and CDI-Elastic provides **elastic compute clusters** with a **serverless Spark engine with dynamic scaling and auto-tuning** that **scales up or down based on the workload and shuts down when processing is complete** — which **eliminates server management** and **allows for consumption-based pricing**. **Pushdown optimization** pushes transformation logic down for efficient processing in the target data ecosystem.

**What this unlocks**
- **Capacity on demand**: heavy processing spins up elastic/serverless compute and then shuts down, so you pay for the run, not for idle infrastructure.
- **Lower operational overhead**: no servers to manage; the runtime auto-tunes and self-scales.
- **Efficiency at the source/target**: pushdown/ELT executes work where the data lives, reducing data movement and improving throughput.

> [verify] The specific branding "ecosystem pushdown," and whether a given runtime option (serverless/elastic, advanced pushdown) is available under a customer's particular legacy entitlement, depend on current offering terms and the customer's agreement.

---

## 6.5 CLAIRE AI across services

**CLAIRE**, Informatica's enterprise AI engine, runs **seamlessly within IDMC** and is **built on deep metadata insight, ensuring accurate and trusted outputs, not guesswork**. It spans applicable IDMC services (and MDM SaaS) in three forms:

- **CLAIRE GPT** — a conversational assistant that lets employees **converse with your data in natural language** to discover, analyze, and execute tasks (positioned to **turn every employee into a data expert**).
- **CLAIRE Copilot** — in-workflow guidance for data professionals, with **no tool switching required**.
- **CLAIRE Agents** — autonomous agents that **independently plan and reason to solve complex data challenges**, discovering data, building pipelines, and proactively fixing data-quality issues.

Informatica cites CLAIRE-driven automation reducing **data-wrangling time by up to ~90%**, with CLAIRE Copilot automating integration-pipeline development. *(Vendor-published estimate; actual results vary by workload.)*

**What this unlocks**
- AI-assisted automation and recommendations reduce manual effort and **democratize data access** across the platform, not just within one licensed service.
- Natural-language and copilot experiences lower the skill barrier, so more of the workforce can be productive with data.
- Because CLAIRE is metadata-driven and platform-wide, its intelligence compounds as more services feed the shared metadata foundation.

> Availability of CLAIRE generative/headless features depends on deployment to a compatible POD; an at-no-additional-cost promotional period for certain CLAIRE generative and headless pre-run-time design activities was referenced through January 31, 2027.

---

## 6.6 Faster time-to-value and low-friction innovation adoption

Low- and no-cost on-ramps make it easy to start and to expand. Informatica offers **Data Loader – Free** and **Cloud Data Integration – Free** (self-service **GET STARTED** signup; the free CDI tier provides up to **20M rows / 10 compute hours per month** with unlimited users), described as lowering **the barriers to get started with data integration** and letting teams **begin moving their data to the cloud without committing to software costs**, while the ability to scale up **minimizes risks from the trial and adoption of these products**.

**What this unlocks**
- Teams can prove value first and commit second, compressing the path from idea to production.
- Adoption of new capabilities is continuous rather than episodic, because there is no procurement gate between "we should try this" and "we are using it."
- Time-to-value is governed by how fast the team can build — not by contract lead times.

---

## 6.7 Simplified procurement — one contract, one unit

Instead of negotiating and tracking many independent service subscriptions, customers commit to a **single consumption unit (the IPU) under one arrangement**. New eligible services are **included and automatically activated** as they are released, so the entitlement keeps pace with the platform without a stream of amendments.

**What this unlocks**
- Dramatically fewer moving parts: one unit and one pool to reason about instead of a patchwork of per-service SKUs and tiers.
- Renewals and expansions become simpler and less contentious, because spend is expressed in a single, comparable unit.
- Reduced **training, maintenance, and procurement costs** from running multiple services together on one platform (Informatica cites Nucleus Research figures including a **413%** average ROI and **$1.08 million** in maintenance/administration savings).

---

## 6.8 FinOps visibility into consumption

The consumption model is instrumented for cost governance. Usage is **tracked automatically within the product**; a dashboard lets customers **view their own usage in real time**; and administrators can **set consumption threshold alerts to ensure cost containment**, with **alerts sent when specific usage thresholds are reached**. Consumption is transparent because it is metered **per scaler, based on the scaler's usage**.

**What this unlocks**
- Real-time cost transparency: teams see what they are consuming and where, and can **track usage to maximize ROI (FinOps)**.
- Proactive control: threshold alerts prevent surprises and keep spend inside plan.
- Better decisions: because capacity is fungible across services, FinOps insight directly informs where to direct the shared pool next.

---

## Summary: Legacy limitation → IPU-model resolution

| Legacy IICS limitation (Section 5) | IPU-model resolution |
|------------------------------------|----------------------|
| Only licensed services are usable; others need a new SKU | **Full portfolio from one pool** — all eligible services accessible; MDM on a per-domain records basis (6.1) |
| Fixed connector entitlements gate new sources/targets | Connectors remain a **tier-based subscription** (Tier A included; Tier B/C/D per End Point) and are **not** funded from the IPU pool; what changes is that the *services* using them draw from one pool, so adding a new source/target no longer requires a new **service** SKU *(CPDS v39.1, pp. 7, 28)* (6.1, 6.2) |
| Per-service capacity ceilings; more = new purchase | **Elasticity and scale on demand** — draw more/less from the pool; absorb peaks without a procurement cycle (6.3) |
| Capacity siloed; surplus cannot fund another need | **One shared pool** — spend follows the work; no stranded capacity (6.1, 6.3) |
| Adopting a new capability requires a new contract | **Try/adopt any service with no new SKU** — swap freely; new services auto-activated on release (6.2) |
| Limited access to newer capabilities | **Serverless & advanced pushdown, CLAIRE AI across services**, Free & PayGo on-ramps available via the platform (6.4, 6.5, 6.6) |
| High friction and slow time-to-value | **Faster time-to-value** — free/low-cost on-ramps; prove value first, commit second (6.6) |
| Fragmented, multi-SKU procurement | **Simplified procurement** — one contract, one unit; auto-included new services (6.7) |
| Shelfware you pay for but cannot reallocate | **FinOps visibility** + fungible pool — real-time usage, threshold alerts, redeploy spend to value (6.8) |

---

## Sources

- Informatica — Cloud Data Integration Pricing (IPU / consumption model; single pool for all eligible services; per-scaler metering incl. Secure Agent, CDI-e, Data Mass Ingestion; swap/test new services; auto-activation of new services; real-time usage dashboard and consumption threshold alerts; FinOps; MDM per-domain records; Nucleus Research ROI/savings): https://www.informatica.com/products/cloud-integration/pricing.html
- Informatica — Intelligent Data Management Cloud (IDMC) platform (unified cloud-native platform; portfolio incl. Data Integration, Quality & Observability, Application Integration, Catalog, Marketplace, Governance, MDM/360, CLAIRE AI/GPT): https://www.informatica.com/products/intelligent-data-management-cloud.html
- Informatica — CLAIRE AI (metadata-driven AI engine within IDMC; CLAIRE GPT, Copilot, Agents; spans applicable IDMC services and MDM SaaS; promotional terms through Jan 31, 2027): https://www.informatica.com/platform/claire-ai.html
- Informatica — Cloud Data Integration product page (ETL/ELT/Spark/fully managed serverless; consumption-based pricing; intelligent optimization engine for automated cost control): https://www.informatica.com/products/cloud-data-integration.html
- Informatica — "What is Cloud Data Integration?" (serverless/elastic compute clusters that scale and shut down; serverless Spark with dynamic scaling and auto-tuning; pushdown optimization): https://www.informatica.com/resources/articles/what-is-cloud-data-integration.html
- Informatica — Free Cloud Data Integration & Data Loader (Data Loader – Free and CDI – Free tiers; up to 20M rows / 10 compute hours per month; self-service signup; lowers barriers, minimizes trial/adoption risk): https://www.informatica.com/free-data-integration.html
