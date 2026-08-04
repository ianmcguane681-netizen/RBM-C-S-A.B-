"""A front end is the last place this repository's recurring defect can be reintroduced.

Every module below this one was built so that *not found* and *could not look* stay
different values. `--json` is where that care is either preserved or thrown away in one
line, because a serialiser has to choose a representation for an absence and the cheapest
choices — `0.0`, `[]`, omitting the key — are all the defect.

So these tests hold the boundary rather than the formatting. A monetary field nobody could
establish is null beside a status saying why. A run where every lane failed to reach its
source is not the same payload as a run where no lane was configured. A placement is
carried whether or not anything went in, because that is the one field behind which money
has already moved and a harvest list without it reads as "READY, nothing placed" on a run
that placed. And the exit codes are identical in both renderings: a caller that switched
to JSON and started reading 0 where it read 2 would have been told a broken pipeline was a
quiet morning by the act of asking for machine-readable output.
"""
from __future__ import annotations

import json

import positions
import run
import status
from lib.operating import AUTONOMOUS, OWNER_OPERATING_MANUALLY, Mode
from lib.outcomes import OPEN, SETTLED, UNKNOWN, VOID, Application, Position
from lib.placing import PLACED, UNRESOLVED, Placement
from lib.reaper import COULD_NOT_LOOK, NOTHING_FOUND, READY, Harvest
from lib.reaping import CONFIGURED, NOT_CONFIGURED, Assembly, Reaping
from lib.ui_contract import SCHEMA_VERSION


# --- money that does not exist stays absent -----------------------------------------

def test_an_open_position_reports_no_return_and_no_profit_rather_than_zero():
    """The stored `returned` is 0.0 on an OPEN position and publishing it is a lie.

    A reader rendering `staked 499.98, returned 0.00` beside a live bet shows a total
    loss that has not happened, and it shows it in the flattering-to-act-on direction:
    somebody looking at a screen of those will reach for the breaker.
    """

    payload = Position("POS-one", "arb", "Arsenal v Chelsea", OPEN, 499.98).to_dict()

    assert payload["status"] == OPEN
    assert payload["returned"] is None
    assert payload["profit"] is None
    assert payload["staked"] == 499.98


def test_an_unknown_position_reports_no_return_either():
    """UNKNOWN is the status that exists because the money's fate was not established.

    Of the four statuses this is the one where a zero is most tempting and most wrong:
    the position was placed, something happened to it, and nobody knows what.
    """

    payload = Position("POS-two", "arb", "a v b", UNKNOWN, 20.0,
                       note="bet365 restricted the account").to_dict()

    assert payload["returned"] is None
    assert payload["profit"] is None
    assert payload["note"]


def test_a_settled_position_publishes_the_return_it_actually_has():
    payload = Position("POS-three", "arb", "a v b", SETTLED, 20.0, returned=22.0).to_dict()

    assert payload["returned"] == 22.0
    assert payload["profit"] == 2.0


def test_a_void_publishes_its_returned_stake_and_no_profit():
    """A void returned the stake, so `returned` is a real figure — and profit is not.

    `Position.profit` is None unless SETTLED, and this is the case that proves the two
    fields are answering different questions rather than one deriving from the other.
    """

    payload = Position("POS-four", "arb", "a v b", VOID, 20.0, returned=20.0).to_dict()

    assert payload["returned"] == 20.0
    assert payload["profit"] is None


def test_an_absent_ledger_is_not_configured_rather_than_nothing_at_risk(tmp_path, capsys):
    code = positions.main(["--json", "--ledger", str(tmp_path / "outcomes.json")])
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["status"] == "NOT_CONFIGURED"
    assert payload["unsettled_exposure"] is None
    assert payload["open"] is None
    assert payload["positions"] is None


def test_an_unreadable_ledger_reports_null_exposure_and_the_reason(tmp_path, capsys):
    """Nought at risk and *unable to say what is at risk* must not render alike.

    This is the ledger equivalent of the breaker reading an unsettled position as zero
    profit: the number that would reassure is exactly the one that was not established.
    """

    path = tmp_path / "outcomes.json"
    path.write_text("{ this is not json", encoding="utf-8")

    code = positions.main(["--json", "--ledger", str(path)])
    payload = json.loads(capsys.readouterr().out)

    assert code == 2
    assert payload["status"] == "UNREADABLE"
    assert payload["reason"]
    assert payload["unsettled_exposure"] is None
    assert payload["positions"] is None


def test_applying_with_no_configured_lane_is_not_configured_rather_than_applied(
    tmp_path, capsys
):
    """Settled outcomes reaching no breaker at all is the thing this must never hide.

    An `applications: []` beside a successful status is a tidy summary of nothing having
    happened, which is how the return leg was decorative for as long as it was.
    """

    ledger = tmp_path / "outcomes.json"
    config = tmp_path / "reapers.json"
    config.write_text("{}", encoding="utf-8")

    code = positions.main(["--apply", "--json", "--ledger", str(ledger),
                           "--config", str(config)])
    payload = json.loads(capsys.readouterr().out)

    assert code == 2
    assert payload["status"] == "NOT_CONFIGURED"
    assert payload["applications"] is None
    assert "no configured lane" in payload["reason"]


