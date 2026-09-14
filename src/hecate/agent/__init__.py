"""Optional mini-SWE-agent scaffold (parallel to Stage-1 single-shot)."""

from hecate.agent.batch import (
    MinisweBatchResult,
    build_swebench_batch_argv,
    run_swebench_batch,
)
from hecate.agent.convert import (
    AgentOutcome,
    MinisweConvertError,
    build_records,
    outcome_to_record,
    read_outcomes,
    read_preds,
    write_generations,
)
from hecate.agent.miniswe import (
    MinisweNotInstalledError,
    MinisweRunResult,
    build_swebench_single_argv,
    require_miniswe,
    run_swebench_single,
)

__all__ = [
    "AgentOutcome",
    "MinisweBatchResult",
    "MinisweConvertError",
    "MinisweNotInstalledError",
    "MinisweRunResult",
    "build_records",
    "build_swebench_batch_argv",
    "build_swebench_single_argv",
    "outcome_to_record",
    "read_outcomes",
    "read_preds",
    "require_miniswe",
    "run_swebench_batch",
    "run_swebench_single",
    "write_generations",
]
