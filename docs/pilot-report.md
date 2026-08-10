# Stage-1 Pilot Report & Go/No-Go (S13)

**Date**: 2026-08-10 (updated after model selection + S13 waiver)  
**Primary remediated run**: `data/outputs/runs/pilot-20x1-v5-repair/`  
**Model**: `qwen/qwen-2.5-7b-instruct` (small tier)  
**Config**: `configs/option_a.yaml` (context caps + `PROMPT_VERSION=v5` + one-shot repair)

## Recommendation

**S13 80% parse-clean waived for M2** — proceed with a **reduced S14** (2 × 300 = 600).

Context-length hard fails are fixed (0 HTTP 400s). Parse-clean reached **65%** on
Qwen-7B (still below the original 80% bar). After comparing small models, Stage-1
locks to the Qwen size ladder and drops Llama from the matrix.

## Model selection (small-model pilot)

| Model | Parse-clean | ctx-400 |
|-------|------------:|--------:|
| `qwen/qwen-2.5-7b-instruct` | **65%** (13/20) | 0 |
| `meta-llama/llama-3.1-8b-instruct` | 35% (7/20) | 0 |

**Active Option A pair for S14:** small `qwen/qwen-2.5-7b-instruct` · large
`qwen/qwen-2.5-72b-instruct`. Estimated mid cost for 600 samples ~$0.71 (≪ $38).

## Pilot metrics

### Baseline (pre-remediation)

| Metric | Value |
|--------|------:|
| Run | `pilot-20x1-final` |
| Parse OK / fail / none | 10 / 9 / 1 |
| Parse-clean (pairs) | **50%** |
| Context-length 400s | **1** |
| Total cost USD | ~0.0068 |

### Remediation matrix (same 20 × qwen-2.5-7b)

| Run | Prompt / path | Parse-clean | ctx-400 | Cost |
|-----|---------------|------------:|--------:|-----:|
| remediated (v2 strict, no fences) | v2 | 35% | 0 | ~$0.011 |
| v3 (strict + optional fence) | v3 | 25% | 0 | ~$0.015 |
| v4 (v1-like + header hint + caps) | v4 | 45% | 0 | ~$0.019 |
| **v5 + one-shot repair** | **v5 + repair** | **65%** | **0** | **~$0.024** |
| v5 + repair (llama-3.1-8b) | v5 + repair | **35%** | 0 | ~$0.002 |

**v5-repair detail (qwen):** 13 / 20 parse OK; `pairs_repaired=1`; remaining 7
fails are still S8 `invalid_structure`. First-pass alone ≈ 60%.

**Shipped defaults:** context file caps + prompt `v5` + runner one-shot repair +
`max_tokens` clamp against `generation.context_window_tokens`.

## Extrapolation

Budget is fine for the reduced 600-sample sweep. Format quality remains imperfect
but is accepted under the M2 waiver so training patches can be collected.

## Red flags

1. **Parse-clean 65%** — waived, not solved.
2. **Repair helps little** — only 1/≈7 failed first-passes became valid.
3. **Stricter prompts hurt** — v2/v3 regressed vs the original pilot.
4. **Context caps work** — no context-length 400s on remediated pilots.

## Next

- S14: `scripts/run_sweep.py` for 2 × 300 with caching (see issue #14).
- Then S15 validation / Stage-1 handoff.

## Bottom line

**Proceed to reduced S14 (Qwen 7B + 72B, 600 samples)** under S13 waiver.
Journal: `2026-08-10-parse-repair-second-small-model`.
