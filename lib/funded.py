"""The rulebook of a funded account, and whether a given equity curve survived it.

A funded-account challenge is not a trading problem with a risk limit attached. It is a
**survival problem with a profit target attached**, and the difference decides everything
downstream. An ordinary account punishes a drawdown by leaving you with less money. This
one deletes the account, the fee paid for it, and every future payout it would have made.
So the quantity worth maximising is not expected return; it is the probability of reaching
the target without ever touching the floor, and those two objectives disagree about
position size by roughly an order of magnitude.

## What this module is and is not

It is the **rules engine**: given a sequence of days, did the account pass, breach, or is it
still running. It contains no strategy, generates nothing, and has no opinion about whether
any edge exists. `lib/funded_sim.py` supplies the days, either from a simulation or, later,
from a real Kraken statement — the evaluator cannot tell the difference and must not.

## The four states, and why the fourth is not a formality

    IN_PROGRESS   the account is alive and has not yet met the target
    PASSED        target met, minimum days served, floor never touched
    BREACHED      a floor was touched, or the clock ran out
    INDETERMINATE the days do not support a verdict

`INDETERMINATE` is the one that earns its keep. A day with no recorded low is not a day
with no drawdown; a gap in the series is not a flat week. Reading either as "fine" declares
a pass on evidence that does not exist, and the same defect has appeared elsewhere in this
repository at least ten times. Evaluate against what is recorded, and say so when it is
not enough.

## The day's LOW decides, not the day's close

Every floor here is checked against the intraday low. A day that was 6% down at 04:00 and
closed flat has breached a 5% daily limit, and the account is gone whatever the close says.
Checking closes is the single most common way a backtest of a prop challenge produces a
pass rate that the real account never reproduces — it is not conservative-versus-optimistic,
it is measuring a different thing.

For that reason `equity_low` is REQUIRED, not optional. A day supplying only a close is
INDETERMINATE rather than assumed-monotone, because assuming the close is the low is
exactly the flattering direction.

## Crypto trades on Sunday, so the day boundary is a rule, not a fact

On a venue that never closes there is no natural end of day, so the firm picks one and it
matters enormously which. A position held across `day_boundary_utc_hour` splits its loss
across two daily allowances; the same position closed an hour earlier spends one. Nothing
about the strategy changed. `day_boundary_utc_hour` is therefore part of the rulebook and
not a display setting, and a strategy tuned to one boundary is not tuned to another.

## The withdrawal trap

Withdrawing profit lowers the balance. Whether that costs you anything depends on a term
most people never read: if the loss floor TRAILS the high-water mark and does not come back
down when you take money out, then every payout walks the balance toward a floor that
stayed where the peak left it. Take four payouts and the account can breach without a
single losing day. `payout_lowers_floor` is that term, `describe()` prints it, and
`lib/funded_sim.py` measures what it costs.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Sequence

IN_PROGRESS = "IN_PROGRESS"
PASSED = "PASSED"
BREACHED = "BREACHED"
INDETERMINATE = "INDETERMINATE"

#: Which floor, or which clock, ended it. Named rather than boolean for the same reason
#: `lib/sizing.py` names the binding constraint: "I was stopped by my own daily limit" and
#: "I was stopped by the account's lifetime floor" call for opposite corrections, and a
#: single BREACHED hides which one you are in.
TOTAL_DRAWDOWN = "TOTAL_DRAWDOWN"
DAILY_LOSS = "DAILY_LOSS"
TIME_EXPIRED = "TIME_EXPIRED"

#: How the lifetime floor is computed.
STATIC = "STATIC"                    # a fixed fraction below the starting balance, forever
TRAILING = "TRAILING"                # a fixed fraction below the high-water mark, forever
TRAILING_LOCKED = "TRAILING_LOCKED"  # trails up to the starting balance, then stops

#: What the high-water mark is measured on. Trailing on the intraday high is materially
#: harsher than trailing on the close: a spike you gave straight back still raises the floor.
ON_CLOSE = "ON_CLOSE"
ON_INTRADAY_HIGH = "ON_INTRADAY_HIGH"

#: What the daily allowance is a percentage OF.
OF_ACCOUNT_SIZE = "OF_ACCOUNT_SIZE"        # the same number of dollars every day
OF_DAY_START_EQUITY = "OF_DAY_START_EQUITY"  # shrinks as the account shrinks

DRAWDOWN_BASES = (STATIC, TRAILING, TRAILING_LOCKED)
TRAIL_MARKS = (ON_CLOSE, ON_INTRADAY_HIGH)
DAILY_BASES = (OF_ACCOUNT_SIZE, OF_DAY_START_EQUITY)


@dataclass(frozen=True, slots=True)
class ChallengeRules:
    """One phase of a funded programme, stated completely enough to be evaluated.

    Every term that changes the answer is a field. There is no `**kwargs`, no "sensible
    default" for a limit, and `terms_confirmed_by` is empty until a person has read the
    provider's published rules and put their name to them. An unconfirmed rulebook still
    evaluates — refusing to model until the paperwork arrives would be its own kind of
    silence — but it says so in every line of output it produces.
    """

    name: str
    account_size: float
    max_total_drawdown_pct: float
    currency: str = "USD"

    #: None means this phase has no target: a funded account you simply keep alive.
    profit_target_pct: float | None = None

    drawdown_basis: str = STATIC
    trail_mark: str = ON_CLOSE

    #: None means no daily rule at all — rarer than people assume, and worth stating
    #: explicitly rather than encoding as a very large number.
    max_daily_loss_pct: float | None = None
    daily_loss_basis: str = OF_ACCOUNT_SIZE
    day_boundary_utc_hour: int = 0

    min_trading_days: int = 0
    #: None means the phase has no deadline.
    max_calendar_days: int | None = None

    #: The trader's share of withdrawn profit. Ian's terms: 0.80.
    profit_split_to_trader: float = 0.80
    #: Profit must reach this fraction of the account before any of it may be withdrawn.
    withdrawal_threshold_pct: float = 0.0
    #: THE TERM WORTH READING. True means the loss floor follows the money out, so a
    #: payout costs no buffer. False means it stays where the high-water mark left it, and
    #: every withdrawal walks the balance closer to a floor that never comes back down.
    payout_lowers_floor: bool = True

    #: What was paid to sit the challenge. Zero for a funded phase.
    fee: float = 0.0

    #: A person who has read the provider's published rules and states these match them.
    #: Empty is UNCONFIRMED, and unconfirmed is loudly different from confirmed-as-zero.
    terms_confirmed_by: str = ""

    def __post_init__(self) -> None:
        if self.account_size <= 0:
            raise ValueError("account_size must be positive")
        if not 0 < self.max_total_drawdown_pct < 100:
            raise ValueError("max_total_drawdown_pct must be between 0 and 100 exclusive")
        if self.profit_target_pct is not None and self.profit_target_pct <= 0:
            raise ValueError("profit_target_pct must be positive, or None for no target")
        if self.max_daily_loss_pct is not None and not 0 < self.max_daily_loss_pct < 100:
            raise ValueError("max_daily_loss_pct must be between 0 and 100, or None")
        if self.drawdown_basis not in DRAWDOWN_BASES:
            raise ValueError(f"drawdown_basis must be one of {DRAWDOWN_BASES}")
        if self.trail_mark not in TRAIL_MARKS:
            raise ValueError(f"trail_mark must be one of {TRAIL_MARKS}")
        if self.daily_loss_basis not in DAILY_BASES:
            raise ValueError(f"daily_loss_basis must be one of {DAILY_BASES}")
        if not 0 <= self.day_boundary_utc_hour <= 23:
            raise ValueError("day_boundary_utc_hour must be an hour of the day")
        if not 0 < self.profit_split_to_trader <= 1:
            raise ValueError("profit_split_to_trader must be a fraction above zero")
        if self.withdrawal_threshold_pct < 0:
            raise ValueError("withdrawal_threshold_pct cannot be negative")
        if self.min_trading_days < 0:
            raise ValueError("min_trading_days cannot be negative")
        if self.max_calendar_days is not None and self.max_calendar_days < 1:
            raise ValueError("max_calendar_days must be at least one day, or None")
        if (
            self.max_calendar_days is not None
            and self.min_trading_days > self.max_calendar_days
        ):
            raise ValueError(
                f"min_trading_days {self.min_trading_days} exceeds max_calendar_days "
                f"{self.max_calendar_days}: the phase could never be passed"
            )

    # -- derived figures ---------------------------------------------------------------

    @property
    def confirmed(self) -> bool:
        return bool(self.terms_confirmed_by.strip())

    @property
    def total_drawdown_amount(self) -> float:
        return self.account_size * self.max_total_drawdown_pct / 100.0

    @property
    def target_balance(self) -> float | None:
        if self.profit_target_pct is None:
            return None
        return self.account_size * (1 + self.profit_target_pct / 100.0)

    @property
    def withdrawal_threshold_amount(self) -> float:
        return self.account_size * self.withdrawal_threshold_pct / 100.0

    def total_floor(self, high_water: float) -> float:
        """The balance at which the account is gone, given the peak reached so far."""

        if self.drawdown_basis == STATIC:
            return self.account_size - self.total_drawdown_amount
        trailed = high_water - self.total_drawdown_amount
        if self.drawdown_basis == TRAILING:
            return trailed
        # TRAILING_LOCKED: the floor climbs with the peak until it reaches the starting
        # balance and then stops, so the worst case for a profitable account is breaking
        # even rather than an ever-rising ratchet.
        return min(trailed, self.account_size)

    def daily_floor(self, day_start_equity: float) -> float | None:
        """The balance at which today alone ends it, or None if there is no daily rule."""

        if self.max_daily_loss_pct is None:
            return None
        basis = (
            self.account_size
            if self.daily_loss_basis == OF_ACCOUNT_SIZE
            else day_start_equity
        )
        return day_start_equity - basis * self.max_daily_loss_pct / 100.0

    def describe(self) -> str:
        lines = []
        if not self.confirmed:
            lines.append(
                "!! TERMS UNCONFIRMED — no person has stated that these match the "
                "provider's published rules. Every figure below is an assumption, and a "
                "result computed from an assumed rulebook is a result about the "
                "assumption."
            )
            lines.append("")
        lines.append(f"{self.name}")
        lines.append(
            f"  account            {self.account_size:,.2f} {self.currency}"
            + (f"   fee {self.fee:,.2f}" if self.fee else "")
        )
        if self.target_balance is None:
            lines.append("  profit target      none — this phase is survival only")
        else:
            lines.append(
                f"  profit target      {self.profit_target_pct:.2f}% "
                f"→ {self.target_balance:,.2f}"
            )
        floor_note = {
            STATIC: "fixed below the starting balance",
            TRAILING: "trails the peak forever",
            TRAILING_LOCKED: "trails the peak up to the starting balance, then locks",
        }[self.drawdown_basis]
        lines.append(
            f"  lifetime floor     {self.max_total_drawdown_pct:.2f}% "
            f"({self.total_drawdown_amount:,.2f}) — {floor_note}"
        )
        if self.drawdown_basis != STATIC:
            lines.append(
                f"                     measured on the {'intraday high' if self.trail_mark == ON_INTRADAY_HIGH else 'daily close'}"
            )
        if self.max_daily_loss_pct is None:
            lines.append("  daily loss         no daily rule")
        else:
            of = "the account size" if self.daily_loss_basis == OF_ACCOUNT_SIZE else "that day's opening equity"
            lines.append(
                f"  daily loss         {self.max_daily_loss_pct:.2f}% of {of}, "
                f"day ends {self.day_boundary_utc_hour:02d}:00 UTC"
            )
        lines.append(
            f"  time               min {self.min_trading_days} trading day(s), "
            + ("no deadline" if self.max_calendar_days is None
               else f"max {self.max_calendar_days} calendar day(s)")
        )
        lines.append(
            f"  payout             {self.profit_split_to_trader:.0%} of withdrawn profit "
            f"to the trader, withdrawable above {self.withdrawal_threshold_amount:,.2f} profit"
        )
        lines.append(
            "                     "
            + ("floor comes back down with the withdrawal, so a payout costs no buffer"
               if self.payout_lowers_floor
               else "floor does NOT come back down after a payout — every withdrawal "
                    "permanently spends buffer, and enough of them breach a winning "
                    "account with no losing day")
        )
        lines.append("  floors are checked against the day's LOW, never its close.")
        return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class Day:
    """One rule-day of the account, as open / high / low / close on the equity curve.

    None of the four is optional and none is defaulted. A day reporting only a close cannot
    be evaluated, and the evaluator says so rather than assuming the close was also the low
    — which would be assuming the account never dipped, on every single day.

    `equity_high` exists because a rulebook that trails the high-water mark on the intraday
    high needs it. An earlier version approximated it with the day's OPEN, which is not an
    approximation but a different quantity: it silently ignored every spike that happened
    after the bell and raised no floor for it. A term the rulebook names must be measured
    or refused, never substituted.
    """

    day: date
    equity_open: float | None
    equity_high: float | None
    equity_low: float | None
    equity_close: float | None
    #: Whether a position was actually opened. Firms count trading days, not calendar days,
    #: and a day flat in cash is not one of them.
    traded: bool = True
    #: A payout taken at the end of this day, already deducted from `equity_close`.
    withdrawn: float = 0.0

    @property
    def readable(self) -> bool:
        return None not in (
            self.equity_open, self.equity_high, self.equity_low, self.equity_close
        )


@dataclass(frozen=True, slots=True)
class Verdict:
    """What happened, why, and how far it got before it happened."""

    status: str
    rules: ChallengeRules
    breached_rule: str = ""
    #: Free text naming what a person can go and do about an INDETERMINATE.
    unreadable: str = ""
    days_elapsed: int = 0
    days_traded: int = 0
    peak_balance: float = 0.0
    final_balance: float = 0.0
    #: The floor as it stood on the last day evaluated — the number worth watching daily.
    floor_at_end: float = 0.0
    #: Cumulative payouts taken during the phase, gross of the split.
    withdrawn_gross: float = 0.0
    breach_day: date | None = None

    @property
    def trader_take(self) -> float:
        """The trader's own money out of the phase, net of what the seat cost."""

        return self.withdrawn_gross * self.rules.profit_split_to_trader - self.rules.fee

    def describe(self) -> str:
        lines = []
        if self.status == INDETERMINATE:
            lines.append(f"INDETERMINATE  {self.rules.name}: no verdict can be stated.")
            lines.append(f"  {self.unreadable}")
            lines.append(
                "  This is not a pass and not a breach. The days on hand do not decide it, "
                "and treating an unreadable day as an uneventful one is how a simulated "
                "pass rate stops describing the real account."
            )
            return "\n".join(lines)

        if self.status == BREACHED:
            reason = {
                TOTAL_DRAWDOWN: (
                    f"the lifetime floor at {self.floor_at_end:,.2f} was touched"
                ),
                DAILY_LOSS: "a single day's loss allowance was spent",
                TIME_EXPIRED: (
                    f"the deadline passed with the target unmet "
                    f"({self.final_balance:,.2f} of "
                    f"{self.rules.target_balance:,.2f})"
                    if self.rules.target_balance is not None else
                    "the deadline passed"
                ),
            }[self.breached_rule]
            when = f" on {self.breach_day.isoformat()}" if self.breach_day else ""
            lines.append(f"BREACHED  {self.rules.name}: {reason}{when}.")
            lines.append(f"  bound by: {self.breached_rule}")
        elif self.status == PASSED:
            lines.append(
                f"PASSED  {self.rules.name}: {self.final_balance:,.2f} "
                f"{self.rules.currency} after {self.days_elapsed} day(s)."
            )
        else:
            lines.append(
                f"IN_PROGRESS  {self.rules.name}: {self.final_balance:,.2f} "
                f"{self.rules.currency}, floor at {self.floor_at_end:,.2f}."
            )
            if self.rules.target_balance is not None:
                lines.append(
                    f"  {self.rules.target_balance - self.final_balance:,.2f} from target, "
                    f"{self.final_balance - self.floor_at_end:,.2f} from the floor."
                )

        lines.append(
            f"  {self.days_traded} trading day(s) of {self.days_elapsed} elapsed, "
            f"peak {self.peak_balance:,.2f}"
        )
        if self.withdrawn_gross:
            lines.append(
                f"  withdrawn {self.withdrawn_gross:,.2f} gross, trader's share "
                f"{self.withdrawn_gross * self.rules.profit_split_to_trader:,.2f}"
                + (f", less the {self.rules.fee:,.2f} fee" if self.rules.fee else "")
            )
        return "\n".join(lines)


