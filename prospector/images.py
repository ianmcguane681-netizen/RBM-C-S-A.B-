"""Photographs, from two places, each with a different obligation attached.

A page with no picture on it looks like a wireframe, and a wireframe does not do the job
this is for — the whole argument for building the thing first is that a finished page lands
differently from a proposal. So there are images. What matters is that neither kind is
allowed on the page silently.

**Their own photographs.** Taken from the business's own public website, with robots.txt
honoured, downloaded into the dossier rather than hotlinked, and never republished
anywhere. The page says whose they are. This is a photograph of that business shown back to
that business on a sample of their own site, and it is the one use where the ownership
question has an easy answer — but the answer is easy only because the page says it out
loud and the sample is not published. Facebook is not a source: it is behind a login wall,
the terms forbid it, and an image scraped from a social page is not clearly the business's
own work anyway.

**Licensed stock.** Openverse, filtered to licences that permit commercial use *and*
modification — so no NC, and no ND, because cropping is a derivative work. Every stock
image carries its licence and its attribution string into the dossier, and the attribution
is rendered on the page. That is a licence condition, not a courtesy.

## The rule that matters more than either

**A stock photograph of a barbershop, on a page headed with a barbershop's name, is a claim
about that barbershop's premises.** It is a fact-shaped thing on the page that did not come
from evidence, which is the defect this package spends most of its code refusing. So a
stock image is labelled where the reader sees it — "stock photograph, not <name>'s
premises" — and `verify.py` fails a page that carries one unlabelled.

That constraint is doing design work as much as legal work. A page that is honest about
which photograph is theirs and which is illustrative is a page whose first reply is often
"here are our actual photos", which is the conversation this is trying to start.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Protocol, Sequence

from prospector.states import (COULD_NOT_LOOK_FOR_IMAGES, IMAGES_FOUND, LICENSED_STOCK,
                               NO_IMAGE_FOUND, SUBJECT_OWN)

USER_AGENT = "prospector/0.1 (sample site builder; respects robots.txt)"
OPENVERSE = "https://api.openverse.org/v1/images/"

#: Commercial use and modification both permitted. NC is out because this is commercial
#: work; ND is out because resizing and cropping a photograph to fit a layout makes a
#: derivative, and a licence that forbids one forbids the layout.
OPENVERSE_LICENCE_FILTER = "commercial,modification"

#: Below this, a photograph is a logo, an icon or a tracking pixel rather than an image a
#: page can be built around.
MIN_WIDTH = 700
MAX_IMAGE_BYTES = 6 * 1024 * 1024


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True, slots=True)
class Image:
    """One photograph, where it came from, and what the page owes it."""

    url: str
    provenance: str
    retrieved_at: str
    #: The sentence the page must print beside a stock image. Empty for their own photos,
    #: which get their own sentence from the renderer.
    label: str = ""
    licence: str = ""
    licence_url: str = ""
    #: Whether the licence *obliges* credit. CC0 and the Public Domain Mark do not, and
    #: printing "attribution required" beside one trains a reader to disbelieve the line
    #: on the images where it is true.
    attribution_required: bool = True
    attribution: str = ""
    creator: str = ""
    title: str = ""
    source_page: str = ""
    #: A smaller copy offered by the source. Wikimedia in particular asks that automated
    #: callers take a thumbnail rather than the original, and answers 429 when they do not.
    thumbnail_url: str = ""
    width: int | None = None
    height: int | None = None
    local_path: str = ""

    @property
    def must_be_labelled(self) -> bool:
        """Whether omitting the label would make the page assert something untrue."""

        return self.provenance == LICENSED_STOCK

    @property
    def must_be_attributed(self) -> bool:
        return bool(self.attribution) and self.attribution_required


@dataclass(frozen=True, slots=True)
class ImageSet:
    """What was found for one business, or why nothing was."""

    status: str
    images: tuple[Image, ...] = ()
    reason: str = ""
    at: str = field(default_factory=_now)

    def describe(self) -> str:
        if self.status == IMAGES_FOUND:
            kinds = ", ".join(sorted({i.provenance for i in self.images}))
            return f"IMAGES_FOUND  {len(self.images)}  ({kinds})"
        if self.status == NO_IMAGE_FOUND:
            return ("NO_IMAGE_FOUND  looked, and nothing usable came back. The page keeps "
                    "its labelled gap, which is a decision rather than an omission.")
        return (f"COULD_NOT_LOOK_FOR_IMAGES  {self.reason}\n"
                f"  No image search happened. This is not the same as there being no "
                f"suitable image.")


class StockSource(Protocol):
    def search(self, query: str, *, limit: int = 3) -> ImageSet: ...


# --------------------------------------------------------------------------------------
# Their own photographs
# --------------------------------------------------------------------------------------

class _Images(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.srcs: list[str] = []
        self.og: list[str] = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "img":
            src = values.get("src") or values.get("data-src") or ""
            if src:
                self.srcs.append(src)
        elif tag == "meta":
            prop = (values.get("property") or values.get("name") or "").lower()
            if prop in ("og:image", "twitter:image") and values.get("content"):
                self.og.append(values["content"])


def _may_fetch(url: str, *, opener=urllib.request.urlopen) -> bool | None:
    """robots.txt, honoured. `None` when it could not be read.

    A robots file that cannot be read is not permission. It is the same third state as
    everywhere else, and here the cheap, correct response to not knowing is not to fetch.
    """

    parts = urllib.parse.urlsplit(url)
    robots_url = urllib.parse.urlunsplit((parts.scheme, parts.netloc, "/robots.txt", "", ""))
    try:
        request = urllib.request.Request(robots_url, headers={"User-Agent": USER_AGENT})
        with opener(request, timeout=10) as response:
            text = response.read(256 * 1024).decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        # No robots file is permission by convention; a 5xx is not an answer.
        if exc.code in (401, 403):
            return False
        if 400 <= exc.code < 500:
            return True
        return None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None
    parser = urllib.robotparser.RobotFileParser()
    parser.parse(text.splitlines())
    return parser.can_fetch(USER_AGENT, url)


def from_subject(site_url: str, *, fetcher=None, limit: int = 3) -> ImageSet:
    """Photographs from the business's own website, if it has one and permits reading it."""

    from prospector.condition import fetch as _fetch

    fetcher = fetcher or _fetch
    if not site_url:
        return ImageSet(COULD_NOT_LOOK_FOR_IMAGES,
                        reason="this business has no website to take photographs from")
    permitted = _may_fetch(site_url)
    if permitted is False:
        return ImageSet(COULD_NOT_LOOK_FOR_IMAGES,
                        reason=f"robots.txt at {site_url} disallows this reader")
    if permitted is None:
        return ImageSet(COULD_NOT_LOOK_FOR_IMAGES,
                        reason=f"robots.txt at {site_url} could not be read, and an "
                               f"unreadable robots file is not permission")
    page = fetcher(site_url)
    if not page.ok or not page.body:
        return ImageSet(COULD_NOT_LOOK_FOR_IMAGES,
                        reason=f"the site did not return a readable page: {page.error or page.status}")
    parser = _Images()
    try:
        parser.feed(page.body)
    except Exception as exc:  # noqa: BLE001 - tag soup is common and not fatal here
        return ImageSet(COULD_NOT_LOOK_FOR_IMAGES, reason=f"the markup would not parse: {exc!r}")

    base = page.final_url or site_url
    at = _now()
    found: list[Image] = []
    for src in parser.og + parser.srcs:
        absolute = urllib.parse.urljoin(base, src)
        if not absolute.lower().startswith(("http://", "https://")):
            continue
        if re.search(r"(logo|icon|sprite|pixel|spacer|badge)", absolute, re.I):
            continue
        if absolute.lower().endswith((".svg", ".gif")):
            continue
        found.append(Image(url=absolute, provenance=SUBJECT_OWN, retrieved_at=at,
                           source_page=base))
        if len(found) >= limit:
            break
    if not found:
        return ImageSet(NO_IMAGE_FOUND, reason=f"no photographs on {base}")
    return ImageSet(IMAGES_FOUND, tuple(found))


