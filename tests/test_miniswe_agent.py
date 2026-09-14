"""Offline tests for optional mini-SWE-agent wiring (no Docker / no API)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from hecate.agent.miniswe import (
    INSTALL_HINT,
    MinisweNotInstalledError,
    argv_from_config,
    build_swebench_single_argv,
    load_miniswe_config,
    require_miniswe,
    run_swebench_single,
)


def test_build_swebench_single_argv_defaults() -> None:
    argv = build_swebench_single_argv(
        instance="django__django-10914",
        model="openrouter/qwen/qwen-2.5-7b-instruct",
    )
    assert argv[:2] == ["mini-extra", "swebench-single"]
    assert "--subset" in argv and argv[argv.index("--subset") + 1] == "lite"
    assert "--split" in argv and argv[argv.index("--split") + 1] == "test"
    assert "--model" in argv
    assert argv[argv.index("--model") + 1] == "openrouter/qwen/qwen-2.5-7b-instruct"
    assert "--instance" in argv
    assert argv[argv.index("--instance") + 1] == "django__django-10914"
    assert "--exit-immediately" in argv


def test_build_swebench_single_argv_optional_flags() -> None:
    argv = build_swebench_single_argv(
        instance="0",
        model="openrouter/qwen/qwen-2.5-7b-instruct",
        output="/tmp/out.traj.json",
        cost_limit=2.5,
        environment_class="docker",
        exit_immediately=False,
    )
    assert "--output" in argv and argv[argv.index("--output") + 1] == "/tmp/out.traj.json"
    assert "--cost-limit" in argv and argv[argv.index("--cost-limit") + 1] == "2.5"
    assert "--environment-class" in argv
    assert argv[argv.index("--environment-class") + 1] == "docker"
    assert "--exit-immediately" not in argv


def test_load_miniswe_config_defaults(tmp_path: Path) -> None:
    repo_config = Path("configs/miniswe.yaml")
    assert repo_config.is_file()
    data = load_miniswe_config(str(repo_config))
    assert data["scaffold"]["subset"] == "lite"
    assert "qwen" in data["defaults"]["model"]

    argv = argv_from_config(
        data,
        instance="django__django-10914",
    )
    assert "django__django-10914" in argv
    assert data["defaults"]["model"] in argv


def test_require_miniswe_raises_when_missing() -> None:
    # sys.modules[name] = None makes ``import name`` raise ImportError.
    with patch.dict("sys.modules", {"minisweagent": None}):
        with pytest.raises(MinisweNotInstalledError) as excinfo:
            require_miniswe()
    message = str(excinfo.value)
    assert "not installed" in message
    assert INSTALL_HINT in message


def test_run_swebench_single_dry_run_with_fake_module() -> None:
    import types

    fake = types.ModuleType("minisweagent")
    with patch.dict("sys.modules", {"minisweagent": fake}):
        # No console script beside the interpreter, so PATH lookup is used.
        with patch("hecate.agent.miniswe.sys.executable", "/nowhere/bin/python"), patch(
            "hecate.agent.miniswe.shutil.which", return_value="/usr/bin/mini-extra"
        ):
            result = run_swebench_single(
                instance="django__django-10914",
                model="openrouter/qwen/qwen-2.5-7b-instruct",
                subset="lite",
                split="test",
                dry_run=True,
            )
    assert result.dry_run is True
    assert result.returncode == 0
    assert result.argv[0] == "/usr/bin/mini-extra"
    assert "swebench-single" in result.argv
    assert "django__django-10914" in result.argv


def test_mini_extra_prefers_interpreter_sibling_over_path(tmp_path: Path) -> None:
    """PATH may hold a mini-extra from another venv, which would run the agent
    under a different Python than the caller's."""
    from hecate.agent.miniswe import _resolve_mini_extra

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    sibling = bin_dir / "mini-extra"
    sibling.write_text("#!/bin/sh\n", encoding="utf-8")

    with patch("hecate.agent.miniswe.sys.executable", str(bin_dir / "python")), patch(
        "hecate.agent.miniswe.shutil.which", return_value="/other/venv/bin/mini-extra"
    ):
        assert _resolve_mini_extra() == str(sibling)


def test_explicit_mini_extra_wins_over_sibling(tmp_path: Path) -> None:
    from hecate.agent.miniswe import _resolve_mini_extra

    assert _resolve_mini_extra("/custom/mini-extra") == "/custom/mini-extra"
