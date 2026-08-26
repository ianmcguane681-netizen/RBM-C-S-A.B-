# Prospector

Point it at an area. It reads the public business directory for that area, works out which
businesses have no website listed or a website with something demonstrably wrong with it,
gathers licensed photographs (or their own), writes a design brief for each, and hands you
a folder per business with a draft note you send yourself.

```bash
python -m prospector --area "County Donegal" --operator "Ian McGuane"
python -m prospector --area "Braga"          --operator "Ian McGuane"   # builds in pt
python -m prospector --area "Ille-et-Vilaine" --operator "Ian McGuane" --language fr
python -m prospector --area "Letterkenny"    --operator "Ian McGuane" --dry
python -m prospector --area "Invented Town"  --operator "Ian McGuane" \
    --from-file prospector/fixtures/synthetic-area.overpass.json
python -m pytest prospector/tests -q
```

Standard library only, with one optional extra: Playwright, for the browser stage below.
No model SDK, no HTTP client, no HTML parser, no framework.

## What it does, stage by stage

```
discover ─► seen ─► presence ─► condition ─► decide ─► images ─► brief ─► verify ─► you
   │          │         │           │           │         │         │        │
OSM via    have I    is there    what is     PREPARE   theirs,   what to   nothing
Overpass   already   a site      wrong       REFUSED   or CC-    design,   on the
           done      at all      with the    INDETER-  licensed  what not  page is
           this one              one they    MINATE    stock     to make   unsourced
                                 have                            up
```

Every stage has three outcomes, never two, and the third one is always "could not tell".
That is the whole design and everything else follows from it — see `states.py`, which is
the first file to read.

## The sentence this is built around

> **"This business has no website" is a claim about a business, and nothing in a directory
> can establish it.**

OpenStreetMap not carrying a `website` tag means a volunteer did not add one. In rural
Ireland that is the common case. So the listing produces `NO_SITE_LISTED` — a fact about
the map — and only an independent search can promote it to `NO_SITE_FOUND`, a fact about
the business. There is no search backend wired in, so **out of the box this tool cannot
establish that anyone lacks a website**, and every draft note it writes says only what was
actually checked:

established absence → "I could not find a website for you anywhere." the map is silent →
"I could not find a website listed for you in the public directories. If you already have
one, ignore this."

Adding a search backend (`presence.Searcher` — anything with `.find(name, locality)`) is
the single highest-value change to this package, because it is what turns the second
sentence into the first.

## Countries and languages

Point it at any administrative area OpenStreetMap knows — a county, a province, a country
— in whatever the local spelling is. Area names are matched on `name`, `name:en` and
`int_name`, so "Deutschland" and "Germany" both resolve, and a name that matches several
areas says which ones it searched rather than quietly picking the smallest.

The country comes from the business's own `addr:country` tag, or the ISO code on the area
relation, or `--country`, in that order — increasingly coarse, so the most specific
evidence wins. The country then decides two things.

**The language.** Eight are shipped: `en`, `ga`, `fr`, `es`, `de`, `it`, `pt`, `nl`.
Portugal builds in Portuguese without being told. `--language` overrides.

**A language this package has no strings for refuses.** It does not fall back to English.
That is the silent failure this whole codebase is organised against, in its most plausible
costume: the page still renders, still looks finished, and the only sign is that a shop in
Kraków got a page in a language nobody there asked for. A business whose language is
unavailable ends `INDETERMINATE [language]`, naming what was wanted and what exists.

**Only `en` is marked reviewed.** The other seven were written by the author, who is not a
native speaker of any of them. They work, and every artefact built from one says in the
brief, in the note and in the run report that a native speaker must read it before it goes
anywhere. Marking a locale reviewed is a one-line change made by whoever did the reading.

**The facts are never translated.** A street name rendered into English is an invented
address. Where OpenStreetMap itself carries `name:en`, that is a fact with a source like
any other and gets used on an English page. Addresses are re-ordered, not rewritten:
`Hauptstraße 12, 10115 Berlin` and `12 Main Street, Donegal Town, F94 X2P8` are the same
code path.

