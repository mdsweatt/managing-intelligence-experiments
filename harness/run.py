"""harness/run.py — run-loop configuration snapshot builder (Experiment 1, Phase 5).

The snapshot captures the full measurement contract before a run begins: which cells
are being run, their fixtures (hashed), the exact API config per unit, the guard
caps, and full version/provenance. It is written to results/<run-id>/snapshot.json
and doubles as the audit trail for replay.
"""

from __future__ import annotations

import datetime as _dt
import time
from typing import Any, Callable

import harness
from harness.assemble import assemble
from harness.runner import execute_call, warm_once_read_many, run_multiturn_session, execute_payload_call
from harness.schema import CallRole


def _recorded(unit: Any) -> int:
    """Extract recorded token count for a unit, treating 'TBD' as 0.

    Args:
        unit: RunUnit instance with fixture.recorded_token_counts and config.model_role

    Returns:
        int: token count (or 0 if TBD or unmeasured)
    """
    tc = unit.fixture.recorded_token_counts
    val = tc.tok_opus if unit.config.model_role == "opus" else tc.tok_hs
    return val if isinstance(val, int) else 0


def estimate_units(units: list[Any]) -> dict:
    """Project calls and input tokens per family: dry-run cost estimate.

    Args:
        units: list[RunUnit] from expand_matrix

    Returns:
        dict with keys:
            - total_calls: total API calls across all units
            - input_tokens_estimate: total input tokens (coarse estimate)
            - by_family: dict mapping family -> {cells, calls, input_tokens_estimate}
            - notes: list of caveats about the estimate
    """
    by_family: dict[str, dict] = {}
    total_calls = 0
    total_input = 0

    for u in units:
        rec = _recorded(u)
        n = u.n

        if u.family == "cache":
            calls = 1 + n                     # one warm-write + n reads
            inp = rec * (1 + n)               # coarse: write bills full input; reads ~cached
        elif u.family == "multiturn":
            turns = u.fixture.proxy.value if isinstance(u.fixture.proxy.value, int) else 1
            calls = n * turns
            inp = rec * n * turns             # coarse: ignores per-turn compounding
        else:                                  # standard, payload
            calls = n
            inp = rec * n

        total_calls += calls
        total_input += inp

        slot = by_family.setdefault(u.family, {"cells": 0, "calls": 0, "input_tokens_estimate": 0})
        slot["cells"] += 1
        slot["calls"] += calls
        slot["input_tokens_estimate"] += inp

    return {
        "total_calls": total_calls,
        "input_tokens_estimate": total_input,
        "by_family": by_family,
        "notes": [
            "Call counts are exact.",
            "Input estimate is single-call/first-turn precise; cache-read, multi-turn compounding, "
            "and ALL output tokens are coarse priors, not measurements.",
            "Unmeasured (TBD) fixtures count as 0 input — freeze + measure for a real estimate.",
        ],
    }


def build_snapshot(rm, units, guard, *, sdk_version, matrix_path, manifest_path, run_id, skipped: list) -> dict:
    """Build the run's config snapshot — the measure contract before measurement begins.

    Args:
        rm: RunMatrix (from load_run_matrix), carries meta.n_per_cell
        units: list[RunUnit] (from expand_matrix), the cells to run
        guard: SpendGuard instance, snapshot() -> dict of caps and counters
        sdk_version: str, the Anthropic SDK version (e.g., "0.109.2")
        matrix_path: str, path to the run matrix YAML
        manifest_path: str, path to the fixtures manifest YAML
        run_id: str, the run's unique identifier
        skipped: list[tuple[int, str]], the (task_id, band) pairs in the matrix that
                 have no fixture in the manifest

    Returns:
        dict with keys: run_id, created_utc, harness_version, sdk_version,
        matrix_path, manifest_path, n_per_cell, guard, units, skipped_bands.
    """
    return {
        "run_id": run_id,
        "created_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "harness_version": harness.__version__,
        "sdk_version": sdk_version,
        "matrix_path": matrix_path,
        "manifest_path": manifest_path,
        "n_per_cell": rm.meta.n_per_cell,
        "guard": guard.snapshot(),
        "units": [
            {
                "cell_key": u.cell_id.key(),
                "task_id": u.cell_id.task_id,
                "band": u.cell_id.band,
                "model_role": u.cell_id.model_role,
                "role_label": u.role_label,
                "family": u.family,
                "config": u.config.model_dump(),
                "fixture_sha256": u.fixture.sha256,
                "n": u.n,
            }
            for u in units
        ],
        "skipped_bands": [list(p) for p in skipped],
    }


