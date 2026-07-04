"""Hardening tests — the fail-loud holes found by the adversarial review of the
capture contract (18 confirmed findings). Each test pins a way a malformed capture
must now be REJECTED at validation time instead of silently entering the dataset.

Grouped by the cluster the finding belongs to. Raw usage fixtures are the live
shapes (docs/live-verification-2026-06-16.md).
"""

from __future__ import annotations

import copy
import math

import pytest
from pydantic import ValidationError

from harness.config import (
    FixtureEntry,
    ModelSpec,
    Proxy,
    RunMatrix,
    TaskSpec,
    config_hash,
    fixture_hash,
)
from harness.schema import (
    CallConfig,
    CallRole,
    CaptureRecord,
    CellId,
    UsageVector,
    derive_quarantine,
)

RAW = {
    "cache_creation": {"ephemeral_1h_input_tokens": 0, "ephemeral_5m_input_tokens": 0},
    "cache_creation_input_tokens": 0,
    "cache_read_input_tokens": 0,
    "inference_geo": "global",
    "input_tokens": 26,
    "output_tokens": 59,
    "output_tokens_details": {"thinking_tokens": 11},
    "server_tool_use": None,
    "service_tier": "standard",
}
RAW_CACHE_WRITE = {
    "cache_creation": {"ephemeral_1h_input_tokens": 0, "ephemeral_5m_input_tokens": 4504},
    "cache_creation_input_tokens": 4504,
    "cache_read_input_tokens": 0,
    "input_tokens": 9,
    "output_tokens": 5,
    "output_tokens_details": {"thinking_tokens": 0},
    "service_tier": "standard",
}
RAW_CACHE_READ = {
    "cache_creation": {"ephemeral_1h_input_tokens": 0, "ephemeral_5m_input_tokens": 0},
    "cache_creation_input_tokens": 0,
    "cache_read_input_tokens": 4504,
    "input_tokens": 9,
    "output_tokens": 5,
    "output_tokens_details": {"thinking_tokens": 0},
    "service_tier": "standard",
}

OPUS = "claude-opus-4-8"


def _cfg(**over) -> CallConfig:
    base = dict(
        model_role="opus",
        model_id=OPUS,
        band="low",
        effort="low",
        thinking="off",
        max_tokens=128000,
    )
    base.update(over)
    return CallConfig(**base)


def _cell(**over) -> CellId:
    base = dict(
        task_id=15,
        task_name="strategy_brief",
        band="low",
        model_role="opus",
        model_id=OPUS,
        role_label="hypothesis",
    )
    base.update(over)
    return CellId(**base)


def _valid(**over):
    """A fully-valid record kwargs dict with real, self-consistent hashes."""
    cfg = over.pop("config", None) or _cfg()
    tok = over.pop("tokenizer_version", "tok-opus")
    base = dict(
        run_id="run-test",
        cell_id=over.pop("cell_id", None) or _cell(),
        config=cfg,
        config_hash=config_hash(cfg, tokenizer_version=tok),
        fixture_hash=fixture_hash("prompt", "input"),
        model_id=OPUS,
        model_version=OPUS,
        tokenizer_version=tok,
        sdk_version="0.109.2",
        usage_raw=copy.deepcopy(RAW),
        stop_reason="end_turn",
        latency_ms=12.0,
        wall_clock_s=1.0,
    )
    base.update(over)
    return base


def _rec(**over) -> CaptureRecord:
    return CaptureRecord(**_valid(**over))


# ----------------------------------------------- Cluster A: missing provenance / measurement


def test_empty_config_hash_rejected():
    with pytest.raises(ValidationError):
        _rec(config_hash="")


def test_non_hex_config_hash_rejected():
    with pytest.raises(ValidationError):
        _rec(config_hash="sha256:not-a-real-hash")


def test_empty_provenance_stamps_rejected():
    for field in ("run_id", "model_id", "model_version", "tokenizer_version", "sdk_version"):
        with pytest.raises(ValidationError):
            _rec(**{field: ""})


