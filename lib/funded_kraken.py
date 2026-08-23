"""Kraken's costs, the challenge terms as currently understood, and the ways in.

`lib/funded.py` is the rulebook and `lib/funded_sim.py` is the arithmetic. Neither knows
anything about Kraken, and that separation is deliberate: the venue's fee schedule and the
programme's terms are the two things most likely to be wrong today and corrected next week,
and they should be correctable in one file without touching a line of maths.

## The terms are NOT confirmed

Nobody has yet put their name to the challenge parameters. `UNCONFIRMED_CHALLENGE` and
`UNCONFIRMED_FUNDED` carry an empty `terms_confirmed_by`, so every report built from them
says so at the top. They are placeholders shaped like the industry norm — an 8% target
against a 6% lifetime floor and a 3% daily limit — and the point of `sweep_drawdown` is
that the recommendation does not have to wait for the real number: it is computed across
the plausible range, and the range is narrow enough that the conclusion holds throughout.

When the real terms arrive, edit the two constants below, set `terms_confirmed_by` to the
name of whoever read the published rules, and re-run. Nothing else changes.

## Cost in units of risk, which is the number that decides things

Fees look negligible as a percentage of notional and are decisive as a fraction of risk.
The conversion is one line and it is the most consequential line here:

    cost_r = (2 x fee_per_side + 2 x slippage_per_side) / stop_distance

A spot scalper working a 0.4% stop at Kraken's entry taker fee pays
`(2 x 0.25 + 2 x 0.02) / 0.4` = **1.35R a round trip**. To make one unit of risk it must
first make 1.35 units to stand still, which no win rate on a symmetric payoff achieves.
That is not a tuning problem, and a model that expressed the same fee as "0.5% of notional"
would have let it pass unremarked.

Perpetual futures change the answer rather than shading it: the taker fee is roughly a
fifth of spot, so the same scalper pays about 0.3R. **Whether the programme is spot or
perps is therefore a bigger determinant of which strategies are viable than any parameter
of the strategies themselves**, and it is the first question to put to the provider.

## Fee figures are as published for the entry volume tier and are not live

They are constants in a file, not a reading from an API, and they are the tier that applies
before any volume discount. A tier improvement makes the model pessimistic, which is the
safe direction; a schedule change makes it wrong, which is why the date is recorded.
"""
from __future__ import annotations

from dataclasses import replace

from lib.funded import (
    OF_ACCOUNT_SIZE as FLOOR_OF_ACCOUNT_SIZE,
    ON_CLOSE,
    STATIC,
    TRAILING_LOCKED,
    ChallengeRules,
)
from lib.funded_sim import Campaign, StrategyProfile, simulate
from lib.thesis import AUTOMATION_PREFIXES

#: As published for the entry (lowest) 30-day volume tier, recorded 2026-08-23. Not read
#: from an API and not live; a tier improvement makes this model pessimistic.
FEES_RECORDED_ON = "2026-08-23"
SPOT_TAKER_PCT = 0.25
SPOT_MAKER_PCT = 0.15
PERP_TAKER_PCT = 0.05
PERP_MAKER_PCT = 0.02

#: What crossing the book costs beyond the fee, on a liquid major. Small, and not zero:
#: a model that sets slippage to zero is asserting a measurement it has not made.
TYPICAL_SLIPPAGE_PCT = 0.02


def cost_r(
    stop_distance_pct: float,
    fee_pct_per_side: float,
    slippage_pct_per_side: float = TYPICAL_SLIPPAGE_PCT,
) -> float:
    """What a round trip costs as a fraction of the amount risked.

    The whole reason `StrategyProfile` takes cost in R rather than in percent of notional.
    See the module docstring for the arithmetic that makes a spot scalper unviable.
    """

    if stop_distance_pct <= 0:
        raise ValueError(
            "stop_distance_pct must be positive: cost as a fraction of risk is undefined "
            "for a position with no defined risk, and defaulting it to zero would report "
            "the cheapest possible trading for the most dangerous possible position"
        )
    return 2 * (fee_pct_per_side + slippage_pct_per_side) / stop_distance_pct


