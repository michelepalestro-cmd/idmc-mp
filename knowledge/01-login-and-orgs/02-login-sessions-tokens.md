# Login, Sessions & Tokens

**Answers:** Which login do I call, and which session goes in which header? How do I mint a JWT? How long do sessions
live, and how do I cache them? How do accounts get locked, and how do I avoid and recover from a lockout? What changes
when an org moves to JWT authentication?

**Read when:** before the first login of a session or script, when a call returns the login page or a 401, after any
`IDS_085` or `IDS_086`, and before an org switches its REST authentication mode.

**Key rules:**
- All three logins go to the domain host; take every later base from the answer (L-AUTH-005, L-AUTH-018, L-AUTH-019).
- Sessions and JWTs die 30 minutes after grant, however busy: cache them with their grant time, refresh at about 25
  minutes, and re-login exactly once on a 401 (L-AUTH-027, L-AUTH-030).
- Logins are scarce: rejected logins from every session add up to one lockout, so one designated session makes one
  attempt; only `IDS_086` means locked (L-AUTH-034, L-AUTH-036, L-AUTH-038).
- Every host script carries a login guard (file lock, cache re-check, block file on rejection), with the block file kept
  per org (L-AUTH-041).
- Session-ID REST authentication is deprecated (documented): put auth behind a `session|jwt` switch with timed refresh
  now (L-AUTH-033).

**Related:** [01 Pods, Hosts & Service Planes](01-pods-hosts-service-planes.md) ·
[03 Identify the Org Before You Write](03-identify-the-org-before-you-write.md) ·
[Script Library](../../toolkit/lib/README.md) (the guarded session module) ·
[Secrets Hygiene](../14-working-with-claude/06-secrets-hygiene.md) ·
[Lessons: Access & Auth](lessons.md)

**Last verified:** 2026-10-03 (evidence 2026-06-27 to 2026-10-02).

> There are three logins (v3, v2, identity-service), all at the domain host. A session is an opaque value sent in a
> plane-specific header, and a JWT is minted from a session for the identity-protected APIs. Automation logs in rarely,
> from one place, and stops at the first rejection.

Credentials always come from environment variables or a protected file outside any repo, never from a literal in a
script or a document.

---

## 1. The three logins

All three go to `https://<domain>.informaticacloud.com` (not the pod host) (L-AUTH-005).

| Login | Request | Returns | Use it for |
|---|---|---|---|
| **v3** | `POST /saas/public/core/v3/login`, `Content-Type: application/json`, body `{"username":"<user>","password":"<pw>"}` | `userInfo.sessionId`, `userInfo.id`, `userInfo.name`, `userInfo.orgId` (the 22-char `<orgIdV3>`), `userInfo.orgName`, `products[].baseApiUrl` (`https://<pod>.<domain>.informaticacloud.com/saas`) | v3 plane, CAI, and any plane that rejects the v2 id (profiling on some pods, MCP asset management) (L-AUTH-018) |
| **v2** | `POST /ma/api/v2/user/login`, body `{"@type":"login","username":"<user>","password":"<pw>"}` | `icSessionId`, `serverUrl` (pod base ending `/saas`), `orgId` (the 6-char `<orgIdV2>`), `orgName` | v2 plane (`<serverUrl>/api/v2/...`), FRS, selections, licence and `-ing` via `IDS-SESSION-ID` (L-AUTH-019) |
| **identity-service** | `POST /identity-service/api/v1/Login`, body `{"username":"<user>","password":"<pw>"}` | `sessionId`, `orgId`; in July it also returned roles, `effectivePrivileges` and `feature.<cap>.*` flags (the entitlement ground truth) | entitlement reads; `GET …/identity-service/api/v1/CurrentUserInfo` and `…/Orgs` (L-AUTH-021) |

Take every later base URL from `baseApiUrl` / `serverUrl`. Never assume the pod.

## 2. Which session goes in which header

