# The unsolicited-website lane: what this repository could and could not recreate

Assessed 2026-08-25, not built and not scheduled. The prompt was a demo doing the rounds:
an agent finds real local businesses with no website or a poor one, builds each of them a
finished site from their own photographs, and hands over a written outreach email. Nothing
is pitched as an idea; the finished thing arrives with the business's name already on it.

The question asked was the narrow one — **with what is in this repository today, could
that be recreated.** The answer splits cleanly in two and the split is worth writing down,
because "yes, it is another lane" is right about half of it and badly wrong about the
other half.

## The half that is already here

The demo's visible part is the site and the email. The part it does not show is the part
that decides *which* business, *whether it has been pitched before*, and *what happens
when the lookup fails* — and that is the part this repository is made of.

**The sequence needs no new code.** `lib/reaper.py` holds look → screen → gates →
authorise → size → READY and knows nothing about odds, filings or chains; a fourth lane is
a `build_<lane>_reaper` and an entry in `LANES`, which `lib/reaping.assemble` loops over
rather than naming three. A lane is journalled and notified by existing, as the arb lane's
notifier wiring already proved.

**The "bad website" judgement has a shape here and it is not a score.**
`lib/candidates.py` argues at length why an opportunity score is a category error, and
this domain is where somebody would reach for one first — page speed, mobile, HTTPS,
freshness, all summed out of a hundred. The cascade is the honest form: an ordered set of
factual disqualifiers, the first refusal decisive, and any stage that could not be
evaluated blocking the surface rather than averaging away.

**The third state is not decorative here, it is the whole reputational risk.** "This
business has no website" and "I could not find this business's website" are the EDGAR-404
defect wearing a different hat, and the cost of confusing them is not a wrong number on a
dashboard — it is an email telling a shop with a perfectly good site that they have none.
So `NO_SITE` / `SITE_PRESENT` / `COULD_NOT_CHECK`, and only the first is pitchable.

**Not pitching the same business twice is `lib/seen.py`, unchanged.** Identity excludes
the volatile part exactly as it excludes the price; an unreadable register reports
`UNCHECKED` and never `NEW`, which here prevents the failure mode of re-pitching the
entire town on the morning the register goes missing.

**Sending is placing, and `lib/operating.py` already governs it.** An outreach email is an
irreversible outward act with a named third party on the other end, which is precisely
what the three modes exist for: `OWNER_OPERATING_MANUALLY` still does all the research and
lets Ian press send. And `lib/placing.py`'s rule transfers intact — record the outreach
*before* sending, because a crash after a send leaves a business that was contacted by
something no part of this system knows about.

**The deliverable pattern is `lib/betslip.py` and the match is exact.** That module exists
because bookmakers have no API, so the slip *is* the product rather than a missing
adapter. Here the built site and the drafted email are the deliverable for the same
reason: there is no "send a sales pitch" API worth having, and the artefact handed to a
person is the point.

## The half that is not here at all

Everything the demo actually shows on screen is absent, and most of it is absent
deliberately.

**No model SDK.** `requirements.txt` says so in a comment and says adding one should be a
decision. Copy for a site, and the outreach email itself, is generated text.

**No templating, no HTML generation, no image handling, no static hosting.** The only HTML
in the repository is the operator dashboard. There is no renderer, nothing that resizes a
photograph, and nowhere to put a finished site.

**No email path.** No SMTP, no provider, no bounce or complaint handling.

**No discovery source.** There is no places connector, and the choice is a real one with a
price: Google Places bills per detail call, and the free OpenStreetMap route has patchy
phone and website coverage, which turns straight into `COULD_NOT_CHECK` volume.

**No HTML parser or headless browser**, which is what "the site is bad" would have to be
established from.

## The three objections that are not about tooling

**It rests on a demand forecast, which is refused across all seven functions.** The lane
can establish facts — no site, a site that does not load, no HTTPS, hours that contradict
the listing. It cannot establish that the owner wants one, will pay, or will reply. That
is the same line already drawn for app development: the board can say what was built does
what it claims and has no view on whether anyone wants it. A version of this lane that
reported "high-probability prospect" would be borrowing credibility from the parts that
can.

**Silence is not a rejection, and this lane is mostly silence.** The outcome ledger feeds
the breakers, and here the outcome arrives sparsely, late, or never. No reply is
`UNKNOWN`, never a loss — and breakers fed on `UNKNOWN` are the decorative safety controls
of Gap 1 all over again, in a lane whose failure is measured in reputation rather than
euro.

**Building a site carrying a real business's name and photographs is not a neutral act.**
It is a spec sample, it must say so on its face, and the photographs belong to somebody.
Unsolicited commercial email into Ireland and the UK is governed rather than merely
frowned upon. None of this is a refusal — a clearly-labelled sample and a small volume of
genuinely addressed mail is ordinary business development — but it is a decision with a
named person behind it, not a default the lane picks up by being switched on.

## The honest answer

Recreating the demo *as a demo* needs no lane at all: it is a person and an agent working
for an afternoon, and this repository contributes nothing to it. Recreating it as
something that runs — a queue that keeps finding businesses, refuses to pitch the same one
twice, says `COULD_NOT_CHECK` out loud, and stops when it is going wrong — is roughly the
half described above, and that half is genuinely already built.

What sits between the two is four missing capabilities, each of which is a purchase or a
dependency decision rather than a design problem.

And step 4 of `docs/target-functions.md` applies here more than anywhere: **prove one
function produces something real before starting a fifth.** Four lanes exist and none has
yet produced a pound. This one is attractive precisely because it looks like it would
produce something quickly, which is the reason to be suspicious of the impulse rather than
to act on it.
