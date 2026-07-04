"""Tests for analysis/judge_gemini_batch.py — the Batch-API transport for the FROZEN 1d judge.

The interactive path died on the Tier-1 250-requests/day quota (2026-07-02), so the judge runs as
Gemini Batch jobs instead. The instrument (model, prompts, thinking_budget, temperature, parser,
K-majority) is byte-identical; ONLY the transport changes. The design is record -> batch -> replay
around an UNTOUCHED quality.analyse():

  pass 1: HybridJudge(empty store) records every rubric prompt (dummy verdicts fail all gates, so
          no pairwise prompts render);
  batch:  prompts -> InlinedRequest chunks under the enqueued-token cap -> submit/poll/fetch;
  pass 2: HybridJudge(rubric store) replays real rubric verdicts, records the TRUE pairwise set;
  pass 3: HybridJudge(full store, strict) replays everything -> the real analyse() output.

Everything here is synthetic and zero-spend; the live batch surface is exercised by the paid smoke
at submission time. The equivalence test is the contract: batch replay == interactive, verdict for
verdict.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from analysis import judge_gemini_batch as jb
from analysis import quality as q

# --------------------------------------------------------------------------- shared synthetic fixture

RUBRIC_T = "RUBRIC {{SOURCE_MATERIAL}} {{TASK_INSTRUCTION}} {{CHECKS}} {{RESPONSE}}"
PAIR_T = "PAIRWISE {{SOURCE_MATERIAL}} {{TASK_INSTRUCTION}} {{RESPONSE_A}} {{RESPONSE_B}}"

RUBRIC_24 = {"pairwise": True,
             "code_checks": [{"id": "words", "type": "word_max", "max": 1000}],
             "checks": [{"id": "faithful", "type": "binary", "text": "no invention", "gate": True},
                        {"id": "depth", "type": "graded", "scores": [0, 1, 2], "text": "depth"}]}

JUDGE = {"rubrics": {"24": RUBRIC_24}, "margin_pp": 10, "k": 3,
         "prompt_text": {"rubric": RUBRIC_T, "pairwise": PAIR_T}}
MATERIAL = {24: {"source_material": "src", "task_instruction": "task"}}


def _cells(n=2):
    """n matched haiku/opus records with distinct texts (distinct rubric prompts per record)."""
    return {(24, "haiku", "off"): [{"response_text": f"haiku out {i}"} for i in range(n)],
            (24, "opus", "off"): [{"response_text": f"opus out {i}"} for i in range(n)]}


def _scripted(prompt: str, rep: int) -> dict:
    """Deterministic verdict script keyed by (prompt, replicate) — varies across replicates on one
    prompt so majority/agreement logic is actually exercised."""
    if prompt.startswith("PAIRWISE"):
        return {"preference": ["A", "A", "TIE"][rep]}
    depth = 2 if "haiku" in prompt else 1
    faithful = "pass" if rep < 2 else "fail"          # 2/3 majority pass
    return {"faithful": faithful, "depth": depth}


def _interactive_judge():
    """The scripted verdicts served the way the interactive path would: k successive calls with the
    same prompt get replicates 0,1,2."""
    seen: dict[str, int] = {}

    def fn(prompt: str) -> dict:
        rep = seen.get(prompt, 0)
        seen[prompt] = rep + 1
        return _scripted(prompt, rep)

    return fn


# --------------------------------------------------------------------------- HybridJudge: recording

def test_recording_judge_dummy_survives_rubric_and_pairwise_callers():
    rj = jb.HybridJudge({})
    out = q.judge_rubric_item(rj, RUBRIC_T, source="s", task="t",
                              checks=RUBRIC_24["checks"], response="r", k=3)
    assert out["faithful"]["verdict"] == "fail"          # dummy fails binary checks (gates stay shut)
    assert isinstance(out["depth"]["verdict"], int)      # graded coercion must not raise
    v = q.judge_pair(rj, PAIR_T, source="s", task="t", resp_haiku="h", resp_opus="o",
                     a_is_haiku=True, k=3)
    assert v["winner"] in {"haiku", "opus", "tie"}       # discarded, but must not raise


def test_recording_judge_counts_prompt_multiplicity():
    rj = jb.HybridJudge({})
    q.judge_rubric_item(rj, RUBRIC_T, source="s", task="t",
                        checks=RUBRIC_24["checks"], response="r", k=3)
    assert len(rj.recorded) == 1
    (_, prompt, count), = rj.recorded_items()
    assert prompt.startswith("RUBRIC") and count == 3


def test_pass1_collects_rubric_prompts_and_no_pairwise():
    prompts = jb.collect_rubric_prompts(_cells(), JUDGE, MATERIAL, k=3, seed="s")
    assert len(prompts) == 4                             # 4 records -> 4 distinct rubric prompts
    assert all(p.startswith("RUBRIC") for _, p, _ in prompts)
    assert all(count == 3 for _, _, count in prompts)    # k replicates each
    # dummy verdicts fail every gate -> analyse() renders zero pairwise prompts in pass 1


# --------------------------------------------------------------------------- HybridJudge: replay

def test_replay_serves_replicates_in_order_then_exhausts():
    p = "RUBRIC x"
    store = {jb.prompt_key(p): [{"faithful": "pass", "depth": 2},
                                {"faithful": "pass", "depth": 1},
                                {"faithful": "fail", "depth": 0}]}
    rj = jb.HybridJudge(store, strict=True)
    assert rj(p)["depth"] == 2 and rj(p)["depth"] == 1 and rj(p)["depth"] == 0
    with pytest.raises(jb.ReplayExhausted):
        rj(p)


def test_strict_replay_raises_on_unknown_prompt():
    rj = jb.HybridJudge({}, strict=True)
    with pytest.raises(jb.ReplayExhausted):
        rj("RUBRIC never-batched")


def test_pass2_replays_rubric_and_collects_true_pairwise_set():
    prompts = jb.collect_rubric_prompts(_cells(), JUDGE, MATERIAL, k=3, seed="s")
    store = {key: [_scripted(p, rep) for rep in range(count)] for key, p, count in prompts}
    pair_prompts = jb.collect_pairwise_prompts(_cells(), JUDGE, MATERIAL, rubric_store=store,
                                               k=3, seed="s")
    # scripted faithful = 2/3 pass on every record -> all eligible -> one pair per matched index
    assert len(pair_prompts) == 2
    assert all(p.startswith("PAIRWISE") and count == 3 for _, p, count in pair_prompts)


# --------------------------------------------------------------------------- the contract

def test_analyse_equivalence_interactive_vs_batch_replay():
    cells = _cells()
    interactive = q.analyse(cells, JUDGE, MATERIAL, judge_fn=_interactive_judge(),
                            k=3, seed="s", run_judge=True)

    rubric = jb.collect_rubric_prompts(cells, JUDGE, MATERIAL, k=3, seed="s")
    store = {key: [_scripted(p, rep) for rep in range(count)] for key, p, count in rubric}
    pairs = jb.collect_pairwise_prompts(cells, JUDGE, MATERIAL, rubric_store=store, k=3, seed="s")
    store.update({key: [_scripted(p, rep) for rep in range(count)] for key, p, count in pairs})

    replayed = q.analyse(cells, JUDGE, MATERIAL,
                         judge_fn=jb.HybridJudge(jb.fresh_store(store), strict=True),
                         k=3, seed="s", run_judge=True)
    assert replayed["rubric_rows"] == interactive["rubric_rows"]
    assert replayed["pairwise_rows"] == interactive["pairwise_rows"]


# --------------------------------------------------------------------------- batch request assembly

def test_build_inlined_requests_pins_frozen_judge_config():
    reqs = jb.build_inlined_requests([("k1", "PROMPT ONE", 3)],
                                     thinking_budget=256, temperature=0, max_output_tokens=2048)
    assert len(reqs) == 3                                # one entry per replicate
    for rep, r in enumerate(reqs):
        assert r.metadata == {"key": f"k1#{rep}"}
        assert r.config.temperature == 0
        assert r.config.max_output_tokens == 2048
        assert r.config.thinking_config.thinking_budget == 256
    assert "PROMPT ONE" in str(reqs[0].contents)


def test_split_batches_respects_token_budget_and_covers_all():
    items = [(f"k{i}", "w " * 2000, 3) for i in range(10)]   # ~1k est tokens per prompt, x3 reps
    chunks = jb.split_batches(items, token_budget=10_000, per_call_output_allowance=500)
    assert sum(len(c) for c in chunks) == len(items)
    flat = [k for c in chunks for k, _, _ in c]
    assert flat == [k for k, _, _ in items]              # order preserved
    assert len(chunks) > 1                               # budget actually forces a split
    for c in chunks:
        est = sum((jb.est_tokens(p) + 500) * n for _, p, n in c)
        assert est <= 10_000


def test_split_batches_rejects_single_item_over_budget():
    with pytest.raises(ValueError):
        jb.split_batches([("k0", "w " * 100_000, 3)], token_budget=10_000,
                         per_call_output_allowance=500)


# --------------------------------------------------------------------------- response ingestion

def _resp(key: str, text: str, *, error=None):
    usage = SimpleNamespace(prompt_token_count=100, candidates_token_count=50,
                            thoughts_token_count=10, total_token_count=160)
    return SimpleNamespace(metadata={"key": key},
                           response=None if error else SimpleNamespace(text=text,
                                                                       usage_metadata=usage),
                           error=error)


def test_ingest_parses_and_routes_failures_to_retry():
    ok = _resp("a#0", '{"faithful": "pass", "depth": 2}')
    garbage = _resp("a#1", "no json here at all")
    errored = _resp("a#2", "", error=SimpleNamespace(code=500, message="boom"))
    results, retries, usage = jb.ingest_inlined_responses([ok, garbage, errored])
    assert results == {"a#0": {"faithful": "pass", "depth": 2}}
    assert sorted(retries) == ["a#1", "a#2"]
    assert len(usage) == 3                               # every attempt logged, ok and failed alike
    assert [u["ok"] for u in usage] == [True, False, False]
    assert usage[0]["in"] == 100 and usage[0]["think"] == 10


def test_store_from_results_orders_replicates_by_index():
    results = {"h1#2": {"depth": 0}, "h1#0": {"depth": 2}, "h1#1": {"depth": 1}}
    store = jb.store_from_results(results)
    assert [v["depth"] for v in store["h1"]] == [2, 1, 0]


# --------------------------------------------------------------------------- state persistence

def test_state_roundtrip(tmp_path):
    st = jb.BatchState(tmp_path / "state.json")
    st.update(phase="rubric", jobs=[{"name": "batches/x", "chunk": 0, "state": "JOB_STATE_PENDING"}])
    st2 = jb.BatchState(tmp_path / "state.json")
    assert st2.data["phase"] == "rubric"
    assert st2.data["jobs"][0]["name"] == "batches/x"


# --------------------------------------------------------------------------- retry round (attempt 2)

def test_build_retry_requests_target_exact_failed_keys():
    prompts = {"h1": "PROMPT ONE", "h2": "PROMPT TWO"}
    reqs = jb.build_retry_requests(["h1#2", "h2#0"], prompts,
                                   thinking_budget=256, temperature=0, max_output_tokens=2048)
    assert [r.metadata["key"] for r in reqs] == ["h1#2", "h2#0"]
    assert "PROMPT ONE" in str(reqs[0].contents) and "PROMPT TWO" in str(reqs[1].contents)
    assert reqs[0].config.thinking_config.thinking_budget == 256


def test_build_retry_requests_unknown_hash_raises():
    with pytest.raises(KeyError):
        jb.build_retry_requests(["missing#0"], {"h1": "P"},
                                thinking_budget=256, temperature=0, max_output_tokens=2048)


# --------------------------------------------------------------------------- streamed persistence

def test_results_jsonl_roundtrip_and_retry_overwrite(tmp_path):
    f = tmp_path / "results.jsonl"
    jb.append_results(f, {"h1#0": {"depth": 2}, "h1#1": {"depth": 1}})
    jb.append_results(f, {"h1#2": {"depth": 0}})           # a later fetch appends
    loaded = jb.load_results(f)
    assert loaded == {"h1#0": {"depth": 2}, "h1#1": {"depth": 1}, "h1#2": {"depth": 0}}
    assert jb.load_results(tmp_path / "absent.jsonl") == {}


def test_missing_keys_reports_unserved_replicates():
    prompts = [("h1", "P1", 3), ("h2", "P2", 2)]
    results = {"h1#0": {}, "h1#1": {}, "h1#2": {}, "h2#0": {}}
    assert jb.missing_keys(prompts, results) == ["h2#1"]
    results["h2#1"] = {}
    assert jb.missing_keys(prompts, results) == []
