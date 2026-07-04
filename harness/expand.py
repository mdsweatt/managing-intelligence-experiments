from __future__ import annotations
import logging
from typing import Optional
from pydantic import BaseModel, ConfigDict
from harness.config import (TaskSpec, ModelSpec, FixtureEntry, RunMatrix, Manifest, SkillEntry,
                            SkillManifest, NeutralManifest)
from harness.schema import CallConfig, CellId

logger = logging.getLogger(__name__)

class RunUnit(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    cell_id: CellId
    config: CallConfig
    role_label: str
    family: str
    fixture: FixtureEntry
    n: int
    # Exp 1c: the frozen skill to inject on the skill-on arm; None for skill-off and all Phase 1a.
    skill_entry: Optional[SkillEntry] = None
    # Exp 1d: the frozen neutral-system block to inject on the neutral arm; None otherwise.
    neutral_entry: Optional[SkillEntry] = None

def resolve_hypothesis_config(task: TaskSpec, band: str, models: dict[str, ModelSpec]) -> CallConfig:
    role = task.hypothesis
    mspec = models[role]
    if role == "haiku":
        effort = None
    elif task.bands_are_effort:           # #15: the band IS the effort level
        effort = band
    else:
        effort = "high"
    thinking = task.thinking if task.thinking is not None else "off"
    return CallConfig(
        model_role=role, model_id=mspec.id, band=band,
        effort=effort, thinking=thinking, temperature="omitted",
        max_tokens=mspec.max_output,
    )

def resolve_swapped_config(hypo: CallConfig, target_role: str, models: dict[str, ModelSpec]) -> CallConfig:
    mspec = models[target_role]
    effort, thinking = hypo.effort, hypo.thinking
    if target_role == "haiku":
        effort = None                      # Haiku has no effort knob
    elif hypo.model_role == "haiku":
        effort, thinking = "low", "off"    # nothing to copy → matched-minimal floor (R1 / SPEC D2)
    return CallConfig(
        model_role=target_role, model_id=mspec.id, band=hypo.band,
        effort=effort, thinking=thinking, temperature="omitted",
        max_tokens=mspec.max_output,
    )

_FAMILY = {"cached_context": "cache", "turns": "multiturn", "payload": "payload"}

def family_for(cost_axis: str) -> str:
    return _FAMILY.get(cost_axis, "standard")

def _lookup_fixture(manifest: Manifest, task_id: int, band: str, bands_are_effort: bool) -> FixtureEntry:
    by = {(f.task_id, f.band): f for f in manifest.fixtures}
    if (task_id, band) in by:
        return by[(task_id, band)]
    if bands_are_effort and (task_id, "shared") in by:   # #15: one artifact serves all effort bands
        return by[(task_id, "shared")]
    raise KeyError(f"no fixture for task {task_id} band {band!r}")

def _unit(task, band, config, role_label, family, fixture, n) -> RunUnit:
    cell = CellId(
        task_id=task.id, task_name=task.name, band=band,
        model_role=config.model_role, model_id=config.model_id, role_label=role_label,
    )
    return RunUnit(cell_id=cell, config=config, role_label=role_label,
                   family=family, fixture=fixture, n=n)

def _factorial_units(task: TaskSpec, band: str, fixture: FixtureEntry,
                     models: dict[str, ModelSpec], skill_entry: Optional[SkillEntry],
                     neutral_entry: Optional[SkillEntry], n: int) -> list[RunUnit]:
    """Exp 1c/1d expansion: the skill × model factorial for one (task, band).

    1c arms are {off, on}; 1d adds a third {neutral} arm (the H8 length-matched control) whenever the
    task declares a neutral block (``neutral_entry`` is not None) — a task without one (the #4
    placebo, or any 1c matrix) stays 2-arm. An explicit ``task.arms`` restriction wins over both
    (Exp 1d skill-off pilot: ``arms: [off]`` measures the natural loose output before skills/labels
    freeze). Each model runs at a fixed, model-natural config (effort=high for Sonnet/Opus, None for
    Haiku — the Phase-1a non-#15 default, so cells are comparable to 1a), standard family. Thinking
    honors ``task.thinking`` (1d #15 runs thinking-on) at the same model-natural convention: Haiku
    supports neither the effort knob nor adaptive thinking (live-verification 2026-06-16), so a
    thinking task runs adaptive on Sonnet/Opus and off on Haiku — within a (task, band, model) the
    ONLY thing that moves is still the arm. The Phase-1a over_service/down_probe swap logic is
    deliberately NOT reused — it imports matched-minimal / tier-pull conventions that would confound
    the factorial."""
    if task.thinking == "enabled":
        raise NotImplementedError(
            f"task {task.id}: thinking='enabled' needs a budget_tokens the harness does not "
            "support; factorial thinking must be 'adaptive' (or omitted)")
    arms = task.effective_arms()
    base_thinking = task.thinking if task.thinking is not None else "off"
    units: list[RunUnit] = []
    for role in (task.factorial_models or []):
        mspec = models[role]
        effort = None if role == "haiku" else "high"
        thinking = "off" if role == "haiku" else base_thinking
        for arm in arms:
            cfg = CallConfig(
                model_role=role, model_id=mspec.id, band=band,
                effort=effort, thinking=thinking, temperature="omitted",
                max_tokens=mspec.max_output,
                skill=(task.skill if arm == "on" else None),
                neutral=(task.neutral if arm == "neutral" else None),
            )
            cell = CellId(
                task_id=task.id, task_name=task.name, band=band,
                model_role=role, model_id=mspec.id, role_label="factorial", skill_arm=arm,
            )
            units.append(RunUnit(
                cell_id=cell, config=cfg, role_label="factorial", family="standard",
                fixture=fixture, n=n,
                skill_entry=(skill_entry if arm == "on" else None),
                neutral_entry=(neutral_entry if arm == "neutral" else None),
            ))
    return units


def expand_matrix(rm: RunMatrix, manifest: Manifest,
                  skill_manifest: Optional[SkillManifest] = None,
                  neutral_manifest: Optional[NeutralManifest] = None) -> list[RunUnit]:
    n = rm.meta.n_per_cell
    skills_by_id = {s.id: s for s in (skill_manifest.skills if skill_manifest else [])}
    neutrals_by_id = {s.id: s for s in (neutral_manifest.neutral if neutral_manifest else [])}
    units: list[RunUnit] = []

    for task in rm.tasks:
        family = family_for(task.cost_axis)

        for band in task.bands:
            try:
                fixture = _lookup_fixture(manifest, task.id, band, bool(task.bands_are_effort))
            except KeyError:
                logger.warning("expand_matrix: skipping task %s band %r — no fixture in manifest", task.id, band)
                continue

            if task.factorial_models is not None:          # Exp 1c/1d determinism A/B
                # The skill entry is required exactly when an "on" arm will run (TaskSpec validates
                # that pairing); the Exp-1d skill-off pilot (arms: [off]) legitimately has no skill.
                skill_entry = None
                if task.skill is not None:
                    skill_entry = skills_by_id.get(task.skill)
                    if skill_entry is None:
                        raise KeyError(
                            f"factorial task {task.id}: skill {task.skill!r} not in the skill manifest "
                            "(pass --skill-manifest / load_skill_manifest)"
                        )
                neutral_entry = None
                if task.neutral is not None:               # Exp 1d neutral arm (opt-in per task)
                    neutral_entry = neutrals_by_id.get(task.neutral)
                    if neutral_entry is None:
                        raise KeyError(
                            f"factorial task {task.id}: neutral {task.neutral!r} not in the neutral "
                            "manifest (pass --neutral-manifest / load_neutral_manifest)"
                        )
                units.extend(_factorial_units(task, band, fixture, rm.models, skill_entry,
                                              neutral_entry, n))
                continue

            hypo = resolve_hypothesis_config(task, band, rm.models)
            units.append(_unit(task, band, hypo, "hypothesis", family, fixture, n))
            for role in (task.over_service or []):
                cfg = resolve_swapped_config(hypo, role, rm.models)
                units.append(_unit(task, band, cfg, "over_service", family, fixture, n))
            for role in (task.down_probe or []):
                cfg = resolve_swapped_config(hypo, role, rm.models)
                units.append(_unit(task, band, cfg, "down_probe", family, fixture, n))

    return units

def skipped_bands(rm: RunMatrix, manifest: Manifest) -> list[tuple[int, str]]:
    """The (task_id, band) pairs listed in the matrix that have no fixture in the manifest —
    surfaced so deferred/missing bands are never silently dropped from a run."""
    skipped: list[tuple[int, str]] = []
    for task in rm.tasks:
        for band in task.bands:
            try:
                _lookup_fixture(manifest, task.id, band, bool(task.bands_are_effort))
            except KeyError:
                skipped.append((task.id, band))
    return skipped
