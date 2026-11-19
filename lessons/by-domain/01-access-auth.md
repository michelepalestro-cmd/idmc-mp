# Lessons: Access & Auth
136 lessons: 124 current, 1 disputed, 11 superseded; evidence dated 2026-06-27 to 2026-11-19.

Last verified: 2026-06-27 to 2026-10-02.

Related: [Pods, Hosts & Service Planes](../../knowledge/01-access-auth-orgs/01-pods-hosts-service-planes.md) · [Login, Sessions & Tokens](../../knowledge/01-access-auth-orgs/02-login-sessions-tokens.md) · [Identify the Org Before You Write](../../knowledge/01-access-auth-orgs/03-identify-the-org-before-you-write.md) · [Users, Roles & Permissions](../../knowledge/01-access-auth-orgs/04-users-roles-permissions.md)

Topics: planes and hosts L-AUTH-001 to 017 · logins, sessions and tokens 018 to 033 · lockout 034 to 045 · org identity and multi-org safety 046 to 056 · users, roles, permissions and entitlement 057 to 076 · superseded beliefs 077 to 087. Each superseded entry names the lesson that overturned it.

## Current
### L-AUTH-001  The auth plane is a property of the host and path; never mix planes
**Kind:** LAW · **Proven:** 2026-09-28 · **Evidence:** Plane table from about 360 live host/header/path combinations (2026-07-25); per-service route tests 2026-09-22 to 09-24; login HTML from FRS and selections routes sent INFA-SESSION-ID (2026-09-28)
IDMC serves roughly ten auth planes, each with its own host and header: v2 `icSessionId` on `<serverUrl>/api/v2/*`; v3 `INFA-SESSION-ID` on `/saas/public/core/v3/*`; `IDS-SESSION-ID` on the pod host's FRS, runtime-selection and licence services and on `<pod>-ing` and `<pod>-dqprofile`; the identity three-header set on `idmc-api.<domain>`, `cdgc-api.<domain>` and `<pod>-mdm`; `INFA-SESSION-ID` on `<pod>-cai`; no header on anonymous CAI. A credential on the wrong plane fails convincingly: a 200 carrying the identity-service login page, a misleading 404, or a 401. Choose the header from the host/path map, not from whichever login you happen to hold.

### L-AUTH-002  Host map: log in at the domain host, then use the pod, per-pod service and shared domain hosts
**Kind:** ROUTE · **Proven:** 2026-09-29 · **Evidence:** 200s per host with the matching header on pods under two domain labels, 2026-07-06 to 2026-09-29
Login and identity-service: `https://<domain>.informaticacloud.com`. Platform: `https://<pod>.<domain>.informaticacloud.com` with v2 under `/saas/api/v2`, v3 under `/saas/public/core/v3` and, without `/saas`, FRS (`/frs/...`), runtime selections (`/runtime/api/v2/...`) and the licence service (`/license-service/api/v1/...`). Per-pod services: `<pod>-cai` (CAI), `<pod>-mdm` (MDM runtime, no `/saas`), `<pod>-ing` (Database Ingestion), `<pod>-dqprofile` (profiling), `<pod>-dqcloud-api` (CDQ dictionaries). Shared: `idmc-api.<domain>` (CDGC `data360`, Marketplace, MDM control), `cdgc-api.<domain>` (CDGC write plane), `hdm.<domain>` (MCP asset management), `mcp.<domain>` (managed MCP servers). A route sent to the wrong host 404s, which is not a capability signal.

### L-AUTH-003  Derive service hosts from the login's base URL; a pod-literal string replace breaks after an org move
**Kind:** GOTCHA · **Proven:** 2026-09-28 · **Evidence:** Code review after an org move (2026-09-28): several builders still targeted the old pod's CAI host; the helper that split the host at the first dot was correct
Take the base from `products[].baseApiUrl` (v3 login) or `serverUrl` (v2 login) and build service hosts by splitting the host at the first dot: `<pod>` + `-cai`, `-mdm`, `-ing`, `-dqprofile` or `-dqcloud-api` + `.<rest>` (drop `/saas` for `-mdm` and for the pod-host services). Builders that computed the CAI host with `serverUrl.replace("<pod1>.<dom1>", "<pod1>-cai.<dom1>")` silently kept calling the pod host once the org lived on another pod, and hard-coded service hosts needed the same review at the move.

### L-AUTH-004  The domain label is one character and not guessable; the wrong label gives 404, IDS_085 or a foreign-org 401
**Kind:** GOTCHA · **Proven:** 2026-09-22 · **Evidence:** Every borrowed URL 404'd between two orgs and the other domain's cdgc-api answered 401 to a foreign-org token (2026-07-26); valid credentials gave 400 IDS_085 at the other label (2026-09-22)
Pods sit under domain labels such as `dm-us`, `dmp-us`, `dm-em`, `dm-ap`, `dm-na` and `dm-uk`; some North American orgs are on `dmp-us`, not `dm-us`. Read the label off `products[].baseApiUrl` instead of guessing it from the pod name. A URL borrowed from an org on the other label returns 404 on the platform plane, `400 IDS_085` at login, and a clean 401 on the other domain's `cdgc-api` host (the route is real; the token belongs to another org).

### L-AUTH-005  Log in at the domain host; send authenticated platform calls to the pod host
**Kind:** ROUTE · **Proven:** 2026-09-22 · **Evidence:** v3 objects 200 on the pod host and 404 on the entry host; login 404 on the pod host (2026-09-21/22)
All three logins go to `https://<domain>.informaticacloud.com`: `POST /saas/public/core/v3/login`, `POST /ma/api/v2/user/login` and `POST /identity-service/api/v1/Login`. Every authenticated v2 and v3 call then goes to the pod base returned in `baseApiUrl` or `serverUrl`. The entry host answered the login but returned 404 on `/public/core/v3/objects`, and the pod host returned 404 for the login path on one pod.

### L-AUTH-006  A zero-byte 200 is gateway prefix routing, not success
**Kind:** GOTCHA · **Proven:** 2026-07-26 · **Evidence:** Real and bogus data360 paths both 200 with 0 bytes; header variants identical (2026-07-26)
A 200 with `Content-Length: 0` and no Content-Type means the gateway routed the path prefix and nothing served it; a bogus sibling such as `/data360/search/api/v99/bogusZZZ` answered identically. It was seen on every `data360` path of one pod while CDGC was licensed there, both with the three identity headers and with Bearer alone. Assert on body shape and Content-Type, never on status alone, and treat the case as a deployment question, not an entitlement ticket.

### L-AUTH-007  A 200 carrying the identity-service login page means wrong plane, wrong header or an expired session
**Kind:** ERROR · **Proven:** 2026-09-28 · **Evidence:** 6 of 26 probe results were fake 200s (2026-09-22); login HTML from FRS/selections with INFA-SESSION-ID (2026-09-28); the HTML-200 re-login fix in a helper (2026-06-27)
Some gateways answer an unauthenticated or wrong-plane request with HTTP 200 and the identity-service login page (the SPA shell). It appeared on FRS and runtime-selection routes sent `INFA-SESSION-ID` instead of `IDS-SESSION-ID`, on `POST /api/v2/miTask`, on `<pod>.<domain>/saas/mftsaas/api/v1/`, on 6 of 26 Database Ingestion deploy probes, and on v2 calls made with a stale `icSessionId`. Treat any 200 whose body starts with `<` or whose Content-Type is HTML as a failure; a session helper should drop its cache and log in exactly once more.

### L-AUTH-008  Sweep the host family by DNS before believing a service-level 404
**Kind:** LAW · **Proven:** 2026-07-26 · **Evidence:** DNS results plus same-path A/B across hosts and bogus-twin controls (2026-07-26)
DNS lookups are free and need no auth. Resolve `<pod>-ing`, `-mdm`, `-cai`, `-dqcloud-api`, `-dqprofile`, `-apigw` and `-apim`, plus `idmc-api.<domain>` and `cdgc-api.<domain>`, and a deliberately bogus `<pod>-bogusZZZ` that must fail. On one `dmp-us` pod `-ing`, `-apigw`, `-apim`, `-mdm`, `-dqcloud-api`, `-dqprofile` and `-cai` resolved while `-dam`, `-prep`, `-dataprep`, `-clairegpt` and `-ai` did not. This check overturned a whole-product UI-only verdict: Database Ingestion paths 404 on the pod host because the service lives on `<pod>-ing`.

### L-AUTH-009  Unprefixed or reversed host forms have no DNS, and -apigw/-apim 503s carry no meaning
**Kind:** GOTCHA · **Proven:** 2026-07-26 · **Evidence:** DNS failures; identical 503 on real and bogus paths (2026-07-26)
Service hosts are always `<pod>-<service>.<domain>`: `mdm.<domain>`, `apigw-pod.<domain>`, `<pod>-cdgc`, `<pod>-mdm-model`, `<pod>-b360` and `<pod>-cs` do not resolve. `<pod>-apigw` and `<pod>-apim` answer nginx 503 on every path, bogus ones included: a load balancer with no backend, so a 503 there proves neither presence nor absence of a route.

### L-AUTH-010  Route families mount per pod and per licensed engine, not per org
**Kind:** GOTCHA · **Proven:** 2026-07-26 · **Evidence:** Live A/B; runtimeEnvironments retested three ways (2026-07-26)
Probed the same week on a `dm-us` org and a `dmp-us` sub-org: `GET /api/v2/license`, `/api/v2/loginAudit`, `/api/v2/{dss,dtemplate,dmask,dreplicate,plan,fileListener}`, `/public/core/v3/runtimeEnvironments` (also with `?limit=1`) and `/public/core/v3/{agent,agentGroups,tags,licenses,orgs,permissions}` answered 200 on the first and 404 on the second, while `/api/v2/runtimeEnvironment` and `/api/v2/agent` answered on both. Prefer the v2 admin forms and never generalise a route inventory from one org.

### L-AUTH-011  A result proven on one org or pod is not evidence for another
**Kind:** LAW · **Proven:** 2026-09-28 · **Evidence:** Live A/B across two orgs (2026-07-25/26); profiling session difference between two pods (2026-09-28)
Route availability, accepted session types and error behaviour differ by pod, org and licensed engine; for example, one pod's profiling service rejected the v2 session that another pod's accepted. Re-probe every route in the org you are working in, store host, header, path, status and date with each verdict, and work in one org per session unless told otherwise. Newer evidence: L-METHOD-155.

### L-AUTH-012  Read the kind of 404 before concluding anything; a 405 proves the route exists
**Kind:** LAW · **Proven:** 2026-07-26 · **Evidence:** 405 vs 404 contrast on data360 routes (2026-07-06); parent-path 404 beside a 200 collection (2026-07-04); typed error on the -ing host vs bare 404 on the pod host (2026-07-26)
A 404 with a text or JSON body means a wrong path, host or domain label: keep hunting. A Spring `No static resource` body means the service is deployed but has no handler at that path; an empty-body 404 after a host sweep means nothing serves the prefix; a typed product error such as `DBMI_TASK_WAS_NOT_FOUND` means a live handler missed a lookup. A 405 means the route exists without that verb, and even known-good collections 404 at their parent path (`.../v1/catalogsources` 200, `.../v1` 404). Confirm with a known-good sibling, the right host and a bogus twin before calling anything a wall.

### L-AUTH-013  Jobs, connections and runtime environments live on v2; v3 adds objects, users, licences and logs
**Kind:** ROUTE · **Proven:** 2026-07-25 · **Evidence:** 200/404 live (2026-07-25)
The v2 plane (`<serverUrl>/api/v2/*`) carries job, activityLog, activityMonitor, mttask, workflow, schedule, connection, agent, runtimeEnvironment and org. The v3 plane (`/saas/public/core/v3/*`) carries objects, lookup, export and import, TagObjects, users, userGroups, roles, privileges, license, securityLog, and read-only activityLog and schedule lists. `GET /public/core/v3/jobs`, `/public/core/v3/connections` and `/public/core/v3/licenses` returned 404 on the org probed (`/public/core/v3/runtimeEnvironments` 404 there and 200 on another pod); `POST /api/v2/alerts` returned 200.

### L-AUTH-014  v2 and activity-log times are pod-local but labelled Z: use the *Utc fields
**Kind:** GOTCHA · **Proven:** 2026-09-28 · **Evidence:** A job list looked 4 h stale after an org move until the *Utc fields were used; re-verified (2026-09-28)
On the pods seen, v2 `createTime`/`startTime` and activity-log `startTime`/`endTime` were pod-local time (UTC-4) carrying a `Z` suffix. Use `startTimeUtc`/`endTimeUtc` from `GET /api/v2/activity/activityLog` to detect completion, and set schedules with both `startTime` (pod-local) and `startTimeUTC`; a fixed -4 h offset is only a fallback.

