# The Laws of Headless IDMC

**Answers:** Which rules most change the outcome when Claude drives IDMC without its UI, why each one holds, and how to
prove you obeyed it.

**Read when:** once at the start of every new org, project or session, and again whenever an answer looks too good,
a wall looks final, or a write is about to touch something live.

**Key rules:**
- Establish the org first and work in one org per session (law 1; L-AUTH-046).
- Take the host and header from the plane map; a 200 can be fake, so read the body and read back every write
  (laws 2, 4, 12; L-AUTH-001, L-METHOD-025, L-METHOD-030).
- Logins are scarce: one session, one attempt, a block file on rejection (law 24; L-AUTH-036, L-AUTH-041).
- One writer per org, an org guard before every destructive call, and a denied action stays denied (law 25;
  L-AUTH-054, L-METHOD-121).
- Every task run and taskflow run is a job and the cap is invisible; CAI calls are not jobs (law 26; L-IPU-041,
  L-CAI-038).
- Runs, scans and previews are spend: approval first (law 29; L-IPU-005, L-METHOD-065).

**Related:** [How to use this KB](01-how-to-use-this-kb.md) · [Capability Map](03-capability-map.md) ·
[Error Triage](04-error-triage.md) · [Evidence Discipline](../14-claude-working-methods/02-evidence-discipline.md) ·
[Overturned Beliefs](../../lessons/overturned-beliefs.md)

**Last verified:** 2026-11-03 (evidence 2026-06-27 to 2026-11-03).

> Thirty rules. They start from the eight laws in the installed IDMC skills (July 2026) and are updated with the
> September and October 2026 evidence: the planes, the fake 200s and the kinds of 404 still hold, but "design almost
> nothing", "PUT never works" and "pushdown is UI-only" do not. Each law has one paragraph of why, the test that proves
> you obeyed it, and the doc and lesson ids behind it. When a law and a newer dated lesson disagree, the lesson wins and
> this page gets fixed.

**Above the laws: the goal and the two rules.** The laws exist to get the user's IDMC deployment built end to end, with
every capability they ask for, on the systems they have.
1. **Never push the user to another technology.** The laws are about how IDMC behaves; they apply to any source, target
   and connector. A system this KB has never covered is built brand new with them.
2. **Never say "not possible" until the workaround ladder has been worked in this org** (lessons, re-probe, another
   plane, clone a UI-made object, capture the UI call, another IDMC component, a Python bridge, one residual click;
   [New Pipeline Milestones](08-new-pipeline-milestones-any-source-any-target.md), "Before you tell anyone no").
   Laws 9, 16, 17 and 19 are the core of that ladder: a wall is a dated verdict, not a final answer. The KB is not an
   allow-list: nothing is forbidden because it is not written here. Native IDMC first; Python only when no IDMC path
   works.

---

## 0. From the July skill laws to these laws

The installed skills carried eight laws (numbered 0–7) and a few supporting rules, from evidence dated 2026-07-25/26.
September 2026 kept most of them and broke two.

| July law (skills) | September status | Now |
|---|---|---|
| 0 Establish the org first; one org per session | stands, and stricter before destructive calls | laws 1, 25 |
| 1 Search existing evidence before calling anything a wall | stands | law 9 |
| 2 A 200 can be fake; bogus-twin every input | stands | laws 4, 5 |
| 3 404 means wrong path or host; read the kind of 404; 403/405 are never entitlement | stands | laws 6, 7 |
| 4 Entitlement comes from deployed engines and privileges, never `products[]` | stands, extended with selections and effective licences | law 11 |
| 5 No HEAD/OPTIONS: probe with an empty POST and vary the Content-Type | stands, with a caveat for id-bearing action routes | law 8 |
| 6 Read and run are headless; design only by cloning or a service's own publish/deploy | **much weaker**: most design objects are now authored headless through packages; a short, dated list of clicks remains | laws 16, 17, 18 |
| 7 MCP is a calling convention, not a network position | stands; "five servers, eleven actions, one write" fell | laws 21, 22 |
| Update idiom: POST to the id; PUT effectively absent | **overturned in part**: PUT proven on three routes | law 14 |
| Four gates: host, engine, adapter, driver | stands | law 20 |
| Sessions: a 30-minute idle timeout | **overturned**: 30 minutes absolute from grant | law 24 |
| Two approvals before any spend; author-time work is free | stands | law 29 |

---

## A. Orient before you act

### Law 1. Establish the org first, in every session

Every IDMC answer is org- and pod-specific, and route families mount per pod and per licensed engine, so a result proven
in one org is not evidence for another. Before anything else, derive the org from three calls: the v3 login
(`userInfo.orgId`, 22 characters, and `products[].baseApiUrl`, which gives the pod and the domain label),
`GET <serverUrl>/api/v2/org` (the 6-character v2 id, `orgUUID`, the parent and sub-orgs) and `GET <serverUrl>/api/v2/agent`
(an empty list leaves entitlement unresolved, not absent). Record org name, both id shapes, pod, domain label and base
URL in the run log, re-derive them every session, and work in one org per session. Switching orgs is an admin action:
every documented org-switch path returned 404.

- **Test:** a receipt line (user, org name, v2 id, pod) is printed before the first write, and a writing script refuses
  to act unless a live `GET /api/v2/org` returns the expected `id`.
