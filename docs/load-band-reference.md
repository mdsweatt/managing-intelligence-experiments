# Load-Band Reference — Experiment 1 Fixture Spine

**Status:** v1.3 — added task #22 (demand-driven) · 2026-06-17 (supersedes v1.2, 2026-06-16)
**Authors:** Mike Sweatt, Claude
**Owner:** TetradStudios
**Relationship to charter:** Elaborates `charter.md` §4 (load bands), §5 (the fixture spine — "gated on calibrating the load-band token thresholds"), and §8 (seed task list). This *is* that calibration. Self-contained: Claude Code or a cold reader can curate fixtures from this without the originating conversation.

---

## 1. What a load band is

A bare task name under-specifies cost. The atomic measured unit is **task × load band**: a task run at a fixed point along its dominant cost-driving dimension, benchmarked at that point.

**Load is not "input size."** Charter §4 names input context the dominant driver and treats output and iteration as secondary knobs "folded in." That holds for the discrete tasks only. Across the 21, cost is driven by **six distinct axes**, five of which §4 collapses:

1. **Input** — prose/document size in the prompt. *(Cache-heavy sub-mode: the cost-driving input is the* cached prefix*, with its own rules — see §6.)*
2. **Output** — generated length (a long-form draft is ~90% output; input barely moves its cost).
3. **Turns** — multi-turn context accumulation; history resent each turn.
4. **Payload** — a file/dataset ingested via tool result or attachment, not the prompt.
5. **Fan-out breadth** — number of items (sources, pages, files) an agentic task spans.
6. **Thinking depth** — reasoning effort; for a strategy task this is the cost driver, not input or output.

Each task is banded on **its** dominant axis. Consequence to keep visible: **"large" is not cross-task comparable** — large-for-summarize (big input) and large-for-draft (big output) are different regimes. The band labels a regime, not a universal unit.

## 2. Two rules

**Rule 1 — the band labels a frozen fixture, not the measured quantity.** You never measure "the small band." You measure one fixed small fixture, N times, for its run-to-run variance (H1). The threshold's only job is to make a task's 2–3 fixtures land in *distinct* regimes, not cluster. So the boundary's precision is irrelevant — **order-of-magnitude spacing** is enough and on-brand for a provocation tool. Not claiming 8K vs 12K tokens is meaningful; claiming ~1K vs ~10K vs ~100K are different load regimes.

**Rule 2 — define the band by the artifact; record the token count as a consequence; never re-target the count per model.** The same text is a different token count on a different tokenizer. Define "10K tokens" and try to hit 10K on each model and you need *different content per model* — breaking the same-fixture-across-models control. So: freeze the content, select it by a model-independent proxy (words / pages / lines / files / turns), let each tokenizer produce whatever count, record it per cell.

> **v1 (corrected 2026-06-16 by live `count_tokens`):** the ladder does **NOT** share one tokenizer. Haiku 4.5 and Sonnet 4.6 share a tokenizer (same sample = 66 tokens each); **Opus 4.8 differs (89 tokens, ~+35%)** — exactly the Opus-4.7 tokenizer change the original caveat warned about. So a fixture has **two** token counts: one for Haiku/Sonnet, one for Opus — **record both**. Rule 2 is **active**: freeze the artifact, select by proxy, record the count *per tokenizer*. Consequence: the Sonnet→Opus over-service number is price-ratio × input-token inflation (~1.35×), not price alone — decompose at analysis. Evidence: `docs/live-verification-2026-06-16.md`.

## 3. Token anchors

Approximate regime markers, not boundaries. Prose ≈ 1.3 tokens/word. **Select by proxy; measure the real count — do not trust these ratios for a specific fixture.**

| Band | Input tokens | ≈ prose |
|------|--------------|---------|
| S | ~1K | ~750 words / ~1.5 pp |
| M | ~10K | ~7.5K words / ~15 pp |
| L | ~100K | ~75K words / short book |

- **Code** is denser and language-dependent (~8–12 tok/line, varies widely) — measure per fixture.
- **Output** range is compressed: standard ≈ 0.5–2K tokens, long ≈ 4–8K (rarely beyond in one call). Max-output ceiling (**verified 2026-06-16**): **Opus 4.8 = 128k, Sonnet 4.6 = 128k, Haiku 4.5 = 64k** — the long band sits far under all three, so headroom is a non-issue. "No `max_tokens` cap" (charter §5) means set `max_tokens` to the model ceiling, *not* omit it (the field is required); when thinking is on, the thinking budget counts toward `max_tokens`. Bands set by natural completion length, never truncation. Capture `usage.output_tokens_details.thinking_tokens` to split thinking cost from text output.
- **Cached-context** floor: ≥ **4,096 tokens** if the cell is Haiku-probed (see §6).