### L-AUTH-015  Verb conventions differ by plane: POST-to-id on v2, POST-then-poll for jobs, empty-POST verb probes
**Kind:** LAW · **Proven:** 2026-07-26 · **Evidence:** July route corpus and live empty-POST probes (2026-07-25/26)
On the v2 plane an update is a POST of the full object to `/api/v2/<resource>/<id>`; elsewhere the idiom is DELETE and re-POST, except where a PUT is proven. PATCH is meaningful mainly in MDM (`entity`, `entity-xref`) and the CDGC content API. Long operations are POST-to-start then GET-to-poll (export, import, metering, scans, CAI publish), and a GET on the starter returns 405 (for example `GET /saas/public/core/v3/export`). There is no HEAD or OPTIONS: probe a write verb with an empty POST (400, 415, 422 or a null-field 500 means the verb exists; 405 means it does not).

### L-AUTH-016  PUT exists: the runtime-environment selections PUT is a proven write
**Kind:** OVERTURNED · **Proven:** 2026-09-28 · **Evidence:** Selections PUT read back with the new services and connectors (2026-09-28)
The July 2026 route corpus counted PUT 0 and PATCH 0 proven. `PUT https://<pod>.<domain>.informaticacloud.com/runtime/api/v2/runtimeEnvironment/<reId>/selections/ui` with `IDS-SESSION-ID` (GET the selections, edit the flags, PUT them back) changed an agent's services and connectors, and the same migration updated CDGC catalog sources with a multipart PUT and profiles with PUT. Treat every other documented PUT or PATCH as unproven until probed.

### L-AUTH-017  MCP and CLAIRE hosts and the credentials they take
**Kind:** ROUTE · **Proven:** 2026-09-28 · **Evidence:** 19 managed servers listed, an OAuth client created (201) and tool calls answered (2026-09-21/28); vendor MCP guide pp.12-18 (April 2026); CLAIRE GPT chat 201 in the UI (2026-07-09)
The managed-MCP registry and OAuth clients live on `https://hdm.<domain>.informaticacloud.com/a2e-mcp-asset-mgmt-svc/api/v1/{mcp-servers,oauth2clients}` with `IDS-SESSION-ID` set to a v3 session. Managed servers answered on `https://mcp.<domain>.informaticacloud.com/mcp-servers/public/<context>` with a Bearer token from `https://<domain>.informaticacloud.com/authz-service/oauth/token` (client credentials) or with an identity JWT (`client_id=idmc_api`) plus `IDS-SESSION-ID`; the April 2026 vendor guide shows `a2e-prod-<pod>-mcp.<domain>` and three methods (session id, JWT, OAuth). OAuth tokens default to 5 minutes (configurable 5 to 1,440). CLAIRE GPT runs on `claire-gpt.<domain>`, and the CLAIRE agent MCP at `<claire_api_url>/claire-orchestrator-ai-agent/api/v1/mcp` with an identity JWT.

### L-AUTH-018  v3 login returns the session, the 22-character org id and the pod base URL
**Kind:** ROUTE · **Proven:** 2026-09-28 · **Evidence:** Used for every migration, CDGC, MCP and profiling call of a September org move (2026-09-28)
`POST https://<domain>.informaticacloud.com/saas/public/core/v3/login`, `Content-Type: application/json`, body `{"username":"<user>","password":"<pw>"}` returns 200 with `userInfo.sessionId`, `userInfo.id`, `userInfo.name`, `userInfo.orgId` (the 22-character `<orgIdV3>`), `userInfo.orgName` and `products[].baseApiUrl` (`https://<pod>.<domain>.informaticacloud.com/saas`). Send the session as `INFA-SESSION-ID` on `/public/core/v3/*` and on `<pod>-cai`, and take the API base from `baseApiUrl`, never from a guessed pod. Use this v3 session where a plane rejects the v2 id (the profiling service on some pods, the MCP asset-management service).

### L-AUTH-019  v2 login returns icSessionId and serverUrl; use serverUrl as the v2 base
**Kind:** ROUTE · **Proven:** 2026-09-28 · **Evidence:** 200 on two orgs (2026-07-25); every v2 call of the September tooling (2026-09-28)
`POST https://<domain>.informaticacloud.com/ma/api/v2/user/login`, `Content-Type: application/json`, body `{"@type":"login","username":"<user>","password":"<pw>"}` returns `icSessionId`, `serverUrl` (the pod base ending in `/saas`), `orgId` (the 6-character `<orgIdV2>`) and `orgName`. Call `<serverUrl>/api/v2/...` with header `icSessionId`, and use `serverUrl` as the base instead of assuming a pod.

### L-AUTH-020  One session value worked on both v2 and v3; the header name is what is plane-specific
**Kind:** OVERTURNED · **Proven:** 2026-09-28 · **Evidence:** v2 calls 200 with the v3 sessionId (2026-09-21); all wrapper calls on one v2 login (2026-09-28)
In September 2026 the v2 `icSessionId` was accepted on `/public/core/v3/*` as `INFA-SESSION-ID`, and the v3 `userInfo.sessionId` was accepted on `/api/v2/*` as `icSessionId`, on pods under both domain labels; wrappers ran every v2 and v3 call on a single v2 login. The July rule "a v3 token on a v2 endpoint gives a 200 HTML page or a 404" was observed on an org where JWT-on-login made the v3 sessionId a JWT, which is probably what v2 rejected (inference; not re-tested). Keep the header name per plane; the opaque session value can be shared.

### L-AUTH-021  Identity-service Login returns sessionId and orgId; CurrentUserInfo and Orgs read the identity
**Kind:** ROUTE · **Proven:** 2026-07-25 · **Evidence:** 200 live (2026-07-25); vendor Address Verification API guide
`POST https://<domain>.informaticacloud.com/identity-service/api/v1/Login`, `Content-Type: application/json`, body `{"username":"<user>","password":"<pw>"}` returns `sessionId` and `orgId` (vendor-documented; a SAML variant exists). In July 2026 the same response carried roles, `effectivePrivileges` and `feature.<cap>.*` flags, the entitlement ground truth. `GET .../identity-service/api/v1/CurrentUserInfo` and `GET .../identity-service/api/v1/Orgs` returned 200 with the current identity and the org list.

### L-AUTH-022  Mint a JWT at identity-service jwt/Token with IDS-SESSION-ID and the USER_SESSION cookie
**Kind:** ROUTE · **Proven:** 2026-09-29 · **Evidence:** Catalog search returned 5,089 assets with the minted JWT (2026-09-24); JWT lengths 2,138-2,180 (2026-09-28)
`POST https://<domain>.informaticacloud.com/identity-service/api/v1/jwt/Token?client_id=<client>&nonce=<random>` (field scripts also append `&access_code=`) with headers `IDS-SESSION-ID: <sid>` and `Cookie: USER_SESSION=<sid>` and an empty body returns `jwt_token`, about 1,700 to 2,200 characters. A `GET` with the same query and `IDS-SESSION-ID` also minted (the CLAIRE and MCP shims). `<sid>` was the identity-service `sessionId` (documented) or the v3 login `sessionId` (proven); use a fresh nonce per request.

### L-AUTH-023  client_id=idmc_api and client_id=cdlg_app are both in use; each is recorded only where it worked
**Kind:** GOTCHA · **Proven:** 2026-09-29 · **Evidence:** MCP, CDGC and MDM calls answered with the respective JWTs (2026-09-21 to 09-29)
`client_id=idmc_api` is the vendor-documented value and worked for the managed MCP servers and the hosted Data Quality agent MCP; `client_id=cdlg_app` was used for CDGC (catalog-source management on `cdgc-api`, `data360` on `idmc-api`) and for MDM record search on `<pod>-mdm`. The CLAIRE agent MCP shim reads its `client_id` from configuration. Which services refuse the other value was never isolated, so copy the value recorded for the service you are calling.

### L-AUTH-024  Send the three identity headers; Bearer alone gets 401 on writes
**Kind:** GOTCHA · **Proven:** 2026-07-26 · **Evidence:** Bearer-only writes 401; scan 201 with all three headers; 401 vs 201 between two helpers (2026-06-28 to 2026-07-26)
On `idmc-api.<domain>`, `cdgc-api.<domain>` and `<pod>-mdm.<domain>` send `Authorization: Bearer <jwt>`, `IDS-SESSION-ID: <sid>` and `X-INFA-ORG-ID: <orgIdV3>`. Bearer alone gets 401 on writes (GETs tolerated it); a catalog scan with a missing header or an empty `capabilityNames` list gets 500 `Login sessionID is missing` from the ccgf-auth-pep guard. A generic helper that sent only the v3 session header got 401 on `data360` where the JWT path succeeded.

### L-AUTH-025  FRS, runtime selections, the licence service and the -ing plane take the v2 session in IDS-SESSION-ID
**Kind:** GOTCHA · **Proven:** 2026-09-28 · **Evidence:** FRS moves and deletes, selections GET/PUT, licence reads and DBMI calls worked with IDS-SESSION-ID; login HTML with INFA-SESSION-ID (2026-09-28)
`https://<pod>.<domain>.informaticacloud.com/frs/api/v1/...` (or `/frs/v1/...`), `/runtime/api/v2/runtimeEnvironment/<reId>/selections/ui` and `/license-service/api/v1/...` take the v2 `icSessionId` in header `IDS-SESSION-ID`. Sent `INFA-SESSION-ID`, the FRS and selections routes return the login HTML with status 200, which a script can mistake for success. The Database Ingestion plane on `<pod>-ing` also worked with `IDS-SESSION-ID`; the helpers sent `IDS-SESSION-ID`, `INFA-SESSION-ID` and `icSessionId` together there, so the minimal header was not isolated.

### L-AUTH-026  The profiling service is scriptable, and on some pods it needs the v3 session
**Kind:** OVERTURNED · **Proven:** 2026-09-28 · **Evidence:** 401 with the v2 id and 8/8 COMPLETED with the v3 id (2026-09-28); headless profiles with IDS-SESSION-ID (2026-09-24)
`https://<pod>-dqprofile.<domain>.informaticacloud.com/profiling-service/api/v1` answered to `IDS-SESSION-ID` from September 2026. On one pod it returned 401 "Exception encountered while processing JWT" to the v2 `icSessionId` and worked with the v3 login `sessionId` in the same header (8 of 8 profile jobs completed); another pod accepted the v2 id. Make the helper pick the session per org. This overturns the July reading that the profiling routes are SPA-session-only.

### L-AUTH-027  The v2 session dies 30 minutes after grant regardless of activity
**Kind:** OVERTURNED · **Proven:** 2026-09-28 · **Evidence:** Sessions died at 30 minutes during a long migration although calls kept flowing (2026-09-28)
Treat the v2 `icSessionId`, and JWTs derived from a session, as absolute 30-minute credentials: store the grant time with the session and log in again when it is older than 24 to 25 minutes (1,500 s), before a long batch starts; on an API 401 drop the cache and log in exactly once more. The 30-minute idle figure is documented for MDM SaaS sessions, a different plane.

### L-AUTH-028  A JWT expires 30 minutes after it is granted; re-mint it from the cached session
**Kind:** LAW · **Proven:** 2026-08-03 · **Evidence:** Vendor Address Verification API guide p.9; bulk-ingest design review (2026-08-03)
The vendor documents that the access token expires 30 minutes after the initial grant and must be regenerated. Re-mint it from the cached session (about 0.5 s, no password) when it is older than about 25 minutes or on any 401, instead of logging in again. Sizing example: 98,115 sequential writes at about 10 per second take about 2.7 h, so a token minted once covers only about 18% of the run.

### L-AUTH-029  Cache the long-lived identity session and the 30-minute JWT separately; each server keeps its own session
**Kind:** RECIPE · **Proven:** reported by a colleague's document (2026-07-16); not probed · **Evidence:** Colleague architecture document v1.0 (2026-07-16); shim behaviour (2026-07-26)
A colleague's MCP fleet reports the identity-service session lasting about 8 hours and the JWT 30 minutes, with a JWT refresh from the cached identity session taking about 0.5 s and no credential prompt. Cache both on disk with the org id and base URL (for example one file per server and role): cold start about 6 to 8 s, warm start about 0 s. Each MCP or product server holds its own session, so a 401 from one server only means that server needs its own login. Not probed here.

