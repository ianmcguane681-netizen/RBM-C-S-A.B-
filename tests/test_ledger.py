"""An unread fact is not a changed fact, and a monitor must not forget what it knew.

This is the recurring defect in its most consequential form yet. A rate-limited node and a
contract whose owner was renounced both leave the field empty. Reporting the first as the
second announces a change nobody made; reporting the second as the first hides one that
happened.

And the subtler half: if an unreadable observation overwrote the baseline, the next run
would find no history, report FIRST_SEEN, and look exactly like a monitor that is working.
A watcher that loses its memory whenever a request times out is worse than none.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from lib.ledger import (
    ABSENT,
    CHANGED,
    FIRST_SEEN,
    UNCHANGED,
    UNREADABLE,
    Change,
    Ledger,
    Observation,
    summarise,
)

SUBJECT = "ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"


def seen(fact, value, *, at="2026-08-02T12:00:00Z", readable=True):
    return Observation(SUBJECT, fact, value, at, source="test", readable=readable)


def ledger(tmp_path, *baseline):
    book = Ledger(tmp_path / "ledger.json")
    if baseline:
        book.record(baseline)
        book.save()
    return Ledger(tmp_path / "ledger.json")


class TestUnreadableIsNotChanged:
    def test_a_failed_read_reports_unreadable_not_absent(self, tmp_path):
        book = ledger(tmp_path, seen("owner", "0xabc"))

        changes = book.compare([seen("owner", "rate limited", readable=False)])

        assert changes[0].status == UNREADABLE

    def test_a_successful_read_of_nothing_is_absent(self, tmp_path):
        """The read worked and the fact is gone. That IS a change, and a different one."""

        book = ledger(tmp_path, seen("owner", "0xabc"))

        changes = book.compare([seen("owner", "")])

        assert changes[0].status == ABSENT

    def test_unreadable_says_the_previous_value_is_not_contradicted(self, tmp_path):
        book = ledger(tmp_path, seen("owner", "0xabc"))

        described = book.compare([seen("owner", "timeout", readable=False)])[0].describe()

        assert "NOT contradicted" in described

    def test_absent_says_the_read_succeeded(self, tmp_path):
        book = ledger(tmp_path, seen("owner", "0xabc"))

        described = book.compare([seen("owner", "")])[0].describe()

        assert "different from not having been read" in described


class TestTheLedgerDoesNotForget:
    def test_an_unreadable_observation_never_overwrites_a_baseline(self, tmp_path):
        """The failure that would look like a working monitor."""

        book = ledger(tmp_path, seen("owner", "0xabc"))

        book.record([seen("owner", "rate limited", readable=False)])
        book.save()

        assert Ledger(tmp_path / "ledger.json").get(SUBJECT, "owner").value == "0xabc"

    def test_the_baseline_survives_a_failed_run_and_still_detects_the_next_change(self, tmp_path):
        book = ledger(tmp_path, seen("owner", "0xabc"))

        book.record([seen("owner", "timeout", readable=False)])
        book.save()

        after = Ledger(tmp_path / "ledger.json")
        assert after.compare([seen("owner", "0xdef")])[0].status == CHANGED

    def test_an_unreadable_first_observation_is_stored_so_the_attempt_is_recorded(self, tmp_path):
        book = Ledger(tmp_path / "ledger.json")

        book.record([seen("owner", "timeout", readable=False)])
        book.save()

        assert len(Ledger(tmp_path / "ledger.json")) == 1

    def test_a_real_reading_after_an_unreadable_baseline_is_first_seen_not_changed(self, tmp_path):
        """Comparing against a failure would report a change from a value never observed."""

        book = ledger(tmp_path, seen("owner", "timeout", readable=False))

        assert book.compare([seen("owner", "0xabc")])[0].status == FIRST_SEEN

    def test_the_ledger_round_trips_through_a_file(self, tmp_path):
        book = ledger(tmp_path, seen("owner", "0xabc"), seen("paused", "false"))

        assert len(book) == 2
        assert book.get(SUBJECT, "paused").value == "false"


class TestChangeDetection:
    def test_a_first_observation_is_not_a_finding(self, tmp_path):
        book = Ledger(tmp_path / "ledger.json")

        assert book.compare([seen("owner", "0xabc")])[0].status == FIRST_SEEN

    def test_an_identical_reading_is_unchanged(self, tmp_path):
        book = ledger(tmp_path, seen("owner", "0xabc"))

        assert book.compare([seen("owner", "0xabc")])[0].status == UNCHANGED

    def test_a_different_reading_is_changed_and_carries_both_values(self, tmp_path):
        book = ledger(tmp_path, seen("owner", "0xabc"))

        change = book.compare([seen("owner", "0xdef")])[0]

        assert change.status == CHANGED
        assert change.before == "0xabc" and change.after == "0xdef"

    def test_comparing_does_not_write(self, tmp_path):
        book = ledger(tmp_path, seen("owner", "0xabc"))

        book.compare([seen("owner", "0xdef")])

        assert book.get(SUBJECT, "owner").value == "0xabc"


class TestMaterialityIsSeparated:
    def test_an_implementation_swap_is_material(self, tmp_path):
        """The one that voids every prior review of an upgradeable contract."""

        book = ledger(tmp_path, seen("implementation", "0x4350"))

        assert book.compare([seen("implementation", "0xbeef")])[0].is_material is True

    def test_an_ordinary_figure_moving_is_not_material(self, tmp_path):
        book = ledger(tmp_path, seen("totalSupply", "1000"))

        assert book.compare([seen("totalSupply", "2000")])[0].is_material is False

    def test_an_unreadable_material_fact_is_not_reported_as_material(self, tmp_path):
        """Materiality attaches to a change, and a failed read is not one."""

        book = ledger(tmp_path, seen("implementation", "0x4350"))

        assert book.compare([seen("implementation", "x", readable=False)])[0].is_material is False

    def test_material_changes_lead_the_summary(self, tmp_path):
        book = ledger(tmp_path, seen("implementation", "0x4350"), seen("totalSupply", "1"))

        text = summarise(book.compare([seen("implementation", "0xbeef"), seen("totalSupply", "2")]))

        assert text.index("MATERIAL CHANGES") < text.index("Other changes")
        assert "may no longer hold" in text


class TestTheSummaryDoesNotOverclaim:
    def test_no_change_says_what_it_did_not_cover(self, tmp_path):
        book = ledger(tmp_path, seen("owner", "0xabc"))

        text = summarise(book.compare([seen("owner", "0xabc")]))

        assert "says nothing about facts not in the ledger" in text

    def test_unreadable_facts_are_listed_separately_from_no_change(self, tmp_path):
        book = ledger(tmp_path, seen("owner", "0xabc"))

        text = summarise(book.compare([seen("owner", "x", readable=False)]))

        assert "Could not be read this run" in text
        assert "No change across" not in text
