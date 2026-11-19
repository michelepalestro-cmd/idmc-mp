# 11. FAQ & Common Customer Questions

Plain-English answers to the questions customers ask most often about moving from legacy IICS licensing to the IDMC Informatica Processing Unit (IPU) consumption model. Where a specific figure or entitlement depends on your agreement, we say so — always confirm the details for your account with your Informatica team and the **Cloud and Product Description Schedule (CPDS)**.

---

### 1. Is IICS going away?

No. **IICS (Informatica Intelligent Cloud Services) and IDMC (Intelligent Data Management Cloud) are the same platform.** IDMC is the current name for what was originally branded IICS — the platform has been expanded and infused with the CLAIRE AI engine over time, but it is a continuous evolution, not a replacement. Your services, jobs, and connections carry forward. What changes with IPUs is the *commercial model* (how you buy capacity), not the platform you run on.

### 2. Do I have to migrate to IPUs?

The IPU consumption model is Informatica's standard, go-forward commercial model for the cloud platform, and most customers move to it at renewal or when adding capabilities. Whether and when you transition depends on your current agreement. There is **no product re-platforming required** to adopt IPUs — it is a licensing/commercial change. Talk to your Informatica account team about timing that fits your renewal cycle.

### 3. Will IPUs cost me more?

Not inherently. IPUs are designed so you **"only pay for the services you require now"** and can redeploy that spend as needs change, rather than paying for fixed per-service tiers whether or not you use them. Whether your total cost goes up, down, or stays flat depends on your actual consumption and the mix of services you use. The key difference is that cost tracks *usage* against a committed pool instead of being fixed to tiers — which is why the model pairs with real-time dashboards and threshold alerts so you can manage it. Independent research (Nucleus Research) cited by Informatica reports outcomes such as a **413% average ROI** and multi-million-dollar savings in maintenance/administration and direct costs for the platform. [verify: your own outcome will vary with usage]

### 4. What exactly is an IPU?

An **Informatica Processing Unit (IPU)** is a universal unit of consumption — a single "currency" you spend across **all eligible IDMC cloud services** from one pool, rather than buying each service separately. Per Informatica: *"Informatica Processing Units (IPUs) give customers access to all eligible cloud services listed in the Cloud and Product Description Schedule."* Different activities draw down IPUs at different rates (see Q8).

### 5. How do I predict my IPU consumption?

Consumption is **calculated per "scaler"** — the meterable dimension of each service — *"based on the scaler's usage including Secure Agent, CDI‑e, Data Mass Ingestion volume and more."* To forecast:

- Estimate the workloads you'll run (integration jobs, ingestion volume, quality/profiling, API calls, MDM domain records, etc.).
- Apply the per-service consumption rates in the Informatica **Measurement/Consumption Guide** for those scalers.
- Use the real-time consumption **dashboard** once you're live to calibrate forecasts against actual drawdown.

Your Informatica team can help build an IPU estimate for your expected usage. Because usage varies, most customers size a committed pool for the baseline and rely on monitoring for the rest.

### 6. What happens if I run out of IPUs / exceed my commit?

Your services **do not stop.** Consumption beyond your committed pool is handled as **overage / on-demand** usage, so workloads keep running and you're billed for the additional consumption per your agreement's terms. To avoid surprises, IDMC lets admins **set consumption threshold alerts** so you're notified before you approach your commit, and the dashboard shows drawdown in real time. Confirm your specific overage terms with your Informatica team. [verify: exact overage pricing/terms are agreement-specific]

### 7. Can I still use my existing connectors and mappings?

Yes. Adopting IPUs is a commercial change, not a rebuild. Your existing **connections, mappings, mapping tasks, and taskflows continue to work** — the *services* that run them now consume from the IPU pool instead of a per-service subscription. **Connectors are the exception:** they remain a separate **tier-based subscription** (Tier A included; Tier B/C/D per End Point) and are **not** paid out of IPUs, so a higher-tier connector can still be its own line item. Confirm connector availability and tier for your sources/targets against the **Product Availability Matrix (PAM)**, as you would today. *(CPDS v39.1, pp. 7, 28.)*

### 8. Do all services consume IPUs at the same rate?

No. **Consumption rates differ by service and by scaler.** For example, data integration metered on Secure Agent or CDI‑e usage, mass/data ingestion metered on volume, and MDM metered on a **per-domain records basis** all draw down IPUs differently. The **Measurement/Consumption Guide** publishes the per-service consumption rates so you can model each workload. This variation is intentional — it aligns cost to the actual work each service performs.

### 9. Do I have to re-platform or rebuild?

No. There is **no re-platforming or rebuild** required to move to IPUs. You keep the same org, Secure Agents, assets, and pipelines. IPUs change how capacity is purchased and metered, not how your solutions are built or where they run.

### 10. How do I monitor consumption?

