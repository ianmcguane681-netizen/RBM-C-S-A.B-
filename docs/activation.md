# Activation: step by step

Written 2026-08-08 to be executed at a laptop, in order, without the session that wrote it
present to answer questions. Every command below was extracted from this file and run
before it was committed; where the output matters, the real output is shown.

`deploy/README.md` is the **box** — droplet, systemd, tunnelling. **This file is the keys,
the config and the theses**, which is the half where a wrong value fails quietly rather
than loudly. Do this on the laptop first. Move to the droplet only once a lane has reached
READY somewhere you can watch it.

---

# PART 0 — What you need before you start

## Things to obtain

| # | What | Where from | Needed for |
|---|---|---|---|
| 1 | **Odds API key** | free tier at the-odds-api.com | the arb lane. The previous key was pasted into a chat and is burned — rotate it |
| 2 | **Alpaca paper keys** — a key id and a secret | alpaca.markets, Paper Trading | the stocks lane: prices, and placing |
| 3 | *(optional)* Ethereum RPC URL | any archive-capable node | the crypto lane, which cannot sign and only reads |
| 4 | *(recommended)* **Telegram bot token and chat id** | `@BotFather` for the token, `@userinfobot` for your id | being told when a lane finds something, and the daily digest whose absence is the alarm |

You do not need all three. Each lane degrades independently and preflight names what is
missing and what it unlocks.

## Decisions to have made

| # | Decision | Default if you have not decided |
|---|---|---|
| 1 | **The stocks ring-fence.** Mechanical floor $1,336, recommendation **$2,000** | use $2,000; change it before it matters |
| 2 | **Which tickers** you will actually hold | `ALAB`, `NET`, `CRDO` |
| 3 | **A reason for each ticker**, in your own words, plus at least one thing that could go wrong | cannot be defaulted — the lane refuses without it |
| 4 | **Paper or live** at Alpaca | **paper** |

## What lands where, in total

| File | Mode | Contains | Committed? |
|---|---|---|---|
| `~/.oddsapi/key` | 600 | the odds key | never — outside the repo |
| `~/.alpaca/key_id` | 600 | Alpaca key id | never |
| `~/.alpaca/secret_key` | 600 | Alpaca secret | never |
| `~/.alpaca/paper` | 600 | empty marker file | never |
| `~/.telegram/bot_token` | 600 | the notification bot token | never |
| `~/.telegram/chat_id` | 600 | which chat to send to | never |
| `data/announced.json` | — | what you have already been told | gitignored |
| `data/notifications.json` | — | every send and what became of it | gitignored |
| `data/reapers.json` | — | balances, watchlist, authority | **gitignored** |
| `data/theses.json` | — | your reasons for each holding | **gitignored** |
| `data/breakers-*.json` | — | written by the system | gitignored |
| `data/outcomes.json` | — | written by the system | gitignored |

**Credentials live in your home directory, never in the repo**, so a public checkout can
never contain one. Never paste a key into a chat window, including to me.

---

# PART 1 — The laptop

## Step 1 — Get the code and prove it runs

**Where:** your laptop, anywhere you keep projects.

```bash
git clone https://github.com/ianmcguane681-netizen/RBM-C-S-A.B-.git
cd RBM-C-S-A.B-
git checkout claude/progress-check-question-dmic2o
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -q
```

**Expect:** `1323 passed, 2 skipped` in about thirty seconds.

**If not:** stop. Nothing below is worth doing against a checkout that does not pass.

Everything after this assumes you are in the repo root and using `.venv/bin/python`.

---

## Step 2 — Place the keys

**Where:** repo root, laptop.

```bash
bash deploy/setup-credentials.sh
```

It prompts one at a time with echo off. **Press ENTER to skip any you do not have yet.**
When it asks about Alpaca's environment, answer **`p`** for paper.

**Places:**

```
~/.oddsapi/key          600, inside a 700 directory
~/.alpaca/key_id        600
~/.alpaca/secret_key    600
~/.alpaca/paper         600, an empty marker
~/.telegram/bot_token   600
~/.telegram/chat_id     600
```

