"""Smoke tests that core dependencies import after install."""

from __future__ import annotations


def test_core_dependencies_import():
    import httpx  # noqa: F401
    import swebench  # noqa: F401
    import unidiff  # noqa: F401
    import yaml  # noqa: F401
    from dotenv import load_dotenv  # noqa: F401

    assert httpx.__version__
    assert swebench.__version__