def _is_rate_limit(e: Exception) -> bool:
    """Check if an exception represents a rate-limit error.

    Checks for:
    - anthropic.RateLimitError (if anthropic SDK is available)
    - Any exception with status_code == 429

    Args:
        e: The exception to check

    Returns:
        bool: True if the exception is a rate-limit error, False otherwise
    """
    try:
        import anthropic
        if isinstance(e, anthropic.RateLimitError):
            return True
    except Exception:
        pass
    return getattr(e, "status_code", None) == 429


def call_with_backoff(thunk: Callable[[], Any], *, max_retries: int = 5, base_delay: float = 1.0, sleep: Callable[[float], None] = time.sleep, is_rate_limit: Callable[[Exception], bool] = _is_rate_limit) -> Any:
    """Call a thunk with exponential backoff on rate-limit errors.

    Retries the thunk on rate-limit errors (as determined by is_rate_limit) with
    exponential backoff. Non-rate-limit errors are re-raised immediately.

    Args:
        thunk: A callable that takes no arguments and returns a value
        max_retries: Maximum number of retries after the initial attempt (default 5)
        base_delay: Base delay in seconds for exponential backoff (default 1.0)
        sleep: A callable that sleeps for a given number of seconds (default time.sleep).
               Injected for testability.
        is_rate_limit: A callable that takes an Exception and returns True if it's a
                       rate-limit error (default _is_rate_limit). Injected for testability.

    Returns:
        The return value of thunk() if it succeeds

    Raises:
        The last exception encountered if max_retries is exceeded, or any non-rate-limit
        exception raised by thunk()
    """
    attempt = 0
    while True:
        try:
            return thunk()
        except Exception as e:
            if not is_rate_limit(e) or attempt >= max_retries:
                raise
            sleep(base_delay * (2 ** attempt))   # exponential backoff
            attempt += 1


import argparse
from pathlib import Path
from harness.config import load_run_matrix, load_manifest, load_skill_manifest, load_neutral_manifest
from harness.expand import expand_matrix, skipped_bands
from harness.guard import SpendGuard
from harness.runner import RunWriter, new_run_id


