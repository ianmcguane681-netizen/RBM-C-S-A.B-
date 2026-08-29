"""Businesses in an area, from OpenStreetMap — and what an absent website tag does not mean.

OpenStreetMap through the Overpass API, because it is the only business directory that is
free, structured, queryable by area, and licensed for this use. Google Places and the
commercial lead databases are none of those things and two of them forbid exactly this.

**The one thing this module exists to stop somebody concluding.** OSM is volunteer-mapped
and its coverage of a shop's *attributes* is far worse than its coverage of the shop's
existence. A café with no `website` tag is overwhelmingly likely to be a café whose website
nobody has typed into OSM — not a café without a website. Reading the absence as a finding
would produce a list of prospects where most of the "no website" entries are wrong, and an
approach built on it opens by telling somebody something false about their own business.

So the tag has three states and the middle one is the honest default:

    SITE_TAGGED     OSM records a website. It may be dead; `connectors/sitecheck` says
    NOT_TAGGED      OSM records none. THIS IS NOT A FINDING THAT NONE EXISTS
    UNREADABLE      the query failed. Nothing is known about this area at all

`NOT_TAGGED` is a lead — a business worth thirty seconds of somebody's search engine — and
`lib/outreach.py` refuses to draft an approach that asserts anything from it. Only a person
who looked converts it into a finding.

**Rate limits and manners.** Overpass is a donated public resource with no key and a strict
fair-use expectation. The default endpoint asks for a small bounding box, one category at a
time, with a real User-Agent, and `lib/http_retry` waits out a 429 rather than hammering
through it. A query that would return a whole city is refused here rather than sent.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Sequence

from lib.http_retry import retrying_urlopen

OVERPASS = "https://overpass-api.de/api/interpreter"

READ = "READ"
UNREADABLE = "UNREADABLE"
REFUSED = "REFUSED"

# What OSM says about a business's website, which is not what is true about it.
SITE_TAGGED = "SITE_TAGGED"
NOT_TAGGED = "NOT_TAGGED"

#: The largest bounding box this will ask for, in degrees. Roughly a town rather than a
#: county. Larger queries are refused rather than sent: Overpass is donated infrastructure
#: with no key, a county-sized query can run for minutes, and the honest way to cover more
#: ground is more small queries over time rather than one large one now.
MAX_BOX_DEGREES = 0.25

#: Categories worth approaching, as OSM tag values. Trades and services where a website is
#: the first thing a customer looks for and where the operator is usually the owner — which
#: is the difference between an approach that reaches a decision-maker and one that reaches
#: a head office that has an agency already.
DEFAULT_CATEGORIES = (
    "shop=hairdresser", "shop=beauty", "shop=butcher", "shop=bakery", "shop=florist",
    "shop=car_repair", "craft=plumber", "craft=electrician", "craft=carpenter",
    "craft=painter", "amenity=restaurant", "amenity=cafe", "amenity=veterinary",
    "leisure=fitness_centre",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class Business:
    """One mapped business, and what OSM does and does not record about it.

    Every contact field is exactly what the tags said, with no inference. A `phone` derived
    from a nearby node or a `website` guessed from a name would be a fact this system
    invented about a real business, and the first thing that happens to an invented fact is
    that somebody acts on it.
    """

    osm_id: str
    name: str
    category: str
    website_status: str
    website: str = ""
    phone: str = ""
    email: str = ""
    address: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    #: A Facebook or Instagram page in `contact:facebook`. Recorded separately from
    #: `website` because a social page IS a web presence and is not a website — it is the
    #: single commonest real answer to "why has this business not got a site", and an
    #: approach that ignores it reads as though nobody looked.
    social: str = ""
    seen_at: str = ""

    @property
    def has_a_recorded_site(self) -> bool:
        return self.website_status == SITE_TAGGED

    @property
    def contactable(self) -> bool:
        return bool(self.email or self.phone)

    def describe(self) -> str:
        lines = [f"{self.name or '(unnamed)'}  [{self.category}]  osm:{self.osm_id}"]
        if self.address:
            lines.append(f"  {self.address}")
        if self.website_status == SITE_TAGGED:
            lines.append(f"  website: {self.website}")
        else:
            lines.append(
                "  website: NOT_TAGGED in OpenStreetMap. That is not a finding that this "
                "business has no website — OSM's coverage of attributes is far worse than "
                "its coverage of premises. Check before saying anything to anybody.")
        if self.social:
            lines.append(f"  social: {self.social}")
        contacts = ", ".join(part for part in (self.phone, self.email) if part)
        lines.append(f"  contact: {contacts or 'none recorded'}")
        return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class Area:
    """A bounding box, refused rather than truncated when it is too big to ask politely."""

    south: float
    west: float
    north: float
    east: float
    name: str = ""

    def __post_init__(self) -> None:
        if self.north <= self.south or self.east <= self.west:
            raise ValueError(
                f"{self.name or 'this area'} is not a box: north must exceed south and "
                f"east must exceed west")
        if (self.north - self.south) > MAX_BOX_DEGREES or (
                self.east - self.west) > MAX_BOX_DEGREES:
            raise ValueError(
                f"{self.name or 'this area'} spans more than {MAX_BOX_DEGREES} degrees. "
                f"Overpass is donated infrastructure with no key and a county-sized query "
                f"can run for minutes. Cover more ground with more small queries over "
                f"time, not one large one now")

    @property
    def bbox(self) -> str:
        return f"{self.south},{self.west},{self.north},{self.east}"


@dataclass(frozen=True, slots=True)
class Listing:
    """What one query returned, or why it returned nothing."""

    status: str
    area: str
    businesses: tuple[Business, ...] = ()
    categories: tuple[str, ...] = ()
    retrieved_at: str = ""
    reason: str = ""

    @property
    def untagged(self) -> tuple[Business, ...]:
        return tuple(b for b in self.businesses if b.website_status == NOT_TAGGED)

    def describe(self) -> str:
        if self.status != READ:
            return (f"{self.status}  {self.area}: {self.reason}\n"
                    f"  Nothing was retrieved. This is not a finding that the area has no "
                    f"businesses in it.")
        return (
            f"{self.area}: {len(self.businesses)} business(es) across "
            f"{len(self.categories)} categor(ies), read {self.retrieved_at}.\n"
            f"  {len(self.untagged)} have no website tag in OpenStreetMap. That is a list "
            f"of leads to CHECK, not a list of businesses without websites."
        )


def build_query(area: Area, categories: Sequence[str]) -> str:
    """An Overpass QL query for nodes and ways in the box matching any category.

    `nwr` rather than `node`, because a business mapped as a building outline is a way and
    querying only nodes silently halves the answer in exactly the towns where mapping is
    best.
    """

    clauses = []
    for category in categories:
        key, _, value = str(category).partition("=")
        if not key or not value:
            continue
        clauses.append(f'  nwr["{key}"="{value}"]({area.bbox});')
    if not clauses:
        raise ValueError("no usable categories; each must be in the form key=value")
    return "[out:json][timeout:60];\n(\n" + "\n".join(clauses) + "\n);\nout center tags;"


def _business_from(element: Mapping[str, Any], seen_at: str) -> Business | None:
    tags = element.get("tags") or {}
    name = str(tags.get("name") or "").strip()
    if not name:
        # Skipped rather than kept as "(unnamed)". An approach needs somebody to address,
        # and an unnamed node is a mapping artefact rather than a business anybody can be
        # written to.
        return None

    website = str(tags.get("website") or tags.get("contact:website") or "").strip()
    category = next(
        (f"{key}={tags[key]}" for key in ("shop", "craft", "amenity", "office", "leisure")
         if tags.get(key)), "unknown")

    address = " ".join(part for part in (
        str(tags.get("addr:housenumber") or ""), str(tags.get("addr:street") or ""),
        str(tags.get("addr:city") or ""), str(tags.get("addr:postcode") or "")) if part)

    centre = element.get("center") or {}
    return Business(
        osm_id=f"{element.get('type', 'node')}/{element.get('id', '')}",
        name=name, category=category,
        website_status=SITE_TAGGED if website else NOT_TAGGED,
        website=website,
        phone=str(tags.get("phone") or tags.get("contact:phone") or "").strip(),
        email=str(tags.get("email") or tags.get("contact:email") or "").strip(),
        address=address.strip(),
        latitude=float(element.get("lat") or centre.get("lat") or 0.0),
        longitude=float(element.get("lon") or centre.get("lon") or 0.0),
        social=str(tags.get("contact:facebook") or tags.get("contact:instagram")
                   or "").strip(),
        seen_at=seen_at,
    )


def businesses_in(
    area: Area,
    *,
    categories: Sequence[str] = DEFAULT_CATEGORIES,
    opener: Callable[..., Any] = retrying_urlopen,
    endpoint: str = OVERPASS,
) -> Listing:
    """Every mapped business in the box matching a category. Never raises for a failure.

    A failure is a status, because a caller assembling a prospect list has to be able to
    say which areas were actually looked at — the argument `connectors/odds.py` makes about
    a scan that reached no book and reported no arb, applied to a town.
    """

    try:
        query = build_query(area, categories)
    except ValueError as error:
        return Listing(REFUSED, area.name or area.bbox, reason=str(error))

    request = urllib.request.Request(
        endpoint, data=urllib.parse.urlencode({"data": query}).encode("utf-8"),
        headers={"User-Agent": "provena-outreach/1.0 (contact via repository owner)"})
    try:
        with opener(request) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as error:  # noqa: BLE001 - any failure to ask is UNREADABLE
        return Listing(UNREADABLE, area.name or area.bbox,
                       reason=f"{type(error).__name__}: {error}"[:160])

    seen_at = _now()
    found = [
        business for element in (payload.get("elements") or [])
        if (business := _business_from(element, seen_at)) is not None
    ]
    # Sorted by name so two runs over the same box produce the same order, which is what
    # makes a diff between them mean something.
    found.sort(key=lambda b: (b.name.lower(), b.osm_id))
    return Listing(READ, area.name or area.bbox, tuple(found), tuple(categories), seen_at)


def describe_coverage(listings: Sequence[Listing]) -> str:
    """Which areas answered and which did not, in one line somebody can act on."""

    answered = [item.area for item in listings if item.status == READ]
    silent = [f"{item.area} ({item.status})" for item in listings if item.status != READ]
    line = f"{len(answered)} of {len(listings)} area(s) answered"
    if silent:
        line += (f"; silent: {', '.join(silent)}. Nothing was established about those "
                 f"areas at all")
    return line
