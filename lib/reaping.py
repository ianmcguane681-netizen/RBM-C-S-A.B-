"""Assemble the three lanes from one config file and run them, without lying about gaps.

`python run.py --reap` is one command and three lanes, and the thing it must not do is the
thing every dashboard does: present a lane that was never configured beside a lane that
looked and found nothing, in the same list, in the same colour.

So assembly is a first-class result rather than a try/except. A lane arrives as one of:

    CONFIGURED       a reaper was built, and it will report its own harvest
    NOT_CONFIGURED   nothing was asked of it. It looked at nothing and found nothing
    UNREADABLE       something was asked of it and could not be read. Not the same
    REFUSED          the configuration was read and is not usable, and why

The whole file being unreadable refuses the run outright, exactly as `run.py` refuses when
the orchestrator state will not parse: proceeding would run every lane as though nothing had
been configured, which is a confident answer built out of a parse error.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from connectors import alpaca
from lib.ui_contract import SCHEMA_VERSION, serialise

CONFIGURED = "CONFIGURED"
NOT_CONFIGURED = "NOT_CONFIGURED"
UNREADABLE = "UNREADABLE"
REFUSED = "REFUSED"

CONFIG = Path("data/reapers.json")
SEEN = Path("data/seen-register.json")
LEDGER = Path("data/outcomes.json")
THESES = Path("data/theses.json")
BREAKER_DIR = Path("data")
KILL_SWITCH = Path("data/HALT")
#: Append-only run history. A record, never a source of truth — `LEDGER` stays the ledger.
JOURNAL = Path("data/journal.sqlite3")

#: Distinguishes "caller said nothing" from "caller said None", where None means *do not
#: journal at all*. A plain `= JOURNAL` default binds the path at import, which makes the
#: constant above unpatchable and sent a full test run's journal into the live `data/`.
_DEFAULT = object()

LANES = ("arb", "stocks", "crypto")

#: What a lane's ring-fence is denominated in when the config does not say, per lane,
#: because the answer is a fact about where the money goes rather than a house preference:
#: arb stakes at UK and Irish books in euro, stocks buys at a venue that quotes dollars.
#:
#: **One table, read by everything.** Until 2026-08-08 this default was written twice —
#: `breakers_for` said EUR and `assemble_stocks` said USD, for the same `currency` key on
#: the same lane — so an unset key made one number euros to every breaker limit and
#: dollars to the share arithmetic. `status.py` builds its breakers through the same
#: function, so a default passed in by each caller would have left the panel and the lane
#: free to disagree all over again.
LANE_CURRENCY = {"arb": "EUR", "stocks": alpaca.QUOTES_IN, "crypto": "USD"}


@dataclass(frozen=True, slots=True)
class Assembly:
    """One lane's readiness, and the reaper if there is one."""

    lane: str
    status: str
    reaper: Any = None
    reason: str = ""

    def describe(self) -> str:
        if self.status == NOT_CONFIGURED:
            return (f"NOT_CONFIGURED  [{self.lane}]\n"
                    f"  Nothing was asked of this lane. It did not look, so it has not "
                    f"reported that there is nothing to find.")
        if self.status == UNREADABLE:
            return (f"UNREADABLE  [{self.lane}]\n  {self.reason}\n"
                    f"  Something was asked of this lane and could not be read. That is "
                    f"not the same as nothing being asked.")
        if self.status == REFUSED:
            return f"REFUSED  [{self.lane}]\n  {self.reason}"
        return f"CONFIGURED  [{self.lane}]"


