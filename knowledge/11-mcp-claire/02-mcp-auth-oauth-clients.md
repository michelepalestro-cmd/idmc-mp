# MCP Auth & OAuth Clients

**Answers:** Which credential should an MCP caller use: session, JWT, OAuth client credentials or an OAuth 2.1 public
client? How do I create, scope, rotate and delete OAuth clients headless? How do I get a token? How do I connect Claude
Desktop or Cowork to the hosted servers?

**Read when:** wiring a daemon, gateway or interactive client to managed MCP servers; a token expires too soon; a
password rotated; an MCP call returns 401 or `IDS_085`.

**Key rules:**
- Daemons, gateways and agents use an OAuth client-credentials token; interactive human-in-the-loop clients use an
  OAuth 2.1 public client with per-user consent (L-MCP-023, L-MCP-119, L-MCP-123).
- Create OAuth clients headless with `POST.../a2e-mcp-asset-mgmt-svc/api/v1/oauth2clients` (v3 session): 201 with
  `clientId` and `clientSecret` (L-MCP-018).
- The secret is shown once: write it straight to a 0600 file, print none of it, and recreate the client if any part
  leaks (L-MCP-019).
- `accessTimeout` is in minutes (5-1440), and the client stores its creator's password: recreate it and update every
  consumer when that password rotates (L-MCP-020, L-MCP-021).
- A valid credential on the wrong domain or pod answers 400 `IDS_085`; each managed server holds its own session, so a
  401 on one says nothing about the others (L-MCP-025).
- In Claude Code, `/informatica-idmc-headless:connect-mcp` creates a scoped client-credentials client (dry run, then `--execute
  --expect-org`), writes it to `~/.idmc_toolkit/mcp_client.env` (0600), and the plugin's bridge
  (`toolkit/lib/idmc_mcp_bridge.py`) uses that file to offer the servers' tools, read-only by default (§3.4).
- Since the October 2026 release the two OAuth servers are named "Informatica OAuth Server (Client Credentials Grant)"
  and "(Authorization Code Grant)"; Authorization Code clients carry `mcp:tools:read|write|execute` scopes (L-MCP-133).

**Related:** [01 Managed MCP Servers](01-managed-mcp-servers-catalog-access.md) ·
[04 Agent-Style MCP & Custom Shims](04-agent-style-mcp-async-orchestration-custom-shims.md) ·
[Access, Auth & Orgs](../01-login-and-orgs) ·
[Secrets Hygiene](../14-working-with-claude/06-secrets-hygiene.md) · [Lessons: CLAIRE & MCP](lessons.md)

**Last verified:** 2026-11-20

> **Summary.** Managed MCP servers accept a **session ID** (`IDS-SESSION-ID`), an identity **JWT**
> (`Authorization: Bearer`, 30 minutes from grant, refreshed from a ~8 h identity session), or an **OAuth token**
> (`Authorization: Bearer`). MCP itself is free in the preview; the backing calls bill IPUs
> ([IPU, Metering & Licensing](../13-ipu-cost)). Catalog of servers:
> [MCP catalog reference](../reference/idmc-api-mcp-reference/content/30-mcp-servers.json).

---

## 1. Pick the credential

| Method | Header on MCP calls | Lifetime | Use for | Evidence |
|---|---|---|---|---|
| Session ID | `IDS-SESSION-ID: <sessionId>` | the login session | quick interactive tests | documented (vendor guide pp.12-14); used with the registry and oauth2clients routes |
| Identity JWT | `Authorization: Bearer <jwt>`; for the DQ agent also `IDS-SESSION-ID: <sessionId>` | **30 min from grant** (not from last use) | scripts and shims that already hold a user login | proven (DQ agent) |
| OAuth client credentials (direct) | `Authorization: Bearer <access token>` | `accessTimeout` minutes (5 to 1440) | daemons, gateways, agents: the agent never holds a user's IDMC password | proven (gateway, `verify_address`) |
| OAuth 2.1 public client | `Authorization: Bearer <per-user token>` from an authorization-code grant; no client secret | the IdP-issued token | Claude Desktop / Cowork connectors and other human-in-the-loop MCP clients (§6.1) | documented by the vendor, not exercised (L-MCP-123) |
| OAuth federated | `Authorization: Bearer <IdP JWT>` | the IdP's | orgs on SAML SSO with an external IdP (Okta, Azure AD) | documented only |

