import assert from "node:assert/strict";
import { mkdtemp, readFile, stat } from "node:fs/promises";
import os from "node:os";
import path from "node:path";


const root = await mkdtemp(path.join(os.tmpdir(), "coding-helper-slides-"));
process.env.SLIDES_ROOT = root;
const { parseDeck, renderDeck } = await import("./server.js");

const kinds = ["title", "problem", "observation", "comparison", "approach", "approach", "state", "dry_run", "dry_run", "code", "correctness", "summary"];
const deck = {
  deck_title: "Valid Sudoku",
  audience: "Beginner programming learner",
  learning_objective: "Trace every state update and implement the validator.",
  slides: kinds.map((kind, index) => ({
    kind,
    title: index === 0 ? "Valid Sudoku, explained from first principles" : `Decision ${index}: each update removes repeated work`,
    takeaway: "The algorithm stores exactly the information needed to reject a duplicate immediately.",
    bullets: ["Rows track digits already seen", "Columns track the same invariant", "Each cell maps to one 3×3 box"],
    flow: ["Read cell", "Map state", "Check duplicate", "Record digit"],
    code: kind === "code" ? "for (int row = 0; row < 9; row++) {\n  for (int col = 0; col < 9; col++) {\n    if (board[row][col] == '.') continue;\n    int digit = board[row][col] - '1';\n    int box = (row / 3) * 3 + col / 3;\n  }\n}" : "",
    table: ["comparison", "dry_run"].includes(kind)
      ? { headers: ["Step", "Cell", "State before", "Decision", "State after"], rows: [["1", "(0,0)=5", "empty", "new", "row0={5}"], ["2", "(0,1)=3", "{5}", "new", "row0={3,5}"]] }
      : { headers: [], rows: [] },
    notes: "Explain the invariant in plain language before showing the code."
  }))
};

const parsed = parseDeck("", deck);
assert.equal(parsed.length, 12);
assert.equal(parsed[0].kind, "title");
assert.equal(parsed[7].table.length, 3);

const rendered = await renderDeck({ job_id: "renderer-test", markdown: "", deck });
const pptxPath = path.join(root, "renderer-test", "deck.pptx");
const htmlPath = path.join(root, "renderer-test", "index.html");
assert.ok((await stat(pptxPath)).size > 10_000);
assert.match(await readFile(htmlPath, "utf-8"), /The algorithm stores exactly/);
assert.match(rendered.pptx_path, /renderer-test\/deck\.pptx$/);
console.log(`slide renderer test passed: ${pptxPath}`);
