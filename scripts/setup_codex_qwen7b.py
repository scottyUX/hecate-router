#!/usr/bin/env python3
"""Download TASK-001 pinned assets into a task-owned directory, on Spark only.

Requires PyYAML and huggingface_hub in the bootstrap environment. This does not
start inference or modify shared caches. Run the read-only capacity check first.
"""
import argparse
import base64
import hashlib
import io
import json
import platform
import tarfile
import urllib.request
from pathlib import Path
import yaml


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--config", type=Path, default=Path("configs/codex_qwen7b.yaml"))
    args = ap.parse_args()
    if platform.system() != "Linux" or platform.machine() != "aarch64":
        ap.error("Spark ARM64 Linux only")
    cfg = yaml.safe_load(args.config.read_text())
    from huggingface_hub import snapshot_download

    root = args.root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    version = cfg["codex"]["version"] + "-linux-arm64"
    meta = json.load(
        urllib.request.urlopen(
            "https://registry.npmjs.org/@openai/codex/" + version, timeout=30
        )
    )
    blob = urllib.request.urlopen(meta["dist"]["tarball"], timeout=120).read()
    alg, expected = meta["dist"]["integrity"].split("-", 1)
    if (
        alg != "sha512"
        or base64.b64encode(hashlib.sha512(blob).digest()).decode() != expected
    ):
        raise ValueError("Codex package integrity mismatch")
    dest = root / "toolchain"
    if dest.exists() and (dest / "package").exists():
        print(
            "Existing Codex package retained; runtime version/hash must match manifest"
        )
    else:
        with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as archive:
            for member in archive.getmembers():
                p = Path(member.name)
                if (
                    p.is_absolute()
                    or ".." in p.parts
                    or member.issym()
                    or member.islnk()
                ):
                    raise ValueError("Unsafe package member")
            archive.extractall(dest)
        (dest / "npm-provenance.json").write_text(
            json.dumps(
                {
                    "version": meta["version"],
                    "integrity": meta["dist"]["integrity"],
                    "tarball": meta["dist"]["tarball"],
                },
                indent=2,
            )
        )
    path = snapshot_download(
        cfg["model"]["id"],
        revision=cfg["model"]["revision"],
        allow_patterns=["*.json", "*.safetensors", "*.txt", "*.jinja", "*.tiktoken"],
        cache_dir=str(root / "hf"),
    )
    (root / "model-path.txt").write_text(path + "\n")
    print(path)


if __name__ == "__main__":
    main()
