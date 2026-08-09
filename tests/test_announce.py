"""A notifier is judged by what it does not send, and by what it never fails to send.

`lib/notify` was built, tested, and called by nothing. Wiring it in is not the small job it
sounds like, because the two ways of getting it wrong sit on opposite sides of one dial.

Send everything, every run, and the arb lane's eight-hourly cadence produces three messages
a day about one standing market. The reader learns the messages are noise and stops opening
them — and the failure lands later, when the message that mattered arrives and is not read.
A signal still present, still true, carrying no information.

Send only what is new, and every suppression is a small silence: a standing opportunity
mentioned once and never again, an order that may or may not exist reported behind a
"you've seen this" rule that was written for something else entirely.

So the properties below are mostly about which of those two errors each case chooses, and
the choice is never split down the middle. A repeat is bounded rather than permanent
(`lib/seen`'s argument: a thing that is still there is still real). An unresolved placement
is keyed by the order, so it can never be deduped away by the READY message that preceded
it. A lost memory suppresses nothing at all, which inverts `CLAUDE.md`'s fail-toward-
stopping — that rule is about money moving, and here the failure worth avoiding is the
invisible one.

And nothing in here may take a lane down. A run that reached READY and then died trying to
tell somebody has lost the finding in the act of reporting it.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import lib.announce as announce
import lib.notify as notify
from lib.announce import (ALREADY_TOLD, ANNOUNCED, Announcer, Line, NOT_CONFIGURED,
                          UNTOLD)
from lib.breakers import ARMED, TRIPPED, BreakerState
from lib.placing import NOT_PLACED, PLACED, Placement, REFUSED, UNRESOLVED
from lib.reaping import Assembly, CONFIGURED, Reaping, UNREADABLE
from lib.reaping import NOT_CONFIGURED as LANE_NOT_CONFIGURED


class Channel:
    """A Telegram that records instead of sending, and can be told to fail."""

    def __init__(self, status: str = notify.SENT, configured: bool = True) -> None:
        self.status = status
        self.is_configured = configured
        self.sent: list[tuple[str, str]] = []

    def send(self, subject: str, body: str):
        self.sent.append((subject, body))
        return notify.Delivery(self.status, "2026-08-09T10:00:00Z", subject,
                               reason="the token was refused")


@dataclass
class Order:
    ticker: str = "ALAB"
    side: str = "buy"
    shares: int = 4
    price: float = 120.5
    cash: float = 482.0
    currency: str = "USD"
    bound_by: str = "the per-position cap"
    at: str = "2026-08-09T10:00:00Z"


@dataclass
class Leg:
    book: str
    selection: str
    decimal_odds: float
    stake: float
    settlement_rule: str = ""


@dataclass
class Slip:
    legs: tuple = ()
    total_stake: float = 100.0
    guaranteed_return: float = 104.0
    observed_at: str = "2026-08-09T10:00:00Z"


@dataclass
class Harvest:
    lane: str
    status: str
    subject: str = ""
    at: str = "2026-08-09T10:00:00Z"
    reason: str = ""
    instruction: Any = None
    permission: Any = None

    def describe(self) -> str:
        return f"{self.status}  [{self.lane}]  {self.subject}"


def ready(lane: str = "stocks", subject: str = "ALAB", instruction: Any = None) -> Harvest:
    return Harvest(lane, "READY", subject,
                   instruction=instruction if instruction is not None else Order())


def blind(lane: str = "arb", reason: str = "the odds feed did not answer") -> Harvest:
    return Harvest(lane, "COULD_NOT_LOOK", reason=reason)


def reaping(*harvests: Harvest, assemblies=(), placements=(), modes=()) -> Reaping:
    """A finished run carrying whatever the test needs it to carry."""

    lanes = {h.lane for h in harvests}
    built = assemblies or tuple(Assembly(lane, CONFIGURED, reaper=SimpleNamespace(
        breakers=SimpleNamespace(state=BreakerState(lane, ARMED)))) for lane in sorted(lanes))
    return Reaping(built, harvests, placements=placements, modes=modes)


def announcer(tmp_path, channel=None, **kw) -> Announcer:
    return Announcer(channel if channel is not None else Channel(),
                     memory_path=tmp_path / "announced.json",
                     theses_path=tmp_path / "theses.json", **kw)


class TestAStandingOpportunityIsToldAgainButNotEveryRun:
    def test_a_ready_instruction_is_announced(self, tmp_path):
        channel = Channel()

        out = announcer(tmp_path, channel).announce_reaping(reaping(ready()))

        assert [a.status for a in out] == [ANNOUNCED]
        assert "ALAB" in channel.sent[0][0]

    def test_the_same_instruction_on_the_next_run_is_not_sent_again(self, tmp_path):
        """The arb lane wakes every eight hours and the market is still there."""

        channel = Channel()
        announcer(tmp_path, channel).announce_reaping(reaping(ready()))
        second = announcer(tmp_path, channel).announce_reaping(reaping(ready()))

        assert [a.status for a in second] == [ALREADY_TOLD]
        assert len(channel.sent) == 1

    def test_it_is_told_again_once_the_window_has_passed(self, tmp_path):
        """Suppressing forever would hide a persistent edge, which `lib/seen` argues is
        the expensive direction of this particular error."""

        channel = Channel()
        announcer(tmp_path, channel).announce_reaping(reaping(ready()))
        later = announcer(tmp_path, channel, repeat_after=0).announce_reaping(
            reaping(ready()))

        assert [a.status for a in later] == [ANNOUNCED]
        assert len(channel.sent) == 2

    def test_two_different_subjects_are_two_different_messages(self, tmp_path):
        channel = Channel()

        out = announcer(tmp_path, channel).announce_reaping(
            reaping(ready(subject="ALAB"), ready(subject="CRDO")))

        assert [a.status for a in out] == [ANNOUNCED, ANNOUNCED]
        assert len(channel.sent) == 2


class TestTheMemoryFailsTowardTelling:
    def test_an_unreadable_memory_suppresses_nothing(self, tmp_path):
        """The inversion of the usual rule, and the reason it is written down.

        Failing toward stopping is about money moving. What can fail here is the record of
        what you have been told, and stopping means an opportunity nobody hears about —
        invisible, where a duplicate message is merely a duplicate message.
        """

        (tmp_path / "announced.json").write_text("{not json at all")
        channel = Channel()

        out = announcer(tmp_path, channel).announce_reaping(reaping(ready()))

        assert [a.status for a in out] == [ANNOUNCED]

    def test_a_lost_memory_does_not_stop_the_run(self, tmp_path):
        (tmp_path / "announced.json").write_text("[]")

        assert announcer(tmp_path).announce_reaping(reaping(ready()))

    def test_a_message_that_did_not_go_is_not_recorded_as_told(self, tmp_path):
        """A token that expires for an hour must not cost an opportunity permanently."""

        failing = Channel(status=notify.UNREACHABLE)
        first = announcer(tmp_path, failing).announce_reaping(reaping(ready()))

        working = Channel()
        second = announcer(tmp_path, working).announce_reaping(reaping(ready()))

        assert [a.status for a in first] == [UNTOLD]
        assert first[0].delivery == notify.UNREACHABLE
        assert [a.status for a in second] == [ANNOUNCED]
        assert len(working.sent) == 1

    def test_no_channel_is_not_a_failure_and_not_a_delivery(self, tmp_path):
        """Somebody who never set up Telegram has not had a notification fail."""

        out = announcer(tmp_path, Channel(configured=False)).announce_reaping(
            reaping(ready()))

        assert [a.status for a in out] == [NOT_CONFIGURED]
        assert "nowhere else" in out[0].describe()

    def test_what_could_not_be_told_is_told_once_a_channel_exists(self, tmp_path):
        announcer(tmp_path, Channel(configured=False)).announce_reaping(reaping(ready()))
        channel = Channel()

        out = announcer(tmp_path, channel).announce_reaping(reaping(ready()))

        assert [a.status for a in out] == [ANNOUNCED]


class TestMoneyThatMayHaveMoved:
    def test_an_unresolved_placement_is_announced(self, tmp_path):
        """The most expensive state this system produces: an order was submitted, nothing
        came back, and a position is on file that may or may not exist."""

        channel = Channel()
        run = reaping(ready(), placements=(Placement(
            "stocks", UNRESOLVED, subject="ALAB", position_id="POS-1",
            client_order_id="COID-1", reason="the broker did not answer"),))

        out = announcer(tmp_path, channel).announce_reaping(run)

        assert [a.status for a in out] == [ANNOUNCED]
        assert "MAY EXIST" in channel.sent[0][0]

    def test_a_placed_order_is_never_reported_as_waiting_for_a_person(self, tmp_path):
        """`READY` says "a person places it". After a fill that sentence is false."""

        channel = Channel()
        run = reaping(ready(), placements=(Placement(
            "stocks", PLACED, subject="ALAB", position_id="POS-1",
            client_order_id="COID-1", filled_quantity=4, requested_quantity=4),))

        announcer(tmp_path, channel).announce_reaping(run)

        assert len(channel.sent) == 1
        assert "PLACED" in channel.sent[0][0]

    def test_an_unresolved_order_is_not_suppressed_by_the_ready_message(self, tmp_path):
        """The dedupe rule was written for standing opportunities. Applying it to an
        order that may exist would silence the one message nobody may miss."""

        channel = Channel()
        announcer(tmp_path, channel).announce_reaping(reaping(ready()))

        out = announcer(tmp_path, channel).announce_reaping(reaping(ready(), placements=(
            Placement("stocks", UNRESOLVED, subject="ALAB", position_id="POS-1"),)))

        assert [a.status for a in out] == [ANNOUNCED]

    def test_a_lane_with_no_adapter_does_not_report_a_failure_to_place(self, tmp_path):
        """Bookmakers take no orders from a program. That is not a placement problem and
        a second message about it would say otherwise."""

        channel = Channel()
        run = reaping(ready(lane="arb", subject="Chelsea v Arsenal", instruction=Slip(
            legs=(Leg("Sky Bet", "Chelsea", 2.1, 50.0),
                  Leg("Betfair", "Draw or Arsenal", 2.2, 50.0)))),
            placements=(Placement("arb", NOT_PLACED, subject="Chelsea v Arsenal",
                                  reason="bookmakers have no betting API"),))

        out = announcer(tmp_path, channel).announce_reaping(run)

        assert [a.status for a in out] == [ANNOUNCED]
        assert "ARB READY" in channel.sent[0][0]

    def test_a_refused_placement_does_not_take_the_instruction_with_it(self, tmp_path):
        """A refusal leaves the instruction sized and waiting, so both go: what to do,
        and what the machine tried and could not. Only a placed or unresolved order makes
        "a person places it" the wrong thing to say."""

        channel = Channel()
        run = reaping(ready(), placements=(Placement(
            "stocks", REFUSED, subject="ALAB",
            reason="the outcome ledger could not be read"),))

        out = announcer(tmp_path, channel).announce_reaping(run)

        assert [a.status for a in out] == [ANNOUNCED, ANNOUNCED]
        assert {"NOT PLACED · stocks · ALAB", "STOCKS READY · 4 ALAB · 482.00 USD"} == {
            subject for subject, _ in channel.sent}


class TestALaneThatStoppedIsNotALaneThatFoundNothing:
    def test_one_failure_to_look_is_not_worth_waking_somebody(self, tmp_path):
        """A flaky endpoint is not a broken pipeline, and a notifier that cannot tell the
        difference teaches its reader to ignore both."""

        channel = Channel()

        out = announcer(tmp_path, channel).announce_reaping(reaping(blind()))

        assert not [a for a in out if a.status == ANNOUNCED]
        assert not channel.sent

    def test_three_in_a_row_is_a_pipeline_and_is_announced(self, tmp_path):
        channel = Channel()
        for _ in range(3):
            out = announcer(tmp_path, channel).announce_reaping(reaping(blind()))

        assert [a.status for a in out] == [ANNOUNCED]
        assert "BLIND" in channel.sent[0][0]

    def test_a_lane_that_looks_again_starts_the_count_from_nothing(self, tmp_path):
        """Two blind runs on Monday and one on Friday is not a broken pipeline."""

        channel = Channel()
        for _ in range(2):
            announcer(tmp_path, channel).announce_reaping(reaping(blind()))
        announcer(tmp_path, channel).announce_reaping(
            reaping(Harvest("arb", "NOTHING_FOUND")))
        announcer(tmp_path, channel).announce_reaping(reaping(blind()))

        assert not channel.sent

    def test_a_lane_nobody_configured_is_never_blind(self, tmp_path):
        """Nothing was asked of it. It did not fail to look; it was not looking."""

        channel = Channel()
        run = Reaping((Assembly("crypto", LANE_NOT_CONFIGURED),), ())
        for _ in range(5):
            announcer(tmp_path, channel).announce_reaping(run)

        assert not channel.sent

    def test_a_halted_lane_is_a_decision_rather_than_a_breakage(self, tmp_path):
        """Somebody wrote data/HALT. Reporting that as a broken pipeline every six hours
        would train the reader to ignore the message that means something."""

        channel = Channel()
        run = Reaping(
            (Assembly("arb", CONFIGURED, reaper=SimpleNamespace(
                breakers=SimpleNamespace(state=BreakerState("arb", ARMED)))),), (),
            modes=(SimpleNamespace(lane="arb", may_reap=False),))
        for _ in range(5):
            announcer(tmp_path, channel).announce_reaping(run)

        assert not channel.sent

    def test_a_lane_whose_configuration_will_not_read_counts_as_blind(self, tmp_path):
        """UNREADABLE is a lane that was asked to look and could not, which is the same
        fact as an unanswered source from the reader's side."""

        channel = Channel()
        run = Reaping((Assembly("stocks", UNREADABLE,
                                reason="the breaker state would not parse"),), ())
        for _ in range(3):
            out = announcer(tmp_path, channel).announce_reaping(run)

        assert [a.status for a in out] == [ANNOUNCED]


