# CAI Asset Lifecycle: author, publish, unpublish, delete

**Answers:** How to author CAI assets headless (clone, in-place change, from-scratch package), publish and unpublish them over `asset/v1` on the `<pod>-cai` host, poll and read every item, delete them through FRS, and which steps still need the console or designer.

**Read when:** before authoring, publishing, redeploying or removing any CAI process, connection or connector.

**Key rules:**
- The asset path is `Explore/<project>/<folder>/<name>.<TYPE>.xml`, resolved from the v3 catalog; anything else gives 'Invalid asset path' (L-CAI-003).
- Publish connectors, then connections, then processes; unpublish in the reverse order (L-CAI-006, L-CAI-007).
- Poll every publish job and read every item: failures arrive inside 200 envelopes (L-CAI-002).
- Delete through FRS only after an unpublish (L-CAI-008).
- Export packages can carry connection secrets in plaintext: treat them as secrets (L-CAI-060).

**Related:** [CAI Runtime](02-cai-runtime-invoke-urls-control.md) · [CAI Event Listeners](06-cai-event-listeners-kafka-amqp-jms.md) · [CAI Connections & Connectors](03-cai-connections-connectors-salesforce-oauth.md) · [CAI Troubleshooting](05-cai-troubleshooting-stuck-assets.md) · [Export & Import](../12-deploy-migrate/01-export-import-v3-migration-api.md) · [Lessons: CAI](lessons.md)

**Last verified:** 2026-11-03

> **Summary.** Every step of a CAI asset's life is headless. Authoring goes through a v3 import
> package (a clone, an in-place change, or a package built from scratch); publishing and unpublishing go through
> `asset/v1/{publish,unpublish}` on the `<pod>-cai` host; deletion goes through FRS after an unpublish. One detail
> overturned every "UI-only" verdict: the asset path is `Explore/<project>/<folder>/<name>.<TYPE>.xml`. Still manual:
> re-activating an API that was deactivated in the console, two stuck runtime states, and designer-only constructs.

---

## 1. The asset model

| Asset | v3 object type | Repository MIME type | What it is |
|---|---|---|---|
| Service connector | `AI_SERVICE_CONNECTOR` | `application/xml+businesssconnector` (three s) | The API definition: connection attributes and actions. It has no endpoint of its own (L-CAI-026). |
| App connection | `AI_CONNECTION` | `application/xml+connection` | Attribute values for one connector, and where it runs (an empty `<agent/>` means the Cloud Server). |
| Process | `PROCESS` | `application/xml+process` | Inputs, outputs, temp fields, the step flow, and the deployment settings (REST binding, access). |
| Guide | `GUIDE` | not exercised here | Publishes the same way per the vendor guide. |

Inside a package each asset is a file named `Explore/<project>/<folder>/<name>.<TYPE>.xml`. The same string is the
**asset path** that publish and unpublish expect (L-CAI-003, 2026-09-28). Where a process runs is covered in
[CAI Connections & Connectors](03-cai-connections-connectors-salesforce-oauth.md).

---

## 2. Authoring

`POST /public/core/v3/objects` is 405 (the catalog is read-only) and the CAI-native design routes
(`asset/v1/processes`, `/import`, `/deploy`, `/save`, `designtime/v1/processes`) do not author anything (L-CAI-025).
All authoring is a v3 migration import. **The import publishes nothing**: publishing is section 3. Package mechanics
(checksums, `exportMetadata.v2.json`, REUSE versus OVERWRITE, all-or-nothing imports) are in
[Editing Packages Safely](../12-deploy-migrate/02-editing-packages-safely.md).

### 2.1 Route A: clone an existing process with its dependencies

1. `POST /public/core/v3/export` with `{"name":"<n>","objects":[{"id":"<objectId>","includeDependencies":true}]}`,
   poll `GET /public/core/v3/export/<id>`, download `GET /public/core/v3/export/<id>/package`.
