"""
idmc_verbmatrix_data.py — per-endpoint HTTP verb support matrix, per service,
plus the API-vs-MCP mapping.

Cell vocabulary (one per verb column):
  YES  verified working on a live org
  DOC  documented by Informatica, not exercised here
  UI   the operation exists but only in the user interface
  4xx  explicitly rejected, code shown (405 = read-only resource)
  --   not documented and not observed. UNKNOWN, not "absent".
"""

Y = "YES"
D = "DOC"
UI = "UI"
N = "--"

# ---------------------------------------------------------------------------
# 1. ADMINISTRATION / CORE  (platform v2 + v3)
# ---------------------------------------------------------------------------
VM_ADMIN = [
    ["/public/core/v3/login", N, Y, N, N, N, "POST only. Returns sessionId + product list + baseApiUrl"],
    ["/ma/api/v2/user/login", N, Y, N, N, N, "Legacy v2 login. Returns icSessionId + serverUrl"],
    ["/identity-service/api/v1/Login", N, Y, N, N, N, "Returns sessionId + orgId. Also works with SAML"],
    ["/identity-service/api/v1/jwt/Token", N, Y, N, N, N, "Mints the JW token. Needs the session as cookie AND header"],
    ["/identity-service/api/v1/CurrentUserInfo", Y, N, N, N, N, "Who am I"],
    ["/identity-service/api/v1/Orgs", Y, N, N, N, N, "Org list"],
    ["/public/core/v3/objects", Y, "405", N, "404", N, "Read-only. The universal asset-inventory endpoint"],
    ["/public/core/v3/users", Y, Y, "405", "405", Y, "No in-place edit. Delete and recreate"],
    ["/public/core/v3/users/{id}", Y, N, "405", "405", Y, "Body key is name, NOT userName"],
    ["/public/core/v3/userGroups", Y, Y, N, N, Y, "roles = a list of plain id STRINGS, not objects"],
    ["/public/core/v3/roles", Y, N, N, N, N, "59 roles on the probed org"],
    ["/public/core/v3/privileges", Y, N, N, N, N, "897 privileges. The entitlement ground truth"],
    ["/public/core/v3/securityLog", Y, N, N, N, N, "The canonical audit log. limit 100-1000"],
    ["/public/core/v3/activityLog", Y, N, N, N, N, "v3 activity log"],
    ["/public/core/v3/schedule", Y, N, N, N, N, "Read. Create is on the v2 plane"],
    ["/public/core/v3/license/metering/ExportMeteringData", N, Y, N, N, N, "Async IPU export. 201 + jobId"],
    ["/public/core/v3/license/org/{id}", Y, N, N, N, N, "Per-org licence detail"],
    ["/api/v2/org", Y, N, N, N, N, "Org id and name"],
    ["/api/v2/alerts", N, Y, N, N, N, "Platform alerts"],
    ["/frs/v1/BaseEntities", Y, N, N, N, N, "OData asset repository. $filter supported"],
    ["/public/core/v3/{licenses, jobs, connections, runtimeEnvironments}", "404", N, N, N, N, "These four live on the v2 plane only"],
]

# ---------------------------------------------------------------------------
# 2. MIGRATION (export / import)
# ---------------------------------------------------------------------------
VM_MIGR = [
    ["/public/core/v3/export", "405", Y, N, N, N, "POST starts the job. 400 if objects[] is empty"],
    ["/public/core/v3/export/{id}", Y, N, N, N, N, "Export job status"],
    ["/public/core/v3/export/{id}/package", Y, N, N, N, N, "Downloads the round-trippable zip"],
    ["/public/core/v3/import/package", N, Y, N, N, N, "Genuine zips only. Hand-built = 400 MigrationSvc_030"],
    ["/public/core/v3/import/{jobId}", Y, N, N, N, N, "Import job status"],
    ["/public/core/v3/import", N, "404", N, N, N, "No such path. Use /import/package"],
    ["/public/core/v3/import/upload", N, "415", N, N, N, "Unsupported media type"],
]

