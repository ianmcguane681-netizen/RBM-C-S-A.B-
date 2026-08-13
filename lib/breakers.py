"""What stops an autonomous lane, before anything is built that can act without asking.

The failure mode of an unattended system is not that it makes a bad decision. It is that it
makes **the same bad decision four hundred times before anybody looks**. Rate of error
matters more than probability of error once nobody is watching, and every control here is
aimed at the rate.

Built first, deliberately. The thing that stops it should exist before the thing that acts.

## Six controls

    ring-fence          a balance the lane may lose and no more
    per-position cap    no single position above a share of that balance
    daily loss limit    down this much today and it stops, without being asked
    consecutive losses  this many in a row and it halts
    sanity bound        an "edge" above this is a data error, not an opportunity
    kill switch         one file, checked every time, halts everything

## Three rules that make them worth having

**A breaker that cannot be evaluated TRIPS.** Fail closed. If the day's profit and loss
cannot be read, the daily loss limit has not been satisfied — it is unknown, and an
unknown limit is not a limit. Everywhere else in this repository an unreadable value is
reported rather than assumed; here it also stops things, because the cost of continuing
wrongly is unbounded and the cost of stopping wrongly is a delay.

**A tripped breaker does not reset itself.** No timer, no midnight rollover. A strategy that
lost five in a row and resumed at 00:00 because a clock ticked has learned nothing and the
sixth loss is on its way. Resetting is a human act and it is recorded with a reason.

**The kill switch is a file.** Not a flag, not an environment variable, not an API call.
`data/HALT` — anything can create it: a phone, a cron job, another program, you at 3am with
no terminal. It is checked before every action and its presence is sufficient. The simplest
possible mechanism, because it is the one that has to work when everything else has not.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from guards.human_acts import AUTOMATION_PREFIXES

ARMED = "ARMED"
TRIPPED = "TRIPPED"
HALTED = "HALTED"

PERMITTED = "PERMITTED"
BLOCKED = "BLOCKED"

#: One file. Anything can create it and its presence is sufficient.
KILL_SWITCH = Path("data/HALT")

#: An edge larger than this is very probably a stale price, a mismatched fixture or a
#: decimal in the wrong place. Real ones are small; large ones are data errors, and acting
#: on one is how a system loses money quickly while believing it is winning.
DEFAULT_SANITY_EDGE_PCT = 15.0


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class Ringfence:
    """A balance a lane may lose, and the limits it operates within."""

    lane: str
    starting_balance: float
    currency: str = "EUR"
    per_position_pct: float = 5.0
    daily_loss_pct: float = 3.0
    max_consecutive_losses: int = 4
    sanity_edge_pct: float = DEFAULT_SANITY_EDGE_PCT
    #: How much of the ring-fence may be OUT AT ONCE, across every live position.
    #:
    #: The per-position cap does not bound this and it was never meant to. Twenty
    #: positions at 5% is the whole ring-fence deployed, and for a lane whose positions
    #: settle days later — a Saturday's football, a stock held over a weekend — that is the
    #: ordinary state of a busy week rather than a pathological one. The daily loss limit
    #: cannot see it either, because it is computed from SETTLED outcomes and none of these
    #: have settled.
    max_deployed_pct: float = 40.0
    #: A blunter instrument for the same failure, and it catches what a percentage misses
    #: when the positions are individually small.
    max_concurrent_positions: int = 8

    def __post_init__(self) -> None:
        if self.starting_balance <= 0:
            raise ValueError("a ring-fence needs a positive balance")
        for name in ("per_position_pct", "daily_loss_pct", "max_deployed_pct"):
            if not 0 < getattr(self, name) <= 100:
                raise ValueError(f"{name} must be between 0 and 100")
        if self.max_consecutive_losses < 1:
            raise ValueError("max_consecutive_losses must be at least 1")
        if self.max_concurrent_positions < 1:
            raise ValueError("max_concurrent_positions must be at least 1")
        if self.per_position_pct > self.max_deployed_pct:
            raise ValueError(
                f"per_position_pct {self.per_position_pct} exceeds max_deployed_pct "
                f"{self.max_deployed_pct}: a single position would breach the total cap, "
                f"so the lane could never place anything"
            )

    @property
    def per_position_limit(self) -> float:
        return self.starting_balance * self.per_position_pct / 100.0

    @property
    def daily_loss_limit(self) -> float:
        return self.starting_balance * self.daily_loss_pct / 100.0

    @property
    def deployed_limit(self) -> float:
        return self.starting_balance * self.max_deployed_pct / 100.0


@dataclass(frozen=True, slots=True)
class Outcome:
    """One settled result. Losses are negative."""

    lane: str
    at: str
    profit: float
    reference: str = ""


@dataclass(frozen=True, slots=True)
class BreakerState:
    lane: str
    status: str = ARMED
    tripped_by: str = ""
    tripped_at: str = ""
    reason: str = ""

    @property
    def is_armed(self) -> bool:
        return self.status == ARMED


@dataclass(frozen=True, slots=True)
class Check:
    name: str
    verdict: str
    detail: str

    def describe(self) -> str:
        mark = {PERMITTED: "  ok  ", BLOCKED: " STOP "}[self.verdict]
        return f"[{mark}] {self.name}\n         {self.detail}"


@dataclass(frozen=True, slots=True)
class Decision:
    verdict: str
    lane: str
    checks: tuple[Check, ...] = ()

    @property
    def blocked_by(self) -> tuple[str, ...]:
        return tuple(c.name for c in self.checks if c.verdict == BLOCKED)

    def describe(self) -> str:
        lines = [f"{self.verdict}  [{self.lane}]", ""]
        lines += [c.describe() for c in self.checks]
        if self.verdict == BLOCKED:
            lines.append("")
            lines.append(
                f"  Blocked by: {', '.join(self.blocked_by)}. Nothing was placed. A tripped "
                f"breaker does not reset itself — clearing it is a human act and is "
                f"recorded with a reason."
            )
        return "\n".join(lines)


class Breakers:
    """Every control, checked together, failing closed."""

    def __init__(self, ringfence: Ringfence, path: str | Path,
                 *, kill_switch: str | Path = KILL_SWITCH, positions: Any = None) -> None:
        self.ringfence = ringfence
        self.path = Path(path)
        self.kill_switch = Path(kill_switch)
        #: Anything exposing `unsettled_exposure(lane)` and `live(lane)` — in practice a
        #: `lib.outcomes.OutcomeLedger`. Absent, the deployed-capital check cannot be
        #: evaluated and therefore BLOCKS: an unknown total is not a total within limits,
        #: and this is the one limit that stands between a lane and its whole ring-fence.
        self.positions = positions
        self.outcomes: list[Outcome] = []
        self.state = BreakerState(ringfence.lane)
        self.readable = True
        self.reason = ""

        if self.path.is_file():
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8"))
                self.outcomes = [Outcome(**o) for o in payload.get("outcomes", [])]
                self.state = BreakerState(**payload.get("state", {"lane": ringfence.lane}))
            except (OSError, ValueError, TypeError) as error:
                self.readable = False
                self.reason = f"{type(error).__name__}: {error}"[:120]

    # -- measurements -----------------------------------------------------------------

    def profit_today(self) -> float:
        today = _today()
        return sum(o.profit for o in self.outcomes if o.at.startswith(today))

    def consecutive_losses(self) -> int:
        run = 0
        for outcome in reversed(self.outcomes):
            if outcome.profit < 0:
                run += 1
            else:
                break
        return run

    @property
    def killed(self) -> bool:
        return self.kill_switch.exists()

    # -- the check --------------------------------------------------------------------

    def check(self, *, proposed_size: float = 0.0, claimed_edge_pct: float = 0.0) -> Decision:
        """Every control, every time. Unreadable state blocks rather than passing."""

        checks: list[Check] = []

        if self.killed:
            checks.append(Check(
                "kill switch", BLOCKED,
                f"{self.kill_switch} exists. Its presence is sufficient and no other "
                f"condition is consulted. Delete it to resume.",
            ))
            return Decision(BLOCKED, self.ringfence.lane, tuple(checks))
        checks.append(Check("kill switch", PERMITTED, f"{self.kill_switch} absent"))

        if not self.readable:
            # Fail closed. An unreadable history means the daily loss and the losing run
            # are UNKNOWN, and an unknown limit is not a limit.
            checks.append(Check(
                "breaker state", BLOCKED,
                f"could not be read ({self.reason}). The daily loss and the losing run are "
                f"therefore unknown, and an unknown limit is not a limit.",
            ))
            return Decision(BLOCKED, self.ringfence.lane, tuple(checks))
        checks.append(Check("breaker state", PERMITTED,
                            f"{len(self.outcomes)} recorded outcome(s)"))

        if self.state.status != ARMED:
            checks.append(Check(
                "previously tripped", BLOCKED,
                f"{self.state.status} since {self.state.tripped_at} "
                f"({self.state.tripped_by}): {self.state.reason}. It does not reset itself.",
            ))
            return Decision(BLOCKED, self.ringfence.lane, tuple(checks))
        checks.append(Check("previously tripped", PERMITTED, "armed"))

        today = self.profit_today()
        limit = self.ringfence.daily_loss_limit
        if today <= -limit:
            checks.append(Check(
                "daily loss limit", BLOCKED,
                f"{today:,.2f} today against a limit of -{limit:,.2f} "
                f"({self.ringfence.daily_loss_pct:.1f}% of the ring-fence).",
            ))
        else:
            checks.append(Check("daily loss limit", PERMITTED,
                                f"{today:,.2f} today, limit -{limit:,.2f}"))

        run = self.consecutive_losses()
        if run >= self.ringfence.max_consecutive_losses:
            checks.append(Check(
                "consecutive losses", BLOCKED,
                f"{run} in a row against a limit of "
                f"{self.ringfence.max_consecutive_losses}. Something is wrong with the "
                f"reasoning rather than with the luck.",
            ))
        else:
            checks.append(Check("consecutive losses", PERMITTED,
                                f"{run} in a row, limit "
                                f"{self.ringfence.max_consecutive_losses}"))

        if proposed_size <= 0:
            checks.append(Check(
                "position size", BLOCKED,
                "no size was proposed, so it cannot be checked against the cap. An "
                "unchecked size is not a permitted one.",
            ))
        elif proposed_size > self.ringfence.per_position_limit:
            checks.append(Check(
                "position size", BLOCKED,
                f"{proposed_size:,.2f} against a cap of "
                f"{self.ringfence.per_position_limit:,.2f} "
                f"({self.ringfence.per_position_pct:.1f}% of the ring-fence).",
            ))
        else:
            checks.append(Check("position size", PERMITTED,
                                f"{proposed_size:,.2f} within "
                                f"{self.ringfence.per_position_limit:,.2f}"))

        checks.extend(self._deployment_checks(proposed_size))

        if claimed_edge_pct > self.ringfence.sanity_edge_pct:
            checks.append(Check(
                "sanity bound", BLOCKED,
                f"a claimed edge of {claimed_edge_pct:.2f}% exceeds "
                f"{self.ringfence.sanity_edge_pct:.2f}%. An edge that size is very "
                f"probably a stale price, a mismatched fixture or a misplaced decimal. "
                f"Real ones are small.",
            ))
        else:
            checks.append(Check("sanity bound", PERMITTED,
                                f"claimed edge {claimed_edge_pct:.2f}%"))

        blocked = any(c.verdict == BLOCKED for c in checks)
        return Decision(BLOCKED if blocked else PERMITTED,
                        self.ringfence.lane, tuple(checks))

    def _deployment_checks(self, proposed_size: float) -> list[Check]:
        """What is already out, which the per-position cap has never bounded.

        Fails closed on an absent or unreadable ledger, for the usual reason: an unknown
        deployed total is not a deployed total within limits, and the cost of being wrong
        here is the whole ring-fence rather than one position.
        """

        if self.positions is None or not getattr(self.positions, "readable", False):
            detail = ("no readable record of open positions is attached, so how much is "
                      "ALREADY out cannot be established. The per-position cap does not "
                      "bound the total — twenty positions at 5% is the whole ring-fence — "
                      "so an unknown total blocks rather than passes.")
            return [Check("deployed capital", BLOCKED, detail),
                    Check("concurrent positions", BLOCKED, detail)]

        lane = self.ringfence.lane
        already = float(self.positions.unsettled_exposure(lane))
        limit = self.ringfence.deployed_limit
        out = []

        if already + max(proposed_size, 0.0) > limit:
            out.append(Check(
                "deployed capital", BLOCKED,
                f"{already:,.2f} is already out and this would make it "
                f"{already + proposed_size:,.2f}, against a cap of {limit:,.2f} "
                f"({self.ringfence.max_deployed_pct:.1f}% of the ring-fence). Settling "
                f"what is open is what frees this, not waiting.",
            ))
        else:
            out.append(Check("deployed capital", PERMITTED,
                             f"{already:,.2f} out, {already + proposed_size:,.2f} after "
                             f"this, limit {limit:,.2f}"))

        live = len(self.positions.live(lane))
        if live >= self.ringfence.max_concurrent_positions:
            out.append(Check(
                "concurrent positions", BLOCKED,
                f"{live} already live against a limit of "
                f"{self.ringfence.max_concurrent_positions}. Small positions do not "
                f"breach the cash cap and still add up to a lane with no attention left "
                f"for any of them.",
            ))
        else:
            out.append(Check("concurrent positions", PERMITTED,
                             f"{live} live, limit "
                             f"{self.ringfence.max_concurrent_positions}"))
        return out

    # -- recording --------------------------------------------------------------------

    def record(self, profit: float, reference: str = "") -> BreakerState:
        """Log a settled outcome and trip if it crosses a limit."""

        if not self.readable:
            raise RuntimeError("refusing to write breaker state that could not be read")
        self.outcomes.append(Outcome(self.ringfence.lane, _now(), profit, reference))

        if self.profit_today() <= -self.ringfence.daily_loss_limit:
            self.state = BreakerState(
                self.ringfence.lane, TRIPPED, "daily loss limit", _now(),
                f"{self.profit_today():,.2f} today against "
                f"-{self.ringfence.daily_loss_limit:,.2f}",
            )
        elif self.consecutive_losses() >= self.ringfence.max_consecutive_losses:
            self.state = BreakerState(
                self.ringfence.lane, TRIPPED, "consecutive losses", _now(),
                f"{self.consecutive_losses()} in a row",
            )
        return self.state

    def reset(self, by: str, reason: str) -> BreakerState:
        """Re-arm. A human act, recorded, and never done by a clock.

        A strategy that lost four in a row and resumed at midnight because a timer expired
        has learned nothing, and the fifth loss is already on its way.
        """

        author = by.strip().lower()
        if not author or any(author.startswith(p) for p in AUTOMATION_PREFIXES):
            raise ValueError(
                f"{by!r} cannot reset a breaker. It tripped because something was wrong, "
                f"and deciding it is now right is exactly the judgement automation must "
                f"not make about its own halt."
            )
        if not reason.strip():
            raise ValueError("a reset needs a stated reason")
        self.state = BreakerState(self.ringfence.lane, ARMED,
                                  reason=f"reset by {by}: {reason}")
        return self.state

    def halt(self, reason: str) -> None:
        """Create the kill switch. Anything may call this; only a person removes it."""

        self.kill_switch.parent.mkdir(parents=True, exist_ok=True)
        self.kill_switch.write_text(f"{_now()}  {reason}\n", encoding="utf-8")

    def save(self) -> None:
        if not self.readable:
            raise RuntimeError("refusing to overwrite breaker state that could not be read")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({
            "outcomes": [asdict(o) for o in self.outcomes],
            "state": asdict(self.state),
        }, indent=2) + "\n", encoding="utf-8")
