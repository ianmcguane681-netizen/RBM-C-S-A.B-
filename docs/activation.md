# Activation: from a fresh clone to lanes that run

Written 2026-08-08 to be executed by Ian at a laptop, in order, without this session
present to answer questions. Every command below was extracted from this file and run
before it was committed; where a command's output matters, the real output is shown.

`deploy/README.md` is the box — Droplet, systemd, tunnelling to the dashboard. **This file
is the keys and the config**, and it is the part where a wrong value fails quietly rather
than loudly. Do this first, on the laptop, against a local checkout. Move to the droplet
once a lane has reached READY where you can watch it.

---

## Before anything: two things that changed today

**1. The stocks lane now REFUSES a ring-fence that is not in dollars.** Until today
`settings["currency"]` had two different defaults in one file, so one balance was euros to
every breaker limit and dollars to the share arithmetic. It is one table now, and a
mismatch stops the lane by name instead of sizing against a rate nobody has:

```
REFUSED  [stocks]
  the ring-fence is denominated in EUR and Alpaca quotes in USD, so sizing would divide
  EUR by a USD ask and buy the wrong number of shares. Nothing here converts between
  them. Set "currency": "USD" on the stocks lane in the config and fund its ring-fence
  in USD.
```

`examples/reapers.example.json` already carries `"currency": "USD"` for stocks, so a config
copied from it today is correct. **If you have an older `data/reapers.json` anywhere, check
that key before you start.**

**2. The shipped example balance cannot buy two of your three priciest names.** See step 4.
This is the one that will look like a broken lane and is not.

---

## 1. The checkout runs

```bash
cd ~/RBM-C-S-A.B-
git checkout claude/progress-check-question-dmic2o
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -q
```

Expect `1323 passed, 2 skipped` in about thirty seconds. If that is not what you see, stop
here — nothing below is worth doing against a checkout that does not pass.

## 2. The keys

```bash
bash deploy/setup-credentials.sh
```

Press ENTER to skip any you do not have yet; it places them one at a time. Verified against
a throwaway `HOME` today — it writes `600` files under `700` directories and both
connectors load what it wrote:

```
600  ~/.oddsapi/key
600  ~/.alpaca/key_id
600  ~/.alpaca/secret_key
600  ~/.alpaca/paper
700  ~/.oddsapi     700  ~/.alpaca
```

**Answer `p` for paper.** Live requires typing `LIVE` in full, and there is no reason to
reach for it — the entire placing path has never met a real broker, so the first live order
would also be the first order of any kind.

Never paste a key into a chat window, including to me. The one that was pasted is burned
and needs rotating at the-odds-api.com before it is placed here.

## 3. What the keys unlock

```bash
.venv/bin/python preflight.py           # presence only; contacts nothing
.venv/bin/python preflight.py --probe   # actually reaches the endpoints
```

Read the marks precisely, because three of them mean different things:

| mark | meaning |
|---|---|
| `ok` | probed, and it answered |
| `set` | present, not probed |
| `--` | present, **deliberately** not probed — run `--probe` to find out |
| `MISS` | absent |
| `DOWN` | present, and the probe failed |

`--` is not `ok`. A key that exists and has never been contacted is a key you do not yet
know works, and `--probe` is the difference. **Run `--probe` once after placing keys** —
that is the step that tells you the odds key is live rather than merely present.

Preflight also prints the arb lane's credit burn per day against the free tier, from the
config in front of you, before you commit to a cadence.

## 4. The configuration — and the trap in it

```bash
cp examples/reapers.example.json data/reapers.json
$EDITOR data/reapers.json
```

The `_` keys in that file are the documentation; read them there. Set `declared_by` to your
own name in both places — it refuses `agent:`, `ai:`, `model:`, `automation:`, `bot:` and
`system:` prefixes, deliberately.

### The trap

The example ships `"balance": 5000.0` for stocks, and `per_position_pct` defaults to 5%.
That is **$250 a position**. `stock_order` buys whole shares and refuses below one:

```
balance $5,000 at 5.0% per position  ->  $250.00 per position
  ALAB  $ 333.99  REFUSED: 250.00 USD bound by risk limit does not buy one share
  NET   $ 302.01  REFUSED: 250.00 USD bound by risk limit does not buy one share
  CRDO  $ 249.99  1 share(s), $249.99, bound by risk limit
```

**Two of your three priciest names refuse to size, and the lane is working correctly.**
Nothing is broken; the position is genuinely too small to round to one share. But if you
copy the example, add your watchlist and see most of it refuse, that is the reason — not a
bug, not a missing key, not the thesis register.

Real output at the two settings worth considering:

```
balance $5,000 at 25% per position  ->  $1,250.00 per position
  ALAB   3 shares, $1,001.97      NET   4 shares, $1,208.04     CRDO  5 shares, $1,249.95

balance $2,000 at 25% per position  ->  $500.00 per position
  ALAB   1 share,  $333.99        NET   1 share,  $302.01       CRDO  2 shares, $499.98
```

**The rule: minimum viable balance = priciest share ÷ per_position_pct.** ALAB at $333.99
against 25% puts the floor at $1,336, and sitting on the floor is fragile — at $1,336 the
limit is $334.00 against a $333.99 share, so a 1% move produces a zero-share refusal.

