"""A run that leaves no record cannot be the evidence that anything works.

Everything a reap produced was printed once and lost. `data/orchestrator.json` kept a
last-run time and an exit code; the harvests, their reasons and the placements existed for
the length of one stdout. So "what did the arb lane find on Tuesday" had no answer, and
neither did the question the plan turns on — *prove one function produces something real
before starting a fourth*.

Two properties matter more than the schema. The journal must never take a run down with it:
a reap that placed an order and then could not write its diary has still placed the order,
and failing the run over the note is the expensive direction. And it must keep the four
kinds of nothing apart, because a COULD_NOT_LOOK read back three weeks later as
NOTHING_FOUND is the founding defect with a timestamp on it.
"""
from __future__ import annotations

import sqlite3

from lib.journal import Journal
from lib.placing import PLACED, UNRESOLVED, Placement
from lib.reaper import COULD_NOT_LOOK, NOTHING_FOUND, READY, Harvest
from lib.reaping import CONFIGURED, NOT_CONFIGURED, Assembly, Reaping


def _reaping(**kw) -> Reaping:
    return Reaping(assemblies=(Assembly("stocks", CONFIGURED),), **kw)


class TestARunSurvivesTheProcessThatRanIt:
    def test_a_recorded_run_is_readable_from_a_new_journal_object(self, tmp_path):
        path = tmp_path / "journal.sqlite3"
        Journal(path).record(_reaping(harvests=(
            Harvest(lane="stocks", status=NOTHING_FOUND, sources_asked=2,
                    sources_answered=2),)))

        reopened = Journal(path)

        assert reopened.counts()["reaper_runs"] == 1
        assert reopened.counts()["harvests"] == 1

    def test_each_run_is_a_new_row_rather_than_an_overwrite(self, tmp_path):
        """Append only. A run that went badly stays on file in the shape it went badly in."""

        path = tmp_path / "journal.sqlite3"
        journal = Journal(path)
        first = journal.record(_reaping())
        second = journal.record(_reaping())

        assert first != second
        assert journal.counts()["reaper_runs"] == 2

    def test_the_placements_of_a_run_are_recoverable_by_its_id(self, tmp_path):
        journal = Journal(tmp_path / "journal.sqlite3")
        run = journal.record(_reaping(
            harvests=(Harvest(lane="stocks", status=READY, subject="ACME"),),
            placements=(Placement("stocks", PLACED, subject="ACME", position_id="POS-1",
                                  client_order_id="abc", filled_quantity=3.0,
                                  requested_quantity=3.0),),
        ))

        placed = journal.placements_for(run)

        assert len(placed) == 1
        assert placed[0]["position_id"] == "POS-1"
        assert placed[0]["status"] == PLACED


class TestTheJournalNeverTakesARunDownWithIt:
    """Losing the note is bad. Losing the order because of the note is worse."""

    def test_an_unopenable_journal_reports_itself_rather_than_raising(self, tmp_path):
        blocked = tmp_path / "not-a-dir"
        blocked.write_text("this is a file", encoding="utf-8")

        journal = Journal(blocked / "journal.sqlite3")

        assert journal.readable is False
        assert journal.reason
        assert journal.record(_reaping()) == ""      # returns, does not raise

    def test_a_write_that_fails_is_recorded_and_swallowed(self, tmp_path, monkeypatch):
        journal = Journal(tmp_path / "journal.sqlite3")

        def broken():
            raise sqlite3.OperationalError("database is locked")

        monkeypatch.setattr(journal, "_connect", lambda: broken())

        assert journal.record(_reaping()) == ""
        assert "OperationalError" in journal.last_error

    def test_an_unreadable_journal_reports_null_counts_not_zero(self, tmp_path):
        """Nought runs recorded and a journal that will not open are different facts.

        Zero would read as "this system has never run", which is a claim about the world
        rather than about the file.
        """

        blocked = tmp_path / "not-a-dir"
        blocked.write_text("x", encoding="utf-8")

        counts = Journal(blocked / "journal.sqlite3").counts()

        assert counts == {"runs": None, "harvests": None, "executions": None}


