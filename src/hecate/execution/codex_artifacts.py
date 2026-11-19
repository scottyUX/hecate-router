"""Immutable run identities and fail-closed, checksum-verified local mirror."""
from __future__ import annotations
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def git_commit_sha():
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True
    )
    return result.stdout.strip() if result.returncode == 0 else None


def checksums(root: Path, *, legacy_links: bool = False) -> dict[str, str]:
    result = {}
    for path in sorted(root.rglob("*")):
        if ".git" in path.parts or path.name in {"checksums.json", "sync_receipt.json"}:
            continue
        if path.is_symlink():
            if legacy_links:
                if not path.resolve().is_relative_to(root.resolve()):
                    raise ValueError("Legacy artifact link escapes run directory")
                value = hashlib.sha256(path.read_bytes()).hexdigest()
            else:
                value = "link:" + hashlib.sha256(os.readlink(path).encode()).hexdigest()
        elif path.is_file():
            value = hashlib.sha256(path.read_bytes()).hexdigest()
        else:
            continue
        result[str(path.relative_to(root))] = value
    return result


def create_run(root: Path, run_id: str, config: dict, provenance: dict) -> Path:
    if not run_id or Path(run_id).name != run_id or run_id in {".", ".."}:
        raise ValueError("Invalid run ID")
    target = root / run_id
    target.mkdir(parents=True, exist_ok=False)
    manifest = {
        "run_id": run_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": provenance.get("git_commit") or git_commit_sha(),
        "python": sys.version,
        "config": config,
        "provenance": provenance,
        "status": "running",
    }
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return target


def finish_run(root: Path, results: dict) -> None:
    (root / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    path = root / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest.update(
        checksum_scheme="sha256-files-and-link-targets-v2",
        status="awaiting_off_spark_copy",
        finished_at=datetime.now(timezone.utc).isoformat(),
    )
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    (root / "checksums.json").write_text(json.dumps(checksums(root), indent=2) + "\n")


def verify_mirror(source: Path, mirror: Path, *, off_spark: bool) -> dict:
    if not off_spark:
        raise ValueError("Must explicitly verify from a machine off Spark")
    if source.resolve() == mirror.resolve():
        raise ValueError("Mirror cannot be the source directory")
    expected = json.loads((source / "checksums.json").read_text())
    manifest = json.loads((source / "manifest.json").read_text())
    legacy = manifest.get("checksum_scheme") != "sha256-files-and-link-targets-v2"
    if checksums(source, legacy_links=legacy) != expected:
        raise ValueError("Source artifacts changed after checksum creation")
    if checksums(mirror, legacy_links=legacy) != expected:
        raise ValueError("Mirror missing or checksum mismatch")
    receipt = {
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "sha256_files": len(expected),
        "status": "verified_off_spark",
    }
    (mirror / "sync_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt
