"""harness/runner.py — the cell-execution skeleton (Experiment 1, Phase 2).

Ties the three pieces together for one captured call:

    guard.check_before_call()         # don't exceed the call ceiling
    → stream_call(...)                # capture full usage + provenance + timing
    → CaptureRecord.from_capture(...) # validate; compute + self-verify config_hash
    → writer.append(record)           # persist the captured data (it was really spent)
    → guard.register(record.usage)    # may raise CeilingBreach → abort the run

Records are append-only at ``results/<run-id>/records.jsonl`` (raw tokens, no dollars);
the expanded matrix + hashes go to ``config-snapshot.yaml`` so a run replays from its
own directory. The matrix-expansion and full Phase-1a loop are built later (Phase 5);
this skeleton is the proven spine they sit on, plus the warm-once-read-many cache path.
"""

from __future__ import annotations

import datetime as _dt
import secrets
from pathlib import Path
from typing import Any, Callable, Optional, Union

import yaml

from harness.client import stream_call
from harness.config import config_hash
from harness.guard import SpendGuard
from harness.schema import CallConfig, CallRole, CaptureRecord, CellId, ExecPath, UsageVector


def config_to_call_params(config: CallConfig) -> dict[str, Any]:
    """Translate the resolved cell config into Anthropic call params: the cell config is
    *applied*, not re-specified by the caller. ``effort`` → ``output_config``; adaptive/enabled
    thinking → ``thinking``. ``temperature`` is never sent (constitution — omitted on every
    call); ``model``/``max_tokens`` are passed directly by the caller."""
    params: dict[str, Any] = {}
    if config.effort is not None:
        params["output_config"] = {"effort": config.effort}
    if config.thinking == "adaptive":
        params["thinking"] = {"type": "adaptive"}
    elif config.thinking == "enabled":
        # 'enabled' thinking requires a budget_tokens the skeleton doesn't yet thread through;
        # emitting {type:'enabled'} alone is a 400. Fail loud rather than build a doomed call.
        raise ValueError(
            "thinking='enabled' needs a budget_tokens not yet supported by the harness; "
            "Phase 1a uses 'adaptive' (see SPEC #15/#16)"
        )
    return params


def new_run_id(
    *,
    prefix: str = "run",
    now: Optional[_dt.datetime] = None,
    token: Optional[str] = None,
) -> str:
    """A sortable, unique run id: ``run-<UTC-timestamp>-<token>``. ``now``/``token`` are
    injectable for deterministic tests; otherwise UTC-now + a short random token."""
    now = now or _dt.datetime.now(_dt.timezone.utc)
    token = token or secrets.token_hex(3)
    return f"{prefix}-{now.strftime('%Y%m%dT%H%M%SZ')}-{token}"


class RunWriter:
    """Append-only writer for one run's directory. Never rewrites a record."""

    def __init__(self, results_root: Union[str, Path], run_id: str):
        self.run_id = run_id
        self.path = Path(results_root) / run_id
        self.path.mkdir(parents=True, exist_ok=True)
        self.records_path = self.path / "records.jsonl"
        self.snapshot_path = self.path / "config-snapshot.yaml"

    def append(self, record: CaptureRecord) -> None:
        with self.records_path.open("a", encoding="utf-8") as f:
            f.write(record.to_jsonl_line() + "\n")

    def write_snapshot(self, data: dict) -> None:
        self.snapshot_path.write_text(
            yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8"
        )


