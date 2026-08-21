"""Routing metrics including Route-AUC vs always-m2."""

from __future__ import annotations

from hecate.router.dataset import RouterExample

_DEFAULT_LAMBDAS = tuple(i / 100 for i in range(101))


def _routed_resolves(example: RouterExample, score: float, lam: float) -> bool:
    if score >= lam:
        return example.m1_resolves
    return example.m2_resolves


def route_metrics(
    examples: list[RouterExample],
    scores: list[float],
    *,
    lambdas: tuple[float, ...] | None = None,
) -> dict[str, float]:
    """always_m1/m2, random, oracle, route_auc, best_lambda, best_route_rate."""
    if len(examples) != len(scores):
        raise ValueError("examples and scores must be the same length")
    if not examples:
        return {
            "always_m1": 0.0,
            "always_m2": 0.0,
            "random": 0.0,
            "oracle": 0.0,
            "route_auc": 0.0,
            "best_lambda": 1.0,
            "best_route_rate": 0.0,
            "n": 0.0,
            "n_positive": 0.0,
        }
    grid = lambdas if lambdas is not None else _DEFAULT_LAMBDAS
    n = len(examples)
    always_m1 = sum(1 for ex in examples if ex.m1_resolves) / n
    always_m2 = sum(1 for ex in examples if ex.m2_resolves) / n
    oracle = sum(1 for ex in examples if ex.m1_resolves or ex.m2_resolves) / n
    random_rate = 0.5 * always_m1 + 0.5 * always_m2
    rates: list[float] = []
    for lam in grid:
        hit = sum(
            1
            for ex, score in zip(examples, scores, strict=True)
            if _routed_resolves(ex, score, lam)
        )
        rates.append(hit / n)
    auc = 0.0
    for index in range(len(grid) - 1):
        width = grid[index + 1] - grid[index]
        left = rates[index] - always_m2
        right = rates[index + 1] - always_m2
        auc += width * 0.5 * (left + right)
    best_i = max(range(len(grid)), key=lambda i: (rates[i], -grid[i]))
    return {
        "always_m1": always_m1,
        "always_m2": always_m2,
        "random": random_rate,
        "oracle": oracle,
        "route_auc": auc,
        "best_lambda": float(grid[best_i]),
        "best_route_rate": rates[best_i],
        "n": float(n),
        "n_positive": float(sum(1 for ex in examples if ex.m1_resolves)),
    }
