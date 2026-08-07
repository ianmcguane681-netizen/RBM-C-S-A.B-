# Running it on a box that stays on

A €5 droplet, a Raspberry Pi or an old laptop — the requirement is not power, it is a
**filesystem that survives a restart**. Two things depend on that and one of them changes
behaviour:

- Credentials are files (`~/.oddsapi/key`, `~/.alpaca/…`), not environment variables.
- `data/` holds the breaker state, the outcome ledger, the seen register, the journal and
  the quota reading. **A lost `data/breakers-arb.json` brings a TRIPPED breaker back
  ARMED**, because the loss history is what trips it. A lost `data/outcomes.json` loses
  open positions — the receipt beside it will report `LOST` rather than pretend, which is
  the guard working, but it is not a state to run in.

That rules out an ephemeral-filesystem PaaS. On DigitalOcean this means a **Droplet**, not
App Platform. Turn backups on; they are pennies and they cover exactly the two files above.

---

## 1. The box

Ubuntu 24.04. As root:

```bash
adduser --disabled-password --gecos "" provena

# DigitalOcean installs your key for root only. Without this, `ssh provena@…` in step 5
# fails: the account has no authorized_keys and password auth is off, so there is no way
# in at all. Copy it before you need it.
rsync --archive --chown=provena:provena ~/.ssh /home/provena/

apt update && apt install -y python3-venv git rsync
ufw allow OpenSSH && ufw enable          # allow first, then enable: the other order
                                         # locks you out of the session you are using
```

Open a second terminal and confirm `ssh provena@<droplet-ip>` works **before** closing the
root session. Locking yourself out of a box that holds a broker key is a bad afternoon.

## 2. The code

```bash
su - provena
git clone https://github.com/ianmcguane681-netizen/RBM-C-S-A.B-.git
cd RBM-C-S-A.B-
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -q          # confirm the box runs it before trusting it
```

## 3. The keys

```bash
bash deploy/setup-credentials.sh
```

It prompts with echo off and writes `600` files under `700` directories. It never takes a
secret as an argument — an argument is visible in `ps` to every user on the box and lands
in `~/.bash_history`, where it outlives any care taken afterwards. `echo "key" > file` has
the same problem and is the usual way this goes wrong.

Then prove they work, before trusting anything downstream of them:

```bash
.venv/bin/python verify.py          # a real call per credential; spends nothing
.venv/bin/python verify.py --book   # and price the portfolio, holding by holding
```

`preflight.py` answers "is a key present". `verify.py` answers "did the service accept it",
which is the question you actually have after placing one. It keeps REFUSED apart from
COULD_NOT_REACH: the first means the key is wrong, the second says nothing about the key,
and confusing them sends you to regenerate a key that was fine. It also shouts PAPER or
LIVE, spends no odds credit — the sports list is free — and imports no order path at all.

Alpaca additionally needs **exactly one** of `paper` or `live`. The script asks, defaults
to paper, and requires you to type `LIVE` in full for the other. A key gives no hint which
environment it belongs to and the base URLs differ by one word.

```bash
.venv/bin/python preflight.py
```

That names what is still missing, what each one unlocks, and — for the arb lane — what the
current cadence will spend per day against the free tier, **before** you commit to it.

## 4. The configuration

```bash
cp examples/reapers.example.json data/reapers.json
$EDITOR data/reapers.json
```

Read the `_` comment keys in that file; they are there rather than in this one. The parts
that matter on a first run:

- `balance` — the ring-fence. Everything else is a percentage of it.
- `sports` and `bookmakers` — fewer of both is cheaper. Preflight prints the arithmetic.
- `authority` — the standing grant, in your own name. It refuses automation prefixes.
- `declarations` — **leave empty for now.** See step 7.
- `autonomous_execution` — **leave `false`.** See step 8.

## 5. Start it

As root:

```bash
mkdir -p /etc/provena
printf 'PROVENA_VIEW_KEY=%s\nPROVENA_COMMAND_KEY=%s\n' \
    "$(openssl rand -hex 24)" "$(openssl rand -hex 24)" > /etc/provena/api.env
chmod 600 /etc/provena/api.env          # the unit file is world-readable; this is not

cp /home/provena/RBM-C-S-A.B-/deploy/*.service /etc/systemd/system/
cp /home/provena/RBM-C-S-A.B-/deploy/*.timer   /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now provena-worker provena-web provena-alerts.timer
systemctl status provena-worker --no-pager
```

The API binds to loopback. To see the dashboard, tunnel from your laptop rather than
opening a port:

```bash
ssh -N -L 8000:127.0.0.1:8000 provena@<droplet-ip>
# then http://127.0.0.1:8000 and paste the VIEW key when asked
```

Use the **view** key in the browser. The command key runs lanes and has no business in
browser storage.

## 6. Check it is actually running

```bash
.venv/bin/python status.py            # SCHEDULER should read RUNNING
journalctl -u provena-worker -f
```

`SCHEDULER` is the first tile on the dashboard for a reason. Every other figure describes
what the lanes found; that one says whether they are being asked at all. If it reads
`STALE`, nothing is running whatever the cadences say.

## 5b. Who may look at it

The web unit binds `127.0.0.1`, so the API is reachable only through the ssh tunnel above
and a key is enough. **If you ever change that bind, a key stops being enough**: an exposed
server requires an operator login and, with no operator credential on the box, serves no
lane data at all rather than falling back to the key.

```bash
su - provena
cd RBM-C-S-A.B-
.venv/bin/python access.py --host 127.0.0.1     # what this box is and what it requires
.venv/bin/python access.py --set-operator ian   # prompts twice, echo off, writes 600
```

The passphrase is hashed with scrypt into `~/.provena/operator.json` and never stored. It
is never taken as an argument and never read from a pipe — an argument is visible in `ps`
and lands in shell history, and a passphrase on a pipe is a passphrase in somebody's
deployment script.

A login yields a session that lasts 8 hours and grants **seeing, never doing**: the command
key still runs lanes and still never has to leave your shell. Five wrong attempts lock the
login for fifteen minutes and raise an alert.

Nothing here encrypts the connection. On plain HTTP a passphrase crosses the network in
clear, so keep the tunnel, or put Caddy or nginx with a certificate in front and leave
uvicorn on loopback behind it.

## 6b. Being told, rather than having to look

Everything in step 6 requires you to go and look. `provena-alerts.timer` is the part that
does not: every fifteen minutes it assesses the same state the dashboard shows and posts
what is asking for you.

```bash
su - provena
mkdir -p ~/.provena && chmod 700 ~/.provena
printf '%s\n' 'https://ntfy.sh/your-private-topic-name' > ~/.provena/alert_webhook
chmod 600 ~/.provena/alert_webhook

cd RBM-C-S-A.B- && .venv/bin/python alerts.py     # see what it would say, now
```

Any endpoint that takes a POST will do — ntfy, a Slack or Discord incoming hook. The URL is
a secret: anyone holding it can post as this system, so it lives in a 600 file and never in
the repository.

**Without a webhook the check still runs and still refuses to look healthy.** It exits 2,
which systemd records as a failed unit, and `alerts.py` says in as many words that the
conditions are real and nobody has been told them. An unconfigured channel is never
reported as a quiet system.

**Why this is its own timer and not part of the worker.** A supervisor cannot report its own
death. The heartbeat going still is the most consequential thing on the page, and if the
check ran inside the process being checked, the one failure that most needs announcing would
be the one that also stops the announcing.

```bash
systemctl list-timers provena-alerts.timer --no-pager   # when it last ran, when it next will
journalctl -u provena-alerts -n 30                      # what it said
```

## 7. Before the arb lane can reach READY

An evening with two bookmakers' abandonment and non-runner rules, once. Until a declaration
exists the lane stops at `INDETERMINATE` and prints the exact key it wants — that is the
gate doing its job, not a bug. Run `python run.py --reap arb` and it will tell you the key.

**This cannot be automated and the guard is structural.** A feed returns odds, not terms.
The only real position this board has examined had a positive margin net of commission and
was refused because one leg voided on abandonment while the other stood.

## 8. Only then, autonomy

Watch it in owner-operating mode first — the lanes research on their cadences and every
instruction waits for you. When you have seen it produce something you would have placed
yourself, set `autonomous_execution: true` for that lane and nothing else.

```bash
touch data/MANUAL     # take the wheel at any time; research continues, placing stops
touch data/HALT       # stop everything, including the research
```

`data/MANUAL` beats the config, because a switch a setting could override is not a switch.
The chain lane refuses autonomy whatever any of this says, and the arb lane has no adapter
to place through — bookmakers take no orders from programs, so its output is a slip you
place by hand. **Autonomy here means stocks.**

## Upgrading

As `provena`:

```bash
cd ~/RBM-C-S-A.B- && git pull && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -q     # green before it is restarted, not after
```

Then as root — `provena` is deliberately not in the sudo group, because a service account
that can become root is a service account whose compromise is a root compromise:

```bash
systemctl restart provena-worker provena-web
systemctl status provena-worker --no-pager
```

`data/` is gitignored, so a pull never touches your ledger, breakers or journal.