def _run_and_capture(
    *,
    client: Any,
    guard: SpendGuard,
    writer: RunWriter,
    cell_id: CellId,
    config: CallConfig,
    fixture_hash: str,
    tokenizer_version: str,
    sdk_version: str,
    messages: list[dict[str, Any]],
    system: Optional[Any] = None,
    call_role: CallRole = CallRole.single,
    cache_hit: Optional[bool] = None,
    turn_index: Optional[int] = None,
    tool_result_tokens: Optional[int] = None,
    exec_path: ExecPath = ExecPath.sync_stream,
    skill_hash: Optional[str] = None,
    persist_text: bool = False,
    clock: Optional[Callable[[], float]] = None,
    **params: Any,
) -> tuple[CaptureRecord, str]:
    """Internal helper: run one cell call end-to-end, persist the record, and return
    ``(record, response_text)`` so callers that need the assistant text can use it
    (e.g. multi-turn loops). ``execute_call`` delegates here and discards the text."""
    # Count the attempt BEFORE the call: a mid-stream failure/retry never reaches
    # register_usage, so counting here keeps the call ceiling a real bound on a failing loop.
    guard.register_attempt()

    extra: dict[str, Any] = {"clock": clock} if clock is not None else {}
    # Apply the cell config (effort/thinking); explicit params win over the derived ones.
    call_params = {**config_to_call_params(config), **params}
    result = stream_call(
        client,
        model=config.model_id,
        max_tokens=config.max_tokens,
        messages=messages,
        system=system,
        **extra,
        **call_params,
    )

    # For a cache read, assert the hit from the MEASURED usage when not supplied: a read that
    # came back as fresh input (cache_read == 0) is a miss, and the schema quarantines it.
    if call_role is CallRole.read and cache_hit is None:
        cache_hit = UsageVector.from_raw(result.usage_raw).cache_read_input_tokens > 0

    record = CaptureRecord.from_capture(
        run_id=writer.run_id,
        cell_id=cell_id,
        config=config,
        config_hash=config_hash(config, tokenizer_version=tokenizer_version),
        fixture_hash=fixture_hash,
        model_version=result.model_version,
        tokenizer_version=tokenizer_version,
        sdk_version=sdk_version,
        usage_raw=result.usage_raw,
        stop_reason=result.stop_reason,
        latency_ms=result.latency_ms,
        wall_clock_s=result.wall_clock_s,
        call_role=call_role,
        cache_hit=cache_hit,
        turn_index=turn_index,
        exec_path=exec_path,
        tool_result_tokens=tool_result_tokens,
        skill_hash=skill_hash,
        # Persist the assistant text only when asked (Exp 1c quality grading); cost-only cells
        # keep the tokens-only posture and store None.
        response_text=(result.response_text if persist_text else None),
        request_id=result.request_id,
        rate_limit=result.rate_limit,
    )
    # Persist first (the breaching call must be captured), but register the spend in `finally`
    # so an append IO error never loses the spend the call already incurred.
    try:
        writer.append(record)  # capture — the call was really spent, quarantined or not
    finally:
        guard.register_usage(record.usage)  # may raise CeilingBreach to abort the run
    return record, result.response_text or ""


def execute_call(**kwargs: Any) -> CaptureRecord:
    """Run one cell call end-to-end and return the validated, persisted record."""
    record, _ = _run_and_capture(**kwargs)
    return record


def warm_once_read_many(
    *,
    client: Any,
    guard: SpendGuard,
    writer: RunWriter,
    cell_id: CellId,
    config: CallConfig,
    fixture_hash: str,
    tokenizer_version: str,
    sdk_version: str,
    cached_system: Any,
    warm_message: dict[str, Any],
    read_messages: list[dict[str, Any]],
    clock: Optional[Callable[[], float]] = None,
    call_wrapper: Callable[[Callable[[], Any]], Any] = lambda f: f(),
) -> tuple[CaptureRecord, list[CaptureRecord]]:
    """Cache cell (#10–12): one warm-write call that creates the cache, then the read calls
    against the same cached prefix. Write cost and read distribution are recorded separately
    (different ``call_role``); every read asserts a hit. Returns ``(write_record, [reads])``.

    ``call_wrapper`` is an optional per-call decorator (default: identity). Pass
    ``call_with_backoff`` from run.py to get per-call retry without re-running the whole
    warm+read sequence on a 429 during reads."""
    common = dict(
        client=client,
        guard=guard,
        writer=writer,
        cell_id=cell_id,
        config=config,
        fixture_hash=fixture_hash,
        tokenizer_version=tokenizer_version,
        sdk_version=sdk_version,
        system=cached_system,
        clock=clock,
    )
    write_record = call_wrapper(lambda: execute_call(**common, messages=[warm_message], call_role=CallRole.write))
    read_records = [
        call_wrapper(lambda msg=msg: execute_call(**common, messages=[msg], call_role=CallRole.read))
        for msg in read_messages
    ]
    return write_record, read_records


def execute_payload_call(*, client, guard, writer, cell_id, config, fixture_hash,
                         tokenizer_version, sdk_version, messages, tools, tool_result_tokens, clock=None):
    """One captured call carrying the payload as a scripted tool_result; tool_result_tokens recorded."""
    record, _ = _run_and_capture(
        client=client, guard=guard, writer=writer, cell_id=cell_id, config=config,
        fixture_hash=fixture_hash, tokenizer_version=tokenizer_version, sdk_version=sdk_version,
        messages=messages, call_role=CallRole.single, tool_result_tokens=tool_result_tokens,
        clock=clock, tools=tools,
    )
    return record


def run_multiturn_session(*, client, guard, writer, cell_id, config, fixture_hash,
                          tokenizer_version, sdk_version, turns, clock=None):
    """Replay scripted USER turns, feeding each model reply forward; one record per turn."""
    messages: list[dict] = []
    records = []
    for i, turn in enumerate(turns):
        messages.append({"role": "user", "content": turn})
        record, reply = _run_and_capture(
            client=client, guard=guard, writer=writer, cell_id=cell_id, config=config,
            fixture_hash=fixture_hash, tokenizer_version=tokenizer_version, sdk_version=sdk_version,
            messages=list(messages), call_role=CallRole.single, turn_index=i, clock=clock,
        )
        records.append(record)
        messages.append({"role": "assistant", "content": reply})
    return records
