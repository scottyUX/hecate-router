"""Optional mini-SWE-agent scaffold (parallel to Stage-1 single-shot)."""

from hecate.agent.miniswe import (
    MinisweNotInstalledError,
    MinisweRunResult,
    build_swebench_single_argv,
    require_miniswe,
    run_swebench_single,
)

__all__ = [
    "MinisweNotInstalledError",
    "MinisweRunResult",
    "build_swebench_single_argv",
    "require_miniswe",
    "run_swebench_single",
]
