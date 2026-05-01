#!/usr/bin/env python3
"""Install the local ai-pr-reviewer project into a target repository."""

from __future__ import annotations

import argparse
import filecmp
import re
import shutil
import sys
from pathlib import Path


REQUIRED_DIRS = ("ai_pr_reviewer",)
REQUIRED_FILES = (Path(".github/workflows/ai-pr-review.yml"),)
OPTIONAL_EXTRAS = (Path(".env.example"), Path(".gitignore"), Path("README.md"), Path("tests"))
OPENAI_DEP = '"openai>=1.0.0",'
SCRIPT_ENTRY = 'ai-pr-reviewer = "ai_pr_reviewer.cli:main"'


def find_source_repo() -> Path:
    """Find the ai-pr-reviewer repository that contains this maintained skill."""
    for parent in Path(__file__).resolve().parents:
        if (parent / "ai_pr_reviewer").is_dir() and (parent / "README.md").is_file():
            return parent
    raise SystemExit("Could not locate the ai-pr-reviewer source repository from this script path.")


SOURCE_REPO = find_source_repo()
README = SOURCE_REPO / "README.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install ai-pr-reviewer into a target repo.")
    parser.add_argument(
        "--target",
        type=Path,
        default=Path.cwd(),
        help="Target repository path. Defaults to the current directory.",
    )
    parser.add_argument(
        "--include-extras",
        action="store_true",
        help="Also copy .env.example, .gitignore, README.md, and tests/ when present.",
    )
    parser.add_argument(
        "--force-overwrite",
        action="store_true",
        help="Overwrite conflicting copied files or directories.",
    )
    return parser.parse_args()


def ensure_source() -> str:
    if not README.exists():
        raise SystemExit(f"Source README not found: {README}")

    readme = README.read_text(encoding="utf-8")
    if "AI PR Reviewer" not in readme:
        raise SystemExit(f"Unexpected README content: {README}")

    return readme


def same_path(source: Path, target: Path) -> bool:
    if source.is_file() and target.is_file():
        return filecmp.cmp(source, target, shallow=False)
    if source.is_dir() and target.is_dir():
        comparison = filecmp.dircmp(source, target)
        return not comparison.left_only and not comparison.right_only and not comparison.diff_files
    return False


def copy_path(source: Path, target: Path, force: bool) -> None:
    if target.exists():
        if same_path(source, target):
            print(f"unchanged: {target}")
            return
        if not force:
            raise SystemExit(
                f"Refusing to overwrite existing path: {target}\n"
                "Re-run with --force-overwrite if replacing it is intentional."
            )
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()

    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    else:
        shutil.copy2(source, target)
    print(f"copied: {target}")


def project_section_bounds(text: str) -> tuple[int, int] | None:
    match = re.search(r"(?m)^\[project\]\s*$", text)
    if not match:
        return None
    next_section = re.search(r"(?m)^\[[^\]]+\]\s*$", text[match.end() :])
    end = match.end() + next_section.start() if next_section else len(text)
    return match.start(), end


def has_openai_dependency(project_text: str) -> bool:
    return re.search(r'["\']openai\s*(?:[<>=!~]|["\'])', project_text) is not None


def add_dependency(text: str) -> str:
    bounds = project_section_bounds(text)
    if bounds is None:
        addition = f"\n[project]\ndependencies = [\n  {OPENAI_DEP}\n]\n"
        return text.rstrip() + addition

    start, end = bounds
    project_text = text[start:end]
    if has_openai_dependency(project_text):
        return text

    dep_match = re.search(r"(?ms)^dependencies\s*=\s*\[(.*?)^\]", project_text)
    if dep_match:
        insert_at = start + dep_match.end() - 1
        separator = "" if text[insert_at - 1] == "\n" else "\n"
        return text[:insert_at] + f"{separator}  {OPENAI_DEP}\n" + text[insert_at:]

    header_end = text.find("\n", start) + 1
    addition = f"dependencies = [\n  {OPENAI_DEP}\n]\n"
    return text[:header_end] + addition + text[header_end:]


def project_scripts_bounds(text: str) -> tuple[int, int] | None:
    match = re.search(r"(?m)^\[project\.scripts\]\s*$", text)
    if not match:
        return None
    next_section = re.search(r"(?m)^\[[^\]]+\]\s*$", text[match.end() :])
    end = match.end() + next_section.start() if next_section else len(text)
    return match.start(), end


def add_script_entry(text: str) -> str:
    bounds = project_scripts_bounds(text)
    if bounds is None:
        return text.rstrip() + f"\n\n[project.scripts]\n{SCRIPT_ENTRY}\n"

    start, end = bounds
    scripts_text = text[start:end]
    if re.search(r"(?m)^ai-pr-reviewer\s*=", scripts_text):
        return text

    insertion = SCRIPT_ENTRY + "\n"
    if text[end - 1] != "\n":
        insertion = "\n" + insertion
    return text[:end] + insertion + text[end:]


def merge_pyproject(target_repo: Path) -> None:
    source_pyproject = SOURCE_REPO / "pyproject.toml"
    target_pyproject = target_repo / "pyproject.toml"

    if not target_pyproject.exists():
        shutil.copy2(source_pyproject, target_pyproject)
        print(f"copied: {target_pyproject}")
        return

    original = target_pyproject.read_text(encoding="utf-8")
    updated = add_script_entry(add_dependency(original))
    if updated == original:
        print(f"unchanged: {target_pyproject}")
        return

    target_pyproject.write_text(updated, encoding="utf-8")
    print(f"updated: {target_pyproject}")


def install(target_repo: Path, include_extras: bool, force: bool) -> None:
    ensure_source()
    target_repo = target_repo.expanduser().resolve()
    if not target_repo.exists() or not target_repo.is_dir():
        raise SystemExit(f"Target repo does not exist or is not a directory: {target_repo}")

    for relative in REQUIRED_DIRS:
        copy_path(SOURCE_REPO / relative, target_repo / relative, force)
    for relative in REQUIRED_FILES:
        copy_path(SOURCE_REPO / relative, target_repo / relative, force)

    merge_pyproject(target_repo)

    if include_extras:
        for relative in OPTIONAL_EXTRAS:
            source = SOURCE_REPO / relative
            if source.exists():
                copy_path(source, target_repo / relative, force)

    print("\nNext steps:")
    print("1. Configure GitHub Actions secret AI_API_KEY.")
    print("2. Configure GitHub Actions variable AI_MODEL.")
    print("3. Optionally configure AI_BASE_URL and AI_MAX_TOKENS.")
    print("4. Ensure workflow permissions allow contents: read and pull-requests: write.")
    print("5. Verify locally with: python3 -m compileall ai_pr_reviewer")


def main() -> int:
    args = parse_args()
    install(args.target, args.include_extras, args.force_overwrite)
    return 0


if __name__ == "__main__":
    sys.exit(main())
