"""harness/schema.py — the capture contract (Experiment 1, Phase 1).

The Pydantic record every captured call validates against *before* it is written to
`results/<run-id>/records.jsonl`. A partial or malformed capture fails loudly here
rather than silently poisoning the dataset — that is this module's whole job.

Design (from docs/SPEC.md §5, CLAUDE.md invariants 2–3, and the stack decision in
Staging_Area/Convo.txt):

  * **Raw verbatim + typed projection.** We store the API's `usage` object *verbatim*
    (`usage_raw`) AND a validated typed projection (`usage`). The projection is always
    *derived* from the raw dict and re-checked for equality on load, so the two can
    never silently disagree. If Anthropic adds a usage field later, `usage_raw` keeps
    it — we don't cherry-pick and quietly miss it.
  * **Raw tokens only — never dollars.** Price is applied downstream in analysis/.
  * **stop_reason quarantine.** Given the no-caps / scope-the-fixture design, anything
    that isn't a natural completion (`end_turn` / `stop_sequence`) means a truncated or
    refused artifact — a corrupted record. It is flagged `quarantined` and excluded from
    the H1 variance set. The gate is *recomputed on load*, so it can't be edited away.
  * **Cache-hit assertion.** Every cache *read* must assert a hit; a TTL-expired read
    silently becomes a fresh-input call (`cache_read_input_tokens == 0`) and is
    quarantined regardless of what the harness claimed.
  * **Replay from the record alone.** Every record carries its identity, the exact call
    config, the fixture/config hashes, and full provenance (model/tokenizer/SDK version,
    request-id, rate-limit headers).

Field names are pinned against the live SDK (anthropic 0.109.2, verified 2026-06-16):
`Usage` → input_tokens, output_tokens, cache_read_input_tokens, cache_creation_input_tokens,
cache_creation{ephemeral_5m_input_tokens, ephemeral_1h_input_tokens}, output_tokens_details
{thinking_tokens}, service_tier, inference_geo, server_tool_use.
"""

from __future__ import annotations

import datetime as _dt
import enum
import json
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from harness.hashing import config_hash, is_sha256_hex

# Natural completions for Phase 1a (non-agentic). Anything else means the artifact is not
# a clean, naturally-bounded completion → the record is quarantined. (`tool_use` becomes a
# natural stop only for the deferred agentic Phase 1b; it is NOT natural here.)
NATURAL_STOP_REASONS: frozenset[str] = frozenset({"end_turn", "stop_sequence"})

# Closed vocabularies for the call-side config (shared with harness.config).
MODEL_ROLE = Literal["haiku", "sonnet", "opus"]
EFFORT = Literal["low", "medium", "high", "max", "xhigh"]
THINKING = Literal["off", "adaptive", "enabled"]


class CallRole(str, enum.Enum):
    """Where a call sits in a cell's call sequence.

    `single`  — an ordinary one-shot call (most cells).
    `write`   — the warm-once cache-creation call of a cache cell (#10–12).
    `read`    — a cache read call; every read must assert a cache hit.
    """

    single = "single"
    write = "write"
    read = "read"


class ExecPath(str, enum.Enum):
    """Which execution path produced the record — provenance only; token data is
    schema-identical across paths so analysis never branches on it."""

    sync_stream = "sync_stream"  # streaming Messages API (the default — every call streams)
    batch = "batch"  # Batches API (50% tier; reserved for L-band independent cells)


def _as_int(v: Any) -> int:
    """API cache/thinking fields arrive as int, ``None``, or absent → normalise to int.

    A non-integral or boolean value is a corrupt/garbled count: fail loud rather than
    silently truncating (e.g. ``int(11.9) == 11`` would drift the projection from raw)."""
    if v is None:
        return 0
    if isinstance(v, bool):  # bool is an int subclass — never a valid token count
        raise ValueError(f"non-integer token count: {v!r}")
    if isinstance(v, float) and not v.is_integer():
        raise ValueError(f"non-integral token count: {v!r}")
    return int(v)


