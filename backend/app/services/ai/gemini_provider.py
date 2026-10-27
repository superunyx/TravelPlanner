import json
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.errors import AppError
from app.services.ai.provider import LLMProvider


class GeminiProvider(LLMProvider):
    """Google Gemini LLM provider implementing JSON output generation."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key
        self.model = model or settings.gemini_model
        self.temperature = 0.7

    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

        generation_config: dict[str, Any] = {
            "temperature": self.temperature,
            "responseMimeType": "application/json",
        }
        if json_schema:
            generation_config["responseSchema"] = json_schema

        payload: dict[str, Any] = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": generation_config,
        }

        try:
            with httpx.Client(timeout=45.0) as client:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            raise AppError(
                status_code=502,
                code="AI_UPSTREAM_ERROR",
                message=f"Gemini API request failed: {exc!s}",
            ) from exc

        try:
            candidates = data.get("candidates", [])
            text_part = candidates[0]["content"]["parts"][0]["text"]
            return json.loads(text_part)  # type: ignore[no-any-return]
        except (IndexError, KeyError, json.JSONDecodeError, TypeError) as exc:
            raise AppError(
                status_code=502,
                code="AI_PARSE_ERROR",
                message=f"Failed to parse JSON response from Gemini: {exc!s}",
            ) from exc
