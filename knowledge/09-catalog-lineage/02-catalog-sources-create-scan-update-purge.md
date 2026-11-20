# Catalog Sources: Create, Scan, Update, Purge

**Answers:** How do I create, clone, update, scan, poll, rename and purge a catalog source headless? Which option keys
does a type accept? Why did a scan end PARTIAL_COMPLETED, 406 or FAILED? How do I turn on catalog Data Quality without
side effects?

**Read when:** registering or cloning a catalog source; tuning filters or capabilities; a scan fails, hangs or skips
objects; moving a source to another org or retiring it.

**Key rules:**
- Create with a multipart `POST.../datasources` (one part `dataSource`, `custom` + `endOfLife` set, no trailing slash) by
  cloning a working source of the same type and remapping every id (L-CDGC-014, L-CDGC-015).
- Build bodies from the type's option schema (`GET.../type/<Type>/capability/<Capability>/configuration`), never from
  guessed keys (L-CDGC-016).
- Update with a multipart `PUT` that repeats the path `id` inside the JSON part, or it answers 400 (L-CDGC-163).
- Scan with a non-empty `capabilityNames` of display names, one source at a time, with the Metadata services selected
  only for the window; "done" means every task COMPLETED and the result visible in search (L-CDGC-034, L-CDGC-035,
  L-CDGC-039, L-CDGC-045).
- Catalog Data Quality needs the runtime environment in the typeCapabilities Scope groups; a clone of a DQ-enabled
  source also brings auto-generated `DQ_Capability_Schedule_*` schedules unless its automation switches are off
  (L-CDGC-143, L-CDGC-152).
- Set Metadata Change Option = Delete before rescanning a changed source (L-CDGC-028), but Retain (or a new source) when
  you narrow its filter: Delete then purges every asset of the dropped scope (L-CDGC-223).
- A second agent OS user on the same host needs `/tmp/poifiles` at 1777, or Metadata Extraction ends PARTIAL_COMPLETED on
  every run (L-CDGC-150).
- A PARTIAL_COMPLETED can carry no message in the job tree: read the agent's scanner Sync log before treating it as a
  failure (a Snowflake role that cannot read tags still extracted every table and view, L-CDGC-168).
- A REST `DELETE` purges metadata only; delete the definition in MCC (L-CDGC-047). Cancel a scan with `POST .../ccgf-orchestration-management-api-server/api/v1/jobs/<jobId>/operations/cancel`, from a script or the console, and poll for CANCELLED (L-CDGC-221, L-CDGC-225).

**Related:** [01 CDGC APIs & Auth](01-cdgc-apis-auth.md) ·
[04 Search, Lineage & Marketplace](04-search-lineage-marketplace.md) ·
[05 CDGC Gaps & Gotchas](05-cdgc-gaps-gotchas.md) ·
[Profiling - What Is Headless](../08-data-quality/02-profiling-what-is-headless.md) · [Lessons: CDGC](lessons.md)

**Last verified:** 2026-11-20

> **Summary.** A catalog source is created with a multipart `POST` to
> `cdgc-api.<domain>/ccgf-catalog-source-management/api/v1/datasources`, updated with a multipart `PUT`, scanned with
> `POST idmc-api.<domain>/data360/executable/v1/catalogsource/<id>` and polled on `data360/observable/v1/jobs/<jobId>`.
> Scans run on the Secure Agent's Metadata services. A stuck scan is cancelled over REST (section 7.6). Secure Agent service selection and host
> sizing: [Secure Agent & Connections](../02-secure-agent).

All calls carry the three identity headers from [01 CDGC APIs & Auth](01-cdgc-apis-auth.md) section 2.4.
`<csId>` = catalog source id (a UUID); `<reId>` = runtime environment id; `<connId>` = v2 connection id.

---

## 1. The lifecycle at a glance

1. **Prepare the agent and the connection**: Metadata services selected on the runtime environment, a native connector
   connection that tests green, scanner drivers in place (section 2).
2. **List the types** the org can create (`datasourceTypes`) and **GET a working source of the same type** as a template.
3. **Create** the source (multipart `POST`, `custom` + `endOfLife` set, every id remapped), then **read it back**.
4. **Run a scan** with the capabilities you need and **poll** the job to a terminal state.
5. **Verify** per capability (not just "the job finished"): search counts, sampled columns, Sync logs.
6. **Tune** with a multipart `PUT`: include filters, profiling excludes, Metadata Change Option, lineage filters.
7. **Rescan** after source changes with the Delete change option.
8. **Retire**: harvest GUID-keyed links, `DELETE` (purge job), then delete the definition in MCC.

---

## 2. Prerequisites

| Gate | What must be true | How to check | Lesson |
|---|---|---|---|
| Services | The RE has `Data Governance and Catalog`; engines `Metadata_Foundation_Agent` and `Metadata_Platform_Service` (plus DIS, Connector_Service) RUNNING | `GET.../runtime/api/v2/runtimeEnvironment/<reId>/selections/ui`; `GET /api/v2/agent/details/<agentId>` | L-CDGC-007, L-CDGC-045 |
| Service window | Metadata services are heavy (several GB of RAM, lots of CPU): select them just before scanning, deselect after | `PUT.../selections/ui` (each PUT can roll engines, ~5 min of queueing) | L-CDGC-045 |
| Connection | Native connector connection that tests green; for PostgreSQL the native connector, not JDBC | `GET /api/v2/connection/test/<connId>` | L-CDGC-023 |
| Scanner drivers | Third-party JDBC jars also under the scanner folders (`Metadata_Foundation_Agent/.../data/browse/drivers/`, `Metadata_Platform_Service/.../lib/drivers/`) | scan log "driver" errors | L-CDGC-024 |
| Profiling engine | Data Profiling launches `pmdtm` natively on the agent; its libraries must load (e.g. `libidn.so.11` on Debian 12) | pmdtm exit code 127 / 134 / 137 | L-CDGC-044 |
| SaaS sources | Salesforce: a native Salesforce connector connection, an integration user with ViewSetup + ViewRoles, and the Metadata services selected before the scan | scan error text | L-CDGC-142, L-CDGC-032 |
| Shared host | A second Secure Agent running as another OS user on the same host can write the scanner's temp report directory | `ls -ld /tmp/poifiles` is `drwxrwxrwt`; write-test as both agent users | L-CDGC-150 |
| IICS source | A dedicated service login it can store (not a personal or borrowed one) | rotation checklist | L-CDGC-030 |
| Roles | Admin, Designer, Governance Administrator (+ CLAIRE GPT User for CLAIRE work) | identity Login roles | L-CDGC-008 |

