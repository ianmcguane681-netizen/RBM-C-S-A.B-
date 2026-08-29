"""League tables and fixtures from football-data.org, and what it means when there are none.

The only free source of structured football results this repository could find that is
neither a scrape nor a licensed feed. The free tier covers a dozen competitions including
the Premier League, at ten requests a minute, which is far more than a lane running every
few hours needs.

**What it gives, and the gap that matters.** Standings — played, won, drawn, lost, goals
for and against — which is exactly what `lib.mispricing.league_strengths` turns into attack
and defence figures. Fixtures with kick-off times and, on most competitions, a venue name.
What it does not give is expected goals, shots, or anything about who is fit. Those are the
inputs a book actually prices on, and their absence is the honest reason to expect a model
built on this to be beaten by a book more often than not. Recorded here rather than
discovered later.

**Goals scored is a lagging measure and this connector does not pretend otherwise.** A
league table in August is four matches of noise; in May it describes a season that is
nearly over. `Standings` carries `matches_played` so a consumer can refuse a table with too
little in it, and `lib.mispricing.league_strengths` omits a team with no games rather than
calling it average.

No credential lives here. The key is read from `~/.footballdata/key`, and its absence is
`NOT_CONFIGURED` — a state, never an exception — so a lane that could not look says so
instead of reporting an empty league.
"""
from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

from lib.http_retry import retrying_urlopen

BASE = "https://api.football-data.org/v4"

CONFIGURED = "CONFIGURED"
NOT_CONFIGURED = "NOT_CONFIGURED"
UNREACHABLE = "UNREACHABLE"
READ = "READ"

#: Free-tier competition codes, so a caller naming one that is not covered is told rather
#: than shown an empty league. The tier changes; this is what it covered on 2026-08-29 and
#: an unlisted code is still ATTEMPTED — the list warns, it does not gate.
FREE_TIER_COMPETITIONS = (
    "PL", "ELC", "BL1", "SA", "PD", "FL1", "PPL", "DED", "BSA", "CL", "EC", "WC",
)

#: Below this many matches played, a league table is noise rather than a measurement. Ten
#: is roughly a quarter of a European league season — enough that one 5-0 no longer moves
#: a team's rate by half, and early enough to be useful before Christmas.
MINIMUM_MATCHES_FOR_STRENGTH = 10


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class Credentials:
    """A key read from a directory the operator controls. Never from this repository."""

    key: str

    @classmethod
    def load(cls, directory: str | Path = "~/.footballdata") -> "Credentials | None":
        path = Path(directory).expanduser() / "key"
        try:
            key = path.read_text(encoding="utf-8").strip()
        except OSError:
            return None
        return cls(key) if key else None


@dataclass(frozen=True, slots=True)
class TeamRow:
    """One team's line in a league table."""

    team: str
    played: int
    goals_for: int
    goals_against: int
    position: int = 0

    def as_mapping(self) -> dict[str, Any]:
        """The shape `lib.mispricing.league_strengths` reads."""

        return {"team": self.team, "played": self.played,
                "goals_for": self.goals_for, "goals_against": self.goals_against}


