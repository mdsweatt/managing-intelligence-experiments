# Does the cap/mandate rule hold — and can we trust the ruler? — Phase 1d results

**Run:** `results/run-20260702T203102Z-f704f0/` (2026-07-02, 78 cells × N=20 = 1,560 calls) ·
**Judge:** frozen `gemini-3.1-pro-preview`, `judge_hash 5fd08ff3…`, graded 2026-07-03 via Batch API ·
**Human panel:** 144 blind labels + 65-row adjudication (owner, 2026-07-03) ·
**Charter:** v0.8 (H7/H8 pre-registered v0.7, 2026-06-29; labels frozen pre-data v0.8, 2026-07-02) ·
**Phase spend:** ≈ $49 of the $100 ceiling, verified against both provider meters (Δ ≤ 0.3%).

## TL;DR

1. **H7 — supported, 24/24.** The a-priori cap/mandate label predicted the *sign* of the skill's
   cost effect on every task × model cell: caps cut mean output −40…−72%, mandates raised it
   +12…+738%. 1c's post-hoc dissociation is now a confirmed rule: **a scaffold's determinism
   effect and its cost effect are separate, independently steerable levers.**
2. **H8 — supported.** A length-matched, structure-free system block reproduces essentially
   **none** of the skill's variance-tightening (median R = **−0.026** across 17 scored cells;
   15 < ⅓, 0 ambiguous, 2 isolated cell-level kills). The determinism lever is the **structure**,
   not "a system block is present." 1a's Lever A survives its placebo test.
3. **H5 re-test — variance half holds broadly** (CoV_output down in 17/24 generative cells,
   often 50–80%), with pre-registered-style honesty about the exceptions: #8 (all tiers) and
   #15-Sonnet got *noisier* with the skill on.
4. **H6 — no de-confounded verdict, and that is the headline finding.** The cross-family judge
   failed its pre-registered gold-standard check: **54.9% agreement with the blind owner panel
   (n=144, κ ≈ 0.04 — chance).** Every conclusion routed through its `faithful` gate — pairwise
   eligibility, the invention-rate story, the H5 quality floor — is **instrument-unvalidated**.
   1c's provisional H6 rejection stands, neither upgraded nor overturned.
5. **The failed ruler is a first-class result for managing intelligence.** A frozen, hashed,
   K=3-replicated LLM judge produced crisp, decisive-looking gates — and measured the owner's
   faithfulness construct no better than a coin flip. Adjudication of all 65 disagreements:
   **83% construct under-specification, 17% owner label slips, 0% judge misapplication.** The
   judge executed its frozen words consistently; *the words were the failure.*

## 1. What was run

- **Matrix (`runs/phase1d.yaml`, frozen pre-data):** 8 generative tasks × 3 models
  (Haiku 4.5 / Sonnet 4.6 / Opus 4.8) × 3 arms (skill-off / **neutral-system** / skill-on)
  + #4 exact-match placebo (2-arm) = 78 cells, flat N=20. Labels frozen in the matrix before
  the run: **caps** #1 email-reply, #6 short copy, #7 minutes-recap, #8 extract-fields;
  **mandates** #9 decision memo, #15 strategy brief (adaptive thinking, Sonnet/Opus),
  #23 spec-draft, #24 status report.
- **Controls:** everything frozen + hashed (fixtures, loose prompts, skills, neutral blocks,
  judge); temperature omitted; identical artifact bytes across models; neutral blocks
  length-matched to each task's skill (−2…−8% words) with structure/length cues stripped.
- **Generation run:** 1,560/1,560 records, all `end_turn`, 0 quarantined, single process,
  **$24.57 measured** (Console cross-check: 2,125,898 tokens, exact) —
  `analysis/output/phase1d-main-run-note.md`.
- **Judge run:** interactive path died on a Tier-1 250-requests/day quota; rerun as **Batch API
  jobs** with the instrument byte-identical (owner-approved operational deviation; equivalence
  contract-tested) — 4,869/4,869 calls parsed, zero retries, **$21.18 measured**, AI Studio meter
  reconciled to 0.3% — `analysis/output/phase1d-judge-run-note.md`.
- **Human panel:** 144-output stratified blind sample (2 per task × model × arm), owner-labeled
  on the `faithful` construct only; then a 65-row de-blinded adjudication of every disagreement.

## 2. Key findings

### 2.1 H7 — the cap/mandate label predicts the cost sign, 24/24 (`h7_sign.csv`)

Δ(mean output tokens), skill-on vs skill-off, per model:

| task (label) | Haiku | Sonnet | Opus |
|---|---:|---:|---:|
| #6 copy (cap) | −64% | −72% | −57% |
| #7 recap (cap) | −49% | −50% | −40% |
| #8 extract (cap) | −49% | −54% | −49% |
| #1 email (cap) | −40% | −52% | −50% |
| #9 memo (mandate) | +137% | +12% | +54% |
| #15 brief (mandate) | +414% | +306% | +86% |
| #23 spec (mandate) | +738% | +79% | +170% |
| #24 status (mandate) | +32% | +17% | +52% |

