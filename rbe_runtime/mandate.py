"""Does this decision permit this action?

The board produces verdicts and nothing consumed them. This is the artifact in between:
given a published decision and a proposed action, it says whether that decision permits
that action, and when it does not, exactly which condition failed.

**The default is REFUSED and permission must be positively established.** This system has
met the same defect in a court archive, an unclassified mechanism, an empty proxy slot, an
absent liquidity venue, an unattempted resample and a rounded percentage: *not found*
rendering as *not there*. Here that defect authorises a trade. So a condition that cannot
be evaluated never satisfies itself by being unreadable, and there is no boolean anywhere
in this module.

`INDETERMINATE` is not a soft `PERMITTED`. It is a refusal with a different reason, kept
separate so a caller can tell "the decision says no" from "I cannot tell what it says".

Pure by construction: no network, no clock of its own, no `connectors` import. Freshness
against live chain state arrives as a `DriftObservation` the caller computed, which keeps
this testable without a chain and keeps `rbe_runtime` from depending on a connector.

What it does NOT do: size a position, choose a price, pick a venue, or decide when to act.
Those are trading decisions and the board has no competence in them.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

PERMITTED = "PERMITTED"
REFUSED = "REFUSED"
EXPIRED = "EXPIRED"
INDETERMINATE = "INDETERMINATE"

ESTABLISHED = "ESTABLISHED"
FAILED = "FAILED"
UNEVALUATED = "UNEVALUATED"

# Outcomes that can permit anything at all. FAIL is obvious. INSUFFICIENT_EVIDENCE is the
# one worth stating: "we could not tell" read as "go ahead" is the sentinel defect at
# decision level, and it is the single most dangerous reading in the system.
PERMITTING_OUTCOMES = frozenset({"PASS", "PASS_WITH_FINDINGS"})

# A reading that entitles a decision to gate an action. Anything else -- a summary, an
# absent record -- is weaker, and weaker is not permitted rather than merely noted.
FULL_SCRUTINY = "full-text"


@dataclass(frozen=True, slots=True)
class ProposedAction:
    """What someone wants to do, in the only terms the board can check.

    `subject` is a locator, not a name: `ethereum:0x...`. A decision about a contract
    permits nothing about a differently-named wrapper of it, and matching on names is how
    that mistake gets made.
    """

    subject: str
    description: str = ""


@dataclass(frozen=True, slots=True)
class DriftObservation:
    """Has the reviewed artefact changed since the board looked at it?

    For an upgradeable contract this is the whole question. CAA's finding is that USDC's
    proxy admin can replace the implementation entirely, so every fact the board
    established holds only while that implementation address is unchanged -- which is one
    `eth_getStorageAt` to check, and far more meaningful than any wall clock.

    Absent means unchecked, never unchanged.
    """

    observed_at_block: int
    implementation: str
    recorded_implementation: str

    @property
    def unchanged(self) -> bool:
        return self.implementation.lower() == self.recorded_implementation.lower()


@dataclass(frozen=True, slots=True)
class ConditionResult:
    name: str
    status: str
    reason: str

    @property
    def blocks(self) -> bool:
        return self.status != ESTABLISHED


@dataclass(frozen=True, slots=True)
class MandateFinding:
    """Per-condition results, never collapsed into a headline.

    The reason a mandate refused is the entire value of it. A caller that only reads
    `status` learns whether to stop; a caller that reads the conditions learns what would
    have to change, which is the difference between a gate and an oracle.
    """

    status: str
    conditions: tuple[ConditionResult, ...]
    review_id: str = ""
    subject: str = ""

    @property
    def failures(self) -> tuple[ConditionResult, ...]:
        return tuple(c for c in self.conditions if c.status == FAILED)

    @property
    def unevaluated(self) -> tuple[ConditionResult, ...]:
        return tuple(c for c in self.conditions if c.status == UNEVALUATED)

    def describe(self) -> str:
        lines = [
            f"{self.status}  for {self.subject or 'the proposed action'} "
            f"under {self.review_id or 'an unnamed decision'}:"
        ]
        for condition in self.conditions:
            lines.append(f"  {condition.name:<14} {condition.status:<13} {condition.reason}")
        if self.status != PERMITTED:
            lines.append(
                "  No action is permitted on this decision. A condition that could not be "
                "evaluated is a refusal, not a pass."
            )
        return "\n".join(lines)


def _outcome(decision: Mapping[str, Any]) -> ConditionResult:
    outcome = str(
        (decision.get("evaluation") or {}).get("outcome") or ""
    )
    if not outcome:
        return ConditionResult("outcome", UNEVALUATED, "no outcome recorded on the decision")
    if outcome not in PERMITTING_OUTCOMES:
        return ConditionResult("outcome", FAILED, f"{outcome} is not a permitting outcome")
    return ConditionResult("outcome", ESTABLISHED, outcome)


def _authority(decision: Mapping[str, Any]) -> ConditionResult:
    if decision.get("binding") is not True:
        return ConditionResult(
            "authority", FAILED,
            "the methodology is non-binding, so no decision under it authorises anything",
        )
    if decision.get("single_authority") is True:
        return ConditionResult(
            "authority", FAILED,
            "signed by a single authority; the four-eyes control was not satisfied",
        )
    return ConditionResult("authority", ESTABLISHED, "binding, two signatures")


def _scrutiny(
    ratification: Mapping[str, Any] | None, reports: Sequence[Mapping[str, Any]]
) -> ConditionResult:
    """How closely a human actually read what they signed for.

    A signature that implies a full reading when there was not one is the same defect
    `board verify` exists to prevent, aimed at the human rather than the agent. So an
    unrecorded basis is UNEVALUATED and a summary basis FAILS -- an unrecorded reading is
    not a full reading, and neither is a skimmed one.
    """

    bases = {
        str(
            ((report.get("raw_record") or {}).get("ai_assistance") or {})
            .get("human_verification_basis")
            or ""
        )
        for report in reports
    }
    bases.discard("")
    if not reports or not bases:
        return ConditionResult(
            "scrutiny", UNEVALUATED, "no verification basis recorded on any seat report"
        )
    weaker = sorted(b for b in bases if b != FULL_SCRUTINY)
    if weaker:
        return ConditionResult(
            "scrutiny", FAILED,
            f"seat drafts verified on {', '.join(weaker)}, not a full reading",
        )
    if ratification is None:
        return ConditionResult("scrutiny", UNEVALUATED, "no ratification recorded")
    return ConditionResult("scrutiny", ESTABLISHED, FULL_SCRUTINY)


def _expiry(indicator: Mapping[str, Any], now: str) -> ConditionResult:
    """The wall clock, which is the weaker of the two and must not stand for the other."""

    expires_at = str(indicator.get("expires_at") or "")
    if not expires_at:
        return ConditionResult("expiry", UNEVALUATED, "no expiry recorded")
    if now >= expires_at:
        return ConditionResult("expiry", FAILED, f"expired at {expires_at}")
    return ConditionResult("expiry", ESTABLISHED, f"valid until {expires_at}")


def _drift(drift: DriftObservation | None) -> ConditionResult:
    """Has the reviewed artefact itself changed?

    Kept apart from expiry deliberately. A first draft folded both into one "freshness"
    condition, and a swapped implementation inside the validity window then reported as
    EXPIRED -- which reads as "re-run it, nothing has changed" when the truth is that the
    thing reviewed no longer exists. Two clocks, two conditions.
    """

    if drift is None:
        return ConditionResult(
            "drift", UNEVALUATED,
            "the artefact was not re-checked; unchecked is not unchanged",
        )
    if not drift.unchanged:
        return ConditionResult(
            "drift", FAILED,
            f"implementation changed from {drift.recorded_implementation} to "
            f"{drift.implementation} by block {drift.observed_at_block}",
        )
    return ConditionResult(
        "drift", ESTABLISHED, f"unchanged at block {drift.observed_at_block}"
    )


def _supersession(decision: Mapping[str, Any]) -> ConditionResult:
    if decision.get("superseded") is True or decision.get("status") == "SUPERSEDED":
        return ConditionResult(
            "supersession", FAILED, "this decision has been superseded by a later review"
        )
    return ConditionResult("supersession", ESTABLISHED, "current")


def _scope(initiation: Mapping[str, Any], action: ProposedAction) -> ConditionResult:
    reviewed = str(initiation.get("repository") or "")
    if not reviewed:
        return ConditionResult("scope", UNEVALUATED, "the decision names no subject")
    if not action.subject:
        return ConditionResult("scope", UNEVALUATED, "the action names no subject")
    if reviewed.strip().lower() != action.subject.strip().lower():
        return ConditionResult(
            "scope", FAILED, f"decision reviewed {reviewed}, action concerns {action.subject}"
        )
    return ConditionResult("scope", ESTABLISHED, reviewed)


def _findings(indicator: Mapping[str, Any]) -> ConditionResult:
    sev1 = indicator.get("unresolved_sev1_count")
    sev2 = indicator.get("unresolved_sev2_count")
    if sev1 is None or sev2 is None:
        return ConditionResult("findings", UNEVALUATED, "unresolved finding counts not recorded")
    if sev1 or sev2:
        return ConditionResult(
            "findings", FAILED, f"{sev1} unresolved SEV-1, {sev2} unresolved SEV-2"
        )
    return ConditionResult("findings", ESTABLISHED, "no unresolved blocking findings")


def evaluate(
    package: Mapping[str, Any],
    action: ProposedAction,
    *,
    now: str,
    session: Mapping[str, Any] | None = None,
    reports: Sequence[Mapping[str, Any]] = (),
    drift: DriftObservation | None = None,
) -> MandateFinding:
    """Evaluate every condition, then combine them without mercy.

    Conditions are evaluated independently and all of them are reported, including the ones
    that passed. A caller needs to know what held as well as what did not, or a refusal
    tells them nothing about what would change it.
    """

    decision = package.get("decision") or {}
    publication = package.get("publication") or {}
    indicator = publication.get("indicator") or {}
    ratification = package.get("ratification")
    initiation = (session or {}).get("initiation") or {}

    conditions = (
        _outcome(decision),
        _authority(decision),
        _scrutiny(ratification, reports),
        _expiry(indicator, now),
        _drift(drift),
        _supersession(decision),
        _scope(initiation, action),
        _findings(indicator),
    )

    # Order matters only for which single word a caller sees. EXPIRED is reported when the
    # ONLY failure is the clock, because "this was permitted yesterday" is a different
    # instruction from "this was never permitted" -- one says re-run the review, the other
    # says do not.
    failed = [c for c in conditions if c.status == FAILED]
    unevaluated = [c for c in conditions if c.status == UNEVALUATED]
    if not failed and not unevaluated:
        status = PERMITTED
    elif [c.name for c in failed] == ["expiry"] and not unevaluated:
        status = EXPIRED
    elif failed:
        status = REFUSED
    else:
        status = INDETERMINATE

    return MandateFinding(
        status=status,
        conditions=conditions,
        review_id=str(indicator.get("review_id") or decision.get("session_id") or ""),
        subject=action.subject,
    )
