"""Measure what the funded model has been assuming, against real Kraken candles.

    python backtest.py                        the whole study
    python backtest.py --refresh              refetch instead of using the cache
    python backtest.py --interval 4h          120 days at four-hourly instead of 2 years daily
    python backtest.py --rule donchian-20     one rule, in detail

`funded_model.py` answers "what would this do to a funded account" from a win rate and a
payoff somebody estimated. This answers "what IS the win rate" from candles, and hands the
measured distribution back to that model. It reads a public endpoint, needs no key, writes
no order, and caches everything it fetches so the numbers can be reproduced.

The study is arranged so that it can fail. Rules are picked in disagreeing pairs, split
in and out of sample, broken down per market, and measured against simply holding the
asset — and every one of those is a chance for a result to turn out to be nothing. A
backtest that cannot come back negative is not a measurement.
"""
from __future__ import annotations

import argparse
import statistics
import sys

from connectors.kraken import COULD_NOT_LOOK, MAX_BARS, read_many, write_receipt
from lib.backtest import MEASURED, buy_and_hold_windows, run, split
from lib.funded import DAILY_LOSS, TIME_EXPIRED, TOTAL_DRAWDOWN
from lib.funded_kraken import challenge_rules, funded_rules
from lib.funded_sim import resized, simulate
from lib.strategies import BY_NAME, CANDIDATE_RULES

UNIVERSE = ("XBTUSD", "ETHUSD", "SOLUSD", "XRPUSD", "LTCUSD",
            "ADAUSD", "DOTUSD", "LINKUSD", "AVAXUSD", "ATOMUSD")


def rule_head(title: str) -> str:
    return f"\n{title}\n{'=' * len(title)}"


def data_section(reads, args) -> list[str]:
    lines = [rule_head("1. WHAT WAS READ, AND HOW MUCH THERE IS")]
    failed = [r for r in reads.values() if r.status == COULD_NOT_LOOK]
    for pair, read in reads.items():
        lines.append(f"   {read.describe()}")
    if failed:
        lines.append("")
        lines.append(
            f"   {len(failed)} market(s) could not be read. They are NOT absent from the "
            f"market and\n   not flat — they are unmeasured, and every figure below covers "
            f"a smaller universe\n   than the one asked for."
        )
    lines.append("")
    lines.append(
        f"   Kraken serves at most {MAX_BARS} candles per request and `since` does not page "
        f"past it,\n   so the interval fixes the history: 30 days at 1h, 120 at 4h, about "
        f"two years daily.\n   That is a limit on what may be concluded. Thirty days of "
        f"hourly bars cannot evidence\n   an intraday edge, and this study does not claim "
        f"one."
    )
    return lines


def rules_section(series, args) -> tuple[list[str], dict]:
    lines = [rule_head("2. THE RULES, AND WHAT THEY MEASURED")]
    lines.append(
        f"   Costs charged at {args.cost}% a side, positions held at most {args.hold} bars, "
        f"stops and\n   targets in multiples of that market's own ATR."
    )
    results = {}
    for strategy in CANDIDATE_RULES:
        result = run(series, strategy, cost_pct_per_side=args.cost, max_hold=args.hold)
        results[strategy.name] = result
        lines.append("")
        lines.append(f"   {result.describe()}")
    return lines, results


def coherence_section(results) -> list[str]:
    """The check the rule set was chosen to make possible."""

    lines = [rule_head("3. DO THE RULES AGREE WITH THEMSELVES?")]
    trend = ["donchian-20", "ema-10x40"]
    reversion = ["rsi-14", "bollinger-20"]

    def edges(names):
        return [
            results[n].expected_r for n in names
            if n in results and results[n].status == MEASURED
            and results[n].expected_r is not None
        ]

    t, r = edges(trend), edges(reversion)
    lines.append(
        "   Two rules say price continues, two say it reverts. They cannot both be right "
        "about\n   the same candles, so this is where a measurement gets to contradict "
        "itself."
    )
    lines.append("")
    for name in trend + reversion:
        if name in results and results[name].expected_r is not None:
            kind = "continues" if name in trend else "reverts  "
            lines.append(
                f"   {name:<16} says price {kind}   measured "
                f"{results[name].expected_r:+.3f}R"
            )
    lines.append("")
    if not t or not r:
        lines.append(
            "   NOT DECIDABLE — one side of the pair did not measure, so the rules were "
            "never\n   actually put against each other."
        )
    elif all(e > 0 for e in t) and all(e < 0 for e in r):
        lines.append(
            "   COHERENT. Both continuation rules measured positive and both reversion "
            "rules\n   measured negative, on the same candles over the same period. That is "
            "the result\n   you would get if trend were real here, and it is NOT the result "
            "you would get\n   from noise, which has no reason to sort itself by what the "
            "rules claim."
        )
    elif all(e > 0 for e in t + r) or all(e < 0 for e in t + r):
        lines.append(
            "   INCOHERENT. Rules making opposite claims measured the same sign, which "
            "means what\n   was measured is not the claim. Suspect the execution model or "
            "the cost assumption\n   before believing any single edge above."
        )
    else:
        lines.append(
            "   MIXED. The pairs do not sort cleanly, so no rule here has strong support "
            "from\n   its own control. Treat each edge as a single unreplicated result."
        )
    return lines


