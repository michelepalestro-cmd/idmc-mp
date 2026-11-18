# Bid Desk: the rebuild, step by step

Every command runs from this folder (`toolkit/demos/bid_desk_document_parsing/`). Every script is a **dry run** until you add
`--execute`; IDMC writes also need `--expect-org <orgIdV3>` (the core library proves the live org first). Add `--offline` to
see every request without logging in. Status per step: **PROVEN** = this call sequence worked end to end in a real org (in
an earlier, non-generic form, 2026-10-13); **ADAPTED** = rewritten generically here and not yet re-run in this form.

Read first: [The Laws of Headless IDMC](../../../knowledge/00-start-here/02-the-laws-of-headless-idmc.md) and
[Error Triage](../../../knowledge/00-start-here/04-error-triage.md).

| # | Step | Status |
|---|---|---|
| 0 | Accounts, credentials, config, org proof | PROVEN |
| 1 | Snowflake: cost guard, roles, objects | PROVEN |
| 2 | Synthetic sample documents | ADAPTED |
| 3 | CRM: agencies + files | PROVEN calls, ADAPTED script |
| 4 | Secure Agent host files | PROVEN |
| 5 | SharePoint: Entra app, consent, token, folders | PROVEN |
| 6 | IDMC project, folders, runtimes | PROVEN |
| 7 | Connections | PROVEN |
| 8 | CLAIRE models + field map | PROVEN calls, ADAPTED documents |
| 9 | Mappings + mapping tasks | PROVEN shapes, ADAPTED build route (toolkit/mapgen, offline-compiled) |
| 10 | Data Quality rule specs + profiles | PROVEN |
| 11 | Taskflows + first run | PROVEN |
| 12 | Profiling run + scorecard | PROVEN |
| 13 | Catalog sources, scans, lineage | PROVEN (feed ADAPTED) |
| 14 | Glossary + links | PROVEN |
| 15 | Tableau workbook | ADAPTED |
| 16 | The demo loop: what-if, verify, reset | PROVEN |
| 17 | Nightly schedule (prepared, not attached) | PROVEN |
| 18 | Optional: one user sees only this project | PROVEN |
| 19 | Teardown | PROVEN core tools, ADAPTED order script |

---

## 0. Accounts, credentials, config, org proof — PROVEN
**Why:** every later step reads names from `config.json` and secrets from your toolkit `.env`.
1. You need: an IDMC org with a Secure Agent group (Data Integration + Data Quality/Profiling + Metadata services enabled,
   see [Secure Agent & Connections](../../../knowledge/02-secure-agent-connections/)), CDGC, a Salesforce org, a SharePoint site,
   a Snowflake account, a Tableau server or site.
2. Put the keys of [ENV_KEYS.md](ENV_KEYS.md) into your toolkit `.env` (outside the toolkit; `IDMC_CREDS_FILE` points to it).
3. `cp config.example.json config.json` and replace every `<...>`.

```
python ../../setup/check_setup.py --demo bid_desk_document_parsing
python "../../lib/idmc_session.py" whoami
python verify/bid_verify.py offline
```
**Expect:** `whoami` prints your org name and its 22-character `orgIdV3` (use it for `--expect-org`); `offline` ends
`ALL CHECKS PASSED`. **Undo:** nothing to undo.

## 1. Snowflake: cost guard, roles, objects — PROVEN
**Why:** Bronze / Silver / Gold tables and the BI views; the resource monitor caps credits.
```
python infra/snowflake_sql.py render infra/snowflake/01_cost_guard_and_access.sql     # paste into a worksheet as ACCOUNTADMIN
python infra/snowflake_sql.py apply "infra/snowflake/0[234]*.sql" --execute
python infra/snowflake_sql.py guard
```
Then create the two users as the comments in `01_...sql` show (key-pair public key for `SNOWFLAKE_USER`, a read-only
`SNOWFLAKE_BI_USER` with role `BID_READER`) and generate `SNOWFLAKE_PAT`.
**Expect:** 8 + 12 + 11 statements `200`; `guard` shows the quota. **Verify:** `python infra/snowflake_sql.py query "SHOW TABLES LIKE 'BID_%'"`.
**Undo:** `teardown/99_snowflake_drop.sql`.
**Gotcha:** quota reached = error **090073** on every client at once (IDMC tasks, catalog profiling, Tableau, the SQL API).
Raise it: `ALTER RESOURCE MONITOR BID_GUARD SET CREDIT_QUOTA = <n>;` (L-ENV-096).

