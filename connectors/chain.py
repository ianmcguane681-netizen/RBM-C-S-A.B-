"""Read chain state as evidence, with the provenance that makes it evidence.

A figure taken from a chain is worth exactly what its provenance is worth. `totalSupply
is 55,000,000` is a claim; `totalSupply at block 25,660,449 on ethereum, contract
0xA0b8...eB48, via eth_call 0x18160ddd, sha256 8f3c...` is a measurement, because anyone
can regenerate it. Every read here returns the second kind or nothing.

Providers are not interchangeable and the differences are not documented anywhere
convenient, so they are declared. Measured on 2026-08-01:

    quicknode (keyed, free tier)  archive 9/9 heights   getLogs  6 blocks
    1rpc.io/eth                   archive 4/8 heights   getLogs 50 blocks
    ethereum-rpc.publicnode.com   archive none          getLogs none
    rpc.ankr.com                  requires a key even for eth_blockNumber
    eth.llamarpc.com              HTTP 521
    cloudflare-eth.com            refuses eth_blockNumber

That table inverts the obvious assumption and is the reason `best_for(task)` exists. The
keyed endpoint is the only one usable for history and is **eight times worse** for logs;
the anonymous one is the reverse. A single "preferred provider" would silently degrade
half the work, so state reads and log walks resolve to different endpoints.

"Unreliable" rather than "yes" is the whole lesson of that measurement. A single
historical query against 1rpc succeeded, which looked like archive support. Repeating it
across a spread of block heights did not: the same `eth_call` was answered at lag 32, 64
and 1000 blocks and refused at 12, 128, 256 and 100,000. That is a load balancer in front
of backends with different state retention, so historical availability is drawn per
request. A figure that reproduces only sometimes cannot satisfy CG-06, and one successful
query is not evidence of a capability -- it is one draw.

Hence reads default to the `finalized` tag rather than an explicit height. Tags are served
consistently, and post-merge finality also means the state cannot later be reorged out
from under evidence already recorded. The tag is what gets queried; the height it resolved
to is what gets recorded.

The log cap is the constraint that shapes everything else, and it is small on every free
endpoint measured. A continuously running watcher only ever asks for the newest blocks --
one request per ten minutes of chain on the 50-block endpoint -- so forward capture is
comfortable. Historical backfill over a month is roughly 4,300 requests at 50 blocks and
36,000 at 6, and is not.

The distinction this module exists to protect: **"the range holds no logs" and "the
provider refused to answer" are different facts.** Recording the second as the first is
how a rate-limited afternoon becomes a permanent statement about on-chain activity. The
first is an observation; the second is a `TransientRetrievalError`.
"""
from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable

from lib.http_retry import TransientRetrievalError, is_transient, retrying_urlopen

USER_AGENT = "evidence-board/0.1 chain evidence"

# Post-merge Ethereum finality. Evidence taken at `latest` can be reorged away; evidence
# taken at `finalized` cannot. Public endpoints also serve tags reliably while serving
# explicit historical heights inconsistently, so this is both the safer and the more
# available choice.
FINALIZED = "finalized"
SAFE = "safe"
LATEST = "latest"
ACCESS_TIMEOUT_SECONDS = 30


@dataclass(frozen=True, slots=True)
class ChainProvider:
    """An RPC endpoint and the limits it actually enforces.

    `serves_archive` and `max_log_range` are declared rather than discovered, for the same
    reason the profile registry declares expected file counts: a caller that learns a limit
    by hitting it has already made a request it cannot use, and a caller that assumes no
    limit will silently receive a truncated answer.
    """

    name: str
    url: str
    chain: str
    max_log_range: int
    # "yes", "no", or "unreliable". A boolean here would have to choose between calling
    # 1rpc an archive provider (it answers some historical heights) and calling it not one
    # (it refuses others). Both are wrong, and the third value is the measurement.
    archive: str = "no"
    requires_key: bool = False

    @property
    def serves_archive(self) -> bool:
        """True only where historical reads can be relied upon, not merely attempted."""

        return self.archive == "yes"