### L-AUTH-030  Session cache that held: one 0600 file per org, grant time, 25-minute refresh, one retry on 401
**Kind:** RECIPE · **Proven:** 2026-09-28 · **Evidence:** Stable across the September tooling and a full org migration (2026-09-28)
Cache `{sid, serverUrl, orgId, t}` in a mode-0600 file per org and reuse it across every script and browser run; log in again when it is older than 1,500 s. Keep the v3 session in its own cache (also about 25 minutes) and the CDGC JWT for about 20 minutes, renewing on 401. Serialize logins with a file lock and re-check the cache after taking the lock, treat an HTML 200 as an expired session, and on an API 401 drop the cache and log in exactly once more. Wrappers that return `(status, body)` without raising need callers that check the status.

### L-AUTH-031  Share one cached session under a file lock rather than a fresh login per agent
**Kind:** OVERTURNED · **Proven:** 2026-09-24 · **Evidence:** 401s from overwritten caches (2026-06-27); a lock attributed to per-script login volume (2026-08-20); no lockouts across dozens of sessions with one shared cache (2026-09-24)
Parallel agents sharing an unguarded session file overwrite or expire each other's session and produce confusing 401s. The fix that held is one shared cache per org, written under a file lock and re-checked after locking, not a fresh login per agent or per script: the extra logins are themselves a lockout risk.

### L-AUTH-032  Switching the org's authentication type to JWT changes what the login returns; stage clients first
**Kind:** RECIPE · **Proven:** JWT-form sessionId proven 2026-06-27; switch side effects untested · **Evidence:** The login sessionId began with ey and was accepted as Bearer (2026-06-27); switch plan only (2026-09-03)
An org administrator can set the org's authentication type to JWT (recorded as Administrator > Authentication > Authentication Type in June 2026 and as Administrator > Settings > General settings > Authentication type in a September plan). With it on, the v3 login `userInfo.sessionId` was a JWT (it starts with `ey`, about 1,700 characters) that CDGC GETs accepted as Bearer. A vendor thread said managed MCP needs the org on JWT, and the plan expected session-ID clients (`INFA-SESSION-ID`, `icSessionId`) to break after the switch; neither claim was verified, and later MCP calls succeeded with OAuth-client tokens and identity JWTs without the org's mode being recorded. Before flipping, move clients behind an `AUTH_MODE=session|jwt` flag, pause schedulers, and keep the switch reversible.

### L-AUTH-033  Session-ID REST authentication is deprecated: JWT becomes the default after the October 2026 release, JWT values are capped at 2,000 characters, and some clients must not use it (documented)
**Kind:** LAW · **Documented:** 2026-10-02 · **Evidence:** Vendor What's New important notices of April 2026 and July 2026 (including the July 'Upcoming change' on the 2,000-character limit), read 2026-10-02; a ~1,700-character JWT session value observed live (2026-06-27); an org switched to JWT by default not yet observed
The Data Integration What's New notices of April and July 2026 say that session-based REST authentication has been deprecated since the October 2025 release and will be dropped in a future release, and that session-based stays the default until JWT becomes the default 'sometime after the October 2026 release' (the April notice had said October 2026, so the date has slipped once). The org administrator chooses the REST authentication type in Administrator settings (L-AUTH-032). With JWT on, the browser UI switches by itself and REST calls still send the session header, but its value is a JWT with a fixed expiry set in Administrator, so scripts must re-authenticate on a timer and on a 401 instead of relying on a long-lived session. From the October 2026 release JWT values are limited to 2,000 characters and longer ones are truncated: a JWT session value of about 1,700 characters was observed (L-AUTH-032), so check token length in clients that add claims or wrap tokens. Do not enable JWT authentication where API Manager or the REST V2 Connector calls IDMC APIs; API Center and, since April 2026, B2B Gateway support it. A related credential change in the same notices: source-control access to Bitbucket needs a Bitbucket API token, because app passwords stopped working on 2026-06-09. Design every script for both modes now: auth behind a session|jwt switch, refresh on a timer and on 401.

### L-AUTH-034  IDS_086 is the only lock code; IDS_085, UI_10000 and a 400 mean the credential or the host is wrong
**Kind:** ERROR · **Proven:** 2026-09-28 · **Evidence:** IDS_086 until an admin unlock (2026-08-18/19, 2026-09-28); IDS_085 at the wrong domain (2026-09-22); v2 403 UI_10000, v3 400 and identity 400 for one rejected credential (2026-08-18); truncated user name (2026-09-20)
`IDS_086` "User account is locked. Contact your organization administrator." (401 on the v3 login) means locked. `IDS_085` "User name or password is not valid" (400 on the v3 login) means a bad or placeholder password, a truncated user name, or valid credentials sent to the wrong login domain; the v2 login answers the same case with `403 UI_10000` and the identity-service Login with 400. Once a lock ages out, a wrong stored password flips the code from `IDS_086` to `IDS_085`.

### L-AUTH-035  IDS_085 at the wrong login domain is not a lockout; check the host before the password
**Kind:** OVERTURNED · **Proven:** 2026-09-22 · **Evidence:** Own domain 200, other domain 400 IDS_085, pod host 404 (2026-09-22)
Before concluding that an account is locked or its password changed, check that the login host matches the org's domain: an org provisioned on `dmp-us` returned `400 IDS_085` when its valid credentials were posted to `dm-us` and 200 at its own domain, while its pod host returned 404 for the login path. Only `IDS_086` means locked, and retries against the wrong host still count toward a lockout.

### L-AUTH-036  Rejected logins from every session add up, and each attempt during a lock can restart it
**Kind:** LAW · **Proven:** 2026-09-28 · **Evidence:** At least 6 failures locked the account (2026-09-28); a single retry after 40 minutes still returned 401 IDS_086 (2026-08-19)
Failed logins from different sessions and tools count against the same account: at least 6 rejections across 3 sessions locked one account. Each new attempt during the lock can reset the cooldown, and one careful retry more than 40 minutes later was still locked. Stop every automated login, schedule no retries, and plan on an unlock rather than on waiting.

### L-AUTH-037  Unlock with an admin or a password reset, then make one confirmed attempt
**Kind:** PROCESS · **Proven:** 2026-09-28 · **Evidence:** Reset unlocked the account and the next single login returned 200 within a minute (2026-09-28)
An org admin can unlock the user (Administrator > Users > the user > Unlock); a password reset also unlocks, either through "Forgot your password?" at `https://<domain>.informaticacloud.com/identity-service/home` or Reset password in Administrator. A second admin is needed when the locked user is the only admin; otherwise open an Informatica support case. The org's lockout policy (Administrator > Organization > Security) may auto-unlock after a window, but sources disagree on whether locks expire and one was still active after 40 minutes. After the unlock, confirm the password in a browser once, then let one session make one attempt.

### L-AUTH-038  One credential, one designated session, one attempt
**Kind:** PROCESS · **Proven:** 2026-09-28 · **Evidence:** At least 6 failed logins from 3 sessions caused the lock; the single attempt after the reset returned 200 (2026-09-28)
When a password is pasted to several parallel sessions, name one session to try it once, and nobody retries after an `IDS_085`. Three sessions each trying the pasted candidates produced at least 6 failures and a lock; after the reset, one session logged in once, a second confirmed from the shared cache, and from then on only one session logged in to that org.

### L-AUTH-039  Automation holding a stale password re-locks the account right after every unlock
**Kind:** ERROR · **Proven:** 2026-08-18 · **Evidence:** IDS_086 persisted until the stored password was corrected and one unlock issued; the next v3 login worked (2026-08-18)
Cron pollers, health checks and helper scripts that log in every few minutes with a stale stored password re-lock the account immediately after each unlock. Correct the password in every config the automation reads, pause or fix the pollers, then ask for one unlock; with the stored copies corrected the unlock holds. One source adds that a poller holding the correct password cannot cause a lock; a later report attributes a lock to login volume alone (L-AUTH-040), so keep login volume low either way.

### L-AUTH-040  Login volume alone was blamed for one lock: reuse one cached session everywhere
**Kind:** LAW · **Proven:** 2026-08-20 · **Evidence:** Lock mid-session after a 696-object inventory (2026-08-20)
Cache the session with its grant time and share it across every script and browser run instead of logging in per call or per script. One lock was attributed to login volume rather than to a bad password: every enumeration and probe script opened fresh v3 and v2 sessions, a 696-object inventory completed, and the lock tripped mid-session. Keep browser automation serial.

### L-AUTH-041  Host-script lockout guard: file lock, re-check, and a block file keyed to the creds fingerprint
**Kind:** SECURITY · **Proven:** 2026-09-28 · **Evidence:** Mocked-network tests 11/11 (2026-09-28)
Serialize logins with `fcntl.flock` on a lock file and re-check the session cache after taking the lock, because another process may just have logged in. When the server rejects a login (any 4xx other than 429), write a block file holding the SHA-256 fingerprint of the creds file; while the fingerprint matches, every process refuses to log in ("fix the creds or delete the block file"). A 5xx or 429 does not block, and an API 401 triggers exactly one re-login. Test it against a mocked network: after a rejected login, 10 further attempts must make 0 network logins, and changing the creds file must lift the block.

### L-AUTH-042  A service that logs in on its own must back off for hours after an auth rejection
**Kind:** SECURITY · **Proven:** 2026-09-28 · **Evidence:** 14/14 offline tests; 20 retries during a block made 0 network calls (2026-09-28)
A scheduler that ticks every few seconds locks the account within a minute if it retries a rejected login. After a 4xx answer other than 429, block logins for hours (a 6-hour default, 21,600 s); after a network failure or 5xx, block for 60 s; show the block on the service's health endpoint and clear it on a good login. To retry sooner, fix the creds and recreate the service. Test it in a throwaway container with `--network none` against a fake login server.

### L-AUTH-043  Rotate a password by updating every stored copy, clearing the guard, and verifying with one login
**Kind:** SECURITY · **Proven:** 2026-09-29 · **Evidence:** Rotation script and a cutover report listing four touchpoints (2026-09-29)
After a human changes the password: prompt for it without echo; write it in place into every creds file (same inode, backups kept, mode 600); delete the lockout block file and the session caches; verify with exactly one login; only then restart the dependent services. Inventory the touchpoints first: host creds files, service env files, catalog sources that store the user's password (the CDI lineage source keeps a user and password in its options), and MCP OAuth clients created with that password; each must be updated or recreated, or it fails or re-locks the account.

### L-AUTH-044  A user lockout does not stop the Secure Agent, only work that needs a user session
**Kind:** GOTCHA · **Proven:** 2026-08-19 · **Evidence:** Schedules kept running during a lock (2026-08-19)
The Secure Agent authenticates with its own agent token, so already-scheduled tasks keep running while the interactive user is locked; REST job triggers, exports and UI work are blocked. Keep login-independent work going during a lock.

### L-AUTH-045  Automate with a native IDMC user; SSO-only users and login-name mismatches fail native login
**Kind:** GOTCHA · **Proven:** 2026-09-28 · **Evidence:** One credential was rejected by the v2 login (403 UI_10000), the v3 login (400) and the identity Login (400); it was attributed to an SSO password, although the domain may also have been wrong (2026-08-18); a later case resolved by a reset (2026-09-28)
If a login keeps returning "User name or password is not valid", the IDMC login name may differ from the e-mail address, the password may be a placeholder, or the user may be SSO-federated with no IDMC-native password; native REST login then needs a native user or an API-only user. Confirm the exact login once in a browser before any scripted attempt, stop after the first failure, and run automation as a dedicated native automation user rather than a personal or SSO account.

### L-AUTH-046  Establish org, pod and domain from the login before any other call
**Kind:** LAW · **Proven:** 2026-09-28 · **Evidence:** Live logins on two orgs (2026-07-25/26); the first milestone of an org migration (2026-09-28)
Before any IDMC work, derive the org in three calls and re-derive it every session instead of caching it: the v3 login (`userInfo.orgId`, `userInfo.orgName`, `userInfo.sessionId`, `products[].baseApiUrl`), `GET /api/v2/org` (the v2 id, `orgUUID`, parent and sub-orgs) and `GET /api/v2/agent` (an empty `[]` leaves entitlement unresolved, not absent). Record the org name, both id shapes, pod, domain label and base URL; guessing the pod was recorded as the most common way to lose an hour.

### L-AUTH-047  Prove which org the session is in with a live read before any destructive call
**Kind:** LAW · **Proven:** 2026-09-28 · **Evidence:** Cleanup receipts began with the live user/org/pod read (2026-09-28)
Before any delete or import, read the org live and compare it with the intended one: `GET /session-service/api/v1/session/User` returns `name` and `orgId` (its host was not recorded), and `GET /api/v2/org` returns `id` and `orgUUID`. Destructive scripts assert the expected id (`GET /api/v2/org` must return `id == <orgIdV2>`) before their first write and print a receipt line with user, org name, v2 id and pod. When someone asks mid-run which org is being changed, this read is the answer.

