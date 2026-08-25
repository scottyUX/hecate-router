"""Fold assignment with label×repo stratification and fallbacks."""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass

from hecate.router.dataset import RouterExample

LABEL_REPO = "label_repo"
REPO = "repo"
ROUND_ROBIN = "round_robin"


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
