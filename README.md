# Managing Intelligence — what does AI actually cost, and can you budget for it?

*Experiment 1 of the Managing Intelligence research program.*

A controlled experiment measuring the **token cost of everyday AI knowledge work** — and how
predictable that cost is. When you ask an AI model to draft an email, summarize a document, or
classify a ticket, you pay for the **tokens** it reads and writes (a token ≈ a short word-fragment —
the unit AI providers bill by). This project asks a simple question with an unobvious answer: *can
you put a budget on that?*

It's built as a **provocation tool, not a finance-grade instrument** — the goal is honest,
non-embarrassing ranges that make AI spend legible, not accountant-exact figures. Everything is
measured in **tokens, not dollars** (token prices change every quarter; token *counts* are stable),
with a price applied only at the very end.

## Why this exists

The industry consensus is that AI costs are impossible to predict. A widely-cited 2026 headline:
*"AI Token Costs Continue to Explode and Nobody Can Predict Them."* RBC reported its LLM token usage
up **over 500% since 2025**; on 2026 earnings calls ~300 companies flagged token costs (up from 93 a
year earlier), and Meta, Uber, and Salesforce have started capping employee AI usage. Meanwhile,
inside companies, the reality is often "do what you think is best with the credit card" — and most
knowledge workers don't even know what a token is, let alone what one costs.

This project takes the "nobody can predict them" claim and **tests it** — carefully, on the everyday
tasks knowledge work is actually made of.

## The short version — what we found

