# Fixture Freeze — 2026-06-21

**Event:** froze 21 Phase-1a fixtures (tranche-1 single-call + tranche-2 cache/multi-turn/payload;
#5-M re-sourced and frozen the same day).
**Provenance:** `anthropic` SDK 0.109.2 · `count_tokens` (free/non-billable) · tok-hs tokenizer =
`claude-sonnet-4-6` (shared with Haiku 4.5) · tok-opus tokenizer = `claude-opus-4-8` · measured by
`harness.fixtures.measure_files`; sha256 = `fixture_hash(prompt, input)` (`harness/hashing.py`).
**Intent:** records the measured counts + hashes each frozen record now replays from (CLAUDE.md
invariants 1–3, 5–6). Discrepancies are **flagged for owner ruling — not silently reconciled.**

## Procedure integrity (pre-freeze check)

Before trusting the procedure on new cells, the 5 cells frozen in Phase 0 (#1-S, #7-M, #15, #10-M,
#7-L) were re-hashed: **all 5 reproduce their recorded sha256 byte-identically**, and
`verify_frozen_artifact` returns True for each. The freeze procedure is therefore byte-identical to
the one that produced the existing frozen hashes.

## Frozen this event (21)

Band column is the **measured** order-of-magnitude classification (`classify_band`, log-nearest to
S=1K / M=10K / L=100K). For output- and turn-axis cells this reflects the *input* count and is
**informational** — the operative band is the output-word / turn-count proxy (see flags).

| Cell | axis | proxy | tok_hs | tok_opus | band(hs/op) | sha256 |
|---|---|---|---|---|---|---|
| #2-S | input | words=122 | 225 | 301 | S/S | `6de33e18c75f0267d63edc92fee4e687ff90a13e0257b2d2f3ccaa99d4e3f150` |
| #2-M | input | words=1181 | 1496 | 2074 | S/S ⚠️ | `8053bc715bb385860400a5d477239d62bcaf5f9c4e7d3f15faa725a3586369a5` |
| #3-S | input | words=38 | 48 | 66 | S/S | `7a92fa70cc30f21652759979134c51091a6481b0600403cf0862aa5e2e59574c` |
| #4-S | input | words=62 | 273 | 386 | S/S | `38c328e4ef3eee33968bef8d52369a77d433b9978c670d78de79914059c0a302` |
| #5-S | input | words=103 | 143 | 212 | S/S | `2d1b6f373782a28106061a6fedc1fd177aeb707b396840ba253878bdd02eb1a2` |
| #5-M | input | words=6911 | 9367 | 13666 | M/M | `37cbd065f2c64db7801b62501b5d6bb48926fa56860b1e833d9b04ae8b23331c` |
| #6-S | output | words=98 | 155 | 227 | S/S ℹ️ | `9c80c0647e86665e0788786ecbff9d51e0f2a8ebfb1b985fdbb7e20f90f7fc01` |
| #7-S | input | words=755 | 1032 | 1521 | S/S | `e601a92e71252cd4c4d95fd1d1366ac4da3a310badafeb244d473ae8eabb0b15` |
| #8-S | input | words=660 | 1594 | 2228 | S/S | `272bab6b7587c57d14aee93fa05158ed0d828eeacebba09245580f9d9fa09f62` |
| #8-M | input | words=6491 | 10160 | 15006 | M/M | `af6f6bc941aa2924016f1d5c48958d058391c1551dc9b19909c8e17832cdf54a` |
| #9-S | output | words=800 | 343 | 542 | S/S ℹ️ | `3e1ecce2f3acef7d6892e439ff47d1ae26671ffaa0d702c6816bbce118aece26` |
| #9-M | output | words=2500 | 431 | 631 | S/S ℹ️ | `4c7683db538a51cb0e04a74e04fd5ff9888a16429a2057efa2d786c65961a432` |
| #22-S | output | words=160 | 441 | 632 | S/S ℹ️ | `8ec511010e0cf71b321a5a31e1bee6b11e2bb33b603f4457c25d9122d2f265fe` |
| #11-M | cached_context | lines=946 | 9019 | 12068 | M/M | `310071b76f2466010bc14be0224eee97f2ce2e8e1ec2ca8904adfdf1b727bdd9` |
| #12-M | cached_context | words=7272 | 10734 | 14722 | M/M | `a7843280d059626aeae4f3010a054419163069594f5225628d734391cd9b0bc6` |
| #16-few | turns | turns=3 | 481 | 620 | S/S ℹ️ | `a7e79182eab2e7609477f673021249d6731451aaba33067d6d171d31ade6e9b8` |
| #16-many | turns | turns=8 | 757 | 995 | S/S ℹ️ | `0ecd1ab194588c79d0cc5f27b0020119d794c0e1105db907eeb4ddb029617022` |
| #17-few | turns | turns=3 | 172 | 212 | S/S ℹ️ | `56180d98f3e4a6875dd7b3f13237dc694d6092543c5492f7eab46482ed121526` |
| #17-many | turns | turns=8 | 365 | 482 | S/S ℹ️ | `9e75cd4a4d05b6d0c5f3717f8cce9b7f6fa127d6931553d6b5713948eb736d0d` |
| #18-M | payload | lines=430 | 19122 | 24240 | M/M | `71902efee71fbd60b2a8a2770e4d7fe5e2dfbdc78a37d51c5ce3cbaf622544d3` |
| #19-M | payload | files=9 | 9259 | 12312 | M/M | `e97e060c4fcec1046530f31578eb7a8ced80415d26439de89d1d51a63b71e6f0` |

**Re-verification:** all 12 tranche-1 cells' live `count_tokens` **matched their recorded counts
exactly** — no tokenizer-version drift. The 8 tranche-2 cells were measured for the first time.
**#5-M** was re-sourced (see below) and measured fresh.

**Cache prefix floor (Haiku-probed, ≥4,096):** #11-M cached prefix (input.md alone) = **8,897**
tok-hs; #12-M = **10,686** tok-hs. Both clear the floor — caching engages uniformly across the ladder.

**Opus tokenizer inflation:** ran **+27% to +48%** across cells (central tendency ~+35%, as
documented in `load-band-reference.md` §2).

## #5-M source swap (same-day follow-up)

The original #5-M draft measured 1,022 tok-hs — S regime, below the ~10K M anchor, clustering with
#5-S rather than landing in a distinct M regime. Owner decision 2026-06-21: **replace the source**
rather than freeze as-is. New source = the *Europe 2031* scenario (https://europe2031.ai/, retrieved
2026-06-21): **title + narrative prose up to (not including) "January 2028 — Taking stock"**, with
markdown cleaned to plain prose (byline / date / hero image dropped, links flattened, heading markers
stripped). 6,911 words → **9,367 tok-hs / 13,666 tok-opus (M/M)** — squarely in the M regime,
matching #7-M (8,880) / #8-M (10,160). `prompt.txt` unchanged ("Translate the following text into
French"). **Provenance note:** third-party published fiction (Daan Juijn et al., ARQ Foundation) used
as an internal measurement source; recorded here and in the manifest comment.

## Flags (owner ruling — not reconciled here)

1. **#2-M frozen as-is despite S-regime count** (1496 tok-hs, intended M). Owner accepted
   2026-06-21: the word-proxy separates it from #2-S (122 vs 1181 words) and the band labels the
   fixture, not the count (load-band Rule 2). Caveat recorded: for task #2 the S↔M comparison is a
   small-S↔large-S step (~6.6×), not the 1K↔10K regime jump #7/#8 achieve. **#5-M took the other
   path** (source replaced to reach M — see above).
2. **#7-L** (frozen in Phase 0) carries a real sha256 and intact bytes, yet `manifest.yaml`'s comment
   calls it "a placeholder … Still DEFERRED." Frozen-but-labeled-deferred predates this event —
   **left for owner ruling** (genuinely frozen, or stale comment?). Not touched.
3. **Rate-tier contradiction — RESOLVED 2026-06-22** (re-verified live): the tier was raised —
   Haiku/Sonnet ITPM 450k, Opus ITPM 2M (see the `live-verification-2026-06-16.md` 2026-06-22
   addendum). A ~100k L-band input fits one call, so the rate tier is **not** an L-band blocker;
   `live-verification` item 5 (50k) is superseded.
4. **Output/turn cells** (#6, #9, #22, #16, #17): the band column is the input count and is
   informational; the operative band is the output-word / turn-count proxy. #9's S↔M
   output-token non-overlap (SPEC §3) is only confirmable at run time, not at freeze.

## Test consequence

`tests/test_config.py::test_manifest_accepts_tbd_placeholders` asserted the *live* manifest always
holds ≥1 `TBD` fixture — true during drafting, false once a tranche is frozen (and now zero TBD
remain). Rewritten to test the schema's TBD-acceptance **synthetically** (mirroring
`test_manifest_accepts_real_token_counts`), keeping the live invariant *frozen ⇒ non-TBD counts*.
Suite: **134 passed**.

## Docs realigned in this change set

`fixtures/manifest.yaml` (comment headers + #5-M provenance) · `docs/SPEC.md` (§8 + changelog +
status) · `README.md` (project state, Phase 3/4 trackers, layout; corrected the stale "no measurement
run" / "101 tests" facts) · `fixtures/README.md` (status block) · `harness/README.md` (Phase 3 build
status) · `docs/phase5-run-loop-design.md` (drafted → frozen). **Not edited** (pre-registration
discipline): `docs/charter.md` revision log — its "every fixture frozen:false / results empty" clause
is stale; flagged here, not silently rewritten.

## Status & still deferred

**Phase 1a is now fully frozen** (21 cells) except the deferred L-band. Still deferred (owner): all
**L-band** artifacts — 7-L, 8-L, cache-L (10/11/12-L), payload-L (18/19-L), each ~100k tokens —
deferred on **sourcing effort** only. (The rate-tier blocker was retired 2026-06-22: re-verified
ITPM 450k Haiku/Sonnet, 2M Opus, so ~100k inputs fit one call.) Phase 1b agentic cells
(#13/14/20/21) remain out of scope until 1a lands.
