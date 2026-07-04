import http from "node:http";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import pptxgen from "pptxgenjs";

const PORT = Number(process.env.PORT || 8200);
const SLIDES_ROOT = process.env.SLIDES_ROOT || "/slides";
const SERVICE_NAME = "slide-renderer";
const VERBOSE_LOGGING = ["1", "true", "yes", "on", "debug"].includes(String(process.env.VERBOSE_LOGGING || "").toLowerCase());
const PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation";

const COLORS = {
  bg: "F8FAFC",
  panel: "FFFFFF",
  ink: "111827",
  muted: "475569",
  line: "CBD5E1",
  teal: "0F766E",
  blue: "2563EB",
  amber: "B45309",
  rose: "BE123C",
  green: "15803D",
  codeBg: "0F172A",
  codeText: "E2E8F0"
};

function log(level, message, metadata = {}) {
  if (level === "debug" && !VERBOSE_LOGGING) {
    return;
  }
  const payload = {
    timestamp: new Date().toISOString(),
    level,
    service: SERVICE_NAME,
    message,
    ...metadata
  };
  const line = JSON.stringify(payload);
  if (level === "error") {
    console.error(line);
  } else {
    console.log(line);
  }
}

function jsonResponse(res, status, payload) {
  res.writeHead(status, { "content-type": "application/json" });
  res.end(JSON.stringify(payload));
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function stripMarkdown(value) {
  return String(value)
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/^#{1,6}\s+/g, "")
    .replace(/[*_~`]/g, "")
    .trim();
}

function truncate(value, maxLength) {
  const text = stripMarkdown(value).replace(/\s+/g, " ");
  if (text.length <= maxLength) {
    return text;
  }
  return `${text.slice(0, Math.max(0, maxLength - 3)).trimEnd()}...`;
}

function splitMarkdownSlides(markdown) {
  const sections = String(markdown)
    .split(/\r?\n---+\r?\n/g)
    .map((section) => section.trim())
    .filter(Boolean);
  return sections.length ? sections : [String(markdown).trim()];
}

function parseTableLines(tableLines) {
  const rows = tableLines
    .map((line) => line.trim())
    .filter((line) => line.startsWith("|"))
    .filter((line) => !/^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?$/.test(line))
    .map((line) =>
      line
        .replace(/^\|/, "")
        .replace(/\|$/, "")
        .split("|")
        .map((cell) => truncate(cell, 42))
    )
    .filter((row) => row.length > 1);
  return rows.slice(0, 7).map((row) => row.slice(0, 5));
}

function parseSlide(section, index) {
  const lines = section.split(/\r?\n/);
  let title = "";
  const bullets = [];
  const paragraphs = [];
  const tableLines = [];
  const codeBlocks = [];
  let inCode = false;
  let codeBuffer = [];

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();
    const trimmed = line.trim();

    if (trimmed.startsWith("```")) {
      if (inCode) {
        codeBlocks.push(codeBuffer.join("\n"));
        codeBuffer = [];
      }
      inCode = !inCode;
      continue;
    }
    if (inCode) {
      codeBuffer.push(line);
      continue;
    }
    if (!trimmed) {
      continue;
    }

    const heading = trimmed.match(/^#{1,6}\s+(.+)$/);
    if (heading && !title) {
      title = truncate(heading[1], 72);
      continue;
    }

    if (trimmed.startsWith("|")) {
      tableLines.push(trimmed);
      continue;
    }

    const bullet = trimmed.match(/^[-*]\s+(.+)$/) || trimmed.match(/^\d+[.)]\s+(.+)$/);
    if (bullet) {
      bullets.push(truncate(bullet[1], 130));
      continue;
    }

    if (!title) {
      title = truncate(trimmed, 72);
    } else {
      paragraphs.push(truncate(trimmed, 130));
    }
  }

  if (inCode && codeBuffer.length) {
    codeBlocks.push(codeBuffer.join("\n"));
  }

  const contentBullets = bullets.length ? bullets : paragraphs;
  return {
    title: title || `Slide ${index + 1}`,
    bullets: contentBullets.slice(0, 6),
    code: codeBlocks[0] || "",
    table: parseTableLines(tableLines),
    raw: section
  };
}

function parseDeck(markdown) {
  const slides = splitMarkdownSlides(markdown).map(parseSlide).filter((slide) => slide.title || slide.bullets.length || slide.code);
  if (!slides.length) {
    return [{ title: "Study Buddy Slides", bullets: ["No slide content was generated."], code: "", table: [], raw: "" }];
  }
  return slides.slice(0, 6);
}

function slideKind(slide, index) {
  const text = `${slide.title} ${slide.bullets.join(" ")}`.toLowerCase();
  if (text.includes("dry") || text.includes("trace") || slide.table.length) {
    return "dry-run";
  }
  if (text.includes("code") || slide.code) {
    return "code";
  }
  if (text.includes("complexity") || text.includes("pitfall") || text.includes("test")) {
    return "summary";
  }
  if (text.includes("plan") || text.includes("algorithm") || text.includes("approach")) {
    return "plan";
  }
  if (text.includes("observation") || text.includes("pattern") || text.includes("idea")) {
    return "observation";
  }
  return index === 0 ? "intro" : "concept";
}

function addBaseSlide(pptx, slide, slideModel, index, total) {
  const accentColors = [COLORS.teal, COLORS.blue, COLORS.amber, COLORS.green, COLORS.rose, COLORS.teal];
  const accent = accentColors[index % accentColors.length];
  slide.background = { color: COLORS.bg };
  slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 0.22, h: 7.5, fill: { color: accent }, line: { color: accent } });
  slide.addText(`0${index + 1}`, { x: 0.45, y: 0.32, w: 0.55, h: 0.3, fontSize: 10, bold: true, color: accent, margin: 0 });
  slide.addText(slideModel.title, {
    x: 0.95,
    y: 0.27,
    w: 10.8,
    h: 0.62,
    fontFace: "Aptos Display",
    fontSize: 26,
    bold: true,
    color: COLORS.ink,
    margin: 0,
    fit: "shrink"
  });
  slide.addText(`Study Buddy  ${index + 1}/${total}`, {
    x: 10.95,
    y: 7.05,
    w: 1.75,
    h: 0.24,
    fontSize: 8,
    color: COLORS.muted,
    align: "right",
    margin: 0
  });
  return accent;
}

