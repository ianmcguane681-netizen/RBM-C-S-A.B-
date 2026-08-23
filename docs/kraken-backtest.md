# What the candles actually say

**Built 2026-08-23.** `funded_model.py` asked what a strategy would do to a funded account
given a win rate somebody estimated. This is where the estimate stops. It reads real Kraken
candles, runs concrete rules over them, and hands the measured distribution back — so the
challenge model is driven by trades that happened rather than by numbers that were typed.

```bash
python backtest.py                     # the whole study, ~90 seconds
python backtest.py --refresh           # refetch instead of using the cache
python backtest.py --rule ema-10x40    # one rule in detail
```

Public endpoint, no key, no order. Everything fetched is cached so the figures reproduce;
`data/kraken.receipt.json` records which candles produced them.

## The answer, first

**A real trend edge exists in this data. It is not strong enough to buy a seat on.**

Two rules that say price continues both measured positive and both survived out of sample.
Two rules that say price reverts both measured negative. That coherence is the strongest
thing in the study. But run the measured distribution against the challenge rulebook and
the best case is `ema-10x40` at 2% risk: **43.1% pass, +$84 net per account against a $500
seat.** Essentially break-even, and that is before the four things the backtest does not
charge for.

So the recommendation is **do not buy a seat yet**, and the study says precisely what would
have to change. That is what a tester is for. A backtest that cannot come back negative is
not a measurement.

## The sample, and its ceiling

Kraken serves at most 720 candles per request and `since` does not page past it. The
interval therefore fixes the history: 30 days at 1h, 120 at 4h, about two years daily.

**This is a limit on what may be concluded, not an inconvenience.** Thirty days of hourly
bars cannot evidence an intraday edge, so this study does not claim one — and that single
constraint decides the shape of everything below. Ten USD majors × 721 daily candles =
**7,210 asset-days over 2024-09-02 to 2026-08-23**. What can be measured here is a
daily-timeframe swing system. Nothing faster.

Deeper intraday history would mean rebuilding candles from the Trades endpoint, a thousand
trades per call — thousands of requests against a free public API for one extra month.
Recorded in `connectors/kraken.py` so the next person does not assume it was overlooked.

## How the study is arranged so it can fail

Four independent chances for a result to turn out to be nothing:

**Rules chosen in disagreeing pairs.** Two say price continues, two say it reverts. They
cannot both be right about the same candles. If they had all measured the same sign, what
was measured would not be the claim — it would be the execution model or the cost
assumption, and no single edge would be believable.

**Look-ahead prevented by absence.** The engine does not hand a strategy the series and ask
it to be careful; it hands over `bars[:i+1]` and executes at `bars[i+1].open`. The future is
not off-limits, it is not there. Same move as `connectors/chain_exec.py` having no signing
method: an absent capability cannot be misused, and a policy about a present one is a thing
somebody edits at eleven at night.

**Out of sample.** First 70% against last 30%.

**The benchmark nobody wants to run.** Simply buying and waiting 45 days made +8% in
**28.5%** of the 6,760 windows tested. A rule that passes less often than that is not a
strategy.

Plus one honest convention: when a single candle reaches both the stop and the target, no
ordering is knowable, so **the stop is taken and the trade is counted as ambiguous.** The
ambiguous fraction prints beside every result, and above 25% the result is marked
untrustworthy at that timeframe. On daily bars it ran at 0.3% — the convention is carrying
almost nothing here, which is exactly what you want to be able to say.

## What measured

| rule | claim | edge/trade | win | payoff | out of sample |
|---|---|---|---|---|---|
| `ema-10x40` | continues | **+0.354R** | 44.8% | 2.12R | **survives** |
| `donchian-20` | continues | **+0.166R** | 42.6% | 1.77R | **survives** |
| `volbreak-20` | repricing | +0.111R | 34.1% | 2.28R | in-sample only — assume fitted |
| `rsi-14` | reverts | −0.032R | 39.7% | 1.43R | negative in-sample |
| `bollinger-20` | reverts | −0.099R | 36.2% | 1.46R | negative in-sample |

**Coherent.** Both continuation rules positive, both reversion rules negative, same candles,
same period. That is the result you get if trend is real here, and it is not the result
noise gives — noise has no reason to sort itself by what the rules claim.

