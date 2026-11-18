# IICS to IPUs — Knowledge Base

*Customer-facing • Built from the modular `sections/` files • Published consumption rates dated to **CPDS v39.1 (effective June 5, 2026)** • Last built: 2026-10-03*

> **Do not hand-edit this file.** It is generated from `sections/00…11` by `build/build_kb.py`. Edit the section files, then re-run the build. See [`AGENTS.md`](./AGENTS.md) and [`README.md`](./README.md). All citations live in [`sources/SOURCES.md`](./sources/SOURCES.md).

## Contents

- [Executive Summary](#executive-summary)
- [1. History & Naming: From IICS to IDMC](#1-history--naming-from-iics-to-idmc)
- [2. The Legacy IICS Licensing Model](#2-the-legacy-iics-licensing-model)
- [3. The IDMC IPU Consumption Model](#3-the-idmc-ipu-consumption-model)
- [4. How Each Service Meters Against IPUs](#4-how-each-service-meters-against-ipus)
- [5. What Customers Are Locked Out Of Under Legacy IICS Licensing](#5-what-customers-are-locked-out-of-under-legacy-iics-licensing)
- [6. What the IPU Model Unlocks](#6-what-the-ipu-model-unlocks)
- [7. Legacy IICS Licensing vs IDMC IPUs — Side by Side](#7-legacy-iics-licensing-vs-idmc-ipus--side-by-side)
- [8. Migrating from Legacy Licensing to IPUs](#8-migrating-from-legacy-licensing-to-ipus)
- [9. The Commercial Model (Customer View)](#9-the-commercial-model-customer-view)
- [10. Should You Move to IPUs? Reasons to Move vs. Reasons to Wait](#10-should-you-move-to-ipus-reasons-to-move-vs-reasons-to-wait)
- [11. FAQ & Common Customer Questions](#11-faq--common-customer-questions)
- [12. Glossary](#12-glossary)

---

## Executive Summary

**"Moving from IICS to IPUs" is a change in how you buy Informatica's cloud — not a
change of product.** You stay on the same platform; you change the commercial model
underneath it. This knowledge base explains that transition end to end: the history, the
old licensing model, the new consumption model, exactly what each service costs in IPUs,
what the old model locked customers out of, what the new model unlocks, how to migrate,
the commercial mechanics, an FAQ, and a glossary.

### The story in five sentences

1. **IICS** (Informatica Intelligent Cloud Services, GA December 2017) is the original
   brand for Informatica's cloud data-management platform; **IDMC** (Intelligent Data
   Management Cloud, unveiled April 2021) is the *same platform*, expanded across the full
   portfolio and built around the **CLAIRE** AI engine.
2. Under **legacy IICS licensing** you bought *each service separately* — a fixed
   edition/tier of Data Integration, of Data Quality, of API Management, and so on — each
   with its own capacity and its own connector entitlements.
3. Under the **IDMC IPU model** you buy *one flexible pool* of **Informatica Processing
   Units (IPUs)** — "a unit of capacity that can be used across eligible Cloud Services" —
   and spend it against whatever mix of services you actually use, metered per usage.
4. That single change removes the walls of the old model: it ends stranded per-service
   capacity, lets you adopt any eligible service (and every newly released one) with no new
   SKU, and adds real-time consumption visibility and AI (CLAIRE) across the platform.
5. Because the platform doesn't move, migrating is a **licensing conversion, not a
   re-platform** — the real work is *estimating and governing consumption*, which the model
   supports with published per-service rates, a real-time dashboard, and threshold alerts.

### At a glance

| | Legacy IICS licensing | IDMC IPU model |
|---|---|---|
| **What you buy** | A fixed edition/tier of each service, separately | One pooled quantity of IPUs |
| **Where spend can go** | Locked to the service you licensed | Any eligible service — spend follows the work |
| **Adding a capability** | New SKU / new contract | Already accessible; just start consuming |
| **New product releases** | Not included until purchased | Auto-activated into your pool on release |
| **Connectivity** | Bounded by connector entitlements | Used as part of normal service consumption |
| **Basis of the bill** | Fixed entitlement, used or not | Actual work performed, metered monthly |
| **Cost visibility** | Fragmented, per-contract | Real-time usage dashboard + threshold alerts |
| **AI (CLAIRE)** | Earlier-generation assistance | CLAIRE / CLAIRE GPT / Copilot / Agents across the platform |
| **The trade-off** | Rigid, but predictable per line | Flexible; cost tracks usage, so it must be governed |

### How this knowledge base is organized

- **Sections 1–2** — the history (IICS→IDMC) and the legacy per-service licensing model.
- **Sections 3–4** — what an IPU is, and exactly how each service meters against the pool
  (with published CPDS v39.1 rates).
- **Sections 5–6** — the heart of the comparison: what legacy licensing *locks out*, and
  what the IPU model *unlocks*.
- **Section 7** — a single side-by-side matrix.
- **Sections 8–9** — how to migrate/convert, and the commercial model in customer terms.
- **Section 10** — should you move? An honest look at reasons to move to IPUs vs. reasons to wait.
- **Sections 11–12** — FAQ / objection handling, and a glossary.

> **Shareable-doc guardrail.** This KB explains the *model*, not any customer's numbers.
> It contains no dollar-per-IPU price and no deal-specific discounting — those are
> provided by Informatica per engagement. Published *consumption rates* (how many IPUs a
> unit of work costs) are quoted from **CPDS v39.1 (effective June 5, 2026)** and dated so
> they can be re-verified; unconfirmed specifics are marked `[verify]`.

---

## 1. History & Naming: From IICS to IDMC

### The one-sentence summary

**"Moving from IICS to IPUs" does not mean moving to a different product.** It means moving from the **legacy Informatica Intelligent Cloud Services (IICS) per-service licensing model** to the modern **Intelligent Data Management Cloud (IDMC) IPU consumption-based licensing model**. The platform your teams log into, the connectors they use, and the services they run are the **same underlying cloud**. What changes is the **commercial and packaging model** underneath it — and, over time, how much broader that platform has become.

This section explains the naming, the timeline, and the precise relationship between "IICS" and "IDMC" so that everyone — customers and account teams alike — is working from the same map.

---

### What IICS was

**IICS = Informatica Intelligent Cloud Services**, Informatica's original cloud-native data-management and integration-platform brand. Informatica announced general availability of Informatica Intelligent Cloud Services in **December 2017**, positioning it as **"the industry's next-generation iPaaS"** (integration Platform as a Service). It was built from the ground up on cloud-native frameworks — a microservices architecture designed to run integration, and later a growing set of data-management services, as cloud services rather than as software you installed and ran yourself.

IICS was the cloud successor to Informatica's earlier cloud integration offering (commonly referred to as *Informatica Cloud*). Informatica itself is a long-established data-management company, **founded in 1993** by Gaurav Dhillon and Diaz Nesamoney, so IICS represented the cloud-native chapter of a much longer product history rather than the company's first product.

In its IICS era, the platform was organized primarily around **discrete cloud services** you licensed individually — most prominently **Cloud Data Integration (CDI)**, with adjacent services such as **Cloud Application Integration (CAI)**, **Cloud Data Quality (CDQ)**, **Cloud Mass Ingestion**, and others available as separate purchases. That per-service structure is the heart of the "legacy licensing model" covered in Section 2.

---

### The IDMC era

**IDMC = Intelligent Data Management Cloud.** Informatica formally unveiled the Intelligent Data Management Cloud at **Informatica World in April 2021**, with then-CEO **Amit Walia** presenting it as **"the industry's most comprehensive, AI-powered, end-to-end data management platform."** Informatica described it as an **"AI-Powered, Cloud-First, Cloud-Native, End-to-End Platform"** that is **"micro-services based and API-driven, scaling for all enterprise workloads with elastic and serverless processing."**

Two points matter for anyone tracking the naming:

- **It was an expansion and unification, not a from-scratch rebuild.** IDMC is the umbrella brand that brought Informatica's cloud services — data integration, application/API integration, data quality, data cataloging and governance, master data management, and more — under a **single, unified platform** with a shared metadata foundation. The IICS services customers already knew became services *within* IDMC.
- **The "~2022" perception is real but imprecise.** Because the IDMC brand was introduced in 2021 and then rolled out heavily across Informatica's marketing, documentation, and packaging through 2021–2022, many customers first *encountered* the IDMC name around 2022. The formal introduction, however, was **April 2021**. [verify: exact first public use of the "IDMC" name may predate the April 2021 unveiling in some materials]

#### What actually changed at the rebrand

| Dimension | IICS framing | IDMC framing |
|---|---|---|
| **Brand / umbrella** | "Intelligent Cloud Services" — integration-led | "Intelligent Data Management Cloud" — full data-management portfolio |
| **Scope** | Integration and adjacent cloud services, licensed individually | One platform spanning integration, quality, catalog, governance, MDM, API/app integration, and AI/agent capabilities |
| **AI** | AI/ML assistance present (CLAIRE) | **CLAIRE® AI at the core**, positioned as an "AI copilot," later extended with CLAIRE GPT natural-language experiences |
| **Metadata** | Per-service | **Unified metadata foundation** — a "metadata system of intelligence" spanning the platform |
| **Commercial model** | Per-service subscriptions, editions, connector entitlements (see Section 2) | **Consumption-based IPU pricing** across eligible services (see Sections 3+) |

The key idea: **the rebrand consolidated a portfolio and put AI and shared metadata at the center**, and it was paired with a move toward the consumption-based IPU commercial model. The plumbing customers were already using did not get thrown away — it was unified under a broader, AI-forward umbrella.

#### CLAIRE — the AI through-line

**CLAIRE** is Informatica's metadata-driven AI engine. Informatica states that **"CLAIRE is at the core of the Intelligent Data Management Cloud,"** and today positions it as an **"AI copilot"** that **"automates thousands of data management tasks,"** with **CLAIRE GPT** adding natural-language interaction. CLAIRE existed in the IICS era, but it became a defining, front-and-center element of the IDMC story.

---

### Why customers still see and hear "IICS"

Even though **IDMC is the current umbrella brand**, the "IICS" name is still very much alive in day-to-day use. This is normal and expected — it does **not** mean a customer is on an old or unsupported product. Common reasons:

- **Login URLs and pod hostnames.** Customers log in through URLs such as **`dm-us.informaticacloud.com`**, and the sign-in page itself still reads **"Log in to Informatica Intelligent Cloud Services."** The regional pod naming (e.g., `dm-us`, `dm-em`, `dm-ap`) predates the IDMC brand and remains in use.
- **Legacy contracts and order documents.** Agreements, SKUs, and renewal paperwork signed during the IICS era continue to reference "Intelligent Cloud Services" and per-service line items even as the platform itself has moved forward.
- **Documentation, APIs, and product internals.** Many REST endpoints, administrative concepts, and older knowledge-base and documentation pages still use "IICS" terminology. License administration, for example, is still expressed in terms of **edition, connector, and custom licenses** (see Section 2).
- **Habit and institutional memory.** Teams that adopted the platform as "IICS" often keep calling it that, the way people still say "Informatica Cloud."

**Bottom line for account conversations:** "IICS" and "IDMC" refer to the **same living platform**. IICS is the original/legacy brand for the cloud services; IDMC is the current umbrella brand for the unified, AI-powered platform those services now live inside.

---

### The precise relationship (say it this way)

- **Same platform, evolving brand.** IDMC is the umbrella; the IICS services are part of it. There was no forced re-platforming or data migration caused by the name change itself.
- **Broader portfolio.** Under IDMC, Informatica pulled its cloud data-management capabilities — integration, data quality and observability, cataloging, governance and privacy, MDM and 360 applications, API and B2B, and AI/agent engineering — into one place with shared metadata.
- **AI-forward.** CLAIRE moved from "a feature" to "the core."
- **A new commercial model.** The IDMC era is the era of **consumption-based IPU pricing**, replacing the older per-service subscription approach.
- **Even the vendor name is evolving.** Following Salesforce's acquisition of Informatica (completed in November 2025), current pages are branded **"Informatica from Salesforce."** This is a corporate/branding change layered on top of the same IDMC platform, and is separate from the IICS→IDMC and licensing-model story.

So when someone says **"we're going from IICS to IPUs,"** translate it internally as: *"We're staying on the same Informatica cloud platform (now branded IDMC), and we're moving our commercial model from legacy per-service IICS licensing to the modern IPU consumption model."* Everything else in this KB builds on that single clarification.

---

## 2. The Legacy IICS Licensing Model

### What "legacy licensing" means here

Before Informatica moved to consumption-based **IPU** pricing (covered in later sections), Informatica cloud was licensed the way most enterprise SaaS was licensed at the time: you **subscribed to specific services, at specific capacity, with specific entitlements**, for a fixed term. In IICS terms, an organization's entitlements were expressed as **licenses**, and Informatica's own administration model still describes those licenses in three categories:

> "Licenses are categorized as **edition** licenses, **connector** licenses, and custom licenses."
> — Informatica documentation, *License categories*

Those licenses collectively **"determine the IDMC subscription level for the organization and provide access to IDMC features, connectors, and bundles."** Understanding these three categories — plus the practical constraints they created — is the whole story of "the legacy model," and it explains exactly *why* Informatica (and its customers) moved to IPUs.

---

### The building blocks of the legacy model

#### 1. Per-service / per-product subscriptions

The legacy model was **service-centric**. You bought the services you intended to use — most commonly **Cloud Data Integration (CDI)** — and each additional capability was a **separate line item**. Want application/API integration? That was **Cloud Application Integration (CAI)**, purchased separately. Want data-quality cleansing and matching? **Cloud Data Quality (CDQ)**, separately. Mass ingestion, API management, B2B, MDM — each was its **own SKU with its own subscription**.

The practical effect: your contract was a **stack of independent subscriptions**, each sized and priced on its own, each with its own capacity and renewal.

#### 2. Edition licenses (feature/usage tiers)

Within a service, what you could actually *do* was governed by an **edition license**. Informatica describes editions as coming in two forms:

- **Feature-based editions**, which unlock specific platform capabilities. Per Informatica's documentation, edition licenses unlock IDMC capabilities such as **"Data Integration mapping tasks,"** business-services components, and fine-grained security. Higher editions unlocked more advanced task types, connectors, and administrative/security features.
- **Usage-based editions**, which grant access **"using a pre-paid consumption model."** (This second form is essentially the mechanism that the modern IPU model generalizes across the whole platform.)

In the classic IICS commercial model, customers typically bought a **named feature edition per service** — the higher the edition, the broader the capability set — and were **capped at that edition's feature set** until they purchased an upgrade. [verify: the specific marketed edition-tier names/labels used in a given customer's IICS-era order documents — these varied by service and over time]

#### 3. Connector licenses (connectivity entitlements)

Connectivity was licensed **separately from the service itself**. Informatica's documentation defines connector licenses as those that **"provide connectivity to entities such as Amazon Redshift, Microsoft SQL Server, and Oracle."** In practice this meant your subscription came with a **defined set of connectors**, and connecting to a source or target **outside that entitled set required buying additional connector licenses** (often sold as connector packs).

This is one of the most important — and most frequently painful — characteristics of the legacy model: **the systems you could integrate were bounded by what you had licensed**, not by what the platform technically supported.

#### 4. Custom licenses, bundles, and packages

Beyond editions and connectors, Informatica also issued **custom licenses** covering **"features, packages, or bundles"** that sat outside a standard edition. Where a custom license overlapped an edition, **"the terms of the custom license override the terms of the edition license."** Trial subscriptions were a related concept — a trial **"might provide limited access to the features, connectors, and packages that are associated with the license."** Bundles let Informatica package specific capability + connector combinations for particular use cases, but they were still **fixed grants of specific entitlements**.

#### 5. Fixed processing capacity and true-ups

Each subscribed service was sized to a **defined capacity/processing tier** — for example, a level of data volume, rows, compute, or a comparable metric appropriate to that service. If actual usage **exceeded the contracted capacity**, the customer generally had to **"true up"**: purchase additional capacity, often at renewal or via a mid-term amendment, to bring the entitlement back in line with real usage. [verify: "true-up" was a general enterprise-subscription mechanism applied to IICS; the exact contractual trigger and cadence were defined per agreement rather than by a single published rule]

---

### Why the legacy model was rigid — the constraints customers actually hit

The legacy structure was clear and predictable, but its rigidity is precisely what created friction as customers' data estates grew and diversified. The recurring pain points:

- **You paid for fixed capacity per service — used or not.** Capacity was committed up front, service by service. If your data-integration volume came in **under** the contracted tier, you had effectively **pre-paid for headroom you never touched** — and there was **no easy way to redirect that spend** to a service you *were* running hot.
- **Services were siloed budgets.** Because each service was its own subscription, **money committed to CDI could not flex over to CDQ, CAI, or MDM.** Even if one service was starved and another was idle, the walls between line items stayed up until the next negotiation.
- **Adopting anything new required a new purchase.** Wanting to try a capability you hadn't licensed — say, adding data quality alongside integration, or standing up an API — meant a **new SKU, a new procurement cycle, and (often) a new negotiation**, rather than simply turning the capability on. That slowed experimentation and time-to-value.
- **Connector limits blocked real integration work.** A new source or target system that fell **outside your entitled connector set** could stall a project until additional connector licenses were purchased — an especially awkward constraint given that the whole point of an iPaaS is to connect to *many* systems.
- **Edition ceilings gated features.** Needing a more advanced task type, security control, or capability that lived in a **higher edition** meant an **upgrade purchase**, even if you needed that one feature only occasionally.
- **Hard to shift budget as priorities changed.** Data programs are rarely static — a project accelerates, a season spikes, a new initiative appears. The legacy model made it **difficult to reallocate committed spend** across services in response, because commitments were locked at the per-service, per-edition, per-connector level.
- **Forecasting and true-ups were lumpy.** Because entitlements were fixed and overages triggered true-ups, customers faced a **plan-high-or-risk-a-true-up** dilemma: over-provision (and waste) to be safe, or under-provision (and risk a mid-term purchase and project disruption).

Put simply, the legacy IICS model asked customers to **predict, per service, how much of each capability they would need for the entire term — and to buy connectivity to match — with limited ability to correct course.** That works when needs are stable and narrow. It becomes a drag the moment a customer wants to consolidate onto one platform, adopt multiple services, connect to a fast-changing set of systems, or handle variable/seasonal workloads.

---

### How this sets up the move to IPUs

Every constraint above maps directly to a design goal of the **IPU consumption model**:

| Legacy constraint | What the IPU model changes |
|---|---|
| Fixed capacity per service, use-it-or-lose-it | A **single pooled** capacity (IPUs) consumed only as work runs |
| Siloed per-service budgets | One pool that can **shift across services** without re-procurement |
| New service = new purchase | Eligible services are **available from day one**; new ones activate automatically |
| Connector entitlements limit reach | Broad connectivity available; connectors remain a separate **tier-based** subscription (Tier A included; B/C/D per End Point; **not** IPU-metered), while the **services** that use them draw from one shared pool *(CPDS v39.1, pp. 7, 28)* |
| Edition ceilings gate features | Consumption metered by usage rather than gated by a purchased feature tier |
| Budget hard to reallocate | Usage can be **tracked, tagged, and reallocated** across projects/departments |

Notably, Informatica's *own* license model already contained the seed of this shift: the **usage-based edition** described above grants access **"using a pre-paid consumption model."** IPUs take that consumption concept and make it the **universal** commercial model across the platform. The mechanics of how IPUs are bought, pooled, and metered are covered in the following sections.

---

## 3. The IDMC IPU Consumption Model

The single biggest change moving from legacy IICS licensing to the **Informatica
Intelligent Data Management Cloud (IDMC)** is *how you buy and how you pay*. Legacy IICS
was licensed as a set of **separate, fixed subscriptions** — you bought a specific edition
of a specific service (Data Integration, Data Quality, API Management, and so on), each
with its own tier, its own entitlements, and its own connector packs. IDMC replaces that
with **one flexible, consumption-based pool** measured in **Informatica Processing Units
(IPUs)**. This section defines the IPU precisely, explains the universal-credit concept,
and contrasts it with the old "buy fixed capacity per service" approach.

---

### 3.1 What an IPU is

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
  numbers of IPUs — see [Section 4](#4-how-each-service-meters-against-ipus).

> **Note on dollar pricing.** The CPDS publishes the *consumption rates* (how many IPUs a
> unit of work costs) but **not** the dollar price of an IPU itself. The per-IPU price is
> set in the customer's Order/quote and is not published in the CPDS. This KB therefore
> never states a per-IPU dollar figure. **`[verify]`** any dollar-per-IPU number against
> the customer's own Order.

---

### 3.2 One pool, spendable across the entire portfolio

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
[Section 4](#4-how-each-service-meters-against-ipus).

---

### 3.3 How consumption is measured

Consumption is **metered automatically inside the platform** and drawn down from your pool
as jobs run.

- **Per "scalar," by usage.** IPU consumption "is calculated per scaler, based on the
  scaler's usage including Secure Agent, CDI-e, Data Mass Ingestion volume and more." A
  *scalar* (scaler) is simply the thing being counted for a given service — compute hours,
  rows processed, gigabytes of data volume, API calls, daily assets stored, events, or
  queries. Each service definition names its scalar and its metric (see the full matrix in
  [Section 4](#4-how-each-service-meters-against-ipus)).
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

### 3.4 Committed pool vs. Flex vs. pay-as-you-go on-ramp

Informatica offers the IPU model in more than one commercial shape. The **metering is the
same**; what differs is the *time window* over which your commitment is measured and how
overage is handled.

| Model | Commitment window | Carry-over | Overage handling |
|---|---|---|---|
| **IDMC – IPU** | Monthly: consume the subscribed IPUs "across a monthly period" | IPUs **do not** carry over to the next month | If consumption exceeds the subscribed number, customer must subscribe to additional IPUs for the remainder of the term |
| **IDMC – Flex IPU** | Annual: consume the subscribed IPUs "across an annual period" | IPUs **do not** carry over to the next annual period | Overage fee (set in the Order) applies to additional consumption |
| **IDMC – Unlimited / Unlimited Flex IPU** | Customer "is not subscribing to a specific maximum quantity of IPUs" | n/a | n/a |

Two related commercial constructs are worth knowing (details, without deal-specific
numbers, live in [Section 9 – Commercial Model](#9-the-commercial-model-customer-view)):

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

### 3.5 How this differs from buying fixed per-service capacity

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

## 4. How Each Service Meters Against IPUs

[Section 3](#3-the-idmc-ipu-consumption-model) explained that IPUs are one universal pool spent
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

### 4.1 The four metering bases (and what they mean)

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

### 4.2 Data Integration (CDI) and its compute-metered relatives

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

#### SQL ELT / advanced pushdown optimization — the biggest lever on consumption

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

### 4.3 Cloud Application Integration (CAI) and APIs

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

### 4.4 Data Ingestion & Replication (mass ingestion) — sub-type by sub-type

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

### 4.5 Cloud Data Quality (CDQ) and Address Verification

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

### 4.6 Cloud Data Governance & Catalog (CDGC) and Data Access Management

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

### 4.7 Marketplace, Integration Hub, and platform/security services

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

### 4.8 CLAIRE / CLAIRE GPT

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

### 4.9 Services that do NOT meter against IPUs

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

See [Section 3.2](#3-the-idmc-ipu-consumption-model) for how these fit alongside the pool, and
[Section 7 – Side-by-Side Matrix](#7-legacy-iics-licensing-vs-idmc-ipus--side-by-side) for the consolidated view.

---

### 4.10 Practical implications for scoping a pool

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

## 5. What Customers Are Locked Out Of Under Legacy IICS Licensing

Legacy Informatica Intelligent Cloud Services (IICS) licensing is built around **per-service subscriptions**. You buy a specific service (for example, Cloud Data Integration) at a specific **processing tier**, with a defined set of **connector entitlements**, for a fixed contract term. Each service you buy is a separate line item with its own capacity, and that capacity is **siloed** to the service it was purchased for.

That structure works cleanly when your needs are static and narrow. It becomes a set of hard walls the moment your needs change, grow, or diversify. This section enumerates what customers are effectively **locked out of** under that model, and why each limit matters to the business.

> Framing note: This section describes the **constraints and their business impact**. The corresponding benefits under the modern IPU consumption model are covered in Section 6.

> **One distinction keeps this section honest.** For every constraint below, note its *nature* — it changes the conversation:
> - **Commercial friction** — the capability exists and works; you simply couldn't *use* it until you bought its SKU/edition/connector. A procurement problem, not a product limit.
> - **Newer-service availability** — the service is genuinely newer than the classic IICS era; in an older contract it wasn't a line you *could* buy yet.
> - **True technical limit** — a hard capability the older setup couldn't do at all. **Rare** in this comparison, and we don't overstate it.
>
> The honest, defensible message: **most legacy lock-outs are commercial (separately-licensed), not technical.** The clearest genuinely-*newer* cases are CLAIRE GPT and the modern forms of Data Marketplace, Data Access Management, and CDGC (§5.6). The capability was there; the commercial model decided how much of it you could reach — and how fast you could adopt what's new. *(Mapping to the items below: 5.1–5.5, 5.7, 5.8 are chiefly **commercial friction**; 5.6 is **newer-service availability**; 5.9 is closest to a **true limit** for regulated workloads until authorization exists.)*

---

### 5.1 Services you did not license simply are not available

Under per-service subscription licensing, you can only use the specific services on your contract. If you licensed data integration but not data quality, governance, master data management, or application/API integration, those services are **out of reach** until you negotiate and purchase them as **new SKUs**.

**Why it matters to customers**
- A data-integration team that discovers a data-quality or governance need cannot simply turn the capability on — it becomes a procurement project.
- Cross-functional initiatives (for example, a "trusted customer view" that needs integration **plus** quality **plus** MDM) require multiple separate purchases before work can even begin.
- Innovation stalls at the boundary of what was originally bought, not at the boundary of what the business needs.

The modern IDMC platform is explicitly positioned as a **unified** portfolio — Data Integration, Data Quality & Observability, Application/API Integration, Data Catalog, Data Marketplace, Governance/Access/Privacy, and MDM & 360 Applications — but under legacy per-service licensing you only get the doors you individually paid to open.

---

### 5.2 Connector count and connector-type limits

Legacy service subscriptions come with **defined connector entitlements**. The set and, in some arrangements, the number/type of connectors you can use is tied to what was licensed. Adding a new source or target type (a new SaaS application, a new cloud data warehouse, a new database) can require an **entitlement change**.

**Why it matters to customers**
- New systems appear constantly (a newly adopted SaaS app, a migration to a new cloud data warehouse). If the connector is not in your entitlement, the integration is blocked until licensing catches up.
- Teams end up building brittle workarounds (custom API calls, manual extracts) to avoid a licensing conversation — adding technical debt and risk.
- Connectivity, which should be a routine technical decision, becomes a **commercial** decision.

> **Connector licensing is tier-based.** Informatica groups connectors into tiers: a base
> tier (**Tier A**) is included, while higher tiers (**Tier B/C/D**) are subscribed
> **separately, per End Point**, and are **not** IPU-metered *(CPDS v39.1, pp. 7, 28)*.
> Connecting to a higher-tier system is therefore a distinct subscription decision. Under
> legacy per-service licensing this compounds the problem: the connector tier *and* the
> service that uses it are both gated by what you bought.

---

### 5.3 Capacity ceilings are per service — hitting the wall means a new purchase

Each legacy service is sized to a **fixed processing tier**. When a workload grows past that tier — more rows, more mappings, more compute hours, more ingestion volume — you hit a **hard ceiling**. The only way through is to **buy more capacity for that specific service**, typically as a contract amendment or a new order.

**Why it matters to customers**
- Growth is punished with friction: exactly when a project succeeds and scales, the platform forces a procurement cycle.
- Seasonal or bursty workloads (month-end close, a large one-time migration, a marketing campaign) cannot be absorbed elastically — you must size and pay for the **peak** even if you only need it occasionally.
- Capacity planning becomes a guessing game with real financial consequences for guessing wrong in either direction.

---

### 5.4 No cross-service flexibility — capacity cannot be shared or reallocated

This is the defining constraint of the legacy model. Because capacity is **siloed per service**, unused capacity in one service **cannot fund a need in another**. If you have surplus Cloud Data Integration capacity but a pressing Cloud Data Quality or MDM need, that surplus is **stranded** — it cannot be redirected.

**Why it matters to customers**
- You can be simultaneously **over-provisioned** in one service and **blocked** in another, paying for both problems at once.
- Every service is its own budget bucket, so priorities cannot flex with the business; money committed to last year's plan cannot follow this year's need.
- The organization loses the ability to reallocate spend to where value is actually being created.

---

### 5.5 Adopting a new capability means friction and new contracts

Because each capability is a separate entitlement, **trying** or **adopting** something new is not a self-service action — it is a **sales and procurement event**. Evaluating a new service typically means engaging a seller, scoping a new SKU, negotiating terms, and amending or signing a contract before hands-on work can start.

**Why it matters to customers**
- The cost of *experimentation* is high: teams cannot cheaply pilot data quality, cataloging, or MDM to see if it delivers value before committing.
- Time-to-value is dominated by procurement lead time, not by how fast the team can build.
- Genuinely useful capabilities go unexplored simply because the friction to try them is too high — the platform's breadth is invisible to the people who could use it.

---

### 5.6 Limited or no access to newer IPU-era capabilities, depending on entitlement

The IDMC platform continues to add capabilities — a **fully managed serverless runtime** and elastic Spark compute, **CLAIRE** AI (including **CLAIRE GPT** and CLAIRE Copilot/Agents), **Data Marketplace**, and low-friction **Free & PayGo** experimentation on-ramps. Under a narrow, fixed per-service entitlement, access to these newer capabilities can be **limited or unavailable** unless your specific entitlement includes them.

**Why it matters to customers**
- You may be running on a platform that has evolved substantially, yet be **fenced off** from its newest, most differentiating features.
- AI-assisted automation (metadata intelligence, natural-language data tasks, in-tool copilots) can bypass your users entirely if the entitlement predates or excludes them.
- Modern runtime options (serverless/elastic compute that scales on demand and shuts down when idle) may not be available to teams still bound to older, fixed-capacity arrangements.

> [verify] Whether a given newer capability is strictly consumption-model-only versus separately licensable under legacy terms depends on the specific entitlement and current Informatica offering terms. Availability of CLAIRE generative/headless features is also governed by deployment to a compatible POD and by current promotional terms (an at-no-additional-cost promotional period for certain CLAIRE generative and headless pre-run-time design activities was referenced through January 31, 2027).

---

### 5.7 Paying for shelfware

The mirror image of siloed capacity is **shelfware**: capacity or services you licensed but do not fully use. Because commitments are made per service and per tier up front, real-world usage rarely matches the plan — and the gap is money spent on entitlement that sits idle.

**Why it matters to customers**
- You pay for the **tier you bought**, not the value you consumed; underused services and headroom become sunk cost.
- Because that idle capacity **cannot be reallocated** (see 5.4), shelfware is pure waste rather than a reserve you can redeploy.
- Renewal conversations become contentious, because it is hard to justify or right-size spend that is fragmented across many independently-committed service lines.

---

### 5.8 Secure Agent capacity is constrained — and overages surface at renewal

Legacy per-service licensing sizes not just data volume but the **runtime footprint**.
Exceeding the entitled number of **Secure Agents** — the runtime engines you install for
on-premises/hybrid connectivity — can create **true-up / compliance exposure at renewal**,
turning a routine technical scaling decision into an unbudgeted commercial liability.

**Why it matters to customers**
- Standing up more agents to serve new teams, regions, or clouds can quietly put you out of
  compliance with your entitlements.
- The exposure typically surfaces at renewal, as an unplanned true-up.
- The IPU model removes the per-agent penalty structure, so you can add agents across
  multi-cloud as needs grow (see Section 6).

---

### 5.9 Compliance authorizations (e.g., FedRAMP) may be unavailable

For public-sector or regulated workloads, authorization can gate the entire platform
decision. Legacy IICS is **not FedRAMP-listed**. Under IDMC, **FedRAMP Moderate is
available for _some_ services / environments only** — it is **not a blanket, platform-wide
authorization**, and the specific service and environment must be validated. `[verify per service]`

**Why it matters to customers**
- Assuming platform-wide compliance coverage is risky; the answer is per-service.
- Confirm FedRAMP (and any other required authorization) for the *exact* services and
  environment you intend to use before committing.

---

### Summary: What legacy IICS licensing locks out

| # | Locked-out item | What it means | Customer impact |
|---|-----------------|---------------|-----------------|
| 1 | **Unlicensed services** | Only the services on your contract are usable; others require a new SKU | New quality/governance/MDM/API needs become procurement projects; cross-functional initiatives stall |
| 2 | **Connector limits** | Connector entitlements are fixed by what was licensed | Adding a new source/target type can require an entitlement change; teams build brittle workarounds |
| 3 | **Per-service capacity ceilings** | Each service is capped at a fixed processing tier | Growth and bursts force a new purchase; you must size and pay for peak |
| 4 | **No cross-service flexibility** | Capacity is siloed and cannot be reallocated | You can be over-provisioned in one service and blocked in another at the same time; spend is stranded |
| 5 | **Adoption friction** | Trying/adopting a new capability requires a new contract | High cost of experimentation; time-to-value gated by procurement, not delivery |
| 6 | **Limited access to newer capabilities** | Serverless, CLAIRE AI/GPT, Marketplace, Free & PayGo may be out of entitlement `[verify]` | Fenced off from the platform's newest, most differentiating features |
| 7 | **Shelfware** | Idle, non-reallocatable licensed capacity | You pay for the tier bought, not value used; waste that cannot be redeployed |
| 8 | **Secure Agent capacity** | Runtime footprint is entitled; exceeding it risks a true-up | Scaling agents across teams/clouds can create compliance exposure that surfaces at renewal |
| 9 | **Compliance authorizations** | Not FedRAMP-listed on IICS; FedRAMP Moderate only for some IDMC services/envs `[verify]` | Regulated/public-sector workloads can be blocked; coverage must be validated per service |

---

## 6. What the IPU Model Unlocks

The **Informatica Processing Unit (IPU)** consumption model replaces siloed, per-service subscriptions with a **single pool of consumption** that can be spent across the Informatica Intelligent Data Management Cloud (IDMC) portfolio. Instead of buying fixed capacity for one service at a time, you commit to a pool of IPUs and draw against it as you use eligible services — metered **per scaler, based on the scaler's usage** (for example Secure Agent, CDI-e / elastic compute, Data Mass Ingestion volume, and more).

This one structural change — **one flexible unit, one pool, one platform** — is what unlocks everything below.

> Framing note: This section describes the **benefits and how they resolve** each legacy constraint. The underlying constraints themselves are detailed in Section 5.

---

### 6.1 Access to the full portfolio from one pool

A single IPU pool provides **access to all eligible cloud services** across IDMC — Data Integration, Data Quality & Observability, Application/API Integration, Data Catalog, Data Marketplace, Governance/Access/Privacy, and MDM & 360 Applications. The breadth of the platform is available to you by default; you draw on whichever services a given initiative requires.

**What this unlocks**
- Cross-functional initiatives (for example, a trusted-customer-view program that needs integration **and** quality **and** MDM) can proceed as one project rather than waiting on multiple separate purchases.
- Teams design around the **best capability for the job**, not around the narrow subset that happened to be licensed.
- MDM remains available, accessed on a **per-domain records basis** alongside the IPU pool.

---

### 6.2 Try and adopt any service with no new SKU

Because eligible services all draw from the same pool, adopting a new capability is a **turn-it-on** decision rather than a **buy-a-new-SKU** decision. Customers can **swap for new services as needed** and **test new applications and address different use cases with ease**, and **all eligible new services are automatically activated once released**.

**What this unlocks**
- The cost of experimentation drops to near zero: a team can pilot data quality, cataloging, or governance to validate value before scaling it up.
- New platform capabilities become available **automatically** as Informatica ships them — no amendment required to gain access to what has been released.
- Innovation is bounded by imagination and delivery speed, not by the shape of a contract signed months earlier.

---

### 6.3 Elasticity and scale on demand

Consumption flexes with real usage. You **pay for what you need now and scale for the future**, drawing more from the pool during peaks and less during quiet periods rather than sizing and paying for a fixed peak tier that sits idle the rest of the time.

**What this unlocks**
- Bursty and seasonal workloads (month-end close, a one-time migration, a campaign) are absorbed without a procurement cycle.
- Growth is no longer punished: a successful project scales by consuming more of an existing pool, not by triggering a new purchase.
- Because the pool is shared, capacity effectively **follows the work** — surplus that a subscription model would strand can instead fund the next priority.

---

### 6.4 Serverless runtime and advanced pushdown optimization

The IPU model meters modern, on-demand runtime options as scalers, so customers can use them as needed. Cloud Data Integration offers **ETL, ELT, Spark, or a fully managed serverless option**, and CDI-Elastic provides **elastic compute clusters** with a **serverless Spark engine with dynamic scaling and auto-tuning** that **scales up or down based on the workload and shuts down when processing is complete** — which **eliminates server management** and **allows for consumption-based pricing**. **Pushdown optimization** pushes transformation logic down for efficient processing in the target data ecosystem.

**What this unlocks**
- **Capacity on demand**: heavy processing spins up elastic/serverless compute and then shuts down, so you pay for the run, not for idle infrastructure.
- **Lower operational overhead**: no servers to manage; the runtime auto-tunes and self-scales.
- **Efficiency at the source/target**: pushdown/ELT executes work where the data lives, reducing data movement and improving throughput.

> [verify] The specific branding "ecosystem pushdown," and whether a given runtime option (serverless/elastic, advanced pushdown) is available under a customer's particular legacy entitlement, depend on current offering terms and the customer's agreement.

---

### 6.5 CLAIRE AI across services

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

### 6.6 Faster time-to-value and low-friction innovation adoption

Low- and no-cost on-ramps make it easy to start and to expand. Informatica offers **Data Loader – Free** and **Cloud Data Integration – Free** (self-service **GET STARTED** signup; the free CDI tier provides up to **20M rows / 10 compute hours per month** with unlimited users), described as lowering **the barriers to get started with data integration** and letting teams **begin moving their data to the cloud without committing to software costs**, while the ability to scale up **minimizes risks from the trial and adoption of these products**.

**What this unlocks**
- Teams can prove value first and commit second, compressing the path from idea to production.
- Adoption of new capabilities is continuous rather than episodic, because there is no procurement gate between "we should try this" and "we are using it."
- Time-to-value is governed by how fast the team can build — not by contract lead times.

---

### 6.7 Simplified procurement — one contract, one unit

Instead of negotiating and tracking many independent service subscriptions, customers commit to a **single consumption unit (the IPU) under one arrangement**. New eligible services are **included and automatically activated** as they are released, so the entitlement keeps pace with the platform without a stream of amendments.

**What this unlocks**
- Dramatically fewer moving parts: one unit and one pool to reason about instead of a patchwork of per-service SKUs and tiers.
- Renewals and expansions become simpler and less contentious, because spend is expressed in a single, comparable unit.
- Reduced **training, maintenance, and procurement costs** from running multiple services together on one platform (Informatica cites Nucleus Research figures including a **413%** average ROI and **$1.08 million** in maintenance/administration savings).

---

### 6.8 FinOps visibility into consumption

The consumption model is instrumented for cost governance. Usage is **tracked automatically within the product**; a dashboard lets customers **view their own usage in real time**; and administrators can **set consumption threshold alerts to ensure cost containment**, with **alerts sent when specific usage thresholds are reached**. Consumption is transparent because it is metered **per scaler, based on the scaler's usage**.

**What this unlocks**
- Real-time cost transparency: teams see what they are consuming and where, and can **track usage to maximize ROI (FinOps)**.
- Proactive control: threshold alerts prevent surprises and keep spend inside plan.
- Better decisions: because capacity is fungible across services, FinOps insight directly informs where to direct the shared pool next.

---

### Summary: Legacy limitation → IPU-model resolution

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

## 7. Legacy IICS Licensing vs IDMC IPUs — Side by Side

This section compares the **legacy IICS per-service licensing model** with the modern **IDMC Informatica Processing Unit (IPU) consumption model** across the dimensions that matter most when you plan, buy, and operate Informatica in the cloud.

> **Note on branding:** *IICS* (Informatica Intelligent Cloud Services) is the original name for Informatica's cloud platform. *IDMC* (Intelligent Data Management Cloud) is the current name for the same platform, expanded and infused with the CLAIRE AI engine. This comparison contrasts the **way capacity was traditionally licensed on IICS** (fixed, per-service subscriptions) with the **way capacity is purchased today under IDMC** (a single, flexible IPU pool). It is a *commercial and operating-model* comparison, not a comparison of two different products.

---

### Comparison matrix

| Dimension | Legacy IICS licensing (per-service subscriptions) | IDMC IPU model (universal consumption) |
|---|---|---|
| **Unit of purchase** | Discrete, per-service subscriptions (e.g., a Cloud Data Integration edition, a Data Quality edition), typically sized to a fixed tier or capacity metric per service. | A single, universal currency — the **Informatica Processing Unit (IPU)** — that can be spent across **all eligible cloud services** on the platform. IPUs "give customers access to all eligible cloud services listed in the Cloud and Product Description Schedule." |
| **How you buy capacity** | You buy (and forecast) each service separately, often at its own tier, with its own renewal. Adding a service means adding another line/subscription. | You buy one **committed pool of IPUs** and draw down against it as you consume. You size the *pool*, not each service. Pay-as-you-go/PayGo options also exist for flexible or trial usage. [verify: PayGo availability varies by agreement] |
| **Flexibility to move spend** | Low. Spend is locked to the specific service purchased. Unused capacity in one service generally cannot be redeployed to another. | High. "Only pay for the services you require now, swap for new services as needed." The same IPU pool can shift toward whichever services you actually use as priorities change. |
| **Service / portfolio access** | Access limited to the services explicitly licensed. Using an additional capability (e.g., API management, MDM) required a new entitlement. | The full breadth of **eligible IDMC services** is reachable from one pool: Data Integration, Application/API & App Integration, Data Ingestion & Replication, Data Quality & Observability, Data Catalog/Governance, MDM & 360 Applications, Data Marketplace, and more. (MDM is metered on a per-domain records basis.) |
| **Connector access** | Connectors licensed by **tier**, tied to the service edition or subscribed separately per connector — constraining what you could connect to. | Connectors remain a **tier-based subscription** — **Tier A is included**; **Tier B/C/D are subscribed separately, per End Point** — and are **not** paid out of IPUs. What changes is that one IPU pool now funds the *services* that use those connectors, so adopting a new capability no longer requires a separate service SKU. *(CPDS v39.1, pp. 7, 28.)* |
| **Adopting a new capability** | Procurement event: scope, quote, contract amendment, then provisioning — before you can begin. | Turn it on and consume. "It is expected that all eligible new services will be included in the Intelligent Data Management Cloud and will be automatically activated for customers once released." You try/adopt within your existing pool, no new contract required to start. |
| **Scaling up / down** | Step-wise and contractual. Growth usually meant moving up a tier or adding subscriptions; scaling down mid-term was difficult. | Elastic. Consumption rises and falls with actual workload against the committed pool; you scale usage without renegotiating per-service tiers. Overage/on-demand consumption absorbs spikes. |
| **AI (CLAIRE)** | Limited/earlier-generation automation; AI was not the organizing principle of the platform. | **CLAIRE**, Informatica's metadata-driven enterprise AI engine, is embedded across IDMC — including **CLAIRE Copilot** (in-workflow guidance), **CLAIRE GPT** (natural-language interaction with your data), and **CLAIRE Agents**. CLAIRE also "helps optimize costs with enhanced performance for hyperscalers and ecosystems." |
| **Serverless & advanced pushdown optimization** | Runtime generally tied to customer-managed Secure Agents; fewer elastic/serverless and pushdown options. | Modern runtime choices are available from the same pool: **Secure Agent**, **serverless** runtime (Informatica-managed compute, no infrastructure to run), and **Advanced Pushdown Optimization (APDO)** to push transformation logic down into cloud data warehouses/lakes for performance and cost efficiency. Consumption is metered per "scaler" (e.g., Secure Agent, CDI‑e, Data Mass Ingestion volume, and more). |
| **Procurement complexity** | Higher. Multiple SKUs, tiers, and renewals to negotiate, track, and true-up per service. | Lower. One agreement and one pool; new services activate without new paperwork. Positioned as reduced "training, maintenance, and procurement costs on one platform." |
| **Cost predictability** | Predictable *per line* because tiers are fixed — but rigid; you pay for the tier whether or not you use it, and unused capacity is stranded. | Predictable at the *pool* level via your committed IPUs, plus real-time visibility to manage drawdown; more variable at the workload level because you pay for actual consumption. Threshold alerts and dashboards support FinOps-style cost containment. |
| **Consumption visibility / monitoring** | Limited cross-service visibility; usage insight was fragmented across separately licensed services. | Built-in, real-time. "Usage is tracked automatically within the product. A dashboard is available within the platform for customers to view their own usage in real time," and admins can "set consumption threshold alerts to ensure cost containment." Operational Insights provides operational/consumption monitoring across the org. |
| **Innovation adoption speed** | Slow — gated by new purchases and provisioning cycles. | Fast — new eligible services are auto-activated on release and can be trialed/adopted from the existing pool, so teams reach new capabilities in days, not procurement cycles. |

---

### Strategic takeaway

The move from **per-service IICS subscriptions** to the **IDMC IPU model** is a shift from *buying discrete products* to *buying a flexible capacity to do data management*. Instead of forecasting demand for each service a year in advance — and stranding whatever you over-buy — you commit to a single pool of IPUs and spend it against whatever mix of services your teams actually need, when they need it.

The practical benefits fall into three themes:

- **Agility:** New and additional capabilities (integration, quality, governance, MDM, API management, ingestion, AI) are reachable from one pool, and newly released eligible services are auto-activated — so adoption is a product decision, not a procurement project.
- **Efficiency:** One agreement, one currency, and CLAIRE-driven optimization reduce procurement, training, and maintenance overhead, and let unused capacity flow to where it creates value rather than sitting stranded in an over-provisioned service tier.
- **Accountability:** Real-time consumption dashboards, per-scaler metering, and threshold alerts give teams FinOps-grade visibility to manage cost against the committed pool.

The trade-off to manage is **variability**: because you pay for what you consume, cost tracks workload rather than a fixed tier. The model addresses this directly with committed pools for a predictable baseline, real-time monitoring, and threshold alerts — so customers get flexibility *and* control. For most organizations, the net effect is broader access to the platform, faster innovation, and better alignment of spend to value.

### Capability availability: standalone IICS vs IDMC / IPUs

The matrix above compares the *commercial model*. This second view compares **capability
availability** — what a customer can actually do on each. The "Legacy IICS" column reflects
the common **integration-only** licensing footprint (a customer's specific IICS entitlement
may include more if they licensed it); rows marked **IDMC-only** are the capabilities a
customer must move to IDMC/IPUs to obtain.

Legend: ✅ available · ⚠️ available with caveats · ◐ partial · ❌ not available.

| Capability | Legacy IICS (integration-only licensing) | IDMC / IPUs | IDMC-only? |
|---|---|---|:--:|
| Core cloud data integration (ETL/ELT) | ✅ Core function | ✅ Same underlying engine, funded via IPUs | — |
| Connectors to source/target systems | ✅ Tier-based, per-connector subscription (Tier B/C/D per End Point) | ✅ Same tier-based connector model — **not IPU-metered**; the *services* using them are funded from one IPU pool ¹ | — |
| Secure Agents (on-prem/hybrid connectivity) | ⚠️ Capacity-constrained; exceeding entitled agents creates true-up/compliance exposure at renewal | ✅ No per-agent penalty; add agents across multi-cloud as needs grow | — |
| API-led / application integration | ✅ Within integration scope | ✅ Funded via IPU pool | — |
| B2B / file-based data exchange | ✅ Within integration scope (connector-dependent) | ✅ Funded via IPU pool | — |
| **Master Data Management (MDM)** | ❌ Not in integration-only licensing | ✅ Available in the IDMC portfolio ² (MDM SaaS metered **per-record**, separate from the IPU pool — see §4.9) | ✔ |
| **Data Quality** | ❌ No | ✅ From the same IPU pool | ✔ |
| **Data Governance & Catalog** | ❌ No | ✅ From the same IPU pool | ✔ |
| **Data Privacy** | ❌ No | ✅ Part of the IDMC portfolio | ✔ |
| **CLAIRE AI engine / CLAIRE Copilot** | ❌ No embedded AI engine | ✅ Yes — Informatica cites up to **~90%** less data-wrangling time; Copilot automates pipeline development ³ | ✔ |
| **FedRAMP Moderate authorization** | ❌ Not FedRAMP-listed | ⚠️ Available for **some** IDMC services / environments only — not a blanket authorization; **validate per service** `[verify]` | ✔ |
| **Dynamic capacity reallocation across use cases** | ❌ Fixed SKU capacity, siloed per line item | ✅ One consumption metric (IPUs) reallocates as priorities shift | ✔ |
| **Burst capacity for large one-off events** (e.g., migrations, M&A ingestion) | ❌ Fixed capacity risks overage penalties | ✅ Scale usage temporarily without tripping overage penalties ⁴ | ✔ |
| Cloud-agnostic flexibility (AWS + Azure, etc.) | ◐ Connectors exist but capacity siloed per environment | ✅ Positioned as more cloud-agnostic than native cloud tools (e.g., AWS Glue/DataBrew) | — |
| **Adding new capabilities without new procurement** | ❌ New capability = new SKU = procurement cycle (can add weeks) | ✅ New services draw from the existing IPU balance | ✔ |
| **Consumption / utility-style financial modeling** | ❌ Fixed-cost, SKU-based | ✅ Scales like a utility with data volume — more predictable for Finance | ✔ |
| Underlying platform / core engine | Same core Informatica platform | Same core platform — **no re-platforming** to convert | — |

**Notes**
1. *Connector correction:* connectors are a **tier-based subscription** (Tier A included;
   Tier B/C/D subscribed separately, per End Point) and are **not** IPU-metered
   *(CPDS v39.1, pp. 7, 28)*. The IPU pool funds the services that use connectors, not the
   connectors themselves.
2. Under integration-only IICS licensing, MDM is not included. Under IDMC it is part of the
   portfolio, but **MDM SaaS is metered per-record**, separate from the IPU pool (see §4.9);
   "unlocked on existing spend" describes the commercial ease of adopting it, not IPU metering.
3. The **~90%** figure is an Informatica-published (vendor-cited) estimate; actual results
   vary by workload.
4. **"Burst"** describes the usage *pattern*; it is not an official Informatica product term.
   Likewise, "one pool / single currency" is a paraphrase of the IPU model, not a verbatim
   Informatica quote (the CPDS defines an IPU as "a unit of capacity that can be used across
   eligible Cloud Services").

---

## 8. Migrating from Legacy Licensing to IPUs

> **Audience:** Customers moving from legacy Informatica IICS licensing to the Informatica Intelligent Data Management Cloud (IDMC) **Informatica Processing Unit (IPU)** consumption model, and the account teams who support them.

### 8.1 The most important point: this is a licensing change, not a re-platform

Moving to IPUs is fundamentally a **commercial and contract conversion**, not a technical migration. IICS and IDMC are the **same platform**: what Informatica historically marketed as "Informatica Intelligent Cloud Services (IICS)" is the same cloud-native environment now branded **Intelligent Data Management Cloud (IDMC)**. The public Cloud & Product Description Schedule (CPDS) still points to the IICS Product Availability Matrix (PAM) for regional and ecosystem service availability *inside* its IDMC section, which reflects that the two names describe one platform. [CPDS §IDMC]

What this means in practice:

- **No lift-and-shift.** Your existing org, Secure Agents, connections, mappings, taskflows, and assets stay exactly where they are.
- **No rebuild.** There is no need to re-develop pipelines, re-point connectors, or recreate runtime environments to consume IPUs.
- **What changes is how you are entitled and billed.** Instead of fixed, per-product or per-user entitlements, you subscribe to a **pool of IPUs** — a single, flexible unit of capacity — and draw it down as you use eligible Cloud Services. [CPDS Definitions]

> **IPU, defined:** *"Informatica Processing Unit (IPU) is a unit of capacity that can be used across eligible Cloud Services."* — CPDS, Definitions.

Because the platform does not change, the risk profile of the move is dominated by **estimating and governing consumption**, not by engineering. The rest of this section is a practical playbook for doing exactly that.

### 8.2 How consumption is metered (what you are actually estimating)

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

### 8.3 Step-by-step: converting to IPUs

#### Step 1 — Frame it as a conversion, and set the team
Confirm internally that the environment does not move. Assemble a small cross-functional group: the Informatica platform owner/admin, a data-engineering lead who knows the pipelines, and a commercial/FinOps or procurement owner. Engage your Informatica account team early — **specific pricing, volume tiers, and commercial terms are provided by Informatica per engagement** and are not derivable from public documents.

#### Step 2 — Baseline your current usage
Inventory what you run today so the estimate is grounded in reality, not guesswork:
- **Assets & jobs:** number and type of mappings, mapping tasks, taskflows, replication/ingestion tasks, and their schedules/frequency.
- **Volumes:** rows processed, data volume moved/transformed, records mastered (MDM), addresses verified, API calls, and peak vs. average throughput.
- **Runtime footprint:** Secure Agents, node/CPU-core counts, and how much runs concurrently.
- **Services in use:** Data Integration, Data Quality, Application/API Integration (CAI), Mass Ingestion, MDM SaaS, Data Governance/Catalog, etc.

The IDMC **admin/monitor** and **Operational Insights** surfaces (see §8.5) are the best places to pull this data if you are already on the platform.

#### Step 3 — Estimate IPU needs
Map each service you use to its **scalar → metric → IPU-per-metric-unit** formula from the current CPDS/Measurement Guide, apply your baselined volumes (respecting the **tiered rates**), and sum to an annualized IPU figure. Then:
- Add a **growth allowance** for known roadmap (new sources, new pipelines, expanding data volumes).
- Model **peaks**, not just averages — consumption is not perfectly flat month to month.
- Use the **IPU estimator** tooling as an accelerator. Informatica provides estimator/calculator assistance to translate a usage profile into an IPU estimate; work this with your account team so it reflects current rates and your specific service mix. *[verify: exact estimator tool name/availability with your Informatica contact]*

#### Step 4 — Right-size the annual commit
Pick a committed IPU pool that covers **steady-state plus reasonable growth**, but resist over-committing "just in case." The model is designed to flex:
- If you **under-commit**, you can add IPUs; sustained overage indicates you should true up (see §8.6).
- If you **over-commit**, you carry capacity you may not use within the term.
- A well-sized commit sits slightly above expected steady-state usage, with overage flexibility absorbing peaks.

#### Step 5 — Plan a phased adoption
You do not have to convert everything at once conceptually. A low-risk sequence:
1. Convert commercially to the IPU pool while workloads keep running unchanged.
2. **Watch actual consumption** for one or more full cycles against the estimate.
3. Onboard additional teams/workloads deliberately, watching the meter as each comes on.
4. Re-baseline the commit at renewal using real consumption data.

#### Step 6 — Stand up monitoring and governance *before* volume grows
Turn on dashboards, alerts, and access controls (see §8.5 and §8.6) on day one so the first surprise is caught by an alert, not an invoice.

#### Worked example — size to the recent trend, not the lifetime average
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

### 8.4 How to monitor consumption after conversion

Informatica meters IPU usage automatically and exposes it to you so there are no black boxes:

- **Automatic, in-product tracking.** "Usage is tracked automatically within the product." [Pricing FAQ]
- **Real-time consumption dashboard.** Administrators can "monitor usage via a dashboard" and see consumption in real time. [Pricing FAQ]
- **Threshold alerts.** Admins can "set consumption threshold alerts," and "alerts are sent when specific usage thresholds are reached." [Pricing FAQ]
- **Per-service access control.** Admins can "control which user has access to each service," which is a direct lever for capping where IPUs can be spent. [Pricing FAQ]

#### Operational Insights and the admin/monitor surfaces
- **Operational Insights** is Informatica's monitoring surface for the platform — it provides visibility into Secure Agent health, job execution, and usage/consumption trends across the org, which makes it a natural home for consumption tracking and capacity planning. *[verify current Operational Insights consumption/metering feature set against docs.informatica.com — the docs portal was not directly retrievable at time of writing]*
- The **IDMC Administrator / Monitor** consoles expose organization-level metering and consumption reporting, letting you attribute usage by service and drill into what is driving draw-down. *[verify exact report/menu names in your org's current release]*

### 8.5 FinOps and governance practices to avoid overage surprises

Treat IPUs like any other consumption-based cloud spend:

- **Assign an owner.** A named FinOps/platform owner watches the consumption dashboard on a regular cadence (weekly early on).
- **Set alerts at multiple thresholds** (e.g., early-warning and near-limit) rather than a single ceiling.
- **Attribute consumption** to teams/workloads so runaway jobs are traceable to a source.
- **Right-size runtimes.** Because compute is metered with a **4-core minimum**, oversized or idle agents and unnecessary concurrency inflate Compute Units. Consolidate and schedule deliberately.
- **Optimize the heavy hitters.** Inefficient mappings, full reloads where incremental would do, and chatty API patterns all consume IPUs; tuning them is direct savings.
- **Hold periodic consumption reviews.** Informatica offers **IDMC Overage Protection**, which lets Informatica and the customer "meet quarterly to review Customer's IPU consumption rate and ensure Customer is properly subscribed for IPUs on a go-forward basis," with the stated purpose of helping the customer "optimize the efficiency of its IPU consumption to avoid unforeseen fees." [CPDS §IDMC – Overage Protection]
- **Re-baseline at renewal** using actual metered consumption, not the original estimate.

### 8.6 What happens if you exceed the commit

Overage is a managed, contractual event, not a service interruption:

> *"Informatica monitors Customer's consumption for overages. If Customer's consumption exceeds its subscribed number of IPUs, Customer must subscribe to additional IPUs for the remainder of the Subscription Period."* — CPDS §IDMC

If consumption exceeds the subscribed IPUs, the **overage fee set forth in the Order** for additional consumption applies. [CPDS p.30] For customers with variable or spiky workloads, **IDMC Overage Protection** exists specifically to give "flexibility in resolving unplanned increases/peaks in … IPU monthly consumption levels." [CPDS §IDMC – Overage Protection] The specific overage rate and any protection terms are set in your Order — discuss them with your account team.

### 8.7 Common pitfalls and how to de-risk

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

### 8.8 Quick checklist

- [ ] Confirmed the move is a licensing conversion (no re-platform)
- [ ] Baselined current assets, volumes, runtimes, and services
- [ ] Mapped each service to its scalar/metric/IPU rate and produced an annualized estimate
- [ ] Added growth + peak buffers; validated with the IPU estimator and account team
- [ ] Right-sized the committed IPU pool
- [ ] Enabled the consumption dashboard, threshold alerts, and per-service access controls
- [ ] Assigned a FinOps owner and set a review cadence (consider Overage Protection)
- [ ] Planned a phased onboarding and a renewal re-baseline

---

## 9. The Commercial Model (Customer View)

> **Scope note:** This section explains the **IPU commercial model at a customer-shareable level** using publicly published Informatica sources. **Specific pricing, dollar-per-IPU figures, and volume discounts are provided by Informatica per engagement and are intentionally out of scope for this document.** No pricing figures are invented here.

### 9.1 One unit for everything: the IPU

The Informatica Intelligent Data Management Cloud (IDMC) is priced with a single consumption currency — the **Informatica Processing Unit (IPU)**.

> *"Informatica Processing Unit (IPU) is a unit of capacity that can be used across eligible Cloud Services."* — CPDS, Definitions

The defining characteristic is **fungibility across the platform**: one IPU pool funds *whatever mix of eligible services you actually use*. Data Integration, Data Quality, Application/API Integration, Mass Ingestion, MDM, Data Governance and Catalog, and other eligible services all draw down from the same pool. As Informatica states, IPUs "give customers access to all eligible cloud services listed in the Cloud and Product Description Schedule," and eligible **new services are automatically activated once released** — so your entitlement grows with the platform without a new SKU each time. [Pricing FAQ]

This replaces the older world of separate, fixed entitlements per product or per user with **one flexible, consumption-based currency**.

### 9.2 How you buy: a committed pool for the subscription term

The model is a classic **committed-consumption** arrangement:

1. **You subscribe to a pool of IPUs** for the **Subscription Period** — *"the term duration of an Order"* (commonly annual; the exact term is set in your Order). [CPDS Definitions]
2. **You draw the pool down as you consume** eligible services. Each service meters usage and deducts IPUs from the pool according to its published formula (see §9.3).
3. **You track drawdown in real time** through the in-product consumption dashboard and alerts (covered in Section 8), so you always know how much of the pool remains.

Because the pool is universal, you are not forced to predict *which* services you will need in what proportion — only your **overall** consumption. If your usage shifts from, say, batch integration toward more data-quality or ingestion work, the same IPUs simply flow to where the work happens.

### 9.3 How consumption is priced across services

Even though there is one currency, different services consume IPUs at different rates that reflect the work they do. Informatica publishes, per service, a **Scalar** (what is counted), a **Metric** (the unit), and an **IPU Per Metric Unit** rate (how many IPUs each unit costs) — and the rate is frequently **tiered so it decreases at higher volumes**. [CPDS §IDMC]

Illustrative (publicly published) example:

| Service | Scalar | Metric | IPU per metric unit (tiered) |
|---|---|---|---|
| Address Verification – Batch | Rows Processed | Per Thousand Rows | 1.10 (first 30K) → 0.43 (30K–300K) → 0.09 (300K–3M) → 0.03 (>3M) |

Compute-heavy services are metered in **Compute Units**, reflecting "the general utilization of processing capacity used or consumed by each respective service" (CPU-cores, nodes, job duration, etc.), with a **4-CPU-core minimum** used in the calculation. [CPDS Definitions] When a job in one service uses another eligible service, the charge is calculated at the **highest applicable consumption rate**. [CPDS §IDMC]

> The complete, current per-service rates live in the public **CPDS** and the **Measurement Guide** (see Sources). Use them, at their current version, for any real estimate.

### 9.4 Under-consuming vs. over-consuming

The commit sets your baseline; the model then handles both directions.

**If you consume less than your commit (under-consume):**
- You have paid for a committed pool sized to your expected usage. Leftover headroom generally reflects capacity you reserved but did not use within the term.
- The practical remedy is **right-sizing at renewal** using your actual metered consumption, rather than carrying an oversized commit forward. (Any true-down or carryover behavior is a commercial matter set in your Order — confirm with your account team.) *[verify carryover/rollover terms per Order]*

**If you consume more than your commit (over-consume / overage):**
> *"Informatica monitors Customer's consumption for overages. If Customer's consumption exceeds its subscribed number of IPUs, Customer must subscribe to additional IPUs for the remainder of the Subscription Period."* — CPDS §IDMC

- Overage does **not** stop your jobs; it is handled commercially. The **overage fee set forth in the Order** applies to the additional consumption. [CPDS p.30]
- For workloads with unplanned peaks, Informatica offers **IDMC – Overage Protection**, which provides "flexibility in resolving unplanned increases/peaks in … IPU monthly consumption levels" and sets up **quarterly reviews** to keep the customer "properly subscribed for IPUs on a go-forward basis" and to "optimize the efficiency of its IPU consumption to avoid unforeseen fees." [CPDS §IDMC – Overage Protection]

### 9.5 Predictability vs. flexibility — the core tradeoff

The IPU model lets you tune where you sit on a spectrum:

| | More predictability | More flexibility |
|---|---|---|
| **Approach** | Commit a pool sized to steady-state + growth; govern tightly | Commit lean and lean on overage/peak mechanisms — or use a **Flex IPU** arrangement |
| **What you get** | A budget you can plan around; fewer surprises | Ability to absorb spikes and new workloads without re-contracting each time |
| **Watch-outs** | Over-committing ties up capacity you may not use | Uncontrolled draw-down can lead to overage fees |

Informatica also defines a **Flex IPU** option, where "the Customer is not subscribing to a specific maximum quantity of IPUs during the Subscription Period" — maximizing flexibility for organizations that prefer not to fix a ceiling. [CPDS Definitions]

**The balanced posture** most customers aim for: commit to a pool slightly above expected steady-state usage, use overage/peak flexibility to absorb the spikes, monitor consumption continuously, and re-baseline the commit at renewal.

### 9.6 Why customers move to this model

- **One currency, all services** — no per-product/per-user entitlement juggling; usage flows to where the work is.
- **Pay for what you use** — "flexible, consumption-based pricing" that lets you "pay for what you need now and scale for the future." [Pricing page]
- **Automatic access to new services** — eligible new capabilities are activated as they release, from the same pool. [Pricing FAQ]
- **Built-in visibility** — automatic usage tracking, a real-time dashboard, and threshold alerts keep spend transparent (see Section 8). [Pricing FAQ]

### 9.7 What is intentionally NOT in this document

To keep this shareable and accurate:

- **No dollar-per-IPU price.** The cost of an IPU is set commercially and is not published here.
- **No volume discounts or deal-specific percentages.** These are provided by Informatica per engagement.
- **No overage or Flex/Overage-Protection rates.** These are set in your **Order**.

For all of the above, and for a firm quote sized to your baselined usage (see Section 8), **engage your Informatica account team.** The public per-service consumption rates (scalars/metrics/IPU-per-metric-unit) that describe *how services meter* are available in the CPDS and Measurement Guide cited below.

---

## 10. Should You Move to IPUs? Reasons to Move vs. Reasons to Wait

Because IICS and IDMC are the **same platform** (see Section 1), moving to IPUs is a
**commercial and timing decision, not a technical one**. "Staying" here means staying on
**legacy per-service licensing for now** — not staying on a different or unsupported
product. The platform evolves either way. This section lays out both sides honestly so a
customer can decide *whether* and *when* to convert.

> **Honesty note (carried from Section 5).** Most reasons to *move* are about **agility,
> access, and efficiency**; most reasons to *wait* are about **predictability, governance
> readiness, and contract timing** — not about capability. And because IPUs are
> Informatica's go-forward commercial model, "wait" is usually **"wait until renewal,"**
> rarely "never."

---

### 10.1 Why a customer would move to IPUs

**1. Access the whole portfolio — and adopt new services with no new SKU.**
One pool funds any eligible service (integration, quality, governance, catalog, MDM,
API, marketplace, ingestion), and newly released eligible services auto-activate. If you
foresee needing *more than one* capability — or want the option to — IPUs remove the
procurement gate (Sections 6.1–6.2).

**2. End stranded, siloed capacity — spend follows the work.**
Under per-service licensing, surplus in one service can't fund a shortage in another. A
single pool lets budget flow to wherever the work actually is, quarter to quarter, with no
re-contracting (Sections 5.4, 6.3).

**3. Elasticity and burst for spikes and one-off events.**
Migrations, seasonal peaks, M&A ingestion, and campaign bursts are absorbed by drawing
more from the pool, instead of sizing and paying for a fixed peak tier year-round
(Section 6.3).

**4. Get the IPU-era capabilities.**
CLAIRE AI / CLAIRE GPT / Copilot, the fully-managed serverless runtime, advanced pushdown
optimization, Data Marketplace, and the Free & PayGo on-ramps are the modern, differentiating
capabilities — reachable from the same pool (Sections 6.4–6.6).

**5. Simplified procurement — one unit, one pool, fewer renewals and true-ups.**
Replace a patchwork of per-service SKUs, tiers, and connector line items with a single
consumption unit and one agreement (Section 6.7).

**6. FinOps visibility and control.**
Real-time consumption dashboards, per-scaler metering, and threshold alerts give a level of
spend transparency the fixed-SKU model never offered (Section 6.8).

**7. Utility-style financial modeling.**
Cost scales with data volume like a utility, which many finance teams find easier to model
and defend than lumpy, periodic SKU true-ups (Sections 6.8, 9.5).

**8. Future-proofing and consolidation.**
IPUs are Informatica's standard go-forward model; new services are included as they ship,
and running multiple capabilities on one platform reduces training, maintenance, and
procurement overhead (Informatica cites Nucleus Research outcomes such as ~413% ROI;
Section 6.7).

**9. Access to newer compliance authorizations, where you need them.**
Some IDMC services/environments carry authorizations (e.g., FedRAMP Moderate) that legacy
IICS does not — relevant for regulated/public-sector workloads (validate per service;
Section 5.9).

---

### 10.2 Why a customer would stay (or wait)

**1. Stable, narrow, well-understood usage.**
If you run essentially **one service at a steady volume** with no appetite for the broader
portfolio, the flexibility of IPUs is value you may not use — and a fixed per-service tier
gives a flat, predictable line item.

**2. Preference for fixed, predictable budgeting.**
Consumption cost **tracks usage**, so it varies. An organization that prizes a fixed,
capex-like number — or whose finance/procurement process favors fixed commitments over
variable consumption — may prefer the certainty of a set tier (accepting the rigidity that
comes with it).

**3. No consumption-governance capacity yet.**
The IPU model rewards active FinOps: someone must watch the dashboard, set thresholds, and
right-size the commit. **Without an owner for consumption**, an org risks overage
surprises — and until it can staff that discipline, a fixed tier is the safer short-term
posture. (The fix is to *build* that capability, then move — Section 8.5.)

**4. Contract timing.**
If you're **mid-term** on a legacy agreement with no compelling trigger, it's usually
cheaper and cleaner to **convert at renewal** than to overlap or unwind an existing
commitment early.

**5. You haven't baselined consumption yet.**
Right-sizing an IPU pool depends on a credible usage estimate. If you can't yet baseline
your workloads confidently, do the estimation work **first** (Section 8.2–8.3) so you don't
over- or under-commit — then convert. Waiting to gather data is legitimate; waiting
indefinitely is not.

**6. Aversion to variable/runaway spend.**
An inefficient mapping, a full reload where incremental would do, or unexpected growth can
raise consumption. Fixed tiers **cap** that exposure (at the cost of flexibility). If your
risk tolerance for variable spend is very low and your workload is volatile, that trade may
favor waiting until you've tuned workloads and set guardrails.

**7. Favorable legacy entitlements to retain until renewal.**
Occasionally a legacy edition, connector, or negotiated term is advantageous to keep for
the remainder of the term. Convert when that advantage lapses rather than leaving value on
the table.

---

### 10.3 A quick decision aid

| Lean toward **MOVING to IPUs** if… | Lean toward **WAITING** (convert at renewal) if… |
|---|---|
| You want (or might want) more than one service | You use exactly one service at a stable volume |
| You expect change, growth, or seasonal/burst workloads | Your usage is flat, narrow, and well-understood |
| You want CLAIRE AI, serverless, pushdown, Marketplace | You have no near-term need for newer capabilities |
| You have — or will staff — a FinOps/consumption owner | You have no owner for consumption governance yet |
| You're at (or near) renewal | You're mid-term with no compelling trigger |
| You can baseline consumption credibly | You can't yet estimate usage to right-size a pool |
| Predictability matters less than flexibility | A fixed, capped budget line matters most |

**The through-line:** if the answer is "wait," pair it with action — **baseline your
consumption now** and set a target renewal to convert. Because the platform is identical
and IPUs are the go-forward model, waiting is a *timing* choice, and the customers who wait
well are the ones who arrive at renewal already knowing the pool they need.

> See also: Section 7 (side-by-side matrix), Section 8 (how to convert and govern
> consumption), Section 9 (the commercial model), and Section 11 (FAQ) for the common
> objections that surface in this decision.

---

## 11. FAQ & Common Customer Questions

Plain-English answers to the questions customers ask most often about moving from legacy IICS licensing to the IDMC Informatica Processing Unit (IPU) consumption model. Where a specific figure or entitlement depends on your agreement, we say so — always confirm the details for your account with your Informatica team and the **Cloud and Product Description Schedule (CPDS)**.

---

#### 1. Is IICS going away?

No. **IICS (Informatica Intelligent Cloud Services) and IDMC (Intelligent Data Management Cloud) are the same platform.** IDMC is the current name for what was originally branded IICS — the platform has been expanded and infused with the CLAIRE AI engine over time, but it is a continuous evolution, not a replacement. Your services, jobs, and connections carry forward. What changes with IPUs is the *commercial model* (how you buy capacity), not the platform you run on.

#### 2. Do I have to migrate to IPUs?

The IPU consumption model is Informatica's standard, go-forward commercial model for the cloud platform, and most customers move to it at renewal or when adding capabilities. Whether and when you transition depends on your current agreement. There is **no product re-platforming required** to adopt IPUs — it is a licensing/commercial change. Talk to your Informatica account team about timing that fits your renewal cycle.

#### 3. Will IPUs cost me more?

Not inherently. IPUs are designed so you **"only pay for the services you require now"** and can redeploy that spend as needs change, rather than paying for fixed per-service tiers whether or not you use them. Whether your total cost goes up, down, or stays flat depends on your actual consumption and the mix of services you use. The key difference is that cost tracks *usage* against a committed pool instead of being fixed to tiers — which is why the model pairs with real-time dashboards and threshold alerts so you can manage it. Independent research (Nucleus Research) cited by Informatica reports outcomes such as a **413% average ROI** and multi-million-dollar savings in maintenance/administration and direct costs for the platform. [verify: your own outcome will vary with usage]

#### 4. What exactly is an IPU?

An **Informatica Processing Unit (IPU)** is a universal unit of consumption — a single "currency" you spend across **all eligible IDMC cloud services** from one pool, rather than buying each service separately. Per Informatica: *"Informatica Processing Units (IPUs) give customers access to all eligible cloud services listed in the Cloud and Product Description Schedule."* Different activities draw down IPUs at different rates (see Q8).

#### 5. How do I predict my IPU consumption?

Consumption is **calculated per "scaler"** — the meterable dimension of each service — *"based on the scaler's usage including Secure Agent, CDI‑e, Data Mass Ingestion volume and more."* To forecast:

- Estimate the workloads you'll run (integration jobs, ingestion volume, quality/profiling, API calls, MDM domain records, etc.).
- Apply the per-service consumption rates in the Informatica **Measurement/Consumption Guide** for those scalers.
- Use the real-time consumption **dashboard** once you're live to calibrate forecasts against actual drawdown.

Your Informatica team can help build an IPU estimate for your expected usage. Because usage varies, most customers size a committed pool for the baseline and rely on monitoring for the rest.

#### 6. What happens if I run out of IPUs / exceed my commit?

Your services **do not stop.** Consumption beyond your committed pool is handled as **overage / on-demand** usage, so workloads keep running and you're billed for the additional consumption per your agreement's terms. To avoid surprises, IDMC lets admins **set consumption threshold alerts** so you're notified before you approach your commit, and the dashboard shows drawdown in real time. Confirm your specific overage terms with your Informatica team. [verify: exact overage pricing/terms are agreement-specific]

#### 7. Can I still use my existing connectors and mappings?

Yes. Adopting IPUs is a commercial change, not a rebuild. Your existing **connections, mappings, mapping tasks, and taskflows continue to work** — the *services* that run them now consume from the IPU pool instead of a per-service subscription. **Connectors are the exception:** they remain a separate **tier-based subscription** (Tier A included; Tier B/C/D per End Point) and are **not** paid out of IPUs, so a higher-tier connector can still be its own line item. Confirm connector availability and tier for your sources/targets against the **Product Availability Matrix (PAM)**, as you would today. *(CPDS v39.1, pp. 7, 28.)*

#### 8. Do all services consume IPUs at the same rate?

No. **Consumption rates differ by service and by scaler.** For example, data integration metered on Secure Agent or CDI‑e usage, mass/data ingestion metered on volume, and MDM metered on a **per-domain records basis** all draw down IPUs differently. The **Measurement/Consumption Guide** publishes the per-service consumption rates so you can model each workload. This variation is intentional — it aligns cost to the actual work each service performs.

#### 9. Do I have to re-platform or rebuild?

No. There is **no re-platforming or rebuild** required to move to IPUs. You keep the same org, Secure Agents, assets, and pipelines. IPUs change how capacity is purchased and metered, not how your solutions are built or where they run.

#### 10. How do I monitor consumption?

Consumption is **tracked automatically within the product**, and *"a dashboard is available within the platform for customers to view their own usage in real time."* Administrators can **monitor usage via the dashboard and set consumption threshold alerts** to contain cost. **Operational Insights** provides broader operational and consumption monitoring across your org (agents, jobs, and usage trends). Together these support a FinOps approach to managing spend.

#### 11. Can I try a new service without a new contract?

Yes — that's a core advantage. New **eligible** services are *"automatically activated for customers once released,"* and because every eligible service draws from the same IPU pool, you can **start using a new capability without a new contract or procurement cycle.** You simply consume IPUs as you use it. (Some newer or specialized services may have specific eligibility terms — confirm in the CPDS.)

#### 12. Does the IPU model include CLAIRE / AI?

Yes. **CLAIRE**, Informatica's metadata-driven enterprise AI engine, is embedded across IDMC and works within the platform you're already consuming. That includes **CLAIRE Copilot** (proactive, in-workflow guidance for data professionals), **CLAIRE GPT** (natural-language interaction to discover, analyze, and execute data tasks), and **CLAIRE Agents**. CLAIRE also *"helps optimize costs with enhanced performance for hyperscalers and ecosystems."* [verify: specific CLAIRE feature availability by service/edition]

#### 13. Is my data / security posture affected?

No — the commercial model doesn't change your security architecture. You continue to run **Secure Agents** in your environment (or use Informatica-managed serverless runtime), and Informatica maintains its enterprise **security, scale, and compliance certifications** for the platform. Data residency, encryption, access controls, and governance operate the same way regardless of whether you're licensed per-service or on IPUs. Confirm specific certifications and controls relevant to your industry with your Informatica team.

#### 14. How is this different from just buying more of a service?

Buying more of a *service* (the legacy approach) locks additional spend to that one service and its tier — and unused capacity is stranded. Buying **IPUs** buys **flexible capacity that any eligible service can draw on.** If your integration workload grows but your quality workload shrinks, the same pool absorbs the shift automatically — no new SKU, no re-tiering, no amendment. You're buying *the ability to do data management*, not a fixed quantity of one product.

#### 15. What is a "committed pool" vs. "PayGo"?

A **committed pool** is a quantity of IPUs you commit to over a term (typically for a better effective rate and a predictable baseline); you draw down against it as you consume. **PayGo (pay-as-you-go)** lets you consume without a large upfront commit — useful for trials, spiky, or exploratory workloads — and pay for what you use. Many customers combine a committed baseline with on-demand/overage for elasticity. [verify: PayGo and commit options available to you are agreement-specific]

#### 16. What is "drawdown" and how does it work?

**Drawdown** is the process of consuming IPUs from your committed pool as jobs and services run. Each metered activity (per its scaler) subtracts IPUs from the pool. The real-time dashboard shows drawdown so you can see how fast the pool is being consumed and project when you'll reach your commit — which is what the **threshold alerts** are for.

#### 17. Can I move spend between services during my term?

Yes. Because all eligible services share one IPU pool, spend naturally flows to whatever you consume — you can **"swap for new services as needed"** without renegotiating per-service tiers. This is the flexibility that per-service IICS licensing didn't offer.

#### 18. Does adopting IPUs affect performance or runtime choices?

No — if anything it broadens them. You can run on **Secure Agents**, on Informatica-managed **serverless** runtime, and use **Advanced Pushdown Optimization (APDO)** to push transformations into your cloud data warehouse/lake for performance and efficiency. All of these are metered through IPU consumption, so you choose the runtime that fits the workload and pay for what it uses.

#### 19. Who administers IPU usage and access?

The **IDMC administrator** can *"control which user has access to each service, monitor usage via a dashboard, and set consumption threshold alerts to ensure cost containment."* This gives a central owner (often a platform or FinOps team) the levers to govern both access and spend across the org.

#### 20. Where do I find the authoritative consumption rates and terms?

The **Cloud and Product Description Schedule (CPDS)** defines eligible services and terms, and the Informatica **Measurement/Consumption Guide** publishes per-service/per-scaler consumption rates. The in-product **usage dashboard** and **Operational Insights** show your actual consumption. For anything specific to your account (commit size, overage, PayGo, connector entitlements), confirm with your Informatica account team.

---

## 12. Glossary

Concise definitions of the key terms used throughout this knowledge base. Terms are grouped into **Platform & branding**, **Services & capabilities**, **Runtime & optimization**, and **Commercial / consumption model**. Where a definition depends on your specific agreement, confirm details in the **Cloud and Product Description Schedule (CPDS)** and the Informatica Measurement/Consumption Guide.

---

### Platform & branding

**IICS (Informatica Intelligent Cloud Services)**
The original brand name for Informatica's cloud data management platform. It is the predecessor name for what is now called IDMC; the two refer to the same continuously evolving platform, not two separate products.

**IDMC (Intelligent Data Management Cloud)**
Informatica's current name for its cloud-native data management platform — described by Informatica as "a cloud-native platform that helps organizations discover, connect and manage data across hybrid and multi-cloud environments" and "the most complete microservices-based, API-driven, AI-powered iPaaS." IDMC is IICS expanded and infused with the CLAIRE AI engine, delivering integration, quality, governance, catalog, MDM, marketplace, and API capabilities from one platform.

**CLAIRE**
Informatica's metadata-driven **enterprise AI engine**, described as "the only enterprise AI built on deep metadata insight." CLAIRE automates thousands of data management tasks across IDMC and includes **CLAIRE Copilot** (proactive, in-workflow guidance), **CLAIRE Agents** (autonomous agents that plan and reason to solve data challenges), and CLAIRE GPT (below).

**CLAIRE GPT**
The conversational, generative-AI interface of CLAIRE. It lets users "converse with your data in natural language to instantly discover, analyze, and even execute complex data tasks," aiming to turn every employee into a data expert.

---

### Services & capabilities

**CDI (Cloud Data Integration)**
IDMC's core service for building data pipelines — AI-powered, largely no-code ETL/ELT integration across multi-cloud and hybrid sources and targets. Often the foundational service on which other services build.

**CAI (Cloud Application Integration)**
IDMC's service for real-time application and process integration — connecting applications and data through APIs, events, and orchestrations (process automation and app-to-app integration).

**Data Ingestion & Replication (CMI / Cloud Mass Ingestion)**
The service family for ingesting and replicating data at scale — batch and real-time — including database, file, application, and streaming ingestion and change data capture (CDC). Historically referred to as **Cloud Mass Ingestion (CMI)**; consumption is often metered on ingestion volume.

**CDQ (Cloud Data Quality)**
IDMC's service for profiling, cleansing, standardizing, validating, and monitoring data quality — including data observability — so downstream data is trusted and fit for use.

**CDGC (Cloud Data Governance & Catalog)**
IDMC's service for metadata management, data cataloging, lineage, business glossary, classification, and governance — helping organizations discover, understand, and govern their data assets. (Related to Informatica's broader "Data Governance, Access & Privacy" capabilities.)

**MDM / Customer 360 / Business 360**
**MDM (Master Data Management)** creates trusted, mastered "golden records" for core business entities. **Customer 360**, and the broader **Business 360** family (e.g., Supplier 360, Product 360), are prebuilt 360-degree applications built on MDM for specific domains. In the IPU model, MDM is typically metered on a **per-domain records basis**.

**Data Marketplace**
An internal, shopping-style experience where users discover, request, and access governed data assets and data products across the organization — promoting reuse and self-service while maintaining governance.

**API Center / API Management**
IDMC capabilities to design, publish, secure, deploy, and monitor APIs — exposing integrations and data as managed APIs for internal and external consumers. (Related capability: **Cloud B2B Gateway** for onboarding B2B trading partners.)

**Cloud Integration Hub (CIH)**
A publish-and-subscribe **data hub** that lets applications share data through a central hub rather than many point-to-point integrations, reducing redundant data movement and simplifying integration topologies.

---

### Runtime & optimization

**Secure Agent**
A lightweight, Informatica-managed runtime engine you install in your own environment (on-premises or in your cloud) to securely run jobs and connect to sources/targets without exposing them directly to the internet. It is a common **scaler** for metering integration consumption.

**Serverless runtime**
An Informatica-managed, elastic compute option that runs jobs without you provisioning or maintaining Secure Agent infrastructure. Compute scales on demand and consumption is metered as you use it — reducing operational overhead.

**Advanced Pushdown Optimization (APDO)**
A technique that pushes transformation logic **down into the target cloud data warehouse or data lake** (e.g., Snowflake, Amazon Redshift, Google BigQuery, Databricks) so processing runs where the data lives, improving performance and cost efficiency instead of moving data out to a separate engine.

**Operational Insights**
Informatica's monitoring capability that provides visibility into the health and operation of your IDMC environment — Secure Agents, jobs/tasks, and usage/consumption trends — supporting proactive operations and FinOps-style cost management. [verify: exact metrics/scope by edition]

---

### Commercial / consumption model

**IPU (Informatica Processing Unit)**
The **universal unit of consumption** in IDMC — a single "currency" spent across all eligible cloud services from one pool. Per Informatica, "Informatica Processing Units (IPUs) give customers access to all eligible cloud services listed in the Cloud and Product Description Schedule." Different services/scalers draw down IPUs at different rates.

**PayGo (Pay-as-you-go)**
A consumption option to use services and pay for what you consume without a large upfront commitment — useful for trials, exploratory, or spiky workloads. [verify: availability and terms are agreement-specific]

**Metering**
The automatic measurement of service usage that determines IPU consumption. "IPU consumption is calculated per scaler, based on the scaler's usage including Secure Agent, CDI‑e, Data Mass Ingestion volume and more," and "usage is tracked automatically within the product."

**Scaler**
The specific meterable dimension of a service used to calculate consumption (for example, Secure Agent usage, CDI‑e, or Data Mass Ingestion volume). Each service maps to one or more scalers with published consumption rates.

**Drawdown**
The process of consuming IPUs from your committed pool as metered activities run. Each job/service subtracts IPUs from the pool; the in-product dashboard shows drawdown in real time.

**Overage**
Consumption **beyond your committed IPU pool**, handled as additional on-demand usage so workloads keep running; it is billed per your agreement's terms. Threshold alerts help you anticipate it. [verify: overage pricing/terms are agreement-specific]

**Committed pool (Committed IPUs)**
A quantity of IPUs a customer commits to over a term, providing a predictable baseline (and typically a better effective rate) that you draw down against as you consume. Often paired with on-demand/overage for elasticity.

**Operational Insights** — *see Runtime & optimization above* (also central to consumption monitoring).

**PAM (Product Availability Matrix)**
Informatica's authoritative reference listing supported versions, platforms, connectors, browsers, and configurations for a product or release. Use it to confirm what is supported/available for your environment (e.g., connector availability).

**Connector**
A prebuilt adapter that lets Informatica services read from and write to a specific source or target system (databases, applications, files, cloud services, APIs, etc.). Connectors are used as part of normal service consumption; check the PAM for availability.

**Org (Organization)**
A logical tenant/workspace in IDMC that contains your users, roles, connections, assets, runtime environments, and licenses/consumption. An org is the top-level container for administering access and monitoring usage; larger customers may operate sub-organizations.

**Pod / POD**
The infrastructure "point of deployment" — a regional cloud environment (cell/cluster) where your IDMC org is hosted. Your pod determines the base URL/data center region your org runs in; knowing your pod matters for API endpoints, regional data residency, and support.

---

## Sources & References

Every non-obvious claim in this knowledge base traces to the canonical, de-duplicated citation registry: [`sources/SOURCES.md`](./sources/SOURCES.md). Published IPU consumption rates are quoted from the **Informatica Cloud & Product Description Schedule (CPDS) v39.1, effective June 5, 2026**; items marked `[verify]` are gated or unconfirmed and are tracked at the bottom of `sources/SOURCES.md` for the next fact-checking pass.
