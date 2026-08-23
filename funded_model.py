"""The paper model for a Kraken funded account: which way in, at what size, for what.

    python funded_model.py                    the whole comparison
    python funded_model.py --paths 20000      more accounts, tighter numbers
    python funded_model.py --strategy thesis-gated --sizes 0.5,1,1.5,2
    python funded_model.py --account 25000 --drawdown 5 --target 10 --fee 900

Nothing here touches a key, a venue or a balance. It simulates accounts against the
rulebook in `lib/funded.py` and prints what became of them, and the only thing it can cost
is the electricity.

**The terms are assumptions until somebody confirms them.** Pass `--confirmed-by "Name"`
once a person has read the provider's published rules and states these match; until then
every section says so, because a result computed from an assumed rulebook is a result about
the assumption. `--drawdown-sweep` is the answer to not knowing yet: it runs the range
rather than guessing a point in it.
"""
from __future__ import annotations

import argparse
import sys

from lib.funded import DAILY_LOSS, TIME_EXPIRED, TOTAL_DRAWDOWN
from lib.funded_kraken import (
    CANDIDATES,
    BY_NAME,
    FEES_RECORDED_ON,
    PERP_MAKER_PCT,
    PERP_TAKER_PCT,
    SPOT_TAKER_PCT,
    challenge_rules,
    confirm_terms,
    funded_rules,
    sweep_drawdown,
    sweep_payout_floor,
    sweep_risk,
)
from lib.funded_sim import simulate

RULE_LABEL = {
    TOTAL_DRAWDOWN: "floor",
    DAILY_LOSS: "daily",
    TIME_EXPIRED: "clock",
}


def rule(title: str) -> str:
    return f"\n{title}\n{'=' * len(title)}"


def comparison(challenge, funded, args) -> list[str]:
    """Every candidate against the same rulebook, ranked by what the trader keeps."""

    lines = [rule("1. THE WAYS IN, RANKED BY WHAT THE TRADER KEEPS")]
    lines.append(
        f"   {args.paths:,} accounts each, seed {args.seed}, "
        f"{args.horizon} funded days, payout every {args.payout_every}."
    )
    lines.append("")
    lines.append(
        f"   {'strategy':<20}{'edge/day':>10}{'pass':>8}"
        f"{'floor':>8}{'daily':>8}{'clock':>8}{'net/acct':>11}{'beat fee':>10}"
    )
    lines.append(f"   {'-' * 83}")

    results = []
    for profile in CANDIDATES:
        campaign = simulate(
            challenge, profile, funded=funded,
            paths=args.paths, seed=args.seed,
            funded_horizon_days=args.horizon,
            payout_every_days=args.payout_every,
        )
        results.append(campaign)

    for campaign in sorted(results, key=lambda c: c.expected_net, reverse=True):
        breaches = campaign.breaches
        lines.append(
            f"   {campaign.profile.name:<20}"
            f"{campaign.profile.expected_daily_r:>+9.2f}R"
            f"{campaign.pass_rate:>8.1%}"
            f"{breaches.get(TOTAL_DRAWDOWN, 0) / args.paths:>8.1%}"
            f"{breaches.get(DAILY_LOSS, 0) / args.paths:>8.1%}"
            f"{breaches.get(TIME_EXPIRED, 0) / args.paths:>8.1%}"
            f"{campaign.expected_net:>11,.0f}"
            f"{campaign.profitable_rate:>10.1%}"
        )

    lines.append("")
    lines.append(
        "   'net/acct' is the mean the trader keeps per account STARTED — the 80% share of "
        "what\n   was withdrawn, less the fee, averaged over the accounts that died as well "
        "as the ones\n   that did not. It is the only column that answers 'should we buy a "
        "seat'."
    )
    dead = [c for c in results if c.profile.edge_r <= 0]
    if dead:
        lines.append("")
        lines.append(
            "   Refused by arithmetic before any simulation: "
            + ", ".join(c.profile.name for c in dead) + "."
        )
        lines.append(
            "   Each loses money per trade after cost. A negative edge is not a sizing "
            "problem, a\n   discipline problem or a bad run, and no risk setting in section "
            "2 rescues one."
        )
    return lines, results