### L-AUTH-048  One org has two id shapes: 6 characters on v2, 22 characters on v3 and identity
**Kind:** GOTCHA · **Proven:** 2026-09-28 · **Evidence:** Read live from both planes (2026-07-26); V3API_016 with the 6-character id (2026-09-28)
The v2 plane reports a 6-character org id (`<orgIdV2>`) and prefixes every v2 object id with it, followed by a type code (`0B` connection, `08` agent, `25` runtime environment; `0Z` was seen on mapping tasks). The v3 and identity planes use a 22-character id (`<orgIdV3>`, returned as `orgUUID` by `/api/v2/org`). Both are correct for the same org. Use the 22-character form for `X-INFA-ORG-ID`, for CAI URN paths and the anonymous CAI tenant, and for licence lookups (`GET /public/core/v3/license/org/<id>` with the 6-character id returns `V3API_016`).

### L-AUTH-049  GET /api/v2/org returns the v2 id, orgUUID, parent and sub-orgs, but no job limit
**Kind:** ROUTE · **Proven:** 2026-09-28 · **Evidence:** Live reads (2026-07-26, 2026-09-23 and 2026-09-28)
`GET <serverUrl>/api/v2/org` with header `icSessionId` returns the v2 org id, name, `orgUUID`, parent, `subOrgs` and `subOrgLimit`, plus fields such as `maxLogRows` and `restApiSessionLimit`; it does not expose the monthly job limit. From a sub-org user, `GET /api/v2/org/<id>` returned `403 REPO_10404`, and `GET /public/core/v3/orgs/<id>` returned 404 on another org.

### L-AUTH-050  Sub-org membership is explicit per user and org switching is an admin action
**Kind:** GOTCHA · **Proven:** 2026-07-26 · **Evidence:** Probes as a sub-org user and as the parent-org admin (2026-07-26)
If a login lands in a different org than the one you were asked to work in, stop: every documented org-switch path returned 404, so reaching another org is an admin action, not something to route around. A parent-org admin could not read a child org's agents (`403 APP_13407`), and a sub-org user could not read `/api/v2/org/<id>` (`403 REPO_10404`).

### L-AUTH-051  Check the parent org before concluding that a sub-org lacks an entitlement
**Kind:** LAW · **Proven:** 2026-07-26 · **Evidence:** Parent listed 22 sub-orgs; the sub-org agent went from 1 to 22 engines (2026-07-26); 0 billed IPU on a sub-org whose runs succeeded (2026-07-04)
Sub-orgs can use capabilities allocated by the parent. One sub-org showed a single engine and no licence reads over REST while its parent ran 22 engines; enabling the services on the sub-org's own agent delivered all 22, an assignment rather than a purchase. Licence allocation to sub-orgs is a UI step (the parent's Administrator > Sub-Organizations > Licenses), a sub-org's runtime environments can be inherited from the parent and show zero agents, and trial or embedded sub-orgs were reported to accrue zero billed IPU while their jobs succeeded.

### L-AUTH-052  Do not bind a sub-org connection to the parent's shared runtime environment as a shortcut
**Kind:** GOTCHA · **Proven:** 2026-07-26 · **Evidence:** Bogus-host control returned the identical error (2026-07-26)
A sub-org connection bound to the parent's shared runtime environment creates fine (200), and its test error changes from `APP_105060` to `error [error [null]]`, which reads as progress but is not: an unroutable bogus host returns the identical error, so the result proves no reachability. Install an agent in the sub-org instead.

### L-AUTH-053  Two runtime environments in one org share every org-scoped object; isolation needs a second org
**Kind:** GOTCHA · **Proven:** 2026-07-06 · **Evidence:** Parity checks between two environments in one org reported in_parity (2026-07-06)
Catalog configuration, glossary, classifications, DQ rules, the MDM model and roles are org-scoped, so two runtime environments in one org share them by construction and there is nothing to mirror. Only RE-bound or duplicated objects can drift: agent versions, connections per environment (often name-mapped) and the mapping-task set. True isolation between environments needs a second IDMC org, which is a purchase.

### L-AUTH-054  One writer per org: only a lead session logs in to and imports into each org
**Kind:** PROCESS · **Proven:** 2026-09-28 · **Evidence:** An org cutover finished with no lockout and no duplicate import, after a morning in which 3 sessions had tried the same login (2026-09-28)
When several Claude sessions work the same program, name one lead that alone logs in to each IDMC org and alone imports or publishes; other lanes work host-side, on application repointing, or read-only, and coordinate by messages and board LEASE comments (owner, since, expires) with heartbeats and DONE-with-evidence posts. Announce every import first and never delete while an import runs.

### L-AUTH-055  Make the shared IDMC client org-aware when two orgs are in play
**Kind:** RECIPE · **Proven:** 2026-09-28 · **Evidence:** About 19 host files and the MCP clients flipped at cutover; org-aware wrapper tests 11/11 (2026-09-28)
Give the shared client one switch (an environment variable such as `IDMC_ORG=source|target`, else a switch file, else a default), a creds file, a session cache and a login host per org, and default it to the new org after a cutover so reads of the old org need an explicit login at its own domain. Scripts pinned to one org assert the selected org before any call, and a migration library can make the source org read-only (any non-GET raises unless explicitly overridden; export POSTs allowed). Flipping a host to the other org is then one write plus remapped id files.

### L-AUTH-056  An org that looked walled had full access; the real blocker was the missing Secure Agent
**Kind:** OVERTURNED · **Proven:** 2026-07-25 · **Evidence:** Login plus connection create/delete (2026-07-25)
A login landed directly in the org with its full privilege set (876 privileges, 38 roles), and connection create and delete both succeeded; the only blocker was that the org had no Secure Agent. Before calling an org inaccessible, log in, read the privileges and try a free create and delete.

### L-AUTH-057  Create a user with POST /public/core/v3/users: the key is name, groups are plain id strings
**Kind:** ROUTE · **Proven:** 2026-07-25 · **Evidence:** 201 live; 400 V3API_007 on userName (2026-07-05, 2026-07-25)
`POST https://<pod>.<domain>.informaticacloud.com/saas/public/core/v3/users` with header `INFA-SESSION-ID` and body `{"name":"<login>","firstName":"...","lastName":"...","email":"...","groups":["<groupId>"]}` returns 201. The identity key is `name` (`userName` returns `400 V3API_007`); `groups` is a list of plain id strings, not `[{"id":...}]` objects and not `userGroupIds`; the body needs at least one role or group (a name-only body returns `V3API_IDSError_033`). Read back with `GET /public/core/v3/users`.

### L-AUTH-058  DELETE /public/core/v3/users/{id} returns 204
**Kind:** OVERTURNED · **Proven:** 2026-09-28 · **Evidence:** 204 plus read-back, 29 users removed (2026-09-28)
`DELETE https://<pod>.<domain>.informaticacloud.com/saas/public/core/v3/users/<userId>` with header `INFA-SESSION-ID` returns 204 and removes the user; confirm with `GET /public/core/v3/users`. 29 users were removed this way in one org cleanup. Back up the user list first, and keep the system and service users (L-AUTH-061).

### L-AUTH-059  There is still no proven in-place user edit: change a user by delete and recreate
**Kind:** GOTCHA · **Proven:** 2026-07-25 · **Evidence:** 405 on PUT and PATCH (2026-07-05, 2026-07-25); 27 seats stranded then restored (2026-07-05)
PUT and PATCH on the users collection returned 405 in July 2026, and PUT/PATCH on the item were recorded as 405 too; in-place edit remains unproven after the September DELETE finding. To change a field over REST, delete and recreate the user (the Admin UI can edit in place). Snapshot the users before any batch delete and test the recreate body on one seat first: a wrong body once stranded 27 seats, which were restored from the snapshot.

### L-AUTH-060  Create groups and bind roles with POST /public/core/v3/userGroups; roles are role-id strings and cost nothing
**Kind:** ROUTE · **Proven:** 2026-07-25 · **Evidence:** 200 live; guessed bodies silently dropped bindings (2026-07-04, 2026-07-25)
`POST /public/core/v3/userGroups` with body `{"name":"<group>","roles":["<roleId>", ...]}` returns 200. Roles are plain role-id strings, not `[{"id":...}]` and not `roleIds`; guessed shapes silently dropped the role bindings, so read back with `GET /public/core/v3/userGroups?limit=200`. DELETE works; PUT and PATCH are untested. Groups and role bindings consume no seats and no IPU; only user seats are licensed.

### L-AUTH-061  Never delete CAI_Anonymous_<orgIdV3> or the service users that live automation uses
**Kind:** GOTCHA · **Proven:** 2026-09-28 · **Evidence:** Kept through a 29-user cleanup (2026-09-28)
Processes deployed with anonymous access run through the org's `CAI_Anonymous_<orgIdV3>` user; deleting it breaks every `/active-bpel/public/rt/<orgIdV3>/<process>` URL. Keep it, the automation user itself, and any service user that a live process, catalog scanner or OAuth client depends on (search the hosts for the user names first). Anonymous endpoints are open to anyone with the URL: acceptable for a demo, not for production writes.

### L-AUTH-062  Roles and privileges are readable over v3; the privilege list is the REST proxy for entitlement
**Kind:** ROUTE · **Proven:** 2026-07-25 · **Evidence:** 200 live (2026-07-25)
`GET /public/core/v3/roles` (for example 59 roles: 35 system and 24 custom; items carry `id` and `roleName`) and `GET /public/core/v3/privileges` (for example 897 effective privileges) return 200. Grep the privileges for a product's prefix before answering whether it is licensed, for example `create.dbmi.task`, `feature.cdam.*`, `create.mcp.CatalogSourceConfiguration` or `metering.admin`.

### L-AUTH-063  Roles that let one login deliver CDI, CAI, CDQ, CDGC, CLAIRE, migration and MCP work
**Kind:** RECIPE · **Proven:** 2026-09-24 · **Evidence:** Runbook prerequisite (2026-09-24); vendor MCP guide chapter 3 (2026-07-25)
A login that drives CDI, CAI, CDQ, CDGC governance and CLAIRE needs the Admin, Designer, Governance Administrator and CLAIRE GPT User roles; export and import additionally need the migration (export/import) and object-admin role. Managed MCP servers need the MCP Server and Deployed MCP Server asset privileges and the Execute and View Managed MCP Servers feature privileges, which the vendor guide says Admin and Designer hold by default (Operator can run servers but cannot create or set permissions on composite ones). Check these first in a new org.

### L-AUTH-064  Persona users with no role bindings give no separation of duties
**Kind:** SECURITY · **Proven:** 2026-07-06 · **Evidence:** User and role audit (2026-07-06)
Creating persona users (engineers, operators, platform admins, governance, MDM) does nothing for separation of duties if they hold no roles while one admin account holds everything. Bind roles per persona, through groups, especially when development and production runtime environments share one org.

### L-AUTH-065  For about 1,000 users plan SAML SSO with SCIM group provisioning, not native accounts
**Kind:** DECISION · **Proven:** design recommendation (2026-07-04), untested · **Evidence:** RBAC scale model (2026-07-04)
A 1,000-user access model concluded that native IDMC accounts do not scale to that size and recommended SAML SSO plus SCIM group provisioning, with roles bound to groups (groups and bindings are free; seats are licensed). Design recommendation; not tested.

### L-AUTH-066  PUT /public/core/v3/users/{id}/addRoles exists, but a successful add was never observed
**Kind:** ROUTE · **Proven:** route answered with a licence error (2026-09-24); success untested · **Evidence:** Helper code plus one recorded licence error (2026-09-24)
A helper read the user with `GET /public/core/v3/users?q=userName=="<login>"`, took role ids from `GET /public/core/v3/roles` and called `PUT /public/core/v3/users/<userId>/addRoles` with body `{"roles":["<roleId>"]}` and header `INFA-SESSION-ID`. The only recorded answer was the error "license status is not enabled" for the Monitor and Operator roles in a shared org, which shows the route is live; a successful add was never observed.

### L-AUTH-067  In a shared org some UI roles are licence-locked for the demo user
**Kind:** WALL · **Proven:** 2026-09-24 · **Evidence:** addRoles licence error and UI permission messages (2026-09-24)
In a shared presales org the demo user saw "insufficient permissions" on Monitor > All Jobs, Data Integration > My Jobs, Monitor > Application Integration and the Application Integration Console, and adding the Monitor or Operator roles failed with "license status is not enabled": the org's licence, not the user's roles, is the limit. Demonstrate with Monitor > Running Jobs, the Operational Insights dashboards and applications that read the job APIs directly.

