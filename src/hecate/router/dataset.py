"""Join Stage-3 labels with Stage-1 prompts for router training."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol

from hecate.data import GenerationRecord
from hecate.data.external_miniswe import JoinedLabelWithText
from hecate.execution.labels import RoutingLabel


class Tokenizer(Protocol):
    def encode(self, text: str) -> list[Any]: ...

    def decode(self, tokens: list[Any]) -> str: ...


class WhitespaceTokenizer:
    """Offline tokenizer: whitespace words as tokens."""

    def encode(self, text: str) -> list[str]:
        return text.split()

    def decode(self, tokens: list[str]) -> str:
        return " ".join(tokens)


@dataclass(frozen=True)
class RouterExample:
    instance_id: str
    repo: str
    text: str
    truncated: bool
    m1_resolves: bool
    m2_resolves: bool
    prompt_hash: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def truncate_text(
    text: str, tokenizer: Tokenizer, *, max_tokens: int
) -> tuple[str, bool]:
    tokens = tokenizer.encode(text)
    if len(tokens) <= max_tokens:
        return text, False
    return tokenizer.decode(tokens[:max_tokens]), True


def build_examples(
    labels: list[RoutingLabel],
    generations: list[GenerationRecord],
    *,
    tokenizer: Tokenizer,
    max_tokens: int = 2048,
    m1_slug: str | None = None,
) -> tuple[list[RouterExample], dict[str, int]]:
    """Join labels to m1 prompts. Patch text is never concatenated into input."""
    by_pair = {(row.instance_id, row.model_slug): row for row in generations}
    examples: list[RouterExample] = []
    skipped_incomplete = 0
    skipped_no_text = 0
    truncated_n = 0
    for label in labels:
        slug = m1_slug or label.m1_slug
        record = by_pair.get((label.instance_id, slug))
        if record is None:
            skipped_incomplete += 1
            continue
        raw = record.prompt or ""
        if not raw.strip():
            skipped_no_text += 1
            continue
        text, truncated = truncate_text(raw, tokenizer, max_tokens=max_tokens)
        if truncated:
            truncated_n += 1
        examples.append(
            RouterExample(
                instance_id=label.instance_id,
                repo=label.repo,
                text=text,
                truncated=truncated,
                m1_resolves=bool(label.m1_resolves),
                m2_resolves=bool(label.m2_resolves),
                prompt_hash=record.prompt_hash,
            )
        )
    counts = {
        "n_examples": len(examples),
        "skipped_incomplete": skipped_incomplete,
        "skipped_no_text": skipped_no_text,
        "truncated": truncated_n,
    }
    return examples, counts


def build_examples_from_text(
    rows: list[JoinedLabelWithText],
    *,
    tokenizer: Tokenizer | None = None,
    max_tokens: int = 2048,
) -> tuple[list[RouterExample], dict[str, int]]:
    """Build router rows from Verified issue text. Fail closed on empty text.

    Gold ``patch`` / ``test_patch`` are never read. Truncation is optional so
    the live frozen path can log it from the ModernBERT tokenizer instead.
    """
    empty = [row.instance_id for row in rows if not (row.problem_statement or "").strip()]
    if empty:
        raise ValueError(f"{len(empty)} empty problem_statement values: {empty}")
    examples: list[RouterExample] = []
    truncated_n = 0
    for row in rows:
        raw = row.problem_statement
        if tokenizer is None:
            text, truncated = raw, False
        else:
            text, truncated = truncate_text(raw, tokenizer, max_tokens=max_tokens)
        if truncated:
            truncated_n += 1
        examples.append(
            RouterExample(
                instance_id=row.instance_id,
                repo=row.repo,
                text=text,
                truncated=truncated,
                m1_resolves=bool(row.small_model_resolved),
                m2_resolves=bool(row.large_model_resolved),
            )
        )
    counts = {
        "n_examples": len(examples),
        "skipped_incomplete": 0,
        "skipped_no_text": 0,
        "truncated": truncated_n,
    }
    return examples, counts
