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


def solution_variants_prompt(problem_text: str, language: str, pattern: str, evidence: str) -> str:
    return f"""You are generating a learning ladder of programming-problem solutions for a modern coding assistant.

Return only one valid JSON object with this shape:
{{
  "approaches": [
    {{
      "approach_type": "BRUTE_FORCE",
      "algorithm_pattern": "string",
      "explanation": "string",
      "pseudocode": "string",
      "code": "string",
      "time_complexity": "string",
      "space_complexity": "string"
    }},
    {{
      "approach_type": "IMPROVED",
      "algorithm_pattern": "string",
      "explanation": "string",
      "pseudocode": "string",
      "code": "string",
      "time_complexity": "string",
      "space_complexity": "string"
    }},
    {{
      "approach_type": "OPTIMAL",
      "algorithm_pattern": "string",
      "explanation": "string",
      "pseudocode": "string",
      "code": "string",
      "time_complexity": "string",
      "space_complexity": "string"
    }}
  ]
}}

Rules:
- Generate at least two approaches: BRUTE_FORCE and OPTIMAL.
- Generate IMPROVED only when it is meaningfully different from both brute force and optimal in algorithm, data structure, or complexity.
- Do not create filler variants. If two approaches would have essentially the same code and complexity, keep only the clearer one.
- Each approach must explain why it improves or differs from the previous one.
- Each code field must be complete and executable as a standalone {language} program.
- Use stdin/stdout for execution tests. If the problem statement is from an online judge and does not define stdin explicitly, read the stated function arguments from stdin in the simplest natural format. For example, if the input is a single string `s`, read one line/string and print the returned string.
- Do not hard-code sample calls in `main`; `main` must read stdin and print exactly one answer.
- Do not use external libraries beyond the language standard library.
- Do not invent unsupported source claims.
- Use the evidence only as grounding; solve the actual problem statement.
- The OPTIMAL approach should be the expected interview/competitive-programming solution.

Problem:
{problem_text}

Language:
{language}

Detected algorithm pattern:
{pattern}

Evidence pack:
{evidence}
"""


def solution_variant_prompt(
    problem_text: str,
    language: str,
    pattern: str,
    evidence: str,
    approach_type: str,
    previous_approaches: list[dict[str, str]],
) -> str:
    previous_summary = "None yet."
    if previous_approaches:
        previous_summary = "\n\n".join(
            "\n".join(
                [
                    f"{item['approach_type']} ({item['algorithm_pattern']}):",
                    f"Pseudocode: {item['pseudocode']}",
                    f"Complexity: {item['time_complexity']} time, {item['space_complexity']} space.",
                ]
            )
            for item in previous_approaches
        )
    approach_guidance = {
        "BRUTE_FORCE": "Use the clearest genuinely naive or direct exhaustive strategy. Prioritize teaching value over efficiency.",
        "IMPROVED": "Use a meaningful intermediate strategy. It must differ from the listed approaches in algorithm, data structure, or complexity; otherwise return the same algorithm only if no honest intermediate exists.",
        "OPTIMAL": "Use the expected interview or competitive-programming solution and explicitly explain why it improves on the listed approaches.",
    }.get(approach_type, "Use a meaningfully distinct strategy.")
    return f"""Generate exactly one {approach_type} solution for a programming-problem learning ladder.

Return only one valid JSON object with these string fields:
- approach_type
- algorithm_pattern
- explanation
- pseudocode
- code
- time_complexity
- space_complexity

Approach requirement:
- Set approach_type to "{approach_type}".
- {approach_guidance}
- Similar intuition or the same high-level goal is acceptable when the algorithm, data structure, state representation, or control flow is genuinely different.
- Do not disguise the same implementation with renamed variables, reordered helpers, or different prose.
- Do not return an array or multiple solutions.

Code requirements:
- The code must be complete and executable as a standalone {language} program.
- Use stdin/stdout. If the problem omits stdin details, use the simplest natural format for the stated function arguments.
- Do not hard-code sample calls in main; read stdin and print exactly one answer.
- Use only the language standard library.
- Solve the actual problem and do not invent unsupported source claims.

Earlier approaches in this ladder:
{previous_summary}

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
- Recommended minimum: generate at least 10 meaningful tests when the problem has enough input variety.
- There is no maximum limit; add enough tests to make the proof convincing without duplicates.
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


def explanation_prompt(problem_summary: str, pattern: str, solution: dict[str, object], evidence: str, verification: dict[str, object]) -> str:
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
- Explain the buildup from brute force to improved to optimal when `approach_ladder` is available.
- The dry_run field must include:
  - one section for each available approach using headings like `## BRUTE_FORCE` and `## OPTIMAL`,
  - a compact code-logic stub or pseudocode trace for that approach,
  - a GeeksforGeeks-style illustration table with columns: Step, Input/Char, Stack/State, Action, Result,
  - how key variables/state change after each step,
  - the exact point where the algorithm makes its main decision.
- Prefer concrete sample values from the problem statement. If no sample is provided, create a small representative input and label it as representative.
- Do not provide generic dry-run text; every step must change or inspect real state.

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


def slide_deck_prompt(
    title: str,
    problem_summary: str,
    pattern: str,
    solution: dict[str, object],
    explanation: dict[str, str],
    sources: list[dict[str, str]],
) -> str:
    return f"""Design a complete teaching deck for a learner who has never seen this problem or algorithm.