Federated OAuth prerequisites (vendor):

- the org is configured for SAML, with its users set up as SAML users;
- an OAuth IdP is set up;
- the IdP's authorization server is **registered through the Administrator REST API "Identity providers" resource**.

---

## 2. Session ID and JWT (L-MCP-024)

### 2.1 Get a session

Either login works as the source of the session:

- v3 platform login: `POST https://<domain>.informaticacloud.com/saas/public/core/v3/login` with
  `{"username":"<user>","password":"<pw>"}` → `userInfo.sessionId`;
- identity login: `POST https://<domain>.informaticacloud.com/identity-service/api/v1/Login` → `sessionId` (read it from
  `userInfo.sessionId`, `sessionId` or `session_id`, depending on the response).

The login host is the **domain** host (`dm-us`, `dmp-us`,...), never the pod host. A right credential on the wrong
domain or pod answers **400 `IDS_085`** "User name or password is not valid". It looks like a bad password, but it is a
routing mistake (L-MCP-025). A few rejected logins lock the account: one attempt, then stop (see
[Access, Auth & Orgs](../01-login-and-orgs)).

### 2.2 Mint the JWT

```
GET  https://<domain>.informaticacloud.com/identity-service/api/v1/jwt/Token?client_id=idmc_api&nonce=<fresh uuid>
IDS-SESSION-ID: <sessionId>
→ {"jwt_token": "<~2,100 characters>"}
```

- `client_id=idmc_api` worked for the managed MCP servers. `client_id=cdlg_app` is the one used for the CDGC API host
  and MDM search.
- The vendor's documented form is a POST that also sends `Cookie: USER_SESSION=<sessionId>`.
- Use a **fresh nonce** per request.
- **Two token tiers:** cache **both** the identity session (~8 h) and the JWT (30 min). Re-mint the JWT from the
  still-valid session, about 5 minutes before expiry. A full re-login is needed only after the session dies. One
  reference fleet measured a cold start (login) of 6-8 s and a warm start of ~0 s from a disk cache.
- **Each MCP server holds its own session state:** a 401 on one server says nothing about the others (L-MCP-025).

### 2.3 Headers for a managed server

```
Authorization: Bearer <jwt_token>
IDS-SESSION-ID: <sessionId>
MCP-Protocol-Version: 2025-06-18
Accept: application/json, text/event-stream
Content-Type: application/json
```

---

## 3. OAuth clients, headless (L-MCP-018)

### 3.1 Create

```
POST https://hdm.<domain>.informaticacloud.com/a2e-mcp-asset-mgmt-svc/api/v1/oauth2clients
IDS-SESSION-ID: <v3 login sessionId>
Content-Type: application/json
```

```json
{"providerType":"IDMC_MCP",
 "clientName":"<name>",
 "description":"<text>",
 "credentials":{"username":"<user>","password":"<pw>"},
 "accessTimeout":1440,
 "enabled":true,
 "mcpServers":[{"id":"<serverId>","name":"<server name>","serverEndpointUrl":"<url>","context":"<context>","serverPolicy":null}]}
```

- **Success:** 201 with `clientId` and `clientSecret`.
- **`mcpServers[]`** lists the servers the client may reach. Copy `id`, `name`, `serverEndpointUrl` and `context`
  straight from the registry read (`GET.../mcp-servers?type=MANAGED`,
  [01](01-managed-mcp-servers-catalog-access.md) §2). Scope it narrowly: one working client listed 12 of the org's
  19 servers.