- **Most everyday tasks *are* budgetable.** Across 67 task-cells run 20 times each, **62 came in
  tight** — run-to-run cost varied by under 15% (median just **4.5%**). Drafting, classifying,
  translating, summarizing, extracting — the workhorse tasks — you *can* put a band on.
  **Caveat:** this covers *discrete, low-fan-out* tasks. The hard, open-ended agentic work
  (multi-source research, multi-file refactors) — where we *expect* budgeting to break — is
  deliberately not tested yet (that's Phase 1b). We tested the everyday half, and it held.
- **No model is a "slot machine."** Haiku, Sonnet, and Opus all show single-digit run-to-run
  variance — none is systematically noisier. The variability that does exist tracks **how much
  freedom the model has over its output**, not which model you pick.
- **Structure is a *predictable* cost lever.** Adding a "skill" (a frozen output template) moves
  token spend in a direction you can call *in advance*: a scaffold that **caps** length (limits how
  long the output may run) cut a task's **output tokens 40–72%** on every task × model cell tested;
  one that **mandates** more (requires extra sections) raised them on every cell — **24 of 24 cells,
  and the direction was predicted before the run.** Cheaper or costlier, you can tell which ahead of
  time.
- **...but structure is not a *proven* quality shortcut.** A skill makes a cheap model's output more
  consistent and better-formatted — yet the evidence doesn't show it *matching* an expensive model on
  quality, so a skill reads as a consistency-and-format lever, not a tier upgrade. Treat that as
  provisional: the one clean test of it ran into the problem in the next bullet.
- **A cautionary tale about grading AI with AI.** When we used a second AI model as a blind quality
  judge, it produced crisp, confident verdicts — yet agreed with human graders only **54.9% of the
  time** (barely better than a coin flip). The lesson, and arguably the most useful finding here:
  **crisp ≠ calibrated.** A consistent, frozen LLM judge can still be measuring the wrong thing;
  only humans caught it — which is why the quality verdict above stays provisional.

## What we measured (in plain terms)

The unit is a **cell**: one *task*, at one *size*, on one *model*, with one *fixed setup*. We run
each cell **20 identical times** and watch how much the token cost bounces around from run to run. If
it barely moves, the task is **bandable** — you can quote a budget range up front. If it swings a
lot, you can only **meter** it after the fact, not predict it. That run-to-run bounce, as a
percentage of the average, is the **coefficient of variation (CoV)** — the headline number. Under
~15% = budgetable; persistently over ~20% = unpredictable.

One clean result sits underneath all of it: with the input held fixed, **100% of the run-to-run
*cost* variance lives in the model's output.** So a task's predictability reduces to one rule — *how much
the output varies × the output's share of total cost* — which points to two ways to make a task
budgetable: **constrain the output** (templates / schemas) or **make the output a small slice of
cost** (a big fixed context).

## A few terms

| term | plain meaning |
|---|---|
| **token** | the unit AI is billed in — roughly a word-fragment. ~750 words ≈ 1,000 tokens. |
| **cell** | one task × one input size × one model × one fixed setup — the thing we repeat 20×. |
| **CoV** | coefficient of variation — run-to-run cost bounce as a % of the average. Low = predictable. |
| **bandable vs. meter** | *bandable* = stable enough to quote a budget range in advance; *meter* = you can only measure it after the fact. |
| **over-service** | paying for a bigger model than the task needs (e.g. Opus where Haiku would do). |
| **skill** | a frozen, structured output template handed to the model to make its output more consistent. |

## The findings in detail — the reports

If you're here for the results, read these three write-ups. Each is plain-English and links to its
own data:

- **`docs/phase1a-report.md`** — *Can you put a budget on a token?* The core bandability result
  (62 of 67 cells tight).
- **`docs/phase1c-report.md`** — *Can a skill make a cheap model punch above its tier?* Structure as
  a cost-and-consistency lever (mostly not a quality one).
- **`docs/phase1d-report.md`** — *Does the cap/mandate rule hold — and can we trust the ruler?* The
  predictable-cost-direction result, and the AI-judge calibration failure.

Behind the reports sits the **pre-registration** — every hypothesis and its "kill condition" (the
result that would prove it *wrong*) was written down *before* any data was collected, so nothing
could be retrofitted after the fact:

- **`docs/charter.md`** — the source of truth: every hypothesis (H1–H8), its kill-condition, and a
  dated revision log.
- **`CLAUDE.md`** — the measurement rules that always hold (measure don't estimate; capture the full
  token vector; hash every record; fixed sample size, no peeking).
- **`docs/SPEC.md`** — the exact run matrix (which tasks × sizes × models × setups).

## What's in this repo

```
CLAUDE.md      the measurement rules ("constitution")
docs/          charter (hypotheses), SPEC (run matrix), the phase reports, prior-art scan
fixtures/      the frozen, hashed task inputs + prompts; skills/ = the output templates
harness/       the Python measurement engine (API caller, capture contract, spend ceiling)
runs/          machine-readable run matrices the harness executes (phase0/1a/1c/1d.yaml)
results/       the captured data — one folder per run, append-only, never hand-edited
prices/        dated $/token tables — applied only at analysis time
analysis/      the hypothesis scripts (h1/h5/h7/h8, quality judge) + committed outputs
RUN.md         the operator runbook for actually executing a run
```

## Verify the findings yourself (no API key needed)

Every number in the reports re-derives offline from the committed data — no key, no spend:

```bash
uv sync                                    # Python 3.12, exact versions from uv.lock
uv run pytest -q                           # 299 tests
uv run python -m analysis.h1 results/run-20260624T112122Z-cfa60e            # H1 (bandability)
uv run python -m analysis.h5 results/run-20260702T203102Z-f704f0            # H5 (determinism)
uv run python -m analysis.h7 results/run-20260702T203102Z-f704f0 --matrix runs/phase1d.yaml
uv run python -m analysis.h8 results/run-20260702T203102Z-f704f0            # H8 (structure vs. any system block)
```

Cross-check the printed tables against the committed CSVs in `analysis/output/`. An API key
(`.env.example`) is needed only to generate *new* records or re-run the LLM judge.

## Status & data

**Done:** Phase 1a (bandability, H1) and Phases 1c + 1d (the determinism A/B — H5/H6/H7/H8) — all
run, analyzed, and reported. **Deferred:** Phase 1b, the high-fan-out agentic tasks, exactly where we
predicted budgeting is hardest. The full dated log lives in the charter's revision log
(`docs/charter.md` §0) and the three phase reports.

The captured runs (`results/`, one folder each, append-only, never hand-edited):

| run | what it is | records |
|---|---|---|
| `run-20260621T171817Z-563d39` | Phase 0 cost gate | 52 |
| `…T031222Z-75dc13` · `…T062227Z-43d1d4` | two aborted 1a attempts (monthly usage limit — see `RUN.md`) | 500 · 512 |
| `run-20260624T112122Z-cfa60e` | ★ Phase 1a — H1 dataset | 2,069 |
| `run-20260628T051203Z-53aa02` | ★ Phase 1c — H5/H6 dataset (judge: Opus 4.8) | 360 |
| `run-20260702T203102Z-f704f0` | ★ Phase 1d — H7/H8 + H5/H6 dataset (judge: Gemini, cross-family) | 1,560 |

★ = canonical hypothesis dataset. Model outputs are stored only where a quality judge grades them
(Phase 1c/1d); Phase 0/1a records are tokens-only by design.

## Provenance & licensing

- **Pre-registration.** Hypotheses and kill-conditions were written before data (see the charter's
  dated revision log). This public repo is a **clean-history mirror** of the private lab repo; the
  private repo's full history is available for verification on reasonable request.
- **Redaction.** Account-scoped API identifiers are stripped from the published records; token
  counts, timing, hashes, and model outputs are untouched. Two third-party copyrighted fixture
  inputs are replaced by `WITHHELD.md` stubs that preserve their sha256, so the frozen-manifest
  hashes stay verifiable.
- **Licensing.** Code is MIT (`LICENSE`); data and documents are CC BY 4.0 (`LICENSE-DATA`). Cite
  via `CITATION.cff`.
- **Method note.** The experiments were designed and operated by the author working with Claude
  (Anthropic) as the implementation agent, under the guardrails in `CLAUDE.md`; every billable gate
  and every artifact freeze was owner-signed.

## The measurement rules (full list in `CLAUDE.md`)

Measure don't estimate · capture the full token usage vector · version-stamp + hash every record ·
fixed sample size, never peek-and-extend · never improvise a fixture · define the band by the
artifact, never re-target the token count per model · dollars live only in `prices/`.
