"""Webatron: the agent that hands you one folder per business and one page to read first.

Everything in this package produces a piece of the picture — a sample site, a comparison,
an evidence file, a costing, a list of ways to reach somebody. Left as pieces they are a
directory listing, and a directory listing is not a thing anybody works from at eight in
the morning. Webatron is the assembly: for each business it writes `BRIEFING.html`, which
answers the four questions in the order they get asked.

    1. What did you build, and can I see it
    2. Who exactly am I contacting, and how
    3. Why should their site be this one — criterion by criterion, both sides measured
    4. What does this cost me to make, put up, secure and watch

And for the run as a whole it writes `WEBATRON.md`: every business, what was decided,
what is waiting on a person, and what the run cost as far as anybody has priced it.

## What Webatron is not, and the reason it is spelled out

It is a name for an assembly step. It proposes; it never authorises. Specifically, and
enforced elsewhere in this package rather than promised here:

- **It cannot send anything.** There is no mail path in this package and a test asserts
  the absence. The briefing is a file; a person reads it and decides.
- **It cannot publish.** Removing the "unofficial sample" banner needs an `Authorisation`
  naming a person at the business, and the constructor refuses automation prefixes.
- **It cannot sign a page.** `--operator` names a human, and `webatron` is refused there
  alongside `agent:` and `bot:` — a page carrying a stranger's business name is signed by
  whoever stands over sending it, and that is not a program.

The parent repository's rule, carried forward intact: agent output is analysis or a
proposal, and is never evidence. Everything in a briefing traces to a measurement or a
fact with a source, which is what makes it worth reading rather than worth believing.
"""
from __future__ import annotations

import html as html_module
import json
import shlex
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from prospector import case as case_mod, contacts as contacts_mod, costs as costs_mod
from prospector import standard
from prospector.states import NO_SITE_FOUND, NO_SITE_LISTED

NAME = "Webatron"
BRIEFING = "BRIEFING.html"
DIGEST = "WEBATRON.md"


def _esc(value: str) -> str:
    return html_module.escape(str(value or ""), quote=True)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True, slots=True)
class Prepared:
    """One business Webatron has something to say about."""

    identity: str
    name: str
    folder: Path
    contacts: contacts_mod.Contacts
    case: case_mod.Case
    presence_status: str = ""
    language: str = "en"
    language_reviewed: bool = True
    unknowns: tuple[str, ...] = ()

    @property
    def blocked_on_a_person(self) -> tuple[str, ...]:
        """Everything a person has to decide before this one can go anywhere."""

        waiting = list(self.unknowns)
        if self.contacts.status != contacts_mod.ROUTES_FOUND:
            waiting.append("no published contact route, so there is nowhere to send this")
        if not self.language_reviewed:
            waiting.append(f"the {self.language} translation has not been read by anybody "
                           f"who speaks it")
        if self.presence_status == NO_SITE_LISTED:
            waiting.append("absence of a website is NOT established — the note must not "
                           "say they have none")
        if self.case.not_addressed:
            waiting.append(f"{len(self.case.not_addressed)} failing criterion/criteria the "
                           f"sample does not fix")
        return tuple(waiting)


