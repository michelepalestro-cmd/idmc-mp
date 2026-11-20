# 1. History & Naming: From IICS to IDMC

## The one-sentence summary

**"Moving from IICS to IPUs" does not mean moving to a different product.** It means moving from the **legacy Informatica Intelligent Cloud Services (IICS) per-service licensing model** to the modern **Intelligent Data Management Cloud (IDMC) IPU consumption-based licensing model**. The platform your teams log into, the connectors they use, and the services they run are the **same underlying cloud**. What changes is the **commercial and packaging model** underneath it — and, over time, how much broader that platform has become.

This section explains the naming, the timeline, and the precise relationship between "IICS" and "IDMC" so that everyone — customers and account teams alike — is working from the same map.

---

## What IICS was

**IICS = Informatica Intelligent Cloud Services**, Informatica's original cloud-native data-management and integration-platform brand. Informatica announced general availability of Informatica Intelligent Cloud Services in **December 2017**, positioning it as **"the industry's next-generation iPaaS"** (integration Platform as a Service). It was built from the ground up on cloud-native frameworks — a microservices architecture designed to run integration, and later a growing set of data-management services, as cloud services rather than as software you installed and ran yourself.

IICS was the cloud successor to Informatica's earlier cloud integration offering (commonly referred to as *Informatica Cloud*). Informatica itself is a long-established data-management company, **founded in 1993** by Gaurav Dhillon and Diaz Nesamoney, so IICS represented the cloud-native chapter of a much longer product history rather than the company's first product.

In its IICS era, the platform was organized primarily around **discrete cloud services** you licensed individually — most prominently **Cloud Data Integration (CDI)**, with adjacent services such as **Cloud Application Integration (CAI)**, **Cloud Data Quality (CDQ)**, **Cloud Mass Ingestion**, and others available as separate purchases. That per-service structure is the heart of the "legacy licensing model" covered in Section 2.

---

## The IDMC era

**IDMC = Intelligent Data Management Cloud.** Informatica formally unveiled the Intelligent Data Management Cloud at **Informatica World in April 2021**, with then-CEO **Amit Walia** presenting it as **"the industry's most comprehensive, AI-powered, end-to-end data management platform."** Informatica described it as an **"AI-Powered, Cloud-First, Cloud-Native, End-to-End Platform"** that is **"micro-services based and API-driven, scaling for all enterprise workloads with elastic and serverless processing."**

Two points matter for anyone tracking the naming:

- **It was an expansion and unification, not a from-scratch rebuild.** IDMC is the umbrella brand that brought Informatica's cloud services — data integration, application/API integration, data quality, data cataloging and governance, master data management, and more — under a **single, unified platform** with a shared metadata foundation. The IICS services customers already knew became services *within* IDMC.
- **The "~2022" perception is real but imprecise.** Because the IDMC brand was introduced in 2021 and then rolled out heavily across Informatica's marketing, documentation, and packaging through 2021–2022, many customers first *encountered* the IDMC name around 2022. The formal introduction, however, was **April 2021**. [verify: exact first public use of the "IDMC" name may predate the April 2021 unveiling in some materials]

### What actually changed at the rebrand

| Dimension | IICS framing | IDMC framing |
|---|---|---|
| **Brand / umbrella** | "Intelligent Cloud Services" — integration-led | "Intelligent Data Management Cloud" — full data-management portfolio |
| **Scope** | Integration and adjacent cloud services, licensed individually | One platform spanning integration, quality, catalog, governance, MDM, API/app integration, and AI/agent capabilities |
| **AI** | AI/ML assistance present (CLAIRE) | **CLAIRE® AI at the core**, positioned as an "AI copilot," later extended with CLAIRE GPT natural-language experiences |
| **Metadata** | Per-service | **Unified metadata foundation** — a "metadata system of intelligence" spanning the platform |
| **Commercial model** | Per-service subscriptions, editions, connector entitlements (see Section 2) | **Consumption-based IPU pricing** across eligible services (see Sections 3+) |

The key idea: **the rebrand consolidated a portfolio and put AI and shared metadata at the center**, and it was paired with a move toward the consumption-based IPU commercial model. The plumbing customers were already using did not get thrown away — it was unified under a broader, AI-forward umbrella.

### CLAIRE — the AI through-line

