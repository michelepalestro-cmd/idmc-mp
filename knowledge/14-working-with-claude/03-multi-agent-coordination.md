# Multi-Agent Coordination

**Answers:** How do several Claude sessions and subagents share one IDMC program without lockouts, double imports,
clobbered files or fake progress? What waits for a human, and how is it asked? How are plans challenged and Claude's
work estimated?

**Read when:** more than one session may be working the same request, org, host or stack; before a gated action
(spend, destructive delete, production deploy); right after a permission guard denied something; planning a demo week
or sizing a task list.

**Key rules:**
- One lead plus lanes, exactly one IDMC writer per org and one importer at a time (L-METHOD-060).
- Find the other sessions first and settle one coordinator before anyone writes; coordinate through tracker comments,
  not messages to approval-gated peers (L-METHOD-061).
- Claim, lease, heartbeat and complete on the tracker; findings go in comments (L-METHOD-062, L-METHOD-063).
- A permission denial covers the outcome: never re-attempt it in pieces, through another tool, a subagent or a peer;
  ask once, batched, naming the action and its rollback (L-METHOD-121, L-METHOD-065).
- Every task sits on one path: Claude, Claude through a named workaround, or the human only as a last resort
  (L-METHOD-066).
- Scope every undo to the files of its change, and give parallel testers of one stack fixed write waves
  (L-METHOD-124).
- Estimate bottom-up from the plan steps; large Claude tasks are overestimated about 2x, so never pad
  (L-METHOD-122).

**Related:** [01 How Claude Reaches and Drives IDMC](01-how-claude-reaches-and-drives-idmc.md) · [02 Evidence Discipline](02-evidence-discipline.md) · [06 Secrets Hygiene](06-secrets-hygiene.md) · [Headless Deletes & Org Cleanup](../12-deploy-migrate/06-headless-deletes-org-cleanup.md) · [Lessons: Claude Working Methods](lessons.md)

**Last verified:** 2026-10-06

> **Summary.** Several Claude sessions and subagents often work one IDMC program at once, sometimes after receiving the
> same prompt. What kept them from locking accounts, double-importing, clobbering files and faking progress: one lead
> plus lanes, one IDMC writer per org, claim / lease / heartbeat / complete on a tracker, human gates kept small and
> batched, a shared session cache with a lockout guard, and strict rules for shared files, shared data and shared live
> stacks. This doc is that protocol, with the tracker quirks and rate limits that shape it.

---

## 1. Roles: one lead, lanes, one writer per org

| Role | Owns | Must not |
|---|---|---|
| **Lead** | the plan, every login to each IDMC org, every import/publish into it, the GO for risky steps | hand its org writes to others mid-change |
| **Host lane** | agent host work: install, systemd, drivers, ports, disk, watchers | log in to IDMC orgs |
| **Caller lane** | repoint preparation (read-only until GO), flip tools, smoke tests | apply changes before GO |
| **Domain lanes** | one component each (CAI, catalog, DQ, app, BI) | touch another lane's objects or files |
| **Read-only lanes** | QA, documentation, checklists, cleanup lists | write anything shared |

(L-METHOD-060)

- Exactly **one IDMC writer per org** and **one importer at a time**; every other session reads.
- One session drives each **shared login** and each **serialized channel** (a per-VM run-command, a shared UI
  session) (L-METHOD-069).
- Risky host scripts are staged as dry runs whose every step prints its undo; they run only on the lead's GO.
- Measured result of this split: a cutover with no lockout and no duplicate import, after a morning in which three
  sessions had tried the same login.

## 2. Starting: find the other sessions first

Several sessions often receive the same instruction or bug list (L-METHOD-061).

1. Search other sessions' recent transcripts and the tracker's recent comments for the same prompt.
2. Settle one coordinator (the lead) and a split by component (one session per system) before anyone writes; two
   crossed splits caused most of the coordination traffic in one clean-up (L-METHOD-061).
