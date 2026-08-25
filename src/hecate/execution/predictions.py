"""Convert Stage-1 generation records into SWE-bench prediction files."""

from __future__ import annotations

import json
from pathlib import Path

from hecate.data import GenerationRecord


def has_executable_patch(record: GenerationRecord) -> bool:
    """True when the record has a non-empty extracted patch that parsed."""
    if record.patch_parse_ok is False:
        return False
    patch = record.extracted_patch
    return bool(patch and patch.strip())


def to_prediction(record: GenerationRecord) -> dict[str, str]:
    """Map a generation record to a SWE-bench prediction row."""
    return {
        "instance_id": record.instance_id,
        "model_name_or_path": record.model_slug,
        "model_patch": record.extracted_patch or "",
    }


def write_predictions(
    records: list[GenerationRecord], path: Path | str
) -> Path:
    """Write JSONL predictions for records that have an executable patch."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        for record in records:
            if not has_executable_patch(record):
                continue
            handle.write(json.dumps(to_prediction(record), ensure_ascii=False))
            handle.write("\n")
    return target
