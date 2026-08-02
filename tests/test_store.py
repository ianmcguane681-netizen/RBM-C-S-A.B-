"""A store that has been written and lost must not read as a store that is new.

This is the recurring defect aimed at the two components that exist only to remember. The
container is reclaimed, the gitignored data goes with it, and the next run finds nothing.
`Ledger` reports `FIRST_SEEN` for every fact; `SeenRegister` answers `NEW` to every
candidate. Both look exactly like a working component on a fresh watchlist.

The receipt is what tells the cases apart, and it can be committed because it carries only
counts and dates — never a subject. Naming the watched tokens, filers or markets is
precisely why the data itself is gitignored in a public repository.
"""
from __future__ import annotations

import json

import pytest

from lib.ledger import Ledger, Observation
from lib.seen import UNCHECKED, SeenRegister
from lib.store import FRESH, INTACT, LOST, UNREADABLE, Receipt, inspect


def observation(fact="owner", value="0xabc"):
    return Observation("subject", fact, value, "2026-08-02T12:00:00Z", "test")


class TestTheReceiptCarriesNoSubjects:
    def test_a_receipt_holds_counts_and_dates_only(self, tmp_path):
        """It is committed to a public repository; the data it vouches for is not."""

        path = tmp_path / "r.json"
        Receipt("ledger.json").written("2026-08-02T12:00:00Z", 26).save(path)

        body = path.read_text(encoding="utf-8")

        assert "26" in body
        for leaked in ("0x", "USDC", "ethereum", "MOD", "Betfair"):
            assert leaked not in body

    def test_writes_accumulate_and_the_first_date_is_kept(self):
        receipt = Receipt("x").written("2026-08-01T00:00:00Z", 5).written("2026-08-02T00:00:00Z", 7)

        assert receipt.writes == 2
        assert receipt.first_write == "2026-08-01T00:00:00Z"
        assert receipt.rows_at_last_write == 7


class TestLostIsNotFresh:
    def test_no_receipt_and_no_data_is_a_genuine_first_run(self, tmp_path):
        status = inspect("x", receipt_path=tmp_path / "r.json", rows_found=0)

        assert status.state == FRESH

    def test_a_receipt_with_writes_and_no_data_is_lost(self, tmp_path):
        path = tmp_path / "r.json"
        Receipt("x").written("2026-08-02T12:00:00Z", 26).save(path)

        assert inspect("x", receipt_path=path, rows_found=0).state == LOST

    def test_lost_says_it_is_not_a_first_run(self, tmp_path):
        path = tmp_path / "r.json"
        Receipt("x").written("2026-08-02T12:00:00Z", 26).save(path)

        described = inspect("x", receipt_path=path, rows_found=0).describe()

        assert "NOT a first run" in described
        assert "26 row(s)" in described

    def test_lost_memory_is_not_trustworthy_and_fresh_is(self, tmp_path):
        path = tmp_path / "r.json"
        Receipt("x").written("2026-08-02T12:00:00Z", 26).save(path)

        assert inspect("x", receipt_path=path, rows_found=0).memory_is_trustworthy is False
        assert inspect("x", receipt_path=tmp_path / "none.json",
                       rows_found=0).memory_is_trustworthy is True

    def test_unreadable_data_is_not_lost_and_not_empty(self, tmp_path):
        status = inspect("x", receipt_path=tmp_path / "r.json", rows_found=None, reason="bad")

        assert status.state == UNREADABLE
        assert "NOT established as empty" in status.describe()

    def test_a_backend_mismatch_is_not_silently_intact(self, tmp_path):
        """A receipt written by one backend and read by another is a person's problem."""

        path = tmp_path / "r.json"
        Receipt("x", backend="postgres").written("2026-08-02T12:00:00Z", 26).save(path)

        status = inspect("x", receipt_path=path, rows_found=26, backend="json")

        assert status.state == UNREADABLE
        assert "postgres" in status.reason


class TestTheLedgerSurvivesLosingItsData:
    def test_a_ledger_written_then_deleted_reports_lost(self, tmp_path):
        """The exact container-reclaimed case, end to end."""

        path = tmp_path / "ledger.json"
        book = Ledger(path)
        book.record([observation()])
        book.save("2026-08-02T12:00:00Z")

        path.unlink()

        assert Ledger(path).status.state == LOST

    def test_a_ledger_never_written_reports_fresh(self, tmp_path):
        assert Ledger(tmp_path / "ledger.json").status.state == FRESH

    def test_an_intact_ledger_reports_intact_with_its_row_count(self, tmp_path):
        path = tmp_path / "ledger.json"
        book = Ledger(path)
        book.record([observation("owner"), observation("paused", "false")])
        book.save("2026-08-02T12:00:00Z")

        assert Ledger(path).status.state == INTACT
        assert Ledger(path).status.rows_found == 2

    def test_a_corrupt_ledger_is_unreadable_rather_than_empty(self, tmp_path):
        path = tmp_path / "ledger.json"
        path.write_text("{not json", encoding="utf-8")

        assert Ledger(path).status.state == UNREADABLE


class TestTheSeenRegisterRefusesToCallALostBacklogNew:
    def test_a_register_written_then_deleted_answers_unchecked(self, tmp_path):
        """Answering NEW would re-surface the entire backlog as novel."""

        path = tmp_path / "seen.json"
        register = SeenRegister(path)
        register.record("some-arb", "2026-08-02T12:00:00Z")
        register.save("2026-08-02T12:00:00Z")

        path.unlink()

        assert SeenRegister.load(path).check("some-arb").status == UNCHECKED

    def test_the_reason_explains_the_store_was_lost(self, tmp_path):
        path = tmp_path / "seen.json"
        register = SeenRegister(path)
        register.record("some-arb", "2026-08-02T12:00:00Z")
        register.save("2026-08-02T12:00:00Z")
        path.unlink()

        assert "LOST" in SeenRegister.load(path).check("some-arb").reason

    def test_a_register_never_written_still_answers_new(self, tmp_path):
        """Losing the distinction in the other direction would make it useless."""

        from lib.seen import NEW

        assert SeenRegister.load(tmp_path / "seen.json").check("x").status == NEW

    def test_an_intact_register_still_reports_sightings(self, tmp_path):
        from lib.seen import SEEN_BEFORE

        path = tmp_path / "seen.json"
        register = SeenRegister(path)
        register.record("id", "2026-08-02T12:00:00Z")
        register.save("2026-08-02T12:00:00Z")

        assert SeenRegister.load(path).check("id").status == SEEN_BEFORE
