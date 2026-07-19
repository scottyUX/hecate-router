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

__all__ = [
    "OpenRouterClient",
    "CompletionResult",
    "OpenRouterError",
    "MissingCredentialError",
    "PermanentAPIError",
    "MalformedResponseError",
    "RetryExhaustedError",
]
