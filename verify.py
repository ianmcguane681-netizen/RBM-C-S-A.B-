"""Prove a credential works, the moment it is placed — and say what it unlocked.

    python verify.py            every credential that exists, at no cost in quota
    python verify.py --json     the same, for a script
    python verify.py --book     also price the real portfolio and report the coverage

`preflight.py` answers "is a key present". This answers "does it work", which is a
different question and the one you actually have after placing one. Presence is a file
test; working means the service accepted it.

**The distinction this command exists to keep.** A key the service *rejected* and a service
that *could not be reached* both leave you without an answer, and only the first is about
the key. Reporting a network timeout as a bad credential sends a person to regenerate a
perfectly good key, discover the new one also "fails", and conclude the system is broken.

    CONFIRMED        the service accepted it on a real call
    REFUSED          the service answered and rejected it. The credential is wrong.
    COULD_NOT_REACH  nobody answered. This says NOTHING about the credential.
    NOT_CONFIGURED   there is nothing here to verify

**It spends nothing.** The Odds API's sports list is free and the Alpaca account and clock
reads cost nothing; the odds *quotes* endpoint, which does spend, is never called. Verifying
a key must not be the thing that empties the allowance it was placed to use.

**It places nothing, ever.** Not a dry run, not a cancelled order — no order path is
imported here at all.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass

CONFIRMED = "CONFIRMED"
REFUSED = "REFUSED"
COULD_NOT_REACH = "COULD_NOT_REACH"
NOT_CONFIGURED = "NOT_CONFIGURED"


@dataclass(frozen=True, slots=True)
class Check:
    name: str
    status: str
    detail: str = ""
    action: str = ""

    def describe(self) -> str:
        mark = {CONFIRMED: " ok ", REFUSED: "WRONG", COULD_NOT_REACH: "DOWN ",
                NOT_CONFIGURED: "MISS "}.get(self.status, "  ?  ")
        lines = [f"[{mark}] {self.name}  {self.status}"]
        if self.detail:
            lines.append(f"         {self.detail}")
        if self.action:
            lines.append(f"         -> {self.action}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {"name": self.name, "status": self.status,
                "detail": self.detail or None, "action": self.action or None}


def _classify(error: Exception) -> tuple[str, str]:
    """An HTTP 401/403 is about the credential. Everything else is about the network.

    A 500 from the venue is deliberately COULD_NOT_REACH: their server broke, which says
    nothing about the key, and a person told their key is wrong will go and replace a key
    that was never the problem.
    """

    import urllib.error

    if isinstance(error, urllib.error.HTTPError):
        if error.code in {401, 403}:
            return REFUSED, f"the service rejected the credential (HTTP {error.code})"
        return COULD_NOT_REACH, f"the service answered HTTP {error.code}"
    return COULD_NOT_REACH, f"{type(error).__name__}: {error}"[:140]


def check_alpaca() -> list[Check]:
    """Account, then clock. Both free, and the account read is what proves the key."""

    from connectors.alpaca import AlpacaBroker

    broker = AlpacaBroker.from_directory()
    if not broker.is_configured:
        return [Check(
            "Alpaca broker", NOT_CONFIGURED,
            "no key_id/secret_key, or neither 'paper' nor 'live' declared",
            "bash deploy/setup-credentials.sh",
        )]

    environment = "PAPER" if broker.is_paper else "LIVE"
    try:
        account = broker.account() or {}
    except Exception as error:  # noqa: BLE001 - the classification IS the output
        status, detail = _classify(error)
        return [Check("Alpaca broker", status, f"{detail}; declared {environment}", (
            "regenerate the key at alpaca.markets and re-run setup-credentials.sh"
            if status == REFUSED else
            "the key may be perfectly good — check the network and Alpaca's status page, "
            "then re-run this"
        ))]

    # Shouted, not mentioned. The base URLs differ by one word and a live order placed
    # believing it was paper is not a mistake anybody finds later.
    marker = "PAPER trading" if broker.is_paper else "*** LIVE MONEY ***"
    cash = account.get("cash")
    checks = [Check(
        "Alpaca broker", CONFIRMED,
        f"accepted, {marker}. account {account.get('status', 'unknown')}"
        + (f", cash {cash} {account.get('currency', '')}" if cash is not None else ""),
    )]

    open_now = broker.is_market_open()
    checks.append(Check(
        "Alpaca market clock",
        CONFIRMED if open_now is not None else COULD_NOT_REACH,
        f"the market is {'OPEN' if open_now else 'CLOSED'}" if open_now is not None
        else "the clock could not be read, so an old price will report STALE rather than "
             "being credited to a shut market",
    ))
    return checks


def check_odds() -> list[Check]:
    """The sports list, which the API serves free. Never the quotes endpoint."""

    from connectors.oddsapi import OddsApiSource

    source = OddsApiSource.from_directory()
    if not source.is_configured:
        return [Check("The Odds API", NOT_CONFIGURED, "no key at ~/.oddsapi/key",
                      "bash deploy/setup-credentials.sh")]
    try:
        sports = source.sports()
    except Exception as error:  # noqa: BLE001
        status, detail = _classify(error)
        return [Check("The Odds API", status, detail, (
            "the key is wrong or has been revoked — get another at the-odds-api.com"
            if status == REFUSED else "check the network, then re-run this"
        ))]

    usage = source.usage
    remaining = (f"{usage.remaining} credit(s) remain" if usage.is_known
                 else "the response carried no quota headers, so the remaining credit is "
                      "UNKNOWN rather than plentiful")
    return [Check("The Odds API", CONFIRMED,
                  f"accepted, {len(sports)} sport(s) in season. {remaining}. "
                  f"The sports list is free; no credit was spent verifying this.")]


def check_chain() -> list[Check]:
    """A block number. The URL is never echoed — it carries a token in its path."""

    import os

    if not os.environ.get("QUICKNODE_ETHEREUM_URL", "").strip():
        return [Check("Ethereum JSON-RPC", NOT_CONFIGURED, "QUICKNODE_ETHEREUM_URL is unset",
                      "export it from a 600 file; never paste it into a shell history")]
    try:
        from connectors.chain import ChainClient, quicknode_ethereum

        block = ChainClient(quicknode_ethereum()).block_number()
    except Exception as error:  # noqa: BLE001
        status, detail = _classify(error)
        return [Check("Ethereum JSON-RPC", status, detail, (
            "the node rejected the token in the URL — rotate it at the provider"
            if status == REFUSED else "check the network, then re-run this"
        ))]
    return [Check("Ethereum JSON-RPC", CONFIRMED, f"accepted, chain head at block {block}")]


def price_the_book() -> tuple[str, dict]:
    """What the real portfolio does against a live source, per holding.

    This is the question the pricing work could not answer without a key: how many of the
    holdings a US broker actually carries. `PARTIALLY_UNPRICED` with the rest named is the
    correct answer here, not a gap — so this prints the split rather than a score.
    """

    from pathlib import Path

    from lib.portfolio import Portfolio
    from lib.pricing import alpaca_prices, value_book
    from status import BOOK

    book = Portfolio(Path(BOOK))
    positions = book.positions()
    if not positions:
        return ("The portfolio holds nothing, so there is nothing to price. This is an "
                "empty book, not a valuation of zero."), {"holdings": 0}

    pricing = value_book(positions, alpaca_prices())
    exposure = book.exposure(pricing.valuations)
    lines = [pricing.describe()]
    lines += [f"    {v.describe()}" for v in pricing.valuations]
    lines.append("")
    lines.append(f"  {exposure.describe()}")
    return "\n".join(lines), {
        "holdings": len(positions),
        "priced": pricing.priced_count,
        "unquotable": list(pricing.unquotable),
        "unreachable": list(pricing.unreachable),
        "look": pricing.look,
    }


def run(*, book: bool = False) -> tuple[dict, int]:
    from lib.credentials import describe as describe_modes, exposed

    checks = check_alpaca() + check_odds() + check_chain()
    payload: dict = {
        "checks": [c.to_dict() for c in checks],
        "credential_modes": [
            {"path": str(f.path), "state": f.state, "mode": f.mode} for f in exposed()
        ],
        "modes_summary": describe_modes(),
    }
    if book:
        text, coverage = price_the_book()
        payload["book"] = {**coverage, "description": text}

    configured = [c for c in checks if c.status != NOT_CONFIGURED]
    failed = [c for c in configured if c.status != CONFIRMED]
    code = 2 if not configured else (1 if failed else 0)
    return payload, code


def main(argv: list[str]) -> int:
    payload, code = run(book="--book" in argv)

    if "--json" in argv:
        from lib.ui_contract import SCHEMA_VERSION

        print(json.dumps({"schema_version": SCHEMA_VERSION, **payload}, indent=2))
        return code

    print("VERIFY  a real call per credential. Nothing is placed and no quota is spent.")
    print()
    for check in payload["checks"]:
        print(Check(check["name"], check["status"], check["detail"] or "",
                    check["action"] or "").describe())
        print()

    print(payload["modes_summary"])
    print()

    if "book" in payload:
        print("THE BOOK, PRICED")
        print(payload["book"]["description"])
        print()

    if code == 2:
        print("Nothing is configured yet, so nothing could be verified. That is not a")
        print("report that the credentials are wrong — there are none to be wrong.")
    elif code == 1:
        print("Something that is configured did not verify. REFUSED means the credential")
        print("is wrong; COULD_NOT_REACH says nothing about it — re-run before replacing")
        print("a key on the strength of it.")
    else:
        print("Every credential present was accepted by the service that owns it.")
    return code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
