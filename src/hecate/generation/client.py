"""Stage-1 OpenRouter client wrapper (S7).

An async client that sends one rendered prompt (S6) to a configured model slug
and returns generated text plus token usage, using the run's fixed decoding
params. It applies a per-request timeout, retries transient failures
(429 or any 5xx, plus timeout/connection errors) with bounded exponential
back-off + full jitter, fails fast on other 4xx, and caps concurrency with an
``asyncio.Semaphore``.

Design + contracts: ``specs/007-openrouter-client/``. Out of scope here: cost /
budget (``hecate.cost``), patch extraction (S8), caching (S9), and the JSONL
generation runner (S11+).
"""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable

import httpx
import yaml

from hecate.utils.env import get_openrouter_api_key

from .errors import (
    MalformedResponseError,
    MissingCredentialError,
    PermanentAPIError,
    RetryExhaustedError,
)

CHAT_COMPLETIONS_PATH = "/chat/completions"

# Request-body keys the client owns; decoding overrides must never set these,
# otherwise a caller could replace the validated prompt or model slug.
RESERVED_BODY_KEYS = frozenset({"model", "messages"})

DEFAULT_TIMEOUT = 60.0
DEFAULT_MAX_RETRIES = 4
DEFAULT_MAX_CONCURRENCY = 8
DEFAULT_BACKOFF_BASE = 0.5
DEFAULT_BACKOFF_CAP = 30.0


@dataclass(frozen=True)
class CompletionResult:
    """The output of one model call.

    ``text`` (a string) is what maps onto ``GenerationRecord.raw_response``.
    ``raw_json`` is a debugging aid only and is intentionally *not* named
    ``raw_response`` to avoid confusion with that string record field.
    """

    model_slug: str
    text: str
    prompt_tokens: int | None
    completion_tokens: int | None
    decoding_params: dict[str, Any]
    finish_reason: str | None = None
    raw_json: dict[str, Any] | None = None


@dataclass(frozen=True)
class _ClientConfig:
    base_url: str
    temperature: float
    max_tokens: int
    model_slugs: tuple[str, ...]


def _repo_root() -> Path:
    # src/hecate/generation/client.py -> repo root is parents[3]
    return Path(__file__).resolve().parents[3]


def _default_config_path() -> Path:
    return _repo_root() / "configs" / "option_a.yaml"


def _load_config(config_path: Path | str | None) -> _ClientConfig:
    path = Path(config_path) if config_path is not None else _default_config_path()
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    base_url = data.get("base_url")
    if not base_url:
        raise ValueError(f"'base_url' missing from config: {path}")
    decoding = data.get("decoding", {}) or {}
    slugs = tuple(
        model["slug"]
        for model in (data.get("models", []) or [])
        if isinstance(model, dict) and model.get("slug")
    )
    return _ClientConfig(
        base_url=base_url,
        temperature=decoding.get("temperature", 0.0),
        max_tokens=decoding.get("max_tokens", 4096),
        model_slugs=slugs,
    )


def _is_transient_status(status: int) -> bool:
    """Transient (retryable) iff HTTP 429 or any 5xx (500 <= status < 600)."""
    return status == 429 or 500 <= status < 600


