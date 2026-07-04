"""analysis/h5.py — H5 (Determinism via skill) token-side analysis for the Phase-1c factorial.

Charter §3 **H5**: a frozen output skill lowers **output-token variance** (and/or mean output) vs
the calibrated-loose prompt, holding model/tokenizer/input fixed. Read on the **output component
only** — never the composite (the skill's fixed ~250-400-tok system block mechanically deflates
composite CoV via "Lever B" and would counterfeit an H5 win; judge-spec §4).

Why a separate module from `h1.py`: `h1.py` keys cells on (task, band, model_role) and is **not
arm-aware** — on the 1c factorial it would merge the 20 skill-off + 20 skill-on records into one
bimodal cell and report a meaningless CoV. This module adds the `skill_arm` axis and the on-vs-off
contrast, while **reusing h1.py's canonical cost model + sample-stdev CoV** (`record_cost`,
`component_costs`, `cov`) so the number is computed identically to the H1 headline.

H5 win per cell (judge-spec §4): skill-on lowers `CoV_output` by **≥ 25% relative** AND does **not
raise** mean output tokens. #4 is the placebo (deterministic ~7-tok label; CoV≈0 both arms) — the
skill must not move it.

Run:  uv run python -m analysis.h5 results/<run-id> [--prices prices/prices-2026-06.yaml]
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics as st
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

from harness.config import load_prices
from analysis.h1 import record_cost, component_costs, cov

# Judge-spec §4 thresholds.
H5_COV_REL = 0.25       # skill-on must cut CoV_output by ≥25% relative
PLACEBO_PP = 0.05       # #4 placebo CoV must move < 5pp absolute


def arm_key(r: dict) -> tuple:
    c = r["cell_id"]
    return (c["task_id"], c["band"], c["model_role"], c["skill_arm"])


def cell_metrics(recs: list[dict], mp) -> dict[str, Any]:
    """Output-side metrics for one arm-cell: mean output tokens, CoV_output (canonical sample-stdev
    CoV of the output dollar component — identical to the CoV of output tokens, price cancels)."""
    out_dollars = [component_costs(r["usage"], mp)["output"] for r in recs]
    return {
        "n": len(recs),
        "mean_output_tokens": st.mean([r["usage"]["output_tokens"] for r in recs]),
        "cov_output": cov(out_dollars),
        "mean_cost_usd": st.mean([record_cost(r["usage"], mp) for r in recs]),
    }


def arm_cells(records: list[dict], prices) -> dict[tuple, dict]:
    """Group factorial records by (task, band, model, arm) and compute per-cell output metrics."""
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in records:
        groups[arm_key(r)].append(r)
    return {k: cell_metrics(v, prices.models[v[0]["model_id"]]) for k, v in groups.items()}


def _rel_reduction(cov_off: Optional[float], cov_on: Optional[float]) -> Optional[float]:
    if cov_off is None or cov_on is None or cov_off == 0:
        return None
    return (cov_off - cov_on) / cov_off


def h5_contrasts(cells: dict[tuple, dict]) -> list[dict]:
    """Pair skill-off vs skill-on for each (task, band, model); compute the H5 contrast + verdict.
    The 1d neutral-system arm (charter §5, Exp 1d H8) rides along as reporting columns only — the
    off/on contrast math is untouched, and a cell without the arm (every 1c cell) carries None."""
    pairs: dict[tuple, dict] = defaultdict(dict)
    for (task, band, model, arm), m in cells.items():
        pairs[(task, band, model)][arm] = m
    rows = []
    for (task, band, model), arms in sorted(pairs.items()):
        off, on = arms.get("off"), arms.get("on")
        if not off or not on:
            continue
        neutral = arms.get("neutral")
        rel = _rel_reduction(off["cov_output"], on["cov_output"])
        mean_delta = (on["mean_output_tokens"] - off["mean_output_tokens"]) / off["mean_output_tokens"] * 100 \
            if off["mean_output_tokens"] else None
        win = (rel is not None and rel >= H5_COV_REL
               and on["mean_output_tokens"] <= off["mean_output_tokens"])
        rows.append({
            "task_id": task, "band": band, "model_role": model,
            "n_off": off["n"], "n_on": on["n"],
            "cov_output_off": off["cov_output"], "cov_output_on": on["cov_output"],
            "cov_rel_reduction": rel,
            "mean_off": off["mean_output_tokens"], "mean_on": on["mean_output_tokens"],
            "mean_delta_pct": mean_delta,
            "h5_output_win": win,
            "n_neutral": neutral["n"] if neutral else None,
            "mean_neutral": neutral["mean_output_tokens"] if neutral else None,
            "cov_output_neutral": neutral["cov_output"] if neutral else None,
        })
    return rows


def load_records(records_path: Path) -> list[dict]:
    recs = []
    with records_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                r = json.loads(line)
                if r["cell_id"].get("role_label") == "factorial":
                    recs.append(r)
    return recs


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="analysis.h5", description="H5 determinism contrast (Phase 1c)")
    p.add_argument("run_dir", help="results/<run-id> directory containing records.jsonl")
    p.add_argument("--prices", default="prices/prices-2026-06.yaml")
    p.add_argument("--out", default="analysis/output")
    a = p.parse_args(argv)

    run_dir = Path(a.run_dir)
    prices = load_prices(a.prices)
    recs = load_records(run_dir / "records.jsonl")
    cells = arm_cells(recs, prices)
    rows = h5_contrasts(cells)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)

    cols = ["task_id", "band", "model_role", "n_off", "n_on",
            "cov_output_off", "cov_output_on", "cov_rel_reduction",
            "mean_off", "mean_on", "mean_delta_pct", "h5_output_win",
            "n_neutral", "mean_neutral", "cov_output_neutral"]   # 1d neutral arm; empty on 1c rows
    with (out / "h5_determinism.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(cols)
        for r in rows:
            w.writerow([r.get(c) for c in cols])

    _print_summary(rows)
    print(f"\nwrote: {out/'h5_determinism.csv'}")
    return 0


def _fmt(x, pct=False):
    if x is None:
        return "  —  "
    return f"{x*100:+6.1f}%" if pct else f"{x:6.3f}"


def _print_summary(rows: list[dict]) -> None:
    # The neutral columns print only when some row carries the 1d arm — a 1c run prints identically.
    has_neutral = any(r.get("n_neutral") is not None for r in rows)
    print("=" * 88)
    print("H5 (Determinism via skill) — Phase 1c · output-component CoV, skill-off vs skill-on")
    print(f"   win = CoV_output ↓ ≥{H5_COV_REL:.0%} relative AND mean output not raised (judge-spec §4)")
    print("=" * 88)
    mean_ntl_h = f"{'mean_ntl':>9} " if has_neutral else ""
    cov_ntl_h = f"{'cov_ntl':>7} " if has_neutral else ""
    print(f"{'task':>4} {'model':>7} | {'mean_off':>9} {mean_ntl_h}{'mean_on':>9} {'Δmean':>8} | "
          f"{'cov_off':>7} {cov_ntl_h}{'cov_on':>7} {'cov_rel↓':>8} | win")
    for r in rows:
        placebo = " (placebo)" if r["task_id"] == 4 else ""
        mean_ntl = cov_ntl = ""
        if has_neutral:   # a row without the arm (e.g. the #4 placebo) shows — in the neutral slots
            mn = r.get("mean_neutral")
            mean_ntl = (f"{mn:>9.1f}" if mn is not None else f"{'—':>9}") + " "
            cov_ntl = _fmt(r.get("cov_output_neutral")) + " "
        print(f"{r['task_id']:>4} {r['model_role']:>7} | {r['mean_off']:>9.1f} {mean_ntl}{r['mean_on']:>9.1f} "
              f"{_fmt(r['mean_delta_pct']/100 if r['mean_delta_pct'] is not None else None, pct=True)} | "
              f"{_fmt(r['cov_output_off'])} {cov_ntl}{_fmt(r['cov_output_on'])} {_fmt(r['cov_rel_reduction'], pct=True)} | "
              f"{'YES' if r['h5_output_win'] else 'no':>3}{placebo}")
    gen = [r for r in rows if r["task_id"] != 4]
    wins = sum(1 for r in gen if r["h5_output_win"])
    print("-" * 88)
    print(f"  H5 output-win on {wins}/{len(gen)} generative cells (#4 placebo excluded).")


if __name__ == "__main__":
    raise SystemExit(main())
