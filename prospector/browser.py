"""Open the site in a real phone-sized browser, measure what actually happens, and take
the photograph that makes the pitch.

Everything in `standard.py` up to this point is read from markup, and markup only goes so
far. A page can carry a perfect viewport tag and still push a 900px table sideways off the
screen; it can be small and still take eight seconds to show anything. The document says
what was intended and the browser says what happens, and only one of those is what the
customer standing outside the shop experiences.

There is a second reason, and for the way this is actually used it may be the bigger one.
**A screenshot of their own site on a phone, next to the sample, is the pitch.** No
paragraph explaining that a layout does not fit a phone will do what one picture of it not
fitting a phone does, and it is their site, so nobody has to be persuaded of anything.

## This stage is optional and says so

Playwright is not a dependency of this package and Chromium is not installed by it. Where
neither is present, the browser criteria come back `NOT_ASSESSED` and the run says the
mobile checks were markup-only. What they never come back as is `MEETS`: an unopened page
is not a page that worked.

## A capture that could not load the page's own stylesheets is not a capture of that page

The rule that keeps this honest. If the CSS 404s, or a font times out, the render on screen
is not what a visitor sees — it is what a visitor sees on a bad day, and screenshotting it
into an email is a misrepresentation of somebody's work. So a capture with failed
subresources is `CAPTURE_INCOMPLETE`: the screenshot is kept for a person to look at, and
the criteria stay unassessed.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

BROWSER_UNAVAILABLE = "BROWSER_UNAVAILABLE"
CAPTURED = "CAPTURED"
CAPTURE_INCOMPLETE = "CAPTURE_INCOMPLETE"
CAPTURE_FAILED = "CAPTURE_FAILED"

#: A mid-range phone in portrait. Not the smallest screen in circulation and not a tablet;
#: what most of the traffic to a local business is actually holding.
PHONE = (390, 844)

#: Sideways scroll beyond this many pixels is a layout that does not fit. A pixel or two of
#: slack, because sub-pixel rounding on a scaled render is not a defect.
SCROLL_SLACK_PX = 4
#: Body text smaller than this is a page you have to pinch to read.
MIN_READABLE_PX = 11.0
#: First contentful paint beyond this is a blank screen for long enough that people leave.
SLOW_PAINT_MS = 3500.0


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True, slots=True)
class Capture:
    """What a phone-sized browser saw, or why it saw nothing."""

    status: str
    url: str = ""
    width: int = PHONE[0]
    height: int = PHONE[1]
    scroll_width: int | None = None
    #: The width the page laid itself out at. On a page with no viewport tag this is the
    #: desktop default — Chromium lays out at ~980px and scales the whole thing down to
    #: fit, so nothing overflows and everything is unreadable. Comparing the document to
    #: THIS would call that page a pass; comparing it to the device width is what a person
    #: holding the phone experiences.
    inner_width: int | None = None
    smallest_font_px: float | None = None
    first_paint_ms: float | None = None
    load_ms: float | None = None
    failed_subresources: tuple[str, ...] = ()
    screenshot_path: str = ""
    reason: str = ""
    at: str = field(default_factory=_now)

    @property
    def shrink(self) -> float:
        """How much the phone had to scale the page down to fit it on the screen.

        1.0 means the page laid itself out for the screen it is on. 0.4 means a desktop
        layout squeezed into a phone, which is where "the text is too small to read"
        actually comes from — the CSS says 13px and the visitor sees 5px.
        """

        if not self.inner_width or not self.width:
            return 1.0
        return min(1.0, self.width / self.inner_width)

    @property
    def usable(self) -> bool:
        """Whether the criteria may be decided from this. Only a complete capture."""

        return self.status == CAPTURED

    def describe(self) -> str:
        if self.status == CAPTURED:
            # Every measurement prints as "not measured" when it is missing rather than
            # as a zero. A first paint of 0ms would be the best number on the page.
            paint = (f"{self.first_paint_ms:.0f}ms" if self.first_paint_ms is not None
                     else "not measured")
            font = (f"{self.smallest_font_px}px" if self.smallest_font_px is not None
                    else "not measured")
            return (f"CAPTURED  {self.url} at {self.width}×{self.height}\n"
                    f"  document {self.scroll_width}px wide in a {self.inner_width}px "
                    f"window, first paint {paint}, smallest body text {font}")
        if self.status == CAPTURE_INCOMPLETE:
            return (f"CAPTURE_INCOMPLETE  {self.url}\n"
                    f"  {len(self.failed_subresources)} of the page's own files did not "
                    f"load: {', '.join(self.failed_subresources[:3])}\n"
                    f"  The screenshot is kept, and no criterion is decided from it. What "
                    f"rendered is not what a visitor sees.")
        if self.status == CAPTURE_FAILED:
            return f"CAPTURE_FAILED  {self.url}\n  {self.reason}"
        return (f"BROWSER_UNAVAILABLE\n  {self.reason}\n"
                f"  The mobile checks are markup-only for this run. That is not the same "
                f"as them passing.")


def chromium_path() -> str:
    """Where Chromium is, if somebody has already put one on this machine.

    Checked in the order of decreasing certainty: an explicit setting, then the path a
    Playwright install or a container image conventionally uses. An empty string means
    "let Playwright find its own", which is right on a machine where it downloaded one.
    """

    explicit = os.environ.get("PROSPECTOR_CHROMIUM", "")
    if explicit and Path(explicit).exists():
        return explicit
    browsers = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "")
    if browsers:
        candidate = Path(browsers) / "chromium"
        if candidate.exists():
            return str(candidate)
    return ""


def available() -> tuple[bool, str]:
    """Whether this stage can run, and if not, what a person can go and do about it."""

    try:
        import playwright.sync_api  # noqa: F401
    except ImportError:
        return False, ("Playwright is not installed. `pip install playwright && playwright "
                       "install chromium` turns the mobile checks from markup-reading into "
                       "measurement, and produces the screenshots.")
    return True, ""


_MIN_FONT_JS = """() => {
  let min = 99;
  for (const el of document.querySelectorAll('p,li,dd,dt,span,a,td,figcaption,small')) {
    const text = (el.textContent || '').trim();
    if (text.length < 12) continue;
    const size = parseFloat(getComputedStyle(el).fontSize);
    if (size && size < min) min = size;
  }
  return min === 99 ? null : min;
}"""

#: Resource kinds whose failure means the render is not the page. A failed tracking pixel
#: or a blocked analytics script changes nothing a visitor sees; a failed stylesheet
#: changes everything.
_LOAD_BEARING = ("stylesheet", "font", "image")


def capture(url: str, *, out_path: Path | str | None = None,
            viewport: tuple[int, int] = PHONE, timeout_ms: int = 30000,
            full_page: bool = True) -> Capture:
    """Open `url` at phone size, measure it, and write a PNG if `out_path` is given."""

    ok, reason = available()
    if not ok:
        return Capture(BROWSER_UNAVAILABLE, url=url, reason=reason)

    from playwright.sync_api import sync_playwright

    width, height = viewport
    failed: list[str] = []
    executable = chromium_path()
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or ""
    args = ["--no-sandbox", "--disable-dev-shm-usage", "--disable-component-update",
            "--no-first-run"]
    try:
        with sync_playwright() as engine:
            launch: dict = {"args": args}
            if executable:
                launch["executable_path"] = executable
            if proxy:
                # The browser is a separate process and does not read the environment the
                # way an HTTP client does, so the proxy is passed explicitly rather than
                # left to luck — with the loopback bypassed, because a proxy asked to
                # relay a request to 127.0.0.1 refuses it, and the first thing anybody
                # renders locally is a file they just wrote or a page they are serving.
                no_proxy = os.environ.get("NO_PROXY") or os.environ.get("no_proxy") or ""
                bypass = ",".join(part for part in
                                  ["localhost", "127.0.0.1", "::1", no_proxy] if part)
                launch["proxy"] = {"server": proxy, "bypass": bypass}
            browser = engine.chromium.launch(**launch)
            try:
                page = browser.new_page(viewport={"width": width, "height": height},
                                        device_scale_factor=2, is_mobile=True,
                                        has_touch=True)
                page.on("requestfailed", lambda request: (
                    failed.append(f"{request.resource_type}: {request.url[:90]}")
                    if request.resource_type in _LOAD_BEARING else None))
                page.on("response", lambda response: (
                    failed.append(f"{response.request.resource_type} "
                                  f"{response.status}: {response.url[:90]}")
                    if response.status >= 400
                    and response.request.resource_type in _LOAD_BEARING else None))
                page.goto(url, wait_until="load", timeout=timeout_ms)
                measurements = {
                    "scroll_width": page.evaluate("document.documentElement.scrollWidth"),
                    "inner_width": page.evaluate("window.innerWidth"),
                    "smallest_font_px": page.evaluate(_MIN_FONT_JS),
                    "first_paint_ms": page.evaluate(
                        "performance.getEntriesByName('first-contentful-paint')[0]"
                        "?.startTime ?? null"),
                    "load_ms": page.evaluate(
                        "performance.timing.loadEventEnd - performance.timing.navigationStart"),
                }
                saved = ""
                if out_path:
                    out = Path(out_path)
                    out.parent.mkdir(parents=True, exist_ok=True)
                    page.screenshot(path=str(out), full_page=full_page)
                    # The full path, not the basename: the caller copies this file into a
                    # dossier and cannot do that from a name alone.
                    saved = str(out)
            finally:
                browser.close()
    except Exception as exc:  # noqa: BLE001 - every browser failure is one outcome here
        return Capture(CAPTURE_FAILED, url=url, reason=repr(exc)[:300])

    status = CAPTURE_INCOMPLETE if failed else CAPTURED
    return Capture(status, url=url, width=width, height=height,
                   failed_subresources=tuple(dict.fromkeys(failed))[:6],
                   screenshot_path=saved, **measurements)
