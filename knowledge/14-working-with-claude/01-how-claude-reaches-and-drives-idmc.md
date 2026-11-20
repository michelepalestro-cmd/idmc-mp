# How Claude Reaches and Drives IDMC

**Answers:** How does a Claude session log in to IDMC, pick the right host and header, change a task safely, and get a
shell on the host that runs the Secure Agent? Which layer (REST, MCP, UI) should a step use, and what gets logged?

**Read when:** setting up a new session, workstation or agent host; writing or reviewing the session helper; a call
answers 401 or a 404 from the wrong plane; you need to run something on the agent VM.

**Key rules:**
- One org-aware session module per host: a cached session (at most 25 minutes, 0600), serialized logins and a block
  file after any rejected login (L-METHOD-002, L-METHOD-003, L-METHOD-004).
- Right host plus right header for each plane, the host derived from the login answer, and a read-back after every
  write (L-METHOD-007, L-METHOD-030).
- Change a mapping task by id: back up, change one field behind an asserted anchor, read back, diff, run, then verify
  the data, not only the state (L-METHOD-010, L-METHOD-044).
- REST first, then a managed MCP tool, a package clone and the UI's own XHR; Playwright only last (L-UI-001, L-UI-002).
- Host reach: pin `--account` on every gcloud call, treat run-command as a shared per-VM singleton, and start long
  jobs detached (L-ENV-009, L-ENV-003, L-ENV-006).
- A service account with IAP-tunnel and SSH rights keeps the IAP hop working while the human login is lapsed
  (L-ENV-008).

**Related:** [02 Evidence Discipline](02-evidence-discipline.md) · [05 Environment Traps](05-environment-traps-windows-git-bash-az-gcloud-docker.md) · [06 Secrets Hygiene](06-secrets-hygiene.md) · [Login, Sessions & Tokens](../01-login-and-orgs/02-login-sessions-tokens.md) · [Lessons: Claude Working Methods](lessons.md)

**Last verified:** 2026-10-06

> **Summary.** A Claude session drives IDMC through a fixed stack: credentials read at run time, one org-aware
> session module that owns login, caching and the lockout guard, the REST planes, managed MCP servers where they add
> something, and the browser UI only as a last resort. Beside the stack it needs a reach path to the agent host (IAP
> hop, cloud run-command, container exec) and a tracker that serves as the single log. Header and route detail lives in
> the domain folders; this is the operating manual.

---

## 1. The stack at a glance

```
  credentials: env vars or a 0600 file per org, outside every repo           (layer 0)
        |
        v
  org-aware session module  -> session cache (<= 25 min, 0600)                (layer 1)
   sess get post call v3_login   -> lock file + block file (lockout guard)
   returns (status, body); never raises     -> host derivation from the login answer
        |
        v
  REST planes: v2 /api/v2. v3 /public/core/v3. FRS. runtime selections      (layer 2)
               <pod>-ing. <pod>-cai. <pod>-dqprofile. cdgc-api / idmc-api. hdm
        |
        +--> managed MCP servers (registry on hdm; OAuth client; streamable HTTP) (layer 3)
        |
        +--> the IDMC UI: XHR capture first, then Playwright from a server        (layer 4)

  beside the stack:  host reach (IAP hop. run-command. container exec)   and   the tracker (single log, leases)
```

| Layer | Job | The rule that matters most | Lessons |
|---|---|---|---|
| 0 Credentials | Supply user, password, keys | Read at run time from env or a 0600 file; never a literal, never printed | (L-METHOD-001), (L-METHOD-087) |
| 1 Session module | Login, cache, headers, guard | One module per host; one login per org; stop at the first rejection | (L-METHOD-002), (L-METHOD-004) |
| 2 REST planes | Read, run, write | Right host + right header; read back every write | (L-METHOD-030), (L-METHOD-010) |
| 3 MCP | Extra capabilities, uniform tools | Enumerate the real registry; MCP is not a network position | (L-METHOD-011) |
| 4 UI | The residual clicks | Capture the UI's own API call before automating it | (L-UI-001), (L-UI-002) |
| Host reach | Agent host, databases, logs | Serialized channels are shared: retry, keep output small | (L-ENV-001), (L-ENV-003) |
| Tracker | Log, leases, gates | Every write with its id and exact undo | (L-METHOD-022) |

