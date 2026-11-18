# MDM SaaS: Runtime vs Design

**Answers:** Which MDM SaaS operations are headless and which stay in the Business 360 UI? Which host and headers do
MDM calls need? How do I prove a business entity is live without trusting a misleading 404 or 403? How do I read MDM
entitlement?

**Read when:** planning any MDM SaaS automation; an MDM call returns 404, 403 or a login page; deciding whether a model
is deployed; checking whether an org holds MDM at all.

**Key rules:**
- The runtime plane on `<pod>-mdm.<domain>` is headless (ingest, read, entity-xref, search, export); model design,
  publish and job runs are Business 360 UI steps with no public route (L-MDM-004, L-MDM-005).
- Address a business entity by its runtime id (for example `c360.person`), never its design GUID (L-MDM-006).
- Prove an entity live with the ingest POST gate plus a fake-entity control; a 403 on GET proves nothing
  (L-MDM-008, L-MDM-009).
- Every MDM call carries a Bearer JWT, `IDS-SESSION-ID` and `X-INFA-ORG-ID`; re-mint the JWT at about 25 minutes
  (L-MDM-003).
- Read entitlement from privileges, roles and design objects, never from the login `products[]` (L-MDM-011).
- MDM runs in the pod: no Secure Agent engine, so agent sizing does not affect it (L-MDM-001).

**Related:** [MDM Records](02-mdm-records-ingest-search-export-cleanup.md) ·
[Business 360 Modeling & Match-Merge](03-business-360-modeling-match-merge.md) ·
[P360 vs MDM SaaS & Licensing](04-p360-vs-mdm-saas-licensing-notes.md) ·
[Migration-Clone Authoring](../10-migration-org-management/03-migration-clone-authoring.md) ·
[Lessons: MDM](../../lessons/by-domain/08-mdm.md)

**Last verified:** 2026-10-03

> **Summary.** MDM SaaS splits cleanly. The runtime plane on `<pod>-mdm.<domain>` (add `-mdm` to the pod label, drop
> `/saas`) is headless; the design plane (business entity models, source systems, match models, survivorship,
> publishing, running jobs) is the Business 360 UI. Whether the one manual model step is a Save or a Publish click is
> disputed (L-MDM-007); either way, prove the result headless with the ingest gate.

---

## 1. The split

| Operation | Plane | Headless? | How | Lesson |
|---|---|---|---|---|
| Ingest a source record | runtime | yes | `POST.../business-entity/public/api/v1/entity/<runtimeId>?sourceSystem=<src>` | L-MDM-019 |
| Read a master record by id | runtime | yes (disputed detail) | `GET.../entity/<runtimeId>/<id>` | L-MDM-021 |
| Update a source record | runtime | documented | `entity-xref` (GET, PUT, PATCH documented) | L-MDM-023 |
| Search and export master records | runtime | yes | `POST.../search/public/api/v1/search` (10,000 per query) | L-MDM-025 |
| Reference 360 lookup | runtime | yes | `POST.../rdm-service/external/v1/search` | L-MDM-026 |
| Fuzzy identity match | MCP | yes | Customer Identification MCP server | L-MDM-027 |
| Author or change a business entity model | design | no (clone only) | Business 360 Modeler; or migrate a same-type template | L-MDM-005, L-MDM-013 |
| Publish or deploy the model | design | no | Modeler (Save or Publish, see section 4) | L-MDM-007 (disputed) |
| Register source systems | design | no | Business 360 Console or Modeler | L-MDM-004 |
| Match models, merge and survivorship rules | design | no | Modeler | L-MDM-038 |
| Run match/merge, ingress, reindex jobs | design | no | Business 360 Console, or job schedules | L-MDM-016 |
| Steward decisions | design | no | Customer 360 steward UI | L-MDM-004 |

The durable plan: do the design clicks once, deliberately, then script everything at run time (L-MDM-004).

---

## 2. Hosts and authentication

**Host (L-MDM-002).** Start from the pod base URL of the login (`https://<pod>.<domain>.informaticacloud.com/saas`),
add `-mdm` to the pod label and drop `/saas`: `https://<pod>-mdm.<domain>.informaticacloud.com`. Routes seen on it:
`/business-entity/public/api/v1/...`, `/search/public/api/v1/search`, `/rdm-service/...`, and the UI apps
(`/ui-config-app`, `/ui-x360-app/...`, `/rdm-ui/`). `mdm.<domain>` has no DNS, nor do `<pod>-mdm-model`, `<pod>-b360`
or `<pod>-cs`.