class TestATrippedBreakerIsToldOncePerTrip:
    def tripped(self, at: str = "2026-08-09T09:00:00Z") -> Reaping:
        state = BreakerState("stocks", TRIPPED, "daily loss limit", at,
                             "three losses took the day past 3%")
        # A real tripped run still produces a harvest: the lane looks, and its own breaker
        # check refuses what it found. A lane emitting nothing at all is a different fact.
        return Reaping((Assembly("stocks", CONFIGURED, reaper=SimpleNamespace(
            breakers=SimpleNamespace(state=state))),),
            (Harvest("stocks", "REFUSED", "ALAB", reason="the breakers blocked it"),))

    def test_a_trip_is_announced(self, tmp_path):
        channel = Channel()

        out = announcer(tmp_path, channel).announce_reaping(self.tripped())

        assert [a.status for a in out] == [ANNOUNCED]
        assert "BREAKER TRIPPED" in channel.sent[0][0]

    def test_the_same_trip_is_not_re_announced_every_run(self, tmp_path):
        """It does not reset on a timer, so it is still tripped on every run for as long
        as nobody re-arms it. Six hourly reminders would not make that clearer."""

        channel = Channel()
        for _ in range(4):
            announcer(tmp_path, channel).announce_reaping(self.tripped())

        assert len(channel.sent) == 1

    def test_a_second_trip_after_a_reset_is_a_second_message(self, tmp_path):
        channel = Channel()
        announcer(tmp_path, channel).announce_reaping(self.tripped())

        announcer(tmp_path, channel).announce_reaping(
            self.tripped(at="2026-08-10T09:00:00Z"))

        assert len(channel.sent) == 2

    def test_an_armed_breaker_says_nothing(self, tmp_path):
        channel = Channel()

        announcer(tmp_path, channel).announce_reaping(reaping(ready()))

        assert all("BREAKER" not in subject for subject, _ in channel.sent)


