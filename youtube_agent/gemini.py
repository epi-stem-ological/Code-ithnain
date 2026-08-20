"""Thin wrapper over the google-genai client."""

from __future__ import annotations

from google import genai
from google.genai import types

from .config import Config


class GeminiError(RuntimeError):
    """Raised when the Gemini API call fails or returns nothing usable."""


class GeminiClient:
    def __init__(self, config: Config):
        self._config = config
        self._client = genai.Client(api_key=config.gemini_api_key)

    @property
    def model(self) -> str:
        return self._config.gemini_model

    def generate(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float = 0.3,
        max_output_tokens: int | None = None,
    ) -> str:
        """Send one prompt and return the model's text."""
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )
        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config,
            )
        except Exception as exc:
            raise GeminiError(f"Gemini request failed: {exc}") from exc

        text = (response.text or "").strip()
        if not text:
            raise GeminiError("Gemini returned an empty response")
        return text