class OpenRouterClient:
    """Async OpenRouter chat-completions client for Stage-1 generation."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        config_path: Path | str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        max_concurrency: int = DEFAULT_MAX_CONCURRENCY,
        backoff_base: float = DEFAULT_BACKOFF_BASE,
        backoff_cap: float = DEFAULT_BACKOFF_CAP,
        transport: httpx.AsyncBaseTransport | None = None,
        validate_slug: bool = True,
        sleep: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        if max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        if max_concurrency <= 0:
            raise ValueError("max_concurrency must be positive")

        # Resolve credential. The S2 loader raises RuntimeError when absent;
        # re-raise as MissingCredentialError so callers see the contract type.
        if not api_key:
            try:
                api_key = get_openrouter_api_key(required=True)
            except RuntimeError as exc:
                raise MissingCredentialError(str(exc)) from exc
        # Stored privately; never placed in repr/logs/exception messages (C-10).
        self._api_key = api_key

        config = _load_config(config_path)
        self._endpoint = config.base_url.rstrip("/") + CHAT_COMPLETIONS_PATH
        self._decoding_defaults: dict[str, Any] = {
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
        }
        self._model_slugs = set(config.model_slugs)
        self._validate_slug = validate_slug

        self._timeout = timeout
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._backoff_cap = backoff_cap
        self._sleep = sleep if sleep is not None else asyncio.sleep

        self._client = httpx.AsyncClient(
            base_url=config.base_url,
            transport=transport,
            timeout=timeout,
        )
        self._semaphore = asyncio.Semaphore(max_concurrency)

    def __repr__(self) -> str:  # never leak the api key
        return (
            f"OpenRouterClient(endpoint={self._endpoint!r}, "
            f"timeout={self._timeout}, max_retries={self._max_retries})"
        )

    async def complete(
        self,
        *,
        model_slug: str,
        prompt: str,
        decoding: dict[str, Any] | None = None,
    ) -> CompletionResult:
        """Send one prompt to ``model_slug`` and return text + token usage."""
        if not prompt:
            raise ValueError("prompt must be non-empty")
        if self._validate_slug and model_slug not in self._model_slugs:
            raise ValueError(
                f"Unknown model slug: {model_slug!r}. Configured slugs: "
                f"{sorted(self._model_slugs)}"
            )

        resolved = {**self._decoding_defaults, **(decoding or {})}
        reserved_conflicts = RESERVED_BODY_KEYS & resolved.keys()
        if reserved_conflicts:
            raise ValueError(
                "decoding must not set reserved request keys "
                f"{sorted(reserved_conflicts)}; the client owns 'model' and "
                "'messages'."
            )
        # Reserved fields are written LAST so they can never be overridden by
        # decoding params, preserving prompt fidelity and the requested slug.
        body: dict[str, Any] = {
            **resolved,
            "model": model_slug,
            "messages": [{"role": "user", "content": prompt}],
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        async with self._semaphore:
            return await self._request_with_retry(model_slug, body, headers, resolved)

    async def _request_with_retry(
        self,
        model_slug: str,
        body: dict[str, Any],
        headers: dict[str, str],
        resolved_decoding: dict[str, Any],
    ) -> CompletionResult:
        max_attempts = self._max_retries + 1
        last_status: int | None = None
        last_error: BaseException | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                response = await self._client.post(
                    self._endpoint,
                    json=body,
                    headers=headers,
                    timeout=self._timeout,
                )
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_status = None
                last_error = exc
                if attempt >= max_attempts:
                    raise RetryExhaustedError(
                        attempts=attempt, last_status=None, last_error=exc
                    ) from exc
                await self._sleep(self._backoff_delay(attempt))
                continue

            status = response.status_code
            if 200 <= status < 300:
                return self._parse(model_slug, response, resolved_decoding)

            if _is_transient_status(status):
                last_status = status
                last_error = None
                if attempt >= max_attempts:
                    raise RetryExhaustedError(attempts=attempt, last_status=status)
                await self._sleep(self._backoff_delay(attempt, response))
                continue

            detail = (response.text or "").strip()
            if len(detail) > 500:
                detail = detail[:500] + "…"
            raise PermanentAPIError(
                status_code=status,
                message=(
                    f"Permanent API error: HTTP {status}"
                    + (f" — {detail}" if detail else "")
                ),
            )

        raise RetryExhaustedError(
            attempts=max_attempts, last_status=last_status, last_error=last_error
        ) from last_error

    def _backoff_delay(
        self, attempt: int, response: httpx.Response | None = None
    ) -> float:
        """Bounded exponential back-off with full jitter; honor Retry-After."""
        ceiling = min(self._backoff_cap, self._backoff_base * (2 ** (attempt - 1)))
        delay = random.uniform(0, ceiling)
        if response is not None and response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                try:
                    delay = max(delay, float(retry_after))
                except ValueError:
                    pass
        return delay

    def _parse(
        self,
        model_slug: str,
        response: httpx.Response,
        resolved_decoding: dict[str, Any],
    ) -> CompletionResult:
        try:
            data = response.json()
        except ValueError as exc:
            raise MalformedResponseError(
                "OpenRouter returned a non-JSON success body",
                status_code=response.status_code,
            ) from exc

        choices = data.get("choices") if isinstance(data, dict) else None
        if not isinstance(choices, list) or not choices:
            raise MalformedResponseError(
                "OpenRouter success response has no 'choices'",
                status_code=response.status_code,
            )
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content:
            raise MalformedResponseError(
                "OpenRouter success response has empty or missing "
                "'choices[0].message.content'",
                status_code=response.status_code,
            )
        text = content
        choice = choices[0]
        usage = data.get("usage") or {}
        return CompletionResult(
            model_slug=model_slug,
            text=text,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            decoding_params=dict(resolved_decoding),
            finish_reason=choice.get("finish_reason"),
            raw_json=data,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> OpenRouterClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()
