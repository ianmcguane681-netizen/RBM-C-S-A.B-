"""Keeping a live site honest: what changed since last time, and what changed for the worse.

Monitoring is the part of this that is a promise rather than a piece of work. Once a
business is paying to have their site watched, silence has to mean something — and the only
way silence means anything is if the watcher can tell the difference between "I looked and
it is fine" and "I could not look". A monitor that reports nothing wrong when it never
managed to load the page is worse than no monitor, because it converts an outage into a
reassurance.

    INTACT       looked, and every criterion is where it was
    IMPROVED     something that was failing now passes
    REGRESSED    something that was passing now fails, and which is named
    GONE         the site did not answer at all, on two attempts
    UNREADABLE   the baseline could not be read, so nothing can be compared
    NOT_WATCHED  no baseline exists yet. The first run records one and says so

`REGRESSED` and `GONE` are the ones that wake somebody. `UNREADABLE` is not a quiet state
either: it means the watch is not running, which is a thing the person paying for it would
want to know that day rather than at renewal.

## What it compares

The standard, criterion by criterion, plus the certificate expiry, which is the single most
common way a small site goes from working to frightening overnight. Nothing here is a
score and nothing is a trend: a criterion either moved or it did not, and the report names
which ones.

## What it does not do

It does not fix anything, and it does not notify anybody — this returns a result and the
caller decides. Both of those are real work and neither should be invented here: an
autonomous fixer editing a client's live site at 3am is exactly the kind of thing this
whole repository exists to refuse.
"""
from __future__ import annotations

import json
import socket
import ssl
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from prospector import browser, condition as condition_mod, standard

INTACT = "INTACT"
IMPROVED = "IMPROVED"
REGRESSED = "REGRESSED"
GONE = "GONE"
UNREADABLE = "UNREADABLE"
NOT_WATCHED = "NOT_WATCHED"

#: A certificate inside this many days is a problem to raise now, not on the day.
CERT_WARNING_DAYS = 21


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True, slots=True)
class Change:
    """One criterion that moved."""

    code: str
    was: str
    now: str
    detail: str = ""

    @property
    def worse(self) -> bool:
        return self.now == standard.FAILS and self.was == standard.MEETS


@dataclass(frozen=True, slots=True)
class Watch:
    """One look at a live site, against the last one."""

    status: str
    url: str = ""
    changes: tuple[Change, ...] = ()
    certificate_days_left: int | None = None
    reason: str = ""
    at: str = field(default_factory=_now)

    @property
    def needs_attention(self) -> bool:
        """Whether a person should hear about this today."""

        return (self.status in (REGRESSED, GONE, UNREADABLE)
                or (self.certificate_days_left is not None
                    and self.certificate_days_left <= CERT_WARNING_DAYS))

    def describe(self) -> str:
        lines = [f"{self.status}  {self.url}"]
        if self.reason:
            lines.append(f"  {self.reason}")
        for change in self.changes:
            mark = "WORSE" if change.worse else "     "
            lines.append(f"  {mark} {change.code}: {change.was} -> {change.now}"
                         + (f" ({change.detail})" if change.detail else ""))
        if self.certificate_days_left is not None:
            if self.certificate_days_left <= CERT_WARNING_DAYS:
                lines.append(f"  CERTIFICATE expires in {self.certificate_days_left} days "
                             f"— browsers will refuse the site outright when it does")
            else:
                lines.append(f"  certificate good for {self.certificate_days_left} days")
        if self.status == UNREADABLE:
            lines.append("  Nothing was compared. That is not the same as nothing having "
                         "changed, and it means the watch is not running.")
        if self.status == NOT_WATCHED:
            lines.append("  A baseline has been recorded. From the next run this compares.")
        return "\n".join(lines)


