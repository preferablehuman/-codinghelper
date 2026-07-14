import { Database, ShieldCheck } from "lucide-react";
import type { JobDetail } from "../types/api";

const labels: Record<string, string> = {
  EXACT_REUSE: "Reused verified previous solution",
  EQUIVALENT_ADAPT: "Adapted from an equivalent verified problem",
  EXTERNAL_DISCOVERY: "Grounded in externally discovered knowledge",
  RELATED_GROUNDING: "Generated using related algorithm references",
  GENERATE_FRESH: "Generated without a reusable match"
};

export default function RetrievalProvenancePanel({ trace }: { trace: JobDetail["retrieval_trace"] }) {
  if (!trace) return null;
  return (
    <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50/70 p-4 dark:border-emerald-900/60 dark:bg-emerald-950/20">
      <div className="flex items-start gap-3">
        <Database className="mt-0.5 text-emerald-600" size={18} aria-hidden="true" />
        <div className="min-w-0 flex-1">
          <p className="font-medium text-zinc-950 dark:text-zinc-100">{labels[trace.route] || labels.GENERATE_FRESH}</p>
          <div className="mt-2 flex flex-wrap gap-2 font-mono text-xs text-zinc-600 dark:text-zinc-300">
            <span>{Math.round(trace.confidence * 100)}% match</span>
            <span>• {trace.asserting_test_count} asserting tests</span>
            <span>• {trace.verification_status || "verification pending"}</span>
            {trace.code_adapted ? <span>• code adapted</span> : null}
            {trace.external_discovery_used ? <span>• external discovery used</span> : null}
          </div>
          {trace.source_titles.length ? <p className="mt-2 truncate text-xs text-zinc-500">Sources: {trace.source_titles.join(", ")}</p> : null}
          <p className="mt-2 flex items-center gap-1 text-xs text-emerald-800 dark:text-emerald-200"><ShieldCheck size={13} /> Verified against the available test suite; not a formal proof.</p>
        </div>
      </div>
    </div>
  );
}
