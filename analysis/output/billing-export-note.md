# Provider billing export — program-wide spend record

`claude_api_cost_2026_06_18_to_2026_07_05.csv` is the **Anthropic Console cost export**
(daily grain, UTC) for the account over 2026-06-18 → 2026-07-05, published as the source for
the program-wide dollar figure. It is a **provider-side receipt**, not harness data: run
records remain tokens-only (CLAUDE.md invariant 2); dollars enter only at analysis time, and
this file is the provider's own meter for that step.

**Scrub applied (one column):** the account's second API key belongs to an unrelated project;
its name is replaced with `other-key-redacted`. Its rows are retained — all $0.00 — because
they are the evidence that **only the `Tokenomics` key spent anything**, i.e. the export is
experiment-scoped. No other cell is modified. `cost_usd == list_price_usd` throughout (no
discounts in effect).

## Attribution — every nonzero date bucket maps to a run id

| Date(s) (UTC) | Spend | What it was |
|---|---|---|
| 2026-06-21/22 | $4.65 | Phase 0/1a cost-gate pilot (`run-20260621T171817Z-563d39`) |
| 2026-06-24/25 | $149.01 | **Phase 1a measurement run** (`run-20260624T112122Z-cfa60e`, ~17.2 h spanning both UTC days) |
| 2026-06-28 | $10.01 | Phase 1c generation ($2.94, measured in-harness) + frozen Opus judge (≈$7.07 — the judge spend that was not persisted in harness records; this export is its measurement) |
| 2026-07-02/03 | $26.67 | Phase 1d generation ($24.57 measured) + design pilot/micropilot |
| **Total (Anthropic)** | **$190.34** | |

## Program-wide reconciliation

$190.34 (Anthropic, this export) + **$21.18** (Gemini judge, measured + meter-reconciled to
Δ≤0.3% — `phase1d-judge-run-note.md`) = **$211.52 for the entire program, fully measured,
zero estimated components.**

Window note: the 2026-06-16 live-verification probes (`docs/live-verification-2026-06-16.md`)
predate the export window; they were cents-level parameter-acceptance calls, not measurement
runs.
