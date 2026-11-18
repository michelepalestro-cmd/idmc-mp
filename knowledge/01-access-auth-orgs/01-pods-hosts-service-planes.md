# Pods, Hosts & Service Planes

**Answers:** Which host and which header does each IDMC API need? How do I build every host from the login answer? Why
does a call answer 404, 401, an HTML page or an empty 200?

**Read when:** before you build any URL or pick a header; when a call fails with a 404, a 401, an HTML 200 or a
zero-byte 200; before you call anything "not licensed".

**Key rules:**
- Log in at the domain host, then take every base from the login answer; never type a pod or string-replace one
  (L-AUTH-002, L-AUTH-003, L-AUTH-005).
- The header comes from the plane of the host and path, not from the session you hold: the value can be shared across
  v2 and v3, the header name cannot (L-AUTH-001, L-AUTH-020, L-AUTH-088).
- Read the body, not the status: an HTML 200 is the login page and a zero-byte 200 is an unserved prefix (L-AUTH-006,
  L-AUTH-007).
- A 404 means wrong path, host or domain label until a DNS sweep and a bogus twin say otherwise (L-AUTH-008,
  L-AUTH-012).
- The domain label (`dm-us` versus `dmp-us`) cannot be guessed, and a result on one pod is not evidence for another
  (L-AUTH-004, L-AUTH-010, L-AUTH-011).

**Related:** [02 Login, Sessions & Tokens](02-login-sessions-tokens.md) ·
[03 Identify the Org Before You Write](03-identify-the-org-before-you-write.md) ·
[Error Triage](../00-start-here/04-error-triage.md) ·
[Lessons: Access & Auth](../../lessons/by-domain/01-access-auth.md)

**Last verified:** 2026-10-03 (evidence 2026-07-06 to 2026-09-30, pods under two domain labels).

> IDMC is not one API. It is about ten **auth planes**, each served from its own host and expecting its own header: the
> **pod host**, a **per-pod service host** (`<pod>-cai`, `<pod>-ing`, `<pod>-mdm`, `<pod>-dqprofile`,
> `<pod>-dqcloud-api`) or a **shared domain host** (`idmc-api`, `cdgc-api`, `hdm`, `mcp`). A call sent to the wrong
> host or with the wrong header fails *convincingly*. Pick the host and header from the tables below.

---

## 1. Host anatomy

Every URL is built from two values that the login returns: the **domain label** (`dm-us`, `dmp-us`, `dm-em`, `dm-ap`,
`dm-na`, `dm-uk`, …) and the **pod** (`usw1`, `usw3`, …).

| Host | Pattern | What lives there |
|---|---|---|
| Domain (entry) host | `https://<domain>.informaticacloud.com` | The three logins, identity-service (JWT mint, CurrentUserInfo, Orgs), authz-service (OAuth tokens) |
| Pod host | `https://<pod>.<domain>.informaticacloud.com` | v2 under `/saas/api/v2`, v3 under `/saas/public/core/v3`, and (without `/saas`) FRS `/frs/...`, runtime selections `/runtime/api/v2/...`, the licence service `/license-service/api/v1/...` |
| Per-pod service hosts | `https://<pod>-<service>.<domain>.informaticacloud.com` | `-cai` (Application Integration), `-ing` (Database Ingestion / DBMI), `-mdm` (MDM runtime, **no** `/saas`), `-dqprofile` (profiling), `-dqcloud-api` (CDQ dictionaries) |
| Shared domain hosts | `https://<name>.<domain>.informaticacloud.com` | `idmc-api` (CDGC `data360`, Marketplace, MDM control), `cdgc-api` (CDGC write plane), `hdm` (MCP asset management), `mcp` (managed MCP servers), `claire-gpt` (CLAIRE GPT) |

Service hosts are **always** `<pod>-<service>.<domain>`. Unprefixed or reversed forms (`mdm.<domain>`, `<pod>-cdgc`,
`<pod>-b360`, `apigw-pod.<domain>`) do not resolve (L-AUTH-009). A route sent to the wrong host 404s, which is not a
capability signal (L-AUTH-002).

## 2. The planes: host → path → header