- **See:** [Identify the Org Before You Write](../01-access-auth-orgs/03-identify-the-org-before-you-write.md) ·
  L-AUTH-046, L-AUTH-011 (2026-09-28), L-AUTH-010, L-AUTH-050.

### Law 2. The auth plane is a property of the host and path

IDMC is about ten planes, each with its own host and header, and the header comes from the map, not from whichever
login you happen to hold. `/api/v2/*` takes `icSessionId`; `/public/core/v3/*` and `<pod>-cai` take `INFA-SESSION-ID`;
FRS, runtime selections, the licence service, `<pod>-ing`, `<pod>-dqprofile` and `hdm` take `IDS-SESSION-ID`;
`idmc-api`, `cdgc-api` and `<pod>-mdm` need all three identity headers (`Authorization: Bearer <jwt>`, `IDS-SESSION-ID`,
`X-INFA-ORG-ID: <orgIdV3>`; Bearer alone gets 401 on writes); anonymous CAI takes none. One session value can serve both
v2 and v3 (proven September 2026), but the header name is per plane. A wrong plane fails convincingly: a 200 carrying the
identity-service login page, a misleading 404, or a 401.

- **Test:** assert on the body shape and Content-Type, not the status. HTML beginning with `<` on a JSON route means
  the wrong plane or an expired session.
- **See:** [Pods, Hosts & Service Planes](../01-access-auth-orgs/01-pods-hosts-service-planes.md) ·
  L-AUTH-001 (2026-09-28), L-AUTH-020, L-AUTH-024, L-AUTH-025.

### Law 3. Derive every host from the login answer; never guess one or string-replace a pod literal

Log in at the domain host `https://<domain>.informaticacloud.com`, then call the base the login returned. Build service
hosts by splitting that base host at its first dot: `<pod>-cai`, `<pod>-ing`, `<pod>-mdm` (no `/saas`),
`<pod>-dqprofile`, `<pod>-dqcloud-api`; the shared hosts are `idmc-api.<domain>`, `cdgc-api.<domain>`, `hdm.<domain>`
and `mcp.<domain>`. The domain label is one character and cannot be guessed from the pod (`dm-us` versus `dmp-us`): the
wrong one gives a 404 on the platform plane, `400 IDS_085` at login (which looks like a bad password) and a foreign-org
401 on the other label's `cdgc-api`. Builders that string-replaced a pod literal kept calling the old pod after an org
moved.

- **Test:** resolve every derived host by DNS next to a nonsense sibling (`<pod>-bogusZZZ` must fail to resolve).
- **See:** [Pods, Hosts & Service Planes](../01-access-auth-orgs/01-pods-hosts-service-planes.md) ·
  L-AUTH-002 (2026-09-29), L-AUTH-003, L-AUTH-004, L-AUTH-005.

---

## B. Read every answer skeptically

### Law 4. A 200 can be fake

Five 200-class answers are not success: a zero-byte 200 with no Content-Type (a gateway routed the prefix and nothing
served it); a 200 whose body is the identity-service login HTML (wrong plane, wrong header or an expired session); a 200
whose value reverts on read-back (a silent rejection, law 12); `200 {"count":0,"objects":[]}` from
`GET /public/core/v3/objects?q=type=='X'` (the type filter is not validated, so a fabricated type returns the same); and
a 201 or 202 with a job id (a submission, not the work, law 13).

- **Test:** bogus-twin the path (`.../v99/bogusZZZ` answering identically means an artifact); read the object back; for
  counts, list unfiltered and group on the client.
- **See:** [Evidence Discipline](../14-claude-working-methods/02-evidence-discipline.md) §2.2 ·
  L-METHOD-025 (2026-07-26), L-AUTH-006, L-AUTH-007, L-METHOD-038, L-MIG-002.

### Law 5. Bogus-twin every input you control

Run a nonsense sibling next to any surprising answer: twin the path, the object name, the host, an error-producing route,
or the whole host. If the twin answers the same way, the answer is an artifact and proves nothing either way. Artifacts
on record: `403 APP_13401` and `500 CMN_001` under `/api/v2/agent/*`; nginx 503 on `<pod>-apigw` and `<pod>-apim` for
every path; `error [error [null]]` on a connection test (an unroutable host returns the same); the MDM 403 on
`entity/<be>/<id>`, which fires before the metadata lookup; zero-byte 200s on `data360` on some orgs.

- **Test:** the real answer differs from its twin's.
- **See:** [Evidence Discipline](../14-claude-working-methods/02-evidence-discipline.md) §2.1 ·
  L-METHOD-024 (2026-07-26), L-AGENT-031, L-AGENT-038, L-MDM-009, L-CDGC-006, L-CDGC-105.

### Law 6. A 404 means wrong path or host until proven otherwise: read the kind of 404

A 404 with a JSON or text body is a wrong path, host or domain label: keep hunting. `No static resource <path>`, or an
empty body after a host sweep, means the route is absent on that host. A 404 carrying a typed product error
(`DBMI_TASK_WAS_NOT_FOUND`) is a live handler that missed a lookup: fix the id. 403 and 405 are role gaps or read-only
resources, never entitlement verdicts. Early probes that read 404s as "not provisioned" were wrong for Database
Ingestion, DAM, CLAIRE, the Process Server and API Manager: their engines were running.

- **Test:** compare the 404 body with a twin's, and look for a 405 on another verb of the same path.
- **See:** [Evidence Discipline](../14-claude-working-methods/02-evidence-discipline.md) §2.3 ·
  L-AUTH-012 (2026-07-26), L-METHOD-026, L-AUTH-071, L-AUTH-087 (overturned).

