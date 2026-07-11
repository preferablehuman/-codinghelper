import { BookOpenCheck, Braces, Cloud, Cpu, Database, ShieldCheck, Sparkles } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";

import { getHealth } from "../api/client";
import ProblemForm from "../components/ProblemForm";
import type { HealthResponse } from "../types/api";

export default function ProblemInputPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    void getHealth().then(setHealth).catch(() => setHealth(null));
  }, []);

  const providerName = health?.model.provider || health?.model_provider || "model gateway";
  const providerLabel = providerName
    .split(/[-_]/g)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
  const isRemote = Boolean(health?.model.remote);
  const runtimeLabel = health
    ? `${providerLabel} · ${health.model.model || "not configured"}`
    : "Checking gateway…";

  return (
    <div className="space-y-6">
      <section className="relative overflow-hidden rounded-2xl border border-zinc-200 bg-zinc-950 px-6 py-8 text-white shadow-xl shadow-zinc-950/10 sm:px-8 dark:border-zinc-800">
        <div className="absolute -right-20 -top-28 h-72 w-72 rounded-full bg-emerald-400/15 blur-3xl" />
        <div className="absolute -bottom-32 left-1/3 h-64 w-64 rounded-full bg-cyan-400/10 blur-3xl" />
        <div className="relative max-w-4xl">
          <div className="inline-flex items-center gap-2 rounded-full border border-emerald-400/20 bg-emerald-400/10 px-3 py-1.5 text-xs font-medium text-emerald-200">
            <Sparkles size={14} aria-hidden="true" />
            From problem statement to verified understanding
          </div>
          <h1 className="mt-5 text-3xl font-semibold tracking-tight sm:text-5xl">
            Learn the path from brute force to optimal.
          </h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-zinc-300 sm:text-lg">
            Generate distinct solution approaches, test executable code, and see the reasoning that connects each improvement.
          </p>
        </div>
      </section>

      <div className="grid min-h-[calc(100vh-24rem)] gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <section className="surface animate-rise-in rounded-2xl p-5 sm:p-7">
          <ProblemForm />
        </section>
        <aside className="space-y-5">
          <section className="surface rounded-2xl p-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-zinc-500 dark:text-zinc-400">Runtime</p>
                <h2 className="mt-2 text-base font-semibold text-zinc-950 dark:text-white">Generation route</h2>
              </div>
              <span className={`mt-1 h-2.5 w-2.5 rounded-full ${health?.model.loaded ? "bg-emerald-500 shadow-[0_0_0_5px_rgba(16,185,129,0.12)]" : "bg-amber-400"}`} />
            </div>
            <div className="mt-5 space-y-3">
              <StatusLine icon={isRemote ? <Cloud size={16} aria-hidden="true" /> : <Cpu size={16} aria-hidden="true" />} label="Model" value={runtimeLabel} />
              <StatusLine icon={<ShieldCheck size={16} aria-hidden="true" />} label="Status" value={health?.model.loaded ? "Ready" : health?.model.error || "Gateway unavailable"} />
              <StatusLine icon={<ShieldCheck size={16} aria-hidden="true" />} label="Provider boundary" value={isRemote ? "Gateway managed" : "Internal API"} />
              <StatusLine icon={<Database size={16} aria-hidden="true" />} label="Evidence" value="Local RAG" />
            </div>
          </section>

          <section className="surface rounded-2xl p-5">
            <h2 className="text-base font-semibold text-zinc-950 dark:text-white">What you’ll get</h2>
            <div className="mt-4 space-y-4">
              <Feature icon={<Braces size={17} />} title="Approach ladder" text="Separate brute-force, improved, and optimal implementations." />
              <Feature icon={<BookOpenCheck size={17} />} title="Guided explanation" text="Dry runs, state changes, pitfalls, and complexity in one view." />
              <Feature icon={<ShieldCheck size={17} />} title="Sandbox proof" text="Generated Java or Python is executed against a full test suite." />
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}

function StatusLine({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-3 dark:border-zinc-800 dark:bg-zinc-900">
      <span className="flex items-center gap-2 text-sm text-zinc-500 dark:text-zinc-400">
        {icon}
        {label}
      </span>
      <span className="max-w-[190px] truncate text-right font-mono text-xs text-zinc-800 dark:text-zinc-100" title={value}>{value}</span>
    </div>
  );
}

function Feature({ icon, title, text }: { icon: ReactNode; title: string; text: string }) {
  return (
    <div className="flex gap-3">
      <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300">
        {icon}
      </div>
      <div>
        <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">{title}</h3>
        <p className="mt-1 text-sm leading-6 text-zinc-500 dark:text-zinc-400">{text}</p>
      </div>
    </div>
  );
}
