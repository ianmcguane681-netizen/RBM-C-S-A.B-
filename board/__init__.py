"""The review board: agent seats, their independence rules, and challenge sheets.

Sits above rbe_runtime and never the reverse. The runtime enforces the lifecycle
and the decision rules; this package is how a board is actually staffed and how
its findings are made readable.
"""

from board.challenges import (
    ChallengeSheet,
    NoChallenge,
    render_review,
    sort_sheets,
    summarise,
    to_finding_record,
)
from board.seats import (
    AgentSeat,
    SeatBrief,
    SeatConfigurationError,
    board_health,
    build_brief,
    require_independent_seats,
    seat_output,
    shared_model_note,
)

__all__ = [
    "AgentSeat", "SeatBrief", "SeatConfigurationError", "board_health", "build_brief",
    "require_independent_seats", "seat_output", "shared_model_note",
    "ChallengeSheet", "NoChallenge", "render_review", "sort_sheets", "summarise",
    "to_finding_record",
]