## 2. Synthetic sample documents — ADAPTED
**Why:** CLAIRE needs real PDFs of the right shape; these are fictional (no real agency).
```
python infra/make_sample_pdfs.py --check
```
**Expect:** four `OK` lines (they are shipped; without `--check` the script rewrites them). **Undo:** none.

## 3. CRM: agencies + files — PROVEN calls, ADAPTED script
**Why:** the sales team's way of working: each PDF attached to its agency as a Salesforce File.
1. Salesforce Setup > App Manager > New Connected App: enable OAuth, scope `api`, **Enable Client Credentials Flow**, run-as
   = an integration user that can create Accounts and ContentVersion (UI-only wall).
2. Seed and record the ids:
```
python infra/sf_files.py seed --execute
python infra/sf_files.py ids
python idmc/bid_mappings.py crm-ids --doc-ids <id1>,<id2>
```
**Expect:** two Accounts, two Files (v1). **Verify:** `python infra/sf_files.py status`. **Undo:** delete the two Accounts
(their Files go with them) in Salesforce; the scripts never delete CRM data.

## 4. Secure Agent host files — PROVEN
**Why:** mapping 1b and 5 run `sf_files.py` as a pre-processing command on the agent (the two stated Python walls).
On every agent of the groups in `idmc.runtime_environment[_crm]`, under `idmc.agent_root` (default `/opt/bid_desk`):
`infra/sf_files.py`, `config.json`, `sf.env` (`SF_INSTANCE_URL`, `SF_CLIENT_ID`, `SF_CLIENT_SECRET`; `chmod 600`), the empty
folder `sharepoint.download_dir_on_agent`, and the Snowflake private key at `snowflake.private_key_file_on_agent` (same path
on every agent, so a task may run on any of them). Use `idmc.agent_python` (Python 3.8+, stdlib only).
**Verify:** on the agent, `python3 /opt/bid_desk/infra/sf_files.py status --config /opt/bid_desk/config.json --env-file /opt/bid_desk/sf.env`.
**Gotcha:** a Salesforce password login depends on the agent's egress IP (L-CONN-110): run the CRM steps on an agent the
org trusts (`runtime_environment_crm`).

## 5. SharePoint: Entra app, consent, token, folders — PROVEN
**Why:** IDMC uploads each file version into one folder per solicitation.
1. Entra admin center > App registrations > New registration (single tenant), redirect URI (public client)
   `https://login.microsoftonline.com/common/oauth2/nativeclient`; Certificates & secrets > New client secret.
2. API permissions: SharePoint > Delegated > `AllSites.Write` (or `Sites.ReadWrite.All`) + `MyFiles.Write`; **Grant admin
   consent** (UI-only wall: an Entra admin; `python infra/sharepoint_setup.py consent-url` prints the URL).
3. Mint the token AFTER consent, for the SharePoint audience (not Graph):
```
python infra/sharepoint_setup.py token-url          # sign in once, copy the code
python infra/sharepoint_setup.py redeem --code <code> --out <file outside the toolkit>   # then copy the value into .env
python infra/sharepoint_setup.py check
python infra/sharepoint_setup.py mkdirs --execute
```
**Expect:** `check` lists a Write scope and `AddListItems=True`. **Undo:** delete the root folder in the library.
**Gotchas:** a Graph-scoped token passes Test Connection and browses 0 objects (L-CONN-100); a token minted before consent
keeps the read scopes, every upload is 403 (L-CONN-111); the library INSERT needs the folder to exist (L-CONN-107).

## 6. IDMC project, folders, runtimes — PROVEN
```
python idmc/bid_project.py build --execute --expect-org <orgIdV3>
python idmc/bid_project.py show
```
**Expect:** project `Bid Desk`, 5 folders, both runtime ids in `state/ids.json`. **Undo:** step 19 (the project goes last).
**Gotcha:** if the v3 create refuses the name, the script creates the fallback name and renames it through FRS (L-MIG-075).

