#!/usr/bin/env python3
"""Measure K=3 prefix truncation at 8192 tokens. Run after fetch_qwen_trajs.py.

Default tokenizer is whitespace (offline). Pass --hf-tokenizer to use
Qwen2.5-Coder-7B-Instruct's tokenizer without loading the 7B weights.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="K=3 truncation audit at 8192 tokens")
    parser.add_argument("--traj-dir", default="data/raw/trajs")
    parser.add_argument(
        "--csv",
        default="data/external/qwen3coder_vs_claude4opus_miniswe_external.csv",
    )
    parser.add_argument("--output", default=None)
    parser.add_argument("--max-tokens", type=int, default=8192)
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument(
        "--hf-tokenizer",
        action="store_true",
        help="Load Qwen2.5-Coder tokenizer (not the 7B model)",
    )
    parser.add_argument("--provenance", default="unknown")
    args = parser.parse_args(argv)

    from hecate.data.external_miniswe import JoinedLabel, JoinError, read_joined_csv, read_joined_text_csv
    from hecate.router.dataset import WhitespaceTokenizer
    from hecate.router.traj import build_traj_examples, parse_traj_dir, truncation_report

    csv_path = Path(args.csv)
    try:
        labels = read_joined_csv(csv_path)
    except JoinError:
        text_rows = read_joined_text_csv(csv_path)
        labels = [
            JoinedLabel(
                instance_id=row.instance_id,
                repo=row.repo,
                small_model_resolved=row.small_model_resolved,
                large_model_resolved=row.large_model_resolved,
            )
            for row in text_rows
        ]
    parsed = parse_traj_dir(Path(args.traj_dir))
    tokenizer = WhitespaceTokenizer()
    if args.hf_tokenizer:
        from transformers import AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(
            "Qwen/Qwen2.5-Coder-7B-Instruct", trust_remote_code=True
        )
    examples, report, _counts = build_traj_examples(
        parsed,
        labels,
        tokenizer=None,
        max_tokens=args.max_tokens,
        provenance=args.provenance,
    )
    measure_tok: WhitespaceTokenizer | _HfTok
    if args.hf_tokenizer:
        measure_tok = _HfTok(tokenizer)
    else:
        measure_tok = WhitespaceTokenizer()
    audit = truncation_report(
        examples,
        k=args.k,
        max_tokens=args.max_tokens,
        tokenizer=measure_tok,
    )
    audit["provenance"] = report.provenance
    audit["n_matched"] = report.n_matched
    audit["tokenizer"] = (
        "Qwen/Qwen2.5-Coder-7B-Instruct" if args.hf_tokenizer else "WhitespaceTokenizer"
    )
    out = Path(args.output) if args.output else Path("data/outputs/runs/truncation.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2))
    print(f"wrote {out}")
    return 0


class _HfTok:
    def __init__(self, tokenizer) -> None:
        self._tok = tokenizer

    def encode(self, text: str) -> list[int]:
        return list(self._tok.encode(text, add_special_tokens=True))

    def decode(self, tokens: list[int]) -> str:
        return str(self._tok.decode(tokens, skip_special_tokens=False))


if __name__ == "__main__":
    sys.exit(main())
