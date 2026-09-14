"""Isolate durable-artifact env so a developer .env cannot push tests to GCS."""

from __future__ import annotations

import pytest

from hecate.utils.artifacts import ARTIFACTS_URI_ENV, REQUIRE_ARTIFACTS_ENV


@pytest.fixture(autouse=True)
def _isolate_artifacts_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ARTIFACTS_URI_ENV, "")
    monkeypatch.setenv(REQUIRE_ARTIFACTS_ENV, "")
