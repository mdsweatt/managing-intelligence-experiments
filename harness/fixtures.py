"""harness/fixtures.py — fixture measurement + freeze tooling (Experiment 1, Phase 3).

Curation is owner work (CLAUDE.md invariant 5: fixtures are decided in advance and frozen).
This module does the *mechanical* half so the owner doesn't have to: it measures the TWO
token counts a fixture has (the tokenizer is NOT shared — Haiku/Sonnet = tok-hs, Opus =
tok-opus, ~+35%), classifies the band by order-of-magnitude anchor, enforces the Haiku cache
floor, and verifies a frozen artifact's bytes still hash to its recorded sha256.

Measuring uses the live ``count_tokens`` endpoint (free) via an injected counter, so the
counts are MEASURED, never estimated (invariant 1). Token counting is the only live call;
freezing is a local hash + manifest edit the owner applies once content is final.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Callable, Optional, Union

from harness.hashing import fixture_hash, fixture_hash_from_files

# The two tokenizers, identified by a representative model id for count_tokens.
TOK_HS_MODEL = "claude-sonnet-4-6"  # Haiku 4.5 & Sonnet 4.6 share this tokenizer (tok-hs)
TOK_OPUS_MODEL = "claude-opus-4-8"  # Opus 4.8 differs ~+35% (tok-opus)

# Order-of-magnitude regime markers (load-band §3). The band labels a regime, not an exact
# count — what matters is that a task's fixtures land in DISTINCT regimes (Rule 1).
BAND_ANCHORS: dict[str, int] = {"S": 1_000, "M": 10_000, "L": 100_000}

HAIKU_CACHE_FLOOR = 4_096  # Haiku's cache minimum; below it, caching silently won't engage

Counter = Callable[[str, str], int]


def count_two(prompt: str, input_text: Optional[str], *, counter: Counter) -> dict[str, int]:
    """Measure the fixture's token count under BOTH tokenizers.

    Counts the combined (prompt + input) content as it is sent, once per tokenizer. The two
    counts differ because Opus's tokenizer is hotter — both are recorded per fixture."""
    text = prompt if input_text is None else f"{prompt}\n\n{input_text}"
    return {
        "tok_hs": counter(TOK_HS_MODEL, text),
        "tok_opus": counter(TOK_OPUS_MODEL, text),
    }


def classify_band(token_count: int, anchors: dict[str, int] = BAND_ANCHORS) -> str:
    """Return the band whose anchor is nearest on a LOG scale (order-of-magnitude spacing)."""
    if token_count <= 0:
        raise ValueError("token_count must be positive")
    lc = math.log10(token_count)
    return min(anchors, key=lambda b: abs(lc - math.log10(anchors[b])))


def assert_cache_floor(token_count: int, *, haiku_probed: bool) -> None:
    """A Haiku-probed cache cell must floor its cached segment at ≥4,096 tokens, else caching
    engages on Sonnet/Opus but silently NOT on Haiku — a threshold artifact, not a real result."""
    if haiku_probed and token_count < HAIKU_CACHE_FLOOR:
        raise ValueError(
            f"cached segment is {token_count} tokens; Haiku-probed cache cells need "
            f"≥{HAIKU_CACHE_FLOOR} so caching engages uniformly across the ladder"
        )


def make_counter(client) -> Counter:
    """Build a live counter from an anthropic client (uses the free count_tokens endpoint)."""

    def _count(model: str, text: str) -> int:
        return client.messages.count_tokens(
            model=model, messages=[{"role": "user", "content": text}]
        ).input_tokens

    return _count


def measure_files(
    prompt_path: Union[str, Path],
    input_path: Optional[Union[str, Path]] = None,
    *,
    counter: Counter,
) -> dict:
    """Measure a fixture straight from its files: the two token counts, the per-tokenizer band
    classification, and the sha256 that pins it. Returns the fields a manifest entry records."""
    prompt = Path(prompt_path).read_text(encoding="utf-8")
    input_text = Path(input_path).read_text(encoding="utf-8") if input_path is not None else None
    counts = count_two(prompt, input_text, counter=counter)
    return {
        "tok_hs": counts["tok_hs"],
        "tok_opus": counts["tok_opus"],
        "band_hs": classify_band(counts["tok_hs"]),
        "band_opus": classify_band(counts["tok_opus"]),
        "sha256": fixture_hash(prompt, input_text),
    }


def verify_frozen_artifact(
    prompt_path: Union[str, Path],
    input_path: Optional[Union[str, Path]],
    expected_sha256: str,
) -> bool:
    """True iff the artifact's current bytes still hash to its recorded sha256 (immutability check)."""
    return fixture_hash_from_files(prompt_path, input_path) == expected_sha256
