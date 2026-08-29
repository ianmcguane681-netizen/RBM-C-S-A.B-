"""Who is missing, recorded by a person, because nothing free and reliable reports it.

This connector exists to be honest about a gap rather than to fill it. Team news is the
single largest input a book prices on that this system cannot retrieve: there is no free,
structured, machine-readable feed of confirmed absentees, the aggregator sites that look
like one are scrapes of press conferences with no guarantee about either accuracy or
timing, and confirmed line-ups appear about an hour before kick-off, which is after the
prices worth taking have moved.

So there are two honest options, and this file takes the second.

**Guess.** Treat a missing report as a fit squad, apply no adjustment, and let the model
compete with a book that knows. That is the option that produces a working system with a
silent, systematic bias against it, and it is the shape of failure this whole repository is
organised around: an absence rendered as a fact.

**Say so.** Report UNKNOWN on every fixture nobody has recorded, let the model carry
"forecast as fully fit — the book is not making that assumption" out with the forecast, and
give a person somewhere to put what they know when they know it. A note typed after reading
a manager's press conference is a real observation with a real source, and it is worth more
than any scrape of the same conference would be.

The file it reads is `data/team-news.json`, the same shape as the rulebook store and for
the same reason: it is a record of somebody looking something up, so it carries who looked,
when, and where. A report older than the fixture's own build-up is STALE rather than
absent — an injury list from Monday is not the team news for Saturday, and the two must not
render alike.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

#: How old a team-news report may be before it stops describing this weekend. Three days
#: covers the ordinary Saturday build-up from midweek; past that a player has returned, a
#: new one has pulled up in training, or both.
STALE_AFTER_DAYS = 3


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, AttributeError, TypeError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


@dataclass(frozen=True, slots=True)
class Report:
    """What one person established about one team's availability, and when.

    `key_absences` is a count of players a reasonable observer would call first-choice, not
    a squad list. The count is what the model uses and the names are what make the count
    checkable — a report saying "two" with nobody named is a number nobody can argue with,
    which is the wrong kind of unarguable.
    """

    team: str
    key_absences: int
    names: tuple[str, ...]
    source: str
    reported_by: str
    reported_at: str

    def __post_init__(self) -> None:
        if self.key_absences < 0:
            raise ValueError(f"{self.team}: a negative absence count is not a reading")
        if not self.source.strip():
            raise ValueError(
                f"{self.team}: a report needs its source — the press conference, the club "
                f"statement, the article. Without it nobody can check it or date it")
        if not self.reported_by.strip():
            raise ValueError(f"{self.team}: a report needs the person who made it")
        if _parse(self.reported_at) is None:
            raise ValueError(
                f"{self.team}: reported_at {self.reported_at!r} is not a readable date, so "
                f"this report can never go out of date")
        if self.key_absences and len(self.names) not in (0, self.key_absences):
            raise ValueError(
                f"{self.team}: {self.key_absences} absence(s) reported and "
                f"{len(self.names)} named. Either name all of them or none — a partial "
                f"list reads as the whole one")

    def age_days(self, now: datetime | None = None) -> float | None:
        reported = _parse(self.reported_at)
        return None if reported is None else (
            (now or _now()) - reported).total_seconds() / 86400.0

    def is_stale(self, now: datetime | None = None,
                 stale_after_days: int = STALE_AFTER_DAYS) -> bool:
        age = self.age_days(now)
        return True if age is None else age > stale_after_days

    def describe(self, now: datetime | None = None) -> str:
        named = f" ({', '.join(self.names)})" if self.names else " (nobody named)"
        mark = "  STALE" if self.is_stale(now) else ""
        return (f"{self.team}: {self.key_absences} key absence(s){named}{mark}\n"
                f"  {self.reported_by} on {self.reported_at}, from {self.source}")


class TeamNews:
    """Reports on disk. Absent, unreadable and out of date are three different answers."""

    def __init__(self, path: str | Path, *, readable: bool = True, reason: str = "") -> None:
        self.path = Path(path)
        self.readable = readable
        self.reason = reason
        self.reports: list[Report] = []

    @classmethod
    def load(cls, path: str | Path) -> "TeamNews":
        news = cls(path)
        if not news.path.is_file():
            return news
        try:
            rows = json.loads(news.path.read_text(encoding="utf-8"))
            news.reports = [
                Report(**{**row, "names": tuple(row.get("names", ()))}) for row in rows]
        except (OSError, ValueError, TypeError) as error:
            return cls(path, readable=False,
                       reason=f"{type(error).__name__}: {error}"[:140])
        return news

    def latest(self, team: str) -> Report | None:
        """The most recent report for a team, or None. Most recent, because a later report
        supersedes an earlier one — a player passed fit on Friday is fit."""

        matching = [r for r in self.reports
                    if r.team.strip().lower() == str(team).strip().lower()]
        if not matching:
            return None
        return max(matching, key=lambda r: _parse(r.reported_at) or datetime.min.replace(
            tzinfo=timezone.utc))

    def feature(self, team: str, name: str, *, now: datetime | None = None):
        """A `lib.mispricing.Feature` for this team's absences, in one of three states.

        The whole point of the module in one method. No report is UNKNOWN with a reason
        that says a person can fix it; an old report is STALE rather than usable; and only
        a current one becomes a number the model may adjust on.
        """

        from lib.mispricing import KNOWN, STALE, UNKNOWN, Feature

        if not self.readable:
            return Feature(name, UNKNOWN, source=str(self.path), detail=(
                f"the team-news file could not be read ({self.reason}). Nobody's report "
                f"was consulted, which is not a report that everybody is fit"))

        report = self.latest(team)
        if report is None:
            return Feature(name, UNKNOWN, source=str(self.path), detail=(
                f"nobody has recorded team news for {team}. There is no free structured "
                f"feed for this, so it stays unknown until a person types what they read. "
                f"The book knows it."))
        if report.is_stale(now):
            return Feature(name, STALE, source=report.source, as_of=report.reported_at,
                           detail=(f"reported {report.reported_at}, more than "
                                   f"{STALE_AFTER_DAYS} days ago. A squad changes in three "
                                   f"days and this one may have"))
        return Feature(name, KNOWN, float(report.key_absences),
                       as_of=report.reported_at, source=report.source)

    def record(self, report: Report) -> None:
        if not self.readable:
            raise RuntimeError(
                f"refusing to write a team-news file that could not be read "
                f"({self.reason}): saving would discard every report already typed in")
        self.reports.append(report)

    def save(self) -> None:
        if not self.readable:
            raise RuntimeError("refusing to overwrite an unreadable team-news file")
        rows = [{**asdict(r), "names": list(r.names)}
                for r in sorted(self.reports, key=lambda r: (r.team, r.reported_at))]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")

    def describe(self, now: datetime | None = None) -> str:
        if not self.readable:
            return (f"UNREADABLE  {self.path}: {self.reason}\n"
                    f"  No report was consulted. Not a finding that everybody is fit.")
        if not self.reports:
            return (f"No team news has been recorded in {self.path}. Every fixture will "
                    f"be forecast as fully fit and will SAY SO — there is no free "
                    f"structured source for this, and the book has one.")
        fresh = [r for r in self.reports if not r.is_stale(now)]
        return (f"{len(self.reports)} report(s), {len(fresh)} still current within "
                f"{STALE_AFTER_DAYS} days")


def template() -> list[dict[str, Any]]:
    """The shape of the file, for somebody filling one in for the first time."""

    return [{
        "team": "Arsenal",
        "key_absences": 2,
        "names": ["a first-choice centre back", "a first-choice striker"],
        "source": "the manager's Friday press conference, as reported by <publication>",
        "reported_by": "Your Name",
        "reported_at": _now().date().isoformat(),
    }]
