#!/usr/bin/env python3
"""Join SWE-bench Verified issue text onto mini-SWE-agent labels.

Usage:
    python scripts/join_miniswe_issue_text.py
    python scripts/join_miniswe_issue_text.py --output-dir data/external
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _artifact_ref(path: Path, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return str(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Join princeton-nlp/SWE-bench_Verified problem_statement onto "
            "the Qwen3-Coder vs Claude 4 Opus mini-SWE-agent labels."
        )
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for CSV/JSON/metadata (default: data/external)",
    )
    parser.add_argument(
        "--labels-csv",
        default=None,
        help="Override labels CSV path (default: <output-dir>/qwen3coder_vs_claude4opus_miniswe_external.csv)",
    )
    args = parser.parse_args(argv)

    from hecate.data.external_miniswe import (
        CSV_NAME,
        EXPECTED_N,
        HEADROOM_PP,
        ORACLE_PCT,
        JoinError,
        complementarity,
        join_and_write_text,
        read_joined_csv,
    )
    from hecate.data.tasks import (
        SWEBENCH_VERIFIED_DATASET,
        SWEBENCH_VERIFIED_SPLIT,
        load_swebench_verified,
    )
    from hecate.utils.manifest import git_commit_sha, write_run_manifest

    repo_root = _repo_root()
    output_dir = (
        Path(args.output_dir)
        if args.output_dir is not None
        else repo_root / "data" / "external"
    )
    labels_path = (
        Path(args.labels_csv) if args.labels_csv is not None else output_dir / CSV_NAME
    )
    labels = read_joined_csv(labels_path)
    if len(labels) != EXPECTED_N:
        print(
            f"error: labels CSV has {len(labels)} rows, expected {EXPECTED_N}",
            file=sys.stderr,
        )
        return 1

    tasks = load_swebench_verified()
    by_id = {
        task.instance_id: {
            "problem_statement": task.problem_statement,
            "base_commit": task.base_commit,
            "repo": task.repo,
        }
        for task in tasks
    }
    try:
        rows, csv_path, json_path = join_and_write_text(labels, by_id, output_dir)
    except JoinError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    stats = complementarity(labels)
    metadata_path = output_dir / "metadata.json"
    if metadata_path.is_file():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if not isinstance(metadata, dict):
            metadata = {}
    else:
        metadata = {}

    artifacts = dict(metadata.get("artifacts") or {})
    artifacts["with_text_csv"] = _artifact_ref(csv_path, repo_root)
    artifacts["with_text_json"] = _artifact_ref(json_path, repo_root)
    metadata["artifacts"] = artifacts
    metadata["issue_text_join"] = {
        "dataset": SWEBENCH_VERIFIED_DATASET,
        "split": SWEBENCH_VERIFIED_SPLIT,
        "n_matched": len(rows),
        "fields": ["problem_statement", "base_commit"],
        "excludes": ["patch", "test_patch"],
        "date_joined": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit_sha(),
    }
    metadata["complementarity"] = stats
    metadata["router_training"] = {
        "drop_in_for_run_train": False,
        "issue_text_joined": True,
        "blocked_on": (
            "Issue text joined. scripts/run_train.py / spec 015 still expect "
            "Lite generations.jsonl; do not point them at this Verified file yet. "
            "Do not use mini-SWE-agent trajectories as router input."
        ),
    }
    write_run_manifest(metadata_path, metadata)

    print(
        f"rows={len(rows)} "
        f"oracle={stats['oracle_pct']}% "
        f"headroom_pp={stats['headroom_pp']} "
        f"(always_small={stats['always_small_pct']}% "
        f"always_large={stats['always_large_pct']}%)"
    )
    print(f"csv={csv_path}")
    print(f"json={json_path}")
    print(f"metadata={metadata_path}")
    if stats["headroom_pp"] != HEADROOM_PP or stats["oracle_pct"] != ORACLE_PCT:
        print(
            "warning: complementarity does not match published "
            f"oracle={ORACLE_PCT}% headroom={HEADROOM_PP}pp",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
