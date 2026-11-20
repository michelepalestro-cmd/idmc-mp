# Script Library: drive IDMC headless from any org

**Answers:** Which generic scripts drive IDMC headless, how are they configured for your org, and which guards do they
apply before a write?

**Read when:** before running or adapting any script from this folder, or when a topic doc names one.

**Key rules:**
- Every script is a dry run until `--execute --expect-org <orgIdV3>`; a destructive call takes explicit ids, a backup
  and a receipt line, and spend waits for approval (L-METHOD-065).
- One login per session through the shared session cache and its block file; never loop logins (L-AUTH-036,
  L-AUTH-041).
- Credentials come from the environment or a 0600 file outside the plugin (`~/.idmc_toolkit/IDMC_LOGIN.txt`), and scripts print key names, never values
  (L-METHOD-001, L-METHOD-087).
- Read the body and read back every write: a 200 can be fake or silently reverted (L-METHOD-025, L-METHOD-030).
- These scripts were not run against a live org in this form: re-verify each call in yours (L-METHOD-035).

**Related:** [Access, Auth & Orgs](../../knowledge/01-login-and-orgs) ·
[Secure Agent & Connections](../../knowledge/02-secure-agent) ·
[Data Integration (CDI)](../../knowledge/04-mappings) · [Mass Ingestion & CDC](../../knowledge/06-cdc-ingestion) ·
[Application Integration (CAI)](../../knowledge/07-app-integration) ·
[Catalog & Governance (CDGC)](../../knowledge/09-catalog-lineage) · [CLAIRE & MCP](../../knowledge/11-mcp-claire) ·
[Migration & Org Management](../../knowledge/12-deploy-migrate) · [Lessons Learned](../../knowledge/lessons)

**Last verified:** 2026-10-04 (structure). Source evidence 2026-07 to 2026-09; compile-checked and exercised offline
with mocked HTTP on 2026-09-29; none of these scripts has been run against a live org in this form.

A small set of generic, stdlib-only Python scripts that let a Claude session drive Informatica IDMC without
the UI, in any org. It covers login and org proof, object inventory, v3 export/import and package editing,
mapping tasks, linear taskflows and schedules, runtime-environment selections, Database Ingestion (CDC), CAI
publish, CDGC, guarded deletes, managed MCP servers and route probing. Each script was adapted from code proven
in 2026-07..09 against production orgs, then sanitised and parameterised. **Re-verify every call in your org.**

---

## 1. Install and run

- Python 3.10 or newer. **No third-party packages**: everything uses the standard library (`urllib`, `json`,
  `zipfile`, `hashlib`). `requests` is not needed.
- Copy the whole folder: every script imports `idmc_http.py` and `idmc_session.py` from its own directory.
- Check it: `python -m py_compile *.py` (all 15 files pass).
- Every script has `-h`. Subcommands that only read are safe to run at once. Anything that changes the org
  prints its request and stops, unless you add `--execute --expect-org <orgIdV3>`.

## 2. Credentials: one file, `~/.idmc_toolkit/IDMC_LOGIN.txt`

Fill in `~/.idmc_toolkit/IDMC_LOGIN.txt` (three `KEY=value` lines: the first three keys below; `toolkit/check_login.py`
creates it) and save; the library finds it by itself. Precedence: environment variables first, then `IDMC_CREDS_FILE`
(a per-org file outside the plugin), then `~/.idmc_toolkit/IDMC_LOGIN.txt`, then a repo-root `IDMC_LOGIN.txt` (only as
a git-clone legacy fallback; the home file always wins). Never share or commit a folder that holds a filled-in login
file. Credentials are sent only over https to a `<domain>.informaticacloud.com` host.