The service selection route and host sizing are covered in [Secure Agent & Connections](../02-secure-agent).

---

## 3. Create a catalog source

### 3.1 The route (L-CDGC-014)

```
POST https://cdgc-api.<domain>.informaticacloud.com/ccgf-catalog-source-management/api/v1/datasources   (no trailing slash)
Authorization: Bearer <jwt>
IDS-SESSION-ID: <sessionId>
X-INFA-ORG-ID: <orgIdV3>
Content-Type: multipart/form-data; boundary=<b>

--<b>
Content-Disposition: form-data; name="dataSource"
Content-Type: application/json

{...definition... }
--<b>--

-> 200/201 with the created source, including its new "id"
```

| Response | Meaning | Fix |
|---|---|---|
| 415 | the body was plain JSON | send multipart with the one part `dataSource` |
| 500 `Custom flag cannot be null` | `custom` / `endOfLife` missing | add `"custom": false, "endOfLife": false` |
| 404 | trailing slash on `.../datasources/` | drop the slash |
| 500 `Error while validating Runtime Environment detail [<reId>] under global config option [Execution]` | `IDS-SESSION-ID` missing, or the RE is not ready | re-send with all three headers, then check the RE (L-CDGC-022) |
| success | source registered | `GET.../datasources/<id>` and compare to what you sent |

### 3.2 The body: clone a working source (L-CDGC-015)

1. `GET.../ccgf-catalog-source-management/api/v1/datasourceTypes` and confirm the type exists (L-CDGC-016); read the
   option schema of each capability you will set (section 4.1).
2. `GET.../datasources/<id>` of a working source of the same type (in this org or another one).
3. Keep `name, description, type, endOfLife, custom, overrides, typeOptions, capabilities, typeCapabilities,
   globalConfigOptions, customAttributes`.
4. Drop `id, createdBy, lastModifiedBy, createdTime, lastModifiedTime, seedVersion, clonedCatalogSourceId, modelVersion,
   isDeleted`.
5. Remap every id: `typeOptions` > `ConnectionId` (the v2 connection id), `globalConfigOptions` > Execution > Runtime
   Settings > `Runtime Environment` (`<reId>`), any runtime environment inside a capability's options, and any catalog id.
   For an IICS source set `IICS URL`, `IICS User`, `IICS Password` from a secrets file at run time.
6. String-scan the JSON and **assert that no id of the old org or old connection is left** (search for the old org's id
   prefix). A clone helper that captured but never swapped its connection argument created a source still bound to the
   old warehouse.
   If the template has Data Quality enabled, switch its automation off in the clone unless you want IDMC-side DQ
   schedules (section 8).
7. POST it; store the returned id in your own name-to-id map (the list call can come back empty, L-CDGC-018).

### 3.3 Anatomy of a definition (L-CDGC-021)

Copy group names from a GET of the same type; the shape below is what GET returned for four types.

```json
{
  "name": "<source name>",
  "description": "<text>",
  "type": "PostgreSQL",
  "custom": false,
  "endOfLife": false,
  "typeOptions": {"configurationProperties": [
    {"optionGroupName": "<Type> OptionGroup", "configOptions": [
      {"key": "ConnectionId", "values": ["<connId>"], "additionalMetadata": null}]}]},
  "capabilities": [
    {"capabilityName": "Metadata Extraction", "configurationProperties": [
      {"optionGroupName": "Metadata Extraction OptionGroup", "configOptions": [
        {"key": "Metadata Change Option", "values": ["Delete"], "additionalMetadata": null},
        {"key": "Type of scan", "values": ["Full"], "additionalMetadata": null}]}]},
    {"capabilityName": "Data Profiling", "configurationProperties": []},
    {"capabilityName": "Data Classification", "configurationProperties": []}],
  "typeCapabilities": [
    {"capabilityName": "Metadata Extraction", "configurationProperties": [
      {"optionGroupName": "Metadata Filter Config", "configOptions": [
        {"key": "Filter Pivot", "values": ["Include Metadata"], "additionalMetadata": null},
        {"key": "Filter Type", "values": ["<filter type, as in a GET of this type>"], "additionalMetadata": null},
        {"key": "Filter Value", "values": ["<schema>.*"], "additionalMetadata": null},
        {"key": "Filter Conditions", "values": ["All Types"], "additionalMetadata": null}]}]}],
  "globalConfigOptions": [
    {"globalConfigurationName": "Execution", "configurationProperties": [
      {"optionGroupName": "Runtime Settings", "configOptions": [
        {"key": "Runtime Environment", "values": ["<reId>"], "additionalMetadata": null}]},
      {"optionGroupName": "Metadata Sync Settings", "configOptions": [
        {"key": "Mode of Execution", "values": ["Full Sync"], "additionalMetadata": null}]}]},
    {"globalConfigurationName": "Configuration", "configurationProperties": [
      {"optionGroupName": "Metadata and Data Filters", "configOptions": [
        {"key": "Filter Options", "values": ["Filter Conditions"], "additionalMetadata": null}]}]}],
  "overrides": [],
  "customAttributes": null
}
```

- Observed `typeOptions` groups: "Salesforce OptionGroup" (`ConnectionId`), "IICS OptionGroup" (`IICS URL`, `IICS User`,
  `IICS Password`). A GET returns the IICS password option as a long opaque string (about 300 characters, probably
  encrypted; not verified): treat saved source JSON as a secret-bearing file (L-CDGC-030).
- `capabilities[]` lists what a scan may run; `typeCapabilities[]` holds that capability's filters.

### 3.4 Multipart helper (extends the helper in doc 01)

```python
import json, uuid, urllib.request, urllib.error
DS = f"{CDGC}/ccgf-catalog-source-management/api/v1/datasources"
READ_ONLY = ("id", "createdBy", "lastModifiedBy", "createdTime", "lastModifiedTime", "seedVersion",
             "clonedCatalogSourceId", "modelVersion", "isDeleted")

def send_datasource(method, url, definition):
    b = uuid.uuid4().hex
    keep = {k: v for k, v in definition.items() if k not in READ_ONLY}
    if method == "PUT":
        keep["id"] = url.rstrip("/").rsplit("/", 1)[-1]   # a PUT repeats the path id in the JSON part (L-CDGC-163)
    part = json.dumps(keep)
    body = (f"--{b}\r\nContent-Disposition: form-data; name=\"dataSource\"\r\n"
            f"Content-Type: application/json\r\n\r\n{part}\r\n--{b}--\r\n").encode()
    h = headers; h["Content-Type"] = f"multipart/form-data; boundary={b}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=body, method=method, headers=h), timeout=90) as r:
            t = r.read()
            return r.status, (json.loads(t) if t else None)
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:800].decode(errors="replace")

# create: send_datasource("POST", DS, clone)                 # no trailing slash
# update: send_datasource("PUT", f"{DS}/{cs_id}", edited)     # retry with "PATCH" if PUT is refused; read it back
```

