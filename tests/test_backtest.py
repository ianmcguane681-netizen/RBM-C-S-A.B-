"""A backtest that cannot come back negative is not a measurement.

Every property here guards a way of accidentally inventing an edge, and the ones worth the
file are the ones that would be invisible in review.

**Look-ahead is prevented by absence.** The engine hands a strategy `bars[:i+1]` and
executes at `bars[i+1].open`, so a rule cannot read the bar it trades on — not because it
is forbidden to, but because the bar is not in the object it was given. The offending line
in a look-ahead bug looks exactly like the correct one, which is why this is structural.

**An unresolvable bar resolves against the trader.** When one candle reaches both the stop
and the target, no ordering is knowable; the stop is taken and the trade is counted as
ambiguous, so a reader can see when a result rests on that convention.

**Too few trades is a state, not a bad result.** A 75% win rate over four trades is noise
with a percentage sign, and reporting it as a finding is how a backtest becomes a story.

**An error is not an empty market.** Kraken puts failures in a JSON array beside a
well-formed empty result — the exact shape that reads as "no trading happened" to a client
checking only the status code.
"""
from __future__ import annotations

import json
import io
from dataclasses import dataclass
from typing import Sequence

import pytest

from connectors.kraken import (
    COULD_NOT_LOOK,
    NOT_ENOUGH_HISTORY,
    READ,
    Bar,
    read_ohlc,
)
from lib.backtest import (
    FLAT,
    INSUFFICIENT_EVIDENCE,
    LONG,
    MEASURED,
    STOP,
    atr,
    buy_and_hold_windows,
    run,
    split,
)
from lib.backtest import COULD_NOT_LOOK as BT_COULD_NOT_LOOK


def bars(closes, *, high_pad=1.0, low_pad=1.0, start_ts=1_700_000_000):
    """A clean daily series. Highs and lows padded so nothing accidentally triggers."""

    return tuple(
        Bar(start_ts + i * 86400, c, c + high_pad, c - low_pad, c, 100.0)
        for i, c in enumerate(closes)
    )


@dataclass(frozen=True, slots=True)
class AlwaysLong:
    """Enters on every bar it is asked about, so the engine's mechanics are what is tested."""

    stop_atr: float = 1.0
    target_atr: float = 2.0
    warmup: int = 20
    name: str = "always-long"
    philosophy: str = "a test fixture, not a claim about markets"

    def signal_at(self, window: Sequence[Bar]) -> int:
        return LONG


@dataclass(frozen=True, slots=True)
class Recorder:
    """Records the window it was handed, so look-ahead can be tested rather than trusted."""

    seen: list = None
    stop_atr: float = 1.0
    target_atr: float = 2.0
    warmup: int = 20
    name: str = "recorder"
    philosophy: str = "a test fixture"

    def signal_at(self, window: Sequence[Bar]) -> int:
        self.seen.append(tuple(b.ts for b in window))
        return FLAT


class TestLookAheadIsPreventedByAbsence:
    def test_the_window_never_contains_a_bar_after_the_decision_bar(self):
        series = bars([100 + i for i in range(80)])
        seen: list = []
        run({"T": series}, Recorder(seen=seen), min_trades=0)
        assert seen, "the strategy was never consulted"
        for i, window_ts in enumerate(seen):
            # Each call must end at the bar being decided on, and the engine walks forward
            # one bar at a time from warmup.
            assert window_ts[-1] == series[len(window_ts) - 1].ts

    def test_the_window_is_strictly_shorter_than_the_series(self):
        # If a strategy were ever handed the whole series it could read the future without
        # a single suspicious line of code.
        series = bars([100 + i for i in range(80)])
        seen: list = []
        run({"T": series}, Recorder(seen=seen), min_trades=0)
        assert max(len(w) for w in seen) < len(series)

    def test_entry_is_the_next_bars_open_not_the_signal_bars_close(self):
        # 30 flat bars to establish ATR, then a jump. Entry must be at the bar AFTER the
        # signal, at its open, which is the price a real order could have got.
        closes = [100.0] * 40 + [200.0] * 20
        series = bars(closes)
        result = run({"T": series}, AlwaysLong(), min_trades=0, cost_pct_per_side=0.0)
        first = result.trades[0]
        signal_index = next(i for i, b in enumerate(series) if b.ts == first.entry_ts) - 1
        assert first.entry == series[signal_index + 1].open


