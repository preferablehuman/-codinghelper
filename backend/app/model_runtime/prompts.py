def problem_analysis_prompt(problem_text: str, language: str, heuristic_patterns: list[str]) -> str:
    return f"""Analyze this programming problem for a local study assistant.

Return only one valid JSON object with:
- summary: concise string
- selected_pattern: one string using snake_case
- candidate_patterns: array of 2 to 6 snake_case strings
- edge_cases: array of specific edge-case strings

Prefer these pattern names when applicable:
arrays, strings, hash_map, two_pointers, sliding_window, prefix_sum, binary_search, sorting, greedy, dynamic_programming, graph_bfs, graph_dfs, dijkstra, union_find, tree_traversal, recursion, backtracking, heap, stack, queue, monotonic_stack, intervals, bit_manipulation

Language:
{language}

Heuristic pattern hints:
{heuristic_patterns}

Problem:
{problem_text}
"""


def solution_prompt(problem_text: str, language: str, pattern: str, evidence: str) -> str:
    return f"""You are generating a programming-problem solution for a local study assistant.

Return only one valid JSON object with these string fields:
- approach_type
- algorithm_pattern
- explanation
- pseudocode
- code
- time_complexity
- space_complexity

Rules:
- The final code must be complete and executable as a standalone {language} program.
- Use stdin/stdout for execution tests. If the problem statement is from an online judge and does not define stdin explicitly, read the stated function arguments from stdin in the simplest natural format. For example, if the input is a single string `s`, read one line/string and print the returned string.
- Do not hard-code sample calls in `main`; `main` must read stdin and print exactly one answer.
- Do not use external libraries beyond the language standard library.
- Do not invent unsupported source claims.
- Use the evidence only as grounding; solve the actual problem statement.
- Set approach_type to "FINAL".

Problem:
{problem_text}

Language:
{language}

Detected algorithm pattern:
{pattern}

Evidence pack:
{evidence}
"""


def tests_prompt(problem_text: str, language: str, solution: dict[str, str]) -> str:
    return f"""Generate execution tests for this programming problem and solution.

Return only one valid JSON array. Each item must be an object with:
- input: string
- expected_output: string or null
- test_type: one of "SAMPLE", "EDGE", "GENERATED", "RANDOM"

Rules:
- Use the normalized stdin/stdout format expected by the solution.
- If the problem has no explicit stdin format, use the simple format implemented by the standalone solution, such as one raw line for a single string argument.
- Include samples if the problem statement contains them.
- Include edge cases relevant to the constraints.
- Keep the total number of tests between 3 and 8.
- expected_output must match exactly, except when multiple valid outputs make a single expected output unsafe; in that case use null.

Problem:
{problem_text}

Language:
{language}

Solution explanation:
{solution["explanation"]}

Solution code:
{solution["code"]}
"""


def repair_prompt(
    problem_text: str,
    language: str,
    evidence: str,
    solution: dict[str, str],
    tests: list[dict[str, str | None]],
    verification: dict[str, object],
) -> str:
    return f"""Repair this programming-problem solution after sandbox verification.

Return only one valid JSON object with these string fields:
- approach_type
- algorithm_pattern
- explanation
- pseudocode
- code
- time_complexity
- space_complexity

Rules:
- The repaired code must be a complete standalone {language} program.
- Keep stdin/stdout behavior compatible with the tests.
- Do not hard-code sample calls in `main`; `main` must read stdin and print exactly one answer.
- Use only the language standard library.
- Fix the observed compile/runtime/wrong-answer issue.
- Do not invent unsupported source claims.
- Set approach_type to "FINAL".

Problem:
{problem_text}

Language:
{language}

Evidence:
{evidence}

Previous solution:
{solution}

Tests:
{tests}

Verification result:
{verification}
"""


def explanation_prompt(problem_summary: str, pattern: str, solution: dict[str, str], evidence: str, verification: dict[str, object]) -> str:
    return f"""Generate a structured explanation for a programming-problem solution.

Return only one valid JSON object with these string fields:
- intuition
- brute_force
- optimized_approach
- dry_run
- pitfalls
- complexity_analysis

Rules:
- Explain in a way suitable for a learner.
- Keep claims grounded in the problem, solution, and evidence.
- Mention verification status without overstating correctness.
- Be specific about pitfalls.

Problem summary:
{problem_summary}

Detected pattern:
{pattern}

Evidence:
{evidence}

Verification:
{verification}

Solution:
{solution}
"""


def slide_markdown_prompt(
    title: str,
    problem_summary: str,
    pattern: str,
    solution: dict[str, str],
    explanation: dict[str, str],
    sources: list[dict[str, str]],
) -> str:
    return f"""Generate a concise learner-focused Markdown deck for this programming explanation.

Return only Markdown, not JSON and not commentary.

Required slides, in this exact order:
1. What Are We Solving?
2. Core Observation
3. Algorithm Plan
4. Step-by-Step Dry Run
5. Code Walkthrough
6. Complexity, Tests, and Pitfalls

Rules:
- Use Markdown slide separators (`---`).
- Keep each slide focused with 3 to 5 learner-friendly bullets.
- Include a compact markdown table on the dry-run slide.
- Include concise pseudocode or a short code excerpt on the code walkthrough slide.
- Prefer simple diagrams described as short flow lines such as `input -> state -> decision -> output`.
- Do not include HTML, theme config, presenter notes, or long source listings.

Title:
{title}

Problem summary:
{problem_summary}

Pattern:
{pattern}

Solution:
{solution}

Explanation:
{explanation}

Sources:
{sources}
"""
