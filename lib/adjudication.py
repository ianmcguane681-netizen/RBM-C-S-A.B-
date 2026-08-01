"""Whether an alleged failure actually occurred, and what is allowed to establish it.

The second source family made the alleged mechanism independent: consumer
allegations made to a regulator, and claims filed in court by different parties in
a different forum. The review board accepted that independence and then named the
gap it leaves open:

    "Complaints are consumer allegations to a regulator and filings are claims put
    to a court. Two independent forums now allege the same mechanism, which
    establishes independence, but neither establishes that the alleged failures
    occurred."                                            -- FND3-SR-001, SEV-2

The accepted remediation was a requirement: a judgment, consent order or
examination finding before asserting the failure occurred. This module is that
requirement. It adds a second axis to evidence, orthogonal to source family:

    source family        does this share an origin with evidence we already hold?
    evidentiary standing is this an allegation, or has a forum decided it?

Adding forums moves the first axis. Only a decision moves the second. The study
could retrieve ten independent complaint databases and remain at ALLEGED.

The rule is deliberately hard to satisfy, because for most records the honest
answer is "this establishes nothing". Procedural posture governs, and posture is
routinely misread:

  * Denying a motion to dismiss establishes nothing. To decide that motion the
    court *assumes the allegations are true*. Treating it as proof of occurrence
    would launder an allegation into a finding under a judge's name -- precisely
    the error the board flagged, made harder to see.
  * Denying summary judgment establishes the opposite of a settled fact: that the
    facts are genuinely disputed and must go to trial.
  * An appellate disposition is relative to the judgment below. "Affirmed" against
    an unknown lower judgment is not a direction. Affirming a defence win and
    affirming a plaintiff win are opposite outcomes behind one word.
  * A settlement or voluntary dismissal is not an admission.

So the classifier refuses to guess. Anything it cannot resolve from explicit
structured values is UNDETERMINED, and UNDETERMINED never establishes occurrence.
Being wrong in this direction costs a research step; being wrong in the other
direction puts an unproven claim into a build decision.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

# --- Axis one is source_family, defined on Source. This is axis two. -----------

ALLEGED = "ALLEGED"
ADJUDICATED = "ADJUDICATED"
EVIDENTIARY_STANDINGS = (ALLEGED, ADJUDICATED)

# --- Posture: what kind of decision this was ----------------------------------

MOTION_TO_DISMISS = "MOTION_TO_DISMISS"
SUMMARY_JUDGMENT = "SUMMARY_JUDGMENT"
TRIAL_JUDGMENT = "TRIAL_JUDGMENT"
CONSENT_ORDER = "CONSENT_ORDER"
EXAMINATION_FINDING = "EXAMINATION_FINDING"
SETTLEMENT = "SETTLEMENT"
APPELLATE_REVIEW = "APPELLATE_REVIEW"
UNDETERMINED_POSTURE = "UNDETERMINED"

# The postures capable of resolving the merits. Membership here is necessary, not
# sufficient: direction still has to have gone against the respondent.
#
# CONSENT_ORDER is included because the board named it, and it is worth being
# explicit about what that costs. A consent order records findings made by the
# regulator, and the respondent typically consents to entry without admitting or
# denying them. It is an official adjudicated finding, which is what was asked
# for; it is not a confession, and nothing here should be read as calling it one.
MERITS_POSTURES = frozenset(
    {SUMMARY_JUDGMENT, TRIAL_JUDGMENT, CONSENT_ORDER, EXAMINATION_FINDING}
)

# Deciding these resolves no fact about whether the failure happened.
NON_MERITS_POSTURES = frozenset(
    {MOTION_TO_DISMISS, SETTLEMENT, APPELLATE_REVIEW, UNDETERMINED_POSTURE}
)

# --- Direction: who the decision went against --------------------------------

AGAINST_RESPONDENT = "AGAINST_RESPONDENT"
FOR_RESPONDENT = "FOR_RESPONDENT"
UNDETERMINED_DIRECTION = "UNDETERMINED"

# Exact-match vocabulary for a forum's own structured disposition value. Free text
# is not parsed and near-matches are not accepted: an unrecognised value is
# UNDETERMINED, which is the safe answer.
#
# Appellate words map to APPELLATE_REVIEW with no direction on purpose. They
# describe what happened to the judgment below, and until that judgment is also
# recorded they carry no direction of their own.
DISPOSITION_VOCABULARY: dict[str, tuple[str, str]] = {
    "judgment for plaintiff": (TRIAL_JUDGMENT, AGAINST_RESPONDENT),
    "judgment for defendant": (TRIAL_JUDGMENT, FOR_RESPONDENT),
    "summary judgment for plaintiff": (SUMMARY_JUDGMENT, AGAINST_RESPONDENT),
    "summary judgment for defendant": (SUMMARY_JUDGMENT, FOR_RESPONDENT),
    "consent order entered": (CONSENT_ORDER, AGAINST_RESPONDENT),
    "examination finding issued": (EXAMINATION_FINDING, AGAINST_RESPONDENT),
    "affirmed": (APPELLATE_REVIEW, UNDETERMINED_DIRECTION),
    "reversed": (APPELLATE_REVIEW, UNDETERMINED_DIRECTION),
    "vacated": (APPELLATE_REVIEW, UNDETERMINED_DIRECTION),
    "remanded": (APPELLATE_REVIEW, UNDETERMINED_DIRECTION),
    "affirmed in part": (APPELLATE_REVIEW, UNDETERMINED_DIRECTION),
    "reversed in part": (APPELLATE_REVIEW, UNDETERMINED_DIRECTION),
    "settled": (SETTLEMENT, UNDETERMINED_DIRECTION),
    "dismissed": (UNDETERMINED_POSTURE, UNDETERMINED_DIRECTION),
    "motion to dismiss denied": (MOTION_TO_DISMISS, UNDETERMINED_DIRECTION),
    "motion to dismiss granted": (MOTION_TO_DISMISS, UNDETERMINED_DIRECTION),
    "summary judgment denied": (SUMMARY_JUDGMENT, UNDETERMINED_DIRECTION),
}


def classify_disposition(disposition: str) -> tuple[str, str]:
    """Map a forum's structured disposition value to (posture, direction).

    Deterministic and total: every input returns a pair, and anything outside the
    vocabulary -- including the empty string the unauthenticated CourtListener
    search API returns for `disposition` -- is UNDETERMINED on both axes.
    """

    key = " ".join(str(disposition or "").strip().lower().split())
    return DISPOSITION_VOCABULARY.get(key, (UNDETERMINED_POSTURE, UNDETERMINED_DIRECTION))


def establishes_occurrence(posture: str, direction: str) -> bool:
    """True only when a forum resolved the merits against the respondent."""

    return posture in MERITS_POSTURES and direction == AGAINST_RESPONDENT


def contradicts_occurrence(posture: str, direction: str) -> bool:
    """True when a forum resolved the merits in the respondent's favour.

    This is counter-evidence on the same mechanism, and it is why the adjudicated
    tier cuts both ways. A source that can only ever confirm is not a source.
    """

    return posture in MERITS_POSTURES and direction == FOR_RESPONDENT


def occurrence_reasoning(posture: str, direction: str) -> str:
    """Say plainly why this record does or does not establish occurrence."""

    if establishes_occurrence(posture, direction):
        return f"{posture} resolved against the respondent: occurrence established."
    if contradicts_occurrence(posture, direction):
        return f"{posture} resolved in the respondent's favour: occurrence contradicted."
    if posture == MOTION_TO_DISMISS:
        return (
            "Motion-to-dismiss posture: the court assumed the allegations were true "
            "to decide the motion, so it found no fact."
        )
    if posture == APPELLATE_REVIEW:
        return (
            "Appellate disposition is relative to the judgment below, which is not "
            "recorded here, so it carries no direction."
        )
    if posture == SETTLEMENT:
        return "A settlement is not an admission and establishes no fact."
    if posture in MERITS_POSTURES:
        return f"{posture} reached the merits but no direction was determinable."
    return "Posture not determinable from the available structured metadata."


# --- Federal Judicial Center Integrated Database -----------------------------
#
# The IDB is the judiciary's own statistical record of every federal civil case,
# and unlike opinion prose it codes the outcome. Two coded fields carry it:
#
#   disposition  how the case ended (0-20)
#   judgment     who it went for: 1 plaintiff, 2 defendant, 3 both, 4 unknown
#
# That is the whole reason this source was adopted. Posture and direction are read
# off official codes rather than inferred from text, which is the same standard the
# RECAP connector applies when it admits a docket on its statutory cause.
#
# The mapping below is deliberately narrower than the codes allow, and each
# exclusion is a rule about what a decision means rather than a data limitation:

FJC_DISPOSITION_TRANSFER = 0
FJC_DISPOSITION_REMAND_STATE = 1
FJC_DISPOSITION_WANT_OF_PROSECUTION = 2
FJC_DISPOSITION_LACK_OF_JURISDICTION = 3
FJC_DISPOSITION_DEFAULT = 4
FJC_DISPOSITION_CONSENT = 5
FJC_DISPOSITION_MOTION_BEFORE_TRIAL = 6
FJC_DISPOSITION_JURY_VERDICT = 7
FJC_DISPOSITION_DIRECTED_VERDICT = 8
FJC_DISPOSITION_COURT_TRIAL = 9
FJC_DISPOSITION_VOLUNTARILY_DISMISSED = 12
FJC_DISPOSITION_SETTLED = 13

FJC_JUDGMENT_PLAINTIFF = 1
FJC_JUDGMENT_DEFENDANT = 2
FJC_JUDGMENT_BOTH = 3
FJC_JUDGMENT_UNKNOWN = 4

# Reached the merits after both sides were heard. Safe in either direction.
_FJC_TRIAL_DISPOSITIONS = frozenset(
    {FJC_DISPOSITION_JURY_VERDICT, FJC_DISPOSITION_DIRECTED_VERDICT, FJC_DISPOSITION_COURT_TRIAL}
)


def classify_fjc_disposition(disposition: Any, judgment: Any) -> tuple[str, str]:
    """Map FJC IDB codes to (posture, direction). Total, deterministic, conservative.

    Three exclusions carry the reasoning, and each drops real volume:

    * **Settled (13) is excluded.** It is the single most common ending for these
      cases -- roughly 7,700 of the 17,200 FCRA records -- and a settlement is not
      an admission. Admitting it would hand the study thousands of false proofs.
    * **Default (4) is excluded.** A defendant who never appeared forfeited the
      case; nobody weighed whether the failure happened.
    * **Judgment on a pre-trial motion (6) is directional.** For the *plaintiff* it
      is a merits win, because a plaintiff cannot prevail on a motion to dismiss --
      winning before trial means summary judgment. For the *defendant* the same
      code covers both a Rule 12(b)(6) dismissal, where the claim failed as a
      matter of law without any fact being found, and Rule 56 summary judgment,
      where the facts were resolved. The IDB does not distinguish them, so a
      defendant win here is UNDETERMINED rather than counter-evidence -- and that
      discards the largest defence-side group (363 records) rather than overstate
      what it proves.
    """

    try:
        disposition_code = int(disposition)
        judgment_code = int(judgment)
    except (TypeError, ValueError):
        return UNDETERMINED_POSTURE, UNDETERMINED_DIRECTION

    if judgment_code == FJC_JUDGMENT_PLAINTIFF:
        if disposition_code == FJC_DISPOSITION_CONSENT:
            return CONSENT_ORDER, AGAINST_RESPONDENT
        if disposition_code == FJC_DISPOSITION_MOTION_BEFORE_TRIAL:
            return SUMMARY_JUDGMENT, AGAINST_RESPONDENT
        if disposition_code in _FJC_TRIAL_DISPOSITIONS:
            return TRIAL_JUDGMENT, AGAINST_RESPONDENT

    if judgment_code == FJC_JUDGMENT_DEFENDANT:
        if disposition_code in _FJC_TRIAL_DISPOSITIONS:
            return TRIAL_JUDGMENT, FOR_RESPONDENT
        if disposition_code == FJC_DISPOSITION_MOTION_BEFORE_TRIAL:
            # Rule 12(b)(6) and Rule 56 share this code. Not separable here.
            return SUMMARY_JUDGMENT, UNDETERMINED_DIRECTION

    if disposition_code == FJC_DISPOSITION_SETTLED:
        return SETTLEMENT, UNDETERMINED_DIRECTION
    if disposition_code == FJC_DISPOSITION_DEFAULT:
        # Deliberately not a merits posture: nobody weighed the allegation.
        return UNDETERMINED_POSTURE, UNDETERMINED_DIRECTION
    return UNDETERMINED_POSTURE, UNDETERMINED_DIRECTION


@dataclass(frozen=True)
class AdjudicatedFinding:
    """One forum decision, and what it is permitted to support.

    `establishes_occurrence` is derived rather than supplied, so a caller cannot
    assert occurrence by setting a flag. It has to come from posture and direction.
    """

    adjudication_id: str
    forum: str
    citation: str
    respondent: str
    mechanism: str
    posture: str
    direction: str
    decided_date: str = ""
    source_url: str = ""
    reasoning_chain: list[str] = field(default_factory=list)

    @property
    def establishes_occurrence(self) -> bool:
        return establishes_occurrence(self.posture, self.direction)

    @property
    def contradicts_occurrence(self) -> bool:
        return contradicts_occurrence(self.posture, self.direction)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["establishes_occurrence"] = self.establishes_occurrence
        data["contradicts_occurrence"] = self.contradicts_occurrence
        data["occurrence_reasoning"] = occurrence_reasoning(self.posture, self.direction)
        return data