2. The package holds the process, its app connection and its service connector as three `.xml` files.
3. For a new asset, change its names and identifiers as listed in L-CAI-017 (the repository item's name, GUID,
   display name and entry id; the process name attributes; the published contribution id; any renamed outputs and
   the bindings that write them). To reach a different REST provider, clone the app connection with a new base URL.
4. Recompute the changed files' SHA-256 lines in `exportPackage.chksum`, upload with
   `POST /public/core/v3/import/package` (multipart, file field `package`), start with
   `POST /public/core/v3/import/<jobId>`, poll to SUCCESSFUL. The org mints its own object id.
5. Publish. Proven: 2026-07-04 and 2026-09-22 (L-CAI-016). Needs the migration (export/import) role.

### 2.2 Route B: change a live process in place (the redeploy loop)

Run the whole loop in one script so a failure rolls itself back (L-CAI-018, 2026-09-28):

| Step | What to do | Why |
|---|---|---|
| 1 | Find the IDMC object id: `GET /public/core/v3/objects?q=type=='PROCESS'`, match the name | Exporting by the GUID written inside the process XML gives `MigrationSvc_034` (L-CAI-019) |
| 2 | Export that one object with `"includeDependencies": false`; keep the zip | The saved zip is the undo |
| 3 | Replace only the element or expressions that change, with a whitespace-tolerant match; assert exactly one hit each | The export is pretty-printed; a silent zero-hit replace ships nothing |
| 4 | Recompute only the changed files' lines in `exportPackage.chksum` (upper-case hex; spaces in paths appear as `\ `) | Untouched lines must stay byte-identical |
| 5 | `POST /public/core/v3/import/<jobId>` with `{"name":"<n>","importSpecification":{"defaultConflictResolution":"OVERWRITE"}}` | Same object id, new content |
| 6 | Publish (section 3) | The import alone changes nothing at runtime |
| 7 | Run side-effect-free verification cases, retrying for about 2 minutes (L-CAI-011) | The runtime can serve the old version for ~20 s |
| 8 | On any failed case, re-import the saved zip and republish | Automatic rollback |

Add new inputs as **optional** parameters so existing callers keep working. Measured: two live processes changed and
verified 10/10 and 15/15, and one attempt rolled back by its own verifier (2026-09-28).

### 2.3 Route C: build the package from scratch

A package you generate yourself imports like a genuine export when it contains (L-CAI-020, 2026-09-25):

- one file per asset under `Explore/<project>/<folder>/`, each a repository item (name, MIME type, description,
  version label `1.0`, state `CURRENT`, the asset XML as its entry, a 22-character alphanumeric GUID, display name);
- the real `<folder>.Folder.json` and `<project>.Project.json`, copied from any genuine export of an object in that
  folder;
- an `exportMetadata.v2.json` listing the folder, the project and each asset, with each asset's dependencies in
  `metadata.objectRefs`;
- `exportPackage.chksum` with a correct hash per file, and a contents CSV.

Import with OVERWRITE and `includeObjects` set to your GUIDs, then publish in dependency order. Persist the GUIDs so a
rebuild overwrites the same assets instead of creating twins. The fastest way to get every element right is to export
a working asset of the same type and copy its structure; the traps that broke builds are in section 2.4.

### 2.4 Rules that decide whether an authored asset publishes