## 2. Layer 0: credentials

- **Where they live.** Environment variables (`IDMC_USER`, `IDMC_PASS`) or a mode-0600 file per org that lives
  outside every repository and shared folder (L-METHOD-001). Two file formats were in use side by side:
  `KEY=value` lines, and plain lines (line 1 user, line 2 password, line 3 login host). Because name=value redaction
  filters miss the second format, inspect any credential file of unknown format only with `wc -c` or `stat`
  (L-METHOD-087).
- **What counts as a credential.** Passwords, session caches, JWTs, OAuth client env files, service-account key
  JSON, Playwright storage states and browser profiles (L-UI-006), and v3 export packages that contain a
  CAI connection written with `encrypted="false"` (L-ENV-051).
- **Which user.** Prefer a dedicated native automation user over a personal or SSO account; failed logins from every
  session add up against one account (L-METHOD-070).
- **At a secret boundary** (a credential only a human holds), build everything else, pre-wire the consumer and hand
  over one named secret plus the one command that consumes it (L-METHOD-067).

Handling rules for secrets are in [06 Secrets Hygiene](06-secrets-hygiene.md).

## 3. Layer 1: the org-aware session module

Every script on a host imports the same small module instead of logging in by itself (L-METHOD-002).

| Piece | Behaviour |
|---|---|
| Interface | `sess`, `get(path)`, `post(path, body)`, `call(method, path, body=None, v3=False)`, `v3_login`, creds dict `C`, constants `ORG`, `HOST` |
| Org selection | env `IDMC_ORG`, else the first word of a switch file, else a safe default; per-org creds file, session cache and login host |
| Moving a host to another org | one write to the switch file plus remapped id files; one cron line can stay on the old org with `IDMC_ORG=<old>` |
| Session cache | `{sid, serverUrl, orgId, t}` in a 0600 file; re-login when older than 1500 s (the v2 session dies ~30 min after grant); separate v3 cache (L-METHOD-003) |
| 401 handling | delete the cache, log in exactly once more, then return the error |
| Lockout guard | `fcntl.flock` around login, re-check the cache after taking the lock, block file keyed to the creds fingerprint on any 4xx except 429 (L-METHOD-004) |
| Return contract | `(status, json-or-text)` for success and error alike; callers must check the status (L-METHOD-006) |
| Host derivation | pod base from `serverUrl` / `products[].baseApiUrl`; CAI host by splitting the base host at the first dot; never replace a pod literal (L-METHOD-007) |
| Org proof | destructive scripts assert the org from a live `GET /api/v2/org` before acting (L-METHOD-008) |
| Tests | fake `urlopen`, temp HOME, count network calls; patched services in a `--network none` container (L-METHOD-005) |

A migration library used on a workstation added two useful rules: the **source org is read-only** (any non-GET
raises unless an explicit env override is set; export POSTs are allowed), and the base URL always comes from the login
answer, never from a guessed pod.

### 3.1 Which header goes with which call (summary)

The authoritative table is in [knowledge/01-login-and-orgs](../01-login-and-orgs). The module only needs to know
which family a path belongs to:

| Call family | Host | Header the helpers sent |
|---|---|---|
| v2 platform `/api/v2/*` | `serverUrl` from the v2 login (`https://<pod>.<domain>.informaticacloud.com/saas`) | `icSessionId: <v2 session>` |
| v3 platform `/public/core/v3/*` | same base | `INFA-SESSION-ID: <session>` |
| FRS `/frs/api/v1/*`, `/frs/v1/*` | `https://<pod>.<domain>.informaticacloud.com` | `IDS-SESSION-ID: <v2 session>` |
| Runtime-environment selections `/runtime/api/v2/...` | pod host | `IDS-SESSION-ID: <v2 session>` |
| Database ingestion `/dbmi/...` | `https://<pod>-ing.<domain>.informaticacloud.com` | `IDS-SESSION-ID` |
| CAI publish `/active-bpel/asset/v1/*` | `https://<pod>-cai.<domain>.informaticacloud.com` | `INFA-SESSION-ID` plus `application/vnd.api+json` Accept and Content-Type |
| Profiling `/profiling-service/api/v1` | `https://<pod>-dqprofile.<domain>.informaticacloud.com` | `IDS-SESSION-ID` (on at least one pod only the v3 session works) |
| Catalog and search `/data360/*`, catalog sources | `idmc-api.<domain>` / `cdgc-api.<domain>` | Bearer JWT + `IDS-SESSION-ID` + `X-INFA-ORG-ID` |
| MCP registry and OAuth clients | `https://hdm.<domain>.informaticacloud.com/a2e-mcp-asset-mgmt-svc/api/v1/...` | `IDS-SESSION-ID: <v3 session>` |

