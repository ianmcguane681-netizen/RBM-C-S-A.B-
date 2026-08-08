"""Candidate tags for one concept must be spellings of one fact, not two different facts.

`EdgarClient.first_reported` exists for tag MIGRATION. It queries every candidate, keeps
the one with the most recent data, and records the rest in `alternates_with_data` — because
a filer that switched tags has split its history and neither series alone is the whole of
it. `_comparability` then refuses the subject INDETERMINATE. That is correct for
`Revenues` versus `RevenueFromContractWithCustomerExcludingAssessedTax`.

It is wrong the moment two candidates are different facts rather than different spellings.
`us-gaap:CommonStockSharesOutstanding` counts shares at the balance-sheet date;
`dei:EntityCommonStockSharesOutstanding` counts them on the cover page, near the filing
date. Both are complete, both are current, and most filers report both — so pairing them
made the split-history check fire on companies that had filed perfectly well. Astera Labs
and Credo were both refused for it against live EDGAR.

The defect hid for months because the spread gate returns REFUSED, which outranks
INDETERMINATE in `decided_by`, so the cascade always reported the spread instead. It
surfaced only when a shut market stopped a spread being computed at all — which is to say
it took two unrelated changes and a Saturday to see a gate that had been wrong all along.

The property that keeps it fixed is narrow and mechanical: a taxonomy prefix inside a
candidate list means the list spans two namespaces, and two namespaces mean two different
facts. Keep them as separate concepts and each NOT_REPORTED is true of the thing it names.
"""
from __future__ import annotations

from check_stock import CONCEPTS


class TestOneConceptIsOneFact:
    def test_no_candidate_list_spans_two_taxonomies(self):
        """The rule the shares-outstanding entry broke."""

        spanning = {
            label: tags for label, tags in CONCEPTS.items()
            if any(":" in tag for tag in tags) and len(tags) > 1
        }

        assert not spanning, (
            f"{spanning} lists candidates from more than one taxonomy. Candidates are "
            f"alternative spellings of ONE fact — a filer carrying data under two of them "
            f"is reported as a split history and refused. A cover-page fact and a "
            f"balance-sheet fact are two facts: give them two entries."
        )

    def test_the_two_share_counts_are_named_separately(self):
        assert CONCEPTS["shares outstanding (balance sheet)"] == ["CommonStockSharesOutstanding"]
        assert CONCEPTS["shares outstanding (cover page)"] == ["dei:EntityCommonStockSharesOutstanding"]

    def test_every_concept_has_at_least_one_candidate(self):
        assert all(tags for tags in CONCEPTS.values())

    def test_a_label_says_which_fact_it_is_when_two_are_close(self):
        """Two share counts under one name would send a reader to the wrong number."""

        share_counts = [label for label in CONCEPTS if "shares outstanding" in label]

        assert len(share_counts) == 2
        assert all("(" in label for label in share_counts), share_counts