| Rule | Symptom when broken | Lesson |
|---|---|---|
| Process inputs are parameter elements; outputs and temp fields are field elements | Import succeeds, publish item fails with a bare "Publish Error" | L-CAI-022 |
| Copy MIME types from a genuine export (the connector's is `businesssconnector`) | Import or publish failure | L-CAI-021 |
| In a REST binding, `otherParams` before `httpHeaders`; a POST action has a body | Connector does not publish or does not call | L-CAI-023 |
| Test XQuery offline; write regex-bearing code with a file tool | Silent wrong output, or bytes such as 0x08 in the deployed logic | L-CAI-024 |
| Anonymous or listed-user access is set in the deployment | No service URL is generated at all | L-CAI-034 |
| Dependencies exist in the target before the process publishes | Item ERROR, dependent entry not found | L-CAI-006 |
| The package carries every connection and connector its processes reference (limit the import with `includeObjects`); a shared connector kept in the package but left out of `includeObjects` resolves the reference without being imported, so the live connection keeps its secrets | Import FAILED `MigrationSvc_031` 'Correct the errors in the Select Assets section', empty details; or 'Internal application provider error' on the PROCESS, with nothing more in the import log | L-CAI-136, L-CAI-156 |
| Fix a failing package under throwaway names (a `zz_` prefix, a subset of the steps), and import the final name only when you expect it to succeed; bisect, then unpublish and FRS-delete the throwaways (L-CLEAN-005) | A name whose first imports failed stayed unroutable after a later SUCCESS publish: 'No plan found for service' on every invoke, while the same XML under a new name answered at once | L-CAI-157, L-CAI-156 |
| A Decision whose branches all end in End or a Jump has no outgoing link | Publish ERROR 'Link definition error: /process/flow/links/link[...]' | L-CAI-135 |
| After a connection or connector republish, the processes that use it are republished last | Processes read 'out-of-date' although the runtime uses the new connection | L-CAI-133 |
| Secrets authored `encrypted="true"` with an empty value, set after import with `asset/v1/update` | A value authored `encrypted="false"` is stored and exported in plaintext | L-CAI-132, L-CAI-060 |

### 2.5 What does not author (use the designer)

| Construct | Status | Lesson |
|---|---|---|
| File listeners, human tasks | Only ever authored in the designer. Kafka and AMQP (JMS) event sources, event-bound processes and fault handling author by package since 2026-10-08: [CAI Event Listeners](06-cai-event-listeners-kafka-amqp-jms.md) | L-CAI-025, L-CAI-116 |
| MCP tool connections (TOOL_CONNECTION) | Import fails `MigrationSvc_031` "Internal error"; recreate in the designer on a private-preview org (newer orgs have no such type) | L-CAI-027, L-MCP-081 |
| Managed APIs and policies (API Manager) | No REST and nothing to clone (July 2026) | L-CAI-094 |

For a UI fallback the designer lives at `https://<pod>.<domain>.informaticacloud.com/aiUI/products/applicationIntegration/main/Explore`
and needs a headed browser (L-CAI-029).

---

## 3. Publish

### 3.1 The call (L-CAI-001, proven 2026-07-09 and 2026-09-28)

```
POST https://<pod>-cai.<domain>.informaticacloud.com/active-bpel/asset/v1/publish
INFA-SESSION-ID: <v3 session id>
Accept: application/vnd.api+json
Content-Type: application/vnd.api+json

{"data":{"type":"publish","attributes":{"assetPaths":["Explore/<project>/<folder>/<name>.PROCESS.xml"]}}}
```

Success is **202** with the job id in `data.id` (and `links.status`). Derive the `-cai` host from the login base URL
by inserting `-cai` after the pod label; never hard-code it (L-CAI-040). `data` must be an object, not an array
(500 ClassCastException, L-CAI-004), and `Accept: application/json` gives 500 NotAcceptable (L-CAI-005).

### 3.2 Poll the job and read every item (L-CAI-002)

`GET .../active-bpel/asset/v1/publish/<id>/Status` (same headers) every 4-5 s, for up to about 3 minutes.

| Field | Values | Meaning |
|---|---|---|
| `data.attributes.jobState` | NOT_STARTED, RUNNING, IN_PROGRESS, QUEUED | still working |
| | SUCCESS | every item published |
| | WARNING | at least one item NOT_FOUND, none in ERROR |
| | ERROR | at least one item failed |
| `itemDetail[].itemState` | SUCCESS, ERROR, NOT_FOUND, BAD_REQUEST | per asset, with `itemStatusDetail` and `assetPath` |

The 202 and the 200 envelopes only confirm that the job was accepted; items fail inside them. `GET` on
`/asset/v1/publish` itself is 405 by design; `GET .../publish/<id>` returns job information.

### 3.3 Order, batching and path resolution (L-CAI-006, L-CAI-003)

1. Resolve each asset path in the org you are publishing to: `GET /public/core/v3/objects?q=type=='<TYPE>'&limit=200`,
   match the last `path` segment to the asset name, and build `Explore/<path>.<TYPE>.xml`. Refuse to publish when zero
   or several objects match. A project name containing a space published fine.
2. Publish in dependency order: service connectors, then app connections, then processes without connection
   references, then processes that call the connection.
3. One call accepts at most 199 paths and processes them in payload order. One asset per call, stopping at the first
   job that is not SUCCESS or WARNING, keeps failures easy to read.

### 3.4 Publish errors

| Signature | Cause | Fix |
|---|---|---|
| Item BAD_REQUEST "Invalid asset path." | Path without `Explore/` or without `.<TYPE>.xml` | Build the path from the v3 object `path` |
| HTTP 500 ClassCastException | `data` sent as an array | Send one object |
| HTTP 500 NotAcceptable | `Accept: application/json` | `application/vnd.api+json` on both headers |
| HTTP 403 on `/active-bpel/asset/publish` | Legacy path (no `/v1/`) or the pod host instead of `<pod>-cai` | Correct path and host |
| Item "Publish Error" with no detail | An input declared as a field element | Declare inputs as parameters (L-CAI-022) |
| Item ERROR naming a dependent or missing entry | Dependency not yet published | Publish in order (3.3) |
| "singleton sequence ... 2 items" or `AvrEntryNotFoundFault` | Stuck runtime state | See [CAI Troubleshooting](05-cai-troubleshooting-stuck-assets.md) (L-CAI-078) |
| Designer Publish fails, REST publish works | A client-side regression (cpfPublish 500 on first publish) | Publish over REST; send the asymmetry evidence to support (L-CAI-013) |

### 3.5 Publishing is not API activation (L-CAI-010, documented)

The first publish activates a process's API. If the API is later deactivated on the Application Integration Console
APIs page, a republish does not reactivate it, and no REST verb activates or deactivates an API. When a published
process does not answer, check its API status in Properties Detail.

### 3.6 Redeploy time and verification (L-CAI-011)

- A single-asset publish job typically finishes within one or two polls; a 9-asset migration wave took about a
  minute end to end (2026-09-28).
- After SUCCESS the runtime can still serve the previous version for about 20 s. Verify with retries (for example 12
  attempts, 10 s apart) before declaring failure; otherwise a good deploy gets rolled back.
- A folder move needs a republish from the new Explore path, and callers of a renamed process get 404 until they are
  switched (L-CAI-012).

---

## 4. Unpublish (L-CAI-007, proven 2026-09-28/29)

```
POST https://<pod>-cai.<domain>.informaticacloud.com/active-bpel/asset/v1/unpublish      (same headers as publish)
{"data":{"type":"unpublish","attributes":{"assetPaths":["Explore/<project>/<folder>/<name>.PROCESS.xml"]}}}
```

Poll `GET .../active-bpel/asset/v1/unpublish/<id>/Status`. Order is the **reverse** of publish: processes, then app
connections, then service connectors. Unpublishing an asset that something still depends on returns item ERROR
"... must be unpublished first. Dependent entry(ies): <names>" with jobState ERROR inside a 200. Maximum 199 per
call.

Unpublish is required before you rename a process or its API name, change Run On or Applies To, or delete the asset.
While unpublished, the process's service URLs stop answering, so plan the caller impact.

---

## 5. Delete through FRS, after the unpublish (L-CAI-008)

| Call | Body / form | Per-item result |
|---|---|---|
| `POST https://<pod>.<domain>.informaticacloud.com/frs/v1/DeleteEntities` (header `IDS-SESSION-ID`) | `{"artifactIds":["<frsGuid>", ...]}` | `FRS_200` deleted, `FRS_082` still published or out of date, `FRS_087` project not empty |
| `DELETE .../frs/api/v1/BaseEntities('<frsGuid>')` | none | 204 |
| `DELETE .../frs/api/v1/Documents('<id>')` | none | 403: do not use |

Read every id back: `FRS_070` means gone. An asset that cannot be unpublished (duplicate runtime rows, missing
runtime entry) stays `FRS_082` forever and keeps its project alive (L-CAI-078). To take one integration out of an org
completely: export it with dependencies as the backup, unpublish processes, then connections, then connectors, delete
through FRS, and switch its callers off. Org-wide order is in
[Headless Deletes & Org Cleanup](../12-deploy-migrate/06-headless-deletes-org-cleanup.md).

---

## 6. Other asset calls

| Call | Use | State |
|---|---|---|
| `GET .../active-bpel/asset/v1/status?MimeType=<process\|screenflow\|connection>` (optional `PublicationStatus=published\|unpublished\|out-of-date`) | Find out-of-date assets; make a publish driver idempotent | MimeType filter 200 live (2026-07-25); PublicationStatus documented (L-CAI-009) |
| `PUT <baseApiUrl>/active-bpel/asset/v1/update?assetType=Process` | Change access (listed users/groups or anonymous), API Gateway authorization, Run On, tracing level | Documented, untested (L-CAI-015) |
| `PUT <baseApiUrl>/active-bpel/asset/v1/update?assetType=AppConnection` | Set sensitive connection values after an import, then republish | Documented, untested (L-CAI-015) |

---

## 7. Why earlier "UI-only" verdicts were wrong

| What was seen | What it really was | Lesson |
|---|---|---|
| Publish "has no REST verb": `/objects/<id>/publish`, `/publish`, `/appint/v1/process/publish` 404; `asset/publish` 403 | Wrong path and wrong host | L-CAI-097 (superseded) → L-CAI-001 |
| The designer's first publish returned 500 | A client regression; the REST publish was unaffected | L-CAI-013 |
| An imported asset published 202, then its item said BAD_REQUEST "Invalid asset path" | The path sent was `<project>/<folder>/<name>`; `Explore/<project>/<folder>/<name>.<TYPE>.xml` publishes | L-CAI-003 |
| `restadmin/processes` returned `{process:[]}`, "proving" nothing was deployed | That route lists process instances (runs), not definitions | L-CAI-043 |
| An agent-bound process never ran | A separate Process Server fault (restart loop), repaired in place | L-CAI-071 |
| Hand-built connectors, connections and processes would not publish | Import-created assets are publishable with the right path | L-CAI-020 |

Date every wall in your own notes and re-test it whenever the path, host, header or tooling changes.

## 8. Overturned beliefs (this area)

| Belief | Believed | Overturned by |
|---|---|---|
| CAI publish is a UI click; there is no REST verb | 2026-07-04 to 07-26 | L-CAI-001 (L-CAI-097) |
| The REST publish is an undocumented bypass | 2026-07-06 to 07-25 | L-CAI-001 (L-CAI-098) |
| First publish is blocked until a vendor fix | 2026-07-08 | L-CAI-013 (L-CAI-099) |
| Imported assets need one UI Save before publish | 2026-09-09 to 09-24 | L-CAI-003, L-CAI-020 (L-CAI-100) |
| CAI authoring is UI-only | 2026-07-04; 2026-09-20 to 09-22 | L-CAI-016, L-CAI-020 (L-CAI-101) |
| Unpublish in the same order as publish | 2026-07-25 to 09-28 | L-CAI-007 (L-CAI-102) |
| Kafka and JMS event sources, listener processes and fault handling are designer-only | 2026-09-22 to 10-07 | L-CAI-116 (L-CAI-117) |

---

## 9. Checklists

**Publish or redeploy**
- [ ] Session is a v3 session for the right org; the `-cai` host is derived from the login base URL.
- [ ] Every asset path resolved from the v3 catalog, exactly one match each.
- [ ] Order: connectors, connections, processes without references, processes with references.
- [ ] Each job polled to a final state and every item read.
- [ ] Verification cases pass (with retries); the undo zip is kept until they do.

**Remove an integration**
- [ ] Backup export with dependencies, stored as a secret (packages can carry plaintext connection values).
- [ ] Callers switched off or repointed first.
- [ ] Unpublish processes, then connections, then connectors; read every item.
- [ ] FRS delete; `FRS_070` read-back for every id; stuck items listed, not forced.
