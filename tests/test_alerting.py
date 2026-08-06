"""A monitoring system's own failures must not look like good news.

Every state this raises was already visible somewhere. `operations.alerts` has existed since
the operator backend landed with nothing writing to it, and a dashboard reports nothing to a
person who is not looking at it — so a system that stopped three days ago and a system with
nothing to say produce the same silence.

The properties below are the ones where the alerting itself is the thing that fails. A look
that could not gather state must not report an empty list of conditions, because that is
indistinguishable from a clean run. A condition that could not be delivered must not be
recorded as announced, or it goes quiet for the whole cooldown having never left the
machine. A store that will not parse must make everything due rather than nothing. And a
condition that clears must leave the store, or the next occurrence starts inside its own
cooldown and stays silent.

The last one is why the exit codes tell 1 apart from 2: raised-and-delivered has done its
job, raised-and-nobody-told has not, and a code that made them equal would file the failure
of the alerting under the alerting working.
"""
from __future__ import annotations

import json

import pytest

from lib.alerting import (
    ASSESSED,
    ATTENTION,
    COULD_NOT_ASSESS,
    DELIVERED,
    NOT_CONFIGURED,
    STOP,
    UNDELIVERABLE,
    AlertStore,
    Assessment,
    Condition,
    assess,
    deliver,
)


def state(**blocks) -> dict:
    base = {
        "scheduler": {"status": "RUNNING", "last_tick_at": "2026-08-06T12:00:00Z"},
        "capital": {"value_status": "EMPTY_BOOK"},
        "money_lanes": [],
    }
    base.update(blocks)
    return base


def lane(name="arb", **fields) -> dict:
    base = {
        "lane": name,
        "places_without_asking": False,
        "breaker": {"status": "ARMED"},
        "positions": {"status": "OK", "stale_open": 0},
        "quota": {"status": "UNKNOWN", "remaining": None, "floor": 25},
    }
    base.update(fields)
    return base


class FakeChannel:
    name = "fake"

    def __init__(self, *, unavailable="", raises=None):
        self._unavailable, self._raises = unavailable, raises
        self.sent: list[tuple[str, ...]] = []

    def unavailable_reason(self) -> str:
        return self._unavailable

    def send(self, conditions, *, assessment):
        if self._raises:
            raise self._raises
        self.sent.append(tuple(c.key for c in conditions))


class TestALookThatFailedIsNotACleanBillOfHealth:
    def test_state_that_could_not_be_gathered_is_could_not_assess(self):
        assessment = assess(None, reason="ImportError: status")

        assert assessment.look == COULD_NOT_ASSESS
        assert assessment.needs_a_person is True

    def test_a_failed_look_still_reaches_a_person(self):
        """Silence is what a failed check produces, and silence is the thing being fixed."""

        channel = FakeChannel()

        delivery = deliver(assess(None, reason="boom"), AlertStore("/tmp/never.json"), channel)

        assert delivery.status == DELIVERED
        assert channel.sent == [("assessment-failed",)]

    def test_a_clean_look_and_a_failed_look_do_not_read_alike(self):
        clean = assess(state())

        assert clean.look == ASSESSED
        assert clean.conditions == ()
        assert clean.needs_a_person is False
        assert "Nothing to report" in clean.describe()
        assert "not a clean bill of health" in assess(None, reason="x").describe()


