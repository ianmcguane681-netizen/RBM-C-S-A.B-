"""Record what you placed and what came back, and hand it to the breakers.

    python positions.py                                   what is open, stale first
    python positions.py --placed arb "Arsenal v Chelsea" --staked 499.98
    python positions.py --settle POS-abc123 --returned 541.08
    python positions.py --void POS-abc123 --note "abandoned; both books voided"
    python positions.py --unknown POS-abc123 --note "bet365 restricted the account"
    python positions.py --apply                           feed settled outcomes to breakers
    python positions.py --json                            any of the above, for a UI

**Typing this in is the honest interface, not a shortcoming.** bet365 and Sky Bet have no
settlement API and never will, so the alternative to a person entering the result is not an
automatic one — it is a circuit breaker that reads zero forever and permits the fifth
losing position as cheerfully as the first. That was the state of this repository until
`lib/outcomes.py` was written.

The lanes that DO have an API — Alpaca fills, chain receipts — will populate the same ledger
from `source=BROKER` and `source=CHAIN` when the execution wire is built. The ledger already
records which, because "I typed it in" and "the broker said so" are different levels of
confidence and flattening them would lose the only thing that distinguishes them.

Exit codes, and they are the same whether the output is prose or `--json`. A caller that
switched rendering and started seeing 0 where it saw 2 would have been told the ledger was
fine by the act of asking for machine-readable output.

    0   nothing needs a person
    1   positions are awaiting settlement, or a breaker tripped while applying
    2   the ledger or the reaper config could not be read
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from lib.outcomes import (
    BROKER,
    CHAIN,
    LEDGER,
    MANUAL,
    OutcomeLedger,
    describe_ledger,
)
from lib.reaping import (
    CONFIG,
    KILL_SWITCH,
    THESES,
    apply_outcomes,
    assemble,
    load_config,
)
from lib.ui_contract import SCHEMA_VERSION

SOURCES = (MANUAL, BROKER, CHAIN)


def _emit(payload: dict) -> None:
    print(json.dumps({"schema_version": SCHEMA_VERSION, **payload}, indent=2))


def _refuse(reason: str, *, as_json: bool, prose: Sequence[str]) -> int:
    """One refusal, rendered either way, so the two cannot drift into different rules."""

    if as_json:
        _emit({"status": "REFUSED", "reason": reason, "position": None})
    else:
        for line in prose:
            print(line)
    return 2


def _ledger(path: Path, *, as_json: bool = False) -> tuple[OutcomeLedger | None, int]:
    book = OutcomeLedger(path)
    if not book.readable:
        if as_json:
            _emit({"status": "UNREADABLE", "reason": book.reason, "position": None})
            return None, 2
        print(f"REFUSING TO WRITE  the outcome ledger at {path} could not be read "
              f"({book.reason}).")
        print("  Overwriting it would erase positions that are still holding money and "
              "un-trip any breaker they had tripped.")
        print(f"  Fix or move {path}, then run this again.")
        return None, 2
    return book, 0


def show(path: Path, *, as_json: bool = False) -> int:
    """What is open, and the exit code decided once for both renderings.

    The JSON status describes the LEDGER — READABLE, UNREADABLE, or NOT_CONFIGURED when
    the file does not exist yet — and never the money, because "no positions" and "no
    ledger" produce the same empty list and mean opposite things. The counts live in
    their own fields and are `null`, not `0`, unless the file exists AND parsed.

    **A ledger that does not exist yet is the case worth spelling out**, because an
    absent file loads as a readable book with no positions and every count derived from
    it comes out zero. Nought at risk is then a confident answer assembled out of a
    missing file, and it is the same answer the ledger gives when everything really has
    settled. `money_state()` in `status.py` draws the line in the same place.
    """

    book = OutcomeLedger(path)
    known = path.is_file() and book.readable
    live = book.live() if known else ()
    pending = book.pending_application() if known else ()

    if not book.readable:
        code = 2
    elif live:
        code = 1
    else:
        code = 1 if pending else 0

    if as_json:
        _emit({
            "status": ("NOT_CONFIGURED" if not path.is_file() else
                       "READABLE" if book.readable else "UNREADABLE"),
            "reason": book.reason or None,
            "open": len(live) if known else None,
            "unsettled_exposure": book.unsettled_exposure() if known else None,
            "stale_open": len(book.stale_open()) if known else None,
            "pending_application": len(pending) if known else None,
            "positions": ([item.to_dict() for item in book.positions]
                          if known else None),
        })
        return code

    print(describe_ledger(book))
    if code == 1 and live:
        print()
        print("Settle them as they land:  python positions.py --settle <id> --returned <n>")
    return code


def placed(path: Path, lane: str, subject: str, staked: float, source: str, *,
           as_json: bool = False) -> int:
    book, code = _ledger(path, as_json=as_json)
    if book is None:
        return code
    position = book.open_position(lane, subject, staked, source=source)
    book.save()
    if as_json:
        _emit({"status": position.status, "position": position.to_dict()})
        return 1
    print(position.describe())
    print()
    print(f"  Settle it with:  python positions.py --settle {position.position_id} "
          f"--returned <amount>")
    return 1


def resolve(path: Path, action: str, identifier: str, *,
            returned: float | None = None, note: str = "", source: str = MANUAL,
            as_json: bool = False) -> int:
    book, code = _ledger(path, as_json=as_json)
    if book is None:
        return code

    if action == "settle":
        if returned is None:
            return _refuse(
                "--settle needs --returned; no amount was assumed",
                as_json=as_json,
                prose=("--settle needs --returned. A settlement with no amount is not a "
                       "settlement, and guessing zero would record a total loss.",),
            )
        position = book.settle(identifier, returned, source=source, note=note)
    elif action == "void":
        position = book.void(identifier, note=note)
    else:
        position = book.mark_unknown(identifier, note)

    book.save()
    if as_json:
        _emit({"status": position.status, "position": position.to_dict(),
               "applied_to_breakers": position.applied_to_breakers})
        return 1
    print(position.describe())
    print()
    print("  Not yet counted by any breaker. Apply it with:  python positions.py --apply")
    return 1


def apply(path: Path, config_path: Path, *, as_json: bool = False) -> int:
    """Every configured lane's breakers, told what settled since the last time.

    Assembles the lanes exactly as `run.py --reap` does rather than building breakers
    directly, so a lane this command counts is a lane that command would run — two
    different notions of "configured" would eventually disagree, and the disagreement
    would be invisible.

    The breaker files, the kill switch and the thesis register are taken from the LEDGER'S
    directory rather than from the module defaults. Otherwise `--ledger` would move one
    file and leave the other four pointing at the live `data/`, so a command aimed at a
    copy would trip the real breakers — which is exactly what the first version did, and
    what its test caught.
    """

    directory = path.parent
    kill_switch = directory / KILL_SWITCH.name
    theses_path = directory / THESES.name

    config, unreadable = load_config(config_path)
    if unreadable:
        if as_json:
            _emit({"status": "UNREADABLE", "reason": unreadable, "applications": None})
            return 2
        print(f"REFUSING TO APPLY  {config_path} could not be read ({unreadable}).")
        print("  Applying anyway would treat every lane as unconfigured, and its losses "
              "would reach nothing while this printed a tidy summary.")
        return 2

    book = OutcomeLedger(path)
    assemblies = assemble(config, directory=directory, kill_switch=kill_switch,
                          theses_path=theses_path)
    applications = apply_outcomes(assemblies, book)

    if not applications:
        if as_json:
            # NOT_CONFIGURED, never an empty success. No lane received these outcomes, so
            # a reader showing "applied: 0" beside a green tick would be showing the
            # breakers as up to date with losses that reached nothing at all.
            _emit({"status": "NOT_CONFIGURED", "applications": None,
                   "reason": "no configured lane has breakers to receive outcomes"})
            return 2
        print("No lane is configured and nothing was applied. Any settled outcome on file "
              "is reaching no breaker at all.")
        return 2

    tripped = False
    for application in applications:
        if not as_json:
            print(application.describe())
            print()
        tripped = tripped or bool(application.tripped_by)

    if as_json:
        _emit({
            "status": ("UNREADABLE" if not book.readable else
                       "TRIPPED" if tripped else "APPLIED"),
            "reason": book.reason or None,
            "applications": [item.to_dict() for item in applications],
            "self_clears": False,
        })
        return 2 if not book.readable else 1 if (tripped or book.live()) else 0

    if not book.readable:
        return 2
    if tripped:
        print("A breaker tripped. It does not reset itself — clearing it is a human act "
              "and is recorded with a reason.")
    return 1 if (tripped or book.live()) else 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--placed", nargs=2, metavar=("LANE", "SUBJECT"))
    parser.add_argument("--staked", type=float)
    parser.add_argument("--settle", metavar="POSITION_ID")
    parser.add_argument("--returned", type=float)
    parser.add_argument("--void", metavar="POSITION_ID")
    parser.add_argument("--unknown", metavar="POSITION_ID")
    parser.add_argument("--note", default="")
    parser.add_argument("--source", choices=SOURCES, default=MANUAL)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--ledger", default=str(LEDGER))
    parser.add_argument("--config", default=str(CONFIG))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    path = Path(args.ledger)

    if args.apply:
        return apply(path, Path(args.config), as_json=args.json)
    if args.placed:
        if args.staked is None or args.staked <= 0:
            return _refuse(
                "--placed needs a positive --staked",
                as_json=args.json,
                prose=("--placed needs a positive --staked. A position with no stake is "
                       "not a position, and it would tell the breakers nothing was at "
                       "risk.",),
            )
        return placed(path, args.placed[0], args.placed[1], args.staked, args.source,
                      as_json=args.json)
    if args.settle:
        return resolve(path, "settle", args.settle, returned=args.returned,
                       note=args.note, source=args.source, as_json=args.json)
    if args.void:
        return resolve(path, "void", args.void, note=args.note, as_json=args.json)
    if args.unknown:
        if not args.note.strip():
            return _refuse(
                "--unknown needs a --note naming what has to be chased",
                as_json=args.json,
                prose=("--unknown needs a --note. An UNKNOWN without a stated reason is "
                       "indistinguishable from neglect, and it is holding the breakers "
                       "short of the full picture until somebody chases it.",),
            )
        return resolve(path, "unknown", args.unknown, note=args.note, as_json=args.json)
    return show(path, as_json=args.json)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        raise SystemExit(0)
    try:
        raise SystemExit(main(argv))
    except (ValueError, RuntimeError) as error:
        print(f"REFUSED  {error}")
        raise SystemExit(2) from error
