"""Tests for harness.guard — the hard spend ceiling (a loop bug must not empty the card).

The guard counts MEASURED tokens + calls (exact, from the usage vector) and aborts on
breach. The only dollar notion is an explicit, conservative SAFETY prior used once to turn
the $ ceiling into a token budget — kept separate from analysis prices/ (which stay TBD).
"""

from __future__ import annotations

import pytest

from harness.guard import CeilingBreach, SpendGuard, tokens_for_dollar_ceiling
from harness.schema import UsageVector


def _usage(inp=0, out=0, cache_read=0, cache_create=0) -> UsageVector:
    raw = {
        "input_tokens": inp,
        "output_tokens": out,
        "cache_read_input_tokens": cache_read,
        "cache_creation_input_tokens": cache_create,
        "cache_creation": {
            "ephemeral_5m_input_tokens": cache_create,
            "ephemeral_1h_input_tokens": 0,
        },
    }
    return UsageVector.from_raw(raw)


def test_guard_counts_the_attempt_before_the_call():
    # register_attempt is the PRE-call gate: it counts the attempt and enforces the ceiling,
    # so a failing/retried call (which never reaches register_usage) is still bounded.
    g = SpendGuard(max_calls=2)
    g.register_attempt()
    g.register_attempt()
    assert g.calls == 2
    with pytest.raises(CeilingBreach):
        g.register_attempt()  # 2 attempts already made


def test_register_usage_does_not_advance_the_call_count():
    # The call is counted at attempt time; register_usage only adds token totals.
    g = SpendGuard(max_calls=10)
    g.register_attempt()
    g.register_usage(_usage(inp=10, out=5))
    assert g.calls == 1


def test_guard_breaches_on_input_token_ceiling():
    g = SpendGuard(max_calls=100, max_input_tokens=100)
    g.register_usage(_usage(inp=60))
    with pytest.raises(CeilingBreach):
        g.register_usage(_usage(inp=60))  # 120 > 100


def test_guard_counts_cache_tokens_as_billed_input():
    g = SpendGuard(max_calls=100, max_input_tokens=1000)
    with pytest.raises(CeilingBreach):
        g.register_usage(_usage(inp=10, cache_read=2000))  # cache_read is billed input


def test_guard_breaches_on_output_ceiling():
    g = SpendGuard(max_calls=100, max_output_tokens=50)
    with pytest.raises(CeilingBreach):
        g.register_usage(_usage(out=51))


def test_guard_tracks_running_totals():
    g = SpendGuard(max_calls=10)
    g.register_attempt()
    g.register_usage(_usage(inp=10, out=5))
    g.register_attempt()
    g.register_usage(_usage(inp=20, out=7, cache_read=3))
    assert g.calls == 2
    assert g.input_tokens == 33  # 10 + (20 + 3)
    assert g.output_tokens == 12


def test_tokens_for_dollar_ceiling_is_a_floor_budget():
    # $500 ceiling at a conservative $75 / 1M tokens prior → 6.66M token budget.
    budget = tokens_for_dollar_ceiling(500, usd_per_million_tokens_prior=75)
    assert budget == (500 * 1_000_000) // 75
    assert isinstance(budget, int) and budget > 0


def test_guard_from_dollar_ceiling_sets_a_token_cap():
    g = SpendGuard.from_dollar_ceiling(0.001, usd_per_million_tokens_prior=75, max_calls=1000)
    # A tiny dollar ceiling → a tiny token budget that trips quickly.
    with pytest.raises(CeilingBreach):
        g.register_usage(_usage(inp=1_000_000))
