def problem_analysis_prompt(problem_text: str, language: str, heuristic_patterns: list[str]) -> str:
    return f"""Analyze this programming problem for a local study assistant.

Return only one valid JSON object with:
- summary: concise string
- selected_pattern: one string using snake_case
- candidate_patterns: array of 2 to 6 snake_case strings
- edge_cases: array of specific edge-case strings
- objective: concise string
- input_entities: array of strings
- output_requirement: string
- constraints: array preserving numeric constraints
- ordering_assumptions: array of strings
- uniqueness_assumptions: array of strings
- value_domain: array of strings
- graph_properties: array of strings
- optimization_target: string
- io_contract: object describing stdin and stdout
- semantic_flags: object with nullable booleans for input_sorted, duplicates_allowed, negative_values_allowed, directed_graph, weighted_graph, negative_weights_allowed, return_indices, return_values, in_place_required, multiple_valid_outputs, modulo_required, contiguous_required, subsequence_allowed

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
- algorithm_pattern must be a concise algorithm or data-structure name, not a paragraph.
- time_complexity must contain the Big-O expression followed by at most one concise explanatory sentence.
- space_complexity must contain the Big-O expression followed by at most one concise explanatory sentence.

Problem:
{problem_text}

Language:
{language}

Detected algorithm pattern:
{pattern}

Evidence pack:
{evidence}
"""


def adapt_verified_solution_prompt(problem_text: str, target_language: str, canonical: dict[str, object], tests: list[dict[str, object]]) -> str:
    return f"""Adapt a retrieved canonical solution to {target_language}.

The canonical algorithm has already been retrieved and verified against the listed tests.
Do not replace it unless the supplied verification data identifies a defect.
Adapt only the language and stdin/stdout wrapper required by the incoming problem.

Return one JSON object with: approach_type, algorithm_pattern, explanation, pseudocode, code, time_complexity, space_complexity.
The code must be a complete standalone stdin/stdout program.

Incoming problem:
{problem_text}

Verified canonical solution:
{canonical}

Reusable tests:
{tests}
"""