function addBulletPanel(pptx, slide, bullets, options = {}) {
  const x = options.x ?? 0.95;
  const y = options.y ?? 1.18;
  const w = options.w ?? 5.95;
  const h = options.h ?? 4.9;
  slide.addShape(pptx.ShapeType.roundRect, {
    x,
    y,
    w,
    h,
    rectRadius: 0.08,
    fill: { color: COLORS.panel },
    line: { color: COLORS.line, transparency: 10 }
  });
  const lines = (bullets.length ? bullets : ["Focus on the state, the decision, and the update after each step."])
    .slice(0, 6)
    .map((bullet) => `- ${bullet}`)
    .join("\n");
  slide.addText(lines, {
    x: x + 0.35,
    y: y + 0.38,
    w: w - 0.7,
    h: h - 0.72,
    fontFace: "Aptos",
    fontSize: options.fontSize ?? 16,
    color: COLORS.ink,
    breakLine: false,
    margin: 0.02,
    fit: "shrink",
    valign: "top",
    paraSpaceAfterPt: 8
  });
}

function addFlowGraphic(pptx, slide, bullets, y = 5.85) {
  const labels = (bullets.length ? bullets : ["Read input", "Track state", "Make decision", "Return answer"])
    .slice(0, 4)
    .map((label) => truncate(label, 32));
  const xValues = [0.95, 3.75, 6.55, 9.35];
  labels.forEach((label, idx) => {
    slide.addShape(pptx.ShapeType.roundRect, {
      x: xValues[idx],
      y,
      w: 2.15,
      h: 0.72,
      rectRadius: 0.08,
      fill: { color: idx % 2 === 0 ? "ECFEFF" : "EFF6FF" },
      line: { color: idx % 2 === 0 ? "67E8F9" : "93C5FD" }
    });
    slide.addText(label, {
      x: xValues[idx] + 0.13,
      y: y + 0.16,
      w: 1.89,
      h: 0.32,
      fontSize: 11,
      bold: true,
      color: COLORS.ink,
      align: "center",
      margin: 0,
      fit: "shrink"
    });
    if (idx < labels.length - 1) {
      slide.addText(">", { x: xValues[idx] + 2.25, y: y + 0.2, w: 0.35, h: 0.26, fontSize: 16, bold: true, color: COLORS.muted, margin: 0 });
    }
  });
}

