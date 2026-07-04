# Phase 1d — frozen judge spec (the cross-family "honest ruler")

**Status:** FROZEN 2026-07-02 · **judge_hash:** `5fd08ff3287cbd32e3f6bbec923a9398ae9bc59143860eab90abbc73632d0e81`
**Instrument:** `fixtures/judge/manifest-phase1d.yaml` (the hashed source of truth; this doc is the
human-readable contract, peer of `docs/phase1c-judge-spec.md`). Charter v0.7 §5 "Experiment 1d",
§5.147 (format-neutral rubric). **Never edit bytes under this hash — revise by cutting a new
instrument.**

## 1. Identity

- **Provider/model:** `gemini` / `gemini-3.1-pro-preview` — cross-family by design (the 1c judge was
  Opus 4.8, same family as one arm; self-preference logged provisionally 2026-06-28). Preview build
  pinned deliberately: 1d is a point-in-time snapshot; the GA fallback (2.5-pro) was probed and is
  costlier/looser. Both `provider` and `judge_config` are folded into `judge_hash`.
- **Call config (pinned):** `thinking_budget: 256` (SOFT — measured 306–547 thinking tok/call on
  real rubric prompts; cost is projected from measurement, not the budget), `temperature: 0`,
  `max_output_tokens: 2048`. Client: `google-genai`, metered `GEMINI_API_KEY`; every attempt's
  `usage_metadata` persisted (0-on-error rejected).
- **Protocol (unchanged from 1c):** K=3 replicate majority; <2/3 agreement ⇒ `low_confidence`
  (never silently averaged); blind order-randomized Haiku-vs-Opus pairwise at matched run index;
  **margin_pp = 10** (the H6 kill-condition margin, frozen since 1c).

## 2. The format-neutral gate (what changed vs 1c)

Pairwise eligibility is gated ONLY by the rubric check tagged `gate: true` — **`faithful`** on every
generative task. Format compliance (the manifest-declared `code_checks`: word caps/ranges, section
presence, requirement/AC counts) is scored and reported per arm but NEVER gates — so a faithful,
format-noncompliant loose output stays eligible, closing 1c's coverage hole (0 eligible skill-off
pairs ⇒ H6 clause 2 untestable). `absolute_pass` (format-inclusive) is still reported as the H5
quality floor. The three mandate tasks' faithful text explicitly rules that *reasoned elaboration ≠
invention* (S2 review decision); #1's rules that the reply's own forward commitments are content,
not inventions (micro-pilot fix, §4).

## 3. Coverage of the 8-task ladder

Per-task LLM checks (semantic; `faithful` + 1–2 quality checks) + `code_checks` (objective; graded
in code, hashed in the manifest) for #1/#7/#8/#15/#23/#24; #6/#9 keep their 1c check text and
legacy in-code checks byte-unchanged (1c is never reinterpreted). #4 = exact-match placebo, no LLM.
The `code_checks` numbers equal the frozen scaffolds' pilot-tuned cues exactly.

## 4. Micro-pilot record (2026-07-02 — the freeze gate)

6 metered calls (5 rubric + 1 pairwise) on **real pilot outputs** with the real instrument:
`analysis/output/phase1d-judge-micropilot-usage.jsonl`, total 10,769 tokens = **$0.049**.

- **Live surface re-verified:** `thinking_budget` accepted; verdict JSON parsed with the correct
  check ids on 6/6; pairwise returned a valid preference. (The micro-pilot calls are themselves the
  "verify live" evidence — no separate probe.)
- **One instrument incoherence caught and fixed pre-freeze:** #1's faithful originally banned
  "invented refund timelines" while the #1 *skill* demands "one clear next step with a timeframe" —
  the gate punished what the treatment requires (observed: a good Opus loose reply failed on its own
  forward commitments). Re-scoped before pinning the hash.
- **Observed fail-rates, logged as a pre-registered caveat:** with the fixed #1 text still untested
  at N, `faithful` failed 2/5 single-replicate reads (#15-, #23-Sonnet loose — both plausibly honest:
  long-form loose output inventing specifics is real signal, and K=3 majority governs the recorded
  verdict). **If loose-arm eligibility collapses at scale, that is a substantive quality finding to
  report (invention rates by arm), not the 1c definitional hole — but the coverage limitation must
  be stated in the H6 read.**

## 5. Cost projection (from measured usage; prices live 2026-07-02)

`gemini-3.1-pro-preview` paid tier: $2/M input, $12/M output *including thinking* (≤200k prompts).
Measured per-call means (real prompts): rubric ≈1,370 in / 460 out+think; pairwise ≈ larger inputs
(two responses). Projection for the full post-run grading: **rubric 4,320 calls ≈ $40; pairwise
≤1,440 calls ≈ $16 ⇒ ≤ ~$56 upper bound** (pairwise shrinks with eligibility). Runs under the $100
Phase-1d ceiling alongside the generation run; usage persisted to `judge_usage.jsonl`; flagged to
the owner before running (billable gate 3).

## 6. Pending

The stratified **human panel** (spot-check export → human labels → `compute_agreement`) validates
this judge after grading — the gold-standard check 1c deferred. Human agreement on `faithful`
verdicts is the priority given §4's caveat.