def test_usage_raw_missing_input_tokens_fails_loud():
    with pytest.raises((ValidationError, ValueError)):
        UsageVector.from_raw({"output_tokens": 7})


def test_empty_usage_raw_fails_loud():
    with pytest.raises((ValidationError, ValueError)):
        UsageVector.from_raw({})


def test_record_with_empty_usage_raw_rejected():
    with pytest.raises(ValidationError):
        _rec(usage_raw={})


# ----------------------------------------------- Cluster: thinking component presence


def test_thinking_on_requires_output_tokens_details():
    raw = copy.deepcopy(RAW)
    del raw["output_tokens_details"]  # thinking call but the component never arrived
    with pytest.raises(ValidationError):
        _rec(config=_cfg(thinking="adaptive"), usage_raw=raw)


def test_thinking_off_does_not_require_details():
    raw = copy.deepcopy(RAW)
    del raw["output_tokens_details"]
    rec = _rec(config=_cfg(thinking="off"), usage_raw=raw)
    assert rec.usage.thinking_tokens == 0


def test_thinking_on_with_null_output_tokens_details_rejected():
    # The SDK-drop shape is present-but-None, NOT absent: final.usage.model_dump() emits
    # output_tokens_details=None when streaming discards it (client.py recovers it from the
    # message_delta with `.get(...) is None`). If that recovery also misses — unverified on
    # Opus 4.8 — the thinking component is gone and from_raw silently projects it to 0 at full
    # output cost. A thinking call with a null component must be REJECTED, not stored as a
    # silent zero (the present-and-{thinking_tokens:0} adaptive zero stays legitimate).
    raw = copy.deepcopy(RAW)
    raw["output_tokens_details"] = None
    with pytest.raises(ValidationError):
        _rec(config=_cfg(thinking="adaptive"), usage_raw=raw)


def test_thinking_on_with_zero_thinking_tokens_kept():
    # The other side of the boundary (regression guard for the null-rejection above): a PRESENT
    # {"thinking_tokens": 0} is a legitimate adaptive zero — the model chose not to think — not a
    # broken capture. It must be KEPT, never rejected. Distinguishes "null = gone" from "0 = real".
    raw = copy.deepcopy(RAW)
    raw["output_tokens_details"] = {"thinking_tokens": 0}
    rec = _rec(config=_cfg(thinking="adaptive"), usage_raw=raw)
    assert rec.usage.thinking_tokens == 0


# ----------------------------------------------- Cluster B: self-verifying hash + identity


def test_config_hash_mismatch_with_inlined_config_rejected():
    # A valid-looking hash that belongs to a DIFFERENT config must be caught.
    wrong = config_hash(_cfg(effort="max"), tokenizer_version="tok-opus")
    with pytest.raises(ValidationError):
        _rec(config=_cfg(effort="low"), config_hash=wrong)


def test_config_hash_must_match_tokenizer_used():
    # Hash computed with tok-hs but the record claims tok-opus → mismatch caught.
    h = config_hash(_cfg(), tokenizer_version="tok-hs")
    with pytest.raises(ValidationError):
        _rec(config_hash=h, tokenizer_version="tok-opus")


def test_model_id_disagreement_across_record_and_config_rejected():
    with pytest.raises(ValidationError):
        _rec(cell_id=_cell(model_id="claude-haiku-4-5-20251001", model_role="opus"))


def test_model_role_disagreement_rejected():
    with pytest.raises(ValidationError):
        _rec(config=_cfg(model_role="sonnet"))  # cell says opus, config says sonnet


# ----------------------------------------------- Cluster C: cache TTL split integrity


def test_cache_ttl_split_nonzero_with_zero_total_rejected():
    raw = copy.deepcopy(RAW_CACHE_WRITE)
    raw["cache_creation_input_tokens"] = 0  # total says nothing cached…
    raw["cache_creation"]["ephemeral_5m_input_tokens"] = 4504  # …but split says 4504
    with pytest.raises((ValidationError, ValueError)):
        UsageVector.from_raw(raw)


# ----------------------------------------------- Cluster D: cache write-side gate


