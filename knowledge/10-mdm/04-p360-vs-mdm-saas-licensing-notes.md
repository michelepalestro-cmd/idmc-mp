# P360 vs MDM SaaS & Licensing Notes

**Answers:** Is "Product 360" the AWS-hosted PIM (P360 Cloud Edition) or the Product 360 app inside MDM SaaS, and how do
I tell which one an org holds? How is MDM SaaS licensed and metered, and which integration work its bundle covers?

**Read when:** an org or document mentions Product 360; scoping or sizing MDM work; deciding whether a flow draws on the
MDM bundle or the IPU pool.

**Key rules:**
- P360 Cloud Edition has no REST API (marker files, an ActiveVOS console, support tickets); the MDM SaaS Product 360
  app shares the REST runtime plane (L-MDM-055).
- Decide which product an org holds from privileges, roles and design objects, never from `products[]` (L-MDM-055,
  L-MDM-011).
- MDM SaaS is licensed by records, and its bundled rights cover only flows where MDM is the sole source or target
  (L-MDM-056).
- There is no documented per-record IPU rate: measure with metering exports before and after a run (L-MDM-057).
- Trial or embedded entitlement says nothing about a production licence (L-MDM-058).

**Related:** [MDM Runtime vs Design](01-mdm-saas-runtime-vs-design.md) ·
[Business 360 Modeling & Match-Merge](03-business-360-modeling-match-merge.md) ·
[IPU Model (mechanics)](../13-ipu-cost/01-ipu-model-mechanics.md) ·
[Lessons: MDM](lessons.md)

**Last verified:** 2026-10-03

> **Summary.** "Product 360" names two different things: the AWS-hosted PIM product, and the Product 360 app inside MDM
> SaaS (Business 360), which sits on the same REST-reachable platform as Customer 360. MDM SaaS is metered outside the
> IPU pool; everything outside its bundle draws on the IPU pool.

---

## 1. Two products behind one name (L-MDM-055)

| | Product 360 Cloud Edition (P360) | MDM SaaS / Business 360 (Customer, Supplier, Product, Reference 360) |
|---|---|---|
| Hosting | AWS-hosted PIM, a separate product | IDMC pod, `<pod>-mdm.<domain>` |
| REST API | none | runtime plane: ingest, read, entity-xref, search, Reference 360 search |
| Deploying configuration | upload an empty marker file (`do_deploy.txt`, `do_deploy_web.txt`) into an S3 customization folder that a cron job scans | Business 360 Modeler |
| Restarting | marker files (`stop_server.txt`, `restart_server.txt`) | not applicable (hosted) |
| Workflows | deploy through the ActiveVOS console UI | Business 360 Console jobs |
| Environment promotion (DEV, QA, PROD) | an Informatica support ticket with a window of at least 4 hours | migration export and import of design objects |
| "Headless" means | scripting S3 file drops | REST calls plus a few UI design steps |
| Documentation | MDM Product 360 Cloud Edition Configuration and Customization Guide (v10.0 read) | Customer 360 SaaS guide, Business 360 docs |

Rule: never design MDM SaaS automation from P360 pages, and never answer a P360 question with MDM SaaS evidence.

---

## 2. Which one does this org have? (L-MDM-055, L-MDM-011)

1. Read the identity Login `effectivePrivileges` (or `GET /public/core/v3/privileges`) and grep for product prefixes:
   `p360`, `catalog.item`, `s360`, `supplier360` for the 360 apps; `mdm.asset.be`, `mdm.asset.srcsystem`,
   `execute.mdm.flows`, `manage.mdm.jobs` for MDM SaaS itself.
2. Check roles: MDM Designer, Customer 360 Data Steward, Manager or Analyst.
3. Check design objects: BUSINESS_ENTITY and other `MDM_*` objects in `GET /public/core/v3/objects`.
4. Open the console app switcher: which 360 apps load without a license wall.
5. Ignore the login `products[]` list: it can show only "Integration Cloud" on an org entitled to MDM.

An org with zero P360-family privileges holds no P360, whatever a document or a deck says. An org with MDM privileges
but no modeled content holds MDM SaaS and simply has nothing deployed yet.

---

## 3. MDM SaaS licensing: bundles in, bundles out (L-MDM-056)

Per the Informatica Cloud Product Description Schedule v39.1 (effective 2026-06-05), MDM SaaS is its own license,
metered by unconsolidated records, not IPUs. It bundles services **only where MDM is the sole source or target of the
data**:

| Bundled with MDM SaaS (data into or out of MDM) | Needs the IPU pool (or its own license) |
|---|---|
| Data Integration with the Business 360 connector and transformations, for loads into or out of MDM | Integration between non-MDM systems |
| Data Synchronization where MDM is the source or target | Data quality work between non-MDM systems |
| Ingestion and replication of Business 360 events | Standalone Mass Ingestion into non-MDM targets |
| DQ assets used for MDM (cleanse, verify, parse, deduplicate, profiling, exception management) | Address verification consumption (a Premium Address Cleansing pack or IPUs) |
| Application Integration (Process Designer and Process Server, OData) for MDM | Standalone CAI and API Center |
| API Gateway; named users; sandboxes; hierarchy management | All of CDGC: catalog, governance, scanners |

