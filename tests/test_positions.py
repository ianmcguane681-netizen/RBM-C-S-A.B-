"""Typing the result in is the honest interface; a breaker reading zero is not.

bet365 and Sky Bet have no settlement API, so the alternative to a person entering the
outcome is not an automatic one — it is the state this repository was in until
`lib/outcomes.py` existed, where the daily loss limit read zero forever and permitted the
fifth losing position as cheerfully as the first.

The properties under test are the ones that keep that from coming back quietly. An
unreadable ledger refuses rather than being overwritten. A lane holding settled outcomes
with no breakers to receive them is REPORTED, not skipped. And the exit codes distinguish
"nothing needs you" from "something is waiting" from "I could not read the file", because a
scheduler that cannot tell those apart will treat the third as the first.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import positions
from lib.outcomes import BROKER, OutcomeLedger

AUTHORITY = {
    "declared_by": "Ian McGuane",
    "reasoning": "two books disagree by more than the cost of taking both sides",
    "considered": ["a book restricts the account"],
    "expires_at": "2099-01-01T00:00:00Z",
    "max_exposure": 50.0,
}


def config_file(tmp_path, **lanes):
    payload = {"arb": {"enabled": True, "balance": 1000.0, "sports": ["soccer_epl"],
                       "authority": dict(AUTHORITY)}}
    payload.update(lanes)
    path = tmp_path / "reapers.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def run(tmp_path, *argv, config=None):
    return positions.main([
        *argv, "--ledger", str(tmp_path / "outcomes.json"),
        "--config", str(config or (tmp_path / "reapers.json")),
    ])


def place(tmp_path, subject="Arsenal v Chelsea", staked="499.98", lane="arb"):
    return run(tmp_path, "--placed", lane, subject, "--staked", staked)


def only_position(tmp_path):
    return OutcomeLedger(tmp_path / "outcomes.json").positions[0]


class TestRecordingAPlacement:
    def test_it_writes_a_position_and_asks_to_be_settled(self, tmp_path, capsys):
        code = place(tmp_path)

        assert code == 1
        assert "--settle POS-" in capsys.readouterr().out

    def test_the_position_is_open_with_the_stake_at_risk(self, tmp_path):
        place(tmp_path, staked="499.98")

        position = only_position(tmp_path)
        assert position.status == "OPEN"
        assert position.staked == pytest.approx(499.98)

    def test_a_stakeless_placement_is_refused(self, tmp_path, capsys):
        code = run(tmp_path, "--placed", "arb", "x", "--staked", "0")

        assert code == 2
        assert "nothing was at risk" in capsys.readouterr().out

    def test_a_placement_with_no_stake_flag_is_refused(self, tmp_path):
        assert run(tmp_path, "--placed", "arb", "x") == 2

    def test_the_source_is_recorded_so_confidence_is_not_flattened(self, tmp_path):
        run(tmp_path, "--placed", "stocks", "MODN", "--staked", "900", "--source", BROKER)

        assert only_position(tmp_path).source == BROKER

    def test_it_defaults_to_manual(self, tmp_path):
        place(tmp_path)

        assert only_position(tmp_path).source == "MANUAL"


class TestSettlingVoidingAndNotKnowing:
    def _placed(self, tmp_path):
        place(tmp_path)
        return only_position(tmp_path).position_id

    def test_settling_records_the_profit(self, tmp_path):
        identifier = self._placed(tmp_path)

        run(tmp_path, "--settle", identifier, "--returned", "541.08")

        assert only_position(tmp_path).profit == pytest.approx(41.10)

    def test_settling_without_an_amount_is_refused_rather_than_assumed_zero(self, tmp_path,
                                                                           capsys):
        """Guessing zero would record a total loss on a bet that may have won."""

        identifier = self._placed(tmp_path)

        code = run(tmp_path, "--settle", identifier)

        assert code == 2
        assert "guessing zero would record a total loss" in capsys.readouterr().out

    def test_voiding_returns_the_stake(self, tmp_path):
        identifier = self._placed(tmp_path)

        run(tmp_path, "--void", identifier, "--note", "abandoned")

        position = only_position(tmp_path)
        assert position.status == "VOID"
        assert position.returned == pytest.approx(position.staked)

    def test_an_unknown_needs_a_note(self, tmp_path, capsys):
        identifier = self._placed(tmp_path)

        code = run(tmp_path, "--unknown", identifier)

        assert code == 2
        assert "indistinguishable from neglect" in capsys.readouterr().out

    def test_an_unknown_with_a_note_is_recorded(self, tmp_path):
        identifier = self._placed(tmp_path)

        run(tmp_path, "--unknown", identifier, "--note", "bet365 restricted the account")

        assert only_position(tmp_path).status == "UNKNOWN"

    def test_resolving_says_it_has_not_reached_a_breaker_yet(self, tmp_path, capsys):
        identifier = self._placed(tmp_path)

        run(tmp_path, "--settle", identifier, "--returned", "500")

        assert "--apply" in capsys.readouterr().out

    def test_amending_a_settled_position_is_refused(self, tmp_path):
        identifier = self._placed(tmp_path)
        run(tmp_path, "--settle", identifier, "--returned", "500")

        with pytest.raises(ValueError, match="the copy that stops you"):
            run(tmp_path, "--settle", identifier, "--returned", "900")


class TestListing:
    def test_an_absent_ledger_is_not_a_broken_one(self, tmp_path, capsys):
        code = run(tmp_path, "--list")

        assert code == 0
        assert "No position is open" in capsys.readouterr().out

    def test_an_open_position_means_something_awaits_you(self, tmp_path, capsys):
        place(tmp_path)

        code = run(tmp_path, "--list")

        assert code == 1
        assert "invisible to the daily loss limit" in capsys.readouterr().out

    def test_a_settled_but_unapplied_outcome_also_awaits_you(self, tmp_path):
        place(tmp_path)
        run(tmp_path, "--settle", only_position(tmp_path).position_id, "--returned", "1")

        assert run(tmp_path, "--list") == 1

    def test_no_arguments_lists(self, tmp_path, capsys):
        place(tmp_path)

        run(tmp_path)

        assert "OPEN" in capsys.readouterr().out


class TestAnUnreadableLedgerRefuses:
    def test_writing_to_it_is_refused(self, tmp_path, capsys):
        (tmp_path / "outcomes.json").write_text("{not json", encoding="utf-8")

        code = place(tmp_path)

        assert code == 2
        assert "still holding money" in capsys.readouterr().out

    def test_listing_it_says_so_rather_than_reporting_nothing_open(self, tmp_path, capsys):
        (tmp_path / "outcomes.json").write_text("[[[", encoding="utf-8")

        code = run(tmp_path, "--list")

        assert code == 2
        assert "not a report that nothing is open" in capsys.readouterr().out


class TestApplyingToTheBreakers:
    def _four_losses(self, tmp_path):
        config_file(tmp_path)
        for index in range(4):
            place(tmp_path, subject=f"match {index}", staked="5")
        book = OutcomeLedger(tmp_path / "outcomes.json")
        for position in book.positions:
            book.settle(position.position_id, 0.0)
        book.save()

    def test_four_recorded_losses_trip_the_lane_through_the_cli(self, tmp_path, capsys):
        """End to end through the command a person actually types."""

        self._four_losses(tmp_path)

        code = run(tmp_path, "--apply")

        assert code == 1
        assert "BREAKER TRIPPED: consecutive losses" in capsys.readouterr().out

    def test_it_says_the_breaker_will_not_clear_itself(self, tmp_path, capsys):
        self._four_losses(tmp_path)

        run(tmp_path, "--apply")

        assert "does not reset itself" in capsys.readouterr().out

    def test_applying_twice_does_not_double_count(self, tmp_path):
        self._four_losses(tmp_path)
        run(tmp_path, "--apply")

        from lib.breakers import Breakers, Ringfence

        run(tmp_path, "--apply")
        controls = Breakers(Ringfence("arb", 1000.0), tmp_path / "breakers-arb.json",
                            kill_switch=tmp_path / "HALT")

        assert controls.profit_today() == pytest.approx(-20.0)

    def test_a_lane_with_outcomes_and_no_breakers_is_reported_not_skipped(self, tmp_path,
                                                                         capsys):
        """Otherwise its losses reach nothing while the report reads tidy."""

        config_file(tmp_path)
        place(tmp_path, lane="stocks", subject="MODN", staked="900")
        book = OutcomeLedger(tmp_path / "outcomes.json")
        book.settle(book.positions[0].position_id, 0.0)
        book.save()

        run(tmp_path, "--apply")

        assert "its results reach nothing" in capsys.readouterr().out

    def test_an_unreadable_config_refuses_rather_than_applying_to_nothing(self, tmp_path,
                                                                         capsys):
        (tmp_path / "reapers.json").write_text("{not json", encoding="utf-8")

        code = run(tmp_path, "--apply")

        assert code == 2
        assert "would reach nothing while this printed a tidy summary" in (
            capsys.readouterr().out)

    def test_no_lane_configured_at_all_is_exit_two(self, tmp_path, capsys):
        (tmp_path / "reapers.json").write_text("{}", encoding="utf-8")

        code = run(tmp_path, "--apply")

        assert code == 2
        assert "reaching no breaker at all" in capsys.readouterr().out

    def test_a_clean_application_with_nothing_live_is_exit_zero(self, tmp_path):
        config_file(tmp_path)
        place(tmp_path, staked="5")
        book = OutcomeLedger(tmp_path / "outcomes.json")
        book.settle(book.positions[0].position_id, 6.0)
        book.save()

        assert run(tmp_path, "--apply") == 0

    def test_an_open_position_keeps_the_exit_code_at_one(self, tmp_path):
        config_file(tmp_path)
        place(tmp_path, staked="5")

        assert run(tmp_path, "--apply") == 1


class TestATripAtAKeyboardIsNotAQuietLane:
    """A breaker can trip here, hours or a day before the lane it stopped next runs. Until
    this was wired, that trip was announced on the next reap — so a lane stopped by the
    fourth losing result looked exactly like a lane finding nothing, for as long as its
    cadence is. The stocks cadence is 24 hours."""

    class Channel:
        is_configured = True

        def __init__(self):
            self.sent = []

        def send(self, subject, body):
            from lib.notify import SENT, Delivery

            self.sent.append((subject, body))
            return Delivery(SENT, "now", subject)

    def announcer(self, tmp_path, channel):
        from lib.announce import Announcer

        return Announcer(channel, memory_path=tmp_path / "announced.json")

    def a_losing_position(self, tmp_path):
        """One loss past the 3% daily limit on a 1,000 ring-fence."""

        config_file(tmp_path)
        place(tmp_path, staked="500")
        run(tmp_path, "--settle", only_position(tmp_path).position_id, "--returned", "0")

    def test_the_trip_is_announced_when_the_outcome_is_applied(self, tmp_path):
        self.a_losing_position(tmp_path)
        channel = self.Channel()

        code = positions.apply(tmp_path / "outcomes.json", tmp_path / "reapers.json",
                               announcer=self.announcer(tmp_path, channel))

        assert code == 1
        assert channel.sent and "BREAKER TRIPPED" in channel.sent[0][0]

    def test_applying_twice_does_not_report_the_same_trip_twice(self, tmp_path):
        """It does not reset itself, so it is still tripped every time this is run."""

        self.a_losing_position(tmp_path)
        channel = self.Channel()

        for _ in range(3):
            positions.apply(tmp_path / "outcomes.json", tmp_path / "reapers.json",
                            announcer=self.announcer(tmp_path, channel))

        assert len(channel.sent) == 1

    def test_an_ordinary_apply_says_nothing(self, tmp_path):
        """Nothing tripped. A message here would teach the reader to ignore the one that
        matters."""

        config_file(tmp_path)
        place(tmp_path, staked="5")
        run(tmp_path, "--settle", only_position(tmp_path).position_id, "--returned", "6")
        channel = self.Channel()

        positions.apply(tmp_path / "outcomes.json", tmp_path / "reapers.json",
                        announcer=self.announcer(tmp_path, channel))

        assert not channel.sent

    def test_a_notifier_that_fails_does_not_change_what_was_applied(self, tmp_path, capsys):
        """The outcomes reached the breakers before anything was sent. A messaging fault
        must not make a correct application look like a failed command."""

        self.a_losing_position(tmp_path)

        class Exploding:
            def announce_breakers(self, _assemblies):
                raise RuntimeError("the notifier broke")

        code = positions.apply(tmp_path / "outcomes.json", tmp_path / "reapers.json",
                               announcer=Exploding())

        assert code == 1
        assert "could not be notified" in capsys.readouterr().out
