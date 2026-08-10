"""Stage-1 prompt template: frozen, versioned instruction string for one task.

Every model in a run receives byte-identical prompts for the same task — the
prompt is the shared scaffold; only the model slug varies at call time.
Single-shot: one prompt → one unified diff; no tool loop.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from hecate.data.tasks import SwebenchTask
from hecate.scaffold.context import ContextBundle

# v5: v4 instructions plus one short valid unified-diff example.
PROMPT_VERSION = "v5"


def _repo_root() -> Path:
    # src/hecate/scaffold/prompt.py -> repo root is parents[3]
    return Path(__file__).resolve().parents[3]


def _default_prompt_dir() -> Path:
    return _repo_root() / "data" / "cache" / "prompts"


def render_prompt(
    task: SwebenchTask,
    context: ContextBundle,
    *,
    version: str | None = None,
) -> str:
    """Deterministic Stage-1 prompt for one task.

    Same task + same context + same version → identical bytes for every model.
    Does not include the gold patch.
    """
    resolved_version = PROMPT_VERSION if version is None else version
    if resolved_version != PROMPT_VERSION:
        raise ValueError(f"Unsupported prompt version: {resolved_version!r}")

    sections = [
        f"You are fixing a GitHub issue in {task.repo}.",
        f"Instance: {task.instance_id}",
        "",
        "## Issue",
        task.problem_statement,
        "",
        "## Relevant files (at base_commit)",
    ]

    if not context.files:
        sections.append("(no files provided)")
        sections.append("")
    else:
        for context_file in context.files:
            sections.append(f"### {context_file.path}")
            sections.append("")
            sections.append(context_file.content)
            sections.append("")

    sections.extend(
        [
            "## Instructions",
            "Respond with a single unified diff that applies the fix.",
            "Use ---/+++ file headers and @@ hunk headers for every change.",
            "Do not include explanations outside the diff.",
            "",
            "Example of a valid unified diff:",
            "--- a/path/file.py",
            "+++ b/path/file.py",
            "@@ -1,3 +1,3 @@",
            " unchanged context",
            "-old line",
            "+new line",
        ]
    )

    return "\n".join(sections)


def prompt_hash(prompt: str) -> str:
    """SHA-256 hex digest of UTF-8 prompt bytes (for records and cache keys)."""
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def write_prompt(
    prompt: str,
    *,
    output_dir: Path | str | None = None,
) -> str:
    """Persist a rendered prompt; return a path string suitable for ``prompt_ref``."""
    directory = Path(output_dir) if output_dir is not None else _default_prompt_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{prompt_hash(prompt)}.txt"
    path.write_text(prompt, encoding="utf-8")
    return str(path)