class TestTheFourKindsOfNothingSurviveBeingWrittenDown:
    def test_a_run_that_could_not_look_is_not_stored_as_one_that_found_nothing(
        self, tmp_path
    ):
        """The founding defect, with a timestamp on it and read back three weeks later."""

        journal = Journal(tmp_path / "journal.sqlite3")
        journal.record(_reaping(harvests=(
            Harvest(lane="stocks", status=COULD_NOT_LOOK, reason="no key"),)))
        journal.record(_reaping(harvests=(
            Harvest(lane="stocks", status=NOTHING_FOUND, sources_asked=2,
                    sources_answered=2),)))

        statuses = [run["status"] for run in journal.recent_runs()]

        assert "COULD_NOT_LOOK" in statuses
        assert "LOOKED" in statuses

    def test_a_run_with_no_configured_lane_is_stored_as_not_configured(self, tmp_path):
        journal = Journal(tmp_path / "journal.sqlite3")
        journal.record(Reaping(assemblies=(Assembly("stocks", NOT_CONFIGURED),)))

        assert journal.recent_runs()[0]["status"] == NOT_CONFIGURED

    def test_an_unresolved_placement_keeps_its_unknown_fill(self, tmp_path):
        """The order MAY exist, and a stored 0.0 would read as a confirmed non-fill.

        This is the value that gets acted on: a reader treating it as "nothing went on"
        submits the same money again.
        """

        journal = Journal(tmp_path / "journal.sqlite3")
        run = journal.record(_reaping(placements=(
            Placement("stocks", UNRESOLVED, subject="ACME", position_id="POS-1",
                      client_order_id="abc", requested_quantity=3.0,
                      reason="the broker returned 502"),)))

        stored = journal.placements_for(run)[0]

        assert stored["filled_quantity"] is None
        assert stored["status"] == UNRESOLVED


class TestItIsARecordAndNotALedger:
    def test_an_empty_journal_says_so_rather_than_implying_nothing_happened(self, tmp_path):
        described = Journal(tmp_path / "journal.sqlite3").describe()

        assert "EMPTY" in described
        assert "not the same as a run that found nothing" in described

    def test_the_journal_is_not_consulted_for_what_is_at_risk(self):
        """`unsettled_exposure` must have exactly one answer, and it is the ledger's.

        A second store answering a money question is worse than no second store: the two
        eventually disagree and nothing says which is right. This pins that the journal
        exposes no such method rather than relying on nobody calling it.
        """

        assert not hasattr(Journal, "unsettled_exposure")
        assert not hasattr(Journal, "live")


def test_a_default_path_is_read_at_call_time_rather_than_bound_at_import():
    """`journal_path: Path = JOURNAL` in the signature is how the suite wrote to `data/`.

    A default argument is evaluated once, when the module is imported, so the module
    constant becomes unpatchable and every test that called `reap()` appended to the live
    operational directory — beside the real breaker state and the real outcome ledger. The
    fixture in conftest could not have caught it, because there was nothing left to patch.

    Gitignore was not the guard. The risk was a test run writing where the money lives.
    """

    import inspect

    import connectors.oddsapi
    import lib.reaping

    reap_default = inspect.signature(lib.reaping.reap).parameters["journal_path"].default
    usage_default = inspect.signature(
        connectors.oddsapi.OddsApiSource.__init__).parameters["usage_path"].default

    # A sentinel, not a Path: the real destination is resolved inside the call.
    assert not isinstance(reap_default, type(lib.reaping.JOURNAL))
    assert not isinstance(usage_default, type(connectors.oddsapi.USAGE))


def test_patching_the_module_constant_redirects_where_a_run_is_recorded(
    tmp_path, monkeypatch
):
    import lib.reaping

    elsewhere = tmp_path / "elsewhere.sqlite3"
    monkeypatch.setattr(lib.reaping, "JOURNAL", elsewhere)
    lib.reaping.reap(
        config_path=tmp_path / "absent.json", ledger_path=tmp_path / "outcomes.json",
        directory=tmp_path, kill_switch=tmp_path / "HALT",
        theses_path=tmp_path / "theses.json",
    )

    assert elsewhere.is_file()


def test_a_run_can_decline_to_be_journalled_at_all(tmp_path):
    import lib.reaping

    lib.reaping.reap(
        config_path=tmp_path / "absent.json", ledger_path=tmp_path / "outcomes.json",
        directory=tmp_path, kill_switch=tmp_path / "HALT",
        theses_path=tmp_path / "theses.json", journal_path=None,
    )

    assert not (tmp_path / "journal.sqlite3").exists()


def test_status_reports_an_unopenable_journal_apart_from_an_empty_one(
    tmp_path, monkeypatch
):
    """A system running for weeks must not read as one that has never run.

    `reap_history.status` carries the distinction, because "no run recorded" is a fact
    about this system and "the journal will not open" is a fact about a file.
    """

    import lib.reaping
    import status

    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()

    monkeypatch.setattr(lib.reaping, "JOURNAL", tmp_path / "data" / "journal.sqlite3")
    assert status.as_json()["reap_history"]["status"] == "EMPTY"

    blocked = tmp_path / "blocked"
    blocked.write_text("not a directory", encoding="utf-8")
    monkeypatch.setattr(lib.reaping, "JOURNAL", blocked / "journal.sqlite3")

    history = status.as_json()["reap_history"]

    assert history["status"] == "UNREADABLE"
    assert history["runs"] is None
    assert history["counts"]["runs"] is None
    assert history["reason"]
