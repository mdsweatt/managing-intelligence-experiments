# `fixtures/` — on-disk fixture formats

This file pins **how a fixture is laid out on disk and how the harness must turn it into an API call**, per cell family. `manifest.yaml` is the registry (one validated entry per cell × band); this README is the consumption contract the **Phase-5 run loop** builds against. When a format here and the manifest schema (`harness/config.py`) disagree, the schema wins on field names/types — escalate genuine conflicts, don't silently reconcile (CLAUDE.md).

## Layout

```
fixtures/task-NN-<slug>/<band>/prompt.txt      # the instruction (always present)
fixtures/task-NN-<slug>/<band>/input.md        # the artifact/context (omitted when there is none)
```

`<band>` is `small` / `medium` / `large` for size-banded cells, or the cell's own band label
(`shared` for #15; `few` / `many` for the turn cells). Any `meta.yaml` files in these dirs are
**empty placeholders, unread by any code** — ignore them.

## The hash contract (all families)

A fixture is pinned by `fixture_hash(prompt, input_text)` = sha256 over
`canonical_json({"prompt": ..., "input": ...})` — **domain-separated, not literal concatenation**
(`harness/hashing.py`). `prompt` and `input` are two distinct fields; a fixture with no artifact
hashes with `input = null` (not `""`). Keep the two files separate on disk — never pre-concatenate.
Token counts are **measured** per tokenizer (`tok_hs`, `tok_opus`) via `harness.fixtures.measure_files`,
never estimated (CLAUDE.md invariants 1, 6). A fixture starts `frozen: false` / `sha256: TBD` during
curation; the owner adjusts content, re-measures, then freezes (all 21 Phase-1a fixtures are now
frozen — see "Current status").

## Per-family call shape

### 1. Standard single-call — input/output cells (#1–9, #15, #22)
`prompt.txt` = the instruction; `input.md` = the artifact (or omitted for prompt-only cells like
#3, #4, #17). The call is **one user message** built as `prompt + "\n\n" + input` (the join used by
`harness.fixtures.count_two`); no separate system prompt. `call_role = single`.

### 2. Cache cells — warm-once-read-many (#10–12)
- `input.md` = the **cached prefix** (a KB / reference set / known source file). Phase 5 sends it as
  the `system` param wrapped as `[{"type": "text", "text": <input>, "cache_control": {"type": "ephemeral"}}]`
  and forwards it through `runner.warm_once_read_many(cached_system=...)`.
- `prompt.txt` = the **single read query**, asked against the cached prefix. It is **reused across all
  N reads** (only model stochasticity moves — that's the H1 read distribution); the one warm-write
  call primes the cache with the same content. Report the write cost and the read distribution
  **separately**; assert a cache hit on every read (quarantine TTL misses — `harness/schema.py`).
- **Haiku floor:** the cached prefix must be **≥ 4,096 tokens** so caching engages uniformly across
  the ladder (`harness.fixtures.assert_cache_floor`). Cache cells are M·L only — no small band.

### 3. Multi-turn cells — scripted turns (#16, #17)  *(convention ratified 2026-06-17)*
- `prompt.txt` = the **pre-scripted USER turns**, separated by a line whose entire content is the
  delimiter `===TURN===`. Only user turns are stored — model responses are generated and, by design,
  compound into later turns' input (the variance amplifier). Turn count is the band (`few` / `many`).
- `input.md` = optional **shared context prepended to the first user turn** (e.g. the failing code in
  #16); omitted for prompt-only creative cells (#17).
- **Phase-5 runner:** read `prompt.txt`, split on `^===TURN===$`, strip each turn; if `input.md`
  exists, prepend it (with `\n\n`) to turn 1. Replay sequentially: send the accumulated `messages`,
  append the model's response, then append the next scripted user turn. Emit **one `CaptureRecord`
  per turn** with `turn_index` set (`harness/schema.py` already supports per-turn capture). The
  session total is the H1 headline; per-turn capture shows where variance enters.

### 4. Payload cells — large artifact via tool-result (#18, #19)  *(convention ratified 2026-06-17)*
- `prompt.txt` = the instruction (the analysis / per-file task).
- `input.md` = the **payload artifact**, delivered to the model as a **tool_result block**, not inline
  prose: Phase 5 sends the prompt as the user turn plus a synthetic `tool_use`/`tool_result` pair
  carrying `input.md`'s bytes. Record `tool_result_tokens` **separately** (`harness/schema.py` stores
  it and guards `tool_result_tokens ≤ input + cache_read`). Payload cells are M·L; band = payload-size
  proxy (`lines` for a dataset, `files` for a batch).
- #19 batches several files inside `input.md`, each preceded by a line `===== FILE: <name> =====`,
  so a uniform per-file instruction applies across the batch (sequential loop, stays Phase 1a).

## Current status (2026-06-21)

**Frozen + hashed** with measured counts — single-call 1–9 + #15 + **#22**; cache **10/11/12-M**;
multi-turn **16/17 (few·many)**; payload **18/19-M** (21 frozen 2026-06-21, record
`docs/fixture-freeze-2026-06-21.md`; #1-S / #7-M / #15 / #10-M were frozen earlier in Phase 0).
#5-M (translate-M) was re-sourced to the ~7k-word *Europe 2031* scenario (europe2031.ai) to reach the
M regime. **Deferred** (owner decision): all **L-band** artifacts — 7-L, 8-L, the cache-L KBs, and
payload-L (each ~100k tokens; sourcing method to be decided). Phase 1b agentic cells (#13/14/20/21)
remain out of scope until 1a lands.
