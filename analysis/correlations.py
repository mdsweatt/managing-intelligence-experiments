"""analysis/correlations.py — exploratory correlation cuts over the Phase-1a H1 table.

**DESCRIPTIVE secondary analysis** of already-collected data — NOT a hypothesis test and NOT a
change to H1 (charter pre-registration discipline). It consumes the enriched
``analysis/output/h1_cov.csv`` (produced by ``analysis.h1``) and aggregates the *already-computed*
within-cell CoVs three ways:

  1. **by model_role** — is any model intrinsically noisier? (expect flat medians → no main effect;
     spread is the over-service signal, a different axis, NOT an H1 result).
  2. **by cost axis** — does within-cell variance track the load axis / the model's degrees of
     freedom? Axis labels are transcribed verbatim from SPEC §3's "cost axis" column.
  3. **input/output decomposition** — *where* does the variance live? The frozen fixture makes the
     input (and cache-read) components deterministic (CoV ≈ 0), so the whole within-cell composite
     CoV reduces to an identity:

         CoV_composite = CoV_output × (output's share of the cell's cost)

     i.e. a task is bandable either because its output barely varies (low CoV_output) **or** because
     output is a small slice of cost (a big fixed/cached context dilutes it). The decomposition
     table reports CoV_output and the implied output cost share (= composite / output CoV).

No pricing happens here — dollars stay isolated in ``analysis.h1`` (charter §4); this module only
regroups CoVs that h1.py already computed.

Run:  uv run python -m analysis.correlations [--in analysis/output/h1_cov.csv --out analysis/output]
"""

from __future__ import annotations

import argparse
import csv
import statistics as st
from collections import defaultdict
from pathlib import Path
from typing import Callable, Optional

# Cost axis per task — transcribed verbatim from docs/SPEC.md §3 ("cost axis" column). This is
# pre-existing run-matrix metadata, decided before any data; it is NOT a post-hoc judgment.
TASK_AXIS: dict[int, str] = {
    1: "input", 2: "input", 3: "input", 4: "input", 5: "input",
    6: "output", 7: "input", 8: "input", 9: "output",
    10: "cached-context", 11: "cached-context", 12: "cached-context",
    15: "thinking", 16: "turns", 17: "turns",
    18: "payload", 19: "payload", 22: "output",
}

# D3 deterministic-output tasks (exact / schema match) — docs/SPEC.md §1 decision D3.
DETERMINISTIC: frozenset[int] = frozenset({4, 5, 8})

# Numeric columns in h1_cov.csv (blank for families where a component does not apply).
_NUMERIC = ("mean_cost_usd", "cov_composite", "cov_input", "cov_output", "cov_cache_read")


def _f(x: Optional[str]) -> Optional[float]:
    """Parse a CSV cell to float, treating blank/missing as None (component N/A for that family)."""
    return float(x) if x not in (None, "") else None


def load_rows(path: Path) -> list[dict]:
    """Load the enriched h1_cov.csv, coercing numerics and tagging each row with its cost axis."""
    rows: list[dict] = []
    with path.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            for k in _NUMERIC:
                r[k] = _f(r.get(k))
            r["task_id"] = int(r["task_id"])
            r["axis"] = TASK_AXIS[r["task_id"]]
            r["deterministic"] = r["task_id"] in DETERMINISTIC
            rows.append(r)
    return rows


# --------------------------------------------------------------------------- grouping

def group_stats(rows: list[dict], key: Callable[[dict], str],
                field: str = "cov_composite") -> dict[str, dict]:
    """n / median / mean / max of `field` per group (rows with a defined value only)."""
    groups: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        v = r.get(field)
        if v is not None:
            groups[key(r)].append(v)
    return {
        k: {"n": len(vs), "median": st.median(vs), "mean": st.mean(vs), "max": max(vs)}
        for k, vs in groups.items()
    }


def decomposition(rows: list[dict]) -> list[dict]:
    """Per-cell input/output split for cells that have an output-component CoV (standard/payload +
    cache; multi-turn has no session-level component split and is skipped).

    output_cost_share = CoV_composite / CoV_output — exact because every non-output component is
    deterministic within a cell (cov_input ≈ 0, cov_cache_read ≈ 0). It is the fraction of the
    cell's cost that the variable output accounts for.
    """
    out: list[dict] = []
    for r in rows:
        co = r["cov_output"]
        if co is None:                      # multi-turn: no component split at session level
            continue
        share = (r["cov_composite"] / co) if co else None
        out.append({
            "task_id": r["task_id"], "band": r["band"], "model_role": r["model_role"],
            "task_name": r["task_name"], "family": r["family"], "axis": r["axis"],
            "cov_input": r["cov_input"], "cov_cache_read": r["cov_cache_read"],
            "cov_output": co, "cov_composite": r["cov_composite"],
            "output_cost_share": share,
        })
    out.sort(key=lambda d: d["cov_output"], reverse=True)
    return out


# --------------------------------------------------------------------------- output

