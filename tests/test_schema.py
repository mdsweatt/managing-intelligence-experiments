"""Tests for harness.schema — the capture contract.

These drive the *behavior* of the contract (the parts that can silently poison the
dataset if wrong): the raw-usage→typed-projection derivation and its consistency
check, the stop_reason quarantine gate, the cache-hit assertion on reads, verbatim
preservation of the raw usage object through JSONL, and fail-loud rejection of
unknown fields. The declarative field lists are exercised incidentally.

Raw usage fixtures below are the *live* shapes captured 2026-06-16
(docs/live-verification-2026-06-16.md), not invented.
"""

from __future__ import annotations

import copy
import json

import pytest
from pydantic import ValidationError

from harness.config import config_hash, fixture_hash
from harness.schema import (
    CallConfig,
    CallRole,
    CaptureRecord,
    CellId,
    ExecPath,
    UsageVector,
    derive_quarantine,
)

# --------------------------------------------------------------------------- fixtures

# Opus, adaptive thinking, effort=low — exact shape from the live verification doc.
RAW_THINKING = {
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

# A cache *write* call (warm-once): creation tokens present, nothing read yet.
RAW_CACHE_WRITE = {
    "cache_creation": {"ephemeral_1h_input_tokens": 0, "ephemeral_5m_input_tokens": 4504},
    "cache_creation_input_tokens": 4504,
    "cache_read_input_tokens": 0,
    "inference_geo": "global",
    "input_tokens": 9,
    "output_tokens": 5,
    "output_tokens_details": {"thinking_tokens": 0},
    "server_tool_use": None,
    "service_tier": "standard",
}

# A cache *read* call: read tokens high, fresh input low (the assertable hit shape).
RAW_CACHE_READ = {
    "cache_creation": {"ephemeral_1h_input_tokens": 0, "ephemeral_5m_input_tokens": 0},
    "cache_creation_input_tokens": 0,
    "cache_read_input_tokens": 4504,
    "inference_geo": "global",
    "input_tokens": 9,
    "output_tokens": 5,
    "output_tokens_details": {"thinking_tokens": 0},
    "server_tool_use": None,
    "service_tier": "standard",
}


def _cell(**over) -> CellId:
    base = dict(
        task_id=15,
        task_name="strategy_brief",
        band="low",
        model_role="opus",
        model_id="claude-opus-4-8",
        role_label="hypothesis",
    )
    base.update(over)
    return CellId(**base)


def _config(**over) -> CallConfig:
    base = dict(
        model_role="opus",
        model_id="claude-opus-4-8",
        band="low",
        effort="low",
        thinking="adaptive",
        max_tokens=128000,
    )
    base.update(over)
    return CallConfig(**base)


def _record(**over) -> CaptureRecord:
    base = dict(
        run_id="run-test",
        model_id="claude-opus-4-8",
        model_version="claude-opus-4-8",
        tokenizer_version="tok-opus",
        sdk_version="0.109.2",
        usage_raw=copy.deepcopy(RAW_THINKING),
        stop_reason="end_turn",
        call_role=CallRole.single,
        exec_path=ExecPath.sync_stream,
        latency_ms=1234.5,
        wall_clock_s=2.5,
        request_id="req_abc",
    )
    base.update(over)
    # Defaults computed AFTER overrides so config_hash matches the (possibly overridden) config.
    base.setdefault("config", _config())
    base.setdefault("cell_id", _cell())
    base.setdefault(
        "config_hash", config_hash(base["config"], tokenizer_version=base["tokenizer_version"])
    )
    base.setdefault("fixture_hash", fixture_hash("prompt", "input"))
    return CaptureRecord(**base)


# --------------------------------------------------------------------------- UsageVector


def test_usage_vector_from_raw_extracts_all_components():
    u = UsageVector.from_raw(RAW_THINKING)
    assert u.input_tokens == 26
    assert u.output_tokens == 59
    assert u.thinking_tokens == 11  # pulled out of nested output_tokens_details
    assert u.cache_read_input_tokens == 0
    assert u.cache_creation_input_tokens == 0
    assert u.service_tier == "standard"


def test_usage_vector_splits_cache_creation_by_ttl():
    u = UsageVector.from_raw(RAW_CACHE_WRITE)
    assert u.cache_creation_input_tokens == 4504
    assert u.cache_creation_5m == 4504
    assert u.cache_creation_1h == 0


def test_usage_vector_coerces_missing_optionals_to_zero():
    # API may send null (not 0) for cache fields; thinking details may be absent entirely.
    raw = {"input_tokens": 12, "output_tokens": 7, "cache_read_input_tokens": None}
    u = UsageVector.from_raw(raw)
    assert u.cache_read_input_tokens == 0
    assert u.cache_creation_input_tokens == 0
    assert u.thinking_tokens == 0


def test_usage_vector_flags_cache_ttl_split_mismatch():
    # If the per-TTL breakdown doesn't sum to the total, the capture is corrupt — fail loud.
    raw = copy.deepcopy(RAW_CACHE_WRITE)
    raw["cache_creation"]["ephemeral_5m_input_tokens"] = 99  # 99 + 0 != 4504
    with pytest.raises(ValidationError):
        UsageVector.from_raw(raw)


# --------------------------------------------------- raw ↔ projection consistency


def test_record_derives_projection_from_raw_usage():
    rec = _record()
    assert rec.usage.input_tokens == 26
    assert rec.usage.thinking_tokens == 11


def test_record_rejects_projection_inconsistent_with_raw():
    # Hand-construct a record whose typed projection disagrees with the verbatim raw dict.
    bad = UsageVector.from_raw(RAW_THINKING).model_copy(update={"output_tokens": 999})
    with pytest.raises(ValidationError):
        _record(usage=bad)


def test_record_preserves_raw_usage_verbatim_including_unknown_keys():
    # Forward-compat: a usage field Anthropic adds later must survive untouched in usage_raw.
    raw = copy.deepcopy(RAW_THINKING)
    raw["some_future_token_field"] = {"nested": 7}
    rec = _record(usage_raw=raw)
    line = rec.to_jsonl_line()
    back = CaptureRecord.from_jsonl_line(line)
    assert back.usage_raw == raw
    assert back.usage_raw["some_future_token_field"] == {"nested": 7}


def test_jsonl_round_trip_is_lossless():
    rec = _record()
    back = CaptureRecord.from_jsonl_line(rec.to_jsonl_line())
    assert back.model_dump() == rec.model_dump()


# --------------------------------------------------- stop_reason quarantine gate


def test_derive_quarantine_truncation_is_quarantined():
    q, reasons = derive_quarantine(
        stop_reason="max_tokens",
        call_role=CallRole.single,
        cache_hit=None,
        cache_read_input_tokens=0,
    )
    assert q is True
    assert any("trunc" in r or "stop_reason" in r for r in reasons)


def test_derive_quarantine_natural_completion_is_clean():
    q, reasons = derive_quarantine(
        stop_reason="end_turn",
        call_role=CallRole.single,
        cache_hit=None,
        cache_read_input_tokens=0,
    )
    assert q is False
    assert reasons == []


def test_record_with_truncated_stop_reason_is_quarantined():
    rec = _record(stop_reason="max_tokens")
    assert rec.quarantined is True


def test_record_with_natural_stop_reason_is_clean():
    rec = _record(stop_reason="end_turn")
    assert rec.quarantined is False
    assert rec.quarantine_reasons == []


def test_record_with_refusal_stop_reason_is_quarantined():
    rec = _record(stop_reason="refusal")
    assert rec.quarantined is True


# --------------------------------------------------- cache-hit assertion on reads


def test_read_call_with_hit_is_clean():
    rec = _record(
        usage_raw=copy.deepcopy(RAW_CACHE_READ),
        call_role=CallRole.read,
        cache_hit=True,
        stop_reason="end_turn",
    )
    assert rec.quarantined is False


def test_read_call_with_zero_cache_read_is_quarantined_even_if_hit_claimed():
    # A TTL-expired read silently becomes a fresh-input call. The contract must catch it
    # regardless of what the harness *claimed*, because cache_read_input_tokens == 0.
    raw = copy.deepcopy(RAW_CACHE_READ)
    raw["cache_read_input_tokens"] = 0
    raw["input_tokens"] = 4513  # the prefix came back as fresh input
    rec = _record(usage_raw=raw, call_role=CallRole.read, cache_hit=True, stop_reason="end_turn")
    assert rec.quarantined is True
    assert any("cache" in r for r in rec.quarantine_reasons)


def test_read_call_with_explicit_miss_is_quarantined():
    rec = _record(
        usage_raw=copy.deepcopy(RAW_CACHE_READ),
        call_role=CallRole.read,
        cache_hit=False,
        stop_reason="end_turn",
    )
    assert rec.quarantined is True


def test_read_call_requires_cache_hit_assertion():
    # call_role=read without a cache_hit verdict is a contract violation, not a default-clean.
    with pytest.raises(ValidationError):
        _record(
            usage_raw=copy.deepcopy(RAW_CACHE_READ),
            call_role=CallRole.read,
            cache_hit=None,
            stop_reason="end_turn",
        )


def test_cache_hit_only_meaningful_on_reads():
    # Asserting a hit on a non-read call is a category error — reject it.
    with pytest.raises(ValidationError):
        _record(call_role=CallRole.single, cache_hit=True)


def test_read_with_fresh_input_exceeding_cache_read_is_quarantined():
    # SPEC: a read must be "cache_read HIGH, input LOW". A degraded/partial read (prefix
    # drift sends most context as fresh input) has cache_read>0 but fails that contract.
    raw = copy.deepcopy(RAW_CACHE_READ)
    raw["cache_read_input_tokens"] = 100  # tiny cached portion
    raw["input_tokens"] = 5000  # most of the context came back as fresh input
    rec = _record(usage_raw=raw, call_role=CallRole.read, cache_hit=True, stop_reason="end_turn")
    assert rec.quarantined is True
    assert any("cache" in r.lower() for r in rec.quarantine_reasons)


# --------------------------------------------------- multi-turn capture


def test_turn_index_recorded_when_present():
    rec = _record(turn_index=3, call_role=CallRole.single)
    assert rec.turn_index == 3


def test_negative_turn_index_rejected():
    with pytest.raises(ValidationError):
        _record(turn_index=-1)


# --------------------------------------------------- fail-loud on unknown fields


def test_unknown_top_level_field_is_rejected():
    with pytest.raises(ValidationError):
        _record(undocumented_field="oops")


def test_quarantine_recomputed_on_reload_not_trusted_from_disk():
    # If a record on disk says quarantined=False but its stop_reason is max_tokens,
    # the contract recomputes the truth on load (the gate can't be bypassed by editing).
    rec = _record(stop_reason="max_tokens")
    payload = json.loads(rec.to_jsonl_line())
    payload["quarantined"] = False
    payload["quarantine_reasons"] = []
    back = CaptureRecord.model_validate(payload)
    assert back.quarantined is True
    assert back.quarantine_reasons  # non-empty
