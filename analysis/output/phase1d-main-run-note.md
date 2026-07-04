# Phase 1d main generation run — run note (billable gate 2 EXECUTED)

**Run:** `results/run-20260702T203102Z-f704f0/` (2026-07-02) · **Matrix:** `runs/phase1d.yaml`
(charter v0.8, frozen through e7dac42) · **These records ARE H-data** (H7/H8 + H5/H6 re-test).
This note records run facts and capture checks only — no hypothesis analysis here.

## Verification (all pass)

- **1,560 / 1,560 records**, exit 0, single uninterrupted process — no resume, no restart.
- **stop_reason:** `end_turn` on all 1,560. **Quarantined: 0.**
- **78 distinct cells, every cell exactly N=20** (pre-committed flat N). Arm split:
  27 off / 27 on / 24 neutral cells (540 / 540 / 480 records).
- **Pre-flight:** 280-test suite green; `--dry-run` expanded exactly 78 units / 1,560 calls
  before any spend.
- **Frozen-artifact stamps spot-checked live:** on-arm records carry the pinned `skill_hash`;
  neutral-arm records carry the neutral block's manifest sha256 (verified against
  `fixtures/neutral/manifest.yaml`, e.g. `short-form-copy-neutral-v2` → `c7a93b18…`, exact match).
- **Thinking capture:** `thinking_tokens` present and nonzero **only** on #15 Sonnet/Opus
  records — exactly the cells configured `thinking: adaptive`. Config integrity holds.

## Measured cost + tokens (Console cross-check basis)

Prices applied at analysis time only (`prices/prices-2026-06.yaml`, same path as the pilot's
Console-exact $2.09 via `analysis.h1.record_cost`). Raw records store tokens only.

| model | input | output | thinking (within output) | cost |
|---|---:|---:|---:|---:|
| claude-haiku-4-5-20251001 | 223,060 | 337,408 | 0 | $1.91 |
| claude-sonnet-4-6 | 223,400 | 519,869 | 111,826 | $8.47 |
| claude-opus-4-8 | 318,320 | 503,841 | 19,680 | $14.19 |
| **total** | **764,780** | **1,361,118** | **131,506** | **$24.57** |

- **Console cross-check total (input + output): 2,125,898 tokens.** Cache read/write: 0 (no
  cache-heavy cells in this matrix).
- **$24.57 measured** vs S6 estimate $21 point / $30 conservative / **$100 ceiling** (4.1×
  margin). Overage vs point is fully attributable to #15 adaptive thinking (below).

## Descriptive finding — adaptive thinking responds to the system-block arm

The pilot (skill-off only) saw #15 adaptive thinking spend 0–62 tok/call; the S6 estimate
carried a +500 tok/call prior on #15 Sonnet/Opus arms. Measured per-arm means (tok/call, n=20):

| model | off | neutral | on |
|---|---:|---:|---:|
| sonnet | 57 | 1,386 | 4,148 |
| opus | 2 | 881 | 101 |

Adaptive thinking is demand-driven and the **arm itself changes the demand** — the skill
scaffold (and even the neutral block) can trigger thinking the bare prompt does not, and the
direction is not monotone across tiers (Sonnet peaks on-arm, Opus on neutral). Capture is
legitimate (charter's "present thinking_tokens: 0" schema case), config unchanged. **Flagged
for the analysis phase, not acted on** (pre-registration discipline): thinking tokens are part
of the output-side cost vector that H5/H7 already score; no hypothesis or kill-condition is
being touched.

## Gate status

- **Gate 2 (this run): DONE.** Records committed with this note.
- **Gate 3 (judge run): NOT started** — owner flag required. Frozen judge
  (`docs/phase1d-judge-spec.md`, judge_hash `5fd08ff3…`) on the metered Gemini key,
  **≤ ~$56 upper bound** (rubric 4,320 calls ≈ $40; pairwise ≤ 1,440 ≈ $16, shrinking with
  measured eligibility) per `analysis/output/phase1d-cost-estimate.md`.
