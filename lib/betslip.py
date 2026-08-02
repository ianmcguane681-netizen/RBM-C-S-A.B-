"""What to type, where, in what order — and what to do when the second leg is gone.

Bookmakers do not have betting APIs. bet365 and Sky Bet will not take an order from a
program, and no amount of engineering changes that, so a bookmaker-to-bookmaker arbitrage is
executed by a person with two tabs open. The deliverable is therefore not an adapter. It is
**a slip good enough to execute from while a price is moving**, which is a different and in
some ways harder thing.

Three properties, and the third is the one that earns its place at two in the afternoon with
one leg already on.

**Stakes are computed to the penny and stated as the amount to type.** Not a percentage, not
a ratio, not "size proportionally". A number to enter in a box, floored so the book cannot
reject it for exceeding what was offered.

**The order is stated and it is not arbitrary.** The leg most likely to disappear goes
first: the shorter price at the softer book, because that is the one being taken by everyone
else who saw it. Failing on the first leg costs nothing. Failing on the second leaves money
on a single selection.

**The abort plan is written BEFORE the first bet goes on.** This is the part slips normally
omit and the part that matters. Once leg one is placed and leg two has vanished, the person
holding an unhedged position is under time pressure, is disappointed, and is exactly the
wrong person to be inventing a plan. So the slip carries, in advance: what the exposure is
in pounds, what the break-even price on the remaining leg would be, and the explicit
permission to accept a small stated loss rather than chase.

## What this cannot fix

Two bets at two bookmakers cannot be placed atomically. The gap between them is the risk,
and it is a risk of the activity rather than of the tooling.

And there is a constraint no slip addresses: **soft bookmakers restrict accounts that
arbitrage.** bet365 and Sky Bet are among the quickest to do it. A slip that works perfectly
for six weeks and then meets a £4.31 maximum stake has not malfunctioned; that is the
business model working as intended, and it should be expected rather than discovered.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

READY_TO_PLACE = "READY_TO_PLACE"
DO_NOT_PLACE = "DO_NOT_PLACE"

#: Below this, a slip is not worth the exposure of placing two bets by hand. Stated rather
#: than judged in the moment, and deliberately not a score.
MINIMUM_RETURN_PCT = 0.5


def _pennies(value: float) -> float:
    """Down, always. A stake rounded up is a stake the book may refuse."""

    return math.floor(value * 100) / 100


@dataclass(frozen=True, slots=True)
class SlipLeg:
    book: str
    selection: str
    decimal_odds: float
    stake: float
    #: What the source said was available. Zero means nobody read it, which the slip says
    #: rather than assuming the book will take the stake.
    max_stake_seen: float = 0.0
    settlement_rule: str = ""

    @property
    def returns(self) -> float:
        return self.stake * self.decimal_odds

    @property
    def stake_is_confirmed(self) -> bool:
        return self.max_stake_seen > 0

    def describe(self, position: int) -> str:
        lines = [
            f"  {position}.  {self.book}",
            f"      back  {self.selection}  at  {self.decimal_odds}",
            f"      STAKE {self.stake:,.2f}          returns {self.returns:,.2f}",
        ]
        if not self.stake_is_confirmed:
            lines.append(
                "      max stake NOT READ. If the book offers less than this, do not "
                "scale up elsewhere — stop and re-slip."
            )
        return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class BetSlip:
    """One arbitrage, as a person executes it."""

    status: str
    market: str
    legs: tuple[SlipLeg, ...] = ()
    total_stake: float = 0.0
    guaranteed_return: float = 0.0
    reason: str = ""

    @property
    def return_pct(self) -> float:
        return (self.guaranteed_return / self.total_stake * 100.0) if self.total_stake else 0.0

    @property
    def concentrated_books(self) -> tuple[str, ...]:
        """Books carrying more than one leg.

        Legitimate — a book pricing two of three selections is not pricing a complete
        market — but concentrated. One account restriction, one voided market or one
        palpable-error claim takes out several legs at once, and the remaining leg is then
        an unhedged bet rather than half an arb. Found by running a three-way slip and
        noticing two legs had landed at the same book.
        """

        seen: dict[str, int] = {}
        for leg in self.legs:
            seen[leg.book] = seen.get(leg.book, 0) + 1
        return tuple(sorted(book for book, count in seen.items() if count > 1))

    @property
    def worst_case_if_a_leg_fails(self) -> float:
        """The loss if the first leg goes on and the second never does.

        The whole first stake is at risk on a single selection. This is the number the
        abort plan is built around and it is always much larger than the return.
        """

        return -self.legs[0].stake if self.legs else 0.0

    def break_even_odds_for(self, index: int) -> float:
        """What the remaining leg must pay to get the money back, if the price moved.

        Not a target to chase. It exists so a person can see at a glance whether the
        remaining price is anywhere near recoverable, and usually it is not.
        """

        if len(self.legs) < 2 or index >= len(self.legs):
            return 0.0
        placed = sum(leg.stake for i, leg in enumerate(self.legs) if i != index)
        remaining = self.legs[index].stake
        return (placed + remaining) / remaining if remaining else 0.0

    def describe(self) -> str:
        if self.status == DO_NOT_PLACE:
            return f"DO NOT PLACE  {self.market}\n  {self.reason}"

        lines = [
            f"BET SLIP  {self.market}",
            f"  total stake {self.total_stake:,.2f}   guaranteed return "
            f"{self.guaranteed_return:,.2f}  ({self.return_pct:+.2f}%)",
            "",
            "PLACE IN THIS ORDER. The first leg is the one most likely to vanish.",
            "",
        ]
        lines += [leg.describe(i + 1) for i, leg in enumerate(self.legs)]
        lines += [
            "",
            "IF THE SECOND LEG IS GONE WHEN YOU GET THERE",
            f"  You are exposed {abs(self.worst_case_if_a_leg_fails):,.2f} on "
            f"{self.legs[0].selection} at {self.legs[0].book}.",
            f"  Break-even on the remaining leg needs "
            f"{self.break_even_odds_for(len(self.legs) - 1):.3f} or better.",
            "  If it is not there: TAKE THE SMALL LOSS. Do not place a worse price to feel",
            "  hedged, and do not increase the stake to make it back. Both of those turn a",
            "  bounded loss into an unbounded position, and this line is written now",
            "  precisely because it is not the advice you will want in the moment.",
            "",
            "BEFORE YOU PLACE, CHECK BY EYE",
            "  - the selections are the same event and the same market at both books",
            "  - the prices are still what is written above",
            "  - both books settle the same way on a non-runner and an abandonment",
        ]
        for book in self.concentrated_books:
            carried = sum(1 for leg in self.legs if leg.book == book)
            lines.append(
                f"  - {carried} of {len(self.legs)} legs are at {book}. One restriction, "
                f"void or\n    palpable-error claim there takes out {carried} legs at once "
                f"and leaves the rest unhedged."
            )
        if any(not leg.settlement_rule.strip() for leg in self.legs):
            lines.append(
                "  - SETTLEMENT RULES WERE NOT READ for at least one leg. No price feed "
                "carries them.\n    This is the check that catches the position that looks "
                "like an arb and is a bet."
            )
        return "\n".join(lines)


def build_slip(
    market: str,
    legs: Sequence[SlipLeg],
    *,
    bankroll_limit: float,
    minimum_return_pct: float = MINIMUM_RETURN_PCT,
) -> BetSlip:
    """Size the legs so every outcome returns the same, and order them for execution.

    Sized to the SMALLEST binding constraint: the bankroll limit, and any leg's read
    maximum. A leg whose maximum was never read does not bind, and the slip says so on that
    leg rather than assuming the book will take it.
    """

    legs = tuple(legs)
    if len(legs) < 2:
        return BetSlip(DO_NOT_PLACE, market,
                       reason="an arbitrage needs at least two legs")

    implied = sum(1.0 / leg.decimal_odds for leg in legs)
    if implied >= 1.0:
        return BetSlip(
            DO_NOT_PLACE, market,
            reason=(f"the combined implied probability is {implied * 100:.3f}%. That is "
                    f"the books' margin and it is the normal state of a market."),
        )

    # Total stake bounded by the bankroll AND by every leg whose maximum was actually read.
    ceilings = [bankroll_limit]
    for leg in legs:
        if leg.stake_is_confirmed:
            # This leg's share of the total is (1/odds)/implied, so a maximum on the leg
            # implies a maximum on the whole position.
            share = (1.0 / leg.decimal_odds) / implied
            ceilings.append(leg.max_stake_seen / share)
    total = _pennies(min(ceilings))

    sized = tuple(
        SlipLeg(
            leg.book, leg.selection, leg.decimal_odds,
            _pennies(total * (1.0 / leg.decimal_odds) / implied),
            leg.max_stake_seen, leg.settlement_rule,
        )
        for leg in legs
    )
    # Recomputed from the FLOORED stakes, never from the ratio. Every earlier version of
    # this arithmetic in this repository over-reported by a fraction of a penny per leg.
    staked = sum(leg.stake for leg in sized)
    guaranteed = min(leg.returns for leg in sized) - staked

    if staked <= 0 or guaranteed / staked * 100.0 < minimum_return_pct:
        return BetSlip(
            DO_NOT_PLACE, market, sized, staked, guaranteed,
            reason=(f"{guaranteed / staked * 100.0:.3f}% return once stakes are floored to "
                    f"the penny, under a {minimum_return_pct:.2f}% floor. Two bets placed "
                    f"by hand carry more risk than this pays for."
                    if staked > 0 else "no stake could be sized"),
        )

    # Shortest price first: it is the one everybody else who saw this is also taking, so it
    # is the one most likely to be gone by the time you get there.
    ordered = tuple(sorted(sized, key=lambda leg: leg.decimal_odds))
    return BetSlip(READY_TO_PLACE, market, ordered, staked, guaranteed)
