"""analysis/quality.py — Phase-1c quality judge (charter §3 H5/H6; docs/phase1c-judge-spec.md).

The cost harness measures tokens exactly but cannot say "Haiku does it *identically*". This module
supplies that missing quality axis for the determinism A/B — and nothing more. It reads a run's
`records.jsonl`, keeps only the factorial cells (`role_label == "factorial"`, which carry
`response_text`), and grades them with the **frozen, hash-pinned** judge instrument
(`fixtures/judge/manifest.yaml`):

  - **Deterministic graders (in code, no LLM, no spend):** #4 exact-match to the gold label; and the
    OBJECTIVE rubric checks for #6/#9 — word counts, #6 hashtag count, #9 section presence — kept out
    of the LLM to remove judge noise from the parts a regex settles (judge-spec §1(a)).
  - **Frozen LLM-judge (billable Opus calls — OFF unless `--run-judge`):** the SEMANTIC rubric checks
    (#6 CTA-validity, hook quality 0–2, faithfulness; #9 single-recommendation-up-front, faithfulness)
    at K replicates with a **majority** vote; an item below the ≥2/3 agreement floor is flagged
    `low_confidence`, never silently averaged.
  - **Blind, order-randomized pairwise (H6):** Haiku-vs-Opus at matched run index, **only on pairs
    where both outputs passed the absolute rubric** (the format-bias coverage fix), with the excluded
    share reported. Order is randomized by a deterministic seed so the grading replays.
  - **Human spot-check export:** a stratified ≥10% sample across models × arms, blinded, with a
    de-blinding key + `compute_agreement` to calibrate the LLM-judge against human labels.

H5 (the quality FLOOR — "skill-on must not grade worse than skill-off") is read here as the rubric
pass-rate per (task, model, arm). H5's token side (`CoV_output` + mean output tokens) is a cost
metric and stays in `analysis/h1.py` — this module owns only quality.

NOTE ON SPEND: deterministic graders are free and always run. The LLM-judge makes billable Opus
calls and runs ONLY with `--run-judge`; on a 360-record run that is ~hundreds of judge calls. It is
built + unit-tested here against an injected fake judge (zero spend); the live judge runs at analysis
time, after the experiment's records exist.

Run:  uv run python -m analysis.quality results/<run-id> \
          [--judge-manifest fixtures/judge/manifest.yaml] [--fixtures-root fixtures] \
          [--run-judge] [--k 3] [--seed 1c] [--spotcheck-frac 0.10] [--out analysis/output]
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics as st
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable, Optional

import yaml

from harness.hashing import judge_hash, sha256_hex

# A JudgeFn takes a fully-substituted prompt and returns the parsed JSON verdict dict. The
# production impl wraps the Anthropic client; tests inject a fake. This is the only spend seam.
JudgeFn = Callable[[str], dict]

AGREEMENT_FLOOR = 2.0 / 3.0   # < this share of K replicates agreeing => low_confidence (judge-spec §2)
GENERATIVE_TASKS = (6, 9)     # LLM-judged + pairwise; #4 is deterministic exact-match only.
                              # LEGACY 1c default — 1d derives the set from the judge manifest
                              # (pairwise_tasks) so the 8-task ladder needs no code change.


def pairwise_tasks(rubrics: dict) -> tuple[int, ...]:
    """The LLM-judged + pairwise task set, derived from the judge manifest's rubrics — the 1d ladder
    widens beyond 1c's three tasks (charter §5, Exp 1d) without another hardcoded set. On the frozen
    1c manifest this derives exactly GENERATIVE_TASKS, so 1c grading is unchanged."""
    return tuple(sorted(int(tid) for tid, r in rubrics.items() if r.get("pairwise")))


# =========================================================================== deterministic graders

def normalize_label(text: str) -> str:
    """The #4 output is a single label on its own; take the last non-empty line, stripped."""
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    return lines[-1] if lines else ""


def grade_exact_match(text: str, gold: str) -> bool:
    """#4 grade: exact string match of the single-label output to the gold label (judge-spec §1)."""
    return normalize_label(text) == gold


def word_count(text: str) -> int:
    return len((text or "").split())


def count_hashtags(text: str) -> int:
    return len(re.findall(r"#\w+", text or ""))


