"""Tests for the Experiment-1c skill axis + output capture (charter §3 H5/H6).

The load-bearing guarantee here is **back-compatibility**: adding the `skill` field to
`CallConfig` and `skill_hash`/`response_text`/`skill_arm` to the records must NOT perturb any
Phase-1a identity. A skill-off config hashes byte-identically to the pre-skill schema and every
existing Phase-1a record still recomputes-and-verifies its config_hash on load. The new axis
only moves identity on the skill-on arm.
"""

from __future__ import annotations

import copy
import glob
from pathlib import Path

import pytest
from pydantic import ValidationError

from harness.assemble import SkillHashMismatch, SkillNotFrozen, assemble
from harness.config import (
    config_hash,
    load_manifest,
    load_run_matrix,
    load_skill_manifest,
    skill_hash,
)
from harness.expand import expand_matrix
from harness.schema import CallConfig, CallRole, CaptureRecord, CellId, ExecPath

FIXTURES_ROOT = "fixtures"
SKILL_MANIFEST = "fixtures/skills/manifest.yaml"
PHASE1C_MANIFEST = "fixtures/manifest-phase1c.yaml"


def _read_file(rel: str) -> str:
    return (Path(FIXTURES_ROOT) / rel).read_text(encoding="utf-8")


# --------------------------------------------------------------------------- back-compat


def test_phase1a_matrix_still_loads():
    """The TaskSpec design-validator (hypothesis XOR factorial_models) must not reject the
    existing Phase-1a ladder matrix."""
    rm = load_run_matrix("runs/phase1a.yaml")
    assert all(t.hypothesis is not None and t.factorial_models is None for t in rm.tasks)


def test_config_hash_recompute_still_matches_across_all_runs():
    """The precise back-compat guarantee for the skill change: every stored record's config_hash
    must still recompute to the same value now that CallConfig carries a `skill` field — for
    Phase-1a/1b cost-only records (skill is None → project to the pre-skill world) AND Phase-1c
    factorial records (a skill-on arm legitimately carries a skill and perturbs the hash). We check
    the hash directly (not full record validation) so this is unaffected by unrelated pre-existing
    record issues (e.g. the older Phase-0 cost-gate run predates the thinking-capture hardening)."""
    import json

    paths = sorted(glob.glob("results/*/records.jsonl"))
    if not paths:
        pytest.skip("no results/*/records.jsonl present")
    checked = 0
    for p in paths:
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                cfg = CallConfig(**d["config"])
                if d["cell_id"].get("role_label") != "factorial":
                    assert cfg.skill is None  # pre-skill / cost-only records project to skill-off
                recomputed = config_hash(cfg, tokenizer_version=d["tokenizer_version"])
                assert recomputed == d["config_hash"], f"config_hash drift in {p}"
                checked += 1
    assert checked > 0


def test_headline_phase1a_run_records_fully_load():
    """The clean H1 headline run (zero quarantined per the report) must still fully validate
    end-to-end under the new schema."""
    path = "results/run-20260624T112122Z-cfa60e/records.jsonl"
    if not Path(path).exists():
        pytest.skip(f"{path} not present")
    import json

    checked = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = CaptureRecord.from_jsonl_line(line)  # raises on any hash/consistency drift
            assert rec.config.skill is None and rec.skill_hash is None
            assert rec.cell_id.skill_arm == "off" and rec.response_text is None
            checked += 1
    assert checked > 2000  # the report cites 2,069 records


def test_config_hash_skill_none_is_byte_identical_to_preskill():
    """A skill=None config must hash exactly as the pre-skill schema did: the `skill` (and, since
    Exp 1d, `neutral`) keys are dropped before hashing, so the canonical payload is unchanged."""
    cfg = CallConfig(model_role="sonnet", model_id="claude-sonnet-4-6", band="S",
                     effort="high", thinking="off", max_tokens=128000)
    assert cfg.skill is None and cfg.neutral is None
    pre_skill_payload = cfg.model_dump()
    pre_skill_payload.pop("skill")              # the shape before the field existed
    pre_skill_payload.pop("neutral")            # ...and before the Exp 1d neutral field existed
    pre_skill_payload["tokenizer_version"] = "tok-hs"
    from harness.hashing import canonical_json, sha256_hex
    expected = sha256_hex(canonical_json(pre_skill_payload))
    assert config_hash(cfg, tokenizer_version="tok-hs") == expected