### Law 7. Sweep the host family by DNS before believing a service-level 404, then apply the stopping rule

Resolve `<pod>-ing`, `-cai`, `-mdm`, `-dqprofile`, `-dqcloud-api`, `idmc-api.<domain>`, `cdgc-api.<domain>`,
`hdm.<domain>` and a bogus control; a name with no DNS is a genuine absence. Stop hunting only on a uniform 404 across
many plausible shapes, with no 405 anywhere and each shape matching its twin; any 405 means keep going. One DNS sweep
turned a whole product's "UI-only" verdict into a wrong-host error: Database Ingestion answers on `<pod>-ing`, not on the
pod host. MDM model deploy is the opposite case: eighteen shapes, a uniform 404 and no 405, so the route does not exist.

- **Test:** the stopping rule, recorded with host, header, path shapes and date.
- **See:** [Pods, Hosts & Service Planes](../01-access-auth-orgs/01-pods-hosts-service-planes.md) §4 ·
  L-AUTH-008 (2026-07-26), L-METHOD-029, L-DBMI-001, L-MDM-005.

### Law 8. No HEAD or OPTIONS: probe a write verb with an empty POST, and vary the Content-Type

An empty POST answering 400, 415 or 422, or a 500 naming a null field (`Cannot invoke Object.getClass because o is
null`), proves the verb exists; a 405 proves it does not. A write route has a second axis:
`POST /public/core/v3/import/package` answered `404 MigrationSvc_025` to JSON, 415 to zip and octet-stream, and
`400 MigrationSvc_030` to multipart, which was the live validator. Only a 405 on every encoding is a verdict. One caveat:
never empty-POST an id-bearing action route (`.../deploy/<id>`, `start`, `publish`); a DBMI `task/deploy/<taskId>` with
no body deployed the task.

- **Test:** `idmc_probe.py verbs|ctypes` in the Script Library, which refuses action words, login routes and paths that
  end in an id.
- **See:** [Evidence Discipline](../14-claude-working-methods/02-evidence-discipline.md) §2.4–2.5 ·
  L-METHOD-027 (2026-07-26), L-METHOD-028, L-MIG-009, L-AUTH-015.

### Law 9. Search the evidence before calling anything a wall; date every wall and re-test it

Grep this KB and the reference library for the path and the exact error string first: one session swept 13
connection-type spellings after `403 APP_10519` and recommended a licence ticket while the verified body
(`type: "TOOLKIT_CCI"`, the connector name in `instanceName`) was already on disk. Record each wall with verb, host,
path, headers, encoding, body shape, answer, the twin's answer, org, pod and date. Live verdicts were seen flipping every
3–5 days, and most of the July "UI-only" list fell in September to a new host, header, path format, encoding or a
captured UI call, never to a louder retry.

- **Test:** the wall record exists and says what would trigger a re-probe (a new agent build, pod, header, path format,
  encoding or tool).
- **See:** [Evidence Discipline](../14-claude-working-methods/02-evidence-discipline.md) §4 ·
  L-METHOD-034 (2026-07-26), L-METHOD-035 (2026-09-28), [Overturned Beliefs](../../lessons/overturned-beliefs.md).

### Law 10. Four evidence states are never merged

WORKS (a live status observed on a stated org and date), DOC (a named guide says so and nobody exercised it), REJECTED
(refused with a code; `405` means the verb does not exist) and UNTESTED (unknown, not unsupported). A blank cell is
untested, not absent. Never upgrade DOC to proven, and keep "rejected: PUT 405" and "untested: PUT, PATCH" in separate
columns: merging them produced every walked-back verdict in the July corpus, where 569 of 830 endpoint-verb pairs had
never been tried. Say the right kind of no: UI-ONLY (one click in something the org owns) is not a GAP (not there).

- **Test:** every capability statement carries its state and a date.
- **See:** [Evidence Discipline](../14-claude-working-methods/02-evidence-discipline.md) §1 ·
  L-METHOD-023 (2026-07-25), L-METHOD-036.

---

## C. Entitlement

### Law 11. Entitlement comes from privileges, engines, selections and effective licences, never from `products[]` or a 404

The v3 login `products[]` list is a launcher label: it said only "Integration Cloud" on orgs entitled to CAI, Database
Ingestion, CDGC, MDM, DAM, CDQ and CLAIRE GPT, and about 90 false "buy a licence" escalations came from reading it. Ground
truth is six reads: the identity-service Login (roles, `effectivePrivileges`, `feature.*` flags);
`GET /api/v2/agent/details/<agentId>` (`agentEngines[]`); the runtime-environment selections; `EffectiveLicenses`
`active[]`; real objects of the type in the v3 catalog; and a free create that validates. With no agent installed,
entitlement is unresolved, not disproven. Check the parent org before calling a sub-org unlicensed: one sub-org's missing
engines were an assignment, not a purchase.

- **Test:** grep the privileges for the product's prefix (`create.dbmi.task`, `create.mcp.CatalogSourceConfiguration`,
  `mdm.asset.be`) and read each agent's engines.
- **See:** [Users, Roles & Permissions](../01-access-auth-orgs/04-users-roles-permissions.md) §6,
  [Entitlement, Licenses & Job Caps](../11-ipu-metering-licensing/03-entitlement-licenses-job-caps.md) ·
  L-AUTH-070 (2026-09-23), L-AUTH-071, L-METHOD-033, L-IPU-031, L-AUTH-051.
