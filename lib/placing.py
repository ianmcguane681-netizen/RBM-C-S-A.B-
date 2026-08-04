"""The last step, and the only one that cannot be undone.

Everything upstream of here is reversible. A harvest can be recomputed, a slip reprinted, an
unsigned transaction thrown away. This module submits, and once the broker has the order
there is no version of this codebase that can take it back.

    PLACED       the order went in and we know it did
    UNRESOLVED   the request may have reached the broker. NOT a failure to place
    NOT_PLACED   deliberately: the mode says a person places, or the lane has no adapter
    REFUSED      a condition said no, and which one is named

## The position is recorded BEFORE the order is sent

That ordering looks wrong and is the only safe one. Placing first and recording second
leaves a window where the process dies between the two, and what is on the other side of
that window is a real position that nothing in this system knows about — invisible to the
breakers, invisible to `unsettled_exposure`, invisible until a statement arrives.

Recording first can leave the opposite: a position on file for an order the broker rejected.
That is a phantom, it is visible, and it is corrected in one command. Over-reporting your
exposure is the direction to fail in.

## UNKNOWN is the case this module is shaped around

A 5xx or a timeout means the request may or may not have reached the broker. The order may
exist. Resubmitting is how you fill twice, and `client_order_id` is derived from the intent
rather than the moment precisely so a retry collides instead of duplicating — but the right
move is not to retry at all. It is to record the position as `UNKNOWN` and stop.

That stop is automatic and needs nothing here: `lib.operating` drops a lane holding an
unresolved `UNKNOWN` to owner-operating, because a lane that does not know its own exposure
has no business opening more. It clears the moment somebody settles or voids the position,
which is a human act.

## Two lanes have no adapter, for two different reasons

**Arb**: bet365 and Sky Bet have no betting API. The slip is the deliverable and always was.
**Crypto**: `connectors/chain_exec` has no key path, no signing library and no send method.

Neither is a gap to be filled later. They are reported as `NOT_PLACED` with the reason, so a
reader never files a deliberate absence as an unfinished feature.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

PLACED = "PLACED"
UNRESOLVED = "UNRESOLVED"
NOT_PLACED = "NOT_PLACED"
REFUSED = "REFUSED"

#: Lanes with no execution adapter, and why. Neither is unfinished work.
NO_ADAPTER = {
    "arb": ("bookmakers have no betting API — bet365 and Sky Bet will not take an order "
            "from a program, and no amount of engineering changes that. The slip IS the "
            "deliverable; place it by hand from the printed order."),
    "crypto": ("this lane cannot sign. connectors/chain_exec has no key path, no signing "
               "library and no send method. Sign the steps in a wallet you control."),
}


@dataclass(frozen=True, slots=True)
class Placement:
    """What happened to one instruction, and what it obliges now."""

    lane: str
    status: str
    subject: str = ""
    position_id: str = ""
    client_order_id: str = ""
    filled_quantity: float = 0.0
    requested_quantity: float = 0.0
    reason: str = ""
    result: Any = None

    @property
    def needs_a_person(self) -> bool:
        return self.status in {UNRESOLVED, REFUSED}

    def describe(self) -> str:
        head = f"{self.status}  [{self.lane}]" + (f"  {self.subject}" if self.subject else "")
        if self.status == PLACED:
            short = (f"\n  {self.filled_quantity:g} of {self.requested_quantity:g} filled; "
                     f"the position is smaller than the one that was sized."
                     if 0 < self.filled_quantity < self.requested_quantity else "")
            return (f"{head}\n  MONEY HAS MOVED. Recorded as {self.position_id}, "
                    f"broker reference {self.client_order_id}.{short}\n"
                    f"  Settle it when it closes:  python positions.py --settle "
                    f"{self.position_id} --returned <amount>")
        if self.status == UNRESOLVED:
            return (f"{head}\n  {self.reason}\n"
                    f"  THE ORDER MAY EXIST. Recorded as {self.position_id} with status "
                    f"UNKNOWN. DO NOT RESUBMIT — query {self.client_order_id} at the "
                    f"broker and find out what actually happened.\n"
                    f"  This lane is now owner-operating until you resolve it, because a "
                    f"lane that does not know its own exposure has no business opening "
                    f"more. Settling or voiding the position clears it.")
        return f"{head}\n  {self.reason}"

    def to_dict(self) -> dict[str, Any]:
        """A placement a reader cannot mistake for a resolved one.

        `needs_a_person` is carried as a field rather than left for the reader to derive
        from the status, because UNRESOLVED is the one that costs money to misread: an
        order that MAY exist, which a caller treating "not PLACED" as "not placed" will
        happily submit a second time.

        `filled_quantity` is null unless something filled. Zero filled and unknown filled
        are the same number and different facts, and the second is UNRESOLVED.
        """

        return {
            "lane": self.lane,
            "status": self.status,
            "subject": self.subject or None,
            "position_id": self.position_id or None,
            "client_order_id": self.client_order_id or None,
            "filled_quantity": (self.filled_quantity if self.status == PLACED else None),
            "requested_quantity": self.requested_quantity or None,
            "reason": self.reason or None,
            "needs_a_person": self.needs_a_person,
        }


def place_harvest(
    harvest: Any,
    *,
    mode: Any,
    ledger: Any,
    broker: Any = None,
    thesis_declared_at: str = "",
) -> Placement:
    """Submit one READY instruction, if everything says it may be submitted.

    Ordered so that every cheap refusal happens before anything is written and long before
    anything is sent.
    """

    from lib.operating import AUTONOMOUS

    lane = getattr(harvest, "lane", "")
    subject = getattr(harvest, "subject", "")
    common = {"lane": lane, "subject": subject}

    if getattr(harvest, "status", "") != "READY":
        return Placement(status=NOT_PLACED, reason=(
            f"the harvest is {getattr(harvest, 'status', 'unknown')}, not READY. Only a "
            f"screened, un-vetoed, authorised and sized instruction is placeable."),
            **common)

    if lane in NO_ADAPTER:
        return Placement(status=NOT_PLACED, reason=NO_ADAPTER[lane], **common)

    if getattr(mode, "mode", "") != AUTONOMOUS:
        return Placement(status=NOT_PLACED, reason=(
            f"{getattr(mode, 'mode', 'the mode')} — {getattr(mode, 'reason', '')} The "
            f"instruction is sized and waiting; you place it."), **common)

    if not getattr(ledger, "readable", False):
        # Placing something that cannot be recorded is worse than not placing. An
        # unrecorded fill reaches no breaker, appears in no exposure, and is found when a
        # statement arrives.
        return Placement(status=REFUSED, reason=(
            f"the outcome ledger could not be read ({getattr(ledger, 'reason', '')}), so "
            f"this order could not be recorded. An order nobody can record is one no "
            f"breaker will ever see."), **common)

    instruction = getattr(harvest, "instruction", None)
    if instruction is None or broker is None:
        return Placement(status=REFUSED, reason=(
            "no instruction, or no broker configured for this lane. Nothing was sent."),
            **common)

    return _place_stock(harvest, instruction, mode=mode, ledger=ledger, broker=broker,
                        thesis_declared_at=thesis_declared_at, common=common)


def _place_stock(harvest, order, *, mode, ledger, broker, thesis_declared_at,
                 common) -> Placement:
    from connectors.alpaca import (
        FILLED,
        PART_FILLED,
        REJECTED,
        UNKNOWN,
        Instruction,
        instruction_id,
    )

    permission = getattr(harvest, "permission", None)
    client_order_id = instruction_id(
        order.ticker, order.side, float(order.shares), thesis_declared_at)

    try:
        instruction = Instruction(
            symbol=order.ticker, side=order.side, quantity=float(order.shares),
            permission=permission, client_order_id=client_order_id)
    except (ValueError, AttributeError, TypeError) as error:
        return Placement(status=REFUSED, client_order_id=client_order_id, reason=(
            f"the order could not be turned into a broker instruction: "
            f"{type(error).__name__}: {error}"), **common)

    # Recorded first. See the module docstring: the window between sending and recording is
    # where an untracked position lives, and a phantom on rejection is the cheaper failure.
    position = ledger.open_position(
        common["lane"], common["subject"] or order.ticker, float(order.cash),
        source="BROKER", note=f"submitted as {client_order_id}")
    ledger.save()

    result = broker.place(instruction)
    shared = dict(common, position_id=position.position_id,
                  client_order_id=client_order_id, result=result,
                  requested_quantity=float(order.shares))

    if result.status == UNKNOWN:
        ledger.mark_unknown(position.position_id, (
            f"the broker's answer could not be established: {result.reason}. The order may "
            f"exist under {client_order_id}."))
        ledger.save()
        return Placement(status=UNRESOLVED, reason=result.reason, **shared)

    if result.status in {FILLED, PART_FILLED}:
        filled = float(result.filled_quantity or 0.0)
        if 0 < filled < float(order.shares):
            # The position is smaller than the one that was sized. Recorded at what
            # actually went on, so unsettled_exposure is not overstated for the rest of
            # its life.
            ledger.amend_stake(position.position_id, filled * float(order.price), note=(
                f"part filled: {filled:g} of {order.shares:g}"))
            ledger.save()
        return Placement(status=PLACED, filled_quantity=filled, **shared)

    # REJECTED, CANCELLED, NOT_CONFIGURED — the broker decided, and nothing is at risk.
    ledger.void(position.position_id, note=(
        f"the broker did not accept it ({result.status}): {result.reason}. Nothing was "
        f"placed and nothing is at risk."))
    ledger.save()
    return Placement(status=NOT_PLACED, reason=(
        f"the broker returned {result.status}: {result.reason}"), **shared)


def describe_placements(placements) -> str:
    if not placements:
        return ""
    lines = ["PLACING"]
    lines += [f"  {p.describe()}" for p in placements]
    placed = [p for p in placements if p.status == PLACED]
    unresolved = [p for p in placements if p.status == UNRESOLVED]
    lines.append("")
    if placed:
        lines.append(f"  {len(placed)} order(s) went in. MONEY HAS MOVED.")
    if unresolved:
        lines.append(
            f"  {len(unresolved)} order(s) are UNRESOLVED and their lanes are now "
            f"owner-operating. Query them at the broker before anything else.")
    if not placed and not unresolved:
        lines.append("  Nothing was placed. Every instruction is waiting for you.")
    return "\n".join(lines)
