# Managing Intelligence — Experiment 1 harness

Measures the **token economics of knowledge work** — what tasks cost in tokens, and how stable that cost is — to test whether task cost is bandable (H1). This serves a **provocation tool**, not a finance-grade instrument: ranges honest and non-embarrassing, not exact. **Denominate in tokens, not dollars** — price is a single scalar applied at analysis time only.

## Project state (as of 2026-07-04)

**Phases 0–6 complete (headline) — the Phase 1a run is captured and the headline H1 result is computed.** Python project under `uv` (pinned `uv.lock`, Python 3.12; `anthropic` SDK + pydantic v2 + pandas/matplotlib). Live API facts have been **verified against the running API** and the pinned docs reconciled — see `docs/live-verification-2026-06-16.md`. The capture contract + harness skeleton are built, adversarially reviewed, and proven live end-to-end. Fixture curation: **21 Phase-1a fixtures are frozen + hashed with measured token counts** (2026-06-21, record in `docs/fixture-freeze-2026-06-21.md`) — single-call 1–9, #15, the new **#22** (creative image-prompt generation, demand-driven per charter §5), cache #10–12 (M), multi-turn #16/#17, and payload #18/#19 (M); on-disk formats for cache/multi-turn/payload pinned in `fixtures/README.md` (#5-M's translate-M source is the ~7k-word *Europe 2031* scenario). The **L-band** artifacts (7-L, 8-L, cache-L, payload-L) remain deferred (owner). The **Phase 0 cost-gate pilot ran** (`results/run-20260621T171817Z-563d39/` — 52 calls, $4.62, clears $500); the **Phase 1a measurement run is complete** (`results/run-20260624T112122Z-cfa60e/` — 2,069 records across all four families, 14.05M tokens, ~17.2 h wall-clock; clean after a first attempt aborted ~25% in on a monthly API *usage limit* — separate from credit balance — and was re-run from scratch). `prices/prices-2026-06.yaml` is now **filled** (live-verified 2026-06-25) and the **headline H1 result is computed** (`analysis/h1.py` → `analysis/output/`; 62/67 cells band tight). **Phase 1c ran 2026-06-28** (`results/run-20260628T051203Z-53aa02/` — 360 records, **$2.94** measured; the frozen Opus judge then graded H5/H6). **Headline: H5 nuanced** — the skill cuts output-token variance and cuts *cost* on short-form #6, but on long-form #9 it tightens variance while *raising* length — and **H6 rejected**: scaffolded Haiku still loses to Opus 12–1 on #6, so tier still buys quality. See the Phase 1c line below + charter §0 state-note 2026-06-28. **Phase 1d ran 2026-07-02→03** (`results/run-20260702T203102Z-f704f0/` — 1,560 records, $24.57; cross-family Gemini judge via Batch API, $21.18; 144-item blind human panel). **Headline: H7 supported 24/24** (cap→cheaper, mandate→dearer — the skill's cost sign is predictable a priori), **H8 supported** (a structure-free system block reproduces ~none of the variance-tightening), and **H6: no verdict — the judge failed its human calibration** (54.9% ≈ chance; the failed ruler is the phase's primary methodological finding). See `docs/phase1d-report.md`. 299 tests green.

Phase progress (build order detailed under "Run procedure"):

