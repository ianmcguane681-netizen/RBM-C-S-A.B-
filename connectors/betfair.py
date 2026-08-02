"""Betfair Exchange: prices, the sizes behind them, and the rules they settle under.

An exchange is the honest half of arbitrage. The prices are other people's money rather
than an operator's opinion, the sizes are visible, and the same market is available to
everyone. That makes it the right first source and a poor complete one: an arb against a
bookmaker still depends on the bookmaker.

Four things this module refuses to do, each because the alternative reads as profit.

**An expired session is not an empty market.** The session token lapses with inactivity.
A scanner whose token died and returned no prices, reporting "no arb", is wrong in the
direction that costs money, and the failure is invisible. Expiry raises rather than
returning nothing.

**A delayed key is not a live key.** Betfair issues a delayed application key by default,
and its prices are minutes old. Every arb computed from them is fiction. The credentials
must DECLARE which they are, and a quote from a delayed key carries the delay on its face
rather than being inferred from a naming convention.

**A market without retrievable rules produces no legs.** AG-02 requires settlement wording
quoted verbatim, so a market whose description could not be fetched yields
`RULES_UNAVAILABLE` rather than legs missing a field. A leg cannot be constructed without
its rule, and this module does not work around that.

**Size at the best price is not size in the market.** `availableToBack` is a ladder; the
top rung is what a stake of that size actually gets. Summing the ladder would report depth
nobody can take at the quoted price.

No credentials live here. They are read from a directory the operator controls, and their
absence is `NOT_CONFIGURED` -- a state, never an exception, so a scan can report which
sources answered.
"""
from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Sequence

from connectors.odds import CONFIGURED, EXCHANGE, NOT_CONFIGURED, UNREACHABLE, MarketQuote
from lib.arb import Leg
from lib.http_retry import TransientRetrievalError, retrying_urlopen

# Endpoints are declared in one place and are the thing most likely to drift. They were
# written from Betfair's published developer documentation and have NOT been exercised
# against the live service from this environment, which has no credentials. Verify before
# relying on a result.
CERT_LOGIN_URL = "https://identitysso-cert.betfair.com/api/certlogin"
INTERACTIVE_LOGIN_URL = "https://identitysso.betfair.com/api/login"
KEEP_ALIVE_URL = "https://identitysso.betfair.com/api/keepAlive"
BETTING_URL = "https://api.betfair.com/exchange/betting/rest/v1.0"
ACCOUNT_URL = "https://api.betfair.com/exchange/account/rest/v1.0"

RULES_UNAVAILABLE = "RULES_UNAVAILABLE"

# Betfair's standard exchange commission on net market winnings. It is a market and account
# dependent rate, so it is a declared default rather than a constant of nature: an operator
# on a different rate sets it and the arithmetic follows.
DEFAULT_COMMISSION_PCT = 5.0


class SessionExpired(TransientRetrievalError):
    """The token lapsed. Deliberately an error, never an empty result.

    Returning no prices here would be indistinguishable from a market with no prices, and
    a scanner would report "no arb" for a market it never saw.
    """