def test_cache_write_that_created_nothing_is_quarantined():
    raw = copy.deepcopy(RAW_CACHE_WRITE)
    raw["cache_creation_input_tokens"] = 0
    raw["cache_creation"]["ephemeral_5m_input_tokens"] = 0
    raw["input_tokens"] = 2745  # prefix billed as fresh input — cache did not engage
    rec = _rec(usage_raw=raw, call_role=CallRole.write)
    assert rec.quarantined is True
    assert any("cache" in r and "creat" in r.lower() for r in rec.quarantine_reasons)


def test_cache_write_that_created_tokens_is_clean():
    rec = _rec(usage_raw=copy.deepcopy(RAW_CACHE_WRITE), call_role=CallRole.write)
    assert rec.quarantined is False


# ----------------------------------------------- Cluster E: numeric robustness


def test_infinite_latency_rejected():
    with pytest.raises(ValidationError):
        _rec(latency_ms=math.inf)


def test_nan_wall_clock_rejected():
    with pytest.raises(ValidationError):
        _rec(wall_clock_s=math.nan)


def test_fractional_token_count_fails_loud():
    raw = copy.deepcopy(RAW)
    raw["input_tokens"] = 26.5  # not an integer token count
    with pytest.raises((ValidationError, ValueError)):
        UsageVector.from_raw(raw)


# ----------------------------------------------- Cluster G: SDK Usage model as usage_raw


def test_sdk_usage_model_is_coerced_to_dict():
    class _FakeUsage:  # stands in for anthropic.types.Usage (a pydantic model)
        def model_dump(self):
            return copy.deepcopy(RAW)

    rec = _rec(usage_raw=_FakeUsage())
    assert isinstance(rec.usage_raw, dict)
    assert rec.usage.input_tokens == 26


# ----------------------------------------------- Cluster H: tool_result_tokens bound


def test_tool_result_tokens_cannot_exceed_folded_input():
    # The payload is folded into input; counting more than input is a caller bug.
    with pytest.raises(ValidationError):
        _rec(tool_result_tokens=10_000)  # input is only 26


def test_tool_result_tokens_within_bound_ok():
    rec = _rec(tool_result_tokens=20)
    assert rec.tool_result_tokens == 20


# ----------------------------------------------- Cluster F: closed-vocabulary enums (config)


def test_tokenizer_typo_rejected():
    with pytest.raises(ValidationError):
        ModelSpec(id=OPUS, tokenizer="tok-XYZ", cache_min=1024, max_output=128000)


def test_proxy_type_typo_rejected():
    with pytest.raises(ValidationError):
        Proxy(type="wordz", value="TBD")


def test_cost_axis_typo_rejected():
    with pytest.raises(ValidationError):
        TaskSpec(id=99, name="x", cost_axis="inputz", bands=["S"], hypothesis="haiku")


def test_model_role_typo_rejected_in_callconfig():
    with pytest.raises(ValidationError):
        CallConfig(model_role="gpt4", model_id=OPUS, band="S", max_tokens=1000)


# ----------------------------------------------- Cluster I: frozen-fixture contract


def test_frozen_fixture_requires_real_hash():
    base = dict(
        task_id=7,
        band="S",
        cost_axis="input",
        proxy={"type": "words", "value": 750},
        files={"prompt": "p.txt", "input": "i.md"},
        recorded_token_counts={"tok_hs": 980, "tok_opus": 1325},
    )
    # frozen=True with a TBD hash is a curation slip — must fail.
    with pytest.raises(ValidationError):
        FixtureEntry(**base, sha256="TBD", frozen=True)
    # frozen=True with a real 64-hex digest is fine.
    good = "a" * 64
    fe = FixtureEntry(**base, sha256=good, frozen=True)
    assert fe.frozen is True


# ----------------------------------------------- regression: real files & direct helpers


def test_derive_quarantine_back_compat_signature():
    # Existing callers pass only the original kwargs; new params default safely.
    q, reasons = derive_quarantine(
        stop_reason="end_turn",
        call_role=CallRole.single,
        cache_hit=None,
        cache_read_input_tokens=0,
    )
    assert q is False and reasons == []
