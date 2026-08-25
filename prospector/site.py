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
from prospector.states import SUBJECT_OWN

#: Fields that become the contact block, in the order a person reads them.
_CONTACT_ORDER = (("phone", "Phone"), ("email", "Email"))

_GAPS = (
    ("Photographs you actually like", "What is here is either your own, taken from your "
                                      "site, or labelled stock. Send better ones and they "
                                      "go straight in."),
    ("A sentence about what you do", "Written by you, or with you. Nothing on this page "
                                     "is invented, so this space is left as it is."),
    ("Services and prices", "The public listing does not carry them."),
)


def _esc(value: str) -> str:
    return html.escape(value, quote=True)


def _address(business: Business) -> str:
    parts = []
    number = business.get("housenumber")
    street = business.get("street")
    if isinstance(number, Fact) and isinstance(street, Fact):
        parts.append(f"{number.value} {street.value}")
    elif isinstance(street, Fact):
        parts.append(street.value)
    for key in ("city", "postcode"):
        value = business.get(key)
        if isinstance(value, Fact):
            parts.append(value.value)
    return ", ".join(parts)


def _hours_rows(business: Business) -> str:
    hours = business.get("opening_hours")
    if not isinstance(hours, Fact):
        return ""
    # Printed verbatim, in the OSM syntax it was recorded in, rather than expanded into
    # days of the week. Expanding it means interpreting a mini-language with edge cases
    # (PH off, Su 12:00-16:00, "off"), and an interpretation error here publishes wrong
    # opening times over a business's name.
    return (f'<section class="card"><h2>Opening hours</h2>'
            f'<p class="hours">{_esc(hours.value)}</p>'
            f'<p class="note">Recorded in the public listing in this form. Confirm before '
            f'this page goes anywhere near a customer.</p></section>')


def _map_link(business: Business) -> str:
    raw = business.raw or {}
    lat, lon = raw.get("lat"), raw.get("lon")
    if lat is None or lon is None:
        centre = raw.get("center") or {}
        lat, lon = centre.get("lat"), centre.get("lon")
    if lat is None or lon is None:
        return ""
    href = f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=18/{lat}/{lon}"
    return (f'<a class="maplink" href="{_esc(href)}" rel="noopener">'
            f'View on the map</a>')


STYLE = """
:root{--ink:#191714;--muted:#6b6155;--line:#e2dcd2;--bg:#faf7f2;--card:#fff;
--accent:#8a5a2b;--warn-bg:#fff6e6;--warn-line:#e3b978;--warn-ink:#5a3d12}
@media (prefers-color-scheme:dark){:root{--ink:#f2ede5;--muted:#a99f92;--line:#33302b;
--bg:#151412;--card:#1e1c19;--accent:#d9a56a;--warn-bg:#2a2318;--warn-line:#6b552f;--warn-ink:#e8cfa4}}
*{box-sizing:border-box}
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


def _images_block(images: Sequence, folder_relative: bool = True) -> tuple[str, str]:
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
            caption = "Your own photograph, from your website. Not republished anywhere."
            alt = "Photograph from the business's own website"
        else:
            caption = image.label or "Stock photograph — not this business's premises."
            alt = "Stock photograph"
        figures.append(f'<figure><img src="{_esc(src)}" alt="{_esc(alt)}" loading="lazy">'
                       f'<figcaption>{_esc(caption)}</figcaption></figure>')
        if image.attribution:
            credits.append(f"<li>{_esc(image.attribution)}</li>")
    return ("".join(figures),
            f"<ul>{''.join(credits)}</ul>" if credits else "")


def render(business: Business, *, operator: str, sources: Sequence[str] = (),
           images: Sequence = ()) -> str:
    """One self-contained HTML page. `operator` is the person whose sample this is.

    `operator` is required and unescapable-by-omission on purpose: an unsigned sample page
    carrying somebody else's business name is the artefact this function refuses to
    produce.
    """

    if not operator.strip():
        raise ValueError("a sample page must name the person who prepared it")

    name = _esc(business.name.value)
    trade = _esc(business.kind.value.replace("_", " "))
    address = _address(business)

    contact_rows = []
    for key, label in _CONTACT_ORDER:
        value = business.get(key)
        if isinstance(value, Fact):
            shown = _esc(value.value)
            href = (f"tel:{value.value}" if key == "phone" else f"mailto:{value.value}")
            contact_rows.append(f'<p class="big"><a href="{_esc(href)}">{shown}</a></p>')
    if address:
        contact_rows.append(f'<p class="big">{_esc(address)}</p>')
    map_link = _map_link(business)
    if map_link:
        contact_rows.append(map_link)
    contact = (f'<section class="card"><h2>Find us</h2>{"".join(contact_rows)}</section>'
               if contact_rows else "")

    figures, credits = _images_block(images)
    figures_block = (f'<section class="figures">{figures}</section>' if figures else "")

    gaps = "".join(f'<div class="gap"><h3>{_esc(title)}</h3><p>{_esc(why)}</p></div>'
                   for title, why in _GAPS)

    source_items = "".join(f"<li>{_esc(s)}</li>" for s in sources)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>{name}</title>
<style>{STYLE}</style>
</head>
<body>
<div class="banner"><strong>Unofficial sample.</strong> This page was prepared by
{_esc(operator)} from publicly listed information, as an example of what a site for
{name} could look like. It is not affiliated with, endorsed by, or connected to
{name}, and nothing on it was supplied by them.</div>
<div class="wrap">
<header>
  <h1>{name}</h1>
  <p class="trade">{trade}</p>
</header>
{figures_block}
{contact}
{_hours_rows(business)}
<section>
  <h2>What is missing from this sample</h2>
  {gaps}
</section>
<footer>
  <p>Every detail on this page came from a public source:</p>
  <ul>{source_items}</ul>
  {credits}
  <p>Business details from OpenStreetMap contributors, available under the Open Database
  Licence (ODbL). Photographs are either the business's own, taken from their own public
  website and shown back to them here, or stock photographs labelled as such and credited
  above.</p>
  <p>Prepared by {_esc(operator)}. Not published, not indexed, and yours to have or to
  have taken down.</p>
</footer>
</div>
</body>
</html>
"""
