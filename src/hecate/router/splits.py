"""Fold assignment with label×repo stratification and fallbacks."""

from __future__ import annotations

import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

from hecate.router.dataset import RouterExample

LABEL_REPO = "label_repo"
REPO = "repo"
ROUND_ROBIN = "round_robin"
GROUPED_REPO = "grouped_repo"
LABEL_STRATIFIED = "label_stratified"
LEAVE_REPO = "leave_repo"
SPECIALIST = "specialist"


@dataclass(frozen=True)
class FoldAssignment:
    seed: int
    strategy: str
    n_folds: int
    fold_of: dict[str, int]


def _assign_from_groups(
    groups: dict[object, list[str]],
    *,
    n_folds: int,
    rng: random.Random,
) -> dict[str, int]:
    fold_of: dict[str, int] = {}
    for ids in groups.values():
        shuffled = list(ids)
        rng.shuffle(shuffled)
        for index, instance_id in enumerate(shuffled):
            fold_of[instance_id] = index % n_folds
    return fold_of


def assign_folds(
    examples: list[RouterExample],
    *,
    n_folds: int = 5,
    seed: int = 0,
) -> FoldAssignment:
    """Prefer (label, repo) strata; fall back to repo, then round-robin."""
    if n_folds < 2:
        raise ValueError("n_folds must be >= 2")
    rng = random.Random(seed)
    ids = [ex.instance_id for ex in examples]
    if len(ids) < n_folds:
        fold_of = {iid: index % n_folds for index, iid in enumerate(ids)}
        return FoldAssignment(
            seed=seed, strategy=ROUND_ROBIN, n_folds=n_folds, fold_of=fold_of
        )

    label_repo: dict[tuple[bool, str], list[str]] = defaultdict(list)
    repo_only: dict[str, list[str]] = defaultdict(list)
    for ex in examples:
        label_repo[(ex.m1_resolves, ex.repo)].append(ex.instance_id)
        repo_only[ex.repo].append(ex.instance_id)

    if all(len(members) >= n_folds for members in label_repo.values()):
        return FoldAssignment(
            seed=seed,
            strategy=LABEL_REPO,
            n_folds=n_folds,
            fold_of=_assign_from_groups(label_repo, n_folds=n_folds, rng=rng),
        )
    if all(len(members) >= n_folds for members in repo_only.values()):
        return FoldAssignment(
            seed=seed,
            strategy=REPO,
            n_folds=n_folds,
            fold_of=_assign_from_groups(repo_only, n_folds=n_folds, rng=rng),
        )
    shuffled = list(ids)
    rng.shuffle(shuffled)
    fold_of = {iid: index % n_folds for index, iid in enumerate(shuffled)}
    return FoldAssignment(
        seed=seed, strategy=ROUND_ROBIN, n_folds=n_folds, fold_of=fold_of
    )


