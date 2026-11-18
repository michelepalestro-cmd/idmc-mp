# README — IICS to IPUs KB

Maintenance, sourcing, and governance notes for this knowledge base. **If you are an AI
agent asked to improve the KB, read [`AGENTS.md`](AGENTS.md) — it is the contract.**
This README covers *why* the rules exist and how to keep the KB trustworthy.

---

## What this KB is (and is not)

**Is:** a customer-facing, end-to-end explanation of the move from **legacy IICS
licensing** to the **IDMC IPU consumption model** — the licensing/commercial change and
the product/capability differences, in one place.

**Is not:** a pricing quote, a contract, or an internal deal desk. It explains the
*model*, not any customer's specific numbers.

---

## File map

See [`AGENTS.md` §2](AGENTS.md) for the full map. In short:

- **`sections\*.md`** — the modular **source of truth**. Improve here.
- **`IICS to IPUs — Knowledge Base.md`** — the **integrated** readable deliverable, built
  from the sections. Don't hand-edit; re-integrate.
- **`sources\SOURCES.md`** — the merged citation registry every claim traces back to.

---

## Sourcing & citation governance

1. **Every non-obvious claim is cited.** Prefer authoritative Informatica sources
   (`informatica.com`, `docs.informatica.com`, `knowledge.informatica.com`, official
   pricing pages) over third-party blogs.
2. **No fabricated specifics.** Per-IPU dollar prices, exact metering multipliers, and
   discount percentages are only stated if a public source confirms them. Otherwise the
   concept is described qualitatively and marked **`[verify]`**.
3. **No internal commercial content.** Deal-specific discounting, volume-tier percentages, price
   lists and confidential contract mechanics do **not** belong anywhere in this KB. They are handled
   by Informatica per engagement and are kept out of it entirely.
4. **Facts are dated.** Informatica changes packaging, metering, and pricing over time.
   Citations note the source date/version so a future agent can tell what's stale.

---

## Freshness policy

Because the underlying facts move, treat the KB as **living**:

- Re-verify pricing/metering/packaging claims periodically (see `CHANGELOG.md` for the
  last verification pass).
- When a claim is re-verified, update its citation date even if the fact didn't change.
- Anything marked `[verify]` is a standing invitation for the next agent to confirm or
  correct it against a live source.

---

## How the deliverable is built

The KB was bootstrapped by **five parallel research agents**, each owning a
non-overlapping set of `sections\` files and doing its own live-web research, then
**integrated** into `IICS to IPUs — Knowledge Base.md`. Ongoing improvement follows the
same modular pattern — see [`AGENTS.md`](AGENTS.md). To rebuild the integrated file
after editing sections, use the **Integrator** role in `AGENTS.md §6`.

---

## Provenance

- Created: **2026-09-03**.
- Change history: see [`CHANGELOG.md`](CHANGELOG.md).
