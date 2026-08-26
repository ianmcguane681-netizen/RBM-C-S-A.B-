"""A run that cannot tell you what it did not do is not worth running twice.

The report is the product. A list of prospects is easy; what makes the list actionable is
that every business the run touched ends in exactly one of three buckets, and the bucket
nobody else prints — the businesses this run has no opinion about — is printed loudest.
These tests run the whole pipeline against the invented fixture with the network switched
off, which also demonstrates the property the `--no-fetch` flag exists to make visible: no
site was assessed, so nothing with a site was prepared.
"""
from __future__ import annotations

import pathlib

from prospector import cli
from prospector.seen import Register

PACKAGE = pathlib.Path(__file__).resolve().parent.parent
FIXTURE = str(PACKAGE / "fixtures/synthetic-area.overpass.json")


def _run(tmp_path, *extra):
    code = cli.main(["--area", "Invented Town", "--operator", "Ian McGuane",
                     "--from-file", FIXTURE, "--out", str(tmp_path / "dossiers"),
                     "--register", str(tmp_path / "prepared.json"), "--no-fetch",
                     "--browser", "never", *extra])
    return code


def test_a_run_with_no_network_prepares_only_what_needs_no_network(tmp_path, capsys):
    assert _run(tmp_path) == 0
    out = capsys.readouterr().out
    # All three businesses with a listed website end INDETERMINATE, including the one
    # whose site is perfectly good: not fetching it means not knowing, and not knowing is
    # not a refusal. The count is the honest cost of running with the network off.
    assert "INDETERMINATE  3" in out
    assert "Hillside Veterinary Practice" in out
    assert "no site was assessed" in out


def test_the_run_names_which_stage_refused_each_business(tmp_path, capsys):
    assert _run(tmp_path) == 0
    out = capsys.readouterr().out
    assert "[contactable]" in out
    assert "Lough View Guest House" in out


def test_an_unnamed_listing_never_reaches_a_page(tmp_path, capsys):
    """There is nothing to put in the <h1>, so it is dropped at the source."""

    assert _run(tmp_path) == 0
    assert "bakery" not in capsys.readouterr().out


def test_a_second_run_prepares_nobody_twice(tmp_path, capsys):
    assert _run(tmp_path) == 0
    first = capsys.readouterr().out
    assert "PREPARED       2" in first
    assert _run(tmp_path) == 0
    second = capsys.readouterr().out
    assert "PREPARED       0" in second
    assert "[seen]" in second


def test_a_dry_run_writes_nothing_and_records_nothing(tmp_path, capsys):
    assert _run(tmp_path, "--dry") == 0
    assert "nothing was written" in capsys.readouterr().out
    assert not (tmp_path / "dossiers").exists()
    assert Register(tmp_path / "prepared.json").check("node/1001").status == "NEW"
