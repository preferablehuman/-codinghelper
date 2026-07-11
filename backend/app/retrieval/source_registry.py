import logging
from dataclasses import dataclass

import httpx
import trafilatura
from bs4 import BeautifulSoup

from app.config import get_settings
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
        "Valid Parentheses in an Expression - GeeksforGeeks",
        "https://www.geeksforgeeks.org/dsa/check-for-balanced-parentheses-in-an-expression/",
        "Stack-based bracket matching pushes openings, checks each closing bracket against the stack top, and finishes balanced only when the stack is empty.",
    ),
    "heap": (
        "Priority queues and heaps - CP Algorithms",
        "https://cp-algorithms.com/data_structures/stack_queue_modification.html",
        "Priority queues help repeatedly select the minimum or maximum available candidate.",
    ),
}

PATTERN_SOURCE_CANDIDATES = {
    "stack": [
        (
            "Valid Parentheses in an Expression - GeeksforGeeks",
            "https://www.geeksforgeeks.org/dsa/check-for-balanced-parentheses-in-an-expression/",
            "geeksforgeeks",
            3,
            "Stack illustration for balanced parentheses with approach comparison and step-by-step explanation.",
        ),
        (
            "Stack data structure - CP Algorithms",
            "https://cp-algorithms.com/data_structures/stack_queue_modification.html",
            "cp_algorithms",
            1,
            "Stack-based algorithms track nested, previous, or monotonic state with last-in-first-out behavior.",
        ),
    ],
    "strings": [
        (
            "String algorithms - CP Algorithms",
            "https://cp-algorithms.com/string/string-hashing.html",
            "cp_algorithms",
            1,
            "String processing problems often rely on scans, matching, hashing, and careful boundary handling.",
        ),
        (
            "Java String documentation",
            "https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/lang/String.html",
            "official_docs",
            1,
            "Official Java String behavior and methods for parsing and scanning text.",
        ),
    ],
    "hash_map": [
        (
            "Hash table based lookup",
            "https://github.com/TheAlgorithms/Python",
            "the_algorithms",
            1,
            "Hash maps support near constant-time lookup and are commonly used to remember values, counts, or indices.",
        ),
        (
            "Java HashMap documentation",
            "https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/util/HashMap.html",
            "official_docs",
            1,
            "Official Java HashMap behavior, lookup, and update semantics.",
        ),
    ],
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


def _source_from_parts(
    title: str,
    url: str,
    source_name: str,
    tier: int,
    text: str,
    method: str,
    license_note: str | None = None,
) -> RetrievedSource:
    stored_text, cache_allowed = apply_storage_limit(source_name, text)
    return RetrievedSource(title, url, source_name, tier, stored_text, method, cache_allowed, license_note)


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


def _candidate_sources_for_patterns(patterns: list[str]) -> list[RetrievedSource]:
    candidates: list[RetrievedSource] = []
    for pattern in patterns[:5]:
        for title, url, source_name, tier, text in PATTERN_SOURCE_CANDIDATES.get(pattern, []):
            candidates.append(_source_from_parts(title, url, source_name, tier, text, "curated_pattern_candidate"))
        candidates.append(_seed_source_for_pattern(pattern))
    return candidates


def _fetch_source(source: RetrievedSource) -> RetrievedSource:
    try:
        response = httpx.get(source.url, timeout=6.0, follow_redirects=True, headers={"user-agent": "StudyBuddyBot/0.1"})
        response.raise_for_status()
    except Exception as exc:
        logger.warning("Source fetch failed url=%s error=%s", source.url, exc)
        return source

    extracted = trafilatura.extract(response.text, include_tables=True, include_comments=False) or ""
    if not extracted.strip():
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
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


def retrieve_sources(
    problem_text: str,
    patterns: list[str],
    source_urls: list[str],
    local_sources: list[RetrievedSource] | None = None,
) -> list[RetrievedSource]:
    settings = get_settings()
    logger.info(
        "Retrieving sources problem_chars=%s pattern_count=%s user_url_count=%s local_count=%s",
        len(problem_text),
        len(patterns),
        len(source_urls),
        len(local_sources or []),
    )
    sources: list[RetrievedSource] = list(local_sources or [])
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
    sources.extend(_candidate_sources_for_patterns(patterns))

    unique: dict[str, RetrievedSource] = {}
    for source in sources:
        unique[source.url] = source
    ordered = list(unique.values())
    fetched: list[RetrievedSource] = []
    local_count = len(local_sources or [])
    target_count = min(settings.max_sources_per_job, max(6, local_count + 4))
    for source in ordered:
        if len(fetched) >= target_count:
            break
        should_fetch = "+fetched" not in source.retrieval_method and source.retrieval_method != "local_rag_reuse"
        fetched.append(_fetch_source(source) if should_fetch else source)
    logger.info(
        "Sources selected total=%s unique=%s final=%s names=%s",
        len(sources),
        len(ordered),
        len(fetched),
        sorted({source.source_name for source in fetched}),
    )
    return fetched
