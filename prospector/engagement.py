"""What stage a business is at, and the one gate that cannot be automated: publishing.

Everything up to now produces a sample nobody asked for, sitting on a disk, labelled as
what it is. This file is about what happens when somebody says yes — and the reason it is
its own module with its own refusals is that the yes changes what the artefact IS.

**A sample carries a banner saying it is unofficial and unaffiliated. A published site does
not.** Removing that banner is the moment a page stops being speculative work and starts
being a business's public face, published under their name, findable by their customers.
Getting that wrong is not a bug that produces a wrong number; it is a stranger's business
misrepresented on the open internet.

So the banner comes off exactly once, in exchange for exactly one thing: an authorisation
that names a person at that business, what they authorised, when, and how it was given.

    SAMPLE       prepared, and nobody has said anything. The default and the assumption
    DECLINED     they said no. Recorded so nobody prepares them again next month
    INTERESTED   they replied and want changes. Revisions arrive as evidence, see handover
    AUTHORISED   a named person authorised publishing. Not a mode, a record
    LIVE         published, at a URL, under that authorisation
    LAPSED       the engagement ended. The site comes down or is handed over
    UNKNOWN      the ledger could not be read. NEVER SAMPLE

`UNKNOWN` is separate for the usual reason pointed at the most expensive case: if an
unreadable ledger answered `SAMPLE`, a business that had already engaged would be prepared
again, and a business that had already DECLINED would be approached again.

## The authorisation refuses to be given by an automation

The parent repository refuses the prefixes `agent:`, `ai:`, `model:`, `automation:`,
`bot:` and `system:` on every judgement that belongs to a named human — ratifying a board
decision, declaring settlement equivalence, re-arming a breaker. Publishing a website under
somebody else's business name is that kind of judgement, and this file refuses the same
prefixes for the same reason. There is no `force=True`.

It also refuses an authorisation with no medium. "They said yes" is not a record; "email
from cathy@shop.ie on 2026-08-27" is, and it is what you will want the day somebody asks
who agreed to this.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

SAMPLE = "SAMPLE"
DECLINED = "DECLINED"
INTERESTED = "INTERESTED"
AUTHORISED = "AUTHORISED"
LIVE = "LIVE"
LAPSED = "LAPSED"
UNKNOWN = "UNKNOWN"

#: The order a business moves through. Not enforced as a straight line — plenty go from
#: INTERESTED back to DECLINED, and a LAPSED one can engage again — but a jump from SAMPLE
#: straight to LIVE means an authorisation was never recorded, and that is refused.
STAGES = (SAMPLE, INTERESTED, AUTHORISED, LIVE, LAPSED, DECLINED, UNKNOWN)

#: Carried over verbatim from the parent repository. A page published under a stranger's
#: business name is a named person's decision.
AUTOMATION_PREFIXES = ("agent:", "ai:", "model:", "automation:", "bot:", "system:")

#: What an authorisation can cover. Separate because they are separate decisions: agreeing
#: to a site going live is not agreeing to it being changed later without asking.
PUBLISH = "PUBLISH"
MONITOR = "MONITOR"
MAINTAIN = "MAINTAIN"
SCOPES = (PUBLISH, MONITOR, MAINTAIN)


class NotAuthorised(RuntimeError):
    """Raised where a page would be published without a record permitting it."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True, slots=True)
class Authorisation:
    """Who at the business agreed, to what, when, and how it was given."""

    business_identity: str
    person: str
    role: str
    medium: str
    granted_on: str
    scopes: tuple[str, ...] = (PUBLISH,)
    #: Where the evidence lives — a mail file, a signed quote, a message id. Not the words
    #: themselves: the point is that somebody can go and look.
    evidence_ref: str = ""
    recorded_at: str = field(default_factory=_now)

    def __post_init__(self) -> None:
        person = (self.person or "").strip()
        if not person:
            raise NotAuthorised("an authorisation must name the person who gave it")
        lowered = person.lower()
        if any(lowered.startswith(prefix) for prefix in AUTOMATION_PREFIXES):
            raise NotAuthorised(
                f"{self.person!r} names an automation. Publishing a website under a "
                f"business's name is a decision a person at that business makes, and no "
                f"flag in this package overrides that.")
        if not (self.medium or "").strip():
            raise NotAuthorised(
                "an authorisation must say how it was given — 'email from cathy@shop.ie, "
                "2026-08-27', 'signed quote', 'agreed on the phone and confirmed by "
                "text'. 'They said yes' is not a record.")
        if not (self.granted_on or "").strip():
            raise NotAuthorised("an authorisation must carry the date it was given")
        unknown = set(self.scopes) - set(SCOPES)
        if unknown:
            raise NotAuthorised(f"unknown scopes: {', '.join(sorted(unknown))}")

    def permits(self, scope: str) -> bool:
        return scope in self.scopes

    def describe(self) -> str:
        return (f"AUTHORISED by {self.person} ({self.role or 'role not stated'}) on "
                f"{self.granted_on}\n  via {self.medium}"
                + (f"\n  evidence: {self.evidence_ref}" if self.evidence_ref else "")
                + f"\n  scopes: {', '.join(self.scopes)}")


