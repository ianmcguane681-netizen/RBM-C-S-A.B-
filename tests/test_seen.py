"""A register that cannot be read must not answer NEW, and a price tick is not a new arb.

Two failure modes, both in the direction that costs money.

If identity included the odds, every tick would be a fresh sighting and the register would
dedupe nothing while appearing to work — the worst kind of broken, because it produces
output.

If an unreadable register answered NEW, a scheduled scan would re-surface its entire
backlog on the day the file went missing: the flattering reading, arriving in bulk, at the
moment there is least reason to trust it.
"""
from __future__ import annotations

import pytest

from lib.seen import (
    ACTED_ON,
    NEW,
    SEEN_BEFORE,
    UNCHECKED,
    SeenRegister,
    arb_identity,
)

WHEN = "2026-08-02T12:00:00Z"
LATER = "2026-08-02T18:00:00Z"


class TestIdentityExcludesThePrice:
    def test_the_same_legs_at_different_odds_are_one_opportunity(self):
        first = arb_identity("Match Odds", [("Betfair", "Team A"), ("Book", "Team B")])
        second = arb_identity("Match Odds", [("Betfair", "Team A"), ("Book", "Team B")])

        assert first == second

    def test_the_legs_read_in_either_order_are_one_opportunity(self):
        first = arb_identity("Match Odds", [("Betfair", "Team A"), ("Book", "Team B")])
        second = arb_identity("Match Odds", [("Book", "Team B"), ("Betfair", "Team A")])

        assert first == second

    def test_a_different_selection_is_a_different_opportunity(self):
        first = arb_identity("Match Odds", [("Betfair", "Team A"), ("Book", "Team B")])
        second = arb_identity("Match Odds", [("Betfair", "Draw"), ("Book", "Team B")])

        assert first != second

    def test_the_same_legs_in_a_different_market_are_different(self):
        first = arb_identity("Match Odds", [("Betfair", "Team A"), ("Book", "Team B")])
        second = arb_identity("Over 2.5", [("Betfair", "Team A"), ("Book", "Team B")])

        assert first != second


class TestAnUnreadableRegisterNeverSaysNew:
    def test_a_corrupt_file_reports_unchecked(self, tmp_path):
        path = tmp_path / "seen.json"
        path.write_text("{not json", encoding="utf-8")

        assert SeenRegister.load(path).check("id").status == UNCHECKED

    def test_unchecked_says_the_candidate_is_not_established_as_new(self, tmp_path):
        path = tmp_path / "seen.json"
        path.write_text("[[[", encoding="utf-8")

        described = SeenRegister.load(path).check("id").describe()

        assert "NOT established as new" in described

    def test_an_absent_file_is_genuinely_empty_and_answers_new(self, tmp_path):
        """A register that has never been written is different from one that broke."""

        assert SeenRegister.load(tmp_path / "seen.json").check("id").status == NEW

    def test_writing_through_an_unreadable_register_is_refused(self, tmp_path):
        path = tmp_path / "seen.json"
        path.write_text("nonsense", encoding="utf-8")
        register = SeenRegister.load(path)

        with pytest.raises(RuntimeError, match="discard every prior sighting"):
            register.record("id", WHEN)


class TestSightingsAccumulate:
    def test_a_first_sighting_is_new(self, tmp_path):
        assert SeenRegister(tmp_path / "s.json").check("id").status == NEW

    def test_a_second_sighting_keeps_the_first_date_and_counts(self, tmp_path):
        register = SeenRegister(tmp_path / "s.json")
        register.record("id", WHEN)
        register.record("id", LATER)

        verdict = register.check("id")

        assert verdict.status == SEEN_BEFORE
        assert verdict.sighting.first_seen == WHEN
        assert verdict.sighting.last_seen == LATER
        assert verdict.sighting.times_seen == 2

    def test_checking_does_not_record(self, tmp_path):
        register = SeenRegister(tmp_path / "s.json")

        register.check("id")

        assert len(register) == 0

    def test_the_register_round_trips_through_a_file(self, tmp_path):
        register = SeenRegister(tmp_path / "s.json")
        register.record("id", WHEN)
        register.save()

        assert SeenRegister.load(tmp_path / "s.json").check("id").status == SEEN_BEFORE

    def test_seen_before_says_it_is_still_real(self, tmp_path):
        register = SeenRegister(tmp_path / "s.json")
        register.record("id", WHEN)

        assert "Still real, and not news" in register.check("id").describe()


class TestActingOutranksSeeing:
    def test_an_acted_on_sighting_reports_acted_on(self, tmp_path):
        register = SeenRegister(tmp_path / "s.json")
        register.record("id", WHEN)
        register.record_action("id", LATER)

        assert register.check("id").status == ACTED_ON

    def test_a_later_sighting_does_not_erase_the_action(self, tmp_path):
        register = SeenRegister(tmp_path / "s.json")
        register.record_action("id", WHEN)
        register.record("id", LATER)

        assert register.check("id").status == ACTED_ON

    def test_acted_on_explains_it_is_reported_because_it_persists(self, tmp_path):
        register = SeenRegister(tmp_path / "s.json")
        register.record_action("id", WHEN)

        assert "not because it is new" in register.check("id").describe()
