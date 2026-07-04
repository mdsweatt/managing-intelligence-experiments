"""Core tests for analysis/correlations.py — axis map, grouping, and the output-share identity."""

import math

from analysis.correlations import (
    TASK_AXIS, DETERMINISTIC, _f, load_rows, group_stats, decomposition,
)


def _row(**kw) -> dict:
    """A loaded-row stub with the fields correlations.py reads (sane defaults)."""
    base = {
        "task_id": 1, "band": "S", "model_role": "opus", "task_name": "t",
        "family": "standard/payload", "axis": "input",
        "cov_input": 0.0, "cov_cache_read": None, "cov_output": 0.1, "cov_composite": 0.05,
    }
    base.update(kw)
    return base


# --------------------------------------------------------------------------- metadata

def test_task_axis_covers_the_run_matrix():
    # all Phase-1a task ids present; high-fan-out 1b ids (13/14/20/21) absent
    assert set(TASK_AXIS) == {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 15, 16, 17, 18, 19, 22}
    assert TASK_AXIS[15] == "thinking"
    assert TASK_AXIS[16] == "turns" and TASK_AXIS[17] == "turns"
    assert TASK_AXIS[10] == "cached-context"
    assert TASK_AXIS[7] == "input" and TASK_AXIS[9] == "output"


def test_deterministic_set_is_the_d3_tasks():
    assert DETERMINISTIC == frozenset({4, 5, 8})


def test_f_parses_blank_as_none():
    assert _f("") is None
    assert _f(None) is None
    assert _f("0.0") == 0.0
    assert math.isclose(_f("0.156"), 0.156)


# --------------------------------------------------------------------------- grouping

def test_group_stats_skips_none_and_computes_median_mean_max():
    rows = [
        _row(model_role="a", cov_composite=0.1),
        _row(model_role="a", cov_composite=0.3),
        _row(model_role="b", cov_composite=0.2),
        _row(model_role="b", cov_composite=None),   # undefined CoV → ignored
    ]
    stats = group_stats(rows, lambda r: r["model_role"])
    assert stats["a"] == {"n": 2, "median": 0.2, "mean": 0.2, "max": 0.3}
    assert stats["b"]["n"] == 1 and stats["b"]["max"] == 0.2


def test_group_stats_by_axis_field_override():
    rows = [_row(axis="thinking", cov_output=0.2), _row(axis="input", cov_output=0.05)]
    stats = group_stats(rows, lambda r: r["axis"], field="cov_output")
    assert stats["thinking"]["median"] == 0.2
    assert stats["input"]["median"] == 0.05


# --------------------------------------------------------------------------- decomposition

def test_decomposition_output_share_is_composite_over_output_cov():
    # output's cost share = CoV_composite / CoV_output (exact because input CoV ≈ 0)
    rows = [_row(cov_output=0.2, cov_composite=0.1)]
    d = decomposition(rows)
    assert len(d) == 1
    assert math.isclose(d[0]["output_cost_share"], 0.5)


def test_decomposition_skips_multiturn_and_guards_zero_output_cov():
    rows = [
        _row(task_id=16, family="multiturn", cov_output=None, cov_composite=0.1),  # skipped
        _row(task_id=4, cov_output=0.0, cov_composite=0.0),                         # share None, no div0
    ]
    d = decomposition(rows)
    assert [r["task_id"] for r in d] == [4]
    assert d[0]["output_cost_share"] is None


def test_decomposition_sorted_by_output_cov_desc():
    rows = [_row(task_id=1, cov_output=0.05), _row(task_id=2, cov_output=0.30),
            _row(task_id=3, cov_output=0.15)]
    d = decomposition(rows)
    assert [r["task_id"] for r in d] == [2, 3, 1]


# --------------------------------------------------------------------------- loading

def test_load_rows_tags_axis_and_coerces_numerics(tmp_path):
    csv_path = tmp_path / "h1_cov.csv"
    csv_path.write_text(
        "task_id,band,model_role,task_name,family,model_id,n,mean_cost_usd,cov_composite,verdict,"
        "cov_input,cov_output,cov_cache_read\n"
        "15,high,sonnet,strategy_brief,standard/payload,m,20,0.15,0.2014,NOT-bandable,0.0,0.204,\n"
        "10,M,haiku,support_vs_kb,cache,m,20,0.002,0.0479,tight,,0.106,0.0\n",
        encoding="utf-8",
    )
    rows = load_rows(csv_path)
    assert rows[0]["axis"] == "thinking" and rows[0]["task_id"] == 15
    assert math.isclose(rows[0]["cov_composite"], 0.2014)
    assert rows[0]["cov_cache_read"] is None        # blank cell → None
    assert rows[1]["axis"] == "cached-context"
    assert rows[1]["cov_input"] is None and rows[1]["cov_cache_read"] == 0.0