These are the session-ID headers the helpers used. The vendor is moving REST authentication to JWT; read the current
status in [Login, Sessions & Tokens](../01-login-and-orgs/02-login-sessions-tokens.md) before building a new
helper (L-AUTH-033).

### 3.2 A minimal module (sketch)

```python
"""idmc.py - one org-aware IDMC session helper for every script on a host (sketch, placeholders)."""
import fcntl, hashlib, json, os, time, urllib.error, urllib.request

HOME = os.path.expanduser("~/.idmc")          # 0700, outside every repository
ORG = os.environ.get("IDMC_ORG") or (open(f"{HOME}/org").read.split or ["source"])[0]
CREDS = f"{HOME}/{ORG}.creds"                 # KEY=value lines: IDMC_USER, IDMC_PASS, IDMC_LOGIN_HOST
C = dict(l.strip.split("=", 1) for l in open(CREDS) if "=" in l)
HOST = C.get("IDMC_LOGIN_HOST", "<domain>.informaticacloud.com")   # the domain host, never the pod host
CACHE, LOCK, BLOCK = f"{HOME}/{ORG}.sess", f"{HOME}/login.lock", f"{HOME}/login.block"
MAX_AGE = 1500                                # the v2 session dies ~1800 s after it is granted

def _fp:
    return hashlib.sha256(open(CREDS, "rb").read).hexdigest[:16]

def _write_0600(path, obj):
    fd = os.open(path, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(obj, f)

def _cached:
    try:
        s = json.load(open(CACHE))
        return s if time.time - s["t"] < MAX_AGE else None
    except (OSError, ValueError, KeyError):
        return None

def login:
    with open(LOCK, "a") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)        # serialize logins across every process on the host
        s = _cached                         # another process may have logged in while we waited
        if s:
            return s
        try:
            b = json.load(open(BLOCK))
            if b.get("fp") == _fp:
                raise SystemExit(f"IDMC login blocked since {b['at']}: fix {CREDS} or delete {BLOCK}")
        except (OSError, ValueError):
            pass
        body = {"@type": "login", "username": C["IDMC_USER"], "password": C["IDMC_PASS"]}
        req = urllib.request.Request(f"https://{HOST}/ma/api/v2/user/login", data=json.dumps(body).encode,
                                     headers={"Content-Type": "application/json", "Accept": "application/json"})
        try:
            r = json.load(urllib.request.urlopen(req, timeout=30))
        except urllib.error.HTTPError as e:
            if e.code < 500 and e.code != 429:   # rejected: nobody logs in again until the creds change
                _write_0600(BLOCK, {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime), "fp": _fp})
            raise
        s = {"sid": r["icSessionId"], "base": r["serverUrl"], "org": r["orgId"], "t": time.time}
        _write_0600(CACHE, s)
        return s

def call(method, path, body=None, v3=False):
    """Returns (status, json-or-text) for success and errors alike. The caller checks the status."""
    for attempt in (1, 2):
        s = _cached or login
        h = {"Accept": "application/json", "Content-Type": "application/json",
             ("INFA-SESSION-ID" if v3 else "icSessionId"): s["sid"]}
        req = urllib.request.Request(s["base"] + path, method=method, headers=h,
                                     data=None if body is None else json.dumps(body).encode)
        try:
            r = urllib.request.urlopen(req, timeout=120)
            t = r.read
            return r.status, (json.loads(t) if t else None)
        except urllib.error.HTTPError as e:
            t = e.read
            if e.code == 401 and attempt == 1:  # session died early: drop the cache, log in once more
                try:
                    os.remove(CACHE)
                except OSError:
                    pass
                continue
            try:
                return e.code, json.loads(t)
            except ValueError:
                return e.code, t.decode(errors="replace")[:2000]
```

