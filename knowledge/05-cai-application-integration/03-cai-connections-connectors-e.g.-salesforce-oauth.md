# CAI Connections & Connectors (e.g. Salesforce OAuth)

**Answers:** How service connectors, app connections and processes fit together; where calls run (Cloud Server or agent); how to build a REST service connector; how to keep connection secrets out of export packages; how to authenticate to Salesforce with client credentials (Connected App or External Client App) and rotate secrets; which upsert patterns are safe.

**Read when:** before building or changing a CAI connection or connector, rotating a SaaS credential, or writing SaaS upserts from CAI.

**Key rules:**
- A REST service connector with a client-credentials token action and an external-id PATCH upsert beats the built-in Salesforce connector (L-CAI-058).
- New Salesforce apps need an External Client App for client credentials; a new Connected App can no longer take a Run As user (L-CONN-063).
- Values written unencrypted travel in plaintext in every export package (L-CAI-060).
- Change a secret by re-importing the connection OVERWRITE under the same GUID and republishing (L-CAI-061).
- A PATCH that carries an empty field sets it empty: omit absent fields (L-CAI-038).

**Related:** [CAI Asset Lifecycle](01-cai-asset-lifecycle-author-publish-unpublish-delete.md) · [CAI Runtime](02-cai-runtime-invoke-urls-control.md) · [CAI Troubleshooting](05-cai-troubleshooting-stuck-assets.md) · [Connections - Create, Test, Update, Delete](../02-secure-agent-connections/03-connections-create-test-update-delete.md) · [Lessons: CAI](../../lessons/by-domain/05-application-integration-cai.md)

**Last verified:** 2026-11-03

> **Summary.** A service connector defines an API; an app connection holds the values (and decides where calls run:
> the Cloud Server unless an agent is set); a process calls `<connection>:<action>`. For SaaS writes, a REST service
> connector with an OAuth client-credentials token action and an external-id `PATCH` upsert beat the built-in
> Salesforce connector, which needs the ModifyMetadata permission. Connection values authored unencrypted travel in
> plaintext inside every export package, so packages are secrets and credentials are rotated after a migration.

---

## 1. Three assets, three jobs

| Asset | Holds | Referenced by | Notes |
|---|---|---|---|
| Service connector (`AI_SERVICE_CONNECTOR`) | Connection attribute definitions (name, label, masked, required, type, test value) and actions (a REST binding with URL template, verb, headers and body; input parameters; output fields mapped from JSON properties) | App connections | Publishing it gives no endpoint (L-CAI-026); test it with the designer's Test action |
| App connection (`AI_CONNECTION`) | Attribute values plus a reference to its connector (connector path, GUID and UUID); where it runs | Processes, as `<connection>:<action>` service steps | An empty agent element means the Cloud Server |
| Process (`PROCESS`) | The logic; builds payloads in XQuery and calls connection actions | Callers over REST/SOAP | See [CAI Runtime](02-cai-runtime-invoke-urls-control.md) |

Publish them in that order and unpublish them in the reverse order ([Asset Lifecycle](01-cai-asset-lifecycle-author-publish-unpublish-delete.md)).

---

## 2. Where calls run: Cloud Server or Secure Agent (L-CAI-056, L-CAI-057)

| Situation | Run on | Why |
|---|---|---|
| The process calls only public cloud APIs | Cloud Server | No agent Process Server needed; worked while an agent engine was broken (350-730 ms per call) |
| The target is on a private network | A Secure Agent with a network path | The Cloud Server cannot reach private hosts |
| An event-based connector (listener) is used | The agent that runs that connector | Vendor rule |
| Signing with a keystore or private key, or RSA encrypt/decrypt functions | A Secure Agent holding the key file | Key files must be on the agent |
| A Human Task step is used | Cloud Server | Vendor rule |
| JDBC connections from CAI on an agent | That agent; drivers in `<agent_home>/apps/process-engine/ext` when "JDBC Jar Directory" is blank (unzipped there, no restart: L-CAI-141) | L-CAI-065 |
| PL/SQL or SQL from CAI where a Data Access Service Connector does not publish | The agent next to the database, through the database's REST layer | L-CAI-139, L-CAI-146 |

