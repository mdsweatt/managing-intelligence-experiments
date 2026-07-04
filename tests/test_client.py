"""Tests for harness.client — the streaming capture wrapper.

Drives the capture behaviour with the fake client (no API spend): the full usage
vector + provenance (request_id, rate-limit headers) is captured off a streamed call,
timing is measured, and the rate-limit headers are filtered from the noise.
"""

from __future__ import annotations

from types import SimpleNamespace

from harness.client import CallResult, extract_rate_limit_headers, stream_call

USAGE = {
    "input_tokens": 50,
    "output_tokens": 30,
    "cache_read_input_tokens": 0,
    "cache_creation_input_tokens": 0,
    "cache_creation": {"ephemeral_5m_input_tokens": 0, "ephemeral_1h_input_tokens": 0},
    "output_tokens_details": {"thinking_tokens": 0},
    "service_tier": "standard",
}
HEADERS = {
    "request-id": "req_live123",
    "anthropic-ratelimit-requests-remaining": "998",
    "anthropic-ratelimit-input-tokens-remaining": "449000",
    "content-type": "application/json",
    "cf-ray": "noise",
}


def test_extract_rate_limit_headers_keeps_only_relevant():
    out = extract_rate_limit_headers(HEADERS)
    assert out["anthropic-ratelimit-requests-remaining"] == "998"
    assert out["request-id"] == "req_live123"
    assert "content-type" not in out
    assert "cf-ray" not in out


def test_stream_call_captures_usage_and_provenance(fake_client, fake_clock):
    client = fake_client(
        [
            {
                "usage": USAGE,
                "stop_reason": "end_turn",
                "model": "claude-haiku-4-5-20251001",
                "request_id": "req_live123",
                "headers": HEADERS,
            }
        ]
    )
    result = stream_call(
        client,
        model="claude-haiku-4-5-20251001",
        max_tokens=64000,
        messages=[{"role": "user", "content": "hi"}],
        clock=fake_clock([0.0, 0.20, 0.85]),  # t0, t_enter (latency), t_done (wall)
    )
    assert isinstance(result, CallResult)
    assert result.usage_raw == USAGE  # verbatim
    assert result.stop_reason == "end_turn"
    assert result.model_version == "claude-haiku-4-5-20251001"
    assert result.request_id == "req_live123"
    assert result.rate_limit["anthropic-ratelimit-requests-remaining"] == "998"
    assert result.latency_ms == 200.0  # (0.20 - 0.0) * 1000
    assert result.wall_clock_s == 0.85  # 0.85 - 0.0


def test_stream_call_passes_system_and_extra_params(fake_client, fake_clock):
    client = fake_client([{"usage": USAGE}])
    stream_call(
        client,
        model="claude-sonnet-4-6",
        max_tokens=128000,
        messages=[{"role": "user", "content": "q"}],
        system=[{"type": "text", "text": "ctx", "cache_control": {"type": "ephemeral"}}],
        output_config={"effort": "high"},
        clock=fake_clock([0.0, 0.1, 0.2]),
    )
    sent = client.messages.calls[0]
    assert sent["model"] == "claude-sonnet-4-6"
    assert sent["max_tokens"] == 128000
    assert sent["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert sent["output_config"] == {"effort": "high"}


def test_stream_call_omits_system_when_none(fake_client, fake_clock):
    client = fake_client([{"usage": USAGE}])
    stream_call(
        client,
        model="m",
        max_tokens=10,
        messages=[{"role": "user", "content": "q"}],
        clock=fake_clock([0.0, 0.1, 0.2]),
    )
    assert "system" not in client.messages.calls[0]


def test_stream_call_recovers_output_tokens_details_from_message_delta(fake_client, fake_clock):
    """SDK 0.109.2's streaming accumulator drops output_tokens_details from the final
    snapshot (it copies every other usage field from message_delta but not this one), so a
    thinking call's final usage has output_tokens_details=null. The thinking-token count
    still rides on the message_delta event — stream_call must recover it from there."""
    delta = SimpleNamespace(
        type="message_delta",
        usage=SimpleNamespace(
            output_tokens_details=SimpleNamespace(model_dump=lambda: {"thinking_tokens": 222})
        ),
    )
    final_usage = {**USAGE, "output_tokens_details": None}  # the SDK bug: null on the final snapshot
    client = fake_client([{"usage": final_usage, "events": [delta]}])
    result = stream_call(
        client,
        model="claude-opus-4-8",
        max_tokens=128000,
        messages=[{"role": "user", "content": "think hard"}],
        thinking={"type": "adaptive"},
        clock=fake_clock([0.0, 0.1, 0.2]),
    )
    assert result.usage_raw["output_tokens_details"] == {"thinking_tokens": 222}
