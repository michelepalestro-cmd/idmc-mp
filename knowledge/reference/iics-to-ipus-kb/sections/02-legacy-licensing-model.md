# 2. The Legacy IICS Licensing Model

## What "legacy licensing" means here

Before Informatica moved to consumption-based **IPU** pricing (covered in later sections), Informatica cloud was licensed the way most enterprise SaaS was licensed at the time: you **subscribed to specific services, at specific capacity, with specific entitlements**, for a fixed term. In IICS terms, an organization's entitlements were expressed as **licenses**, and Informatica's own administration model still describes those licenses in three categories:

> "Licenses are categorized as **edition** licenses, **connector** licenses, and custom licenses."
> — Informatica documentation, *License categories*

Those licenses collectively **"determine the IDMC subscription level for the organization and provide access to IDMC features, connectors, and bundles."** Understanding these three categories — plus the practical constraints they created — is the whole story of "the legacy model," and it explains exactly *why* Informatica (and its customers) moved to IPUs.

---

## The building blocks of the legacy model

### 1. Per-service / per-product subscriptions

The legacy model was **service-centric**. You bought the services you intended to use — most commonly **Cloud Data Integration (CDI)** — and each additional capability was a **separate line item**. Want application/API integration? That was **Cloud Application Integration (CAI)**, purchased separately. Want data-quality cleansing and matching? **Cloud Data Quality (CDQ)**, separately. Mass ingestion, API management, B2B, MDM — each was its **own SKU with its own subscription**.

The practical effect: your contract was a **stack of independent subscriptions**, each sized and priced on its own, each with its own capacity and renewal.

### 2. Edition licenses (feature/usage tiers)

Within a service, what you could actually *do* was governed by an **edition license**. Informatica describes editions as coming in two forms:

- **Feature-based editions**, which unlock specific platform capabilities. Per Informatica's documentation, edition licenses unlock IDMC capabilities such as **"Data Integration mapping tasks,"** business-services components, and fine-grained security. Higher editions unlocked more advanced task types, connectors, and administrative/security features.
- **Usage-based editions**, which grant access **"using a pre-paid consumption model."** (This second form is essentially the mechanism that the modern IPU model generalizes across the whole platform.)

In the classic IICS commercial model, customers typically bought a **named feature edition per service** — the higher the edition, the broader the capability set — and were **capped at that edition's feature set** until they purchased an upgrade. [verify: the specific marketed edition-tier names/labels used in a given customer's IICS-era order documents — these varied by service and over time]

### 3. Connector licenses (connectivity entitlements)

Connectivity was licensed **separately from the service itself**. Informatica's documentation defines connector licenses as those that **"provide connectivity to entities such as Amazon Redshift, Microsoft SQL Server, and Oracle."** In practice this meant your subscription came with a **defined set of connectors**, and connecting to a source or target **outside that entitled set required buying additional connector licenses** (often sold as connector packs).

This is one of the most important — and most frequently painful — characteristics of the legacy model: **the systems you could integrate were bounded by what you had licensed**, not by what the platform technically supported.

### 4. Custom licenses, bundles, and packages

Beyond editions and connectors, Informatica also issued **custom licenses** covering **"features, packages, or bundles"** that sat outside a standard edition. Where a custom license overlapped an edition, **"the terms of the custom license override the terms of the edition license."** Trial subscriptions were a related concept — a trial **"might provide limited access to the features, connectors, and packages that are associated with the license."** Bundles let Informatica package specific capability + connector combinations for particular use cases, but they were still **fixed grants of specific entitlements**.

### 5. Fixed processing capacity and true-ups

Each subscribed service was sized to a **defined capacity/processing tier** — for example, a level of data volume, rows, compute, or a comparable metric appropriate to that service. If actual usage **exceeded the contracted capacity**, the customer generally had to **"true up"**: purchase additional capacity, often at renewal or via a mid-term amendment, to bring the entitlement back in line with real usage. [verify: "true-up" was a general enterprise-subscription mechanism applied to IICS; the exact contractual trigger and cadence were defined per agreement rather than by a single published rule]

---

## Why the legacy model was rigid — the constraints customers actually hit

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

## How this sets up the move to IPUs

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

## Sources

- Informatica docs — License categories (edition, connector, and custom licenses; editions are feature-based or usage-based; usage-based uses a "pre-paid consumption model"; connector licenses "provide connectivity to entities such as Amazon Redshift, Microsoft SQL Server, and Oracle"; custom licenses override editions on overlap; licenses "determine the IDMC subscription level"): https://docs.informatica.com/cloud-common-services/administrator/current-version/organization-administration/licenses/license-categories.html
- Informatica docs — License types (trial subscriptions and access to "the features, connectors, and packages that are associated with the license"): https://docs.informatica.com/cloud-common-services/administrator/current-version/organization-administration/licenses/license-types.html
- Informatica — Cloud Integration pricing (contrast: "flexible, consumption-based pricing"; access to "all eligible cloud services"; per-scaler metering): https://www.informatica.com/products/cloud-integration/pricing.html
- Informatica — "The truth about Informatica pricing" blog (IPU contrast with seat/per-service models; shift usage without "another procurement cycle"; access to all IPU-supported services "from the get-go"): https://www.informatica.com/blogs/the-truth-about-informatica-pricing.html
- EconoTimes — "Informatica Delivers the Industry's Next-generation iPaaS" (IICS GA Dec 19, 2017; service-centric iPaaS context): https://www.econotimes.com/Informatica-Delivers-the-Industrys-Next-generation-iPaaS-1066596
