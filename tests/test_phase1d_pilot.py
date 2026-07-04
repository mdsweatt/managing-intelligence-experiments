"""Tests for the Phase-1d skill-off pilot mechanics (charter §5 Exp 1d; design spine S3).

The pilot measures each new task's NATURAL loose output (in words, from response_text) BEFORE the
skills and cap/mandate labels freeze — so its matrix runs the factorial machinery with the arm set
restricted to {off} and no skill declared. Load-bearing guarantees:

  * **`arms: [off]` runs skill-less:** a factorial task whose effective arms exclude "on" needs no
    `skill` id; expansion yields one off-arm unit per model with `role_label == "factorial"` (so
    `response_text` persists — the pilot's entire point) and a config_hash byte-identical to the
    pre-skill schema (invariant-3 back-compat, same trick as the skill/neutral axes).
  * **`thinking` honored at the model-natural convention:** 1d #15 runs thinking-on; Haiku supports
    neither the effort knob nor ADAPTIVE thinking (live-verification 2026-06-16), so a thinking task
    expands to adaptive on Sonnet/Opus and off on Haiku — the arm remains the only within-cell axis.
  * **1c matrices are unperturbed:** no `arms`/`h7_label` key ⇒ prior behavior, byte-identical.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from harness.config import TaskSpec, config_hash, load_run_matrix, load_manifest
from harness.expand import expand_matrix
from harness.hashing import canonical_json, sha256_hex
from harness.schema import CallConfig

HAIKU = "claude-haiku-4-5-20251001"


def _pilot_task(**over) -> TaskSpec:
    base = dict(id=23, name="spec_draft", cost_axis="output", bands=["S"],
                factorial_models=["haiku", "sonnet", "opus"], arms=["off"])
    base.update(over)
    return TaskSpec(**base)


# --------------------------------------------------------------------------- TaskSpec validation

def test_arms_off_only_needs_no_skill():
    t = _pilot_task()
    assert t.skill is None
    assert t.effective_arms() == ("off",)


def test_arms_including_on_still_requires_skill():
    with pytest.raises(ValidationError, match="must declare a `skill` id"):
        _pilot_task(arms=["off", "on"])


def test_default_arms_still_require_skill():
    """No `arms` key ⇒ the 1c default {off,on} ⇒ skill required — 1c matrices unperturbed."""
    with pytest.raises(ValidationError, match="must declare a `skill` id"):
        _pilot_task(arms=None)


def test_arms_neutral_requires_neutral_id():
    with pytest.raises(ValidationError, match="requires a `neutral` block id"):
        _pilot_task(arms=["off", "neutral"])


def test_arms_must_not_be_empty():
    with pytest.raises(ValidationError, match="must not be empty"):
        _pilot_task(arms=[])


def test_arms_and_h7_label_are_factorial_only():
    for field in ("arms", "h7_label"):
        with pytest.raises(ValidationError, match="only used by factorial"):
            TaskSpec(id=1, name="draft_email", cost_axis="input", bands=["S"],
                     hypothesis="haiku", **{field: ["off"] if field == "arms" else "cap"})


def test_h7_label_round_trips_on_factorial_task():
    t = _pilot_task(h7_label="mandate")
    assert t.h7_label == "mandate"


# --------------------------------------------------------------------------- expansion

def _pilot_rm():
    """A 1c-shaped matrix with the tasks swapped for two pilot (arms:[off]) tasks, one thinking-on."""
    rm = load_run_matrix("runs/phase1c.yaml")
    tasks = [
        _pilot_task(),
        _pilot_task(id=15, name="strategy_brief_1d", thinking="adaptive"),
    ]
    return rm.model_copy(update={"tasks": tasks})


def _fixture_entry(task_id: int):
    """Reuse a frozen 1c fixture entry, rebadged to the pilot task id (content is irrelevant to
    expansion mechanics — lookup is by (task_id, band))."""
    man = load_manifest("fixtures/manifest-phase1c.yaml")
    entry = next(f for f in man.fixtures if f.task_id == 6)
    return entry.model_copy(update={"task_id": task_id})


def _pilot_manifest():
    man = load_manifest("fixtures/manifest-phase1c.yaml")
    return man.model_copy(update={"fixtures": [_fixture_entry(23), _fixture_entry(15)]})


def test_expand_pilot_yields_one_off_unit_per_model_no_skill_manifest_needed():
    units = expand_matrix(_pilot_rm(), _pilot_manifest())          # note: NO skill manifest passed
    t23 = [u for u in units if u.cell_id.task_id == 23]
    assert len(t23) == 3                                            # 3 models × 1 arm
    for u in t23:
        assert u.cell_id.skill_arm == "off"
        assert u.role_label == "factorial"                          # => response_text persists
        assert u.config.skill is None and u.config.neutral is None
        assert u.skill_entry is None and u.neutral_entry is None


def test_pilot_config_hash_is_byte_identical_to_pre_skill_schema():
    units = expand_matrix(_pilot_rm(), _pilot_manifest())
    u = next(u for u in units if u.cell_id.task_id == 23 and u.cell_id.model_role == "haiku")
    payload = u.config.model_dump()
    payload.pop("skill")
    payload.pop("neutral")
    payload["tokenizer_version"] = "tok-hs"
    assert config_hash(u.config, tokenizer_version="tok-hs") == sha256_hex(canonical_json(payload))


def test_pilot_thinking_adaptive_on_sonnet_opus_off_on_haiku():
    units = expand_matrix(_pilot_rm(), _pilot_manifest())
    t15 = {u.cell_id.model_role: u for u in units if u.cell_id.task_id == 15}
    assert t15["haiku"].config.thinking == "off"          # no adaptive support (verified 2026-06-16)
    assert t15["sonnet"].config.thinking == "adaptive"
    assert t15["opus"].config.thinking == "adaptive"
    # the non-thinking pilot task stays off everywhere
    t23 = {u.cell_id.model_role: u for u in units if u.cell_id.task_id == 23}
    assert {u.config.thinking for u in t23.values()} == {"off"}


def test_factorial_thinking_enabled_fails_loud_at_expansion():
    rm = _pilot_rm()
    tasks = [rm.tasks[0], rm.tasks[1].model_copy(update={"thinking": "enabled"})]
    with pytest.raises(NotImplementedError, match="budget_tokens"):
        expand_matrix(rm.model_copy(update={"tasks": tasks}), _pilot_manifest())


def test_1c_matrix_expansion_unchanged():
    """The exact 1c call still yields 18 two-arm cells, all thinking-off (regression guard)."""
    from harness.config import load_skill_manifest
    rm = load_run_matrix("runs/phase1c.yaml")
    manifest = load_manifest("fixtures/manifest-phase1c.yaml")
    skills = load_skill_manifest("fixtures/skills/manifest.yaml")
    units = expand_matrix(rm, manifest, skills)
    assert len(units) == 18
    assert {u.cell_id.skill_arm for u in units} == {"off", "on"}
    assert {u.config.thinking for u in units} == {"off"}
