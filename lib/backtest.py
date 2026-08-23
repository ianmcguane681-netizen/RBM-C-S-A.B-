"""Running a rule over real candles, and refusing to overstate what came out.

`lib/funded_sim.py` asks what a strategy would do to a funded account given an assumed
win rate and payoff. This module is where those numbers stop being assumed. It walks real
Kraken candles, applies a rule, and reports the trades it actually produced — so the
challenge model can be driven by a measured distribution rather than somebody's estimate.

## Look-ahead is prevented by absence, not by discipline

The classic backtest defect is using the bar you are trading on to decide to trade. It
inflates every result and it is nearly invisible in code review, because the offending line
looks exactly like the correct one.

So the engine does not hand a strategy the price series and ask it to be careful. **It
hands over `bars[:i+1]` — a window ending at the decision bar — and executes at
`bars[i+1].open`.** The future is not off-limits to the strategy; it is not there. This is
the same move as `connectors/chain_exec.py` having no signing method: an absent capability
cannot be misused, and a policy about a present one is a thing somebody edits at eleven
at night.

## The intrabar problem, which has no honest solution

When a bar's low reaches the stop and its high reaches the target, candles cannot say which
came first. Both answers are defensible and one of them is flattering, so:

    the stop is taken, always — the pessimistic reading
    the trade is counted as AMBIGUOUS
    the fraction of ambiguous trades is reported beside every result

That last part is what makes it honest. If a tenth of trades are ambiguous the result is
roughly right; if half are, the strategy's stop and target are close enough together that
daily candles cannot resolve it and **the measurement is not evidence at that timeframe** —
which is a finding about the study, and one the reader must be shown rather than protected
from.

## Three states, and a minimum

    MEASURED              enough trades to say something
    INSUFFICIENT_EVIDENCE the rule ran and produced too few trades to conclude from
    COULD_NOT_LOOK        there were no candles to run it over

`INSUFFICIENT_EVIDENCE` is not a bad result and must never be read as one. A rule that
fired four times in two years has told you nothing about its win rate, and a 75% win rate
over four trades is noise with a percentage sign. `MIN_TRADES` is where the line sits and
it is deliberately blunt.

## What is charged, and what is not

Fees and slippage are charged on both legs at rates the caller supplies, and expressed in
units of risk — the same `cost_r` that `lib/funded_kraken.py` computes from the fee
schedule, except measured against the stop each trade actually used.

Not modelled, and every one flatters the result: partial fills, a stop that slips past its
level in a fast move, funding paid on a perpetual held overnight, and the market impact of
the position itself. Treat a measured edge here as an upper bound.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Protocol, Sequence

from connectors.kraken import Bar

MEASURED = "MEASURED"
INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
COULD_NOT_LOOK = "COULD_NOT_LOOK"

LONG = 1
FLAT = 0
SHORT = -1

#: Why a position closed.
STOP = "STOP"
TARGET = "TARGET"
TIMEOUT = "TIMEOUT"
DATA_ENDED = "DATA_ENDED"

#: Below this many trades, no win rate is worth quoting. Blunt on purpose: the alternative
#: is a confidence interval nobody reads, attached to a point estimate everybody quotes.
MIN_TRADES = 30

#: Above this share of trades unresolvable within their bar, the timeframe is too coarse
#: for the stop and target being used, and the measurement is not evidence.
MAX_TOLERABLE_AMBIGUITY = 0.25


class Strategy(Protocol):
    """A rule that looks at candles up to now and says what it wants to be holding.

    `signal_at` receives a window ENDING at the bar being decided on. There is no
    parameter for the rest of the series because there is no honest use for it.
    """

    name: str
    philosophy: str
    warmup: int
    stop_atr: float
    target_atr: float

    def signal_at(self, window: Sequence[Bar]) -> int: ...


# --------------------------------------------------------------------------------------
# Indicators, all computed from a window that ends at the decision bar
# --------------------------------------------------------------------------------------


def true_range(previous: Bar, current: Bar) -> float:
    return max(
        current.high - current.low,
        abs(current.high - previous.close),
        abs(current.low - previous.close),
    )


def atr(window: Sequence[Bar], period: int) -> float | None:
    """Average true range, or None when there is not enough window to compute it.

    None rather than zero. A zero ATR would size a position by dividing by nothing, and
    the resulting stop distance would be either infinite or nonsense depending on which
    line rounded first.
    """

    if len(window) < period + 1:
        return None
    ranges = [
        true_range(window[i - 1], window[i])
        for i in range(len(window) - period, len(window))
    ]
    value = statistics.fmean(ranges)
    return value if value > 0 else None


def ema(values: Sequence[float], period: int) -> float | None:
    if len(values) < period:
        return None
    k = 2.0 / (period + 1)
    out = statistics.fmean(values[:period])
    for value in values[period:]:
        out = value * k + out * (1 - k)
    return out


def rsi(closes: Sequence[float], period: int) -> float | None:
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(len(closes) - period, len(closes)):
        change = closes[i] - closes[i - 1]
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))
    up, down = statistics.fmean(gains), statistics.fmean(losses)
    if down == 0:
        return 100.0 if up > 0 else 50.0
    return 100.0 - 100.0 / (1 + up / down)


# --------------------------------------------------------------------------------------
# Trades and results
# --------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Trade:
    """One round trip, in price and in units of the risk it took."""

    pair: str
    direction: int
    entry_ts: int
    exit_ts: int
    entry: float
    exit: float
    stop: float
    target: float
    exit_reason: str
    bars_held: int
    #: Result before costs, in multiples of the distance from entry to stop.
    r_gross: float
    #: Fees and slippage on both legs, in the same units.
    cost_r: float
    #: The bar that closed this trade reached both the stop and the target, and candles
    #: cannot say which came first. Resolved as the stop, and counted here.
    ambiguous: bool = False

    @property
    def r_net(self) -> float:
        return self.r_gross - self.cost_r

    @property
    def won(self) -> bool:
        return self.r_net > 0


@dataclass(frozen=True, slots=True)
class BacktestResult:
    """What a rule did over real candles, or why nothing can be said about it."""

    status: str
    strategy: str
    philosophy: str
    pairs: tuple[str, ...]
    trades: tuple[Trade, ...] = ()
    bars_used: int = 0
    span_days: float = 0.0
    detail: str = ""

    @property
    def r_values(self) -> tuple[float, ...]:
        return tuple(t.r_net for t in self.trades)

    @property
    def win_rate(self) -> float | None:
        if not self.trades:
            return None
        return sum(1 for t in self.trades if t.won) / len(self.trades)

    @property
    def payoff_ratio(self) -> float | None:
        """Mean win over mean loss, both in R. None if the sample has no losses or no wins.

        None is not 'infinite' and not 'perfect'. A sample with no losing trade has not
        established that the strategy cannot lose; it has established that the sample is
        too small or the period too kind.
        """

        wins = [t.r_net for t in self.trades if t.won]
        losses = [-t.r_net for t in self.trades if not t.won]
        if not wins or not losses:
            return None
        return statistics.fmean(wins) / statistics.fmean(losses)

    @property
    def expected_r(self) -> float | None:
        return statistics.fmean(self.r_values) if self.trades else None

    @property
    def mean_cost_r(self) -> float | None:
        return statistics.fmean([t.cost_r for t in self.trades]) if self.trades else None

    @property
    def ambiguous_fraction(self) -> float:
        if not self.trades:
            return 0.0
        return sum(1 for t in self.trades if t.ambiguous) / len(self.trades)

    @property
    def trades_per_day(self) -> float:
        return len(self.trades) / self.span_days if self.span_days else 0.0

    @property
    def max_drawdown_r(self) -> float:
        """Worst peak-to-trough of the cumulative R curve, in units of risk.

        The number that decides whether a funded account survives the strategy, and the one
        a headline return never shows.
        """

        peak = running = worst = 0.0
        for r in self.r_values:
            running += r
            peak = max(peak, running)
            worst = min(worst, running - peak)
        return worst

    @property
    def trustworthy(self) -> bool:
        return (
            self.status == MEASURED
            and self.ambiguous_fraction <= MAX_TOLERABLE_AMBIGUITY
        )

    def measured_correlation(self) -> float | None:
        """How much trades opening on the same day agree, above what chance would give.

        `lib/funded_sim.py` takes an `intraday_correlation` and the assumed profiles guess
        it. Here it can be measured, and it matters: a portfolio of ten crypto majors is
        not ten independent bets, so days when the rule is wrong tend to be days it is
        wrong everywhere, and that is what spends a daily loss allowance in one sitting.

        The estimator is the standard one for equicorrelated binary outcomes: the excess of
        observed same-sign pairs over the rate independence would produce, scaled by the
        room that was available above it. None when no day carried two trades — which is
        not a correlation of zero, it is an absence of the pairs needed to see one.
        """

        by_day: dict[int, list[bool]] = {}
        for trade in self.trades:
            by_day.setdefault(trade.entry_ts // 86400, []).append(trade.won)

        agree = pairs = 0
        for outcomes in by_day.values():
            for i in range(len(outcomes)):
                for j in range(i + 1, len(outcomes)):
                    pairs += 1
                    agree += outcomes[i] == outcomes[j]
        if not pairs:
            return None

        p = self.win_rate or 0.0
        expected = p * p + (1 - p) * (1 - p)
        if expected >= 1:
            return None
        observed = agree / pairs
        return max(0.0, min(1.0, (observed - expected) / (1 - expected)))

    def measured_profile(self, name: str = "") -> "object":
        """Hand these trades to `lib/funded_sim.py` as a profile it can run accounts with.

        Everything the simulator was guessing is filled in from the sample: the trade rate,
        the win rate, the payoff, the cost, the correlation, and — the part a two-point
        model cannot carry — the actual distribution of results, tails included.

        `holds_overnight` is True and not a choice. These are daily bars, so every position
        is held through whatever the programme calls the end of its day, and a strategy that
        holds overnight may not claim a self-imposed daily stop. That is not a limitation of
        the model; it is the fact that nobody is awake to apply one.
        """

        from lib.funded_sim import StrategyProfile

        if self.status != MEASURED:
            raise ValueError(
                f"{self.strategy} is {self.status}: a profile built from it would present "
                f"an unmeasured rule as a measured one, which is the whole thing this "
                f"module exists to prevent"
            )
        win = self.win_rate
        payoff = self.payoff_ratio
        if not 0 < win < 1 or payoff is None:
            raise ValueError(
                f"{self.strategy} has no losses or no wins in {len(self.trades)} trades, so "
                f"its payoff ratio is undefined. That is a fact about the sample, not about "
                f"the rule"
            )
        return StrategyProfile(
            name=name or f"{self.strategy} (measured)",
            description=self.philosophy,
            trades_per_day=max(self.trades_per_day, 1e-6),
            win_rate=win,
            payoff_ratio=payoff,
            risk_per_trade_pct=1.0,
            cost_r=self.mean_cost_r or 0.0,
            empirical_r=self.r_values,
            intraday_correlation=(
                self.measured_correlation() if self.measured_correlation() is not None
                else 0.35
            ),
            daily_stop_at=None,
            holds_overnight=True,
        )

    def by_pair(self) -> dict[str, list[Trade]]:
        out: dict[str, list[Trade]] = {}
        for trade in self.trades:
            out.setdefault(trade.pair, []).append(trade)
        return out

    def describe(self) -> str:
        if self.status == COULD_NOT_LOOK:
            return (
                f"COULD_NOT_LOOK  {self.strategy}: {self.detail}\n"
                f"  Nothing follows about this rule. It was not run."
            )
        if self.status == INSUFFICIENT_EVIDENCE:
            return (
                f"INSUFFICIENT_EVIDENCE  {self.strategy}: {len(self.trades)} trade(s) "
                f"over {self.span_days:.0f} days.\n"
                f"  {self.detail}\n"
                f"  Any win rate computed from this is noise with a percentage sign. The "
                f"rule is not\n  refuted — it is unmeasured, and those are different."
            )
        lines = [
            f"MEASURED  {self.strategy}: {len(self.trades)} trades across "
            f"{len(self.pairs)} pair(s) over {self.span_days:.0f} days"
        ]
        lines.append(
            f"  edge {self.expected_r:+.3f}R per trade after costs, "
            f"{self.win_rate:.1%} win"
            + (f" at {self.payoff_ratio:.2f}R" if self.payoff_ratio else " (no losses in sample)")
        )
        lines.append(
            f"  worst drawdown {self.max_drawdown_r:.1f}R, "
            f"{self.trades_per_day:.3f} trades/day, cost {self.mean_cost_r:.3f}R"
        )
        if self.ambiguous_fraction:
            note = (
                "  UNTRUSTWORTHY AT THIS TIMEFRAME" if not self.trustworthy
                else "  tolerable"
            )
            lines.append(
                f"  {self.ambiguous_fraction:.1%} of trades hit stop and target in the "
                f"same bar.{note}"
            )
        return "\n".join(lines)


# --------------------------------------------------------------------------------------
# The engine
# --------------------------------------------------------------------------------------


def _walk_one_pair(
    pair: str,
    bars: Sequence[Bar],
    strategy: Strategy,
    *,
    cost_pct_per_side: float,
    max_hold: int,
) -> list[Trade]:
    """One pass over one market, one position at a time."""

    trades: list[Trade] = []
    i = max(strategy.warmup, 1)
    while i < len(bars) - 1:
        # The window ENDS at bar i. Everything after it is unavailable rather than merely
        # off-limits, which is the only version of this guard that survives a refactor.
        window = bars[:i + 1]
        direction = strategy.signal_at(window)
        if direction == FLAT:
            i += 1
            continue

        span = atr(window, 14)
        if span is None:
            i += 1
            continue

        entry_bar = i + 1
        entry = bars[entry_bar].open
        risk = strategy.stop_atr * span
        stop = entry - direction * risk
        target = entry + direction * strategy.target_atr * risk
        if risk <= 0 or stop <= 0:
            i += 1
            continue

        exit_price = bars[-1].close
        exit_index = len(bars) - 1
        reason = DATA_ENDED
        ambiguous = False

        last = min(entry_bar + max_hold, len(bars) - 1)
        for j in range(entry_bar, last + 1):
            bar = bars[j]
            hit_stop = bar.low <= stop if direction == LONG else bar.high >= stop
            hit_target = bar.high >= target if direction == LONG else bar.low <= target
            if hit_stop and hit_target:
                # Candles cannot order two levels inside one bar. Take the stop and say so.
                exit_price, exit_index, reason, ambiguous = stop, j, STOP, True
                break
            if hit_stop:
                exit_price, exit_index, reason = stop, j, STOP
                break
            if hit_target:
                exit_price, exit_index, reason = target, j, TARGET
                break
            if j == last and j < len(bars) - 1:
                exit_price, exit_index, reason = bar.close, j, TIMEOUT
                break

        r_gross = (exit_price - entry) * direction / risk
        cost_r = (entry + exit_price) * (cost_pct_per_side / 100.0) / risk
        trades.append(Trade(
            pair, direction, bars[entry_bar].ts, bars[exit_index].ts, entry, exit_price,
            stop, target, reason, exit_index - entry_bar, r_gross, cost_r, ambiguous,
        ))
        # Resume after the exit: one position at a time, and no re-entry on the bar that
        # closed the last one.
        i = max(exit_index, i + 1)
    return trades


def run(
    series: dict[str, Sequence[Bar]],
    strategy: Strategy,
    *,
    cost_pct_per_side: float = 0.07,
    max_hold: int = 20,
    min_trades: int = MIN_TRADES,
) -> BacktestResult:
    """Run one rule across every market supplied and pool the trades.

    Pooling is what makes the sample large enough to say anything at all — ten markets of
    two years is 7,200 asset-days where one market is 720. It is also the assumption most
    likely to be wrong, because crypto majors move together, so `by_pair()` exists and the
    report prints the per-market breakdown: a pooled edge carried by one asset is a fact
    about that asset.
    """

    usable = {pair: bars for pair, bars in series.items() if len(bars) > strategy.warmup + 2}
    if not usable:
        return BacktestResult(
            COULD_NOT_LOOK, strategy.name, strategy.philosophy, tuple(series),
            detail=(
                f"no market had more than {strategy.warmup + 2} candles, which is what "
                f"this rule needs before it can produce a first signal"
            ),
        )

    trades: list[Trade] = []
    bars_used = 0
    span = 0.0
    for pair, bars in usable.items():
        trades.extend(_walk_one_pair(
            pair, bars, strategy,
            cost_pct_per_side=cost_pct_per_side, max_hold=max_hold,
        ))
        bars_used += len(bars)
        span = max(span, (bars[-1].ts - bars[0].ts) / 86400.0)

    trades.sort(key=lambda t: t.entry_ts)
    if len(trades) < min_trades:
        return BacktestResult(
            INSUFFICIENT_EVIDENCE, strategy.name, strategy.philosophy, tuple(usable),
            tuple(trades), bars_used, span,
            detail=f"{min_trades} is the fewest this engine will draw a conclusion from",
        )
    return BacktestResult(
        MEASURED, strategy.name, strategy.philosophy, tuple(usable),
        tuple(trades), bars_used, span,
    )


def split(
    series: dict[str, Sequence[Bar]], at: float = 0.7
) -> tuple[dict[str, Sequence[Bar]], dict[str, Sequence[Bar]]]:
    """Cut every market at the same fraction of its history.

    The out-of-sample half is the only defence against the thing backtests are for, which
    is finding a rule that explains the past. A rule tuned on everything will always look
    good on everything.
    """

    if not 0 < at < 1:
        raise ValueError("the split point must be strictly inside the series")
    early, late = {}, {}
    for pair, bars in series.items():
        cut = int(len(bars) * at)
        early[pair], late[pair] = bars[:cut], bars[cut:]
    return early, late


def buy_and_hold_windows(
    bars: Sequence[Bar], window_days: int, target_pct: float
) -> tuple[int, int]:
    """How often simply holding would have made the target over the challenge's length.

    The benchmark that decides whether a rule is worth having at all. A clever strategy
    that passes the challenge less often than buying the asset and waiting is not a
    strategy, and this is the cheapest possible way to find that out.

    Returns (windows that made the target, windows tested).
    """

    made = tested = 0
    for i in range(len(bars) - window_days):
        start, end = bars[i].close, bars[i + window_days].close
        if start <= 0:
            continue
        tested += 1
        if (end - start) / start * 100.0 >= target_pct:
            made += 1
    return made, tested
