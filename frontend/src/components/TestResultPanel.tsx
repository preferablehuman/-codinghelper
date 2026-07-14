import { Play } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { executeCode } from "../api/client";
import type { ExecutionResponse, ExecutionResultItem, GeneratedSolution, TestCase, VerificationRun } from "../types/api";

const APPROACH_ORDER: Record<string, number> = {
  BRUTE_FORCE: 0,
  NAIVE: 0,
  IMPROVED: 1,
  AVERAGE: 1,
  OPTIMAL: 2,
  EXPECTED: 2,
  FINAL: 3,
  REPAIRED: 4
};

export default function TestResultPanel({
  tests,
  verificationRuns,
  solutions = [],
  language
}: {
  tests: TestCase[];
  verificationRuns: VerificationRun[];
  solutions?: GeneratedSolution[];
  language: string;
}) {
  const orderedSolutions = useMemo(() => orderSolutions(solutions), [solutions]);
  const preferred = useMemo(() => preferredSolution(orderedSolutions), [orderedSolutions]);
  const [selectedSolutionId, setSelectedSolutionId] = useState<string | null>(preferred?.id ?? null);
  const solution = orderedSolutions.find((candidate) => candidate.id === selectedSolutionId) ?? preferred;
  const latest = verificationRuns.filter((run) => run.solution_id === solution?.id).at(-1);
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [runResult, setRunResult] = useState<ExecutionResponse | null>(null);
  const recommendedMinimum = 10;
  const hasRecommendedMinimum = tests.length >= recommendedMinimum;

  useEffect(() => {
    if (preferred && !orderedSolutions.some((candidate) => candidate.id === selectedSolutionId)) {
      setSelectedSolutionId(preferred.id);
    }
  }, [orderedSolutions, preferred, selectedSolutionId]);

  useEffect(() => {
    setRunResult(null);
    setRunError(null);
  }, [solution?.id]);

  async function handleRunGeneratedTests() {
    if (!solution) {
      return;
    }
    setRunning(true);
    setRunError(null);
    try {
      setRunResult(
        await executeCode({
          language,
          code: solution.code,
          input: "",
          expected_output: null,
          tests: tests.map((test) => ({ input: test.input_data, expected_output: test.expected_output })),
          timeout_seconds: 5,
          memory_mb: 256
        })
      );
    } catch (err) {
      setRunError(err instanceof Error ? err.message : "Unable to execute generated tests");
      setRunResult(null);
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="space-y-4">
      <section className="surface p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-emerald-600">Verification</h2>
            <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">Choose the generated solution whose code should be executed.</p>
          </div>
          <button
            type="button"
            onClick={() => void handleRunGeneratedTests()}
            disabled={running || !solution || tests.length === 0}
            className="focus-ring inline-flex h-10 items-center gap-2 rounded-md bg-emerald-600 px-3 text-sm font-semibold text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-zinc-400"
          >
            <Play size={15} aria-hidden="true" />
            {running ? `Running ${solution ? approachLabel(solution.approach_type) : "solution"}...` : `Execute ${tests.length} tests`}
          </button>
        </div>
        <div className="mt-4 grid gap-3 lg:grid-cols-3" aria-label="Solution to test">
          {orderedSolutions.map((candidate) => {
            const selected = candidate.id === solution?.id;
            return (
              <button
                key={candidate.id}
                type="button"
                onClick={() => setSelectedSolutionId(candidate.id)}
                disabled={running}
                aria-pressed={selected}
                className={`focus-ring rounded-md border p-3 text-left transition disabled:cursor-wait ${
                  selected
                    ? "border-emerald-500 bg-emerald-50 dark:bg-emerald-950/30"
                    : "border-zinc-200 bg-white hover:border-zinc-300 hover:bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-950 dark:hover:border-zinc-700 dark:hover:bg-zinc-900"
                }`}
              >
                <span className="font-mono text-xs font-semibold text-zinc-950 dark:text-zinc-100">{approachLabel(candidate.approach_type)}</span>
                <span className="mt-1 block text-xs text-zinc-500 dark:text-zinc-400">{candidate.algorithm_pattern}</span>
              </button>
            );
          })}
        </div>
        {solution ? (
          <p className="mt-3 text-sm text-zinc-600 dark:text-zinc-300">
            Selected for execution: <span className="font-semibold text-zinc-950 dark:text-white">{approachLabel(solution.approach_type)}</span>
          </p>
        ) : null}
        {latest ? (
          <div className="mt-4 grid gap-3 sm:grid-cols-4">
            <Metric label="Status" value={latest.status} />
            <Metric label="Passed" value={String(latest.passed_count)} />
            <Metric label="Failed" value={String(latest.failed_count)} />
            <Metric label="Avg Time" value={latest.execution_time_ms ? `${latest.execution_time_ms} ms` : "-"} />
          </div>
        ) : (
          <p className="mt-3 text-sm text-zinc-500 dark:text-zinc-400">Verification has not run yet.</p>
        )}
        {runResult ? (
          <div className="mt-4 grid gap-3 sm:grid-cols-4">
            <Metric label="Run Status" value={runResult.status} />
            <Metric label="Run Passed" value={String(runResult.passed_count)} />
            <Metric label="Run Failed" value={String(runResult.failed_count)} />
            <Metric label="Run Avg" value={runResult.average_execution_time_ms === null ? "-" : `${runResult.average_execution_time_ms} ms`} />
          </div>
        ) : null}
        {runError ? <p className="mt-3 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-900/60 dark:bg-red-950/40 dark:text-red-200">{runError}</p> : null}
        <div
          className={`mt-4 rounded-md border p-3 text-sm ${
            hasRecommendedMinimum
              ? "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900/60 dark:bg-emerald-950/30 dark:text-emerald-200"
              : "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200"
          }`}
        >
          Recommended minimum: {recommendedMinimum} meaningful test cases. There is no maximum limit.
        </div>
        {latest?.stderr ? <pre className="mt-3 whitespace-pre-wrap rounded-md bg-red-50 p-3 text-xs text-red-700 dark:bg-red-950/40 dark:text-red-200">{latest.stderr}</pre> : null}
      </section>
      <section className="surface overflow-hidden">
        <div className="border-b border-zinc-200 px-5 py-4 dark:border-zinc-800">
          <h2 className="text-sm font-semibold text-zinc-950 dark:text-white">Test Cases</h2>
        </div>
        <div className="divide-y divide-zinc-100 dark:divide-zinc-800">
          {tests.length === 0 ? (
            <p className="p-4 text-sm text-zinc-500 dark:text-zinc-400">No tests generated yet.</p>
          ) : (
            tests.map((test, index) => {
              const execution = resultForTest(runResult, index);
              return (
                <div key={test.id} className="p-5">
                  <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                    <p className="text-xs font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">Test case {index + 1}</p>
                    {execution ? (
                      <div className="flex items-center gap-2 font-mono text-xs">
                        <span className={execution.status === "PASSED" ? "text-emerald-600 dark:text-emerald-300" : "text-red-600 dark:text-red-300"}>
                          {execution.status}
                        </span>
                        <span className="rounded bg-zinc-100 px-2 py-1 text-zinc-600 dark:bg-zinc-900 dark:text-zinc-300">
                          {execution.execution_time_ms} ms
                        </span>
                      </div>
                    ) : null}
                  </div>
                  <div className={`grid gap-3 ${execution ? "lg:grid-cols-3" : "md:grid-cols-2"}`}>
                    <div>
                      <p className="text-xs font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-400">Input</p>
                      <pre className="mt-1 min-h-16 overflow-auto whitespace-pre-wrap rounded-md bg-zinc-950 p-3 font-mono text-xs text-zinc-100">
                        {test.input_data || "(empty input)"}
                      </pre>
                    </div>
                    <div>
                      <p className="text-xs font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-400">Expected</p>
                      <pre className="mt-1 min-h-16 overflow-auto whitespace-pre-wrap rounded-md bg-zinc-100 p-3 font-mono text-xs text-zinc-800 dark:bg-zinc-900 dark:text-zinc-100">
                        {test.expected_output || "(none)"}
                      </pre>
                    </div>
                    {execution ? (
                      <div>
                        <p className="text-xs font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-400">Returned value</p>
                        <pre className="mt-1 min-h-16 overflow-auto whitespace-pre-wrap rounded-md bg-cyan-50 p-3 font-mono text-xs text-cyan-950 dark:bg-cyan-950/30 dark:text-cyan-100">
                          {execution.stdout || "(empty output)"}
                        </pre>
                        {execution.stderr ? (
                          <pre className="mt-2 overflow-auto whitespace-pre-wrap rounded-md bg-red-50 p-3 font-mono text-xs text-red-800 dark:bg-red-950/40 dark:text-red-200">
                            {execution.stderr}
                          </pre>
                        ) : null}
                      </div>
                    ) : null}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </section>
    </div>
  );
}

function resultForTest(runResult: ExecutionResponse | null, testIndex: number): ExecutionResultItem | undefined {
  return runResult?.results.find((result) => result.test_index === testIndex);
}

function preferredSolution(solutions: GeneratedSolution[]): GeneratedSolution | undefined {
  return (
    solutions.find((solution) => solution.approach_type.toUpperCase() === "OPTIMAL") ??
    solutions.find((solution) => solution.approach_type.toUpperCase() === "EXPECTED") ??
    solutions.find((solution) => solution.approach_type.toUpperCase() === "FINAL") ??
    solutions.at(-1)
  );
}

function orderSolutions(solutions: GeneratedSolution[]): GeneratedSolution[] {
  return [...solutions].sort((left, right) => {
    const leftRank = APPROACH_ORDER[left.approach_type.toUpperCase()] ?? 10;
    const rightRank = APPROACH_ORDER[right.approach_type.toUpperCase()] ?? 10;
    return leftRank - rightRank;
  });
}

function approachLabel(approachType: string): string {
  const normalized = approachType.toUpperCase();
  if (normalized === "BRUTE_FORCE" || normalized === "NAIVE") {
    return "Brute force";
  }
  if (normalized === "IMPROVED" || normalized === "AVERAGE") {
    return "Improved";
  }
  if (normalized === "OPTIMAL" || normalized === "EXPECTED") {
    return "Expected solution";
  }
  if (normalized === "FINAL") {
    return "Verified solution";
  }
  return approachType.replaceAll("_", " ").toLowerCase();
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-zinc-200 bg-zinc-50 p-3 dark:border-zinc-800 dark:bg-zinc-900">
      <p className="text-xs uppercase tracking-wide text-zinc-500 dark:text-zinc-400">{label}</p>
      <p className="mt-1 font-mono text-lg font-semibold text-zinc-950 dark:text-zinc-100">{value}</p>
    </div>
  );
}
