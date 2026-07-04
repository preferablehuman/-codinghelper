from dataclasses import dataclass


@dataclass(frozen=True)
class SourceCompliancePolicy:
    source_name: str
    allow_fetch: bool
    allow_cache_full_text: bool
    allow_cache_snippets: bool
    max_chars_to_store: int
    require_user_provided_url: bool


POLICIES = {
    "cp_algorithms": SourceCompliancePolicy("cp_algorithms", True, True, True, 12000, False),
    "official_docs": SourceCompliancePolicy("official_docs", True, True, True, 12000, False),
    "the_algorithms": SourceCompliancePolicy("the_algorithms", True, True, True, 12000, False),
    "stack_exchange": SourceCompliancePolicy("stack_exchange", True, False, True, 2000, False),
    "codeforces": SourceCompliancePolicy("codeforces", True, False, True, 2000, False),
    "geeksforgeeks": SourceCompliancePolicy("geeksforgeeks", True, False, True, 1500, False),
    "generic_web": SourceCompliancePolicy("generic_web", True, False, True, 1200, True),
}


def get_policy(source_name: str) -> SourceCompliancePolicy:
    return POLICIES.get(source_name, POLICIES["generic_web"])


def apply_storage_limit(source_name: str, text: str) -> tuple[str, bool]:
    policy = get_policy(source_name)
    if policy.allow_cache_full_text:
        return text[: policy.max_chars_to_store], True
    if policy.allow_cache_snippets:
        return text[: policy.max_chars_to_store], False
    return "", False
