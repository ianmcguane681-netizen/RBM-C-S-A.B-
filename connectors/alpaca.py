"""Place an order, and never report one as unplaced when it might have gone through.

The first execution adapter, and stocks first on purpose: paper mode exists, orders can be
cancelled before fill and sold after, and the worst failure is a bad order rather than a
drained wallet. The chain adapter holds private keys and comes last.

## The defect this module exists to avoid

Every other connector here reads. This one *writes*, and writing changes what an unread
answer means. If a read times out, nothing happened and the previous value stands. If a
SUBMIT times out, **the order may well have been placed** — the request reached the broker
and the response did not come back. Reporting that as "not placed" invites an immediate
retry, and the retry fills twice.

That is the repository's recurring defect at its most expensive: an unknown state read as
the flattering one, costing real money within seconds rather than eventually.

So:

    SUBMITTED     the broker acknowledged it
    FILLED        it executed, wholly
    PART_FILLED   it executed in part, and the remainder is stated
    CANCELLED     it was withdrawn before filling
    REJECTED      the broker refused it, with the reason
    UNKNOWN       the outcome could not be established. NOT "not placed".

`UNKNOWN` never permits a retry. Every order carries a `client_order_id` derived from the
instruction, so a resubmission of the same instruction is refused by the broker as a
duplicate rather than accepted as a second order. Idempotency is the only real defence and
it has to be at submission, not in a wrapper.

## What the adapter will not do

It places what it is handed and originates nothing. An instruction arrives already carrying
the `Permission` that authorised it, and the adapter refuses anything not `PERMITTED` —
including `INDETERMINATE`, which is not a weaker yes. That check is redundant with the
caller by design: the last thing before money moves should re-read the authorisation rather
than trust that somebody upstream did.

## Paper against live

Exactly one of `paper` or `live` must be declared in the credential directory, exactly as
Betfair's delayed and live keys are. The two base URLs differ by one word and the keys look
identical, and a live order placed believing it was paper is the failure that ends the
experiment.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from lib.http_retry import TransientRetrievalError, retrying_urlopen
from lib.thesis import PERMITTED, Permission

PAPER_BASE = "https://paper-api.alpaca.markets"
LIVE_BASE = "https://api.alpaca.markets"
DATA_BASE = "https://data.alpaca.markets"

#: The currency every price out of this venue is denominated in. Alpaca lists US equities
#: and quotes them in dollars; nothing here converts.
#:
#: Stated once, here, because it is a fact about the venue rather than a preference of a
#: caller. It used to be a default argument in two other modules, and on 2026-08-08 those
#: two defaults disagreed — see `lib.reaping.assemble_stocks`.
QUOTES_IN = "USD"

SUBMITTED = "SUBMITTED"
FILLED = "FILLED"
PART_FILLED = "PART_FILLED"
CANCELLED = "CANCELLED"
REJECTED = "REJECTED"
UNKNOWN = "UNKNOWN"

NOT_CONFIGURED = "NOT_CONFIGURED"

BUY = "buy"
SELL = "sell"

#: Alpaca's own order statuses, mapped. Anything unrecognised becomes UNKNOWN rather than
#: being guessed at, because a status this module does not know is a status it cannot
#: report on honestly.
_STATUS = {
    "new": SUBMITTED, "accepted": SUBMITTED, "pending_new": SUBMITTED,
    "accepted_for_bidding": SUBMITTED, "held": SUBMITTED,
    "filled": FILLED, "partially_filled": PART_FILLED,
    "canceled": CANCELLED, "expired": CANCELLED, "done_for_day": CANCELLED,
    "rejected": REJECTED, "suspended": REJECTED, "stopped": REJECTED,
}


@dataclass(frozen=True, slots=True)
class AlpacaCredentials:
    key_id: str
    secret_key: str
    paper: bool

    @property
    def base(self) -> str:
        return PAPER_BASE if self.paper else LIVE_BASE

    @classmethod
    def load(cls, directory: str | Path = "~/.alpaca") -> "AlpacaCredentials | None":
        """Exactly one of `paper` or `live`, or this refuses to load.

        A key gives no hint which environment it belongs to, and the base URLs differ by
        one word. Declaring it is the only way the distinction survives contact with a
        hurried afternoon.
        """

        root = Path(directory).expanduser()
        key_id, secret = root / "key_id", root / "secret_key"
        if not key_id.is_file() or not secret.is_file():
            return None

        paper_marker, live_marker = (root / "paper").is_file(), (root / "live").is_file()
        if paper_marker == live_marker:
            raise ValueError(
                f"{root} must contain exactly one of 'paper' or 'live'. A live order "
                f"placed believing it was paper is not a bug you find later."
            )
        return cls(
            key_id.read_text(encoding="utf-8").strip(),
            secret.read_text(encoding="utf-8").strip(),
            paper=paper_marker,
        )


@dataclass(frozen=True, slots=True)
class Quote:
    """A two-sided price WITH the size behind it, which is what makes it a price."""

    symbol: str
    bid: float
    bid_size: float
    ask: float
    ask_size: float
    observed_at: str

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2.0

    @property
    def spread_pct(self) -> float:
        return (self.ask - self.bid) / self.mid * 100.0 if self.mid else 0.0

    def executable_price(self, side: str) -> float:
        """What you actually pay or receive — never the mid.

        The mid is the number everyone quotes and nobody trades at. Sizing against it
        understates cost by half the spread on entry and again on exit.
        """

        return self.ask if side == BUY else self.bid


@dataclass(frozen=True, slots=True)
class MarketClock:
    """Whether the venue is open, and when it next changes.

    Exists so that "this price is 20 hours old" and "the market is shut" are answerable
    as different questions. On a Saturday the last quote of Friday genuinely IS the last
    price — it is not stale data, and reporting it as stale would send a reader looking
    for a broken feed. Neither is it tradeable.
    """

    is_open: bool
    at: str = ""
    next_open: str = ""
    next_close: str = ""


@dataclass(frozen=True, slots=True)
class Instruction:
    """A sized, authorised order. Carries the permission that allowed it."""

    symbol: str
    side: str
    quantity: float
    permission: Permission
    #: Stable across retries: the broker rejects a duplicate rather than filling twice.
    client_order_id: str

    def __post_init__(self) -> None:
        if self.side not in {BUY, SELL}:
            raise ValueError(f"side must be {BUY!r} or {SELL!r}, not {self.side!r}")
        if self.quantity <= 0:
            raise ValueError("quantity must be positive; direction is carried by side")
        if not self.client_order_id.strip():
            raise ValueError(
                "a client order id is required: without one a retry after an UNKNOWN "
                "outcome fills twice"
            )


@dataclass(frozen=True, slots=True)
class OrderResult:
    status: str
    symbol: str
    client_order_id: str
    broker_order_id: str = ""
    filled_quantity: float = 0.0
    requested_quantity: float = 0.0
    filled_avg_price: float = 0.0
    reason: str = ""

    @property
    def may_have_been_placed(self) -> bool:
        """True when a retry could double-fill. The question that matters after a timeout."""

        return self.status not in {REJECTED, CANCELLED}

    def describe(self) -> str:
        if self.status == UNKNOWN:
            return (
                f"UNKNOWN  {self.symbol} {self.requested_quantity:g}\n"
                f"  The outcome could not be established: {self.reason}\n"
                f"  This is NOT a report that the order was not placed. The request may "
                f"have reached the broker. DO NOT RESUBMIT — query "
                f"{self.client_order_id} and find out."
            )
        if self.status == REJECTED:
            return f"REJECTED  {self.symbol}: {self.reason}"
        if self.status == PART_FILLED:
            return (
                f"PART_FILLED  {self.symbol}: {self.filled_quantity:g} of "
                f"{self.requested_quantity:g} at {self.filled_avg_price:,.4f}. "
                f"{self.requested_quantity - self.filled_quantity:g} remains unfilled and "
                f"the position is smaller than the one that was sized."
            )
        if self.status == FILLED:
            return (f"FILLED  {self.symbol}: {self.filled_quantity:g} at "
                    f"{self.filled_avg_price:,.4f}")
        return f"{self.status}  {self.symbol} {self.requested_quantity:g}"


class AlpacaBroker:
    """Reads prices and places orders. Originates nothing."""

    name = "Alpaca"

    def __init__(
        self,
        credentials: AlpacaCredentials | None,
        *,
        opener: Callable[..., Any] = retrying_urlopen,
    ) -> None:
        self.credentials = credentials
        self._opener = opener

    @classmethod
    def from_directory(cls, directory: str | Path = "~/.alpaca", **kw: Any) -> "AlpacaBroker":
        try:
            return cls(AlpacaCredentials.load(directory), **kw)
        except ValueError:
            # An undeclared environment is NOT_CONFIGURED rather than an exception: a scan
            # should report it alongside the others instead of dying.
            return cls(None, **kw)

    @property
    def is_configured(self) -> bool:
        return self.credentials is not None

    @property
    def is_paper(self) -> bool | None:
        """None when unconfigured — deliberately not False, which would read as live."""

        return self.credentials.paper if self.credentials else None

    def _headers(self) -> dict[str, str]:
        assert self.credentials is not None
        return {
            "APCA-API-KEY-ID": self.credentials.key_id,
            "APCA-API-SECRET-KEY": self.credentials.secret_key,
            "Content-Type": "application/json",
        }

    def _call(self, url: str, *, method: str = "GET", body: dict | None = None) -> Any:
        payload = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(
            url, data=payload, headers=self._headers(), method=method
        )
        with self._opener(request) as response:
            raw = response.read().decode("utf-8")
        return json.loads(raw) if raw.strip() else {}

    # -- reading ---------------------------------------------------------------------

    def account(self) -> dict | None:
        """Balance and buying power. None when unconfigured, never a zero balance."""

        if not self.is_configured:
            return None
        return self._call(f"{self.credentials.base}/v2/account")

    def clock(self) -> "MarketClock | None":
        """Whether the venue is open, asked of the venue. None when it could not be asked.

        Asked rather than computed. A calendar in this repository would have to know US
        market holidays, half days and the occasional unscheduled close, and would be
        wrong silently on exactly the days it mattered. The broker already knows.

        `None` is the third state and callers must not read it as closed OR open: an
        unreachable clock means the question was not answered.
        """

        if not self.is_configured:
            return None
        try:
            payload = self._call(f"{self.credentials.base}/v2/clock") or {}
        except (urllib.error.URLError, TransientRetrievalError, ValueError, OSError):
            return None
        if "is_open" not in payload:
            return None
        return MarketClock(
            is_open=bool(payload["is_open"]),
            at=str(payload.get("timestamp", "")),
            next_open=str(payload.get("next_open", "")),
            next_close=str(payload.get("next_close", "")),
        )

    def quote(self, symbol: str) -> Quote | None:
        """Latest bid and ask WITH sizes. None when unconfigured or unquoted."""

        if not self.is_configured:
            return None
        payload = self._call(f"{DATA_BASE}/v2/stocks/{symbol}/quotes/latest")
        row = (payload or {}).get("quote") or {}
        bid, ask = float(row.get("bp") or 0.0), float(row.get("ap") or 0.0)
        if bid <= 0 or ask <= 0:
            # A one-sided or absent quote is not a price. Returning the side that exists
            # would let a caller size against a market with nothing on the other side.
            return None
        return Quote(
            symbol, bid, float(row.get("bs") or 0.0), ask, float(row.get("as") or 0.0),
            str(row.get("t") or ""),
        )

    def daily_closes(self, symbol: str, *, days: int = 30) -> tuple[float, ...] | None:
        """Recent daily closes, newest last. `None` when they could not be read.

        `None` rather than an empty tuple, and the difference is the point. `lib/sizing`
        turns unknown volatility into NOT_MEASURED and refuses to state a size at all,
        because skipping the volatility ceiling raises the permitted size exactly when
        nothing is known about how far the price moves. An empty tuple would compute a
        volatility of zero and sail past that.
        """

        if not self.is_configured:
            return None
        start = (datetime.now(timezone.utc) - timedelta(days=days * 2)).date().isoformat()
        try:
            payload = self._call(
                f"{DATA_BASE}/v2/stocks/{symbol}/bars"
                f"?timeframe=1Day&start={start}&limit={days}&adjustment=split"
            )
        except Exception:  # noqa: BLE001 - a failed read is not a flat market
            return None
        bars = (payload or {}).get("bars") or []
        closes = tuple(float(bar["c"]) for bar in bars if bar.get("c"))
        return closes or None

    def order_by_client_id(self, client_order_id: str) -> OrderResult:
        """What actually happened to an order. The answer after an UNKNOWN."""

        if not self.is_configured:
            return OrderResult(NOT_CONFIGURED, "", client_order_id,
                               reason="no credentials in ~/.alpaca")
        try:
            row = self._call(
                f"{self.credentials.base}/v2/orders:by_client_order_id"
                f"?client_order_id={client_order_id}"
            )
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return OrderResult(
                    CANCELLED, "", client_order_id,
                    reason="the broker has no order with this id, so it was never accepted",
                )
            return OrderResult(UNKNOWN, "", client_order_id, reason=f"HTTP {error.code}")
        except (TransientRetrievalError, OSError, ValueError) as error:
            return OrderResult(UNKNOWN, "", client_order_id,
                               reason=f"{type(error).__name__}: {error}"[:120])
        return self._to_result(row, client_order_id)

    # -- writing ---------------------------------------------------------------------

    def place(self, instruction: Instruction) -> OrderResult:
        """Submit, and refuse anything not positively permitted.

        The permission is re-read here rather than trusted from upstream. The last thing
        before money moves is exactly where a redundant check earns its place.
        """

        if instruction.permission.status != PERMITTED:
            return OrderResult(
                REJECTED, instruction.symbol, instruction.client_order_id,
                requested_quantity=instruction.quantity,
                reason=(
                    f"the attached permission is {instruction.permission.status}, not "
                    f"{PERMITTED}. INDETERMINATE is not a weaker yes and this adapter does "
                    f"not act on one."
                ),
            )
        if not self.is_configured:
            return OrderResult(
                NOT_CONFIGURED, instruction.symbol, instruction.client_order_id,
                requested_quantity=instruction.quantity,
                reason="no credentials in ~/.alpaca; nothing was sent",
            )

        body = {
            "symbol": instruction.symbol,
            "qty": str(instruction.quantity),
            "side": instruction.side,
            "type": "market",
            "time_in_force": "day",
            "client_order_id": instruction.client_order_id,
        }
        try:
            row = self._call(f"{self.credentials.base}/v2/orders", method="POST", body=body)
        except urllib.error.HTTPError as error:
            detail = ""
            try:
                detail = error.read().decode("utf-8")[:160]
            except Exception:  # noqa: BLE001 - the body is a courtesy, not a requirement
                pass
            if 400 <= error.code < 500:
                # A 4xx is the broker having decided. That is a refusal, not an unknown.
                return OrderResult(
                    REJECTED, instruction.symbol, instruction.client_order_id,
                    requested_quantity=instruction.quantity,
                    reason=f"HTTP {error.code}: {detail}",
                )
            return OrderResult(
                UNKNOWN, instruction.symbol, instruction.client_order_id,
                requested_quantity=instruction.quantity,
                reason=f"HTTP {error.code}: {detail}",
            )
        except (TransientRetrievalError, OSError, ValueError) as error:
            # The request may have reached the broker. This is the case the whole module
            # is shaped around.
            return OrderResult(
                UNKNOWN, instruction.symbol, instruction.client_order_id,
                requested_quantity=instruction.quantity,
                reason=f"{type(error).__name__}: {error}"[:120],
            )
        return self._to_result(row, instruction.client_order_id,
                               requested=instruction.quantity)

    def cancel(self, broker_order_id: str) -> bool:
        if not self.is_configured:
            return False
        try:
            self._call(f"{self.credentials.base}/v2/orders/{broker_order_id}",
                       method="DELETE")
            return True
        except (urllib.error.HTTPError, TransientRetrievalError, OSError, ValueError):
            return False

    @staticmethod
    def _to_result(row: dict, client_order_id: str, requested: float = 0.0) -> OrderResult:
        raw_status = str(row.get("status") or "").lower()
        status = _STATUS.get(raw_status, UNKNOWN)
        filled = float(row.get("filled_qty") or 0.0)
        asked = float(row.get("qty") or requested or 0.0)
        # Alpaca reports partially_filled explicitly, but a "filled" with a short quantity
        # would otherwise read as complete. Checked rather than trusted.
        if status == FILLED and 0 < filled < asked:
            status = PART_FILLED
        return OrderResult(
            status=status,
            symbol=str(row.get("symbol") or ""),
            client_order_id=str(row.get("client_order_id") or client_order_id),
            broker_order_id=str(row.get("id") or ""),
            filled_quantity=filled,
            requested_quantity=asked,
            filled_avg_price=float(row.get("filled_avg_price") or 0.0),
            reason="" if status != UNKNOWN else f"unrecognised broker status {raw_status!r}",
        )


def instruction_id(subject: str, side: str, quantity: float, thesis_declared_at: str) -> str:
    """A stable id for one intended trade.

    Derived from the intent rather than from the moment, so a retry after an UNKNOWN
    produces the SAME id and the broker rejects it as a duplicate. A timestamp here would
    make every retry a new order, which is the bug this is built to prevent.
    """

    import hashlib

    seed = f"{subject}|{side}|{quantity:.8f}|{thesis_declared_at}".encode("utf-8")
    return f"eb-{hashlib.sha256(seed).hexdigest()[:24]}"
