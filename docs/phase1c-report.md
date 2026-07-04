# Can a skill make a cheap model punch above its tier? — Phase 1c results

*Managing Intelligence · Experiment 1c (Determinism A/B) · run `run-20260628T051203Z-53aa02` · 2026-06-28*

> **The question.** Phase 1a proved *where* token-cost variance lives — 100% of it is in the output —
> and named two architectural levers to tame it. **Lever A** was "constrain the output (skills /
> scripts / schemas)," but 1a could only show it *correlationally*: pinned-output tasks happen to be
> tight. It never took one task and *tightened it on purpose*. Phase 1c is that causal test. It asks
> two things a frozen **skill** (a structured output scaffold, injected as a `system` block) might
> buy: **(H5)** lower output-token variance and/or cost, and **(H6)** *tier-agnostic quality* — can
> Haiku-with-a-skill match Opus? If yes, scaffolding substitutes for model tier, and "over-service"
> (paying for a bigger model than the task needs) becomes an architecture problem, not a fixed cost.

---

## TL;DR

- We ran a **2×3 factorial** — skill {off, on} × model {Haiku, Sonnet, Opus} — on three tasks
  (#4 classify, #6 short-form copy, #9 long-form draft), **N = 20/cell, 360 calls**, then graded the
  output with a **frozen, pre-registered quality judge**. The skill-off arm is a deliberately
  *natural* request, so a positive H5 measures **scaffolding, not prompt verbosity**.
- **H5 (determinism) — supported, but with a sharp split.** The skill reliably cuts output-token
  **variance** (CoV down ≥25% on 4 of 6 generative cells). But it only cuts **cost** on **short-form
  (#6)** — there mean output fell 57–72%. On **long-form (#9)** the scaffold *tightened* variance on
  **Sonnet/Opus** yet **raised** length (Opus +50%, Haiku +135%), because it mandates required
  sections — so on long work the skill buys **predictability, not cheapness.** The lone exception is
  **#9-Haiku**, which neither tightened *nor* shortened (the one cell that matches the H5
  kill-condition). The #4 placebo stayed flat (confound guard holds).
- **H6 (tier-agnostic quality) — rejected, as measured.** With the skill applied, a blind pairwise
  judge still preferred **Opus over Haiku 12–1** on #6 (net 55%, far outside the ±10-pp equivalence
  margin). On #9, scaffolded Haiku passed the rubric only **5%** of the time — it couldn't even hold
  the long-form structure to enter the comparison. **Tier still buys quality — and appears to matter
  *more* on the harder task** (scaffolded Haiku can't hold the long-form structure well enough to be
  compared at all).
- **Two caveats keep that rejection provisional.** (1) The judge **is Opus 4.8**, so same-family
  **self-preference** plausibly inflates the 12–1 — and to a human eye the #6 Haiku and Opus posts
  look *close*. (2) The format rubric encodes the *skill's own* structure, so skill-off failing it is
  partly **definitional**, not a pure quality gap. A human spot-check (24 blinded items) is the
  pending tie-breaker. **We are not yet closing H6 — we're reporting where the instrument landed.**
- **The shape of the answer:** a skill is a **determinism-and-format lever, not a tier-substitution
  lever.** It makes a cheap model *more consistent and better-formatted*; it does not make it *as
  good*. That is genuinely useful — and it is the opposite of the strong over-service hope.

---

## 1. What was run

The unit is a **cell**: one task, one model, one skill arm, N = 20 identical runs. The design crosses
two axes on purpose — this is a **causal factorial**, not 1a's one-axis-at-a-time variance map —
because each pairwise contrast still isolates one axis (skill at fixed model; model at fixed skill),
and the **skill × tier interaction is exactly the H6 object**.

| | |
|---|---|
| **Design** | 2×3 factorial: skill {off, on} × model {Haiku, Sonnet, Opus} |
| **Tasks** | #4 classify/triage (**placebo** — already ~0% CoV), #6 short-form copy, #9 long-form draft |
| **Cells** | 18 (3 tasks × 3 models × 2 arms) · **N = 20**, flat, pre-committed |
| **Records** | 360 captured · **0 quarantined** · all `end_turn` (no truncation) |
| **Models** | Haiku 4.5 (`claude-haiku-4-5-20251001`), Sonnet 4.6 (`claude-sonnet-4-6`), Opus 4.8 (`claude-opus-4-8`) |
| **Load** | input 118,180 tok · output 149,923 tok · thinking **off** in 1c |
| **Spend** | **$2.94 measured** (Haiku $0.21 · Sonnet $0.85 · Opus $1.88), vs a $4.69 conservative bound and a **$15** hard ceiling |
| **Wall-clock** | ≈ 46 min (sequential) |
| **Provenance** | Each record carries config hash, fixture hash, and — on the skill-on arm — the frozen `skill_hash`; replays from the record alone. The Load/Spend aggregates above are computed from `records.jsonl`. |