### 3.5 List and read (L-CDGC-017)

- `GET.../ccgf-catalog-source-management/api/v1/datasources?offset=0&limit=100` returns `datasources[]`.
- `GET.../datasources/<id>` returns the definition; save it before every change (it is the undo file).
- `GET https://idmc-api.<domain>.informaticacloud.com/data360/catalog-source-management/v1/catalogsources` also lists
  sources with `totalElements` on the orgs tested, but this prefix has flipped between an empty 404 and 200 on the same
  org: use it only as a secondary read (L-CDGC-019).
- The list has come back empty while MCC showed the sources (L-CDGC-018): keep your own name-to-id map.

---

## 4. Types and per-type notes

| `type` | Binding | Typical capabilities | Notes |
|---|---|---|---|
| `PostgreSQL` | `ConnectionId` = a native PostgreSQL connection (`com.informatica.adapter.postgres`) | Metadata Extraction, Data Profiling, Data Classification (+ Lineage Discovery, Data Quality, Data Observability) | Native, not JDBC: JDBC scans miss sequences, constraints and FKs (L-CDGC-023). Filters are `schema.*` (L-CDGC-026). COMPLETED WITH ERRORS from skipped C-language functions is benign (L-CDGC-042). Exclude tables with pgvector columns from profiling (L-CDGC-043); json, enum and array columns are skipped by profiling (L-CDGC-044). |
| `Google BigQuery` | `ConnectionId` = a BigQuery V2 connection | Metadata Extraction, Data Profiling, Data Classification (+ Lineage Discovery, Data Quality) | Include-filter to the live datasets; stale copies elsewhere confuse CLAIRE (L-CDGC-027). An include entry naming a dataset that does not exist logs "Could not find matching schemas": remove it. Views whose SQL the analyzer cannot parse get no lineage ([04](04-search-lineage-marketplace.md) section 8) (L-CDGC-151). Profiling a 26-dataset project took about 2 h (L-CDGC-033). A column named `rows` and transient 503s end profiling PARTIAL_COMPLETED (L-CDGC-043). |
| `IICS` | `IICS URL`, `IICS User`, `IICS Password` | Metadata Extraction + Lineage Discovery | Include filter `Data Integration` / `<project>` / `All Types`; rescan after new task types (L-CDGC-029). Breaks on password rotation (L-CDGC-030). One rescan failed at Catalog Source Extraction after flat-file tasks were added (open, L-CDGC-046). |
| `Salesforce` | `ConnectionId` = the v2 id of a native `Salesforce` connection | Metadata Extraction | Catalogs every standard and custom (`*__c`) object with its fields. A "no permissions to access connections which are selected" refusal is not a connection-type wall: select the Metadata services and retry before building a new connection (L-CDGC-142). A federated id in `ConnectionId` is refused. Holds the whole org schema (L-CDGC-032). |
| `Microsoft Fabric Data Warehouse` | Fabric connection (`com.informatica.adapter.fabricdw`) | Metadata Extraction | One of three native Fabric types; no extra entitlement. Its `typeCapabilities` lacked Data Quality in one org (L-CDGC-025). |
| SharePoint Online (take the type name from `datasourceTypes`) | connection URL = the tenant root `https://<tenant>.sharepoint.com`; `Subsite_URL` = the full site URL `https://<tenant>.sharepoint.com/sites/<site>` | Metadata Extraction | The scanner asks Azure AD for a token whose resource is the connection URL: with the site URL there the scan fails with AADSTS500011 (resource principal not found); with the tenant root and a relative subsite (`sites/<site>`) it fails with 'no protocol: sites/<site>/_api/web'. A create that omits any Scanner Configuration option answers 500: send all of them (Partition Detection false). The scan catalogs the site, its libraries, folders and documents (L-CDGC-162). |
| `Databricks Delta Lake` | a Databricks Delta connection | none: **end-of-life** | A create answers 500 'Informatica dropped support for DataSourceType Databricks Delta Lake' (L-CDGC-206, which supersedes L-CDGC-188). Use `Databricks Notebooks` instead. |
| `Databricks Notebooks` (the unified Databricks source) | `ConnectionId` = a native Databricks Delta connection | Metadata Extraction, Lineage Discovery (+ Data Profiling, Data Classification, Data Quality) | Catalogs Unity Catalog tables, views, columns, volumes, jobs, pipelines, notebooks; derives view-on-table lineage from view SQL. Set `databricks.lineageFromUnity` and grant the scan user system.access lineage, or the job ends PARTIAL_COMPLETED with 403s on the lineage API. Metric views land as Tables with no source edge (L-CDGC-206). |
| File System (take the type name from `datasourceTypes`) | the directory a mapping's flat-file connection reads or writes, on the same Secure Agent | Metadata Extraction | Its `FileServer` root is the target a mapping's flat-file reference is MERGE-assigned to for lineage ([04](04-search-lineage-marketplace.md) section 9.1) (L-CDGC-160). |
| `Tableau` (take the type name from `datasourceTypes`) | the Tableau server, through a Secure Agent that can reach it (a temporary tunnel worked, L-CDGC-199) | Metadata Extraction (+ lineage stitching to warehouse sources) | Scope the project filter to workbooks whose data sources read live warehouses: a workbook reading a warehouse that is gone hangs the scan in Test Connection with no timeout, because the stitching check opens that connection (L-CDGC-223). Then MERGE its warehouse reference (L-CDGC-201). |
| Azure Blob Storage (take the type name from `datasourceTypes`) | a Microsoft Azure Blob Storage V3 connection | Metadata Extraction | Scan on a Secure Agent: the source refuses the Hosted Agent (DISPATCH_REJECTED) although the connection tests there (L-CONN-129). Catalogs StorageAccount > Container > files (class `com.infa.odin.models.file.flat.FlatFile`); stitch a mapping that reads an agent-folder copy onto it by path ([04](04-search-lineage-marketplace.md) section 9.1; L-CDGC-227). One container scanned in about 4-5 min (L-CDGC-230). |
| `JDBC` (generic) | a JDBC V2 connection | Metadata Extraction, Data Profiling, Data Quality, Data Classification, Relationship Discovery, Glossary Association | **No Lineage Discovery** (its capability configuration answers 404): lineage for a database reached only through JDBC comes from the IICS source plus a MERGE, and curated edges (L-CDGC-234). Use a native type where one exists: JDBC scans miss sequences, constraints and FKs on PostgreSQL (L-CDGC-023). |

