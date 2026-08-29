"""An approach to a stranger must be true about them, and must be allowed to be sent.

Every other lane in this repository can be wrong and lose money. This one can be wrong and
be *rude to a real person about their own business* — and unlike a bad trade, that cannot be
taken back and it lands on somebody who did not ask to be involved. So the properties here
split into two groups and both are hard refusals rather than warnings.

**What may be claimed.** The lane's opening line is "I could not find a website for you" or
"I looked at your site and noticed these things". The recipient knows which of those is true
of them, so a draft resting on anything less than a real observation is not merely unhelpful
— it is the end of the conversation and a fair reason to be annoyed.

The trap is specific and this file is mostly about it. OpenStreetMap's coverage of premises
is far better than its coverage of attributes, so a business with no `website` tag is
overwhelmingly likely to be one whose website nobody has typed into OSM. A lane that read
that absence as a finding would send a list of messages most of which open with something
false. So OSM silence is INDETERMINATE, it does not draft, and the only thing that converts
it is a named person recording a search.

**Whether it may be sent at all.** Suppression outranks everything; an address that looks
like a named individual's rather than a company's is refused on the ePrivacy line; a
business written to inside the cooldown is refused. And an unreadable suppression list
refuses EVERYTHING, which inverts how the seen register behaves — the cost of a missed
approach is one email nobody sent, and the cost of a missed suppression is writing again to
somebody who already said no.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from connectors.directory import (
    NOT_TAGGED,
    READ,
    SITE_TAGGED,
    UNREADABLE,
    Area,
    Business,
    build_query,
    businesses_in,
)
from connectors.sitecheck import (
    ERRORED,
    FAIL,
    NOT_ASSESSED,
    PASS,
    REACHED,
    Criterion,
    SiteReport,
    check,
)
from connectors.sitecheck import UNREACHABLE as SITE_UNREACHABLE
from lib.outreach import (
    ADEQUATE,
    NEEDS_WORK,
    NO_SITE_FOUND,
    NOT_ESTABLISHED,
    Approach,
    ApproachLog,
    SearchLog,
    SuppressionList,
    assess,
    contactability,
    draft,
    looks_like_an_individual,
    summarise,
)

NOW = datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc)
SENDER = {"sender": "Ian McGuane",
          "sender_detail": "I build small websites for local businesses in Cork"}


def business(**overrides) -> Business:
    settings = dict(osm_id="node/1", name="Paul's Plumbing", category="craft=plumber",
                    website_status=NOT_TAGGED, email="info@paulsplumbing.ie")
    settings.update(overrides)
    return Business(**settings)


def stores(tmp_path):
    return {
        "suppression": SuppressionList.load(tmp_path / "suppression.json"),
        "log": ApproachLog.load(tmp_path / "approaches.json"),
        "searches": SearchLog.load(tmp_path / "searches.json"),
    }


def searched(tmp_path, key="node/1", *, url="", days_ago=1):
    log = SearchLog.load(tmp_path / "searches.json")
    log.record(key, website=url, checked_by="Ian McGuane",
               when=(NOW - timedelta(days=days_ago)).isoformat())
    return log


def good_site(url="https://paulsplumbing.ie") -> SiteReport:
    return SiteReport(REACHED, url, url, 200, (
        Criterion("the site answers", PASS, "HTTP 200"),
        Criterion("https", PASS, "served over HTTPS"),
        Criterion("mobile viewport", PASS, "declares a viewport"),
        Criterion("page title", PASS, "titled 'Paul's Plumbing, Cork'"),
    ), 0.4, 12_000, "2026-08-29T12:00:00Z")


def poor_site(url="https://paulsplumbing.ie") -> SiteReport:
    return SiteReport(REACHED, url, url, 200, (
        Criterion("the site answers", PASS, "HTTP 200"),
        Criterion("https", FAIL, "served over plain HTTP",
                  remedy="a free Let's Encrypt certificate"),
        Criterion("mobile viewport", FAIL, "no viewport meta tag",
                  remedy="one line in the head"),
    ), 0.4, 12_000, "2026-08-29T12:00:00Z")


class TestOpenStreetMapSilenceIsALeadNotAFinding:
    def test_an_untagged_business_is_not_established_and_does_not_draft(self, tmp_path):
        """The trap the whole lane is built around. OSM's coverage of attributes is far
        worse than its coverage of premises, so most "no website" entries would be wrong —
        and every message built on one opens with something false."""

        prospect = assess(business(), None, now=NOW, **stores(tmp_path))

        assert prospect.finding == NOT_ESTABLISHED
        assert "not a finding that no website exists" in prospect.describe()
        assert isinstance(draft(prospect, **SENDER), str)

    def test_the_refusal_names_the_command_that_would_close_it(self, tmp_path):
        """"INDETERMINATE" alone trains a reader to skim. This has to be an errand."""

        prospect = assess(business(), None, now=NOW, **stores(tmp_path))

        assert "outreach.py --searched" in prospect.describe()

    def test_a_persons_search_turns_it_into_a_finding(self, tmp_path):
        found = stores(tmp_path) | {"searches": searched(tmp_path)}

        prospect = assess(business(), None, now=NOW, **found)

        assert prospect.finding == NO_SITE_FOUND
        assert isinstance(draft(prospect, **SENDER), Approach)

    def test_the_draft_says_i_could_not_find_and_never_you_do_not_have(self, tmp_path):
        found = stores(tmp_path) | {"searches": searched(tmp_path)}
        approach = draft(assess(business(), None, now=NOW, **found), **SENDER)

        assert "could not find a website" in approach.body
        assert "I may simply have missed it" in approach.body
        assert "you do not have" not in approach.body.lower()
        assert "you have no website" not in approach.body.lower()

    def test_a_search_that_found_a_site_does_not_draft_until_it_is_checked(self, tmp_path):
        found = stores(tmp_path) | {
            "searches": searched(tmp_path, url="https://paulsplumbing.ie")}

        prospect = assess(business(), None, now=NOW, **found)

        assert prospect.finding == NOT_ESTABLISHED
        assert "has not been checked" in prospect.describe()

    def test_a_stale_search_stops_counting(self, tmp_path):
        """A business with no website in March may have one now, and an approach resting
        on a six-month-old search is the embarrassing kind of wrong."""

        found = stores(tmp_path) | {"searches": searched(tmp_path, days_ago=200)}

        assert assess(business(), None, now=NOW, **found).finding == NOT_ESTABLISHED

    def test_a_search_cannot_be_attributed_to_automation(self, tmp_path):
        """Nothing here can search the web, so a machine-attributed search would unlock a
        message to a stranger that nobody actually checked."""

        log = SearchLog.load(tmp_path / "s.json")

        with pytest.raises(ValueError, match="cannot be named as having searched"):
            log.record("node/1", website="", checked_by="agent:crawler")


class TestASiteThatWasNotReachedIsNotABadSite:
    def test_an_unreachable_site_is_not_established_and_does_not_draft(self, tmp_path):
        unreached = SiteReport(SITE_UNREACHABLE, "https://x.ie", reason="timed out")

        prospect = assess(business(website_status=SITE_TAGGED, website="https://x.ie"),
                          unreached, now=NOW, **stores(tmp_path))

        assert prospect.finding == NOT_ESTABLISHED
        assert "unanswered request, not a bad website" in prospect.describe()
        assert isinstance(draft(prospect, **SENDER), str)

    def test_an_http_error_is_a_real_finding_and_does_draft(self, tmp_path):
        """A 404 or a 500 on somebody's own domain is checkable, real, and one of the
        strongest reasons to get in touch. It is not a failure to look."""

        broken = SiteReport(ERRORED, "https://x.ie", "https://x.ie", 500, (
            Criterion("the site answers", FAIL, "the address returns HTTP 500",
                      remedy="find out whether the hosting has lapsed"),), 0.3, 0, "")

        prospect = assess(business(website_status=SITE_TAGGED, website="https://x.ie"),
                          broken, now=NOW, **stores(tmp_path))

        assert prospect.finding == NEEDS_WORK
        assert isinstance(draft(prospect, **SENDER), Approach)

    def test_a_site_that_passes_everything_is_adequate_and_does_not_draft(self, tmp_path):
        """There is nothing to tell this business that they do not already know, and an
        approach without something to say is a nuisance."""

        prospect = assess(business(website_status=SITE_TAGGED), good_site(), now=NOW,
                          **stores(tmp_path))

        assert prospect.finding == ADEQUATE
        assert "nothing to say" in draft(prospect, **SENDER)

    def test_a_draft_about_a_site_carries_only_what_was_measured(self, tmp_path):
        approach = draft(assess(business(website_status=SITE_TAGGED), poor_site(),
                                now=NOW, **stores(tmp_path)), **SENDER)

        assert len(approach.claims) == 2
        assert all("FAIL" not in claim for claim in approach.claims)
        assert "None of that is a judgement about how the site looks" in approach.body

    def test_the_draft_offers_the_list_to_whoever_built_it(self, tmp_path):
        """A message whose only acceptable outcome is hiring the sender is a sales pitch.
        One that is useful either way is worth reading."""

        approach = draft(assess(business(website_status=SITE_TAGGED), poor_site(),
                                now=NOW, **stores(tmp_path)), **SENDER)

        assert "hand the list to whoever built it" in approach.body


class TestWhoMayBeWrittenTo:
    def test_a_role_address_on_a_company_domain_is_permitted(self):
        individual, why = looks_like_an_individual("info@paulsplumbing.ie")

        assert individual is False
        assert "role address" in why

    def test_a_first_name_address_is_refused(self):
        """The ePrivacy line is corporate versus individual subscriber, and this cannot
        tell which side of it a first name sits on. It refuses rather than guesses."""

        individual, _ = looks_like_an_individual("paul@paulsplumbing.ie")

        assert individual is True

    def test_a_free_mail_domain_is_refused(self):
        assert looks_like_an_individual("paulsplumbing@gmail.com")[0] is True

    def test_the_refusal_says_it_is_not_legal_advice(self, tmp_path):
        contact = contactability(business(email="paul@paulsplumbing.ie"), now=NOW,
                                 **{k: v for k, v in stores(tmp_path).items()
                                    if k != "searches"})

        assert contact.permitted is False
        assert "not legal advice" in contact.reason
        assert "decide for yourself" in contact.reason

    def test_a_permitted_contact_still_records_why(self, tmp_path):
        """An approach that goes out has a record of why it was allowed to, which is what
        makes a complaint answerable with something better than "the system thought it was
        fine"."""

        contact = contactability(business(), now=NOW,
                                 **{k: v for k, v in stores(tmp_path).items()
                                    if k != "searches"})

        assert contact.permitted is True
        assert "opt-out" in contact.reason

    def test_a_business_with_no_contact_details_is_not_approached(self, tmp_path):
        contact = contactability(business(email="", phone=""), now=NOW,
                                 **{k: v for k, v in stores(tmp_path).items()
                                    if k != "searches"})

        assert contact.permitted is False
        assert "decision for a person" in contact.reason

    def test_a_phone_number_is_a_conversation_rather_than_a_broadcast(self, tmp_path):
        contact = contactability(business(email="", phone="021 123 4567"), now=NOW,
                                 **{k: v for k, v in stores(tmp_path).items()
                                    if k != "searches"})

        assert contact.permitted is True and contact.channel == "phone"

    def test_every_draft_carries_an_opt_out_and_names_the_sender(self, tmp_path):
        found = stores(tmp_path) | {"searches": searched(tmp_path)}
        approach = draft(assess(business(), None, now=NOW, **found), **SENDER)

        assert "STOP" in approach.body
        assert approach.body.count("Ian McGuane") >= 2

    def test_an_unnamed_sender_cannot_draft_at_all(self, tmp_path):
        found = stores(tmp_path) | {"searches": searched(tmp_path)}
        prospect = assess(business(), None, now=NOW, **found)

        assert "must identify who is sending it" in draft(
            prospect, sender="", sender_detail="")


