# Live API Verification — 2026-06-16

**SDK:** anthropic 0.109.2  |  **Models:** haiku=`claude-haiku-4-5-20251001`, sonnet=`claude-sonnet-4-6`, opus=`claude-opus-4-8`

Confirms/corrects the 2026-06-15 pinned facts in `SPEC.md` / `load-band-reference.md`. Discrepancies are flagged for owner ruling — **not** auto-applied (pre-registration discipline).


## 1. Tokenizer sharing

- count_tokens of the sample paragraph: `{'haiku': 66, 'sonnet': 66, 'opus': 89}`
- **Shared across all three:** NO ✗
- Pinned: shared-v1 across Haiku 4.5 / Sonnet 4.6 / Opus 4.8 (one count per fixture)

## 2. Models API (ceilings, effort, thinking capabilities)

### haiku — `claude-haiku-4-5-20251001`
- max_input_tokens: `200000`  |  max_tokens (output ceiling): `64000`
- pinned max_output: `64000`
- capabilities (raw):

```json
{
  "batch": {
    "supported": true
  },
  "citations": {
    "supported": true
  },
  "code_execution": {
    "supported": false
  },
  "context_management": {
    "clear_thinking_20251015": {
      "supported": true
    },
    "clear_tool_uses_20250919": {
      "supported": true
    },
    "compact_20260112": {
      "supported": false
    },
    "supported": true
  },
  "effort": {
    "high": {
      "supported": false
    },
    "low": {
      "supported": false
    },
    "max": {
      "supported": false
    },
    "medium": {
      "supported": false
    },
    "supported": false,
    "xhigh": {
      "supported": false
    }
  },
  "image_input": {
    "supported": true
  },
  "pdf_input": {
    "supported": true
  },
  "structured_outputs": {
    "supported": true
  },
  "thinking": {
    "supported": true,
    "types": {
      "adaptive": {
        "supported": false
      },
      "enabled": {
        "supported": true
      }
    }
  }
}
```
### sonnet — `claude-sonnet-4-6`
- max_input_tokens: `1000000`  |  max_tokens (output ceiling): `128000`
- pinned max_output: `64000`
- capabilities (raw):

```json
{
  "batch": {
    "supported": true
  },
  "citations": {
    "supported": true
  },
  "code_execution": {
    "supported": true
  },
  "context_management": {
    "clear_thinking_20251015": {
      "supported": true
    },
    "clear_tool_uses_20250919": {
      "supported": true
    },
    "compact_20260112": {
      "supported": true
    },
    "supported": true
  },
  "effort": {
    "high": {
      "supported": true
    },
    "low": {
      "supported": true
    },
    "max": {
      "supported": true
    },
    "medium": {
      "supported": true
    },
    "supported": true,
    "xhigh": {
      "supported": false
    }
  },
  "image_input": {
    "supported": true
  },
  "pdf_input": {
    "supported": true
  },
  "structured_outputs": {
    "supported": true
  },
  "thinking": {
    "supported": true,
    "types": {
      "adaptive": {
        "supported": true
      },
      "enabled": {
        "supported": true
      }
    }
  }
}
```
### opus — `claude-opus-4-8`
- max_input_tokens: `1000000`  |  max_tokens (output ceiling): `128000`
- pinned max_output: `128000`
- capabilities (raw):

```json
{
  "batch": {
    "supported": true
  },
  "citations": {
    "supported": true
  },
  "code_execution": {
    "supported": true
  },
  "context_management": {
    "clear_thinking_20251015": {
      "supported": true
    },
    "clear_tool_uses_20250919": {
      "supported": true
    },
    "compact_20260112": {
      "supported": true
    },
    "supported": true
  },
  "effort": {
    "high": {
      "supported": true
    },
    "low": {
      "supported": true
    },
    "max": {
      "supported": true
    },
    "medium": {
      "supported": true
    },
    "supported": true,
    "xhigh": {
      "supported": true
    }
  },
  "image_input": {
    "supported": true
  },
  "pdf_input": {
    "supported": true
  },
  "structured_outputs": {
    "supported": true
  },
  "thinking": {
    "supported": true,
    "types": {
      "adaptive": {
        "supported": true
      },
      "enabled": {
        "supported": false
      }
    }
  }
}
```

