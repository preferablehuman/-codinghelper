import Editor from "@monaco-editor/react";
import ReactMarkdown from "react-markdown";
import { AlertTriangle, Braces, CheckCircle2, Layers3, Play, RotateCcw, Terminal, XCircle } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { executeCode } from "../api/client";
import type { ExecutionResponse, ExecutionResultItem, GeneratedSolution, TestCase } from "../types/api";

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

export default function CodeViewer({
  solutions,
  language,
  tests = []
}: {
  solutions: GeneratedSolution[];
  language: string;
  tests?: TestCase[];
}) {
  const orderedSolutions = useMemo(() => orderSolutions(solutions), [solutions]);
  const preferred = useMemo(() => preferredSolution(orderedSolutions), [orderedSolutions]);
  const [activeId, setActiveId] = useState<string | null>(preferred?.id ?? null);
  const activeSolution = orderedSolutions.find((solution) => solution.id === activeId) ?? preferred;
  const [code, setCode] = useState(activeSolution?.code ?? "");
  const [customInput, setCustomInput] = useState("");
  const [expectedOutput, setExpectedOutput] = useState("");
  const [running, setRunning] = useState<"custom" | "generated" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [runResult, setRunResult] = useState<ExecutionResponse | null>(null);

  useEffect(() => {
    if (preferred && !orderedSolutions.some((solution) => solution.id === activeId)) {
      setActiveId(preferred.id);
    }
  }, [activeId, orderedSolutions, preferred]);

  useEffect(() => {
    setCode(activeSolution?.code ?? "");
    setRunResult(null);
    setError(null);
  }, [activeSolution?.id, activeSolution?.code]);

  const monacoLanguage = editorLanguage(language);
  const primaryResult = runResult?.results[0];
  const resultTone = useMemo(() => toneForStatus(runResult?.status), [runResult?.status]);

  if (!activeSolution) {
    return <p className="text-sm text-zinc-500 dark:text-zinc-400">Code will appear when generation completes.</p>;
  }

  async function handleRun() {
    setRunning("custom");
    setError(null);
    try {
      const result = await executeCode({
        language,
        code,
        input: customInput,
        expected_output: expectedOutput.trim() ? expectedOutput : null,
        timeout_seconds: 5,
        memory_mb: 256
      });
      setRunResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to execute code");
      setRunResult(null);
    } finally {
      setRunning(null);
    }
  }

  async function handleRunGeneratedTests() {
    setRunning("generated");
    setError(null);
    try {
      const result = await executeCode({
        language,
        code,
        input: "",
        expected_output: null,
        tests: tests.map((test) => ({
          input: test.input_data,
          expected_output: test.expected_output
        })),
        timeout_seconds: 5,
        memory_mb: 256
      });
      setRunResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to execute generated tests");
      setRunResult(null);
    } finally {
      setRunning(null);
    }
  }

  return (
    <div className="grid gap-5 2xl:grid-cols-[minmax(0,1fr)_440px]">
      <section className="min-w-0 space-y-4">
        <div className="surface overflow-hidden">
          <div className="border-b border-zinc-200 p-4 dark:border-zinc-800">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="flex items-center gap-2 text-base font-semibold text-zinc-950 dark:text-white">
                  <Layers3 size={18} className="text-emerald-500" aria-hidden="true" />
                  Implementation ladder
                </h2>
                <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">Compare brute force, improved, and expected approaches side by side.</p>
              </div>
              <span className="rounded-md border border-zinc-200 bg-zinc-50 px-2 py-1 font-mono text-xs text-zinc-600 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-300">
                {orderedSolutions.length} variant{orderedSolutions.length === 1 ? "" : "s"}
              </span>
            </div>
            <div className="mt-4 grid gap-3 lg:grid-cols-3">
              {orderedSolutions.map((solution) => {
                const selected = solution.id === activeSolution.id;
                return (
                  <button
                    key={solution.id}
                    type="button"
                    onClick={() => setActiveId(solution.id)}
                    className={`focus-ring min-h-[132px] rounded-md border p-3 text-left transition duration-200 hover:-translate-y-0.5 ${
                      selected
                        ? "border-emerald-500 bg-emerald-50 shadow-sm shadow-emerald-950/10 dark:bg-emerald-950/30"
                        : "border-zinc-200 bg-white hover:border-zinc-300 hover:bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-950 dark:hover:border-zinc-700 dark:hover:bg-zinc-900"
                    }`}
                  >
                    <span className={`inline-flex rounded-md px-2 py-1 font-mono text-xs ${approachBadgeClass(solution.approach_type)}`}>
                      {approachLabel(solution.approach_type)}
                    </span>
                    <p className="mt-3 line-clamp-2 text-sm font-semibold text-zinc-950 dark:text-zinc-100">{solution.algorithm_pattern}</p>
                    <p className="mt-2 font-mono text-xs text-zinc-500 dark:text-zinc-400">
                      {solution.time_complexity} time / {solution.space_complexity} space
                    </p>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-zinc-800 bg-zinc-950 px-4 py-3">
            <div>
              <h3 className="flex items-center gap-2 text-sm font-semibold text-zinc-100">
                <Terminal size={16} className="text-emerald-300" aria-hidden="true" />
                {approachLabel(activeSolution.approach_type)}
              </h3>
              <p className="mt-1 font-mono text-xs text-zinc-400">
                {activeSolution.algorithm_pattern} - {activeSolution.time_complexity} time - {activeSolution.space_complexity} space
              </p>
            </div>
            <button
              type="button"
              onClick={() => {
                setCode(activeSolution.code);
                setRunResult(null);
                setError(null);
              }}
              className="focus-ring inline-flex h-9 items-center gap-2 rounded-md border border-zinc-700 px-3 text-sm text-zinc-200 transition hover:bg-zinc-900"
            >
              <RotateCcw size={15} aria-hidden="true" />
              Reset
            </button>
          </div>
          <div className="h-[620px]">
            <Editor
              height="100%"
              language={monacoLanguage}
              theme="vs-dark"
              value={code}
              onChange={(value) => setCode(value ?? "")}
              options={{
                minimap: { enabled: false },
                fontSize: 14,
                fontLigatures: true,
                lineNumbersMinChars: 3,
                padding: { top: 16, bottom: 16 },
                scrollBeyondLastLine: false,
                wordWrap: "on"
              }}
            />
          </div>
        </div>
      </section>

      <aside className="space-y-4">
        <section className="surface p-4">
          <h3 className="flex items-center gap-2 text-sm font-semibold text-zinc-950 dark:text-white">
            <Braces size={16} className="text-cyan-600 dark:text-cyan-300" aria-hidden="true" />
            Approach notes
          </h3>
          <ReactMarkdown className="markdown-body mt-3">{activeSolution.explanation}</ReactMarkdown>
          <div className="mt-4 rounded-md border border-zinc-200 bg-zinc-50 p-3 dark:border-zinc-800 dark:bg-zinc-900">
            <p className="text-xs font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">Logic stub</p>
            <pre className="mt-2 max-h-52 overflow-auto whitespace-pre-wrap rounded-md bg-zinc-950 p-3 font-mono text-xs leading-5 text-zinc-100">
              {activeSolution.pseudocode || "Read input\nUpdate state\nReturn answer"}
            </pre>
          </div>
        </section>

        <section className="surface p-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-zinc-950 dark:text-white">Custom test</h3>
            <span className="rounded-md bg-zinc-100 px-2 py-1 font-mono text-xs text-zinc-600 dark:bg-zinc-900 dark:text-zinc-300">{language}</span>
          </div>
          <label className="mt-4 block">
            <span className="text-xs font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-400">stdin</span>
            <textarea
              value={customInput}
              onChange={(event) => setCustomInput(event.target.value)}
              className="focus-ring mt-2 min-h-36 w-full rounded-md border border-zinc-300 bg-zinc-950 px-3 py-2 font-mono text-sm leading-6 text-zinc-100 placeholder:text-zinc-500 dark:border-zinc-700"
              placeholder="Paste input exactly as the program should read it"
            />
          </label>
          <label className="mt-4 block">
            <span className="text-xs font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-400">expected output</span>
            <textarea
              value={expectedOutput}
              onChange={(event) => setExpectedOutput(event.target.value)}
              className="focus-ring mt-2 min-h-24 w-full rounded-md border border-zinc-300 bg-white px-3 py-2 font-mono text-sm leading-6 text-zinc-950 transition dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-100"
              placeholder="Optional exact output"
            />
          </label>
          <button
            type="button"
            onClick={() => void handleRun()}
            disabled={running !== null || !code.trim()}
            className="focus-ring mt-4 inline-flex h-11 w-full items-center justify-center gap-2 rounded-md bg-emerald-600 px-4 text-sm font-semibold text-white shadow-sm shadow-emerald-900/20 transition duration-200 hover:-translate-y-0.5 hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-zinc-400 disabled:hover:translate-y-0"
          >
            <Play size={16} aria-hidden="true" />
            {running === "custom" ? "Running..." : "Run custom input"}
          </button>
          <button
            type="button"
            onClick={() => void handleRunGeneratedTests()}
            disabled={running !== null || !code.trim() || tests.length === 0}
            className="focus-ring mt-3 inline-flex h-11 w-full items-center justify-center gap-2 rounded-md border border-zinc-300 bg-white px-4 text-sm font-semibold text-zinc-800 transition duration-200 hover:-translate-y-0.5 hover:bg-zinc-100 disabled:cursor-not-allowed disabled:text-zinc-400 disabled:hover:translate-y-0 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-100 dark:hover:bg-zinc-900"
          >
            <Play size={16} aria-hidden="true" />
            {running === "generated" ? "Running tests..." : `Run generated tests (${tests.length})`}
          </button>
        </section>

        <section className="surface overflow-hidden">
          <div className="flex items-center justify-between border-b border-zinc-200 px-4 py-3 dark:border-zinc-800">
            <h3 className="text-sm font-semibold text-zinc-950 dark:text-white">Run output</h3>
            {runResult ? <StatusBadge status={runResult.status} /> : null}
          </div>
          <div className="p-4">
            {error ? (
              <ErrorBlock message={error} />
            ) : runResult && primaryResult ? (
              <RunResult result={primaryResult} response={runResult} tone={resultTone} expectedOutput={expectedOutput} />
            ) : (
              <p className="text-sm text-zinc-500 dark:text-zinc-400">No custom run yet.</p>
            )}
          </div>
        </section>
      </aside>
    </div>
  );
}

function RunResult({
  result,
  response,
  tone,
  expectedOutput
}: {
  result: ExecutionResultItem;
  response: ExecutionResponse;
  tone: "pass" | "fail" | "warn";
  expectedOutput: string;
}) {
  const Icon = tone === "pass" ? CheckCircle2 : tone === "warn" ? AlertTriangle : XCircle;
  const message = fallbackMessage(result.status);
  return (
    <div className="space-y-4">
      <div className="flex items-start gap-3">
        <Icon
          size={19}
          className={tone === "pass" ? "text-emerald-600" : tone === "warn" ? "text-amber-600" : "text-red-600"}
          aria-hidden="true"
        />
        <div>
          <p className="font-mono text-sm font-semibold text-zinc-950 dark:text-zinc-100">{result.status}</p>
          <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">{message}</p>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2">
        <MetricChip label="Passed" value={String(response.passed_count)} />
        <MetricChip label="Failed" value={String(response.failed_count)} />
        <MetricChip label="Avg" value={response.average_execution_time_ms === null ? "-" : `${response.average_execution_time_ms} ms`} />
      </div>
      {response.results.length > 1 ? <ResultList results={response.results} /> : null}
      <OutputBlock label="stdout" value={result.stdout} emptyText="(empty)" />
      {result.stderr ? <OutputBlock label="stderr" value={result.stderr} tone="error" /> : null}
      {expectedOutput.trim() && response.results.length === 1 ? <OutputBlock label="expected" value={expectedOutput} /> : null}
      <p className="font-mono text-xs text-zinc-500 dark:text-zinc-400">First result: {result.execution_time_ms} ms</p>
    </div>
  );
}

function MetricChip({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-zinc-200 bg-zinc-50 p-2 dark:border-zinc-800 dark:bg-zinc-900">
      <p className="text-xs uppercase tracking-wide text-zinc-500 dark:text-zinc-400">{label}</p>
      <p className="mt-1 font-mono text-xs font-semibold text-zinc-950 dark:text-zinc-100">{value}</p>
    </div>
  );
}

function ResultList({ results }: { results: ExecutionResultItem[] }) {
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-400">Generated test results</p>
      <div className="mt-2 max-h-48 overflow-auto rounded-md border border-zinc-200 dark:border-zinc-800">
        {results.map((item) => (
          <div key={item.test_index} className="flex items-center justify-between gap-3 border-b border-zinc-100 px-3 py-2 text-xs last:border-b-0 dark:border-zinc-800">
            <span className="font-mono text-zinc-500 dark:text-zinc-400">#{item.test_index + 1}</span>
            <span className={item.status === "PASSED" ? "text-emerald-600 dark:text-emerald-300" : "text-red-600 dark:text-red-300"}>{item.status}</span>
            <span className="font-mono text-zinc-500 dark:text-zinc-400">{item.execution_time_ms} ms</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function OutputBlock({
  label,
  value,
  tone = "default",
  emptyText = ""
}: {
  label: string;
  value: string;
  tone?: "default" | "error";
  emptyText?: string;
}) {
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-400">{label}</p>
      <pre
        className={`mt-2 max-h-48 overflow-auto whitespace-pre-wrap rounded-md p-3 font-mono text-xs ${
          tone === "error"
            ? "bg-red-50 text-red-800 dark:bg-red-950/40 dark:text-red-200"
            : "bg-zinc-950 text-zinc-100"
        }`}
      >
        {value || emptyText}
      </pre>
    </div>
  );
}

function ErrorBlock({ message }: { message: string }) {
  return (
    <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800 dark:border-red-900/60 dark:bg-red-950/40 dark:text-red-200">
      <div className="flex items-start gap-2">
        <AlertTriangle size={17} aria-hidden="true" />
        <span>{message}</span>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const tone = toneForStatus(status);
  const classes =
    tone === "pass"
      ? "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-200"
      : tone === "warn"
        ? "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-200"
        : "border-red-200 bg-red-50 text-red-700 dark:border-red-900/60 dark:bg-red-950/40 dark:text-red-200";
  return <span className={`rounded-md border px-2 py-1 font-mono text-xs ${classes}`}>{status}</span>;
}

function toneForStatus(status?: string): "pass" | "fail" | "warn" {
  if (status === "PASSED") {
    return "pass";
  }
  if (status === "TIMEOUT") {
    return "warn";
  }
  return "fail";
}

function fallbackMessage(status: string): string {
  if (status === "PASSED") {
    return "The program completed successfully.";
  }
  if (status === "FAILED") {
    return "The program ran, but the output did not match the expected value.";
  }
  if (status === "COMPILE_ERROR") {
    return "Compilation failed before execution.";
  }
  if (status === "RUNTIME_ERROR") {
    return "The program threw an error while running.";
  }
  if (status === "TIMEOUT") {
    return "Execution reached the sandbox time limit.";
  }
  return "The sandbox returned a non-passing result.";
}

function orderSolutions(solutions: GeneratedSolution[]): GeneratedSolution[] {
  return [...solutions].sort((left, right) => {
    const leftRank = APPROACH_ORDER[left.approach_type.toUpperCase()] ?? 10;
    const rightRank = APPROACH_ORDER[right.approach_type.toUpperCase()] ?? 10;
    return leftRank - rightRank;
  });
}

function preferredSolution(solutions: GeneratedSolution[]): GeneratedSolution | undefined {
  return (
    solutions.find((solution) => solution.approach_type.toUpperCase() === "OPTIMAL") ??
    solutions.find((solution) => solution.approach_type.toUpperCase() === "EXPECTED") ??
    solutions.find((solution) => solution.approach_type.toUpperCase() === "FINAL") ??
    solutions.at(-1)
  );
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

function approachBadgeClass(approachType: string): string {
  const normalized = approachType.toUpperCase();
  if (normalized === "BRUTE_FORCE" || normalized === "NAIVE") {
    return "bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-200";
  }
  if (normalized === "IMPROVED" || normalized === "AVERAGE") {
    return "bg-cyan-100 text-cyan-800 dark:bg-cyan-950/60 dark:text-cyan-200";
  }
  return "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-200";
}

function editorLanguage(language: string): string {
  const normalized = language.toLowerCase();
  if (normalized === "cpp" || normalized === "c++") {
    return "cpp";
  }
  if (normalized === "javascript" || normalized === "js") {
    return "javascript";
  }
  if (normalized === "python") {
    return "python";
  }
  return "java";
}