- [x] **Phase 0 — Foundations & live verification.** `uv` env, `.env`, git; `harness/verify_live.py` ran and **corrected four pinned facts** — tokenizer is *not* shared (Opus 4.8 ≈ +35%), Opus rejects `temperature` (→ omit everywhere), Sonnet max-output is 128k, rate tier raised (~100k L-band now fits one call). `$500` hard ceiling set.
- [x] **Phase 1 — Capture contract** (`harness/schema.py`, `config.py`, `hashing.py`): the Pydantic record (raw `usage` verbatim + a typed projection validated against it) every record validates against, plus typed loaders for `runs/*.yaml` / `manifest.yaml` / `prices/*.yaml` and deterministic `config_hash` / `fixture_hash`. Fail-loud on missing provenance, mis-stamped hashes, truncated/refused `stop_reason`, cache misses, and out-of-vocabulary config. 67 tests; SDK field names pinned live (anthropic 0.109.2).
- [x] **Phase 2 — Harness skeleton** (`harness/client.py`, `guard.py`, `runner.py`): streaming capture (full usage + `request_id` + rate headers + timing), the hard call/token ceiling (attempts counted before the call; spend registered even if persistence fails), and `execute_call` / `warm_once_read_many` proven live end-to-end (`skeleton_demo.py`). Adversarially reviewed (8 fixes applied; backoff / config-snapshot / fsync deferred to Phase 5, noted in `harness/README.md`). 95 tests.
- [x] **Phase 3 — Curate Phase 1a fixtures** (draft → owner freezes; two token counts per fixture). `harness/fixtures.py` (measure two counts / classify band / cache-floor / verify) built. **21 Phase-1a fixtures frozen + hashed** (2026-06-21, `docs/fixture-freeze-2026-06-21.md`): tranche 1 (1–9 + #15, measured + re-verified), tranche 2 (cache #10–12 M, multi-turn #16/17, payload #18/19 M), plus **#22** (image-prompt generation, demand-driven). On-disk formats for cache/multi-turn/payload pinned in `fixtures/README.md` (#5-M re-sourced to the ~7k-word *Europe 2031* scenario). **Deferred** (owner): all L-band (7-L/8-L, cache-L, payload-L).
- [x] **Phase 4 — Phase 0 cost gate** (`runs/phase0.yaml`, the machine form of the `runs/phase0-calibration.yaml` spec) vs the $500 ceiling — **ran 2026-06-21** (`results/run-20260621T171817Z-563d39/` — 52 calls, $4.62; clears $500).
- [x] **Phase 5 — Phase 1a run** (committed flat N=20) — **ran 2026-06-24→25** (`results/run-20260624T112122Z-cfa60e/` — 2,069 records, every cell at N, zero quarantined, cache-hits asserted on all #10–12 reads, per-turn capture on #16/17, tool-result tokens on #18/19; ~17.2 h). First attempt hit a monthly *usage limit* at 24.7% (a Console setting separate from credit balance — lessons logged in [`RUN.md`](RUN.md)); re-run clean after the cap was raised.
- [x] **Phase 6 — Analysis** — **headline H1 result computed** (`analysis/h1.py` → `analysis/output/`): `prices/prices-2026-06.yaml` filled from **live 2026-06-25** pricing; within-cell CoV per cell on the dollar-weighted composite (+ per component), cache write/read kept separate, multi-turn session-total + per-turn. **Result: 62/67 cells band tight (CoV <15%; median 4.5%, max 20.1%), 4 borderline, 1 at the 20% kill-edge (#15 thinking-on).** The §3 prediction (variance tracks **fan-out**) is **untested** here — its high-fan-out cells (#13/14/20/21) are deferred to Phase 1b — and the noise found in these low-fan-out cells tracks **output latitude**, a driver §3 didn't name (logged as an *unpredicted* finding, not a confirmation — see the charter's 2026-06-26 correction). *Not* a hypothesis change. 144 tests green.

- [x] **Phase 1c — Determinism A/B (charter v0.6, H5/H6)** — the causal test of Lever A (does a well-defined skill buy lower output variance/cost and tier-agnostic quality?). The harness gained a skill axis + output capture (skill-off stays byte-identical to the pre-skill schema, so Phase 1a is untouched), `runs/phase1c.yaml` (skill {off,on} × model {Haiku,Sonnet,Opus} on #4/#6/#9). **Skills FROZEN** (`fixtures/skills/`); the **quality judge FROZEN** (`docs/phase1c-judge-spec.md` + `fixtures/judge/`: two prompts, `judge_hash` `d12c36a2…` pinned, Opus 4.8 surface live-verified `docs/live-verification-judge-2026-06-28.md`) with graders in `analysis/quality.py`. **Ran 2026-06-28** (`results/run-20260628T051203Z-53aa02/` — 360 records, all `end_turn`, 0 quarantined, **$2.94** vs the $15 ceiling; cost estimate `analysis/output/phase1c-cost-estimate.md` projected $2.96 point / $4.69 conservative). The frozen Opus judge graded H5/H6 (`analysis/quality.py --run-judge`, K=3). **Result: H5 nuanced** (token side in `analysis/h5.py` → `output/h5_determinism.csv`: skill cuts output CoV on #6 + #9-Sonnet/Opus and cuts *cost* on #6, but *raises* mean output on long-form #9; #4 placebo flat) and **H6 rejected** (`output/quality-findings.md`/`quality_pairwise.csv`: Opus preferred over Haiku 12–1 on #6 skill-on — tier still buys quality). Recorded in the charter §0 state-note 2026-06-28; 24-item blinded spot-check (`output/quality_spotcheck.csv`) awaits human validation. 199 tests green.
- [x] **Phase 1d — Determinism A/B, de-confounded + widened (charter v0.8, H7/H8 + H5/H6 re-test)** — **RUN + GRADED + HUMAN-CALIBRATED + REPORTED 2026-07-03** (`docs/phase1d-report.md`; charter 2026-07-03 state note). 78 cells × N=20 = 1,560 records, $24.57; judge via Batch API (quota pivot, instrument unchanged), $21.18. **H7 supported 24/24** (cap→cheaper, mandate→dearer, every model — the cost sign is predictable a priori); **H8 supported** (neutral block reproduces ~none of the variance-tightening, median R=−0.03 — determinism is the *structure*); **H5 variance half holds** (17/24 cells; #8 + #15-Sonnet inversions flagged); **H6: no verdict — the cross-family judge failed its human calibration** (54.9% ≈ chance vs the 144-item blind owner panel; adjudication: 83% construct fuzz / 0% judge error), so all faithful-gated reads are instrument-unvalidated and 1c's provisional rejection stands. The failed ruler is the phase's primary methodological finding: crisp ≠ calibrated. Possible 1e (construct-first judge, re-grade stored records) scoped in the report.

Phase **1b** (agentic #13/14/20/21) is deferred.

**Supplementary — descriptive, not pre-registration:** `analysis/correlations.py` →
`analysis/output/correlations-findings.md` — three exploratory cuts of the H1 table (by model, by
cost axis, input/output decomposition). No model is intrinsically noisier (flat medians); the axis
ladder runs **thinking ≫ turns > cached-context > output > input ≈ payload**; and within-cell
variance is entirely an output-component effect (`CoV_composite = CoV_output × output cost share`).
**Secondary analysis of existing data — NOT a hypothesis change.** 153 tests green.

## Document hierarchy (read in this order)

1. **`CLAUDE.md`** (root) — the **constitution**: invariants that always hold. Claude Code auto-loads it.
2. **`docs/charter.md`** — the **source of truth**: pre-registered hypotheses (H1–H8; H5/H6 = the Phase 1c determinism A/B, H7/H8 = the Phase 1d follow-on), kill-conditions, predictions, constructs.
3. **`docs/load-band-reference.md`** — the **fixture spine**: the six cost axes, the two fixture rules, per-task bands and selection proxies.
4. **`docs/SPEC.md`** — the **run matrix + capture contract**: pins the decisions the charter defers (D1/D2/D3), the Phase 0 cost gate, global config, the Phase 1a matrix, the record schema.

**Results layer (for readers here for the findings, start here instead):** the three phase reports —
`docs/phase1a-report.md` (H1 bandability), `docs/phase1c-report.md` (H5/H6 determinism A/B),
`docs/phase1d-report.md` (H7/H8 + the judge-calibration failure) — each points to its dataset and
run notes. The pre-registration layer above is how to check the reports weren't retrofitted.

`runs/*.yaml` is `SPEC.md` §3 made machine-readable — **the harness consumes the YAML, not the markdown table.**

`docs/product-vision.md` sits **downstream** of these four — the report→living-instrument product framing (feeds charter §10). It is **strategy, not pre-registration**; read it after the experiment docs, never as evidence for H1–H4.

## Layout

```
CLAUDE.md          constitution (root)
pyproject.toml     uv project + pinned deps (uv.lock, .python-version)
docs/              charter, load-band-reference, SPEC, live-verification-*, product-vision, prior-art/
fixtures/          frozen + hashed artifacts; manifest.yaml is the registry; README.md pins the on-disk call formats; skills/ = Exp-1c frozen skill scaffolds + manifest
harness/           verify_live · schema/config/hashing (contract) · client/guard/runner (skeleton) · fixtures (curation) · skeleton_demo (live proof)
runs/              machine matrices: phase0.yaml (+ phase0-calibration.yaml spec), phase1a.yaml,
                   phase1c.yaml + phase1c-pilot.yaml, phase1d.yaml + phase1d-pilot.yaml
results/           APPEND-ONLY captured data, one dir per run; never hand-edit (manifest below)
prices/            per-model $/token, dated; applied at analysis ONLY
analysis/          h1 (H1 variance) · h5/h7/h8 (1c/1d hypotheses) · quality.py (judge + panel)
                   · judge_gemini*.py (cross-family judge, interactive + Batch API) · output/ (committed CSVs/findings)
```

## Data manifest (`results/`)

One dir per run, append-only. Canonical hypothesis datasets are marked ★; the rest are gates,
pilots, and honest failures kept for the operational record.

| run dir | matrix | what it is | records | `response_text`? |
|---|---|---|---|---|
| `run-20260621T171817Z-563d39` | phase0 | Phase 0 cost gate | 52 | no |
| `run-20260624T031222Z-75dc13` | phase1a | aborted 1a attempt #1 (monthly usage limit — see `RUN.md`) | 500 | no |
| `run-20260624T062227Z-43d1d4` | phase1a | aborted 1a attempt #2 (same limit, ~24.7% in) | 512 | no |
| `run-20260624T112122Z-cfa60e` | phase1a | ★ Phase 1a H1 dataset | 2,069 | no |
| `run-20260628T043414Z-859f8e` | phase1c-pilot | 1c pilot | 12 | yes |
| `run-20260628T051203Z-53aa02` | phase1c | ★ Phase 1c H5/H6 dataset (judge: Opus 4.8) | 360 | yes |
| `run-20260702T133840Z-64d579` | phase1d-pilot | 1d skill-off design pilot (design input, never H-data) | 180 | yes |
| `run-20260702T203102Z-f704f0` | phase1d | ★ Phase 1d H7/H8 + H5/H6 dataset (judge: Gemini 3.1 Pro preview, cross-family) | 1,560 | yes |

`response_text` is persisted **only** where a quality judge grades outputs (1c/1d factorial cells);
all Phase 0/1a records are tokens-only by design (charter invariant 2, 1c-scoped exception).

## Run procedure

1. **Verify the time-sensitive API facts live** (CLAUDE.md "Verify live") — tokenizer sharing, cache minimums, max-output ceilings, `effort` levels, temperature-with-thinking. Don't trust the 2026-06-15 values blind. **✅ done 2026-06-16** — `harness/verify_live.py` → `docs/live-verification-2026-06-16.md`; re-run on each model release.
2. **Build the harness skeleton** and prove it end-to-end on one throwaway fixture: call → full usage capture → `config_hash` → cost-ceiling → cache-hit assertion.
3. **Curate fixtures** (frozen artifact + exact prompt per cell; register in `fixtures/manifest.yaml`, hash, set `frozen: true`). Start with Phase 1a discrete cells.
4. **Phase 0 — cost gate** (`runs/phase0.yaml`; spec form `runs/phase0-calibration.yaml`): small-N pilot over the cost-spanning subset → project full-matrix cost → gate the universal-Opus commitment by the pre-stated decision rule.
5. **Phase 1a run** (`runs/phase1a.yaml`): committed flat N; records to `results/<run-id>/`. Operator runbook: [`RUN.md`](RUN.md).
6. **Analysis**: CoV per cell on the dollar-weighted composite + per component; prices applied here.
7. **Phase 1c — Determinism A/B** (`runs/phase1c.yaml`, `fixtures/skills/`, judge `docs/phase1c-judge-spec.md`): skill {off,on} × model factorial on #4/#6/#9 + the frozen quality judge; tests charter H5/H6. Freeze the skills + judge (the harness refuses unfrozen ones), then run behind the spend ceiling; then `analysis/h5.py` (H5 token side) + `analysis/quality.py --run-judge` (H6). **Ran 2026-06-28** (`results/run-20260628T051203Z-53aa02/`): H5 nuanced, H6 rejected — see charter §0 state-note 2026-06-28.

Phase **1b** (agentic #13/14/20/21) is deferred — adds a tool-use-loop module + frozen-corpus fixtures later.

## Verify the findings without an API key

Every hypothesis number in the reports re-derives offline from committed records + committed
prices — no key, no spend:

```bash
uv sync                                    # Python 3.12, exact versions from uv.lock
uv run pytest -q                           # 299 tests
uv run python -m analysis.h1 results/run-20260624T112122Z-cfa60e            # H1 (1a)
uv run python -m analysis.h5 results/run-20260702T203102Z-f704f0            # H5 3-arm (1d)
uv run python -m analysis.h7 results/run-20260702T203102Z-f704f0 --matrix runs/phase1d.yaml
uv run python -m analysis.h8 results/run-20260702T203102Z-f704f0            # H8 neutral ratio
```

Cross-check the printed tables against the committed `analysis/output/**/*.csv`. API keys
(`.env.example`) are needed only to generate new records or re-run the LLM judge.

## Provenance & licensing (public release)

- **Pre-registration:** hypotheses and kill-conditions were written before data (charter §0
  revision log, dated entries). This public repository is a **clean-history mirror** of the
  private lab repo — the ordering evidence is the charter's internal dated log and the run
  records' timestamps; the private repo's full git history is available for verification on
  reasonable request.
- **Redaction:** account-scoped API identifiers (`request_id`, batch job names) are removed from
  the published records; token counts, timing, hashes, and model outputs are untouched. Two
  fixture inputs are third-party copyrighted works replaced by `WITHHELD.md` stubs carrying
  their sha256 (the frozen-manifest hashes remain verifiable); no published record contains
  their text. The provider billing export
  (`analysis/output/claude_api_cost_2026_06_18_to_2026_07_05.csv`) has one redaction: the name
  of an unrelated project's API key (all-$0 rows, retained as scope evidence) — see
  `analysis/output/billing-export-note.md`.
- **Licensing:** code MIT (`LICENSE`); data + documents CC BY 4.0 (`LICENSE-DATA`). Cite via
  `CITATION.cff`.
- **Method note:** experiments were designed and operated by the author working with Claude
  (Anthropic) as the implementation agent, under the guardrails in `CLAUDE.md`; every billable
  gate and every artifact freeze was owner-signed.

## Non-negotiables (full list in `CLAUDE.md`)

Measure don't estimate · capture the full usage vector · version-stamp + hash every record · flat N, never peek-and-extend · never improvise a fixture · define the band by the artifact, never re-target the token count per model · dollars live only in `prices/`.
