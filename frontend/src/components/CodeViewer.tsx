import Editor from "@monaco-editor/react";

import type { GeneratedSolution } from "../types/api";

export default function CodeViewer({ solution, language }: { solution?: GeneratedSolution; language: string }) {
  if (!solution) {
    return <p className="text-sm text-slate-500">Code will appear when generation completes.</p>;
  }

  const monacoLanguage = language === "java" ? "java" : "python";

  return (
    <div className="rounded-md border border-slate-200 bg-white">
      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold">Final Code</h2>
          <p className="text-xs text-slate-500">
            {solution.algorithm_pattern} · {solution.time_complexity} time · {solution.space_complexity} space
          </p>
        </div>
      </div>
      <div className="h-[520px]">
        <Editor
          height="100%"
          language={monacoLanguage}
          value={solution.code}
          options={{ readOnly: true, minimap: { enabled: false }, fontSize: 13, wordWrap: "on" }}
        />
      </div>
    </div>
  );
}

