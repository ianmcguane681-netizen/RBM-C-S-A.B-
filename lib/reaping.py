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
from typing import Any

CONFIGURED = "CONFIGURED"
NOT_CONFIGURED = "NOT_CONFIGURED"
UNREADABLE = "UNREADABLE"
REFUSED = "REFUSED"

CONFIG = Path("data/reapers.json")
THESES = Path("data/theses.json")
BREAKER_DIR = Path("data")
KILL_SWITCH = Path("data/HALT")

LANES = ("arb", "stocks", "crypto")


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
        ready = [h for h in self.harvests if h.status == "READY"]
        if ready:
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


def _breakers(lane: str, settings: dict, *, directory: Path, kill_switch: Path):
    from lib.breakers import Breakers, Ringfence

    ring = Ringfence(
        lane, float(settings["balance"]),
        currency=str(settings.get("currency", "EUR")),
        per_position_pct=float(settings.get("per_position_pct", 5.0)),
        daily_loss_pct=float(settings.get("daily_loss_pct", 3.0)),
    )
    return Breakers(ring, directory / f"breakers-{lane}.json", kill_switch=kill_switch)


def assemble_arb(settings: dict, *, directory: Path, kill_switch: Path) -> Assembly:
    from lib.arb import EquivalenceDeclaration
    from lib.arb_reaper import StandingAuthority, build_arb_reaper

    grant = settings.get("authority") or {}
    if not grant:
        return Assembly("arb", REFUSED, reason=(
            "no standing authority is declared. A lane that mints its own authorisation "
            "is one nobody authorised."))

    try:
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
        breakers = _breakers("arb", settings, directory=directory,
                             kill_switch=kill_switch)
    except (KeyError, TypeError, ValueError) as error:
        return Assembly("arb", REFUSED, reason=f"{type(error).__name__}: {error}"[:200])

    if not breakers.readable:
        return Assembly("arb", UNREADABLE, reason=(
            f"the breaker state would not parse ({breakers.reason}). An unknown daily "
            f"loss is not a satisfied daily loss limit."))

    return Assembly("arb", CONFIGURED, build_arb_reaper(
        authority=authority, breakers=breakers,
        sports=tuple(settings.get("sports", ())), declarations=declarations,
        prefer_distinct_books=bool(settings.get("prefer_distinct_books", True)),
    ))


def assemble_stocks(settings: dict, *, directory: Path, kill_switch: Path,
                    theses_path: Path) -> Assembly:
    from lib.stocks_reaper import build_stocks_reaper
    from lib.thesis import ThesisRegister

    theses = ThesisRegister(theses_path)
    if not theses.readable:
        return Assembly("stocks", UNREADABLE, reason=(
            f"the thesis register would not parse ({theses.reason}). What is authorised "
            f"is unknown rather than nothing."))

    try:
        breakers = _breakers("stocks", settings, directory=directory,
                             kill_switch=kill_switch)
    except (KeyError, TypeError, ValueError) as error:
        return Assembly("stocks", REFUSED, reason=f"{type(error).__name__}: {error}"[:200])

    if not breakers.readable:
        return Assembly("stocks", UNREADABLE, reason=(
            f"the breaker state would not parse ({breakers.reason})."))

    return Assembly("stocks", CONFIGURED, build_stocks_reaper(
        watchlist=tuple(settings.get("watchlist", ())), theses=theses, breakers=breakers,
        free_balance=float(settings.get("free_balance", settings["balance"])),
        currency=str(settings.get("currency", "USD")),
    ))


def assemble_crypto(settings: dict, *, directory: Path, kill_switch: Path,
                    theses_path: Path) -> Assembly:
    from lib.crypto_reaper import build_crypto_reaper
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
        breakers = _breakers("crypto", settings, directory=directory,
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
    """One assembly per lane, always all three, in a stable order."""

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
        out.append(builders[lane](settings))
    return tuple(out)


def reap(
    *,
    config_path: Path = CONFIG,
    directory: Path = BREAKER_DIR,
    kill_switch: Path = KILL_SWITCH,
    theses_path: Path = THESES,
) -> Reaping:
    """Assemble, run every configured lane, and keep the ones that could not look."""

    config, unreadable = load_config(config_path)
    if unreadable:
        return Reaping(refusal=(
            f"{config_path} could not be read ({unreadable}). Running anyway would treat "
            f"every lane as unconfigured, which is a confident answer assembled out of a "
            f"parse error."))

    assemblies = assemble(config, directory=directory, kill_switch=kill_switch,
                          theses_path=theses_path)

    harvests: list[Any] = []
    for assembly in assemblies:
        if assembly.status != CONFIGURED:
            continue
        harvests.extend(assembly.reaper.reap())
    return Reaping(assemblies, tuple(harvests))
