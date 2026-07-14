from app.rag.problem_matcher import hard_contradictions
from app.rag.problem_signature import ProblemSignature, SemanticFlags


def signature(**flags):
    return ProblemSignature(semantic_flags=SemanticFlags(**flags))


def test_indices_and_values_are_hard_contradiction():
    assert "return indices versus return values" in hard_contradictions(signature(return_indices=True), signature(return_values=True))


def test_substring_and_subsequence_are_not_reused():
    contradictions = hard_contradictions(signature(contiguous_required=True, subsequence_allowed=False), signature(contiguous_required=False, subsequence_allowed=True))
    assert "contiguous versus non-contiguous" in contradictions
    assert "substring versus subsequence" in contradictions


def test_unknown_flags_do_not_create_false_contradictions():
    assert hard_contradictions(signature(input_sorted=True), signature()) == []