### 4.1 Read a type's option schema (L-CDGC-016)

```
GET {CDGC}/ccgf-catalog-source-management/api/v1/datasourceTypes?offset=0&limit=200
-> 200 {"datasourceTypes": [{..., "iicsConnectionTypes": [...], "optionGroups": [...], "documentationInfo": {...}}], "metadata": {...}}

GET {CDGC}/ccgf-catalog-source-management/api/v1/type/<TypeName>/capability/<CapabilityName, URL-encoded>/configuration
    e.g..../type/PostgreSQL/capability/Data%20Quality/configuration
-> 200 {"optionGroups": [{"options": [{"name", "dataType", "required", "defaultValue", "staticValues", "conditions"}]}]}
```

- Both answer with the three identity headers. A type entry also carries facts such as supported source versions
  (PostgreSQL: 10.x through 14.x) and authentication modes (Database, Kerberos).
- The configuration read describes the **typeCapabilities** layer (filters and Scope groups), not the `capabilities[]`
  run switches (L-CDGC-143).
- Data Quality's `Data Quality Scope` group: `Sampling Type` (All Rows, Limit N Rows as the default, Custom Query),
  `No of rows to limit` (default 1000, shown for Limit N Rows), `Sampling Query` (shown for Custom Query) and
  `Runtime Environment`.
- Data Classification returns no option groups at the type level, so there is no auto-accept threshold to set there
  (L-CDGC-061 stands).
- Build every new body from these reads plus a GET of a working source; never guess option keys.
- A 404 'capability configuration does not exist' means the type does not offer that capability, because an invented
  capability name answers 400 'invalid type or capability' instead: the generic `JDBC` type answered 200 for six
  capabilities and 404 for Lineage Discovery. Read the type's capability configurations before promising lineage for
  any source type (L-CDGC-234, 2026-11-01).

---

## 5. Capabilities: names and what they do

Use the **display names** in `capabilityNames` and in definitions (L-CDGC-035). Enum-style names such as
`CATALOG_EXTRACT` (an older reference example) are not what proven runs used.

| Display name | Produces | Runs in | Notes |
|---|---|---|---|
| Metadata Extraction | Structure: database, schema, table, view, column, keys, procedures | Java scanner on the agent (its Sync log is under `Metadata_Foundation_Agent`) | Change option Retain/Delete; include filters; alone it did not catalog a view outside the include scope (L-CDGC-087) |
| Lineage Discovery | Data-flow lineage from view SQL and mapping definitions; connection-assignment recommendations | scanner and cloud services | Required for IICS lineage; stitch the references it leaves unresolved with a `connectionAssignment` MERGE ([04](04-search-lineage-marketplace.md) section 9.1) (L-CDGC-029, L-CDGC-159) |
| Data Profiling | Column statistics | native `pmdtm` on the agent | The only capability that needs the native DTM (L-CDGC-044) |
| Data Classification | CLAIRE data-element classifications | scanner and cloud services | Auto-accept threshold is the bulk lever (L-CDGC-061) |
| Data Quality | Rule occurrences scored (Rule Generation, Rule Profiling, Batch Profiling, Score Propagation) | the DQ engine | Runs alone (`["Data Quality"]`, about 15 min for a warehouse source) once both Scope groups carry a runtime environment; without it Rule Profiling FAILS in 0 s with no error text. A 406 for DQ alone was seen before that setting existed (L-CDGC-143, L-CDGC-036). Afterwards each RuleInstance carries its own `value`, `totalCount` and `exception`, whether the occurrence was made in the UI or over REST (L-CDGC-166, L-CDGC-161) |
| Data Observability | Observability metrics | depends on profiling output | Skipped when profiling fails (L-CDGC-036) |
| Relationship Discovery (UI label) | Similar columns, join keys | - | Not lineage; containment threshold 0.4 or more (L-CDGC-087) |
| Glossary Associations (UI label) | Automatic term-to-column links above a confidence threshold | - | API name not captured |

Job hierarchies also show internal tasks such as "Auto Classification" and "Bulk Ingestion". One source can run all its
capabilities in one scan (L-CDGC-036).

---

## 6. Filters and options (edited by multipart PUT)

| Where | `optionGroupName` | Keys and example values | Use | Lesson |
|---|---|---|---|---|
| `typeCapabilities` > Metadata Extraction | `Metadata Filter Config` (one group per pattern) | `Filter Pivot` ["Include Metadata"], `Filter Type` (["Data Integration"] for IICS; the dataset/schema type for databases), `Filter Value` ["<pattern>"], `Filter Conditions` ["All Types"] | Scope what is cataloged | L-CDGC-027 |
| `capabilities` > Metadata Extraction | `Metadata Extraction OptionGroup` | `Metadata Change Option` ["Retain"] or ["Delete"]; `Type of scan` ["Full"] | Delete drops objects gone from the source | L-CDGC-028 |
| `typeCapabilities` > Data Profiling | `Profiling Filter Config` | include: `Filter Pivot` ["Include Metadata"], `Filter Type` ["Tables"], `Filter Value` ["<schema>.*"]; exclude: the same group with an exclude pivot and `schema.table` | Skip tables that break profiling | L-CDGC-043 |
| Scope group of Data Profiling (in `typeCapabilities` per L-CDGC-143; copy the layer from a GET of your source) | `Data Profiling Scope` | `Profiling Run Scope` ["Full"], `Sampling Type` ["Limit N Rows"], `No of rows to limit` ["1000"], `Percentage of data to select` ["10"], `Runtime Environment` ["<reId>"], `Text Qualifier` ["Double Quote"] | Sampling and runtime for profiling | L-CDGC-021, L-CDGC-143 |
| `typeCapabilities` > Data Quality | `Data Quality Scope` | `Sampling Type` (All Rows / Limit N Rows / Custom Query), `No of rows to limit` ["1000"], `Sampling Query`, `Runtime Environment` ["<reId>"] | Without the runtime environment, Rule Profiling fails in 0 s | L-CDGC-143, L-CDGC-016 |
| `capabilities` > Data Quality | run switches | `Run Rule Occurrence Frequency`, `Data Quality Automation`, `Data Quality Automation Scope` (e.g. "Apply on all Data Elements"), `Data Quality Run Scope`, `Data Quality Remediation`, `Create Data Quality Failure Ticket`, `Cache Result` (the PUT validator names the mandatory ones) | `true` on the first two creates IDMC-side schedules (section 8) | L-CDGC-143, L-CDGC-152 |
| `typeCapabilities` > Lineage Discovery | `Lineage Discovery Filter Config` | `Filter Pivot` ["Include"], `Filter Type` ["Catalog Source Name"], `Filter Value` ["<source name>",...] | Limit which sources an IICS source stitches to (effect not recorded) | L-CDGC-141, L-CDGC-159 |
| `globalConfigOptions` > Execution | `Runtime Settings`, `Metadata Sync Settings` | `Runtime Environment` ["<reId>"], `Mode of Execution` ["Full Sync"] | Where the scan runs. A maintained public script records that `Runtime Environment` has been mandatory since March 2026 (empty = 500; `["MultiTenantServerless"]` for a custom source) and that the `Execution Mode` capability option and the `Metadata Schedule Settings` block were dropped from the payload: copy a fresh GET of your type rather than an old body | L-CDGC-021, L-CDGC-270 |