**And the rule about sending changes at the border.** Each note carries the regime for
where it is going — EU/EEA ePrivacy, UK PECR, US CAN-SPAM, Canada's CASL (consent first,
the strict one), Australia's Spam Act — and an unknown country prints the strictest
reading rather than the mildest. It is a prompt to check, not legal advice, and it says
so.

A note in a language you do not read is a note you cannot judge, so every non-English
draft carries the opening sentence in English underneath.

## It does not sell a template

One layout stamped across a county is worth what a template is worth, and the third
recipient in the same town can see the seams. So the pipeline's product is a **brief**,
not a page: `BRIEF.md` carries the facts with their sources, the gaps that must stay gaps,
the photographs with the label and credit each one obliges, and the constraints stated as
constraints. It goes to whoever designs the page — you, a designer, or a model given the
brief — and what comes back goes through the verifier before anybody sees it.

`site.py` still renders a plain reference page, so every business ends a run with
something correct on disk. It is the fallback and it is deliberately unexciting.

**That moves the guarantee.** A single template can be audited once. A page designed for
each business has been read by nobody before it exists, so "nothing on this page is
invented" has to be enforced on the output:

```bash
python -m prospector.verify dossiers/county-donegal/bridge-end-barbers--node-1001
```

`verify.py` reads the page as a browser does and refuses anything fact-shaped it cannot
trace to `evidence.json` — an invented phone number, a founding year, a price, "family-
run", "award-winning", a claim hidden in alt text, a photograph nobody recorded, a missing
sample banner, a page that would be indexed. `COULD_NOT_VERIFY` is a failure, not a pass.

## The standard: what counts as a site that needs replacing

The whole tool rests on one judgement, so it is written down in **`STANDARD.md`**: twenty
named criteria in four tiers, each checkable, each with a reason a business owner would
accept.

```
BLOCKING     loads · not an error · not a placeholder · HTTPS
MOBILE       viewport · zoom allowed · no fixed width · no legacy markup · not heavy
             · no sideways scroll † · readable text † · paints quickly †
CONVERSION   tappable phone · address · opening hours · a contact path
CRAFT        title · description · one h1 · LocalBusiness JSON-LD · og tags · icon · lang

† measured by opening the page in a phone-sized browser
```

**A business is approached only over a failure in the first three tiers.** Craft failures
are recorded and never pitched — tiers one to three cost the owner customers, tier four
makes a developer wince, and a cold email to a stranger about their missing structured
data is how this whole activity gets a reputation.

Mobile sits above conversion because that is where the traffic is: most people looking for
a local business are on a phone, standing somewhere, deciding whether to walk in or call.
The highest-value single finding the tool produces is a phone number that is text rather
than a `tel:` link — invisible on a desktop, costing calls every day on a phone.

Each criterion returns `MEETS`, `FAILS` or `NOT_ASSESSED`, and the third blocks rather
than passing. Nothing is summed, because a total is exactly what would let a site that
does not work on a phone pass on the strength of its meta description.

**The tool meets its own standard.** `standard.assess` runs over the page this package
generates and a test asserts it meets every criterion the evidence supports. Emailing
somebody about their viewport tag with a page attached that renders at desktop width
deserves the reply it would get.

## The browser stage, and the thing you actually send

```bash
pip install playwright && playwright install chromium    # optional
```

With it, each site is opened in Chromium at 390×844 and measured, and two screenshots are
taken: **their site on a phone, and the sample at the same size.** `COMPARISON.html` puts
them side by side with the named failures underneath. That page is the pitch, and it
persuades by not arguing — nothing is drawn on either picture, both are dated and
labelled, and the findings are things the owner can check on their own phone in a minute.

Without it, those three criteria are `NOT_ASSESSED` and the run says so: **markup-only is
a weaker claim and is stated as one.** An unopened page is never a page that passed.

The measured criteria catch what markup cannot, including the case markup gets backwards:
a page with no viewport tag lays out at ~980px and lets the phone shrink the whole thing,
so nothing overflows its own layout — a naive check passes it while the visitor reads 5px
text. Both criteria measure against the screen rather than the layout.

