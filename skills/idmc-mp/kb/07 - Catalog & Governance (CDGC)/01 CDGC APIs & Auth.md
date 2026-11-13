# CDGC APIs & Auth

**Answers:** Which host serves which CDGC route? How do I get the three identity headers (JWT, session, org id)? Which
route does which catalog job? What does a CDGC status code mean? How do I prove the org has CDGC?

**Read when:** starting any catalog, glossary, lineage or Marketplace work headless; a data360 or ccgf call returns 401,
404, 406, 415 or a zero-byte 200; someone says "CDGC is not entitled".

**Key rules:**
- Send all three headers on every call: `Authorization: Bearer <cdlg_app JWT>`, `IDS-SESSION-ID`, `X-INFA-ORG-ID`; the
  JWT lives 30 minutes from grant, so cache it about 20 minutes and re-mint on any 401 (L-CDGC-001, L-CDGC-002).
- `data360/*` routes live on `idmc-api.<domain>`, `ccgf-*` routes on `cdgc-api.<domain>`; a 404 on the pod host is a
  wrong-host result, not a wall (L-CDGC-005).
- Probe a bogus twin next to every verdict: data360 can answer a zero-byte or identical 200 for nonsense paths
  (L-CDGC-006).
- Decide entitlement from runtime-environment services, agent engines, privileges and a real call, never from
  `products[]` or a 404; an empty catalog is unpopulated, not unentitled (L-CDGC-007).
- Governance is org-scoped: every runtime environment of an org shares one catalog, glossary, classification set and DQ
  rule set (L-CDGC-009).
- Read back after every write: 207 items, echo-only 200s and silent no-ops happen on this plane (L-CDGC-065,
  L-CDGC-098).

**Related:** [02 Catalog Sources](<02 Catalog Sources - Create, Scan, Update, Purge.md>) ·
[04 Search, Lineage & Marketplace](<04 Search, Lineage & Marketplace.md>) ·
[05 CDGC Gaps & Gotchas](<05 CDGC Gaps & Gotchas.md>) ·
[Access, Auth & Orgs](<../01 - Access, Auth & Orgs/>) · [Lessons: CDGC](<../13 - Lessons Learned/07 Catalog & Governance (CDGC).md>)

**Last verified:** 2026-11-03

> **Summary.** Cloud Data Governance & Catalog (CDGC, with Metadata Command Center and Data Marketplace) is driven over
> two API hosts per domain: `idmc-api.<domain>` for the `data360/*` routes (search, content, scans, jobs, Marketplace) and
> `cdgc-api.<domain>` for the `ccgf-*` routes (catalog-source management, the contentv2 write plane, searchv2) and
> Marketplace provisioning. Almost everything a UI user does in CDGC is headless; the remaining walls are listed in
> [05 CDGC Gaps & Gotchas](<05 CDGC Gaps & Gotchas.md>). No vendor CDGC REST guide was available, so every route here is
> probe-derived. Machine-readable route lists: [15-cdgc.json](<../12 - Reference Library/IDMC API & MCP Reference/content/15-cdgc.json>),
> [19-marketplace.json](<../12 - Reference Library/IDMC API & MCP Reference/content/19-marketplace.json>).

