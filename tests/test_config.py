"""Tests for harness.config — run-matrix / manifest / prices validation + hashing.

The loaders are exercised against the *real* repo YAML (runs/phase1a.yaml,
fixtures/manifest.yaml, prices/prices-2026-06.yaml) — round-tripping the actual
files is the strongest guarantee the models match what the harness consumes, and
catches drift if a YAML changes. The hashing tests pin determinism + the documented
fixture-hash convention.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from harness.config import (
    Manifest,
    Prices,
    RunMatrix,
    canonical_json,
    config_hash,
    fixture_hash,
    load_manifest,
    load_prices,
    load_run_matrix,
)
from harness.schema import CallConfig

REPO = Path(__file__).resolve().parent.parent
PHASE1A = REPO / "runs" / "phase1a.yaml"
MANIFEST = REPO / "fixtures" / "manifest.yaml"
PRICES = REPO / "prices" / "prices-2026-06.yaml"


# --------------------------------------------------------------------------- run matrix


def test_load_run_matrix_validates_real_phase1a():
    rm = load_run_matrix(PHASE1A)
    assert isinstance(rm, RunMatrix)
    assert rm.meta.n_per_cell == 20
    assert rm.meta.cost_ceiling_usd == 500
    # tokenizer is NOT shared: Opus differs from Haiku/Sonnet.
    assert rm.models["opus"].tokenizer == "tok-opus"
    assert rm.models["haiku"].tokenizer == "tok-hs"
    assert rm.models["haiku"].cache_min == 4096
    assert rm.models["sonnet"].max_output == 128000


def test_run_matrix_has_all_phase1a_tasks():
    rm = load_run_matrix(PHASE1A)
    ids = {t.id for t in rm.tasks}
    # Phase 1a discrete/cache/thinking/turns/payload cells (1b deferred: 13,14,20,21).
    # #22 = demand-driven creative meta-prompting cell, added 2026-06-17 (charter §5).
    assert ids == {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 15, 16, 17, 18, 19, 22}


def test_run_matrix_preserves_per_task_config():
    rm = load_run_matrix(PHASE1A)
    by_id = {t.id: t for t in rm.tasks}
    # #15 thinking cell: bands are effort levels.
    assert by_id[15].bands == ["low", "high", "max"]
    assert by_id[15].bands_are_effort is True
    assert by_id[15].thinking == "adaptive"
    # cache cell carries its warm-once spec + Haiku floor.
    assert by_id[10].cache is not None
    assert by_id[10].cache.mode == "warm_once_read_many"
    assert by_id[10].cache.min_floor_if_haiku == 4096
    # multi-turn cell.
    assert by_id[16].multiturn is not None
    assert by_id[16].multiturn.per_turn_capture is True
    # #22 creative meta-prompting: output axis, S only, Sonnet-hyp + Opus over-service + Haiku down-probe.
    assert by_id[22].cost_axis == "output"
    assert by_id[22].bands == ["S"]
    assert by_id[22].hypothesis == "sonnet"
    assert by_id[22].over_service == ["opus"]
    assert by_id[22].down_probe == ["haiku"]


def test_run_matrix_rejects_unknown_key():
    raw = yaml.safe_load(PHASE1A.read_text())
    raw["meta"]["surprise_knob"] = 1  # an undocumented key must fail loud
    with pytest.raises(ValidationError):
        RunMatrix.model_validate(raw)


def test_run_matrix_rejects_unknown_task_key():
    raw = yaml.safe_load(PHASE1A.read_text())
    raw["tasks"][0]["mystery"] = "x"
    with pytest.raises(ValidationError):
        RunMatrix.model_validate(raw)


# --------------------------------------------------------------------------- manifest


def test_load_manifest_validates_real_file():
    m = load_manifest(MANIFEST)
    assert isinstance(m, Manifest)
    assert m.schema_version == 2
    assert len(m.fixtures) >= 3  # the worked task-07 example (S/M/L)


def test_manifest_accepts_tbd_placeholders():
    # An uncurated (deferred) fixture carries TBD token counts + sha256 until the owner measures +
    # freezes. Tested SYNTHETICALLY (mirrors test_manifest_accepts_real_token_counts) so it does not
    # depend on the live manifest's transient drafting state: once a tranche is frozen the registry
    # may legitimately carry zero TBD fixtures (true after the 2026-06-21 Phase-1a freeze).
    raw = yaml.safe_load(MANIFEST.read_text())
    raw["fixtures"][0]["recorded_token_counts"] = {"tok_hs": "TBD", "tok_opus": "TBD"}
    raw["fixtures"][0]["sha256"] = "TBD"
    raw["fixtures"][0]["frozen"] = False
    m = Manifest.model_validate(raw)
    assert m.fixtures[0].recorded_token_counts.tok_hs == "TBD"
    assert m.fixtures[0].frozen is False  # a TBD fixture is never frozen (curation contract)
    # Invariant on the LIVE manifest: once frozen, a fixture must carry measured (non-TBD) counts,
    # not just a real sha256 (frozen implies fully measured).
    for f in load_manifest(MANIFEST).fixtures:
        if f.frozen:
            assert f.recorded_token_counts.tok_hs != "TBD" and f.recorded_token_counts.tok_opus != "TBD"


def test_manifest_accepts_real_token_counts():
    raw = yaml.safe_load(MANIFEST.read_text())
    raw["fixtures"][0]["recorded_token_counts"] = {"tok_hs": 980, "tok_opus": 1325}
    m = Manifest.model_validate(raw)
    assert m.fixtures[0].recorded_token_counts.tok_hs == 980


def test_manifest_rejects_unknown_fixture_key():
    raw = yaml.safe_load(MANIFEST.read_text())
    raw["fixtures"][0]["bogus"] = 1
    with pytest.raises(ValidationError):
        Manifest.model_validate(raw)


# --------------------------------------------------------------------------- prices


def test_load_prices_accepts_tbd_placeholders():
    # The loader must accept the TBD-placeholder form (the NumOrTBD union) — tested in-memory so it
    # stays valid after Phase 6 fills the live file. (Pre-Phase-6 the live file was all-TBD.)
    raw = yaml.safe_load(PRICES.read_text())
    raw["as_of"] = "TBD"
    raw["source"] = "TBD"
    for model in raw["models"].values():
        for k in ("input", "output", "cache_read", "cache_write_5m", "thinking"):
            model[k] = "TBD"
    p = Prices.model_validate(raw)
    assert isinstance(p, Prices)
    assert p.currency == "USD"
    assert p.models["claude-opus-4-8"].input == "TBD"


def test_live_prices_file_is_filled_at_phase6():
    # Phase 6 (analysis) filled prices/prices-2026-06.yaml from current published pricing (verified
    # live 2026-06-25). Value-agnostic on purpose — prices rot quarterly; we assert *filled*, not a
    # specific number, so a future price update doesn't break the test.
    p = load_prices(PRICES)
    assert p.as_of != "TBD" and p.source != "TBD"
    for model in p.models.values():
        for v in (model.input, model.output, model.cache_read, model.cache_write_5m, model.thinking):
            assert isinstance(v, (int, float)) and v > 0


def test_prices_accept_real_values():
    raw = yaml.safe_load(PRICES.read_text())
    raw["models"]["claude-opus-4-8"]["input"] = 15.0
    raw["models"]["claude-opus-4-8"]["cache_read"] = 1.5
    p = Prices.model_validate(raw)
    assert p.models["claude-opus-4-8"].input == 15.0


# --------------------------------------------------------------------------- hashing


def test_canonical_json_is_key_order_independent():
    assert canonical_json({"b": 1, "a": 2}) == canonical_json({"a": 2, "b": 1})


def test_config_hash_is_deterministic():
    c1 = CallConfig(
        model_role="opus",
        model_id="claude-opus-4-8",
        band="low",
        effort="low",
        thinking="adaptive",
        max_tokens=128000,
    )
    c2 = CallConfig(
        model_role="opus",
        model_id="claude-opus-4-8",
        band="low",
        effort="low",
        thinking="adaptive",
        max_tokens=128000,
    )
    assert config_hash(c1, tokenizer_version="tok-opus") == config_hash(
        c2, tokenizer_version="tok-opus"
    )


def test_config_hash_changes_when_config_changes():
    base = CallConfig(
        model_role="opus",
        model_id="claude-opus-4-8",
        band="low",
        effort="low",
        thinking="adaptive",
        max_tokens=128000,
    )
    changed = base.model_copy(update={"effort": "max"})
    h = config_hash(base, tokenizer_version="tok-opus")
    assert h != config_hash(changed, tokenizer_version="tok-opus")
    # tokenizer is part of the config identity (same fixture → different token count).
    assert h != config_hash(base, tokenizer_version="tok-hs")


def test_config_hash_is_hex_sha256():
    h = config_hash(
        CallConfig(
            model_role="haiku",
            model_id="claude-haiku-4-5-20251001",
            band="S",
            effort=None,
            thinking="off",
            max_tokens=64000,
        ),
        tokenizer_version="tok-hs",
    )
    assert len(h) == 64 and all(ch in "0123456789abcdef" for ch in h)


def test_fixture_hash_pins_collision_safe_convention():
    # Domain-separated (canonical JSON), NOT raw concatenation. Pins the exact bytes hashed
    # so a frozen fixture's sha256 is reproducible by any auditor.
    canonical = '{"input":"INPUT","prompt":"PROMPT"}'
    expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    assert fixture_hash("PROMPT", "INPUT") == expected


def test_fixture_hash_prompt_only_uses_null_input():
    canonical = '{"input":null,"prompt":"PROMPT"}'
    expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    assert fixture_hash("PROMPT", None) == expected
    assert fixture_hash("PROMPT") == expected


def test_fixture_hash_has_no_concatenation_collision():
    # The exact failure of literal "(prompt + input)": these must NOT collide.
    assert fixture_hash("a", "b") != fixture_hash("ab", None)
    assert fixture_hash("a", "b") != fixture_hash("ab", "")