def test_config_hash_skill_on_is_distinct():
    base = dict(model_role="sonnet", model_id="claude-sonnet-4-6", band="S",
                effort="high", thinking="off", max_tokens=128000)
    off = config_hash(CallConfig(**base), tokenizer_version="tok-hs")
    on = config_hash(CallConfig(**base, skill="short-form-copy-scaffold-v1"), tokenizer_version="tok-hs")
    assert off != on


# --------------------------------------------------------------------------- cell key


def test_cell_key_skill_off_unchanged_on_suffixed():
    common = dict(task_id=6, task_name="short_form_copy", band="S",
                  model_role="haiku", model_id="claude-haiku-4-5-20251001", role_label="factorial")
    off = CellId(**common, skill_arm="off")
    on = CellId(**common, skill_arm="on")
    assert off.key() == "t6:S:haiku:factorial"          # pre-skill shape preserved
    assert on.key() == "t6:S:haiku:factorial:skill-on"  # distinct, never collides with off
    assert off.key() != on.key()


# --------------------------------------------------------------------------- design validator


def test_taskspec_requires_exactly_one_design():
    from harness.config import TaskSpec
    # both set -> reject
    with pytest.raises(ValidationError, match="EITHER"):
        TaskSpec(id=99, name="x", cost_axis="output", bands=["S"],
                 hypothesis="haiku", factorial_models=["haiku"], skill="s")
    # neither set -> reject
    with pytest.raises(ValidationError, match="EITHER"):
        TaskSpec(id=99, name="x", cost_axis="output", bands=["S"])
    # factorial without skill -> reject
    with pytest.raises(ValidationError, match="must declare a `skill`"):
        TaskSpec(id=99, name="x", cost_axis="output", bands=["S"], factorial_models=["haiku"])
    # valid ladder + valid factorial both pass
    TaskSpec(id=99, name="x", cost_axis="output", bands=["S"], hypothesis="haiku")
    TaskSpec(id=99, name="x", cost_axis="output", bands=["S"],
             factorial_models=["haiku", "opus"], skill="s")


# --------------------------------------------------------------------------- factorial expansion


def test_phase1c_expands_2x3_factorial():
    rm = load_run_matrix("runs/phase1c.yaml")
    manifest = load_manifest(PHASE1C_MANIFEST)
    skills = load_skill_manifest(SKILL_MANIFEST)
    units = expand_matrix(rm, manifest, skills)

    # 3 tasks × 1 band × 3 models × 2 skill arms = 18 cells.
    assert len(units) == 18
    assert {u.role_label for u in units} == {"factorial"}

    t6 = [u for u in units if u.cell_id.task_id == 6]
    assert len(t6) == 6
    assert {u.cell_id.model_role for u in t6} == {"haiku", "sonnet", "opus"}
    assert {u.cell_id.skill_arm for u in t6} == {"off", "on"}
    # skill id + skill_entry are present iff the arm is on; absent iff off
    for u in t6:
        on = u.cell_id.skill_arm == "on"
        assert (u.config.skill is not None) == on
        assert (u.skill_entry is not None) == on
        assert u.family == "standard"
    # Haiku arm carries no effort knob; Sonnet/Opus arms run effort=high, thinking off.
    haiku = next(u for u in t6 if u.cell_id.model_role == "haiku")
    opus = next(u for u in t6 if u.cell_id.model_role == "opus")
    assert haiku.config.effort is None
    assert (opus.config.effort, opus.config.thinking) == ("high", "off")


