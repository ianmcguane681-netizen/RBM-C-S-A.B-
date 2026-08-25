"""The reference render: a plain, correct page, produced so the pipeline always has one.

**This is the fallback, not the product.** The page that gets sent should be designed for
the business in front of you — see `brief.py` for why, and for what goes to whoever designs
it. One template stamped across a county is worth what a template is worth, and the third
recipient in the same town can see the seams. What this file guarantees is that every
business in a run ends with *something* correct on disk, and that the correct-by-construction
version exists to compare a designed page against.

Three rules hold here and are re-checked by `verify.py` on any page, however it was built.

**Nothing appears that did not come from a `Fact`.** No invented founding year, no
"family-run since", no "we pride ourselves on". Generated prose about a business you have
never spoken to is indistinguishable from retrieved prose once it is on a page, and the
first time a recipient reads a sentence about their own business that is not true, the
pitch is over and deservedly so. Where a real site would have copy, this one carries a
labelled gap.

**The page says what it is, at the top, always.** It is an unofficial sample, prepared by a
named person, from public information, with no affiliation. A page carrying a business's
name that does NOT say this is a passable forgery of that business's web presence, and the
difference between a generous piece of speculative work and something quite a lot worse is
exactly that banner. `render` cannot be asked to omit it.

**Photographs carry their obligations.** Their own photograph is labelled as theirs; a
stock photograph is labelled as stock, because a picture of *a* barbershop on a page headed
with *this* barbershop's name asserts that these are their premises. Attribution required
by a licence is rendered, not summarised.
"""
from __future__ import annotations

import html
from typing import Sequence

from prospector.business import Business, Fact
from prospector.locales import CATALOGUE, NUMBER_LAST, RTL, Locale
from prospector.states import SUBJECT_OWN

#: Fields that become the contact block, in the order a person reads them.
_CONTACT_ORDER = (("phone", "Phone"), ("email", "Email"))

#: The gaps, as locale keys. A gap explained in a language the reader does not speak is
#: an unexplained gap, which reads as an unfinished page rather than a deliberate one.
_GAP_KEYS = (("gap_photos_title", "gap_photos_body"),
             ("gap_words_title", "gap_words_body"),
             ("gap_services_title", "gap_services_body"))


def _esc(value: str) -> str:
    return html.escape(value, quote=True)


def _address(business: Business, locale: Locale) -> str:
    """The same facts in the order the country writes them.

    Not cosmetic. "12 Hauptstraße, 10115 Berlin" and "Hauptstraße 12, 10115 Berlin" carry
    identical information, and only one of them looks like it was written by somebody who
    has been to Germany. The values themselves are never rewritten.
    """

    parts = []
    number = business.get("housenumber")
    street = business.get("street")
    if isinstance(number, Fact) and isinstance(street, Fact):
        parts.append(f"{street.value} {number.value}" if locale.address_order == NUMBER_LAST
                     else f"{number.value} {street.value}")
    elif isinstance(street, Fact):
        parts.append(street.value)
    city = business.get("city")
    postcode = business.get("postcode")
    if locale.postcode_before_city:
        # "10115 Berlin" is one line with a space, not two fields with a comma between
        # them — the comma is the tell that a form filled this in rather than a person.
        joined = " ".join(v.value for v in (postcode, city) if isinstance(v, Fact))
        if joined:
            parts.append(joined)
    else:
        parts += [v.value for v in (city, postcode) if isinstance(v, Fact)]
    return ", ".join(parts)


def _hours_rows(business: Business, locale: Locale) -> str:
    hours = business.get("opening_hours")
    if not isinstance(hours, Fact):
        return ""
    # Printed verbatim, in the OSM syntax it was recorded in, rather than expanded into
    # days of the week. Expanding it means interpreting a mini-language with edge cases
    # (PH off, Su 12:00-16:00, "off"), and an interpretation error here publishes wrong
    # opening times over a business's name.
    return (f'<section class="card"><h2>{_esc(locale.text("opening_hours"))}</h2>'
            f'<p class="hours">{_esc(hours.value)}</p>'
            f'<p class="note">{_esc(locale.text("hours_note"))}</p></section>')


def _map_link(business: Business, locale: Locale) -> str:
    raw = business.raw or {}
    lat, lon = raw.get("lat"), raw.get("lon")
    if lat is None or lon is None:
        centre = raw.get("center") or {}
        lat, lon = centre.get("lat"), centre.get("lon")
    if lat is None or lon is None:
        return ""
    href = f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=18/{lat}/{lon}"
    return (f'<a class="maplink" href="{_esc(href)}" rel="noopener">'
            f'{_esc(locale.text("map_link"))}</a>')


