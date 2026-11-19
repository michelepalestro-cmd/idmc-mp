# README — IICS to IPUs KB

Maintenance, sourcing and governance notes for this knowledge base. **If you are an AI agent asked
to improve the KB, read [`AGENTS.md`](AGENTS.md); it is the contract.** To *use* the KB, open
[`start-here.md`](start-here.md).

## What this KB is (and is not)

**Is:** a customer-facing, end-to-end explanation of the move from **legacy IICS licensing** to the
**IDMC IPU consumption model**: the licensing and commercial change and the product and capability
differences, in one place.

**Is not:** a pricing quote, a contract or a deal desk. It explains the *model*, not any customer's
numbers.

## File map

- [`sections/`](sections/00-executive-summary.md): 13 Markdown files, `00` to `12`. **The source of
  truth and the thing you read.** Improve here.
- [`sources/SOURCES.md`](sources/SOURCES.md): the citation registry every claim traces back to.
- `build/build_kb.py`: joins the sections into one file, `iics-to-ipus-knowledge-base.md`, on demand
  (Python 3.10+, standard library only). The joined file is generated and not shipped.
- `build/build_pdf.py`: renders that joined file to `iics-to-ipus-knowledge-base.pdf` (needs
  `markdown`, `pymdown-extensions`, `playwright` and a browser). The PDF is not shipped either.
- [`CHANGELOG.md`](CHANGELOG.md): what changed, when, and by which role.

From the repo root:

```bash
cd knowledge/12-reference-library/iics-to-ipus-kb
python3 build/build_kb.py      # -> iics-to-ipus-knowledge-base.md (generated, not committed)
python3 build/build_pdf.py     # optional -> iics-to-ipus-knowledge-base.pdf
```

## Sourcing and citation governance

1. **Every non-obvious claim is cited.** Prefer authoritative Informatica sources (`informatica.com`,
   `docs.informatica.com`, `knowledge.informatica.com`, official pricing pages) over third-party blogs.
2. **No fabricated specifics.** Per-IPU prices, exact metering multipliers and discount percentages
   are stated only if a public source confirms them. Otherwise the concept is described
   qualitatively and marked **`[verify]`**.
3. **No internal commercial content.** Deal-specific discounting, volume-tier percentages, price
   lists and confidential contract mechanics do not belong anywhere in this KB.
4. **Facts are dated.** Informatica changes packaging, metering and pricing over time. Citations note
   the source date or version (rates are anchored on CPDS v39.1, effective 2026-06-05).

## Freshness policy

- Re-verify pricing, metering and packaging claims periodically (see `CHANGELOG.md` for the last
  verification pass).
- When a claim is re-verified, update its citation date even if the fact did not change.
- Anything marked `[verify]` is a standing invitation for the next agent to confirm or correct it.
- Before you finish, run `python3 toolkit/tools/secret_scan.py .` from the repo root (must print CLEAN).

## Provenance

Created 2026-09-03 by five parallel research agents, each owning a non-overlapping set of section
files. Change history: [`CHANGELOG.md`](CHANGELOG.md).
