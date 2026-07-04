import { RefreshCw, Trash2 } from "lucide-react";
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
    <section>
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Job History</h1>
          <p className="text-sm text-slate-500">Past explanations and verification runs.</p>
        </div>
        <button
          type="button"
          onClick={() => void loadJobs()}
          className="focus-ring inline-flex h-9 items-center gap-2 rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-700 hover:bg-slate-100"
        >
          <RefreshCw size={16} aria-hidden="true" />
          Refresh
        </button>
      </div>
      {error ? <p className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}
      <div className="overflow-hidden rounded-md border border-slate-200 bg-white">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-100 text-left text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3">Problem</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Language</th>
              <th className="px-4 py-3">Pattern</th>
              <th className="px-4 py-3">Created</th>
              <th className="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading ? (
              <tr>
                <td className="px-4 py-8 text-center text-slate-500" colSpan={6}>
                  Loading jobs...
                </td>
              </tr>
            ) : jobs.length === 0 ? (
              <tr>
                <td className="px-4 py-8 text-center text-slate-500" colSpan={6}>
                  No jobs yet.
                </td>
              </tr>
            ) : (
              jobs.map((job) => (
                <tr key={job.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <Link to={`/jobs/${job.id}`} className="font-medium text-teal-700 hover:text-teal-900">
                      {job.title || "Untitled problem"}
                    </Link>
                    <p className="text-xs text-slate-500">{job.current_step}</p>
                  </td>
                  <td className="px-4 py-3">{job.status}</td>
                  <td className="px-4 py-3">{job.language}</td>
                  <td className="px-4 py-3">{job.detected_pattern || "-"}</td>
                  <td className="px-4 py-3">{new Date(job.created_at).toLocaleString()}</td>
                  <td className="px-4 py-3 text-right">
                    <button
                      type="button"
                      onClick={() => void handleDelete(job.id)}
                      className="focus-ring inline-flex h-8 w-8 items-center justify-center rounded-md border border-slate-300 text-slate-600 hover:bg-red-50 hover:text-red-700"
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

