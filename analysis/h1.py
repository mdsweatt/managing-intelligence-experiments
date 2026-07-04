"""analysis/h1.py — H1 (Stability) variance computation for the Phase-1a dataset.

Reads a run's `records.jsonl`, applies `prices/` scalars **here and only here** (charter §4),
and computes the headline H1 metric: **within-cell coefficient of variation (CoV) on the
dollar-weighted composite**, plus per-component CoV to localise where the variance lives.

Family-specific handling, per CLAUDE.md + analysis/README.md:
  - **cache (#10–12):** the warm-write cost and the read distribution are reported SEPARATELY —
    never mixed (a write+reads mixture is bimodal and its CoV is meaningless). Cell headline = the
    read distribution's CoV.
  - **multi-turn (#16/17):** headline = session-total CoV (sum the composite across a session's
    turns); per-turn CoV is also reported to see where variance enters (late-turn compounding).
  - **standard / payload:** straightforward CoV over the N identical runs.

Within-cell variance is kept strictly separate from between-model variance (the latter is the
over-service signal, NOT an H1 result), so nothing here compares across model_role.

Run:  uv run python -m analysis.h1 results/<run-id> [--prices prices/prices-2026-06.yaml]
"""

from __future__ import annotations

import argparse
import json
import statistics as st
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

from harness.config import ModelPrices, load_prices

# Charter §3 H1 kill-condition threshold: CoV under ~15–20% → bandable; over → distribution-monitoring.
TIGHT = 0.15      # comfortably bandable
OUTER = 0.20      # kill-condition outer edge


# --------------------------------------------------------------------------- cost model

def record_cost(usage: dict[str, Any], mp: ModelPrices) -> float:
    """Dollar-weighted composite cost of one record's usage vector (prices are $/1M tokens).

    The three input components (fresh input / cache-read / cache-creation) are mutually exclusive
    and additive; output is priced once. ``thinking_tokens`` and ``tool_result_tokens`` are NOT
    added — they are subsets already folded into output_tokens / input_tokens respectively
    (schema.py invariants 4 & 5), so adding them would double-count.
    """
    return (
        usage["input_tokens"] * mp.input
        + usage["output_tokens"] * mp.output
        + usage.get("cache_read_input_tokens", 0) * mp.cache_read
        + usage.get("cache_creation_input_tokens", 0) * mp.cache_write_5m
    ) / 1_000_000


def component_costs(usage: dict[str, Any], mp: ModelPrices) -> dict[str, float]:
    """Per-component dollar cost — to localise *where* the within-cell variance lives."""
    return {
        "input": usage["input_tokens"] * mp.input / 1e6,
        "output": usage["output_tokens"] * mp.output / 1e6,
        "cache_read": usage.get("cache_read_input_tokens", 0) * mp.cache_read / 1e6,
        "cache_write": usage.get("cache_creation_input_tokens", 0) * mp.cache_write_5m / 1e6,
    }


def cov(values: list[float]) -> Optional[float]:
    """Sample coefficient of variation (stdev/mean). None if undefined (n<2 or mean==0)."""
    if len(values) < 2:
        return None
    mean = st.mean(values)
    if mean == 0:
        return 0.0
    return st.stdev(values) / mean


def split_sessions(recs: list[dict]) -> list[list[dict]]:
    """Split an ordered multi-turn cell into sessions on each turn_index==0 (records are in
    append order, and each session writes turn 0,1,…,k consecutively)."""
    sessions: list[list[dict]] = []
    cur: list[dict] = []
    for r in recs:
        if r.get("turn_index") == 0 and cur:
            sessions.append(cur)
            cur = []
        cur.append(r)
    if cur:
        sessions.append(cur)
    return sessions


# --------------------------------------------------------------------------- loading / grouping

def cell_key(r: dict) -> tuple:
    c = r["cell_id"]
    return (c["task_id"], c["band"], c["model_role"])


def load_cells(records_path: Path) -> dict[tuple, list[dict]]:
    """Group records by cell, preserving file (append) order within each cell."""
    cells: dict[tuple, list[dict]] = defaultdict(list)
    with records_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                r = json.loads(line)
                cells[cell_key(r)].append(r)
    return cells


