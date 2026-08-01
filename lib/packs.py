"""What a domain has to declare before this engine can study it.

The shape is deliberately narrow. A pack supplies vocabulary and named mechanisms; it
does not supply logic, thresholds, or gate outcomes. A domain that could set its own
proof-gate thresholds would be marking its own homework, in the same way a methodology
profile that could supply its own outcome vocabulary would be deciding what FAIL means.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from lib.terms import contains_any


@dataclass(frozen=True, slots=True)
class TermGroup:
    """One condition: at least one of these terms appears in the text.

    Named, because a rule that fires for an unobvious reason should be able to say which
    group carried it. Matching is delegated to `contains_any`, which uses word-boundary
    matching -- substring matching once classified "telecommunications" as
    "communication" and "distilled" as "still", and that fix must not be re-lost here.
    """

    name: str
    terms: tuple[str, ...]

    def matches(self, text: str) -> bool:
        return contains_any(text, list(self.terms))


@dataclass(frozen=True, slots=True)
class MechanismRule:
    """A named mechanism and the conditions that identify it.

    `requires` is an AND of ORs: every element must be satisfied, and an element is
    satisfied by any one of its groups. That is exactly the shape the original if-ladder
    had -- three plain conjunctions and one with a disjunctive second limb -- so this
    expresses the existing rules rather than approximating them.
    """

    mechanism_id: str
    requires: tuple[tuple[TermGroup, ...], ...]

    def matches(self, text: str) -> bool:
        return all(
            any(group.matches(text) for group in alternatives)
            for alternatives in self.requires
        )

    def matching_groups(self, text: str) -> list[str]:
        """Which groups carried this rule. Diagnostics, never a decision input."""

        return [
            group.name
            for alternatives in self.requires
            for group in alternatives
            if group.matches(text)
        ]


@dataclass(frozen=True, slots=True)
class DomainPack:
    """One domain's vocabulary, mechanisms and sources.

    `default_mechanism` is the unclassified fallback. It is a per-pack value rather than
    a shared constant for a specific reason: two records that both failed to classify
    once matched each other on a shared fallback and produced a corroboration PASS from
    two records that had corroborated nothing. A fallback must never be equality-matched
    as though it were a result, and packs having distinct fallbacks makes an accidental
    cross-domain match impossible as well as forbidden.
    """

    domain_id: str
    name: str
    research_question: str

    # The family that supplies the study's discovery material. It is the family whose
    # sole presence caps a finding, so its name appears in finding text -- but never in
    # a state identifier, or the state machine would be about one connector again.
    primary_source_family: str

    process_terms: tuple[str, ...]
    failure_terms: tuple[str, ...]
    taxonomy_phrases: tuple[str, ...]
    software_addressable_terms: tuple[str, ...]

    mechanism_rules: tuple[MechanismRule, ...]
    default_mechanism: str
    mechanism_definitions: dict[str, dict[str, str]]

    # Retrieval is correctly per-domain: connectors are the socket, not the weld.
    connectors: dict[str, Callable[..., Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # A pack that names a mechanism in a rule and defines it nowhere would produce a
        # finding whose operational step is blank, which reads as an incomplete study
        # rather than an incomplete pack.
        declared = {rule.mechanism_id for rule in self.mechanism_rules}
        declared.add(self.default_mechanism)
        undefined = sorted(declared - set(self.mechanism_definitions))
        if undefined:
            raise ValueError(f"{self.domain_id}: mechanisms declared but not defined: {undefined}")
        if self.default_mechanism in {rule.mechanism_id for rule in self.mechanism_rules}:
            raise ValueError(
                f"{self.domain_id}: the fallback {self.default_mechanism!r} is also a rule "
                "outcome, so a classified record and an unclassified one would be "
                "indistinguishable"
            )

    def classify(self, text: str) -> str:
        """First matching rule wins, in declared order. No match is the fallback."""

        for rule in self.mechanism_rules:
            if rule.matches(text):
                return rule.mechanism_id
        return self.default_mechanism

    def definition(self, mechanism: str) -> dict[str, str]:
        return dict(
            self.mechanism_definitions.get(
                mechanism, self.mechanism_definitions[self.default_mechanism]
            )
        )

    @property
    def mechanism_ids(self) -> frozenset[str]:
        return frozenset({rule.mechanism_id for rule in self.mechanism_rules} | {self.default_mechanism})