@dataclass(frozen=True, slots=True)
class Reaping:
    """Every lane's assembly, and every harvest from the ones that ran."""

    assemblies: tuple[Assembly, ...] = ()
    harvests: tuple[Any, ...] = field(default_factory=tuple)
    refusal: str = ""
    #: What settled since the last run, handed to each lane's breakers before it reaped.
    applications: tuple[Any, ...] = field(default_factory=tuple)
    #: Who is placing for each lane — the machine, or the owner.
    modes: tuple[Any, ...] = field(default_factory=tuple)
    #: What was actually submitted. Empty when nothing was, which is the usual case.
    placements: tuple[Any, ...] = field(default_factory=tuple)

    @property
    def ready(self) -> tuple[str, ...]:
        return tuple(a.lane for a in self.assemblies if a.status == CONFIGURED)

    @property
    def looked(self) -> bool:
        """Whether ANY configured lane actually looked.

        Assembling three lanes that all fail to reach their source is not a run. The
        caller needs to tell that apart from a run that found nothing, or a scheduler
        reads a broken pipeline as a quiet morning — every morning, indefinitely.
        """

        return any(h.status != "COULD_NOT_LOOK" for h in self.harvests)

    def describe(self) -> str:
        if self.refusal:
            return f"REFUSING TO REAP\n  {self.refusal}"

        lines = ["LANES"]
        lines += [f"  {a.describe()}" for a in self.assemblies]
        lines.append("")

        if self.modes:
            from lib.operating import describe_modes

            lines.append(describe_modes(self.modes))
            lines.append("")

        if self.applications:
            lines.append("OUTCOMES APPLIED BEFORE REAPING")
            lines += [f"  {a.describe()}" for a in self.applications]
            lines.append("")
        if not self.ready:
            lines.append(
                "No lane was configured, so NOTHING was looked at. This is not a report "
                "that there was nothing to find."
            )
            return "\n".join(lines)

        lines.append(f"HARVESTS from {len(self.ready)} lane(s): "
                     f"{', '.join(self.ready)}")
        lines.append("")
        for harvest in self.harvests:
            lines.append(harvest.describe())
            lines.append("")
        if self.placements:
            from lib.placing import describe_placements

            lines.append(describe_placements(self.placements))
            lines.append("")

        ready = [h for h in self.harvests if h.status == "READY"]
        placed = [p for p in self.placements if p.status == "PLACED"]
        if ready and placed:
            lines.append(f"{len(ready)} instruction(s) reached READY and {len(placed)} "
                         f"went in. MONEY HAS MOVED — see PLACING above.")
        elif ready:
            lines.append(f"{len(ready)} instruction(s) reached READY. NOTHING HAS BEEN "
                         f"PLACED, SIGNED OR SENT.")
        elif not self.looked:
            lines.append(
                "NO CONFIGURED LANE LOOKED. Every one of them failed to reach its source, "
                "so this run establishes nothing at all — it is not a quiet morning, it "
                "is a pipeline that did not run."
            )
        else:
            lines.append("Nothing reached READY. Every lane's reason is stated above.")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """The whole run for a reader, keeping the four different kinds of nothing apart.

        `describe()` distinguishes them in prose and a summarised JSON view would put them
        back together, so the top-level status names which one this was:

            REFUSED           the config would not parse; no lane was even assembled
            NOT_CONFIGURED    nothing was asked of any lane, so nothing looked
            COULD_NOT_LOOK    lanes were configured and every one failed to reach a source
            LOOKED            at least one lane actually reached its sources

        The last two are the pair that matters. A scheduler that reads COULD_NOT_LOOK as a
        quiet market reads a broken pipeline as a quiet market every morning, indefinitely.

        `placements` is carried whether or not anything went in. It is the only field here
        behind which money has already moved, and a UI rendering harvests without it would
        show READY beside "nothing has been placed" on a run that placed.
        """

        if self.refusal:
            status = "REFUSED"
        elif not self.ready:
            status = NOT_CONFIGURED
        elif not self.looked:
            status = "COULD_NOT_LOOK"
        else:
            status = "LOOKED"

        return {
            "schema_version": SCHEMA_VERSION,
            "status": status,
            "reason": self.refusal or None,
            "assemblies": [
                {"lane": item.lane, "status": item.status, "reason": item.reason or None}
                for item in self.assemblies
            ],
            "modes": [serialise(item) for item in self.modes],
            "applications": [serialise(item) for item in self.applications],
            "harvests": [serialise(item) for item in self.harvests],
            "placements": [serialise(item) for item in self.placements],
        }


