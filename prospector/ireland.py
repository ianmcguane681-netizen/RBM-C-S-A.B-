"""Ireland, as the thing you actually point this at — and the naming traps in doing so.

The tool is not Irish-specific and this file does not make it so. What it holds is the list
of areas worth scanning on this island, spelled the way OpenStreetMap spells them, with the
handful of places where the obvious name is the wrong one. Every one of those traps costs a
run: `--area "Cork"` searches something, reports businesses, and quietly means a different
Cork than the one you had in mind.

## The traps, all four of them

**Cork, Galway, Limerick and Waterford are each two areas.** The city is its own local
authority and is not inside the county. Scanning "County Cork" and expecting Cork City in
the results is the single most likely way to conclude a county is empty when it is not.

**Dublin is four.** Dublin City, Fingal, South Dublin and Dún Laoghaire–Rathdown. "County
Dublin" is a traditional county that no longer administers anything, and what it matches in
OSM varies.

**Tipperary is one now.** North and South Riding merged in 2014; both names still appear in
older data and neither is a current authority.

**The North is a different country for the rules that matter here.** Antrim, Armagh, Down,
Fermanagh, Londonderry/Derry and Tyrone are in the United Kingdom: PECR rather than the
Irish implementation of ePrivacy, sterling rather than euro, and postcodes rather than
Eircodes. `countries.py` gets that right from the area's ISO code; this file groups them
separately so nobody scans "Ireland" and assumes one rulebook covers the results.

## What this file will not do

Guess which spelling OSM carries today. Names change, and the run reports how many areas
matched and searches all of them, which is a better answer than a hard-coded id going stale
in a file nobody re-checks. Where a name is genuinely ambiguous it is noted here and the
alternative is given.
"""
from __future__ import annotations

from dataclasses import dataclass

IE = "IE"
GB = "GB"

#: The Eircode shape, for reference. Already matched by the standard's address check —
#: repeated here because it is the one piece of Irish-specific formatting that shows up in
#: a contact block, and because "A65 F4E2" has a space in it that half of the internet's
#: postcode regexes drop.
EIRCODE = r"[A-Z]\d{2}\s?[A-Z0-9]{4}"


@dataclass(frozen=True, slots=True)
class Area:
    """One place to point a scan at."""

    name: str
    country: str
    note: str = ""
    #: Another spelling worth trying if the first matches nothing. Names in OSM move.
    also: str = ""

    @property
    def is_local_authority(self) -> bool:
        return not self.note.startswith("traditional county")


#: The 31 local authorities of the Republic, which is the administrative reality and the
#: level most likely to resolve cleanly.
REPUBLIC: tuple[Area, ...] = (
    Area("Carlow", IE, also="County Carlow"),
    Area("Cavan", IE, also="County Cavan"),
    Area("Clare", IE, also="County Clare"),
    Area("Cork City", IE, "its own authority — NOT inside County Cork"),
    Area("County Cork", IE, "excludes Cork City; scan both", also="Cork"),
    Area("Donegal", IE, also="County Donegal"),
    Area("Dublin City", IE, "one of the four Dublin authorities"),
    Area("Fingal", IE, "north County Dublin: Swords, Balbriggan, Malahide"),
    Area("South Dublin", IE, "Tallaght, Clondalkin, Lucan"),
    Area("Dún Laoghaire–Rathdown", IE, "note the en dash; try the hyphen spelling too",
         also="Dun Laoghaire-Rathdown"),
    Area("Galway City", IE, "its own authority — NOT inside County Galway"),
    Area("County Galway", IE, "excludes Galway City; scan both", also="Galway"),
    Area("Kerry", IE, also="County Kerry"),
    Area("Kildare", IE, also="County Kildare"),
    Area("Kilkenny", IE, also="County Kilkenny"),
    Area("Laois", IE, also="County Laois"),
    Area("Leitrim", IE, also="County Leitrim"),
    Area("Limerick", IE, "city and county merged in 2014 into one authority",
         also="County Limerick"),
    Area("Longford", IE, also="County Longford"),
    Area("Louth", IE, also="County Louth"),
    Area("Mayo", IE, also="County Mayo"),
    Area("Meath", IE, also="County Meath"),
    Area("Monaghan", IE, also="County Monaghan"),
    Area("Offaly", IE, also="County Offaly"),
    Area("Roscommon", IE, also="County Roscommon"),
    Area("Sligo", IE, also="County Sligo"),
    Area("Tipperary", IE, "North and South Riding merged in 2014; both still appear in "
                          "older data and neither is current", also="County Tipperary"),
    Area("Waterford", IE, "city and county merged in 2014 into one authority",
         also="County Waterford"),
    Area("Westmeath", IE, also="County Westmeath"),
    Area("Wexford", IE, also="County Wexford"),
    Area("Wicklow", IE, also="County Wicklow"),
)

#: Northern Ireland. In the United Kingdom for every rule this tool prints: PECR rather
#: than the Irish ePrivacy implementation, sterling, and UK postcodes.
NORTH: tuple[Area, ...] = (
    Area("County Antrim", GB, "United Kingdom: PECR, sterling, UK postcodes"),
    Area("County Armagh", GB, "United Kingdom: PECR, sterling, UK postcodes"),
    Area("County Down", GB, "United Kingdom: PECR, sterling, UK postcodes"),
    Area("County Fermanagh", GB, "United Kingdom: PECR, sterling, UK postcodes"),
    Area("County Londonderry", GB, "United Kingdom; also mapped as County Derry",
         also="County Derry"),
    Area("County Tyrone", GB, "United Kingdom: PECR, sterling, UK postcodes"),
)

#: The whole island in one query. Listed because somebody will try it, with the reason not
#: to: Overpass runs on donated hardware, a country-wide business query is a request to be
#: rate-limited, and a run that dies halfway leaves you unable to tell an empty county from
#: an interrupted one.
WHOLE = (
    Area("Ireland", IE, "the state, in one query — expect a timeout and a rate limit. "
                        "Scan county by county instead"),
)

ALL: tuple[Area, ...] = REPUBLIC + NORTH


def areas(include_north: bool = True) -> tuple[Area, ...]:
    return ALL if include_north else REPUBLIC


def find(name: str) -> Area | None:
    """The area matching `name` under either spelling, or `None`."""

    wanted = (name or "").strip().casefold()
    for area in ALL + WHOLE:
        if wanted in (area.name.casefold(), (area.also or "").casefold()):
            return area
    return None


def country_of(name: str) -> str:
    """`IE`, `GB`, or an empty string where this file does not know the area.

    An empty string rather than a guess: `countries.py` reads the ISO code off the area
    relation and is the better answer, and a default of IE here would quietly print Irish
    sending rules for a scan of Ballymena.
    """

    area = find(name)
    return area.country if area else ""