@dataclass(frozen=True, slots=True)
class BetfairCredentials:
    """What is needed to mint a session, loaded from disk rather than passed around.

    `delayed` is declared, not inferred. Betfair's delayed keys conventionally carry a
    suffix, but resting a correctness property on a naming convention is how a scanner ends
    up arbing five-minute-old prices and believing itself.
    """

    app_key: str
    username: str
    delayed: bool
    certificate: Path | None = None
    certificate_key: Path | None = None
    password: str = ""

    @property
    def can_login_non_interactively(self) -> bool:
        return bool(self.certificate and self.certificate_key)

    @classmethod
    def load(cls, directory: str | Path = "~/.betfair") -> "BetfairCredentials | None":
        """Read credentials, or return None when they are simply not there.

        None rather than an exception: an unconfigured source is an ordinary state of the
        world that a scan must be able to report, not an error that ends the scan.
        """

        root = Path(directory).expanduser()
        app_key = root / "app_key"
        username = root / "username"
        if not app_key.is_file() or not username.is_file():
            return None

        delayed_marker = root / "delayed"
        live_marker = root / "live"
        if delayed_marker.is_file() == live_marker.is_file():
            raise ValueError(
                f"{root} must contain exactly one of 'delayed' or 'live' so the key's "
                f"kind is declared rather than guessed from its name"
            )

        password_file = root / "password"
        certificate, certificate_key = root / "client.crt", root / "client.key"
        return cls(
            app_key=app_key.read_text(encoding="utf-8").strip(),
            username=username.read_text(encoding="utf-8").strip(),
            delayed=delayed_marker.is_file(),
            certificate=certificate if certificate.is_file() else None,
            certificate_key=certificate_key if certificate_key.is_file() else None,
            password=password_file.read_text(encoding="utf-8").strip()
            if password_file.is_file() else "",
        )