def certificate_days_left(url: str, *, timeout: float = 10.0) -> int | None:
    """Days until the TLS certificate expires, or `None` where that could not be told.

    `None` rather than a large number, because a monitor that cannot read a certificate
    and reports plenty of time is the defect this package is built around, pointed at the
    one failure that takes a site off the internet on a known date.
    """

    if not url.lower().startswith("https://"):
        return None
    host = url.split("://", 1)[1].split("/")[0].split(":")[0]
    try:
        context = ssl.create_default_context()
        with socket.create_connection((host, 443), timeout=timeout) as raw:
            with context.wrap_socket(raw, server_hostname=host) as tls:
                not_after = tls.getpeercert().get("notAfter")
    except (OSError, ssl.SSLError, ValueError, KeyError, AttributeError):
        return None
    if not not_after:
        return None
    try:
        expires = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(
            tzinfo=timezone.utc)
    except ValueError:
        return None
    return (expires - datetime.now(timezone.utc)).days


def _states(report: Any) -> dict[str, str]:
    return {a.code: a.state for a in getattr(report, "assessments", ())}


def look(url: str, *, baseline: Path | str, use_browser: bool = True,
         fetcher=condition_mod.fetch) -> Watch:
    """Check a live site against its recorded baseline, and update the baseline."""

    baseline = Path(baseline)
    previous: dict[str, str] | None = None
    if baseline.exists():
        try:
            stored = json.loads(baseline.read_text(encoding="utf-8"))
            previous = dict(stored.get("states") or {})
            if not previous:
                previous = None
        except (OSError, ValueError) as exc:
            return Watch(UNREADABLE, url=url,
                         reason=f"the baseline at {baseline} will not parse: {exc!r}")

    capture = None
    if use_browser and browser.available()[0]:
        capture = browser.capture(url)
    current = condition_mod.assess(url, fetcher=fetcher, capture=capture)
    if current.status == condition_mod.DEFICIENT and any(
            f.code in ("UNREACHABLE", "DOMAIN_DOES_NOT_RESOLVE") for f in current.findings):
        # Recorded, but the baseline is left alone: a site that is down has not changed its
        # criteria, it has stopped answering, and overwriting the baseline with an empty
        # report would make the recovery look like a hundred improvements.
        return Watch(GONE, url=url, reason=current.findings[0].detail,
                     certificate_days_left=certificate_days_left(url))

    states = _states(current.report)
    days = certificate_days_left(url)
    if not states:
        return Watch(UNREADABLE, url=url,
                     reason=f"the site was reached and produced no report: {current.reason}",
                     certificate_days_left=days)

    baseline.parent.mkdir(parents=True, exist_ok=True)
    baseline.write_text(json.dumps({"url": url, "at": _now(), "states": states}, indent=1),
                        encoding="utf-8")
    if previous is None:
        return Watch(NOT_WATCHED, url=url, certificate_days_left=days)

    changes = []
    for code, state in states.items():
        was = previous.get(code)
        if was is not None and was != state:
            detail = next((a.detail for a in current.report.assessments if a.code == code), "")
            changes.append(Change(code, was, state, detail))
    changes.sort(key=lambda change: (not change.worse, change.code))
    if any(change.worse for change in changes):
        status = REGRESSED
    elif changes:
        status = IMPROVED
    else:
        status = INTACT
    return Watch(status, url=url, changes=tuple(changes), certificate_days_left=days)


def main(argv: list[str] | None = None) -> int:
    """`python -m prospector.watch --url https://... --baseline data/watch/shop.json`.

    Exit codes are the point: 0 when nothing needs a person, 1 when something does. That
    is what makes it usable from cron without anybody writing a wrapper that decides what
    counts as bad news.
    """

    import argparse
    import sys

    parser = argparse.ArgumentParser(prog="prospector.watch")
    parser.add_argument("--url", required=True, help="the live site to check")
    parser.add_argument("--baseline", required=True,
                        help="where this site's last report is kept, one file per site")
    parser.add_argument("--no-browser", dest="browser", action="store_false",
                        help="skip the rendered checks even where Playwright is installed")
    args = parser.parse_args(argv)

    result = look(args.url, baseline=args.baseline, use_browser=args.browser)
    print(result.describe())
    return 1 if result.needs_attention else 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