def load_config(path: Path = CONFIG) -> tuple[dict, str]:
    """The config, or the reason there isn't one. An absent file is not a broken one."""

    if not path.is_file():
        return {}, ""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return {}, f"{type(error).__name__}: {error}"[:160]
    if not isinstance(payload, dict):
        return {}, f"{path} does not contain a JSON object"
    return payload, ""


def breakers_for(lane: str, settings: dict, *, directory: Path, kill_switch: Path):
    """The breakers a lane runs under, from that lane's slice of the config.

    The currency default comes from `LANE_CURRENCY` rather than this function, so the
    panel that describes a lane and the code that runs it cannot end up denominating the
    same balance differently. An unlisted lane falls back to EUR, which is a guess — but a
    lane that is not in that table is also not in `PLACERS`, so it cannot spend the money
    it would be guessing about.
    """

    from lib.breakers import Breakers, Ringfence
    from lib.outcomes import LEDGER, OutcomeLedger

    ring = Ringfence(
        lane, float(settings["balance"]),
        currency=str(settings.get("currency", LANE_CURRENCY.get(lane, "EUR"))),
        per_position_pct=float(settings.get("per_position_pct", 5.0)),
        daily_loss_pct=float(settings.get("daily_loss_pct", 3.0)),
        max_deployed_pct=float(settings.get("max_deployed_pct", 40.0)),
        max_concurrent_positions=int(settings.get("max_concurrent_positions", 8)),
    )
    # The ledger lives beside the breaker files, so the deployed-capital check can see what
    # is already out. Without it that check cannot be evaluated and blocks — which is right,
    # and would also mean no lane could ever place.
    return Breakers(ring, directory / f"breakers-{lane}.json", kill_switch=kill_switch,
                    positions=OutcomeLedger(directory / LEDGER.name))


def assemble_arb(settings: dict, *, directory: Path, kill_switch: Path) -> Assembly:
    from lib.arb import EquivalenceDeclaration
    from lib.seen import SeenRegister
    from lib.arb_reaper import StandingAuthority, build_arb_reaper

    grant = settings.get("authority") or {}
    if not grant:
        return Assembly("arb", REFUSED, reason=(
            "no standing authority is declared. A lane that mints its own authorisation "
            "is one nobody authorised."))

    try:
        # A bare string here would iterate into single characters and request eleven
        # bookmakers named "b", "e", "t"... The API would answer 200 with nothing in it,
        # so this refuses the lane rather than letting a typo become a quiet market.
        listed = settings.get("bookmakers") or ()
        if isinstance(listed, str):
            raise ValueError(
                'bookmakers must be a JSON list such as ["skybet", "paddypower"], not '
                'one string'
            )
        bookmakers = tuple(str(book) for book in listed)
        authority = StandingAuthority(
            declared_by=str(grant["declared_by"]),
            reasoning=str(grant["reasoning"]),
            considered=tuple(grant.get("considered", ())),
            expires_at=str(grant["expires_at"]),
            max_exposure=float(grant["max_exposure"]),
            declared_at=str(grant.get("declared_at", "")),
            currency=str(grant.get("currency", "EUR")),
        )
        declarations = {
            key: EquivalenceDeclaration(
                str(row["declared_by"]), str(row["reasoning"]),
                tuple(row.get("scenarios_checked", ())),
            )
            for key, row in (settings.get("declarations") or {}).items()
        }
        breakers = breakers_for("arb", settings, directory=directory,
                             kill_switch=kill_switch)
    except (KeyError, TypeError, ValueError) as error:
        return Assembly("arb", REFUSED, reason=f"{type(error).__name__}: {error}"[:200])

    if not breakers.readable:
        return Assembly("arb", UNREADABLE, reason=(
            f"the breaker state would not parse ({breakers.reason}). An unknown daily "
            f"loss is not a satisfied daily loss limit."))

    return Assembly("arb", CONFIGURED, build_arb_reaper(
        register=SeenRegister.load(directory / SEEN.name),
        authority=authority, breakers=breakers,
        sports=tuple(settings.get("sports", ())), declarations=declarations,
        bookmakers=bookmakers,
        prefer_distinct_books=bool(settings.get("prefer_distinct_books", True)),
    ))


