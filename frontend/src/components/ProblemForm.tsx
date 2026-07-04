import { Send } from "lucide-react";
import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";

import { createJob } from "../api/client";

export default function ProblemForm() {
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [problemText, setProblemText] = useState("");
  const [language, setLanguage] = useState("python");
  const [difficulty, setDifficulty] = useState("easy");
  const [sourceUrls, setSourceUrls] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const created = await createJob({
        title: title.trim() || undefined,
        problem_text: problemText,
        language,
        difficulty,
        source_urls: sourceUrls
          .split(/\r?\n/)
          .map((value) => value.trim())
          .filter(Boolean)
      });
      navigate(`/jobs/${created.job_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create job");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold">New Explanation Job</h1>
        <p className="text-sm text-slate-500">Paste a programming problem and run the local explanation pipeline.</p>
      </div>
      {error ? <p className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}
      <label className="block">
        <span className="text-sm font-medium text-slate-700">Problem title</span>
        <input
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          className="focus-ring mt-1 h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm"
          placeholder="Two Sum"
        />
      </label>
      <label className="block">
        <span className="text-sm font-medium text-slate-700">Problem statement</span>
        <textarea
          required
          minLength={10}
          value={problemText}
          onChange={(event) => setProblemText(event.target.value)}
          className="focus-ring mt-1 min-h-[300px] w-full rounded-md border border-slate-300 bg-white px-3 py-2 font-mono text-sm leading-6"
          placeholder="Paste the full problem statement, examples, constraints, and input/output format."
        />
      </label>
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block">
          <span className="text-sm font-medium text-slate-700">Programming language</span>
          <select
            value={language}
            onChange={(event) => setLanguage(event.target.value)}
            className="focus-ring mt-1 h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm"
          >
            <option value="python">Python</option>
            <option value="java">Java</option>
            <option value="cpp" disabled>
              C++ (later)
            </option>
            <option value="javascript" disabled>
              JavaScript (later)
            </option>
          </select>
        </label>
        <label className="block">
          <span className="text-sm font-medium text-slate-700">Difficulty estimate</span>
          <select
            value={difficulty}
            onChange={(event) => setDifficulty(event.target.value)}
            className="focus-ring mt-1 h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm"
          >
            <option value="easy">Easy</option>
            <option value="medium">Medium</option>
            <option value="hard">Hard</option>
          </select>
        </label>
      </div>
      <label className="block">
        <span className="text-sm font-medium text-slate-700">Optional source URLs</span>
        <textarea
          value={sourceUrls}
          onChange={(event) => setSourceUrls(event.target.value)}
          className="focus-ring mt-1 min-h-24 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
          placeholder="One URL per line"
        />
      </label>
      <button
        type="submit"
        disabled={submitting}
        className="focus-ring inline-flex h-10 items-center gap-2 rounded-md bg-teal-600 px-4 text-sm font-medium text-white hover:bg-teal-700 disabled:cursor-not-allowed disabled:bg-slate-400"
      >
        <Send size={16} aria-hidden="true" />
        {submitting ? "Submitting..." : "Submit"}
      </button>
    </form>
  );
}

