# harness/ — the benchmark runner (build target)

The module split below is **the implementer's call** — don't make four files if two do. What's
fixed is the set of **responsibilities** and the **invariants** they must enforce (`../CLAUDE.md`).

## Responsibilities

**API client**
- Call the Anthropic API; capture the **full `usage` vector** every call: `input`, `output`,
  `cache_read_input_tokens`, `cache_creation_input_tokens`, tool-result tokens, and
  `thinking_tokens` (from `output_tokens_details`). Plus `latency_ms`, `wall_clock`.
- Stamp `model_id`, `model_version`, `tokenizer_version` on every record.
- `max_tokens` = the model's output ceiling (never omit). Backoff/batching for rate limits.

**Matrix expansion**
- Load `runs/*.yaml`; expand each task into `(band × model × config)` cells.
- Apply the over-service rule (`match_hypothesis_config_swap_model`): the over-service / down-probe
  model runs at the **hypothesis cell's config**, swapping only the model. Matched-minimal for
  no-thinking tasks; matched-thinking for #15/#16.

**Cell execution**
- Flat **N per cell**, pre-committed, uniform. **Never** observe a noisy cell and add runs.
- Resolve the fixture from `fixtures/manifest.yaml`; **assert its `sha256`** before running; never
  improvise or regenerate a fixture — if missing/unfrozen, stop.
- Compute and record a `config_hash` (exact fixture + full config) so every run replays.

**Cache cells (#10–12)** — `warm_once_read_many`
- One cache-**write** call, then the read calls; record `call_role`. Report write cost and read
  distribution **separately** (a naive N× loop = bimodal mixture = meaningless CoV).
- **Assert a cache hit on every read** (`cache_read` high, `input` low); discard/flag misses.
  Keep reads inside the cache TTL window — backoff that delays a read past TTL causes a miss.
- Floor the cached segment at **≥ 4,096 tokens** when the cell is Haiku-probed.

**Multi-turn cells (#16, #17)**
- Pre-scripted user turns, fixed across runs (only model stochasticity moves). Capture usage
  **per turn** (`turn_index`), not per session — variance is non-stationary across turns.

**Cost & safety**
- Pre-run cost estimate + **hard call/spend ceiling**; abort on breach.

## Writes to

`results/<run-id>/records.jsonl` (raw tokens, **no dollars**) + `results/<run-id>/config-snapshot.yaml`.

## Build status

- **Phase 3 (fixtures) — done.** `fixtures.py` measures the two token counts per fixture
  (live `count_tokens`), classifies the band, enforces the Haiku ≥4,096 cache floor, and verifies a
  frozen artifact still hashes to its `sha256`. **21 Phase-1a fixtures frozen + hashed** with measured
  counts (2026-06-21, `docs/fixture-freeze-2026-06-21.md`); #5-M re-sourced to the *Europe 2031*
  scenario, L-band deferred. The manifest→messages
  assembly (resolve cell → read fixture files → build the per-cell-type call → assert sha256) is the
  matrix-expansion step now built in Phase 5 (`harness/expand.py` / `assemble.py` / `run.py`).
- **Phase 2 (skeleton) — done.** `client.py` (streaming capture: full usage vector + `request_id`
  + rate-limit headers + timing), `guard.py` (hard call/token ceiling; attempts counted *before*
  the call so a failing loop is bounded; tokens registered even if persistence fails), `runner.py`
  (`execute_call` → capture → hash → record → ceiling; `warm_once_read_many` with the cache-hit
  assertion). Proven end-to-end live by `skeleton_demo.py`. Adversarially reviewed (3 lenses).
- **Deferred to Phase 5 (the real run loop), surfaced by review — not silently dropped:**
  - **Rate-limit backoff / batching** + the cache-TTL interaction (a 429 mid-warm-window can push a
    read past TTL → a miss). SPEC §6. The skeleton relies on the SDK's transparent retries only.
  - **`config-snapshot.yaml` written by the run spine** + a stamped harness code-version, so a run
    replays from its dir alone (`write_snapshot` exists; nothing calls it yet, and there is no
    `harness.__version__`). SPEC §5.
  - **`records.jsonl` fsync durability** — a hard crash mid-write could leave a torn final line;
    low priority (each append opens/writes/closes), revisit if it bites.
