"""harness/hashing.py — deterministic hashing shared by the schema and the config.

Lives in its own module (depending on neither ``schema`` nor ``config``) so the capture
record can *recompute and self-verify* its ``config_hash`` on construction and on load,
without a circular import. ``config_hash`` is duck-typed: it accepts a ``CallConfig`` (or
any object with ``model_dump``) or a plain dict.

Conventions (pinned here; see fixtures/manifest.yaml for the registry side):
  * ``canonical_json`` — sorted keys, compact separators, ``ensure_ascii=False`` so non-ASCII
    fixture content (e.g. the translate task) hashes by its actual characters.
  * ``fixture_hash`` — sha256 over canonical JSON ``{"input": …, "prompt": …}``. Domain-separated,
    NOT literal ``prompt + input`` concatenation, which collides ((``"a"``,``"b"``) vs
    (``"ab"``, None)). A prompt-only fixture hashes with ``input=null``, distinct from ``input=""``.
  * ``config_hash`` — sha256 over the resolved call config + tokenizer version (the tokenizer is
    part of identity: the same fixture is a different token count on Opus vs Haiku/Sonnet).
All digests are bare 64-char lowercase hex.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Optional, Union

_SHA256_HEX = re.compile(r"[0-9a-f]{64}")


def canonical_json(obj: Any) -> str:
    """Stable serialisation for hashing: sorted keys, no incidental whitespace, raw unicode."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def is_sha256_hex(s: str) -> bool:
    """True iff ``s`` is a bare 64-char lowercase-hex sha256 digest."""
    return bool(_SHA256_HEX.fullmatch(s))


def fixture_hash(prompt: str, input_text: Optional[str] = None) -> str:
    """sha256 of the fixture content, domain-separated so the (prompt, input) split is
    unambiguous. Matches the ``sha256`` a frozen fixture carries in the manifest."""
    return sha256_hex(canonical_json({"prompt": prompt, "input": input_text}))


def skill_hash(text: str) -> str:
    """sha256 of a skill's frozen bytes, domain-separated under ``{"skill": …}`` so it can
    never collide with a fixture hash. Matches the ``sha256`` a frozen skill carries in
    ``fixtures/skills/manifest.yaml`` and the ``skill_hash`` pinned on each skill-on record
    (Exp 1c)."""
    return sha256_hex(canonical_json({"skill": text}))


def judge_hash(components: dict) -> str:
    """sha256 of the frozen quality-judge instrument (Exp 1c judge-spec §2), domain-separated
    under ``{"judge": …}`` so it can never collide with a fixture or skill hash.

    ``components`` carries the exact pinned inputs the spec hashes — ``{judge_model, k,
    prompt_rubric, prompt_pairwise, rubrics, margin_pp}`` — and the digest is order-independent
    (``canonical_json`` sorts keys). Matches the ``judge_hash`` recorded in
    ``fixtures/judge/manifest.yaml`` and ``docs/phase1c-judge-spec.md`` §2, and stamped on every
    judging-output record so the grading replays from the record alone."""
    return sha256_hex(canonical_json({"judge": components}))


def fixture_hash_from_files(
    prompt_path: Union[str, Path], input_path: Optional[Union[str, Path]] = None
) -> str:
    """Convenience: hash a fixture straight from its files (text, utf-8)."""
    prompt = Path(prompt_path).read_text(encoding="utf-8")
    input_text = Path(input_path).read_text(encoding="utf-8") if input_path is not None else None
    return fixture_hash(prompt, input_text)


def config_hash(config: Any, *, tokenizer_version: str) -> str:
    """sha256 over the resolved call config + tokenizer version. Together with
    ``fixture_hash`` this pins "the exact fixture + full config" (CLAUDE.md invariant 3).

    ``config`` may be a ``CallConfig`` (anything with ``model_dump``) or a plain dict —
    duck-typed so this module need not import the schema (avoids a circular import).

    Back-compat (Exp 1c skill axis): a skill-less config (``skill is None``) hashes
    byte-identically to the pre-skill schema — the ``skill`` key is dropped before hashing —
    so every Phase-1a record still recomputes-and-verifies its ``config_hash`` on load. Only a
    real skill (the skill-on arm) perturbs the hash, which is exactly the new axis we want
    captured. This mirrors ``CellId.key()`` omitting ``skill_arm`` when ``off``: skill-off ==
    the pre-skill world, identical down to the digest."""
    payload = config.model_dump() if hasattr(config, "model_dump") else dict(config)
    if payload.get("skill") is None:
        payload.pop("skill", None)
    # Exp 1d neutral arm: same back-compat trick — a neutral=None config drops the key, so 1a/1c
    # records (which predate the field) recompute byte-identically. Only the neutral arm perturbs it.
    if payload.get("neutral") is None:
        payload.pop("neutral", None)
    payload["tokenizer_version"] = tokenizer_version
    return sha256_hex(canonical_json(payload))
