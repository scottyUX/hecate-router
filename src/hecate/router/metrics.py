"""Routing metrics including Route-AUC vs always-m2."""

from __future__ import annotations

from hecate.router.dataset import RouterExample

_DEFAULT_LAMBDAS = tuple(i / 100 for i in range(101))
DEFAULT_LAMBDAS = _DEFAULT_LAMBDAS


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


def auroc(labels: list[bool], scores: list[float]) -> float | None:
    """Mann-Whitney AUROC. None if a class is missing."""
    if len(labels) != len(scores):
        raise ValueError("labels and scores must be the same length")
    pos = [score for score, flag in zip(scores, labels, strict=True) if flag]
    neg = [score for score, flag in zip(scores, labels, strict=True) if not flag]
    if not pos or not neg:
        return None
    greater = 0.0
    pairs = 0
    for p_score in pos:
        for n_score in neg:
            pairs += 1
            if p_score > n_score:
                greater += 1.0
            elif p_score == n_score:
                greater += 0.5
    return greater / pairs


def f1_score(labels: list[bool], scores: list[float], *, threshold: float = 0.5) -> float:
    tp = fp = fn = 0
    for flag, score in zip(labels, scores, strict=True):
        pred = score >= threshold
        if pred and flag:
            tp += 1
        elif pred and not flag:
            fp += 1
        elif not pred and flag:
            fn += 1
    if tp + fp == 0 or tp + fn == 0:
        return 0.0
    precision = tp / (tp + fp)
    recall = tp / (tp + fn)
    if precision + recall == 0:
        return 0.0
    return 2.0 * precision * recall / (precision + recall)


def accuracy_score(
    labels: list[bool], scores: list[float], *, threshold: float = 0.5
) -> float:
    if not labels:
        return 0.0
    hits = sum(
        1
        for flag, score in zip(labels, scores, strict=True)
        if (score >= threshold) == flag
    )
    return hits / len(labels)


def brier_score(labels: list[bool], scores: list[float]) -> float:
    if not labels:
        return 0.0
    total = 0.0
    for flag, score in zip(labels, scores, strict=True):
        err = score - (1.0 if flag else 0.0)
        total += err * err
    return total / len(labels)


def sweep_lambda_curve(
    examples: list[RouterExample],
    scores: list[float],
    *,
    lambdas: tuple[float, ...] | None = None,
) -> list[dict[str, float]]:
    """Per-λ routing curve using the same policy as ``_normalized_route_auc``.

    ``use_small = score >= lam``. ``cost`` is the share routed to the large
    model (existing definition). ``frac_cheap`` is the share routed to Qwen.
    """
    if len(examples) != len(scores):
        raise ValueError("examples and scores must be the same length")
    grid = lambdas if lambdas is not None else _DEFAULT_LAMBDAS
    n = len(examples)
    if n == 0:
        return []
    rows: list[dict[str, float]] = []
    for lam in grid:
        large_n = 0
        hits = 0
        for ex, score in zip(examples, scores, strict=True):
            use_small = score >= lam
            if use_small:
                hits += int(ex.m1_resolves)
            else:
                large_n += 1
                hits += int(ex.m2_resolves)
        cost = large_n / n
        rows.append(
            {
                "lambda": float(lam),
                "frac_cheap": (n - large_n) / n,
                "cost": cost,
                "resolved_rate": hits / n,
            }
        )
    return rows


def _normalized_route_auc(
    examples: list[RouterExample],
    scores: list[float],
    *,
    lambdas: tuple[float, ...],
) -> float:
    n = len(examples)
    always_small = sum(1 for ex in examples if ex.m1_resolves) / n
    always_large = sum(1 for ex in examples if ex.m2_resolves) / n
    denom = always_large - always_small
    points: dict[float, float] = {0.0: 0.0, 1.0: 1.0}
    for row in sweep_lambda_curve(examples, scores, lambdas=lambdas):
        cost = row["cost"]
        rate = row["resolved_rate"]
        y = 0.0 if denom == 0 else (rate - always_small) / denom
        if cost not in (0.0, 1.0):
            points[cost] = y
    xs = sorted(points)
    auc = 0.0
    for index in range(len(xs) - 1):
        width = xs[index + 1] - xs[index]
        if width <= 0:
            continue
        auc += width * 0.5 * (points[xs[index]] + points[xs[index + 1]])
    return auc


def text_route_metrics(
    examples: list[RouterExample],
    scores: list[float],
    *,
    lambdas: tuple[float, ...] | None = None,
) -> dict[str, float | None]:
    """Normalized Route-AUC plus classification diagnostics.

    ``route_auc`` is the cost-vs-resolved-rate curve anchored at always-small
    (0, 0) and always-large (1, 1). ``lift_vs_large_auc`` is the Lite integral
    (rate − always-large) kept as a secondary diagnostic.
    """
    if len(examples) != len(scores):
        raise ValueError("examples and scores must be the same length")
    legacy = route_metrics(examples, scores, lambdas=lambdas)
    grid = lambdas if lambdas is not None else _DEFAULT_LAMBDAS
    labels = [ex.m1_resolves for ex in examples]
    always_small = float(legacy["always_m1"])
    always_large = float(legacy["always_m2"])
    oracle = float(legacy["oracle"])
    if not examples:
        normalized = 0.0
        clf_auroc: float | None = None
        clf_f1 = 0.0
        clf_acc = 0.0
        clf_brier = 0.0
    else:
        normalized = _normalized_route_auc(examples, scores, lambdas=grid)
        clf_auroc = auroc(labels, scores)
        clf_f1 = f1_score(labels, scores)
        clf_acc = accuracy_score(labels, scores)
        clf_brier = brier_score(labels, scores)
    return {
        "always_m1": always_small,
        "always_m2": always_large,
        "always_small": always_small,
        "always_large": always_large,
        "random": float(legacy["random"]),
        "oracle": oracle,
        "headroom": oracle - always_large,
        "route_auc": normalized,
        "lift_vs_large_auc": float(legacy["route_auc"]),
        "best_lambda": float(legacy["best_lambda"]),
        "best_route_rate": float(legacy["best_route_rate"]),
        "auroc": clf_auroc,
        "f1": clf_f1,
        "accuracy": clf_acc,
        "brier": clf_brier,
        "n": float(legacy["n"]),
        "n_positive": float(legacy["n_positive"]),
    }
