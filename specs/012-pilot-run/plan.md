# Implementation Plan: Pilot Run (20 × 1)

**Branch**: `012-pilot-run` | **Date**: 2026-08-10 | **Spec**: [spec.md](./spec.md)

## Summary

Execute `scripts/run_pilot.py --tasks 20 --model qwen/qwen-2.5-7b-instruct` with
live OpenRouter, capturing JSONL + manifest (cost, wall-clock, pair timings).
Add timing fields to the S11 runner if missing. Document inspection notes.

## Technical Context

**Language/Version**: Python 3.10+  
**Primary Dependencies**: Existing S11 runner + OpenRouter  
**Storage**: `data/outputs/runs/pilot-20x1/` (gitignored)  
**Testing**: Offline runner tests remain green; pilot itself is a live ops run  
**Constraints**: Hard ceiling $100; day-2 parse gate

## Constitution Check

| Principle | Verdict |
|-----------|---------|
| II Manifest | PASS — pilot writes full manifest |
| III Offline CI | PASS — no new ungated live tests |
| V Budget | PASS — S10 authorize still enforced |
| VI Secrets | PASS — key from `.env` only |

**Result: GREEN**