If you want the lane to actually place something tonight, the two workable settings are:

```json
"stocks": {
  "enabled": true,
  "balance": 2000.0,
  "free_balance": 2000.0,
  "currency": "USD",
  "per_position_pct": 25.0,
  "max_deployed_pct": 75.0,
  "max_concurrent_positions": 4,
  "watchlist": ["ALAB", "NET", "CRDO"]
}
```

That is level 1 of `docs/levelling-design.md`. Verified by assembling it: ring-fence
`2,000.00 USD`, per position `500.00`, deployed cap `1,500.00`, daily loss `60.00`,
concurrent `4`.

**`max_deployed_pct` must be raised with `per_position_pct`** — `Ringfence` refuses
`per_position_pct > max_deployed_pct` outright, and at the default 40% a single 25%
position is nearly all the lane may hold at once, so it would settle one position at a time
and never accumulate evidence.

**Expect the daily loss limit to bite at these settings.** It stays at 3% of the ring-fence
— $60 — while a position is now $334, so closing a single loser at −18% halts the lane for
the rest of that day. `profit_today` counts only outcomes dated today, so it clears at
midnight and needs no reset; it is `max_consecutive_losses` that trips and stays tripped. A
lane that stops for the day after one bad close is the limit working, not a fault. Raise
`daily_loss_pct` only deliberately, and know that you are widening the control that catches
a strategy going wrong across a session.

Leave `autonomous_execution: false`. See step 7.

## 5. A thesis per watchlist entry, or the lane refuses it

The stocks lane REFUSES a watchlist entry with no live thesis, rather than skipping it —
"nobody authorised this" is a result worth printing. A thesis is a human act and cannot be
written by me or by any automation prefix.

```bash
.venv/bin/python run.py --reap stocks
```

It will name each ticker that has none. Write them in `data/theses.json`; each carries the
reasoning, what was considered against it, an expiry and a `max_exposure`.

**`max_exposure` must fit inside `per_position_pct`**, or every instruction sizes to
something the breakers then refuse. At `balance 2000` and 25%, the per-position cap is
$500, so a thesis limit above that is silently the looser of the two and the ring-fence
wins.

## 6. Watch it run before it runs itself

```bash
.venv/bin/python run.py --reap --dry     # all three lanes, sending nothing whatever the modes say
.venv/bin/python status.py               # money, breakers, open positions, scheduler
.venv/bin/python positions.py            # what is open; --settle feeds the breakers
```

`--dry` sends nothing regardless of any mode. Use it first, every time, after a config
change.

Exit codes are meaningful and the scheduler reads them: `0` nothing needs you, `1` there are
findings, `2` **nothing was looked at**. A `2` is not a quiet market.

## 7. Only then, autonomy

Run in owner-operating mode until you have seen an instruction you would have placed
yourself. Then set `autonomous_execution: true` for **stocks and nothing else**.

```bash
touch data/MANUAL     # take the wheel; research continues, placing stops
touch data/HALT       # stop everything, including the research
```

`data/MANUAL` beats the config, because a switch a setting could override is not a switch.
The chain lane refuses autonomy whatever the config says. The arb lane has no adapter at
all — bookmakers take no orders from programs, so its output is a slip you place by hand.

## 8. What the arb lane still needs from you

A **settlement declaration** for the two books you will actually place at: an evening with
their abandonment and non-runner rules pages, once. Until then the lane correctly stops at
`INDETERMINATE` and prints the exact key it wants.

```bash
.venv/bin/python run.py --reap arb    # prints the key, e.g.  Sky Bet|bet365
```

This cannot be automated and the guard is structural: `EquivalenceDeclaration` refuses every
automation prefix. A feed returns odds, not terms. The only real position this board
examined had a positive margin net of commission and was refused because one leg voided on
abandonment while the other stood.

**Watch the quota.** The free tier is 500 credits a month — 16.4 a day. Preflight prints
what your configured cadence will actually spend. A spent account is indistinguishable from
a quiet market for the rest of the month, which is why `MINIMUM_REMAINING = 25` exists: the
reserve is what lets you run one scan by hand after the cadence has been stopped.

---

## Decisions waiting on you, not on code

1. **Level 1 for stocks.** Mechanical floor $1,336, recommendation $2,000. You said this
   needs more discussion — the config above uses $2,000 so the lane can run; change it
   before it matters.
2. **The top of the ladder** — the most a lane should ever run, whatever it proves.
3. **The bar** — settled outcomes and elapsed days that earn a level. Proposal: 20 settled
   and 60 days for stocks, both required.
4. **Rotate the burned odds key**, and the QuickNode URL, which embeds its auth token in the
   path and has been flagged across many sessions.

## If something looks wrong

- **A lane reports nothing found** — check the exit code. `2` means nothing was looked at.
- **Every stock refuses to size** — step 4. The balance is below one share.
- **The stocks lane is REFUSED with a currency message** — set `"currency": "USD"`.
- **`SCHEDULER` reads STALE or NEVER_STARTED** — nothing is running the lanes, whatever the
  cadences say. That tile is first on the dashboard for exactly this reason.
- **A breaker is TRIPPED** — it does not self-clear, and `Breakers.reset` needs a named
  human and a stated reason. That is the design, not an obstacle.
