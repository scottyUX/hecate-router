/** v3 trajectory router. PENDING spec until a smoke run exists. */

export const ROUTER_V3 = {
  status: "pending",
  date: "2026-08-26",
  rev: 2,
  n: 500,
  djangoN: 231,
  restN: 269,
  stretch: {
    djangoRouteAuc: 0.55,
  },
  v1v2: {
    djangoRouteAuc: { text: "0.477 ± 0.030", fusion: "0.482 ± 0.020" },
    djangoAuroc: { text: "0.516 ± 0.015", fusion: "0.518 ± 0.021" },
    groupedRouteAuc: { text: "0.589 ± 0.194", fusion: "0.593 ± 0.180" },
  },
  sweRouter: {
    mix1: {
      gpt5miniK0: "0.549",
      gpt5miniK3: "0.694",
      deepseekK0: "0.627",
      deepseekK3: "0.750",
    },
    smithRepoDisjoint: {
      gpt5miniK0: "0.626",
      gpt5miniK3: "0.547",
      deepseekK0: "0.555",
      deepseekK3: "0.547",
    },
  },
  paperDeviation:
    "No 3-way LLM paraphrases of q (SWE-Router §A.2); skipped for cost.",
  traces: {
    provenance: "hf",
    nMatched: 500,
    resolveBitsInDump: false,
    k3TruncationRate: 0.006,
    k3TruncatedN: 3,
    medianTokens: 3495,
    maxTokens: 11008,
  },
  gpu: {
    blocked: true,
    reason:
      "Quota GPUS_ALL_REGIONS is 0 on hecate-506120 (regional NVIDIA_L4_GPUS is 1). Smoke not run. Full protocol not started.",
  },
  secondHoldout: "sympy/sympy",
  related: [
    "/journal/2026-08-25-text-only-router-v1",
    "/journal/2026-08-26-oracle-metrics-fusion-v2",
  ],
} as const;
