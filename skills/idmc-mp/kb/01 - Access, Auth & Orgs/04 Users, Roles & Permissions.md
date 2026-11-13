# Users, Roles & Permissions

**Answers:** How do I create, delete and change users, groups and role bindings headless? Which roles does an
automation login need? What do permission errors really mean? How do I tell what an org is entitled to run, and whether
it is a trial?

**Read when:** setting up the automation user and personas, before any batch change to users, when a call fails with a
permission signature, and before anyone says "not licensed".

**Key rules:**
- Users are created (201) and deleted (204) but not edited in place: snapshot first, then delete and recreate
  (L-AUTH-057, L-AUTH-058, L-AUTH-059).
- Groups take roles as plain role-id strings; guessed shapes silently drop the bindings, so read back (L-AUTH-060).
- Run automation as a dedicated native user holding the roles in §3 (L-AUTH-045, L-AUTH-063).
- Entitlement comes from six reads, never from the login `products[]` list; licence limits read -1 and hide the job cap
  (L-AUTH-070, L-AUTH-072, L-AUTH-074).
- Permission signatures are role gaps, not missing products; never delete `CAI_Anonymous_<orgIdV3>` (L-AUTH-061,
  L-AUTH-068, L-AUTH-069).
- Object permissions decide which objects a user sees. To limit a user to one project, write entries on everything else
  for everyone else, and keep one direct role on the user (L-AUTH-089, L-AUTH-090, L-AUTH-091).

**Related:** [03 Identify the Org Before You Write](<03 Identify the Org Before You Write.md>) ·
[Entitlement, Licenses & Job Caps](<../11 - IPU, Metering & Licensing/03 Entitlement, Licenses & Job Caps.md>) ·
[Runtime Environments - Services & Connectors](<../02 - Secure Agent & Connections/02 Runtime Environments - Services & Connectors.md>) ·
[Lessons: Access & Auth](<../13 - Lessons Learned/01 Access & Auth.md>)

**Last verified:** 2026-10-13 (evidence 2026-07-04 to 2026-10-13).

> Users, groups, roles and privileges are readable and largely writable over the v3 plane. Roles bind through groups and
> cost nothing. **Entitlement is read from privileges, engines, selections and effective licences, never from the login
> `products[]` list.** Never delete the org's anonymous CAI user or live service users.

All routes below are on `https://<pod>.<domain>.informaticacloud.com/saas/public/core/v3/...` with header
`INFA-SESSION-ID` unless noted.

---

## 1. Users

| Operation | Route | Result / notes | Lesson |
|---|---|---|---|
| List | `GET /users` (supports `?q=userName=="<login>"`) | 200 | L-AUTH-066 |
| Create | `POST /users`, body `{"name":"<login>","firstName":"…","lastName":"…","email":"…","groups":["<groupId>"]}` | 201. The key is **`name`** (`userName` → `400 V3API_007`); `groups` is a list of plain id strings; the body needs at least one role or group (else `V3API_IDSError_033`) | L-AUTH-057 |
| Delete | `DELETE /users/<userId>` | **204** (29 users removed in one cleanup). Read back with `GET /users`. Overturns the recorded "405" | L-AUTH-058 |
| Edit in place | PUT/PATCH on the collection or the item | **405 / unproven.** Change a user by delete + recreate; the Admin UI can edit in place | L-AUTH-059 |
| Add / remove roles | `PUT /users/<userId>/addRoles` and `/removeRoles`, body `{"roles":["<role name>"]}` | 204. Role **names**, not ids (a bad value is reported as 'name is invalid'). Removing a user's last direct role answers `400 V3API_IDSError_044` 'The group must have at least one role': add the new role first, then remove the old ones | L-AUTH-066, L-AUTH-090 |
| Add / remove groups | `PUT /users/<userId>/addGroups` and `/removeGroups`, body `{"groups":["<group name>"]}` | 204 | L-AUTH-090 |

**Before any batch change:** snapshot the users (`GET /users` to a file) and test the recreate body on one seat. A wrong
body once stranded 27 seats, which were restored from the snapshot (L-AUTH-059).

## 2. Groups and role bindings

- `POST /userGroups`, body `{"name":"<group>","roles":["<roleId>",...]}` → 200. Roles are **plain role-id strings**, not
  `[{"id":…}]` and not `roleIds`. Guessed shapes silently dropped the bindings, so read back with
  `GET /userGroups?limit=200` (L-AUTH-060).
- Members: `PUT /userGroups/<groupId>/addUsers` (and `removeUsers`) with `{"users":["<user name>"]}` → 204. The empty-body
  message names `userNames`, but that property gets a bare `400 V3API_007` (L-AUTH-090).
