# Phase 1d skill-off pilot — cost estimate (the billable gate)

**Date:** 2026-07-02 · **Matrix:** `runs/phase1d-pilot.yaml` (18 cells × N=10 = 180 calls, loose arm
only) · **Ceiling:** $10 hard (`--usd-prior 25` → 400k-token guard budget per stream) · **Prices:**
`prices/prices-2026-06.yaml` (live 2026-06-25).

**Estimate: $4.16 point / $5.98 conservative** — 2.4× / 1.7× margin under the $10 abort ceiling.

## Method (measure, don't estimate — invariant 1)

- **Inputs are measured exactly**: free `count_tokens` on each frozen fixture (prompt+input as
  assembled), both tokenizers, 2026-07-02 — now pinned in `fixtures/manifest-phase1d.yaml`
  `recorded_token_counts` (162–540 tok; input is <5% of the estimate).
- **Outputs are priors anchored on prior MEASUREMENT, labeled as priors** (replaced by this pilot's
  own data): short tasks (#1/#7/#8) anchor on the 1c loose-arm #6 cells (means 259–332, max 378);
  longer tasks (#23/#24, #15-Haiku) anchor on the 1c loose-arm #9 cells (Haiku 412, Sonnet 1,015,
  Opus 1,110, max 1,238); the two #15 thinking cells anchor on the **1a #15 thinking-on effort=high
  records** — the same config the 1d factorial runs — Sonnet mean 10,392 / max 14,752, Opus mean
  4,960 / max 6,630. Point = mean-anchored; conservative = max-anchored + headroom.

## Result (per cell, 10 calls each)

| cell | in tok | out (pt / cons) | cost pt | cost cons |
|---|---|---|---|---|
| #1 haiku/sonnet/opus | 162–216 | 300–330 / 500 | $0.16 | $0.24 |
| #7 haiku/sonnet/opus | 372–540 | 350–380 / 600–650 | $0.21 | $0.33 |
| #8 haiku/sonnet/opus | 262–378 | 250–270 / 450–470 | $0.15 | $0.24 |
| #15 haiku (thinking off) | 213 | 450 / 800 | $0.03 | $0.04 |
| **#15 sonnet (adaptive)** | 213 | **10,400 / 15,000** | **$1.57** | **$2.26** |
| **#15 opus (adaptive)** | 309 | **5,000 / 7,000** | **$1.27** | **$1.77** |
| #23 haiku/sonnet/opus | 308–469 | 450–1,100 / 700–1,500 | $0.48 | $0.66 |
| #24 haiku/sonnet/opus | 270–373 | 350–650 / 600–1,000 | $0.30 | $0.45 |
| **TOTAL (180 calls)** | | | **$4.16** | **$5.98** |

**The two #15 thinking cells are ~68% of the point cost** ($2.83 of $4.16) — expected: 1a already
showed thinking is the hottest cost axis, and the pilot must measure #15 under its real run config
(natural range under thinking is exactly the H7 label question for #15). Conservative output total
≈ 337k tokens vs the guard's 400k budget — the ceiling can actually catch a blowout, with the
`max_calls = 181` backstop behind it.

## Run command (after owner go)

    uv run python -m harness.run --matrix runs/phase1d-pilot.yaml \
        --manifest fixtures/manifest-phase1d.yaml --usd-prior 25 --out results/

Records land in `results/run-<ts>/` — a **design input only** (never H-data). Post-run: word-count
`response_text` per cell → natural ranges per model → tune scaffolds (explicit numeric cues) →
freeze labels in `runs/phase1d.yaml`.
