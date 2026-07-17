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


class MalformedResponseError(OpenRouterError):
    """A 2xx response whose body is missing the expected completion shape.

    Raised instead of silently returning empty text, so callers never receive a
    ``CompletionResult`` that violates the "non-empty text on success" contract
    (C-1 / SC-001).
    """

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        self.status_code = status_code
        super().__init__(message)


class RetryExhaustedError(OpenRouterError):
    """Raised when transient failures persist past the retry budget.

    ``last_status`` is the final HTTP status (``None`` for a network-level
    failure); ``last_error`` preserves the underlying exception (e.g. a
    ``httpx.ConnectTimeout`` vs ``httpx.ConnectError``) so callers can tell a
    timeout from a connection failure. The exception is also chained via
    ``raise ... from`` at the raise site.
    """

    def __init__(
        self,
        attempts: int,
        last_status: int | None = None,
        last_error: BaseException | None = None,
        message: str | None = None,
    ) -> None:
        self.attempts = attempts
        self.last_status = last_status
        self.last_error = last_error
        if message is None:
            if last_status is not None:
                detail = f"last status: {last_status}"
            elif last_error is not None:
                detail = f"last error: {type(last_error).__name__}: {last_error}"
            else:
                detail = "no further detail"
            message = f"Retries exhausted after {attempts} attempt(s) ({detail})"
        super().__init__(message)
