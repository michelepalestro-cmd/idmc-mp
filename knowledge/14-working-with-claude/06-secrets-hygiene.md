# Secrets Hygiene

**Answers:** Where do secrets leak in IDMC work with Claude? How are they read, passed, rotated, scrubbed from git and
sequestered, and how is a KB or package checked before it is shared?

**Read when:** handling any credential, key, token, storage state or export package; passing a secret to a warehouse,
a container or a remote host; after an exposure; before sharing a transcript, document, KB or package.

**Key rules:**
- Read credentials at run time from env vars or a 0600 file, print key names only, and never print a file of unknown
  format (L-METHOD-001, L-METHOD-087).
- Anything printed is exposed: say so, rotate it, and never use the value again (L-METHOD-088).
- Never pass a secret as a SQL `SET` or an HTTP query parameter, because warehouse query logs keep it; send it in the
  request body and prove the path with a dummy value first (L-ENV-078).
- Redact login bodies inside UI capture hooks, and never reuse an MCP shim that disables TLS verification
  (L-UI-002, L-MCP-124).
- Rotate in one coordinated window with every consumer listed, and scrub every git ref, not just the branch
  (L-ENV-049, L-ENV-045).
- A secret scan (`toolkit/tools/secret_scan.py`, run by the pre-commit hook and CI) must pass before anything is
  shared, and is never weakened to make it pass (L-METHOD-090, L-METHOD-084).

**Related:** [01 How Claude Reaches and Drives IDMC](01-how-claude-reaches-and-drives-idmc.md) · [03 Multi-Agent Coordination](03-multi-agent-coordination.md) · [04 UI Automation with Playwright](04-ui-automation-with-playwright.md) · [Agent-Style MCP & Custom Shims](../11-mcp-claire/04-agent-style-mcp-async-orchestration-custom-shims.md) · [Lessons: Environment & Ops](lessons-environment-ops.md)

**Last verified:** 2026-10-03

> **Summary.** In the sessions behind this KB, secrets leaked far more often through the working environment than
> through IDMC: credential files printed into transcripts, tokens embedded in git remote URLs, keys committed to a
> repository, export packages carrying an OAuth secret in plaintext, world-readable `.env` backups, browser storage
> states and XHR captures, warehouse query logs, memory and note files, and a literal `%VAR%` folder that captured a key.
> The rules: use secrets where they live, print key names only, read them from 0600 files at run time, treat anything
> printed as exposed, rotate in one coordinated window, scrub git history properly, and sequester rather than delete.

---

## 1. The rules

1. **Credentials are read at run time** from environment variables or a 0600 file outside every repository, never
   written as literals in scripts, configs, command lines, tracker comments or chat (L-METHOD-001).
2. **Use a secret where it lives.** Run psql inside the database container with the container's own password
   variable; let a script read its env file itself; print only key names (L-METHOD-087).
3. **Never print a credential file of unknown format**; inspect it with `wc -c` and `stat` only
   (L-METHOD-087).
4. **Never paste tokens, cookies or Network-tab requests** into chat; share the error text (L-METHOD-088).
5. **Anything printed is exposed.** Say so, list it for rotation, and do not use or store the value again
   (L-METHOD-088).
6. **Show-once secrets go straight to a 0600 file**; if any part reaches a log, delete and recreate the object
   (L-METHOD-089).
7. **Rotate in one coordinated window** with every consumer listed (L-ENV-049).
8. **Sequester, do not delete**: move loose secret files to a dated archive with a stub and an undo line
   (L-ENV-050).
9. Org ids, pod names, agent ids and host addresses are configuration, not secrets; they still stay out of anything
   you share: keep them in private, deployment-specific notes and write placeholders (`<org-id>`, `<pod-host>`,
   `<secure-agent-host>`) in shared documents.

## 2. Where secrets leak

