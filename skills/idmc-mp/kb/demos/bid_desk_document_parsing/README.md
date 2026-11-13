# Bid Desk: document to decision

A public-sector sales team attaches solicitation PDFs (a bid packet and a signature page) to the agencies in the CRM.
One nightly IDMC pipeline reads every new file version, copies it to SharePoint, parses it with CLAIRE, checks it with
Data Quality rules, decides what the bid still needs, lands everything in Snowflake and shows it in one Tableau workbook.
The catalog shows where every number came from (lineage) and what every word means (glossary).

**Start with [BUILD.md](BUILD.md)** (the numbered rebuild). This page is the overview.

## What the audience sees

| Solicitation (synthetic) | What IDMC finds | Decision at the start (blank documents) | After the what-if (completed copies) |
|---|---|---|---|
| **ECPC-2031-07** Example County Purchasing Cooperative, janitorial bid packet (3 pages) | 8 bid-form lines, none priced; 8 Bid Proposal Page fields blank; 2 product numbers the PDF broke across a line, re-joined in Silver | **PRICE THE BID** | **FIX 2 ITEMS**: one price with 3 decimals (the agency counts two), one line without a brand |
| **EUSD-31-RFQ-04** Example Unified School District, Exhibit A signature page (1 page) | 12 vendor fields blank; certified e-signature only; an unsigned form is rejected | **SIGN THE FORM** | **SUBMIT THE FORM** |

The loop: **Run** (tonight's batch, now, about 4 minutes), **What-if** (sales attaches the completed copies as new versions of
the same CRM files, then Run), **Reset** (the originals come back as new versions, nothing is deleted, then the pipeline).

The two PDFs are SYNTHETIC: `infra/make_sample_pdfs.py` generates them (fictional agencies, every completed page stamped
SAMPLE). Swap in your own documents later: CLAIRE learns one model per layout, so a new layout is a new model, not new code.

## Architecture

```
 CRM (Salesforce)                 IDMC (one project "Bid Desk", 5 stage folders)                     Snowflake            Tableau
 Account = agency      --1--> [1 CRM Bid Documents]  -> BID_BRZ_SF_AGENCY / BID_BRZ_SF_DOCUMENT (PDF as base64)
 Files = ContentVersion        only NEW versions (lookup "read before?")                    |
                               [1b Transfer to SharePoint] --> SharePoint library: <root>/<agency> - <solicitation>/<file>
                               [2a Read the Bid Packet]   PDF bytes -> Structure Parser + CLAIRE model -> BID_BRZ_BID_PACKET
                               [2b Read the Signature Page]                                  -> BID_BRZ_SIGNATURE_PAGE
                               [3a Bid Lines DQ]  rule specs: price filled, 2 decimals, brand -> BID_SLV_BID_LINES
                               [3b Required Fields DQ] rule specs: filled in, e-mail format  -> BID_SLV_REQUIRED_FIELDS
                               [4 Bid Readiness]  counts per document -> one decision        -> BID_GLD_READINESS --> BID_V_BI_* --> 1 workbook,
                               [5 Reset] (Reset taskflow only)                                                                     6 tabs
                               Taskflows "Bid Desk - Run" / "Bid Desk - Reset"; nightly schedule prepared, not attached
                               Data Profiling: 3 profiles x 7 rule specs -> BID_DQ_SCORECARD
 Catalog (CDGC): sources "Bid Desk - Salesforce / - Snowflake / - Data Lineage" -> lineage CRM -> IDMC -> Snowflake -> BI views
                 glossary domain "Bid Desk": 13 terms linked to Snowflake columns  -> BID_LINEAGE / BID_GLOSSARY (Tableau tabs)
```

Tableau tabs: **Bid Desk** (decisions, bid form, required forms) · **Data Quality** · **Lineage** · **Glossary and Governance** ·
**Mapping** (each IDMC step) · **Parsing** (what CLAIRE read).

## IDMC services used

| Service | What it does here |
|---|---|
| Data Integration (CDI) | 8 mappings + mapping tasks, 2 linear taskflows, 1 schedule (prepared) |
| CLAIRE intelligent structure models | 2 models learned from the sample PDFs, used by a Structure Parser in 2a / 2b |
| Cloud Data Quality + Data Profiling | 7 rule specifications used in mappings 3a / 3b AND in 3 profiles (one definition, two uses) |
| Data Governance & Catalog (CDGC) | 3 catalog sources, scans with profiling, lineage connection assignment, glossary + links |
| Administrator | project, folders, connections, runtime environments; optional viewer role / group / object permissions |
| Connectors | Salesforce, Snowflake Data Cloud (key pair), SharePoint Online (delegated Entra OAuth) |

## Real vs stand-in

