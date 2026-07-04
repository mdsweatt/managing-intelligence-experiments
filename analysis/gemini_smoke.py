"""Gemini meter-verification smoke test — Phase 1d build (NOT the frozen judge).

Makes N identical small calls to a pinned Gemini model and prints exact per-call
`usage_metadata` + aggregate totals, so you can reconcile against AI Studio:
  * AI Studio > Usage shows request count + token counts (immediately),
  * $ spend accrues in Google Cloud Billing for the Generative Language API (may lag hours).

Consistency check (this project's own logic): with a fixed prompt + temperature 0,
`prompt_token_count` is identical on every call (deterministic input); candidates +
thoughts vary by model sampling. A single value in "prompt tokens/call" is the
"input accounting is exact/repeatable" signal. (gemini-2.5-pro mandates thinking, so
`thoughts_token_count` is non-zero and varies — exactly why the judge-spec captures it
separately.)

BILLABLE (tiny — hundreds of tokens for the default run). Run while watching AI Studio:

    uv run python -m analysis.gemini_smoke --n 10 --model gemini-2.5-pro

Bump --n or --max-output-tokens if the $ line on the dashboard is too small to see.
This is a throwaway diagnostic; the frozen judge instrument comes later.
"""
from __future__ import annotations

import argparse
import statistics as st
from pathlib import Path

from dotenv import load_dotenv
import google.genai as g
from google.genai import types

PROMPT = ('You are a strict grader. Reply with ONLY the JSON object '
          '{"verdict":"pass"} — no prose, no code fence.')


def _safe_text(resp) -> str:
    try:
        return resp.text or ""
    except Exception:
        return "<no text / blocked>"


def main() -> None:
    ap = argparse.ArgumentParser(description="Gemini meter-verification smoke test (billable, tiny).")
    ap.add_argument("--model", default="gemini-2.5-pro")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--max-output-tokens", type=int, default=512)  # room for the answer alongside thinking
    # Pin the thinking control to test acceptance on the pinned judge model. 3.x is preview-only and
    # may expose `thinking_level` rather than `thinking_budget` — probe whichever the model accepts.
    ap.add_argument("--thinking-budget", type=int, default=None,
                    help="set ThinkingConfig(thinking_budget=N); 2.5-pro rejects 0 (->400)")
    ap.add_argument("--thinking-level", default=None,
                    help="set ThinkingConfig(thinking_level=STR) instead (3.x surface)")
    args = ap.parse_args()

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")  # repo-root .env -> GEMINI_API_KEY
    client = g.Client()
    thinking = None
    if args.thinking_budget is not None:
        thinking = types.ThinkingConfig(thinking_budget=args.thinking_budget)
    elif args.thinking_level is not None:
        thinking = types.ThinkingConfig(thinking_level=args.thinking_level)
    cfg = types.GenerateContentConfig(
        max_output_tokens=args.max_output_tokens,
        temperature=0,  # deterministic input; gemini-2.5-pro MANDATES thinking (budget 0 -> 400), so
                        # with no --thinking-* flag thinking is left at the model default.
        thinking_config=thinking,  # None => model default; else the pinned budget/level probed above
    )

    thinking_desc = (f"budget={args.thinking_budget}" if args.thinking_budget is not None
                     else f"level={args.thinking_level}" if args.thinking_level is not None
                     else "default")
    print(f"model={args.model}  n={args.n}  thinking={thinking_desc}  temperature=0\n")
    prompts, cands, thoughts, totals = [], [], [], []
    bad = 0
    for i in range(args.n):
        resp = client.models.generate_content(model=args.model, contents=PROMPT, config=cfg)
        um = resp.usage_metadata
        p = (getattr(um, "prompt_token_count", None) or 0) if um else 0
        cnd = (getattr(um, "candidates_token_count", None) or 0) if um else 0
        th = (getattr(um, "thoughts_token_count", None) or 0) if um else 0
        tot = (getattr(um, "total_token_count", None) or 0) if um else 0
        if tot == 0:  # docs: a failed/blocked call reports usage 0 — flag, don't trust it
            bad += 1
            print(f"  call {i + 1:2}: TOTAL=0  <-- FLAG (error/blocked)  text={_safe_text(resp)[:50]!r}")
            continue
        prompts.append(p); cands.append(cnd); thoughts.append(th); totals.append(tot)
        print(f"  call {i + 1:2}: prompt={p:4}  candidates={cnd:4}  thoughts={th:4}  total={tot:4}")

    print("\n--- aggregate (reconcile against AI Studio > Usage) ---")
    print(f"  model:             {args.model}")
    print(f"  successful calls:  {len(totals)}   flagged/zero: {bad}")
    if totals:
        cov = (st.pstdev(cands) / st.mean(cands)) if st.mean(cands) else 0.0
        print(f"  prompt tokens/call: {sorted(set(prompts))}  (single value => deterministic input)")
        print(f"  candidates: sum={sum(cands)}  mean={st.mean(cands):.1f}  CoV={cov:.3f}")
        print(f"  thoughts:   sum={sum(thoughts)}")
        print(f"  TOTAL TOKENS THIS RUN: {sum(totals)}   <-- expect AI Studio to show ~this on {args.model}")
    print("\nNote: token usage shows in AI Studio > Usage right away; the $ line in Cloud Billing")
    print("(Generative Language API) can lag by hours. The token reconciliation is the precise check.")


if __name__ == "__main__":
    main()
