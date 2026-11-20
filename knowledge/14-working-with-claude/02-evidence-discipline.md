# Evidence Discipline

**Answers:** How sure is a finding? How do I tell a real 200, 404 or 405 from an artifact, prove that a write landed,
prove that a process is or is not in a data path, read vendor documentation reliably, and publish a number or latency
that holds?

**Read when:** before stating any verdict ("not licensed", "works", "done", "not in the path", "N seconds"); after a
change to agents, runtime selections or pipelines; when a capability question is answered from vendor docs.

**Key rules:**
- Four evidence states: WORKS (a dated live status), DOC, REJECTED, UNTESTED; never merge rejected with untested
  (L-METHOD-023).
- Probe with a bogus twin, an empty POST, Content-Type variants and a host sweep before calling anything a wall
  (L-METHOD-024, L-METHOD-027, L-METHOD-029).
- Read back every write and every item of an async job; a job id is a submission, not success (L-METHOD-030,
  L-METHOD-031).
- Never score from a status, a container state or an issue state; a new-connection sampler cannot prove a process is
  out of a data path, so measure bytes on its existing sockets, then run a reversible stop test (L-METHOD-041,
  L-METHOD-123).
- Read the live schedule (crontab, systemd timer, IDMC schedule), never a repository copy of it (L-METHOD-124).
- Every published number comes from a read-only collector: success-only, per hop n / average / fastest / last, p50 only
  from at least 5 samples and p95 from at least 20 (L-METHOD-049).
- After any agent, selection or pipeline change, run one read-only sweep scoped to "since <change time>"; a green
  sweep covers only its window (L-METHOD-057).

**Related:** [01 How Claude Reaches and Drives IDMC](01-how-claude-reaches-and-drives-idmc.md) · [03 Multi-Agent Coordination](03-multi-agent-coordination.md) · [Error Triage](../00-start-here/04-error-triage.md) · [Performance, Concurrency & Job Caps](../04-mappings/06-performance-concurrency-job-caps.md) · [Lessons: Claude Working Methods](lessons.md)

**Last verified:** 2026-10-03

> **Summary.** Almost every wrong IDMC conclusion on record came from weak evidence, not from IDMC: a 404 read as
> "unlicensed", a zero-byte 200 read as "works", a type filter that silently matched nothing, a status standing in for
> an observation, an idle-looking process that was in the data path. This doc is the rulebook: the evidence states, the
> probe toolkit, read-back after every write, dated walls, the stages authored / deployed / running / integrated, the
> false-green families, the post-change sweep, the latency collector, and a red-flag checklist to run before any verdict.

---

## 1. The four evidence states

| State | Means | How to say it | Lesson |
|---|---|---|---|
| **WORKS** | a live status code observed on a stated org and date | "proven as of <date> on <org/pod>"; re-probe before promising | (L-METHOD-023) |
| **DOC** | a named Informatica guide states it; nobody exercised it | "documented, unproven"; never report as working | (L-METHOD-023) |
| **REJECTED** | refused with a code | a finding; `405` = the verb does not exist at any permission level | (L-METHOD-023) |
| **UNTESTED** | absent from all evidence | "unknown", never "unsupported"; 569 of 830 endpoint-verb pairs were untested in one early endpoint corpus | (L-METHOD-023) |

Rules that follow from the table:

- A blank or `--` cell is **untested**, not absent; `405` is absent. They are opposites.
- Keep `rejected: PUT 405` and `untested: PUT, PATCH` in separate columns. Merging them produced every walked-back
  verdict in that corpus.
- Vendor documentation is durable; live probes are dated snapshots that were seen flipping every 3-5 days
  (L-METHOD-035).
- A verb census is itself a dated snapshot. An early count had PUT at 0 proven; a PUT on runtime-environment
  selections was proven later (L-METHOD-032).

### 1.1 Six verdicts for "can this run headless?"

| Verdict | Means |
|---|---|
| HEADLESS | a live status proved it |
| HEADLESS-DOC | documented, unexercised |
| NEEDS SHELL | no browser needed, but a host shell is (agent install, driver staging) |
| UI-ONLY | licensed and working; a human clicks |
| UNTESTED | unknown |
| WRONG-HOST RISK | recorded absent, but the host family was never swept |