The process Run On property picks the Cloud Server, one agent or an agent group. It is locked while the process is
published: unpublish, change, republish (or use the documented, untested `asset/v1/update`). Agent-bound work needs a
healthy Process Server; see [Process Server on a Secure Agent](04-process-server-on-a-secure-agent.md).

---

## 3. Building a REST service connector (L-CAI-023, L-CAI-020)

Build connectors as XML inside an import package (or clone a working one) and publish them over REST. Rules that
mattered in practice:

- **Attribute definitions.** Declare every credential attribute with `masked="true"`; note that this alone did not
  keep the stored value encrypted (section 5).
- **Element order.** In a REST binding, `otherParams` must come before `httpHeaders`.
- **Bodies.** A POST action needs a body. Bodies can be literal templates that substitute inputs (for example a
  body that is just the `payload` input) or be generated as JSON from the input parameters.
- **Token calls.** Send an OAuth client-credentials token request as a form-encoded POST body
  (`Content-Type: application/x-www-form-urlencoded`), never as URL query parameters, so the client secret does not
  appear in a URL or a log line. In the working builder the `&` separators of that body were double-escaped inside
  the XML entry.
- **Outputs.** Map each JSON property you need to an output field; unmapped properties are dropped.
- **One generic action.** One upsert action whose object, external-id field, external-id value and JSON payload
  are inputs serves every object (section 6).
- **Timeouts.** An action's `requestTimeout` is in seconds: `10000` means no practical timeout; with `10` a slow answer
  times out after 10 s and returns HTTP 500, which a retry loop treats like any 5xx (L-CAI-128).
- **Errors as data or as faults.** `failOnError="false"` puts the HTTP status in an output marked
  `responseStatusCode="true"` and still maps the error body (a transport error reads 500); `failOnError="true"` raises
  the fault `HTTP_<n>` with the body as the reason, caught by a catch around the Service step (L-CAI-129).

Copy element structure and MIME types from a genuine export of a working connector rather than typing them
(L-CAI-021).

- **Query strings.** The `url` of a REST action is an XQuery template: write `&amp;amp;` between query parameters in the
  XML file. A single-escaped `&` publishes, then every call fails before it is sent, with only 'An error occurred when
  executing the expression' in the agent's catalina log (L-CAI-145).
- **File bytes in: a Salesforce file as base64** (L-CAI-154, 2026-10-26). A process cannot use the REST download
  (`GET /services/data/v<nn>/sobjects/ContentVersion/<id>/VersionData` returns raw binary). Add a REST action
  `POST {$instance_url}/services/Soap/u/64.0` with `Content-Type: text/xml; charset=UTF-8`, `SOAPAction: ""` and
  `Accept-Encoding: identity`, whose body is a partner-API `retrieve` of `VersionData,Checksum,Title,PathOnClient,
  VersionNumber` for `ContentVersion` with the OAuth access token as the SOAP `sessionId`. Take each value with
  `substring-before(substring-after($response, 'VersionData>'), '<')` (the namespace prefix does not matter, and base64
  holds no '<'). `Checksum` is the version's MD5: compare it before attaching a copy again. Attaching a new version stays
  on REST (`POST .../sobjects/ContentVersion` with VersionData as base64, 201). Keep files under the Cloud Server's
  5 MB payload limit (L-CAI-051).
- **File bytes out: a binary body** (L-CAI-155, 2026-10-26). Turn the base64 into an attachment with
  `sff:createAttachmentFromBase64($temp.file, $temp.b64, '<mime type>')` (the temp field typed attachment), and give
  the action one input of `type="attachment"` and a `restSimpleBinding` with an empty `<body></body>`: the connector
  then sends the attachment itself as the body. Proven against Azure Blob Storage Put Blob (`PUT https://{$account}.
  blob.core.windows.net/{$container}/{$blob}?{$sas}`, headers `x-ms-blob-type: BlockBlob`, `x-ms-version`, the content
  type twice, `Accept-Encoding: identity`): 201, MD5-identical, also into a hierarchical-namespace account. Keep the SAS
  in an encrypted connection attribute (L-CAI-132), URL-encode the blob name, and branch on the status with
  `failOnError` false (L-CAI-129). It should suit any REST API that takes a binary body; only Azure was tested.
