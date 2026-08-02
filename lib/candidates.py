"""Whether an opportunity is worth putting in front of a person — as a cascade, not a score.

The suggestion this replaces was a weighted Opportunity Score: settlement certainty,
liquidity, price freshness, profit percent, commission, execution complexity and historical
reliability, summed to a number out of a hundred, with a threshold above which things get
surfaced. The dimensions are the right dimensions. The sum is the problem, and the argument
against it is a position this board actually failed.

That position scored well on six of the seven. Liquidity fine, freshness forty seconds,
profit positive net of two percent commission, commission known, two legs and trivial to
execute. One dimension was fatal: on abandonment the exchange leg voids and the bookmaker
leg stands if the fixture is replayed within forty-eight hours. Any sane weighting puts six
good dimensions past a threshold and surfaces an unhedged single bet for the whole
bookmaker stake.

**Settlement equivalence is not a dimension. It is a precondition.** No quantity of profit
compensates for the legs not being the same event. A weighted sum treats a disqualifier as
a deduction, which is a category error, and it is the specific error that turns an evidence
system into a scoring model.

The second problem is worse because it is invisible. **What score does an unmeasured
dimension get?** A scan that reached nought of five books knows nothing about market
liquidity. Scored as zero it drags the total down and real opportunities are missed. Left
out of the average it *raises* the score — the number goes up because less was looked at.
There is no honest scalar for `NOT_ASSESSED`, and a score is a machine for committing that
error at speed.

So: the same dimensions, kept apart, evaluated in order, with the first refusal decisive
and any unmeasured stage blocking the surface rather than averaging away.

    REFUSED        a stage said no, and which one is named
    INDETERMINATE  a stage could not be evaluated; this does NOT surface
    SURFACED       every stage was evaluated and none refused

`INDETERMINATE` is separate from `REFUSED` because "the settlement rules say no" and "I
could not read the settlement rules" call for different responses, and merging them either
hides a refusal or invents one.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

PASSED = "PASSED"
REFUSED = "REFUSED"
INDETERMINATE = "INDETERMINATE"
SURFACED = "SURFACED"

#: Stage verdicts, worst first. A known refusal outranks an unknown, because a definitive
#: disqualifier is decisive whatever else could not be measured.
PRECEDENCE = (REFUSED, INDETERMINATE, PASSED)


@dataclass(frozen=True, slots=True)
class Stage:
    """One question, its answer, and why — never a number."""

    name: str
    verdict: str
    detail: str = ""
    #: True when this stage alone can disqualify. Recorded so a reader can see which
    #: questions were preconditions and which were preferences.
    disqualifying: bool = False

    def describe(self) -> str:
        mark = {PASSED: "  ok  ", REFUSED: " STOP ", INDETERMINATE: "  ??  "}[self.verdict]
        gate = " (precondition)" if self.disqualifying else ""
        return f"[{mark}] {self.name}{gate}\n         {self.detail}"


@dataclass(frozen=True, slots=True)
class Candidate:
    subject: str
    stages: tuple[Stage, ...] = field(default_factory=tuple)

    @property
    def verdict(self) -> str:
        for level in PRECEDENCE:
            if level == PASSED:
                break
            if any(stage.verdict == level for stage in self.stages):
                return level if level == REFUSED else INDETERMINATE
        return SURFACED

    @property
    def decided_by(self) -> Stage | None:
        """The first stage at the deciding level, in the order the stages were written.

        Order matters and is the author's: the cheapest and most fatal questions come
        first, so a position that cannot settle is refused before anyone prices it.
        """

        level = self.verdict
        if level == SURFACED:
            return None
        wanted = REFUSED if level == REFUSED else INDETERMINATE
        return next(stage for stage in self.stages if stage.verdict == wanted)

    def describe(self) -> str:
        lines = [f"{self.verdict}  {self.subject}"]
        decider = self.decided_by
        if decider is not None:
            lines.append(f"  decided by: {decider.name}")
        lines.append("")
        lines += [stage.describe() for stage in self.stages]
        if self.verdict == INDETERMINATE:
            lines.append("")
            lines.append(
                "  Not surfaced. A stage could not be evaluated, which is different from a "
                "stage saying no, and neither is a reason to act. Nothing here says the "
                "opportunity is bad; it says it has not been established."
            )
        if self.verdict == SURFACED:
            lines.append("")
            lines.append(
                "  Every stage was evaluated and none refused. That is the whole claim. It "
                "is not a ranking, there is no score, and nothing here says this is better "
                "than anything else that also surfaced."
            )
        return "\n".join(lines)


def screen(subject: str, stages: Sequence[Stage]) -> Candidate:
    """Run the cascade. Every stage is evaluated and reported, refusal or not.

    Short-circuiting would be cheaper and would throw away the reason a reader most wants:
    a position refused on settlement is worth knowing about if it was ALSO illiquid and
    stale, because the second pair says do not go looking for a fix.
    """

    return Candidate(subject, tuple(stages))


# --------------------------------------------------------------------------------------
# Stage builders. Each is deliberately a separate function returning a separate answer,
# because the moment they return numbers someone will add them up.
# --------------------------------------------------------------------------------------

def settlement_stage(status: str, reason: str = "") -> Stage:
    """AG-02. The precondition, and the one the worked example proved is not negotiable."""

    from lib.arb import INDETERMINATE as ARB_INDETERMINATE, SETTLEMENT_MISMATCH

    if status == SETTLEMENT_MISMATCH:
        return Stage("settlement equivalence", REFUSED, disqualifying=True, detail=(
            f"The legs do not settle under the same rules, so they are not the same event "
            f"and no margin makes them one. {reason}"
        ))
    if status == ARB_INDETERMINATE:
        return Stage("settlement equivalence", INDETERMINATE, disqualifying=True, detail=(
            f"Settlement equivalence could not be established. {reason}"
        ))
    return Stage("settlement equivalence", PASSED, disqualifying=True, detail=(
        "The legs settle under matching rules, or a named human declared them equivalent "
        "with the scenarios checked."
    ))


def seen_stage(verdict) -> Stage:
    """Has this already been put in front of you? Repeats do not refuse."""

    from lib.seen import ACTED_ON, NEW, SEEN_BEFORE, UNCHECKED

    if verdict.status == UNCHECKED:
        return Stage("already seen", INDETERMINATE, detail=verdict.describe())
    if verdict.status == ACTED_ON:
        return Stage("already seen", REFUSED, disqualifying=True, detail=(
            f"{verdict.describe()} Acting again would double a position already taken."
        ))
    if verdict.status == SEEN_BEFORE:
        # Not a refusal. A standing opportunity that is still there is still real, and
        # auto-rejecting repeats would hide a persistent genuine edge.
        return Stage("already seen", PASSED, detail=verdict.describe())
    assert verdict.status == NEW
    return Stage("already seen", PASSED, detail="Not previously surfaced.")


def size_stage(available: float, wanted: float, *, binding: str = "") -> Stage:
    """Is there enough available stake, and which side is the constraint?"""

    if available <= 0:
        return Stage("executable size", INDETERMINATE, detail=(
            "No available size was measured. This is not a finding of zero depth; nothing "
            "was read."
        ))
    if available < wanted:
        return Stage("executable size", REFUSED, disqualifying=True, detail=(
            f"{available:,.2f} available against {wanted:,.2f} wanted"
            + (f", bound by {binding}" if binding else "")
        ))
    return Stage("executable size", PASSED, detail=(
        f"{available:,.2f} available against {wanted:,.2f} wanted"
        + (f", bound by {binding}" if binding else "")
    ))


def cost_stage(return_pct: float, cost_pct: float) -> Stage:
    """Does the edge survive the round trip? Commission is inside `return_pct` already."""

    if cost_pct < 0:
        return Stage("cost floor", INDETERMINATE, detail=(
            "Round-trip cost was not measured, so it is not known whether the edge "
            "survives it."
        ))
    if return_pct <= cost_pct:
        return Stage("cost floor", REFUSED, disqualifying=True, detail=(
            f"{return_pct:.2f}% return against {cost_pct:.2f}% round-trip cost. An edge "
            f"that has to clear its own friction before it is even wrong is a different "
            f"proposition from the one that was argued."
        ))
    return Stage("cost floor", PASSED, detail=(
        f"{return_pct:.2f}% return against {cost_pct:.2f}% round-trip cost"
    ))


def freshness_stage(age_seconds: float, limit_seconds: float) -> Stage:
    """How old is the oldest price? A price is perishable in a way a block height is not."""

    if age_seconds < 0:
        return Stage("price freshness", INDETERMINATE, detail=(
            "No observation timestamp was recorded, so the age of these prices is unknown "
            "and could be anything."
        ))
    if age_seconds > limit_seconds:
        return Stage("price freshness", REFUSED, disqualifying=True, detail=(
            f"Oldest price is {age_seconds:.0f}s old against a {limit_seconds:.0f}s limit. "
            f"Legs quoted this far apart were never simultaneously available."
        ))
    return Stage("price freshness", PASSED, detail=(
        f"Oldest price is {age_seconds:.0f}s old against a {limit_seconds:.0f}s limit"
    ))


def coverage_stage(answered: int, known: int) -> Stage:
    """How much of the intended universe was actually seen.

    Never a refusal on its own — a real opportunity at two books is still real. But a scan
    reaching nothing cannot establish that these were the best prices, and that is
    INDETERMINATE rather than a pass.
    """

    if answered <= 0:
        return Stage("scan coverage", INDETERMINATE, detail=(
            f"Nought of {known} source(s) answered. A better price may exist at a source "
            f"that was never asked, and absence of an arb here is absence of evidence."
        ))
    return Stage("scan coverage", PASSED, detail=(
        f"{answered} of {known} source(s) answered."
        + ("" if answered == known else " A better price may exist at one that did not.")
    ))