| Leak path | How it happened | Prevention | Cleanup | Lesson |
|---|---|---|---|---|
| Session transcripts | credential files `cat`-ed or grepped; a plain-lines file slipped past name=value redaction | size/metadata only; use the secret where it lives | rotate; log the exposure (not the value) | (L-METHOD-087) |
| `docker inspect` output | DSN passwords sit in the container environment and in `Cmd`/`Args` | never paste inspect output; redact `Env`, `Cmd`, `Args`, `Entrypoint` | rotate what was shown | (L-METHOD-087), (L-ENV-045) |
| Browser Network-tab dumps | `Cookie:` and `Authorization:` headers are full credentials that bypass MFA | share the error text only | rotate, log out | (L-METHOD-088) |
| Storage states and browser profiles | cookies including session JWTs (one state held 46) | 0600, outside repos and the script folder | sequester or delete; log out | (L-UI-006) |
| Git remote URLs | a token in the URL sits in `.git/config`, process listings and `git remote -v` output | a credential helper reading a 0600 file; short-lived tokens revoked on exit | rotate; scrub the URL | (L-ENV-043) |
| Committed files | `.gitignore` does not untrack; a committed key stays valid | gitignore creds, caches, logs and locks; a staged secret scan before each commit | `git rm --cached`, commit, rotate, scrub history | (L-ENV-044), (L-ENV-046) |
| Git history and tags | tags and other refs pin pre-scrub commits | scrub all refs; orphan rebuilds | verify no ref reaches old secret SHAs | (L-ENV-045) |
| `.example` files and backups | generated examples and `*.bak` configs kept real values | scan every file type; exclude backups from commits | rotate | (L-ENV-045) |
| IDMC export packages | a CAI app connection written with `encrypted="false"` puts client ids and secrets in plaintext in every package | mark secret attributes masked/encrypted; treat packages as secrets (0600, private folder) | rotate after the migration; leave a README where packages were | (L-ENV-051) |
| Logs | a new OAuth client secret's prefix reached a local log | write show-once values straight to files; mask in errors | delete and recreate the client | (L-METHOD-089) |
| Old `.env` backups | dated backups accumulate old values and are often 0644 | 0600 at creation; approved backup location | chmod, move, delete | (L-ENV-048) |
| A literal `%VAR%` folder | `%LOCALAPPDATA%` written from bash created a real folder that captured a key | `$LOCALAPPDATA` or absolute paths | quarantine; rotate the key | (L-ENV-020) |
| Cloud-specific mount paths | a missing `/home/<cloud-default-user>/<key>.json` became an empty directory | project-relative paths, Docker secrets, a secret manager | fix the path; force-recreate | (L-ENV-030) |
| Service-account keys | user-managed keys never expire; old ones accumulate | list keys; rotate before hosts move or repos go public | delete old keys; check audit logs for the old key id | (L-ENV-052), (L-ENV-044) |
| Command lines and process listings | a secret passed as an argument | pass by variable name (`docker run -e NAME`), read inside the script | rotate | (L-METHOD-089) |
| Memory files, notes and tracker comments | passwords and tokens written into narrative notes and issue text | write names and locations only | rotate; scrub or sequester the file | (L-METHOD-087) |
| Other OS users on the same host | a second agent's user could read the apps' secret files | deny other users; 0600 owned by the consuming user | verify the denial | (L-METHOD-089) |
| Warehouse query logs | a keyed-hash salt passed as an HTTP query parameter (`{salt:String}`) or a SQL `SET` was written into `system.query_log`, `system.text_log` and the server log | send the secret in the request body (section 3); dummy-value self-test before the real value | rotate the salt; purge or expire the log rows | (L-ENV-078) |
| UI capture logs | an XHR capture recorded the identity-service login request, whose body carries the username and password in clear | redact inside the capture hook ([04 UI Automation](04-ui-automation-with-playwright.md), section 8) | rotate the password if an unredacted log was shared | (L-UI-002) |
| Third-party MCP shims | a field-distributed stdio shim created its HTTPS context with `ssl.CERT_NONE` and `check_hostname=False`, so it would hand the IDMC user's credentials to any certificate | grep shims for `CERT_NONE`, `check_hostname`, `verify=False`, `_create_unverified_context`; restore verification or pin a CA bundle; credentials from a 0600 file or the environment, never arguments ([shim checklist](../11-mcp-claire/04-agent-style-mcp-async-orchestration-custom-shims.md)) | patch before reuse | (L-MCP-124) |
| Scratch scripts in `/tmp` | admin passwords inside world-readable scratch files on a shared host | write them 0600 and shred them after use | shred; rotate if another user could read them | (L-METHOD-124) |

