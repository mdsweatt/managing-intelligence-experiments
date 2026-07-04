"""Tests for analysis/quality.py — the Phase-1c quality judge (charter §3 H5/H6).

Pure-function graders are tested directly; every LLM-judged path takes an INJECTED fake judge, so
the whole suite runs with zero API spend (the live judge runs only at analysis time). Mirrors the
style of tests/test_analysis_h1.py (pure math) + tests/test_analysis_correlations.py (CSV via
tmp_path).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from analysis import quality as q

JUDGE_MANIFEST = "fixtures/judge/manifest.yaml"
JUDGE_MANIFEST_1D = "fixtures/judge/manifest-phase1d.yaml"
PHASE1C_MANIFEST = "fixtures/manifest-phase1c.yaml"
FIXTURES_ROOT = "fixtures"
# The frozen 1c judge_hash (fixtures/judge/manifest.yaml). Pinned here so the Phase-1d provider-fold
# in load_judge can be proven NOT to perturb the frozen 1c instrument (byte-identical replay).
JUDGE_HASH_1C = "d12c36a2c8e77a31d712ff6d7913e58f049177a1587412e01fe9800367a4616c"


# --------------------------------------------------------------------------- fakes / builders

class SeqJudge:
    """Returns scripted replies in order (for testing majority + agreement floor)."""

    def __init__(self, replies):
        self.replies = list(replies)

    def __call__(self, prompt):
        return self.replies.pop(0)


def all_pass_judge(prompt: str) -> dict:
    """Constant fake: every binary check passes, hook=2, pairwise=tie. Branches rubric vs pairwise
    on the prompt body. Returns a superset of ids; judge_rubric_item reads only the task's ids."""
    if "RESPONSE A:" in prompt:
        return {"preference": "tie"}
    return {"cta_valid": "pass", "hook_quality": 2, "faithful": "pass",
            "recommendation_upfront": "pass"}


def memo_text(words: int = 800) -> str:
    head = ("Recommendation: pilot a replacement.\n"
            "Background\nfoo\nOptions Considered\nbar\nCost & Budget\nbaz\n"
            "Risks\nqux\nNext Steps\ndone\n")
    body = ("word " * max(0, words - q.word_count(head))).strip()
    return head + body


def copy_text(n_words: int = 30, hashtags: int = 2) -> str:
    tags = " ".join(f"#tag{i}" for i in range(hashtags))
    return ("Is your team flying blind? " + "word " * (n_words - 5)).strip() + f"\nBook a demo.\n{tags}"


def _rec(task_id, model_role, arm, text, *, task_name="t"):
    return {
        "cell_id": {"task_id": task_id, "task_name": task_name, "band": "S",
                    "model_role": model_role, "model_id": "m", "role_label": "factorial",
                    "skill_arm": arm},
        "response_text": text,
    }


