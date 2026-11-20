# Working safely with Claude on IDMC: cheat sheet

The rules that keep a Claude session safe and fast with IDMC: logins, hosts, evidence, gated actions, parallel
sessions, UI automation, workstation traps and secrets; applies to every session before its first IDMC call.

**Start with:** `python3 toolkit/check_login.py` (one attempt, cached session, lockout guard; skill `idmc-mp`), then
[01 How Claude Reaches and Drives IDMC](01-how-claude-reaches-and-drives-idmc.md) and its §10 checklists.

## Rules that work

| Rule | How | Lesson |
|---|---|---|
| One org-aware session module per host | Cached session (<= 25 min, 0600), serialized logins, block file after any rejected login | L-METHOD-002, L-METHOD-003, L-METHOD-004 |
| Establish the org first | Org name, both id shapes, pod, domain, base URL from a live read; destructive scripts assert it | L-METHOD-008 |
| Right host + right header | Derive every host from the login answer; never string-replace a pod literal | L-METHOD-007 |
| Search before probing | Grep the lessons and KB; date every wall and re-test it | L-METHOD-034, L-METHOD-035 |
| Probe honestly | Bogus twin, empty POST, Content-Type variants, host sweep before any "wall" | L-METHOD-024, L-METHOD-026 |
| Read back every write | A job id is a submission; read every item inside a 200 envelope | L-METHOD-030, L-METHOD-031 |
| Four evidence states | WORKS (dated), DOC, REJECTED, UNTESTED; never merge rejected with untested | L-METHOD-023 |
| Entitlement from engines | `agentEngines[]`, privileges, selections; never `products[]` or a 404 | L-METHOD-033 |
| Order of means | REST -> managed MCP tool -> package clone -> the UI's own XHR -> Playwright last | L-UI-001, L-UI-002 |
| Change a task by id | Back up, change one field behind an asserted anchor, read back, diff, run, verify the data | L-METHOD-010, L-METHOD-044 |
| One writer per org | One lead plus lanes; one importer at a time; find other sessions first | L-METHOD-060, L-METHOD-061 |
| Numbers from collectors | Success-only, n / average / last; p50 from >= 5 samples, p95 from >= 20 | L-METHOD-049 |
| Sweep after a change | One read-only sweep scoped to "since <change time>" | L-METHOD-057 |
| Secrets at run time | Env vars or a 0600 file outside every repo; print key names only | L-METHOD-001, L-METHOD-087 |

## What doesn't work, and the workaround

| Wall | Workaround | Lesson |
|---|---|---|
| Re-trying a failed login (about six failures from all sessions lock the account) | One attempt; on `IDS_085` check domain and full username; on `IDS_086` stop, owner resets, ONE attempt | L-METHOD-070 |
| A 200 as proof (zero-byte, login HTML, value reverts) | Read the body; compare with a known-real plane; read back | L-METHOD-025, L-METHOD-030 |
| Scoring from a status, container or issue state; task SUCCESS with 0 rows | Positive observation: rows landed, `successTargetRows`, a target count | L-METHOD-041, L-METHOD-043 |
| Splitting a denied action into pieces, another tool, a subagent or a peer | The denial covers the outcome: build up to the gate, ask once naming action and rollback | L-METHOD-121 |
| Running IPU-consuming or UI-dependent harnesses unattended | Explicit approval flags (`RUN_APPROVED=1`); build and commit, do not run | L-METHOD-068 |
| Playwright behind a transparent proxy renders blank | Headless Chromium with Private / Local Network Access checks off, else a host outside the proxy | L-UI-031, L-UI-013 |
| git-bash swallows `az`; MSYS rewrites `/paths`; heredocs mangle backslashes | `python -m azure.cli`; `MSYS_NO_PATHCONV=1` for IDMC helpers only; write scripts with file tools | L-ENV-016, L-ENV-017, L-ENV-023 |
| Run-command is a per-VM singleton with a 4 KB tail; long jobs die with the call | Retry, keep output small; start long jobs detached and poll a log | L-ENV-003, L-ENV-006 |
| Human cloud login lapsed | Service account with IAP-tunnel and SSH rights; pin `--account` on every gcloud call | L-ENV-008, L-ENV-009 |

## Fastest safe path

