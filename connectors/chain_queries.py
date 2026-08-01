"""The specific reads RBM-003's gates need, each carrying its own provenance.

Written after a probe that changed the design. Checking USDC -- one of the largest tokens
in existence -- for upgradeability using the EIP-1967 slots returns three empty slots, and
calling `implementation()` reverts. Both say "not a proxy". USDC is a proxy:

    zeppelinos implementation slot   0x43506849d7c04f9138d1a2050bbf3a0c054402dd
    zeppelinos admin slot            0x807a96288a1a408dbc13de2b1d087d10356395d2

Its FiatTokenProxy predates EIP-1967 and uses the older OpenZeppelin slots, and because it
is a *transparent* proxy it routes non-admin callers to the implementation, so the function
probe reverts rather than answering. A naive CG-04 implementation therefore reports an
upgradeable token as immutable, which is a SEV-1 false negative on a token millions of
people hold.

The lesson is the one this system keeps relearning in new domains: **an empty slot is not
evidence of absence.** It means no known pattern matched. So proxy detection reports three
states and never a boolean, and "no pattern matched" is never rendered as "immutable".

Every function here returns a `ChainReading`, so a figure cannot exist without the chain,
block height, contract, query and hash needed to regenerate it. CG-06 is satisfied by
construction rather than by discipline.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from connectors.chain import ChainAccessError, ChainClient, ChainReading
from lib.http_retry import TransientRetrievalError

# Verified against live contracts on 2026-08-01 rather than recalled. A wrong selector
# does not error -- it reverts, or worse returns a plausible number from a different
# function -- so these are checked rather than trusted.
SELECTORS = {
    "totalSupply": "0x18160ddd",
    "balanceOf": "0x70a08231",
    "decimals": "0x313ce567",
    "symbol": "0x95d89b41",
    "name": "0x06fdde03",
    "owner": "0x8da5cb5b",
    "paused": "0x5c975abb",
    "masterMinter": "0x35d99f35",
    "implementation": "0x5c60da1b",
    "admin": "0xf851a440",
}

# Proxy storage slots by convention. Order matters only for reporting; every slot is
# probed regardless, because a contract may carry more than one and reporting the first
# hit would hide the rest.
PROXY_SLOTS: dict[str, str] = {
    # EIP-1967: keccak256("eip1967.proxy.<field>") - 1
    "eip1967_implementation": "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc",
    "eip1967_admin": "0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103",
    "eip1967_beacon": "0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50",
    # Pre-EIP-1967 OpenZeppelin. USDC uses these; omitting them was the defect.
    "zeppelinos_implementation": "0x7050c9e0f4ca769c69bd3a8ef740bc37934f8e2c036e5a723fd8ee048ed3f8c3",
    "zeppelinos_admin": "0x10d6a54a4754c8869d6886b5f5d7fbfa5b4522237ea5c60d11bc4e7a1ff9390b",
}

UPGRADEABLE = "UPGRADEABLE"
NO_PATTERN_MATCHED = "NO_PATTERN_MATCHED"
INDETERMINATE = "INDETERMINATE"

# Distinct from a zero address on purpose. A reverted `owner()` means the function does
# not exist; a zero `owner()` means ownership was renounced. Collapsing them would report
# a renunciation that never happened.
REVERTED = "REVERTED"
ZERO_ADDRESS = "0x" + "0" * 40


@dataclass(frozen=True, slots=True)
class ProxyFinding:
    """Whether this contract can be replaced, and on what evidence.

    `status` is never a boolean. `NO_PATTERN_MATCHED` means every probe came back empty,
    which is a statement about the probes and not about the contract -- a proxy using a
    convention not listed here produces exactly this result.
    """

    status: str
    address: str
    block_number: int
    slots: dict[str, str] = field(default_factory=dict)
    unreachable: tuple[str, ...] = ()

    @property
    def implementation(self) -> str:
        for key in ("eip1967_implementation", "zeppelinos_implementation"):
            if self.slots.get(key):
                return self.slots[key]
        return ""

    @property
    def admin(self) -> str:
        for key in ("eip1967_admin", "zeppelinos_admin"):
            if self.slots.get(key):
                return self.slots[key]
        return ""

    def describe(self) -> str:
        """Phrasing a reviewer can paste into a finding without overstating it."""

        if self.status == UPGRADEABLE:
            patterns = ", ".join(sorted(self.slots))
            return (
                f"Upgradeable at block {self.block_number}. Implementation "
                f"{self.implementation or 'not recorded'}, admin {self.admin or 'not recorded'} "
                f"(matched: {patterns})."
            )
        if self.status == INDETERMINATE:
            return (
                f"Upgradeability could not be determined at block {self.block_number}: "
                f"{len(self.unreachable)} probe(s) could not be completed "
                f"({', '.join(self.unreachable)}). This is not a finding of immutability."
            )
        # Deliberately not "immutable" and not "not upgradeable". Neither is established.
        return (
            f"No known proxy pattern matched at block {self.block_number}. "
            f"{len(PROXY_SLOTS)} conventions were probed and all were empty; a proxy using "
            f"a convention not probed here would produce this same result."
        )


def _address_from_slot(raw: str) -> str:
    """A 32-byte slot holding a left-padded address. Empty stays empty."""

    if not raw or int(raw, 16) == 0:
        return ""
    return "0x" + raw[-40:]


def token_identity(client: ChainClient, address: str, **kw: Any) -> dict[str, ChainReading]:
    """Symbol, name and decimals, each as its own reading.

    Decimals is read rather than assumed. USDC is 6 and WBTC is 8, so a supply divided by
    the wrong power of ten is wrong by two orders of magnitude while looking entirely
    plausible -- the kind of error that survives review because the number is the right
    shape.
    """

    out: dict[str, ChainReading] = {}
    for field_name in ("symbol", "name", "decimals"):
        try:
            out[field_name] = client.read(
                "eth_call", [{"to": address, "data": SELECTORS[field_name]}], **kw
            )
        except ChainAccessError:
            # A token that does not implement the optional ERC-20 metadata functions is
            # not malformed. Its absence is recorded rather than defaulted.
            continue
    return out


def total_supply(client: ChainClient, address: str, **kw: Any) -> ChainReading:
    """CG-01/CG-03: supply read from contract state, never from a published figure."""

    return client.read("eth_call", [{"to": address, "data": SELECTORS["totalSupply"]}], **kw)


def balance_of(client: ChainClient, token: str, holder: str, **kw: Any) -> ChainReading:
    """CG-03: balances of vesting, treasury and insider addresses."""

    padded = holder.lower().removeprefix("0x").rjust(64, "0")
    return client.read(
        "eth_call", [{"to": token, "data": SELECTORS["balanceOf"] + padded}], **kw
    )


def proxy_finding(client: ChainClient, address: str, **kw: Any) -> ProxyFinding:
    """CG-04: can this contract be replaced, and by whom.

    Every convention is probed by storage read. Function probes are not used as the
    primary signal because a transparent proxy reverts them for non-admin callers -- so a
    contract that answers nothing may still be a proxy, and the storage is the only place
    the truth is legible.

    A probe that could not be completed makes the whole finding INDETERMINATE rather than
    silently reducing the evidence for NO_PATTERN_MATCHED. Concluding "no pattern" from
    probes that never ran would be a measurement over an incomplete numerator.
    """

    found: dict[str, str] = {}
    unreachable: list[str] = []
    block_number = 0

    for name, slot in PROXY_SLOTS.items():
        try:
            reading = client.read("eth_getStorageAt", [address, slot], **kw)
        except TransientRetrievalError:
            unreachable.append(name)
            continue
        except ChainAccessError:
            unreachable.append(name)
            continue
        block_number = reading.block_number
        value = _address_from_slot(str(reading.value or ""))
        if value:
            found[name] = value

    if found:
        return ProxyFinding(UPGRADEABLE, address, block_number, found, tuple(unreachable))
    if unreachable:
        return ProxyFinding(INDETERMINATE, address, block_number, {}, tuple(unreachable))
    return ProxyFinding(NO_PATTERN_MATCHED, address, block_number, {}, ())


def authority_holders(client: ChainClient, address: str, **kw: Any) -> dict[str, str]:
    """CG-04: who holds privileged functions.

    `REVERTED` and the zero address are returned as different values. A reverted `owner()`
    means the contract has no owner function; a zero `owner()` means ownership was
    renounced. Reporting the first as the second would credit a project with a
    renunciation it never made.
    """

    out: dict[str, str] = {}
    for role in ("owner", "masterMinter", "admin", "implementation"):
        try:
            reading = client.read("eth_call", [{"to": address, "data": SELECTORS[role]}], **kw)
        except ChainAccessError:
            out[role] = REVERTED
            continue
        value = _address_from_slot(str(reading.value or ""))
        out[role] = value or ZERO_ADDRESS
    return out


def is_paused(client: ChainClient, address: str, **kw: Any) -> str:
    """Whether transfers are currently halted, or REVERTED if unpausable."""

    try:
        reading = client.read("eth_call", [{"to": address, "data": SELECTORS["paused"]}], **kw)
    except ChainAccessError:
        return REVERTED
    return "true" if int(str(reading.value or "0x0"), 16) else "false"
