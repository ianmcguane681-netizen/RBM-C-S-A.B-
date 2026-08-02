"""Many books, one request — and the two things the feed cannot tell you.

The-Odds-API aggregates bookmaker prices across sports and regions in a single call, which
takes the arbitrage lane from nought configured sources to a real universe for the price of
a free key. It is by a distance the cheapest fix for the coverage gate, which is currently
the loudest defect in the lane: a scan reaching no source and reporting no arb has
established nothing, and AG-05 exists to say so.

**What it cannot do, and this is structural rather than a limitation to route around.**
A feed returns odds. A `Leg` in `lib/arb.py` refuses construction without a maximum stake
and a settlement rule quoted verbatim, and the feed carries neither:

    max_stake         odds are not liquidity
    settlement_rule   the aggregator does not carry each book's terms

So this connector yields `Quote`, never `Leg`. Discovery here, verification at the book.
The only position this board has examined had a *positive* margin net of commission and was
refused because one leg voided on abandonment while the other stood — the gate that caught
it reads prose the aggregator does not return.

**Latency is the empirical question and the docs will not answer it.** Aggregated prices
are polled, not streamed, and the lag between a book's true price and this feed is exactly
the window an arb lives in. Every quote therefore carries the feed's own `last_update` for
the book rather than the time of the request, so `screen.py`'s freshness stage measures the
real age instead of the age of the HTTP call.

No credential lives here. The key is read from a directory the operator controls and its
absence is `NOT_CONFIGURED` — a state, never an exception, so a scan can report which
sources were silent rather than appearing to have covered them.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

from connectors.odds import CONFIGURED, NOT_CONFIGURED, UNREACHABLE, BOOKMAKER, MarketQuote
from lib.arbfind import Quote
from lib.http_retry import TransientRetrievalError, retrying_urlopen

BASE = "https://api.the-odds-api.com/v4"

#: Head-to-head. Chosen as the default because it is the market whose outcome set is
#: unambiguous, which `find_arb` requires: totals and handicaps need a line as well as a
#: side, and a market whose outcomes are guessed is a market that looks complete when it
#: is not.
H2H = "h2h"

#: Regions whose books are reachable from Ireland. Named rather than defaulted to `us`,
#: because a scan of American books that reports no arb is answering a question nobody
#: asked while looking exactly like an answer to the one they did.
UK_IE_EU = "uk,eu"


@dataclass(frozen=True, slots=True)
class OddsApiCredentials:
    key: str

    @classmethod
    def load(cls, directory: str | Path = "~/.oddsapi") -> "OddsApiCredentials | None":
        root = Path(directory).expanduser()
        key = root / "key"
        if not key.is_file():
            return None
        value = key.read_text(encoding="utf-8").strip()
        return cls(value) if value else None


@dataclass(frozen=True, slots=True)
class Usage:
    """What the free tier has left. Recorded because running out reads as no arbs.

    The API returns remaining and used in response headers. A scan that failed because
    the quota was spent must not be reported as a scan that found nothing.
    """

    remaining: int = -1
    used: int = -1

    @property
    def is_known(self) -> bool:
        return self.remaining >= 0

    def describe(self) -> str:
        if not self.is_known:
            return "quota unknown (the response carried no usage headers)"
        return f"{self.remaining} request(s) remaining, {self.used} used"


class OddsApiSource:
    """One configured feed. Reports its own absence rather than raising."""

    name = "The Odds API"
    kind = BOOKMAKER

    def __init__(
        self,
        credentials: OddsApiCredentials | None,
        *,
        regions: str = UK_IE_EU,
        opener: Callable[..., Any] = retrying_urlopen,
    ) -> None:
        self.credentials = credentials
        self.regions = regions
        self._opener = opener
        self.usage = Usage()

    @classmethod
    def from_directory(
        cls, directory: str | Path = "~/.oddsapi", **kw: Any
    ) -> "OddsApiSource":
        return cls(OddsApiCredentials.load(directory), **kw)

    @property
    def is_configured(self) -> bool:
        return self.credentials is not None

    def _get(self, path: str, params: dict[str, str]) -> Any:
        assert self.credentials is not None
        query = urllib.parse.urlencode({**params, "apiKey": self.credentials.key})
        request = urllib.request.Request(f"{BASE}{path}?{query}")
        with self._opener(request) as response:
            payload = json.loads(response.read().decode("utf-8"))
            headers = getattr(response, "headers", None)
            if headers is not None:
                try:
                    self.usage = Usage(
                        int(headers.get("x-requests-remaining", -1)),
                        int(headers.get("x-requests-used", -1)),
                    )
                except (TypeError, ValueError):
                    self.usage = Usage()
        return payload

    def sports(self) -> tuple[str, ...]:
        """Sport keys currently in season. Free — this call does not spend quota."""

        if not self.is_configured:
            return ()
        return tuple(
            str(row["key"]) for row in self._get("/sports", {}) if row.get("active")
        )

    def quotes(self, sport: str, *, market: str = H2H) -> tuple[Quote, ...]:
        """Every book's price for every event in one sport.

        Each quote carries the FEED's `last_update` for that book, not the time of this
        request. The gap between them is the latency that decides whether a discovered
        candidate is still there, and stamping it with request time would hide exactly
        that.
        """

        if not self.is_configured:
            return ()

        payload = self._get(
            f"/sports/{sport}/odds",
            {"regions": self.regions, "markets": market, "oddsFormat": "decimal"},
        )

        out: list[Quote] = []
        for event in payload or []:
            title = self._event_title(event)
            for book in event.get("bookmakers") or []:
                book_name = str(book.get("title") or book.get("key") or "")
                observed = str(book.get("last_update") or "")
                for offered in book.get("markets") or []:
                    if offered.get("key") != market:
                        continue
                    stamp = str(offered.get("last_update") or observed)
                    for outcome in offered.get("outcomes") or []:
                        price = outcome.get("price")
                        name = str(outcome.get("name") or "")
                        if price is None or not name:
                            continue
                        try:
                            out.append(Quote(book_name, title, name, float(price), stamp))
                        except ValueError:
                            # Odds at or below 1.0 are not a price. Skipped rather than
                            # coerced, and the skip is invisible only because a missing
                            # selection surfaces as INCOMPLETE_BOOK downstream.
                            continue
        return tuple(out)

    @staticmethod
    def _event_title(event: dict) -> str:
        home, away = event.get("home_team"), event.get("away_team")
        stamp = str(event.get("commence_time") or "")
        if home and away:
            return f"{home} v {away} @ {stamp}"
        return f"{event.get('id', 'unknown event')} @ {stamp}"

    @staticmethod
    def outcomes_for(quotes: Sequence[Quote], market: str) -> tuple[str, ...]:
        """Every distinct selection any book quoted for a market.

        A weaker guarantee than it looks and the docstring says so: if NO book quoted the
        draw, the set is two-way and the market reads complete. `find_arb` takes the
        outcome set from the caller for that reason, and a caller using this should know it
        is reading the books' union rather than the sport's true outcome set.
        """

        return tuple(sorted({q.selection for q in quotes if q.market == market}))

    def quote(self, market: str) -> MarketQuote:
        """The `OddsSource` protocol member, so coverage reporting includes this feed."""

        if not self.is_configured:
            return MarketQuote(
                NOT_CONFIGURED, self.name, self.kind, market=market,
                reason="no key in ~/.oddsapi; free tier at the-odds-api.com",
            )
        try:
            found = [q for q in self.quotes(market.split("|")[0]) if q.market == market]
        except (TransientRetrievalError, OSError, ValueError) as error:
            return MarketQuote(
                UNREACHABLE, self.name, self.kind, market=market,
                reason=f"{type(error).__name__}: {error}"[:120],
            )
        if not found:
            return MarketQuote(
                CONFIGURED, self.name, self.kind, market=market,
                reason="reached, and this market was not among the events returned",
            )
        # NO legs, and this is the honest answer rather than a gap. A `Leg` requires a
        # maximum stake and a settlement rule; this feed carries neither, so it can report
        # that it covered the market and cannot report a bettable price. `legs=()` beside
        # CONFIGURED is precisely that distinction, and `stake_is_observed=False` says the
        # size behind these prices was never read.
        best = max(found, key=lambda q: q.net_odds)
        return MarketQuote(
            CONFIGURED, self.name, self.kind, market=market, legs=(),
            observed_at=best.observed_at, stake_is_observed=False,
            reason=(
                f"{len(found)} price(s) across {len({q.book for q in found})} book(s); "
                f"best {best.decimal_odds} on {best.selection} at {best.book}. These are "
                f"discovery quotes, not legs: no available stake and no settlement rule "
                f"was read, and both must be confirmed at the book before a position."
            ),
        )