def _write_group_csv(path: Path, label: str, stats: dict[str, dict], order: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([label, "n", "median_cov", "mean_cov", "max_cov"])
        for k in order:
            s = stats[k]
            w.writerow([k, s["n"], f"{s['median']:.6f}", f"{s['mean']:.6f}", f"{s['max']:.6f}"])


def _write_decomposition_csv(path: Path, rows: list[dict]) -> None:
    cols = ["task_id", "band", "model_role", "task_name", "family", "axis",
            "cov_input", "cov_cache_read", "cov_output", "cov_composite", "output_cost_share"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            w.writerow([r.get(c) for c in cols])


def _plot_decomposition(rows: list[dict], path: Path) -> None:
    """Scatter CoV_output (x) vs CoV_composite (y). Points fall on/below y=x: the vertical drop is
    the deterministic-mass dilution (composite = output_CoV × output_cost_share)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fam_color = {"standard/payload": "#4C72B0", "cache": "#55A868"}
    xs = [r["cov_output"] * 100 for r in rows]
    ys = [r["cov_composite"] * 100 for r in rows]
    colors = [fam_color.get(r["family"], "#888") for r in rows]

    fig, ax = plt.subplots(figsize=(8, 8))
    lim = max(xs + ys) * 1.08
    ax.plot([0, lim], [0, lim], color="#bbb", ls="--", lw=1, label="y = x (output is 100% of cost)")
    ax.scatter(xs, ys, c=colors, s=42, edgecolor="white", linewidth=0.6, zorder=3)
    for r in rows:                                  # annotate the #18 opus/sonnet showcase
        if r["task_id"] == 18:
            ax.annotate(f"#18-{r['model_role']}", (r["cov_output"] * 100, r["cov_composite"] * 100),
                        textcoords="offset points", xytext=(7, -2), fontsize=8)
    ax.set_xlabel("CoV of the OUTPUT component (%)")
    ax.set_ylabel("CoV of the $-weighted composite (%)")
    ax.set_title("Where within-cell variance lives — input CoV ≈ 0, output carries it all\n"
                 "(drop below y=x = dilution by the fixed/cached context)")
    from matplotlib.patches import Patch
    handles = [Patch(color=c, label=f) for f, c in fam_color.items()]
    handles += [plt.Line2D([], [], color="#bbb", ls="--", label="y = x")]
    ax.legend(handles=handles, fontsize=8, loc="upper left")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def _plot_by_axis(stats: dict[str, dict], path: Path) -> None:
    """Bar of median composite CoV per cost axis, sorted ascending (the latitude ladder)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    order = sorted(stats, key=lambda k: stats[k]["median"])
    xs = range(len(order))
    ys = [stats[k]["median"] * 100 for k in order]

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(xs, ys, color="#4C72B0")
    ax.axhline(15, color="#888", ls="--", lw=1, label="15% bandable")
    ax.axhline(20, color="#C44E52", ls="--", lw=1, label="20% kill-edge")
    ax.set_xticks(list(xs))
    ax.set_xticklabels([f"{k}\n(n={stats[k]['n']})" for k in order], fontsize=8)
    ax.set_ylabel("median within-cell CoV (%)")
    ax.set_title("Within-cell variance by cost axis (Phase 1a) — the degrees-of-freedom ladder")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def _print_summary(rows: list[dict], by_model: dict, by_axis: dict, decomp: list[dict]) -> None:
    line = "=" * 76
    print(line)
    print("Phase-1a correlation cuts (DESCRIPTIVE — not a hypothesis test)")
    print(line)

    print("\n[1] by model_role — is any model intrinsically noisier? (flat medians ⇒ no main effect)")
    for k in sorted(by_model, key=lambda k: by_model[k]["median"]):
        s = by_model[k]
        print(f"     {k:8s} n={s['n']:2d}  median {s['median']:5.1%}  mean {s['mean']:5.1%}  max {s['max']:5.1%}")

    print("\n[2] by cost axis — the degrees-of-freedom ladder (ascending median CoV)")
    for k in sorted(by_axis, key=lambda k: by_axis[k]["median"]):
        s = by_axis[k]
        print(f"     {k:15s} n={s['n']:2d}  median {s['median']:5.1%}  mean {s['mean']:5.1%}  max {s['max']:5.1%}")

    std = [r for r in rows if r["family"] == "standard/payload" and r["cov_input"] is not None]
    cin = [r["cov_input"] for r in std]
    print("\n[3] input/output decomposition — where the variance lives")
    print(f"     standard/payload cells: cov_input  min {min(cin):.4f} · max {max(cin):.4f}  "
          f"(frozen fixture ⇒ input is deterministic)")
    print("     ⇒ CoV_composite = CoV_output × (output's cost share). Highest output CoV:")
    for r in decomp[:5]:
        sh = f"{r['output_cost_share']:.0%}" if r["output_cost_share"] is not None else " n/a"
        print(f"        {r['task_id']:>2}-{r['band']:<4}-{r['model_role']:<6} {r['axis']:<14} "
              f"out-CoV {r['cov_output']:5.1%}  composite {r['cov_composite']:5.1%}  out-share {sh}")


# --------------------------------------------------------------------------- main

def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="analysis.correlations",
                                description="Descriptive correlation cuts over the Phase-1a H1 table")
    p.add_argument("--in", dest="in_path", default="analysis/output/h1_cov.csv",
                   help="enriched h1_cov.csv (from analysis.h1)")
    p.add_argument("--out", default="analysis/output")
    a = p.parse_args(argv)

    rows = load_rows(Path(a.in_path))
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)

    by_model = group_stats(rows, lambda r: r["model_role"])
    by_axis = group_stats(rows, lambda r: r["axis"])
    decomp = decomposition(rows)

    _write_group_csv(out / "correlations_by_model.csv", "model_role", by_model,
                     sorted(by_model, key=lambda k: by_model[k]["median"]))
    _write_group_csv(out / "correlations_by_axis.csv", "cost_axis", by_axis,
                     sorted(by_axis, key=lambda k: by_axis[k]["median"]))
    _write_decomposition_csv(out / "decomposition.csv", decomp)
    _plot_decomposition(decomp, out / "decomposition_scatter.png")
    _plot_by_axis(by_axis, out / "cov_by_axis.png")

    _print_summary(rows, by_model, by_axis, decomp)
    print(f"\nwrote: {out/'correlations_by_model.csv'} · {out/'correlations_by_axis.csv'} · "
          f"{out/'decomposition.csv'} · {out/'decomposition_scatter.png'} · {out/'cov_by_axis.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