# #9 required sections (judge-spec §1, #9 check 1) — matched as a heading-ish line start (optionally
# behind a markdown #, a list bullet, bold **, or a "1." number), case-insensitive.
SECTIONS_9: dict[str, str] = {
    "recommendation": r"recommendation",
    "background": r"background",
    "options": r"options",
    "cost": r"cost",
    "risks": r"risk",
    "next_steps": r"next\s+steps",
}
_HEADING_PREFIX = r"(?im)^\s*(?:#{1,6}\s*|\d+[.\)]\s*|[-*]\s*|\*\*\s*)?"


def sections_present(text: str) -> dict[str, bool]:
    return {name: bool(re.search(_HEADING_PREFIX + pat, text or "")) for name, pat in SECTIONS_9.items()}


def code_checks_from_spec(specs: list[dict], text: str) -> dict[str, Any]:
    """Interpret a manifest-declared `code_checks` list (charter §5, Exp 1d — the 8-task ladder's
    objective checks live in the judge manifest, never in code). Per spec: the raw measurement under
    `id`, a boolean under `{id}_ok` — the same shape as the hardcoded #6/#9 dicts."""
    out: dict[str, Any] = {}
    for spec in specs:
        cid, kind = spec["id"], spec["type"]
        if kind == "word_max":
            wc = word_count(text)
            out[cid], out[f"{cid}_ok"] = wc, wc <= spec["max"]
        elif kind == "word_range":
            wc = word_count(text)
            out[cid], out[f"{cid}_ok"] = wc, spec["min"] <= wc <= spec["max"]
        elif kind == "sections_all":
            # name -> regex fragment, each matched behind the same heading-ish prefix as SECTIONS_9
            secs = {name: bool(re.search(_HEADING_PREFIX + pat, text or ""))
                    for name, pat in spec["patterns"].items()}
            out[cid], out[f"{cid}_ok"] = secs, all(secs.values())
        elif kind == "regex_count":
            count = len(re.findall(spec["pattern"], text or ""))
            hi = spec.get("max")
            out[cid], out[f"{cid}_ok"] = count, spec["min"] <= count <= (hi if hi is not None else math.inf)
        else:
            raise ValueError(f"unknown code_check type {kind!r}")
    return out


def code_checks(task_id: int, text: str, spec: Optional[list[dict]] = None) -> dict[str, Any]:
    """The OBJECTIVE (code-graded) rubric checks for a generative task. Returns named booleans plus
    the raw measurements, so the CSV can show *why* a check failed. A manifest-declared `spec` takes
    the 1d interpreter; spec None keeps the hardcoded 1c #6/#9 branches (1c is not reinterpreted)."""
    if spec is not None:
        return code_checks_from_spec(spec, text)
    if task_id == 6:
        wc, ht = word_count(text), count_hashtags(text)
        return {"words": wc, "words_ok": wc <= 60, "hashtags": ht, "hashtags_ok": 2 <= ht <= 3}
    if task_id == 9:
        wc = word_count(text)
        secs = sections_present(text)
        return {"words": wc, "length_ok": 720 <= wc <= 880,
                "sections": secs, "sections_ok": all(secs.values())}
    raise ValueError(f"no code checks for task {task_id}")


# =========================================================================== judge config (frozen)

def load_judge(manifest_path: str | Path, fixtures_root: str | Path) -> dict:
    """Load + integrity-verify the frozen judge instrument. Reads the two prompt templates, checks
    each prompt file's sha256, recomputes the composite judge_hash over the pinned components, and —
    once the manifest is FROZEN — asserts it equals the recorded value (replay check, judge-spec §2).
    Returns the manifest enriched with the prompt texts and the computed judge_hash."""
    root = Path(fixtures_root)
    m = yaml.safe_load(Path(manifest_path).read_text(encoding="utf-8"))
    prompts = {}
    for kind in ("rubric", "pairwise"):
        text = (root / m["prompts"][kind]["file"]).read_text(encoding="utf-8")
        if sha256_hex(text) != m["prompts"][kind]["sha256"]:
            raise ValueError(f"judge prompt {kind!r} sha256 mismatch — frozen file edited under its hash")
        prompts[kind] = text
    components = {
        "judge_model": m["judge_model"], "k": m["k"], "margin_pp": m["margin_pp"],
        "prompt_rubric": prompts["rubric"], "prompt_pairwise": prompts["pairwise"],
        "rubrics": m["rubrics"],
    }
    # Phase-1d extends the hashed identity (CLAUDE.md "extends invariants 3 & 5"): a cross-family
    # judge changes grading behaviour, so the provider + its judge_config (thinking/temperature/max-
    # output) are part of the instrument. Folded in ONLY when present, so a Phase-1c manifest (which
    # carries neither key) recomputes byte-identically and its FROZEN replay check still passes —
    # the same back-compat trick config_hash uses to drop skill=None.
    if m.get("provider") is not None:
        components["provider"] = m["provider"]
    if m.get("judge_config") is not None:
        components["judge_config"] = m["judge_config"]
    computed = judge_hash(components)
    recorded = m.get("judge_hash")
    if m.get("status") == "FROZEN" and recorded != computed:
        raise ValueError(f"judge_hash mismatch: manifest {recorded} != computed {computed} "
                         "— the frozen judge instrument changed")
    return {**m, "prompt_text": prompts, "judge_hash_computed": computed}