# ---------------------------------------------------------------------------
# 3. CDI
# ---------------------------------------------------------------------------
VM_CDI = [
    ["/api/v2/connection", Y, Y, N, N, N, "POST creates. Verified create-then-delete round trip"],
    ["/api/v2/connection/{id}", Y, Y, N, N, Y, "v2 pattern: POST with the id in the path IS the update"],
    ["/api/v2/connection/test/{id}", Y, N, N, N, N, "Metadata handshake. Not a data run, so 0 IPU"],
    ["/api/v2/connection/source/{cid}", Y, N, N, N, N, "Browse source metadata. 403 on some connections"],
    ["/api/v2/connector", Y, N, N, N, N, "153 connectors in the global catalog"],
    ["/api/v2/connector/metadata", Y, N, N, N, N, "200 with an empty array = connector not activated"],
    ["/api/v2/runtimeEnvironment", Y, Y, N, N, N, "POST exists (400 on an empty body proves the verb)"],
    ["/api/v2/agent", Y, N, N, N, N, "Agent list"],
    ["/api/v2/agent/details/{agentId}", Y, N, N, N, N, "agentEngines[] = what is really deployed"],
    ["/api/v2/agent/installerInfo/{platform}", Y, N, N, N, N, "downloadUrl + installToken for headless install"],
    ["/api/v2/agent/service", N, "403", N, N, N, "Agent service enablement is an Administrator UI toggle"],
    ["/api/v2/mttask", Y, Y, "405", N, N, "POST needs an existing mappingId (403 APP_13533 without)"],
    ["/api/v2/mttask/{id}", Y, Y, "405", N, N, "POST with id = update. No PUT on the v2 plane"],
    ["/api/v2/job", Y, Y, N, N, N, "RunAJob. POST {taskId, taskType} returns a runId"],
    ["/api/v2/mapping", Y, "400", N, N, N, "POST returns HTML 'Internal error'. Designer canvas only"],
    ["/api/v2/schedule", Y, Y, N, N, N, "POST creates a real native schedule"],
    ["/api/v2/activity/activityLog", Y, N, N, N, N, "Job telemetry. rowLimit param"],
    ["/api/v2/activity/activityMonitor", Y, N, N, N, N, "Currently-running jobs"],
    ["/api/v2/task?type=X", Y, N, N, N, N, "403 for MI_TASK and DVT types"],
    ["/api/v2/taskflow", Y, "404", N, N, N, "Read works. Publish has no verb"],
    ["/api/v2/workflow", Y, N, N, N, N, "Workflow read"],
]

# ---------------------------------------------------------------------------
# 4. CAI — asset lifecycle
# ---------------------------------------------------------------------------
VM_CAI_ASSET = [
    ["/active-bpel/asset/v1/publish", "405", Y, N, N, N, "Bulk publish, max 199 assets. Returns 202 + jobId"],
    ["/active-bpel/asset/v1/publish/{id}", Y, N, N, N, N, "Publish job information"],
    ["/active-bpel/asset/v1/publish/{id}/Status", Y, N, N, N, N, "Per-asset itemState SUCCESS / ERROR"],
    ["/active-bpel/asset/v1/unpublish", N, Y, N, N, N, "Bulk unpublish, same body shape, max 199"],
    ["/active-bpel/asset/v1/unpublish/{id}", D, N, N, N, N, "Unpublish job information"],
    ["/active-bpel/asset/v1/unpublish/{id}/Status", D, N, N, N, N, "Unpublish status"],
    ["/active-bpel/asset/v1/status", Y, N, N, N, N, "Filter by MimeType and PublicationStatus"],
    ["/active-bpel/asset/v1/update?assetType=Process", N, N, D, N, N, "Update allowed users/groups, anon access, tracing"],
    ["/active-bpel/asset/v1/update?assetType=AppConnection", N, N, D, N, N, "Update connection attributes. Needs a UI republish after"],
    ["/active-bpel/asset/v1/processes", N, "500", N, N, N, "Authoring a process is designer-canvas only"],
    ["/active-bpel/asset/publish  (no /v1/)", N, "403", N, N, N, "The wrong path. This is the origin of the publish myth"],
]

