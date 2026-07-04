"""harness/skeleton_demo.py — Phase 2 end-to-end proof (THROWAWAY).

Proves the harness skeleton against the LIVE API on a throwaway fixture (NOT a curated
one; these calls do NOT enter any measurement dataset — they write to a temp dir that is
discarded). Exercises the full spine the real run sits on:

  1. discrete call (Haiku)            — stream → capture full usage + provenance → hash → record
  2. warm-once-read-many (Sonnet)     — cache write + reads, with the cache-hit assertion
  3. cost ceiling                     — a tiny guard that aborts mid-run (CeilingBreach)

Run:  uv run python -m harness.skeleton_demo
Cost: a few cheap calls, well under $0.05. Requires ANTHROPIC_API_KEY in .env.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from harness.config import fixture_hash
from harness.guard import CeilingBreach, SpendGuard
from harness.runner import RunWriter, execute_call, new_run_id, warm_once_read_many
from harness.schema import CallConfig, CallRole, CellId

HAIKU = "claude-haiku-4-5-20251001"
SONNET = "claude-sonnet-4-6"

# A ~1.5k-token throwaway "knowledge base" so Sonnet's 1,024-token cache minimum engages.
_PARA = (
    "Individuals and enterprises are beginning to consume intelligence at scale and will need "
    "to budget and allocate it the way they budget headcount, capex, and opex. A token is the "
    "unit of that spend, yet most knowledge workers do not know what a token is or what it costs. "
    "Subscription products hide token consumption, so even motivated users have no meter at the "
    "surface they work on. The atomic unit of measurement is a task at a load band, benchmarked "
    "for its run-to-run variance rather than reported as a single number. "
)
KB_PREFIX = "THROWAWAY KNOWLEDGE BASE FOR THE SKELETON DEMO.\n\n" + (_PARA * 12)


def _summarize(label: str, rec) -> None:
    u = rec.usage
    print(
        f"  [{label}] role={rec.call_role.value} model={rec.model_id} "
        f"in={u.input_tokens} out={u.output_tokens} "
        f"cache_read={u.cache_read_input_tokens} cache_write={u.cache_creation_input_tokens} "
        f"thinking={u.thinking_tokens} | stop={rec.stop_reason} quarantined={rec.quarantined} "
        f"| hit={rec.cache_hit} req={rec.request_id} "
        f"rate_hdrs={len(rec.rate_limit)} latency={rec.latency_ms:.0f}ms "
        f"hash={rec.config_hash[:10]}…"
    )


def main() -> None:
    load_dotenv()
    client = anthropic.Anthropic()
    sdk = anthropic.__version__
    print(f"Phase 2 skeleton proof — live API, anthropic {sdk} (THROWAWAY; temp dir)\n")

    with tempfile.TemporaryDirectory() as tmp:
        run_id = new_run_id(token="skeleton")
        writer = RunWriter(tmp, run_id)
        guard = SpendGuard(max_calls=20, max_input_tokens=2_000_000, max_output_tokens=200_000)

        # 1. Discrete call on Haiku.
        print("1. Discrete call (Haiku) — capture → hash → record")
        haiku_cfg = CallConfig(
            model_role="haiku",
            model_id=HAIKU,
            band="S",
            effort=None,
            thinking="off",
            max_tokens=64000,
        )
        haiku_cell = CellId(
            task_id=1,
            task_name="draft_email",
            band="S",
            model_role="haiku",
            model_id=HAIKU,
            role_label="hypothesis",
        )
        prompt = "Draft a two-sentence reminder email about a 3pm budget review. Subject + body."
        rec = execute_call(
            client=client,
            guard=guard,
            writer=writer,
            cell_id=haiku_cell,
            config=haiku_cfg,
            fixture_hash=fixture_hash(prompt, None),
            tokenizer_version="tok-hs",
            sdk_version=sdk,
            messages=[{"role": "user", "content": prompt}],
            call_role=CallRole.single,
        )
        _summarize("discrete", rec)

        # 2. Cache cell on Sonnet — warm once, read twice; assert the hit on each read.
        print("\n2. Cache cell (Sonnet) — warm-once-read-many; assert cache hit")
        sonnet_cfg = CallConfig(
            model_role="sonnet",
            model_id=SONNET,
            band="M",
            effort="high",
            thinking="off",
            max_tokens=128000,
        )
        sonnet_cell = CellId(
            task_id=10,
            task_name="support_vs_kb",
            band="M",
            model_role="sonnet",
            model_id=SONNET,
            role_label="hypothesis",
        )
        write_rec, read_recs = warm_once_read_many(
            client=client,
            guard=guard,
            writer=writer,
            config=sonnet_cfg,
            cell_id=sonnet_cell,
            fixture_hash=fixture_hash("Answer strictly from the KB.", KB_PREFIX),
            tokenizer_version="tok-hs",
            sdk_version=sdk,
            cached_system=[
                {"type": "text", "text": KB_PREFIX, "cache_control": {"type": "ephemeral"}}
            ],
            warm_message={"role": "user", "content": "Reply only: KB loaded."},
            read_messages=[
                {"role": "user", "content": "Per the KB, what is the unit of intelligence spend?"},
                {"role": "user", "content": "Per the KB, why don't workers know token costs?"},
            ],
        )
        _summarize("warm-write", write_rec)
        for r in read_recs:
            _summarize("read", r)
        hits = sum(1 for r in read_recs if r.cache_hit and not r.quarantined)
        print(f"   → cache hits asserted on {hits}/{len(read_recs)} reads")

        # 3. Cost ceiling — a deliberately tiny guard that must abort mid-run.
        print("\n3. Cost ceiling — tiny guard must abort (CeilingBreach)")
        tiny = SpendGuard(max_calls=20, max_input_tokens=5)  # 5-token input budget
        try:
            execute_call(
                client=client,
                guard=tiny,
                writer=writer,
                cell_id=haiku_cell,
                config=haiku_cfg,
                fixture_hash=fixture_hash(prompt, None),
                tokenizer_version="tok-hs",
                sdk_version=sdk,
                messages=[{"role": "user", "content": prompt}],
                call_role=CallRole.single,
            )
            print("   ✗ UNEXPECTED: ceiling did not trip")
        except CeilingBreach as e:
            print(f"   ✓ aborted as designed: {e}")

        # 4. Verify what landed on disk — every record reloads + revalidates.
        print("\n4. Persisted records — reload + revalidate from disk")
        from harness.schema import CaptureRecord

        lines = writer.records_path.read_text().strip().splitlines()
        reloaded = [CaptureRecord.from_jsonl_line(ln) for ln in lines]
        print(f"   {len(reloaded)} records written; all reload + revalidate cleanly")
        print(f"   guard totals: {json.dumps(guard.snapshot())}")
        print(f"   sample raw usage (verbatim): {json.dumps(reloaded[0].usage_raw)}")
        print("\n✓ Phase 2 skeleton proven end-to-end (capture → hash → ceiling → cache-hit).")


if __name__ == "__main__":
    main()