def sizing(best, args) -> list[str]:
    lines = [rule(f"2. HOW MUCH, FOR {best.name.upper()}")]
    lines.append(
        "   Size sets both how fast the target arrives and how likely the floor is touched\n"
        "   on the way. Both failures are total, so there is an interior optimum rather "
        "than\n   a direction to push in."
    )
    lines.append("")
    lines.append(f"   {'risk/trade':>11}{'pass':>8}{'floor':>8}{'clock':>8}{'days':>7}{'net/acct':>11}")
    lines.append(f"   {'-' * 53}")
    swept = sweep_risk(
        best, tuple(args.sizes),
        challenge=challenge_rules(
            account_size=args.account, max_total_drawdown_pct=args.drawdown,
            profit_target_pct=args.target, max_daily_loss_pct=args.daily,
            max_calendar_days=args.days, fee=args.fee,
        ),
        funded=funded_rules(
            account_size=args.account, max_total_drawdown_pct=args.drawdown,
            max_daily_loss_pct=args.daily,
        ),
        paths=args.paths, seed=args.seed,
        funded_horizon_days=args.horizon, payout_every_days=args.payout_every,
    )
    for size, campaign in swept:
        days = campaign.median_days_to_pass
        lines.append(
            f"   {size:>10.2f}%{campaign.pass_rate:>8.1%}"
            f"{campaign.breaches.get(TOTAL_DRAWDOWN, 0) / args.paths:>8.1%}"
            f"{campaign.breaches.get(TIME_EXPIRED, 0) / args.paths:>8.1%}"
            f"{(f'{days:.0f}' if days else '—'):>7}"
            f"{campaign.expected_net:>11,.0f}"
        )
    top = max(swept, key=lambda pair: pair[1].expected_net)
    lines.append("")
    lines.append(
        f"   Best of those tried: {top[0]:g}% of the account per trade, "
        f"{top[1].expected_net:,.0f} net per account."
    )
    lines.append(
        "   Overshooting is worse than undershooting and the curve is not symmetric: a "
        "breach\n   costs the fee AND the account, a timeout costs only the fee. When in "
        "doubt, the\n   smaller size."
    )
    return lines


def drawdown_sensitivity(best, args) -> list[str]:
    lines = [rule("3. THE FLOOR WE HAVE NOT CONFIRMED YET")]
    lines.append(
        "   The lifetime drawdown limit is the term nobody has read off the provider's "
        "page.\n   Rather than guess it, here is the answer across the plausible range."
    )
    lines.append("")
    lines.append(f"   {'floor':>7}{'pass':>8}{'net/acct':>11}   verdict")
    lines.append(f"   {'-' * 50}")
    for floor, campaign in sweep_drawdown(
        best, tuple(args.floors),
        terms={
            "account_size": args.account, "profit_target_pct": args.target,
            "max_daily_loss_pct": args.daily, "max_calendar_days": args.days,
            "fee": args.fee, "confirmed_by": args.confirmed_by,
        },
        paths=args.paths, seed=args.seed,
        funded_horizon_days=args.horizon, payout_every_days=args.payout_every,
    ):
        verdict = "worth a seat" if campaign.expected_net > 0 else "do not buy"
        lines.append(
            f"   {floor:>6.1f}%{campaign.pass_rate:>8.1%}"
            f"{campaign.expected_net:>11,.0f}   {verdict}"
        )
    lines.append("")
    lines.append(
        "   Read the column, not a row. If the verdict is the same the whole way down, the\n"
        "   exact term does not need to be known before deciding. If it flips, it does, and\n"
        "   the flip point is the number to go and check."
    )
    return lines


def payout_term(best, args) -> list[str]:
    lines = [rule("4. THE ONE LINE OF THE CONTRACT WORTH READING")]
    lines.append(
        "   When profit is withdrawn the balance falls. Whether the loss floor falls with "
        "it\n   is a term, and it is usually not the headline one."
    )
    lines.append("")
    for lowers, campaign in sweep_payout_floor(
        best,
        challenge=challenge_rules(
            account_size=args.account, max_total_drawdown_pct=args.drawdown,
            profit_target_pct=args.target, max_daily_loss_pct=args.daily,
            max_calendar_days=args.days, fee=args.fee,
        ),
        funded_terms={
            "account_size": args.account, "max_total_drawdown_pct": args.drawdown,
            "max_daily_loss_pct": args.daily,
        },
        paths=args.paths, seed=args.seed,
        funded_horizon_days=args.horizon, payout_every_days=args.payout_every,
    ):
        label = (
            "floor follows the money out" if lowers
            else "floor stays at the peak"
        )
        life = campaign.funded_days
        median_life = (
            f"{sorted(life)[len(life) // 2]:.0f} days" if life else "—"
        )
        lines.append(
            f"   {label:<32}net {campaign.expected_net:>9,.0f}   "
            f"funded account lives {median_life}"
        )
    lines.append("")
    lines.append(
        "   If those two numbers differ materially, the payout schedule is not an "
        "administrative\n   detail — it is a risk parameter, and taking money out on the "
        "wrong terms breaches a\n   winning account without a single losing day."
    )
    return lines