How to apply it: classify each flow by its endpoints. A CAI process that updates MDM from a CRM event is inside the
bundle; the same process writing CRM to a warehouse is not. When a proposal mixes both, size MDM as the record-based
line and everything else against the IPU pool.

---

## 4. Metering (L-MDM-057, L-MDM-058)

- MDM (and Operational Insights) meter outside the IPU pool; connectors are tier-licensed per endpoint rather than
  IPU-metered (CPDS v39.1).
- The Customer 360 docs give **no per-record IPU rate**. A near-empty org's metering export showed only an API
  Center baseline line, which is not an MDM rate.
- To learn a real unit cost, take a metering export before and after an ingest and before and after a match/merge
  run, and diff the MDM meter lines. Until then, do not extrapolate a cost to a large record count.
- MCP calls are billed as the underlying service; a fuzzy lookup through the Customer Identification MCP server
  consumes the MDM or IDMC service it wraps.
- Entitlement on a trial or embedded org (roles, privileges and feature flags that show nearly the whole suite) says
  nothing about what a production commercial license includes.

Metering mechanics and rate cards are covered by the IPU lessons linked above.

---

## 5. Sizing and scoping cautions for MDM

| Caution | Why |
|---|---|
| Keep MDM scoped to a curated, business-relevant population | Operating caps (search and export 10,000 per query, CSV import 100,000 rows, job queueing) and record-based licensing make a full estate of tens of millions of rows the wrong target; route the rest to the warehouse and catalog |
| Measure divergence before promising reconciliation | Mirrored sources give match/merge nothing to resolve (L-MDM-045) |
| Plan the design clicks and the metered first run explicitly | Model publish, source systems, match and survivorship are UI; the first native run is metered (L-MDM-053) |
| Keep DaaS enrichment off unless you have data for it | Supplier-entity enrichment bills per external lookup (L-MDM-040) |
| Name things honestly | A SQL dedup layer is not MDM; "golden record" means MDM in Informatica terms (L-MDM-052) |

---

## 6. The MDM SaaS apps and how they appear

| App | UI path on `<pod>-mdm` | Runtime entity ids seen | Privilege prefixes |
|---|---|---|---|
| Customer 360 | `/ui-x360-app/app/c360/` | `c360.person`, `c360.organization` | `mdm.*`, Customer 360 roles |
| Supplier 360 | `/s360` | `s360.supplier` | `s360`, `supplier360` |
| Product 360 app (inside MDM SaaS, not P360 Cloud Edition) | `/p360` | `p360.item` | `p360`, `catalog.item` |
| Reference 360 | `/rdm-ui/` | reference data sets (search via `/rdm-service/external/v1/search`) | reference-data privileges |
| Multidomain MDM | `/ui-x360-app/app/mde` | your own business entities | `mdm.asset.be` and related |
| Business 360 Console and Modeler | `/ui-config-app` | not applicable | `mdm.asset.*`, `manage.mdm.jobs` |

Source systems use dotted ids of the form `c360.<system>.system`. The ids above came from record exports and
console views; your org's own entities have their own runtime ids ([Runtime vs Design](01-mdm-saas-runtime-vs-design.md)
section 3).

---

## 7. Questions to settle before quoting or designing

| Question | Short answer | Lesson |
|---|---|---|
| Is this org on P360 Cloud Edition or on MDM SaaS? | Read the privileges and design objects; ignore `products[]` | L-MDM-055, L-MDM-011 |
| Can the whole MDM flow be automated? | Run time yes (ingest, read, search, export); design and job runs are Business 360 UI steps | L-MDM-004 |
| Can a script deploy the model? | No public route; plan one Modeler step (its exact form, Save or Publish, is disputed) and prove it with the ingest gate | L-MDM-005, L-MDM-007 |
| Does the MDM license cover the integration and CAI work? | Only for data moving into or out of MDM | L-MDM-056 |
| What does a record cost in IPUs? | MDM is record-licensed; record-processing cost is unknown until measured with before/after metering | L-MDM-057 |
| Can P360 be automated over REST? | No: marker files, the ActiveVOS console and support tickets | L-MDM-055 |
| Does a trial org's entitlement carry over? | No: confirm the production order | L-MDM-058 |

Sources behind this page: the Cloud Product Description Schedule v39.1 packaging section (bundles and metering), the
MDM Product 360 Cloud Edition Configuration and Customization Guide v10.0, the Customer 360 SaaS guide (April 2026),
and privilege and object reads on two orgs.

---

## 8. Overturned beliefs (this area)

| Belief | Believed | Overturned by |
|---|---|---|
| The Product 360 documentation describes the MDM you have | to 2026-07-26 | L-MDM-055 (L-MDM-067) |
| MDM / Customer 360 is not licensed because the login products list shows only Integration Cloud | 2026-07-04 to 07-06 | L-MDM-011 (L-MDM-066) |
