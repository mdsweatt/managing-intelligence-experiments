# Phase 1d judge run — run note (billable gate 3 EXECUTED, Batch-API transport)

**Graded:** `results/run-20260702T203102Z-f704f0` (all 1,560 factorial outputs) ·
**Instrument:** FROZEN judge `5fd08ff3287cbd32…` (`fixtures/judge/manifest-phase1d.yaml`,
`docs/phase1d-judge-spec.md`) — hash verified at plan, every step, and finalize ·
**Outputs:** `analysis/output/phase1d/quality_{rubric,pairwise,spotcheck}*.csv`,
`quality-findings.md`; raw grading record in `analysis/output/phase1d/batch/`
(state / results / per-attempt usage; prompt files re-derivable deterministically via
`judge_gemini_batch plan` — pass 1 is a pure function of the frozen records + manifests).

## Operational deviation: interactive → Batch API (instrument unchanged)

The pre-registered interactive run **crashed 2026-07-02** on a quota the micro-pilot could not
have revealed: Tier-1 `GenerateRequestsPerDayPerProjectPerModel = 250` for `gemini-3.1-pro`
(owner's AI Studio screenshot: 25 RPM / 250 RPD; the GA 2.5-pro's 1K RPD would also have taken
~6 days). ~244 calls (≈$2, Google-metered) burned with the in-memory usage log lost — the
end-of-run-write flaw, fixed structurally below. **Owner-approved transport change (2026-07-03):**
Gemini **Batch API** — model, prompt bytes, `thinking_budget`, `temperature`,
`max_output_tokens`, tolerant parser, K=3 majority, and the 2-attempt retry contract are
**byte-identical**; `judge_hash` untouched. Batch quota was verified independent of the exhausted
interactive cap by a $0.02 live smoke before submission. Driver: `analysis/judge_gemini_batch.py`
(commit `7282536`), record→batch→replay around an **unmodified** `quality.analyse()`, with a
tested batch==interactive equivalence contract; every fetched result and usage row streams to
disk on arrival.

## Verification (all pass)

- **4,869 / 4,869 calls parsed OK** — 4,320 rubric (1,418 distinct prompts × K; 22 records share
  byte-identical outputs with a cell-mate) + 549 pairwise. **Zero parse failures, zero retry
  rounds, zero failed-final keys.** Strict finalize confirmed no unserved replicate keys before
  grading.
- 3 sequential rubric batches + 1 pairwise batch, each under the 5M enqueued-token Tier-1 cap.
  Observed once: chunk 1's ~$10.41 completion tripped the **$10/10-min Tier-1 spend window**,
  bouncing the next submission for one 10-min poll tick — self-healed, no data impact.
- Wall-clock: ~7h submission-to-finalize (2026-07-03 04:27–11:3xZ), single day — the preview
  model's point-in-time-snapshot concern (spec §1) did not straddle days.

## Measured cost + usage (from the streamed per-attempt log)

| phase | calls | input | output | thinking | cost (batch $1/M in, $6/M out+think) |
|---|---:|---:|---:|---:|---:|
| rubric | 4,320 | 6,022,590 | 123,557 | 2,132,551 | $19.56 |
| pairwise | 549 | 623,127 | 3,241 | 162,577 | $1.62 |
| **total** | **4,869** | **6,645,717** | **126,798** | **2,295,128** | **$21.18** |

vs ≤ ~$28 batch bound (≤$56 interactive). Judge-path total incl. smoke + crashed interactive
attempt ≈ **$23.4**. Phase-1d billable total (generation $24.57 + judge) ≈ **$48 vs the $100
ceiling**. Thinking ran ~494 tok/call mean — inside the micro-pilot's measured soft-budget range
(306–547), as the freeze documented.

**Independent meter check (owner, Google AI Studio, 2026-07-03):** dashboard total **$22.66**;
its token/request counters show the *interactive* surface only — 247 requests / 247.41k in /
85.48k out = the crashed run + micro-pilot (matches the 247/250 RPD peak), ≈ $1.52 at interactive
prices. Batch tokens are metered separately, but batch dollars are in the total:
$1.52 + $21.18 (this note's streamed usage log) + $0.02 smoke ≈ **$22.72 vs $22.66 — delta $0.06
(~0.3%, display rounding)**. Harness capture and the provider meter agree again.

## Pre-registered caveat, observed (for the H6 read — not acted on)

Pairwise eligibility (both sides of a matched pair passing the format-neutral `faithful` gate)
admitted **183 of 480 possible pairs (38%)** — the loose-arm-invention signal the judge spec §4
flagged as plausible real signal, not the 1c definitional hole. The analysis must report
invention rates by arm and carry the coverage limitation in the H6 conclusion, per spec.

## Gate status

Gate 3 DONE. Next (owner pre-approved): h5/h7/h8 + quality analysis → **human panel**
(stratified spot-check export is written: 144 rows) → 1d report + doc alignment.