class TestAnUnresolvableBarResolvesAgainstTheTrader:
    def test_a_bar_reaching_both_levels_is_taken_as_the_stop(self):
        # A wide bar spanning stop and target. No ordering is knowable from a candle.
        series = list(bars([100.0] * 40))
        wide = series[40 - 1]
        series = tuple(series[:40]) + (
            Bar(wide.ts + 86400, 100.0, 130.0, 70.0, 100.0, 100.0),
        ) + bars([100.0] * 5, start_ts=wide.ts + 2 * 86400)
        result = run({"T": series}, AlwaysLong(), min_trades=0, cost_pct_per_side=0.0)
        ambiguous = [t for t in result.trades if t.ambiguous]
        assert ambiguous, "the spanning bar should have produced an ambiguous trade"
        assert all(t.exit_reason == STOP for t in ambiguous)
        assert all(t.r_gross < 0 for t in ambiguous)

    def test_the_ambiguous_fraction_is_reported_rather_than_absorbed(self):
        series = bars([100.0] * 60)
        result = run({"T": series}, AlwaysLong(), min_trades=0)
        assert 0.0 <= result.ambiguous_fraction <= 1.0

    def test_a_result_leaning_on_that_convention_is_marked_untrustworthy(self):
        # The convention is defensible for a tenth of trades and not for half of them.
        series = bars([100.0] * 60)
        result = run({"T": series}, AlwaysLong(), min_trades=0)
        forced = type(result)(
            MEASURED, result.strategy, result.philosophy, result.pairs,
            tuple(
                type(t)(t.pair, t.direction, t.entry_ts, t.exit_ts, t.entry, t.exit,
                        t.stop, t.target, t.exit_reason, t.bars_held, t.r_gross,
                        t.cost_r, True)
                for t in result.trades
            ),
            result.bars_used, result.span_days,
        )
        assert forced.ambiguous_fraction == 1.0
        assert not forced.trustworthy


class TestTooFewTradesIsAStateNotABadResult:
    def test_a_rule_that_barely_fires_is_insufficient_evidence(self):
        series = bars([100 + i for i in range(60)])
        result = run({"T": series}, AlwaysLong(), min_trades=1000)
        assert result.status == INSUFFICIENT_EVIDENCE

    def test_the_refusal_says_the_rule_is_unmeasured_rather_than_refuted(self):
        series = bars([100 + i for i in range(60)])
        # Normalised because the prose wraps, and the property is the words rather than
        # where the line breaks fall.
        result = " ".join(run({"T": series}, AlwaysLong(), min_trades=1000).describe().split())
        assert "is not refuted" in result
        assert "it is unmeasured" in result

    def test_no_candles_at_all_is_could_not_look(self):
        result = run({"T": bars([100.0] * 3)}, AlwaysLong())
        assert result.status == BT_COULD_NOT_LOOK

    def test_a_profile_cannot_be_built_from_an_unmeasured_rule(self):
        # The bridge into the challenge model is exactly where an unmeasured rule would
        # get laundered into a measured-looking pass rate.
        series = bars([100 + i for i in range(60)])
        with pytest.raises(ValueError, match="unmeasured rule as a measured one"):
            run({"T": series}, AlwaysLong(), min_trades=1000).measured_profile()


class TestStatisticsRefuseToOverstate:
    def test_a_sample_with_no_losses_has_no_payoff_ratio(self):
        # None, not infinity. A sample with no loser has not established that the rule
        # cannot lose; it has established that the sample is small or the period kind.
        closes = [100.0] * 40 + [100 + i * 20 for i in range(1, 25)]
        result = run({"T": bars(closes)}, AlwaysLong(), min_trades=0, cost_pct_per_side=0.0)
        if result.trades and all(t.won for t in result.trades):
            assert result.payoff_ratio is None

    def test_atr_is_none_rather_than_zero_when_it_cannot_be_computed(self):
        # A zero ATR divides a stop distance by nothing further down.
        assert atr(bars([100.0] * 3), 14) is None

    def test_a_perfectly_flat_market_has_no_atr(self):
        flat = tuple(Bar(1_700_000_000 + i * 86400, 100.0, 100.0, 100.0, 100.0, 1.0)
                     for i in range(40))
        assert atr(flat, 14) is None

    def test_correlation_is_none_when_no_two_trades_share_a_day(self):
        # Not a correlation of zero — an absence of the pairs needed to see one.
        series = bars([100 + i for i in range(90)])
        result = run({"T": series}, AlwaysLong(), min_trades=0)
        assert result.measured_correlation() is None


