import logging
from dataclasses import dataclass

import httpx
import trafilatura
from bs4 import BeautifulSoup

from app.config import get_settings
from app.retrieval.compliance import apply_storage_limit, get_policy


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetrievedSource:
    title: str
    url: str
    source_name: str
    source_tier: int
    text: str
    retrieval_method: str
    is_cache_allowed: bool
    license_note: str | None = None


# Direct teaching references only. Language/API manuals and broad homepages are
# deliberately excluded because they do not explain why an algorithm works.
PATTERN_SOURCES: dict[str, list[tuple[str, str, str, int, str]]] = {
    "arrays": [
        ("Array data structure and operations", "https://www.geeksforgeeks.org/array-data-structure-guide/", "geeksforgeeks", 3, "Arrays store indexed values contiguously; solutions usually exploit direct access, scans, or auxiliary state."),
    ],
    "strings": [
        ("String algorithms", "https://cp-algorithms.com/string/string-hashing.html", "cp_algorithms", 1, "String algorithms turn repeated comparisons into indexed, hashed, or stateful scans."),
    ],
    "hash_map": [
        ("Hashing data structure", "https://www.geeksforgeeks.org/dsa/hashing-data-structure/", "geeksforgeeks", 3, "Hashing remembers membership, counts, or indices so repeated searches become constant-time lookups on average."),
        ("Hash table implementations", "https://github.com/TheAlgorithms/Python/tree/master/data_structures/hashing", "the_algorithms", 1, "Reference implementations show how keys map to stored state and how collisions are handled."),
    ],
    "two_pointers": [
        ("Two pointers technique", "https://www.geeksforgeeks.org/dsa/two-pointers-technique/", "geeksforgeeks", 3, "Two pointers coordinate positions so each movement discards work that never needs to be revisited."),
    ],
    "sliding_window": [
        ("Sliding window technique", "https://www.geeksforgeeks.org/window-sliding-technique/", "geeksforgeeks", 3, "A sliding window reuses state from the previous contiguous range instead of recomputing it."),
    ],
    "prefix_sum": [
        ("Prefix sum technique", "https://www.geeksforgeeks.org/dsa/prefix-sum-array-implementation-applications-competitive-programming/", "geeksforgeeks", 3, "Prefix sums precompute cumulative state so range queries become differences of two stored values."),
    ],
    "binary_search": [
        ("Binary search on sorted and monotonic spaces", "https://cp-algorithms.com/num_methods/binary_search.html", "cp_algorithms", 1, "Binary search maintains a true/false boundary and discards half of a monotonic search space each step."),
    ],
    "sorting": [
        ("Sorting algorithms", "https://www.geeksforgeeks.org/dsa/sorting-algorithms/", "geeksforgeeks", 3, "Sorting exposes order so later scans, grouping, or greedy choices become simpler."),
    ],
    "greedy": [
        ("Greedy algorithms", "https://www.geeksforgeeks.org/dsa/greedy-algorithms/", "geeksforgeeks", 3, "A greedy proof connects a locally best safe choice to an optimal remaining subproblem."),
    ],
    "dynamic_programming": [
        ("Introduction to dynamic programming", "https://cp-algorithms.com/dynamic_programming/intro-to-dp.html", "cp_algorithms", 1, "Dynamic programming defines reusable states, transitions, base cases, and an evaluation order."),
    ],
    "graph_bfs": [
        ("Breadth-first search", "https://cp-algorithms.com/graph/breadth-first-search.html", "cp_algorithms", 1, "BFS uses a queue to visit an unweighted graph in nondecreasing distance layers."),
    ],
    "graph_dfs": [
        ("Depth-first search", "https://cp-algorithms.com/graph/depth-first-search.html", "cp_algorithms", 1, "DFS follows one branch completely while preserving return state for traversal and component reasoning."),
    ],
    "dijkstra": [
        ("Dijkstra shortest paths", "https://cp-algorithms.com/graph/dijkstra_sparse.html", "cp_algorithms", 1, "Dijkstra repeatedly finalizes the smallest tentative nonnegative distance using a priority queue."),
    ],
    "union_find": [
        ("Disjoint set union", "https://cp-algorithms.com/data_structures/disjoint_set_union.html", "cp_algorithms", 1, "Union-find tracks component representatives with path compression and union by rank or size."),
    ],
    "tree_traversal": [
        ("Tree traversal techniques", "https://www.geeksforgeeks.org/dsa/tree-traversals-inorder-preorder-and-postorder/", "geeksforgeeks", 3, "Traversal order determines when a node is processed relative to its subtrees."),
    ],
    "recursion": [
        ("Recursion and recursive state", "https://www.geeksforgeeks.org/dsa/recursion-algorithms/", "geeksforgeeks", 3, "Recursion solves a smaller instance, defines a base case, and combines the returned result."),
    ],
    "backtracking": [
        ("Backtracking algorithms", "https://www.geeksforgeeks.org/dsa/backtracking-algorithms/", "geeksforgeeks", 3, "Backtracking chooses, explores, and undoes state while pruning branches that cannot succeed."),
    ],
    "heap": [
        ("Heap data structure", "https://www.geeksforgeeks.org/dsa/heap-data-structure/", "geeksforgeeks", 3, "A heap maintains the next minimum or maximum candidate while updates remain logarithmic."),
    ],
    "stack": [
        ("Stack data structure", "https://www.geeksforgeeks.org/dsa/stack-data-structure/", "geeksforgeeks", 3, "A stack preserves unresolved work in last-in-first-out order."),
        ("Balanced parentheses with a stack", "https://www.geeksforgeeks.org/dsa/check-for-balanced-parentheses-in-an-expression/", "geeksforgeeks", 3, "Bracket matching pushes openings and resolves each closing bracket against the latest unmatched opening."),
    ],
    "queue": [
        ("Queue data structure", "https://www.geeksforgeeks.org/dsa/queue-data-structure/", "geeksforgeeks", 3, "A queue processes discovered work in first-in-first-out order."),
    ],
    "monotonic_stack": [
        ("Monotonic stack pattern", "https://www.geeksforgeeks.org/dsa/how-to-identify-and-solve-monotonic-stack-problems/", "geeksforgeeks", 3, "A monotonic stack discards dominated candidates while preserving the next useful boundary."),
    ],
    "intervals": [
        ("Merging overlapping intervals", "https://www.geeksforgeeks.org/dsa/merging-intervals/", "geeksforgeeks", 3, "Sorting intervals by start exposes overlaps that can be merged in one scan."),
    ],
    "bit_manipulation": [
        ("Bit manipulation", "https://cp-algorithms.com/algebra/bit-manipulation.html", "cp_algorithms", 1, "Bit operations encode compact state and exploit binary identities for constant-time updates."),
    ],
}


