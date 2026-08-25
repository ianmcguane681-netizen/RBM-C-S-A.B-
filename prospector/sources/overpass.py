"""Businesses in an area, from OpenStreetMap via Overpass.

OpenStreetMap is the source for v1 for one reason that outranks its coverage: it is
redistributable. Google's Places terms forbid storing most of what it returns, which makes
a local register of who has been prepared and when — the thing that stops a business being
pitched twice — a licence breach rather than a design choice. OSM under ODbL permits the
register, and requires attribution, which the generated pages carry.

The cost is coverage, and it is a real cost stated rather than discovered: a rural county
carries a fraction of its businesses, and website tags are sparser still. That does not
make the tool wrong, it makes `NO_SITE_LISTED` mean less than it looks like it means, which
is why `presence.py` refuses to promote it to a claim about the business.

## Two queries, not one, and the second one is the point

Overpass will resolve an area and select inside it in a single request. Doing that makes an
unknown area name and an area with no matching businesses return the same empty list — a
typo in "County Donegal" reporting an empty county. So the area is resolved first, and a
name that resolves to nothing returns `AREA_UNKNOWN` rather than a clean, confident, wrong
zero. The extra request is the price of being able to tell those apart.

## What a failure returns

Never an empty list. A timeout, a 429, a 504 under load, an endpoint that has been blocked
by a corporate proxy — all `SOURCE_UNREADABLE` with the reason attached, because a lane
that reports "no businesses found" when it could not reach the directory is the recurring
defect at the top of the pipeline, where it poisons everything downstream.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Sequence

from prospector.business import ABSENT, Business, Fact
from prospector.states import AREA_UNKNOWN, LOOKED, SOURCE_UNREADABLE

#: The public instance. Overridable per call: mirrors exist, some carry regional extracts
#: only, and some networks block one and not another.
DEFAULT_ENDPOINT = "https://overpass-api.de/api/interpreter"

#: Identifies the caller to a free service run on donated hardware. Overpass asks for this
#: and blocks unidentified bulk traffic, which is entirely reasonable of it.
USER_AGENT = "prospector/0.1 (+https://github.com/ianmcguane681-netizen)"

ATTRIBUTION = ("Business details from OpenStreetMap contributors, available under the "
               "Open Database Licence (ODbL).")

#: What counts as a business worth preparing a site for. Curated rather than "everything
#: with a name", because an area query without a filter returns bus stops and post boxes,
#: and a pipeline whose first stage is 90% noise gets its later stages tuned to the noise.
DEFAULT_KINDS: tuple[str, ...] = (
    'shop',
    'craft',
    'office',
    'amenity~"^(restaurant|cafe|pub|bar|fast_food|veterinary|dentist|driving_school|childcare)$"',
    'tourism~"^(hotel|guest_house|bed_and_breakfast|caravan_site|camp_site)$"',
    'leisure~"^(fitness_centre|sports_centre)$"',
    'healthcare',
)

#: Tags that name a business rather than describe it. Read into `Business.fields`.
_FIELD_TAGS = {
    "phone": ("phone", "contact:phone", "contact:mobile"),
    "email": ("email", "contact:email"),
    "street": ("addr:street",),
    "housenumber": ("addr:housenumber",),
    "city": ("addr:city", "addr:town", "addr:village"),
    "postcode": ("addr:postcode",),
    "opening_hours": ("opening_hours",),
    "cuisine": ("cuisine",),
    "facebook": ("contact:facebook", "facebook"),
    "instagram": ("contact:instagram", "instagram"),
}

_WEBSITE_TAGS = ("website", "contact:website", "url", "brand:website")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True, slots=True)
class Discovery:
    """What one look at one area produced, and whether it was a look at all."""

    status: str
    area: str
    businesses: tuple[Business, ...] = ()
    reason: str = ""
    endpoint: str = ""
    at: str = field(default_factory=_now)

    def describe(self) -> str:
        if self.status == LOOKED:
            return (f"LOOKED  [{self.area}]  {len(self.businesses)} businesses\n"
                    f"  via {self.endpoint}")
        if self.status == AREA_UNKNOWN:
            return (f"AREA_UNKNOWN  [{self.area}]\n"
                    f"  No administrative area of that name exists in OpenStreetMap. This "
                    f"is not an empty area — nothing was searched. Try the name as it "
                    f"appears on openstreetmap.org, e.g. 'County Donegal', 'Ireland'.")
        return (f"SOURCE_UNREADABLE  [{self.area}]\n  {self.reason}\n"
                f"  The directory could not be read, so nothing is known about this area. "
                f"That is not the same as the area having no businesses.")


class _Transport:
    """Overpass over stdlib HTTP. Separated so tests can substitute it without a network."""

    def __init__(self, endpoint: str = DEFAULT_ENDPOINT, timeout: float = 180.0) -> None:
        self.endpoint = endpoint
        self.timeout = timeout

    def query(self, ql: str) -> Any:
        request = urllib.request.Request(
            self.endpoint,
            data=urllib.parse.urlencode({"data": ql}).encode("utf-8"),
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))


def _area_query(area: str) -> str:
    escaped = area.replace('"', '\\"')
    # Administrative boundaries only. Without the filter, "Donegal" matches the town, a
    # townland and a electoral division, and the selection silently becomes the smallest.
    return (f'[out:json][timeout:90];'
            f'relation["name"="{escaped}"]["boundary"="administrative"];out ids tags;')


def _poi_query(area_ids: Sequence[int], kinds: Sequence[str], limit: int) -> str:
    #: Overpass area ids are relation id + 3600000000. Documented, stable, and the only way
    #: to select "inside this relation" without re-resolving the name.
    areas = "".join(f"area({3600000000 + rid})->.a{i};" for i, rid in enumerate(area_ids))
    unions = []
    for i in range(len(area_ids)):
        for kind in kinds:
            unions.append(f'nwr[{kind}]["name"](area.a{i});')
    return (f'[out:json][timeout:180];{areas}'
            f'({"".join(unions)});out center {int(limit)};')


def _fact(tags: dict[str, Any], names: Sequence[str], source: str, at: str) -> Fact | str:
    for name in names:
        value = str(tags.get(name, "")).strip()
        if value:
            return Fact(value=value, source=source, retrieved_at=at)
    return ABSENT


def to_business(element: dict[str, Any], *, at: str) -> Business | None:
    """One Overpass element as a `Business`, or `None` if it has no name.

    An unnamed element is not a business this tool can do anything with: the deliverable is
    a page with the business's name on it, and there is nothing to put there.
    """

    tags = element.get("tags") or {}
    name = str(tags.get("name", "")).strip()
    if not name:
        return None
    identity = f"{element.get('type', 'node')}/{element.get('id', '')}"
    source = f"openstreetmap:{identity}"
    kind = ABSENT
    for key in ("shop", "amenity", "craft", "office", "tourism", "leisure", "healthcare"):
        if tags.get(key):
            kind = Fact(value=str(tags[key]), source=source, retrieved_at=at)
            break
    if kind is ABSENT:
        kind = Fact(value="business", source=source, retrieved_at=at)
    fields = {}
    for field_name, tag_names in _FIELD_TAGS.items():
        value = _fact(tags, tag_names, source, at)
        if isinstance(value, Fact):
            fields[field_name] = value
    return Business(
        identity=identity,
        name=Fact(value=name, source=source, retrieved_at=at),
        kind=kind,
        website=_fact(tags, _WEBSITE_TAGS, source, at),
        fields=fields,
        raw={"tags": dict(tags), "lat": element.get("lat"), "lon": element.get("lon"),
             "center": element.get("center")},
    )


def discover(area: str, *, kinds: Sequence[str] = DEFAULT_KINDS, limit: int = 200,
             transport: Any = None) -> Discovery:
    """Businesses in `area`, or a stated reason there are none to report."""

    transport = transport or _Transport()
    endpoint = getattr(transport, "endpoint", "")
    at = _now()
    try:
        resolved = transport.query(_area_query(area))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError,
            ValueError) as exc:
        return Discovery(SOURCE_UNREADABLE, area, reason=f"resolving the area: {exc!r}",
                         endpoint=endpoint, at=at)
    area_ids = [int(e["id"]) for e in resolved.get("elements", []) if e.get("id")]
    if not area_ids:
        return Discovery(AREA_UNKNOWN, area, endpoint=endpoint, at=at)
    try:
        found = transport.query(_poi_query(area_ids, kinds, limit))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError,
            ValueError) as exc:
        return Discovery(SOURCE_UNREADABLE, area, reason=f"selecting businesses: {exc!r}",
                         endpoint=endpoint, at=at)
    businesses = []
    for element in found.get("elements", []):
        business = to_business(element, at=at)
        if business is not None:
            businesses.append(business)
    return Discovery(LOOKED, area, businesses=tuple(businesses), endpoint=endpoint, at=at)