def repo_histogram(examples: list[RouterExample]) -> dict[str, Any]:
    """Repo-size histogram used to justify grouped CV."""
    counts = Counter(ex.repo for ex in examples)
    n = len(examples)
    if not counts:
        return {
            "n_repos": 0,
            "n_examples": 0,
            "min": 0,
            "max": 0,
            "median": 0,
            "n_repos_lt_5": 0,
            "share_top3": 0.0,
            "counts": {},
        }
    sizes = sorted(counts.values())
    top = counts.most_common()
    top3 = sum(size for _, size in top[:3])
    return {
        "n_repos": len(counts),
        "n_examples": n,
        "min": sizes[0],
        "max": sizes[-1],
        "median": sizes[len(sizes) // 2],
        "n_repos_lt_5": sum(1 for size in sizes if size < 5),
        "share_top3": top3 / n if n else 0.0,
        "counts": dict(sorted(counts.items())),
    }


def assign_grouped_repo_folds(
    examples: list[RouterExample],
    *,
    n_folds: int = 5,
    seed: int = 0,
) -> FoldAssignment:
    """Put each repo in exactly one fold (greedy pack by size)."""
    if n_folds < 2:
        raise ValueError("n_folds must be >= 2")
    rng = random.Random(seed)
    by_repo: dict[str, list[str]] = defaultdict(list)
    for ex in examples:
        by_repo[ex.repo].append(ex.instance_id)
    items = list(by_repo.items())
    rng.shuffle(items)
    items.sort(key=lambda pair: -len(pair[1]))
    fold_n = [0] * n_folds
    fold_of: dict[str, int] = {}
    for _repo, ids in items:
        fold = min(range(n_folds), key=lambda index: (fold_n[index], index))
        for instance_id in ids:
            fold_of[instance_id] = fold
        fold_n[fold] += len(ids)
    return FoldAssignment(
        seed=seed, strategy=GROUPED_REPO, n_folds=n_folds, fold_of=fold_of
    )


def assign_label_stratified_folds(
    examples: list[RouterExample],
    *,
    n_folds: int = 5,
    seed: int = 0,
) -> FoldAssignment:
    """Stratify by label only. Repos may leak across train and val."""
    if n_folds < 2:
        raise ValueError("n_folds must be >= 2")
    rng = random.Random(seed)
    by_label: dict[bool, list[str]] = defaultdict(list)
    for ex in examples:
        by_label[ex.m1_resolves].append(ex.instance_id)
    return FoldAssignment(
        seed=seed,
        strategy=LABEL_STRATIFIED,
        n_folds=n_folds,
        fold_of=_assign_from_groups(by_label, n_folds=n_folds, rng=rng),
    )


def assign_leave_repo_out(
    examples: list[RouterExample],
    repo: str,
    *,
    seed: int = 0,
) -> FoldAssignment:
    """Two folds: hold ``repo`` (fold 0), then hold everything else (fold 1).

    Not greedy pack. Fold 0 is exactly ``repo``; fold 1 is the complement.
    """
    hold_repo = (repo or "").strip()
    if not hold_repo:
        raise ValueError("hold repo must be a non-empty string")
    in_repo = [ex.instance_id for ex in examples if ex.repo == hold_repo]
    out_repo = [ex.instance_id for ex in examples if ex.repo != hold_repo]
    if not in_repo:
        present = sorted({ex.repo for ex in examples})
        raise ValueError(f"hold repo {hold_repo!r} is missing from examples; have {present}")
    if not out_repo:
        raise ValueError(f"hold repo {hold_repo!r} covers every example; reverse split is empty")
    fold_of = {iid: 0 for iid in in_repo}
    fold_of.update({iid: 1 for iid in out_repo})
    return FoldAssignment(
        seed=seed, strategy=LEAVE_REPO, n_folds=2, fold_of=fold_of
    )


def assign_specialist_split(
    examples: list[RouterExample],
    repo: str,
    *,
    hold_fraction: float = 0.2,
    seed: int = 0,
) -> FoldAssignment:
    """Single-repo 80/20 split, label-stratified on ``m1_resolves``.

    Fold 0 is the holdout; fold 1 is train. Other repos are ignored.
    Instance ids are sorted inside each stratum, and strata are walked in
    sorted key order, so the holdout is independent of caller list order.
    """
    hold_repo = (repo or "").strip()
    if not hold_repo:
        raise ValueError("specialist repo must be a non-empty string")
    if not 0.0 < hold_fraction < 1.0:
        raise ValueError(f"hold_fraction must be in (0, 1), got {hold_fraction}")
    in_repo = [ex for ex in examples if ex.repo == hold_repo]
    if not in_repo:
        present = sorted({ex.repo for ex in examples})
        raise ValueError(
            f"specialist repo {hold_repo!r} is missing from examples; have {present}"
        )
    by_label: dict[bool, list[str]] = defaultdict(list)
    for ex in in_repo:
        by_label[ex.m1_resolves].append(ex.instance_id)
    rng = random.Random(seed)
    fold_of: dict[str, int] = {}
    n_hold = 0
    for key in sorted(by_label):
        ids = sorted(by_label[key])
        rng.shuffle(ids)
        n_stratum_hold = int(len(ids) * hold_fraction + 0.5)
        if n_stratum_hold >= len(ids) and len(ids) > 1:
            n_stratum_hold = len(ids) - 1
        for index, instance_id in enumerate(ids):
            fold_of[instance_id] = 0 if index < n_stratum_hold else 1
        n_hold += min(n_stratum_hold, len(ids))
    n_train = len(fold_of) - n_hold
    if n_hold == 0 or n_train == 0:
        raise ValueError(
            f"specialist split for {hold_repo!r} is empty "
            f"(n_train={n_train}, n_hold={n_hold}, n={len(fold_of)})"
        )
    return FoldAssignment(
        seed=seed, strategy=SPECIALIST, n_folds=2, fold_of=fold_of
    )