def load_task_material(phase1c_manifest: str | Path, fixtures_root: str | Path,
                       tasks: tuple[int, ...] = GENERATIVE_TASKS) -> dict[int, dict]:
    """Source material (the frozen blurb/brief = fixture input) + task instruction (the loose prompt)
    per generative task, read straight from the fixtures manifest — 1c or 1d, any manifest whose
    entries carry files.prompt (+ optional files.input). The judge sees the source as ground truth
    for faithfulness and the instruction as the task — never the skill."""
    root = Path(fixtures_root)
    man = yaml.safe_load(Path(phase1c_manifest).read_text(encoding="utf-8"))
    out: dict[int, dict] = {}
    for entry in man["fixtures"]:
        tid = entry["task_id"]
        if tid not in tasks:
            continue
        files = entry["files"]
        inp = files.get("input")   # a prompt-only task has no separate source; the slot renders empty
        out[tid] = {
            "task_instruction": (root / files["prompt"]).read_text(encoding="utf-8").strip(),
            "source_material": (root / inp).read_text(encoding="utf-8").strip() if inp else "",
        }
    return out


# =========================================================================== majority / agreement

def majority(values: list) -> tuple[Any, float]:
    """Most-common value and the share of replicates that agree on it (1.0 == unanimous)."""
    c = Counter(values)
    top, n = c.most_common(1)[0]
    return top, n / len(values)


def is_low_confidence(agreement: float) -> bool:
    return agreement + 1e-9 < AGREEMENT_FLOOR


# =========================================================================== LLM rubric judging

def _render_checks(checks: list[dict]) -> str:
    """Format the per-task LLM checks for the rubric prompt's {{CHECKS}} slot."""
    lines = []
    for c in checks:
        kind = ("graded " + "/".join(str(s) for s in c["scores"])) if c["type"] == "graded" \
            else 'binary "pass" or "fail"'
        lines.append(f'- {c["id"]} ({kind}): {c["text"]}')
    return "\n".join(lines)


def render_rubric_prompt(template: str, *, source: str, task: str, checks: list[dict], response: str) -> str:
    return (template
            .replace("{{SOURCE_MATERIAL}}", source)
            .replace("{{TASK_INSTRUCTION}}", task)
            .replace("{{CHECKS}}", _render_checks(checks))
            .replace("{{RESPONSE}}", response))


def _coerce_verdict(check: dict, raw: Any) -> Any:
    """Normalize one judge reply for one check into {"pass","fail"} or an int score."""
    if check["type"] == "graded":
        return int(raw)
    return "pass" if str(raw).strip().lower() == "pass" else "fail"


def judge_rubric_item(judge_fn: JudgeFn, template: str, *, source: str, task: str,
                      checks: list[dict], response: str, k: int) -> dict:
    """K replicate rubric judgments of one output → per-check {verdict, agreement, low_confidence}."""
    prompt = render_rubric_prompt(template, source=source, task=task, checks=checks, response=response)
    replicates: list[dict] = [judge_fn(prompt) for _ in range(k)]
    out: dict[str, dict] = {}
    for c in checks:
        vals = [_coerce_verdict(c, rep[c["id"]]) for rep in replicates]
        verdict, agree = majority(vals)
        out[c["id"]] = {"verdict": verdict, "agreement": agree, "low_confidence": is_low_confidence(agree)}
    return out


# =========================================================================== absolute-rubric pass

