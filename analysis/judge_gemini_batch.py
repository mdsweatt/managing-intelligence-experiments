"""Batch-API transport for the FROZEN 1d judge (docs/phase1d-judge-spec.md).

The interactive path died on the Tier-1 250-requests/day quota (2026-07-02). This module reruns
the judge through Gemini Batch jobs — an OPERATIONAL transport change only: the instrument (model,
prompt bytes, thinking_budget, temperature, max_output_tokens, tolerant parser, K-replicate
majority, 2-attempt retry contract) is byte-identical and `judge_hash` is untouched. quality.py's
`analyse()` is never modified; the batch layer wraps it as record -> batch -> replay:

  pass 1  `collect_rubric_prompts`   — HybridJudge({}) records every rubric prompt; its dummy
          verdicts fail every gate, so no pairwise prompt renders (nothing to mis-record).
  batch   `build_inlined_requests` / `split_batches` -> submit, poll, fetch (CLI below), results
          streamed to disk per attempt the moment they are fetched (the interactive path lost its
          in-memory usage log to the quota crash; nothing here is memory-only).
  pass 2  `collect_pairwise_prompts` — replays the real rubric verdicts so eligibility is real,
          records the TRUE pairwise prompt set.
  pass 3  `analyse(judge_fn=HybridJudge(full_store, strict=True))` — the real output, zero spend.

Parse failures mirror the interactive 2-attempt contract: a failed item goes to ONE retry batch
round; a second failure is a hard error (the interactive `raise last`), escalated, never papered
over. Per-attempt usage rows mirror judge_gemini._usage_record's schema.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
from collections import deque
from pathlib import Path
from typing import Any, Optional

from analysis.quality import _parse_json
from harness.hashing import sha256_hex

# Tier-1 Batch cap is 5M enqueued tokens per model across ACTIVE jobs (verified live 2026-07-02,
# ai.google.dev/gemini-api/docs/rate-limits); we chunk under it with margin. Output allowance per
# call sized from the micro-pilot's measured ~460 out+think mean, rounded up.
TOKEN_BUDGET = 4_500_000
OUTPUT_ALLOWANCE = 600
BATCH_PRICE_IN, BATCH_PRICE_OUT = 1.0, 6.0   # $/M, 50% of interactive (live 2026-07-02)


class ReplayExhausted(Exception):
    """A prompt was asked of the replay store that it cannot serve (unknown, or replicates spent)."""


class _DummyVerdict(dict):
    """Recording-pass stand-in verdict: answers every check id with "1" — coerces cleanly for both
    binary checks ("1" != "pass" -> "fail", so every gate stays shut) and graded checks (int("1")).
    A shut gate is the point: pass 1 must render zero pairwise prompts."""

    def __missing__(self, key: str) -> str:
        return "1"


def prompt_key(prompt: str) -> str:
    return sha256_hex(prompt)[:32]


def fresh_store(store: dict[str, list[dict]]) -> dict[str, list[dict]]:
    """A consumable copy — HybridJudge pops replicates, so each analyse() pass needs its own."""
    return {k: list(v) for k, v in store.items()}


class HybridJudge:
    """A JudgeFn over a replay store. Known prompt -> next queued replicate verdict. Unknown
    prompt -> recorded (with multiplicity) and answered with a gate-failing dummy, unless
    strict=True, where anything unservable raises ReplayExhausted."""

    def __init__(self, store: dict[str, Any], strict: bool = False):
        self.store: dict[str, deque] = {k: deque(v) for k, v in store.items()}
        self.strict = strict
        self.recorded: dict[str, list] = {}   # key -> [prompt, count], insertion-ordered

    def __call__(self, prompt: str) -> dict:
        key = prompt_key(prompt)
        queue = self.store.get(key)
        if queue:
            return queue.popleft()
        if queue is not None:   # known prompt, replicates spent — a store-building bug, never dummy
            raise ReplayExhausted(f"replicates exhausted for prompt {key}")
        if self.strict:
            raise ReplayExhausted(f"no batch result for prompt {key}: {prompt[:80]!r}")
        rec = self.recorded.setdefault(key, [prompt, 0])
        rec[1] += 1
        return _DummyVerdict()

    def recorded_items(self) -> list[tuple[str, str, int]]:
        return [(k, p, c) for k, (p, c) in self.recorded.items()]


def collect_rubric_prompts(cells: dict, judge: dict, material: dict, *, k: int,
                           seed: str) -> list[tuple[str, str, int]]:
    """Pass 1: run the real analyse() with an empty-store HybridJudge; every prompt it records is a
    rubric prompt (dummy verdicts shut every pairwise gate)."""
    from analysis.quality import analyse
    hj = HybridJudge({})
    analyse(cells, judge, material, judge_fn=hj, k=k, seed=seed, run_judge=True)
    return hj.recorded_items()


def collect_pairwise_prompts(cells: dict, judge: dict, material: dict, *, rubric_store: dict,
                             k: int, seed: str) -> list[tuple[str, str, int]]:
    """Pass 2: replay real rubric verdicts (real eligibility) and record the true pairwise set."""
    from analysis.quality import analyse
    hj = HybridJudge(fresh_store(rubric_store))
    analyse(cells, judge, material, judge_fn=hj, k=k, seed=seed, run_judge=True)
    return hj.recorded_items()


# =========================================================================== batch request assembly

def build_inlined_requests(items: list[tuple[str, str, int]], *, thinking_budget: int,
                           temperature: float, max_output_tokens: int) -> list:
    """One InlinedRequest per replicate, tagged metadata key '<prompt_key>#<replicate>', pinned to
    the frozen judge_config exactly (spec §1)."""
    from google.genai import types
    reqs = []
    for key, prompt, count in items:
        for rep in range(count):
            reqs.append(types.InlinedRequest(
                contents=[types.Content(role="user", parts=[types.Part(text=prompt)])],
                metadata={"key": f"{key}#{rep}"},
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                    thinking_config=types.ThinkingConfig(thinking_budget=thinking_budget)),
            ))
    return reqs


def est_tokens(prompt: str) -> int:
    return max(1, len(prompt) // 4)


def split_batches(items: list[tuple[str, str, int]], *, token_budget: int,
                  per_call_output_allowance: int) -> list[list[tuple[str, str, int]]]:
    """Greedy in-order split so each chunk's estimated enqueued tokens (input estimate + output
    allowance, x replicates) stays under the Tier-1 per-model cap. Chunks run SEQUENTIALLY —
    the cap counts tokens across all *active* jobs."""
    chunks: list[list] = []
    cur: list = []
    cur_cost = 0
    for item in items:
        _, prompt, count = item
        cost = (est_tokens(prompt) + per_call_output_allowance) * count
        if cost > token_budget:
            raise ValueError(f"single item exceeds token budget: {cost} > {token_budget}")
        if cur and cur_cost + cost > token_budget:
            chunks.append(cur)
            cur, cur_cost = [], 0
        cur.append(item)
        cur_cost += cost
    if cur:
        chunks.append(cur)
    return chunks


def build_retry_requests(retry_keys: list[str], prompts_by_hash: dict[str, str], *,
                         thinking_budget: int, temperature: float, max_output_tokens: int) -> list:
    """Attempt-2 requests for exactly the failed '<hash>#<rep>' keys — the batch mirror of the
    interactive 2-attempt contract. Raises KeyError if a key's prompt is unknown (state corruption:
    never silently re-derive a frozen prompt)."""
    from google.genai import types
    reqs = []
    for key in retry_keys:
        h = key.rsplit("#", 1)[0]
        prompt = prompts_by_hash[h]
        reqs.append(types.InlinedRequest(
            contents=[types.Content(role="user", parts=[types.Part(text=prompt)])],
            metadata={"key": key},
            config=types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                thinking_config=types.ThinkingConfig(thinking_budget=thinking_budget)),
        ))
    return reqs


# =========================================================================== response ingestion

def _u(um: Any, field: str) -> int:
    v = getattr(um, field, None) if um is not None else None
    return int(v) if v is not None else 0


def ingest_inlined_responses(responses: list) -> tuple[dict, list, list]:
    """Batch results -> ({key: parsed_verdict}, [keys to retry], [usage rows]). Every attempt gets
    a usage row, success or failure (a failed call is still input-billed — judge-spec §1). Parsing
    is quality._parse_json, byte-identical to the interactive path."""
    results: dict[str, dict] = {}
    retries: list[str] = []
    usage: list[dict] = []
    for r in responses:
        key = (getattr(r, "metadata", None) or {}).get("key")
        err = getattr(r, "error", None)
        resp = getattr(r, "response", None) if err is None else None
        text = (getattr(resp, "text", None) or "") if resp is not None else ""
        um = getattr(resp, "usage_metadata", None) if resp is not None else None
        parsed: Optional[dict] = None
        if err is None:
            try:
                parsed = _parse_json(text)
            except (ValueError, json.JSONDecodeError):
                parsed = None
        ok = parsed is not None
        usage.append({"key": key, "ok": ok,
                      "in": _u(um, "prompt_token_count"), "out": _u(um, "candidates_token_count"),
                      "think": _u(um, "thoughts_token_count"), "total": _u(um, "total_token_count"),
                      "error": (str(getattr(err, "message", err)) if err is not None
                                else (None if ok else f"unparseable: {text[:80]!r}"))})
        if ok:
            results[key] = parsed
        else:
            retries.append(key)
    return results, retries, usage


def store_from_results(results: dict[str, dict]) -> dict[str, list[dict]]:
    """{'<hash>#<rep>': verdict} -> {'<hash>': [verdicts in replicate order]} for HybridJudge."""
    grouped: dict[str, list[tuple[int, dict]]] = {}
    for key, verdict in results.items():
        h, rep = key.rsplit("#", 1)
        grouped.setdefault(h, []).append((int(rep), verdict))
    return {h: [v for _, v in sorted(reps)] for h, reps in grouped.items()}


def append_results(path: Path, results: dict[str, dict]) -> None:
    """Stream parsed verdicts to disk the moment a fetch lands — nothing graded lives only in
    memory (the interactive path lost ~250 calls' log to exactly that)."""
    with Path(path).open("a", encoding="utf-8") as f:
        for key, verdict in results.items():
            f.write(json.dumps({"key": key, "verdict": verdict}) + "\n")


def load_results(path: Path) -> dict[str, dict]:
    path = Path(path)
    if not path.exists():
        return {}
    out: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            out[row["key"]] = row["verdict"]
    return out


def missing_keys(prompts: list[tuple[str, str, int]], results: dict[str, dict]) -> list[str]:
    """Replicate keys still unserved — must be [] before the strict pass-3 replay may run."""
    return [f"{h}#{rep}" for h, _, count in prompts for rep in range(count)
            if f"{h}#{rep}" not in results]


# =========================================================================== state persistence

class BatchState:
    """Crash-safe run state (job names, phase cursor) — everything needed to resume from a fresh
    session lives here, on disk, updated atomically on every transition."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.data: dict = json.loads(self.path.read_text()) if self.path.exists() else {}

    def update(self, **kw: Any) -> None:
        self.data.update(kw)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=2), encoding="utf-8")
        tmp.replace(self.path)


# =========================================================================== CLI orchestration
# Thin glue over the tested pieces above. plan (free) -> step [--go] (submits/polls/fetches, one
# state transition per call, resume-safe from the state file alone) -> finalize (free, strict).

def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_world(a) -> tuple[dict, dict, dict, int]:
    """The exact loading path of quality.main — same manifests, same shapes."""
    from analysis.quality import load_factorial, load_judge, load_task_material, pairwise_tasks
    judge = load_judge(a.judge_manifest, a.fixtures_root)
    material = load_task_material(a.phase1c_manifest, a.fixtures_root,
                                  tasks=pairwise_tasks(judge["rubrics"]))
    cells = load_factorial(Path(a.run_dir) / "records.jsonl")
    return judge, material, cells, judge["k"]


def _write_prompts(path: Path, prompts: list[tuple[str, str, int]]) -> None:
    path.write_text("".join(json.dumps({"hash": h, "prompt": p, "count": c}) + "\n"
                            for h, p, c in prompts), encoding="utf-8")


def _read_prompts(path: Path) -> list[tuple[str, str, int]]:
    return [(r["hash"], r["prompt"], r["count"])
            for r in (json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x)]


def _phase_estimate(prompts: list[tuple[str, str, int]]) -> tuple[int, int, float]:
    calls = sum(c for _, _, c in prompts)
    tok_in = sum(est_tokens(p) * c for _, p, c in prompts)
    usd = (tok_in * BATCH_PRICE_IN + calls * 500 * BATCH_PRICE_OUT) / 1e6
    return calls, tok_in, usd


def _append_usage(path: Path, rows: list[dict], *, phase: str, job: str, round_: int) -> None:
    with path.open("a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps({**r, "phase": phase, "job": job, "round": round_,
                                "ts": _now()}) + "\n")


def _client():
    from dotenv import load_dotenv
    load_dotenv()
    from google import genai
    return genai.Client()


def _jc(judge: dict) -> dict:
    jc = judge.get("judge_config", {})
    return dict(thinking_budget=jc["thinking_budget"], temperature=jc.get("temperature", 0),
                max_output_tokens=jc.get("max_output_tokens", 2048))


def _submit(client, judge: dict, reqs: list, display: str) -> str:
    job = client.batches.create(model=judge["judge_model"], src=reqs,
                                config={"display_name": display})
    return job.name


def _chunks_for_phase(state: BatchState, phase: str, prompts: list) -> list[list]:
    return split_batches(prompts, token_budget=TOKEN_BUDGET,
                         per_call_output_allowance=OUTPUT_ALLOWANCE)


def cmd_plan(a) -> int:
    judge, material, cells, k = _load_world(a)
    out = Path(a.out) / "batch"
    out.mkdir(parents=True, exist_ok=True)
    prompts = collect_rubric_prompts(cells, judge, material, k=k, seed=a.seed)
    _write_prompts(out / "rubric-prompts.jsonl", prompts)
    chunks = _chunks_for_phase(None, "rubric", prompts)
    calls, tok_in, usd = _phase_estimate(prompts)
    st = BatchState(out / "state.json")
    st.update(phase="rubric", run_dir=str(a.run_dir), seed=a.seed, k=k,
              judge_hash=judge["judge_hash_computed"], model=judge["judge_model"],
              chunks_total=len(chunks), chunks_done=0, jobs=[], failed_final=[],
              created=_now())
    print(f"judge_hash (computed): {judge['judge_hash_computed']}")
    print(f"rubric phase: {len(prompts)} prompts x k -> {calls} calls in {len(chunks)} "
          f"sequential batches (~{tok_in / 1e6:.1f}M input tokens est)")
    print(f"rubric estimate at batch prices: ~${usd:.2f} "
          f"(pairwise phase sized after rubric verdicts; interactive bound was ~$8 batch)")
    print(f"state: {out / 'state.json'}")
    return 0


def cmd_step(a) -> int:
    out = Path(a.out) / "batch"
    st = BatchState(out / "state.json")
    if not st.data:
        print("no state — run plan first")
        return 1
    if st.data.get("failed_final"):
        print(f"ESCALATE: {len(st.data['failed_final'])} keys failed both attempts: "
              f"{st.data['failed_final'][:5]} — not advancing")
        return 2
    phase = st.data["phase"]
    if phase == "done":
        print("all phases complete — run finalize")
        return 0

    prompts_path = out / f"{phase}-prompts.jsonl"
    prompts = _read_prompts(prompts_path)
    prompts_by_hash = {h: p for h, p, _ in prompts}
    active = [j for j in st.data["jobs"] if j.get("phase") == phase and not j.get("done")]

    if active:
        client = _client()
        job_rec = active[0]
        job = client.batches.get(name=job_rec["name"])
        state_name = str(job.state and job.state.name)
        print(f"{job_rec['name']} [{phase} chunk {job_rec['chunk']}]: {state_name}")
        if state_name in ("JOB_STATE_PENDING", "JOB_STATE_QUEUED", "JOB_STATE_RUNNING",
                          "JOB_STATE_UPDATING"):
            return 0
        if state_name != "JOB_STATE_SUCCEEDED":
            print(f"ESCALATE: batch ended {state_name}: {getattr(job, 'error', None)}")
            return 2
        responses = (job.dest and job.dest.inlined_responses) or []
        results, retries, usage = ingest_inlined_responses(responses)
        append_results(out / "results.jsonl", results)
        _append_usage(out / "usage.jsonl", usage, phase=phase, job=job_rec["name"],
                      round_=job_rec.get("round", 1))
        job_rec["done"] = True
        if retries:
            if job_rec.get("round", 1) >= 2:
                st.update(failed_final=st.data["failed_final"] + retries, jobs=st.data["jobs"])
                print(f"ESCALATE: {len(retries)} keys failed attempt 2")
                return 2
            if not a.go:
                print(f"{len(retries)} parse failures need an attempt-2 batch — rerun with --go")
                st.update(jobs=st.data["jobs"], pending_retry={"keys": retries,
                                                               "round": job_rec.get("round", 1) + 1})
                return 0
            reqs = build_retry_requests(retries, prompts_by_hash, **_jc_from_state(st))
            name = _submit(client, {"judge_model": st.data["model"]}, reqs,
                           f"phase1d-{phase}-retry")
            st.data["jobs"].append({"name": name, "phase": phase, "chunk": job_rec["chunk"],
                                    "round": job_rec.get("round", 1) + 1, "done": False,
                                    "submitted": _now()})
            st.update(jobs=st.data["jobs"])
            print(f"submitted attempt-2 batch {name} for {len(retries)} keys")
            return 0
        if job_rec.get("round", 1) == 1:
            st.data["chunks_done"] = st.data.get("chunks_done", 0) + 1
        st.update(jobs=st.data["jobs"], chunks_done=st.data["chunks_done"])
        print(f"fetched {len(results)} results ({st.data['chunks_done']}/{st.data['chunks_total']} "
              f"chunks done)")
        # fall through: maybe submit the next chunk or advance the phase

    results = load_results(out / "results.jsonl")
    pending_retry = st.data.get("pending_retry")
    if pending_retry:
        if not a.go:
            print(f"{len(pending_retry['keys'])} keys await attempt 2 — rerun with --go")
            return 0
        client = _client()
        reqs = build_retry_requests(pending_retry["keys"], prompts_by_hash, **_jc_from_state(st))
        name = _submit(client, {"judge_model": st.data["model"]}, reqs, f"phase1d-{phase}-retry")
        st.data["jobs"].append({"name": name, "phase": phase, "chunk": -1,
                                "round": pending_retry["round"], "done": False,
                                "submitted": _now()})
        st.data.pop("pending_retry")
        st.update(**st.data)
        print(f"submitted attempt-2 batch {name}")
        return 0

    missing = missing_keys(prompts, results)
    if missing:
        chunks = _chunks_for_phase(st, phase, prompts)
        done = st.data.get("chunks_done", 0)
        if done >= len(chunks):
            print(f"ESCALATE: all chunks done but {len(missing)} keys missing (e.g. {missing[:3]})")
            return 2
        if not a.go:
            print(f"next: submit {phase} chunk {done + 1}/{len(chunks)} — rerun with --go")
            return 0
        client = _client()
        chunk = chunks[done]
        reqs = build_inlined_requests(chunk, **_jc_from_state(st))
        name = _submit(client, {"judge_model": st.data["model"]}, reqs,
                       f"phase1d-{phase}-chunk{done + 1}")
        st.data["jobs"].append({"name": name, "phase": phase, "chunk": done + 1, "round": 1,
                                "done": False, "submitted": _now()})
        st.update(jobs=st.data["jobs"])
        calls = sum(c for _, _, c in chunk)
        print(f"submitted {name}: {phase} chunk {done + 1}/{len(chunks)} ({calls} calls)")
        return 0

    # phase complete
    if phase == "rubric":
        judge, material, cells, k = _load_world(_args_from_state(a, st))
        store = store_from_results(results)
        pair_prompts = collect_pairwise_prompts(cells, judge, material, rubric_store=store,
                                                k=k, seed=st.data["seed"])
        _write_prompts(out / "pairwise-prompts.jsonl", pair_prompts)
        chunks = _chunks_for_phase(st, "pairwise", pair_prompts)
        calls, tok_in, usd = _phase_estimate(pair_prompts)
        st.update(phase="pairwise", chunks_total=len(chunks), chunks_done=0)
        print(f"rubric phase COMPLETE -> pairwise: {len(pair_prompts)} pairs x k = {calls} calls "
              f"in {len(chunks)} batches (~${usd:.2f} est). Rerun step --go to submit.")
        return 0
    st.update(phase="done")
    print("pairwise phase COMPLETE — run finalize")
    return 0


def _jc_from_state(st: BatchState) -> dict:
    """judge_config for submissions, reloaded from the frozen manifest recorded in state."""
    import yaml
    man = yaml.safe_load(Path(st.data["judge_manifest"]).read_text(encoding="utf-8")) \
        if st.data.get("judge_manifest") else None
    jc = (man or {}).get("judge_config", {"thinking_budget": 256, "temperature": 0,
                                          "max_output_tokens": 2048})
    return dict(thinking_budget=jc["thinking_budget"], temperature=jc.get("temperature", 0),
                max_output_tokens=jc.get("max_output_tokens", 2048))


def _args_from_state(a, st: BatchState):
    a.run_dir = st.data["run_dir"]
    return a


def cmd_finalize(a) -> int:
    from analysis.quality import (_write_findings, _write_pairwise_csv, _write_rubric_csv,
                                  _write_spotcheck, analyse, pairwise_tasks, spotcheck_sample)
    out_root = Path(a.out)
    out = out_root / "batch"
    st = BatchState(out / "state.json")
    judge, material, cells, k = _load_world(_args_from_state(a, st))
    results = load_results(out / "results.jsonl")
    for phase_file in ("rubric-prompts.jsonl", "pairwise-prompts.jsonl"):
        missing = missing_keys(_read_prompts(out / phase_file), results)
        if missing:
            print(f"INCOMPLETE: {phase_file} has {len(missing)} unserved keys — refusing to grade")
            return 2
    store = store_from_results(results)
    res = analyse(cells, judge, material, judge_fn=HybridJudge(fresh_store(store), strict=True),
                  k=k, seed=st.data["seed"], run_judge=True)
    gen_tasks = pairwise_tasks(judge["rubrics"])
    _write_rubric_csv(out_root / "quality_rubric.csv", res["rubric_rows"])
    _write_pairwise_csv(out_root / "quality_pairwise.csv", res["pairwise_rows"])
    spot = spotcheck_sample(cells, frac=a.spotcheck_frac, seed=st.data["seed"], tasks=gen_tasks)
    _write_spotcheck(out_root / "quality_spotcheck.csv", out_root / "quality_spotcheck_key.csv", spot)
    _write_findings(out_root / "quality-findings.md", judge, res["rubric_rows"],
                    res["pairwise_rows"], run_judge=True, run_dir=st.data["run_dir"],
                    phase_label="Phase-1d")
    print(f"judge_hash (computed): {judge['judge_hash_computed']}")
    print(f"graded {sum(len(v) for v in cells.values())} outputs; wrote quality_* to {out_root}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="analysis.judge_gemini_batch",
                                description="Batch-API transport for the frozen 1d judge")
    p.add_argument("command", choices=["plan", "step", "finalize"])
    p.add_argument("run_dir", nargs="?", help="results/<run-id> (plan; later steps read state)")
    p.add_argument("--judge-manifest", default="fixtures/judge/manifest-phase1d.yaml")
    p.add_argument("--phase1c-manifest", "--fixtures-manifest", dest="phase1c_manifest",
                   default="fixtures/manifest-phase1d.yaml")
    p.add_argument("--fixtures-root", default="fixtures")
    p.add_argument("--seed", default="phase1c")
    p.add_argument("--spotcheck-frac", type=float, default=0.10)
    p.add_argument("--out", default="analysis/output/phase1d")
    p.add_argument("--go", action="store_true", help="permit a billable batch submission this step")
    a = p.parse_args(argv)
    if a.command == "plan":
        if not a.run_dir:
            p.error("plan requires run_dir")
        rc = cmd_plan(a)
        BatchState(Path(a.out) / "batch" / "state.json").update(judge_manifest=a.judge_manifest)
        return rc
    if a.command == "step":
        return cmd_step(a)
    return cmd_finalize(a)


if __name__ == "__main__":
    raise SystemExit(main())