class TestNothingHereMayEndARun:
    def test_a_formatter_that_raises_becomes_untold_rather_than_a_crash(self, tmp_path):
        """The finding was real. Reporting it badly beats losing it."""

        channel = Channel()
        # An instruction with none of the fields a stocks message reads off it.
        broken = Harvest("stocks", "READY", "ALAB", instruction=object())

        out = announcer(tmp_path, channel).announce_reaping(reaping(broken))

        assert [a.status for a in out] == [UNTOLD]
        assert "could not be built" in out[0].reason

    def test_one_broken_message_does_not_stop_the_others(self, tmp_path):
        channel = Channel()

        out = announcer(tmp_path, channel).announce_reaping(reaping(
            Harvest("stocks", "READY", "BAD", instruction=object()), ready(subject="ALAB")))

        assert {a.status for a in out} == {UNTOLD, ANNOUNCED}

    def test_a_channel_that_raises_does_not_escape(self, tmp_path):
        class Exploding:
            is_configured = True

            def send(self, *_a):
                raise RuntimeError("the socket died")

        out = announcer(tmp_path, Exploding()).announce_reaping(reaping(ready()))

        assert [a.status for a in out] == [UNTOLD]


class TestTheDigestIsTheHeartbeat:
    def test_it_reports_lanes_that_found_nothing(self, tmp_path):
        """A digest listing only findings is indistinguishable from one that never sent."""

        channel = Channel()

        announcer(tmp_path, channel).announce_heartbeat(
            [Line("reap-arb", "COMPLETED"), Line("reap-stocks", "NEVER_RAN")])

        assert "NEVER_RAN" in channel.sent[0][1]

    def test_it_goes_once_a_day_however_often_it_is_offered(self, tmp_path):
        """The supervisor wakes every minute and offers the digest every time."""

        channel = Channel()
        for _ in range(5):
            announcer(tmp_path, channel).announce_heartbeat([Line("reap-arb", "COMPLETED")],
                                                            day="2026-08-09")

        assert len(channel.sent) == 1

    def test_a_new_day_is_a_new_digest(self, tmp_path):
        channel = Channel()
        announcer(tmp_path, channel).announce_heartbeat([], day="2026-08-09")

        announcer(tmp_path, channel).announce_heartbeat([], day="2026-08-10")

        assert len(channel.sent) == 2

    def test_a_digest_that_failed_to_send_is_retried_the_same_day(self, tmp_path):
        """Recording a failure as sent would make the alarm's absence mean nothing."""

        announcer(tmp_path, Channel(status=notify.UNREACHABLE)).announce_heartbeat(
            [], day="2026-08-09")
        working = Channel()

        out = announcer(tmp_path, working).announce_heartbeat([], day="2026-08-09")

        assert out.status == ANNOUNCED
        assert len(working.sent) == 1