def absolute_pass(task_id: int, code: dict, llm: Optional[dict],
                  rubric: Optional[dict] = None) -> Optional[bool]:
    """Did this output pass the absolute rubric (judge-spec §1(a))? The graded 0–2 hook is a
    sensitivity floor, not a gate — only its presence (score ≥ 1) gates. Returns None if the LLM
    checks weren't run (so pairwise coverage can't be decided).

    Data-driven form (charter §5, Exp 1d): when the rubric declares `code_checks`, pass = every
    declared `{id}_ok` flag True AND every LLM check passes (binary -> "pass"; graded -> verdict ≥
    its `pass_floor`, default 1 — presence gates, same convention as the 1c hook). The 1c manifest
    declares no `code_checks`, so 1c falls through to the hardcoded #6/#9 logic unchanged."""
    if llm is None:
        return None
    if rubric is not None and rubric.get("code_checks"):
        if not all(code[f"{s['id']}_ok"] for s in rubric["code_checks"]):
            return False
        for c in rubric.get("checks", []):
            v = llm[c["id"]]["verdict"]
            if (v < c.get("pass_floor", 1)) if c["type"] == "graded" else (v != "pass"):
                return False
        return True
    if task_id == 6:
        return (code["words_ok"] and code["hashtags_ok"]
                and llm["cta_valid"]["verdict"] == "pass"
                and llm["hook_quality"]["verdict"] >= 1
                and llm["faithful"]["verdict"] == "pass")
    if task_id == 9:
        return (code["sections_ok"] and code["length_ok"]
                and llm["recommendation_upfront"]["verdict"] == "pass"
                and llm["faithful"]["verdict"] == "pass")
    raise ValueError(task_id)


def eligibility(task_id: int, code: dict, llm: Optional[dict], rubrics: dict) -> Optional[bool]:
    """Is this output eligible for the blind pairwise? **Format-neutral** (charter §5.147, Exp 1d):
    if the task's rubric marks any check ``gate: true``, eligibility = every gate-flagged check passes
    — substance only (faithfulness), so a faithful but format-noncompliant loose output is admitted.
    That closes 1c's coverage hole (skill-off failed the format gate ⇒ 0 eligible pairs ⇒ H6 clause 2
    untestable). If NO check is gated (a Phase-1c manifest), fall back to the legacy format-inclusive
    ``absolute_pass`` so 1c grading is not reinterpreted. ``None`` if the LLM judge did not run."""
    if llm is None:
        return None
    gate_ids = [c["id"] for c in rubrics[str(task_id)].get("checks", []) if c.get("gate")]
    if not gate_ids:
        return absolute_pass(task_id, code, llm)
    return all(llm[cid]["verdict"] == "pass" for cid in gate_ids)


# =========================================================================== pairwise (H6)

def _elig(g: dict) -> Optional[bool]:
    """Pairwise eligibility for one graded output: the format-neutral ``eligible`` field, falling back
    to the legacy ``absolute_pass`` for records/tests that predate it (so 1c is not reinterpreted)."""
    return g.get("eligible", g.get("absolute_pass"))

def haiku_is_a(seed: str, task_id: int, arm: str, idx: int) -> bool:
    """Deterministic, replayable order randomization: which model takes label A in this pair."""
    h = sha256_hex(f"{seed}:{task_id}:{arm}:{idx}")
    return int(h, 16) % 2 == 0


def render_pairwise_prompt(template: str, *, source: str, task: str, resp_a: str, resp_b: str) -> str:
    return (template
            .replace("{{SOURCE_MATERIAL}}", source)
            .replace("{{TASK_INSTRUCTION}}", task)
            .replace("{{RESPONSE_A}}", resp_a)
            .replace("{{RESPONSE_B}}", resp_b))


def judge_pair(judge_fn: JudgeFn, template: str, *, source: str, task: str,
               resp_haiku: str, resp_opus: str, a_is_haiku: bool, k: int) -> dict:
    """K replicate pairwise judgments of one Haiku/Opus pair → {winner in {haiku,opus,tie},
    agreement, low_confidence}. The judge sees blind A/B; we map back here."""
    resp_a, resp_b = (resp_haiku, resp_opus) if a_is_haiku else (resp_opus, resp_haiku)
    prompt = render_pairwise_prompt(template, source=source, task=task, resp_a=resp_a, resp_b=resp_b)
    prefs = [str(judge_fn(prompt)["preference"]).strip().upper() for _ in range(k)]

    def to_model(p: str) -> str:
        if p == "TIE":
            return "tie"
        chose_a = (p == "A")
        return "haiku" if (chose_a == a_is_haiku) else "opus"

    winner, agree = majority([to_model(p) for p in prefs])
    return {"winner": winner, "agreement": agree, "low_confidence": is_low_confidence(agree)}


# =========================================================================== loading / grouping

