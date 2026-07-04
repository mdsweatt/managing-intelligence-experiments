# SPEC.md — Experiment 1 Run Matrix & Capture Contract

**Status:** v0.7 — 2026-07-02
**Owner:** TetradStudios
**Relationship:** Operationalizes `charter.md` §5 (controls) + `load-band-reference.md` (fixture spine) into the executable run matrix, and pins the decisions the charter deliberately defers. `runs/*.yaml` is the machine form of §3. `CLAUDE.md` (repo root) is the standing constitution this run obeys. When this doc and the charter conflict, the charter wins on *hypotheses*; this doc wins on *run mechanics* — escalate genuine conflicts, don't silently reconcile.

---

## 1. Decisions pinned (pre-registration)

Recorded before any measurement. Changes logged here with date.

**D1 — Over-service probing pattern.**
- Every sub-Opus task runs at its hypothesized tier **+ Opus** (the waste baseline). **Gated:** the *universal*-Opus commitment is conditional on the Phase 0 cost gate (§4); hypothesis-tier and Haiku-down-probe cells are not gated.
- Haiku **down-probe** only where Haiku is a live option: **#6, #8** (and #7 via the full ladder). Not run where Haiku is implausible (e.g. research, refactor).
- **Full ladder** (Haiku + Sonnet + Opus) on two representatives — **#1** (Haiku-hyp) and **#7** (Sonnet-hyp) — to publish the complete gradient.
- **#15** (Opus-hyp) down-probes to **Sonnet**.