And four kinds of "cannot": a **hard wall** (empty-body 404, or 405 on every verb: design a click in), a **read-only
resource** (405 on this verb: use the update idiom, `POST /api/v2/<resource>/{id}` on the v2 plane), **not on this
host** (404 with a body: try the other host) and **nobody checked** (never quote it as a limit). Commercially,
UI-ONLY ("one click in something you already own") must never be presented as a GAP ("not there")
(L-METHOD-036).

## 2. The probe toolkit

### 2.1 Bogus twins

Probe a nonsense sibling next to every input you control. If the twin answers the same way, the answer is an
artifact (L-METHOD-024).

| Twin the... | Example | Artifact it exposes |
|---|---|---|
| path | `GET /data360/search/api/v99/bogusZZZ` | a gateway that answers every prefix with a zero-byte 200 |
| object name | `.../entity/ZZFAKEENTITY` | a 403 from an ACL that runs before the metadata lookup |
| host | an unroutable IP in a connection test | `error [error [null]]` that never touched the network |
| error-producing route | `GET /api/v2/agent/bogusZZZ` | router 403/500 answers that prove no handler exists |
| whole host | any path on `-apim` / `-apigw` | nginx 503 from a load balancer with no backend |

### 2.2 A 200 can be fake

- `200` with `Content-Length: 0` and no `Content-Type` = prefix routing with nothing behind it. The control is a
  known-real plane: `GET /api/v2/bogusZZZnope` returns `404 "Resource not found"` (L-METHOD-025).
- `200` carrying the identity-service login HTML = wrong plane, wrong header or a stale session. One record read
  "passed" this way and fooled both a slide and the first re-check (L-METHOD-025).
- `200` whose value reverts on read-back = a silent rejection (L-METHOD-030).
- `200 {"count":0,"objects":[]}` from `GET /public/core/v3/objects?q=type=='X'` proves nothing: the type filter is not
  validated and a fake type returns the same (L-METHOD-038).

### 2.3 Read the kind of 404

| You see | It means | Do |
|---|---|---|
| 404 with a JSON or text body | wrong path or wrong host | keep hunting; check `dm-us` vs `dmp-us`, pod host vs domain host |
| 404 empty body, or `No static resource <path>` | the route is absent (after a host sweep) | stop; design the click in |
| 404 with a typed product error (`DBMI_TASK_WAS_NOT_FOUND`) | a live handler answering a lookup | fix the id |
| `404 CMN00005` on the MDM host | generic; bogus siblings get it too | compare with a twin |
| 403 / 405 | role gap or read-only resource | never read as entitlement |

(L-METHOD-026)

### 2.4 Empty-POST verb probes

IDMC has no HEAD or OPTIONS. POST an empty body: `400` / `415` / `422` = the verb exists and the body is wrong;
a `500` naming a null field (`Cannot invoke Object.getClass because o is null`) = the handler parsed and ran;
`405` = no such verb. An empty body cannot create anything (L-METHOD-027).

### 2.5 Vary the Content-Type

The same upload route answered four ways on one org:

| Content-Type on `POST /public/core/v3/import/package` | Answer | Reading |
|---|---|---|
| `application/json` | `404 MigrationSvc_025` | looks like "wrong path"; it is not |
| `application/zip` | `415` | verb and path exist |
| `application/octet-stream` | `415` | verb and path exist |
| `multipart/form-data` | `400 MigrationSvc_030` | validator reached: the route is alive |

Only a `405` on every encoding is a verdict (L-METHOD-028).

### 2.6 Sweep the host family, then apply the stopping rule

Resolve candidate hosts by DNS before believing any service-level 404 (`<pod>-ing`, `-cai`, `-mdm`, `-dqprofile`,
`-dqcloud-api`, `idmc-api.<domain>`, `cdgc-api.<domain>`, `hdm.<domain>`, plus a bogus suffix as the control). Then
stop only on uniform 404 across many plausible shapes with no 405 anywhere, each shape matching its twin; any 405
means keep going (L-METHOD-029). A single DNS sweep turned a whole product's "UI-only" verdict into a
wrong-host error.

