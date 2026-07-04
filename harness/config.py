"""harness/config.py — typed config validation (Experiment 1, Phase 1).

The other half of the capture contract: the Pydantic models the harness validates
`runs/*.yaml`, `fixtures/manifest.yaml`, and `prices/*.yaml` through *before* it runs.
The hash functions that pin every record to its exact fixture + config (CLAUDE.md
invariant 3) live in `harness.hashing` and are re-exported here for convenience.

Every model is ``extra="forbid"`` — an unrecognised key in a hand-edited YAML fails loud
rather than being silently ignored. Closed-vocabulary fields (tokenizer, cost_axis,
model roles, proxy type, …) are typed as ``Literal`` so a typo fails loud too — a
``tokenizer`` typo would otherwise silently corrupt ``config_hash`` and break the
across-cell single-axis control. The loaders round-trip the real repo files (see
tests/test_config.py), so model drift is caught immediately.
"""

from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import Any, Literal, Optional, Union

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

# Re-exported so existing callers (and tests) can `from harness.config import config_hash`.
from harness.hashing import (  # noqa: F401
    canonical_json,
    config_hash,
    fixture_hash,
    fixture_hash_from_files,
    is_sha256_hex,
    skill_hash,
)

# Call-side vocab is owned by harness.schema (single source of truth); config-side below.
from harness.schema import EFFORT, MODEL_ROLE

TOKENIZER = Literal["tok-hs", "tok-opus"]
COST_AXIS = Literal["input", "output", "turns", "payload", "cached_context", "thinking_depth"]
PROXY_TYPE = Literal["words", "pages", "lines", "files", "turns"]

# A value that is a real number/int once curated, or the literal "TBD" placeholder until then.
IntOrTBD = Union[int, Literal["TBD"]]
NumOrTBD = Union[float, Literal["TBD"]]

_STRICT = ConfigDict(extra="forbid")


# ===========================================================================  run matrix
# Mirrors runs/phase1a.yaml (the machine form of docs/SPEC.md §3).


class RateTier(BaseModel):
    model_config = _STRICT
    itpm: int
    otpm: int
    rpm: int
    as_of: _dt.date


class RunMeta(BaseModel):
    model_config = _STRICT
    phase: str
    derived_from: str
    n_per_cell: int = Field(gt=0)
    universal_opus_status: str
    gate: str
    cost_ceiling_usd: int = Field(gt=0)
    verified_live: _dt.date
    rate_tier: RateTier


class Defaults(BaseModel):
    model_config = _STRICT
    max_tokens: str  # sentinel "model_ceiling" — resolved per model at expansion time
    temperature: str  # "omit"
    effort: EFFORT  # global default ("high"); typo'd effort levels fail loud


class OverServiceRule(BaseModel):
    model_config = _STRICT
    rule: str
    optional_as_used: bool


class ModelSpec(BaseModel):
    model_config = _STRICT
    id: str
    tokenizer: TOKENIZER  # tok-hs (Haiku/Sonnet, shared) | tok-opus (differs ~+35%)
    cache_min: int
    max_output: int


class TaskCacheSpec(BaseModel):
    model_config = _STRICT
    mode: str  # warm_once_read_many
    assert_hit: bool
    min_floor_if_haiku: Optional[int] = None


class MultiturnSpec(BaseModel):
    model_config = _STRICT
    scripted: bool
    per_turn_capture: bool


