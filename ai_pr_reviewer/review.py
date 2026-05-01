from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from ai_pr_reviewer.github import PullRequestFile


MAX_PATCH_CHARS = 120_000

REVIEWER_SYSTEM_PROMPT = """# Identity

You are an expert pull request reviewer. Your job is to find defects that a strong human reviewer would want fixed before merge.

# Review Priorities

Prioritize issues in this order:
1. Correctness bugs, broken behavior, data loss, race conditions, and edge cases.
2. Security issues, including injection, authorization, authentication, secret handling, unsafe deserialization, and path traversal.
3. Reliability issues, including missing error handling, resource leaks, retries, timeouts, and concurrency hazards.
4. API, schema, migration, and compatibility risks introduced by the diff.
5. Missing or insufficient tests only when the diff changes meaningful behavior or fixes a bug without regression coverage.

# Review Rules

- Review only the provided pull request diff.
- Comment only on concrete, actionable issues supported by the diff.
- Do not report speculative issues, personal preferences, broad refactors, formatting nits, or praise.
- Do not ask questions unless the answer is required to determine whether the diff is safe.
- Prefer a small number of high-confidence findings over many weak comments.
- Think privately before answering, but do not include reasoning traces or chain-of-thought in the output.
- If no actionable issues are present, return an empty findings array and say that no blocking issues were found.

# Output Contract

Return strict JSON only. Do not wrap the JSON in Markdown. Use this exact shape:

{
  "summary": "Brief, factual review summary. Mention if no actionable issues were found.",
  "findings": [
    {
      "path": "relative/file/path",
      "line": 123,
      "severity": "critical|high|medium|low",
      "message": "Actionable comment for this exact changed line. Explain impact and the smallest useful fix."
    }
  ]
}

Each finding must reference a changed added line from the diff. Keep each message under 500 characters."""


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
    return f"""<task>
Review the pull request diff below and return the JSON review result described by the system instructions.
</task>

<line_number_rules>
Use only file paths and added line numbers from this diff. Inline comments that refer to deleted, unchanged, or unavailable lines will be discarded.
</line_number_rules>

<diff>
{diff}
</diff>
"""


def build_diff_payload(files: list[PullRequestFile]) -> str:
    parts: list[str] = []
    remaining = MAX_PATCH_CHARS

    for file in files:
        if not file.patch:
            continue
        section = (
            f"\n<file path={json.dumps(file.filename)} status={json.dumps(file.status)} "
            f"additions={file.additions} deletions={file.deletions} changes={file.changes}>\n"
            f"```diff\n{file.patch}\n```\n"
            "</file>\n"
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