| Variable | Meaning |
|---|---|
| `IDMC_USER` | Full login name. A truncated name gives a false `IDS_085`. |
| `IDMC_PASS` | Password. |
| `IDMC_LOGIN_HOST` | The **domain** host `<domain>.informaticacloud.com` (for example the `dm-us` or `dmp-us` label). A pasted browser address or pod host is reduced to it (a pod host answers 404 on login). The wrong domain answers `IDS_085`, which looks like a bad password. |
| `IDMC_CREDS_FILE` | Optional `KEY=value` file (for example one per org); its values win over `IDMC_LOGIN.txt`. It must live **outside** the plugin; the scripts refuse a path inside it. Environment values win. |
| `IDMC_CACHE_DIR` | Session caches, the login lock, the block file and its HMAC key. The default is `~/.idmc_session` (0700; files 0600). It is refused inside the plugin. |
| `IDMC_PROFILE` | The cache name. Use one per org. The default is a hash of user and login host. |
| `IDMC_MCP_ENV_FILE` | Default `--env` for `idmc_mcp.py` (the 0600 OAuth file that `client-create` writes). |

Rules:

- Never put a password on a command line: it lands in shell history and in transcripts.
- Session ids, JWTs and OAuth tokens stay in memory or in 0600 cache files. They are redacted in all output and
  logs (`redact()` masks by key name, case-insensitively by substring: password, secret, token, api key, private key,
  session id, cookie, credential, signature...; it also masks the `value`/`values` of `{"key": "<secret name>"}` pairs,
  and printed JSON answers are redacted too).
- Redirects are followed only to https on the same host, so session headers never leave it; `Session.call` refuses an
  absolute URL outside the login's `<domain>.informaticacloud.com`.
- Export packages can hold plaintext secrets. For example, a CAI app connection saved with `encrypted="false"`
  carried an OAuth client secret into every later export. Exports and edited packages are written 0600. Keep
  packages outside the plugin and out of any repo.
- An OAuth client secret is shown once. `idmc_mcp.py client-create` writes it straight to a new 0600 file and
  never prints it. If any part of a secret reaches a log, delete the client and create a new one.

## 3. The safety model (applies to every script)

1. **Dry-run by default.** A write prints `[DRY-RUN] <label>: <METHOD> <plane>:<path>` and its redacted body,
   and sends nothing. The reads it needs, such as the GET for a diff preview, still happen.
2. **`--execute` needs `--expect-org <orgIdV3>` for every write.** This is stricter than "destructive only" on
   purpose: wrong-org writes were the costliest risk in the source work. Before the first write, the gate
   runs `Session.require_org()`, which:
   - reads `GET /api/v2/org` live and requires its `id` to equal the session's v2 org id;
   - requires every v3 org id seen (the login's `orgUuid`, `/api/v2/org` `orgUuid`, and the session-service user
     when it answers) to equal the id you passed;
   - stops with "ORG GUARD FAILED, nothing sent" on any difference.
3. **Read back after every write and print what changed.** Bindings are compared field by field; a 200 whose
   value reverted is reported as a silent rejection. The FRS delete checks each object with
   `GET /frs/v1/BaseEntities('<id>')`. Imports list their per-object results.
4. **`--log FILE`** appends every write and its read-back as redacted JSON lines.
5. **Lockout guard.** A few rejected logins lock an account (`IDS_086`), and every retry restarts the lock.
   - Logins are serialised by a file lock, and the cache is re-checked after the lock is taken.
   - Each run makes one attempt; there are no retry loops.
   - A rejected login (4xx) writes a block file keyed by a fingerprint of the credentials (HMAC-SHA256 under a
     random per-machine key kept 0600 in `IDMC_CACHE_DIR`). While the fingerprint matches, no process logs in
     again, `toolkit/mapgen` included (it logs in through this library). Fix the credentials, which changes the fingerprint, or have
     a human confirm them in a browser, then delete the block file.
   - 5xx, 429 and network errors stop the run without a block.
   - Sessions die about 30 min after grant, whatever the activity, so re-login happens at 24 min. An API 401
     drops the cache and logs in once more, at most once per call and once per 5 minutes per session.
6. **Idempotent where it matters.** Existing names are updated rather than duplicated. A name that exists twice
   is refused, because the same task name can live in unrelated folders: address tasks by id. Glossary items
   are tracked in a registry file.

Evidence words used below: **PROVEN 2026-09** means the call worked against a production org in September 2026.
**ADAPTED** means the logic around a proven call was changed or combined (re-verify it). **UNTESTED** means
documented or inferred only.

