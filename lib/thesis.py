"""An authorised reason to act — the input no board in this repository can produce.

RBM-003 section 11 states that a review conducted under it can never authorise a
transaction, and `mandate.evaluate()` has therefore never returned `PERMITTED`. That is
correct and it stays. The gates establish that a contract is what it claims, which is
hygiene, and hygiene is not a reason to buy anything.

What was missing is the other half. A decision to hold something has two inputs and the
boards only ever supplied one:

    the board      "this contract is / is not what it claims"      a VETO input
    a person       "I want to hold this, for this reason"          a THESIS input

**The asymmetry is the whole design: the board can veto but never authorise, and a thesis
can authorise but never override a veto.** Written the other way round — a thesis able to
proceed past a SEV-1 finding, or a board able to originate a position — either half becomes
decoration. A crypto review that could authorise would be claiming its hygiene checks
constitute an edge; a thesis that could ignore findings would make the review a formality
somebody skips.

## Why a thesis is not a forecast in the sense this repository refuses

It plainly contains a prediction: nobody holds an asset expecting nothing. The difference is
in who is accountable and what is claimed. A scoring model asserts an edge as a *system
output*, derived from inputs, with the derivation implying it is checkable. A thesis asserts
nothing on the system's behalf — it records that a named person decided, what they reasoned,
what they considered might go wrong, how much they are willing to lose and by when they will
revisit. None of that is presented as established. It is presented as *authorised*, which is
a different claim and an honest one.

Modelled on `EquivalenceDeclaration` in `lib/arb.py`, which solved the same problem for
settlement rules: when a judgement cannot be derived, name the human who made it and record
their reasoning rather than inventing a computation.

## What is refused at construction

    an automation author       agent:, ai:, model:, automation: — a machine cannot decide this
    empty reasoning            an undefended position is one nobody has to defend
    nothing considered         at least one thing that could go wrong, in their words
    no expiry                  an open-ended grant is the failure mode of every grant
    no exposure limit          "how much am I willing to lose" is the decision, not a detail
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

PERMITTED = "PERMITTED"
REFUSED = "REFUSED"
EXPIRED = "EXPIRED"
INDETERMINATE = "INDETERMINATE"

#: Prefixes that cannot author a thesis. Identical to the set `board verify` refuses, and
#: for the identical reason: the accountability is the point of the record.
AUTOMATION_PREFIXES = ("agent:", "ai:", "model:", "automation:", "bot:", "system:")

#: Findings that veto regardless of any thesis. A thesis grants authority to act on a
#: position; it does not grant authority to disbelieve the evidence.
BLOCKING_SEVERITIES = frozenset({"SEV-1", "SEV-2"})


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, AttributeError, TypeError):
        return None


@dataclass(frozen=True, slots=True)
class Thesis:
    """One person's authorised reason to hold one thing, bounded and dated."""

    subject: str
    declared_by: str
    reasoning: str
    considered: tuple[str, ...]
    declared_at: str
    expires_at: str
    max_exposure: float
    currency: str = "EUR"
    #: True when the person authorising is also the person who benefits. For personal
    #: capital that is normal and not a defect; it is recorded so the decision is never
    #: mistaken for an independently validated one.
    self_granted: bool = True

    def __post_init__(self) -> None:
        author = self.declared_by.strip().lower()
        if not author:
            raise ValueError("a thesis needs a named author")
        if any(author.startswith(prefix) for prefix in AUTOMATION_PREFIXES):
            raise ValueError(
                f"{self.declared_by!r} cannot author a thesis: this is the judgement a "
                f"board deliberately does not make, and automation authoring it would put "
                f"the system back in the position of originating its own reasons"
            )
        if not self.reasoning.strip():
            raise ValueError("a position with no stated reasoning is one nobody has to defend")
        if not any(item.strip() for item in self.considered):
            raise ValueError(
                "at least one thing that could go wrong must be named. A thesis that "
                "considered nothing is a hope with a signature on it"
            )
        if not _parse(self.expires_at):
            raise ValueError("a thesis needs a readable expiry; an open-ended grant is the "
                             "failure mode of every grant")
        if self.max_exposure <= 0:
            raise ValueError("max_exposure must be positive: how much you are willing to "
                             "lose IS the decision, not a detail attached to it")

    @property
    def is_expired(self) -> bool:
        expiry = _parse(self.expires_at)
        return expiry is not None and _now() > expiry

    def describe(self) -> str:
        lines = [
            f"THESIS  {self.subject}",
            f"  declared by {self.declared_by} on {self.declared_at}, expires "
            f"{self.expires_at}",
            f"  exposure limit {self.max_exposure:,.2f} {self.currency}",
            f"  reasoning: {self.reasoning}",
            "  considered:",
        ]
        lines += [f"    - {item}" for item in self.considered if item.strip()]
        if self.self_granted:
            lines.append(
                "  SELF-GRANTED: the person authorising this is the person exposed to it. "
                "Normal for personal capital, recorded so it is never read as independent "
                "validation."
            )
        return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class Permission:
    """Whether an action is permitted, with every condition reported separately."""

    status: str
    subject: str
    conditions: tuple[tuple[str, str, str], ...] = ()

    def describe(self) -> str:
        lines = [f"{self.status}  {self.subject}", ""]
        for name, verdict, detail in self.conditions:
            mark = {"MET": "  ok  ", "UNMET": " STOP ", "UNKNOWN": "  ??  "}[verdict]
            lines.append(f"[{mark}] {name}")
            lines.append(f"         {detail}")
        lines.append("")
        if self.status == PERMITTED:
            lines.append(
                "  PERMITTED means: the evidence does not veto this, and a named person "
                "authorised it within a stated limit and date. It does NOT mean the board "
                "endorsed it. No board here can, and none did."
            )
        elif self.status == INDETERMINATE:
            lines.append(
                "  A condition could not be evaluated. That is not a refusal and it is not "
                "permission; nothing has been established either way."
            )
        return "\n".join(lines)


