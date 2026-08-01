"""CG-06: a figure that cannot be regenerated is a claim.

Every `ChainReading` already carries the chain, block height, contract, query and hash
needed to reproduce it. That makes provenance structural rather than remembered, which is
most of CG-06 — but it proves the figure was *recorded* properly, not that it is *true*.

Re-running a sample at its recorded height is what closes the gap. Three outcomes, and the
third is the one that matters:

    REPRODUCED     the same query at the same height returns the same hash
    DIVERGED       it does not -- a real finding about the provider, not an error
    NOT_ATTEMPTED  the re-run could not be made

`NOT_ATTEMPTED` exists because archive availability is drawn per request on unkeyed
providers. A sample that could not be run must never be counted as a sample that passed,
and a resample rate computed over attempts that never happened is a coverage figure over a
denominator that does not exist. This system has met that defect in a court archive, in a
proxy probe and in a liquidity venue; here it is again.

Divergence is not an exception either. A provider returning different state for the same
pinned height is not serving what it claims, and that is exactly the kind of thing a
reviewer needs told rather than retried away.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Sequence

from connectors.chain import (
    ChainAccessError,
    ChainClient,
    ChainReading,
    _is_block_reference,
)
from lib.http_retry import TransientRetrievalError

REPRODUCED = "REPRODUCED"
DIVERGED = "DIVERGED"
NOT_ATTEMPTED = "NOT_ATTEMPTED"


@dataclass(frozen=True, slots=True)
class ResampleOutcome:
    """One reading, re-run or not, and what came back."""

    status: str
    reading: ChainReading
    observed_sha256: str = ""
    reason: str = ""

    @property
    def block_number(self) -> int:
        return self.reading.block_number


@dataclass(frozen=True, slots=True)
class ResampleResult:
    """What a re-run establishes about a set of readings.

    There is no single "pass rate" property. A rate would have to choose a denominator,
    and both available choices are wrong: over attempted, it hides how little was
    attempted; over requested, it counts unattempted samples as failures. The three counts
    are reported and the reviewer picks the question.
    """

    outcomes: tuple[ResampleOutcome, ...]
    requested: int
    provider: str
    serves_archive: bool

    @property
    def reproduced(self) -> tuple[ResampleOutcome, ...]:
        return tuple(o for o in self.outcomes if o.status == REPRODUCED)

    @property
    def diverged(self) -> tuple[ResampleOutcome, ...]:
        return tuple(o for o in self.outcomes if o.status == DIVERGED)

    @property
    def not_attempted(self) -> tuple[ResampleOutcome, ...]:
        return tuple(o for o in self.outcomes if o.status == NOT_ATTEMPTED)

    @property
    def establishes_reproducibility(self) -> bool:
        """True only when every sampled reading was attempted and every one reproduced.

        Deliberately strict. A partial resample establishes something about the readings
        it reached and nothing about CG-06, which is a claim about the set.
        """

        return bool(self.outcomes) and not self.diverged and not self.not_attempted

    def describe(self) -> str:
        lines = [
            f"Resampled {len(self.outcomes)} of {self.requested} requested reading(s) "
            f"via {self.provider}:",
            f"  reproduced     {len(self.reproduced)}",
            f"  diverged       {len(self.diverged)}",
            f"  not attempted  {len(self.not_attempted)}",
        ]
        for outcome in self.diverged:
            lines.append(
                f"  DIVERGED at block {outcome.block_number}: recorded "
                f"{outcome.reading.content_sha256[:16]}, observed "
                f"{outcome.observed_sha256[:16]}. The provider is not serving the state "
                f"it is being asked for."
            )
        if self.not_attempted:
            lines.append(
                f"  {len(self.not_attempted)} reading(s) could not be re-run. This "
                f"neither confirms nor contradicts them, and they are not counted as "
                f"reproduced."
            )
        if not self.serves_archive:
            lines.append(
                f"  {self.provider} is not a reliable archive provider, so a resample "
                f"here is opportunistic rather than a measurement of reproducibility."
            )
        return "\n".join(lines)


def resample(
    client: ChainClient,
    readings: Sequence[ChainReading],
    *,
    fraction: float = 1.0,
    rng: random.Random | None = None,
    **kw: Any,
) -> ResampleResult:
    """Re-run a sample of readings at their recorded heights.

    Sampling is random rather than first-n. Re-running the first few would systematically
    check the readings taken earliest, which on a walk that degrades over time are the ones
    least likely to be wrong.
    """

    if not 0 < fraction <= 1:
        raise ValueError("fraction must be within (0, 1]")

    chooser = rng or random.Random()
    pool = list(readings)
    sample_size = max(1, round(len(pool) * fraction)) if pool else 0
    sampled = chooser.sample(pool, sample_size) if sample_size else []

    outcomes: list[ResampleOutcome] = []
    for reading in sampled:
        try:
            repeated = client.read(
                reading.method,
                [p for p in reading.params if not _is_block_reference(p)],
                block_number=reading.block_number,
                **kw,
            )
        except (TransientRetrievalError, ChainAccessError) as error:
            outcomes.append(
                ResampleOutcome(NOT_ATTEMPTED, reading, reason=str(error)[:120])
            )
            continue
        status = REPRODUCED if repeated.content_sha256 == reading.content_sha256 else DIVERGED
        outcomes.append(ResampleOutcome(status, reading, repeated.content_sha256))

    return ResampleResult(
        outcomes=tuple(outcomes),
        requested=len(sampled),
        provider=client.provider.name,
        serves_archive=client.provider.serves_archive,
    )
