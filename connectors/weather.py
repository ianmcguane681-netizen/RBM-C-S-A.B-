"""What the weather will be at a venue, or an honest answer about why that is not known.

Open-Meteo, because it is the only serious forecast API that needs no key at all — which
matters more here than accuracy does. A weather feature is one input among several and the
lane must be able to run without an operator signing up for anything; a source needing a
credential would mean the wind adjustment is UNKNOWN on every machine until somebody
registers, and an adjustment that is always unknown is an adjustment nobody notices is
missing.

Two things this connector is careful about, and both are the same care the odds connectors
take.

**A forecast has an age and a horizon, and neither is the same as being wrong.** A reading
retrieved an hour ago for a fixture in three days is a real forecast that will change. So
every reading carries `issued_at` and the hour it describes, and `WeatherReading.feature`
converts to `lib.mispricing.Feature` with a STALE state rather than silently using an old
number. What this module will not do is refuse a forecast for being three days out: that is
a judgement about how much to trust it, and it belongs to the model that consumes it.

**A venue is a place, and the place has to be established before the weather is.** Nothing
here guesses coordinates from a team name. `geocode` asks Open-Meteo's geocoding service by
name and returns `NOT_FOUND` when it finds nothing, which is a different answer from a
network failure and leads somewhere different: one is a name to correct, the other is a
request to repeat. A stadium's coordinates recorded once in `data/venues.json` are better
than either, and `VenueBook` is where they live.

The failure this file exists to avoid is small and specific: a timed-out weather call
becoming a still, dry evening in a goals model. `NOT_CONFIGURED`, `UNREACHABLE` and
`NOT_FOUND` are three states and none of them is a wind speed of zero.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from lib.http_retry import retrying_urlopen

FORECAST_BASE = "https://api.open-meteo.com/v1/forecast"
GEOCODE_BASE = "https://geocoding-api.open-meteo.com/v1/search"

READ = "READ"
UNREACHABLE = "UNREACHABLE"
NOT_FOUND = "NOT_FOUND"
#: The service answered and has no forecast for that hour. Its free forecast runs about 16
#: days ahead, so a fixture beyond that is not a failure and must not read as one.
OUT_OF_HORIZON = "OUT_OF_HORIZON"

#: How far from the requested kick-off hour a returned reading may be and still describe
#: the match. The API returns hourly values, so one hour is the resolution itself; beyond
#: that the reading is about a different part of the evening.
NEAREST_HOUR_TOLERANCE = 1

#: How old a forecast may be before it is reported STALE rather than READ. Open-Meteo
#: refreshes hourly, so anything past a few hours is a superseded run of the model — still
#: a forecast, and not the current one.
STALE_AFTER_HOURS = 6


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, AttributeError, TypeError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


@dataclass(frozen=True, slots=True)
class Place:
    """A resolved location, and where the resolution came from.

    `source` is not decoration. A coordinate somebody recorded from the club's own ground
    and a coordinate a geocoder matched to a town of the same name are different qualities
    of fact, and a model that adjusted for wind at the wrong stadium would be confidently
    wrong in a way nothing downstream could detect.
    """

    name: str
    latitude: float
    longitude: float
    source: str = ""

    def describe(self) -> str:
        return (f"{self.name} at {self.latitude:.4f}, {self.longitude:.4f} "
                f"({self.source or 'source not recorded'})")


@dataclass(frozen=True, slots=True)
class WeatherReading:
    """The conditions forecast for one hour at one place, or why there are none."""

    status: str
    place: str
    #: The hour this describes, as the service returned it.
    valid_at: str = ""
    #: When the forecast run was issued, so age can be judged rather than assumed.
    issued_at: str = ""
    temperature_c: float | None = None
    wind_speed_kph: float | None = None
    precipitation_mm: float | None = None
    reason: str = ""

    def age_hours(self, now: datetime | None = None) -> float | None:
        issued = _parse(self.issued_at)
        return None if issued is None else (
            (now or _now()) - issued).total_seconds() / 3600.0

    def is_stale(self, now: datetime | None = None) -> bool:
        age = self.age_hours(now)
        # An unreadable issue time is treated as stale. A forecast whose age cannot be
        # established has not been established to be current, and the direction that stops
        # an adjustment being applied is the direction to be wrong in.
        return True if age is None else age > STALE_AFTER_HOURS

    def features(self, now: datetime | None = None) -> tuple:
        """The three readings as `lib.mispricing.Feature`s, each carrying its own state.

        Per reading rather than per call, because a service can return a temperature and a
        null precipitation for the same hour, and a bundle that took the whole call's
        status would either discard a good reading or promote a missing one.
        """

        from lib.mispricing import KNOWN, STALE, UNKNOWN, Feature

        named = (("temperature_c", self.temperature_c),
                 ("wind_speed_kph", self.wind_speed_kph),
                 ("precipitation_mm", self.precipitation_mm))

        if self.status != READ:
            return tuple(
                Feature(name, UNKNOWN, source="open-meteo",
                        detail=f"{self.status}: {self.reason}")
                for name, _ in named)

        stale = self.is_stale(now)
        out = []
        for name, value in named:
            if value is None:
                out.append(Feature(name, UNKNOWN, source="open-meteo", as_of=self.valid_at,
                                   detail="the forecast carried no value for this hour"))
            elif stale:
                out.append(Feature(name, STALE, source="open-meteo", as_of=self.issued_at,
                                   detail=(f"issued {self.issued_at}, more than "
                                           f"{STALE_AFTER_HOURS}h ago; a newer run of the "
                                           f"model has superseded it")))
            else:
                out.append(Feature(name, KNOWN, float(value), as_of=self.valid_at,
                                   source="open-meteo"))
        return tuple(out)

    def describe(self) -> str:
        if self.status != READ:
            return (f"{self.status}  {self.place}: {self.reason}\n"
                    f"  No conditions were established. This is not a still, dry evening.")
        parts = [
            f"{self.temperature_c:.1f}C" if self.temperature_c is not None else "temp ?",
            (f"wind {self.wind_speed_kph:.0f} km/h" if self.wind_speed_kph is not None
             else "wind ?"),
            (f"rain {self.precipitation_mm:.1f} mm" if self.precipitation_mm is not None
             else "rain ?"),
        ]
        aged = " (STALE)" if self.is_stale() else ""
        return f"{self.place} at {self.valid_at}: {', '.join(parts)}{aged}"


class VenueBook:
    """Coordinates somebody recorded, read before anything is geocoded.

    A geocoder asked for "Anfield" will answer, and it will also answer for a street of
    that name in another country. Recorded coordinates are the better fact and this is
    consulted first; the geocoder is the fallback, and what it returns is marked as such.
    """

    def __init__(self, path: str | Path, *, readable: bool = True, reason: str = "") -> None:
        self.path = Path(path)
        self.readable = readable
        self.reason = reason
        self.places: dict[str, Place] = {}

    @classmethod
    def load(cls, path: str | Path) -> "VenueBook":
        book = cls(path)
        if not book.path.is_file():
            return book
        try:
            rows = json.loads(book.path.read_text(encoding="utf-8"))
            for row in rows:
                place = Place(str(row["name"]), float(row["latitude"]),
                              float(row["longitude"]),
                              str(row.get("source") or f"recorded in {book.path.name}"))
                book.places[place.name.strip().lower()] = place
        except (OSError, ValueError, TypeError, KeyError) as error:
            return cls(path, readable=False,
                       reason=f"{type(error).__name__}: {error}"[:140])
        return book

    def get(self, name: str) -> Place | None:
        return self.places.get(str(name).strip().lower())


def geocode(
    name: str,
    *,
    opener: Callable[..., Any] = retrying_urlopen,
    country: str = "",
) -> tuple[Place | None, str]:
    """Resolve a place name to coordinates. Returns `(place, reason)`, never raises.

    `reason` is empty on success and otherwise says which kind of failure it was, because
    NOT_FOUND and UNREACHABLE send a person to opposite ends of the problem: one is a name
    to correct, one is a request to make again.
    """

    if not str(name).strip():
        return None, "no place name was supplied"

    params = {"name": str(name).strip(), "count": "1", "format": "json"}
    if country:
        params["countryCode"] = country
    request = urllib.request.Request(
        f"{GEOCODE_BASE}?{urllib.parse.urlencode(params)}",
        headers={"User-Agent": "provena-mispricing/1.0"})
    try:
        with opener(request) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as error:  # noqa: BLE001 - any failure to ask is UNREACHABLE
        return None, f"{UNREACHABLE}: {type(error).__name__}: {error}"[:160]

    results = payload.get("results") or []
    if not results:
        return None, (f"{NOT_FOUND}: the geocoder has no place called {name!r}. That is an "
                      f"answer about the name, not about the network")
    first = results[0]
    try:
        return Place(str(first.get("name") or name), float(first["latitude"]),
                     float(first["longitude"]),
                     source=f"open-meteo geocoder, matched {first.get('name')!r} in "
                            f"{first.get('country') or 'an unnamed country'}"), ""
    except (KeyError, TypeError, ValueError) as error:
        return None, f"{UNREACHABLE}: the geocoder's answer had no usable coordinates ({error})"


def forecast_at(
    place: Place,
    when: str,
    *,
    opener: Callable[..., Any] = retrying_urlopen,
    now: datetime | None = None,
) -> WeatherReading:
    """The conditions forecast for the hour containing `when`, at `place`.

    Never raises. Every failure is a status, because a caller assembling evidence from four
    sources has to be able to say which ones answered — the argument `connectors/odds.py`
    makes about a scan that reached no book and reported no arb.
    """

    kickoff = _parse(when)
    if kickoff is None:
        return WeatherReading(UNREACHABLE, place.name, reason=(
            f"{when!r} is not a readable kick-off time, so no hour could be asked for"))

    moment = now or _now()
    horizon = (kickoff - moment).total_seconds() / 86400.0
    if horizon > 15.0:
        return WeatherReading(OUT_OF_HORIZON, place.name, reason=(
            f"kick-off is {horizon:.1f} days away and the free forecast runs about 16 "
            f"days ahead. The service is working; there is simply no forecast yet"))

    params = {
        "latitude": f"{place.latitude:.4f}",
        "longitude": f"{place.longitude:.4f}",
        "hourly": "temperature_2m,wind_speed_10m,precipitation",
        "windspeed_unit": "kmh",
        "timezone": "UTC",
        # A window rather than a single hour: the API returns whole days, and asking for
        # the day either side of kick-off covers a fixture near midnight UTC without a
        # second request.
        "start_date": (kickoff - timedelta(days=1)).date().isoformat(),
        "end_date": (kickoff + timedelta(days=1)).date().isoformat(),
    }
    request = urllib.request.Request(
        f"{FORECAST_BASE}?{urllib.parse.urlencode(params)}",
        headers={"User-Agent": "provena-mispricing/1.0"})
    try:
        with opener(request) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as error:  # noqa: BLE001
        return WeatherReading(UNREACHABLE, place.name,
                              reason=f"{type(error).__name__}: {error}"[:160])

    return _hour_from(payload, place, kickoff, moment)


def _hour_from(payload: Mapping[str, Any], place: Place, kickoff: datetime,
               moment: datetime) -> WeatherReading:
    """Pick the hour nearest kick-off, and refuse if the nearest one is not near.

    Taking the closest available hour whatever its distance is how a Saturday-evening
    fixture gets Sunday-morning weather. The tolerance is one hour because the data is
    hourly; anything further away describes a different part of the evening.
    """

    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    if not times:
        return WeatherReading(UNREACHABLE, place.name, reason=(
            "the service answered with no hourly series at all"))

    parsed = [(index, _parse(value)) for index, value in enumerate(times)]
    usable = [(index, stamp) for index, stamp in parsed if stamp is not None]
    if not usable:
        return WeatherReading(UNREACHABLE, place.name,
                              reason="no timestamp in the hourly series could be read")

    index, stamp = min(usable, key=lambda row: abs((row[1] - kickoff).total_seconds()))
    gap_hours = abs((stamp - kickoff).total_seconds()) / 3600.0
    if gap_hours > NEAREST_HOUR_TOLERANCE:
        return WeatherReading(OUT_OF_HORIZON, place.name, reason=(
            f"the nearest hour returned is {gap_hours:.1f}h from kick-off, outside the "
            f"{NEAREST_HOUR_TOLERANCE}h tolerance. Conditions {gap_hours:.0f} hours away "
            f"are a different part of the evening"))

    def at(key: str) -> float | None:
        series = hourly.get(key) or []
        if index >= len(series):
            return None
        value = series[index]
        return None if value is None else float(value)

    # The generation time is the forecast run's own stamp. Absent, the reading is treated
    # as of unknown age, which `is_stale` reports as stale.
    issued = str(payload.get("generationtime_stamp") or "")
    if not issued:
        issued = moment.isoformat(timespec="seconds").replace("+00:00", "Z")

    return WeatherReading(
        READ, place.name,
        valid_at=stamp.isoformat(timespec="seconds").replace("+00:00", "Z"),
        issued_at=issued,
        temperature_c=at("temperature_2m"),
        wind_speed_kph=at("wind_speed_10m"),
        precipitation_mm=at("precipitation"),
    )


def conditions_for(
    venue: str,
    kickoff: str,
    *,
    venues: VenueBook | None = None,
    opener: Callable[..., Any] = retrying_urlopen,
    now: datetime | None = None,
) -> tuple[WeatherReading, Place | None]:
    """Venue name to conditions, recorded coordinates first and the geocoder second."""

    place = venues.get(venue) if venues is not None else None
    if place is None:
        place, reason = geocode(venue, opener=opener)
        if place is None:
            status = NOT_FOUND if reason.startswith(NOT_FOUND) else UNREACHABLE
            return WeatherReading(status, venue, reason=reason), None
    return forecast_at(place, kickoff, opener=opener, now=now), place
