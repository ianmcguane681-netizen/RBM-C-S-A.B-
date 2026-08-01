"""Telling a pause from a wall.

A rate limit that clears is a pause; one that does not is a spent budget, and the two
look identical for the first few requests. Measured on a long retrieval run against a
public API: forty records assessed with no deferral at all, then every subsequent
request refused. Pushing on would have converted the remaining work into deferrals and
learned nothing, at the cost of one request each.

This matters most for a process that runs continuously. A watcher that hits a quota wall
at 3am and keeps going will have burned the day's allowance by morning and recorded
nothing but refusals.
"""
from __future__ import annotations


# A rate limit that clears is a pause; one that does not is a spent budget, and the
# two look identical for the first few records. Observed on the 430-record census:
# forty records assessed with no deferral at all, then every subsequent request
# refused. Pushing on would have converted the remaining ~330 records into deferrals
# and learned nothing about any of them, at the cost of 330 more requests.
#
# Stopping here is not an incomplete measurement being concealed. It is the refusal
# the deferred guard already produces, reached sooner and more cheaply.
CONSECUTIVE_DEFERRAL_LIMIT = 5
DEFERRAL_BACKOFF_SECONDS = 5.0


class DeferralBudget:
    """Track whether deferrals are intermittent or sustained.

    A separate object rather than two variables in the loop, because the rule it
    encodes has to be testable without a network. A guard whose stopping branch has
    never run is a guess about what it would do.
    """

    def __init__(self, limit: int = CONSECUTIVE_DEFERRAL_LIMIT) -> None:
        self.limit = limit
        self.consecutive = 0
        self.reason = ""

    def record_success(self) -> None:
        """One retrieval getting through means the limit was a pause, not a wall."""

        self.consecutive = 0

    def record_deferral(self, position: int, total: int) -> bool:
        """Note a deferral. Returns True when the walk should stop."""

        self.consecutive += 1
        if self.consecutive < self.limit:
            return False
        self.reason = (
            f"{self.consecutive} consecutive deferrals at record {position} of {total}: "
            f"the API is refusing sustained requests, not intermittently"
        )
        return True

    @property
    def exhausted(self) -> bool:
        return bool(self.reason)
