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
IICS to IPUs KB\
├─ START HERE.md      ← orientation + reading order (read first)
├─ README.md          ← sourcing governance + freshness policy
├─ AGENTS.md          ← THIS FILE — the improvement protocol
├─ CHANGELOG.md       ← every change logged, newest first
├─ IICS to IPUs — Knowledge Base.md   ← the INTEGRATED, readable deliverable (GENERATED)
├─ build\
│   └─ build_kb.py    ← rebuilds the integrated deliverable from sections\ (Integrator tool)
├─ sections\          ← the MODULAR SOURCE OF TRUTH (edit here)
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
└─ sources\
    ├─ SOURCES.md          ← the merged, canonical citation registry
    └─ _agentN-sources.md  ← per-agent scratch citation lists (merge-safe)
```

**Golden rule of source of truth:** `sections\*.md` are the source of truth. The
top-level **`IICS to IPUs — Knowledge Base.md`** is a *built* artifact — an integration of
the sections plus connective tissue (exec summary, matrix, glossary). **Edit sections;
then re-integrate.** Never hand-edit the integrated file with content that isn't
reflected in a section — it will be overwritten on the next integration.

---

## 3. The improvement loop (do these in order)

1. **Claim your work.** Add a `CHANGELOG.md` entry at the top marked `IN PROGRESS`
   naming the file(s) you will touch and your agent label. This prevents two agents
   colliding on the same file.
2. **Read before writing.** Read the target section AND `sources\SOURCES.md` so you
   build on what exists instead of duplicating or contradicting it.
3. **Research with live sources.** Use web tools against **authoritative Informatica
   sources** (`informatica.com`, `docs.informatica.com`, `knowledge.informatica.com`,
   official pricing pages). Prefer primary sources over blogs.
4. **Improve.** Fix inaccuracies, deepen thin spots, refresh stale facts, tighten
   writing, add examples. Keep the customer-facing tone.
5. **Cite.** Every specific or non-obvious claim gets a citation. Update the section's
   own `## Sources` block AND append to `sources\_agent<yourlabel>-sources.md`
   (your own file — never edit another agent's `_agent*-sources.md`).
6. **Log it.** Flip your `CHANGELOG.md` entry from `IN PROGRESS` to `DONE`, dated, with
   a one-line summary of what changed and why.
7. **Flag integration.** If your change alters content that appears in the integrated
   `IICS to IPUs — Knowledge Base.md`, note `NEEDS RE-INTEGRATION` in your changelog
   entry so the next integrator rebuilds it.

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
| **Integrator** | Rebuilds `IICS to IPUs — Knowledge Base.md` from the sections and merges `_agent*-sources.md` into `SOURCES.md`. |

---

## 6. How to re-integrate the main KB (Integrator role)

The integration is **scripted and reproducible** — do not hand-assemble the deliverable.

1. Make sure no section edit is still `IN PROGRESS` in `CHANGELOG.md`.
2. Run the build:
   ```
   python build/build_kb.py
   ```
   It reads `sections\00…11` in order, strips each file's trailing `## Sources` block,
   demotes headings so the deliverable has a single H1, rewrites `(./NN-*.md)`
   cross-references into in-document `#anchors`, and regenerates a table of contents and
   the `Sources & References` pointer. It is idempotent and prints a summary (sections
   integrated, size, `[verify]` count).
3. If you added a section file, add its filename to `SECTION_FILES` in `build/build_kb.py`.
4. Keep `sources\SOURCES.md` current by hand (it is the *curated, canonical* registry, not
   an auto-merge): fold any new URLs from `sources\_agent*-sources.md` in, de-duplicated,
   one dated line per source, and update the standing `[verify]` list.
5. Add a `CHANGELOG.md` entry: `Re-integrated main KB from sections` (or
   `Regenerated deliverable via build_kb.py`), dated.
6. **Regenerate the PDF** (the shareable deliverable): `python build/build_pdf.py`. It renders
   `IICS to IPUs — Knowledge Base.md` → `IICS to IPUs — Knowledge Base.pdf` (Markdown→HTML→PDF
   via Playwright/msedge; requires `pip install markdown pymdown-extensions playwright`). It
   reads ONLY the generated `.md` (built from `sections\`). Re-run after `build_kb.py`.

---

## 7. Conflict avoidance (multiple agents at once)

- **One agent per section file at a time.** The `CHANGELOG.md` `IN PROGRESS` claim is
  how you reserve it. Check the changelog before you start.
- **Never edit another agent's `_agent*-sources.md`.** Use your own.
- The integrator is the *only* role that edits `IICS to IPUs — Knowledge Base.md` and
  `sources\SOURCES.md`, and only when no section edits are `IN PROGRESS`.
