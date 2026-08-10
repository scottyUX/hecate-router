# Tasks: Pilot Run (20 × 1)

- [x] T001 Ensure runner manifest records `wall_clock_s`, `cost_per_sample_usd`, `pair_timings`
- [x] T002 Run live pilot: `python scripts/run_pilot.py --tasks 20 --model qwen/qwen-2.5-7b-instruct --output-dir data/outputs/runs/pilot-20x1-final`
- [x] T003 Verify 20 JSONL records + manifest metrics
- [x] T004 Inspect a sample of patches; write notes under `specs/012-pilot-run/inspection-notes.md`
- [x] T005 Confirm offline `pytest tests/test_runner.py -q` still passes