**Telegram is not a lane and skipping it breaks nothing** — every lane still runs and the
notifier reports `NOT_CONFIGURED`, which is not a failure. What you lose is the point of a
lane running on a cadence: an instruction that reaches READY at 16:00 on a Monday sits in a
log until somebody opens a terminal. Two minutes with `@BotFather` is the whole of it.

**Expect** it to print exactly that, with the modes. Verified against a throwaway `HOME`
today — those modes are what it produces, and both connectors then load what it wrote.

**Why not just `echo key > file`:** an argument is visible in `ps` to every user on the box
and lands in `~/.bash_history`, where it outlives any care taken afterwards.

**Live vs paper:** `live` requires typing `LIVE` in full. There is no reason to reach for
it — the placing path has never met a real broker, so the first live order would also be
the first order of any kind.

---

## Step 3 — Find out whether the keys actually work

**Where:** repo root.

```bash
.venv/bin/python preflight.py           # presence only — contacts nothing
.venv/bin/python preflight.py --probe   # actually reaches the endpoints
```

**Read the marks precisely.** Five of them, and three mean different things:

| mark | meaning |
|---|---|
| `ok` | probed, and it answered |
| `set` | present, not probed |
| `--` | present, **deliberately** not probed |
| `MISS` | absent |
| `DOWN` | present, and the probe failed |

**`--` is not `ok`.** A key that exists and has never been contacted is one you do not yet
know works. **Run `--probe` once after placing keys** — that is the step that settles it.

Preflight also prints the arb lane's credit burn per day against the free tier, from the
config in front of you, before you commit to a cadence.

---

## Step 4 — The reaper config

**Where:** repo root.

```bash
mkdir -p data
cp examples/reapers.example.json data/reapers.json
$EDITOR data/reapers.json
```

The `_` keys in that file are its documentation — read them there. Set `declared_by` to
**your own name** in both places; it refuses `agent:`, `ai:`, `model:`, `automation:`,
`bot:` and `system:` prefixes.

### ⚠ Replace the whole `stocks` block

The shipped example is `"balance": 5000.0` with `per_position_pct` defaulting to 5% — that
is **$250 a position**, and `stock_order` buys whole shares and refuses below one:

```
balance $5,000 at 5.0% per position  ->  $250.00 per position
  ALAB  $ 333.99  REFUSED: 250.00 USD bound by risk limit does not buy one share
  NET   $ 302.01  REFUSED: 250.00 USD bound by risk limit does not buy one share
  CRDO  $ 249.99  1 share(s), $249.99, bound by risk limit
```

**Two of your three names silently refuse and the lane is working correctly.** No error, no
missing key — the position is genuinely too small to round to one share.

Use this instead:

```json
"stocks": {
  "enabled": true,
  "balance": 2000.0,
  "free_balance": 2000.0,
  "currency": "USD",
  "per_position_pct": 25.0,
  "max_deployed_pct": 75.0,
  "max_concurrent_positions": 4,
  "autonomous_execution": false,
  "watchlist": ["ALAB", "NET", "CRDO"]
}
```

**Verified by assembling it:** ring-fence `2,000.00 USD`, per position `500.00`, deployed
cap `1,500.00`, daily loss `60.00`, concurrent `4`. Buys 1 ALAB, 1 NET, 2 CRDO.

Three things about those numbers:

- **`"currency": "USD"` is mandatory.** A euro ring-fence now stops the lane by name,
  because sizing would divide euros by a dollar ask. If you have an older
  `data/reapers.json` anywhere, check that key first.
- **`max_deployed_pct` must rise with `per_position_pct`.** `Ringfence` refuses
  `per_position_pct > max_deployed_pct`, and at the default 40% a single 25% position is
  nearly all the lane may hold at once — it would settle one position at a time and never
  accumulate evidence.
- **The daily loss limit will bite.** It stays at 3% of the ring-fence — $60 — while a
  position is now $334, so closing one loser at −18% halts the lane for the rest of that
  day. It clears at midnight; it is `max_consecutive_losses` that trips and stays tripped.
  That is the limit working, not a fault.

