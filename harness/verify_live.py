"""Phase 0 — live API verification.

Confirms or CORRECTS the time-sensitive API facts the experiment depends on
(CLAUDE.md "Verify live, don't assert from memory") before any fixture work or
measurement run. Writes docs/live-verification-<date>.md and prints a summary.

Probes are intentionally cheap: count_tokens is free; the Models API is free;
message probes use tiny max_tokens. Total cost is well under $1.

Discrepancies vs the repo's pinned (2026-06-15) facts are REPORTED, never
silently reconciled — per the constitution they go to the owner for a ruling,
then SPEC.md / load-band-reference.md are updated with a version + timestamp.

Run:  uv run python -m harness.verify_live
"""

from __future__ import annotations

import datetime as dt
import json
import math
import traceback
import uuid
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS = REPO_ROOT / "docs"

# The exact IDs we will run (matches runs/phase1a.yaml models block).
MODELS: dict[str, str] = {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
    "opus": "claude-opus-4-8",
}

# Repo's pinned facts (load-band-reference.md / SPEC.md, 2026-06-15) for diffing.
PINNED = {
    "cache_min": {"haiku": 4096, "sonnet": 1024, "opus": 1024},
    "max_output": {"haiku": 64000, "sonnet": 64000, "opus": 128000},
    "tokenizer": "shared-v1 across Haiku 4.5 / Sonnet 4.6 / Opus 4.8 (one count per fixture)",
    "temperature": "settable (realistic-default) for non-thinking cells; NOT settable with thinking on",
    "effort": "Opus low/high/max(+xhigh); Sonnet low/high/max (no xhigh); Haiku none",
}

SAMPLE = (
    "Individuals and enterprises are beginning to consume intelligence at scale and will need "
    "to budget and allocate it the way they budget headcount, capex, and opex. A token is the "
    "unit of that spend, yet most knowledge workers do not know what a token is or what it costs."
)

client = anthropic.Anthropic()


# --------------------------------------------------------------------------- helpers
def _to_dict(obj):
    for attr in ("model_dump", "to_dict"):
        if hasattr(obj, attr):
            try:
                return getattr(obj, attr)()
            except Exception:
                pass
    try:
        return json.loads(json.dumps(obj, default=lambda o: getattr(o, "__dict__", str(o))))
    except Exception:
        return {"_repr": repr(obj)}


def count_tokens(model: str, text: str) -> int:
    return client.messages.count_tokens(
        model=model, messages=[{"role": "user", "content": text}]
    ).input_tokens


def _try_call(model: str, **overrides) -> dict:
    params = dict(
        model=model,
        max_tokens=overrides.pop("max_tokens", 16),
        messages=[{"role": "user", "content": "Reply with the single word: ok"}],
    )
    params.update(overrides)
    try:
        resp = client.messages.create(**params)
        return {"ok": True, "stop_reason": resp.stop_reason}
    except anthropic.APIStatusError as e:
        return {
            "ok": False,
            "status": e.status_code,
            "type": getattr(e, "type", None),
            "message": (getattr(e, "message", "") or "")[:300],
        }
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": repr(e)[:300]}


# --------------------------------------------------------------------------- probes
def probe_tokenizer() -> dict:
    counts = {role: count_tokens(mid, SAMPLE) for role, mid in MODELS.items()}
    return {"counts": counts, "shared": len(set(counts.values())) == 1}


def probe_models() -> dict:
    out = {}
    for role, mid in MODELS.items():
        try:
            raw = _to_dict(client.models.retrieve(mid))
            out[role] = {
                "id": raw.get("id"),
                "display_name": raw.get("display_name"),
                "max_input_tokens": raw.get("max_input_tokens"),
                "max_tokens": raw.get("max_tokens"),
                "capabilities": raw.get("capabilities"),
                "raw_keys": sorted(raw.keys()),
            }
        except Exception as e:  # noqa: BLE001
            out[role] = {"error": repr(e)[:300]}
    return out


