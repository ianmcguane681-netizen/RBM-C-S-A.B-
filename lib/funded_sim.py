"""The paper model: many ways of trading a funded account, run against the rulebook.

`lib/funded.py` knows whether a sequence of days passed or breached. This module makes the
days. It answers one question and it is not "which strategy makes the most money":

    Given what the strategy is ASSUMED to do per trade, what fraction of accounts reach
    the target without touching a floor, and what does the 80% share of what they withdraw
    come to, net of the fee paid for every account including the ones that died?

## Read this before quoting a number out of it

**These are simulated returns from an assumed distribution. They are not evidence that any
edge exists.** Every profile below carries a win rate and a payoff that a person estimated;
the model then computes their consequences exactly. If the estimate is wrong the output is
wrong in the same direction and with more decimal places. What the model is genuinely good
for is the part that is pure arithmetic once the estimate is granted — how a drawdown floor
interacts with position size, what a daily limit costs a strategy that holds overnight,
whether a payout schedule is survivable — and those conclusions are robust to the estimate
being somewhat off, which is why they are the ones stated in `docs/kraken-funded-model.md`.

This is the same distinction the reapers make when they say the audit chain is what is
lost. A working number is not a reviewed one, and a simulated number is not an observed one.

## The three things this model does that a naive one does not

**Trades within a day are correlated.** A day is usually one market regime, and a strategy
that is wrong is often wrong four times before lunch. Modelling a day as independent coin
flips understates the daily-loss breach probability by a factor that grows with trade
count — it is the single largest error in amateur prop-account modelling, and
`intraday_correlation` is the dial.

**Cost is charged in units of risk, not of notional.** What matters to a funded account is
what a round trip costs relative to the distance to the stop. Kraken's taker fee at the
entry tier is around 0.25% a side; a scalper working a 0.4% stop pays about 1.2R in fees
to win 1R, and no win rate rescues that. Expressing cost as `cost_r` makes that visible in
the profile instead of hiding it in a notional percentage that looks small.

**The intraday low is generated, not inferred.** Each day is played trade by trade and the
running minimum is recorded, because that is the number every floor is checked against.

## What the simulator does NOT model

Named because an absent factor must not read as a factor of zero:

    slippage that widens exactly when the strategy needs it most
    a stop that gaps through on a Sunday wick
    the exchange being unreachable while a position is open
    correlation ACROSS days, so a bad week is only ever four independent bad days
    the overnight gap itself: a held position resolves in the next day's trades rather
        than jumping the account through its floor while nobody is at the screen
    any change in the edge itself over the horizon

All five push in the same direction, which is against the trader. Treat every pass rate
here as an optimistic bound rather than a forecast.
"""
from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass, field, replace
from datetime import date, timedelta

from lib.funded import (
    BREACHED,
    DAILY_LOSS,
    INDETERMINATE,
    PASSED,
    TIME_EXPIRED,
    TOTAL_DRAWDOWN,
    AccountWalk,
    ChallengeRules,
    Day,
    Verdict,
    withdrawable,
)

#: What the per-trade risk is a percentage of.
OF_ACCOUNT_SIZE = "OF_ACCOUNT_SIZE"    # the same dollars every trade, win or lose
OF_CURRENT_EQUITY = "OF_CURRENT_EQUITY"  # compounds up, and de-risks on the way down
RISK_BASES = (OF_ACCOUNT_SIZE, OF_CURRENT_EQUITY)


