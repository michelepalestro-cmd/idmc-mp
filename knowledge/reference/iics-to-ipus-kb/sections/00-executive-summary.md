# Executive Summary

**"Moving from IICS to IPUs" is a change in how you buy Informatica's cloud — not a
change of product.** You stay on the same platform; you change the commercial model
underneath it. This knowledge base explains that transition end to end: the history, the
old licensing model, the new consumption model, exactly what each service costs in IPUs,
what the old model locked customers out of, what the new model unlocks, how to migrate,
the commercial mechanics, an FAQ, and a glossary.

## The story in five sentences

1. **IICS** (Informatica Intelligent Cloud Services, GA December 2017) is the original
   brand for Informatica's cloud data-management platform; **IDMC** (Intelligent Data
   Management Cloud, unveiled April 2021) is the *same platform*, expanded across the full
   portfolio and built around the **CLAIRE** AI engine.
2. Under **legacy IICS licensing** you bought *each service separately* — a fixed
   edition/tier of Data Integration, of Data Quality, of API Management, and so on — each
   with its own capacity and its own connector entitlements.
3. Under the **IDMC IPU model** you buy *one flexible pool* of **Informatica Processing
   Units (IPUs)** — "a unit of capacity that can be used across eligible Cloud Services" —
   and spend it against whatever mix of services you actually use, metered per usage.
4. That single change removes the walls of the old model: it ends stranded per-service
   capacity, lets you adopt any eligible service (and every newly released one) with no new
   SKU, and adds real-time consumption visibility and AI (CLAIRE) across the platform.
5. Because the platform doesn't move, migrating is a **licensing conversion, not a
   re-platform** — the real work is *estimating and governing consumption*, which the model
   supports with published per-service rates, a real-time dashboard, and threshold alerts.

## At a glance

| | Legacy IICS licensing | IDMC IPU model |
|---|---|---|
| **What you buy** | A fixed edition/tier of each service, separately | One pooled quantity of IPUs |
| **Where spend can go** | Locked to the service you licensed | Any eligible service — spend follows the work |
| **Adding a capability** | New SKU / new contract | Already accessible; just start consuming |
| **New product releases** | Not included until purchased | Auto-activated into your pool on release |
| **Connectivity** | Bounded by connector entitlements | Used as part of normal service consumption |
| **Basis of the bill** | Fixed entitlement, used or not | Actual work performed, metered monthly |
| **Cost visibility** | Fragmented, per-contract | Real-time usage dashboard + threshold alerts |
| **AI (CLAIRE)** | Earlier-generation assistance | CLAIRE / CLAIRE GPT / Copilot / Agents across the platform |
| **The trade-off** | Rigid, but predictable per line | Flexible; cost tracks usage, so it must be governed |

## How this knowledge base is organized

- **Sections 1–2** — the history (IICS→IDMC) and the legacy per-service licensing model.
- **Sections 3–4** — what an IPU is, and exactly how each service meters against the pool
  (with published CPDS v39.1 rates).
- **Sections 5–6** — the heart of the comparison: what legacy licensing *locks out*, and
  what the IPU model *unlocks*.
- **Section 7** — a single side-by-side matrix.
- **Sections 8–9** — how to migrate/convert, and the commercial model in customer terms.
- **Section 10** — should you move? An honest look at reasons to move to IPUs vs. reasons to wait.
- **Sections 11–12** — FAQ / objection handling, and a glossary.

> **Shareable-doc guardrail.** This KB explains the *model*, not any customer's numbers.
> It contains no dollar-per-IPU price and no deal-specific discounting — those are
> provided by Informatica per engagement. Published *consumption rates* (how many IPUs a
> unit of work costs) are quoted from **CPDS v39.1 (effective June 5, 2026)** and dated so
> they can be re-verified; unconfirmed specifics are marked `[verify]`.