The exclude pivot is `Filter Pivot` ["Exclude Metadata"] with `Filter Type` ["Tables"] and `Filter Value`
["<schema>.<table>"], next to the `Include Metadata` groups (L-CDGC-172). A PostgreSQL table with an array column is
never profiled, so exclude it or profile a copy that casts the arrays to text (L-CDGC-171).

---

## 7. Run and poll a scan

### 7.1 Run (L-CDGC-034)

```
POST https://idmc-api.<domain>.informaticacloud.com/data360/executable/v1/catalogsource/<csId>
{"capabilityNames": ["Metadata Extraction", "Data Profiling", "Data Classification"]}

-> 201 (200 also seen) {"jobId": "<jobId>", "trackingURI": "..."}
```

The ids this route expects are listed by `GET .../data360/executable/v1/catalogsources` (`{"catalogSources":[...]}`;
L-CDGC-245, code read). Custom lineage can also come from a Custom catalog source: zip a `links.csv` (Source, Target, Association), stage it on
`ccgf-metadata-staging`, create the source with `custom` true, then run it (L-CDGC-269, code read, not probed here).

| Response | Meaning |
|---|---|
| 201/200 + `jobId` | accepted (not done) |
| 406 `Job is in progress` | a job of this source is active or stuck (positive evidence the route works) |
| 500 `no capability is being chosen` | empty `capabilityNames` |
| 400 `Failed to read request` | wrong body shape |
| 500 ccgf-auth-pep `Login sessionID is missing` (or 406) | a header is missing |
| 405 | GET or DELETE on this path |

- The same body also worked on `/data360/catalog-source-management/v1/catalogsources/<csId>/sync` and on the `cdgc-api`
  host.
- List only capabilities configured on the source. Every scan is IPU-metered (L-CDGC-103).
- A failed start with no active job is often transient: wait 60-90 s and retry once (L-CDGC-038).

### 7.2 Poll (L-CDGC-037)

- One job: `GET.../data360/observable/v1/jobs/<jobId>?expandChildren=TASK-HIERARCHY` returns `status` and `tasks[]`
  (`name`, `status` per capability).
- List: `GET.../data360/observable/api/v1/jobs?limit=N` (the `/api/` infix is required on the list) with
  `metadata.totalElements`.
- Second list, with the ids the cancel route takes: `GET https://cdgc-api.<domain>.informaticacloud.com/ccgf-orchestration-management-api-server/api/v1/jobs?metadataOnly=false&offset=<n>&limit=60`.
  It is ordered oldest first, so start at total-60 (L-CDGC-223).

| Status | Class | Meaning |
|---|---|---|
| CREATED, QUEUED, SUBMITTED, STARTING, RUNNING | running | keep polling (20-40 s) |
| COMPLETED | terminal | every task finished |
| PARTIAL_COMPLETED | terminal | published, some assets skipped (UI "Completed with Errors"): read the task log. The job tree can carry no message at all (L-CDGC-168, L-CDGC-170): read the scanner's Sync log on the agent (7.5) before calling it a failure |
| FAILED | terminal | read the failing task; retry once after 60 s if it was a start or transient error |
| CANCELLED, ABORTED | terminal | cancelled in MCC or aborted |

### 7.3 One source at a time (L-CDGC-045)

```python
TERMINAL = {"COMPLETED", "PARTIAL_COMPLETED", "FAILED", "CANCELLED", "ABORTED"}
def scan(cs_id, caps):
    for attempt in (1, 2):
        c, r = call("POST", f"{API}/data360/executable/v1/catalogsource/{cs_id}", {"capabilityNames": caps})
        if c in (200, 201):
            break
        if c == 406:
            raise RuntimeError("a job already holds this source: wait, or cancel it (7.6)")
        time.sleep(90)
    else:
        raise RuntimeError(f"start failed: {c} {r}")
    job = r["jobId"]
    while True:
        time.sleep(40)
        c, j = call("GET", f"{API}/data360/observable/v1/jobs/{job}?expandChildren=TASK-HIERARCHY")
        if isinstance(j, dict) and j.get("status") in TERMINAL:
            return j["status"], [(t["name"], t["status"]) for t in j.get("tasks", [])]

# Select the Metadata services, then: for cs_id, caps in plan: print(scan(cs_id, caps)); then deselect the services.
```

### 7.4 When is a scan done? (L-CDGC-039)

A 201 or 406 only means accepted or active. Call it done when every capability task is COMPLETED **and** the result is
visible: `core.profiled=True` and a `lastProfiledState` other than "Not Profiled" on sampled columns, classifications
present, a fresh `lastScanned`, the expected counts in search (see
[04 Search, Lineage & Marketplace](04-search-lineage-marketplace.md) section 5). Report metadata extraction separately
from profiling, DQ, lineage, observability and classification.

### 7.5 Verifying on the agent

- Scanner Sync log: `<agent_home>/apps/Metadata_Foundation_Agent/data/workspaces/<source>-<uuid>/logs/<jobId>_Sync.log`.
  Success markers: `Metadata extraction application completed`, `ProcessEnd status:Success`, `failed:0`,
  `BULK_CONTENT_PUBLISHER "Writing N records"`, `BulkIngestionResponse` with Success (L-CDGC-041).
- A "not found" in that log can be text inside a cataloged function body, not an error (L-CDGC-041).
- A Snowflake extraction can end PARTIAL_COMPLETED, with no message in the job tree, when the connection's role cannot
  read tags. The Sync log (`<agent_home>/apps/Metadata_Foundation_Agent/data/workspaces/<source>-.../logs/*_Sync.log`)
  shows 'Unable to resolve TAGS objects from SNOWFLAKE for filter ...' and 'Total objects processed count N is the same
  as objects count with errors. Status will be altered to Partially completed', while its 'Overwriting table
  definition' lines show every table and view (with view SQL) extracted, and the new tables appear in search. Read the
  scanner log before treating a partial as a failure (L-CDGC-168).
