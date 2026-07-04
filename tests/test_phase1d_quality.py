"""Tests for the Phase-1d generalization of analysis/quality.py + analysis/h5.py (charter §5, Exp 1d).

1d widens the ladder from 1c's hardcoded {4, 6, 9} to the 8-task set driven entirely by the judge
manifest — pairwise flags, grader dispatch, declared `code_checks` — and surfaces the neutral-system
arm (H8) in the H5 token-side table. Everything here runs on SYNTHETIC rubric dicts + fake texts:
no dependency on the DRAFT 1d manifest (being authored in parallel) and zero API spend. The frozen
1c instrument's behavior is pinned by tests/test_analysis_quality.py, which must keep passing —
the one CLI test below touches only the FROZEN 1c files, never the draft.
"""

from __future__ import annotations

import json
import math

import pytest

from analysis import quality as q
from analysis.h5 import arm_cells, h5_contrasts
from harness.config import ModelPrices


# --------------------------------------------------------------------------- pairwise-task derivation

def test_pairwise_tasks_derived_from_rubrics():
    rubrics = {"4": {"grader": "exact_match", "pairwise": False},
               "24": {"pairwise": True}, "6": {"pairwise": True},
               "9": {"pairwise": True}, "15": {"pairwise": True}}
    assert q.pairwise_tasks(rubrics) == (6, 9, 15, 24)   # sorted ints, exact-match excluded


def test_pairwise_tasks_on_1c_shape_equals_legacy_constant():
    rubrics_1c = {"4": {"grader": "exact_match", "pairwise": False},
                  "6": {"pairwise": True}, "9": {"pairwise": True}}
    assert q.pairwise_tasks(rubrics_1c) == q.GENERATIVE_TASKS


# --------------------------------------------------------------------------- code_checks_from_spec

def test_spec_word_max():
    spec = [{"id": "words", "type": "word_max", "max": 5}]
    ok = q.code_checks_from_spec(spec, "one two three")
    assert ok["words"] == 3 and ok["words_ok"] is True
    over = q.code_checks_from_spec(spec, "w " * 10)
    assert over["words"] == 10 and over["words_ok"] is False


def test_spec_word_range():
    spec = [{"id": "words", "type": "word_range", "min": 3, "max": 5}]
    assert q.code_checks_from_spec(spec, "a b c d")["words_ok"] is True
    assert q.code_checks_from_spec(spec, "a b")["words_ok"] is False        # under min
    assert q.code_checks_from_spec(spec, "a b c d e f")["words_ok"] is False  # over max


def test_spec_sections_all_uses_heading_prefix_convention():
    spec = [{"id": "sections", "type": "sections_all",
             "patterns": {"summary": "summary", "progress": "progress",
                          "next_steps": r"next\s+steps"}}]
    ok = q.code_checks_from_spec(spec, "## Summary\nx\n**Progress**\ny\n- Next Steps\nz")
    assert ok["sections"] == {"summary": True, "progress": True, "next_steps": True}
    assert ok["sections_ok"] is True
    # a mid-line mention is body text, not a heading — the fragment must anchor at line start
    missing = q.code_checks_from_spec(spec, "## Summary\nwe made progress today\nNext steps\n")
    assert missing["sections"]["progress"] is False and missing["sections_ok"] is False


def test_spec_regex_count_min_and_max():
    pat = r"(?im)^\s*(?:#{1,6}\s*)?SUB-[A-Z0-9]+-\d+"
    three = "SUB-PWR-1 x\n## SUB-PWR-2\n  SUB-AV-3 y\n"
    no_max = [{"id": "req_ids", "type": "regex_count", "pattern": pat, "min": 3}]
    ok = q.code_checks_from_spec(no_max, three)
    assert ok["req_ids"] == 3 and ok["req_ids_ok"] is True                  # max absent -> inf
    assert q.code_checks_from_spec(no_max, "SUB-PWR-1\n")["req_ids_ok"] is False   # under min
    capped = [{"id": "req_ids", "type": "regex_count", "pattern": pat, "min": 1, "max": 2}]
    assert q.code_checks_from_spec(capped, three)["req_ids_ok"] is False    # over max