| Header | Value | Planes |
|---|---|---|
| `icSessionId` | v2 session (or v3 `sessionId`, see §3) | `/api/v2/*` |
| `INFA-SESSION-ID` | v3 session (or v2 id) | `/public/core/v3/*`, `<pod>-cai` |
| `IDS-SESSION-ID` | v2 `icSessionId` for FRS/selections/licence/`-ing`; **v3** session for `-dqprofile` on some pods and for `hdm` | FRS, runtime selections, licence service, `-ing`, `-dqprofile`, `hdm`, and (with Bearer) the identity APIs |
| `Authorization: Bearer <jwt>` + `IDS-SESSION-ID` + `X-INFA-ORG-ID: <orgIdV3>` | JWT minted from a session (§4) | `idmc-api`, `cdgc-api`, `<pod>-mdm`. **Bearer alone gets 401 on writes** (L-AUTH-024) |

Sent `INFA-SESSION-ID` instead of `IDS-SESSION-ID`, FRS and selections return the **login HTML with status 200**, which a
script can mistake for success (L-AUTH-025).

## 3. One session value, several headers

In September 2026 the v2 `icSessionId` was accepted on `/public/core/v3/*` as `INFA-SESSION-ID`, and the v3 `sessionId`
on `/api/v2/*` as `icSessionId`, on pods under both domain labels. Wrappers ran every v2 and v3 call on a single v2 login
(L-AUTH-020). This overturns a July rule that a v3 session on v2 gives a 200 HTML page. That case was probably an org
with JWT-on-login, whose `sessionId` is a JWT (inference, not re-tested). **Keep the header name per plane; share the
value if it works in your org.** Per-pod exception: one pod's profiling service rejected the v2 id and needed the v3
session (L-AUTH-026).

## 4. Minting a JWT

```
POST https://<domain>.informaticacloud.com/identity-service/api/v1/jwt/Token?client_id=<client>&nonce=<random>
IDS-SESSION-ID: <sid>
Cookie: USER_SESSION=<sid>
(empty body)                                   →  {"jwt_token": "<~1,700–2,200 chars>"}
```

- A `GET` with the same query and `IDS-SESSION-ID` also mints (L-AUTH-022). Use a fresh nonce per request.
- `<sid>` was the identity-service `sessionId` (documented) or the v3 login `sessionId` (proven).
- **`client_id`:** `idmc_api` (the documented value) worked for the managed MCP servers and the hosted DQ agent MCP.
  `cdlg_app` was used for CDGC (`cdgc-api`, `data360` on `idmc-api`) and MDM search on `<pod>-mdm`. Which service refuses
  the other value was never isolated, so copy the value recorded for the service you call (L-AUTH-023).

## 5. Lifetimes and the cache that held