def caveats() -> list[str]:
    return [
        rule("5. WHAT THIS IS NOT"),
        "   These are simulated returns from an ASSUMED per-trade distribution. Nothing "
        "here is\n   evidence that any of these strategies has an edge. Every win rate and "
        "payoff above is\n   somebody's estimate, and the model computes their consequences "
        "exactly — if the\n   estimate is wrong the output is wrong in the same direction, "
        "with more decimals.",
        "",
        "   What survives a wrong estimate is the structural half: that cost in units of "
        "risk\n   decides which strategies are possible at all, that size has an interior "
        "optimum,\n   that a payout can breach a winning account. Those are arithmetic on "
        "the rulebook.",
        "",
        "   Not modelled, all of which push against the trader: slippage that widens when "
        "it\n   matters, a stop gapping through on a Sunday wick, the exchange unreachable "
        "with a\n   position open, correlation across days, and any decay in the edge over "
        "the horizon.",
        "",
        f"   Kraken fees recorded {FEES_RECORDED_ON} at the entry volume tier: spot taker "
        f"{SPOT_TAKER_PCT}%,\n   perp taker {PERP_TAKER_PCT}%, perp maker {PERP_MAKER_PCT}%. "
        "Constants in a file, not a live read.",
        "",
        "   FIRST QUESTION FOR THE PROVIDER: is the account spot or perpetual futures? At "
        "these\n   fee schedules that one answer decides more about which strategies are "
        "viable than\n   every parameter of the strategies put together.",
    ]


def parse_list(text: str) -> tuple[float, ...]:
    return tuple(float(part) for part in text.split(",") if part.strip())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--paths", type=int, default=4000,
                        help="accounts simulated per strategy (default 4000)")
    parser.add_argument("--seed", type=int, default=20260823,
                        help="seeded so a quoted figure can be reproduced")
    parser.add_argument("--account", type=float, default=10_000.0)
    parser.add_argument("--drawdown", type=float, default=6.0,
                        help="lifetime loss floor, %% of the account")
    parser.add_argument("--target", type=float, default=8.0,
                        help="profit target to pass, %% of the account")
    parser.add_argument("--daily", type=float, default=3.0,
                        help="daily loss allowance, %% of the account")
    parser.add_argument("--days", type=int, default=45,
                        help="calendar days allowed for the challenge")
    parser.add_argument("--fee", type=float, default=500.0)
    parser.add_argument("--horizon", type=int, default=180,
                        help="funded days simulated after a pass")
    parser.add_argument("--payout-every", type=int, default=14,
                        help="days between withdrawals in the funded phase")
    parser.add_argument("--strategy", default="",
                        help="name to carry into sections 2-4 (default: the best earner)")
    parser.add_argument("--sizes", type=parse_list, default=(0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0))
    parser.add_argument("--floors", type=parse_list, default=(4.0, 5.0, 6.0, 8.0, 10.0, 12.0))
    parser.add_argument("--confirmed-by", default="",
                        help="the person who read the provider's published rules")
    args = parser.parse_args(argv)

    challenge = challenge_rules(
        account_size=args.account, max_total_drawdown_pct=args.drawdown,
        profit_target_pct=args.target, max_daily_loss_pct=args.daily,
        max_calendar_days=args.days, fee=args.fee,
    )
    funded = funded_rules(
        account_size=args.account, max_total_drawdown_pct=args.drawdown,
        max_daily_loss_pct=args.daily,
    )
    if args.confirmed_by:
        challenge = confirm_terms(challenge, args.confirmed_by)
        funded = confirm_terms(funded, args.confirmed_by)

    print("KRAKEN FUNDED ACCOUNT — PAPER MODEL")
    print("=" * 79)
    print()
    print(challenge.describe())
    print()
    print(funded.describe())

    lines, results = comparison(challenge, funded, args)
    print("\n".join(lines))

    if args.strategy:
        if args.strategy not in BY_NAME:
            print(
                f"\nNo candidate named '{args.strategy}'. Known: "
                f"{', '.join(sorted(BY_NAME))}.",
                file=sys.stderr,
            )
            return 2
        best = BY_NAME[args.strategy]
    else:
        viable = [c for c in results if c.profile.edge_r > 0]
        if not viable:
            print(
                "\nNo candidate has a positive edge after cost, so there is nothing to "
                "size.\nSections 2 to 4 are skipped rather than run on a losing strategy."
            )
            print("\n".join(caveats()))
            return 0
        best = max(viable, key=lambda c: c.expected_net).profile

    print("\n".join(sizing(best, args)))
    print("\n".join(drawdown_sensitivity(best, args)))
    print("\n".join(payout_term(best, args)))
    print("\n".join(caveats()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