def load_factorial(records_path: Path) -> dict[tuple, list[dict]]:
    """Group factorial records by (task_id, model_role, skill_arm), preserving append order (the
    matched run index for pairing). Skips non-factorial / text-less records."""
    cells: dict[tuple, list[dict]] = defaultdict(list)
    with records_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            cid = r["cell_id"]
            if cid.get("role_label") != "factorial" or r.get("response_text") is None:
                continue
            cells[(cid["task_id"], cid["model_role"], cid.get("skill_arm", "off"))].append(r)
    return cells


# =========================================================================== production judge fn

def make_judge_fn(client: Any, judge_model: str, *, max_tokens: int = 2048,
                  effort: Optional[str] = None) -> JudgeFn:
    """Wrap an Anthropic client as a JudgeFn: stream one call (uniform capture via harness.client),
    thinking OFF (omitted) and temperature OMITTED per judge-spec §2, parse the JSON verdict from the
    response text. effort is left to the model default unless set."""
    from harness.client import stream_call

    params: dict[str, Any] = {}
    if effort is not None:
        params["output_config"] = {"effort": effort}

    def _judge(prompt: str) -> dict:
        # Verified live 2026-06-28: thinking off + temperature omitted; prompt-instructed JSON parses
        # reliably. One retry guards the rare unparseable reply so a billable call isn't wasted.
        # (output_config.format json_schema is also accepted with thinking off — a future hardening.)
        last: Exception | None = None
        for _ in range(2):
            res = stream_call(client, model=judge_model, max_tokens=max_tokens,
                              messages=[{"role": "user", "content": prompt}], **params)
            try:
                return _parse_json(res.response_text)
            except (ValueError, json.JSONDecodeError) as e:
                last = e
        raise last  # type: ignore[misc]

    return _judge


