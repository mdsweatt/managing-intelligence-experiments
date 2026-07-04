# CLAUDE.md — Managing Intelligence / Experiment 1 harness

Standing guardrails for Claude Code in this repo. Read before every session.

This file is the **constitution** (invariants that always hold). `docs/SPEC.md` is the **run matrix** (which cells, what N, per-cell config) — `runs/*.yaml` is its machine form, which the harness consumes. `docs/load-band-reference.md` is the **fixture spine**. `docs/charter.md` (the charter) is the **source of truth** (pre-registered hypotheses + kill-conditions). `README.md` is the orientation map (layout + run procedure). When they conflict, **escalate to me — do not silently reconcile.**

## What this repo does

Experiment 1 measures **within-cell run-to-run variance** of token cost per `(task × load band × model × config)`, to test **H1**: is a task's cost stable enough to express as a band? This is a **provocation tool**, not a finance-grade instrument — ranges honest and non-embarrassing, not exact. **Denominate in tokens, not dollars**; price is a single scalar applied at analysis time only.

## Non-negotiable measurement invariants

1. **Measure, don't estimate.** The API returns exact token counts — that is the data. Never substitute a guessed or derived number for one a call would return. Label any genuine prior as a prior until data replaces it.
2. **Capture the full usage vector every call:** `input`, `output`, `cache_read`, `cache_write`, tool-result tokens — plus latency and wall-clock. Components are not fungible (a cache-read token ≈ 1/10 the dollar weight of fresh input), so store them separately. Store **raw tokens**; never bake dollars into stored records.
3. **Version-stamp + hash every record:** model+tokenizer version, run date, and a hash of the exact fixture + full config. Every run must replay from its record alone.
4. **Flat N, pre-committed, uniform across cells (see SPEC).** NEVER observe a noisy cell and add runs to tighten it — sequential peek-and-extend p-hacks variance downward. A noisy cell is a *finding* (flag it for distribution-monitoring), not a prompt to collect more.
5. **Never improvise, regenerate, or "improve" a fixture.** Fixtures are frozen, decided in advance, pinned by hash. If a fixture seems wrong or is missing, **stop and ask** — do not fill the gap yourself.
6. **Define the band by the artifact; record the token count as a consequence; never re-target the count per model.** Tuning content to hit a token number needs different content per model and breaks the same-fixture-across-models control. (v1 — **verified live 2026-06-16**: Haiku 4.5 and Sonnet 4.6 share a tokenizer, but **Opus 4.8 differs (~+35%)** — so a fixture has **two** token counts, not one. Rule 2 is **active**, not dormant: select by proxy [words / pages / lines / files / turns], measure the count *per tokenizer*, don't tune to it.)

## Controls

- **Within a cell:** hold everything fixed — frozen artifact, exact prompt, model+tokenizer, effort, temperature. Only model stochasticity moves.
- **Across cells:** change **exactly one axis** at a time (load band **or** model **or** thinking on/off). Varying two destroys attribution. (**Phase 1c exception:** the determinism A/B is a deliberate two-axis *factorial* — skill × model — pre-registered as such; see the Experiment 1c section below and charter v0.6.)
- **Temperature:** **omitted on every call** (provider default), recorded as `omitted`. Verified 2026-06-16: Opus 4.8 rejects `temperature` outright ("deprecated for this model") and Sonnet 4.6 rejects it when thinking is on, so uniform omission is the only setting that holds across the ladder — only model stochasticity moves, as intended.
- **`effort`:** pinned at default `high` for all non-#15 cells (it moves *all* token spend — a global lurking variable). Haiku has no effort knob. **Exception:** over-service Opus runs are governed by the SPEC over-service config, **NOT** this default — do not set them to `high` unless SPEC says so.
- **No `max_tokens` cap → set `max_tokens` to the model ceiling, do not omit it** (the field is required). Cost is bounded by **fixture scoping, never truncation** — a truncated artifact is not a natural one. Capture `usage.output_tokens_details.thinking_tokens` separately when thinking is on.

## Cache-heavy cells (#10–12)

- **warm-once-read-many:** one cache-write call, then the read calls. Report the write cost and the read distribution **separately** — a naive N× loop yields a bimodal write+reads mixture and a meaningless CoV.
- **Assert a cache hit on every read** via the usage vector (cache_read high, input low). Discard/flag misses: a TTL-expired read silently becomes a fresh-input call and corrupts the distribution. Keep reads inside the cache TTL window.
- **If Haiku-probed:** floor the cached segment at **≥ 4,096 tokens** (Haiku's cache minimum; Sonnet/Opus is 1,024) so caching engages uniformly across the ladder.

## Multi-turn cells (#16, #17)

- **Pre-scripted user turns,** fixed across runs — only model stochasticity moves. Model responses compound into later turns' input (a variance amplifier, by design).
- **Capture per-turn usage,** not just session total. Variance is non-stationary (it grows with turn count): the H1 headline is session-total CoV, but per-turn capture is required to see where variance enters and to avoid mistaking late-turn compounding for an unbandable task.

## Experiment 1c — Determinism A/B (skill axis + quality judge)

A causal sub-experiment (charter v0.6, **H5/H6**) testing whether a **well-defined skill** — a frozen output scaffold injected as a `system` block — buys (H5) lower output-token variance/cost and (H6) tier-agnostic quality (Haiku-with-skill ≈ Opus). It reuses the Experiment-1 harness and model ladder; the **skill-off arm is a calibrated-loose baseline** (a natural request — so H5 tests scaffolding, not prompt verbosity), #6/#9 reuse the frozen Phase-1a *inputs*, and **#4 is a mixed placebo** (keeps its constrained prompt). Fixtures: `runs/phase1c.yaml`, `fixtures/manifest-phase1c.yaml`, `fixtures/skills/`. Three deliberate, pre-registered departures from the Phase-1a rules above — declared here, **not silently reconciled**:

- **Two-axis factorial (vs "exactly one axis").** 1c crosses skill {off,on} × model {Haiku,Sonnet,Opus} on tasks #4/#6/#9. Sound for *causal* inference: each pairwise contrast still isolates one axis, and the skill×tier interaction **is** the H6 object. Attribution is preserved per-contrast — this is not a Phase-1a observational cell.
- **Output-text persistence (scoped exception to invariant 2).** 1c persists `response_text` on the record so the quality judge can grade H6. ON **only** for factorial cells (`role_label == "factorial"`); every cost-only Phase-1a/1b record stays tokens-only.
- **Skills + judge are frozen, hashed, pre-registered artifacts (extends invariants 3 & 5).** A skill is frozen and pinned by `skill_hash` in `fixtures/skills/manifest.yaml` exactly like a fixture, with **identical text across all models** (never tuned per model — invariant 6). The quality judge (model + rubric + prompt) is itself frozen, hashed, and **pre-registered before any data** — deterministic graders where the task allows (#4 exact-match), else a frozen LLM-judge with a fixed rubric, K-replicate majority, and blind order-randomized pairwise preference for tier-equivalence (self-preference guard + human spot-check).

**Pre-skill identity is preserved exactly:** a skill-off config hashes byte-identically to the pre-skill schema (`config_hash` drops `skill=None`) and a skill-off cell key omits the arm — so Phase-1a records and analysis are untouched. **Before running the judge, verify its model's live API surface** (effort/thinking/temperature acceptance) per "Verify live" below — do not assert from memory.

## Operational guardrails

- **Pre-run cost estimate + hard call/spend ceiling.** A loop bug must not be able to empty the card — abort on ceiling breach.
- **Rate-limit handling** (backoff / batching) so a large-input cell can't hit a TPM wall mid-run. Watch the interaction with cache TTL: backoff that delays reads past the TTL is the cache-miss hazard above.

## Verify live, don't assert from memory

Before relying on any API surface detail — `effort` levels per model, whether temperature is settable with thinking on, cache minimums, max-output ceilings, the shared-tokenizer claim — confirm it against the live API (test param acceptance directly) or current docs. `load-band-reference.md` records these as of 2026-06-15; treat that as **needing re-confirmation, not gospel.** First pass re-confirmed **2026-06-16** — see `docs/live-verification-2026-06-16.md` (it corrected the shared-tokenizer claim, Sonnet's max-output, and temperature settability; cache mins + Opus ceiling held). Re-run on each model release.

## Pre-registration discipline

Any change to a hypothesis or kill-condition is logged in the charter with version + timestamp **before** any measurement data exists for it. Never quietly retrofit a hypothesis to data. If a result tempts a hypothesis change, **flag it — don't make it.**