def probe_temperature() -> dict:
    results = {}
    for role, mid in MODELS.items():
        r = {"temp_no_thinking": _try_call(mid, temperature=0.7)}
        if role in ("opus", "sonnet"):
            r["temp_with_thinking"] = _try_call(
                mid,
                temperature=0.7,
                thinking={"type": "adaptive"},
                output_config={"effort": "low"},
                max_tokens=2000,
            )
        results[role] = r
    return results


def _make_prefix(model: str, target_tokens: int, base_cache: dict) -> str:
    if model not in base_cache:
        base_cache[model] = max(1, count_tokens(model, SAMPLE))
    reps = max(1, math.ceil(target_tokens / base_cache[model]))
    return f"[{uuid.uuid4().hex}] " + (SAMPLE + " ") * reps


def probe_cache() -> dict:
    base_cache: dict[str, int] = {}
    targets = [1500, 3000, 5000]  # brackets 1024 / 2048 / 4096 candidate minimums
    out = {}
    for role, mid in MODELS.items():
        rows = []
        for t in targets:
            prefix = _make_prefix(mid, t, base_cache)
            try:
                resp = client.messages.create(
                    model=mid,
                    max_tokens=16,
                    system=[
                        {"type": "text", "text": prefix, "cache_control": {"type": "ephemeral"}}
                    ],
                    messages=[{"role": "user", "content": "Reply: ok"}],
                )
                u = _to_dict(resp.usage)
                created = u.get("cache_creation_input_tokens") or 0
                read = u.get("cache_read_input_tokens") or 0
                inp = u.get("input_tokens") or 0
                rows.append(
                    {
                        "target": t,
                        "approx_prefix_tokens": inp + created + read,
                        "cache_creation": created,
                        "cache_read": read,
                        "input": inp,
                        "cached": bool(created),
                    }
                )
            except Exception as e:  # noqa: BLE001
                rows.append({"target": t, "error": repr(e)[:200]})
        out[role] = rows
    return out


def probe_thinking_usage() -> dict:
    mid = MODELS["opus"]
    try:
        resp = client.messages.create(
            model=mid,
            max_tokens=3000,
            thinking={"type": "adaptive"},
            output_config={"effort": "low"},
            messages=[
                {"role": "user", "content": "What is 17 * 24? Think briefly, then give the number."}
            ],
        )
        usage = _to_dict(resp.usage)
        return {
            "ok": True,
            "stop_reason": resp.stop_reason,
            "block_types": [getattr(b, "type", "?") for b in resp.content],
            "usage_keys": sorted(usage.keys()),
            "usage": usage,
        }
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": repr(e)[:300], "trace": traceback.format_exc()[-600:]}


def probe_headers() -> dict:
    mid = MODELS["haiku"]
    try:
        raw = client.messages.with_raw_response.create(
            model=mid, max_tokens=16, messages=[{"role": "user", "content": "Reply: ok"}]
        )
        headers = {k: v for k, v in raw.headers.items()}
        relevant = {
            k: v
            for k, v in headers.items()
            if ("request-id" in k.lower() or "ratelimit" in k.lower())
        }
        msg = raw.parse()
        return {
            "ok": True,
            "request_id_attr": getattr(msg, "_request_id", None),
            "relevant_headers": relevant,
            "all_header_keys": sorted(headers.keys()),
        }
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": repr(e)[:300]}


# --------------------------------------------------------------------------- report
def _infer_cache_min(rows: list) -> str:
    cached = [r for r in rows if r.get("cached")]
    if not cached:
        return "no cache engaged up to ~5000 tokens (minimum > ~5000?)"
    smallest = min(cached, key=lambda r: r["approx_prefix_tokens"])
    not_cached = [r for r in rows if not r.get("cached") and "error" not in r]
    upper = smallest["approx_prefix_tokens"]
    lower = max((r["approx_prefix_tokens"] for r in not_cached), default=0)
    return f"engages by ~{upper} tokens" + (f"; did NOT engage at ~{lower}" if lower else "")


