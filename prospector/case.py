"""Why their site should be the one we built — criterion by criterion, both sides measured.

The temptation in a pitch is to describe the new thing in adjectives. Modern, clean, fast,
mobile-friendly. None of those are checkable and all of them are what the last person to
email this business also said, so they land as noise.

The case here is built differently and it costs nothing to make: **both pages are put
through the same standard, and every point is one criterion where theirs fails and ours
passes, with both measurements printed.** Nobody has to be persuaded of anything — a person
can open their own site on their own phone and see the same thing.

That construction has a property worth stating plainly, because it is what stops this from
becoming marketing: **where the sample does not fix something, the case says so.** If their
site has no opening hours and the map does not carry any either, that criterion is listed
as *not addressed* rather than quietly dropped. A pitch that only lists wins reads like
every other pitch; one that says "these three are fixed, this fourth one I cannot fix
without you" reads like somebody who actually looked.

    CASE_MADE      at least one criterion theirs fails and the sample meets
    NO_CASE        nothing in the first three tiers separates them
    INDETERMINATE  one of the two pages was not assessed, so nothing can be compared
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from prospector import standard
from prospector.standard import APPROACHABLE_TIERS, CRAFT, FAILS, MEETS, NOT_ASSESSED

CASE_MADE = "CASE_MADE"
NO_CASE = "NO_CASE"
#: There is no site to compare against. Not a gap in the case — for a business with no
#: website at all it IS the case, and it is the strongest version of it.
NO_SITE_TO_COMPARE = "NO_SITE_TO_COMPARE"
INDETERMINATE = "INDETERMINATE"

FIXED = "FIXED"
NOT_ADDRESSED = "NOT_ADDRESSED"
#: The sample meets a criterion and there is no site of theirs to have failed it.
OFFERED = "OFFERED"
UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class Point:
    """One criterion, measured on both pages."""

    code: str
    tier: str
    title: str
    why: str
    theirs: str
    ours: str
    verdict: str

    @property
    def is_reason_to_write(self) -> bool:
        """Whether this point belongs in a first approach at all.

        Only a fixed failure in the first three tiers. A craft point is true and is worth
        having in the room later; leading with one is how a cold email about somebody's
        meta description gets sent.
        """

        return self.verdict == FIXED and self.tier in APPROACHABLE_TIERS


@dataclass(frozen=True, slots=True)
class Case:
    """The whole comparison, and what may be claimed from it."""

    status: str
    points: tuple[Point, ...] = ()
    reason: str = ""

    @property
    def fixed(self) -> tuple[Point, ...]:
        return tuple(point for point in self.points if point.is_reason_to_write)

    @property
    def not_addressed(self) -> tuple[Point, ...]:
        """Failures on their site the sample does not fix. Said out loud, not dropped."""

        return tuple(point for point in self.points
                     if point.verdict == NOT_ADDRESSED and point.tier in APPROACHABLE_TIERS)

    @property
    def craft(self) -> tuple[Point, ...]:
        return tuple(point for point in self.points
                     if point.tier == CRAFT and point.verdict == FIXED)

    @property
    def offered(self) -> tuple[Point, ...]:
        """What the sample does, where there is nothing to compare it against."""

        return tuple(point for point in self.points if point.verdict == OFFERED)

    def describe(self) -> str:
        if self.status == NO_SITE_TO_COMPARE:
            lines = [f"NO_SITE_TO_COMPARE  {self.reason}",
                     "  There is nothing to be better than, so the case is simply what "
                     "this page does that nothing currently does for them:"]
            for point in self.offered:
                lines.append(f"  [{point.tier}] {point.title} — {point.ours}")
            return "\n".join(lines)
        if self.status == INDETERMINATE:
            return (f"INDETERMINATE  {self.reason}\n"
                    f"  Nothing was compared, so there is no case — which is not the same "
                    f"as there being nothing wrong with their site.")
        if self.status == NO_CASE:
            return ("NO_CASE  nothing in BLOCKING, MOBILE or CONVERSION separates the two "
                    "pages.\n  Whatever else is true, that is not a reason to write to "
                    "somebody.")
        lines = [f"CASE_MADE  {len(self.fixed)} thing(s) their site fails and this one does not"]
        for point in self.fixed:
            lines.append(f"  [{point.tier}] {point.title}")
            lines.append(f"      theirs: {point.theirs}")
            lines.append(f"      ours:   {point.ours}")
            lines.append(f"      why it matters: {point.why}")
        for point in self.not_addressed:
            lines.append(f"  [NOT FIXED] {point.title}")
            lines.append(f"      theirs: {point.theirs}")
            lines.append(f"      ours:   {point.ours}")
            lines.append(f"      This one needs them — say so rather than leaving it out.")
        if self.craft:
            lines.append(f"  Also improved, and not a reason to write: "
                         f"{', '.join(point.code for point in self.craft)}")
        return "\n".join(lines)


def _by_code(report: Any) -> dict[str, Any]:
    return {a.code: a for a in getattr(report, "assessments", ())}


def build(their_report: Any, our_report: Any, *, has_site: bool = True,
          no_site_reason: str = "", established_absence: bool = False) -> Case:
    """Compare the two reports and produce the case, including where there is none.

    `has_site` false is not a missing measurement — it is a business with no website, which
    is the clearest case there is and deserves to read like one rather than like a checker
    that failed.
    """

    theirs = _by_code(their_report)
    ours = _by_code(our_report)
    if not ours:
        return Case(INDETERMINATE, reason="the sample was never assessed")
    if not has_site:
        # The wording tracks what was actually established. "They have no website" is a
        # claim about the business and only a search that looked can support it; a silent
        # directory supports "nothing listed for them", which is weaker and true.
        today = ("they have no website, so nothing does this for them today"
                 if established_absence
                 else "nothing listed for them does this today")
        offered = tuple(
            Point(a.code, a.tier, a.criterion.title, a.criterion.why, today, a.detail,
                  OFFERED)
            for a in our_report.assessments
            if a.state == MEETS and a.tier in APPROACHABLE_TIERS)
        return Case(NO_SITE_TO_COMPARE, offered,
                    reason=no_site_reason or "no website is listed for this business")
    if not theirs:
        return Case(INDETERMINATE, reason="their site was never assessed")

    points: list[Point] = []
    for code, their_assessment in theirs.items():
        if their_assessment.state != FAILS:
            continue
        our_assessment = ours.get(code)
        if our_assessment is None or our_assessment.state == NOT_ASSESSED:
            verdict, ours_detail = UNKNOWN, "not assessed on the sample"
        elif our_assessment.state == MEETS:
            verdict, ours_detail = FIXED, our_assessment.detail
        else:
            verdict, ours_detail = NOT_ADDRESSED, our_assessment.detail
        criterion = their_assessment.criterion
        points.append(Point(code, criterion.tier, criterion.title, criterion.why,
                            their_assessment.detail, ours_detail, verdict))

    order = {tier: index for index, tier in enumerate(standard.TIERS)}
    points.sort(key=lambda point: (order[point.tier], point.code))
    case = Case(CASE_MADE, tuple(points))
    return case if case.fixed else Case(NO_CASE, tuple(points))