## 7. Connections — PROVEN
```
python idmc/bid_connections.py --offline build all       # look at the bodies (secrets shown as <KEY>)
python idmc/bid_connections.py build all --execute --expect-org <orgIdV3>
python idmc/bid_connections.py test
```
**Expect:** three connections, each test `OK`. **Verify:** browse an object of each in the designer once, or run step 11.
**Undo:** `toolkit/lib/idmc_frs_delete.py v2-delete connection <id>` after all tasks are gone.
See [Connections](../../../knowledge/02-secure-agent-connections/03-connections-create-test-update-delete.md) and
[Connector Notes](../../../knowledge/02-secure-agent-connections/04-connector-notes-bigquery-postgresql-salesforce-jdbc-flat-file.md).

## 8. CLAIRE models + field map — PROVEN calls, ADAPTED documents
**Why:** CLAIRE learns each layout from the document itself; no OCR, no template code.
```
python idmc/bid_claire_models.py discover bid            # prints the groups and fields CLAIRE found (saves nothing)
python idmc/bid_claire_models.py create bid --execute --expect-org <orgIdV3>
python idmc/bid_claire_models.py create sig --execute --expect-org <orgIdV3>
python idmc/bid_claire_models.py fields bid
python idmc/bid_claire_models.py fields sig
```
**Expect:** two models in folder 2; `fields` prints the proposed map (model field -> Bronze column) and stores it in
`state/ids.json` `claire_field_map`. Edit it there if a field landed in a `TEXT_nn` slot you want named.
**Verify:** open the model in the designer (it opens like a UI-made one). **Undo:** step 19.
The six calls, auth rules and the tuning are in the script's docstring and in
[How Claude Builds Mappings Headless §10](../../../knowledge/03-cdi-data-integration/02-how-claude-builds-mappings-headless.md).
**Gotchas:** the service wants the session as cookie AND header (cookie alone = 200 `{"valid": false}`); every POST after
`validateWidget` needs `X-CSRF-TOKEN` (missing = 404, not 403); train on the completed sample so every field exists
(`claire.<key>.train_on`); `update` keeps the model id, but each parse mapping keeps a copy: Synchronize the Structure Parser.

## 9. Mappings + mapping tasks — PROVEN shapes, ADAPTED build route
**Why:** small mappings, one business step each, left to right in folder order.
```
python idmc/bid_mappings.py render          # state/specs/*.json: every name, object, SQL and id filled in for your org (to read)
python idmc/bid_mappings.py build --offline # lint + compile + package 1, 1b, 3a, 3b, 4, 5 with placeholder ids (no login)
```
**Expect (offline):** `OK` for six mappings: 1 = 9 transformations / 7 links, 1b = 6 / 5, 3a = 9 / 8, 3b = 6 / 5,
4 = 9 / 8, 5 = 3 / 2, packages under `state/packages/`, and the note that placeholder packages cannot be imported.
Then get each mapping into IDMC:
* **1, 1b, 3a, 3b, 4, 5** are built headless by the toolkit's generator (`toolkit/mapgen`, route 5: spec -> IMF JSON ->
  DTEMPLATE package -> v3 import, see [Route 5](../../../knowledge/03-cdi-data-integration/02-how-claude-builds-mappings-headless.md)).
  Each template in `idmc/templates/mappings/` is a mapgen spec (nodes with their fields, expressions, lookups, rule specs,
  links) plus the blueprint's own keys (`task`, `status`, `notes`, `soqlFilters`). Run steps 6, 7 and 10 (`bid_dq.py build`:
  3a / 3b bind the rule specs' ids) and `crm-ids` (step 3) first, then:
  ```
  python idmc/bid_mappings.py build                                         # real ids; resolves org + connection guids read-only
  python idmc/bid_mappings.py import                                        # dry run: previews each package NEW / EXISTS
  python idmc/bid_mappings.py import --execute --expect-org <orgIdV3>        # REUSE (first import)
  python idmc/bid_mappings.py build --only 3a                                # a rebuild keeps the SAME guid (state mapping_guids)
  python idmc/bid_mappings.py import --only 3a --mode OVERWRITE --execute --expect-org <orgIdV3>
  ```
  **Expect:** each import ends SUCCESSFUL and the read-back finds the mapping by name with the guid of the build.
  **Status: ADAPTED.** The generator is PROVEN elsewhere (multi-transformation mappings on BigQuery, PostgreSQL and
  Salesforce, KB L-CDI-033 / L-CDI-204 / L-CDI-217); these six specs compile offline but have not yet been imported or run
  in this form. Snowflake and SharePoint take the generator's generic connector path; a build-time template hook adds the
  Salesforce source shape (owner / resource, SOQL filter, L-CONN-108) and the Snowflake target shape (L-CONN-093). Before
  the first real run, compare one generated adapter with an export of a designer-built mapping (`toolkit/lib/idmc_export_import.py
  export`). **Fallback** if an import or a run fails on an adapter: author that mapping in the designer from its rendered
  spec (route 4, click path below), then clone and patch headless (`idmc_export_import.py` + `idmc_package_edit.py`).
