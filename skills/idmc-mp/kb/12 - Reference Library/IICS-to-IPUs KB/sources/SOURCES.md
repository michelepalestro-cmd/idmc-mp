# SOURCES — IICS to IPUs KB

The canonical, de-duplicated citation registry for this knowledge base. Every non-obvious
claim in the sections traces back to one of these. Each entry notes **what it confirms**
and the **access date**; `[verify]` marks sources that were gated/unretrievable and need
an authenticated or repeat check.

Per-agent raw citation logs from the initial build are retained alongside this file as
`_agent1-sources.md` … `_agent5-sources.md` (scratch; this file is the merged canonical
version). See [`../AGENTS.md`](../AGENTS.md) for how to add sources.

---

## Primary Informatica — platform & product

- **Intelligent Data Management Cloud (product overview)** — IDMC as a "unified
  cloud-native platform"; portfolio (integration, quality & observability, app/API
  integration, catalog, governance, marketplace, MDM/360, CLAIRE); "pay only for what you
  use." Accessed 2026-09-03.
  <https://www.informatica.com/products/intelligent-data-management-cloud.html>
- **Cloud Integration / iPaaS (product page)** — IDMC described as "microservices-based,
  API-driven, AI-powered iPaaS"; service portfolio. Accessed 2026-09-03.
  <https://www.informatica.com/products/cloud-integration.html>
- **Cloud Data Integration (product page)** — ETL/ELT/Spark/fully-managed serverless;
  pushdown optimization; consumption-based pricing; FinOps optimization. Accessed 2026-09-03.
  <https://www.informatica.com/products/cloud-data-integration.html>
- **"What is Cloud Data Integration?" (article)** — elastic/serverless compute clusters
  that scale and shut down; serverless Spark with dynamic scaling and auto-tuning; pushdown
  optimization. Accessed 2026-09-03.
  <https://www.informatica.com/resources/articles/what-is-cloud-data-integration.html>
- **CLAIRE AI (platform page)** — CLAIRE as metadata-driven enterprise AI within IDMC;
  CLAIRE GPT (natural language), CLAIRE Copilot (in-workflow), CLAIRE Agents (autonomous);
  spans applicable IDMC services + MDM SaaS; at-no-additional-cost promotional period for
  certain generative/headless features referenced through Jan 31, 2027. Accessed 2026-09-03.
  <https://www.informatica.com/platform/claire-ai.html>

## Pricing, consumption model & the IPU rates

- **Cloud Integration Pricing page (IPU model & FAQ)** — flexible, consumption-based
  pricing; "pay for what you need now and scale for the future"; IPUs "give customers
  access to all eligible cloud services listed in the Cloud and Product Description
  Schedule"; consumption "calculated per scaler … Secure Agent, CDI-e, Data Mass Ingestion
  volume and more"; usage tracked automatically; real-time dashboard; consumption threshold
  alerts; per-service access control; new eligible services auto-activated; MDM offered
  per-domain records; Nucleus Research 413% ROI and savings figures. Accessed 2026-09-03.
  <https://www.informatica.com/products/cloud-integration/pricing.html>
- **Cloud & Product Description Schedule (CPDS), v39.1 — "Informatica from Salesforce,"
  effective June 5, 2026 (PDF)** — the authoritative public consumption matrix and
  definitions: IPU ("a unit of capacity that can be used across eligible Cloud Services");
  Compute Units (min 4 CPU-cores), Rows Processed, Data Volume, API Calls, Daily Assets
  Stored, Events; per-service Scalar/Metric/IPU-per-metric-unit tiered rates for CDI,
  Advanced DI, CAI, API Center, Application/Database/File/Streaming Ingestion and CDC,
  DI-CDC, SQL ELT, CDQ/Advanced DQ, DQ Real-Time, Address Verification & Geo Coding, DGC
  Catalog/Governance/Scanner/Metadata Record Consumption, Data Access Management, Data
  Marketplace, Integration Hub, INFACore, B2B, CLAIRE GPT, Secrets Manager, CMK, Additional
  Org; monthly IPU vs annual Flex IPU; no carry-over; overage ("must subscribe to
  additional IPUs for the remainder of the Subscription Period"; overage fee per Order);
  IDMC – Overage Protection (quarterly reviews; 25%-over-2-consecutive / 3-of-5-months /
  100%-in-one-month triggers); cross-service "highest applicable rate" and
  natural-language-query rules; MDM SaaS per-Unconsolidated-Record and Operational Insights
  per-instance treatment; Subscription Period and Flex IPU definitions; IDMC section points
  to the IICS PAM (confirming one platform); **connector tiers (pp. 7, 28): Tier A included,
  Tier B/C/D subscribed separately per End Point and NOT IPU-metered.** Accessed 2026-09-03.
  <https://www.informatica.com/content/dam/informatica-com/en/docs/informatica-cloud-and-product-description-schedule.pdf>
- **Measurement Guide (Informatica Network / Knowledge Base article DOC-19140)** — the
  authoritative per-scalar measurement methodology cited by the pricing page. **`[verify]`**
  — login-gated; did not render for anonymous retrieval on 2026-09-03. Confirm exact
  computation detail via an authenticated Informatica Network session.
  <https://knowledge.informatica.com/s/article/DOC-19140>
- **Free Cloud Data Integration & Data Loader** — Data Loader–Free (unlimited) and CDI–Free
  (up to 20M rows / 10 compute hours per month) on-ramps; self-service signup; lowers
  barriers and minimizes trial/adoption risk. Accessed 2026-09-03.
  <https://www.informatica.com/free-data-integration.html>
- **"The truth about Informatica pricing" (blog)** — IPU contrast with seat/per-service
  models; shift usage without "another procurement cycle"; access to IPU-supported services
  "from the get-go." Accessed 2026-09-03.
  <https://www.informatica.com/blogs/the-truth-about-informatica-pricing.html>

## Informatica documentation — licensing mechanics

- **License categories (Cloud Common Services / Administrator docs)** — licenses are
  "edition, connector, and custom licenses"; editions are feature-based or usage-based
  (usage-based uses "a pre-paid consumption model"); connector licenses "provide
  connectivity to entities such as Amazon Redshift, Microsoft SQL Server, and Oracle";
  custom licenses override editions on overlap; licenses "determine the IDMC subscription
  level." (Note: `docs.informatica.com` returned 403 to anonymous fetchers on 2026-09-03;
  content confirmed via on-page navigation / cached retrieval.) Accessed 2026-09-03.
  <https://docs.informatica.com/cloud-common-services/administrator/current-version/organization-administration/licenses/license-categories.html>
