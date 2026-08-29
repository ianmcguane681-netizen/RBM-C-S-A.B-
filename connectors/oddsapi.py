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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

from connectors.odds import CONFIGURED, NOT_CONFIGURED, UNREACHABLE, BOOKMAKER, MarketQuote
from lib.arbfind import Quote
from lib.http_retry import TransientRetrievalError, retrying_urlopen

BASE = "https://api.the-odds-api.com/v4"


def market_type_for(sport: str, market: str) -> str:
    """The key a settlement rulebook is filed under, from the feed's sport and market keys.

    Sport rather than competition — `soccer_epl` and `soccer_efl_cup` both become `soccer`
    — because a book publishes one set of football rules and applies it across leagues. The
    exceptions are real (a competition-specific abandonment policy for a cup replay) and
    they are exceptions a person records in the clause wording, which is quoted verbatim
    and can say so. Keying per competition instead would multiply the reading job by the
    number of leagues scanned and guarantee that almost nothing was ever read.

    Empty in, empty out. An unknown sport must not become a rulebook key that looks real.
    """

    family = str(sport).split("_", 1)[0].strip()
    kind = str(market).strip()
    return f"{family}/{kind}" if family and kind else ""

#: Head-to-head. Chosen as the default because it is the market whose outcome set is
#: unambiguous, which `find_arb` requires: totals and handicaps need a line as well as a
#: side, and a market whose outcomes are guessed is a market that looks complete when it
#: is not.
H2H = "h2h"

#: Regions whose books are reachable from Ireland. Named rather than defaulted to `us`,
#: because a scan of American books that reports no arb is answering a question nobody
#: asked while looking exactly like an answer to the one they did.
UK_IE_EU = "uk,eu"

#: Where the last quota reading is kept, so a floor can mean something across processes.
#: Not a credential and not a subject — a count and a timestamp — but it lives under
#: `data/` with the rest of the operational state and is gitignored with it.
USAGE = Path("data/oddsapi-usage.json")

#: Stop spending here rather than at nought.
#:
#: The free tier is 500 requests a MONTH, and two scheduler lanes were asking every thirty
#: minutes at two and four credits a run — 288 a day, the whole allowance in under two
#: days. The failure that produces is the one this module's own docstring warns about: an
#: exhausted key errors, the lane reports no arb, and a spent account is indistinguishable
#: from a quiet market.
#:
#: The floor is not nought because the last credits are worth more than the ones before
#: them. They are what lets a person run one scan deliberately, by hand, on a fixture they
#: actually care about, after the cadence has been stopped.
MINIMUM_REMAINING = 25

#: Distinguishes "caller said nothing" from "caller said None", where None means do
#: not persist at all. A plain `= USAGE` default binds the path at import, which made
#: the constant unpatchable and sent test writes into the live `data/`.
_DEFAULT = object()


#: A free tier, in requests per month. Named so the burn-rate estimate has something to be
#: a fraction OF, and so the number appears once rather than in four comments.
FREE_TIER_MONTHLY = 500


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def credits_per_day(
    *,
    sports: int,
    cadence_seconds: float,
    bookmakers: Sequence[str] = (),
    regions: str = UK_IE_EU,
    markets: int = 1,
) -> float:
    """What a lane will spend a day at these settings. Arithmetic, not a forecast.

    The API charges one credit per market per region, and counts up to ten named books as
    a single region — so the bookmakers filter is a halving, and a second sport is a
    doubling. Both are easy to change without noticing what they cost, which is how a
    month's allowance goes in two days.

    This exists so the cost is stated BEFORE a key is placed rather than discovered from a
    lane that has quietly stopped finding anything. `preflight` prints it, and it reads the
    config in front of it rather than trusting a comment written when the defaults were
    different.
    """

    if cadence_seconds <= 0:
        raise ValueError("a cadence of nought would spend the allowance immediately")
    per_request = markets * (1 if bookmakers else len([
        part for part in regions.split(",") if part.strip()
    ]))
    return (86_400 / cadence_seconds) * max(sports, 0) * per_request


