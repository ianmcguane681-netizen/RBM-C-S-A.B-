"""Monitoring is a promise, so silence has to mean something.

Once a business is paying to have their site watched, "nothing to report" is a claim. The
only way it is worth anything is if the watcher can tell "I looked and it is fine" from "I
could not look" — a monitor that reports nothing wrong when it never loaded the page
converts an outage into a reassurance, which is worse than having no monitor at all.

The other property here is about what a regression is. Not a score going down: a named
criterion that was passing and now fails, with the name in the report, because the person
who gets that message has to know what to go and fix.
"""
from __future__ import annotations

import json

from prospector import condition as condition_mod
from prospector.watch import (GONE, INTACT, IMPROVED, NOT_WATCHED, REGRESSED, UNREADABLE,
                              Watch, look)

GOOD = ('<html lang="en"><head><meta name="viewport" content="width=device-width">'
        '<title>Shop</title><meta name="description" content="A shop">'
        '<link rel="icon" href="/i.png"><meta property="og:title" content="Shop">'
        '<meta property="og:image" content="/i.png"></head><body><h1>Shop</h1>'
        '<p>Opening hours: Mon-Fri 09:00-17:00</p>'
        '<p><a href="tel:+353740000000">Call</a></p>'
        '<p><a href="mailto:hi@shop.example">Email</a></p>'
        '<p>1 Main Street, Donegal Town, F94 X2P8</p></body></html>')


def _fetcher(body, ok=True):
    def fetch(url, timeout=None):
        if not ok:
            return condition_mod.Fetch(False, error="URLError(timeout)")
        return condition_mod.Fetch(True, body, 200, url, scheme="https")
    return fetch


def _look(tmp_path, body, ok=True):
    return look("https://shop.example", baseline=tmp_path / "baseline.json",
                use_browser=False, fetcher=_fetcher(body, ok))


def test_the_first_look_records_a_baseline_and_says_it_is_not_watching_yet(tmp_path):
    """A first run cannot compare, and reporting INTACT would be a claim it cannot make."""

    result = _look(tmp_path, GOOD)
    assert result.status == NOT_WATCHED
    assert not result.needs_attention
    assert (tmp_path / "baseline.json").exists()


def test_an_unchanged_site_is_intact(tmp_path):
    _look(tmp_path, GOOD)
    assert _look(tmp_path, GOOD).status == INTACT


def test_a_criterion_that_stops_passing_is_named(tmp_path):
    """Not "the score dropped". The person reading this has to know what to fix."""

    _look(tmp_path, GOOD)
    result = _look(tmp_path, GOOD.replace('<a href="tel:+353740000000">Call</a>',
                                          "074 912 0001"))
    assert result.status == REGRESSED
    assert result.needs_attention
    assert any(change.code == "PHONE_TAPPABLE" and change.worse
               for change in result.changes)
    assert "PHONE_TAPPABLE" in result.describe()


def test_a_fix_is_reported_too_and_does_not_wake_anybody(tmp_path):
    _look(tmp_path, GOOD.replace('<a href="tel:+353740000000">Call</a>', "074 912 0001"))
    result = _look(tmp_path, GOOD)
    assert result.status == IMPROVED
    assert not result.needs_attention


def test_a_site_that_stops_answering_is_gone_rather_than_changed(tmp_path):
    _look(tmp_path, GOOD)
    result = _look(tmp_path, GOOD, ok=False)
    assert result.status == GONE
    assert result.needs_attention


def test_an_outage_does_not_overwrite_the_baseline(tmp_path):
    """Otherwise the recovery reports twenty improvements and the outage vanishes."""

    _look(tmp_path, GOOD)
    before = json.loads((tmp_path / "baseline.json").read_text(encoding="utf-8"))
    _look(tmp_path, GOOD, ok=False)
    after = json.loads((tmp_path / "baseline.json").read_text(encoding="utf-8"))
    assert before["states"] == after["states"]


def test_an_unreadable_baseline_is_not_a_quiet_state(tmp_path):
    """It means the watch is not running, which the person paying for it wants to know."""

    (tmp_path / "baseline.json").write_text("{ not json", encoding="utf-8")
    result = _look(tmp_path, GOOD)
    assert result.status == UNREADABLE
    assert result.needs_attention
    assert "not the same as nothing having changed" in result.describe()


def test_a_certificate_about_to_expire_needs_attention_on_its_own():
    """The most common way a working small site becomes a frightening one overnight."""

    assert Watch(INTACT, certificate_days_left=9).needs_attention
    assert not Watch(INTACT, certificate_days_left=200).needs_attention


def test_a_certificate_that_could_not_be_read_is_never_reported_as_plenty_of_time():
    """`None`, not a large number. This is the defect this package is built around,
    pointed at a failure that happens on a known date."""

    assert Watch(INTACT, certificate_days_left=None).certificate_days_left is None
    assert "certificate" not in Watch(INTACT).describe()


def test_the_command_line_exits_nonzero_only_when_a_person_is_needed(tmp_path):
    """So it can be a cron line without anybody writing a wrapper to interpret it."""

    from prospector.watch import main

    assert Watch(INTACT).needs_attention is False
    assert Watch(REGRESSED).needs_attention is True
    assert callable(main)