STYLE = """
:root{--ink:#191714;--muted:#6b6155;--line:#e4ded4;--bg:#faf7f2;--card:#fff;
--accent:#a8511f;--bad:#8c2f16;--good:#2f6a43}
@media (prefers-color-scheme:dark){:root{--ink:#f4efe7;--muted:#a99f92;--line:#332f2a;
--bg:#141311;--card:#1d1b18;--accent:#e0925c;--bad:#e0836a;--good:#77b98d}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:16px/1.62 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial}
.wrap{max-width:62rem;margin:0 auto;padding:34px clamp(18px,4vw,32px) 80px}
.serif{font-family:ui-serif,Georgia,"Iowan Old Style",serif}
.kicker{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);
font-weight:600;margin:0 0 8px}
h1{font-size:clamp(28px,5vw,42px);line-height:1.1;margin:0 0 10px;letter-spacing:-.02em}
.sub{color:var(--muted);margin:0 0 26px}
h2{font-size:13px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);
margin:38px 0 12px;font-weight:600;border-top:1px solid var(--line);padding-top:16px}
.cards{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(min(100%,240px),1fr))}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px 18px}
.card .label{font-size:11.5px;letter-spacing:.1em;text-transform:uppercase;
color:var(--muted);margin:0 0 6px}
.card .value{font-size:18px;font-weight:600;margin:0;overflow-wrap:anywhere}
.card .value a{color:var(--accent);text-decoration:none}
.card .note{color:var(--muted);font-size:13px;margin:8px 0 0}
.src{color:var(--muted);font-size:11.5px;font-family:ui-monospace,Menlo,monospace;
margin:6px 0 0}
table{width:100%;border-collapse:collapse;font-size:14.5px}
th{text-align:left;font-size:11.5px;letter-spacing:.1em;text-transform:uppercase;
color:var(--muted);font-weight:600;padding:0 10px 8px 0}
td{border-top:1px solid var(--line);padding:11px 10px 11px 0;vertical-align:top}
td.theirs{color:var(--bad)}
td.ours{color:var(--good)}
.tier{font-family:ui-monospace,Menlo,monospace;font-size:11px;color:var(--muted)}
.why{color:var(--muted);font-size:13.5px;margin:6px 0 0}
.warn{background:#fff6e6;border:1px solid #e3b978;color:#5a3d12;border-radius:14px;
padding:16px 18px;margin:14px 0}
@media (prefers-color-scheme:dark){.warn{background:#2a2318;border-color:#6b552f;
color:#e8cfa4}}
.warn ul{margin:8px 0 0;padding-left:18px}
pre{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;
overflow-x:auto;font-size:12.5px;line-height:1.5}
.shots{display:grid;gap:16px;grid-template-columns:repeat(auto-fit,minmax(min(100%,240px),1fr))}
.shots figure{margin:0}
.shots img{width:100%;height:auto;border:1px solid var(--line);border-radius:14px;
max-height:60vh;object-fit:cover;object-position:top}
.shots figcaption{color:var(--muted);font-size:12.5px;margin-top:8px}
.files a{display:inline-block;margin:0 14px 8px 0}
footer{margin-top:40px;border-top:1px solid var(--line);padding-top:16px;color:var(--muted);
font-size:12.5px}
"""


def _contacts_html(contacts: contacts_mod.Contacts) -> str:
    if contacts.status != contacts_mod.ROUTES_FOUND:
        return f'<div class="warn">{_esc(contacts.describe())}</div>'
    cards = []
    for route in contacts.routes:
        value = (f'<a href="{_esc(route.href)}">{_esc(route.value)}</a>' if route.href
                 else _esc(route.value))
        cards.append(f'<div class="card"><p class="label">{_esc(route.kind)}</p>'
                     f'<p class="value">{value}</p>'
                     f'<p class="note">{_esc(route.note)}</p>'
                     f'<p class="src">{_esc(route.source)}</p></div>')
    named = ""
    if contacts.named_person:
        named = (f'<p class="note">Ask for {_esc(contacts.named_person)} — published by '
                 f'them: {_esc(contacts.named_person_source)}</p>')
    return f'<div class="cards">{"".join(cards)}</div>{named}'