- **Shapes that did not create a client:** `mcpServersDetails`, `mcpServerIds`, `servers`, `resources`.
- **`accessTimeout` is in minutes** (see §4). One early note wrote it as seconds; that is wrong (L-MCP-020).
- **How the route was found.** It is not in the vendor guide, which documents only the UI wizard. It was found by
  recording the UI's own requests with a headless browser while a client was created in the MCP Server Authorization
  page. That is a reusable method for finding undocumented routes
  ([Claude Working Methods & Tooling](../14-working-with-claude)).

### 3.2 List, read back, delete

```
GET.../a2e-mcp-asset-mgmt-svc/api/v1/oauth2clients?type=IDMC_MCP&page=1&size=50&sortBy=lastModifiedDate&sortOrder=desc&grantType=client_credentials
       → {"content":[ {client},... ]}
DELETE.../a2e-mcp-asset-mgmt-svc/api/v1/oauth2clients/<clientId>
```

Read-back after create: the list shows the client with its servers. The real proof is a token plus one tool call (§5).

### 3.3 Handle the secret (L-MCP-019)

The create response is the **only** time the secret is shown, both over REST and in the UI wizard.

- Write it straight into a file opened with `os.open(path, os.O_WRONLY|os.O_CREAT|os.O_TRUNC, 0o600)`, and print none
  of it. The file needs:

```
IDMC_CLIENT_ID=<clientId>
IDMC_CLIENT_SECRET=<secret>
IDMC_TOKEN_URL=https://<domain>.informaticacloud.com/authz-service/oauth/token
MCP_BASE=https://mcp.<domain>.informaticacloud.com/mcp-servers/public/
```

- Mask the password in any echoed error (`str(err).replace(pw, "***")`).
- **If even a prefix of the secret reaches a log or a transcript, delete the client and create a new one**, quietly. In
  one run the first attempt's prefix reached a local log, so the client was deleted and recreated.
- A compromised client: **Disable** stops token issuance without deleting it (UI), or delete and recreate it over REST.
- Keep client secrets in a secret manager or a 0600 env file on the consuming host, one item per role or consumer
  (L-MCP-048).

### 3.4 The plugin does this for you: `/informatica-idmc-headless:connect-mcp`

The plugin's command runs §3.1 to §3.3 and §5 with the toolkit, so nobody hand-writes the calls:

1. `python3 toolkit/lib/idmc_mcp.py servers` lists the org's servers (an empty list or 403: MCP is off or the user
   lacks the AI Agent Engineering privileges).
2. `python3 toolkit/lib/idmc_mcp.py client-create --name claude-code-mcp --contexts <c1,c2,...>` is a dry run; the
   same with `--execute --expect-org <orgIdV3>` creates the client and writes the secret straight to
   `~/.idmc_toolkit/mcp_client.env` (0600, never printed). `--allow-writes` adds `IDMC_MCP_ALLOW_WRITES=1`.
   `clients` lists clients and `client-delete <clientId> --execute --expect-org <orgIdV3>` removes an old one.
3. The plugin starts the bridge `toolkit/lib/idmc_mcp_bridge.py` as its MCP server (`plugin.json` `mcpServers`). It
   reads that file, takes a client-credentials token (Basic auth, `grant_type=client_credentials`) and offers each
   server's tools as `mcp__plugin_informatica-idmc-headless_idmc__<server>_<tool>`. Read-only by default: only reading tools are offered
   unless the file holds `IDMC_MCP_ALLOW_WRITES=1`. Without the file it offers one status tool and makes no call.
4. `python3 toolkit/lib/idmc_mcp_bridge.py --check` lists the servers and tools before a restart of Claude Code.

The client stores its creator's password (§4): after that password changes, run the command again.

---

## 4. Token lifetime and rotation

- **`accessTimeout` is minutes (L-MCP-020).** The UI default is 5 minutes and the range is 5 to 1440.
  `"accessTimeout":1440` produced tokens with `expires_in` = 86,400 s (24 h). Five minutes breaks any background
  enrichment job or gateway, so raise it deliberately.
- **The client stores its creator's username and password (L-MCP-021).** When that user's password
  changes, recreate the client and copy the new secret to **every consumer** (gateways, cron jobs, scripts). Keep a list
  of consumers next to the client name.