3. Post the lanes on the tracker (epic comment) and claim each lane's items (section 3). Send the lane rules to every
   session that joins later: late joiners deployed outside the single-writer lane.
4. Before live execution, check for recent edits by others (files modified in the last few minutes); if a sibling is
   already driving, defer to it and mirror the honest state instead of double-driving (L-METHOD-072).
5. Before coding a fix assigned to you, read the tracker comments on it and the deploy undo list: a peer may already
   have shipped an interim version, so rebase on the live file (L-METHOD-061).

**Messages or tracker comments.** A session running in a prompting permission mode holds every incoming cross-session
message for its user's approval; many expire undelivered, and a stream of them interrupts the user (about 15 in one
clean-up). Before messaging, check the peer's mode (its messages arrive marked as prompting; delivery notices say
"held for approval"). Message only peers that receive directly; for the others post one tracker comment on the issue
they read, and never resend a denied or expired message (L-METHOD-061). Keep the hash guard on every shared-file
write regardless (section 6): it still caught a peer that never received the warning.

## 3. The tracker protocol: claim, lease, heartbeat, complete

Comment templates that worked (L-METHOD-062), (L-METHOD-063):

```
CLAIM <session> <UTC ISO> owns: <item keys / objects / files>
      peers must NOT: <e.g. create or run these tasks; restart the Secure Agent; stop the legacy service>
LEASE owner=<session> since=<UTC ISO> expires=<UTC ISO + 30m>
HEARTBEAT <session> <UTC ISO>: <one line of progress>            (at least every 15 minutes)
DONE by <session> <UTC ISO>: <evidence: command, status, counts, read-back>
CLAIM RELEASED - free for any session
FENCE <paths and services owned by <session>> until <condition>
```

Rules:

- **Claim atomically** (assignee = your session, state = In Progress, LEASE comment) before touching anything; never
  edit an item under another session's live lease; comments are append-only.
- **Findings go in comments**, not only in chat, so the next session inherits them; open an issue for new work instead
  of doing it silently; move blocked work to a blocked state with the reason and take something else.
- **One canonical lease format** and a reaper that understands exactly that format. Reap by the tracker's own
  `updated_at` (heartbeat labels get clobbered by concurrent label PATCHes), sweep orphans (a lease label with no
  active lease comment) separately, re-assert terminal states after a reaper race, and ship the reaper and
  validate-sweep crons with the deploy so they cannot drift to retired scripts (L-METHOD-064).
- **Fences.** If another session appears to be editing live files, stay off them and switch to verification or
  read-only work; say so on the tracker (L-METHOD-063).
- **Wait on exact labels.** Completion polls match the exact lane or agent id; a substring match once released a deploy
  before its review had finished (L-METHOD-081).

### 3.1 Board hygiene

(L-METHOD-078)

- The actionable queue is open issues without a `blocked:*` label; each blocked label (or `needs:<person>-decision`)
  names the human or gate: `ui-only`, `entitlement`, `decision`, `app-deploy`, `spend`.
- Native priority is the do-order (urgent = breaks the demo now, high = correctness or a quick decision, medium =
  improves, low = later), mirrored in tier labels; dependency links where they exist.
- Every issue ends in exactly one terminal state (Done, or a Blocked state present in every project) with an
  escalation comment: why blocked / what was done / plan after unblock. Built-but-undeployed work is labelled
  awaiting deploy, not Done.
- Measure dispositioned issues (Done plus blocked-with-reason) over total, not the open count; releasing a blocked
  issue returns it to the queue, so the open count never reaches zero.
- When agents grow the board faster than they drain it, broadcast a convergence directive (finish or release before
  creating). Merge duplicate epics into one parent with pointer comments.
- Keep one central project as the single log; freeze older projects as archives (L-METHOD-022).

## 4. Gated actions: what waits for a human

(L-METHOD-065)