def _source_name_for_url(url: str) -> str:
    if "geeksforgeeks" in url:
        return "geeksforgeeks"
    if "github.com" in url:
        return "the_algorithms"
    if "cp-algorithms.com" in url:
        return "cp_algorithms"
    return "generic_web"


def _source_from_parts(title: str, url: str, source_name: str, tier: int, text: str, method: str) -> RetrievedSource:
    stored_text, cache_allowed = apply_storage_limit(source_name, text)
    return RetrievedSource(title, url, source_name, tier, stored_text, method, cache_allowed)


def _candidate_sources_for_patterns(patterns: list[str]) -> list[RetrievedSource]:
    candidates: list[RetrievedSource] = []
    normalized_patterns = list(dict.fromkeys(pattern.strip().lower() for pattern in patterns if pattern.strip()))[:4]
    for pattern in normalized_patterns:
        entries = PATTERN_SOURCES.get(pattern)
        if not entries:
            continue
        for title, url, source_name, tier, text in entries:
            candidates.append(_source_from_parts(title, url, source_name, tier, text, "curated_algorithm_pattern"))
    if candidates:
        return candidates
    return [
        _source_from_parts(
            "Algorithm design and analysis",
            "https://www.geeksforgeeks.org/dsa/fundamentals-of-algorithms/",
            "geeksforgeeks",
            3,
            "Algorithm design connects constraints to a data structure, invariant, state update, and complexity target.",
            "curated_algorithm_fallback",
        )
    ]


def _fetch_source(source: RetrievedSource) -> RetrievedSource:
    if not get_policy(source.source_name).allow_discovery:
        logger.warning("Source fetch denied by compliance policy source=%s", source.source_name)
        return source
    try:
        response = httpx.get(source.url, timeout=8.0, follow_redirects=True, headers={"user-agent": "StudyBuddyBot/0.2"})
        response.raise_for_status()
    except Exception as exc:
        logger.warning("Source fetch failed url=%s error=%s", source.url, exc)
        return source

    extracted = trafilatura.extract(response.text, include_tables=True, include_comments=False) or ""
    if not extracted.strip():
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "noscript", "nav", "footer"]):
            tag.decompose()
        extracted = soup.get_text("\n")
    text = "\n".join(line.strip() for line in extracted.splitlines() if line.strip())
    if not text:
        return source
    stored_text, cache_allowed = apply_storage_limit(source.source_name, text)
    return RetrievedSource(
        title=source.title,
        url=source.url,
        source_name=source.source_name,
        source_tier=source.source_tier,
        text=stored_text,
        retrieval_method=f"{source.retrieval_method}+fetched",
        is_cache_allowed=cache_allowed,
        license_note="Fetched and stored according to source policy.",
    )


def is_algorithm_source(source: RetrievedSource) -> bool:
    lowered = f"{source.title} {source.url} {source.text[:500]}".lower()
    excluded = ("docs.python.org", "docs.oracle.com", "python documentation", "java documentation", "api reference")
    if any(token in lowered for token in excluded):
        return False
    signals = ("algorithm", "approach", "pattern", "complexity", "data structure", "search", "traversal", "dynamic programming", "stack", "queue", "hash")
    return any(token in lowered for token in signals)


def retrieve_sources(
    problem_text: str,
    patterns: list[str],
    source_urls: list[str],
    local_sources: list[RetrievedSource] | None = None,
) -> list[RetrievedSource]:
    settings = get_settings()
    logger.info(
        "Retrieving algorithm sources problem_chars=%s pattern_count=%s user_url_count=%s local_count=%s",
        len(problem_text),
        len(patterns),
        len(source_urls),
        len(local_sources or []),
    )
    sources = [source for source in (local_sources or []) if is_algorithm_source(source)]
    for url in source_urls:
        source_name = _source_name_for_url(url)
        sources.append(
            _source_from_parts(
                "User-provided algorithm reference",
                url,
                source_name,
                3 if source_name == "geeksforgeeks" else 4,
                f"User-provided coding or algorithm reference: {url}",
                "user_provided_algorithm_url",
            )
        )
    sources.extend(_candidate_sources_for_patterns(patterns))

    unique = list({source.url: source for source in sources}.values())
    target_count = min(settings.max_sources_per_job, max(3, min(6, len(unique))))
    selected = [
        _fetch_source(source)
        if "+fetched" not in source.retrieval_method
        and not source.retrieval_method.startswith(("local_rag", "legacy_job_rag", "knowledge_corpus"))
        else source
        for source in unique[:target_count]
    ]
    logger.info("Algorithm sources selected unique=%s final=%s urls=%s", len(unique), len(selected), [source.url for source in selected])
    return selected
