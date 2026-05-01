from __future__ import annotations

from openai import OpenAI


class ReviewModel:
    def __init__(self, api_key: str, base_url: str | None, model: str, max_tokens: int) -> None:
        client_options = {"api_key": api_key}
        if base_url:
            client_options["base_url"] = base_url

        self.client = OpenAI(**client_options)
        self.model = model
        self.max_tokens = max_tokens

    def review(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise pull request reviewer. Return strict JSON only.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=self.max_tokens,
            temperature=0.1,
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("Model returned an empty response")
        return content