# ---------------------------------------------------------------------------
# 5. CAI — invocation + runtime administration
# ---------------------------------------------------------------------------
VM_CAI_RT = [
    ["/active-bpel/rt", Y, N, N, N, N, "List deployed processes"],
    ["/active-bpel/rt/{Process}", Y, Y, D, D, D, "A process can be exposed on ANY of the five verbs"],
    ["/active-bpel/public/rt/{Tenant}/{Process}", Y, Y, D, D, D, "Anonymous. No auth header at all"],
    ["/active-bpel/public/rt/{Tenant}/{Proc}/event/{Msg}", N, D, N, N, N, "Anonymous message event"],
    ["/active-bpel/rt/{Process}?swagger", D, N, N, N, N, "Spec discovery. ?wsdl on the soap path"],
    ["/active-bpel/restadmin/urn/{OrgID}", Y, N, N, N, N, "Read all URN mappings"],
    ["/active-bpel/restadmin/urn/", N, N, D, N, D, "PUT adds or updates, DELETE removes. No POST"],
    ["/active-bpel/restadmin/scheduler/schedules", Y, D, D, N, D, "Full CRUD. Writes return 204. No PATCH"],
    ["/active-bpel/restadmin/processes/", Y, N, N, N, N, "Default page size 20. listStart + maxReturn to page"],
    ["/active-bpel/restadmin/processes/{id}/suspend", N, N, D, N, N, "PUT, returns 204"],
    ["/active-bpel/restadmin/processes/{id}/resume", N, N, D, N, N, "PUT, returns 204"],
    ["/active-bpel/restadmin/processes/{id}/terminate", N, N, D, N, N, "PUT, returns 204"],
    ["/active-bpel/local/restadmin/eventconnection/start", N, D, N, N, N, "Start a listener-based event source"],
    ["/active-bpel/local/restadmin/eventconnection/stop", N, D, N, N, N, "Stop a listener event source"],
    ["/active-bpel/odata/v4/{connection}", Y, N, N, N, N, "OData v2 and v4. $metadata for the contract"],
    ["API activate / deactivate", N, N, N, N, N, "No verb at any path. Console click only"],
]

# ---------------------------------------------------------------------------
# 6. CDGC
# ---------------------------------------------------------------------------
VM_CDGC = [
    ["/data360/executable/v1/catalogsource/{id}", "405", Y, N, N, "405", "POST triggers a scan. Send capabilityNames[] or you get 500"],
    ["/data360/executable/v1/executables", Y, Y, N, N, N, "Executable list and run"],
    ["/data360/executable/v1/catalogsource/{id}/cancel", N, "404", N, N, N, "No cancel verb. Stuck scans clear only in the MCC UI"],
    ["/data360/observable/api/v1/jobs", Y, N, N, N, N, "Job list. The /api/ segment is REQUIRED here"],
    ["/data360/observable/v1/jobs/{jobId}", Y, N, N, N, N, "Poll one job. ?expandChildren for the task tree"],
    ["/data360/catalog-source-management/v1/catalogsources", Y, Y, N, N, Y, "Register and delete a catalog source"],
    ["/data360/catalog-source-management/v1/catalogsources/{id}", Y, N, N, N, Y, "Source detail"],
    ["/data360/catalog-source-management/v1/catalogsourcetypes", "404", N, N, N, N, "Type list exists only in the MCC New-Source wizard"],
    ["/data360/search/api/v1/search", "405", Y, N, N, N, "POST a raw Elasticsearch DSL body"],
    ["/ccgf-contentv2/api/v1/publish", N, Y, N, N, N, "The CDGC write plane. 207 Multi-Status: check each item"],
    ["/data360/glossary/v1/terms  (~20 variants)", "404", "404", "404", "404", "404", "Empty-body 404 = the route is not mounted at all"],
    ["/data360/classification/api/v1/accept  (37+ paths)", N, "404", "404", "404", N, "No Accept anywhere. The UI offers only Dismiss"],
    ["/data360/lineage/v1/*  (25+ variants)", "404", "404", N, N, N, "No lineage endpoint. Read lineage via catalog objects or MCP"],
    ["/data360/asset/v1/*/stakeholders  (100+ variants)", "404", "404", "405", "404", N, "Steward and owner assignment has no verb"],
]

