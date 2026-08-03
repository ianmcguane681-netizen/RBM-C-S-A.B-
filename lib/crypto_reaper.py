"""The chain lane, worked to an unsigned transaction and no further, by construction.

Structurally the same as the other two lanes. What differs is where it stops and why it
cannot be persuaded to stop later.

    look     the watchlist, with identity, upgradeability and a round trip read per token
    screen   the cascade, ordered so a token that cannot be sold is refused before pricing
    gates    what no cascade stage establishes
    thesis   a person's, per token, from the register — never minted from a standing grant
    size     a SwapPlan from connectors/chain_exec, which has no way to sign

## No standing grant here, unlike arb

The arb lane mints a thesis per market from a standing authorisation, and that is
defensible there because an arb makes no claim about the fixture — the claim is that two
books disagree by more than the cost of taking both sides. Holding a token is the opposite:
it is entirely a view about that token. So this lane requires a thesis somebody wrote for
this specific asset, and a watchlist entry without one is REFUSED rather than skipped.

## Autonomy is refused twice, in two different ways

`lib.reaper.NEVER_AUTONOMOUS` contains this lane, so constructing the reaper with
`autonomous_execution=True` raises. That is a policy, and a policy is a thing somebody
changes at eleven at night.

`connectors/chain_exec` is the second refusal and the load-bearing one: it has no key path,
no signing library and no send method. An absent capability cannot be reconfigured.

## Sold, then bought — the ordering that matters

The cascade asks whether the token can be SOLD before it asks what it costs. A token that
quotes on the buy leg and not on the sell leg is the sharpest finding the chain connectors
produce, and any ordering that prices the position first risks presenting a number for
something there is no way out of.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from lib.candidates import INDETERMINATE, PASSED, REFUSED, Candidate, Stage
from lib.reaper import Reaper, Unworthy

#: Decimals of the asset the position is priced in. USDC and USDT are 6, not 18, and the
#: connectors compared raw amounts across quote assets once already.
QUOTE_DECIMALS = {"USDC": 6, "USDT": 6, "DAI": 18, "WETH": 18}

#: How far the price must rise just to break even before the round trip is called too dear.
#: A stated ceiling rather than a judgement made while looking at a chart.
MAX_BREAKEVEN_MOVE_PCT = 8.0

#: The default tolerance handed to the swap builder, in basis points.
SLIPPAGE_BPS = 50


@dataclass(frozen=True, slots=True)
class Subject:
    """One token with everything read about it, so the stages perform no I/O."""

    token: str
    stake_units: int
    quote_name: str = "USDC"
    identity: Mapping[str, Any] | None = None
    proxy: Any = None
    trip: Any = None
    reason: str = ""

    @property
    def subject(self) -> str:
        return self.token

    @property
    def symbol(self) -> str:
        reading = (self.identity or {}).get("symbol")
        return str(getattr(reading, "value", "") or "") if reading is not None else ""


@dataclass(frozen=True, slots=True)
class Reading:
    status: str
    detail: str
    blocking: bool = True

    def describe(self) -> str:
        return f"{self.status}: {self.detail}"


def screen_subject(
    subject: Subject, *, max_breakeven_move_pct: float = MAX_BREAKEVEN_MOVE_PCT
) -> Candidate:
    """Can it be identified, can it be sold, and only then what it costs."""

    from connectors.chain_costs import INDETERMINATE as TRIP_INDETERMINATE
    from connectors.chain_costs import NO_ROUTE, PRICED
    from connectors.chain_queries import INDETERMINATE as PROXY_INDETERMINATE
    from connectors.chain_queries import UPGRADEABLE

    stages: list[Stage] = []

    if not subject.identity:
        stages.append(Stage(
            "the contract answers", INDETERMINATE, disqualifying=True,
            detail=(f"nothing was read from {subject.token}"
                    + (f": {subject.reason}" if subject.reason else "")
                    + ". Not a finding that the address is empty."),
        ))
    else:
        stages.append(Stage(
            "the contract answers", PASSED, disqualifying=True,
            detail=(f"{len(subject.identity)} identity call(s) answered"
                    + (f"; symbol {subject.symbol}" if subject.symbol else "")),
        ))

    proxy_status = getattr(subject.proxy, "status", "")
    if proxy_status == UPGRADEABLE:
        stages.append(Stage(
            "the code cannot be swapped under you", REFUSED, disqualifying=True,
            detail=(f"{subject.proxy.describe()} Whoever holds the admin key can replace "
                    f"the contract you evaluated with a different one after you buy, and "
                    f"no board is watching this."),
        ))
    elif proxy_status in {"", PROXY_INDETERMINATE}:
        stages.append(Stage(
            "the code cannot be swapped under you", INDETERMINATE, disqualifying=True,
            detail=(getattr(subject.proxy, "describe", lambda: "upgradeability was not "
                            "probed")() + " This is not a finding of immutability."),
        ))
    else:
        stages.append(Stage(
            "the code cannot be swapped under you", PASSED, disqualifying=True,
            detail=subject.proxy.describe(),
        ))

    trip_status = getattr(subject.trip, "status", "")
    if trip_status == PRICED:
        stages.append(Stage(
            "there is a way out", PASSED, disqualifying=True,
            detail=(f"in via {subject.trip.entry_venue}, out via "
                    f"{subject.trip.exit_venue} at block {subject.trip.block_number}."),
        ))
        stages.append(_affordable(subject, max_breakeven_move_pct))
        return Candidate(subject.token, tuple(stages))

    if trip_status == NO_ROUTE:
        stages.append(Stage(
            "there is a way out", REFUSED, disqualifying=True,
            detail=(f"{subject.trip.reason or 'no route both ways'}. A token that can be "
                    f"bought and not sold is not a cheap position, it is a donation."),
        ))
    else:
        stages.append(Stage(
            "there is a way out", INDETERMINATE, disqualifying=True,
            detail=((getattr(subject.trip, "reason", "") or
                     "the round trip was not measured")
                    + ". This is not a finding that the trade is cheap."),
        ))
    stages.append(Stage(
        "the round trip is affordable", INDETERMINATE, disqualifying=True,
        detail="no priced round trip, so the cost of entering and leaving is unknown.",
    ))
    return Candidate(subject.token, tuple(stages))


def _affordable(subject: Subject, ceiling: float) -> Stage:
    """Breakeven move, not round-trip loss. Losing 5% needs 5.26% back to be level."""

    move = float(subject.trip.breakeven_move_pct)
    if move > ceiling:
        return Stage(
            "the round trip is affordable", REFUSED, disqualifying=True,
            detail=(f"the price must rise {move:.2f}% before the position is level, over a "
                    f"{ceiling:.2f}% ceiling. That is the cost of going in and coming "
                    f"straight back out, and it is paid whatever happens next."),
        )
    return Stage(
        "the round trip is affordable", PASSED, disqualifying=True,
        detail=(f"{subject.trip.round_trip_loss * 100:.2f}% of the stake to go in and out; "
                f"the price must rise {move:.2f}% to be level, within {ceiling:.2f}%."),
    )


def gates_for(subject: Subject, *, portfolio: Any = None) -> tuple[Reading, ...]:
    """Preconditions the cascade does not cover. Gas is not among them — see below."""

    readings: list[Reading] = []
    if portfolio is not None and not getattr(portfolio, "readable", True):
        readings.append(Reading(
            "PORTFOLIO_UNREADABLE",
            ("what is already held could not be read, so whether this adds to a position "
             "or opens one is unknown rather than new"),
        ))
    if getattr(subject.trip, "gas_price_wei", 0) in (0, None):
        readings.append(Reading(
            "GAS_PRICE_NOT_READ",
            ("the gas price was not read at the time of the round trip, so the figures "
             "exclude a cost that is real and is not small on this chain"),
        ))
    return tuple(readings)


def build_crypto_reaper(
    *,
    watchlist: Sequence[str],
    theses: Any,
    breakers: Any,
    wallet: str,
    client: Any = None,
    quote_name: str = "USDC",
    portfolio: Any = None,
    register: Any = None,
    slippage_bps: int = SLIPPAGE_BPS,
    max_breakeven_move_pct: float = MAX_BREAKEVEN_MOVE_PCT,
    deadline_seconds: int = 600,
    default_probe: float = 100.0,
    now: Callable[[], int] | None = None,
) -> Reaper:
    """The chain lane as a `Reaper`. It produces something to sign and cannot sign it.

    Constructing this with `autonomous_execution=True` raises: the lane is in
    `NEVER_AUTONOMOUS`. The adapter underneath refuses independently, which is the refusal
    that survives somebody changing their mind about the policy.
    """

    decimals = QUOTE_DECIMALS.get(quote_name, 18)

    def _stake_units(token: str) -> int:
        thesis = theses.current(token)
        amount = float(thesis.max_exposure) if thesis is not None else default_probe
        return int(amount * 10**decimals)

    def look():
        from connectors.chain_costs import round_trip
        from connectors.chain_queries import proxy_finding, token_identity

        if not getattr(theses, "readable", True):
            raise RuntimeError(
                f"the thesis register could not be read "
                f"({getattr(theses, 'reason', 'no reason recorded')}), so what is "
                f"authorised is unknown rather than nothing"
            )
        if client is None:
            raise RuntimeError(
                "no chain client is configured, so nothing was read. This is not a "
                "finding that the tokens are untradeable."
            )

        asked, answered, subjects = len(watchlist), 0, []
        for token in watchlist:
            units = _stake_units(token)
            try:
                identity = token_identity(client, token)
                proxy = proxy_finding(client, token)
                trip = round_trip(client, token, units, quote_name=quote_name)
            except Exception as error:  # noqa: BLE001 - one silent token is not a silent scan
                subjects.append(Subject(
                    token, units, quote_name,
                    reason=f"{type(error).__name__}: {error}"[:120]))
                continue
            answered += 1
            subjects.append(Subject(token, units, quote_name, identity, proxy, trip))

        if not answered:
            raise RuntimeError(
                f"the chain answered for none of {asked} watchlist entries; nothing "
                f"was read"
            )
        return subjects, asked, answered

    def size(subject: Subject, permission: Any):
        from connectors.chain_exec import NOT_BUILDABLE, UNSIGNED, build_swap_plan
        from connectors.chain_liquidity import QUOTE_TOKENS

        quote_asset = QUOTE_TOKENS.get(quote_name, "")
        if not quote_asset:
            return None

        plan = build_swap_plan(
            client, wallet=wallet, token_in=quote_asset, token_out=subject.token,
            amount_in=subject.stake_units, permission=permission,
            slippage_bps=slippage_bps, deadline_seconds=deadline_seconds, now=now)
        if plan.status == UNSIGNED:
            return plan
        if plan.status == NOT_BUILDABLE:
            # A read failed. INDETERMINATE, and the reaper's None is what says so.
            return None
        return Unworthy(f"the swap could not be planned: {plan.reason}")

    def measure(plan) -> tuple[float, float]:
        """Cash at risk, and no claimed edge — the thesis is the reason and it is a
        person's, unquantified on purpose."""

        return (plan.amount_in / 10**decimals, 0.0)

    return Reaper(
        name="crypto", lane="crypto",
        look=look,
        screen=lambda s: screen_subject(
            s, max_breakeven_move_pct=max_breakeven_move_pct),
        gates=lambda s: gates_for(s, portfolio=portfolio),
        thesis_for=lambda s: theses.current(s.token),
        size=size,
        breakers=breakers,
        measure=measure,
        register=register,
        identity=lambda s: f"crypto:{s.token.lower()}",
    )
