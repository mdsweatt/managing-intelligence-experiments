"""Core-math tests for analysis/h1.py — the dollar composite, CoV, and session split."""

import math

from harness.config import ModelPrices
from analysis.h1 import record_cost, component_costs, cov, split_sessions

# Opus-like prices ($/1M tokens)
MP = ModelPrices(input=5.0, output=25.0, cache_read=0.5, cache_write_5m=6.25, thinking=25.0)


def test_record_cost_prices_each_component_once():
    usage = {"input_tokens": 1_000_000, "output_tokens": 1_000_000,
             "cache_read_input_tokens": 1_000_000, "cache_creation_input_tokens": 1_000_000}
    # 5 (input) + 25 (output) + 0.5 (cache_read) + 6.25 (cache_write) = 36.75
    assert math.isclose(record_cost(usage, MP), 36.75)


def test_record_cost_does_NOT_double_count_thinking_or_tool_result():
    """thinking_tokens are inside output_tokens; tool_result_tokens are inside input — the composite
    must price output/input once and ignore these subset fields (schema invariants 4 & 5)."""
    plain = {"input_tokens": 1000, "output_tokens": 2000}
    with_subsets = {**plain, "thinking_tokens": 1500, "tool_result_tokens": 800}
    assert record_cost(with_subsets, MP) == record_cost(plain, MP)


def test_record_cost_standard_has_zero_cache_terms():
    usage = {"input_tokens": 200, "output_tokens": 400}
    assert math.isclose(record_cost(usage, MP), (200 * 5.0 + 400 * 25.0) / 1e6)


def test_component_costs_sum_to_composite():
    usage = {"input_tokens": 300, "output_tokens": 700,
             "cache_read_input_tokens": 5000, "cache_creation_input_tokens": 100}
    comps = component_costs(usage, MP)
    assert math.isclose(sum(comps.values()), record_cost(usage, MP))


def test_cov_basic():
    assert cov([10, 10, 10]) == 0.0
    assert cov([5]) is None
    assert math.isclose(cov([2, 4, 6]), 2.0 / 4.0)   # stdev=2, mean=4


def test_cov_zero_mean_returns_zero():
    assert cov([0, 0, 0]) == 0.0


def test_split_sessions_on_turn_index_reset():
    recs = [{"turn_index": t} for t in (0, 1, 2, 0, 1, 2, 0, 1, 2)]
    sessions = split_sessions(recs)
    assert len(sessions) == 3
    assert all(len(s) == 3 for s in sessions)
    assert [r["turn_index"] for r in sessions[0]] == [0, 1, 2]
