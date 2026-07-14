from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass


_NAVIGATION_LINES = {
    "sign in", "sign up", "login", "register", "problems", "submissions",
    "discuss", "editorial", "solutions", "premium", "accept", "cookie policy",
}
_LABELS = {
    "input": "Input:", "input format": "Input:",
    "output": "Output:", "output format": "Output:",
    "constraint": "Constraints:", "constraints": "Constraints:",
    "example": "Examples:", "examples": "Examples:", "sample": "Examples:",
    "sample input": "Sample Input:", "sample output": "Sample Output:",
}
_SOURCE_PATTERNS = (
    ("leetcode", re.compile(r"leetcode(?:\.com)?/problems/([a-z0-9-]+)", re.I)),
    ("codeforces", re.compile(r"codeforces(?:\.com)?/(?:contest|problemset/problem)/(\d+)/(\w+)", re.I)),
    ("hackerrank", re.compile(r"hackerrank(?:\.com)?/challenges/([a-z0-9-]+)", re.I)),
)


@dataclass(frozen=True)
class NormalizedProblem:
    original_text: str
    normalized_text: str
    statement_hash: str
    extracted_title: str | None
    source_platform: str | None
    source_problem_id: str | None
    sample_inputs: list[str]
    sample_outputs: list[str]


def normalize_problem(text: str) -> NormalizedProblem:
    original = unicodedata.normalize("NFKC", text or "").replace("\r\n", "\n").replace("\r", "\n")
    source_platform, source_problem_id = _source_identity(original)
    lines: list[str] = []
    previous_heading = ""
    for raw in original.split("\n"):
        line = _normalize_markdown(raw)
        if not line:
            continue
        lower = line.casefold().strip(" :")
        if lower in _NAVIGATION_LINES:
            continue
        label = _LABELS.get(lower)
        if label:
            line = label
        if line.endswith(":") or raw.lstrip().startswith("#"):
            heading = line.casefold().strip(" :")
            if heading == previous_heading:
                continue
            previous_heading = heading
        lines.append(line)
    normalized = "\n".join(lines).strip()
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    normalized = "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in normalized.splitlines())
    title = _extract_title(normalized)
    sample_inputs, sample_outputs = _extract_samples(normalized)
    digest = hashlib.sha256(normalized.casefold().encode("utf-8")).hexdigest()
    return NormalizedProblem(original, normalized, digest, title, source_platform, source_problem_id, sample_inputs, sample_outputs)


def _normalize_markdown(line: str) -> str:
    line = line.strip()
    line = re.sub(r"^#{1,6}\s*", "", line)
    line = re.sub(r"^[-*+]\s+", "- ", line)
    line = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", line)
    line = re.sub(r"(?<!`)`([^`]+)`(?!`)", r"\1", line)
    line = re.sub(r"\*\*([^*]+)\*\*|__([^_]+)__", lambda m: m.group(1) or m.group(2), line)
    return re.sub(r"\s+", " ", line).strip()


def _extract_title(text: str) -> str | None:
    for line in text.splitlines():
        candidate = line.strip(" :")
        if candidate and candidate.casefold() not in _LABELS and len(candidate) <= 160:
            return candidate
    return None


def _source_identity(text: str) -> tuple[str | None, str | None]:
    for platform, pattern in _SOURCE_PATTERNS:
        match = pattern.search(text)
        if match:
            return platform, "-".join(match.groups())
    return None, None


def _extract_samples(text: str) -> tuple[list[str], list[str]]:
    inputs: list[str] = []
    outputs: list[str] = []
    active: list[str] | None = None
    buffer: list[str] = []
    for line in text.splitlines():
        lower = line.casefold().strip()
        if lower in {"sample input:", "input:"}:
            if active is not None and buffer:
                active.append("\n".join(buffer).strip())
            active, buffer = inputs, []
        elif lower in {"sample output:", "output:"}:
            if active is not None and buffer:
                active.append("\n".join(buffer).strip())
            active, buffer = outputs, []
        elif lower in {"constraints:", "examples:"}:
            if active is not None and buffer:
                active.append("\n".join(buffer).strip())
            active, buffer = None, []
        elif active is not None and line.strip():
            buffer.append(line)
    if active is not None and buffer:
        active.append("\n".join(buffer).strip())
    return inputs, outputs
