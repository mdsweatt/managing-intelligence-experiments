"""Shared test fixtures — a fake Anthropic client that mimics the streaming surface
(`client.messages.stream(...) -> context manager` exposing `until_done`,
`get_final_message`, `request_id`, `response.headers`), so the runner/client/guard
can be unit-tested with zero API spend. The live end-to-end proof lives separately."""

from __future__ import annotations

from types import SimpleNamespace

import pytest


class _FakeUsage:
    def __init__(self, d: dict):
        self._d = dict(d)

    def model_dump(self) -> dict:
        return dict(self._d)


class _FakeFinalMessage:
    def __init__(self, usage: dict, stop_reason: str, model: str):
        self.usage = _FakeUsage(usage)
        self.stop_reason = stop_reason
        self.model = model


class _FakeStream:
    """Mimics anthropic's MessageStream context manager. Iterating it yields the scripted
    ``events`` (the real SDK stream is iterable); if ``raise_in`` is set, the exception is
    raised on iteration to simulate a mid-stream failure (where the real SDK raises)."""

    def __init__(self, final: _FakeFinalMessage, request_id: str, headers: dict,
                 raise_in=None, events=()):
        self._final = final
        self._rid = request_id
        self._headers = headers
        self._raise_in = raise_in
        self._events = list(events)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False  # does not suppress — matches the SDK

    def __iter__(self):
        if self._raise_in is not None:
            raise self._raise_in
        yield from self._events

    def until_done(self):
        if self._raise_in is not None:
            raise self._raise_in
        return None

    def get_final_message(self):
        return self._final

    @property
    def request_id(self):
        return self._rid

    @property
    def response(self):
        return SimpleNamespace(headers=self._headers)


class _FakeMessages:
    def __init__(self, responses: list[dict]):
        self._responses = list(responses)
        self.calls: list[dict] = []  # records kwargs of each stream() call for assertions

    def stream(self, **kwargs):
        self.calls.append(kwargs)
        if not self._responses:
            raise AssertionError("FakeClient ran out of scripted responses")
        spec = self._responses.pop(0)
        return _FakeStream(
            _FakeFinalMessage(
                spec.get("usage", {"input_tokens": 1, "output_tokens": 1}),
                spec.get("stop_reason", "end_turn"),
                spec.get("model", "fake-model"),
            ),
            spec.get("request_id", "req_fake"),
            spec.get("headers", {}),
            raise_in=spec.get("raise"),
            events=spec.get("events", ()),
        )


class FakeClient:
    """Stand-in for anthropic.Anthropic with a scripted sequence of stream responses."""

    def __init__(self, responses: list[dict]):
        self.messages = _FakeMessages(responses)


@pytest.fixture
def fake_client():
    def _make(responses: list[dict]) -> FakeClient:
        return FakeClient(responses)

    return _make


@pytest.fixture
def fake_clock():
    """A deterministic monotonic clock: returns the supplied values in order."""

    def _make(values: list[float]):
        seq = iter(values)
        return lambda: next(seq)

    return _make
