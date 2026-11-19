# AGENTS.md — How Multiple Agents Improve This KB

> This file is the **contract** for any AI agent (or person) asked to *improve*,
> *update*, *fact-check*, or *extend* the **IICS to IPUs KB**. Read it fully before
> touching anything. Following it is what keeps the KB accurate, shareable, and
> mergeable when several agents work on it over time.

---

## 1. What this KB is

A **customer-facing** knowledge base explaining, end to end, the transition from
**legacy Informatica IICS licensing** (per-service subscriptions with fixed tiers and
connector entitlements) to the modern **IDMC IPU consumption model** (one flexible pool
of Informatica Processing Units spendable across the whole portfolio) — covering **both**
the licensing/commercial change **and** the product/capability differences.

Audience: **customers and the account teams who serve them.** Everything here must be
safe to share externally.

---

## 2. File map & source of truth

```
iics-to-ipus-kb/
├─ start-here.md      ← orientation + reading order (read first)
├─ README.md          ← sourcing governance + freshness policy
├─ AGENTS.md          ← THIS FILE: the improvement protocol
├─ CHANGELOG.md       ← every change logged, newest first
├─ build/
│   ├─ build_kb.py    ← joins sections/ into iics-to-ipus-knowledge-base.md (stdlib, Python 3.10+)
│   └─ build_pdf.py   ← renders that file to iics-to-ipus-knowledge-base.pdf (third-party packages)
├─ sections/          ← the MODULAR SOURCE OF TRUTH (edit here)
│   ├─ 00-executive-summary.md
│   ├─ 01-history-iics-to-idmc.md
│   ├─ 02-legacy-licensing-model.md
│   ├─ 03-ipu-consumption-model.md
│   ├─ 04-ipu-metering-by-service.md
│   ├─ 05-what-iics-locks-out.md
│   ├─ 06-what-ipus-unlock.md
│   ├─ 07-side-by-side-matrix.md
│   ├─ 08-migration-and-conversion.md
│   ├─ 09-commercial-model.md
│   ├─ 10-why-move-why-stay.md
│   ├─ 11-faq-objections.md
│   └─ 12-glossary.md
└─ sources/
    └─ SOURCES.md     ← the merged, canonical citation registry
```

**Golden rule of source of truth:** `sections/*.md` are the source of truth and what readers open.
The single-file `iics-to-ipus-knowledge-base.md` and its PDF are *built* on demand from the sections
and are not committed; never hand-edit them.

---

## 3. The improvement loop (do these in order)

1. **Claim your work.** Add a `CHANGELOG.md` entry at the top marked `IN PROGRESS`
   naming the file(s) you will touch and your agent label. This prevents two agents
   colliding on the same file.
2. **Read before writing.** Read the target section AND `sources/SOURCES.md` so you
   build on what exists instead of duplicating or contradicting it.
3. **Research with live sources.** Use web tools against **authoritative Informatica
   sources** (`informatica.com`, `docs.informatica.com`, `knowledge.informatica.com`,
   official pricing pages). Prefer primary sources over blogs.
4. **Improve.** Fix inaccuracies, deepen thin spots, refresh stale facts, tighten
   writing, add examples. Keep the customer-facing tone.
5. **Cite.** Every specific or non-obvious claim gets a citation. Update the section's
   own `## Sources` block AND, if several agents are working at once, append to your own
   scratch list `sources/_agent<yourlabel>-sources.md` (never edit another agent's) for the
   integrator to fold into `SOURCES.md`; working alone, add to `SOURCES.md` directly.
6. **Log it.** Flip your `CHANGELOG.md` entry from `IN PROGRESS` to `DONE`, dated, with
   a one-line summary of what changed and why.
7. **Flag integration.** If you added a section or left per-agent source lists behind, note
   `NEEDS RE-INTEGRATION` in your changelog entry so the next integrator folds them in.

---

## 4. Non-negotiable quality rules

- **Cite every non-obvious claim.** No citation → not in the KB.
- **Never fabricate specifics.** Do not invent per-IPU dollar prices, exact metering
  multipliers, or discount percentages. If a specific figure can't be verified from a
  source, describe the concept qualitatively and mark it **`[verify]`**.
- **Keep it shareable.** NO discount schedules, price lists, deal-specific pricing, or
  confidential contract mechanics in any file. When in doubt, leave it out.
- **Date your facts.** Informatica changes pricing, metering, and packaging. When you
  cite a rate or capability, note the date/source version so freshness is auditable.
- **Match the house style.** Clean GitHub-flavored Markdown, clear H2/H3, tables for
  comparisons, bold key terms, short paragraphs.
- **Don't duplicate across sections.** Section 5 (locked out) and Section 6 (unlocked)
  are complements, not copies. Cross-reference instead of repeating.

---

## 5. Roles an improving agent can take

Pick one per pass and say which in your changelog entry:

| Role | What it does |
|---|---|
| **Fact-checker** | Verifies existing claims against live Informatica sources; fixes or flags `[verify]` items. |
| **Depth-expander** | Adds missing detail, examples, or an under-covered service/scenario. |
| **Freshness-updater** | Re-checks pricing/metering/packaging that may have changed; updates dates. |
| **Editor** | Improves clarity, consistency, and cross-references without changing facts. |
| **Integrator** | Merges `_agent*-sources.md` into `SOURCES.md`, checks the build, and produces the single-file or PDF version when one is asked for. |

---

## 6. How to re-integrate the main KB (Integrator role)

The integration is **scripted and reproducible**; do not hand-assemble a single-file version.

1. Make sure no section edit is still `IN PROGRESS` in `CHANGELOG.md`.
2. From `knowledge/12-reference-library/iics-to-ipus-kb`, run `python3 build/build_kb.py`
   (Python 3.10+, standard library only). It reads `sections/00…12` in order, strips each file's
   trailing `## Sources` block, demotes headings so the output has a single H1, rewrites
   `NN-*.md` cross-references into in-document `#anchors`, adds a table of contents and writes
   `iics-to-ipus-knowledge-base.md`. It is idempotent and prints a summary (sections integrated,
   size, `[verify]` count). The output is generated; do not commit it.
3. If you added a section file, add its filename to `SECTION_FILES` in `build/build_kb.py`.
4. Keep `sources/SOURCES.md` current by hand (it is the *curated, canonical* registry, not an
   auto-merge): fold in any new URLs from `sources/_agent*-sources.md`, de-duplicated, one dated
   line per source, update the standing `[verify]` list, then delete the merged scratch lists.
5. For a shareable PDF, run `python3 build/build_pdf.py` after `build_kb.py`. It needs
   `pip install markdown pymdown-extensions playwright` and the browser channel named in the script
   (msedge). It reads only the generated `.md` and writes `iics-to-ipus-knowledge-base.pdf`, which
   is not committed either.
6. Add a `CHANGELOG.md` entry, dated, and run `python3 toolkit/tools/secret_scan.py .` from the repo
   root (must print CLEAN).

---

## 7. Conflict avoidance (multiple agents at once)

- **One agent per section file at a time.** The `CHANGELOG.md` `IN PROGRESS` claim is
  how you reserve it. Check the changelog before you start.
- **Never edit another agent's `_agent*-sources.md`.** Use your own.
- The integrator is the *only* role that edits `sources/SOURCES.md` wholesale, and only when no
  section edits are `IN PROGRESS`.
