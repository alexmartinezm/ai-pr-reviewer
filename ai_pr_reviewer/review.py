from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from ai_pr_reviewer.github import PullRequestFile


MAX_PATCH_CHARS = 120_000


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    severity: str
    message: str


@dataclass(frozen=True)
class ReviewResult:
    summary: str
    findings: list[Finding]


def build_review_prompt(files: list[PullRequestFile]) -> str:
    diff = build_diff_payload(files)
    return f"""Review this GitHub pull request diff as a senior software engineer.

Focus on correctness, security, reliability, maintainability, and missing tests. Only report concrete issues that are visible in the diff. Do not nitpick style. Do not praise the code.

Return strict JSON only, with this exact shape:
{{
  "summary": "Brief review summary. Mention if no actionable issues were found.",
  "findings": [
    {{
      "path": "relative/file/path",
      "line": 123,
      "severity": "critical|high|medium|low",
      "message": "Actionable comment for this exact changed line."
    }}
  ]
}}

Rules:
- Use only line numbers from added lines in the provided diff.
- Keep messages under 500 characters.
- Prefer fewer, higher-confidence findings.
- If there are no concrete issues, return an empty findings array.

Diff:
{diff}
"""


def build_diff_payload(files: list[PullRequestFile]) -> str:
    parts: list[str] = []
    remaining = MAX_PATCH_CHARS

    for file in files:
        if not file.patch:
            continue
        section = (
            f"\n--- FILE: {file.filename}\n"
            f"status={file.status} additions={file.additions} deletions={file.deletions} changes={file.changes}\n"
            f"{file.patch}\n"
        )
        if len(section) > remaining:
            parts.append(section[:remaining])
            parts.append("\n[Diff truncated due to size]\n")
            break
        parts.append(section)
        remaining -= len(section)

    return "".join(parts) if parts else "[No textual diff available]"


def parse_review_response(content: str) -> ReviewResult:
    data = json.loads(_extract_json(content))
    summary = str(data.get("summary") or "AI review completed.").strip()
    findings = []

    for item in data.get("findings") or []:
        try:
            path = str(item["path"]).strip()
            line = int(item["line"])
            severity = str(item.get("severity") or "medium").strip().lower()
            message = str(item["message"]).strip()
        except (KeyError, TypeError, ValueError):
            continue

        if not path or line < 1 or not message:
            continue
        if severity not in {"critical", "high", "medium", "low"}:
            severity = "medium"

        findings.append(Finding(path=path, line=line, severity=severity, message=message[:1000]))

    return ReviewResult(summary=summary, findings=findings)


def filter_findings_for_changed_lines(result: ReviewResult, files: list[PullRequestFile]) -> ReviewResult:
    changed_lines_by_file = {file.filename: file.changed_lines for file in files}
    filtered = [
        finding
        for finding in result.findings
        if finding.path in changed_lines_by_file and finding.line in changed_lines_by_file[finding.path]
    ]
    return ReviewResult(summary=result.summary, findings=filtered)


def build_github_review(result: ReviewResult) -> tuple[str, list[dict[str, Any]]]:
    comments = [
        {
            "path": finding.path,
            "line": finding.line,
            "side": "RIGHT",
            "body": f"**{finding.severity.upper()}**: {finding.message}",
        }
        for finding in result.findings
    ]
    return result.summary, comments


def _extract_json(content: str) -> str:
    stripped = content.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped

    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, flags=re.DOTALL)
    if fenced:
        return fenced.group(1)

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end != -1 and end > start:
        return stripped[start : end + 1]

    raise ValueError("Model response did not contain a JSON object")
