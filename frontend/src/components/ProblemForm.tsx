import { ArrowRight, Braces, FileCode2, Gauge, Keyboard, LoaderCircle } from "lucide-react";
import { FormEvent, KeyboardEvent, useState } from "react";
import { useNavigate } from "react-router-dom";

import { createJob } from "../api/client";

const languages = [
  { id: "java", label: "Java", note: "JDK 17" },
  { id: "python", label: "Python", note: "3.11" }
];
const difficulties = ["easy", "medium", "hard"];

export default function ProblemForm() {
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [problemText, setProblemText] = useState("");
  const [language, setLanguage] = useState("java");
  const [difficulty, setDifficulty] = useState("easy");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const created = await createJob({
        title: title.trim() || undefined,
        problem_text: problemText,
        language,
        difficulty,
        source_urls: []
      });
      navigate(`/jobs/${created.job_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create job");
    } finally {
      setSubmitting(false);
    }
  }

  function handleKeyboardSubmit(event: KeyboardEvent<HTMLFormElement>) {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      event.preventDefault();
      event.currentTarget.requestSubmit();
    }
  }

  return (
    <form onSubmit={handleSubmit} onKeyDown={handleKeyboardSubmit} className="space-y-7">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-zinc-200 pb-5 dark:border-zinc-800">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-600 dark:text-emerald-400">New session</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight text-zinc-950 dark:text-white">Describe the challenge</h2>
          <p className="mt-2 text-sm leading-6 text-zinc-500 dark:text-zinc-400">Include examples, constraints, and input/output details for the strongest result.</p>
        </div>
        <div className="hidden items-center gap-2 rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs text-zinc-500 sm:flex dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-400">
          <Keyboard size={15} aria-hidden="true" />
          <kbd className="font-mono">Ctrl ↵</kbd>
        </div>
      </div>

      {error ? <p role="alert" className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-900/60 dark:bg-red-950/40 dark:text-red-200">{error}</p> : null}

      <label className="block">
        <span className="flex items-center gap-2 text-sm font-semibold text-zinc-800 dark:text-zinc-200">
          <FileCode2 size={16} aria-hidden="true" />
          Problem title <span className="font-normal text-zinc-400">(optional)</span>
        </span>
        <input
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          className="focus-ring mt-2 h-12 w-full rounded-xl border border-zinc-300 bg-white px-4 text-base text-zinc-950 transition placeholder:text-zinc-400 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-100"
          placeholder="e.g. Sort Characters By Frequency"
        />
      </label>

      <label className="block">
        <span className="flex items-center justify-between gap-3 text-sm font-semibold text-zinc-800 dark:text-zinc-200">
          <span className="flex items-center gap-2"><Braces size={16} aria-hidden="true" />Problem statement</span>
          <span className="font-mono text-xs font-normal text-zinc-400">{problemText.length.toLocaleString()} chars</span>
        </span>
        <div className="mt-2 overflow-hidden rounded-xl border border-zinc-800 bg-zinc-950 shadow-inner shadow-black/20 transition focus-within:ring-2 focus-within:ring-emerald-500 focus-within:ring-offset-2 dark:ring-offset-zinc-950">
          <div className="flex items-center gap-1.5 border-b border-zinc-800 px-4 py-2.5">
            <span className="h-2.5 w-2.5 rounded-full bg-red-400/80" />
            <span className="h-2.5 w-2.5 rounded-full bg-amber-400/80" />
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-400/80" />
            <span className="ml-2 font-mono text-xs text-zinc-500">problem.txt</span>
          </div>
          <textarea
            required
            minLength={10}
            value={problemText}
            onChange={(event) => setProblemText(event.target.value)}
            className="min-h-[360px] w-full resize-y bg-transparent px-4 py-4 font-mono text-sm leading-7 text-zinc-100 outline-none placeholder:text-zinc-600 sm:min-h-[430px]"
            placeholder="Paste the full problem statement, examples, constraints, and input/output format…"
          />
        </div>
      </label>

      <div className="grid gap-6 lg:grid-cols-2">
        <fieldset>
          <legend className="flex items-center gap-2 text-sm font-semibold text-zinc-800 dark:text-zinc-200"><Braces size={16} aria-hidden="true" />Language</legend>
          <div className="mt-2 grid grid-cols-2 gap-2">
            {languages.map((item) => {
              const selected = language === item.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  aria-pressed={selected}
                  onClick={() => setLanguage(item.id)}
                  className={`focus-ring rounded-xl border p-3 text-left transition ${selected ? "border-emerald-500 bg-emerald-50 text-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-100" : "border-zinc-200 bg-white text-zinc-700 hover:border-zinc-300 dark:border-zinc-800 dark:bg-zinc-950 dark:text-zinc-300"}`}
                >
                  <span className="block text-sm font-semibold">{item.label}</span>
                  <span className="mt-1 block font-mono text-xs opacity-60">{item.note}</span>
                </button>
              );
            })}
          </div>
        </fieldset>

        <fieldset>
          <legend className="flex items-center gap-2 text-sm font-semibold text-zinc-800 dark:text-zinc-200"><Gauge size={16} aria-hidden="true" />Difficulty</legend>
          <div className="mt-2 grid grid-cols-3 gap-2">
            {difficulties.map((item) => {
              const selected = difficulty === item;
              return (
                <button
                  key={item}
                  type="button"
                  aria-pressed={selected}
                  onClick={() => setDifficulty(item)}
                  className={`focus-ring h-[66px] rounded-xl border text-sm font-semibold capitalize transition ${selected ? "border-zinc-950 bg-zinc-950 text-white dark:border-white dark:bg-white dark:text-zinc-950" : "border-zinc-200 bg-white text-zinc-600 hover:border-zinc-300 dark:border-zinc-800 dark:bg-zinc-950 dark:text-zinc-300"}`}
                >
                  {item}
                </button>
              );
            })}
          </div>
        </fieldset>
      </div>

      <div className="flex flex-col gap-3 border-t border-zinc-200 pt-5 sm:flex-row sm:items-center sm:justify-between dark:border-zinc-800">
        <p className="max-w-lg text-xs leading-5 text-zinc-500 dark:text-zinc-400">The pipeline retrieves evidence, generates distinct approaches, runs tests, and repairs the optimal implementation when needed.</p>
        <button
          type="submit"
          disabled={submitting || problemText.trim().length < 10}
          className="focus-ring inline-flex h-12 shrink-0 items-center justify-center gap-2 rounded-xl bg-emerald-600 px-5 text-sm font-semibold text-white shadow-lg shadow-emerald-900/15 transition hover:-translate-y-0.5 hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-zinc-300 disabled:text-zinc-500 disabled:shadow-none disabled:hover:translate-y-0 dark:disabled:bg-zinc-800"
        >
          {submitting ? <LoaderCircle size={17} className="animate-spin" aria-hidden="true" /> : null}
          {submitting ? "Starting analysis…" : "Generate solution ladder"}
          {!submitting ? <ArrowRight size={17} aria-hidden="true" /> : null}
        </button>
      </div>
    </form>
  );
}
