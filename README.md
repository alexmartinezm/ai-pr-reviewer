# AI PR Reviewer

AI PR Reviewer is a GitHub Action that reviews pull request diffs with an OpenAI-compatible model API and posts a GitHub pull request review with a summary plus inline comments.

The model client uses the OpenAI SDK and can target OpenAI or any OpenAI-compatible API:

```python
from openai import OpenAI

client = OpenAI(
    api_key="your_api_key",
    base_url="https://api.example.com/v1",
)
```

Required values:

- `AI_API_KEY`: API key for your model provider.
- `AI_MODEL`: model name to use for reviews.

Optional values:

- `AI_BASE_URL`: OpenAI-compatible API base URL. Leave unset to use the OpenAI SDK default.
- `AI_MAX_TOKENS`: defaults to `4000`.

## What It Does

- Runs on GitHub `pull_request` events.
- Fetches the PR files and unified patches through the GitHub API.
- Sends the diff to an OpenAI-compatible chat completions endpoint.
- Requires the model to return strict JSON findings.
- Posts one PR review using `GITHUB_TOKEN`.
- Adds inline comments only on added lines in the diff.
- Falls back to a summary-only review if no valid inline comments are returned.

## Add To An Existing GitHub Repository

Copy these files and directories into the repository where you want automatic PR reviews:

- `ai_pr_reviewer/`
- `pyproject.toml`
- `.github/workflows/ai-pr-review.yml`

Optional but recommended:

- `README.md`
- `.env.example`
- `tests/`
- `.gitignore`

If the target repository already has a `pyproject.toml`, do not overwrite it. Add the dependency and script entry to the existing file instead:

```toml
dependencies = [
  "openai>=1.0.0",
]

[project.scripts]
ai-pr-reviewer = "ai_pr_reviewer.cli:main"
```

If the target repository already has dependencies, only add `openai>=1.0.0` to the existing dependency list.

## GitHub Configuration

Add this repository content to the GitHub repository you want reviewed, then configure the secret:

- `AI_API_KEY`: API key for your OpenAI-compatible provider.

Required repository variables:

- `AI_MODEL`: model name.

Optional repository variables:

- `AI_BASE_URL`: API base URL. Leave unset to use the OpenAI SDK default.
- `AI_MAX_TOKENS`: max response tokens. Defaults to `4000`.

The workflow is already included at `.github/workflows/ai-pr-review.yml`.

Configure these in GitHub under `Settings` -> `Secrets and variables` -> `Actions`.

Required workflow permissions in `.github/workflows/ai-pr-review.yml`:

```yaml
permissions:
  contents: read
  pull-requests: write
```

Also check repository settings under `Settings` -> `Actions` -> `General` -> `Workflow permissions` and ensure GitHub Actions can read repository contents and write pull request reviews.

Commit and push the files from the target repository:

```bash
git add ai_pr_reviewer pyproject.toml .github/workflows/ai-pr-review.yml
git commit -m "add AI pull request reviewer"
git push
```

After pushing, open or update a pull request. The GitHub Action will run and post a review on the PR.

## Local Usage

Install locally:

```bash
python -m pip install .
```

Run a dry review against an existing PR:

```bash
export GITHUB_TOKEN="ghp_or_ghs_token"
export GITHUB_REPOSITORY="owner/repo"
export PR_NUMBER="123"
export AI_API_KEY="your_api_key"
export AI_BASE_URL="https://api.example.com/v1"
export AI_MODEL="your-model-name"

ai-pr-reviewer --dry-run
```

To post the review, omit `--dry-run`.

## GitHub Forks

This workflow uses the regular `pull_request` event for safety. GitHub does not expose repository secrets to pull requests from forks by default, so forked PRs may not be reviewed automatically unless you adjust your repository policy.

Avoid switching to `pull_request_target` unless you fully understand the security implications.

## Configuration

Environment variables:

- `GITHUB_TOKEN`: token used to read PR files and post reviews.
- `GITHUB_REPOSITORY`: repository in `owner/repo` format. Set automatically in GitHub Actions.
- `PR_NUMBER`: pull request number. Optional in GitHub Actions because it is read from the event payload.
- `AI_API_KEY`: required model provider API key.
- `AI_BASE_URL`: optional OpenAI-compatible API base URL.
- `AI_MODEL`: required model name.
- `AI_MAX_TOKENS`: optional max response tokens.
- `AI_REVIEW_DRY_RUN`: set to `true` to print the review payload instead of posting it.

## Development

Run a syntax check:

```bash
python -m compileall ai_pr_reviewer
```

Install dev dependencies:

```bash
python -m pip install -e ".[dev]"
```
