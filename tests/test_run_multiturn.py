# tests/test_run_multiturn.py
from harness.client import stream_call

class _Block:
    def __init__(self, text): self.type, self.text = "text", text
class _Msg:
    def __init__(self, text):
        self.content = [_Block(text)]
        self.usage = type("U", (), {"model_dump": lambda s: {"input_tokens": 5, "output_tokens": 7}})()
        self.stop_reason, self.model = "end_turn", "m-1"
class _Stream:
    def __init__(self, text): self._t = text; self.request_id = "req_1"
        # response.headers
    def __enter__(self): self.response = type("R", (), {"headers": {}})(); return self
    def __exit__(self, *a): return False
    def __iter__(self): return iter(())     # real SDK stream is iterable; no thinking deltas here
    def until_done(self): pass
    def get_final_message(self): return _Msg(self._t)
class FakeClient:
    def __init__(self, text): self._t = text
    class _M:
        def __init__(self, outer): self._o = outer
        def stream(self, **kw): return _Stream(self._o._t)
    @property
    def messages(self): return FakeClient._M(self)

def test_stream_call_captures_response_text():
    r = stream_call(FakeClient("hello world"), model="m", max_tokens=10,
                    messages=[{"role": "user", "content": "hi"}], clock=lambda: 0.0)
    assert r.response_text == "hello world"


from harness.guard import SpendGuard
from harness.runner import RunWriter, new_run_id, run_multiturn_session
from harness.schema import CallConfig, CellId

def test_multiturn_one_record_per_turn_with_index(tmp_path):
    writer = RunWriter(tmp_path, new_run_id(token="mt"))
    guard = SpendGuard(max_calls=10, max_input_tokens=10_000, max_output_tokens=10_000)
    cfg = CallConfig(model_role="sonnet", model_id="m", band="few", effort="high", max_tokens=128000)
    cell = CellId(task_id=17, task_name="iterative_refine", band="few",
                  model_role="sonnet", model_id="m", role_label="hypothesis")
    recs = run_multiturn_session(
        client=FakeClient("ok"), guard=guard, writer=writer, cell_id=cell, config=cfg,
        fixture_hash="a" * 64, tokenizer_version="tok-hs", sdk_version="0.109.2",
        turns=["turn one", "turn two", "turn three"], clock=lambda: 0.0,
    )
    assert [r.turn_index for r in recs] == [0, 1, 2]
    assert guard.calls == 3
