"""One version number for every `--json` output in the repository.

The commands here grew a machine-readable form so a front end can render what is running
without parsing prose or re-implementing the gates. That makes their field names a
promise, and a promise nobody numbered is one that gets broken quietly: a reader written
against `unsettled_exposure` and handed a payload that no longer carries it has no way to
say which of the two is wrong.

So every top-level payload carries `schema_version`, and it lives here rather than as a
literal in each command, because four copies of `"1.0"` drift into four different answers
about the same contract.

**Bump the major when a reader that worked would now break** — a field removed or renamed,
a value that meant one thing meaning another. Adding a field is a minor bump: a reader
ignoring it is still correct.

**What the version does not buy.** It says the shape is stable, not that the numbers are
present. Every payload keeps the third states the rest of this repository is built on:
`NOT_CONFIGURED`, `UNREADABLE` and a real zero are different values, and a monetary field
that does not exist is `null` beside a status that says why. A UI that coerces those nulls
to zero has reintroduced the defect at the last possible moment, after every module below
it took care to avoid it.
"""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

SCHEMA_VERSION = "1.0"


def serialise(value: Any) -> Any:
    """Anything a lane hangs off a harvest, in JSON, without dropping what it cannot type.

    The lane types are supplied by their callers and `lib/reaper.py` is deliberately
    ignorant of them, so this walks whatever it is given: a `to_dict` if the type has one,
    a dataclass's fields if it does not, then the containers.

    **The last branch stringifies rather than returning null**, which is the whole reason
    this is a named function with a docstring. An object with no `to_dict` and no
    dataclass fields returning `None` would vanish from a UI rendering an otherwise
    complete READY instruction — an absence produced by the serialiser and indistinguishable
    from an absence in the data. That is this repository's recurring defect wearing a
    different hat, and a visible `"<Foo object at 0x...>"` in the payload is a bug report
    where a null is a silent wrong answer.
    """

    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if is_dataclass(value) and not isinstance(value, type):
        return {key: serialise(item) for key, item in asdict(value).items()}
    if isinstance(value, (tuple, list)):
        return [serialise(item) for item in value]
    if isinstance(value, dict):
        return {str(key): serialise(item) for key, item in value.items()}
    return str(value)
