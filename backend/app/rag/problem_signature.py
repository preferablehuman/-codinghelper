from __future__ import annotations

import re
from pydantic import BaseModel, Field


class SemanticFlags(BaseModel):
    input_sorted: bool | None = None
    duplicates_allowed: bool | None = None
    negative_values_allowed: bool | None = None
    directed_graph: bool | None = None
    weighted_graph: bool | None = None
    negative_weights_allowed: bool | None = None
    return_indices: bool | None = None
    return_values: bool | None = None
    in_place_required: bool | None = None
    multiple_valid_outputs: bool | None = None
    modulo_required: bool | None = None
    contiguous_required: bool | None = None
    subsequence_allowed: bool | None = None


class ProblemSignature(BaseModel):
    objective: str = ""
    input_entities: list[str] = Field(default_factory=list)
    output_requirement: str = ""
    constraints: list[str] = Field(default_factory=list)
    ordering_assumptions: list[str] = Field(default_factory=list)
    uniqueness_assumptions: list[str] = Field(default_factory=list)
    value_domain: list[str] = Field(default_factory=list)
    graph_properties: list[str] = Field(default_factory=list)
    optimization_target: str = ""
    io_contract: dict[str, object] = Field(default_factory=dict)
    semantic_flags: SemanticFlags = Field(default_factory=SemanticFlags)


def deterministic_signature(text: str) -> ProblemSignature:
    lower = text.casefold()
    flags = SemanticFlags(
        input_sorted=_flag(lower, ("sorted array", "sorted sequence"), ("unsorted", "not sorted")),
        duplicates_allowed=_flag(lower, ("duplicates allowed", "may contain duplicates"), ("distinct", "unique elements")),
        negative_values_allowed=_flag(lower, ("negative integers", "may be negative"), ("positive integers", "non-negative")),
        directed_graph=_flag(lower, ("directed graph",), ("undirected graph",)),
        weighted_graph=_flag(lower, ("weighted graph", "edge weight"), ("unweighted graph",)),
        negative_weights_allowed=_flag(lower, ("negative weight",), ("non-negative weight", "positive weight")),
        return_indices=_contains(lower, "return the indices", "return indices", "indices of"),
        return_values=_contains(lower, "return the values", "return values", "values of"),
        in_place_required=_contains(lower, "in-place", "in place"),
        multiple_valid_outputs=_contains(lower, "any valid", "any order", "multiple answers"),
        modulo_required=_contains(lower, "modulo", "mod ", "% 1000000007"),
        contiguous_required=_contains(lower, "contiguous", "subarray", "substring"),
        subsequence_allowed=_contains(lower, "subsequence", "not necessarily contiguous"),
    )
    constraints = [line.strip() for line in text.splitlines() if re.search(r"(?:<=|>=|<|>|10\^|10\*\*|\d+\s*(?:to|\.\.)\s*\d+)", line)]
    objective = next((line.strip() for line in text.splitlines() if any(word in line.casefold() for word in ("find", "return", "determine", "compute", "minimize", "maximize"))), "")
    output = next((line.strip() for line in text.splitlines() if line.casefold().startswith("output")), "")
    return ProblemSignature(
        objective=objective,
        output_requirement=output,
        constraints=constraints,
        ordering_assumptions=["sorted"] if flags.input_sorted else [],
        uniqueness_assumptions=["duplicates allowed" if flags.duplicates_allowed else "distinct"] if flags.duplicates_allowed is not None else [],
        value_domain=["negative values allowed"] if flags.negative_values_allowed else [],
        graph_properties=[item for item, enabled in (("directed", flags.directed_graph), ("weighted", flags.weighted_graph)) if enabled],
        optimization_target="minimize" if "minimize" in lower or "minimum" in lower else "maximize" if "maximize" in lower or "maximum" in lower else "",
        io_contract={"has_explicit_input": "input:" in lower, "has_explicit_output": "output:" in lower},
        semantic_flags=flags,
    )


def _contains(text: str, *phrases: str) -> bool | None:
    return True if any(phrase in text for phrase in phrases) else None


def _flag(text: str, positive: tuple[str, ...], negative: tuple[str, ...]) -> bool | None:
    if any(item in text for item in negative):
        return False
    if any(item in text for item in positive):
        return True
    return None
