# analysis/ — H1 variance computation

**Implemented in `h1.py`** — run: `uv run python -m analysis.h1 results/<run-id>` (headline H1 result
computed 2026-06-25; outputs in `output/`). Reads `results/<run-id>/records.jsonl`, applies `prices/`
scalars, computes per-cell distributions.

- **Headline H1 metric:** coefficient of variation per cell on the **dollar-weighted composite**.
- **Per-component CoV** (input / output / cache-read / cache-write / thinking) to localize *where*
  the variance lives.
- Bandable if CoV < ~15–20% (charter threshold); otherwise flag for distribution-monitoring.
- Report **distributions** — mean, median, spread, **and tail** — not point estimates.
- Keep **within-cell** variance strictly separate from **between-model** variance (the latter is
  the over-service signal, not an H1 result).
- Cache cells: write cost and read distribution reported separately (never mixed).
- Multi-turn cells: session-total CoV is the headline; inspect per-turn to see if late-turn
  compounding drives a breach.

Prices enter **only here**, never in stored records. Outputs (tables, plots) go to `analysis/output/`.

## Correlation cuts — `correlations.py` (descriptive secondary analysis)

**Run:** `uv run python -m analysis.correlations` (reads the enriched `output/h1_cov.csv` produced by
`h1.py`; **no pricing** — it only regroups CoVs h1.py already computed). This is **exploratory /
descriptive analysis of existing data — NOT a hypothesis test and NOT a change to H1** (charter
pre-registration discipline). Three cuts:

- **by model_role** — flat medians ⇒ no model is intrinsically noisier (the over-service signal is a
  *different* axis and is excluded).
- **by cost axis** (labels transcribed from SPEC §3) — the degrees-of-freedom ladder
  (thinking ≫ turns > cached-context > output > input ≈ payload).
- **input/output decomposition** — the frozen fixture makes input (and cache-read) deterministic
  (CoV ≈ 0), so within-cell variance is entirely an output-component effect and reduces to the
  identity **`CoV_composite = CoV_output × output cost share`**.

Outputs to `output/`: `correlations_by_model.csv`, `correlations_by_axis.csv`, `decomposition.csv`,
`decomposition_scatter.png`, `cov_by_axis.png`, and the write-up `correlations-findings.md`.
Depends on `h1.py` having been run first (it consumes the enriched CSV, including the per-component
`cov_input` / `cov_output` / `cov_cache_read` columns).

## Quality judge — `quality.py` (Phase-1c H5/H6)

**Run:** `uv run python -m analysis.quality results/<run-id> [--run-judge]` (loads the FROZEN,
hash-pinned judge instrument `fixtures/judge/manifest.yaml`; see `docs/phase1c-judge-spec.md`). The
quality axis for the determinism A/B — what the token harness can't measure ("Haiku does it
*identically*").

- **Deterministic graders (free, always run):** #4 exact-match to the gold label; #6/#9 objective
  checks (word counts, hashtags, section presence) in code, never by the LLM.
- **Frozen LLM-judge (`--run-judge`; billable Opus calls — off by default):** the semantic rubric
  checks at **K=3 majority** with a ≥2/3 **agreement floor** (low-confidence items flagged, not
  averaged); blind, seed-randomized **pairwise** (Haiku vs Opus) on **rubric-passing pairs only**,
  with the excluded share reported, and the ≤10-pp equivalence test.
- **Human spot-check:** a stratified ≥10% blinded sample + de-blinding key (`compute_agreement`).
- `judge_hash` is recomputed and re-checked against the manifest on every run (replay guard).

Outputs to `output/`: `quality_rubric.csv` (H5 floor), `quality_pairwise.csv` (H6),
`quality_spotcheck.csv` (+ `_key.csv`), and `quality-findings.md`. H5's token side
(`CoV_output` + mean output tokens) lives in **`h5.py`** (below); `quality.py` owns only the
quality axis.

## H5 determinism contrast — `h5.py` (Phase-1c token side)

**Run:** `uv run python -m analysis.h5 results/<run-id>` → `output/h5_determinism.csv` + a printed
contrast table. Computes the **skill-off vs skill-on** output-component contrast for the 1c factorial:
per (task, band, model, **skill_arm**) it reports `CoV_output` + mean output tokens, then the on/off
**relative CoV reduction** and **mean delta**, with an H5 win flag = *CoV_output ↓ ≥25% relative AND
mean output not raised* (judge-spec §4); #4 is the placebo.

Why separate from `h1.py`: `h1.py` keys cells on (task, band, model_role) and is **not arm-aware** —
on the 1c data it would merge a cell's 20 skill-off + 20 skill-on records into one bimodal
distribution and report a meaningless CoV. `h5.py` **reuses h1.py's canonical primitives**
(`record_cost`, `component_costs`, `cov` — same cost model, same sample-stdev CoV) and only adds the
`skill_arm` axis + the contrast, so the number is computed identically to the H1 headline. Read on
the **output component only**, never the composite (the skill's fixed `system` block would otherwise
deflate composite CoV via Lever B and counterfeit an H5 win — charter §3b).