**Auth (L-MDM-003).**

| Step | Call |
|---|---|
| Identity login | `POST https://<domain>.informaticacloud.com/identity-service/api/v1/Login` returns `sessionId` and `orgId` |
| Mint a JWT | `GET https://<domain>.informaticacloud.com/identity-service/api/v1/jwt/Token?client_id=cdlg_app&nonce=<n>` with the `IDS-SESSION-ID` header |
| Every MDM call | three headers: `Authorization` carrying the Bearer JWT, `IDS-SESSION-ID`, and `X-INFA-ORG-ID: <orgIdV3>` |

Bearer alone gets 401 on writes. The JWT expires 30 minutes after it is minted, whatever the activity, so re-mint it
from the cached identity session at about 25 minutes or on any 401 (no password needed). The MDM session itself times
out after 30 minutes idle. Details of the identity plane are in the auth lessons linked above.

---

## 3. Runtime id, not design GUID (L-MDM-006)

The record API addresses a business entity by its **runtime metadata id** (for example `c360.person`,
`c360.organization`, or the id of your own entity). The design or FRS GUID of the same entity returns
`404 "The requested metadata with GUID <x> cannot be found during load"` even on a live runtime, which looks exactly
like an undeployed model. A "deploy wall" can be exactly this identifier mistake: by runtime id the same runtime
answered 200 and already held hundreds of active master records.

Where to find the runtime id: the Customer 360 app and the Business 360 Console show it (entity selector, job names on
My Jobs); source-system ids follow a similar dotted form (for example `c360.<system>.system`).

---

## 4. The one manual model step, and why its form is disputed (L-MDM-007)

| Source | What it says | Strength |
|---|---|---|
| UI inspection of a deployed entity | The entity's menu offered Properties and Automapping only, no Publish; the model was runtime-effective on Save; only match models carry a Published state | Direct observation on an org with a deployed entity |
| Route sweeps and write-ups | Business 360 Modeler Publish is one click that gates all the 360 apps (sequence: Person, then Supplier, then Product) | Inferred; the sweep org had nothing modeled, so the button was never seen |
| Everyone | There is no public REST route that deploys or publishes a model | Proven: 18 shapes, 404 without a single 405 (L-MDM-005) |

What to do: plan one Modeler step (Save, plus Publish if your release offers it for the entity), capture the
confirmation text as the receipt, and then prove the result headless with the gate in section 5. Business 360 Explore
does show Publish and Unpublish for process assets (Ingress, MDMFlow), which is a different object type (L-MDM-017).

---

## 5. The deploy gate and the bogus-entity control (L-MDM-008, L-MDM-009)

```
POST https://<pod>-mdm.<domain>.informaticacloud.com/business-entity/public/api/v1/entity/<runtimeId>?sourceSystem=<src>
POST https://<pod>-mdm.<domain>.informaticacloud.com/business-entity/public/api/v1/entity/ZZFAKEENTITY?sourceSystem=<src>
```

| Real name | Fake name | Verdict |
|---|---|---|
| 404 "metadata... cannot be found during load" | same 404 | Nothing deployed under that name (or you used the design GUID) |
| 201, or a validation 400 | 404 | The entity is live; the plane accepts the call |
| anything | anything but 404 | Discard the run; the control failed |

Keep the probe body deliberately invalid so a live entity answers 400 and no junk record is written. Corroborate an
empty org with the unfiltered `GET /public/core/v3/objects?limit=5` (count 1, a single Default project). A harness
built on this gate reports DEFERRED and exits 0 until the entity is live, then flips to the real checks
(L-MDM-051).

**Do not use these as existence tests:**
- `GET.../entity/<be>/<id>` returning 403: the access check runs before the metadata lookup, so the same 403 fires
  for a fabricated name.
- `GET https://idmc-api.<domain>.informaticacloud.com/data360/mdm/v1/businessEntities` returning 200: its bogus twin
  returns a byte-identical 200 (prefix routing, not a handler).
- A 200 whose body is the identity-service login page: wrong plane (check Content-Type and body shape).

---

## 6. Reading MDM probe results