## 4. Per-task table

| # | Task | Cost axis | Bands | Selection proxy | Phase |
|---|------|-----------|-------|-----------------|-------|
| 1 | Draft short email | input (fixed-small) | S only | words of brief | 1a |
| 2 | Rewrite / re-tone | input (≈ output) | S·M | words of passage | 1a |
| 3 | Factual Q (no tools) | input (fixed-small) | S only | — | 1a |
| 4 | Classify / triage | input (fixed-small) | S only | words of item | 1a |
| 5 | Translate | input (≈ output) | S·M | words of source | 1a |
| 6 | Short-form copy | output (fixed-small) | S only | — | 1a |
| 7 | Summarize a doc | input | S·M·L | words / pages | 1a |
| 8 | Extract structured data | input | S·M·L | words / pages | 1a |
| 9 | Long-form draft | **output** | S·M | target output words | 1a |
| 10 | Support vs fixed KB | **cached-context** | M·L | words / pages of KB | 1a |
| 11 | Code edit in known file | **cached-context** | M·L | lines of cached repo | 1a |
| 12 | Q&A vs fixed reference | **cached-context** | M·L | words / pages of ref | 1a |
| 13 | Multi-source research | **fan-out breadth** | by corpus size | # frozen sources | 1b |
| 14 | Competitive analysis | **fan-out breadth** | by corpus size | # frozen pages | 1b |
| 15 | Strategy from a brief | **thinking depth** | low·med·high effort | effort / budget | 1a |
| 16 | Debug (multi-turn) | **turns** (+ thinking?) | few·many turns | # turns | 1a |
| 17 | Iterative refinement | **turns** | few·many turns | # turns | 1a |
| 18 | Analyze large dataset | **payload** | M·L | rows (× cols) | 1a |
| 19 | Batch file processing | **payload** (+ light fan-out) | M·L | # files × size | 1a |
| 20 | Multi-file refactor | cached + fan-out | widest | repo lines + # subagents | 1b |
| 21 | Codebase / doc audit | cached + fan-out + payload | widest | # files/lines + breadth | 1b |
| 22 | Image-gen prompt from context | output (fixed-small) | S only | target output words | 1a |

## 5. Notes on judgment-call rows

- **#9** bands on *output*, not input — the cleanest case where §4's "input size" framing fails outright. Compressed range → 2 bands.
- **#10–12** — cache cells; see §6.
- **#15** — cost axis is thinking effort, controlled by the **`effort`** param (`output_config={"effort": ...}`), *not* a token budget. Mechanism is **not uniform across the ladder**: Opus 4.8 and Sonnet 4.6 support `effort` (Opus: `low`→`max` incl. `xhigh`; Sonnet: `low`→`max`, **no `xhigh`**); Haiku 4.5 has **no `effort`** param at all. So band #15 on the levels common to Opus + Sonnet — **`low` / `high` / `max`** — enable thinking via `thinking: {type: "adaptive"}`, and **do not probe Haiku** (no comparable control, low value for hard reasoning). Effort is a behavioral signal, not a strict budget, so thinking length varies run-to-run → #15 is a candidate **high-variance regime alongside fan-out** (H1-relevant). Note: temperature is **omitted on every call** (verified 2026-06-16 — Opus 4.8 rejects it outright; Sonnet 4.6 rejects it with thinking on), recorded as `omitted`; #15 runs at the model's thinking-default sampling.
- **#16 / #17** — turn axis; bands = turn count. Convention: **pre-scripted turns** (§8.1) — user messages fixed across runs, so only model stochasticity moves. (Model-response length still compounds into later turns' input, so multi-turn stays a variance amplifier even when scripted — that compounding *is* the cost behavior we want.) Hold `effort` fixed (Sonnet default) and vary turns, not both. #16 likely has thinking on (adaptive).
- **#19** — payload axis with light fan-out; stays **1a** because a *fixed* batch loops sequentially, no agentic orchestration (see §7).
- **#22** (added 2026-06-17, demand-driven per charter §5) — output axis like #6/#9, but the artifact is a *prompt*, not a document: read a frozen context (e.g. a requirements set) and write image-generation prompt text for a downstream tool. Banded **S only** (two short image-prompts, well under the output ceiling); proxy = target output words. It is the set's **creative meta-prompting** probe — does open-ended generation, where output latitude is widest, band as tightly as the structured generation in #1/#6/#9? Generative → SPEC D3 "elsewhere, where checked" equivalence, not a headliner (same posture as #9). Sonnet hypothesis, Opus over-service, Haiku down-probe.