def assemble_stocks(settings: dict, *, directory: Path, kill_switch: Path,
                    theses_path: Path) -> Assembly:
    from connectors import alpaca
    from lib.seen import SeenRegister
    from lib.stocks_reaper import build_stocks_reaper
    from lib.thesis import ThesisRegister

    theses = ThesisRegister(theses_path)
    if not theses.readable:
        return Assembly("stocks", UNREADABLE, reason=(
            f"the thesis register would not parse ({theses.reason}). What is authorised "
            f"is unknown rather than nothing."))

    try:
        breakers = breakers_for("stocks", settings, directory=directory,
                             kill_switch=kill_switch)
    except (KeyError, TypeError, ValueError) as error:
        return Assembly("stocks", REFUSED, reason=f"{type(error).__name__}: {error}"[:200])

    if not breakers.readable:
        return Assembly("stocks", UNREADABLE, reason=(
            f"the breaker state would not parse ({breakers.reason})."))

    # Read off the ring-fence rather than the config a second time. One number funds this
    # lane and that same number sizes its orders, so the two must be in the same units;
    # asking the settings dict twice is how they came to disagree in the first place.
    currency = breakers.ringfence.currency
    if currency != alpaca.QUOTES_IN:
        # Not a conversion, because there is no rate here and an FX rate is itself a price
        # that goes stale — see docs/pricing-design.md. Sizing would be wrong by the rate
        # in whichever direction the rate happened to sit, so the lane stops instead.
        return Assembly("stocks", REFUSED, reason=(
            f"the ring-fence is denominated in {currency} and Alpaca quotes in "
            f"{alpaca.QUOTES_IN}, so sizing would divide {currency} by a "
            f"{alpaca.QUOTES_IN} ask and buy the wrong number of shares. Nothing here "
            f"converts between them. Set \"currency\": \"{alpaca.QUOTES_IN}\" on the "
            f"stocks lane in the config and fund its ring-fence in {alpaca.QUOTES_IN}."))

    return Assembly("stocks", CONFIGURED, build_stocks_reaper(
        register=SeenRegister.load(directory / SEEN.name),
        watchlist=tuple(settings.get("watchlist", ())), theses=theses, breakers=breakers,
        free_balance=float(settings.get("free_balance", settings["balance"])),
        currency=currency,
    ))


def assemble_crypto(settings: dict, *, directory: Path, kill_switch: Path,
                    theses_path: Path) -> Assembly:
    from lib.crypto_reaper import build_crypto_reaper
    from lib.seen import SeenRegister
    from lib.thesis import ThesisRegister

    wallet = str(settings.get("wallet", "")).strip()
    if not wallet:
        return Assembly("crypto", REFUSED, reason=(
            "no wallet address is configured, so there is nobody to build a transaction "
            "for."))

    theses = ThesisRegister(theses_path)
    if not theses.readable:
        return Assembly("crypto", UNREADABLE, reason=(
            f"the thesis register would not parse ({theses.reason}). What is authorised "
            f"is unknown rather than nothing."))

    try:
        breakers = breakers_for("crypto", settings, directory=directory,
                             kill_switch=kill_switch)
        client = _chain_client(settings)
    except (KeyError, TypeError, ValueError) as error:
        return Assembly("crypto", REFUSED, reason=f"{type(error).__name__}: {error}"[:200])

    if client is None:
        return Assembly("crypto", NOT_CONFIGURED, reason="no chain provider is available")
    if not breakers.readable:
        return Assembly("crypto", UNREADABLE, reason=(
            f"the breaker state would not parse ({breakers.reason})."))

    return Assembly("crypto", CONFIGURED, build_crypto_reaper(
        register=SeenRegister.load(directory / SEEN.name),
        watchlist=tuple(settings.get("watchlist", ())), theses=theses, breakers=breakers,
        wallet=wallet, client=client,
        quote_name=str(settings.get("quote_name", "USDC")),
    ))


