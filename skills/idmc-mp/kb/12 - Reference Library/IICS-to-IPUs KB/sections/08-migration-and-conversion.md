# 8. Migrating from Legacy Licensing to IPUs

> **Audience:** Customers moving from legacy Informatica IICS licensing to the Informatica Intelligent Data Management Cloud (IDMC) **Informatica Processing Unit (IPU)** consumption model, and the account teams who support them.

## 8.1 The most important point: this is a licensing change, not a re-platform

Moving to IPUs is fundamentally a **commercial and contract conversion**, not a technical migration. IICS and IDMC are the **same platform**: what Informatica historically marketed as "Informatica Intelligent Cloud Services (IICS)" is the same cloud-native environment now branded **Intelligent Data Management Cloud (IDMC)**. The public Cloud & Product Description Schedule (CPDS) still points to the IICS Product Availability Matrix (PAM) for regional and ecosystem service availability *inside* its IDMC section, which reflects that the two names describe one platform. [CPDS §IDMC]

What this means in practice:

- **No lift-and-shift.** Your existing org, Secure Agents, connections, mappings, taskflows, and assets stay exactly where they are.
- **No rebuild.** There is no need to re-develop pipelines, re-point connectors, or recreate runtime environments to consume IPUs.
- **What changes is how you are entitled and billed.** Instead of fixed, per-product or per-user entitlements, you subscribe to a **pool of IPUs** — a single, flexible unit of capacity — and draw it down as you use eligible Cloud Services. [CPDS Definitions]

> **IPU, defined:** *"Informatica Processing Unit (IPU) is a unit of capacity that can be used across eligible Cloud Services."* — CPDS, Definitions.

Because the platform does not change, the risk profile of the move is dominated by **estimating and governing consumption**, not by engineering. The rest of this section is a practical playbook for doing exactly that.

## 8.2 How consumption is metered (what you are actually estimating)

Under the IPU model, each eligible Cloud Service draws down IPUs according to a published formula with three parts. Understanding this is the key to a credible estimate. [CPDS §IDMC packaging]

| Element | What it means | Examples from the public CPDS |
|---|---|---|
| **Scalar** | The thing being counted for that service | `Rows Processed`, `Compute Units`, `Org`, data volume, API calls |
| **Metric** | The unit the scalar is measured in | `Per Thousand Rows`, `Per Org` |
| **IPU Per Metric Unit** | How many IPUs each metric unit consumes (often **tiered** so the rate drops at higher volume) | Address Verification – Batch: **1.10** IPU per 1K rows for the first 30K, falling to **0.43 / 0.09 / 0.03** at higher volume tiers |

A few consumption behaviors are important to model up front:

- **Compute-based services** are measured in **Compute Units**, which reflect "the general utilization of processing capacity used or consumed by each respective service" — inputs include CPU-cores (or logical CPU-cores), nodes, outbound API calls, and job duration, with **a minimum of four (4) CPU-cores used to calculate Compute Units**. [CPDS Definitions]
- **Cross-service work is charged at the highest applicable rate.** "If a job or task running in one Cloud Service uses components of another eligible Cloud Service, the Compute Units for that job or task will be calculated based on the highest applicable consumption rate." Natural-language queries that trigger another service consume IPUs for that service too. [CPDS §IDMC]
- **New services are added automatically.** Eligible new Cloud Services "will be automatically activated for customers once released," and can be consumed from the same IPU pool. [Pricing FAQ]

> The full, current per-service scalars, metrics, and IPU rates are published by Informatica in the **CPDS** and the **Measurement Guide** (see Sources). Always price against the current version.

## 8.3 Step-by-step: converting to IPUs

### Step 1 — Frame it as a conversion, and set the team
Confirm internally that the environment does not move. Assemble a small cross-functional group: the Informatica platform owner/admin, a data-engineering lead who knows the pipelines, and a commercial/FinOps or procurement owner. Engage your Informatica account team early — **specific pricing, volume tiers, and commercial terms are provided by Informatica per engagement** and are not derivable from public documents.

### Step 2 — Baseline your current usage
Inventory what you run today so the estimate is grounded in reality, not guesswork:
- **Assets & jobs:** number and type of mappings, mapping tasks, taskflows, replication/ingestion tasks, and their schedules/frequency.
- **Volumes:** rows processed, data volume moved/transformed, records mastered (MDM), addresses verified, API calls, and peak vs. average throughput.
- **Runtime footprint:** Secure Agents, node/CPU-core counts, and how much runs concurrently.
- **Services in use:** Data Integration, Data Quality, Application/API Integration (CAI), Mass Ingestion, MDM SaaS, Data Governance/Catalog, etc.

The IDMC **admin/monitor** and **Operational Insights** surfaces (see §8.5) are the best places to pull this data if you are already on the platform.

