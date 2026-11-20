# Identify the Org Before You Write

**Answers:** Which org am I in, and how do I prove it before a write? What are the two org id shapes and which one does
each API want? How do sub-orgs, parents and shared orgs change what I can see and delete? How do I work with two orgs
at once?

**Read when:** at the start of every session, before every destructive call, when a login lands somewhere unexpected,
and whenever two orgs or two workloads share one session module or one org.

**Key rules:**
- Derive the org from three calls every session (login, `GET /api/v2/org`, `GET /api/v2/agent`) and record both id
  shapes, pod, domain label and base URL (L-AUTH-046, L-AUTH-049).
- Use the 22-character `<orgIdV3>` for `X-INFA-ORG-ID`, CAI paths and licence reads (L-AUTH-048).
- Before a destructive call, re-read the org live, assert it in code and print a receipt line (L-AUTH-047).
- Switching orgs is an admin action; check the parent before calling a sub-org unlicensed (L-AUTH-050, L-AUTH-051).
- One writer per org; in a shared org, merge every workload's keep list before any cleanup (L-AUTH-054,
  L-CLEAN-034).

**Related:** [01 Pods, Hosts & Service Planes](01-pods-hosts-service-planes.md) ·
[02 Login, Sessions & Tokens](02-login-sessions-tokens.md) ·
[Headless Deletes & Org Cleanup](../12-deploy-migrate/06-headless-deletes-org-cleanup.md) ·
[Multi-Agent Coordination](../14-working-with-claude/03-multi-agent-coordination.md) ·
[Lessons: Access & Auth](lessons.md)

**Last verified:** 2026-10-03 (evidence 2026-07-06 to 2026-10-01).

> Every IDMC answer is org-specific, and a proven result in one org is not evidence for another. Sub-org membership is
> explicit, and switching orgs is an admin action. When several Claude sessions work one program, **one lead session is
> the only writer per org**.

---

## 1. The three-call preflight (every session, before anything else)

| # | Call | Read |
|---|---|---|
| 1 | v3 login at `https://<domain>.informaticacloud.com/saas/public/core/v3/login` | `userInfo.orgId` (22-char), `userInfo.orgName`, `userInfo.sessionId`, `products[].baseApiUrl` → pod + domain label |
| 2 | `GET <serverUrl>/api/v2/org` (header `icSessionId`) | the 6-char v2 id, `orgUUID` (= the 22-char id), name, parent, `subOrgs`, `subOrgLimit`, `maxLogRows`, `restApiSessionLimit`. **Not** the monthly job limit (L-AUTH-049) |
| 3 | `GET <serverUrl>/api/v2/agent` | agents. `[]` leaves entitlement **unresolved, not absent** (L-AUTH-046) |

Record, and **re-derive per session** rather than caching across days: org name · v2 id · v3 id · pod · domain label ·
base URL. Guessing the pod was recorded as the single most common way to lose an hour.

## 2. One org, two id shapes

- **v2: 6 characters** (`<orgIdV2>`). It prefixes every v2 object id, followed by a type code: `0B` connection, `08`
  agent, `25` runtime environment; `0Z` was seen on mapping tasks (L-AUTH-048).
- **v3 / identity: 22 characters** (`<orgIdV3>`, returned as `orgUUID` by `/api/v2/org`).
- Both are correct for the same org, so do not "fix" the difference. Use the **22-char** form for `X-INFA-ORG-ID`, for CAI
  URN paths and the anonymous CAI tenant, and for licence lookups: `GET /public/core/v3/license/org/<id>` with the
  6-char id returns `V3API_016`.

## 3. Prove the org before any destructive call

1. Read the org live, just before the first write:
   - `GET /session-service/api/v1/session/User` → `name`, `orgId` (the host used was never recorded; try the pod host);
   - `GET /api/v2/org` → `id`, `orgUUID`.
2. **Assert in code:** the script refuses to write unless `GET /api/v2/org` returns `id == <expected orgIdV2>` (or
   `orgUUID == <expected orgIdV3>`).
3. Print a **receipt line** before the first write (user, org name, v2 id, pod), and keep it in the run log.
4. If anyone asks mid-run "which org are you deleting from?", that receipt is the answer. A cleanup was once interrupted
   by exactly that question (L-AUTH-047).

