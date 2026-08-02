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
        return "\n".join(lines)


def _settlement_matches(legs: Sequence[Leg]) -> bool:
    """Identical wording, compared case- and space-insensitively and nothing more.

    Deliberately crude. Anything smarter would be deciding that two differently worded
    rules mean the same thing, which is a judgement no string comparison is entitled to
    make and precisely the judgement that costs money when it is wrong.
    """

    normalised = {" ".join(leg.settlement_rule.lower().split()) for leg in legs}
    return len(normalised) == 1


def evaluate(legs: Sequence[Leg], *, target_stake: float = 0.0) -> ArbFinding:
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
    if not _settlement_matches(legs):
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
    )
