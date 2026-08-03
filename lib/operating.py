"""Who is placing right now — the machine, or you — and how you take it back.

Placing is allowed to be automatic. This is the layer that decides whether it is, for each
lane, at this moment, and it is deliberately the simplest thing in the repository.

    AUTONOMOUS                 the lane places its own instructions
    OWNER_OPERATING_MANUALLY   the lane looks, screens, sizes and reports — you place
    HALTED                     nothing runs at all

The middle mode is the point. A stopped system tells you nothing, so "I am taking the wheel"
must not mean "I am blind". Under `OWNER_OPERATING_MANUALLY` every lane still runs end to
end and still produces a sized, permitted instruction; the only thing that changes is who
puts it on. That is what makes it a mode a person will actually use, rather than a switch
they avoid because flipping it costs them the research too.

## Autonomy is asserted, never assumed

**An absent, unreadable or unrecognised mode means OWNER_OPERATING_MANUALLY.** Not
AUTONOMOUS. This is the repository's recurring defect pointed at the most consequential
switch it has: a missing config key, a typo, a half-written file or a directory that could
not be read must never resolve to "place freely". Autonomy has to be positively stated, and
everything else falls back to the mode where a human is in the loop.

## Two mechanisms, because they fail differently

**The config** (`data/reapers.json`, `"autonomous_execution": true`) is the deliberate
setting. Editing JSON at two in the morning on a phone is not a plan.

**The files** are the fast switch. `data/MANUAL` drops every lane to owner-operating;
`data/MANUAL-arb` drops one. Creating a file is something anything can do from anywhere —
a phone, a text editor, `touch` over SSH — and it needs no code path in this repository to
be working at the time. `data/HALT` and `data/HALT-<lane>` stop the lane outright, as before.

**The file always beats the config.** A switch that could be overridden by a setting is not
a switch.

## Coming back is a human act

`resume(by, reason)` deletes the manual file and refuses every automation prefix, exactly as
`Breakers.reset` does. The reasoning is identical: the system dropped to manual because
something warranted a person, and deciding that the person is no longer needed is precisely
the judgement automation must not make about its own supervision.

## An unresolved UNKNOWN drops the lane to manual on its own

A position whose outcome could not be established means the lane does not know its own
exposure. Placing more on top of that is the failure the breakers exist to prevent, and the
breakers cannot see it — an `UNKNOWN` never reaches them, by design. So it is caught here
instead, and it clears the moment somebody settles or voids the position.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

AUTONOMOUS = "AUTONOMOUS"
OWNER_OPERATING_MANUALLY = "OWNER_OPERATING_MANUALLY"
HALTED = "HALTED"

#: Where the mode came from, so a reader can tell a deliberate setting from a fallback.
FROM_CONFIG = "CONFIG"
FROM_FILE = "FILE"
FROM_EXPOSURE = "UNRESOLVED_EXPOSURE"
FROM_REFUSAL = "REFUSED_FOR_THIS_LANE"
FROM_DEFAULT = "DEFAULT"

HALT_FILE = "HALT"
MANUAL_FILE = "MANUAL"

#: Identical to `lib.thesis` and `lib.breakers`, and for the identical reason.
AUTOMATION_PREFIXES = ("agent:", "ai:", "model:", "automation:", "bot:", "system:")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class Mode:
    """What is placing for one lane right now, and why it is that rather than something else."""

    lane: str
    mode: str
    source: str
    reason: str = ""

    @property
    def may_place(self) -> bool:
        return self.mode == AUTONOMOUS

    @property
    def may_reap(self) -> bool:
        """Manual still looks. Only HALTED stops the research as well as the placing."""

        return self.mode != HALTED

    def describe(self) -> str:
        if self.mode == HALTED:
            return (f"HALTED  [{self.lane}]\n  {self.reason}\n"
                    f"  Nothing runs. Remove the file to resume; it will come back in "
                    f"whatever mode the config and the manual switch then say.")
        if self.mode == AUTONOMOUS:
            return (f"AUTONOMOUS  [{self.lane}]\n  {self.reason}\n"
                    f"  This lane PLACES ITS OWN INSTRUCTIONS. To take the wheel without "
                    f"stopping the research, create the manual switch — the lane keeps "
                    f"looking, screening and sizing, and you place.")
        return (f"OWNER OPERATING MANUALLY  [{self.lane}]\n  {self.reason}\n"
                f"  The lane still looks, screens, gates, authorises and sizes. Nothing "
                f"is placed automatically; each instruction waits for you.")


def _present(directory: Path, name: str, lane: str) -> Path | None:
    """The global file, or the per-lane one. Either is enough."""

    for candidate in (directory / name, directory / f"{name}-{lane}"):
        try:
            if candidate.exists():
                return candidate
        except OSError:
            # A directory that cannot be stat'd is not a directory with no switch in it.
            return candidate
    return None


def operating_mode(
    lane: str,
    *,
    directory: Path,
    config_autonomous: Any = None,
    unresolved_unknowns: int = 0,
) -> Mode:
    """The mode, by precedence. The first rule that matches decides.

    Ordered so that every rule which can only make the system SAFER comes before the one
    rule that can make it act. Autonomy is the last thing consulted and the only thing that
    has to be positively true.
    """

    from lib.reaper import NEVER_AUTONOMOUS

    halt = _present(directory, HALT_FILE, lane)
    if halt is not None:
        return Mode(lane, HALTED, FROM_FILE, f"{halt} exists.")

    if lane in NEVER_AUTONOMOUS and config_autonomous:
        # Not silently downgraded. A config asking for something refused outright is a
        # misunderstanding worth reading about rather than a setting that quietly did
        # nothing.
        return Mode(lane, OWNER_OPERATING_MANUALLY, FROM_REFUSAL, (
            f"the config asks for autonomous placement on the {lane} lane and that is "
            f"refused whatever it says: a chain transaction is atomic, irreversible and "
            f"signed with keys controlling the rest of the wallet. The adapter has no key "
            f"path either, so this is belt and braces."))

    manual = _present(directory, MANUAL_FILE, lane)
    if manual is not None:
        return Mode(lane, OWNER_OPERATING_MANUALLY, FROM_FILE, (
            f"{manual} exists. A switch that a setting could override would not be a "
            f"switch, so this beats the config."))

    if unresolved_unknowns:
        return Mode(lane, OWNER_OPERATING_MANUALLY, FROM_EXPOSURE, (
            f"{unresolved_unknowns} position(s) in this lane have an outcome that could "
            f"not be established, so the lane does not know its own exposure. An UNKNOWN "
            f"never reaches the breakers by design, so it is caught here. Settle or void "
            f"them and this clears."))

    if config_autonomous is True:
        return Mode(lane, AUTONOMOUS, FROM_CONFIG,
                    "the config states autonomous_execution for this lane.")

    if config_autonomous is None:
        return Mode(lane, OWNER_OPERATING_MANUALLY, FROM_DEFAULT, (
            "no autonomy is stated for this lane. Absent is not permission — autonomy is "
            "asserted, never assumed, because a missing key must not resolve to placing "
            "freely."))

    return Mode(lane, OWNER_OPERATING_MANUALLY, FROM_CONFIG, (
        f"the config gives autonomous_execution as {config_autonomous!r}, which is not "
        f"True. Anything that is not an explicit yes is a no."))


def modes_for(
    lanes: Sequence[str],
    config: dict,
    *,
    directory: Path,
    ledger: Any = None,
) -> tuple[Mode, ...]:
    """One mode per lane, always all of them, in the order given."""

    unknowns: dict[str, int] = {}
    if ledger is not None and getattr(ledger, "readable", False):
        from lib.outcomes import UNKNOWN

        for position in ledger.positions:
            if position.status == UNKNOWN:
                unknowns[position.lane] = unknowns.get(position.lane, 0) + 1
    elif ledger is not None:
        # Unreadable. Every lane is treated as holding unresolved exposure, because an
        # unreadable ledger is not an empty one and this is the direction that stops.
        unknowns = {lane: 1 for lane in lanes}

    out = []
    for lane in lanes:
        settings = config.get(lane) or {}
        out.append(operating_mode(
            lane, directory=directory,
            config_autonomous=settings.get("autonomous_execution"),
            unresolved_unknowns=unknowns.get(lane, 0),
        ))
    return tuple(out)


def take_the_wheel(directory: Path, reason: str, *, lane: str = "") -> Path:
    """Drop to owner-operating. Anything may call this; only a person reverses it.

    Deliberately unguarded on the way in and guarded on the way out, the same asymmetry as
    the kill switch. Becoming more cautious needs no authority; becoming less does.
    """

    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (f"{MANUAL_FILE}-{lane}" if lane else MANUAL_FILE)
    path.write_text(f"{_now()}  {reason}\n", encoding="utf-8")
    return path


def resume(directory: Path, by: str, reason: str, *, lane: str = "") -> bool:
    """Hand it back to the machine. A named human only, with a stated reason.

    Same guard as `Breakers.reset` and for the same reason: the system went to manual
    because something warranted a person, and deciding that the person is no longer needed
    is exactly the judgement automation must not make about its own supervision.
    """

    author = by.strip().lower()
    if not author:
        raise ValueError("resuming autonomous placement needs a named person")
    if any(author.startswith(prefix) for prefix in AUTOMATION_PREFIXES):
        raise ValueError(
            f"{by!r} cannot resume autonomous placement. Something warranted a person "
            f"taking the wheel, and deciding they are no longer needed is the judgement "
            f"automation must not make about its own supervision"
        )
    if not reason.strip():
        raise ValueError(
            "a resume without a stated reason is indistinguishable from an impatient one"
        )

    path = directory / (f"{MANUAL_FILE}-{lane}" if lane else MANUAL_FILE)
    if not path.exists():
        return False
    path.unlink()
    return True


def describe_modes(modes: Sequence[Mode]) -> str:
    lines = ["OPERATING MODE"]
    lines += [f"  {mode.describe()}" for mode in modes]
    placing = [m.lane for m in modes if m.may_place]
    lines.append("")
    lines.append(
        f"  {len(placing)} lane(s) will place without asking: {', '.join(placing)}."
        if placing else
        "  No lane places automatically. Every instruction waits for you."
    )
    return "\n".join(lines)
