"""Tests for harness.fixtures — fixture measurement + freeze tooling (Phase 3).

The tooling measures the TWO token counts per fixture (tok-hs = Haiku/Sonnet shared,
tok-opus = Opus differs ~+35%), classifies the band by order-of-magnitude anchors,
enforces the Haiku cache floor, and verifies a frozen fixture's bytes still hash to its
recorded sha256. Token counting is injected (a fake counter) so tests cost no API.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from harness.fixtures import (
    BAND_ANCHORS,
    assert_cache_floor,
    classify_band,
    count_two,
    measure_files,
    verify_frozen_artifact,
)
from harness.hashing import fixture_hash


def _fake_counter():
    # Opus runs ~+35% hotter than the shared Haiku/Sonnet tokenizer (live-verified).
    def _c(model: str, text: str) -> int:
        base = len(text.split())
        return int(base * 1.35) if "opus" in model else base

    return _c


def test_count_two_returns_both_tokenizers():
    counts = count_two("a b c", "d e f g", counter=_fake_counter())
    # 7 words combined → tok_hs=7, tok_opus=floor(7*1.35)=9
    assert counts["tok_hs"] == 7
    assert counts["tok_opus"] == 9
    assert counts["tok_opus"] > counts["tok_hs"]  # Opus is the hotter count


def test_count_two_handles_prompt_only():
    counts = count_two("one two three", None, counter=_fake_counter())
    assert counts["tok_hs"] == 3


def test_classify_band_maps_to_nearest_order_of_magnitude():
    assert classify_band(950) == "S"  # ~1K
    assert classify_band(9000) == "M"  # ~10K
    assert classify_band(88000) == "L"  # ~100K
    # Order-of-magnitude spacing is what matters; a value between anchors goes to the nearer.
    assert classify_band(1400) == "S"
    assert classify_band(40000) == "L"  # closer to 100K than 10K on a log scale? check intent


def test_assert_cache_floor_blocks_below_4096_when_haiku_probed():
    with pytest.raises(ValueError):
        assert_cache_floor(2745, haiku_probed=True)
    assert_cache_floor(4513, haiku_probed=True)  # ok
    assert_cache_floor(2000, haiku_probed=False)  # not Haiku → no floor


def test_measure_files_reads_prompt_and_input(tmp_path):
    (tmp_path / "prompt.txt").write_text("summarize this", encoding="utf-8")
    (tmp_path / "input.md").write_text("one two three four five", encoding="utf-8")
    out = measure_files(tmp_path / "prompt.txt", tmp_path / "input.md", counter=_fake_counter())
    assert out["tok_hs"] == len("summarize this one two three four five".split())
    assert out["sha256"] == fixture_hash("summarize this", "one two three four five")


def test_verify_frozen_artifact_detects_tampering(tmp_path):
    p = tmp_path / "prompt.txt"
    i = tmp_path / "input.md"
    p.write_text("P", encoding="utf-8")
    i.write_text("I", encoding="utf-8")
    digest = fixture_hash("P", "I")
    assert verify_frozen_artifact(p, i, digest) is True
    i.write_text("I-CHANGED", encoding="utf-8")
    assert verify_frozen_artifact(p, i, digest) is False
