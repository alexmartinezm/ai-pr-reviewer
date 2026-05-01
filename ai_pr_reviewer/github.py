from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PullRequestFile:
    filename: str
    status: str
    additions: int
    deletions: int
    changes: int
    patch: str

    @property
    def changed_lines(self) -> set[int]:
        return parse_added_lines(self.patch)


class GitHubClient:
    def __init__(self, token: str, owner: str, repo: str, api_url: str = "https://api.github.com") -> None:
        self.token = token
        self.owner = owner
        self.repo = repo
        self.api_url = api_url.rstrip("/")

    def get_pull_request_files(self, pull_number: int) -> list[PullRequestFile]:
        items: list[dict[str, Any]] = []
        page = 1

        while True:
            path = f"/repos/{self.owner}/{self.repo}/pulls/{pull_number}/files"
            data = self._request("GET", path, query={"per_page": "100", "page": str(page)})
            items.extend(data)
            if len(data) < 100:
                break
            page += 1

        return [
            PullRequestFile(
                filename=item["filename"],
                status=item.get("status", "modified"),
                additions=int(item.get("additions", 0)),
                deletions=int(item.get("deletions", 0)),
                changes=int(item.get("changes", 0)),
                patch=item.get("patch") or "",
            )
            for item in items
        ]

    def create_pull_request_review(
        self,
        pull_number: int,
        body: str,
        comments: list[dict[str, Any]],
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "body": body,
            "event": "COMMENT",
        }
        if comments:
            payload["comments"] = comments

        return self._request("POST", f"/repos/{self.owner}/{self.repo}/pulls/{pull_number}/reviews", payload=payload)

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        query: dict[str, str] | None = None,
    ) -> Any:
        url = f"{self.api_url}{path}"
        if query:
            url = f"{url}?{urllib.parse.urlencode(query)}"

        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(
            url,
            data=body,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "User-Agent": "ai-pr-reviewer",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                response_body = response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            error_body = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"GitHub API request failed: {method} {path} {error.code} {error_body}") from error

        if not response_body:
            return None
        return json.loads(response_body)


def parse_added_lines(patch: str) -> set[int]:
    lines: set[int] = set()
    new_line_number: int | None = None

    for line in patch.splitlines():
        if line.startswith("@@"):
            new_line_number = _parse_hunk_start(line)
            continue

        if new_line_number is None:
            continue

        if line.startswith("+") and not line.startswith("+++"):
            lines.add(new_line_number)
            new_line_number += 1
        elif line.startswith("-") and not line.startswith("---"):
            continue
        elif line.startswith("\\"):
            continue
        else:
            new_line_number += 1

    return lines


def _parse_hunk_start(line: str) -> int:
    marker = line.split(" ")[2]
    start = marker.split(",", 1)[0].lstrip("+")
    return int(start)