## 4. The scripts

| Script | Lines | What it is for | Writes? |
|---|---|---|---|
| `idmc_http.py` | 313 | Shared plumbing: HTTP that never raises, response verdicts, redaction, multipart, poll, diff, JSONL log, the `WriteGate`. | n/a (library) |
| `idmc_session.py` | 426 | Guarded v2 + v3 login, pod hosts, plane headers, JWT mint, `whoami`, `require_org`. CLI `whoami`, `hosts`, `get`. | no |
| `idmc_objects.py` | 197 | v3 object list/search/census, references, path lookup, v2 detail GETs, v2 <-> v3 id resolution. | no |
| `idmc_export_import.py` | 202 | v3 export -> package; upload -> start -> poll -> per-object result -> log; REUSE / OVERWRITE with a NEW/EXISTS preview. | import |
| `idmc_package_edit.py` | 260 | Offline package surgery: replace or regex-edit a file (nested zips too), drop objects, remap an id, and fix `exportMetadata.v2.json` and `exportPackage.chksum`. | local file only |
| `idmc_mttask.py` | 254 | Mapping tasks: show, clone a template task (upsert by name), change `customQuery` safely, run via `/api/v2/job`, read logs. | yes |
| `idmc_taskflow_schedule.py` | 225 | Linear taskflows and schedules: upsert, create or end schedules, bind/unbind (also task level), audit, snapshot/restore, run. | yes |
| `idmc_runtime_selections.py` | 162 | Runtime-environment services and connectors: show, set with a diff and a "never select all" guard, restore. | yes |
| `idmc_dbmi.py` | 167 | Database Ingestion on `<pod>-ing`: list, details, status, create, deploy, start/stop/resume/undeploy, delete once undeployed. | yes |
| `idmc_cai_publish.py` | 161 | CAI publish/unpublish in dependency waves, per-item check, publication-status read-back. | yes |
| `idmc_cdgc.py` | 273 | CDGC: JWT check, catalog sources (multipart create/update), scans and jobs, ES search, glossary with registry and undo, term links. | yes |
| `idmc_frs_delete.py` | 206 | Guarded deletes: FRS dependency check, KEEP guards, leaf-first `DeleteEntities` rounds, per-item codes, read-back; v2 DELETE with read-back. | yes |
| `idmc_mcp.py` | 257 | Managed MCP: registry, OAuth clients (secret to a 0600 file), `tools/list` and `tools/call` (OAuth or session auth, nested envelope, async poll). | yes |
| `idmc_probe.py` | 157 | Route discovery: bogus-twin comparison, empty-POST verb probe, Content-Type variation, DNS sweep, GET sweep. | verbs/ctypes only |

### Planes, hosts and headers (from `idmc_session.py`)

All hosts are derived from the login answer (`serverUrl`; `products[].baseApiUrl` is cross-checked by `whoami`).
The pod host is split at its first dot, so `<pod>-cai.<domain>...` is computed rather than hard-coded; an older
string-replace of a pod literal broke when the org moved to another pod.

| Plane | Host | Header set |
|---|---|---|
| `v2` / `v3` | `https://<pod>.<domain>.informaticacloud.com/saas` + `/api/v2/...` or `/public/core/v3/...` | `icSessionId` / `INFA-SESSION-ID`, both carrying the v2 session id (PROVEN 2026-09) |
| `frs`, `runtime` | `https://<pod>.<domain>.informaticacloud.com` + `/frs/...` or `/runtime/...` | `IDS-SESSION-ID` (v2 id); `INFA-SESSION-ID` there returns the login HTML |
| `dbmi` | `https://<pod>-ing.<domain>.informaticacloud.com` | `IDS-SESSION-ID` + `INFA-SESSION-ID` + `icSessionId` |
| `cai` | `https://<pod>-cai.<domain>.informaticacloud.com` | `INFA-SESSION-ID`; Accept and Content-Type `application/vnd.api+json` |
| `cdgc` / `d360` | `https://cdgc-api.<domain>...` / `https://idmc-api.<domain>...` | Bearer JWT (`client_id=cdlg_app`) + `X-INFA-ORG-ID: <orgIdV3>` + `IDS-SESSION-ID` |
| `hdm`, `profiling` | `https://hdm.<domain>...`, `https://<pod>-dqprofile.<domain>...` | `IDS-SESSION-ID` with the **v3** session id (the v2 id got 401 on one pod) |
| `session` | `https://<pod>.<domain>.informaticacloud.com/session-service/...` | `IDS-SESSION-ID` + `USER_SESSION` cookie (UNTESTED headless; `whoami` treats it as optional) |
| managed MCP | `https://mcp.<domain>.informaticacloud.com/mcp-servers/public/<context>` | OAuth Bearer (client credentials), or a session JWT `client_id=idmc_api` + `IDS-SESSION-ID` |

