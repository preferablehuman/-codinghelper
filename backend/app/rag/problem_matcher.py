from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Literal

from app.config import Settings
from app.db.models import CanonicalProblem
from app.rag.problem_normalizer import NormalizedProblem
from app.rag.problem_repository import ProblemRepository
from app.rag.problem_signature import ProblemSignature
from app.rag.embeddings import embed_texts
from app.rag.qdrant_store import QdrantStore
from app.model_runtime.base import BaseModelRuntime
from app.model_runtime.json_utils import parse_json_object
from app.model_runtime.prompts import problem_equivalence_prompt


Route = Literal["EXACT_REUSE", "EQUIVALENT_ADAPT", "RELATED_GROUNDING", "EXTERNAL_DISCOVERY", "GENERATE_FRESH"]


@dataclass(frozen=True)
class RetrievalDecision:
    route: Route
    canonical_problem_id: str | None
    match_type: str
    confidence: float
    contradictions: list[str] = field(default_factory=list)
    reusable_solution_ids: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    component_scores: dict[str, float] = field(default_factory=dict)


def adjudicate_equivalence(runtime: BaseModelRuntime, decision: RetrievalDecision, incoming: ProblemSignature, canonical: CanonicalProblem) -> RetrievalDecision:
    if decision.route != "EQUIVALENT_ADAPT" or decision.contradictions:
        return decision
    stored = _stored_signature(canonical)
    try:
        raw = runtime.generate(problem_equivalence_prompt(incoming.model_dump(), stored.model_dump()), max_new_tokens=1024, json_mode=True, schema_name="problem_equivalence")
        data = parse_json_object(raw)
    except Exception:
        return RetrievalDecision("RELATED_GROUNDING", decision.canonical_problem_id, "RELATED_PROBLEM", decision.confidence, reasons=[*decision.reasons, "Equivalence adjudication unavailable; reuse withheld"], component_scores=decision.component_scores)
    relation = str(data.get("relation", "DIFFERENT")).upper()
    confidence = min(float(data.get("confidence", 0.0)), decision.confidence)
    if relation not in {"EXACT", "EQUIVALENT"}:
        return RetrievalDecision("RELATED_GROUNDING", decision.canonical_problem_id, "RELATED_PROBLEM", confidence, reasons=[*decision.reasons, f"LLM advisory relation={relation}"], component_scores=decision.component_scores)
    return RetrievalDecision(decision.route, decision.canonical_problem_id, decision.match_type, confidence, reusable_solution_ids=decision.reusable_solution_ids, reasons=[*decision.reasons, f"LLM advisory relation={relation}"], component_scores=decision.component_scores)