* **2a, 2b** (Structure Parser): UI once (wall below): the generator has no Structure Parser node. Build 2a, then 2b as a
  copy with the other model and filter. Their specs document the shape.

Designer click path (any spec): Data Integration > New > Mappings > Mapping > Create; name = the spec's `name`, location =
`Bid Desk/<the spec's task.folder>`. For each node in order: Source / Lookup = connection + object or query from the spec
(a Salesforce source's filter is its `soqlFilters` entry);
Expression = each field of the spec (Output, or Variable when `kind` says so); Filter / Joiner / Aggregator = the condition
or group-by of the spec; Rule Specification = the rule spec named by `asset` with the `map` of the spec; Target = connection +
existing table, operation Insert, field mapping as the spec's last link; for a full reload set the target's Advanced
**Pre SQL** runtime attribute to the spec's `writerAttrs` truncate. Save, validate.

2a in the designer: Source `Bid Desk - Snowflake` view `BID_V_DOCUMENTS`, Query Options > Filter > Advanced
`DOC_TYPE = 'Bid packet'` -> Expression `x_bytes` binary, precision 8388608, `DEC_BASE64(CONTENT_B64)` -> Structure Parser:
Input Type **Buffer**, model `Bid Desk - Bid packet model`, Incoming Fields: **exclude** `CONTENT_B64`, Field Mapping
`x_bytes` -> `Data`, Output Fields: tick **Passthrough** -> Expression `x_run` / `x_ts` / `x_ism` -> Target
`BID_BRZ_BID_PACKET`, Insert, field mapping = `state/ids.json` `claire_field_map.bid`.

Then the tasks (runtime, the two pre-processing commands, move into the folders):
```
python idmc/bid_mappings.py tasks --execute --expect-org <orgIdV3>
python idmc/bid_mappings.py list
```
**Expect:** 8 tasks `<mapping name> - task`; 1b and 5 read back their `preProcessingCmd`. **Undo:** step 19.
**Gotchas:** the CRM Files filter is a plain `ContentDocumentId IN (...)` list: `FirstPublishLocationId` is set on version 1
only (L-CONN-114), and the catalog cannot parse a sub-query filter (ContentVersion then drops out of lineage). A Snowflake
full reload needs the runtime attribute `presql`; the truncate flag is ignored (L-CONN-106). A Snowflake BINARY column cannot
be a CDI source: keep the bytes as base64 text and decode in the Expression (L-CONN-113, L-CDI-244). Keep `CONTENT_B64` out
of the parser's input group or it repeats on every parsed row. Expression OUTPUT ports cannot reference OUTPUT ports: use
VARIABLE ports (L-CDI-105). On Snowflake the source Advanced filter is sent verbatim; Preview Data ignores it (L-CDI-233).
Generator: every source and lookup declares its fields (the reader selects only those, so 1b never reads `CONTENT_B64`);
keep target fields in step with `infra/snowflake/*.sql`; Snowflake NUMBER columns are NUMERIC ports (a bigint lookup port
fails, L-CONN-095); a Salesforce datetime source field needs precision 24, scale 0 (L-CDI-245); lint's `CONN_KIND` warning
for Snowflake / SharePoint is expected (their generic connector path); packages built `--offline` carry placeholder ids
and `import` refuses them.

## 10. Data Quality rule specs + profiles — PROVEN
**Why:** the agency's own rules (two decimals, item number, unit, brand, e-mail) as rule specifications, used both in the
mappings and in Data Profiling: one definition, two uses.
```
python idmc/bid_dq.py build --execute --expect-org <orgIdV3>      # BEFORE step 9's real build: 3a / 3b bind the rule ids
python idmc/bid_dq.py rulespecs
python idmc/bid_dq.py profiles
```
**Expect:** 7 rule specs in folder 3 (each import's script read back and compared), 3 profiles with 7 + 5 + 2 rule
occurrences. **Undo:** step 19. Details: [DQ Assets](../../../knowledge/06-data-quality-profiling/01-dq-assets-rule-specs-cleanse-dictionaries-verifiers.md),
[Profiling - What Is Headless](../../../knowledge/06-data-quality-profiling/02-profiling-what-is-headless.md).
**Gotchas:** rule specs have no create verb: the script clones ONE existing single-string-input rule spec of your org
(`idmc.template_rule_spec`; make one in the UI if the org has none), one package per rule (an import is all-or-nothing);
`checksumValid` must be true or the import never starts; a failed import can leave a shell that a later REUSE picks up
(`REPO_36004`): re-import under a new name. Profiles: no client-side ids in the create body (else 500); a dot was refused in
profile names (the script replaces it).

## 11. Taskflows + first run — PROVEN
```
python idmc/bid_taskflows.py build --execute --expect-org <orgIdV3>     # add --no-sharepoint until step 5's check passes
python idmc/bid_taskflows.py show
python idmc/bid_demo.py run --execute --expect-org <orgIdV3>
python idmc/bid_demo.py verify start
```
**Expect:** both taskflows in folder 5; the run ends SUCCESS in about 4 minutes; `verify start` prints `OK ECPC-2031-07
PRICE THE BID` and `OK EUSD-31-RFQ-04 SIGN THE FORM`. **Undo:** step 19. See [Taskflows & Schedules](../../../knowledge/03-cdi-data-integration/04-taskflows-schedules.md).
**Gotchas:** 1 and 1b continue on error, so the CRM or SharePoint being down never blocks what is in Snowflake; two
taskflows sharing tasks cannot overlap (REPO_17314); 'Internal error. The DTM process terminated unexpectedly' with an
empty session log = the connection login failed, read the agent's tomcat log (L-CONN-109).

## 12. Profiling run + scorecard — PROVEN
```
python idmc/bid_dq.py run all --execute --expect-org <orgIdV3>
python idmc/bid_dq.py results
python idmc/bid_dq.py land --execute --expect-org <orgIdV3>
```
**Expect:** e.g. 'Product number on one line' below 100% on Bronze (2 lines broken by the PDF) and 100% on Silver.
**Gotchas:** run one profile at a time; count from the run-keyed metric store, never from ValueFrequencies (not run-keyed),
and accept Patterns rows only when they carry this column's key, run and profile (an unknown column id still answers 200).
See [DQ Scorecards](../../../knowledge/06-data-quality-profiling/04-dq-scorecards-warehouse-pattern-and-data-profiling-scorecards.md).

## 13. Catalog sources, scans, lineage — PROVEN (feed ADAPTED)
```
python idmc/bid_catalog.py create --execute --expect-org <orgIdV3>
python idmc/bid_catalog.py scan --execute --expect-org <orgIdV3>
python idmc/bid_catalog.py refs
python idmc/bid_catalog.py merge --execute --expect-org <orgIdV3>
python idmc/bid_catalog.py chain
python idmc/bid_catalog.py feed --execute --expect-org <orgIdV3>
```
**Expect:** three sources; `chain` walks from `BID_V_BI_DECISIONS` back through every IDMC task to Salesforce Account and
ContentVersion. **Demo start:** Catalog > search `ContentVersion` > Lineage (downstream to Gold). **Undo:** MERGE ->
`operationType=SPLIT` (registry in `state/ids.json`); a REST DELETE of a source only purges its metadata (wall below).
Details: [Catalog Sources](../../../knowledge/07-catalog-governance-cdgc/02-catalog-sources-create-scan-update-purge.md),
[Search, Lineage & Marketplace](../../../knowledge/07-catalog-governance-cdgc/04-search-lineage-marketplace.md),
[CDGC Gaps & Gotchas](../../../knowledge/07-catalog-governance-cdgc/05-cdgc-gaps-gotchas.md).
**Gotchas:** sources are cloned from a same-type source of your org (`idmc.catalog_templates`; create one per type in
Metadata Command Center if none exists); scans bill IPUs and the Snowflake profiling counts against the cost guard; the
catalog reads each task's RUN metadata, so lineage appears after a pipeline run; auto-accept never resolves IDMC connection
references (that is what `merge` does); only distance-1 hops come back per asset, so `chain` walks hop by hop; CLAIRE steps
show at table level only; SharePoint shows as a stub unless you catalog the site too.

## 14. Glossary + links — PROVEN
```
python idmc/bid_glossary.py create --execute --expect-org <orgIdV3>
python idmc/bid_glossary.py publish --execute --expect-org <orgIdV3>
python idmc/bid_glossary.py verify
python idmc/bid_glossary.py feed --execute --expect-org <orgIdV3>
```
**Expect:** domain `Bid Desk`, 13 terms Published, 17 links (one Content Publish Task). **Undo:** `bid_glossary.py undo
--execute ...`. See [Glossary, Links & Classification](../../../knowledge/07-catalog-governance-cdgc/03-glossary-links-classification.md).

## 15. Tableau workbook — ADAPTED
```
python dashboards/bid_tableau.py build
python dashboards/bid_tableau.py publish --execute
```
**Expect:** one workbook, six tabs (Bid Desk, Data Quality, Lineage, Glossary and Governance, Mapping, Parsing), each with rows.
**Verify:** `python verify/bid_verify.py data` (every BI view has rows). **Undo:** delete the workbook in Tableau.
**Note:** live Snowflake connection with the read-only user embedded; the source demo used Hyper extracts. If the server
rejects the generated `.twb`, open it in Tableau Desktop, save, publish.

## 16. The demo loop — PROVEN
```
python idmc/bid_demo.py whatif --execute --expect-org <orgIdV3>     # completed copies as new CRM versions, then Run
python idmc/bid_demo.py verify whatif                              # FIX 2 ITEMS / SUBMIT THE FORM
python idmc/bid_demo.py publish --execute --expect-org <orgIdV3>   # lineage + glossary feeds, then Tableau
python idmc/bid_demo.py reset --execute --expect-org <orgIdV3>     # originals back as new versions (nothing deleted), then the pipeline
python idmc/bid_demo.py verify start
python idmc/bid_demo.py status
```
Run of show (20 min): Tableau Bid Desk tab -> Salesforce Account > Files -> IDMC Monitor: Run -> mapping 1 (only new
versions) -> model + mapping 2a (PDF in, rows out) -> mapping 3a + Data Quality tab -> decisions -> what-if -> Catalog lineage
from ContentVersion and the glossary -> reset after the demo.

## 17. Nightly schedule (prepared, not attached) — PROVEN
```
python idmc/bid_taskflows.py schedule --execute --expect-org <orgIdV3>            # creates it unbound
python idmc/bid_taskflows.py schedule --attach --execute --expect-org <orgIdV3>   # ONLY on the owner's OK: it runs every day
python idmc/bid_taskflows.py detach --execute --expect-org <orgIdV3>              # undo
```
**Gotcha:** v2 `startTime` is POD-LOCAL time labelled `Z`; `startTimeUTC` is true UTC. The core tool
`toolkit/lib/idmc_taskflow_schedule.py schedule-create ... --pod-offset-hours` handles the offset if the pod refuses the body.

## 18. Optional: one user sees only this project — PROVEN
Set `access.enabled: true` and the names in `config.json`, then:
```
python idmc/bid_access.py plan                 # writes state/access_backup.json, prints every change
python idmc/bid_access.py apply --execute --expect-org <orgIdV3>
python idmc/bid_access.py verify
python idmc/bid_access.py undo --execute --expect-org <orgIdV3>
```
**Gotchas:** the role JSON property is `privileges` (`privilegeIds` = 400 V3API_007); `addRoles` takes role NAMES; IDMC
refuses to remove a user's last role (add first); list the CAI anonymous user too or CAI processes cannot run restricted DI
tasks; the system role Admin sees every asset whatever its object permissions; objects created later stay visible until you
run `apply` again.

## 19. Teardown — PROVEN core tools, ADAPTED order script
```
python teardown/bid_teardown.py plan
python teardown/bid_teardown.py export
python teardown/bid_teardown.py idmc
```
It prints the guarded core commands in order (export first, schedule detach, access undo, glossary undo, lineage SPLIT,
catalog, tasks/models/rule specs/folders/project leaf-first, connections, Snowflake, CRM, SharePoint, Tableau) and never
deletes by itself.

---

## Gotchas (every hard-won fix, one line each)
- Snowflake 090073: the resource monitor stopped the warehouse; raise the quota (L-ENV-096).
- `ContentVersion.FirstPublishLocationId` is set on version 1 only; filter Files by `ContentDocumentId` (L-CONN-114).
- The catalog cannot parse a sub-query CRM filter: use a plain id list or ContentVersion vanishes from lineage.
- CDI rejects a ContentVersion new-version insert (`REQUIRED_FIELD_MISSING [Title]` with Title sent); REST accepts it: the
  reset writes over REST from a pre-processing command (L-CONN-115).
- SharePoint Online: mint the refresh token for the SharePoint audience, not Graph (L-CONN-100); a token carries only the
  consented scopes, so mint it AFTER admin consent (L-CONN-111); the folder must exist before an INSERT; the bytes come from
  `Attachment_File_Path` on the agent (L-CONN-107).
- A Snowflake BINARY column cannot be a CDI source ('Unknown native type'): base64 text + `DEC_BASE64` (L-CONN-113, L-CDI-244).
- Structure Discovery: session as cookie AND header; `X-CSRF-TOKEN` on every POST; don't follow the unauthenticated 302 (L-CDI-224).
- CLAIRE types values (dates, numbers, phones): tune them to text so Bronze keeps what the PDF says; export every text block.
- A Structure Parser keeps a copy of its model: Synchronize after a model update; changing its model drops links and Passthrough (L-CDI-232).
- Snowflake writer full reload = runtime attribute `presql` (L-CONN-106).
- Generated mappings (toolkit/mapgen): Salesforce sources need owner / resource + the SOQL filter in readOptions (L-CONN-108),
  Snowflake targets objectType 'table' + tableType = TABLE (L-CONN-093): `bid_mappings.py build` adds both through a
  template hook; rebuild under the same guid and import OVERWRITE to change a mapping (a task POST changes nothing).
- Rule specs: clone a template through a package, one package per rule, check `checksumValid` and read the script back.
- Profiles: no client-side ids; one at a time; count from run-keyed metrics only.
- Catalog sources: multipart with one part `dataSource`, `custom` + `endOfLife` set; never an empty `capabilityNames`.
- Lineage: MERGE the IDMC connection references onto the cataloged database / org; undo = SPLIT.
- A Salesforce password login depends on the agent's egress IP (L-CONN-110).
- New v2 objects (tasks, taskflows) are born in Default: move them with FRS MoveEntities.
- Every run is one IDMC job and wakes the warehouse: nothing in this blueprint runs on its own.

## UI-only walls (no API did it; click path given)
| Wall | Click path |
|---|---|
| Entra app registration + **admin consent** for the SharePoint write scope | Entra admin center > App registrations > your app > API permissions > Add (SharePoint, Delegated) > Grant admin consent |
| Salesforce Connected App with client credentials | Setup > App Manager > New Connected App > Enable OAuth > Enable Client Credentials Flow > run-as user |
| **Structure Parser mapping 2a** (then 2b) | Data Integration > New > Mappings > Mapping (step 9 click path) |
| Mappings 1, 1b, 3a, 3b, 4, 5: **not a wall** (`bid_mappings.py build` + `import`, toolkit/mapgen); the designer is the fallback only if a generated adapter fails on import or run | the same designer path, from each rendered spec |
| A template rule spec (if the org has none) | Data Quality > New > Rule Specification (one string input) |
| A template catalog source per type (if the org has none) | Metadata Command Center > New > Catalog Source > Snowflake / Salesforce / Informatica Intelligent Cloud Services |
| Removing a catalog source definition | Metadata Command Center > Catalog Sources > the source > Delete (REST DELETE only purges metadata) |
| Snowflake programmatic access token; Tableau PAT | Snowsight > your user > Programmatic access tokens; Tableau > My Account Settings > Personal Access Tokens |
| Secure Agent install | see [Secure Agent - Install, Run & Tune](../../../knowledge/02-secure-agent-connections/01-secure-agent-install-run-tune.md) |
