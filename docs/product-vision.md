# Product vision — the instrument, not a report

**Status:** strategy / product vision (v0.2 — 2026-06-23; v0.1 same day, revised after an independent review pass)
**Owner:** TetradStudios
**Relationship:** **Downstream of `charter.md`; feeds charter §10 (publication / content angle). This is NOT pre-registration.** Nothing here is a hypothesis or a kill-condition, and nothing here may be cited as evidence for H1–H4. The charter and SPEC remain the source of truth for what the experiments claim; this doc describes what the *product* built on top of those measurements would be. When this doc and the charter appear to conflict, the charter wins — escalate, don't silently reconcile.

> **Why this doc exists.** Mainstream coverage (e.g. SmarterX/Marketing AI Institute, *"AI Token Costs Continue to Explode and Nobody Can Predict Them,"* 2026-06-23 — logged in charter §9 addendum) frames enterprise cost **unpredictability** as the core blocker to AI rollout, and treats it as effectively unsolvable. This doc records the position that the deliverable which answers that framing is a **living instrument**, not a static report — and what that instrument looks like and how an enterprise leverages it.

---

## 1. The distinction

A **report** is a snapshot: *"Task X costs Y tokens / $Z, as of June 2026."* The charter already says why that is a trap:

- **It decays in weeks.** A tokenizer or price change obsoletes the figure at constant behavior (charter §7; observed: Opus 4.7 ≈ +35% tokens, a hidden price bump). The unit moves under you.
- **It commoditizes.** The static task→token library is the thing the prior-art scan says closes as the white space closes (charter §9: GDPval v2, Artificial Analysis already reporting tokens). A report is the **hook, not the moat.**

An **instrument** is a *meter that re-zeroes itself* and is *parameterized by the customer's reality.* The through-line:

> **The instrument is Experiment 1's own discipline, kept current and projected onto a customer's task mix.** The exact properties that make the experiment rigorous are the properties that make the product an instrument rather than a report.

It does **not** re-benchmark a customer's live prompts — that would break the frozen-fixture control (CLAUDE.md rule 5 / charter §5) that H1 depends on. It projects from the **frozen-fixture benchmark library**, parameterized by the customer's task mix and frequencies (see §2's calculator). Observing a customer's live *actuals* is a separate, telemetry-driven step (§4), not a re-run of the benchmark.

See `docs/images/report_vs_instrument_whiteboard.png` for the one-glance version.

---

## 2. What the instrument looks like — defining properties

| Experiment-1 discipline | → Product property |
|---|---|
| Version-stamp every record (model + tokenizer + date) — charter §4, CLAUDE.md rule 3 | **Self-recalibrating.** Re-runs on each model release; every figure carries a freshness date and flags *why* it moved ("Opus 4.9 shifted the tokenizer"). A living meter, not a settled number. |
| Distributions + tails, not point estimates — charter §6, §10 | **Bandable-vs-monitor-only labeling.** The H1 fork *becomes a product behavior*: per task it says "budget this (tight CoV)" vs. "you can only meter this (noisy)." The honest answer to "nobody can predict" — *some* things you can, and the instrument says which. |
| Four-variable decomposition — charter §4 | **Parameterized calculator.** The customer supplies the one number they know (frequency) + their task mix; the engine computes measured tokens/task × frequency × a hot-swappable price scalar × band → a role/team projection. Price stays quarantined to one knob so the projection survives the cost collapse. |
| H3 cache / fan-out / payload / multi-turn decomposition — charter §6 | **Explanatory, not just numeric.** Attributes the bill *within a task*: *this* much is cache-reload waste, *this* much is multi-turn accumulation, *this* much is payload. Turns a number you can't act on into one you can. (Over-service — the same work on a bigger model — is a *between-model* axis, **not** part of this within-task decomposition; charter §3 keeps it separate from H1. It surfaces in the §3 maturity arc, step 2.) |
| "Verify live, don't assert from memory" — CLAUDE.md | **Measure the customer's own stack, don't quote a generic benchmark.** Distinct from self-recalibration above (which re-runs the *library* on each model release): this re-measures against the customer's *specific* models, effort settings, and prompts rather than asserting a published average. The methodological paranoia — distrust any cached number until a call confirms it — is the product feature. |

The property that crosses from *interesting* to *durable*:

- **Outcome-linkage (the moat).** Tying spend to *work produced*, not just tokens consumed — which enables the waste-ratio framing (H4) and the move from **showback** (decays ~10–20%/yr, can backfire — charter §9) to **chargeback** (durable). Charter §9 already names this as the moat; the instrument is where it is realized.

---

## 3. How an enterprise leverages it — the maturity arc

A left→right arc that maps onto the charter's free-hook → paid-accountability funnel (charter §3 H4, §9). It deliberately parallels the **FinOps** lifecycle — *Inform* (step 1: plan / budget) → *Optimize* (step 2: right-size) → *Operate* (steps 3–4: monitor + charge back) — because charter §9 mandates **aligning vocabulary with FinOps for buyer credibility** (FinOps Foundation; the discipline TechCrunch's "Tokenomics Foundation" is modeled on — charter §9 addendum):

