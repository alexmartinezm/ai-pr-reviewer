from __future__ import annotations

import argparse
import json
import sys

from ai_pr_reviewer.config import load_config
from ai_pr_reviewer.github import GitHubClient
from ai_pr_reviewer.llm import ReviewModel
from ai_pr_reviewer.review import build_github_review, build_review_prompt, filter_findings_for_changed_lines, parse_review_response


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AI pull request reviewer")
    parser.add_argument("--dry-run", action="store_true", help="Print the generated review instead of posting to GitHub")
    args = parser.parse_args(argv)

    try:
        config = load_config()
        dry_run = args.dry_run or config.dry_run

        github = GitHubClient(config.github_token, config.owner, config.repo)
        files = github.get_pull_request_files(config.pull_request_number)
        if not files:
            print("No files changed in pull request; skipping review.")
            return 0

        prompt = build_review_prompt(files)
        model = ReviewModel(config.api_key, config.base_url, config.model, config.max_tokens)
        raw_review = model.review(prompt)
        review = filter_findings_for_changed_lines(parse_review_response(raw_review), files)
        body, comments = build_github_review(review)

        if dry_run:
            print(json.dumps({"body": body, "comments": comments}, indent=2))
            return 0

        github.create_pull_request_review(config.pull_request_number, body=body, comments=comments)
        print(f"Posted AI review with {len(comments)} inline comment(s).")
        return 0
    except Exception as error:
        print(f"ai-pr-reviewer failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
