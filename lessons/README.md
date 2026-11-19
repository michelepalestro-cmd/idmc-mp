# Lessons Learned

> **Summary.** Every lesson this KB rests on: **2,340 lessons** in 14 domain files, each with a stable id
> (`L-<DOM>-<NNN>`), a kind, a date, the evidence that proved it and one to six sentences of generic, placeholder-only
> text. 2,135 are current, 182 are superseded (kept so nobody re-learns them) and 23 are disputed. The topic docs cite
> these ids; [Overturned Beliefs](overturned-beliefs.md) lists every belief that fell and what replaced it.

Last verified: 2026-11-19, against lessons.jsonl (evidence dates 2026-06-27 to 2026-11-19 across all files).

Related: [How to use this KB](../knowledge/00-start-here/01-how-to-use-this-kb.md) ·
[Overturned Beliefs](overturned-beliefs.md) · [The Laws of Headless IDMC](../knowledge/00-start-here/02-the-laws-of-headless-idmc.md) ·
[Capability Map](../knowledge/00-start-here/03-capability-map.md) · [Changelog](../knowledge/00-start-here/06-changelog.md)

---

## 1. How the lessons are organized

- **One file per domain group**, numbered `01`–`14` in the same order as the topic folders; `12`, `13` and `14` split the
  working-methods folder into methods, environment and UI automation.
- **Inside each file:**
  - a summary line with the counts and the evidence range, a topic line that says which id ranges cover which subject,
    and links to the topic docs;
  - `## Current`: the lessons to use, grouped by subject. Disputed lessons sit here too, flagged in their meta line
    (`03 Data Integration (CDI)` keeps its three in a separate `## Disputed` section);
  - `## Superseded / overturned (kept so nobody re-learns them)`: every older belief, each with the date range it was
    held and the lesson that overturned it;
  - in `12` and `13` only, `## Other general lessons (not IDMC-specific)`: current lessons about QA suites, BI tools and dashboards fed by IDMC, API
    gateways, Office files and app platforms that came out of the same work (14 and 24 lessons).
- **Each lesson** has this shape:

```
### L-CDI-050  Silent no-op: a target-parameter POST returns 200 but the task keeps its mapping's targets
**Kind:** GOTCHA · **Proven:** 2026-09-29 · **Evidence:** <HTTP code / read-back / count / measured time>
<one to six sentences: the exact verb, host pattern, path, headers, body shape, error codes and read-back>
```

- **A superseded lesson** replaces the meta line with `**Was believed:** <date range> · **Overturned by:** <id>`, and
  its heading ends with ", overturned <date>".
- **Provenance** (which tracker issues, memory files or documents proved each lesson) is kept outside this KB.
  These files carry only generic text.

## 2. The files and their counts

Counts are the `### L-` headings in each file.

| File | Id prefixes | Lessons | Current | Superseded | Disputed | Evidence dates |
|---|---|---|---|---|---|---|
| [01 Access & Auth](by-domain/01-access-auth.md) | `AUTH` | 136 | 124 | 11 | 1 | 2026-06-27 to 2026-11-19 |
| [02 Secure Agent & Connections](by-domain/02-secure-agent-connections.md) | `AGENT` (142), `CONN` (152) | 294 | 268 | 23 | 3 | 2026-06-27 to 2026-11-19 |
| [03 Data Integration (CDI)](by-domain/03-data-integration-cdi.md) | `CDI` | 330 | 306 | 21 | 3 | 2026-06-27 to 2026-11-19 |
| [04 Mass Ingestion & CDC](by-domain/04-mass-ingestion-cdc.md) | `DBMI` | 71 | 65 | 5 | 1 | 2026-07-04 to 2026-11-19 |
| [05 Application Integration (CAI)](by-domain/05-application-integration-cai.md) | `CAI` | 214 | 197 | 16 | 1 | 2026-07-01 to 2026-11-19 |
| [06 Data Quality & Profiling](by-domain/06-data-quality-profiling.md) | `DQ` | 172 | 154 | 14 | 4 | 2026-06-27 to 2026-11-19 |
| [07 Catalog & Governance (CDGC)](by-domain/07-catalog-governance-cdgc.md) | `CDGC` | 266 | 238 | 26 | 2 | 2026-06-27 to 2026-11-19 |
| [08 MDM](by-domain/08-mdm.md) | `MDM` | 120 | 107 | 11 | 2 | 2026-07-04 to 2026-11-19 |
| [09 CLAIRE & MCP](by-domain/09-claire-mcp.md) | `MCP` | 149 | 133 | 14 | 2 | 2026-07-04 to 2026-11-19 |
| [10 Migration & Org Management](by-domain/10-migration-org-management.md) | `CLEAN` (37), `MIG` (131) | 168 | 150 | 17 | 1 | 2026-07-04 to 2026-11-19 |
| [11 IPU, Metering & Licensing](by-domain/11-ipu-metering-licensing.md) | `IPU` | 68 | 59 | 7 | 2 | 2026-06-28 to 2026-11-19 |
| [12 Claude Working Methods](by-domain/12-claude-working-methods.md) | `METHOD` | 171 | 163 (14 general) | 8 | 0 | 2026-07-04 to 2026-11-19 |
| [13 Environment & Ops](by-domain/13-environment-ops.md) | `ENV` | 144 | 141 (26 general) | 3 | 0 | 2026-07-04 to 2026-11-19 |
| [14 UI Automation](by-domain/14-ui-automation.md) | `UI` | 37 | 30 | 6 | 1 | 2026-07-06 to 2026-10-26 |
| **Total** | 16 prefixes | **2,340** | **2,135** | **182** | **23** | 2026-06-27 to 2026-11-19 |

