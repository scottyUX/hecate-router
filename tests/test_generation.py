"""Offline tests for the S7 OpenRouter client wrapper.

Every test uses ``httpx.MockTransport`` so nothing touches the network — the
suite runs with zero provider spend and without ``OPENROUTER_API_KEY`` set
(spec FR-012 / SC-005). A single opt-in live smoke test is doubly gated behind
``RUN_LIVE_TESTS=1`` *and* ``OPENROUTER_API_KEY``.
"""

from __future__ import annotations

import asyncio
import json
import os

import httpx
import pytest

from hecate.generation import (
    CompletionResult,
    MalformedResponseError,
    MissingCredentialError,
    OpenRouterClient,
    PermanentAPIError,
    RetryExhaustedError,
)

# A slug that exists in configs/option_a.yaml.
SLUG = "meta-llama/llama-3.1-8b-instruct"

SUCCESS_BODY = {
    "choices": [
        {
            "message": {"content": "diff --git a/x b/x\n"},
            "finish_reason": "stop",
        }
    ],
    "usage": {"prompt_tokens": 12, "completion_tokens": 7},
}


async def _no_sleep(_delay: float) -> None:
    """Back-off sleep replacement so retry tests run instantly."""
    return None


def make_client(handler, **kwargs) -> OpenRouterClient:
    """Build a client wired to a MockTransport and an instant back-off sleep."""
    kwargs.setdefault("api_key", "test-key")
    kwargs.setdefault("sleep", _no_sleep)
    return OpenRouterClient(transport=httpx.MockTransport(handler), **kwargs)


def sequence_handler(items):
    """Handler that yields successive items (Response or Exception) per call."""
    state = {"i": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        index = min(state["i"], len(items) - 1)
        state["i"] += 1
        item = items[index]
        if isinstance(item, Exception):
            raise item
        return item

    return handler, state


# --------------------------------------------------------------------------
# User Story 1 — single call returns text + usage
# --------------------------------------------------------------------------


async def test_complete_returns_text_and_usage():  # T008
    async with make_client(lambda r: httpx.Response(200, json=SUCCESS_BODY)) as client:
        result = await client.complete(model_slug=SLUG, prompt="fix the bug")

    assert isinstance(result, CompletionResult)
    assert result.text.startswith("diff --git")
    assert result.prompt_tokens == 12
    assert result.completion_tokens == 7
    assert result.model_slug == SLUG
    assert result.finish_reason == "stop"


async def test_decoding_params_from_config_and_override():  # T009
    captured: dict[str, dict] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json=SUCCESS_BODY)

    async with make_client(handler) as client:
        result = await client.complete(model_slug=SLUG, prompt="hi")
        assert captured["body"]["temperature"] == 0.0
        assert captured["body"]["max_tokens"] == 4096
        assert result.decoding_params["temperature"] == 0.0
        assert result.decoding_params["max_tokens"] == 4096

        overridden = await client.complete(
            model_slug=SLUG, prompt="hi", decoding={"temperature": 0.7}
        )
        assert captured["body"]["temperature"] == 0.7
        assert overridden.decoding_params["temperature"] == 0.7
        # non-overridden defaults still present
        assert overridden.decoding_params["max_tokens"] == 4096


async def test_prompt_sent_verbatim_and_missing_usage_is_none():  # T010
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["messages"] == [{"role": "user", "content": "verbatim PROMPT"}]
        # response omits "usage"
        return httpx.Response(200, json={"choices": [{"message": {"content": "x"}}]})

    async with make_client(handler) as client:
        result = await client.complete(model_slug=SLUG, prompt="verbatim PROMPT")

    assert result.text == "x"
    assert result.prompt_tokens is None
    assert result.completion_tokens is None


