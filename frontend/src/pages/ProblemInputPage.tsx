import ProblemForm from "../components/ProblemForm";

export default function ProblemInputPage() {
  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
      <section>
        <ProblemForm />
      </section>
      <aside className="border-l border-slate-200 pl-6">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Pipeline</h2>
        <ol className="mt-4 space-y-3 text-sm text-slate-700">
          <li>1. Analyze the problem and likely algorithm pattern.</li>
          <li>2. Collect approved source metadata and snippets.</li>
          <li>3. Build chunks, vectors, and evidence claims.</li>
          <li>4. Generate code and tests.</li>
          <li>5. Verify in the sandbox and produce study material.</li>
        </ol>
      </aside>
    </div>
  );
}

