"""Whether a store has ever been written, so a lost one is not read as a new one.

Both persistent things in this repository — the monitor ledger and the seen register —
report a vanished store exactly as they report a fresh one. `Ledger('/gone/x.json')` holds
zero entries and calls every fact `FIRST_SEEN`; `SeenRegister.load('/gone/x.json')` answers
`NEW` to everything. That is this repository's recurring defect wearing its most expensive
clothes yet, because both of those components exist *only* to remember.

The container is reclaimed and the ledger goes with it. The next run finds nothing, reports
first sightings across the board, and looks exactly like a monitor doing its job on a
watchlist it has just been handed.

**The fix is a receipt that outlives the data.** The data itself cannot be committed: it
records which tokens, filers and markets are being watched, and this repository is public.
The receipt carries no subjects at all — a store id, how many times it has been written,
when first and last, and which backend — so it is safe to commit, and a fresh container can
tell the two cases apart:

    FRESH       no receipt and no data. Genuinely the first run.
    INTACT      receipt and data agree.
    LOST        the receipt records writes and the data is gone. NOT a first run.
    UNREADABLE  the data exists and could not be parsed.

`LOST` is the whole point. It is not recoverable — the observations really are gone — but it
is *reportable*, and a monitor that says "I have been run 47 times and my memory is empty"
is telling the truth, where one that says `FIRST_SEEN` is not.

This is also the seam a real database drops into. `backend` is recorded rather than assumed,
so a receipt written against `json` and read against `postgres` is a mismatch a person can
see, instead of a silently empty result.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path

FRESH = "FRESH"
INTACT = "INTACT"
LOST = "LOST"
UNREADABLE = "UNREADABLE"

JSON_BACKEND = "json"


@dataclass(frozen=True, slots=True)
class Receipt:
    """Committable proof that a store has been written. Carries no subjects, ever.

    Deliberately no list of what is stored: the receipt is committed to a public
    repository and the data it vouches for is gitignored precisely because naming the
    watched subjects would defeat that.
    """

    store_id: str
    backend: str = JSON_BACKEND
    writes: int = 0
    first_write: str = ""
    last_write: str = ""
    #: Rows at the last write. A count, never the rows. Lets a reader see that a store
    #: which held 26 facts now holds none, which is a different alarm from an absent file.
    rows_at_last_write: int = 0

    @classmethod
    def load(cls, path: str | Path) -> "Receipt | None":
        path = Path(path)
        if not path.is_file():
            return None
        try:
            return cls(**json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError, TypeError):
            return None

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2) + "\n", encoding="utf-8")

    def written(self, when: str, rows: int) -> "Receipt":
        return replace(
            self,
            writes=self.writes + 1,
            first_write=self.first_write or when,
            last_write=when,
            rows_at_last_write=rows,
        )


@dataclass(frozen=True, slots=True)
class StoreStatus:
    state: str
    store_id: str
    receipt: Receipt | None = None
    rows_found: int = 0
    reason: str = ""

    @property
    def memory_is_trustworthy(self) -> bool:
        """Whether a comparison against this store means anything.

        FRESH is trustworthy: there is genuinely nothing to compare against and saying so
        is honest. LOST is not, and neither is UNREADABLE.
        """

        return self.state in {FRESH, INTACT}

    def describe(self) -> str:
        if self.state == FRESH:
            return (
                f"FRESH  {self.store_id} has never been written. Nothing to compare "
                f"against, and nothing lost."
            )
        if self.state == INTACT:
            receipt = self.receipt
            assert receipt is not None
            return (
                f"INTACT  {self.store_id}: {self.rows_found} row(s), written "
                f"{receipt.writes} time(s) since {receipt.first_write}."
            )
        if self.state == UNREADABLE:
            return (
                f"UNREADABLE  {self.store_id} exists and could not be parsed "
                f"({self.reason}). Its contents are NOT established as empty."
            )
        receipt = self.receipt
        assert receipt is not None
        return (
            f"!! LOST  {self.store_id} was written {receipt.writes} time(s), last on "
            f"{receipt.last_write} holding {receipt.rows_at_last_write} row(s), and the "
            f"data is now absent. This is NOT a first run. Every comparison this store "
            f"would make is meaningless until it is rebuilt, and anything it reports as "
            f"newly seen may have been seen many times before."
        )


def inspect(
    store_id: str,
    *,
    receipt_path: str | Path,
    rows_found: int | None,
    backend: str = JSON_BACKEND,
    reason: str = "",
) -> StoreStatus:
    """Compare what the receipt claims against what the data shows.

    `rows_found=None` means the data could not be read at all, which is different from
    reading it and finding nothing.
    """

    receipt = Receipt.load(receipt_path)

    if rows_found is None:
        return StoreStatus(UNREADABLE, store_id, receipt, 0, reason)

    if receipt is None or receipt.writes == 0:
        # No receipt and no data is a genuine first run. No receipt and data present is
        # also FRESH-ish, but the rows are real, so INTACT is the honest reading: the
        # receipt is simply younger than the store.
        return StoreStatus(INTACT if rows_found else FRESH, store_id, receipt, rows_found)

    if rows_found == 0:
        return StoreStatus(LOST, store_id, receipt, 0)

    if backend != receipt.backend:
        return StoreStatus(
            UNREADABLE, store_id, receipt, rows_found,
            reason=f"receipt was written by the {receipt.backend} backend, read by {backend}",
        )

    return StoreStatus(INTACT, store_id, receipt, rows_found)