def test_spec_unknown_type_raises():
    with pytest.raises(ValueError, match="unknown code_check type"):
        q.code_checks_from_spec([{"id": "x", "type": "line_count", "max": 3}], "t")


# --------------------------------------------------------------------------- code_checks dispatch

def test_code_checks_spec_none_keeps_legacy_shapes():
    six = q.code_checks(6, "short post #a #b")
    assert set(six) == {"words", "words_ok", "hashtags", "hashtags_ok"}
    nine = q.code_checks(9, "Recommendation\n" + "word " * 800)
    assert set(nine) == {"words", "length_ok", "sections", "sections_ok"}
    with pytest.raises(ValueError, match="no code checks"):
        q.code_checks(24, "text")                                           # unknown + no spec


def test_code_checks_with_spec_routes_to_interpreter_for_any_task():
    out = q.code_checks(24, "a b c", spec=[{"id": "words", "type": "word_max", "max": 130}])
    assert out == {"words": 3, "words_ok": True}


# --------------------------------------------------------------------------- data-driven absolute_pass

RUBRIC_24 = {"pairwise": True,
             "code_checks": [{"id": "words", "type": "word_range", "min": 300, "max": 500}],
             "checks": [{"id": "faithful", "type": "binary", "text": "x", "gate": True},
                        {"id": "depth", "type": "graded", "scores": [0, 1, 2], "text": "x"}]}
CODE_OK = {"words": 400, "words_ok": True}
LLM_OK = {"faithful": {"verdict": "pass"}, "depth": {"verdict": 2}}


def test_absolute_pass_rubric_driven_all_pass():
    assert q.absolute_pass(24, CODE_OK, LLM_OK, RUBRIC_24) is True


def test_absolute_pass_rubric_driven_code_check_fails():
    assert q.absolute_pass(24, {"words": 700, "words_ok": False}, LLM_OK, RUBRIC_24) is False


def test_absolute_pass_rubric_driven_llm_binary_fails():
    llm = {"faithful": {"verdict": "fail"}, "depth": {"verdict": 2}}
    assert q.absolute_pass(24, CODE_OK, llm, RUBRIC_24) is False


def test_absolute_pass_rubric_driven_graded_pass_floor():
    # default pass_floor 1: presence gates (score 1 passes, 0 fails) — the 1c hook convention
    assert q.absolute_pass(24, CODE_OK, {**LLM_OK, "depth": {"verdict": 1}}, RUBRIC_24) is True
    assert q.absolute_pass(24, CODE_OK, {**LLM_OK, "depth": {"verdict": 0}}, RUBRIC_24) is False
    # a declared pass_floor raises the gate
    strict = {**RUBRIC_24, "checks": [RUBRIC_24["checks"][0],
                                      {"id": "depth", "type": "graded", "scores": [0, 1, 2],
                                       "text": "x", "pass_floor": 2}]}
    assert q.absolute_pass(24, CODE_OK, {**LLM_OK, "depth": {"verdict": 1}}, strict) is False


def test_absolute_pass_rubric_driven_none_without_llm():
    assert q.absolute_pass(24, CODE_OK, None, RUBRIC_24) is None


def test_absolute_pass_legacy_6_9_unchanged_without_rubric():
    code6 = {"words_ok": True, "hashtags_ok": True}
    llm6 = {"cta_valid": {"verdict": "pass"}, "hook_quality": {"verdict": 2},
            "faithful": {"verdict": "pass"}}
    assert q.absolute_pass(6, code6, llm6) is True
    assert q.absolute_pass(6, code6, {**llm6, "hook_quality": {"verdict": 0}}) is False
    code9 = {"sections_ok": True, "length_ok": True}
    llm9 = {"recommendation_upfront": {"verdict": "pass"}, "faithful": {"verdict": "pass"}}
    assert q.absolute_pass(9, code9, llm9) is True
    assert q.absolute_pass(9, {**code9, "length_ok": False}, llm9) is False