class TestSuppressionOutranksEverything:
    def test_a_suppressed_business_is_never_drafted(self, tmp_path):
        kept = stores(tmp_path)
        kept["suppression"].add("node/1", "asked not to be contacted")
        kept["searches"] = searched(tmp_path)

        prospect = assess(business(), None, now=NOW, **kept)

        assert prospect.contact.permitted is False
        assert isinstance(draft(prospect, **SENDER), str)

    def test_an_unreadable_suppression_list_refuses_everybody(self, tmp_path):
        """The opposite of how the seen register behaves, and right here: the cost of a
        missed approach is one email nobody sent, and the cost of a missed suppression is
        writing again to somebody who already said no."""

        path = tmp_path / "suppression.json"
        path.write_text("{not json", encoding="utf-8")
        listing = SuppressionList.load(path)

        blocked, why = listing.suppressed("anything at all")

        assert blocked is True
        assert "an unreadable list is not an empty one" in why

    def test_an_unreadable_suppression_list_refuses_to_be_overwritten(self, tmp_path):
        path = tmp_path / "suppression.json"
        path.write_text("{not json", encoding="utf-8")

        with pytest.raises(RuntimeError, match="already asked not to be contacted"):
            SuppressionList.load(path).add("node/1", "reason")

    def test_a_recent_approach_blocks_a_second_one(self, tmp_path):
        kept = stores(tmp_path)
        kept["log"].record("node/1", "a website for Paul's Plumbing",
                           when=(NOW - timedelta(days=10)).isoformat())
        kept["searches"] = searched(tmp_path)

        prospect = assess(business(), None, now=NOW, **kept)

        assert prospect.contact.permitted is False
        assert "cooldown" in prospect.contact.reason

    def test_an_approach_outside_the_cooldown_is_allowed_again(self, tmp_path):
        kept = stores(tmp_path)
        kept["log"].record("node/1", "an earlier message",
                           when=(NOW - timedelta(days=400)).isoformat())
        kept["searches"] = searched(tmp_path)

        assert assess(business(), None, now=NOW, **kept).contact.permitted is True

    def test_an_unreadable_approach_log_refuses_rather_than_writing_twice(self, tmp_path):
        path = tmp_path / "approaches.json"
        path.write_text("{not json", encoding="utf-8")

        blocked, why = ApproachLog.load(path).recently_approached("node/1")

        assert blocked is True
        assert "An unknown is not a no" in why

    def test_the_approach_log_is_not_the_seen_register(self):
        """They look alike and answer different questions: one records what was SURFACED
        to the operator, the other what was SENT to a third party."""

        from lib.outreach import APPROACHES
        from lib.reaping import SEEN

        assert APPROACHES != SEEN