**CLAIRE** is Informatica's metadata-driven AI engine. Informatica states that **"CLAIRE is at the core of the Intelligent Data Management Cloud,"** and today positions it as an **"AI copilot"** that **"automates thousands of data management tasks,"** with **CLAIRE GPT** adding natural-language interaction. CLAIRE existed in the IICS era, but it became a defining, front-and-center element of the IDMC story.

---

## Why customers still see and hear "IICS"

Even though **IDMC is the current umbrella brand**, the "IICS" name is still very much alive in day-to-day use. This is normal and expected — it does **not** mean a customer is on an old or unsupported product. Common reasons:

- **Login URLs and pod hostnames.** Customers log in through URLs such as **`dm-us.informaticacloud.com`**, and the sign-in page itself still reads **"Log in to Informatica Intelligent Cloud Services."** The regional pod naming (e.g., `dm-us`, `dm-em`, `dm-ap`) predates the IDMC brand and remains in use.
- **Legacy contracts and order documents.** Agreements, SKUs, and renewal paperwork signed during the IICS era continue to reference "Intelligent Cloud Services" and per-service line items even as the platform itself has moved forward.
- **Documentation, APIs, and product internals.** Many REST endpoints, administrative concepts, and older knowledge-base and documentation pages still use "IICS" terminology. License administration, for example, is still expressed in terms of **edition, connector, and custom licenses** (see Section 2).
- **Habit and institutional memory.** Teams that adopted the platform as "IICS" often keep calling it that, the way people still say "Informatica Cloud."

**Bottom line for account conversations:** "IICS" and "IDMC" refer to the **same living platform**. IICS is the original/legacy brand for the cloud services; IDMC is the current umbrella brand for the unified, AI-powered platform those services now live inside.

---

## The precise relationship (say it this way)

- **Same platform, evolving brand.** IDMC is the umbrella; the IICS services are part of it. There was no forced re-platforming or data migration caused by the name change itself.
- **Broader portfolio.** Under IDMC, Informatica pulled its cloud data-management capabilities — integration, data quality and observability, cataloging, governance and privacy, MDM and 360 applications, API and B2B, and AI/agent engineering — into one place with shared metadata.
- **AI-forward.** CLAIRE moved from "a feature" to "the core."
- **A new commercial model.** The IDMC era is the era of **consumption-based IPU pricing**, replacing the older per-service subscription approach.
- **Even the vendor name is evolving.** Following Salesforce's acquisition of Informatica (completed in November 2025), current pages are branded **"Informatica from Salesforce."** This is a corporate/branding change layered on top of the same IDMC platform, and is separate from the IICS→IDMC and licensing-model story.

So when someone says **"we're going from IICS to IPUs,"** translate it internally as: *"We're staying on the same Informatica cloud platform (now branded IDMC), and we're moving our commercial model from legacy per-service IICS licensing to the modern IPU consumption model."* Everything else in this KB builds on that single clarification.

---

## Sources

- Informatica — Intelligent Data Management Cloud (product overview): https://www.informatica.com/products/intelligent-data-management-cloud.html
- Informatica — Cloud Integration / iPaaS (product page, IDMC framing): https://www.informatica.com/products/cloud-integration.html
- Informatica — Cloud Integration pricing (consumption-based / IPU context): https://www.informatica.com/products/cloud-integration/pricing.html
- PR Newswire — "Informatica Unveils Industry's First Intelligent Data Management Cloud" (April 13, 2021; Informatica World; Amit Walia; CLAIRE at core; consumption-based pricing): https://www.prnewswire.com/news-releases/informatica-unveils-industrys-first-intelligent-data-management-cloud-the-foundation-of-digital-transformation-301267932.html
- EconoTimes — "Informatica Delivers the Industry's Next-generation iPaaS" (IICS GA, Dec 19, 2017): https://www.econotimes.com/Informatica-Delivers-the-Industrys-Next-generation-iPaaS-1066596
- Wikipedia — Informatica (company founding 1993; corporate timeline; Salesforce acquisition completed Nov 18, 2025): https://en.wikipedia.org/wiki/Informatica
- Informatica IICS sign-in page (login/pod URL still branded "Intelligent Cloud Services"): https://dm-us.informaticacloud.com/identity-service/home
- Informatica docs — License categories (edition/connector/custom licenses still in use): https://docs.informatica.com/cloud-common-services/administrator/current-version/organization-administration/licenses/license-categories.html
