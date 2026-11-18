# 5. What Customers Are Locked Out Of Under Legacy IICS Licensing

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

## 5.1 Services you did not license simply are not available

Under per-service subscription licensing, you can only use the specific services on your contract. If you licensed data integration but not data quality, governance, master data management, or application/API integration, those services are **out of reach** until you negotiate and purchase them as **new SKUs**.

**Why it matters to customers**
- A data-integration team that discovers a data-quality or governance need cannot simply turn the capability on — it becomes a procurement project.
- Cross-functional initiatives (for example, a "trusted customer view" that needs integration **plus** quality **plus** MDM) require multiple separate purchases before work can even begin.
- Innovation stalls at the boundary of what was originally bought, not at the boundary of what the business needs.

The modern IDMC platform is explicitly positioned as a **unified** portfolio — Data Integration, Data Quality & Observability, Application/API Integration, Data Catalog, Data Marketplace, Governance/Access/Privacy, and MDM & 360 Applications — but under legacy per-service licensing you only get the doors you individually paid to open.

---

## 5.2 Connector count and connector-type limits

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

## 5.3 Capacity ceilings are per service — hitting the wall means a new purchase

Each legacy service is sized to a **fixed processing tier**. When a workload grows past that tier — more rows, more mappings, more compute hours, more ingestion volume — you hit a **hard ceiling**. The only way through is to **buy more capacity for that specific service**, typically as a contract amendment or a new order.

**Why it matters to customers**
- Growth is punished with friction: exactly when a project succeeds and scales, the platform forces a procurement cycle.
- Seasonal or bursty workloads (month-end close, a large one-time migration, a marketing campaign) cannot be absorbed elastically — you must size and pay for the **peak** even if you only need it occasionally.
- Capacity planning becomes a guessing game with real financial consequences for guessing wrong in either direction.

---

## 5.4 No cross-service flexibility — capacity cannot be shared or reallocated

This is the defining constraint of the legacy model. Because capacity is **siloed per service**, unused capacity in one service **cannot fund a need in another**. If you have surplus Cloud Data Integration capacity but a pressing Cloud Data Quality or MDM need, that surplus is **stranded** — it cannot be redirected.

**Why it matters to customers**
- You can be simultaneously **over-provisioned** in one service and **blocked** in another, paying for both problems at once.
- Every service is its own budget bucket, so priorities cannot flex with the business; money committed to last year's plan cannot follow this year's need.
- The organization loses the ability to reallocate spend to where value is actually being created.

---

## 5.5 Adopting a new capability means friction and new contracts

Because each capability is a separate entitlement, **trying** or **adopting** something new is not a self-service action — it is a **sales and procurement event**. Evaluating a new service typically means engaging a seller, scoping a new SKU, negotiating terms, and amending or signing a contract before hands-on work can start.

**Why it matters to customers**
- The cost of *experimentation* is high: teams cannot cheaply pilot data quality, cataloging, or MDM to see if it delivers value before committing.
- Time-to-value is dominated by procurement lead time, not by how fast the team can build.
- Genuinely useful capabilities go unexplored simply because the friction to try them is too high — the platform's breadth is invisible to the people who could use it.

---

## 5.6 Limited or no access to newer IPU-era capabilities, depending on entitlement

The IDMC platform continues to add capabilities — a **fully managed serverless runtime** and elastic Spark compute, **CLAIRE** AI (including **CLAIRE GPT** and CLAIRE Copilot/Agents), **Data Marketplace**, and low-friction **Free & PayGo** experimentation on-ramps. Under a narrow, fixed per-service entitlement, access to these newer capabilities can be **limited or unavailable** unless your specific entitlement includes them.

**Why it matters to customers**
- You may be running on a platform that has evolved substantially, yet be **fenced off** from its newest, most differentiating features.
- AI-assisted automation (metadata intelligence, natural-language data tasks, in-tool copilots) can bypass your users entirely if the entitlement predates or excludes them.
- Modern runtime options (serverless/elastic compute that scales on demand and shuts down when idle) may not be available to teams still bound to older, fixed-capacity arrangements.

> [verify] Whether a given newer capability is strictly consumption-model-only versus separately licensable under legacy terms depends on the specific entitlement and current Informatica offering terms. Availability of CLAIRE generative/headless features is also governed by deployment to a compatible POD and by current promotional terms (an at-no-additional-cost promotional period for certain CLAIRE generative and headless pre-run-time design activities was referenced through January 31, 2027).

---

## 5.7 Paying for shelfware

The mirror image of siloed capacity is **shelfware**: capacity or services you licensed but do not fully use. Because commitments are made per service and per tier up front, real-world usage rarely matches the plan — and the gap is money spent on entitlement that sits idle.

**Why it matters to customers**
- You pay for the **tier you bought**, not the value you consumed; underused services and headroom become sunk cost.
- Because that idle capacity **cannot be reallocated** (see 5.4), shelfware is pure waste rather than a reserve you can redeploy.
- Renewal conversations become contentious, because it is hard to justify or right-size spend that is fragmented across many independently-committed service lines.

---

## 5.8 Secure Agent capacity is constrained — and overages surface at renewal

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

## 5.9 Compliance authorizations (e.g., FedRAMP) may be unavailable

For public-sector or regulated workloads, authorization can gate the entire platform
decision. Legacy IICS is **not FedRAMP-listed**. Under IDMC, **FedRAMP Moderate is
available for _some_ services / environments only** — it is **not a blanket, platform-wide
authorization**, and the specific service and environment must be validated. `[verify per service]`

**Why it matters to customers**
- Assuming platform-wide compliance coverage is risky; the answer is per-service.
- Confirm FedRAMP (and any other required authorization) for the *exact* services and
  environment you intend to use before committing.

---

## Summary: What legacy IICS licensing locks out

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

## Sources

- Informatica — Cloud Data Integration Pricing (IPU / consumption model, eligible services, per-scaler metering, swap/activate new services, FinOps dashboard & threshold alerts): https://www.informatica.com/products/cloud-integration/pricing.html
- Informatica — Intelligent Data Management Cloud (IDMC) platform (unified cloud-native platform; portfolio of services): https://www.informatica.com/products/intelligent-data-management-cloud.html
- Informatica — CLAIRE AI (CLAIRE, CLAIRE GPT, CLAIRE Copilot/Agents across IDMC; promotional terms through Jan 31, 2027): https://www.informatica.com/platform/claire-ai.html
- Informatica — Cloud Data Integration product page (ETL/ELT/Spark/serverless; consumption-based pricing; intelligent optimization engine): https://www.informatica.com/products/cloud-data-integration.html
- Informatica — Free Cloud Data Integration & Data Loader (free tiers, self-service signup, lowering barriers to adoption): https://www.informatica.com/free-data-integration.html
- Informatica — "What is Cloud Data Integration?" (serverless/elastic compute clusters, pushdown optimization): https://www.informatica.com/resources/articles/what-is-cloud-data-integration.html