# --------------------------------------------------------------------------------------
# The terms, as currently understood and not yet confirmed
# --------------------------------------------------------------------------------------

def confirm_terms(rules: ChallengeRules, by: str) -> ChallengeRules:
    """Attach the name of the person who read the provider's published rules.

    Refuses the automation prefixes, for the same reason `lib/arb.py` refuses them on a
    settlement equivalence: stating that two documents say the same thing is a reading, and
    a reading is somebody's. The model will happily run on unconfirmed terms — it says so
    on every page — but it will not let the confirmation itself be minted by whatever
    happens to be running.
    """

    name = by.strip()
    if not name:
        raise ValueError(
            "confirming the terms needs the name of the person who read the provider's "
            "published rules. Leave terms_confirmed_by empty instead: unconfirmed is a "
            "state the reports know how to print"
        )
    if any(name.lower().startswith(prefix) for prefix in AUTOMATION_PREFIXES):
        raise ValueError(
            f"'{name}' is an automation. Confirming that these parameters match the "
            f"provider's published rules is a reading of a document, and the whole value "
            f"of the confirmation is that a person did it and can be asked about it"
        )
    return replace(rules, terms_confirmed_by=name)


DEFAULT_ACCOUNT_SIZE = 10_000.0
DEFAULT_FEE = 500.0

#: Ian's stated split.
TRADER_SPLIT = 0.80


def challenge_rules(
    *,
    account_size: float = DEFAULT_ACCOUNT_SIZE,
    max_total_drawdown_pct: float = 6.0,
    profit_target_pct: float = 8.0,
    max_daily_loss_pct: float | None = 3.0,
    max_calendar_days: int | None = 45,
    min_trading_days: int = 5,
    drawdown_basis: str = STATIC,
    fee: float = DEFAULT_FEE,
    confirmed_by: str = "",
) -> ChallengeRules:
    """The evaluation phase. Every default here is an assumption until `confirmed_by`."""

    return ChallengeRules(
        name=f"Kraken challenge {account_size:,.0f} @ {max_total_drawdown_pct:g}% floor",
        account_size=account_size,
        max_total_drawdown_pct=max_total_drawdown_pct,
        profit_target_pct=profit_target_pct,
        drawdown_basis=drawdown_basis,
        trail_mark=ON_CLOSE,
        max_daily_loss_pct=max_daily_loss_pct,
        daily_loss_basis=FLOOR_OF_ACCOUNT_SIZE,
        day_boundary_utc_hour=0,
        min_trading_days=min_trading_days,
        max_calendar_days=max_calendar_days,
        profit_split_to_trader=TRADER_SPLIT,
        fee=fee,
        terms_confirmed_by=confirmed_by,
    )


def funded_rules(
    *,
    account_size: float = DEFAULT_ACCOUNT_SIZE,
    max_total_drawdown_pct: float = 6.0,
    max_daily_loss_pct: float | None = 3.0,
    withdrawal_threshold_pct: float = 1.0,
    drawdown_basis: str = TRAILING_LOCKED,
    payout_lowers_floor: bool = True,
    confirmed_by: str = "",
) -> ChallengeRules:
    """The live phase: no target, survive and take the 80%.

    `drawdown_basis` differs from the challenge on purpose. A funded account whose floor
    trails the peak is the common arrangement and it is the one that interacts badly with
    payouts, so it is the default here — the optimistic assumption belongs on the side of
    the thing being tested, not on the side of the answer.
    """

    return ChallengeRules(
        name=f"Kraken funded {account_size:,.0f} @ {max_total_drawdown_pct:g}% floor",
        account_size=account_size,
        max_total_drawdown_pct=max_total_drawdown_pct,
        profit_target_pct=None,
        drawdown_basis=drawdown_basis,
        trail_mark=ON_CLOSE,
        max_daily_loss_pct=max_daily_loss_pct,
        daily_loss_basis=FLOOR_OF_ACCOUNT_SIZE,
        min_trading_days=0,
        max_calendar_days=None,
        profit_split_to_trader=TRADER_SPLIT,
        withdrawal_threshold_pct=withdrawal_threshold_pct,
        payout_lowers_floor=payout_lowers_floor,
        fee=0.0,
        terms_confirmed_by=confirmed_by,
    )


