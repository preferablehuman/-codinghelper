import ReactMarkdown from "react-markdown";
import { Braces, Footprints, GitBranch, Route } from "lucide-react";
import { useMemo } from "react";

import type { Explanation, GeneratedSolution } from "../types/api";

const APPROACH_ORDER: Record<string, number> = {
  BRUTE_FORCE: 0,
  NAIVE: 0,
  IMPROVED: 1,
  AVERAGE: 1,
  OPTIMAL: 2,
  EXPECTED: 2,
  FINAL: 3
};

export default function DryRunVisualizer({
  explanation,
  solutions = []
}: {
  explanation?: Explanation;
  solutions?: GeneratedSolution[];
}) {
  const orderedSolutions = useMemo(() => orderSolutions(solutions), [solutions]);
  const activeSolution = preferredSolution(orderedSolutions);

  if (!explanation && !activeSolution) {
    return <p className="text-sm text-zinc-500 dark:text-zinc-400">Dry run will appear when explanation generation completes.</p>;
  }

  return (
    <div className="grid gap-5 xl:grid-cols-[360px_minmax(0,1fr)]">
      <aside className="space-y-4">
        <section className="surface p-4">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-zinc-950 dark:text-white">
            <GitBranch size={16} className="text-emerald-500" aria-hidden="true" />
            Approach buildup
          </h2>
          <div className="mt-4 space-y-3">
            {orderedSolutions.length ? (
              orderedSolutions.map((solution, index) => (
                <div key={solution.id} className="rounded-md border border-zinc-200 bg-zinc-50 p-3 dark:border-zinc-800 dark:bg-zinc-900">
                  <div className="flex items-center justify-between gap-3">
                    <span className={`rounded-md px-2 py-1 font-mono text-xs ${approachBadgeClass(solution.approach_type)}`}>
                      {approachLabel(solution.approach_type)}
                    </span>
                    <span className="font-mono text-xs text-zinc-500 dark:text-zinc-400">0{index + 1}</span>
                  </div>
                  <p className="mt-3 text-sm font-semibold text-zinc-950 dark:text-zinc-100">{solution.algorithm_pattern}</p>
                  <p className="mt-2 font-mono text-xs text-zinc-500 dark:text-zinc-400">
                    {solution.time_complexity} time / {solution.space_complexity} space
                  </p>
                </div>
              ))
            ) : (
              <p className="text-sm text-zinc-500 dark:text-zinc-400">Approach variants will appear with the next generated job.</p>
            )}
          </div>
        </section>

        <section className="surface p-4">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-zinc-950 dark:text-white">
            <Braces size={16} className="text-cyan-600 dark:text-cyan-300" aria-hidden="true" />
            Code logic stub
          </h2>
          <pre className="mt-3 max-h-[420px] overflow-auto whitespace-pre-wrap rounded-md bg-zinc-950 p-4 font-mono text-xs leading-5 text-zinc-100 shadow-inner shadow-black/20">
            {activeSolution?.pseudocode || "Read input\nInitialize state\nProcess each item\nPrint answer"}
          </pre>
        </section>
      </aside>

      <section className="space-y-4">
        <div className="surface overflow-hidden">
          <div className="border-b border-zinc-200 px-5 py-4 dark:border-zinc-800">
            <h2 className="flex items-center gap-2 text-base font-semibold text-zinc-950 dark:text-white">
              <Route size={18} className="text-emerald-500" aria-hidden="true" />
              Execution trace
            </h2>
            <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">Follow the state changes, decision points, and output as the code runs.</p>
          </div>
          <div className="p-5">
            <ReactMarkdown className="markdown-body">{explanation?.dry_run || activeSolution?.explanation || ""}</ReactMarkdown>
          </div>
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <section className="surface p-5">
            <h3 className="flex items-center gap-2 text-sm font-semibold text-zinc-950 dark:text-white">
              <Footprints size={16} className="text-amber-600 dark:text-amber-300" aria-hidden="true" />
              Step guidance
            </h3>
            <div className="markdown-body mt-3">
              <ol>
                <li>Map each input token to the variable that reads it.</li>
                <li>Track the state after every loop iteration or recursive call.</li>
                <li>Mark the exact condition where the code chooses one branch over another.</li>
                <li>Confirm the final printed value from the last state snapshot.</li>
              </ol>
            </div>
          </section>
          <section className="surface p-5">
            <h3 className="text-sm font-semibold text-zinc-950 dark:text-white">Pitfalls</h3>
            <ReactMarkdown className="markdown-body mt-3">{explanation?.pitfalls || "Pitfalls will appear when explanation generation completes."}</ReactMarkdown>
          </section>
        </div>
      </section>
    </div>
  );
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
