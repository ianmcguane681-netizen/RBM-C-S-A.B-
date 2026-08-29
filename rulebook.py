"""Record what a book's rules page says, and see what two books still disagree about.

    python rulebook.py                             what has been read, and what has not
    python rulebook.py --book "Smarkets"           one book's coverage, topic by topic
    python rulebook.py --compare "Smarkets" "William Hill"
    python rulebook.py --topics                    the questions worth reading a page for
    python rulebook.py --record examples/arb/rulebook.example.json

This is the evening's work the arb lane keeps asking for. Every candidate it finds reports
INDETERMINATE naming a pair of books whose settlement rules nobody has read, and this is
where the reading goes once it is done — once, per pair of books, per market type, not per
bet.

**Nothing here fetches a rules page.** A bookmaker's terms are prose with defined terms,
cross-references and per-competition exceptions, and a scraper that got 90% of it would be
producing rules that are wrong in a way nobody could see. You open the page, you copy the
clause, you paste it in. What this holds is the record that you did, when, and from which
URL — so that in six months the same clause can be checked against what the page says then.

**It will not tell you two differently-worded rules mean the same thing.** That judgement
is yours and it is recorded with your name on it, exactly as `check_arb.py` requires. What
this does is show the two clauses side by side, tell you which topics neither of you has
read, and refuse to let silence count as agreement.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from lib.rulebook import (
    COVERED,
    DIVERGENT,
    STALE_AFTER_DAYS,
    TOPICS,
    Clause,
    RulebookStore,
    TopicDeclaration,
)

STORE = Path("data/rulebooks.json")

TEMPLATE = {
    "clauses": [
        {
            "book": "Smarkets",
            "market_type": "soccer/h2h",
            "topic": "abandonment",
            "verbatim": "PASTE THE OPERATOR'S RULES TEXT HERE, WORD FOR WORD",
            "source_url": "https://help.smarkets.com/...",
            "read_by": "Your Name",
            "read_at": "2026-08-29",
        }
    ],
    "declarations": [
        {
            "book_a": "Smarkets",
            "book_b": "William Hill",
            "topic": "abandonment",
            "settle_alike": True,
            "declared_by": "Your Name",
            "reasoning": "WHY these two wordings settle the same way, in your own words",
            "declared_at": "2026-08-29",
            "scenarios_checked": [
                "abandoned at 70 minutes with the score 2-0, replayed within 48 hours"
            ],
        }
    ],
}


def describe_topics() -> str:
    lines = [
        f"The {len(TOPICS)} settlement questions worth reading a book's rules page for.",
        "A divergence on a precondition alone makes the position a bet rather than a lock.",
        "",
    ]
    for topic in TOPICS:
        gate = "  (precondition)" if topic.disqualifying else "  (worth knowing)"
        lines.append(f"{topic.key}{gate}")
        lines.append(f"    {topic.question}")
        lines.append(f"    {topic.why}")
        lines.append("")
    lines.append(
        f"A reading older than {STALE_AFTER_DAYS} days reports STALE rather than read. A "
        f"book revises its terms and tells nobody, so the age of the reading is the only "
        f"protection there is."
    )
    return "\n".join(lines)


def record(store: RulebookStore, path: Path) -> int:
    """Add clauses and declarations from a JSON file. Refuses the whole file on any error.

    All or nothing on purpose. Half a file applied leaves the operator unsure which half,
    and the cheapest way to find out is to re-read pages they have already read.
    """

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        print(f"{path} could not be read: {type(error).__name__}: {error}")
        return 2

    # Keys starting with an underscore are notes to the person filling the file in, and
    # the shipped example is full of them. Stripped rather than refused: an example that
    # cannot explain itself is an example nobody uses correctly.
    def fields(row: dict) -> dict:
        return {key: value for key, value in row.items() if not key.startswith("_")}

    try:
        clauses = [Clause(**fields(row)) for row in payload.get("clauses", ())]
        declarations = [
            TopicDeclaration(**{**fields(row),
                                "scenarios_checked": tuple(row.get("scenarios_checked", ()))})
            for row in payload.get("declarations", ())
        ]
    except (TypeError, ValueError) as error:
        print(f"REFUSED, and nothing was written: {error}")
        return 2

    if not clauses and not declarations:
        print(f"{path} holds no clauses and no declarations. Nothing was written.")
        return 2

    for clause in clauses:
        store.record(clause)
    for declaration in declarations:
        store.declare(declaration)
    store.save()
    print(f"Recorded {len(clauses)} clause(s) and {len(declarations)} declaration(s) "
          f"into {store.path}.")
    print(store.describe())
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--store", default=str(STORE), help="where the readings are kept")
    parser.add_argument("--market-type", default="soccer/h2h",
                        help="rules are filed per market type; soccer/h2h by default")
    parser.add_argument("--book", help="show one book's coverage, topic by topic")
    parser.add_argument("--compare", nargs=2, metavar=("BOOK_A", "BOOK_B"),
                        help="what these two books agree on, differ on, and have not read")
    parser.add_argument("--record", metavar="FILE",
                        help="add clauses and declarations from a JSON file")
    parser.add_argument("--template", action="store_true",
                        help="print a file to fill in and pass to --record")
    parser.add_argument("--topics", action="store_true",
                        help="the questions, and why each one is worth an evening")
    args = parser.parse_args(argv)

    if args.topics:
        print(describe_topics())
        return 0
    if args.template:
        print(json.dumps(TEMPLATE, indent=2))
        return 0

    store = RulebookStore.load(Path(args.store))
    if not store.readable:
        # Exit 2 rather than 1: nothing was examined. The same code `run.py --reap` uses
        # for a lane that did not look, and for the same reason — a scheduler must not read
        # this as a clean report.
        print(store.describe())
        return 2

    if args.record:
        return record(store, Path(args.record))

    if args.compare:
        comparison = store.compare(args.compare[0], args.compare[1], args.market_type)
        print(comparison.describe())
        return {COVERED: 0, DIVERGENT: 1}.get(comparison.verdict, 2)

    if args.book:
        print(store.rulebook(args.book, args.market_type).describe())
        return 0

    print(store.describe(args.market_type))
    books = store.books(args.market_type)
    if len(books) < 2:
        print("")
        print("Fewer than two books are recorded for this market type, so there is no "
              "pair to compare. The arb lane will report INDETERMINATE on every candidate "
              "until there is.")
        return 2
    print("")
    for index, first in enumerate(books):
        for second in books[index + 1:]:
            print(store.compare(first, second, args.market_type).describe())
            print("")
    return 0


if __name__ == "__main__":
    sys.exit(main())