## 3. Cache minimums (warm-write probe at ~1500 / ~3000 / ~5000 tokens)

### haiku — `claude-haiku-4-5-20251001`
| target | approx prefix tok | cache_creation | cache_read | input | cached? |
|---|---|---|---|---|---|
| 1500 | 1388 | 0 | 0 | 1388 | no |
| 3000 | 2745 | 0 | 0 | 2745 | no |
| 5000 | 4513 | 4504 | 0 | 9 | YES |
- **Inferred minimum:** engages by ~4513 tokens; did NOT engage at ~2745  |  pinned: `4096`

### sonnet — `claude-sonnet-4-6`
| target | approx prefix tok | cache_creation | cache_read | input | cached? |
|---|---|---|---|---|---|
| 1500 | 1391 | 1382 | 0 | 9 | YES |
| 3000 | 2747 | 2738 | 0 | 9 | YES |
| 5000 | 4519 | 4510 | 0 | 9 | YES |
- **Inferred minimum:** engages by ~1391 tokens  |  pinned: `1024`

### opus — `claude-opus-4-8`
| target | approx prefix tok | cache_creation | cache_read | input | cached? |
|---|---|---|---|---|---|
| 1500 | 1447 | 1437 | 0 | 10 | YES |
| 3000 | 2854 | 2844 | 0 | 10 | YES |
| 5000 | 4768 | 4758 | 0 | 10 | YES |
- **Inferred minimum:** engages by ~1447 tokens  |  pinned: `1024`


## 4. Temperature & sampling settability

- Pinned: settable (realistic-default) for non-thinking cells; NOT settable with thinking on

