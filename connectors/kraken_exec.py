"""Sending an order to Kraken, and the four ways that can go.

The counterpart to `connectors/kraken.py`, which only reads. This one can move money, so
almost all of it is about the cases where it must not.

    VALIDATED       Kraken checked the order and, by request, did NOT place it
    FILLED          it went on
    REJECTED        Kraken decided against it. Nothing is at risk
    UNKNOWN         the answer could not be established. The order MAY exist
    NOT_CONFIGURED  no credentials. Nothing was sent and nothing was attempted

## This is the SPOT API, and the funded account is not on it

`api.kraken.com` serves Kraken's spot exchange. Kraken Pro perpetual futures — which is
what the funded programme is reported to run on — is a different host, a different API and
a different auth scheme at `futures.kraken.com`. **None of it is implemented here.** A
funded-account order cannot be sent by this module and would not be accepted by this host.

That is stated rather than left to be discovered, because the two are close enough that
somebody will assume one adapter covers both, and the way they would find out is an order
for the wrong instrument on the wrong account.

## An entry without an exit is refused

`Instruction` requires a stop price and will not construct without one. Kraken attaches it
to the entry as a conditional close, so the stop is submitted in the same request as the
order it protects — not as a second call that can fail on its own, leaving a position with
nothing underneath it.

The alternative, placing an entry now and a stop a moment later, has a window in it, and
the window is the whole risk of the position. This repository already records positions
before sending for the same class of reason.

## The nonce is a shared, monotonic secret and it is a real trap

Every private Kraken call carries a nonce that must exceed every nonce used before it on
that key. Two processes on one key interleave and the lower one is rejected — and a
rejected nonce comes back looking exactly like a rejected order. Somebody reading "invalid
nonce" as "Kraken did not want this trade" would be wrong in the most expensive direction,
so `_next_nonce` persists the last value beside the credentials and always exceeds it, and
a nonce error is reported as its own thing rather than as a refusal.

## Kraken has no client-order-id de-duplication, so a retry can fill twice

Alpaca rejects a duplicate `client_order_id`, which is what makes retrying safe there. On
Kraken `userref` is a label and nothing more: send the same order twice and you own it
twice.

So this adapter never retries a submit. On UNKNOWN it stops and `resolve()` exists to ask
Kraken what actually happened, by the same `userref` the order carried. That is the only
correct move, and it is the reason `userref` is derived from the intent rather than from
the moment.

## Errors arrive with HTTP 200

Kraken reports failure in a JSON `error` array beside a well-formed result, the same shape
the OHLC reader has to defend against. A client checking only the status code reads a
refusal as a success — and here that would mean recording a fill that never happened.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from lib.http_retry import retrying_urlopen

VALIDATED = "VALIDATED"
FILLED = "FILLED"
PART_FILLED = "PART_FILLED"
SUBMITTED = "SUBMITTED"
CANCELLED = "CANCELLED"
REJECTED = "REJECTED"
UNKNOWN = "UNKNOWN"
NOT_CONFIGURED = "NOT_CONFIGURED"

BUY = "buy"
SELL = "sell"

API = "https://api.kraken.com"
VENUE = "Kraken spot"

#: Where the key lives. Never in this repository, never pasted into a chat.
DEFAULT_CREDENTIALS_DIR = "~/.kraken"

#: Kraken's own errors that mean "your clock or your counter", not "your order".
NONCE_ERRORS = ("EAPI:Invalid nonce",)


class NonceRegression(RuntimeError):
    """The nonce counter went backwards, which means another process shares this key.

    Its own exception because the alternative is reporting it as a rejected order, and a
    caller that reads "rejected" will reasonably try again with a fresh order.
    """


@dataclass(frozen=True, slots=True)
class KrakenCredentials:
    """An API key pair, read from a directory nobody else can read."""

    key: str
    secret: str
    directory: Path

    @classmethod
    def load(cls, directory: str | Path = DEFAULT_CREDENTIALS_DIR) -> "KrakenCredentials":
        path = Path(directory).expanduser()
        key_file, secret_file = path / "key", path / "secret"
        if not key_file.exists() or not secret_file.exists():
            raise ValueError(
                f"no credentials in {path}. Expected a 'key' and a 'secret' file, mode "
                f"600. Create them by hand from Kraken's API settings page; nothing in "
                f"this repository will write them for you and none of it belongs in git."
            )
        key = key_file.read_text(encoding="utf-8").strip()
        secret = secret_file.read_text(encoding="utf-8").strip()
        if not key or not secret:
            raise ValueError(f"the credential files in {path} are empty")
        try:
            base64.b64decode(secret)
        except Exception as error:  # noqa: BLE001 - any decode failure is the same answer
            raise ValueError(
                f"the secret in {path} is not valid base64, so it is not a Kraken API "
                f"secret. Signing would fail on every call: {error}"
            ) from error
        return cls(key, secret, path)

    def permissions_are_private(self) -> bool | None:
        """Are the credential files readable only by their owner?

        None on a platform where the question does not have this answer — Windows does not
        express permissions in POSIX mode bits, and returning False there would report a
        secure file as exposed.
        """

        import os
        import stat

        if os.name != "posix":
            return None
        for name in ("key", "secret"):
            mode = (self.directory / name).stat().st_mode
            if mode & (stat.S_IRWXG | stat.S_IRWXO):
                return False
        return True


def _next_nonce(directory: Path, now_ms: Callable[[], int] = lambda: int(time.time() * 1000)) -> int:
    """A nonce strictly greater than any this key has used, as far as this box knows.

    The clock is the usual source, but a clock that steps backwards — an NTP correction, a
    resumed VM — would produce a nonce Kraken has already seen. So the last one is
    remembered and the new one is forced past it.
    """

    marker = directory / "nonce"
    previous = 0
    if marker.exists():
        try:
            previous = int(marker.read_text(encoding="utf-8").strip() or 0)
        except ValueError:
            previous = 0
    nonce = max(now_ms(), previous + 1)
    marker.write_text(str(nonce), encoding="utf-8")
    return nonce


def userref_for(subject: str, side: str, quantity: float, thesis_declared_at: str) -> int:
    """A stable 32-bit label for one intended trade.

    Derived from the intent rather than the moment, so the same intended order carries the
    same reference and `resolve()` can find it after an UNKNOWN. Kraken does NOT reject a
    duplicate userref — this identifies an order, it does not prevent a second one — which
    is exactly why this adapter never retries a submit.
    """

    seed = f"{subject}|{side}|{quantity:.8f}|{thesis_declared_at}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(seed).digest()[:4], "big") & 0x7FFFFFFF


@dataclass(frozen=True, slots=True)
class Instruction:
    """A sized, authorised order that knows how it gets out.

    `stop_price` is required. An entry with no exit attached is not a smaller risk than one
    with a bad exit; it is an unbounded one, and this class will not construct without it.
    """

    pair: str
    side: str
    volume: float
    stop_price: float
    permission: Any
    userref: int
    #: None means market. A limit price makes the entry a maker order, which on Kraken is
    #: most of the difference between a viable strategy and an unviable one.
    limit_price: float | None = None

    def __post_init__(self) -> None:
        if self.side not in {BUY, SELL}:
            raise ValueError(f"side must be {BUY!r} or {SELL!r}, not {self.side!r}")
        if self.volume <= 0:
            raise ValueError("volume must be positive; direction is carried by side")
        if self.stop_price <= 0:
            raise ValueError(
                "a stop price is required and must be positive. An entry with no exit "
                "attached is an unbounded position, not a smaller one"
            )
        if self.limit_price is not None and self.limit_price <= 0:
            raise ValueError("a limit price, when given, must be positive")
        if self.side == BUY and self.limit_price and self.stop_price >= self.limit_price:
            raise ValueError(
                f"a buy's stop ({self.stop_price}) must sit BELOW its entry "
                f"({self.limit_price}). As written this order stops out on arrival"
            )
        if self.side == SELL and self.limit_price and self.stop_price <= self.limit_price:
            raise ValueError(
                f"a sell's stop ({self.stop_price}) must sit ABOVE its entry "
                f"({self.limit_price}). As written this order stops out on arrival"
            )


@dataclass(frozen=True, slots=True)
class OrderResult:
    status: str
    pair: str
    userref: int
    txid: str = ""
    filled_quantity: float = 0.0
    requested_quantity: float = 0.0
    filled_avg_price: float = 0.0
    reason: str = ""
    #: What Kraken says it understood the order to be. Present on VALIDATED, where it is
    #: the entire point: the venue's reading of the instruction, before it is live.
    description: str = ""

    @property
    def may_have_been_placed(self) -> bool:
        """True when a second submit could double-fill. The question after a timeout."""

        return self.status not in {REJECTED, CANCELLED, NOT_CONFIGURED, VALIDATED}

    def describe(self) -> str:
        if self.status == VALIDATED:
            return (
                f"VALIDATED  {self.pair} {self.requested_quantity:g}\n"
                f"  Kraken accepted this as a well-formed order and DID NOT PLACE IT.\n"
                f"  It reads it as: {self.description or '(no description returned)'}\n"
                f"  Nothing is at risk. This is a dry run against the real venue, not a fill."
            )
        if self.status == UNKNOWN:
            return (
                f"UNKNOWN  {self.pair} {self.requested_quantity:g}\n"
                f"  The outcome could not be established: {self.reason}\n"
                f"  This is NOT a report that nothing was placed. DO NOT RESUBMIT — Kraken "
                f"does not\n  reject a duplicate, so a second send fills twice. Resolve it: "
                f"python trade.py --resolve {self.userref}"
            )
        if self.status == REJECTED:
            return f"REJECTED  {self.pair}: {self.reason}\n  Nothing is at risk."
        if self.status == NOT_CONFIGURED:
            return f"NOT_CONFIGURED  {self.pair}: {self.reason}"
        if self.status in {FILLED, PART_FILLED}:
            return (
                f"{self.status}  {self.pair}: {self.filled_quantity:g} of "
                f"{self.requested_quantity:g} at {self.filled_avg_price:,.4f}\n"
                f"  MONEY HAS MOVED. Kraken reference {self.txid}."
            )
        return f"{self.status}  {self.pair} {self.requested_quantity:g}  {self.reason}"


@dataclass(frozen=True, slots=True)
class BalanceRead:
    """What is in the account, or why that is not known.

    Zero and unknown are the same number and different facts. A sizing routine handed a
    zero it should have read as unknown sizes nothing, which is safe; one handed a stale
    balance sizes against money that is not there, which is not.
    """

    status: str
    balances: dict[str, float] = None
    reason: str = ""

    @property
    def readable(self) -> bool:
        return self.status == FILLED  # reused vocabulary: the read completed

    def total_usd(self) -> float | None:
        if not self.readable or self.balances is None:
            return None
        return sum(v for k, v in self.balances.items() if k in {"ZUSD", "USD"})


class KrakenBroker:
    """Reads the account and sends orders. Originates nothing, and defaults to not sending.

    `place()` takes `validate` and it defaults to **True**. Placing is the argument you have
    to pass, not the one you have to remember to suppress.
    """

    name = VENUE

    def __init__(
        self,
        credentials: KrakenCredentials | None,
        *,
        opener: Callable[..., Any] = retrying_urlopen,
        nonce: Callable[[Path], int] = _next_nonce,
    ) -> None:
        self.credentials = credentials
        self._opener = opener
        self._nonce = nonce

    @classmethod
    def from_directory(
        cls, directory: str | Path = DEFAULT_CREDENTIALS_DIR, **kw: Any
    ) -> "KrakenBroker":
        try:
            return cls(KrakenCredentials.load(directory), **kw)
        except ValueError:
            # Unconfigured is a state a report can print, not an exception that kills a
            # scan that was also going to say six other useful things.
            return cls(None, **kw)

    @property
    def is_configured(self) -> bool:
        return self.credentials is not None

    def _call(self, path: str, data: dict[str, Any]) -> dict[str, Any]:
        """One signed private call. Raises on transport failure; returns Kraken's payload."""

        assert self.credentials is not None
        body = dict(data)
        body["nonce"] = self._nonce(self.credentials.directory)
        post = urllib.parse.urlencode(body)
        message = path.encode() + hashlib.sha256(
            (str(body["nonce"]) + post).encode()
        ).digest()
        signature = base64.b64encode(
            hmac.new(base64.b64decode(self.credentials.secret), message,
                     hashlib.sha512).digest()
        ).decode()
        request = urllib.request.Request(
            API + path, data=post.encode(),
            headers={
                "API-Key": self.credentials.key,
                "API-Sign": signature,
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "rbm-kraken-exec",
            },
            method="POST",
        )
        with self._opener(request) as response:
            return json.loads(response.read().decode("utf-8") or "{}")

    def balance(self) -> BalanceRead:
        if not self.is_configured:
            return BalanceRead(NOT_CONFIGURED, None,
                               f"no credentials in {DEFAULT_CREDENTIALS_DIR}")
        try:
            payload = self._call("/0/private/Balance", {})
        except (urllib.error.URLError, OSError, ValueError, TimeoutError) as error:
            return BalanceRead(UNKNOWN, None, f"{type(error).__name__}: {error}")
        errors = payload.get("error") or []
        if errors:
            return BalanceRead(UNKNOWN, None, "; ".join(str(e) for e in errors))
        return BalanceRead(
            FILLED, {k: float(v) for k, v in (payload.get("result") or {}).items()}
        )

    def place(self, instruction: Instruction, *, validate: bool = True) -> OrderResult:
        """Submit, or — by default — ask Kraken to check it without submitting.

        The permission is re-read here rather than trusted from upstream. The last thing
        before money moves is exactly where a redundant check earns its place.
        """

        from lib.thesis import PERMITTED

        shared = {"pair": instruction.pair, "userref": instruction.userref,
                  "requested_quantity": instruction.volume}

        status = getattr(instruction.permission, "status", None)
        if status != PERMITTED:
            return OrderResult(REJECTED, reason=(
                f"the attached permission is {status}, not {PERMITTED}. INDETERMINATE is "
                f"not a weaker yes and this adapter does not act on one."), **shared)

        if not self.is_configured:
            return OrderResult(NOT_CONFIGURED, reason=(
                f"no credentials in {DEFAULT_CREDENTIALS_DIR}; nothing was sent"), **shared)

        body: dict[str, Any] = {
            "pair": instruction.pair,
            "type": instruction.side,
            "ordertype": "limit" if instruction.limit_price else "market",
            "volume": f"{instruction.volume:.8f}",
            "userref": instruction.userref,
            # The stop rides with the entry. A second call to attach it has a window in it,
            # and the window is the entire risk of the position.
            "close[ordertype]": "stop-loss",
            "close[price]": f"{instruction.stop_price:.8f}",
        }
        if instruction.limit_price:
            body["price"] = f"{instruction.limit_price:.8f}"
        if validate:
            body["validate"] = "true"

        try:
            payload = self._call("/0/private/AddOrder", body)
        except urllib.error.HTTPError as error:
            if 400 <= error.code < 500:
                # The venue decided. A refusal, not an unknown.
                return OrderResult(REJECTED, reason=f"HTTP {error.code}", **shared)
            return OrderResult(UNKNOWN, reason=(
                f"HTTP {error.code} from Kraken. The request may have been processed."),
                **shared)
        except (urllib.error.URLError, OSError, TimeoutError) as error:
            return OrderResult(UNKNOWN, reason=(
                f"{type(error).__name__}: {error}. The request may have reached Kraken."),
                **shared)
        except ValueError as error:
            return OrderResult(UNKNOWN, reason=(
                f"Kraken's reply could not be parsed ({error}). An unreadable answer is "
                f"not a refusal."), **shared)

        errors = payload.get("error") or []
        if any(str(e).startswith(NONCE_ERRORS) for e in errors):
            raise NonceRegression(
                f"Kraken rejected the nonce ({'; '.join(str(e) for e in errors)}). Another "
                f"process is using this key, or the clock moved. NOTHING WAS PLACED, but "
                f"this is not the order being refused and must not be retried as though "
                f"it were."
            )
        if errors:
            return OrderResult(REJECTED, reason="; ".join(str(e) for e in errors), **shared)

        result = payload.get("result") or {}
        description = (result.get("descr") or {}).get("order", "")
        if validate:
            # Kraken returns a description and no txid. Saying FILLED here would be the
            # single worst bug this file could contain.
            return OrderResult(VALIDATED, description=description, **shared)

        txids = result.get("txid") or []
        if not txids:
            return OrderResult(UNKNOWN, description=description, reason=(
                "Kraken returned no error and no transaction id, so whether the order "
                "exists is not established."), **shared)
        return OrderResult(SUBMITTED, txid=str(txids[0]), description=description, **shared)

    def resolve(self, userref: int) -> OrderResult:
        """Ask Kraken what happened to an order, after an UNKNOWN. The alternative to retrying.

        Checks open orders and then recently closed ones. A userref found in neither is
        still UNKNOWN rather than 'never placed': Kraken's closed-order history is paged
        and this looks at one page.
        """

        if not self.is_configured:
            return OrderResult(NOT_CONFIGURED, "", userref,
                               reason=f"no credentials in {DEFAULT_CREDENTIALS_DIR}")
        for path, key in (("/0/private/OpenOrders", "open"),
                          ("/0/private/ClosedOrders", "closed")):
            try:
                payload = self._call(path, {"userref": userref})
            except (urllib.error.URLError, OSError, ValueError, TimeoutError) as error:
                return OrderResult(UNKNOWN, "", userref, reason=(
                    f"could not ask Kraken: {type(error).__name__}: {error}"))
            errors = payload.get("error") or []
            if errors:
                return OrderResult(UNKNOWN, "", userref,
                                   reason="; ".join(str(e) for e in errors))
            orders = ((payload.get("result") or {}).get(key) or {})
            for txid, order in orders.items():
                filled = float(order.get("vol_exec", 0) or 0)
                requested = float(order.get("vol", 0) or 0)
                state = str(order.get("status", ""))
                status = {
                    "closed": FILLED if filled >= requested > 0 else PART_FILLED,
                    "canceled": CANCELLED,
                    "expired": CANCELLED,
                    "open": SUBMITTED,
                    "pending": SUBMITTED,
                }.get(state, UNKNOWN)
                return OrderResult(
                    status, str(order.get("descr", {}).get("pair", "")), userref,
                    txid=txid, filled_quantity=filled, requested_quantity=requested,
                    filled_avg_price=float(order.get("price", 0) or 0),
                    reason=f"Kraken reports this order as {state!r}",
                    description=str(order.get("descr", {}).get("order", "")),
                )
        return OrderResult(UNKNOWN, "", userref, reason=(
            "no order with this reference is open, and none appears on the first page of "
            "closed orders. That is not proof it was never placed — check the account."))