- **Regenerate Secret** in the UI re-authenticates with the username and password first. It is the recovery path when a
  secret is lost.

---

## 5. Getting and using a token

The Informatica OAuth server uses the **client-credentials** grant over **HTTP POST** (OAuth 2.0), at
`https://<domain>.informaticacloud.com/authz-service/oauth/token` (the MCP Server Authorization page shows the endpoint).
The request is the standard OAuth 2.0 client-credentials shape. The exact body was not recorded in these sources, so
verify it on your org:

```
POST https://<domain>.informaticacloud.com/authz-service/oauth/token
Authorization: Basic <base64(clientId:clientSecret)>      (the wizard also shows this "authentication header value")
Content-Type: application/x-www-form-urlencoded
grant_type=client_credentials
→ {"access_token":"<token>","expires_in":<seconds>,...}
```

Then call a managed server with `Authorization: Bearer <access_token>` on its `serverEndpointUrl`. A gateway that refreshed
this token served 83 Informatica tools, and `verify_address` answered Status Ok.
[04](04-agent-style-mcp-async-orchestration-custom-shims.md) §6.4 covers the gateway pattern.

---

## 6. The UI lifecycle (vendor; Configuration → MCP Server Authorization) (L-MCP-022)

| Operation | Where | What to know |
|---|---|---|
| Add OAuth client | Add OAuth Client wizard: **Authentication** (your IDMC username and password) → **Details** (name, description, access-token timeout) → **Resources** (which MCP servers) → **Generate Credentials** | Shows the client ID, the secret and the auth header value (base64 of `id:secret`) **once** |
| Edit | edit icon | name, description, timeout, server scope |
| Regenerate secret | Actions → Regenerate Secret | re-authenticates first |
| Disable / enable | Actions | Disable stops token issuance without deleting; enabled on creation |
| Delete | delete icon | for clients no longer needed |
| Download report | Download CSV | every client with status, servers and last update. It ignores on-screen filters, which makes it a good audit artifact. |

### 6.1 OAuth 2.1 public client for interactive MCP clients (documented by the vendor, not exercised; L-MCP-123)

Since the October 2026 release this server is called "Informatica OAuth Server (Authorization Code Grant)" and its
clients "Authorization Code" clients, with the scopes `mcp:tools:read`, `mcp:tools:write`, `mcp:tools:execute` (and
`mcp:resources:read` for resources); clients created earlier inherit the three tool scopes (L-MCP-133).

The vendor publishes an "Informatica" plugin for Claude Enterprise (Claude Desktop, Cowork and Claude Code). It bundles a
`catalog-and-data-discovery` skill (metadata-first discovery: terms, ownership, certification, PII tags; missing metadata
is reported as a gap, not guessed) and two connectors to the hosted servers Catalog Discovery and CLAIRE Data Exploration
Agent. It is the interactive, per-user counterpart of the client-credentials client in §3.

| Credential | Grant | Secret | Use for |
|---|---|---|---|
| OAuth 2.0 client (§3) | client credentials | yes, shown once | headless agents, gateways, CI |
| OAuth 2.1 client, Public | authorization code, per user (IDMC login + consent) | none | Claude Desktop / Cowork connectors, other human-in-the-loop MCP clients |

1. **IDMC (org admin):** AI Agent Engineering > Configuration > MCP Server Authorization > **Informatica OAuth 2.1** >
   Add OAuth 2.1 Client. Name it; **Token Endpoint Authentication Method: Public**; callback URL
   `https://claude.ai/api/mcp/auth_callback`; select **Catalog Discovery** and **CLAIRE Data Exploration Agent**; Create;
   copy the Client ID (a public client has no secret).
2. **Claude Desktop (organization admin):** Organization settings > Connectors > Add > All available: add
   *Informatica Catalog Discovery* (`https://mcp.<domain>.informaticacloud.com/mcp-servers/public/cdgccatalogdiscovery`)
   and *Informatica Data Exploration* (`https://mcp.<domain>.informaticacloud.com/mcp-servers/public/dataexplorationagent`),
   each with the Client ID.