### L-AUTH-068  403 MigrationSvc_038 is a permission gate; for Add-On Bundle templates it can persist
**Kind:** ERROR · **Proven:** 2026-09-29 · **Evidence:** 403 then 200 after the role grant (2026-07-05/06); bundle-template 403 on 2026-09-22 and 2026-09-29 but not on 2026-09-23
`403 MigrationSvc_038` "User does not have required permissions" on `POST /public/core/v3/export` is a permission gate, not a missing route or entitlement: an empty-body POST returns 400 (the route is writable), and granting the migration (export/import) and object-admin role, about a one-minute Administrator change, turned the 403 into 200. For Add-On Bundle templates such as `dsst__copy_data_new_tgt` and `dlt__copy_data` the 403 persisted for a non-admin user in some orgs and not in others (disputed); bundle content is system content, so create mapping tasks over the template rather than exporting it.

### L-AUTH-069  A CAI 403 on invoke is a per-process access list; other role gaps have their own signatures
**Kind:** GOTCHA · **Proven:** 2026-07-26 · **Evidence:** 403 persisted after a broad role grant (2026-07-06); CAI scheduler 401 beside JSON process lists (2026-07-26)
A 403 when invoking a published CAI process comes from that process's allowed users and groups (grant the Service Consumer role on the process); broad org roles, including the migration and admin roles, did not fix it. Other signatures of a role gap rather than a missing route: the CAI scheduler answering 401 while process lists answer JSON; MDM search returning `403 Authorization Client Error`; a CDQ dictionary host returning 401 on one pod (also recorded as not mounted there).

### L-AUTH-070  The login products[] list is a licensing label, not the entitlement map
**Kind:** OVERTURNED · **Proven:** 2026-09-23 · **Evidence:** 59 roles, 897 privileges and 88 feature flags with products listing Integration Cloud only (2026-07-09); selections enabled for CAI, DBMI and governance (2026-09-23); CDGC writes in such an org (2026-09-28)
The v3 login `products[]` list can name only "Integration Cloud" while the org is entitled to CAI, Database Ingestion, CDGC, MDM, DAM, CDQ, CLAIRE GPT and hundreds of connector types. Read entitlement instead from the identity-service Login (roles, `effectivePrivileges`, `feature.<cap>.*` flags), the licence service `EffectiveLicenses()`, `agentEngines[]` per agent, the runtime-environment service selections, the managed MCP registry, the console app switcher, and whether a real create call validates.

### L-AUTH-071  Deployed engines, not a 404, decide what an org can run
**Kind:** LAW · **Proven:** 2026-07-05 · **Evidence:** agentEngines[] listed DBMI, DAM and CAI engines running while the 404s were wrong paths (2026-07-05)
Never infer entitlement from a 404 or from `products[]`. The ground truth for deployed capability is `GET <serverUrl>/api/v2/agent/details/<agentId>` with `agentEngines[].agentEngineStatus.appname` on every agent (a fully enabled agent ran 17 engines, a base agent 8); earlier "not provisioned" verdicts for Database Ingestion, DAM, the CAI Process Server and API Manager came from wrong paths. With no agent installed, entitlement is unresolved, not disproven.

### L-AUTH-072  Read effective licences from the licence service; its limits read -1 and hide the job cap
**Kind:** ROUTE · **Proven:** 2026-09-28 · **Evidence:** Readouts in two orgs (2026-09-28); the console's licence call confirmed MDM (2026-07-06)
`GET https://<pod>.<domain>.informaticacloud.com/license-service/api/v1/OrgLicenseAssignment('<orgIdV3>')/EffectiveLicenses()` with `IDS-SESSION-ID: <v2 icSessionId>` and `Accept: application/json` returns `active[]` (id, name) and `limits{}`. The console calls it, and it confirmed MDM and CLAIRE GPT entitlements that `products[]` omitted. Every limit read -1 (32 in one org, 76 in another), including in an org that had just hit a 10,000 jobs/month cap, so the job cap cannot be read here.

### L-AUTH-073  v3 license/org needs the 22-character id; there is no licence inventory route on some orgs
**Kind:** ROUTE · **Proven:** 2026-09-28 · **Evidence:** Live reads (2026-07-25/26 and 2026-09-28)
`GET /public/core/v3/license/org/<orgIdV3>` returned per-org licence detail (200; trial licences came without names and `customLimits=[]`), while the 6-character id returned `V3API_016`. There was no licence inventory route on a sub-org: `/public/core/v3/licenses` returned `404 No static resource`, `/api/v2/license` 404 (200 on another org) and `/api/v2/org/<id>/license[s]` 404. Read the inventory in Administrator > Organization > Licenses, or for a sub-org in the parent's Sub-Organizations > Licenses.

### L-AUTH-074  Establish entitlement ground truth in six reads and classify each capability
**Kind:** RECIPE · **Proven:** 2026-09-28 · **Evidence:** Procedure used to correct about 90 false licence escalations (2026-07-06) and re-applied in September orgs (2026-09-23/28)
(1) Identity-service Login: roles, `effectivePrivileges`, `feature.<cap>.*` flags. (2) `GET /api/v2/agent/details/<agentId>` on every agent: engines and their status. (3) Runtime-environment selections: which services are enabled. (4) Licence service `EffectiveLicenses()`: active licences. (5) v3 object counts per type, as content only, because the `q=type==` filter is not validated. (6) A free create call that validates. Then classify each capability as HEADLESS (REST works), UI-ONLY (provisioned, no REST write) or PURCHASE (engine and privilege genuinely absent).

### L-AUTH-075  Audit logs: v3 securityLog is canonical; the v2 audit resources vary by org
**Kind:** ROUTE · **Proven:** disputed (2026-07-25/26) · **Evidence:** Conflicting live records (2026-07-25/26); no cap-change entry (2026-09-28)
`GET /public/core/v3/securityLog?limit=N` (N from 100 to 1,000) is the canonical audit log (200). `GET /api/v2/loginAudit` answered only on a parent or standalone org (404 on a sub-org). `GET /api/v2/auditlog` is disputed: one table records 404 ("superseded by securityLog") and another records it live on both orgs probed; it also did not record a job-cap change.

### L-AUTH-076  API coverage is uneven: write is weakest, catalog and MDM are richest
**Kind:** LAW · **Proven:** 2026-07-14 · **Evidence:** consistent with this KB's API route corpus and probes (see knowledge/12-reference-library)
The public API surface is incomplete and write coverage is its weakest part: catalog and MDM expose richer APIs than integration, while Data Integration exposes mainly operational APIs (schedule, monitor, logs, status). Routes fall into three tiers (documented public, undocumented but used by the UI, gated), and REST coverage is wider than MCP. Mapping design over API or MCP is not a documented public capability; the design gap is worked around by cloning tasks and by package import (see the CDI headless routes).

### L-AUTH-088  v3 routes answer 401 to a v2 session header, and wrappers can hide it as 'no objects'
**Kind:** GOTCHA · **Proven:** 2026-09-30 · **Evidence:** 401 reproduced; an empty inventory traced to a swallowed 401 (2026-09-30)
`/public/core/v3/...` routes need `INFA-SESSION-ID: <v3 session>`. Sending the v2 `icSessionId` returns 401 'API request does not contain a valid INFA-SESSION-ID'. A helper that returns an empty list for any non-dict body turns that 401 into '0 objects'. Check the status code before trusting an empty result, and cross-check one object you know exists.

### L-AUTH-089  Object permissions over REST: read, add and remove access-control entries on projects, assets, connections and runtime environments
**Kind:** RECIPE · **Proven:** 2026-10-13 · **Evidence:** 201 + read-back + 204 on a probe connection; 972 entries written on 81 objects (projects, assets, connections, runtime environments) and read back (2026-10-13)
`GET /saas/public/core/v3/objects/<frsId>/permissions` returns the object's access-control list; `[]` means no restriction (anyone whose roles allow the type). `POST` to the same path with `{"principal":{"type":"USER"|"GROUP","name":"<user name or group name>"},"permissions":{"read":true,"update":true,"delete":true,"execute":true,"changePermission":true}}` returns 201 and a list holding the new entry with its `id`; the same principal given by `id` instead of `name` gets a bare 400 V3API_007. `DELETE .../permissions/<entryId>` returns 204. Connections and runtime environments take their v2 `federatedId`; a catalog-source UUID is refused with 400 V3API_AccessControlError_001. The first entry restricts the object to the listed principals, so add the owner first, and list the CAI anonymous user too or CAI processes cannot run the restricted tasks (vendor Asset Management guide). An empty body names the missing parts (`principal`, then `permission`). Writes took about one second each.

### L-AUTH-090  Role, group and membership writes: the 'must not be empty' message names the Java field, not the JSON property
**Kind:** GOTCHA · **Proven:** 2026-10-13 · **Evidence:** role create 400 with privilegeIds, 201 with privileges; group create and addUsers 400 with the validator's names, 201/204 with roles/users; removeGroups by name 204; removeRoles of all six direct roles 400 IDSError_044, then addRoles + removeRoles by name 204 (2026-10-13)
`POST /public/core/v3/roles` answers "Field 'privilegeIds' must not be empty", yet a body with `privilegeIds` gets a bare 400 V3API_007; the JSON property is `privileges`, a list of privilege ids (read them with `GET /roles?q=roleId==%22<id>%22&expand=privileges`; 'Default'-status privileges are accepted) -> 201. In the same way `POST /userGroups` names 'roleIds' but takes `roles` (role ids), and `PUT /userGroups/<id>/addUsers` names 'userNames' but takes `users` (user names) -> 204. `PUT /users/<id>/removeRoles` and `/addRoles` take `roles` as role NAMES (a bad value is reported as 'name is invalid'), `/removeGroups` and `/addGroups` take `groups` as group names. A user must keep one direct role: removing the last one answers 400 V3API_IDSError_044 "The group must have at least one role" (it means the user), so add the new role before removing the old ones. When a correctly named body gets a bare V3API_007, drop the Ids/Names suffix. In `q=` filters, URL-encode the double quotes and spaces (`roleName==%22Data%20Viewer%22`).

### L-AUTH-091  Limit one user to one project: a view-and-run role, a group, and object permissions on everything else for everyone else
**Kind:** PATTERN · **Proven:** 2026-10-13 · **Evidence:** applied on an org with 27 projects, 58 connections and 4 runtime environments: 81 objects x 12 principals, read back; undo = DELETE of the logged entry ids plus the role and group writes (2026-10-13)
Role privileges cap what a user can do; object permissions cap which objects the user sees. (1) Build a custom role from the view and execute privileges of the system roles Data Integration Task Executor and Monitor (DI, DQ, Profile and Monitor services plus Admin view.project, view.folder, view.connection, view.agent, view.agent.group; no schedule, CAI, catalog, MDM, Marketplace or CLAIRE privileges) and a group that holds it. (2) On every other project, connection and runtime environment, add entries with all five permissions for every other group, every other named user and the CAI anonymous user, which keeps everyone else's access as it was. (3) Remove the user's other groups and direct roles and add the new group. Leave the target project, its connections and its runtime environments without entries (the role already limits the user to view and run there). Installed-app projects (MDM) and system content can stay open when the role cannot list their asset types; restrict only the viewable assets inside them. Snapshot users, groups and every list first, and log each entry id for the undo.

### L-AUTH-092  An unlock does not stick while a scheduled client still holds the old password: find it from the failed-login cadence in the security log
**Kind:** GOTCHA · **Proven:** 2026-10-19 · **Evidence:** failed-login cadence matched a */5 cron; after updating 3 copies and re-enabling: 0 failures, all runs green (2026-10-19)
After a password reset, an IDMC user re-locked (IDS_086) minutes after an admin unlock. GET /public/core/v3/securityLog?limit=100..1000 (limit below 100 is a 400) showed USER_LOGIN_FAILED by 'System built-in user' twice every 5 minutes at hh:m0:02 and hh:m5:02, then ACCOUNT_LOCKED: the fingerprint of a */5 cron that logs in twice per run. Comparing SHA-256 prefixes of the stored passwords (never the values) located every copy of the stale one: a monitor's env file, a container env_file (needs a container recreate, not just a file edit), and a CAI app connection secret (asset/v1/update, then republish the connection). Pause the scheduled client first, then unlock, then update every copy, then re-enable; confirm with zero USER_LOGIN_FAILED afterwards. Prefer a dedicated integration user so a person's password reset cannot lock the automation.

### L-AUTH-093  The Tableau V3 writer prints the Tableau REST session token in the mapping session log
**Kind:** GOTCHA · **Proven:** 2026-10-21 · **Evidence:** Session log of a successful publish run shows the token line (2026-10-21)
At INFO level the Tableau V3 writer logs 'Tableau Rest Runner: User logged in.' followed by 'Session token: <token>' and the site id in clear text. Anyone who can download the session log (GET /api/v2/activity/activityLog/<id>/sessionLog, L-CDI-211) can reuse that session until it expires. Treat Tableau V3 session logs as secret-bearing: restrict who can read them, do not attach them to tickets unredacted, and prefer a dedicated Tableau user with publish rights only on the target project.