**The two arms (calibrated-loose baseline).** *Skill-off* is a **natural user request** — the
structure lives in the skill, not the prompt — so a positive H5 measures the scaffold, not a longer
prompt. *Skill-on* injects a frozen, hashed scaffold (output schema/format + scope/length caps) as a
`system` block, **identical across all three models** (never tuned per model). #6/#9 reuse the frozen
Phase-1a input verbatim; **#4 is a mixed placebo** — it keeps its constrained classification prompt,
and its "skill" is a redundant procedure that should move nothing.

**The quality judge** is a frozen, pre-registered instrument (`docs/phase1c-judge-spec.md`):
**Opus 4.8**, **K = 3** replicate judgments with a 2/3 majority/agreement floor, a per-task rubric,
and a **blind, order-randomized pairwise** preference test run **only on rubric-passing pairs**. Its
model + rubric + prompts are hashed (`judge_hash d12c36a2…`) and were pinned **before any grading
data existed**.

## 2. How it was run

Same discipline as 1a — **measure, don't estimate**; full usage vector per call; tokens stored,
dollars applied only at analysis time; frozen, hash-pinned fixtures and skills. Three things are
specific to 1c, and **two are pre-registered departures from 1a's rules**, declared rather than
silently reconciled (charter v0.6):

- **Two-axis factorial** (vs 1a's one-axis-at-a-time) — sound for *causal* attribution, as above.
- **Output text is persisted** (`response_text`) on the factorial cells, so the judge can grade
  quality — the cost-only 1a/1b records stay tokens-only.
- **Read H5 on the output component only,** never the composite: the skill's fixed ~250–400-token
  `system` block would otherwise deflate composite CoV mechanically (1a's "Lever B") and counterfeit
  an H5 win. So H5 = `CoV_output` + mean output tokens, skill-off vs skill-on, same model.

> **One honest operational note.** The 360-call generation run is guarded by the $15 ceiling. The
> downstream **judge is not** — it builds a bare client with no spend guard. Its volume is bounded by
> the dataset (≤ ~960 calls — the actual run made 783), so exposure is **~$8–10** (against a ≤$13
> pre-run bound), not open-ended — but the judge's own token spend was **not persisted** (it writes
> verdict CSVs only), an instrument-cost gap to close.

## 3. Key findings

### 3.1 H5 — the skill cuts variance everywhere it bites, but cuts *cost* only on short work

For each (task, model) we compared `CoV_output` and mean output tokens across the two arms. The
pre-registered win condition (judge-spec §4): **skill-on lowers `CoV_output` by ≥ 25% relative AND
does not raise mean output.**

| Task | Model | mean off → on | Δ mean | CoV off → on | CoV rel. ↓ | H5 win |
|---|---|---|---|---|---|---|
| #4 placebo | all | 7–8 → 7–8 | +0% | 0.00 → 0.00 | — | flat ✓ (guard holds) |
| **#6** short | Haiku | 259 → 91 | **−65%** | .138 → .049 | **−64%** | **yes** |
| #6 | Opus | 332 → 143 | **−57%** | .065 → .018 | **−72%** | **yes** |
| #6 | Sonnet | 332 → 95 | **−72%** | .052 → .040 | −22% | no (missed 25% bar; CoV near floor) |
| **#9** long | Haiku | 412 → **967** | **+135%** | .067 → .069 | −3% | no |
| #9 | Sonnet | 1015 → 1034 | +2% | .085 → .036 | **−57%** | no (mean not cut) |
| #9 | Opus | 1110 → **1665** | **+50%** | .075 → .024 | **−68%** | no (mean not cut) |

The strict conjunction passes on **2/6** generative cells (#6-Haiku/Opus). But that undersells the
variance result: **CoV fell ≥25% on 4/6** cells. What knocks #9 out of the *strict* win isn't
variance — it's that the long-form scaffold **raises length**. Lever A is therefore **causally real
for variance**, and for *cost* on short-form; the 1a correlation was not a coincidence.

### 3.2 The dissociation: a scaffold tightens *and* lengthens long work

The cleanest finding is the split between #6 and #9. The short-form skill caps a sprawling task —
fewer tokens, far less spread. The long-form skill **mandates required sections** (recommendation,
background, options, cost, risks, next steps), so each draft is **more consistent but longer**:
Opus's #9 output grew +50% with the skill while its variance fell 68%. For long, structured work the
honest reading is: **the skill buys predictability, not a smaller bill.** "Determinism" and
"efficiency" are not the same lever, and 1c pulls them apart.

(The one true miss is **#9-Haiku**: +135% length and *no* variance reduction. Haiku follows the
long-form scaffold expansively and inconsistently — it is the cell that matches the H5 kill-condition,
and, not coincidentally, the cell where H6 fails hardest below.)

### 3.3 H6 — the skill lifts format compliance hard, but does not close the quality gap

Two graders speak to quality. First, the **absolute rubric** (objective format checks in code +
semantic checks by the judge). The skill's effect here is dramatic:

| | skill-off pass-rate | skill-on pass-rate |
|---|---|---|
| #4 placebo (exact-match) | 100% | 100% |
| #6 short — Haiku / Sonnet / Opus | 0% / 0% / 0% | **100% / 90% / 100%** |
| #9 long — Haiku / Sonnet / Opus | 0% / 0% / 0% | **5% / 50% / 100%** |

Skill-on outputs pass; skill-off outputs almost never do — *but read that honestly* (§5): the rubric
encodes the **skill's own** required format, so a natural request fails it largely **by definition**.
The semantic hook score (a less circular signal) tells the real lift: #6 hook rose 1.3–1.95 (off) →
2.0 (on). The skill genuinely improves the writing; it also defines the test it passes.

Second — and this is the H6 verdict — the **blind pairwise** preference, Haiku vs Opus, on
rubric-passing pairs only:

| Task | Arm | eligible pairs | Haiku wins | Opus wins | ties | net-pref | equivalent? |
|---|---|---|---|---|---|---|---|
| #6 | skill-on | 20 | 1 | **12** | 7 | 55% | **no** |
| #6 | skill-off | 0 | — | — | — | (100% excluded) | — |
| #9 | skill-on | 1 | 0 | 1 | 0 | (95% excluded) | — |
| #9 | skill-off | 0 | — | — | — | (100% excluded) | — |

*Only rubric-passing outputs are eligible for the blind preference test. Skill-off fails the format
rubric ~100% of the time and #9-Haiku-on fails it 95% of the time — so those rows have too few
eligible pairs to judge (the "excluded" share is the coverage caveat).*

On the one cleanly-measured cell (#6, skill-on), **Opus is preferred 12–1** — net preference 55%,
far outside the ±10-pp equivalence margin. The H6 kill-condition ("Haiku-with-skill fails equivalence
vs Opus-with-skill beyond the margin") is **met**. On #9, scaffolded Haiku passes the long-form rubric
only 5% of the time, so 95% of pairs are excluded and the comparison rests on a single pair — H6 is
**not even assessable** there, which is itself the finding: tier matters *more* on the harder task.

### 3.4 Read the H6 rejection honestly — it is provisional

The rejection is real on the instrument's terms, but two confounds keep it from being the final word:

- **The judge is Opus 4.8.** Same-family **self-preference** is a known bias and it points *against*
  H6 — it would inflate the 12–1. The judge-spec acknowledges this as "conservative," but here it is
  load-bearing. To a human reading the 20 #6 pairs side-by-side
  ([`analysis/output/phase1c_6_haiku_vs_opus.md`](../analysis/output/phase1c_6_haiku_vs_opus.md)),
  the Haiku and Opus posts look **close** — same hook/body/CTA/hashtag structure, Opus a touch
  punchier. That is the pattern of a mild register preference, not a quality chasm. The pending
  **24-item blinded human spot-check** is the tie-breaker.
- **No skill-off pairwise baseline.** Because skill-off yields *zero* rubric-passing pairs, H6's
  *second* clause — does the skill **narrow** the Haiku→Opus gap *more than* the loose prompt? — is
  **unanswerable from this design.** We can say the gap is open *with* the skill; we cannot compare it
  to the gap *without* one. That's a design gap, not a result.

## 4. What this means for managing intelligence

- **A skill is a determinism-and-cost lever, not a tier-substitution lever.** Phase 1a reframed
  "specialized skills" from a quality story into a predictability story; 1c **confirms the
  predictability half causally** (variance falls) and **refutes the tier-substitution half** (a
  scaffolded Haiku still loses to Opus). Scaffolding moves a task from "meter it" toward "budget it";
  it does not move it down a model tier.
- **Determinism ≠ efficiency on long work.** The most actionable surprise: a scaffold that tightens a
  long task's variance can *raise* its token bill. If the goal is a predictable budget, the skill
  helps; if the goal is a *smaller* budget, on long-form it can backfire. Measure both — they diverge.
- **Over-service is not (yet) an architecture problem you can skill your way out of.** The strong hope
  — "scaffold a cheap model and stop paying for Opus" — does **not** hold on this evidence for quality.
  It holds for *consistency*. Where quality rests on latent capability (longer, less templated work),
  tier still buys something a frozen scaffold cannot supply.

## 5. Honest limits

- **H6's verdict is provisional.** The judge is same-family as one arm (self-preference, §3.4), the
  human spot-check is **not yet done**, and the format rubric is partly circular. We report H6 as
  *rejected on the instrument*, not as settled.
- **The "narrows the gap" clause is untested.** Skill-off has no rubric-passing pairs, so there is no
  loose-prompt pairwise baseline to beat (§3.4). A future arm needs to fix this.
- **Lean design, by pre-registration.** One frozen instance per task (no within-task generalization),
  a **bundled** skill (format + scope + length together — no mechanism ablation telling us *which*
  part does the work), and **no neutral-system control** (so part of any effect could be "a system
  block was present" rather than "*this* scaffold"). #9-Haiku's failure is one instance, not a law.
- **Instrument-cost not measured.** The judge's own token spend wasn't persisted (~$8–10 estimated
  from the 783-call volume; ≤$13 pre-run bound), and it ran unguarded — bounded by the dataset, but a
  gap to close.
- **One snapshot.** N = 20, June-2026 models and prices, three tasks. A point-in-time prior.

We are **not** claiming "skills replace big models" — nor the opposite. We're claiming something
narrower: *a frozen skill makes a cheaper model measurably more consistent and better-formatted, and
on short work cheaper too — but, on this evidence, not as good; the quality gap is widest exactly
where the task is hardest.*

## 6. Next steps

1. **Close H6 with the human spot-check.** Grade the 24 blinded items
   (`analysis/output/quality_spotcheck.csv`) and compare to the judge — the direct test of whether the
   12–1 is real or Opus flattering its own tier. Populate the per-item `llm_pass` so the comparison is
   item-by-item, not just stratum-level.
2. **A 1d that fixes the design gaps.** Add a **neutral-system control arm** (system block present, no
  scaffold) to separate "structure" from "any system text"; a **skill-off pairwise baseline** (judge
  loose-vs-loose) so H6's "narrows the gap" clause becomes answerable; and a **cross-family judge**
  (or human panel) to neutralize self-preference.
3. **Explain #9-Haiku.** Read why scaffolded Haiku misses the long-form rubric 95% of the time — is it
  dropping required sections, or over-running length? That distinguishes "weak model" from "rubric too
  strict," and it's the crux of the harder-task-tier-gap claim.

*(Pre-registration is in [`docs/charter.md`](charter.md) §0 state-note 2026-06-28 + §3 H5/H6; nothing
in this report alters a hypothesis or kill-condition.)*

---

## Reproduce it

```bash
# H5 token side — per-(task,model,arm) CoV_output + mean output, with the on/off contrast
uv run python -m analysis.h5 results/run-20260628T051203Z-53aa02

# H6 quality — deterministic graders + the frozen LLM judge (billable Opus; ~$9-13)
uv run python -m analysis.quality results/run-20260628T051203Z-53aa02 \
  --judge-manifest fixtures/judge/manifest.yaml \
  --phase1c-manifest fixtures/manifest-phase1c.yaml \
  --run-judge --k 3 --seed phase1c
```

H5 per-cell: [`analysis/output/h5_determinism.csv`](../analysis/output/h5_determinism.csv) ·
quality: [`analysis/output/quality-findings.md`](../analysis/output/quality-findings.md),
[`quality_rubric.csv`](../analysis/output/quality_rubric.csv),
[`quality_pairwise.csv`](../analysis/output/quality_pairwise.csv) ·
the #6 side-by-side read: [`phase1c_6_haiku_vs_opus.md`](../analysis/output/phase1c_6_haiku_vs_opus.md) ·
methodology + pre-registration: [`docs/charter.md`](charter.md), [`docs/phase1c-judge-spec.md`](phase1c-judge-spec.md).
