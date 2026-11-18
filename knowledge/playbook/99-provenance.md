# Provenance — how old is this, and how to re-verify

> **July 2026 snapshot.** Where this file says "UI-only", "no REST verb" or "walled", read it as a dated verdict:
> many were overturned later (KB `lessons/overturned-beliefs.md`, Laws 16-19). Before telling a user
> something is not possible, work the workaround ladder in KB `knowledge/00-start-here/08 New Pipeline Milestones`.
> "Org A" / "Org B" are two example orgs; derive your own values (Law 1).

## Evidence classes, never blended

| Class | Means | Trust |
|---|---|---|
| **Live** | A status code was observed against a real org on a real pod, on a stated date | High, but dated and org-specific |
| **Documented** | A named Informatica guide states it; nobody exercised it here | Plausible, unproven. Never report as "works" |
| **Untested** | Absent from all evidence | **Unknown, not unsupported.** 569 of 830 verb combinations. Never quote as a limitation |
| **Rejected** | The verb was explicitly refused, with the code | A finding. `405` = read-only at any permission level |

## Dates

| Source | Date | Note |
|---|---|---|
| Endpoint corpus (166 endpoints, 830 combinations, 11 MCP actions) | 2026-07-25 | Two orgs, two pods |
| Org A live probe + connector creation | 2026-07-26 | Agent install, `TOOLKIT_CCI`, three connections |
| Org B tracker lessons | **2026-07-08 export** | Board decisions after that date are not in it |
| Vendor MCP guide | April 2026 | Protocol `2025-06-18` |

**Live verdicts in this corpus flipped on a three-to-five-day cadence.** Re-probe anything you are
about to promise a customer.

## How much of this has been tested on agents

Two different things are verified, and they are worth keeping apart.

**Internal consistency — proven.** The skill's counts are cross-footed against the CSV corpus at build
time, so the numbers cannot drift from the dictionary or the master document.

**Agent behaviour — tested 2026-07-26, 7 subagent runs.** Four adversarial scenarios (borrowed
cross-org endpoint under time pressure · 13 failed connector spellings → "file a licensing ticket" ·
two zero-byte 200s → "add them as WORKS to the deck" · `products[]` + a blank verb cell → "approve this
customer email"). Result: **every run refused the wrong answer**, including the control runs with the
skill withheld — agents pointed at this knowledge base reach the right verdict without the skill.

So the measured failure was never correctness. It was **retrieval cost**: right answers took 20–50 tool
calls and up to 34 files, because per-service hosts, caps and corrections lived only in `content/*.json`
with no route from the skill. `knowledge/playbook/08-answers-planes-caps-corrections.md` and the SKILL.md
per-service table exist to collapse that, and are generated so they cannot drift.

**Still untested:** whether those additions actually cut the tool-call count, and whether an agent with
**no** pointer to this KB (the true cold-start case) complies. One test run also read `skill_src/` prose
directly — when withholding the skill, bar `skill/`, `skill_src/` and `.claude/skills/` explicitly.
