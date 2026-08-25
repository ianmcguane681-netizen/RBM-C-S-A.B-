# Prospector

Point it at an area. It reads the public business directory for that area, works out which
businesses have no website listed or a website with something demonstrably wrong with it,
builds each one a sample site out of facts that carry a source, and hands you a folder per
business with a draft note you send yourself.

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
discover ──► seen ──► presence ──► condition ──► decide ──► dossier ──► you send it
   │           │          │            │            │           │
OSM via     have I     is there    what is       PREPARE     four files
Overpass    already    a site      wrong with    REFUSED     on disk
            done       at all      the one       INDETERM.
            this one              they have
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
  request to be blocked; go county by county.

## Provenance

Extracted from the RBM repository, which is a review-board and trading system with nothing
to do with websites. What transferred was the doctrine, not the code: the third state at
every stage, the cascade instead of the score, the register that reports `UNCHECKED`
rather than `NEW`, the deliverable that stops where a person is required, and the refusal
to let an automation sign for a judgement. Those were learned there by getting them wrong,
mostly expensively.