UNCONFIRMED_CHALLENGE = challenge_rules()
UNCONFIRMED_FUNDED = funded_rules()


# --------------------------------------------------------------------------------------
# The ways this system could actually trade the account
# --------------------------------------------------------------------------------------
#
# Each profile names what in this repository would run it. That constraint is doing work:
# it excludes the strategies that model well and that nothing here can execute, and it is
# how the list stays a plan rather than a survey. Win rates and payoffs are estimates — see
# the warning at the top of lib/funded_sim.py — but the COSTS are computed from Kraken's
# published schedule and are the reason several of these are refused by arithmetic before
# any estimate is involved.

CANDIDATES: tuple[StrategyProfile, ...] = (
    StrategyProfile(
        name="spot-scalp",
        description=(
            "Many small intraday trades on spot majors, crossing the spread. The obvious "
            "way in, and the one the fee schedule refuses: 0.4% stops at spot taker fees."
        ),
        trades_per_day=12,
        win_rate=0.55,
        payoff_ratio=1.0,
        risk_per_trade_pct=0.35,
        cost_r=cost_r(0.4, SPOT_TAKER_PCT),
        intraday_correlation=0.45,
        daily_stop_at=0.6,
    ),
    StrategyProfile(
        name="perp-scalp-maker",
        description=(
            "The same idea on perpetuals, posting rather than crossing. Same edge, a fifth "
            "of the cost — the profile differs from spot-scalp in nothing but the venue "
            "and the order type."
        ),
        trades_per_day=8,
        win_rate=0.55,
        payoff_ratio=1.05,
        risk_per_trade_pct=0.35,
        cost_r=cost_r(0.8, PERP_MAKER_PCT),
        intraday_correlation=0.45,
        daily_stop_at=0.6,
    ),
    StrategyProfile(
        name="momentum-swing",
        description=(
            "Few positions, wide stops, held for days. Low win rate carried by the payoff. "
            "Holds through the daily boundary, so a bad night spends two allowances."
        ),
        trades_per_day=0.8,
        win_rate=0.38,
        payoff_ratio=3.0,
        risk_per_trade_pct=1.0,
        cost_r=cost_r(3.0, PERP_TAKER_PCT),
        intraday_correlation=0.25,
        daily_stop_at=None,
        holds_overnight=True,
    ),
    StrategyProfile(
        name="mean-reversion",
        description=(
            "Fade the extremes. Wins four times in five and gives it all back in the fifth. "
            "The classic funded-account killer: the equity curve looks immaculate right up "
            "to the day the floor is touched."
        ),
        trades_per_day=4,
        win_rate=0.78,
        payoff_ratio=0.50,
        risk_per_trade_pct=0.6,
        cost_r=cost_r(1.5, PERP_TAKER_PCT),
        intraday_correlation=0.70,
        daily_stop_at=0.6,
    ),
    StrategyProfile(
        name="funding-carry",
        description=(
            "Hold the perp against the spot and collect the funding rate. Nearly every day "
            "is a small win. Necessarily held overnight, and its whole risk is in the "
            "basis moving while it is."
        ),
        trades_per_day=0.5,
        win_rate=0.88,
        payoff_ratio=0.30,
        risk_per_trade_pct=1.5,
        cost_r=cost_r(2.0, PERP_TAKER_PCT),
        intraday_correlation=0.85,
        daily_stop_at=None,
        holds_overnight=True,
    ),
    StrategyProfile(
        name="cross-venue-arb",
        description=(
            "What lib/arbfind.py already does for bookmakers, applied to two crypto venues. "
            "Almost never wrong and almost never available — its constraint is opportunity "
            "count, not accuracy, so it fails the CLOCK rather than the floor."
        ),
        trades_per_day=0.35,
        win_rate=0.96,
        payoff_ratio=0.8,
        risk_per_trade_pct=2.0,
        cost_r=cost_r(1.0, PERP_TAKER_PCT),
        intraday_correlation=0.10,
        daily_stop_at=0.6,
    ),
    StrategyProfile(
        name="thesis-gated",
        description=(
            "What lib/crypto_reaper.py does: a written thesis per asset, few positions, "
            "conviction size. The only candidate whose decisions a person signs, and the "
            "only one whose trade count is set by how often somebody writes a thesis."
        ),
        trades_per_day=0.25,
        win_rate=0.50,
        payoff_ratio=2.6,
        risk_per_trade_pct=1.5,
        cost_r=cost_r(4.0, PERP_TAKER_PCT),
        intraday_correlation=0.20,
        daily_stop_at=None,
        holds_overnight=True,
    ),
)

