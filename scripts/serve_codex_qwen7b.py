#!/usr/bin/env python3
"""Start the task-owned inference container; stop it explicitly after TASK-001."""
import argparse
import json
import platform
import subprocess
from pathlib import Path
from urllib.parse import urlparse
import yaml


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--config", type=Path, default=Path("configs/codex_qwen7b.yaml"))
    args = ap.parse_args()
    if platform.system() != "Linux" or platform.machine() != "aarch64":
        ap.error("Spark ARM64 Linux only")
    cfg = yaml.safe_load(args.config.read_text())
    model = (
        "/hf/models--"
        + cfg["model"]["id"].replace("/", "--")
        + "/snapshots/"
        + cfg["model"]["revision"]
    )
    port = urlparse(cfg["serving"]["endpoint"]).port
    # Refuse an already occupied GPU; do not terminate or reuse another workload.
    active = subprocess.check_output(
        ["nvidia-smi", "--query-compute-apps=pid", "--format=csv,noheader"], text=True
    ).strip()
    if active:
        raise RuntimeError(
            "GPU compute processes are active; defer and review capacity"
        )
    command = [
        "docker",
        "run",
        "-d",
        "--name",
        cfg["serving"].get("container_name", "hecate-task001-model"),
        "--gpus",
        "all",
        "--shm-size=4g",
        "-p",
        f"127.0.0.1:{port}:8000",
        "-v",
        f"{args.root.resolve()}/hf:/hf:ro",
        "-e",
        "HF_HUB_OFFLINE=1",
        "-e",
        "TRANSFORMERS_OFFLINE=1",
        cfg["serving"]["image"],
        "--model",
        model,
        "--tokenizer",
        model,
        "--served-model-name",
        cfg["model"]["id"],
        "--dtype",
        cfg["model"]["precision"],
        "--max-model-len",
        str(cfg["model"]["context_tokens"]),
        "--max-num-seqs",
        "1",
        "--gpu-memory-utilization",
        str(cfg["serving"]["gpu_memory_utilization"]),
        "--enable-auto-tool-choice",
        "--tool-call-parser",
        cfg["serving"]["parser"],
        "--generation-config",
        "vllm",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
    ]
    (args.root / "serving-command.json").write_text(
        json.dumps(command, indent=2) + "\n"
    )
    subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