Consumption is **tracked automatically within the product**, and *"a dashboard is available within the platform for customers to view their own usage in real time."* Administrators can **monitor usage via the dashboard and set consumption threshold alerts** to contain cost. **Operational Insights** provides broader operational and consumption monitoring across your org (agents, jobs, and usage trends). Together these support a FinOps approach to managing spend.

### 11. Can I try a new service without a new contract?

Yes — that's a core advantage. New **eligible** services are *"automatically activated for customers once released,"* and because every eligible service draws from the same IPU pool, you can **start using a new capability without a new contract or procurement cycle.** You simply consume IPUs as you use it. (Some newer or specialized services may have specific eligibility terms — confirm in the CPDS.)

### 12. Does the IPU model include CLAIRE / AI?

Yes. **CLAIRE**, Informatica's metadata-driven enterprise AI engine, is embedded across IDMC and works within the platform you're already consuming. That includes **CLAIRE Copilot** (proactive, in-workflow guidance for data professionals), **CLAIRE GPT** (natural-language interaction to discover, analyze, and execute data tasks), and **CLAIRE Agents**. CLAIRE also *"helps optimize costs with enhanced performance for hyperscalers and ecosystems."* [verify: specific CLAIRE feature availability by service/edition]

### 13. Is my data / security posture affected?

No — the commercial model doesn't change your security architecture. You continue to run **Secure Agents** in your environment (or use Informatica-managed serverless runtime), and Informatica maintains its enterprise **security, scale, and compliance certifications** for the platform. Data residency, encryption, access controls, and governance operate the same way regardless of whether you're licensed per-service or on IPUs. Confirm specific certifications and controls relevant to your industry with your Informatica team.

### 14. How is this different from just buying more of a service?

Buying more of a *service* (the legacy approach) locks additional spend to that one service and its tier — and unused capacity is stranded. Buying **IPUs** buys **flexible capacity that any eligible service can draw on.** If your integration workload grows but your quality workload shrinks, the same pool absorbs the shift automatically — no new SKU, no re-tiering, no amendment. You're buying *the ability to do data management*, not a fixed quantity of one product.

### 15. What is a "committed pool" vs. "PayGo"?

A **committed pool** is a quantity of IPUs you commit to over a term (typically for a better effective rate and a predictable baseline); you draw down against it as you consume. **PayGo (pay-as-you-go)** lets you consume without a large upfront commit — useful for trials, spiky, or exploratory workloads — and pay for what you use. Many customers combine a committed baseline with on-demand/overage for elasticity. [verify: PayGo and commit options available to you are agreement-specific]

### 16. What is "drawdown" and how does it work?

**Drawdown** is the process of consuming IPUs from your committed pool as jobs and services run. Each metered activity (per its scaler) subtracts IPUs from the pool. The real-time dashboard shows drawdown so you can see how fast the pool is being consumed and project when you'll reach your commit — which is what the **threshold alerts** are for.

### 17. Can I move spend between services during my term?

Yes. Because all eligible services share one IPU pool, spend naturally flows to whatever you consume — you can **"swap for new services as needed"** without renegotiating per-service tiers. This is the flexibility that per-service IICS licensing didn't offer.

### 18. Does adopting IPUs affect performance or runtime choices?

No — if anything it broadens them. You can run on **Secure Agents**, on Informatica-managed **serverless** runtime, and use **Advanced Pushdown Optimization (APDO)** to push transformations into your cloud data warehouse/lake for performance and efficiency. All of these are metered through IPU consumption, so you choose the runtime that fits the workload and pay for what it uses.

### 19. Who administers IPU usage and access?

The **IDMC administrator** can *"control which user has access to each service, monitor usage via a dashboard, and set consumption threshold alerts to ensure cost containment."* This gives a central owner (often a platform or FinOps team) the levers to govern both access and spend across the org.

### 20. Where do I find the authoritative consumption rates and terms?

The **Cloud and Product Description Schedule (CPDS)** defines eligible services and terms, and the Informatica **Measurement/Consumption Guide** publishes per-service/per-scaler consumption rates. The in-product **usage dashboard** and **Operational Insights** show your actual consumption. For anything specific to your account (commit size, overage, PayGo, connector entitlements), confirm with your Informatica account team.

## Sources

- Informatica — Cloud Data Integration / Cloud pricing (IPU model, FAQ, scalers, dashboard, auto-activation, benefits, ROI): https://www.informatica.com/products/cloud-integration/pricing.html
- Informatica — CLAIRE AI (CLAIRE, CLAIRE GPT, CLAIRE Copilot, CLAIRE Agents): https://www.informatica.com/platform/claire-ai.html
- Informatica — Intelligent Data Management Cloud (IDMC definition, CLAIRE): https://www.informatica.com/products/intelligent-data-management-cloud.html
- Informatica — Cloud Integration / IDMC iPaaS (service portfolio): https://www.informatica.com/products/cloud-integration.html
