"""Should this be put in front of you at all — as a cascade, never a score.

    python screen.py examples/arb/match-odds.json
    python screen.py examples/arb/match-odds.json --acted    # record that you acted

The layer between "is this valid" and "should I act". It originates nothing and ranks
nothing: it can only refuse, or decline to conclude, or pass a candidate through with every
stage's answer attached.

Exit codes so a scheduler can act without parsing text:

    0   SURFACED       every stage evaluated, none refused
    1   INDETERMINATE  a stage could not be evaluated, so it does not surface
    2   REFUSED        a stage said no, and the output names which

The alternative to this was a weighted score out of a hundred. The position in
`examples/arb/match-odds.json` is why it is not: six of seven dimensions are good and the
seventh is fatal, so any sane weighting surfaces an unhedged single bet.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

from check_arb import load
from connectors.odds import KNOWN_SOURCES, scan
from lib.arb import evaluate
from lib.candidates import (
    INDETERMINATE,
    REFUSED,
    SURFACED,
    coverage_stage,
    freshness_stage,
    screen,
    seen_stage,
    settlement_stage,
    size_stage,
    cost_stage,
)
from lib.seen import SeenRegister, arb_identity

REGISTER = Path("data/seen-register.json")
FRESHNESS_LIMIT_SECONDS = 120.0


def _age(legs) -> float:
    """Seconds since the OLDEST leg was observed, or -1 if any leg has no timestamp.

    Oldest rather than newest: the position is only as fresh as its stalest side, and a
    leg with no timestamp makes the age unknown rather than zero.
    """

    stamps = []
    for leg in legs:
        raw = (leg.observed_at or "").replace("Z", "+00:00")
        try:
            stamps.append(datetime.fromisoformat(raw))
        except ValueError:
            return -1.0
    if not stamps:
        return -1.0
    return (datetime.now(timezone.utc) - min(stamps)).total_seconds()


def main(path: str, *, acted: bool) -> int:
    legs, target, market, equivalence = load(Path(path))
    finding = evaluate(legs, target_stake=target, equivalence=equivalence)
    coverage = scan(market, KNOWN_SOURCES)

    identity = arb_identity(market, [(leg.book, leg.selection) for leg in legs])
    register = SeenRegister.load(REGISTER)
    seen = register.check(identity)

    smallest = min((leg.max_stake for leg in legs), default=0.0)
    binding = min(legs, key=lambda leg: leg.max_stake).book if legs else ""
    wanted = target or smallest

    candidate = screen(market, [
        # Order is the author's: cheapest and most fatal first, so a position that cannot
        # settle is refused before anybody prices it.
        settlement_stage(finding.status, finding.reason),
        seen_stage(seen),
        size_stage(smallest, wanted, binding=binding),
        freshness_stage(_age(legs), FRESHNESS_LIMIT_SECONDS),
        # Commission is already inside the net odds the return was computed from. A
        # negative cost means it was not measured, which is INDETERMINATE, not free.
        cost_stage(finding.return_pct, 0.0 if finding.total_stake else -1.0),
        coverage_stage(len(coverage.answered), len(coverage.quotes)),
    ])

    print(candidate.describe())

    if acted:
        stamp = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        register.record_action(identity, stamp)
        register.save()
        print(f"\nRecorded as acted on at {stamp}. It will refuse next time.")
    elif register.readable:
        stamp = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        register.record(identity, stamp)
        register.save()

    return {SURFACED: 0, INDETERMINATE: 1, REFUSED: 2}[candidate.verdict]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(3)
    raise SystemExit(main(sys.argv[1], acted="--acted" in sys.argv))