class UsageVector(BaseModel):
    """Typed projection of the raw ``usage`` object — the cost-bearing token components,
    kept separate because they are not fungible (a cache-read token ≈ 1/10 the dollar
    weight of fresh input). Always derived from the verbatim raw dict via :meth:`from_raw`.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    cache_read_input_tokens: int = Field(default=0, ge=0)
    cache_creation_input_tokens: int = Field(default=0, ge=0)
    # Per-TTL split of cache creation (writes are priced by TTL); must sum to the total.
    cache_creation_5m: int = Field(default=0, ge=0)
    cache_creation_1h: int = Field(default=0, ge=0)
    thinking_tokens: int = Field(default=0, ge=0)
    # Price-tier / provenance carried verbatim from usage; the rest lives in usage_raw.
    service_tier: Optional[str] = None

    @model_validator(mode="after")
    def _cache_split_sums(self) -> "UsageVector":
        # The per-TTL split must ALWAYS equal the total — including the total==0 case, which
        # otherwise lets a desynced capture (split>0 while total==0) through. All-zero passes.
        split = self.cache_creation_5m + self.cache_creation_1h
        if split != self.cache_creation_input_tokens:
            raise ValueError(
                "cache_creation TTL split "
                f"(5m={self.cache_creation_5m} + 1h={self.cache_creation_1h} = {split}) "
                f"!= cache_creation_input_tokens ({self.cache_creation_input_tokens})"
            )
        return self

    @classmethod
    def from_raw(cls, raw: Any) -> "UsageVector":
        """Project a verbatim API ``usage`` object into the typed component vector.

        Accepts a dict or the SDK ``Usage`` model (``get_final_message().usage`` is a
        pydantic model, not a dict) — coerced via ``model_dump``. The two core token
        counts are mandatory: a missing ``input_tokens``/``output_tokens`` is a broken
        capture and must fail loud, never coerce to a fabricated 0 (CLAUDE.md invariant 1)."""
        if not isinstance(raw, dict):
            if hasattr(raw, "model_dump"):
                raw = raw.model_dump()
            else:
                raise ValueError(f"usage must be a dict or have model_dump(); got {type(raw)}")
        for key in ("input_tokens", "output_tokens"):
            if raw.get(key) is None:
                raise ValueError(
                    f"usage missing required token field {key!r} — refusing to coerce a "
                    "measurement to 0 (CLAUDE.md invariants 1 & 2)"
                )
        details = raw.get("output_tokens_details") or {}
        creation = raw.get("cache_creation") or {}
        return cls(
            input_tokens=_as_int(raw.get("input_tokens")),
            output_tokens=_as_int(raw.get("output_tokens")),
            cache_read_input_tokens=_as_int(raw.get("cache_read_input_tokens")),
            cache_creation_input_tokens=_as_int(raw.get("cache_creation_input_tokens")),
            cache_creation_5m=_as_int(creation.get("ephemeral_5m_input_tokens")),
            cache_creation_1h=_as_int(creation.get("ephemeral_1h_input_tokens")),
            thinking_tokens=_as_int(details.get("thinking_tokens")),
            service_tier=raw.get("service_tier"),
        )


class CallConfig(BaseModel):
    """The exact, resolved call configuration — stored inline so a record is
    self-describing and a run replays from it alone. `config_hash` is computed over this."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    model_role: MODEL_ROLE
    model_id: str = Field(min_length=1)
    band: str  # the band label on the cell's dominant axis (S/M/L, low/high/max, few/many…)
    effort: Optional[EFFORT] = None  # None for Haiku (no effort knob)
    thinking: THINKING = "off"
    temperature: str = "omitted"  # constitution: omitted on every call, recorded as such
    max_tokens: int = Field(gt=0)  # the model output ceiling; never omitted, never a cap
    # Exp 1c skill axis: the skill id (a frozen scaffold in skills/manifest.yaml) injected as a
    # `system` block on the skill-on arm. None == skill-off, which hashes byte-identically to the
    # pre-skill schema (see harness.hashing.config_hash), so Phase-1a records are untouched.
    skill: Optional[str] = None
    # Exp 1d neutral arm (charter §5 H8): the id of a frozen, structure-free `system` block (the
    # length-matched control), injected on the neutral arm. Mutually exclusive with `skill`. None ==
    # not the neutral arm, and (like skill=None) is dropped from config_hash so 1a/1c hashes are
    # untouched. A call injects at most ONE system block: the skill (on) OR the neutral control.
    neutral: Optional[str] = None

    @model_validator(mode="after")
    def _skill_and_neutral_exclusive(self) -> "CallConfig":
        if self.skill is not None and self.neutral is not None:
            raise ValueError(
                f"skill and neutral are mutually exclusive (a call injects one system block): "
                f"skill={self.skill!r}, neutral={self.neutral!r}"
            )
        return self


