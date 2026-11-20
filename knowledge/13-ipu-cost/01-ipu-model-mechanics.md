# IPU model: how consumption is metered

**Answers:** What is an IPU and how does each service meter against it? How is a compute hour computed? What is free
and what is metered? What sits outside the IPU pool? How do I size a workload in IPUs?

**Read when:** estimating IPU consumption for a design, scoping a customer workload, or explaining why a meter moved;
not for what an IPU costs (that is a term of each customer's Order).

**Key rules:**
- An IPU is one pool that every eligible service draws at its own published rate; what an IPU costs comes from the
  customer's Order, never from this KB (L-IPU-001, L-IPU-019).
- Development, reads, export/import and taskflow orchestration are free; runs, previews, scans and serverless hours
  are metered (L-IPU-005).
- Classify each flow first, then ask for counts and sizes with a complexity level, never runtimes (L-IPU-008).
- Derive volumes from business drivers, not from discovery sample files (L-IPU-008).
- Report steady state plus a peak band (growth x cadence x batched versus unbatched API writes), and check the target
  API's concurrency limits (L-IPU-008, L-IPU-009).
- Keep the unit (per month or per year) in every variable and output (L-IPU-016).

**Related:** [02 Metering & Consumption Exports](02-metering-consumption-exports.md) · [03 Entitlement, Licenses & Job Caps](03-entitlement-licenses-job-caps.md) · [IICS-to-IPUs KB](../reference/iics-to-ipus-kb/start-here.md) · [Measurement Guide](https://docs.informatica.com) · [Lessons: IPU, Metering & Licensing](lessons.md)

**Last verified:** 2026-10-03

> An IPU is one fungible credit that every eligible IDMC service draws down at its own published rate (compute hours,
> rows, GB, API calls, assets, queries). MDM SaaS, Operational Insights and connectors sit outside the pool. Monthly
> subscriptions are measured per month. This page covers only how consumption is computed, from CPDS v39.1 and the
> Measurement Guide 39.1 (both published by Informatica at https://docs.informatica.com).

Evidence state: sections 1-5 are **documented** (vendor CPDS and Measurement Guide) unless a lesson says proven;
sections 6-7 mix documentation with field measurements.

---

## 1. What an IPU is

(L-IPU-001.) The CPDS definition: 'a unit of capacity that can be used across eligible Cloud Services'.

- **One pool.** A subscription is one quantity of IPUs, aggregated across the customer's orgs and sub-orgs; any eligible
  service can draw it. New eligible services are activated for the pool automatically.
- **Per-service rates.** Each service has a scalar (what is counted), a metric (the unit) and an IPU-per-metric-unit
  rate, usually tiered so the marginal rate falls with volume.
- **Monthly measurement.** All scalars and IPU consumption are measured per month.
- **Cross-service rules.** A job that uses components of another service is charged at the highest applicable rate; a
  natural-language (CLAIRE GPT) query that triggers another service also consumes that service's IPUs.
- **Compute Units** measure processing capacity (cores, nodes, job duration); a minimum of four CPU cores is used.

## 2. Subscription shapes

(L-IPU-002.)

| Offering | Window | Carry-over | Beyond the subscription |
|---|---|---|---|
| IDMC - IPU | Monthly | None | Subscribe to more IPUs for the rest of the term |
| IDMC - Flex IPU | Annual | None | The overage fee in the Order |
| Unlimited - IDMC - Flex IPU | Term | n/a | No maximum; single parent org |
| IDMC - Overage Protection (with IDMC - IPU only) | Quarterly reviews | n/a | Review when over by up to 25% in 2 consecutive months or 3 of 5, or by 100% in one month |

IPU and Flex IPU must be provisioned separately and may not share an org.

## 3. How services meter

(L-IPU-003.) Published tier-1 rates from CPDS v39.1; re-verify against the current CPDS before relying on
any figure.

| Service | Scalar / metric | IPU per metric unit (tiers) |
|---|---|---|
| Data Integration | compute hours | 0.16 first 2,000 h/month; 0.025 after |
| Data Integration - Advanced Serverless | compute hours | 0.28 first 2,000 h; 0.10 after |
| Advanced Data Integration (elastic) | compute hours | 0.19 |
| SQL ELT (advanced pushdown) | million rows | 0.048 first 100M; 0.010; 0.002; 0.0003 above 5T |
| Data Quality | compute hours | 0.38 first 2,000 h; 0.152 after |
| Data Quality - Real Time | million rows | 35.0 first 12M; 26.3 after |
| Application Integration | thousand API calls | 1.453 first 20K; 1.163; 0.038; 0.032; 0.015 above 12.5M |
| API Center | million API calls | 13.33 |
| Database Ingestion - CDC | million rows | 6.5 first 15M; 0.55; 0.05 above 750M |
| DI - CDC (via CDI) | million rows | 4.88 first 15M; 0.41; 0.04 |
| Database / Application Ingestion (bulk) | GB | 0.1 first 2 TB; 0.08; 0.05; 0.018 |
| File Ingestion | GB | 0.03 first 5 TB; 0.015 |
| Streaming Ingestion | GB | 0.27 first 1 TB; 0.135 |
| DGC Catalog / Governance | daily assets | 0.83 per 100K (first 500K) / 0.95 per 1K (first 40K) |
| DGC Scanner | compute hours | 0.32 (serverless 0.56) |
| CLAIRE GPT | thousand queries | 50 |

The rate card turns usage into IPUs; the customer's Order turns IPUs into money. Pattern to scalar matters more than
data size: bulk is GB-priced and cheap, CDC is row-priced and front-loaded, batch DQ is compute hours, real-time DQ is
expensive per row, and SQL ELT pushdown falls to fractions of an IPU per million rows at scale.

## 4. How a compute hour is computed

(L-IPU-004; Measurement Guide.)

- **Data Integration** (mapping task, mapping, synchronization, data transfer): one compute hour = one job running one
  hour on the integration service using up to four CPU cores. Measured to the second, no minimum, pro-rated above four
  cores. Examples from the guide: a 90-minute job four times a day on up to 4 cores = 6 compute hours a day, 180 a month;
  a 45-minute job four times a day on 6 cores = 4 x 0.75 x 6/4 = 4.5 a day.
- **Data Replication tasks**: one compute hour per 2.5 hours of job time on the agent (up to 4 cores).
- **Serverless**: compute hours = the serverless compute-unit factor (set when the serverless runtime is configured)
  times elapsed time.
- **Application Integration**: one API call = one execution of a process, subprocess, guide or OData endpoint (each
  subprocess call adds one), not one outbound HTTP call; processes deployed to a Secure Agent also accrue compute hours.
  The same feed meters differently as a CAI process (per call) or as a CDI mapping with a REST connector (compute hours):
  confirm the build style before sizing.

**Worked arithmetic with the published rates**

| Workload | IPU per month |
|---|---|
| 3,000 DI compute hours | 2,000 x 0.16 + 1,000 x 0.025 = 345 |
| 50M CDC rows through DI - CDC | 15M x 4.88/M + 35M x 0.41/M = 73.2 + 14.35 = about 87.6 |
| 20K CAI calls | 20 x 1.453 = about 29 |
| 1,000 CLAIRE GPT questions | 50 (plus the IPUs of any service they trigger) |

## 5. Free versus metered

(L-IPU-005.)

| Free (0 IPU) | Metered |
|---|---|
| Development in any org (creating or editing tasks, mappings, connections, schedules, catalog-source configs) | Task and taskflow member runs (compute hours) |
| Taskflow and Linear Taskflow orchestration itself (the Measurement Guide) | UI data preview (charged compute hours) |
| Migration export/import and clones | Catalog scans and profiles |
| Connection create, test (a metadata handshake) and delete | DaaS lookups, address verification rows |
| User groups and role bindings | Serverless runtime hours |
| Metering-export reads | Every backing service call behind a managed MCP tool |

MCP itself was not metered during the AI Agent Engineering preview, but the CDGC, CDI, Marketplace or MDM calls behind
it bill at the normal rates: an agent looping on prompts can burn IPUs while the MCP line reads zero. Author-time work
never needs a spend gate; the run does (L-IPU-020). Job counts are a separate ledger from IPUs
([doc 03](03-entitlement-licenses-job-caps.md) section 6).

## 6. What sits outside the pool

(L-IPU-006; L-IPU-007.)

- **MDM SaaS** (Customer 360 and the other 360 apps) is licensed by unconsolidated records per data domain. Its bundle
  (Data Integration with the Business 360 connector, Data Synchronization with unlimited Secure Agents, ingestion of
  Business 360 events, DQ assets, Application Integration, API Gateway, 100 named users, sandboxes, hierarchies) applies
  only where MDM is the sole source or target. Address Verify still needs a Premium Address pack or IPUs.
  Non-MDM-to-non-MDM integration, standalone ingestion, standalone CAI/API Center and all of CDGC use the IPU pool.
- **Operational Insights** is subscribed per instance.
- **Connectors** are tier-licensed (Tier A included; Tiers B, C, D per end point) and are not IPU-metered. The
  Administrator 'Unique Endpoints' export lists each connection with its pricing tier ([doc 02](02-metering-consumption-exports.md) section 6).
- **Data Integration and Data Quality** meter separately (both compute hours) but draw one pool; DQ assets run inside a
  CDI mapping on the agent and bill as DQ hours.

## 7. Sizing method and field numbers

1. **Classify each flow** (L-IPU-008): a live database with ongoing changes = CDI + CDC (one Database
   Ingestion and Replication task does snapshot and CDC); batch reads, file drops, ETL and DQ = CDI; application writes
   and API ingests = CAI calls; a BI tool live-querying the warehouse = 0 IPU.
2. **Ask for counts and sizes, never runtimes, and derive them from business drivers** (L-IPU-008). Work
   volumes down from the drivers (sites x active customers x activity per customer x cadence), not from discovery
   sample files: in one engagement the sample-derived anchor was about 3x too low, and published industry benchmarks
   for both monthly and weekly billing cadences sided with the driver-derived figure. Give the customer three plain
   input columns that mirror the calculator's own questions, plus a computed IPU column they never fill in:

   | What the calculator asks for | How much per month | How big / how complex |
   |---|---|---|
   | database: records per month and row size | `<records>` | `<KB per row>` |
   | file: files per month and file size | `<files>` | `<MB per file>` |
   | API: calls per month | `<calls>` | n/a |
   | DQ: records per month and how thorough | `<records>` | Simple / Moderate / Complex |
   | ETL: runs per month and how complex | `<runs>` | Simple / Moderate / Complex |

   For compute-hour lines ask for the calculator's own complexity level (Simple, Moderate or Complex), never a runtime
   the customer cannot know. Footnote the units: a record is one row, and its size is the KB that row takes, not its
   number of columns; the customer gives counts and sizes and the calculator converts them to GB.
3. **Know what dominates at small volumes** (L-IPU-009): below about 1 GB a month ingestion is near 0 IPU and
   scheduled compute hours dominate; for API-write targets, batching is the lever (one call per document instead of per
   line, then bulk batches, took one flow from about 20 to 4.8 to 0.1 IPU a month). A whole small pipeline pooled to
   about 24-36 IPU a month.
4. **Model CDC explicitly** (L-IPU-011): continuous CDC keeps the warehouse bill flat and moves cost into
   IDMC; the first 15M rows a month are the expensive tier.
5. **Count pure warehouse work as 0 IPU** (L-IPU-012): BI live queries and marts built by warehouse SQL
   outside IDMC; IDMC task runs (pushdown included) are metered.
6. **Serverless trades IPUs for operations** (L-IPU-013): a Secure Agent has no runtime-hour charge (its jobs
   still meter compute hours); serverless variants cost more per unit and cannot reach private data elsewhere.
7. **Price the target too** (L-IPU-014): warehouse capacity bills separately; a pay-as-you-go Fabric capacity
   bills per second while Active.
8. **Estimator traps** (L-IPU-010): a service name that does not match the rate card exactly (the rate card
   abbreviates the CDC lines) prices at 0 with no error; keep rate-card names and metering names as separate constants
   and recalculate before trusting a total.
9. **Report steady state plus a peak band** (L-IPU-008): steady state first (about 36 IPU a month in one small
   ERP-write engagement), then a peak projection that combines growth, a faster cadence (monthly to weekly) and the
   batched-versus-unbatched band for API writes (about 100 batched to about 147 unbatched in that case, because
   per-line writes cost about 4x, L-IPU-009). Check feasibility against the target API's own concurrency limits: for
   an ERP REST target a document with nested lines is one call, and its governance limits (a base of 5-20 concurrent
   requests plus 10 per add-on licence) sat orders of magnitude above even peak volume. Below about 1 GB a month, run
   and task counts drive cost, not volume.

## 8. Rules for using these numbers

- This page stops at IPUs. What an IPU costs is set in each customer's Order; take commercial questions to the
  Informatica account team (L-IPU-019).
- Keep the unit in every variable name and output: a monthly quantity read as annual, or the reverse, is wrong
  twelvefold (L-IPU-016).
- Treat every run as spend: get and record explicit approval before burning IPUs in someone else's org
  (L-IPU-020).
- Label estimates as estimates; a trial org's zero is trial-conditional ([doc 02](02-metering-consumption-exports.md)).

## 9. Overturned beliefs (IPU model)

| Believed | Until | Now | Lesson |
|---|---|---|---|
| Connectors draw from the IPU pool | 2026-09-03 | Connectors are tier-licensed per end point | L-IPU-048 -> L-IPU-006 |
| Database Ingestion is metered as a fixed floor plus 24x7 runtime | disputed | The CPDS meters CDC per million rows and bulk per GB | L-IPU-040 |