function addConceptGraphic(pptx, slide, kind, accent) {
  const centerX = 9.55;
  const centerY = 3.35;
  const labels =
    kind === "observation"
      ? ["Observation", "Invariant", "Update"]
      : kind === "summary"
        ? ["Cost", "Checks", "Risks"]
        : ["Input", "State", "Answer"];
  const colors = ["E0F2FE", "DCFCE7", "FEF3C7"];
  labels.forEach((label, idx) => {
    const angle = (Math.PI * 2 * idx) / labels.length - Math.PI / 2;
    const x = centerX + Math.cos(angle) * 1.3;
    const y = centerY + Math.sin(angle) * 1.0;
    slide.addShape(pptx.ShapeType.ellipse, {
      x,
      y,
      w: 1.45,
      h: 0.8,
      fill: { color: colors[idx] },
      line: { color: accent, transparency: 25 }
    });
    slide.addText(label, {
      x: x + 0.08,
      y: y + 0.26,
      w: 1.29,
      h: 0.24,
      fontSize: 10,
      bold: true,
      color: COLORS.ink,
      align: "center",
      margin: 0,
      fit: "shrink"
    });
  });
  slide.addShape(pptx.ShapeType.ellipse, {
    x: centerX + 0.18,
    y: centerY + 0.08,
    w: 1.55,
    h: 0.86,
    fill: { color: "FFFFFF" },
    line: { color: accent, width: 1.3 }
  });
  slide.addText("Trace", {
    x: centerX + 0.38,
    y: centerY + 0.38,
    w: 1.16,
    h: 0.22,
    fontSize: 12,
    bold: true,
    color: accent,
    align: "center",
    margin: 0
  });
}

function addManualTable(pptx, slide, rows, x, y, w, h) {
  if (!rows.length) {
    return;
  }
  const colCount = Math.max(...rows.map((row) => row.length));
  const rowCount = rows.length;
  const colW = w / colCount;
  const rowH = h / rowCount;
  rows.forEach((row, rowIndex) => {
    for (let colIndex = 0; colIndex < colCount; colIndex += 1) {
      const cell = row[colIndex] || "";
      const isHeader = rowIndex === 0;
      slide.addShape(pptx.ShapeType.rect, {
        x: x + colIndex * colW,
        y: y + rowIndex * rowH,
        w: colW,
        h: rowH,
        fill: { color: isHeader ? "E2E8F0" : "FFFFFF" },
        line: { color: COLORS.line, width: 0.75 }
      });
      slide.addText(cell, {
        x: x + colIndex * colW + 0.05,
        y: y + rowIndex * rowH + 0.07,
        w: colW - 0.1,
        h: rowH - 0.1,
        fontSize: isHeader ? 10 : 9,
        bold: isHeader,
        color: COLORS.ink,
        margin: 0,
        fit: "shrink",
        valign: "mid"
      });
    }
  });
}

function addCodeBlock(pptx, slide, code, x, y, w, h) {
  const cleanCode = String(code || "")
    .split(/\r?\n/)
    .slice(0, 16)
    .join("\n")
    .trim();
  slide.addShape(pptx.ShapeType.roundRect, {
    x,
    y,
    w,
    h,
    rectRadius: 0.08,
    fill: { color: COLORS.codeBg },
    line: { color: "1E293B" }
  });
  slide.addText(cleanCode || "for each item:\n  update state\n  keep the best answer\nreturn answer", {
    x: x + 0.25,
    y: y + 0.25,
    w: w - 0.5,
    h: h - 0.5,
    fontFace: "Consolas",
    fontSize: 10.5,
    color: COLORS.codeText,
    margin: 0,
    fit: "shrink",
    valign: "top",
    breakLine: false
  });
}

