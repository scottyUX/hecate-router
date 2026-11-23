#!/usr/bin/env python3
"""TASK-012 off-Spark checkpoint: copy finished runs to this machine, verify, receipt.

Run on the Mac (never on Spark). `workspace/` (the agent's final checkout, ~80MB
per attempt, reproducible from base commit + agent/patch.diff) stays on Spark;
every other checksummed file must match before a receipt is written back.
"""
from __future__ import annotations
import argparse
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from hecate.execution.codex_artifacts import checksums

EXCLUDED = 'workspace/'


def verify(mirror: Path) -> dict:
    expected = json.loads((mirror / 'checksums.json').read_text())
    expected = {k: v for k, v in expected.items() if not k.startswith(EXCLUDED)}
    if checksums(mirror) != expected:
        raise ValueError(f'Mirror checksum mismatch: {mirror.name}')
    return {'verified_at': datetime.now(timezone.utc).isoformat(), 'sha256_files': len(expected),
            'excluded_prefixes': [EXCLUDED], 'status': 'verified_off_spark'}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--remote-root', default='~/work/hecate-task012')
    ap.add_argument('--mirror', type=Path, default=Path.home() / 'hecate-spark-mirror/task012/runs')
    args = ap.parse_args()
    if platform.system() == 'Linux' and platform.machine() == 'aarch64':
        raise SystemExit('Run off Spark')
    listing = subprocess.check_output(['ssh', 'spark', f'cd {args.remote_root}/runs && for d in task012-*; do '
                                       '[ -f "$d/checksums.json" ] && [ ! -f "$d/sync_receipt.json" ] && echo "$d"; done; true'],
                                      text=True).split()
    args.mirror.mkdir(parents=True, exist_ok=True)
    for name in listing:
        subprocess.run(['rsync', '-a', '--exclude', EXCLUDED, '--exclude', 'export-check/',
                        f'spark:{args.remote_root}/runs/{name}/', str(args.mirror / name) + '/'], check=True)
        receipt = verify(args.mirror / name)
        (args.mirror / name / 'sync_receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
        subprocess.run(['scp', '-q', str(args.mirror / name / 'sync_receipt.json'),
                        f'spark:{args.remote_root}/runs/{name}/sync_receipt.json'], check=True)
        print(json.dumps({'run': name, **receipt}), flush=True)
    print(json.dumps({'receipted': len(listing)}))


if __name__ == '__main__':
    main()
