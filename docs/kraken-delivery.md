# The delivery mechanism

**Built 2026-08-23.** The path from "a rule measured well" to "it is on my phone" to "the
order is at the venue". Three pieces, and each can be used without the next.

```bash
python signals.py                 # what the rule says right now, printed
python signals.py --send          # the same, on Telegram and Discord
python signals.py --send --quiet-ok   # send even when nothing is signalling
```

## What each piece can and cannot do

| | can | cannot |
|---|---|---|
| `signals.py` | scan, size, message | place. No key path, no broker imported |
| `lib/notify.py` | Telegram + Discord | anything about money |
| `connectors/kraken_exec.py` | sign and send to Kraken **spot** | perpetual futures |

**`connectors/kraken_exec.py` is the first adapter in this repository that can sign and
send.** The chain lane's refusal is structural and stays that way; this is a different venue
and a deliberate decision. It is reached only through `lib/placing.py`, so the operating
mode, the breakers and the record-before-send ordering all get their say.

## Setting up a channel

By hand, once, mode 600. Never pasted into a chat, never in this repository:

```
~/.telegram/bot_token      from @BotFather
~/.telegram/chat_id        your own chat id
~/.discord/webhook         a channel webhook URL
```

Either alone works. Both is better, and the reason is the next section.

**The Discord webhook URL is itself the credential** — there is no separate id, so anyone
holding it can post to the channel. It is redacted out of every log line and error message,
the same as a bot token, for a stronger reason: a token is half of a credential and the
webhook is the whole of one.

## Silence is what this is careful about

A scanner that only messages you when it finds something has a defect in its quietest state.
No message means all of:

    nothing was found                      fine, and what you hoped to hear
    the scan died                          nothing has run since Tuesday
    the notifier broke                     a token expired, a webhook was deleted
    six markets could not be read          a broken pipeline reading as a quiet market

So `--quiet-ok` sends a message when nothing is signalling, and an unread market is **always
named** — an unread market is not a quiet one, and any of them may be signalling.

**`PARTIAL` is why two channels beat one.** A fan-out reporting success whenever any channel
worked would let Discord fail silently for a month, and you would find out on the day
Telegram also went down — which is the day it mattered. So a partial delivery is its own
state, it names the channel that failed, and `signals.py` exits non-zero on it so a cron job
finds out too. A channel that is simply not configured is *not* counted as a failure: having
only Telegram is a choice, not an outage.

## Four decisions worth knowing about

### The forming candle is not a candle

Kraken's series ends with the bar currently forming. Deciding on it means the signal appears
at nine in the morning, vanishes at two and returns at six — one rule giving three answers
about one day, none of which the backtest ever saw, because a backtest reads completed bars.

**The forming bar is dropped and the decision is made on the last closed one.** The entry
price is the live one, which is exactly what `lib/backtest.py` modelled: decide on a closed
bar, execute at the next opportunity.

### An unread order book refuses the size rather than shrinking it

Sizing takes the minimum of four measured ceilings and names the binding one: risk limit,
per-position cap, exit depth, volatility bound. Exit depth is read live from Kraken's public
order book.

If that read fails the size is `INDETERMINATE`, not computed from the three that remain — a
constraint that silently drops out **raises** the permitted size, so the missing one is
always the flattering one. In practice this is visible: run the scanner without a depth
reader and every signal comes back unsizeable.

### An entry with no exit will not construct

`Instruction` requires a stop price, and Kraken attaches it to the entry as a conditional
close, so the stop is submitted in the same request as the order it protects. Placing the
entry now and the stop a moment later has a window in it, and the window is the entire risk
of the position. A stop on the wrong side of the entry is refused too — as written, that
order stops out on arrival.

### The dry run is real

`place()` takes `validate` and it **defaults to True**: Kraken checks the order, returns its
own reading of it, and does not place it. Placing is the argument you pass, not the one you
remember to suppress. `VALIDATED` is its own status and `may_have_been_placed` is False for
it — returning `FILLED` for a dry run would be the single worst bug the adapter could carry.

## Two Kraken traps the adapter is shaped around

**The nonce is monotonic and shared.** Every private call carries a nonce that must exceed
every nonce used before on that key. Two processes on one key interleave and the lower one
is rejected — and a rejected nonce comes back looking exactly like a rejected order. The
last value is persisted beside the credentials and always exceeded, and a nonce error raises
`NonceRegression` rather than being reported as a refusal somebody would retry.

**Kraken has no client-order-id de-duplication.** Alpaca rejects a duplicate
`client_order_id`, which is what makes retrying safe there. On Kraken `userref` is a label:
send the same order twice and you own it twice. So this adapter **never retries a submit**.
On `UNKNOWN` it stops, and `resolve(userref)` asks Kraken what actually happened. That is
why the reference is derived from the intent rather than from the moment.

And the same trap as the price reader: **Kraken reports failure in a JSON array beside a
well-formed result, with HTTP 200.** A client checking only the status code records a fill
that never happened.

## What is deliberately not here

**Perpetual futures.** The funded programme runs on Kraken Pro perps — a different host, API
and auth scheme at `futures.kraken.com`. None of it is implemented, and a funded-account
order cannot be sent from here. Stated loudly because the two are close enough that somebody
will assume one adapter covers both, and the way they would find out is an order for the
wrong instrument on the wrong account.

**`kraken` is not in `lib.reaping.LANES`.** It has a placer and a broker factory, so it can
be gated and placed through the normal path, but nothing runs it on a cadence and no
orchestrator assembles it. That is the remaining decision, and it should follow a reason to
trade rather than precede one.

**A reason to trade.** `docs/kraken-backtest.md` measured the edge this scanner signals on
and concluded it is real but not strong enough to buy a funded seat with. The mechanism
being ready is not the edge being ready, and building the first is how you find out whether
the second matters — not a commitment to use it.