Leave `autonomous_execution: false`. See Step 7.

---

## Step 5 — Write a thesis for each ticker

**This is the step only you can do.** The stocks lane REFUSES a watchlist entry with no
live thesis rather than skipping it — *"nobody authorised this"* is a result worth
printing. There is **no CLI for this**; you edit the JSON by hand.

**Where:** repo root.

```bash
cp examples/theses.example.json data/theses.json
$EDITOR data/theses.json
```

**Places:** `data/theses.json` — a **JSON array**, one object per holding.

For each entry, replace:

| field | what to put |
|---|---|
| `subject` | the ticker, e.g. `"ALAB"` |
| `declared_by` | **your own name** — refuses automation prefixes |
| `reasoning` | why *you* want to hold it, in your words. Not a description of the company |
| `considered` | **at least one** thing that could go wrong. An empty list is refused |
| `declared_at` / `expires_at` | ISO-8601 UTC. An open-ended grant is the failure mode of every grant |
| `max_exposure` | the most you will put behind it — see the warning below |
| `currency` | **`"USD"`** — see the warning below |

### ⚠ Two traps in this file specifically

**1. No comment keys. Not one.** `reapers.json` is a dict, so its `_` keys are simply never
read — that trains you into a habit that breaks this file. `theses.json` is a *list* whose
rows are passed straight to `Thesis(**row)`, so a single stray key takes out the whole
register and the entire lane with it:

```
with a comment  : UNREADABLE — the thesis register would not parse
                  (TypeError: Thesis.__init__() got an unexpected keyword argument '_note')
```

Not "that one entry is skipped" — the lane is UNREADABLE. Put your notes in the
`reasoning` and `considered` strings, which are real fields.

**2. Set `"currency": "USD"` explicitly.** `Thesis.currency` defaults to `"EUR"`, and
`_limit_from` reads `thesis.max_exposure` as a bare float with **no currency check** — so a
thesis left at the default acts as a dollar limit while claiming to be euros. This is the
same defect class fixed in the ring-fence today, in a place that has not been fixed yet.
Setting it explicitly protects you completely; it is on the list to fix properly.

**3. `max_exposure` must fit inside the per-position cap.** At `balance 2000` and 25% the
cap is $500, so a thesis above that is silently the looser of the two and the ring-fence
wins. $500 matches.

**Verify it parses before moving on:**

```bash
.venv/bin/python -c "
from lib.thesis import ThesisRegister
r = ThesisRegister('data/theses.json')
print('readable:', r.readable, r.reason)
for t in r.entries: print(' ', t.subject, t.max_exposure, t.currency)
"
```

**Expect** `readable: True` and one line per ticker. If it says `False`, the reason names
the exact problem.

---

## Step 6 — Run it, sending nothing

**Where:** repo root.

```bash
.venv/bin/python run.py --reap --dry     # all three lanes, sends nothing whatever the modes say
.venv/bin/python run.py --reap stocks    # one lane
.venv/bin/python status.py               # money, breakers, open positions, scheduler
.venv/bin/python positions.py            # what is open
```

**Use `--dry` first, every time, after a config change.** It sends nothing regardless of
any mode setting.

**Exit codes are meaningful** and the scheduler reads them:

| code | meaning |
|---|---|
| `0` | nothing needs you |
| `1` | there are findings |
| `2` | **nothing was looked at** — not a quiet market |

A `2` is the one to care about. It means a lane could not reach its evidence.

**Every run ends with a `NOTIFICATIONS` block** saying who was told. `--dry` deliberately
tells nobody — a flag that promises to send nothing and then messages your phone is a flag
you cannot trust again — so use a real `--reap` to see the wire work. `python status.py`
has the same answer for the last few days: whether anything has actually reached you, or
only been attempted.

---

## Step 7 — Only then, autonomy

Run in owner-operating mode until you have seen an instruction you would have placed
yourself. Then set `autonomous_execution: true` for **stocks and nothing else**.

