"""A business as this system is allowed to know it: facts with a source attached.

Every field is a `Fact`, and a `Fact` carries where it came from. That is not ceremony. The
deliverable is a web page carrying a real business's name, address and opening hours, sent
to that business — and the first question a sceptical recipient asks is "where did you get
that". A field that cannot answer must not reach the page.

It is also the guard against the failure this design most wants to avoid. A model asked to
"write the About section" will produce plausible sentences containing invented facts — a
founding year, a family history, a speciality. Those sentences are indistinguishable from
retrieved ones once they are on the page. So retrieved facts live here, carry provenance,
and are the only thing the generator is permitted to print; everything else is a marked
gap. The parent repository states the same rule for its boards: agent output is analysis or
a proposal, and is never evidence.

`ABSENT` is a real value and is not `None`-with-a-shrug. It means the source was read and
did not carry this field, which is different from the field never having been looked for.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

#: The source was read and does not carry this field. Distinct from never having looked.
ABSENT = "ABSENT"


@dataclass(frozen=True, slots=True)
class Fact:
    """One retrieved value and where it came from."""

    value: str
    source: str
    retrieved_at: str

    def __post_init__(self) -> None:
        if not self.source:
            # A fact without a source is exactly the thing this type exists to prevent
            # from existing, so it cannot be constructed rather than being caught later.
            raise ValueError("a Fact must name its source")


@dataclass(frozen=True, slots=True)
class Business:
    """What is known about one business, and nothing else.

    `identity` is the stable key used by the seen register and by the dossier directory
    name. It comes from the source (for OpenStreetMap, `node/123456`), never from the name,
    because two hairdressers in one county share a name more often than anyone expects and
    a renamed shop is still the same shop.
    """

    identity: str
    name: Fact
    kind: Fact
    #: Named separately from `fields` because a decision hangs on it, and burying the value
    #: a whole cascade turns on inside a dictionary is how it gets defaulted by accident.
    website: Fact | str = ABSENT
    fields: Mapping[str, Fact | str] = field(default_factory=dict)
    #: Everything the source said, kept verbatim so a person can check the reading. Never
    #: printed on a page.
    raw: Mapping[str, Any] = field(default_factory=dict)

    def get(self, key: str) -> Fact | str:
        """The fact under `key`, or `ABSENT`. Never `None`, and never an empty string.

        Callers do `if isinstance(v, Fact)`. An empty string returned here would be falsy
        in exactly the same way as a missing field and the distinction would be lost at the
        first `if`, which is the defect this package is organised around.
        """

        if key == "website":
            return self.website
        value = self.fields.get(key, ABSENT)
        return value if value else ABSENT

    def name_in(self, language: str) -> Fact:
        """`name:<language>` if OpenStreetMap carries one, otherwise the default name.

        Never a translation. A business's name is its name, and rendering `Rua da
        Boavista` as `Boavista Street` would be inventing an address; but where the map
        itself carries `name:en`, that is a fact with a source like any other and using it
        on an English page is reading the source rather than paraphrasing it.
        """

        tags = (self.raw or {}).get("tags") or {}
        localised = str(tags.get(f"name:{language}", "")).strip()
        if localised:
            return Fact(value=localised, source=self.name.source,
                        retrieved_at=self.name.retrieved_at)
        return self.name

    def known(self) -> dict[str, Fact]:
        """The subset that is actually known, for the generator to print."""

        out: dict[str, Fact] = {"name": self.name, "kind": self.kind}
        for key, value in self.fields.items():
            if isinstance(value, Fact):
                out[key] = value
        return out
