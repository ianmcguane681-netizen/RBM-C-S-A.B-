"""Kraken's public price history, and the honest size of it.

The one connector in this repository that needs no credential: Kraken serves OHLC candles
to anybody. That makes it the first evidence source the money side has ever had which can
be read on a fresh machine with nothing configured, and it is why the funded-account work
can move from estimated edges to measured ones.

## The cap is 720 candles, and it decides what may be concluded

Kraken returns at most 720 candles per request and `since` does not page backwards past
that — asking for a year of hourly bars returns the most recent thirty days, not an error.
So the available history is fixed by the interval:

    1h    720 bars     30 days
    4h    720 bars    120 days
    1d    720 bars    720 days, about two years

**This is a constraint on what can be claimed, not an inconvenience to engineer around.**
Thirty days of hourly bars cannot evidence an intraday strategy's edge, and a backtest that
reported one anyway would be the same defect this repository keeps finding: a number
computed from too little, presented as a finding. `NOT_ENOUGH_HISTORY` is a real answer and
`lib/backtest.py` refuses a verdict when it comes back.

Deeper intraday history would mean rebuilding candles from the Trades endpoint, which
paginates a thousand trades at a time — thousands of calls against a free public API for
one month of extra data. Not done, and recorded here so the next person does not rediscover
the option and assume it was overlooked.

## Three states, and the middle one is the point

    READ                 candles came back
    NOT_ENOUGH_HISTORY   fewer than asked for; the series is short, not absent
    COULD_NOT_LOOK       the request failed, or Kraken reported an error

An empty candle list with an error beside it is NOT a market with no trading. Kraken puts
its errors in a JSON array alongside a perfectly well-formed empty result, which is exactly
the shape that gets read as "nothing happened" by a client that only checks the status code.

## The cache is what makes a backtest reproducible

Candles are written to `data/kraken/` and read from there by default. A backtest whose
numbers move because it re-fetched is a backtest nobody can check, and the cache is also
what stops a parameter sweep from making four hundred requests to a free API. Delete the
directory to refetch; `--refresh` does the same thing deliberately.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Sequence

from lib.http_retry import retrying_urlopen

READ = "READ"
NOT_ENOUGH_HISTORY = "NOT_ENOUGH_HISTORY"
COULD_NOT_LOOK = "COULD_NOT_LOOK"

API = "https://api.kraken.com/0/public/OHLC"

#: Kraken's hard cap. Not configurable, and asking for more returns this many silently.
MAX_BARS = 720

#: Minutes per bar, by the name people use for it.
INTERVALS = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240, "1d": 1440,
             "1w": 10080}

DEFAULT_CACHE = Path("data/kraken")

#: Kraken asks for one request a second from anonymous clients. Being a good citizen of a
#: free API is also self-interest: the alternative to a polite delay is a ban.
POLITE_DELAY_SECONDS = 1.0


@dataclass(frozen=True, slots=True)
class Bar:
    """One candle. Times are UTC epoch seconds, as Kraken sends them."""

    ts: int
    open: float
    high: float
    low: float
    close: float
    volume: float

    @property
    def when(self) -> datetime:
        return datetime.fromtimestamp(self.ts, tz=timezone.utc)

    @property
    def is_sane(self) -> bool:
        """Does this candle describe a possible bar?

        A high below the open, or a low above the close, is a malformed record rather than
        a strange market. Backtests read highs and lows to decide whether a stop was hit,
        so one bad candle silently invents or destroys a trade.
        """

        return (
            self.high >= max(self.open, self.close)
            and self.low <= min(self.open, self.close)
            and self.low > 0
        )


@dataclass(frozen=True, slots=True)
class OhlcRead:
    """Candles, or the reason there are none."""

    status: str
    pair: str
    interval: str
    bars: tuple[Bar, ...] = ()
    detail: str = ""
    fetched_at: str = ""
    from_cache: bool = False

    @property
    def usable(self) -> bool:
        return self.status == READ

    @property
    def span_days(self) -> float:
        if len(self.bars) < 2:
            return 0.0
        return (self.bars[-1].ts - self.bars[0].ts) / 86400.0

    def describe(self) -> str:
        if self.status == COULD_NOT_LOOK:
            return (
                f"COULD_NOT_LOOK  {self.pair} {self.interval}: {self.detail}\n"
                f"  No conclusion about this market follows. This is a fact about the "
                f"request, not about the price."
            )
        if self.status == NOT_ENOUGH_HISTORY:
            return (
                f"NOT_ENOUGH_HISTORY  {self.pair} {self.interval}: "
                f"{len(self.bars)} bar(s), {self.detail}"
            )
        source = "cache" if self.from_cache else "Kraken"
        return (
            f"READ  {self.pair} {self.interval}: {len(self.bars)} bars covering "
            f"{self.span_days:.0f} days, from {source}"
        )


def _cache_path(cache_dir: Path, pair: str, interval: str) -> Path:
    return cache_dir / f"{pair}-{interval}.json"


def _parse(rows: Sequence, pair: str, interval: str) -> tuple[tuple[Bar, ...], str]:
    """Turn Kraken's array-of-arrays into bars, dropping the malformed with a count.

    Kraken sends numbers as strings. A row that will not parse is dropped rather than
    guessed at, and the count comes back so a series that is quietly half-missing cannot
    look like a clean read.
    """

    bars: list[Bar] = []
    dropped = 0
    for row in rows:
        try:
            bar = Bar(int(row[0]), float(row[1]), float(row[2]), float(row[3]),
                      float(row[4]), float(row[6]))
        except (TypeError, ValueError, IndexError):
            dropped += 1
            continue
        if not bar.is_sane:
            dropped += 1
            continue
        bars.append(bar)
    bars.sort(key=lambda b: b.ts)
    note = f"{dropped} malformed candle(s) dropped" if dropped else ""
    return tuple(bars), note


def read_ohlc(
    pair: str,
    interval: str = "1d",
    *,
    want_bars: int = MAX_BARS,
    cache_dir: Path | None = None,
    refresh: bool = False,
    opener: Callable = retrying_urlopen,
    sleep: Callable[[float], None] = time.sleep,
) -> OhlcRead:
    """Candles for one pair, from the cache unless told otherwise.

    `want_bars` above `MAX_BARS` is not an error and not silently satisfied: Kraken returns
    720 and the read comes back NOT_ENOUGH_HISTORY saying so, because a caller who asked
    for two thousand bars and got 720 has a different backtest than the one they wrote.
    """

    if interval not in INTERVALS:
        raise ValueError(
            f"unknown interval {interval!r}; Kraken serves {', '.join(INTERVALS)}"
        )
    cache_dir = cache_dir or DEFAULT_CACHE
    path = _cache_path(cache_dir, pair, interval)

    if not refresh and path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            bars, note = _parse(payload.get("rows", []), pair, interval)
            read = OhlcRead(
                READ, pair, interval, bars, note,
                payload.get("fetched_at", ""), from_cache=True,
            )
            if len(bars) < want_bars:
                return OhlcRead(
                    NOT_ENOUGH_HISTORY, pair, interval, bars,
                    f"cache holds {len(bars)}, {want_bars} asked for",
                    read.fetched_at, from_cache=True,
                )
            return read
        except (OSError, ValueError) as error:
            # A corrupt cache is not an absent market and not a reason to report zero bars.
            # Fall through and fetch; say so if the fetch also fails.
            cache_error = f"cache at {path} unreadable ({error})"
        else:  # pragma: no cover - defensive
            cache_error = ""
    else:
        cache_error = ""

    url = f"{API}?pair={pair}&interval={INTERVALS[interval]}"
    try:
        with opener(urllib.request.Request(url, headers={"User-Agent": "rbm-backtest"})) as response:
            payload = json.load(response)
    except (urllib.error.URLError, OSError, ValueError, TimeoutError) as error:
        detail = f"{type(error).__name__}: {error}"
        if cache_error:
            detail = f"{detail}; {cache_error}"
        return OhlcRead(COULD_NOT_LOOK, pair, interval, (), detail)

    # Kraken reports failure in a JSON array beside a well-formed empty result. A client
    # that only checks the HTTP status reads "no candles" and calls it a quiet market.
    errors = payload.get("error") or []
    if errors:
        return OhlcRead(
            COULD_NOT_LOOK, pair, interval, (),
            f"Kraken returned {'; '.join(str(e) for e in errors)}",
        )

    result = payload.get("result") or {}
    keys = [k for k in result if k != "last"]
    if not keys:
        return OhlcRead(
            COULD_NOT_LOOK, pair, interval, (),
            "Kraken returned no series for this pair. Check the pair name — an unknown "
            "pair is an error here, not an empty market.",
        )

    bars, note = _parse(result[keys[0]], pair, interval)
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"pair": pair, "kraken_pair": keys[0], "interval": interval,
                    "fetched_at": fetched_at, "rows": result[keys[0]]}),
        encoding="utf-8",
    )
    sleep(POLITE_DELAY_SECONDS)

    if len(bars) < want_bars:
        return OhlcRead(
            NOT_ENOUGH_HISTORY, pair, interval, bars,
            f"Kraken served {len(bars)}, {want_bars} asked for"
            + (f"; {note}" if note else "")
            + (f" (the cap is {MAX_BARS})" if want_bars > MAX_BARS else ""),
            fetched_at,
        )
    return OhlcRead(READ, pair, interval, bars, note, fetched_at)


def read_many(
    pairs: Sequence[str], interval: str = "1d", **kw
) -> dict[str, OhlcRead]:
    """Every pair asked for, including the ones that failed.

    Failures stay in the mapping rather than being filtered out. A universe that silently
    shrank from eight markets to five is a different study from the one that was
    commissioned, and the caller must be able to see that it happened.
    """

    return {pair: read_ohlc(pair, interval, **kw) for pair in pairs}


@dataclass(frozen=True, slots=True)
class DepthRead:
    """How much can be sold within a tolerated slippage, or why that is not known.

    `lib/sizing.py` treats an unmeasured constraint as INDETERMINATE rather than skipping
    it, because a constraint that silently drops out RAISES the permitted size. Exit depth
    is the one most often unavailable and the one that most deserves that treatment: it is
    the answer to "can I get out", and sizing past it is how a position becomes a holding.
    """

    status: str
    pair: str
    #: Quote-currency value available on the bid side within the tolerance.
    exitable_value: float = 0.0
    slippage_pct: float = 0.0
    mid: float = 0.0
    detail: str = ""

    @property
    def usable(self) -> bool:
        return self.status == READ


def read_depth(
    pair: str,
    *,
    slippage_pct: float = 0.5,
    count: int = 100,
    opener: Callable = retrying_urlopen,
) -> DepthRead:
    """Walk the bid side and total what could be sold inside `slippage_pct` of the mid.

    Never cached. A book from an hour ago is not a measurement of what can be sold now, and
    the whole point of this number is that it is current.
    """

    url = f"{API.replace('/OHLC', '/Depth')}?pair={pair}&count={count}"
    try:
        with opener(urllib.request.Request(
            url, headers={"User-Agent": "rbm-backtest"}
        )) as response:
            payload = json.load(response)
    except (urllib.error.URLError, OSError, ValueError, TimeoutError) as error:
        return DepthRead(COULD_NOT_LOOK, pair, detail=f"{type(error).__name__}: {error}")

    errors = payload.get("error") or []
    if errors:
        return DepthRead(COULD_NOT_LOOK, pair,
                         detail="; ".join(str(e) for e in errors))
    result = payload.get("result") or {}
    keys = [k for k in result if k != "last"]
    if not keys:
        return DepthRead(COULD_NOT_LOOK, pair, detail="Kraken returned no book")

    book = result[keys[0]]
    try:
        bids = [(float(p), float(v)) for p, v, *_ in book.get("bids", [])]
        asks = [(float(p), float(v)) for p, v, *_ in book.get("asks", [])]
    except (TypeError, ValueError) as error:
        return DepthRead(COULD_NOT_LOOK, pair, detail=f"unparseable book: {error}")
    if not bids or not asks:
        return DepthRead(COULD_NOT_LOOK, pair, detail="one side of the book was empty")

    mid = (bids[0][0] + asks[0][0]) / 2
    floor = mid * (1 - slippage_pct / 100.0)
    value = sum(price * volume for price, volume in bids if price >= floor)
    return DepthRead(READ, pair, value, slippage_pct, mid)


def write_receipt(reads: dict[str, OhlcRead], cache_dir: Path | None = None) -> Path:
    """Record what was fetched, beside a cache that is not committed.

    The same split the rest of `data/` uses: the bulk stays out of git, a receipt carrying
    counts and dates goes in. Price candles are not secret — the receipt is here because a
    backtest quoting a figure needs the reader to be able to check WHICH candles produced
    it, and a cache directory that is not in the repository cannot answer that on its own.

    Failed reads are recorded too. A universe that quietly shrank from ten markets to seven
    is a different study from the one that was commissioned.
    """

    cache_dir = cache_dir or DEFAULT_CACHE
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir.parent / "kraken.receipt.json"
    path.write_text(json.dumps({
        "written_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "markets": {
            pair: {
                "status": read.status,
                "interval": read.interval,
                "bars": len(read.bars),
                "span_days": round(read.span_days, 1),
                "first": read.bars[0].when.date().isoformat() if read.bars else None,
                "last": read.bars[-1].when.date().isoformat() if read.bars else None,
                "fetched_at": read.fetched_at,
                "detail": read.detail,
            }
            for pair, read in sorted(reads.items())
        },
    }, indent=2) + "\n", encoding="utf-8")
    return path
