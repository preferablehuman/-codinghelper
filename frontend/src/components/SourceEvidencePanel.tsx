import { ExternalLink } from "lucide-react";

import type { EvidenceItem, SourceDocument } from "../types/api";

export default function SourceEvidencePanel({
  sources,
  evidence
}: {
  sources: SourceDocument[];
  evidence: EvidenceItem[];
}) {
  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_420px]">
      <section className="surface overflow-hidden">
        <div className="border-b border-zinc-200 px-5 py-4 dark:border-zinc-800">
          <h2 className="text-sm font-semibold text-zinc-950 dark:text-white">Sources</h2>
        </div>
        <div className="divide-y divide-zinc-100 dark:divide-zinc-800">
          {sources.length === 0 ? (
            <p className="p-4 text-sm text-zinc-500 dark:text-zinc-400">Sources will appear after retrieval.</p>
          ) : (
            sources.map((source) => (
              <div key={source.id} className="p-5">
                <a
                  href={source.url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-2 font-medium text-emerald-700 hover:text-emerald-900 dark:text-emerald-300 dark:hover:text-emerald-200"
                >
                  {source.title}
                  <ExternalLink size={14} aria-hidden="true" />
                </a>
                <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
                  {source.source_name} - tier {source.source_tier} - {source.retrieval_method}
                </p>
                {source.license_note ? <p className="mt-2 text-xs text-zinc-600 dark:text-zinc-400">{source.license_note}</p> : null}
              </div>
            ))
          )}
        </div>
      </section>
      <section className="surface overflow-hidden">
        <div className="border-b border-zinc-200 px-5 py-4 dark:border-zinc-800">
          <h2 className="text-sm font-semibold text-zinc-950 dark:text-white">Evidence Claims</h2>
        </div>
        <div className="divide-y divide-zinc-100 dark:divide-zinc-800">
          {evidence.length === 0 ? (
            <p className="p-4 text-sm text-zinc-500 dark:text-zinc-400">Evidence will appear after chunking.</p>
          ) : (
            evidence.map((item) => (
              <div key={item.id} className="p-5">
                <p className="text-sm leading-6 text-zinc-800 dark:text-zinc-200">{item.claim}</p>
                <p className="mt-2 text-xs text-zinc-500 dark:text-zinc-400">Support score: {item.support_score.toFixed(2)}</p>
              </div>
            ))
          )}
        </div>
      </section>
    </div>
  );
}
