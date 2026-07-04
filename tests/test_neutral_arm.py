"""Tests for the Phase-1d neutral-system arm (charter §5 H8) — the 3rd factorial arm.

Phase 1c had a 2-arm skill axis {off, on}. Phase 1d adds a **neutral** arm: a frozen, length-matched,
structure-free `system` block (the H8 control) that isolates "the scaffold's structure" from "a
task-directed system block is present". The load-bearing guarantees mirror test_phase1c.py:

  * **Back-compat:** adding a `neutral` field to CallConfig + "neutral" to CellId.skill_arm must NOT
    perturb any Phase-1a/1c identity. A neutral=None config hashes byte-identically to the pre-neutral
    schema, so 1c skill-on records still recompute their config_hash.
  * **Distinct identity:** off / neutral / on are three distinct config_hashes and cell keys.
  * **A task opts in:** only a factorial task that declares a `neutral` id gets the 3rd arm; #4-style
    placebos (no neutral) stay 2-arm, so a 1c matrix is unchanged.
"""

from __future__ import annotations

import copy

import pytest
from pydantic import ValidationError

from harness.assemble import SkillHashMismatch, SkillNotFrozen, assemble
from harness.config import (
    NeutralManifest,
    SkillEntry,
    config_hash,
    load_manifest,
    load_neutral_manifest,
    load_run_matrix,
    load_skill_manifest,
)
from harness.expand import expand_matrix
from harness.hashing import canonical_json, sha256_hex, skill_hash
from harness.schema import CallConfig, CallRole, CaptureRecord, CellId, ExecPath

from pathlib import Path

FIXTURES_ROOT = "fixtures"
SKILL_MANIFEST = "fixtures/skills/manifest.yaml"
NEUTRAL_MANIFEST = "fixtures/neutral/manifest.yaml"
PHASE1C_MANIFEST = "fixtures/manifest-phase1c.yaml"
HAIKU = "claude-haiku-4-5-20251001"


def _read_file(rel: str) -> str:
    return (Path(FIXTURES_ROOT) / rel).read_text(encoding="utf-8")


# --------------------------------------------------------------------------- config_hash

def test_config_hash_neutral_none_is_byte_identical_to_pre_neutral():
    """A neutral=None config must hash exactly as the pre-neutral schema did — so every 1c skill-on
    record (which predates the neutral field) still recomputes-and-verifies its config_hash."""
    cfg = CallConfig(model_role="sonnet", model_id="claude-sonnet-4-6", band="S",
                     effort="high", thinking="off", max_tokens=128000,
                     skill="short-form-copy-scaffold-v1")
    assert cfg.neutral is None
    payload = cfg.model_dump()
    payload.pop("neutral")                       # the shape before the field existed
    payload["tokenizer_version"] = "tok-hs"
    expected = sha256_hex(canonical_json(payload))
    assert config_hash(cfg, tokenizer_version="tok-hs") == expected


def test_config_hash_three_arms_are_distinct():
    base = dict(model_role="haiku", model_id=HAIKU, band="S", effort=None,
                thinking="off", max_tokens=64000)
    off = config_hash(CallConfig(**base), tokenizer_version="tok-hs")
    on = config_hash(CallConfig(**base, skill="short-form-copy-scaffold-v1"), tokenizer_version="tok-hs")
    neutral = config_hash(CallConfig(**base, neutral="short-form-copy-neutral-v1"), tokenizer_version="tok-hs")
    assert len({off, on, neutral}) == 3


def test_callconfig_skill_and_neutral_are_mutually_exclusive():
    with pytest.raises(ValidationError, match="mutually exclusive"):
        CallConfig(model_role="haiku", model_id=HAIKU, band="S", max_tokens=1000,
                   skill="s", neutral="n")


# --------------------------------------------------------------------------- cell key

def test_cell_key_neutral_arm_is_suffixed():
    common = dict(task_id=6, task_name="short_form_copy", band="S",
                  model_role="haiku", model_id=HAIKU, role_label="factorial")
    assert CellId(**common, skill_arm="neutral").key() == "t6:S:haiku:factorial:skill-neutral"
    # off/on unchanged (back-compat)
    assert CellId(**common, skill_arm="off").key() == "t6:S:haiku:factorial"
    assert CellId(**common, skill_arm="on").key() == "t6:S:haiku:factorial:skill-on"


# --------------------------------------------------------------------------- expansion

def _rm_with_neutral_on_6():
    """The 1c matrix with a neutral id added to task #6 (and NOT #9), + a matching neutral manifest."""
    rm = load_run_matrix("runs/phase1c.yaml")
    tasks = [t.model_copy(update={"neutral": "short-form-copy-neutral-v1"}) if t.id == 6 else t
             for t in rm.tasks]
    rm2 = rm.model_copy(update={"tasks": tasks})
    neutrals = NeutralManifest(schema_version=1, neutral=[
        SkillEntry(id="short-form-copy-neutral-v1",
                   file="neutral/short-form-copy-neutral-v1.md",
                   sha256="TBD", frozen=False, applies_to=[6])])
    return rm2, neutrals


def test_expand_three_arms_when_task_declares_neutral():
    rm, neutrals = _rm_with_neutral_on_6()
    manifest = load_manifest(PHASE1C_MANIFEST)
    skills = load_skill_manifest(SKILL_MANIFEST)
    units = expand_matrix(rm, manifest, skills, neutrals)

    t6 = [u for u in units if u.cell_id.task_id == 6]
    assert len(t6) == 9  # 3 models × 3 arms
    assert {u.cell_id.skill_arm for u in t6} == {"off", "neutral", "on"}
    for u in t6:
        arm = u.cell_id.skill_arm
        assert (u.config.skill is not None) == (arm == "on")
        assert (u.skill_entry is not None) == (arm == "on")
        assert (u.config.neutral is not None) == (arm == "neutral")
        assert (u.neutral_entry is not None) == (arm == "neutral")