| Observation | Meaning | Lesson |
|---|---|---|
| Uniform 404 across many shapes, no 405 | The route does not exist: stop hunting | L-MDM-005 |
| Any 405 | The route exists with another verb: keep going | L-MDM-005 |
| 404 `CMN00005` | Generic not-found on the MDM host; bogus siblings return it too | L-MDM-010 |
| 403 with an `errorId` next to a bogus sibling's 404 `CMN00005` | The route exists; the caller lacks a role | L-MDM-010 |
| 400 `RDM.0040044` on an empty POST | The validator was reached: the verb exists | L-MDM-026 |
| 404 on one prefix (for example `/business-360/*`) | That prefix is absent; the host may still be live | L-MDM-010 |
| Name does not resolve in DNS | The host genuinely does not exist | L-MDM-002 |

---

## 7. Entitlement is not reachability (L-MDM-011)

Read MDM entitlement from:
- identity Login `effectivePrivileges`: CRUD on `mdm.asset.be`, `.srcsystem`, `.hierarchy`, `.relationship`,
  `.jobdef`, `.appmodel`; `execute.mdm.flows`; `manage.mdm.jobs`, `manage.mdm.schedules`;
- roles such as MDM Designer and Customer 360 Data Steward, Manager and Analyst;
- design objects: BUSINESS_ENTITY and other `MDM_*` objects in `GET /public/core/v3/objects`;
- the console app switcher (the 360 apps load without a license wall).

The login `products[]` list is only a label. An org can hold 83 MDM privileges and the MDM Designer role and still have
no reachable deploy route, and route mounting can differ per pod: probe the routes separately. New orgs are enabled in
order: license, MDM administrator role, then Customer 360 "Yes, Set up Application" (L-MDM-012).

---

## 8. Design objects through migration (L-MDM-013, L-MDM-014)

BUSINESS_ENTITY, MDM_SRC_SYSTEM, REFERENCE_ENTITY and RULE_SPECIFICATION objects travel in v3 migration packages:
export a same-type template, retarget namespace, GUID, name and FRS id, recompute checksums, upload with
`multipart/form-data` (a JSON upload returns `404 MigrationSvc_025`, which is a content-type trap, not a closed route),
start the import and poll to SUCCESSFUL. This lands design objects only; whether they are live without the Modeler
step is part of the section 4 dispute, so run the gate. An org with no same-type object has nothing to clone (export
returns `400 MigrationSvc_041`), and importing an entity exported from another org into an empty MDM org is untested.
Mechanics: [Migration-Clone Authoring](../10-migration-org-management/03-migration-clone-authoring.md).

---

## 9. Where MDM runs (L-MDM-001, L-MDM-015)

MDM SaaS is hosted in the pod; there is no MDM engine on a Secure Agent, so agent sizing and service selection do not
affect it. An agent matters only for integration jobs that move data into or out of MDM. Calling MDM services from
inside the console page (for example from a browser automation script) is redirected and blocked by the page's
content-security policy: call the REST routes from outside, or drive the UI.

**Golden records served without MDM SaaS.** While MDM is not ready, a warehouse stand-in produces the golden tables
([Business 360 Modeling & Match-Merge](03-business-360-modeling-match-merge.md) section 8). Those tables can be
activated from the warehouse directly: a CDP can read them in place through a zero-copy connection (counts matched the
warehouse row for row, deletes included), while segment publishing and activation stayed UI or admin steps for an
integration user. The serving and activation patterns are in
[Serving Outputs to BI and Apps](../03-cdi-data-integration/10-serving-outputs-to-bi-and-apps-freshness-latency-reverse-etl.md) (L-ENV-087).

---

## 10. Overturned beliefs (this area)

| Belief | Believed | Overturned by |
|---|---|---|
| A record-API 404 "metadata... cannot be found" means the entity is not deployed | 2026-07-04 to 07-06 | L-MDM-006 (L-MDM-059) |
| MDM is undeployed because ~30 REST endpoints return 404 | to 2026-07-06 | L-MDM-018 (L-MDM-060) |
| A 403 on GET entity means the entity exists | to 2026-07-26 | L-MDM-009 (L-MDM-062) |
| A deploy verb must exist somewhere: keep hunting | to 2026-07-26 | L-MDM-005 (L-MDM-063) |
| The `<pod>-mdm` host is not mounted | 2026-07-26 | L-MDM-010 (L-MDM-064) |
| MDM is not licensed (products[]) | 2026-07-04 to 07-06 | L-MDM-011 (L-MDM-066) |
| The clone route is closed (MigrationSvc_025) | 2026-07-26 | L-MDM-014 (L-MDM-068) |