@dataclass(frozen=True, slots=True)
class StrategyProfile:
    """One way of trading, described by what it does per trade rather than per year.

    Annualised return is the wrong unit for this problem. A challenge is decided in weeks
    by the shape of the worst run, so the model needs the per-trade distribution and the
    trade count, and derives the rest.
    """

    name: str
    #: Why anybody would run this, and what in this repository could actually do it.
    description: str
    trades_per_day: float
    win_rate: float
    #: What a win pays, in multiples of what was risked. 2.0 means risk 1 to make 2.
    payoff_ratio: float
    risk_per_trade_pct: float
    #: The round trip's fees and slippage, as a fraction of the amount risked. See the
    #: module docstring: this is the number that decides whether scalping is viable.
    cost_r: float
    risk_basis: str = OF_ACCOUNT_SIZE
    #: 0.0 = every trade independent. 1.0 = the whole day is one bet repeated.
    intraday_correlation: float = 0.35
    #: Stop trading for the day once this fraction of the firm's daily allowance is spent.
    #: None means trade on regardless, which is what an undisciplined operator does and
    #: what the model should be able to show the cost of.
    daily_stop_at: float | None = 0.6
    #: Measured per-trade results in R, when this profile came from `lib/backtest.py`
    #: rather than from somebody's estimate. When present it REPLACES the win/payoff coin
    #: flip: the day is played by resampling real trades, which keeps the shape of the
    #: distribution — the occasional -1.4R gap through a stop, the rare +6R runner — that a
    #: two-point model throws away. Those tails are what breach funded accounts, so
    #: throwing them away is not a simplification, it is the flattering direction.
    empirical_r: tuple[float, ...] = ()
    #: How far the stop sits from entry, as a percentage of price. Optional because a
    #: profile can be stated purely in R, but supplying it is what lets the model check
    #: the position against the venue's leverage cap — see `implied_leverage`.
    stop_distance_pct: float | None = None
    #: Does risk sit on the books across the day boundary. This is not a label: a
    #: strategy that holds overnight may not also claim a self-imposed daily stop, because
    #: a stop somebody has to be awake to apply is not a limit. `__post_init__` refuses
    #: the combination rather than letting a profile bank protection it does not have.
    holds_overnight: bool = False

    def __post_init__(self) -> None:
        if self.trades_per_day <= 0:
            raise ValueError("trades_per_day must be positive")
        if not 0 < self.win_rate < 1:
            raise ValueError("win_rate must be strictly between 0 and 1")
        if self.payoff_ratio <= 0:
            raise ValueError("payoff_ratio must be positive")
        if not 0 < self.risk_per_trade_pct <= 100:
            raise ValueError("risk_per_trade_pct must be between 0 and 100")
        if self.cost_r < 0:
            raise ValueError("cost_r cannot be negative")
        if self.risk_basis not in RISK_BASES:
            raise ValueError(f"risk_basis must be one of {RISK_BASES}")
        if not 0 <= self.intraday_correlation <= 1:
            raise ValueError("intraday_correlation must be between 0 and 1")
        if self.daily_stop_at is not None and not 0 < self.daily_stop_at <= 1:
            raise ValueError("daily_stop_at must be a fraction of the allowance, or None")
        if self.stop_distance_pct is not None and self.stop_distance_pct <= 0:
            raise ValueError("stop_distance_pct must be positive, or None if not stated")
        if self.holds_overnight and self.daily_stop_at is not None:
            raise ValueError(
                f"{self.name} holds overnight and also claims a daily stop at "
                f"{self.daily_stop_at:.0%} of the allowance. A stop that only acts while "
                f"somebody is awake does not bound a position held through the night — "
                f"set daily_stop_at=None, or model the strategy as flat overnight"
            )

    def implied_leverage(self) -> float | None:
        """Notional as a multiple of the account, or None if the stop is not stated.

        Risk-based sizing says nothing about how much notional it takes to express that
        risk, and on a venue with a leverage cap those are different constraints. A 0.4%
        stop risking 2% of the account needs five times the account in notional; the same
        2% risk behind a 4% stop needs half of it. None is NOT "no leverage used" — it is
        "not computable from what this profile states", and the report prints it that way.
        """

        if self.stop_distance_pct is None:
            return None
        return self.risk_per_trade_pct / self.stop_distance_pct

    @property
    def edge_r(self) -> float:
        """Expected R per trade, after cost. Negative means the rest is arithmetic.

        Measured trades are already net of the costs charged in the backtest, so their mean
        is taken as it stands. Subtracting `cost_r` again would charge the fee twice.
        """

        if self.empirical_r:
            return statistics.fmean(self.empirical_r)
        return (
            self.win_rate * self.payoff_ratio
            - (1 - self.win_rate)
            - self.cost_r
        )

    @property
    def measured(self) -> bool:
        return bool(self.empirical_r)

    @property
    def expected_daily_r(self) -> float:
        return self.edge_r * self.trades_per_day

    def describe(self) -> str:
        edge = self.edge_r
        verdict = (
            "positive" if edge > 0 else
            "ZERO after cost" if edge == 0 else
            "NEGATIVE after cost — no amount of position sizing fixes this"
        )
        return "\n".join([
            f"{self.name}",
            f"  {self.description}",
            f"  {self.trades_per_day:g} trade(s)/day, {self.win_rate:.0%} win at "
            f"{self.payoff_ratio:.2f}R, costing {self.cost_r:.2f}R a round trip",
            f"  risking {self.risk_per_trade_pct:.2f}% of "
            + ("the account" if self.risk_basis == OF_ACCOUNT_SIZE else "current equity")
            + f", {self.intraday_correlation:.0%} intraday correlation",
            "  daily stop at "
            + (f"{self.daily_stop_at:.0%} of the allowance"
               if self.daily_stop_at is not None else "NONE — trades on regardless")
            + (", holds overnight" if self.holds_overnight else ", flat overnight"),
            f"  edge {edge:+.3f}R per trade ({verdict}), "
            f"{self.expected_daily_r:+.3f}R per day"
            + (f"  [MEASURED from {len(self.empirical_r)} real trades]"
               if self.measured else "  [ESTIMATED, not measured]"),
            "  implied leverage " + (
                "not computable — this profile does not state its stop distance"
                if self.implied_leverage() is None
                else f"{self.implied_leverage():.1f}x the account per position"
            ),
        ])


