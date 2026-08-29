"""The flipper lane must stop where the evidence stops, and say which kind of stop it is.

`tests/test_flipper.py` holds the arithmetic. This holds the lane, and the properties here
are the ones `docs/flipper-design.md` names about the lane rather than about the numbers:

    at physical capacity the lane reports AT_CAPACITY, not "nothing found"
    a source that could not be reached is COULD_NOT_LOOK, never "no deals today"
    the lane is in NO_ADAPTER and never reaches a placer
    below the comparable floor the harvest is INDETERMINATE, not REFUSED

The last is the one worth reading twice. "Too few sales to know what this resells for" and
"I worked it out and it is not worth buying" are different facts and lead a person to
different places — one to typing in five more completed sales, one to moving on. A lane
that reported both as REFUSED would quietly make the first look like the second, and the
first is the commonest honest answer this lane has while the eBay sold-data question is
open.

The authorisation property is here too. An arb's standing grant is defensible because the
position makes no claim about the fixture; a flip claims the item is underpriced and will
resell, so the grant is BOUNDED at a figure and a person writes their own thesis above it.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from lib.flipper import (
    SOLD,
    URGENT,
    Capacity,
    Comparable,
    FeeSchedule,
    Holding,
    ItemKey,
    capacity_from,
)
from lib.flipper_reaper import (
    MAXIMUM_SPREAD_PCT,
    BoundedAuthority,
    BuySuggestion,
    Listing,
    build_flipper_reaper,
    flipper_identity,
    gates_for,
    measure_suggestion,
    opportunities_from,
    screen_opportunity,
    size_opportunity,
)
from lib.candidates import INDETERMINATE, REFUSED
from lib.reaper import COULD_NOT_LOOK, READY, Unworthy
from lib.reaper import INDETERMINATE as HARVEST_INDETERMINATE
from lib.reaper import REFUSED as HARVEST_REFUSED

NOW = datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc)


def key(grade="9") -> ItemKey:
    return ItemKey(title="Charizard Base Set Holo", grade=grade, grader="PSA",
                   qualifiers=("Base Set", "1999", "Unlimited"))


def listing(price: float = 200.0) -> Listing:
    return Listing(key=key(), price=price, currency="EUR", source="eBay",
                   url="https://example.invalid/itm/1")


def fees(**overrides) -> FeeSchedule:
    settings = dict(commission_pct=13.25, fixed_fee=0.30, postage=5.0,
                    returns_rate_pct=3.0)
    settings.update(overrides)
    return FeeSchedule(**settings)


class Source:
    """A comparable source that answers with whatever it was given."""

    name = "test"

    def __init__(self, prices, *, days_ago=10, item=None, status="READ"):
        self.prices = prices
        self.days_ago = days_ago
        self.item = item
        self.status = status

    def sold_for(self, wanted):
        from connectors.ebay import SoldLookup

        if self.status != "READ":
            return SoldLookup(self.status, wanted.key, source=self.name,
                              reason="no credentials")
        return SoldLookup("READ", wanted.key, tuple(
            Comparable(key=self.item or wanted, price=price, currency="EUR", kind=SOLD,
                       observed_at=(NOW - timedelta(days=self.days_ago)).isoformat(),
                       source=self.name)
            for price in self.prices), self.name, NOW.isoformat())


def authority(**overrides) -> BoundedAuthority:
    settings = dict(
        declared_by="Ian McGuane",
        reasoning="graded items have an exact identity and a comparable set",
        considered=("the exit is not contracted",),
        expires_at=(NOW + timedelta(days=90)).isoformat(),
        per_item_ceiling=250.0, max_exposure=200.0)
    settings.update(overrides)
    return BoundedAuthority(**settings)


def opportunity(*, prices=(400.0, 410.0, 420.0, 430.0, 440.0), price=200.0,
                held=0, days_ago=10, item=None, status="READ"):
    return opportunities_from(
        [listing(price)], sources=[Source(prices, days_ago=days_ago, item=item,
                                          status=status)],
        fees=fees(),
        capacity=capacity_from([Holding(key=f"h{n}", cost=100.0,
                                        bought_at=(NOW - timedelta(days=1)).isoformat())
                                for n in range(held)], now=NOW),
        now=NOW)[0]


class TestTooFewSalesIsNotARefusal:
    def test_below_the_floor_the_cascade_is_indeterminate(self):
        """"Too few sales to know" and "I worked it out and it is not worth it" lead a
        person to different places — one to typing in five more completed sales, one to
        moving on."""

        screened = screen_opportunity(opportunity(prices=(400.0, 410.0)))

        assert screened.verdict == INDETERMINATE
        assert screened.decided_by.name == "there are enough sold comparables"
        assert "NOT a low estimate" in screened.decided_by.detail

    def test_below_the_floor_the_sizer_returns_none_rather_than_unworthy(self):
        """None is a constraint that could not be MEASURED, which the reaper reports as
        INDETERMINATE. `Unworthy` would say it was measured and came out badly."""

        sized = size_opportunity(opportunity(prices=(400.0, 410.0)),
                                 ring_fence_limit=250.0)

        assert sized is None

    def test_a_thin_margin_returns_unworthy_rather_than_none(self):
        """The other side of the same distinction: this WAS measured."""

        sized = size_opportunity(opportunity(prices=(230.0,) * 6), ring_fence_limit=250.0)

        assert isinstance(sized, Unworthy)
        assert "net on the buy" in sized.reason


class TestAtCapacityIsNotNothingFound:
    def test_a_full_shelf_refuses_by_name_in_the_cascade(self):
        screened = screen_opportunity(opportunity(held=20))

        assert screened.verdict == REFUSED
        assert screened.decided_by.name == "there is capacity"
        assert "AT_CAPACITY" in screened.decided_by.detail

    def test_a_full_shelf_also_blocks_at_the_gates(self):
        """Twice, on purpose: the cascade decides whether to surface and the gates decide
        whether the thesis may authorise. A shelf that stopped one and not the other is a
        hole exactly the width of whichever check somebody remembered to run."""

        readings = gates_for(opportunity(held=20), per_item_thesis_above=250.0)

        assert any(r.status == "AT_CAPACITY" and r.blocking for r in readings)

    def test_the_sizer_refuses_at_capacity_with_the_shelf_count(self):
        sized = size_opportunity(opportunity(held=20), ring_fence_limit=250.0)

        assert isinstance(sized, Unworthy)
        assert "20 of 20" in sized.reason


class TestTheAuthorisationIsBounded:
    def test_an_item_above_the_ceiling_needs_its_own_thesis(self):
        """An arb's standing grant is defensible because the position makes no claim about
        the fixture. A flip claims the item is underpriced and will resell, so an unbounded
        grant would authorise that judgement in advance for every item forever."""

        readings = gates_for(opportunity(price=400.0), per_item_thesis_above=250.0)

        blocking = [r for r in readings if r.status == "PER_ITEM_THESIS_REQUIRED"]
        assert blocking and blocking[0].blocking
        assert "look at it themselves before money moves" in blocking[0].detail

    def test_a_written_thesis_closes_it(self):
        found = opportunity(price=400.0)

        readings = gates_for(found, per_item_thesis_above=250.0,
                             theses={found.subject: "I know this card"})

        assert not any(r.status == "PER_ITEM_THESIS_REQUIRED" for r in readings)

    def test_an_item_under_the_ceiling_runs_on_the_standing_grant(self):
        readings = gates_for(opportunity(price=200.0), per_item_thesis_above=250.0)

        assert not any(r.status == "PER_ITEM_THESIS_REQUIRED" for r in readings)

    def test_a_ceiling_of_nought_is_refused_as_not_a_standing_grant(self):
        with pytest.raises(ValueError, match="not what a standing grant is for"):
            authority(per_item_ceiling=0.0)

    def test_a_standing_grant_cannot_be_held_by_automation(self):
        with pytest.raises(ValueError, match="cannot hold a standing authority"):
            authority(declared_by="agent:sourcing")

    def test_the_minted_thesis_says_the_position_rests_on_a_claim(self):
        thesis = authority().thesis_for("a card at 200.00 EUR")

        considered = " ".join(thesis.considered)
        assert "DOES rest on a claim" in considered
        assert "Above the ceiling a person writes their own thesis" in considered


class TestTheWideSpreadRefusal:
    def test_a_spread_wider_than_the_limit_is_refused_rather_than_averaged(self):
        """A spread that wide usually means the key is catching two different things — a
        reprint, another parallel, a damaged slab — rather than one item with a volatile
        price."""

        screened = screen_opportunity(
            opportunity(prices=(100.0, 150.0, 300.0, 600.0, 900.0)))

        assert screened.verdict == REFUSED
        assert screened.decided_by.name == "the exit is a distribution"
        assert "Narrow the key rather than averaging across it" in (
            screened.decided_by.detail)

    def test_a_tight_spread_passes_and_states_the_shape(self):
        screened = screen_opportunity(opportunity())

        stage = next(s for s in screened.stages if s.name == "the exit is a distribution")
        assert "n=5" in stage.detail
        assert "not the median" in stage.detail

    def test_the_limit_is_wide_enough_for_a_real_card_market(self):
        """Guarded so a future tightening has to argue with a number rather than just
        pass: graded card prices genuinely move, and a limit that refused everything would
        be a lane nobody runs."""

        assert MAXIMUM_SPREAD_PCT >= 100.0


class TestTheSuggestion:
    def test_a_suggestion_carries_the_distribution_rather_than_a_price(self):
        suggestion = size_opportunity(opportunity(), ring_fence_limit=250.0)

        printed = suggestion.describe()
        assert "What comparable items ACTUALLY SOLD FOR" in printed
        assert "sale(s) in 90 days" in printed
        assert "THE EXIT IS NOT CONTRACTED" in printed

    def test_an_urgent_suggestion_says_urgent_is_meant_to_be_rare(self):
        """Tier inflation is the failure to design against: if these arrive often the
        thresholds are wrong rather than the market being generous."""

        suggestion = size_opportunity(
            opportunity(prices=(600.0, 610.0, 620.0, 630.0, 640.0)),
            ring_fence_limit=250.0)

        assert suggestion.tier == URGENT
        assert "meant to be rare" in suggestion.describe()

    def test_an_item_over_the_ring_fence_is_refused_on_size_not_on_merit(self):
        sized = size_opportunity(opportunity(price=240.0), ring_fence_limit=100.0)

        assert isinstance(sized, Unworthy)
        assert "The item is not the problem; the size is" in sized.reason

    def test_the_breakers_get_the_outlay_and_the_claimed_margin(self):
        suggestion = size_opportunity(opportunity(), ring_fence_limit=250.0)

        outlay, margin = measure_suggestion(suggestion)

        assert outlay == suggestion.buy
        assert margin == suggestion.trip.net_margin_pct

    def test_identity_excludes_the_asking_price(self):
        """Including it makes every relist a new sighting and the register dedupes nothing
        while appearing to work."""

        cheap = opportunity(price=200.0)
        dear = opportunity(price=240.0)

        assert flipper_identity(cheap) == flipper_identity(dear)
        assert "200" not in flipper_identity(cheap)

    def test_identity_separates_the_same_card_on_two_sites(self):
        one = opportunity()
        other = opportunities_from(
            [Listing(key=key(), price=200.0, currency="EUR", source="DoneDeal")],
            sources=[Source((400.0,) * 5)], fees=fees(), capacity=Capacity(0), now=NOW)[0]

        assert flipper_identity(one) != flipper_identity(other)


class TestTheLaneEndToEnd:
    class _Breakers:
        class _Verdict:
            verdict = "PERMITTED"
            blocked_by = ()

        def check(self, **_kw):
            return self._Verdict()

    def _reaper(self, **overrides):
        settings = dict(
            authority=authority(), breakers=self._Breakers(), fees=fees(),
            ring_fence_limit=250.0, sources=[Source((400.0, 410.0, 420.0, 430.0, 440.0))],
            listings=lambda: ([listing()], 1, 1), holdings=lambda: (),
            now=lambda: NOW)
        settings.update(overrides)
        return build_flipper_reaper(**settings)

    def test_no_listing_source_is_could_not_look(self):
        """A lane with no source reporting "no deals today" is the exact confusion the
        status set exists to prevent, and it is the likeliest state of this lane for a
        while."""

        harvests = self._reaper(listings=None).reap()

        assert harvests[0].status == COULD_NOT_LOOK
        assert "not a finding that there is nothing worth buying" in harvests[0].reason

    def test_a_silent_comparable_source_is_reported_without_blocking(self):
        """Too few comparables already blocks in the cascade. This says WHY the count is
        low, which is a different and more useful thing to read."""

        readings = gates_for(opportunity(status="NOT_CONFIGURED"),
                             per_item_thesis_above=250.0)

        silent = [r for r in readings if r.status == "COMPARABLE_SOURCE_SILENT"]
        assert silent and not silent[0].blocking

    def test_a_priced_item_with_a_real_margin_reaches_ready(self):
        harvests = self._reaper().reap()

        assert [h.status for h in harvests] == [READY]
        assert isinstance(harvests[0].instruction, BuySuggestion)

    def test_too_few_comparables_reaches_indeterminate_rather_than_refused(self):
        harvests = self._reaper(sources=[Source((400.0, 410.0))]).reap()

        assert harvests[0].status == HARVEST_INDETERMINATE

    def test_a_full_shelf_reaches_refused_naming_the_shelf(self):
        full = [Holding(key=f"h{n}", cost=100.0, bought_at=NOW.isoformat())
                for n in range(20)]

        harvests = self._reaper(holdings=lambda: full).reap()

        assert harvests[0].status == HARVEST_REFUSED
        assert "capacity" in harvests[0].reason.lower()

    def test_the_lane_can_never_reach_a_placer(self):
        """eBay takes no automated purchase worth relying on, and Facebook Marketplace and
        DoneDeal have no public API at all. That is not a missing adapter, exactly as
        bookmakers not taking a program's order is not one for arb."""

        from lib.placing import NO_ADAPTER, PLACERS

        assert "flipper" in NO_ADAPTER
        assert "flipper" not in PLACERS
        assert "no automated purchase" in NO_ADAPTER["flipper"]

    def test_no_scraper_was_written_for_the_sources_that_forbid_one(self):
        """docs/flipper-design.md refuses this by name and the refusal has to be checkable,
        because it is the kind of thing that gets added later by somebody who did not read
        the document."""

        from pathlib import Path

        for name in ("lib/flipper.py", "lib/flipper_reaper.py", "lib/ebay_config.py",
                     "connectors/ebay.py"):
            source = Path(name).read_text(encoding="utf-8").lower()
            assert "facebook.com" not in source
            assert "donedeal" not in source or "no public api" in source


