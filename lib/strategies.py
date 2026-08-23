"""Concrete rules, each with the belief about markets that would have to be true.

A strategy is not a set of parameters. It is a claim about why money is available, and the
parameters are one expression of that claim. So every rule here carries a `philosophy` that
says what it believes, who is on the other side of the trade, and what would have to change
for the edge to stop existing — and the report prints it beside the measured numbers.

That pairing is the whole design. A measured edge with no story behind it is a pattern
found in 7,200 asset-days by looking, and enough looking finds patterns in noise. A story
with no measurement is an opinion. Neither is worth a funded account on its own, and the
report shows both so a reader can refuse a rule that has one and not the other.

## Why these five

They are chosen to disagree with each other. Two say price continues, two say price
reverts, one says nothing at all and just holds. If the trend rules and the reversion rules
both measure a positive edge over the same candles, something is wrong with the measurement
rather than right with the strategies — and that check is only available because the set
was picked to make it possible.

## Everything is long and short

The account is reported to be perpetual futures, where a short costs no more than a long.
A long-only crypto rule measured over 2024-2026 is substantially a measurement of whether
crypto went up during 2024-2026, and `allow_short=False` exists to demonstrate exactly that
rather than to be used.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from connectors.kraken import Bar
from lib.backtest import FLAT, LONG, SHORT, atr, ema, rsi


@dataclass(frozen=True, slots=True)
class Donchian:
    """Buy new highs, sell new lows."""

    lookback: int = 20
    stop_atr: float = 2.0
    target_atr: float = 3.0
    allow_short: bool = True

    @property
    def name(self) -> str:
        return f"donchian-{self.lookback}"

    @property
    def warmup(self) -> int:
        return self.lookback + 15

    @property
    def philosophy(self) -> str:
        return (
            "Price continues. A market making a new high has no holder above it sitting on "
            "a loss and waiting to get out even, so the supply that normally caps a rally "
            "is absent. The other side of the trade is somebody taking profit early or "
            "shorting a move they think has gone too far, and both are systematically "
            "wrong in an asset class with no valuation anchor to be too far from. "
            "It stops working when the market ranges: every breakout then reverses and the "
            "rule pays a stop for each one, which is why its losing runs are long and its "
            "winning trades are few and large."
        )

    def signal_at(self, window: Sequence[Bar]) -> int:
        if len(window) < self.lookback + 1:
            return FLAT
        recent = window[-self.lookback - 1:-1]
        close = window[-1].close
        if close > max(bar.high for bar in recent):
            return LONG
        if self.allow_short and close < min(bar.low for bar in recent):
            return SHORT
        return FLAT


@dataclass(frozen=True, slots=True)
class EmaCross:
    """Hold the direction the averages agree on."""

    fast: int = 10
    slow: int = 40
    stop_atr: float = 2.0
    target_atr: float = 4.0
    allow_short: bool = True

    @property
    def name(self) -> str:
        return f"ema-{self.fast}x{self.slow}"

    @property
    def warmup(self) -> int:
        return self.slow + 15

    @property
    def philosophy(self) -> str:
        return (
            "The same claim as the breakout rule, made more slowly and therefore more "
            "cheaply: trends persist, so the recent average sitting above the older one is "
            "information about the next move rather than about the last. It trades far less "
            "often than a breakout rule because it only fires on the crossing, and it gives "
            "back more at the top because an average has to be dragged down before it "
            "reverses. Included as the control on the breakout: if trend is real, both "
            "should measure positive, and if only one does then what was measured is the "
            "parameter, not the trend."
        )

    def signal_at(self, window: Sequence[Bar]) -> int:
        closes = [bar.close for bar in window]
        if len(closes) < self.slow + 2:
            return FLAT
        fast_now, slow_now = ema(closes, self.fast), ema(closes, self.slow)
        fast_prev, slow_prev = ema(closes[:-1], self.fast), ema(closes[:-1], self.slow)
        if None in (fast_now, slow_now, fast_prev, slow_prev):
            return FLAT
        if fast_prev <= slow_prev and fast_now > slow_now:
            return LONG
        if self.allow_short and fast_prev >= slow_prev and fast_now < slow_now:
            return SHORT
        return FLAT


@dataclass(frozen=True, slots=True)
class RsiReversion:
    """Buy what has fallen too fast."""

    period: int = 14
    oversold: float = 30.0
    overbought: float = 70.0
    stop_atr: float = 2.0
    target_atr: float = 2.0
    allow_short: bool = True

    @property
    def name(self) -> str:
        return f"rsi-{self.period}"

    @property
    def warmup(self) -> int:
        return self.period + 15

    @property
    def philosophy(self) -> str:
        return (
            "Price reverts. A move that goes far in few bars is mostly forced selling — "
            "liquidations, margin calls, a fund that has to be out by Friday — and forced "
            "sellers are price-insensitive, so they push past where a willing seller would "
            "have stopped. The edge is being the willing buyer they need, and the payment "
            "is for providing liquidity when it is scarce. It stops working, expensively, "
            "when the move is not forced but informed: then the thing that looked oversold "
            "was correctly priced on news the buyer had not read, and the rule buys every "
            "rung of the way down."
        )

    def signal_at(self, window: Sequence[Bar]) -> int:
        closes = [bar.close for bar in window]
        value = rsi(closes, self.period)
        if value is None:
            return FLAT
        if value <= self.oversold:
            return LONG
        if self.allow_short and value >= self.overbought:
            return SHORT
        return FLAT


@dataclass(frozen=True, slots=True)
class BollingerFade:
    """Buy the lower band, sell the upper one."""

    period: int = 20
    deviations: float = 2.0
    stop_atr: float = 2.0
    target_atr: float = 2.0
    allow_short: bool = True

    @property
    def name(self) -> str:
        return f"bollinger-{self.period}"

    @property
    def warmup(self) -> int:
        return self.period + 15

    @property
    def philosophy(self) -> str:
        return (
            "The same claim as the RSI rule with a different definition of 'too far': "
            "measured in standard deviations of this market's own recent behaviour rather "
            "than in the shape of its recent closes. It is the control on that rule for the "
            "same reason the moving-average cross is the control on the breakout. Where the "
            "two reversion rules disagree, what was measured was the indicator."
        )

    def signal_at(self, window: Sequence[Bar]) -> int:
        closes = [bar.close for bar in window]
        if len(closes) < self.period:
            return FLAT
        recent = closes[-self.period:]
        mean = sum(recent) / len(recent)
        variance = sum((c - mean) ** 2 for c in recent) / len(recent)
        sd = variance ** 0.5
        if sd <= 0:
            return FLAT
        close = closes[-1]
        if close < mean - self.deviations * sd:
            return LONG
        if self.allow_short and close > mean + self.deviations * sd:
            return SHORT
        return FLAT


@dataclass(frozen=True, slots=True)
class VolatilityBreakout:
    """Trade the day that is bigger than the days before it."""

    period: int = 20
    threshold: float = 1.6
    stop_atr: float = 1.5
    target_atr: float = 3.0
    allow_short: bool = True

    @property
    def name(self) -> str:
        return f"volbreak-{self.period}"

    @property
    def warmup(self) -> int:
        return self.period + 15

    @property
    def philosophy(self) -> str:
        return (
            "A bar much larger than the recent average is information arriving, and "
            "information takes more than one bar to be priced by everybody who will act on "
            "it. The claim is not that the market is trending but that it is currently "
            "repricing, and that the repricing continues in the direction it started. "
            "It is the only rule here whose entry is conditioned on volatility rather than "
            "on direction, which makes it the one most likely to be trading a different "
            "thing than the other four — and therefore the one worth having if it measures "
            "positive when they do not."
        )

    def signal_at(self, window: Sequence[Bar]) -> int:
        if len(window) < self.period + 2:
            return FLAT
        span = atr(window[:-1], self.period)
        if span is None:
            return FLAT
        bar = window[-1]
        size = bar.high - bar.low
        if size < self.threshold * span or size <= 0:
            return FLAT
        # Where it closed within its own range says which side won the bar.
        position = (bar.close - bar.low) / size
        if position >= 0.66:
            return LONG
        if self.allow_short and position <= 0.34:
            return SHORT
        return FLAT


#: The set, chosen to disagree. Two say price continues, two say it reverts, one says the
#: market is repricing and does not care which way.
CANDIDATE_RULES = (
    Donchian(),
    EmaCross(),
    RsiReversion(),
    BollingerFade(),
    VolatilityBreakout(),
)

BY_NAME = {rule.name: rule for rule in CANDIDATE_RULES}
