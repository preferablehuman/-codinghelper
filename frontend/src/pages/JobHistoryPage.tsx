import { BrainCircuit, RefreshCw, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { deleteJob, listJobs } from "../api/client";
import type { JobListItem } from "../types/api";

export default function JobHistoryPage() {
  const [jobs, setJobs] = useState<JobListItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function loadJobs() {
    setLoading(true);
    setError(null);
    try {
      setJobs(await listJobs());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load jobs");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadJobs();
  }, []);

  async function handleDelete(jobId: string) {
    await deleteJob(jobId);
    setJobs((current) => current.filter((job) => job.id !== jobId));
  }

  return (
    <section className="animate-rise-in">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-950 dark:text-white">Job History</h1>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">Past explanations and verification runs.</p>
        </div>
        <button
          type="button"
          onClick={() => void loadJobs()}
          className="focus-ring inline-flex h-10 items-center gap-2 rounded-md border border-zinc-300 bg-white px-3 text-sm text-zinc-700 transition hover:bg-zinc-100 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-200 dark:hover:bg-zinc-900"
        >
          <RefreshCw size={16} aria-hidden="true" />
          Refresh
        </button>
      </div>
      {error ? <p className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-900/60 dark:bg-red-950/40 dark:text-red-200">{error}</p> : null}
      <div className="surface overflow-hidden">
        <table className="min-w-full divide-y divide-zinc-200 text-sm dark:divide-zinc-800">
          <thead className="bg-zinc-100 text-left text-xs uppercase tracking-wide text-zinc-500 dark:bg-zinc-900 dark:text-zinc-400">
            <tr>
              <th className="px-5 py-3">Problem</th>
              <th className="px-5 py-3">Status</th>
              <th className="px-5 py-3">Language</th>
              <th className="px-5 py-3">Pattern</th>
              <th className="px-5 py-3">Created</th>
              <th className="px-5 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
            {loading ? (
              <tr>
                <td className="px-5 py-8 text-center text-zinc-500 dark:text-zinc-400" colSpan={6}>
                  Loading jobs...
                </td>
              </tr>
            ) : jobs.length === 0 ? (
              <tr>
                <td className="px-5 py-8 text-center text-zinc-500 dark:text-zinc-400" colSpan={6}>
                  No jobs yet.
                </td>
              </tr>
            ) : (
              jobs.map((job) => (
                <tr key={job.id} className="transition hover:bg-zinc-50 dark:hover:bg-zinc-900">
                  <td className="px-5 py-4">
                    <Link to={`/jobs/${job.id}`} className="font-medium text-emerald-700 hover:text-emerald-900 dark:text-emerald-300 dark:hover:text-emerald-200">
                      {job.title || "Untitled problem"}
                    </Link>
                    <p className="text-xs text-zinc-500 dark:text-zinc-400">{job.current_step}</p>
                  </td>
                  <td className="px-5 py-4 text-zinc-700 dark:text-zinc-300">{job.status}</td>
                  <td className="px-5 py-4 text-zinc-700 dark:text-zinc-300">{job.language}</td>
                  <td className="px-5 py-4 text-zinc-700 dark:text-zinc-300">
                    {job.detected_pattern ? (
                      <Link to={`/jobs/${job.id}?tab=pattern`} className="focus-ring inline-flex items-center gap-2 rounded-md border border-emerald-200 bg-emerald-50 px-2 py-1 font-mono text-xs text-emerald-700 transition hover:bg-emerald-100 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-200 dark:hover:bg-emerald-950/70">
                        <BrainCircuit size={13} aria-hidden="true" />
                        {job.detected_pattern}
                      </Link>
                    ) : "-"}
                  </td>
                  <td className="px-5 py-4 text-zinc-700 dark:text-zinc-300">{new Date(job.created_at).toLocaleString()}</td>
                  <td className="px-5 py-4 text-right">
                    <button
                      type="button"
                      onClick={() => void handleDelete(job.id)}
                      className="focus-ring inline-flex h-9 w-9 items-center justify-center rounded-md border border-zinc-300 text-zinc-600 transition hover:bg-red-50 hover:text-red-700 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-red-950/40 dark:hover:text-red-200"
                      title="Delete job"
                    >
                      <Trash2 size={15} aria-hidden="true" />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