# ---------------------------------------------------------------------------
# 7. CDQ
# ---------------------------------------------------------------------------
VM_CDQ = [
    ["/quality/public/v2/dictionaries/", N, Y, N, N, N, "Create. name <=125 chars, <=42 unique columns"],
    ["/quality/public/v2/dictionaries/{id}", N, N, N, N, D, "Delete a dictionary"],
    ["/quality/public/v2/dictionaries/{id}/rows", N, D, D, N, D, "POST adds, PUT replaces all, DELETE clears. 10,000 rows/call"],
    ["/quality/public/v2/dictionaries/{id}/finishUpload", N, D, N, N, N, "Mandatory commit. Skip it and you get 424"],
    ["/quality/public/v2/scorecards", "404", "404", N, N, N, "The public v2 API is dictionaries and nothing else"],
    ["/dataquality/addressverification/api/v1/process", "405", D, "405", "405", "405", "POST only. The vendor documents 405 for everything else"],
    ["/data360/dq/v1/ruleSpecifications", "404", "404", "404", "404", "404", "Native rule CRUD has no route"],
    ["/data360/businessDataset/v1  (RuleOccurrence)", N, "404", N, N, N, "The object that computes a score has no create verb"],
]

# ---------------------------------------------------------------------------
# 8. DATA PROFILING
# ---------------------------------------------------------------------------
VM_PROF = [
    ["/profiling-service/api/v1/profile", Y, D, N, N, N, "List. Vendor states create/update/delete exist"],
    ["/profiling-service/api/v1/profile/{uuid}", Y, N, D, D, D, "GET verified. DELETE appears in the vendor guide"],
    ["/profiling-service/api/v1/runDetail/{uuid}/filter", Y, N, N, N, N, "Run history: status, rows, cost"],
    ["/profiling-service/api/v1/ruleOccurrence/...{uuid}", Y, N, N, N, N, "Scorecard rule bindings for a profile"],
    ["/profiling-service/api/v1/ruleOccurrence/ruleType", Y, N, N, N, N, "The six DQ dimensions"],
    ["/metric-store/api/v1/odata/Profiles('{uuid}')/Columns", Y, N, N, N, N, "Per-column scored metrics. OData, $count works"],
    ["/metric-store/.../Profiles('{uuid}')/Insights|Patterns", Y, N, N, N, N, "Insights, patterns, value frequencies"],
    ["Query CRUD  (create / update / delete queries)", D, D, D, D, D, "Vendor-stated. Paths are in a guide not held locally"],
]

# ---------------------------------------------------------------------------
# 9. MASS INGESTION
# ---------------------------------------------------------------------------
VM_CMI = [
    ["/dbmi/public/api/v2/task/create", N, D, N, N, N, "Vendor-documented 201. Returns 404 on the probed org"],
    ["/dbmi/public/api/v2/task/details", "404", N, N, N, N, "404, and 503 on the other host"],
    ["/dbmi/public/api/v2/job/status", "404", N, N, N, N, "No ingestion job status"],
    ["/api/v2/miTask  (+6 name variants)", "404", "500", N, N, N, "POST returns identity-service login HTML"],
    ["/public/mi/v1/tasks  (+8 variants)", "404", "404", N, N, N, "No static resource"],
    ["Task authoring", UI, UI, UI, UI, UI, "Wizard only. Engines ARE running: this is not a licence gap"],
    ["Run monitoring", Y, N, N, N, N, "Via /api/v2/activity/activityLog"],
]