- **A public link is not the route** (L-CAI-158, 2026-10-26): creating a Salesforce `ContentDistribution` for a
  server-side copy was refused for an API-only integration user (`INSUFFICIENT_ACCESS_ON_CROSS_REFERENCE_ENTITY`);
  moving the bytes through the process needed no extra permission, and a public link would expose the file to anyone
  holding the URL.
- **Data Access Service Connector (JDBC).** A `businessConnector agentOnly="true"` with the JDBC pool attributes and its
  actions in `<dasActions>` (L-CAI-140). In one org it would not publish at all (L-CAI-139): check that it publishes in
  the target org first, or reach the database through its REST layer (L-CAI-146).

---

## 4. App connections

- **Values.** Each attribute of the connector gets a value; credential values should be set so that they are stored
  as sensitive (section 5).
- **Connector reference.** The connection points at its connector by path (a `project:/rt.connector/<connector>/...`
  style path), GUID and UUID; keep the GUIDs stable across rebuilds so an OVERWRITE import replaces the same assets.
- **Runtime.** No agent set means the Cloud Server.
- **Built-in SaaS connectors.** An app connection can also wrap one of Informatica's own connectors (for example the
  Salesforce SOA connector with form-based login attributes). A builder for that variant existed; its publish outcome
  is not recorded, and the same plaintext rule applies to its login attributes.
- **Migration.** A v3 import brings the connection design; verify it in the target with one real call before
  switching callers (L-CAI-087).

---

## 5. Secrets: plaintext in export packages (L-CAI-060, L-CAI-061)

What was found (2026-09-28): an app connection whose client id and client secret had been written unencrypted kept
them in plaintext, and every v3 export package that included it carried them in plaintext. The connector's
`masked="true"` definitions did not prevent this. The vendor guide states that sensitive fields are not exported;
that applies to values stored as sensitive, not to values written unencrypted. The headless form that stores an
encrypted value was established on 2026-10-08 (rule 3, L-CAI-132).

Rules:

1. Treat every export zip as a secret: store it with 0600 permissions, off shared or synced folders, and leave a note
   where it used to be.
2. Rotate any credential that was ever inside a package, printed in a session, or shared in chat, and do it after
   the migration.
3. Set secrets after import (proven 2026-10-08, L-CAI-132): author the attribute `encrypted="true"` with an empty value,
   import, then `PUT https://<pod>-cai.<domain>.informaticacloud.com/active-bpel/asset/v1/update?assetType=AppConnection`
   (`INFA-SESSION-ID`, JSON) with `{"connections":[{"guid":{"$t":"<objectId>"},"attributes":[{"key":{"$t":"Password"},"value":{"$t":"<secret>"}}]}]}`
   and republish the connection, then its dependent processes. The export then carries `encrypted="true"` with an
   empty value. An attribute authored `encrypted="false"` is stored, and exported, in plaintext by the same call.
4. The route that did work headless for a rotation: regenerate the connection with the new value under the same GUID,
   import it with OVERWRITE, republish, and make one real call (L-CAI-061). It stores the value unencrypted again, so
   rule 1 still applies.
5. Never print a credential file to inspect it; check it with size and metadata commands only.

---

## 6. OAuth against a Salesforce Connected App (L-CAI-058, L-CAI-062)

**Why not the built-in connector.** The built-in CAI Salesforce connector needs the ModifyMetadata permission, which
is more than an integration user should hold. A REST service connector keeps the integration user to API access plus
object-level rights on the objects it writes.

**The shape that worked:**

| Piece | What it does |
|---|---|
| Connected App with the client-credentials flow | Issues tokens for a dedicated integration user; restrict its scopes and, where your policy allows, relax IP rules for this app only |
| Connection attributes | Token URL, client id, client secret, API version (for example v64 or newer) |
| Token action | Form-encoded client-credentials POST to the token URL; outputs `access_token` and `instance_url` |
| Upsert action | `PATCH <instance_url>/services/data/v<nn>/sobjects/<Object>/<ExtIdField>/<value>` with a Bearer token; an idempotent create-or-update |
| Process | Token step, then upsert step, then outputs such as the record id and a created flag |

