"""A lane that can read its evidence is not a lane that has concluded anything.

Two separations are load-bearing here, and both are the recurring defect in a new place.

`NOT_CONFIGURED` against `UNREACHABLE`: a missing key and a dead endpoint need opposite
responses from a person, and a preflight that merged them would send them to the wrong one.

`READY` against `DEGRADED`: arbitrage runs perfectly well with no credentials -- you type
odds off two screens -- but a live scan reaching nought of five books and reporting "no arb"
is the most expensive sentence this repository can produce. The code is fine. The system is
blind. Calling that READY would be true about the first and false about the second.
"""
from __future__ import annotations

import pytest

from lib.preflight import (
    BLOCKED,
    CONFIGURED,
    DEGRADED,
    NOT_ATTEMPTED,
    NOT_CONFIGURED,
    READY,
    UNREACHABLE,
    LaneReadiness,
    Requirement,
    arb_lane,
    crypto_lane,
    report,
    stocks_lane,
)


def requirement(status, *, required=True):
    return Requirement("test", "thing", status, unlocks="something", required=required)


class TestMissingIsNotBroken:
    def test_an_absent_credential_is_not_an_unreachable_endpoint(self):
        assert NOT_CONFIGURED != UNREACHABLE

    def test_crypto_without_a_url_is_not_configured_rather_than_unreachable(self):
        """Nothing was contacted, so nothing can be said about whether it answers."""

        lane = crypto_lane(environ={})

        assert lane.requirements[0].status == NOT_CONFIGURED

    def test_crypto_without_a_url_is_blocked(self):
        assert crypto_lane(environ={}).status == BLOCKED

    def test_an_unprobed_url_is_configured_not_ready(self):
        lane = crypto_lane(environ={"QUICKNODE_ETHEREUM_URL": "https://example/abc123"})

        assert lane.requirements[0].status == CONFIGURED
        assert lane.status == READY


class TestSecretsAreNotEchoed:
    def test_the_node_url_never_appears_in_the_report(self):
        """It carries an auth token in its path. That is why it is in an env var."""

        secret = "https://snowy-frog.quiknode.pro/deadbeefcafe/"

        text = report([crypto_lane(environ={"QUICKNODE_ETHEREUM_URL": secret})])

        assert secret not in text
        assert "deadbeefcafe" not in text


class TestDegradedIsItsOwnAnswer:
    def test_an_optional_gap_degrades_rather_than_blocks(self):
        lane = LaneReadiness("x", "", (requirement(NOT_CONFIGURED, required=False),))

        assert lane.status == DEGRADED

    def test_a_required_gap_blocks(self):
        lane = LaneReadiness("x", "", (requirement(NOT_CONFIGURED),))

        assert lane.status == BLOCKED

    def test_blocked_beats_degraded_when_both_are_present(self):
        lane = LaneReadiness("x", "", (
            requirement(NOT_CONFIGURED, required=False), requirement(NOT_CONFIGURED),
        ))

        assert lane.status == BLOCKED

    def test_arb_with_no_credentials_is_degraded_not_blocked(self, tmp_path):
        """It still does the maths honestly. It just cannot see any prices."""

        assert arb_lane(home=tmp_path).status == DEGRADED

    def test_arb_says_how_many_sources_it_actually_reaches(self, tmp_path):
        lane = arb_lane(home=tmp_path)

        assert f"0 of {len(lane.requirements)} sources" in lane.summary


class TestBetfairKeyKindMustBeDeclared:
    def _betfair(self, tmp_path, *markers):
        root = tmp_path / ".betfair"
        root.mkdir()
        (root / "app_key").write_text("key", encoding="utf-8")
        for marker in markers:
            (root / marker).write_text("", encoding="utf-8")
        # By name, not by index: a new source added ahead of Betfair must not silently
        # repoint these assertions at a different requirement.
        return next(r for r in arb_lane(home=tmp_path).requirements
                    if r.name == "Betfair Exchange")

    def test_a_key_with_no_declared_kind_does_not_count_as_configured(self, tmp_path):
        """A delayed quote read as a live one is a price you cannot trade at."""

        found = self._betfair(tmp_path)

        assert found.status == NOT_CONFIGURED
        assert "undeclared" in found.detail

    def test_a_key_declared_both_ways_does_not_count_either(self, tmp_path):
        assert self._betfair(tmp_path, "delayed", "live").status == NOT_CONFIGURED

    def test_a_key_with_exactly_one_marker_counts_and_names_the_kind(self, tmp_path):
        found = self._betfair(tmp_path, "delayed")

        assert found.status == NOT_ATTEMPTED
        assert "delayed" in found.detail

    def test_presence_is_not_reported_as_a_successful_login(self, tmp_path):
        """Nothing authenticated. Smarkets caps logins at five per five minutes."""

        assert self._betfair(tmp_path, "live").status != READY


class TestStocksNeedsNoKey:
    def test_edgar_is_configured_without_any_credential(self):
        assert stocks_lane().requirements[0].status == CONFIGURED

    def test_the_stocks_lane_is_ready_out_of_the_box(self):
        assert stocks_lane().status == READY


class TestTheReportDoesNotOverclaim:
    def test_ready_is_stated_to_mean_retrieval_and_not_a_decision(self):
        text = report([stocks_lane()])

        assert "does NOT mean" in text
        assert "a board has been convened" in text

    def test_an_unmet_requirement_carries_a_remedy(self):
        found = crypto_lane(environ={}).requirements[0]

        assert "QUICKNODE_ETHEREUM_URL" in found.describe()
