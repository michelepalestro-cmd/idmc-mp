# Lessons Learned

> **Summary.** Every lesson this KB rests on: **2,039 lessons** in 14 domain files, each with a stable id
> (`L-<DOM>-<NNN>`), a kind, a date, the evidence that proved it and one to six sentences of generic, placeholder-only
> text. 1,834 are current, 182 are superseded (kept so nobody re-learns them) and 23 are disputed. The topic docs cite
> these ids; [Overturned Beliefs](overturned-beliefs.md) lists every belief that fell and what replaced it.

Last verified: 2026-11-18, against lessons.jsonl (evidence dates 2026-06-27 to 2026-11-13 across all files).

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
| [01 Access & Auth](by-domain/01-access-auth.md) | `AUTH` | 98 | 86 | 11 | 1 | 2026-06-27 to 2026-11-10 |
| [02 Secure Agent & Connections](by-domain/02-secure-agent-connections.md) | `AGENT` (123), `CONN` (141) | 264 | 238 | 23 | 3 | 2026-06-27 to 2026-11-05 |
| [03 Data Integration (CDI)](by-domain/03-data-integration-cdi.md) | `CDI` | 305 | 281 | 21 | 3 | 2026-06-27 to 2026-11-12 |
| [04 Mass Ingestion & CDC](by-domain/04-mass-ingestion-cdc.md) | `DBMI` | 64 | 58 | 5 | 1 | 2026-07-04 to 2026-11-02 |
| [05 Application Integration (CAI)](by-domain/05-application-integration-cai.md) | `CAI` | 163 | 146 | 16 | 1 | 2026-07-01 to 2026-11-01 |
| [06 Data Quality & Profiling](by-domain/06-data-quality-profiling.md) | `DQ` | 163 | 145 | 14 | 4 | 2026-06-27 to 2026-11-12 |
| [07 Catalog & Governance (CDGC)](by-domain/07-catalog-governance-cdgc.md) | `CDGC` | 226 | 198 | 26 | 2 | 2026-06-27 to 2026-11-01 |
| [08 MDM](by-domain/08-mdm.md) | `MDM` | 90 | 77 | 11 | 2 | 2026-07-04 to 2026-11-12 |
| [09 CLAIRE & MCP](by-domain/09-claire-mcp.md) | `MCP` | 131 | 115 | 14 | 2 | 2026-07-04 to 2026-11-13 |
| [10 Migration & Org Management](by-domain/10-migration-org-management.md) | `MIG` (100), `CLEAN` (36) | 136 | 118 | 17 | 1 | 2026-07-04 to 2026-11-02 |
| [11 IPU, Metering & Licensing](by-domain/11-ipu-metering-licensing.md) | `IPU` | 60 | 51 | 7 | 2 | 2026-06-28 to 2026-11-12 |
| [12 Claude Working Methods](by-domain/12-claude-working-methods.md) | `METHOD` | 160 | 152 (14 general) | 8 | 0 | 2026-07-04 to 2026-11-13 |
| [13 Environment & Ops](by-domain/13-environment-ops.md) | `ENV` | 139 | 136 (26 general) | 3 | 0 | 2026-07-04 to 2026-11-12 |
| [14 UI Automation](by-domain/14-ui-automation.md) | `UI` | 37 | 30 | 6 | 1 | 2026-07-06 to 2026-10-26 |
| **Total** | 16 prefixes | **1,763** | **1,563** | **181** | **19** | 2026-06-27 to 2026-10-26 |

A machine-readable copy of the same lessons, one JSON object per line, is [lessons.jsonl](lessons.jsonl) in this
folder, with the fields `id`, `domain`, `kind`, `title`, `text`, `evidence`, `date`, `status` and `supersedes_id`
(1,665 lines, the same ids as the headings). For a current or disputed lesson every field equals its heading, meta line and body (`text` is the body with its lines joined by spaces); for a superseded lesson `text` is the body followed by 'Was believed <dates>; overturned by <id>.', and `kind`, `evidence` and `date` keep the values the belief had.

## 3. Kinds

