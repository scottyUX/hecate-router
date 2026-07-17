"""Error hierarchy for the OpenRouter client wrapper (S7).

These types let callers distinguish a deterministic client-side failure
(``PermanentAPIError``), an exhausted-retry failure (``RetryExhaustedError``),
and a missing credential (``MissingCredentialError``) — see
``specs/007-openrouter-client/contracts/client-api.md`` (C-6, C-7, C-8).
"""

from __future__ import annotations


class OpenRouterError(Exception):
    """Base class for all OpenRouter client errors."""


class MissingCredentialError(OpenRouterError):
    """Raised at construction when no API key is available.

    Wraps the ``RuntimeError`` raised by
    ``hecate.utils.env.get_openrouter_api_key`` so callers see a single,
    client-specific error type.
    """


class PermanentAPIError(OpenRouterError):
    """A deterministic, non-retryable HTTP failure (any non-429 4xx)."""

    def __init__(self, status_code: int, message: str | None = None) -> None:
        self.status_code = status_code
        super().__init__(message or f"Permanent API error: HTTP {status_code}")


class RetryExhaustedError(OpenRouterError):
    """Raised when transient failures persist past the retry budget."""

    def __init__(
        self,
        attempts: int,
        last_status: int | None = None,
        message: str | None = None,
    ) -> None:
        self.attempts = attempts
        self.last_status = last_status
        super().__init__(
            message
            or f"Retries exhausted after {attempts} attempt(s) "
            f"(last status: {last_status})"
        )