# --------------------------------------------------------------------------------------
# Playing a day
# --------------------------------------------------------------------------------------


#: Above this, Knuth's method underflows to a constant and would silently return a fixed
#: count rather than a draw. Nothing sane reaches it; refusing beats returning a number.
_POISSON_CEILING = 400.0


def _poisson(rng: random.Random, mean: float) -> int:
    """Knuth's method. Here rather than numpy because `requirements.txt` says a new
    dependency is a decision, and this is ten lines for one distribution."""

    if mean > _POISSON_CEILING:
        raise ValueError(
            f"trades_per_day of {mean:g} is past where this draw stays numerically "
            f"honest ({_POISSON_CEILING:g}). It would return a fixed count dressed as a "
            f"random one"
        )
    limit = math.exp(-mean)
    k, product = 0, rng.random()
    while product > limit:
        k += 1
        product *= rng.random()
    return k


def play_day(
    profile: StrategyProfile,
    rules: ChallengeRules,
    when: date,
    opening_equity: float,
    rng: random.Random,
) -> Day:
    """Play one day trade by trade, recording the running low as it goes.

    The low is generated rather than inferred because every floor in `lib/funded.py` is
    checked against it. A day summarised by its close has thrown away the only number that
    decides whether the account survived. The high is generated for the same reason, for
    the rulebooks that trail their floor on it.
    """

    equity = opening_equity
    low = high = opening_equity
    count = _poisson(rng, profile.trades_per_day)

    # One regime draw for the day. Each trade then either follows it or is drawn on its
    # own, which gives equicorrelated outcomes with `intraday_correlation` as the weight —
    # the cheapest honest way to stop a day being four independent coin flips.
    measured = profile.empirical_r
    regime_won = rng.random() < profile.win_rate
    regime_r = rng.choice(measured) if measured else 0.0

    allowance = rules.max_daily_loss_pct
    self_stop = None
    if allowance is not None and profile.daily_stop_at is not None:
        firm_floor = rules.daily_floor(opening_equity)
        assert firm_floor is not None
        self_stop = opening_equity - (opening_equity - firm_floor) * profile.daily_stop_at

    hard_floor = rules.total_floor(opening_equity)

    traded = False
    for _ in range(count):
        traded = True
        follows_the_day = rng.random() < profile.intraday_correlation

        basis = (
            rules.account_size
            if profile.risk_basis == OF_ACCOUNT_SIZE
            else max(equity, 0.0)
        )
        risk = basis * profile.risk_per_trade_pct / 100.0
        if measured:
            # Resample a real trade. Costs are already inside a measured R.
            r = regime_r if follows_the_day else rng.choice(measured)
        else:
            won = regime_won if follows_the_day else rng.random() < profile.win_rate
            r = (profile.payoff_ratio if won else -1.0) - profile.cost_r
        equity += r * risk
        low = min(low, equity)
        high = max(high, equity)

        # Two reasons to stop for the day: the operator's own buffer, and the account
        # already being gone. The second is not a strategy decision — there is nothing
        # left to trade — and continuing past it would generate days the walker would
        # then have to ignore.
        if self_stop is not None and equity <= self_stop:
            break
        if equity <= hard_floor:
            break

    return Day(when, opening_equity, high, low, equity, traded=traded)


