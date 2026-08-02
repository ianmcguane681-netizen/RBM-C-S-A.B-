"""What each lane needs before it can read anything, and what it can already do.

"Built, just needs credentials" is a claim about a system, and like every other claim
here it should be checkable rather than asserted. This is the check.

It answers per lane, per requirement, in the vocabulary the connectors already use:

    READY           present, and a probe confirmed it works
    CONFIGURED      present, not probed
    NOT_CONFIGURED  absent
    UNREACHABLE     present, and the probe failed
    NOT_ATTEMPTED   deliberately not probed

`NOT_CONFIGURED` and `UNREACHABLE` are kept apart for the reason they always are here: a
missing key and a dead endpoint need opposite responses from a person, and a report that
merged them would send them to the wrong one.

The subtler distinction is at the lane level. A lane with no missing credentials is not
therefore a lane that can tell you anything:

    READY      every requirement met
    DEGRADED   it runs, but on a fraction of the evidence it is meant to see
    BLOCKED    a requirement it cannot work without is missing

Arbitrage is the case that forces `DEGRADED` to exist. `check_arb.py` needs no credentials
at all -- you type odds off two screens and it checks the maths honestly. But a live scan
with no configured book reaches nought of five sources, and "no arb found" from nought of
five is the most expensive sentence this repository knows how to produce. The lane works.
It just cannot see. Reporting that as READY would be true about the code and false about
the system.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Sequence

READY = "READY"
CONFIGURED = "CONFIGURED"
NOT_CONFIGURED = "NOT_CONFIGURED"
UNREACHABLE = "UNREACHABLE"
NOT_ATTEMPTED = "NOT_ATTEMPTED"

DEGRADED = "DEGRADED"
BLOCKED = "BLOCKED"

CRYPTO = "crypto"
STOCKS = "stocks"
ARB = "arb"

#: Statuses that mean the requirement is not currently usable.
UNMET = frozenset({NOT_CONFIGURED, UNREACHABLE})


@dataclass(frozen=True, slots=True)
class Requirement:
    """One thing a lane needs, what having it buys, and how to supply it."""

    lane: str
    name: str
    status: str
    unlocks: str
    detail: str = ""
    remedy: str = ""
    #: False when the lane still does useful work without it. A requirement that is not
    #: required but missing produces DEGRADED rather than BLOCKED.
    required: bool = True

    @property
    def is_met(self) -> bool:
        return self.status not in UNMET

    def describe(self) -> str:
        mark = {
            READY: "  ok  ", CONFIGURED: "  set ", NOT_ATTEMPTED: "  --  ",
            NOT_CONFIGURED: " MISS ", UNREACHABLE: " DOWN ",
        }.get(self.status, "  ?   ")
        lines = [f"[{mark}] {self.name}"]
        if self.detail:
            lines.append(f"           {self.detail}")
        lines.append(f"           unlocks: {self.unlocks}")
        if not self.is_met and self.remedy:
            lines.append(f"           to fix:  {self.remedy}")
        return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class LaneReadiness:
    lane: str
    summary: str
    requirements: tuple[Requirement, ...] = field(default_factory=tuple)

    @property
    def missing(self) -> tuple[Requirement, ...]:
        return tuple(r for r in self.requirements if not r.is_met)

    @property
    def status(self) -> str:
        """BLOCKED beats DEGRADED beats READY."""

        if any(r.required for r in self.missing):
            return BLOCKED
        if self.missing:
            return DEGRADED
        return READY

    def describe(self) -> str:
        lines = [f"{self.lane.upper():<8} {self.status}", f"         {self.summary}", ""]
        lines += [r.describe() for r in self.requirements]
        return "\n".join(lines)


# --------------------------------------------------------------------------------------
# Probes. Each returns (status, detail) and never raises: a preflight that crashes on a
# dead endpoint has failed at the one job it has.
# --------------------------------------------------------------------------------------

def _probe_chain() -> tuple[str, str]:
    try:
        from connectors.chain import ChainClient, best_for

        client = ChainClient(best_for("state"))
        block = int(client.read("eth_getBlockByNumber", ["finalized", False]).value["number"], 16)
        return READY, f"finalized block {block:,}"
    except Exception as error:  # noqa: BLE001 - any failure is a failure to reach it
        return UNREACHABLE, f"{type(error).__name__}: {error}"[:140]


def _probe_edgar() -> tuple[str, str]:
    try:
        from connectors.edgar import EdgarClient

        cik = EdgarClient().cik_for_ticker("AAPL")
        return READY, f"resolved AAPL to CIK {cik}"
    except Exception as error:  # noqa: BLE001
        return UNREACHABLE, f"{type(error).__name__}: {error}"[:140]


# --------------------------------------------------------------------------------------
# Lanes
# --------------------------------------------------------------------------------------

def crypto_lane(*, probe: bool = False, environ: dict[str, str] | None = None) -> LaneReadiness:
    env = os.environ if environ is None else environ
    url = env.get("QUICKNODE_ETHEREUM_URL", "").strip()

    if not url:
        status, detail = NOT_CONFIGURED, ""
    elif probe:
        status, detail = _probe_chain()
    else:
        # The URL is never echoed. It carries an auth token in its path, which is why it
        # lives in an environment variable and not in a tracked file.
        status, detail = CONFIGURED, "set (value not shown; it contains an auth token)"

    return LaneReadiness(
        CRYPTO,
        "Six gates against live chain state. Two USDC reviews published and exported.",
        (
            Requirement(
                CRYPTO, "Ethereum JSON-RPC endpoint", status,
                unlocks="check_token.py, chain-evidence, monitor tokens, trade_sheet cost panel",
                detail=detail,
                remedy="export QUICKNODE_ETHEREUM_URL='https://...' (any archive-capable node)",
            ),
        ),
    )


def stocks_lane(*, probe: bool = False) -> LaneReadiness:
    from connectors.edgar import DEFAULT_AGENT

    if probe:
        status, detail = _probe_edgar()
    else:
        status, detail = CONFIGURED, f"User-Agent: {DEFAULT_AGENT}"

    return LaneReadiness(
        STOCKS,
        "Filing gates against SEC EDGAR. No API key exists to obtain; EDGAR asks only "
        "that a client identify itself.",
        (
            Requirement(
                STOCKS, "SEC EDGAR identification", status,
                unlocks="check_stock.py, RBM-004 evidence, monitor tickers",
                detail=detail,
                remedy="EdgarClient(user_agent='you you@example.com') -- must contain an address",
            ),
        ),
    )


def arb_lane(*, probe: bool = False, home: str | Path | None = None) -> LaneReadiness:
    """Credentials are checked by presence only, and never probed by default.

    A login is a real authentication event against a real account. Smarkets caps logins at
    five per five minutes, so a preflight that logged in every run could exhaust the budget
    a scan then needs. Presence is what this answers; `--probe` is opt-in.
    """

    root = Path(home).expanduser() if home else Path.home()
    requirements: list[Requirement] = []

    # First, because it is the only source that covers many books in one request and the
    # only one that turns nought-of-five coverage into a real universe for a free key.
    oddsapi = root / ".oddsapi" / "key"
    has_key = oddsapi.is_file() and oddsapi.read_text(encoding="utf-8").strip()
    requirements.append(Requirement(
        ARB, "The Odds API", NOT_ATTEMPTED if has_key else NOT_CONFIGURED,
        unlocks="many books in one request; discovery for scan_arb.py",
        detail=("key present" if has_key else ""), required=False,
        remedy="free key at the-odds-api.com, then ~/.oddsapi/key",
    ))

    betfair = root / ".betfair"
    have_key = (betfair / "app_key").is_file()
    delayed, live = (betfair / "delayed").is_file(), (betfair / "live").is_file()
    if not have_key:
        detail, status = "", NOT_CONFIGURED
    elif delayed == live:
        # Exactly one marker, always. A key whose kind is unknown would quote delayed
        # prices that read as live ones, and a delayed price is not a price you can trade.
        status = NOT_CONFIGURED
        detail = ("app_key present but the kind is undeclared: create exactly one of "
                  "'delayed' or 'live'")
    else:
        status = NOT_ATTEMPTED if not probe else CONFIGURED
        detail = f"app_key present, declared {'delayed' if delayed else 'live'}"
    requirements.append(Requirement(
        ARB, "Betfair Exchange", status,
        unlocks="live exchange prices, one of five sources in an odds scan",
        detail=detail, required=False,
        remedy="~/.betfair/{app_key,username,password} plus one of {delayed,live}",
    ))

    smarkets = root / ".smarkets"
    have = (smarkets / "username").is_file() and (smarkets / "password").is_file()
    requirements.append(Requirement(
        ARB, "Smarkets", NOT_ATTEMPTED if have else NOT_CONFIGURED,
        unlocks="a second exchange, so a divergence has two sides",
        detail="username and password present" if have else "", required=False,
        remedy="~/.smarkets/{username,password}",
    ))

    for name, why in (
        ("Matchbook", "needs API credentials"),
        ("Paddy Power", "no public odds API; needs a licensed feed"),
        ("Bet365", "no public odds API; needs a licensed feed"),
    ):
        requirements.append(Requirement(
            ARB, name, NOT_CONFIGURED, unlocks="one more source in an odds scan",
            required=False, remedy=why,
        ))

    covered = sum(1 for r in requirements if r.is_met)
    return LaneReadiness(
        ARB,
        f"Arb maths, settlement-rule divergence and stake sizing all run on typed odds "
        f"with no credentials at all. Live scanning currently reaches {covered} of "
        f"{len(requirements)} sources. A feed gives discovery only: available stake and "
        f"settlement rules are read at the book, never from an aggregator.",
        tuple(requirements),
    )


def all_lanes(*, probe: bool = False) -> tuple[LaneReadiness, ...]:
    return (crypto_lane(probe=probe), stocks_lane(probe=probe), arb_lane(probe=probe))


def report(lanes: Sequence[LaneReadiness]) -> str:
    lines: list[str] = []
    for lane in lanes:
        lines.append(lane.describe())
        lines.append("")

    lines.append("=" * 74)
    blocked = [l for l in lanes if l.status == BLOCKED]
    degraded = [l for l in lanes if l.status == DEGRADED]
    ready = [l for l in lanes if l.status == READY]

    if ready:
        lines.append(f"READY:    {', '.join(l.lane for l in ready)}")
    if degraded:
        lines.append(f"DEGRADED: {', '.join(l.lane for l in degraded)} -- runs, but on a "
                     f"fraction of the evidence it is meant to see")
    if blocked:
        lines.append(f"BLOCKED:  {', '.join(l.lane for l in blocked)}")

    lines.append("")
    lines.append("A lane reading READY means it can retrieve its evidence. It does NOT mean")
    lines.append("a board has been convened, nor that any decision exists. Those are separate")
    lines.append("questions and this command has no view on either.")
    return "\n".join(lines)