def problem_equivalence_prompt(incoming: dict[str, object], canonical: dict[str, object]) -> str:
    return f"""Judge whether two programming-problem signatures describe the same executable task.
Return one JSON object with relation (EXACT, EQUIVALENT, RELATED, or DIFFERENT), confidence (0 to 1), matching_requirements, contradictions, adaptation_required, and reason.
This is advisory. Never ignore deterministic contradictions supplied in either signature.

Incoming signature: {incoming}
Canonical signature: {canonical}
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
- algorithm_pattern must be a concise algorithm or data-structure name, not a paragraph.
- time_complexity must contain the Big-O expression followed by at most one concise explanatory sentence.
- space_complexity must contain the Big-O expression followed by at most one concise explanatory sentence.
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
- algorithm_pattern must be a concise algorithm or data-structure name, not a paragraph.
- time_complexity must contain the Big-O expression followed by at most one concise explanatory sentence.
- space_complexity must contain the Big-O expression followed by at most one concise explanatory sentence.
- explanation must teach a beginner the approach intuition, prerequisite concepts, data structures and their operations, algorithm flow, important state variables, correctness idea, and how this approach differs from earlier approaches.

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
- algorithm_pattern must be a concise algorithm or data-structure name, not a paragraph.
- time_complexity must contain the Big-O expression followed by at most one concise explanatory sentence.
- space_complexity must contain the Big-O expression followed by at most one concise explanatory sentence.
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
- Write for a complete beginner who may not know the problem pattern or data structures yet.
- Keep claims grounded in the problem, solution, and evidence.
- Mention verification status without overstating correctness.
- Be specific about pitfalls.
- This request covers one verified approach. Explain that approach completely; the application will label and combine it with the other verified approaches.
- intuition: explain the problem in plain language, the goal, the main insight, and how a learner could discover the approach.
- brute_force: teach the direct approach from first principles, including its state, decisions, repeated work, and limitations. Then explain what motivates the next approach.
- optimized_approach: for every approach, explain the algorithm flow in execution order, why each step exists, what work it avoids, and how it differs from the other approaches.
- Before using any data structure, explain what it is, which operations are used, what each stored value means, and why it fits this problem. Cover arrays, lists, maps, sets, stacks, queues, heaps, recursion, or other structures actually used by the code.
- Explain recursion and backtracking basics when used: call state, base case, choice, recursive transition, return value, and state restoration.
- Explain important code blocks and variables by name. Connect pseudocode phases to the executable code rather than paraphrasing the code line by line.
- Include a short correctness argument based on an invariant or exhaustive coverage for each approach.
- complexity_analysis: derive time and space costs for each approach, define every symbol used, and distinguish auxiliary memory from output storage.
- pitfalls: organize mistakes by approach and include input parsing, boundary cases, state mutation/restoration, duplicates/order, overflow, and output-format concerns when applicable.
- The dry_run field must include:
  - `### Example being traced`: quote the first complete input/output example from the problem summary or solution context. Never silently replace a supplied example with an invented one.
  - `### Annotated code stub`: give compact pseudocode that mirrors this solution's actual control flow. Number the phases and name the real state variables used by the code.
  - `### State model`: define every variable or data-structure field visible in the trace, its initial value, permitted values, and what changing it means.
  - `### Step-by-step execution`: trace the given example from parsing through final output. Use a Markdown table with columns `Step`, `Code phase`, `Current input`, `State before`, `Condition / decision`, `Action`, `State after`, and `Return / output`.
  - show loop iterations, recursive calls, base cases, pruning, mutations, backtracking/restoration, returned values, and output accumulation whenever the solution uses them.
  - split dense operations into micro-steps; do not jump from input directly to the answer or use phrases such as "continue similarly" for the important branch.
  - after the table, include `### Call and return flow` for recursive solutions or `### Iteration flow` for iterative solutions. Explain how control moves between code phases.
  - include `### Why this step is valid` and connect the main decisions to the invariant or problem rule they preserve.
- Prefer concrete sample values from the original problem. If the supplied context truly contains no example, create the smallest representative input, label it clearly, and explain why it exercises the core logic.
- Do not provide generic dry-run prose. Every row must inspect or change concrete state, and every state change must be consistent with the supplied code.
- Prefer completeness and teaching clarity over brevity. Do not assume prior competitive-programming knowledge.

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


def pattern_lesson_prompt(
    pattern_key: str,
    display_name: str,
    problem_summary: str,
    evidence: list[str],
    source_refs: list[dict[str, object]],
    approaches: list[dict[str, object]],
) -> str:
    return f"""Create a reusable, beginner-first lesson about the algorithm pattern `{pattern_key}`.

Return exactly one JSON object with these string fields:
- display_name
- overview
- mental_model
- recognition_cues
- core_operations
- invariants
- worked_example
- implementation_guide
- complexity_tradeoffs
- pitfalls
- related_patterns
- evidence_summary

Teaching requirements:
- Explain the pattern itself, not only the supplied programming problem.
- Start from first principles and define every data structure before using it.
- Show how a learner recognizes this pattern from constraints, input shape, and repeated-work clues.
- Explain state transitions and the invariant that makes the pattern correct.
- `core_operations` must describe the operations used, their usual costs, and what each stored value means.
- `worked_example` must be a concrete micro-step trace with state before, decision, action, and state after. Use Markdown, including a table when helpful.
- `implementation_guide` must contain language-neutral pseudocode and a checklist for translating it into code.
- `complexity_tradeoffs` must explain best/typical/worst costs when they differ, auxiliary memory, and when another pattern is preferable.
- `pitfalls` must include correctness, boundaries, duplicates, mutation, and performance traps relevant to the pattern.
- `related_patterns` must compare close alternatives and explain how to choose between them.
- Ground claims in the supplied evidence and approaches. Do not cite sources that are not supplied.
- Write a durable lesson that can be reused across future problems using the same normalized pattern.
- Format multi-point content as real Markdown lists with one item per line; never place an entire numbered list on one line.
- Keep Markdown tables on separate lines with a header separator row so the lesson UI can render them accessibly.
- Prefer completeness and clarity over brevity.

Normalized pattern: {pattern_key}
Display name hint: {display_name}
Problem that first motivated this lesson: {problem_summary}
Evidence claims: {evidence}
Approved source references: {source_refs}
Verified solution approaches: {approaches}
"""
