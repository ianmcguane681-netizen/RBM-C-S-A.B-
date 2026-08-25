"""Whether to prepare a sample for this business — as an ordered cascade, not a score.

Same argument as everywhere else in this package and it is the load-bearing one: a weighted
"prospect score" treats a disqualifier as a deduction. A business with a perfectly good
website scores well on trade, on contactability, on locality, and a threshold will
eventually let it through — at which point somebody receives an unsolicited redesign of a
site they are happy with.

So the stages run in order, the first refusal is decisive and names itself, and a stage that
could not be evaluated blocks rather than averaging away:

    PREPARE        every stage was evaluated and none refused
    REFUSED        a stage said no. Which one is in the reason
    INDETERMINATE  a stage could not be evaluated. This does NOT prepare

The order is chosen so the cheap, local, free checks refuse before anything reaches the
network: a business with no name and no way to contact it is not worth a fetch, and a
business prepared last week is not worth one either.
"""
from __future__ import annotations

from dataclasses import dataclass

from prospector.business import Business, Fact
from prospector.condition import Condition
from prospector.presence import Presence
from prospector.seen import Sighting
from prospector.states import (COULD_NOT_LOOK, DEFICIENT, NEW, NO_SITE_FOUND,
                               NO_SITE_LISTED, SEEN_BEFORE, SERVICEABLE, SITE_LISTED,
                               SITE_REACHED, UNCHECKED, UNDETERMINED)

PREPARE = "PREPARE"
REFUSED = "REFUSED"
INDETERMINATE = "INDETERMINATE"


@dataclass(frozen=True, slots=True)
class Decision:
    """What the cascade decided, which stage decided it, and why."""

    status: str
    stage: str = ""
    reason: str = ""
    #: The one sentence the outreach note is allowed to open with. Derived here rather
    #: than in the writer, because it is a claim about evidence and this is where the
    #: evidence is.
    opening_claim: str = ""

    def describe(self) -> str:
        if self.status == PREPARE:
            return f"PREPARE       {self.reason}"
        if self.status == REFUSED:
            return f"REFUSED       [{self.stage}] {self.reason}"
        return (f"INDETERMINATE [{self.stage}] {self.reason}\n"
                f"              Not a refusal and not permission. Nothing was prepared.")


def _contactable(business: Business) -> bool:
    return any(isinstance(business.get(key), Fact)
               for key in ("phone", "email", "street", "city"))


def decide(business: Business, sighting: Sighting, presence: Presence,
           condition: Condition | None, *, prepare_again: bool = False) -> Decision:
    """The cascade. `condition` is `None` when there was no site to assess."""

    if not business.name.value.strip():
        return Decision(REFUSED, "named", "the listing carries no name to put on a page")

    if not _contactable(business):
        return Decision(REFUSED, "contactable",
                        "no phone, email or street address is listed, so there is no way "
                        "to put this in front of the owner")

    if sighting.status == UNCHECKED:
        return Decision(INDETERMINATE, "seen", sighting.reason or "the register is unreadable")
    if sighting.status == SEEN_BEFORE and not prepare_again:
        return Decision(REFUSED, "seen",
                        f"prepared {len(sighting.dates)}x already, last on "
                        f"{sighting.dates[-1]}. Pass --again to prepare it anyway.")

    if presence.status == COULD_NOT_LOOK:
        return Decision(INDETERMINATE, "presence", presence.reason)

    if presence.status == NO_SITE_FOUND:
        return Decision(PREPARE, "presence", "a search found no website for this business",
                        opening_claim="I could not find a website for you anywhere, so I "
                                      "built you one to look at.")

    if presence.status == NO_SITE_LISTED:
        # The weakest ground on which this package will prepare anything, and the note has
        # to say so. The map being silent is not evidence about the business, so the
        # opening claim is about the SEARCH rather than about them — which also happens to
        # be the version that survives the owner replying "we do have a website".
        return Decision(PREPARE, "presence",
                        "the public listing carries no website. This is NOT established "
                        "absence — see the opening claim",
                        opening_claim="I could not find a website listed for you in the "
                                      "public directories, so I put together what one "
                                      "could look like. If you already have one, ignore "
                                      "this with my apologies.")

    if presence.is_social_only:
        return Decision(PREPARE, "presence",
                        f"the only web presence listed is a social page: {presence.url}",
                        opening_claim="Your Facebook page is doing the job of a website at "
                                      "the moment, so I put together what a site of your "
                                      "own could look like.")

    if presence.status in (SITE_LISTED, SITE_REACHED):
        if condition is None or condition.status == UNDETERMINED:
            reason = condition.reason if condition else "the site was never assessed"
            return Decision(INDETERMINATE, "condition", reason)
        if condition.status == SERVICEABLE:
            return Decision(REFUSED, "condition",
                            f"{presence.url} answered and no named defect was found. "
                            f"Nothing here justifies an approach.")
        if condition.status == DEFICIENT:
            defects = ", ".join(f.code for f in condition.defects)
            return Decision(PREPARE, "condition",
                            f"{presence.url} has named defects: {defects}",
                            opening_claim=_defect_claim(condition))

    return Decision(INDETERMINATE, "presence",
                    f"unhandled presence state {presence.status!r}")


def _defect_claim(condition: Condition) -> str:
    codes = {f.code for f in condition.defects}
    if "DOMAIN_DOES_NOT_RESOLVE" in codes:
        return ("Your domain does not resolve at all any more — the registration may have "
                "lapsed. I built a replacement you can look at.")
    if "UNREACHABLE" in codes or "SERVER_ERROR" in codes:
        return ("Your website did not load on either of two attempts today, so I built a "
                "page that does.")
    if "PLACEHOLDER" in codes or "EMPTY_PAGE" in codes or "NOT_FOUND" in codes:
        return ("The address listed for your website shows a placeholder rather than a "
                "site, so I built what could be there instead.")
    if "NO_MOBILE_VIEWPORT" in codes:
        return ("Your site is served to phones at desktop width, which is most of the "
                "people looking for you. Here is the same information laid out for a "
                "phone.")
    if "NO_HTTPS" in codes:
        return ("Your site is served over plain HTTP, so browsers show visitors a 'Not "
                "secure' warning before they read a word. Here is a version without it.")
    return "I noticed a few fixable things about your site, and built an example."
