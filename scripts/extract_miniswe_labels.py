#!/usr/bin/env python3
"""Extract matched-scaffold mini-SWE-agent labels (Qwen3-Coder vs Claude 4 Opus).

Usage:
    python scripts/extract_miniswe_labels.py
    python scripts/extract_miniswe_labels.py --output-dir data/external
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected object at {url}")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Join Qwen3-Coder and Claude 4 Opus mini-SWE-agent v1.0.0 "
            "per-instance labels (SWE-bench Verified, 500)."
        )
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for CSV/JSON/metadata (default: data/external)",
    )
    parser.add_argument(
        "--small-url",
        default=None,
        help="Override small-model per_instance_details.json URL",
    )
    parser.add_argument(
        "--large-url",
        default=None,
        help="Override large-model per_instance_details.json URL",
    )
    args = parser.parse_args(argv)

    from hecate.data.external_miniswe import (
        CSV_NAME,
        EXPECTED_N,
        JSON_NAME,
        LARGE_METADATA_URL,
        LARGE_PUBLISHED_PCT,
        LARGE_RESOLVED_COUNT,
        LARGE_SOURCE_URL,
        LARGE_SUBMISSION,
        SMALL_METADATA_URL,
        SMALL_PUBLISHED_PCT,
        SMALL_RESOLVED_COUNT,
        SMALL_SOURCE_URL,
        SMALL_SUBMISSION,
        git_peek_sensitivity,
        join_labels,
        write_csv,
        write_json,
    )
    from hecate.utils.manifest import git_commit_sha, write_run_manifest

    output_dir = (
        Path(args.output_dir)
        if args.output_dir is not None
        else _repo_root() / "data" / "external"
    )
    small_url = args.small_url or SMALL_SOURCE_URL
    large_url = args.large_url or LARGE_SOURCE_URL
    pulled_at = datetime.now(timezone.utc).isoformat()

    small_details = _fetch_json(small_url)
    large_details = _fetch_json(large_url)
    rows = join_labels(small_details, large_details)
    peek = git_peek_sensitivity(rows)

    csv_path = write_csv(rows, output_dir / CSV_NAME)
    json_path = write_json(rows, output_dir / JSON_NAME)
    small_resolved = sum(1 for row in rows if row.small_model_resolved)
    large_resolved = sum(1 for row in rows if row.large_model_resolved)

    metadata = {
        "dataset": "qwen3coder_vs_claude4opus_miniswe_external",
        "label": "externally sourced matched-scaffold substitute; not an in-house run",
        "split": "verified",
        "leaderboard_track": "bash-only",
        "n_instances": EXPECTED_N,
        "not_lite": True,
        "do_not_merge_with": "in-house Qwen 2.5 7B/72B SWE-bench Lite single-shot labels",
        "date_pulled": pulled_at,
        "git_commit": git_commit_sha(),
        "excluded_instances": [],
        "scaffold": {
            "name": "mini-SWE-agent",
            "small_model_version": "1.0.0",
            "large_model_version": "1.0.0",
            "same_day": "2025-08-02",
            "attempts": 1,
        },
        "small_model": {
            "display": "Qwen3-Coder 480B/A35B Instruct",
            "submission": SMALL_SUBMISSION,
            "source_url": small_url,
            "metadata_url": SMALL_METADATA_URL,
            "published_resolve_pct": SMALL_PUBLISHED_PCT,
            "resolved_count": small_resolved,
            "expected_resolved_count": SMALL_RESOLVED_COUNT,
        },
        "large_model": {
            "display": "Claude 4 Opus (20250514)",
            "submission": LARGE_SUBMISSION,
            "source_url": large_url,
            "metadata_url": LARGE_METADATA_URL,
            "published_resolve_pct": LARGE_PUBLISHED_PCT,
            "resolved_count": large_resolved,
            "expected_resolved_count": LARGE_RESOLVED_COUNT,
        },
        "decoding": {
            "harness_swebench_yaml_temperature": 0.0,
            "qwen3_coder_vendor_recommended": {
                "temperature": 0.7,
                "top_p": 0.8,
            },
            "published_run_sampling": "unknown — not in submission metadata.yaml",
            "caveat": (
                "Harness config at mini-SWE-agent v1.0.0 sets temperature=0.0. "
                "Qwen3-Coder vendor recommendations are temperature=0.7, top_p=0.8; "
                "community reports greedy underperforms for this model. Actual "
                "sampling used in the published run is not recorded in metadata.yaml. "
                "Disclose as: harness config says greedy, but model-specific "
                "behavior under greedy is contested and unverified for this run."
            ),
        },
        "opus_git_peek": peek,
        "router_training": {
            "drop_in_for_run_train": False,
            "blocked_on": (
                "Join these labels with SWE-bench Verified issue-text prompts "
                "before scripts/run_train.py. Do not use mini-SWE-agent "
                "trajectories as router input."
            ),
        },
        "artifacts": {
            "csv": str(csv_path),
            "json": str(json_path),
        },
    }
    metadata_path = write_run_manifest(output_dir / "metadata.json", metadata)

    print(
        f"rows={len(rows)} "
        f"small={small_resolved}/{len(rows)} ({SMALL_PUBLISHED_PCT}%) "
        f"large={large_resolved}/{len(rows)} ({LARGE_PUBLISHED_PCT}%) "
        f"git_peek_sensitivity={peek['sensitivity_recode_false_pct']}%"
    )
    print(f"csv={csv_path}")
    print(f"json={json_path}")
    print(f"metadata={metadata_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