---

## D. Write so that you can prove it

### Law 12. Read back after every write

A 200 whose value reverts is a silent rejection, and several IDMC writes do exactly that: new target parameters POSTed
to a mapping task over a real mapping (200, targets unchanged, because the task re-derives them from its mapping); a
cross-connector `targetConnectionId`; `sessionProperties {"Pushdown Optimization":"Full"}` on its own (it persists, but
the session log shows no pushdown until the temporary-view property and the cross-schema flag are set too); a workflow
update without its `scheduleId` (the schedule is unbound); an FRS PATCH of
`customAttributes` (204, no change); a Marketplace collection PUT with stakeholders (echoes 200, persists nothing); a
delete of a Published glossary term (reported deleted, still searchable).

- **Test:** GET the object and compare the field you meant to change. After a v2 DELETE a GET answering 403 means gone,
  except for schedules, whose deleted GET is an empty 200 shell: check the list instead.
- **See:** [Changing Pipelines Safely](../03-cdi-data-integration/08-changing-pipelines-safely.md) §6 ·
  L-METHOD-030 (2026-09-28), L-CDI-050 (2026-09-29), L-CDI-202, L-CDGC-098, L-CDGC-059, L-CDI-081.

### Law 13. POST to start, GET to poll, and read every item

Export, import, CAI publish and unpublish, catalog scans, metering exports, profile runs and DBMI deploys are jobs: the
starter returns an id (or a 201/202), and a GET on the starter itself is 405 by design. Items fail inside success
envelopes: a publish job answers 202 and then reports an item as BAD_REQUEST; `ccgf-contentv2` answers
207 Multi-Status; an import reports one state for the whole job while `?expand=objects` holds each object's result, and
one failing object skips all the others.

- **Test:** poll to a terminal state, then read `itemDetail[].itemState`, `?expand=objects`, the per-item FRS codes or
  the 207 items.
- **See:** [CAI Asset Lifecycle](../05-cai-application-integration/01-cai-asset-lifecycle-author-publish-unpublish-delete.md) §3.2,
  [Export & Import](../10-migration-org-management/01-export-import-v3-migration-api.md) §3.3 ·
  L-METHOD-031 (2026-07-26), L-CAI-002 (2026-09-28), L-MIG-012.

### Law 14. Update by POSTing the full object to its id; use PUT only where it is proven; re-send every secret

The v2 update idiom is `POST /api/v2/<resource>/<id>` with the full GET body minus the audit fields
(`PUT /api/v2/mttask/<id>` is 405). The July rule "PUT is effectively absent" fell on 2026-09-28: PUT is proven on the
runtime-environment selections (`/runtime/api/v2/runtimeEnvironment/<reId>/selections/ui`), on CDGC catalog sources
(multipart) and on Data Profiling profiles. Every other documented PUT or PATCH (CAI restadmin, `asset/v1/update`,
MDM `entity-xref`) stays documented until someone probes it. GET bodies return secrets masked, and POSTing a masked
value back blanks the secret: re-supply it on every update, even one that only flips an unrelated field.

- **Test:** GET and compare the changed field, then run the connection test or a small job.
- **See:** [Connections](../02-secure-agent-connections/03-connections-create-test-update-delete.md) §4,
  [Runtime Environments](../02-secure-agent-connections/02-runtime-environments-services-connectors.md) §3 ·
  L-AUTH-015, L-AUTH-016 (2026-09-28), L-CDI-046, L-CONN-006, L-CONN-007.

### Law 15. Address objects by id, never by name, and resolve ids with the right key

The same task names exist in unrelated folders, and the v2 list calls hide `frsGuid` and `scheduleId`: only each
object's detail GET shows them. Resolve a mapping task's v3 id through its detail's `frsGuid`, a mapping's through
`assetFrsGuid`, a workflow's by exact name among `WORKFLOW` objects (require exactly one match), and a path through
`POST /public/core/v3/lookup`. Use exact v3 type names: `type=='DBMI'` returns 0 while the real type is `DBMI_TASK`,
which once made thirteen clone-authored objects look deleted. v2 ids are 20 characters (`<orgIdV2>`, a type code such as
`0Z` task, `0N` workflow, `D0` schedule, `0B` connection, `08` agent or `25` runtime environment, then a sequence);
v3/FRS ids are 22-character GUIDs.

- **Test:** every create, run and delete takes an id, and every name lookup returns exactly one match.
- **See:** [CDI Object Model](../03-cdi-data-integration/01-cdi-object-model.md) §6 ·
  L-CDI-010 (2026-09-28), L-METHOD-009, L-CDI-009, L-CDI-011, L-CDI-018, L-MIG-055.

---

## E. Design, deploy and the residual clicks

### Law 16. Design is headless through packages, clones and each service's own calls, not through a create verb