- Profiling failures: `<agent_home>/apps/Data_Integration_Server/logs/s_cp_*_session.log` names the failing table; the
  observable API gives no error detail (L-CDGC-043).
- Zero profiled columns everywhere: check the pmdtm exit code (127 = a native library, 134 = SIGABRT, 137 = OOM)
  (L-CDGC-044).
- Monitor rows still RUNNING after a source was deleted are display orphans when no scanner process is left (L-CDGC-042).
- A scan that hangs: the scanner writes thread dumps every 10 minutes under
  `<agent_home>/apps/Metadata_Foundation_Agent/data/workspaces/<source>-*/jobs/<ts>-*/debug/thread_dumps/`. A Tableau scan
  stuck in Test Connection showed `ConnectionsChecker.checkConnections` waiting with no timeout on a socket to a
  stitched warehouse that had been shut down (L-CDGC-223).

### 7.6 Cancel

Cancel over REST (L-CDGC-221, L-CDGC-225, 2026-10-26). The superseded verdict that no REST cancel exists (L-CDGC-040)
came from the wrong routes, such as `POST.../catalogsource/<id>/cancel`.

```
POST https://cdgc-api.<domain>.informaticacloud.com/ccgf-orchestration-management-api-server/api/v1/jobs/<jobId>/operations/cancel
(the three identity headers, empty body)  -> 200; the job shows CANCEL_REQUESTED at once
```

- The console's Cancel Job (MCC > Monitor > <job>) sends exactly this call; a script with the session used for other
  cdgc-api calls also got 200.
- **Timing depends on the running task.** With Test Connection running, the job reached CANCELLED within 1-2 minutes
  and released the source lock. A cancel sent during Catalog Source Extraction left the job CANCEL_REQUESTED for more
  than 50 minutes, with Bulk Ingestion STARTING, and the source stayed locked. Poll for CANCELLED before you start
  the next job, and cancel before extraction starts when you can.
- A stuck job holds the source lock: runs return 406 and a delete returns 400 until it is cancelled. Find its id in
  either job list (7.2).

---

## 8. Operating scans safely

- **Service window.** Select the Metadata services, scan serially, deselect (L-CDGC-045). Deselecting after one window gave
  back about 3.7 GB of RAM on a 32 GB host and roughly halved CPU pressure.
- **One source at a time**, profiling only where you need it. Profiling is the expensive and failure-prone capability.
- **Scope first.** Include filters on warehouses (L-CDGC-027, L-CDGC-033). Filters change what you pay for.
- **CLAIRE interplay.** CLAIRE goes blind on a source while it scans and lags fresh scans: no rescans within about 40 minutes
  of a demo (L-CDGC-090).
- **Cost.** Scans are IPU-metered; configuration and reads are not (L-CDGC-103). Never loop "run until accepted".
- **Plan the time** (L-CDGC-230, one 2 vCPU / 16 GB Secure Agent, one job at a time): an IICS source (Metadata
  Extraction + Lineage Discovery, one project) 1,295-1,542 s, with Lineage Discovery STARTING until extraction, Merge
  Operation and Connection Assignment finish (16-18 min) and then 3-5 min; Snowflake (one schema) 768 s; SharePoint
  Online 493 s; Azure Blob (one container) 4-5 min; Tableau (a few workbooks, through a tunnel) 819 s; the Data
  Quality capability about 15 min, holding the source lock. Rescanning storage, IICS, warehouse and BI in that order
  took about an hour: run them in sequence.
- **Scans through a temporary tunnel** (L-ENV-099): run the tunnel as its own process for the whole scan window, make
  the poll retry DNS and socket errors, and close the tunnel only at a final job state; a helper whose cleanup closed
  the tunnel after one DNS error killed a running scan.
- **A stitched warehouse that is gone hangs the scan** (L-CDGC-223): a Tableau scan sat in Test Connection with no
  timeout because an in-scope workbook read a shut-down warehouse; it blocks the next scan with 406 until cancelled.
  Give the projects you need their own source stitched only to live warehouse sources, or drop the dead project from
  the filter (with Metadata Change Option = Retain first: Delete with a narrowed filter purges the dropped project's
  assets).
