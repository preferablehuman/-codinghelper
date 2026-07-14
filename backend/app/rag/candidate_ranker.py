from dataclasses import dataclass
from difflib import SequenceMatcher

from app.rag.problem_matcher import hard_contradictions, signature_compatibility
from app.rag.problem_normalizer import NormalizedProblem
from app.rag.problem_signature import ProblemSignature


@dataclass(frozen=True)
class RankedCandidate:
    score: float
    relation: str
    contradictions: list[str]


def rank_candidate(incoming: NormalizedProblem, incoming_signature: ProblemSignature, candidate: NormalizedProblem, candidate_signature: ProblemSignature) -> RankedCandidate:
    if incoming.statement_hash == candidate.statement_hash:
        return RankedCandidate(1.0, "EXACT", [])
    lexical = SequenceMatcher(None, incoming.normalized_text, candidate.normalized_text).ratio()
    contradictions = hard_contradictions(incoming_signature, candidate_signature)
    compatibility = 0.0 if contradictions else signature_compatibility(incoming_signature, candidate_signature)
    score = lexical * 0.65 + compatibility * 0.35
    relation = "DIFFERENT" if contradictions or score < 0.72 else "EQUIVALENT" if score >= 0.90 else "RELATED"
    return RankedCandidate(score, relation, contradictions)