### Step 3 — Estimate IPU needs
Map each service you use to its **scalar → metric → IPU-per-metric-unit** formula from the current CPDS/Measurement Guide, apply your baselined volumes (respecting the **tiered rates**), and sum to an annualized IPU figure. Then:
- Add a **growth allowance** for known roadmap (new sources, new pipelines, expanding data volumes).
- Model **peaks**, not just averages — consumption is not perfectly flat month to month.
- Use the **IPU estimator** tooling as an accelerator. Informatica provides estimator/calculator assistance to translate a usage profile into an IPU estimate; work this with your account team so it reflects current rates and your specific service mix. *[verify: exact estimator tool name/availability with your Informatica contact]*

### Step 4 — Right-size the annual commit
Pick a committed IPU pool that covers **steady-state plus reasonable growth**, but resist over-committing "just in case." The model is designed to flex:
- If you **under-commit**, you can add IPUs; sustained overage indicates you should true up (see §8.6).
- If you **over-commit**, you carry capacity you may not use within the term.
- A well-sized commit sits slightly above expected steady-state usage, with overage flexibility absorbing peaks.

### Step 5 — Plan a phased adoption
You do not have to convert everything at once conceptually. A low-risk sequence:
1. Convert commercially to the IPU pool while workloads keep running unchanged.
2. **Watch actual consumption** for one or more full cycles against the estimate.
3. Onboard additional teams/workloads deliberately, watching the meter as each comes on.
4. Re-baseline the commit at renewal using real consumption data.

### Step 6 — Stand up monitoring and governance *before* volume grows
Turn on dashboards, alerts, and access controls (see §8.5 and §8.6) on day one so the first surprise is caught by an alert, not an invoice.

