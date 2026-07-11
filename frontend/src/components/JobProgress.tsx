import type { JobDetail } from "../types/api";

export default function JobProgress({ job }: { job: JobDetail }) {
  const statusClass =
    job.status === "FAILED"
      ? "bg-red-100 text-red-700 border-red-200 dark:bg-red-950/50 dark:text-red-200 dark:border-red-900/70"
      : job.status === "COMPLETED"
        ? "bg-emerald-100 text-emerald-700 border-emerald-200 dark:bg-emerald-950/50 dark:text-emerald-200 dark:border-emerald-900/70"
        : "bg-amber-100 text-amber-800 border-amber-200 dark:bg-amber-950/50 dark:text-amber-200 dark:border-amber-900/70";

  return (
    <div className="surface p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100">{job.current_step}</p>
          <p className="font-mono text-xs text-zinc-500 dark:text-zinc-400">pattern: {job.detected_pattern || "detecting"}</p>
        </div>
        <span className={`rounded-md border px-2.5 py-1 text-xs font-medium ${statusClass}`}>{job.status}</span>
      </div>
      <div className="mt-3 h-2 overflow-hidden rounded-full bg-zinc-100 dark:bg-zinc-800">
        <div className="h-full bg-emerald-600 transition-all duration-500 ease-out" style={{ width: `${job.progress_percent}%` }} />
      </div>
      {job.error_message ? <p className="mt-2 text-sm text-red-700 dark:text-red-300">{job.error_message}</p> : null}
    </div>
  );
}