# Anonymous and free. Serves current state and block tags reliably; historical heights
# are a lottery (see the module docstring).
ONE_RPC_ETHEREUM = ChainProvider(
    name="1rpc.io",
    url="https://1rpc.io/eth",
    chain="ethereum",
    max_log_range=50,
    # Measured 2026-08-01: the same eth_call succeeded at lag 32, 64 and 1000 blocks and
    # was refused at 12, 128, 256 and 100,000. That is a load balancer in front of
    # backends with different state retention, not an archive node.
    archive="unreliable",
)

# Latest state only. Kept as a declared fallback rather than deleted, because a caller that
# only needs current state should be able to spread load across both.
PUBLICNODE_ETHEREUM = ChainProvider(
    name="publicnode",
    url="https://ethereum-rpc.publicnode.com",
    chain="ethereum",
    max_log_range=0,
    archive="no",
)

QUICKNODE_URL_ENV = "QUICKNODE_ETHEREUM_URL"


def quicknode_ethereum(url: str = "") -> ChainProvider:
    """A keyed QuickNode endpoint, read from the environment by default.

    The URL embeds the auth token in its path, so it is a credential and never appears
    in this repository. Measured on 2026-08-01 against a free-tier endpoint:

        archive     9 of 9 heights answered, from the tip to 5,000,000 blocks back
        getLogs     6 blocks inclusive succeeds, 7 returns HTTP 413

    The log cap is contract-independent -- WBTC failed at 7 blocks with ~60 logs while
    USDC succeeded at 6 with 482 -- so it is a span limit rather than a result limit, and
    it is eight times tighter than the anonymous public endpoint's.

    That inversion is why providers are chosen per task rather than globally. This one is
    for state; 1rpc is for logs. A single "best provider" would be wrong for half the work.
    """

    resolved = (url or os.environ.get(QUICKNODE_URL_ENV, "")).strip()
    if not resolved:
        raise ChainAccessError(
            f"No QuickNode URL. Set {QUICKNODE_URL_ENV}; it contains an auth token and "
            f"must never be committed."
        )
    return ChainProvider(
        name="quicknode",
        url=resolved,
        chain="ethereum",
        max_log_range=6,
        archive="yes",
        requires_key=True,
    )


PROVIDERS: dict[str, ChainProvider] = {
    ONE_RPC_ETHEREUM.name: ONE_RPC_ETHEREUM,
    PUBLICNODE_ETHEREUM.name: PUBLICNODE_ETHEREUM,
}


def best_for(task: str, *, quicknode_url: str = "") -> ChainProvider:
    """Pick a provider by what it is measurably good at, not by preference order.

    `state` needs archive reliability; `logs` needs range. Measurement says no single
    endpoint wins both, and pretending otherwise would silently degrade one of them.
    """

    if task == "state":
        try:
            return quicknode_ethereum(quicknode_url)
        except ChainAccessError:
            # Falling back is legitimate for current-state reads, which 1rpc serves
            # reliably. It is not legitimate for historical reads, and `read` already
            # refuses those against an unreliable provider rather than guessing.
            return ONE_RPC_ETHEREUM
    if task == "logs":
        return ONE_RPC_ETHEREUM
    raise ValueError(f"Unknown task {task!r}; expected 'state' or 'logs'")


class ChainAccessError(RuntimeError):
    """The provider gave a real answer and the answer was an error.

    Distinct from `TransientRetrievalError` on purpose: this one will not succeed on
    retry. A malformed address or a call to a non-contract is an answer about the world.
    """