def decide_local_retrieval(
    repository: ProblemRepository,
    normalized: NormalizedProblem,
    incoming_signature: ProblemSignature,
    language: str,
    settings: Settings,
) -> RetrievalDecision:
    if not settings.rag_reuse_enabled:
        return RetrievalDecision("EXTERNAL_DISCOVERY" if settings.rag_external_discovery_enabled else "GENERATE_FRESH", None, "NO_MATCH", 0.0, reasons=["Local reuse disabled"])
    exact = repository.find_exact(normalized)
    if exact:
        solutions = repository.verified_solutions(exact.id, language)
        if not solutions:
            solutions = repository.verified_solutions(exact.id)
        return RetrievalDecision(
            "EXACT_REUSE" if solutions else "RELATED_GROUNDING",
            exact.id,
            "EXACT_SOURCE_ID" if normalized.source_platform and normalized.source_problem_id == exact.source_problem_id else "EXACT_STATEMENT",
            1.0,
            reusable_solution_ids=[solution.id for solution in solutions],
            reasons=["Deterministic source identity or normalized statement hash matched"],
        )

    lexical_candidates = repository.lexical_candidates(normalized.normalized_text, settings.rag_max_local_candidates)
    semantic_by_id: dict[str, float] = {}
    try:
        vectors = embed_texts([normalized.normalized_text], settings.embedding_model_name, allow_remote_download=settings.embedding_allow_remote_download, cache_dir=settings.embedding_cache_dir)
        for result in QdrantStore().search_problem_variants(vectors[0] if vectors else [], limit=settings.rag_max_local_candidates):
            payload = result.get("payload", {}) if isinstance(result, dict) else {}
            if isinstance(payload, dict) and payload.get("canonical_problem_id"):
                semantic_by_id[str(payload["canonical_problem_id"])] = float(result.get("score", 0.0))
    except Exception:
        semantic_by_id = {}
    candidates = {candidate.id: (candidate, lexical) for candidate, lexical in lexical_candidates}
    for candidate_id in semantic_by_id:
        if candidate_id not in candidates:
            candidate = repository.db.get(CanonicalProblem, candidate_id)
            if candidate and candidate.status == "ACTIVE":
                candidates[candidate_id] = (candidate, 0.0)
    best: tuple[CanonicalProblem, float, list[str], dict[str, float]] | None = None
    for candidate, lexical in candidates.values():
        stored_signature = _stored_signature(candidate)
        contradictions = hard_contradictions(incoming_signature, stored_signature)
        compatibility = 0.0 if contradictions else signature_compatibility(incoming_signature, stored_signature)
        scores = {
            "semantic": semantic_by_id.get(candidate.id, lexical),
            "lexical": lexical,
            "constraint": compatibility,
            "io": compatibility,
            "objective": compatibility,
        }
        final = (
            scores["semantic"] * settings.rag_semantic_weight
            + scores["lexical"] * settings.rag_lexical_weight
            + scores["constraint"] * settings.rag_constraint_weight
            + scores["io"] * settings.rag_io_weight
            + scores["objective"] * settings.rag_objective_weight
        )
        if best is None or final > best[1]:
            best = candidate, final, contradictions, scores
    if not best:
        return RetrievalDecision("EXTERNAL_DISCOVERY" if settings.rag_external_discovery_enabled else "GENERATE_FRESH", None, "NO_MATCH", 0.0)
    candidate, score, contradictions, scores = best
    if contradictions:
        return RetrievalDecision("RELATED_GROUNDING", candidate.id, "REJECTED_CONTRADICTION", score, contradictions, reasons=["Hard semantic contradiction prevents reuse"], component_scores=scores)
    solutions = repository.verified_solutions(candidate.id, language) or repository.verified_solutions(candidate.id)
    if score >= settings.rag_equivalent_threshold and solutions:
        return RetrievalDecision("EQUIVALENT_ADAPT", candidate.id, "EQUIVALENT_VARIANT", score, reusable_solution_ids=[item.id for item in solutions], reasons=["High compatible lexical/semantic score; adaptation and reverification required"], component_scores=scores)
    if score >= settings.rag_related_threshold:
        return RetrievalDecision("RELATED_GROUNDING", candidate.id, "RELATED_PROBLEM", score, reasons=["Related evidence only; executable reuse prohibited"], component_scores=scores)
    return RetrievalDecision("EXTERNAL_DISCOVERY" if settings.rag_external_discovery_enabled else "GENERATE_FRESH", None, "NO_MATCH", score, component_scores=scores)


def hard_contradictions(incoming: ProblemSignature, stored: ProblemSignature) -> list[str]:
    pairs = {
        "return indices versus return values": ("return_indices", "return_values"),
        "sorted versus unsorted input": ("input_sorted",),
        "duplicates allowed versus distinct elements": ("duplicates_allowed",),
        "directed versus undirected graph": ("directed_graph",),
        "negative edge weights": ("negative_weights_allowed",),
        "contiguous versus non-contiguous": ("contiguous_required",),
        "substring versus subsequence": ("subsequence_allowed",),
        "in-place contract": ("in_place_required",),
    }
    left = incoming.semantic_flags.model_dump()
    right = stored.semantic_flags.model_dump()
    contradictions: list[str] = []
    if left.get("return_indices") and right.get("return_values") or left.get("return_values") and right.get("return_indices"):
        contradictions.append("return indices versus return values")
    for reason, names in pairs.items():
        for name in names:
            if left.get(name) is not None and right.get(name) is not None and left[name] != right[name] and reason not in contradictions:
                contradictions.append(reason)
    return contradictions


def signature_compatibility(left: ProblemSignature, right: ProblemSignature) -> float:
    left_flags = left.semantic_flags.model_dump()
    right_flags = right.semantic_flags.model_dump()
    comparable = [(left_flags[key], right_flags[key]) for key in left_flags if left_flags[key] is not None and right_flags[key] is not None]
    flag_score = sum(a == b for a, b in comparable) / len(comparable) if comparable else 0.75
    objective_score = 1.0 if left.objective and right.objective and set(left.objective.casefold().split()) & set(right.objective.casefold().split()) else 0.6
    return (flag_score + objective_score) / 2


def _stored_signature(problem: CanonicalProblem) -> ProblemSignature:
    try:
        flags = json.loads(problem.semantic_flags_json or "{}")
    except json.JSONDecodeError:
        flags = {}
    return ProblemSignature(
        objective=problem.objective_signature or "",
        constraints=json.loads(problem.constraint_signature_json or "[]") if (problem.constraint_signature_json or "").lstrip().startswith("[") else [],
        io_contract={"input": problem.input_signature_json, "output": problem.output_signature_json},
        semantic_flags=flags,
    )