1. Find other sessions on the same request and live leases; settle one coordinator (L-METHOD-061). Read-back: tracker shows your claim.
2. Log in once and prove the org (L-METHOD-008). Read-back: org name and id match the user's.
3. Read agent engines and status, not `products[]` (L-METHOD-033). Read-back: engines RUNNING.
4. Grep the lessons for the thing you are about to try (L-METHOD-034). Read-back: matching lesson ids, or none.
5. Before a write: restorable backup (v3 export, JSON), dry run, assert the org and every anchor. Read-back: dry-run plan.
6. Gated actions (spend, shared deletes, production data, privilege, another owner's org) wait for an explicit OK,
   batched into one list (L-METHOD-065). Read-back: the approval recorded.
7. Write, then read it back and verify the data effect, not the status (L-METHOD-030). Read-back: ids, row counts, job states.
8. Log the id and exact undo; if any call was interrupted or rejected, read back anyway (L-METHOD-021).
9. After an agent, selection or pipeline change, run the scoped read-only sweep (L-METHOD-057).

## Top traps

- `IDS_085` -> wrong login domain or username, not a bad password -> check host first, one attempt (L-METHOD-070).
- Stale-password cron or poller re-locks the account after an unlock -> pause it first (L-METHOD-070).
- `count:0` from `objects?q=type=='X'` -> the type filter is not validated -> exact type name, unfiltered list (L-METHOD-038).
- 404 read as "not licensed" -> wrong path or host -> read the kind of 404, sweep hosts (L-METHOD-026, L-METHOD-033).
- A rejected tool call "did nothing" -> it may already have run -> read back everything it could change (L-METHOD-021).
- "It runs every N minutes" from a repo copy -> read the live crontab, timer or IDMC schedule (L-METHOD-124).
- "Done" without a stage -> say authored / deployed / running / integrated, with evidence (L-METHOD-056).
- Storage states, profiles and XHR captures are credentials -> redact login bodies in the hook, 0600 (L-UI-006, L-UI-002).
- CLAIRE chat harness exits early or publishes -> settle only on reply markers; stop at Publish / Accept prompts (L-UI-028, L-UI-030).
- UI click "worked" -> verbatim receipt plus a REST read-back (L-UI-010).
- Anything printed is exposed -> say so, rotate, never reuse the value (L-METHOD-088).
- Secret in a SQL `SET` or query parameter -> lands in warehouse query logs -> send it in the body (L-ENV-078).
- Rotating piecemeal breaks consumers -> one coordinated window, every consumer listed (L-ENV-049).
- Large Claude tasks are overestimated about 2x -> estimate bottom-up, never pad (L-METHOD-122).
- A multi-hour orchestrator in a Claude session gets reaped -> run it on a server with a done-ledger, or as a scheduled
  IDMC taskflow (L-METHOD-148, L-METHOD-160).
- Response shapes typed from the docs -> capture a live body; v3 list envelopes differ per resource (L-METHOD-171, L-ENV-143).
- A write-capable IDMC MCP behind an unattended `--dangerously-skip-permissions` bot -> read-only tools or a human
  confirm gate (L-METHOD-164).

## Go deeper

- [01 How Claude Reaches and Drives IDMC](01-how-claude-reaches-and-drives-idmc.md): the layered stack, session module, REST planes, host reach, checklists.
- [02 Evidence Discipline](02-evidence-discipline.md): evidence states, probe toolkit, false greens, red flags.
- [03 Multi-Agent Coordination](03-multi-agent-coordination.md): lead and lanes, tracker protocol, gated actions, lockout avoidance.
- [04 UI Automation with Playwright](04-ui-automation-with-playwright.md): when the UI is truly walled, proxies, storage states, XHR capture.
- [05 Environment Traps](05-environment-traps-windows-git-bash-az-gcloud-docker.md): Windows/git-bash, Azure, gcloud/IAP, Docker, data-platform CLIs.
- [06 Secrets Hygiene](06-secrets-hygiene.md): rules, leak points, rotation, scrubbing git, publication gates.
- Lessons: [Claude Working Methods](lessons.md) (L-METHOD-*), [Environment & Ops](lessons-environment-ops.md) (L-ENV-*),
  [UI Automation](lessons-ui-automation.md) (L-UI-*); skip each file's superseded section.