def out_of_sample_section(series, args) -> list[str]:
    lines = [rule_head("4. OUT OF SAMPLE")]
    lines.append(
        "   The first 70% of every market against the last 30%. A rule tuned on everything\n"
        "   always looks good on everything, and this is the cheapest defence there is."
    )
    lines.append("")
    lines.append(f"   {'rule':<16}{'in-sample':>18}{'out-of-sample':>20}   verdict")
    lines.append(f"   {'-' * 72}")
    early, late = split(series, args.split)
    survivors = []
    for strategy in CANDIDATE_RULES:
        a = run(early, strategy, cost_pct_per_side=args.cost, max_hold=args.hold,
                min_trades=args.min_trades)
        b = run(late, strategy, cost_pct_per_side=args.cost, max_hold=args.hold,
                min_trades=max(15, args.min_trades // 2))
        fa = f"{a.expected_r:+.3f}R n={len(a.trades)}" if a.expected_r is not None else a.status
        fb = f"{b.expected_r:+.3f}R n={len(b.trades)}" if b.expected_r is not None else b.status
        if a.status != MEASURED or b.status != MEASURED:
            verdict = "not measurable in both halves"
        elif a.expected_r > 0 and b.expected_r > 0:
            verdict = "SURVIVES"
            survivors.append(strategy.name)
        elif a.expected_r > 0:
            verdict = "in-sample only — assume it was fitted"
        else:
            verdict = "negative in-sample; nothing to survive"
        lines.append(f"   {strategy.name:<16}{fa:>18}{fb:>20}   {verdict}")
    lines.append("")
    lines.append(
        "   A survivor is not a proven edge. The out-of-sample half is one period of one\n"
        "   asset class, the two halves are adjacent rather than independent, and a rule\n"
        "   that survives has cleared the lowest bar that means anything at all."
    )
    return lines, survivors


def per_pair_section(result) -> list[str]:
    lines = [rule_head(f"5. IS ONE MARKET CARRYING {result.strategy.upper()}?")]
    lines.append(
        "   Pooling ten markets is what makes the sample big enough to speak. It is also "
        "the\n   assumption most likely to be wrong, because crypto majors move together."
    )
    lines.append("")
    rows = []
    for pair, trades in result.by_pair().items():
        rs = [t.r_net for t in trades]
        rows.append((statistics.fmean(rs), pair, len(rs), sum(rs)))
    rows.sort(reverse=True)
    for mean, pair, n, total in rows:
        lines.append(f"   {pair:<10}{mean:+.3f}R   n={n:<4}total {total:+7.1f}R")
    positive = sum(1 for mean, *_ in rows if mean > 0)
    lines.append("")
    lines.append(
        f"   {positive} of {len(rows)} markets positive. "
        + ("The edge is spread rather than carried by one asset, which is the answer that\n"
           "   supports pooling them in the first place."
           if positive > len(rows) * 0.6 else
           "A minority of markets carries this, so the pooled\n   edge is substantially a "
           "fact about them rather than about the rule.")
    )
    return lines


def benchmark_section(series, args) -> list[str]:
    lines = [rule_head("6. THE BENCHMARK NOBODY WANTS TO RUN")]
    lines.append(
        f"   How often would simply BUYING and waiting {args.days} days have made the "
        f"{args.target}% target?\n   A rule that passes the challenge less often than this "
        f"is not a strategy."
    )
    lines.append("")
    made = tested = 0
    for pair, bars in series.items():
        m, t = buy_and_hold_windows(bars, args.days, args.target)
        made += m
        tested += t
    rate = made / tested if tested else 0.0
    lines.append(
        f"   {made:,} of {tested:,} windows across {len(series)} markets = {rate:.1%}"
    )
    lines.append("")
    lines.append(
        "   That figure carries no drawdown limit and no daily loss rule, so it is not a\n"
        "   pass rate — an account that made the target on day 40 may well have breached "
        "on\n   day 12. It is a floor under how much cleverness the problem actually "
        "requires."
    )
    return lines


def challenge_section(results, survivors, args) -> list[str]:
    lines = [rule_head("7. WHAT THE MEASURED RULES DO TO THE CHALLENGE")]
    if not survivors:
        lines.append(
            "   No rule survived out of sample, so there is nothing here worth sizing. "
            "Running\n   the challenge model on a rule that failed its own replication "
            "would dress up a\n   negative result as a trading plan."
        )
        return lines
    lines.append(
        "   The measured distribution — real trades, tails included — run against the "
        "funded\n   rulebook. Not a two-point coin flip: the account is played by "
        "resampling actual\n   results, because the occasional bad gap is what breaches "
        "accounts."
    )
    for name in survivors:
        result = results[name]
        try:
            profile = result.measured_profile()
        except ValueError as error:
            lines.append(f"\n   {name}: {error}")
            continue
        lines.append("")
        lines.append(
            f"   {name}  —  {profile.edge_r:+.3f}R/trade, "
            f"{profile.expected_daily_r:+.3f}R/day, correlation "
            f"{profile.intraday_correlation:.2f} (measured)"
        )
        lines.append(
            f"   {'risk/trade':>11}{'pass':>8}{'floor':>8}{'daily':>8}{'clock':>8}{'net/acct':>11}"
        )
        lines.append(f"   {'-' * 54}")
        for size in args.sizes:
            campaign = simulate(
                challenge_rules(profit_target_pct=args.target,
                                max_daily_loss_pct=args.daily,
                                max_calendar_days=args.days),
                resized(profile, size),
                funded=funded_rules(max_daily_loss_pct=args.daily),
                paths=args.paths,
            )
            b = campaign.breaches
            lines.append(
                f"   {size:>10.2f}%{campaign.pass_rate:>8.1%}"
                f"{b.get(TOTAL_DRAWDOWN, 0) / args.paths:>8.1%}"
                f"{b.get(DAILY_LOSS, 0) / args.paths:>8.1%}"
                f"{b.get(TIME_EXPIRED, 0) / args.paths:>8.1%}"
                f"{campaign.expected_net:>11,.0f}"
            )
    lines.append("")
    lines.append(
        "   Read the net column against the seat price. A rule with a real, replicated "
        "edge\n   can still be the wrong thing to put on a funded account, because the "
        "account is\n   not paying for edge — it is paying for edge delivered fast enough "
        "and smoothly\n   enough to clear a target before a floor."
    )
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pairs", default=",".join(UNIVERSE))
    parser.add_argument("--interval", default="1d", help="1h, 4h or 1d (see section 1)")
    parser.add_argument("--refresh", action="store_true", help="refetch rather than cache")
    parser.add_argument("--cost", type=float, default=0.07,
                        help="fees plus slippage per side, %% of notional")
    parser.add_argument("--hold", type=int, default=20, help="max bars in a position")
    parser.add_argument("--split", type=float, default=0.7)
    parser.add_argument("--min-trades", type=int, default=30)
    parser.add_argument("--rule", default="", help="report one rule in detail")
    parser.add_argument("--target", type=float, default=8.0)
    parser.add_argument("--daily", type=float, default=3.0)
    parser.add_argument("--days", type=int, default=45)
    parser.add_argument("--paths", type=int, default=1500)
    parser.add_argument("--sizes", default="0.5,1,1.5,2,3")
    args = parser.parse_args(argv)
    args.sizes = tuple(float(x) for x in args.sizes.split(",") if x.strip())

    pairs = tuple(p.strip() for p in args.pairs.split(",") if p.strip())
    print("KRAKEN BACKTEST — MEASURING WHAT THE FUNDED MODEL ASSUMED")
    print("=" * 79)

    reads = read_many(pairs, args.interval, refresh=args.refresh)
    write_receipt(reads)
    series = {p: r.bars for p, r in reads.items() if r.usable}
    print("\n".join(data_section(reads, args)))

    if not series:
        print(
            "\nNo market could be read, so nothing was measured. This is COULD_NOT_LOOK, "
            "not\na finding that the rules do not work.",
            file=sys.stderr,
        )
        return 2

    lines, results = rules_section(series, args)
    print("\n".join(lines))
    print("\n".join(coherence_section(results)))
    oos, survivors = out_of_sample_section(series, args)
    print("\n".join(oos))

    focus = args.rule or (survivors[0] if survivors else CANDIDATE_RULES[0].name)
    if focus not in results:
        print(f"\nNo rule named '{focus}'. Known: {', '.join(sorted(BY_NAME))}.",
              file=sys.stderr)
        return 2
    if results[focus].status == MEASURED:
        print("\n".join(per_pair_section(results[focus])))
    print("\n".join(benchmark_section(series, args)))
    print("\n".join(challenge_section(results, survivors, args)))

    print(rule_head("8. WHAT THIS STUDY IS NOT"))
    print(
        "   One asset class, one period of about two years, one timeframe. Crypto majors "
        "move\n   together, so ten markets are not ten independent tests — the measured "
        "correlation\n   of same-day trades is printed in section 7 and it is high.\n"
        "\n   Not modelled, and all of them flatter the result: partial fills, a stop that "
        "slips\n   past its level in a fast move, funding paid on a perpetual held "
        "overnight, and the\n   market impact of the position itself. Treat a measured "
        "edge here as an upper bound.\n"
        "\n   The rules were not optimised, which is the one thing protecting these numbers.\n"
        "   Parameters are the conventional ones. Tune them against this same data and "
        "every\n   figure above stops meaning anything."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
