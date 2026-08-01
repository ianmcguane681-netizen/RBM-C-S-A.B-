"""Exact, case-insensitive term matching without substring leakage.

Word-boundary anchored for a reason that cost real time to find: plain substring
matching once classified "telecommunications" as "communication" and "distilled"
as "still". Any domain pack that matches vocabulary should use this.
"""
from __future__ import annotations

import re


def matched_terms(text: str, terms: list[str]) -> list[str]:
    """Return exact case-insensitive term matches without substring leakage."""

    return [
        term
        for term in terms
        if re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text, flags=re.IGNORECASE)
    ]


def contains_any(text: str, terms: list[str]) -> bool:
    return bool(matched_terms(text, terms))