@dataclass(frozen=True, slots=True)
class Engagement:
    """One business's stage, and the record behind it."""

    identity: str
    status: str = SAMPLE
    name: str = ""
    authorisation: Authorisation | None = None
    live_url: str = ""
    #: Set when the site is being watched. Monitoring is a promise, so it is recorded
    #: rather than inferred from the fact that a URL exists.
    monitored: bool = False
    note: str = ""
    updated_at: str = field(default_factory=_now)

    @property
    def may_publish(self) -> bool:
        return bool(self.authorisation and self.authorisation.permits(PUBLISH))

    @property
    def may_monitor(self) -> bool:
        return bool(self.authorisation and self.authorisation.permits(MONITOR))

    def describe(self) -> str:
        if self.status == UNKNOWN:
            return (f"UNKNOWN  {self.identity}\n  {self.note}\n"
                    f"  The ledger could not be read, so what has been agreed with this "
                    f"business is unknown. It is not therefore a fresh prospect.")
        head = f"{self.status}  {self.name or self.identity}"
        if self.live_url:
            head += f"  {self.live_url}"
        if self.authorisation:
            head += "\n  " + self.authorisation.describe().replace("\n", "\n  ")
        if self.status == LIVE and not self.monitored:
            head += "\n  Not monitored. Nothing is checking that this stays up."
        return head


class Ledger:
    """Who has engaged, at what stage, on whose say-so. A JSON file, read before every act.

    Gitignored, like every other file here that carries subjects: it is a list of real
    businesses, what they agreed to and who agreed it.
    """

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def _load(self) -> dict | None:
        if not self.path.exists():
            # Never written is genuinely empty. Unreadable is not.
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return data if isinstance(data, dict) else None

    def get(self, identity: str) -> Engagement:
        rows = self._load()
        if rows is None:
            return Engagement(identity, UNKNOWN,
                              note=f"{self.path} exists and could not be parsed")
        row = rows.get(identity)
        if not row:
            return Engagement(identity, SAMPLE)
        authorisation = None
        if row.get("authorisation"):
            try:
                fields = dict(row["authorisation"])
                fields["scopes"] = tuple(fields.get("scopes", (PUBLISH,)))
                authorisation = Authorisation(**fields)
            except (TypeError, NotAuthorised) as exc:
                # A stored authorisation that will not reconstruct is not an authorisation.
                # Publishing on the strength of a malformed record is exactly the failure
                # the record exists to prevent.
                return Engagement(identity, UNKNOWN, name=row.get("name", ""),
                                  note=f"the stored authorisation will not load: {exc}")
        return Engagement(identity, row.get("status", SAMPLE), row.get("name", ""),
                          authorisation, row.get("live_url", ""),
                          bool(row.get("monitored", False)), row.get("note", ""),
                          row.get("updated_at", ""))

    def put(self, engagement: Engagement) -> bool:
        """Write one engagement. False when the ledger could not be written."""

        rows = self._load()
        if rows is None:
            return False
        row = {k: v for k, v in asdict(engagement).items() if k != "identity"}
        if engagement.authorisation is None:
            row["authorisation"] = None
        rows[engagement.identity] = row
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(rows, indent=1, sort_keys=True, default=str),
                                 encoding="utf-8")
        except OSError:
            return False
        return True