## 3. Handling patterns

- **Print names, not values.** List the keys of an env file (`cut -d= -f1`), never the file.
- **Inspect unknown formats safely**: `wc -c <file>`, `stat <file>`; never `cat`, `head` or `grep` a file whose format
  you do not know (L-METHOD-087).
- **Use secrets in place**:
  `sudo docker exec -i <pg-container> sh -c 'PGPASSWORD=$POSTGRES_PASSWORD psql -U <user> -d <db> -f -'`
  keeps the password inside the container (L-ENV-010).
- **Pass by name.** `docker run -e IDMC_USER -e IDMC_PASS...` forwards the values without putting them in argv.
- **Read at run time** inside the script that needs the secret; never echo it; mask it in errors with
  `.replace(pw, '***')` (L-METHOD-089).
- **Show-once secrets** (OAuth client secrets, install tokens): write with
  `os.open(path, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)` and never print them (L-METHOD-089).
- **Secret managers**: stream the existing file into the secret manager without printing it, then compare length and
  SHA-256 of the stored version; one vault item per role (L-ENV-047).
- **Git pushes**: a credential helper that reads a 0600 file, or a one-day token minted for the push, revoked in a
  `trap... EXIT`, and scrubbed from the remote URL (L-ENV-043).
- **Committed tooling**: separate creds files read at run time; gitignore creds, session caches, keys, logs, locks and
  caches; commit an example config; run a staged secret scan with PEM detection anchored at line start
  (L-ENV-046).
- **Work up to the secret boundary** when only a human holds the credential: build and pre-wire everything, then hand
  over one named secret and one command (L-METHOD-067).
- **Know who can reach what.** An evidenced map of every identity against every data store surfaces over-broad BI,
  CDC and app credentials (L-METHOD-091).
- **Secrets inside warehouse SQL** (L-ENV-078). When you pseudonymise columns before staging a sample for
  IDMC (keyed hashes of names, agents or e-mails), the key must not reach any log. ClickHouse writes `SET` statements
  and substitutes HTTP query parameters into `system.query_log`, `system.text_log` and the server log, so both routes
  leak; assume any warehouse's query history keeps literal statement text. The route that held: send the secret in the
  HTTP POST body as a one-row external table and read it with a scalar subquery. Keep the file root-only (0400), never
  put the secret on a command line, and search for it with `grep -F -f <file>`.
  1. Run the whole path once with a random dummy value, wait for the log flush (about 7.5 s), and grep `query_log`,
     `text_log` and the server log for the dummy; proceed only on 0 hits.
  2. After every real run, repeat the grep for the real value, and publish nothing if it hits.

```bash
curl -s "http://localhost:8123/?query_id=$QID&salt_structure=s%20String&salt_format=TabSeparated" \
  -F 'query=@export.sql' -F 'salt=@<salt-file>;filename=salt'
# export.sql: WITH (SELECT any(s) FROM salt) AS _salt SELECT lower(hex(SHA256(concat(_salt, '|', col))))...
```

## 4. Rotation

(L-ENV-049)

1. **List every consumer** before touching anything: host creds files, service env files, IDMC connections, CDC tasks,
   BI data sources, admin tools, pipelines, secret-manager copies, catalog scanners that store the password, OAuth
   clients that store the user's password (those must be recreated), and workstation env files.
2. **Pick the window.** Rotate after critical events such as demos, not just before them.
3. **Change it at the source**, then update every consumer within minutes, writing files in place so bind-mounted
   containers see the change (L-ENV-028).
4. **Re-arm the login guard**: delete the block file and session caches, verify with exactly one login, then restart the
   consumers (L-METHOD-004).
5. **Verify**: run the end-to-end rehearsal; for keys, confirm in the audit logs that the old key id shows no further
   use (L-ENV-044).
6. **After a migration**, rotate everything that travelled in export packages or was pasted in chat
   (L-ENV-051).

A committed key is fixed by deleting the key, not by deleting the file; history rewriting is hygiene on top
(L-ENV-044).