### 2.7 Search before you probe

Grep the KB, its evidence and the verb matrix for the endpoint and the exact error string first. A session once swept
13 connection-type spellings after a `403 APP_10519` and recommended a licensing ticket; the verified body
(`type: "TOOLKIT_CCI"`, connector name in `instanceName`) was already on disk (L-METHOD-034).

**Reading vendor documentation.** Claude's web-fetch tool was refused (HTTP 403) by the vendor documentation site, and
it returns a model summary instead of the page, which proved unreliable for limits and tables. Fetch the raw page
instead (L-METHOD-126):

1. GET the page read-only with a desktop-browser User-Agent (Python `urllib` or `curl`); no login is involved.
2. Drop `script`, `style`, `nav`, `header` and `footer` elements, strip the tags, collapse whitespace, and save
   `<name>.txt` with the source URL on line 1.
3. Grep the saved text for the exact sentence and quote it with its URL and the page's "Updated:" month. Search for a
   phrase from the body, not a heading: the saved text also holds the guide's whole table of contents. Prefer
   `.../current-version/...` URLs.
4. Record the claim as DOC (documented, unproven) until a run on an org confirms it (section 1).

```python
import html, re, urllib.request
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
def page_text(url):
    h = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60).read.decode("utf-8", "replace")
    h = re.sub(r"(?is)<(script|style|nav|header|footer)[^>]*>.*?</\1>", " ", h)
    t = html.unescape(re.sub(r"(?s)<[^>]+>", " ", h))
    return re.sub(r"\n\s*\n+", "\n", re.sub(r"[ \t\r]+", " ", t))
# open(name + ".txt", "w", encoding="utf-8").write(url + "\n" + page_text(url))
```

### 2.8 Prove where a fault lives

Make the identical call with the same session on a case that should work and one that fails (for example re-publish
versus first publish): a deterministic split is ticket-grade evidence. When an error is ambiguous, reproduce the
operation outside IDMC, for example the JDBC driver run by hand on the agent host, and read the target system's own
logs (L-METHOD-051).

**Proving a process is NOT in a data path** (L-METHOD-123). A sampler that flags only new outbound connections
misses traffic on long-lived tunnels and keep-alive connections. A data gateway that serves a chat-to-SQL feature keeps
its tunnels to the vendor cloud open, so it looked idle to such a sampler for six minutes around a query, and stopping
its Secure Agent then broke the feature within minutes. To prove absence:

1. Before and during one triggered request, compare the per-socket byte counters of the process
   (`ss -tinp`: `bytes_sent`, `bytes_received`) or its `/proc/<pid>/io` `rchar` / `wchar` deltas, together with the
   process's own log lines.
2. If the counters move, the process is in the path. If they do not, run the reversible stop test with the restart
   command ready (`systemctl stop <unit>`, trigger the request, `systemctl start <unit>`) and time the recovery.
3. A negative from a new-connection sampler is not evidence.

## 3. Writes: read back, then read the items

| After this write | Read back with | Watch for |
|---|---|---|
| v2 `POST /api/v2/<resource>/{id}` | `GET` the same id, compare the field | a reverted value = silent rejection (L-METHOD-030) |
| v2 `DELETE` | `GET` the id | 403 = gone; a deleted schedule's GET is an empty 200 shell, so check the list |
| FRS delete / move | the per-item codes, then a GET | `FRS_200` ok, `FRS_082` still published, `FRS_087` project not empty, `FRS_070` not found |
| FRS PATCH of `customAttributes` | a GET | 204 and nothing changed |
| Export, import, publish, scan, metering export | poll the job, then each item | a job id is a submission, not success; items fail inside 200 envelopes and `207 Multi-Status` (L-METHOD-031) |
| Anything a user rejected mid-call | a GET of every object it could have touched | the request may have landed anyway (L-METHOD-021) |

## 4. Dating walls and re-testing them

Record every wall in this shape, on the tracker and in the KB (L-METHOD-035):