@dataclass(frozen=True, slots=True)
class PayoutPolicy:
    """How often profit comes out, and how much of it is left behind.

    A policy, not a rule: the provider decides what MAY be withdrawn, the trader decides
    what IS. Separating them matters because the right answer inverts with the floor.

    Under a TRAILING floor that does not reset, retained profit raises the floor along with
    the balance and buys nothing, so the money is safer in your bank than in the account:
    withdraw little and often.

    Under a STATIC floor the retained profit is permanent room. The floor never moves, so
    every dollar left behind widens the gap to it forever, and the gap is what the strategy
    spends when it has a bad week. Withdrawing 100% of profit every cycle resets the account
    to the thinnest buffer it will ever have, over and over, which is why the survival curve
    across `retain_fraction` is the interesting one on Kraken's rulebook.
    """

    every_days: int = 14
    #: Of the withdrawable profit, the share left in the account rather than taken.
    retain_fraction: float = 0.0

    def __post_init__(self) -> None:
        if self.every_days < 1:
            raise ValueError("every_days must be at least one day")
        if not 0 <= self.retain_fraction < 1:
            raise ValueError(
                "retain_fraction must be at least 0 and below 1: retaining everything is "
                "not a payout policy, it is declining to be paid"
            )


def resized(profile: StrategyProfile, risk_per_trade_pct: float) -> StrategyProfile:
    """The same strategy at a different size.

    Position size is not a strategy and does not belong in a list of rival strategies. It
    is a separate question asked of whichever strategy won, and the challenge answers it
    differently from an ordinary account: size sets both how fast the target arrives and
    how likely the floor is touched on the way, and those move in opposite directions.
    """

    return replace(
        profile,
        name=f"{profile.name} @ {risk_per_trade_pct:g}%",
        risk_per_trade_pct=risk_per_trade_pct,
    )


# --------------------------------------------------------------------------------------
# Running a campaign
# --------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PathResult:
    """One account's whole life: the challenge, then the funded phase if it got there."""

    challenge: Verdict
    funded: Verdict | None
    #: The trader's 80% share of everything withdrawn, before the fee is taken off.
    gross_take: float = 0.0
    fees_paid: float = 0.0
    funded_days: int = 0

    @property
    def net_take(self) -> float:
        return self.gross_take - self.fees_paid

    @property
    def reached_funding(self) -> bool:
        return self.challenge.status == PASSED


