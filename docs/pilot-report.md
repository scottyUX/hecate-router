# Stage-1 Pilot Report & Go/No-Go (S13)

**Date**: 2026-08-10 (updated after remediation re-pilots)  
**Primary remediated run**: `data/outputs/runs/pilot-20x1-v4/`  
**Model**: `qwen/qwen-2.5-7b-instruct` (small tier)  
**Config**: `configs/option_a.yaml` (context caps + `PROMPT_VERSION=v4`)

## Recommendation

**NO-GO for M2 (full 1,200-sample sweep).**

Context-length hard fails are fixed (0 HTTP 400s on the remediations). Parse-clean
rate remains **well below 80%** (best remediations ~45–50%). Do not start S14 yet.

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

| Run | Prompt | Parse-clean | ctx-400 | Cost |
|-----|--------|------------:|--------:|-----:|
| remediated (v2 strict, no fences) | v2 | 35% | 0 | ~$0.011 |
| v3 (strict + optional fence) | v3 | 25% | 0 | ~$0.015 |
| **v4 (v1-like + header hint + caps)** | **v4** | **45%** | **0** | ~$0.019 |

**Shipped defaults after remediation:** context file caps in Option A + prompt `v4`
+ runner `max_tokens` clamp against `generation.context_window_tokens`.

## Extrapolation to full sweep (unchanged conclusion)

Budget is still fine (<< $38 / $100). **Quality is the blocker.**

## Red flags (updated)

1. **Parse-clean still ~45%** under v4 — S8 `invalid_structure` dominates.
2. **Stricter prompts hurt** — v2/v3 regressed vs the original pilot.
3. **Context caps work** — `astropy__astropy-7746` no longer 400s; prompts may
   include `[truncated …]` markers when files exceed budgets.

## Exit criteria to flip to GO (unchanged)

1. Parse-clean rate **≥ 80%** on a fresh 20×1 (same model), **or** advisor waiver.
2. **0** context-length hard fails on the pilot set.
3. Re-run checklist in `specs/012-pilot-run/quickstart.md`.

## Next engineering (toward S14)

- Keep context caps + `max_tokens` clamp (keep).
- Investigate S8 failure modes on the 11 v4 fails (snippet-only vs broken hunks).
- Consider a single bounded repair retry on `patch_parse_ok=False` (cost-aware).
- Optionally trial the other small model (`meta-llama/llama-3.1-8b-instruct`) on
  the same 20 before changing the gate.

## Bottom line

**NO-GO.** Context window risk is mitigated; parse-clean is not ready for M2.
