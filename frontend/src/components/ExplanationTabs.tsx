import ReactMarkdown from "react-markdown";
import { Download, ExternalLink, FileDown, Play, Route } from "lucide-react";
import { useMemo, useState } from "react";

import { executeCode } from "../api/client";
import type { ExecutionResponse, Explanation, GeneratedSolution, SlideArtifact, TestCase, VerificationRun } from "../types/api";

const APPROACH_ORDER: Record<string, number> = {
  BRUTE_FORCE: 0,
  NAIVE: 0,
  IMPROVED: 1,
  AVERAGE: 1,
  OPTIMAL: 2,
  EXPECTED: 2,
  FINAL: 3
};

interface IllustrationRow {
  step: string;
  input: string;
  state: string;
  action: string;
  result: string;
}

export default function ExplanationTabs({
  explanation,
  solutions = [],
  tests = [],
  verificationRuns = [],
  language,
  slide
}: {
  explanation?: Explanation;
  solutions?: GeneratedSolution[];
  tests?: TestCase[];
  verificationRuns?: VerificationRun[];
  language: string;
  slide?: SlideArtifact;
}) {
  const orderedSolutions = useMemo(() => orderSolutions(solutions), [solutions]);
  const preferred = useMemo(() => preferredSolution(orderedSolutions), [orderedSolutions]);
  const [activeId, setActiveId] = useState<string | null>(preferred?.id ?? null);
  const activeSolution = orderedSolutions.find((solution) => solution.id === activeId) ?? preferred;
  const activeDryRun = useMemo(
    () => extractApproachMarkdown(explanation?.dry_run || "", activeSolution?.approach_type || ""),
    [activeSolution?.approach_type, explanation?.dry_run]
  );
  const illustrationRows = useMemo(
    () => buildIllustrationRows(activeDryRun, activeSolution),
    [activeDryRun, activeSolution]
  );
  const latestVerification = verificationRuns.at(-1);
  const [running, setRunning] = useState(false);
  const [runResult, setRunResult] = useState<ExecutionResponse | null>(null);
  const [runError, setRunError] = useState<string | null>(null);

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

  function handleDownloadIllustration() {
    if (!activeSolution) {
      return;
    }
    const svg = buildIllustrationSvg(activeSolution, illustrationRows);
    const blob = new Blob([svg], { type: "image/svg+xml" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${approachLabel(activeSolution.approach_type).toLowerCase().replace(/\s+/g, "-")}-illustration.svg`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-5">
      <section className="surface p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-zinc-950 dark:text-white">Explanation workspace</h2>
            <p className="mt-1 max-w-3xl text-sm leading-6 text-zinc-600 dark:text-zinc-400">
              Select a solution, inspect the reasoning, run the generated tests, and download the teaching artifacts from one place.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={handleDownloadIllustration}
              disabled={!activeSolution}
              className="focus-ring inline-flex h-10 items-center gap-2 rounded-md border border-zinc-300 bg-white px-3 text-sm font-semibold text-zinc-800 transition hover:bg-zinc-100 disabled:cursor-not-allowed disabled:text-zinc-400 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-100 dark:hover:bg-zinc-900"
            >
              <Download size={15} aria-hidden="true" />
              Illustration SVG
            </button>
            {slide?.pptx_path ? (
              <a
                href={slide.pptx_path}
                target="_blank"
                rel="noreferrer"
                className="focus-ring inline-flex h-10 items-center gap-2 rounded-md bg-emerald-600 px-3 text-sm font-semibold text-white transition hover:bg-emerald-700"
              >
                <FileDown size={15} aria-hidden="true" />
                PPTX
              </a>
            ) : null}
            {slide?.html_path ? (
              <a
                href={slide.html_path}
                target="_blank"
                rel="noreferrer"
                className="focus-ring inline-flex h-10 items-center gap-2 rounded-md border border-zinc-300 bg-white px-3 text-sm font-semibold text-zinc-800 transition hover:bg-zinc-100 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-100 dark:hover:bg-zinc-900"
              >
                <ExternalLink size={15} aria-hidden="true" />
                Preview
              </a>
            ) : null}
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
                className={`focus-ring min-h-[126px] rounded-md border p-3 text-left transition duration-200 hover:-translate-y-0.5 ${
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

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_420px]">
        <section className="space-y-5">
          <section className="surface p-5">
            <h3 className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-emerald-600">Reasoning</h3>
            <ReactMarkdown className="markdown-body mt-3">{activeSolution?.explanation || explanation?.intuition || ""}</ReactMarkdown>
          </section>

          <section className="surface overflow-hidden">
            <div className="border-b border-zinc-200 px-5 py-4 dark:border-zinc-800">
              <h3 className="flex items-center gap-2 text-base font-semibold text-zinc-950 dark:text-white">
                <Route size={18} className="text-emerald-500" aria-hidden="true" />
                Dry run and code logic
              </h3>
            </div>
            <div className="grid gap-5 p-5 lg:grid-cols-[320px_minmax(0,1fr)]">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">Logic stub</p>
                <pre className="mt-2 max-h-[420px] overflow-auto whitespace-pre-wrap rounded-md bg-zinc-950 p-4 font-mono text-xs leading-5 text-zinc-100">
                  {activeSolution?.pseudocode || "Read input\nTrack state\nMake decision\nReturn answer"}
                </pre>
              </div>
              <ReactMarkdown className="markdown-body min-w-0">{activeDryRun || explanation?.dry_run || ""}</ReactMarkdown>
            </div>
          </section>

          <section className="surface overflow-hidden">
            <div className="border-b border-zinc-200 px-5 py-4 dark:border-zinc-800">
              <h3 className="text-base font-semibold text-zinc-950 dark:text-white">Illustration</h3>
              <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">Step-by-step state changes in the same spirit as GFG illustrations.</p>
            </div>
            <Illustration rows={illustrationRows} />
          </section>
        </section>

        <aside className="space-y-4">
          <section className="surface p-4">
            <h3 className="text-sm font-semibold text-zinc-950 dark:text-white">Proof run</h3>
            <p className="mt-2 text-sm leading-6 text-zinc-600 dark:text-zinc-400">
              Execute the selected solution against every generated test and inspect the aggregate timing.
            </p>
            <button
              type="button"
              onClick={() => void handleRunGeneratedTests()}
              disabled={running || !activeSolution || tests.length === 0}
              className="focus-ring mt-4 inline-flex h-11 w-full items-center justify-center gap-2 rounded-md bg-emerald-600 px-4 text-sm font-semibold text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-zinc-400"
            >
              <Play size={16} aria-hidden="true" />
              {running ? "Running..." : `Execute ${tests.length} tests`}
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

          <section className="surface p-4">
            <h3 className="text-sm font-semibold text-zinc-950 dark:text-white">Pitfalls</h3>
            <ReactMarkdown className="markdown-body mt-3">{explanation?.pitfalls || "Pitfalls will appear when explanation generation completes."}</ReactMarkdown>
          </section>

          <section className="surface p-4">
            <h3 className="text-sm font-semibold text-zinc-950 dark:text-white">Complexity</h3>
            <ReactMarkdown className="markdown-body mt-3">
              {explanation?.complexity_analysis || `${activeSolution?.time_complexity ?? ""}\n\n${activeSolution?.space_complexity ?? ""}`}
            </ReactMarkdown>
          </section>
        </aside>
      </div>
    </div>
  );
}

function Illustration({ rows }: { rows: IllustrationRow[] }) {
  return (
    <div className="grid gap-3 p-5 md:grid-cols-2 xl:grid-cols-3">
      {rows.map((row, index) => (
        <div key={`${row.step}-${index}`} className="min-w-0 overflow-hidden rounded-md border border-zinc-200 bg-zinc-50 p-4 dark:border-zinc-800 dark:bg-zinc-900">
          <div className="flex items-center justify-between gap-3">
            <span className="font-mono text-xs font-semibold text-emerald-600 dark:text-emerald-300">Step {row.step || index + 1}</span>
            <span className="rounded-md bg-zinc-950 px-2 py-1 font-mono text-xs text-zinc-100">{row.input || "-"}</span>
          </div>
          <p className="mt-3 max-w-full break-all text-sm font-semibold text-zinc-950 [overflow-wrap:anywhere] dark:text-zinc-100">{row.action || "Inspect state"}</p>
          <p className="mt-2 max-w-full break-all font-mono text-xs leading-5 text-zinc-600 [overflow-wrap:anywhere] dark:text-zinc-400">state: {row.state || "-"}</p>
          <p className="mt-2 max-w-full break-all text-sm text-zinc-600 [overflow-wrap:anywhere] dark:text-zinc-300">{row.result || "Continue"}</p>
        </div>
      ))}
    </div>
  );
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

function buildIllustrationRows(markdown: string, solution?: GeneratedSolution): IllustrationRow[] {
  const tableRows = parseMarkdownTable(markdown);
  if (tableRows.length) {
    return tableRows.slice(0, 9);
  }
  const lines = (solution?.pseudocode || "")
    .split(/\r?\n/)
    .map((line) => line.replace(/^\d+[.)]\s*/, "").trim())
    .filter(Boolean)
    .slice(0, 6);
  const sourceLines = lines.length ? lines : ["Read input", "Initialize state", "Process each item", "Return answer"];
  return sourceLines.map((line, index) => ({
    step: String(index + 1),
    input: index === 0 ? "input" : "",
    state: index === 0 ? "empty" : "updated",
    action: line,
    result: index === sourceLines.length - 1 ? "answer ready" : "continue"
  }));
}

function parseMarkdownTable(markdown: string): IllustrationRow[] {
  const lines = markdown.split(/\r?\n/).filter((line) => line.trim().startsWith("|"));
  if (lines.length < 2) {
    return [];
  }
  const rows = lines
    .filter((line) => !/^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?$/.test(line.trim()))
    .map((line) =>
      line
        .replace(/^\|/, "")
        .replace(/\|$/, "")
        .split("|")
        .map((cell) => cell.trim())
    );
  const body = rows.slice(1);
  return body.map((row, index) => ({
    step: row[0] || String(index + 1),
    input: row[1] || "",
    state: row[2] || "",
    action: row[3] || "",
    result: row[4] || ""
  }));
}

function buildIllustrationSvg(solution: GeneratedSolution, rows: IllustrationRow[]): string {
  const width = 1180;
  const rowHeight = 92;
  const height = 130 + Math.max(rows.length, 1) * rowHeight;
  const cards = rows
    .map((row, index) => {
      const y = 96 + index * rowHeight;
      return `<g>
  <rect x="36" y="${y}" width="1108" height="72" rx="10" fill="${index % 2 === 0 ? "#ecfdf5" : "#eff6ff"}" stroke="#d4d4d8"/>
  <text x="58" y="${y + 27}" font-family="Consolas, monospace" font-size="16" fill="#047857">Step ${escapeSvg(row.step || String(index + 1))}</text>
  <text x="190" y="${y + 27}" font-family="Inter, Arial" font-size="16" fill="#18181b">${escapeSvg(row.action || "Inspect state")}</text>
  <text x="190" y="${y + 52}" font-family="Consolas, monospace" font-size="14" fill="#52525b">input=${escapeSvg(row.input || "-")} | state=${escapeSvg(row.state || "-")} | result=${escapeSvg(row.result || "-")}</text>
</g>`;
    })
    .join("\n");
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
  <rect width="100%" height="100%" fill="#fafafa"/>
  <text x="36" y="44" font-family="Inter, Arial" font-size="28" font-weight="700" fill="#18181b">${escapeSvg(approachLabel(solution.approach_type))} Illustration</text>
  <text x="36" y="74" font-family="Consolas, monospace" font-size="16" fill="#52525b">${escapeSvg(solution.algorithm_pattern)} - ${escapeSvg(solution.time_complexity)} time / ${escapeSvg(solution.space_complexity)} space</text>
  ${cards}
</svg>`;
}

function escapeSvg(value: string): string {
  return value.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
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
