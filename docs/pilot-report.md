# Stage-1 Pilot Report & Go/No-Go (S13)

**Date**: 2026-08-10  
**Pilot run**: `data/outputs/runs/pilot-20x1-final/`  
**Model**: `qwen/qwen-2.5-7b-instruct` (small tier)  
**Config**: `configs/option_a.yaml`  
**Git**: see run manifest `git_commit`

## Recommendation

**NO-GO for M2 (full 1,200-sample sweep).**

The pilot produces patches and stays far under budget, but it is **not clean**:
only ~53% of responses parse as valid unified diffs under S8, and oversized
oracle contexts can hard-fail the provider. Fix scaffold/context sizing and raise
parse-clean rate before authorizing full-matrix spend.

## Pilot metrics (S12)

| Metric | Value |
|--------|------:|
| Tasks × models | 20 × 1 |
| Records written | 20 |
| Parse OK | 10 (50% of pairs; **52.6%** of responses) |
| Parse fail | 9 |
| Provider error (no response) | 1 |
| Total cost (USD) | **~$0.0068** |
| Cost per paid sample (USD) | **~$0.00029** |
| Wall clock | **~102 s** (~5.1 s/pair including clones) |

Source details: [`specs/012-pilot-run/inspection-notes.md`](../specs/012-pilot-run/inspection-notes.md).

## Extrapolation to full sweep (300 × 4 = 1,200)

Assumptions (explicit):

1. Per-sample cost scales like the **small-model** pilot mean (~$0.00029). Large
   models in Option A are ~5–15× more expensive per token; a conservative blend
   of ~**10×** small-model cost for the matrix average is used below.
2. Wall-clock scales roughly linearly with pairs after repo caches warm; pilot
   included cold clones.
3. Context-length refusals and parse failures continue at similar rates unless
   remediated (they should not).

| Estimate | Low (small-like) | Conservative blend |
|----------|-----------------:|-------------------:|
| Cost for 1,200 samples | ~$0.35 | ~$3–5 |
| Vs target / ceiling | << $38 / $100 | << $38 / $100 |
| Wall-clock (sequential-ish) | ~1.5–3 h | ~4–8 h |

**Budget is not the blocker.** Quality is.

## Red flags

1. **Parse-clean rate ~53%** — many outputs look like diffs but fail S8
   validation (incomplete hunks / structure). Not ready to treat as a clean
   counterfactual matrix.
2. **Context length overflow** — at least one oracle context (~126k chars)
   exceeded the ~32k token model window (`PermanentAPIError` HTTP 400). Needs
   truncation, file capping, or model/window policy before scale.
3. **Day-2 gate** — issue #12: if patches don't parse cleanly, stop and debug
   scaffold rather than push to M2. That condition holds.

## What already works

- End-to-end runner (S11): cache, budget authorize, JSONL, manifest, resume.
- Hard ceiling guard (S10) and offline CI suite.
- Live OpenRouter path returns human-readable diffs on successes.
- Pilot spend is negligible; resume/caching prevents duplicate paid calls.

## Deferred (advisors)

Stage-3 label scheme — binary “escalate?” vs multiclass “cheapest-resolver” —
remains open until a cleaner small/large solve-rate split is available from
execution (Stage 2), not from this dirty parse mix.

## Exit criteria to flip to GO

Before starting S14:

1. Parse-clean rate **≥ 80%** on a fresh 20×1 (same model) after scaffold/extract
   fixes, **or** documented acceptance of a lower bar by advisors.
2. No context-length hard fails on the pilot set (truncate/cap oracle files or
   skip with an explicit recorded reason that is not an API 400 surprise).
3. Re-run pilot checklist in [`specs/012-pilot-run/quickstart.md`](../specs/012-pilot-run/quickstart.md).

## Bottom line

**NO-GO** on M2 full sweep today. Continue engineering on prompt/context size and
patch extraction quality; re-pilot; then revisit go/no-go.