def test_the_json_and_prose_renderings_of_a_ledger_exit_the_same_way(tmp_path, capsys):
    """One code path decides the code, so a UI cannot get a quieter answer than a person.

    The two renderings drifting is not hypothetical: they are separate branches with
    separate returns, and the JSON branch is the one written last and exercised least.
    """

    path = tmp_path / "outcomes.json"
    for argv in ([], ["--json"]):
        codes = []
        for state in ("{ broken", "[]"):
            path.write_text(state, encoding="utf-8")
            codes.append(positions.main([*argv, "--ledger", str(path)]))
            capsys.readouterr()
        assert codes == [2, 0], f"{argv or 'prose'} gave {codes}"


# --- a refusal keeps its reason in either rendering ----------------------------------

def test_settling_without_an_amount_is_refused_in_json_with_the_reason_intact(
    tmp_path, capsys
):
    """The prose refusal names what guessing zero would record. The JSON must too.

    A UI that gets a bare REFUSED renders a red box, and the operator's next move is to
    guess. The reason is the part that tells them the field is missing, not the record.
    """

    path = tmp_path / "outcomes.json"
    path.write_text("[]", encoding="utf-8")

    code = positions.main(["--json", "--settle", "POS-one", "--ledger", str(path)])
    payload = json.loads(capsys.readouterr().out)

    assert code == 2
    assert payload["status"] == "REFUSED"
    assert "--returned" in payload["reason"]
    assert payload["position"] is None


def test_an_unknown_without_a_note_is_refused_in_json_too(tmp_path, capsys):
    path = tmp_path / "outcomes.json"
    path.write_text("[]", encoding="utf-8")

    code = positions.main(["--json", "--unknown", "POS-one", "--ledger", str(path)])
    payload = json.loads(capsys.readouterr().out)

    assert code == 2
    assert payload["status"] == "REFUSED"
    assert "note" in payload["reason"]


# --- the reap payload ----------------------------------------------------------------

def _harvest(status_name: str = NOTHING_FOUND, **kw) -> Harvest:
    return Harvest(lane="arb", status=status_name, **kw)


def test_a_run_where_every_lane_failed_to_look_is_not_a_run_that_found_nothing():
    """COULD_NOT_LOOK and NOT_CONFIGURED are separate top-level statuses, not one nothing.

    `describe()` has always separated them in prose — "no lane was configured" against
    "no configured lane looked" — and a summarised JSON status is exactly where they get
    put back together. A scheduler reading the merged version treats a pipeline that did
    not run as a quiet market, every morning, indefinitely.
    """

    blind = Reaping(
        assemblies=(Assembly("arb", CONFIGURED),),
        harvests=(_harvest(COULD_NOT_LOOK, reason="no key in ~/.oddsapi"),),
    )
    unasked = Reaping(assemblies=(Assembly("arb", NOT_CONFIGURED),))

    assert blind.to_dict()["status"] == "COULD_NOT_LOOK"
    assert unasked.to_dict()["status"] == NOT_CONFIGURED
    assert blind.to_dict()["status"] != unasked.to_dict()["status"]


def test_a_run_that_reached_a_source_says_so_even_when_it_found_nothing():
    looked = Reaping(
        assemblies=(Assembly("arb", CONFIGURED),),
        harvests=(_harvest(NOTHING_FOUND, sources_asked=3, sources_answered=3),),
    )

    assert looked.to_dict()["status"] == "LOOKED"


def test_a_reap_that_placed_carries_the_placement_beside_the_harvest():
    """The one field behind which money has already moved is never inferred from harvests.

    A payload of READY harvests and no placements is what a UI renders as "NOTHING HAS
    BEEN PLACED" — which is what the prose says in exactly the case where nothing was.
    On a run that placed, the same shape is a false statement about real money.
    """

    reaping = Reaping(
        assemblies=(Assembly("stocks", CONFIGURED),),
        harvests=(Harvest(lane="stocks", status=READY, subject="ACME"),),
        placements=(Placement("stocks", PLACED, subject="ACME", position_id="POS-one",
                              client_order_id="abc", filled_quantity=3.0,
                              requested_quantity=3.0),),
    )

    payload = reaping.to_dict()

    assert len(payload["placements"]) == 1
    assert payload["placements"][0]["status"] == PLACED
    assert payload["placements"][0]["position_id"] == "POS-one"


def test_an_unresolved_placement_says_a_person_is_needed_without_deriving_it():
    """UNRESOLVED is the status that costs money to misread as "not placed".

    The order may exist. A caller filtering on `status == "PLACED"` to decide whether to
    submit concludes it did not go in and submits it again, which is the one mistake this
    lane can make twice with the same money.
    """

    payload = Placement("stocks", UNRESOLVED, subject="ACME", position_id="POS-one",
                        client_order_id="abc", requested_quantity=3.0,
                        reason="the broker returned 502").to_dict()

    assert payload["needs_a_person"] is True
    assert payload["filled_quantity"] is None
    assert payload["client_order_id"] == "abc"
    assert payload["reason"]


