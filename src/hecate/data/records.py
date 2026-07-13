"""Canonical per-(task, model) generation record schema."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any, Literal

Tier = Literal["small", "large"]


@dataclass
class GenerationRecord:
    """One Stage-1 generation outcome for a (task, model) pair.

    Stage-2 placeholders (``patch_applied``, ``fail_to_pass``, ``pass_to_pass``)
    are always present in serialized form so execution results can be appended
    later without reshaping the schema.
    """

    instance_id: str
    repo: str
    base_commit: str
    model_slug: str
    tier: Tier
    prompt: str | None = None
    prompt_hash: str | None = None
    prompt_ref: str | None = None
    context_files: list[str] = field(default_factory=list)
    raw_response: str | None = None
    extracted_patch: str | None = None
    patch_parse_ok: bool | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    cost_usd: float | None = None
    decoding_params: dict[str, Any] = field(default_factory=dict)
    timestamp: str | None = None
    run_id: str | None = None
    # Stage 2 placeholders — always serialized (null until execution).
    patch_applied: bool | None = None
    fail_to_pass: list[str] | None = None
    pass_to_pass: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dict; Stage-2 keys are always present."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GenerationRecord:
        """Reconstruct a record from ``to_dict`` / JSON object output."""
        known = {f.name for f in fields(cls)}
        payload = {key: value for key, value in data.items() if key in known}
        # Ensure mutable defaults are concrete when missing from older payloads.
        if "context_files" not in payload or payload["context_files"] is None:
            payload["context_files"] = []
        if "decoding_params" not in payload or payload["decoding_params"] is None:
            payload["decoding_params"] = {}
        return cls(**payload)

    def to_json(self, *, indent: int | None = None) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_json(cls, text: str) -> GenerationRecord:
        return cls.from_dict(json.loads(text))


def append_jsonl(path: Path | str, record: GenerationRecord) -> None:
    """Append one record as a JSON line (creates parent dirs as needed)."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(record.to_json())
        handle.write("\n")


def read_jsonl(path: Path | str) -> list[GenerationRecord]:
    """Read all GenerationRecord lines from a JSONL file."""
    target = Path(path)
    records: list[GenerationRecord] = []
    with target.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                records.append(GenerationRecord.from_json(stripped))
            except (json.JSONDecodeError, TypeError, KeyError) as exc:
                raise ValueError(
                    f"Invalid GenerationRecord on line {line_number} of {target}"
                ) from exc
    return records
