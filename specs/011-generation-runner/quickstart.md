# Quickstart: Generation Runner

## Prerequisites

```bash
pip install -e ".[dev]"
# Live path only:
# cp .env.example .env  # set OPENROUTER_API_KEY
```

## Offline dry-run (1 task)

```bash
python scripts/run_pilot.py --tasks 1 --dry-run \
  --model qwen/qwen-2.5-7b-instruct
```

Expected:

- Exit 0
- Manifest under `data/outputs/runs/<run_id>/manifest.json` with `dry_run: true`
- No network; no API key required

## Offline tests

```bash
pytest tests/test_runner.py -v
pytest tests/ -q
```

Expected: pass with no `OPENROUTER_API_KEY` and no network (SC-005).

## Live 1-task smoke (optional)

```bash
RUN_LIVE_TESTS=1 pytest tests/test_runner.py -m live -v
# or:
python scripts/run_pilot.py --tasks 1 --model qwen/qwen-2.5-7b-instruct
```

Expected: one JSONL record + manifest; cost ledger updated if a paid call occurred.

## Resume check

Re-run the same command after a successful live generation; cache hits should
perform zero provider calls (SC-002).