**New apps: an External Client App, and rotating without breaking IDMC** (L-CONN-063). A newly created
Connected App could no longer be given a client-credentials Run As user: Setup > Edit Policies answered 'Invalid User'
for every user (integration, admin, API-only), and the Metadata API silently dropped `oauthClientCredentialUser`. Older
apps keep the Run As they got at creation. To rotate onto a new app:
1. Create an External Client App with the client-credentials flow running as the integration user, and read its secret
   once (it is shown once).
2. Point the CAI REST connection at it by re-importing the connection with OVERWRITE and republishing (L-CAI-061).
3. Prove one real call, then block the old app (its token call then returns `app_blocked`).
4. For the integration user's password: the REST `/password` resource returned NOT_FOUND; SOAP `setPassword` worked.
   Delete the user's `AuthSession` records to revoke live sessions (old cached sessions then get 401
   `INVALID_SESSION_ID`).
5. Update the IDMC Salesforce connection in the same minute (the security token can stay empty when the agent's IP
   is trusted); a task that logs in during the swap can fail once, so rerun it. Measured: all CAI logins moved within
   minutes, 87 integration logins after rotation, 0 failures.

**Errors and fixes.**

| Signature | Meaning | Fix |
|---|---|---|
| `invalid_client_id` on the token call | The connection's consumer key does not match the Connected App | Fix the key, re-import and republish, re-test before switching callers |
| 'Invalid User' when setting a client-credentials Run As user | A newly created Connected App | Use an External Client App (L-CONN-063) |
| `app_blocked` on the token call | The app was blocked after a rotation | Point the connection at the new app |
| 401 `INVALID_SESSION_ID` | A cached session revoked by deleting `AuthSession` records | Log in again |
| "Foreign key external ID not found" | The parent record of an external-id relationship does not exist yet | Retry in real time; for reconciliation re-send without the relationship, then re-link (L-CAI-063) |
| New Contacts silently blocked | An active CRM duplicate rule | Decide where dedup lives; adjust the rule (L-CAI-064) |
| `STORAGE_LIMIT_EXCEEDED` behind a CAI 500 | The target org is out of storage | Free space; check the target before debugging CAI (L-CAI-080) |
| One of two simultaneous calls returns 500 | Two callers upserting the same record in the same second | One caller per record per event (L-CAI-079) |

---

## 7. Upsert patterns (L-CAI-059, L-CAI-083, L-CAI-085)

1. **Idempotent upserts by external id.** `PATCH.../sobjects/<Object>/<ExtIdField>/<value>` creates or updates, so
   retries are safe.
2. **Parents by external id, not by read-back.** Link children with relationship fields such as
   `"<Parent>__r":{"<ParentExtIdField>":"<value>"}`; this removes the round trip of reading parent ids back before
   child writes (the same pattern shortens batch pipelines).
3. **Build the payload in XQuery.** JSON-escape strings, emit a number only when it is `castable as xs:decimal` (else
   `null`), map booleans from 'true', 't', '1' and 'yes', and omit a relationship entirely when its parent key is empty.
   Omit any field you have no value for: a PATCH that carries an empty field sets it empty in the target (L-CAI-038).
4. **Retry the retryable.** Parent not landed yet, DUPLICATE_VALUE, UNABLE_TO_LOCK_ROW, REQUEST_LIMIT and 5xx: retry
   after 3, 6 and 12 s; skip beyond a burst limit and let the scheduled batch reconcile.
5. **Keep test identities out at the source.** Filter them in the relay or in the source query of every sync, not by
   deleting them in the target, where the next run would recreate them.
6. **One rule in every writer.** If a batch task also writes the same fields, apply the same transformation there and
   prove it with a full diff.
7. **Measure.** Application call to SaaS record through CAI: about 0.2-2 s (L-CAI-084).

---

## 8. Overturned beliefs (this area)

| Belief | Believed | Overturned by |
|---|---|---|
| Secrets inside an app connection can only be set in the UI | 2026-07-08 to 09-25 | L-CAI-061 (L-CAI-103) |
| CAI authoring (connectors and connections included) is UI-only | 2026-07-04; 2026-09-20 to 09-22 | L-CAI-016, L-CAI-020 (L-CAI-101) |
