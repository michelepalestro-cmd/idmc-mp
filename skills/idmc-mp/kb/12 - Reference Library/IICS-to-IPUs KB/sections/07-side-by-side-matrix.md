# 7. Legacy IICS Licensing vs IDMC IPUs — Side by Side

This section compares the **legacy IICS per-service licensing model** with the modern **IDMC Informatica Processing Unit (IPU) consumption model** across the dimensions that matter most when you plan, buy, and operate Informatica in the cloud.

> **Note on branding:** *IICS* (Informatica Intelligent Cloud Services) is the original name for Informatica's cloud platform. *IDMC* (Intelligent Data Management Cloud) is the current name for the same platform, expanded and infused with the CLAIRE AI engine. This comparison contrasts the **way capacity was traditionally licensed on IICS** (fixed, per-service subscriptions) with the **way capacity is purchased today under IDMC** (a single, flexible IPU pool). It is a *commercial and operating-model* comparison, not a comparison of two different products.

---

## Comparison matrix

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

## Strategic takeaway

The move from **per-service IICS subscriptions** to the **IDMC IPU model** is a shift from *buying discrete products* to *buying a flexible capacity to do data management*. Instead of forecasting demand for each service a year in advance — and stranding whatever you over-buy — you commit to a single pool of IPUs and spend it against whatever mix of services your teams actually need, when they need it.

The practical benefits fall into three themes:

- **Agility:** New and additional capabilities (integration, quality, governance, MDM, API management, ingestion, AI) are reachable from one pool, and newly released eligible services are auto-activated — so adoption is a product decision, not a procurement project.
- **Efficiency:** One agreement, one currency, and CLAIRE-driven optimization reduce procurement, training, and maintenance overhead, and let unused capacity flow to where it creates value rather than sitting stranded in an over-provisioned service tier.
- **Accountability:** Real-time consumption dashboards, per-scaler metering, and threshold alerts give teams FinOps-grade visibility to manage cost against the committed pool.

The trade-off to manage is **variability**: because you pay for what you consume, cost tracks workload rather than a fixed tier. The model addresses this directly with committed pools for a predictable baseline, real-time monitoring, and threshold alerts — so customers get flexibility *and* control. For most organizations, the net effect is broader access to the platform, faster innovation, and better alignment of spend to value.

## Capability availability: standalone IICS vs IDMC / IPUs

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

## Sources

- Informatica — Cloud Data Integration / Cloud pricing (IPU consumption model, FAQ, benefits): https://www.informatica.com/products/cloud-integration/pricing.html
- Informatica — Cloud & Product Description Schedule (CPDS) v39.1 (connector tiers pp. 7, 28; MDM per-record; IPU definition): https://www.informatica.com/content/dam/informatica-com/en/docs/informatica-cloud-and-product-description-schedule.pdf
- Capability-availability rows derived from an internal, de-identified capability comparison (not part of this KB; no customer or deal detail is used).
- Informatica — CLAIRE AI (CLAIRE, CLAIRE GPT, CLAIRE Copilot, CLAIRE Agents): https://www.informatica.com/platform/claire-ai.html
- Informatica — Cloud Integration / IDMC iPaaS (service portfolio): https://www.informatica.com/products/cloud-integration.html
- Informatica — Intelligent Data Management Cloud (IDMC definition, CLAIRE): https://www.informatica.com/products/intelligent-data-management-cloud.html