def test_expand_task_without_neutral_stays_two_arm():
    """#9 has no neutral id -> unchanged 2-arm {off,on} (a 1c matrix is not perturbed)."""
    rm, neutrals = _rm_with_neutral_on_6()
    manifest = load_manifest(PHASE1C_MANIFEST)
    skills = load_skill_manifest(SKILL_MANIFEST)
    units = expand_matrix(rm, manifest, skills, neutrals)
    t9 = [u for u in units if u.cell_id.task_id == 9]
    assert len(t9) == 6
    assert {u.cell_id.skill_arm for u in t9} == {"off", "on"}


def test_expand_1c_matrix_unchanged_without_neutral_manifest():
    """The exact 1c call (no neutral manifest) still yields 18 two-arm cells."""
    rm = load_run_matrix("runs/phase1c.yaml")
    manifest = load_manifest(PHASE1C_MANIFEST)
    skills = load_skill_manifest(SKILL_MANIFEST)
    units = expand_matrix(rm, manifest, skills)
    assert len(units) == 18
    assert {u.cell_id.skill_arm for u in units} == {"off", "on"}


# --------------------------------------------------------------------------- assemble (real artifacts)

def test_assemble_injects_neutral_block_as_system():
    rm, neutrals = _rm_with_neutral_on_6()
    # use the REAL frozen neutral manifest so the frozen gate + on-disk sha256 are exercised
    neutrals = load_neutral_manifest(NEUTRAL_MANIFEST)
    manifest = load_manifest(PHASE1C_MANIFEST)
    skills = load_skill_manifest(SKILL_MANIFEST)
    units = expand_matrix(rm, manifest, skills, neutrals)

    nu = next(u for u in units if u.cell_id.task_id == 6 and u.cell_id.skill_arm == "neutral")
    plan = assemble(nu, _read_file, require_frozen=True)
    neutral_text = _read_file(nu.neutral_entry.file)
    assert plan.system == [{"type": "text", "text": neutral_text}]
    assert plan.skill_hash == skill_hash(neutral_text)   # the injected block's hash rides on the record
    # the neutral block is STRUCTURE-FREE: it must not carry the skill's format/length constraints
    assert "60 words" not in neutral_text and "hashtag" not in neutral_text.lower()


def test_neutral_frozen_gate_bites_on_mismatch():
    rm, _ = _rm_with_neutral_on_6()
    neutrals = load_neutral_manifest(NEUTRAL_MANIFEST)
    manifest = load_manifest(PHASE1C_MANIFEST)
    skills = load_skill_manifest(SKILL_MANIFEST)
    nu = next(u for u in expand_matrix(rm, manifest, skills, neutrals)
              if u.cell_id.skill_arm == "neutral")
    wrong = nu.neutral_entry.model_copy(update={"sha256": "0" * 64})
    with pytest.raises(SkillHashMismatch):
        assemble(nu.model_copy(update={"neutral_entry": wrong}), _read_file, require_frozen=True)


# --------------------------------------------------------------------------- record integrity

RAW_GEN = {
    "cache_creation": {"ephemeral_1h_input_tokens": 0, "ephemeral_5m_input_tokens": 0},
    "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0, "inference_geo": "global",
    "input_tokens": 320, "output_tokens": 84, "output_tokens_details": {"thinking_tokens": 0},
    "server_tool_use": None, "service_tier": "standard",
}


def _neutral_record(**over) -> CaptureRecord:
    cfg = CallConfig(model_role="haiku", model_id=HAIKU, band="S", effort=None, thinking="off",
                     max_tokens=64000, neutral="short-form-copy-neutral-v1")
    cell = CellId(task_id=6, task_name="short_form_copy", band="S", model_role="haiku",
                  model_id=HAIKU, role_label="factorial", skill_arm="neutral")
    base = dict(
        run_id="run-test", cell_id=cell, config=cfg,
        config_hash=config_hash(cfg, tokenizer_version="tok-hs"), fixture_hash="a" * 64,
        model_id=HAIKU, model_version=HAIKU, tokenizer_version="tok-hs", sdk_version="0.109.2",
        usage_raw=copy.deepcopy(RAW_GEN), stop_reason="end_turn",
        call_role=CallRole.single, exec_path=ExecPath.sync_stream, latency_ms=10.0, wall_clock_s=0.5,
        skill_hash=skill_hash("the neutral text"),
        response_text="A LinkedIn post about the product.",
    )
    base.update(over)
    return CaptureRecord(**base)


def test_neutral_record_roundtrips():
    rec = _neutral_record()
    again = CaptureRecord.from_jsonl_line(rec.to_jsonl_line())
    assert again.config.neutral == "short-form-copy-neutral-v1"
    assert again.config.skill is None
    assert again.cell_id.skill_arm == "neutral"
    assert again.skill_hash == rec.skill_hash


def test_neutral_arm_without_block_hash_is_rejected():
    # neutral set (a block was injected) but no skill_hash recorded -> half-set wiring bug
    with pytest.raises(ValidationError, match="mismatch"):
        _neutral_record(skill_hash=None)


def test_neutral_arm_must_agree_with_skill_arm():
    cell_off = CellId(task_id=6, task_name="short_form_copy", band="S", model_role="haiku",
                      model_id=HAIKU, role_label="factorial", skill_arm="off")
    with pytest.raises(ValidationError, match="mismatch"):
        _neutral_record(cell_id=cell_off)