def test_missing_credential_translates_runtime_error(monkeypatch):  # T011
    def boom(*_args, **_kwargs):
        raise RuntimeError("OPENROUTER_API_KEY is not set.")

    monkeypatch.setattr("hecate.generation.client.get_openrouter_api_key", boom)

    called = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        called["n"] += 1
        return httpx.Response(200, json=SUCCESS_BODY)

    with pytest.raises(MissingCredentialError):
        OpenRouterClient(transport=httpx.MockTransport(handler))  # no api_key

    assert called["n"] == 0  # never attempted a request


async def test_timeout_is_propagated_to_request():  # T012 (FR-004)
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["timeout"] = request.extensions.get("timeout")
        return httpx.Response(200, json=SUCCESS_BODY)

    async with make_client(handler, timeout=12.5) as client:
        await client.complete(model_slug=SLUG, prompt="hi")

    assert captured["timeout"]["read"] == 12.5


async def test_request_targets_configured_base_url():  # T013 (FR-011)
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, json=SUCCESS_BODY)

    async with make_client(handler) as client:
        await client.complete(model_slug=SLUG, prompt="hi")

    assert captured["url"] == "https://openrouter.ai/api/v1/chat/completions"


async def test_unknown_slug_rejected_before_request():  # T014 (FR-011)
    called = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        called["n"] += 1
        return httpx.Response(200, json=SUCCESS_BODY)

    async with make_client(handler) as client:
        with pytest.raises(ValueError):
            await client.complete(model_slug="nope/not-a-model", prompt="hi")
        assert called["n"] == 0

    # validate_slug=False allows any slug through
    async with make_client(handler, validate_slug=False) as client:
        result = await client.complete(model_slug="nope/not-a-model", prompt="hi")
        assert result.text


async def test_empty_prompt_rejected():
    async with make_client(lambda r: httpx.Response(200, json=SUCCESS_BODY)) as client:
        with pytest.raises(ValueError):
            await client.complete(model_slug=SLUG, prompt="")


async def test_decoding_cannot_override_model_or_messages():  # P1
    captured: dict[str, dict] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json=SUCCESS_BODY)

    async with make_client(handler) as client:
        for reserved in ({"model": "attacker/model"}, {"messages": [{"x": 1}]}):
            with pytest.raises(ValueError):
                await client.complete(
                    model_slug=SLUG, prompt="real prompt", decoding=reserved
                )

        # A benign decoding override still goes through with reserved fields intact.
        result = await client.complete(
            model_slug=SLUG, prompt="real prompt", decoding={"top_p": 0.9}
        )
    assert captured["body"]["model"] == SLUG
    assert captured["body"]["messages"] == [{"role": "user", "content": "real prompt"}]
    assert captured["body"]["top_p"] == 0.9
    assert result.model_slug == SLUG


async def test_empty_or_malformed_success_body_raises():  # P2 (shape validation)
    # 2xx with no choices
    async with make_client(lambda r: httpx.Response(200, json={})) as client:
        with pytest.raises(MalformedResponseError):
            await client.complete(model_slug=SLUG, prompt="hi")

    # 2xx with empty content string
    empty_content = {"choices": [{"message": {"content": ""}}]}
    async with make_client(lambda r: httpx.Response(200, json=empty_content)) as client:
        with pytest.raises(MalformedResponseError):
            await client.complete(model_slug=SLUG, prompt="hi")

    # 2xx with non-JSON body
    async with make_client(lambda r: httpx.Response(200, text="not json")) as client:
        with pytest.raises(MalformedResponseError):
            await client.complete(model_slug=SLUG, prompt="hi")


# --------------------------------------------------------------------------
# User Story 2 — survive transient failures
# --------------------------------------------------------------------------


async def test_retry_on_429_then_success():  # T018
    handler, state = sequence_handler(
        [httpx.Response(429), httpx.Response(200, json=SUCCESS_BODY)]
    )
    async with make_client(handler) as client:
        result = await client.complete(model_slug=SLUG, prompt="hi")
    assert result.text.startswith("diff")
    assert state["i"] == 2


