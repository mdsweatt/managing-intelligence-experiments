"""Core-math tests for analysis/h7.py — the Phase-1d H7 cap/mandate sign test (charter §3 H7).

H7 asks whether the FROZEN cap/mandate label predicts the sign of Δ(mean output tokens) between
skill-off and skill-on. These tests exercise the sign / hit / exclusion logic on synthetic
factorial records, passing labels as a plain mapping (main() owns the runs/phase1d.yaml loading —
the file does not exist until the freeze).
"""

import csv
import math

from harness.config import ModelPrices
from analysis.h5 import arm_cells
from analysis.h7 import COLS, h7_rows, label_counts, write_csv

# Opus-like prices ($/1M tokens) — mirrors tests/test_analysis_h5.py
MP = ModelPrices(input=5.0, output=25.0, cache_read=0.5, cache_write_5m=6.25, thinking=25.0)


def _rec(task, model, arm, out, inp=100):
    return {"cell_id": {"task_id": task, "band": "S", "model_role": model,
                        "skill_arm": arm, "role_label": "factorial"},
            "model_id": "claude-opus-4-8",
            "usage": {"input_tokens": inp, "output_tokens": out}}


class _P:  # minimal Prices stand-in exposing .models[model_id]
    def __init__(self, mp): self.models = {"claude-opus-4-8": mp}


def _rows(recs, labels):
    return h7_rows(arm_cells(recs, _P(MP)), labels)


def _pair(task, model, off_outs, on_outs):
    return ([_rec(task, model, "off", o) for o in off_outs]
            + [_rec(task, model, "on", o) for o in on_outs])


def test_mandate_with_mean_up_is_hit():
    rows = _rows(_pair(9, "opus", [100, 120], [200, 220]), {9: "mandate"})
    (r,) = rows
    assert (r["predicted_sign"], r["observed_sign"]) == ("+", "+")
    assert r["hit"] is True and r["excluded"] is False
    assert math.isclose(r["mean_delta_pct"], (210 - 110) / 110 * 100)


def test_cap_with_mean_up_is_miss():
    (r,) = _rows(_pair(6, "opus", [100, 120], [200, 220]), {6: "cap"})
    assert (r["predicted_sign"], r["observed_sign"]) == ("-", "+")
    assert r["hit"] is False


def test_cap_with_mean_down_is_hit():
    (r,) = _rows(_pair(6, "opus", [200, 220], [100, 120]), {6: "cap"})
    assert (r["predicted_sign"], r["observed_sign"]) == ("-", "-")
    assert r["hit"] is True


def test_exact_tie_is_observed_zero_and_a_miss():
    # off mean 110 == on mean 110 exactly → "0", which matches neither sign → miss
    (r,) = _rows(_pair(9, "opus", [100, 120], [110, 110]), {9: "mandate"})
    assert r["observed_sign"] == "0"
    assert r["hit"] is False


def test_unlabeled_cell_present_in_rows_but_excluded_from_counts():
    recs = _pair(4, "opus", [100, 120], [200, 220]) + _pair(9, "opus", [100, 120], [200, 220])
    rows = _rows(recs, {4: None, 9: "mandate"})           # #4-style placebo: no label
    r4 = next(r for r in rows if r["task_id"] == 4)
    assert r4["excluded"] is True and r4["hit"] is None and r4["predicted_sign"] is None
    counts = label_counts(rows)
    assert counts["overall"] == (1, 1)                    # only #9 counts toward the headline
    assert counts["mandate"] == (1, 1)


def test_task_missing_from_mapping_is_also_excluded():
    (r,) = _rows(_pair(7, "opus", [100, 120], [50, 70]), {})
    assert r["excluded"] is True and r["hit"] is None


def test_neutral_arm_ignored_and_incomplete_pairs_skipped():
    # a 3-arm cell yields exactly one off/on row; an off+neutral cell (no on) yields none
    recs = (_pair(6, "opus", [200, 220], [100, 120])
            + [_rec(6, "opus", "neutral", o) for o in (150, 170)]
            + [_rec(9, "opus", "off", o) for o in (100, 120)]
            + [_rec(9, "opus", "neutral", o) for o in (100, 120)])
    rows = _rows(recs, {6: "cap", 9: "mandate"})
    assert [r["task_id"] for r in rows] == [6]
    assert (rows[0]["n_off"], rows[0]["n_on"]) == (2, 2)


def test_label_counts_per_group():
    recs = (_pair(6, "opus", [200, 220], [100, 120])      # cap, mean down → hit
            + _pair(7, "opus", [100, 120], [200, 220])    # cap, mean up → miss
            + _pair(9, "opus", [100, 120], [200, 220])    # mandate, mean up → hit
            + _pair(4, "opus", [100, 120], [100, 120]))   # unlabeled → excluded
    counts = label_counts(_rows(recs, {6: "cap", 7: "cap", 9: "mandate", 4: None}))
    assert counts["cap"] == (1, 2)
    assert counts["mandate"] == (1, 1)
    assert counts["overall"] == (2, 3)


def test_csv_has_exact_columns_and_excluded_row(tmp_path):
    rows = _rows(_pair(4, "opus", [100, 120], [200, 220]), {4: None})
    path = tmp_path / "h7_sign.csv"
    write_csv(rows, path)
    with path.open(newline="", encoding="utf-8") as f:
        got = list(csv.reader(f))
    assert got[0] == COLS
    assert len(got) == 2                                  # excluded rows still appear in the CSV
    assert got[1][COLS.index("excluded")] == "True"