```
WALL <short name>
  verb + host + path : POST https://<pod>-cai.<domain>.informaticacloud.com/active-bpel/asset/v1/publish
  headers + encoding : INFA-SESSION-ID, Accept/Content-Type application/vnd.api+json
  body shape         : {"data":{"type":"publish","attributes":{"assetPaths":["<path>"]}}}
  answer             : <status> <error code> <message head>
  twin / control     : <what the bogus twin returned>
  org / pod / date   : <org> / <pod> / <YYYY-MM-DD>
  re-probe when      : agent build, pod, header, path format, content type or available tools change
```

Re-probe instead of re-grinding: a wall needs a new angle (a host, a header, an encoding, a path format, a captured UI
call), not a louder retry. Many walls fell exactly this way; they are listed in the overturned-beliefs
sections of the domain docs and in section 10 below.

## 5. Suspect your own input first

Walls that turned out to be inputs (L-METHOD-038):

| "Wall" | Real cause |
|---|---|
| `IDS_085` "user name or password is not valid", read as a lockout | wrong login domain, or a truncated username |
| "the authored objects vanished" | `type=='DBMI'` returns 0 (the type is `DBMI_TASK`) and the objects sat in another user's project |
| CAI publish `BAD_REQUEST "Invalid asset path"`, read as "needs a designer Save" | the path format; `Explore/<project>/<folder>/<name>.PROCESS.xml` works |
| import route "closed" | the JSON Content-Type on a multipart route |
| "not entitled" | the login `products[]` list read as the entitlement set (L-METHOD-033) |

## 6. Stages: authored, deployed, running, integrated

Never round a stage up (L-METHOD-039):

| Stage | Proven by |
|---|---|
| Authored | the design object exists (v3 object read, by id) |
| Deployed / published | the runtime accepts it (publish job items SUCCESS, deploy status `deployed`, a runtime call answers) |
| Running | a run completed with rows in the target (activity log plus a warehouse count) |
| Integrated | the live application reads IDMC-produced data, reacts to a CAI decision or shows DQ results |

- Keep a dual gate per step: works in the app, visible in the IDMC UI.
- A schedule is "set", not "proven", until a run started by the scheduler itself completes at its window
  (L-METHOD-040).
- Never simulate IDMC behaviour and present it as real; label in-house analogs as analogs until the genuine runtime
  produces the outputs, and keep the legacy path alive until then.

## 7. False greens

Never score from a status code, a container state, a process state or an issue state (L-METHOD-041).

| False green | What it hid | Positive observation instead |
|---|---|---|
| hostname returns 200 | routed to the wrong application | the right content in the body |
| containers Up (healthy) | a pipeline that processed nothing for 38 hours | rows landing, fresh timestamps, completed runs |
| health checks green | every route returning 500 | real requests along the user's path |
| item marked Done | code absent or uncommitted | the files on disk, committed; the tests re-run |
| tests green | the app could not parse a request body | the app serving a real request |
| a count of 0 | a swallowed 404 | the call's status and body |
| task SUCCESS | 0 rows written | `successTargetRows` and a target count (L-METHOD-043) |
| panel green | a dropped table and a hard-coded fallback | an explicit unavailable state (L-METHOD-042) |
| gate exited 0 | failures masked by the driver or by `tail` | the summary line (L-METHOD-047) |
| a new-connection sampler shows no traffic from a process | traffic on tunnels the process already holds open | per-socket byte deltas, then a stop test (section 2.8) (L-METHOD-123) |
| the schedule file in the repository says "hourly" | the live cron entry ran every 20 s | the live crontab, systemd timer or IDMC schedule (L-METHOD-124) |
| a cron line is in place and "runs" | a bare `flock -n... python3 <job> >> log` did no work for an hour | a wrapper that logs non-zero exits and writes a heartbeat; after any cron edit, check that the log moves at the next due tick (L-METHOD-124) |
| every pipeline hop green, yet the BI page never shows the new record | the open embedded view stays bound to the workbook revision it loaded | a fresh view session; see [Serving Outputs to BI and Apps](../04-mappings/09-serving-outputs-to-bi-and-apps-freshness-latency-reverse-etl.md) (L-ENV-083) |
| a DQ format dimension reads 99% | the rule tested a parsed value, not the stored string | count the non-matching stored values by pattern; see [DQ Scorecards](../08-data-quality/04-dq-scorecards-warehouse-pattern-and-data-profiling-scorecards.md) (L-DQ-105) |

