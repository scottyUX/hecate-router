"""Run manifest helpers for Stage-1 reproducibility."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


def git_commit_sha(*, cwd: Path | str | None = None) -> str | None:
    """Return current HEAD SHA, or None if git is unavailable."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    sha = result.stdout.strip()
    return sha or None


def write_run_manifest(path: Path | str, payload: dict[str, Any]) -> Path:
    """Write a JSON run manifest (creates parent dirs). Returns the path."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return target