BY_NAME = {profile.name: profile for profile in CANDIDATES}


# --------------------------------------------------------------------------------------
# Sweeps: the two questions that do not have a single answer yet
# --------------------------------------------------------------------------------------


def sweep_risk(
    profile: StrategyProfile,
    sizes: tuple[float, ...] = (0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0),
    *,
    challenge: ChallengeRules | None = None,
    funded: ChallengeRules | None = None,
    **kw,
) -> tuple[tuple[float, Campaign], ...]:
    """The same strategy across position sizes.

    There is an interior optimum and finding it is most of the value here. Too small and
    the clock beats you; too large and the floor does. Both failures are total, and the
    curve between them is not symmetric — overshooting the size is much worse than
    undershooting it, because a breach costs the fee and the account while a timeout costs
    only the fee.
    """

    from lib.funded_sim import resized

    challenge = challenge or challenge_rules()
    funded = funded or funded_rules()
    return tuple(
        (size, simulate(challenge, resized(profile, size), funded=funded, **kw))
        for size in sizes
    )


def sweep_drawdown(
    profile: StrategyProfile,
    floors: tuple[float, ...] = (4.0, 5.0, 6.0, 8.0, 10.0, 12.0),
    *,
    terms: dict | None = None,
    **kw,
) -> tuple[tuple[float, Campaign], ...]:
    """The same strategy across lifetime floors, because the real floor is not yet known.

    This is how the unconfirmed term is handled rather than guessed. A recommendation that
    holds across the whole plausible range does not need the exact number, and one that
    does not hold across it was never safe to make from a single assumed value.
    """

    # Everything except the floor is held constant across the sweep, including the terms
    # the caller changed on the command line. A sweep that quietly reverted to defaults for
    # the account size would compare six floors on an account nobody asked about.
    terms = dict(terms or {})
    funded_terms = {
        key: value for key, value in terms.items()
        if key in ("account_size", "max_daily_loss_pct", "confirmed_by")
    }
    return tuple(
        (
            floor,
            simulate(
                challenge_rules(max_total_drawdown_pct=floor, **terms),
                profile,
                funded=funded_rules(max_total_drawdown_pct=floor, **funded_terms),
                **kw,
            ),
        )
        for floor in floors
    )


def sweep_payout_floor(
    profile: StrategyProfile,
    *,
    challenge: ChallengeRules | None = None,
    funded_terms: dict | None = None,
    **kw,
) -> tuple[tuple[bool, Campaign], ...]:
    """What the payout term is worth, in money.

    Identical accounts, identical strategy, one term different: whether the loss floor
    comes back down when profit is withdrawn. If the difference is large, this is the line
    of the contract to read before signing it.
    """

    challenge = challenge or challenge_rules()
    funded_terms = dict(funded_terms or {})
    return tuple(
        (
            lowers,
            simulate(
                challenge, profile,
                funded=funded_rules(payout_lowers_floor=lowers, **funded_terms), **kw
            ),
        )
        for lowers in (True, False)
    )
