"""From a rule that measured well to a sized instruction somebody can act on.

`lib/backtest.py` established which rules have an edge. `lib/funded_sim.py` established
what that edge does to an account. This is the part in between and the part that reaches a
person: what the rule says RIGHT NOW, at what size, with the stop it was measured with.

It sends nothing and places nothing. It produces a `Signal`, and `signals.py` puts that on
a phone.

## The last candle is not a candle yet

Kraken's OHLC series ends with the bar currently forming. Deciding on it means the signal
appears at nine in the morning, vanishes at two, and comes back at six — the same rule
producing three different answers about one day, none of which the backtest ever saw,
because a backtest reads completed bars.

**So the forming bar is dropped and the decision is made on the last CLOSED one.** The
price used for the entry is the current one, which is exactly the shape the backtest
modelled: decide on a closed bar, execute at the next opportunity.

That is not a refinement. A signal that flickers is one somebody eventually acts on at the
wrong moment, and every measured figure in `docs/kraken-backtest.md` would be describing a
different strategy from the one being traded.

## The size is the minimum of what every constraint allows, and it says which one bound it

`lib/sizing.py` does the arithmetic and names the binding constraint, because "my own rules
are holding me back" and "the market cannot absorb me" call for opposite responses.

Four constraints, and all four are measured rather than assumed:

    risk limit        a share of the ring-fence
    per-position cap  the ring-fence's own limit
    exit depth        read from Kraken's live order book
    volatility bound  from the same ATR the stop uses

If the order book cannot be read the size is INDETERMINATE rather than computed from the
three that remain — a constraint that silently drops out RAISES the permitted size, so the
missing one is always the flattering one.

## A signal is not an order and this module cannot make it one

There is no broker here, no key path and no send. `connectors/kraken_exec.py` is the thing
that can place, it is reached through `lib/placing.py` so the mode and the breakers get
their say, and none of that is importable from this file by accident.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Sequence

from connectors.kraken import Bar
from lib.backtest import FLAT, LONG, atr
from lib.sizing import (
    INDETERMINATE,
    SIZED,
    Constraint,
    Size,
    exit_depth,
    size_position,
    volatility_bound,
)

BUY = "buy"
SELL = "sell"


@dataclass(frozen=True, slots=True)
class Signal:
    """One rule's answer about one market, sized, with the exit it was measured with."""

    pair: str
    side: str
    strategy: str
    philosophy: str
    #: The close of the last COMPLETED bar — what the rule actually decided on.
    decided_on: int
    #: The live price the entry would be taken at.
    price: float
    stop: float
    target: float
    atr: float
    size: Size
    volume: float = 0.0
    risk_cash: float = 0.0
    notional: float = 0.0

    @property
    def actionable(self) -> bool:
        return self.size.status == SIZED and self.volume > 0

    @property
    def reward_to_risk(self) -> float:
        risk = abs(self.price - self.stop)
        return abs(self.target - self.price) / risk if risk else 0.0

    def describe(self) -> str:
        head = f"{self.side.upper()} {self.pair}"
        if not self.actionable:
            return (
                f"{head}  —  NO SIZE\n"
                f"{self.size.describe()}"
            )
        return "\n".join([
            f"{head}  {self.volume:.8f} at ~{self.price:,.4f}",
            f"  stop      {self.stop:,.4f}   ({abs(self.price - self.stop) / self.price * 100:.2f}% away)",
            f"  target    {self.target:,.4f}   {self.reward_to_risk:.2f}:1 reward to risk",
            f"  risking   {self.risk_cash:,.2f}   notional {self.notional:,.2f}",
            f"  bound by  {self.size.bound_by}",
            f"  rule      {self.strategy}, decided on the bar closing "
            f"{_stamp(self.decided_on)}",
        ])


def _stamp(ts: int) -> str:
    from datetime import datetime, timezone

    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%MZ")