| Credential | Lifetime | Refresh |
|---|---|---|
| v2 `icSessionId` | **30 min absolute from grant**, even while in use (L-AUTH-027, overturning "30-min idle") | log in again when older than 24–25 min (1,500 s), before a long batch starts |
| v3 session | ~30 min (treat the same) | own cache, ~25 min |
| JWT | 30 min from grant (vendor-documented) | re-mint from the cached session (~0.5 s, no password) at ~25 min or on any 401 (L-AUTH-028) |
| identity-service session | reported ~8 h (colleague's document, not probed) | cache separately from the JWT (L-AUTH-029) |
| MCP OAuth token | 5 min default (configurable 5–1,440) | see [knowledge/11-mcp-claire](../11-mcp-claire/02-mcp-auth-oauth-clients.md) |

**The cache pattern that survived a full org migration** (L-AUTH-030, 031):

1. Keep one cache file per org, mode 0600, holding `{sid, serverUrl, orgId, t}` (t = grant time). Share it across every
   script and browser run.
2. Serialize logins with a file lock, and **re-check the cache after taking the lock** (another process may just have
   logged in).
3. Refresh when `now - t > 1500`.
4. Treat an HTML 200 as an expired session.
5. On an API 401, drop the cache and log in **exactly once** more.
6. Never give each parallel agent its own login. Per-agent logins overwrote each other's caches and added lockout risk.

Sizing example: 98,115 sequential writes at ~10/s take ~2.7 h, so a token minted once covers only ~18% of the run
unless the helper refreshes it.

## 6. Orgs switched to JWT authentication

An org administrator chooses the org's REST authentication type in Administrator settings. With JWT on, the v3 login
`sessionId` was a JWT (starts with `ey`, ~1,700 chars) that CDGC GETs accepted as Bearer (L-AUTH-032, proven).

**Status (vendor notices; documented, not observed)** (L-AUTH-033):

| Item | What the notices say |
|---|---|
| Session-ID REST authentication | Deprecated since the October 2025 release; support is dropped in a later release |
| Default | Session-based stays the default until JWT becomes the default "sometime after the October 2026 release" (the timeline has slipped once already) |
| Headers | Unchanged (`icSessionId`, `INFA-SESSION-ID`); the value becomes a JWT with a fixed expiry set in Administrator |
| Token length | From the October 2026 release JWT values are capped at 2,000 characters and longer values are truncated; a ~1,700-character value was observed, so check clients that add claims or wrap tokens |
| Do not enable JWT | while API Manager or the REST V2 Connector calls IDMC APIs; API Center and B2B Gateway support JWT |

Before an org flips (or is flipped by default):
- move every client behind an `AUTH_MODE=session|jwt` flag that refreshes on a timer and on a 401, and never assumes a
  session lives longer than the configured JWT expiry;
- pause schedulers for the switch;
- keep the switch reversible.

The effect on session-header clients was predicted but has not been verified on an org that switched.

## 7. Lockouts: how they happen and how to avoid them

| Code | Meaning |
|---|---|
| `IDS_086` (401 on v3 login) "User account is locked" | **Locked.** The only lock code (L-AUTH-034) |
| `IDS_085` (400 on v3 login) "User name or password is not valid" | Bad or placeholder password, a truncated user name, **or valid credentials sent to the wrong domain host** (L-AUTH-035). v2 answers the same case with `403 UI_10000`; identity Login with 400 |

How locks happen:
- Rejected logins from **all** sessions and tools add up: at least 6 rejections across 3 sessions locked one account.
  Attempts during a lock can restart the cooldown, and one careful retry after 40 min was still locked (L-AUTH-036).
- Automation holding a **stale password** re-locks the account right after every unlock (L-AUTH-039).
- One lock was blamed on **login volume alone**: every probe script opened fresh sessions (L-AUTH-040).

Rules that prevented further locks:
1. **One credential, one designated session, one attempt.** When a password is shared with several sessions, one tries
   it once, and nobody retries after `IDS_085` (L-AUTH-038).
2. **Check the login host before the password.** `IDS_085` at the other domain label is not a lockout.
3. **Login guard in every host script** (L-AUTH-041):
   - use a file lock, then re-check the cache;
   - on any 4xx other than 429, write a **block file** holding the SHA-256 fingerprint of the creds file, and refuse to
     log in while the fingerprint matches;
   - a 5xx or 429 does not block;
   - test it on a mocked network: after a rejection, 10 further attempts must make 0 network logins.
   - **key the block file per org** : when one session module serves two orgs (for example the source
     and target of a migration), one shared block file lets a rejected login on one org stop every tool for the other.
     Keep the creds file, the session cache, the login host and the block file per org (the Script Library keys its
     cache and block file by `IDMC_PROFILE`, one per org), let read-only checks reuse the cached session of the org they
     need, and stop logging in to a retired org for routine reads.
4. **Long-running services** that log in on their own:
   - after an auth rejection, back off for hours (6 h default);
   - after a network error or 5xx, back off for 60 s;
   - show the block on the health endpoint (L-AUTH-042).
5. **Run automation as a dedicated native IDMC user**, not a personal or SSO-federated account. SSO users have no native
   password for REST (L-AUTH-045).

Recovery:
- An org admin unlocks the user (Administrator > Users > Unlock), or a password reset unlocks it ("Forgot your password?"
  on the identity-service home, or Reset in Administrator).
- If the locked user is the only admin, you need another admin or Informatica support.
- After the unlock, confirm the password once in a browser, then let one session log in once (L-AUTH-037).

While a user is locked, **the Secure Agent keeps running scheduled work** (it has its own token). Only work that needs a
user session stops: REST triggers, exports, UI (L-AUTH-044).

## 8. Rotating a password without re-locking the account

1. **Inventory every touchpoint first:**
   - host creds files and service env files;
   - catalog sources that store the user's password (lineage sources keep a user and password in their options);
   - MCP OAuth clients created with that password.
2. A human changes the password.
3. Prompt for the new value without echo, and write it **in place** into every creds file (same inode, backups kept, mode 600).
4. Delete the lockout block file and the session caches.
5. **Verify with exactly one login**, then restart the dependent services, then recreate or update the catalog sources
   and OAuth clients (L-AUTH-043).