class TestTheSplitCutsEveryMarketTheSameWay:
    def test_both_halves_together_are_the_whole_series(self):
        series = {"A": bars([1.0] * 100), "B": bars([2.0] * 50)}
        early, late = split(series, 0.7)
        for pair in series:
            assert tuple(early[pair]) + tuple(late[pair]) == series[pair]

    def test_the_cut_is_at_the_same_fraction_of_each(self):
        series = {"A": bars([1.0] * 100), "B": bars([2.0] * 50)}
        early, _ = split(series, 0.7)
        assert len(early["A"]) == 70 and len(early["B"]) == 35

    @pytest.mark.parametrize("at", [0.0, 1.0, -0.5, 2.0])
    def test_a_split_outside_the_series_is_refused(self, at):
        with pytest.raises(ValueError):
            split({"A": bars([1.0] * 10)}, at)


class TestTheBenchmarkCounts:
    def test_a_market_that_only_rises_makes_every_window(self):
        rising = bars([100 * (1.01 ** i) for i in range(120)])
        made, tested = buy_and_hold_windows(rising, 45, 8.0)
        assert tested > 0 and made == tested

    def test_a_flat_market_makes_none(self):
        made, tested = buy_and_hold_windows(bars([100.0] * 120), 45, 8.0)
        assert tested > 0 and made == 0


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


def opener_returning(payload):
    def opener(request, **kw):
        return FakeResponse(json.dumps(payload).encode())
    return opener


class TestAnErrorIsNotAnEmptyMarket:
    def test_krakens_error_array_is_could_not_look(self, tmp_path):
        # The shape that matters: HTTP 200, a well-formed result, and the failure sitting
        # in a JSON array beside it.
        read = read_ohlc(
            "XBTUSD", "1d", cache_dir=tmp_path,
            opener=opener_returning({"error": ["EQuery:Unknown asset pair"], "result": {}}),
            sleep=lambda _: None,
        )
        assert read.status == COULD_NOT_LOOK
        assert "Unknown asset pair" in read.detail

    def test_an_unknown_pair_is_could_not_look_not_a_quiet_market(self, tmp_path):
        read = read_ohlc(
            "NOPEUSD", "1d", cache_dir=tmp_path,
            opener=opener_returning({"error": [], "result": {"last": 0}}),
            sleep=lambda _: None,
        )
        assert read.status == COULD_NOT_LOOK

    def test_a_network_failure_is_could_not_look(self, tmp_path):
        def boom(request, **kw):
            raise TimeoutError("the socket gave up")

        read = read_ohlc("XBTUSD", "1d", cache_dir=tmp_path, opener=boom,
                         sleep=lambda _: None)
        assert read.status == COULD_NOT_LOOK
        assert "no conclusion" in read.describe().lower()

    def test_a_short_series_is_not_enough_history_rather_than_a_read(self, tmp_path):
        rows = [[1_700_000_000 + i * 86400, "1", "2", "0.5", "1.5", "1", "10", 5]
                for i in range(10)]
        read = read_ohlc(
            "XBTUSD", "1d", cache_dir=tmp_path, want_bars=720,
            opener=opener_returning({"error": [], "result": {"X": rows, "last": 0}}),
            sleep=lambda _: None,
        )
        assert read.status == NOT_ENOUGH_HISTORY
        assert len(read.bars) == 10

    def test_a_malformed_candle_is_dropped_and_counted(self, tmp_path):
        good = [[1_700_000_000 + i * 86400, "1", "2", "0.5", "1.5", "1", "10", 5]
                for i in range(5)]
        # A high below the close is a broken record, not a strange market. Backtests read
        # highs to decide whether a target was hit.
        bad = [[1_700_000_500, "1", "0.2", "0.5", "1.5", "1", "10", 5]]
        read = read_ohlc(
            "XBTUSD", "1d", cache_dir=tmp_path, want_bars=1,
            opener=opener_returning({"error": [], "result": {"X": good + bad, "last": 0}}),
            sleep=lambda _: None,
        )
        assert len(read.bars) == 5
        assert "1 malformed" in read.detail

    def test_a_read_is_cached_and_replayed_without_a_second_request(self, tmp_path):
        rows = [[1_700_000_000 + i * 86400, "1", "2", "0.5", "1.5", "1", "10", 5]
                for i in range(5)]
        calls = []

        def counting(request, **kw):
            calls.append(request)
            return FakeResponse(
                json.dumps({"error": [], "result": {"X": rows, "last": 0}}).encode()
            )

        first = read_ohlc("XBTUSD", "1d", cache_dir=tmp_path, want_bars=1,
                          opener=counting, sleep=lambda _: None)
        second = read_ohlc("XBTUSD", "1d", cache_dir=tmp_path, want_bars=1,
                           opener=counting, sleep=lambda _: None)
        assert first.status == READ and second.status == READ
        assert len(calls) == 1, "the second read should have come from the cache"
        assert second.from_cache
