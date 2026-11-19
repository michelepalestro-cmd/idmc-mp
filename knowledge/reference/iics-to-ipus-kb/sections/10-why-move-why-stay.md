# 10. Should You Move to IPUs? Reasons to Move vs. Reasons to Wait

Because IICS and IDMC are the **same platform** (see Section 1), moving to IPUs is a
**commercial and timing decision, not a technical one**. "Staying" here means staying on
**legacy per-service licensing for now** — not staying on a different or unsupported
product. The platform evolves either way. This section lays out both sides honestly so a
customer can decide *whether* and *when* to convert.

> **Honesty note (carried from Section 5).** Most reasons to *move* are about **agility,
> access, and efficiency**; most reasons to *wait* are about **predictability, governance
> readiness, and contract timing** — not about capability. And because IPUs are
> Informatica's go-forward commercial model, "wait" is usually **"wait until renewal,"**
> rarely "never."

---

## 10.1 Why a customer would move to IPUs

**1. Access the whole portfolio — and adopt new services with no new SKU.**
One pool funds any eligible service (integration, quality, governance, catalog, MDM,
API, marketplace, ingestion), and newly released eligible services auto-activate. If you
foresee needing *more than one* capability — or want the option to — IPUs remove the
procurement gate (Sections 6.1–6.2).

**2. End stranded, siloed capacity — spend follows the work.**
Under per-service licensing, surplus in one service can't fund a shortage in another. A
single pool lets budget flow to wherever the work actually is, quarter to quarter, with no
re-contracting (Sections 5.4, 6.3).

**3. Elasticity and burst for spikes and one-off events.**
Migrations, seasonal peaks, M&A ingestion, and campaign bursts are absorbed by drawing
more from the pool, instead of sizing and paying for a fixed peak tier year-round
(Section 6.3).

**4. Get the IPU-era capabilities.**
CLAIRE AI / CLAIRE GPT / Copilot, the fully-managed serverless runtime, advanced pushdown
optimization, Data Marketplace, and the Free & PayGo on-ramps are the modern, differentiating
capabilities — reachable from the same pool (Sections 6.4–6.6).

**5. Simplified procurement — one unit, one pool, fewer renewals and true-ups.**
Replace a patchwork of per-service SKUs, tiers, and connector line items with a single
consumption unit and one agreement (Section 6.7).

**6. FinOps visibility and control.**
Real-time consumption dashboards, per-scaler metering, and threshold alerts give a level of
spend transparency the fixed-SKU model never offered (Section 6.8).

**7. Utility-style financial modeling.**
Cost scales with data volume like a utility, which many finance teams find easier to model
and defend than lumpy, periodic SKU true-ups (Sections 6.8, 9.5).

**8. Future-proofing and consolidation.**
IPUs are Informatica's standard go-forward model; new services are included as they ship,
and running multiple capabilities on one platform reduces training, maintenance, and
procurement overhead (Informatica cites Nucleus Research outcomes such as ~413% ROI;
Section 6.7).

**9. Access to newer compliance authorizations, where you need them.**
Some IDMC services/environments carry authorizations (e.g., FedRAMP Moderate) that legacy
IICS does not — relevant for regulated/public-sector workloads (validate per service;
Section 5.9).

---

## 10.2 Why a customer would stay (or wait)

**1. Stable, narrow, well-understood usage.**
If you run essentially **one service at a steady volume** with no appetite for the broader
portfolio, the flexibility of IPUs is value you may not use — and a fixed per-service tier
gives a flat, predictable line item.

**2. Preference for fixed, predictable budgeting.**
Consumption cost **tracks usage**, so it varies. An organization that prizes a fixed,
capex-like number — or whose finance/procurement process favors fixed commitments over
variable consumption — may prefer the certainty of a set tier (accepting the rigidity that
comes with it).

**3. No consumption-governance capacity yet.**
The IPU model rewards active FinOps: someone must watch the dashboard, set thresholds, and
right-size the commit. **Without an owner for consumption**, an org risks overage
surprises — and until it can staff that discipline, a fixed tier is the safer short-term
posture. (The fix is to *build* that capability, then move — Section 8.5.)

**4. Contract timing.**
If you're **mid-term** on a legacy agreement with no compelling trigger, it's usually
cheaper and cleaner to **convert at renewal** than to overlap or unwind an existing
commitment early.

**5. You haven't baselined consumption yet.**
Right-sizing an IPU pool depends on a credible usage estimate. If you can't yet baseline
your workloads confidently, do the estimation work **first** (Section 8.2–8.3) so you don't
over- or under-commit — then convert. Waiting to gather data is legitimate; waiting
indefinitely is not.

**6. Aversion to variable/runaway spend.**
An inefficient mapping, a full reload where incremental would do, or unexpected growth can
raise consumption. Fixed tiers **cap** that exposure (at the cost of flexibility). If your
risk tolerance for variable spend is very low and your workload is volatile, that trade may
favor waiting until you've tuned workloads and set guardrails.

**7. Favorable legacy entitlements to retain until renewal.**
Occasionally a legacy edition, connector, or negotiated term is advantageous to keep for
the remainder of the term. Convert when that advantage lapses rather than leaving value on
the table.

---

## 10.3 A quick decision aid

| Lean toward **MOVING to IPUs** if… | Lean toward **WAITING** (convert at renewal) if… |
|---|---|
| You want (or might want) more than one service | You use exactly one service at a stable volume |
| You expect change, growth, or seasonal/burst workloads | Your usage is flat, narrow, and well-understood |
| You want CLAIRE AI, serverless, pushdown, Marketplace | You have no near-term need for newer capabilities |
| You have — or will staff — a FinOps/consumption owner | You have no owner for consumption governance yet |
| You're at (or near) renewal | You're mid-term with no compelling trigger |
| You can baseline consumption credibly | You can't yet estimate usage to right-size a pool |
| Predictability matters less than flexibility | A fixed, capped budget line matters most |

**The through-line:** if the answer is "wait," pair it with action — **baseline your
consumption now** and set a target renewal to convert. Because the platform is identical
and IPUs are the go-forward model, waiting is a *timing* choice, and the customers who wait
well are the ones who arrive at renewal already knowing the pool they need.

> See also: Section 7 (side-by-side matrix), Section 8 (how to convert and govern
> consumption), Section 9 (the commercial model), and Section 11 (FAQ) for the common
> objections that surface in this decision.

---

## Sources

- Informatica — Cloud Data Integration / Cloud pricing (consumption model, benefits, FinOps
  dashboard/alerts, auto-activation of new services, ROI): https://www.informatica.com/products/cloud-integration/pricing.html
- Informatica — Cloud & Product Description Schedule (CPDS) v39.1 (IPU definition, overage /
  Overage Protection, Flex IPU; FedRAMP/compliance handled per service): https://www.informatica.com/content/dam/informatica-com/en/docs/informatica-cloud-and-product-description-schedule.pdf
- This section synthesizes the trade-offs established in Sections 5, 6, 8, and 9; no new
  external claims are introduced beyond those already cited there.
