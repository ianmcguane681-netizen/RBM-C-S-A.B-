"""Their site on a phone, next to the one you built, on one page.

This is the pitch. Everything else in the package exists to make sure the page on the right
is honest and the sentence in the note is defensible; this is the artefact that does the
persuading, and it persuades by not arguing. Two screenshots at the same size, taken the
same way, and underneath them the named criteria their site fails, each with the reason it
matters to them rather than to a developer.

Three rules, and they are the same three the sample page follows.

**Their screenshot is labelled with when it was taken and at what size.** A picture of
somebody's website with no date on it is a picture they cannot check, and the first thing
an owner will say is "that was before we fixed it".

**Nothing is annotated onto their screenshot.** No red circles, no arrows, no scores. The
findings are listed beside it in words they can verify themselves by opening their own site
on their own phone.

**A capture that could not load their stylesheets never appears here.** `browser.py`
returns `CAPTURE_INCOMPLETE` for that, and a page built from it would be showing a stranger
a broken version of their own work and calling it their website.
"""
from __future__ import annotations

import html as html_module
from typing import Any, Sequence

from prospector import standard


def _esc(value: str) -> str:
    return html_module.escape(value or "", quote=True)


STYLE = """
:root{--ink:#191714;--muted:#6b6155;--line:#e4ded4;--bg:#faf7f2;--card:#fff;
--accent:#a8511f;--bad:#8c2f16}
@media (prefers-color-scheme:dark){:root{--ink:#f4efe7;--muted:#a99f92;--line:#332f2a;
--bg:#141311;--card:#1d1b18;--accent:#e0925c;--bad:#e0836a}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:16px/1.6 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial}
.wrap{max-width:60rem;margin:0 auto;padding:36px clamp(18px,4vw,32px) 72px}
h1{font-family:ui-serif,Georgia,serif;font-size:clamp(26px,4.4vw,36px);line-height:1.15;
margin:0 0 8px;letter-spacing:-.015em}
.sub{color:var(--muted);margin:0 0 30px;max-width:60ch}
.pair{display:grid;gap:22px;grid-template-columns:repeat(auto-fit,minmax(min(100%,260px),1fr))}
.side h2{font-size:13px;letter-spacing:.11em;text-transform:uppercase;color:var(--muted);
margin:0 0 10px}
.frame{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:8px;
overflow:hidden}
.frame img{width:100%;height:auto;display:block;border-radius:12px;
max-height:70vh;object-fit:cover;object-position:top}
.meta{color:var(--muted);font-size:12.5px;margin:9px 2px 0}
.missing{border:1px dashed var(--line);border-radius:18px;padding:26px;color:var(--muted);
font-size:14.5px}
h3{font-size:19px;margin:34px 0 12px;font-family:ui-serif,Georgia,serif}
ul.findings{list-style:none;padding:0;margin:0}
ul.findings li{border-top:1px solid var(--line);padding:14px 0}
.code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px;
color:var(--bad);letter-spacing:.03em}
.what{font-weight:600;margin:2px 0 4px}
.why{color:var(--muted);font-size:14.5px;margin:0}
footer{margin-top:38px;border-top:1px solid var(--line);padding-top:18px;
color:var(--muted);font-size:13px}
"""


def render(*, name: str, operator: str, their_capture: Any, sample_shot: str,
           report: Any = None, site_url: str = "") -> str:
    """One page holding both screenshots and the findings behind the approach."""

    usable = bool(their_capture is not None
                  and getattr(their_capture, "usable", False)
                  and getattr(their_capture, "screenshot_path", ""))
    if usable:
        theirs = (f'<div class="frame"><img src="{_esc(their_capture.screenshot_path)}" '
                  f'alt="{_esc(name)} as it renders on a phone"></div>'
                  f'<p class="meta">{_esc(site_url or their_capture.url)} · captured '
                  f'{_esc(their_capture.at)} · {their_capture.width}×'
                  f'{their_capture.height}, the size of a phone screen</p>')
    else:
        # Stated, not hidden. A missing panel with a reason is honest; a page that quietly
        # shows only the sample reads as a page that had nothing to compare against.
        reason = (their_capture.describe().splitlines()[1].strip()
                  if their_capture is not None and their_capture.describe().splitlines()[1:]
                  else "no capture was taken")
        theirs = (f'<div class="missing"><strong>No usable screenshot of the current '
                  f'site.</strong><br>{_esc(reason)}<br><br>Nothing is shown rather than '
                  f'something misleading: a render whose stylesheets did not arrive is a '
                  f'picture of a bad day, not of their website.</div>')

    findings = ""
    if report is not None:
        items = []
        for assessment in report.approachable_failures:
            items.append(
                f'<li><div class="code">{_esc(assessment.code)} · '
                f'{_esc(assessment.tier)}</div>'
                f'<p class="what">{_esc(assessment.criterion.title)} — '
                f'{_esc(assessment.detail)}</p>'
                f'<p class="why">{_esc(assessment.criterion.why)}</p></li>')
        if items:
            findings = (f'<h3>What the current site fails, and why it matters</h3>'
                        f'<ul class="findings">{"".join(items)}</ul>'
                        f'<p class="meta">Every one of these is checkable on your own '
                        f'phone in a minute. The full standard, including the things this '
                        f'site passes, is in STANDARD.md.</p>')

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>{_esc(name)} — before and after</title>
<style>{STYLE}</style>
</head>
<body><div class="wrap">
<h1>{_esc(name)}, on a phone</h1>
<p class="sub">Both screenshots are taken the same way, at the size of a phone screen. The
one on the left is the current site; the one on the right is a sample built from publicly
listed details. Nothing has been drawn on either.</p>
<div class="pair">
  <div class="side"><h2>The site today</h2>{theirs}</div>
  <div class="side"><h2>The sample</h2>
    <div class="frame"><img src="{_esc(sample_shot)}" alt="The sample site on a phone"></div>
    <p class="meta">A sample prepared by {_esc(operator)}. Not affiliated with
    {_esc(name)}, not published, and not indexed.</p>
  </div>
</div>
{findings}
<footer>Prepared by {_esc(operator)}. The sample is unofficial and carries that on its
face. Business details from OpenStreetMap contributors under the ODbL.</footer>
</div></body>
</html>
"""