### Worked example — size to the recent trend, not the lifetime average
The single most important sizing lesson. Below is an **illustrative** IDMC account entitled to **300 IPU/month**, showing total IPU consumption across *all* services versus that commit (a typical pattern; the figures are rounded and are not any one customer's):

| Month | Total IPU used | % of 300 commit |
|---|---:|---:|
| Sep | 210 | 70% |
| Nov | 305 | 102% |
| Jan | 30 | 10% |
| Apr | 530 | 177% |
| May | 545 | 182% |
| Jul | 185 | 62% |

- The **12-month average was ≈ 195 IPU (65%)** — but the **recent 3-month average ran ~118–157%**, with a **peak month of 182%**. Dominant draws rotated between **Mass Ingestion (Database)** and **Data Integration**; the shared pool absorbed the swings against the single 300 commit.
- **Interpretation:** this account is **under-committed** — recent months routinely exceed 100%, driving overage. The right move at renewal is to raise the commit toward the **recent-average-plus-headroom** *or* move to **Flex IPU** so the quiet months (10–33%) bankroll the spikes within the annual bucket.
- **Lesson:** size on the **recent trend and the peak**, never the stale lifetime average — the 65% lifetime figure badly understates current need. This is exactly what the pool is designed to absorb, and exactly why the commit must track reality.

## 8.4 How to monitor consumption after conversion

Informatica meters IPU usage automatically and exposes it to you so there are no black boxes:

- **Automatic, in-product tracking.** "Usage is tracked automatically within the product." [Pricing FAQ]
- **Real-time consumption dashboard.** Administrators can "monitor usage via a dashboard" and see consumption in real time. [Pricing FAQ]
- **Threshold alerts.** Admins can "set consumption threshold alerts," and "alerts are sent when specific usage thresholds are reached." [Pricing FAQ]
- **Per-service access control.** Admins can "control which user has access to each service," which is a direct lever for capping where IPUs can be spent. [Pricing FAQ]

### Operational Insights and the admin/monitor surfaces
- **Operational Insights** is Informatica's monitoring surface for the platform — it provides visibility into Secure Agent health, job execution, and usage/consumption trends across the org, which makes it a natural home for consumption tracking and capacity planning. *[verify current Operational Insights consumption/metering feature set against docs.informatica.com — the docs portal was not directly retrievable at time of writing]*
- The **IDMC Administrator / Monitor** consoles expose organization-level metering and consumption reporting, letting you attribute usage by service and drill into what is driving draw-down. *[verify exact report/menu names in your org's current release]*

## 8.5 FinOps and governance practices to avoid overage surprises

Treat IPUs like any other consumption-based cloud spend:

- **Assign an owner.** A named FinOps/platform owner watches the consumption dashboard on a regular cadence (weekly early on).
- **Set alerts at multiple thresholds** (e.g., early-warning and near-limit) rather than a single ceiling.
- **Attribute consumption** to teams/workloads so runaway jobs are traceable to a source.
- **Right-size runtimes.** Because compute is metered with a **4-core minimum**, oversized or idle agents and unnecessary concurrency inflate Compute Units. Consolidate and schedule deliberately.
- **Optimize the heavy hitters.** Inefficient mappings, full reloads where incremental would do, and chatty API patterns all consume IPUs; tuning them is direct savings.
- **Hold periodic consumption reviews.** Informatica offers **IDMC Overage Protection**, which lets Informatica and the customer "meet quarterly to review Customer's IPU consumption rate and ensure Customer is properly subscribed for IPUs on a go-forward basis," with the stated purpose of helping the customer "optimize the efficiency of its IPU consumption to avoid unforeseen fees." [CPDS §IDMC – Overage Protection]
- **Re-baseline at renewal** using actual metered consumption, not the original estimate.

## 8.6 What happens if you exceed the commit

Overage is a managed, contractual event, not a service interruption:

> *"Informatica monitors Customer's consumption for overages. If Customer's consumption exceeds its subscribed number of IPUs, Customer must subscribe to additional IPUs for the remainder of the Subscription Period."* — CPDS §IDMC

If consumption exceeds the subscribed IPUs, the **overage fee set forth in the Order** for additional consumption applies. [CPDS p.30] For customers with variable or spiky workloads, **IDMC Overage Protection** exists specifically to give "flexibility in resolving unplanned increases/peaks in … IPU monthly consumption levels." [CPDS §IDMC – Overage Protection] The specific overage rate and any protection terms are set in your Order — discuss them with your account team.

## 8.7 Common pitfalls and how to de-risk

| Pitfall | Why it happens | De-risking move |
|---|---|---|
| **Treating it as a technical migration** | Assumes pipelines must be rebuilt | Confirm early: same platform, no re-platform (§8.1) |
| **Estimating on averages only** | Ignores monthly peaks | Model peak consumption and add a growth buffer (§8.3) |
| **Over-committing "to be safe"** | Fear of overage | Right-size to steady-state + growth; let overage flexibility absorb peaks (§8.4) |
| **Under-committing without monitoring** | No visibility into draw-down | Turn on the dashboard + threshold alerts before scaling (§8.4) |
| **No consumption owner** | "Everyone/no one" watches spend | Assign a FinOps owner and a review cadence (§8.5) |
| **Idle/oversized Secure Agents** | 4-core minimum inflates Compute Units | Consolidate agents; schedule and tune workloads (§8.5) |
| **Pricing against a stale schedule** | CPDS/rates change by version | Always estimate against the current CPDS/Measurement Guide (§8.2) |
| **Guessing at commercial terms** | Public docs omit pricing/discounts | Get pricing, tiers, and terms from your Informatica account team |
| **Assuming MDM "includes" CDI/CDQ for general use** | MDM SaaS bundles a slice of CDI/CDQ/ingestion/CAI/Address, but **only where MDM is the source or target** of the data (CPDS v39.1) | Size general-purpose integration/quality that does *not* touch MDM from your **separate IPU pool** — don't assume it's covered by the MDM subscription |
| **Forgetting Data Quality runs *inside* a CDI mapping** | DQ assets (cleanse, parse, dedupe, match, verify) execute as transformations within a Cloud Data Integration mapping/taskflow — DQ is not a standalone runtime | Budget CDI entitlement/skills alongside DQ; and remember the **highest-applicable-rate rule** (§8.2) re-rates the whole mapping at the DQ rate |

## 8.8 Quick checklist

- [ ] Confirmed the move is a licensing conversion (no re-platform)
- [ ] Baselined current assets, volumes, runtimes, and services
- [ ] Mapped each service to its scalar/metric/IPU rate and produced an annualized estimate
- [ ] Added growth + peak buffers; validated with the IPU estimator and account team
- [ ] Right-sized the committed IPU pool
- [ ] Enabled the consumption dashboard, threshold alerts, and per-service access controls
- [ ] Assigned a FinOps owner and set a review cadence (consider Overage Protection)
- [ ] Planned a phased onboarding and a renewal re-baseline

---

## Sources

- **Informatica — Pricing (IDMC / IPU pricing model & FAQ).** Consumption-based pricing; IPUs give access to all eligible Cloud Services; consumption calculated per scaler (Secure Agent, CDI-e, Data Mass Ingestion volume, and more); usage tracked automatically; real-time dashboard; consumption threshold alerts; per-service access control; new services auto-activated. https://www.informatica.com/products/cloud-integration/pricing.html (accessed 2026-09-03)
- **Informatica — Cloud & Product Description Schedule (CPDS), v39.1 (Informatica from Salesforce), effective June 5, 2026.** IPU definition ("a unit of capacity that can be used across eligible Cloud Services"); IDMC packaging with per-service Scalar/Metric/IPU-Per-Metric-Unit and tiered rates (e.g., Address Verification – Batch); Compute Units definition and 4-CPU-core minimum; highest-applicable-rate rule for cross-service jobs; overage handling ("must subscribe to additional IPUs for the remainder of the Subscription Period"; overage fee per Order); IDMC – Overage Protection (quarterly consumption reviews); Flex IPU definition; Subscription Period definition; IICS PAM referenced within the IDMC section. https://www.informatica.com/content/dam/informatica-com/en/docs/informatica-cloud-and-product-description-schedule.pdf (accessed 2026-09-03)
- **Informatica — Measurement Guide (referenced by the pricing page; login-gated Knowledge Base article DOC-19140).** Detailed per-scaler measurement methodology. https://knowledge.informatica.com/s/article/DOC-19140 (referenced 2026-09-03; content behind authentication)
- **Informatica — Intelligent Data Management Cloud (product page).** IDMC described as a unified cloud-native data management platform with consumption-based pricing ("Pay only for what you use"). https://www.informatica.com/products/intelligent-data-management-cloud.html (accessed 2026-09-03)