Placeholders: `<domain>` = the regional label of your login host (`dm-us`, `dm-em`,...); `<pod>` = the pod label of your
login base URL (for example `usw3` or `emw1`);
`<orgIdV3>` = the 22-character org id; `<sessionId>` = your login session id; `<reId>`, `<connId>`, `<catalogSourceId>`,
`<jobId>`, `<identity>` (an asset's internal UUID), `<externalId>`.

---

## 1. The planes at a glance

| Host | Path prefixes | Serves | Evidence |
|---|---|---|---|
| `https://<domain>.informaticacloud.com` | `/identity-service/api/v1/Login`, `/identity-service/api/v1/jwt/Token` | Identity: session and the CDGC JWT | proven |
| `https://idmc-api.<domain>.informaticacloud.com` | `/data360/search/api/v1/search`, `/data360/search/v1/assets[/<id>]`, `/data360/content/v1/assets[/<id>]`, `/data360/executable/v1/...`, `/data360/observable/...`, `/data360/catalog-source-management/v1/...`, `/data360/marketplace/api/v1\|v2/...` | Search, asset reads, glossary and content writes, scan runs, job polling, Marketplace | proven |
| `https://cdgc-api.<domain>.informaticacloud.com` | `/ccgf-catalog-source-management/api/v1/datasources...`, `/ccgf-contentv2/api/v1/publish`, `/ccgf-searchv2/api/v1/search`, `/cdmp-marketplace/api/v1/provisioning/*` | Catalog-source create/update/purge, the 207 write plane, searchv2, Marketplace provisioning reads | proven |
| `https://cdgc-api.<domain>.informaticacloud.com` (orchestration) | `/ccgf-orchestration-management-api-server/api/v1/jobs?metadataOnly=false&offset=<n>&limit=60` (oldest first), `.../jobs/<jobId>/operations/cancel` | Catalog job list and cancel (L-CDGC-223, L-CDGC-225) | proven 2026-10-26 (console capture and script replay) |
| `https://ccgf-api.<domain>.informaticacloud.com` | `/ccgf-orchestration-management-api-server/api/v1/management/job` | Classification Promotion job (seen from a browser session once) | observed once, disputed |
| `https://cdmp-app.<domain>.informaticacloud.com/` | UI | The Marketplace app (SSO after login) | observed |
| `<pod>-cdgc.<domain>.informaticacloud.com` | none | Does not resolve (no DNS) | probed |
| `https://<pod>.<domain>.informaticacloud.com` | platform v2/v3 | Does **not** serve data360: a 404 there is a wrong-host result | probed |

Notes:
- Some routes answered on both API hosts: the scan run on `cdgc-api` as well as `idmc-api`, Marketplace `dataAssets`
  on `cdgc-api`, and helper code on one org called `ccgf-catalog-source-management` on its `idmc-api` base. Prefer the
  host in the table (L-CDGC-005).
- The `data360/catalog-source-management/v1/*` prefix is not reliably routed on every org; use the ccgf plane for writes
  (L-CDGC-019).
- The v3 object catalog (`/public/core/v3/objects`) is read-only for catalog content (`POST` = 405). CDGC authoring goes
  through the ccgf and data360 routes, never through v3 objects (L-CDGC-071).

---

## 2. Credentials: from login to the three headers

### 2.1 Log in once

Use the org's login host (`https://<domain>.informaticacloud.com`), never the pod host, and one cached session shared by all
scripts. Either of these gives what CDGC needs:
- the v3 login `POST https://<domain>.informaticacloud.com/saas/public/core/v3/login` with `{"username":"<user>","password":"<pw>"}`
  returns `userInfo.sessionId` and `userInfo.orgId` (the 22-character id for `X-INFA-ORG-ID`);
- the identity-service login `POST https://<domain>.informaticacloud.com/identity-service/api/v1/Login` returns `sessionId`
  and `orgId` (plus roles and `effectivePrivileges`).

Login mechanics, lockout guards and session lifetimes belong to [Access, Auth & Orgs](<../01 - Access, Auth & Orgs/>).
A few rejected logins lock the account, so stop after the first rejection.

### 2.2 Mint the CDGC JWT (L-CDGC-001)

```
POST https://<domain>.informaticacloud.com/identity-service/api/v1/jwt/Token?client_id=cdlg_app&nonce=<random>&access_code=
IDS-SESSION-ID: <sessionId>
Cookie: USER_SESSION=<sessionId>
(empty body)

200 {"jwt_token": "<about 2,100 characters>"}
```

- The JWT lives **30 minutes from grant**; the identity session lasts hours. Cache the JWT about 20 minutes and re-mint
  on any 401.
- A GET form (`...jwt/Token?client_id=<id>&nonce=<uuid>` with `IDS-SESSION-ID`) is also recorded.
- `client_id=cdlg_app` is the value used for CDGC and MDM search; `client_id=idmc_api` is the one used for the managed MCP
  servers (see [CLAIRE & MCP](<../09 - CLAIRE & MCP/>)).
- Platform direction (documented by the vendor, not exercised): session-ID REST authentication is deprecated and JWT
  becomes the default after the October 2026 release; plan every session-header client for Bearer JWT
  (L-AUTH-033, [Access, Auth & Orgs](<../01 - Access, Auth & Orgs/>)).

### 2.3 Alternative: JWT-on-login (L-CDGC-004)

If Administrator > Authentication sets the org's authentication type to JWT, the v3 login `userInfo.sessionId` is itself a
JWT (starts with `ey`, about 1,700 characters). CDGC accepted it directly as the Bearer (with the same value in
`IDS-SESSION-ID`) for reads and for content/publish writes. Changing the org's auth type can break other session-id
clients, so do not flip it on a shared org without the owner.

### 2.4 The header contract (L-CDGC-002)

| Header | Value | Needed for | Symptom when missing |
|---|---|---|---|
| `Authorization` | `Bearer <jwt>` | every call | 401 |
| `IDS-SESSION-ID` | `<sessionId>` | runs, creates, updates (GETs sometimes tolerate its absence) | 500 ccgf-auth-pep "Login sessionID is missing" (or 406) on a scan run; runtime-environment validation failure on catalog-source create |
| `X-INFA-ORG-ID` | `<orgIdV3>` | every data360 call | 401 / 500 as above |
| `X-INFA-SEARCH-LANGUAGE` | `elasticsearch` | `data360/search/api/v1/search`, `ccgf-searchv2` | search does not parse the DSL body |
| `Content-Type` / `Accept` | `application/json` (multipart for catalog-source create/update) | writes | 415 on catalog-source create with JSON |
| `X-INFA-PRODUCT-ID` | `CDGC` | the `ccgf-contentv2/api/v1/publish` of a DQ rule occurrence (L-CDGC-161); an earlier relationship capture sent any value | 500 'Required request header X-INFA-PRODUCT-ID' on the rule-occurrence publish |

A helper that sends only the v3 `INFA-SESSION-ID` gets 401 on data360 (L-CDGC-003). Route every CDGC call
through one helper that owns the JWT cache.

### 2.5 A minimal helper (standard library only)

```python
import json, time, urllib.request, urllib.error

DOMAIN = "dm-us"                                             # read it from your login host; dm-us vs dmp-us matters
LOGIN  = f"https://{DOMAIN}.informaticacloud.com"
API    = f"https://idmc-api.{DOMAIN}.informaticacloud.com"   # data360/*
CDGC   = f"https://cdgc-api.{DOMAIN}.informaticacloud.com"   # ccgf-*, cdmp-marketplace
SID, ORG = "<sessionId>", "<orgIdV3>"                        # from the login response, never hard-coded in a repo

_jwt = {"t": 0.0, "v": None}
def jwt:
    if not _jwt["v"] or time.time - _jwt["t"] > 20 * 60:   # the JWT lives 30 min from grant
        url = f"{LOGIN}/identity-service/api/v1/jwt/Token?client_id=cdlg_app&nonce=n{int(time.time)}&access_code="
        req = urllib.request.Request(url, data=b"", method="POST", headers={
            "IDS-SESSION-ID": SID, "Cookie": "USER_SESSION=" + SID, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            _jwt["v"], _jwt["t"] = json.loads(r.read)["jwt_token"], time.time
    return _jwt["v"]

def headers(search=False):
    h = {"Authorization": "Bearer " + jwt, "IDS-SESSION-ID": SID, "X-INFA-ORG-ID": ORG,
         "Content-Type": "application/json", "Accept": "application/json"}
    if search:
        h["X-INFA-SEARCH-LANGUAGE"] = "elasticsearch"
    return h

def call(method, url, body=None, search=False):
    """Returns (status, json-or-text). Never raises on 4xx/5xx: callers must check the status."""
    data = None if body is None else json.dumps(body).encode
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=data, method=method,
                                                           headers=headers(search)), timeout=90) as r:
            t = r.read
            return r.status, (json.loads(t) if t else None)
    except urllib.error.HTTPError as e:
        if e.code == 401:
            _jwt["v"] = None                                  # re-mint on the next call
        return e.code, e.read[:1500].decode(errors="replace")
```

The multipart variant for catalog-source create and update is in
[02 Catalog Sources](<02 Catalog Sources - Create, Scan, Update, Purge.md>) section 3.4. The pacing wrapper for long walks
(429 handling) is in [04 Search, Lineage & Marketplace](<04 Search, Lineage & Marketplace.md>) section 4.

---

## 3. Which route for which job

| Job | Verb and path | Host | Notes | Doc |
|---|---|---|---|---|
| Mint the JWT | `POST /identity-service/api/v1/jwt/Token?client_id=cdlg_app&nonce=<n>&access_code=` | `<domain>` | `IDS-SESSION-ID` + `Cookie: USER_SESSION` | 01 |
| List source types | `GET /ccgf-catalog-source-management/api/v1/datasourceTypes?offset=0&limit=200` | cdgc-api | the data360 `catalogsourcetypes` 404s | 02 |
| Read a type's option schema | `GET /ccgf-catalog-source-management/api/v1/type/<Type>/capability/<Capability, URL-encoded>/configuration` | cdgc-api | option groups with name, dataType, required, defaultValue, staticValues, conditions (L-CDGC-016); 404 'capability configuration does not exist' = the type does not offer it, 400 'invalid type or capability' = a bogus name (L-CDGC-234) | 02 |
| List sources | `GET /ccgf-catalog-source-management/api/v1/datasources?offset=0&limit=100` | cdgc-api | `datasources[]`; keep your own name-to-id map | 02 |
| Read a source | `GET.../datasources/<id>` | cdgc-api | the before-state backup | 02 |
| Create a source | `POST.../datasources` (no trailing slash), multipart part `dataSource` | cdgc-api | `custom` and `endOfLife` required | 02 |
| Update a source | `PUT.../datasources/<id>`, multipart part `dataSource` | cdgc-api | repeat `id` in the JSON part (400 without it, L-CDGC-163); PATCH as fallback | 02 |
| Purge a source | `DELETE.../datasources/<id>` | cdgc-api | purges metadata; the definition stays (UI delete) | 02 |
| Run a scan | `POST /data360/executable/v1/catalogsource/<id>` `{"capabilityNames":[...]}` | idmc-api | 201 + `jobId`; IPU-metered | 02 |
| Poll one job | `GET /data360/observable/v1/jobs/<jobId>?expandChildren=TASK-HIERARCHY` | idmc-api | status + `tasks[]` | 02 |
| List jobs | `GET /data360/observable/api/v1/jobs?limit=N` | idmc-api | the `/api/` infix is required here | 02 |
| List jobs (orchestration view) | `GET /ccgf-orchestration-management-api-server/api/v1/jobs?metadataOnly=false&offset=<total-60>&limit=60` | cdgc-api | oldest first, so start at total-60 (L-CDGC-223) | 02 |
| List executables | `GET /data360/executable/v1/executables?type=<type>` | idmc-api | 200; type values not recorded | 02 |
| Search (Elasticsearch DSL) | `POST /data360/search/api/v1/search` | idmc-api | + `X-INFA-SEARCH-LANGUAGE: elasticsearch` | 04 |
| Search (knowledge query) | `POST /data360/search/v1/assets?knowledgeQuery=<q>&segments=all` body `{"from":0,"size":N}` | idmc-api | `hits[]` with summary and systemAttributes | 04 |
| Read one asset | `GET /data360/search/v1/assets/<identity>?scheme=internal&segments=<list>` | idmc-api | `scheme=external` for slash-free ids | 04 |
| Create a domain or term | `POST /data360/content/v1/assets` | idmc-api | `core.classType` Domain / BusinessTerm | 03 |
| Rename, describe, link, classify | `PATCH /data360/content/v1/assets/<identity>?scheme=internal` (or `<externalId>?scheme=external`) | idmc-api | operations array on segments `summary`, `glossary`, `dataClassification`; a technical asset takes `core.description` alone (L-CDGC-164) | 03 |
| Delete a domain or term | `DELETE /data360/content/v1/assets/<identity>?scheme=internal` | idmc-api | verify by search | 03 |
| Publish relationships / curation status | `POST /ccgf-contentv2/api/v1/publish` | cdgc-api | 207 Multi-Status; read each item | 03 |
| Create a DQ rule occurrence | `POST /ccgf-contentv2/api/v1/publish` (+ `X-INFA-PRODUCT-ID: CDGC`), then `POST /ccgf-ruleautomation/api/v1/dataQuality/sync` | cdgc-api | 207 with a 201 per item, then PASSED (L-CDGC-161) | [DQ Scorecards](<../06 - Data Quality & Profiling/04 DQ Scorecards (warehouse pattern and Data Profiling scorecards).md>) §4 |
| Assign a connection reference (lineage stitch) | `POST /ccgf-contentv2/api/v1/assignment/connectionAssignment?operationType=MERGE` (`SPLIT` undoes) | cdgc-api | a job id; it completes even for a bogus reference, so read a target table's lineage back (L-CDGC-159) | 04 |
| Classification Promotion | `POST /ccgf-orchestration-management-api-server/api/v1/management/job` | ccgf-api | seen once from a browser; disputed | 03 |
| searchv2 | `POST /ccgf-searchv2/api/v1/search` | cdgc-api | subset of ES query types | 04 |
| Marketplace objects | `/data360/marketplace/api/v1/{dataAssets,dataCollections,categories,termsOfUse,orders}`, `/api/v2/{data-collections,delivery-targets,orders}` | idmc-api | producer side is REST | 04 |
| Marketplace provisioning reads | `GET /cdmp-marketplace/api/v1/provisioning/{deliveryTemplates,deliveryFormats,deliveryMethods}` | cdgc-api | ids for targets and orders | 04 |
| Lineage hops (proven 2026-10-08) | `GET /data360/search/v1/assets/<identity>?scheme=internal&segments=all` (the `lineage` and neighborhood segments) | idmc-api | one hop per read; the `/data360/lineage/*` graph routes are not served; MCP `get_asset_details` also reads lineage | 04 |
| Curated lineage edges (proven 2026-10-08) | `POST /ccgf-contentv2/api/v1/publish` (+ `X-INFA-PRODUCT-ID: CDGC`) with RELATIONSHIP items `core.DataSetDataFlow` / `core.DirectionalDataFlow` | cdgc-api | 207; DELETE items undo | 04 |
| Cancel a scan | `POST /ccgf-orchestration-management-api-server/api/v1/jobs/<jobId>/operations/cancel` (empty body) | cdgc-api | 200, then CANCEL_REQUESTED; poll for CANCELLED before the next run (1-2 min in Test Connection, 50+ min once extraction runs). Proven from the console and a script, 2026-10-26 (L-CDGC-221, L-CDGC-225) | 02 |

---

## 4. Status and error triage for CDGC

| You see | Where | Meaning | Do | Lesson |
|---|---|---|---|---|
| 401 | any data360/ccgf call | JWT expired, or only the v3 session header was sent | re-mint; send all three headers | L-CDGC-002, L-CDGC-003 |
| 500 `Login sessionID is missing` (ccgf-auth-pep), sometimes 406 | scan run | missing `IDS-SESSION-ID` / `X-INFA-ORG-ID` | three headers | L-CDGC-034 |
| 500 `no capability is being chosen` | scan run | empty `capabilityNames` | list the capabilities | L-CDGC-034 |
| 400 `Failed to read request` | scan run | wrong body shape | `{"capabilityNames":[...]}` | L-CDGC-034 |
| 406 `Job is in progress` | scan run | a job of that source is active (or stuck) | wait, or cancel it over REST (`.../jobs/<jobId>/operations/cancel`) and poll for CANCELLED | L-CDGC-221, L-CDGC-225 (L-CDGC-040, superseded) |
| 400 `Job is in progress... cancel current job` | source DELETE | a stuck job holds the lock | cancel it over REST or in MCC, then delete | L-CDGC-221, L-CDGC-225 (L-CDGC-040, superseded) |
| 415 | source create | JSON body | multipart part `dataSource` | L-CDGC-014 |
| 500 `Custom flag cannot be null` | source create | `custom` / `endOfLife` missing | add both | L-CDGC-014 |
| 404 | `POST.../datasources/` | trailing slash | drop it | L-CDGC-014 |
| 500 `Error while validating Runtime Environment detail [...]` | source create | missing `IDS-SESSION-ID`, or the RE is not ready | send headers, then check the RE | L-CDGC-022 |
| 400 | GET/PATCH `.../assets/<externalId>` with slashes | encoded slashes in the path | resolve the identity by search | L-CDGC-057 |
| 500 | search | unknown field name | exact names (`core.profiled`) | L-CDGC-076 |
| 400 | search with a `match` or `match_phrase` query | query type not accepted | `term`, `bool`, `wildcard` or `exists`; compare names client-side | L-CDGC-165 |
| 400 `dataSource id in request path and body do not match` | source PUT | the JSON part omits `id` | set `id` to the path id; PUT; read back | L-CDGC-163 |
| 400 `Asset name update not supported for technical assets` | PATCH `summary` on a table, view or column | the patch also carries `core.name` | `core.description` alone | L-CDGC-164 |
| 500 `Required request header X-INFA-PRODUCT-ID` | `ccgf-contentv2/api/v1/publish` of a rule occurrence | the header is missing | `X-INFA-PRODUCT-ID: CDGC` | L-CDGC-161 |
| enum-conversion error | `connectionAssignment?operationType=ASSIGN` (or `UNASSIGN`, `ACCEPT`, `CREATE`) | not a value of the enum | `MERGE`; `SPLIT` to undo | L-CDGC-159 |
| 400 `MissingServletRequestParameter` | `POST /data360/search/v1/assets` | no `knowledgeQuery` parameter | add `knowledgeQuery` and `segments`, or use `search/api/v1/search` | L-CDGC-074 |
| 405 | GET on search or scan-run paths | POST-only by design | POST | L-CDGC-034, L-CDGC-073 |
| 429 | asset and search walks; bursts of description PATCHes | rate limit | pace and back off | L-CDGC-013, L-CDGC-164 |
| 200 with `Content-Length: 0`, or identical to a bogus twin | data360 on some orgs | gateway artifact | bogus-twin; no verdict | L-CDGC-006 |
| 404 on `/data360/*` at the pod host | platform host | wrong host | `idmc-api` / `cdgc-api` | L-CDGC-005 |
| empty-body 404 identical to the twin on `data360/catalog-source-management` | some orgs | prefix not routed | use the ccgf plane | L-CDGC-019 |
| 207 with `items: []` | `ccgf-contentv2/api/v1/publish` | nothing applied (silent no-op) | read back; use content PATCH | L-CDGC-065 |
| 200 whose change is gone on re-GET | e.g. `PUT /dataCollections/<id>` with stakeholders | echo-only false green | re-GET after every write | L-CDGC-098 |
| 400 `MigrationSvc_034 Object resolution failed` | v3 export of a catalog asset | CDGC is not exportable | rebuild through the APIs | L-CDGC-071 |
| Metadata Extraction PARTIAL_COMPLETED, "Total objects processed count N is the same as objects count with errors" | scan job | the scanner's report could not be written (a second agent OS user and a shared `/tmp/poifiles` at 755) | `chmod 1777 /tmp/poifiles` | L-CDGC-150 |
| Snowflake Metadata Extraction PARTIAL_COMPLETED, no message in the job tree | scan job | the role cannot read tags ('Unable to resolve TAGS objects from SNOWFLAKE' in the agent's Sync log); every table and view was extracted | read the scanner log before treating it as a failure | L-CDGC-168 |
| Data Quality: Rule Generation COMPLETED, Rule Profiling FAILED in 0 s, no error text | scan job | no runtime environment in the source's typeCapabilities Scope groups | add it, PUT, rerun | L-CDGC-143 |
| Data Quality PARTIAL_COMPLETED, no message, one rule occurrence never scored | scan job | a decimal-input rule bound to a text column | bind a typed view column | L-CDGC-170 |
| Lookups by name miss at random; full reads of one source differ in count | search paged with `from`/`size` | unsorted pages overlap | `"sort": [{"core.identity": {"order": "asc"}}]`, filter `core.origin` + `elementType` OBJECT | L-CDGC-169 |
| 200 `[]` from `GET /api/v2/connection/source/<connId>` | v2 platform | proves nothing (seen for a known-good connection) | judge table visibility by Metadata Extraction | L-CDGC-150 |

---

## 5. Entitlement, readiness and roles

**Decide entitlement from ground truth, never from `products[]` or a 404** (L-CDGC-007). In order:

1. Runtime environment services: `GET https://<pod>.<domain>.informaticacloud.com/runtime/api/v2/runtimeEnvironment/<reId>/selections/ui`
   with `IDS-SESSION-ID`; look for `Data Governance and Catalog` enabled:true.
2. Agent engines: `GET /api/v2/agent/details/<agentId>` (v2 session); `Metadata_Platform_Service` and
   `Metadata_Foundation_Agent` RUNNING (plus DIS and Connector_Service).
3. Privileges and roles from the identity-service Login: `create.mcp.CatalogSourceConfiguration`,
   `execute.mcp.CatalogSourceConfiguration`, `create.PROFILE`, Governance Owner / Governance Administrator.
4. A real call: `GET.../ccgf-catalog-source-management/api/v1/datasources` with a real JSON body, a search that returns
   hits, or a catalog-source create that validates.
5. An empty catalog is **unpopulated**, not unentitled: scan a source and search again.

**Governance is org-scoped** (L-CDGC-009): two runtime environments in one org share one catalog, glossary,
classification set and DQ rule set. Only RE-bound objects and the warehouse each catalog source targets differ. Isolation
needs a second org.

**Roles for one working login** (L-CDGC-008): Admin, Designer, Governance Administrator and CLAIRE GPT User.
Populate the governance roles (Data Owner, Data Steward) in Administrator before anyone assigns stakeholders in the UI.

---

## 6. Probing discipline for CDGC

- **Probe-derived only.** No vendor CDGC REST guide was held; record host, header set, verb, status and date for every
  verdict and re-probe when the build changes (L-CDGC-010).
- **Host and infix first.** `/data360/marketplace/v1/...` (no `/api/`) and data360 paths on the pod host 404'd while the
  real routes worked (L-CDGC-137 superseded). Sweep `idmc-api`, `cdgc-api` and `ccgf-api` before calling a
  wall.
- **Bogus twins.** On some orgs data360 fake-200s (zero bytes, or byte-identical for nonsense paths). Probe a nonsense
  sibling next to every real path and assert on body shape (L-CDGC-006).
- **405 vs 404.** A 405, 415, 400 on an empty body, or a typed 500 proves a live handler; a uniform empty 404 across many
  shapes means no route.
- **Read back.** 207 items, echo-only 200s and silent no-ops happen on this plane. Re-GET or search after every write.
- **INFACore** is a client SDK; its "service" 404 is expected and means nothing (L-CDGC-011).
- **Pace.** Sequential calls with backoff on 429 (L-CDGC-013).

---

## 7. Apps and UI surfaces

| Surface | What it is for | Notes |
|---|---|---|
| Metadata Command Center (MCC) | Register, configure, run and monitor catalog sources; Configure > Lineage (connection assignment, also headless: L-CDGC-159); Associations > Stakeholders | Cancel a running scan and delete a source definition only here |
| Data Governance and Catalog (DGC) | Search and browse assets; Lineage, Data Quality, Relationships, Contains tabs; glossary and classifications | Customize/admin pages show "nothing to display" even when the catalog is full (L-CDGC-012) |
| CDGC UI search | Keyword and AI (Query) search | AI Query can return 0 org-wide; Keyword works (`cgsearch/<id>?query=<term>&type=Keyword`) (L-CDGC-080) |
| Data Marketplace app (`cdmp-app.<domain>`) | Consumer and producer UI | Delivery templates are created only here (L-CDGC-096) |
| Asset Score tab (`cdgc.<domain>/asset/<id>`) | DQ rule-occurrence scores | Headless: the asset's `dataQuality` segment returns the per-dimension DQResult objects; occurrences are RuleInstance assets (L-CDGC-144) |

---

## 8. MCP coverage (summary)

- **CDGC Metadata Search** server: `search_metadata` (natural language) and `get_asset_details` (`id`, `scheme`), which
  returns lineage, profile and descriptions (L-CDGC-100). It is no longer the only programmatic lineage read: REST reads the same hops from the asset read's `lineage` segment (L-CDGC-181, which supersedes L-CDGC-085).
- **Data Provisioning** server: `list_data_collections`, `list_delivery_targets`, `checkout_data_order` (L-CDGC-099).
- The org's managed registry also lists `cdgccatalogdiscovery`, `cdgcsearchmetadata`, `cdgcdataqualityscore` and
  `cdgccatalogenrichment` (glossary and classification write tools, not exercised here).
- MCP is a calling convention over the same service APIs: it does not widen the write surface, and backing calls still
  bill. Details and authentication: [CLAIRE & MCP](<../09 - CLAIRE & MCP/>).

---

## Lessons cited in this doc

L-CDGC-001 JWT mint · L-CDGC-002 three headers · L-CDGC-003 v3-only helper 401 · L-CDGC-004 JWT-on-login ·
L-CDGC-005 host map · L-CDGC-006 zero-byte 200s · L-CDGC-007 entitlement truth · L-CDGC-008 roles ·
L-CDGC-009 org-scoped governance · L-CDGC-010 probe-derived routes · L-CDGC-011 INFACore · L-CDGC-012 MCC vs DGC ·
L-CDGC-013 rate limits · L-CDGC-019 data360 catalog-source prefix · L-CDGC-071 v3 read-only for CDGC ·
L-CDGC-080 Keyword search · L-CDGC-099/100 MCP · L-CDGC-143/144 catalog DQ · L-CDGC-159 connection assignment ·
L-CDGC-161 rule-occurrence publish · L-CDGC-163 PUT id · L-CDGC-164 technical-asset descriptions · L-CDGC-165 search
query types · L-CDGC-168 Snowflake tags partial · L-CDGC-169 sorted search paging · L-CDGC-170 typed rule binding. Full text: [Lessons: CDGC](<../13 - Lessons Learned/07 Catalog & Governance (CDGC).md>).
