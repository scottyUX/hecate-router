"""Tests for .env discovery and API key loading."""

from __future__ import annotations

import pytest

from hecate.utils.env import (
    OPENROUTER_API_KEY_ENV,
    find_dotenv,
    get_openrouter_api_key,
    load_env,
)


def test_find_dotenv_returns_none_when_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert find_dotenv() is None


def test_load_env_reads_api_key_from_dotenv(tmp_path, monkeypatch):
    dotenv = tmp_path / ".env"
    dotenv.write_text(f"{OPENROUTER_API_KEY_ENV}=test-key-123\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(OPENROUTER_API_KEY_ENV, raising=False)

    loaded = load_env(dotenv_path=dotenv)
    assert loaded == dotenv
    assert get_openrouter_api_key() == "test-key-123"


def test_get_openrouter_api_key_required_raises_when_missing(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(OPENROUTER_API_KEY_ENV, raising=False)

    with pytest.raises(RuntimeError, match=OPENROUTER_API_KEY_ENV):
        get_openrouter_api_key(required=True)