Return only one valid JSON object with this shape:
{{
  "deck_title": "string",
  "audience": "beginner programming learner",
  "learning_objective": "what the learner can explain or execute after the deck",
  "slides": [
    {{
      "kind": "title|problem|observation|comparison|approach|state|dry_run|code|correctness|verification|summary|references",
      "title": "takeaway-style title",
      "takeaway": "one sentence that states the slide's main point",
      "bullets": ["0 to 5 concise supporting points"],
      "flow": ["2 to 5 ordered state or decision labels"],
      "code": "short relevant pseudocode or code excerpt, otherwise empty",
      "table": {{"headers": ["header"], "rows": [["cell"]]}},
      "notes": "optional detailed teaching explanation"
    }}
  ]
}}

Narrative requirements:
- Create 12 to 16 slides following a cumulative learning progression.
- Open with a minimal title slide, then explain the problem in plain language and translate constraints into algorithm observations.
- Compare every genuinely distinct BRUTE_FORCE, IMPROVED, and OPTIMAL approach from Solution. Give each approach its own slide and explain what state it stores, what work it avoids, and why it improves.
- Include one full comparison slide with approach, core idea, time, space, strength, and limitation.
- Include one state/data-structure slide that visually describes what each stored value means.
- Include at least two concrete dry-run slides. Use real sample values and tables with Step, Input or Cell, State Before, Decision, State After, and Result.
- Include at least two code slides: first map pseudocode to phases, then trace the most important executable code lines. Keep each excerpt under 18 lines.
- Include a correctness slide centered on the invariant and why all invalid/valid cases are covered.
- Include verification with generated test categories, pass/fail counts, complexity, and pitfalls.
- Close with a synthesis slide that teaches when to recognize and reuse this pattern, followed by a short references slide containing only relevant algorithm/code-intuition sources.

Writing and layout requirements:
- Each slide has exactly one teaching job and a takeaway-style title.
- Use concrete state changes and decisions, not generic claims such as "this is efficient".
- Keep visible bullets concise; place deeper explanation in notes.
- Use flow only for ordered processes. Use table only when row/column comparison materially teaches the idea.
- Do not repeat the same bullet across slides. Do not expose prompt or production instructions.
- Never fabricate sample values, code behavior, complexity, or verification results; derive them from the supplied problem, solution, explanation, and sources.

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