A capture whose stylesheets did not load is `CAPTURE_INCOMPLETE` and decides nothing. The
screenshot is kept for a person to look at, and it never goes in a comparison: a render of
somebody's site with its CSS missing is a picture of a bad day, not of their website.

## Photographs

Two sources, each with a different obligation, and neither is allowed on the page
silently.

**Theirs.** Taken from the business's own public website with robots.txt honoured,
downloaded into the dossier rather than hotlinked, never republished, and labelled on the
page as their own photograph. This is their picture shown back to them on a sample of
their own site — the one use where the ownership question has an easy answer, and it is
easy only because the page says so and the sample is not published. Facebook is not a
source: login wall, terms, and no reason to think the image is theirs anyway.

**Licensed stock.** Openverse, no key needed, filtered to licences permitting commercial
use *and* modification — NC is out because this is commercial work, ND is out because
cropping to a layout makes a derivative. Licence, licence URL and the verbatim attribution
travel into the dossier; credit is rendered where the licence requires it, and CC0 is not
described as requiring it.

**Every stock photograph is labelled where the reader sees it.** A stock barbershop on a
page headed with this barbershop's name asserts these are their premises — a fact-shaped
thing that did not come from evidence, which is the defect the whole package refuses.
`verify.py` fails a page carrying one unlabelled.

## What it will not do

**No score.** Not for prospects, not for websites. A weighted sum treats a disqualifier as
a deduction, and an unmeasured dimension has no honest number: scored zero it invents
defects, dropped from the average it raises the total because less was looked at. See
`STANDARD.md` for the twenty criteria and the tiers that replace a total. `SERVICEABLE`
means no named defect was found — never that a site is good, which is not a machine-
checkable property.

**No invented copy.** Everything printed on a sample page came from a `Fact` with a source
attached, and `EVIDENCE.md` in each folder lists every one of them. Where a real site
would have prose, the sample carries a labelled gap. A generated sentence about a business
you have never spoken to is indistinguishable from a retrieved one once it is on the page.

**No photographs.** The demo this came from used the businesses' own photos. Those belong
to the business or to whoever took them.

**No sending.** There is no `smtplib` import in this package and a test enforces its
absence. Everything else here is reversible; an email that has arrived is not. The
pipeline stops one step short and gives you the thing you would have sent.

**No unsigned pages.** `--operator` is required, and a name beginning `agent:`, `ai:`,
`model:`, `automation:`, `bot:` or `system:` is refused. A page carrying a stranger's
business name is signed by the person who stands over sending it.

## What each dossier holds

index.html the sample site: responsive, self-contained, noindex, banner at the top saying
it is an unofficial sample by <operator>, unaffiliated NOTE.md the draft approach, opening
with the strongest claim the evidence supports and no stronger, plus a checklist to read
before sending EVIDENCE.md every fact, its source and retrieval time; what was checked;
what was found; and the warning, where it applies, not to overstate the absence
evidence.json the same for a machine

## Where the data comes from, and why not Google

OpenStreetMap via Overpass, under ODbL, with attribution on every generated page. Google
Places has far better coverage and its terms forbid storing most of what it returns —
which would make the register that stops a business being approached twice a licence
breach rather than a design choice. The cost of choosing OSM is coverage, and it is a real
one: a rural county carries a fraction of its businesses and far fewer website tags. That
does not make the tool wrong; it makes `NO_SITE_LISTED` mean less than it looks like it
means, which is why nothing here promotes it to a claim about the business.

## After the yes: revisions, publishing, monitoring

The sample is full of labelled gaps on purpose — those gaps are what gets a reply, and the
reply is where the business becomes a customer.

**Revisions arrive as evidence.** Each dossier carries `OWNER-SUPPLIED.json`. What the
owner said goes in it, with their name and how they said it, and the next build merges it:
their corrections outrank the map (the map is what a passer-by recorded, sometimes years
ago), their photographs replace the stock ones with no licence question attached, and
their words fill the copy gaps. **The rule about invented copy does not move** — a
sentence about the business written by anything other than the business is still refused.
What changes is that the sentences now exist and have somebody's name on them. Content in
that file with no `from.person` and `from.medium` is `HANDOVER_UNREADABLE`, not
"supplied".

