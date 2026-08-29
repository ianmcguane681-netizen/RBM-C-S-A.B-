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
#: A lane taken out of the rotation on purpose. Reported rather than dropped, because a
#: preflight that simply stopped mentioning a lane would read as a lane that never existed
#: — and the next person would go looking for why its credentials are not checked.
PARKED = "PARKED"

CRYPTO = "crypto"
STOCKS = "stocks"
ARB = "arb"
MISPRICING = "mispricing"

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
    #: Why this lane is out of the rotation. Set only for a parked lane, and it outranks
    #: every requirement below: an unchecked credential on a lane that is not running is
    #: not a thing anybody needs to go and fix.
    parked_because: str = ""

    @property
    def missing(self) -> tuple[Requirement, ...]:
        return tuple(r for r in self.requirements if not r.is_met)

    @property
    def status(self) -> str:
        """PARKED beats BLOCKED beats DEGRADED beats READY."""

        if self.parked_because:
            return PARKED
        if any(r.required for r in self.missing):
            return BLOCKED
        if self.missing:
            return DEGRADED
        return READY

    def describe(self) -> str:
        lines = [f"{self.lane.upper():<8} {self.status}", f"         {self.summary}", ""]
        if self.parked_because:
            lines.append(f"         NOT IN THE ROTATION: {self.parked_because}")
            lines.append("")
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