| Action | Gate | Pattern while waiting |
|---|---|---|
| Spending money or paid credits | two approvals: a request stating what and why, then a separate confirm | write the free carve-outs down first (for example ordinary IDMC usage on an existing licence) |
| Destructive delete of shared data | the owner's explicit OK | back up (v3 export, JSON), list the ids on the tracker, delete only those |
| DNS and other outward-facing changes | the owner | stage the change and its undo |
| Production data changes | the owner | dry run, backup, reversible script |
| Any write in an org you do not own | the owner's OK before writes | log each write with its id and exact undo; if not approved, pause and list what was done for a keep/rollback decision |
| Privilege escalation to finish a job | never without a direct OK | if an integration user is correctly refused, back up and wait |
| Runs that consume IPUs or depend on a UI step | explicit approval flags in the harness (`RUN_APPROVED=1`) | build and commit the harness, do not run it (L-METHOD-068) |
| A credential only the human holds | the human | build everything else; hand over one named secret and one command (L-METHOD-067) |

**Under a "no questions" directive**, decide with reversible, documented defaults and record each decision with its
undo; the gates above still hold (L-METHOD-066). **On a production or shared login**, use one serial
session, reversible probes only, zero spend and minimal egress, and log every probe with its cleanup
(L-METHOD-069).

### 4.1 A denial covers the outcome

When the user's permission guard (for example an auto-mode classifier) denies an action, such as a production deploy,
a SaaS record delete or a bulk copy of production code to a workstation, the denial applies to the result, not to that
one command (L-METHOD-121):

- do not split it into smaller steps, route it through another tool, or ask a subagent or another session to do it;
- if a peer's own guard blocked one of its edits, do not redo it at the peer's request;
- build and test everything up to the gated step (read-only probes, private build directories and throwaway copies
  are fine), then ask once for an explicit approval that names the action and its rollback, batching several such
  approvals into one list.

### 4.2 Three paths for every task

(L-METHOD-066)

| Path | Use when | Examples |
|---|---|---|
| 1. Claude | Claude can do it with the access it has | REST and CLI calls, scripts, read-only checks, builds |
| 2. Claude through a named workaround | a console step, a paid service or a missing access has an alternative | an API or CLI instead of a console, a scripted browser, a self-managed runtime, a test identity, a free alternative to a paid service, a wildcard DNS name instead of a DNS change |
| 3. The human, as a last resort | all four conditions below hold | identity, money, legal standing, people, an owner-only business decision |

A task goes to the human only when all four hold: (1) it needs their identity, money, legal standing, people or an
owner-only business decision, or an account Claude has no credential for; (2) no workaround exists and the attempts are
listed; (3) their step is reduced to exact clicks or words, with minutes; (4) it appears in one place only.

- Internal, reversible, no-cost decisions with a recommendation are Claude's: apply the default and record how to
  reverse it (L-METHOD-066).
- One-line approvals (production deploy, destructive delete, spend) stay on Claude's task and are batched into one
  list; they never become a human task.
- Group the remaining human steps by sitting (one sign-in sitting, one decision memo per business). A strict
  workaround hunt cut one human list from 86 tasks (about 100 h) to 16 (about 3 h, plus conversations that cannot be
  delegated).

## 5. Lockout avoidance with a shared session cache

Failed logins from every session and tool add up against one account; about six locked it, and each further attempt
restarted the lock (L-METHOD-070).

1. Every script on a host uses one session module with a shared 0600 cache (reuse for up to 25 minutes)
   (L-METHOD-003).
2. Logins are serialized with a file lock, and a rejected login writes a block file keyed to the creds fingerprint;
   nothing logs in again until the creds change (L-METHOD-004).
3. Exactly one designated session logs in to each org; UI runs reuse a saved storage state inside its window
   (L-UI-005) and stop at the first rejected login (L-UI-004).
4. On `IDS_085` check the login domain and the full username before anything else; on `IDS_086` stop everything,
   have the owner reset (a reset also unlocks), confirm in a browser, then make ONE attempt and share the session.