Every cap negative, every mandate positive, every model — the sign was called in advance from
`sign(scaffold demand − natural skill-off length)`, labels frozen before any N=20 data. The #4
placebo sat flat (exact-match ~100%, 7-token outputs), as designed. **Rule of thumb this buys:**
you can predict whether a skill will save or cost you money *before deploying it*, by comparing
its demand to the task's natural output length. 1c's surprise is now a planning tool.

### 2.2 H8 — the tightening is the structure, not the system block (`h8_neutral.csv`)

R = share of the skill's CoV reduction reproduced by the neutral block; scored only where the
skill itself cut CoV ≥25% (17/24 cells; R is unstable near the floor). **Median R = −0.026** —
the neutral arm sits on top of skill-off, not between off and on. 15/17 cells < ⅓ (supported),
0 ambiguous, 2 isolated kills (#1-Opus R=0.82, #24-Haiku R=0.74) — real heterogeneity, reported,
but nowhere near the pre-registered kill (≥½ *across* the high-latitude tasks). Priming is not
the mechanism; structure is.

**But the neutral block is not behaviorally inert** (descriptive, H8-adjacent): it *raised* mean
output on mandates (e.g. #9-Haiku 415→862 tokens), triggered adaptive thinking the bare prompt
did not (#15-Sonnet: 57→1,386 tok/call; skill-on 4,148; Opus non-monotone 2→881→101), and its
outputs were the most enrichment-laden in the human panel's disagreement set (25/65 rows). A
"be helpful and thorough" block changes *how much* the model writes — it just doesn't make the
output *repeatable*. Only structure does that.

### 2.3 H5 re-test — variance lever confirmed, with named exceptions (`h5_determinism.csv`)

CoV_output fell in 17/24 generative cells, frequently by 50–80% (e.g. #9-Opus 0.084→0.014,
#23-Opus 0.091→0.030). Exceptions, flagged not smoothed: **#8 extract-fields got noisier on all
three tiers** (Haiku 0.062→0.100) — a cap task whose scaffold *shortens* output but destabilizes
it; and **#15-Sonnet** (0.101→0.269), where the mandate + adaptive thinking interact. The 1c
split verdict ("determinism lever, not always cheaper") survives its de-confounded re-test, now
with H7 supplying the cost-direction rule and #8 standing as the open counterexample on the
variance side.

### 2.4 H6 and the ruler — the judge failed its gold-standard check

The de-confounding worked mechanically: the cross-family judge showed **no** pro-Claude-family
tie-breaking pattern and preferred Opus where the off-arm gap was open (#1-off: 13–2), removing
1c's self-preference confound. The format-neutral gate produced decisive-looking numbers:
183/480 pairs eligible; #6 eligibility off/neutral/on = 3/2/19 of 20; on-arm equivalence at
#1 (net preference 55% → 0%).

Then the pre-registered calibration ran: **owner blind panel, 144 items, agreement 54.9%,
κ ≈ 0.04** — statistically indistinguishable from ignoring each other. Misses were symmetric
(31 vs 34), and per-task agreement ranged from 15/18 (#1) to **5/18 (#9 — below chance)**.
Adjudication of all 65 disagreements (de-blinded, owner-classified): **54 construct** (the
frozen check text legitimately admits both readings — e.g. #6's literal "every claim supported"
vs a marketing-faithfulness reading; #23's "requirements can go either way"), **11 owner label
slips** (correcting them: 62.5%, κ ≈ 0.20 — still weak), **0 judge errors**. 59/65 disagreements
were judge-*unanimous* (3/3): the instrument was confident, consistent, and measuring a
different construct than its owner.

**Consequently:** H6 gets **no 1d verdict**. The eligibility-gated pairwise, the
"Haiku-invents-under-mandates" mechanism, and the H5 quality floor are all downgraded to
instrument-unvalidated observations. 1c's provisional rejection stands. What survives is the
method lesson: *crisp ≠ calibrated.* A hashed, replicated, unanimous judge can still be
measuring the wrong thing — and only a human panel can tell you.

## 3. What this means for managing intelligence

1. **Skills are a budgeting instrument, not just a quality one.** H7 makes the cost direction
   of a scaffold predictable a priori — like a training program where tempo work (caps) cuts
   session volume and forced extra sets (mandates) raise it, while both tighten form (variance).
   Cost-of-intelligence planning can price a skill *before* deployment.
2. **Buy determinism with structure, not vibes.** H8 kills the "any system prompt helps"
   hypothesis for variance: role/quality framing moved cost and thinking but produced zero
   repeatability. If the goal is bandable output, the scaffold must encode format, scope, and
   length — the things 1a's Lever A actually named.
3. **LLM-judge gates are unvalidated instruments until proven otherwise.** The most expensive
   lesson of 1d cost $21: every downstream "quality" number inherited the judge's construct,
   and the construct was fuzzy in exactly the place (elaboration vs invention) where all the
   interesting phenomena live. Calibrate the ruler against the task owner *before* freezing it —
   a ~$0.05 micro-pilot proved the plumbing but could never prove the construct.
4. **The un-validated observations are still leads:** weak-tier models elaborating confidently
   under big mandates, and neutral blocks inflating cost without buying repeatability, are both
   worth re-testing under a validated gate before they become claims.

## 4. Honest limits

- **Single human rater** (the owner) — the gold standard is one person's construct; symmetric
  misses suggest the construct itself is under-specified, so "judge wrong, human right" is not
  the claim. The claim is non-agreement.
- **S-band only, N=20, 8 tasks** — the ladder is wider than 1c's but still small-input; #13
  (research, high fan-out) was dropped pre-data and remains untested.
- **Preview judge model** pinned as a point-in-time snapshot; grading completed within one day,
  but the instrument is not reproducible after the preview retires.
- **Batch transport deviation** from the pre-registered interactive path — instrument bytes
  unchanged, equivalence contract-tested, owner-approved, fully logged
  (`analysis/output/phase1d-judge-run-note.md`).
- 22 records shared byte-identical outputs with a cell-mate (temperature-omitted determinism),
  so 1,418 distinct rubric prompts served 1,440 records — handled, noted.

## 5. Next steps

- **Inter-human agreement study (proposed 2026-07-04, owner).** The 1d panel has n=1 rater, so
  "the judge failed" and "the construct has no stable ground truth" are observationally
  identical. Before any judge re-instrumentation: 2–3 colleagues × ~30–40 blind items from the
  disagreement-dense strata (#6/#8/#9), same blinding protocol, measuring **inter-human κ**.
  Decision fork: humans agree with each other *and* the judge → the 1d check texts were fine and
  the owner construct drifted; agree with each other *and* the owner → the judge's construct is
  genuinely off, re-instrument (1e below); **don't agree with each other → the taste band is
  irreducible** → abandon the point-verdict gate and report pass-rate *bands* across 2–3 frozen
  rubric-strictness settings (sensitivity-of-verdict-to-construct as a first-class number).
  Evidence the mixture is non-trivial in both directions: per-task agreement ranged 17%–72% with
  the rater pair fixed (words are load-bearing), yet the owner's own #23 adjudication notes say
  "can go either way" (some irreducibility is real). **Known challenge, logged with the
  proposal:** for the knowledge-work tasks this ladder is built from — requirement decomposition
  (#23), strategic briefs (#15), status reporting (#24) — the reference reader is a *specific
  decision-maker*, and a good output is tailored to that principal's tastes and preferences.
  Quality may be **principal-relative**: a shared gold standard across raters might not exist
  even in principle, and any durable instrument may need a per-principal preference profile
  rather than one universal `faithful` line. The inter-human study is also the cheapest way to
  measure how large that principal-relativity term actually is.
- **If H6 still matters:** a Phase 1e that *starts* from the construct — operationalize
  `faithful` as enumerable claim-support (closer to #1's carve-out, which scored 15/18), build a
  small owner-labeled calibration set **first**, freeze a judge only after it clears an agreement
  bar (e.g. κ ≥ 0.6) on held-out items, then re-grade the existing 1d records (they're stored;
  re-grading is ~$21, no new generation needed).
- **If the product is the priority:** H7 + H8 + the 1a/1b variance map are already the
  provocation-tool assets — the cap/mandate rule is the single most communicable finding the
  project has produced. The H6 question can wait for a validated ruler.

## Reproduce it

```bash
# token-side analyses (free, local)
uv run python -m analysis.h7 results/run-20260702T203102Z-f704f0 --matrix runs/phase1d.yaml --out analysis/output/phase1d
uv run python -m analysis.h8 results/run-20260702T203102Z-f704f0 --out analysis/output/phase1d
uv run python -m analysis.h5 results/run-20260702T203102Z-f704f0 --out analysis/output/phase1d

# judge grading, batch transport (state-machine CLI; plan is free, step --go is billable)
uv run python -m analysis.judge_gemini_batch plan results/run-20260702T203102Z-f704f0
uv run python -m analysis.judge_gemini_batch step --go     # repeat until "run finalize"
uv run python -m analysis.judge_gemini_batch finalize

# human-panel agreement (after labeling quality_spotcheck.csv)
uv run python -c "from analysis.quality import compute_agreement; print(compute_agreement('analysis/output/phase1d/quality_spotcheck.csv','analysis/output/phase1d/quality_spotcheck_key.csv'))"
```