### L-AUTH-094  Activity-log and v2 local times are UTC-4 on a US west pod too: the offset is not the pod's zone, so always read the *Utc fields
**Kind:** OVERTURNED · **Proven:** 2026-10-19 · **Evidence:** Activity-log rows read 2026-10-18/19 on a usw1 org: endTime - endTimeUtc = -4 h on every row
On a us-west pod (usw1) the activity-log `startTime`/`endTime` still read 4 hours behind `startTimeUtc`/`endTimeUtc` with a 'Z' suffix, the same offset as on an east pod, so the offset is not pod-local time (and not Pacific time either, as an earlier note assumed). Never derive the offset from the pod: use `startTimeUtc`/`endTimeUtc` for completion and durations, and re-check schedules' startTime against startTimeUTC after any daylight-saving change. Refines L-AUTH-014.

### L-AUTH-095  Each IDMC user carries its own lockout threshold (maxLoginAttempts): read it before pointing automation at a user
**Kind:** FACT · **Proven:** 2026-10-19 · **Evidence:** Users read-back in a new org (2026-10-19)
`GET /public/core/v3/users` returns `maxLoginAttempts` per user, as a string, and it differs inside one org: a newly created admin user had '3' while another admin had '10' and the CAI anonymous user '3'. With 3, one stale stored password in a */5 job locks the user within minutes (IDS_086, L-AUTH-092). Check the value of any user that unattended jobs will use, raise it where policy allows, and keep people's interactive users out of automation.

### L-AUTH-096  Creating an IDMC org through the Azure Native ISV service first fails on the Entra user profile and on a Marketplace purchase block
**Kind:** GOTCHA · **Proven:** 2026-11-10 · **Evidence:** Profile fields saved and read back through Graph; plan 'Informatica CDI' isFree true, isPayg false, price $0, no payment method required; Marketplace re-blocked after every attempt (2026-11-10)
The create validation rejected the user with 'Business Phone Number is not in the expected format (10-25 characters...). CompanyName is empty. Country is empty', then with 'Marketplace is not enabled for the Azure subscription'. Fill business phone, company and country on the Entra user (Graph), and switch the billing profile's Marketplace purchase policy from NotAllowed to AllAllowed only for the attempt: Sponsorship-type credits do not cover Marketplace, so any other Marketplace purchase made meanwhile bills the card. Confirm the plan is the free one before creating, and block purchases again afterwards (verify 0 Marketplace subscriptions remain).

### L-AUTH-097  Azure Native IDMC org create from the CLI: the informatica extension, the free plan's own term id, a managed identity and an Informatica Region
**Kind:** RECIPE · **Proven:** 2026-11-10 · **Evidence:** Request passed Azure validation and reached provisioning once the term id, identity and region were set (2026-11-10)
Use `python -m azure.cli informatica data-management organization create -g <rg> -n <name> -l <region> --company-details @company.json --user-details @user.json --marketplace-details @mkt.json` (in git-bash call azure.cli through python, L-ENV-016). The marketplace offer is publisher informatica, offer prod-idmc_as_azure_native_isv_service, plan idmc_ans_public ('Informatica CDI'); the term id must be the plan's own (read it from the offer's plan availabilities), a guessed term fails validation. The newer API version also needs a managed identity and an Informatica Region, which no Azure API lists (the portal shows a dropdown); the company 'business' field is the business type, and country takes 'USA'. Register the Microsoft.SaaS and Microsoft.Marketplace resource providers first (free; a documented cause of ISV signup failures).

### L-AUTH-098  Azure Native IDMC signup: 'Partner signup failed ... Unexpected error occurred' on every variation from a personal-account Sponsorship tenant
**Kind:** WALL · **Proven:** 2026-11-10 · **Evidence:** Failures across 3 Azure regions, 3 Informatica Region values, 3 emails, plain and #EXT# UPN, link to an existing org; 0 charges; all test resources deleted (2026-11-10)
Once Azure-side validation passed, every create or link-existing-org attempt failed about 1-4 minutes in, inside Informatica's signup step, with 'Object reference not set to an instance of an object' or 'Partner signup failed ... Unexpected error occurred. Please try again later' and no detail. Varying Azure region, Informatica Region value, email (personal, plus-alias, corporate domain), UPN form, company domain and new-versus-link did not change it; Owner role, complete profile, accepted terms and registered providers were all in place. The likely trigger is the tenant type (a personal Microsoft account in a default directory on a Sponsorship subscription), unconfirmed. Do not keep retrying: send the operation ids to Informatica's Azure Native team, or use a company Entra tenant with a pay-as-you-go or enterprise subscription; existing IDMC orgs remain the free route.

### L-AUTH-099  v3 userGroups and roles lists cap limit at 200 (V3API_IDSError_003); there is no get-by-id for users or groups
**Kind:** GOTCHA · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence high: code plus its tests, change notes or live-check notes); not probed here
`GET /public/core/v3/userGroups?limit=1000` and `/roles?limit=1000` answer 400 `V3API_IDSError_003` 'Invalid value in limit parameter: must be between 0 and 200'; page with `limit=200&skip=<n>` (the client pages users at 200 too). `GET /public/core/v3/users/<id>` is 405 with `Allow: DELETE`; fetch one user with `q=userId==<id>` or `q=userName==<name>` (the only filterable fields, exact match). userGroups has no get-by-id or by-name route either: filter with `q=userGroupName=="<name>"` or scan the pages. Role details come from `GET /public/core/v3/roles?q=roleName=="<name>"&expand=privileges` (`/roles/<id>` is not a route).

### L-AUTH-100  v2 user update by v3 user id fails 403 REPO_10704; change users only through v3 membership PUTs
**Kind:** ERROR · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence medium: code only); not probed here
`POST /api/v2/user/<v3 userId>` (legacy v2 update, XML) answered 403 `<code>REPO_10704</code>` 'Internal error. An error occurred while loading the user.' for a freshly created, not yet activated user (earlier testing saw 400). In-place scalar edits (name, email, time zone) stayed unavailable; group and role changes work through `PUT /public/core/v3/users/<id>/addGroups|removeGroups|addRoles|removeRoles`. Roles a user already gets from a group need no direct assignment. Refines L-AUTH-059.

### L-AUTH-101  Object ACLs: PUT /permissions/<aclId> updates, DELETE /permissions clears all, GET /permissions/checkAccess reports your own rights
**Kind:** ROUTE · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence high: code plus its tests, change notes or live-check notes); not probed here
Beyond list/add/delete-one, the v3 object-permissions resource has: `PUT /public/core/v3/objects/<id>/permissions/<aclId>` with the same `{principal:{type,name},permissions:{read,update,delete,execute,changePermission}}` body to replace one entry; `DELETE /public/core/v3/objects/<id>/permissions` to remove every entry (back to unrestricted); `GET /public/core/v3/objects/<id>/permissions/<aclId>` for one entry; and `GET /public/core/v3/objects/<id>/permissions/checkAccess[?type=<asset type>]`, which returns the caller's own permissions including `create` (whether that asset type can be created in a project or folder). A duplicate add for the same principal is rejected. POST may return an array or a single object; accept both. Refines L-AUTH-089.

### L-AUTH-102  Retry policy for IDMC REST: one re-login on 401, bounded 429 backoff, resend only read-only calls after a dropped connection
**Kind:** PATTERN · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence high: code plus its tests, change notes or live-check notes); not probed here
A maintained client does: on 401, log in once and resend; if that login fails, stop and tell the user (never loop, to avoid lockout). On 429, wait `Retry-After` (seconds or HTTP date) or `ratelimit-reset` (seconds), capped at 60 s, up to 3 times; Informatica documents neither header for v3, so without one back off 2, 4, 8 s plus up to 25% jitter. On EOF or connection reset (IDMC drops connections now and then in long call runs) resend only GETs and read-only POSTs such as `/public/core/v3/lookup`, at most twice (1 s, 2 s); never resend writes, which may already have been applied. A lookup still rate-limited after retries should leave the asset in the deploy set rather than drop it.

### L-AUTH-103  Login host per region code (v3 login URL table)
**Kind:** FACT · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence medium: code only); not probed here
`POST https://<login host>/saas/public/core/v3/login`, where the login host by region is: US, USE2, USE4, USE6, USW1, USW3, USW5 -> dm-us; USW1-1, USW3-1 -> dm1-us; USW1-2 -> dm2-us; CAC1 -> dm-na; EMEA, EMWE1 -> dm-em; EMC1 -> dm1-em; UK1 -> dm-uk; APJ, APSE1 -> dm-ap; APNE1 -> dm1-ap; APNE2 -> dm-apne; APSE2 -> dm1-apse; APAUC1 -> dm1-apau (all `.informaticacloud.com`). The org's working host is still the `products[].baseApiUrl` the login returns, not this table.

### L-AUTH-104  Removing a role from a group's last role, or a user's last direct role, is refused; the v3 error codes
**Kind:** ERROR · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence high: code plus its tests, change notes or live-check notes); not probed here
`PUT /public/core/v3/users/<id>/removeRoles` that would leave the user with no direct role fails 400 `V3API_IDSError_048` 'Failed to remove role(s) from the user <id>' wrapping `V3API_IDSError_044` 'The group must have at least one role' - IDMC keeps a user's direct roles in a hidden per-user group, whatever roles their user groups grant. `PUT /userGroups/<id>/addRoles|removeRoles` take `{"roles":[<role names>]}` and `addUsers|removeUsers` take `{"users":[<user names>]}`; a group must keep at least one role. Refines L-AUTH-090.

### L-AUTH-105  Role privilege edits: PUT addPrivileges/removePrivileges take privilege NAMES and return 204; create takes ids; a role must keep at least one privilege
**Kind:** GOTCHA · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence high: code plus its tests, change notes or live-check notes); not probed here
`POST /public/core/v3/roles` takes `privileges` as privilege ids, but `PUT /public/core/v3/roles/<roleId>/addPrivileges` and `/removePrivileges` take `{"privileges":["<privilege name>",...]}` with names such as `view.auditLog`, and answer 204. Three independent clients (a Python CLI, a Python SDK, a Terraform provider that translates ids into names before the call) do this. The vendor spec says removePrivileges cannot strip the last privilege, so add before you remove. An idempotent reconcile diffs the desired privilege set against `GET /roles?q=roleId=="<id>"&expand=privileges`, adds what is missing, then removes the extras. Rename or describe changes need a delete and recreate (the provider marks name and description ForceNew).

### L-AUTH-106  GET /public/core/v3/privileges hides disabled and unlicensed privileges unless q=status==All
**Kind:** GOTCHA · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence medium: code only); not probed here
`GET /public/core/v3/privileges` returns only the privileges the org can currently use. `?q=status==All` adds the Disabled (expired licence) and Unassigned (never licensed) ones. Each item has `id`, `name`, `description`, `service` and `status` (Enabled, Disabled, Unassigned, Default). Use the default list when you judge whether a feature is licensed, and the All list when you map privilege names to ids for role definitions that must also work in a differently licensed org. Refines L-AUTH-090.

### L-AUTH-107  Roles can be addressed by name: /public/core/v3/roles/name/<roleName>/addPrivileges and /removePrivileges
**Kind:** ROUTE · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence low: a comment or README claim); not probed here
Besides `/roles/<roleId>/...`, the SDK calls `PUT /public/core/v3/roles/name/<roleName>/addPrivileges` and `.../removePrivileges` with `{"privileges":["<privilege name>"]}`, which saves a lookup when a role's name is stable across orgs and its id is not. URL-encode role names that contain spaces. Untested in the SDK (no tests cover it).

### L-AUTH-108  SAML group and role mappings over REST: Orgs/<orgId>/SAMLConfig/{groupMappings,roleMappings} and add/removeSamlGroupMappings
**Kind:** ROUTE · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence medium: code only); not probed here
`GET /public/core/v3/Orgs/<orgId>/SAMLConfig/groupMappings?limit=200&skip=0` and `.../SAMLConfig/roleMappings` list the SSO mappings. `PUT /public/core/v3/Orgs/<orgId>/addSamlGroupMappings` with `{"groupMappings":[{"roleName":"<IDMC role>","samlGroupName":["<IdP group>"]}],"reuseGroup":true}` adds mappings (204). `reuseGroup:false` creates a new IDMC group instead of reusing one with the same name as the SAML group. `PUT .../removeSamlGroupMappings` with `{"groupMappings":[...]}` removes them (204). `<orgId>` is `userInfo.orgId` from the v3 login. Vendor documentation bundled in another repository gives the body fields as plural arrays (`samlGroupNames`, `samlRoleNames`): L-AUTH-129, not probed here.