- DELETE works; PUT and PATCH are untested.
- Groups and role bindings consume **no seats and no IPU**. Only user seats are licensed.
- Persona users (engineer, operator, governance, MDM, …) with no role bindings give **no separation of duties**. Bind
  roles per persona through groups, especially when dev and prod runtime environments share one org (L-AUTH-064).
- For ~1,000 users, plan SAML SSO + SCIM group provisioning, not native accounts (design recommendation, untested;
  L-AUTH-065).

## 3. Roles and privileges (read)

- `GET /roles` (e.g. 59 roles: 35 system + 24 custom; items carry `id`, `roleName`) and `GET /privileges` (e.g. 897
  effective privileges) → 200 (L-AUTH-062).
- **Grep the privileges for a product's prefix** before answering "is it licensed?": e.g. `create.dbmi.task`,
  `feature.cdam.*`, `create.mcp.CatalogSourceConfiguration`, `metering.admin`.

**Roles one automation login needs** to drive CDI, CAI, CDQ, CDGC governance and CLAIRE (L-AUTH-063):
- Admin, Designer, Governance Administrator and CLAIRE GPT User;
- plus the migration (export/import) and object-admin role for packages;
- managed MCP servers additionally need the MCP Server and Deployed MCP Server asset privileges and the
  Execute/View Managed MCP Servers feature privileges. Per the vendor guide, Admin and Designer hold these by default,
  and Operator can run servers but not create composite ones.

### 3.1 Create a custom role (L-AUTH-090)

`POST /roles`, body `{"name":"<role>","description":"…","privileges":["<privilegeId>",…]}` → 201 with the role's `id`. The
empty-body message names `privilegeIds`, but that property gets a bare `400 V3API_007`. Copy privilege ids from a system
role: `GET /roles?q=roleId==%22<roleId>%22&expand=privileges` lists each privilege's `id`, `name`, `service` and `status`
('Default'-status privileges are accepted). URL-encode the quotes and spaces in `q=`. `DELETE /roles/<roleId>` → 204.

## 3a. Object permissions: which objects a user sees (L-AUTH-089, L-AUTH-091)

Role privileges decide what a user may do with a type of object; object permissions decide which objects. An object with
no entries is open to everyone whose roles allow the type; its first entry restricts it to the listed users and groups
(vendor Asset Management guide).

| Operation | Route | Result / notes |
|---|---|---|
| Read | `GET /objects/<frsId>/permissions` | 200; `[]` = no restriction |
| Add | `POST /objects/<frsId>/permissions`, body `{"principal":{"type":"USER" or "GROUP","name":"<user or group name>"},"permissions":{"read":true,"update":true,"delete":true,"execute":true,"changePermission":true}}` | 201, a list holding the new entry's `id`. A principal given by `id` gets a bare `400 V3API_007` |
| Remove | `DELETE /objects/<frsId>/permissions/<entryId>` | 204 |

Projects, folders and assets take their FRS id; connections and runtime environments their v2 `federatedId`; a
catalog-source UUID is refused (`400 V3API_AccessControlError_001`, L-CDGC-195). Add the owner first, and list the CAI
anonymous user wherever CAI processes run the restricted tasks. Writes took about one second each.

**Limit one user to one project (L-AUTH-091).**
1. A custom role with only view and run privileges (copied from Data Integration Task Executor and Monitor: DI, DQ,
   Profile and Monitor services plus the Admin view privileges for projects, folders, connections and agents), and a group
   that holds it.
2. On every other project, connection and runtime environment: entries with all five permissions for every other group,
   every other named user and the CAI anonymous user. Everyone else keeps exactly the access they had.
3. The user: add the new role directly, then remove the other roles and groups (a user keeps one direct role).
4. Leave the target project, its connections and its runtime environments without entries: the role already limits the
   user to view and run there. Installed-app projects (MDM) and system content can stay open when the role cannot list
   their types; restrict only the viewable assets inside them.
5. Snapshot users, groups and every list first, and log each entry id for the undo. The catalog has no per-source
   permission route (L-CDGC-195), so such a user gets no catalog role.

## 4. Users you must never delete

- **`CAI_Anonymous_<orgIdV3>`**: processes deployed with anonymous access run through it. Deleting it breaks every
  `/active-bpel/public/rt/<orgIdV3>/<process>` URL (L-AUTH-061). Anonymous endpoints are open to anyone who has the
  URL, which is fine for a demo but not for production writes.
- The **automation user itself**, and any **service user** a live process, catalog scanner or OAuth client depends on.
  Search the hosts and configs for the user names before a cleanup.

## 5. Permission signatures, and what they really mean

