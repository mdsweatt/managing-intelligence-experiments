import harness
from harness.config import load_run_matrix, load_manifest
from harness.expand import expand_matrix
from harness.guard import SpendGuard
from harness.run import build_snapshot, estimate_units, call_with_backoff
from harness.runner import RunWriter, new_run_id
from harness.run import run_units
from harness.run import run as run_orch
from harness.schema import CaptureRecord
from tests.test_run_multiturn import FakeClient as _BaseFakeClient


class FakeClient(_BaseFakeClient):
    """FakeClient extended to return output_tokens_details in usage_raw so
    thinking='adaptive' cells (e.g. task 16) pass the schema validator."""
    class _M:
        def __init__(self, outer): self._o = outer
        class _Stream:
            def __init__(self, text): self._t = text; self.request_id = "req_1"
            def __enter__(self):
                self.response = type("R", (), {"headers": {}})()
                return self
            def __exit__(self, *a): return False
            def __iter__(self): return iter(())   # real SDK stream is iterable
            def until_done(self): pass
            def get_final_message(self):
                class _Block:
                    def __init__(self, text): self.type, self.text = "text", text
                class _Msg:
                    def __init__(self, text):
                        self.content = [_Block(text)]
                        self.usage = type("U", (), {
                            "model_dump": lambda s: {
                                "input_tokens": 5, "output_tokens": 7,
                                "output_tokens_details": {"thinking_tokens": 0},
                            }
                        })()
                        self.stop_reason, self.model = "end_turn", "m-1"
                return _Msg(self._t)
        def stream(self, **kw): return FakeClient._M._Stream(self._o._t)
    @property
    def messages(self): return FakeClient._M(self)


def test_version_present():
    assert isinstance(harness.__version__, str) and harness.__version__


def test_snapshot_has_plan_and_provenance():
    rm = load_run_matrix("runs/phase1a.yaml")
    units = expand_matrix(rm, load_manifest("fixtures/manifest.yaml"))
    guard = SpendGuard(max_calls=9999, max_input_tokens=1, max_output_tokens=1)
    snap = build_snapshot(rm, units, guard, sdk_version="0.109.2",
                          matrix_path="runs/phase1a.yaml", manifest_path="fixtures/manifest.yaml",
                          run_id="run-x", skipped=[])
    assert snap["harness_version"] == harness.__version__
    assert snap["sdk_version"] == "0.109.2"
    assert snap["n_per_cell"] == rm.meta.n_per_cell
    assert len(snap["units"]) == len(units)
    assert snap["units"][0]["fixture_sha256"] == units[0].fixture.sha256
    assert snap["skipped_bands"] == []


def test_snapshot_records_skipped_bands():
    rm = load_run_matrix("runs/phase1a.yaml")
    units = expand_matrix(rm, load_manifest("fixtures/manifest.yaml"))
    guard = SpendGuard(max_calls=9999, max_input_tokens=1, max_output_tokens=1)
    snap = build_snapshot(rm, units, guard, sdk_version="0.109.2",
                          matrix_path="runs/phase1a.yaml", manifest_path="fixtures/manifest.yaml",
                          run_id="run-x", skipped=[(8, "L")])
    assert snap["skipped_bands"] == [[8, "L"]]


def test_estimate_counts_calls_and_input_tokens():
    rm = load_run_matrix("runs/phase1a.yaml")
    units = expand_matrix(rm, load_manifest("fixtures/manifest.yaml"))
    est = estimate_units(units)
    # standard unit: n calls. cache unit: 1 write + n reads. multiturn: n*turns. payload: n.
    assert est["total_calls"] > len(units)          # cache/multiturn multiply calls
    assert est["input_tokens_estimate"] > 0
    assert set(est["by_family"]) <= {"standard", "cache", "multiturn", "payload"}
    assert any("coarse" in note for note in est["notes"])


class _RL(Exception):
    pass


def test_backoff_retries_then_succeeds():
    sleeps = []
    calls = {"n": 0}
    def thunk():
        calls["n"] += 1
        if calls["n"] < 3:
            raise _RL()
        return "ok"
    out = call_with_backoff(thunk, base_delay=0.1, sleep=sleeps.append,
                            is_rate_limit=lambda e: isinstance(e, _RL))
    assert out == "ok" and calls["n"] == 3 and len(sleeps) == 2