1. **Plan a rollout** *(the article's literal wall).* Project cost from measured bands × expected frequency — *with honest bands and tails*, and an explicit "these workflows are monitor-only, don't point-estimate them." Answers "we can't estimate what this will cost" without lying about the parts that genuinely can't be pinned.
2. **Right-size / pre-deployment sizing.** The over-service finding operationalized: *"this workflow matches Haiku at equivalent output (where checked, per SPEC D3) — you're paying the model price premium × ~1.35× tokenizer inflation to run Opus."* (Never a blanket "identical"; no asserted price multiple — the dollar ratio comes from `prices/` at analysis, never from memory.) This is the **evidence base routing needs** (charter §9 demoted routing-as-feature; this is the layer underneath it).
3. **Continuous drift monitoring.** Post-deployment, track actual vs. predicted; alert when a task's distribution drifts (a new model version moved the tokenizer; a workflow's fan-out crept up). The living-meter discipline as an ops product.
4. **Chargeback / accountability** *(the paid layer).* Attribute cost to teams / roles / outcomes — the mechanism prior art says actually changes behavior, vs. the dashboard that decays.
5. **Procurement leverage** *(indirect on the article's packaging gripe).* It won't fix opaque per-seat licensing — but it gives the enterprise the **consumption ground-truth** to evaluate seat-license vs. pay-as-you-go for *their* actual mix, and to negotiate from data instead of vibes.

**The funnel** (a free→paid gradient that runs *orthogonal* to the FinOps phases above — FinOps models the lifecycle, not the monetization step): free provocation snapshot (hook) → parameterized estimator (their mix) → continuously-metered, outcome-linked, chargeback instrument (paid, durable).

---

## 4. Honest boundaries

What the instrument does **not** do — recorded so the framing doesn't oversell:

- **It does not fix vendor pricing/packaging opacity.** The article's loudest complaint is about *contracts* (per-seat vs. pay-as-you-go, pooled quotas, routing hiding model choice). We denominate in **tokens** and quarantine price (charter §4). We supply the *consumption* side of the equation, not the contract side — adjacent, not the same.
- **The hardest case is the part most deferred.** Open-ended, high-fan-out, compound work (the "three-hour strategy conversation," 24/7 agent loops) is Phase 1b (charter #13/14/20/21), deferred — and where H1 is most likely to *break* into distribution-monitoring. The instrument delivers value there (it says *which* work is bandable vs. must-be-metered) but will not hand over a tight point estimate, and arguably nothing can.
- **It is a living meter, not a one-time answer.** Tokens-per-task is stable only within a fixed model+tokenizer version (charter §7). The predictability it offers has a shelf life and must be continuously re-run. That is the feature (it is the moat, not the commoditizing static library) — but it means the deliverable is an instrument to operate, not a report to read.
- **Continuous monitoring needs live telemetry it does not yet have.** The §3 arc's step 3 (track *actual* vs. predicted) is a large leap beyond a frozen-fixture benchmark harness: it requires instrumenting the customer's day-to-day usage — a proxy/middleware layer, or (more likely) **vendor-native analytics APIs** (charter §9 notes Anthropic's Enterprise Analytics API already exposes per-named-user cost). Experiment 1 produces only the *predicted* side; the *actual* side is an unbuilt integration. Naming it keeps the arc honest.
- **A token-denominated meter does not unify a multi-vendor stack.** Cross-provider token counts aren't comparable (different tokenizers — charter §5, SPEC §2's "tokenizer NOT uniform"), so a meter denominated strictly in tokens (charter §4) cannot natively roll up Anthropic + OpenAI + Gemini spend. This is *why* v1 is Anthropic-first (charter §5 v0.3); cross-provider is the paid-precision pass, not the v1 instrument.

---

*Experiment 1 produces the **calibration data** for this instrument; it is not the instrument. Productization is downstream of the measurement program and is not gated by any single run.*
