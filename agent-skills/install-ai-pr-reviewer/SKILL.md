---
name: install-ai-pr-reviewer
description: Installs the AI PR Reviewer GitHub Action from this source repository into another repository and reports the required GitHub secrets, variables, and permissions. Use when the user asks to add, set up, install, configure, or copy ai-pr-reviewer into a repo for automatic pull request reviews.
---

# Install AI PR Reviewer

## Source Of Truth

Always read the source repository `README.md` before acting. Follow that README over these notes if they differ.

This skill is maintained inside the AI PR Reviewer source repository. The installer locates that repository from its own path, so it does not need user-specific absolute paths.

## Quick Start

From the target repository, run the installer from the AI PR Reviewer source checkout:

```bash
python3 /path/to/ai-pr-reviewer/agent-skills/install-ai-pr-reviewer/scripts/install-ai-pr-reviewer.py
```

For a different target repository:

```bash
python3 /path/to/ai-pr-reviewer/agent-skills/install-ai-pr-reviewer/scripts/install-ai-pr-reviewer.py --target /path/to/repo
```

For a maintainable local agent install, symlink this skill folder instead of copying it:

```bash
ln -s /path/to/ai-pr-reviewer/agent-skills/install-ai-pr-reviewer ~/.claude/skills/install-ai-pr-reviewer
```

## Workflow

1. Read the source repository `README.md`.
2. Confirm the target repo. Default to the current working directory unless the user specifies another path.
3. Run the installer script.
4. Verify the copied Python package with `python3 -m compileall ai_pr_reviewer` from the target repo.
5. Remove generated `__pycache__` files if the verification command creates them.
6. Tell the user to configure GitHub Actions settings.

## Installer Behavior

The script copies the required reviewer files from the AI PR Reviewer source repository:

- `ai_pr_reviewer/`
- `.github/workflows/ai-pr-review.yml`

For `pyproject.toml`:

- If the target repo has no `pyproject.toml`, it copies the source file.
- If the target repo already has `pyproject.toml`, it adds only `openai>=1.0.0` and the `ai-pr-reviewer` project script.
- It does not overwrite an existing `pyproject.toml`.

Optional extras can be copied with `--include-extras`:

- `.env.example`
- `.gitignore`
- `README.md`
- `tests/`

The script refuses to overwrite conflicting existing files or directories unless `--force-overwrite` is passed.

## GitHub Configuration To Report

Required secret:

- `AI_API_KEY`

Required repository variable:

- `AI_MODEL`

Optional repository variables:

- `AI_BASE_URL`
- `AI_MAX_TOKENS`

Required workflow permissions:

```yaml
permissions:
  contents: read
  pull-requests: write
```

Also remind the user to check `Settings` -> `Actions` -> `General` -> `Workflow permissions` so GitHub Actions can read repository contents and write pull request reviews.
