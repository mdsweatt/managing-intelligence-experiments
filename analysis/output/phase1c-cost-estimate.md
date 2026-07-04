# Phase-1c cost estimate — 360-call run vs ceiling

Projection of `runs/phase1c.yaml` (3 tasks × 3 models × 2 skill arms × N=20 = **360 calls**). Output tokens are MEASURED from the micro-pilot (`runs/phase1c-pilot.yaml`, N=1/cell, `run-20260628T043414Z-859f8e`); input tokens are measured (pilot records for #6/#9; free count_tokens for #4). Dollars from `prices/prices-2026-06.yaml` (Haiku $1/$5, Sonnet $3/$15, Opus $5/$25 per Mtok). Per CLAUDE.md the run is denominated in tokens; price is a scalar applied here only.

- **Point estimate** (pilot output as-is): **$2.96**
- **Conservative bound** (output ×2.0 skill-off [unconstrained], ×1.4 skill-on [length-capped]): **$4.69**
- **Ceiling:** $50 → headroom **17×** (point) / **11×** (conservative)
- **Opus contribution:** $1.87 point / $2.93 conservative (62% of the conservative total)

## Per task

| task | point $ | conservative $ |
|---|---|---|
| #4 | 0.18 | 0.19 |
| #6 | 0.47 | 0.78 |
| #9 | 2.30 | 3.72 |
| **all** | **2.96** | **4.69** |

## Per cell (input/output tokens from pilot, cost × N=20)

| task | model | arm | in tok | out tok (pilot) | point $ | cons $ |
|---|---|---|---|---|---|---|
| #4 | haiku | off | 273 | 7 | 0.006 | 0.007 |
| #4 | haiku | on | 498 | 7 | 0.011 | 0.011 |
| #4 | sonnet | off | 273 | 7 | 0.018 | 0.021 |
| #4 | sonnet | on | 498 | 7 | 0.032 | 0.033 |
| #4 | opus | off | 386 | 7 | 0.042 | 0.046 |
| #4 | opus | on | 703 | 7 | 0.074 | 0.075 |
| #6 | haiku | off | 92 | 254 | 0.027 | 0.053 |
| #6 | haiku | on | 308 | 89 | 0.015 | 0.019 |
| #6 | sonnet | off | 92 | 314 | 0.100 | 0.194 |
| #6 | sonnet | on | 309 | 96 | 0.047 | 0.059 |
| #6 | opus | off | 140 | 299 | 0.164 | 0.313 |
| #6 | opus | on | 431 | 145 | 0.116 | 0.145 |
| #9 | haiku | off | 145 | 514 | 0.054 | 0.106 |
| #9 | haiku | on | 404 | 1067 | 0.115 | 0.157 |
| #9 | sonnet | off | 145 | 1039 | 0.320 | 0.632 |
| #9 | sonnet | on | 405 | 1065 | 0.344 | 0.472 |
| #9 | opus | off | 228 | 1083 | 0.564 | 1.106 |
| #9 | opus | on | 580 | 1697 | 0.906 | 1.246 |

## Notes / caveats

- Pilot output is a single sample per cell (a cost gate wants a conservative bound, not per-cell variance) — the conservative column inflates output to absorb N=1 sampling noise and the skill-off arm's higher, unconstrained spread. The real N=20 per-cell mean will sit near the point estimate.
- No call hit `max_tokens`/truncation in the pilot (all `end_turn`); max single output was the Opus #9 skill-on memo. Output is the cost driver; input is small and exactly measured.
- #4 output is a single label (~7 tokens, confirmed live = `P1_Critical`); its cost is input-dominated and negligible.
- **Recommendation:** the conservative bound ($4.69) is ~11× under the $50 provisional ceiling. Finalize `cost_ceiling_usd` in `runs/phase1c.yaml` to a value that preserves a safety margin over the conservative bound (proposed: **$15**).
