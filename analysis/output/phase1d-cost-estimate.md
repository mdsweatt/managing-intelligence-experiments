# Phase 1d main generation run — S6 cost estimate (billable gate 2)

**Date:** 2026-07-02 · **Matrix:** `runs/phase1d.yaml` (78 cells × N=20 = 1,560 calls) ·
**Ceiling:** $100 hard (`--usd-prior 25`) · **Prices:** `prices/prices-2026-06.yaml` (live 2026-06-25).

**Estimate: ~$21 point / ~$30 conservative** — 4.8× / 3.3× margin under the ceiling.

## Anchors (measurement first, priors labeled)

- **Inputs measured:** fixture `recorded_token_counts` (free `count_tokens`, 2026-07-02); system
  blocks (skills/neutral) estimated words × measured tokenizer ratios (~1.5 tok-hs / ~2.0 tok-opus,
  from the fixtures' own measured counts).
- **Off/neutral-arm outputs:** the pilot's measured per-cell output-token means (neutral assumed ≈
  off; H8's own question). **On-arm outputs:** scaffold demand × ratio +15% structure overhead
  (caps ~100w; mandates ~1,400–1,450w / ~550w); #6/#9 anchored by 1c measurement.
- **#15 thinking:** adaptive spent only 0–62 tok/call in the pilot; a +500 tok/call prior is added
  on all Sonnet/Opus #15 arms (conservative ×1.5 on top). Thinking remains the least predictable
  component — the $100 ceiling and the 1,561-call guard are the real backstop.
- **Conservative bound:** every output prior ×1.5.

## After the run (billable gate 3, separately flagged)

The frozen cross-family judge (`docs/phase1d-judge-spec.md`) grades the records: ≤ ~$56 upper bound
on the metered Gemini key (rubric 4,320 calls ≈ $40; pairwise ≤ 1,440 ≈ $16, shrinking with
eligibility) — projected from the measured $0.049 micro-pilot at live 2026-07-02 prices.

## Run command (after owner go)

    uv run python -m harness.run --matrix runs/phase1d.yaml \
        --manifest fixtures/manifest-phase1d.yaml \
        --skill-manifest fixtures/skills/manifest-phase1d.yaml \
        --neutral-manifest fixtures/neutral/manifest.yaml \
        --usd-prior 25 --out results/

Operational (per RUN.md lessons): check the Console monthly usage limit first; expect a few hours
of wall-clock (1,560 sequential streamed calls; the 180-call pilot took ~20 min); NO resume — a
partial run is rerun, not extended.