### haiku — `claude-haiku-4-5-20251001`
- temperature=0.7, thinking OFF → OK ✓
### sonnet — `claude-sonnet-4-6`
- temperature=0.7, thinking OFF → OK ✓
- temperature=0.7, thinking ON → REJECTED ✗ (400 invalid_request_error: Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': '`temperature` may only be set to 1 when thinking is enabled or in adaptive mode. Please consult our documentation at https://docs.claude.com/en/docs/build-with-claude/extended-thinking#important-considerations)
### opus — `claude-opus-4-8`
- temperature=0.7, thinking OFF → REJECTED ✗ (400 invalid_request_error: Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': '`temperature` is deprecated for this model.'}, 'request_id': 'req_REDACTED'})
- temperature=0.7, thinking ON → REJECTED ✗ (400 invalid_request_error: Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': '`temperature` may only be set to 1 when thinking is enabled or in adaptive mode. Please consult our documentation at https://docs.claude.com/en/docs/build-with-claude/extended-thinking#important-considerations)

## 5. Thinking + usage object shape (Opus, adaptive, effort=low)

- stop_reason: `end_turn`  |  block types: `['thinking', 'text']`
- usage keys: `['cache_creation', 'cache_creation_input_tokens', 'cache_read_input_tokens', 'inference_geo', 'input_tokens', 'output_tokens', 'output_tokens_details', 'server_tool_use', 'service_tier']`
- usage (raw):

```json
{
  "cache_creation": {
    "ephemeral_1h_input_tokens": 0,
    "ephemeral_5m_input_tokens": 0
  },
  "cache_creation_input_tokens": 0,
  "cache_read_input_tokens": 0,
  "inference_geo": "global",
  "input_tokens": 26,
  "output_tokens": 59,
  "output_tokens_details": {
    "thinking_tokens": 11
  },
  "server_tool_use": null,
  "service_tier": "standard"
}
```

### Addendum (2026-06-21) — streaming drops `output_tokens_details` (SDK 0.109.2)

The §5 probe above used a **non-streaming** `messages.create()`, so it saw
`output_tokens_details.thinking_tokens` populated. The harness **streams every call**
(item 6 below), and under streaming the field is **lost**: SDK 0.109.2's `MessageStream`
accumulator (`anthropic/lib/streaming/_messages.py` → `accumulate_event`) copies every
usage field from the `message_delta` event **except** `output_tokens_details`, so
`stream.get_final_message().usage.output_tokens_details` comes back `null` on a thinking
call. Phase 0's #15 cells captured `thinking_tokens: 0` for exactly this reason.

The count still rides on the `message_delta` event. Fix (commit `e5c7106`): `stream_call`
iterates the stream and recovers `output_tokens_details` from the delta, overlaying it when
the final snapshot's value is null. **Verified live 2026-06-21** (streaming Sonnet, adaptive,
effort=high): `message_delta` → `{"thinking_tokens": 194}`, final snapshot → `null`,
`stream_call` recovers it. So the "Confirmed as pinned" line below (`thinking_tokens` at
`usage.output_tokens_details.thinking_tokens`) holds for the **field location**, but only
non-streaming populates it directly — streamed capture must recover it from the delta.

**Sub-addendum (2026-06-23) — recovery confirmed on Opus 4.8 + fail-loud backstop.** The
2026-06-21 verification above was on **Sonnet**; Opus 4.8 was still unverified — and the cells
that depend on it (#15 thinking-depth, #16 matched-thinking) are Opus. Re-verified live
**2026-06-23** through the real path (`harness.client.stream_call`, adaptive, effort=high): Opus
4.8's `message_delta` **does** carry `output_tokens_details`, and `stream_call` recovers it —
captured `{"thinking_tokens": 29}`, `stop_reason=end_turn`. The recovery holds across the ladder
(Sonnet **and** Opus), not Sonnet-only.

**Defense in depth (commit `23fd3aa`):** the capture contract now also rejects a thinking call
whose `usage_raw["output_tokens_details"]` is **absent OR present-but-null** (previously only the
absent case was caught; present-but-null slipped through and `from_raw` silently projected
`thinking_tokens=0` at full output cost). So if the recovery ever misses on a future SDK/model,
the record fails loud on the first call rather than entering the dataset as a silent zero —
closing the last silent re-run risk in the thinking path.

## 6. Provenance headers (request-id + rate limits)

- `_request_id` attr: `req_REDACTED`
- relevant headers:

```json
{
  "anthropic-ratelimit-input-tokens-limit": "50000",
  "anthropic-ratelimit-input-tokens-remaining": "50000",
  "anthropic-ratelimit-input-tokens-reset": "2026-06-17T03:27:02Z",
  "anthropic-ratelimit-output-tokens-limit": "10000",
  "anthropic-ratelimit-output-tokens-remaining": "10000",
  "anthropic-ratelimit-output-tokens-reset": "2026-06-17T03:27:03Z",
  "anthropic-ratelimit-requests-limit": "50",
  "anthropic-ratelimit-requests-remaining": "49",
  "anthropic-ratelimit-requests-reset": "2026-06-17T03:27:03Z",
  "anthropic-ratelimit-tokens-limit": "60000",
  "anthropic-ratelimit-tokens-remaining": "60000",
  "anthropic-ratelimit-tokens-reset": "2026-06-17T03:27:02Z",
  "request-id": "req_REDACTED"
}
```
- all header keys: `['anthropic-organization-id', 'anthropic-ratelimit-input-tokens-limit', 'anthropic-ratelimit-input-tokens-remaining', 'anthropic-ratelimit-input-tokens-reset', 'anthropic-ratelimit-output-tokens-limit', 'anthropic-ratelimit-output-tokens-remaining', 'anthropic-ratelimit-output-tokens-reset', 'anthropic-ratelimit-requests-limit', 'anthropic-ratelimit-requests-remaining', 'anthropic-ratelimit-requests-reset', 'anthropic-ratelimit-tokens-limit', 'anthropic-ratelimit-tokens-remaining', 'anthropic-ratelimit-tokens-reset', 'cf-cache-status', 'cf-ray', 'connection', 'content-encoding', 'content-security-policy', 'content-type', 'date', 'request-id', 'server', 'strict-transport-security', 'traceresponse', 'transfer-encoding', 'vary', 'x-robots-tag']`

## ⚠️ Flagged for owner ruling (do NOT silently reconcile)

1. Tokenizer is NOT shared across the ladder — Rule 2 re-arms; fixtures need a per-model token count (not one count).
2. sonnet max_output is 128000 (pinned 64000).
3. Opus 4.8 REJECTS temperature even with thinking OFF — breaks D2 'hold config fixed, swap only the model' for the temperature control across a Sonnet→Opus over-service comparison. Owner ruling needed.

4. **Tokenizer detail:** Haiku 4.5 and Sonnet 4.6 share a tokenizer (sample = 66 tokens each); **Opus 4.8 differs (89 tokens, ~+35%)** — matches the charter's Opus-4.7 caveat. A fixture therefore has **two** token counts (Haiku/Sonnet vs Opus), not one. The Sonnet→Opus over-service number = price-ratio × **input-token inflation (~1.35×)**, not price-ratio alone (SPEC D2's "dominated by the per-token price ratio" no longer holds for Opus comparisons).
5. **[SUPERSEDED 2026-06-22 — tier since raised; see addendum at end of file.]** **Rate limits are low (≈ tier 1):** ITPM 50,000 input tok/min · OTPM 10,000 output/min · 50 requests/min · 60,000 tokens/min. **An L-band fixture (~100k input) exceeds the 50k ITPM in a single call → not runnable at ~100k on this tier** (affects #7-L, #8-L, #10-L, #12-L). OTPM 10k/min also throttles thinking-max (#15) and long-form (#9) output. Resolve before any L-band run: limit increase / Batches API / shrink the L anchor.
6. **`max_tokens` = ceiling ⇒ stream everywhere:** ceilings are 64k–128k; a non-streaming call with max_tokens that high trips the SDK's long-request timeout guard (`ValueError`). Plan: **stream every call** and read final accumulated usage — uniform capture, no truncation, sidesteps the guard.

**Confirmed as pinned (no change needed):** cache minimums (Haiku 4096, Sonnet 1024, Opus 1024), Opus max-output (128k), effort levels (Opus low–max+xhigh; Sonnet low–max no xhigh; Haiku none), `thinking_tokens` at `usage.output_tokens_details.thinking_tokens`, adaptive thinking on Sonnet/Opus.

> Next: owner rules on each; then update `SPEC.md` / `load-band-reference.md` / `runs/*.yaml` with a version + timestamp (charter pre-registration discipline).

### Addendum (2026-06-22) — rate tier raised; re-verified live

Re-probed the `anthropic-ratelimit-*` response headers per model (3 minimal `messages` calls). The
tier-1 limits captured above (50k ITPM / 10k OTPM / 50 rpm on 2026-06-16, and still 50k in the
2026-06-21 addendum) have been **raised**. Live as of 2026-06-22:

| Model | ITPM (input) | OTPM (output) | RPM | tokens/min |
|---|---|---|---|---|
| Haiku 4.5 (`claude-haiku-4-5-20251001`) | 450,000 | 90,000 | 1,000 | 540,000 |
| Sonnet 4.6 (`claude-sonnet-4-6`) | 450,000 | 90,000 | 1,000 | 540,000 |
| Opus 4.8 (`claude-opus-4-8`) | 2,000,000 | 200,000 | 1,000 | 2,200,000 |

**Item 5 is superseded.** A ~100k-token L-band input now fits one call on every model (Opus has 2M
ITPM; Haiku/Sonnet 450k). #7-L on Opus (55,427 input tok) fits with wide headroom. The L-band
deferral therefore rests on **sourcing effort only**, not the rate tier. (`runs/phase1a.yaml` and
SPEC §8 carried `itpm 450k as_of 2026-06-16`; that was premature — the captures show 50k through
2026-06-21. The 450k / 2M tier is confirmed effective 2026-06-22.) OTPM is now 90k–200k/min, so the
earlier thinking-max (#15) / long-form (#9) OTPM-throttle concern is also relieved.
