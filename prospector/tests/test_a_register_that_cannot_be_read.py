"""A register that has never been written and one that will not parse are different things.

Both are "no dates for this business" if you squint, and squinting here re-approaches an
entire county. The first run of a fresh install must proceed; a corrupted file must stop
the businesses it covers. So the loader distinguishes the two, and a failed WRITE is
reported to the caller rather than swallowed, because an unrecorded preparation is one that
happens again next week.
"""
from __future__ import annotations

from prospector.seen import Register
from prospector.states import NEW, SEEN_BEFORE, UNCHECKED


def test_a_register_that_does_not_exist_yet_reports_new(tmp_path):
    assert Register(tmp_path / "prepared.json").check("node/1").status == NEW


def test_a_register_that_will_not_parse_never_reports_new(tmp_path):
    path = tmp_path / "prepared.json"
    path.write_text("{ this is not json", encoding="utf-8")
    sighting = Register(path).check("node/1")
    assert sighting.status == UNCHECKED
    assert "It is not therefore new" in sighting.describe()


def test_a_register_holding_a_list_instead_of_a_map_is_unreadable_not_empty(tmp_path):
    """A shape change is a fault. Reading it as 'nobody has been prepared' is the defect."""

    path = tmp_path / "prepared.json"
    path.write_text('["node/1"]', encoding="utf-8")
    assert Register(path).check("node/1").status == UNCHECKED


def test_recording_a_preparation_makes_it_seen(tmp_path):
    register = Register(tmp_path / "prepared.json")
    assert register.record("node/1", at="2026-08-25T00:00:00+00:00")
    sighting = register.check("node/1")
    assert sighting.status == SEEN_BEFORE
    assert sighting.dates == ("2026-08-25T00:00:00+00:00",)


def test_a_write_that_fails_says_so_rather_than_returning_quietly(tmp_path):
    path = tmp_path / "prepared.json"
    path.write_text("{ broken", encoding="utf-8")
    assert Register(path).record("node/1") is False
