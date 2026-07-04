# Phase 1d — build notes (decisions log)

**Status:** build-phase notes, **pre-data** (no 1d measurement exists). Pre-registration lives in
`docs/charter.md` v0.7 (§3 H7/H8, §5 Experiment 1d). This file records *build* decisions that are
**not** pre-registration commitments. Branch: `feat/phase1d-preregistration`. The frozen 1d
judge-spec (the hashed instrument contract, peer of `docs/phase1c-judge-spec.md`) is cut later, at
judge-freeze time; this is the decision that feeds it.

---

## Decision 1 — the cross-family judge is `google-genai` + a metered Gemini Developer API key

**Decided 2026-06-30.** The Phase 1d "honest ruler" (charter §5) is the standard **`google-genai`**
SDK calling a pinned Gemini Pro-tier model, authenticated by a **metered Gemini Developer API key**
(`GEMINI_API_KEY`). **Not** the consumer AI Pro subscription; **not** the agentic Antigravity SDK.

### Why — the subscription cannot back a programmatic, metered judge
The whole point of the judge is a *legible, persisted token meter*. We verified, against
authoritative sources (not agy's say-so — agy was wrong repeatedly here):

- **`agy -p` CLI logs carry no usable token counts.** The `~/.gemini/antigravity-cli/brain/<id>/`
  JSONL transcripts log conversation *steps* only; the per-conversation SQLite `.db` stores usage as
  an **unlabeled protobuf** (we raw-decoded it — the integers are there but the field→semantic map
  isn't recoverable, and `/usage` only rounds). So past `agy` renders are **not** post-hoc meterable.
- **The Antigravity SDK authenticates with a metered key or Vertex — no subscription path.** Its own
  README (`google-antigravity/antigravity-sdk-python`) shows `export GEMINI_API_KEY=…` or
  `vertex=True` + GCP ADC; **nothing** about `useG1Credits` / AI Pro. observability.md even warns
  about an "invalid API key." agy's "toggle `useG1Credits` and the SDK uses your subscription" claim
  is **refuted by the SDK's own docs** — that toggle is a CLI/app feature, not a programmatic one.

So a metered key is required **regardless** of which SDK we pick. Given that, the Antigravity SDK's
only draw (subscription savings) evaporates, and `google-genai` wins on every other axis:

| | Antigravity SDK | **`google-genai`** ✓ |
|---|---|---|
| Auth | Gemini key / Vertex | same key |
| Token metering | `usage_metadata` ✓ | `usage_metadata` ✓ |
| Shape | **agentic** (must lock down via `policies=[deny("*")]`) | **non-agentic, single-shot** |
| Stability | Research Preview (API may churn) | **GA** |
| Model pin | `model=…` | `model=…` |
| Dependency | compiled runtime binary | lightweight client |

The agentic SDK would only pay off if the judge needed tools/sub-agents — it explicitly does not.

### Model
- Pin a **Pro-tier** id (the 1c judge used the strongest tier "to avoid a weak judge"). The SDK
  default `gemini-3.5-flash` is too weak for a grader.
- **VERIFY-LIVE the exact id** from `https://ai.google.dev/gemini-api/docs/models/gemini` — the SDK
  docs explicitly say "do not assume valid model identifiers," and the current Gemini lineup is newer
  than the assistant's training cutoff. Pin a stable/dated build, hash it into the 1d judge-spec.

### Token capture (closes the 1c "judge tokens not persisted" gap)
`usage_metadata` exposes `prompt_token_count`, `cached_content_token_count`, `candidates_token_count`
(excludes thinking), `thoughts_token_count`, `total_token_count`. Persist all per call. Two guards
the Gemini docs themselves flag — and which match existing harness discipline:
- **Store `thoughts_token_count` separately** (thinking can balloon totals) — same posture as #15.
- **Reject/flag 0-on-error**: a failed call reports usage `0`. Don't silently record 0 at full
  apparent cost — mirror SPEC §5's #15/#16 null-thinking rejection rule.

### Auth / ops
- Key in `.env` as `GEMINI_API_KEY` (✅ added; payment set). `.env` is gitignored + untracked —
  **never commit it**. Load via the harness's env path; `genai.Client()` reads `GEMINI_API_KEY`.
- Judge runs **under the spend ceiling** with usage **persisted** (e.g. `results/<run>/judge_usage.jsonl`).
- Pre-run **micro-pilot** to pin the committed cost (as 1c did 12 calls → $2.96 est → $2.94 actual).
- Free tier exists but is rate-limited; use the paid key for a clean batch run.

---

## Seam sketch — `make_gemini_judge_fn` (drop-in for the existing `JudgeFn`)

> **SKETCH — not wired or tested.** The `google-genai` API surface (`genai.Client`,
> `generate_content`, `GenerateContentConfig`, `ThinkingConfig`, `usage_metadata`, `resp.text`) and
> the model id are asserted from memory and **must be verified against the installed SDK version**
> (`uv add google-genai` first — not yet installed). It reuses `analysis/quality.py`'s exact contract:
> `JudgeFn = Callable[[str], dict]` returning the parsed verdict (rubric → check-id keys; pairwise →
> `{"preference": ...}`), with the same 2-try retry and the same tolerant `_parse_json`.

```python
# analysis/judge_gemini.py  (sketch)
import json
from typing import Optional
from google import genai
from google.genai import types

from analysis.quality import JudgeFn, _parse_json   # reuse the contract + tolerant parser

def make_gemini_judge_fn(
    judge_model: str,                    # pinned Pro id — VERIFY-LIVE from ai.google.dev
    *,
    max_output_tokens: int = 2048,
    usage_sink: Optional[list[dict]] = None,   # per-call usage_metadata appended here -> persist it
) -> JudgeFn:
    client = genai.Client()              # reads GEMINI_API_KEY from env (.env must be loaded)

    cfg = types.GenerateContentConfig(
        max_output_tokens=max_output_tokens,
        # frozen-judge determinism — pin these in the 1d judge-spec; field names are VERIFY-LIVE:
        thinking_config=types.ThinkingConfig(thinking_budget=0),   # thinking OFF
        # temperature=<pinned>,                                    # decide + pin (or omit + lean on K=3)
        # response_mime_type="application/json", response_schema=<verdict schema>,  # optional hardening
    )

    def _judge(prompt: str) -> dict:
        last: Exception | None = None
        for _ in range(2):               # one retry, mirrors make_judge_fn
            resp = client.models.generate_content(model=judge_model, contents=prompt, config=cfg)
            um = getattr(resp, "usage_metadata", None)
            if usage_sink is not None:
                usage_sink.append({
                    "model": judge_model,
                    "prompt":     getattr(um, "prompt_token_count", None),
                    "cached":     getattr(um, "cached_content_token_count", None),
                    "candidates": getattr(um, "candidates_token_count", None),
                    "thoughts":   getattr(um, "thoughts_token_count", None),
                    "total":      getattr(um, "total_token_count", None),
                })
            # 0-on-error guard: if total==0 the call likely failed — flag, don't trust the verdict.
            try:
                return _parse_json(resp.text)
            except (ValueError, json.JSONDecodeError) as e:
                last = e
        raise last  # type: ignore[misc]

    return _judge
```

**CLI wiring** (replaces the `anthropic.Anthropic()` branch when the judge family is Gemini):
```python
usage_log: list[dict] = []
judge_fn = make_gemini_judge_fn(judge["judge_model"], usage_sink=usage_log)
# ... after analyse(), dump usage_log -> results/<run>/judge_usage.jsonl   (persist judge tokens)
```
The 1d **judge manifest** gains a `provider: gemini` (or `judge_family`) field so the CLI dispatches;
`judge_model` becomes the pinned Gemini id; recompute + pin a new `judge_hash` (cut a new instrument —
never edit bytes under 1c's frozen hash).

---

## Build prerequisites / VERIFY-LIVE checklist (before freezing the 1d judge)
- [x] `uv add google-genai` (2.10.0); `genai.Client()` reads `GEMINI_API_KEY` from the loaded `.env` (confirmed by the smoke + step-0 probe).
- [x] Pin the exact Pro model id: **`gemini-3.1-pro-preview`** (step-0 re-probe 2026-06-30). Confirmed it accepts `thinking_config(thinking_budget=256)` — no 400. **Budget is SOFT, not a hard cap:** tiny probe spent ~139/256, but a real 610-tok rubric prompt (E2E smoke) spent 434 — thinking scales with prompt size and can exceed the budget, so the later micro-pilot must pin cost on *real* prompts. (`response_schema` unused — optional future hardening.)
- [x] Temperature handling: **pinned `temperature=0`** (deterministic + replayable), recorded in `fixtures/judge/manifest-phase1d.yaml` `judge_config`.
- [x] `resp.text` + `resp.usage_metadata.*` attribute names confirmed against google-genai 2.10.0 (smoke + probe).
- [ ] One micro-pilot to pin cost; set the 1d spend ceiling. *(deferred — later phase)*
- [ ] Re-verify the format-neutral rubric + pairwise prompts render under the new judge (charter §5). *(deferred — later phase; the DRAFT manifest reuses 1c's prompts/rubrics as placeholders until then.)*

## Build status — 2026-06-30 (judge instrument, scoped)
Built + tested (208 pass, zero spend on the suite): `analysis/judge_gemini.py`
(`make_gemini_judge_fn` + testable `_build_judge` core; logs every attempt incl. failures to a
usage sink), the `provider`/`judge_config` fold in `analysis/quality.py:load_judge` (1c hash proven
byte-unchanged), CLI provider dispatch + `out/judge_usage.jsonl` persistence in `main()`, and the
**DRAFT** `fixtures/judge/manifest-phase1d.yaml`. The manifest is DRAFT, not FROZEN: `judge_hash` is
computed but not asserted (gates on `status == FROZEN`), so the placeholder rubric can be replaced
without a tripwire. **FREEZE** (final `judge_hash` pinned) waits on the format-neutral rubric +
micro-pilot phase.

## Format-neutral rubric — mechanism (2026-06-30, charter §5.147)
**The 1c coverage hole:** pairwise eligibility gated on the *full* absolute rubric, which included the
format code-checks (#6 ≤60 words / 2–3 hashtags; #9 six sections / 720–880 words). Skill-off/loose
output naturally misses those → `absolute_pass=False` → **0 eligible skill-off pairs** → H6 clause 2
("skill narrows the gap *more than* a loose prompt") was unanswerable.

**The fix — grade substance independent of structure.** Eligibility is now **data-driven from the
frozen instrument**: a rubric check tagged `gate: true` is the *only* thing that gates the pairwise.
1d tags exactly **`faithful`** (per #6/#9) — so a faithful but format-noncompliant loose output is
**eligible**, closing the hole and making the loose-vs-loose baseline measurable. Everything else
(CTA, hook, word/hashtag/section counts) is still scored + reported by arm, but never gates. The
pairwise prompt was already substance-first ("Format compliance is NOT a discriminator"), so **no
prompt-file change** — the format-neutrality lives in the checks + the gate, not the template.

**Design decisions (owner-approved 2026-06-30):** gate lives in the *manifest* (hashed instrument),
not in code, so it generalizes to the ~9-task ladder and is part of `judge_hash`; scope = the
mechanism on the reused #6/#9 (per-task check text for the wider ladder rides along at FREEZE).

**Code (`analysis/quality.py`):** new `eligibility(task_id, code, llm, rubrics)` — all `gate: true`
checks pass ⇒ eligible; **no gate flag ⇒ fall back to legacy `absolute_pass`** so 1c is *not*
reinterpreted. `analyse` sets `g["eligible"]`; `_pairwise` gates on it (via `_elig`, which falls back
to `absolute_pass`) and now loops **three arms** `(off, neutral, on)` (H8's neutral arm; absent in 1c
data). `absolute_pass` is retained as the reported, format-inclusive H5 quality floor.

**Validation:** proven free by unit tests (a faithful/format-noncompliant pair: excluded under the old
gate → eligible under the new; 1c manifest has no gate flags; full suite 215 pass). A **billable**
re-grade of the real 1c `results/run-20260628…` #6/#9 outputs with the Gemini judge (to show real
eligible-pair counts, ~$3–5) is the optional confirmation on real data — flag before running.

**Still deferred to FREEZE:** the ~9-task cap/mandate ladder + per-task check text, neutral-system
blocks, `runs/phase1d.yaml`, the micro-pilot cost + $100 ceiling, and pinning the final `judge_hash`.

## Freeze-phase decomposition (2026-06-30)
Six sub-projects, dependency-ordered: **S1** harness neutral arm (independent) → **S2** task ladder
(new fixtures/loose-prompts/skills for ~6 generative tasks) → **S3** cap/mandate classification +
skill-off pilot (freeze labels in `runs/phase1d.yaml`) + **S4** per-task neutral blocks → **S5**
`runs/phase1d.yaml` (3 arms × 3 models × ~9 tasks × N=20) → **S6** micro-pilot cost + $100 ceiling →
FREEZE judge. Two hard pre-registration calls gate S2–S5: the **task roster** (which ~9 generative
tasks, cap/mandate balance) and the **classification rule** (which skill-off mean; the sign formula
breaks per-model — #9-Opus natural output *exceeds* the 800w constraint yet behaves as a mandate —
and the new tasks have no measured mean, so either an a-priori design call or a billable skill-off
pilot). Owner picked: **S1 first, then design the spine.**

## Freeze-phase S1 — harness neutral arm (BUILT 2026-06-30, TDD)
The 3rd factorial arm (charter §5 H8). Representation: a **dual field** — `CallConfig.neutral` (the
neutral-block id) alongside `skill`, **mutually exclusive** (a call injects at most one `system`
block). Back-compat is the same trick as the skill axis: `config_hash` drops `neutral` when None, so
1a/1c hashes are byte-identical (proven — the cross-run recompute test still passes); `CellId.key()`
adds a `:skill-neutral` suffix only on the neutral arm. `CellId.skill_arm` gains `"neutral"`; the
record's arm-agreement check is now arm-aware (skill_hash ⟺ a block injected; skill_arm ∈
{off,neutral,on} agrees with which of skill/neutral is set). `skill_hash` is reused as "the injected
system-block hash" (skill OR neutral; skill_arm disambiguates).

**Opt-in per task:** a factorial task gets the neutral arm ONLY if it declares a `neutral` id;
without one (the #4 placebo, or any 1c matrix) it stays 2-arm {off,on} — so the frozen 1c run is
unperturbed. Files: `harness/{schema,hashing,config,expand,assemble,run}.py` + a **separate**
`fixtures/neutral/manifest.yaml` (reuses `SkillEntry`; kept apart from the frozen skills registry so
a neutral block is by construction NOT a skill). Neutral blocks authored + frozen for the two locked
tasks: `neutral/short-form-copy-neutral-v1.md` (144w vs skill 136w, +5.9%) and
`neutral/long-form-draft-neutral-v1.md` (169w vs 158w, +7.0%) — structure-free role/quality prose,
no format/sections/scope/length cues, not self-labeled as a control. 12 new tests; full suite 227.
**Pending before the real run:** owner + Gemini review of the neutral-block text (mirroring the 1c
skill freeze); neutral blocks for the rest of the roster land with S2/S4. *(Done 2026-07-02 — the
review found scope clauses in the v1 blocks; superseded by -v2. See "S2 + neutral-block review"
below.)*

## Freeze-phase design spine — LOCKED 2026-06-30 (pre-data; owner-decided)
Grounded in real day-to-day knowledge work (owner steer: tasks that mirror what people actually do).

**Roster — 8 generative tasks, 4 cap / 4 mandate** (final identities + labels freeze in
`runs/phase1d.yaml` before the run, invariant 4):
- **CAP:** #6 announcement/social post *(ready)* · #7 meeting-minutes / recap-email from a transcript ·
  #8 extract action-items/fields · #1 draft/reply email.
- **MANDATE:** #9 decision memo from a brief *(ready)* · #15 strategy/planning brief *(thinking-on)* ·
  project-status report from notes · **spec-draft from a requirement + a format example**.
- **#7 leans CAP** (concise recap-email — the owner's actual workflow).
- **spec-draft** is the purest thesis instance — the format/example the owner pastes in *is* the skill;
  scoped to a SMALL band (compact requirement + compact example + bounded output) — the priciest cell,
  sized deliberately for the S6 ceiling.
- **Departure from the charter §5 candidate list (flagged, not silent):** #13 multi-source research is
  DROPPED (heaviest build — needs a frozen source-set fixture) in favor of the owner's real
  high-frequency tasks (project-status report, spec-draft). Within the §5 latitude ("candidates …
  plus 2–3 more; final identities frozen in `runs/phase1d.yaml`"); pre-data, so this finalizes rather
  than retrofits. **H7/H8 + kill-conditions unchanged.**

**Cap/mandate classification rule — LOCKED.** Reference = **skill-off mean output in WORDS** (measured
from `response_text`, tokenizer-independent — NOT token÷1.3, which overstated Opus by ~+35% and
manufactured a phantom "#9-Opus cap edge case"). **One label per task**: CAP if the scaffold's demand
is clearly below the natural word range on all three models, MANDATE if clearly above; boundary tasks
(constraint ≈ natural on any model — e.g. 1c's #9-Sonnet, +3%) are flagged/excluded from the headline
H7 test. **New tasks:** a cheap **billable skill-off pilot** (words; ~5–10 calls × 3 models × 6 tasks)
measures the natural range BEFORE labels freeze, so each skill's constraint sits clearly outside it.
Measured anchors (1c, words): **#6 CAP** (natural 139–212w; cap ≤60w) · **#9 MANDATE** (natural
255–696w; mandate ~800w + 6 sections).

**Build order (S2 → S3/S4 → S5 → S6):** (1) author + freeze fixtures + loose prompts for the 6 new
tasks [non-billable]; (2) skill-off pilot → measure natural word ranges [**BILLABLE — flag first**];
(3) design + author skills (cap/mandate demand set outside the measured range) + length-matched
neutral blocks [non-billable; owner + Gemini review, mirroring the 1c freeze]; (4) freeze cap/mandate
labels + the matrix in `runs/phase1d.yaml` [S5]; (5) micro-pilot cost + $100 ceiling → FREEZE the
judge (pin `judge_hash`) [S6].

## S2 + neutral-block review — 2026-07-02 (owner + independent Gemini review; pre-freeze, pre-data)

The step-1 review of the six S2 draft artifacts (`fixtures/task-{01,07,08,15,23,24}-*/`) and the two
frozen S1 neutral blocks. Owner review first (commit `7ab2c1d`: #15/#24 rewritten as true
example-style — they had claimed example content while holding only meta-instructions; #23's example
moved off-domain from an aviation weather feed, whose degraded-mode item overlapped the PFCS offline
requirement, to a payroll export service; #24's example de-migrated to avoid lexical overlap with the
Atlas migration notes). Then an independent Gemini review (`agy`, inline-context) on the corrected
drafts. Its four MUST-FIX findings, triaged:

- **#1 scaffold bleed (ADOPTED).** The example was a billing/refund reply — same domain as the input
  fixture, with a copyable fact (*"back on your card within 3–5 business days"*) colliding with the
  input's "5–7 business days" refund promise. Example swapped to an account-email-change reply: same
  format (acknowledge → bullets → next step with a timeframe → sign-off), zero money content.
- **#8 loose prompt carried a hidden format cue (ADOPTED).** "Extract the key **structured** details"
  → "Extract the key details". The task's structure lives in the skill arm, not the natural request.
- **v1 neutral blocks carried treatment ingredients (ADOPTED — the consequential one).** Both blocks
  held faithfulness/anti-invention clauses mirroring their skills' scope constraints, plus an
  "even-handedly" echo of the #9 skill and a soft brevity cue ("in a busy feed") in #6's. Charter §3
  H8 defines the skill's structure under test as "format/schema + **scope**/length constraints" — so
  these were scope constraints sitting in the control arm, biasing toward a **false kill** of H8
  (anti-invention plausibly tightens CoV_output by itself). Cut **-v2** blocks (v1 bytes untouched):
  pure role/quality framing, re-length-matched (#6 129w/136w = −5.1%; #9 155w/158w = −1.9%), hashes
  pinned in `fixtures/neutral/manifest.yaml`; v1 entries retained but marked SUPERSEDED. **Standing
  rule for the six S4 blocks:** role/quality framing only — no faithfulness/scope clauses, no stance
  words ("even-handed"), no audience-attention cues that imply length.
- **#15 label-inversion risk (MODIFIED — pilot-gated, not edited now).** Gemini flags that a natural
  thinking-on strategy brief likely runs *longer* than the scaffold-compliant ~300–450w, which would
  invert the intended MANDATE into a cap. Direction is credible (1c's #9 hit 696w natural without
  thinking) — but the locked classification rule already gates labels on the measured pilot range, so
  editing the scaffold *before* the pilot would be tuning to a guess. **Pre-committed decision rule:**
  if the pilot's natural range on any model reaches the scaffold-compliant length, raise the
  scaffold's demand (explicit word floor + per-section depth) and re-check against the measured
  range; if it still won't separate, flag/exclude #15 from the headline H7 test (boundary rule).

One Gemini nice-to-have and two owner findings, recorded as pre-committed pilot decisions:

- **#24 boundary risk (owner + Gemini agree).** The scaffold's own anti-invention rule ("use only
  what the notes provide") caps how far above natural the mandate can push. Post-pilot options, in
  order: per-section **elaboration** demands (impact + plan per risk — elaboration is allowed,
  invention is not); else flag/exclude as boundary. Note Gemini's proposed remedy (expand the input
  notes) is rejected — richer input *raises* natural output and makes the mandate separation harder.
- **Numeric demand cues (owner).** H7's frozen label is `sign(scaffold length constraint − skill-off
  mean output)` — the formula needs a number on the scaffold side, and only #8 is quasi-numeric
  today (8 one-line fields). The post-pilot tuning pass must add an explicit numeric length cue to
  every scaffold (cap ceilings / mandate floors), placed clearly outside the measured natural range —
  the 1c precedent (#6 "≤ 60 words", #9 "~800 words ±10%").
- **Scaffold-style note (owner, for the eventual report).** The 1d skill arm mixes two scaffold
  styles: instruction-style (#6/#9, frozen 1c artifacts) and example-style (the six new tasks, per
  the owner's real workflow). Each task's on/off contrast is within-task so H7 is unaffected, but the
  ladder-level aggregate pools both styles — record it as a described design property, not a confound
  to fix.

## Non-billable build batch — 2026-07-02 (everything runnable up to the first billable gate)

All remaining non-billable work, built in one pass (SPEC §3c is the run-matrix-side summary). The
first billable gate (the skill-off pilot) is now fully staged behind a cost estimate + owner flag.

**Fixture registry frozen (`fixtures/manifest-phase1d.yaml`).** The 6 new S2 fixtures hashed
2026-07-02 (post-review) — frozen BEFORE the pilot runs on them, so the measured natural ranges bind
to immutable inputs. Reused 1c #4/#6/#9 entries copied byte-identically. `recorded_token_counts`
deliberately TBD until the pilot cost-gate (free `count_tokens`; counts are cost inputs, not content).

**Skill-off pilot staged (`runs/phase1d-pilot.yaml`).** 6 tasks × 3 models × arms:[off] × N=10 =
180 calls, ceiling $10, `phase0-calibration` hygiene (design input only, never H-data). N=10 chosen
from the spine's "~5–10" so a per-model natural RANGE is visible, not a point — owner confirms N at
the cost gate. Dry-run verified: 18 units expand, every unit assembles under `require_frozen=True`,
`response_text` persists (role_label factorial).

**Harness mechanics for the pilot (TDD, in `tests/test_phase1d_pilot.py`).** (1) `TaskSpec.arms`
restricts factorial arms; skill required only when "on" is in the effective set; a YAML-1.1
coercion maps bare `off`/`on` (parsed as booleans) back to arm names. (2) Factorial `thinking` is
honored (1a's #15 convention arrives in the factorial world): **model-natural** — `adaptive` on
Sonnet/Opus, `off` on Haiku (Haiku supports neither the effort knob nor adaptive thinking,
live-verification 2026-06-16; `enabled` needs a budget the harness doesn't thread → fails loud at
expansion). ⚠️ **OWNER SIGN-OFF at the pilot gate:** this is the "#15 thinking-on handling" decision
— the alternative (thinking off everywhere) loses #15's tier-pull character; the cost is that
#15-Haiku cells are natural-config, not thinking-matched, exactly like the effort knob already is.
(3) `TaskSpec.h7_label` ("cap"|"mandate", factorial-only) is where labels freeze in
`runs/phase1d.yaml`. All back-compat proven (1c expansion byte-unchanged; skill-less config_hash
identical to the pre-skill schema).

**Judge rubrics authored for all 8 tasks (`fixtures/judge/manifest-phase1d.yaml`, still DRAFT).**
Every generative task: `faithful` as the ONLY pairwise gate (charter §5.147) + 1–3 semantic checks
+ objective format checks now declared IN the manifest as `code_checks`
(word_max / word_range / sections_all / regex_count — interpreted by `analysis/quality.py`, never
sent to the LLM) so they ride inside `judge_hash`. #6/#9 keep their 1c check text + legacy in-code
checks (1c never reinterpreted). Numeric values (word caps, count floors) are PROVISIONAL — they
track the post-pilot scaffold cues and are re-checked at FREEZE; #15/#24 get their word_range floors
only once those cues exist.

**Analysis modules (all synthetic-tested, zero spend).** `analysis/h7.py` — per-cell Δmean sign vs
the frozen label, unlabeled cells reported-but-excluded; the at/below-chance statistical read
belongs to the report. `analysis/h8.py` — ratio R with the pre-registered bands (<⅓ supported /
⅓–½ ambiguous / ≥½ killed). **Build-time operationalization (charter left "clear reduction"
unnumbered):** a cell is SCORED for H8 only when the skill's relative CoV_output reduction is
**≥ 25%** — `H5_COV_REL`, the H5 practically-meaningful bar, imported from `analysis/h5.py` as the
single source. Logged here pre-data; flag, don't retrofit. Float note: an R sitting numerically at
a band edge is float-sensitive — the report must treat near-boundary values as such.
`analysis/h5.py` — rows now carry the neutral arm's n/mean/CoV (blank on 1c data; off/on contrast
untouched). `analysis/quality.py` — task set, grader dispatch, code checks, and absolute_pass are
now data-driven from the judge manifest with legacy fallbacks (1c byte-identical; proven by the
untouched 1c test suite).

**Spend/rate machinery verified for 1d scale (no change needed).** `SpendGuard` is built
unconditionally per run: `max_calls = expanded calls + 1`, token budgets derived from
`meta.cost_ceiling_usd` + the mandatory `--usd-prior`, attempts counted pre-call (a failing loop
trips the ceiling). Backoff = 5 exponential retries; 1d has no cache cells, so the backoff↔TTL
hazard doesn't apply. The $100 ceiling is just `cost_ceiling_usd: 100` in `runs/phase1d.yaml` at S6.

**Open at the next (billable) gates, in order:** (1) pilot cost estimate → owner flag (fills
`recorded_token_counts` via free `count_tokens`; confirms pilot N and the #15 thinking decision) →
run the pilot; (2) post-pilot: tune scaffolds w/ numeric cues → freeze skills + 6 neutral blocks →
freeze labels in `runs/phase1d.yaml` (+ add #23/#24 to charter §8 with a v0.8 log line — an
owner-signed charter edit, deliberately not made unilaterally here); (3) judge micro-pilot + live
re-verify → FREEZE judge_hash; (4) the main run under $100.

## S3/S4/S5 staged — 2026-07-02 (pilot ran; artifacts staged for the owner's freeze)

**Pilot (gate 1) RAN, owner-approved:** `results/run-20260702T133840Z-64d579/` — 180/180 `end_turn`,
$2.09 vs the $4.16 point estimate ($10 ceiling untouched). Owner cross-checked the Console:
**165,841 total tokens reported; the records sum to 165,841 — delta 0** (instrument validated
against the provider's own meter). The estimate halved because **adaptive thinking barely fired**
(#15 Sonnet/Opus: 0–62 thinking tok/call vs the 1a anchor's 5–10k on the 1a brief) — thinking spend
is prompt-contingent. Natural ranges + label read: `analysis/output/phase1d-pilot-findings.md`.

**Scaffold cues (S3) applied + second Gemini review triaged** (commit `be55210`): caps #1 ≤100w /
#7 ≤100w / #8 ≤90w (below every model's natural min); mandates #15 ~1400w / #23 ≥12 reqs·≥3 ACs·
~1450w / #24 ~550w+elaboration (+23–27% over natural max — the #9 precedent margin). Gemini's label
table: clean on all six. Adopted: #23 example now shows 3 ACs (contradicted its own rule), #24
example demonstrates its elaboration rule, and the three mandates' `faithful` check text clarified —
*reasoned elaboration ≠ invention* — defusing the length-floor/faithful-gate collision it flagged
as a coverage-hole risk. Pushed back: padding #15/#23 examples to demanded depth (a ~1400w example
forces a ~1400w neutral block via the ±10% match — an absurd control; the numeric cue carries the
demand).

**Neutral blocks (S4) authored + third Gemini review triaged.** Six blocks, length-matched −2.3% to
−7.8%, canonical in `fixtures/neutral/`, registered `frozen:false`. Gemini (given the paired skills
+ the −v2 exemplars as calibration) flagged semantic treatment-leaks; **adopted** — cut "difficult
conversation" (#1: injected premise/stance), the audience-moved-on/"quietly" framing (#7: brevity
cue by the "busy feed" precedent), "for their company and no other / rather than generic business
advice" (#15: specificity-grounding directive), "real engineering rather than paperwork" + "carry
that intent forward with care" (#23: depth cue + fidelity directive), and the "treat the notes as
…" directive (#24). **Pushed back, recorded:** #8's "key details" mirrors the loose prompt's own
task naming (all arms share it — task-direction, not a scope filter); #24's "honest" described the
notes, not the output (the surrounding directive was cut anyway). Every replacement is same-register
role/quality prose; length bands re-verified; cue screen clean.

**Matrix (S5) staged:** `runs/phase1d.yaml` — 78 cells / 1,560 calls, `h7_label` frozen in-matrix
(caps #1/#6/#7/#8, mandates #9/#15/#23/#24, #4 unlabeled placebo 2-arm), #15 thinking-adaptive
(model-natural), $100 ceiling. Dry-run verified: expansion 78/27-24-27 arms, every staged manifest
sha256 matches its bytes, every unit assembles, and `require_frozen` **refuses** the staged skills —
the matrix cannot fire before the owner flips `frozen:true`. Registries:
`fixtures/skills/manifest-phase1d.yaml` (6 new + 3 reused 1c entries, byte-identical) and the
extended `fixtures/neutral/manifest.yaml`. The `fixtures/task-*/scaffold-example-DRAFT.md` drafts
are deleted in the freeze commit (canonical bytes live in `fixtures/skills/`).

**Remaining before the main run:** owner freeze (skills + neutral blocks: flip `frozen:true`, no
byte edits) → charter §8 #23/#24 addition + v0.8 log line (owner-signed) → judge FREEZE (micro-pilot
+ live Gemini re-verify + pin `judge_hash`) → S6 pre-run cost estimate vs the $100 ceiling → run.