class TestTheConditionsThatStopALane:
    def test_a_tripped_breaker_is_a_stop_naming_that_it_does_not_self_clear(self):
        found = assess(state(money_lanes=[lane(breaker={"status": "TRIPPED"})])).conditions

        assert [c.key for c in found] == ["breaker-tripped:arb"]
        assert found[0].severity == STOP
        assert "does not self-clear" in found[0].summary

    def test_an_unreadable_breaker_sends_a_person_to_the_file_to_restore(self):
        found = assess(state(money_lanes=[lane(breaker={"status": "UNREADABLE"})])).conditions

        assert found[0].key == "breaker-unreadable:arb"
        assert "data/breakers-arb.json" in found[0].action

    def test_an_unbuildable_ring_fence_is_not_reported_as_a_corrupt_file(self):
        """The two shared the word UNREADABLE, and one of them has no file to repair.

        This alert told an operator to inspect `data/breakers-stocks.json` for a lane whose
        config simply had no balance in it. The file had never existed. A refusal that names
        the wrong thing to go and do is worse than one that names nothing.
        """

        found = assess(state(money_lanes=[lane(
            "stocks", breaker={"status": "INVALID_CONFIGURATION", "reason": "KeyError: 'balance'"}
        )])).conditions

        assert found[0].key == "lane-misconfigured:stocks"
        assert "data/reapers.json" in found[0].action
        assert "breakers-stocks.json" not in found[0].action

    def test_placing_without_asking_and_without_limits_is_one_condition_not_two(self):
        """Neither half alarms on its own; together nothing bounds what the lane spends."""

        found = assess(state(money_lanes=[lane(
            places_without_asking=True, breaker={"status": "NOT_CONFIGURED"}
        )])).conditions

        assert [c.key for c in found] == ["autonomous-without-limits:arb"]
        assert found[0].severity == STOP

    def test_a_manual_lane_without_limits_does_not_alarm(self):
        assert assess(state(money_lanes=[lane(breaker={"status": "NOT_CONFIGURED"})])).conditions == ()

    def test_a_stopped_supervisor_is_the_loudest_thing_here(self):
        found = assess(state(scheduler={"status": "STALE", "last_tick_at": "2026-08-01T00:00:00Z"})).conditions

        assert found[0].key == "supervisor-stale"
        assert found[0].severity == STOP

    def test_a_supervisor_that_never_ran_is_attention_rather_than_stop(self):
        """Nothing is at risk from a system that has not started. It still wants a person."""

        found = assess(state(scheduler={"status": "NEVER_STARTED"})).conditions

        assert found[0].severity == ATTENTION

    def test_an_unreadable_heartbeat_says_it_cannot_tell_rather_than_reporting_fine(self):
        found = assess(state(scheduler={"status": "UNREADABLE", "reason": "bad json"})).conditions

        assert found[0].key == "supervisor-unreadable"
        assert found[0].severity == STOP

    def test_a_measured_quota_at_its_floor_is_raised(self):
        found = assess(state(money_lanes=[lane(
            quota={"status": "KNOWN", "remaining": 11, "floor": 25}
        )])).conditions

        assert found[0].key == "quota-floor:arb"
        assert "looks exactly like a quiet market" in found[0].summary

    def test_a_quota_nobody_measured_is_not_an_alert(self):
        """Never having looked is not the same as having looked and found it spent."""

        found = assess(state(money_lanes=[lane(
            quota={"status": "UNKNOWN", "remaining": None, "floor": 25}
        )])).conditions

        assert found == ()

    def test_stops_are_ordered_first_so_truncation_cannot_hide_them(self):
        found = assess(state(
            scheduler={"status": "NEVER_STARTED"},
            money_lanes=[lane(breaker={"status": "TRIPPED"})],
        )).conditions

        assert [c.severity for c in found] == [STOP, ATTENTION]


class TestAConditionMustNameWhatToDo:
    def test_a_condition_with_no_action_is_refused_at_construction(self):
        """"INDETERMINATE" on its own trains a reader to dismiss the next one too."""

        with pytest.raises(ValueError, match="names what a person"):
            Condition("k", STOP, "arb", "something is wrong", "   ")

    def test_a_severity_outside_the_two_is_refused(self):
        with pytest.raises(ValueError):
            Condition("k", "WARNING", "arb", "summary", "do this")


class TestSayingItTwiceAndSayingItNever:
    def _condition(self):
        return Condition("breaker-tripped:arb", STOP, "arb", "tripped", "re-arm it")

    def test_a_standing_condition_is_not_announced_every_run(self, tmp_path):
        store = AlertStore(tmp_path / "alerts.json")
        condition = self._condition()
        store.announced(condition)

        assert store.due(condition) is False

    def test_a_standing_condition_is_announced_again_after_the_cooldown(self, tmp_path):
        """A condition silenced forever by its own dedup is the defect it exists to fix."""

        store = AlertStore(tmp_path / "alerts.json")
        condition = self._condition()
        store.announced(condition)

        assert store.due(condition, repeat_after=0) is True

    def test_a_condition_that_clears_leaves_the_store(self, tmp_path):
        """Or its next occurrence starts inside a cooldown it never earned."""

        store = AlertStore(tmp_path / "alerts.json")
        condition = self._condition()
        store.announced(condition)

        assert store.cleared([]) == ("breaker-tripped:arb",)
        assert store.due(condition) is True

    def test_an_unreadable_store_makes_everything_due_rather_than_nothing(self, tmp_path):
        path = tmp_path / "alerts.json"
        path.write_text("{ not json", encoding="utf-8")

        store = AlertStore(path)

        assert store.readable is False
        assert store.due(self._condition()) is True

    def test_an_unreadable_store_refuses_to_be_overwritten(self, tmp_path):
        path = tmp_path / "alerts.json"
        path.write_text("{ not json", encoding="utf-8")

        with pytest.raises(RuntimeError, match="refusing to overwrite"):
            AlertStore(path).save()

    def test_a_saved_store_leaves_a_receipt_carrying_counts_and_not_subjects(self, tmp_path):
        store = AlertStore(tmp_path / "alerts.json")
        store.announced(self._condition())
        store.save()

        receipt = json.loads((tmp_path / "alerts.receipt.json").read_text(encoding="utf-8"))

        assert receipt["writes"] >= 1


