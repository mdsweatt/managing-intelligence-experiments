# RUN.md — Launching the Phase 1a measurement run

**Status:** ✅ **RAN — Phase 1a complete (2026-06-25).** Dataset: `results/run-20260624T112122Z-cfa60e/`
(2,069 records, verified clean — all four families, zero quarantined). This is **build-phase 5** of
**Experiment 1** — the live N=20 sweep over the **Phase-1a** cells. Read `CLAUDE.md` (constitution)
first; this is the operator runbook. **Read "Lessons from the actual run" at the bottom before the
next run** — the first attempt aborted on a usage limit and the whole thing took ~17 h.

## TL;DR

```bash
uv run python -m harness.run --matrix runs/phase1a.yaml --usd-prior 30 --out results/
```

- **Expected cost ≈ $100** (cost-gate central projection, universal Opus, Opus ≈ 60%). **Hard
  ceiling $500** (abort backstop, not a budget). Fund ≥ ~$300 of API credits before launching.
- **~2,069 billable calls** across Haiku / Sonnet / Opus at flat N=20. **This is a billable run —
  flag the spend before launching** (project convention: every live API touch is flagged first).
- Output → `results/<run-id>/records.jsonl` (raw tokens, no dollars) + `config-snapshot.yaml`.

## Where this sits (terminology — three overlapping "phase" layers)

1. **Research program → Experiments:** Experiment 1 (stability / H1, *this repo*) → Experiment 2
   (decomposition / H2·H3, later).
2. **Within Experiment 1 → 1a / 1b:** **Phase 1a** = the 21 discrete / non-agentic cells (what runs
   here). **Phase 1b** = agentic cells #13/14/20/21 (deferred).
3. **Build-order phases 0–6:** 0 foundations · 1 capture contract · 2 skeleton · 3 fixtures ·
   4 cost gate · **5 = this Phase-1a run** · 6 analysis. ("Phase 0 cost gate" actually runs in
   build-phase 4 — naming is overloaded.)

## Pre-flight checklist

A billable, no-resume run — verify each gate before launching. Last refreshed **2026-06-23**.

**Before launch — gates (all green except the credits caveat):**

- [x] **Fixtures frozen** — 26/0 (`fixtures/manifest.yaml`); dry-run = **67 units / 2,069 calls**,
  #7-L in, deferred L cells auto-skip. **Re-confirmed 2026-06-23 — no drift since the freeze.**
  (`docs/fixture-freeze-2026-06-21.md`)
- [x] **Harness verified** — **136 tests green**; frozen-gate · spend-guard · rate-backoff ·
  config-snapshot all wired + proven live (Phase 0, `results/run-20260621T171817Z-563d39/`).
- [x] **Capture integrity** — SPEC §5 conformance audited; **thinking-token capture verified live on
  Opus** (streaming recovery + absent-or-null fail-loud guard, commit `23fd3aa`) → no silent-zero
  risk on #15/#16. (`live-verification-2026-06-16.md` 2026-06-23 sub-addendum)
