"""OpenRouter client, generation runner, and patch extraction."""

from __future__ import annotations

from .client import CompletionResult, OpenRouterClient
from .errors import (
    MalformedResponseError,
    MissingCredentialError,
    OpenRouterError,
    PermanentAPIError,
    RetryExhaustedError,
)
from .patch import ExtractionResult, extract_patch
from .runner import RunConfig, RunResult, load_run_config, run_generation

__all__ = [
    "OpenRouterClient",
    "CompletionResult",
    "OpenRouterError",
    "MissingCredentialError",
    "PermanentAPIError",
    "MalformedResponseError",
    "RetryExhaustedError",
    "ExtractionResult",
    "extract_patch",
    "RunConfig",
    "RunResult",
    "load_run_config",
    "run_generation",
]
