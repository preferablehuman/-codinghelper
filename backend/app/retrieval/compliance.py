from dataclasses import dataclass


@dataclass(frozen=True)
class SourceCompliancePolicy:
    source_name: str
    allow_discovery: bool
    allow_problem_statement_storage: bool
    allow_solution_text_storage: bool
    allow_code_storage: bool
    allow_full_text: bool
    allow_snippets: bool
    require_attribution: bool
    max_chars_to_store: int
    requests_per_minute: int
    robots_or_terms_note: str
    require_user_provided_url: bool = False

    @property
    def allow_fetch(self) -> bool:
        return self.allow_discovery

    @property
    def allow_cache_full_text(self) -> bool:
        return self.allow_full_text

    @property
    def allow_cache_snippets(self) -> bool:
        return self.allow_snippets


def _policy(name: str, *, full: bool, statement: bool = False, solution: bool = False, code: bool = False, chars: int, rpm: int, attribution: bool = True, note: str = "Review source terms before changing this policy.", user_url: bool = False) -> SourceCompliancePolicy:
    return SourceCompliancePolicy(name, True, statement, solution, code, full, True, attribution, chars, rpm, note, user_url)


POLICIES = {
    "cp_algorithms": _policy("cp_algorithms", full=True, solution=True, code=True, chars=12000, rpm=30),
    "official_docs": _policy("official_docs", full=True, chars=12000, rpm=30),
    "the_algorithms": _policy("the_algorithms", full=True, solution=True, code=True, chars=12000, rpm=20, note="Only allowlisted licensed repositories."),
    "stack_exchange": _policy("stack_exchange", full=False, statement=True, solution=False, code=False, chars=2000, rpm=20, note="Use the official API and retain CC attribution."),
    "codeforces": _policy("codeforces", full=False, chars=2000, rpm=10, note="Official API metadata only; do not scrape submissions or editorials."),
    "geeksforgeeks": _policy("geeksforgeeks", full=False, chars=1500, rpm=10, note="Teaching snippets only; no solution/code promotion."),
    "user_url": _policy("user_url", full=False, chars=1200, rpm=10, user_url=True),
    "generic_web": SourceCompliancePolicy("generic_web", False, False, False, False, False, False, True, 0, 0, "Generic automated discovery is disabled.", True),
    "leetcode": SourceCompliancePolicy("leetcode", False, False, False, False, False, False, True, 0, 0, "Automated LeetCode crawling is explicitly denied."),
}

DENIED_SOURCES = {"leetcode", "leetcode.com", "google_search", "bing_search", "arbitrary_github"}


def get_policy(source_name: str) -> SourceCompliancePolicy:
    return POLICIES.get(source_name, POLICIES["generic_web"])


def apply_storage_limit(source_name: str, text: str) -> tuple[str, bool]:
    policy = get_policy(source_name)
    if policy.allow_full_text:
        return text[: policy.max_chars_to_store], True
    if policy.allow_snippets:
        return text[: policy.max_chars_to_store], False
    return "", False