STYLE = """
:root{--ink:#191714;--muted:#6b6155;--line:#e2dcd2;--bg:#faf7f2;--card:#fff;
--accent:#8a5a2b;--warn-bg:#fff6e6;--warn-line:#e3b978;--warn-ink:#5a3d12}
@media (prefers-color-scheme:dark){:root{--ink:#f2ede5;--muted:#a99f92;--line:#33302b;
--bg:#151412;--card:#1e1c19;--accent:#d9a56a;--warn-bg:#2a2318;--warn-line:#6b552f;--warn-ink:#e8cfa4}}
*{box-sizing:border-box}
[dir="rtl"] .trade,[dir="rtl"] h1,[dir="rtl"] p,[dir="rtl"] li{text-align:right}
body{margin:0;background:var(--bg);color:var(--ink);
font:16px/1.6 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial}
.wrap{max-width:720px;margin:0 auto;padding:0 20px 64px}
.banner{background:var(--warn-bg);border-bottom:1px solid var(--warn-line);
color:var(--warn-ink);padding:12px 20px;font-size:14px}
.banner strong{font-weight:650}
header{padding:56px 0 32px;border-bottom:1px solid var(--line)}
h1{font-size:clamp(30px,6vw,44px);line-height:1.15;margin:0 0 8px;letter-spacing:-.02em}
.trade{color:var(--muted);font-size:15px;text-transform:uppercase;letter-spacing:.08em}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;
padding:20px 22px;margin:20px 0}
h2{font-size:15px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);
margin:0 0 12px;font-weight:600}
.big{font-size:20px;margin:0 0 4px}
a{color:var(--accent)}
.hours{white-space:pre-wrap;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
font-size:15px;margin:0}
.note{color:var(--muted);font-size:13px;margin:10px 0 0}
.gap{border:1px dashed var(--line);border-radius:12px;padding:18px 20px;margin:12px 0;
background:transparent}
.gap h3{margin:0 0 4px;font-size:16px}
.gap p{margin:0;color:var(--muted);font-size:14px}
.figures{margin:24px 0;display:grid;gap:14px}
figure{margin:0}
figure img{width:100%;height:auto;border-radius:12px;display:block;border:1px solid var(--line)}
figcaption{color:var(--muted);font-size:12.5px;margin-top:6px}
.maplink{display:inline-block;margin-top:6px;font-size:14px}
footer{margin-top:44px;padding-top:20px;border-top:1px solid var(--line);
color:var(--muted);font-size:13px}
footer ul{padding-left:18px;margin:8px 0}
"""


def _images_block(images: Sequence, locale: Locale) -> tuple[str, str]:
    """The figures, and the attribution lines the licences oblige.

    Returns both because they belong in different places on the page and neither is
    optional: a licence condition rendered only next to the picture is missed when the
    picture is scrolled past, and a label rendered only in the footer is not a label.
    """

    if not images:
        return "", ""
    figures, credits = [], []
    for image in images:
        src = image.local_path or image.url
        if image.provenance == SUBJECT_OWN:
            caption = locale.text("own_caption")
            alt = locale.text("own_alt")
        else:
            # The label travels with the image in the operator's language for the brief,
            # and is rendered here in the reader's. Both say the same thing, and the
            # verifier checks for the one the page is actually in.
            caption = locale.text("stock_caption")
            alt = locale.text("stock_alt")
        figures.append(f'<figure><img src="{_esc(src)}" alt="{_esc(alt)}" loading="lazy">'
                       f'<figcaption>{_esc(caption)}</figcaption></figure>')
        if image.attribution:
            credits.append(f"<li>{_esc(image.attribution)}</li>")
    return ("".join(figures),
            f"<ul>{''.join(credits)}</ul>" if credits else "")


def render(business: Business, *, operator: str, sources: Sequence[str] = (),
           images: Sequence = (), locale: Locale | str = "en") -> str:
    """One self-contained HTML page. `operator` is the person whose sample this is.

    `operator` is required and unescapable-by-omission on purpose: an unsigned sample page
    carrying somebody else's business name is the artefact this function refuses to
    produce.
    """

    if not operator.strip():
        raise ValueError("a sample page must name the person who prepared it")
    if isinstance(locale, str):
        # A code with no strings raises rather than falling back: `locales.choose` is where
        # an unavailable language is turned into a refusal, and reaching here with one
        # means that stage was skipped.
        locale = CATALOGUE[locale]

    display_name = business.name_in(locale.code)
    name = _esc(display_name.value)
    trade = _esc(business.kind.value.replace("_", " "))
    address = _address(business, locale)

    contact_rows = []
    for key, label in _CONTACT_ORDER:
        value = business.get(key)
        if isinstance(value, Fact):
            shown = _esc(value.value)
            href = (f"tel:{value.value}" if key == "phone" else f"mailto:{value.value}")
            contact_rows.append(f'<p class="big"><a href="{_esc(href)}">{shown}</a></p>')
    if address:
        contact_rows.append(f'<p class="big">{_esc(address)}</p>')
    map_link = _map_link(business, locale)
    if map_link:
        contact_rows.append(map_link)
    contact = (f'<section class="card"><h2>{_esc(locale.text("find_us"))}</h2>'
               f'{"".join(contact_rows)}</section>'
               if contact_rows else "")

    figures, credits = _images_block(images, locale)
    figures_block = (f'<section class="figures">{figures}</section>' if figures else "")

    gaps = "".join(f'<div class="gap"><h3>{_esc(locale.text(title))}</h3>'
                   f'<p>{_esc(locale.text(body))}</p></div>'
                   for title, body in _GAP_KEYS)

    source_items = "".join(f"<li>{_esc(s)}</li>" for s in sources)

    return f"""<!doctype html>
<html lang="{locale.code}" dir="{locale.direction}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>{name}</title>
<style>{STYLE}</style>
</head>
<body>
<div class="banner"><strong>{_esc(locale.text("banner_lead"))}</strong>
{_esc(locale.text("banner_body", operator=operator, name=display_name.value))}</div>
<div class="wrap">
<header>
  <h1>{name}</h1>
  <p class="trade">{trade}</p>
</header>
{figures_block}
{contact}
{_hours_rows(business, locale)}
<section>
  <h2>{_esc(locale.text("missing_heading"))}</h2>
  {gaps}
</section>
<footer>
  <p>{_esc(locale.text("sources_intro"))}</p>
  <ul>{source_items}</ul>
  {credits}
  <p>{_esc(locale.text("attribution_note"))}</p>
  <p>{_esc(locale.text("prepared_by", operator=operator))}</p>
</footer>
</div>
</body>
</html>
"""
