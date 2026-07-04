"""Core-math tests for analysis/h8.py — the Phase-1d H8 neutral-arm ratio (charter §3 H8).

R = (CoV_off − CoV_neutral) / (CoV_off − CoV_on) on the output component, with the pre-registered
verdict bands (< ⅓ supported · ⅓–½ ambiguous · ≥ ½ killed) and the near-floor scoring guard (the
skill's own relative reduction must clear H5_COV_REL = 25%; docs/phase1d-build-notes.md).

Construction trick: a two-value cell [mean−d, mean+d] has CoV = d·√2/mean, and the √2 cancels in
both R and the relative reduction — so band placement is exact by choosing d.
"""

import csv
import json
import math

from harness.config import ModelPrices
from analysis.h5 import arm_cells
from analysis.h8 import COLS, h8_rows, main, verdict, write_csv

MP = ModelPrices(input=5.0, output=25.0, cache_read=0.5, cache_write_5m=6.25, thinking=25.0)
HAIKU = "claude-haiku-4-5-20251001"                       # real id → resolvable in prices yaml


def _rec(task, model, arm, out, inp=100, model_id="claude-opus-4-8"):
    return {"cell_id": {"task_id": task, "band": "S", "model_role": model,
                        "skill_arm": arm, "role_label": "factorial"},
            "model_id": model_id,
            "usage": {"input_tokens": inp, "output_tokens": out}}


class _P:  # minimal Prices stand-in exposing .models[model_id]
    def __init__(self, mp): self.models = {"claude-opus-4-8": mp}


def _cell(task, off_outs, neu_outs, on_outs, model="opus"):
    return ([_rec(task, model, "off", o) for o in off_outs]
            + [_rec(task, model, "neutral", o) for o in neu_outs]
            + [_rec(task, model, "on", o) for o in on_outs])


def _rows(recs):
    return h8_rows(arm_cells(recs, _P(MP)))


def test_r_computed_correctly_on_clean_three_arm_cell():
    # d: off=20, neutral=10, on=0 → R = (20−10)/(20−0) = 0.5; skill reduction = 100% → scored
    (r,) = _rows(_cell(6, [80, 120], [90, 110], [100, 100]))
    assert math.isclose(r["R"], 0.5)
    assert math.isclose(r["skill_rel_reduction"], 1.0)
    assert r["scored"] is True
    assert (r["n_off"], r["n_neutral"], r["n_on"]) == (2, 2, 2)
    assert math.isclose(r["cov_output_off"], 20 * math.sqrt(2) / 100)


def test_verdict_bands():
    # boundary semantics: R < 1/3 supported, 1/3 ≤ R < 1/2 ambiguous, R ≥ 1/2 killed
    assert verdict(0.0) == "supported"
    assert verdict(1 / 3) == "ambiguous"
    assert verdict(1 / 2) == "killed"
    # cell-level cases sit clearly INSIDE each band (an exact-0.5 construction lands on the float
    # knife-edge — boundary semantics are pinned by the exact-fraction asserts above)
    supported = _cell(6, [80, 120], [85, 115], [100, 100])   # R = (20−15)/20 = 0.25
    ambiguous = _cell(7, [80, 120], [88, 112], [100, 100])   # R = (20−12)/20 = 0.40
    killed = _cell(9, [80, 120], [92, 108], [100, 100])      # R = (20−8)/20  = 0.60
    rows = _rows(supported + ambiguous + killed)
    by_task = {r["task_id"]: r for r in rows}
    assert math.isclose(by_task[6]["R"], 0.25) and by_task[6]["verdict"] == "supported"
    assert math.isclose(by_task[7]["R"], 0.40) and by_task[7]["verdict"] == "ambiguous"
    assert math.isclose(by_task[9]["R"], 0.60) and by_task[9]["verdict"] == "killed"


def test_unscored_when_skill_reduction_below_guard():
    # off d=20, on d=16 → reduction 20% < 25% guard; R = (20−10)/(20−16) = 2.5, blown up near the
    # floor — exactly what the guard exists to keep out of the headline
    (r,) = _rows(_cell(6, [80, 120], [90, 110], [84, 116]))
    assert math.isclose(r["skill_rel_reduction"], 0.2)
    assert r["scored"] is False and r["verdict"] is None
    assert math.isclose(r["R"], 2.5)                      # still reported, just not scored


def test_unscored_when_cov_off_equals_cov_on():
    (r,) = _rows(_cell(6, [90, 110], [90, 110], [90, 110]))
    assert r["R"] is None and r["scored"] is False and r["verdict"] is None
    assert math.isclose(r["skill_rel_reduction"], 0.0)


def test_unscored_when_cov_off_is_zero():
    (r,) = _rows(_cell(6, [100, 100], [90, 110], [100, 100]))
    assert r["R"] is None and r["scored"] is False
    assert r["skill_rel_reduction"] is None


def test_two_arm_cell_skipped_entirely():
    recs = ([_rec(9, "opus", "off", o) for o in (80, 120)]
            + [_rec(9, "opus", "on", o) for o in (100, 100)])
    assert _rows(recs) == []


def test_main_writes_csv_with_exact_columns(tmp_path):
    run_dir = tmp_path / "run"; run_dir.mkdir()
    recs = _cell(6, [80, 120], [92, 108], [100, 100], model="haiku")  # R = 0.6 → killed
    for r in recs:
        r["model_id"] = HAIKU
    with (run_dir / "records.jsonl").open("w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r) + "\n")
    out = tmp_path / "out"
    assert main([str(run_dir), "--prices", "prices/prices-2026-06.yaml", "--out", str(out)]) == 0
    with (out / "h8_neutral.csv").open(newline="", encoding="utf-8") as f:
        got = list(csv.reader(f))
    assert got[0] == ["task_id", "band", "model_role", "n_off", "n_neutral", "n_on",
                      "cov_output_off", "cov_output_neutral", "cov_output_on",
                      "skill_rel_reduction", "scored", "R", "verdict"]
    assert len(got) == 2
    row = dict(zip(got[0], got[1]))
    assert row["task_id"] == "6" and row["scored"] == "True" and row["verdict"] == "killed"
    assert math.isclose(float(row["R"]), 0.6)


def test_csv_writer_blank_verdict_for_unscored(tmp_path):
    rows = _rows(_cell(6, [90, 110], [90, 110], [90, 110]))
    path = tmp_path / "h8_neutral.csv"
    write_csv(rows, path)
    with path.open(newline="", encoding="utf-8") as f:
        got = list(csv.reader(f))
    assert got[0] == COLS
    row = dict(zip(got[0], got[1]))
    assert row["verdict"] == "" and row["R"] == "" and row["scored"] == "False"