def size_signal(
    pair: str,
    side: str,
    price: float,
    stop: float,
    *,
    balance: float,
    risk_pct: float,
    per_position_limit: float,
    depth_value: float | None,
    slippage_pct: float,
    realised_vol_pct: float | None,
    tolerated_move_pct: float,
) -> Size:
    """Every ceiling, in cash. `None` depth or volatility makes it INDETERMINATE.

    `depth_value` of None is a book that could not be read, not a market with no bids. The
    difference decides whether this returns a size or refuses to, and getting it the other
    way round produces the largest position exactly when least is known.
    """

    risk_distance = abs(price - stop)
    if risk_distance <= 0 or price <= 0:
        return Size(INDETERMINATE, pair)

    # The cash a position may put at risk converts to a position VALUE through the stop
    # distance: risking 100 with a 2% stop is a 5,000 position.
    leverage_to_risk = price / risk_distance
    constraints = [
        Constraint("risk limit", balance * risk_pct / 100.0 * leverage_to_risk,
                   f"{risk_pct:.2f}% of {balance:,.2f} at a "
                   f"{risk_distance / price * 100:.2f}% stop"),
        Constraint("per-position cap", per_position_limit,
                   "the ring-fence's own limit on one position"),
        volatility_bound(balance * leverage_to_risk, realised_vol_pct, tolerated_move_pct),
    ]
    if depth_value is None:
        constraints.append(Constraint(
            "exit depth", -1.0,
            "the order book could not be read, so what can be sold is unknown"))
    else:
        constraints.append(exit_depth(depth_value, slippage_pct))
    return size_position(pair, constraints, currency="USD")


def scan(
    series: dict[str, Sequence[Bar]],
    strategy: Any,
    *,
    balance: float,
    risk_pct: float = 1.0,
    per_position_limit: float,
    depth_reader: Callable[[str], Any] | None = None,
    slippage_pct: float = 0.5,
    tolerated_move_pct: float = 2.0,
    atr_period: int = 14,
) -> list[Signal]:
    """What the rule says about every market right now.

    Every market is visited and a market with no signal simply produces none. A market
    whose candles could not be read is NOT in `series` at all — that filtering happens in
    the caller, where the COULD_NOT_LOOK can still be reported, because a market silently
    missing from a scan reads as a market with nothing to say.
    """

    signals: list[Signal] = []
    for pair, bars in series.items():
        if len(bars) < strategy.warmup + 3:
            continue

        # Drop the bar that is still forming. See the module docstring: deciding on it
        # produces a signal that flickers through the day and was never backtested.
        closed = tuple(bars[:-1])
        direction = strategy.signal_at(closed)
        if direction == FLAT:
            continue

        span = atr(closed, atr_period)
        if span is None:
            continue

        # The live price is the forming bar's latest close — the best available estimate of
        # what an order would touch right now.
        price = float(bars[-1].close)
        side = BUY if direction == LONG else SELL
        stop = price - direction * strategy.stop_atr * span
        target = price + direction * strategy.target_atr * span
        if stop <= 0:
            continue

        depth_value = None
        if depth_reader is not None:
            read = depth_reader(pair)
            if getattr(read, "usable", False):
                depth_value = float(read.exitable_value)

        realised_vol_pct = span / price * 100.0 if price else None
        size = size_signal(
            pair, side, price, stop,
            balance=balance, risk_pct=risk_pct,
            per_position_limit=per_position_limit,
            depth_value=depth_value, slippage_pct=slippage_pct,
            realised_vol_pct=realised_vol_pct,
            tolerated_move_pct=tolerated_move_pct,
        )
        volume = risk_cash = notional = 0.0
        if size.status == SIZED:
            notional = size.amount
            volume = notional / price
            risk_cash = volume * abs(price - stop)

        signals.append(Signal(
            pair=pair, side=side, strategy=strategy.name,
            philosophy=strategy.philosophy, decided_on=closed[-1].ts,
            price=price, stop=stop, target=target, atr=span, size=size,
            volume=volume, risk_cash=risk_cash, notional=notional,
        ))
    return signals


def describe_scan(signals: Sequence[Signal], *, scanned: int, blind: Sequence[str] = ()) -> str:
    """The whole scan, including the markets that said nothing and the ones that could not.

    A scan reporting only its hits cannot be told apart from a scan that reached two markets
    of ten. This repository has produced that defect in an odds feed, an EDGAR read and a
    chain query, and it is the one this file is most likely to reproduce.
    """

    lines = [f"{len(signals)} signal(s) from {scanned} market(s) read"]
    if blind:
        lines.append(
            f"  {len(blind)} market(s) COULD NOT BE READ: {', '.join(sorted(blind))}. "
            f"They are not quiet — they are unmeasured, and any of them may be signalling."
        )
    actionable = [s for s in signals if s.actionable]
    refused = [s for s in signals if not s.actionable]
    for signal in actionable:
        lines.append("")
        lines.append(signal.describe())
    if refused:
        lines.append("")
        lines.append(
            f"  {len(refused)} signal(s) could not be sized and are NOT actionable:"
        )
        for signal in refused:
            lines.append(f"    {signal.side.upper()} {signal.pair}: {signal.size.status}")
    if not signals:
        lines.append("  Nothing is signalling. That is a reading of every market above.")
    return "\n".join(lines)