def family_of(recs: list[dict]) -> str:
    roles = {r["call_role"] for r in recs}
    if roles & {"read", "write"}:
        return "cache"
    if any(r.get("turn_index") is not None for r in recs):
        return "multiturn"
    return "standard/payload"


# --------------------------------------------------------------------------- per-cell analysis

def analyse_cell(recs: list[dict], prices) -> dict:
    """Compute the H1 metrics for one cell, with family-appropriate handling."""
    fam = family_of(recs)
    mp = prices.models[recs[0]["model_id"]]
    task_id, band, model_role = cell_key(recs[0])
    base = {
        "task_id": task_id, "band": band, "model_role": model_role,
        "task_name": recs[0]["cell_id"]["task_name"], "family": fam,
        "model_id": recs[0]["model_id"],
    }

    if fam == "cache":
        reads = [r for r in recs if r["call_role"] == "read"]
        writes = [r for r in recs if r["call_role"] == "write"]
        read_costs = [record_cost(r["usage"], mp) for r in reads]
        write_costs = [record_cost(r["usage"], mp) for r in writes]
        # headline = the read distribution (write reported separately, never mixed in)
        base.update(
            n=len(reads),
            mean_cost_usd=st.mean(read_costs),
            cov_composite=cov(read_costs),
            cov_output=cov([component_costs(r["usage"], mp)["output"] for r in reads]),
            cov_cache_read=cov([component_costs(r["usage"], mp)["cache_read"] for r in reads]),
            write_cost_usd=st.mean(write_costs) if write_costs else None,
            note="headline=read distribution; write cost separate",
        )
        return base

    if fam == "multiturn":
        sessions = split_sessions(recs)
        session_totals = [sum(record_cost(t["usage"], mp) for t in s) for s in sessions]
        # per-turn: CoV of each turn position across sessions
        per_turn = defaultdict(list)
        for s in sessions:
            for t in s:
                per_turn[t["turn_index"]].append(record_cost(t["usage"], mp))
        base.update(
            n=len(sessions),
            turns=max(len(s) for s in sessions),
            mean_cost_usd=st.mean(session_totals),
            cov_composite=cov(session_totals),          # headline = session-total CoV
            cov_per_turn={t: cov(v) for t, v in sorted(per_turn.items())},
            note="headline=session-total CoV; per-turn shows where variance enters",
        )
        return base

    # standard / payload
    costs = [record_cost(r["usage"], mp) for r in recs]
    comps = [component_costs(r["usage"], mp) for r in recs]
    base.update(
        n=len(recs),
        mean_cost_usd=st.mean(costs),
        cov_composite=cov(costs),
        cov_input=cov([c["input"] for c in comps]),
        cov_output=cov([c["output"] for c in comps]),
    )
    return base


def band_verdict(cov_composite: Optional[float]) -> str:
    if cov_composite is None:
        return "n/a"
    if cov_composite < TIGHT:
        return "tight"            # comfortably bandable
    if cov_composite < OUTER:
        return "borderline"       # within the kill-condition window
    return "NOT-bandable"         # breaches the kill-condition


# --------------------------------------------------------------------------- main