class TaskSpec(BaseModel):
    model_config = _STRICT
    id: int
    name: str
    cost_axis: COST_AXIS
    bands: list[str]  # band labels are cross-axis (S/M/L, low/high/max, few/many) — kept free
    # Phase-1a ladder: a task declares its hypothesised minimum-sufficient tier (+ optional
    # over-service / down-probe swaps). Exp 1c instead declares `factorial_models` + `skill`
    # and runs the skill×model crossing. Exactly one of (hypothesis, factorial_models) is set.
    hypothesis: Optional[MODEL_ROLE] = None
    over_service: Optional[list[MODEL_ROLE]] = None
    down_probe: Optional[list[MODEL_ROLE]] = None
    equivalence: Optional[Literal["exact_match", "schema_match"]] = None  # D3 output-equivalence
    note: Optional[str] = None
    cache: Optional[TaskCacheSpec] = None
    thinking: Optional[Literal["adaptive", "enabled", "off"]] = None  # for #15/#16
    temperature: Optional[str] = None  # "uncontrolled" for #15
    bands_are_effort: Optional[bool] = None
    multiturn: Optional[MultiturnSpec] = None
    # Exp 1c (determinism A/B): the models to cross with skill {off,on}, and the skill id (a
    # frozen entry in skills/manifest.yaml) injected on the skill-on arm.
    factorial_models: Optional[list[MODEL_ROLE]] = None
    skill: Optional[str] = None
    # Exp 1d: the id of a frozen neutral-system block (neutral/manifest.yaml) for the H8 control arm.
    # OPTIONAL even for factorial tasks — a task with it gets the 3rd (neutral) arm; one without it
    # (e.g. the #4 placebo, or any 1c matrix) stays 2-arm {off,on}.
    neutral: Optional[str] = None
    # Exp 1d: restrict which factorial arms run. None (default) = the full set ({off,on} + neutral
    # when declared). The skill-off pilot (runs/phase1d-pilot.yaml) runs `arms: [off]` — measuring
    # the natural loose output BEFORE the skills/labels freeze, so `skill` is only required when the
    # effective arm set actually includes "on".
    arms: Optional[list[Literal["off", "neutral", "on"]]] = None
    # Exp 1d H7: the pre-registered cap/mandate label — sign(scaffold demand − skill-off mean output)
    # — FROZEN in runs/phase1d.yaml before the N=20 run (charter §3 H7; no relabeling after data).
    # None = outside the H7 headline (the #4 placebo, a boundary-flagged task, or any 1c matrix).
    h7_label: Optional[Literal["cap", "mandate"]] = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_yaml_bool_arms(cls, data: Any) -> Any:
        """YAML 1.1 parses bare ``off``/``on`` as booleans, so ``arms: [off]`` arrives as
        ``[False]`` — coerce the two unambiguous booleans back to their arm names so a hand-written
        matrix fails loud only on a REAL typo, not on YAML's spelling of our own vocabulary."""
        if isinstance(data, dict) and isinstance(data.get("arms"), list):
            data["arms"] = [{True: "on", False: "off"}[a] if isinstance(a, bool) else a
                            for a in data["arms"]]
        return data

    def effective_arms(self) -> tuple[str, ...]:
        """The factorial arms this task runs (Exp 1c/1d): an explicit `arms` restriction wins
        (e.g. the skill-off pilot's `arms: [off]`); otherwise {off,on} + neutral when declared."""
        if self.arms:
            return tuple(self.arms)
        return ("off", "neutral", "on") if self.neutral is not None else ("off", "on")

    @model_validator(mode="after")
    def _exactly_one_design(self) -> "TaskSpec":
        """A task is either a Phase-1a ladder cell (hypothesis tier + swaps) or an Exp-1c/1d
        factorial cell (skill × models, optionally + neutral/arms) — never both, never neither.
        `skill` is required exactly when the effective arm set includes "on"; `skill`/`neutral`/
        `arms`/`h7_label` are exclusive to factorial tasks."""
        is_factorial = self.factorial_models is not None
        if is_factorial == (self.hypothesis is not None):
            raise ValueError(
                f"task {self.id}: set EITHER `hypothesis` (Phase-1a ladder) OR `factorial_models` "
                "(Exp 1c skill×model) — not both, not neither"
            )
        if not is_factorial:
            for field in ("skill", "neutral", "arms", "h7_label"):
                if getattr(self, field) is not None:
                    raise ValueError(
                        f"task {self.id}: `{field}` is only used by factorial (Exp 1c/1d) tasks")
            return self
        if self.arms is not None and not self.arms:
            raise ValueError(f"task {self.id}: `arms` must not be empty (omit it for the full set)")
        eff = self.effective_arms()
        if "on" in eff and self.skill is None:
            raise ValueError(f"task {self.id}: a factorial (Exp 1c) task must declare a `skill` id "
                             "(its effective arms include 'on')")
        if "neutral" in eff and self.neutral is None:
            raise ValueError(f"task {self.id}: arm 'neutral' requires a `neutral` block id")
        return self


class RunMatrix(BaseModel):
    model_config = _STRICT
    meta: RunMeta
    defaults: Defaults
    over_service: OverServiceRule
    models: dict[str, ModelSpec]
    tasks: list[TaskSpec]


# ===========================================================================  manifest
# Mirrors fixtures/manifest.yaml (the frozen-fixture registry).


class Proxy(BaseModel):
    model_config = _STRICT
    type: PROXY_TYPE  # words | pages | lines | files | turns
    value: IntOrTBD


class FixtureFiles(BaseModel):
    model_config = _STRICT
    prompt: str
    input: Optional[str] = None  # omitted for fixed-small / output / thinking tasks


class RecordedTokenCounts(BaseModel):
    model_config = _STRICT
    tok_hs: IntOrTBD  # Haiku/Sonnet count
    tok_opus: IntOrTBD  # Opus count (tokenizer NOT shared — two counts per fixture)


class FixtureCacheSpec(BaseModel):
    model_config = _STRICT
    mode: Optional[str] = None
    assert_hit: Optional[bool] = None
    min_floor_if_haiku: Optional[int] = None