# --------------------------------------------------------------------------------------
# Licensed stock
# --------------------------------------------------------------------------------------

class Openverse:
    """Openverse, no key required, filtered to licences that permit what a sample does."""

    def __init__(self, endpoint: str = OPENVERSE, opener=urllib.request.urlopen) -> None:
        self.endpoint = endpoint
        self.opener = opener

    def search(self, query: str, *, limit: int = 3) -> ImageSet:
        params = urllib.parse.urlencode({
            "q": query, "page_size": max(limit * 3, 6), "size": "large",
            "license_type": OPENVERSE_LICENCE_FILTER, "mature": "false",
        })
        request = urllib.request.Request(f"{self.endpoint}?{params}",
                                         headers={"User-Agent": USER_AGENT,
                                                  "Accept": "application/json"})
        try:
            with self.opener(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError,
                ValueError) as exc:
            return ImageSet(COULD_NOT_LOOK_FOR_IMAGES, reason=f"Openverse: {exc!r}")

        at = _now()
        images: list[Image] = []
        for result in payload.get("results", []):
            licence = (result.get("license") or "").lower()
            # Belt and braces over the API filter: an ND image cannot be cropped to a
            # layout, and an NC image cannot be used in commercial work at all. Neither is
            # a judgement call to be made later by whoever is building the page.
            if "nd" in licence.split("-") or "nc" in licence.split("-"):
                continue
            width = result.get("width")
            if width and int(width) < MIN_WIDTH:
                continue
            images.append(Image(
                url=result.get("url", ""), provenance=LICENSED_STOCK, retrieved_at=at,
                label="Stock photograph — not this business's premises.",
                licence=_licence_name(licence, result.get("license_version", "")),
                attribution_required=licence not in ("cc0", "pdm"),
                licence_url=result.get("license_url", ""),
                attribution=result.get("attribution", ""),
                creator=result.get("creator", ""), title=result.get("title", ""),
                source_page=result.get("foreign_landing_url", ""),
                thumbnail_url=result.get("thumbnail", ""),
                width=width, height=result.get("height")))
            if len(images) >= limit * 3:
                # Candidates rather than a final selection. One host refusing an automated
                # download (Wikimedia rate-limits shared addresses hard) should cost a
                # photograph, not the page's whole image set, so the caller downloads down
                # the list until it has what it needs.
                break
        if not images:
            return ImageSet(NO_IMAGE_FOUND,
                            reason=f"nothing for {query!r} under a licence that permits "
                                   f"commercial use and modification")
        return ImageSet(IMAGES_FOUND, tuple(images))


