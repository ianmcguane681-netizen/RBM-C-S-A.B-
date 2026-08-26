"""The reference render: a page good enough to send, built only from facts.

**Still the fallback, not the product** — `brief.py` says why one layout stamped across a
county is worth what a template is worth. What changed is the floor. A plain page proved
nothing except that the pipeline ran; a business owner opening it on a phone has to feel
that somebody made them something, in the first two seconds, or the rest of the email does
not get read.

So this page is built the way the standard says a small business page should be built, and
`standard.py` is run over its own output. That is the discipline the whole file exists
for: **the sample is measured by the same criteria used to decide the business's own site
was deficient.** A tool that emails somebody about their missing viewport tag, attaching a
page that renders at desktop width, deserves the reply it gets.

Concretely, and all of it from facts:

- a tappable `tel:` link, and a fixed call bar on a phone, because a local visitor's next
  action is a phone call and everything else on the page is in service of it
- opening hours and an address where a person standing in the street can read them
- `LocalBusiness` JSON-LD assembled from the same facts printed on the page, so the map
  card and the answer box carry them too
- one `<h1>`, a title, a description, a language, an icon
- type that is large enough to read at arm's length, a layout that has never heard of a
  fixed pixel width, and photographs that carry their own labels

## What is still not here, and will not be

Headlines. "Keep the frame, change everything else" is a good line and nobody at this
business said it. The `<h1>` is their name and the sub-heading is their trade, both facts,
and the space where the copy would go is labelled as a space. That is the constraint that
makes a designed page necessary rather than optional, which is the honest position: this
render is a good page, and the one worth sending is written with the owner.
"""
from __future__ import annotations

import html
import json
import re
from typing import Any, Mapping, Sequence

from prospector.business import Business, Fact
from prospector.locales import CATALOGUE, NUMBER_LAST, RTL, Locale
from prospector.states import SUBJECT_OWN, SUBJECT_SUPPLIED

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


#: An inline mark rather than a photograph: an icon in the tab is one of the criteria, and
#: a business's real logo is theirs and is not on the map.
FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 "
           "32'%3E%3Crect width='32' height='32' rx='7' fill='%23191714'/%3E%3Ctext x='16'"
           " y='23' font-family='Georgia,serif' font-size='19' fill='%23f2ede5' "
           "text-anchor='middle'%3E%E2%97%8F%3C/text%3E%3C/svg%3E")

STYLE = """
:root{--ink:#191714;--muted:#6b6155;--line:#e4ded4;--bg:#faf7f2;--card:#fff;
--accent:#a8511f;--accent-ink:#fff;--band:#efe8dd;
--warn-bg:#fff6e6;--warn-line:#e3b978;--warn-ink:#5a3d12;--shadow:rgba(25,23,20,.09)}
@media (prefers-color-scheme:dark){:root{--ink:#f4efe7;--muted:#a99f92;--line:#332f2a;
--bg:#141311;--card:#1d1b18;--accent:#e0925c;--accent-ink:#191714;--band:#1a1815;
--warn-bg:#2a2318;--warn-line:#6b552f;--warn-ink:#e8cfa4;--shadow:rgba(0,0,0,.4)}}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);
font:17px/1.65 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,
sans-serif;overflow-x:hidden}
.serif{font-family:ui-serif,Georgia,"Iowan Old Style","Times New Roman",serif}
.wrap{width:100%;max-width:66rem;margin:0 auto;padding:0 clamp(20px,5vw,40px)}
a{color:var(--accent)}
.banner{background:var(--warn-bg);border-bottom:1px solid var(--warn-line);
color:var(--warn-ink);padding:11px clamp(20px,5vw,40px);font-size:13.5px;line-height:1.55}
.banner strong{font-weight:650}
.top{display:flex;align-items:center;justify-content:space-between;gap:16px;
padding:18px 0;border-bottom:1px solid var(--line)}
.mark{font-weight:600;font-size:17px;letter-spacing:-.01em}
.btn{display:inline-block;background:var(--accent);color:var(--accent-ink);
text-decoration:none;font-weight:600;font-size:15px;padding:11px 18px;border-radius:9px;
white-space:nowrap}
.btn.ghost{background:transparent;color:var(--ink);border:1px solid var(--line)}
.hero{position:relative;margin:0;padding:clamp(48px,9vw,104px) 0 clamp(36px,7vw,72px)}
.hero.has-photo{color:#f6f1e9;background:#141311}
.hero .photo{position:absolute;inset:0;overflow:hidden}
.hero .photo img{width:100%;height:100%;object-fit:cover;opacity:.5}
.hero .inner{position:relative}
.kicker{font-size:12.5px;letter-spacing:.14em;text-transform:uppercase;
color:var(--accent);font-weight:600;margin:0 0 14px}
.hero.has-photo .kicker{color:#e9a874}
h1{font-size:clamp(38px,8.5vw,68px);line-height:1.04;letter-spacing:-.02em;
margin:0 0 14px;font-weight:600}
.trade{font-size:clamp(17px,2.4vw,21px);color:var(--muted);margin:0 0 26px;max-width:30ch}
.hero.has-photo .trade{color:#ddd3c6}
.herocredit{font-size:12px;color:var(--muted);margin:0 0 18px;max-width:52ch}
.hero.has-photo .herocredit{color:#c9bfb2}
.actions{display:flex;flex-wrap:wrap;gap:10px}
.facts{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));
border-top:1px solid var(--line);background:var(--band)}
.fact{padding:20px clamp(20px,5vw,28px);border-right:1px solid var(--line)}
.fact:last-child{border-right:0}
.fact dt{font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);
margin:0 0 6px}
.fact dd{margin:0;font-size:17px;font-weight:550;line-height:1.4;overflow-wrap:anywhere}
.fact dd a{text-decoration:none}
section{padding:clamp(44px,7vw,80px) 0}
h2{font-size:clamp(26px,4.4vw,38px);line-height:1.15;letter-spacing:-.015em;margin:0 0 18px;
font-weight:600}
h3{font-size:17px;margin:0 0 5px;font-weight:600}
.lede{color:var(--muted);max-width:56ch;margin:0 0 26px}
.big-lede{color:var(--ink);font-size:clamp(20px,3vw,26px);line-height:1.45;max-width:34ch}
.hours{white-space:pre-wrap;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
font-size:16px;margin:0}
.note{color:var(--muted);font-size:13.5px;margin:12px 0 0}
.gallery{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(min(100%,260px),1fr))}
figure{margin:0;border-radius:14px;overflow:hidden;background:var(--card);
box-shadow:0 1px 3px var(--shadow)}
figure img{width:100%;height:auto;display:block;aspect-ratio:4/3;object-fit:cover}
figcaption{color:var(--muted);font-size:12.5px;padding:10px 14px}
.gaps{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(min(100%,240px),1fr))}
.gap{border:1px dashed var(--line);border-radius:14px;padding:20px}
.gap p{margin:0;color:var(--muted);font-size:14.5px}
.visit{background:var(--band);border-top:1px solid var(--line)}
.rows{border-top:1px solid var(--line)}
.row{display:flex;flex-wrap:wrap;gap:6px 24px;padding:14px 0;
border-bottom:1px solid var(--line)}
.row dt{width:9rem;color:var(--muted);font-size:12px;letter-spacing:.1em;
text-transform:uppercase;margin:3px 0 0}
.row dd{margin:0;flex:1 1 14rem;overflow-wrap:anywhere}
footer{padding:36px 0 120px;border-top:1px solid var(--line);color:var(--muted);
font-size:13px}
footer ul{padding-left:18px;margin:8px 0}
.callbar{position:fixed;left:0;right:0;bottom:0;display:none;gap:10px;padding:10px 14px
env(safe-area-inset-bottom);background:var(--card);border-top:1px solid var(--line);
box-shadow:0 -2px 14px var(--shadow);z-index:9}
.callbar .btn{flex:1;text-align:center;padding:14px 18px;font-size:16px}
@media (max-width:640px){.callbar{display:flex}.fact{border-right:0;
border-bottom:1px solid var(--line)}}
[dir="rtl"] .row dt{text-align:right}
"""


