"""Core-math tests for analysis/h5.py — the Phase-1c H5 determinism contrast (charter §3 H5).

H5's token side: per (task, band, model, skill_arm) CoV_output + mean output tokens, then the
skill-on vs skill-off contrast. Reuses analysis/h1.py's canonical cost model + sample-stdev CoV;
the ONLY new behavior is arm-awareness (h1.py merges arms) and the on/off contrast verdict.
"""

import math

from harness.config import ModelPrices
from analysis.h5 import arm_key, cell_metrics, arm_cells, h5_contrasts

# Opus-like prices ($/1M tokens) — mirrors tests/test_analysis_h1.py
MP = ModelPrices(input=5.0, output=25.0, cache_read=0.5, cache_write_5m=6.25, thinking=25.0)


def _rec(task, model, arm, out, inp=100):
    return {"cell_id": {"task_id": task, "band": "S", "model_role": model, "skill_arm": arm},
            "model_id": "claude-opus-4-8",
            "usage": {"input_tokens": inp, "output_tokens": out}}


def test_arm_key_separates_skill_arms():
    off = _rec(6, "haiku", "off", 100)
    on = _rec(6, "haiku", "on", 100)
    assert arm_key(off) != arm_key(on)
    assert arm_key(off) == (6, "S", "haiku", "off")


def test_arm_cells_does_not_merge_arms():
    """The whole point: same (task,band,model), different arm → two cells, never one bimodal cell."""
    recs = [_rec(6, "haiku", "off", 100), _rec(6, "haiku", "off", 100),
            _rec(6, "haiku", "on", 200), _rec(6, "haiku", "on", 200)]
    cells = arm_cells(recs, _prices())
    assert set(cells) == {(6, "S", "haiku", "off"), (6, "S", "haiku", "on")}
    assert cells[(6, "S", "haiku", "off")]["mean_output_tokens"] == 100
    assert cells[(6, "S", "haiku", "on")]["mean_output_tokens"] == 200


def test_cell_metrics_cov_output_is_sample_stdev_over_mean():
    # outputs [100,100,100,200]: mean 125, sample stdev 50 → CoV 0.4 (price cancels in CoV)
    recs = [_rec(6, "opus", "off", o) for o in (100, 100, 100, 200)]
    m = cell_metrics(recs, MP)
    assert m["mean_output_tokens"] == 125
    assert math.isclose(m["cov_output"], 0.4)


def test_h5_contrast_win_when_cov_down_and_mean_not_raised():
    off = [_rec(6, "opus", "off", o) for o in (100, 100, 100, 200)]  # cov 0.4, mean 125
    on = [_rec(6, "opus", "on", 50) for _ in range(4)]               # cov 0,   mean 50
    rows = h5_contrasts(arm_cells(off + on, _prices()))
    row = next(r for r in rows if r["task_id"] == 6 and r["model_role"] == "opus")
    assert math.isclose(row["cov_rel_reduction"], 1.0)
    assert math.isclose(row["mean_delta_pct"], -60.0)
    assert row["h5_output_win"] is True


def test_h5_contrast_no_win_when_mean_raised():
    """Long-form pattern: variance falls but mean output RISES → not an H5 win (judge-spec §4)."""
    off = [_rec(9, "opus", "off", o) for o in (900, 1000, 1100, 1000)]   # mean 1000
    on = [_rec(9, "opus", "on", o) for o in (1480, 1500, 1520, 1500)]    # mean 1500, tiny cov
    rows = h5_contrasts(arm_cells(off + on, _prices()))
    row = next(r for r in rows if r["task_id"] == 9)
    assert row["cov_rel_reduction"] > 0.25      # variance did fall
    assert row["mean_delta_pct"] > 0            # but mean rose
    assert row["h5_output_win"] is False


# --- a tiny prices stand-in exposing .models[model_id] like harness.config Prices ---
class _P:
    def __init__(self, mp): self.models = {"claude-opus-4-8": mp}


def _prices():
    return _P(MP)