### L-AUTH-109  Read the org's trusted IP ranges with GET /public/core/v3/Orgs/<orgId>/TrustedIP
**Kind:** ROUTE · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence low: a comment or README claim); not probed here
`GET /public/core/v3/Orgs/<orgId>/TrustedIP` with `INFA-SESSION-ID` returns the org's trusted IP address ranges (`<orgId>` = `userInfo.orgId` from the v3 login). Check it before running automation from a new egress IP, because logins from outside the ranges are refused. Only the read is implemented and it has no tests; no write verb was seen.

### L-AUTH-110  User password routes: POST /public/core/v3/Users/ChangePassword and /Users/ResetPassword
**Kind:** ROUTE · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence medium: code only); not probed here
`POST /public/core/v3/Users/ChangePassword` with `{"userId":"<id>","oldPassword":"<old>","newPassword":"<new>"}` changes a password. `POST /public/core/v3/Users/ResetPassword` with `{"userId":"<id>","securityAnswer":"<answer>","newPassword":"<new>"}` resets it with the security answer. Note the capital U in `Users`. Rotating a service user's password this way still needs every stored copy updated (see the lockout lessons).

### L-AUTH-111  v3 user create accepts forcePasswordChange, maxLoginAttempts, authentication (0 native, 1 SAML), aliasName, roles and groups
**Kind:** FACT · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence medium: code only); not probed here
`POST /public/core/v3/users` takes `name`, `firstName`, `lastName` and `email`, plus optional `password` (empty: the user gets an activation email; at most 255 characters), `description`, `title`, `phone`, `forcePasswordChange`, `maxLoginAttempts`, `authentication` (0 native, 1 SAML), `aliasName`, `roles` (role ids) and `groups` (group ids). Set `maxLoginAttempts` on service users when you create them, rather than finding a low default later. Refines L-AUTH-095.

### L-AUTH-112  securityLog q= filter: entryTime range joined by 'and', other fields appended with ';', window at most 14 days
**Kind:** RECIPE · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence medium: code only); not probed here
`GET /public/core/v3/securityLog?limit=100&skip=<m>&q=entryTime>="<ISO ms Z>" and entryTime<="<ISO ms Z>";actionCategory=="<cat>";actor=="<user>";objectName=="<name>"` filters server-side, and the results are under `entries[]`. The CLI's help says the date range is at most 14 days, so split longer audits into 14-day windows. Page with skip until `entries` is empty. Refines L-AUTH-075.

### L-AUTH-113  Two error envelopes: v2 {@type:error,code,description,statusCode} vs v3 {error:{code,message,requestId,details}}
**Kind:** FACT · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence medium: code only); not probed here
v2 routes return errors such as `{"@type":"error","code":"UI_10000","description":"...","statusCode":403}`. v3 routes return `{"error":{"code":"IDS_085","message":"...","requestId":"<id>","details":[...]}}`. Parse both shapes in one error handler, and log `requestId` for support tickets.

### L-AUTH-114  Detect the JWT switch from the token's shape and refresh before exp
**Kind:** PATTERN · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence medium: code only); not probed here
No org field shows whether the org issues JWTs or session ids (the v2 org record has no auth-type field). A token with three base64url segments whose payload decodes to a dict is a JWT. Read `exp` without verifying the signature (a scheduling decision, not authorization) and re-login 60 s before it. Persist the last-seen mode and alert once when it flips: a parent-org admin can flip it. Under JWT, also treat 403 from active-bpel and dbmi as possible expiry (re-auth once). Under session ids, keep 403 failing fast. Refines L-AUTH-032.

### L-AUTH-115  Sending the token in three session headers breaks at JWT size: route one header per path family
**Kind:** GOTCHA · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence medium: code only); not probed here
A client that sends the same token as INFA-SESSION-ID, icSessionId and IDS-SESSION-ID costs about 6.2 KB per request once the token is a JWT (measured: 2,075 chars x 3). That approaches the 8 KB default header limit of nginx and many load balancers. Send one header per path family: v3 INFA-SESSION-ID, v2 icSessionId, mftsaas, dbmi and identity IDS-SESSION-ID. Probe active-bpel before trimming it. Under JWT, v2 logout revokes nothing (stateless): rely on a short TTL. Refines L-AUTH-033.

### L-AUTH-116  An org guard after every login accepts both org-id forms and fails closed
**Kind:** SECURITY · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence high: code plus its tests, change notes or live-check notes); not probed here
When prod and dev share a login URL, the credential alone decides the org. After each login, compare against an expected org id. Accept either form: v3 login reports the 22-character orgUUID, while v2 login and `GET /api/v2/org` report the short orgId (the org record carries `orgId`, `id` and `orgUUID`). Call /api/v2/org directly, not through the retrying wrapper, so a 401 cannot recurse into login. If the org cannot be proven, discard the session and raise. Refines L-AUTH-047.

### L-AUTH-117  Check a v2 session before reuse: POST /api/v2/user/validSessionId
**Kind:** ROUTE · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence high: code plus its tests, change notes or live-check notes); not probed here
POST <serverUrl>/api/v2/user/validSessionId with header icSessionId and body {"@type":"validatedToken","userName":"<user>","icToken":"<sessionId>"} returns isValidToken and timeUntilExpire (minutes). A long-running client calls it at most every few minutes and re-logs in only when isValidToken is false, which avoids a login per request.

### L-AUTH-118  Log in to IDMC with an identity-provider JWT: POST /ma/api/v2/user/loginOAuth
**Kind:** ROUTE · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence medium: code only); not probed here
POST https://<login-host>/ma/api/v2/user/loginOAuth with {"orgId":"<orgId>","oauthToken":"<jwt>"} exchanges a short-lived JWT from the org's identity provider (obtained by ROPC from Okta, Entra ID and the like) for a v2 session; the response has the v2 login shape (serverUrl, icSessionId). It needs SAML configured org-wide. A monitoring vendor's agent uses it as the non-password mode beside v2 /ma/api/v2/user/login and v3 /saas/public/core/v3/login.

### L-AUTH-119  Role assignment to users matches the role's displayName, not roleName; SAML-mapped orgs reject the change
**Kind:** GOTCHA · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence high: code plus its tests, change notes or live-check notes, or vendor documentation bundled in the repository); not probed here
`PUT /public/core/v3/users/<id>/addRoles` and `/removeRoles` with `{"roles":[...]}` match the role's `displayName` (for example 'Data Integration Data Previewer'), not its `roleName` ('Data Preview'); sending roleName fails for every role whose two names differ. Read both fields from `GET /public/core/v3/roles` and send `displayName` when it is set, else `roleName`. Roles a user already gets from a group need not be added directly, and a user must keep one direct role (L-AUTH-104). The client's docs add that the API refuses role and group assignment changes when the org maps SAML groups and roles. Refines L-AUTH-090.

### L-AUTH-120  v3 user groups: create once, then change only membership; name and description are immutable, no GET or PUT by id
**Kind:** ROUTE · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence high: code plus its tests, change notes or live-check notes, or vendor documentation bundled in the repository); not probed here
Verified live: `POST /public/core/v3/userGroups` with `{"name":"<group>","description":"<text>","roles":["<roleId>",...],"users":["<userId>",...]}` (roles required and non-empty); `GET /userGroups/<id>` and `PUT /userGroups/<id>` both answer 405 (the path allows only DELETE), so read through the list with `q=userGroupName=="<name>"`. `DELETE /public/core/v3/userGroups/<id>` deletes. Membership changes only through `PUT /userGroups/<id>/addRoles|removeRoles` (`{"roles":[<role names>]}`) and `addUsers|removeUsers` (`{"users":[<user names>]}`), adding before removing. A group's name and description cannot be changed after creation: to rename, create a new group, move members and roles, delete the old one.

### L-AUTH-121  A role cannot be left without privileges: V3API_IDSError_088
**Kind:** ERROR · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence medium: code or a guide); not probed here
`PUT /public/core/v3/roles/<id>/removePrivileges` (or `/roles/name/<name>/removePrivileges`) that would leave the role with no privileges fails with `V3API_IDSError_088`, and `POST /public/core/v3/roles` needs a name and at least one privilege id. The v3 Roles API has no general update: the only change to an existing custom role is adding or removing privileges, so add the replacement privileges first, then remove. An org exposes 600+ privileges (625 across 19 services in one dev org). Refines L-AUTH-105.

### L-AUTH-122  v2 audit log pages with batchSize and batchId, newest batch first; default is the latest 200 entries
**Kind:** ROUTE · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence medium: code or a guide); not probed here
`GET /api/v2/auditlog` (header `icSessionId`) returns the most recent 200 entries when called without parameters; page with `batchSize=<n>` and `batchId=<k>`, where batchId is a 0-based batch number and 0 is the newest batch. Rows carry `id`, `username`, `category` (AGENT, AUTH, CONNECTION, USER...), `event` (CREATE, DELETE, UPDATE, RUN, PUBLISH...), `eventParam` (up to 1,024 characters), `objectId`, `objectName`, `entryTime`, `entryTimeUTC`, `message`, `orgId` and `version`. It covers object and admin actions, while securityLog is the v3 canonical log; probe the route on your org first, since L-AUTH-075 records it as 404 on some orgs.

### L-AUTH-123  End a v3 REST session with POST /saas/public/core/v3/logout; the vendor connector sends the wrong header
**Kind:** ROUTE · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence medium: code or a guide); not probed here
`POST <loginHost>/saas/public/core/v3/logout` (equivalently `<baseApiUrl>/public/core/v3/logout`) with an empty body and the header `INFA-SESSION-ID: <sessionId>` ends the session. The vendor's 2018 IICS REST API service connector binds this action with an `IDS-SESSION-ID` header although its own description says INFA-SESSION-ID; a later community V3 connector inherits `INFA-SESSION-ID` from its base POST action. Use INFA-SESSION-ID, log out at the end of every CAI process that logs in, and do not reuse a session after logout.

### L-AUTH-124  Treat 403 with error.code AUTH_01 as an expired session, like 401
**Kind:** GOTCHA · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence medium: code or a guide); not probed here
A maintained IDMC ingestion client classifies an auth failure as HTTP 401 or HTTP 403 whose v3 envelope has `error.code == "AUTH_01"`, and on either logs in again once and resends. A plain 403 with any other code is a real permission error and must not trigger a relogin loop. Add AUTH_01 to the relogin trigger of L-AUTH-102.

### L-AUTH-125  JWT-authentication orgs return a JWT as the session id: allow up to 16,000 characters and re-auth before expiry
**Kind:** FACT · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence high: code plus its tests, change notes or live-check notes, or vendor documentation bundled in the repository); not probed here
An org admin can set the org's REST authentication type to Session ID (30 minutes idle expiry plus up to a 2-minute grace) or JWT. Under JWT the 'session id' returned by v2/v3 login is a JWT, so the documented maximum session-id length is 16,000 characters; size header buffers, DB columns and log masks for that. Scripts must re-authenticate before the JWT expires rather than relying on idle refresh. The header name is still icSessionId (v2), INFA-SESSION-ID (v3) or IDS-SESSION-ID (other services).

### L-AUTH-126  validSessionId: timeUntilExpire drops to 0 under one minute; re-login at 0, not at isValidToken=false
**Kind:** GOTCHA · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence high: code plus its tests, change notes or live-check notes, or vendor documentation bundled in the repository); not probed here
`POST <serverUrl>/api/v2/user/validSessionId` body {"@type":"validatedToken","userName","icToken":<session id or JWT>} returns timeUntilExpire in whole minutes and isValidToken. The vendor note: timeUntilExpire becomes 0 when less than one minute remains, and isValidToken only turns false after expiry, so re-authenticate when timeUntilExpire is 0. The same call validates JWT-type sessions. Refines L-AUTH-117.

### L-AUTH-127  REST rules: no session header on login/register, @type only on v2 JSON, POST is full-replace unless partial mode
**Kind:** GOTCHA · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence high: code plus its tests, change notes or live-check notes, or vendor documentation bundled in the repository); not probed here
Vendor rules: do not send icSessionId or INFA-SESSION-ID on login and register calls; resources and attributes are case-sensitive; JSON is the default when Content-Type/Accept are absent (v2 also takes XML, whose lists come wrapped in <root>). `@type` may be used in v2 JSON bodies but must not appear in v3 bodies. v2 POST updates are full mode: omitted fields are reset unless the resource supports JSON partial mode (few do). Do not log out while requests on that session are still executing.