## 5. Scrubbing git history

(L-ENV-045)

1. **Find everything first**: scan every file type, including `.example` files, `*.bak` configs and redacted
   `docker inspect` output (`Env`, `Cmd`, `Args`, `Entrypoint`).
2. **Rotate first**: the secret is compromised the moment it was pushed.
3. **Rewrite every ref**, not just the branch: tags pin pre-scrub commits. Delete or recreate every tag on the old
   commits; rebuilding scrubbed branches as orphan commits makes the old blobs unreachable.
4. **Verify on every remote** that no branch or tag still reaches the old secret SHAs.
5. **Scan with a battery**: a secrets scanner in no-git mode, literal regexes for the known values, and a high-entropy
   quoted-assignment rule. Know the false positives (minified JS, empty example keys, public keys, issuer URLs, cert
   paths, `${VAR}` references, hashes, UUID keys).
6. **Have an independent critic scan** the result: one caught two secrets the capture's own gate had missed.

## 6. Sequestering

(L-ENV-050)

- Move loose standalone secret files (install tokens, API tokens, credential bundles, installer JSON with a live token)
  into a dated archive folder with a README that recommends rotation.
- Leave a `.SEQUESTERED.txt` stub where each file was, and write one UNDO line per move.
- Leave credentials that running tools read (for example an MCP server config pointing at a creds file) in place until
  their consumers are repointed in the same change; rotate them instead of moving them.
- To cut runtime coupling to another environment, move its credential files to a quarantine folder (reversible) and
  verify the application still serves.
- Where a document must be kept but contains a secret, keep a redacted copy in the working tree and the original in the
  sequestered archive.

## 7. Publication gates

- A zone or sanitize gate needs substring rules for identifiers, separate identifier and prose replacements, and proof
  both ways: it must fail on the private build and pass on the clean one (L-METHOD-090).
- A leak gate proves nothing leaked, not that the text still works: read the output for broken commands, collapsed
  table rows and dangling references (L-METHOD-090).
- Keep the gate's own block-list out of the generic zone, because it names what it blocks.
- **Scan every format and every name.** A gate that reads only text files passes leaks inside.docx,.pptx,.xlsx and
  PDF content and in file and folder names. A package that passed a text-only gate failed the full gate with about 250
  hits, mostly inside a generated.docx whose sanitized rebuild never landed because the document was open in an
  editor, plus an internal subfolder. Scan every format and every file name, refuse to build the share archive unless
  the gate is clean, and never weaken the gate to make it pass (L-METHOD-084).
- **Private provenance stays outside the shared folder.** Which project, system or person proved a lesson lives in a
  private file outside the share, and no shared link points into it (L-METHOD-084).
- **Skills point to the canonical KB.** A reference skill built from an earlier snapshot does not contain later
  lessons: start each IDMC skill with a pointer to read the canonical KB first (L-METHOD-084).
- **Allocate lesson ids at write time.** When several sessions add lessons the same day, ids move under you: take each
  id from the maximum over the markdown headings and the JSONL, write both in one pass, then check for duplicate ids
  (L-METHOD-084).

## 8. Checklists

**Before committing or pushing**
- [ ] Creds, session caches, keys, storage states, logs and locks are gitignored and untracked (`git ls-files` check)
- [ ] Staged secret scan passes; PEM rule anchored at line start
- [ ] No token in any remote URL (`git config --get-regexp url` shows none)
- [ ] Push token short-lived and revoked on exit

**Before sharing a transcript, document or package**
- [ ] No credential file was printed; only key names appear
- [ ] No `docker inspect`, Network-tab or storage-state content is included
- [ ] Export packages are treated as secrets and stay in a private 0600 location
- [ ] For a KB or package: the full-format gate (text,.docx,.pptx,.xlsx, PDF content and every file name) is clean,
      and no link points into private provenance

**After an exposure**
- [ ] Say so plainly; record where it leaked (never the value)
- [ ] List every consumer; rotate in one window; re-arm the login guard with one verified login
- [ ] For OAuth clients that leaked: delete and recreate; update their env files
- [ ] Confirm the old credential shows no further use