def build_report(results: dict) -> str:
    today = dt.date.today().isoformat()
    L = []
    a = L.append
    a(f"# Live API Verification — {today}\n")
    a(
        f"**SDK:** anthropic {anthropic.__version__}  |  **Models:** "
        + ", ".join(f"{r}=`{m}`" for r, m in MODELS.items())
        + "\n"
    )
    a(
        "Confirms/corrects the 2026-06-15 pinned facts in `SPEC.md` / "
        "`load-band-reference.md`. Discrepancies are flagged for owner ruling — "
        "**not** auto-applied (pre-registration discipline).\n"
    )

    flags: list[str] = []

    # 1. Tokenizer
    tok = results["tokenizer"]
    a("\n## 1. Tokenizer sharing\n")
    a(f"- count_tokens of the sample paragraph: `{tok['counts']}`")
    a(f"- **Shared across all three:** {'YES ✓' if tok['shared'] else 'NO ✗'}")
    a(f"- Pinned: {PINNED['tokenizer']}")
    if not tok["shared"]:
        flags.append(
            "Tokenizer is NOT shared across the ladder — Rule 2 re-arms; "
            "fixtures need a per-model token count (not one count)."
        )

    # 2. Models API: ceilings, effort, thinking
    a("\n## 2. Models API (ceilings, effort, thinking capabilities)\n")
    for role, info in results["models"].items():
        a(f"### {role} — `{MODELS[role]}`")
        if "error" in info:
            a(f"- ERROR: {info['error']}")
            flags.append(f"Models API retrieve failed for {role}: {info['error']}")
            continue
        a(
            f"- max_input_tokens: `{info['max_input_tokens']}`  |  max_tokens (output ceiling): `{info['max_tokens']}`"
        )
        a(f"- pinned max_output: `{PINNED['max_output'][role]}`")
        if info["max_tokens"] not in (None, PINNED["max_output"][role]):
            flags.append(
                f"{role} max_output is {info['max_tokens']} (pinned {PINNED['max_output'][role]})."
            )
        caps = info.get("capabilities")
        a(f"- capabilities (raw):\n\n```json\n{json.dumps(caps, indent=2)[:1500]}\n```")

    # 3. Cache minimums
    a("\n## 3. Cache minimums (warm-write probe at ~1500 / ~3000 / ~5000 tokens)\n")
    for role, rows in results["cache"].items():
        a(f"### {role} — `{MODELS[role]}`")
        a("| target | approx prefix tok | cache_creation | cache_read | input | cached? |")
        a("|---|---|---|---|---|---|")
        for r in rows:
            if "error" in r:
                a(f"| {r['target']} | — | — | — | — | ERROR: {r['error']} |")
            else:
                a(
                    f"| {r['target']} | {r['approx_prefix_tokens']} | {r['cache_creation']} | "
                    f"{r['cache_read']} | {r['input']} | {'YES' if r['cached'] else 'no'} |"
                )
        inferred = _infer_cache_min(rows)
        pinned_min = PINNED["cache_min"][role]
        a(f"- **Inferred minimum:** {inferred}  |  pinned: `{pinned_min}`\n")
        # Heuristic discrepancy flag
        cached_sizes = [r["approx_prefix_tokens"] for r in rows if r.get("cached")]
        if cached_sizes:
            smallest_cached = min(cached_sizes)
            # If pinned says 1024 but nothing cached below ~2000, or pinned 4096 but caches at ~1500, flag.
            if pinned_min <= 1024 and smallest_cached > 2000:
                flags.append(
                    f"{role} cache minimum looks HIGHER than pinned 1024 "
                    f"(smallest cached ~{smallest_cached})."
                )
            if pinned_min >= 4096 and smallest_cached < 3000:
                flags.append(
                    f"{role} cache minimum looks LOWER than pinned {pinned_min} "
                    f"(cached at ~{smallest_cached})."
                )

    # 4. Temperature / sampling
    a("\n## 4. Temperature & sampling settability\n")
    a(f"- Pinned: {PINNED['temperature']}\n")
    for role, r in results["temperature"].items():
        a(f"### {role} — `{MODELS[role]}`")
        nt = r["temp_no_thinking"]
        a(
            f"- temperature=0.7, thinking OFF → {'OK ✓' if nt.get('ok') else 'REJECTED ✗ '}"
            + (
                ""
                if nt.get("ok")
                else f"({nt.get('status')} {nt.get('type')}: {nt.get('message') or nt.get('error')})"
            )
        )
        if "temp_with_thinking" in r:
            wt = r["temp_with_thinking"]
            a(
                f"- temperature=0.7, thinking ON → {'OK ✓' if wt.get('ok') else 'REJECTED ✗ '}"
                + (
                    ""
                    if wt.get("ok")
                    else f"({wt.get('status')} {wt.get('type')}: {wt.get('message') or wt.get('error')})"
                )
            )
        if role == "opus" and not r["temp_no_thinking"].get("ok"):
            flags.append(
                "Opus 4.8 REJECTS temperature even with thinking OFF — breaks D2 "
                "'hold config fixed, swap only the model' for the temperature control "
                "across a Sonnet→Opus over-service comparison. Owner ruling needed."
            )

    # 5. Thinking tokens / usage shape
    a("\n## 5. Thinking + usage object shape (Opus, adaptive, effort=low)\n")
    tu = results["thinking_usage"]
    if tu.get("ok"):
        a(f"- stop_reason: `{tu['stop_reason']}`  |  block types: `{tu['block_types']}`")
        a(f"- usage keys: `{tu['usage_keys']}`")
        a(f"- usage (raw):\n\n```json\n{json.dumps(tu['usage'], indent=2)}\n```")
    else:
        a(f"- ERROR: {tu.get('error')}")
        flags.append(f"Thinking/usage probe failed: {tu.get('error')}")

    # 6. Provenance headers
    a("\n## 6. Provenance headers (request-id + rate limits)\n")
    h = results["headers"]
    if h.get("ok"):
        a(f"- `_request_id` attr: `{h['request_id_attr']}`")
        a(f"- relevant headers:\n\n```json\n{json.dumps(h['relevant_headers'], indent=2)}\n```")
        a(f"- all header keys: `{h['all_header_keys']}`")
    else:
        a(f"- ERROR: {h.get('error')}")

    # Escalations
    a("\n## ⚠️ Flagged for owner ruling (do NOT silently reconcile)\n")
    if flags:
        for i, f in enumerate(flags, 1):
            a(f"{i}. {f}")
    else:
        a("- None — all probed facts match the pinned values.")
    a(
        "\n> Next: owner rules on each; then update `SPEC.md` / `load-band-reference.md` "
        "with a version + timestamp (charter pre-registration discipline).\n"
    )

    return "\n".join(L)


# --------------------------------------------------------------------------- main
def main() -> None:
    print("Phase 0 live verification — probing", ", ".join(MODELS.values()))
    results = {}
    for name, fn in [
        ("tokenizer", probe_tokenizer),
        ("models", probe_models),
        ("cache", probe_cache),
        ("temperature", probe_temperature),
        ("thinking_usage", probe_thinking_usage),
        ("headers", probe_headers),
    ]:
        print(f"  · {name} ...", flush=True)
        results[name] = fn()

    report = build_report(results)
    out_path = DOCS / f"live-verification-{dt.date.today().isoformat()}.md"
    out_path.write_text(report, encoding="utf-8")
    raw_path = DOCS / f"live-verification-{dt.date.today().isoformat()}.raw.json"
    raw_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")

    print("\n" + report)
    print(f"\nWrote {out_path.relative_to(REPO_ROOT)} and {raw_path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
