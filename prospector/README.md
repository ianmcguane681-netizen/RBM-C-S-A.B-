# Prospector

Point it at an area. It reads the public business directory for that area, works out which
businesses have no website listed or a website with something demonstrably wrong with it,
gathers licensed photographs (or their own), writes a design brief for each, and hands you
a folder per business with a draft note you send yourself.

```bash
python -m prospector --area "County Donegal" --operator "Ian McGuane"
python -m prospector --area "Letterkenny"    --operator "Ian McGuane" --dry
python -m prospector --area "Invented Town"  --operator "Ian McGuane" \
    --from-file prospector/fixtures/synthetic-area.overpass.json
python -m pytest prospector/tests -q
```

Standard library only. No model SDK, no HTTP client, no HTML parser, no framework.

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
defects, dropped from the average it raises the total because less was looked at. Findings
are named, checkable, and either a `DEFECT` or an `OBSERVATION`. `SERVICEABLE` means no
named defect was found — never that a site is good, which is not a machine-checkable
property.

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

## Known limits

- **Coverage is the binding constraint.** Expect a county to yield tens of usable
  businesses, not thousands, and expect most of the ones with a website to have no website
  tag on the map.
- **No search backend**, so absence is never established. Above.
- **No outcome loop.** Nothing here records whether an approach was answered, and silence
  is `UNKNOWN` rather than a refusal. Any future "which counties are worth working" number
  has to be built on that distinction or it will be a story about what people did not say.
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
