# Blog Post Design — "The Bill Was the Easy Part"

**Date:** 2026-07-07
**Deliverable:** One blog post for https://www.mikescorner.io/blog about the Managing Intelligence / Experiment 1 program, aligned with the public mirror (github.com/mdsweatt/managing-intelligence-experiments) so every experimental claim is verifiable there.
**Status:** Design approved in session 2026-07-06/07. Awaiting spec review.

---

## 1. Frame

| Element | Decision |
|---|---|
| **Register** | A — build log / case study (VOICE.md §4), think-piece seasoning in the reader turn only |
| **Audience** | AI-budget owners: practitioners and engineering leaders spending real money on LLM APIs who can't predict the bill. Technically fluent, budget-motivated. Stats translated, numbers kept. |
| **Thesis** | *I spent $211.52 measuring what AI work costs. The bill turned out to be predictable. The thing I couldn't measure was quality.* |
| **Structure** | "The Reveal" — chronological opening third, then findings ordered by argument (what held → what broke), landing on the twist |
| **Length** | ~1,700–1,900 words + 4 whiteboard panels |
| **Title** | Working title: **"The Bill Was the Easy Part"**. Alternates held: "The Meter and the Judge", "What AI Work Actually Costs". Final call at draft review. |
| **Series posture** | Single post; each section written so it can later explode into its own deep-dive. Close carries a forward hook to a future Fable 5 / concentration-of-power post. |

## 2. Section-by-section outline

### §1 Hook (~150 words)
Wednesday morning drive to work, The Artificial Intelligence Show (SmarterX) in the speakers, the $8,000 stat lands: SemiAnalysis bought a $200/month Claude plan and drove it to the weekly limits — up to ~$8,000 of tokens at API pricing ($14,000 for the ChatGPT equivalent). Beat: *I wasn't surprised. Five days earlier I'd pre-registered eight hypotheses about exactly this.*
Listen date **confirmed by Mike: Wednesday 2026-06-17** (article ran Tue 2026-06-16).

### §2 The Itch
- Watching the Claude Code token meter in real time since launch; knowing API prices makes the subscription arbitrage obvious.
- March 2026: the token tracker built with the CraftRole crew (**naming CraftRole in print: approved by Mike**) — client-facing API tokens are COGS ("Monthly API Cost (COGS)"), dev tokens ride the subscription ("Dev Token Allocation"); a "Suggested Client Price" card with margin math. Personal backstory, not repo-verifiable (untracked `Staging_Area/`).
- The Max 5x plan: $125/month ($132.50 with tax).
- GitHub Copilot's billing change landing at the day job: Copilot moved from premium requests to usage-based **"AI Credits" consumed by token usage**, announced 2026-04-27, effective **2026-06-01** — eleven days before charter v0.1. The new model ships org-level token budget controls, i.e., enterprises being taught to budget tokens. **Name Copilot; employer stays generic** ("at the day job") — confirmed by Mike. Sources verified: github.blog announcement + tech-insider.org.
- Friday 2026-06-12: charter v0.1 written — the same day the US government took Fable 5 dark (export-control directive). One sentence only; it pays off at the close.

### §3 The Machine — PANEL 1
- Pre-registration in one paragraph: hypotheses + kill-conditions written before data, frozen hash-pinned fixtures, N=20 per cell flat (no peek-and-extend), full usage vector captured per call.
- Hard number lands alone: **$211.52. Fully measured, zero estimated components.** ($190.34 Anthropic Console + $21.18 Gemini judge.)
- Honest-failure beat inside the build story: first Phase-1a run died ~24.7% in — a monthly API usage limit, not money; both aborted runs kept in the public data manifest as honest failures.
- Public repo link lands here (pinned tag — see §6).

### §4 What Held — PANEL 2
- 2,069 records, 67 cells, ~14.05M tokens, 17.2 h wall-clock.
- **62/67 cells CoV < 15%; median 4.5%; max 20.1%.**
- Variance ladder by axis: payload 1.0% · input 1.9% · output 3.3% · cached-context 4.7% · turns 6.2% · **thinking 14.6%** (the one hot axis).
- Same-task contrast: #18 analyze-dataset — Opus 0.3% vs Sonnet 16.7% CoV, same frozen input; the model *chooses* to write more. All run-to-run cost variance lives in the output component.
- Tokenizer discovery: live verification showed Opus tokenizes the same fixture ~+35% vs Haiku/Sonnet — the unit moved under us; hence version-stamping everything.

