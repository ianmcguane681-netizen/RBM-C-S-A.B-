"""How to reach this business, from what they have published — and the line about who.

The pitch has to arrive somewhere. A dossier that establishes a business needs a website
and then leaves you hunting for a phone number has done the interesting half and skipped
the useful one, so this assembles every published route to them, each with its source, and
says plainly when there is none.

    ROUTES_FOUND     at least one published way to reach the business
    NO_ROUTE_FOUND   looked, and the sources carry none. Not the same as not looking
    COULD_NOT_LOOK   the sources were not read

## The line this module does not cross

**Business contact channels, published by the business, and nothing else.** The shop's
number, the info@ address, the contact form, the trading address, the social account they
put on their own listing. All of it is information a business publishes so that customers
will use it, and using it to write to that business about that business is what it is for.

What this will not do is assemble a person. No looking up who the director is, no guessing
`firstname@`, no scraping a name off a review, no personal mobile found on a Facebook post.
A named individual's work address is still personal data under the GDPR, the shop's
info@ address mostly is not, and the difference is the difference between business
development and something a recipient would rightly be annoyed about.

Where a business has itself published "ask for Cathy" on its own site, that is a fact with
a source like any other and it is recorded — because they published it, in that form, for
that purpose.

## Ranking, and why the phone is usually first

For a local business the phone is the channel they actually watch, and it is also the one
where the pitch works best: the sample is open in front of them while you describe it. The
order here is the order to try, not a ranking of quality — an email address is a better
first contact for a business that is busy at the bench all day, which is a judgement for
the person, so the list is presented rather than acted on.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Sequence

from prospector.business import Business, Fact

ROUTES_FOUND = "ROUTES_FOUND"
NO_ROUTE_FOUND = "NO_ROUTE_FOUND"
COULD_NOT_LOOK = "COULD_NOT_LOOK"

PHONE = "PHONE"
EMAIL = "EMAIL"
FORM = "FORM"
SOCIAL = "SOCIAL"
ADDRESS = "ADDRESS"

#: The order to try, for a local trade. Not a ranking of quality — see the docstring.
ORDER = (PHONE, EMAIL, FORM, SOCIAL, ADDRESS)

_SOCIAL_FIELDS = ("facebook", "instagram")


@dataclass(frozen=True, slots=True)
class Route:
    """One published way in."""

    kind: str
    value: str
    source: str
    #: What this route is good for, in a sentence, because "SOCIAL" on its own tells the
    #: person holding the dossier nothing about whether to use it at nine on a Tuesday.
    note: str = ""

    @property
    def href(self) -> str:
        if self.kind == PHONE:
            return "tel:" + re.sub(r"[^\d+]", "", self.value)
        if self.kind == EMAIL:
            return "mailto:" + self.value
        if self.kind in (FORM, SOCIAL):
            return self.value
        return ""


@dataclass(frozen=True, slots=True)
class Contacts:
    """Every route, in the order to try them, or a stated reason there are none."""

    status: str
    routes: tuple[Route, ...] = ()
    reason: str = ""
    #: A person the business itself has published as the one to ask for. Rarely present,
    #: never inferred.
    named_person: str = ""
    named_person_source: str = ""

    @property
    def best(self) -> Route | None:
        return self.routes[0] if self.routes else None

    def of_kind(self, kind: str) -> tuple[Route, ...]:
        return tuple(route for route in self.routes if route.kind == kind)

    def describe(self) -> str:
        if self.status == ROUTES_FOUND:
            lines = [f"ROUTES_FOUND  {len(self.routes)}"]
            for route in self.routes:
                lines.append(f"  {route.kind:8} {route.value}"
                             + (f"  — {route.note}" if route.note else ""))
                lines.append(f"           source: {route.source}")
            if self.named_person:
                lines.append(f"  ASK FOR  {self.named_person}  "
                             f"(published by them: {self.named_person_source})")
            return "\n".join(lines)
        if self.status == NO_ROUTE_FOUND:
            return ("NO_ROUTE_FOUND  the public listing carries no phone, no email, no "
                    "form and no address.\n  There is nowhere to send this, so it is not "
                    "worth building. Nothing was missed; there is nothing there.")
        return (f"COULD_NOT_LOOK  {self.reason}\n"
                f"  No contact route was established. That is not the same as there being "
                f"none, and a dossier built on it has nowhere to go.")


def _address_line(business: Business) -> str:
    parts = []
    number = business.get("housenumber")
    street = business.get("street")
    if isinstance(street, Fact):
        parts.append(f"{number.value} {street.value}" if isinstance(number, Fact)
                     else street.value)
    for key in ("city", "postcode"):
        value = business.get(key)
        if isinstance(value, Fact):
            parts.append(value.value)
    return ", ".join(parts)


def assemble(business: Business, *, site_contacts: Sequence[Route] = (),
             looked: bool = True) -> Contacts:
    """Every published route to `business`, from the listing and anything read from a site.

    `site_contacts` is what a reader of their own website found — a contact form URL, an
    address in the footer. It is passed in rather than fetched here so that this module
    stays a piece of arithmetic over evidence, and so a dossier built without a site fetch
    reports `COULD_NOT_LOOK` rather than a confident short list.
    """

    if not looked:
        return Contacts(COULD_NOT_LOOK, reason="the sources were not read")

    routes: list[Route] = []
    phone = business.get("phone")
    if isinstance(phone, Fact):
        routes.append(Route(PHONE, phone.value, phone.source,
                            "the channel a local trade actually watches; the sample can be "
                            "open in front of them while you talk"))
    email = business.get("email")
    if isinstance(email, Fact):
        routes.append(Route(EMAIL, email.value, email.source,
                            "better for a business that is at the bench all day — the "
                            "sample can be attached and read when they sit down"))
    routes.extend(route for route in site_contacts if route.kind == FORM)
    for field_name in _SOCIAL_FIELDS:
        value = business.get(field_name)
        if isinstance(value, Fact):
            routes.append(Route(SOCIAL, value.value, value.source,
                                f"their {field_name} page — read on a phone, often by "
                                f"whoever is standing at the counter"))
    routes.extend(route for route in site_contacts if route.kind not in (FORM,))
    address = _address_line(business)
    if address:
        routes.append(Route(ADDRESS, address, business.get("street").source
                            if isinstance(business.get("street"), Fact) else "the listing",
                            "walking in with it on a laptop is the highest-converting "
                            "version of this and the least scalable"))

    if not routes:
        return Contacts(NO_ROUTE_FOUND)
    order = {kind: index for index, kind in enumerate(ORDER)}
    routes.sort(key=lambda route: order.get(route.kind, len(ORDER)))
    return Contacts(ROUTES_FOUND, tuple(routes))
