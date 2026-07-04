# tests/test_run_payload.py
from harness.guard import SpendGuard
from harness.runner import RunWriter, new_run_id, execute_payload_call
from harness.schema import CallConfig, CellId
from tests.test_run_multiturn import FakeClient

def test_payload_call_records_tool_result_tokens(tmp_path):
    writer = RunWriter(tmp_path, new_run_id(token="pl"))
    guard = SpendGuard(max_calls=5, max_input_tokens=10_000, max_output_tokens=10_000)
    cfg = CallConfig(model_role="sonnet", model_id="m", band="M", effort="high", max_tokens=128000)
    cell = CellId(task_id=18, task_name="analyze_dataset", band="M",
                  model_role="sonnet", model_id="m", role_label="hypothesis")
    rec = execute_payload_call(
        client=FakeClient("done"), guard=guard, writer=writer, cell_id=cell, config=cfg,
        fixture_hash="b" * 64, tokenizer_version="tok-hs", sdk_version="0.109.2",
        messages=[{"role": "user", "content": "analyze"}],
        tools=[{"name": "provide_payload", "description": "d", "input_schema": {"type": "object", "properties": {}}}],
        tool_result_tokens=3, clock=lambda: 0.0,
    )
    assert rec.tool_result_tokens == 3 and guard.calls == 1