def write_jsonl(path: Path, recs) -> None:
    path.write_text("\n".join(json.dumps(r) for r in recs) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- deterministic graders

def test_exact_match_grader():
    assert q.grade_exact_match("P1_Critical", "P1_Critical")
    assert not q.grade_exact_match("P2_High", "P1_Critical")


def test_exact_match_takes_last_nonempty_line():
    # a model that emitted reasoning then the label on its own line still matches on the label
    assert q.grade_exact_match("Let me think...\n\nP1_Critical\n", "P1_Critical")
    # trailing prose after the label does NOT match (a format failure, correctly)
    assert not q.grade_exact_match("P1_Critical because finance is blocked", "P1_Critical")


def test_hashtag_and_word_counts():
    assert q.count_hashtags("a #x #y #z b") == 3
    assert q.word_count("one two three") == 3


def test_code_checks_6():
    ok = q.code_checks(6, copy_text(40, hashtags=2))
    assert ok["words_ok"] and ok["hashtags_ok"]
    too_long = q.code_checks(6, copy_text(80, hashtags=2))
    assert not too_long["words_ok"]
    bad_tags = q.code_checks(6, copy_text(40, hashtags=5))
    assert not bad_tags["hashtags_ok"]


def test_code_checks_9_sections_and_length():
    ok = q.code_checks(9, memo_text(800))
    assert ok["sections_ok"] and ok["length_ok"]
    missing = q.code_checks(9, "Recommendation\nBackground\nRisks\n" + "word " * 800)
    assert not missing["sections_ok"]          # missing Options/Cost/Next Steps
    short = q.code_checks(9, memo_text(300))
    assert not short["length_ok"]


# --------------------------------------------------------------------------- majority / agreement

def test_majority_and_agreement_floor():
    assert q.majority(["pass", "fail", "pass"]) == ("pass", pytest.approx(2 / 3))
    assert not q.is_low_confidence(2 / 3)       # a 2-1 split meets the >=2/3 floor
    assert q.is_low_confidence(1 / 3)           # a 1-1-1 split is below it
    assert not q.is_low_confidence(1.0)


def test_judge_rubric_item_majority_and_low_confidence():
    checks = [{"id": "cta_valid", "type": "binary", "text": "x"},
              {"id": "hook_quality", "type": "graded", "scores": [0, 1, 2], "text": "x"},
              {"id": "faithful", "type": "binary", "text": "x"}]
    # cta: pass,pass,fail -> pass (2/3, confident). hook: 2,1,0 -> no majority (low conf).
    # faithful: pass,pass,pass -> unanimous.
    judge = SeqJudge([
        {"cta_valid": "pass", "hook_quality": 2, "faithful": "pass"},
        {"cta_valid": "pass", "hook_quality": 1, "faithful": "pass"},
        {"cta_valid": "fail", "hook_quality": 0, "faithful": "pass"},
    ])
    out = q.judge_rubric_item(judge, "{{SOURCE_MATERIAL}}{{TASK_INSTRUCTION}}{{CHECKS}}{{RESPONSE}}",
                              source="s", task="t", checks=checks, response="r", k=3)
    assert out["cta_valid"]["verdict"] == "pass" and not out["cta_valid"]["low_confidence"]
    assert out["hook_quality"]["low_confidence"]          # 2/1/0 -> no >=2/3 agreement
    assert out["faithful"]["agreement"] == pytest.approx(1.0)


# --------------------------------------------------------------------------- absolute-rubric pass

def test_absolute_pass_6_requires_hook_present_and_all_binaries():
    code = {"words_ok": True, "hashtags_ok": True}
    good = {"cta_valid": {"verdict": "pass"}, "hook_quality": {"verdict": 2}, "faithful": {"verdict": "pass"}}
    assert q.absolute_pass(6, code, good) is True
    weak_hook = {**good, "hook_quality": {"verdict": 0}}      # hook absent -> fail the gate
    assert q.absolute_pass(6, code, weak_hook) is False
    assert q.absolute_pass(6, {"words_ok": False, "hashtags_ok": True}, good) is False


def test_absolute_pass_returns_none_without_llm():
    assert q.absolute_pass(9, {"sections_ok": True, "length_ok": True}, None) is None


# --------------------------------------------------------------------------- pairwise

def test_haiku_is_a_is_deterministic_and_varies():
    a = [q.haiku_is_a("seed", 6, "on", i) for i in range(20)]
    assert a == [q.haiku_is_a("seed", 6, "on", i) for i in range(20)]   # replays
    assert any(a) and not all(a)                                         # both orders occur


def test_judge_pair_maps_blind_labels_back_to_models():
    # Judge always prefers "A". With a_is_haiku True, A->haiku; with False, A->opus.
    jp_h = q.judge_pair(lambda p: {"preference": "A"}, "{{RESPONSE_A}}{{RESPONSE_B}}{{SOURCE_MATERIAL}}{{TASK_INSTRUCTION}}",
                        source="s", task="t", resp_haiku="H", resp_opus="O", a_is_haiku=True, k=3)
    assert jp_h["winner"] == "haiku"
    jp_o = q.judge_pair(lambda p: {"preference": "A"}, "{{RESPONSE_A}}{{RESPONSE_B}}{{SOURCE_MATERIAL}}{{TASK_INSTRUCTION}}",
                        source="s", task="t", resp_haiku="H", resp_opus="O", a_is_haiku=False, k=3)
    assert jp_o["winner"] == "opus"


def test_pairwise_coverage_excludes_format_failures():
    judge = q.load_judge(JUDGE_MANIFEST, FIXTURES_ROOT)
    material = q.load_task_material(PHASE1C_MANIFEST, FIXTURES_ROOT)
    # 3 matched #6 pairs: pair 0 both pass; pair 1 haiku fails rubric; pair 2 both pass.
    def grade(passes):
        return {"absolute_pass": passes, "_text": "x"}
    graded = {
        (6, "haiku", "on"): [grade(True), grade(False), grade(True)],
        (6, "opus", "on"): [grade(True), grade(True), grade(True)],
    }
    rows = q._pairwise(graded, judge, material, judge_fn=lambda p: {"preference": "tie"},
                       k=3, seed="s", run_judge=True)
    r6 = next(r for r in rows if r["task_id"] == 6 and r["arm"] == "on")
    assert r6["total_pairs"] == 3 and r6["eligible_pairs"] == 2
    assert r6["excluded_share"] == pytest.approx(1 / 3)
    assert r6["ties"] == 2 and r6["wins_haiku"] == 0 and r6["wins_opus"] == 0


def _always_pick(model: str):
    """A judge_fn that always prefers the given model regardless of blind A/B order — it reads which
    side carries the model's tag in the RESPONSE A block (texts are tagged 'HAIKU'/'OPUS')."""
    def fn(prompt: str) -> dict:
        a_block = prompt.split("RESPONSE A:")[1].split("RESPONSE B:")[0]
        a_is_target = model.upper() in a_block.upper()
        return {"preference": "A" if a_is_target else "B"}
    return fn


def test_pairwise_net_pref_and_equivalence_margin():
    judge = q.load_judge(JUDGE_MANIFEST, FIXTURES_ROOT)
    material = q.load_task_material(PHASE1C_MANIFEST, FIXTURES_ROOT)
    # 10 eligible pairs; judge always prefers opus -> net_pref 100% -> NOT equivalent (>10pp).
    graded = {(9, "haiku", "off"): [{"absolute_pass": True, "_text": "HAIKU"} for _ in range(10)],
              (9, "opus", "off"): [{"absolute_pass": True, "_text": "OPUS"} for _ in range(10)]}
    rows = q._pairwise(graded, judge, material, judge_fn=_always_pick("opus"),
                       k=3, seed="s", run_judge=True)
    r = next(r for r in rows if r["task_id"] == 9 and r["arm"] == "off")
    assert r["wins_opus"] == 10 and r["wins_haiku"] == 0
    assert r["net_pref"] == pytest.approx(1.0) and r["equivalent"] is False


def test_pairwise_equivalent_when_within_margin():
    judge = q.load_judge(JUDGE_MANIFEST, FIXTURES_ROOT)
    material = q.load_task_material(PHASE1C_MANIFEST, FIXTURES_ROOT)
    # All ties -> net_pref 0 -> equivalent (<=10pp).
    graded = {(6, "haiku", "on"): [{"absolute_pass": True, "_text": "HAIKU"} for _ in range(10)],
              (6, "opus", "on"): [{"absolute_pass": True, "_text": "OPUS"} for _ in range(10)]}
    rows = q._pairwise(graded, judge, material, judge_fn=lambda p: {"preference": "tie"},
                       k=3, seed="s", run_judge=True)
    r = next(r for r in rows if r["task_id"] == 6 and r["arm"] == "on")
    assert r["ties"] == 10 and r["net_pref"] == pytest.approx(0.0) and r["equivalent"] is True


# --------------------------------------------------------------------------- format-neutral gate (1d)

# 1d rubrics mark exactly the substance check that gates pairwise eligibility with `gate: true`;
# everything else (CTA, hook, and the code-graded word/hashtag/section counts) is scored + reported
# but never gates — so a faithful-but-format-noncompliant loose output is eligible (charter §5.147).
RUBRICS_1D = {"6": {"pairwise": True, "checks": [
    {"id": "cta_valid", "type": "binary", "text": "x"},
    {"id": "hook_quality", "type": "graded", "scores": [0, 1, 2], "text": "x"},
    {"id": "faithful", "type": "binary", "text": "x", "gate": True}]}}
RUBRICS_1C = {"6": {"pairwise": True, "checks": [
    {"id": "cta_valid", "type": "binary", "text": "x"},
    {"id": "hook_quality", "type": "graded", "scores": [0, 1, 2], "text": "x"},
    {"id": "faithful", "type": "binary", "text": "x"}]}}  # no gate flag -> legacy behaviour


def test_eligibility_faithfulness_only_gate():
    faithful = {"faithful": {"verdict": "pass"}, "cta_valid": {"verdict": "fail"},
                "hook_quality": {"verdict": 0}}
    # format + CTA + hook all fail, but faithful passes -> eligible (format is not a gate in 1d)
    assert q.eligibility(6, {"words_ok": False, "hashtags_ok": False}, faithful, RUBRICS_1D) is True
    unfaithful = {"faithful": {"verdict": "fail"}, "cta_valid": {"verdict": "pass"},
                  "hook_quality": {"verdict": 2}}
    # everything else perfect, but unfaithful -> excluded (hallucination has no place in a quality pair)
    assert q.eligibility(6, {"words_ok": True, "hashtags_ok": True}, unfaithful, RUBRICS_1D) is False


def test_eligibility_is_none_without_llm():
    assert q.eligibility(6, {"words_ok": True, "hashtags_ok": True}, None, RUBRICS_1D) is None


def test_eligibility_without_gate_falls_back_to_absolute_pass():
    # A rubric with no gate flag (1c) keeps the legacy format-inclusive gate — 1c is not reinterpreted.
    good = {"cta_valid": {"verdict": "pass"}, "hook_quality": {"verdict": 2},
            "faithful": {"verdict": "pass"}}
    assert q.eligibility(6, {"words_ok": True, "hashtags_ok": True}, good, RUBRICS_1C) is True
    assert q.eligibility(6, {"words_ok": False, "hashtags_ok": True}, good, RUBRICS_1C) is False


def test_pairwise_gates_on_eligible_admitting_format_noncompliant_faithful_pairs():
    judge = q.load_judge(JUDGE_MANIFEST, FIXTURES_ROOT)
    material = q.load_task_material(PHASE1C_MANIFEST, FIXTURES_ROOT)
    # pair 0: eligible True for both though absolute_pass False (format-noncompliant); pair 1: both
    # eligible AND absolute_pass. The OLD absolute_pass gate would admit only pair 1 (=1); the NEW
    # eligible gate admits both (=2) — this is the 1c coverage hole closing.
    graded = {
        (6, "haiku", "off"): [{"eligible": True, "absolute_pass": False, "_text": "H"},
                              {"eligible": True, "absolute_pass": True, "_text": "H"}],
        (6, "opus", "off"): [{"eligible": True, "absolute_pass": False, "_text": "O"},
                             {"eligible": True, "absolute_pass": True, "_text": "O"}],
    }
    rows = q._pairwise(graded, judge, material, judge_fn=lambda p: {"preference": "tie"},
                       k=3, seed="s", run_judge=True)
    r = next(r for r in rows if r["task_id"] == 6 and r["arm"] == "off")
    assert r["total_pairs"] == 2 and r["eligible_pairs"] == 2


def test_pairwise_handles_neutral_arm():
    judge = q.load_judge(JUDGE_MANIFEST, FIXTURES_ROOT)
    material = q.load_task_material(PHASE1C_MANIFEST, FIXTURES_ROOT)
    graded = {(6, "haiku", "neutral"): [{"eligible": True, "_text": "H"} for _ in range(3)],
              (6, "opus", "neutral"): [{"eligible": True, "_text": "O"} for _ in range(3)]}
    rows = q._pairwise(graded, judge, material, judge_fn=lambda p: {"preference": "tie"},
                       k=3, seed="s", run_judge=True)
    r = next(r for r in rows if r["task_id"] == 6 and r["arm"] == "neutral")
    assert r["eligible_pairs"] == 3 and r["ties"] == 3


def test_1d_manifest_declares_faithfulness_gate():
    judge = q.load_judge(JUDGE_MANIFEST_1D, FIXTURES_ROOT)
    for tid in ("6", "9"):
        gates = [c["id"] for c in judge["rubrics"][tid]["checks"] if c.get("gate")]
        assert gates == ["faithful"], tid


def test_1c_manifest_has_no_gate_flags():
    judge = q.load_judge(JUDGE_MANIFEST, FIXTURES_ROOT)
    for tid in ("6", "9"):
        assert not any(c.get("gate") for c in judge["rubrics"][tid]["checks"]), tid


# --------------------------------------------------------------------------- judge config / hash

def test_load_judge_verifies_prompt_hashes_and_computes_judge_hash():
    judge = q.load_judge(JUDGE_MANIFEST, FIXTURES_ROOT)
    assert judge["judge_model"] == "claude-opus-4-8" and judge["k"] == 3 and judge["margin_pp"] == 10
    from harness.hashing import is_sha256_hex
    assert is_sha256_hex(judge["judge_hash_computed"])
    assert "{{SOURCE_MATERIAL}}" in judge["prompt_text"]["rubric"]


def test_load_judge_raises_on_frozen_hash_mismatch(tmp_path):
    import yaml
    m = yaml.safe_load(Path(JUDGE_MANIFEST).read_text())
    m["status"] = "FROZEN"
    m["judge_hash"] = "0" * 64           # wrong
    p = tmp_path / "manifest.yaml"
    p.write_text(yaml.safe_dump(m))
    # prompt files are referenced relative to fixtures_root, which still points at the real tree
    with pytest.raises(ValueError, match="judge_hash mismatch"):
        q.load_judge(p, FIXTURES_ROOT)


def test_load_judge_1c_hash_is_unchanged_by_the_provider_fold():
    # The Phase-1d provider/judge_config fold in load_judge must be back-compat: a 1c manifest carries
    # neither key, so its recomputed judge_hash must still equal the pinned frozen value byte-for-byte.
    judge = q.load_judge(JUDGE_MANIFEST, FIXTURES_ROOT)
    assert judge["judge_hash_computed"] == JUDGE_HASH_1C
    assert judge.get("provider") is None   # 1c has no provider -> anthropic path in main()


def test_load_judge_1d_frozen_loads_and_folds_provider_into_hash():
    # FROZEN 2026-07-02 (was DRAFT during the build): the recorded judge_hash is now ASSERTED on
    # every load — this test riding the real manifest is itself the replay check.
    judge = q.load_judge(JUDGE_MANIFEST_1D, FIXTURES_ROOT)
    assert judge["status"] == "FROZEN"
    assert judge["provider"] == "gemini"
    assert judge["judge_config"]["thinking_budget"] == 256
    assert judge["k"] == 3 and judge["margin_pp"] == 10   # kill-condition unchanged from 1c
    from harness.hashing import is_sha256_hex
    assert is_sha256_hex(judge["judge_hash_computed"])
    # provider + judge_config are folded in, so the 1d instrument is a DIFFERENT hash than 1c.
    assert judge["judge_hash_computed"] != JUDGE_HASH_1C
    # FROZEN => the pinned judge_hash equals the recompute (load_judge would have raised otherwise).
    assert judge["judge_hash_computed"] == judge["judge_hash"]


def test_load_task_material_reads_real_fixtures():
    mat = q.load_task_material(PHASE1C_MANIFEST, FIXTURES_ROOT)
    assert set(mat) == {6, 9}
    assert "Cadence" in mat[6]["source_material"]
    assert "Northwind" in mat[9]["source_material"]


# --------------------------------------------------------------------------- spot-check

def test_spotcheck_is_stratified_and_deterministic(tmp_path):
    recs = ([_rec(6, "haiku", "on", copy_text()) for _ in range(20)]
            + [_rec(9, "opus", "off", memo_text()) for _ in range(20)]
            + [_rec(4, "haiku", "on", "P1_Critical") for _ in range(20)])
    p = tmp_path / "records.jsonl"
    write_jsonl(p, recs)
    cells = q.load_factorial(p)
    s1 = q.spotcheck_sample(cells, frac=0.10, seed="x")
    s2 = q.spotcheck_sample(cells, frac=0.10, seed="x")
    assert [r["spot_id"] for r in s1] == [r["spot_id"] for r in s2]      # replays
    # ≥10% per generative stratum (2 of 20), and NO #4 rows (deterministic task excluded)
    strata = {(r["task_id"], r["model_role"], r["arm"]) for r in s1}
    assert strata == {(6, "haiku", "on"), (9, "opus", "off")}
    assert all(r["task_id"] in (6, 9) for r in s1)
    assert sum(1 for r in s1 if r["task_id"] == 6) == 2


# --------------------------------------------------------------------------- end-to-end (fake judge)

def test_analyse_end_to_end_with_fake_judge(tmp_path):
    judge = q.load_judge(JUDGE_MANIFEST, FIXTURES_ROOT)
    material = q.load_task_material(PHASE1C_MANIFEST, FIXTURES_ROOT)
    recs = []
    for arm in ("off", "on"):
        for role in ("haiku", "opus"):
            recs += [_rec(6, role, arm, copy_text()) for _ in range(3)]
            recs += [_rec(9, role, arm, memo_text()) for _ in range(3)]
            recs += [_rec(4, role, arm, "P1_Critical") for _ in range(3)]
    p = tmp_path / "records.jsonl"
    write_jsonl(p, recs)
    cells = q.load_factorial(p)
    res = q.analyse(cells, judge, material, judge_fn=all_pass_judge, k=3, seed="s", run_judge=True)

    # #4 exact-match pass-rate is 100%
    r4 = [r for r in res["rubric_rows"] if r["task_id"] == 4]
    assert r4 and all(r["pass_rate"] == 1.0 and r["metric"] == "exact_match" for r in r4)
    # #6/#9 absolute pass-rate is 100% under the all-pass judge
    gen = [r for r in res["rubric_rows"] if r["task_id"] in (6, 9)]
    assert gen and all(r["pass_rate"] == 1.0 for r in gen)
    # pairwise ran on all 3 matched pairs per (task, arm); all ties
    pw = [r for r in res["pairwise_rows"] if r["task_id"] in (6, 9)]
    assert pw and all(r["eligible_pairs"] == 3 and r["ties"] == 3 for r in pw)
    assert all(r["excluded_share"] == 0.0 for r in pw)


def test_main_without_run_judge_is_free_and_writes_outputs(tmp_path):
    recs = [_rec(6, "haiku", "on", copy_text()) for _ in range(5)]
    recs += [_rec(4, "opus", "off", "P1_Critical") for _ in range(5)]
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    write_jsonl(run_dir / "records.jsonl", recs)
    out = tmp_path / "out"
    rc = q.main([str(run_dir), "--judge-manifest", JUDGE_MANIFEST,
                 "--phase1c-manifest", PHASE1C_MANIFEST, "--fixtures-root", FIXTURES_ROOT,
                 "--out", str(out)])
    assert rc == 0
    for name in ("quality_rubric.csv", "quality_pairwise.csv", "quality_spotcheck.csv",
                 "quality_spotcheck_key.csv", "quality-findings.md"):
        assert (out / name).exists(), name
    # #4 exact-match still graded without any LLM call
    rubric = (out / "quality_rubric.csv").read_text()
    assert "exact_match" in rubric


def test_compute_agreement(tmp_path):
    labeled = tmp_path / "labeled.csv"
    key = tmp_path / "key.csv"
    labeled.write_text("spot_id,task_id,response_text,human_pass\na,6,x,pass\nb,6,y,fail\nc,6,z,pass\n")
    key.write_text("spot_id,task_id,model_role,arm,idx,llm_pass\na,6,h,on,0,pass\nb,6,h,on,1,pass\nc,6,h,on,2,pass\n")
    res = q.compute_agreement(labeled, key)
    assert res["n"] == 3 and res["agreement"] == pytest.approx(2 / 3)