### `idmc_session.py`: log in once, prove the org

- **Use it** first in every session: `python idmc_session.py whoami` (two logins; `--no-v3` for one), then
  `whoami --expect-org <orgIdV3>` before any write session. `hosts` shows the derived hosts. `get <plane> <path>`
  is a single read-only GET with a verdict (JSON / HTML-200 / EMPTY-200 / 404 kind).
- **PROVEN 2026-09:**
  - the v2 login returns `icSessionId`, `serverUrl`, `orgId` and `orgUuid`;
  - the v3 login returns `userInfo.sessionId`, `userInfo.orgId` and `products[].baseApiUrl`;
  - the v2 id works on the v2, v3, frs, runtime, dbmi and cai planes;
  - the JWT mint `POST /identity-service/api/v1/jwt/Token?client_id=cdlg_app&nonce=..&access_code=` with
    `IDS-SESSION-ID` and a `USER_SESSION` cookie works (the GET form with `client_id=idmc_api` was also proven);
  - `GET /api/v2/org` works.
- **ADAPTED / UNTESTED:** the session-service user read, and the Windows `msvcrt` lock (the POSIX `fcntl` lock
  pattern is proven).
- The guard was tested offline on 2026-09-29 with the network mocked. One rejected login wrote the block, three
  further attempts made zero network calls, and changing the credentials lifted it.

### `idmc_objects.py`: find things (read-only)

- `list` pages `GET /public/core/v3/objects?limit=200&skip=N&q=...`. **The `q` filter is not validated**: a wrong
  type name returns 0 objects, not an error (`type=='DBMI'` returns 0 while the real type is `DBMI_TASK`), so
  run `census` for the real names. It also filters client-side (`--path-prefix`, `--name-contains`).
- `refs` walks `/objects/<id>/references?refType=uses|usedBy`. `lookup` uses `POST /public/core/v3/lookup`
  (read-only).
- `resolve` maps ids in both directions:
  - a v2 MTT to its `frsGuid` (from the detail GET only; the list omits it);
  - a v2 workflow to its v3 id by exact name among WORKFLOW objects (exactly one match required);
  - a v3 id back to the v2 task (tries `GET /api/v2/mttask/<v3id>`, ADAPTED, then a bounded detail scan).
- A one-off 500 "Objects Listing Failed" seen during a peer's import is retried once.

### `idmc_export_import.py`: move design content

- `export` (changes nothing in the org, so no `--execute`):
  - `POST /public/core/v3/export` with `objects:[{"id","includeDependencies"}]`, then poll, then
    `GET /export/<id>/package`;
  - checks the PK magic and prints the object count per type;
  - a scope of about 200 objects exported in about 20 s.
- `import`:
  - previews each packaged object as NEW, REUSE or OVERWRITE (by path lookup);
  - uploads multipart to `/import/package` (field `package`) and **never starts a job whose `checksumValid` is
    false**;
  - starts it with `POST /public/core/v3/import/<jobId>`, then polls and prints the root failures (not the
    "skipped because of previous failures" noise), the per-object result and the log.
- Traps it prints: see the docstring. In short:
  - the import is all-or-nothing, and `includeObjects` does not exclude an object from validation;
  - `objectSpecification` returned `V3API_007` in every shape tried;
  - tags are dropped (re-tag with `TagObjects`);
  - nothing is published, deployed or scheduled;
  - use the object id, not a CAI process GUID (`MigrationSvc_034`).
