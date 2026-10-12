"""mini-SWE-agent's OpenRouterModel, with ``extra_headers`` sent as HTTP headers.

Upstream's OpenRouterModel merges every ``model_kwargs`` key into the JSON
body. litellm instead turns ``extra_headers`` into request headers, which is
how the Claude Opus leaderboard entry sent
``anthropic-beta: interleaved-thinking-2025-05-14`` (spec 018). This subclass
does the same over OpenRouter; everything else is upstream's behavior.

Selected with ``--model-class hecate.agent.openrouter_headers.OpenRouterHeadersModel``.
Requires the ``agent`` extra.
"""

from __future__ import annotations

import json

import requests
from minisweagent.models.openrouter_model import (
    OpenRouterAPIError,
    OpenRouterAuthenticationError,
    OpenRouterModel,
    OpenRouterRateLimitError,
)
from minisweagent.models.utils.actions_toolcall import BASH_TOOL


class OpenRouterHeadersModel(OpenRouterModel):
    def _query(self, messages: list[dict[str, str]], **kwargs):
        # The config keeps extra_headers, so the trajectory records it.
        params = self.config.model_kwargs | kwargs
        extra_headers = params.pop("extra_headers", None) or {}
        headers = {
            **extra_headers,
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.config.model_name,
            "messages": messages,
            "tools": [BASH_TOOL],
            "usage": {"include": True},
            **params,
        }
        # Mirrors upstream OpenRouterModel._query (mini-swe-agent 2.0.0),
        # including its 60 s timeout and error mapping.
        try:
            response = requests.post(self._api_url, headers=headers, data=json.dumps(payload), timeout=60)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                raise OpenRouterAuthenticationError("Authentication failed.") from e
            elif response.status_code == 429:
                raise OpenRouterRateLimitError("Rate limit exceeded") from e
            else:
                raise OpenRouterAPIError(f"HTTP {response.status_code}: {response.text}") from e
        except requests.exceptions.RequestException as e:
            raise OpenRouterAPIError(f"Request failed: {e}") from e


__all__ = ["OpenRouterHeadersModel"]
