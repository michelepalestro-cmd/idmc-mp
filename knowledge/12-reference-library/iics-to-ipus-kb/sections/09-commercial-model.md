# 9. The Commercial Model (Customer View)

> **Scope note:** This section explains the **IPU commercial model at a customer-shareable level** using publicly published Informatica sources. **Specific pricing, dollar-per-IPU figures, and volume discounts are provided by Informatica per engagement and are intentionally out of scope for this document.** No pricing figures are invented here.

## 9.1 One unit for everything: the IPU

The Informatica Intelligent Data Management Cloud (IDMC) is priced with a single consumption currency — the **Informatica Processing Unit (IPU)**.

> *"Informatica Processing Unit (IPU) is a unit of capacity that can be used across eligible Cloud Services."* — CPDS, Definitions

The defining characteristic is **fungibility across the platform**: one IPU pool funds *whatever mix of eligible services you actually use*. Data Integration, Data Quality, Application/API Integration, Mass Ingestion, MDM, Data Governance and Catalog, and other eligible services all draw down from the same pool. As Informatica states, IPUs "give customers access to all eligible cloud services listed in the Cloud and Product Description Schedule," and eligible **new services are automatically activated once released** — so your entitlement grows with the platform without a new SKU each time. [Pricing FAQ]

This replaces the older world of separate, fixed entitlements per product or per user with **one flexible, consumption-based currency**.

## 9.2 How you buy: a committed pool for the subscription term

The model is a classic **committed-consumption** arrangement:

1. **You subscribe to a pool of IPUs** for the **Subscription Period** — *"the term duration of an Order"* (commonly annual; the exact term is set in your Order). [CPDS Definitions]
2. **You draw the pool down as you consume** eligible services. Each service meters usage and deducts IPUs from the pool according to its published formula (see §9.3).
3. **You track drawdown in real time** through the in-product consumption dashboard and alerts (covered in Section 8), so you always know how much of the pool remains.

Because the pool is universal, you are not forced to predict *which* services you will need in what proportion — only your **overall** consumption. If your usage shifts from, say, batch integration toward more data-quality or ingestion work, the same IPUs simply flow to where the work happens.

## 9.3 How consumption is priced across services

Even though there is one currency, different services consume IPUs at different rates that reflect the work they do. Informatica publishes, per service, a **Scalar** (what is counted), a **Metric** (the unit), and an **IPU Per Metric Unit** rate (how many IPUs each unit costs) — and the rate is frequently **tiered so it decreases at higher volumes**. [CPDS §IDMC]

Illustrative (publicly published) example:

| Service | Scalar | Metric | IPU per metric unit (tiered) |
|---|---|---|---|
| Address Verification – Batch | Rows Processed | Per Thousand Rows | 1.10 (first 30K) → 0.43 (30K–300K) → 0.09 (300K–3M) → 0.03 (>3M) |

Compute-heavy services are metered in **Compute Units**, reflecting "the general utilization of processing capacity used or consumed by each respective service" (CPU-cores, nodes, job duration, etc.), with a **4-CPU-core minimum** used in the calculation. [CPDS Definitions] When a job in one service uses another eligible service, the charge is calculated at the **highest applicable consumption rate**. [CPDS §IDMC]

> The complete, current per-service rates live in the public **CPDS** and the **Measurement Guide** (see Sources). Use them, at their current version, for any real estimate.

## 9.4 Under-consuming vs. over-consuming

The commit sets your baseline; the model then handles both directions.

**If you consume less than your commit (under-consume):**
- You have paid for a committed pool sized to your expected usage. Leftover headroom generally reflects capacity you reserved but did not use within the term.
- The practical remedy is **right-sizing at renewal** using your actual metered consumption, rather than carrying an oversized commit forward. (Any true-down or carryover behavior is a commercial matter set in your Order — confirm with your account team.) *[verify carryover/rollover terms per Order]*

**If you consume more than your commit (over-consume / overage):**
> *"Informatica monitors Customer's consumption for overages. If Customer's consumption exceeds its subscribed number of IPUs, Customer must subscribe to additional IPUs for the remainder of the Subscription Period."* — CPDS §IDMC

