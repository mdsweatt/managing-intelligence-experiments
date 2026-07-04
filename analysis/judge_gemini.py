"""analysis/judge_gemini.py — the Phase-1d cross-family judge fn (charter v0.7 §5; build notes).

Phase 1d swaps the quality judge to a CROSS-FAMILY model to remove the Opus-vs-Opus self-preference
risk 1c logged (charter §5 "the honest ruler"). This module is the Gemini half of the JudgeFn seam:
`make_gemini_judge_fn` returns a `JudgeFn` that is byte-compatible with
`analysis.quality.make_judge_fn` — same call contract (a rubric prompt -> a dict keyed by check ids;
a pairwise prompt -> {"preference": "A"|"B"|"TIE"}), the same 2-try retry, and the same tolerant
`_parse_json`. The one addition is an operational fix 1c missed: it captures the full Gemini
`usage_metadata` for EVERY attempt (successes AND failures — a failed call is still input-billed)
into a caller-supplied sink, so the judge's token spend is persisted and the billing dashboard
reconciles (charter §5 "persists its token usage").

The judge is METERED: `genai.Client()` reads `GEMINI_API_KEY` from the loaded `.env` (docs/phase1d-
build-notes.md — NOT the AI Pro subscription, NOT the Antigravity SDK). The model + thinking config
are pinned in `fixtures/judge/manifest-phase1d.yaml` and driven from there.

Verified-live SDK surface (google-genai 2.10.0): `client.models.generate_content(model, contents,
config)`; `types.GenerateContentConfig(max_output_tokens, temperature, thinking_config=
types.ThinkingConfig(thinking_budget=...))`; `resp.text` (raises on a blocked reply); and
`resp.usage_metadata.{prompt,cached_content,candidates,thoughts,total}_token_count`. gemini-2.5-pro
MANDATES thinking (thinking_budget=0 -> HTTP 400) but accepts a fixed budget — so there is no safe
default budget; it is a required, manifest-pinned parameter.
"""
from __future__ import annotations

import json
from typing import Any, Callable, Optional

from analysis.quality import JudgeFn, _parse_json


def _usage_record(judge_model: str, resp: Any, *, attempt: int, ok: bool,
                  error: Optional[str]) -> dict:
    """One usage-sink row per attempt. Mirrors gemini_smoke.py's defensive getattr extraction so a
    missing/None `usage_metadata` (a blocked/failed call) still records total=0 — flaggable, never
    silently trusted (the 0-on-error guard)."""
    um = getattr(resp, "usage_metadata", None) if resp is not None else None

    def _f(name: str) -> int:
        return (getattr(um, name, None) or 0) if um else 0

    return {
        "model": judge_model,
        "attempt": attempt,
        "ok": ok,
        "error": error,
        "prompt": _f("prompt_token_count"),
        "cached": _f("cached_content_token_count"),
        "candidates": _f("candidates_token_count"),
        "thoughts": _f("thoughts_token_count"),
        "total": _f("total_token_count"),
    }


def _build_judge(call_fn: Callable[[str], Any], judge_model: str,
                 usage_sink: Optional[list[dict]]) -> JudgeFn:
    """The provider-agnostic retry/usage core. `call_fn(prompt)` performs one generate_content and
    returns the response object; kept separate from the SDK wiring so it is testable with a fake
    (zero spend, no network). Two attempts, mirroring `make_judge_fn`: every attempt — a raised API
    error, an unparseable/blocked reply, or a success — appends a usage row, so all spend is logged."""
    def _judge(prompt: str) -> dict:
        last: Exception | None = None
        for attempt in range(2):
            try:
                resp = call_fn(prompt)
            except Exception as e:  # network / API error — the call may still be input-billed
                if usage_sink is not None:
                    usage_sink.append(_usage_record(judge_model, None, attempt=attempt,
                                                    ok=False, error=repr(e)))
                last = e
                continue
            try:
                verdict = _parse_json(resp.text)   # resp.text raises ValueError on a blocked reply
            except (ValueError, json.JSONDecodeError) as e:
                if usage_sink is not None:
                    usage_sink.append(_usage_record(judge_model, resp, attempt=attempt,
                                                    ok=False, error=repr(e)))
                last = e
                continue
            if usage_sink is not None:
                usage_sink.append(_usage_record(judge_model, resp, attempt=attempt,
                                                ok=True, error=None))
            return verdict
        raise last  # type: ignore[misc]

    return _judge


def make_gemini_judge_fn(
    judge_model: str,
    *,
    thinking_budget: int,
    temperature: float = 0.0,
    max_output_tokens: int = 2048,
    usage_sink: Optional[list[dict]] = None,
) -> JudgeFn:
    """Wrap a pinned Gemini model as a JudgeFn (Phase-1d cross-family judge). Contract-identical to
    `analysis.quality.make_judge_fn`. `thinking_budget` is REQUIRED and pinned from the judge
    manifest (gemini-2.5-pro rejects 0, so there is no safe default). `usage_sink`, if given,
    receives one row per attempt incl. failures so the metered spend is persisted."""
    from google import genai
    from google.genai import types

    client = genai.Client()  # reads GEMINI_API_KEY from the loaded .env
    cfg = types.GenerateContentConfig(
        max_output_tokens=max_output_tokens,
        temperature=temperature,
        thinking_config=types.ThinkingConfig(thinking_budget=thinking_budget),
    )

    def call_fn(prompt: str) -> Any:
        return client.models.generate_content(model=judge_model, contents=prompt, config=cfg)

    return _build_judge(call_fn, judge_model, usage_sink)