def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="analysis.h1", description="H1 within-cell CoV (Phase 1a)")
    p.add_argument("run_dir", help="results/<run-id> directory containing records.jsonl")
    p.add_argument("--prices", default="prices/prices-2026-06.yaml")
    p.add_argument("--out", default="analysis/output")
    a = p.parse_args(argv)

    run_dir = Path(a.run_dir)
    prices = load_prices(a.prices)
    cells = load_cells(run_dir / "records.jsonl")
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)

    rows = [analyse_cell(recs, prices) for _, recs in sorted(cells.items())]
    for r in rows:
        r["verdict"] = band_verdict(r["cov_composite"])

    # ---- main CSV: one row per cell ----
    import csv
    # Headline columns first (byte-stable prefix — the committed Phase-6 artifact), then the
    # per-component CoV decomposition appended (already computed in analyse_cell; missing keys for a
    # given family — e.g. cov_input on cache/multiturn — write blank via r.get).
    cols = ["task_id", "band", "model_role", "task_name", "family", "model_id",
            "n", "mean_cost_usd", "cov_composite", "verdict",
            "cov_input", "cov_output", "cov_cache_read"]
    with (out / "h1_cov.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            w.writerow([r.get(c) for c in cols])

    # ---- cache write-vs-read CSV (kept separate, per the cache invariant) ----
    with (out / "cache_write_vs_read.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["task_id", "band", "model_role", "write_cost_usd", "read_mean_cost_usd", "read_cov"])
        for r in rows:
            if r["family"] == "cache":
                w.writerow([r["task_id"], r["band"], r["model_role"],
                            r.get("write_cost_usd"), r["mean_cost_usd"], r["cov_composite"]])

    # ---- multi-turn per-turn CSV ----
    with (out / "multiturn_per_turn.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["task_id", "band", "model_role", "turn_index", "cov"])
        for r in rows:
            if r["family"] == "multiturn":
                for t, c in r["cov_per_turn"].items():
                    w.writerow([r["task_id"], r["band"], r["model_role"], t, c])

    # ---- plot: CoV per cell, sorted, with the kill-condition band ----
    _plot(rows, out / "h1_cov.png")

    _print_summary(rows)
    print(f"\nwrote: {out/'h1_cov.csv'} · {out/'cache_write_vs_read.csv'} · "
          f"{out/'multiturn_per_turn.csv'} · {out/'h1_cov.png'}")
    return 0


def _plot(rows: list[dict], path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fam_color = {"standard/payload": "#4C72B0", "cache": "#55A868", "multiturn": "#C44E52"}
    data = sorted([r for r in rows if r["cov_composite"] is not None], key=lambda r: r["cov_composite"])
    xs = range(len(data))
    ys = [r["cov_composite"] * 100 for r in data]
    colors = [fam_color[r["family"]] for r in data]

    fig, ax = plt.subplots(figsize=(13, 6))
    ax.bar(xs, ys, color=colors)
    ax.axhline(TIGHT * 100, color="#888", ls="--", lw=1, label=f"{TIGHT:.0%} comfortably bandable")
    ax.axhline(OUTER * 100, color="#C44E52", ls="--", lw=1, label=f"{OUTER:.0%} kill-condition edge")
    ax.set_ylabel("within-cell CoV of dollar-weighted composite (%)")
    ax.set_xlabel("cell (sorted by CoV)")
    ax.set_title("H1 — within-cell run-to-run variance, Phase 1a (N=20/cell)")
    from matplotlib.patches import Patch
    handles = [Patch(color=c, label=f) for f, c in fam_color.items()]
    handles += [plt.Line2D([], [], color="#888", ls="--", label=f"{TIGHT:.0%} bandable"),
                plt.Line2D([], [], color="#C44E52", ls="--", label=f"{OUTER:.0%} kill-edge")]
    ax.legend(handles=handles, fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def _print_summary(rows: list[dict]) -> None:
    valid = [r for r in rows if r["cov_composite"] is not None]
    covs = [r["cov_composite"] for r in valid]
    by_verdict = defaultdict(int)
    for r in valid:
        by_verdict[r["verdict"]] += 1
    print("=" * 72)
    print(f"H1 (Stability) — Phase 1a · {len(rows)} cells · within-cell CoV on $-weighted composite")
    print("=" * 72)
    print(f"  cells: {len(valid)} with defined CoV "
          f"({len(rows)-len(valid)} deterministic/zero-mean → CoV n/a)")
    print(f"  CoV   : min {min(covs):.1%} · median {st.median(covs):.1%} · "
          f"mean {st.mean(covs):.1%} · max {max(covs):.1%}")
    print(f"  verdict (charter threshold {TIGHT:.0%}/{OUTER:.0%}):")
    for v in ("tight", "borderline", "NOT-bandable"):
        print(f"     {v:13s}: {by_verdict.get(v,0):2d}")
    worst = sorted(valid, key=lambda r: r["cov_composite"], reverse=True)[:6]
    print("  noisiest cells (CoV desc):")
    for r in worst:
        print(f"     {r['task_id']:>2}-{r['band']:<4}-{r['model_role']:<6} {r['family']:<16} "
              f"CoV {r['cov_composite']:5.1%}  {r['verdict']}")


if __name__ == "__main__":
    raise SystemExit(main())
