"""The functions a control-plane UI may render, including ones not built yet.

Hard-coding three cards into a front end would make every new operating function a UI
rewrite. This registry is the stable boundary instead. A function can be active, limited,
or merely reserved, and a reserved slot is never presented as an empty but working lane.

SRE is deliberately research-only at this stage. Security research without a written target
scope can become unauthorised access, so its remedy names the first human act required
before any crawler, scanner, or model is connected.
"""
from __future__ import annotations

from dataclasses import dataclass

ACTIVE = "ACTIVE"
LIMITED = "LIMITED"
RESERVED = "RESERVED"


@dataclass(frozen=True, slots=True)
class FunctionSpec:
    function_id: str
    name: str
    category: str
    status: str
    reaper: str
    execution: str
    ui_actions: tuple[str, ...]
    limitation: str = ""
    remedy: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.function_id,
            "name": self.name,
            "category": self.category,
            "status": self.status,
            "reaper": self.reaper,
            "execution": self.execution,
            "ui_actions": list(self.ui_actions),
            "limitation": self.limitation or None,
            "remedy": self.remedy or None,
        }


FUNCTIONS = (
    FunctionSpec(
        "arb", "Arbitrage betting", "MONEY", ACTIVE, "AVAILABLE",
        "HUMAN_BET_SLIP",
        ("RUN", "VIEW_HARVEST", "RECORD_PLACEMENT", "SETTLE"),
        limitation=(
            "ordinary bookmakers expose no supported order API; the exact bet slip is "
            "the execution system"
        ),
    ),
    FunctionSpec(
        "stocks", "Stocks", "MONEY", LIMITED, "AVAILABLE", "ALPACA_ADAPTER_UNWIRED",
        ("RUN", "VIEW_HARVEST", "RECORD_PLACEMENT", "SETTLE"),
        limitation=(
            "the paper broker adapter exists, but READY StockOrder is not yet converted "
            "to an Alpaca Instruction"
        ),
        remedy="build and observe the READY-to-paper-order bridge before enabling placement",
    ),
    FunctionSpec(
        "crypto", "Crypto", "MONEY", LIMITED, "AVAILABLE", "UNSIGNED_TRANSACTION",
        ("RUN", "VIEW_HARVEST", "RECORD_PLACEMENT", "SETTLE"),
        limitation=(
            "the transaction plan is exact but the adapter has no signing or send path"
        ),
        remedy="inspect and sign the generated transaction in a wallet you control",
    ),
    FunctionSpec(
        "sre", "Security Research Engine", "RESEARCH", RESERVED, "NOT_BUILT",
        "RESEARCH_ONLY",
        ("VIEW_SCOPE", "VIEW_FINDINGS"),
        limitation=(
            "no authorised target scope, disclosure policy, scanner, or bounty workflow "
            "is configured"
        ),
        remedy=(
            "record an explicit authorised target list and each programme's safe-harbour "
            "rules before connecting any active testing"
        ),
    ),
)


def function_specs() -> tuple[FunctionSpec, ...]:
    """Every UI function in display order; callers never infer slots from money lanes."""

    return FUNCTIONS
