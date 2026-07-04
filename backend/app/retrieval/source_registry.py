import logging
from dataclasses import dataclass

from app.retrieval.compliance import apply_storage_limit


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


CURATED_PATTERN_SOURCES = {
    "binary_search": (
        "Binary search - CP Algorithms",
        "https://cp-algorithms.com/num_methods/binary_search.html",
        "Binary search applies when the search space is sorted or monotonic. It repeatedly halves the candidate range and checks a predicate.",
    ),
    "dynamic_programming": (
        "Dynamic Programming - The Algorithms",
        "https://github.com/TheAlgorithms",
        "Dynamic programming stores answers for overlapping subproblems and builds larger answers from smaller states.",
    ),
    "graph_bfs": (
        "Breadth First Search - CP Algorithms",
        "https://cp-algorithms.com/graph/breadth-first-search.html",
        "Breadth first search explores vertices in increasing distance order for unweighted graphs.",
    ),
    "sliding_window": (
        "Sliding window technique overview",
        "https://www.geeksforgeeks.org/window-sliding-technique/",
        "Sliding window maintains a contiguous range and updates state as the range expands or shrinks.",
    ),
    "hash_map": (
        "Hash table based lookup",
        "https://github.com/TheAlgorithms/Python",
        "Hash maps support near constant-time lookup and are commonly used to remember values, counts, or indices.",
    ),
    "two_pointers": (
        "Two pointers pattern examples - The Algorithms",
        "https://github.com/TheAlgorithms/Python",
        "Two pointers keep two positions moving through a sequence to avoid checking every pair.",
    ),
    "stack": (
        "Stack data structure - CP Algorithms",
        "https://cp-algorithms.com/data_structures/stack_queue_modification.html",
        "Stack-based algorithms track nested, previous, or monotonic state with last-in-first-out behavior.",
    ),
    "heap": (
        "Priority queues and heaps - CP Algorithms",
        "https://cp-algorithms.com/data_structures/stack_queue_modification.html",
        "Priority queues help repeatedly select the minimum or maximum available candidate.",
    ),
}

GENERAL_KNOWLEDGE_SOURCES = [
    (
        "CP-Algorithms",
        "https://cp-algorithms.com/",
        "cp_algorithms",
        1,
        "Open algorithm explanations for competitive programming and data structures.",
    ),
    (
        "The Algorithms",
        "https://github.com/TheAlgorithms",
        "the_algorithms",
        1,
        "Open-source reference implementations across languages.",
    ),
    (
        "Python documentation",
        "https://docs.python.org/3/",
        "official_docs",
        1,
        "Official Python language and standard library reference.",
    ),
    (
        "Java documentation",
        "https://docs.oracle.com/en/java/",
        "official_docs",
        1,
        "Official Java language and platform documentation.",
    ),
]


def _source_name_for_url(url: str) -> str:
    if "geeksforgeeks" in url:
        return "geeksforgeeks"
    if "github.com" in url:
        return "the_algorithms"
    if "docs.python.org" in url or "docs.oracle.com" in url:
        return "official_docs"
    if "cp-algorithms.com" in url:
        return "cp_algorithms"
    return "generic_web"


def _source_from_parts(title: str, url: str, source_name: str, tier: int, text: str, method: str) -> RetrievedSource:
    stored_text, cache_allowed = apply_storage_limit(source_name, text)
    return RetrievedSource(title, url, source_name, tier, stored_text, method, cache_allowed)


def _seed_source_for_pattern(pattern: str) -> RetrievedSource:
    title, url, text = CURATED_PATTERN_SOURCES.get(
        pattern,
        (
            "Algorithm reference seed",
            "https://cp-algorithms.com/",
            "Choose an algorithmic pattern from constraints, input shape, and required complexity, then verify with edge cases.",
        ),
    )
    source_name = "geeksforgeeks" if "geeksforgeeks" in url else ("the_algorithms" if "github.com" in url else "cp_algorithms")
    tier = 3 if source_name == "geeksforgeeks" else 1
    return _source_from_parts(title, url, source_name, tier, text, "curated_pattern_reference")


def _general_sources() -> list[RetrievedSource]:
    return [
        _source_from_parts(title, url, source_name, tier, text, "curated_knowledge_base")
        for title, url, source_name, tier, text in GENERAL_KNOWLEDGE_SOURCES
    ]


def retrieve_sources(problem_text: str, patterns: list[str], source_urls: list[str]) -> list[RetrievedSource]:
    logger.info(
        "Retrieving sources problem_chars=%s pattern_count=%s user_url_count=%s",
        len(problem_text),
        len(patterns),
        len(source_urls),
    )
    sources: list[RetrievedSource] = []
    for url in source_urls:
        title = "User provided source"
        source_name = _source_name_for_url(url)
        stored_text, cache_allowed = apply_storage_limit(source_name, f"User provided source for this problem: {url}")
        sources.append(
            RetrievedSource(
                title=title,
                url=url,
                source_name=source_name,
                source_tier=3 if source_name == "geeksforgeeks" else 4,
                text=stored_text,
                retrieval_method="user_provided_url",
                is_cache_allowed=cache_allowed,
                license_note="Stored conservatively according to source policy.",
            )
        )

    sources.extend(_general_sources())

    for pattern in patterns[:4]:
        sources.append(_seed_source_for_pattern(pattern))

    unique: dict[str, RetrievedSource] = {}
    for source in sources:
        unique[source.url] = source
    result = list(unique.values())
    logger.info(
        "Sources selected total=%s unique=%s names=%s",
        len(sources),
        len(result),
        sorted({source.source_name for source in result}),
    )
    return result
