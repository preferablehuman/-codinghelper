import { Download, ExternalLink } from "lucide-react";

import type { SlideArtifact } from "../types/api";

export default function SlideViewer({ slide }: { slide?: SlideArtifact }) {
  if (!slide) {
    return <p className="text-sm text-slate-500">Slides will appear when slide generation completes.</p>;
  }
  return (
    <section className="rounded-md border border-slate-200 bg-white p-4">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Slides</h2>
      <dl className="mt-3 grid gap-3 text-sm">
        <div>
          <dt className="text-xs uppercase tracking-wide text-slate-500">Markdown artifact</dt>
          <dd className="mt-1 font-mono text-xs text-slate-700">{slide.markdown_path}</dd>
        </div>
        {slide.html_path ? (
          <div>
            <dt className="text-xs uppercase tracking-wide text-slate-500">HTML preview</dt>
            <dd className="mt-1">
              <a href={slide.html_path} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 text-teal-700 hover:text-teal-900">
                Open rendered slides
                <ExternalLink size={14} aria-hidden="true" />
              </a>
            </dd>
          </div>
        ) : null}
        {slide.pptx_path ? (
          <div>
            <dt className="text-xs uppercase tracking-wide text-slate-500">PowerPoint deck</dt>
            <dd className="mt-1">
              <a href={slide.pptx_path} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 text-teal-700 hover:text-teal-900">
                Download PPTX
                <Download size={14} aria-hidden="true" />
              </a>
            </dd>
          </div>
        ) : null}
      </dl>
    </section>
  );
}
