from __future__ import annotations

from typing import Any


class ReviewModel:
    def __init__(
        self,
        api_key: str,
        base_url: str | None,
        model: str,
        max_tokens: int,
        reasoning_effort: str | None = None,
        reasoning_parameter: str = "reasoning",
    ) -> None:
        from openai import OpenAI

        client_options = {"api_key": api_key}
        if base_url:
            client_options["base_url"] = base_url

        self.client = OpenAI(**client_options)
        self.model = model
        self.max_tokens = max_tokens
        self.reasoning_effort = reasoning_effort
        self.reasoning_parameter = reasoning_parameter

    def review(self, system_prompt: str, user_prompt: str) -> str:
        request = build_chat_completion_request(
            self.model,
            system_prompt,
            user_prompt,
            self.max_tokens,
            self.reasoning_effort,
            self.reasoning_parameter,
        )

        response = self.client.chat.completions.create(**request)

        content = response.choices[0].message.content
        if not content:
            raise ValueError("Model returned an empty response")
        return content


def build_chat_completion_request(
    model: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    reasoning_effort: str | None = None,
    reasoning_parameter: str = "reasoning",
) -> dict[str, Any]:
    request: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.1,
    }

    if reasoning_effort and reasoning_parameter == "reasoning":
        request["reasoning"] = {"effort": reasoning_effort}
    elif reasoning_effort and reasoning_parameter == "reasoning_effort":
        request["reasoning_effort"] = reasoning_effort

    return request