### §5 The Levers — PANEL 3
- 1c/1d compressed: a frozen scaffold (skill) makes output more repeatable (H5 variance half: CoV down in 17/24 cells in 1d, often 50–80%).
- Whether it saves or costs money depends on cap-vs-mandate — and the sign was predicted a priori **24/24** (caps −40…−72%, mandates +12…+738%; outlier: #23 spec-draft on Haiku +738%).
- Placebo: a length-matched neutral system block reproduces ~none of the tightening (median R = −0.026). The structure does the work, not the presence of a system block.

### §6 What Broke — PANEL 4
- The tier-quality question (scaffolded Haiku ≈ Opus?) required a judge. Built properly: frozen rubric, hashed (`5fd08ff3…`), cross-family model (Gemini 3.1 Pro), K=3 replicates, 59/65 disagreements unanimous.
- Checked against 144 blind owner labels: **54.9% agreement, κ ≈ 0.04 — statistically chance.** Per-task range 15/18 down to 5/18 (below chance).
- The admission, plainly: adjudication of all 65 disagreements → **83% construct under-specification (mine), 17% owner label slips, 0% judge misapplication.** The judge didn't fail me; my definition of "good" failed the judge.
- Phrase to keep: **"crisp ≠ calibrated."** Context: 1c's provisional H6 rejection (Opus preferred 12–1 over scaffolded Haiku) stands, neither upgraded nor overturned.

### §7 The Key Insight
- Cost is a property of the machine — measurable, bandable, predictable. Quality is a relationship between the work and whoever pays for it.
- **The one load-bearing analogy (gym):** a training log tells you exactly what a session cost — sets, tonnage, time. It can't tell you whether the session was *good*; that takes a coach's eye, and a coach calibrated to someone else's goals reads your log wrong at coin-flip rates.
- Labeled speculation: quality may be *principal-relative*. That's the next study (inter-human agreement panel), not a finding.

### §8 What This Means For You (reader turn — 4 imperatives)
1. **Budget in tokens, not dollars.** Price is a scalar applied at analysis time; the tokenizer alone moved 35% under us on one model release.
2. **Band tasks, not averages.** A per-token budget built on a company-wide average is wrong for almost everyone in it; task-level bands came in tight.
3. **Know your two hot levers.** Thinking mode is the variance amplifier (14.6% vs ~1–6% for everything else); scaffolds save or spend depending on cap-vs-mandate, and the sign is predictable before deployment.
4. **Don't automate quality judgment you haven't calibrated.** A crisp judge isn't a correct one — check it against your own blind labels before you trust it with anything.

### §9 Close
- Callback to the car: Roetzer's question, quoted + linked — *"By this fall, when we're all in budgeting for 2027, how do you even begin to do this? It's going to be crazy."* The post is one measured answer.
- Aphorism candidates (final call at draft review):
  - (a) "The bill was the easy part. The taste is still yours to own."
  - (b) "You can meter intelligence. You can't yet meter good."
- Forward hook: *Next: what happens when the most powerful models get gated — and who gets left holding the expensive ones.*
- CTA: **mike@mikescorner.io** (confirmed by Mike).

## 3. Whiteboard panels (brief descriptions)

Hand-drawn whiteboard style (consistent with the two existing panels in `docs/images/`), produced via the design-illustration workflow. One panel per major section; each carries the methodology so the prose stays narrative.

**Panel 1 — "The Machine" (§3).** A left-to-right pipeline sketch: a "frozen fixture" box with a padlock and hash stamp → arrow labeled "same prompt ×20" → a three-rung model ladder (Haiku / Sonnet / Opus) → a receipt-style "usage vector" slip itemizing input / output / cache read / cache write → a filed record card stamped with a hash → a GitHub repo box. Headline scrawl: **"$211.52 · 8 hypotheses · 3,989 measured runs."** (3,989 = 2,069 + 360 + 1,560 harness records; excludes the 4,869 Gemini judge calls, which the caption may note.)

**Panel 2 — "The Variance Ladder" (§4).** A vertical ladder of six rungs, one per axis, each annotated with its CoV: payload 1.0% at the calm bottom rising to thinking 14.6% at the top — the top rung circled hard with a small flame doodle and "the hot axis" note. Margin scrawl: **"62/67 under 15% · median 4.5%."**

**Panel 3 — "Caps vs Mandates" (§5).** A single "scaffold" document icon in the center with two diverging arrows: left arrow bending down labeled **"CAP −40…−72%"** (scissors doodle), right arrow bending up labeled **"MANDATE +12…+738%"** (megaphone doodle). Below, a deliberately boring flat line labeled "placebo block · R ≈ −0.03." Headline scrawl: **"Sign predicted 24/24."**

**Panel 4 — "Crisp ≠ Calibrated" (§6).** Left: a robot judge at a bench with a clipboard, wearing badges "frozen · hashed · K=3 · unanimous." Right: a human figure with a stack of 144 blind index cards. Between them, a flipping coin labeled **"54.9%."** Bottom scrawl: **"83% of the fuzz was mine."**

## 4. Voice checklist bindings (VOICE.md §8)

- Scene open: §1 (car, Wednesday morning, podcast). Number in first 150 words: $8,000.
- Honest admission: §6 (83% construct fuzz — mine), plus the 24.7% abort in §3.
- One load-bearing analogy: training log vs coach's eye (§7). No other extended analogies.
- Numbers land alone: $211.52 (§3); 54.9% (§6).
- Rhetorical question answered immediately: Roetzer's question at close, answered by the post itself.
- Speculation labeled: principal-relative quality (§7).
- Reader turn: §8, four imperatives. Close: aphorism + callback + forward hook (§9).
- No anti-pattern phrases (VOICE.md §6). No em-dash abuse, no exclamation marks, no emoji.

## 5. Hard constraints (fabrication + alignment)

1. **Never cite ~$103 for Phase 1a** — that figure lives only in an internal doc excluded from the mirror. The publicly verifiable Phase-1a figure is **$149.01** (billing export; includes both aborted attempts).
2. Every stat, quote, date, and anecdote: real, sourced, or flagged `[MIKE: …]`. No invented personal detail, ever.
3. Experimental claims link to the public mirror **pinned to a tag** (v1.1 — see §7), never to `main`.
4. Personal backstory (token meter habit, CraftRole tracker, Max 5x price, Copilot change) is presented as backstory, not as repo-verifiable evidence.
5. External claims keep source qualifiers: SemiAnalysis figures are "up to ~$8,000" / "roughly $14,000" (not exact); attribute the study to SemiAnalysis, encountered via SmarterX Episode 219.
6. Model/date stamps stay in the prose where load-bearing (results are stamped to Haiku 4.5 / Sonnet 4.6 / Opus 4.8, June–July 2026) — findings are dated, per the project's own re-verification discipline.

## 6. Claim → source map (links pinned to mirror tag v1.1)

Base URL: `https://github.com/mdsweatt/managing-intelligence-experiments/blob/v1.1/`

| Claim in post | Source (repo-relative) |
|---|---|
| $211.52 total; $190.34 Anthropic + $21.18 Gemini; "fully measured, zero estimated components" | `analysis/output/billing-export-note.md` + `analysis/output/claude_api_cost_2026_06_18_to_2026_07_05.csv` |
| Phase 1a spend $149.01 (incl. aborted attempts) | `analysis/output/billing-export-note.md` |
| 67 cells × N=20; 2,069 records; ~14.05M tokens; 17.2 h; 0 quarantined | `docs/phase1a-report.md` |
| 62/67 CoV < 15%; median 4.5%; max 20.1% | `docs/phase1a-report.md` + `analysis/output/h1_cov.csv` |
| Variance ladder (payload 1.0 → thinking 14.6) | `docs/phase1a-report.md` + `analysis/output/cov_by_axis.png` |
| #18: Opus 0.3% vs Sonnet 16.7% CoV, same input | `docs/phase1a-report.md` |
| Run-to-run cost variance is entirely output-side | `docs/phase1a-report.md` + `analysis/output/decomposition.csv` |
| Opus tokenizes ~+35% vs Haiku/Sonnet; temperature omitted (Opus rejects the param) | `docs/live-verification-2026-06-16.md` + `docs/charter.md` §4–5 |
| First 1a run aborted ~24.7% on monthly usage limit; aborted runs kept | `RUN.md` + `results/README.md` (data manifest) |
| H7: sign predicted 24/24; caps −40…−72%; mandates +12…+738% (#23-Haiku +738%) | `docs/phase1d-report.md` + `analysis/output/phase1d/h7_sign.csv` |
| H8: placebo block, median R = −0.026 | `docs/phase1d-report.md` + `analysis/output/phase1d/h8_neutral.csv` |
| H5 1d re-test: CoV down 17/24, often 50–80% | `docs/phase1d-report.md` + `analysis/output/phase1d/h5_determinism.csv` |
| Judge: frozen, hashed `5fd08ff3…`, Gemini 3.1 Pro, K=3; $21.18; 4,869 calls | `docs/phase1d-judge-spec.md` + `docs/phase1d-report.md` |
| Judge vs owner: 54.9% (n=144), κ ≈ 0.04; per-task 15/18 → 5/18 | `docs/phase1d-report.md` + `analysis/output/phase1d/adjudication.csv` |
| Adjudication: 83% construct fuzz / 17% owner slips / 0% judge misapplication; 59/65 unanimous | `docs/phase1d-report.md` + `analysis/output/phase1d/adjudication.csv` |
| 1c: Opus preferred 12–1 (blind pairwise, skill-on #6); scaffolded Haiku 5% rubric pass (#9) | `docs/phase1c-report.md` |
| Pre-registration ordering (v0.1 2026-06-12 → v0.8 2026-07-02; retraction note 2026-06-26) | `docs/charter.md` §0 |
| 1c generation $2.94; 1d main run $24.57 (Console-exact) | `docs/phase1c-report.md` / `docs/phase1d-report.md` |

**External sources (linked inline, 2–4 words of running text):**

| Claim | Source |
|---|---|
| $200 Claude plan → up to ~$8,000; ChatGPT → ~$14,000; −900% return | SemiAnalysis (x.com/SemiAnalysis_/status/2064815044085318040), via SmarterX "Is the Era of Affordable AI Over?" (smarterx.ai/smarterxblog/i-subscription-pricing-subsidy, 2026-06-16) |
| Roetzer quote ("budgeting for 2027… how do you even begin") | Same SmarterX article / Episode 219 (podcast.smarterx.ai/shownotes/219) |
| "Nobody can predict AI token costs" framing (optional foil) | SmarterX 2026-06-23 (smarterx.ai/smarterxblog/ai-token-costs-pricing) |
| Meta curbing employee AI usage, 2027 token budgets | The Information via the-decoder.com (linked in SmarterX article) |
| Fable 5 export-control directive 2026-06-12; restored ~2026-06-30/07-01 | anthropic.com/news/fable-mythos-access + anthropic.com/news/redeploying-fable-5 + NYT 2026-06-30 |
| Copilot → usage-based "AI Credits" (token-consumed), announced 2026-04-27, effective 2026-06-01 | github.blog/news-insights/company-news/github-copilot-is-moving-to-usage-based-billing/ (primary) + tech-insider.org/ie/github-copilot-usage-based-billing-2026/ |

## 7. Execution plan (after spec approval)

1. **Panels:** produce the 4 whiteboard panels (design-illustration workflow, style-matched to existing `docs/images/` panels).
2. **Mirror v1.1:** commit panels to private repo `docs/images/`, rebuild mirror (`scripts/build_public_mirror.py`), push, tag **v1.1**. This also publishes the billing-export note (currently on mirror `main` but absent from v1.0) at a pinned tag. This spec ships in v1.1 (no exclude-list entry — planning transparency is on-brand).
3. **Draft** the post in full per this outline (writing-in-mikes-voice skill as hard constraint), all `[MIKE]` flags left visible.
4. **Link check:** every claim-map URL resolves at v1.1 before the draft is called done.
5. **Voice checklist** (§4 above) self-check, then deliver draft for Mike's review. Revise, don't regenerate.
6. **Doc alignment:** confirm the post's numbers match the Budgeting_AI_Work deck ($211.52 program total already aligned) and the repo README framing; no new claims introduced anywhere without a source.

## 8. Open items

**Resolved 2026-07-07 (Mike's spec review):** listen date = Wed 2026-06-17 · Copilot named, employer generic · CraftRole nameable in print · CTA = mike@mikescorner.io · Copilot billing change verified (usage-based AI Credits, effective 2026-06-01; github.blog + tech-insider.org).

**Remaining:**
- `[MIKE]` Final title + aphorism pick at draft review.