**D2 — Over-service config: match the hypothesis cell, swap only the model.** The headline waste number holds the hypothesis cell's config fixed (thinking posture, effort, temperature) and changes only the model. This generalizes "matched-minimal" and is the operative rule:
- No-thinking discrete tasks → **matched-minimal** (thinking off, effort floor) on the Opus run too. The clean "you chose a bigger model for the same work" number. Note (verified 2026-06-16): the tokenizer is **not** shared — the same fixture is ~35% more input tokens on Opus, so this number = per-token price ratio × **input-token inflation (~1.35×)**; report the two factors separately.
- Thinking tasks (**#15, #16**) → **matched-thinking**: both models run thinking-on at the same effort/band. (Resolves the otherwise-ambiguous posture for #16 — never compare Sonnet-thinking vs Opus-no-thinking.)
- The global `effort=high` default (§2) does **not** apply to over-service Opus runs — their config is dictated by this rule.
- **Optional second condition** — Opus "as typically used" (thinking-on, effort high) to capture real-world waste — is **deferred / off by default**. It cannot carry the "identical" claim (not apples-to-apples); add later only as a clearly-labeled secondary number.

**D3 — Output-equivalence criterion** (needed for the over-service *claim*, not for the H1 run). Pre-registered, lightweight, task-typed:
- Deterministic outputs (**#4** classify, **#8** extract, **#5** translate) → exact-match / schema-match. Objective and free.
- Generative headliners (**#1, #6, #7**) → 2–4 binary quality checks (a rubric), judged by an LLM-judge + human spot-check on a sample.
- Elsewhere: report "cheaper at equivalent output where checked," never a blanket "identical."

**Inherited from `load-band-reference.md` §8:** pre-scripted multi-turn (#16, #17); `effort` param for #15 (bands `low/high/max`, no Haiku probe, thinking `adaptive`, temperature uncontrolled); Haiku probe for cache cells #10–12 with a **≥ 4,096-token** cached-segment floor; Sonnet hypothesis / Opus over-service for the Sonnet–Opus tasks.

---

## 2. Global config (defaults; `runs/*.yaml` carries the machine form)

- **N = 20**, flat, pre-committed, uniform across cells. Phase 0 confirms affordability; if revised it is revised **once, before the real run**, and stays uniform. Never extend per-cell (anti-peeking).
- **`max_tokens` = model output ceiling**, never omitted (the field is required). Bounds are by fixture scoping, never truncation. *(Ceilings **verified 2026-06-16** — Opus 128k / Sonnet 128k / Haiku 64k.)* Every ceiling is ≫16k, so **stream every call** and read the final accumulated usage — this avoids the SDK's long-request timeout guard and keeps capture uniform.
- **Temperature:** **omitted on every call** (provider default), recorded as `omitted`. *(Verified 2026-06-16: Opus 4.8 rejects `temperature` outright ("deprecated for this model"); Sonnet 4.6 rejects it with thinking on — uniform omission is the only control that holds across the ladder. Only model stochasticity moves.)*
- **`effort` = `high`** for all non-#15 Sonnet/Opus cells (a global lurking variable — fixed, not free). Haiku has no `effort` knob. Over-service Opus runs are exempt (see D2).
- **Models** *(IDs + facts **verified live 2026-06-16**; see `docs/live-verification-2026-06-16.md`):*
  | role | id | cache min (tokens) |
  |------|----|--------------------|
  | Haiku | `claude-haiku-4-5-20251001` | 4,096 |
  | Sonnet | `claude-sonnet-4-6` | 1,024 |
  | Opus | `claude-opus-4-8` | 1,024 |
  **Tokenizer is NOT uniform** (verified 2026-06-16): Haiku 4.5 and Sonnet 4.6 share one; **Opus 4.8 differs (~+35%)**. A fixture has **two** token counts (Haiku/Sonnet vs Opus) — record both. Rule 2 (load-band §2) is **active**.

---

## 3. Run matrix — Phase 1a

`+OS` = over-service (matched config per D2). `+DP` = down-probe.

| # | task | cost axis | bands | hyp tier | + over-service | + down-probe | handling |
|---|------|-----------|-------|----------|----------------|--------------|----------|
| 1 | draft email | input (fixed-S) | S | Haiku | Opus | Sonnet | full-ladder rep |
| 2 | rewrite / re-tone | input (≈output) | S·M | Haiku | Opus | — | |
| 3 | factual Q (no tools) | input (fixed-S) | S | Haiku | Opus | — | |
| 4 | classify / triage | input (fixed-S) | S | Haiku | Opus | — | exact-match equiv |
| 5 | translate | input (≈output) | S·M | Haiku | Opus | — | |
| 6 | short-form copy | output (fixed-S) | S | Sonnet | Opus | Haiku | |
| 7 | summarize a doc | input | S·M·L | Sonnet | Opus | Haiku | full-ladder rep |
| 8 | extract structured | input | S·M·L | Sonnet | Opus | Haiku | schema-match equiv |
| 9 | long-form draft | **output** | S·M | Sonnet | Opus | — | output-banded; verify band non-overlap |
| 10 | support vs fixed KB | **cached-context** | M·L | Sonnet | Opus | Haiku | warm-once-read-many; ≥4,096 floor if Haiku |
| 11 | code edit in known file | **cached-context** | M·L | Sonnet | Opus | Haiku | warm-once-read-many; ≥4,096 floor if Haiku |
| 12 | Q&A vs fixed reference | **cached-context** | M·L | Sonnet | Opus | Haiku | warm-once-read-many; ≥4,096 floor if Haiku |
| 15 | strategy from a brief | **thinking depth** | low·high·max effort | Opus | — | Sonnet | thinking `adaptive`; temp uncontrolled; bands = effort |
| 16 | debug (multi-turn) | **turns** | few·many | Sonnet | Opus | — | pre-scripted; per-turn capture; matched-thinking |
| 17 | iterative refinement | **turns** | few·many | Sonnet | Opus | — | pre-scripted; per-turn capture |
| 18 | analyze large dataset | **payload** | M·L | Sonnet | Opus | — | payload via tool-result/attachment |
| 19 | batch file processing | **payload** (+light fan-out) | M·L | Sonnet | Opus | — | stays 1a (sequential loop) |
| 22 | image-gen prompt from context | output (fixed-S) | S | Sonnet | Opus | Haiku | creative meta-prompting; generative → D3 "elsewhere" rubric (not a headliner); demand-driven (charter §5); added 2026-06-17 |

Phase **1b** (#13, #14, #20, #21 — agentic; tool-use loop + stubbed tools over a frozen corpus) is deferred and **not** specified here.

Rough size (for the ceiling): ≈ 80 base cells × N=20 ≈ 1.6k calls; multi-turn turn-multiplier adds ≈ +600; cache cells add a write call each. Order **low thousands of calls** — but **cost is tail-dominated** (L-band-on-Opus, thinking-max-on-Opus), which is exactly why Phase 0 prices the tail first.

---

## 3b. Run matrix — Phase 1c (Determinism A/B — tests H5, H6)

A causal sub-experiment (charter v0.6) testing whether a **well-defined skill** buys lower output variance/cost (H5) and tier-agnostic quality (H6). Machine form: `runs/phase1c.yaml`; skills: `fixtures/skills/manifest.yaml`. A **2×3 factorial** — skill {off, on} × model {Haiku, Sonnet, Opus} — on three frozen Phase-1a fixtures, N=20/cell, **standard family**:

| # | task | cost axis | band | models (each × skill off/on) | role | why this task |
|---|------|-----------|------|------------------------------|------|---------------|
| 4 | classify / triage | input | S | Haiku · Sonnet · Opus | factorial | **placebo control** — already ~0% CoV; the skill should NOT move it (H5 guard) |
| 6 | short-form copy | output | S | Haiku · Sonnet · Opus | factorial | high output-latitude — Lever A should bite (H5); tier gap should close (H6) |
| 9 | long-form draft | output | S | Haiku · Sonnet · Opus | factorial | high output-latitude — Lever A should bite (H5); tier gap should close (H6) |

= 3 tasks × 3 models × 2 skill arms × N20 = **18 cells / 360 calls** (+ judge calls — §5, judge spec). Headline tier contrast: **Haiku vs Opus**.

**The two arms (calibrated-loose baseline; fixtures `fixtures/manifest-phase1c.yaml`).** *Skill-off* is a **natural user request** — a realistic prompt with no rigid structure — so a positive H5 measures *scaffolding*, not prompt verbosity. *Skill-on* adds a frozen, hashed scaffold (`fixtures/skills/<id>.md`) as an **uncached `system` block** — output schema/format + scope/length caps, **identical across all three models** (never tuned per model — Rule 2 / invariant 6), applied in one pass (no hidden self-check; thinking is off). For #6/#9 the loose prompts reuse the frozen Phase-1a **input** blurb/brief; **#4 is mixed** — it keeps its frozen constrained prompt (the task needs its label set) with a redundant-procedure placebo skill. Frozen + pinned by `skill_hash`/`fixture_hash`; the harness refuses an unfrozen skill or fixture (the review gate).

**Per-model config.** Effort=high for Sonnet/Opus, none for Haiku; thinking off; temperature omitted; `max_tokens`=ceiling — each model's Phase-1a non-#15 default, so 1c cells are comparable to 1a. The Phase-1a over-service swap logic is **not** reused (it imports matched-minimal / tier-pull conventions that would confound the factorial).

**Two declared departures from Phase-1a discipline** (charter v0.6; CLAUDE.md §"Experiment 1c"): the **two-axis factorial** (justified for causal attribution — each pairwise contrast isolates one axis; the skill×tier interaction is the H6 object) and **output-text persistence** for the quality judge. The quality judge is a frozen, pre-registered instrument — its contract lives in `docs/phase1c-judge-spec.md` and feeds §7.

**Read H5 on the output component, not the composite.** The skill-on `system` block is fixed ~250–400 tokens; that deterministic input mass would lower the *composite* CoV via Lever B even with zero Lever-A effect. So H5 = `CoV_output` + mean output tokens (skill-off vs skill-on, same model); total-token cost incl. the skill's own input is reported separately (the user's "efficiency" is the total). Lean-design caveats (one instance/task, bundled treatment, no neutral-system control) are pre-registered in the judge spec §5 and charter §3b.

**Run status (2026-06-28 · matrix ran; expectations above unchanged — pre-registration).** This matrix ran 2026-06-28 (`results/run-20260628T051203Z-53aa02/`, 360 records, $2.94; judge graded via `analysis/quality.py --run-judge`). The "should bite / should close" notes in the table above are **pre-registered expectations, left as written** — outcomes are recorded only as result-pointers in the **charter §0 state-note 2026-06-28** and `analysis/output/{h5_determinism.csv, quality-findings.md}` (headline: H5 nuanced — variance falls, but the long-form scaffold raises length; H6 rejected — Opus still preferred over scaffolded Haiku on #6). H5's token side is computed by `analysis/h5.py` (arm-aware; `analysis/h1.py` is not). **Phase 1d** (charter v0.7 — re-tests H5/H6 on a de-confounded instrument + tests H7/H8, via a 3-arm × 3-model factorial on a ~9-task cap↔mandate ladder) is **pre-registered, build in progress** — see §3c.

## 3c. Run matrix — Phase 1d (matrix STAGED; artifacts pending the owner's freeze)

Charter v0.7 §5 "Experiment 1d" is the pre-registration; `docs/phase1d-build-notes.md` is the build
log (design spine LOCKED 2026-06-30; S2 fixtures reviewed + frozen 2026-07-02; skill-off pilot RAN
2026-07-02 — `results/run-20260702T133840Z-64d579/`, 180/180 clean, $2.09, Console cross-check
exact to the token). The **full 3-arm matrix `runs/phase1d.yaml` is now STAGED**: 78 cells (8
ladder tasks × 3 arms × 3 models + the #4 placebo 2-arm) × N=20 = 1,560 calls, $100 ceiling,
`h7_label`s frozen in-matrix from the measured pilot ranges (caps #1/#6/#7/#8; mandates
#9/#15/#23/#24). Its 6 new skills (`fixtures/skills/manifest-phase1d.yaml`, pilot-tuned numeric
cues) and 6 new neutral blocks (`fixtures/neutral/manifest.yaml`, length-matched −2.3%…−7.8%,
triple-Gemini-reviewed) are staged **`frozen:false`** — the harness's require_frozen gate refuses
to run them until the owner's sign-off flips them, so the matrix cannot fire early. Remaining
before the run: owner freeze → charter §8 #23/#24 addition (v0.8, owner-signed) → judge FREEZE
(micro-pilot + live re-verify + pin `judge_hash`) → S6 cost estimate vs the ceiling. Build state:

- **Fixture registry: `fixtures/manifest-phase1d.yaml` (FROZEN 2026-07-02).** The 6 new tasks —
  #1 email_reply, #7 minutes_recap, #8 extract_fields (intended **cap**); #15 strategy_brief_1d
  (thinking-on), #23 spec_draft, #24 status_report (intended **mandate**) — each a calibrated-loose
  one-line prompt + frozen S-band input (111–237 input words), hashed **before** the pilot runs on
  them; plus byte-identical copies of the frozen 1c #4/#6/#9 entries. `recorded_token_counts` stay
  TBD until the pilot cost-gate (free `count_tokens`; the 1c convention — counts are cost-estimation
  inputs, not part of the content freeze).
- **Skill-off design pilot: `runs/phase1d-pilot.yaml`** — 6 new tasks × 3 models × **arms:[off]** ×
  N=10 (180 calls, ceiling $10, **billable — cost-gated, owner-flagged first**). Measures each
  task's natural loose output in **words** so scaffold demands + labels are set against measurement
  (design spine S3). Its records are a **design input only** — never mixed into H1/H5/H7/H8 (the
  phase0-calibration hygiene rule). Harness mechanics added for it: a factorial task may restrict
  `arms` (skill required only when "on" runs) and may set `thinking: adaptive`, honored at the
  **model-natural convention** — adaptive on Sonnet/Opus, off on Haiku (Haiku has neither the effort
  knob nor adaptive thinking; live-verification 2026-06-16) — so within a (task, band, model) the
  arm remains the only moving axis.
- **Judge instrument: `fixtures/judge/manifest-phase1d.yaml` (FROZEN 2026-07-02, `judge_hash
  5fd08ff3287cbd32…`; contract in `docs/phase1d-judge-spec.md`).** Format-neutral rubrics for
  **all 8** generative tasks (`faithful` is the only pairwise gate per charter §5.147; objective
  format checks are declared in the manifest as `code_checks` and graded in code); frozen after
  the post-pilot numeric cues + the live Gemini micro-pilot re-verify. *(This line said DRAFT
  during the build window — the freeze is recorded here for the read-through reader.)*
- **Analysis (non-billable, built):** `analysis/h7.py` (cap/mandate sign test; labels read from the
  frozen `runs/phase1d.yaml` `h7_label` field), `analysis/h8.py` (neutral-arm ratio R, verdict bands
  <⅓ / ⅓–½ / ≥½; scored only where the skill cut CoV ≥25% — the H5 bar, a build-time
  operationalization logged in the build notes), a 3-arm-aware `analysis/h5.py`, and an 8-task
  data-driven `analysis/quality.py`.

---

## 4. Phase 0 — cost calibration gate (precedes the full run)

Owner ruling: price the real cost before committing to universal Opus.

- **Subset** (cost-spanning, each at hyp tier **+ Opus**, N = 3–5): **#1-S** (cheap floor), **#7-M** and **#7-L** (input gradient), **#10-M** (cache warm+read shape), **#15-high** (thinking tail). Chosen to bracket the cost regimes so the projection covers the expensive tail, not just the floor.
- **Procedure:** measure per-call cost per cell → project full-matrix cost = Σ(per-call cost × cells × N), with the **Opus contribution broken out** → compare to the hard ceiling (§6).
- **Decision rule (pre-stated, so it isn't improvised):**
  - Full projection incl. universal Opus **clears** the ceiling → run Phase 1a as specified.
  - Opus portion **breaches** it → **fallback:** Opus over-service runs only on the full-ladder reps (#1, #7) + a representative sample, not universally.
  - Either way the choice is made **once, from cost, not from variance.**
- **Hygiene:** Phase 0 calls are **cost-only** — they do **not** enter the H1 variance dataset. The real run uses the committed flat N fresh.

---

## 5. Capture contract (every record)

Append-only at `results/<run-id>/records.jsonl`. **Raw tokens only — no dollars** (price applied at analysis, §7).

Per call:
- `run_id`, `timestamp`, `cell_id` (task / band / model / config), `config_hash`, `fixture_hash`
- `model_id`, `model_version`, `tokenizer_version`
- **usage vector:** `input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`, `tool_result_tokens` (if any), `thinking_tokens` (from `output_tokens_details`)
- `latency_ms`, `wall_clock`
- cache cells: `call_role` ∈ {`write`, `read`}; **every read asserts a cache hit** (cache_read high, input low) or is flagged/discarded
- thinking cells (#15/#16): a thinking call whose `output_tokens_details` is **missing or null is rejected** — no silent `thinking_tokens=0` at full output cost (verified live on Opus 4.8 2026-06-23; see `live-verification-2026-06-16.md`)
- multi-turn cells: one record **per turn** (`turn_index` + per-turn usage), not per session
- **Phase-1c factorial cells only:** `response_text` (the assistant output, persisted for the quality judge) and `skill_hash` (the frozen skill bytes, skill-on arm only). These are the **only** records carrying output text — every cost-only Phase-1a/1b record stays tokens-only (invariant 2). `cell_id.skill_arm` ∈ {off, on}; a skill-off cell is byte-identical in identity to its pre-skill self.

`results/<run-id>/config-snapshot.yaml`: the exact expanded matrix + harness code version + all hashes, so any run replays from its record alone.

---

## 6. Cost & safety guardrails

- Pre-run cost estimate + **hard call/spend ceiling** — *value: **OWNER TO SET*** — abort on breach (a loop bug must not empty the card).
- Rate-limit backoff / batching. Watch the **cache-TTL interaction**: backoff that delays reads past the TTL turns a read into a fresh-input call → discard/flag (see §5).

---

## 7. Analysis hook (downstream; see charter §6)

H1 = coefficient of variation per cell on the **dollar-weighted composite** + per component (the composite is the headline; per-component localizes where variance lives). Price scalars from `prices/` applied **at analysis time only**. Within-cell variance stays strictly separate from between-model variance (the latter is the over-service signal, not an H1 result).

---

## 8. Open items (owner — close before the run)

- **Hard cost ceiling ($)** — **$500**, owner-set 2026-06-16. Harness aborts on breach.
- **`prices/` values** — fill from current pricing at analysis time. *Left as verify-markers; not asserted from memory.*
- **Fixtures** — frozen artifact + exact prompt per cell. **Largely done.** *(2026-06-21: 21 Phase-1a fixtures **frozen + hashed** with measured counts — single-call 1–9, 15, 22; cache 10/11/12-M; multi-turn 16/17 (few·many); payload 18/19-M. Record: `docs/fixture-freeze-2026-06-21.md`. On-disk call formats pinned in `fixtures/README.md` (cache prefix, multi-turn `===TURN===`, payload tool_result). #5-M's translate source is the ~7k-word *Europe 2031* scenario. **L-band deferred** (owner): 7-L/8-L, cache-L, payload-L.)*
- **Live verification** — ✅ **done 2026-06-16** (`docs/live-verification-2026-06-16.md`). Cache mins, ceilings, effort, thinking, usage shape, and provenance headers confirmed; Sonnet max-output, the shared-tokenizer claim, and temperature settability corrected. **Rate tier re-verified live 2026-06-22** — Haiku/Sonnet ITPM 450k / OTPM 90k, Opus ITPM 2M / OTPM 200k, 1000 rpm; a ~100k L-band input fits one call (the tier-1 50k captures in the verification doc's item 5 are superseded). **Opus 4.8 thinking-token capture re-verified live 2026-06-23** (streaming recovery confirmed on Opus; capture contract hardened to reject a missing/null thinking component — commit `23fd3aa`). Re-run on each model release.
- **As-typically-used Opus** (D2 optional second condition) — decide later, off for now.

---

*Changelog: v0.7 (2026-07-02) — added **§3c Phase 1d build state** (pre-data): `fixtures/manifest-phase1d.yaml` frozen (6 new calibrated-loose S-band fixtures #1/#7/#8/#15/#23/#24 + reused 1c #4/#6/#9), the **skill-off design pilot** `runs/phase1d-pilot.yaml` (18 cells × N=10, arms:[off], cost-gated), harness `arms`/factorial-`thinking` mechanics (model-natural: adaptive on Sonnet/Opus, off on Haiku), 8-task format-neutral judge rubrics (DRAFT, `code_checks` in-manifest), and the H7/H8 analysis modules. The full `runs/phase1d.yaml` (labels + skills + neutral blocks) deliberately waits on the pilot (invariant 4). · v0.6 (2026-06-29) — forward-pointer only: charter **v0.7** pre-registers **Phase 1d** (Experiment 1d — re-tests H5/H6 on a de-confounded instrument + tests **H7** cap-vs-mandate / **H8** scaffold-specificity); 1d's run matrix is **build-pending**, not yet specified here, and the §3b Phase-1c matrix is unchanged. · v0.5 (2026-06-27) — added **§3b Phase 1c (Determinism A/B)**: the 2×3 skill×model factorial on #4/#6/#9 (`runs/phase1c.yaml`, `fixtures/skills/`), tests charter v0.6 H5/H6; extended §5 capture contract with `response_text` + `skill_hash` (factorial cells only); judge contract in `docs/phase1c-judge-spec.md`. Pre-data; declares the two departures (factorial + output persistence) logged in charter v0.6 and CLAUDE.md. · v0.4 (2026-06-21) — froze 21 Phase-1a fixtures (single-call 1–9/15/22, cache 10/11/12-M, multi-turn 16/17 few·many, payload 18/19-M): counts measured per tokenizer (tok-hs/tok-opus) + sha256 pinned, all tranche-1 counts re-verified against `count_tokens` (exact match), cache prefixes clear the Haiku ≥4,096 floor — record in `docs/fixture-freeze-2026-06-21.md`; #5-M (translate-M) re-sourced to the ~7k-word *Europe 2031* scenario to reach M; L-band still deferred. · v0.3 (2026-06-17) — added matrix cell **#22 image-gen prompt from context** (output-axis, S, Sonnet-hyp + Opus over-service + Haiku down-probe) to §3; demand-driven per charter §5 (charter bumped v0.4→v0.5); generative cell, follows D3's "elsewhere, where checked" equivalence treatment (NOT added to the #1/#6/#7 headliner trio, matching #9). Pre-data, so it extends the pre-registration. Also aligned the Status header to the changelog (was lagging at v0.1). · v0.2 (2026-06-16) — live-verification reconciliation (`docs/live-verification-2026-06-16.md`): Sonnet max-output 64k→128k (+1M context); tokenizer NOT shared (Opus 4.8 ~+35%, two counts/fixture, Rule 2 active); temperature omitted on every call (Opus rejects it, Sonnet rejects with thinking on); stream every call; cache mins + Opus ceiling confirmed; hard ceiling set to $500; rate tier raised. · v0.1 (2026-06-16) — initial run-matrix pre-registration; D1/D2/D3 pinned; Phase 0 gate added.*