@dataclass(frozen=True, slots=True)
class ChainReading:
    """A value and everything needed to regenerate it.

    `provenance` is not decoration. CG-06 requires that every figure record chain, block
    height, contract and query, and this is the type that makes forgetting one impossible
    rather than merely discouraged.
    """

    value: Any
    chain: str
    block_number: int
    method: str
    params: Any
    provider: str
    retrieved_at: str
    content_sha256: str = field(default="")

    def __post_init__(self) -> None:
        if not self.content_sha256:
            object.__setattr__(self, "content_sha256", self.digest())
        if self.block_number <= 0:
            raise ValueError(
                "A reading without a block height cannot be reproduced, so it is a claim "
                "rather than a measurement. Refusing to construct one."
            )

    def digest(self) -> str:
        payload = json.dumps(
            {
                "chain": self.chain,
                "block": self.block_number,
                "method": self.method,
                "params": self.params,
                "value": self.value,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def provenance(self) -> dict[str, Any]:
        return {
            "kind": "CHAIN_STATE",
            "chain": self.chain,
            "block_number": self.block_number,
            "method": self.method,
            "params": self.params,
            "provider": self.provider,
            "retrieved_at": self.retrieved_at,
            "content_sha256": self.content_sha256,
        }


class ChainClient:
    """JSON-RPC access that distinguishes a refusal from an answer."""

    def __init__(
        self,
        provider: ChainProvider = ONE_RPC_ETHEREUM,
        *,
        api_key: str = "",
        post_json: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None,
        clock: Callable[[], str] | None = None,
    ) -> None:
        # `requires_key` means the endpoint is credentialed, not that a separate key
        # argument is expected. QuickNode embeds its token in the URL path, so the URL
        # *is* the credential; demanding an additional `api_key` would reject a perfectly
        # authenticated provider. What matters is that a credentialed provider never runs
        # with an empty URL, because an unauthenticated call returns an authorisation
        # error that is indistinguishable from an empty result.
        if provider.requires_key and not provider.url.strip():
            raise ChainAccessError(
                f"{provider.name} is a credentialed endpoint with no URL configured."
            )
        self.provider = provider
        self.api_key = api_key
        self._post_json = post_json or self._default_post_json
        self._clock = clock or _utc_now

    # -- transport ---------------------------------------------------------------

    def _default_post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
            method="POST",
        )
        with retrying_urlopen(request, timeout=ACCESS_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8", errors="ignore"))

    def call(self, method: str, params: list[Any] | None = None) -> Any:
        """One JSON-RPC call. Raises rather than returning a value it did not get."""

        payload = {"jsonrpc": "2.0", "method": method, "params": params or [], "id": 1}
        try:
            body = self._post_json(self.provider.url, payload)
        except Exception as error:  # noqa: BLE001 - re-raised, never swallowed
            if is_transient(error):
                raise TransientRetrievalError(
                    f"{method} on {self.provider.name} could not be completed: {error}"
                ) from error
            raise ChainAccessError(f"{method} on {self.provider.name} failed: {error}") from error

        if "error" in body:
            message = str(body["error"].get("message", body["error"]))
            # Some providers report throttling and archive refusal inside a 200 response
            # with a JSON-RPC error, so status code alone does not classify it.
            if _is_transient_rpc_message(message):
                raise TransientRetrievalError(
                    f"{method} on {self.provider.name} was refused, not answered: {message}"
                )
            raise ChainAccessError(f"{method} on {self.provider.name}: {message}")
        return body.get("result")

    # -- reads -------------------------------------------------------------------

    def block_number(self) -> int:
        return int(self.call("eth_blockNumber"), 16)

    def resolve_block(self, tag: str = FINALIZED) -> int:
        """Turn a block tag into the concrete height it currently means."""

        block = self.call("eth_getBlockByNumber", [tag, False])
        if not block or "number" not in block:
            raise ChainAccessError(f"{self.provider.name} did not resolve tag {tag!r}")
        return int(block["number"], 16)

    def read(
        self,
        method: str,
        params: list[Any],
        *,
        block_number: int | None = None,
        tag: str = FINALIZED,
    ) -> ChainReading:
        """Perform a read and pin it to a block height.

        Defaults to reading at `finalized` rather than `latest`, for two reasons.

        The first is correctness: on post-merge Ethereum `latest` can still be reorged, so
        evidence taken there can be quietly invalidated by consensus. `finalized` cannot.
        Recording a figure that a reorg later erases is the chain-native version of
        recording a rate limit as an observation.

        The second is availability, discovered by measurement rather than assumption. A
        public endpoint that load-balances across backends with different state retention
        answers an explicit historical height inconsistently -- measured on 1rpc.io, the
        same query succeeded at lag 32, 64 and 1000 blocks and was refused at 12, 128, 256
        and 100,000. Tags are served reliably; explicit historical heights are not. So the
        tag is what we query, and the height it resolved to is what we record.

        The height is resolved *before* the value is read, so a recorded height is never
        later than the state it describes.
        """

        if block_number is not None:
            if not self.provider.serves_archive:
                raise ChainAccessError(
                    f"{self.provider.name} does not serve archive state, so it cannot "
                    f"answer for block {block_number}. Its answer for 'latest' would be a "
                    f"different measurement wearing this block's label."
                )
            height = block_number
            pinned = _with_block_tag(method, params, hex(height))
        else:
            height = self.resolve_block(tag)
            # Query by tag, record by number. Querying the resolved number instead would
            # re-introduce the availability lottery for no gain.
            pinned = _with_block_tag(method, params, tag)

        value = self.call(method, pinned)
        return ChainReading(
            value=value,
            chain=self.provider.chain,
            block_number=height,
            method=method,
            params=pinned,
            provider=self.provider.name,
            retrieved_at=self._clock(),
        )

    def get_logs(
        self, address: str, topics: list[Any], from_block: int, to_block: int
    ) -> tuple[list[dict[str, Any]], list[tuple[int, int]]]:
        """Fetch logs across a range, splitting to respect the provider's cap.

        Returns the logs and the ranges actually covered. The caller needs the second:
        a partial walk that reported only its logs would understate activity by exactly
        the ranges it never reached, with nothing in the result to say so.
        """

        if self.provider.max_log_range <= 0:
            raise ChainAccessError(
                f"{self.provider.name} does not serve logs; a caller expecting them would "
                f"read its refusal as an absence of activity."
            )
        if to_block < from_block:
            raise ValueError("to_block precedes from_block")

        collected: list[dict[str, Any]] = []
        covered: list[tuple[int, int]] = []
        start = from_block
        while start <= to_block:
            end = min(start + self.provider.max_log_range - 1, to_block)
            result = self.call(
                "eth_getLogs",
                [
                    {
                        "address": address,
                        "topics": topics,
                        "fromBlock": hex(start),
                        "toBlock": hex(end),
                    }
                ],
            )
            collected.extend(result or [])
            covered.append((start, end))
            start = end + 1
        return collected, covered


def _with_block_tag(method: str, params: list[Any], tag: str) -> list[Any]:
    """Append the block tag for methods that accept one, leave others alone."""

    if method in {"eth_call", "eth_getBalance", "eth_getCode", "eth_getStorageAt"}:
        return [*params, tag]
    return list(params)


_TRANSIENT_RPC_WORDING = (
    "rate limit",
    "too many requests",
    "capacity",
    "timeout",
    "timed out",
    "try again",
    "temporarily",
    "archive requests require",
)


def _is_transient_rpc_message(message: str) -> bool:
    """Is this JSON-RPC error a refusal to answer rather than an answer?

    String matching, which is normally the wrong tool -- but JSON-RPC has no structured
    field for "I declined", and the alternative is treating every refusal as an
    observation. The list is deliberately narrow and anchored to wording observed in the
    wild rather than guessed at.
    """

    lowered = message.lower()
    return any(phrase in lowered for phrase in _TRANSIENT_RPC_WORDING)


def _utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