def run_path(
    challenge: ChallengeRules,
    funded: ChallengeRules | None,
    profile: StrategyProfile,
    rng: random.Random,
    *,
    start: date,
    challenge_day_cap: int,
    funded_horizon_days: int,
    payout: PayoutPolicy,
) -> PathResult:
    """One account, from the day the fee is paid to the end of the horizon.

    A breach in the funded phase loses the ACCOUNT, not the money already withdrawn. That
    asymmetry is the whole economic case for taking payouts early and often, and the model
    exists partly to price how much survival that costs when the floor does not come back
    down after a payout.
    """

    walk = AccountWalk(challenge)
    when = start
    for _ in range(challenge_day_cap):
        settled = walk.step(play_day(profile, challenge, when, walk.equity, rng))
        when += timedelta(days=1)
        if settled is not None:
            break
    challenge_verdict = walk.verdict()

    if challenge_verdict.status != PASSED or funded is None:
        return PathResult(challenge_verdict, None, 0.0, challenge.fee, 0)

    funded_walk = AccountWalk(funded)
    gross_withdrawn = 0.0
    funded_days = 0
    for index in range(1, funded_horizon_days + 1):
        day = play_day(profile, funded, when, funded_walk.equity, rng)
        if index % payout.every_days == 0:
            take = withdrawable(funded, day.equity_close) * (1 - payout.retain_fraction)
            if take:
                day = Day(
                    day.day, day.equity_open, day.equity_high, day.equity_low,
                    day.equity_close - take, traded=day.traded, withdrawn=take,
                )
        settled = funded_walk.step(day)
        when += timedelta(days=1)
        funded_days = index
        if settled is not None:
            break
    funded_verdict = funded_walk.verdict()
    gross_withdrawn = funded_verdict.withdrawn_gross

    return PathResult(
        challenge_verdict, funded_verdict,
        gross_withdrawn * funded.profit_split_to_trader,
        challenge.fee + funded.fee,
        funded_days,
    )


@dataclass(frozen=True, slots=True)
class Campaign:
    """What happened across every simulated account for one strategy."""

    profile: StrategyProfile
    challenge: ChallengeRules
    funded: ChallengeRules | None
    paths: int
    funded_horizon_days: int
    payout: PayoutPolicy = PayoutPolicy()
    passed: int = 0
    indeterminate: int = 0
    unresolved: int = 0
    breaches: dict[str, int] = field(default_factory=dict)
    funded_breaches: dict[str, int] = field(default_factory=dict)
    days_to_pass: tuple[int, ...] = ()
    net_takes: tuple[float, ...] = ()
    funded_days: tuple[int, ...] = ()

    @property
    def pass_rate(self) -> float:
        return self.passed / self.paths if self.paths else 0.0

    @property
    def expected_net(self) -> float:
        return statistics.fmean(self.net_takes) if self.net_takes else 0.0

    @property
    def median_net(self) -> float:
        return statistics.median(self.net_takes) if self.net_takes else 0.0

    @property
    def profitable_rate(self) -> float:
        """The fraction of accounts that returned more than the fee. Not the pass rate —
        an account can pass and then breach the funded phase before its first payout."""

        if not self.net_takes:
            return 0.0
        return sum(1 for t in self.net_takes if t > 0) / len(self.net_takes)

    @property
    def median_days_to_pass(self) -> float | None:
        return statistics.median(self.days_to_pass) if self.days_to_pass else None

    def describe(self) -> str:
        lines = [self.profile.name]
        lines.append(
            f"  pass rate            {self.pass_rate:6.1%}   "
            f"({self.passed} of {self.paths})"
        )
        if self.days_to_pass:
            lines.append(
                f"  days to pass         {self.median_days_to_pass:6.0f}   median of the "
                f"accounts that passed"
            )
        for rule in (TOTAL_DRAWDOWN, DAILY_LOSS, TIME_EXPIRED):
            count = self.breaches.get(rule, 0)
            if count:
                lines.append(
                    f"  lost to {rule:<13}{count / self.paths:6.1%}"
                )
        if self.unresolved:
            lines.append(
                f"  still running        {self.unresolved / self.paths:6.1%}   "
                f"neither passed nor breached inside the day cap"
            )
        if self.indeterminate:
            # Must never be silently absorbed into a failure count: it means the model
            # produced a day the rulebook could not read, which is a bug in the model
            # rather than an outcome of the strategy.
            lines.append(
                f"  !! INDETERMINATE     {self.indeterminate}   the rulebook could not "
                f"read a generated day. This is a defect, not a result."
            )
        if self.funded is not None:
            lines.append(
                f"  net to the trader    {self.expected_net:>9,.0f} mean   "
                f"{self.median_net:>9,.0f} median   over "
                f"{self.funded_horizon_days} funded day(s)"
            )
            lines.append(
                f"  beat the fee         {self.profitable_rate:6.1%}   of all accounts "
                f"started, not of those funded"
            )
            for rule in (TOTAL_DRAWDOWN, DAILY_LOSS):
                count = self.funded_breaches.get(rule, 0)
                if count:
                    lines.append(
                        f"  funded acct lost to {rule:<14}{count:>5}   "
                        f"{count / self.passed:.0%} of funded accounts"
                        if self.passed else ""
                    )
            if self.funded_days:
                lines.append(
                    f"  funded account life  {statistics.median(self.funded_days):6.0f}   "
                    f"median days before breach or horizon"
                )
        return "\n".join(line for line in lines if line)