The July core insight, "read almost everything, run almost everything, design almost nothing", is overturned for most
object types. `POST /public/core/v3/objects` is still 405 and `POST /api/v2/mapping` is not a create route, but by
2026-10-03 all of these were headless: real multi-transformation mappings synthesized as IMF JSON and imported (route 5),
including Union, Rank, Sequence, connected and unconnected Lookup, Data Masking, Rule Specification, Cleanse,
Deduplicate, Normalizer, mapplets and Update/Upsert/Delete/Data Driven writes (L-CDI-204); full SQL ELT
(pushdown) switched on per mapping task over v2 (L-CDI-202);
mapping tasks over the parameterized Copy Data bundle templates with the logic in `customQuery` (route 1); clones and
from-scratch packages for CAI assets, DBMI tasks, rule specifications, MDM business entities, profiles and
advanced-taskflow XML; linear taskflows and schedules over v2; DBMI `task/create`; Data Profiling `POST /profile`; CDGC
catalog sources, glossary domains, terms, links and classifications; users, groups, connections and MCP OAuth clients.
On 2026-10-06 catalog connection assignments (L-CDGC-159), catalog Data Quality rule occurrences (L-CDGC-161) and
intelligent structure models (L-CDI-223) followed.
Pick the cheapest route that is visible where it has to be: lineage and CLAIRE see real transformations, not SQL strings.

- **Test:** the new object appears in the v3 catalog by id with its exact type, the template is unchanged, and the next
  step (wrap in a task, publish, deploy, run) succeeds.
- **See:** [How Claude Builds Mappings Headless](../03-cdi-data-integration/02-how-claude-builds-mappings-headless.md),
  [Migration-Clone Authoring](../10-migration-org-management/03-migration-clone-authoring.md) ·
  L-METHOD-093 (2026-09-29), L-METHOD-098 (overturned), L-CDI-033, L-CDI-204, L-CDI-021, L-MIG-023, L-MIG-022.

### Law 17. Know the residual clicks and design them in

Still UI-only, or unsolved headless, on 2026-10-03. Each item is a dated verdict to re-probe, not a law of nature:

- **MDM:** business-entity model publish or deploy in the Modeler (whether Save alone is enough is disputed), match and
  merge and other job runs, steward decisions.
- **CDQ:** rule logic in the rule-builder canvas (a clone inherits its template's logic), per-rule scorecard pass rates
  (console only), the dictionary "Convert to API" click, authoring cleanse, parse, labeler, deduplicate and verifier
  assets.
- **CDGC:** bulk acceptance of CLAIRE-generated classifications (the auto-accept threshold is the lever), steward and
  owner assignment, deleting a catalog-source definition (REST only purges it), DAM policy authoring
  on the orgs probed, and Marketplace delivery templates, ratings and approvals. Cancelling a scan left this list on
  2026-10-26: `POST .../ccgf-orchestration-management-api-server/api/v1/jobs/<jobId>/operations/cancel` answers 200 from a
  script (L-CDGC-221, L-CDGC-225). Lineage reads and curated lineage
  writes left this list on 2026-10-08: the asset read's `lineage` segment gives every hop and the ccgf-contentv2 publish
  writes RELATIONSHIP edges (L-CDGC-181, L-CDGC-179); the `/data360/lineage/*` graph itself is still not routed.
  Lineage connection assignment left this list on 2026-10-06:
  `connectionAssignment?operationType=MERGE` stitches each reference and `SPLIT` undoes it (L-CDGC-159).
- **CAI:** activating or deactivating an API (a republish does not reactivate it), human tasks and file listeners
  (Kafka and AMQP event sources and listener processes left this list on 2026-10-08: L-CAI-116), MCP tool connections (their import fails, and newer orgs lack the type altogether: L-MCP-081), and assets stuck
  with duplicate or missing runtime entries (support).
- **CDI:** publishing an advanced taskflow made or copied by API, and moving a mapping to another connector type by
  package edit. The Data Quality transformation and Update Strategy are still unproven in generated mappings
  (L-CDI-204); full pushdown and the other transformations are headless now (law 16).
- **Platform:** sub-org licence allocation, serverless runtime-environment creation, the org's REST authentication
  mode, the agent's Shell Service, and perhaps the first connection of a brand-new add-on connector type (July
  evidence, untested since connector selection became headless).

- **Test:** before accepting one, run the ladder in law 19, and record the confirmation text of the click.
- **See:** [UI Automation with Playwright](../14-claude-working-methods/04-ui-automation-with-playwright.md) §1,
  [Capability Map](03-capability-map.md) · L-UI-001 (2026-09-29), L-MDM-005, L-MDM-007, L-DQ-010, L-DQ-031,
  L-CDGC-061, L-CDGC-066, L-CDGC-047, L-CAI-010, L-CAI-078, L-CDI-070, L-IPU-035, L-CONN-005.

### Law 18. An import creates design objects only: secure, bind, deploy, publish and tag them separately

A v3 package does not carry connection passwords or keys, Secure Agents, runtime-environment service selections,
schedules and their bindings, tags, CDGC catalog content, profile rule occurrences, CAI publication or DBMI deployment.
After an import nothing is runnable until those steps are done: set secrets from host files and test, re-select
services, create schedules unbound and bind them, re-tag with `TagObjects`, re-bind rule specifications,
`asset/v1/publish` in dependency order, `task/deploy` and `job/start`. Imports are all-or-nothing, `REUSE` keeps an
existing same-named object (which may be older than the source), and a CAI app connection written with
`encrypted="false"` carries its secret in plaintext into every package.

- **Test:** the post-import checklist of the migration runbook is complete, and the package is stored 0600, off shared
  folders, with its secrets rotated afterwards.
- **See:** [Export & Import](../10-migration-org-management/01-export-import-v3-migration-api.md) §5 ·
  L-MIG-017 (2026-09-28), L-MIG-024, L-MIG-011, L-MIG-018.