3. **Each user:** Settings > Plugins > Discover > Informatica > Add, then **Connect** each connector: the browser opens the
   IDMC login, and "Continue Connecting" completes the per-user grant (both rows show a check mark).
4. **Verify:** in a new Cowork conversation, "+ > Plugins" shows the plugin and its skill (turn it on under Browse
   plugins > Your plugins if missing).

Prerequisites: a Claude Enterprise plan; an IDMC user with catalog permissions; a runtime environment running the Data
Gateway (data exploration runs through it, [03](03-claire-gpt-prompting-rules-patterns.md) §6); an IDMC admin to
create the client. The OAuth 2.1 server for human-in-the-loop clients is documented in the vendor MCP guide (L-MCP-119).

**In Claude Code** the vendor plugin's source ships its two server URLs empty, so it does nothing until you add your
pod's URLs and a credential yourself (L-MCP-135); `/informatica-idmc-headless:connect-mcp` (§3.4) covers every server the org lists.
Agent platforms built on Microsoft's MCP catalog get five Informatica servers with client-credentials manifests
(L-MCP-136).

---

## 7. Privileges and roles

- **MCP privileges** (vendor, chapter 3):
  - feature privileges **Execute Managed MCP Servers** and **View Managed MCP Servers**;
  - asset privileges **MCP Server** and **Deployed MCP Server**, for composite servers.

  Admin and Designer hold them by default. Operator can run but cannot create composite servers.
- **A login that drives all of CDI, CAI, CDQ, CDGC governance and CLAIRE** needed Admin, Designer, Governance
  Administrator and **CLAIRE GPT User** (L-MCP-068). Check this first in a new org.
- Hold credentials per role, not per person. A 403 then becomes "log in as the role that has it" rather than a
  debugging session (L-MCP-048).

---

## 8. Metering (L-MCP-026)

During the AI Agent Engineering preview, MCP server usage is not separately monetized. Every backing CDGC, CDI,
Marketplace or MDM call still bills IPUs at the service rate card (vendor guide p.7). Budget the underlying service, not
the MCP layer. Loops, parallel sub-agents and chatty gateways multiply backing calls
([IPU, Metering & Licensing](../13-ipu-cost)).

---

## 9. "The org must switch REST authentication to JWT for MCP": disputed (L-MCP-027)

Informatica staff once told a team that using MCP requires the org's REST authentication type switched from Session ID
to JWT. That is an org-admin toggle: Administrator → Settings → General settings → Authentication type. The
flip has blast radius: every client that authenticates with a session header (`INFA-SESSION-ID`, `icSessionId`) must move
to Bearer JWT first. Plan the flip with a code path per mode, a quiet window and a rollback.

**Status: disputed, untested.** The vendor guide says session-ID *or* JWT authentication works, "depending on how the org
is configured". Later sessions called managed servers successfully with Bearer JWT plus `IDS-SESSION-ID`, and with OAuth
tokens. Whether that org's toggle had been flipped is not recorded. Check the setting before you change it, and never
flip it under a live workload. Plan the move anyway: the vendor documents session-ID REST authentication as deprecated,
with JWT the default after the October 2026 release (L-AUTH-033;
[Access, Auth & Orgs](../01-login-and-orgs)).

---

## 10. Overturned beliefs (kept so nobody re-learns them)

| Belief | Held | Overturned by | Lesson |
|---|---|---|---|
| "MCP OAuth clients are created only in the UI wizard; the secret is shown once" | 2026-07-26 (guide); a migration runbook draft of 2026-09-28 | `POST.../a2e-mcp-asset-mgmt-svc/api/v1/oauth2clients` → 201 + secret (2026-09-28). "Shown once" still holds. | L-MCP-072 → L-MCP-018 |

---

## 11. Open questions

- The exact token request body the authz service accepts (form vs JSON, Basic header vs body credentials).
- Whether an OAuth client can be created without embedding a user password, for example for a service account.
- Whether federated OAuth tokens work with every managed server.
- The org REST-auth-mode requirement for MCP (§9).