class TestAMessageCarriesTheReasonOrSaysWhyItCannot:
    def test_a_stocks_message_carries_the_thesis(self, tmp_path):
        (tmp_path / "theses.json").write_text(json.dumps([{
            "subject": "ALAB", "declared_by": "Ian McGuane",
            "reasoning": "interconnect spending scales with the build-out",
            "considered": ["customer concentration"],
            "declared_at": "2026-08-08T00:00:00Z", "expires_at": "2027-01-01T00:00:00Z",
            "max_exposure": 500.0, "currency": "USD"}]))
        channel = Channel()

        announcer(tmp_path, channel).announce_reaping(reaping(ready()))

        assert "interconnect spending" in channel.sent[0][1]

    def test_an_unreadable_register_is_not_reported_as_an_unreasoned_instruction(
            self, tmp_path):
        """"No thesis was attached" would tell a reader their gates let something through
        unauthorised, when in fact a file failed to parse. Two different emergencies."""

        (tmp_path / "theses.json").write_text("{[")
        channel = Channel()

        announcer(tmp_path, channel).announce_reaping(reaping(ready()))
        body = channel.sent[0][1]

        assert "not shown" in body
        assert "no thesis reasoning was attached" not in body

    def test_the_chain_message_says_nothing_here_can_sign_it(self, tmp_path):
        """An operator who waits for a fill on this lane waits for an event that cannot
        occur."""

        channel = Channel()
        plan = SimpleNamespace(token_in="USDC", token_out="0xabc", amount_in=100_000_000,
                               quoted_out=5_000, min_out=4_975, slippage_bps=50,
                               block_number=21_000_000, steps=(1, 2), at="2026-08-09")

        announcer(tmp_path, channel).announce_reaping(
            reaping(ready(lane="crypto", subject="LINK", instruction=plan)))

        subject, body = channel.sent[0]
        assert "UNSIGNED" in subject
        assert "NOTHING HERE CAN SIGN THIS" in body

    def test_the_bot_token_is_removed_without_taking_the_diagnosis_with_it(self):
        """A refusal has to name what a person can go and do about it."""

        redacted = notify._redact(
            "HTTP Error 401: Unauthorized for url: "
            "https://api.telegram.org/bot12345:SECRET/sendMessage")

        assert "SECRET" not in redacted
        assert "401" in redacted and "sendMessage" in redacted


