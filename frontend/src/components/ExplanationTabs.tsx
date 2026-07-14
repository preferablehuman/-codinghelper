import ReactMarkdown from "react-markdown";
import { Play, Route } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { executeCode } from "../api/client";
import type { ExecutionResponse, Explanation, GeneratedSolution, TestCase, VerificationRun } from "../types/api";

const APPROACH_ORDER: Record<string, number> = {
  BRUTE_FORCE: 0,
  NAIVE: 0,
  IMPROVED: 1,
  AVERAGE: 1,
  OPTIMAL: 2,
  EXPECTED: 2,
  FINAL: 3
};

export default function ExplanationTabs({
  explanation,
  solutions = [],
  tests = [],
  verificationRuns = [],
  language
}: {
  explanation?: Explanation;
  solutions?: GeneratedSolution[];
  tests?: TestCase[];
  verificationRuns?: VerificationRun[];
  language: string;
}) {
  const orderedSolutions = useMemo(() => orderSolutions(solutions), [solutions]);
  const preferred = useMemo(() => preferredSolution(orderedSolutions), [orderedSolutions]);
  const [activeId, setActiveId] = useState<string | null>(preferred?.id ?? null);
  const activeSolution = orderedSolutions.find((solution) => solution.id === activeId) ?? preferred;
  const activeDryRun = useMemo(
    () => formatWalkthroughMarkdown(extractApproachMarkdown(explanation?.dry_run || "", activeSolution?.approach_type || "")),
    [activeSolution?.approach_type, explanation?.dry_run]
  );
  const activeIntuition = useMemo(
    () => stripApproachHeading(extractApproachMarkdown(explanation?.intuition || "", activeSolution?.approach_type || "")),
    [activeSolution?.approach_type, explanation?.intuition]
  );
  const activeApproachDetail = useMemo(
    () => stripApproachHeading(extractApproachMarkdown(explanation?.optimized_approach || "", activeSolution?.approach_type || "")),
    [activeSolution?.approach_type, explanation?.optimized_approach]
  );
  const activePitfalls = useMemo(
    () => stripApproachHeading(extractApproachMarkdown(explanation?.pitfalls || "", activeSolution?.approach_type || "")),
    [activeSolution?.approach_type, explanation?.pitfalls]
  );
  const activeComplexity = useMemo(
    () => stripApproachHeading(extractApproachMarkdown(explanation?.complexity_analysis || "", activeSolution?.approach_type || "")),
    [activeSolution?.approach_type, explanation?.complexity_analysis]
  );
  const latestVerification = verificationRuns.filter((run) => run.solution_id === activeSolution?.id).at(-1);
  const [running, setRunning] = useState(false);
  const [runResult, setRunResult] = useState<ExecutionResponse | null>(null);
  const [runError, setRunError] = useState<string | null>(null);

  useEffect(() => {
    if (preferred && !orderedSolutions.some((solution) => solution.id === activeId)) {
      setActiveId(preferred.id);
    }
  }, [activeId, orderedSolutions, preferred]);

  useEffect(() => {
    setRunResult(null);
    setRunError(null);
  }, [activeSolution?.id]);

  if (!explanation && !activeSolution) {
    return <p className="text-sm text-zinc-500 dark:text-zinc-400">Explanation will appear when generation completes.</p>;
  }

  async function handleRunGeneratedTests() {
    if (!activeSolution) {
      return;
    }
    setRunning(true);
    setRunError(null);
    try {
      setRunResult(
        await executeCode({
          language,
          code: activeSolution.code,
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
    <div className="space-y-5">
      <section className="surface p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-zinc-950 dark:text-white">Explanation workspace</h2>
            <p className="mt-1 max-w-3xl text-sm leading-6 text-zinc-600 dark:text-zinc-400">
              Select a solution and learn its foundations, intuition, state, execution flow, code, complexity, and common mistakes from first principles.
            </p>
          </div>
        </div>

        <div className="mt-5 grid gap-3 lg:grid-cols-3">
          {orderedSolutions.map((solution) => {
            const selected = solution.id === activeSolution?.id;
            return (
              <button
                key={solution.id}
                type="button"
                onClick={() => setActiveId(solution.id)}
                disabled={running}
                className={`focus-ring min-h-[126px] rounded-md border p-3 text-left transition duration-200 hover:-translate-y-0.5 disabled:cursor-wait disabled:hover:translate-y-0 ${
                  selected
                    ? "border-emerald-500 bg-emerald-50 dark:bg-emerald-950/30"
                    : "border-zinc-200 bg-white hover:bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-950 dark:hover:bg-zinc-900"
                }`}
              >
                <span className={`rounded-md px-2 py-1 font-mono text-xs ${approachBadgeClass(solution.approach_type)}`}>{approachLabel(solution.approach_type)}</span>
                <p className="mt-3 text-sm font-semibold text-zinc-950 dark:text-zinc-100">{solution.algorithm_pattern}</p>
                <p className="mt-2 font-mono text-xs text-zinc-500 dark:text-zinc-400">
                  {solution.time_complexity} time / {solution.space_complexity} space
                </p>
              </button>
            );
          })}
        </div>
      </section>

      <section className="surface overflow-hidden">
        <div className="border-b border-zinc-200 px-5 py-4 dark:border-zinc-800">
          <h3 className="flex items-center gap-2 text-base font-semibold text-zinc-950 dark:text-white">
            <Route size={18} className="text-emerald-500" aria-hidden="true" />
            Complete explanation: {activeSolution ? approachLabel(activeSolution.approach_type) : "solution"}
          </h3>
          <p className="mt-1 text-sm leading-6 text-zinc-500 dark:text-zinc-400">
            One continuous lesson covering foundations, intuition, data structures, code flow, the supplied example, state transitions, pitfalls, and complexity.
          </p>
        </div>
        <div className="space-y-8 p-5">
          <div>
            <h4 className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-emerald-600">Foundations and intuition</h4>
            <ReactMarkdown className="markdown-body mt-3">{activeIntuition || activeSolution?.explanation || ""}</ReactMarkdown>
          </div>
          <div className="border-t border-zinc-200 pt-6 dark:border-zinc-800">
            <h4 className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-emerald-600">Approach and data-structure flow</h4>
            <ReactMarkdown className="markdown-body mt-3">{activeApproachDetail || activeSolution?.explanation || ""}</ReactMarkdown>
          </div>
          <div className="border-t border-zinc-200 pt-6 dark:border-zinc-800">
            <h4 className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-emerald-600">Annotated code stub</h4>
            <CodeStub source={activeSolution?.pseudocode || "Read input\nTrack state\nMake decision\nReturn answer"} />
          </div>
          <div className="border-t border-zinc-200 pt-6 dark:border-zinc-800">
            <h4 className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-emerald-600">Given-example execution trace</h4>
            <WalkthroughContent markdown={activeDryRun || explanation?.dry_run || ""} />
          </div>
          <div className="border-t border-zinc-200 pt-6 dark:border-zinc-800">
            <h4 className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-emerald-600">Pitfalls</h4>
            <ReactMarkdown className="markdown-body mt-3">{activePitfalls || "Pitfalls will appear when explanation generation completes."}</ReactMarkdown>
          </div>
          <div className="border-t border-zinc-200 pt-6 dark:border-zinc-800">
            <h4 className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-emerald-600">Complexity</h4>
            <ReactMarkdown className="markdown-body mt-3">
              {activeComplexity || `${activeSolution?.time_complexity ?? ""}\n\n${activeSolution?.space_complexity ?? ""}`}
            </ReactMarkdown>
          </div>
        </div>
      </section>

      <section className="surface p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-sm font-semibold text-zinc-950 dark:text-white">Proof run</h3>
              {activeSolution ? (
                <span className="rounded-md border border-emerald-200 bg-emerald-50 px-2 py-1 font-mono text-xs text-emerald-700 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-200">
                  Testing: {approachLabel(activeSolution.approach_type)}
                </span>
              ) : null}
            </div>
            <p className="mt-2 text-sm leading-6 text-zinc-600 dark:text-zinc-400">
              Execute the solution selected at the top of this explanation against every generated test and inspect the aggregate timing.
            </p>
            <button
              type="button"
              onClick={() => void handleRunGeneratedTests()}
              disabled={running || !activeSolution || tests.length === 0}
              className="focus-ring mt-4 inline-flex h-11 w-full items-center justify-center gap-2 rounded-md bg-emerald-600 px-4 text-sm font-semibold text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-zinc-400"
            >
              <Play size={16} aria-hidden="true" />
              {running ? `Running ${activeSolution ? approachLabel(activeSolution.approach_type) : "solution"}...` : `Execute ${tests.length} tests`}
            </button>
            {runResult ? (
              <div className="mt-4 grid grid-cols-2 gap-2">
                <Metric label="Status" value={runResult.status} />
                <Metric label="Avg" value={runResult.average_execution_time_ms === null ? "-" : `${runResult.average_execution_time_ms} ms`} />
                <Metric label="Passed" value={String(runResult.passed_count)} />
                <Metric label="Failed" value={String(runResult.failed_count)} />
              </div>
            ) : latestVerification ? (
              <div className="mt-4 grid grid-cols-2 gap-2">
                <Metric label="Verified" value={latestVerification.status} />
                <Metric label="Avg" value={latestVerification.execution_time_ms ? `${latestVerification.execution_time_ms} ms` : "-"} />
                <Metric label="Passed" value={String(latestVerification.passed_count)} />
                <Metric label="Failed" value={String(latestVerification.failed_count)} />
              </div>
            ) : null}
            {runError ? <p className="mt-3 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-900/60 dark:bg-red-950/40 dark:text-red-200">{runError}</p> : null}
      </section>
    </div>
  );
}

function CodeStub({ source }: { source: string }) {
  const lines = formatCodeLines(source);
  return (
    <div className="mt-3 overflow-hidden rounded-lg border border-zinc-800 bg-zinc-950 shadow-inner">
      <div className="flex items-center gap-2 border-b border-zinc-800 bg-zinc-900 px-4 py-2">
        <span className="h-2.5 w-2.5 rounded-full bg-red-400" />
        <span className="h-2.5 w-2.5 rounded-full bg-amber-400" />
        <span className="h-2.5 w-2.5 rounded-full bg-emerald-400" />
        <span className="ml-2 font-mono text-[11px] uppercase tracking-wider text-zinc-500">logic map</span>
      </div>
      <ol className="max-h-[560px] overflow-auto py-3">
        {lines.map((line, index) => (
          <li key={`${index}-${line}`} className="grid grid-cols-[44px_minmax(0,1fr)] px-3 font-mono text-xs leading-6 text-zinc-100">
            <span className="select-none border-r border-zinc-800 pr-3 text-right text-zinc-600">{index + 1}</span>
            <code className="min-w-0 whitespace-pre-wrap break-words pl-4">{line}</code>
          </li>
        ))}
      </ol>
    </div>
  );
}

function WalkthroughContent({ markdown }: { markdown: string }) {
  const sections = parseWalkthroughSections(markdown);
  return (
    <div className="mt-4 space-y-6">
      {sections.map((section, index) => {
        const normalizedTitle = section.title.toLowerCase();
        return (
          <section key={`${section.title}-${index}`} className="rounded-lg border border-zinc-200 bg-zinc-50/70 p-4 dark:border-zinc-800 dark:bg-zinc-900/60">
            <div className="flex items-center gap-3">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-emerald-100 font-mono text-xs font-bold text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">
                {index + 1}
              </span>
              <h5 className="text-sm font-semibold text-zinc-950 dark:text-white">{section.title}</h5>
            </div>
            {normalizedTitle.includes("code stub") ? (
              <CodeStub source={section.body} />
            ) : normalizedTitle.includes("step-by-step") ? (
              <ExecutionTable markdown={section.body} />
            ) : normalizedTitle.includes("state model") ? (
              <StateModel body={section.body} />
            ) : (
              <ReactMarkdown className="markdown-body mt-3">{section.body}</ReactMarkdown>
            )}
          </section>
        );
      })}
    </div>
  );
}

function StateModel({ body }: { body: string }) {
  const items = body.split(/;|\r?\n/).map((item) => item.trim()).filter(Boolean);
  return (
    <dl className="mt-4 grid gap-3 md:grid-cols-2">
      {items.map((item, index) => {
        const separator = item.indexOf(":");
        const name = separator > 0 ? item.slice(0, separator).trim() : `State ${index + 1}`;
        const meaning = separator > 0 ? item.slice(separator + 1).trim() : item;
        return (
          <div key={`${name}-${index}`} className="rounded-md border border-zinc-200 bg-white p-3 dark:border-zinc-700 dark:bg-zinc-950">
            <dt className="font-mono text-xs font-semibold text-emerald-700 dark:text-emerald-300">{name}</dt>
            <dd className="mt-1 text-sm leading-6 text-zinc-600 dark:text-zinc-300">{meaning}</dd>
          </div>
        );
      })}
    </dl>
  );
}

function ExecutionTable({ markdown }: { markdown: string }) {
  const table = parseExecutionTable(markdown);
  if (!table) {
    return <ReactMarkdown className="markdown-body mt-3">{markdown}</ReactMarkdown>;
  }
  return (
    <div className="mt-4 overflow-x-auto rounded-lg border border-zinc-200 bg-white dark:border-zinc-700 dark:bg-zinc-950">
      <table className="min-w-[1180px] border-collapse text-left text-xs">
        <thead className="sticky top-0 bg-zinc-100 text-zinc-700 dark:bg-zinc-900 dark:text-zinc-200">
          <tr>{table.headers.map((header) => <th key={header} className="border-b border-r border-zinc-200 px-3 py-3 font-semibold last:border-r-0 dark:border-zinc-700">{header}</th>)}</tr>
        </thead>
        <tbody>
          {table.rows.map((row, rowIndex) => (
            <tr key={rowIndex} className="align-top odd:bg-white even:bg-zinc-50 dark:odd:bg-zinc-950 dark:even:bg-zinc-900/60">
              {table.headers.map((_, cellIndex) => (
                <td key={cellIndex} className={`border-b border-r border-zinc-200 px-3 py-3 leading-5 last:border-r-0 dark:border-zinc-800 ${cellIndex === 0 ? "font-mono font-semibold text-emerald-700 dark:text-emerald-300" : "text-zinc-700 dark:text-zinc-300"}`}>
                  {row[cellIndex] || "—"}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatCodeLines(source: string): string[] {
  const expanded = source
    .replace(/\s*;\s*/g, ";\n")
    .replace(/:\s+(?=(?:if|for|while|return|add|remove|recurse|solve|backtrack)\b)/gi, ":\n")
    .replace(/\)\s+(?=(?:if|for|while|return)\b)/gi, ")\n");
  const lines = expanded.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  return lines.length ? lines : [source.trim()];
}

function parseWalkthroughSections(markdown: string): Array<{ title: string; body: string }> {
  const lines = markdown.split(/\r?\n/);
  const sections: Array<{ title: string; body: string[] }> = [];
  for (const line of lines) {
    const heading = line.match(/^###\s+(.+)$/);
    if (heading) {
      sections.push({ title: heading[1].trim(), body: [] });
    } else if (sections.length) {
      sections[sections.length - 1].body.push(line);
    }
  }
  if (!sections.length) {
    return [{ title: "Execution walkthrough", body: markdown.trim() }];
  }
  return sections.map((section) => ({ title: section.title, body: section.body.join("\n").trim() }));
}

function parseExecutionTable(markdown: string): { headers: string[]; rows: string[][] } | null {
  const lines = markdown.split(/\r?\n/).map((line) => line.trim()).filter((line) => line.startsWith("|"));
  if (lines.length < 3) return null;
  const cells = (line: string) => line.replace(/^\|/, "").replace(/\|$/, "").split("|").map((cell) => cell.trim());
  const headers = cells(lines[0]);
  const rows = lines.slice(2).map(cells).filter((row) => row.some(Boolean));
  return headers.length && rows.length ? { headers, rows } : null;
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-zinc-200 bg-zinc-50 p-3 dark:border-zinc-800 dark:bg-zinc-900">
      <p className="text-xs uppercase tracking-wide text-zinc-500 dark:text-zinc-400">{label}</p>
      <p className="mt-1 font-mono text-sm font-semibold text-zinc-950 dark:text-zinc-100">{value}</p>
    </div>
  );
}

function extractApproachMarkdown(markdown: string, approachType: string): string {
  if (!markdown || !approachType) {
    return markdown;
  }
  const labels = [approachType, approachLabel(approachType), approachType.replaceAll("_", " ")].map((value) => value.toLowerCase());
  const sections = markdown.split(/(?=^##\s+)/gim);
  const match = sections.find((section) => {
    const heading = section.split(/\r?\n/, 1)[0]?.replace(/^##\s+/, "").trim().toLowerCase() || "";
    return labels.some((label) => heading.includes(label));
  });
  return match || markdown;
}

function stripApproachHeading(markdown: string): string {
  return markdown.replace(/^##\s+[^\r\n]+\r?\n+/, "").trim();
}

function formatWalkthroughMarkdown(markdown: string): string {
  const content = stripApproachHeading(markdown);
  if (!content.startsWith("{") || !content.endsWith("}")) {
    return content;
  }
  try {
    const parsed = JSON.parse(content) as Record<string, unknown>;
    return Object.entries(parsed)
      .filter(([, value]) => typeof value === "string" && value.trim())
      .map(([heading, value]) => `${heading.startsWith("#") ? heading : `### ${heading}`}\n\n${String(value).trim()}`)
      .join("\n\n");
  } catch {
    return content;
  }
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