- PROVEN 2026-09 end to end, in a 190-object org-to-org migration and in CAI/taskflow redeploys.

### `idmc_package_edit.py`: edit a package without breaking it (offline)

- `inspect` / `verify` recompute every path-keyed checksum line. GUID-keyed opaque lines are left as they are.
- `sub`:
  - makes a whitespace-tolerant regex replacement with an exact expected count, for example
    `--pattern '<process\b.*?</process>'`;
  - reads the replacement from a file, because shell heredocs once turned `\b` into a backspace byte;
  - handles nested zip members with `outer.zip!member`.
- `drop` removes whole objects: their files, metadata entries, chksum lines and CSV rows. It refuses while
  another object still lists them in `objectRefs`.
- `remap` swaps an id everywhere, nested zips included; `--drop-entry` removes the old metadata entry.
  - The default remaps `objectRefs`; that was proven for a runtime-environment reference the target lacked.
  - For a connection swap use `--refs keep`: a 2026-08 lesson found that adding the new connection GUID to
    `objectRefs` failed with `MigrationSvc_031`.
- Only the changed files' `SHA256` lines are rewritten (upper-case hex, Java-properties key escaping such as
  `\ `), and so is the line for `exportMetadata.v2.json` when it changes; otherwise the import fails with
  `MigrationSvc_073`. Files the package never checksummed (the contents CSV) stay unlisted.
- Rules PROVEN 2026-09 in real imports. Tested offline on synthetic packages on 2026-09-29.

### `idmc_mttask.py`: mapping tasks

- `clone` follows the proven pattern that ran a production pipeline of one task per table over the
  `dsst__copy_data_new_tgt` bundle template:
  1. GET the template task and strip the audit fields and parameter ids.
  2. Set name, `$Source$` (`sourceConnectionId`, `customQuery`, or a source object) and `$Target$` (object,
     `tgtObjectAttributes.parent`, `oprRuntimeAttrs` Bulk + Write truncate or Write append).
  3. Add `--fetch-runtime` when the target will gain columns. Without `fetchMode RUNTIME`, new columns are
     silently written as NULL.
  4. Upsert by name: create lands in Default, update POSTs to `/api/v2/mttask/<id>`; there is no PUT.
  5. Read back and diff.
  6. Optionally move the task with FRS `MoveEntities` and tag it.
- `set-query` replaces an anchor only if it occurs exactly once.
- `run`:
  - refuses when the activity monitor shows the task running (`REPO_17314` otherwise);
  - posts `/api/v2/job`, polls the activity log for the `runId` and prints rows and errors;
  - reports state 2 with 0 target rows as FAILED;
  - detects the monthly job cap message. Every task run and every taskflow run is one job, and the cap is
    invisible headless because the license API shows -1.

### `idmc_taskflow_schedule.py`: taskflows and schedules

- `upsert` builds a linear taskflow from task ids (names read from each task) and keeps the `scheduleId` on
  update.
- `schedule-create`:
  - creates the schedule unbound and is idempotent by name;
  - sets both `startTime` (pod-local) and `startTimeUTC`. v2 times are pod-local but labelled `Z` (UTC-4 on the
    pods seen), so the offset is derived from an existing schedule or taken from `--pod-offset-hours`.
- `schedule-end` sets both `endTime` and `endTimeUTC` (ADAPTED from the fix that worked).
- `bind`, `unbind`, `task-bind` and `task-unbind` POST the full body with `scheduleId` set or null and read it
  back.
- `audit` lists every workflow binding and every **task-level** binding. The MTT list hides `scheduleId`; a
  missed task-level schedule ran once more in the old org during a real cutover.
- `snapshot` then `restore` is the rollback baseline for a cutover.

### `idmc_runtime_selections.py`: agent services and connectors

- `GET/PUT /runtime/api/v2/runtimeEnvironment/<reId>/selections/ui` with `IDS-SESSION-ID`. PROVEN 2026-09; it
  was the first proven PUT recorded for IDMC.
