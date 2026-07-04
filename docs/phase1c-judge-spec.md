# Phase 1c — Quality-Judge Specification (pre-registration)

**Status:** FROZEN v1.0 — 2026-06-28 — **owner-reviewed · live-verified · `judge_hash` pinned.** (v1.0 freeze: wrote the two prompt templates [`fixtures/judge/`], verified the Opus 4.8 judge-call surface live [`docs/live-verification-judge-2026-06-28.md`], computed + pinned `judge_hash`. v0.3, post-Gemini-review: pairwise runs only on rubric-passing pairs [format-bias fix]; graded hook score for #6; #4 gold rationale + logged dissent; calibrated-loose baseline + mixed-#4 design note. v0.2: pinned #4 gold = P1_Critical, the ≤10-pp H6 margin, the H5 output-component metric + ≥25%-relative threshold; sharpened pairwise to substance; §5 caveats. v0.1: initial draft.)
**Relationship:** Operationalizes the H6 quality-equivalence claim and the H5 quality-floor for the determinism A/B (`docs/charter.md` §3 H5/H6; SPEC §3b). This judge is a **frozen, pre-registered instrument** — its model + rubric + prompts are version-stamped and hashed (`judge_hash`, §2) before any judging data exists, exactly like a fixture, so the grading replays from the records. **FROZEN 2026-06-28: grading may now proceed** (it was gated until this doc was reviewed + frozen).

This exists because the cost harness measures tokens exactly but cannot say "Haiku does it *identically*" (charter §5; charter.md:103). The judge supplies that missing quality axis — and nothing more.

---

## 0. What the judge must answer

- **H5 quality-floor** — within a model, does the skill-on output stay at least as good as skill-off? (A skill that cuts tokens by wrecking quality is not a win.)
- **H6 tier-equivalence** — with the skill on, is **Haiku** output quality-equivalent to **Opus** on the same task, and does the skill **narrow** the skill-off Haiku→Opus gap?

The headline H6 statistic is the **Haiku-vs-Opus quality gap, skill-off minus skill-on**, per task.

**Design note (calibrated-loose baseline; mixed #4).** For #6/#9 the skill-off arm is a *natural user request* (e.g. "Write a LinkedIn post announcing the product below") and the **skill supplies the structure** — so H5 tests *scaffolding beyond a normal prompt*, not prompt verbosity (the Gemini-review fix). **#4 is mixed:** classification needs its P1–P4 definitions to be a valid task, so #4's baseline is its *frozen Phase-1a constrained prompt* and its skill is a redundant procedure — a true placebo (should change nothing). Fixtures: `fixtures/manifest-phase1c.yaml`.

---

## 1. Graders by task (frozen)

### #4 classify_triage — deterministic exact-match (no LLM-judge)
- **Baseline:** #4's skill-off arm is the **frozen Phase-1a constrained prompt** (it carries the P1–P4 label set + definitions the task needs); the skill is a redundant procedure. Placebo prediction: **no change** in tokens or label.
- **Pinned gold label: `P1_Critical`** (owner decision, 2026-06-27). The frozen S ticket ("Cannot export monthly invoices to CSV"; finance blocked, month-end close tomorrow, stated workarounds failed). **Rationale:** the prompt's P1 definition fires on *"full work stoppage **and** no workaround"* independent of deadline timing — the ticket says "we are blocked" with failed workarounds — so P1 holds via the work-stoppage clause even if "tomorrow" reads as "near-term." **Logged dissent:** an independent Gemini review argued for `P2_High`, reading only the deadline clause ("tomorrow" = not same-day); it overlooked the work-stoppage clause. The ambiguity is real — hence the explicit pin, **not revisited against the data** (pre-registration). Phase 1a's 0.0% CoV on #4 proves only that the model was *consistent*, not which label (output wasn't stored), so it does not settle this.
- Grade = exact string match of the model's single-label output to gold. Objective and free. Quality here is binary-correct; the placebo prediction is that the skill moves neither tokens nor correctness. (If the models split P1/P2 *between* tiers, that is a between-model correctness note, not a within-cell variance effect — report it, don't let it masquerade as H5.)

### #6 short_form_copy & #9 long_form_draft — frozen rubric + blind pairwise
Two complementary measurements per output (both LLM-judged with the frozen judge below):

**(a) Absolute rubric — binary compliance + faithfulness** (the H5 quality-floor). Each check is pass/fail; report the per-output pass-count.

*#6 short-form copy:*
1. ≤ 60 words.
2. Exactly one call to action inviting a demo.
3. 2–3 hashtags present.
4. Opens with a distinct one-line hook (line 1 is a hook, not body). **Hook quality** is *additionally* scored **0–2** (0 = generic/absent, 1 = present-but-weak, 2 = sharp) as a **graded sensitivity floor** — the binary checks saturate once both models obey the skill, so the graded hook score is what keeps #6's quality floor discriminating (Gemini-review NICE-TO-HAVE).
5. **Faithfulness:** every product claim is supported by the blurb; nothing invented.

*#9 long-form memo:*
1. All required sections present (Recommendation, Background, Options Considered, Cost & Budget, Risks, Next Steps).
2. A single explicit recommendation stated up front (one line).
3. Length in 720–880 words (~800 ±10%).
4. **Faithfulness:** no invented vendor names or dollar figures beyond the brief.

(Checks 1/3 for #6 and #9 are computable deterministically — word counts, section regex — and are done in code, not by the LLM, to remove judge noise from the objective parts. The LLM judges only the semantic checks: hook quality, CTA validity, faithfulness, single-recommendation.)

**(b) Blind pairwise preference** (the H6 tier-equivalence). For each (task, skill-arm), pair a **Haiku** output with an **Opus** output (matched run index), present both **blind** with **order randomized** (label A/B, not model names), and ask the judge: *which is the better response to the task, or tie?* The judge must score **substance, not polish** — for the memo: is the recommendation well-reasoned, even-handed across options, and faithful to the brief; for the copy: is it sharp, on-message, and faithful to the blurb. **Format is not a discriminator here:** under the skill both models satisfy the format checks, so a fixed-format prompt cannot carry the equivalence claim — it must rest on reasoning + faithfulness. Aggregate A-wins / B-wins / ties → a Haiku-vs-Opus preference rate per arm.
- **Pinned equivalence margin:** tier-equivalence holds for a (task, arm) when the **net preference for either model ≤ 10 percentage points** (i.e. |wins_Haiku − wins_Opus| / pairs ≤ 0.10, ties excluded from the numerator). Margin set **before data**; not revisited.
- **Coverage rule — pair only rubric-passing outputs** (format-bias fix, Gemini-review NICE-TO-HAVE). Run the pairwise only on Haiku/Opus pairs where **both** outputs passed the absolute rubric (§1(a)); **report the share of pairs excluded**. Rationale: in the skill-off arm the loose baseline lets the weaker model fail format, which an LLM judge cannot fully ignore — including those pairs would inflate the skill-off Haiku→Opus gap and make H6's "narrowing" look artificially good. (If too few skill-off pairs survive, report that as a coverage limit, not a closed gap.)

---

## 2. The judge (FROZEN config — live-verified 2026-06-28)

- **Judge model:** Opus 4.8 (`claude-opus-4-8`) — the strongest tier, to avoid a weak judge. *Self-preference risk* (Opus grading Opus output) is real and is mitigated by the blind + order-randomized + pairwise protocol and the human spot-check (§3). **Verified live 2026-06-28** (`docs/live-verification-judge-2026-06-28.md`): Opus 4.8 **rejects `temperature`** (400 "deprecated for this model") → omitted; **thinking off** works (param omitted); `output_config.format` json_schema is also accepted with thinking off. The judge therefore omits `temperature` and runs thinking off; verdicts are prompt-instructed JSON with a tolerant parse + one retry (json_schema is an available, non-hashed hardening).
- **Determinism of the judge:** the judge has its own variance. Run **K = 3** replicate judgments per item; take the **majority** (rubric: majority pass/fail per check; pairwise: majority of {A, B, tie}). Pre-register an **agreement floor**: an item where the 3 replicates do not reach ≥ 2/3 agreement is **flagged low-confidence**, not silently averaged. Target: judge disagreement ≪ the H5/H6 effect being measured.
- **Frozen prompts:** one fixed rubric-judge prompt (`fixtures/judge/rubric-judge-prompt.md`) and one fixed pairwise-judge prompt (`fixtures/judge/pairwise-judge-prompt.md`), hashed below. No per-task tuning beyond substituting the task's rubric checks (the per-task LLM-judged checks live in `fixtures/judge/manifest.yaml`).
- **Hashing:** `judge_hash = harness.hashing.judge_hash` over {judge model id, K, the two prompt templates, the per-task rubric text, the margin}. Computed by `analysis/quality.py` and re-checked on every run (replay guard). **Pinned: `d12c36a2c8e77a31d712ff6d7913e58f049177a1587412e01fe9800367a4616c`** (also in `fixtures/judge/manifest.yaml`).
- **Check-count note (charter reconciliation):** `docs/charter.md` §3 calls for "2–4 binary checks/task" as the *directional* intent; the frozen instrument here is the source of truth — #6 has 3 LLM checks (incl. the 0–2 graded hook sensitivity floor) + 2 code checks, #9 has 2 LLM + 2 code checks. The 0–2 hook is graded, not binary, by design (§1(a)). Reconciled, not tuned to data.

---

## 3. Validation & honesty guards

- **Human spot-check** on a stratified sample (≥ ~10% of generative outputs, spanning models × arms) to calibrate the LLM-judge against a human label — both for the rubric checks and the pairwise preference. If LLM↔human agreement is poor, the judge is not trustworthy and the H6 claim weakens to "cheaper, where checked" (charter §5 fallback).
- **Blind to condition:** the judge never sees model name, skill arm, or run index.
- **No rubric tuning to data:** the rubric is frozen before any output is graded (this doc). A result that tempts a rubric change is **flagged, not applied** (pre-registration discipline).
- **Report ties honestly:** "Haiku ≈ Opus with the skill" is only claimed where the pairwise margin AND the rubric floor both support it, task by task — never as a blanket.

---

## 4. Outputs (feeds SPEC §7 / charter §6)

Per task, per skill arm, per model: rubric pass-rate; and per (task, arm): the Haiku-vs-Opus pairwise preference.

**H5 — read on the OUTPUT component, never the composite.** The skill adds a fixed ~250–400-token `system` block to every skill-on call. By the Phase-1a identity `CoV_composite = CoV_output × (output cost share)`, that fixed input mass **mechanically lowers composite CoV (Lever B) even if the skill does nothing to the output (Lever A)**. So H5 is judged on:
- **`CoV_output`** (output-token component) and **mean output tokens**, skill-off vs skill-on at the same model — the Lever-A-clean signal.
- **rubric pass-rate must not drop** (a skill that cuts tokens by wrecking quality is not a win).
- **Total-token / dollar cost reported separately and honestly**, *including the skill's own input* — the user's "more efficient token usage" is the *total*, and the skill may pay input to save output (it can net out either way; report it, don't hide it).
- **Pinned H5 threshold:** on the high-latitude tasks (#6, #9), skill-on lowers `CoV_output` by **≥ 25% relative** (and does not raise mean output tokens) vs skill-off at the same model. **Placebo guard:** #4 shows **< 5 pp** absolute change — if it tightens materially too, the effect is a confound, not the skill.

**H6 — the Haiku→Opus pairwise gap, skill-off minus skill-on, per task.** Equivalence per the §1(b) ≤10-pp margin; the claim is "the skill closes the tier gap" only where the gap was open skill-off and within-margin skill-on, *and* the rubric floor holds.

## 5. Scope & caveats (pre-registered, lean design)

The owner chose the lean 2×3 (2026-06-27). These limits are declared up front so the result is read honestly, not as more than it is:
- **Bundled treatment.** The skill bundles output schema + structure + length caps in one artifact, applied in a single pass (no hidden multi-step "self-check" — thinking is off in 1c, so a model can't verify-then-revise invisibly). A positive H5 cannot be disaggregated into *which* sub-mechanism drives it — only "this skill, as a whole." The *verbosity* confound (skill ≈ a wordier restatement of the prompt) is **addressed** by the calibrated-loose baseline: the skill-off prompt carries none of the structure, so the skill's content is genuinely additive. Mechanism ablation is future work.
- **One frozen instance per task.** Each cell is N=20 runs of a single ticket/blurb/brief, so "Haiku-with-skill ≈ Opus" is shown **per instance/task**, not across a task population. Generalization needs more fixtures (deferred).
- **No neutral-system control.** Skill-off has *no* `system` block, so the contrast bundles "skill content" with "a system block exists." A length-matched neutral-system arm (deferred) would isolate content; not run in the lean design.
- **Same-family judge.** Opus 4.8 judges Opus-vs-Haiku, a self-preference risk that biases *against* H6 (conservative — equivalence is harder to claim, not easier); the human spot-check (§3) calibrates it.

---

*Freeze procedure — COMPLETED 2026-06-28: ✅ rubrics + gold label + margin reviewed; ✅ judge prompts written (`fixtures/judge/`) and owner-reviewed; ✅ Opus 4.8 live param acceptance verified (`docs/live-verification-judge-2026-06-28.md`); ✅ `judge_hash` computed + pinned (§2); ✅ status flipped to FROZEN. Graders implemented in `analysis/quality.py`.*