Monitors and audits must be able to say "I do not know": emit `available=0` with a reason, record UNKNOWN (not NO)
when a system is unreachable, treat no-data as alerting, and confirm an "empty" reading with an independent query
(L-METHOD-042). Prove every verifier can fail by injecting a fault, and reconcile what was discovered
against what actually ran (L-METHOD-047).

## 8. Proving what IDMC actually did

- **Evidence layer per capability.** IDMC-native output versus an equivalent in warehouse SQL or scripts; the
  warehouse's query history shows the writer (a script client with no Informatica engine signature is not IDMC);
  check which schema the running tasks really write; audit wrappers for side-channel DDL; classify REAL, FACADE,
  NOT IDMC, DISCONNECTED (L-METHOD-043).
- **Transformed, not copied.** Join target to source on the key and count changed values per column; show a DQ flag
  catching exactly the known-bad rows; pair it with the job's own row counts. Build specs from the SQL that actually
  produces the live table, not a staged copy (L-METHOD-044).
- **Parity.** Same watermark on both sides, counts both ways, `EXCEPT DISTINCT` on
  `to_json_string(struct(<common cols>))` in both directions, run-time columns excluded, latest snapshot pinned, drift
  direction read, a full delete-aware reload after purges, and no widened tolerances (L-METHOD-053).
- **Environment of the evidence.** Know which host, datasource and checkout produced it; a dev overlay does not prove
  production (L-METHOD-050).
- **Measure alone.** Quiesce other load before timing anything (L-METHOD-052).
- **Fix at the source.** Scheduled rebuilds erase manual fixes to outputs (L-METHOD-054).

### 8.1 The post-change verification sweep

After any agent, runtime-selection or pipeline change, run one read-only script that takes the change time T and only
reads (L-METHOD-057). Run it in every org that shares the host, then time one real end-to-end story hop by
hop. A green sweep is evidence only for the window it covered (L-METHOD-041).

