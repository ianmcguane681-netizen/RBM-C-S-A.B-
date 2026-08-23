"""What the measured rule says right now, on your phone.

    python signals.py                     scan and print
    python signals.py --send              scan and send to Telegram and Discord
    python signals.py --send --quiet-ok   send even when nothing is signalling
    python signals.py --rule ema-10x40 --risk 1.5

Reads Kraken's public candles and order book, runs a rule that survived
`docs/kraken-backtest.md`, sizes what it finds against a ring-fence, and puts it on a
phone. **It places nothing.** There is no key path in this command and no broker is
constructed; `connectors/kraken_exec.py` is the thing that can send, it is reached through
`lib/placing.py` so the mode and the breakers get their say, and it is not imported here.

Set up a channel by hand, once:

    ~/.telegram/bot_token   and   ~/.telegram/chat_id      (mode 600)
    ~/.discord/webhook                                     (mode 600)

Either alone is fine; both is better, and the reason is `--quiet-ok` below. Never paste a
token into a chat and never put one in this repository.

## Silence is the thing this command is careful about

A scanner that only messages you when it finds something has a defect in its quietest
state: no message means "nothing found", "the scan died", "the notifier broke" and "six
markets could not be read", and the flattering reading is the one a person adopts.

So a scan that reads every market and finds nothing can still say so — that is
`--quiet-ok`, and it is what makes silence mean something. A scan that could not READ a
market says which, always, because an unread market is not a quiet one.
"""
from __future__ import annotations

import argparse
import sys

from connectors.kraken import read_depth, read_many
from lib.breakers import Ringfence
from lib.kraken_lane import describe_scan, scan
from lib.notify import (
    ALL_SENT,
    NOT_CONFIGURED,
    Channels,
    scan_silence_message,
    signal_message,
)
from lib.strategies import BY_NAME

UNIVERSE = ("XBTUSD", "ETHUSD", "SOLUSD", "XRPUSD", "LTCUSD",
            "ADAUSD", "DOTUSD", "LINKUSD", "AVAXUSD", "ATOMUSD")

#: The rule that survived in and out of sample in docs/kraken-backtest.md. Changing this
#: default should follow a re-run of `python backtest.py`, not a hunch.
DEFAULT_RULE = "donchian-20"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pairs", default=",".join(UNIVERSE))
    parser.add_argument("--interval", default="1d")
    parser.add_argument("--rule", default=DEFAULT_RULE)
    parser.add_argument("--balance", type=float, default=10_000.0,
                        help="the ring-fenced balance this lane may risk")
    parser.add_argument("--risk", type=float, default=1.0,
                        help="%% of the ring-fence risked per position")
    parser.add_argument("--slippage", type=float, default=0.5,
                        help="%% of mid within which the position must be exitable")
    parser.add_argument("--send", action="store_true",
                        help="deliver to every configured channel")
    parser.add_argument("--quiet-ok", action="store_true",
                        help="send a message even when nothing is signalling")
    parser.add_argument("--cached", action="store_true",
                        help="use cached candles rather than refetching")
    args = parser.parse_args(argv)

    if args.rule not in BY_NAME:
        print(f"No rule named {args.rule!r}. Known: {', '.join(sorted(BY_NAME))}.",
              file=sys.stderr)
        return 2
    strategy = BY_NAME[args.rule]

    pairs = tuple(p.strip() for p in args.pairs.split(",") if p.strip())
    reads = read_many(pairs, args.interval, refresh=not args.cached)
    series = {p: r.bars for p, r in reads.items() if r.usable}
    blind = tuple(p for p, r in reads.items() if not r.usable)

    ring = Ringfence("kraken", args.balance, currency="USD")
    signals = scan(
        series, strategy,
        balance=args.balance, risk_pct=args.risk,
        per_position_limit=ring.per_position_limit,
        depth_reader=lambda pair: read_depth(pair, slippage_pct=args.slippage),
        slippage_pct=args.slippage,
    )

    print(f"KRAKEN SIGNALS — {strategy.name}")
    print("=" * 70)
    print(describe_scan(signals, scanned=len(series), blind=blind))
    print()
    print("NOTHING HAS BEEN PLACED. This command has no broker and no key path.")

    if not args.send:
        return 0

    channels = Channels.from_home()
    actionable = [s for s in signals if s.actionable]

    if not actionable:
        if not args.quiet_ok:
            print("\nNothing to send. Use --quiet-ok to have silence confirmed instead.")
            return 0
        subject, body = scan_silence_message(len(series), blind)
        broadcast = channels.send(subject, body)
        print(f"\n{broadcast.describe()}")
        return 0 if broadcast.status in {ALL_SENT, NOT_CONFIGURED} else 1

    worst = 0
    print()
    for signal in actionable:
        subject, body = signal_message(signal, ring_balance=args.balance)
        broadcast = channels.send(subject, body)
        print(broadcast.describe())
        if broadcast.status not in {ALL_SENT, NOT_CONFIGURED}:
            # A delivery that partly failed is a fact about the notifier, and the exit code
            # is how a cron job finds out about it.
            worst = 1
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