async function writePptx(jobDir, jobId, slides) {
  const pptx = new pptxgen();
  pptx.layout = "LAYOUT_WIDE";
  pptx.author = "Study Buddy";
  pptx.company = "Study Buddy";
  pptx.subject = "Programming problem explanation";
  pptx.title = slides[0]?.title || "Study Buddy Slides";
  pptx.lang = "en-US";
  pptx.theme = {
    headFontFace: "Aptos Display",
    bodyFontFace: "Aptos",
    lang: "en-US"
  };

  slides.forEach((slideModel, index) => {
    const slide = pptx.addSlide();
    const kind = slideKind(slideModel, index);
    const accent = addBaseSlide(pptx, slide, slideModel, index, slides.length);

    if (kind === "dry-run") {
      addBulletPanel(pptx, slide, slideModel.bullets.slice(0, 3), { x: 0.95, y: 1.18, w: 4.0, h: 4.75, fontSize: 14 });
      addManualTable(pptx, slide, slideModel.table, 5.25, 1.25, 6.85, 4.55);
      if (!slideModel.table.length) {
        addFlowGraphic(pptx, slide, slideModel.bullets, 5.9);
      }
      return;
    }

    if (kind === "code") {
      addBulletPanel(pptx, slide, slideModel.bullets.slice(0, 3), { x: 0.95, y: 1.18, w: 4.15, h: 4.75, fontSize: 14 });
      addCodeBlock(pptx, slide, slideModel.code, 5.35, 1.2, 6.85, 4.85);
      return;
    }

    addBulletPanel(pptx, slide, slideModel.bullets, { x: 0.95, y: 1.18, w: 6.05, h: 4.55 });
    addConceptGraphic(pptx, slide, kind, accent);
    addFlowGraphic(pptx, slide, slideModel.bullets, 6.05);
  });

  const pptxPath = path.join(jobDir, "deck.pptx");
  await pptx.writeFile({ fileName: pptxPath });
  return pptxPath;
}

function renderTableHtml(rows) {
  if (!rows.length) {
    return "";
  }
  return `<table>${rows
    .map((row, rowIndex) => {
      const tag = rowIndex === 0 ? "th" : "td";
      return `<tr>${row.map((cell) => `<${tag}>${escapeHtml(cell)}</${tag}>`).join("")}</tr>`;
    })
    .join("")}</table>`;
}

function renderSlideHtml(slide) {
  const bullets = slide.bullets.length
    ? `<ul>${slide.bullets.map((bullet) => `<li>${escapeHtml(bullet)}</li>`).join("")}</ul>`
    : "";
  const table = renderTableHtml(slide.table);
  const code = slide.code ? `<pre><code>${escapeHtml(slide.code)}</code></pre>` : "";
  return `<section class="slide-card">
      <h2>${escapeHtml(slide.title)}</h2>
      ${bullets}
      ${table}
      ${code}
    </section>`;
}