# ---------------------------------------------------------------------------
# 10. DATA MARKETPLACE
# ---------------------------------------------------------------------------
VM_DMP = [
    ["/data360/marketplace/api/v1/dataAssets", Y, Y, D, N, N, "Vendor documents GET, POST and PUT on this resource"],
    ["/data360/marketplace/api/v1/dataAssets/{id}/dataElements", D, D, D, N, N, "GET, POST, PUT per the CAI Design guide"],
    ["/data360/marketplace/api/v1/dataCollections", Y, Y, N, N, N, "Create returns 201"],
    ["/data360/marketplace/api/v1/categories", Y, Y, N, N, N, "Create returns 201"],
    ["/data360/marketplace/api/v1/orders", Y, Y, N, N, N, "POST places a real order"],
    ["/data360/marketplace/api/v1/termsOfUse", Y, Y, N, N, N, "Create returns 201"],
    ["/data360/marketplace/api/v1/dataAssets/{id}/ratings", N, N, "405", N, N, "Ratings have no write verb"],
    ["/data360/marketplace/api/v2/data-collections", Y, N, N, N, N, "v2 read plane"],
    ["/data360/marketplace/api/v2/delivery-targets", Y, Y, N, N, N, "Create a delivery target"],
    ["/data360/marketplace/api/v2/orders", N, Y, N, N, N, "Order on the v2 plane"],
    ["/data360/marketplace/api/v2/delivery-targets/templates", "400", "405", N, N, N, "Wrong plane. Templates live on cdmp-marketplace"],
    ["/cdmp-marketplace/api/v1/provisioning/deliveryTemplates", Y, "405", N, N, N, "Read only. Creating a template is UI"],
    ["/cdmp-marketplace/api/v1/provisioning/deliveryFormats", Y, N, N, N, N, "Read the format IDs"],
    ["/cdmp-marketplace/api/v1/provisioning/deliveryMethods", Y, N, N, N, N, "Read the method IDs"],
]

# ---------------------------------------------------------------------------
# 11. MDM / C360 / B360 / R360
# ---------------------------------------------------------------------------
VM_MDM = [
    ["/business-entity/public/api/v1/entity/{be}", N, Y, N, N, N, "POST ingests a source record. Needs ?sourceSystem="],
    ["/business-entity/public/api/v1/entity/{be}/{id}", Y, N, D, D, N, "GET disputed 200 vs 404. PUT and PATCH documented"],
    ["/business-entity/public/api/v1/entity-xref/{...}", D, N, D, D, N, "Source records. USE THIS for source-system updates"],
    ["/business-entity/public/api/v1/entity/{be}/search", "404", "405", N, N, N, "No public search or list on the probed org"],
    ["search  (documented resource)", N, D, N, N, N, "Search across or within business entities"],
    ["searchmatch  (documented resource)", N, D, N, N, N, "Match against the published match model"],
    ["/business-entity/public/api/v1/deploy  (~20 paths)", "404", "404", "404", N, N, "Business-entity deploy has no verb. B360 Modeler only"],
    ["/data360/ingress/api/v1/jobs", "404", "404", N, N, N, "Ingress and match-merge triggers have no verb"],
    ["/data360/mdm/v1/businessEntities  (7+ bases)", "404", N, N, N, N, "No BE list endpoint resolves"],
    ["/rdm-service/external/v1/search", Y, "400", N, N, N, "Reference 360 search. GET works, POST does not"],
    ["/rdm-service/api/v1/referenceDataSets", "404", N, N, N, N, "No R360 dataset CRUD"],
]