class AccountWalk:
    """The rulebook applied one day at a time, holding the state a verdict needs.

    A class rather than a loop body because two callers need to ask the rulebook the same
    questions: `evaluate`, which walks days somebody recorded, and `lib/funded_sim.py`,
    which has to know after each generated day whether the account is still alive. Two
    implementations of "has this breached" would agree on the day they were written and
    not a month later, and the one that drifts would be the simulator — which is the one
    whose answer nobody can check against a statement.

    Everything that decides a verdict lives here. `evaluate` is a loop over `step` and
    nothing else.
    """

    __slots__ = (
        "rules", "equity", "high_water", "floor", "days_traded", "days_elapsed",
        "withdrawn_gross", "_verdict",
    )

    def __init__(self, rules: ChallengeRules) -> None:
        self.rules = rules
        self.equity = rules.account_size
        self.high_water = rules.account_size
        self.floor = rules.total_floor(rules.account_size)
        self.days_traded = 0
        self.days_elapsed = 0
        self.withdrawn_gross = 0.0
        self._verdict: Verdict | None = None

    @property
    def finished(self) -> bool:
        return self._verdict is not None

    def daily_floor(self) -> float | None:
        """Where today ends it, given where today opened. For a same-day stop-out rule."""

        return self.rules.daily_floor(self.equity)

    def _settle(self, verdict: Verdict) -> Verdict:
        self._verdict = verdict
        return verdict

    def step(self, day: Day) -> Verdict | None:
        """Apply one day. Returns a terminal Verdict, or None if the account is still alive.

        Within a day the order is: floors first, target second. A day that dipped through
        the floor at 04:00 and closed above the target did not pass — the account was
        already closed when the profit arrived. Evaluating the target first produces passes
        the real account never sees, and it is an easy ordering to get wrong because the
        close is the number in front of you.
        """

        if self._verdict is not None:
            raise ValueError(
                f"this account already finished as {self._verdict.status}; a walk does not "
                f"continue past its verdict"
            )

        if not day.readable:
            missing = [
                name for name, value in (
                    ("open", day.equity_open),
                    ("high", day.equity_high),
                    ("low", day.equity_low),
                    ("close", day.equity_close),
                ) if value is None
            ]
            return self._settle(Verdict(
                INDETERMINATE, self.rules,
                unreadable=(
                    f"day {self.days_elapsed + 1} ({day.day.isoformat()}) is missing its "
                    f"{', '.join(missing)}. Supply it, or evaluate only the days before it "
                    f"— the low in particular cannot be inferred from the close."
                ),
                days_elapsed=self.days_elapsed, days_traded=self.days_traded,
                peak_balance=self.high_water, final_balance=self.equity,
                floor_at_end=self.floor, withdrawn_gross=self.withdrawn_gross,
            ))

        rules = self.rules
        self.floor = rules.total_floor(self.high_water)
        daily_floor = rules.daily_floor(day.equity_open)

        # The low decides, never the close. The lifetime floor is tested first because it
        # is the one that cannot be recovered from.
        if day.equity_low <= self.floor:
            return self._settle(Verdict(
                BREACHED, rules, TOTAL_DRAWDOWN,
                days_elapsed=self.days_elapsed + 1, days_traded=self.days_traded,
                peak_balance=self.high_water, final_balance=day.equity_low,
                floor_at_end=self.floor, withdrawn_gross=self.withdrawn_gross,
                breach_day=day.day,
            ))
        if daily_floor is not None and day.equity_low <= daily_floor:
            return self._settle(Verdict(
                BREACHED, rules, DAILY_LOSS,
                days_elapsed=self.days_elapsed + 1, days_traded=self.days_traded,
                peak_balance=self.high_water, final_balance=day.equity_low,
                floor_at_end=daily_floor, withdrawn_gross=self.withdrawn_gross,
                breach_day=day.day,
            ))

        self.equity = day.equity_close
        self.withdrawn_gross += day.withdrawn
        self.days_elapsed += 1
        if day.traded:
            self.days_traded += 1

        # The peak the account actually reached is measured BEFORE the payout came out of
        # it: `equity_close` is already net of the withdrawal.
        mark = day.equity_close + day.withdrawn
        if rules.trail_mark == ON_INTRADAY_HIGH:
            mark = max(mark, day.equity_high)
        self.high_water = max(self.high_water, mark)

        if day.withdrawn and rules.payout_lowers_floor:
            # The floor follows the money out, never below the starting balance. Without
            # this the balance drops by the payout while the floor stays at the peak, which
            # is the term that quietly kills accounts that never had a losing day.
            self.high_water = max(rules.account_size, self.high_water - day.withdrawn)

        self.floor = rules.total_floor(self.high_water)

        # A payout can put the balance under its own floor the moment it lands, and that is
        # a breach caused by the withdrawal rather than by a trade. Checking it here rather
        # than waiting for the next day's low matters when the series ends on a payout: the
        # account would otherwise be reported alive on its last recorded day and dead in
        # the provider's system.
        if day.withdrawn and self.equity <= self.floor:
            return self._settle(Verdict(
                BREACHED, rules, TOTAL_DRAWDOWN,
                days_elapsed=self.days_elapsed, days_traded=self.days_traded,
                peak_balance=self.high_water, final_balance=self.equity,
                floor_at_end=self.floor, withdrawn_gross=self.withdrawn_gross,
                breach_day=day.day,
            ))

        target = rules.target_balance
        if target is not None:
            if self.equity >= target and self.days_traded >= rules.min_trading_days:
                return self._settle(Verdict(
                    PASSED, rules,
                    days_elapsed=self.days_elapsed, days_traded=self.days_traded,
                    peak_balance=self.high_water, final_balance=self.equity,
                    floor_at_end=self.floor, withdrawn_gross=self.withdrawn_gross,
                ))
            # A deadline only ends a phase that HAS a target. A funded account with no
            # target and a calendar limit is a horizon somebody chose to stop watching at,
            # not a failure, and reporting it as BREACHED would put a loss in the ledger
            # that nobody took.
            if (
                rules.max_calendar_days is not None
                and self.days_elapsed >= rules.max_calendar_days
            ):
                return self._settle(Verdict(
                    BREACHED, rules, TIME_EXPIRED,
                    days_elapsed=self.days_elapsed, days_traded=self.days_traded,
                    peak_balance=self.high_water, final_balance=self.equity,
                    floor_at_end=self.floor, withdrawn_gross=self.withdrawn_gross,
                    breach_day=day.day,
                ))
        return None

    def verdict(self) -> Verdict:
        """The settled verdict, or the state of an account that is still running."""

        if self._verdict is not None:
            return self._verdict
        return Verdict(
            IN_PROGRESS, self.rules,
            days_elapsed=self.days_elapsed, days_traded=self.days_traded,
            peak_balance=self.high_water, final_balance=self.equity,
            floor_at_end=self.floor, withdrawn_gross=self.withdrawn_gross,
        )


def evaluate(rules: ChallengeRules, days: Sequence[Day]) -> Verdict:
    """Walk the days in order and state what the rulebook says about them."""

    if not days:
        return Verdict(
            INDETERMINATE, rules,
            unreadable=(
                "no days were supplied. Nothing has been evaluated, which is different "
                "from an account that has not moved."
            ),
        )

    walk = AccountWalk(rules)
    for day in days:
        settled = walk.step(day)
        if settled is not None:
            return settled
    return walk.verdict()


def withdrawable(rules: ChallengeRules, equity: float) -> float:
    """Profit that may be taken out now, gross of the split. Zero below the threshold.

    It is profit above the STARTING balance that is withdrawable; the threshold only
    decides whether the tap is open yet. Withdrawing down to the starting balance and
    withdrawing down to the threshold are different policies with different survival
    consequences, and `lib/funded_sim.py` compares them rather than picking one here.
    """

    profit = equity - rules.account_size
    if profit <= 0 or profit < rules.withdrawal_threshold_amount:
        return 0.0
    return profit


def trader_share(rules: ChallengeRules, gross: float) -> float:
    return gross * rules.profit_split_to_trader
