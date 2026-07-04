"""analysis/h8.py — H8 (Scaffold-specific determinism) neutral-arm ratio for the Phase-1d factorial.

Charter §3 **H8**: H5's output-variance reduction is caused by the **scaffold's structure**
(format/schema + scope/length constraints), not the mere presence of a `system` block. Per
(task, band, model) cell running ALL THREE arms {off, neutral, on}, the length-matched
structure-free neutral block's share of the skill's tightening is

    R = (CoV_off − CoV_neutral) / (CoV_off − CoV_on)

computed on **CoV of the output component only** (like h5 — a fixed system block mechanically
deflates the composite and would counterfeit the read). Pre-registered verdict bands (charter §3
H8): **R < ⅓ → "supported"** (most tightening needs the actual structure); **⅓ ≤ R < ½ →
"ambiguous"**; **R ≥ ½ → "killed"** — the kill-condition: the neutral arm reproduces ≥ ½ of the
skill's CoV_output tightening, so part of H5's effect was "any system block / priming", not the
scaffold.

Scoring guard (charter: "scored only on cells where the skill itself produced a clear reduction —
R is unstable near the CoV floor"): a cell is scored=True only when the skill's relative CoV
reduction (cov_off − cov_on)/cov_off ≥ H5_COV_REL — imported from analysis.h5 (0.25, the H5
practically-meaningful bar; single source of truth). The charter does not pin the number; the 25%
operationalization is a build-time decision recorded in docs/phase1d-build-notes.md. R is None
(and the cell unscored) when cov_off is None/0, cov_off == cov_on (zero denominator), or any arm's
CoV is undefined. A 2-arm cell (no neutral) is skipped entirely — it carries no H8 information.

Run:  uv run python -m analysis.h8 results/<run-id> [--prices prices/prices-2026-06.yaml] \
          [--out analysis/output]
"""

from __future__ import annotations

import argparse
import csv
import statistics as st
from collections import defaultdict
from pathlib import Path
from typing import Optional

from harness.config import load_prices
from analysis.h5 import H5_COV_REL, arm_cells, load_records

# Charter §3 H8 pre-registered verdict bands on R.
SUPPORTED = 1 / 3
KILLED = 1 / 2

COLS = ["task_id", "band", "model_role", "n_off", "n_neutral", "n_on",
        "cov_output_off", "cov_output_neutral", "cov_output_on",
        "skill_rel_reduction", "scored", "R", "verdict"]


def verdict(r: float) -> str:
    if r < SUPPORTED:
        return "supported"
    if r < KILLED:
        return "ambiguous"
    return "killed"


def h8_rows(cells: dict[tuple, dict]) -> list[dict]:
    """Per (task, band, model) with all three arms: R + the near-floor scoring guard."""
    groups: dict[tuple, dict] = defaultdict(dict)
    for (task, band, model, arm), m in cells.items():
        groups[(task, band, model)][arm] = m
    rows = []
    for (task, band, model), arms in sorted(groups.items()):
        if not all(a in arms for a in ("off", "neutral", "on")):
            continue  # 2-arm cell: no neutral → no H8 read
        off, neu, on = arms["off"], arms["neutral"], arms["on"]
        c_off, c_neu, c_on = off["cov_output"], neu["cov_output"], on["cov_output"]
        # the skill's own relative reduction — the scoring-guard quantity (h5's contrast)
        rel = (c_off - c_on) / c_off if (c_off not in (None, 0) and c_on is not None) else None
        # R is undefined at a zero denominator (cov_off == cov_on) or any missing CoV
        if c_off in (None, 0) or c_on is None or c_neu is None or c_off == c_on:
            r_ratio = None
        else:
            r_ratio = (c_off - c_neu) / (c_off - c_on)
        scored = rel is not None and rel >= H5_COV_REL and r_ratio is not None
        rows.append({
            "task_id": task, "band": band, "model_role": model,
            "n_off": off["n"], "n_neutral": neu["n"], "n_on": on["n"],
            "cov_output_off": c_off, "cov_output_neutral": c_neu, "cov_output_on": c_on,
            "skill_rel_reduction": rel,
            "scored": scored,
            "R": r_ratio,
            "verdict": verdict(r_ratio) if scored else None,
        })
    return rows


def write_csv(rows: list[dict], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(COLS)
        for r in rows:
            w.writerow([r.get(c) for c in COLS])


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="analysis.h8", description="H8 neutral-arm ratio (Phase 1d)")
    p.add_argument("run_dir", help="results/<run-id> directory containing records.jsonl")
    p.add_argument("--prices", default="prices/prices-2026-06.yaml")
    p.add_argument("--out", default="analysis/output")
    a = p.parse_args(argv)

    prices = load_prices(a.prices)
    recs = load_records(Path(a.run_dir) / "records.jsonl")
    rows = h8_rows(arm_cells(recs, prices))
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    write_csv(rows, out / "h8_neutral.csv")

    _print_summary(rows)
    print(f"\nwrote: {out/'h8_neutral.csv'}")
    return 0


def _fmt(x):
    return f"{x:6.3f}" if x is not None else "  —  "


def _print_summary(rows: list[dict]) -> None:
    print("=" * 88)
    print("H8 (Scaffold-specific determinism) — Phase 1d · neutral-arm share of the skill's tightening")
    print(f"   R=(CoVoff−CoVneu)/(CoVoff−CoVon) on CoV_output · <{SUPPORTED:.2f} supported · "
          f"<{KILLED:.2f} ambiguous · ≥{KILLED:.2f} killed")
    print(f"   scored only where the skill's own reduction ≥ {H5_COV_REL:.0%} (near-floor guard; "
          "docs/phase1d-build-notes.md)")
    print("=" * 88)
    print(f"{'task':>4} {'model':>7} | {'cov_off':>7} {'cov_neu':>7} {'cov_on':>7} | "
          f"{'skill_rel↓':>10} {'R':>6} | verdict")
    for r in rows:
        rel = f"{r['skill_rel_reduction']*100:+8.1f}%" if r["skill_rel_reduction"] is not None else "    —    "
        print(f"{r['task_id']:>4} {r['model_role']:>7} | {_fmt(r['cov_output_off'])} "
              f"{_fmt(r['cov_output_neutral'])} {_fmt(r['cov_output_on'])} | "
              f"{rel} {_fmt(r['R'])} | {r['verdict'] or ('unscored' if not r['scored'] else '')}")
    scored = [r for r in rows if r["scored"]]
    print("-" * 88)
    for v in ("supported", "ambiguous", "killed"):
        print(f"  {v:10s}: {sum(1 for r in scored if r['verdict'] == v):2d}")
    if scored:
        print(f"  median R over {len(scored)} scored cells: {st.median(r['R'] for r in scored):.3f}")
    print(f"  3-arm cells left unscored by the guard: {len(rows) - len(scored)}")


if __name__ == "__main__":
    raise SystemExit(main())