- **Auto-generated DQ schedules (L-CDGC-152).** With catalog Data Quality scoring and CLAIRE rule
  recommendations in use, `GET /api/v2/schedule` lists three schedules created within one second of each other and owned
  by the user who ran the job: `DQ_Capability_Schedule_Daily_<epochMs>`, `..._Weekly_<epochMs>` and
  `..._Monthly_<epochMs>` (description "Auto generated schedule for existing Rule Templates"). A source whose Data
  Quality switches read `Run Rule Occurrence Frequency: true` and `Data Quality Automation: true` (scope "Apply on all
  Data Elements") runs accepted rule occurrences on those schedules and attaches automation rules to every data element
  in scope, and a clone of it inherits that. For a new estate:
  1. In the clone's Data Quality entry set `{"key": "Run Rule Occurrence Frequency", "values": ["false"]}` and
     `{"key": "Data Quality Automation", "values": ["false"]}` unless you want IDMC-side scheduling.
  2. Run Metadata Extraction alone first; enable profiling, classification and DQ only once the asset list holds just the
     intended tables.
  3. After every accept of recommended rules, re-read `GET /api/v2/schedule` for `DQ_Capability_Schedule_*`.
  4. Count those runs through the catalog jobs API: they are not in the v2 activity log (L-IPU-055).

---

## 9. Update, rename, rebind

- **Update** (L-CDGC-020): GET, save the before-state, edit, strip read-only fields but keep `id` = the path id, multipart
  `PUT .../datasources/<id>` (PATCH fallback), read it back. Without `id` in the JSON part the PUT answers 400 'dataSource
  id in request path and body do not match' (L-CDGC-163). Filters and options changed this way take effect on the next
  scan. The read-back returns `capabilities` and `typeCapabilities` in a different order from the body sent: compare
  them keyed by `capabilityName`, not by index (L-CDGC-212).
- **Rename** (L-CDGC-141): GET the source, change `name`, multipart `PUT` it back: 200, the id is unchanged and the
  read-back shows the new name. In the same change update every IICS source's Lineage Discovery filter of type
  "Catalog Source Name" (it stores sources by name, so stitching silently loses a renamed one), your local name-to-id
  maps and scripts, then rescan the renamed source so CLAIRE stops showing the old resource name (L-CDGC-147).
  Display-style names with spaces, dots and hyphens are accepted (`<Demo> 3.0 - Snowflake`); rename the listed sources
  first, then the IICS source with its rewritten filter in one PUT, and check its Metadata Extraction filter, which
  names projects by name and so drops a project renamed in Explore (L-CDGC-186).
- **Rebind to another connection**: editing `ConnectionId` to a connection's federated id was refused; a PUT that
  changed the connection binding, with `id` repeated, read back with the new binding (L-CDGC-163). When the database
  only moved, update the existing connection in place (`POST /api/v2/connection/<id>`): every catalog source that uses
  it stays bound (L-CDGC-049).

## 10. Rescans after source changes

- Set `Metadata Change Option` = `Delete` before rescanning a source whose objects were removed or renamed; with `Retain` a
  renamed database leaves both trees in the catalog (L-CDGC-028). Do not combine Delete with a narrowed filter when the
  dropped scope still holds wanted assets: it purges every asset of the dropped scope, so set Retain or use a new source
  when you narrow scope (L-CDGC-223, L-CDGC-157).
- Extend include filters to newly added datasets (e.g. CDC or real-time views) before the rescan (L-CDGC-028).
- A newly added view is not cataloged unless it is inside the include scope, and its lineage needs Lineage Discovery and a
  rescan (L-CDGC-087).
- A scan may overwrite catalog descriptions with blank source descriptions: re-run your curation script afterwards
  (L-CDGC-055).

## 11. Purge and delete

1. Harvest what is keyed to the source's asset GUIDs (term links, accepted classifications) into a name-keyed manifest
   (L-CDGC-084).
2. Save the definition: `GET.../datasources/<id>`.
3. `DELETE https://cdgc-api.<domain>.informaticacloud.com/ccgf-catalog-source-management/api/v1/datasources/<id>` starts a
   bulk purge job that removes the harvested metadata (L-CDGC-047).
4. The definition stays listed: delete it in MCC > Catalog Sources (keep the id list for that UI step).
5. Only then delete the connection; while a catalog source holds it, `DELETE /api/v2/connection/<id>` answers
   "asset used by another asset" (after `REPO_10242` for mappings) (L-CDGC-048).

**Replacing a source** with another for the same system (for example JDBC to the native scanner): MERGE the IICS and
Tableau connection references onto the new source and SPLIT them from the old one, one job at a time (L-CDGC-210). The
SPLIT leaves the edges the old source already holds, so lineage shows the flow twice until the old source is purged
with the steps above; move curated edges and term links to the new assets first (L-CDGC-211). A SPLIT also does not hold
against the catalog's location-based assignment: after a COMPLETED SPLIT the next scan read the reference ASSIGNED again
and kept opening the dead connection. To keep a connection out of a scan, change what the scanning source covers (a
new source scoped to the assets you need) or retire the target source (L-CDGC-226).

---

## 12. Troubleshooting

| Symptom | Likely cause | Fix | Lesson |
|---|---|---|---|
| Scan FAILED: "None of the Assets met filter criteria" | PostgreSQL filter written as `db.schema.*` | `schema.*` | L-CDGC-026 |
| Metadata Extraction PARTIAL_COMPLETED on every run, "Total objects processed count <n> is the same as objects count with errors", although the objects were read | `AccessDeniedException` on `/tmp/poifiles` in the scanner log: the first agent OS user created the shared Apache POI temp directory with mode 755 and a second agent user cannot write its Excel scan report | `chmod 1777 /tmp/poifiles`; write-test as both agent users; check other `/tmp` directories owned by the first user; on a new shared host create it 1777 up front or give each agent its own `java.io.tmpdir` | L-CDGC-150 |
| "Could not find matching schemas" in the scan log | an include filter names a dataset that does not exist | remove the entry | L-CDGC-151 |
| BigQuery scan FAILED: 'Unable to resolve EXTERNAL_TABLES/VIEWS/... objects from BIG_QUERY ... select s.schema_name ...', 'No input was processed' | the identity has dataset-level roles only; the region-level SCHEMATA query needs project-level dataset metadata (and job user, L-CDGC-154) | project-level metadata read, for example roles/bigquery.metadataViewer | L-CDGC-182 |
| IICS source PARTIAL_COMPLETED: 'Failed to extract CDIR inputs: Could not parse filter expression: Include:All Types:<project>' | a CDIR (Database Ingestion) filter with Filter Conditions 'All Types' | Filter Conditions 'Database'; CDC tasks then catalog but get no lineage edges, so add them as curated lineage | L-CDGC-183 |
| BigQuery catalog-source Data Profiling FAILED, no message, no agent session | unresolved; the scanner stores STRING columns without a length and NUMERIC(p,s) as a type string | profile BigQuery with Data Profiling profiles over REST; vendor case with the job ids | L-CDGC-184 |
| BigQuery Data Quality PARTIAL_COMPLETED, the string rules of one table unscored | that table also carries a decimal-input rule occurrence (NUMERIC, NUMERIC(p,s) or a view column) | text-input twins of the decimal rules on STRING snapshot columns | L-CDGC-185 |
| Views with no lineage; `UnsupportedOperationException` or `Parse error NoViableAlt` in the scan log | the BigQuery SQL analyzer cannot parse that view's SQL | see [04](04-search-lineage-marketplace.md) section 8 | L-CDGC-151 |
| `GET /api/v2/connection/source/<connId>` returns 200 `[]` | that read proves nothing about table visibility (also seen for a known-good connection) | judge visibility by a Metadata Extraction run | L-CDGC-150 |
| Snowflake Metadata Extraction PARTIAL_COMPLETED, no message in the job tree | the role cannot read tags ('Unable to resolve TAGS objects from SNOWFLAKE' in the Sync log); every table and view was still extracted | read the Sync log (7.5); confirm the new tables in search | L-CDGC-168 |
| Data Quality: Rule Profiling FAILED in under a second, no error text | no runtime environment in the Scope groups | add both Scope groups with `<reId>`, PUT, read back, rerun `["Data Quality"]` | L-CDGC-143 |
| Data Quality run PARTIAL_COMPLETED, no message, one rule occurrence never scored | a decimal-input rule bound to a text (VARCHAR) column | bind a numeric column of a typed view ([DQ Scorecards](../08-data-quality/04-dq-scorecards-warehouse-pattern-and-data-profiling-scorecards.md) §4) | L-CDGC-170 |
| `DQ_Capability_Schedule_*` schedules appear | Data Quality automation switches on | switch them off (section 8) | L-CDGC-152 |
| COMPLETED WITH ERRORS on a JDBC PostgreSQL source | JDBC cannot read system catalogs | native connector | L-CDGC-023 |
| COMPLETED WITH ERRORS, "Only supported languages SQL, PL/pgSQL" | C-language extension functions skipped | benign | L-CDGC-042 |
| Profiling PARTIAL_COMPLETED | one table failed (pgvector, a column named `rows`, transient 503) | session log, profiling exclude, re-run profiling only | L-CDGC-043 |
| Metadata cataloged, 0 columns profiled | pmdtm dies at launch (missing library) or no Data Profiling capability | fix the library; add the capability | L-CDGC-044 |
| Every run 406 | a job holds the lock | wait, or cancel it (`jobs/<jobId>/operations/cancel`) and poll for CANCELLED | L-CDGC-221, L-CDGC-225 |
| A cancelled job stays CANCEL_REQUESTED for 50 min and more | the cancel reached it during Catalog Source Extraction | poll for CANCELLED; cancel before extraction | L-CDGC-225 |
| A Tableau scan sits in Test Connection RUNNING, extraction SUBMITTED, no timeout | an in-scope workbook reads a warehouse that is gone | cancel; a source scoped to live stitched warehouses (section 8) | L-CDGC-223 |
| A SPLIT reference reads ASSIGNED again at the next scan | location-based automatic assignment | change the scanning source's scope | L-CDGC-226 |
| Azure Blob Storage V3 catalog scan DISPATCH_REJECTED on the hosted runtime | that source refuses the Hosted Agent | scan on a Secure Agent | L-CONN-129 |
| A scan through a tunnel fails right after a DNS error | the helper's cleanup closed the tunnel | tunnel as its own process; retry DNS in the poll | L-ENV-099 |
| Salesforce: "no permissions to access connections which are selected" | not a connection-type wall; cause not isolated (Metadata services not selected, or a connection permission granted later) | select the Metadata services and rescan before building a new connection | L-CDGC-142 |
| IICS scans start failing | the stored user's password rotated | update the source; use a service login | L-CDGC-030 |
| IICS rescan FAILED at Catalog Source Extraction | unresolved (seen after flat-file tasks were added) | quiet-window rescan; filter bisect | L-CDGC-046 |
| Old and new trees both in the catalog | `Metadata Change Option` = Retain | Delete, rescan | L-CDGC-028 |
| New view missing | outside the include scope, or Metadata Extraction only | scope it; Lineage Discovery; rescan | L-CDGC-087 |
| Create 415 / 500 / 404 | JSON body / missing custom+endOfLife / trailing slash | see 3.1 | L-CDGC-014 |
| PUT 400 'dataSource id in request path and body do not match' | the JSON part omits `id` | set `id` to the path id, PUT, read back | L-CDGC-163 |
| SharePoint Online scan fails with AADSTS500011 (resource principal not found) | the site URL is the connection URL | URL = the tenant root, `Subsite_URL` = the full site URL | L-CDGC-162 |
| SharePoint Online scan fails with 'no protocol: sites/<site>/_api/web' | a relative subsite | `Subsite_URL` = the full site URL | L-CDGC-162 |
| SharePoint Online create answers 500 | a Scanner Configuration option omitted | send all of them (Partition Detection false) | L-CDGC-162 |
| List returns 0 sources | headers, pagination, or a login-specific quirk | your own id map; cross-check the UI | L-CDGC-018 |
| Scan start failed once | transient | wait 60-90 s, retry once | L-CDGC-038 |

---

## 13. Overturned beliefs (kept so nobody re-learns them)

| Earlier belief (dates) | Overturned by (date) |
|---|---|
| Scans can only be triggered in the UI; the ccgf-auth-pep 500 is a platform bug (2026-06-27 to 2026-07-25) (L-CDGC-120) | Three headers + non-empty `capabilityNames` -> 201 + jobId (2026-06-28) (L-CDGC-034) |
| 406 with zero profiled columns = a stuck scan is the root cause (2026-06-28) (L-CDGC-121) | The native profiling engine crashed at launch (2026-06-28) (L-CDGC-044) |
| Source types can only be picked in the MCC wizard (2026-07-04 to 2026-08-20) (L-CDGC-124) | `GET.../datasourceTypes` (2026-09-24) (L-CDGC-016) |
| Object selection, capability configuration and rebinding are MCC-only (2026-06-29 to 2026-08-20) (L-CDGC-127) | Multipart PUT of the edited definition (2026-09-25/29) (L-CDGC-020) |
| Registration and deletion are MCC-only where `catalog-source-management` is not routed (2026-08-18 to 2026-09-28) (L-CDGC-128) | Multipart create on the ccgf plane; REST purge (2026-09-24 to 2026-09-29) (L-CDGC-014, L-CDGC-047) |
| The scan capability is the enum `CATALOG_EXTRACT` (2026-07-25 to 2026-09-13) (L-CDGC-134) | Display names such as "Metadata Extraction" (2026-08-20, 2026-09-28) (L-CDGC-035) |
| The observable path form is disputed (2026-07-08) (L-CDGC-135) | List needs `/api/`, single-job poll does not (2026-07-10, 2026-09-29) (L-CDGC-037) |
| `readyToRun=false` blocks creation until a support ticket (2026-06-27) (L-CDGC-136) | Scans never blocked; creates validated with `IDS-SESSION-ID` (2026-06-28, 2026-09-24) (L-CDGC-022) |
| A Salesforce source on a legacy v2 Salesforce connection type cannot scan (2026-09-29) (L-CDGC-031) | The same source on the same native connection scanned every object (2026-09-30) (L-CDGC-142) |
| Running only the Data Quality capability returns 406 (2026-07-09) (L-DQ-044) | DQ alone runs once the Scope groups carry a runtime environment (2026-09-30) (L-CDGC-143) |
| There is no REST cancel for a catalog job; cancel in MCC (to 2026-10-25) (L-CDGC-040) | `POST .../jobs/<jobId>/operations/cancel`, captured from the console and replayed from a script (2026-10-26) (L-CDGC-221, L-CDGC-225) |

## Lessons cited in this doc

L-CDGC-007, 008, 014-049, 055, 084, 087, 090, 103, 141-143, 147, 159-163, 166, 168, 170, 206, 210-212, 221, 223, 225, 226, 230, 234, 245, 269, 270, L-CONN-129, L-ENV-099,
L-IPU-055, and the superseded L-CDGC-031, 040, 120, 121, 124, 127, 128, 134, 135, 136, 188 and L-DQ-044 (superseded by L-CDGC-143).
Full text: [Lessons: CDGC](lessons.md).
