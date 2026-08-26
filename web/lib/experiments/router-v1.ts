/** Verified against the v1 journal write-up and LDO run on 2026-08-25/26. */

export const ROUTER_V1 = {
  n: 500,
  djangoN: 231,
  restN: 269,
  truncation: 0.032,
  alwaysSmall: 0.554,
  alwaysLarge: 0.676,
  oracle: 0.714,
  headroomPp: 3.8,
  djangoAlwaysSmall: 0.58,
  restAlwaysSmall: 0.532,
  target: {
    routeAuc: 0.55,
    auroc: 0.6,
  },
  complementarity: {
    smallOnly: 19,
    both: 258,
    neither: 143,
    opusOnly: 80,
  },
  chart: {
    routeAuc: [
      { split: "Grouped 5-fold", logistic: 0.589, mlp: 0.491 },
      { split: "Leaky stratified", logistic: 0.533, mlp: 0.513 },
      { split: "Django holdout", logistic: 0.477, mlp: 0.484 },
    ],
    auroc: [
      { split: "Grouped 5-fold", logistic: 0.534, mlp: 0.514 },
      { split: "Django holdout", logistic: 0.516, mlp: 0.528 },
    ],
    folds: [
      { fold: "django n=231", routeAuc: 0.45, auroc: 0.51 },
      { fold: "sympy n=75", routeAuc: 0.84, auroc: 0.57 },
      { fold: "sphinx mix n=65", routeAuc: 0.51, auroc: 0.57 },
      { fold: "matplotlib n=65", routeAuc: 0.55, auroc: 0.5 },
      { fold: "sklearn mix n=64", routeAuc: 0.35, auroc: 0.34 },
    ],
  },
  logistic: {
    grouped: {
      routeAuc: "0.589 ± 0.194",
      auroc: "0.534 ± 0.083",
      acc: "0.525 ± 0.082",
      leakyRouteAuc: "0.533 ± 0.077",
    },
    django: {
      routeAuc: "0.477 ± 0.030",
      auroc: "0.516 ± 0.015",
      acc: "0.519 ± 0.060",
    },
    rest: {
      routeAuc: "0.578 ± 0.023",
      auroc: "0.552 ± 0.064",
      acc: "0.537 ± 0.018",
    },
  },
  mlp: {
    grouped: {
      routeAuc: "0.491 ± 0.142",
      auroc: "0.514 ± 0.068",
      acc: "0.528 ± 0.084",
      leakyRouteAuc: "0.513 ± 0.094",
    },
    django: {
      routeAuc: "0.484 ± 0.086",
      auroc: "0.528 ± 0.065",
    },
  },
} as const;