class CellId(BaseModel):
    """Identity of the cell a record belongs to: (task × band × model × config role)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    task_id: int
    task_name: str = Field(min_length=1)
    band: str
    model_role: MODEL_ROLE
    model_id: str = Field(min_length=1)
    # "factorial" is the Exp 1c skill×model design (vs Phase-1a's hypothesis/over-service ladder).
    role_label: Literal["hypothesis", "over_service", "down_probe", "factorial"]
    # Exp 1c skill arm ("off"/"on"); Exp 1d adds "neutral" (the H8 length-matched control). "off" is
    # the pre-skill world and is OMITTED from the grouping key, so every Phase-1a cell key is
    # byte-unchanged; "on"/"neutral" cells gain a suffix. Mirrors config_hash dropping skill/neutral.
    skill_arm: Literal["off", "neutral", "on"] = "off"

    def key(self) -> str:
        """Stable grouping key for per-cell variance aggregation in analysis. Skill-off cells
        (all of Phase 1a) keep their exact pre-skill key; skill-on cells get a ``:skill-on`` tail
        so the two arms never collide into one bimodal distribution."""
        base = f"t{self.task_id}:{self.band}:{self.model_role}:{self.role_label}"
        return base if self.skill_arm == "off" else f"{base}:skill-{self.skill_arm}"


def derive_quarantine(
    *,
    stop_reason: Optional[str],
    call_role: CallRole,
    cache_hit: Optional[bool],
    cache_read_input_tokens: int,
    cache_creation_input_tokens: int = 0,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
) -> tuple[bool, list[str]]:
    """Decide whether a record must be excluded from the H1 variance set, and why.

    Pure and deterministic so it is unit-testable and recomputed identically on load
    (the gate cannot be bypassed by hand-editing a stored record). The token-count args
    default to ``None``/0 so existing single-call callers need not supply them.
    """
    reasons: list[str] = []

    if stop_reason is None or stop_reason not in NATURAL_STOP_REASONS:
        reasons.append(f"non-natural stop_reason: {stop_reason!r} (truncated/refused/incomplete)")

    if call_role is CallRole.read:
        # A read must show a real cache hit. Zero read tokens => TTL expired => fresh-input
        # call masquerading as a read; quarantine regardless of the claimed verdict.
        if cache_read_input_tokens <= 0:
            reasons.append("cache read returned 0 cache_read_input_tokens (TTL-expired miss)")
        else:
            if cache_hit is False:
                reasons.append("cache read asserted as a miss by the harness")
            # SPEC: a read is "cache_read HIGH, input LOW". If fresh input exceeds the cached
            # portion the prefix only partially matched (drift) — a degraded read, not a clean hit.
            if input_tokens is not None and input_tokens > cache_read_input_tokens:
                reasons.append(
                    f"degraded cache read: fresh input ({input_tokens}) exceeds cache_read "
                    f"({cache_read_input_tokens}) — cache_read not HIGH / input not LOW"
                )

    if call_role is CallRole.write:
        # The warm-once write must actually create cache. Zero creation => the prefix fell
        # below the model's cache minimum and was billed as fresh input — not a real warm.
        if cache_creation_input_tokens <= 0:
            reasons.append(
                "cache write created 0 cache_creation_input_tokens "
                "(prefix below cache minimum / cache did not engage)"
            )
        if cache_read_input_tokens > 0:
            reasons.append(
                "cache write returned cache_read tokens — a hit on a stale prefix, "
                "not a fresh warm-once write"
            )

    # A real measured call never reports zero input AND zero output. Both-zero is a
    # non-measurement masquerading as a clean record.
    if input_tokens == 0 and output_tokens == 0:
        reasons.append("input_tokens == output_tokens == 0 (not a real measured call)")

    return (len(reasons) > 0, reasons)


class CaptureRecord(BaseModel):
    """One captured API call (one *turn* for multi-turn cells). Append-only; never mutated.

    Build from a response via :meth:`from_capture`; the harness supplies only the raw
    usage dict + context and the projection/quarantine fields are derived here.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    # --- identity & provenance -------------------------------------------------------
    # Every stamp is non-empty so a wiring bug that drops one fails loud, never writes an
    # un-replayable record (CLAUDE.md invariant 3). The two hashes carry the sha256 shape
    # they are built from; config_hash is additionally recomputed and checked below.
    run_id: str = Field(min_length=1)
    timestamp: _dt.datetime = Field(default_factory=lambda: _dt.datetime.now(_dt.timezone.utc))
    cell_id: CellId
    config: CallConfig
    config_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    fixture_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    # Exp 1c/1d: bare sha256 of the frozen injected `system` block — the skill (skill-on arm) OR the
    # neutral control (neutral arm) — pinned at write like fixture_hash; None on every "off" /
    # Phase-1a record. Shape-checked below; not recomputed on load (the block text isn't carried here
    # — it lives in skills/manifest.yaml or neutral/manifest.yaml; skill_arm says which).
    skill_hash: Optional[str] = None

    model_id: str = Field(min_length=1)
    model_version: str = Field(min_length=1)  # the model the API resolved/served (resp.model)
    tokenizer_version: str = Field(min_length=1)  # tok-hs | tok-opus (NOT shared)
    sdk_version: str = Field(min_length=1)  # anthropic.__version__ — SDK behaviour is provenance

    # --- usage: verbatim + typed projection -----------------------------------------
    usage_raw: dict[str, Any]  # the API usage object, byte-for-byte (forward-compatible)
    usage: UsageVector  # derived from usage_raw; re-checked for equality on load
    # tool-result tokens are folded into input by the API; the harness counts them
    # separately when a payload rides in as a tool result (#18/#19). None when absent.
    tool_result_tokens: Optional[int] = Field(default=None, ge=0)

    # --- output text (Exp 1c only) ---------------------------------------------------
    # The model's assistant text, persisted ONLY for the determinism-A/B factorial cells so the
    # frozen quality judge can grade H6. A deliberate, scoped departure from the "raw tokens, no
    # payloads" posture (CLAUDE.md invariant 2) — None on every cost-only Phase-1a/1b record, so
    # their storage posture is unchanged.
    response_text: Optional[str] = None

    # --- timing ----------------------------------------------------------------------
    # allow_inf_nan=False: a non-finite reading (clock anomaly) fails loud at capture, rather
    # than serialising to JSON null and breaking the reload (replay-from-record).
    # latency_ms is an upper bound (it absorbs transparent SDK retry/backoff), not a clean RTT
    # — a diagnostic, never a measurement input.
    latency_ms: float = Field(ge=0, allow_inf_nan=False)
    wall_clock_s: float = Field(ge=0, allow_inf_nan=False)  # full call incl. stream accumulation

    # --- call shape ------------------------------------------------------------------
    call_role: CallRole = CallRole.single
    cache_hit: Optional[bool] = None  # set (asserted) only on reads
    turn_index: Optional[int] = Field(default=None, ge=0)  # set for multi-turn cells
    exec_path: ExecPath = ExecPath.sync_stream

    # --- gate (derived; recomputed on load) ------------------------------------------
    stop_reason: Optional[str]
    quarantined: bool = False
    quarantine_reasons: list[str] = Field(default_factory=list)

    # --- raw provenance headers ------------------------------------------------------
    request_id: Optional[str] = None  # audit gold: pins the exact call if a number is challenged
    rate_limit: Optional[dict[str, str]] = None  # anthropic-ratelimit-* headers, verbatim

    @model_validator(mode="before")
    @classmethod
    def _derive_projection(cls, data: Any) -> Any:
        """Normalise a non-dict ``usage_raw`` (the SDK ``Usage`` model) to a plain dict, then
        derive the typed projection from it if not supplied."""
        if isinstance(data, dict) and "usage_raw" in data:
            data = dict(data)
            raw = data["usage_raw"]
            if not isinstance(raw, dict) and hasattr(raw, "model_dump"):
                raw = raw.model_dump()
                data["usage_raw"] = raw
            if data.get("usage") is None:
                data["usage"] = UsageVector.from_raw(raw).model_dump()
        return data

    @model_validator(mode="after")
    def _check_consistency_and_gate(self) -> "CaptureRecord":
        # 1. The typed projection must equal what the verbatim raw dict yields — no drift.
        expected = UsageVector.from_raw(self.usage_raw)
        if self.usage != expected:
            raise ValueError(
                "usage projection disagrees with usage_raw "
                f"(projection={self.usage.model_dump()}, derived={expected.model_dump()})"
            )

        # 2. Model identity must agree across the (deliberately redundant) places it is stored,
        #    so a record can never claim one model's identity while carrying another's usage.
        if not (self.model_id == self.config.model_id == self.cell_id.model_id):
            raise ValueError(
                "model_id disagreement: "
                f"record={self.model_id!r}, config={self.config.model_id!r}, "
                f"cell={self.cell_id.model_id!r}"
            )
        if self.config.model_role != self.cell_id.model_role:
            raise ValueError(
                f"model_role disagreement: config={self.config.model_role!r}, "
                f"cell={self.cell_id.model_role!r}"
            )

        # 2b. Arm identity must agree across its redundant stores (Exp 1c/1d). A call that injects a
        #     system block carries its id in the config (skill=on, neutral=neutral), a skill_hash on
        #     the record (the injected block's hash, either arm), and the matching skill_arm on the
        #     cell; an "off" call carries none of the three. Any half-set state is a wiring bug that
        #     would silently mislabel an arm — fail loud. (skill_hash is the injected-block hash; it
        #     is populated on both the skill-on and neutral arms.)
        injected = self.config.skill is not None or self.config.neutral is not None
        if (self.skill_hash is not None) != injected:
            raise ValueError(
                f"block/skill_hash mismatch: config.skill={self.config.skill!r}, "
                f"config.neutral={self.config.neutral!r}, skill_hash={self.skill_hash!r}"
            )
        expected_arm = ("on" if self.config.skill is not None
                        else "neutral" if self.config.neutral is not None else "off")
        if self.cell_id.skill_arm != expected_arm:
            raise ValueError(
                f"skill_arm/config mismatch: cell.skill_arm={self.cell_id.skill_arm!r}, "
                f"config.skill={self.config.skill!r}, config.neutral={self.config.neutral!r} "
                f"(expected arm {expected_arm!r})"
            )
        if self.skill_hash is not None and not is_sha256_hex(self.skill_hash):
            raise ValueError(
                f"skill_hash must be a bare 64-char hex sha256 or None, got {self.skill_hash!r}"
            )

        # 3. config_hash is a recomputable fingerprint — re-derive it and fail loud on mismatch
        #    (a stale/copy-pasted/wrong-tokenizer hash silently breaks the audit chain).
        expected_hash = config_hash(self.config, tokenizer_version=self.tokenizer_version)
        if self.config_hash != expected_hash:
            raise ValueError(
                "config_hash does not match the inlined config + tokenizer "
                f"(stored={self.config_hash}, recomputed={expected_hash})"
            )

        # 4. A thinking call must carry its component. Distinguish "absent" (broken capture →
        #    reject) from "present and 0" (a legitimate adaptive zero → keep).
        if self.config.thinking in ("adaptive", "enabled"):
            # Absent OR present-but-None both mean the component never arrived (the SDK drops
            # it as null on the stream's final snapshot; client.py recovers it from the
            # message_delta). Either way: reject loud, never store a silent thinking=0 at full
            # output cost. A present {"thinking_tokens": 0} is a legitimate adaptive zero — kept.
            if self.usage_raw.get("output_tokens_details") is None:
                raise ValueError(
                    f"thinking={self.config.thinking!r} but usage_raw['output_tokens_details'] "
                    "is absent or null — the thinking component was not captured"
                )

        # 5. tool_result_tokens are folded into the input the call billed; counting more than
        #    that folded input is a caller bug (e.g. the raw payload word-count).
        if self.tool_result_tokens is not None:
            folded = self.usage.input_tokens + self.usage.cache_read_input_tokens
            if self.tool_result_tokens > folded:
                raise ValueError(
                    f"tool_result_tokens ({self.tool_result_tokens}) exceeds the folded input "
                    f"it is a subset of ({folded} = input + cache_read)"
                )

        # 6. cache_hit is meaningful only on reads, and required there.
        if self.call_role is CallRole.read:
            if self.cache_hit is None:
                raise ValueError("call_role=read requires a cache_hit assertion (got None)")
        elif self.cache_hit is not None:
            raise ValueError(
                f"cache_hit is only meaningful on reads; got {self.cache_hit!r} "
                f"on call_role={self.call_role.value}"
            )

        # 7. Recompute the quarantine verdict from ground truth (never trusted from disk).
        quarantined, reasons = derive_quarantine(
            stop_reason=self.stop_reason,
            call_role=self.call_role,
            cache_hit=self.cache_hit,
            cache_read_input_tokens=self.usage.cache_read_input_tokens,
            cache_creation_input_tokens=self.usage.cache_creation_input_tokens,
            input_tokens=self.usage.input_tokens,
            output_tokens=self.usage.output_tokens,
        )
        # validate_assignment is on; assign via __dict__ to avoid re-triggering this validator.
        self.__dict__["quarantined"] = quarantined
        self.__dict__["quarantine_reasons"] = reasons
        return self

    # --- construction & serialisation ------------------------------------------------
    @classmethod
    def from_capture(
        cls,
        *,
        run_id: str,
        cell_id: CellId,
        config: CallConfig,
        config_hash: str,
        fixture_hash: str,
        model_version: str,
        tokenizer_version: str,
        sdk_version: str,
        usage_raw: dict[str, Any],
        stop_reason: Optional[str],
        latency_ms: float,
        wall_clock_s: float,
        call_role: CallRole = CallRole.single,
        cache_hit: Optional[bool] = None,
        turn_index: Optional[int] = None,
        exec_path: ExecPath = ExecPath.sync_stream,
        tool_result_tokens: Optional[int] = None,
        skill_hash: Optional[str] = None,
        response_text: Optional[str] = None,
        request_id: Optional[str] = None,
        rate_limit: Optional[dict[str, str]] = None,
        timestamp: Optional[_dt.datetime] = None,
    ) -> "CaptureRecord":
        """The harness entry point: build a validated record from an API response and its
        cell context. The typed projection and quarantine verdict are derived here."""
        kwargs: dict[str, Any] = dict(
            run_id=run_id,
            cell_id=cell_id,
            config=config,
            config_hash=config_hash,
            fixture_hash=fixture_hash,
            model_id=config.model_id,
            model_version=model_version,
            tokenizer_version=tokenizer_version,
            sdk_version=sdk_version,
            usage_raw=usage_raw,
            stop_reason=stop_reason,
            latency_ms=latency_ms,
            wall_clock_s=wall_clock_s,
            call_role=call_role,
            cache_hit=cache_hit,
            turn_index=turn_index,
            exec_path=exec_path,
            tool_result_tokens=tool_result_tokens,
            skill_hash=skill_hash,
            response_text=response_text,
            request_id=request_id,
            rate_limit=rate_limit,
        )
        if timestamp is not None:
            kwargs["timestamp"] = timestamp
        return cls(**kwargs)

    def to_jsonl_line(self) -> str:
        """One newline-free JSON object for append-only records.jsonl (raw tokens only)."""
        return self.model_dump_json()

    @classmethod
    def from_jsonl_line(cls, line: str) -> "CaptureRecord":
        return cls.model_validate(json.loads(line))
