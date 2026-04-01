from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from config import settings


class LLMClient:
    def __init__(self) -> None:
        self.enabled = settings.is_llm_runtime_enabled() and bool(settings.LLM_API_KEY)
        self.provider = settings.LLM_PROVIDER
        self.model = settings.LLM_MODEL
        self.api_base = settings.LLM_API_BASE
        self.timeout = settings.LLM_TIMEOUT
        self.temperature = settings.LLM_TEMPERATURE
        self.max_tokens = settings.LLM_MAX_TOKENS
        self._client = None
        if self.enabled:
            self._client = OpenAI(api_key=settings.LLM_API_KEY, base_url=self.api_base, timeout=self.timeout)

    def is_available(self) -> bool:
        return self.enabled and self._client is not None

    def generate_json(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        if not self.is_available():
            raise RuntimeError("LLM client is not available")
        response = self._client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = response.choices[0].message.content or "{}"
        return json.loads(content)