A v3 login (`POST https://<domain>.informaticacloud.com/saas/public/core/v3/login`, body `{"username","password"}`,
answer `userInfo.sessionId` and `products[].baseApiUrl`) goes through the same lock, block file and a separate cache.
A long-running service applies the same guard in memory: pause logins for hours after an auth rejection, about 60 s
after a transient failure, and show the block on its health endpoint (L-METHOD-004).

## 4. Layer 2: working over the REST planes

### 4.1 The loop for changing a mapping task

This is how a session actually "works with a mapping" headless (L-METHOD-010):

1. **Find it by id.** Resolve by path with `POST /public/core/v3/lookup` and require exactly one match; names repeat
   across folders (L-METHOD-009).
2. **Back it up.** Save the v2 task JSON, the old SQL as a file, and a v3 export of the task.
3. **Change one field.** `GET /api/v2/mttask/<id>`, drop the read-only fields, replace an anchor inside
   `$Source$.customQuery` after asserting it occurs exactly once, `POST /api/v2/mttask/<id>`.
4. **Read it back** and compare the field (L-METHOD-030).
5. **Diff before it goes live.** Run old and new SQL against current data in the warehouse.
6. **Run and poll.** `POST /api/v2/job {"@type":"job","taskId":"<taskId>","taskType":"MTT"}` returns a `runId`; poll
   `GET /api/v2/activity/activityLog?taskId=<taskId>&rowLimit=1` every 5-10 s until the row's `runId` matches and
   `endTime` is set. State 1 = success, 2 = warning, 3 = failed; a success or warning with
   `successTargetRows == 0` is a failure to investigate (L-METHOD-043).
7. **Verify the data**, not only the state: row counts, parity, a transformed-not-copied check (L-METHOD-044).

Monitoring notes that save time: `GET /api/v2/activity/activityMonitor` lists what is running (check it before
starting anything, and before re-arming a paused cron (L-METHOD-059)); tasks inside a linear taskflow
log under the taskflow's own activity-log entry (`entries[]`), not under their task ids; and the agent host keeps a
session log per run, which is independent evidence of timing and row counts. Route and error detail:
[knowledge/04-mappings](../04-mappings).

### 4.2 Changing many things safely

| Pattern | Rule | Lesson |
|---|---|---|
| Write-capable scripts | dry run by default, `--execute` to act; backup, UNDO log and manifest; cron edits by tagged comment-out | (L-METHOD-013) |
| Patches | anchored, count-asserted, SKIP when applied; one canonical chain; proven by re-running on its own output | (L-METHOD-014) |
| Safety switches | assert the new value after editing a dry-run/apply flag | (L-METHOD-015) |
| Deploys | export, apply, verify and roll back automatically in one run | (L-METHOD-016) |
| New runtime modes | env flags that default off; flag script waits for idle; `off` is the rollback | (L-METHOD-017) |
| Controllers that start jobs | build, wait for idle, recreate at once | (L-METHOD-018) |
| Cron runners | non-blocking lock, exit 0 when held; pid plus heartbeat liveness | (L-METHOD-019) |
| Builders, plans, id files | one source per org; generated copies only | (L-METHOD-020) |
| Placement | builders place and tag at creation; an hourly guard sweeps strays | (L-METHOD-086) |

### 4.3 Reading safely

Every probe result goes through the evidence rules before it becomes a conclusion: bogus twins, the kinds of 404,
empty-POST verb probes, Content-Type variation and read-backs. See [02 Evidence Discipline](02-evidence-discipline.md).
Keep those checks in a kept, GET-only-by-default harness rather than in fresh one-off probes (L-METHOD-012).

## 5. Layer 3: MCP servers