# ---------------------------------------------------------------------------
# 12. OPERATIONAL INSIGHTS  (GraphQL)
# ---------------------------------------------------------------------------
VM_OI = [
    ["/active-bpel/opsanalytics-das/metrics?query={processJobReport(..)}", D, N, N, N, N, "GraphQL. 13 months of history. Accept: text/csv"],
    ["/active-bpel/opsanalytics-das/metrics?query={processRunsByNameEnv(..)}", D, N, N, N, N, "Aggregated by process name and environment. 1 month"],
    ["Full GraphQL schema", N, N, N, N, N, "Withheld from the guide. See Informatica KB 000259754"],
    ["/public/core/v3/operationalInsights", "404", N, N, N, N, "Wrong plane. OI is GraphQL on the active-bpel host"],
    ["Alert rules, MDM monitoring, DI job export", UI, UI, UI, UI, UI, "Console only. Metrics refresh once a week"],
]

# ---------------------------------------------------------------------------
# 13. DAM / API MANAGER / CLAIRE
# ---------------------------------------------------------------------------
VM_OTHER = [
    ["/data360/dam/v1/policies  (~40 variants)", "404", "404", "404", "404", "404", "DAM engine IS running. No REST plane on the probed org"],
    ["/public/apim/v1/apis  (+5 variants)", "404", "404", N, N, N, "API Manager engine IS running. No authoring verb"],
    ["/public/api/v1/apiPortal", "404", N, N, N, N, "Developer Portal. The cleanest true entitlement gap"],
    ["/data360/clairegpt/*  (32-path sweep)", "404", "404", N, N, N, "No engine deployed. Licence console disagrees: CONTESTED"],
    ["/dataprep/projects, /prep/v1/projects", "404", "404", N, N, N, "Data Preparation"],
    ["/api/v2/task?type=DVT", "403", N, N, N, N, "403 'DVT is not a valid task type'"],
]

# ===========================================================================
# API vs MCP
# ===========================================================================

# The 11 MCP actions mapped onto their REST equivalent
MCP_TO_REST = [
    ["CDGC Metadata Search", "search_metadata", "READ",
     "POST /data360/search/api/v1/search", "YES",
     "REST is richer: raw Elasticsearch DSL vs one natural-language string"],
    ["CDGC Metadata Search", "get_asset_details", "READ",
     "no single equivalent", "PARTIAL",
     "Returns lineage + profile in one call. The REST lineage paths all 404"],
    ["Customer Identification", "search_master_record", "READ",
     "no equivalent", "NO",
     "Fuzzy MDM match. REST has no public search or list resource"],
    ["Customer Identification", "get_master_record_details", "READ",
     "GET /business-entity/public/api/v1/entity/{be}/{id}", "DISPUTED",
     "The REST equivalent is the contested 200-vs-404 endpoint"],
    ["Data Provisioning", "list_data_collections", "READ",
     "GET /data360/marketplace/api/v1/dataCollections", "YES",
     "Straight wrapper"],
    ["Data Provisioning", "list_delivery_targets", "READ",
     "GET /cdmp-marketplace/api/v1/provisioning/*", "YES",
     "Misnamed: it returns collection detail, not a target list"],
    ["Data Provisioning", "checkout_data_order", "CREATE",
     "POST /data360/marketplace/api/v1/orders", "YES",
     "The only MCP action that persists anything new"],
    ["Job Management", "run_mapping_task", "EXECUTE",
     "POST /api/v2/job", "YES",
     "Straight wrapper over RunAJob"],
    ["Job Management", "get_job_status", "READ",
     "GET /api/v2/activity/activityLog", "YES",
     "REST is richer: full history rather than one job"],
    ["Job Management", "stop_running_job", "EXECUTE",
     "v2 Stop Job resource", "YES",
     "Straight wrapper"],
    ["Address Verification", "verify_address", "CHECK",
     "POST /dataquality/addressverification/api/v1/process", "YES",
     "REST is richer: 6 modes, 1,000 addresses per batch call"],
]