### Law 19. Before driving the UI, capture the UI's own call

Work down one ladder and stop at the first rung that works: REST on the right host with the right header, through the
probe toolkit; a managed MCP tool from the org's real registry; a clone through a v3 package; a capture of the XHR the
console sends for that click, replayed with the session helper's headers; Playwright from a server (behind a
transparent enterprise proxy the IDMC single-page apps rendered blank, L-UI-011, but headless Chromium with the Private
and Local Network Access checks off worked there on 2026-10-06, L-UI-031, so that verdict is disputed); and last, one
precise click handed to a human with a receipt. XHR capture found the runtime-environment selections PUT and the MCP OAuth-client route, both of
which had been recorded as UI-only, and driving the legacy form that the console iframes made agent engine configuration
headless (L-AGENT-088, 2026-09-29). The catalog's rule-occurrence form, captured once and replayed over REST, made
catalog rule occurrences headless (L-CDGC-161, L-UI-032, 2026-10-06).

- **Test:** every committing click has its verbatim confirmation text and a REST read-back.
- **See:** [UI Automation with Playwright](../14-claude-working-methods/04-ui-automation-with-playwright.md) §1, §6, §8 ·
  L-UI-001 (2026-09-29), L-UI-002 (2026-09-28), L-UI-010, L-UI-011, L-UI-031 (2026-10-06).

---

## F. Runtime and hosts

### Law 20. Fix the four gates in order: host, engine, adapter, driver; only then bodies and credentials

A working connection or job needs a healthy host (RAM, disk, swap, native libraries, egress, exactly one agentcore JVM
under a real supervisor), the service's engine selected and RUNNING on that runtime environment, the connector's adapter
selected and deployed on that agent, and third-party drivers staged where their consumer reads them. Each gate fails with
its own signature, and `403 APP_105060` is a family: "No running service found of type <Engine>" is the engine gate,
"Unable to fetch Connector attributes [com.informatica.adapter.<x>]" is the adapter gate, and "... of type
Connector_Service" is a binding to another runtime environment. RUNNING is a deployment signal: only a passing
connection test or a job that lands rows proves an engine usable.

- **Test:** `GET /api/v2/agent/details/<agentId>`, then `GET /api/v2/connection/test/<connId>` (free), then a small run
  checked by row count.
- **See:** [Troubleshooting - the Four Gates](../02-secure-agent-connections/05-troubleshooting-the-four-gates.md) ·
  L-AGENT-034 (2026-09-28), L-AGENT-023, L-CONN-018, L-CONN-015.
### Law 21. A runtime environment is a network position; MCP is not one

Whatever runs a task must be able to reach the data. A Secure Agent reaches only what its host's network reaches; the
Informatica Cloud Hosted Agent reaches only SaaS (a private host bound to it creates fine and never connects); a
serverless environment reaches only its own cloud account. Every connector a mapping uses must sit on the one agent that
runs it. Managed MCP servers run in Informatica's cloud: they never replace a Secure Agent, never reach a private database
the agent cannot, and never widen what the underlying service APIs allow. The reverse also bites: CLAIRE GPT's "Query the
data" runs through the Data Gateway on a Secure Agent of the org, over tunnels it keeps open, so a sampler of new
connections saw nothing and stopping that agent broke the feature. Prove that a process is outside a data path with
byte counters on its existing sockets or a reversible stop test, never with the absence of new connections
(L-AGENT-051, L-METHOD-123).

- **Test:** a connection test from the runtime environment the task will use; for MCP, the server's actual tool list.
- **See:** [Runtime Environments](../02-secure-agent-connections/02-runtime-environments-services-connectors.md) §1,
  [MCP vs REST](../09-claire-mcp/05-mcp-vs-rest-when-to-use-which.md) §1 ·
  L-AGENT-036 (2026-07-26), L-CONN-022, L-MCP-006 (2026-07-26), L-AGENT-097.

### Law 22. Enumerate the real MCP registry before declaring an MCP wall

The org's managed servers are listed at
`GET https://hdm.<domain>.informaticacloud.com/a2e-mcp-asset-mgmt-svc/api/v1/mcp-servers?type=MANAGED` with the v3
session in `IDS-SESSION-ID`. One org exposed 19 servers and about 140 tools where the April 2026 guide listed five
servers and eleven actions, and two same-day verdicts built only on the servers wired into one session ("MCP is DQ-only")
were wrong. MCP now writes (connections, runtime-environment selections, glossary and classification, users and roles,
export and import), but no MCP verb authors a CDI field mapping, deploys a DBMI task or publishes a CAI process. A local
MCP configuration can silently point at a different org.

- **Test:** `tools/list` against each server's `serverEndpointUrl`, and print which identity URL and org any local shim
  logs into.
- **See:** [Managed MCP Servers](../09-claire-mcp/01-managed-mcp-servers-catalog-access.md) ·
  L-MCP-001 (2026-09-23), L-MCP-003, L-MCP-033, L-MCP-005.

### Law 23. Every service selection costs RAM, disk and an engine rollover: select only what the scope needs

