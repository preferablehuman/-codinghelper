import type { JobDetail } from "../types/api";

export default function JobProgress({ job }: { job: JobDetail }) {
  const statusClass =
    job.status === "FAILED"
      ? "bg-red-100 text-red-700 border-red-200"
      : job.status === "COMPLETED"
        ? "bg-emerald-100 text-emerald-700 border-emerald-200"
        : "bg-amber-100 text-amber-800 border-amber-200";

  return (
    <div className="rounded-md border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-slate-900">{job.current_step}</p>
          <p className="text-xs text-slate-500">Pattern: {job.detected_pattern || "detecting"}</p>
        </div>
        <span className={`rounded-md border px-2.5 py-1 text-xs font-medium ${statusClass}`}>{job.status}</span>
      </div>
      <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
        <div className="h-full bg-teal-600 transition-all" style={{ width: `${job.progress_percent}%` }} />
      </div>
      {job.error_message ? <p className="mt-2 text-sm text-red-700">{job.error_message}</p> : null}
    </div>
  );
}

