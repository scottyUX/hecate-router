#!/usr/bin/env python3
"""Verify the frozen paper subset from a checksum-pinned Verified parquet."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def select_tasks(rows: list[dict], manifest: dict) -> list[dict]:
    ids = [row["instance_id"] for row in rows]
    if len(rows) != 500 or len(set(ids)) != 500:
        raise ValueError("Expected all500 distinct Verified tasks")
    selected = [row for row in rows if row["difficulty"] in {"1-4 hours", ">4 hours"}]
    if sorted(row["instance_id"] for row in selected) != manifest["instance_ids"]:
        raise ValueError("Selected task IDs differ from the frozen paper subset")
    if Counter(row["difficulty"] for row in selected) != manifest["difficulty_counts"]:
        raise ValueError("Difficulty counts differ from the paper")
    if Counter(row["repo"] for row in selected) != manifest["repo_counts"]:
        raise ValueError("Repository counts differ from the paper")
    if manifest["repetitions"] != 4 or len(selected) * 4 != manifest["planned_attempts"]:
        raise ValueError("Paper replication requires45 tasks with4 attempts each")
    return sorted(selected, key=lambda row: row["instance_id"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parquet", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=Path("configs/kimi_codex_swebench45_tasks.json"))
    parser.add_argument("--output", type=Path, required=True, help="Metadata only; no gold/test patches or hidden labels")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    digest = hashlib.sha256(args.parquet.read_bytes()).hexdigest()
    if digest != manifest["parquet_sha256"]:
        raise ValueError("Official dataset bytes differ from the pinned revision")
    import pyarrow.parquet as pq
    rows = select_tasks(pq.read_table(args.parquet).to_pylist(), manifest)
    # This task index may be shared with orchestration. Evaluator-only metadata
    # remains in the original dataset and never enters an agent prompt/workspace.
    public = [{key: row[key] for key in ("instance_id", "repo", "base_commit", "difficulty")} for row in rows]
    output = {"dataset_revision": manifest["revision"], "parquet_sha256": digest,
              "selection_manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
              "task_count": len(public), "planned_attempts": len(public) * 4, "tasks": public}
    with args.output.open("x") as handle:
        handle.write(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"verified_tasks": len(public), "planned_attempts": len(public) * 4}))


if __name__ == "__main__":
    main()