| You see | Real cause | Fix | Lesson |
|---|---|---|---|
| `403 MigrationSvc_038` "User does not have required permissions" on `POST /public/core/v3/export` | Permission gate. An empty-body POST gives 400, so the route is writable | Grant the migration (export/import) + object-admin role (a ~1-minute Administrator change). **For Add-On Bundle templates** (e.g. `dsst__copy_data_new_tgt`, `dlt__copy_data`) the 403 persisted for a non-admin in some orgs and not in others (disputed): don't export bundles, create mapping tasks over them | L-AUTH-068 |
| 403 when invoking a published CAI process | That **process's** allowed users/groups (not org roles) | Grant Service Consumer on the process | L-AUTH-069 |
| CAI scheduler 401 while process lists answer JSON | Role gap on the scheduler plane | Role grant | L-AUTH-069 |
| MDM search `403 Authorization Client Error` | Role gap | Role grant | L-AUTH-069 |
| "license status is not enabled" when adding Monitor/Operator roles; "insufficient permissions" on Monitor > All Jobs, My Jobs, the CAI Console | In a **shared** org, the org's licence locks those UI roles for a demo user | Demonstrate with Monitor > Running Jobs, Operational Insights, and apps that read the job APIs directly | L-AUTH-067 |

## 6. Entitlement: what is the org actually allowed to run?

**The login `products[]` list is a label, not the entitlement map** (L-AUTH-070). It can say only "Integration Cloud"
while the org is entitled to CAI, Database Ingestion, CDGC, MDM, DAM, CDQ, CLAIRE GPT and hundreds of connector types.
About 90 false "buy a licence" escalations came from reading it.

**Six reads establish ground truth** (L-AUTH-074). Classify each capability as HEADLESS, UI-ONLY or PURCHASE:
1. **Identity-service Login:** roles, `effectivePrivileges`, `feature.<cap>.*` flags.
2. **`GET <serverUrl>/api/v2/agent/details/<agentId>`** on every agent: `agentEngines[].agentEngineStatus.appname`
   and the status. Deployed engines decide what can run; with no agent installed, entitlement is **unresolved**
   (L-AUTH-071).
3. **Runtime-environment selections:** which services and connectors are enabled
   (see [02 - Secure Agent & Connections](<../02 - Secure Agent & Connections/02 Runtime Environments - Services & Connectors.md>)).
4. **Licence service:** `GET https://<pod>.<domain>.informaticacloud.com/license-service/api/v1/OrgLicenseAssignment('<orgIdV3>')/EffectiveLicenses`
   with `IDS-SESSION-ID: <v2 sid>` and `Accept: application/json` returns `active[]` and `limits{}`. **Every limit read
   -1**, even in an org that had just hit a 10,000 jobs/month cap, so the job cap is invisible here (L-AUTH-072).
   `GET /public/core/v3/license/org/<orgIdV3>` gives per-org detail (the 6-char id → `V3API_016`). There is no licence
   inventory route on some sub-orgs; read it in Administrator (L-AUTH-073).
5. **v3 object counts** per type, as content only (the `q=type==` filter is not validated, so a fake type returns 0 too).
6. **A free create call that validates** (e.g. create + delete a connection).

Two more reads settle the questions people ask next:

- **Is this a trial org?** `GET https://<pod>.<domain>.informaticacloud.com/license-service/api/v1/OrgLicenseAssignment('<orgIdV3>')/Views`
  names the base edition (for example a Trial edition). On a trial org the Licenses page showed no jobs row, every
  `EffectiveLicenses` limit read -1, and the Metering page showed serverless compute-unit meters of 10,000 hours,
  which say nothing about the monthly job limit; budget test rounds in jobs and assume a cap
  (L-IPU-056).
- **Did a promised entitlement arrive?** Poll `GET /public/core/v3/license/org/<orgIdV3>` and every agent's
  `GET /api/v2/agent/details/<agentId>` every 10 minutes, alert on content changes (not on `updateTime`, which moves on
  its own), and treat a new engine on the agents as the decisive signal (L-IPU-057;
  [Entitlement, Licenses & Job Caps](<../11 - IPU, Metering & Licensing/03 Entitlement, Licenses & Job Caps.md>)).

## 7. Audit logs

- `GET /public/core/v3/securityLog?limit=N` (N = 100–1,000) is the canonical audit log (200).
- `GET /api/v2/loginAudit` answered only on a parent or standalone org.
- `GET /api/v2/auditlog` is disputed: one record says 404, another says live. It also did not record a job-cap change
  (L-AUTH-075).

## 8. Vendor context

Vendor guidance (mid-2026) matched what the probes found: API coverage is uneven and write coverage weakest. Catalog
and MDM have richer APIs than integration; Data Integration exposes mainly operational APIs; REST coverage is wider than
MCP; mapping design over API/MCP is on the vendor roadmap with no committed date, so check the current release notes
(L-AUTH-076). Much of the design gap was later worked around by cloning and package import. See
[03 - Data Integration (CDI)](<../03 - Data Integration (CDI)/02 How Claude Builds Mappings Headless.md>).