class TestTheWireItself:
    """`lib/notify` was built, tested and called by nothing for a day. The property that
    keeps it called is not that a function exists but that the run reaches it."""

    def test_a_reap_hands_its_finished_run_to_the_announcer(self, tmp_path):
        import lib.reaping

        seen = []

        class Stub:
            def announce_reaping(self, run):
                seen.append(run)
                return (announce.Announcement("READY", "arb", "x", ANNOUNCED),)

        out = lib.reaping.reap(config_path=tmp_path / "reapers.json", directory=tmp_path,
                               ledger_path=tmp_path / "outcomes.json",
                               theses_path=tmp_path / "theses.json", announcer=Stub())

        assert seen and [a.status for a in out.announcements] == [ANNOUNCED]

    def test_the_default_is_the_production_announcer_rather_than_none(self, tmp_path,
                                                                     monkeypatch):
        """A wire that only works when a caller passes an announcer is not wired."""

        import lib.reaping

        built = []
        monkeypatch.setattr(lib.reaping, "default_announcer",
                            lambda: built.append(True) or Announcer(None))

        lib.reaping.reap(config_path=tmp_path / "reapers.json", directory=tmp_path,
                         ledger_path=tmp_path / "outcomes.json",
                         theses_path=tmp_path / "theses.json")

        assert built

    def test_a_dry_run_tells_nobody_and_says_so(self, tmp_path):
        """`--dry` promises to send nothing whatever the modes say. A flag that messaged
        somebody's phone anyway is a flag nobody can trust again."""

        import lib.reaping

        out = lib.reaping.reap(config_path=tmp_path / "reapers.json", directory=tmp_path,
                               ledger_path=tmp_path / "outcomes.json",
                               theses_path=tmp_path / "theses.json", place=False)

        assert not out.announcements
        assert "dry run" in out.describe()
        assert out.to_dict()["notifications"]["status"] == "NOT_ATTEMPTED"

    def test_a_notifier_that_explodes_does_not_lose_the_run(self, tmp_path):
        """The findings would be destroyed in the act of reporting them."""

        import lib.reaping

        class Exploding:
            def announce_reaping(self, _run):
                raise RuntimeError("the notifier itself broke")

        out = lib.reaping.reap(config_path=tmp_path / "reapers.json", directory=tmp_path,
                               ledger_path=tmp_path / "outcomes.json",
                               theses_path=tmp_path / "theses.json",
                               announcer=Exploding())

        assert out.assemblies
        assert "still stands" in out.describe()

    def test_the_report_always_says_whether_anybody_was_told(self, tmp_path):
        """On a screen, a run that could not tell anybody looks exactly like one that
        did. The person who is not reading the screen is the point."""

        run = Reaping((Assembly("stocks", CONFIGURED),), (ready(),), announcements=(
            announce.Announcement("READY", "stocks", "ALAB", UNTOLD,
                                  delivery=notify.REFUSED, reason="bad token"),))

        assert "DID NOT GO OUT" in run.describe()


