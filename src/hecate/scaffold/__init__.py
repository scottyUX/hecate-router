"""Stage-1 prompt template: render a frozen, versioned prompt from a task and its context.

Every model in a run receives byte-identical prompts for the same task — the
prompt is the shared scaffold; only the model slug varies at call time.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from hecate.data.tasks import SwebenchTask

PROMPT_VERSION = "v1"


@dataclass(frozen=True)
class ContextFile:
    """One file supplied as context for a task, at its base commit."""

    path: str
    content: str


@dataclass(frozen=True)
class ContextBundle:
    """File context for one task, as selected by S5 (oracle or BM25).

    Placeholder shape pending S5's context builder — S6 only needs a path and
    contents per file, independent of how the files were selected.
    """

    files: list[ContextFile] = field(default_factory=list)


def render_prompt(
    task: SwebenchTask, context: ContextBundle, *, version: str = PROMPT_VERSION
) -> str:
    """Deterministic Stage-1 prompt for one task. Same inputs -> same string for every model."""
    if version != PROMPT_VERSION:
        raise ValueError(f"Unsupported prompt version: {version!r}")

    sections = [
        f"You are fixing a GitHub issue in {task.repo}.",
        "",
        "## Issue",
        task.problem_statement,
        "",
        "## Relevant files (at base_commit)",
    ]

    for context_file in sorted(context.files, key=lambda f: f.path):
        sections.append(f"### {context_file.path}")
        sections.append("")
        sections.append(context_file.content)
        sections.append("")

    sections.extend(
        [
            "## Instructions",
            "Respond with a single unified diff that applies the fix.",
            "Do not include explanations outside the diff.",
        ]
    )

    return "\n".join(sections)


def prompt_hash(prompt: str) -> str:
    """Content hash of a rendered prompt, for cache keys and record storage."""
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


__all__ = [
    "PROMPT_VERSION",
    "ContextBundle",
    "ContextFile",
    "prompt_hash",
    "render_prompt",
]
