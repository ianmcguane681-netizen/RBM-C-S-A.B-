"""Smarkets: the same exchange questions, at a fraction of the ceremony.

No application key, no activation fee, no certificate. A session token is minted from an
ordinary account login, sent as `Authentication: Session-Token <token>`, and renewed
automatically by any authenticated request within its thirty-minute window.

Why it matters more than the convenience: **an exchange-against-exchange pair is far more
likely to settle alike than an exchange against a traditional bookmaker.** The evidence
that prompted this connector is a real divergence between Betfair Exchange and bet365 on
horse racing -- reduction factors against Rule 4, and a 5p waiver on one side only, worth
0.15 to 0.45 in odds at ordinary prices, which is more than most arb margins. Two exchanges
share a product shape, so the settlement question starts from a better place. It is still a
question, and this module never answers it for the operator.

Two limits it declares rather than works around.

**Login is rate limited to 5 requests per 300 seconds.** A connector that re-authenticated
on every failure would exhaust that in under half a minute and lock itself out for five,
during which every market reads as unavailable. Login is attempted once per call.

**Unrestricted prices need an API-user account.** Without that flag the documentation says
prices may be restricted, so a thin or empty book is `RESTRICTED_OR_EMPTY` rather than a
finding that no liquidity exists.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from connectors.odds import CONFIGURED, EXCHANGE, NOT_CONFIGURED, UNREACHABLE, MarketQuote
from lib.arb import Leg
from lib.http_retry import TransientRetrievalError, retrying_urlopen

BASE = "https://api.smarkets.com/v3"
LOGIN_URL = f"{BASE}/sessions/"

# Smarkets charges commission on net winnings per market, and the rate varies by account
# and market. Declared rather than assumed, so an operator on a different rate sets it and
# the arithmetic follows.
DEFAULT_COMMISSION_PCT = 2.0

RESTRICTED_OR_EMPTY = "RESTRICTED_OR_EMPTY"


class SmarketsSessionError(TransientRetrievalError):
    """Login failed or the token lapsed. An error, never an empty market."""


@dataclass(frozen=True, slots=True)
class SmarketsCredentials:
    username: str
    password: str

    @classmethod
    def load(cls, directory: str | Path = "~/.smarkets") -> "SmarketsCredentials | None":
        root = Path(directory).expanduser()
        username, password = root / "username", root / "password"
        if not username.is_file() or not password.is_file():
            return None
        return cls(
            username=username.read_text(encoding="utf-8").strip(),
            password=password.read_text(encoding="utf-8").strip(),
        )


@dataclass
class SmarketsSession:
    credentials: SmarketsCredentials
    transport: Callable[[str, dict[str, str], bytes | None, str], Any] | None = None
    _token: str = field(default="", init=False, repr=False)

    @property
    def is_open(self) -> bool:
        return bool(self._token)

    def _request(self, url: str, headers: dict[str, str], body: bytes | None, method: str) -> Any:
        if self.transport is not None:
            return self.transport(url, headers, body, method)
        request = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:  # pragma: no cover - network
            with retrying_urlopen(request) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:  # pragma: no cover - network
            raise TransientRetrievalError(f"Smarkets {error.code} for {url}") from error
        except OSError as error:  # pragma: no cover - network
            raise TransientRetrievalError(f"Smarkets unreachable: {error}") from error

    def login(self) -> str:
        payload = json.dumps({
            "username": self.credentials.username,
            "password": self.credentials.password,
            "remember": False,
        }).encode()
        result = self._request(
            LOGIN_URL, {"Content-Type": "application/json"}, payload, "POST"
        )
        token = str((result or {}).get("token") or "")
        if not token:
            raise SmarketsSessionError(
                f"Smarkets login returned no token: {str(result)[:120]}"
            )
        self._token = token
        return token

    def headers(self) -> dict[str, str]:
        if not self._token:
            self.login()
        return {
            "Authentication": f"Session-Token {self._token}",
            "Content-Type": "application/json",
        }

    def get(self, path: str, *, _retried: bool = False) -> Any:
        """One authenticated GET, re-authenticating at most once.

        Once, and never in a loop. Login is capped at 5 requests per 300 seconds, so a
        connector that re-authenticated on every failure would exhaust the allowance in
        under half a minute and then lock itself out for five -- during which every market
        it looked at would read as unavailable rather than unqueried.
        """

        try:
            return self._request(f"{BASE}{path}", self.headers(), None, "GET")
        except TransientRetrievalError as error:
            if "401" in str(error) and not _retried:
                self._token = ""
                return self.get(path, _retried=True)
            raise


@dataclass(frozen=True, slots=True)
class SmarketsSource:
    """An `OddsSource` over the Smarkets exchange."""

    session: SmarketsSession | None
    commission_pct: float = DEFAULT_COMMISSION_PCT
    name: str = "Smarkets"
    kind: str = EXCHANGE

    @classmethod
    def from_directory(cls, directory: str | Path = "~/.smarkets", **kw: Any) -> "SmarketsSource":
        credentials = SmarketsCredentials.load(directory)
        if credentials is None:
            return cls(session=None, **kw)
        return cls(session=SmarketsSession(credentials), **kw)

    def quote(self, market: str, *, observed_at: str = "") -> MarketQuote:
        if self.session is None:
            return MarketQuote(
                NOT_CONFIGURED, self.name, self.kind, market=market,
                reason="no credentials found; see connectors/smarkets.py for the file layout",
            )
        try:
            info = self.session.get(f"/markets/{market}/")
            contracts = self.session.get(f"/markets/{market}/contracts/")
            book = self.session.get(f"/markets/{market}/quotes/")
        except TransientRetrievalError as error:
            return MarketQuote(
                UNREACHABLE, self.name, self.kind, market=market, reason=str(error)[:160]
            )

        markets = (info or {}).get("markets") or []
        detail = markets[0] if markets else {}
        rules = str(detail.get("description") or detail.get("rules") or "").strip()
        if not rules:
            return MarketQuote(
                UNREACHABLE, self.name, self.kind, market=market,
                reason="RULES_UNAVAILABLE: the market carried no description, so settlement "
                       "cannot be compared against another book",
            )

        names = {
            str(c.get("id")): str(c.get("name") or c.get("id"))
            for c in ((contracts or {}).get("contracts") or [])
        }
        stamp = observed_at or str(detail.get("last_executed_at") or "")

        legs: list[Leg] = []
        for contract_id, quotes in (book or {}).items():
            offers = (quotes or {}).get("bids") or []
            if not offers:
                continue
            # Top of book only: the rest of the ladder is not available at this price.
            best = offers[0]
            price, size = best.get("price"), best.get("quantity")
            if not price or not size:
                continue
            # Smarkets quotes price as a percentage probability in hundredths.
            decimal_odds = 10000.0 / float(price)
            legs.append(Leg(
                book=self.name,
                market=f"{market}:{detail.get('name', market)}",
                selection=names.get(str(contract_id), str(contract_id)),
                decimal_odds=decimal_odds,
                settlement_rule=rules,
                max_stake=float(size) / 10000.0,
                observed_at=stamp,
                commission_pct=self.commission_pct,
            ))

        return MarketQuote(
            CONFIGURED, self.name, self.kind,
            market=f"{market}:{detail.get('name', market)}",
            legs=tuple(legs), observed_at=stamp, stake_is_observed=True,
            reason="" if legs else
                   f"{RESTRICTED_OR_EMPTY}: no priced contracts returned. Unrestricted "
                   f"prices require an API-user account, so this is not a finding that the "
                   f"market has no liquidity.",
        )
