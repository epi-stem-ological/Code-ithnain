"""Runtime configuration, loaded from the environment (and .env if present)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = "gemini-2.5-flash"


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or unusable."""


@dataclass(frozen=True)
class Config:
    gemini_api_key: str
    gemini_model: str
    output_dir: Path

    @classmethod
    def from_env(cls) -> "Config":
        key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not key:
            raise ConfigError(
                "GEMINI_API_KEY is not set. Copy .env.example to .env and add your "
                "key from https://aistudio.google.com/apikey"
            )
        output_dir = Path(os.environ.get("YTA_OUTPUT_DIR", "out"))
        output_dir.mkdir(parents=True, exist_ok=True)
        return cls(
            gemini_api_key=key,
            gemini_model=os.environ.get("GEMINI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL,
            output_dir=output_dir,
        )