## 6. Cache-heavy handling (#10, #11, #12)

- **No small band.** A tiny cached context is archetype-contradictory (if it's small, why cache it?). Charter pegs #10/#12 as "large, repeated." Bands = M·L only, on the cached-context axis.
- **Two numbers per cell, not one.** Run **warm-once-read-many**: one cache *write* call, then the read calls. Report the write-once cost *and* the read distribution separately. A naive "run N×" loop instead yields a bimodal write+reads mixture and a meaningless CoV.
- **Cache minimums are not uniform across the ladder** (**verified live 2026-06-16**): Sonnet 4.6 and Opus 4.8 cache from **1,024** tokens; Haiku 4.5 needs **4,096** (warm-write probe: Sonnet/Opus engaged by ~1.4k, Haiku not until ~4.5k). A cached prefix between 1,024 and 4,096 caches on Sonnet/Opus and silently *won't* on Haiku — a threshold artifact, not a real difference. **If these cells are Haiku-probed (§8.3), floor the cached segment at ≥4,096** so caching engages uniformly. The floor binds only the cached prefix; the per-call query rides on top and can be small.

## 7. Phase split

- **1a — single-call or scriptable:** #1–12, 15, 16, 17, 18, 19. Build first: the tractable majority, and the discrete cells are where tight variance is predicted — the fastest path to a first "what tasks cost" result.
- **1b — agentic (needs a tool-use loop + stubbed tools over a frozen corpus):** #13, 14, 20, 21. Real orchestration code; build after 1a. §5's "few hundred lines" estimate undercounts these.
- **#19** stays 1a: a fixed batch loops sequentially. Confirm at build.
- **1c — determinism A/B (skill axis):** **not a new band.** A *skill {off, on}* treatment crossed with the model ladder (charter v0.6 H5/H6; SPEC §3b), on its own registry `fixtures/manifest-phase1c.yaml`. The skill-off arm is a **calibrated-loose baseline** (a natural request) so H5 tests scaffolding not verbosity; #6/#9 use new loose prompts that **reuse the frozen Phase-1a input** blurb/brief; #4 keeps its frozen constrained prompt (placebo). The skill is a frozen scaffold (`fixtures/skills/`), injected as an uncached `system` block. Determinism is a *treatment* layered on the spine, not a point on a cost axis.

## 8. Resolved decisions (v1.1)

The §8 forks are closed. Two items carry to `SPEC.md`; one matrix sub-question remains.

1. **Multi-turn scripting (#16, #17): pre-scripted.** User turns fixed across runs; only model stochasticity varies. Reactive scripting deferred to a later variant. (Model-response length still compounds into later turns — multi-turn stays a variance amplifier by design.)
2. **Thinking-effort (#15, #16): the `effort` param**, not `budget_tokens`. Opus 4.8 + Sonnet 4.6 support `effort` (Sonnet has no `xhigh`); Haiku 4.5 does not. #15 bands = **`low` / `high` / `max`** (common to Opus + Sonnet), thinking via `adaptive`, no Haiku probe. **Temperature (corrected 2026-06-16): Opus 4.8 rejects `temperature` outright; Sonnet 4.6 rejects it with thinking on.** → *SPEC control:* **omit `temperature` on every call** (provider default), record as `omitted` — uniform across the ladder. Pin `effort` at default `high` for all non-#15 cells (it affects *all* token spend, so it's a global lurking variable — Haiku has no such knob), and capture `usage.output_tokens_details.thinking_tokens`.
3. **Haiku probe for cache-heavy #10–12: yes, with the ≥4,096 cached-segment floor.** Revisit after first data.
4. **Sonnet–Opus tasks (#9, 13, 16, 18, 20, 21): Sonnet is the hypothesis**, Opus the over-service comparison (the "what you'd waste" baseline).

**Remaining matrix sub-question (for SPEC):** the over-service comparison pattern for the rest of the ladder — do the Haiku-tier tasks (#1–5) also run vs Opus to quantify the waste, and do any Sonnet-tier tasks get a Haiku down-probe? *Recommendation:* every task = hypothesized tier **+ Opus** (the waste baseline) for sub-Opus hypotheses; Opus-hypothesis tasks (#15) probe down to Sonnet; cache-heavy already carry the Haiku probe. Reserve the full three-tier ladder for a few representative tasks to show the gradient.

---

*Feeds: `SPEC.md` (run matrix) and `fixtures/` (frozen artifact + exact prompt per cell). Next: resolve §8, calibrate exact anchors against real inputs, then curate fixtures.*