- `set`:
  - backs up the GET body (the undo) and shows a diff;
  - refuses switching on more than `--max-enable` items (default 5), enabling every item in services or
    connectors, or disabling a mandatory item;
  - reads back after 5 s.
- The reason: selecting everything on a shared 4-vCPU host pulled about 18 GB, took the load to about 189 and
  filled swap.
- Every PUT also rolls DIS, Mass Ingestion and Connector Service to the newest build, so jobs queue about
  5 min. Change selections between runs, not during one.

### `idmc_dbmi.py`: Database Ingestion (CDC)

- PROVEN 2026-09 in a production cutover:
  - `task/create`;
  - `task/deploy/<taskId>` (an empty body is enough);
  - `job/start|stop|resume|undeploy {"jobId": <int>}`;
  - status via `GET /dbmi/api/v1/task/<taskId>/job` (`status`, `runId` = job id);
  - FRS `BaseEntities` delete.
- Ids on this plane are numeric; a GUID is refused because it gives a routing 404. `create` requires the
  location to be a project only.
- `delete` refuses unless the job is undeployed. `undeploy` prints the CDC hand-over rule: STOP, do not undeploy,
  when a slot moves to another task or org; rollback is then "stop new, resume old".
- There is no update verb (see the docstring for the two workarounds).

### `idmc_cai_publish.py`: CAI publish and unpublish

- The asset path format is `Explore/<project>/<folder>/<name>.<TYPE>.xml`. A bare path fails the item with
  `BAD_REQUEST 'Invalid asset path'`.
- Waves go service connector -> app connection -> processes, reversed for unpublish, at most 199 assets per call.
  The first failed wave stops the ones after it. Every `itemDetail[].itemState` is checked, because a 202 is only
  submission.
- The read-back uses the v3 `customAttributes.publicationStatus`.
- PROVEN 2026-09: 9/9 assets in a migration, plus cleanup unpublish waves.

### `idmc_cdgc.py`: catalog, scans, search, glossary

- Catalog-source create is multipart with one part named `dataSource` (plain JSON gives 415) and needs `custom`
  and `endOfLife`. `--map OLD=NEW` remaps connection and runtime-environment ids, and `--forbid-prefix` proves
  that no old-org id is left.
- Update is a multipart PUT (PATCH fallback) with a backup and a diff. Password option values are masked in all
  output.
- Scans read the source's capability names; an empty list gives a misleading 500. A scan bills IPUs.
- Search pages the ES endpoint and backs off on 429.
- The glossary uses a registry file for idempotency, and `glossary-undo` deletes in reverse.
- PROVEN 2026-09 in a catalog rebuild: 5 sources, 33 terms and 42 links. REST cannot delete a source definition
  (DELETE only purges its metadata); that is a UI step.

### `idmc_frs_delete.py`: delete safely

1. `deps` shows who uses an object and what it uses (`GetInboundDocRefs` / `GetAllDependencies`).
2. `delete` refuses:
   - Add-On Bundles content and the Default project;
   - anything in `--keep-file`;
   - published CAI assets (`FRS_082`; unpublish first);
   - objects referenced from outside the delete set, unless `--allow-inbound`.
3. It then deletes leaf-first in rounds (containers last), in batches of 25. It prints the per-item codes
   (`FRS_200`, `FRS_082`, `FRS_087`) and reads each object back (404 / `FRS_070` = gone).
4. `v2-delete` covers `mttask`, `mapping` (only when `tasks[]` is empty), `connection`, `agent`,
   `runtimeEnvironment`, `schedule` (read back from the list, because a deleted schedule's GET is an empty 200
   shell) and `workflow`.
- PROVEN 2026-09 in a production org cleanup of 80+ objects. Back up with an export first. Remember that a
  rejected or interrupted run may already have deleted objects: read back before you report.

### `idmc_mcp.py`: managed MCP servers

- `servers` reads the org's managed registry from the `hdm` host. One org had 19 servers with about 140 tools.
  Enumerate the whole registry before you call anything a wall.
- `client-create` builds `mcpServers:[{id,name,serverEndpointUrl,context,serverPolicy:null}]`; other body shapes
  did not create a client. It writes `IDMC_CLIENT_ID`, `IDMC_CLIENT_SECRET`, `IDMC_TOKEN_URL`, `MCP_BASE` and
  `IDMC_ORG_ID` to a new 0600 file.