**What you will actually receive**, once the channel exists: one message per new
instruction (with the stake, the odds or the shares, and your own thesis reason, so it can
be acted on without unlocking anything), one when a breaker trips — including one tripped by
`positions.py --apply` at your keyboard, hours before that lane would next run — one when a
lane has failed to reach its source three runs running, and one short digest a day saying
what each lane found. A standing
opportunity is re-told every six hours rather than every run, and the digest reports the
lanes that found nothing on purpose — **it is the message whose absence is the alarm**, so
a day without one means something has stopped.

```bash
touch data/MANUAL     # take the wheel; research continues, placing stops
touch data/HALT       # stop everything, including the research
rm data/MANUAL        # hand it back
```

`data/MANUAL` beats the config, because a switch a setting could override is not a switch.
The chain lane refuses autonomy whatever the config says. The arb lane has no adapter at
all — bookmakers take no orders from programs, so its output is a slip you place by hand.
**Autonomy here means stocks.**

---

## Step 8 — What the arb lane still needs from you

A **settlement declaration** for the two books you will actually place at: an evening with
their abandonment and non-runner rules pages, once.

```bash
.venv/bin/python run.py --reap arb    # prints the exact key it wants, e.g.  Sky Bet|bet365
```

Until it exists the lane correctly stops at `INDETERMINATE`. **This cannot be automated and
the guard is structural** — `EquivalenceDeclaration` refuses every automation prefix. A feed
returns odds, not terms. The only real position this board examined had a positive margin
net of commission and was refused because one leg voided on abandonment while the other
stood.

**Watch the quota.** The free tier is 500 credits a month — 16.4 a day. A spent account is
indistinguishable from a quiet market for the rest of the month, which is why
`MINIMUM_REMAINING = 25` exists: the reserve is what lets you run one scan by hand after
the cadence has been stopped.

---

# PART 2 — The droplet, later

Only once a lane has reached READY on the laptop. Full runbook in **`deploy/README.md`**:
the box and user, the clone, `setup-credentials.sh` again on that machine, the config and
theses again, systemd units, and an ssh tunnel to the dashboard.

Two things that decide the shape and are easy to get wrong:

- **`data/` must survive a restart.** It holds the breaker state, the ledger, the seen
  register, the journal and the quota reading. A lost `data/breakers-arb.json` brings a
  TRIPPED breaker back ARMED, because the loss history is what trips it. That rules out an
  ephemeral-filesystem PaaS — on DigitalOcean, a **Droplet, not App Platform**.
- **Credentials are files in a real home directory**, so the worker unit deliberately does
  not set `ProtectHome`.

After starting it, the check that matters:

```bash
.venv/bin/python status.py     # SCHEDULER must read RUNNING
```

`SCHEDULER` is the first tile on the dashboard for a reason. Every other figure describes
what the lanes found; that one says whether they are being asked at all. **A stopped
supervisor leaves a system that looks entirely normal** — the dashboard renders, the ledger
is intact, every lane reports the state it was last left in, and nothing happens.

---

# If something looks wrong

| symptom | cause |
|---|---|
| every stock refuses to size | Step 4 — the balance is below one share |
| stocks lane REFUSED, currency message | set `"currency": "USD"` |
| stocks lane UNREADABLE | Step 5 — a comment key in `data/theses.json` |
| a ticker REFUSED, "no thesis" | Step 5 — write one, or the expiry has passed |
| a lane reports nothing found | check the exit code; `2` means nothing was looked at |
| preflight shows `--` | present but never contacted — run `--probe` |
| `SCHEDULER` STALE / NEVER_STARTED | nothing is running the lanes, whatever the cadences say |
| a breaker is TRIPPED | it does not self-clear. `Breakers.reset` needs a named human and a stated reason. That is the design |

# Still waiting on you, not on code

1. **Level 1 for stocks** — floor $1,336, recommendation $2,000. You said this needs more
   discussion; the config above uses $2,000 so the lane can run.
2. **The top of the ladder**, and **the bar** — proposal: 20 settled outcomes and 60 days.
3. **Rotate the burned odds key**, and the QuickNode URL, which embeds its auth token in
   the path and has been flagged across many sessions.
4. **A settlement declaration** for the two books you will actually use.