def _parse_json(text: str) -> dict:
    """Tolerant verdict parse: prefer strict JSON; else extract the first {...} block."""
    text = (text or "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            raise ValueError(f"judge returned no JSON object: {text[:120]!r}")
        return json.loads(m.group(0))


# =========================================================================== analysis pipeline

def analyse(cells: dict[tuple, list[dict]], judge: dict, material: dict[int, dict], *,
            judge_fn: Optional[JudgeFn], k: int, seed: str, run_judge: bool) -> dict:
    """Grade every cell. Returns rubric rows (per task×model×arm), pairwise rows (per task×arm),
    and per-output grades (kept for the spot-check + pairwise pairing)."""
    graded: dict[tuple, list[dict]] = {}   # (task,model,arm) -> [per-output grade dicts in run order]
    rubric_rows: list[dict] = []

    for (task_id, model_role, arm), recs in sorted(cells.items()):
        rubric = judge["rubrics"][str(task_id)]
        per_output: list[dict] = []
        for idx, r in enumerate(recs):
            text = r["response_text"]
            g: dict[str, Any] = {"idx": idx, "model_role": model_role, "arm": arm, "_text": text}
            if rubric.get("grader") == "exact_match":   # manifest-dispatched (1c declares it on "4")
                g["exact_match"] = grade_exact_match(text, rubric["gold"])
                g["label"] = normalize_label(text)
            else:
                cc = code_checks(task_id, text, spec=rubric.get("code_checks"))
                g["code"] = cc
                llm = None
                if run_judge:
                    llm = judge_rubric_item(
                        judge_fn, judge["prompt_text"]["rubric"],
                        source=material[task_id]["source_material"],
                        task=material[task_id]["task_instruction"],
                        checks=rubric["checks"],
                        response=text, k=k)
                g["llm"] = llm
                g["absolute_pass"] = absolute_pass(task_id, cc, llm, rubric)   # reported floor (format-incl.)
                g["eligible"] = eligibility(task_id, cc, llm, judge["rubrics"])  # pairwise gate (§5.147)
            per_output.append(g)
        graded[(task_id, model_role, arm)] = per_output
        rubric_rows.append(_rubric_row(task_id, model_role, arm, per_output, rubric))

    pairwise_rows = _pairwise(graded, judge, material, judge_fn=judge_fn, k=k, seed=seed,
                              run_judge=run_judge, tasks=pairwise_tasks(judge["rubrics"]))
    return {"graded": graded, "rubric_rows": rubric_rows, "pairwise_rows": pairwise_rows}


def _rubric_row(task_id: int, model_role: str, arm: str, per_output: list[dict],
                rubric: Optional[dict] = None) -> dict:
    n = len(per_output)
    row = {"task_id": task_id, "model_role": model_role, "arm": arm, "n": n}
    exact = (rubric.get("grader") == "exact_match") if rubric is not None else task_id == 4
    if exact:
        correct = sum(1 for g in per_output if g["exact_match"])
        row.update(metric="exact_match", pass_rate=correct / n if n else None,
                   low_confidence=0)
        return row
    passes = [g["absolute_pass"] for g in per_output]
    judged = [p for p in passes if p is not None]
    low = sum(1 for g in per_output if g.get("llm")
              and any(c["low_confidence"] for c in g["llm"].values()))
    row.update(metric="absolute_rubric",
               pass_rate=(sum(judged) / len(judged)) if judged else None,
               low_confidence=low)
    # Mean of the FIRST graded-type check's verdicts, reported under the legacy mean_hook_score
    # column — on the 1c manifest that is exactly #6's hook_quality, unchanged.
    if rubric is not None:
        graded_ids = [c["id"] for c in rubric.get("checks", []) if c.get("type") == "graded"]
        graded_id = graded_ids[0] if graded_ids else None
    else:
        graded_id = "hook_quality" if task_id == 6 else None
    if graded_id is not None:
        hooks = [g["llm"][graded_id]["verdict"] for g in per_output if g.get("llm")]
        row["mean_hook_score"] = st.mean(hooks) if hooks else None
    return row


def _pairwise(graded: dict, judge: dict, material: dict, *, judge_fn, k, seed, run_judge,
              tasks: tuple[int, ...] = GENERATIVE_TASKS) -> list[dict]:
    rows: list[dict] = []
    for task_id in tasks:
        for arm in ("off", "neutral", "on"):   # 1d adds the neutral-system arm (H8); absent in 1c data
            haiku = graded.get((task_id, "haiku", arm), [])
            opus = graded.get((task_id, "opus", arm), [])
            n_pairs = min(len(haiku), len(opus))
            if n_pairs == 0:
                continue
            eligible = [i for i in range(n_pairs) if _elig(haiku[i]) and _elig(opus[i])]
            row = {"task_id": task_id, "arm": arm, "total_pairs": n_pairs,
                   "eligible_pairs": len(eligible),
                   "excluded_share": (n_pairs - len(eligible)) / n_pairs}
            if not run_judge:
                row.update(wins_haiku=None, wins_opus=None, ties=None, low_confidence=None,
                           net_pref=None, equivalent=None,
                           note="run with --run-judge for the H6 pairwise")
                rows.append(row)
                continue
            wins = Counter()
            low = 0
            for i in eligible:
                a_is_haiku = haiku_is_a(seed, task_id, arm, i)
                # recover the raw response text for this matched index
                v = judge_pair(judge_fn, judge["prompt_text"]["pairwise"],
                               source=material[task_id]["source_material"],
                               task=material[task_id]["task_instruction"],
                               resp_haiku=haiku[i]["_text"], resp_opus=opus[i]["_text"],
                               a_is_haiku=a_is_haiku, k=k)
                if v["low_confidence"]:
                    low += 1
                    continue
                wins[v["winner"]] += 1
            decided = wins["haiku"] + wins["opus"] + wins["tie"]
            net = abs(wins["haiku"] - wins["opus"]) / decided if decided else None
            row.update(wins_haiku=wins["haiku"], wins_opus=wins["opus"], ties=wins["tie"],
                       low_confidence=low, net_pref=net,
                       equivalent=(net is not None and net <= judge["margin_pp"] / 100.0))
            rows.append(row)
    return rows


# =========================================================================== spot-check export

def spotcheck_sample(cells: dict[tuple, list[dict]], *, frac: float, seed: str,
                     tasks: tuple[int, ...] = GENERATIVE_TASKS) -> list[dict]:
    """Stratified ≥frac sample across generative (task, model, arm) strata, blinded. Deterministic
    selection by hash so it replays. Returns rows carrying both blinded + de-blinding fields."""
    rows: list[dict] = []
    for (task_id, model_role, arm), recs in sorted(cells.items()):
        if task_id not in tasks:
            continue
        n = len(recs)
        take = max(1, math.ceil(frac * n)) if n else 0
        # deterministic order: sort indices by hash, take the first `take`
        order = sorted(range(n), key=lambda i: sha256_hex(f"{seed}:spot:{task_id}:{model_role}:{arm}:{i}"))
        for i in order[:take]:
            spot_id = sha256_hex(f"{seed}:{task_id}:{model_role}:{arm}:{i}")[:12]
            rows.append({"spot_id": spot_id, "task_id": task_id,
                         "model_role": model_role, "arm": arm, "idx": i,
                         "response_text": recs[i]["response_text"]})
    return rows


def compute_agreement(labeled_csv: str | Path, key_csv: str | Path) -> dict:
    """Calibrate the LLM-judge against human labels: fraction of spot-checked items where the human
    label matches the LLM verdict. Reads the human-filled blinded sample + the de-blinding key."""
    human = {r["spot_id"]: r.get("human_pass", "").strip().lower()
             for r in csv.DictReader(Path(labeled_csv).open(encoding="utf-8"))}
    key = {r["spot_id"]: r.get("llm_pass", "").strip().lower()
           for r in csv.DictReader(Path(key_csv).open(encoding="utf-8"))}
    pairs = [(human[s], key[s]) for s in human if human.get(s) and key.get(s)]
    n = len(pairs)
    agree = sum(1 for h, l in pairs if h == l)
    return {"n": n, "agreement": agree / n if n else None}


# =========================================================================== main / IO

def _write_rubric_csv(path: Path, rows: list[dict]) -> None:
    cols = ["task_id", "model_role", "arm", "n", "metric", "pass_rate", "mean_hook_score", "low_confidence"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            w.writerow([r.get(c) for c in cols])


def _write_pairwise_csv(path: Path, rows: list[dict]) -> None:
    cols = ["task_id", "arm", "total_pairs", "eligible_pairs", "excluded_share",
            "wins_haiku", "wins_opus", "ties", "low_confidence", "net_pref", "equivalent"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            w.writerow([r.get(c) for c in cols])


def _write_spotcheck(path: Path, key_path: Path, rows: list[dict]) -> None:
    # blinded sample for the human (no model/arm/idx, no LLM verdict — avoid anchoring)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["spot_id", "task_id", "response_text", "human_pass"])
        for r in rows:
            w.writerow([r["spot_id"], r["task_id"], r["response_text"], ""])
    # de-blinding key (model/arm/idx + a slot for the LLM verdict to compare against)
    with key_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["spot_id", "task_id", "model_role", "arm", "idx", "llm_pass"])
        for r in rows:
            w.writerow([r["spot_id"], r["task_id"], r["model_role"], r["arm"], r["idx"], ""])


def _write_findings(path: Path, judge: dict, rubric_rows: list[dict], pairwise_rows: list[dict],
                    *, run_judge: bool, run_dir: str, phase_label: str = "Phase-1c") -> None:
    lines = [f"# {phase_label} quality findings — {run_dir}", ""]
    lines.append(f"Judge instrument: `{judge['judge_model']}` · K={judge['k']} · "
                 f"margin={judge['margin_pp']}pp · status={judge.get('status')} · "
                 f"judge_hash=`{judge['judge_hash_computed'][:16]}…`")
    lines.append(f"LLM-judge run: **{'yes' if run_judge else 'no (deterministic graders only)'}**")
    lines.append("")
    lines.append("## H5 quality floor — rubric pass-rate (skill-on must not grade worse than skill-off)")
    lines.append("")
    lines.append("| task | model | arm | n | metric | pass-rate | mean hook | low-conf |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in rubric_rows:
        pr = "—" if r["pass_rate"] is None else f"{r['pass_rate']:.0%}"
        hk = r.get("mean_hook_score")
        hk = "—" if hk is None else f"{hk:.2f}"
        lines.append(f"| {r['task_id']} | {r['model_role']} | {r['arm']} | {r['n']} | "
                     f"{r['metric']} | {pr} | {hk} | {r['low_confidence']} |")
    lines.append("")
    lines.append("## H6 tier-equivalence — blind pairwise (Haiku vs Opus), rubric-passing pairs only")
    lines.append("")
    lines.append("| task | arm | pairs | eligible | excluded | Haiku | Opus | ties | low-conf | net-pref | equivalent |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in pairwise_rows:
        ex = f"{r['excluded_share']:.0%}"
        net = "—" if r.get("net_pref") is None else f"{r['net_pref']:.0%}"
        eq = "—" if r.get("equivalent") is None else ("yes" if r["equivalent"] else "no")
        lines.append(f"| {r['task_id']} | {r['arm']} | {r['total_pairs']} | {r['eligible_pairs']} | "
                     f"{ex} | {r.get('wins_haiku')} | {r.get('wins_opus')} | {r.get('ties')} | "
                     f"{r.get('low_confidence')} | {net} | {eq} |")
    lines.append("")
    lines.append("_H6 is claimed only where the gap was open skill-off and within-margin skill-on, "
                 "AND the rubric floor holds (judge-spec §4). Excluded-share is the coverage caveat._")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="analysis.quality",
                                description="Phase-1c quality judge (H5 floor + H6 tier-equivalence)")
    p.add_argument("run_dir", help="results/<run-id> directory containing records.jsonl")
    p.add_argument("--judge-manifest", default="fixtures/judge/manifest.yaml")
    p.add_argument("--phase1c-manifest", "--fixtures-manifest", dest="phase1c_manifest",
                   default="fixtures/manifest-phase1c.yaml",
                   help="fixtures manifest the task material (loose prompt + source input) is read "
                        "from (1c or 1d)")
    p.add_argument("--fixtures-root", default="fixtures")
    p.add_argument("--run-judge", action="store_true",
                   help="make billable Opus judge calls (default off: deterministic graders only)")
    p.add_argument("--k", type=int, default=None, help="replicates (default: judge manifest k)")
    p.add_argument("--seed", default="phase1c", help="seed for pairwise order + spot-check selection")
    p.add_argument("--spotcheck-frac", type=float, default=0.10)
    p.add_argument("--effort", default=None, help="judge effort override (default: model default)")
    p.add_argument("--out", default="analysis/output")
    a = p.parse_args(argv)

    run_dir = Path(a.run_dir)
    judge = load_judge(a.judge_manifest, a.fixtures_root)
    gen_tasks = pairwise_tasks(judge["rubrics"])   # (6, 9) on the 1c manifest; the 8-task ladder on 1d
    material = load_task_material(a.phase1c_manifest, a.fixtures_root, tasks=gen_tasks)
    cells = load_factorial(run_dir / "records.jsonl")
    k = a.k or judge["k"]
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)

    judge_fn: Optional[JudgeFn] = None
    usage_sink: Optional[list[dict]] = None
    provider = judge.get("provider", "anthropic")   # Phase-1c judge has no provider key -> anthropic
    if a.run_judge:
        n_gen = sum(len(v) for (t, _, _), v in cells.items() if t in gen_tasks)
        metered = " (METERED — Gemini Developer API key)" if provider == "gemini" else ""
        print(f"⚠️  --run-judge: ~{n_gen * k} billable {provider}:{judge['judge_model']} rubric "
              f"calls + pairwise calls{metered}. Notify the owner before running on a full dataset.")
        from dotenv import load_dotenv
        load_dotenv()
        if provider == "gemini":
            from analysis.judge_gemini import make_gemini_judge_fn
            jc = judge.get("judge_config", {})
            usage_sink = []
            judge_fn = make_gemini_judge_fn(
                judge["judge_model"],
                thinking_budget=jc["thinking_budget"],
                temperature=jc.get("temperature", 0),
                max_output_tokens=jc.get("max_output_tokens", 2048),
                usage_sink=usage_sink,
            )
        else:
            import anthropic
            judge_fn = make_judge_fn(anthropic.Anthropic(), judge["judge_model"], effort=a.effort)

    res = analyse(cells, judge, material, judge_fn=judge_fn, k=k, seed=a.seed, run_judge=a.run_judge)

    _write_rubric_csv(out / "quality_rubric.csv", res["rubric_rows"])
    _write_pairwise_csv(out / "quality_pairwise.csv", res["pairwise_rows"])
    spot = spotcheck_sample(cells, frac=a.spotcheck_frac, seed=a.seed, tasks=gen_tasks)
    _write_spotcheck(out / "quality_spotcheck.csv", out / "quality_spotcheck_key.csv", spot)
    _write_findings(out / "quality-findings.md", judge, res["rubric_rows"], res["pairwise_rows"],
                    run_judge=a.run_judge, run_dir=str(run_dir))

    if usage_sink is not None:   # persist the metered judge spend (Phase-1d op fix: 1c left it unlogged)
        usage_path = out / "judge_usage.jsonl"
        usage_path.write_text("".join(json.dumps(r) + "\n" for r in usage_sink), encoding="utf-8")
        tot = sum(r["total"] for r in usage_sink)
        fails = sum(1 for r in usage_sink if not r["ok"])
        print(f"judge usage: {len(usage_sink)} attempts ({fails} failed) · {tot} tokens · "
              f"wrote {usage_path}")

    print(f"judge_hash (computed): {judge['judge_hash_computed']}")
    print(f"cells: {len(cells)} · spot-check sample: {len(spot)}")
    print(f"wrote: {out/'quality_rubric.csv'} · {out/'quality_pairwise.csv'} · "
          f"{out/'quality_spotcheck.csv'} · {out/'quality-findings.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