def test_a_harvest_with_no_register_says_nothing_looked_it_up():
    """Absent register and readable register that found nothing are different claims.

    A lane on a thirty-minute cadence re-offers the same standing arb every run. "Not
    seen before" from a register that was never attached is a manufactured novelty.
    """

    payload = Harvest(lane="arb", status=READY, subject="a v b").to_dict()

    assert payload["seen"]["status"] == "NO_REGISTER"
    assert payload["seen"]["reason"]


def test_a_lane_that_declared_no_sources_did_not_ask_and_get_silence():
    payload = _harvest(NOTHING_FOUND).to_dict()

    assert payload["sources"]["status"] == "NOT_DECLARED"
    assert payload["sources"]["asked"] is None
    assert payload["sources"]["answered"] is None


def test_a_working_decision_is_never_rendered_as_a_reviewed_one():
    """`board_convened` is carried as false rather than left out.

    The reapers reach READY without an audit chain, and the loss of that chain is the
    difference between a working decision and a reviewed one. A key a reader has to
    notice is missing is a key they will not notice is missing.
    """

    payload = Harvest(lane="arb", status=READY, subject="a v b").to_dict()

    assert payload["board_convened"] is False


def test_owner_operating_manually_still_reports_that_the_lane_researches():
    """Two permissions, two fields. Inferring one from the other gets this mode wrong.

    OWNER_OPERATING_MANUALLY looks, screens, gates and sizes; only the placing waits for
    a person. A UI collapsing it to "off" hides a lane that is running.
    """

    manual = Mode("arb", OWNER_OPERATING_MANUALLY, "data/MANUAL", "the switch is set")
    auto = Mode("stocks", AUTONOMOUS, "config", "autonomous_execution is true")

    assert manual.to_dict() == {
        "lane": "arb", "mode": OWNER_OPERATING_MANUALLY, "source": "data/MANUAL",
        "reason": "the switch is set", "may_reap": True, "may_place": False,
    }
    assert auto.to_dict()["may_place"] is True


def test_an_application_carries_what_was_withheld_from_the_breakers():
    """The skipped lists are the point of the type, and a count of applied hides them.

    An open position contributes nothing and a void is deliberately not applied. Both
    mean the breakers are working with less than the full picture, and a reader shown
    only "2 applied" has no way to know it.
    """

    payload = Application(
        "arb", applied=("POS-one", "POS-two"), skipped_unsettled=("POS-three",),
        skipped_void=("POS-four",), tripped_by="daily loss limit",
    ).to_dict()

    assert payload["skipped_unsettled"] == ["POS-three"]
    assert payload["skipped_void"] == ["POS-four"]
    assert payload["tripped_by"] == "daily loss limit"
    assert payload["self_clears"] is False


def test_an_unknown_reaper_lane_is_refused_identically_in_both_renderings(capsys):
    prose = run.reap("horses")
    capsys.readouterr()
    machine = run.reap("horses", as_json=True)
    payload = json.loads(capsys.readouterr().out)

    assert prose == machine == 2
    assert payload["status"] == "REFUSED"
    assert "horses" in payload["reason"]


def test_asking_for_json_does_not_quieten_a_run_that_looked_at_nothing(
    monkeypatch, capsys
):
    monkeypatch.setattr("lib.reaping.reap", lambda **_kw: Reaping())

    code = run.reap("arb", as_json=True)
    payload = json.loads(capsys.readouterr().out)

    assert code == 2
    assert payload["status"] == NOT_CONFIGURED
    assert payload["placements"] == []


def test_json_output_does_not_change_whether_the_lane_places(monkeypatch):
    """`--json` is a rendering. `--dry` is the flag that stops things being sent.

    Wiring them together would make a UI a quieter way to run a live lane, which is the
    kind of convenience that is discovered afterwards from a filled order.
    """

    asked: list[bool] = []

    def fake_reap(*, place=True, **_kw):
        asked.append(place)
        return Reaping()

    monkeypatch.setattr("lib.reaping.reap", fake_reap)

    run.reap("arb", as_json=True)
    run.reap("arb", dry=True, as_json=True)

    assert asked == [True, False]


# --- the version on the contract ------------------------------------------------------

def test_every_machine_readable_payload_carries_the_same_schema_version(
    tmp_path, monkeypatch, capsys
):
    """One constant, not four literals, or the four drift and each claims to be the truth."""

    monkeypatch.chdir(tmp_path)
    positions.main(["--json", "--ledger", str(tmp_path / "outcomes.json")])
    ledger_payload = json.loads(capsys.readouterr().out)

    assert ledger_payload["schema_version"] == SCHEMA_VERSION
    assert Reaping().to_dict()["schema_version"] == SCHEMA_VERSION
    assert status.as_json()["schema_version"] == SCHEMA_VERSION