def run(*, matrix_path, manifest_path, fixtures_root, out_root, dry_run, usd_prior, limit,
        skill_manifest_path=None, neutral_manifest_path=None, client=None, clock=None) -> dict:
    rm = load_run_matrix(matrix_path)
    manifest = load_manifest(manifest_path)
    # Exp 1c factorial matrices reference a skill manifest; Phase-1a matrices don't (None is fine).
    skill_manifest = load_skill_manifest(skill_manifest_path) if skill_manifest_path else None
    # Exp 1d factorial matrices with a neutral arm reference a neutral manifest (None is fine otherwise).
    neutral_manifest = load_neutral_manifest(neutral_manifest_path) if neutral_manifest_path else None
    units = expand_matrix(rm, manifest, skill_manifest, neutral_manifest)
    skipped = skipped_bands(rm, manifest)
    if limit is not None:
        units = units[:limit]
    if dry_run:
        return {"mode": "dry_run", "units": len(units), "estimate": estimate_units(units),
                "skipped_bands": skipped}

    if client is None:
        import anthropic
        from dotenv import load_dotenv
        load_dotenv(); client = anthropic.Anthropic()
    if usd_prior is None:
        raise ValueError("a real run needs --usd-prior (the conservative $/1M-token safety prior)")
    import anthropic as _a
    from harness.fixtures import make_counter
    est = estimate_units(units)
    guard = SpendGuard.from_dollar_ceiling(rm.meta.cost_ceiling_usd,
                                           usd_per_million_tokens_prior=usd_prior,
                                           max_calls=est["total_calls"] + 1)
    run_id = new_run_id()
    writer = RunWriter(out_root, run_id)
    writer.write_snapshot(build_snapshot(rm, units, guard, sdk_version=_a.__version__,
                                         matrix_path=matrix_path, manifest_path=manifest_path,
                                         run_id=run_id, skipped=skipped))
    read_file = lambda rel: (Path(fixtures_root) / rel).read_text(encoding="utf-8")
    written = run_units(units, client=client, guard=guard, writer=writer, read_file=read_file,
                        counter=make_counter(client), sdk_version=_a.__version__, models=rm.models,
                        clock=clock)
    return {"mode": "run", "run_id": run_id, "records": written, "out": str(writer.path)}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="harness.run", description="Experiment-1 benchmark run loop")
    p.add_argument("--matrix", required=True)
    p.add_argument("--manifest", default="fixtures/manifest.yaml")
    p.add_argument("--skill-manifest", default=None, help="skills/manifest.yaml (Exp 1c only)")
    p.add_argument("--neutral-manifest", default=None, help="neutral/manifest.yaml (Exp 1d neutral arm)")
    p.add_argument("--fixtures-root", default="fixtures")
    p.add_argument("--out", default="results")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--usd-prior", type=float, default=None)
    p.add_argument("--limit", type=int, default=None)
    a = p.parse_args(argv)
    import json
    out = run(matrix_path=a.matrix, manifest_path=a.manifest, fixtures_root=a.fixtures_root,
              out_root=a.out, dry_run=a.dry_run, usd_prior=a.usd_prior, limit=a.limit,
              skill_manifest_path=a.skill_manifest, neutral_manifest_path=a.neutral_manifest)
    print(json.dumps(out, indent=2, default=str))
    return 0


def run_units(units, *, client, guard, writer, read_file, counter, sdk_version, models, clock=None) -> int:
    written = 0
    for u in units:
        plan = assemble(u, read_file, require_frozen=True)     # frozen gate; refuses unfrozen
        tok = models[u.config.model_role].tokenizer
        common = dict(client=client, guard=guard, writer=writer, cell_id=u.cell_id, config=u.config,
                      fixture_hash=plan.fixture_hash, tokenizer_version=tok, sdk_version=sdk_version,
                      clock=clock)
        if u.family == "standard":
            # Exp 1c factorial cells inject the skill as a `system` block and persist output text
            # for the quality judge; Phase-1a standard cells have system=None and store no text.
            persist = u.role_label == "factorial"
            for _ in range(u.n):
                call_with_backoff(lambda: execute_call(
                    **common, messages=plan.messages, call_role=CallRole.single,
                    system=plan.system, skill_hash=plan.skill_hash, persist_text=persist))
                written += 1
        elif u.family == "cache":
            warm_once_read_many(
                **common, cached_system=plan.system, warm_message=plan.warm_message,
                read_messages=plan.read_messages * u.n, call_wrapper=call_with_backoff)
            written += 1 + u.n
        elif u.family == "multiturn":
            for _ in range(u.n):
                recs = call_with_backoff(lambda: run_multiturn_session(**common, turns=plan.turns))
                written += len(recs)
        elif u.family == "payload":
            payload_text = plan.messages[2]["content"][0]["content"]
            trt = counter(u.config.model_id, payload_text)     # free count_tokens at run setup
            for _ in range(u.n):
                call_with_backoff(lambda: execute_payload_call(
                    **common, messages=plan.messages, tools=plan.tools, tool_result_tokens=trt))
                written += 1
        else:
            raise ValueError(f"unknown family {u.family!r}")
    return written


if __name__ == "__main__":
    raise SystemExit(main())