def _json_ld(business: Business, locale: Locale, display_name: str,
             address: str) -> str:
    """`LocalBusiness`, built from the same facts printed on the page and nothing else.

    This is the criterion most small sites fail and the one with the most direct payoff:
    the hours, the address and the number in the map card and the answer box come from
    here. Assembled field by field rather than from a template, so a fact that is absent
    is absent from the mark-up too — an empty `telephone` would be a claim that there is
    no number.
    """

    data: dict[str, object] = {"@context": "https://schema.org",
                               "@type": "LocalBusiness", "name": display_name}
    phone = business.get("phone")
    if isinstance(phone, Fact):
        data["telephone"] = phone.value
    email = business.get("email")
    if isinstance(email, Fact):
        data["email"] = email.value
    if address:
        postal: dict[str, str] = {"@type": "PostalAddress"}
        street = business.get("street")
        number = business.get("housenumber")
        if isinstance(street, Fact):
            postal["streetAddress"] = (f"{street.value} {number.value}"
                                       if isinstance(number, Fact) and
                                       locale.address_order == NUMBER_LAST
                                       else (f"{number.value} {street.value}"
                                             if isinstance(number, Fact) else street.value))
        for key, field_name in (("city", "addressLocality"), ("postcode", "postalCode")):
            value = business.get(key)
            if isinstance(value, Fact):
                postal[field_name] = value.value
        data["address"] = postal
    hours = business.get("opening_hours")
    if isinstance(hours, Fact):
        # Printed in the OSM syntax it was recorded in. Expanding it into schema.org's
        # format means interpreting a small language with edge cases, and an interpretation
        # error here publishes wrong opening times over somebody's name.
        data["openingHours"] = hours.value
    raw = business.raw or {}
    lat, lon = raw.get("lat"), raw.get("lon")
    if lat is None or lon is None:
        centre = raw.get("center") or {}
        lat, lon = centre.get("lat"), centre.get("lon")
    if lat is not None and lon is not None:
        data["geo"] = {"@type": "GeoCoordinates", "latitude": lat, "longitude": lon}
    # `<` escaped, because a business name containing `</script>` would otherwise close
    # the block and everything after it would be markup. json.dumps escapes quotes and
    # nothing else, and this is a page built from a name a stranger controls.
    return (json.dumps(data, ensure_ascii=False, indent=1)
            .replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026"))


def _map_href(business: Business) -> str:
    raw = business.raw or {}
    lat, lon = raw.get("lat"), raw.get("lon")
    if lat is None or lon is None:
        centre = raw.get("center") or {}
        lat, lon = centre.get("lat"), centre.get("lon")
    if lat is None or lon is None:
        return ""
    return f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=18/{lat}/{lon}"


def _caption_for(image, locale: Locale) -> tuple[str, str]:
    if image.provenance == SUBJECT_SUPPLIED:
        # The only provenance with no question attached: they own it and they sent it.
        return locale.text("supplied_caption"), locale.text("own_alt")
    if image.provenance == SUBJECT_OWN:
        return locale.text("own_caption"), locale.text("own_alt")
    return locale.text("stock_caption"), locale.text("stock_alt")


def _figure(image, locale: Locale) -> str:
    src = image.local_path or image.url
    if image.provenance in (SUBJECT_OWN, SUBJECT_SUPPLIED):
        caption, alt = _caption_for(image, locale)
    else:
        caption, alt = locale.text("stock_caption"), locale.text("stock_alt")
    return (f'<figure><img src="{_esc(src)}" alt="{_esc(alt)}" loading="lazy">'
            f'<figcaption>{_esc(caption)}</figcaption></figure>')


def render(business: Business, *, operator: str, sources: Sequence[str] = (),
           images: Sequence = (), locale: Locale | str = "en",
           copy: Mapping[str, str] | None = None, authorisation: Any = None) -> str:
    """One self-contained page.

    `copy` is what the business itself sent back — see `handover.py`. It is printed as
    written. Nothing here composes, improves or extends it, because a sentence about a
    business written by anything other than that business is invention however good it
    sounds.

    `authorisation` turns the sample into their site. Passing one removes the "unofficial
    sample" banner and the `noindex` — the moment a page stops being speculative work and
    becomes a business's public face — so it is validated rather than believed, and a
    record that does not permit publishing raises instead of quietly rendering a sample.
    """

    if not operator.strip():
        raise ValueError("a sample page must name the person who prepared it")
    published = False
    if authorisation is not None:
        from prospector.engagement import NotAuthorised, PUBLISH

        if not getattr(authorisation, "permits", lambda scope: False)(PUBLISH):
            raise NotAuthorised(
                "the authorisation passed to render() does not permit PUBLISH, so the "
                "sample banner cannot come off. Publishing is the one thing in this "
                "package that a flag does not decide.")
        published = True
    if isinstance(locale, str):
        # A code with no strings raises rather than falling back: `locales.choose` is where
        # an unavailable language is turned into a refusal, and reaching here with one
        # means that stage was skipped.
        locale = CATALOGUE[locale]

    copy = dict(copy or {})
    display = business.name_in(locale.code)
    name = display.value
    trade = business.kind.value.replace("_", " ")
    address = _address(business, locale)
    phone = business.get("phone")
    email = business.get("email")
    hours = business.get("opening_hours")
    city = business.get("city")
    map_href = _map_href(business)

    tel = ""
    if isinstance(phone, Fact):
        # Everything but digits and a leading plus, because a tel: link with spaces in it
        # is a link some phones will not dial.
        cleaned = re.sub(r"[^\d+]", "", phone.value)
        tel = (f'<a class="btn" href="tel:{_esc(cleaned)}">'
               f'{_esc(locale.text("call_action"))}</a>')

    hero_photo = ""
    hero_credit = ""
    gallery_images = list(images)
    if gallery_images:
        first = gallery_images.pop(0)
        own = first.provenance == SUBJECT_OWN
        alt = locale.text("own_alt") if own else locale.text("stock_alt")
        hero_photo = (f'<div class="photo"><img src="{_esc(first.local_path or first.url)}"'
                      f' alt="{_esc(alt)}"></div>')
        # The label follows the photograph into the hero. A stock image used as a backdrop
        # behind a business's name is the strongest version of the claim it must not make,
        # so the caption is not something the layout gets to drop.
        caption = locale.text("own_caption") if own else locale.text("stock_caption")
        hero_credit = f'<p class="herocredit">{_esc(caption)}</p>'
        if first.attribution:
            hero_credit = (f'<p class="herocredit">{_esc(caption)} '
                           f'{_esc(first.attribution)}</p>')

    facts_cells = []
    if isinstance(phone, Fact):
        cleaned = re.sub(r"[^\d+]", "", phone.value)
        facts_cells.append(f'<div class="fact"><dt>{_esc(locale.text("call_action"))}</dt>'
                           f'<dd><a href="tel:{_esc(cleaned)}">{_esc(phone.value)}</a></dd>'
                           f'</div>')
    if address:
        facts_cells.append(f'<div class="fact"><dt>{_esc(locale.text("find_us"))}</dt>'
                           f'<dd>{_esc(address)}</dd></div>')
    if isinstance(hours, Fact):
        facts_cells.append(f'<div class="fact"><dt>{_esc(locale.text("opening_hours"))}</dt>'
                           f'<dd>{_esc(hours.value)}</dd></div>')
    facts = f'<dl class="facts">{"".join(facts_cells)}</dl>' if facts_cells else ""

    gallery = ""
    if gallery_images:
        figures = "".join(_figure(image, locale) for image in gallery_images)
        gallery = f'<section class="wrap"><div class="gallery">{figures}</div></section>'

    credits = "".join(f"<li>{_esc(image.attribution)}</li>" for image in images
                      if image.attribution)

    # A gap the business has already filled is not a gap. The section disappears entirely
    # once they have answered all of it, which is what the page becoming theirs looks like.
    supplied_photo = any(getattr(i, "provenance", "") == SUBJECT_SUPPLIED for i in images)
    filled = {"gap_photos_title": supplied_photo,
              "gap_words_title": bool(copy.get("about")),
              "gap_services_title": bool(copy.get("services"))}
    gaps = "".join(f'<div class="gap"><h3>{_esc(locale.text(title))}</h3>'
                   f'<p>{_esc(locale.text(body))}</p></div>'
                   for title, body in _GAP_KEYS if not filled.get(title))

    # Their words, printed as written.
    words = ""
    if copy.get("about"):
        words += (f'<section class="wrap"><p class="lede serif big-lede">'
                  f'{_esc(copy["about"])}</p></section>')
    if copy.get("services"):
        words += (f'<section class="wrap"><h2 class="serif">'
                  f'{_esc(locale.text("gap_services_title"))}</h2>'
                  f'<p class="lede">{_esc(copy["services"])}</p></section>')

    visit_rows = []
    if address:
        link = (f' &middot; <a href="{_esc(map_href)}" rel="noopener">'
                f'{_esc(locale.text("map_link"))}</a>') if map_href else ""
        visit_rows.append(f'<div class="row"><dt>{_esc(locale.text("find_us"))}</dt>'
                          f'<dd>{_esc(address)}{link}</dd></div>')
    if isinstance(hours, Fact):
        visit_rows.append(f'<div class="row"><dt>{_esc(locale.text("opening_hours"))}</dt>'
                          f'<dd><span class="hours">{_esc(hours.value)}</span>'
                          f'<p class="note">{_esc(locale.text("hours_note"))}</p></dd></div>')
    if isinstance(phone, Fact):
        cleaned = re.sub(r"[^\d+]", "", phone.value)
        visit_rows.append(f'<div class="row"><dt>{_esc(locale.text("call_action"))}</dt>'
                          f'<dd><a href="tel:{_esc(cleaned)}">{_esc(phone.value)}</a></dd>'
                          f'</div>')
    if isinstance(email, Fact):
        visit_rows.append(f'<div class="row"><dt>Email</dt>'
                          f'<dd><a href="mailto:{_esc(email.value)}">{_esc(email.value)}</a>'
                          f'</dd></div>')
    visit = (f'<section class="visit"><div class="wrap"><h2 class="serif">'
             f'{_esc(locale.text("find_us"))}</h2><dl class="rows">'
             f'{"".join(visit_rows)}</dl></div></section>') if visit_rows else ""

    description = ", ".join(part for part in
                            (name, trade, city.value if isinstance(city, Fact) else "")
                            if part)
    # The ODbL attribution is a licence condition on OpenStreetMap data, so it appears
    # exactly when OSM data is still on the page — which after a handover is often not the
    # case, the business having corrected everything themselves.
    osm_sourced = any("openstreetmap" in str(s).lower() for s in sources)
    source_items = "".join(f"<li>{_esc(s)}</li>" for s in sources)
    kicker = " &middot; ".join(_esc(p) for p in
                               (trade, city.value if isinstance(city, Fact) else "") if p)

    return f"""<!doctype html>
<html lang="{locale.code}" dir="{locale.direction}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{'' if published else '<meta name="robots" content="noindex, nofollow">'}
<meta name="description" content="{_esc(description)}">
<meta property="og:title" content="{_esc(name)}">
<meta property="og:description" content="{_esc(description)}">
<meta property="og:image" content="{_esc(FAVICON)}">
<link rel="icon" href="{FAVICON}">
<title>{_esc(name)}</title>
<style>{STYLE}</style>
<script type="application/ld+json">
{_json_ld(business, locale, name, address)}
</script>
</head>
<body>
{'' if published else f'''<div class="banner"><strong>{_esc(locale.text("banner_lead"))}</strong>
{_esc(locale.text("banner_body", operator=operator, name=name))}</div>'''}
<div class="wrap">
  <div class="top"><span class="mark serif">{_esc(name)}</span>{tel}</div>
</div>
<header class="hero{' has-photo' if hero_photo else ''}">
  {hero_photo}
  <div class="wrap inner">
    <p class="kicker">{kicker}</p>
    <h1 class="serif">{_esc(name)}</h1>
    <p class="trade">{_esc(trade)}{(' &middot; ' + _esc(city.value)) if isinstance(city, Fact) else ''}</p>
    {hero_credit}
    <div class="actions">{tel}
      {f'<a class="btn ghost" href="{_esc(map_href)}" rel="noopener">{_esc(locale.text("map_link"))}</a>' if map_href else ''}
    </div>
  </div>
</header>
{facts}
{gallery}
{words}
{f'''<section class="wrap">
  <h2 class="serif">{_esc(locale.text("missing_heading"))}</h2>
  <div class="gaps">{gaps}</div>
</section>''' if gaps else ""}
{visit}
<footer><div class="wrap">
  <p>{_esc(locale.text("sources_intro"))}</p>
  <ul>{source_items}</ul>
  {f'<ul>{credits}</ul>' if credits else ''}
  {f'<p>{_esc(locale.text("attribution_note"))}</p>' if osm_sourced else ''}
  <p>{_esc(locale.text("prepared_by", operator=operator)) if not published
       else _esc(f"Built by {operator} for {name}.")}</p>
</div></footer>
{f'<nav class="callbar">{tel}</nav>' if tel else ''}
</body>
</html>
"""