- `tools` and `call` speak JSON-RPC over streamable HTTP: `initialize` (protocol `2025-06-18`), then keep
  `Mcp-Session-Id`, then `notifications/initialized`, then `tools/list` or `tools/call`. SSE `data:` lines are
  parsed and nested envelopes unwrapped.
- For the Data Quality agent server use `--auth session --nested --poll`. `call` is a write because tools can
  act, and it checks the OAuth file's org against `--expect-org`.
- PROVEN 2026-09 except `client-delete`, which is UNTESTED.

### `idmc_probe.py`: find routes without fooling yourself

- `twin` compares a real path with a nonsense sibling. Only a difference is evidence; a zero-byte 200, the login
  HTML or a router 403/500 that the twin also returns proves nothing.
- `hosts` resolves `<pod>-ing`, `-cai`, `-dqprofile` and the other service hosts, with a bogus host as control
  (DNS only, in parallel).
- `verbs` sends one empty-body POST (400/415/422 = the verb exists; 405 = no verb). `ctypes` sends empty POSTs
  with five Content-Types. Both are **writes**, and they refuse:
  - action words (deploy, start, run, publish...);
  - login and token routes (an attempt counts toward the lockout);
  - paths ending in an id.
  The source lesson called empty POSTs safe, but an id-bearing action endpoint acts on an empty body: a DBMI
  `task/deploy/<id>` POST with no body deployed the task.

## 5. Recipes

- **Change a CAI process headless**:
  1. `idmc_objects.py list --type PROCESS` to get its object id.
  2. `idmc_export_import.py export --id <id> --no-deps --out p.zip` (keep it: it is the undo).
  3. `idmc_package_edit.py sub p.zip --file Explore/<p>/<f>/<n>.PROCESS.xml --pattern '<process\b.*?</process>'
     --repl-file new.xml --out p2.zip --execute`.
  4. `idmc_export_import.py import p2.zip --mode OVERWRITE --include <id> --execute --expect-org <orgIdV3>`.
  5. `idmc_cai_publish.py publish --path Explore/<p>/<f>/<n>.PROCESS.xml --execute --expect-org <orgIdV3>`.
  6. Verify with a side-effect-free call. The runtime can serve the old version for about 20 s.
- **Cut schedules over between orgs**:
  1. Run `audit` and `snapshot` in the old org.
  2. `unbind` there, including task level.
  3. Create schedules unbound in the new org beforehand; `bind` them after the switch.
  4. Rollback = `restore <snapshot>`.
- **Remove an app's footprint**:
  1. Back up with `export`, which includes dependencies.
  2. Unbind and delete its taskflows; `unpublish` its CAI assets.
  3. `idmc_frs_delete.py delete --ids-file ... --keep-file ...`.
  4. `idmc_dbmi.py stop|undeploy`, then `delete`.
  5. `v2-delete` its tasks, mappings and connections, in that order.
- **Add one connector to an agent**: `idmc_runtime_selections.py set <reId> --enable "connectors:<name>"`, then
  `--execute --expect-org <orgIdV3>`, then poll `/api/v2/agent/details/<agentId>` until the engines are RUNNING.

## 6. Known gaps (re-verify before you rely on them)

- UNTESTED here:
  - the session-service header set in `whoami` (optional evidence only; the guard relies on `/api/v2/org`);
  - the Windows file lock;
  - `idmc_mcp.py client-delete`;
  - the `--federated` job start (a 2026-08 note saw `403 REPO_19035` with `taskFederatedId`);
  - the v3-to-v2 shortcut `GET /api/v2/mttask/<v3id>`.
- ADAPTED: `schedule-end`, pod-offset derivation, the import NEW/EXISTS preview (path lookup), and every guard,
  diff and redaction helper. These are new in this library and were tested offline with mocks only.
- Not covered: connection create/update/test, profiling, MDM, advanced-taskflow and mapping (IMF) generation,
  user management, Secure Agent installation. See the domain folders.