def test_absolute_pass_rubric_without_code_checks_falls_through_to_legacy():
    # the 1c manifest case: a rubric IS passed (analyse always passes it now) but declares no
    # code_checks -> the hardcoded #6 logic decides, so 1c grading is not reinterpreted
    rubric_1c = {"pairwise": True, "checks": [{"id": "cta_valid", "type": "binary", "text": "x"}]}
    code6 = {"words_ok": True, "hashtags_ok": True}
    llm6 = {"cta_valid": {"verdict": "pass"}, "hook_quality": {"verdict": 0},
            "faithful": {"verdict": "pass"}}
    assert q.absolute_pass(6, code6, llm6, rubric_1c) is False   # legacy hook-presence gate held


# --------------------------------------------------------------------------- grader dispatch in analyse

def test_analyse_dispatches_exact_match_by_manifest_not_task_id():
    # grader: exact_match on a NON-4 id must take the exact-match path (no code_checks call)
    judge = {"rubrics": {"12": {"grader": "exact_match", "gold": "APPROVED", "pairwise": False}}}
    cells = {(12, "haiku", "off"): [{"response_text": "APPROVED"},
                                    {"response_text": "DENIED"}]}
    res = q.analyse(cells, judge, {}, judge_fn=None, k=3, seed="s", run_judge=False)
    row = res["rubric_rows"][0]
    assert row["metric"] == "exact_match" and row["pass_rate"] == pytest.approx(0.5)
    assert res["graded"][(12, "haiku", "off")][0]["exact_match"] is True
    assert res["pairwise_rows"] == []                    # nothing pairwise-flagged in this manifest


def test_analyse_generative_task_uses_manifest_code_checks():
    judge = {"rubrics": {"24": {"pairwise": True,
                                "code_checks": [{"id": "words", "type": "word_max", "max": 5}],
                                "checks": [{"id": "faithful", "type": "binary", "text": "x",
                                            "gate": True}]}}}
    cells = {(24, "haiku", "off"): [{"response_text": "one two three"}]}
    res = q.analyse(cells, judge, {}, judge_fn=None, k=3, seed="s", run_judge=False)
    g = res["graded"][(24, "haiku", "off")][0]
    assert g["code"] == {"words": 3, "words_ok": True}   # spec-driven, no hardcoded branch
    assert g["absolute_pass"] is None and g["eligible"] is None   # LLM judge did not run


def test_analyse_end_to_end_on_a_synthetic_1d_task_with_fake_judge():
    rubric_t = "RUBRIC {{SOURCE_MATERIAL}} {{TASK_INSTRUCTION}} {{CHECKS}} {{RESPONSE}}"
    pair_t = "PAIRWISE {{SOURCE_MATERIAL}} {{TASK_INSTRUCTION}} {{RESPONSE_A}} {{RESPONSE_B}}"
    judge = {"rubrics": {"24": RUBRIC_24}, "margin_pp": 10,
             "prompt_text": {"rubric": rubric_t, "pairwise": pair_t}}
    material = {24: {"source_material": "src", "task_instruction": "task"}}
    fake = lambda p: {"preference": "tie"} if p.startswith("PAIRWISE") \
        else {"faithful": "pass", "depth": 2}
    text = "word " * 400
    cells = {(24, "haiku", "off"): [{"response_text": text}],
             (24, "opus", "off"): [{"response_text": text}]}
    res = q.analyse(cells, judge, material, judge_fn=fake, k=3, seed="s", run_judge=True)
    assert all(r["pass_rate"] == 1.0 for r in res["rubric_rows"])
    pw = next(r for r in res["pairwise_rows"] if r["task_id"] == 24)   # derived, not hardcoded
    assert pw["eligible_pairs"] == 1 and pw["ties"] == 1 and pw["equivalent"] is True


# --------------------------------------------------------------------------- graded-check mean

def _llm(depth, faithful="pass"):
    return {"depth": {"verdict": depth, "agreement": 1.0, "low_confidence": False},
            "faithful": {"verdict": faithful, "agreement": 1.0, "low_confidence": False}}


def test_rubric_row_means_first_graded_check_from_rubric():
    per_output = [{"absolute_pass": True, "llm": _llm(2)},
                  {"absolute_pass": True, "llm": _llm(1)}]
    row = q._rubric_row(24, "haiku", "off", per_output, RUBRIC_24)
    assert row["mean_hook_score"] == pytest.approx(1.5)   # legacy column name, new graded id


