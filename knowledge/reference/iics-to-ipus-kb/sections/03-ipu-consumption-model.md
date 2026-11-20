# 3. The IDMC IPU Consumption Model

The single biggest change moving from legacy IICS licensing to the **Informatica
Intelligent Data Management Cloud (IDMC)** is *how you buy and how you pay*. Legacy IICS
was licensed as a set of **separate, fixed subscriptions** — you bought a specific edition
of a specific service (Data Integration, Data Quality, API Management, and so on), each
with its own tier, its own entitlements, and its own connector packs. IDMC replaces that
with **one flexible, consumption-based pool** measured in **Informatica Processing Units
(IPUs)**. This section defines the IPU precisely, explains the universal-credit concept,
and contrasts it with the old "buy fixed capacity per service" approach.

---

## 3.1 What an IPU is

> **Informatica Processing Unit (IPU)** — "a unit of capacity that can be used across
> eligible Cloud Services."
> — *Informatica Cloud and Product Description Schedule (CPDS), v39.1*

That one sentence carries the whole idea. An IPU is **not** a license for a particular
product and it is **not** a seat, a server, or a connector. It is a **generic, fungible
unit of consumption** — a credit — that you spend as you actually *use* the platform.
Informatica sometimes renders the acronym as "Informatica Processing Unit" and, in some
commercial materials, "Informatica Pricing Unit"; the meaning is the same: a universal
consumption credit that "give[s] customers access to all eligible cloud services listed in
the Cloud and Product Description Schedule."

Key properties of an IPU:

- **Universal.** The same IPU can be spent on data integration one day and data quality,
  cataloging, ingestion, or API calls the next. It is not pre-committed to any one service.
- **Metered, not seat-based.** You are billed for the *work performed* (compute hours,
  rows, gigabytes, API calls, etc.), not for how many people are logged in or how many
  copies of a product you installed.
- **Rate-based per service.** Each eligible service draws down IPUs at a **published
  per-service rate** (the "IPU per metric unit" in the consumption matrix). A compute-hour
  of standard Data Integration and a gigabyte of database ingestion cost *different*
  numbers of IPUs — see [Section 4](04-ipu-metering-by-service.md).

> **Note on dollar pricing.** The CPDS publishes the *consumption rates* (how many IPUs a
> unit of work costs) but **not** the dollar price of an IPU itself. The per-IPU price is
> set in the customer's Order/quote and is not published in the CPDS. This KB therefore
> never states a per-IPU dollar figure. **`[verify]`** any dollar-per-IPU number against
> the customer's own Order.

---

## 3.2 One pool, spendable across the entire portfolio

Under IICS you sized each product independently and hoped you guessed right: too much Data
Quality and not enough Data Integration meant stranded spend on one and a blocking
shortage on the other. IDMC collapses those separate buckets into **one shared pool of
IPUs** that any eligible service can draw from.

- **One contract, one pool.** You subscribe to a quantity of IPUs, and consumption
  pricing "enables you to pay for what you need now and scale for the future," with the
  ability to "swap for new services as needed."
- **Spend where the work is.** IPUs "may be applied against Cloud Services" as you use
  them. If this quarter's project is heavy on mass ingestion and light on cataloging, the
  pool naturally flows that way; next quarter it can flow the other way — with **no
  re-contracting** and no per-service true-up.
- **Access to the whole eligible portfolio.** The subscription grants access to *all*
  eligible services in the IDMC consumption matrix, not a hand-picked few. Services span
  Cloud Data Integration (CDI), Cloud Application Integration (CAI), Data Ingestion &
  Replication (application, database/CDC, file, streaming), Cloud Data Quality (CDQ),
  Cloud Data Governance & Catalog (CDGC), Data Marketplace, API Center / API Management,
  Integration Hub, INFACore, and CLAIRE GPT, among others.
