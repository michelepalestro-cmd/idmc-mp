# Metering and consumption exports

**Answers:** How do I read IPU consumption headless? Which export job types and windows work, and what do the errors
mean? What do the CSV columns hold? What does the Administrator Metering page read, and is its '10,000' the job cap?
How do I estimate usage when billed IPU reads 0, and what does an activity-log row carry?

**Read when:** reporting or reconciling IPU consumption; a metering export fails; billed IPU reads 0; building a usage
proxy or a job count from the activity log.

**Key rules:**
- Read billed consumption with the async `ExportMeteringData` job (201, poll, download); the summary GETs return 404
  even where it works (L-IPU-021, L-IPU-022).
- Keep `PROJECT_FOLDER` (and plan `ASSET` the same way) windows at 30 days or less, or the export answers 400
  `LS_298`; `SUMMARY` accepts longer windows (L-IPU-021).
- Trial and embedded sub-orgs export a header-only CSV: estimate with a labelled proxy from the activity log
  (L-IPU-023, L-IPU-024).
- Activity-log rows carry no `runtimeEnvironmentId` and no `agentId`; attribute through `entries[].agentId`, and count
  jobs as task rows plus taskflow rows plus their children (L-IPU-024).
- The Metering page's serverless compute-unit meters are not the monthly job cap (L-IPU-056, L-IPU-041).
- A meter that could not read reports 0: treat zero or unsampled as unknown (L-IPU-025).

**Related:** [01 IPU Model (mechanics)](01-ipu-model-mechanics.md) · [03 Entitlement, Licenses & Job Caps](03-entitlement-licenses-job-caps.md) · [Login, Sessions & Tokens](../01-login-and-orgs/02-login-sessions-tokens.md) · [IDMC API & MCP Reference: admin and core](../reference/idmc-api-mcp-reference/content/10-admin-core.json) · [Lessons: IPU, Metering & Licensing](lessons.md)

**Last verified:** 2026-11-03

> IPU consumption is readable headless through one asynchronous job that returns a ZIP of CSVs. Trial and embedded
> sub-orgs accrue zero billed IPU while jobs run, so estimate with a clearly labelled proxy from the activity log. The
> Administrator console adds the Metering page (its own services, section 1.1) and CSV exports (agents, licences, CAI
> connections, unique connector endpoints) that REST does not offer.

---

## 1. What can be read, and how

| Need | Route or place | State |
|---|---|---|
| Billed consumption by meter and day | `POST /public/core/v3/license/metering/ExportMeteringData` -> poll -> download | Proven headless (L-IPU-021) |
| Summary reads | `GET.../metering/MeteringUsageSummary`, `AssetUsageSummary`, `/metering/summary`, `/consumption-summary` | 404 'No static resource' (L-IPU-022) |
| Per-run duration and rows (estimates) | `GET /api/v2/activity/activityLog` | Proven; retention is short (days) |
| Usage dashboard, threshold alerts | Administrator Metering console | UI (documented) |
| Agent, licence, CAI connection, endpoint inventories | Administrator CSV exports | UI (L-IPU-028) |
| Licence list | none over REST; Administrator > Licenses | See [doc 03](03-entitlement-licenses-job-caps.md) |
| Meter allocations and usage (the Metering page) | license-service `metering/org/('<orgIdV3>')/instances`, metering-service `queryAggregatedMeterData` | Captured from the page with a browser session (section 1.1) |
| Base edition (trial or not) | license-service `OrgLicenseAssignment('<orgIdV3>')/Views` | Read with a browser session (section 1.1) |
| Job cap | none | Not readable anywhere (L-IPU-041) |

### 1.1 The Metering page's own services

The Administrator Metering page reads two services on the pod host (L-IPU-056). These calls were captured
from the page's own requests with the browser session (cookies plus the XSRF header); the same calls with a REST
session header are untested.

```
GET  https://<pod>.<domain>.informaticacloud.com/license-service/api/v1/metering/org/('<orgIdV3>')/instances?aggregatedMeterOnly=true
     -> each meter with strMaxValue and strUsed

POST https://<pod>.<domain>.informaticacloud.com/metering-service/api/v1/metering/org/('<orgIdV3>')/queryAggregatedMeterData
     {"orgId":"<orgIdV3>","meterId":"<meterId>","dataGranularity":["ALL"],"startTime":"<iso>","endTime":"<iso>"}
     -> allocation, remaining and daily average

GET  https://<pod>.<domain>.informaticacloud.com/license-service/api/v1/OrgLicenseAssignment('<orgIdV3>')/Views
     -> the base edition by name (for example 'Intelligent Data Management Cloud Trial', plus MDM and governance trials)
```

On a trial org the page showed one service, 'Org Consumption', with three meters at a maximum of 10,000 and 0 used
(Data Integration with Advanced Serverless, Advanced Data Integration, Advanced DI with Advanced Serverless). These are
serverless compute-unit meters: Secure Agent jobs do not draw from them, so a '10,000' there says nothing about the
monthly job limit (L-IPU-041). `Views` identifies a trial org before you plan job volumes, while its
`EffectiveLicenses` limits still read -1 (L-AUTH-072).