def test_rubric_row_no_graded_check_no_mean():
    rubric = {"pairwise": True, "checks": [{"id": "faithful", "type": "binary", "text": "x"}]}
    per_output = [{"absolute_pass": True,
                   "llm": {"faithful": {"verdict": "pass", "agreement": 1.0, "low_confidence": False}}}]
    row = q._rubric_row(24, "haiku", "off", per_output, rubric)
    assert "mean_hook_score" not in row


# --------------------------------------------------------------------------- CLI alias (frozen 1c files)

def test_main_accepts_fixtures_manifest_alias(tmp_path):
    rec = {"cell_id": {"task_id": 6, "task_name": "t", "band": "S", "model_role": "haiku",
                       "model_id": "m", "role_label": "factorial", "skill_arm": "on"},
           "response_text": "Is your team flying blind? word word\nBook a demo.\n#a #b"}
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "records.jsonl").write_text(json.dumps(rec) + "\n", encoding="utf-8")
    out = tmp_path / "out"
    rc = q.main([str(run_dir), "--judge-manifest", "fixtures/judge/manifest.yaml",
                 "--fixtures-manifest", "fixtures/manifest-phase1c.yaml",
                 "--fixtures-root", "fixtures", "--out", str(out)])
    assert rc == 0
    assert (out / "quality_rubric.csv").exists()          # alias maps onto the same dest


# --------------------------------------------------------------------------- h5 neutral-arm columns

MP = ModelPrices(input=5.0, output=25.0, cache_read=0.5, cache_write_5m=6.25, thinking=25.0)


class _P:
    def __init__(self, mp): self.models = {"claude-opus-4-8": mp}


def _hrec(task, model, arm, out, inp=100):
    return {"cell_id": {"task_id": task, "band": "S", "model_role": model, "skill_arm": arm},
            "model_id": "claude-opus-4-8",
            "usage": {"input_tokens": inp, "output_tokens": out}}


def test_h5_rows_carry_neutral_metrics_when_arm_present():
    recs = ([_hrec(6, "haiku", "off", o) for o in (100, 100, 100, 200)]
            + [_hrec(6, "haiku", "on", 50) for _ in range(4)]
            + [_hrec(6, "haiku", "neutral", o) for o in (100, 100, 100, 200)])
    rows = h5_contrasts(arm_cells(recs, _P(MP)))
    r = next(r for r in rows if r["task_id"] == 6)
    assert r["n_neutral"] == 4 and r["mean_neutral"] == 125
    assert math.isclose(r["cov_output_neutral"], 0.4)     # same sample-stdev CoV as the off arm
    assert r["h5_output_win"] is True                     # off/on contrast math untouched


def test_h5_rows_neutral_is_none_without_the_arm():
    recs = ([_hrec(6, "haiku", "off", o) for o in (100, 100, 100, 200)]
            + [_hrec(6, "haiku", "on", 50) for _ in range(4)])
    rows = h5_contrasts(arm_cells(recs, _P(MP)))
    r = next(r for r in rows if r["task_id"] == 6)
    assert r["n_neutral"] is None and r["mean_neutral"] is None
    assert r["cov_output_neutral"] is None                # every 1c cell lands here
    assert math.isclose(r["cov_rel_reduction"], 1.0)      # contrast unchanged by the new columns


# --------------------------------------------------------------------------- findings title phase label

def test_write_findings_title_carries_phase_label(tmp_path):
    judge = {"judge_model": "m", "k": 3, "margin_pp": 10, "status": "FROZEN",
             "judge_hash_computed": "abc123" * 11}
    p = tmp_path / "f.md"
    q._write_findings(p, judge, [], [], run_judge=False, run_dir="results/x",
                      phase_label="Phase-1d")
    assert p.read_text(encoding="utf-8").startswith("# Phase-1d quality findings — results/x")


def test_write_findings_default_label_stays_phase1c(tmp_path):
    judge = {"judge_model": "m", "k": 3, "margin_pp": 10, "status": "FROZEN",
             "judge_hash_computed": "abc123" * 11}
    p = tmp_path / "f.md"
    q._write_findings(p, judge, [], [], run_judge=False, run_dir="results/x")
    assert p.read_text(encoding="utf-8").startswith("# Phase-1c quality findings — results/x")
