"""How much, bound by which constraint — and what a monitor event obliges you to do.

RBF-001 components 3 and 5. Neither originates anything: sizing answers *how much* for a
position someone else decided to take, and the obligation table answers *what now* for a
change someone else's monitor observed.

## Sizing

The size is the **minimum** of what each constraint allows, and the output names **which one
bound it**. That distinction is the whole value of the panel:

    sized to 4,200
      bound by: exit depth at 1.8% slippage
      your risk limit would have allowed 11,000

"My own rules are holding me back" and "the market cannot absorb me" are different
situations calling for different responses, and a single number hides which one you are in.

**An unmeasured constraint makes the size INDETERMINATE rather than dropping out.** This is
the same rule as `lib/candidates.py` and for the same reason: a constraint that is silently
skipped raises the permitted size, so the flattering direction is also the unmeasured one.
Volatility is the constraint most often unavailable — it needs price history — and a sizing
that quietly ignored it would let a position through at full risk limit precisely when
nothing is known about how far the price moves.

## Obligations

What a monitor event compels, chosen in advance and applied in the moment. That order
matters: these are decisions made while calm and executed while not.

The row that would be got wrong by default is the last one. **An `UNREADABLE` fact carries
no obligation at all.** A monitor that reduced a position because a node timed out would be
a catastrophe assembled out of an unhandled sentinel, and this repository has produced that
class of bug in six less consequential places.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

SIZED = "SIZED"
REFUSED = "REFUSED"
INDETERMINATE = "INDETERMINATE"

#: A constraint that could not be measured. Distinct from a constraint of zero, which is a
#: measurement saying you may take nothing.
NOT_MEASURED = -1.0


@dataclass(frozen=True, slots=True)
class Constraint:
    """One ceiling, and where it came from."""

    name: str
    limit: float
    detail: str = ""

    @property
    def is_measured(self) -> bool:
        return self.limit != NOT_MEASURED

    def describe(self) -> str:
        if not self.is_measured:
            return f"  {self.name}: NOT MEASURED — {self.detail}"
        return f"  {self.name}: {self.limit:,.2f}  {self.detail}"


@dataclass(frozen=True, slots=True)
class Size:
    status: str
    asset: str
    amount: float = 0.0
    currency: str = "EUR"
    constraints: tuple[Constraint, ...] = ()
    bound_by: str = ""

    @property
    def unmeasured(self) -> tuple[Constraint, ...]:
        return tuple(c for c in self.constraints if not c.is_measured)

    def describe(self) -> str:
        lines = []
        if self.status == INDETERMINATE:
            lines.append(f"INDETERMINATE  {self.asset}: no size can be stated.")
            lines.append(
                f"  {len(self.unmeasured)} constraint(s) were not measured. Sizing without "
                f"them would size against the constraints that happened to be available, "
                f"which is always the larger number."
            )
        elif self.status == REFUSED:
            lines.append(f"REFUSED  {self.asset}: every permitted size is zero or less.")
            lines.append(f"  bound by: {self.bound_by}")
        else:
            lines.append(f"SIZED  {self.asset}: {self.amount:,.2f} {self.currency}")
            lines.append(f"  bound by: {self.bound_by}")
            others = [c for c in self.constraints if c.name != self.bound_by and c.is_measured]
            if others:
                loosest = max(others, key=lambda c: c.limit)
                lines.append(
                    f"  {loosest.name} would have allowed {loosest.limit:,.2f}"
                )
        lines.append("")
        lines += [c.describe() for c in self.constraints]
        return "\n".join(lines)


def size_position(
    asset: str,
    constraints: Sequence[Constraint],
    *,
    currency: str = "EUR",
) -> Size:
    """The minimum of every measured ceiling, or INDETERMINATE if any is unmeasured.

    Rounded DOWN to the penny. An earlier auto-sizing produced 100.00000000000001 against
    a 100.00 limit and reported that a book offering exactly 100.00 could not supply it.
    """

    constraints = tuple(constraints)
    if not constraints:
        return Size(INDETERMINATE, asset, currency=currency)

    unmeasured = [c for c in constraints if not c.is_measured]
    if unmeasured:
        return Size(INDETERMINATE, asset, currency=currency, constraints=constraints)

    binding = min(constraints, key=lambda c: c.limit)
    amount = math.floor(binding.limit * 100) / 100
    if amount <= 0:
        return Size(REFUSED, asset, 0.0, currency, constraints, binding.name)
    return Size(SIZED, asset, amount, currency, constraints, binding.name)


def risk_limit(free_balance: float, pct_of_balance: float) -> Constraint:
    return Constraint(
        "risk limit", free_balance * pct_of_balance / 100.0,
        f"{pct_of_balance:.2f}% of {free_balance:,.2f} free",
    )


def exit_depth(value_at_tolerable_slippage: float, slippage_pct: float) -> Constraint:
    """CG-05, as a ceiling. You cannot size past what you can actually sell."""

    return Constraint(
        "exit depth", value_at_tolerable_slippage,
        f"exitable within {slippage_pct:.2f}% slippage",
    )


def volatility_bound(
    free_balance: float, realised_vol_pct: float | None, tolerated_move_pct: float
) -> Constraint:
    """Size so a one-window move costs no more than the tolerated fraction of balance.

    `None` volatility is NOT_MEASURED, never a zero and never ignored. It needs price
    history, which is the input most often absent, and skipping it raises the permitted
    size exactly when nothing is known about how far the price moves.
    """

    if realised_vol_pct is None:
        return Constraint(
            "volatility bound", NOT_MEASURED,
            "no price history available, so realised volatility is unknown",
        )
    if realised_vol_pct <= 0:
        return Constraint(
            "volatility bound", NOT_MEASURED,
            "realised volatility computed as zero, which is a measurement failure rather "
            "than a still market",
        )
    limit = free_balance * (tolerated_move_pct / realised_vol_pct)
    return Constraint(
        "volatility bound", limit,
        f"{realised_vol_pct:.2f}% realised against {tolerated_move_pct:.2f}% tolerated",
    )


def venue_maximum(available: float, venue: str) -> Constraint:
    return Constraint("venue maximum", available, f"offered by {venue}")


# --------------------------------------------------------------------------------------
# Obligations
# --------------------------------------------------------------------------------------

#: What the holder must do, chosen in advance. Ordered from most to least compelling.
EXIT_OR_REVIEW = "EXIT_OR_RE_REVIEW"
FREEZE = "FREEZE"
NO_ADDITIONS = "NO_ADDITIONS"
RE_READ = "RE_READ"
NONE = "NONE"


@dataclass(frozen=True, slots=True)
class Obligation:
    action: str
    fact: str
    why: str
    deadline_days: int = 0

    def describe(self) -> str:
        when = f" within {self.deadline_days} day(s)" if self.deadline_days else ""
        if self.action == NONE:
            return f"  {self.fact}: no obligation. {self.why}"
        return f"  !! {self.action}{when} — {self.fact}\n     {self.why}"


#: The table. Each row is a policy decided while calm and applied while not.
POLICY: dict[str, tuple[str, str, int]] = {
    "implementation": (EXIT_OR_REVIEW,
                       "Every fact the board established was established about different "
                       "code. The review rests on nothing until it is re-run.", 7),
    "admin": (EXIT_OR_REVIEW,
              "Who can replace the code has changed, so the guarantees survive only as "
              "long as a different party chooses not to act.", 7),
    "proxy_status": (EXIT_OR_REVIEW,
                     "The upgradeability of the contract itself has changed.", 7),
    "paused": (FREEZE,
               "Transfers may be halted, which means you may be unable to exit at all. "
               "Sizing and cost floors are meaningless while this holds.", 0),
    "owner": (NO_ADDITIONS,
              "Authority moved. Material, and a re-review is required before adding.", 0),
    "masterMinter": (NO_ADDITIONS,
                     "Mint authority moved. Supply guarantees are now held by a different "
                     "party.", 0),
    "restatements": (NO_ADDITIONS,
                     "A figure the review relied on was refiled at another value.", 0),
    "tag": (RE_READ,
            "The filer changed XBRL tag, so the series relied on may be silently stale.", 0),
}


def obligations_for(changes: Sequence) -> tuple[Obligation, ...]:
    """Map monitor changes to what they compel.

    An UNREADABLE change carries NO obligation. A monitor that reduced a position because
    a node timed out would be a catastrophe built out of an unhandled sentinel, and this
    is the row that would be got wrong by default.
    """

    from lib.ledger import ABSENT, CHANGED, UNREADABLE

    out: list[Obligation] = []
    for change in changes:
        fact = f"{change.subject} {change.fact}"

        if change.status == UNREADABLE:
            out.append(Obligation(
                NONE, fact,
                "The fact was NOT read this run. A failed read is not an event, the "
                "previous value stands, and nothing is owed.",
            ))
            continue

        if change.status not in {CHANGED, ABSENT}:
            continue

        key = next(
            (k for k in POLICY if k == change.fact or change.fact.endswith(f":{k}")), ""
        )
        if not key:
            out.append(Obligation(
                NONE, fact,
                "Changed, and no policy row covers this fact. Recorded so the gap is "
                "visible rather than read as 'nothing required'.",
            ))
            continue

        action, why, days = POLICY[key]
        if change.status == ABSENT:
            why = f"The fact is no longer reported at all. {why}"
        out.append(Obligation(action, fact, why, days))
    return tuple(out)


def summarise_obligations(obligations: Sequence[Obligation]) -> str:
    compelling = [o for o in obligations if o.action != NONE]
    if not compelling:
        return (
            "No obligation arises from this run. That covers only the facts in the ledger, "
            "and says nothing about anything not being watched."
        )
    lines = [f"{len(compelling)} obligation(s) arise from this run:"]
    order = (EXIT_OR_REVIEW, FREEZE, NO_ADDITIONS, RE_READ)
    lines += [o.describe() for a in order for o in compelling if o.action == a]
    lines.append("")
    lines.append(
        "Each is a policy chosen in advance rather than a judgement made now. That is the "
        "point of having written it down."
    )
    return "\n".join(lines)