def _case_html(case: case_mod.Case) -> str:
    if case.status == case_mod.NO_SITE_TO_COMPARE:
        rows = "".join(
            f'<tr><td><span class="tier">{_esc(point.tier)}</span><br>'
            f'<strong>{_esc(point.title)}</strong>'
            f'<p class="why">{_esc(point.why)}</p></td>'
            f'<td class="theirs">{_esc(point.theirs)}</td>'
            f'<td class="ours">{_esc(point.ours)}</td></tr>' for point in case.offered)
        return (f'<p class="sub">{_esc(case.reason)} — so there is nothing to be better '
                f'than. The case is what this page does that nothing currently does for '
                f'them.</p><table><thead><tr><th>Criterion</th><th>Today</th>'
                f'<th>The one we built</th></tr></thead><tbody>{rows}</tbody></table>')
    if case.status != case_mod.CASE_MADE:
        return f'<div class="warn">{_esc(case.describe())}</div>'
    rows = []
    for point in case.fixed:
        rows.append(
            f'<tr><td><span class="tier">{_esc(point.tier)}</span><br>'
            f'<strong>{_esc(point.title)}</strong>'
            f'<p class="why">{_esc(point.why)}</p></td>'
            f'<td class="theirs">{_esc(point.theirs)}</td>'
            f'<td class="ours">{_esc(point.ours)}</td></tr>')
    table = (f'<table><thead><tr><th>Criterion</th><th>Their site</th>'
             f'<th>The one we built</th></tr></thead><tbody>{"".join(rows)}</tbody></table>')
    if case.not_addressed:
        items = "".join(f"<li><strong>{_esc(point.title)}</strong> — theirs: "
                        f"{_esc(point.theirs)}; ours: {_esc(point.ours)}</li>"
                        for point in case.not_addressed)
        table += (f'<div class="warn"><strong>Not fixed by the sample, and worth saying so '
                  f'rather than leaving out:</strong><ul>{items}</ul></div>')
    if case.craft:
        table += (f'<p class="why">Also improved, and not a reason to write to anybody: '
                  f'{_esc(", ".join(point.title for point in case.craft))}.</p>')
    return table


def _shots_html(folder: Path) -> str:
    pairs = [("their-site-mobile.png", "Their site today, at the size of a phone screen"),
             ("sample-mobile.png", "The sample, same size, nothing drawn on either")]
    figures = [f'<figure><img src="{name}" alt="{_esc(caption)}">'
               f'<figcaption>{_esc(caption)}</figcaption></figure>'
               for name, caption in pairs if (folder / name).exists()]
    if not figures:
        return ('<div class="warn">No screenshots. Either no browser was available or the '
                'capture was incomplete — a render whose stylesheets did not arrive is a '
                'picture of a bad day rather than of their website, and is never shown.'
                '</div>')
    return f'<div class="shots">{"".join(figures)}</div>'