- **New services are added automatically.** The subscription "includes updates to the IDMC
  matrix during the applicable Subscription Period, such as inclusion of additional Cloud
  Services" — newly released eligible services "will be automatically activated for
  customers once released." You do not sign a new deal to try a newly launched capability;
  you simply start consuming IPUs against it.
- **Pool spans your orgs.** You "may use any eligible Cloud Services in the matrix above
  across all their Orgs/Sub-orgs as long as the total aggregated IPUs consumed across all
  Orgs do not exceed the subscribed quantity." The pool is measured in aggregate, not
  fenced per environment.

A few things sit **outside** the IPU pool by design. **Master Data Management (MDM SaaS /
Customer 360, Product 360, Supplier 360, Reference 360)** is subscribed **separately on a
per-record basis** (per *Unconsolidated Record*, by Data Domain), not metered against IPUs.
**Operational Insights** is subscribed **per instance** and requires a compatible product.
Some premium connectors and Data-as-a-Service content also carry their own terms. These
distinctions matter for scoping and are detailed in
[Section 4](04-ipu-metering-by-service.md).

---

## 3.3 How consumption is measured

Consumption is **metered automatically inside the platform** and drawn down from your pool
as jobs run.

- **Per "scalar," by usage.** IPU consumption "is calculated per scaler, based on the
  scaler's usage including Secure Agent, CDI-e, Data Mass Ingestion volume and more." A
  *scalar* (scaler) is simply the thing being counted for a given service — compute hours,
  rows processed, gigabytes of data volume, API calls, daily assets stored, events, or
  queries. Each service definition names its scalar and its metric (see the full matrix in
  [Section 4](04-ipu-metering-by-service.md)).
- **Measured monthly.** "All scalars and IPU consumption will be measured on a monthly
  basis."
- **Tracked automatically, with alerts.** Usage "is tracked automatically within the
  product." A real-time dashboard lets customers "view their own usage," administrators can
  "control which user has access to each service," and "alerts are sent when specific usage
  thresholds are reached" (you can "set consumption threshold alerts"). This gives the pool
  a built-in **FinOps** control loop — you can watch draw-down and act before you overrun.
- **Cross-service rules.** Two rules prevent double-dipping and gaming:
  - If a **natural-language query** (e.g., CLAIRE GPT) "triggers use of another eligible
    Cloud Service, IPUs will also be consumed for the other service."
  - Otherwise, if a job "running in one Cloud Service uses components of another eligible
    Cloud Service, the Compute Units for that job or task will be calculated based on **the
    highest applicable consumption rate**."
- **What a "Compute Unit" actually measures.** For compute-metered services, a *Compute
  Unit* measures "the general utilization of processing capacity" — inputs include
  processing power, transformation work, the number of physical or logical CPU-cores
  assigned to a job, nodes, outbound API calls, and job duration. Note a **minimum of four
  (4) CPU-cores (or logical CPU-cores) is used to calculate Compute Units.**

---

## 3.4 Committed pool vs. Flex vs. pay-as-you-go on-ramp

Informatica offers the IPU model in more than one commercial shape. The **metering is the
same**; what differs is the *time window* over which your commitment is measured and how
overage is handled.

| Model | Commitment window | Carry-over | Overage handling |
|---|---|---|---|
| **IDMC – IPU** | Monthly: consume the subscribed IPUs "across a monthly period" | IPUs **do not** carry over to the next month | If consumption exceeds the subscribed number, customer must subscribe to additional IPUs for the remainder of the term |
| **IDMC – Flex IPU** | Annual: consume the subscribed IPUs "across an annual period" | IPUs **do not** carry over to the next annual period | Overage fee (set in the Order) applies to additional consumption |
| **IDMC – Unlimited / Unlimited Flex IPU** | Customer "is not subscribing to a specific maximum quantity of IPUs" | n/a | n/a |

Two related commercial constructs are worth knowing (details, without deal-specific
numbers, live in [Section 9 – Commercial Model](09-commercial-model.md)):