class TestNothingInThisLaneCanSend:
    def test_no_module_in_the_outreach_path_imports_an_email_client(self):
        """Structural, like `connectors/chain_exec.py` having no signing library. The
        deliverable is a draft and a person presses send."""

        from pathlib import Path

        for name in ("lib/outreach.py", "outreach.py", "connectors/directory.py",
                     "connectors/sitecheck.py"):
            source = Path(name).read_text(encoding="utf-8")
            assert "smtplib" not in source
            assert "import smtp" not in source
            assert "sendmail" not in source

    def test_the_draft_says_out_loud_that_it_was_not_sent(self, tmp_path):
        found = stores(tmp_path) | {"searches": searched(tmp_path)}
        printed = draft(assess(business(), None, now=NOW, **found), **SENDER).describe()

        assert "NOT SENT" in printed
        assert "send it yourself" in printed


class TestTheDirectorySource:
    def test_an_oversized_area_is_refused_rather_than_sent(self):
        """Overpass is donated infrastructure with no key, and a county-sized query can
        run for minutes."""

        with pytest.raises(ValueError, match="more than"):
            Area(south=51.0, west=-9.0, north=52.0, east=-8.0, name="most of Munster")

    def test_a_box_that_is_not_a_box_is_refused(self):
        with pytest.raises(ValueError, match="is not a box"):
            Area(south=52.0, west=-8.0, north=51.0, east=-9.0)

    def test_the_query_asks_for_ways_as_well_as_nodes(self):
        """A business mapped as a building outline is a way, and querying only nodes
        silently halves the answer in exactly the towns where mapping is best."""

        query = build_query(Area(51.88, -8.50, 51.90, -8.45), ("shop=bakery",))

        assert "nwr[" in query and "node[" not in query

    def test_a_failed_query_is_unreadable_rather_than_an_empty_town(self):
        def dead(_request, **_kw):
            raise OSError("connection reset")

        listing = businesses_in(Area(51.88, -8.50, 51.90, -8.45), opener=dead)

        assert listing.status == UNREADABLE
        assert "not a finding that the area has no businesses" in listing.describe()

    def test_an_unnamed_node_is_skipped_rather_than_kept_as_unnamed(self):
        """An approach needs somebody to address, and an unnamed node is a mapping
        artefact rather than a business anybody can be written to."""

        payload = {"elements": [
            {"type": "node", "id": 1, "lat": 51.9, "lon": -8.47,
             "tags": {"shop": "bakery"}},
            {"type": "node", "id": 2, "lat": 51.9, "lon": -8.47,
             "tags": {"shop": "bakery", "name": "The Bakery"}},
        ]}

        class Response:
            def read(self):
                return json.dumps(payload).encode()

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        listing = businesses_in(Area(51.88, -8.50, 51.90, -8.45),
                                opener=lambda *_a, **_kw: Response())

        assert [b.name for b in listing.businesses] == ["The Bakery"]

    def test_a_social_page_is_recorded_separately_from_a_website(self):
        """A Facebook page IS a web presence and is not a website — the commonest real
        answer to "why has this business not got a site", and an approach that ignores it
        reads as though nobody looked."""

        shop = Business(osm_id="node/1", name="A Shop", category="shop=bakery",
                        website_status=NOT_TAGGED, social="fb.com/ashop")

        assert shop.has_a_recorded_site is False
        assert "social: fb.com/ashop" in shop.describe()

    def test_a_listing_reports_untagged_as_leads_rather_than_as_findings(self):
        listing_text = businesses_in.__doc__ or ""
        from connectors.directory import Listing

        described = Listing(READ, "Cork", (
            Business(osm_id="n/1", name="A", category="shop=bakery",
                     website_status=NOT_TAGGED),), ("shop=bakery",), "now").describe()

        assert "leads to CHECK, not a list of businesses without websites" in described
        assert listing_text


