#!/usr/bin/env python3
"""Run the full generation sweep: 4 models × 300 SWE-bench Lite tasks.

Usage (once implemented):
    python scripts/run_sweep.py --config configs/option_a.yaml
"""

from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Hecate Stage 1 full sweep runner")
    parser.add_argument("--config", default="configs/option_a.yaml", help="Path to config YAML")
    parser.add_argument("--dry-run", action="store_true", help="Validate config without API calls")
    parser.add_argument("--resume", action="store_true", help="Resume from cache (default)")
    args = parser.parse_args()
    raise SystemExit(
        "Full sweep runner not yet implemented. Complete the pilot gate (M1) first."
    )


if __name__ == "__main__":
    main()