- **Enumerate the real registry first**: `GET https://hdm.<domain>.informaticacloud.com/a2e-mcp-asset-mgmt-svc/api/v1/mcp-servers?type=MANAGED`.
  In September 2026 one org exposed 19 managed servers and about 140 tools, which falsified walls that had been
  declared from the two servers wired into a session (L-METHOD-011). The October 2026 release lists 23 shared servers
  in the public registry (no login needed), but only the org registry says what your org exposes (L-MCP-132).
- **Inside Claude Code**: `/idmc-mp:connect-mcp` creates a scoped OAuth client for the org's servers, and the plugin's
  bridge (`toolkit/lib/idmc_mcp_bridge.py`, started by the plugin) offers their tools as Claude Code tools
  (`mcp__plugin_idmc-mp_idmc__*`). It is read-only unless the client was created with writes allowed, and
  `idmc_mcp_bridge.py --check` lists what it would offer.
- **What MCP is not.** It is a calling convention: it never replaces a Secure Agent, never reaches a private database
  the agent cannot, and its backing calls still bill IPUs. Read a server's tool list before assuming it can write.
- **When it helps.** Lineage reads, fuzzy identity matching, the hosted DQ agent on uploaded files, address
  verification, or one uniform tool surface through a local gateway that holds a single OAuth client.
- **OAuth clients** can be created headless; the secret is shown once, so write it straight to a 0600 file and
  recreate the client if any part of it reaches a log (L-METHOD-089).
- **Local MCP configs** can point at a different org than the one you are working in; check before trusting an empty
  answer (L-METHOD-011). Running one MCP server per environment, give each instance its own env files and a distinct
  server name (L-ENV-142).
- **Write tools need a human gate.** If you build your own MCP tools, make writes preview-then-confirm and keep secrets
  in server-side plan files, never in tool arguments (L-METHOD-162, L-METHOD-163). Never put a write-capable IDMC MCP
  behind an unattended `claude -p --dangerously-skip-permissions` bot: anyone who can post to it, or text it reads,
  can trigger writes (L-METHOD-164).

Protocol and tool detail: [knowledge/11-mcp-claire](../11-mcp-claire).

## 6. Layer 4: the UI, last

Try, in order: the REST route on the right host and plane, a managed MCP tool, a clone through a v3 package, and a
capture of the UI's own XHR for that click; only then drive the UI with Playwright from a server, or hand one precise
click to a human with a receipt (L-UI-001), (L-UI-002), (L-UI-010). Browser
automation from behind a transparent enterprise proxy once rendered the IDMC apps blank (L-UI-011, now disputed): on
2026-10-06 headless Chromium with the Private and Local Network Access checks off drove Metadata Command Center, the
catalog and the mapping designer from behind such a proxy (L-UI-031). Try that flag set first, and keep a host outside
the proxy as the fallback.
See [04 UI Automation with Playwright](04-ui-automation-with-playwright.md) §6.

## 7. Reaching the host that runs the Secure Agent

| Path | Use it when | Traps | Lessons |
|---|---|---|---|
| Direct SSH | your egress address is stable and allowlisted | egress rotates mid-session; timeout = network, `Permission denied` = auth | (L-ENV-011), (L-ENV-012) |
| IAP jump host | direct SSH is blocked | pin `--account` every call; base64-inline the script; `scp` big files via the jump host; never pipe stdin through Windows `gcloud compute ssh`; runs as a service account with IAP and SSH rights (section 7.1) | (L-ENV-001), (L-ENV-002), (L-ENV-009), (L-ENV-008) |
| Cloud run-command (`invoke`) | no SSH path at all | runs as root with `HOME=/root`; per-VM singleton shared by every session; ~4 KB output tail; `--scripts @file` | (L-ENV-003) |
| Managed run-command | `invoke` is jammed | output via `show --instance-view`; 25 per VM; a delete lock can pin them | (L-ENV-004) |
| Provider web console | human fallback | it connects from the provider's addresses, so narrowing port 22 breaks it | (L-ENV-012) |
| Container exec on the host | you need a key or client that lives in a container | `sudo docker`; run the script where the key already is | (L-ENV-010), (L-ENV-026) |

Rules that apply to every path:

- **Run long orchestrations on a server, not in a Claude session.** A laptop background shell can be reaped under
  memory pressure, and idle sessions are reaped too; keep a done-ledger, and for a multi-day chain move it into a
  scheduled IDMC taskflow with a gate mapping (L-METHOD-148, L-METHOD-160).
- **Ship scripts as files or base64**, never through heredocs, scp or remote editors; verify with a checksum or
  `od -c` (L-ENV-007).
- **Start long jobs detached** (`setsid` or `nohup... </dev/null > log 2>&1 &`), then poll the log for a done marker;
  never finalize on the end of an SSH stream (L-ENV-006).
- **Anything started through run-command dies on reboot**: start agents and daemons through systemd and check the
  cgroup (L-ENV-005).
- **Keep output small**: filter on the host and print summaries; write big dumps to a file and read them in chunks
  (L-ENV-003).
- **Use absolute paths** in remote scripts and back files up before writing (L-ENV-035).
- When two agents share one VM, run a read-only host watcher during risky work (L-ENV-040).

```bash
# rc.sh <script>: run a script on the agent VM through the cloud control plane, retrying while the singleton is busy
set -u
for i in 1 2 3 4 5 6; do
  out=$(python -m azure.cli vm run-command invoke -g "$RG" -n "$VM" --command-id RunShellScript \
        --scripts @"$1" --query "value[0].message" -o tsv 2>&1) && { printf '%s\n' "$out"; exit 0; }
  case "$out" in
    *"in progress"*|*Conflict*) sleep $((20 + i * 10));;       # another session holds the channel
    *) printf '%s\n' "$out" >&2; exit 1;;
  esac
done
echo "run-command still busy after retries" >&2; exit 2
```

```bash
# The script that runs remotely (as root): resolve the tool user's home, keep the output under the tail limit
set -eu
sudo -u <user> -H bash -lc 'cd ~ && python3./check.py' > /tmp/check.out 2>&1 || true
tail -c 3500 /tmp/check.out
```

```bash
# IAP hop to a VM with no open SSH path from here (placeholders; pin the account on every call)
B64=$(base64 -w0 remote.sh)
gcloud compute ssh <jump-vm> --zone <zone> --tunnel-through-iap --account=<user> \
  --command "echo $B64 | base64 -d | ssh -i <key-file> <user>@<vm-ip> 'sudo bash -s'"
```

### 7.1 The IAP hop as a service account (human login lapsed)

IAP SSH does not need an interactive human login. A service account that holds the IAM rights to tunnel through IAP and
to SSH to the jump VM keeps working while the human token sits in a reauthentication window; a warehouse-only service
account does not have those rights (L-ENV-008). Prove the path once with
`gcloud compute ssh <jump-vm>... --command true` before you depend on it.

1. Tar the job locally: `tar czf pkg.tgz main.sh <files>`, plus a small hop script `hop.sh` (below).
2. Copy both to the jump VM with up to 4 tries, 10 s apart, pinning the account (L-ENV-009).
3. Run the hop with stdin closed (`</dev/null`) and filter gcloud's banner lines out of the output.
4. The hop script copies the tarball on with plain `scp`/`ssh` (`-o BatchMode=yes -o ConnectTimeout=20`), unpacks it
   in a temporary directory on the target VM, runs it and removes it. When the onward SSH key sits in another user's
   home on the jump VM, the hop script runs `scp`/`ssh` under `sudo`.

```bash
# run.sh: run main.sh on <vm> through <jump-vm> as a service account (placeholders)
Z="--account=<service-account> --project <cloud-project> --zone <zone> --tunnel-through-iap"
for i in 1 2 3 4; do gcloud compute scp pkg.tgz hop.sh <jump-vm>:/tmp/ $Z && break; sleep 10; done
gcloud compute ssh <jump-vm> $Z --command 'bash /tmp/hop.sh' </dev/null \
  | grep -viE '^(Warning|Updating|External IP|Existing host|Pseudo-terminal)'

# hop.sh (runs on the jump VM)
KEY=<key-file>; [ -r "$KEY" ] || SU=sudo
O="-o BatchMode=yes -o ConnectTimeout=20 -i $KEY"
$SU scp $O /tmp/pkg.tgz <user>@<vm>:/tmp/ &&
$SU ssh $O <user>@<vm> 'mkdir -p /tmp/x && tar xzf /tmp/pkg.tgz -C /tmp/x && cd /tmp/x && bash main.sh; rm -rf /tmp/x /tmp/pkg.tgz'
```