| Check | Call | Red flag |
|---|---|---|
| Agents and engines | `GET /api/v2/agent`; per agent `GET /api/v2/agent/<id>` (skip `active: false`: their engine lists are stale); then `GET /api/v2/agent/details/<id>` | any `agentEngineStatus.status` other than RUNNING |
| Runs since T | `GET /api/v2/activity/activityLog?rowLimit=1000`, paged with `offset` | state 2 (warning) or 3 (failed) since T; the oldest row returned is newer than T, so the window is truncated: page further |
| Running now | `GET /api/v2/activity/activityMonitor?details=true` | stuck or unexpected jobs |
| Schedules | `GET /api/v2/schedule` | disabled, or the wrong cadence |
| CDC | `GET https://<pod>-ing.<domain>.informaticacloud.com/dbmi/api/v1/task/<taskId>/job` per task | not running |
| Outputs | minutes since the last write of each landed table (BigQuery `<dataset>.__TABLES__.last_modified_time`; for a view, query its newest row, because a view's last-modified time is its definition change, L-ENV-079); the real-time leg's failures and p50 from its decision table | stale tables; a failure burst or a p50 jump |
| Host | free memory and swap | swap full; OOM kills |

Keep it read-only by construction: no writes, and never import a legacy script for one of its helpers, because its
module-level code may delete things (L-METHOD-124).

### 8.2 End-to-end proof with namespaced test identities

(L-METHOD-104)

1. Create the test identities in a run-specific namespace (for example `qa.<run>.<n>@example.com`) and drive the
   real public endpoints on every channel, through each channel's real UI as well
   ([04 UI Automation with Playwright](04-ui-automation-with-playwright.md), section 7).
2. Before any cleanup, run a read-only trace for the namespace. Per source row it prints the event time, the CDC
   landing lag, the IDMC landing task and time, the golden-table appearance, the CRM record id and the BI publish
   time, so every hop is proven per record. Keep the output as the evidence.
3. Purge net-zero on every surface with a script that refuses any pattern outside the namespace and dry-runs by
   default (`--apply` to act): application tables in foreign-key order, the identity provider, the mail catcher, and
   CRM records by external id (children first, then empty the recycle bin). Source deletes reach the warehouse
   through CDC.
4. Budget IDMC jobs per story (each event that triggers a lane costs one lane run) and read the job budget before and
   after ([Entitlement, Licenses & Job Caps](../13-ipu-cost/03-entitlement-licenses-job-caps.md)).
5. Enrichment that deliberately skips test identities (address verification, for example) must still be proven on a
   real record.

| Row | Event time | CDC landed (lag) | IDMC landing task (+s) | Golden table (+s) | CRM id | BI publish (+s) |
|---|---|---|---|---|---|---|

## 9. Numbers, deletions and completion claims

- **Numbers.** Every figure comes from a query and every timing from a measurement with its window; no p50 below about
  5 timed calls or p95 below about 20 (one slow histogram bucket became a "1,600 ms" headline from 13 timed calls); no
  estimated coverage percentages (L-METHOD-049, L-ENV-088). API-gateway policy expressions have no clock, so
  time calls in each backend (a `server-timing: app;dur=<ms>` response header) and log that field (L-ENV-088).
- **Deletions.** Enumerate, never infer: live counts, producers and consumers, task-level schedules (visible only in the
  task detail GET), app readers of the output; a 403 on enumeration means "not deletable" (L-METHOD-048).
- **Completion.** The doer never validates. A second agent re-runs the evidence, checks the artifacts are committed,
  probes endpoints expecting 401/405 rather than 404, and bounces anything that does not reproduce
  (L-METHOD-045). For figures and blocker lists use refute-only reviewers, and when two audits disagree
  report the stricter one (L-METHOD-046).
- **Ceilings.** When the headless surface is exhausted, report the residue by owner and blocker instead of re-running
  agents at it (L-METHOD-055). The residue is usually a UI-only final step or a gate, rarely a licence
  (L-METHOD-037).

### 9.1 Publish latencies only from a read-only collector

Every latency shown on a page, runbook or status report comes from a collector, never typed in (L-METHOD-049).

1. Compute each hop from timestamps the platform already records: source commit to CDC landing; event to the first
   successful CAI upsert in your decision log; event to the end of the first fully successful CDI lane run that
   started after it; event to the first verification row; gateway log time to warehouse arrival. Use a rolling window
   (24 h).
2. Publish per hop `{label, path, n, avg_ms, fastest_ms, last_ms, last_at, status: ok|no_samples|unavailable, source,
   note}`, plus `window_hours`, `generated_at`, `excluded[]` and the pipeline `mode`.
3. Count successes only: HTTP below 500 (4xx fast-fails drag "fastest" down), IDMC runs SUCCESS or WARNING, a lane only
   when every task succeeded. A sample belongs to the window in which it completed; drop samples that overlap a deploy
   and negative values (clock skew); match an outcome to its event within 10 minutes and count only the event's own
   first check.
4. Keep hops independent (one failing query marks only its hop `unavailable`), write the output atomically (temp file
   plus rename), refuse to publish when fewer than 3 hops were measured, hide hops with no samples, split lane
   statistics by pipeline mode, and show batch schedules as cadence plus last run, never as a latency.
5. Read-only by construction: PostgreSQL in a `READ ONLY` transaction with a `statement_timeout`; BigQuery SELECT-only
   behind a guard with `maximum_bytes_billed` and job labels. Mark every assumed table, column or process name with
   `# ASSUMPTION:` and its evidence, keep hops over unconfirmed schemas behind a flag, and check that each hop keys on
   names the callers actually log (a hop keyed on a name nobody writes stays at 0 samples forever).

| Before publishing a number, ask | The trap it catches |
|---|---|
| are failures excluded? | an average over all calls (809 ms at 51.8% success, the failures sitting at the timeout) |
| is it the last attempt only? | a client that stores latency for the final attempt, hiding retries and backoff |
| wall clock or task span? | a run's wall time quoted as the IDMC task time |
| is a view counted as a hop? | a "real-time view" hop that is only a view over the CDC table |
| does it depend on the pipeline mode? | lane times quoted across a cadence change |
| is the cadence still true? | an "every 4 h" rebuild that had become daily |
| is the first-seen timestamp preserved? | a re-check that overwrites the time and destroys the first-time latency |
| is the measure still defined? | a re-applied DDL that redefines a view without a newer column |
| was the dashboard timed cold and warm? | a 17-26 s cold load caused by the BI vendor's CDN assets, while viewers see 8-9 s warm |

Reference numbers from one stack, for orientation only: CAI to a SaaS target about 2 s; a CDC row about 26 s average
(10 s fastest); an event-driven CDI lane about 106 s average (62 s fastest) to the trusted record.

## 10. Red flags: about to say X, check Y

Run this before any verdict leaves the session (L-METHOD-056):

| About to say | Check first |
|---|---|
| "not entitled" / "not licensed" | `agentEngines[]` and their status, privileges, runtime-environment selections; not a 404 or `products[]` (L-METHOD-033) |
| "not possible" / "no API" | KB grep, host sweep, empty POST, Content-Type variants, the UI's own XHR (L-UI-002) |
| "the account is locked" | the login domain and the full username; one attempt only (L-METHOD-070) |
| "it works" | the body, not the status; a bogus twin of the 200 |
| "done" | the stage (authored / deployed / running / integrated) and the environment of the evidence |
| "it vanished" / "count is 0" | the exact v3 type name, other users' projects, unfiltered listing |
| "UI-only" | whether a clone, a service's own publish/deploy call, an MCP tool or a captured XHR does it |
| "limitation" (to a customer) | is the cell UNTESTED? is it dated? re-probe on their org |
| reusing an endpoint from another org | re-derive org, pod and domain (L-METHOD-008) |
| "MCP can do it" | the server's actual tool list; MCP does not widen what REST can reach (L-METHOD-011) |
| "nothing happened" after an interrupted call | a read-back of everything it could have changed (L-METHOD-021) |
| "the monitor shows empty" | an independent query through a different client (L-METHOD-042) |
| "X is not in the data path" | per-socket byte deltas and a reversible stop test, not a new-connection sampler (L-METHOD-123) |
| "it runs every N minutes" | the live crontab, timer or IDMC schedule, not the repository copy (L-METHOD-124) |
| "latency is N s" | the collector's n, window, success-only rule and pipeline mode (L-METHOD-049) |
| "the docs say" | the raw page text with its URL and Updated month; label it DOC, not WORKS (L-METHOD-126) |
| a response shape taken from the docs | a captured live body; build test fakes that reproduce the live failures (L-METHOD-171) |
| "your lessons" / "IDMC can't, X can" (a comparison) | the provenance of every claim (this project, another project, general guidance), and each product claim checked against current vendor docs (L-METHOD-149, L-METHOD-157) |
| "IDMC can do X" (a capability rating) | the tier: built in, built with IDMC assets and proven, or buildable but not yet built (L-METHOD-161) |
| "the agent status is stale" / "the test passes with the agent stopped" | whether the same agent identity now runs on another host (L-METHOD-154) |

## 11. Overturned beliefs (kept so nobody re-learns them)

| Belief | Believed | Overturned by |
|---|---|---|
| Zero PUT proven anywhere; never design on PUT | 2026-07-25 to 2026-09-27 | PUT on runtime-environment selections (L-METHOD-032); was L-METHOD-096 |
| A documented path that 404s means absent or unlicensed | to 2026-07-25 | the host-family sweep and stopping rule (L-METHOD-029); was L-METHOD-097 |
| Read almost everything, run almost everything, design almost nothing | 2026-07-13 to 2026-09-22 | clones, service publish/deploy calls, selections PUT, IMF mapping import (L-METHOD-093); was L-METHOD-098 |
| Clone-authored objects do not persist in a shared org | 2026-09-23 to 2026-09-25 | a wrong type name and another user's project (L-METHOD-038); was L-METHOD-101 |
| A login listing only Integration Cloud has no catalog or CAI entitlement | 2026-09-21 to 2026-09-22 | engines, selections and headless catalog writes (L-METHOD-033); was L-METHOD-102 |
| Playwright is a screenshot tool, not an automation path | 2026-07-10 | designer authoring by automation (L-UI-021); was L-UI-022 |
