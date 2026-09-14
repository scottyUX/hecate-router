# mini-SWE-agent smoke runs — cost summary

All runs: SWE-bench Lite, mini-swe-agent 2.4.6, arm64 Mac with
`--platform linux/amd64` (x86 images under Rosetta), `--workers 1`.

## Per run

| run | instance | model | calls | cost | exit_status | patch |
|---|---|---|---:|---:|---|---:|
| miniswe-72b-retry2 | 14182 | 72B | 8 | $0.0118 | RepeatedFormatError | 0 ch |
| miniswe-mac-smoke | 12907 | 7B | 18 | $0.0015 | Submitted | 0 ch |
| miniswe-mac-smoke | 14182 | 7B | 85 | $0.0041 | BadRequestError | 0 ch |
| miniswe-mac-smoke72 | 12907 | 72B | 6 | $0.0155 | Submitted | 778 ch |
| miniswe-mac-smoke72 | 14182 | 72B | 23 | $0.1040 | LimitsExceeded | 0 ch |
| miniswe-72b-retry | 14182 | 72B | — | _lost_ | killed (provider stall, ~11 min no response) | 0 ch |

**Measured total: $0.1371** across 5 completed instances.

The killed run's cost was never written: mini-SWE persists `instance_cost`
only when an instance terminates, so an interrupted instance leaves no record.
Estimated $0.10-0.30 by comparison with the capped run ($0.104 at 23 calls).
For a long sweep, treat OpenRouter's usage API as the source of truth, not the
trajectories.

## Per-instance cost by model

| model | instances | mean | min | max |
|---|---:|---:|---:|---:|
| 72B | 3 | $0.0438 | $0.0118 | $0.1040 |
| 7B | 2 | $0.0028 | $0.0015 | $0.0041 |

Parser-path reference (`data/output/runs/sweep-2x300-qwen`, 600 samples,
single-shot): **$0.567 total** — $0.00162/instance for 72B, $0.00027 for 7B.

## Projection to the full 600

| arm | mean/instance | x300 |
|---|---:|---:|
| 7B | $0.0028 | $0.85 |
| 72B | $0.0438 | $13.14 |
| **600 total** | | **$13.99** |

Caveats on that projection:

- n=2 per arm, both astropy, both unresolved. Not a representative sample.
- The 72B mean is inflated by one instance truncated at a $0.10 cap; a run
  allowed to finish could cost more, not less.
- Cost per call grows superlinearly (history is resent every step), so
  instances that run longer cost disproportionately more.
- Against `option_a.yaml`: target_usd 38, ceiling_usd 100.