- **License types (Administrator docs)** — trial subscriptions and access to "the features,
  connectors, and packages that are associated with the license." Accessed 2026-09-03.
  <https://docs.informatica.com/cloud-common-services/administrator/current-version/organization-administration/licenses/license-types.html>

## Press & corporate history

- **PR Newswire — "Informatica Unveils Industry's First Intelligent Data Management Cloud"
  (April 13, 2021)** — IDMC unveiled at Informatica World by CEO Amit Walia; "cloud-native,
  micro-services based and API-driven"; consumption-based pricing; "CLAIRE … is at the core
  of the Intelligent Data Management Cloud." Accessed 2026-09-03.
  <https://www.prnewswire.com/news-releases/informatica-unveils-industrys-first-intelligent-data-management-cloud-the-foundation-of-digital-transformation-301267932.html>
- **EconoTimes — "Informatica Delivers the Industry's Next-generation iPaaS" (Dec 19, 2017)**
  — IICS general availability; "next-generation iPaaS." Accessed 2026-09-03.
  <https://www.econotimes.com/Informatica-Delivers-the-Industrys-Next-generation-iPaaS-1066596>
- **Wikipedia — Informatica** — company founded 1993; corporate timeline; Salesforce
  acquisition completed November 18, 2025 ("Informatica from Salesforce" branding).
  Corroborating/secondary source. Accessed 2026-09-03.
  <https://en.wikipedia.org/wiki/Informatica>
- **Informatica IICS sign-in page** — login/pod URL still branded "Log in to Informatica
  Intelligent Cloud Services" (evidence the IICS name persists in-product). Accessed 2026-09-03.
  <https://dm-us.informaticacloud.com/identity-service/home>

---

## Non-public source (not part of the shareable citation set)

- **An internal, de-identified capability comparison** (imported 2026-09-03) — capability facts folded
  into §5/§6/§7 (Secure Agent compliance exposure, MDM/DQ/Governance/Privacy availability, CLAIRE ~90%
  wrangling reduction, FedRAMP, burst capacity, dynamic reallocation, cloud-agnostic positioning,
  utility-style modeling). It is not part of this KB, and no customer or deal detail from it is used.
  Its own "no per-connector SKU / draws from IPU pool" phrasing was **corrected** against CPDS v39.1
  pp. 7, 28 (connectors are tier-based and not IPU-metered).

---

## Standing `[verify]` items (for the next fact-checking pass)

- **Measurement Guide (DOC-19140)** — confirm exact per-scalar computation detail via an
  authenticated Informatica Network session.
- **FedRAMP Moderate** — confirm exactly which IDMC services/environments carry the
  authorization (per-service, not blanket); IICS is not FedRAMP-listed.
- **Exact first public use of the "IDMC" name** — April 2021 unveiling confirmed; earlier
  internal/marketing use possible.
- **Marketed legacy edition-tier labels** — docs confirm editions exist; the specific
  IICS-era tier names are per-Order. (Connector mechanics now resolved: tier-based, Tier A
  included, B/C/D per End Point, not IPU-metered — CPDS v39.1 pp. 7, 28.)
- **"PayGo" metered billing mechanics** and **IPU carryover/rollover** on under-consumption
  — governed by the customer's Order, not the public CPDS.
- **IPU estimator** exact tool name / public availability.
- **Operational Insights** and **Administrator/Monitor** exact consumption-report names by
  current release.
- **Standalone CLAIRE (non-GPT) metering** — CLAIRE GPT is metered (50 IPU/1K queries); the
  always-on CLAIRE engine appears embedded rather than a separate scalar.
- **"Ecosystem pushdown" branding** — "pushdown optimization" / APDO confirmed; that exact
  label not verified.
