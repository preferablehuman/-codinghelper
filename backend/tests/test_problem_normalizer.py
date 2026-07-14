from app.rag.problem_normalizer import normalize_problem


def test_formatting_only_changes_share_hash():
    left = normalize_problem("# Two Sum\n\nInput Format:\nA sorted array nums\nOutput:\nReturn indices")
    right = normalize_problem("Two Sum\r\nInput:   \r\nA sorted array nums\r\nOutput Format:\r\nReturn indices")
    assert left.statement_hash == right.statement_hash


def test_semantic_change_changes_hash():
    indices = normalize_problem("Two Sum\nInput: array nums\nOutput: return indices")
    values = normalize_problem("Two Sum\nInput: array nums\nOutput: return values")
    assert indices.statement_hash != values.statement_hash


def test_platform_navigation_removed_but_constraints_preserved():
    result = normalize_problem("Sign In\n# Search\nConstraints:\n1 <= n <= 10^5\nSubmissions")
    assert "Sign In" not in result.normalized_text
    assert "1 <= n <= 10^5" in result.normalized_text