def test_phase1c_skill_off_and_on_keys_are_distinct_cells():
    rm = load_run_matrix("runs/phase1c.yaml")
    manifest = load_manifest(PHASE1C_MANIFEST)
    skills = load_skill_manifest(SKILL_MANIFEST)
    keys = [u.cell_id.key() for u in expand_matrix(rm, manifest, skills)]
    assert len(keys) == len(set(keys))  # no two cells collide (skill arm is in the key)


# --------------------------------------------------------------------------- assemble


def test_assemble_injects_skill_as_system_block():
    rm = load_run_matrix("runs/phase1c.yaml")
    manifest = load_manifest(PHASE1C_MANIFEST)
    skills = load_skill_manifest(SKILL_MANIFEST)
    units = expand_matrix(rm, manifest, skills)

    on_unit = next(u for u in units if u.cell_id.task_id == 6 and u.cell_id.skill_arm == "on")
    off_unit = next(u for u in units if u.cell_id.task_id == 6 and u.cell_id.skill_arm == "off")

    # artifacts are FROZEN: run through the real frozen gate — this also verifies the manifest
    # sha256 matches the on-disk bytes (else assemble would raise Skill/FixtureHashMismatch).
    on_plan = assemble(on_unit, _read_file, require_frozen=True)
    off_plan = assemble(off_unit, _read_file, require_frozen=True)

    skill_text = _read_file(on_unit.skill_entry.file)
    assert on_plan.system == [{"type": "text", "text": skill_text}]
    assert on_plan.skill_hash == skill_hash(skill_text)
    # the user message carries the CALIBRATED-LOOSE baseline prompt (the constraints live in the
    # skill, not the prompt) — this is what makes H5 a scaffolding test, not a verbosity test.
    user_msg = on_plan.messages[0]["content"]
    assert on_plan.messages[0]["role"] == "user"
    assert "Output only the post" in user_msg          # the loose baseline
    assert "maximum 60 words" not in user_msg           # the constraint lives in the skill, not here
    assert "≤ 60 words" in skill_text                    # ...and the skill carries it

    assert off_plan.system is None
    assert off_plan.skill_hash is None


def test_phase1c_artifacts_are_frozen():
    """Guard the freeze: every 1c skill and fixture must stay frozen (a future un-freeze fails CI)."""
    assert all(s.frozen for s in load_skill_manifest(SKILL_MANIFEST).skills)
    assert all(f.frozen for f in load_manifest(PHASE1C_MANIFEST).fixtures)


def test_assemble_frozen_gate_still_bites_on_unfrozen_or_mismatched_skill():
    """The artifacts are frozen now, so synthesize the failure cases to keep gate coverage:
    an unfrozen skill → SkillNotFrozen; a frozen skill whose hash no longer matches → SkillHashMismatch."""
    rm = load_run_matrix("runs/phase1c.yaml")
    manifest = load_manifest(PHASE1C_MANIFEST)
    skills = load_skill_manifest(SKILL_MANIFEST)
    on_unit = next(u for u in expand_matrix(rm, manifest, skills) if u.cell_id.skill_arm == "on")

    unfrozen = on_unit.skill_entry.model_copy(update={"frozen": False, "sha256": "TBD"})
    with pytest.raises(SkillNotFrozen):
        assemble(on_unit.model_copy(update={"skill_entry": unfrozen}), _read_file, require_frozen=True)

    wrong = on_unit.skill_entry.model_copy(update={"sha256": "0" * 64})
    with pytest.raises(SkillHashMismatch):
        assemble(on_unit.model_copy(update={"skill_entry": wrong}), _read_file, require_frozen=True)


# --------------------------------------------------------------------------- record integrity

RAW_GEN = {
    "cache_creation": {"ephemeral_1h_input_tokens": 0, "ephemeral_5m_input_tokens": 0},
    "cache_creation_input_tokens": 0,
    "cache_read_input_tokens": 0,
    "inference_geo": "global",
    "input_tokens": 320,
    "output_tokens": 84,
    "output_tokens_details": {"thinking_tokens": 0},
    "server_tool_use": None,
    "service_tier": "standard",
}


