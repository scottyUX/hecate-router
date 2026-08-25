"""SWE-bench Lite/Verified loading and canonical record schema."""

from hecate.data.records import (
    GenerationRecord,
    Tier,
    append_jsonl,
    read_jsonl,
)
from hecate.data.tasks import (
    SWEBENCH_LITE_DATASET,
    SWEBENCH_LITE_EXPECTED_COUNT,
    SWEBENCH_LITE_SPLIT,
    SWEBENCH_VERIFIED_DATASET,
    SWEBENCH_VERIFIED_EXPECTED_COUNT,
    SWEBENCH_VERIFIED_SPLIT,
    SwebenchTask,
    get_task,
    load_swebench_lite,
    load_swebench_verified,
)

__all__ = [
    "SWEBENCH_LITE_DATASET",
    "SWEBENCH_LITE_EXPECTED_COUNT",
    "SWEBENCH_LITE_SPLIT",
    "SWEBENCH_VERIFIED_DATASET",
    "SWEBENCH_VERIFIED_EXPECTED_COUNT",
    "SWEBENCH_VERIFIED_SPLIT",
    "GenerationRecord",
    "SwebenchTask",
    "Tier",
    "append_jsonl",
    "get_task",
    "load_swebench_lite",
    "load_swebench_verified",
    "read_jsonl",
]
