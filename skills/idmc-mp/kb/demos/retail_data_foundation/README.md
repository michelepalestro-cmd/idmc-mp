# Retail Data Foundation (blueprint prefix `rdf_`)

**What it shows.** A simulated multi-store retail business (customers, memberships, orders, order lines, payments,
store visits, products) whose whole data layer runs on Informatica IDMC, built headless from this folder:
every change in the operational database reaches the warehouse in seconds (CDC), a handful of real multi-transformation
mappings cleanse, de-duplicate and score customers into a golden record, data quality is measured and published as a
scorecard, governed records flow back to the operational database and to the CRM (reverse ETL, batch and real time),
and the catalog explains all of it with a business glossary, classification and lineage.

**Who it is for.** Anyone with an IDMC org, a Secure Agent, a Google Cloud project (BigQuery) and a Salesforce
Developer Edition org who wants the retail demo's IDMC layer in their own environment. Read
[BUILD.md](BUILD.md) next; it is a numbered rebuild with one command per step.

## Architecture

```
 infra/ stand-ins                     IDMC (your org, your Secure Agent)                         targets
 ----------------                     ----------------------------------                         -------
 Postgres 16 "rdf_retail"  --CDC (Database Ingestion, hot 5 s + cold 10 s tasks)----------> BigQuery rdf_cdc (MERGE)
   public.customers ...                                                                      (real-time replicas, BI)
   (seed.py + traffic.py)
        |                  --batch lane (linear taskflow tf_rdf_full, every 4 h; tf_rdf_customer on demand)
        |                     m_rdf_ingest_customers  PG -> rdf_land (4 flows, 1 job)
        |                     m_rdf_ingest_activity   PG -> rdf_land (4 flows, 1 job)
        |                     m_rdf_customer_golden   cleanse (SQL in BigQuery) -> rdf_staging.stg_customers
        |                                             survivorship -> rdf_gold.customer_golden
        |                                             Router VALID -> PG activation.customer_golden (reverse ETL)
        |                                                    else  -> rdf_gold.customer_review
        |                     m_rdf_dq_scorecard      rules -> dq_results; Aggregators + Union -> dq_scorecard
        |                     m_rdf_sales_facts       order_line_facts, store_daily_sales, visit_facts
        |                     m_rdf_crm_sync          clean-only + count gate -> Salesforce Contact (Upsert ext id)
        |
 app sign-up (traffic.py --cai) --REST--> CAI rdf_cai_customer_to_crm  (token -> Contact upsert, 0.2-2 s) --> Salesforce
                                          CAI rdf_cai_membership_to_crm (membership record, parent by external id)
 Data Quality:   CDQ rule specifications bound in Data Profiling profiles on the source tables (rdf_prof_*);
                 Address Verification through the managed MCP server dqverifyaddress (verify_address)
 Catalog (CDGC): rdf_cat_pg (PostgreSQL), rdf_cat_bq (BigQuery), rdf_cat_cdi (IICS lineage of the project);
                 auto classification on scan; glossary domain "Retail Data Foundation" (14 terms) linked to the tables
```

## IDMC services used

| Service | What this blueprint builds | Script |
|---|---|---|
| Administrator / connections | 5 connections: PostgreSQL (app role + CDC role), BigQuery V2 (CDI + Database Ingestion), Salesforce | `idmc/01_connections.py` |
| Database Ingestion (CDC) | `dbmi_rdf_cdc_hot` + `dbmi_rdf_cdc_cold`, PostgreSQL pgoutput -> BigQuery, own slot + publication each | `idmc/02_cdc.py` |
| Data Integration (CDI) | 6 consolidated mappings generated headless (spec -> IMF -> package -> import), 6 mapping tasks | `idmc/03_mappings.py` |
| Taskflows + schedules | `tf_rdf_full` (6 tasks, every 4 h), `tf_rdf_customer` (sign-up lane), `sch_rdf_every_4h` | `idmc/04_taskflows.py` |
| Application Integration (CAI) | service connector `rdf_sfdc_rest`, app connection `rdf_sfdc_rest_conn`, 2 processes | `idmc/05_cai.py` |
| Data Quality / Data Profiling | 3 profiles with rule-spec bindings; warehouse scorecard in a mapping; address verification | `idmc/06_dq.py` |
| Catalog (CDGC) | 3 catalog sources, scans (metadata, profiling, classification, lineage), glossary + links | `idmc/07_catalog.py` |

