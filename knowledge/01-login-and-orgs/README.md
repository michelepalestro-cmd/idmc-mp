# Login, orgs and access: cheat sheet

Logging in to IDMC headless, picking the right host and header for every call, proving which org you are in before
any write, and managing users, roles and entitlement reads; it applies at the start of every session and before any
"not licensed" verdict.

**Start with:** `/idmc-mp:connect` (runs `toolkit/check_login.py` once), then `python3 toolkit/lib/idmc_session.py whoami`
and `hosts`. Open first: [Login, Sessions & Tokens](02-login-sessions-tokens.md).

## What works (headless)

| Task | How (exact route/tool/command) | Lesson |
|---|---|---|
| v3 login | `POST https://<domain>.informaticacloud.com/saas/public/core/v3/login` -> `sessionId`, 22-char `orgId`, `products[].baseApiUrl` | L-AUTH-005, L-AUTH-018 |
| v2 login | `POST https://<domain>.informaticacloud.com/ma/api/v2/user/login` (`"@type":"login"`) -> `icSessionId`, `serverUrl`, 6-char org id | L-AUTH-019 |
| Build hosts | Base from `baseApiUrl`/`serverUrl`; service hosts = `<pod>` + `-cai`/`-ing`/`-mdm`/`-dqprofile`/`-dqcloud-api` + `.<domain>...` (`idmc_session.py hosts`) | L-AUTH-002, L-AUTH-003 |
| Pick the header | v2 `icSessionId`; v3 and `-cai` `INFA-SESSION-ID`; FRS, selections, licence, `-ing` `IDS-SESSION-ID`; `idmc-api`/`cdgc-api`/`-mdm` Bearer JWT + `IDS-SESSION-ID` + `X-INFA-ORG-ID` | L-AUTH-001, L-AUTH-024, L-AUTH-025 |
| One session for v2 and v3 | Same value worked in both; keep the header name per plane | L-AUTH-020 |
| Mint a JWT | `POST /identity-service/api/v1/jwt/Token?client_id=<client>&nonce=<random>` with `IDS-SESSION-ID` + `Cookie: USER_SESSION=<sid>` | L-AUTH-022, L-AUTH-023 |
| Prove the org | `GET <serverUrl>/api/v2/org` (`id`, `orgUUID`, parent, `subOrgs`) + `GET <serverUrl>/api/v2/agent` | L-AUTH-046, L-AUTH-049 |
| Check a session before reuse | `POST <serverUrl>/api/v2/user/validSessionId`; re-login when `timeUntilExpire` is 0 | L-AUTH-117 (reported), L-AUTH-126 (reported) |
| Create / delete a user | `POST /public/core/v3/users` (key `name`, `groups` as id strings) -> 201; `DELETE /users/<userId>` -> 204 | L-AUTH-057, L-AUTH-058 |
| Group with roles | `POST /public/core/v3/userGroups` with `roles` as plain role-id strings; read back `GET /userGroups?limit=200` | L-AUTH-060 |
| Custom role | `POST /public/core/v3/roles` with `privileges` (ids) -> 201 | L-AUTH-090 |
| Object permissions | `GET`/`POST /public/core/v3/objects/<frsId>/permissions`, `DELETE .../permissions/<entryId>` | L-AUTH-089 |
| Roles and privileges | `GET /public/core/v3/roles`, `GET /privileges`; grep privileges for a product prefix | L-AUTH-062 |
| Entitlement | Six reads (identity Login, per-agent `agentEngines[]`, selections, licence service, object counts, a free create) | L-AUTH-074 |
| Audit log | `GET /public/core/v3/securityLog?limit=N` (N 100-1,000) | L-AUTH-075 |

## What doesn't work, and the workaround

| Wall | Workaround | Lesson |
|---|---|---|
| Login on the pod host, or v3 objects on the entry host -> 404 | Log in at the domain host, call the pod base from the login | L-AUTH-005 |
| Guessed pod or domain label (`dm-us` vs `dmp-us`) -> 404, `400 IDS_085`, foreign-org 401 | Read the label off `products[].baseApiUrl` | L-AUTH-004 |
| `icSessionId` on `/public/core/v3/*` -> 401, shown by wrappers as "0 objects" | `INFA-SESSION-ID`; check the status before trusting an empty list | L-AUTH-088 |
| `INFA-SESSION-ID` on FRS or selections -> 200 with login HTML | `IDS-SESSION-ID: <v2 sid>`; treat any HTML 200 as a failure | L-AUTH-025, L-AUTH-007 |
| Bearer alone on identity-protected writes -> 401 | Send all three identity headers | L-AUTH-024 |
| Edit a user in place (PUT/PATCH 405 or unproven) | Snapshot, delete + recreate, or the v3 membership PUTs | L-AUTH-059, L-AUTH-100 (reported) |
| Switch org over the API (every path 404) | Admin action; membership is explicit per user | L-AUTH-050 |
| Read entitlement from login `products[]` | It is a label; do the six reads | L-AUTH-070 |
| Read the monthly job cap over the API (licence limits read -1; `/api/v2/org` has none) | Ask Informatica / read Administrator | L-AUTH-072, L-AUTH-049 |
| `GET /public/core/v3/license/org/<6-char id>` -> `V3API_016` | Use the 22-char `<orgIdV3>` | L-AUTH-048, L-AUTH-073 |
| SSO-only user for REST automation | Dedicated native IDMC user | L-AUTH-045 |
| Sub-org connection on the parent's shared runtime -> `error [error [null]]` | Proves nothing; install an agent in the sub-org | L-AUTH-052 |