- [x] **Live API facts current** — rate tier Haiku/Sonnet ITPM 450k, **Opus ITPM 2M** (2026-06-22);
  ceilings, tokenizer, temperature, thinking all verified. Large-input cells (incl. #7-L at 55k tok)
  fit with headroom.
- [x] **Cost gate cleared $500** → run as specified, universal Opus (central ≈ **$100**).
- [⚠] **Credits funded — $316** (verified covers it, ~3.2× the ~$100 central). **Caveat:** $316 is
  *below* the $500 software ceiling, so your **credit balance is the effective backstop**, not the
  harness abort — top past $500 if you want the harness to stop it cleanly. A mid-run credit
  exhaustion is **not** retried (aborts with partial data).
- [⚠] **Monthly *usage limit* — CHECK THIS; it is NOT the same as credit balance.** ⚠️ **This bit us
  on 2026-06-24:** the first run aborted at 24.7% with `400: "You have reached your specified API
  usage limits. You will regain access on 2026-07-01 at 00:00 UTC."` — a **monthly spend cap set in
  the Anthropic Console (Org → Limits)**, exhausted *even though credits were funded*. Credits and the
  usage limit are independent gates. Confirm the monthly usage limit comfortably exceeds the run's
  projected cost (≥ ~$150) **before** launching, or the run dies mid-flight and re-runs from scratch
  (no resume). The cap resets at the calendar-month boundary.
- [x] **API key** present in `.env`.

**At launch:**

- [ ] `--usd-prior 30` — **not 150** (see "The `--usd-prior` knob" below; 150 aborts ~⅓ in).
- [ ] Command is `--matrix runs/phase1a.yaml --out results/` (TL;DR above).
- [ ] **Flag the billable run** (project convention: every live API touch is flagged first).

**During the run:**

- [ ] **`Ctrl-C` is safe** — completed records are already on disk; no mid-run resume
  (relaunch = a new run dir).
- [ ] **Sanity-check the first #15/#16-Opus record:** `thinking_tokens > 0`. Belt-and-suspenders —
  the guard now fails loud if capture ever breaks, but a 30-second eyeball confirms it live.
- [ ] Watch for a credit-exhaustion abort (partial data, not retried).

**After the run — discipline:**

- [ ] **Flat N — do NOT** observe a noisy cell and add runs (anti-peeking; a noisy cell is a
  *finding*, not a prompt to collect more — CLAUDE.md invariant 4).
- [ ] `results/<run-id>/` is token-denominated + **append-only** — never hand-edit.
- [ ] Analysis (build-phase 6, see "After the run" below): fill `prices/` from **current published
  pricing** (verify live, not from memory); compute CoV per cell.

## The `--usd-prior` knob (use 30, not 150)

It's a **safety backstop, not a price** (real prices live in `prices/`, applied at analysis only).
The guard converts it: `budget = $500 / prior × 1M tokens`, applied to the input **and** output
streams independently; it aborts if either exceeds the budget.

- The run uses **~10–12M input tokens** (≈8.8M single-call precise + multi-turn compounding + cache
  reads). So the budget must exceed that.
- `--usd-prior 30` → budget **16.7M** tokens/stream → run completes with headroom, still trips a
  genuine runaway far below $500.
- **Do NOT use 150** → budget only 3.33M → the guard would **abort ~⅓ of the way in** (that prior was
  fine for the tiny 52-call Phase-0 run, not this one).

## Optional smoke test first (machinery check — NOT a cost estimate)

```bash
uv run python -m harness.run --matrix runs/phase1a.yaml --usd-prior 30 --limit 25 --out results/
```

Runs the first 25 units live to confirm records write, auth + credits work, and the format is right
(~$1–2). **Do not extrapolate its cost** — units aren't cost-ordered, so the first 25 are the cheap
S/Haiku cells; the expensive Opus / L-band / thinking cells come later. Trust the **~$100 cost-gate
projection** (which bracketed the expensive tail) for the dollar figure, not a ×80 of the smoke test.

## Run it

1. Confirm credits funded (≥ ~$300) and **flag the billable run**.
2. Launch the full command (TL;DR above).
3. It streams; **`Ctrl-C` is safe** — records completed so far are already on disk in
   `results/<run-id>/`. (A re-launch starts a new run dir; there is no mid-run resume.)

## After the run → build-phase 6 (Analysis)

- Fill `prices/prices-2026-06.yaml` with **current** published pricing (verify live — do not assert
  from memory; the file is all `TBD` by design until now).
- Compute **CoV per cell** → the H1 result. Records are token-denominated; dollars enter **only** here.

## Still deferred (out of scope for this run)

- **L-band fixtures** beyond #7-L (which is frozen as the cost-gate exemplar + the `full_ladder_rep`
  L cell): 8-L, cache-L (10/11/12-L), payload-L (18/19-L) — sourcing effort, owner to author.
- **Phase 1b** (agentic #13/14/20/21) and **Experiment 2** (decomposition).

## Lessons from the actual run (2026-06-25)

The run finished clean — but only on the **second attempt**, over **~17 h**. Three things the next
long live run should bake in:

1. **Monthly *usage limit* ≠ credit balance — check both.** The first attempt had $316 of credits
   funded and still aborted at **24.7%** on the Console's monthly *usage limit*
   (`regain access on 2026-07-01` — resets the 1st of the month). Topping up credits does **not**
   clear a usage cap; they are independent gates. Now a pre-flight gate above. Raising the cap and
   re-launching fixed it.
2. **Budget ~17 h wall-clock, not a half-day.** The full 2,069 calls ran **~17.2 h**
   (06-24 11:21 → 06-25 04:32 UTC). Per-call time swings **~20×** by cell type — ~6 s for a tiny
   draft, ~120 s for a large-payload #18/19 call, ~160 s for a thinking-on #15 call — on top of
   highly variable API latency (the *same* standard cells ran 4× slower at one point in the day than
   another). Don't promise a tight ETA; the **thinking (#15) and large-payload (#18/19) cells
   dominate the tail**.
3. **No resume → an abort re-runs from scratch.** The 24.7% abort discarded 512 clean records and
   cost **~$30** of re-spend; the re-run started a fresh run dir. Records write **append-only per
   call**, so a *skip-already-complete* resume layer is the single highest-leverage robustness fix —
   it covers **every** interruption (power loss, API abort, rate wall, Ctrl-C), not just one. Worth
   building before the next long run. (A persistent VM only covers *local-machine* failure; it would
   **not** have prevented the account-level usage-limit abort that actually hit us.)