5. Pause every cron or poller that holds a stale password before an unlock, or it re-locks the account.
6. Prefer a dedicated native automation user; the Secure Agent keeps running scheduled work during a user lock.

## 6. Shared files and shared artifacts

- **Files a peer is using.** Skip anything whose files changed in the last 20 minutes or so, protect files that recent
  scripts reference, and leave Office-open files alone (L-METHOD-071).
- **Before overwriting a shared file**, record its hash (or mtime and size) when you read it and refuse to write if it
  changed; co-edit with compare-and-swap; edit shared deployed files from the live copy and three-way merge peers'
  live edits; ship only the files you changed (L-METHOD-071).
- **An unclaimed live change** (uncommitted edits from an unknown or absent session in a file that is live): commit
  the live content as-is first, then commit your fix on top (L-METHOD-072).
- **One live publisher** for a shared artifact (a BI workbook, a plan): a lease, a lock file, an announced version,
  a replace conditional on that version still being live, and a guardian cron that re-applies the canonical patch
  chain only when it is safe (L-METHOD-074), (L-METHOD-014).
- **One source of truth** for builders, plans and id files; copies drift (L-METHOD-020).
- **Knowledge.** One canonical KB that every agent reads, a per-agent standing file updated on every task, and one
  source file per section for anything many agents edit (L-METHOD-084).

## 7. Shared data

- Delete only the ids your session created; a time-window sweep deleted another session's rows
  (L-METHOD-073).
- Give your test data a unique namespace; wait for a concurrent writer to stop before sweeping its namespace; never
  delete append-only audit rows other writers share.
- Before deleting something that looks unused, check whether another session's scripts own and recreate it, and keep a
  dump of what you remove (L-METHOD-073).
- A sudden data drop is a question for the owning session, with the evidence and the last good backup, before any
  "repair" (L-METHOD-083).
- Measurement over inference before any delete (L-METHOD-048).

## 8. Live stacks and demo weeks

(L-METHOD-075)

- Announce each rebuild window on the tracker; tag the previous image for rollback and roll back automatically if the
  new container is unhealthy.
- Propose a change freeze (no rebuilds, restarts, proxy or gateway edits) from two hours before a demo until it ends.
- At T-30 minutes run one rehearsal command that exercises every hop and cleans up after itself, a real-browser smoke
  of every public surface, and a DOWN/RECOVERED monitor.
