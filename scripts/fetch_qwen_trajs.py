#!/usr/bin/env python3
"""Step 0: recover official Qwen3-Coder mini-SWE-agent traces.

Provenance order: S3 → HF JSONL. Docent is linked in metadata.yaml (manual).
Fail-closed label match against the v1/v2 277/500 CSV. Never invent a K=3 regen.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

S3_URI = (
    "s3://swe-bench-submissions/bash-only/"
    "20250802_mini-v1.0.0_Qwen3-Coder-480B-A35B-Instruct/trajs"
)
HF_DATASET = "parsaidp/swe-bench-verified-raw-traces-qwen3-coder"
HF_FILE = "data/full.jsonl"
HF_URL = (
    "https://huggingface.co/datasets/parsaidp/swe-bench-verified-raw-traces-qwen3-coder"
    "/resolve/main/data/full.jsonl"
)
DOCENT_URL = (
    "https://docent.transluce.org/dashboard/f39d3041-d9d7-4f1b-b75e-8a13addb9e6e"
)
SUBMISSION = "20250802_mini-v1.0.0_qwen3-coder-480b-a35b-instruct"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _try_s3(dest: Path) -> bool:
    aws = shutil.which("aws")
    if aws is None:
        print("s3: aws cli not found", flush=True)
        return False
    dest.mkdir(parents=True, exist_ok=True)
    listed = subprocess.run(
        [aws, "s3", "ls", S3_URI.rstrip("/") + "/"],
        capture_output=True,
        text=True,
        check=False,
    )
    if listed.returncode != 0 or not listed.stdout.strip():
        print(f"s3: empty or inaccessible ({listed.stderr.strip() or listed.stdout.strip()})", flush=True)
        return False
    sync = subprocess.run(
        [aws, "s3", "sync", S3_URI, str(dest)],
        check=False,
    )
    if sync.returncode != 0:
        print("s3: sync failed", flush=True)
        return False
    print(f"s3: synced to {dest}", flush=True)
    return True


def _try_hf(dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        from huggingface_hub import hf_hub_download

        path = hf_hub_download(
            repo_id=HF_DATASET,
            filename=HF_FILE,
            repo_type="dataset",
        )
        shutil.copy(path, dest)
        print(f"hf: copied {HF_FILE} to {dest}", flush=True)
        return True
    except Exception as exc:
        print(f"hf: huggingface_hub failed ({exc}); trying raw URL", flush=True)
    try:
        with urllib.request.urlopen(HF_URL, timeout=120) as response:
            dest.write_bytes(response.read())
        print(f"hf: downloaded {dest}", flush=True)
        return True
    except Exception as exc:
        print(f"hf: download failed ({exc})", flush=True)
        return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch Qwen3-Coder trajs and label-match")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for traces (default: data/raw/trajs)",
    )
    parser.add_argument(
        "--csv",
        default=None,
        help="Labels CSV (default: data/external joined file)",
    )
    parser.add_argument("--skip-s3", action="store_true")
    args = parser.parse_args(argv)

    root = _repo_root()
    out_dir = (
        Path(args.output_dir) if args.output_dir is not None else root / "data" / "raw" / "trajs"
    )
    csv_path = (
        Path(args.csv)
        if args.csv is not None
        else root / "data" / "external" / "qwen3coder_vs_claude4opus_miniswe_external.csv"
    )

    provenance = None
    source_path = out_dir
    if not args.skip_s3 and _try_s3(out_dir):
        provenance = "s3"
    else:
        jsonl = out_dir / "full.jsonl"
        if _try_hf(jsonl):
            provenance = "hf"
            source_path = jsonl
        else:
            print(
                "Step 0 failed. Docent (manual): "
                f"{DOCENT_URL}\n"
                "Do not generate truncated K=3 traces. A full re-run at "
                "temperature=0.0 (~$124) is a later decision.",
                flush=True,
            )
            return 2

    from hecate.data.external_miniswe import read_joined_csv, read_joined_text_csv
    from hecate.router.traj import match_traj_labels, parse_traj_dir
    from hecate.utils.manifest import git_commit_sha, write_run_manifest

    try:
        labels = read_joined_csv(csv_path)
    except Exception:
        from hecate.data.external_miniswe import JoinError

        try:
            text_rows = read_joined_text_csv(csv_path)
        except JoinError:
            raise
        from hecate.data.external_miniswe import JoinedLabel

        labels = [
            JoinedLabel(
                instance_id=row.instance_id,
                repo=row.repo,
                small_model_resolved=row.small_model_resolved,
                large_model_resolved=row.large_model_resolved,
            )
            for row in text_rows
        ]
    parsed = parse_traj_dir(source_path)
    report = match_traj_labels(parsed, labels, provenance=provenance)
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit_sha(),
        "submission": SUBMISSION,
        "s3_uri": S3_URI,
        "hf_dataset": HF_DATASET,
        "docent_url": DOCENT_URL,
        "provenance": provenance,
        "source_path": str(source_path),
        "n_labels": report.n_labels,
        "n_trajs": report.n_trajs,
        "n_matched": report.n_matched,
        "n_with_traj_resolved": report.n_with_traj_resolved,
        "missing_from_trajs": list(report.missing_from_trajs),
        "extra_trajs": list(report.extra_trajs),
        "resolve_mismatches": list(report.resolve_mismatches),
        "note": (
            "Fail-closed. A mismatch is not permission to generate truncated "
            "K=3 traces. Full re-run at temp=0.0 is a separate later decision."
        ),
    }
    stub = write_run_manifest(out_dir / "provenance.json", payload)
    print(json.dumps({k: payload[k] for k in (
        "provenance", "n_labels", "n_trajs", "n_matched", "n_with_traj_resolved"
    )}, indent=2))
    print(f"provenance={stub}", flush=True)
    try:
        report.raise_if_failed()
    except Exception as exc:
        print(f"LABEL MATCH FAILED: {exc}", flush=True)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
