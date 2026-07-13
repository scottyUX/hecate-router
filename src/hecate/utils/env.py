"""Environment variable loading for local development."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

OPENROUTER_API_KEY_ENV = "OPENROUTER_API_KEY"


def find_dotenv(start: Path | None = None) -> Path | None:
    """Walk parents from *start* (default: cwd) looking for a `.env` file."""
    current = (start or Path.cwd()).resolve()
    for directory in (current, *current.parents):
        candidate = directory / ".env"
        if candidate.is_file():
            return candidate
    return None


def load_env(*, dotenv_path: Path | str | None = None) -> Path | None:
    """Load variables from `.env` if present. Returns the path loaded, or None."""
    path = Path(dotenv_path) if dotenv_path is not None else find_dotenv()
    if path is None:
        return None
    load_dotenv(path, override=False)
    return path


def get_openrouter_api_key(*, required: bool = False) -> str | None:
    """Return the OpenRouter API key after loading `.env`."""
    load_env()
    value = os.getenv(OPENROUTER_API_KEY_ENV)
    if required and not value:
        raise RuntimeError(
            f"{OPENROUTER_API_KEY_ENV} is not set. "
            "Copy .env.example to .env and add your OpenRouter API key."
        )
    return value