async def test_retry_on_503_then_success():  # T018
    handler, _ = sequence_handler(
        [httpx.Response(503), httpx.Response(200, json=SUCCESS_BODY)]
    )
    async with make_client(handler) as client:
        result = await client.complete(model_slug=SLUG, prompt="hi")
    assert result.text.startswith("diff")


async def test_uncommon_5xx_is_transient():  # T019 (I1: 500 <= status < 600)
    handler, _ = sequence_handler(
        [httpx.Response(520), httpx.Response(200, json=SUCCESS_BODY)]
    )
    async with make_client(handler) as client:
        result = await client.complete(model_slug=SLUG, prompt="hi")
    assert result.text.startswith("diff")


async def test_persistent_transient_raises_retry_exhausted():  # T020
    async with make_client(lambda r: httpx.Response(503), max_retries=2) as client:
        with pytest.raises(RetryExhaustedError) as excinfo:
            await client.complete(model_slug=SLUG, prompt="hi")
    assert excinfo.value.attempts == 3  # max_retries + 1
    assert excinfo.value.last_status == 503


async def test_permanent_4xx_fails_fast():  # T021
    called = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        called["n"] += 1
        return httpx.Response(401)

    async with make_client(handler) as client:
        with pytest.raises(PermanentAPIError) as excinfo:
            await client.complete(model_slug=SLUG, prompt="hi")
    assert excinfo.value.status_code == 401
    assert called["n"] == 1  # no retries


async def test_connection_and_timeout_errors_are_retried():  # T022
    handler, _ = sequence_handler(
        [
            httpx.ConnectError("boom"),
            httpx.ReadTimeout("slow"),
            httpx.Response(200, json=SUCCESS_BODY),
        ]
    )
    async with make_client(handler, max_retries=4) as client:
        result = await client.complete(model_slug=SLUG, prompt="hi")
    assert result.text.startswith("diff")


async def test_network_exhaustion_preserves_underlying_error():  # P2 (chaining)
    handler, _ = sequence_handler([httpx.ConnectError("no route to host")])
    async with make_client(handler, max_retries=1) as client:
        with pytest.raises(RetryExhaustedError) as excinfo:
            await client.complete(model_slug=SLUG, prompt="hi")

    err = excinfo.value
    assert err.attempts == 2
    assert err.last_status is None
    assert isinstance(err.last_error, httpx.ConnectError)
    # Exception is chained so the root cause is not lost.
    assert isinstance(err.__cause__, httpx.ConnectError)
    assert "ConnectError" in str(err)


# --------------------------------------------------------------------------
# User Story 3 — bounded concurrency
# --------------------------------------------------------------------------


async def test_concurrency_capped():  # T025
    state = {"inflight": 0, "peak": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        state["inflight"] += 1
        state["peak"] = max(state["peak"], state["inflight"])
        await asyncio.sleep(0.01)
        state["inflight"] -= 1
        return httpx.Response(200, json=SUCCESS_BODY)

    async with make_client(handler, max_concurrency=3) as client:
        await asyncio.gather(
            *(client.complete(model_slug=SLUG, prompt="hi") for _ in range(12))
        )

    assert state["peak"] <= 3
    assert state["peak"] > 0


# --------------------------------------------------------------------------
# Opt-in live smoke test (doubly gated; never runs in CI)
# --------------------------------------------------------------------------


@pytest.mark.live
async def test_live_smoke():  # T027
    if not (os.getenv("RUN_LIVE_TESTS") == "1" and os.getenv("OPENROUTER_API_KEY")):
        pytest.skip("live test requires RUN_LIVE_TESTS=1 and OPENROUTER_API_KEY")

    async with OpenRouterClient(max_concurrency=1) as client:
        result = await client.complete(
            model_slug=SLUG, prompt="Reply with a single word."
        )
    assert result.text
    assert result.prompt_tokens and result.completion_tokens