The selections PUT downloads a package for each newly selected service or connector and rolls Data_Integration_Server,
MassIngestionRuntime and Connector_Service to their newest builds, even when it only deselects; jobs submitted meanwhile
queue for about 5 minutes. Selecting every service once pulled about 18 GB in 8 minutes, drove a 4-vCPU host to a load of
about 189 and filled swap. Budget about 16 GB of RAM once Data Integration is on and about 20 GB of free disk, switch the
catalog Metadata services on only for scan windows, and change selections between lanes, never just before a timed run or
a demo. Dependencies ride along: a Data Quality selection also enables three storage connectors. What a selection
downloads stays: `<agent_home>/downloads/` is the live package store that installed services run from, so size the disk
for it and never prune it (pruning put 14 of 20 services into ERROR). Engine properties such as the DTM heap and pool
belong in the agent's cloud-side configuration, which survives the rollovers (L-AGENT-094, L-AGENT-088).

- **Test:** GET and save the selections (the undo), PUT, GET again, poll `agentEngines[]` until RUNNING, then re-test
  one connection per engine.
- **See:** [Runtime Environments](../02-secure-agent-connections/02-runtime-environments-services-connectors.md) §3–6,
  [Secure Agent](../02-secure-agent-connections/01-secure-agent-install-run-tune.md) §6 ·
  L-AGENT-039 (2026-09-28), L-AGENT-040, L-AGENT-041, L-AGENT-042 (2026-09-29), L-AGENT-052, L-AGENT-094 (2026-09-30).

---

## G. Sessions, orgs and other sessions

### Law 24. Logins are scarce: one designated session, one attempt, one shared cache

Rejected logins from every session and tool add up against one account: about six rejections across three sessions
locked one, and each attempt during a lock can restart it. `IDS_086` is the only lock code; `IDS_085` usually means
valid credentials sent to the wrong domain host, or a truncated user name. The v2 session and JWTs die 30 minutes after
grant however busy you are (the July "30-minute idle" belief is overturned), so cache the session with its grant time,
refresh at about 25 minutes, and on a 401 log in exactly once more. Serialize logins with a file lock and write a block
file on any rejected login, so nothing retries until the credentials change. A Secure Agent keeps running scheduled work
while its user is locked.

- **Test:** on a mocked network, after one rejection, ten further attempts make zero network logins.
- **See:** [Login, Sessions & Tokens](../01-access-auth-orgs/02-login-sessions-tokens.md) §5–7 ·
  L-AUTH-027 (2026-09-28), L-AUTH-034, L-AUTH-035, L-AUTH-036, L-AUTH-041, L-METHOD-070.

### Law 25. One writer per org; prove the org before any destructive call; a rejected call may already have run

When several sessions work one program, one lead session is the only one that logs in to each org and the only importer
or publisher; the others work read-only, host-side or on preparation, and coordinate through leases. Destructive scripts
assert the expected org id from a live `GET /api/v2/org` and print a receipt before the first delete, select what to
delete from an explicit id list (never by name or by date window), and never delete platform content: Add-On Bundles,
the Default project, `CAI_Anonymous_<orgIdV3>`, system classifications, a live replication slot. A tool call the user
rejected mid-run had already landed 68 repository deletes. A permission denial (a production deploy, a SaaS record
delete, a bulk copy of production code) covers the outcome, not the one command: never re-attempt it in pieces, through
another tool, a subagent or a peer; build and test up to the gated step, then ask once for an explicit approval that
names the action and its rollback (L-METHOD-121).

- **Test:** read back everything an interrupted or rejected call could have touched, and report the real state.
- **See:** [Multi-Agent Coordination](../14-claude-working-methods/03-multi-agent-coordination.md),
  [Headless Deletes & Org Cleanup](../10-migration-org-management/06-headless-deletes-org-cleanup.md) ·
  L-AUTH-054, L-CDI-149 (2026-09-28), L-CLEAN-001, L-CLEAN-016, L-CLEAN-017, L-CLEAN-020, L-METHOD-121.

---

## H. Cost, caps and speed

### Law 26. Every task run and every taskflow run is a job, and the monthly job cap is invisible headless

An org stopped at a cap of 10,000 jobs per month: from then on every Data Integration start failed within about
5 seconds with "You have exceeded your monthly limit of 10,000 jobs." No API shows the cap: `EffectiveLicenses`
limits all read -1, `GET /api/v2/org` carries no job limit, and the audit log recorded neither the cap nor its lift. A
linear taskflow of N tasks costs N + 1 jobs, and event lanes burned 17–21 jobs per event. Running CDC jobs, CAI
processes and MCP address verification kept working, and CAI invocations are not jobs at all: they do not appear in the
activity log and did not move the budget, so moving work between CAI and another layer saves no jobs, while
consolidating CDI tasks does (L-CAI-038). Count jobs yourself from the activity log (it keeps only a few days):
the task rows plus the taskflow rows plus each taskflow's child entries (L-IPU-024). At the cap only the first
start of a lane carries the error; the lane's other tasks log an empty error, 0 rows and a state outside 1/2/3, so a
breaker that matches the message on FAILED rows sees a fraction of the blocked runs (L-IPU-060). When the
reset day is unknown, guard on the worst of four windows (UTC month, org-timezone month, since the licence day, rolling
30 days) and fail closed (L-IPU-059); shed load at soft (~85%) and hard (~95%) thresholds of your own ledger
(L-IPU-043).

- **Test:** a month-to-date job counter per org, and a breaker that lets exactly one probe lane through after a backoff.
- **See:** [Entitlement, Licenses & Job Caps](../11-ipu-metering-licensing/03-entitlement-licenses-job-caps.md) §5–7,
  [Performance, Concurrency & Job Caps](../03-cdi-data-integration/07-performance-concurrency-job-caps.md) §7 ·
  L-IPU-041 (2026-09-28), L-CDI-131, L-CDI-132, L-IPU-042, L-CAI-038, L-IPU-043.

