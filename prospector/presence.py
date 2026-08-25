"""Does this business have a website — and what is the strongest thing that can honestly
be said, given what was actually checked.

This module exists because of one sentence that is easy to write and almost always wrong:
"this business has no website". Nothing in a directory can establish that. OpenStreetMap
not carrying a `website` tag means a volunteer did not add one, and in rural Ireland that
is the common case rather than the exception — the shop has a site, or a Facebook page it
treats as one, and the map simply does not say so.

So the listing produces a claim about the LISTING, and only an independent search can
promote it to a claim about the BUSINESS:

    SITE_LISTED      the directory carries a URL
    NO_SITE_LISTED   the directory carries none. A gap in the directory
    NO_SITE_FOUND    a search was run for this name and place, and found nothing
    COULD_NOT_LOOK   no search was available, or the search failed

**The default is `COULD_NOT_LOOK`, and that is deliberate.** There is no search backend
wired in — a web search API is a paid dependency and adding one is a decision, not a
detail — so out of the box this package can say "the map does not list a site" and cannot
say "there is no site". Every downstream stage is built to carry that distinction to the
person reading the dossier, rather than quietly rounding it to the flattering reading that
would let an outreach note open with "I noticed you don't have a website".

The seam is `Searcher`. Anything with `.find(name, locality) -> SearchResult` plugs in.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from prospector.business import ABSENT, Business, Fact
from prospector.states import (COULD_NOT_LOOK, NO_SITE_FOUND, NO_SITE_LISTED, SITE_LISTED,
                               SITE_REACHED)

#: URL hosts that are a social presence rather than a website. A Facebook page is the thing
#: this tool most often finds in place of a site, and calling it "has a website" would
#: discard the best prospects in the county. It is recorded as what it is.
SOCIAL_HOSTS = ("facebook.com", "fb.me", "fb.com", "instagram.com", "twitter.com",
                "x.com", "tiktok.com", "linkedin.com", "linktr.ee", "wa.me",
                "business.site", "sites.google.com", "wixsite.com/mysite")


@dataclass(frozen=True, slots=True)
class SearchResult:
    """What an independent search for this business found."""

    status: str
    url: str = ""
    reason: str = ""


class Searcher(Protocol):
    def find(self, name: str, locality: str) -> SearchResult: ...


class NoSearcher:
    """The default. Says it cannot look, every time, and never says nothing is there.

    Substituting a real search backend is the single highest-value addition to this
    package, because it is what turns "the map does not list one" into a fact about the
    business that an outreach note may honestly rest on.
    """

    def find(self, name: str, locality: str) -> SearchResult:
        return SearchResult(COULD_NOT_LOOK,
                            reason="no web-search backend is configured, so the absence "
                                   "of a website has not been established")


@dataclass(frozen=True, slots=True)
class Presence:
    """The listing's claim, the search's claim, and what may be said out loud."""

    status: str
    url: str = ""
    is_social_only: bool = False
    reason: str = ""

    @property
    def may_claim_no_website(self) -> bool:
        """Whether an outreach note may state that the business has no website.

        True only for `NO_SITE_FOUND` — an actual search that actually found nothing. A
        missing map tag never reaches this, which is the whole point of the type.
        """

        return self.status == NO_SITE_FOUND

    def describe(self) -> str:
        if self.status == SITE_LISTED:
            what = "a social page, not a website" if self.is_social_only else "a website"
            return f"SITE_LISTED  {self.url}  ({what})"
        if self.status == SITE_REACHED:
            return f"SITE_REACHED  {self.url}  (found by search, not listed on the map)"
        if self.status == NO_SITE_FOUND:
            return ("NO_SITE_FOUND  a search for this name and locality found nothing. "
                    "This may be stated to the business.")
        if self.status == NO_SITE_LISTED:
            return ("NO_SITE_LISTED  the map carries no website for this business. This "
                    "is a gap in OpenStreetMap and must NOT be stated to the business as "
                    "'you have no website'.")
        return f"COULD_NOT_LOOK  {self.reason}"


def is_social(url: str) -> bool:
    lowered = url.lower()
    return any(host in lowered for host in SOCIAL_HOSTS)


def _locality(business: Business) -> str:
    for key in ("city", "street"):
        value = business.get(key)
        if isinstance(value, Fact):
            return value.value
    return ""


def assess(business: Business, *, searcher: Searcher | None = None) -> Presence:
    """The listing first; the search only when the listing is silent."""

    listed = business.website
    if isinstance(listed, Fact) and listed.value:
        return Presence(SITE_LISTED, url=listed.value, is_social_only=is_social(listed.value))
    # The map is silent. Everything below decides how strong a statement that supports.
    searcher = searcher or NoSearcher()
    result = searcher.find(business.name.value, _locality(business))
    if result.status == SITE_REACHED and result.url:
        return Presence(SITE_REACHED, url=result.url, is_social_only=is_social(result.url))
    if result.status == NO_SITE_FOUND:
        return Presence(NO_SITE_FOUND)
    if listed is ABSENT:
        return Presence(NO_SITE_LISTED, reason=result.reason)
    return Presence(COULD_NOT_LOOK, reason=result.reason)
