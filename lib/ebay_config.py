"""Turn the flipper lane's configuration into a listing source, or into an honest refusal.

The lane needs candidate items from somewhere, and `docs/flipper-design.md` is blunt about
what that somewhere can be. eBay is reachable with caveats. Amazon's PA-API is gated behind
an affiliate account with sales, which is gated behind having the thing you are trying to
start. **Facebook Marketplace and DoneDeal have no public API and scraping them is against
their terms — that is not a missing adapter and no scraper is to be written for either**,
exactly as bookmakers not taking a program's order is not a missing adapter for arb.

So v1 is eBay-to-eBay, or eBay comparables against a source typed in by hand — and the
second of those is what works today, while the sold-data question at the top of the design
document is still open.

`listings_from_config` returns a callable or `None`, and `None` is what makes the lane
report COULD_NOT_LOOK rather than "no deals today". That distinction is the reason this
file is separate from the reaper: the reaper must not know what an eBay key is, and the
refusal must not be a shrug.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Sequence

#: Items a person is watching, typed in by hand. The candidate source that works with no
#: credentials at all: a listing somebody found and pasted is exactly as real as one that
#: arrived over HTTP, and the lane's job is the arithmetic rather than the finding.
WATCHLIST = Path("data/flipper-watchlist.json")


def listings_from_config(
    settings: Any, *, directory: Path
) -> Callable[[], tuple[Sequence[Any], int, int]] | None:
    """A `look` source for the flipper, or None when nothing is configured.

    None rather than an empty callable, because an empty callable would make the lane
    report NOTHING_FOUND — "it looked properly and there was nothing" — when in fact it
    looked at nothing. The reaper turns None into COULD_NOT_LOOK, which is the honest
    reading and the one that does not read as a quiet market.
    """

    path = directory / WATCHLIST.name
    if not path.is_file():
        return None

    def read() -> tuple[Sequence[Any], int, int]:
        from lib.flipper import ItemKey
        from lib.flipper_reaper import Listing

        # A watchlist that will not parse RAISES, and the reaper turns that into
        # COULD_NOT_LOOK. Returning an empty list would say the shelf-worth of items
        # somebody typed in came back with nothing worth buying.
        rows = json.loads(path.read_text(encoding="utf-8"))

        listings: list[Listing] = []
        skipped = 0
        for row in rows:
            if str(row.get("_note", "")):
                continue
            try:
                listings.append(Listing(
                    key=ItemKey(
                        title=str(row["title"]), grade=str(row["grade"]),
                        grader=str(row["grader"]),
                        qualifiers=tuple(str(q) for q in row.get("qualifiers", ())),
                        cert=str(row.get("cert", ""))),
                    price=float(row["price"]),
                    currency=str(row.get("currency", "EUR")),
                    source=str(row.get("source", str(path))),
                    url=str(row.get("url", "")),
                    observed_at=str(row.get("observed_at", ""))))
            except (KeyError, TypeError, ValueError):
                # One unusable row is not a failed look, and it is not silently dropped
                # either: it comes out in the source count below, where a watchlist of
                # twenty rows reporting three examined is visible rather than inferred.
                skipped += 1

        return listings, len(rows), len(rows) - skipped

    return read


def template() -> list[dict]:
    """The shape of `data/flipper-watchlist.json`."""

    return [{
        "_note": ("One item somebody is selling. The grade and the grader are part of the "
                  "identity rather than modifiers on it: the same card raw and at PSA 10 "
                  "can differ by fifty times, so a comparable that does not match on both "
                  "is a different item with the same name."),
        "title": "Charizard Base Set Holo",
        "qualifiers": ["Base Set", "1999", "Unlimited"],
        "grade": "9",
        "grader": "PSA",
        "price": 240.0,
        "currency": "EUR",
        "source": "eBay",
        "url": "https://www.ebay.ie/itm/...",
        "observed_at": "2026-08-29",
    }]