@dataclass(frozen=True, slots=True)
class Standings:
    """A competition's table, or why there is not one."""

    status: str
    competition: str
    rows: tuple[TeamRow, ...] = ()
    season: str = ""
    retrieved_at: str = ""
    reason: str = ""

    @property
    def matches_played(self) -> int:
        """Total team-matches in the table. Two per fixture, and that is fine: it is used
        as a measure of how much evidence the table holds, not as a fixture count."""

        return sum(row.played for row in self.rows)

    @property
    def has_enough_evidence(self) -> bool:
        """Whether any team has played enough for its rate to mean something.

        The MINIMUM applies per team rather than to the total, because a table where one
        side has played fourteen and another four is not a table with an average of nine —
        the four-game team's rate is still noise and the model would use it as though it
        were not.
        """

        return bool(self.rows) and min(row.played for row in self.rows) >= (
            MINIMUM_MATCHES_FOR_STRENGTH)

    def team(self, name: str) -> TeamRow | None:
        wanted = str(name).strip().lower()
        return next((r for r in self.rows if r.team.strip().lower() == wanted), None)

    def describe(self) -> str:
        if self.status == NOT_CONFIGURED:
            return (f"{self.competition}: NOT_CONFIGURED — {self.reason}. No table was "
                    f"retrieved. This is not a finding that the competition has no table.")
        if self.status == UNREACHABLE:
            return (f"{self.competition}: UNREACHABLE — {self.reason}. The table is "
                    f"unknown, not absent.")
        note = "" if self.has_enough_evidence else (
            f"  NOT ENOUGH EVIDENCE: a team has played fewer than "
            f"{MINIMUM_MATCHES_FOR_STRENGTH} matches, so its scoring rate is noise and "
            f"strengths derived from it would be a confident number with nothing behind it.")
        return (f"{self.competition} {self.season}: {len(self.rows)} team(s), "
                f"{self.matches_played} team-matches played, read {self.retrieved_at}"
                + (f"\n{note}" if note else ""))


@dataclass(frozen=True, slots=True)
class Fixture:
    """One scheduled match, with the venue when the competition publishes one."""

    home: str
    away: str
    kickoff: str
    competition: str = ""
    venue: str = ""
    matchday: int = 0

    @property
    def subject(self) -> str:
        """The same naming the odds feed uses, so the two can be matched on one string."""

        return f"{self.home} v {self.away} @ {self.kickoff}"


@dataclass(frozen=True, slots=True)
class Fixtures:
    status: str
    competition: str
    matches: tuple[Fixture, ...] = ()
    retrieved_at: str = ""
    reason: str = ""

    def describe(self) -> str:
        if self.status != READ:
            return (f"{self.competition}: {self.status} — {self.reason}. No fixture list "
                    f"was retrieved, which is not a finding that nothing is scheduled.")
        return (f"{self.competition}: {len(self.matches)} fixture(s), "
                f"read {self.retrieved_at}")


@dataclass
class FootballData:
    """The client. Every method returns a status and none of them raises for an absence."""

    credentials: Credentials | None = None
    opener: Callable[..., Any] = retrying_urlopen
    #: Set on the last successful call, so a caller can report which competitions answered.
    answered: list[str] = field(default_factory=list)

    @classmethod
    def from_directory(cls, directory: str | Path = "~/.footballdata",
                       **kw: Any) -> "FootballData":
        return cls(Credentials.load(directory), **kw)

    @property
    def is_configured(self) -> bool:
        return self.credentials is not None

    def _get(self, path: str) -> Any:
        assert self.credentials is not None
        request = urllib.request.Request(
            f"{BASE}{path}",
            headers={"X-Auth-Token": self.credentials.key,
                     "User-Agent": "provena-mispricing/1.0"})
        with self.opener(request) as response:
            return json.loads(response.read().decode("utf-8"))

    def standings(self, competition: str) -> Standings:
        if not self.is_configured:
            return Standings(NOT_CONFIGURED, competition, reason=(
                "no key at ~/.footballdata/key. Free registration at football-data.org"))
        try:
            payload = self._get(f"/competitions/{competition}/standings")
        except Exception as error:  # noqa: BLE001 - any failure to reach it is UNREACHABLE
            return Standings(UNREACHABLE, competition,
                             reason=f"{type(error).__name__}: {error}"[:160])

        # The API returns several tables — TOTAL, HOME, AWAY. TOTAL is the one whose rates
        # the model wants; picking the first would silently take HOME on the competitions
        # that order them differently, and a home-only attack strength multiplied by a home
        # advantage would count the same effect twice.
        tables = [t for t in (payload.get("standings") or [])
                  if str(t.get("type") or "").upper() == "TOTAL"]
        if not tables:
            return Standings(UNREACHABLE, competition, reason=(
                "the answer carried no TOTAL table. Taking another one would mix a "
                "home-only rate into a model that applies its own home advantage"))

        rows: list[TeamRow] = []
        for entry in tables[0].get("table") or []:
            name = str((entry.get("team") or {}).get("name") or "").strip()
            if not name:
                continue
            rows.append(TeamRow(
                team=name,
                played=int(entry.get("playedGames") or 0),
                goals_for=int(entry.get("goalsFor") or 0),
                goals_against=int(entry.get("goalsAgainst") or 0),
                position=int(entry.get("position") or 0),
            ))
        season = str((payload.get("season") or {}).get("startDate") or "")
        self.answered.append(competition)
        return Standings(READ, competition, tuple(rows), season, _now())

    def fixtures(self, competition: str, *, days_ahead: int = 7) -> Fixtures:
        if not self.is_configured:
            return Fixtures(NOT_CONFIGURED, competition, reason=(
                "no key at ~/.footballdata/key"))
        try:
            payload = self._get(
                f"/competitions/{competition}/matches?status=SCHEDULED")
        except Exception as error:  # noqa: BLE001
            return Fixtures(UNREACHABLE, competition,
                            reason=f"{type(error).__name__}: {error}"[:160])

        matches: list[Fixture] = []
        for entry in payload.get("matches") or []:
            home = str((entry.get("homeTeam") or {}).get("name") or "").strip()
            away = str((entry.get("awayTeam") or {}).get("name") or "").strip()
            kickoff = str(entry.get("utcDate") or "").strip()
            if not (home and away and kickoff):
                # Skipped rather than half-filled. A fixture missing a side or a time
                # cannot be matched to an odds market, and a placeholder would match the
                # wrong one.
                continue
            matches.append(Fixture(
                home=home, away=away, kickoff=kickoff, competition=competition,
                venue=str(entry.get("venue") or "").strip(),
                matchday=int(entry.get("matchday") or 0),
            ))
        return Fixtures(READ, competition, tuple(matches), _now())