def stocks_lane(*, probe: bool = False, home: str | Path | None = None) -> LaneReadiness:
    from connectors.edgar import DEFAULT_AGENT

    if probe:
        status, detail = _probe_edgar()
    else:
        status, detail = CONFIGURED, f"User-Agent: {DEFAULT_AGENT}"

    from pathlib import Path as _Path

    root = _Path(home).expanduser() if home else _Path.home()
    alpaca = root / ".alpaca"
    has_keys = (alpaca / "key_id").is_file() and (alpaca / "secret_key").is_file()
    paper, live = (alpaca / "paper").is_file(), (alpaca / "live").is_file()
    if not has_keys:
        broker_status, broker_detail = NOT_CONFIGURED, ""
    elif paper == live:
        # A key gives no hint which environment it belongs to and the base URLs differ by
        # one word. A live order placed believing it was paper is not found later.
        broker_status = NOT_CONFIGURED
        broker_detail = "keys present but the environment is undeclared: create exactly " \
                        "one of 'paper' or 'live'"
    else:
        broker_status = NOT_ATTEMPTED
        broker_detail = f"keys present, declared {'paper' if paper else 'LIVE'}"

    return LaneReadiness(
        STOCKS,
        "Filing gates against SEC EDGAR, and execution through a broker. No API key "
        "exists for EDGAR; it asks only that a client identify itself.",
        (
            Requirement(
                STOCKS, "SEC EDGAR identification", status,
                unlocks="check_stock.py, RBM-004 evidence, monitor tickers",
                detail=detail,
                remedy="EdgarClient(user_agent='you you@example.com') -- must contain an address",
            ),
            Requirement(
                STOCKS, "Alpaca broker", broker_status,
                unlocks="prices with size behind them, and paper order execution",
                detail=broker_detail, required=False,
                remedy="~/.alpaca/{key_id,secret_key} plus exactly one of {paper,live}",
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

    # Not a credential, and the only requirement on this lane that no amount of money
    # buys. Every candidate the lane finds reports INDETERMINATE until two books' rules
    # have been read once, so a preflight that listed five paid feeds and omitted the one
    # unpaid job standing between the lane and a placeable position would be describing
    # the wrong bottleneck.
    # Counted before the rulebook requirement is appended: a rulebook is not a source, and
    # folding it into "reaches N of M sources" would move that number for a reason that has
    # nothing to do with how many books the lane can see.
    covered = sum(1 for r in requirements if r.is_met)
    sources = len(requirements)

    rulebook = _rulebook_requirement()
    requirements.append(rulebook)

    return LaneReadiness(
        ARB,
        f"Arb maths, settlement-rule divergence and stake sizing all run on typed odds "
        f"with no credentials at all. Live scanning currently reaches {covered} of "
        f"{sources} sources. A feed gives discovery only: available stake and "
        f"settlement rules are read at the book, never from an aggregator.\n"
        f"         Settlement rulebooks: {rulebook.status}. {rulebook.detail}\n"
        f"         Quota at the current settings: {_arb_burn()}",
        tuple(requirements),
    )


def mispricing_lane(*, probe: bool = False,
                    home: str | Path | None = None) -> LaneReadiness:
    """What the forecasting lane can actually see, and what it is forecasting without.

    The summary leads with the model's PAPER status rather than with the credentials,
    because that is the binding constraint: a lane with every key present and a PAPER model
    places nothing, and a reader who scanned the requirement list and saw three green lines
    would take the wrong thing from it.

    Only the odds feed is `required`. Everything else DEGRADES: without a league table the
    lane reports every fixture UNPRICED naming the strengths it wanted, which is a correct
    and useful answer, where without prices it has nothing to compare a forecast against
    and has not looked at all.
    """

    root = Path(home).expanduser() if home else Path.home()
    requirements: list[Requirement] = []

    oddsapi = root / ".oddsapi" / "key"
    has_odds = oddsapi.is_file() and oddsapi.read_text(encoding="utf-8").strip()
    requirements.append(Requirement(
        MISPRICING, "The Odds API", NOT_ATTEMPTED if has_odds else NOT_CONFIGURED,
        unlocks="the prices a forecast is compared against; without it nothing is compared",
        detail="key present" if has_odds else "",
        # The only hard requirement. A model with no price to disagree with has not looked.
        required=True,
        remedy="free key at the-odds-api.com, then ~/.oddsapi/key. SHARED with the arb "
               "lane — check the burn line below before enabling both",
    ))

    football = root / ".footballdata" / "key"
    has_league = football.is_file() and football.read_text(encoding="utf-8").strip()
    requirements.append(Requirement(
        MISPRICING, "football-data.org", NOT_ATTEMPTED if has_league else NOT_CONFIGURED,
        unlocks="league tables, and therefore team attack and defence strengths",
        detail="key present" if has_league else "", required=False,
        remedy="free key at football-data.org, then ~/.footballdata/key",
    ))

    # No credential, so it is CONFIGURED whenever the lane is allowed out to the network.
    requirements.append(Requirement(
        MISPRICING, "open-meteo", CONFIGURED,
        unlocks="wind and rain at the ground, a small adjustment applied only when known",
        detail="no key needed; conditions are UNKNOWN per fixture if the call fails",
        required=False, remedy="none — it needs no account",
    ))

    news = Path("data/team-news.json")
    requirements.append(Requirement(
        MISPRICING, "team news", CONFIGURED if news.is_file() else NOT_CONFIGURED,
        unlocks="the largest single input a book prices that this system cannot retrieve",
        detail=("recorded by hand in data/team-news.json" if news.is_file() else
                "no free structured source exists for this. Every fixture is forecast as "
                "fully fit AND SAYS SO; the book is not making that assumption"),
        required=False,
        remedy="record what you read, in the shape connectors/teamnews.template() prints",
    ))

    covered = sum(1 for r in requirements if r.is_met)
    return LaneReadiness(
        MISPRICING,
        f"A FORECAST lane — it claims a price is wrong, which the arb lane never does, and "
        f"a wrong forecast loses the whole stake. {_model_status()}\n"
        f"         Evidence: {covered} of {len(requirements)} source(s) reachable.\n"
        f"         Quota, SHARED with the arb lane: {_arb_burn()}",
        tuple(requirements),
    )


def _model_status() -> str:
    """Whether a model is declared, and whether it may size anything.

    Read from the config rather than asserted, because PAPER versus LIVE is the difference
    between a lane that records what it would have done and one that spends money, and it
    is a one-word edit in a file on a box.
    """

    try:
        from lib.reaping import CONFIG, load_config

        config, unreadable = load_config(CONFIG)
        if unreadable:
            return f"The model is UNKNOWN — {CONFIG} would not parse ({unreadable})."
        declared = (config.get("mispricing") or {}).get("model") or {}
        if not declared:
            return ("No model is declared, so this lane will REFUSE to assemble. It bets "
                    "on a claim about a fixture and needs a named person's method.")
        status = str(declared.get("status", "PAPER"))
        if status != "LIVE":
            return (f"{declared.get('name', 'the model')} is {status}: it evaluates every "
                    f"fixture and CANNOT SIZE ANYTHING. Only a named person promotes it, "
                    f"against a settled record.")
        promoted = str(declared.get("promoted_on") or "NOTHING RECORDED")
        return (f"{declared.get('name', 'the model')} is LIVE and may size. "
                f"Promoted on: {promoted}.")
    except Exception as error:  # noqa: BLE001 - a preflight that raises has failed its job
        return f"The model status could not be read ({type(error).__name__})."


def _rulebook_requirement() -> Requirement:
    """Whether anybody has read two books' settlement rules, and how far they got.

    Three states rather than present/absent, because "no store" and "a store that will not
    parse" send a person to opposite ends of the job — one to a rules page, one to a text
    editor — and "one book read" is neither.
    """

    from lib.rulebook import DISQUALIFYING, RulebookStore
    from lib.reaping import RULEBOOKS

    store = RulebookStore.load(RULEBOOKS)
    common = dict(
        lane=ARB, name="settlement rulebooks",
        unlocks="the arb lane's first gate; without it every candidate is INDETERMINATE",
        remedy="python rulebook.py --topics, then --template and --record",
        # NOT required, and the distinction is the one `DEGRADED` exists for. A lane with
        # no rulebook still runs, still finds candidates and still reports each one as
        # INDETERMINATE naming the two books whose rules need reading — which is the most
        # useful output this lane produces before anybody has read anything. What it cannot
        # do is reach READY. That is a lane seeing a fraction of its evidence, not a lane
        # that cannot start.
        required=False,
    )
    if not store.readable:
        return Requirement(status=UNREACHABLE,
                           detail=f"{RULEBOOKS} would not parse: {store.reason}", **common)
    if store.lost:
        return Requirement(status=NOT_CONFIGURED, detail=(
            f"the store has been written before and the file is gone "
            f"({store.status.describe()})"), **common)

    books = store.books()
    if len(books) < 2:
        return Requirement(status=NOT_CONFIGURED, detail=(
            f"{len(books)} book(s) recorded; a comparison needs two"), **common)

    covered = [
        (a, b) for index, a in enumerate(books) for b in books[index + 1:]
        if store.compare(a, b, "soccer/h2h").verdict == "COVERED"
    ]
    if not covered:
        return Requirement(status=CONFIGURED, detail=(
            f"{len(books)} book(s) recorded and no pair is covered on all "
            f"{len(DISQUALIFYING)} precondition(s) yet. Run "
            f"`python rulebook.py` to see what is outstanding"), **common)
    return Requirement(status=READY, detail=(
        f"{len(covered)} pair(s) fully read: "
        + "; ".join(f"{a} vs {b}" for a, b in covered)), **common)


def _arb_burn() -> str:
    """What this lane will spend a day, computed from the config actually in front of us.

    Printed BEFORE a key exists, which is the only moment it can change a decision. The
    alternative is finding out from a lane that stopped finding anything three weeks in,
    and an exhausted key is indistinguishable from a quiet market — which is the failure
    this whole file is written to prevent, arriving through the billing system instead of
    the network.
    """

    from connectors.oddsapi import credits_per_day, describe_burn

    try:
        from lib.reaping import CONFIG, load_config
        from run import REAP_CADENCES

        config, unreadable = load_config(CONFIG)
        if unreadable:
            return f"not computable — {CONFIG} would not parse ({unreadable})"
        settings = config.get("arb") or {}
        sports = len(settings.get("sports") or ())
        if not sports:
            return (f"no sports are configured in {CONFIG}, so nothing would be scanned "
                    f"and nothing would be spent")
        daily = credits_per_day(
            sports=sports,
            cadence_seconds=REAP_CADENCES["arb"],
            bookmakers=tuple(settings.get("bookmakers") or ()),
        )
        return describe_burn(daily)
    except Exception as error:  # noqa: BLE001 - an estimate that raises is not a preflight
        # UNKNOWN, never a reassuring number. A preflight that crashes computing a cost
        # has failed at the one job it has, and a silent 0.0 would read as free.
        return f"not computable ({type(error).__name__}: {error})"


def all_lanes(*, probe: bool = False) -> tuple[LaneReadiness, ...]:
    """One readiness per declared lane, including lanes nobody has described yet.

    This returned three hand-listed calls, so a fourth lane was simply ABSENT here — and
    `status.as_json` builds its `engines` list from this, which the operator dashboard
    turns into division cards. A lane could therefore be configured, assembled, scheduled
    and holding a ring-fence while having no card on the page at all. Absence is the worst
    of the available failures: there is nothing to notice.

    A lane with no readiness function gets a `LaneReadiness` that says so, carrying an
    unmet requirement so it reports BLOCKED rather than READY. An undescribed lane has not
    been established to have everything it needs; it has been established that nobody has
    said what it needs, and those must not render alike.
    """

    from lib.reaping import ALL_LANES, PARKED_LANES

    described = {
        "crypto": crypto_lane, "stocks": stocks_lane, "arb": arb_lane,
        "mispricing": mispricing_lane,
    }

    out: list[LaneReadiness] = []
    for lane in ALL_LANES:
        if lane in PARKED_LANES:
            # Its requirements are deliberately NOT evaluated. Probing a parked lane's
            # endpoint would put a credential nobody needs on a report of things to go and
            # do, and a red line against a lane that is not running is noise that teaches
            # a reader to skim the ones that are.
            out.append(LaneReadiness(
                lane, "Built and tested, and out of the rotation.",
                parked_because=PARKED_LANES[lane]))
            continue
        build = described.get(lane)
        if build is None:
            out.append(LaneReadiness(lane, (
                f"No preflight description exists for {lane!r}. What this lane needs "
                f"before it can read anything has not been written down, so nothing here "
                f"has been checked."
            ), (Requirement(
                lane=lane,
                name=f"a readiness description for {lane}",
                status=NOT_CONFIGURED,
                detail=f"add {lane}_lane() to lib/preflight and register it in all_lanes",
                unlocks="an honest answer about what this lane is missing",
                required=True,
            ),)))
            continue
        out.append(build(probe=probe))
    return tuple(out)


def report(lanes: Sequence[LaneReadiness]) -> str:
    lines: list[str] = []
    for lane in lanes:
        lines.append(lane.describe())
        lines.append("")

    lines.append("=" * 74)
    blocked = [l for l in lanes if l.status == BLOCKED]
    degraded = [l for l in lanes if l.status == DEGRADED]
    ready = [l for l in lanes if l.status == READY]
    parked = [l for l in lanes if l.status == PARKED]

    if parked:
        lines.append(f"PARKED:   {', '.join(l.lane for l in parked)} -- not running, and "
                     f"nothing here has been checked for them")
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
