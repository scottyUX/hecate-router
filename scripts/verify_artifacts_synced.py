#!/usr/bin/env python3
"""Fail if a local run was never confirmed at HECATE_ARTIFACTS_URI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Confirm a run directory exists at HECATE_ARTIFACTS_URI"
    )
    parser.add_argument("--run-dir", required=True)
    parser.add_argument(
        "--uri",
        default=None,
        help="Override destination (default: manifest artifacts_uri or env + run_id)",
    )
    args = parser.parse_args(argv)

    from hecate.utils.artifacts import (
        ARTIFACTS_URI_ENV,
        ArtifactError,
        artifacts_uri_from_env,
        run_dest_uri,
        verify_run_synced,
    )

    run_dir = Path(args.run_dir)
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.is_file():
        print(f"missing {manifest_path}", file=sys.stderr)
        return 1
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    dest = args.uri or manifest.get("artifacts_uri")
    if not dest:
        base = artifacts_uri_from_env()
        run_id = manifest.get("run_id")
        if not base or not run_id:
            print(
                f"no destination: set --uri, manifest artifacts_uri, or {ARTIFACTS_URI_ENV}",
                file=sys.stderr,
            )
            return 1
        dest = run_dest_uri(str(base), str(run_id))
    try:
        verify_run_synced(run_dir, str(dest))
    except ArtifactError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"ok {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
