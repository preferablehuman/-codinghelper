import ReactMarkdown from "react-markdown";

import type { Explanation, GeneratedSolution } from "../types/api";

export default function ExplanationTabs({
  explanation,
  solution
}: {
  explanation?: Explanation;
  solution?: GeneratedSolution;
}) {
  if (!explanation && !solution) {
    return <p className="text-sm text-slate-500">Explanation will appear when generation completes.</p>;
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <section className="rounded-md border border-slate-200 bg-white p-4">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Intuition</h2>
        <ReactMarkdown className="prose prose-sm mt-3 max-w-none">{explanation?.intuition || solution?.explanation || ""}</ReactMarkdown>
      </section>
      <section className="rounded-md border border-slate-200 bg-white p-4">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Optimized approach</h2>
        <ReactMarkdown className="prose prose-sm mt-3 max-w-none">{explanation?.optimized_approach || ""}</ReactMarkdown>
      </section>
      <section className="rounded-md border border-slate-200 bg-white p-4">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Brute force</h2>
        <ReactMarkdown className="prose prose-sm mt-3 max-w-none">{explanation?.brute_force || ""}</ReactMarkdown>
      </section>
      <section className="rounded-md border border-slate-200 bg-white p-4">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Complexity</h2>
        <ReactMarkdown className="prose prose-sm mt-3 max-w-none">{explanation?.complexity_analysis || ""}</ReactMarkdown>
      </section>
    </div>
  );
}