class TestAnUndeliveredAlertIsNotADeliveredOne:
    def _assessment(self):
        return Assessment(ASSESSED, (Condition("k", STOP, "arb", "tripped", "re-arm"),))

    def test_a_failing_channel_does_not_record_the_condition_as_announced(self, tmp_path):
        """The ordering that makes this safe: send first, record after it returned.

        The reverse marks an alert delivered that never left the machine, and the condition
        then sits silent for the whole cooldown.
        """

        store = AlertStore(tmp_path / "alerts.json")
        channel = FakeChannel(raises=OSError("connection refused"))

        delivery = deliver(self._assessment(), store, channel)

        assert delivery.status == UNDELIVERABLE
        assert store.due(Condition("k", STOP, "arb", "tripped", "re-arm")) is True

    def test_no_channel_is_reported_as_nobody_told_rather_than_as_sent(self, tmp_path):
        delivery = deliver(self._assessment(), AlertStore(tmp_path / "a.json"), None)

        assert delivery.status == NOT_CONFIGURED
        assert "nobody has been told" in delivery.describe()

    def test_an_unconfigured_channel_names_what_to_configure(self, tmp_path):
        channel = FakeChannel(unavailable="write the URL to ~/.provena/alert_webhook")

        delivery = deliver(self._assessment(), AlertStore(tmp_path / "a.json"), channel)

        assert delivery.status == NOT_CONFIGURED
        assert "~/.provena/alert_webhook" in delivery.reason

    def test_nothing_to_say_is_delivered_rather_than_undeliverable(self, tmp_path):
        """An empty run must not report a delivery failure it never attempted."""

        delivery = deliver(Assessment(ASSESSED, ()), AlertStore(tmp_path / "a.json"), None)

        assert delivery.status == DELIVERED
        assert delivery.announced == ()


class TestTheExitCodesTellTheFailuresApart:
    def _run(self, monkeypatch, tmp_path, state_payload, *, channel=None, reason=""):
        import alerts
        import lib.alerting as alerting

        monkeypatch.setattr(alerting, "STORE", tmp_path / "alerts.json")
        monkeypatch.setattr(alerts, "STORE", tmp_path / "alerts.json")
        monkeypatch.setattr(alerting, "gather_state", lambda: (state_payload, reason))
        monkeypatch.setattr(alerts, "gather_state", lambda: (state_payload, reason))
        monkeypatch.setattr(alerts, "WebhookChannel", lambda: channel or FakeChannel())
        return alerts.run()

    def test_nothing_wrong_exits_zero(self, monkeypatch, tmp_path):
        _, code = self._run(monkeypatch, tmp_path, state())

        assert code == 0

    def test_raised_and_delivered_exits_one(self, monkeypatch, tmp_path):
        _, code = self._run(monkeypatch, tmp_path,
                            state(money_lanes=[lane(breaker={"status": "TRIPPED"})]))

        assert code == 1

    def test_raised_and_nobody_told_exits_two(self, monkeypatch, tmp_path):
        _, code = self._run(
            monkeypatch, tmp_path,
            state(money_lanes=[lane(breaker={"status": "TRIPPED"})]),
            channel=FakeChannel(unavailable="no webhook configured"),
        )

        assert code == 2

    def test_nothing_checked_at_all_exits_three(self, monkeypatch, tmp_path):
        _, code = self._run(monkeypatch, tmp_path, None, reason="ImportError")

        assert code == 3
