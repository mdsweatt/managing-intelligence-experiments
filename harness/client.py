"""harness/client.py — the streaming capture wrapper (Experiment 1, Phase 2).

One job: make a single Anthropic call and capture *exactly* what it returned — the full
``usage`` object verbatim plus provenance (``request_id``, rate-limit headers) and timing —
without interpreting or estimating anything. The typed record is assembled downstream from
this raw capture (harness.schema).

Why streaming (verified 2026-06-16): every cell runs ``max_tokens`` = the model output
ceiling (64k–128k), and a non-streaming call with a ceiling that high trips the SDK's
long-request timeout guard. Streaming every call sidesteps that and keeps capture uniform.
Headers and request-id come off ``stream.response`` / ``stream.request_id`` (SDK 0.109.2).

Caveat (SDK 0.109.2): the streamed final snapshot does NOT match the non-streamed ``usage``
shape — ``accumulate_event`` (anthropic/lib/streaming/_messages.py) copies every usage field
from the ``message_delta`` event EXCEPT ``output_tokens_details``, so a thinking call's final
usage carries ``output_tokens_details: null`` and the thinking-token count is lost. We iterate
the events ourselves and recover it from the ``message_delta`` (where the count still rides).
"""

from __future__ import annotations

import time
from typing import Any, Callable, Optional

from pydantic import BaseModel, ConfigDict, Field


def extract_rate_limit_headers(headers: dict[str, str]) -> dict[str, str]:
    """Keep the provenance headers worth storing (rate-limit state + request-id); drop the
    transport noise. Reconstructs throttling after the fact and pins the exact call."""
    out: dict[str, str] = {}
    for k, v in headers.items():
        kl = k.lower()
        if "ratelimit" in kl or kl == "request-id":
            out[kl] = v
    return out


class CallResult(BaseModel):
    """The raw capture of one streamed call — handed to ``CaptureRecord.from_capture``."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    usage_raw: dict[str, Any]  # the API usage object, verbatim
    stop_reason: Optional[str]
    model_version: str  # the model the API actually served (final_message.model)
    request_id: Optional[str]
    rate_limit: dict[str, str]
    # Wall time from request start to response headers, INCLUDING any transparent SDK retries
    # + backoff sleeps (default max_retries=2) — an upper bound on a single-attempt RTT, not a
    # clean round-trip. A diagnostic, not a measurement input.
    latency_ms: float = Field(ge=0)
    wall_clock_s: float = Field(ge=0)  # request start → stream fully drained (incl. retries)
    response_text: Optional[str] = None  # accumulated assistant text; transient, not stored in records


def stream_call(
    client: Any,
    *,
    model: str,
    max_tokens: int,
    messages: list[dict[str, Any]],
    system: Optional[Any] = None,
    clock: Callable[[], float] = time.perf_counter,
    **params: Any,
) -> CallResult:
    """Stream one call and capture the full usage vector + provenance + timing.

    ``params`` passes through call options (``output_config`` for effort, ``thinking``,
    ``service_tier``, …). ``clock`` is injectable for deterministic timing in tests.
    """
    call_kwargs: dict[str, Any] = dict(model=model, max_tokens=max_tokens, messages=messages)
    if system is not None:
        call_kwargs["system"] = system
    call_kwargs.update(params)

    t0 = clock()
    thinking_details: Any = None  # output_tokens_details off the message_delta (SDK drops it)
    with client.messages.stream(**call_kwargs) as stream:
        t_response = clock()  # response object (with headers) is available once entered
        for event in stream:  # iterating drains the stream AND lets us see what the snapshot loses
            if getattr(event, "type", None) == "message_delta":
                usage = getattr(event, "usage", None)
                details = getattr(usage, "output_tokens_details", None) if usage is not None else None
                if details is not None:
                    thinking_details = details  # last message_delta wins (cumulative final usage)
        final = stream.get_final_message()
        request_id = stream.request_id
        headers = dict(stream.response.headers)
        t_done = clock()

    usage_raw = final.usage.model_dump()
    # Recover output_tokens_details the SDK's stream accumulator discarded (see module docstring).
    if usage_raw.get("output_tokens_details") is None and thinking_details is not None:
        usage_raw["output_tokens_details"] = (
            thinking_details.model_dump() if hasattr(thinking_details, "model_dump")
            else dict(thinking_details)
        )

    text = "".join(
        getattr(b, "text", "") for b in (getattr(final, "content", None) or []) if getattr(b, "type", None) == "text"
    )
    return CallResult(
        usage_raw=usage_raw,
        stop_reason=final.stop_reason,
        model_version=final.model,
        request_id=request_id,
        rate_limit=extract_rate_limit_headers(headers),
        latency_ms=(t_response - t0) * 1000.0,
        wall_clock_s=(t_done - t0),
        response_text=text,
    )
