/** Verified against gitignored run artifacts on 2026-08-26. Logistic is the headline head. */

export const ROUTER_V2 = {
  leak: true,
  n: 500,
  djangoN: 231,
  restN: 269,
  truncation: 0.032,
  cacheFiles: 623,
  parseErrors: 1,
  target: {
    djangoRouteAuc: 0.55,
    djangoAuroc: 0.6,
  },
  chart: {
    routeAuc: [
      { split: "Grouped 5-fold", text: 0.589, fusion: 0.593, metrics: 0.488 },
      { split: "Django holdout", text: 0.477, fusion: 0.482, metrics: 0.479 },
    ],
    auroc: [
      { split: "Grouped 5-fold", text: 0.534, fusion: 0.553, metrics: 0.47 },
      { split: "Django holdout", text: 0.516, fusion: 0.518, metrics: 0.48 },
    ],
  },
  logistic: {
    grouped: {
      text: { routeAuc: "0.589 ± 0.194", auroc: "0.534 ± 0.083", acc: "0.525 ± 0.082", brier: "0.251 ± 0.017", f1: "0.629 ± 0.123" },
      fusion: { routeAuc: "0.593 ± 0.180", auroc: "0.553 ± 0.070", acc: "0.535 ± 0.087", brier: "0.250 ± 0.017", f1: "0.641 ± 0.116" },
      metrics: { routeAuc: "0.488 ± 0.104", auroc: "0.470 ± 0.096", acc: "0.495 ± 0.077", brier: "0.262 ± 0.017", f1: "0.419 ± 0.228" },
    },
    django: {
      text: { routeAuc: "0.477 ± 0.030", auroc: "0.516 ± 0.015", acc: "0.519 ± 0.060", brier: "0.250 ± 0.008", alwaysSmall: "0.580" },
      fusion: { routeAuc: "0.482 ± 0.020", auroc: "0.518 ± 0.021", acc: "0.527 ± 0.068", brier: "0.250 ± 0.010", alwaysSmall: "0.580" },
      metrics: { routeAuc: "0.479 ± 0.101", auroc: "0.480 ± 0.081", acc: "0.494 ± 0.078", brier: "0.259 ± 0.014", alwaysSmall: "0.580" },
    },
    rest: {
      text: { routeAuc: "0.578 ± 0.023", auroc: "0.552 ± 0.064", acc: "0.537 ± 0.018" },
      fusion: { routeAuc: "0.581 ± 0.050", auroc: "0.573 ± 0.068", acc: "0.558 ± 0.024" },
      metrics: { routeAuc: "0.486 ± 0.074", auroc: "0.490 ± 0.038", acc: "0.488 ± 0.026" },
    },
  },
  mlp: {
    grouped: {
      text: { routeAuc: "0.491 ± 0.142", auroc: "0.514 ± 0.068" },
      fusion: { routeAuc: "0.467 ± 0.119", auroc: "0.533 ± 0.080" },
      metrics: { routeAuc: "0.447 ± 0.102", auroc: "0.493 ± 0.091" },
    },
    django: {
      text: { routeAuc: "0.484 ± 0.086", auroc: "0.528 ± 0.065" },
      fusion: { routeAuc: "0.469 ± 0.020", auroc: "0.543 ± 0.046" },
      metrics: { routeAuc: "0.546 ± 0.042", auroc: "0.521 ± 0.075" },
    },
  },
} as const;
