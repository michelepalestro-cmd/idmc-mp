# START HERE — IICS to IPUs KB

This folder is the **IICS to IPUs Knowledge Base**: how Informatica customers move from **legacy IICS
licensing** (named services with fixed tiers and connector entitlements) to the **IDMC IPU
consumption model** (one pool of Informatica Processing Units spendable across the portfolio). It
covers both the licensing and commercial change and the product and capability differences, and it
is written to be **customer-facing**.

**What to open, in order:**

1. **[`sections/`](sections/00-executive-summary.md)**: the KB itself, one file per topic, read in
   number order:
   [00 Executive summary](sections/00-executive-summary.md) ·
   [01 History, IICS to IDMC](sections/01-history-iics-to-idmc.md) ·
   [02 Legacy licensing model](sections/02-legacy-licensing-model.md) ·
   [03 IPU consumption model](sections/03-ipu-consumption-model.md) ·
   [04 IPU metering by service](sections/04-ipu-metering-by-service.md) ·
   [05 What IICS locks out](sections/05-what-iics-locks-out.md) ·
   [06 What IPUs unlock](sections/06-what-ipus-unlock.md) ·
   [07 Side-by-side matrix](sections/07-side-by-side-matrix.md) ·
   [08 Migration and conversion](sections/08-migration-and-conversion.md) ·
   [09 Commercial model](sections/09-commercial-model.md) ·
   [10 Why move, why stay](sections/10-why-move-why-stay.md) ·
   [11 FAQ and objections](sections/11-faq-objections.md) ·
   [12 Glossary](sections/12-glossary.md).
2. **[`sources/SOURCES.md`](sources/SOURCES.md)**: the citation registry. Every non-obvious claim
   traces here.
3. **[`README.md`](README.md)**: sourcing governance, the freshness policy, and how to build a
   single-file (`.md`) or PDF version with `build/build_kb.py` and `build/build_pdf.py`.
4. **[`AGENTS.md`](AGENTS.md)**: the multi-agent improvement contract.
5. **[`CHANGELOG.md`](CHANGELOG.md)**: what changed, when, and by which role.

> **Customer-facing guardrail:** this KB explains the *model*, not any customer's numbers. It
> contains no discount schedules or deal-specific pricing. Unverified specifics are marked `[verify]`.
