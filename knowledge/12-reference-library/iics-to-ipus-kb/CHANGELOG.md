# CHANGELOG — IICS to IPUs KB

Newest first. Every improvement gets an entry. Agents: see [`AGENTS.md`](AGENTS.md)
for how to claim work (`IN PROGRESS`) and log it (`DONE`), and when to flag
`NEEDS RE-INTEGRATION`.

Entry format:
```
## YYYY-MM-DD — <role> — <status: IN PROGRESS | DONE | NEEDS RE-INTEGRATION>
- <agent/author label>: <what changed and why>
- Files: <files touched>
```

---

## 2026-10-03 — Editor — DONE (share sanitization)
- Removed the internal pricing and deal-notes material and the internal capability-comparison workbook
  from the KB (they are kept outside the shared KB) and every reference to them; reworded the
  shareable-guardrail lines; turned the §8.3 worked sizing example into an illustrative one (rounded,
  not any one customer's figures). Regenerated the `.md` with `build_kb.py` and the `.pdf` with
  `build_pdf.py`.
- Files: `README.md`, `start-here.md`, `AGENTS.md`, this changelog, `sources/SOURCES.md`,
  `sections/00, 07, 08, 09`, `build/build_pdf.py` (docstring), generated `.md` + `.pdf`.

## 2026-09-29 — Editor — DONE (de-identification for the generic Reference Library)
- Moved with the Master IDMC KB rebuild into `knowledge/12-reference-library\IICS-to-IPUs KB\`, the KB's
  generic, org-agnostic zone. Removed person and session names from this changelog (the session label
  is now `S-33`) and replaced customer names in the internal working files with neutral labels. No
  section, generated `.md` or `.pdf` changed; the PDF text was checked and already names no customer
  or person.
- Files: this changelog and the internal working files (since removed from the KB).

## 2026-09-03 — Fact-checker/Integrator — DONE (PDF freshness verify + §2 connector residual)
- Verified the master **PDF is fully up to date**: snapshotted the `.md`, re-ran `build_kb.py`
  (rebuild came out **byte-identical** → `.md` already reflected `sections/`), then regenerated
  the PDF via `build_pdf.py`. Confirmed mtime ordering sections ≤ `.md` ≤ `.pdf` (456 KB).
- Fixed **one residual connector conflation** the prior sweep missed: **§2** "How this sets up
  the move to IPUs" table said connectors were accessed "through the same pool" → corrected to
  connectors = separate **tier-based** subscription (Tier A incl; B/C/D per End Point; **not**
  IPU-metered); only the *services* draw from the pool *(CPDS v39.1, pp. 7, 28)*.
- Re-verified: 13 sections, TOC + anchors clean, **11 `[verify]`**, no line describes connectors
  as drawn/funded from the IPU pool, **0 leakage** (prices, discount schedules, customer names).
- Files: `sections/02`, generated master `.md` + `.pdf`, this changelog.

## 2026-09-03 — Fact-checker (session S-33) — DONE (connector-in-pool sweep, from the KB owner's fact-check)
- Swept the whole deliverable for the recurring **connectors-draw-from-the-IPU-pool** error
  (per the KB owner's fact-check point #1). Found and fixed **two residual conflations** the earlier
  correction missed: **§6** summary table ("Connectivity … you draw on from the shared pool
  `[verify]`") and **§11** FAQ Q7 ("connectors … now consume from the IPU pool"). Both rewritten
  to the confirmed CPDS v39.1 (pp. 7, 28) fact: connectors are a separate **tier-based
  subscription** (Tier A included; B/C/D per End Point), **not** IPU-metered; the *services*
  that use them draw from the pool. Resolved the stray `[verify]` on the §6 line.
- Re-verified the other five fact-check items are already correctly stated: CLAIRE ~90% is
  labeled a vendor-published estimate (§6, §7); MDM is "per-domain records basis, not metered
  against IPUs" (§3/§4.9/§6/§7); FedRAMP stays `[verify]`/"validate per service"; "licensing
  change, not a re-platform" is stated as confirmed (§8.1); "burst"/"one pool" flagged as
  informal paraphrases (§7 notes).
- Rebuilt via `build_kb.py` (13 sections, 1,636 lines, **11 `[verify]`**) and regenerated the
  PDF via `build_pdf.py` (454 KB). Final grep confirms no line describes connectors as
  consuming/drawing/funded-from the IPU pool.
- Files: `sections/06`, `sections/11`, generated master `.md` + `.pdf`, this changelog.

## 2026-09-03 — Integrator (session S-33) — DONE (PDF deliverable)
- Added `build/build_pdf.py` and rendered **`IICS to IPUs — Knowledge Base.pdf`** (~53 pages,
  ~442 KB) from the generated master `.md` — Markdown→HTML (tables, fenced code, GitHub-style
  anchors so the Contents links resolve)→PDF via Playwright/msedge. Clean print style: Arial,
  Informatica blue (no orange), zebra tables, per-section page breaks, footer page numbers.
- Shareability: renders ONLY the generated deliverable (built from `sections/`), so nothing outside
  `sections/` can reach the PDF. Visually verified cover + comparison matrix.
- Files: `build/build_pdf.py`, `IICS to IPUs — Knowledge Base.pdf`, this changelog.

## 2026-09-03 — Depth-expander — DONE (why-move-vs-why-stay decision section)
- Added **§10 "Should You Move to IPUs? Reasons to Move vs. Reasons to Wait"** — a balanced,
  honest decision guide: 9 reasons to move (access/agility/elasticity/AI/procurement/FinOps/
  utility-modeling/future-proofing/compliance), 7 reasons to wait (stable-narrow usage/
  fixed-budget preference/no-FinOps-owner-yet/contract timing/not-yet-baselined/variable-spend
  aversion/favorable legacy entitlements), plus a "lean toward MOVING vs WAITING" decision table.
  Honesty-labeled: move = agility/access/efficiency; stay = predictability/governance/timing,
  and "wait" = usually "wait until renewal," not "never."
- Renumbered downstream: **FAQ 10→11, Glossary 11→12** (files renamed + H1s bumped +
  `build_kb.py` SECTION_FILES + exec-summary outline + AGENTS.md file map + START HERE updated).
- Rebuilt via `build_kb.py`: **13 sections, 1,636 lines, 12 `[verify]`**; TOC + all in-doc
  anchors verified (0 missing). Regenerated PDF (454 KB). No internal leakage (new section adds
  no $/IPU, discount, or customer-identifiable content).
- Files: new `sections/10-why-move-why-stay.md`; renamed `sections/11,12`; `build/build_kb.py`;
  `sections/00`; `AGENTS.md`; `start-here.md`; generated master `.md` + `.pdf`; this changelog.

## 2026-09-03 — Integrator (session S-33) — DONE (best-of-both merge; consolidated to one master)
- Final consolidation per the KB owner's instruction: this folder is now the **single master KB**.
  Folded in the unique content from a parallel `IICS to IPUs\` draft folder (built by
  a 7-agent research pass in session S-33), then archived that duplicate folder.
- **§5**: added the **commercial-friction / newer-service / true-technical-limit** honesty-label
  framing (with a mapping of 5.1–5.9 to each nature) — makes the lock-out claims defensible.
- **§8.3**: added a **worked sizing example** (recent 3-month average far above the lifetime
  average) teaching "size to the recent trend + peak, not the
  lifetime average," and the monthly-vs-Flex implication.
- **§8.7**: added two pitfall rows — **MDM "source-or-target" bundling** (don't assume MDM
  includes CDI/CDQ for general-purpose use) and **Data Quality runs *inside* a CDI mapping**
  (budget CDI; highest-rate rule re-rates the whole mapping).
- Internal pricing material was kept out of the build (it has since been removed from the KB).
- Verified the connector correction wording (§5.2, §7) matches the CPDS v39.1 pp.7,28 fact — no re-edit.
- Rebuilt via `build/build_kb.py`: 12 sections, 1,504 lines, 12 `[verify]`; **leakage check clean**
  (no prices or discount schedules in the deliverable).
- Files: `sections/05, 08`, generated master, this changelog.

## 2026-09-03 — Depth-expander/Integrator — DONE (capability-comparison xlsx)
- Integrated an internal, de-identified capability-comparison workbook (not part of the KB).
- **§7**: added a **"Capability availability: standalone IICS vs IDMC/IPUs"** table (17 rows,
  IDMC-only markers); **FIXED** the connector line — connectors are **tier-based** (Tier A
  included; Tier B/C/D separate per End Point) and are **NOT IPU-metered** (CPDS v39.1 pp. 7, 28).
- **§5**: added **5.8** (Secure Agent capacity → true-up/compliance exposure at renewal) and
  **5.9** (FedRAMP Moderate is per-service, not blanket; IICS not listed); +2 summary rows;
  resolved the connector `[verify]` to a confirmed tier-based note.
- **§6**: added CLAIRE **~90%** data-wrangling-reduction (vendor-cited).
- Kept customer and deal specifics out of the KB entirely; verified **0 leakage** in the master.
- Coordinated a mutual hold with concurrent session `S-33` (KB consolidation);
  rebuilt via `build_kb.py` (1,479 lines). Handoff: this session stands down on the folder
  so `S-33` performs the final best-of-both merge of its unique items.
- Files: `sections/05,06,07`, `sources/SOURCES.md`, generated master.

## 2026-09-03 — Bootstrap — DONE
- Scaffold created: folder structure, `start-here.md`, `README.md`, `AGENTS.md`,
  `CHANGELOG.md`, `sections\`, `sources\`, `build\`.
- Five parallel research agents drafted the 11 section files (`01`–`11`) with live-web
  research and per-agent source lists (`sources\_agent1..5-sources.md`).
- Authored `sections\00-executive-summary.md` (front matter + at-a-glance table) and the
  curated canonical `sources\SOURCES.md` (de-duplicated from the per-agent lists, with a
  standing `[verify]` list).
- Added `build\build_kb.py` and generated `IICS to IPUs — Knowledge Base.md` from
  `sections\00…11` (12 files → 1,395 lines; 11 `[verify]` markers preserved; headings
  demoted, cross-links rewritten to in-doc anchors, per-section source blocks consolidated).
- Key sourcing outcome: primary anchor is **CPDS v39.1 (eff. June 5, 2026)** for IPU
  definitions and per-service rates; IDMC unveiling corrected to **April 2021** (not 2022);
  Measurement Guide (DOC-19140) is login-gated and left `[verify]`.
- Files: entire KB.