`donchian-20` is positive in 8 of 10 markets (best XRP +0.473R, worst DOT −0.133R), so the
pooled edge is spread rather than carried by one asset.

## The philosophy, since that is what a strategy actually is

The rule that survived best, stated as a belief rather than as parameters:

> **Price continues.** A market making a new N-day high has no holder above it sitting on a
> loss and waiting to get out even, so the supply that normally caps a rally is absent. The
> other side of the trade is somebody taking profit early, or shorting a move they think has
> gone too far — and both are systematically wrong in an asset class with no valuation
> anchor to be too far from.
>
> **It stops working when the market ranges.** Every breakout then reverses and the rule
> pays a stop for each one, which is why its losing runs are long and its winning trades are
> few and large. A 42.6% win rate is not a flaw in it; it is the shape of the thing.

That last property is exactly what a funded account punishes, which is finding 2 below.

Every rule in `lib/strategies.py` carries its philosophy in the same form — what it believes,
who is on the other side, and what would have to change for the edge to stop existing — and
the report prints it beside the measured numbers. **A measured edge with no story is a
pattern found by looking, and enough looking finds patterns in noise. A story with no
measurement is an opinion.** Neither is worth a funded account alone.

## Why a real edge still fails the challenge

### 1. The daily loss limit does most of the killing

`donchian-20` at 2% risk, measured distribution, 1,500 accounts:

| | pass | lost to floor | lost to daily | lost to clock | net |
|---|---|---|---|---|---|
| with a 3% daily limit | 38.3% | 16.0% | **39.1%** | 6.5% | **−247** |
| with no daily limit | 50.3% | 31.7% | 0.0% | 18.0% | **+204** |

That one term is the difference between losing and making money. And these are daily-bar
strategies, so **every position is held overnight and no self-imposed daily stop can defend
it** — the model refuses to let a profile claim both, because a stop somebody has to be
awake to apply is not a limit.

This is the third time the daily limit has come out as the decisive unknown. It is the
question to put to the provider.

### 2. The edge is real but too slow

+0.067R per day for `donchian-20`. Reaching 8% in 45 days needs roughly 0.18R per day at 1%
risk, so the rule must be sized up — and sizing up is what breaches the floor. That is the
interior optimum from the funded model, arriving from the other direction: at 0.5% risk 95%
of accounts run out of clock, at 3% risk 96% breach.

Even with the daily limit removed and the challenge made easier — 5% target, 90 days — the
best net is +$386 on a $500 seat. Marginal.

### 3. Ten crypto majors are not ten independent bets

Same-day trades agree far more than chance: **measured correlation 0.66** for `donchian-20`,
against the 0.35 the estimated profiles had been guessing. When a breakout rule is wrong it
tends to be wrong everywhere at once, and that is what spends a daily allowance in one
sitting.

Correlation is real but second-order here: forcing it to zero moves net from −247 to −150.
Still negative. Worth knowing which of your problems is the big one.

## What would have to change

In the order that would matter:

1. **No daily loss limit** (or one large enough not to bind). Turns −247 into +204 on its own.
2. **A faster edge, or a longer deadline.** The measured rule needs about three times the
   daily R it produces to clear 8% in 45 days at a survivable size.
3. **Genuinely uncorrelated markets.** Worth something, but the smallest of the three.

## What this study is not

One asset class, one period of about two years, one timeframe, and the two out-of-sample
halves are adjacent rather than independent. A rule that survived has cleared the lowest bar
that means anything, not a high one.

Not modelled, and every one flatters the result:

    partial fills
    a stop that slips past its level in a fast move
    funding paid on a perpetual held overnight
    the market impact of the position itself

Treat every measured edge here as an upper bound.

**The rules were not optimised, and that is the one thing protecting these numbers.**
Parameters are the conventional ones — 20-day Donchian, 10/40 EMA, 14-period RSI. Tune them
against this same data and every figure above stops meaning anything.

## Where it lives

```
connectors/kraken.py   public OHLC, three states, the 720-candle ceiling, the cache
lib/backtest.py        the engine: windowed execution, ambiguity, out-of-sample, benchmark
lib/strategies.py      five rules, each carrying the belief that would have to be true
backtest.py            the CLI that prints the eight sections
tests/test_backtest.py 28 tests, all offline
```

`data/kraken/` is gitignored bulk; `data/kraken.receipt.json` is committed and records which
candles a quoted figure came from.
