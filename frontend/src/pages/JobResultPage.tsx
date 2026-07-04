import { RotateCcw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import { getJob, getJobStatus, rerunJob } from "../api/client";
import CodeViewer from "../components/CodeViewer";
import DryRunVisualizer from "../components/DryRunVisualizer";
import ExplanationTabs from "../components/ExplanationTabs";
import JobProgress from "../components/JobProgress";
import SlideViewer from "../components/SlideViewer";
import SourceEvidencePanel from "../components/SourceEvidencePanel";
import TestResultPanel from "../components/TestResultPanel";
import type { JobDetail } from "../types/api";

const terminalStatuses = new Set(["COMPLETED", "FAILED"]);

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

  const latestSolution = useMemo(() => job?.solutions.at(-1), [job]);
  const latestExplanation = useMemo(() => job?.explanations.at(-1), [job]);
  const latestSlide = useMemo(() => job?.slide_artifacts.at(-1), [job]);

  if (error) {
    return <p className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p>;
  }

  if (!job) {
    return <p className="text-sm text-slate-500">Loading job...</p>;
  }

  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">{job.title || "Untitled problem"}</h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-600">{job.problem_summary || job.problem_text.slice(0, 220)}</p>
        </div>
        <button
          type="button"
          onClick={() => jobId && rerunJob(jobId).then(loadJob)}
          className="focus-ring inline-flex h-9 items-center gap-2 rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-700 hover:bg-slate-100"
        >
          <RotateCcw size={16} aria-hidden="true" />
          Rerun
        </button>
      </div>

      <JobProgress job={job} />

      <div className="border-b border-slate-200">
        <nav className="flex flex-wrap gap-5 text-sm">
          {["explanation", "code", "tests", "sources", "dry-run", "slides"].map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              className={`border-b-2 px-1 py-3 capitalize ${
                activeTab === tab ? "border-teal-600 text-teal-700" : "border-transparent text-slate-600 hover:text-slate-900"
              }`}
            >
              {tab.replace("-", " ")}
            </button>
          ))}
        </nav>
      </div>

      {activeTab === "explanation" ? <ExplanationTabs explanation={latestExplanation} solution={latestSolution} /> : null}
      {activeTab === "code" ? <CodeViewer solution={latestSolution} language={job.language} /> : null}
      {activeTab === "tests" ? <TestResultPanel tests={job.test_cases} verificationRuns={job.verification_runs} /> : null}
      {activeTab === "sources" ? <SourceEvidencePanel sources={job.sources} evidence={job.evidence_items} /> : null}
      {activeTab === "dry-run" ? <DryRunVisualizer explanation={latestExplanation} /> : null}
      {activeTab === "slides" ? <SlideViewer slide={latestSlide} /> : null}
    </section>
  );
}
