"""What the business sent back, and why it outranks the map.

The sample is deliberately full of labelled gaps: no copy, no prices, no photographs of
their own, hours printed in the syntax a volunteer typed them in. Those gaps are the part
that gets a reply — "that's not our hours any more", "here are some actual photos of the
shop", "we do upholstery as well now" — and this module is what turns that reply into
something the page may carry.

**Owner-supplied facts outrank map facts, and the reason is not politeness.** The map says
what a passer-by recorded, sometimes years ago. The owner says what is true. Where the two
disagree the owner wins, and `EVIDENCE.md` records both, because the moment the page says
something a customer relies on, "where did this come from" has to have an answer that is
not "OpenStreetMap, probably 2019".

**Their copy is evidence; generated copy is still refused.** This is the line that does not
move. A sentence about the business written by the business is a fact with a source. A
sentence about the business written by anything else is invention, however good it sounds,
and `verify.py` goes on refusing it. What changes when they reply is not the rule — it is
that the evidence now exists.

**Photographs they send carry no licence question.** They own them, they handed them over,
and the page says they came from the business rather than labelling them as stock. That is
the whole reason the sample ships without their photos: the first reply is where the real
ones arrive.

## The file

One JSON file per dossier, `OWNER-SUPPLIED.json`, written as an empty template when the
dossier is prepared and filled in by a person from the reply. It is a person's job because
somebody has to read an email and decide what was actually said, and that is not a
transcription task.

    NOTHING_SUPPLIED     the template is untouched, or there is no file. The sample stands
    SUPPLIED             facts arrived, each carrying who said them and how
    HANDOVER_UNREADABLE  the file exists and will not parse. NOT nothing supplied
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from prospector.business import Business, Fact
from prospector.states import HANDOVER_UNREADABLE, NOTHING_SUPPLIED, SUPPLIED

FILENAME = "OWNER-SUPPLIED.json"

#: Fields a business can correct or add. Deliberately the same keys the map uses, so a
#: supplied value replaces a mapped one rather than sitting beside it under a new name.
FIELDS = ("phone", "email", "street", "housenumber", "city", "postcode", "opening_hours",
          "website")

#: Free text they wrote about themselves. Rendered on the page as theirs, never edited into
#: something better, because "improved" copy is copy they did not write.
COPY_KEYS = ("about", "services")

TEMPLATE = {
    "_read_me": [
        "Fill this in from what the business actually said, in their words. Anything you "
        "put here is printed on their page as fact, with them as the source.",
        "Leave a field out if they did not mention it. An empty string is not an answer.",
        "'from' must name the person who said it and how — this is what EVIDENCE.md "
        "cites when somebody asks where a detail came from.",
    ],
    "from": {"person": "", "role": "", "medium": "", "on": ""},
    "fields": {},
    "copy": {},
    "photos": [],
}


@dataclass(frozen=True, slots=True)
class Handover:
    """What arrived from the business, and who said it."""

    status: str
    person: str = ""
    medium: str = ""
    on: str = ""
    fields: Mapping[str, str] = field(default_factory=dict)
    copy: Mapping[str, str] = field(default_factory=dict)
    photos: tuple[str, ...] = ()
    reason: str = ""

    @property
    def source(self) -> str:
        """The provenance string every supplied fact carries."""

        who = self.person or "the business"
        via = f" via {self.medium}" if self.medium else ""
        when = f" on {self.on}" if self.on else ""
        return f"owner:{who}{via}{when}"

    def describe(self) -> str:
        if self.status == SUPPLIED:
            return (f"SUPPLIED  {len(self.fields)} corrected field(s), "
                    f"{len(self.copy)} piece(s) of copy, {len(self.photos)} photograph(s)"
                    f"\n  from {self.source}")
        if self.status == HANDOVER_UNREADABLE:
            return (f"HANDOVER_UNREADABLE  {self.reason}\n"
                    f"  The business may well have replied. Nothing was read, so nothing "
                    f"was used — which is not the same as them not answering.")
        return ("NOTHING_SUPPLIED  the template is untouched, so the sample stands as it "
                "is, gaps and all.")


def template_for(folder: Path) -> Path:
    """Write the empty template into a dossier and return its path."""

    path = Path(folder) / FILENAME
    if not path.exists():
        path.write_text(json.dumps(TEMPLATE, indent=1), encoding="utf-8")
    return path


def read(folder: Path) -> Handover:
    """Read one dossier's handover file."""

    path = Path(folder) / FILENAME
    if not path.exists():
        return Handover(NOTHING_SUPPLIED)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return Handover(HANDOVER_UNREADABLE, reason=f"{path}: {exc!r}")
    if not isinstance(data, dict):
        return Handover(HANDOVER_UNREADABLE, reason=f"{path} is not an object")

    fields = {k: str(v).strip() for k, v in (data.get("fields") or {}).items()
              if k in FIELDS and str(v).strip()}
    copy = {k: str(v).strip() for k, v in (data.get("copy") or {}).items()
            if k in COPY_KEYS and str(v).strip()}
    photos = tuple(str(p).strip() for p in (data.get("photos") or []) if str(p).strip())
    if not (fields or copy or photos):
        return Handover(NOTHING_SUPPLIED)

    who = data.get("from") or {}
    person = str(who.get("person", "")).strip()
    medium = str(who.get("medium", "")).strip()
    if not person or not medium:
        # Facts with nobody behind them are the thing this package refuses everywhere else.
        # A page cannot cite "somebody said so" when a customer asks about opening hours.
        return Handover(HANDOVER_UNREADABLE,
                        reason=(f"{path} carries content but no source: 'from.person' and "
                                f"'from.medium' must both say who told you and how. "
                                f"Anything here goes on their page as fact."))
    return Handover(SUPPLIED, person=person, medium=medium,
                    on=str(who.get("on", "")).strip(),
                    fields=fields, copy=copy, photos=photos)


def merge(business: Business, handover: Handover) -> Business:
    """The business as the owner corrected it. Map facts survive where they said nothing.

    Nothing is deleted: a field the owner did not mention keeps its mapped value and its
    mapped provenance, so the page does not lose the address because the reply was about
    the hours.
    """

    if handover.status != SUPPLIED:
        return business
    at = handover.on or ""
    fields = dict(business.fields)
    website = business.website
    for key, value in handover.fields.items():
        fact = Fact(value=value, source=handover.source, retrieved_at=at or "supplied")
        if key == "website":
            website = fact
        else:
            fields[key] = fact
    return Business(identity=business.identity, name=business.name, kind=business.kind,
                    website=website, fields=fields, raw=business.raw)