The source of truth is [lessons.jsonl](lessons.jsonl), one JSON object per line, in this folder; the `by-domain/` files
are the readable view. Each line has the fields `id`, `domain`, `kind`, `title`, `text`, `evidence`, `date`, `status` and `supersedes_id`
(one line per lesson, the same ids as the headings). For a current or disputed lesson every field equals its heading, meta line and body (`text` is the body with its lines joined by spaces); for a superseded lesson `text` is the body followed by 'Was believed <dates>; overturned by <id>.', and `kind`, `evidence` and `date` keep the values the belief had.

## 3. Kinds

| Kind | Means | Count |
|---|---|---|
| `GOTCHA` | a trap: something that looks like one thing and is another | 805 |
| `RECIPE` | a proven multi-step procedure | 320 |
| `ROUTE` | an exact verb, host, path, headers and body with the success signal and read-back | 209 |
| `PROCESS` | an end-to-end way of working | 158 |
| `WALL` | something that is not headless, dated (many walls are superseded) | 142 |
| `LAW` | a rule that holds across orgs and changes outcomes | 141 |
| `OVERTURNED` | the newer lesson that replaced an older belief; its partner is a superseded lesson | 130 |
| `FACT` | a fact worth knowing, with its source | 96 |
| `PATTERN` | a reusable way to do something | 79 |
| `ERROR` | an error signature and what it really means | 77 |
| `PERF` | a measured performance fact | 58 |
| `SECURITY` | a rule about secrets, access or exposure | 54 |
| `DECISION` | a choice made, with its reasons | 45 |
| `WORKAROUND` | a way around a wall | 18 |
| `WORKS`, `FIX`, `LIMIT`, `PROBE`, `TRIAGE` | rarer kinds | 4, 1, 1, 1, 1 |

## 4. Status values

| Status | Means | Where it sits |
|---|---|---|
| `current` | the latest dated evidence: use it | the `## Current` section |
| `superseded` | an older belief kept so nobody re-learns it; it names the lesson that overturned it and the dates it was held | the `## Superseded / overturned` section, and a row in [Overturned Beliefs](overturned-beliefs.md) |
| `disputed` | dated records disagree; the text says which reading to trust, or that neither is safe | `## Current` (flagged in the meta line), or `## Disputed` in `03` |

## 5. Id prefixes

| Prefix | Domain key | File |
|---|---|---|
| `AUTH` | `auth` | [01-access-auth.md](by-domain/01-access-auth.md) |
| `AGENT`, `CONN` | `agent`, `connections` | [02-secure-agent-connections.md](by-domain/02-secure-agent-connections.md) |
| `CDI` | `cdi` | [03-data-integration-cdi.md](by-domain/03-data-integration-cdi.md) |
| `DBMI` | `dbmi-cdc` | [04-mass-ingestion-cdc.md](by-domain/04-mass-ingestion-cdc.md) |
| `CAI` | `cai` | [05-application-integration-cai.md](by-domain/05-application-integration-cai.md) |
| `DQ` | `dq-profiling` | [06-data-quality-profiling.md](by-domain/06-data-quality-profiling.md) |
| `CDGC` | `cdgc` | [07-catalog-governance-cdgc.md](by-domain/07-catalog-governance-cdgc.md) |
| `MDM` | `mdm` | [08-mdm.md](by-domain/08-mdm.md) |
| `MCP` | `claire-mcp` | [09-claire-mcp.md](by-domain/09-claire-mcp.md) |
| `CLEAN`, `MIG` | `migration`, `org-cleanup` | [10-migration-org-management.md](by-domain/10-migration-org-management.md) |
| `IPU` | `ipu-licensing` | [11-ipu-metering-licensing.md](by-domain/11-ipu-metering-licensing.md) |
| `METHOD` | `claude-method` | [12-claude-working-methods.md](by-domain/12-claude-working-methods.md) |
| `ENV` | `environment-ops` | [13-environment-ops.md](by-domain/13-environment-ops.md) |
| `UI` | `ui-automation` | [14-ui-automation.md](by-domain/14-ui-automation.md) |

Ids are stable. At the rebuild, the current lessons of each prefix were numbered first and its superseded beliefs
last (for example `L-AUTH-077` to `L-AUTH-087`). A lesson added later takes the next free number of its prefix, so from
now on a high number can be either a new lesson or an old belief: read its status, not its number. An id is never
reused or renumbered. A lesson withdrawn from this shared KB (for example one that was only about internal
pricing) leaves a gap in its prefix; its id stays retired.

## 6. How to add a lesson

Follow [CONTRIBUTING.md](../CONTRIBUTING.md). In short: search first; add the lesson to `lessons.jsonl` and to its
`by-domain/` file under `## Current`, with the next free id of its prefix; keep evidence states honest (proven, documented,
reported, rejected, untested) and never upgrade one; for an overturned belief use the kind `OVERTURNED` and move the old
lesson to `## Superseded / overturned` with a row in [Overturned Beliefs](overturned-beliefs.md). Then run
`python3 toolkit/tools/sync_lesson_counts.py` (rebuilds every count in this folder), `python3 toolkit/tools/build_skill_field_lessons.py`,
`python3 tests/run_tests.py` and `python3 toolkit/tools/secret_scan.py`.

