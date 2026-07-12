import {
  BookOpenText,
  FileStack,
  FlaskConical,
  PlaySquare,
  RotateCcw,
  type LucideIcon
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import { getJob, getJobStatus, rerunJob } from "../api/client";
import CodeViewer from "../components/CodeViewer";
import ExplanationTabs from "../components/ExplanationTabs";
import JobProgress from "../components/JobProgress";
import RetrievalProvenancePanel from "../components/RetrievalProvenancePanel";
import SourceEvidencePanel from "../components/SourceEvidencePanel";
import TestResultPanel from "../components/TestResultPanel";
import type { JobDetail } from "../types/api";

const terminalStatuses = new Set(["COMPLETED", "FAILED"]);
const resultTabs: { id: string; label: string; icon: LucideIcon }[] = [
  { id: "explanation", label: "Explanation", icon: BookOpenText },
  { id: "code", label: "Code", icon: PlaySquare },
  { id: "tests", label: "Tests", icon: FlaskConical },
  { id: "sources", label: "Sources", icon: FileStack }
];

export default function JobResultPage() {
  const { jobId } = useParams();
  const [job, setJob] = useState<JobDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState("explanation");

  async function loadJob() {
    if (!jobId) {
      return;
    }
    try {
      setJob(await getJob(jobId));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load job");
    }
  }

  useEffect(() => {
    void loadJob();
  }, [jobId]);

  useEffect(() => {
    if (!job || terminalStatuses.has(job.status)) {
      return undefined;
    }
    const interval = window.setInterval(() => {
      if (!jobId) {
        return;
      }
      void getJobStatus(jobId)
        .then((status) => {
          setJob((current) =>
            current
              ? {
                  ...current,
                  status: status.status,
                  progress_percent: status.progress_percent,
                  current_step: status.current_step,
                  error_message: status.error_message
                }
              : current
          );
          if (terminalStatuses.has(status.status)) {
            void loadJob();
          }
        })
        .catch((err) => {
          setError(err instanceof Error ? err.message : "Unable to load job status");
        });
    }, 1500);
    return () => window.clearInterval(interval);
  }, [job?.id, job?.status, jobId]);

  const latestExplanation = useMemo(() => job?.explanations.at(-1), [job]);
  const latestSlide = useMemo(() => job?.slide_artifacts.at(-1), [job]);
  const verifiedSolutions = useMemo(() => job?.solutions.filter((solution) => solution.verification_status !== "FAILED") || [], [job]);

  if (error) {
    return <p className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-900/60 dark:bg-red-950/40 dark:text-red-200">{error}</p>;
  }

  if (!job) {
    return <p className="text-sm text-zinc-500 dark:text-zinc-400">Loading job...</p>;
  }

  return (
    <section className="min-h-[calc(100vh-7rem)] space-y-5">
      <div className="surface animate-rise-in p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-semibold text-zinc-950 dark:text-white">{job.title || "Untitled problem"}</h1>
            <span className="rounded-md border border-zinc-200 bg-zinc-50 px-2 py-1 font-mono text-xs text-zinc-600 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-300">
              {job.language}
            </span>
            <StatusPill status={job.status} />
          </div>
          <p className="mt-2 max-w-5xl text-base leading-7 text-zinc-600 dark:text-zinc-400">{job.problem_summary || job.problem_text.slice(0, 220)}</p>
        </div>
        <button
          type="button"
          onClick={() => jobId && rerunJob(jobId).then(loadJob)}
          className="focus-ring inline-flex h-10 items-center gap-2 rounded-md border border-zinc-300 bg-white px-3 text-sm text-zinc-700 transition hover:bg-zinc-100 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-200 dark:hover:bg-zinc-900"
        >
          <RotateCcw size={16} aria-hidden="true" />
          Rerun
        </button>
        </div>
        <div className="mt-5 grid gap-3 sm:grid-cols-3">
          <HeaderMetric label="Approaches" value={String(verifiedSolutions.length || 0)} />
          <HeaderMetric label="Tests" value={String(job.test_cases.length || 0)} />
          <HeaderMetric label="Pattern" value={job.detected_pattern || "detecting"} />
        </div>
        <RetrievalProvenancePanel trace={job.retrieval_trace} />
      </div>

      <JobProgress job={job} />

      <div className="grid gap-5 xl:grid-cols-[260px_minmax(0,1fr)]">
        <aside className="surface p-2 xl:sticky xl:top-24 xl:self-start">
          <div className="border-b border-zinc-200 px-3 py-3 dark:border-zinc-800">
            <p className="font-mono text-xs uppercase tracking-[0.2em] text-emerald-600">analysis</p>
            <p className="mt-1 text-sm font-medium text-zinc-950 dark:text-zinc-100">{job.detected_pattern || "pattern pending"}</p>
          </div>
          <nav className="mt-2 space-y-1">
            {resultTabs.map((tab) => {
              const Icon = tab.icon;
              const selected = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActiveTab(tab.id)}
                  className={`focus-ring flex h-11 w-full items-center gap-3 rounded-md px-3 text-left text-sm transition duration-200 ${
                    selected
                      ? "bg-zinc-950 text-emerald-300 shadow-sm dark:bg-white dark:text-zinc-950"
                      : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-950 dark:text-zinc-400 dark:hover:bg-zinc-900 dark:hover:text-zinc-100"
                  }`}
                >
                  <Icon size={16} aria-hidden="true" />
                  {tab.label}
                </button>
              );
            })}
          </nav>
        </aside>

        <div className="min-w-0 animate-fade-in">
          {activeTab === "explanation" ? (
            <ExplanationTabs
              explanation={latestExplanation}
              solutions={verifiedSolutions}
              tests={job.test_cases}
              verificationRuns={job.verification_runs}
              language={job.language}
              slide={latestSlide}
            />
          ) : null}
          {activeTab === "code" ? <CodeViewer solutions={verifiedSolutions} language={job.language} tests={job.test_cases} /> : null}
          {activeTab === "tests" ? (
            <TestResultPanel tests={job.test_cases} verificationRuns={job.verification_runs} solutions={verifiedSolutions} language={job.language} />
          ) : null}
          {activeTab === "sources" ? <SourceEvidencePanel sources={job.sources} evidence={job.evidence_items} /> : null}
        </div>
      </div>
    </section>
  );
}

function StatusPill({ status }: { status: string }) {
  const color =
    status === "COMPLETED"
      ? "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-200"
      : status === "FAILED"
        ? "border-red-200 bg-red-50 text-red-700 dark:border-red-900/60 dark:bg-red-950/40 dark:text-red-200"
        : "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-200";
  return <span className={`rounded-md border px-2 py-1 font-mono text-xs ${color}`}>{status}</span>;
}

function HeaderMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-zinc-200 bg-zinc-50 px-3 py-2 dark:border-zinc-800 dark:bg-zinc-900">
      <p className="text-xs uppercase tracking-wide text-zinc-500 dark:text-zinc-400">{label}</p>
      <p className="mt-1 truncate font-mono text-sm font-semibold text-zinc-950 dark:text-zinc-100">{value}</p>
    </div>
  );
}
