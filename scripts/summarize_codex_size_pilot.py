#!/usr/bin/env python3
"""Summarize paired TASK-002 runs without dropping or replacing selected tasks."""
from __future__ import annotations
import argparse
import json
import statistics
from pathlib import Path


def summarize_arm(run: Path, ids: list[str]) -> tuple[dict, dict]:
    results = json.loads((run / "results.json").read_text())
    manifest = json.loads((run / "manifest.json").read_text())
    if manifest["provenance"]["task_selection"]["instance_ids"] != ids:
        raise ValueError("Task selection differs between paired arms")
    rows = results["rows"]
    indexed = {row["instance_id"]: row for row in rows}
    if len(indexed) != len(rows) or set(indexed) != set(ids):
        raise ValueError("Arm must contain every selected task exactly once")
    valid = [r for r in rows if r.get("resolved") is not None]
    times = [r["episode_wall_s"] for r in rows if r.get("episode_wall_s") is not None]
    inference = [
        r["inference_wall_s"] for r in rows if r.get("inference_wall_s") is not None
    ]
    usages = [u.get("usage") for r in rows for u in r.get("usage_records", [])]

    def tokens(key):
        values = [u.get(key) for u in usages if u is not None]
        return (
            sum(v for v in values if v is not None)
            if values
            and all(v is not None for v in values)
            and all(u is not None for u in usages)
            else None
        )

    solved = sum(r["resolved"] for r in valid)
    summary = {
        "run_id": run.name,
        "model": manifest["config"]["model"],
        "selected": len(ids),
        "records": len(rows),
        "agent_attempted": sum("termination_reason" in r for r in rows),
        "evaluable": len(valid),
        "resolved": solved,
        "unresolved": sum(r.get("resolved") is False for r in rows),
        "infrastructure_errors": len(rows) - len(valid),
        "resolution_fraction_selected": solved / len(ids),
        "resolution_fraction_evaluable": solved / len(valid) if valid else None,
        "agent_wall_s_total": sum(times),
        "agent_wall_s_median": statistics.median(times) if times else None,
        "inference_request_wall_s_total": sum(inference),
        "model_requests": sum(r.get("model_requests", 0) for r in rows),
        "tool_completions": sum(r.get("tool_calls", 0) for r in rows),
        "input_tokens": tokens("input_tokens"),
        "output_tokens": tokens("output_tokens"),
        "usage_records_missing_tokens": sum(u is None for u in usages),
        "has_derived_request_timings": any(
            m.get("timing_source") == "gateway_log_timestamps"
            for r in rows
            for m in r.get("usage_records", [])
        ),
        "provider_api_cost_usd": 0,
        "sync_verified": (run / "sync_receipt.json").exists(),
    }
    return summary, indexed


def summarize(small: Path, large: Path, selection: Path) -> dict:
    ids = json.loads(selection.read_text())["instance_ids"]
    a, ar = summarize_arm(small, ids)
    b, br = summarize_arm(large, ids)
    left = json.loads((small / "manifest.json").read_text())["config"]
    right = json.loads((large / "manifest.json").read_text())["config"]
    for key in ("serving", "codex", "sandbox", "limits", "selection_manifest", "pilot"):
        if left[key] != right[key]:
            raise ValueError("Paired arms differ in shared protocol: " + key)
    if (
        a["model"]["id"] != "Qwen/Qwen2.5-Coder-7B-Instruct"
        or b["model"]["id"] != "Qwen/Qwen2.5-Coder-14B-Instruct"
    ):
        raise ValueError("Arm labels do not match model identities")
    paired = {
        "both": [],
        "7b_only": [],
        "14b_only": [],
        "neither": [],
        "infrastructure_error": [],
    }
    for iid in ids:
        x, y = ar[iid].get("resolved"), br[iid].get("resolved")
        key = (
            "infrastructure_error"
            if x is None or y is None
            else "both"
            if x and y
            else "7b_only"
            if x
            else "14b_only"
            if y
            else "neither"
        )
        paired[key].append(iid)
    return {
        "task_id": "TASK-002",
        "small": a,
        "large": b,
        "paired_counts": {k: len(v) for k, v in paired.items()},
        "paired_task_ids": paired,
        "interpretation": "One seeded attempt per task; balanced diagnostic training sample; descriptive comparison, not a population estimate or significance claim.",
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--small", type=Path, required=True)
    ap.add_argument("--large", type=Path, required=True)
    ap.add_argument(
        "--selection",
        type=Path,
        default=Path("configs/codex_qwen_size_pilot_tasks.json"),
    )
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    if args.output.exists():
        raise FileExistsError("Do not overwrite an earlier summary")
    summary = summarize(args.small, args.large, args.selection)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