def rest_days(kickoff: str, last_played: str) -> float | None:
    """Days between a side's previous fixture and this one. `None` when either is unknown.

    None rather than a plausible seven. A team whose last fixture nobody could establish is
    not a well-rested team, and the model treats the two differently.
    """

    from lib.mispricing import _parse  # noqa: PLC0415 - one date parser, not two

    start, previous = _parse(kickoff), _parse(last_played)
    if start is None or previous is None:
        return None
    return (start - previous).total_seconds() / 86400.0


def strengths_from(standings: Standings) -> tuple[dict, float, str]:
    """Attack and defence per team from a table, with the refusal stated rather than raised.

    Returns `(strengths, league_goals_per_team, refusal)`. A non-empty refusal means the
    strengths are empty and why — a table that was never retrieved and a table with four
    matches in it are different problems and the caller has to be able to tell a person
    which one they have.
    """

    from lib.mispricing import league_strengths

    if standings.status != READ:
        return {}, 0.0, (f"the {standings.competition} table was not retrieved "
                         f"({standings.status}: {standings.reason})")
    if not standings.has_enough_evidence:
        return {}, 0.0, (
            f"the {standings.competition} table holds fewer than "
            f"{MINIMUM_MATCHES_FOR_STRENGTH} matches for at least one team. Scoring rates "
            f"from that are noise, and a strength computed from noise is a confident "
            f"number with nothing behind it")

    strengths, rate = league_strengths([row.as_mapping() for row in standings.rows])
    if not strengths:
        return {}, 0.0, (f"no team in the {standings.competition} table has played a "
                         f"match, so no rate exists to be relative to")
    return strengths, rate, ""


def describe_sources(results: Sequence[Any]) -> str:
    """Which competitions answered and which did not, in one line a person can act on."""

    answered = [r.competition for r in results if getattr(r, "status", "") == READ]
    silent = [f"{r.competition} ({r.status})" for r in results
              if getattr(r, "status", "") != READ]
    if not silent:
        return f"{len(answered)} of {len(results)} competition(s) answered"
    return (f"{len(answered)} of {len(results)} competition(s) answered; silent: "
            f"{', '.join(silent)}. Anything not found in a silent competition was not "
            f"looked for")
