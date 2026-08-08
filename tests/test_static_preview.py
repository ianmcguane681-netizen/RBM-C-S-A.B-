"""A static-site connector must render the dashboard without Python or redirects."""
from pathlib import Path


ROOT = Path("index.html").read_text(encoding="utf-8")
SCRIPT = Path("backend/static/app.js").read_text(encoding="utf-8")


def test_root_is_the_dashboard_not_a_redirect_to_an_internal_file():
    assert "http-equiv=\"refresh\"" not in ROOT
    assert "NEXUS" in ROOT
    assert 'href="backend/static/styles.css"' in ROOT
    assert 'src="backend/static/app.js"' in ROOT


def test_a_failed_api_fetch_draws_no_dashboard_at_all():
    """A static host has no API, and the honest answer is to say so — not to draw one.

    This used to assert the opposite: that a failed fetch rendered a hardcoded preview so
    the page had something to show. That preview invented `NOT_CONNECTED` lane statuses and
    `UNKNOWN` breaker states in the same vocabulary the measured ones use, so a page that
    had never reached an API was pixel-identical to one reporting three dead lanes and an
    unarmed breaker. Ian loaded it, read the tiles as readings, and asked why a key wasn't
    required before entry. He was right, and the rule is the repository's oldest one: a
    value meaning "I could not look" must never render as "there is nothing there".

    So the static case now shows the gate with its reason, and the dashboard body stays
    hidden. Less to look at, and nothing on screen that nobody measured.
    """

    catch = SCRIPT.split("catch (error)", 1)[1]

    assert "showGate" in catch
    assert "did not answer" in catch
    assert "renderOverview" not in catch


def test_the_reason_a_page_is_blank_is_always_one_of_four_named_ones():
    """Blank with no explanation is its own failure. Each cause has a different remedy:
    start a server, set a key on the server, enter a key here, or open it over http."""

    for reason in ("opened as a file", "serving nothing", "not accepted",
                   "did not answer", "needs the read-only key"):
        assert reason in SCRIPT, reason
