"""Nothing tells anybody. Every warning in this system waits to be looked at.

`operations.alerts` has existed in `migrations/0002` since the operator backend landed and
**nothing has ever written to it** — the same schema-with-no-writer the journal was, in the
one table whose job is to interrupt somebody. Until now every consequential state has been
*visible*: a TRIPPED breaker, a supervisor that stopped three days ago, an unreadable
outcome ledger, an odds key at its floor. All of them render correctly on a dashboard, and a
dashboard reports nothing to a person who is not looking at it.

That is this repository's founding defect moved up one level, to the operator. A system that
has quietly stopped and a system with nothing to report produce the same silence, and the
silence is what an owner reads when they do not open the page. Fail toward stopping means
little if the stop is never announced.

**Three states, at every layer, for the same reason as everywhere else.**

    RAISED / CLEAR / INDETERMINATE          one condition
    ASSESSED / COULD_NOT_ASSESS             the whole look
    DELIVERED / UNDELIVERABLE / NOT_CONFIGURED   getting it to a person

`COULD_NOT_ASSESS` is the one that earns its keep. A check that could not run is not a check
that passed, so a state file that will not parse produces an alert rather than a quiet page;
an unreadable limit is not a satisfied limit, and an unreadable *system* is not a well one.

**Severity has two values on purpose.** `STOP` means money is exposed or a control cannot be
read. `ATTENTION` means a person has something to do and nothing is bleeding. A third middle
level would be a scoring model with a friendlier name, and the first thing a reader does
with three levels is ignore the middle one.

**This module derives, it does not re-read.** Conditions are computed from the payload
`status.as_json()` already produces, so the alert and the dashboard cannot disagree about
what is true. A second reader of the breaker files would eventually contradict the first,
and then there are two answers to "is this lane stopped" and nothing to say which is right.
It is the ring-fence-built-twice defect, and the fix is to have one reader.

**What this module cannot do, and the deployment has to.** A supervisor cannot report its
own death: if this only ever ran inside `run.py --serve`, the process whose absence is the
most consequential fact on the page would be the one responsible for announcing it. So
`alerts.py` is a separate command with its own timer — `deploy/provena-alerts.timer` — and
the checker is deliberately not the thing being checked.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol, Sequence

STOP = "STOP"
ATTENTION = "ATTENTION"

ASSESSED = "ASSESSED"
COULD_NOT_ASSESS = "COULD_NOT_ASSESS"

DELIVERED = "DELIVERED"
UNDELIVERABLE = "UNDELIVERABLE"
NOT_CONFIGURED = "NOT_CONFIGURED"

STORE = Path("data/alerts.json")

#: How long a condition that is still true waits before it is announced again. Long enough
#: that a breaker tripped on Monday does not send 4,320 notifications by Wednesday; short
#: enough that it is not quietly forgotten either. A condition silenced forever by its own
#: dedup is the same defect as never raising it.
REPEAT_AFTER_SECONDS = 12 * 3600


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _age_seconds(stamp: str) -> float | None:
    try:
        moment = datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return (datetime.now(timezone.utc) - moment).total_seconds()


@dataclass(frozen=True, slots=True)
class Condition:
    """One thing that is true and wants a person.

    `key` is the identity across runs, so the same tripped breaker is one condition
    announced twice rather than two conditions. `action` is not optional and not decoration:
    a notification that says INDETERMINATE and nothing else trains its reader to dismiss it,
    which is a worse outcome than not sending it.
    """

    key: str
    severity: str
    subject: str
    summary: str
    action: str

    def __post_init__(self) -> None:
        if self.severity not in {STOP, ATTENTION}:
            raise ValueError(f"severity must be {STOP} or {ATTENTION}, not {self.severity!r}")
        if not self.action.strip():
            raise ValueError(
                f"condition {self.key!r} states no action. A refusal names what a person "
                f"can go and do about it, or it teaches them to skim."
            )

    def describe(self) -> str:
        return f"[{self.severity}] {self.subject}: {self.summary}\n    -> {self.action}"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class Assessment:
    """What one look found, including the look failing."""

    look: str
    conditions: tuple[Condition, ...] = ()
    reason: str = ""
    at: str = ""

    @property
    def stops(self) -> tuple[Condition, ...]:
        return tuple(c for c in self.conditions if c.severity == STOP)

    @property
    def needs_a_person(self) -> bool:
        return bool(self.conditions) or self.look == COULD_NOT_ASSESS

    def describe(self) -> str:
        if self.look == COULD_NOT_ASSESS:
            return (
                f"COULD_NOT_ASSESS: {self.reason}\n"
                f"    -> This is not a clean bill of health. Nothing was checked, so every "
                f"control below is unknown rather than satisfied."
            )
        if not self.conditions:
            return (
                "Nothing to report. Every control that could be read was read, and none of "
                "them is asking for you."
            )
        return "\n".join(c.describe() for c in self.conditions)

    def to_dict(self) -> dict:
        return {
            "look": self.look,
            "at": self.at or _now(),
            "reason": self.reason or None,
            "stop": len(self.stops),
            "attention": len(self.conditions) - len(self.stops),
            "conditions": [c.to_dict() for c in self.conditions],
        }


# -- the rules ---------------------------------------------------------------------------
#
# Each returns conditions from one block of the state payload. Split per block so a change
# to one panel cannot silently drop the checks belonging to another.


def _scheduler_conditions(state: dict) -> list[Condition]:
    scheduler = state.get("scheduler") or {}
    status = scheduler.get("status")

    if status == "STALE":
        # The most consequential silence in the system: everything renders, the ledger is
        # intact, every lane reports the state it was last left in, and nothing runs.
        return [Condition(
            "supervisor-stale", STOP, "supervisor",
            f"The heartbeat stopped moving (last tick {scheduler.get('last_tick_at')}). "
            f"No lane is being run whatever its cadence says.",
            "ssh to the box and `systemctl status provena-worker`, then "
            "`journalctl -u provena-worker -n 50` for why it stopped.",
        )]
    if status == "NEVER_STARTED":
        return [Condition(
            "supervisor-never-started", ATTENTION, "supervisor",
            "No supervisor has ever run here. Every cadence is an intention.",
            "Start it: `systemctl enable --now provena-worker`, or `python run.py --serve`.",
        )]
    if status == "UNREADABLE":
        return [Condition(
            "supervisor-unreadable", STOP, "supervisor",
            f"The heartbeat file will not parse ({scheduler.get('reason')}), so whether "
            f"anything is running cannot be established.",
            "Read data/heartbeat.json. If it is corrupt, delete it and restart the worker "
            "— an absent heartbeat reports NEVER_STARTED, which is at least a true state.",
        )]
    return []


def _lane_conditions(lane: dict) -> list[Condition]:
    name = lane.get("lane", "?")
    found: list[Condition] = []

    breaker = (lane.get("breaker") or {}).get("status")
    if breaker == "TRIPPED":
        found.append(Condition(
            f"breaker-tripped:{name}", STOP, name,
            f"The {name} breaker is TRIPPED and does not self-clear.",
            f"Read why in `python status.py`, then re-arm deliberately with a named human: "
            f"breakers reset refuses every automation prefix.",
        ))
    elif breaker == "UNREADABLE":
        found.append(Condition(
            f"breaker-unreadable:{name}", STOP, name,
            f"The {name} breaker state will not parse, so its loss history is unknown. An "
            f"unreadable limit is not a satisfied limit.",
            f"Inspect data/breakers-{name}.json. Do not delete it: a lost history brings a "
            f"TRIPPED breaker back ARMED, which is the one direction this must not fail in.",
        ))
    elif breaker == "INVALID_CONFIGURATION":
        # Kept apart from UNREADABLE because the two send a person to different places, and
        # this alert saying "inspect data/breakers-<lane>.json" about a file that has never
        # existed is what exposed them sharing one word.
        found.append(Condition(
            f"lane-misconfigured:{name}", STOP, name,
            f"No ring-fence could be built for {name}: "
            f"{(lane.get('breaker') or {}).get('reason')}. Nothing is corrupt; the lane has "
            f"never been fully configured, and an unknown limit is not a satisfied limit.",
            f"Finish the {name} block in data/reapers.json — a balance and a currency at "
            f"minimum — or disable the lane until you have.",
        ))

    # A lane permitted to place with no limits configured. Neither half is an alert on its
    # own — plenty of lanes sit unconfigured, and plenty place under a ring-fence — and the
    # combination is a lane that can spend with nothing bounding what it spends.
    if lane.get("places_without_asking") and breaker == "NOT_CONFIGURED":
        found.append(Condition(
            f"autonomous-without-limits:{name}", STOP, name,
            f"{name} places without asking and has no breaker configured, so nothing bounds "
            f"what it can put at risk.",
            f"Either configure the ring-fence for {name} in data/reapers.json, or set its "
            f"mode back to manual until you have.",
        ))

    positions = lane.get("positions") or {}
    if positions.get("status") in {"UNREADABLE", "LOST"}:
        found.append(Condition(
            f"ledger-unreadable:{name}", STOP, name,
            f"The outcome ledger reads {positions['status']} for {name}: what is open and "
            f"what is at risk cannot be established.",
            "Restore data/outcomes.json from the box's backup. Until then treat every lane "
            "as having unknown exposure rather than none.",
        ))
    elif positions.get("stale_open"):
        found.append(Condition(
            f"positions-stale:{name}", ATTENTION, name,
            f"{positions['stale_open']} {name} position(s) have been open past the staleness "
            f"window. Money that is open is invisible to the daily loss limit.",
            f"`python positions.py --list`, then settle, void or mark unknown each one.",
        ))

    quota = lane.get("quota") or {}
    remaining, floor = quota.get("remaining"), quota.get("floor")
    if quota.get("status") == "KNOWN" and remaining is not None and floor is not None:
        if remaining <= floor:
            found.append(Condition(
                f"quota-floor:{name}", ATTENTION, name,
                f"The odds quota is at {remaining}, on or below its floor of {floor}. The "
                f"lane will decline to spend, and a spent account looks exactly like a "
                f"quiet market.",
                "Wait for the monthly reset, lengthen the arb cadence, or narrow the sports "
                "list — see `python preflight.py` for what the current settings cost.",
            ))
    # A quota nobody has measured is deliberately NOT an alert. Never having looked is not
    # the same as having looked and found it spent, and the connector already refuses to
    # block on it for that reason.

    return found


def _access_conditions() -> list[Condition]:
    """Somebody guessing the operator passphrase, which no page would otherwise show.

    Read from the attempt record directly rather than from the state payload: this is not a
    money fact and has no business on the capital dashboard, but it is exactly the kind of
    thing that is discovered weeks later in a log nobody opens.
    """

    from lib.access import MAX_FAILURES, AttemptRecord, ATTEMPTS

    record = AttemptRecord(ATTEMPTS)
    if not record.readable:
        return [Condition(
            "access-record-unreadable", STOP, "access",
            f"The failed-login record at {record.path} will not parse, so the lockout "
            f"cannot be evaluated. Logins are being refused until it is repaired.",
            "Inspect the file and remove it if its contents are not recoverable; an "
            "unreadable lockout is refused rather than assumed absent.",
        )]
    from lib.credentials import exposed

    loose = exposed()
    if loose:
        found = [Condition(
            "credential-mode", ATTENTION, "access",
            f"{len(loose)} credential file(s) are readable beyond their owner: "
            f"{', '.join(str(f.path) for f in loose)}.",
            "chmod 600 each of them. The files are present and working, which is why "
            "nothing else reports this.",
        )]
    else:
        found = []

    failures = record.recent_failures()
    if failures >= MAX_FAILURES:
        return found + [Condition(
            "access-locked-out", STOP, "access",
            f"{failures} failed logins in the last window: the operator login is locked "
            f"out. If this was not you, the passphrase is being guessed.",
            "Check who can reach this port — `python access.py` says whether it is exposed "
            "— and change the passphrase with `python access.py --set-operator <name>`.",
        )]
    if failures > 1:
        return found + [Condition(
            "access-failures", ATTENTION, "access",
            f"{failures} failed login attempt(s) recently.",
            "If none of them was you, bind the API to loopback and reach it over an ssh "
            "tunnel rather than leaving the port open.",
        )]
    return found


def _capital_conditions(state: dict) -> list[Condition]:
    capital = state.get("capital") or {}
    if capital.get("value_status") in {"LOST", "UNREADABLE"}:
        return [Condition(
            "portfolio-unreadable", STOP, "portfolio",
            f"The portfolio book reads {capital['value_status']}: {capital.get('reason')}",
            "Restore data/portfolio.json from backup. A receipt claiming entries beside a "
            "file holding none means there WAS a book — do not start a fresh one over it.",
        )]
    return []


def assess(state: dict | None, *, reason: str = "") -> Assessment:
    """Turn one state payload into the conditions that want a person.

    `state=None` is the COULD_NOT_ASSESS path and must be carried, not swallowed. A run
    that could not gather state and a run that found nothing wrong both produce an empty
    list of conditions, and treating them alike is how a monitoring system reports that a
    burning building is fine.
    """

    if state is None:
        return Assessment(COULD_NOT_ASSESS, (), reason or "no state was gathered", _now())

    found: list[Condition] = []
    found.extend(_scheduler_conditions(state))
    found.extend(_capital_conditions(state))
    found.extend(_access_conditions())
    for lane in state.get("money_lanes") or ():
        found.extend(_lane_conditions(lane))

    # STOP first: the order is what a reader sees first in a notification that gets
    # truncated, and truncation must not be what decides which control they hear about.
    found.sort(key=lambda c: (c.severity != STOP, c.key))
    return Assessment(ASSESSED, tuple(found), "", _now())


def gather_state() -> tuple[dict | None, str]:
    """The dashboard's own payload, with prices deliberately not consulted.

    Nothing here alerts on a valuation, and pricing the book would put a broker call — and
    its rate limit — inside a check that runs every few minutes on a timer. The source
    reports itself unavailable, which the capital block already knows how to say.
    """

    try:
        import status

        return status.as_json(_NoPrices()), ""
    except Exception as error:  # noqa: BLE001 - a failed gather is a condition, not a crash
        return None, f"{type(error).__name__}: {error}"[:200]


class _NoPrices:
    name = "not-consulted"

    def unavailable_reason(self) -> str:
        return (
            "prices are not consulted when assessing alerts: nothing here alerts on a "
            "valuation, and a broker call on a timer is a rate limit waiting to happen."
        )

    def market_state(self) -> str:
        from lib.pricing import UNKNOWN

        return UNKNOWN

    def price(self, asset: str):  # pragma: no cover - never reached; the source is unavailable
        return None


# -- what has already been said ----------------------------------------------------------


@dataclass
class AlertStore:
    """What was announced, when, so the same fact is not announced every five minutes.

    Follows `SeenRegister` and `Breakers`: a JSON file, a readable flag, a reason, and a
    receipt beside it carrying counts and dates and never a subject.
    """

    path: Path
    readable: bool = True
    reason: str = ""
    _seen: dict[str, dict] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.path = Path(self.path)
        if self.path.is_file():
            try:
                self._seen = json.loads(self.path.read_text(encoding="utf-8"))
                if not isinstance(self._seen, dict):
                    raise ValueError("alert store is not an object")
            except (OSError, ValueError) as error:
                self._seen, self.readable = {}, False
                self.reason = f"{type(error).__name__}: {error}"[:120]

    def due(self, condition: Condition, *, repeat_after: float = REPEAT_AFTER_SECONDS) -> bool:
        """First time, or long enough since the last time.

        An unreadable store makes everything due. Re-announcing a condition somebody has
        already seen is a nuisance; staying silent because the file that remembers what was
        said will not open is the failure this whole module exists to prevent.
        """

        if not self.readable:
            return True
        last = (self._seen.get(condition.key) or {}).get("announced_at")
        if not last:
            return True
        age = _age_seconds(last)
        return age is None or age >= repeat_after

    def announced(self, condition: Condition, *, at: str = "") -> None:
        record = self._seen.setdefault(condition.key, {"first_seen_at": at or _now(), "count": 0})
        record["announced_at"] = at or _now()
        record["count"] = int(record.get("count", 0)) + 1
        record["severity"] = condition.severity

    def cleared(self, keys: Sequence[str]) -> tuple[str, ...]:
        """Forget conditions that are no longer true, and say which.

        A condition that stops being true has to leave the store, or the next time it
        occurs it will be inside its own cooldown and stay silent.
        """

        gone = tuple(k for k in self._seen if k not in set(keys))
        for key in gone:
            self._seen.pop(key, None)
        return gone

    def save(self) -> None:
        if not self.readable:
            # Same refusal as `Breakers.save()`: overwriting a file that would not parse
            # discards whatever it held and rebuilds the memory from nothing.
            raise RuntimeError(
                f"refusing to overwrite an unreadable alert store ({self.reason}). Move "
                f"{self.path} aside by hand if the loss of its history is acceptable."
            )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._seen, indent=2, sort_keys=True) + "\n",
                             encoding="utf-8")

        from lib.store import JSON_BACKEND, Receipt

        receipt_path = self.path.with_suffix(".receipt.json")
        previous = Receipt.load(receipt_path) or Receipt(self.path.name, JSON_BACKEND)
        previous.written(_now(), len(self._seen)).save(receipt_path)


# -- getting it to a person ----------------------------------------------------------------


class Channel(Protocol):
    """Somewhere an alert can be sent. A missing one is stated, never assumed absent."""

    name: str

    def unavailable_reason(self) -> str:
        """`""` when it can be used, otherwise what a person must configure."""

    def send(self, conditions: Sequence[Condition], *, assessment: Assessment) -> None:
        """Deliver, or raise. Raising is reported as UNDELIVERABLE, never swallowed."""


@dataclass(frozen=True, slots=True)
class Delivery:
    status: str
    channel: str
    announced: tuple[str, ...] = ()
    reason: str = ""

    def describe(self) -> str:
        if self.status == NOT_CONFIGURED:
            return (
                f"NOT DELIVERED  no channel is configured ({self.reason}). The conditions "
                f"above are real and nobody has been told them by this system."
            )
        if self.status == UNDELIVERABLE:
            return (
                f"UNDELIVERED  {self.channel} failed: {self.reason}. The conditions above "
                f"stand and are NOT recorded as announced, so the next run will try again."
            )
        return f"DELIVERED  {len(self.announced)} condition(s) via {self.channel}."

    def to_dict(self) -> dict:
        return {"status": self.status, "channel": self.channel,
                "announced": list(self.announced), "reason": self.reason or None}


class WebhookChannel:
    """A URL in a file, posted as JSON. Deliberately the dullest thing that works.

    The URL lives at `~/.provena/alert_webhook`, mode 600, for the same reason every other
    credential here does: it is a secret — anyone holding it can post as this system — and
    it must never arrive in the repository or in a chat message. It suits ntfy, a Slack or
    Discord incoming hook, or anything that accepts a POST.
    """

    name = "webhook"

    def __init__(self, path: str | Path = "~/.provena/alert_webhook", *, opener=None) -> None:
        self.path = Path(path).expanduser()
        self._opener = opener

    def _url(self) -> str:
        try:
            return self.path.read_text(encoding="utf-8").strip()
        except OSError:
            return ""

    def unavailable_reason(self) -> str:
        if not self._url():
            return (
                f"no webhook configured: write the URL to {self.path} (mode 600). Any "
                f"endpoint that accepts a POST will do — ntfy, Slack, Discord."
            )
        return ""

    def send(self, conditions: Sequence[Condition], *, assessment: Assessment) -> None:
        import urllib.request

        body = json.dumps({
            "text": "\n".join(c.describe() for c in conditions),
            "at": assessment.at,
            "stop": len(assessment.stops),
            "conditions": [c.to_dict() for c in conditions],
        }).encode("utf-8")
        request = urllib.request.Request(
            self._url(), data=body, headers={"Content-Type": "application/json"},
            method="POST",
        )
        opener = self._opener or (lambda r: urllib.request.urlopen(r, timeout=10))
        with opener(request):
            pass


def deliver(
    assessment: Assessment,
    store: AlertStore,
    channel: Channel | None,
    *,
    repeat_after: float = REPEAT_AFTER_SECONDS,
) -> Delivery:
    """Announce what is due, and record it as announced ONLY once it was.

    The ordering matters and it fails in the safe direction, the same way
    `apply_to_breakers` does: the send happens first, and the store is written after it
    returned. A crash between the two re-announces a condition somebody has already seen,
    which is a nuisance. The reverse ordering would mark an alert as delivered that never
    left the building, and the condition would then sit silent for the whole cooldown.
    """

    due = [c for c in assessment.conditions if store.due(c, repeat_after=repeat_after)]
    if assessment.look == COULD_NOT_ASSESS:
        # A failed look is itself worth announcing: silence is what it would otherwise
        # produce, and silence is the thing being fixed.
        due = [Condition(
            "assessment-failed", STOP, "alerting",
            f"The alert check could not read the system state: {assessment.reason}",
            "Run `python alerts.py` by hand and read the traceback. Nothing was checked, "
            "so no control below has been confirmed.",
        )] + due

    if not due:
        return Delivery(DELIVERED, channel.name if channel else "none", ())

    if channel is None:
        return Delivery(NOT_CONFIGURED, "none", (), "no channel was supplied")
    unavailable = channel.unavailable_reason()
    if unavailable:
        return Delivery(NOT_CONFIGURED, channel.name, (), unavailable)

    try:
        channel.send(due, assessment=assessment)
    except Exception as error:  # noqa: BLE001 - an undelivered alert is a state, not a crash
        return Delivery(UNDELIVERABLE, channel.name, (), f"{type(error).__name__}: {error}"[:160])

    at = _now()
    for condition in due:
        store.announced(condition, at=at)
    return Delivery(DELIVERED, channel.name, tuple(c.key for c in due))
