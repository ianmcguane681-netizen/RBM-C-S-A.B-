# What a good small-business website has to do

This is the standard. It exists because "their website is bad" is a matter of taste until
somebody writes the criteria down, and a tool that approaches strangers on the strength of
an aesthetic judgement has no answer when one of them asks what exactly is wrong with it.

Twenty criteria, in four tiers, each one checkable and each one with a reason a business
owner would accept. **No score.** A weighted total lets a site that does not work on a
phone pass on the strength of its meta description, and an unmeasured criterion has no
honest number — scored zero it invents faults, dropped from the average it flatters.

The rule the tiers exist to produce:

> **A business is approached only over a failure in BLOCKING, MOBILE or CONVERSION.**
> Craft failures are recorded and never pitched.

Tiers one to three cost the owner customers. Tier four makes a web developer wince. A cold
email to a stranger about their missing structured data is how this whole activity gets a
reputation.

---

## Why mobile sits above conversion

Most people looking for a local business are on a phone, standing somewhere, deciding
whether to walk in or call. A site that renders at desktop width on a phone has not
degraded gracefully — it has failed, for the majority of the people who reach it, and a
missing viewport tag is a one-line fix nobody has made.

That is also why the highest-value single finding this tool produces is a phone number
that is text rather than a `tel:` link. It is invisible on a desktop and it costs calls
every day on a phone.

---

## Tier 1 — BLOCKING: the site does not work at all

| Criterion | What is checked | Why it matters to them |
|---|---|---|
| `LOADS` | Two fetches, spaced. Both must fail before this fails | A dead address printed on a van, a card and a directory listing |
| `NOT_AN_ERROR` | HTTP status of the final response after redirects | A listed address returning 404 sends away everyone who followed it |
| `NOT_A_PLACEHOLDER` | Known parking, default-server and "coming soon" phrases | Tells a customer the business is gone, whatever the truth is |
| `HTTPS` | The site answers on `https://` with a non-error status | Browsers label plain HTTP "Not secure" — the first thing a visitor reads about the business |

## Tier 2 — MOBILE: it does not work where the traffic is

| Criterion | What is checked | Why it matters to them |
|---|---|---|
| `VIEWPORT` | `meta viewport` with `width=device-width` (or the older `initial-scale=1`) | Without it a phone renders at desktop width and shrinks: unreadable until the visitor pinches |
| `ZOOM_ALLOWED` | The viewport tag does not set `user-scalable=no` or `maximum-scale=1` | Breaks the page for anyone who needs larger text; usually copied in from a template by accident |
| `NO_FIXED_WIDTH` | No fixed pixel width ≥ 700px on a top-level container, in CSS or inline, and no wide table layout | Forces sideways scrolling on every phone |
| `NO_LEGACY_MARKUP` | Framesets, Flash objects, `marquee`, or a fixed-width table layout with `font`/`center` tags | Cannot be made to adapt to a small screen |
| `NOT_HEAVY` | HTML over 600 KB, or more than 8 render-blocking scripts in the head | Several seconds of blank screen on a phone signal, and people leave |

`font` and `center` on their own are untidy, not broken, and do not fail anything. Plenty
of usable pages carry one.

## Tier 3 — CONVERSION: a visitor cannot act

| Criterion | What is checked | Why it matters to them |
|---|---|---|
| `PHONE_TAPPABLE` | A `tel:` link exists | On a phone, a number that is not a link has to be memorised or copied — most people just leave |
| `ADDRESS_PRESENT` | A postal address in the text or structured data, or a map link | Somebody in the street deciding whether to walk in needs it on the page, not on a third-party listing |
| `HOURS_PRESENT` | Opening hours in the text or structured data | "Are they open now" is the question a local site is asked most; answering it elsewhere sends people to Google's answer instead of yours |
| `CONTACT_PATH` | A `mailto:`, a form, or a contact page | Not everyone can call — people message outside hours, from work, or because they would rather write it down |

## Tier 4 — CRAFT: real, and never a reason to write to somebody

| Criterion | What is checked |
|---|---|
| `TITLE` | A non-empty `<title>` |
| `META_DESCRIPTION` | A description, or the search engine picks a sentence — usually the cookie banner |
| `HEADING` | Exactly one non-empty `<h1>` |
| `STRUCTURED_DATA` | `LocalBusiness` JSON-LD — how hours, address and phone reach the map card |
| `SOCIAL_PREVIEW` | `og:title` and `og:image`, or a shared link pastes as a bare grey URL |
| `FAVICON` | `link rel=icon` |
| `LANG` | A `lang` attribute on `<html>` |

---

## Three states, not two

Every criterion returns `MEETS`, `FAILS` or `NOT_ASSESSED`, and the third one blocks
rather than passing. A criterion that could not be evaluated is not a criterion that was
met, and the ones that decide whether a stranger gets an email are exactly where guessing
is least affordable.

At the level of the whole site that produces the same three states the rest of the package
uses: `DEFICIENT` when something in the first three tiers failed, `SERVICEABLE` when
nothing did, and `UNDETERMINED` when something that would have decided it could not be
read. **`SERVICEABLE` is not praise.** It means no named defect was found. There is no
machine-checkable definition of a good website and this file does not pretend to one.

## What the standard cannot see

No rendering happens. There is no browser, so there is no measurement of what actually
paints, no Core Web Vitals, no screenshot, and no view of a layout that collapses at 360px
for reasons invisible in the markup. What is checked is what can be read from the document
and the response: tags, structure, sizes, links, and whether the things a person needs in
order to act are present.

Which means a site can meet all twenty criteria and still be ugly, confusing or wrong.
That is a judgement for a person, and this tool does not make it — it finds the sites that
fail on something demonstrable and leaves taste to the human being who sends the email.

## The tool holds itself to it

`standard.assess` is run over the sample page this package generates, and a test asserts
it meets every criterion the evidence supports. Emailing somebody about their missing
viewport tag with a page attached that renders at desktop width deserves the reply it
would get.

```bash
python -m prospector.verify <dossier folder>   # facts, labels, and the mobile tier
```