## Fastest safe path

1. Run `/idmc-mp:connect`. First run creates `~/.idmc_toolkit/IDMC_LOGIN.txt`; the user fills native user, password and
   login host (in a terminal with `--setup`, never in chat). **Proof:** CONNECTED summary with org name, org id, pod, user.
2. If the login fails, stop: no second attempt until the user fixes the cause (L-AUTH-038). **Proof:** the message names
   the cause (`IDS_085` wrong creds/host, `IDS_086` locked).
3. Record org name, v2 id, v3 id, pod, domain label, base URL (`idmc_session.py whoami`). **Proof:** `GET /api/v2/org`
   returns the expected `id`/`orgUUID` (L-AUTH-046).
4. Derive every host from the login (`idmc_session.py hosts`), never type one. **Proof:** the hosts print from the answer.
5. Pick the header per plane (table above). **Proof:** JSON body, not HTML or zero bytes (L-AUTH-006, L-AUTH-007).
6. Read `GET /api/v2/agent`. **Proof:** agents listed; `[]` means entitlement *unresolved*, not absent (L-AUTH-046).
7. Cache the session with its grant time; refresh at ~25 min; one re-login on 401 (L-AUTH-027, L-AUTH-030).
8. Before any write: `--execute --expect-org <orgIdV3>` and a receipt line. **Proof:** live org read matches (L-AUTH-047, L-AUTH-116 (reported)).
9. Before "not licensed": the six entitlement reads (L-AUTH-074). **Proof:** engines in `agentEngines[]`, privileges grep.

## Top traps

- `IDS_085` -> bad creds, truncated user **or the wrong domain host** -> check the host, never retry; only `IDS_086`
  means locked (L-AUTH-034, L-AUTH-035).
- Rejected logins from every session add up to one lockout, and attempts during a lock can restart it (L-AUTH-036);
  one credential, one session, one attempt (L-AUTH-038).
- Re-lock right after an unlock -> a scheduled client holds the old password -> find it from `USER_LOGIN_FAILED`
  cadence in `securityLog`; pause it, unlock, update every copy (L-AUTH-092, L-AUTH-039).
- `maxLoginAttempts` is per user and can be 3 -> read it before pointing automation at a user (L-AUTH-095).
- Session dies 30 min after grant even while busy -> refresh at ~25 min, not on idle (L-AUTH-027).
- 404 -> wrong path, host or label first; DNS sweep + bogus twin before any verdict; 405 proves the route (L-AUTH-008, L-AUTH-012).
- Results do not transfer between orgs or pods -> re-probe in this org (L-AUTH-011).
- v2 and activity-log times are pod-local labelled `Z` -> use the `*Utc` fields (L-AUTH-014).
- Removing a user's last direct role -> `400 V3API_IDSError_044` -> add the new role first (L-AUTH-090).
- Guessed group-role shapes drop bindings silently -> plain role-id strings, then read back (L-AUTH-060).
- Never delete `CAI_Anonymous_<orgIdV3>` or live service users: anonymous CAI URLs break (L-AUTH-061).
- `logoutall` ends every v2 REST session in the org -> never call it from shared automation (L-AUTH-132 (reported)).

## Go deeper

- [Pods, Hosts & Service Planes](01-pods-hosts-service-planes.md): host anatomy, plane -> header table, fake 200s and 404 kinds.
- [Login, Sessions & Tokens](02-login-sessions-tokens.md): the three logins, JWT mint, lifetimes, cache, lockout and rotation.
- [Identify the Org Before You Write](03-identify-the-org-before-you-write.md): three-call preflight, id shapes, sub-orgs, two orgs at once.
- [Users, Roles & Permissions](04-users-roles-permissions.md): users, groups, roles, object permissions, entitlement reads, audit.
- [Lessons: Access & Auth](lessons.md): every current and superseded `L-AUTH` lesson.
- [Error Triage](../00-start-here/04-error-triage.md): the org-wide error table.