| Kind | Means | Count |
|---|---|---|
| `GOTCHA` | a trap: something that looks like one thing and is another | 563 |
| `RECIPE` | a proven multi-step procedure | 228 |
| `LAW` | a rule that holds across orgs and changes outcomes | 137 |
| `WALL` | something that is not headless, dated (many walls are superseded) | 132 |
| `PROCESS` | an end-to-end way of working | 136 |
| `OVERTURNED` | the newer lesson that replaced an older belief; its partner is a superseded lesson | 125 |
| `ROUTE` | an exact verb, host, path, headers and body with the success signal and read-back | 111 |
| `ERROR` | an error signature and what it really means | 56 |
| `DECISION` | a choice made, with its reasons | 41 |
| `PERF` | a measured performance fact | 44 |
| `SECURITY` | a rule about secrets, access or exposure | 41 |
| `WORKAROUND` | a way around a wall | 17 |
| `PATTERN`, `WORKS`, `FACT`, `PROBE`, `FIX` | kinds used by lessons added after the rebuild (a reusable pattern, a confirmed working path, a fact, a probe result, a fix) | 20, 3, 4, 1, 1 |

## 4. Status values

| Status | Means | Where it sits |
|---|---|---|
| `current` | the latest dated evidence: use it | the `## Current` section |
| `superseded` | an older belief kept so nobody re-learns it; it names the lesson that overturned it and the dates it was held | the `## Superseded / overturned` section, and a row in [Overturned Beliefs](overturned-beliefs.md) |
| `disputed` | dated records disagree; the text says which reading to trust, or that neither is safe | `## Current` (flagged in the meta line), or `## Disputed` in `03` |

## 5. Id prefixes

| Prefix | Domain key | File |
|---|---|---|
| `AUTH` | `auth` | 0 |
| `AGENT`, `CONN` | `agent`, `connections` | 02 |
| `CDI` | `cdi` | 0 |
| `DBMI` | `dbmi-cdc` | 0 |
| `CAI` | `cai` | 0 |
| `DQ` | `dq-profiling` | 0 |
| `CDGC` | `cdgc` | 0 |
| `MDM` | `mdm` | 0 |
| `MCP` | `claire-mcp` | 0 |
| `MIG`, `CLEAN` | `migration`, `org-cleanup` | 10 |
| `IPU` | `ipu-licensing` | 0 |
| `METHOD` | `claude-method` | 0 |
| `ENV` | `environment-ops` | 0 |
| `UI` | `ui-automation` | 0 |

Ids are stable. At the rebuild, the current lessons of each prefix were numbered first and its superseded beliefs
last (for example `L-AUTH-077` to `L-AUTH-087`). A lesson added later takes the next free number of its prefix, so from
now on a high number can be either a new lesson or an old belief: read its status, not its number. An id is never
reused or renumbered. A lesson withdrawn from this shared KB (for example one that was only about internal
pricing) leaves a gap in its prefix; its id stays retired.

## 6. How to add a lesson

1. **Search first.** Grep this folder for the path, the error code or the key phrase: the lesson may exist, perhaps as
   a superseded belief that your evidence brings back.
2. **Pick the file and the prefix**, and take the next free number for that prefix (for example the next `L-CDI-`
   after the highest one in `03`).
3. **Write it** in the `## Current` section, under the subject it belongs to, in the shape shown in section 1: a short
   declarative title, the kind, the date it was proven, the evidence (an HTTP code, a read-back, a count or a measured
   time), and generic text with placeholders (`<pod>`, `<domain>`, `<orgIdV3>`, `<reId>`, `<connId>`, `<taskId>`).
   Keep numbers, drop names: no customer, app, person, org, id, host or tracker key belongs here.
4. **Keep the evidence state honest:** "proven <date>", "documented", "rejected (<code>)" or "untested". Never upgrade
   a documented claim to proven.
5. **If it overturns an older lesson,** give the new lesson the kind `OVERTURNED`; move the old one to the
   `## Superseded / overturned` section with `**Was believed:** <date range> · **Overturned by:** <new id>` and
   ", overturned <date>" on its heading; add a row to [Overturned Beliefs](overturned-beliefs.md); then fix the topic
   doc (its text and its overturned-beliefs table) and, if they are affected, the
   [Capability Map](../knowledge/00-start-here/03-capability-map.md) and the
   [Laws](../knowledge/00-start-here/02-the-laws-of-headless-idmc.md).
6. **Update the counts** in the file's summary line and in the table in section 2.
7. **Add the JSON line** to `lessons.jsonl` with the same id, and record its raw sources in the provenance file
   kept outside this KB.
8. **Run the zone gate** on the KB root; it must print CLEAN.

A superseded entry looks like this:

```
### L-CDI-190  Swapping a mapping's target connection to another warehouse later is a quick change, overturned 2026-07-04
**Was believed:** 2026-06-27 (a plan) · **Overturned by:** L-CDI-050, L-CDI-031
Cross-connector retargets of tasks silently reverted, and target changes on tasks over real mappings are no-ops.
Retargeting means changing the mapping.
```