def _licence_name(code: str, version: str) -> str:
    """`by-sa` + `4.0` -> `CC BY-SA 4.0`; `cc0` -> `CC0 1.0`, not `CC CC0 1.0`."""

    code = (code or "").lower()
    if code == "cc0":
        return f"CC0 {version}".strip()
    if code == "pdm":
        return "Public Domain Mark"
    return f"CC {code.upper()} {version}".strip()


def download(image: Image, into: Path, *, opener=urllib.request.urlopen,
             name_hint: str = "") -> Image:
    """Fetch the file into the dossier. Returns the image with `local_path` set, or as-is.

    Downloading rather than hotlinking, for two reasons that both matter: a sample page
    should not put load on the business's own server, and a page whose photograph vanishes
    when someone tidies their media library is worse than no page.
    """

    into.mkdir(parents=True, exist_ok=True)
    # Named for what it is rather than for its URL: several stock hosts encode the whole
    # path in base64, and an 80-character filename in a folder a person opens is noise.
    suffix = Path(urllib.parse.urlsplit(image.url).path).suffix.lower()
    if suffix not in (".jpg", ".jpeg", ".png", ".webp", ".avif"):
        suffix = ".jpg"
    stem = name_hint or ("theirs" if image.provenance == SUBJECT_OWN else "stock")
    name = f"{stem}{suffix}"
    target = into / name
    # The original first, the source's own thumbnail second. Wikimedia serves a large share
    # of Openverse and asks automated callers to take the smaller copy; it answers 429 when
    # they do not, and honouring that is both the polite reading and the one that works.
    for candidate in (image.url, image.thumbnail_url):
        if not candidate:
            continue
        try:
            request = urllib.request.Request(candidate, headers={"User-Agent": USER_AGENT})
            with opener(request, timeout=30) as response:
                kind = (response.headers.get("Content-Type") or "").lower()
                if not kind.startswith("image/"):
                    continue
                blob = response.read(MAX_IMAGE_BYTES)
            target.write_bytes(blob)
            return Image(**{**_as_dict(image), "local_path": name})
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
            continue
    # A failed download is not a missing photograph: the record of the image and where it
    # came from survives, and the caller must not report the set as found. See
    # `dossier.write`, which downgrades the status rather than reporting an empty success.
    return Image(**{**_as_dict(image), "local_path": ""})


def _as_dict(image: Image) -> dict:
    return {slot: getattr(image, slot) for slot in Image.__slots__}


def gather(*sets: ImageSet) -> ImageSet:
    """Combine sources, keeping the strongest status and every reason.

    Their own photographs first, always: a page showing a business its own premises is
    doing something a stock photograph cannot.
    """

    images = tuple(i for s in sets if s.status == IMAGES_FOUND for i in s.images)
    if images:
        ordered = tuple(sorted(images, key=lambda i: i.provenance != SUBJECT_OWN))
        return ImageSet(IMAGES_FOUND, ordered)
    reasons = "; ".join(s.reason for s in sets if s.reason)
    if any(s.status == COULD_NOT_LOOK_FOR_IMAGES for s in sets):
        return ImageSet(COULD_NOT_LOOK_FOR_IMAGES, reason=reasons)
    return ImageSet(NO_IMAGE_FOUND, reason=reasons)