- Overage does **not** stop your jobs; it is handled commercially. The **overage fee set forth in the Order** applies to the additional consumption. [CPDS p.30]
- For workloads with unplanned peaks, Informatica offers **IDMC – Overage Protection**, which provides "flexibility in resolving unplanned increases/peaks in … IPU monthly consumption levels" and sets up **quarterly reviews** to keep the customer "properly subscribed for IPUs on a go-forward basis" and to "optimize the efficiency of its IPU consumption to avoid unforeseen fees." [CPDS §IDMC – Overage Protection]

## 9.5 Predictability vs. flexibility — the core tradeoff

The IPU model lets you tune where you sit on a spectrum:

| | More predictability | More flexibility |
|---|---|---|
| **Approach** | Commit a pool sized to steady-state + growth; govern tightly | Commit lean and lean on overage/peak mechanisms — or use a **Flex IPU** arrangement |
| **What you get** | A budget you can plan around; fewer surprises | Ability to absorb spikes and new workloads without re-contracting each time |
| **Watch-outs** | Over-committing ties up capacity you may not use | Uncontrolled draw-down can lead to overage fees |

Informatica also defines a **Flex IPU** option, where "the Customer is not subscribing to a specific maximum quantity of IPUs during the Subscription Period" — maximizing flexibility for organizations that prefer not to fix a ceiling. [CPDS Definitions]

**The balanced posture** most customers aim for: commit to a pool slightly above expected steady-state usage, use overage/peak flexibility to absorb the spikes, monitor consumption continuously, and re-baseline the commit at renewal.

## 9.6 Why customers move to this model

- **One currency, all services** — no per-product/per-user entitlement juggling; usage flows to where the work is.
- **Pay for what you use** — "flexible, consumption-based pricing" that lets you "pay for what you need now and scale for the future." [Pricing page]
- **Automatic access to new services** — eligible new capabilities are activated as they release, from the same pool. [Pricing FAQ]
- **Built-in visibility** — automatic usage tracking, a real-time dashboard, and threshold alerts keep spend transparent (see Section 8). [Pricing FAQ]

## 9.7 What is intentionally NOT in this document

To keep this shareable and accurate:

- **No dollar-per-IPU price.** The cost of an IPU is set commercially and is not published here.
- **No volume discounts or deal-specific percentages.** These are provided by Informatica per engagement.
- **No overage or Flex/Overage-Protection rates.** These are set in your **Order**.

For all of the above, and for a firm quote sized to your baselined usage (see Section 8), **engage your Informatica account team.** The public per-service consumption rates (scalars/metrics/IPU-per-metric-unit) that describe *how services meter* are available in the CPDS and Measurement Guide cited below.

---

## Sources

- **Informatica — Pricing (IDMC / IPU pricing model & FAQ).** Flexible, consumption-based pricing; "pay for what you need now and scale for the future"; IPUs give access to all eligible Cloud Services; new services auto-activated; usage tracked automatically with a real-time dashboard and consumption threshold alerts. https://www.informatica.com/products/cloud-integration/pricing.html (accessed 2026-09-03)
- **Informatica — Cloud & Product Description Schedule (CPDS), v39.1 (Informatica from Salesforce), effective June 5, 2026.** IPU definition; Subscription Period definition; per-service Scalar/Metric/IPU-Per-Metric-Unit with tiered rates (Address Verification – Batch example); Compute Units definition and 4-CPU-core minimum; highest-applicable-rate rule; overage handling and overage fee per Order; IDMC – Overage Protection (quarterly reviews); Flex IPU definition. https://www.informatica.com/content/dam/informatica-com/en/docs/informatica-cloud-and-product-description-schedule.pdf (accessed 2026-09-03)
- **Informatica — Measurement Guide (referenced by the pricing page; login-gated Knowledge Base article DOC-19140).** Per-scaler measurement methodology. https://knowledge.informatica.com/s/article/DOC-19140 (referenced 2026-09-03; content behind authentication)
- **Informatica — Intelligent Data Management Cloud (product page).** Unified cloud-native platform; consumption-based pricing ("Pay only for what you use"). https://www.informatica.com/products/intelligent-data-management-cloud.html (accessed 2026-09-03)
