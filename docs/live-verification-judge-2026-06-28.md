# Live API Verification — Phase-1c quality judge — 2026-06-28

**SDK:** anthropic 0.109.2  |  **Judge model:** `claude-opus-4-8`

Verifies the judge-call surface that `analysis/quality.py` (`make_judge_fn`) relies on, per the
"Verify live, don't assert from memory" rule and `docs/phase1c-judge-spec.md` §2 ("VERIFY LIVE
before first use"). Done with a ~4-call billable probe (negligible spend: ~270 input + ~15 output
tokens total). Extends the model-surface facts in `docs/live-verification-2026-06-16.md`.

## Results

| Check | Result | Note |
|---|---|---|
| Baseline call, **thinking off** (param omitted), no temperature | ✅ works | `model_version = claude-opus-4-8`; returns plain text |
| `temperature` accepted? | ❌ **rejected (400)** | `invalid_request_error`: "`temperature` is deprecated for this model." → **omit it** (matches spec) |
| `output_config.format` json_schema with thinking off | ✅ accepted | returned valid `{"preference":"tie"}` against an enum schema |
| `make_judge_fn` path (`harness.client.stream_call`, thinking off, no temperature, prompt-instructed JSON + tolerant parse) | ✅ works | returned parseable `{"preference":"A"}` end-to-end |

## Decisions (carried into the frozen judge)

- **Judge calls omit `temperature`** (rejected outright) and run with **thinking off** (param
  omitted — on Opus 4.8 that is no-thinking). This matches judge-spec §2.
- **Verdict transport:** prompt-instructed JSON + a tolerant first-`{…}` parse, with **one retry**
  on an unparseable reply so a billable call isn't wasted. `output_config.format` json_schema is
  *also* accepted with thinking off and is recorded here as an available future hardening — it is
  **not** part of `judge_hash` (the hash covers model + K + prompts + rubrics + margin only;
  effort/output_config are not frozen-instrument fields).
- No `effort` is pinned for the judge (not a judge-spec / `judge_hash` field); calls use the model
  default unless `--effort` is passed to `analysis.quality`.

Probe script (not committed): `scratchpad/judge_probe.py`.
