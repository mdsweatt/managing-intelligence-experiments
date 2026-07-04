import pytest
from harness.schema import CallConfig, CellId
from harness.config import FixtureEntry
from harness.expand import RunUnit
from harness.assemble import assemble, FixtureNotFrozen, FixtureHashMismatch
from harness.hashing import fixture_hash

FILES = {
    "t/p.txt": "Draft an email.",
    "t/in.md": "Vendor missed delivery.",
}
def reader(path): return FILES[path]

def _unit(family="standard", frozen=True, sha=None, inp="t/in.md"):
    files = {"prompt": "t/p.txt"}
    if inp: files["input"] = inp
    sha = sha if sha is not None else fixture_hash(FILES["t/p.txt"], FILES.get(inp) if inp else None)
    fx = FixtureEntry(task_id=1, band="S", cost_axis="input",
                      proxy={"type": "words", "value": 3},
                      files=files, recorded_token_counts={"tok_hs": 10, "tok_opus": 14},
                      sha256=sha, frozen=frozen)
    cfg = CallConfig(model_role="haiku", model_id="m", band="S", max_tokens=64000)
    cell = CellId(task_id=1, task_name="draft_email", band="S",
                  model_role="haiku", model_id="m", role_label="hypothesis")
    return RunUnit(cell_id=cell, config=cfg, role_label="hypothesis", family=family, fixture=fx, n=20)

def test_standard_joins_prompt_and_input():
    plan = assemble(_unit(), reader)
    assert plan.messages == [{"role": "user", "content": "Draft an email.\n\nVendor missed delivery."}]
    assert plan.system is None and plan.call_role_is_single()

def test_standard_prompt_only_when_no_input():
    plan = assemble(_unit(inp=None), reader)
    assert plan.messages == [{"role": "user", "content": "Draft an email."}]

def test_frozen_gate_refuses_unfrozen():
    with pytest.raises(FixtureNotFrozen):
        assemble(_unit(frozen=False, sha="TBD"), reader)

def test_frozen_gate_refuses_hash_mismatch():
    with pytest.raises(FixtureHashMismatch):
        assemble(_unit(sha="0" * 64), reader)

def test_dry_run_skips_frozen_gate():
    plan = assemble(_unit(frozen=False, sha="TBD"), reader, require_frozen=False)
    assert plan.messages is not None

def test_cache_puts_input_in_cached_system_and_prompt_in_read():
    plan = assemble(_unit(family="cache"), reader)
    assert plan.system == [{"type": "text", "text": "Vendor missed delivery.",
                            "cache_control": {"type": "ephemeral"}}]
    assert plan.read_messages == [{"role": "user", "content": "Draft an email."}]
    assert plan.warm_message == {"role": "user", "content": "Reply only: ready."}

def test_multiturn_splits_on_delimiter_and_prepends_input_to_turn1():
    FILES["t/turns.txt"] = "First question.\n===TURN===\nSecond question."
    u = _unit(family="multiturn")
    u.fixture.files.prompt = "t/turns.txt"  # FixtureFiles is mutable enough for the test
    # recompute the stored hash for the new content
    u2 = _unit(family="multiturn", sha=fixture_hash(FILES["t/turns.txt"], FILES["t/in.md"]))
    u2.fixture.files.prompt = "t/turns.txt"
    plan = assemble(u2, reader)
    assert plan.turns == ["Vendor missed delivery.\n\nFirst question.", "Second question."]

def test_payload_builds_tool_result_history():
    plan = assemble(_unit(family="payload"), reader)
    assert plan.tools and plan.tools[0]["name"] == "provide_payload"
    roles = [m["role"] for m in plan.messages]
    assert roles == ["user", "assistant", "user"]
    assert plan.messages[1]["content"][0]["type"] == "tool_use"
    tr = plan.messages[2]["content"][0]
    assert tr["type"] == "tool_result" and tr["content"] == "Vendor missed delivery."
    assert plan.tool_result_tokens is None   # filled by run.py from a free count_tokens
