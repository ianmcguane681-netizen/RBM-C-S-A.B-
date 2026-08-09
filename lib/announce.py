"""What in a run is worth a person's phone, and telling each of those things once.

`lib/notify` can send a message and says honestly what happened to it. It does not know
what is worth sending, and that is the whole of the problem this module solves: a lane that
reaches READY on a cadence produces the same true statement every run, so wiring `send()`
straight into the reapers would buzz a phone every eight hours about one standing arb. The
reader stops looking, and then misses the one that mattered — a signal still present, still
correct, and carrying no information. That is this repository's founding defect wearing its
politest disguise.

So the judgement lives here, and it has four outcomes:

    ANNOUNCED       a message was built, sent, and the service acknowledged it
    ALREADY_TOLD    worth telling, and you were told inside the repeat window
    UNTOLD          worth telling, and the telling did not happen — carrying which of
                    `lib/notify`'s delivery failures it was
    NOT_CONFIGURED  there is no channel. Nobody was told and nothing failed

`ALREADY_TOLD` is a suppression, every suppression is a small silence, and silence is the
thing this repository distrusts most — so it is bounded rather than permanent.
`REPEAT_AFTER_SECONDS` re-tells a standing opportunity instead of deciding on your behalf
that you have heard enough about it, which is `lib/seen`'s argument applied to messaging:
an opportunity that is still there is still real, and a repeat is information, not noise.

## The memory fails toward telling, and that inverts the usual rule

`CLAUDE.md` says fail toward stopping: an unreadable limit is not a satisfied limit, and
where an error could go either way, halt rather than continue. That rule is about *money
moving*. The thing that can fail here is the record of what you have already been told, and
suppressing on a lost record means an opportunity nobody ever hears about — an invisible
failure, which is the expensive direction for a notifier.

So an unreadable memory dedupes **nothing**. You may be told twice, which you can see and
which costs a moment; you are never told nothing, which you cannot see at all. The two
rules agree in what they are for: choose the failure a person will notice.

## Nothing here raises

A messaging fault must not take a lane down. Every path returns an `Announcement`, a
formatter that blows up becomes `UNTOLD` with the exception in it, and a memory that will
not write is a message already sent rather than a run that crashed after sending it.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from lib import notify

ANNOUNCED = "ANNOUNCED"
ALREADY_TOLD = "ALREADY_TOLD"
UNTOLD = "UNTOLD"
NOT_CONFIGURED = "NOT_CONFIGURED"

#: What kind of thing was worth saying. Kept on the announcement so a reader can tell a
#: quiet run (nothing was worth saying) from a mute one (plenty was, and none of it went).
READY = "READY"
PLACEMENT = "PLACEMENT"
BREAKER = "BREAKER"
BLIND = "BLIND"
HEARTBEAT = "HEARTBEAT"

#: What has already been said, and how many runs each lane has been blind. A record, never
#: a source of truth about the money — losing it costs a duplicate message and nothing else.
MEMORY = Path("data/announced.json")

#: How long a standing item stays told. Matches `lib.reaper.Reaper.cooldown_seconds`, and
#: for the same reason: eight hours of arb cadence should not produce eight messages about
#: one market, and a market still standing tomorrow is worth mentioning again.
REPEAT_AFTER_SECONDS = 6 * 3600

#: How many consecutive runs a lane must fail to reach its source before that is worth
#: waking somebody for. One is a flaky endpoint; three in a row is a pipeline, and a
#: pipeline that reads as a quiet market is the failure `COULD_NOT_LOOK` exists to name.
BLIND_RUNS_BEFORE_TELLING = 3


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _age_seconds(stamp: str) -> float | None:
    """Seconds since an ISO stamp, or None when it cannot be read.

    None is not zero and not infinity. The caller treats an unreadable stamp as "tell them
    again", because a message you cannot date is one you cannot prove was delivered.
    """

    try:
        when = datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - when).total_seconds()


@dataclass(frozen=True, slots=True)
class Announcement:
    """One thing worth saying, and what became of saying it."""

    kind: str
    lane: str
    subject: str
    status: str
    at: str = ""
    reason: str = ""
    #: The delivery status from `lib.notify` when a send was attempted. Empty when none
    #: was, which is a different fact from a send that failed.
    delivery: str = ""

    def describe(self) -> str:
        head = f"{self.status}  [{self.lane}] {self.kind}" + (
            f"  {self.subject}" if self.subject else "")
        if self.status == ANNOUNCED:
            return head
        if self.status == ALREADY_TOLD:
            return f"{head}\n  {self.reason}"
        if self.status == NOT_CONFIGURED:
            return (f"{head}\n  No Telegram credentials, so nobody was told and nothing "
                    f"failed. This finding is in the report above and nowhere else.")
        return (f"{head}\n  {self.delivery}: {self.reason}\n"
                f"  This was worth telling you and the telling did not happen.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "lane": self.lane,
            "subject": self.subject or None,
            "status": self.status,
            "at": self.at or None,
            "reason": self.reason or None,
            "delivery": self.delivery or None,
        }


@dataclass(frozen=True, slots=True)
class Line:
    """One row of the daily digest: a lane, its last known state, and why."""

    lane: str
    status: str
    reason: str = ""


class Memory:
    """What has been said and which lanes are blind, as plain JSON that outlives a run.

    Unreadable is not empty here in the usual sense — it is emptier. A register that will
    not parse answers "you have not been told" to every question, so nothing is suppressed
    on the run where the file is lost. See the module docstring: for a notifier, the safe
    direction is telling you twice.

    A lost file is then rewritten from what this run knows, and the history does not come
    back. That costs repeat messages about things still standing, which is the price of
    the choice above and not a second bug.
    """

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else MEMORY
        self.readable = True
        self.reason = ""
        self.told: dict[str, str] = {}
        self.blind: dict[str, dict[str, Any]] = {}

        if not self.path.is_file():
            return
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            self.told = {str(k): str(v) for k, v in (payload.get("told") or {}).items()}
            self.blind = {str(k): dict(v) for k, v in (payload.get("blind") or {}).items()}
        except (OSError, ValueError, AttributeError, TypeError) as error:
            self.readable = False
            self.reason = f"{type(error).__name__}: {error}"[:120]
            self.told, self.blind = {}, {}

    def told_at(self, key: str) -> str:
        """When this was last said, or "" for never — and "" whenever the file was lost."""

        return self.told.get(key, "") if self.readable else ""

    def record(self, key: str, at: str) -> None:
        self.told[key] = at

    def save(self) -> None:
        """Best effort, and deliberately so.

        A message that went out and then failed to be recorded is a duplicate tomorrow. A
        message that did not go out because the record could not be written is a silence,
        and the two are not close in cost.
        """

        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            # Bounded, because this file grows by one key per market per lane forever and
            # a notifier's diary must not become the largest thing in `data/`.
            told = dict(sorted(self.told.items(), key=lambda row: row[1])[-500:])
            self.path.write_text(
                json.dumps({"told": told, "blind": self.blind}, indent=2) + "\n",
                encoding="utf-8")
        except OSError:
            pass


class Announcer:
    """Reads a run, decides what a person needs to hear, and hands it to `lib/notify`.

    Constructed with no channel it announces nothing and says `NOT_CONFIGURED` for every
    finding — which is why the default is silence rather than a live `Telegram`. A default
    that read `~/.telegram` would mean a test, an experiment or an import at the wrong
    moment could message somebody. Production asks for the channel explicitly, in
    `default_announcer`.
    """

    def __init__(
        self,
        telegram: Any = None,
        *,
        memory_path: str | Path | None = None,
        theses_path: str | Path | None = None,
        repeat_after: float = REPEAT_AFTER_SECONDS,
        blind_runs: int = BLIND_RUNS_BEFORE_TELLING,
    ) -> None:
        self.telegram = telegram
        self.memory = Memory(memory_path)
        self.theses_path = theses_path
        self.repeat_after = float(repeat_after)
        self.blind_runs = int(blind_runs)

    # -- the one public entry point per caller ------------------------------------------

    def announce_reaping(self, reaping: Any) -> tuple[Announcement, ...]:
        """Everything in one reap that a person would want to know, most urgent first.

        The order is the order somebody reads a phone in: money that has already moved or
        may have, then a stopped lane, then an opportunity, then a blind pipeline. A
        breaker that tripped during this run is told before the instruction it refused, so
        the two are never read the other way round.
        """

        out: list[Announcement] = []
        try:
            placed = self._placements(reaping)
            out += [a for a, _ in placed]
            out += list(self.announce_breakers(getattr(reaping, "assemblies", ())))
            out += self._ready(reaping, told_by_placement={s for _, s in placed})
            out += self._blind(reaping)
        except Exception as error:  # noqa: BLE001 - announcing must not end a run
            out.append(Announcement(
                READY, "", "", UNTOLD, _now(),
                reason=f"the run could not be read for announcement: "
                       f"{type(error).__name__}: {error}"[:200]))
        self.memory.save()
        return tuple(out)

    def announce_heartbeat(self, lanes: Sequence[Line], *, extra: str = "",
                           day: str = "") -> Announcement:
        """The daily digest, at most once a day, whose ABSENCE is the alarm.

        Keyed by date rather than by a window, because "did today's digest arrive" is the
        question a person actually asks, and a rolling twenty-four hours answers a
        different one. A digest that failed to send is not recorded as sent, so the next
        tick tries again — the one message in this module worth retrying within the day.
        """

        today = day or _now()[:10]
        announcement = self._tell(
            HEARTBEAT, "", today, key=f"{HEARTBEAT}|{today}",
            build=lambda: notify.heartbeat_message(lanes, extra=extra),
            repeat_after=None,
            already="today's digest has already been sent",
        )
        self.memory.save()
        return announcement

    # -- what is worth saying -----------------------------------------------------------

    def _ready(self, reaping: Any, *, told_by_placement: set[str]) -> list[Announcement]:
        out = []
        for harvest in getattr(reaping, "harvests", ()):
            if getattr(harvest, "status", "") != "READY":
                continue
            if f"{harvest.lane}|{harvest.subject}" in told_by_placement:
                # The order went in, or may have. "A person places it" is false in the
                # first case and dangerous in the second — somebody placing by hand
                # against an order that may already exist doubles the position — so the
                # placement message went instead of this one.
                continue
            out.append(self._tell(
                READY, harvest.lane, harvest.subject,
                key=f"{READY}|{harvest.lane}|{harvest.subject}",
                build=lambda h=harvest: self._ready_message(h),
                repeat_after=self.repeat_after,
                already=(f"you were told about this within the last "
                         f"{self.repeat_after / 3600:.0f}h. It is still standing, and it "
                         f"is in the report above."),
            ))
        return out

    def _placements(self, reaping: Any) -> list[tuple[Announcement, str]]:
        """Money that moved, and money that may have. The second one is why this exists.

        `UNRESOLVED` is the single most urgent thing this system can produce: an order was
        submitted, the broker did not answer, and a position is recorded that may or may
        not exist. It is keyed by the position rather than by a window, so it is told once
        per order and never suppressed as a repeat of the READY message that preceded it.

        Only `PLACED` and `UNRESOLVED` replace that READY message. A `REFUSED` placement —
        an unreadable ledger, a lane with no execution path — leaves the instruction
        exactly where it was, sized and waiting, so both messages go: one saying what to
        do, one saying what the machine tried and could not.
        """

        from lib.placing import NOT_PLACED, PLACED, UNRESOLVED

        out = []
        for placement in getattr(reaping, "placements", ()):
            status = getattr(placement, "status", "")
            if status == NOT_PLACED:
                # The usual case for arb and chain: no adapter exists, which the READY
                # message already says. Announcing it as well would tell a person the
                # same fact twice under a heading that sounds like a failure.
                continue
            reference = (getattr(placement, "position_id", "")
                         or getattr(placement, "client_order_id", "") or _now()[:10])
            out.append((
                self._tell(
                    PLACEMENT, placement.lane, placement.subject,
                    key=f"{PLACEMENT}|{placement.lane}|{placement.subject}|{reference}",
                    build=lambda p=placement: notify.placement_message(p),
                    repeat_after=None,
                    already="this placement has already been reported",
                ),
                (f"{placement.lane}|{placement.subject}"
                 if status in {PLACED, UNRESOLVED} else ""),
            ))
        return out

    def announce_breakers(self, assemblies: Sequence[Any]) -> tuple[Announcement, ...]:
        """A tripped breaker, once per trip rather than once per run.

        Keyed by when it tripped, so re-arming and tripping again is a second message
        while the same trip sitting there for a week is not seven. The lane has stopped
        placing and does not restart itself, which is exactly the state that looks like a
        quiet market from outside.

        Public and taking assemblies rather than a whole run, because a trip does not only
        happen during a reap. `positions.py --apply` hands the breakers what settled, and
        the fourth loss in a row trips one right there — at a keyboard, hours or a day
        before the lane next runs. Reporting that only on the next reap would leave a
        stopped lane looking like a quiet one for as long as its cadence is.
        """

        from lib.breakers import TRIPPED

        out = []
        for assembly in assemblies:
            breakers = getattr(getattr(assembly, "reaper", None), "breakers", None)
            state = getattr(breakers, "state", None)
            if state is None or getattr(state, "status", "") != TRIPPED:
                continue
            out.append(self._tell(
                BREAKER, assembly.lane, getattr(state, "tripped_by", ""),
                key=f"{BREAKER}|{assembly.lane}|{getattr(state, 'tripped_at', '')}",
                build=lambda lane=assembly.lane, s=state: notify.breaker_message(lane, s),
                repeat_after=None,
                already="this trip has already been reported, and it is still tripped",
            ))
        # Saved here rather than only in `announce_reaping`, so a caller that announces
        # trips alone still records what it said and does not repeat it every invocation.
        self.memory.save()
        return tuple(out)

    def _blind(self, reaping: Any) -> list[Announcement]:
        """Lanes that did not reach a source, counted across runs rather than within one.

        A lane is blind when it was asked to look and could not: its configuration would
        not read, or every subject came back `COULD_NOT_LOOK`. Two states deliberately do
        not count. `NOT_CONFIGURED` is nobody asking, and a HALTED lane is somebody
        deciding — neither is a pipeline that broke, and reporting them here would train
        the reader to ignore the message that means something.
        """

        from lib.reaping import CONFIGURED, NOT_CONFIGURED as LANE_NOT_CONFIGURED

        out = []
        modes = {getattr(m, "lane", ""): m for m in getattr(reaping, "modes", ())}
        harvests: dict[str, list[Any]] = {}
        for harvest in getattr(reaping, "harvests", ()):
            harvests.setdefault(harvest.lane, []).append(harvest)

        for assembly in getattr(reaping, "assemblies", ()):
            lane = assembly.lane
            if assembly.status == LANE_NOT_CONFIGURED:
                continue
            mode = modes.get(lane)
            if mode is not None and not getattr(mode, "may_reap", True):
                continue

            if assembly.status != CONFIGURED:
                blind, reason = True, assembly.reason or f"the lane is {assembly.status}"
            else:
                mine = harvests.get(lane, [])
                blind = bool(mine) and all(h.status == "COULD_NOT_LOOK" for h in mine)
                reason = mine[0].reason if blind and mine else ""
                if not mine:
                    blind, reason = True, (
                        "the lane was configured, was permitted to run, and produced no "
                        "harvest at all — not even a refusal")

            # An unreadable memory starts this count from nothing, which is the one place
            # the fail-toward-telling rule cannot help: the count IS the memory, and
            # announcing on run one instead would report a flaky endpoint as a broken
            # pipeline. The silence is bounded — `save` rewrites the file at the end of
            # this run — and the daily digest carries the lane's state meanwhile.
            record = self.memory.blind.get(lane, {}) if self.memory.readable else {}
            if not blind:
                self.memory.blind.pop(lane, None)
                continue

            runs = int(record.get("runs", 0)) + 1
            self.memory.blind[lane] = {"runs": runs, "since": record.get("since") or _now(),
                                       "reason": reason[:200]}
            if runs < self.blind_runs:
                continue
            out.append(self._tell(
                BLIND, lane, f"{runs} run(s)",
                key=f"{BLIND}|{lane}",
                build=lambda lane=lane, runs=runs, reason=reason:
                    notify.blind_lane_message(lane, runs, reason),
                repeat_after=self.repeat_after,
                already=f"this lane has been reported blind within the last "
                        f"{self.repeat_after / 3600:.0f}h and still is",
            ))
        return out

    # -- saying it ----------------------------------------------------------------------

    def _tell(self, kind: str, lane: str, subject: str, *, key: str, build: Any,
              repeat_after: float | None, already: str) -> Announcement:
        """Build one message and send it, unless it was said recently enough.

        `repeat_after=None` means never repeat this key: a specific order, a specific
        trip, a specific day. A window means the thing itself can persist and is worth
        saying again when it does.
        """

        at = _now()
        last = self.memory.told_at(key)
        if last:
            age = _age_seconds(last)
            if repeat_after is None or (age is not None and age < repeat_after):
                return Announcement(kind, lane, subject, ALREADY_TOLD, at,
                                    reason=f"{already} (last told {last})")

        if self.telegram is None or not getattr(self.telegram, "is_configured", False):
            return Announcement(kind, lane, subject, NOT_CONFIGURED, at,
                                delivery=notify.NOT_CONFIGURED)

        try:
            title, body = build()
        except Exception as error:  # noqa: BLE001 - a formatter fault is not a non-event
            # The finding was real. Saying so badly beats saying nothing, so this reports
            # UNTOLD with the fault rather than dropping the item on the floor.
            return Announcement(kind, lane, subject, UNTOLD, at, delivery=UNTOLD,
                                reason=f"the message could not be built: "
                                       f"{type(error).__name__}: {error}"[:200])

        delivery = self.telegram.send(title, body)
        if delivery.status != notify.SENT:
            # NOT recorded as told. A refused or undelivered message must be retried on
            # the next run, or a token that expired for an hour costs an opportunity
            # silently — which is the exact shape of failure this module exists to stop.
            return Announcement(kind, lane, subject, UNTOLD, at,
                                delivery=delivery.status, reason=delivery.reason)

        self.memory.record(key, at)
        return Announcement(kind, lane, subject, ANNOUNCED, at, delivery=delivery.status)

    def _ready_message(self, harvest: Any) -> tuple[str, str]:
        """The right formatter for the lane, and the thesis the instruction rests on."""

        instruction = harvest.instruction
        if harvest.lane == "arb":
            return notify.arb_message(instruction, market=harvest.subject, at=harvest.at)

        thesis, why_unknown = self._thesis_for(harvest.subject)
        if harvest.lane == "crypto":
            return notify.chain_message(instruction, subject=harvest.subject,
                                        thesis=thesis, why_unknown=why_unknown)
        return notify.stocks_message(instruction, thesis=thesis, why_unknown=why_unknown)

    def _thesis_for(self, subject: str) -> tuple[Any, str]:
        """The thesis behind an instruction, or why it could not be quoted.

        Three answers, not two. A thesis; no thesis on file under that name; or a register
        that would not read. The last two look identical in a message that only knows how
        to omit the reason, and one of them means the reason exists and was not shown.
        """

        from lib.reaping import THESES
        from lib.thesis import ThesisRegister

        try:
            register = ThesisRegister(self.theses_path if self.theses_path is not None
                                      else THESES)
        except Exception as error:  # noqa: BLE001
            return None, f"the thesis register could not be opened ({error})"[:160]

        if not register.readable:
            return None, f"the thesis register would not parse ({register.reason})"
        thesis = register.current(subject)
        if thesis is None:
            return None, (f"no thesis is on file for {subject}, which should not be "
                          f"possible for a permitted instruction")
        return thesis, ""


def default_announcer(**kw: Any) -> Announcer:
    """The production announcer: the real channel, the real memory, the real register."""

    return Announcer(notify.Telegram.from_directory(), **kw)
