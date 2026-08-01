"""CG-03: supply that is locked, read from contracts rather than from a website.

Published tokenomics and deployed contract routinely disagree, and the published version
is the one everybody models. An unlock schedule is code, so it is retrievable, and this
module retrieves it.

Two limits shape the design, and both are stated rather than worked around.

**Discovery is partial by construction.** The gate wants lock contracts *found*, not
supplied. Finding them properly means enumerating a token's largest holders, and that is
not possible from raw JSON-RPC -- it needs an indexer, or a walk of every Transfer since
deployment, which is tens of thousands of requests at a six-block log cap. So this probes
a registry plus whatever a reviewer supplies, and reports how thin that search was.

**The registry ships empty.** An earlier draft of this design named Team Finance, UNCX and
PinkLock as declared constants. Their addresses cannot be verified from here -- there is no
way to search a chain by name -- and writing addresses from memory into the registry that
decides whether supply is locked is exactly the recalled-not-retrieved error this
repository keeps catching in other people's work. A wrong locker address returns a zero
balance, which renders as "no locks found". The failure is silent and flattering.

So `NO_LOCK_CONTRACT_IDENTIFIED` reports that zero lockers were searched until an operator
registers verified ones. That is a weaker finding than the alternative, and a true one.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

from connectors.chain import ChainAccessError, ChainClient
from connectors.chain_queries import balance_of, total_supply
from lib.http_retry import TransientRetrievalError
from lib.shares import format_share

LOCKS_FOUND = "LOCKS_FOUND"
NO_LOCK_CONTRACT_IDENTIFIED = "NO_LOCK_CONTRACT_IDENTIFIED"
INDETERMINATE = "INDETERMINATE"

# Addresses tokens are burned to. Distinct from a lock: burned supply is gone, locked
# supply returns. Reporting them together would tell a holder the wrong thing about what
# can hit the market later.
BURN_ADDRESSES = (
    "0x0000000000000000000000000000000000000000",
    "0x000000000000000000000000000000000000dEaD",
)


@dataclass(frozen=True, slots=True)
class RegisteredLocker:
    """A locker address and how it came to be trusted.

    `verified_by` is not decoration. A registry that accepted bare addresses would
    accumulate guesses indistinguishable from checks, and the whole point of the registry
    is that its entries are better evidence than a recollection.
    """

    address: str
    name: str
    verified_by: str


# Empty on purpose. See the module docstring: an unverified locker address returns zero and
# reads as an absence of locks, which is the most flattering possible way to be wrong.
LOCKER_REGISTRY: tuple[RegisteredLocker, ...] = ()


@dataclass(frozen=True, slots=True)
class HolderBalance:
    address: str
    label: str
    balance: int
    block_number: int

    def share_of(self, supply: int) -> float:
        return (self.balance / supply * 100.0) if supply else 0.0


@dataclass(frozen=True, slots=True)
class LockFinding:
    """What is locked, what is burned, and how hard anyone looked.

    Locked and burned are separate fields and are never summed. Burned supply cannot
    return; locked supply is scheduled to. A holder asking "what can hit the market" needs
    the second number and not their total.
    """

    status: str
    token: str
    block_number: int
    total_supply: int
    locked: tuple[HolderBalance, ...] = ()
    burned: tuple[HolderBalance, ...] = ()
    searched: tuple[str, ...] = ()
    registry_size: int = 0
    unreachable: tuple[str, ...] = ()

    @property
    def locked_supply(self) -> int:
        return sum(h.balance for h in self.locked)

    @property
    def burned_supply(self) -> int:
        return sum(h.balance for h in self.burned)

    def describe(self) -> str:
        percent = lambda amount: format_share(amount, self.total_supply)

        if self.status == INDETERMINATE:
            return (
                f"Lock position could not be established at block {self.block_number}: "
                f"{len(self.unreachable)} probe(s) could not be completed. This is not a "
                f"finding about how much supply is locked."
            )

        lines = [f"Supply position for {self.token} at block {self.block_number}:"]
        if self.burned:
            lines.append(
                f"  burned  {self.burned_supply:,} ({percent(self.burned_supply)}) "
                f"-- cannot return to circulation"
            )
        if self.locked:
            lines.append(
                f"  locked  {self.locked_supply:,} ({percent(self.locked_supply)}) "
                f"-- scheduled to return; burned and locked are NOT summed"
            )
            for holder in self.locked:
                lines.append(
                    f"            {holder.balance:,} at {holder.address} ({holder.label})"
                )

        if self.status == NO_LOCK_CONTRACT_IDENTIFIED:
            # Never "unlocked", never "no locks", never "fully circulating". None of those
            # is established by a search this thin, and the description says how thin.
            lines.append("")
            if self.registry_size == 0:
                lines.append(
                    "  No lock contract was identified, and the locker registry is EMPTY: "
                    "zero known lockers were searched. This finding establishes nothing "
                    "about whether supply is locked."
                )
            else:
                lines.append(
                    f"  No lock contract was identified among {len(self.searched)} address"
                    f"(es) searched ({self.registry_size} from the registry). Supply held "
                    f"by a locker not in the registry would produce this same result."
                )
            lines.append(
                "  Top-holder enumeration is not available from JSON-RPC, so this search "
                "covers only registered and supplied addresses."
            )
        return "\n".join(lines)


def verify_locker(client: ChainClient, address: str, **kw: Any) -> bool:
    """Is this address a contract?

    An externally-owned account holding tokens is a person, not a lock. Registering one
    would report a whale's balance as locked supply, which is wrong in the direction that
    makes a token look safer than it is.
    """

    reading = client.read("eth_getCode", [address], **kw)
    code = str(reading.value or "0x")
    return len(code) > 2


def lock_finding(
    client: ChainClient,
    token: str,
    *,
    candidates: Sequence[str] = (),
    registry: Sequence[RegisteredLocker] = LOCKER_REGISTRY,
    **kw: Any,
) -> LockFinding:
    """CG-03 over whatever addresses can actually be checked.

    Burn addresses are always probed because they are chain constants rather than
    discoveries. Everything else comes from the registry or the caller, and the finding
    records which.
    """

    try:
        supply_reading = total_supply(client, token, **kw)
    except TransientRetrievalError as error:
        return LockFinding(INDETERMINATE, token, 0, 0, unreachable=(str(error)[:100],))
    except ChainAccessError as error:
        return LockFinding(INDETERMINATE, token, 0, 0, unreachable=(str(error)[:100],))

    supply = int(str(supply_reading.value or "0x0"), 16)
    block_number = supply_reading.block_number

    burned: list[HolderBalance] = []
    locked: list[HolderBalance] = []
    searched: list[str] = []
    unreachable: list[str] = []

    def _probe(address: str, label: str, into: list[HolderBalance]) -> None:
        searched.append(f"{address} ({label})")
        try:
            reading = balance_of(client, token, address, **kw)
        except TransientRetrievalError as error:
            unreachable.append(f"{address}: {str(error)[:60]}")
            return
        except ChainAccessError:
            return
        amount = int(str(reading.value or "0x0"), 16)
        if amount > 0:
            into.append(HolderBalance(address, label, amount, reading.block_number))

    for address in BURN_ADDRESSES:
        _probe(address, "burn address", burned)
    for locker in registry:
        _probe(locker.address, f"registry: {locker.name}", locked)
    for address in candidates:
        _probe(address, "supplied candidate", locked)

    if unreachable and not locked and not burned:
        return LockFinding(
            INDETERMINATE, token, block_number, supply,
            searched=tuple(searched), registry_size=len(registry),
            unreachable=tuple(unreachable),
        )

    status = LOCKS_FOUND if locked else NO_LOCK_CONTRACT_IDENTIFIED
    return LockFinding(
        status=status,
        token=token,
        block_number=block_number,
        total_supply=supply,
        locked=tuple(locked),
        burned=tuple(burned),
        searched=tuple(searched),
        registry_size=len(registry),
        unreachable=tuple(unreachable),
    )