class TestTheSiteChecker:
    def _report(self, html: str, status: int = 200):
        class Response:
            url = "https://example.ie"

            def __init__(self):
                self.status = status

            def read(self, _limit=None):
                return html.encode()

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        return check("https://example.ie", opener=lambda *_a, **_kw: Response())

    def test_a_missing_viewport_fails_with_a_remedy(self):
        report = self._report("<html><head><title>A Shop, Cork</title></head>"
                              "<body>" + "word " * 100 + "</body></html>")

        viewport = next(c for c in report.criteria if c.name == "mobile viewport")
        assert viewport.status == FAIL
        assert "one line in the head" in viewport.remedy

    def test_a_page_that_could_not_be_read_is_not_assessed_rather_than_failed(self):
        """A site that timed out has not failed a mobile check; nothing was checked."""

        report = SiteReport(SITE_UNREACHABLE, "https://x.ie", reason="timed out")

        assert report.assessed is False
        assert "NOTHING about it has been established" in report.describe()

    def test_a_parked_domain_is_the_strongest_case_in_the_list(self):
        report = self._report("<html><head><title>Coming Soon</title></head>"
                              "<body>Website coming soon</body></html>")

        parked = next(c for c in report.criteria if c.name == "real content")
        assert parked.status == FAIL
        assert "strongest case" in parked.remedy

    def test_a_placeholder_title_fails(self):
        report = self._report("<html><head><title>Just another WordPress site</title>"
                              "</head><body>" + "word " * 100 + "</body></html>")

        assert next(c for c in report.criteria
                    if c.name == "page title").status == FAIL

    def test_a_script_rendered_page_is_not_assessed_and_argues_against_approaching(self):
        """An HTML shell plus a bundle means somebody built this with a modern framework,
        and telling them it needs rebuilding is the message that ends the conversation."""

        report = self._report('<html><head><title>App</title></head>'
                              '<body><div id="root"></div><script src="/b.js"></script>'
                              '</body></html>')

        rendered = next(c for c in report.criteria if c.name == "server-rendered")
        assert rendered.status == NOT_ASSESSED
        assert "reason NOT to approach" in rendered.detail

    def test_a_contact_failure_is_supporting_rather_than_material(self):
        """A shop whose number is on a contact page rather than the home page is normal,
        and this reads one page."""

        report = self._report("<html><head><title>A Shop, Cork</title>"
                              '<meta name="viewport" content="width=device-width">'
                              "</head><body>" + "word " * 100 + "</body></html>")

        contact = next(c for c in report.criteria if c.name == "contact details")
        assert contact.status == FAIL and contact.material is False
        assert report.material_failures == ()

    def test_no_url_checks_nothing_and_says_so(self):
        report = check("")

        assert report.assessed is False
        assert "not a finding about any website" in report.describe()


class TestTheSummary:
    def test_not_established_is_neither_a_prospect_nor_a_rejection(self, tmp_path):
        prospects = [assess(business(), None, now=NOW, **stores(tmp_path))]

        text = summarise(prospects)

        assert "NOT_ESTABLISHED" in text
        assert "looked at and learned nothing about" in text
