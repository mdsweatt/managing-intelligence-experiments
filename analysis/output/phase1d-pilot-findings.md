# Phase 1d skill-off pilot — natural-range findings (design spine S3)

**Run:** `results/run-20260702T133840Z-64d579/` (2026-07-02, 180/180 records, all `end_turn`,
0 quarantined) · **Measured cost: $2.09** vs $4.16 point / $5.98 conservative / $10 ceiling.
**Independent meter check (owner, Claude Console, 2026-07-02):** Console reports $2.09 and
**165,841 total tokens**; the records sum to input 54,590 + output 111,251 = **165,841 — exact
match, delta 0**. The harness capture and the provider's own meter agree to the token.
**These records are a DESIGN input only** (never H-data). Words measured from `response_text`
(tokenizer-independent, per the locked classification rule).

## Why cost halved: the adaptive-zero finding

The #15 Sonnet/Opus cells ran `thinking: adaptive` as configured — the component was captured on
every record — but the model spent only **0–62 thinking tokens per call** (vs the 1a #15 anchor of
~5k–10k at effort=high on the *1a* brief). Adaptive thinking is demand-driven: this S-band brief
didn't trigger it. Legitimate capture (the schema's "present thinking_tokens: 0" case), config
unchanged; noted as a descriptive finding — thinking cost is prompt-contingent, not config-fixed.

## Natural loose output in WORDS (N=10 per cell)

| task | haiku (min–max, mean) | sonnet (min–max, mean) | opus (min–max, mean) |
|---|---|---|---|
| #1 email_reply | 125–197, **166** | 183–261, **224** | 151–217, **176** |
| #7 minutes_recap | 137–179, **153** | 176–233, **201** | 130–154, **142** |
| #8 extract_fields | 118–170, **146** | 160–182, **169** | 156–166, **162** |
| #15 strategy_brief_1d | 258–304, **273** | 866–1139, **986** | 643–934, **764** |
| #23 spec_draft | 311–417, **368** | 931–1158, **1034** | 464–529, **492** |
| #24 status_report | 180–236, **209** | 351–432, **384** | 223–256, **238** |

Descriptive note: **Sonnet is systematically the most verbose** on every task (consistent with the
1c #9-Sonnet pattern) — it is Sonnet's natural ceiling that any MANDATE demand must clear.

## Label read (against the locked rule: demand clearly outside the range on ALL three models)

**Caps are clean.** Ladder-wide natural minimum per task: #1 = 125w, #7 = 130w, #8 = 118w. A cap
cue of **#1 ≤100w · #7 ≤100w · #8 ≤90w** sits clearly below every model's minimum (and 30–55%
below the means). → freeze CAP.

**Mandates as drafted are mixed** — scaffold-compliant output under the current (number-free)
scaffolds ≈ 350–450w (#15), 600–800w (#23), 250–350w (#24), which lands ABOVE Haiku's natural but
INSIDE/BELOW Sonnet's on all three tasks. Gemini's #15 inversion warning was right in direction,
for Sonnet/Opus. The pre-committed decision rule (build-notes "S2 + neutral-block review") says:
raise the demand with an explicit floor, re-check against the measured range, else flag/exclude.

**Proposed numeric cues (the #9 precedent: its frozen 800w mandate sits +15% over its measured
696w natural max):**

| task | label | proposed cue | vs natural max | vs highest mean |
|---|---|---|---|---|
| #1 | CAP | ≤ 100 words | −20% (min 125) | −55% |
| #7 | CAP | ≤ 100 words | −23% (min 130) | −50% |
| #8 | CAP | ≤ 90 words | −24% (min 118) | −47% |
| #15 | MANDATE | ~1,400 words (±10%) | +23% over 1,139 | +42% |
| #23 | MANDATE | ≥12 requirements, ≥3 acceptance criteria each, ~1,450 words (±10%) | +25% over 1,158 | +40% |
| #24 | MANDATE | ~550 words (±10%) + per-item elaboration (impact + plan per risk) | +27% over 432 | +43% |

Anti-invention tension on the mandates (raised at the S2 review) stands: the cues demand
**elaboration** (depth per section/requirement/risk), the scaffolds' faithfulness lines stay, and
the judge's `faithful` gate polices the difference. Haiku may fail to hold the raised mandates —
that is the pre-registered **capability floor** (H7 prediction; cf. 1c #9-Haiku), not a design flaw.

## Next (non-billable): apply cues to the six scaffolds → owner + Gemini review → freeze skills,
neutral blocks (length-matched to final scaffolds), labels + matrix in `runs/phase1d.yaml`, judge
`code_checks` numbers aligned at FREEZE.