def gate(engagement: Engagement, scope: str = PUBLISH) -> Authorisation:
    """The authorisation permitting `scope`, or a refusal naming what is missing.

    Called by everything that would make a sample public. It raises rather than returning
    a boolean because the caller's next line writes a file to a web server, and a boolean
    somebody forgot to check is the shape of every accident this package is built around.
    """

    if engagement.status == UNKNOWN:
        raise NotAuthorised(
            f"the engagement ledger could not be read, so whether {engagement.identity} "
            f"authorised anything is unknown. Fix the ledger; do not publish past it.")
    if engagement.authorisation is None:
        raise NotAuthorised(
            f"{engagement.name or engagement.identity} has no recorded authorisation. A "
            f"sample becomes a published site only when a named person at the business "
            f"has said so, and that record is what removes the 'unofficial sample' "
            f"banner.")
    if not engagement.authorisation.permits(scope):
        raise NotAuthorised(
            f"{engagement.authorisation.person} authorised "
            f"{', '.join(engagement.authorisation.scopes)} — not {scope}. Agreeing to a "
            f"site going live is not agreeing to {scope.lower()}.")
    return engagement.authorisation


def main(argv: list[str] | None = None) -> int:
    """`python -m prospector.engagement` — read the ledger, or record a stage.

    Deliberately small. Recording that a business said yes is a thing a person does once,
    at a keyboard, having read an email; it is not a pipeline stage and giving it a
    pipeline's ergonomics would suggest otherwise.
    """

    import argparse
    import sys

    parser = argparse.ArgumentParser(prog="prospector.engagement")
    parser.add_argument("--ledger", default="data/engagements.json")
    parser.add_argument("--identity", default="", help="e.g. node/1001. Omit to list all")
    parser.add_argument("--name", default="")
    parser.add_argument("--status", choices=STAGES, default="")
    parser.add_argument("--live-url", default="")
    parser.add_argument("--monitored", action="store_true")
    parser.add_argument("--note", default="")
    group = parser.add_argument_group(
        "authorisation", "all four are required together, and none of them is optional "
        "because the record is the only thing that removes the sample banner")
    group.add_argument("--by", default="", help="the person at the business who agreed")
    group.add_argument("--role", default="", help="owner, manager, whatever they said")
    group.add_argument("--via", default="", help="'email 2026-08-27', 'signed quote'")
    group.add_argument("--on", default="", help="the date they agreed")
    group.add_argument("--scope", action="append", choices=SCOPES, default=[])
    group.add_argument("--evidence", default="", help="where the proof of it lives")
    args = parser.parse_args(argv)

    ledger = Ledger(Path(args.ledger))
    if not args.identity:
        rows = ledger._load()
        if rows is None:
            print(f"UNKNOWN  {args.ledger} exists and could not be parsed.", file=sys.stderr)
            return 1
        if not rows:
            print("No engagements recorded yet.")
            return 0
        for identity in sorted(rows):
            print(ledger.get(identity).describe())
            print()
        return 0

    current = ledger.get(args.identity)
    if not any((args.status, args.by, args.live_url, args.note, args.monitored)):
        print(current.describe())
        return 0

    authorisation = current.authorisation
    if args.by or args.via or args.on or args.scope:
        try:
            authorisation = Authorisation(
                business_identity=args.identity, person=args.by, role=args.role,
                medium=args.via, granted_on=args.on,
                scopes=tuple(args.scope or (PUBLISH,)), evidence_ref=args.evidence)
        except NotAuthorised as exc:
            print(f"REFUSED: {exc}", file=sys.stderr)
            return 2

    status = args.status or (AUTHORISED if authorisation and current.status == SAMPLE
                             else current.status)
    if status == LIVE and not (authorisation and authorisation.permits(PUBLISH)):
        print("REFUSED: a business cannot be marked LIVE without an authorisation that "
              "permits PUBLISH. Record who agreed, and how, first.", file=sys.stderr)
        return 2

    updated = Engagement(args.identity, status, args.name or current.name, authorisation,
                         args.live_url or current.live_url,
                         args.monitored or current.monitored,
                         args.note or current.note, _now())
    if not ledger.put(updated):
        print(f"NOT RECORDED: {args.ledger} could not be written. Nothing was saved, and "
              f"the next run will not know about this.", file=sys.stderr)
        return 1
    print(updated.describe())
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