def write_briefing(prepared: Prepared, *, operator: str, costing: costs_mod.Costing,
                   folder: Path | None = None) -> Path:
    """The one page to read before picking up the phone."""

    folder = Path(folder or prepared.folder)
    waiting = prepared.blocked_on_a_person
    warn = ""
    if waiting:
        items = "".join(f"<li>{_esc(item)}</li>" for item in waiting)
        count = "1 thing needs" if len(waiting) == 1 else f"{len(waiting)} things need"
        warn = (f'<div class="warn"><strong>Before this goes anywhere, {count} '
                f'you:</strong><ul>{items}</ul></div>')
    files = "".join(
        f'<a href="{name}">{_esc(label)}</a>'
        for name, label in (("index.html", "The site we built"),
                            ("COMPARISON.html", "Before and after"),
                            ("NOTE.md", "Draft note"),
                            ("BRIEF.md", "Design brief"),
                            ("EVIDENCE.md", "Evidence"),
                            ("VERIFY.md", "Verification"),
                            ("OWNER-SUPPLIED.json", "Their reply goes here"))
        if (folder / name).exists())

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>{_esc(prepared.name)} — {NAME} briefing</title>
<style>{STYLE}</style>
</head>
<body><div class="wrap">
<p class="kicker">{NAME} briefing · {_esc(_now())}</p>
<h1 class="serif">{_esc(prepared.name)}</h1>
<p class="sub">Prepared for {_esc(operator)}. Nothing here has been sent to anybody, and
nothing has been published.</p>
{warn}
<h2>The site we built</h2>
{_shots_html(folder)}
<p class="files" style="margin-top:16px">{files}</p>
<h2>How to reach them</h2>
{_contacts_html(prepared.contacts)}
<h2>Why their site should be this one</h2>
{_case_html(prepared.case)}
<h2>What this costs</h2>
<pre>{_esc(costing.describe())}</pre>
<footer>Assembled by {NAME}, which proposes and never authorises.
It cannot send, it cannot publish, and it cannot sign a page.
Every line above traces to a measurement or to a fact with a source — see EVIDENCE.md.</footer>
</div></body>
</html>
"""
    path = folder / BRIEFING
    path.write_text(page, encoding="utf-8")
    return path


def write_digest(prepared: Sequence[Prepared], *, out_dir: Path, operator: str,
                 costing: costs_mod.Costing, area: str = "",
                 refused: Sequence[str] = (), indeterminate: Sequence[str] = (),
                 live: int = 0) -> Path:
    """One file for the whole run: what is ready, what is waiting, what it cost."""

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    lines = [f"# {NAME} — {area or 'run'} — {_now()}", "",
             f"Prepared for {operator}. {len(prepared)} briefing(s) ready to read, "
             f"{len(refused)} refused, {len(indeterminate)} indeterminate.", "",
             "Nothing has been sent and nothing has been published. Each briefing is a "
             "file; you decide what leaves the machine.", "",
             "## Ready to read", ""]
    if not prepared:
        lines.append("_Nothing was prepared in this run._")
    for item in prepared:
        waiting = item.blocked_on_a_person
        mark = ""
        if waiting:
            mark = (" — **1 thing needs you**" if len(waiting) == 1
                    else f" — **{len(waiting)} things need you**")
        best = item.contacts.best
        route = f"{best.kind.lower()} {best.value}" if best else "no contact route"
        if item.case.status == case_mod.NO_SITE_TO_COMPARE:
            # Worded from what was established, not from what would sell better: a silent
            # directory is "nothing listed", and only a search that looked supports "none".
            head = ("no website found" if "search found" in item.case.reason
                    else "no site listed for them")
            summary = f"{head} · {len(item.case.offered)} things the sample does"
        else:
            summary = f"{len(item.case.fixed)} point(s) in the case"
        lines.append(f"- **{item.name}** ({route}) · {summary}{mark}")
        lines.append(f"  `{item.folder}/{BRIEFING}`")
        for reason in waiting:
            lines.append(f"    - {reason}")
    if refused:
        lines += ["", "## Refused, and by which stage", ""]
        lines += [f"- {line}" for line in refused]
    if indeterminate:
        lines += ["", "## Indeterminate — not a refusal, and not nothing", ""]
        lines += [f"- {line}" for line in indeterminate]
    lines += ["", "## Money", "", "```", costing.describe(), "",
              costs_mod.cost_of_a_run(costing, prepared=len(prepared), live=live), "```", ""]
    path = out_dir / DIGEST
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def notify(command: str, digest: Path) -> tuple[bool, str]:
    """Hand the digest to whatever the operator uses, and say honestly how it went.

    A command rather than a mail client, for the reason the rest of the package has no mail
    path: the moment this could send, the question of what it might send to whom becomes
    live. This runs something the operator wrote, with the digest path substituted, and
    reports the exit code rather than swallowing it — a notifier that fails silently is a
    run nobody hears about, which is worse than no notifier at all.
    """

    if not command:
        return False, "no command configured"
    parts = [part.replace("{digest}", str(digest)) for part in shlex.split(command)]
    try:
        finished = subprocess.run(parts, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"the notify command would not run: {exc!r}"
    if finished.returncode != 0:
        return False, (f"the notify command exited {finished.returncode}: "
                       f"{(finished.stderr or finished.stdout or '').strip()[:200]}")
    return True, "sent"
