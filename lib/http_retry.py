"""One retry policy, shared by every connector that talks to a rate-limited API.

The docket join gained backoff after a 429 silently degraded every adjudicated
record to unjoined, which made the study's result depend on how busy the API was
that afternoon. The FJC connector did not gain it, so the very next long run died
mid-pagination on the same status code from the same host.

Two connectors calling the same API had two different answers to "what does 429
mean", which is how that happens. There is one answer now, and it lives here:
a 429 is the server asking the client to wait, so the client waits.

Waiting is not always enough. Backoff can be exhausted, and then the caller has to
decide what the failure *means*. That decision has one correct answer and this
module supplies it too: a transient failure is not an observation. It says nothing
about the case, the docket, or the archive -- only that the client could not ask.
Recording it alongside real answers is how a busy afternoon becomes a permanent
finding, so `TransientRetrievalError` exists to make the difference impossible to
lose in a string.
"""
from __future__ import annotations

import socket
import time
import urllib.error
import urllib.request
from typing import Callable

# Retried statuses: rate limiting and the transient gateway errors CourtListener
# returns under load. Everything else is a real answer and is raised immediately --
# retrying a 401 or a 404 only wastes the caller's time and the server's.
RETRYABLE_STATUSES = (429, 502, 503, 504)
BACKOFF_SECONDS = (5, 20, 60)


class TransientRetrievalError(RuntimeError):
    """Raised when the client could not reach an answer, as opposed to reaching one.

    The distinction is the whole point. A 404 and an exhausted 429 both leave the
    caller without a record, but only the 404 is evidence: it says the thing is not
    there. The 429 says the client was rate-limited, which is a fact about the run
    and not about the world, and it must never be written down as though it were an
    assessment.
    """


def is_transient(error: BaseException) -> bool:
    """Could this failure plausibly succeed on a later attempt?

    HTTPError subclasses URLError, so it is tested first: a 404 arriving as a URLError
    must not be classed transient just because of its base class.
    """

    if isinstance(error, urllib.error.HTTPError):
        return error.code in RETRYABLE_STATUSES
    return isinstance(error, (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionError))


def retrying_urlopen(
    request: urllib.request.Request,
    *,
    timeout: int = 45,
    sleep: Callable[[float], None] = time.sleep,
):
    """Open a request, waiting out rate limits rather than failing through them."""

    for attempt in range(len(BACKOFF_SECONDS) + 1):
        try:
            return urllib.request.urlopen(request, timeout=timeout)
        except urllib.error.HTTPError as error:
            if error.code not in RETRYABLE_STATUSES or attempt == len(BACKOFF_SECONDS):
                raise
            sleep(BACKOFF_SECONDS[attempt])
    raise RuntimeError("unreachable")  # pragma: no cover - loop returns or raises
