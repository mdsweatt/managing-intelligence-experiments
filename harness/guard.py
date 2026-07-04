"""harness/guard.py — the hard call/spend ceiling (Experiment 1, Phase 2).

A loop bug must not be able to empty the card (CLAUDE.md "Operational guardrails",
SPEC §6). The guard counts MEASURED tokens and calls — exact values off the usage
vector, not estimates — and aborts the run the instant a pre-set cap is breached.

Denomination stays in tokens (constitution: dollars live only in prices/). The single
dollar notion here is an explicit, conservative SAFETY prior used *once*, up front, to
convert the $ ceiling into a token budget via :func:`tokens_for_dollar_ceiling`. That
prior is operational headroom, not an analysis price — it is intentionally pessimistic
(a high $/token) so the budget under-counts and the guard trips early rather than late.
"""

from __future__ import annotations

from typing import Optional

from harness.schema import UsageVector


class CeilingBreach(RuntimeError):
    """Raised the moment a call/token cap is exceeded — aborts the run."""


def tokens_for_dollar_ceiling(ceiling_usd: float, *, usd_per_million_tokens_prior: float) -> int:
    """Turn a $ safety ceiling into a token budget using a conservative price PRIOR.

    Intentionally pessimistic: pass the most expensive plausible $/1M-token rate so the
    resulting budget is a floor and the guard aborts before real spend reaches the ceiling.
    This is a safety estimate, NOT an analysis price (those live in prices/).

    NOTE on sizing the prior: :meth:`SpendGuard.from_dollar_ceiling` applies the returned
    budget to input AND output *independently*, so combined token spend can reach ~2× the
    budget before either cap trips. For the $ ceiling to hold, the prior must therefore be
    ≥ the SUMMED worst-case input + output $/1M rate (the most expensive model's input rate
    plus its output rate), not a blended/averaged rate. The guard also bounds spend to the
    ceiling PLUS at most one in-flight call's worth (token caps are checked post-call)."""
    if ceiling_usd <= 0 or usd_per_million_tokens_prior <= 0:
        raise ValueError("ceiling and price prior must be positive")
    return int((ceiling_usd * 1_000_000) // usd_per_million_tokens_prior)


class SpendGuard:
    """Tracks calls + billed tokens against hard caps; raises CeilingBreach on breach.

    Billed input = input + cache_read + cache_creation (all priced as input variants);
    output = output_tokens (thinking is part of output). Caps left as ``None`` are unbounded.
    """

    def __init__(
        self,
        *,
        max_calls: int,
        max_input_tokens: Optional[int] = None,
        max_output_tokens: Optional[int] = None,
    ):
        if max_calls <= 0:
            raise ValueError("max_calls must be positive")
        self.max_calls = max_calls
        self.max_input_tokens = max_input_tokens
        self.max_output_tokens = max_output_tokens
        self.calls = 0
        self.input_tokens = 0
        self.output_tokens = 0

    @classmethod
    def from_dollar_ceiling(
        cls,
        ceiling_usd: float,
        *,
        usd_per_million_tokens_prior: float,
        max_calls: int,
    ) -> "SpendGuard":
        """Build a guard whose combined token budget is derived from a $ ceiling + prior.

        The single budget is applied to input and output separately as a simple, strict
        bound (each capped at the full budget) so either stream alone tripping aborts."""
        budget = tokens_for_dollar_ceiling(
            ceiling_usd, usd_per_million_tokens_prior=usd_per_million_tokens_prior
        )
        return cls(max_calls=max_calls, max_input_tokens=budget, max_output_tokens=budget)

    def register_attempt(self) -> None:
        """Call BEFORE issuing a request: counts the attempt and enforces the call ceiling.

        Counting at attempt time (not on success) is what makes the call ceiling a real
        backstop: a call that errors or is retried-then-fails never reaches
        :meth:`register_usage`, so if attempts weren't counted a systematically-failing loop
        would spin forever while the guard read zero. The call ceiling is the coarse,
        model-independent bound that still trips when token capture is impossible."""
        if self.calls >= self.max_calls:
            raise CeilingBreach(f"call ceiling reached: {self.calls}/{self.max_calls} calls")
        self.calls += 1

    def register_usage(self, usage: UsageVector) -> None:
        """Call AFTER a completed call: add measured tokens; abort if a token cap is breached.

        Does NOT advance the call count (that happened at :meth:`register_attempt`). Must run
        even if persisting the record fails, so spend is never lost to an IO error."""
        self.input_tokens += (
            usage.input_tokens + usage.cache_read_input_tokens + usage.cache_creation_input_tokens
        )
        self.output_tokens += usage.output_tokens
        if self.max_input_tokens is not None and self.input_tokens > self.max_input_tokens:
            raise CeilingBreach(
                f"input-token ceiling breached: {self.input_tokens}/{self.max_input_tokens}"
            )
        if self.max_output_tokens is not None and self.output_tokens > self.max_output_tokens:
            raise CeilingBreach(
                f"output-token ceiling breached: {self.output_tokens}/{self.max_output_tokens}"
            )

    def snapshot(self) -> dict:
        """Current totals + caps for the run's config-snapshot."""
        return {
            "calls": self.calls,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "max_calls": self.max_calls,
            "max_input_tokens": self.max_input_tokens,
            "max_output_tokens": self.max_output_tokens,
        }