- **Overage Protection** is an option that pairs with the monthly **IDMC – IPU** model. It
  triggers a joint review when consumption exceeds the subscribed quantity "by up to 25% in
  any two (2) consecutive months or any three (3) out of five (5) months, or by 100% in any
  one (1) month," so the customer can right-size the subscription. It does **not** apply to
  Flex IPU.
- **Free / pay-as-you-go on-ramp.** Before or alongside a committed pool, Informatica
  offers no-cost entry points: **Cloud Data Loader – Free** (unlimited rows/users,
  community support) and **Cloud Data Integration – Free** (up to **20M rows / 10 compute
  hours per month**, unlimited users, community + live chat). These let teams start moving
  data at zero cost and graduate to consumption-priced IDMC when they need enterprise
  capabilities. A true metered "PayGo" motion (pay per consumption via card, no annual
  commit) is positioned as part of this on-ramp; specific PayGo billing mechanics should be
  **`[verify]`**'d against a live Informatica pricing page.

---

## 3.5 How this differs from buying fixed per-service capacity

The mental model shift is the whole point of the migration:

| | **Legacy IICS (fixed per-service)** | **IDMC IPU (one consumption pool)** |
|---|---|---|
| **What you buy** | A tier/edition of each specific service, separately | One pool of IPUs |
| **Where spend can go** | Locked to the service you licensed | Any eligible service, shifted freely |
| **Adding a capability** | New SKU / new subscription / new negotiation | Already accessible; just start consuming |
| **New product releases** | Not included until purchased | Auto-added to the matrix during the term |
| **Risk of mis-sizing** | Strand spend on one service, run short on another | Pool absorbs the mix; only total matters |
| **Basis of the bill** | Fixed entitlement, largely regardless of use | Actual work performed, metered monthly |
| **Cost visibility** | Per-contract, static | Real-time usage dashboard + threshold alerts |

In short: IICS made you **predict** your needs product-by-product and pay for that
prediction. IDMC lets you **commit once to a pool** and then **spend it wherever the work
actually is**, with the platform metering every job and giving you the telemetry to manage
the draw-down. That flexibility — plus automatic access to every new service Informatica
ships — is the core commercial advantage of the IPU model, and it is why understanding
*how each service meters* (next section) is essential to scoping and governing a pool well.

---

## Sources

- Informatica — *Cloud and Product Description Schedule (CPDS)*, **Version 39.1, effective
  June 5, 2026** (PDF). Definitions of IPU ("a unit of capacity that can be used across
  eligible Cloud Services"), Compute Units, scalars/metrics; monthly IPU vs. annual Flex
  IPU rules; carry-over and overage; Overage Protection thresholds; cross-service
  (highest-rate) and natural-language rules; MDM SaaS per-record and Operational Insights
  per-instance treatment. Accessed 2026-09-03.
  <https://www.informatica.com/content/dam/informatica-com/en/docs/informatica-cloud-and-product-description-schedule.pdf>
- Informatica — *Cloud Data Integration Pricing* page. IPU/consumption-pricing narrative;
  "calculated per scaler … Secure Agent, CDI-e, Data Mass Ingestion volume and more";
  automatic in-product tracking, usage dashboard, and threshold alerts; MDM offered
  separately per-domain records; new eligible services auto-activated. Accessed 2026-09-03.
  <https://www.informatica.com/products/cloud-integration/pricing.html>
- Informatica — *Cloud Data Integration* product page. Consumption-based pricing ("pay only
  for what you use"), FinOps cost optimization. Accessed 2026-09-03.
  <https://www.informatica.com/products/cloud-data-integration.html>
- Informatica — *Free Cloud Data Integration*. Data Loader – Free (unlimited) and CDI –
  Free (up to 20M rows / 10 compute hours per month) on-ramps; IDMC uses consumption
  pricing. Accessed 2026-09-03.
  <https://www.informatica.com/free-data-integration.html>