function renderHtml(slides) {
  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Study Buddy Slides</title>
    <style>
      body { margin: 0; font-family: Inter, ui-sans-serif, system-ui, sans-serif; background: #f8fafc; color: #111827; }
      main { max-width: 1040px; margin: 0 auto; padding: 28px 18px 48px; display: grid; gap: 18px; }
      .slide-card { min-height: 440px; background: #fff; border: 1px solid #dbe3ef; border-left: 7px solid #0f766e; border-radius: 8px; padding: 30px 34px; box-shadow: 0 12px 28px rgba(15, 23, 42, 0.07); }
      h2 { margin: 0 0 18px; font-size: 28px; line-height: 1.15; letter-spacing: 0; }
      ul { margin: 0; padding-left: 22px; font-size: 18px; line-height: 1.55; }
      li { margin: 8px 0; }
      table { width: 100%; border-collapse: collapse; margin-top: 18px; font-size: 14px; }
      th, td { border: 1px solid #cbd5e1; padding: 9px 10px; text-align: left; vertical-align: top; }
      th { background: #e2e8f0; }
      pre { margin-top: 18px; padding: 18px; border-radius: 8px; background: #0f172a; color: #e2e8f0; overflow: auto; }
      code { font-family: Consolas, ui-monospace, SFMono-Regular, monospace; font-size: 13px; line-height: 1.45; }
    </style>
  </head>
  <body>
    <main>
      ${slides.map(renderSlideHtml).join("\n")}
    </main>
  </body>
</html>`;
}

async function readJson(req) {
  const chunks = [];
  for await (const chunk of req) {
    chunks.push(chunk);
  }
  const raw = Buffer.concat(chunks).toString("utf-8");
  return raw ? JSON.parse(raw) : {};
}

async function renderDeck(payload) {
  const jobId = String(payload.job_id || "unknown").replace(/[^a-zA-Z0-9_-]/g, "");
  const markdown = String(payload.markdown || "");
  const slides = parseDeck(markdown);
  log("info", "render.started", { job_id: jobId, markdown_chars: markdown.length, slide_count: slides.length });
  const jobDir = path.join(SLIDES_ROOT, jobId);
  await mkdir(jobDir, { recursive: true });
  await writeFile(path.join(jobDir, "deck.md"), markdown, "utf-8");
  const pptxPath = await writePptx(jobDir, jobId, slides);
  await writeFile(path.join(jobDir, "index.html"), renderHtml(slides), "utf-8");
  log("info", "render.files_written", { job_id: jobId, pptx_path: pptxPath, slide_count: slides.length });
  return {
    html_path: `http://localhost:${PORT}/slides/${jobId}/index.html`,
    pptx_path: `http://localhost:${PORT}/slides/${jobId}/deck.pptx`,
    pdf_path: null
  };
}

function contentTypeFor(filePath) {
  if (filePath.endsWith(".html")) {
    return "text/html";
  }
  if (filePath.endsWith(".pptx")) {
    return PPTX_MIME;
  }
  if (filePath.endsWith(".md")) {
    return "text/markdown";
  }
  return "application/octet-stream";
}

const server = http.createServer(async (req, res) => {
  const started = Date.now();
  try {
    const url = new URL(req.url || "/", `http://localhost:${PORT}`);
    log("debug", "http.request.started", { method: req.method, path: url.pathname });
    if (req.method === "GET" && url.pathname === "/health") {
      log("info", "http.request.completed", { method: req.method, path: url.pathname, status: 200, elapsed_ms: Date.now() - started });
      return jsonResponse(res, 200, { status: "ok", service: "slide-renderer" });
    }
    if (req.method === "POST" && url.pathname === "/render") {
      const payload = await readJson(req);
      const rendered = await renderDeck(payload);
      log("info", "render.completed", {
        job_id: String(payload.job_id || "unknown"),
        html_path: rendered.html_path,
        pptx_path: rendered.pptx_path,
        elapsed_ms: Date.now() - started
      });
      return jsonResponse(res, 200, rendered);
    }
    if (req.method === "GET" && url.pathname.startsWith("/slides/")) {
      const safePath = url.pathname.replace(/^\/slides\//, "").replace(/\.\./g, "");
      const filePath = path.join(SLIDES_ROOT, safePath);
      const body = await readFile(filePath);
      res.writeHead(200, { "content-type": contentTypeFor(filePath) });
      log("info", "slide.asset.served", {
        path: safePath,
        bytes: body.length,
        status: 200,
        elapsed_ms: Date.now() - started
      });
      return res.end(body);
    }
    log("info", "http.request.completed", { method: req.method, path: url.pathname, status: 404, elapsed_ms: Date.now() - started });
    return jsonResponse(res, 404, { detail: "Not found" });
  } catch (error) {
    log("error", "http.request.failed", {
      error: String(error?.message || error),
      elapsed_ms: Date.now() - started
    });
    return jsonResponse(res, 500, { detail: String(error?.message || error) });
  }
});

server.listen(PORT, "0.0.0.0", () => {
  log("info", "server.listening", { port: PORT, slides_root: SLIDES_ROOT, verbose: VERBOSE_LOGGING });
});
