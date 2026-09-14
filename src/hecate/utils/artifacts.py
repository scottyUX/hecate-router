"""Copy a finished run off the training disk. LoRA weights are not complete until this succeeds."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from hecate.utils.env import load_env
from hecate.utils.manifest import write_run_manifest

ARTIFACTS_URI_ENV = "HECATE_ARTIFACTS_URI"
REQUIRE_ARTIFACTS_ENV = "HECATE_REQUIRE_ARTIFACTS"
REQUIRED_RUN_FILES = ("results.json", "manifest.json")
_TRUTHY = {"1", "true", "yes", "on"}


class ArtifactError(RuntimeError):
    """Fail-closed artifact sync or verify error."""


def artifacts_uri_from_env() -> str | None:
    """Return ``HECATE_ARTIFACTS_URI`` after loading ``.env``, or None."""
    load_env()
    raw = (os.environ.get(ARTIFACTS_URI_ENV) or "").strip()
    return raw or None


def require_artifacts_env() -> bool:
    load_env()
    raw = (os.environ.get(REQUIRE_ARTIFACTS_ENV) or "").strip().lower()
    return raw in _TRUTHY


def resolve_artifacts_uri(
    *,
    backend: str,
    allow_unsynced: bool = False,
) -> str | None:
    """URI for the durable copy, or None when a local-only run is allowed.

    ``--backend lora`` must set ``HECATE_ARTIFACTS_URI`` unless
    ``allow_unsynced`` is true. That is the direct fix for adapters that
    died on a stopped VM. Scripted/frozen runs sync only when the URI is set.
    """
    uri = artifacts_uri_from_env()
    if allow_unsynced:
        return uri
    kind = (backend or "").strip().lower()
    if kind == "lora" and not uri:
        raise ArtifactError(
            f"{ARTIFACTS_URI_ENV} must be set for --backend lora so adapters "
            "are copied off this disk. Pass --allow-unsynced only for a local "
            "debug run that may lose weights."
        )
    if require_artifacts_env() and not uri:
        raise ArtifactError(
            f"{REQUIRE_ARTIFACTS_ENV} is set but {ARTIFACTS_URI_ENV} is empty"
        )
    return uri


def run_dest_uri(base_uri: str, run_id: str) -> str:
    rid = (run_id or "").strip()
    if not rid:
        raise ArtifactError("run_id must be a non-empty string")
    if "/" in rid or rid in {".", ".."}:
        raise ArtifactError(f"refusing run_id that is not a single path segment: {rid!r}")
    scheme, root = _split_uri(base_uri)
    if scheme == "gs":
        return f"{root}/runs/{rid}"
    return str(Path(root) / "runs" / rid)


def _split_uri(uri: str) -> tuple[str, str]:
    raw = (uri or "").strip()
    if not raw:
        raise ArtifactError("artifacts URI is empty")
    if raw.startswith("gs://"):
        parsed = urlparse(raw)
        if not parsed.netloc:
            raise ArtifactError(f"gs:// URI missing bucket: {uri!r}")
        prefix = parsed.path.strip("/")
        root = f"gs://{parsed.netloc}"
        if prefix:
            root = f"{root}/{prefix}"
        return "gs", root.rstrip("/")
    if raw.startswith("file://"):
        path = raw[len("file://") :]
        if not path:
            raise ArtifactError(f"file:// URI missing path: {uri!r}")
        return "file", str(Path(path).expanduser().resolve())
    if raw.startswith("/"):
        return "file", str(Path(raw).expanduser().resolve())
    raise ArtifactError(
        f"unsupported artifacts URI {uri!r}; expected gs://..., file://..., or an absolute path"
    )


def dest_has_results(dest_uri: str) -> bool:
    return _dest_has(dest_uri.rstrip("/"), "results.json")


def sync_run_dir(run_dir: Path | str, dest_uri: str, *, overwrite: bool = False) -> str:
    """Copy ``run_dir`` to ``dest_uri``. Refuses to overwrite an existing run."""
    src = Path(run_dir)
    if not src.is_dir():
        raise ArtifactError(f"run dir missing: {src}")
    dest = dest_uri.rstrip("/")
    if dest_has_results(dest) and not overwrite:
        raise ArtifactError(
            f"refusing to overwrite existing run at {dest}. "
            "Use a new run_id or pass overwrite=True."
        )
    if dest.startswith("gs://"):
        _gcloud_rsync(src, dest)
    else:
        _copy_local(src, Path(dest))
    return dest


def verify_run_synced(run_dir: Path | str, dest_uri: str) -> None:
    """Treat a missing remote copy the same as a missing local adapter."""
    src = Path(run_dir)
    dest = dest_uri.rstrip("/")
    missing = [
        name for name in REQUIRED_RUN_FILES if not _dest_has(dest, name)
    ]
    if (src / "checkpoints").is_dir() and any((src / "checkpoints").iterdir()):
        if not _dest_has_prefix(dest, "checkpoints/"):
            missing.append("checkpoints/")
    if (src / "holdout_scores.jsonl").is_file() and not _dest_has(
        dest, "holdout_scores.jsonl"
    ):
        missing.append("holdout_scores.jsonl")
    if missing:
        raise ArtifactError(
            f"run is not complete: missing from {dest}: {missing}. "
            "Trained locally but never confirmed off this disk."
        )


def finalize_run_artifacts(
    run_dir: Path | str,
    *,
    base_uri: str,
    run_id: str,
    overwrite: bool = False,
) -> str:
    """Stamp the manifest, copy the run, and fail if the copy is incomplete."""
    dest = run_dest_uri(base_uri, run_id)
    src = Path(run_dir)
    manifest = src / "manifest.json"
    if manifest.is_file():
        payload: dict[str, Any] = json.loads(manifest.read_text(encoding="utf-8"))
        payload["artifacts_uri"] = dest
        write_run_manifest(manifest, payload)
    sync_run_dir(src, dest, overwrite=overwrite)
    verify_run_synced(src, dest)
    return dest


def _dest_has(dest_uri: str, relative: str) -> bool:
    if dest_uri.startswith("gs://"):
        return _gcloud_exists(f"{dest_uri}/{relative}")
    return (Path(dest_uri) / relative).exists()


def _dest_has_prefix(dest_uri: str, prefix: str) -> bool:
    if dest_uri.startswith("gs://"):
        return _gcloud_exists(f"{dest_uri}/{prefix.rstrip('/')}")
    target = Path(dest_uri) / prefix
    return target.exists() and (
        target.is_file() or (target.is_dir() and any(target.iterdir()))
    )


def _copy_local(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)


def _gcloud_exists(uri: str) -> bool:
    result = _gcloud(["storage", "ls", uri])
    return result.returncode == 0


def _gcloud_rsync(src: Path, dest: str) -> None:
    result = _gcloud(
        ["storage", "rsync", "--recursive", str(src), dest]
    )
    if result.returncode != 0:
        raise ArtifactError(
            f"gcloud storage rsync failed for {dest}: {result.stderr.strip() or result.stdout.strip()}"
        )


def _gcloud(args: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["gcloud", *args],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise ArtifactError(
            "gcloud not found; cannot sync to gs://. Install the Cloud SDK "
            "or set HECATE_ARTIFACTS_URI to a local file:// path."
        ) from exc
