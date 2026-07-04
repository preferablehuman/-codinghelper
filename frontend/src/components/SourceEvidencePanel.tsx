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
      <section className="rounded-md border border-slate-200 bg-white">
        <div className="border-b border-slate-200 px-4 py-3">
          <h2 className="text-sm font-semibold">Sources</h2>
        </div>
        <div className="divide-y divide-slate-100">
          {sources.length === 0 ? (
            <p className="p-4 text-sm text-slate-500">Sources will appear after retrieval.</p>
          ) : (
            sources.map((source) => (
              <div key={source.id} className="p-4">
                <a href={source.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 font-medium text-teal-700 hover:text-teal-900">
                  {source.title}
                  <ExternalLink size={14} aria-hidden="true" />
                </a>
                <p className="mt-1 text-xs text-slate-500">
                  {source.source_name} · tier {source.source_tier} · {source.retrieval_method}
                </p>
                {source.license_note ? <p className="mt-2 text-xs text-slate-600">{source.license_note}</p> : null}
              </div>
            ))
          )}
        </div>
      </section>
      <section className="rounded-md border border-slate-200 bg-white">
        <div className="border-b border-slate-200 px-4 py-3">
          <h2 className="text-sm font-semibold">Evidence Claims</h2>
        </div>
        <div className="divide-y divide-slate-100">
          {evidence.length === 0 ? (
            <p className="p-4 text-sm text-slate-500">Evidence will appear after chunking.</p>
          ) : (
            evidence.map((item) => (
              <div key={item.id} className="p-4">
                <p className="text-sm text-slate-800">{item.claim}</p>
                <p className="mt-2 text-xs text-slate-500">Support score: {item.support_score.toFixed(2)}</p>
              </div>
            ))
          )}
        </div>
      </section>
    </div>
  );
}

