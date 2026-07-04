import ReactMarkdown from "react-markdown";

import type { Explanation } from "../types/api";

export default function DryRunVisualizer({ explanation }: { explanation?: Explanation }) {
  if (!explanation) {
    return <p className="text-sm text-slate-500">Dry run will appear when explanation generation completes.</p>;
  }
  return (
    <section className="rounded-md border border-slate-200 bg-white p-4">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Dry Run</h2>
      <ReactMarkdown className="prose prose-sm mt-3 max-w-none">{explanation.dry_run}</ReactMarkdown>
      <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">{explanation.pitfalls}</div>
    </section>
  );
}

