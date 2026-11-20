# 12. Glossary

Concise definitions of the key terms used throughout this knowledge base. Terms are grouped into **Platform & branding**, **Services & capabilities**, **Runtime & optimization**, and **Commercial / consumption model**. Where a definition depends on your specific agreement, confirm details in the **Cloud and Product Description Schedule (CPDS)** and the Informatica Measurement/Consumption Guide.

---

## Platform & branding

**IICS (Informatica Intelligent Cloud Services)**
The original brand name for Informatica's cloud data management platform. It is the predecessor name for what is now called IDMC; the two refer to the same continuously evolving platform, not two separate products.

**IDMC (Intelligent Data Management Cloud)**
Informatica's current name for its cloud-native data management platform — described by Informatica as "a cloud-native platform that helps organizations discover, connect and manage data across hybrid and multi-cloud environments" and "the most complete microservices-based, API-driven, AI-powered iPaaS." IDMC is IICS expanded and infused with the CLAIRE AI engine, delivering integration, quality, governance, catalog, MDM, marketplace, and API capabilities from one platform.

**CLAIRE**
Informatica's metadata-driven **enterprise AI engine**, described as "the only enterprise AI built on deep metadata insight." CLAIRE automates thousands of data management tasks across IDMC and includes **CLAIRE Copilot** (proactive, in-workflow guidance), **CLAIRE Agents** (autonomous agents that plan and reason to solve data challenges), and CLAIRE GPT (below).

**CLAIRE GPT**
The conversational, generative-AI interface of CLAIRE. It lets users "converse with your data in natural language to instantly discover, analyze, and even execute complex data tasks," aiming to turn every employee into a data expert.

---

## Services & capabilities

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

## Runtime & optimization

**Secure Agent**
A lightweight, Informatica-managed runtime engine you install in your own environment (on-premises or in your cloud) to securely run jobs and connect to sources/targets without exposing them directly to the internet. It is a common **scaler** for metering integration consumption.

**Serverless runtime**
An Informatica-managed, elastic compute option that runs jobs without you provisioning or maintaining Secure Agent infrastructure. Compute scales on demand and consumption is metered as you use it — reducing operational overhead.

**Advanced Pushdown Optimization (APDO)**
A technique that pushes transformation logic **down into the target cloud data warehouse or data lake** (e.g., Snowflake, Amazon Redshift, Google BigQuery, Databricks) so processing runs where the data lives, improving performance and cost efficiency instead of moving data out to a separate engine.

**Operational Insights**
Informatica's monitoring capability that provides visibility into the health and operation of your IDMC environment — Secure Agents, jobs/tasks, and usage/consumption trends — supporting proactive operations and FinOps-style cost management. [verify: exact metrics/scope by edition]

---

## Commercial / consumption model

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

## Sources

- Informatica — Cloud Data Integration / Cloud pricing (IPU, scaler, metering, dashboard, per-domain MDM): https://www.informatica.com/products/cloud-integration/pricing.html
- Informatica — CLAIRE AI (CLAIRE, CLAIRE GPT, CLAIRE Copilot, CLAIRE Agents): https://www.informatica.com/platform/claire-ai.html
- Informatica — Cloud Integration / IDMC iPaaS (service portfolio, iPaaS description): https://www.informatica.com/products/cloud-integration.html
- Informatica — Intelligent Data Management Cloud (IDMC definition, CLAIRE): https://www.informatica.com/products/intelligent-data-management-cloud.html