def test_backoff_gives_up_after_max():
    import pytest
    with pytest.raises(_RL):
        call_with_backoff(lambda: (_ for _ in ()).throw(_RL()),
                          max_retries=2, base_delay=0.0, sleep=lambda s: None,
                          is_rate_limit=lambda e: isinstance(e, _RL))


def _frozen(units, files):
    """Freeze each unit's fixture against the fake file contents so the gate passes."""
    from harness.hashing import fixture_hash
    for u in units:
        p = files[u.fixture.files.prompt]
        i = files.get(u.fixture.files.input) if u.fixture.files.input else None
        object.__setattr__(u.fixture, "sha256", fixture_hash(p, i))
        object.__setattr__(u.fixture, "frozen", True)

def test_run_units_writes_records_per_family(tmp_path):
    rm = load_run_matrix("runs/phase1a.yaml")
    units = expand_matrix(rm, load_manifest("fixtures/manifest.yaml"))
    # pick one of each family for a fast loop
    pick = {}
    for u in units:
        pick.setdefault(u.family, u)
    units = list(pick.values())
    files = {}   # synth file contents keyed by the fixtures' relative paths
    for u in units:
        files[u.fixture.files.prompt] = "Q one\n===TURN===\nQ two" if u.family == "multiturn" else "do it"
        if u.fixture.files.input:
            files[u.fixture.files.input] = "CONTEXT BODY"
    _frozen(units, files)
    writer = RunWriter(tmp_path, new_run_id(token="loop"))
    guard = SpendGuard(max_calls=100000, max_input_tokens=10**9, max_output_tokens=10**9)
    written = run_units(units, client=FakeClient("ok"), guard=guard, writer=writer,
                        read_file=lambda p: files[p], counter=lambda m, t: 3,
                        sdk_version="0.109.2", models=rm.models, clock=lambda: 0.0)
    lines = writer.records_path.read_text().strip().splitlines()
    assert len(lines) == written
    recs = [CaptureRecord.from_jsonl_line(l) for l in lines]
    assert any(r.call_role.value == "write" for r in recs)   # cache family ran a warm-write
    assert any(r.turn_index == 1 for r in recs)              # multiturn produced >1 turn


def test_dry_run_returns_estimate_without_client(tmp_path):
    out = run_orch(matrix_path="runs/phase1a.yaml", manifest_path="fixtures/manifest.yaml",
                   fixtures_root="fixtures", out_root=str(tmp_path),
                   dry_run=True, usd_prior=None, limit=None, client=None)
    assert out["mode"] == "dry_run"
    assert out["estimate"]["total_calls"] > 0
    assert "skipped_bands" in out          # deferred bands surfaced even on a dry run
    # dry-run must NOT require a client and must NOT write records
    assert not list(tmp_path.glob("*/records.jsonl"))


def test_module_main_reaches_run_units_without_nameerror(tmp_path):
    """`python -m harness.run` (real-run path) must reach run_units bound.

    Regression for a definition-order bug: run_units was defined AFTER the
    `if __name__ == "__main__"` guard, so under __main__ execution main()->run()
    referenced it before it was bound -> NameError. Import-time tests never hit
    this (the guard is skipped on import) and the only run() test used --dry-run
    (returns before the run_units reference). We drive the real-run branch with
    --limit 0 so it reaches the run_units call but makes ZERO API calls, and a
    dummy key so the offline client constructs. After the fix: exit 0.
    """
    import os
    import subprocess
    import sys

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env = {**os.environ, "ANTHROPIC_API_KEY": "sk-ant-dummy-for-offline-construct"}
    proc = subprocess.run(
        [sys.executable, "-m", "harness.run",
         "--matrix", "runs/phase0.yaml", "--usd-prior", "150",
         "--limit", "0", "--out", str(tmp_path)],
        cwd=repo_root, env=env, capture_output=True, text=True,
    )
    assert "run_units" not in proc.stderr, proc.stderr   # the NameError names it
    assert proc.returncode == 0, f"stdout={proc.stdout}\nstderr={proc.stderr}"