| If you get | Cause | Fix |
|---|---|---|
| `Permission denied (publickey)` at the jump VM | the global gcloud account flipped, or the service account lacks the SSH right | pin `--account` on the call (L-ENV-009); check the account's IAM roles |
| `Reauthentication failed, cannot prompt` | the call ran as the human account | move the call to the service account |
| the onward `scp` prompts or hangs | no `BatchMode`, or the hop user cannot read the key | `-o BatchMode=yes`; run under `sudo` when the key belongs to another user |

Check the human login with a timeout before relying on it (`timeout 15 gcloud auth print-access-token`). Warehouse-only
work needs no hop at all: a throwaway container that mounts a service-account key read-only is enough (L-ENV-008).
Before resizing or rebooting the VM behind these paths, read the resize notes in
[05 Environment Traps](05-environment-traps-windows-git-bash-az-gcloud-docker.md) (section 8.1) and the post-boot
checklist in [Secure Agent - Install, Run & Tune](../02-secure-agent/01-secure-agent-install-run-tune.md)
(L-ENV-069).

## 8. Where the tracker fits

A task board (an issue tracker with comments, labels and an API) is the program's memory and its coordination
surface:

- **One central project** is the single log of all IDMC activity; older projects are frozen as archives with
  cross-reference comments (L-METHOD-022).
- **Leases and claims** tell other sessions what you own and what they must not touch (L-METHOD-062),
  (L-METHOD-063).
- **Gated items** carry a blocked label that names the human they wait on (L-METHOD-065),
  (L-METHOD-078).
- **Two write paths** worked: REST under the tracker's rate limit, with a unique idempotency marker inside the comment
  HTML; and bulk writes through the ORM shell inside the tracker's API container
  (`docker exec -i <tracker-api> python manage.py shell < /tmp/x.py`). Both have quirks (L-METHOD-077).

Full protocol: [03 Multi-Agent Coordination](03-multi-agent-coordination.md).

## 9. What to log

| Event | Where | Minimum content |
|---|---|---|
| Any write to an org | tracker comment on the owning issue | object id, what changed, the exact undo, session, UTC time (L-METHOD-022) |
| A wall | tracker, then the KB | verb, host, path, headers, body shape, error code, org, date (L-METHOD-035) |
| A probe | tracker | what was created, the cleanup, the zero-residue check (L-METHOD-069) |
| A decision taken without asking | tracker | the default chosen and its undo (L-METHOD-066) |
| A UI-only step | tracker | the verbatim confirmation, the UI path, the REST read-back (L-UI-010) |
| Data leaving the network | egress ledger | bytes per action and dataset, retries included (L-METHOD-092) |
| Host changes | backup directory plus UNDO log | one restore line per change (L-METHOD-013) |
| Secrets | nowhere | names and locations only (L-METHOD-087) |

## 10. Checklists

**Start of a session**
1. Look for other sessions working the same request and for live leases or fences on the tracker (L-METHOD-061).
2. Establish the org from the cached session: org name, both id shapes, pod, domain, base URL (L-METHOD-008).
3. Read the agent engines and their status, not the login `products[]` (L-METHOD-033).
4. Confirm your reach path to the agent host and who else is using it (L-ENV-003).
5. Search the KB for the thing you are about to try before probing (L-METHOD-034).

**Before a write**
1. Take a backup that can be restored (v3 export, JSON, file copy).
2. Dry run; assert the org from a live read; assert every anchor.
3. If anything shared is touched, claim it and announce the window.

**After a write**
1. Read it back, then verify the data effect, not only the status.
2. Log the id and the undo on the tracker; release the lease with evidence.
3. If a call was interrupted or rejected, read back anyway: it may have run (L-METHOD-021).
4. After an agent, runtime-selection or pipeline change, run the read-only verification sweep scoped to "since <change
   time>" ([02 Evidence Discipline](02-evidence-discipline.md), section 8) (L-METHOD-057).