| Plane | Host | Path prefix | Header(s) | Lesson |
|---|---|---|---|---|
| v2 platform | `<serverUrl>` (pod host + `/saas`) | `/api/v2/*`: job, activityLog, mttask, workflow, schedule, connection, agent, runtimeEnvironment, org | `icSessionId: <sid>` | L-AUTH-013, 019 |
| v3 platform | pod host | `/saas/public/core/v3/*`: objects, lookup, export/import, TagObjects, users, userGroups, roles, privileges, license, securityLog | `INFA-SESSION-ID: <sid>`. The v2 header name (`icSessionId`) here answers 401 'API request does not contain a valid INFA-SESSION-ID' | L-AUTH-013, 018, 088 |
| FRS (the repository behind Explore) | pod host | `/frs/v1/...` or `/frs/api/v1/...` | `IDS-SESSION-ID: <v2 sid>` | L-AUTH-025 |
| Runtime selections | pod host | `/runtime/api/v2/runtimeEnvironment/<reId>/selections/ui` | `IDS-SESSION-ID: <v2 sid>` | L-AUTH-016, 025 |
| Licence service | pod host | `/license-service/api/v1/OrgLicenseAssignment('<orgIdV3>')/EffectiveLicenses()` | `IDS-SESSION-ID: <v2 sid>` | L-AUTH-072 |
| Database Ingestion | `<pod>-ing` | `/dbmi/public/api/v2/...`, `/dbmi/api/v1/...` | `IDS-SESSION-ID` (helpers also sent `INFA-SESSION-ID` + `icSessionId`; minimum not isolated) | L-AUTH-025 |
| Profiling | `<pod>-dqprofile` | `/profiling-service/api/v1/...` | `IDS-SESSION-ID`. **On some pods only the v3 session works** | L-AUTH-026 |
| CDQ dictionaries | `<pod>-dqcloud-api` | dictionary API (write-only) | see [knowledge/06-data-quality-profiling](../06-data-quality-profiling/) | L-AUTH-069 |
| Application Integration | `<pod>-cai` | `/active-bpel/...` | `INFA-SESSION-ID` | L-AUTH-001 |
| Anonymous CAI runtime | `<pod>-cai` | `/active-bpel/public/rt/<orgIdV3>/<process>` | none (open to anyone with the URL) | L-AUTH-061 |
| Identity-protected APIs | `idmc-api`, `cdgc-api`, `<pod>-mdm` | `data360/...`, `ccgf-*`, MDM search/entity | **all three**: `Authorization: Bearer <jwt>`, `IDS-SESSION-ID: <sid>`, `X-INFA-ORG-ID: <orgIdV3>` | L-AUTH-024 |
| MCP asset management | `hdm` | `/a2e-mcp-asset-mgmt-svc/api/v1/{mcp-servers,oauth2clients}` | `IDS-SESSION-ID: <v3 sid>` | L-AUTH-017 |
| Managed MCP servers | `mcp` | `/mcp-servers/public/<context>` | Bearer (OAuth client token, or identity JWT + `IDS-SESSION-ID`) | L-AUTH-017 |

Rule of thumb: **v2 → `icSessionId`; v3 and CAI → `INFA-SESSION-ID`; FRS, selections, licence, `-ing`, `-dqprofile`,
`hdm` → `IDS-SESSION-ID`; anything on `idmc-api`/`cdgc-api`/`-mdm` → the three identity headers.** The session *value*
can be shared across v2 and v3 (see [02](02-login-sessions-tokens.md) §3). The header *name* is what differs per plane.
A wrapper that turns any error body into an empty list hides a wrong-header 401 as "0 objects": check the status before
you trust an empty result, and cross-check one object you know exists (L-AUTH-088).

## 3. Derive hosts from the login, never guess them

1. Log in (v3 or v2) at the domain host.
2. Take the base from `products[].baseApiUrl` (v3) or `serverUrl` (v2): `https://<pod>.<domain>.informaticacloud.com/saas`.
3. Build service hosts by splitting the host at the first dot and appending the suffix:
   `<pod>` + `-cai` / `-ing` / `-mdm` / `-dqprofile` / `-dqcloud-api` + `.<domain>.informaticacloud.com`.
   Drop `/saas` for `-mdm` and for the pod-host services (FRS, runtime, licence).
4. Build shared hosts from the domain label: `idmc-api.<domain>…`, `cdgc-api.<domain>…`, `hdm.<domain>…`, `mcp.<domain>…`.

Why it matters (L-AUTH-003): builders that did `serverUrl.replace("<pod>.<domain>", "<pod>-cai.<domain>")` kept silently
calling the old pod after an org moved. Anything hard-coded is a bug waiting for the next migration.

**The domain label is one character and not guessable** (L-AUTH-004). Some North American orgs are on `dmp-us`, not
`dm-us`. A URL borrowed from an org on the other label returns 404 on the platform plane, `400 IDS_085` at login
(which looks like a bad password), and a clean 401 on the other domain's `cdgc-api` (a foreign-org token).

