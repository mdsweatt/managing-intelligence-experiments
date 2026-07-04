"""Tests for analysis/judge_gemini.py — the Phase-1d cross-family (Gemini) judge fn.

The SDK wiring in `make_gemini_judge_fn` is thin; the risk lives in the retry + usage-logging core
(`_build_judge`), which is exercised here with a FAKE `call_fn` — zero spend, no network, no
GEMINI_API_KEY needed. Mirrors tests/test_analysis_quality.py's injected-fake-judge style.
"""

from __future__ import annotations

import pytest

from analysis import judge_gemini as jg


# --------------------------------------------------------------------------- fakes

class FakeUM:
    """Stand-in for google-genai's usage_metadata (defensive getattr in _usage_record)."""

    def __init__(self, *, prompt=0, cached=0, candidates=0, thoughts=0, total=0):
        self.prompt_token_count = prompt
        self.cached_content_token_count = cached
        self.candidates_token_count = candidates
        self.thoughts_token_count = thoughts
        self.total_token_count = total


class FakeResp:
    """Stand-in for a generate_content response. `text=None` mimics a blocked reply, where
    google-genai raises ValueError on `.text` access (still input-billed, so usage is populated)."""

    def __init__(self, text, um=None):
        self._text = text
        self.usage_metadata = um

    @property
    def text(self):
        if self._text is None:
            raise ValueError("no candidates / blocked")
        return self._text


def _seq(*resps):
    """A call_fn that returns the given responses in order."""
    box = list(resps)
    return lambda prompt: box.pop(0)


# --------------------------------------------------------------------------- happy path

def test_success_returns_verdict_and_logs_one_usage_row():
    sink: list[dict] = []
    resp = FakeResp('{"preference": "A"}', FakeUM(prompt=100, candidates=20, total=120))
    judge = jg._build_judge(_seq(resp), "gemini-x", sink)
    assert judge("RESPONSE A: ...") == {"preference": "A"}
    assert len(sink) == 1
    assert sink[0]["ok"] is True and sink[0]["attempt"] == 0
    assert sink[0]["prompt"] == 100 and sink[0]["candidates"] == 20 and sink[0]["total"] == 120
    assert sink[0]["error"] is None


def test_rubric_shape_passes_through_unchanged():
    resp = FakeResp('{"cta_valid": "pass", "hook_quality": 2, "faithful": "pass"}', FakeUM(total=40))
    judge = jg._build_judge(_seq(resp), "gemini-x", None)   # usage_sink=None is allowed
    out = judge("rubric prompt")
    assert out == {"cta_valid": "pass", "hook_quality": 2, "faithful": "pass"}


# --------------------------------------------------------------------------- retry / failure logging

def test_parse_failure_then_success_logs_both_attempts():
    sink: list[dict] = []
    bad = FakeResp("not json at all", FakeUM(total=10))
    good = FakeResp('{"cta_valid": "pass"}', FakeUM(total=50))
    judge = jg._build_judge(_seq(bad, good), "gemini-x", sink)
    assert judge("rubric prompt") == {"cta_valid": "pass"}
    assert [r["ok"] for r in sink] == [False, True]
    assert [r["attempt"] for r in sink] == [0, 1]
    assert sink[0]["total"] == 10 and sink[1]["total"] == 50   # spend logged for BOTH attempts


def test_blocked_reply_is_logged_with_spend_then_retried():
    sink: list[dict] = []
    blocked = FakeResp(None, FakeUM(prompt=80, total=80))      # .text raises -> failed attempt
    good = FakeResp('{"preference": "TIE"}', FakeUM(total=90))
    judge = jg._build_judge(_seq(blocked, good), "gemini-x", sink)
    assert judge("RESPONSE A: x RESPONSE B: y") == {"preference": "TIE"}
    assert sink[0]["ok"] is False and sink[0]["total"] == 80   # blocked call is still input-billed
    assert sink[1]["ok"] is True


def test_two_parse_failures_raise_and_log_two_failures():
    sink: list[dict] = []
    bad = FakeResp("nope", FakeUM(total=5))
    judge = jg._build_judge(lambda p: bad, "gemini-x", sink)   # same bad resp every attempt
    with pytest.raises(ValueError):
        judge("rubric prompt")
    assert len(sink) == 2 and all(r["ok"] is False for r in sink)


def test_api_error_is_logged_and_flagged_zero_then_raised():
    sink: list[dict] = []

    def boom(prompt):
        raise RuntimeError("503 unavailable")

    judge = jg._build_judge(boom, "gemini-x", sink)
    with pytest.raises(RuntimeError, match="503"):
        judge("rubric prompt")
    assert len(sink) == 2 and all(r["ok"] is False for r in sink)
    assert all("503" in (r["error"] or "") for r in sink)
    assert all(r["total"] == 0 for r in sink)   # 0-on-error guard: no usage_metadata to trust


def test_usage_record_none_response_is_all_zero():
    rec = jg._usage_record("gemini-x", None, attempt=1, ok=False, error="boom")
    assert rec["total"] == 0 and rec["prompt"] == 0 and rec["model"] == "gemini-x"
    assert rec["ok"] is False and rec["error"] == "boom" and rec["attempt"] == 1