# Capability-level side by side
CAP_COMPARE = [
    ["Search / discover catalog assets", "YES", "YES", "Both. REST takes Elasticsearch DSL; MCP takes natural language"],
    ["Read asset lineage", "NO", "YES", "MCP ONLY. Every REST lineage path returns 404"],
    ["Read profiling statistics", "YES", "YES", "REST on the dqprofile host; MCP bundles it into get_asset_details"],
    ["Trigger a catalog scan", "YES", "NO", "REST ONLY. POST executable/v1/catalogsource/{id}"],
    ["Register or delete a catalog source", "YES", "NO", "REST ONLY"],
    ["Read DQ scores / scorecards", "YES", "NO", "REST ONLY, and read-only at that"],
    ["Create or edit a DQ dictionary", "YES", "NO", "REST ONLY. Full CRUD on the dqcloud-api host"],
    ["Verify / standardize an address", "YES", "YES", "Both. REST does 1,000 per call; MCP does one"],
    ["Run a mapping task", "YES", "YES", "Both"],
    ["Check job status", "YES", "YES", "Both. REST gives full history"],
    ["Stop a running job", "YES", "YES", "Both"],
    ["Create a connection", "YES", "NO", "REST ONLY. Verified create-then-delete"],
    ["Create or schedule a mapping task", "YES", "NO", "REST ONLY"],
    ["Suspend / resume / terminate a process", "YES", "NO", "REST ONLY, on the CAI restadmin plane"],
    ["Publish a CAI process", "YES", "NO", "REST ONLY. Bulk, up to 199 assets"],
    ["Invoke a CAI process", "YES", "NO", "REST ONLY. Any of the five verbs, or anonymous"],
    ["Ingest an MDM source record", "YES", "NO", "REST ONLY"],
    ["Fuzzy-match a customer identity", "NO", "YES", "MCP ONLY. No REST search resource on the probed org"],
    ["Read an MDM golden record", "DISPUTED", "YES", "MCP is the safer path while the REST GET stays contested"],
    ["List marketplace collections", "YES", "YES", "Both"],
    ["Raise a data access request", "YES", "YES", "Both"],
    ["Create a marketplace delivery target", "YES", "NO", "REST ONLY"],
    ["Author a mapping / transform logic", "NO", "NO", "NEITHER. Designer canvas"],
    ["Accept a CLAIRE classification", "NO", "NO", "NEITHER. No Accept control exists at all"],
    ["Author a business-glossary term", "NO", "NO", "NEITHER. The route is not mounted"],
    ["Assign a steward or data owner", "NO", "NO", "NEITHER"],
    ["Deploy an MDM business entity", "NO", "NO", "NEITHER. B360 Modeler"],
    ["Author a mass-ingestion task", "NO", "NO", "NEITHER. Wizard"],
    ["Create a DAM masking policy", "NO", "NO", "NEITHER on this org"],
    ["Publish a taskflow", "NO", "NO", "NEITHER. Unresolved: one report says otherwise"],
]

# The structural difference, as a table
API_VS_MCP_SHAPE = [
    ["Number of endpoints", "Hundreds, one per resource", "ONE per server (5 servers)"],
    ["HTTP verbs you choose", "GET, POST, PUT, PATCH, DELETE", "None. Always POST"],
    ["How intent is expressed", "The verb plus the URL path", "A named action in the JSON-RPC body"],
    ["Transport", "Plain REST over HTTPS", "MCP protocol 2025-06-18, streamable HTTP"],
    ["Auth", "6 planes, plane-specific headers", "IDS-SESSION-ID, Bearer JWT, or OAuth2"],
    ["Request shape", "Service-specific JSON per endpoint", "Uniform: tool name plus typed arguments"],
    ["Discovery", "Read the documentation", "tools/list returns the schema at runtime"],
    ["Total operations", "~250 probed; hundreds documented", "11 actions across 5 servers"],
    ["Can it write?", "Yes, on many resources", "One action (checkout_data_order)"],
    ["Can it author a design asset?", "No", "No"],
    ["Billing", "IPUs per service rate card", "The same IPUs. MCP itself is not metered in preview"],
    ["Error surface", "Full HTTP status vocabulary", "Tool-level isError plus a text payload"],
]