### L-AUTH-128  SCIM 2.0: manage SCIM tokens on v3 and read SCIM-managed users and groups on /scim-service
**Kind:** ROUTE · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence medium: code or a guide); not probed here
Prereqs: Administrator options 'Map SAML Groups and Roles' and 'Enable IdP to push users/groups using SCIM 2.0' on, and a role that can read and update the org. `GET <baseApiUrl>/public/core/v3/scimTokens` lists {id, value (masked), expiry, status}; `POST .../scimTokens` (no body) returns a new token with its full value once; `DELETE .../scimTokens/<tokenId>` -> 204. At most two tokens may exist, expired ones included, so delete one before creating a third. Reads: `GET <serverUrl>/scim-service/Users?filter=userName eq "<user>"` and `GET <serverUrl>/scim-service/Groups`, headers `Content-Type: application/scim+json` and `Authorization: <SCIM token>` (no session header); paging startIndex (1-based), count, sortOrder asc|desc.

### L-AUTH-129  SAML mapping bodies use plural arrays samlGroupNames / samlRoleNames; role mappings have their own add/remove routes
**Kind:** GOTCHA · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence medium: code or a guide); not probed here
Vendor docs give `PUT /public/core/v3/Orgs/<orgId>/addSamlGroupMappings` body {"groupMappings":[{"roleName":"<role>","samlGroupNames":["<g1>","<g2>"]}],"reuseGroup":false} (plural `samlGroupNames`, not `samlGroupName`). SAML role mappings: `PUT .../addSamlRoleMappings` and `.../removeSamlRoleMappings` with {"roleMappings":[{"roleName","samlRoleNames":[...]}]}; group removal is `.../removeSamlGroupMappings` (one table in the doc says removeGroupMappings; the example uses removeSamlGroupMappings). All answer 204. GET `.../SAMLConfig/groupMappings` filters with q=roleId==|roleName==|samlGroupNames==, limit default 200, skip. Conflicts with L-AUTH-108: probe before relying on either.

### L-AUTH-130  Register an OIDC identity provider before loginOAuth; the JWT must carry iss, sub, aud, exp, nbf, iat, jti and is single-use
**Kind:** ROUTE · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence medium: code or a guide); not probed here
`POST <baseApiUrl>/public/core/v3/Orgs/<orgId>/IdentityProviders` body {type:"OIDC", endPoints:{issuer:<https URL>, keys:<https JWKS URL>} (each at most 255 chars, same scheme, issuer a prefix of keys), accountPolicy:{link:{tokenClaim (default sub), matchType (e.g. uid)}}, signingAlgorithm (default RS256)}; GET lists it, PUT/DELETE `.../IdentityProviders/<idpId>`. Then `POST https://<login-host>/ma/api/v2/user/loginOAuth` {oauthToken, orgId}. The access token is accepted once (jti/uti replay protection); iss must equal the registered issuer; aud maps to the org's SAML entity id (`api://<orgId>.<cloud>-<region>.informaticacloud.com` or `api://<cloud>-<region>.informaticacloud.com`). Users must be activated SAML users. Refines L-AUTH-118.

### L-AUTH-131  loginSaml and loginSf: v2 logins with an IdP SAML assertion or a Salesforce session
**Kind:** ROUTE · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence medium: code or a guide); not probed here
`POST https://<login-host>/ma/api/v2/user/loginSaml` {samlToken:<Base64 SAML assertion XML>, orgId} returns the v2 user object (serverUrl, icSessionId). A SAML assertion already used for browser SSO is rejected for API login even if unexpired. `POST https://<login-host>/ma/api/v2/user/loginSf` takes a Salesforce session id and server URL obtained from the Salesforce Web Services API; the IDMC user must already be activated. Legacy orgs may have 6-character org ids instead of 22.

### L-AUTH-132  logoutall ends every v2 REST session in the org, not just yours
**Kind:** GOTCHA · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence high: code plus its tests, change notes or live-check notes, or vendor documentation bundled in the repository); not probed here
`POST <serverUrl>/api/v2/user/logout` (icSessionId) ends only that v2 session (200). `POST https://<login-host>/ma/api/v2/user/logoutall` with the user's credentials in the body ends ALL v2 REST sessions for the organization, which kills every other script, agent-side caller and scheduler using v2 sessions. Never call it from shared automation; and never log out while your own requests are still executing.

### L-AUTH-133  TrustedIP PUT overwrites all ranges; enabling it from automation can lock out your own callers
**Kind:** GOTCHA · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence high: code plus its tests, change notes or live-check notes, or vendor documentation bundled in the repository); not probed here
`PUT <baseApiUrl>/public/core/v3/Orgs/<orgId>/TrustedIP` body {"enableIP":true, "ipRanges":[{"startIP":"<a.b.c.d>","endIP":"<a.b.c.d>"}]} replaces every existing range (read with GET first and merge), and enableIP:true requires at least one range. Include the egress IPs of every script host, agent-side caller and admin before enabling, or logins from elsewhere are refused. A sub-org's ranges are independent of its parent's, so set each org separately. Refines L-AUTH-109.

### L-AUTH-134  Create automation users as identityType 2 (non-human); users list caps at limit 200 and is dynamically rate limited
**Kind:** FACT · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence high: code plus its tests, change notes or live-check notes, or vendor documentation bundled in the repository); not probed here
`POST /public/core/v3/users` accepts `identityType`: 1 = human, 2 = non-human account for integrations and APIs; it is required when the org enforces multi-factor authentication, so service users for scripts should be created as 2. Other documented fields: forcePasswordChange, maxLoginAttempts, authentication (non-zero = SAML, then aliasName required), and roles or groups (one of them required). Omit password and IDMC emails an activation link. `GET /public/core/v3/users?q=userName=="<n>"&limit=<<=200>&skip=<n>` (default 100); the users resource answers 'too many requests' under load, so throttle bulk loops. Refines L-AUTH-057.

### L-AUTH-135  securityLog defaults to the last 24 h / 200 rows; actor, actionCategory, objectName and skip need an entryTime range; event codes to alert on
**Kind:** FACT · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence high: code plus its tests, change notes or live-check notes, or vendor documentation bundled in the repository); not probed here
`GET <baseApiUrl>/public/core/v3/securityLog` (admin role, INFA-SESSION-ID) without q returns only the last 24 hours, at most 200 entries. The vendor syntax separates every clause with ';': `?q=entryTime>="<ISO Z>";entryTime<="<ISO Z>";actor=='<user>'` (window at most 14 days; limit 100-1000). actor, actionCategory, objectName and skip are rejected unless an entryTime range is present. actionCategory: Agent, Authentication, Group, Organization, Organization-Access-Config, Preference, Privilege, Privilege-Category, Role, SAML-Config, Sub-organization, User. actionEvent includes USER_LOGIN, AGENT_LOGIN, LOGOUT, ADMIN_ROLE_ASSIGNED/UNASSIGNED, PASSWORD_RESET/UPDATE, MFA_ENABLED/DISABLED, VERIFY_MFA_FAILURE/SUCCESS, TEMP_ACCESS_ENABLED/DISABLED, ACCESS_ENABLED/DISABLED, USAGE_TYPE_CHANGED, SCIM_TOKEN_EXPIRY_NOTIFICATION, CREATE, UPDATE, DELETE, DISABLE. Refines L-AUTH-112.

### L-AUTH-136  The v2 login response carries user PII (emails, security question, roles, group creators): allow-list fields, never log it raw
**Kind:** SECURITY · **Reported:** 2026-11-19 · **Evidence:** Public third-party code read 2026-11-19 (confidence high: code plus its tests, change notes or live-check notes, or vendor documentation bundled in the repository); not probed here
`POST /ma/api/v2/user/login` returns, besides icSessionId, serverUrl, orgId, orgUuid and id, the user's emails, the security question text, roles[], usergroups[] (with createdBy/updatedBy addresses) and masked password/securityAnswer; there is no org name. A client should extract only the fields it needs (icSessionId, serverUrl, orgUuid, orgId) and drop the rest before any logging, exception message or file write. Treat a non-JSON Content-Type on login as a failure (proxy or SSO page), and never retry a 401/403 login (lockout).

## Superseded / overturned (kept so nobody re-learns them)
### L-AUTH-077  IDMC REST has no PUT or PATCH; update only by POST to the id, overturned 2026-09-28
**Was believed:** 2026-07-25 to 2026-09-27 · **Overturned by:** L-AUTH-016
The July 2026 route corpus counted GET 82, POST 37, PUT 0, PATCH 0 and DELETE 5 proven, and concluded that updates are POSTs to the id or delete and re-POST. A proven PUT on runtime-environment selections broke the rule.

### L-AUTH-078  Never send a v3 session to a v2 endpoint; always keep two separate sessions, overturned 2026-09-21
**Was believed:** 2026-07-05 to 2026-09-20 · **Overturned by:** L-AUTH-020
July notes held that a v3 sessionId sent to a v2 endpoint returns a misleading 200 HTML page or a 404, so two logins and two caches are mandatory. September wrappers ran v2 and v3 on one session value; the July case probably involved a JWT-form sessionId.

### L-AUTH-079  The Data Profiling routes are SPA-session-only and not scriptable, overturned 2026-09-24
**Was believed:** 2026-07-09 to 2026-09-23 · **Overturned by:** L-AUTH-026
July records called the profiling service an SPA session plane whose `IDS-SESSION-ID` is injected by the browser (a plain `INFA-SESSION-ID` GET returned login HTML). September calls with `IDS-SESSION-ID` created, ran and polled profiles headless.

### L-AUTH-080  The IDMC session is a 30-minute idle timeout, so a cached session stays valid while calls keep flowing, overturned 2026-09-28
**Was believed:** 2026-07-05 to 2026-09-27 · **Overturned by:** L-AUTH-027
Session helpers cached `session.json` on the assumption of a 30-minute idle timeout and reused it while active. Long September runs showed the v2 session dies 30 minutes after grant regardless of activity.

### L-AUTH-081  Parallel agents should each log in and mint their own token instead of sharing a cache, overturned 2026-08-20
**Was believed:** 2026-06-27 to 2026-08-19 · **Overturned by:** L-AUTH-031
The June fix for 401s from an overwritten shared cache was a self-minted token per helper. Per-script logins later contributed to a lockout, and a shared cache under a file lock replaced the pattern.

### L-AUTH-082  Repeated IDS_085 at login means the account is locked or its password changed, overturned 2026-09-22
**Was believed:** 2026-09-22 (part of one session) · **Overturned by:** L-AUTH-035
A session read repeated `IDS_085` answers as a lockout or a rotated password. The same day a login at the org's own domain returned 200: the credentials had been posted to the wrong domain.

### L-AUTH-083  Access to the org is a hard wall that only the account owner can clear, overturned 2026-07-25
**Was believed:** 2026-07-24 · **Overturned by:** L-AUTH-056
A README recorded an org as blocked behind an access wall only the owner could clear. The next day a login landed in the org with full privileges and a connection create/delete succeeded.

### L-AUTH-084  /public/core/v3/users/{id} rejects GET, PUT, PATCH and DELETE with 405, overturned 2026-09-28
**Was believed:** 2026-07-25 to 2026-09-27 · **Overturned by:** L-AUTH-058
The July corpus called this route "the canonical proof" of no in-place edit and prescribed delete and recreate through the collection, although its own admin table listed GET and DELETE as supported. DELETE on the item returned 204 in September; PUT and PATCH remain unproven.

### L-AUTH-085  The login products[] list decides entitlement, overturned 2026-09-23
**Was believed:** 2026-07-04 to 2026-09-21 · **Overturned by:** L-AUTH-070
Orgs whose v3 login listed only "Integration Cloud" were declared unable to catalog, run CAI or use MDM, and about 90 items were escalated as licence purchases. Privileges, engines, selections and successful writes showed the capabilities were entitled.

### L-AUTH-086  Read and run are headless; publish, deploy and serve are UI-only, overturned 2026-09-28
**Was believed:** 2026-07-09 to 2026-09-27 (overturned in part) · **Overturned by:** L-AUTH-016
A July framing held that everything can be read and the data plane run over REST, but publish, deploy and serve have no REST verb. September evidence moved several lines (CAI publish, Database Ingestion deploy, runtime-selection PUT, clone- and package-authored design objects); MDM model deploy and some governance actions still stand. Use the framing only as a starting hypothesis.

### L-AUTH-087  A 404 on a REST probe means the capability is not provisioned, overturned 2026-07-05
**Was believed:** until 2026-07-05 · **Overturned by:** L-AUTH-071
Early July probes concluded that Database Ingestion, DAM, CLAIRE, the CAI Process Server and API Manager were not provisioned because guessed routes returned 404. The deployed engine list showed them running; the 404s were wrong paths or hosts.