## 2. The export job

(L-IPU-021.) All on the pod base `<serverUrl>` (`https://<pod>.<domain>.informaticacloud.com/saas`) with
header `INFA-SESSION-ID: <v3 session>`.

```
POST <serverUrl>/public/core/v3/license/metering/ExportMeteringData
Content-Type: application/json
{"jobType": "SUMMARY", "startDate": "2026-06-01T00:00:00Z", "endDate": "2026-07-26T00:00:00Z"}
-> 201 {"jobId": "<id>",...}

GET  <serverUrl>/public/core/v3/license/metering/ExportMeteringData/<jobId>     # poll every ~20 s until SUCCESS (3-5 min)
     (also recorded as GET.../license/metering/jobs/<jobId>; try the first, then the second)
GET  <serverUrl>/public/core/v3/license/metering/ExportMeteringData/<jobId>/download
     (the jobs form is recorded as.../license/metering/jobs/<jobId>/download)
-> a ZIP with one CSV per org (read the body as bytes)
```

| Detail | Value |
|---|---|
| `jobType` | `SUMMARY`, `ASSET`, `PROJECT_FOLDER` |
| Dates | Full ISO-8601 with a zone. A bare `2026-06-01` gives 400 `V3API_007`; `jobType` alone gives 400 `LS_147` |
| Window | `SUMMARY`: 33 and 90 days worked. `PROJECT_FOLDER`: at most 30 days, or 400 `LS_298` and no job; plan `ASSET` the same way (L-IPU-021) |
| Cost | The export and its reads cost 0 IPU and need no extra entitlement |
| CSV columns | `OrgId,MeterId,MeterName,Date,BillingPeriodStartDate,BillingPeriodEndDate,MeterUsage,IPU,Scalar,MetricCategory,OrgName,OrgType,IPURate` |

```python
# generic sketch
import io, json, time, urllib.request, zipfile
B = f"{server_url}/public/core/v3/license/metering/ExportMeteringData"
H = {"INFA-SESSION-ID": v3_session, "Content-Type": "application/json", "Accept": "application/json"}
def req(url, body=None, method="GET"):
    r = urllib.request.Request(url, data=json.dumps(body).encode if body else None, headers=H, method=method)
    with urllib.request.urlopen(r, timeout=120) as x:
        return x.status, x.read
st, raw = req(B, {"jobType": "SUMMARY", "startDate": "2026-06-01T00:00:00Z",
                  "endDate": "2026-09-01T00:00:00Z"}, "POST")
job = json.loads(raw)["jobId"]
while json.loads(req(f"{B}/{job}")[1]).get("status") not in ("SUCCESS", "FAILED"):
    time.sleep(20)
st, zbytes = req(f"{B}/{job}/download")
for name in zipfile.ZipFile(io.BytesIO(zbytes)).namelist:
    print(name)                      # one CSV per org
```

**If the export fails**

| Answer | Cause | Fix |
|---|---|---|
| 400 `V3API_007` | a bare date such as `2026-06-01` | full ISO-8601 with a zone (`2026-06-01T00:00:00Z`) |
| 400 `LS_147` | `jobType` sent alone | add `startDate` and `endDate` |
| 400 `LS_298` '... can not be apart 30 days', no job created | a `PROJECT_FOLDER` window longer than 30 days (plan `ASSET` the same way) | split into windows of 30 days or less; `SUMMARY` accepted 33 days with the same dates (L-IPU-021) |
| 404 'No static resource' on a summary GET | the summary reads are not served | use the export; the 404 says nothing about entitlement (L-IPU-022) |
| SUCCESS, header-only CSV | a trial or embedded sub-org | use the proxy (section 5; L-IPU-023) |

The summary GETs 404 even where this works (L-IPU-022): an earlier session concluded from those 404s that a
Consumption API entitlement had to be requested, and was wrong within hours (L-IPU-045, superseded by L-IPU-021).

## 3. Reading the CSV

- `MeterUsage` is the raw scalar in the meter's metric (compute hours, rows, GB, calls); `IPU` is the converted draw;
  `IPURate` and `Scalar` show the conversion; `MetricCategory` groups meters by service.
- One CSV per org: a parent's export probably also covers its sub-orgs, which draw the same pool (L-IPU-001).
- Billing periods need not align with calendar months (a period can end mid-month), so aggregate by
  `BillingPeriodStartDate`/`BillingPeriodEndDate`, not by calendar month (L-IPU-027).
- Some meters are counted per day (catalog and governance assets, scanners) and row-metered pushdown appears within
  about 15 minutes of job completion (Measurement Guide), so a same-day read can be incomplete.

## 4. When billed IPU reads 0

- **Trial and embedded sub-orgs** accrue zero billed IPU even while jobs run: a daily 22-mapping pipeline produced a
  header-only export (L-IPU-023). A zero verdict from such an org is trial-conditional; the real rate comes
  only from the Order.