class FixtureEntry(BaseModel):
    model_config = _STRICT
    task_id: int
    band: str
    cost_axis: COST_AXIS
    proxy: Proxy
    files: FixtureFiles
    recorded_token_counts: RecordedTokenCounts
    sha256: str  # "TBD" until curated, then the 64-char hex (see fixture_hash)
    frozen: bool
    cache: Optional[FixtureCacheSpec] = None

    @model_validator(mode="after")
    def _frozen_implies_real_hash(self) -> "FixtureEntry":
        """Enforce the immutability contract (manifest line 3, CLAUDE.md invariant 5): a
        ``frozen`` fixture must carry a real digest; an unfrozen one stays ``TBD`` until then.
        Catches the curation slip of flipping ``frozen`` before pasting the hash."""
        if self.frozen and not is_sha256_hex(self.sha256):
            raise ValueError(
                f"frozen fixture (task {self.task_id}/{self.band}) must carry a 64-char hex "
                f"sha256, got {self.sha256!r}"
            )
        if not self.frozen and self.sha256 != "TBD" and not is_sha256_hex(self.sha256):
            raise ValueError(
                f"unfrozen fixture (task {self.task_id}/{self.band}) sha256 must be 'TBD' or a "
                f"64-char hex digest, got {self.sha256!r}"
            )
        return self


class Manifest(BaseModel):
    model_config = _STRICT
    schema_version: int
    fixtures: list[FixtureEntry]


# ===========================================================================  skills (Exp 1c)
# Mirrors skills/manifest.yaml — the frozen-skill registry, governed by the same immutability
# contract as fixtures (CLAUDE.md invariant 5): a frozen skill carries a real digest.


class SkillEntry(BaseModel):
    model_config = _STRICT
    id: str  # referenced by TaskSpec.skill and stored on CallConfig.skill
    file: str  # path to the skill scaffold, relative to fixtures_root (e.g. skills/email-concise-v1.md)
    sha256: str  # "TBD" until frozen, then the 64-char hex (see harness.hashing.skill_hash)
    frozen: bool
    applies_to: Optional[list[int]] = None  # task ids this skill is authored for (sanity only)
    note: Optional[str] = None

    @model_validator(mode="after")
    def _frozen_implies_real_hash(self) -> "SkillEntry":
        if self.frozen and not is_sha256_hex(self.sha256):
            raise ValueError(
                f"frozen skill {self.id!r} must carry a 64-char hex sha256, got {self.sha256!r}"
            )
        if not self.frozen and self.sha256 != "TBD" and not is_sha256_hex(self.sha256):
            raise ValueError(
                f"unfrozen skill {self.id!r} sha256 must be 'TBD' or a 64-char hex digest, "
                f"got {self.sha256!r}"
            )
        return self


class SkillManifest(BaseModel):
    model_config = _STRICT
    schema_version: int
    skills: list[SkillEntry]


class NeutralManifest(BaseModel):
    """Mirrors fixtures/neutral/manifest.yaml — the frozen neutral-system-block registry (Exp 1d H8
    control). A neutral block is structurally identical to a skill entry (id/file/sha256/frozen), so
    it reuses ``SkillEntry``, but lives in a SEPARATE manifest: the frozen skills registry stays
    untouched, and the neutral block is by construction NOT a skill — it is the per-task,
    length-matched, structure-free control that isolates the scaffold's structure from mere presence
    of a system block (charter §5 H8). Same immutability contract (frozen ⇒ real digest)."""

    model_config = _STRICT
    schema_version: int
    neutral: list[SkillEntry]


# ===========================================================================  prices
# Mirrors prices/prices-2026-06.yaml. Values stay TBD until applied at analysis time.


class ModelPrices(BaseModel):
    model_config = _STRICT
    input: NumOrTBD
    output: NumOrTBD
    cache_read: NumOrTBD
    cache_write_5m: NumOrTBD
    thinking: NumOrTBD


class Prices(BaseModel):
    model_config = _STRICT
    currency: str
    unit: str
    as_of: Union[_dt.date, str]  # "TBD" until pulled
    source: str
    models: dict[str, ModelPrices]


# ===========================================================================  loaders


def _load_yaml(path: Union[str, Path]) -> Any:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def load_run_matrix(path: Union[str, Path]) -> RunMatrix:
    return RunMatrix.model_validate(_load_yaml(path))


def load_manifest(path: Union[str, Path]) -> Manifest:
    return Manifest.model_validate(_load_yaml(path))


def load_skill_manifest(path: Union[str, Path]) -> SkillManifest:
    return SkillManifest.model_validate(_load_yaml(path))


def load_neutral_manifest(path: Union[str, Path]) -> NeutralManifest:
    return NeutralManifest.model_validate(_load_yaml(path))


def load_prices(path: Union[str, Path]) -> Prices:
    return Prices.model_validate(_load_yaml(path))