### Law 27. Small CDI tasks are latency-bound: fewer tasks and a dependency DAG beat bigger machines

Every mapping task pays about 20 s of fixed cost (DTM start about 14 s, dispatch about 5 s) before it moves a row, so a
62-task linear taskflow took 21–24 minutes for about 53k rows. Staging the lane on its read/write dependency DAG at
concurrency 4 cut a 16-task lane from 462 s to 215 s (measured) and the 62-task lane to about 5.5 minutes (estimated);
the floor is the longest sequential chain. Cap concurrency near the host's vCPU count on a shared host, keep at most about
five BigQuery readers per mapping (the DTM heap setting is agent-wide and every DTM gets it), and never design one mapping
task per table per layer. The agent caps concurrency too: DIS runs at most `maxDTMProcesses` DTMs at once, 2 by default,
so a controller that starts 4 tasks gets 2 until the pool is raised cloud-side (L-AGENT-099). Full SQL ELT is
not automatically faster: it writes a mapping's targets one after another (about 5.4 s each plus about 3 s), so a
5-target warehouse-only mapping took 43 s against 29 s in agent mode; keep it only behind a measured speed gate
(L-CDI-203).

- **Test:** the tasks on the critical path × 20 s is the floor. If that is still too slow, the job is CDC or CAI, not a
  CDI lane.
- **See:** [Performance, Concurrency & Job Caps](../03-cdi-data-integration/07-performance-concurrency-job-caps.md) ·
  L-CDI-121 (2026-09-29), L-CDI-124, L-CDI-125, L-CDI-126, L-CDI-129, L-CDI-114, L-AGENT-099, L-CDI-203.

### Law 28. Change live pipelines side by side, behind a swap gate; the rebuild must equal live

For one field: back up (the v2 JSON, the old SQL, a v3 export), change only that field after asserting its anchor occurs
once, read back, diff the old and new SQL on current data, run once while nothing that contains the task is running, and
patch the generator the same day, because the next rebuild otherwise reverts the fix. For many objects: build shadow or
parity copies that write only to parity datasets, prove them with a two-way `EXCEPT DISTINCT` and an idempotency double
run, pass the application's end-to-end suite, swap the taskflows in place, switch the orchestrator's plan behind a flag,
re-gate, and only then delete the old objects. When a real-time CAI process and a batch task write the same fields, both
must implement the same rule. Count a parity result only from a run that ended in success and actually rewrote the
target (its last-modified time at or after the run start): a mapping that failed every run once read "parity green"
from an earlier run's table (L-CDI-141).

- **Test:** the rollback kit (saved task JSON, workflow bodies, schedule snapshot, mapping package) exists before the
  switch.
- **See:** [Changing Pipelines Safely](../03-cdi-data-integration/08-changing-pipelines-safely.md) ·
  L-CDI-135, L-CDI-136, L-CDI-141, L-CDI-142 (2026-09-29), L-CDI-150, L-CDI-141.

### Law 29. Author-time work is free; runs are spend, and spend needs approval

Development, reads, clones, migration export and import, connection create, test and delete, user groups and role
bindings, and taskflow orchestration itself cost 0 IPU. Task and taskflow runs (compute hours), UI data previews, catalog
scans and profiles, DaaS and address-verification lookups, serverless runtime hours, and every service call behind a
managed MCP tool are metered, even while the MCP layer itself reads zero. Get explicit approval before burning IPUs in
someone else's org, and put approval flags (`RUN_APPROVED=1`) in any harness that would run metered work.

- **Test:** the run log names the approval next to each metered run.
- **See:** [IPU Model](../11-ipu-metering-licensing/01-ipu-model-mechanics.md) §5 ·
  L-IPU-005 (2026-09-03), L-IPU-020, L-MCP-026, L-METHOD-065, L-METHOD-068.

---

## I. Secrets

### Law 30. Secrets are read at run time, printed by name only, and rotated once exposed

Credentials come from environment variables or a 0600 file outside every repository, never from a literal in a script,
on a command line, in a tracker comment or in chat. Inspect a credential file of unknown format only with `wc -c` or
`stat`, use a secret where it lives (inside its container), write show-once secrets (OAuth client secrets, install
tokens) straight to a 0600 file, and treat anything printed as exposed: list it for rotation and rotate every consumer in
one window. Export packages, browser storage states and session caches are secrets too.

- **Test:** a staged secret scan passes before any commit, and the transcript shows key names but no values.
- **See:** [Secrets Hygiene](../14-claude-working-methods/06-secrets-hygiene.md) ·
  L-METHOD-001 (2026-09-28), L-METHOD-087, L-METHOD-088, L-METHOD-089, L-ENV-049.

---

## When a law seems wrong

1. Look for a newer dated lesson in the domain's lessons file and in
   [Overturned Beliefs](../../lessons/overturned-beliefs.md). The newest proven evidence wins.
2. If you have new evidence yourself, record it as a lesson with its date, host, header and status, move the old belief to
   the superseded section, and fix this page and the [Capability Map](03-capability-map.md) in the same change.
3. A law about a wall (laws 16 and 17) is only as good as its last probe date. Re-probe on your own org before promising
   anything to anyone.
