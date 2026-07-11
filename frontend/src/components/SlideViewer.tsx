import { Download, ExternalLink, ListChecks, Presentation, Route } from "lucide-react";

import type { SlideArtifact } from "../types/api";

export default function SlideViewer({ slide }: { slide?: SlideArtifact }) {
  if (!slide) {
    return <p className="text-sm text-zinc-500 dark:text-zinc-400">Slides will appear when slide generation completes.</p>;
  }

  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_380px]">
      <section className="surface overflow-hidden">
        <div className="border-b border-zinc-200 px-5 py-4 dark:border-zinc-800">
          <h2 className="flex items-center gap-2 text-base font-semibold text-zinc-950 dark:text-white">
            <Presentation size={18} className="text-emerald-500" aria-hidden="true" />
            Presentation deck
          </h2>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">Generated as a real PowerPoint deck with a rendered browser preview.</p>
        </div>
        <div className="grid gap-4 p-5 md:grid-cols-2">
          {slide.pptx_path ? (
            <a
              href={slide.pptx_path}
              target="_blank"
              rel="noreferrer"
              className="focus-ring group rounded-md border border-emerald-200 bg-emerald-50 p-5 transition duration-200 hover:-translate-y-0.5 hover:border-emerald-300 hover:bg-emerald-100 dark:border-emerald-900/60 dark:bg-emerald-950/30 dark:hover:bg-emerald-950/50"
            >
              <Download size={22} className="text-emerald-700 dark:text-emerald-300" aria-hidden="true" />
              <p className="mt-4 text-lg font-semibold text-zinc-950 dark:text-white">Download PPTX</p>
              <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">Open the deck in PowerPoint or compatible editors.</p>
            </a>
          ) : null}
          {slide.html_path ? (
            <a
              href={slide.html_path}
              target="_blank"
              rel="noreferrer"
              className="focus-ring group rounded-md border border-cyan-200 bg-cyan-50 p-5 transition duration-200 hover:-translate-y-0.5 hover:border-cyan-300 hover:bg-cyan-100 dark:border-cyan-900/60 dark:bg-cyan-950/30 dark:hover:bg-cyan-950/50"
            >
              <ExternalLink size={22} className="text-cyan-700 dark:text-cyan-300" aria-hidden="true" />
              <p className="mt-4 text-lg font-semibold text-zinc-950 dark:text-white">Open preview</p>
              <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">Review the rendered slide sequence in the browser.</p>
            </a>
          ) : null}
        </div>
        <div className="border-t border-zinc-200 px-5 py-4 dark:border-zinc-800">
          <p className="text-xs font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">Markdown artifact</p>
          <p className="mt-2 break-all font-mono text-xs text-zinc-700 dark:text-zinc-300">{slide.markdown_path}</p>
        </div>
      </section>

      <aside className="space-y-4">
        <section className="surface p-5">
          <h3 className="flex items-center gap-2 text-sm font-semibold text-zinc-950 dark:text-white">
            <ListChecks size={16} className="text-emerald-500" aria-hidden="true" />
            Deck sections
          </h3>
          <ul className="mt-4 space-y-2 text-sm text-zinc-700 dark:text-zinc-300">
            <DeckItem label="Problem framing" />
            <DeckItem label="Approach ladder" />
            <DeckItem label="Brute force baseline" />
            <DeckItem label="Improved approach" />
            <DeckItem label="Expected solution" />
            <DeckItem label="Step-by-step dry run" />
            <DeckItem label="Code logic trace" />
            <DeckItem label="Complexity and tests" />
          </ul>
        </section>
        <section className="surface p-5">
          <h3 className="flex items-center gap-2 text-sm font-semibold text-zinc-950 dark:text-white">
            <Route size={16} className="text-amber-600 dark:text-amber-300" aria-hidden="true" />
            Dry-run requirement
          </h3>
          <p className="mt-3 text-sm leading-6 text-zinc-600 dark:text-zinc-400">
            Every generated deck now includes a visual step table plus a code logic trace so learners can follow the execution path without leaving the slides.
          </p>
        </section>
      </aside>
    </div>
  );
}

function DeckItem({ label }: { label: string }) {
  return (
    <li className="flex items-center gap-2">
      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" aria-hidden="true" />
      <span>{label}</span>
    </li>
  );
}