| System | Real or stand-in |
|---|---|
| Salesforce | REAL org of yours (a developer org works). Two Accounts + Files, loaded by `infra/sf_files.py seed` |
| SharePoint Online | REAL site of yours, written by IDMC (needs an Entra admin's consent once) |
| Snowflake | REAL account (a trial works). Everything under one schema, prefix `BID_`, guarded by a resource monitor |
| Tableau | REAL server or Cloud site of yours |
| The documents | SYNTHETIC (generated); no real agency, person or price |

Python in the runtime path, two stated walls only (everything else runs in IDMC):
1. **Reset** writes new CRM file versions over Salesforce REST from mapping 5's pre-processing command: the CDI Salesforce
   connector rejected a ContentVersion new-version insert that REST accepts (KB lesson L-CONN-115).
2. **1b** stages the newest file bytes on the agent from its pre-processing command: the SharePoint Online connector uploads
   from its `Attachment_File_Path` and CDI cannot write a binary file there itself (L-CONN-107).

## How long a rebuild takes

About half a day when the org, a Secure Agent and the four accounts exist: 1 h accounts and consent, 1 h IDMC objects and
CLAIRE models, 1-2 h mappings (six built headless by core/mapgen, ADAPTED; 2a / 2b in the designer), 1 h DQ + catalog +
glossary, 30 min Tableau and the demo loop.
Building is free; each run uses one IDMC job and a few minutes of an X-Small warehouse.

## Credentials needed (key names only; values live in your toolkit `.env`, outside this folder)

| Key | What it is | Where to get it |
|---|---|---|
| `IDMC_USER` | IDMC login name (org admin, or Designer + Operator + Admin privileges) | your IDMC org administrator |
| `IDMC_PASS` | that user's IDMC login | your IDMC org administrator |
| `IDMC_LOGIN_HOST` | the DOMAIN login host of your region, e.g. `dm-us.informaticacloud.com` | the IDMC address bar after sign-in, without the pod label |
| `SF_USERNAME` | Salesforce integration user of the IDMC connection | Salesforce Setup > Users |
| `SF_PASSWORD` | that user's Salesforce login | Salesforce Setup > Users |
| `SF_SECURITY_TOKEN` | the user's security token (empty when the agent's IP is trusted) | Salesforce: Settings > Reset My Security Token |
| `SF_INSTANCE_URL` | the org's My Domain URL | Salesforce Setup > My Domain |
| `SF_CLIENT_ID` | Connected App consumer key, client-credentials flow (seed / what-if / reset / staging) | Salesforce Setup > App Manager > your app > Manage Consumer Details |
| `SF_CLIENT_SECRET` | that Connected App's consumer secret | same page |
| `SNOWFLAKE_USER` | Snowflake service user for IDMC (key pair) | you create it (infra/snowflake/01_cost_guard_and_access.sql) |
| `SNOWFLAKE_PAT` | programmatic access token for the Snowflake SQL API (setup SQL, verify, feeds) | Snowsight > your user > Programmatic access tokens |
| `SNOWFLAKE_BI_USER` | read-only Snowflake user embedded in the Tableau data sources | you create it (role BID_READER) |
| `SNOWFLAKE_BI_PASSWORD` | that read-only user's login | set when you create it |
| `ENTRA_TENANT_ID` | Microsoft Entra tenant id | Entra admin center > Overview |
| `ENTRA_CLIENT_ID` | application id of the Entra app registration for IDMC SharePoint | Entra admin center > App registrations > your app |
| `ENTRA_CLIENT_SECRET` | a client secret of that app | App registrations > your app > Certificates & secrets |
| `SHAREPOINT_REFRESH_TOKEN` | delegated refresh token for the SharePoint audience, minted after admin consent | `infra/sharepoint_setup.py token-url` + `redeem` (BUILD step 5) |
| `TABLEAU_PAT_NAME` | Tableau personal access token name | Tableau: My Account Settings > Personal Access Tokens |
| `TABLEAU_PAT_SECRET` | Tableau personal access token secret (shown once) | same page |

On the Secure Agent host, a separate `sf.env` (0600, outside any shared folder) holds `SF_INSTANCE_URL`, `SF_CLIENT_ID`,
`SF_CLIENT_SECRET` for the two pre-processing commands, and the Snowflake private key file sits at
`snowflake.private_key_file_on_agent`.

## Folder map

| Path | What |
|---|---|
| `config.example.json` | every name and setting; copy to `config.json`. Ids the build creates go to `state/ids.json` (do not share either) |
| `ENV_KEYS.md` | the `.env` keys of this blueprint, one per line |
| `infra/` | `make_sample_pdfs.py` + `sample_docs/` (synthetic PDFs), `snowflake/*.sql` + `snowflake_sql.py` (SQL API runner), `sf_files.py` (CRM files), `sharepoint_setup.py` (consent, token, folders) |
| `idmc/` | `bid_project`, `bid_connections`, `bid_claire_models`, `bid_mappings`, `bid_dq`, `bid_taskflows`, `bid_catalog`, `bid_glossary`, `bid_access` (optional), `bid_demo` (the demo loop); `templates/` (connection bodies, 8 mapping specs, DQ rules + profiles, governance) |
| `dashboards/bid_tableau.py` | the one workbook, 6 tabs, built and published over REST |
| `verify/bid_verify.py` | `offline` (no login), `idmc`, `data` checks |
| `teardown/` | `bid_teardown.py` (ordered undo through the core library) + `99_snowflake_drop.sql` |

## Proven vs adapted

The source demo ran end to end in a real org on 2026-10-13 (run, what-if, reset, twice, through the CRM). Every REST body and
call order here comes from it. Rewritten generically for this blueprint and **not yet re-run in this form**: the names, the
synthetic documents (so the CLAIRE models, the field map and the SQL label patterns are new), the decision texts, the Tableau
workbook (live connection instead of extracts) and the lineage feed. BUILD.md marks each step PROVEN or ADAPTED.