## Real vs stand-in

| Part | Here | Notes |
|---|---|---|
| Operational database | **stand-in**: PostgreSQL 16 in docker (`infra/`), synthetic dirty data | any PostgreSQL with logical decoding works |
| Front ends (web, mobile app, store tills, staff console) | **out of scope** | `infra/traffic.py` writes what they would write and calls CAI the way an app would |
| Warehouse | **real** BigQuery in your Google Cloud project | the proven path; another warehouse means new connections and SQL dialect (see BUILD.md "Other warehouses") |
| CRM | **real** Salesforce (a free Developer Edition org is enough) | needs the custom fields listed in BUILD.md step 0 |
| IDMC | **real**: your org and your Secure Agent | nothing is simulated on the IDMC side |
| BI dashboards | not included | point any BI tool at `rdf_gold.*` and `rdf_cdc.*` (the scorecard view is `rdf_gold.v_dq_scorecard`) |

## Credentials needed

Put these keys in the toolkit `.env` (outside the toolkit; `setup/.env.example`, section `[retail_data_foundation]`).
Scripts read them at run time and print key names only. Details and where to get each one: [ENV_KEYS.md](ENV_KEYS.md).

| Key | What it is |
|---|---|
| `IDMC_USER`, `IDMC_PASS`, `IDMC_LOGIN_HOST` | IDMC login (core keys); the login host is the domain host, never a pod host |
| `PG_HOST`, `PG_PORT`, `PG_DB` | how the **Secure Agent** reaches the stand-in Postgres |
| `PG_USER`, `PG_PASS` | owner / application role of the source database |
| `PG_CDC_USER`, `PG_CDC_PASS` | replication-only role for Database Ingestion |
| `BQ_PROJECT`, `BQ_KEY_FILE`, `GCS_STAGING_BUCKET` | Google Cloud project, service-account key file path, staging bucket name |
| `SF_LOGIN_URL` | Salesforce My Domain URL |
| `SF_CLIENT_ID`, `SF_CLIENT_SECRET` | Connected App (client-credentials flow) used by CAI and by verify/ |
| `SF_USERNAME`, `SF_PASSWORD`, `SF_SECURITY_TOKEN` | API-only integration user for the CDI Salesforce connection |
| `CAI_RT_BASE` | optional, printed by `idmc/05_cai.py url` after publishing |

## How long a rebuild takes

About 2-3 hours the first time on a prepared org (Secure Agent running, BigQuery project and Salesforce org ready),
most of it waiting: agent service selection (~5 min per change), the CDC initial load, the first catalog scans
(one source at a time, 10-40 min each). A repeat rebuild of the CDI + CAI layer alone is about 20 minutes.

## Evidence words

**PROVEN** = the call or pattern worked end to end in a real org in 2026-09 / 2026-10, in an earlier
(non-generic) form. **ADAPTED** = rewritten generically for this blueprint and checked offline only (compile, lint,
render, package): re-verify it in your org. BUILD.md marks every step. Count at the time of writing: 22 PROVEN,
11 ADAPTED (see the table at the end of BUILD.md).

## Folder map

```
README.md  BUILD.md  ENV_KEYS.md  config.example.json  requirements.txt
infra/      docker-compose.yml, sql/01_schema.sql, sql/02_cdc_prereqs.sql, sql/03_bigquery_ddl.sql,
            seed.py, traffic.py, bq_setup.py, pgexec.py
idmc/       00_resolve.py .. 07_catalog.py (the numbered build), sql/ (warehouse SQL of the mappings),
            mappings/rdf_specs.py (the 6 mapping specs), cai/cai_assets.py (CAI XML),
            catalog/glossary.json, templates/ (connection, CDC and catalog-source bodies),
            lib/rdf_common.py (shared helpers), (mapping generator: the toolkit's core/mapgen/)
verify/     offline_check.py (no network), e2e_check.py (sign-up -> golden -> reverse ETL -> CRM)
teardown/   teardown.py (reverse order, backup first), pg_teardown.sql
state/      written by the scripts: ids.json, packages/, rendered/ (org-specific: never share)
```
