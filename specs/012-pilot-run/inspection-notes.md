# Pilot inspection notes (S12 + S13 remediation)

**Model**: `qwen/qwen-2.5-7b-instruct`  
**Date**: 2026-08-10

## Latest run (v4 — shipped direction)

**Path**: `data/outputs/runs/pilot-20x1-v4/`

| Metric | Value |
|--------|------:|
| Records | 20 |
| `patch_parse_ok=True` | 9 |
| `patch_parse_ok=False` | 11 |
| No response | 0 |
| Parse-clean | **45%** |
| Context-length 400s | **0** |
| Total cost USD | ~0.019 |

## Comparison

| Run | Parse-clean | ctx-400 |
|-----|------------:|--------:|
| baseline `pilot-20x1-final` | 50% | 1 |
| v2 strict | 35% | 0 |
| v3 fence example | 25% | 0 |
| v4 caps + light header hint | 45% | 0 |

## Day-2 / S13 gate

Context overflow is solved. Parse-clean **does not** meet ≥80%. **NO-GO** for S14.