A tool call the user rejects mid-run may **already have executed server-side**. Always read back and report what
actually happened (see [Headless Deletes & Org Cleanup](../12-deploy-migrate/06-headless-deletes-org-cleanup.md)).

## 4. Parents, sub-orgs and runtime environments

- **Membership is explicit per user.** If a login lands in an org other than the one you were asked about, stop: every
  documented org-switch path returned 404, so this is an admin action. A parent-org admin could not read a child's agents
  (`403 APP_13407`), and a sub-org user could not read `/api/v2/org/<id>` (`403 REPO_10404`) (L-AUTH-050).
- **Check the parent before concluding a sub-org lacks something** (L-AUTH-051):
  - sub-orgs can use capabilities the parent allocates;
  - one sub-org showed 1 engine while its parent ran 22, and enabling services on the sub-org's own agent delivered all
    22, which was an assignment, not a purchase;
  - licence allocation to sub-orgs is a UI step in the parent (Sub-Organizations > Licenses);
  - a sub-org's runtime environments can be inherited and show zero agents.
- **Don't bind a sub-org connection to the parent's shared runtime environment** as a shortcut. It creates fine, and the
  test error changes to `error [error [null]]`, but an unroutable bogus host returns the identical error, so it proves
  nothing. Install an agent in the sub-org (L-AUTH-052).
- **Two runtime environments in one org share every org-scoped object**: catalog config, glossary, classifications, DQ
  rules, the MDM model, roles. Only RE-bound objects can drift: agent versions, connections, the task set. True
  dev/prod isolation needs a **second org** (L-AUTH-053).
- **A shared org has more than one keep list.** An object that nothing in your stack calls can still belong to another
  workload in the same org: one "safe to delete" task was another team's asset. Merge the keep lists of every workload,
  and grep configuration and plan files (JSON, YAML, env, cron) as well as code before you call anything unused
  (L-CLEAN-034; [Headless Deletes & Org Cleanup](../12-deploy-migrate/06-headless-deletes-org-cleanup.md) §2).

## 5. Working with two orgs at once (e.g. a migration)

- Give the shared client **one switch**: an env var such as `IDMC_ORG=source|target`, else a switch file, else a
  default. Keep a creds file, a session cache, a login host and a lockout block file **per org**, so a rejected login
  on one org never blocks the other.
- After a cutover, default the switch to the **new** org, so reads of the old org need an explicit login at its own
  domain (L-AUTH-055).
- Scripts pinned to one org assert the selected org before any call.
- A migration library can make the **source org read-only**: any non-GET raises unless explicitly overridden, and
  export POSTs are allowed.
- **One writer per org** (L-AUTH-054):
  - only the lead session logs in to and imports into or publishes in each org;
  - other lanes work host-side, on app repointing, or read-only, and coordinate by messages and LEASE comments on the
    tracker;
  - announce every import first, and never delete while an import runs.
- **Decommissioning the source org**: build the delete list from the source inventory, the source-to-target id map and
  the import's object log, give every object one verdict (twin created, reused an older same-named object, no twin,
  probe, dependency, shared or vendor content), and keep the deletion a separate, approved step after cutover and smoke
  tests (L-MIG-073; [Headless Deletes & Org Cleanup](../12-deploy-migrate/06-headless-deletes-org-cleanup.md)).

## 6. "The org looks walled": check before you believe it

A login once landed directly in an org with its full privilege set (876 privileges, 38 roles), and connection
create/delete both succeeded. The only real blocker was that no Secure Agent was installed (L-AUTH-056). Before calling an
org inaccessible or unentitled:
1. log in;
2. read privileges and roles;
3. read each agent's engines;
4. try a free create + delete.

Then read [04 Users, Roles & Permissions](04-users-roles-permissions.md) §6.

## 7. Preflight checklist (copy into any new script)

- [ ] Logged in at the org's **own** domain host; base URL taken from the login.
- [ ] v2 id, v3 id, pod, domain label recorded in the run log.
- [ ] Agent list read. An empty list is reported as "unresolved", not "no entitlement".
- [ ] For writes: `--expect-org <id>` asserted against a live read; receipt line printed.
- [ ] Session cache per org; one writer per org when parallel sessions exist.