def simulate(
    challenge: ChallengeRules,
    profile: StrategyProfile,
    *,
    funded: ChallengeRules | None = None,
    paths: int = 5_000,
    seed: int = 20260823,
    start: date | None = None,
    challenge_day_cap: int | None = None,
    funded_horizon_days: int = 180,
    payout: PayoutPolicy | None = None,
) -> Campaign:
    """Run `paths` accounts and report what became of them.

    Seeded by default so a figure quoted in a document can be reproduced from the document.
    An unseeded model whose numbers move between runs cannot be argued with, and a number
    nobody can check is one nobody should act on.
    """

    if paths < 1:
        raise ValueError("paths must be at least one")
    payout = payout or PayoutPolicy()
    rng = random.Random(seed)
    start = start or date(2026, 9, 1)
    cap = challenge_day_cap or challenge.max_calendar_days or 60

    passed = indeterminate = unresolved = 0
    breaches: dict[str, int] = {}
    funded_breaches: dict[str, int] = {}
    days_to_pass: list[int] = []
    net_takes: list[float] = []
    funded_days: list[int] = []

    for _ in range(paths):
        result = run_path(
            challenge, funded, profile, rng,
            start=start, challenge_day_cap=cap,
            funded_horizon_days=funded_horizon_days,
            payout=payout,
        )
        status = result.challenge.status
        if status == PASSED:
            passed += 1
            days_to_pass.append(result.challenge.days_elapsed)
            if result.funded is not None and result.funded.status == BREACHED:
                rule = result.funded.breached_rule
                funded_breaches[rule] = funded_breaches.get(rule, 0) + 1
            funded_days.append(result.funded_days)
        elif status == BREACHED:
            rule = result.challenge.breached_rule
            breaches[rule] = breaches.get(rule, 0) + 1
        elif status == INDETERMINATE:
            indeterminate += 1
        else:
            unresolved += 1
        net_takes.append(result.net_take)

    return Campaign(
        profile, challenge, funded, paths, funded_horizon_days, payout,
        passed=passed, indeterminate=indeterminate, unresolved=unresolved,
        breaches=breaches, funded_breaches=funded_breaches,
        days_to_pass=tuple(days_to_pass), net_takes=tuple(net_takes),
        funded_days=tuple(funded_days),
    )