def describe_burn(daily: float, *, budget_monthly: int = FREE_TIER_MONTHLY) -> str:
    """The estimate beside the allowance, saying plainly which side of it this falls."""

    budget_daily = budget_monthly / 30.4
    verdict = "fits" if daily <= budget_daily else "OVERSPENDS"
    days = f"{budget_monthly / daily:.1f}" if daily > 0 else "unlimited"
    return (f"{daily:.1f} credit(s)/day against {budget_daily:.1f} on a "
            f"{budget_monthly}/month tier — {verdict}; the allowance lasts {days} day(s)")


class QuotaFloorReached(RuntimeError):
    """Raised instead of spending the reserve. Becomes COULD_NOT_LOOK, never NOTHING_FOUND.

    A `RuntimeError` rather than a returned empty list, because every caller in this
    repository already turns an exception from `look()` into COULD_NOT_LOOK, and an empty
    list into "scanned, found nothing". Getting that backwards here would report a lane
    that refused to spend as a lane that looked and saw a quiet market.
    """


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
    #: What the last call actually cost. The price is per region and per market rather
    #: than per request, so a widened scan spends faster than it looks and this is the
    #: only figure that says by how much.
    last: int = -1

    @property
    def is_known(self) -> bool:
        return self.remaining >= 0

    def describe(self) -> str:
        if not self.is_known:
            return "quota unknown (the response carried no usage headers)"
        return f"{self.remaining} request(s) remaining, {self.used} used"

    def save(self, path: Path | None) -> None:
        """Carry the reading to the next process. Best effort, and never fatal.

        Each `run.py --reap arb` is a fresh process, so an in-memory count protects one
        run and nothing else — and the lane runs on a cadence, which is precisely the
        shape that empties a monthly allowance. Persisting is what makes the floor mean
        anything across the day.

        A write that fails is swallowed: the quota reading is a guard, and a guard that
        takes the scan down with it when its own bookkeeping file is read-only has done
        more damage than the thing it was guarding against.
        """

        if path is None or not self.is_known:
            return
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({
                "remaining": self.remaining, "used": self.used, "last": self.last,
                "recorded_at": _now(),
            }, indent=2) + "\n", encoding="utf-8")
        except OSError:
            pass

    @classmethod
    def load(cls, path: Path | None) -> "Usage":
        """The last reading, or UNKNOWN. An absent file has never been measured.

        Unknown deliberately does NOT block: never having looked is not the same as
        having looked and found the tier spent, and refusing to spend a credit we have no
        evidence is gone would make a missing file indistinguishable from an empty
        account. One request then teaches us, and the floor applies from there.
        """

        if path is None or not path.is_file():
            return cls()
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
            return cls(int(row.get("remaining", -1)), int(row.get("used", -1)),
                       int(row.get("last", -1)))
        except (OSError, ValueError, TypeError):
            return cls()

    def to_dict(self) -> dict[str, Any]:
        """Quota with the unknown kept as null rather than the sentinel.

        `-1` was going straight into `scan_arb.py --json` as `quota_remaining`, where a
        reader renders it as a number and a dashboard shows minus one request remaining.
        The sentinel is fine inside a comparison and is not a value to publish: an
        unmeasured quota is UNKNOWN, and a lane that stopped because it ran out must not
        be told apart from one that found nothing by guessing at this field.
        """

        return {
            "status": "KNOWN" if self.is_known else "UNKNOWN",
            "remaining": self.remaining if self.is_known else None,
            "used": self.used if self.used >= 0 else None,
            "last_request_cost": self.last if self.last >= 0 else None,
        }


