"""A flip is arbitrage-shaped and the exit is not contracted, which changes everything.

`docs/flipper-design.md` names the properties this file has to hold, and every one of them
is a defence against the same class of error: a number that looks like evidence and is not.

    an asking price is never used to size; only sold comparables are
    below the comparable floor the verdict is INDETERMINATE, not a wide estimate
    a margin is computed after fees, postage and the returns rate, never before
    an item with a wide comparable spread does not present as a point estimate
    n=3 and n=47 produce visibly different confidence in the output
    URGENT requires a margin materially above ROUTINE, so the tiers cannot collapse
    at physical capacity the lane reports AT_CAPACITY, not "nothing found"
    an unsold item past the write-down horizon stops counting at cost
    the lane is in NO_ADAPTER and never reaches a placer
    a source that could not be reached is COULD_NOT_LOOK, never "no deals today"

The first is the one the whole function turns on. A completed sale is a transaction that
happened; an active listing is somebody's hope. A flipper built on asking prices computes
margins against numbers nobody paid and produces confident, wrong, profitable-looking
suggestions all day — so the distinction is in the type rather than in a comment, and the
tests below try to get an asking price into a stake by every route the code allows.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from lib.flipper import (
    ASKING,
    CAPACITY,
    COMPARABLE_FLOOR,
    INDETERMINATE,
    MINIMUM_BUY,
    MINIMUM_TIER_GAP_PCT,
    NOT_WORTH_IT,
    PRICED,
    ROUTINE,
    ROUTINE_NET_PCT,
    SOLD,
    URGENT,
    URGENT_NET_PCT,
    WRITE_DOWN_DAYS,
    Comparable,
    FeeSchedule,
    Holding,
    ItemKey,
    book_value,
    break_even_sell,
    capacity_from,
    distribution,
    round_trip,
    tier,
)

NOW = datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc)


def key(grade="9", grader="PSA", title="Charizard Base Set Holo") -> ItemKey:
    return ItemKey(title=title, grade=grade, grader=grader,
                   qualifiers=("Base Set", "1999", "Unlimited"))


def sale(price: float, *, days_ago: int = 10, kind: str = SOLD, item: ItemKey | None = None,
         currency: str = "EUR") -> Comparable:
    return Comparable(
        key=item or key(), price=price, currency=currency, kind=kind,
        observed_at=(NOW - timedelta(days=days_ago)).isoformat(), source="test")


def fees(**overrides) -> FeeSchedule:
    settings = dict(commission_pct=13.25, fixed_fee=0.30, postage=5.0,
                    returns_rate_pct=3.0)
    settings.update(overrides)
    return FeeSchedule(**settings)


class TestAnAskingPriceNeverBecomesEvidence:
    def test_a_comparable_must_say_whether_anybody_paid_it(self):
        """No default on `kind`. SOLD by default would let an asking price become evidence
        by omission, which is the single failure the whole function is built to prevent."""

        with pytest.raises(TypeError):
            Comparable(key=key(), price=100.0, currency="EUR",
                       observed_at=NOW.isoformat())

    def test_an_invented_kind_is_refused(self):
        with pytest.raises(ValueError, match="somebody's hope"):
            Comparable(key=key(), price=100.0, currency="EUR", kind="LISTED",
                       observed_at=NOW.isoformat())

    def test_asking_prices_are_excluded_from_the_distribution_entirely(self):
        asking_only = [sale(500.0, kind=ASKING) for _ in range(20)]

        spread = distribution(key(), asking_only, now=NOW)

        assert spread.status == INDETERMINATE
        assert spread.count == 0
        assert spread.asking_seen == 20

    def test_the_refusal_says_the_asking_prices_were_discarded_and_why(self):
        """Silently dropping them would leave a person staring at a comparable count of
        nought beside a page full of listings."""

        spread = distribution(key(), [sale(500.0, kind=ASKING)], now=NOW)

        assert "which nobody paid" in spread.reason

    def test_asking_prices_never_move_the_numbers_that_are_sized_against(self):
        sold = [sale(300.0 + n) for n in range(COMPARABLE_FLOOR)]
        with_asking = sold + [sale(9_000.0, kind=ASKING) for _ in range(10)]

        assert (distribution(key(), sold, now=NOW).conservative
                == distribution(key(), with_asking, now=NOW).conservative)


class TestTheComparableFloor:
    def test_below_the_floor_the_verdict_is_indeterminate(self):
        """Not a low estimate and not a wide range. Unestablished."""

        spread = distribution(key(), [sale(300.0) for _ in range(COMPARABLE_FLOOR - 1)],
                              now=NOW)

        assert spread.status == INDETERMINATE
        assert spread.median is None
        assert "has not been established" in spread.describe()

    def test_at_the_floor_it_prices(self):
        spread = distribution(key(), [sale(300.0 + n) for n in range(COMPARABLE_FLOOR)],
                              now=NOW)

        assert spread.status == PRICED

    def test_a_comparable_at_a_different_grade_is_a_different_item(self):
        """The same card raw and at PSA 10 can differ by fifty times, so a comparable that
        does not match on grade is not a comparable — it is a different item with the same
        name."""

        wrong_grade = [sale(300.0, item=key(grade="10")) for _ in range(20)]

        assert distribution(key(grade="9"), wrong_grade, now=NOW).status == INDETERMINATE

    def test_a_comparable_from_a_different_grader_is_a_different_item(self):
        """Grade inflation between graders is a live argument in trading cards — a CGC 9.5
        and a PSA 10 are not the same item, which is exactly why the floor requires both."""

        wrong_grader = [sale(300.0, item=key(grader="CGC")) for _ in range(20)]

        assert distribution(key(grader="PSA"), wrong_grader, now=NOW).status == (
            INDETERMINATE)

    def test_sales_outside_the_window_are_discarded_and_the_reason_is_stated(self):
        """Cards bubbled through 2020-22 and corrected, so a sale from 2021 is a different
        market rather than an old data point."""

        old = [sale(300.0, days_ago=200) for _ in range(20)]

        spread = distribution(key(), old, now=NOW)

        assert spread.status == INDETERMINATE
        assert "a different market" in spread.reason

    def test_a_sale_in_another_currency_is_not_converted(self):
        """There is no FX rate in this repository and a rate is itself a price that goes
        stale, so a converted comparable would be a guess wearing a number."""

        dollars = [sale(300.0, currency="USD") for _ in range(20)]

        spread = distribution(key(), dollars, now=NOW, currency="EUR")

        assert spread.status == INDETERMINATE
        assert "no rate here that is not itself a stale price" in spread.reason


class TestADistributionIsNeverAPointEstimate:
    def _spread(self, prices):
        return distribution(key(), [sale(p) for p in prices], now=NOW)

    def test_n_equals_five_and_n_equals_fifty_read_differently(self):
        """`n=3 over 90 days` and `n=47 over 14 days` are different facts and must not both
        render as "sells for 120"."""

        few = self._spread([300.0 + n for n in range(5)])
        many = self._spread([300.0 + n for n in range(50)])

        assert "5 sale(s)" in few.describe()
        assert "50 sale(s)" in many.describe()

    def test_two_sets_with_the_same_median_report_different_spreads(self):
        """100/104 and 40/200 have the same middle and are not the same evidence."""

        tight = self._spread([100.0, 101.0, 102.0, 103.0, 104.0])
        wide = self._spread([40.0, 60.0, 102.0, 150.0, 200.0])

        assert tight.median == wide.median
        assert wide.spread_pct > tight.spread_pct

    def test_sizing_uses_the_conservative_end_rather_than_the_median(self):
        """The median is what a typical seller got, and assuming this sale will be typical
        is a forecast. The direction to be wrong in is the one that refuses a marginal item
        rather than the one that buys it."""

        spread = self._spread([100.0, 150.0, 200.0, 250.0, 300.0])

        assert spread.conservative < spread.median

    def test_with_fewer_than_four_sales_the_lowest_is_used(self):
        """A quartile of three numbers is an arithmetic exercise rather than a
        measurement."""

        spread = distribution(key(), [sale(p) for p in (100.0, 200.0, 300.0)],
                              now=NOW, floor=3)

        assert spread.conservative == 100.0

    def test_the_description_always_carries_count_window_and_spread(self):
        printed = self._spread([300.0 + n for n in range(6)]).describe()

        assert "sale(s) in 90 days" in printed
        assert "median" in printed and "spread" in printed


class TestFeesBeforeMarginAlways:
    def test_the_round_trip_itemises_every_deduction(self):
        """A single net figure with the fees folded in is the shape that lets somebody
        sanity-check a wrong number and fail to."""

        printed = round_trip(200.0, 300.0, fees()).describe()

        for line in ("commission", "fixed fee", "processing", "postage",
                     "returns allowance"):
            assert line in printed

    def test_the_margin_is_net_and_is_taken_against_the_buy(self):
        trip = round_trip(200.0, 300.0, fees())

        assert trip.net_profit < 300.0 - 200.0
        assert trip.net_margin_pct == pytest.approx(trip.net_profit / 200.0 * 100.0)

    def test_the_platform_takes_its_cut_of_the_postage_the_buyer_paid(self):
        """How eBay actually charges, and the half people forget."""

        without = round_trip(200.0, 300.0, fees(postage_charged=0.0))
        with_postage = round_trip(200.0, 300.0, fees(postage_charged=6.0))

        assert with_postage.commission > without.commission

    def test_a_returns_rate_is_charged_on_the_whole_round_trip(self):
        """A returned item costs the postage both ways and usually cannot be relisted at
        the same price, so it is not a haircut on the fee."""

        none = round_trip(200.0, 300.0, fees(returns_rate_pct=0.0))
        some = round_trip(200.0, 300.0, fees(returns_rate_pct=5.0))

        assert some.returns_cost > (some.commission * 0.05)
        assert some.net_profit < none.net_profit

    def test_a_fee_schedule_with_no_commission_is_refused(self):
        """Every threshold in the lane moves with the real rate, so an unset one must
        refuse rather than flatter every margin."""

        with pytest.raises(ValueError, match="read off an account"):
            FeeSchedule(commission_pct=0.0, fixed_fee=0.30)

    def test_a_small_item_needs_a_bigger_markup_merely_to_break_even(self):
        """The arithmetic that inverted the original tiering and produced the 75 floor:
        postage and the fixed fee do not scale down."""

        small = break_even_sell(40.0, fees()) / 40.0 - 1.0
        large = break_even_sell(200.0, fees()) / 200.0 - 1.0

        assert small > large
        assert small > 0.30   # a 40 EUR item needs about a third on merely to stand still

    def test_the_floor_is_where_a_realistic_markup_starts_working(self):
        """Sanity on MINIMUM_BUY itself rather than on a number copied beside it."""

        needed = break_even_sell(MINIMUM_BUY, fees()) / MINIMUM_BUY - 1.0

        assert 0.20 < needed < 0.35


class TestTheTiersCannotCollapseIntoEachOther:
    def test_urgent_is_materially_above_routine(self):
        """The failure to design against is tier inflation: if routine finds arrive often
        they are read as noise, and the day an urgent one arrives it is skimmed with them.
        This asserts the gap so the two cannot be tuned together into one."""

        assert URGENT_NET_PCT - ROUTINE_NET_PCT >= MINIMUM_TIER_GAP_PCT

    def test_the_thresholds_are_net_rather_than_markup(self):
        """A markup that has not had fees taken out of it is the number that made the
        original 40 EUR tier look viable when it lost money. Asserted through the
        arithmetic: a 40% markup does NOT reach the 30% routine threshold."""

        trip = round_trip(200.0, 280.0, fees())

        assert (280.0 / 200.0 - 1.0) * 100 == pytest.approx(40.0)
        assert trip.net_margin_pct < ROUTINE_NET_PCT
        assert tier(trip.net_margin_pct) == NOT_WORTH_IT

    def test_each_tier_is_reached_at_its_own_threshold(self):
        assert tier(URGENT_NET_PCT) == URGENT
        assert tier(ROUTINE_NET_PCT) == ROUTINE
        assert tier(ROUTINE_NET_PCT - 0.1) == NOT_WORTH_IT

    def test_the_tier_is_a_property_of_the_opportunity(self):
        """Not a notification setting, so the same item carries the same urgency wherever
        it is read."""

        assert tier(60.0) == tier(60.0) == URGENT


class TestCapacityAndTheWriteDown:
    def _held(self, count: int, *, days_ago: int = 5):
        return [Holding(key=f"item-{n}", cost=100.0,
                        bought_at=(NOW - timedelta(days=days_ago)).isoformat())
                for n in range(count)]

    def test_a_full_shelf_is_at_capacity_rather_than_nothing_found(self):
        """A full shelf is a different fact from a quiet market and leads somewhere else:
        the next thing to do is sell something, not look harder."""

        shelf = capacity_from(self._held(CAPACITY), now=NOW)

        assert shelf.full is True
        assert "AT_CAPACITY" in shelf.describe()
        assert "not a finding that there is nothing to buy" in shelf.describe()

    def test_a_sold_item_frees_a_slot(self):
        held = self._held(3)
        held[0] = Holding(key="sold", cost=100.0, bought_at=held[0].bought_at,
                          sold_at=NOW.isoformat())

        assert capacity_from(held, now=NOW).held == 2

    def test_a_written_down_item_still_occupies_the_shelf(self):
        """The write-down is about what the book says it is worth, not about where the
        item is — it is still physically in the hallway."""

        stale = self._held(2, days_ago=WRITE_DOWN_DAYS + 10)

        shelf = capacity_from(stale, now=NOW)

        assert shelf.held == 2
        assert shelf.written_down == 2
        assert "no longer counted at cost" in shelf.describe()

    def test_an_unsold_item_past_the_horizon_stops_counting_at_cost(self):
        """An item nobody bid on for fifty days is not worth what was paid for it, and
        carrying it at cost overstates the book."""

        fresh = self._held(1, days_ago=5)
        stale = self._held(1, days_ago=WRITE_DOWN_DAYS + 1)

        carried, written = book_value(fresh + stale, now=NOW)

        assert carried == 100.0
        assert written == 100.0

    def test_an_item_with_an_unreadable_purchase_date_is_written_down(self):
        """The direction that understates the book is the one to be wrong in."""

        assert Holding(key="x", cost=100.0, bought_at="last summer").written_down(NOW)

    def test_a_sold_item_is_never_written_down(self):
        sold = Holding(key="x", cost=100.0,
                       bought_at=(NOW - timedelta(days=400)).isoformat(),
                       sold_at=NOW.isoformat())

        assert sold.written_down(NOW) is False


class TestTheItemKeyIsTheIdentity:
    def test_a_grade_is_required(self):
        with pytest.raises(ValueError, match="part of the identity"):
            ItemKey(title="Charizard", grade="", grader="PSA")

    def test_an_unrecognised_grader_is_refused(self):
        """An unrecognised grader's number cannot be matched against anything, so the item
        is not machine-identifiable — which is the axis the whole scope was chosen on."""

        with pytest.raises(ValueError, match="not a grader this lane recognises"):
            ItemKey(title="Charizard", grade="9", grader="MyMate")

    def test_the_grader_is_normalised_but_the_grade_is_not(self):
        assert ItemKey(title="x", grade="9.5", grader="cgc").grader == "CGC"
        assert ItemKey(title="x", grade="9.5", grader="CGC").grade == "9.5"

    def test_the_cert_number_is_not_part_of_matching(self):
        """A cert identifies one physical slab, and two slabs of the same card at the same
        grade are exactly what a comparable set is made of."""

        one = ItemKey(title="x", grade="9", grader="PSA", cert="12345")
        other = ItemKey(title="x", grade="9", grader="PSA", cert="67890")

        assert one.matches(other)

    def test_qualifiers_are_part_of_matching(self):
        base = ItemKey(title="x", grade="9", grader="PSA", qualifiers=("1999",))
        reprint = ItemKey(title="x", grade="9", grader="PSA", qualifiers=("2002",))

        assert not base.matches(reprint)
