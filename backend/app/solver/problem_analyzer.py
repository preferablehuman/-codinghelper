import logging
from dataclasses import dataclass

from app.model_runtime.base import BaseModelRuntime
from app.model_runtime.json_utils import optional_string, parse_json_object, response_preview
from app.model_runtime.prompts import problem_analysis_prompt
from app.rag.problem_signature import ProblemSignature, deterministic_signature


logger = logging.getLogger(__name__)


PATTERN_KEYWORDS = {
    "arrays": ["array", "list", "sequence", "element"],
    "strings": ["string", "character", "substring", "subsequence"],
    "sliding_window": ["subarray", "substring", "window", "longest", "at most", "contiguous"],
    "hash_map": ["two sum", "frequency", "duplicate", "anagram", "lookup", "indices"],
    "prefix_sum": ["sum range", "range sum", "prefix", "cumulative"],
    "binary_search": ["sorted", "minimum possible", "maximum possible", "search", "monotonic"],
    "sorting": ["sort", "sorted", "order"],
    "greedy": ["minimum number", "maximum number", "choose", "interval scheduling"],
    "dynamic_programming": ["ways", "minimum cost", "maximum profit", "subsequence", "dp"],
    "graph_bfs": ["shortest path", "level", "unweighted graph", "grid"],
    "graph_dfs": ["connected", "island", "cycle", "dfs"],
    "dijkstra": ["weighted graph", "shortest path", "non-negative"],
    "union_find": ["disjoint", "union", "connected components"],
    "tree_traversal": ["tree", "binary tree", "root", "leaf"],
    "recursion": ["recursive", "recursion"],
    "backtracking": ["all combinations", "permutations", "subsets", "backtrack"],
    "heap": ["kth", "top k", "priority", "median"],
    "stack": ["parentheses", "next greater", "monotonic stack"],
    "queue": ["queue", "first in first out"],
    "monotonic_stack": ["next greater", "previous smaller", "monotonic"],
    "two_pointers": ["pair", "sorted array", "left", "right"],
    "intervals": ["interval", "overlap", "merge"],
    "bit_manipulation": ["bit", "xor", "mask"],
}


@dataclass(frozen=True)
class ProblemAnalysis:
    summary: str
    selected_pattern: str
    candidate_patterns: list[str]
    edge_cases: list[str]
    signature: ProblemSignature


def analyze_problem(runtime: BaseModelRuntime, problem_text: str, language: str) -> ProblemAnalysis:
    heuristic = analyze_problem_heuristic(problem_text)
    deterministic = deterministic_signature(problem_text)
    logger.debug(
        "Analyzing problem with model language=%s heuristic_selected=%s candidate_count=%s problem_chars=%s",
        language,
        heuristic.selected_pattern,
        len(heuristic.candidate_patterns),
        len(problem_text),
    )
    raw = runtime.generate(
        problem_analysis_prompt(problem_text, language, heuristic.candidate_patterns),
        max_new_tokens=1024,
        json_mode=True,
        schema_name="problem_analysis",
    )
    try:
        data = parse_json_object(raw)
    except ValueError:
        logger.error("Problem analysis JSON parse failed response_preview=%s", response_preview(raw))
        raise
    summary = optional_string(data, "summary") or heuristic.summary
    candidate_patterns = _normalize_patterns(data.get("candidate_patterns"))
    selected_pattern = _normalize_pattern(optional_string(data, "selected_pattern") or heuristic.selected_pattern)

    if selected_pattern not in PATTERN_KEYWORDS:
        selected_pattern = heuristic.selected_pattern
    if not candidate_patterns:
        candidate_patterns = heuristic.candidate_patterns
    if selected_pattern not in candidate_patterns:
        candidate_patterns = [selected_pattern, *candidate_patterns]

    edge_cases = _normalize_edge_cases(data.get("edge_cases")) or heuristic.edge_cases
    signature_data = {key: data.get(key, getattr(deterministic, key)) for key in ProblemSignature.model_fields}
    try:
        signature = ProblemSignature.model_validate(signature_data)
    except Exception:
        logger.warning("Problem semantic signature validation failed; using deterministic signature")
        signature = deterministic
    logger.info(
        "Problem analysis parsed selected_pattern=%s candidate_count=%s edge_case_count=%s",
        selected_pattern,
        len(candidate_patterns),
        len(edge_cases),
    )
    return ProblemAnalysis(
        summary=summary,
        selected_pattern=selected_pattern,
        candidate_patterns=candidate_patterns[:6],
        edge_cases=edge_cases[:10],
        signature=signature,
    )


def analyze_problem_heuristic(problem_text: str) -> ProblemAnalysis:
    lower = problem_text.lower()
    scored: list[tuple[int, str]] = []
    for pattern, keywords in PATTERN_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in lower)
        if score:
            scored.append((score, pattern))

    scored.sort(reverse=True)
    candidates = [pattern for _, pattern in scored[:4]] or ["hash_map", "arrays"]
    selected = candidates[0]
    summary = problem_text.strip().splitlines()[0][:240]
    if len(problem_text.strip()) > len(summary):
        summary = f"{summary}..."

    analysis = ProblemAnalysis(
        summary=summary,
        selected_pattern=selected,
        candidate_patterns=candidates,
        edge_cases=["empty input where valid", "single element", "duplicates", "large values", "no solution"],
        signature=deterministic_signature(problem_text),
    )
    logger.debug("Heuristic analysis selected_pattern=%s candidates=%s", analysis.selected_pattern, analysis.candidate_patterns)
    return analysis


def _normalize_patterns(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    patterns = []
    for item in value:
        if not isinstance(item, str):
            continue
        pattern = _normalize_pattern(item)
        if pattern in PATTERN_KEYWORDS and pattern not in patterns:
            patterns.append(pattern)
    return patterns


def _normalize_pattern(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def _normalize_edge_cases(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]