- **Near-zero usage** (for example a single API Center line of 0.0000133 IPU) is independent evidence that no integration
  job ever ran in the org; check it before diagnosing "broken" runs (L-IPU-026).
- **A meter that reports 0 because it could not read** is a false green: an estimator returned success with 0.0 when the
  activity-log call returned 403 or nothing. Treat zero or unsampled as unknown and fail on collector errors
  (L-IPU-025).

## 5. A labelled proxy from the activity log

(L-IPU-024.)

**What an activity-log row carries** (L-IPU-024). Top-level rows of
`GET <serverUrl>/api/v2/activity/activityLog?rowLimit=1000&offset=<n>` carry `objectId`, `objectName`, `type` (`MTT`,
`WORKFLOW`, `MAPPING`), `runId`, `startTimeUtc` / `endTimeUtc`, `state`, the row counts, `startedBy` (the user) and
`runContextType` (`REST_API_V2` for API starts, `SCHEDULER` for schedule starts). They carry **no**
`runtimeEnvironmentId` and **no** `agentId`. Each row's `entries[]` (one per mapping run, or a taskflow's children)
carries `agentId`, `subTaskEntries`, `transformationEntries` and `logEntryItemAttrs`. So attribute usage to a runtime
environment by mapping `entries[].agentId` to its environment, or by object-name prefix. The log pages 1,000 rows per
call; on a busy org about 3,700-3,800 rows covered the last ~4 days. Profile runs and catalog jobs are not in this log
at all (L-IPU-055). The log is not complete history either: a full read for one busy project held 1,076 entries
reaching back three weeks against more than 500 jobs a day, and each task keeps `maxLogs: 10`, so counts read from it
are lower bounds (L-CDI-288).

```
page GET <serverUrl>/api/v2/activity/activityLog?rowLimit=1000&offset=<n>   # header icSessionId; until a short page
for each run (flatten entries[] of taskflow runs):
    hours = (endTimeUtc - startTimeUtc) / 3600                    # use the *Utc fields; others are pod-local with a Z
    proxy_ipu = hours * RATE                                      # editable, e.g. 1.0, or 0.16 per DI compute hour
    env = runtime_env_of(entries[].agentId) or name_prefix(objectName)   # rows have no runtimeEnvironmentId
group by day, type, env
emit: estimate=true, billed=false, basis=activityLog-duration, model_version=proxy-v1
```

Count jobs as the task rows plus the taskflow rows plus each taskflow's child entries: 2,329 rows were 2,775 jobs
([doc 03](03-entitlement-licenses-job-caps.md) section 7.1).

Emit proxy rows next to the billed rows from the export (`estimate=false, billed=true, source=ExportMeteringData`) in
the same table, so dashboards switch to billed data when it appears. Measured: a proxy of 3.92 IPU over 200 runs against
3.95 processing hours from another source. The activity log keeps only a few days, so collect it on a schedule; the same
feed is the only way to count jobs against a monthly job limit ([doc 03](03-entitlement-licenses-job-caps.md)).

## 6. Administrator CSV exports

(L-IPU-028.) Downloaded from the Administrator console (the menu path was not recorded); treat them as
customer data.

| Export | Columns | Use |
|---|---|---|
| Agents | UUID, Agent Group Name, Agent Name, Available Processors, Created On, Updated On, Status, Version, Agent ID | Agent inventory with cores and versions |
| License | UUID, License Type Name, Service Name, Edition Name, Category (Mappings, Packages, Connectors, Bundles,...), License Type (for example SUBSCRIPTION), Expiration Date | The licence inventory REST does not offer |
| CAI Connections | UUID, Connection Name, Connector Type, Publication Status, OData Enabled, Runs On Agent Only | CAI connection census |
| Unique Endpoints | UUID, Connection, Connection Type, Pricing Tier, Connector Property Name/Value, Service URL, Database, Schema, Host, Username, Created, Last Used, Days Since Last Used | Connector tier licensing per end point; stale-connection cleanup |

## 7. The console and alerts

Usage is tracked automatically in the product: the Administrator Metering console shows consumption and administrators
can set consumption-threshold alerts (documented, L-IPU-027). For a monthly IDMC - IPU subscription, compare the month's
IPU total with the subscribed quantity: Overage Protection reviews trigger at 25% over in two consecutive months (or three
of five) or 100% over in one month ([doc 01](01-ipu-model-mechanics.md) section 2).

## 8. Jobs are a separate ledger

The export measures IPUs. Monthly job limits count task and taskflow runs, including taskflow runs that incur no compute
hours, and are not visible in the export or any API (L-IPU-044). Keep the job ledger described in
[doc 03](03-entitlement-licenses-job-caps.md) section 7.1.

## 9. Overturned beliefs (metering)

| Believed | Until | Now | Lesson |
|---|---|---|---|
| Metering needs an org-admin Consumption API entitlement; actuals are UI-only | 2026-07-04 | The async export works with no new entitlement | L-IPU-045 -> L-IPU-021 |
| Licensing and consumption have no API at all | 2026-07-26 | Consumption is readable through the export; only the licence inventory is UI-only | L-IPU-046 -> L-IPU-021 |
