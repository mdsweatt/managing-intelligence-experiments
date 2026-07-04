# Phase-1a correlation cuts — findings

**Status: descriptive / observational secondary analysis (2026-06-25). NOT pre-registration, NOT a
hypothesis test, NOT a change to H1.** These are exploratory cuts of *already-collected* Phase-1a
data, recorded as a result-pointer. Nothing here may be cited as confirming or refuting a
hypothesis; the *causal* test of the thesis below is a separate, not-yet-run experiment (see §5).

**Reproduce:** `uv run python -m analysis.correlations` (reads the enriched
`analysis/output/h1_cov.csv` from `analysis.h1`; no pricing happens here). Outputs:
`correlations_by_model.csv`, `correlations_by_axis.csv`, `decomposition.csv`,
`decomposition_scatter.png`, `cov_by_axis.png`.

---

## 0. Why these cuts

The working thesis from the deep-dive: **within-cell, run-to-run token variance tracks the model's
degrees of freedom** — pin the output and variance vanishes; give the model latitude (think as long
as it likes, write as much as it likes, iterate over turns) and variance enters. If that holds, it
underwrites the budgeting story: *which* tasks are bandable is predictable from task structure, and
adding determinism (skills/scaffolding) should move a task toward the bandable end. These three cuts
test the premise against the 67-cell table.

## 1. By model — no main effect

Median within-cell CoV is **flat across the ladder**: haiku 4.8% · opus 4.6% · sonnet 3.9%.
Model identity does **not** make a model intrinsically noisier. Sonnet's higher *mean* (6.7%) and
*max* (20.1%) come entirely from *which cells it carried* (it owns the thinking #15 cells), not from
the model. The big run-to-run divergences are **task×model interactions**, and they don't point at
any one model: #18-M analyze (opus 0.3% vs sonnet 16.7%), #8-M extract (haiku 1.3% vs sonnet 10.4%),
#17-few iterate (opus 19.2% vs sonnet 3.2%), #11-M code-edit (haiku 15.6% vs sonnet 3.7%).

> **Budgeting read:** you cannot blame "the unpredictable model," and a *cheaper* model is not
> inherently *less* bandable. (Between-model *cost* gaps are the over-service signal — a different
> axis — and are deliberately excluded here.)

## 2. By cost axis — the degrees-of-freedom ladder

Median within-cell CoV grouped by SPEC §3 cost axis, ascending:

| Cost axis | n | median | mean | max |
|---|---|---|---|---|
| payload | 4 | 1.0% | 4.8% | 16.7% |
| input | 30 | 1.9% | 3.7% | 10.4% |
| output | 10 | 3.3% | 3.9% | 7.1% |
| cached-context | 9 | 4.7% | 5.7% | 15.6% |
| turns | 8 | 6.2% | 8.1% | 19.2% |
| **thinking** | 6 | **14.6%** | **15.2%** | **20.1%** |

The ladder is monotonic in the amount of latitude the axis grants the model, and **thinking is the
only axis whose median lands in the kill-condition window** — ~8× the input/payload tasks. The
premise holds at the axis level.

*Caveat:* `payload` (n=4) is bimodal, not genuinely tightest — its median hides the #18 opus/sonnet
split (see §3); read its mean/max, not its median. Small-n axes are descriptive only.

## 3. Input/output decomposition — *where* the variance lives (the centerpiece)

The frozen fixture makes the input identical on every run, so the **input component has CoV ≈ 0 on
every standard/payload cell** (`cov_input` = 0.0000, min and max) and the **cache-read component has
CoV ≈ 0 on every cache cell**. **100% of within-cell variance is an output-component phenomenon.**
That collapses the whole metric to an identity:

> **CoV_composite = CoV_output × (output's share of the cell's cost)**

So a task is bandable for one of two distinct reasons — and the data shows both, plus the failure:

| Mechanism | example | output CoV | output cost share | composite CoV |
|---|---|---|---|---|
| **Output barely varies** (length pinned) | #5 translate | 0.5–1% | 88% | **0.4–1%** |
| | #9 long-form draft | 3–5% | 94–98% | **2–5%** |
| **Output diluted** (small cost share) | #7-L summarize | 8–21% | **7–9%** | **0.8–1.4%** |
| | #18-M analyze (opus) | 4.1% | **8%** | **0.3%** |
| **Both bad → unbandable** | #15 thinking | 15–20% | **91–99%** | **14–20%** |

Thinking breaches because it is the worst of both: the output (reasoning) is **95–99% of the cost**
*and* its length swings 15–20% run-to-run. There is no deterministic mass to dilute it.

### The #18 anomaly, resolved
Same fixed dataset, same prompt: **opus** composite 0.3%, **sonnet** composite 16.7% (48× apart).
The decomposition explains it without mystery — opus wrote a **short, consistent** analysis (output
= 8% of cost, output CoV 4.1%); sonnet wrote a **long, variable** one (output = 89% of cost, output
CoV 18.7%). It's a verbosity/latitude difference in the output, exactly the degrees-of-freedom
mechanism — not noise and not a model being "worse."

## 4. What this means for the budgeting question

- The model-stochasticity floor is small (§1) and the variance that exists is **structured and
  predictable from task shape** (§2–3). You can label a task *budget-this* vs *meter-this* a priori.
- The two levers on bandability are now explicit and **architectural**: (a) **constrain the output**
  (scripts/schemas/length caps → lower CoV_output) and (b) **shrink the output's cost share** (cache
  or fix a large context → lower the multiplier). Either one tightens the band; thinking-style tasks
  resist both.
- This is the measured version of the "specialized skills add determinism → bandable cost" thesis:
  skills act on lever (a), prompt-caching on lever (b).

## 5. Limits & the causal follow-up

These cuts are **observational across 67 heterogeneous cells** (one run, N=20, June-2026
models/prices). The axis→variance and latitude→variance links are **correlational across task
types**, not a controlled manipulation — so they *motivate* but do not *prove* "adding determinism
reduces a task's variance." The clean causal test is a **determinism A/B**: take one task, run it
*prompted* vs *skill-scripted*, hold the model fixed, and measure CoV_output, tokens, and
cross-model quality-equivalence. And the regime where H1 is predicted to break — high-fan-out
agentic #13/14/20/21 — remains **Phase 1b, unmeasured**; these cuts say nothing about it.
