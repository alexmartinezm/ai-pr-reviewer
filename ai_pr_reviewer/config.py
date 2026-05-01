from __future__ import annotations

import json
import os
from dataclasses import dataclass


DEFAULT_MAX_TOKENS = 4000
REASONING_EFFORT_VALUES = {"none", "minimal", "low", "medium", "high", "xhigh"}
REASONING_PARAMETER_VALUES = {"reasoning", "reasoning_effort"}
DEFAULT_REASONING_PARAMETER = "reasoning"


@dataclass(frozen=True)
class Config:
    github_token: str
    github_repository: str
    pull_request_number: int
    api_key: str
    model: str
    base_url: str | None = None
    reasoning_effort: str | None = None
    reasoning_parameter: str = DEFAULT_REASONING_PARAMETER
    max_tokens: int = DEFAULT_MAX_TOKENS
    dry_run: bool = False

    @property
    def owner(self) -> str:
        return self.github_repository.split("/", 1)[0]

    @property
    def repo(self) -> str:
        return self.github_repository.split("/", 1)[1]


def load_config() -> Config:
    github_repository = _required_env("GITHUB_REPOSITORY")
    if "/" not in github_repository:
        raise ValueError("GITHUB_REPOSITORY must be in the form owner/repo")

    return Config(
        github_token=_required_env("GITHUB_TOKEN"),
        github_repository=github_repository,
        pull_request_number=_pull_request_number(),
        api_key=_required_env("AI_API_KEY"),
        model=_required_env("AI_MODEL"),
        base_url=_optional_env("AI_BASE_URL"),
        reasoning_effort=_reasoning_effort_env("AI_REASONING_EFFORT"),
        reasoning_parameter=_reasoning_parameter_env("AI_REASONING_PARAMETER"),
        max_tokens=_int_env("AI_MAX_TOKENS", DEFAULT_MAX_TOKENS),
        dry_run=_bool_env("AI_REVIEW_DRY_RUN"),
    )


def _pull_request_number() -> int:
    value = os.getenv("PR_NUMBER") or os.getenv("GITHUB_EVENT_PULL_REQUEST_NUMBER")
    if value:
        try:
            return int(value.strip())
        except ValueError:
            raise ValueError(f"PR_NUMBER is not a valid integer: {value!r}")

    event_path = os.getenv("GITHUB_EVENT_PATH")
    if not event_path:
        raise ValueError("Set PR_NUMBER or run inside a pull_request GitHub Actions event")

    try:
        with open(event_path, "r", encoding="utf-8") as event_file:
            event = json.load(event_file)
    except OSError as exc:
        raise ValueError(f"Could not read GITHUB_EVENT_PATH={event_path!r}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"GITHUB_EVENT_PATH contains invalid JSON: {exc}") from exc

    pull_request = event.get("pull_request") or {}
    number = pull_request.get("number") or event.get("number")
    if not number:
        raise ValueError("Could not determine pull request number from GITHUB_EVENT_PATH")
    return int(number)


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value or not value.strip():
        raise ValueError(f"Missing required environment variable: {name}")
    return value.strip()


def _optional_env(name: str) -> str | None:
    value = os.getenv(name)
    if not value or not value.strip():
        return None
    return value.strip()


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value or not value.strip():
        return default
    try:
        return int(value.strip())
    except ValueError:
        raise ValueError(f"{name} must be an integer, got: {value!r}")


def _reasoning_effort_env(name: str) -> str | None:
    value = _optional_env(name)
    if value is None:
        return None

    normalized = value.lower()
    if normalized not in REASONING_EFFORT_VALUES:
        allowed = ", ".join(sorted(REASONING_EFFORT_VALUES))
        raise ValueError(f"{name} must be one of: {allowed}")
    return normalized


def _reasoning_parameter_env(name: str) -> str:
    value = _optional_env(name)
    if value is None:
        return DEFAULT_REASONING_PARAMETER

    normalized = value.lower()
    if normalized not in REASONING_PARAMETER_VALUES:
        allowed = ", ".join(sorted(REASONING_PARAMETER_VALUES))
        raise ValueError(f"{name} must be one of: {allowed}")
    return normalized


def _bool_env(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}