def _chain_client(settings: dict):
    import os

    from connectors.chain import ChainClient, best_for

    try:
        provider = best_for(str(settings.get("task", "state")),
                            quicknode_url=os.environ.get("QUICKNODE_ETHEREUM_URL", ""))
    except Exception:  # noqa: BLE001 - no provider is NOT_CONFIGURED, not a crash
        return None
    return ChainClient(provider)


def assemble(
    config: dict,
    *,
    directory: Path = BREAKER_DIR,
    kill_switch: Path = KILL_SWITCH,
    theses_path: Path = THESES,
) -> tuple[Assembly, ...]:
    """One assembly per lane in `LANES`, in a stable order, whatever that list holds.

    More lanes than these three are planned, so the loop is written against `LANES`
    rather than against the number three, and a lane listed without a builder is
    REPORTED rather than raised. `builders[lane]` on an unknown key is a `KeyError` out
    of the middle of an assembly pass — every OTHER lane's result is lost with it, so
    the run reports nothing at all because one lane was half-added.
    """

    builders = {
        "arb": lambda s: assemble_arb(s, directory=directory, kill_switch=kill_switch),
        "stocks": lambda s: assemble_stocks(s, directory=directory,
                                            kill_switch=kill_switch,
                                            theses_path=theses_path),
        "crypto": lambda s: assemble_crypto(s, directory=directory,
                                            kill_switch=kill_switch,
                                            theses_path=theses_path),
    }

    out: list[Assembly] = []
    for lane in LANES:
        settings = config.get(lane) or {}
        if not settings or not settings.get("enabled", True):
            out.append(Assembly(lane, NOT_CONFIGURED))
            continue
        build = builders.get(lane)
        if build is None:
            out.append(Assembly(lane, REFUSED, reason=(
                f"{lane!r} is a declared lane with no builder in lib/reaping.assemble. "
                f"It is configured and enabled, so this is half an addition rather than "
                f"a lane nobody asked for: write its assemble_{lane}() before running it.")))
            continue
        out.append(build(settings))
    return tuple(out)


def apply_outcomes(assemblies: Sequence[Assembly], ledger: Any) -> tuple[Any, ...]:
    """Tell every lane's breakers what settled, before that lane looks at anything.

    Applied to the reaper's OWN `Breakers` object rather than to a freshly loaded one.
    Building a second instance would write the trip to disk and leave the reaper checking
    the in-memory copy it loaded at assembly time, which is armed — the breaker would trip
    and permit the position in the same run.

    A lane holding settled outcomes with no breakers to apply them to is reported rather
    than skipped. Silence there would mean a lane's losses reach nothing at all while the
    report shows two tidy lines about the lanes that worked.
    """

    from lib.outcomes import SETTLED, Application, apply_to_breakers

    applications: list[Any] = []
    configured = set()
    for assembly in assemblies:
        if assembly.status != CONFIGURED or assembly.reaper is None:
            continue
        configured.add(assembly.lane)
        applications.append(
            apply_to_breakers(ledger, assembly.reaper.breakers, lane=assembly.lane))

    if getattr(ledger, "readable", False):
        orphaned = {p.lane for p in ledger.positions
                    if p.status == SETTLED and not p.applied_to_breakers} - configured
        for lane in sorted(orphaned):
            applications.append(Application(lane, refusal=(
                f"{lane} has settled outcomes and no configured breakers, so its results "
                f"reach nothing. Enable the lane in the reaper config or its losses go "
                f"uncounted.")))
    return tuple(applications)


