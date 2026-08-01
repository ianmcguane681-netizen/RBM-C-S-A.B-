"""Rendering quantities as shares without rounding small ones into zero."""
from __future__ import annotations


def format_share(amount: int, total: int) -> str:
    """A percentage that never rounds a nonzero quantity down to zero.

    SHIB's burned supply is 0.0049% of total, which at two decimal places renders as
    "0.00%" and reads as nothing burned. A holder drawing that conclusion has been misled
    by a formatter, which is the same defect as every sentinel in this repository: a value
    meaning "very small" presented as one meaning "none".

    Precision therefore grows until the figure is distinguishable from zero.
    """

    if not total:
        return "n/a"
    share = amount / total * 100
    if share == 0:
        return "0%"
    for places in (2, 4, 6, 8):
        rendered = f"{share:.{places}f}"
        if float(rendered) != 0:
            return f"{rendered}%"
    return "<0.00000001%"