class TestTheSupervisorOffersTheDigestEveryTick:
    def test_it_is_offered_on_every_tick_and_sent_once(self, tmp_path, monkeypatch):
        """A supervisor restarted every morning with a 24-hour timer sends nothing ever.
        The date key is what makes offering it cheaply the right design."""

        import run as runner

        monkeypatch.setattr(runner, "main", lambda go: 0)
        monkeypatch.setattr(runner, "STATE", tmp_path / "orchestrator.json")
        channel = Channel()

        runner.serve(interval=0, limit=3, heartbeat=tmp_path / "heartbeat.json",
                     announcer=announcer(tmp_path, channel))

        assert len(channel.sent) == 1

    def test_the_digest_names_every_lane_including_the_ones_that_never_ran(
            self, tmp_path, monkeypatch):
        """On a system where nothing is on a cadence yet, NEVER_RAN is the most useful
        line in the message — and the one a findings-only digest would omit."""

        import run as runner

        monkeypatch.setattr(runner, "main", lambda go: 0)
        monkeypatch.setattr(runner, "STATE", tmp_path / "orchestrator.json")
        channel = Channel()

        runner.serve(interval=0, limit=1, heartbeat=tmp_path / "heartbeat.json",
                     announcer=announcer(tmp_path, channel))

        body = channel.sent[0][1]
        assert "reap-arb" in body and "NEVER_RAN" in body

    def test_a_broken_digest_does_not_end_the_schedule(self, tmp_path, monkeypatch):
        """A messaging outage is a poor reason for the lanes to stop running."""

        import run as runner

        ticks = []
        monkeypatch.setattr(runner, "main", lambda go: ticks.append(go) or 0)
        monkeypatch.setattr(runner, "STATE", tmp_path / "orchestrator.json")

        class Exploding:
            def announce_heartbeat(self, *_a, **_kw):
                raise RuntimeError("the digest broke")

        runner.serve(interval=0, limit=3, heartbeat=tmp_path / "heartbeat.json",
                     announcer=Exploding())

        assert len(ticks) == 3
