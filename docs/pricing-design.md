# Wiring a price source into portfolio valuation

Designed 2026-08-05. **Built 2026-08-06 in `lib/pricing.py`**, and this file is kept as
the argument behind the code rather than as a plan. Where the building answered a question
this design left open, the answer is marked BUILT below.

## What is missing, exactly

`status.py` values every holding with `p.value_at(None)` — in both the text panel and
`as_json`. `None` means "no price available", so **every holding marks UNPRICED whatever
is actually knowable**. `CAPITAL AT COST` shows what was paid and `priced_value` is
permanently null.

Meanwhile `connectors/alpaca.AlpacaBroker.quote(symbol)` already returns a live bid and ask
with a timestamp, and `lib/portfolio.value_at()` already accepts `unit_price`, `source`,
`priced_at` and `stale_after_seconds` and already has `PRICED / UNPRICED / STALE`.

So the machinery exists at both ends and nothing joins them. This is wiring plus three
decisions, and the decisions are the whole job.

**It does not block any lane.** The stocks reaper fetches its own quote for sizing
(`_price()` is a stage in its cascade). What is blocked is the *portfolio* view: what the
holdings are worth now, the allocation split, anything downstream of a current value.

---

## Decision 1 — value at the BID, and say so

A holding is worth what you could get for it, which is the bid. Valuing at the ask, or at
the mid, states a price nobody is offering you and overstates the book by the spread on
every line. On a thin small cap that is not a rounding difference.

`Quote` already carries both sides and their sizes. Use `bid`. Record `source` as the
connector so a reader can see where the number came from.

`executable_price(side)` exists for *orders* and is a different question — that one is
about what you would pay to get in.

## Decision 2 — staleness is mandatory, not defaulted

`value_at(..., stale_after_seconds=-1.0)` means "never goes stale", and that default must
not be used here. A price fetched an hour ago and rendered as current is this repository's
recurring defect wearing a timestamp; the dashboard refreshes on load and would happily
show a Friday price on a Sunday as though the market were open.

Pass an explicit ceiling and pass `priced_at` from the quote's own `t` field — the feed's
timestamp, never the time of the HTTP call. `connectors/oddsapi` already makes exactly this
distinction and says why.

A sensible starting ceiling is **fifteen minutes** during market hours. Note that a US
market being closed is not staleness — the last trade genuinely is the last price — so
either the ceiling is generous enough to cover a weekend or `STALE` needs to mean
"the market is shut", which is a different fact and probably deserves its own state.
**Decide that explicitly rather than picking a number.**

**BUILT: its own state, and the unknown case is the one that matters.** `MARKET_CLOSED` is
a price past the ceiling at a venue the clock reports shut, and it counts toward the total
because the last trade genuinely is the last price. `AlpacaBroker.is_market_open()` returns
True, False or **None**, and a clock that could not be read leaves the valuation on STALE.
Resolving an unread clock to "closed" would relabel every stale price as an honest weekend
one — an outage arriving as reassurance — which is the direction this repository refuses.

## Decision 3 — currency, and this is the one that will bite

**The book is in EUR. Alpaca quotes in USD.** There is no FX rate anywhere in this
repository, and an FX rate is itself a price that goes stale.

This already caused a live defect: the dashboard summed `EUR 39.00` and `USD -77.00` and
printed `-EUR 38.00`. The fix there was to refuse the total and say why, and the same
answer applies here.

**Recommended for a first version: do not convert.** Value each holding in the currency it
is quoted in, carry that currency with the figure, and refuse any total that spans more
than one. `Realised.to_dict()` and the dashboard's realised tile already do exactly this
and are the pattern to copy.

Adding FX later is a real piece of work with its own third state — an unavailable rate must
make the total UNKNOWN, not fall back to a stale rate — and it should not be smuggled in as
part of this job.

---

## Coverage: expect a partial answer, and do not treat it as a bug

Alpaca quotes **US-listed** equities and ETFs. A representative real book here holds:

- Six US-listed names — Cloudflare, Astera Labs, Credo, Rubrik, Modine, SentinelOne.
  Quotable.
- Four European UCITS ETFs — a Vanguard S&P 500 accumulating, an iShares NASDAQ 100
  accumulating, an iShares MSCI Global Semiconductors, an iShares Physical Gold. These are
  Irish-domiciled and almost certainly **not** available from Alpaca. *Verify rather than
  assume; if they are quotable, this section is happily wrong.*

So the honest outcome is roughly six of ten priced and the book reporting
`PARTIALLY_UNPRICED` with the four ETFs named in `unpriced_assets`. **That is the correct
result, not a gap to paper over.** The temptation to reach for a scraped price or a stale
figure so the total looks complete is the defect this whole system is built against —
`status.py` already refuses a total that mixes priced and unpriced holdings.

If those four matter enough to price, that is a second connector and a separate job.

---

## Failure behaviour

- A quote that fails, returns one-sided, or returns nothing → `UNPRICED` for that holding.
  **Never fall back to a previously seen price.** A remembered value rendered as current is
  the vanished-ledger defect: it looks like data and is a memory.
- One asset failing must not fail the others. Value what can be valued and name the rest.
- The whole price source being unreachable → every holding `UNPRICED`, and the panel says
  the source could not be reached, which is not the same as a book of unquotable assets.
  `COULD_NOT_LOOK` versus `NOTHING_FOUND`, applied to prices.
- Alpaca rate limits exist. Ten holdings is nothing, but isolate the calls so one 429 does
  not take the page down, and do not retry into the limit.

**BUILT, and the second half of that line had teeth.** `AlpacaBroker` defaults to
`retrying_urlopen`, which sleeps 5, 20 and 60 seconds on a 429 — correct for the research
connector it was written for, and about fourteen minutes of blank panel across ten
rate-limited holdings here. The valuation path passes a single-attempt opener with a 10s
timeout; the lanes keep the retrying one.

---

## Shape

Keep `status.py` free of connector knowledge. Something like:

```
lib/pricing.py
    class PriceSource(Protocol):   quote(asset) -> (price, currency, at) | None
    def value_book(book, source, *, stale_after_seconds) -> list[Valuation]
```

`status.py` then calls `value_book(...)` where it currently hardcodes `value_at(None)`, and
the connector stays behind the protocol so a second source (for the ETFs, or for crypto)
is an argument rather than a rewrite. The lane registry work is the precedent: one place
decides, everything else derives.

## Tests to write

Properties, not coverage:

- a holding priced from a live quote reports `PRICED` with its source and timestamp
- a quote older than the ceiling reports `STALE`, and `STALE` is not `PRICED`
- a failed quote reports `UNPRICED` and **does not** reuse the last known price
- one asset failing leaves the others priced and names the failure
- the source being unreachable is reported apart from a book of unquotable assets
- a book spanning two currencies produces no single total, and says which currencies
- valuing uses the bid: a book with a wide spread is not valued at the ask
- the existing guarantee still holds — a book with no entries is `NOT_CONFIGURED` /
  `EMPTY_BOOK` with a null total, never `0.0`

## What this job is not

- Not FX. Not a net-worth figure across currencies.
- Not the portfolio performance chart — that needs a stored time series, which is a
  different piece of work with its own staleness questions.
- Not pricing the crypto lane's holdings; the chain connector is a separate source.
- Not touching any lane's own pricing. The stocks reaper quotes independently and works.

## Rough size

An hour or two for the wiring and the tests, if the three decisions above are made first
rather than discovered halfway through.
