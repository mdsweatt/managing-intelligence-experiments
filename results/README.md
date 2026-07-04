# results/ — captured data (APPEND-ONLY)

One directory per run: `results/<run-id>/`.

- `records.jsonl` — one JSON object per call (per **turn** for multi-turn cells). **Raw token
  counts only — never dollars.** Schema: `docs/SPEC.md` §5.
- `config-snapshot.yaml` — the exact expanded matrix + harness code version + all fixture/config
  hashes, so the run replays from this directory alone.

**Never hand-edit a record.** This is the measurement. Re-running produces a new `<run-id>`; it
does not overwrite. Dollars are computed downstream in `analysis/` using `prices/` — they are not
stored here.