- For headless IDMC demos, stage the slow parts (a new agent's engines can take more than 30 minutes) and run only the
  headless moments live.
- Give the demo scene one owner. Catalog work by other sessions (rescans, renames, deletions, data quality runs) changes
  CLAIRE's answers, so the catalog owner announces each change and the scene owner re-tests the prompts after it (L-METHOD-120).
- Before moving a shared feed from one org to another, dry-run it against both and diff per kind (L-METHOD-119).
- **Zero-prep demos.** The presenter does nothing before a demo: Claude runs and undoes every Claude-side switch
  (freezes, rebuilds, forced lanes, fast modes), and a pre-demo checklist for the presenter is a defect. Raise only a
  real external wall that only the presenter can clear (for example a BI login that expires on a known policy), with
  its exact time and the one-time permanent fix. Never trade demo behaviour for cost without saying so (a longer lane
  gap silently broke the live sign-up-to-governed-record moment), and keep internal items out of the presenter's
  summary (L-METHOD-075).
- **Change wording everywhere.** After any change of instructions or wording, grep every copy (runbook, UI strings,
  status lines, tracker pages); one rewording missed three places that still gave the old instruction
  (L-METHOD-075).
- **Scoped undo.** Scope every undo to the files of that change: a git revert of a shared commit, or retagging an older
  image, also undoes other sessions' later work. Build a patch-only undo, test it in a scratch clone, and disable the
  unsafe one (L-METHOD-124).
- **Write waves.** When several sessions test against one stack, give each a fixed write wave inside the hour (for
  example :00-:15, :20-:35, :40-:55) so their pipeline bursts do not overlap, and give one session every CRM purge
  (L-METHOD-124).
- **Scratch files.** Scripts that hold admin passwords never sit in a world-readable `/tmp`: write them 0600 and shred
  them after use (L-METHOD-124).

## 9. Rate limits and fleet sizing

(L-METHOD-076)

| Limit | What happened | Rule |
|---|---|---|
| Model API, account-wide across subagents and the main loop (about 50 requests/min on the plan in use) | agents died on 429 when two fleets ran | hold about 6-7 concurrent agents and slot-fill; one fleet per specialist set; resume a 429-killed agent with SendMessage instead of respawning |
| Tracker API (HTTP 429; `error_code 5900 RATE_LIMIT_EXCEEDED` on one self-hosted tracker) | a paginated read silently lost about 15 issues | pace reads 0.4-1.4 s apart, sleep 15-20 s on the limit error, never truncate a paginated read |
| Workflow barriers | a parallel barrier stalled on its slowest agent | prefer a pipeline shape (L-METHOD-082) |

- The main loop does mechanical tracker work over plain HTTP (scans, labels, reaping), which costs no model budget.
- Subagents inherit the parent's effort level: pass a low effort for bulk review and chunk the inputs; build large
  joins in code from agents' partial results (L-METHOD-082).
- Parallelize backend and IDMC REST work; serialize browser work and UI authoring on shared trees and backends
  (L-METHOD-080).
- Quiesce other load before measuring anything (L-METHOD-052).
- Have a subagent write a large script or document in several calls (modules or sections, each checked before the next):
  agents that tried to write one very large file in a single response died with 'API Error: The response stopped
  arriving' and lost the output (L-METHOD-127).
- Never message a subagent or workflow agent that is still running: the harness resumes it from its transcript in a new
  process, so two copies then work the same task, UI session and objects in parallel. Read its output file for progress,
  wait for the completion notice, then resume it with the message; if it already happened, stop one copy at once and
  give the other sole ownership (L-METHOD-128).

## 10. Fleet shape and verification

- Map specialists one-to-one to domain labels with generated worklists; add only gap-fillers with distinct ids to a
  board a live fleet is draining; require proof that no API path exists before accepting "UI-only"
  (L-METHOD-079).
- Validated is a state after Done, set by a different agent (matched by persona family) that reproduces the evidence
  (L-METHOD-045).
- Audit the tracker against live reality cluster by cluster and fix misclassification in the classifier itself
  (L-METHOD-079); adversarially refute claimed blocks (L-METHOD-046).
- Report the true ceiling and the residue by owner rather than re-dispatching agents at blocked work
  (L-METHOD-055).
- For a large backlog, idempotent append-only seeders (a re-run adds 0) and a file-locked board with atomic `next`
  claims drained 354 tasks with zero overlap (L-METHOD-085).
- **Adversarial critics before execution.** After the read-only discovery lanes, have several independent critic
  passes attack the plan with the raw captures in hand. Each discovery lane writes FACTS, GAPS and RISKS, every item
  tagged with its provenance (live, kb or inferred) and its evidence path; each critic tags findings blocker, major or
  minor, with the evidence and a fix; then one authoritative decisions list overrides the plan wherever they differ.
  Four critics over one plan found 5 blockers and 46 majors, among them a job-budget guard blind to profile runs and
  catalog jobs, a catalog source cloned with DQ automation switched on, and a host-protection step ordered after the run
  it was meant to protect (L-METHOD-046).

### 10.1 Estimating Claude's work

Across 79 tracked Claude tasks the actuals ran well under the estimates, and more so the larger the task
(L-METHOD-122):

| Estimated size | Median actual / estimate |
|---|---|
| up to 30 min | 0.88 |
| 31-60 min | 0.92 |
| 1-4 h | 0.56 (0.35 where Claude logged its own time) |
| above 4 h | 0.44 |

- Never pad Claude estimates. Build them bottom-up from the plan steps: one build and deploy about 45-60 min, one
  read-only check 15-20 min, one new data source 60-90 min of active work, one secret swap about 15 min per group of
  services.
- Treat any single task above about 8 h as one to split, and report totals on one basis, split into must-do,
  calendar-bound and later. Elapsed-time outliers (28-34 h) were waiting, not work.
- Size the human's part to a real calendar: a minimum version per one- to two-week cycle.
- Time-box subagents up front ("write your outputs by T+45 min"): fan-out agents once spent about 55 min on
  reachability probes before writing anything.

## 11. Tracker API quirks to design around

(L-METHOD-077)

| Quirk | Design around it |
|---|---|
| list reads drop items under load | retry and union across passes; never trust one full-board snapshot |
| labels come back as UUIDs | resolve through the project's label map |
| state PATCH is eventually consistent | re-read after sign-out and re-PATCH |
| no issue-relation REST endpoint (on one version) | insert dependencies through the database, or record them in comments |
| project names reject `&` and parentheses | use "and" |
| ORM: label through-table needs project and workspace ids | `get_or_create(..., defaults={project, workspace})` |
| ORM: label removal is a soft delete | trust the through-table's default manager or hard-delete the row |
| ORM: comments regenerate plain text from HTML on save | put idempotency markers inside the HTML |
| ORM: `QuerySet.delete` does not return the usual tuple | call it bare and re-count |

Write paths: REST under the rate limit, or bulk through the ORM shell inside the tracker's API container
(`docker exec -i <tracker-api> python manage.py shell < /tmp/x.py`), which also works through a managed cloud
run-command (L-ENV-004).

## 12. Anti-patterns and the rule that fixed each

| What went wrong | Rule |
|---|---|
| Three sessions tried the same login; the account locked | one designated session, one attempt, one shared cache (section 5) |
| Two claim schemes and a reaper that understood only one | one canonical lease format (L-METHOD-064) |
| A substring label match released a deploy early | wait on exact labels (L-METHOD-081) |
| A time-window cleanup deleted another session's rows | delete only tracked ids (L-METHOD-073) |
| Peers edited the same live file | hash gate, live copy, three-way merge, fences (L-METHOD-071) |
| A stale generator reverted fixes on each publish | one canonical patch chain plus a guardian (L-METHOD-074) |
| Duplicate epics for one program | merge into one parent (L-METHOD-078) |
| Many parallel browser sessions on one backend | serialize UI work (L-METHOD-080) |
| Measurements taken under a fleet's load | quiesce first (L-METHOD-052) |
| A tool call rejected mid-run was reported as "nothing happened" | read back first (L-METHOD-021) |
| A denied production deploy was about to be re-attempted through a subagent | a denial covers the outcome (section 4.1, L-METHOD-121) |
| About 15 cross-session messages sat waiting for the user's approval in one clean-up | tracker comments for prompting peers (section 2, L-METHOD-061) |
| An undo built as a git revert would have reverted three later deploys | a patch-only undo scoped to the change (section 8, L-METHOD-124) |
| A padded plan estimate was rejected as unreasonable | bottom-up estimates calibrated on actuals (section 10.1, L-METHOD-122) |
| Three build subagents read for minutes and died with no files | write output skeletons within the first ~15 tool calls and cap the reading (L-METHOD-152) |
| A chat "yes" was taken as clearing an auto-mode block on a production deploy | stage everything; run the cutover in ask mode with the user approving each step, the unproven step first (L-METHOD-151, L-METHOD-150) |
| Sessions orchestrating a multi-day build were reaped and the chain stalled | run the chain on a server or as a scheduled IDMC taskflow with a gate mapping (L-METHOD-148, L-METHOD-160) |