class OddsApiSource:
    """One configured feed. Reports its own absence rather than raising."""

    name = "The Odds API"
    kind = BOOKMAKER

    def __init__(
        self,
        credentials: OddsApiCredentials | None,
        *,
        regions: str = UK_IE_EU,
        bookmakers: Sequence[str] = (),
        minimum_remaining: int = MINIMUM_REMAINING,
        usage_path: Any = _DEFAULT,
        opener: Callable[..., Any] = retrying_urlopen,
    ) -> None:
        """`bookmakers` narrows the request itself; empty keeps the whole region.

        Quota is charged per region, and up to ten named books cost what one region does.
        So asking for five books instead of `uk,eu` halves the price of every scan, which
        matters on a free tier of 500 against a lane on a thirty-minute cadence.

        **It defaults to empty deliberately, and that is the whole design of this
        argument.** A filter is the operator narrowing what they looked at, and a narrowed
        scan that finds no arb looks exactly like a wide scan that found no arb. If a
        provider key is wrong, retired, or simply not carried in this region, the feed
        answers 200 with those books absent — no error anywhere — and the lane reports a
        quiet market. Defaulting to a hard-coded list would apply that risk to every
        caller who never asked for it, so the narrowing is a written choice in
        `data/reapers.json` and `scan_arb --json` reports the books requested beside the
        books seen so the two can be compared.
        """

        self.credentials = credentials
        self.regions = regions
        self.bookmakers = tuple(dict.fromkeys(
            str(book).strip() for book in bookmakers if str(book).strip()
        ))
        if len(self.bookmakers) > 10:
            raise ValueError(
                f"{len(self.bookmakers)} bookmakers requested; the API prices each ten as "
                f"one region, so an eleventh silently doubles the cost of every scan. "
                f"Split a wider universe into a second deliberate request, or drop to a "
                f"region and pay for it knowingly"
            )
        self._opener = opener
        self.minimum_remaining = int(minimum_remaining)
        # Resolved here so USAGE is read at call time rather than bound at import.
        chosen = USAGE if usage_path is _DEFAULT else usage_path
        self.usage_path = Path(chosen) if chosen is not None else None
        self.usage = Usage.load(self.usage_path)

    @classmethod
    def from_directory(
        cls, directory: str | Path = "~/.oddsapi", **kw: Any
    ) -> "OddsApiSource":
        return cls(OddsApiCredentials.load(directory), **kw)

    @property
    def is_configured(self) -> bool:
        return self.credentials is not None

    def _spendable(self) -> None:
        """Refuse before the request, not after. Raises `QuotaFloorReached`.

        Checked here rather than in the lane because this is the only place a credit is
        actually spent, and a guard that sits one level up is a guard somebody bypasses by
        calling the connector directly.
        """

        if self.usage.is_known and self.usage.remaining <= self.minimum_remaining:
            raise QuotaFloorReached(
                f"{self.usage.remaining} request(s) remain on the odds key and the floor "
                f"is {self.minimum_remaining}. NOTHING WAS SCANNED, and this is not a "
                f"report that no arb exists. Lengthen the cadence in run.py or cut the "
                f"sports list, then clear {self.usage_path} to resume; the reserve is "
                f"there so a scan you run deliberately still works."
            )

    def _get(self, path: str, params: dict[str, str]) -> Any:
        assert self.credentials is not None
        self._spendable()
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
                        int(headers.get("x-requests-last", -1)),
                    )
                except (TypeError, ValueError):
                    self.usage = Usage()
                # Recorded even when the reading is the one that will stop the next run.
                # Especially then.
                self.usage.save(self.usage_path)
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

        # `bookmakers` REPLACES `regions` rather than filtering within it; sending both
        # is what the API rejects. Filtering afterwards would be free of this risk and
        # would also be free of the saving: the quota is spent when the request is made.
        scope = ({"bookmakers": ",".join(self.bookmakers)} if self.bookmakers
                 else {"regions": self.regions})
        payload = self._get(
            f"/sports/{sport}/odds",
            {**scope, "markets": market, "oddsFormat": "decimal"},
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
                            out.append(Quote(book_name, title, name, float(price), stamp,
                                             market_type=market_type_for(sport, market)))
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
