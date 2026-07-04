"""Tests for harness.runner — the cell-execution skeleton.

Ties the streaming client, the spend guard, and the Phase 1 capture contract together:
guard-check → stream → build+validate a CaptureRecord (capture → hash) → register spend →
append to results/<run-id>/records.jsonl. Plus the warm-once-read-many cache path with its
cache-hit assertion. All driven by the fake client (no API spend).
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from harness.config import config_hash
from harness.guard import CeilingBreach, SpendGuard
from harness.runner import (
    RunWriter,
    config_to_call_params,
    execute_call,
    new_run_id,
    warm_once_read_many,
)
from harness.schema import CallConfig, CallRole, CaptureRecord, CellId

SONNET = "claude-sonnet-4-6"


def _cfg(**over) -> CallConfig:
    base = dict(
        model_role="sonnet",
        model_id=SONNET,
        band="M",
        effort="high",
        thinking="off",
        max_tokens=128000,
    )
    base.update(over)
    return CallConfig(**base)


def _cell(role_label="hypothesis", **over) -> CellId:
    base = dict(
        task_id=10,
        task_name="support_vs_kb",
        band="M",
        model_role="sonnet",
        model_id=SONNET,
        role_label=role_label,
    )
    base.update(over)
    return CellId(**base)


def _usage(inp=40, out=120, cache_read=0, cache_create=0):
    return {
        "input_tokens": inp,
        "output_tokens": out,
        "cache_read_input_tokens": cache_read,
        "cache_creation_input_tokens": cache_create,
        "cache_creation": {
            "ephemeral_5m_input_tokens": cache_create,
            "ephemeral_1h_input_tokens": 0,
        },
        "output_tokens_details": {"thinking_tokens": 0},
        "service_tier": "standard",
    }


def _resp(usage, **over):
    return {
        "usage": usage,
        "stop_reason": "end_turn",
        "model": SONNET,
        "request_id": "req_x",
        "headers": {"request-id": "req_x"},
        **over,
    }


_CLOCK = [0.0, 0.1, 0.3, 10.0, 10.1, 10.3, 20.0, 20.1, 20.3]  # enough ticks for a few calls


def _common(writer, guard):
    return dict(
        client=None,
        guard=guard,
        writer=writer,
        config=_cfg(),
        cell_id=_cell(),
        fixture_hash="a" * 64,
        tokenizer_version="tok-hs",
        sdk_version="0.109.2",
    )


# ----------------------------------------------------------------- run id + writer


def test_new_run_id_is_deterministic_with_injected_inputs():
    rid = new_run_id(
        now=dt.datetime(2026, 6, 17, 14, 30, 5, tzinfo=dt.timezone.utc), token="abc123"
    )
    assert rid == "run-20260617T143005Z-abc123"


def test_run_writer_creates_dir_and_round_trips_records(tmp_path, fake_client):
    writer = RunWriter(tmp_path, "run-test")
    guard = SpendGuard(max_calls=10)
    client = fake_client([_resp(_usage()), _resp(_usage(inp=99))])
    execute_call(
        **{
            **_common(writer, guard),
            "client": client,
            "messages": [{"role": "user", "content": "q1"}],
            "call_role": CallRole.single,
        }
    )
    execute_call(
        **{
            **_common(writer, guard),
            "client": client,
            "messages": [{"role": "user", "content": "q2"}],
            "call_role": CallRole.single,
        }
    )
    lines = (Path(writer.path) / "records.jsonl").read_text().strip().splitlines()
    assert len(lines) == 2
    recs = [CaptureRecord.from_jsonl_line(ln) for ln in lines]
    assert recs[0].usage.input_tokens == 40 and recs[1].usage.input_tokens == 99


def test_run_writer_writes_snapshot(tmp_path):
    import yaml

    writer = RunWriter(tmp_path, "run-test")
    writer.write_snapshot({"matrix": "expanded", "ceiling_usd": 500})
    data = yaml.safe_load((Path(writer.path) / "config-snapshot.yaml").read_text())
    assert data["ceiling_usd"] == 500


# ----------------------------------------------------------------- execute_call


def test_execute_call_builds_validated_record_and_registers_spend(tmp_path, fake_client):
    writer = RunWriter(tmp_path, "run-test")
    guard = SpendGuard(max_calls=10)
    client = fake_client([_resp(_usage(inp=40, out=120))])
    rec = execute_call(
        **{
            **_common(writer, guard),
            "client": client,
            "messages": [{"role": "user", "content": "q"}],
            "call_role": CallRole.single,
        }
    )
    assert isinstance(rec, CaptureRecord)
    assert rec.quarantined is False
    assert rec.config_hash == config_hash(_cfg(), tokenizer_version="tok-hs")
    assert guard.calls == 1 and guard.input_tokens == 40 and guard.output_tokens == 120


def test_execute_call_checks_guard_before_calling(tmp_path, fake_client):
    writer = RunWriter(tmp_path, "run-test")
    guard = SpendGuard(max_calls=1)
    guard.calls = 1  # ceiling already spent
    client = fake_client([_resp(_usage())])
    with pytest.raises(CeilingBreach):
        execute_call(
            **{
                **_common(writer, guard),
                "client": client,
                "messages": [{"role": "user", "content": "q"}],
                "call_role": CallRole.single,
            }
        )
    assert client.messages.calls == []  # no API call was attempted


def test_execute_call_records_the_breaching_call_then_aborts(tmp_path, fake_client):
    writer = RunWriter(tmp_path, "run-test")
    guard = SpendGuard(max_calls=10, max_input_tokens=50)
    client = fake_client([_resp(_usage(inp=100))])
    with pytest.raises(CeilingBreach):
        execute_call(
            **{
                **_common(writer, guard),
                "client": client,
                "messages": [{"role": "user", "content": "q"}],
                "call_role": CallRole.single,
            }
        )
    # The breaching call's data is still captured (it was really spent).
    lines = (Path(writer.path) / "records.jsonl").read_text().strip().splitlines()
    assert len(lines) == 1


# ----------------------------------------------------------------- cache warm-once-read-many


def test_warm_once_read_many_writes_write_then_reads_with_hits(tmp_path, fake_client):
    writer = RunWriter(tmp_path, "run-test")
    guard = SpendGuard(max_calls=10)
    client = fake_client(
        [
            _resp(_usage(inp=9, out=5, cache_create=2000)),  # warm write
            _resp(_usage(inp=12, out=80, cache_read=2000)),  # read 1 (hit)
            _resp(_usage(inp=15, out=90, cache_read=2000)),  # read 2 (hit)
        ]
    )
    write_rec, read_recs = warm_once_read_many(
        client=client,
        guard=guard,
        writer=writer,
        config=_cfg(),
        cell_id=_cell(),
        fixture_hash="a" * 64,
        tokenizer_version="tok-hs",
        sdk_version="0.109.2",
        cached_system=[{"type": "text", "text": "KB", "cache_control": {"type": "ephemeral"}}],
        warm_message={"role": "user", "content": "warm"},
        read_messages=[{"role": "user", "content": "q1"}, {"role": "user", "content": "q2"}],
    )
    assert write_rec.call_role is CallRole.write and write_rec.quarantined is False
    assert len(read_recs) == 2
    for r in read_recs:
        assert r.call_role is CallRole.read and r.cache_hit is True and r.quarantined is False
    lines = (Path(writer.path) / "records.jsonl").read_text().strip().splitlines()
    assert len(lines) == 3


def test_warm_once_read_many_flags_a_cache_miss(tmp_path, fake_client):
    writer = RunWriter(tmp_path, "run-test")
    guard = SpendGuard(max_calls=10)
    client = fake_client(
        [
            _resp(_usage(inp=9, out=5, cache_create=2000)),  # warm write
            _resp(_usage(inp=2000, out=80, cache_read=0)),  # read came back as fresh input
        ]
    )
    _, read_recs = warm_once_read_many(
        client=client,
        guard=guard,
        writer=writer,
        config=_cfg(),
        cell_id=_cell(),
        fixture_hash="a" * 64,
        tokenizer_version="tok-hs",
        sdk_version="0.109.2",
        cached_system=[{"type": "text", "text": "KB", "cache_control": {"type": "ephemeral"}}],
        warm_message={"role": "user", "content": "warm"},
        read_messages=[{"role": "user", "content": "q1"}],
    )
    assert read_recs[0].cache_hit is False
    assert read_recs[0].quarantined is True


def test_warm_once_read_many_wraps_each_call_independently(tmp_path, fake_client):
    """call_wrapper must be invoked once per inner execute_call (1 write + N reads),
    not once around the whole sequence. Default identity wrapper = unchanged behavior."""
    writer = RunWriter(tmp_path, "run-test")
    guard = SpendGuard(max_calls=10)
    client = fake_client(
        [
            _resp(_usage(inp=9, out=5, cache_create=2000)),   # warm write
            _resp(_usage(inp=12, out=80, cache_read=2000)),   # read 1
            _resp(_usage(inp=15, out=90, cache_read=2000)),   # read 2
        ]
    )
    calls = {"n": 0}

    def counting_wrapper(thunk):
        calls["n"] += 1
        return thunk()

    write_rec, read_recs = warm_once_read_many(
        client=client,
        guard=guard,
        writer=writer,
        config=_cfg(),
        cell_id=_cell(),
        fixture_hash="a" * 64,
        tokenizer_version="tok-hs",
        sdk_version="0.109.2",
        cached_system=[{"type": "text", "text": "KB", "cache_control": {"type": "ephemeral"}}],
        warm_message={"role": "user", "content": "warm"},
        read_messages=[{"role": "user", "content": "q1"}, {"role": "user", "content": "q2"}],
        call_wrapper=counting_wrapper,
    )
    # wrapper must have been called once for the write and once per read: 1 + 2 = 3
    assert calls["n"] == 3
    assert write_rec.call_role is CallRole.write
    assert len(read_recs) == 2


# ----------------------------------------------------------------- config → API params


def test_config_to_call_params_haiku_is_minimal():
    cfg = CallConfig(
        model_role="haiku",
        model_id="claude-haiku-4-5-20251001",
        band="S",
        effort=None,
        thinking="off",
        max_tokens=64000,
    )
    # Haiku has no effort knob, thinking off, temperature omitted → no extra params.
    assert config_to_call_params(cfg) == {}


def test_config_to_call_params_maps_effort_and_thinking():
    cfg = CallConfig(
        model_role="opus",
        model_id="claude-opus-4-8",
        band="low",
        effort="low",
        thinking="adaptive",
        max_tokens=128000,
    )
    params = config_to_call_params(cfg)
    assert params["output_config"] == {"effort": "low"}
    assert params["thinking"] == {"type": "adaptive"}
    assert "temperature" not in params  # never sent (constitution)


def test_execute_call_applies_config_effort_to_the_api_call(tmp_path, fake_client):
    writer = RunWriter(tmp_path, "run-test")
    guard = SpendGuard(max_calls=10)
    client = fake_client([_resp(_usage())])
    execute_call(
        client=client,
        guard=guard,
        writer=writer,
        config=_cfg(effort="high"),
        cell_id=_cell(),
        fixture_hash="a" * 64,
        tokenizer_version="tok-hs",
        sdk_version="0.109.2",
        messages=[{"role": "user", "content": "q"}],
        call_role=CallRole.single,
    )
    assert client.messages.calls[0]["output_config"] == {"effort": "high"}


def test_config_to_call_params_rejects_enabled_thinking_without_budget():
    # 'enabled' thinking requires budget_tokens; emitting {type:'enabled'} alone 400s.
    cfg = CallConfig(
        model_role="haiku",
        model_id="claude-haiku-4-5-20251001",
        band="S",
        effort=None,
        thinking="enabled",
        max_tokens=64000,
    )
    with pytest.raises(ValueError):
        config_to_call_params(cfg)


# ----------------------------------------------------------------- spend safety on failure


def test_attempt_is_counted_even_when_the_stream_fails(tmp_path, fake_client):
    # A mid-stream failure must still advance the call ceiling (else a failing loop is
    # unbounded) — but it writes no record and counts no tokens (none were captured).
    writer = RunWriter(tmp_path, "run-test")
    guard = SpendGuard(max_calls=10)
    client = fake_client([{"raise": RuntimeError("connection dropped mid-stream")}])
    with pytest.raises(RuntimeError):
        execute_call(
            **{
                **_common(writer, guard),
                "client": client,
                "messages": [{"role": "user", "content": "q"}],
                "call_role": CallRole.single,
            }
        )
    assert guard.calls == 1  # the attempt was counted
    assert guard.input_tokens == 0 and guard.output_tokens == 0
    records = Path(writer.path) / "records.jsonl"
    assert (not records.exists()) or records.read_text() == ""


def test_failing_loop_trips_the_call_ceiling(tmp_path, fake_client):
    writer = RunWriter(tmp_path, "run-test")
    guard = SpendGuard(max_calls=2)
    client = fake_client([{"raise": RuntimeError("boom")} for _ in range(5)])
    for _ in range(2):
        with pytest.raises(RuntimeError):
            execute_call(
                **{
                    **_common(writer, guard),
                    "client": client,
                    "messages": [{"role": "user", "content": "q"}],
                    "call_role": CallRole.single,
                }
            )
    with pytest.raises(CeilingBreach):  # third attempt blocked before any API call
        execute_call(
            **{
                **_common(writer, guard),
                "client": client,
                "messages": [{"role": "user", "content": "q"}],
                "call_role": CallRole.single,
            }
        )


def test_spend_is_registered_even_if_append_fails(tmp_path, fake_client):
    # If persistence fails AFTER the call was billed, the spend must still reach the guard
    # (else a retrying supervisor overspends while the guard reads zero).
    class FailingWriter(RunWriter):
        def append(self, record):
            raise IOError("disk full")

    writer = FailingWriter(tmp_path, "run-test")
    guard = SpendGuard(max_calls=10)
    client = fake_client([_resp(_usage(inp=40, out=120))])
    with pytest.raises(IOError):
        execute_call(
            **{
                **_common(writer, guard),
                "client": client,
                "messages": [{"role": "user", "content": "q"}],
                "call_role": CallRole.single,
            }
        )
    assert guard.calls == 1
    assert guard.input_tokens == 40 and guard.output_tokens == 120  # spend still counted
