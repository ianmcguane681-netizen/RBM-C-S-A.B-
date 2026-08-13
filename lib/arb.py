"""Is this actually a lock, and what happens when it isn't?

An arbitrage is two prices on the same outcome that together guarantee a return. The maths
is trivial. Everything that makes arbing lose money is in the words "the same outcome", and
this module is built around that rather than around the arithmetic.

**The killer is settlement, not price.** Two books offering "Team A to win" can settle
differently: one voids on abandonment and the other pays, one settles at 90 minutes and the
other includes extra time, one applies dead-heat reduction and the other does not. Both legs
priced correctly, and the arb is a coin flip. So a `Leg` cannot be constructed without its
settlement rule, and `is_lock` refuses any pair whose rules are not declared identical.

**A guaranteed profit is guaranteed only if both legs stand.** If one leg voids and the
other loses, the whole stake on the losing side is gone. That exposure is computed and
reported beside the profit, always, because a 2% edge with a 98% one-sided downside is not
a 2% edge.

**Odds without a size are not odds.** The headline price is available for a limited stake
and often for very little of it. Every leg carries `max_stake`, and a lock that cannot be
filled at the size required is reported as unfillable rather than as profit.

No forecast, no probability estimate, no expected value over repeated plays. Those need a
model of what will happen; this needs only what is offered right now.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

from guards.human_acts import is_automation

LOCK = "LOCK"
NO_LOCK = "NO_LOCK"
UNFILLABLE = "UNFILLABLE"
SETTLEMENT_MISMATCH = "SETTLEMENT_MISMATCH"
INDETERMINATE = "INDETERMINATE"


@dataclass(frozen=True, slots=True)
class Leg:
    """One side of a proposed arb, priced somewhere, under some rules.

    `settlement_rule` is mandatory and free text on purpose: it is the operator's own
    wording, quoted rather than normalised, because normalising it is exactly where two
    different rules become one and the arb becomes a bet.
    """

    book: str
    market: str
    selection: str
    decimal_odds: float
    settlement_rule: str
    max_stake: float
    observed_at: str
    commission_pct: float = 0.0

    def __post_init__(self) -> None:
        if self.decimal_odds <= 1.0:
            raise ValueError(f"{self.book}: decimal odds must exceed 1.0")
        if not self.settlement_rule.strip():
            raise ValueError(
                f"{self.book}: a leg without a stated settlement rule cannot be compared "
                f"to another leg"
            )
        if self.max_stake <= 0:
            raise ValueError(f"{self.book}: a leg with no available stake is not a price")

    @property
    def net_odds(self) -> float:
        """Odds after the exchange's commission on winnings.

        Ignoring commission is the most common way a paper arb evaporates: a 2% edge on
        an exchange charging 5% of net winnings was never an edge.
        """

        return 1.0 + (self.decimal_odds - 1.0) * (1.0 - self.commission_pct / 100.0)

    @property
    def implied_pct(self) -> float:
        return 100.0 / self.net_odds


@dataclass(frozen=True, slots=True)
class ArbFinding:
    """What the two prices establish, and what they do not."""

    status: str
    legs: tuple[Leg, ...]
    total_stake: float = 0.0
    stakes: tuple[float, ...] = ()
    guaranteed_return: float = 0.0
    reason: str = ""
    equivalence: "EquivalenceDeclaration | None" = None

    @property
    def total_implied_pct(self) -> float:
        return sum(leg.implied_pct for leg in self.legs)

    @property
    def margin_pct(self) -> float:
        """How far under 100% the combined implied probabilities sit.

        Positive means a lock exists at these prices and sizes. It is not a rate of
        return: the return is `guaranteed_return` over `total_stake`, which is lower once
        commission and rounding are taken.
        """

        return 100.0 - self.total_implied_pct

    @property
    def return_pct(self) -> float:
        if not self.total_stake:
            return 0.0
        return self.guaranteed_return / self.total_stake * 100.0

    @property
    def worst_case_if_a_leg_voids(self) -> float:
        """The loss if one leg is voided and the other loses.

        A void returns its own stake and settles nothing, so the exposure is the whole
        stake on the other leg. This is the number that turns a 2% edge into a decision
        about counterparty risk rather than arithmetic.
        """

        return -max(self.stakes) if self.stakes else 0.0

    def describe(self) -> str:
        if self.status == SETTLEMENT_MISMATCH:
            return (
                f"NOT AN ARB: the legs settle under different rules.\n  {self.reason}\n"
                f"  Two correctly priced legs that settle differently are a bet, not a "
                f"lock, and this is the most common way arbitrage loses money."
            )
        if self.status == UNFILLABLE:
            return (
                f"A lock exists at these prices and cannot be filled: {self.reason}. "
                f"Headline odds are offered at a size, and this is not a finding of profit."
            )
        if self.status == INDETERMINATE:
            return (
                f"No conclusion: {self.reason}. This is not a finding that no arb exists."
            )
        if self.status == NO_LOCK:
            return (
                f"No lock. Combined implied probability is "
                f"{self.total_implied_pct:.2f}%, which is at or above 100%. Staking both "
                f"sides here loses {-self.margin_pct:.2f}% of turnover on average, and "
                f"'on average' is not a guarantee either way."
            )
        lines = [
            f"LOCK at {self.margin_pct:.2f}% margin, returning "
            f"{self.return_pct:.2f}% on {self.total_stake:,.2f} staked:",
        ]
        for leg, stake in zip(self.legs, self.stakes):
            lines.append(
                f"  {stake:>12,.2f} on {leg.selection} @ {leg.decimal_odds} "
                f"({leg.net_odds:.4f} net) with {leg.book}, max {leg.max_stake:,.2f}"
            )
        lines.append(f"  guaranteed return: {self.guaranteed_return:,.2f} whichever leg wins")
        lines.append(
            f"  IF ONE LEG VOIDS AND THE OTHER LOSES: {self.worst_case_if_a_leg_voids:,.2f}. "
            f"The guarantee holds only while both legs stand."
        )
        lines.append(
            f"  settlement, quoted from each operator and NOT normalised: "
            + " | ".join(f"{leg.book}: {leg.settlement_rule}" for leg in self.legs)
        )
        if self.equivalence is not None:
            lines.append(
                f"  THE RULES DIFFER IN WORDING. {self.equivalence.declared_by} declared "
                f"them equivalent: {self.equivalence.reasoning}"
            )
            if self.equivalence.scenarios_checked:
                lines.append(
                    f"  scenarios checked: "
                    + "; ".join(self.equivalence.scenarios_checked)
                )
            lines.append(
                "  This lock rests on that judgement. If the rules diverge in a scenario "
                "not checked above, it is a bet."
            )
        return "\n".join(lines)


def reduction_factor_odds(decimal_odds: float, reduction_pct: float) -> float:
    """Betfair Exchange: the reduction factor applies to the ODDS of remaining runners.

        new = (old - 1) * (1 - rf) + 1
    """

    return (decimal_odds - 1.0) * (1.0 - reduction_pct / 100.0) + 1.0


def rule4_effective_odds(decimal_odds: float, deduction_pct: float) -> float:
    """A traditional bookmaker: Rule 4 deducts a percentage of the WINNINGS.

    Different mechanism, same algebra -- deducting r from winnings and multiplying the net
    odds by (1 - r) are the same operation, so at equal rates the two settle identically.
    """

    winnings = (decimal_odds - 1.0) * (1.0 - deduction_pct / 100.0)
    return 1.0 + winnings


def non_runner_divergence(
    decimal_odds: float, exchange_reduction_pct: float, bookmaker_deduction_pct: float
) -> tuple[float, float, float]:
    """What a withdrawal actually costs on each side, and the gap between them.

    Built because the mechanisms LOOK incomparable and are not. Betfair Exchange applies a
    reduction factor to the odds; a bookmaker deducts from winnings under Rule 4. At equal
    rates those are the same number, which invites the conclusion that non-runners are a
    solved scenario.

    They are not. The rates come from different places -- Tattersalls' table keyed to the
    withdrawn horse's starting price, against a per-runner factor assigned from market
    percentage that moves -- and at least one bookmaker waives the first 5p while the
    Exchange waives nothing. So the divergence is computed rather than assumed away.
    """

    exchange = reduction_factor_odds(decimal_odds, exchange_reduction_pct)
    bookmaker = rule4_effective_odds(decimal_odds, bookmaker_deduction_pct)
    return exchange, bookmaker, bookmaker - exchange


@dataclass(frozen=True, slots=True)
class EquivalenceDeclaration:
    """A named human stating that two differently worded rules settle the same way.

    The first version of this module compared rule text for equality and nothing else, on
    the reasoning that no string comparison is entitled to decide two wordings mean the
    same thing. That reasoning is right and the consequence was a tool that refuses almost
    every real pair, which is useless and teaches its user to ignore it.

    A worked case, from Betfair and bet365's own dead-heat pages. Betfair: "your return
    will be half of what it could have been". bet365: "stake divided by the number of tying
    competitors, paid at full odds on that reduced stake, the remainder treated as lost".
    On 100 at 2.0 in a two-way dead heat both return 100. Same settlement, no shared words.

    So the judgement stays human and becomes a record instead of an assumption: who decided
    the rules match, and on what reasoning. The same shape as `board verify --by` -- an
    attestation the machine cannot make for itself and must not fake.
    """

    declared_by: str
    reasoning: str
    scenarios_checked: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        # `is_automation` rather than a tuple written out here. This call site listed four
        # prefixes while every other guard listed six, so `declared_by="bot: scanner"`
        # constructed a settlement equivalence — the one judgement that turns an arb from
        # INDETERMINATE into something placeable. Four plausible prefixes read exactly as
        # complete as six, which is why this must not be a local literal.
        if not self.declared_by.strip() or is_automation(self.declared_by):
            raise ValueError(
                "settlement equivalence must be declared by a named human; comparing "
                "wordings is exactly the judgement automation is not entitled to make"
            )
        if not self.reasoning.strip():
            raise ValueError(
                "a declaration without reasoning is indistinguishable from a guess"
            )


def _settlement_matches(
    legs: Sequence[Leg], equivalence: EquivalenceDeclaration | None = None
) -> bool:
    """Identical wording, or a human saying the different wordings settle alike.

    Still crude on its own, and still refusing by default. `equivalence` does not weaken
    that: it records who took responsibility for the judgement, so a mismatch that was
    waived is distinguishable in the record from one that never existed.
    """

    normalised = {" ".join(leg.settlement_rule.lower().split()) for leg in legs}
    return len(normalised) == 1 or equivalence is not None


def evaluate(
    legs: Sequence[Leg],
    *,
    target_stake: float = 0.0,
    equivalence: EquivalenceDeclaration | None = None,
) -> ArbFinding:
    """Two or more mutually exclusive, collectively exhaustive legs.

    Stakes are split so every outcome returns the same amount, which is what makes the
    return guaranteed rather than merely positive.
    """

    legs = tuple(legs)
    if len(legs) < 2:
        return ArbFinding(INDETERMINATE, legs, reason="an arb needs at least two legs")
    if len({leg.market for leg in legs}) != 1:
        return ArbFinding(
            SETTLEMENT_MISMATCH, legs,
            reason=f"different markets: {sorted({leg.market for leg in legs})}",
        )
    if len({leg.selection for leg in legs}) != len(legs):
        return ArbFinding(
            INDETERMINATE, legs, reason="two legs name the same selection"
        )
    if not _settlement_matches(legs, equivalence):
        return ArbFinding(
            SETTLEMENT_MISMATCH, legs,
            reason="; ".join(f"{leg.book}: {leg.settlement_rule!r}" for leg in legs),
        )

    total_implied = sum(leg.implied_pct for leg in legs)
    if total_implied >= 100.0:
        return ArbFinding(NO_LOCK, legs)

    # Equal return on every outcome: stake_i proportional to 1/odds_i.
    stake = target_stake if target_stake > 0 else min(
        leg.max_stake * total_implied / leg.implied_pct for leg in legs
    )
    # Floored to whole pennies, which is what can actually be staked, and floored rather
    # than rounded because rounding up can exceed a book's limit. Without this the auto
    # sizing produced 100.00000000000001 against a 100.00 limit and refused itself with
    # "BookA needs 100.00 but offers 100.00".
    stakes = tuple(
        math.floor(stake * leg.implied_pct / total_implied * 100) / 100 for leg in legs
    )
    stake = sum(stakes)

    over = [
        f"{leg.book} needs {s:,.2f} but offers {leg.max_stake:,.2f}"
        for leg, s in zip(legs, stakes) if s > leg.max_stake
    ]
    if over:
        return ArbFinding(
            UNFILLABLE, legs, total_stake=stake, stakes=stakes, reason="; ".join(over)
        )

    returns = [s * leg.net_odds for leg, s in zip(legs, stakes)]
    return ArbFinding(
        LOCK, legs, total_stake=stake, stakes=stakes,
        guaranteed_return=min(returns) - stake,
        equivalence=equivalence,
    )
