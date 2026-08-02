# Seven sectors: what building them actually costs

Asked 2026-08-02. An honest estimate, which means naming what is uncertain rather than
producing a confident schedule.

## The headline

**Build time is not the binding constraint.** One working session produced three lanes, six
connectors, the arbitrage discovery engine, the portfolio and sizing layers, a change
monitor and 619 tests. Code is the cheap part and it is getting cheaper.

Three things are the constraint, in this order:

1. **Your attention**, for every step that requires a human. This is the scarcest and the
   least elastic.
2. **Capital**, for the two sectors that need inventory.
3. **Accounts and credentials**, which are cheap but sequential — most cannot be obtained by
   anyone but you.

None of the three is affected by how fast the building goes, which is why a schedule
expressed in build weeks would be the wrong shape of answer.

## The seven are not one kind of thing

Grouping them by what they actually need matters more than ordering them:

| | Sector | Kind | Does the board machinery help? |
|---|---|---|---|
| 1 | Crypto | verification | **Yes** — built, two decisions published |
| 2 | Stocks | verification | **Yes** — built, one awaiting ratification |
| 3 | Arb betting | discovery + execution | Partly — gates built, discovery built, no live source |
| 4 | Flipping | discovery + execution | Partly — only when the exit is contracted |
| 5 | Etsy | operations | Barely — unit economics and the fee monitor only |
| 6 | App development | production | **Yes, already** — RBM-002 reviews engineering artefacts |
| 7 | YouTube shorts | production | **No** — nothing here applies |

The first two are done. The board verifies claims against primary sources and refuses to
conclude past the evidence. That is a *verification* engine, and it transfers to sectors 3
and 4 in part, to 5 barely, and to 7 not at all.

**For operations and production, an "agent" is doing labour rather than judgement.** That is
a different build with different risks, and calling both things "an agent" hides the
difference. An agent that reads a contract and refuses to over-claim is this repository. An
agent that produces sixty short videos a month is a factory, and the discipline that makes
the first trustworthy has nothing to say about the second.

## Costs I am confident about

| Item | Cost | Note |
|---|---|---|
| SEC EDGAR | free | no key exists to buy; User-Agent only |
| Supabase project | £0/month | confirmed against the account |
| Alpaca paper + market data | free | key and secret, paper account |
| Betfair delayed key | free | already held |
| Betfair live key | £499 one-off | the number you were quoted |
| Smarkets / Matchbook API | free with an account | not yet obtained |
| The Odds API free tier | free, 500 req/month | already used and found limiting |
| Google Play developer | ~$25 one-off | verify before relying on it |
| Apple developer | ~$99/year | verify before relying on it |

## Costs I would not quote without checking

Paid odds feeds. Published figures ranged from **$99–$499/month**, and the enterprise ones
(OpticOdds, OddsJam) do not publish at all and quote by company size. A monthly feed at that
level is worse value than Betfair's one-off £499, which reframes that decision.

**Agent compute is the one that scales badly and is easiest to underestimate.** Seven agents
running continuously is a recurring bill that grows with the number of sectors, not with the
revenue from them. It is the only line here that punishes breadth directly, and it should be
measured on one sector before being multiplied by seven.

## Capital, which is not a build cost

Flipping and Etsy need inventory. That is not a technology cost and no amount of building
reduces it. It is also the only money on this list that can be lost rather than spent:
a subscription buys a month, inventory buys a position.

## The binding constraint, stated plainly

**Every sector produces output that needs a human in the loop, and the queue is already
behind.**

RBM-002's first live engineering review produced six reports. They have been sitting
unverified since before today. Twelve more reports were verified in this session on a
standing authority with the basis recorded, accurately, as
`standing-authority-2026-08-02-not-individually-read` — both methodology auditors raised
that as a finding rather than let it pass.

Two boards are sitting at `GOVERNANCE_VALIDATION` waiting on two commands.

That is four lanes, one stalled mid-review and two awaiting a signature, before Etsy,
flipping and YouTube exist. Seven agents would not clear that queue; they would fill it
faster. The rate limit on this whole system is how much a person can actually read and
sign, and it does not rise when more is built.

## YouTube shorts, named separately

Worth flagging factually because it is the one item where nothing in this repository
applies. There is no claim being verified, so the machinery that makes the rest trustworthy
is simply absent. Platforms also have their own rules on mass-produced and inauthentic
content, and those rules change; a channel built on volume is exposed to a policy decision
in the way an Etsy shop is exposed to a fee change. That is a real risk, it is worth
checking the current terms before building rather than after, and it is your call.

## What I would actually do

Not a schedule. An order, with the reasons.

1. **Clear the queue before adding to it.** Two ratifications, six unverified RBM-002
   reports. That closes the stocks lane, closes the engineering lane, and app development
   then needs nothing further built at all.
2. **Finish one sector to revenue before starting a second.** Arbitrage is closest: the
   gates work, discovery works, and it is one free Smarkets account from surfacing
   candidates end to end. Prove one lane produces something before multiplying the pattern.
3. **Persistence, once.** The migration is generated. Everything above stops dying with the
   container, and every later sector inherits it for free.
4. **Then pick the next sector on evidence** — what step 2 actually taught, rather than on
   the assumption that seven lanes each behave like the first.

The honest summary: building all seven is achievable and is not the hard part. Running all
seven is the hard part, and the cost that decides it is measured in your attention rather
than in money or in weeks.