class TestTheLaneIsRegistered:
    def test_it_is_in_the_running_lanes_with_its_own_currency(self):
        from lib.reaping import LANE_CURRENCY, LANES

        assert "flipper" in LANES
        assert LANE_CURRENCY["flipper"] == "EUR"

    def test_it_is_scheduled_at_the_cadence_an_opportunity_disappears_at(self):
        """The only cadence here set by how fast an OPPORTUNITY goes rather than how fast
        the evidence changes: a severely underpriced graded card is gone in minutes."""

        import run

        assert run.REAP_CADENCES["flipper"] <= 6 * 3600

    def test_it_refuses_to_assemble_without_a_real_fee_schedule(self, tmp_path):
        """Every floor and threshold moves with the rate, and reading it off a published
        card rather than the account is how a margin becomes fiction."""

        from lib.reaping import REFUSED, assemble_flipper

        assembled = assemble_flipper(
            {"enabled": True, "balance": 1000.0, "authority": {
                "declared_by": "Ian McGuane", "reasoning": "x", "considered": [],
                "expires_at": "2099-01-01T00:00:00Z", "per_item_ceiling": 250.0,
                "max_exposure": 200.0}},
            directory=tmp_path, kill_switch=tmp_path / "HALT")

        assert assembled.status == REFUSED
        assert "flatters every margin" in assembled.reason

    def test_it_refuses_to_assemble_without_an_authority(self, tmp_path):
        from lib.reaping import REFUSED, assemble_flipper

        assembled = assemble_flipper(
            {"enabled": True, "balance": 1000.0, "fees": {"commission_pct": 13.0,
                                                          "fixed_fee": 0.3}},
            directory=tmp_path, kill_switch=tmp_path / "HALT")

        assert assembled.status == REFUSED
        assert "underpriced and will resell" in assembled.reason