def evaluate(
    thesis: Thesis | None,
    *,
    subject: str,
    findings: Sequence[dict] | None = None,
    board_outcome: str = "",
    proposed_exposure: float = 0.0,
) -> Permission:
    """Both halves, reported separately, with the veto outranking the authorisation.

    `findings=None` means the board's findings could not be read, which is INDETERMINATE
    rather than an absence of findings. A position permitted because nobody could read the
    evidence is the exact failure this repository exists to prevent.
    """

    conditions: list[tuple[str, str, str]] = []

    # --- the veto half ---------------------------------------------------------------
    if findings is None:
        conditions.append((
            "board evidence", "UNKNOWN",
            "The board's findings could not be read. This is NOT a finding that there are "
            "none, and permission cannot rest on evidence nobody retrieved.",
        ))
    else:
        blocking = [
            f for f in findings
            if str(f.get("severity", "")) in BLOCKING_SEVERITIES
            and str(f.get("status", "OPEN")).upper() == "OPEN"
        ]
        if blocking:
            titles = ", ".join(str(f.get("title", f.get("finding_id", "?")))[:60]
                               for f in blocking[:3])
            conditions.append((
                "board evidence", "UNMET",
                f"{len(blocking)} unresolved blocking finding(s): {titles}. A thesis "
                f"authorises acting on a position; it does not authorise disbelieving the "
                f"evidence.",
            ))
        else:
            conditions.append((
                "board evidence", "MET",
                f"No unresolved SEV-1 or SEV-2 findings"
                + (f"; outcome {board_outcome}" if board_outcome else "")
                + ". The board does not thereby endorse this — it has not vetoed it.",
            ))

    # --- the authorisation half ------------------------------------------------------
    if thesis is None:
        conditions.append((
            "authorised thesis", "UNMET",
            "No thesis exists for this subject. The boards establish what is true and "
            "cannot originate a reason to act, so with no authorisation there is nothing "
            "to permit.",
        ))
    elif thesis.subject != subject:
        conditions.append((
            "authorised thesis", "UNMET",
            f"The thesis on file names {thesis.subject}, not {subject}.",
        ))
    elif thesis.is_expired:
        conditions.append((
            "authorised thesis", "UNMET",
            f"Expired {thesis.expires_at}. A lapsed authorisation is not a weaker one.",
        ))
    else:
        conditions.append((
            "authorised thesis", "MET",
            f"Declared by {thesis.declared_by}, expires {thesis.expires_at}.",
        ))

    # --- the limit -------------------------------------------------------------------
    if thesis is None:
        conditions.append(("exposure limit", "UNKNOWN", "No thesis, so no stated limit."))
    elif proposed_exposure <= 0:
        conditions.append((
            "exposure limit", "UNKNOWN",
            "No proposed exposure was supplied, so it cannot be checked against the limit.",
        ))
    elif proposed_exposure > thesis.max_exposure:
        conditions.append((
            "exposure limit", "UNMET",
            f"{proposed_exposure:,.2f} proposed against a stated limit of "
            f"{thesis.max_exposure:,.2f} {thesis.currency}.",
        ))
    else:
        conditions.append((
            "exposure limit", "MET",
            f"{proposed_exposure:,.2f} within {thesis.max_exposure:,.2f} {thesis.currency}.",
        ))

    verdicts = [verdict for _, verdict, _ in conditions]
    if "UNMET" in verdicts:
        expired = thesis is not None and thesis.is_expired
        return Permission(EXPIRED if expired else REFUSED, subject, tuple(conditions))
    if "UNKNOWN" in verdicts:
        return Permission(INDETERMINATE, subject, tuple(conditions))
    return Permission(PERMITTED, subject, tuple(conditions))


class ThesisRegister:
    """Theses on file, one per subject. Append-only; a superseded one is kept."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.entries: list[Thesis] = []
        self.readable = True
        self.reason = ""
        if self.path.is_file():
            try:
                self.entries = [
                    Thesis(**{**row, "considered": tuple(row.get("considered", ()))})
                    for row in json.loads(self.path.read_text(encoding="utf-8"))
                ]
            except (OSError, ValueError, TypeError) as error:
                self.readable = False
                self.reason = f"{type(error).__name__}: {error}"[:120]

    def current(self, subject: str) -> Thesis | None:
        """The newest unexpired thesis for a subject, or None.

        `None` when unreadable too: a register that could not be parsed must not answer
        "no thesis" in a way indistinguishable from "no thesis was ever declared", so
        callers check `readable` and get INDETERMINATE rather than REFUSED.
        """

        if not self.readable:
            return None
        live = [t for t in self.entries if t.subject == subject and not t.is_expired]
        return max(live, key=lambda t: t.declared_at) if live else None

    def add(self, thesis: Thesis) -> None:
        if not self.readable:
            raise RuntimeError("refusing to write a register that could not be read")
        self.entries.append(thesis)

    def save(self) -> None:
        if not self.readable:
            raise RuntimeError("refusing to overwrite a register that could not be read")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps([asdict(t) for t in self.entries], indent=2) + "\n", encoding="utf-8"
        )
