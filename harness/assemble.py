from __future__ import annotations
from typing import Any, Callable, Optional
from pydantic import BaseModel, ConfigDict
from harness.expand import RunUnit
from harness.hashing import fixture_hash, skill_hash

TURN_DELIM = "===TURN==="
PAYLOAD_TOOL = {
    "name": "provide_payload",
    "description": "Returns the dataset or batch of files to analyze.",
    "input_schema": {"type": "object", "properties": {}},
}
_PAYLOAD_TOOL_USE_ID = "toolu_payload_fixture"

class FixtureNotFrozen(RuntimeError): ...
class FixtureHashMismatch(RuntimeError): ...
class SkillNotFrozen(RuntimeError): ...
class SkillHashMismatch(RuntimeError): ...

class CallPlan(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    family: str
    fixture_hash: str
    messages: Optional[list] = None
    system: Optional[Any] = None
    tools: Optional[list] = None
    warm_message: Optional[dict] = None
    read_messages: Optional[list] = None
    turns: Optional[list[str]] = None
    tool_result_tokens: Optional[int] = None
    skill_hash: Optional[str] = None  # Exp 1c: sha256 of the injected skill (skill-on), else None
    def call_role_is_single(self) -> bool:
        return self.family in ("standard",)

def _system_block(unit: RunUnit, read_file: Callable[[str], str], *, require_frozen: bool
                  ) -> tuple[Optional[list], Optional[str]]:
    """Resolve the injected `system` block for a factorial unit: the skill (skill-on arm, Exp 1c) OR
    the neutral control block (neutral arm, Exp 1d) — at most one is set. Same frozen + hash
    discipline fixtures get (CLAUDE.md invariant 5): the bytes are read, hashed, and verified against
    the manifest digest before they can ride on a call. Returns ``(system, hash)`` — ``(None, None)``
    for the "off" arm and every Phase-1a cell.

    The block is injected UNCACHED (a plain system text block): its input cost is part of what we
    measure, and caching would drag the cache-hit machinery onto the standard family. The config
    carrying ``skill``/``neutral`` and the record carrying ``skill_hash`` are checked for mutual
    agreement downstream (harness.schema), so an entry without a matching config field can't slip by."""
    entry = unit.skill_entry if unit.skill_entry is not None else unit.neutral_entry
    if entry is None:
        return None, None
    text = read_file(entry.file)
    digest = skill_hash(text)
    if require_frozen:
        if not entry.frozen:
            raise SkillNotFrozen(f"system block {entry.id!r} is not frozen")
        if entry.sha256 != digest:
            raise SkillHashMismatch(
                f"system block {entry.id!r}: recorded {entry.sha256} != {digest}")
    return [{"type": "text", "text": text}], digest


def assemble(unit: RunUnit, read_file: Callable[[str], str], *, require_frozen: bool = True) -> CallPlan:
    prompt = read_file(unit.fixture.files.prompt)
    input_text = read_file(unit.fixture.files.input) if unit.fixture.files.input else None
    digest = fixture_hash(prompt, input_text)
    if require_frozen:
        if not unit.fixture.frozen:
            raise FixtureNotFrozen(f"task {unit.cell_id.task_id}/{unit.cell_id.band} fixture is not frozen")
        if unit.fixture.sha256 != digest:
            raise FixtureHashMismatch(
                f"task {unit.cell_id.task_id}/{unit.cell_id.band}: recorded {unit.fixture.sha256} != {digest}")
    if unit.family == "standard":
        content = prompt if input_text is None else f"{prompt}\n\n{input_text}"
        system, skill_h = _system_block(unit, read_file, require_frozen=require_frozen)
        return CallPlan(family="standard", fixture_hash=digest,
                        messages=[{"role": "user", "content": content}],
                        system=system, skill_hash=skill_h)
    if unit.family == "cache":
        if input_text is None:
            raise ValueError("cache fixture requires an input.md (the cached prefix)")
        return CallPlan(
            family="cache", fixture_hash=digest,
            system=[{"type": "text", "text": input_text, "cache_control": {"type": "ephemeral"}}],
            warm_message={"role": "user", "content": "Reply only: ready."},
            read_messages=[{"role": "user", "content": prompt}],
        )
    if unit.family == "multiturn":
        turns = [t.strip() for t in prompt.split(TURN_DELIM)]
        if input_text is not None:
            turns[0] = f"{input_text}\n\n{turns[0]}"
        return CallPlan(family="multiturn", fixture_hash=digest, turns=turns)
    if unit.family == "payload":
        if input_text is None:
            raise ValueError("payload fixture requires an input.md (the payload artifact)")
        messages = [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": [
                {"type": "tool_use", "id": _PAYLOAD_TOOL_USE_ID, "name": "provide_payload", "input": {}}]},
            {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": _PAYLOAD_TOOL_USE_ID, "content": input_text}]},
        ]
        return CallPlan(family="payload", fixture_hash=digest, tools=[PAYLOAD_TOOL], messages=messages)
    raise NotImplementedError(unit.family)
