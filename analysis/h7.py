"""analysis/h7.py — H7 (Determinism ≠ cost — cap vs mandate) sign test for the Phase-1d factorial.

Charter §3 **H7**: a skill lowers output-token *variance* on any high-latitude task, but its effect
on **mean output tokens** — hence cost — has a sign predictable a priori: a scaffold that **caps**
(constrains output below the natural skill-off length) lowers mean output; one that **mandates**
(requires more structure/content than the natural output) raises it. This converts 1c's **post-hoc**
#6/#9 dissociation into an a-priori test: per (task, band, model) factorial pair, does the
pre-registered label predict the SIGN of Δ(mean output tokens) between skill-off and skill-on?

Read on the **output component only** (mean output tokens), like h5 — the skill's fixed system
block mechanically moves the input side, so a composite read would counterfeit the contrast.

Labels come **frozen from `runs/phase1d.yaml`** — set before the N=20 run per charter §3 H7 and
invariant 4 (no relabeling after data; the label is data-independent by construction). The core
functions take a plain `{task_id: label}` mapping so the math is testable without the file;
`main()` owns the yaml via `load_run_matrix` → `{task.id: task.h7_label}`. A task whose
`h7_label` is None (the #4 placebo, or a boundary-flagged task) is **excluded**: its row still
appears in the CSV but does not count toward the headline.

The kill-condition reads "sign prediction at/below chance or systematically inverted" — the
statistical interpretation belongs to the report; this module reports the counts.

Run:  uv run python -m analysis.h7 results/<run-id> --matrix runs/phase1d.yaml \
          [--prices prices/prices-2026-06.yaml] [--out analysis/output]
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from typing import Optional

from harness.config import load_prices, load_run_matrix
from analysis.h5 import arm_cells, load_records

# Charter §3 H7 sign rule: mandate → mean output UP ("+"), cap → mean output DOWN ("-").
PREDICTED_SIGN = {"mandate": "+", "cap": "-"}

COLS = ["task_id", "band", "model_role", "h7_label", "n_off", "n_on",
        "mean_off", "mean_on", "mean_delta_pct",
        "predicted_sign", "observed_sign", "hit", "excluded"]


def h7_rows(cells: dict[tuple, dict], labels: dict[int, Optional[str]]) -> list[dict]:
    """Pair skill-off vs skill-on per (task, band, model) — the neutral arm is H8's object,
    ignored here — and score the frozen label's sign prediction against Δ(mean output tokens)."""
    pairs: dict[tuple, dict] = defaultdict(dict)
    for (task, band, model, arm), m in cells.items():
        if arm in ("off", "on"):
            pairs[(task, band, model)][arm] = m
    rows = []
    for (task, band, model), arms in sorted(pairs.items()):
        off, on = arms.get("off"), arms.get("on")
        if not off or not on:
            continue
        label = labels.get(task)
        predicted = PREDICTED_SIGN.get(label)
        excluded = label is None
        mean_off, mean_on = off["mean_output_tokens"], on["mean_output_tokens"]
        observed = "0" if mean_on == mean_off else ("+" if mean_on > mean_off else "-")
        rows.append({
            "task_id": task, "band": band, "model_role": model,
            "h7_label": label,
            "n_off": off["n"], "n_on": on["n"],
            "mean_off": mean_off, "mean_on": mean_on,
            "mean_delta_pct": (mean_on - mean_off) / mean_off * 100 if mean_off else None,
            "predicted_sign": predicted, "observed_sign": observed,
            # an exact tie ("0") never matches "+"/"-" → counted as a miss, per pre-registration
            "hit": (predicted == observed) if not excluded else None,
            "excluded": excluded,
        })
    return rows


def label_counts(rows: list[dict]) -> dict[str, tuple[int, int]]:
    """(hits, total) per label group + overall — over non-excluded rows only (the headline)."""
    counts: dict[str, list[int]] = {"cap": [0, 0], "mandate": [0, 0], "overall": [0, 0]}
    for r in rows:
        if r["excluded"]:
            continue
        for key in (r["h7_label"], "overall"):
            counts[key][0] += 1 if r["hit"] else 0
            counts[key][1] += 1
    return {k: (h, t) for k, (h, t) in counts.items()}


def write_csv(rows: list[dict], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(COLS)
        for r in rows:
            w.writerow([r.get(c) for c in COLS])


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="analysis.h7", description="H7 cap/mandate sign test (Phase 1d)")
    p.add_argument("run_dir", help="results/<run-id> directory containing records.jsonl")
    p.add_argument("--matrix", required=True,
                   help="runs/phase1d.yaml — the FROZEN h7_label source (charter §3 H7, invariant 4)")
    p.add_argument("--prices", default="prices/prices-2026-06.yaml")
    p.add_argument("--out", default="analysis/output")
    a = p.parse_args(argv)

    labels = {t.id: t.h7_label for t in load_run_matrix(a.matrix).tasks}
    prices = load_prices(a.prices)
    recs = load_records(Path(a.run_dir) / "records.jsonl")
    rows = h7_rows(arm_cells(recs, prices), labels)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    write_csv(rows, out / "h7_sign.csv")

    _print_summary(rows)
    print(f"\nwrote: {out/'h7_sign.csv'}")
    return 0


def _print_summary(rows: list[dict]) -> None:
    print("=" * 88)
    print("H7 (Determinism ≠ cost) — Phase 1d · frozen cap/mandate label vs sign of Δ(mean output)")
    print("   labels frozen pre-run in runs/phase1d.yaml (charter §3 H7); a tie ('0') is a miss")
    print("=" * 88)
    print(f"{'task':>4} {'model':>7} {'label':>8} | {'mean_off':>9} {'mean_on':>9} {'Δmean':>8} | "
          f"{'pred':>4} {'obs':>3} | hit")
    for r in rows:
        d = r["mean_delta_pct"]
        delta = f"{d:+7.1f}%" if d is not None else "   —   "
        mark = "excl" if r["excluded"] else ("HIT" if r["hit"] else "miss")
        print(f"{r['task_id']:>4} {r['model_role']:>7} {r['h7_label'] or '—':>8} | "
              f"{r['mean_off']:>9.1f} {r['mean_on']:>9.1f} {delta} | "
              f"{r['predicted_sign'] or '—':>4} {r['observed_sign']:>3} | {mark}")
    counts = label_counts(rows)
    print("-" * 88)
    for g in ("cap", "mandate", "overall"):
        h, t = counts[g]
        print(f"  {g:8s}: {h}/{t} sign hits")
    excluded = [r for r in rows if r["excluded"]]
    if excluded:
        cells = ", ".join(f"#{r['task_id']}-{r['band']}-{r['model_role']}" for r in excluded)
        print(f"  excluded (h7_label=None, outside the headline): {cells}")


if __name__ == "__main__":
    raise SystemExit(main())
