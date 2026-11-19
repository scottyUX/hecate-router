#!/usr/bin/env python3
"""Offline TASK-004 replay; no inference, sandbox launch or command execution.

An input manifest explicitly names training/pilot logs and adapter formats. Full
run manifests/evaluator rows are not used as observation data. Canonical mode
accepts only the versioned Event contract. Historical replay is diagnostic unless
controller masks and frozen training normalization are explicitly supplied.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.metadata
import json
import shutil
import sys
from pathlib import Path
import yaml
from hecate.execution.codex_artifacts import create_run, finish_run
from hecate.telemetry import adapters
from hecate.telemetry.collector import collect
from hecate.telemetry.events import Event, digest
from hecate.telemetry.state import StateBuilder, save_normalizer


def replay(manifest, config):
    StateBuilder(config)  # validate the pinned schema before reading logs
    events = []
    coverage = []
    episodes = set()
    sources = {}
    for item in manifest["episodes"]:
        episode = item["episode_id"]
        if episode in episodes:
            raise ValueError("Duplicate episode identity")
        episodes.add(episode)
        identity = {
            k: item[k]
            for k in [
                "task_id",
                "run_id",
                "session_id",
                "harness",
                "harness_version",
                "split",
            ]
        }
        if identity["split"] not in {"train", "pilot"}:
            raise ValueError("Replay scope is training/pilot only")
        identity["model_revision"] = item.get("model_revision")
        source = Path(item["path"]).resolve()
        paths = list(source.glob("*")) if source.is_dir() else [source]
        # Explicit allowlist: do not read evaluation, patches or full task rows.
        names = (
            {"gateway.jsonl", "model.jsonl", "result.json"}
            if source.is_dir()
            else {source.name}
        )
        for p in paths:
            if p.is_file() and p.name in names:
                sources[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
        fmt = item["format"]
        if fmt == "canonical-v1":
            rows = adapters.read_jsonl(source)
            stream = [Event.from_dict(r) for r in rows]
            if any(e.episode_id != episode or e.identity != identity for e in stream):
                raise ValueError("Canonical identity differs from input manifest")
            report = {"format": fmt}
        else:
            functions = {
                "hecate-codex-v1": adapters.hecate_codex,
                "hecate-mini-v1": adapters.mini,
                "e7-session-v1": adapters.e7_session,
                "e7-proxy-v1": adapters.e7_proxy,
            }
            if fmt not in functions:
                raise ValueError("Unsupported adapter format/version")
            stream, report = functions[fmt](
                source,
                episode_id=episode,
                identity=identity,
                config=item.get("execution_config", {}),
                role=item.get("model_role", "m1"),
            )
        events.extend(stream)
        coverage.append({"episode_id": episode, "events": len(stream), **report})
    observations = collect(events, config)
    return events, observations, coverage, sources


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inputs", type=Path, required=True)
    ap.add_argument(
        "--config", type=Path, default=Path("configs/routing_observation.yaml")
    )
    ap.add_argument("--output-root", type=Path, required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument(
        "--fit-split",
        type=Path,
        help="Explicit training/reserved-ID manifest; fit a new normalizer",
    )
    ap.add_argument("--normalizer", type=Path)
    ap.add_argument("--router-ready", action="store_true")
    args = ap.parse_args()
    if args.fit_split and args.normalizer:
        ap.error("Choose fitting or a frozen normalizer")
    config = yaml.safe_load(args.config.read_text())
    manifest = json.loads(args.inputs.read_text())
    run = create_run(
        args.output_root,
        args.run_id,
        config,
        {
            "argv": sys.argv,
            "input_manifest_hash": digest(manifest),
            "dependencies": {"PyYAML": importlib.metadata.version("PyYAML")},
            "execution": "offline CPU-only replay",
        },
    )
    for path, name in [
        (args.inputs, "inputs.json"),
        (args.config, "config.yaml"),
        (args.fit_split, "split.json"),
        (args.normalizer, "input-normalizer.json"),
    ]:
        if path:
            shutil.copy2(path, run / name)
    snapshot = run / "source"
    snapshot.mkdir()
    for path in [Path(__file__), *Path("src/hecate/telemetry").glob("*.py")]:
        shutil.copy2(path, snapshot / path.name)
    try:
        events, rows, coverage, sources = replay(manifest, config)
        normalizer = (
            json.loads(args.normalizer.read_text()) if args.normalizer else None
        )
        if args.fit_split:
            normalizer = StateBuilder(config).fit(
                rows, json.loads(args.fit_split.read_text())
            )
            save_normalizer(run / "normalizer.json", normalizer)
        builder = StateBuilder(config, normalizer)
        states = [builder.build(row, router_ready=args.router_ready) for row in rows]
        for name, records in [
            ("events.jsonl", [e.to_dict() for e in events]),
            ("observations.jsonl", states),
        ]:
            (run / name).write_text(
                "".join(
                    json.dumps(r, sort_keys=True, allow_nan=False) + "\n"
                    for r in records
                )
            )
        finish_run(
            run,
            {
                "mode": "offline_replay",
                "observations": len(states),
                "events": len(events),
                "coverage": coverage,
                "source_hashes": sources,
                "schema_hash": builder.schema_hash,
                "normalizer_hash": normalizer["hash"] if normalizer else None,
            },
        )
        print(
            json.dumps(
                {
                    "run_dir": str(run),
                    "observations": len(states),
                    "coverage": coverage,
                },
                indent=2,
            )
        )
    except BaseException as exc:
        finish_run(
            run,
            {"status": "failed", "error": str(exc), "error_type": type(exc).__name__},
        )
        raise


if __name__ == "__main__":
    main()