## 4. Failures that look like answers

| You see | It means | Do |
|---|---|---|
| **200 with `Content-Length: 0`**, no Content-Type | Gateway prefix routing; nothing served the path. A bogus sibling (`/…/v99/bogusZZZ`) answers identically | Treat as absent/undeployed, not as success and not as an entitlement ticket (L-AUTH-006) |
| **200 whose body is the identity-service login page** (HTML, starts with `<`) | Wrong plane, wrong header (e.g. `INFA-SESSION-ID` on FRS or selections) or an expired session | Fix the header; if it is right, drop the session cache and log in exactly once more (L-AUTH-007) |
| **404 with a text/JSON body** | Wrong path, wrong host or wrong domain label | Keep hunting; check the host family first (L-AUTH-012) |
| **404 `No static resource`** (Spring) | The service is deployed but has no handler at that path | Wrong path on the right host |
| **404 empty body after a host sweep** | Nothing serves that prefix anywhere | A real wall (for that pod) |
| **Typed product error** (e.g. `DBMI_TASK_WAS_NOT_FOUND`) | A live handler missed a lookup | The route is real; the id is wrong |
| **405** | The route exists without that verb | Try the other verb; never call it "absent" |
| **503 from `<pod>-apigw` / `<pod>-apim`** | A load balancer with no backend, identical for bogus paths | Means nothing either way (L-AUTH-009) |
| 401 on another domain's `cdgc-api` | The route is real; the token belongs to another org | Log in to the right org |
| 401 'API request does not contain a valid INFA-SESSION-ID' on `/public/core/v3/*`, or an inventory that reads "0 objects" | The v2 header name was sent, and a helper swallowed the 401 | Send `INFA-SESSION-ID`; check the status before trusting an empty list (L-AUTH-088) |

**DNS sweep first (free, no auth)** (L-AUTH-008): resolve `<pod>-ing`, `-mdm`, `-cai`, `-dqcloud-api`, `-dqprofile`,
`-apigw`, `-apim`, `idmc-api.<domain>`, `cdgc-api.<domain>` and a deliberately bogus `<pod>-bogusZZZ` (must fail). This one
check overturned a whole-product "UI-only" verdict: the Database Ingestion paths 404 on the pod host because the service
lives on `<pod>-ing`.

## 5. Route availability differs by pod and org

- Route families mount **per pod and per licensed engine**, not per org (L-AUTH-010). Probed the same week, the first
  org answered 200 and the second 404 on each of these:
  - `/api/v2/license` and `/api/v2/loginAudit`;
  - `/api/v2/{dss,dtemplate,dmask,dreplicate,plan,fileListener}`;
  - `/public/core/v3/runtimeEnvironments` and `/public/core/v3/{agent,agentGroups,tags,licenses,orgs,permissions}`.
  `/api/v2/runtimeEnvironment` and `/api/v2/agent` answered on both. **Prefer the v2 admin forms.**
- **A result proven on one org or pod is not evidence for another** (L-AUTH-011). For example, one pod's profiling service
  rejected the v2 session another pod accepted. Store host + header + path + status + date with every verdict, and work
  in one org per session.

## 6. Verb and time conventions

- **Updates:** on v2, POST the full object to `/api/v2/<resource>/<id>`. Elsewhere, DELETE and re-POST unless a PUT is proven.
  PUT *does* exist on runtime selections and on CDGC catalog sources (multipart), which overturns "PUT never works"
  (L-AUTH-015, 016).
- **Long operations:** POST to start, then GET to poll (export, import, metering, scans, CAI publish). A GET on the starter returns 405.
- **No HEAD/OPTIONS:** probe a write verb with an empty POST. 400/415/422 (or a null-field 500) means the verb exists; 405
  means it does not. Vary the `Content-Type` too (json, multipart, zip, octet-stream) before declaring an upload route absent.
- **Timestamps:** v2 `createTime`/`startTime` and activity-log `startTime`/`endTime` were **pod-local time (UTC-4)
  labelled `Z`** on the pods seen. Use `startTimeUtc`/`endTimeUtc`, and set schedules with both `startTime` and
  `startTimeUTC` (L-AUTH-014).

## 7. Checklist before you design a call

- [ ] Host built from `baseApiUrl` / `serverUrl` (not typed), with the right suffix and `/saas` rule.
- [ ] Header chosen from the §2 table for that host and path.
- [ ] Response checked for body shape and Content-Type, not just the status.
- [ ] A bogus twin (path, object name or host) is run next to any surprising 200/403/500.
- [ ] The verdict is recorded with org, pod, host, header, status and date.
