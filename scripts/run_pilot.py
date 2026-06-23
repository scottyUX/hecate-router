#!/usr/bin/env python3
"""Run a pilot generation sweep: 20 tasks × 1 model.

Usage (once implemented):
    python scripts/run_pilot.py --config configs/option_a.yaml --tasks 20 --model qwen2.5-7b
"""

from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Hecate Stage 1 pilot runner")
    parser.add_argument("--config", default="configs/option_a.yaml", help="Path to config YAML")
    parser.add_argument("--tasks", type=int, default=20, help="Number of SWE-bench Lite tasks")
    parser.add_argument("--model", required=False, help="Model slug (single model for pilot)")
    parser.add_argument("--dry-run", action="store_true", help="Validate config without API calls")
    args = parser.parse_args()
    raise SystemExit(
        "Pilot runner not yet implemented. See GitHub issues S5–S11."
    )


if __name__ == "__main__":
    main()
