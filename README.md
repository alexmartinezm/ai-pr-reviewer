# AI PR Reviewer

AI PR Reviewer is a GitHub Action that reviews pull request diffs with an OpenAI-compatible model API and posts a GitHub pull request review with a summary plus inline comments.

## Recommended Setup: Agent Skill

This repository includes an agent skill that installs AI PR Reviewer into existing repositories. Recommended flow:

- Skill: `agent-skills/install-ai-pr-reviewer`
- Add the skill to your agent.
- Open the target repository with your agent.
- Ask the agent to use `install-ai-pr-reviewer` for that repository.
- The skill copies the required reviewer package and GitHub workflow.
- The skill updates an existing `pyproject.toml` without overwriting it.
- The skill reports the required GitHub secret, variables, and workflow permissions.

For local agent usage, symlink the skill into your agent skills directory:

```bash
ln -s /path/to/ai-pr-reviewer/agent-skills/install-ai-pr-reviewer ~/.claude/skills/install-ai-pr-reviewer
```

Then, from the target repository, ask your agent:

```text
Use the install-ai-pr-reviewer skill to set up AI PR Reviewer in this repository.
```

The skill wraps the installer script internally. You usually do not need to run the script directly, but it is available at:

```bash
agent-skills/install-ai-pr-reviewer/scripts/install-ai-pr-reviewer.py
```

Manual setup is still documented below if you prefer to copy files yourself.

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
- `AI_REASONING_EFFORT`: optional reasoning effort for models/providers that support it.
- `AI_REASONING_PARAMETER`: optional request body shape for reasoning effort. Defaults to `reasoning`.

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
- `AI_REASONING_EFFORT`: opt-in reasoning effort. Supported values are `none`, `minimal`, `low`, `medium`, `high`, and `xhigh`.
- `AI_REASONING_PARAMETER`: reasoning request body shape. Supported values are `reasoning` and `reasoning_effort`. Defaults to `reasoning`.

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
export AI_REASONING_EFFORT="medium"
export AI_REASONING_PARAMETER="reasoning"

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
- `AI_REASONING_EFFORT`: optional reasoning effort for models/providers that support it. Supported values are `none`, `minimal`, `low`, `medium`, `high`, and `xhigh`.
- `AI_REASONING_PARAMETER`: optional request body shape for reasoning effort. Use `reasoning` for OpenAI-style APIs or `reasoning_effort` for providers that explicitly document that field.
- `AI_REVIEW_DRY_RUN`: set to `true` to print the review payload instead of posting it.

## Prompt Design

The reviewer uses a curated prompt split into two parts:

- A system prompt with durable reviewer identity, review priorities, hard rules, and the JSON output contract.
- A user prompt containing the current PR diff wrapped in XML-like tags to make file boundaries and task context explicit.

The prompt is intentionally strict:

- It prioritizes correctness, security, reliability, compatibility, and meaningful missing tests.
- It asks for fewer high-confidence findings instead of many speculative comments.
- It forbids style nits, praise, broad refactors, and unsupported guesses.
- It tells the model to think privately but return only strict JSON.
- It requires each finding to reference an added line in the diff; the application also validates this before posting inline comments.

## Reasoning Effort

`AI_REASONING_EFFORT` is opt-in because support is model and provider dependent.

When set, the value is sent as an additional JSON body field through the OpenAI Python SDK `extra_body` option. This avoids passing unsupported Python keyword arguments to `chat.completions.create()` while still producing the intended request body.

The default body shape is OpenAI-style:

```json
{
  "reasoning": {
    "effort": "medium"
  }
}
```

Some OpenAI-compatible providers document a flat field instead. For those providers, set `AI_REASONING_PARAMETER=reasoning_effort` to send:

```json
{
  "reasoning_effort": "medium"
}
```

Do not use headers for reasoning effort. This is request-body model configuration, not transport metadata.

Recommended starting points:

- `low`: faster reviews with modest reasoning.
- `medium`: balanced quality, latency, and cost.
- `high`: deeper review for security-sensitive or high-value repositories.

Use higher values only if your provider supports them and the added latency/cost is worthwhile.

## Sources Used For Prompt Improvements

- OpenAI Prompt Engineering: recommends clear role separation, explicit instructions, examples/output contracts, and Markdown/XML-style boundaries for prompt sections and context.
- OpenAI Reasoning Models: describes reasoning effort as a tuning knob with provider/model-dependent values, plus the tradeoff between quality, latency, and token usage.
- GitHub REST API Pull Request Reviews: documents creating grouped PR reviews, inline review comments, `line`, `side`, `path`, and the `COMMENT` review event.
- GitHub Copilot Code Review docs: reinforces using comment-only AI reviews, actionable inline comments, and repository-level custom review guidance patterns.

Reference links:

- https://platform.openai.com/docs/guides/prompt-engineering
- https://platform.openai.com/docs/guides/reasoning
- https://docs.github.com/en/rest/pulls/reviews?apiVersion=2022-11-28#create-a-review-for-a-pull-request
- https://docs.github.com/en/copilot/using-github-copilot/code-review/using-copilot-code-review

## Development

Run a syntax check:

```bash
python -m compileall ai_pr_reviewer
```

Install dev dependencies:

```bash
python -m pip install -e ".[dev]"
```