**Publishing is a named person's decision, and there is no `force=True`.**

```bash
python -m prospector.engagement --identity node/1001 --name "Bridge End Barbers" \
    --by "Cathy Doherty" --role owner --via "email 2026-08-27" --on 2026-08-27 \
    --scope PUBLISH --scope MONITOR --evidence mail/cathy-2026-08-27.eml
```

That record is the only thing that removes the "unofficial sample" banner and the
`noindex`. `render()` validates it rather than trusting a flag; an authorisation naming
`agent:`, `ai:`, `model:`, `automation:`, `bot:` or `system:` is refused in the
constructor, as the parent repository refuses them for ratifying a board decision. A
`MONITOR` authorisation does not publish anything — agreeing to have a site watched is not
agreeing to have it published. And the verifier inverts once a page is live: a published
page carrying the sample banner, or telling search engines to ignore it, or with no record
of who authorised it, all fail.

**Monitoring is a promise, so silence has to mean something.**

```bash
python -m prospector.watch --url https://bridgeendbarbers.ie \
    --baseline data/watch/bridge-end-barbers.json      # exit 1 when a person is needed
```

INTACT · IMPROVED · REGRESSED · GONE · UNREADABLE · NOT_WATCHED

A regression is a named criterion that was passing and now fails — never a score going
down — because whoever reads the message has to know what to fix. An outage does not
overwrite the baseline, or the recovery would report twenty improvements and the outage
would vanish. An unreadable baseline is not a quiet state: it means the watch is not
running, which is the thing a paying client would want to know that day. And the
certificate expiry is checked, because it is the most common way a working small site
becomes a frightening one overnight — reported as `None` when it cannot be read, never as
plenty of time.

## Known limits

- **Coverage is the binding constraint.** Expect a county to yield tens of usable
  businesses, not thousands, and expect most of the ones with a website to have no website
  tag on the map.
- **No search backend**, so absence is never established. Above.
- **Eight languages**, and no machine translation step. A ninth is a dict in `locales.py`;
  a page in a language nobody involved can read is a page nobody can check, and the check
  is the product.
- **Country coverage in the table is EU/EEA, UK, US, CA, AU, NZ.** Anywhere else resolves
  to `COUNTRY_UNKNOWN`, which refuses to guess a language and prints the strict sending
  rule.
- **No outcome loop.** The engagement ledger records what a business agreed to, and
  nothing records whether an unanswered approach was read, refused or missed. Silence is
  `UNKNOWN`, not a no. Any future "which counties are worth working" number has to be
  built on that distinction or it will be a story about what people did not say.
- **No hosting and no DNS.** Publishing here means the page is authorised and built; it
  does not put it on a server or point a domain at it. Those need credentials for a
  registrar and a host, which is a decision and a set of secrets, not a missing function.
- **No revenue projection, deliberately.** The ledger holds what was agreed. What a
  retainer is worth next quarter is a forecast, and the parent repository refuses those
  across every lane for the same reason: nothing here can establish it.
- **Opening hours are printed in OSM syntax, verbatim.** Expanding `Tu-Fr 09:00-18:00; PH
  off` into English means interpreting a small language with edge cases, and an
  interpretation error publishes wrong opening times over a business's name.
- **Rate limits.** Overpass is free, donated hardware. A whole country in one query is a
  request to be blocked; go county by county. Openverse is free too, and a large share of
  what it indexes is hosted by Wikimedia, which rate-limits shared addresses hard — a
  download refused there costs a photograph, not the page, and the set is downgraded to
  `COULD_NOT_LOOK_FOR_IMAGES` rather than reporting an empty success.

## Provenance

Extracted from the RBM repository, which is a review-board and trading system with nothing
to do with websites. What transferred was the doctrine, not the code: the third state at
every stage, the cascade instead of the score, the register that reports `UNCHECKED`
rather than `NEW`, the deliverable that stops where a person is required, and the refusal
to let an automation sign for a judgement. Those were learned there by getting them wrong,
mostly expensively.
