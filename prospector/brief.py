"""The design brief: what a page for this business must contain, must not contain, and may
be built out of — handed to whoever or whatever designs it.

This file exists because of a decision about what is being sold. One template applied to
every business in a county is a product with a shape: it is cheap, it is obvious by the
third recipient, and it is worth what a template is worth. A page designed for the business
in front of you is a different offer, and it cannot come out of a renderer, because a
renderer that produced genuinely different pages would just be a template with more
branches.

So the pipeline stops producing the page and starts producing the brief. The brief goes to
a designer — a person, or a model with a design instruction — and whatever comes back goes
through `verify.py` before anybody sees it. The guarantee moves from "the generator cannot
invent facts" to "the page is checked against the evidence", which is the only version of
that guarantee that survives the page being designed rather than filled in.

`site.py` remains, as the reference render. It is the fallback for when nobody has designed
anything yet, and it is deliberately plain: the brief is the product, not the fallback.

## What the brief carries

The facts, each with its source, because those are the only things allowed on the page. The
gaps, named, because a designed page has to put something where the copy would go and the
answer is a labelled space rather than a plausible sentence. The images, with the label and
the attribution each one obliges. And the constraints, stated as constraints rather than
suggestions, because the person reading this may be a model, and a model given a style note
and a rule will treat both as style notes unless the rule is unmistakable.
"""
from __future__ import annotations

from prospector.business import Business, Fact
from prospector.cascade import Decision
from prospector.countries import Country
from prospector.countries import UNKNOWN as COUNTRY_UNKNOWN
from prospector.images import ImageSet
from prospector.locales import CATALOGUE, Locale
from prospector.presence import Presence
from prospector.states import IMAGES_FOUND, LICENSED_STOCK, SUBJECT_OWN


def write_brief(business: Business, presence: Presence, decision: Decision,
                image_set: ImageSet, *, operator: str, locale: Locale | str = "en",
                country: Country = COUNTRY_UNKNOWN) -> str:
    """The brief for one business, as Markdown."""

    if isinstance(locale, str):
        locale = CATALOGUE[locale]
    name = business.name_in(locale.code).value
    trade = business.kind.value.replace("_", " ")
    lines = [f"# Design brief — {name}", "",
             f"A one-page sample site for a {trade}, to be shown to the business itself. "
             f"Prepared for {operator}.", "",
             f"**Language: {locale.name} (`{locale.code}`), written {locale.direction}. "
             f"Country: {country.name or 'not established'}.** Every word you write goes "
             f"on the page in {locale.name} — headings, buttons, the lot. The facts below "
             f"are printed exactly as the source carries them and are never translated: a "
             f"street name rendered into English is an invented address."
             + (f"\n\n> {locale.caveat}" if not locale.reviewed else ""), "",
             "**Design it for this business.** There is no house template and there is not "
             "meant to be one: a page that could be any of forty businesses in the county "
             "is worth what a template is worth, and the recipient can tell. Type, colour, "
             "layout and voice are yours. The facts are not.", "",
             "## The facts you may use, and nothing else", ""]
    for key, fact in business.known().items():
        lines.append(f"- **{key}** — {fact.value}  \n  `{fact.source}` at {fact.retrieved_at}")
    lines += ["", "Anything not in that list is not known. Not 'probably', not 'safe to "
                  "assume' — not known, and it may not appear on the page in any form, "
                  "including alt text.", ""]

    lines += ["## Where the copy would go", "",
              "A real site has sentences about the business. Nobody here has spoken to "
              "them, so those sentences do not exist. Leave the space and label it — "
              "'a sentence about what you do, in your words' — rather than filling it. "
              "The labelled gap is the part that gets a reply.", ""]

    lines += ["## Photographs", "", "```", image_set.describe(), "```", ""]
    if image_set.status == IMAGES_FOUND:
        for image in image_set.images:
            if image.provenance == SUBJECT_OWN:
                lines += [f"- **Theirs** — `{image.local_path or image.url}`  ",
                          f"  from their own site, {image.source_page}  ",
                          f"  The page must say it is their photograph. It is not "
                          f"republished anywhere and comes down on request."]
            elif image.provenance == LICENSED_STOCK:
                credit = ("attribution required, verbatim" if image.must_be_attributed
                          else "no attribution required by this licence; credit anyway")
                lines += [f"- **Stock** — `{image.local_path or image.url}`  ",
                          f"  {image.licence}, {image.licence_url}  ",
                          f"  {credit}: {image.attribution}  ",
                          f"  **Must carry the label**: \"{image.label}\" — a stock "
                          f"photograph of a {trade}, on a page headed with this "
                          f"business's name, asserts that these are their premises "
                          f"unless the page says otherwise."]
        lines.append("")

    lines += ["## Hard constraints — the page fails verification without these", "",
              "1. A banner, visible without scrolling, saying it is an **unofficial "
              "sample** prepared by " + operator + ", **not affiliated** with " + name + ".",
              "2. `<meta name=\"robots\" content=\"noindex, nofollow\">`. This is a sample "
              "about somebody's business and must never compete with them in search.",
              "3. No invented facts. No founding year, no prices, no phone number other "
              "than the one above, no 'family-run', no 'established', no 'award-winning'.",
              "4. Every photograph from the list above, labelled and attributed as it "
              "says there. No other images, and no data: URIs.",
              "5. A viewport meta tag and a layout that works at 360px. The tool refuses "
              "sites that do not have one; producing one would be quite a look.",
              "6. Self-contained: one HTML file, styles inline. It is emailed and opened "
              "from disk as often as it is hosted.", "",
              "## Check it before it goes anywhere", "",
              "```bash",
              "python -m prospector.verify <this folder>",
              "```", "",
              "That reads the page against `evidence.json` and refuses anything "
              "fact-shaped it cannot trace. `COULD_NOT_VERIFY` is a failure, not a pass.",
              "",
              "## What you are opening with", "",
              f"> {locale.text(decision.claim_key) if decision.claim_key else decision.opening_claim}",
              "", (f"In English, for you: *{decision.opening_claim}*" if locale.code != "en"
                   else ""), "",
              f"Presence: `{presence.status}`. "
              + ("This is established absence — the note may say so."
                 if presence.may_claim_no_website else
                 "This is NOT established absence. Do not let the page or the note imply "
                 "the business has no website; what is known is that no site was listed."),
              ""]
    return "\n".join(lines)