@dataclass
class BetfairSession:
    """Holds a session token and re-mints it when it lapses.

    The operator never handles a token. It is minted here, held in memory, refreshed, and
    discarded when the process ends.
    """

    credentials: BetfairCredentials
    transport: Callable[[str, dict[str, str], bytes | None], Any] | None = None
    _token: str = field(default="", init=False, repr=False)

    @property
    def is_open(self) -> bool:
        return bool(self._token)

    def _post(self, url: str, headers: dict[str, str], body: bytes | None) -> Any:
        if self.transport is not None:
            return self.transport(url, headers, body)
        request = urllib.request.Request(url, data=body, headers=headers, method="POST")
        context = None
        if self.credentials.can_login_non_interactively and "cert" in url:
            context = ssl.create_default_context()
            context.load_cert_chain(
                str(self.credentials.certificate), str(self.credentials.certificate_key)
            )
        try:
            with retrying_urlopen(request) as response:  # pragma: no cover - network
                return json.load(response)
        except urllib.error.HTTPError as error:  # pragma: no cover - network
            raise TransientRetrievalError(f"Betfair {error.code} for {url}") from error
        except OSError as error:  # pragma: no cover - network
            raise TransientRetrievalError(f"Betfair unreachable: {error}") from error

    def login(self) -> str:
        creds = self.credentials
        if creds.can_login_non_interactively:
            payload = f"username={creds.username}&password={creds.password}".encode()
            result = self._post(CERT_LOGIN_URL, {
                "X-Application": creds.app_key,
                "Content-Type": "application/x-www-form-urlencoded",
            }, payload)
            status = result.get("loginStatus")
            if status != "SUCCESS":
                raise SessionExpired(f"Betfair certificate login refused: {status}")
            self._token = str(result.get("sessionToken") or "")
        else:
            payload = f"username={creds.username}&password={creds.password}".encode()
            result = self._post(INTERACTIVE_LOGIN_URL, {
                "X-Application": creds.app_key,
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            }, payload)
            if result.get("status") != "SUCCESS":
                raise SessionExpired(f"Betfair login refused: {result.get('error')}")
            self._token = str(result.get("token") or "")
        if not self._token:
            raise SessionExpired("Betfair returned no session token")
        return self._token

    def headers(self) -> dict[str, str]:
        if not self._token:
            self.login()
        return {
            "X-Application": self.credentials.app_key,
            "X-Authentication": self._token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def call(self, url: str, payload: dict[str, Any], *, _retried: bool = False) -> Any:
        """One Betting API call, re-authenticating once if the token has lapsed.

        Exactly once. Retrying a login loop against a refused credential would hammer the
        identity service and eventually lock the account.
        """

        result = self._post(url, self.headers(), json.dumps(payload).encode())
        if isinstance(result, dict) and result.get("faultcode"):
            detail = str(result.get("faultstring") or result)
            if "INVALID_SESSION" in detail.upper() and not _retried:
                self._token = ""
                return self.call(url, payload, _retried=True)
            raise SessionExpired(f"Betfair rejected the call: {detail}")
        return result


@dataclass(frozen=True, slots=True)
class BetfairSource:
    """An `OddsSource` over the Betfair Exchange."""

    session: BetfairSession | None
    commission_pct: float = DEFAULT_COMMISSION_PCT
    name: str = "Betfair Exchange"
    kind: str = EXCHANGE

    @classmethod
    def from_directory(cls, directory: str | Path = "~/.betfair", **kw: Any) -> "BetfairSource":
        credentials = BetfairCredentials.load(directory)
        if credentials is None:
            return cls(session=None, **kw)
        return cls(session=BetfairSession(credentials), **kw)

    def _catalogue(self, market_id: str) -> dict[str, Any]:
        assert self.session is not None
        results = self.session.call(f"{BETTING_URL}/listMarketCatalogue/", {
            "filter": {"marketIds": [market_id]},
            "marketProjection": ["MARKET_DESCRIPTION", "RUNNER_DESCRIPTION", "EVENT"],
            "maxResults": 1,
        })
        return results[0] if results else {}

    def _book(self, market_id: str) -> dict[str, Any]:
        assert self.session is not None
        results = self.session.call(f"{BETTING_URL}/listMarketBook/", {
            "marketIds": [market_id],
            "priceProjection": {"priceData": ["EX_BEST_OFFERS"]},
        })
        return results[0] if results else {}

    def quote(self, market: str, *, observed_at: str = "") -> MarketQuote:
        if self.session is None:
            return MarketQuote(
                NOT_CONFIGURED, self.name, self.kind, market=market,
                reason="no credentials found; see connectors/betfair.py for the file layout",
            )

        try:
            catalogue = self._catalogue(market)
            book = self._book(market)
        except TransientRetrievalError as error:
            return MarketQuote(
                UNREACHABLE, self.name, self.kind, market=market, reason=str(error)[:160]
            )

        rules = str((catalogue.get("description") or {}).get("rules") or "").strip()
        if not rules:
            # AG-02 needs the wording verbatim. Without it a Leg cannot be built, and
            # building one anyway would let a settlement mismatch through unseen.
            return MarketQuote(
                UNREACHABLE, self.name, self.kind, market=market,
                reason=f"{RULES_UNAVAILABLE}: market description carried no rules text, so "
                       f"settlement cannot be compared against another book",
            )

        names = {
            r.get("selectionId"): str(r.get("runnerName") or r.get("selectionId"))
            for r in catalogue.get("runners", ())
        }
        market_name = str(catalogue.get("marketName") or market)
        stamp = observed_at or str(book.get("lastMatchTime") or "")

        legs: list[Leg] = []
        for runner in book.get("runners", ()):
            offers = ((runner.get("ex") or {}).get("availableToBack") or ())
            if not offers:
                continue
            # The top rung only. Summing the ladder reports depth nobody can take at the
            # quoted price.
            best = offers[0]
            price, size = best.get("price"), best.get("size")
            if not price or not size:
                continue
            legs.append(Leg(
                book=self.name,
                market=f"{market}:{market_name}",
                selection=names.get(runner.get("selectionId"), str(runner.get("selectionId"))),
                decimal_odds=float(price),
                settlement_rule=rules,
                max_stake=float(size),
                observed_at=stamp,
                commission_pct=self.commission_pct,
            ))

        return MarketQuote(
            CONFIGURED, self.name, self.kind, market=f"{market}:{market_name}",
            legs=tuple(legs), observed_at=stamp,
            stake_is_observed=True,
            reason="DELAYED KEY: prices are minutes old and no arb computed from them is "
                   "real" if self.session.credentials.delayed else "",
        )

    def balance(self) -> dict[str, Any] | None:
        """Account funds, for AG-04. None when unconfigured, never zero."""

        if self.session is None:
            return None
        return self.session.call(f"{ACCOUNT_URL}/getAccountFunds/", {})
