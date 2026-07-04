import type { TestCase, VerificationRun } from "../types/api";

export default function TestResultPanel({
  tests,
  verificationRuns
}: {
  tests: TestCase[];
  verificationRuns: VerificationRun[];
}) {
  const latest = verificationRuns.at(-1);
  return (
    <div className="space-y-4">
      <section className="rounded-md border border-slate-200 bg-white p-4">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Verification</h2>
        {latest ? (
          <div className="mt-3 grid gap-3 sm:grid-cols-3">
            <Metric label="Status" value={latest.status} />
            <Metric label="Passed" value={String(latest.passed_count)} />
            <Metric label="Failed" value={String(latest.failed_count)} />
          </div>
        ) : (
          <p className="mt-3 text-sm text-slate-500">Verification has not run yet.</p>
        )}
        {latest?.stderr ? <pre className="mt-3 whitespace-pre-wrap rounded-md bg-red-50 p-3 text-xs text-red-700">{latest.stderr}</pre> : null}
      </section>
      <section className="rounded-md border border-slate-200 bg-white">
        <div className="border-b border-slate-200 px-4 py-3">
          <h2 className="text-sm font-semibold">Test Cases</h2>
        </div>
        <div className="divide-y divide-slate-100">
          {tests.length === 0 ? (
            <p className="p-4 text-sm text-slate-500">No tests generated yet.</p>
          ) : (
            tests.map((test, index) => (
              <div key={test.id} className="grid gap-3 p-4 md:grid-cols-2">
                <div>
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Input {index + 1}</p>
                  <pre className="mt-1 whitespace-pre-wrap rounded-md bg-slate-100 p-3 text-xs">{test.input_data || "(empty input)"}</pre>
                </div>
                <div>
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Expected</p>
                  <pre className="mt-1 whitespace-pre-wrap rounded-md bg-slate-100 p-3 text-xs">{test.expected_output || "(none)"}</pre>
                </div>
              </div>
            ))
          )}
        </div>
      </section>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-lg font-semibold">{value}</p>
    </div>
  );
}