def _skill_on_record(**over) -> CaptureRecord:
    cfg = CallConfig(model_role="haiku", model_id="claude-haiku-4-5-20251001", band="S",
                     effort=None, thinking="off", max_tokens=64000,
                     skill="short-form-copy-scaffold-v1")
    cell = CellId(task_id=6, task_name="short_form_copy", band="S", model_role="haiku",
                  model_id="claude-haiku-4-5-20251001", role_label="factorial", skill_arm="on")
    base = dict(
        run_id="run-test", cell_id=cell, config=cfg,
        config_hash=config_hash(cfg, tokenizer_version="tok-hs"),
        fixture_hash="a" * 64,
        model_id="claude-haiku-4-5-20251001", model_version="claude-haiku-4-5-20251001",
        tokenizer_version="tok-hs", sdk_version="0.109.2",
        usage_raw=copy.deepcopy(RAW_GEN), stop_reason="end_turn",
        call_role=CallRole.single, exec_path=ExecPath.sync_stream,
        latency_ms=10.0, wall_clock_s=0.5,
        skill_hash=skill_hash("the skill text"),
        response_text="Hook line.\nBody.\nBook a demo.\n#a #b",
    )
    base.update(over)
    return CaptureRecord(**base)


def test_skill_on_record_roundtrips_with_text():
    rec = _skill_on_record()
    again = CaptureRecord.from_jsonl_line(rec.to_jsonl_line())
    assert again.config.skill == "short-form-copy-scaffold-v1"
    assert again.cell_id.skill_arm == "on"
    assert again.skill_hash == rec.skill_hash
    assert again.response_text == rec.response_text  # output text persisted for the judge


def test_skill_on_config_without_skill_hash_is_rejected():
    with pytest.raises(ValidationError, match="block/skill_hash mismatch"):
        _skill_on_record(skill_hash=None)


def test_skill_arm_must_agree_with_config_skill():
    cell_off = CellId(task_id=6, task_name="short_form_copy", band="S", model_role="haiku",
                      model_id="claude-haiku-4-5-20251001", role_label="factorial", skill_arm="off")
    with pytest.raises(ValidationError, match="skill_arm/config mismatch"):
        _skill_on_record(cell_id=cell_off)


def test_bad_skill_hash_shape_is_rejected():
    with pytest.raises(ValidationError, match="skill_hash must be"):
        _skill_on_record(skill_hash="not-a-sha")


# --- judge_hash (Exp 1c quality-judge instrument freeze, judge-spec §2) -----------------------

_JUDGE_COMPONENTS = {
    "judge_model": "claude-opus-4-8",
    "k": 3,
    "margin_pp": 10,
    "prompt_rubric": "rubric prompt text",
    "prompt_pairwise": "pairwise prompt text",
    "rubrics": {"6": "copy checks", "9": "memo checks"},
}


def test_judge_hash_is_a_bare_sha256():
    from harness.hashing import is_sha256_hex, judge_hash

    assert is_sha256_hex(judge_hash(_JUDGE_COMPONENTS))


def test_judge_hash_is_key_order_independent():
    from harness.hashing import judge_hash

    reordered = {k: _JUDGE_COMPONENTS[k] for k in reversed(list(_JUDGE_COMPONENTS))}
    assert judge_hash(reordered) == judge_hash(_JUDGE_COMPONENTS)


def test_judge_hash_changes_when_any_component_changes():
    from harness.hashing import judge_hash

    base = judge_hash(_JUDGE_COMPONENTS)
    for key, new in [("margin_pp", 5), ("k", 5), ("judge_model", "claude-sonnet-4-6"),
                     ("prompt_rubric", "edited"), ("prompt_pairwise", "edited"),
                     ("rubrics", {"6": "edited", "9": "memo checks"})]:
        assert judge_hash({**_JUDGE_COMPONENTS, key: new}) != base, key


def test_judge_hash_is_domain_separated_from_skill_and_fixture():
    # Same payload bytes under a different domain key must not collide.
    from harness.hashing import fixture_hash, judge_hash, skill_hash

    text = "identical bytes"
    assert judge_hash({"x": text}) != skill_hash(text) != fixture_hash(text)
