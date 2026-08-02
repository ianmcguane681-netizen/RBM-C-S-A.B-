"""Place bets — and say plainly when one leg matched and the other did not.

The second execution adapter. Everything in `connectors/alpaca.py` about an unknown submit
applies here and applies harder: a bet is irreversible the moment it matches. There is no
sell, no cancel-after-fill, and no counterparty to ring.

## The failure this module exists to name

An exchange **partially matches as a matter of course**. Ask for £250 at 2.16 and you may
get £80, because that is all anyone was offering at that price. For an ordinary bet that is
a smaller bet. For an arbitrage it is a different thing entirely:

    leg A matched £250   leg B matched £80

is not "an arb at a smaller size". It is a £250 position on one outcome, hedged for £80, and
an unhedged £170 bet on a selection nobody chose to back. **A partially matched arb is worse
than an arb that never went on**, because the second costs nothing and the first is a
directional position taken by accident.

So `LEG_EXPOSED` is a first-class state and it is what the module is shaped around. It is
reported loudly, with the exposed amount and the selection, because it is the one outcome
that needs a person immediately.

## Sequencing, and the risk no code removes

Two legs cannot be placed atomically at two venues. One goes first, and between them the
price can move or vanish. This adapter places the **thinnest side first** — the leg with the
least available stake, which is the one most likely to disappear — because failing on the
first leg costs nothing and failing on the second leaves you exposed.

That reduces the risk. It does not remove it, nothing does, and a system implying otherwise
would be lying about the central hazard of the activity.

## What it will not do

Originate anything, or place without a `PERMITTED` permission attached. Same as the broker
adapter and for the same reason: the last thing before money moves re-reads the
authorisation rather than trusting that somebody upstream did.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Sequence

from lib.http_retry import TransientRetrievalError
from lib.thesis import PERMITTED, Permission

MATCHED = "MATCHED"
PART_MATCHED = "PART_MATCHED"
UNMATCHED = "UNMATCHED"
REJECTED = "REJECTED"
UNKNOWN = "UNKNOWN"
NOT_CONFIGURED = "NOT_CONFIGURED"

#: The arbitrage-level outcome that matters. One leg on, another not, and money at risk on
#: a single selection that nobody decided to back.
LEG_EXPOSED = "LEG_EXPOSED"
ALL_LEGS_MATCHED = "ALL_LEGS_MATCHED"
NOTHING_PLACED = "NOTHING_PLACED"

BETTING_URL = "https://api.betfair.com/exchange/betting/rest/v1.0"

#: Betfair restricts customerOrderRef to alphanumerics, dashes and dots, 32 characters.
_REF_ALLOWED = re.compile(r"[^A-Za-z0-9.-]")

_ORDER_STATUS = {
    "EXECUTION_COMPLETE": MATCHED,
    "EXECUTABLE": UNMATCHED,
    "EXPIRED": REJECTED,
    "PENDING": UNKNOWN,
}


def bet_ref(market_id: str, selection_id: int, side: str, size: float, price: float,
            thesis_declared_at: str) -> str:
    """A stable reference for one intended bet.

    Derived from the intent, never the moment. Betfair rejects a duplicate
    `customerOrderRef`, so a retry after an UNKNOWN is refused by the exchange rather than
    accepted as a second bet — which on an irreversible instrument is the whole defence.
    """

    seed = f"{market_id}|{selection_id}|{side}|{size:.2f}|{price:.4f}|{thesis_declared_at}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]
    return _REF_ALLOWED.sub("", f"eb-{digest}")[:32]


@dataclass(frozen=True, slots=True)
class BetInstruction:
    """One sized, authorised bet on one selection."""

    market_id: str
    selection_id: int
    side: str
    size: float
    price: float
    permission: Permission
    customer_order_ref: str
    #: What the source said was available at this price when the candidate was found. Used
    #: only to order the legs, never to assume a fill.
    available_when_seen: float = 0.0

    def __post_init__(self) -> None:
        if self.side not in {"BACK", "LAY"}:
            raise ValueError(f"side must be BACK or LAY, not {self.side!r}")
        if self.size <= 0:
            raise ValueError("size must be positive")
        if self.price <= 1.0:
            raise ValueError("price must exceed 1.0")
        if not self.customer_order_ref.strip():
            raise ValueError(
                "a customer order ref is required: on an irreversible instrument it is the "
                "only thing standing between a retry and a second bet"
            )


@dataclass(frozen=True, slots=True)
class BetResult:
    status: str
    market_id: str
    selection_id: int
    customer_order_ref: str
    requested_size: float = 0.0
    matched_size: float = 0.0
    average_price: float = 0.0
    bet_id: str = ""
    reason: str = ""

    @property
    def unmatched_size(self) -> float:
        return max(0.0, self.requested_size - self.matched_size)

    @property
    def may_have_been_placed(self) -> bool:
        return self.status not in {REJECTED, NOT_CONFIGURED}

    def describe(self) -> str:
        if self.status == UNKNOWN:
            return (
                f"UNKNOWN  {self.market_id}/{self.selection_id} {self.requested_size:,.2f}\n"
                f"  {self.reason}\n"
                f"  This is NOT a report that the bet was not placed. A bet is irreversible "
                f"once matched. DO NOT RE-PLACE — query {self.customer_order_ref}."
            )
        if self.status == PART_MATCHED:
            return (
                f"PART_MATCHED  {self.market_id}/{self.selection_id}: "
                f"{self.matched_size:,.2f} of {self.requested_size:,.2f} at "
                f"{self.average_price:.3f}. {self.unmatched_size:,.2f} unmatched."
            )
        if self.status == MATCHED:
            return (f"MATCHED  {self.market_id}/{self.selection_id}: "
                    f"{self.matched_size:,.2f} at {self.average_price:.3f}")
        return f"{self.status}  {self.market_id}/{self.selection_id}: {self.reason}"


@dataclass(frozen=True, slots=True)
class ArbExecution:
    """What happened across every leg, and the exposure if it went wrong."""

    status: str
    results: tuple[BetResult, ...] = ()
    reason: str = ""

    @property
    def exposed_legs(self) -> tuple[BetResult, ...]:
        """Legs carrying matched money whose counterpart legs did not fully match."""

        if self.status != LEG_EXPOSED:
            return ()
        return tuple(r for r in self.results if r.matched_size > 0)

    @property
    def exposure(self) -> float:
        """The largest matched stake with no completed hedge behind it."""

        if self.status != LEG_EXPOSED:
            return 0.0
        matched = [r.matched_size for r in self.results if r.matched_size > 0]
        return max(matched) - min(matched) if len(matched) > 1 else max(matched, default=0.0)

    def describe(self) -> str:
        lines = [f"{self.status}"]
        if self.reason:
            lines.append(f"  {self.reason}")
        lines.append("")
        lines += [f"  {r.describe()}" for r in self.results]
        if self.status == LEG_EXPOSED:
            lines.append("")
            lines.append(
                f"  !! EXPOSED {self.exposure:,.2f}. This is not a smaller arb. It is a "
                f"directional position on a single selection, taken by accident, and it "
                f"needs a person NOW: hedge the remainder by hand or close what matched."
            )
        if self.status == ALL_LEGS_MATCHED:
            lines.append("")
            lines.append(
                "  Every leg matched in full at the sizes requested. The position is the "
                "one that was sized; it is not thereby a profitable one."
            )
        return "\n".join(lines)


class BetfairExecutor:
    """Places bets through an existing authenticated session. Originates nothing."""

    name = "Betfair Exchange"

    def __init__(self, session: Any | None) -> None:
        self.session = session

    @property
    def is_configured(self) -> bool:
        return self.session is not None

    def place_bet(self, instruction: BetInstruction) -> BetResult:
        """One leg. Refuses anything not positively permitted."""

        if instruction.permission.status != PERMITTED:
            return BetResult(
                REJECTED, instruction.market_id, instruction.selection_id,
                instruction.customer_order_ref, instruction.size,
                reason=(f"the attached permission is {instruction.permission.status}, not "
                        f"{PERMITTED}; INDETERMINATE is not a weaker yes"),
            )
        if not self.is_configured:
            return BetResult(
                NOT_CONFIGURED, instruction.market_id, instruction.selection_id,
                instruction.customer_order_ref, instruction.size,
                reason="no Betfair session; nothing was sent",
            )

        payload = {
            "marketId": instruction.market_id,
            "customerRef": instruction.customer_order_ref,
            "instructions": [{
                "selectionId": instruction.selection_id,
                "side": instruction.side,
                "orderType": "LIMIT",
                "customerOrderRef": instruction.customer_order_ref,
                "limitOrder": {
                    "size": round(instruction.size, 2),
                    "price": instruction.price,
                    # FILL_OR_KILL: match in full at this price or not at all. For an arb
                    # a partial match is the failure this module is named after, so the
                    # exchange is asked to refuse rather than to half-fill.
                    "timeInForce": "FILL_OR_KILL",
                },
            }],
        }

        try:
            report = self.session.call(f"{BETTING_URL}/placeOrders/", payload)
        except (TransientRetrievalError, OSError, ValueError) as error:
            return BetResult(
                UNKNOWN, instruction.market_id, instruction.selection_id,
                instruction.customer_order_ref, instruction.size,
                reason=f"{type(error).__name__}: {error}"[:140],
            )
        return self._to_result(report, instruction)

    def place_arb(self, instructions: Sequence[BetInstruction]) -> ArbExecution:
        """Every leg, thinnest first, stopping the moment a leg fails.

        Thinnest first because the leg with least available stake is the one most likely to
        vanish, and failing on the FIRST leg costs nothing while failing on a later one
        leaves money on a single selection. Stopping on failure is the same reasoning: once
        one leg has not gone on, placing the rest adds exposure rather than removing it.
        """

        if len(instructions) < 2:
            return ArbExecution(NOTHING_PLACED, (),
                                "an arb needs at least two legs; nothing was placed")

        ordered = sorted(instructions, key=lambda i: i.available_when_seen or float("inf"))
        results: list[BetResult] = []

        for instruction in ordered:
            result = self.place_bet(instruction)
            results.append(result)
            if result.status != MATCHED:
                break

        placed = [r for r in results if r.matched_size > 0]
        if not placed:
            return ArbExecution(
                NOTHING_PLACED, tuple(results),
                "no leg matched, so no money is at risk. This is the cheap failure and it "
                "is the one to prefer.",
            )
        if len(results) == len(instructions) and all(r.status == MATCHED for r in results):
            return ArbExecution(ALL_LEGS_MATCHED, tuple(results))
        return ArbExecution(
            LEG_EXPOSED, tuple(results),
            f"{len(placed)} of {len(instructions)} leg(s) carry matched money and the "
            f"position is not hedged.",
        )

    @staticmethod
    def _to_result(report: Any, instruction: BetInstruction) -> BetResult:
        if not isinstance(report, dict):
            return BetResult(
                UNKNOWN, instruction.market_id, instruction.selection_id,
                instruction.customer_order_ref, instruction.size,
                reason=f"unrecognised response shape: {type(report).__name__}",
            )

        status = str(report.get("status") or "")
        reports = report.get("instructionReports") or []
        if status == "FAILURE" and not reports:
            return BetResult(
                REJECTED, instruction.market_id, instruction.selection_id,
                instruction.customer_order_ref, instruction.size,
                reason=str(report.get("errorCode") or "FAILURE with no instruction report"),
            )
        if not reports:
            # A SUCCESS carrying no instruction report says nothing about the bet. Treated
            # as unknown rather than as a silent success.
            return BetResult(
                UNKNOWN, instruction.market_id, instruction.selection_id,
                instruction.customer_order_ref, instruction.size,
                reason=f"status {status!r} with no instruction report",
            )

        row = reports[0]
        if str(row.get("status")) == "FAILURE":
            return BetResult(
                REJECTED, instruction.market_id, instruction.selection_id,
                instruction.customer_order_ref, instruction.size,
                reason=str(row.get("errorCode") or "instruction rejected"),
            )

        matched = float(row.get("sizeMatched") or 0.0)
        order_status = _ORDER_STATUS.get(str(row.get("orderStatus") or ""), UNKNOWN)
        # An EXECUTION_COMPLETE with less matched than requested is a partial fill however
        # complete the exchange calls it. Checked rather than trusted.
        if order_status == MATCHED and 0 < matched < round(instruction.size, 2):
            order_status = PART_MATCHED
        elif order_status == MATCHED and matched <= 0:
            # Complete, and nothing matched: FILL_OR_KILL killed it. No money at risk.
            order_status = REJECTED

        return BetResult(
            status=order_status,
            market_id=instruction.market_id,
            selection_id=instruction.selection_id,
            customer_order_ref=str(row.get("customerOrderRef")
                                   or instruction.customer_order_ref),
            requested_size=instruction.size,
            matched_size=matched,
            average_price=float(row.get("averagePriceMatched") or 0.0),
            bet_id=str(row.get("betId") or ""),
            reason="" if order_status != REJECTED else "killed unmatched at the asked price",
        )