def reap(
    *,
    lanes: Sequence[str] | None = None,
    config_path: Path = CONFIG,
    ledger_path: Path = LEDGER,
    directory: Path = BREAKER_DIR,
    kill_switch: Path = KILL_SWITCH,
    theses_path: Path = THESES,
    place: bool = True,
    brokers: Any = None,
    journal_path: Any = _DEFAULT,
) -> Reaping:
    """Assemble, apply outcomes, then run every selected lane.

    Applying comes FIRST and that ordering is the point. A breaker that has not been told
    about yesterday's four losses will permit a fifth position perfectly happily, which is
    the failure the breakers exist to prevent and the reason `lib/outcomes` was written.
    """

    from lib.operating import modes_for
    from lib.outcomes import OutcomeLedger

    config, unreadable = load_config(config_path)
    if unreadable:
        return Reaping(refusal=(
            f"{config_path} could not be read ({unreadable}). Running anyway would treat "
            f"every lane as unconfigured, which is a confident answer assembled out of a "
            f"parse error."))

    selected = tuple(lanes) if lanes is not None else LANES
    unknown = set(selected) - set(LANES)
    if unknown:
        return Reaping(refusal=(
            f"unknown reaper lane(s): {', '.join(sorted(unknown))}. Choose from "
            f"{', '.join(LANES)}."))

    assemblies = tuple(
        assembly for assembly in assemble(
            config, directory=directory, kill_switch=kill_switch,
            theses_path=theses_path
        ) if assembly.lane in selected
    )

    ledger = OutcomeLedger(ledger_path)
    applications = apply_outcomes(assemblies, ledger)
    modes = {m.lane: m for m in modes_for(selected, config, directory=directory,
                                          ledger=ledger)}

    harvests: list[Any] = []
    for assembly in assemblies:
        if assembly.status != CONFIGURED:
            continue
        if not modes[assembly.lane].may_reap:
            # HALTED, and that is the one mode which stops the research as well as the
            # placing. The lane is not silently absent — its mode is printed above with
            # the reason, which is the distinction between "did not run" and "found
            # nothing". Owner-operating deliberately does NOT come here: taking the wheel
            # must not also mean going blind.
            continue
        # A lane whose breaker just tripped during application still runs. Its own breaker
        # check refuses it, and reading the refusal with its reason beats the lane silently
        # vanishing from the report.
        harvests.extend(assembly.reaper.reap())
    placements = _place(harvests, modes, ledger, brokers) if place else ()
    reaping = Reaping(assemblies, tuple(harvests), applications=applications,
                      modes=tuple(modes[lane] for lane in selected),
                      placements=placements)

    # Recorded AFTER the run, and unable to affect it. Everything a reap produces was
    # printed once and lost, so "what did the arb lane find on Tuesday" had no answer and
    # neither did "has any lane produced anything real" — which is the question the plan
    # turns on. `Journal.record` never raises: a reap that placed an order and then could
    # not write its diary has still placed the order, and losing the run over the note
    # would fail in the expensive direction.
    # Resolved here rather than in the signature, so JOURNAL is read at call time.
    destination = JOURNAL if journal_path is _DEFAULT else journal_path
    if destination is not None:
        from lib.journal import Journal

        Journal(destination).record(
            reaping, lane=lanes[0] if lanes and len(lanes) == 1 else "",
            dry_run=not place,
        )
    return reaping


def _place(harvests, modes, ledger, brokers) -> tuple[Any, ...]:
    """Submit what the mode permits. Everything else is reported, not silently dropped.

    A harvest that was not placed still produces a `Placement` saying why, because "your
    lane is owner-operating so this is waiting for you" and "nothing reached READY" are
    different facts and only one of them needs you.
    """

    from lib.placing import broker_for, place_harvest

    supplied = brokers or {}
    out = []
    for harvest in harvests:
        if harvest.status != "READY":
            continue
        # `broker_for` rather than an `if lane == "stocks"` branch here: which lanes have a
        # venue is one fact, and it belongs beside the placer that uses it rather than in
        # the loop that iterates them.
        broker = supplied.get(harvest.lane) or broker_for(harvest.lane)
        thesis = getattr(harvest.permission, "subject", "")
        out.append(place_harvest(
            harvest, mode=modes[harvest.lane], ledger=ledger, broker=broker,
            thesis_declared_at=str(thesis)))
    return tuple(out)
